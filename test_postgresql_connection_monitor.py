"""PostgreSQL Connection Status Monitor - TDD Test Suite"""

import time
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Mock classes
# =============================================================================

class MockPSQLConnection:
    """Simulated PostgreSQL database connection."""

    def __init__(self, host="localhost", port=5432, dbname="testdb", user="testuser"):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self._closed = False

    def cursor(self):
        return MockCursor()

    def close(self):
        self._closed = True

    def commit(self):
        pass


class MockCursor:
    """Simulated database cursor."""

    def __init__(self):
        self._rows = []

    def execute(self, query, params=None):
        self._query = query
        self._params = params

        if "pg_stat_activity" in query and "state" in query:
            self._rows = [
                ("idle", 20),
                ("active", 15),
                ("idle in transaction", 10),
            ]
        elif "pg_stat_activity" in query:
            self._rows = [(45, 100)]
        elif "pg_stat_statements" in query or "slow" in query.lower():
            self._rows = [
                ("DELETE FROM logs WHERE created_at < NOW() - INTERVAL '7 days'", 5.2, 2800.0, 45),
                ("SELECT * FROM orders WHERE status = 'pending'", 2.5, 2500.0, 300),
                ("UPDATE inventory SET qty = qty - 1", 1.8, 1200.0, 120),
            ]
        elif "setting" in query and "max_connections" in query:
            self._rows = [("max_connections", "100")]
        elif "response_time" in query:
            self._rows = [(0.035, 0.082, 0.012)]
        return self

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def close(self):
        pass


class PostgreSQLMonitor:
    """PostgreSQL connection status monitor."""

    def __init__(self, connection=None, prometheus_interval=15):
        self.connection = connection or MockPSQLConnection()
        self.prometheus_interval = prometheus_interval
        self._metrics_collected = []
        self._last_collection_time = None

    def get_connection_stats(self):
        """Get current connection statistics."""
        cur = self.connection.cursor()
        cur.execute(
            "SELECT count(*), (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') FROM pg_stat_activity"
        )
        rows = cur.fetchall()
        cur.close()

        current_connections = rows[0][0]
        max_connections = int(rows[0][1]) if rows[0][1] else 100

        return {
            "current_connections": current_connections,
            "max_connections": max_connections,
            "ratio": round(current_connections / max_connections, 4),
        }

    def get_connection_distribution(self):
        """Get connection state distribution."""
        cur = self.connection.cursor()
        cur.execute(
            "SELECT state, count(*) FROM pg_stat_activity GROUP BY state"
        )
        rows = cur.fetchall()
        cur.close()

        distribution = {}
        for row in rows:
            distribution[row[0]] = row[1]
        return distribution

    def get_response_time_stats(self):
        """Get response time statistics."""
        cur = self.connection.cursor()
        cur.execute("SELECT avg_time, max_time, min_time FROM response_time_metrics")
        rows = cur.fetchall()
        cur.close()

        avg_time_ms = float(rows[0][0]) * 1000 if rows[0][0] else 0
        max_time_ms = float(rows[0][1]) * 1000 if rows[0][1] else 0
        min_time_ms = float(rows[0][2]) * 1000 if rows[0][2] else 0

        return {
            "avg_response_time_ms": round(avg_time_ms, 2),
            "max_response_time_ms": round(max_time_ms, 2),
            "min_response_time_ms": round(min_time_ms, 2),
        }

    def get_slow_queries(self, threshold_seconds=1.0):
        """Get slow query list (queries exceeding threshold)."""
        cur = self.connection.cursor()
        cur.execute(
            "SELECT query, total_exec_time, mean_exec_time, call_count FROM pg_stat_statements ORDER BY mean_exec_time DESC"
        )
        rows = cur.fetchall()
        cur.close()

        slow = []
        for row in rows:
            mean_time = float(row[2]) / 1000.0
            if mean_time > threshold_seconds:
                slow.append({
                    "query": row[0],
                    "total_time_seconds": round(float(row[1]), 2),
                    "mean_time_seconds": round(mean_time, 2),
                    "call_count": int(row[3]),
                })
        return slow

    def collect_prometheus_metrics(self):
        """Collect Prometheus metrics."""
        now = time.time()
        if self._last_collection_time and (now - self._last_collection_time) < self.prometheus_interval:
            return self._metrics_collected[-1]

        conn_stats = self.get_connection_stats()
        resp_stats = self.get_response_time_stats()
        slow_queries = self.get_slow_queries()

        metrics = {
            "timestamp": now,
            "pg_connections_current": conn_stats["current_connections"],
            "pg_connections_max": conn_stats["max_connections"],
            "pg_connections_ratio": conn_stats["ratio"],
            "pg_response_time_avg_ms": resp_stats["avg_response_time_ms"],
            "pg_response_time_max_ms": resp_stats["max_response_time_ms"],
            "pg_slow_query_count": len(slow_queries),
        }

        self._last_collection_time = now
        self._metrics_collected.append(metrics)
        return metrics

    def get_monitoring_dashboard(self):
        """Get monitoring dashboard data."""
        conn_stats = self.get_connection_stats()
        resp_stats = self.get_response_time_stats()
        slow_queries = self.get_slow_queries()
        distribution = self.get_connection_distribution()

        return {
            "connection_stats": conn_stats,
            "response_time": resp_stats,
            "slow_queries": slow_queries,
            "connection_distribution": distribution,
            "prometheus_interval_seconds": self.prometheus_interval,
        }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def monitor():
    """Create default monitor instance."""
    return PostgreSQLMonitor(prometheus_interval=15)


@pytest.fixture
def monitor_with_custom_interval():
    """Create monitor with custom collection interval."""
    return PostgreSQLMonitor(prometheus_interval=10)


@pytest.fixture
def monitor_short_interval():
    """Create monitor with short collection interval."""
    return PostgreSQLMonitor(prometheus_interval=1)


# =============================================================================
# Tests: Connection Stats
# =============================================================================

class TestConnectionStats:
    """Connection count statistics tests."""

    def test_current_connections_value(self, monitor):
        """Verify current connection count is returned correctly."""
        stats = monitor.get_connection_stats()
        assert stats["current_connections"] == 45

    def test_max_connections_value(self, monitor):
        """Verify max connection count is returned correctly."""
        stats = monitor.get_connection_stats()
        assert stats["max_connections"] == 100

    def test_ratio_calculation(self, monitor):
        """Verify connection ratio calculation."""
        stats = monitor.get_connection_stats()
        expected_ratio = 45 / 100
        assert abs(stats["ratio"] - expected_ratio) < 0.0001

    def test_ratio_boundary_zero(self):
        """Verify ratio boundary when connections are zero."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(0, 100)]
        mock_conn.cursor.return_value = mock_cursor

        monitor = PostgreSQLMonitor(connection=mock_conn)
        stats = monitor.get_connection_stats()
        assert stats["ratio"] == 0.0

    def test_ratio_boundary_full(self):
        """Verify ratio boundary when connections are at max."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(100, 100)]
        mock_conn.cursor.return_value = mock_cursor

        monitor = PostgreSQLMonitor(connection=mock_conn)
        stats = monitor.get_connection_stats()
        assert abs(stats["ratio"] - 1.0) < 0.0001


# =============================================================================
# Tests: Connection Distribution
# =============================================================================

class TestConnectionDistribution:
    """Connection state distribution tests."""

    def test_distribution_has_expected_states(self, monitor):
        """Verify returned states include expected types."""
        dist = monitor.get_connection_distribution()
        assert "idle" in dist
        assert "active" in dist
        assert "idle in transaction" in dist

    def test_distribution_counts_sum_to_total(self, monitor):
        """Verify sum of all state counts equals total connections."""
        dist = monitor.get_connection_distribution()
        total = sum(dist.values())
        assert total == 45

    def test_distribution_idle_count(self, monitor):
        """Verify idle state connection count."""
        dist = monitor.get_connection_distribution()
        assert dist["idle"] == 20

    def test_distribution_active_count(self, monitor):
        """Verify active state connection count."""
        dist = monitor.get_connection_distribution()
        assert dist["active"] == 15


# =============================================================================
# Tests: Response Time
# =============================================================================

class TestResponseTime:
    """Response time tests."""

    def test_avg_response_time_under_threshold(self, monitor):
        """Verify average response time <= 50ms."""
        stats = monitor.get_response_time_stats()
        assert stats["avg_response_time_ms"] <= 50.0

    def test_avg_response_time_value(self, monitor):
        """Verify specific average response time value."""
        stats = monitor.get_response_time_stats()
        assert abs(stats["avg_response_time_ms"] - 35.0) < 0.01

    def test_max_response_time_value(self, monitor):
        """Verify max response time value."""
        stats = monitor.get_response_time_stats()
        assert abs(stats["max_response_time_ms"] - 82.0) < 0.01

    def test_min_response_time_value(self, monitor):
        """Verify min response time value."""
        stats = monitor.get_response_time_stats()
        assert abs(stats["min_response_time_ms"] - 12.0) < 0.01

    def test_response_time_threshold_exceeded(self):
        """Verify detection when average response time > 50ms."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(0.075, 0.120, 0.030)]
        mock_conn.cursor.return_value = mock_cursor

        monitor = PostgreSQLMonitor(connection=mock_conn)
        stats = monitor.get_response_time_stats()
        assert stats["avg_response_time_ms"] > 50.0


# =============================================================================
# Tests: Slow Queries
# =============================================================================

class TestSlowQueries:
    """Slow query tests."""

    def test_slow_queries_returns_list(self, monitor):
        """Verify slow queries returns a list type."""
        slow = monitor.get_slow_queries()
        assert isinstance(slow, list)

    def test_slow_queries_count(self, monitor):
        """Verify slow query count (>1 second)."""
        slow = monitor.get_slow_queries(threshold_seconds=1.0)
        assert len(slow) == 3

    def test_slow_query_has_required_fields(self, monitor):
        """Verify slow query entries contain required fields."""
        slow = monitor.get_slow_queries()
        required_fields = {"query", "total_time_seconds", "mean_time_seconds", "call_count"}
        for item in slow:
            assert set(item.keys()) == required_fields

    def test_slow_query_mean_time_above_threshold(self, monitor):
        """Verify all slow queries have mean time > 1 second."""
        slow = monitor.get_slow_queries(threshold_seconds=1.0)
        for item in slow:
            assert item["mean_time_seconds"] > 1.0

    def test_slow_query_first_item(self, monitor):
        """Verify sort order: slow queries ordered by mean time descending."""
        slow = monitor.get_slow_queries()
        assert slow[0]["query"] == "DELETE FROM logs WHERE created_at < NOW() - INTERVAL '7 days'"
        assert slow[0]["mean_time_seconds"] == 2.8

    def test_no_slow_queries_with_high_threshold(self, monitor):
        """Verify no slow queries returned with high threshold."""
        slow = monitor.get_slow_queries(threshold_seconds=10.0)
        assert len(slow) == 0

    def test_custom_threshold(self, monitor):
        """Verify custom threshold works correctly."""
        slow = monitor.get_slow_queries(threshold_seconds=2.0)
        assert len(slow) == 2


# =============================================================================
# Tests: Prometheus Metrics
# =============================================================================

class TestPrometheusMetrics:
    """Prometheus metrics collection tests."""

    def test_prometheus_interval_default(self, monitor):
        """Verify default collection interval <= 15 seconds."""
        assert monitor.prometheus_interval <= 15

    def test_prometheus_interval_custom(self, monitor_with_custom_interval):
        """Verify custom collection interval."""
        assert monitor_with_custom_interval.prometheus_interval == 10

    def test_prometheus_metrics_structure(self, monitor):
        """Verify Prometheus metrics contain required fields."""
        metrics = monitor.collect_prometheus_metrics()
        required_keys = {
            "timestamp",
            "pg_connections_current",
            "pg_connections_max",
            "pg_connections_ratio",
            "pg_response_time_avg_ms",
            "pg_response_time_max_ms",
            "pg_slow_query_count",
        }
        assert set(metrics.keys()) == required_keys

    def test_prometheus_metrics_values(self, monitor):
        """Verify Prometheus metric values are correct."""
        metrics = monitor.collect_prometheus_metrics()
        assert metrics["pg_connections_current"] == 45
        assert metrics["pg_connections_max"] == 100
        assert metrics["pg_slow_query_count"] == 3

    def test_prometheus_interval_enforcement(self, monitor_short_interval):
        """Verify no re-collection within interval."""
        m = monitor_short_interval
        first = m.collect_prometheus_metrics()

        with patch("time.time", return_value=first["timestamp"] + 0.5):
            second = m.collect_prometheus_metrics()

        assert first is second

    def test_prometheus_collects_after_interval(self, monitor_short_interval):
        """Verify re-collection after interval elapses."""
        m = monitor_short_interval
        first = m.collect_prometheus_metrics()

        with patch("time.time", return_value=first["timestamp"] + 2):
            second = m.collect_prometheus_metrics()

        assert first is not second
        assert second["timestamp"] > first["timestamp"]


# =============================================================================
# Tests: Monitoring Dashboard
# =============================================================================

class TestMonitoringDashboard:
    """Monitoring dashboard integration tests."""

    def test_dashboard_has_all_sections(self, monitor):
        """Verify dashboard contains all data sections."""
        dashboard = monitor.get_monitoring_dashboard()
        expected_sections = {
            "connection_stats",
            "response_time",
            "slow_queries",
            "connection_distribution",
            "prometheus_interval_seconds",
        }
        assert set(dashboard.keys()) == expected_sections

    def test_dashboard_connection_ratio_visible(self, monitor):
        """Verify connection ratio is displayed in dashboard."""
        dashboard = monitor.get_monitoring_dashboard()
        assert "ratio" in dashboard["connection_stats"]
        assert dashboard["connection_stats"]["ratio"] == 0.45

    def test_dashboard_avg_response_time_under_limit(self, monitor):
        """Verify average response time in dashboard <= 50ms."""
        dashboard = monitor.get_monitoring_dashboard()
        assert dashboard["response_time"]["avg_response_time_ms"] <= 50.0

    def test_dashboard_slow_queries_present(self, monitor):
        """Verify slow queries list is present in dashboard."""
        dashboard = monitor.get_monitoring_dashboard()
        slow = dashboard["slow_queries"]
        assert isinstance(slow, list)
        assert len(slow) > 0
        for q in slow:
            assert q["mean_time_seconds"] > 1.0

    def test_dashboard_prometheus_interval(self, monitor):
        """Verify Prometheus collection interval is shown in dashboard."""
        dashboard = monitor.get_monitoring_dashboard()
        assert dashboard["prometheus_interval_seconds"] <= 15


# =============================================================================
# Tests: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_connection_ratio_precision(self):
        """Verify ratio precision."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(33, 7)]
        mock_conn.cursor.return_value = mock_cursor

        monitor = PostgreSQLMonitor(connection=mock_conn)
        stats = monitor.get_connection_stats()
        assert abs(stats["ratio"] - (33 / 7)) < 0.0001

    def test_empty_slow_queries_list(self):
        """Verify empty list returned when no slow queries."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("SELECT 1", 0.1, 0.5, 1000),
        ]
        mock_conn.cursor.return_value = mock_cursor

        monitor = PostgreSQLMonitor(connection=mock_conn)
        slow = monitor.get_slow_queries(threshold_seconds=1.0)
        assert slow == []

    def test_monitoring_with_default_connection(self):
        """Verify monitor works with default Mock connection."""
        monitor = PostgreSQLMonitor()
        stats = monitor.get_connection_stats()
        assert "ratio" in stats
        assert 0 <= stats["ratio"] <= 1

    def test_response_time_zero_values(self):
        """Verify handling when response times are zero."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(0, 0, 0)]
        mock_conn.cursor.return_value = mock_cursor

        monitor = PostgreSQLMonitor(connection=mock_conn)
        stats = monitor.get_response_time_stats()
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["max_response_time_ms"] == 0.0
        assert stats["min_response_time_ms"] == 0.0

    def test_prometheus_reuses_metrics_within_interval(self):
        """Verify cached metrics returned within collection interval."""
        m = PostgreSQLMonitor(prometheus_interval=30)
        first = m.collect_prometheus_metrics()

        with patch("time.time", return_value=first["timestamp"] + 5):
            second = m.collect_prometheus_metrics()

        assert first is second

    def test_full_dashboard_integration(self):
        """Full dashboard integration test."""
        monitor = PostgreSQLMonitor(prometheus_interval=15)
        dashboard = monitor.get_monitoring_dashboard()

        conn = dashboard["connection_stats"]
        assert conn["current_connections"] == 45
        assert conn["max_connections"] == 100
        assert abs(conn["ratio"] - 0.45) < 0.0001

        resp = dashboard["response_time"]
        assert resp["avg_response_time_ms"] <= 50.0

        slow = dashboard["slow_queries"]
        assert len(slow) == 3
        for q in slow:
            assert q["mean_time_seconds"] > 1.0

        dist = dashboard["connection_distribution"]
        assert sum(dist.values()) == 45

        assert dashboard["prometheus_interval_seconds"] <= 15
