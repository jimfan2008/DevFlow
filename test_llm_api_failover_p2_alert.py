import uuid
import pytest
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


# ====================================================================
# 领域模型
# ====================================================================

class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class AlertRecord:
    """告警记录"""
    id: str
    service: str
    severity: Severity
    error_rate: float
    message: str
    status: AlertStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ====================================================================
# 告警评估引擎
# ====================================================================

ALERT_THRESHOLDS = {
    Severity.P0: (80.0, float("inf")),
    Severity.P1: (50.0, 80.0),
    Severity.P2: (5.0, 50.0),
    Severity.P3: (0.0, 5.0),
}


def evaluate_llm_api_error_rate(error_rate: float) -> Optional[Severity]:
    """根据 LLM API 错误率评估告警等级"""
    for severity, (low, high) in ALERT_THRESHOLDS.items():
        if low <= error_rate < high:
            return severity
    return None


class AlertRepository:
    """内存告警存储"""

    def __init__(self):
        self._alerts: dict[str, AlertRecord] = {}

    def save(self, record: AlertRecord) -> AlertRecord:
        self._alerts[record.id] = record
        return record

    def find_by_id(self, alert_id: str) -> Optional[AlertRecord]:
        return self._alerts.get(alert_id)

    def find_all(self) -> list[AlertRecord]:
        return list(self._alerts.values())

    def count_by_status(self, status: AlertStatus) -> int:
        return sum(1 for r in self._alerts.values() if r.status == status)

    def clear(self):
        self._alerts.clear()


class LlmApiAlertService:
    """LLM API 错误率告警服务"""

    def __init__(self, repository: AlertRepository):
        self.repository = repository

    def trigger_alert(self, error_rate: float) -> Optional[AlertRecord]:
        """触发告警：评估错误率并写入告警记录"""
        severity = evaluate_llm_api_error_rate(error_rate)
        if severity is None:
            return None

        record = AlertRecord(
            id=str(uuid.uuid4()),
            service="llm_api",
            severity=severity,
            error_rate=round(error_rate, 2),
            message=f"LLM API error rate {error_rate:.1f}% exceeds threshold for {severity.value}",
            status=AlertStatus.NEW,
        )
        return self.repository.save(record)


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def repo():
    repo_instance = AlertRepository()
    yield repo_instance
    repo_instance.clear()


@pytest.fixture
def alert_service(repo):
    return LlmApiAlertService(repository=repo)


# ====================================================================
# 测试用例
# ====================================================================

class TestLlmApiP2AlertTrigger:
    """LLM API 故障切换 P2 告警触发"""

    # ── 基本路径：error_rate=20% 触发 P2 ──

    def test_p2_alert_triggered_at_20_percent_error_rate(self, alert_service, repo):
        record = alert_service.trigger_alert(error_rate=20.0)
        assert record is not None
        assert record.severity == Severity.P2
        assert record.service == "llm_api"
        assert record.error_rate == 20.0

    def test_p2_alert_has_new_status(self, alert_service, repo):
        record = alert_service.trigger_alert(error_rate=20.0)
        assert record is not None
        assert record.status == AlertStatus.NEW

    def test_p2_alert_written_to_repository(self, alert_service, repo):
        record = alert_service.trigger_alert(error_rate=20.0)
        assert record is not None
        stored = repo.find_by_id(record.id)
        assert stored is not None
        assert stored.severity == Severity.P2
        assert stored.service == "llm_api"
        assert stored.status == AlertStatus.NEW
        assert stored.error_rate == 20.0

    def test_p2_alert_message_contains_error_rate(self, alert_service):
        record = alert_service.trigger_alert(error_rate=20.0)
        assert record is not None
        assert "20.0%" in record.message
        assert "P2" in record.message

    def test_p2_alert_has_unique_id(self, alert_service, repo):
        r1 = alert_service.trigger_alert(error_rate=20.0)
        r2 = alert_service.trigger_alert(error_rate=15.0)
        assert r1 is not None and r2 is not None
        assert r1.id != r2.id

    # ── 边界值：5% (P2 下界) ──

    def test_p2_lower_bound_at_5_percent(self, alert_service, repo):
        record = alert_service.trigger_alert(error_rate=5.0)
        assert record is not None
        assert record.severity == Severity.P2
        assert record.error_rate == 5.0

    def test_below_5_percent_does_not_trigger_p2(self, alert_service):
        record = alert_service.trigger_alert(error_rate=4.99)
        assert record is None or record.severity != Severity.P2

    # ── 边界值：接近 50% (P2 上界，不包括 50%) ──

    def test_p2_upper_bound_at_49_99_percent(self, alert_service, repo):
        record = alert_service.trigger_alert(error_rate=49.99)
        assert record is not None
        assert record.severity == Severity.P2

    def test_at_50_percent_is_p1_not_p2(self, alert_service):
        record = alert_service.trigger_alert(error_rate=50.0)
        assert record is not None
        assert record.severity == Severity.P1

    def test_at_50_percent_not_p2(self, alert_service):
        record = alert_service.trigger_alert(error_rate=50.0)
        assert record is not None
        assert record.severity != Severity.P2

    # ── 区间内随机值验证 ──

    @pytest.mark.parametrize("rate", [5.0, 10.0, 20.0, 30.0, 40.0, 49.99])
    def test_all_rates_in_p2_range_trigger_p2(self, alert_service, rate):
        record = alert_service.trigger_alert(error_rate=rate)
        assert record is not None
        assert record.severity == Severity.P2
        assert record.service == "llm_api"
        assert record.status == AlertStatus.NEW

    # ── 告警记录持久化验证 ──

    def test_multiple_alerts_all_stored(self, alert_service, repo):
        for rate in [5.0, 15.0, 25.0, 35.0, 45.0]:
            alert_service.trigger_alert(error_rate=rate)
        all_alerts = repo.find_all()
        assert len(all_alerts) == 5
        for a in all_alerts:
            assert a.severity == Severity.P2
            assert a.service == "llm_api"
            assert a.status == AlertStatus.NEW

    def test_repository_counts_new_alerts(self, alert_service, repo):
        alert_service.trigger_alert(error_rate=20.0)
        alert_service.trigger_alert(error_rate=30.0)
        assert repo.count_by_status(AlertStatus.NEW) == 2

    # ── 错误率超出 5%-50% 不触发 P2 ──

    def test_zero_error_rate_no_p2(self, alert_service):
        record = alert_service.trigger_alert(error_rate=0.0)
        assert record is None or record.severity != Severity.P2

    def test_negative_error_rate_no_p2(self, alert_service):
        record = alert_service.trigger_alert(error_rate=-1.0)
        assert record is None or record.severity != Severity.P2

    def test_100_percent_error_rate_no_p2(self, alert_service):
        record = alert_service.trigger_alert(error_rate=100.0)
        assert record is None or record.severity != Severity.P2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
