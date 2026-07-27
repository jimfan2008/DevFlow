"""PostgreSQL连接状态监控测试用例"""

import time
from unittest.mock import MagicMock, patch, PropertyMock
import pytest


# ---------- Mock 数据模型 ----------

class MockDBStats:
    """模拟数据库统计信息"""

    def __init__(self, current_connections: int, max_connections: int, avg_response_time_ms: float, slow_queries: list):
        self.current_connections = current_connections
        self.max_connections = max_connections
        self.avg_response_time_ms = avg_response_time_ms
        self.slow_queries = slow_queries


class MockPrometheusCollector:
    """模拟 Prometheus 指标采集器"""

    def __init__(self):
        self.collected_metrics: dict = {}
        self.collection_intervals: list = []
        self._last_collection_time: float = 0.0

    def collect(self, stats: MockDBStats) -> dict:
        now = time.time()
        if self._last_collection_time > 0:
            self.collection_intervals.append(now - self._last_collection_time)
        self._last_collection_time = now
        self.collected_metrics = {
            "pg_current_connections": stats.current_connections,
            "pg_max_connections": stats.max_connections,
            "pg_connection_ratio": stats.current_connections / stats.max_connections if stats.max_connections > 0 else 0,
            "pg_avg_response_time_ms": stats.avg_response_time_ms,
            "pg_slow_query_count": len([q for q in stats.slow_queries if q.get("duration_s", 0) > 1.0]),
        }
        return self.collected_metrics


# ---------- 被测试的业务逻辑 ----------

class PostgresConnectionMonitor:
    """PostgreSQL连接状态监控器"""

    MAX_RESPONSE_TIME_MS = 50
    SLOW_QUERY_THRESHOLD_MS = 1000
    MAX_PROMETHEUS_INTERVAL_S = 15

    def __init__(self, db_stats: MockDBStats, collector: MockPrometheusCollector):
        self.db_stats = db_stats
        self.collector = collector

    def get_connection_ratio(self) -> float:
        """返回当前连接数 / 最大连接数比例"""
        if self.db_stats.max_connections <= 0:
            return 0.0
        return self.db_stats.current_connections / self.db_stats.max_connections

    def is_response_time_ok(self) -> bool:
        """平均响应时间是否 <= 50ms"""
        return self.db_stats.avg_response_time_ms <= self.MAX_RESPONSE_TIME_MS

    def get_slow_queries(self) -> list:
        """返回慢查询列表（>1秒）"""
        threshold_s = self.SLOW_QUERY_THRESHOLD_MS / 1000.0
        return [q for q in self.db_stats.slow_queries if q.get("duration_s", 0) > threshold_s]

    def is_prometheus_interval_ok(self) -> bool:
        """Prometheus 采集间隔是否 <= 15秒"""
        if not self.collector.collection_intervals:
            return True  # 尚未采集多次，默认通过
        return all(interval <= self.MAX_PROMETHEUS_INTERVAL_S for interval in self.collector.collection_intervals)

    def run_full_check(self) -> dict:
        """运行完整检查，返回所有指标"""
        self.collector.collect(self.db_stats)
        return {
            "connection_ratio": self.get_connection_ratio(),
            "response_time_ok": self.is_response_time_ok(),
            "slow_queries": self.get_slow_queries(),
            "prometheus_interval_ok": self.is_prometheus_interval_ok(),
            "metrics": self.collector.collected_metrics,
        }


# ---------- Pytest Fixtures ----------

@pytest.fixture
def normal_stats() -> MockDBStats:
    """正常状态：连接数适中、响应时间正常、无慢查询"""
    return MockDBStats(
        current_connections=30,
        max_connections=100,
        avg_response_time_ms=25.0,
        slow_queries=[],
    )


@pytest.fixture
def high_load_stats() -> MockDBStats:
    """高负载：连接数接近上限"""
    return MockDBStats(
        current_connections=95,
        max_connections=100,
        avg_response_time_ms=45.0,
        slow_queries=[],
    )


@pytest.fixture
def slow_query_stats() -> MockDBStats:
    """存在慢查询"""
    return MockDBStats(
        current_connections=20,
        max_connections=100,
        avg_response_time_ms=30.0,
        slow_queries=[
            {"query": "SELECT * FROM users", "duration_s": 0.5},
            {"query": "UPDATE orders SET status='done'", "duration_s": 2.3},
            {"query": "DELETE FROM logs WHERE created_at < '2025-01-01'", "duration_s": 5.1},
        ],
    )


@pytest.fixture
def collector() -> MockPrometheusCollector:
    return MockPrometheusCollector()


@pytest.fixture
def monitor(normal_stats, collector):
    return PostgresConnectionMonitor(normal_stats, collector)


# ---------- 测试用例 ----------

class TestConnectionRatio:
    """验收标准 1：显示当前连接数/最大连接数比例"""

    def test_normal_ratio(self, monitor):
        ratio = monitor.get_connection_ratio()
        assert ratio == 0.3, f"期望 0.3，实际 {ratio}"

    def test_high_load_ratio(self, high_load_stats, collector):
        mon = PostgresConnectionMonitor(high_load_stats, collector)
        ratio = mon.get_connection_ratio()
        assert ratio == 0.95, f"期望 0.95，实际 {ratio}"

    def test_zero_max_connections(self, collector):
        stats = MockDBStats(current_connections=0, max_connections=0, avg_response_time_ms=10.0, slow_queries=[])
        mon = PostgresConnectionMonitor(stats, collector)
        ratio = mon.get_connection_ratio()
        assert ratio == 0.0, "最大连接数为 0 时应返回 0.0"

    def test_ratio_in_metrics(self, monitor, collector):
        result = monitor.run_full_check()
        assert "pg_connection_ratio" in result["metrics"]
        assert result["metrics"]["pg_connection_ratio"] == 0.3


class TestResponseTime:
    """验收标准 2：平均响应时间 <= 50ms"""

    def test_response_time_within_limit(self, monitor):
        assert monitor.is_response_time_ok() is True

    def test_response_time_exceeds_limit(self, collector):
        stats = MockDBStats(current_connections=10, max_connections=100, avg_response_time_ms=75.0, slow_queries=[])
        mon = PostgresConnectionMonitor(stats, collector)
        assert mon.is_response_time_ok() is False

    def test_response_time_at_boundary(self, collector):
        stats = MockDBStats(current_connections=10, max_connections=100, avg_response_time_ms=50.0, slow_queries=[])
        mon = PostgresConnectionMonitor(stats, collector)
        assert mon.is_response_time_ok() is True, "等于 50ms 应视为合格"


class TestSlowQueries:
    """验收标准 3：慢查询列表（>1秒的查询）"""

    def test_no_slow_queries(self, monitor):
        result = monitor.get_slow_queries()
        assert result == [], "无慢查询时应返回空列表"

    def test_slow_queries_detected(self, slow_query_stats, collector):
        mon = PostgresConnectionMonitor(slow_query_stats, collector)
        slow = mon.get_slow_queries()
        assert len(slow) == 2, f"期望 2 条慢查询，实际 {len(slow)}"
        assert slow[0]["query"] == "UPDATE orders SET status='done'"
        assert slow[1]["query"] == "DELETE FROM logs WHERE created_at < '2025-01-01'"

    def test_fast_query_not_included(self, collector):
        stats = MockDBStats(
            current_connections=10,
            max_connections=100,
            avg_response_time_ms=20.0,
            slow_queries=[
                {"query": "SELECT 1", "duration_s": 0.999},
            ],
        )
        mon = PostgresConnectionMonitor(stats, collector)
        slow = mon.get_slow_queries()
        assert len(slow) == 0, "0.999秒不应被视为慢查询"

    def test_exactly_one_second_is_not_slow(self, collector):
        stats = MockDBStats(
            current_connections=10,
            max_connections=100,
            avg_response_time_ms=20.0,
            slow_queries=[
                {"query": "SELECT * FROM big_table", "duration_s": 1.0},
            ],
        )
        mon = PostgresConnectionMonitor(stats, collector)
        slow = mon.get_slow_queries()
        assert len(slow) == 0, "恰好 1.0 秒不应被视为慢查询（需 > 1秒）"


class TestPrometheusInterval:
    """验收标准 4：Prometheus 指标采集间隔 <= 15秒"""

    def test_no_intervals_yet(self, monitor):
        assert monitor.is_prometheus_interval_ok() is True

    def test_interval_within_limit(self, monitor):
        # 模拟多次采集，间隔正常
        monitor.collector._last_collection_time = 100.0
        monitor.collector.collection_intervals = [5.0, 10.0, 3.0]
        assert monitor.is_prometheus_interval_ok() is True

    def test_interval_exceeds_limit(self, monitor):
        monitor.collector.collection_intervals = [5.0, 20.0, 3.0]
        assert monitor.is_prometheus_interval_ok() is False

    def test_interval_at_boundary(self, monitor):
        monitor.collector.collection_intervals = [15.0, 10.0]
        assert monitor.is_prometheus_interval_ok() is True, "恰好 15 秒应视为合格"

    def test_collected_metrics_contains_connection_info(self, monitor, collector):
        monitor.run_full_check()
        metrics = collector.collected_metrics
        assert metrics["pg_current_connections"] == 30
        assert metrics["pg_max_connections"] == 100
        assert metrics["pg_avg_response_time_ms"] == 25.0


class TestFullCheck:
    """集成测试：完整检查流程"""

    def test_full_check_normal(self, monitor):
        result = monitor.run_full_check()
        assert result["connection_ratio"] == 0.3
        assert result["response_time_ok"] is True
        assert result["slow_queries"] == []
        assert result["prometheus_interval_ok"] is True
        assert result["metrics"]["pg_slow_query_count"] == 0

    def test_full_check_with_issues(self, slow_query_stats, collector):
        mon = PostgresConnectionMonitor(slow_query_stats, collector)
        result = mon.run_full_check()
        assert result["response_time_ok"] is True
        assert len(result["slow_queries"]) == 2
        assert result["metrics"]["pg_slow_query_count"] == 2
