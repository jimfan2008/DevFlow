"""监控数据自定义时间范围查询 - TDD 测试用例"""

import time
from datetime import datetime, timedelta

import pytest


class MockMonitorAPI:
    """模拟监控数据 API 接口"""

    def __init__(self):
        self.call_count = 0
        self.last_query = None

    def fetch(self, start_time, end_time, metric_name="cpu"):
        self.call_count += 1
        self.last_query = {
            "start": start_time,
            "end": end_time,
            "metric": metric_name,
        }
        total_seconds = (end_time - start_time).total_seconds()
        interval = max(1.0, total_seconds / 100.0)
        points = []
        for i in range(int(total_seconds / interval) + 1):
            ts = start_time + timedelta(seconds=interval * i)
            value = 30.0 + (i * 7.0) % 70.0
            points.append({"timestamp": ts, "value": round(value, 2)})
        return points


class MonitoringService:
    """监控数据查询服务"""

    PRESETS = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "custom": None,
    }

    def __init__(self, api):
        self.api = api

    def query(self, preset="1h", metric="cpu",
              start_time=None, end_time=None):
        if preset == "custom":
            if start_time is None or end_time is None:
                raise ValueError("自定义范围必须指定 start_time 和 end_time")
            if start_time >= end_time:
                raise ValueError("start_time 必须早于 end_time")
            return self._do_query(start_time, end_time, metric, preset)
        if preset not in self.PRESETS:
            raise ValueError("不支持的时间范围: " + preset)
        if self.PRESETS[preset] is None:
            raise ValueError("预设范围无效: " + preset)
        now = datetime.now()
        end_time = now
        start_time = now - self.PRESETS[preset]
        return self._do_query(start_time, end_time, metric, preset)

    def _do_query(self, start_time, end_time, metric, preset):
        data = self.api.fetch(start_time, end_time, metric)
        return {
            "preset": preset,
            "start": start_time,
            "end": end_time,
            "metric": metric,
            "data": data,
            "count": len(data),
        }

    def query_with_timing(self, **kwargs):
        t0 = time.perf_counter()
        result = self.query(**kwargs)
        result["elapsed_seconds"] = time.perf_counter() - t0
        return result


@pytest.fixture
def mock_api():
    return MockMonitorAPI()


@pytest.fixture
def service(mock_api):
    return MonitoringService(mock_api)


# ============================================================
# 1. 5 种预设时间范围测试
# ============================================================

class TestPresetRanges:

    def test_1h_preset_works(self, service):
        result = service.query(preset="1h")
        assert result["preset"] == "1h"
        assert result["count"] > 0

    def test_6h_preset_works(self, service):
        result = service.query(preset="6h")
        assert result["preset"] == "6h"
        assert result["count"] > 0

    def test_24h_preset_works(self, service):
        result = service.query(preset="24h")
        assert result["preset"] == "24h"
        assert result["count"] > 0

    def test_7d_preset_works(self, service):
        result = service.query(preset="7d")
        assert result["preset"] == "7d"
        assert result["count"] > 0

    def test_all_five_presets_exist(self, service):
        keys = list(service.PRESETS.keys())
        assert "1h" in keys
        assert "6h" in keys
        assert "24h" in keys
        assert "7d" in keys
        assert "custom" in keys

    def test_unknown_preset_raises(self, service):
        with pytest.raises(ValueError, match="不支持"):
            service.query(preset="30d")

    def test_1h_span_is_correct(self, service, mock_api):
        service.query(preset="1h")
        span = (mock_api.last_query["end"] - mock_api.last_query["start"]).total_seconds()
        assert abs(span - 3600.0) < 1.0

    def test_6h_span_is_correct(self, service, mock_api):
        service.query(preset="6h")
        span = (mock_api.last_query["end"] - mock_api.last_query["start"]).total_seconds()
        assert abs(span - 21600.0) < 1.0

    def test_24h_span_is_correct(self, service, mock_api):
        service.query(preset="24h")
        span = (mock_api.last_query["end"] - mock_api.last_query["start"]).total_seconds()
        assert abs(span - 86400.0) < 1.0

    def test_7d_span_is_correct(self, service, mock_api):
        service.query(preset="7d")
        span = (mock_api.last_query["end"] - mock_api.last_query["start"]).total_seconds()
        assert abs(span - 604800.0) < 1.0


# ============================================================
# 2. 自定义时间范围测试
# ============================================================

class TestCustomRange:

    def test_custom_range_success(self, service):
        s = datetime(2026, 7, 1, 10, 0, 0)
        e = datetime(2026, 7, 1, 12, 0, 0)
        result = service.query(
            preset="custom",
            start_time=s,
            end_time=e,
        )
        assert result["preset"] == "custom"
        assert result["start"] == s
        assert result["end"] == e
        assert result["count"] > 0

    def test_custom_missing_start_raises(self, service):
        with pytest.raises(ValueError, match="start_time 和 end_time"):
            service.query(preset="custom", end_time=datetime.now())

    def test_custom_missing_end_raises(self, service):
        with pytest.raises(ValueError, match="start_time 和 end_time"):
            service.query(preset="custom", start_time=datetime.now())

    def test_custom_start_after_end_raises(self, service):
        with pytest.raises(ValueError, match="start_time 必须早于"):
            service.query(
                preset="custom",
                start_time=datetime(2026, 7, 10),
                end_time=datetime(2026, 7, 1),
            )

    def test_custom_equal_times_raises(self, service):
        same = datetime(2026, 7, 1, 12, 0, 0)
        with pytest.raises(ValueError, match="start_time 必须早于"):
            service.query(
                preset="custom",
                start_time=same,
                end_time=same,
            )

    def test_custom_with_metric_name(self, service):
        s = datetime(2026, 7, 1, 0, 0, 0)
        e = datetime(2026, 7, 1, 1, 0, 0)
        result = service.query(
            preset="custom",
            start_time=s,
            end_time=e,
            metric="memory",
        )
        assert result["metric"] == "memory"


# ============================================================
# 3. 响应时间 <= 3 秒测试
# ============================================================

class TestResponseTime:

    def test_1h_within_3_seconds(self, service):
        result = service.query_with_timing(preset="1h")
        assert result["elapsed_seconds"] < 3.0

    def test_6h_within_3_seconds(self, service):
        result = service.query_with_timing(preset="6h")
        assert result["elapsed_seconds"] < 3.0

    def test_24h_within_3_seconds(self, service):
        result = service.query_with_timing(preset="24h")
        assert result["elapsed_seconds"] < 3.0

    def test_7d_within_3_seconds(self, service):
        result = service.query_with_timing(preset="7d")
        assert result["elapsed_seconds"] < 3.0

    def test_custom_within_3_seconds(self, service):
        s = datetime(2026, 7, 1)
        e = datetime(2026, 7, 2)
        result = service.query_with_timing(
            preset="custom",
            start_time=s,
            end_time=e,
        )
        assert result["elapsed_seconds"] < 3.0


# ============================================================
# 4. 图表趋势展示测试
# ============================================================

class TestChartTrend:

    def test_each_point_has_timestamp_and_value(self, service):
        result = service.query(preset="1h")
        for point in result["data"]:
            assert "timestamp" in point
            assert "value" in point

    def test_values_are_numeric(self, service):
        result = service.query(preset="6h")
        for point in result["data"]:
            assert isinstance(point["value"], (int, float))

    def test_timestamps_increasing(self, service):
        result = service.query(preset="24h")
        timestamps = [p["timestamp"] for p in result["data"]]
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i - 1]

    def test_values_show_variation(self, service):
        result = service.query(preset="7d")
        values = [p["value"] for p in result["data"]]
        unique_values = set(values)
        assert len(unique_values) > 1

    def test_enough_points_for_7d(self, service):
        result = service.query(preset="7d")
        assert result["count"] >= 50

    def test_enough_points_for_1h(self, service):
        result = service.query(preset="1h")
        assert result["count"] >= 5

    def test_metric_propagated_to_api(self, service, mock_api):
        service.query(preset="1h", metric="disk_io")
        assert mock_api.last_query["metric"] == "disk_io"
