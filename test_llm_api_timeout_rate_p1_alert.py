import math
import sys
import os

import pytest

# 从生产模块引入被测领域模型（非内联Mock）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from app.models.llm_monitoring import (
    AlertSeverity,
    AlertRecord,
    AlertsTable,
    TimeoutTracker,
    TimeoutAlertSystem,
)


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def alerts_table():
    table = AlertsTable()
    table.clear()
    return table


@pytest.fixture
def tracker():
    return TimeoutTracker()


@pytest.fixture
def alert_system(tracker, alerts_table):
    return TimeoutAlertSystem(tracker=tracker, alerts_table=alerts_table)


# ====================================================================
# 测试：超时率 > 20% 触发 P1 告警
# ====================================================================

class TestTimeoutRateP1Alert:
    """验证当超时率超过20%时，系统自动触发P1级别告警"""

    def test_timeout_rate_30_percent_triggers_p1_alert(self, alert_system, tracker):
        # 记录 30% 超时率：10 次请求中 3 次超时
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        assert tracker.timeout_rate == pytest.approx(30.0)
        alert = alert_system.check_and_alert()

        assert alert is not None
        assert alert.severity == AlertSeverity.P1

    def test_p1_alert_contains_timeout_rate_30(self, alert_system, tracker):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.timeout_rate == pytest.approx(30.0)

    def test_p1_alert_contains_threshold_20(self, alert_system, tracker):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.threshold == 20.0

    def test_p1_alert_severity_is_p1(self, alert_system, tracker):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertSeverity.P1

    def test_p1_alert_metric_is_llm_request_timeout_total(self, alert_system, tracker):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert = alert_system.check_and_alert()
        assert alert is not None
        assert alert.metric == "llm_request_timeout_total"


# ====================================================================
# 测试：告警记录写入 alerts 表
# ====================================================================

class TestAlertRecordWrittenToTable:
    """告警记录写入 alerts 表"""

    def test_alert_record_inserted_into_alerts_table(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()

        assert alerts_table.count() == 1
        record = alerts_table.find_all()[0]
        assert record.severity == AlertSeverity.P1
        assert record.timeout_rate == pytest.approx(30.0)
        assert record.threshold == 20.0
        assert record.metric == "llm_request_timeout_total"

    def test_alert_record_has_generated_id(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()

        record = alerts_table.find_all()[0]
        assert record.alert_id is not None
        assert len(record.alert_id) > 0

    def test_alert_record_has_triggered_at(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()

        record = alerts_table.find_all()[0]
        assert record.triggered_at is not None
        assert len(record.triggered_at) > 0

    def test_p1_alert_can_be_found_by_severity(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()

        p1_records = alerts_table.find_by_severity(AlertSeverity.P1)
        assert len(p1_records) == 1
        assert p1_records[0].timeout_rate == pytest.approx(30.0)

    def test_p1_alert_can_be_found_by_id(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert = alert_system.check_and_alert()
        assert alert is not None

        found = alerts_table.find_by_id(alert.alert_id)
        assert found is not None
        assert found.alert_id == alert.alert_id
        assert found.severity == AlertSeverity.P1


# ====================================================================
# 测试：告警内容完整性
# ====================================================================

class TestAlertContent:
    """告警内容包含 timeout_rate=30%、threshold=20%、severity=P1、metric=llm_request_timeout_total"""

    def test_to_dict_contains_timeout_rate(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()
        record = alerts_table.find_all()[0]
        d = record.to_dict()

        assert d["timeout_rate"] == pytest.approx(30.0)

    def test_to_dict_contains_threshold(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()
        record = alerts_table.find_all()[0]
        d = record.to_dict()

        assert d["threshold"] == 20.0

    def test_to_dict_contains_severity_p1(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()
        record = alerts_table.find_all()[0]
        d = record.to_dict()

        assert d["severity"] == "P1"

    def test_to_dict_contains_metric(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()
        record = alerts_table.find_all()[0]
        d = record.to_dict()

        assert d["metric"] == "llm_request_timeout_total"

    def test_to_dict_contains_alert_id(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()
        record = alerts_table.find_all()[0]
        d = record.to_dict()

        assert "alert_id" in d
        assert len(d["alert_id"]) > 0

    def test_to_dict_contains_triggered_at(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert_system.check_and_alert()
        record = alerts_table.find_all()[0]
        d = record.to_dict()

        assert "triggered_at" in d
        assert len(d["triggered_at"]) > 0


# ====================================================================
# 测试：阈值边界条件
# ====================================================================

class TestThresholdBoundaries:
    """阈值边界条件验证"""

    def test_timeout_rate_exactly_20_percent_does_not_trigger_p1(self, alert_system, tracker, alerts_table):
        # 恰好 20%：10 次请求中 2 次超时
        for _ in range(8):
            tracker.record_request(timed_out=False)
        for _ in range(2):
            tracker.record_request(timed_out=True)

        assert tracker.timeout_rate == pytest.approx(20.0)
        alert = alert_system.check_and_alert()

        # 超时率等于 20%，不大于 20%，不触发 P1（触发 P2）
        assert alert is None or alert.severity != AlertSeverity.P1

    def test_timeout_rate_21_percent_triggers_p1(self, alert_system, tracker, alerts_table):
        # 21% 超时率：100 次请求中 21 次超时
        for _ in range(79):
            tracker.record_request(timed_out=False)
        for _ in range(21):
            tracker.record_request(timed_out=True)

        assert math.isclose(tracker.timeout_rate, 21.0, abs_tol=0.1)
        alert = alert_system.check_and_alert()

        assert alert is not None
        assert alert.severity == AlertSeverity.P1

    def test_timeout_rate_15_percent_does_not_trigger_p1(self, alert_system, tracker, alerts_table):
        # 15% 超时率
        for _ in range(85):
            tracker.record_request(timed_out=False)
        for _ in range(15):
            tracker.record_request(timed_out=True)

        assert math.isclose(tracker.timeout_rate, 15.0, abs_tol=0.1)
        alert = alert_system.check_and_alert()

        assert alert is None or alert.severity != AlertSeverity.P1

    def test_timeout_rate_50_percent_triggers_p1(self, alert_system, tracker, alerts_table):
        # 50% 超时率
        for _ in range(5):
            tracker.record_request(timed_out=False)
        for _ in range(5):
            tracker.record_request(timed_out=True)

        assert tracker.timeout_rate == pytest.approx(50.0)
        alert = alert_system.check_and_alert()

        assert alert is not None
        assert alert.severity == AlertSeverity.P1
        assert alert.timeout_rate == pytest.approx(50.0)
        assert alert.threshold == 20.0

    def test_no_requests_no_alert(self, alert_system, tracker, alerts_table):
        alert = alert_system.check_and_alert()
        assert alert is None
        assert alerts_table.count() == 0

    def test_zero_timeout_no_alert(self, alert_system, tracker, alerts_table):
        for _ in range(10):
            tracker.record_request(timed_out=False)

        alert = alert_system.check_and_alert()
        assert alert is None
        assert alerts_table.count() == 0


# ====================================================================
# 测试：P1 告警去重
# ====================================================================

class TestP1AlertDeduplication:
    """P1 告警不应重复触发"""

    def test_p1_alert_only_triggered_once(self, alert_system, tracker, alerts_table):
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert1 = alert_system.check_and_alert()
        assert alert1 is not None
        assert alert1.severity == AlertSeverity.P1

        # 再次检查不应再触发 P1 告警
        alert2 = alert_system.check_and_alert()
        assert alert2 is None
        assert alerts_table.count() == 1

    def test_p1_alert_with_more_timeouts_no_duplicate(self, alert_system, tracker, alerts_table):
        for _ in range(3):
            tracker.record_request(timed_out=False)
        for _ in range(7):
            tracker.record_request(timed_out=True)

        alert1 = alert_system.check_and_alert()
        assert alert1 is not None

        # 再增加超时请求
        for _ in range(5):
            tracker.record_request(timed_out=True)

        alert2 = alert_system.check_and_alert()
        assert alert2 is None
        assert alerts_table.count() == 1


# ====================================================================
# 测试：完整验收标准场景
# ====================================================================

class TestFullAcceptanceScenario:
    """完整验收标准场景：超时率=30% → P1 告警 → 写入 alerts 表"""

    def test_full_scenario_timeout_30_percent_p1_alert_in_table(self):
        """端到端验证：
        - 超时率 30% 超过阈值 20%
        - 生成 P1 级别告警
        - 告警包含 timeout_rate=30%, threshold=20%, severity=P1, metric=llm_request_timeout_total
        - 告警记录写入 alerts 表
        """
        table = AlertsTable()
        tracker = TimeoutTracker()
        system = TimeoutAlertSystem(tracker=tracker, alerts_table=table)

        # 模拟 30% 超时率
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        assert math.isclose(tracker.timeout_rate, 30.0, abs_tol=1e-9)

        # 触发告警
        alert = system.check_and_alert()

        # 验证告警不为 None
        assert alert is not None

        # 验证告警内容
        assert alert.timeout_rate == pytest.approx(30.0)
        assert alert.threshold == 20.0
        assert alert.severity == AlertSeverity.P1
        assert alert.metric == "llm_request_timeout_total"

        # 验证写入 alerts 表
        assert table.count() == 1
        record = table.find_all()[0]
        assert record.alert_id == alert.alert_id
        assert record.severity == AlertSeverity.P1
        assert record.timeout_rate == pytest.approx(30.0)
        assert record.threshold == 20.0
        assert record.metric == "llm_request_timeout_total"

        # 验证可序列化
        d = record.to_dict()
        assert d["timeout_rate"] == pytest.approx(30.0)
        assert d["threshold"] == 20.0
        assert d["severity"] == "P1"
        assert d["metric"] == "llm_request_timeout_total"
        assert d["alert_id"] == alert.alert_id

    def test_full_scenario_higher_timeout_rate_50_percent(self):
        """更高超时率的完整场景"""
        table = AlertsTable()
        tracker = TimeoutTracker()
        system = TimeoutAlertSystem(tracker=tracker, alerts_table=table)

        for _ in range(5):
            tracker.record_request(timed_out=False)
        for _ in range(5):
            tracker.record_request(timed_out=True)

        assert tracker.timeout_rate == pytest.approx(50.0)

        alert = system.check_and_alert()
        assert alert is not None
        assert alert.severity == AlertSeverity.P1
        assert alert.timeout_rate == pytest.approx(50.0)
        assert alert.threshold == 20.0
        assert alert.metric == "llm_request_timeout_total"

        assert table.count() == 1

    def test_multiple_alerts_in_table_after_reset(self, alert_system):
        """多次触发告警（通过 reset 重置去重标记）"""
        table = alert_system.alerts_table
        tracker = alert_system.tracker

        # 第一轮：30% 超时率
        for _ in range(7):
            tracker.record_request(timed_out=False)
        for _ in range(3):
            tracker.record_request(timed_out=True)

        alert1 = alert_system.check_and_alert()
        assert alert1 is not None

        # 重置
        tracker.reset()
        alert_system.reset()

        # 第二轮：40% 超时率
        for _ in range(6):
            tracker.record_request(timed_out=False)
        for _ in range(4):
            tracker.record_request(timed_out=True)

        alert2 = alert_system.check_and_alert()
        assert alert2 is not None

        # 验证表中有两条记录
        assert table.count() == 2
        records = table.find_all()
        assert records[0].timeout_rate == pytest.approx(30.0)
        assert records[1].timeout_rate == pytest.approx(40.0)
        assert alert1.alert_id != alert2.alert_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
