import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


# ====================================================================
# 领域模型 — Token 配额告警
# ====================================================================

class AlertLevel(str, Enum):
    """告警级别"""
    P0 = "P0"  # 严重 — SMS + 电话 + 邮件
    P1 = "P1"  # 紧急 — SMS + 邮件
    P2 = "P2"  # 警告 — 邮件 + 站内信
    P3 = "P3"  # 提示 — 站内信


@dataclass
class QuotaAlertRecord:
    """Token 配额告警记录"""
    alert_id: str
    level: AlertLevel
    usage: int
    quota: int
    usage_percent: float
    threshold_percent: float
    triggered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "level": self.level.value,
            "usage": self.usage,
            "quota": self.quota,
            "usage_percent": self.usage_percent,
            "threshold_percent": self.threshold_percent,
            "triggered_at": self.triggered_at,
        }


class NotificationDispatcher:
    """通知分发器：根据告警级别路由到不同通知渠道"""

    def __init__(self):
        self.sent_notifications: List[Dict] = []

    def dispatch(self, alert: QuotaAlertRecord):
        """根据告警级别分派通知"""
        notification = {
            "alert_id": alert.alert_id,
            "level": alert.level.value,
            "channels": [],
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        if alert.level == AlertLevel.P0:
            notification["channels"] = ["sms", "phone_call", "email"]
        elif alert.level == AlertLevel.P1:
            notification["channels"] = ["sms", "email"]
        elif alert.level == AlertLevel.P2:
            notification["channels"] = ["email", "in_app"]
        elif alert.level == AlertLevel.P3:
            notification["channels"] = ["in_app"]

        self.sent_notifications.append(notification)
        return notification

    def get_notifications_by_level(self, level: AlertLevel) -> List[Dict]:
        return [n for n in self.sent_notifications if n["level"] == level.value]

    def reset(self):
        self.sent_notifications.clear()


class TokenQuotaManager:
    """Token 配额管理器：跟踪消耗、判断阈值、触发告警"""

    # 告警阈值定义（百分比）
    P3_THRESHOLD = 50.0   # 50% — 提示
    P2_THRESHOLD = 70.0   # 70% — 警告
    P1_THRESHOLD = 90.0   # 90% — 紧急
    P0_THRESHOLD = 100.0  # 100% — 严重（熔断）

    def __init__(self, daily_quota: int, notification_dispatcher: Optional[NotificationDispatcher] = None):
        self.daily_quota = daily_quota
        self._usage = 0
        self.dispatcher = notification_dispatcher or NotificationDispatcher()
        self._alerts: List[QuotaAlertRecord] = []
        # 各级别是否已触发（防止重复告警）
        self._p3_triggered = False
        self._p2_triggered = False
        self._p1_triggered = False
        self._p0_triggered = False

    @property
    def usage(self) -> int:
        return self._usage

    @property
    def remaining(self) -> int:
        return max(0, self.daily_quota - self._usage)

    @property
    def usage_percent(self) -> float:
        if self.daily_quota == 0:
            return 0.0
        return round(self._usage / self.daily_quota * 100, 2)

    @property
    def is_exhausted(self) -> bool:
        return self._usage >= self.daily_quota

    @property
    def alerts(self) -> List[QuotaAlertRecord]:
        return list(self._alerts)

    def consume(self, tokens: int) -> bool:
        """消耗 token，返回是否允许（未超限）"""
        if self._usage + tokens > self.daily_quota:
            return False
        self._usage += tokens
        self._check_thresholds()
        return True

    def force_consume(self, tokens: int):
        """强制消耗（不受限额限制，用于模拟场景）"""
        self._usage += tokens
        self._check_thresholds()

    def _check_thresholds(self):
        """检查是否跨越告警阈值（按从低到高顺序，全部匹配的都触发）"""
        percent = self.usage_percent

        # P3 — 50%
        if percent >= self.P3_THRESHOLD and not self._p3_triggered:
            self._p3_triggered = True
            alert = self._create_alert(AlertLevel.P3, self.P3_THRESHOLD, percent)
            self.dispatcher.dispatch(alert)

        # P2 — 70%
        if percent >= self.P2_THRESHOLD and not self._p2_triggered:
            self._p2_triggered = True
            alert = self._create_alert(AlertLevel.P2, self.P2_THRESHOLD, percent)
            self.dispatcher.dispatch(alert)

        # P1 — 90%
        if percent >= self.P1_THRESHOLD and not self._p1_triggered:
            self._p1_triggered = True
            alert = self._create_alert(AlertLevel.P1, self.P1_THRESHOLD, percent)
            self.dispatcher.dispatch(alert)

        # P0 — 100%（耗尽）
        if percent >= self.P0_THRESHOLD and not self._p0_triggered:
            self._p0_triggered = True
            alert = self._create_alert(AlertLevel.P0, self.P0_THRESHOLD, percent)
            self.dispatcher.dispatch(alert)

    def _create_alert(self, level: AlertLevel, threshold_percent: float, usage_percent: float) -> QuotaAlertRecord:
        alert = QuotaAlertRecord(
            alert_id=str(uuid.uuid4()),
            level=level,
            usage=self._usage,
            quota=self.daily_quota,
            usage_percent=usage_percent,
            threshold_percent=threshold_percent,
        )
        self._alerts.append(alert)
        return alert

    def reset(self):
        """重置（如新的一天）"""
        self._usage = 0
        self._p3_triggered = False
        self._p2_triggered = False
        self._p1_triggered = False
        self._p0_triggered = False
        self._alerts.clear()


# ====================================================================
# FastAPI 应用
# ====================================================================

app = FastAPI(title="Token Quota Alert API")

_system_manager: Optional[TokenQuotaManager] = None
_system_dispatcher: Optional[NotificationDispatcher] = None


def init_system(daily_quota: int = 1000000):
    global _system_manager, _system_dispatcher
    _system_dispatcher = NotificationDispatcher()
    _system_manager = TokenQuotaManager(daily_quota, _system_dispatcher)
    return _system_manager, _system_dispatcher


@app.post("/v1/chat/completions")
async def chat_completion(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")

    if _system_manager is None or _system_manager.is_exhausted:
        return JSONResponse(
            status_code=429,
            content={"error": "token_quota_exceeded"},
        )

    tokens_per_call = 100
    ok = _system_manager.consume(tokens_per_call)
    if not ok:
        return JSONResponse(
            status_code=429,
            content={"error": "token_quota_exceeded"},
        )

    return {
        "choices": [{"message": {"content": "OK"}}],
        "usage": {
            "total_tokens": tokens_per_call,
            "remaining_tokens": _system_manager.remaining,
        },
    }


@app.get("/v1/token-quota/status")
async def token_quota_status(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")

    if _system_manager is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    return {
        "usage": _system_manager.usage,
        "quota": _system_manager.daily_quota,
        "remaining": _system_manager.remaining,
        "usage_percent": _system_manager.usage_percent,
        "is_exhausted": _system_manager.is_exhausted,
        "alert_count": len(_system_manager.alerts),
    }


@app.get("/v1/token-quota/alerts")
async def token_quota_alerts(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")

    if _system_manager is None:
        return {"alerts": []}

    return {"alerts": [a.to_dict() for a in _system_manager.alerts]}


@app.post("/v1/token-quota/admin-reset")
async def admin_reset(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    if _system_manager is not None:
        _system_manager.reset()
    if _system_dispatcher is not None:
        _system_dispatcher.reset()
    return {"status": "reset"}


client = TestClient(app)


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture(autouse=True)
def reset_system():
    init_system(daily_quota=1000)
    yield


@pytest.fixture
def manager():
    return _system_manager


@pytest.fixture
def dispatcher():
    return _system_dispatcher


# ====================================================================
# 测试 — 告警阈值触发
# ====================================================================

class TestQuotaAlertThresholdTrigger:
    """Token 消耗达到配额阈值时触发告警"""

    def test_no_alert_below_threshold(self, manager, dispatcher):
        """消耗低于最低阈值（50%）时不触发任何告警"""
        manager.consume(499)  # 49.9%
        assert len(manager.alerts) == 0
        assert len(dispatcher.sent_notifications) == 0

    def test_p3_alert_triggered_at_50_percent(self, manager, dispatcher):
        """消耗达到 50% 时触发 P3 级别告警"""
        manager.consume(500)  # 50%
        assert len(manager.alerts) == 1
        alert = manager.alerts[0]
        assert alert.level == AlertLevel.P3
        assert alert.threshold_percent == 50.0
        assert alert.usage_percent == 50.0

    def test_p2_alert_triggered_at_70_percent(self, manager, dispatcher):
        """消耗达到 70% 时触发 P2 级别告警"""
        manager.consume(700)  # 70%
        # 先触发 P3(50%)，再触发 P2(70%)
        alerts = manager.alerts
        assert len(alerts) == 2
        assert alerts[0].level == AlertLevel.P3
        assert alerts[1].level == AlertLevel.P2
        assert alerts[1].threshold_percent == 70.0

    def test_p1_alert_triggered_at_90_percent(self, manager, dispatcher):
        """消耗达到 90% 时触发 P1 级别告警"""
        manager.consume(900)  # 90%
        alerts = manager.alerts
        assert len(alerts) == 3
        assert alerts[0].level == AlertLevel.P3
        assert alerts[1].level == AlertLevel.P2
        assert alerts[2].level == AlertLevel.P1
        assert alerts[2].threshold_percent == 90.0

    def test_p0_alert_triggered_at_100_percent(self, manager, dispatcher):
        """消耗达到 100% 时触发 P0 级别告警"""
        manager.force_consume(1000)  # 100%
        alerts = manager.alerts
        assert len(alerts) == 4
        assert alerts[3].level == AlertLevel.P0
        assert alerts[3].threshold_percent == 100.0
        assert alerts[3].usage_percent == 100.0

    def test_incremental_consume_triggers_alerts_sequentially(self, manager, dispatcher):
        """分批消耗 token，按顺序触发各级别告警"""
        manager.consume(250)   # 25% — 无告警
        assert len(manager.alerts) == 0

        manager.consume(250)   # 50% — P3
        assert len(manager.alerts) == 1
        assert manager.alerts[-1].level == AlertLevel.P3

        manager.consume(200)   # 70% — P2
        assert len(manager.alerts) == 2
        assert manager.alerts[-1].level == AlertLevel.P2

        manager.consume(200)   # 90% — P1
        assert len(manager.alerts) == 3
        assert manager.alerts[-1].level == AlertLevel.P1

        manager.consume(100)   # 100% — P0
        assert len(manager.alerts) == 4
        assert manager.alerts[-1].level == AlertLevel.P0


# ====================================================================
# 测试 — 通知方式符合级别定义
# ====================================================================

class TestNotificationChannelsByLevel:
    """通知方式符合级别定义"""

    def test_p3_notification_is_in_app_only(self, manager, dispatcher):
        """P3 级别仅发送站内信通知"""
        manager.consume(500)  # 触发 P3
        notifications = dispatcher.sent_notifications
        assert len(notifications) == 1
        assert notifications[0]["channels"] == ["in_app"]
        assert notifications[0]["level"] == "P3"

    def test_p2_notification_is_email_and_in_app(self, manager, dispatcher):
        """P2 级别发送邮件 + 站内信通知"""
        manager.consume(700)  # 触发 P3 + P2
        p2_notifications = dispatcher.get_notifications_by_level(AlertLevel.P2)
        assert len(p2_notifications) == 1
        assert p2_notifications[0]["channels"] == ["email", "in_app"]
        assert p2_notifications[0]["level"] == "P2"

    def test_p1_notification_is_sms_and_email(self, manager, dispatcher):
        """P1 级别发送 SMS + 邮件通知"""
        manager.consume(900)  # 触发 P3 + P2 + P1
        p1_notifications = dispatcher.get_notifications_by_level(AlertLevel.P1)
        assert len(p1_notifications) == 1
        assert p1_notifications[0]["channels"] == ["sms", "email"]
        assert p1_notifications[0]["level"] == "P1"

    def test_p0_notification_is_sms_phone_and_email(self, manager, dispatcher):
        """P0 级别发送 SMS + 电话 + 邮件通知"""
        manager.force_consume(1000)  # 触发全部
        p0_notifications = dispatcher.get_notifications_by_level(AlertLevel.P0)
        assert len(p0_notifications) == 1
        assert p0_notifications[0]["channels"] == ["sms", "phone_call", "email"]
        assert p0_notifications[0]["level"] == "P0"

    def test_all_level_notifications_have_unique_alert_ids(self, manager, dispatcher):
        """各告警级别的通知记录具有唯一的 alert_id"""
        manager.force_consume(1000)
        alert_ids = [n["alert_id"] for n in dispatcher.sent_notifications]
        assert len(alert_ids) == len(set(alert_ids)), "每个通知应有唯一 alert_id"

    def test_notification_sent_at_is_valid_isoformat(self, manager, dispatcher):
        """通知记录中的 sent_at 是有效的 ISO 格式时间"""
        manager.consume(500)
        notification = dispatcher.sent_notifications[0]
        sent_at = notification["sent_at"]
        parsed = datetime.fromisoformat(sent_at)
        assert parsed.tzinfo is not None, "sent_at 应包含时区信息"


# ====================================================================
# 测试 — 告警去重
# ====================================================================

class TestAlertDeduplication:
    """告警去重：同一级别在同一周期内只触发一次"""

    def test_p3_not_triggered_twice(self, manager, dispatcher):
        """P3 告警在同一周期内不会重复触发"""
        manager.consume(250)  # 25%
        manager.consume(250)  # 50% — P3 触发
        assert len(manager.alerts) == 1

        manager.consume(10)   # 51% — 仍在 P3 范围内
        assert len(manager.alerts) == 1  # 不应新增

    def test_each_level_triggers_once(self, manager, dispatcher):
        """各级别告警各只触发一次"""
        manager.force_consume(1000)
        levels = [a.level for a in manager.alerts]
        assert levels == [AlertLevel.P3, AlertLevel.P2, AlertLevel.P1, AlertLevel.P0]
        assert len(levels) == len(set(levels)), "不应有重复级别"

    def test_notification_count_equals_alert_count(self, manager, dispatcher):
        """通知数量等于告警数量（一对一映射）"""
        manager.force_consume(1000)
        assert len(dispatcher.sent_notifications) == len(manager.alerts)

    def test_no_notification_for_non_triggered_levels(self, manager, dispatcher):
        """未达阈值时不会发送对应级别的通知"""
        manager.consume(400)  # 40% — 未达任何阈值
        assert len(dispatcher.sent_notifications) == 0

    def test_partial_thresholds_no_extra_notifications(self, manager, dispatcher):
        """仅达到 P2 阈值时不会发送 P1/P0 通知"""
        manager.consume(700)  # 70% — 触发 P3 + P2
        p1_notifications = dispatcher.get_notifications_by_level(AlertLevel.P1)
        p0_notifications = dispatcher.get_notifications_by_level(AlertLevel.P0)
        assert len(p1_notifications) == 0
        assert len(p0_notifications) == 0


# ====================================================================
# 测试 — 边界值
# ====================================================================

class TestBoundaryValues:
    """边界值测试"""

    def test_exactly_at_p3_threshold_triggers(self, manager, dispatcher):
        """恰好 50% 时触发 P3 告警"""
        manager.consume(500)
        assert len(manager.alerts) == 1
        assert manager.alerts[0].level == AlertLevel.P3

    def test_just_below_p3_threshold_no_alert(self, manager, dispatcher):
        """略低于 50% 时不触发 P3 告警"""
        manager.consume(499)
        assert len(manager.alerts) == 0

    def test_exactly_at_p2_threshold_triggers(self, manager, dispatcher):
        """恰好 70% 时触发 P2 告警"""
        manager.consume(700)
        p2_alerts = [a for a in manager.alerts if a.level == AlertLevel.P2]
        assert len(p2_alerts) == 1

    def test_just_below_p2_threshold_no_p2(self, manager, dispatcher):
        """略低于 70% 时不触发 P2 告警"""
        manager.consume(699)
        p2_alerts = [a for a in manager.alerts if a.level == AlertLevel.P2]
        assert len(p2_alerts) == 0

    def test_exactly_at_p1_threshold_triggers(self, manager, dispatcher):
        """恰好 90% 时触发 P1 告警"""
        manager.consume(900)
        p1_alerts = [a for a in manager.alerts if a.level == AlertLevel.P1]
        assert len(p1_alerts) == 1

    def test_exactly_at_p0_threshold_triggers(self, manager, dispatcher):
        """恰好 100% 时触发 P0 告警"""
        manager.force_consume(1000)
        p0_alerts = [a for a in manager.alerts if a.level == AlertLevel.P0]
        assert len(p0_alerts) == 1

    def test_zero_quota_no_division_error(self):
        """配额为 0 时不产生除零错误"""
        manager = TokenQuotaManager(daily_quota=0)
        assert manager.usage_percent == 0.0

    def test_usage_percent_rounding(self, manager, dispatcher):
        """usage_percent 正确舍入到小数点后两位"""
        manager.consume(333)  # 33.3%
        assert manager.usage_percent == 33.3


# ====================================================================
# 测试 — 配额耗尽后请求被拒绝
# ====================================================================

class TestQuotaExhaustion:
    """配额耗尽后新请求返回 429"""

    def test_consume_returns_false_when_over_quota(self, manager):
        """消耗超过配额时 consume 返回 False"""
        manager.consume(950)
        result = manager.consume(100)
        assert result is False

    def test_consume_allows_exactly_quota(self, manager):
        """恰好等于配额时 consume 返回 True"""
        result = manager.consume(1000)
        assert result is True

    def test_exhausted_flag_is_true(self, manager):
        """配额耗尽时 is_exhausted 为 True"""
        manager.consume(1000)
        assert manager.is_exhausted is True

    def test_remaining_is_zero_when_exhausted(self, manager):
        """配额耗尽时 remaining 为 0"""
        manager.consume(1000)
        assert manager.remaining == 0

    def test_remaining_is_non_negative(self, manager):
        """remaining 始终非负"""
        manager.force_consume(1500)
        assert manager.remaining >= 0


# ====================================================================
# 测试 — HTTP 接口
# ====================================================================

class TestQuotaAlertHTTP:
    """通过 HTTP 接口验证配额告警"""

    def test_chat_completion_returns_200_when_within_quota(self):
        """配额范围内请求返回 200"""
        init_system(daily_quota=10000)
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        assert resp.status_code == 200
        body = resp.json()
        assert "choices" in body
        assert "usage" in body

    def test_chat_completion_returns_429_when_quota_exhausted(self):
        """配额耗尽后请求返回 429"""
        init_system(daily_quota=100)
        resp1 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        assert resp1.status_code == 200  # 消耗 100，达到 100%

        resp2 = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        assert resp2.status_code == 429
        assert resp2.json()["error"] == "token_quota_exceeded"

    def test_status_endpoint_returns_correct_usage(self):
        """状态接口返回正确的用量信息"""
        init_system(daily_quota=1000)
        client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})  # 消耗 100
        resp = client.get("/v1/token-quota/status", headers={"Authorization": "Bearer test"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["usage"] == 100
        assert body["quota"] == 1000
        assert body["remaining"] == 900
        assert body["usage_percent"] == 10.0

    def test_alerts_endpoint_returns_alert_records(self):
        """告警接口返回告警记录"""
        init_system(daily_quota=1000)
        # 消耗到 100% 触发全部告警
        for _ in range(10):
            client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})

        resp = client.get("/v1/token-quota/alerts", headers={"Authorization": "Bearer test"})
        assert resp.status_code == 200
        body = resp.json()
        alerts = body["alerts"]
        assert len(alerts) == 4  # P3 + P2 + P1 + P0
        levels = [a["level"] for a in alerts]
        assert "P3" in levels
        assert "P2" in levels
        assert "P1" in levels
        assert "P0" in levels

    def test_no_auth_returns_401(self):
        """缺少授权头返回 401"""
        resp = client.post("/v1/chat/completions")
        assert resp.status_code == 401

        resp = client.get("/v1/token-quota/status")
        assert resp.status_code == 401

        resp = client.get("/v1/token-quota/alerts")
        assert resp.status_code == 401

    def test_reset_restores_system(self):
        """管理员重置后系统恢复"""
        init_system(daily_quota=100)
        client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        assert resp.status_code == 429

        resp = client.post("/v1/token-quota/admin-reset", headers={"Authorization": "Bearer admin"})
        assert resp.status_code == 200

        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        assert resp.status_code == 200

    def test_response_includes_remaining_tokens(self):
        """响应中包含剩余 token 数量"""
        init_system(daily_quota=1000)
        resp = client.post("/v1/chat/completions", headers={"Authorization": "Bearer test"})
        body = resp.json()
        assert body["usage"]["remaining_tokens"] == 900


# ====================================================================
# 测试 — 完整场景
# ====================================================================

class TestFullScenario:
    """完整场景：从 0 消耗到 100%，验证各级别告警和通知"""

    def test_full_consumption_triggers_all_alerts_and_notifications(self):
        """完整消耗场景：从 0% 到 100%，触发全部级别告警"""
        init_system(daily_quota=1000)

        # 消耗 500 → P3 (50%)
        _system_manager.consume(500)
        assert len(_system_manager.alerts) == 1
        assert _system_manager.alerts[0].level == AlertLevel.P3
        p3_notif = _system_dispatcher.get_notifications_by_level(AlertLevel.P3)
        assert len(p3_notif) == 1
        assert p3_notif[0]["channels"] == ["in_app"]

        # 消耗 200 → P2 (70%)
        _system_manager.consume(200)
        assert len(_system_manager.alerts) == 2
        assert _system_manager.alerts[1].level == AlertLevel.P2
        p2_notif = _system_dispatcher.get_notifications_by_level(AlertLevel.P2)
        assert len(p2_notif) == 1
        assert p2_notif[0]["channels"] == ["email", "in_app"]

        # 消耗 200 → P1 (90%)
        _system_manager.consume(200)
        assert len(_system_manager.alerts) == 3
        assert _system_manager.alerts[2].level == AlertLevel.P1
        p1_notif = _system_dispatcher.get_notifications_by_level(AlertLevel.P1)
        assert len(p1_notif) == 1
        assert p1_notif[0]["channels"] == ["sms", "email"]

        # 消耗 100 → P0 (100%)
        _system_manager.consume(100)
        assert len(_system_manager.alerts) == 4
        assert _system_manager.alerts[3].level == AlertLevel.P0
        p0_notif = _system_dispatcher.get_notifications_by_level(AlertLevel.P0)
        assert len(p0_notif) == 1
        assert p0_notif[0]["channels"] == ["sms", "phone_call", "email"]

        # 验证配额已耗尽
        assert _system_manager.is_exhausted is True
        assert _system_manager.remaining == 0

        # 验证通知总数
        assert len(_system_dispatcher.sent_notifications) == 4

    def test_reset_clears_alerts_and_allows_new_period(self):
        """重置后告警清零，新周期可重新开始"""
        init_system(daily_quota=1000)
        _system_manager.force_consume(1000)  # 触发全部告警
        assert len(_system_manager.alerts) == 4
        assert _system_manager.is_exhausted is True

        _system_manager.reset()
        assert len(_system_manager.alerts) == 0
        assert _system_manager.is_exhausted is False
        assert _system_manager.usage == 0
        assert _system_manager.remaining == 1000

        # 新周期可正常消耗
        result = _system_manager.consume(500)
        assert result is True
        assert _system_manager.usage == 500

    def test_quota_alert_record_to_dict_contains_all_fields(self):
        """告警记录 to_dict 包含所有必需字段"""
        manager = TokenQuotaManager(daily_quota=1000)
        manager.consume(500)  # 触发 P3
        alert = manager.alerts[0]
        d = alert.to_dict()

        expected_keys = {"alert_id", "level", "usage", "quota", "usage_percent", "threshold_percent", "triggered_at"}
        assert set(d.keys()) == expected_keys
        assert d["level"] == "P3"
        assert d["usage"] == 500
        assert d["quota"] == 1000
        assert d["usage_percent"] == 50.0
        assert d["threshold_percent"] == 50.0
        assert d["alert_id"] is not None
        assert d["triggered_at"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
