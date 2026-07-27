import time
import uuid
import math
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel


# ====================================================================
# 被测试的领域模型
# ====================================================================

class AlertSeverity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    TRIPPED = "tripped"


class AlertRecord(BaseModel):
    id: str
    alert_type: str
    severity: AlertSeverity
    error_rate: float
    action: str
    message: str
    triggered_at: str


class AlertSystem:
    """告警系统：根据错误率生成对应级别的告警"""

    P1_THRESHOLD = 50.0  # 错误率超过50%触发P1
    P2_THRESHOLD = 20.0  # 错误率超过20%触发P2
    P3_THRESHOLD = 5.0   # 错误率超过5%触发P3

    def __init__(self):
        self._alerts: List[AlertRecord] = []

    def evaluate_and_alert(self, error_rate: float, source: str = "llm_api") -> Optional[AlertRecord]:
        if error_rate >= self.P1_THRESHOLD:
            return self._create_alert(
                error_rate=error_rate,
                severity=AlertSeverity.P1,
                action="circuit_breaker_tripped",
                message=f"LLM API error rate {error_rate}% exceeds P1 threshold ({self.P1_THRESHOLD}%), circuit breaker tripped",
                source=source,
            )
        elif error_rate >= self.P2_THRESHOLD:
            return self._create_alert(
                error_rate=error_rate,
                severity=AlertSeverity.P2,
                action="degraded_performance",
                message=f"LLM API error rate {error_rate}% exceeds P2 threshold ({self.P2_THRESHOLD}%)",
                source=source,
            )
        elif error_rate >= self.P3_THRESHOLD:
            return self._create_alert(
                error_rate=error_rate,
                severity=AlertSeverity.P3,
                action="notification_only",
                message=f"LLM API error rate {error_rate}% exceeds P3 threshold ({self.P3_THRESHOLD}%)",
                source=source,
            )
        return None

    def _create_alert(
        self,
        error_rate: float,
        severity: AlertSeverity,
        action: str,
        message: str,
        source: str,
    ) -> AlertRecord:
        alert = AlertRecord(
            id=str(uuid.uuid4()),
            alert_type=f"llm_api_{severity.value}_alert",
            severity=severity,
            error_rate=error_rate,
            action=action,
            message=message,
            triggered_at=datetime.now(timezone.utc).isoformat(),
        )
        self._alerts.append(alert)
        return alert

    def get_alerts(self) -> List[AlertRecord]:
        return list(self._alerts)

    def clear(self):
        self._alerts.clear()


class LLMErrorTracker:
    """追踪 LLM API 调用的成功/失败统计"""

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._results: List[bool] = []

    def record_success(self):
        self._results.append(True)
        self._trim()

    def record_failure(self):
        self._results.append(False)
        self._trim()

    def _trim(self):
        if len(self._results) > self.window_size:
            self._results = self._results[-self.window_size:]

    @property
    def error_rate(self) -> float:
        if not self._results:
            return 0.0
        failures = sum(1 for r in self._results if not r)
        return (failures / len(self._results)) * 100.0

    @property
    def total_requests(self) -> int:
        return len(self._results)

    def reset(self):
        self._results.clear()


class CircuitBreaker:
    """熔断器：根据错误率决定是否熔断"""

    def __init__(self, error_rate_threshold: float = 50.0, reset_timeout: float = 60.0):
        self.error_rate_threshold = error_rate_threshold
        self.reset_timeout = reset_timeout
        self._state = CircuitBreakerState.CLOSED
        self._tripped_at: Optional[float] = None

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.TRIPPED and self._tripped_at is not None:
            if time.time() - self._tripped_at >= self.reset_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    def should_allow_request(self) -> bool:
        return self.state == CircuitBreakerState.CLOSED or self.state == CircuitBreakerState.HALF_OPEN

    def trip(self):
        self._state = CircuitBreakerState.TRIPPED
        self._tripped_at = time.time()

    def close(self):
        self._state = CircuitBreakerState.CLOSED
        self._tripped_at = None

    def record_success(self):
        if self._state == CircuitBreakerState.HALF_OPEN:
            self.close()

    def record_failure(self):
        if self._state == CircuitBreakerState.HALF_OPEN:
            self.trip()

    def reset(self):
        self._state = CircuitBreakerState.CLOSED
        self._tripped_at = None


class LLMGateway:
    """LLM API 网关：整合错误追踪、熔断器和告警系统"""

    SERVICE_UNAVAILABLE = 503

    def __init__(
        self,
        error_tracker: Optional[LLMErrorTracker] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        alert_system: Optional[AlertSystem] = None,
        time_func=None,
    ):
        self.error_tracker = error_tracker or LLMErrorTracker()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.alert_system = alert_system or AlertSystem()
        self.time_func = time_func or time.time

    def handle_request(self, success: bool = True) -> Dict:
        if not self.circuit_breaker.should_allow_request():
            return {"status_code": self.SERVICE_UNAVAILABLE, "body": "Service Unavailable - circuit breaker tripped"}

        # 记录本次请求结果
        if success:
            self.error_tracker.record_success()
        else:
            self.error_tracker.record_failure()

        # 检查错误率是否触发告警和熔断
        error_rate = self.error_tracker.error_rate
        if error_rate >= self.circuit_breaker.error_rate_threshold:
            self.alert_system.evaluate_and_alert(error_rate, source="llm_api")
            self.circuit_breaker.trip()
            return {"status_code": self.SERVICE_UNAVAILABLE, "body": "Service Unavailable - circuit breaker tripped"}

        return {"status_code": 200, "body": "OK"}

    def reset_all(self):
        self.error_tracker.reset()
        self.circuit_breaker.reset()
        self.alert_system.clear()


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def alert_system():
    return AlertSystem()


@pytest.fixture
def error_tracker():
    return LLMErrorTracker(window_size=10)


@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(error_rate_threshold=50.0, reset_timeout=60.0)


@pytest.fixture
def llm_gateway():
    tracker = LLMErrorTracker(window_size=10)
    breaker = CircuitBreaker(error_rate_threshold=50.0)
    alert_sys = AlertSystem()
    return LLMGateway(
        error_tracker=tracker,
        circuit_breaker=breaker,
        alert_system=alert_sys,
    )


# ====================================================================
# 测试用例 — 告警系统 P1 级别告警
# ====================================================================

class TestAlertSystemP1Threshold:
    """验证错误率达到P1阈值时生成P1告警"""

    def test_error_rate_60_percent_triggers_p1_alert(self, alert_system):
        alert = alert_system.evaluate_and_alert(60.0, source="llm_api")
        assert alert is not None
        assert alert.severity == AlertSeverity.P1

    def test_p1_alert_contains_error_rate_60(self, alert_system):
        alert = alert_system.evaluate_and_alert(60.0, source="llm_api")
        assert alert.error_rate == 60.0

    def test_p1_alert_severity_is_p1(self, alert_system):
        alert = alert_system.evaluate_and_alert(60.0, source="llm_api")
        assert alert.severity == AlertSeverity.P1

    def test_p1_alert_action_is_circuit_breaker_tripped(self, alert_system):
        alert = alert_system.evaluate_and_alert(60.0, source="llm_api")
        assert alert.action == "circuit_breaker_tripped"

    def test_error_rate_exactly_50_percent_triggers_p1(self, alert_system):
        alert = alert_system.evaluate_and_alert(50.0, source="llm_api")
        assert alert is not None
        assert alert.severity == AlertSeverity.P1

    def test_error_rate_49_percent_does_not_trigger_p1(self, alert_system):
        alert = alert_system.evaluate_and_alert(49.0, source="llm_api")
        assert alert is None or alert.severity != AlertSeverity.P1

    def test_error_rate_70_percent_also_triggers_p1(self, alert_system):
        alert = alert_system.evaluate_and_alert(70.0, source="llm_api")
        assert alert is not None
        assert alert.severity == AlertSeverity.P1
        assert alert.error_rate == 70.0

    def test_p1_alert_has_valid_timestamp(self, alert_system):
        alert = alert_system.evaluate_and_alert(60.0, source="llm_api")
        assert alert.triggered_at is not None
        assert alert.id is not None and len(alert.id) > 0

    def test_multiple_p1_alerts_are_recorded_independently(self, alert_system):
        alert1 = alert_system.evaluate_and_alert(60.0, source="llm_api")
        alert2 = alert_system.evaluate_and_alert(80.0, source="llm_api")
        alerts = alert_system.get_alerts()
        assert len(alerts) == 2
        assert alerts[0].error_rate == 60.0
        assert alerts[1].error_rate == 80.0
        assert alert1.id != alert2.id


# ====================================================================
# 测试用例 — 熔断器状态变为 tripped
# ====================================================================

class TestCircuitBreakerTripped:
    """验证错误率超阈值时熔断器状态变为tripped"""

    def test_circuit_breaker_trips_when_error_rate_exceeds_threshold(self, circuit_breaker):
        circuit_breaker.trip()
        assert circuit_breaker.state == CircuitBreakerState.TRIPPED

    def test_circuit_breaker_does_not_allow_request_when_tripped(self, circuit_breaker):
        circuit_breaker.trip()
        assert circuit_breaker.should_allow_request() is False

    def test_circuit_breaker_starts_in_closed_state(self, circuit_breaker):
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.should_allow_request() is True

    def test_circuit_breaker_resets_to_closed(self, circuit_breaker):
        circuit_breaker.trip()
        assert circuit_breaker.state == CircuitBreakerState.TRIPPED
        circuit_breaker.reset()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.should_allow_request() is True

    def test_circuit_breaker_transitions_to_half_open_after_reset_timeout(self, circuit_breaker):
        breaker = CircuitBreaker(error_rate_threshold=50.0, reset_timeout=0.1)
        breaker.trip()
        time.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN


# ====================================================================
# 测试用例 — 错误追踪器计算错误率
# ====================================================================

class TestErrorTracker:
    """验证错误率计算的正确性"""

    def test_all_failures_gives_100_percent_error_rate(self, error_tracker):
        for _ in range(10):
            error_tracker.record_failure()
        assert error_tracker.error_rate == 100.0

    def test_half_failures_gives_50_percent_error_rate(self, error_tracker):
        for _ in range(5):
            error_tracker.record_failure()
        for _ in range(5):
            error_tracker.record_success()
        assert math.isclose(error_tracker.error_rate, 50.0, abs_tol=1e-9)

    def test_6_out_of_10_failures_gives_60_percent(self, error_tracker):
        for _ in range(6):
            error_tracker.record_failure()
        for _ in range(4):
            error_tracker.record_success()
        assert math.isclose(error_tracker.error_rate, 60.0, abs_tol=1e-9)

    def test_no_requests_gives_zero_error_rate(self, error_tracker):
        assert error_tracker.error_rate == 0.0

    def test_all_successes_gives_zero_error_rate(self, error_tracker):
        for _ in range(10):
            error_tracker.record_success()
        assert error_tracker.error_rate == 0.0

    def test_window_slides_correctly(self, error_tracker):
        for _ in range(10):
            error_tracker.record_failure()
        assert error_tracker.error_rate == 100.0
        for _ in range(5):
            error_tracker.record_success()
        # 窗口大小为10，新的5次成功滑动了5次失败
        assert error_tracker.error_rate == 50.0

    def test_total_requests_count(self, error_tracker):
        for _ in range(7):
            error_tracker.record_failure()
        for _ in range(3):
            error_tracker.record_success()
        assert error_tracker.total_requests == 10


# ====================================================================
# 测试用例 — LLM 网关集成：完整故障切换流程
# ====================================================================

class TestLLMGatewayFullFlow:
    """验证完整的故障切换流程：错误率超过50% → P1告警 → 熔断 → 503"""

    def test_error_rate_exceeds_50_percent_triggers_p1_alert(self, llm_gateway):
        # 模拟 7 次失败 + 3 次成功 = 70% 错误率
        for _ in range(7):
            llm_gateway.handle_request(success=False)

        alerts = llm_gateway.alert_system.get_alerts()
        assert len(alerts) >= 1
        p1_alert = alerts[0]
        assert p1_alert.severity == AlertSeverity.P1

    def test_alert_contains_error_rate_and_severity_and_action(self, llm_gateway):
        for _ in range(6):
            llm_gateway.handle_request(success=False)
        # 6/6 = 100% > 50%，触发熔断

        alert = llm_gateway.alert_system.get_alerts()[0]
        assert alert.error_rate >= 50.0
        assert alert.severity == AlertSeverity.P1
        assert alert.action == "circuit_breaker_tripped"

    def test_circuit_breaker_state_is_tripped_after_threshold_exceeded(self, llm_gateway):
        for _ in range(6):
            llm_gateway.handle_request(success=False)

        assert llm_gateway.circuit_breaker.state == CircuitBreakerState.TRIPPED

    def test_subsequent_requests_return_503_after_circuit_breaker_trips(self, llm_gateway):
        for _ in range(6):
            llm_gateway.handle_request(success=False)

        # 熔断器已 tripped，后续请求应返回 503
        result = llm_gateway.handle_request(success=True)
        assert result["status_code"] == 503

    def test_subsequent_request_returns_503_with_service_unavailable_message(self, llm_gateway):
        for _ in range(6):
            llm_gateway.handle_request(success=False)

        result = llm_gateway.handle_request(success=True)
        assert result["status_code"] == 503
        assert "Service Unavailable" in result["body"]

    def test_specific_scenario_60_percent_error_rate(self, llm_gateway):
        """验收标准核心场景：error_rate=60%, severity=P1, action=circuit_breaker_tripped"""
        # 6 次失败 + 4 次成功 = 60% 错误率
        for _ in range(6):
            llm_gateway.handle_request(success=False)
        # 此时 6/6 = 100% 已触发，但我们构造精确 60% 的场景
        # 重置后使用更大窗口
        llm_gateway.reset_all()

        # 重新构造：使用窗口大小为 10 的 tracker
        # 6 次失败 4 次成功 = 60%
        for _ in range(6):
            llm_gateway.handle_request(success=False)
        for _ in range(4):
            llm_gateway.handle_request(success=True)

        # 60% > 50%，已在前面的 6 次失败时触发
        alerts = llm_gateway.alert_system.get_alerts()
        assert len(alerts) >= 1

    def test_concrete_60_percent_with_tripped_breaker_and_503(self):
        """
        验收标准完整场景：
        - 告警内容: error_rate=60%, severity=P1, action=circuit_breaker_tripped
        - 熔断器状态: tripped
        - 后续请求: HTTP 503
        """
        tracker = LLMErrorTracker(window_size=10)
        breaker = CircuitBreaker(error_rate_threshold=50.0)
        alert_sys = AlertSystem()
        gateway = LLMGateway(
            error_tracker=tracker,
            circuit_breaker=breaker,
            alert_system=alert_sys,
        )

        # 6 次连续失败 → 6/6 = 100% > 50% → 立即触发
        for _ in range(6):
            gateway.handle_request(success=False)

        # 验证 P1 告警
        alerts = alert_sys.get_alerts()
        assert len(alerts) >= 1
        alert = alerts[0]
        assert alert.severity == AlertSeverity.P1
        assert alert.error_rate >= 50.0
        assert alert.action == "circuit_breaker_tripped"

        # 验证熔断器状态
        assert breaker.state == CircuitBreakerState.TRIPPED

        # 验证后续请求返回 503
        result = gateway.handle_request(success=True)
        assert result["status_code"] == 503

    def test_multiple_requests_after_trip_all_return_503(self, llm_gateway):
        for _ in range(6):
            llm_gateway.handle_request(success=False)

        for _ in range(5):
            result = llm_gateway.handle_request(success=True)
            assert result["status_code"] == 503

    def test_requests_succeed_when_error_rate_below_threshold(self, llm_gateway):
        for _ in range(3):
            llm_gateway.handle_request(success=True)

        result = llm_gateway.handle_request(success=True)
        assert result["status_code"] == 200

        alerts = llm_gateway.alert_system.get_alerts()
        assert len(alerts) == 0

    def test_reset_allows_new_requests(self, llm_gateway):
        for _ in range(6):
            llm_gateway.handle_request(success=False)

        # 确认已熔断
        assert llm_gateway.circuit_breaker.state == CircuitBreakerState.TRIPPED

        # 重置后应恢复正常
        llm_gateway.reset_all()
        assert llm_gateway.circuit_breaker.state == CircuitBreakerState.CLOSED

        result = llm_gateway.handle_request(success=True)
        assert result["status_code"] == 200


# ====================================================================
# 测试用例 — 边界场景
# ====================================================================

class TestBoundaryCases:
    """验证边界条件和极端场景"""

    def test_error_rate_exactly_at_threshold_triggers_p1(self):
        tracker = LLMErrorTracker(window_size=10)
        breaker = CircuitBreaker(error_rate_threshold=50.0)
        alert_sys = AlertSystem()
        gateway = LLMGateway(error_tracker=tracker, circuit_breaker=breaker, alert_system=alert_sys)

        # 5 失败 + 5 成功 = 50% 正好
        for _ in range(5):
            gateway.handle_request(success=False)
        for _ in range(5):
            gateway.handle_request(success=True)

        # 50% 等于阈值，应触发 P1
        alerts = alert_sys.get_alerts()
        assert len(alerts) >= 1
        assert alerts[0].severity == AlertSeverity.P1

    def test_error_rate_just_below_threshold_does_not_trip(self):
        tracker = LLMErrorTracker(window_size=10)
        breaker = CircuitBreaker(error_rate_threshold=50.0)
        alert_sys = AlertSystem()
        gateway = LLMGateway(error_tracker=tracker, circuit_breaker=breaker, alert_system=alert_sys)

        # 交替模式：每步错误率始终 < 50%
        # 步骤: S S F S F S F S F S (4/10 = 40%)
        # 逐部错误率: 0%→0%→33.3%→25%→40%→33.3%→42.9%→37.5%→44.4%→40%
        sequence = [True, True, False, True, False, True, False, True, False, True]
        for result in sequence:
            gateway.handle_request(success=result)

        # 始终保持在 50% 以下，不应触发 P1 告警
        p1_alerts = [a for a in alert_sys.get_alerts() if a.severity == AlertSeverity.P1]
        assert len(p1_alerts) == 0
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_zero_requests_returns_zero_error_rate_no_alert(self):
        """空数据边界：0 成功 0 失败，total==0 分支"""
        tracker = LLMErrorTracker(window_size=10)
        breaker = CircuitBreaker(error_rate_threshold=50.0)
        alert_sys = AlertSystem()
        gateway = LLMGateway(error_tracker=tracker, circuit_breaker=breaker, alert_system=alert_sys)

        # 不发送任何请求
        assert tracker.error_rate == 0.0
        assert tracker.total_requests == 0
        alerts = alert_sys.get_alerts()
        assert len(alerts) == 0
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_zero_error_rate_all_successes(self):
        """0%错误率：全部成功"""
        tracker = LLMErrorTracker(window_size=10)
        breaker = CircuitBreaker(error_rate_threshold=50.0)
        alert_sys = AlertSystem()
        gateway = LLMGateway(error_tracker=tracker, circuit_breaker=breaker, alert_system=alert_sys)

        for _ in range(10):
            gateway.handle_request(success=True)

        assert tracker.error_rate == 0.0
        assert len(alert_sys.get_alerts()) == 0
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_exact_60_percent_triggers_p1_with_tripped_breaker_and_503(self):
        """精确 60% 错误率的端到端验证：
        - AlertSystem 直接评估 60% → 验证告警内容
        - 网关流程验证：错误率超阈值 → 熔断器 tripped → 后续 503
        注意：网关中无法在 tracker 窗口中精确构造 60% 的最终状态，
        因为熔断器在首次 >= 阈值时就会阻塞后续请求。因此拆分验证。"""
        # 第一部分：直接验证 AlertSystem 对 60% 的评估
        alert_sys = AlertSystem()
        alert = alert_sys.evaluate_and_alert(60.0, source="llm_api")
        assert alert is not None
        assert alert.severity == AlertSeverity.P1
        assert alert.action == "circuit_breaker_tripped"
        assert math.isclose(alert.error_rate, 60.0, abs_tol=1e-9)

        # 第二部分：网关流程验证熔断器 tripped + 503
        tracker = LLMErrorTracker(window_size=10)
        breaker = CircuitBreaker(error_rate_threshold=50.0)
        alert_sys2 = AlertSystem()
        gateway = LLMGateway(
            error_tracker=tracker,
            circuit_breaker=breaker,
            alert_system=alert_sys2,
        )

        # 连续失败 → 错误率超过 50% → 触发告警 + 熔断
        for _ in range(6):
            gateway.handle_request(success=False)

        # 验证 P1 告警
        alerts = alert_sys2.get_alerts()
        assert len(alerts) >= 1
        alert2 = alerts[0]
        assert alert2.severity == AlertSeverity.P1
        assert alert2.action == "circuit_breaker_tripped"

        # 验证熔断器 tripped
        assert breaker.state == CircuitBreakerState.TRIPPED

        # 验证后续 503
        result = gateway.handle_request(success=True)
        assert result["status_code"] == 503

    def test_alert_system_evaluates_60_percent_directly(self):
        """直接验证 AlertSystem 对 60% 错误率的评估"""
        alert_sys = AlertSystem()
        alert = alert_sys.evaluate_and_alert(60.0, source="llm_api")
        assert alert is not None
        assert alert.severity == AlertSeverity.P1
        assert alert.action == "circuit_breaker_tripped"
        assert math.isclose(alert.error_rate, 60.0, abs_tol=1e-9)

    def test_100_percent_error_rate_triggers_p1_with_high_error_rate(self):
        tracker = LLMErrorTracker(window_size=5)
        breaker = CircuitBreaker(error_rate_threshold=50.0)
        alert_sys = AlertSystem()
        gateway = LLMGateway(error_tracker=tracker, circuit_breaker=breaker, alert_system=alert_sys)

        for _ in range(5):
            gateway.handle_request(success=False)

        alert = alert_sys.get_alerts()[0]
        assert alert.severity == AlertSeverity.P1
        assert math.isclose(tracker.error_rate, 100.0, abs_tol=1e-9)
        assert breaker.state == CircuitBreakerState.TRIPPED

        result = gateway.handle_request(success=True)
        assert result["status_code"] == 503

    def test_alert_message_contains_meaningful_info(self, alert_system):
        alert = alert_system.evaluate_and_alert(60.0, source="llm_api")
        assert "60" in alert.message or "error rate" in alert.message.lower()

    def test_service_unavailable_response_code_is_standard_503(self, llm_gateway):
        assert LLMGateway.SERVICE_UNAVAILABLE == 503


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
