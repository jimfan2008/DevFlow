"""监控数据自定义时间范围查询测试"""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest


class MockTimeRangeSelector:
    """模拟时间范围选择器"""

    PRESETS = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "custom": None,
    }

    def __init__(self):
        self.current_preset = "24h"
        self.custom_start = None
        self.custom_end = None

    def set_preset(self, preset_key):
        if preset_key not in self.PRESETS:
            raise ValueError(f"不支持的时间范围: {preset_key}")
        self.current_preset = preset_key
        return self.get_time_range()

    def set_custom_range(self, start: datetime, end: datetime):
        if start >= end:
            raise ValueError("开始时间必须早于结束时间")
        self.current_preset = "custom"
        self.custom_start = start
        self.custom_end = end
        return (start, end)

    def get_time_range(self):
        now = datetime.now()
        if self.current_preset == "custom":
            return (self.custom_start, self.custom_end)
        delta = self.PRESETS[self.current_preset]
        return (now - delta, now)


class MockMonitoringDataProvider:
    """模拟监控数据提供者"""

    def __init__(self):
        self._data_store = {}
        self._query_history = []

    def _generate_mock_data(self, start, end, interval_seconds=60):
        points = []
        current = start
        i = 0
        while current <= end:
            value = 50 + (i % 10) * 5
            points.append({
                "timestamp": current.isoformat(),
                "value": value,
                "cpu": round(30 + (i % 7) * 5, 2),
                "memory": round(60 + (i % 5) * 3, 2),
            })
            current += timedelta(seconds=interval_seconds)
            i += 1
        return points

    def query(self, start, end, metrics=None):
        start_str = start.isoformat() if isinstance(start, datetime) else str(start)
        end_str = end.isoformat() if isinstance(end, datetime) else str(end)
        key = f"{start_str}_{end_str}"
        if key not in self._data_store:
            self._data_store[key] = self._generate_mock_data(start, end)
        query_record = {
            "start": start_str,
            "end": end_str,
            "metrics": metrics,
            "query_time": time.time(),
        }
        self._query_history.append(query_record)
        return self._data_store[key]

    def get_query_history(self):
        return self._query_history


class MonitoringDashboard:
    """监控仪表盘"""

    def __init__(self, data_provider: MockMonitoringDataProvider):
        self.data_provider = data_provider
        self.selector = MockTimeRangeSelector()
        self.current_data = None
        self.last_update_time = None

    def load_data(self, preset_or_range=None):
        start_time = time.time()
        if isinstance(preset_or_range, str):
            start, end = self.selector.set_preset(preset_or_range)
        elif isinstance(preset_or_range, tuple):
            start, end = preset_or_range
        else:
            start, end = self.selector.get_time_range()
        self.current_data = self.data_provider.query(start, end)
        self.last_update_time = time.time() - start_time
        return self.current_data

    def get_trend(self, metric_key="value"):
        if not self.current_data:
            return []
        return [point[metric_key] for point in self.current_data]

    def get_update_time(self):
        return self.last_update_time or 0


@pytest.fixture
def data_provider():
    return MockMonitoringDataProvider()


@pytest.fixture
def dashboard(data_provider):
    return MonitoringDashboard(data_provider)


# ---------- 预设时间范围测试 ----------


class TestPresetTimeRanges:

    def test_5_presets_available(self, dashboard):
        presets = list(MockTimeRangeSelector.PRESETS.keys())
        expected = ["1h", "6h", "24h", "7d", "custom"]
        assert presets == expected

    def test_switch_to_1h_returns_data(self, dashboard):
        result = dashboard.load_data("1h")
        assert isinstance(result, list)
        assert len(result) > 0
        assert "timestamp" in result[0]
        assert "value" in result[0]

    def test_switch_to_6h_returns_data(self, dashboard):
        result = dashboard.load_data("6h")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_switch_to_24h_returns_data(self, dashboard):
        result = dashboard.load_data("24h")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_switch_to_7d_returns_data(self, dashboard):
        result = dashboard.load_data("7d")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_invalid_preset_raises_error(self, dashboard):
        with pytest.raises(ValueError, match="不支持的时间范围"):
            dashboard.selector.set_preset("invalid")


# ---------- 自定义时间范围测试 ----------


class TestCustomTimeRange:

    def test_custom_range_returns_data(self, dashboard):
        end = datetime.now()
        start = end - timedelta(hours=3)
        result = dashboard.load_data((start, end))
        assert isinstance(result, list)
        assert len(result) > 0

    def test_custom_range_invalid_raises_error(self, dashboard):
        start = datetime.now()
        end = start - timedelta(hours=1)
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            dashboard.selector.set_custom_range(start, end)

    def test_custom_range_equal_raises_error(self, dashboard):
        now = datetime.now()
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            dashboard.selector.set_custom_range(now, now)

    def test_custom_range_data_falls_within_range(self, dashboard):
        end = datetime.now()
        start = end - timedelta(hours=2)
        dashboard.load_data((start, end))
        data = dashboard.current_data
        timestamps = [datetime.fromisoformat(p["timestamp"]) for p in data]
        assert all(start <= ts <= end for ts in timestamps)


# ---------- 更新时间 <= 3秒测试 ----------


class TestUpdateTime:

    def test_1h_update_within_3_seconds(self, dashboard):
        dashboard.load_data("1h")
        elapsed = dashboard.get_update_time()
        assert elapsed <= 3.0, f"1h 更新时间 {elapsed:.3f}s 超过 3秒"

    def test_6h_update_within_3_seconds(self, dashboard):
        dashboard.load_data("6h")
        elapsed = dashboard.get_update_time()
        assert elapsed <= 3.0, f"6h 更新时间 {elapsed:.3f}s 超过 3秒"

    def test_24h_update_within_3_seconds(self, dashboard):
        dashboard.load_data("24h")
        elapsed = dashboard.get_update_time()
        assert elapsed <= 3.0, f"24h 更新时间 {elapsed:.3f}s 超过 3秒"

    def test_7d_update_within_3_seconds(self, dashboard):
        dashboard.load_data("7d")
        elapsed = dashboard.get_update_time()
        assert elapsed <= 3.0, f"7d 更新时间 {elapsed:.3f}s 超过 3秒"

    def test_custom_update_within_3_seconds(self, dashboard):
        end = datetime.now()
        start = end - timedelta(hours=3)
        dashboard.load_data((start, end))
        elapsed = dashboard.get_update_time()
        assert elapsed <= 3.0, f"自定义范围更新时间 {elapsed:.3f}s 超过 3秒"


# ---------- 图表趋势展示测试 ----------


class TestChartTrend:

    def test_trend_returns_values(self, dashboard):
        dashboard.load_data("1h")
        trend = dashboard.get_trend("value")
        assert isinstance(trend, list)
        assert len(trend) > 0
        assert all(isinstance(v, (int, float)) for v in trend)

    def test_trend_cpu_metric(self, dashboard):
        dashboard.load_data("6h")
        trend = dashboard.get_trend("cpu")
        assert isinstance(trend, list)
        assert len(trend) > 0

    def test_trend_memory_metric(self, dashboard):
        dashboard.load_data("24h")
        trend = dashboard.get_trend("memory")
        assert isinstance(trend, list)
        assert len(trend) > 0

    def test_trend_values_are_ordered_by_time(self, dashboard):
        dashboard.load_data("1h")
        data = dashboard.current_data
        timestamps = [p["timestamp"] for p in data]
        assert timestamps == sorted(timestamps)

    def test_trend_no_data_returns_empty(self, dashboard):
        dashboard.current_data = None
        trend = dashboard.get_trend("value")
        assert trend == []

    def test_trend_7d_has_enough_points(self, dashboard):
        dashboard.load_data("7d")
        trend = dashboard.get_trend("value")
        expected_min_points = 7 * 24  # at least 1 point per hour
        assert len(trend) >= expected_min_points, f"7天数据点过少: {len(trend)}"


# ---------- 数据提供者查询记录测试 ----------


class TestDataProviderQueryHistory:

    def test_query_history_records_calls(self, dashboard):
        dashboard.load_data("1h")
        dashboard.load_data("6h")
        history = dashboard.data_provider.get_query_history()
        assert len(history) == 2

    def test_query_history_contains_timestamps(self, dashboard):
        dashboard.load_data("24h")
        history = dashboard.data_provider.get_query_history()
        record = history[0]
        assert "start" in record
        assert "end" in record
        assert "query_time" in record
