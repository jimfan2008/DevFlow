import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import Optional
import uuid


# ====================================================================
# 被测试的领域模型
# ====================================================================


class AlertLevel(str):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TokenLimitConfig:
    """限流成本配置"""

    P2_THRESHOLD_PERCENT = 80
    P1_THRESHOLD_PERCENT = 90
    P0_THRESHOLD_PERCENT = 95

    def __init__(self, daily_limit: int = 1000000):
        self.daily_limit = daily_limit

    @property
    def p2_threshold(self):
        return int(self.daily_limit * self.P2_THRESHOLD_PERCENT / 100)

    @property
    def p1_threshold(self):
        return int(self.daily_limit * self.P1_THRESHOLD_PERCENT / 100)

    @property
    def p0_threshold(self):
        return int(self.daily_limit * self.P0_THRESHOLD_PERCENT / 100)


class AlertRecord:
    """告警记录"""

    def __init__(
        self,
        alert_id: str,
        severity: str,
        content: dict,
        triggered_at: Optional[datetime] = None,
    ):
        self.alert_id = alert_id
        self.severity = severity
        self.content = content
        self.triggered_at = triggered_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity,
            "content": self.content,
            "triggered_at": self.triggered_at.isoformat(),
        }


class AlertsTable:
    """模拟 alerts 表的内存存储"""

    def __init__(self):
        self._records: list[AlertRecord] = []

    def insert(self, record: AlertRecord) -> AlertRecord:
        self._records.append(record)
        return record

    def get_all(self) -> list[AlertRecord]:
        return list(self._records)

    def find_by_severity(self, severity: str) -> list[AlertRecord]:
        return [r for r in self._records if r.severity == severity]

    def find_by_id(self, alert_id: str) -> Optional[AlertRecord]:
        for r in self._records:
            if r.alert_id == alert_id:
                return r
        return None

    def count(self) -> int:
        return len(self._records)

    def clear(self):
        self._records.clear()


class TokenUsageMonitor:
    """Token 消耗监控器"""

    def __init__(self, config: TokenLimitConfig):
        self._config = config
        self._current_usage = 0

    @property
    def current_usage(self) -> int:
        return self._current_usage

    @property
    def daily_limit(self) -> int:
        return self._config.daily_limit

    @property
    def usage_percent(self) -> float:
        if self._config.daily_limit == 0:
            return 0.0
        return round(self._current_usage / self._config.daily_limit * 100, 2)

    def record_usage(self, amount: int):
        self._current_usage += amount

    def reset(self):
        self._current_usage = 0


class AlertService:
    """告警服务"""

    def __init__(
        self,
        monitor: TokenUsageMonitor,
        alerts_table: AlertsTable,
        time_func=None,
        id_func=None,
    ):
        self._monitor = monitor
        self._alerts_table = alerts_table
        self._time_func = time_func or (lambda: datetime.now(timezone.utc))
        self._id_func = id_func or (lambda: str(uuid.uuid4()))
        self._triggered_levels: dict[str, bool] = {}

    def check_and_alert(self) -> Optional[AlertRecord]:
        monitor = self._monitor
        usage = monitor.current_usage
        limit = monitor.daily_limit

        if limit == 0:
            return None

        config = monitor._config
        severity = self._calculate_severity_by_threshold(usage, config)

        if severity is None:
            return None

        percent = round(usage / limit * 100, 2)
        alert_content = {
            "current_usage": usage,
            "daily_limit": limit,
            "usage_percent": f"{int(percent)}%",
            "severity": severity,
        }

        if severity in self._triggered_levels:
            return None

        self._triggered_levels[severity] = True

        alert_id = self._id_func()
        record = AlertRecord(
            alert_id=alert_id,
            severity=severity,
            content=alert_content,
            triggered_at=self._time_func(),
        )
        self._alerts_table.insert(record)
        return record

    def _calculate_severity_by_threshold(self, usage: int, config: TokenLimitConfig) -> Optional[str]:
        if usage >= config.p0_threshold:
            if self._triggered_levels.get(AlertLevel.P0):
                return None
            return AlertLevel.P0
        elif usage >= config.p1_threshold:
            if self._triggered_levels.get(AlertLevel.P1):
                return None
            return AlertLevel.P1
        elif usage >= config.p2_threshold:
            if self._triggered_levels.get(AlertLevel.P2):
                return None
            return AlertLevel.P2
        return None


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def alerts_table():
    table = AlertsTable()
    yield table
    table.clear()


@pytest.fixture
def config():
    return TokenLimitConfig(daily_limit=1000000)


@pytest.fixture
def monitor(config):
    return TokenUsageMonitor(config)


@pytest.fixture
def time_mock():
    return Mock(return_value=datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def id_mock():
    call_count = [0]
    def _gen():
        call_count[0] += 1
        return f"alert-{call_count[0]:04d}"
    return _gen


@pytest.fixture
def service(monitor, alerts_table, time_mock, id_mock):
    return AlertService(
        monitor=monitor,
        alerts_table=alerts_table,
        time_func=time_mock,
        id_func=id_mock,
    )


# ====================================================================
# 测试：Token 消耗达到日限额 80% 时触发 P2 告警
# ====================================================================


class TestP2AlertAt80Percent:

    def test_trigger_p2_alert_at_80_percent(self, service, monitor, alerts_table):
        """当日 Token 消耗达到日限额 80% 时，触发 P2 级别告警"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        assert alert is not None
        assert alert.severity == AlertLevel.P2

    def test_alert_content_contains_current_usage(self, service, monitor, alerts_table):
        """告警内容包含 current_usage=800000"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        assert alert.content["current_usage"] == 800000

    def test_alert_content_contains_daily_limit(self, service, monitor, alerts_table):
        """告警内容包含 daily_limit=1000000"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        assert alert.content["daily_limit"] == 1000000

    def test_alert_content_contains_usage_percent_80(self, service, monitor, alerts_table):
        """告警内容包含 usage_percent=80%"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        assert alert.content["usage_percent"] == "80%"

    def test_alert_content_contains_severity_p2(self, service, monitor, alerts_table):
        """告警内容包含 severity=P2"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        assert alert.content["severity"] == "P2"

    def test_alert_record_written_to_alerts_table(self, service, monitor, alerts_table):
        """告警记录写入 alerts 表"""
        monitor.record_usage(800000)
        service.check_and_alert()

        assert alerts_table.count() == 1
        record = alerts_table.get_all()[0]
        assert record.severity == AlertLevel.P2
        assert record.content["current_usage"] == 800000
        assert record.content["daily_limit"] == 1000000
        assert record.content["usage_percent"] == "80%"

    def test_alert_record_has_generated_id(self, service, monitor, alerts_table):
        """告警记录包含生成的唯一 ID"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        assert alert.alert_id is not None
        assert len(alert.alert_id) > 0

    def test_alert_record_has_trigger_time(self, service, monitor, alerts_table):
        """告警记录包含触发时间"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        assert alert.triggered_at is not None
        assert isinstance(alert.triggered_at, datetime)
        assert alert.triggered_at.tzinfo is not None


# ====================================================================
# 测试：P2 告警不触发的边界情况
# ====================================================================


class TestP2AlertBoundary:

    def test_no_alert_below_80_percent(self, service, monitor, alerts_table):
        """消耗低于 80% 时，不触发 P2 告警"""
        monitor.record_usage(799999)
        alert = service.check_and_alert()
        assert alert is None
        assert alerts_table.count() == 0

    def test_exact_80_percent_triggers_alert(self, service, monitor, alerts_table):
        """恰好 80% 时触发 P2 告警"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertLevel.P2

    def test_81_percent_still_p2_not_p1(self, service, monitor, alerts_table):
        """81% 时仍然触发 P2 级别（而非 P1）"""
        monitor.record_usage(810000)
        alert = service.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertLevel.P2

    def test_90_percent_triggers_p1_not_p2(self, service, monitor, alerts_table):
        """90% 时触发 P1 级别而非 P2"""
        monitor.record_usage(900000)
        alert = service.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertLevel.P1


# ====================================================================
# 测试：P2 告警不重复触发
# ====================================================================


class TestP2AlertNoDuplicate:

    def test_p2_alert_not_triggered_twice(self, service, monitor, alerts_table):
        """达到 80% 后重复检查不产生第二条 P2 告警"""
        monitor.record_usage(800000)
        first = service.check_and_alert()
        assert first is not None

        second = service.check_and_alert()
        assert second is None
        assert alerts_table.count() == 1

    def test_usage_increases_no_duplicate_p2(self, service, monitor, alerts_table):
        """达到 80% 后继续消耗但仍在 P2 范围内，不重复产生告警"""
        monitor.record_usage(800000)
        first = service.check_and_alert()
        assert first is not None
        assert first.severity == AlertLevel.P2

        monitor.record_usage(50000)
        second = service.check_and_alert()
        assert second is None
        assert alerts_table.count() == 1


# ====================================================================
# 测试：从 P2 升级的情况
# ====================================================================


class TestAlertLevelEscalation:

    def test_escalation_from_p2_to_p1(self, service, monitor, alerts_table):
        """消耗从 80% 增长到 90% 时，触发 P1 升级告警"""
        monitor.record_usage(800000)
        p2_alert = service.check_and_alert()
        assert p2_alert is not None
        assert p2_alert.severity == AlertLevel.P2

        monitor.record_usage(100000)
        p1_alert = service.check_and_alert()
        assert p1_alert is not None
        assert p1_alert.severity == AlertLevel.P1

    def test_escalation_from_p2_to_p0(self, service, monitor, alerts_table):
        """消耗从 80% 直接增长到 95% 时，触发 P0 告警"""
        monitor.record_usage(800000)
        p2_alert = service.check_and_alert()
        assert p2_alert is not None
        assert p2_alert.severity == AlertLevel.P2

        monitor.record_usage(150000)
        p0_alert = service.check_and_alert()
        assert p0_alert is not None
        assert p0_alert.severity == AlertLevel.P0

    def test_multiple_escalert_records_in_table(self, service, monitor, alerts_table):
        """每次升级都会产生一条新记录"""
        monitor.record_usage(800000)
        service.check_and_alert()

        monitor.record_usage(100000)
        service.check_and_alert()

        monitor.record_usage(50000)
        service.check_and_alert()

        assert alerts_table.count() == 3
        records = alerts_table.get_all()
        assert records[0].severity == AlertLevel.P2
        assert records[1].severity == AlertLevel.P1
        assert records[2].severity == AlertLevel.P0


# ====================================================================
# 测试：TokenUsageMonitor 的正确性
# ====================================================================


class TestTokenUsageMonitor:

    def test_initial_usage_is_zero(self, monitor):
        """初始消耗为 0"""
        assert monitor.current_usage == 0

    def test_usage_accumulates_correctly(self, monitor):
        """消耗累计正确"""
        monitor.record_usage(100000)
        monitor.record_usage(200000)
        monitor.record_usage(500000)
        assert monitor.current_usage == 800000

    def test_daily_limit_returns_config_value(self, monitor):
        """日限额返回配置值"""
        assert monitor.daily_limit == 1000000

    def test_usage_percent_at_80(self, monitor):
        """800000/1000000 = 80%"""
        monitor.record_usage(800000)
        assert monitor.usage_percent == 80.0

    def test_reset_clears_usage(self, monitor):
        """重置后消耗归零"""
        monitor.record_usage(800000)
        monitor.reset()
        assert monitor.current_usage == 0
        assert monitor.usage_percent == 0.0


# ====================================================================
# 测试：AlertRecord 序列化
# ====================================================================


class TestAlertRecordSerialization:

    def test_to_dict_contains_all_fields(self, service, monitor, alerts_table):
        """序列化包含所有必需字段"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()
        d = alert.to_dict()

        assert "alert_id" in d
        assert "severity" in d
        assert "content" in d
        assert "triggered_at" in d

    def test_to_dict_content_unchanged(self, service, monitor, alerts_table):
        """序列化后内容字段不变"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()
        d = alert.to_dict()

        assert d["content"]["current_usage"] == 800000
        assert d["content"]["daily_limit"] == 1000000
        assert d["content"]["usage_percent"] == "80%"
        assert d["content"]["severity"] == "P2"

    def test_severity_in_dict_is_p2(self, service, monitor, alerts_table):
        """序列化后严重程度为 P2"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()
        d = alert.to_dict()

        assert d["severity"] == "P2"


# ====================================================================
# 测试：AlertsTable 查询能力
# ====================================================================


class TestAlertsTableQuery:

    def test_find_by_severity_p2(self, service, monitor, alerts_table):
        """按 P2 级别查询能获取对应记录"""
        monitor.record_usage(800000)
        service.check_and_alert()

        p2_records = alerts_table.find_by_severity(AlertLevel.P2)
        assert len(p2_records) == 1
        assert p2_records[0].content["current_usage"] == 800000

    def test_find_by_id_returns_correct_record(self, service, monitor, alerts_table):
        """按 ID 精确查询"""
        monitor.record_usage(800000)
        alert = service.check_and_alert()

        found = alerts_table.find_by_id(alert.alert_id)
        assert found is not None
        assert found.alert_id == alert.alert_id
        assert found.severity == AlertLevel.P2

    def test_find_by_id_nonexistent_returns_none(self, alerts_table):
        """查询不存在的 ID 返回 None"""
        assert alerts_table.find_by_id("nonexistent-id") is None

    def test_table_count_increments_with_insert(self, service, monitor, alerts_table):
        """插入记录后数量递增"""
        assert alerts_table.count() == 0
        monitor.record_usage(800000)
        service.check_and_alert()
        assert alerts_table.count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
