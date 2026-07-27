import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import time
import json


# ==============================================================================
# Mock implementation of alert history service
# ==============================================================================

class AlertRecord:
    """告警记录模型"""

    def __init__(self, alert_id, triggered_at, content, status, handler, severity="high"):
        self.alert_id = alert_id
        self.triggered_at = triggered_at
        self.content = content
        self.status = status
        self.handler = handler
        self.severity = severity

    def to_dict(self):
        return {
            "alert_id": self.alert_id,
            "triggered_at": self.triggered_at.isoformat() if isinstance(self.triggered_at, datetime) else str(self.triggered_at),
            "content": self.content,
            "status": self.status,
            "handler": self.handler,
            "severity": self.severity,
        }


class AlertHistoryService:
    """告警历史服务 - 生产模拟"""

    MIN_RETENTION_DAYS = 90

    def __init__(self):
        self._records = []

    def add_record(self, record: AlertRecord):
        self._records.append(record)

    def add_records(self, records: list):
        self._records.extend(records)

    def query(self, status=None, severity=None, handler=None, start_date=None, end_date=None):
        """多条件筛选查询"""
        results = self._records[:]

        if status is not None:
            results = [r for r in results if r.status == status]
        if severity is not None:
            results = [r for r in results if r.severity == severity]
        if handler is not None:
            results = [r for r in results if r.handler == handler]
        if start_date is not None:
            results = [r for r in results if r.triggered_at >= start_date]
        if end_date is not None:
            results = [r for r in results if r.triggered_at <= end_date]

        return results

    def get_retention_days(self):
        """返回配置的保留天数"""
        return self.MIN_RETENTION_DAYS

    def get_all_records(self):
        return self._records[:]


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def service():
    """创建空的告警历史服务"""
    return AlertHistoryService()


@pytest.fixture
def service_with_data(service):
    """预填充120条跨越120天的告警数据"""
    now = datetime(2026, 7, 16, 12, 0, 0)
    records = []

    statuses = ["pending", "processing", "resolved", "ignored"]
    severities = ["low", "medium", "high", "critical"]
    handlers = ["张三", "李四", "王五", "赵六"]
    contents = [
        "CPU使用率超过90%",
        "内存不足告警",
        "磁盘空间低于10%",
        "网络延迟超过500ms",
        "数据库连接池耗尽",
        "API响应时间超过3秒",
    ]

    for i in range(120):
        triggered_at = now - timedelta(days=i)
        record = AlertRecord(
            alert_id=f"ALERT-{1000 + i}",
            triggered_at=triggered_at,
            content=contents[i % len(contents)],
            status=statuses[i % len(statuses)],
            handler=handlers[i % len(handlers)],
            severity=severities[i % len(severities)],
        )
        records.append(record)

    service.add_records(records)
    return service


@pytest.fixture
def empty_service():
    """完全空的服务实例"""
    return AlertHistoryService()


# ==============================================================================
# Tests: 告警历史保存 >= 90 天
# ==============================================================================

class TestAlertHistoryRetention:

    def test_retention_days_configured_at_least_90(self, service):
        """验收标准：至少保留90天历史数据"""
        retention = service.get_retention_days()
        assert retention >= 90, f"保留天数 {retention} 天，小于要求的 90 天"

    def test_records_from_90_days_ago_are_present(self, service_with_data):
        """90 天前的记录仍然在查询结果中"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        date_90_days_ago = now - timedelta(days=90)
        results = service_with_data.query(start_date=date_90_days_ago)
        # 应包含从第 0 天到第 90 天的记录（含边界）
        assert len(results) >= 91, f"90 天前的记录数 {len(results)} 不足"

    def test_records_from_95_days_ago_are_present(self, service_with_data):
        """95 天前的记录仍然在查询结果中"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        date_95_days_ago = now - timedelta(days=95)
        results = service_with_data.query(start_date=date_95_days_ago)
        assert len(results) >= 96, f"95 天前的记录数 {len(results)} 不足"

    def test_oldest_record_is_at_least_90_days_old(self, service_with_data):
        """最旧记录的年龄至少90天"""
        all_records = service_with_data.get_all_records()
        all_records_sorted = sorted(all_records, key=lambda r: r.triggered_at)
        oldest = all_records_sorted[0]
        now = datetime(2026, 7, 16, 12, 0, 0)
        age_days = (now - oldest.triggered_at).days
        assert age_days >= 90, f"最旧记录年龄 {age_days} 天，不足 90 天"


# ==============================================================================
# Tests: 多条件筛选
# ==============================================================================

class TestMultiConditionFiltering:

    def test_filter_by_status_only(self, service_with_data):
        """按处理状态筛选"""
        results = service_with_data.query(status="resolved")
        assert len(results) > 0, "resolved 状态应至少有一条记录"
        for r in results:
            assert r.status == "resolved", f"期望 resolved, 实际 {r.status}"

    def test_filter_by_severity_only(self, service_with_data):
        """按严重程度筛选"""
        results = service_with_data.query(severity="critical")
        assert len(results) > 0, "critical 级别应至少有一条记录"
        for r in results:
            assert r.severity == "critical"

    def test_filter_by_handler_only(self, service_with_data):
        """按处理人筛选"""
        results = service_with_data.query(handler="张三")
        assert len(results) > 0, "张三处理的记录应至少有一条"
        for r in results:
            assert r.handler == "张三"

    def test_filter_by_date_range(self, service_with_data):
        """按日期范围筛选"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        start = now - timedelta(days=30)
        end = now - timedelta(days=10)
        results = service_with_data.query(start_date=start, end_date=end)
        assert len(results) == 21, f"期望 21 条，实际 {len(results)}"
        for r in results:
            assert r.triggered_at >= start, "记录日期应 >= start_date"
            assert r.triggered_at <= end, "记录日期应 <= end_date"

    def test_filter_combined_status_and_severity(self, service_with_data):
        """组合筛选：状态 + 严重程度"""
        results = service_with_data.query(status="pending", severity="high")
        for r in results:
            assert r.status == "pending"
            assert r.severity == "high"

    def test_filter_combined_all_conditions(self, service_with_data):
        """组合筛选：状态 + 严重程度 + 处理人 + 日期范围"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        results = service_with_data.query(
            status="pending",
            severity="high",
            handler="张三",
            start_date=now - timedelta(days=60),
            end_date=now,
        )
        for r in results:
            assert r.status == "pending"
            assert r.severity == "high"
            assert r.handler == "张三"
            assert r.triggered_at >= now - timedelta(days=60)
            assert r.triggered_at <= now

    def test_filter_returns_empty_when_no_match(self, service_with_data):
        """无匹配时返回空列表"""
        results = service_with_data.query(handler="不存在的人")
        assert results == [], f"期望空列表，实际 {len(results)} 条"

    def test_filter_no_conditions_returns_all(self, service_with_data):
        """不传条件时返回全部记录"""
        results = service_with_data.query()
        assert len(results) == 120, f"期望 120 条，实际 {len(results)}"


# ==============================================================================
# Tests: 查询响应时间 <= 1 秒
# ==============================================================================

class TestQueryResponseTime:

    def test_single_condition_query_within_1_second(self, service_with_data):
        """单条件查询响应时间 <= 1 秒"""
        start_time = time.monotonic()
        service_with_data.query(status="resolved")
        elapsed = time.monotonic() - start_time
        assert elapsed <= 1.0, f"单条件查询耗时 {elapsed:.4f}s，超过 1s 上限"

    def test_multi_condition_query_within_1_second(self, service_with_data):
        """多条件查询响应时间 <= 1 秒"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        start_time = time.monotonic()
        service_with_data.query(
            status="pending",
            severity="critical",
            handler="李四",
            start_date=now - timedelta(days=60),
            end_date=now,
        )
        elapsed = time.monotonic() - start_time
        assert elapsed <= 1.0, f"多条件查询耗时 {elapsed:.4f}s，超过 1s 上限"

    def test_full_scan_query_within_1_second(self, service_with_data):
        """全量查询响应时间 <= 1 秒"""
        start_time = time.monotonic()
        service_with_data.query()
        elapsed = time.monotonic() - start_time
        assert elapsed <= 1.0, f"全量查询耗时 {elapsed:.4f}s，超过 1s 上限"

    def test_empty_db_query_within_1_second(self, empty_service):
        """空库查询响应时间 <= 1 秒"""
        start_time = time.monotonic()
        empty_service.query()
        elapsed = time.monotonic() - start_time
        assert elapsed <= 1.0, f"空库查询耗时 {elapsed:.4f}s，超过 1s 上限"


# ==============================================================================
# Tests: 告警记录字段完整性
# ==============================================================================

class TestAlertRecordFields:

    def test_record_contains_triggered_at(self, service_with_data):
        """记录包含触发时间"""
        results = service_with_data.query()
        assert len(results) > 0
        record = results[0]
        assert record.triggered_at is not None
        assert isinstance(record.triggered_at, datetime)

    def test_record_contains_content(self, service_with_data):
        """记录包含告警内容"""
        results = service_with_data.query()
        record = results[0]
        assert record.content is not None
        assert isinstance(record.content, str)
        assert len(record.content) > 0

    def test_record_contains_status(self, service_with_data):
        """记录包含处理状态"""
        results = service_with_data.query()
        record = results[0]
        assert record.status is not None
        assert isinstance(record.status, str)
        assert record.status in ("pending", "processing", "resolved", "ignored")

    def test_record_contains_handler(self, service_with_data):
        """记录包含处理人"""
        results = service_with_data.query()
        record = results[0]
        assert record.handler is not None
        assert isinstance(record.handler, str)

    def test_record_to_dict_contains_all_required_fields(self, service_with_data):
        """序列化为字典时包含所有必需字段"""
        results = service_with_data.query()
        record_dict = results[0].to_dict()
        required_keys = {"alert_id", "triggered_at", "content", "status", "handler"}
        assert required_keys.issubset(record_dict.keys()), (
            f"缺少字段: {required_keys - set(record_dict.keys())}"
        )


# ==============================================================================
# Tests: 边界情况
# ==============================================================================

class TestEdgeCases:

    def test_boundary_date_inclusive_start(self, service_with_data):
        """start_date 边界包含当天"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        results = service_with_data.query(start_date=now)
        # 当天的记录应被包含
        for r in results:
            assert r.triggered_at >= now

    def test_boundary_date_inclusive_end(self, service_with_data):
        """end_date 边界包含当天"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        results = service_with_data.query(end_date=now)
        # 所有记录都 <= now（now 是最近时间），所以应返回全部 120 条
        assert len(results) == 120
        # 验证当天的记录确实在结果中
        today_records = [r for r in results if r.triggered_at == now]
        assert len(today_records) >= 1, "当天记录应包含在查询结果中"

    def test_add_single_record_and_query(self, empty_service):
        """单条记录添加后可查询"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        rec = AlertRecord(
            alert_id="ALERT-9999",
            triggered_at=now,
            content="单条测试告警",
            status="pending",
            handler="测试人",
        )
        empty_service.add_record(rec)
        results = empty_service.query(status="pending")
        assert len(results) == 1
        assert results[0].alert_id == "ALERT-9999"

    def test_records_sorted_by_date_ascending_when_queried_by_range(self, service_with_data):
        """按日期范围查询返回的记录应可正常排序"""
        now = datetime(2026, 7, 16, 12, 0, 0)
        results = service_with_data.query(
            start_date=now - timedelta(days=10),
            end_date=now - timedelta(days=5),
        )
        sorted_results = sorted(results, key=lambda r: r.triggered_at)
        for i in range(1, len(sorted_results)):
            assert sorted_results[i].triggered_at >= sorted_results[i - 1].triggered_at
