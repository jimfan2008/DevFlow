import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import pytest
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


# ====================================================================
# 领域模型
# ====================================================================

class AlertSeverity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class BreakerState(str, Enum):
    CLOSED = "closed"
    TRIPPED = "tripped"
    HALF_OPEN = "half_open"


@dataclass
class AlertRecord:
    id: str
    reason: str
    severity: AlertSeverity
    usage: int
    daily_limit: int
    usage_percent: float
    triggered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.id,
            "reason": self.reason,
            "severity": self.severity.value,
            "usage": self.usage,
            "daily_limit": self.daily_limit,
            "usage_percent": self.usage_percent,
            "triggered_at": self.triggered_at,
        }


class DailyTokenTracker:
    """跟踪当日 Token 消耗"""

    def __init__(self, daily_limit: int, date_tag: str = ""):
        self.daily_limit = daily_limit
        self.date_tag = date_tag
        self._usage = 0

    @property
    def usage(self) -> int:
        return self._usage

    @property
    def usage_percent(self) -> float:
        if self.daily_limit == 0:
            return 0.0
        return round(self._usage / self.daily_limit * 100, 2)

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self._usage)

    @property
    def is_exhausted(self) -> bool:
        return self._usage >= self.daily_limit

    def consume(self, tokens: int):
        self._usage += tokens

    def reset(self):
        self._usage = 0


class DailyLimitBreaker:
    """基于日限额的熔断器"""

    def __init__(self, trip_at_percent: float = 100.0, reset_timeout: float = 300.0):
        self.trip_at_percent = trip_at_percent
        self.reset_timeout = reset_timeout
        self._state = BreakerState.CLOSED
        self._tripped_at: Optional[float] = None

    @property
    def state(self) -> BreakerState:
        if self._state == BreakerState.TRIPPED and self._tripped_at is not None:
            if time.time() - self._tripped_at >= self.reset_timeout:
                self._state = BreakerState.HALF_OPEN
        return self._state

    @property
    def is_tripped(self) -> bool:
        return self.state == BreakerState.TRIPPED

    def should_allow(self) -> bool:
        return self.state in (BreakerState.CLOSED, BreakerState.HALF_OPEN)

    def trip(self):
        self._state = BreakerState.TRIPPED
        self._tripped_at = time.time()

    def reset(self):
        self._state = BreakerState.CLOSED
        self._tripped_at = None

    def record_success(self):
        if self._state == BreakerState.HALF_OPEN:
            self.reset()

    def record_failure(self):
        if self._state == BreakerState.HALF_OPEN:
            self.trip()


class DailyLimitAlertSystem:
    """基于日限额的告警系统"""

    P2_THRESHOLD = 80.0
    P1_THRESHOLD = 100.0

    def __init__(self, tracker: DailyTokenTracker, breaker: DailyLimitBreaker):
        self.tracker = tracker
        self.breaker = breaker
        self._alerts: List[AlertRecord] = []
        self._p1_triggered: bool = False
        self._p2_triggered: bool = False

    @property
    def alerts(self) -> List[AlertRecord]:
        return list(self._alerts)

    @property
    def p1_alert_count(self) -> int:
        return sum(1 for a in self._alerts if a.severity == AlertSeverity.P1)

    @property
    def p2_alert_count(self) -> int:
        return sum(1 for a in self._alerts if a.severity == AlertSeverity.P2)

    def check_and_alert(self) -> Optional[AlertRecord]:
        percent = self.tracker.usage_percent

        if percent >= self.P1_THRESHOLD and not self._p1_triggered:
            return self._create_alert(
                reason="daily_limit_exceeded",
                severity=AlertSeverity.P1,
            )

        if percent >= self.P2_THRESHOLD and not self._p2_triggered:
            return self._create_alert(
                reason="daily_limit_warning",
                severity=AlertSeverity.P2,
            )

        return None

    def _create_alert(self, reason: str, severity: AlertSeverity) -> AlertRecord:
        alert = AlertRecord(
            id=str(uuid.uuid4()),
            reason=reason,
            severity=severity,
            usage=self.tracker.usage,
            daily_limit=self.tracker.daily_limit,
            usage_percent=self.tracker.usage_percent,
        )
        self._alerts.append(alert)

        if severity == AlertSeverity.P1:
            self._p1_triggered = True
            self.breaker.trip()
        elif severity == AlertSeverity.P2:
            self._p2_triggered = True

        return alert

    def reset(self):
        self._alerts.clear()
        self._p1_triggered = False
        self._p2_triggered = False


# ====================================================================
# FastAPI 应用
# ====================================================================

app = FastAPI()

_system_tracker: Optional[DailyTokenTracker] = None
_system_breaker: Optional[DailyLimitBreaker] = None
_system_alert: Optional[DailyLimitAlertSystem] = None


def init_system(daily_limit: int = 1000000, date_tag: str = ""):
    global _system_tracker, _system_breaker, _system_alert
    _system_tracker = DailyTokenTracker(daily_limit, date_tag=date_tag)
    _system_breaker = DailyLimitBreaker(trip_at_percent=100.0)
    _system_alert = DailyLimitAlertSystem(_system_tracker, _system_breaker)
    return _system_tracker, _system_breaker, _system_alert


@app.post("/v1/chat/completions")
async def chat_completion(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")

    if _system_breaker is None or _system_breaker.should_allow() is False:
        return JSONResponse(
            status_code=429,
            content={"error": "daily_token_limit_exceeded"},
        )

    tokens_per_call = 100
    _system_tracker.consume(tokens_per_call)
    _system_alert.check_and_alert()

    return {"choices": [{"message": {"content": "OK"}}]}


@app.post("/v1/chat/completions/admin-reset")
async def admin_reset(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    if _system_tracker is not None:
        _system_tracker.reset()
    if _system_breaker is not None:
        _system_breaker.reset()
    if _system_alert is not None:
        _system_alert.reset()
    return {"status": "reset"}


client = TestClient(app)


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture(autouse=True)
def reset_system():
    init_system(daily_limit=1000)
    yield


@pytest.fixture
def tracker():
    return _system_tracker


@pytest.fixture
def breaker():
    return _system_breaker


@pytest.fixture
def alert_system():
    return _system_alert


# ====================================================================
# 测试 — P1 告警：reason=daily_limit_exceeded, severity=P1
# ====================================================================

class TestP1AlertContent:
    """告警系统生成 P1 级别告警，包含 reason=daily_limit_exceeded, severity=P1"""

    def test_p1_alert_generated_when_limit_exhausted(self, tracker, alert_system):
        tracker.consume(1000)
        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertSeverity.P1

    def test_p1_alert_reason_is_daily_limit_exceeded(self, tracker, alert_system):
        tracker.consume(1000)
        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.reason == "daily_limit_exceeded"

    def test_p1_alert_severity_is_p1(self, tracker, alert_system):
        tracker.consume(1000)
        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertSeverity.P1

    def test_p1_alert_contains_usage_and_limit(self, tracker, alert_system):
        tracker.consume(1000)
        alert = alert_system.check_and_alert()
        assert alert.usage == 1000
        assert alert.daily_limit == 1000

    def test_p1_alert_usage_percent_is_100(self, tracker, alert_system):
        tracker.consume(1000)
        alert = alert_system.check_and_alert()
        assert alert.usage_percent == 100.0

    def test_p1_alert_has_unique_id(self, tracker, alert_system):
        tracker.consume(1000)
        alert1 = alert_system.check_and_alert()
        assert alert1 is not None

        alert_system.reset()
        tracker.reset()
        tracker.consume(1000)
        alert2 = alert_system.check_and_alert()
        assert alert2 is not None
        assert alert1.id != alert2.id

    def test_p1_alert_appears_in_alerts_list(self, tracker, alert_system):
        tracker.consume(1000)
        alert_system.check_and_alert()
        assert len(alert_system.alerts) == 1
        assert alert_system.alerts[0].reason == "daily_limit_exceeded"
        assert alert_system.alerts[0].severity == AlertSeverity.P1

    def test_to_dict_contains_all_expected_fields(self, tracker, alert_system):
        tracker.consume(1000)
        alert = alert_system.check_and_alert()
        d = alert.to_dict()
        assert d["reason"] == "daily_limit_exceeded"
        assert d["severity"] == "P1"
        assert d["usage"] == 1000
        assert d["daily_limit"] == 1000
        assert d["usage_percent"] == 100.0


# ====================================================================
# 测试 — 熔断器状态为 tripped
# ====================================================================

class TestBreakerTripped:
    """熔断器状态为 tripped"""

    def test_breaker_closed_before_exhaustion(self, tracker, breaker):
        tracker.consume(500)
        assert breaker.state == BreakerState.CLOSED
        assert breaker.should_allow() is True

    def test_breaker_trips_when_limit_exhausted(self, tracker, alert_system, breaker):
        tracker.consume(1000)
        alert_system.check_and_alert()
        assert breaker.state == BreakerState.TRIPPED

    def test_breaker_trips_after_p1_alert(self, tracker, alert_system, breaker):
        tracker.consume(1000)
        alert_system.check_and_alert()
        assert breaker.is_tripped is True

    def test_should_allow_false_when_tripped(self, tracker, alert_system, breaker):
        tracker.consume(1000)
        alert_system.check_and_alert()
        assert breaker.should_allow() is False

    def test_trip_called_by_alert_system(self, tracker, alert_system, breaker):
        tracker.consume(1000)
        alert_system.check_and_alert()
        # 验证是 check_and_alert 触发了 trip，而不是其他路径
        assert breaker.is_tripped is True
        assert breaker.state == BreakerState.TRIPPED


# ====================================================================
# 测试 — HTTP 429 响应
# ====================================================================

class TestHttp429Response:
    """新的推理请求返回 HTTP 429，Body 包含 error=daily_token_limit_exceeded"""

    def test_normal_request_returns_200(self):
        init_system(daily_limit=10000)
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp.status_code == 200

    def test_after_limit_exhausted_returns_429(self):
        init_system(daily_limit=100)
        resp1 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp1.status_code == 200
        resp2 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp2.status_code == 429

    def test_429_body_contains_daily_token_limit_exceeded(self):
        init_system(daily_limit=100)
        client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "daily_token_limit_exceeded"

    def test_429_response_is_json(self):
        init_system(daily_limit=100)
        client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp.headers["content-type"] == "application/json"

    def test_429_only_after_limit_exhausted(self):
        init_system(daily_limit=500)
        resp1 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp1.status_code == 200
        resp2 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp2.status_code == 200
        resp3 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp3.status_code == 200
        resp4 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp4.status_code == 200
        resp5 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        assert resp5.status_code == 200
        resp6 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        # 500*5=500, consumed 500, remaining 0
        assert resp6.status_code == 429

    def test_all_requests_return_429_after_exhaustion(self):
        init_system(daily_limit=100)
        client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
        for _ in range(5):
            resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test-token"})
            assert resp.status_code == 429
            assert resp.json()["error"] == "daily_token_limit_exceeded"


# ====================================================================
# 测试 — 401 鉴权
# ====================================================================

class TestAuth:
    """缺少 Authorization 时返回 401"""

    def test_missing_auth_returns_401(self):
        init_system(daily_limit=10000)
        resp = client.post("/v1/chat/completions")
        assert resp.status_code == 401

    def test_missing_auth_returns_401_detail(self):
        init_system(daily_limit=10000)
        resp = client.post("/v1/chat/completions")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Missing authorization"

    def test_empty_auth_returns_401(self):
        init_system(daily_limit=10000)
        resp = client.post("/v1/chat/completions", headers={"Authorization": ""})
        assert resp.status_code == 401

    def test_valid_auth_succeeds(self):
        init_system(daily_limit=10000)
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer valid-token"})
        assert resp.status_code == 200


# ====================================================================
# 测试 — 边界比率
# ====================================================================

class TestBoundaryRatios:
    """边界比率测试"""

    def test_at_exactly_100_percent_triggers_p1(self, tracker, alert_system, breaker):
        tracker.consume(1000)
        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertSeverity.P1
        assert alert.usage_percent == 100.0

    def test_just_below_100_percent_does_not_trip(self, tracker, alert_system, breaker):
        tracker.consume(999)
        alert = alert_system.check_and_alert()
        assert alert is None
        assert breaker.state == BreakerState.CLOSED

    def test_at_exactly_80_percent_triggers_p2(self, tracker, alert_system, breaker):
        tracker.consume(800)
        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertSeverity.P2
        assert alert.usage_percent == 80.0

    def test_just_below_80_percent_no_alert(self, tracker, alert_system):
        tracker.consume(799)
        alert = alert_system.check_and_alert()
        assert alert is None

    def test_from_p2_to_p1_escalation(self, tracker, alert_system, breaker):
        tracker.consume(800)
        p2 = alert_system.check_and_alert()
        assert p2 is not None
        assert p2.severity == AlertSeverity.P2
        assert breaker.state == BreakerState.CLOSED

        tracker.consume(200)
        p1 = alert_system.check_and_alert()
        assert p1 is not None
        assert p1.severity == AlertSeverity.P1
        assert breaker.state == BreakerState.TRIPPED

    def test_both_alerts_recorded_in_history(self, tracker, alert_system):
        tracker.consume(800)
        alert_system.check_and_alert()
        tracker.consume(200)
        alert_system.check_and_alert()
        assert alert_system.p2_alert_count == 1
        assert alert_system.p1_alert_count == 1

    def test_no_duplicate_p1_alert(self, tracker, alert_system):
        tracker.consume(1000)
        first = alert_system.check_and_alert()
        assert first is not None
        second = alert_system.check_and_alert()
        assert second is None

    def test_no_duplicate_p2_alert(self, tracker, alert_system):
        tracker.consume(800)
        first = alert_system.check_and_alert()
        assert first is not None
        second = alert_system.check_and_alert()
        assert second is None

    def test_p2_triggered_flag_prevents_second_p2(self, tracker, alert_system):
        tracker.consume(800)
        alert_system.check_and_alert()
        tracker.consume(50)
        second = alert_system.check_and_alert()
        assert second is None


# ====================================================================
# 测试 — 熔断器重置、半开/恢复
# ====================================================================

class TestBreakerResetAndRecovery:
    """CircuitBreaker.reset() 和半开/恢复机制"""

    def test_reset_restores_closed_state(self, breaker):
        breaker.trip()
        assert breaker.state == BreakerState.TRIPPED
        breaker.reset()
        assert breaker.state == BreakerState.CLOSED
        assert breaker.should_allow() is True

    def test_reset_allows_requests_after_trip(self, breaker):
        breaker.trip()
        assert breaker.should_allow() is False
        breaker.reset()
        assert breaker.should_allow() is True
        assert breaker.state == BreakerState.CLOSED

    def test_half_open_after_reset_timeout(self):
        short_breaker = DailyLimitBreaker(trip_at_percent=100.0, reset_timeout=0.05)
        short_breaker.trip()
        assert short_breaker.state == BreakerState.TRIPPED
        time.sleep(0.1)
        assert short_breaker.state == BreakerState.HALF_OPEN

    def test_half_open_allows_request(self):
        short_breaker = DailyLimitBreaker(trip_at_percent=100.0, reset_timeout=0.05)
        short_breaker.trip()
        time.sleep(0.1)
        assert short_breaker.state == BreakerState.HALF_OPEN
        assert short_breaker.should_allow() is True

    def test_success_in_half_open_recovers_to_closed(self):
        short_breaker = DailyLimitBreaker(trip_at_percent=100.0, reset_timeout=0.05)
        short_breaker.trip()
        time.sleep(0.1)
        assert short_breaker.state == BreakerState.HALF_OPEN
        short_breaker.record_success()
        assert short_breaker.state == BreakerState.CLOSED

    def test_failure_in_half_open_retrips(self):
        short_breaker = DailyLimitBreaker(trip_at_percent=100.0, reset_timeout=0.05)
        short_breaker.trip()
        time.sleep(0.1)
        assert short_breaker.state == BreakerState.HALF_OPEN
        short_breaker.record_failure()
        assert short_breaker.state == BreakerState.TRIPPED

    def test_reset_timeout_does_not_auto_close(self):
        short_breaker = DailyLimitBreaker(trip_at_percent=100.0, reset_timeout=0.05)
        short_breaker.trip()
        time.sleep(0.1)
        assert short_breaker.state == BreakerState.HALF_OPEN
        assert short_breaker.should_allow() is True
        short_breaker.record_success()
        assert short_breaker.state == BreakerState.CLOSED

    def test_full_system_reset_restores_normal(self):
        init_system(daily_limit=200)
        client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        assert resp.status_code == 429

        resp = client.post("/v1/chat/completions/admin-reset", headers={"Authorization": "Bearer admin"})
        assert resp.status_code == 200

        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        assert resp.status_code == 200


# ====================================================================
# 测试 — 多日期隔离
# ====================================================================

class TestMultiDateIsolation:
    """多日期隔离：每日消耗独立统计"""

    def test_reset_for_new_day_clears_usage(self, tracker, breaker):
        tracker.consume(1000)
        assert tracker.is_exhausted is True
        tracker.reset()
        assert tracker.usage == 0
        assert tracker.is_exhausted is False

    def test_new_day_allows_new_requests(self, tracker, alert_system, breaker):
        tracker.consume(1000)
        alert_system.check_and_alert()
        assert breaker.is_tripped is True

        alert_system.reset()
        tracker.reset()
        breaker.reset()
        assert breaker.state == BreakerState.CLOSED
        assert tracker.usage == 0

        alert_system.check_and_alert()
        assert alert_system.p1_alert_count == 0

    def test_date_tag_isolation(self):
        day1_tracker = DailyTokenTracker(daily_limit=1000, date_tag="2026-07-20")
        day2_tracker = DailyTokenTracker(daily_limit=1000, date_tag="2026-07-21")

        day1_tracker.consume(1000)
        assert day1_tracker.is_exhausted is True
        assert day2_tracker.is_exhausted is False
        assert day2_tracker.usage == 0

        day2_tracker.consume(500)
        assert day2_tracker.usage == 500
        assert day1_tracker.usage == 1000

    def test_independent_breaker_per_day(self):
        breaker_day1 = DailyLimitBreaker(trip_at_percent=100.0)
        breaker_day2 = DailyLimitBreaker(trip_at_percent=100.0)

        breaker_day1.trip()
        assert breaker_day1.is_tripped is True
        assert breaker_day2.is_tripped is False
        assert breaker_day2.should_allow() is True


# ====================================================================
# 测试 — 不同 AlertSeverity 级别
# ====================================================================

class TestAlertSeverityLevels:
    """不同 AlertSeverity 级别的告警"""

    def test_p1_severity_is_p1(self):
        assert AlertSeverity.P1.value == "P1"

    def test_p2_severity_is_p2(self):
        assert AlertSeverity.P2.value == "P2"

    def test_p3_severity_is_p3(self):
        assert AlertSeverity.P3.value == "P3"

    def test_p1_alert_deduplication(self, tracker, alert_system):
        tracker.consume(1000)
        alert_system.check_and_alert()
        assert alert_system.p1_alert_count == 1
        alert_system.check_and_alert()
        assert alert_system.p1_alert_count == 1

    def test_p2_alert_deduplication(self, tracker, alert_system):
        tracker.consume(800)
        alert_system.check_and_alert()
        assert alert_system.p2_alert_count == 1
        alert_system.check_and_alert()
        assert alert_system.p2_alert_count == 1


# ====================================================================
# 测试 — 验收标准完整场景
# ====================================================================

class TestFullAcceptanceScenario:
    """验收标准完整场景：100% → P1告警 → 熔断 → 429"""

    def test_full_scenario_p1_alert_tripped_429(self):
        init_system(daily_limit=500)

        # 发送 6 次请求，每次消耗 100 tokens
        # 前 5 次消耗 500 tokens（达到 100%），第 5 次触发 P1 告警并熔断
        # 第 6 次请求因熔断器已跳开返回 429
        for i in range(6):
            resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
            if i < 5:
                assert resp.status_code == 200, f"Request {i+1} expected 200 but got {resp.status_code}"
            else:
                assert resp.status_code == 429, f"Request {i+1} expected 429 but got {resp.status_code}"

        # 验证告警内容
        assert _system_alert is not None
        alerts = _system_alert.alerts
        assert len(alerts) >= 1
        last_alert = alerts[-1]
        assert last_alert.reason == "daily_limit_exceeded"
        assert last_alert.severity == AlertSeverity.P1

        # 验证熔断器状态
        assert _system_breaker is not None
        assert _system_breaker.state == BreakerState.TRIPPED

        # 验证后续请求仍是 429
        for _ in range(3):
            resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
            assert resp.status_code == 429
            body = resp.json()
            assert body["error"] == "daily_token_limit_exceeded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
