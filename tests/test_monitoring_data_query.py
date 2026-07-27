import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class MockMonitoringDataAPI:
    """Mock 监控数据 API，模拟返回不同时间范围的数据"""

    def __init__(self):
        self.call_count = 0
        self.last_query = None

    def query_data(self, start_time, end_time, metric_name="cpu_usage"):
        self.call_count += 1
        self.last_query = {
            "start_time": start_time,
            "end_time": end_time,
            "metric_name": metric_name,
        }
        duration_seconds = (end_time - start_time).total_seconds()
        num_points = max(1, int(duration_seconds / 60))
        data_points = []
        for i in range(num_points):
            data_points.append(
                {
                    "timestamp": (start_time + timedelta(minutes=i)).isoformat(),
                    "value": 50 + (i % 30),
                }
            )
        return {"data": data_points, "total": len(data_points)}


class MonitoringDataQueryService:
    """监控数据查询服务"""

    PRESET_RANGES = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "custom": None,
    }

    def __init__(self, api: MockMonitoringDataAPI):
        self.api = api

    def query_with_preset(self, preset_key: str, metric_name: str = "cpu_usage"):
        now = datetime.now()
        if preset_key == "custom":
            raise ValueError("自定义模式需传入 start_time 和 end_time")
        if preset_key not in self.PRESET_RANGES or self.PRESET_RANGES[preset_key] is None:
            raise ValueError(f"不支持的时间范围预设: {preset_key}")
        start_time = now - self.PRESET_RANGES[preset_key]
        return self.api.query_data(start_time, now, metric_name)

    def query_with_custom_range(
        self, start_time: datetime, end_time: datetime, metric_name: str = "cpu_usage"
    ):
        if start_time >= end_time:
            raise ValueError("起始时间必须早于结束时间")
        return self.api.query_data(start_time, end_time, metric_name)

    def query_and_format_for_chart(
        self, preset_key: str = "1h", metric_name: str = "cpu_usage"
    ):
        result = self.query_with_preset(preset_key, metric_name)
        chart_data = {
            "labels": [point["timestamp"] for point in result["data"]],
            "values": [point["value"] for point in result["data"]],
            "metric": metric_name,
            "preset": preset_key,
        }
        return chart_data


# ---------- Fixtures ----------

@pytest.fixture
def mock_api():
    return MockMonitoringDataAPI()


@pytest.fixture
def service(mock_api):
    return MonitoringDataQueryService(mock_api)


# ---------- Tests ----------

class TestPresetTimeRanges:
    """验证 5 种预设时间范围都能正常查询"""

    def test_query_1_hour_preset(self, service, mock_api):
        result = service.query_with_preset("1h")
        assert result is not None
        assert result["total"] >= 1
        expected_duration = timedelta(hours=1)
        actual_duration = mock_api.last_query["end_time"] - mock_api.last_query["start_time"]
        assert abs(actual_duration.total_seconds() - expected_duration.total_seconds()) < 2

    def test_query_6_hours_preset(self, service, mock_api):
        result = service.query_with_preset("6h")
        assert result is not None
        assert result["total"] >= 1
        expected_duration = timedelta(hours=6)
        actual_duration = mock_api.last_query["end_time"] - mock_api.last_query["start_time"]
        assert abs(actual_duration.total_seconds() - expected_duration.total_seconds()) < 2

    def test_query_24_hours_preset(self, service, mock_api):
        result = service.query_with_preset("24h")
        assert result is not None
        assert result["total"] >= 1
        expected_duration = timedelta(hours=24)
        actual_duration = mock_api.last_query["end_time"] - mock_api.last_query["start_time"]
        assert abs(actual_duration.total_seconds() - expected_duration.total_seconds()) < 2

    def test_query_7_days_preset(self, service, mock_api):
        result = service.query_with_preset("7d")
        assert result is not None
        assert result["total"] >= 1
        expected_duration = timedelta(days=7)
        actual_duration = mock_api.last_query["end_time"] - mock_api.last_query["start_time"]
        assert abs(actual_duration.total_seconds() - expected_duration.total_seconds()) < 2

    def test_all_5_presets_supported(self, service):
        supported_presets = ["1h", "6h", "24h", "7d", "custom"]
        for preset in supported_presets:
            assert preset in service.PRESET_RANGES, f"预设 {preset} 未注册"

    def test_custom_preset_raises_without_params(self, service):
        with pytest.raises(ValueError, match="自定义"):
            service.query_with_preset("custom")

    def test_invalid_preset_raises_error(self, service):
        with pytest.raises(ValueError, match="不支持"):
            service.query_with_preset("30d")


class TestCustomTimeRange:
    """验证自定义时间范围查询"""

    def test_custom_range_success(self, service, mock_api):
        start = datetime.now() - timedelta(hours=3)
        end = datetime.now()
        result = service.query_with_custom_range(start, end)
        assert result is not None
        assert result["total"] >= 1
        assert mock_api.last_query["start_time"] == start
        assert mock_api.last_query["end_time"] == end

    def test_custom_range_start_after_end_raises(self, service):
        start = datetime.now()
        end = start - timedelta(hours=1)
        with pytest.raises(ValueError, match="起始时间"):
            service.query_with_custom_range(start, end)

    def test_custom_range_large_window(self, service, mock_api):
        start = datetime.now() - timedelta(days=30)
        end = datetime.now()
        result = service.query_with_custom_range(start, end)
        assert result["total"] >= 1


class TestQueryPerformance:
    """验证查询响应时间 ≤3 秒"""

    def test_1h_query_under_3_seconds(self, service):
        import time
        t0 = time.perf_counter()
        service.query_with_preset("1h")
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"1小时查询耗时 {elapsed:.3f}s 超过 3 秒"

    def test_6h_query_under_3_seconds(self, service):
        import time
        t0 = time.perf_counter()
        service.query_with_preset("6h")
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"6小时查询耗时 {elapsed:.3f}s 超过 3 秒"

    def test_24h_query_under_3_seconds(self, service):
        import time
        t0 = time.perf_counter()
        service.query_with_preset("24h")
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"24小时查询耗时 {elapsed:.3f}s 超过 3 秒"

    def test_7d_query_under_3_seconds(self, service):
        import time
        t0 = time.perf_counter()
        service.query_with_preset("7d")
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"7天查询耗时 {elapsed:.3f}s 超过 3 秒"

    def test_custom_range_query_under_3_seconds(self, service):
        import time
        start = datetime.now() - timedelta(hours=2)
        end = datetime.now()
        t0 = time.perf_counter()
        service.query_with_custom_range(start, end)
        elapsed = time.perf_counter() - t0
        assert elapsed < 3.0, f"自定义查询耗时 {elapsed:.3f}s 超过 3 秒"


class TestChartDataFormatting:
    """验证图表数据格式正确"""

    def test_chart_has_labels_and_values(self, service):
        chart = service.query_and_format_for_chart("1h")
        assert "labels" in chart
        assert "values" in chart
        assert len(chart["labels"]) == len(chart["values"])
        assert len(chart["labels"]) > 0

    def test_chart_values_are_numeric(self, service):
        chart = service.query_and_format_for_chart("6h")
        for v in chart["values"]:
            assert isinstance(v, (int, float))

    def test_chart_labels_are_iso_timestamps(self, service):
        chart = service.query_and_format_for_chart("24h")
        for label in chart["labels"]:
            datetime.fromisoformat(label)

    def test_chart_includes_metric_name(self, service):
        chart = service.query_and_format_for_chart("7d", "memory_usage")
        assert chart["metric"] == "memory_usage"

    def test_chart_includes_preset_key(self, service):
        chart = service.query_and_format_for_chart("1h")
        assert chart["preset"] == "1h"

    def test_chart_trend_values_change(self, service):
        chart = service.query_and_format_for_chart("7d")
        values = chart["values"]
        unique_values = set(values)
        assert len(unique_values) > 1, "图表趋势数据应有变化"
