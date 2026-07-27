"""监控数据自定义时间范围查询 - TDD 测试用例"""

import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class MockMonitoringService:
    """模拟监控数据服务"""

    def __init__(self):
        self._data_store = {}
        self._query_time = 0.5  # 模拟查询耗时（秒）

    def set_query_time(self, seconds):
        self._query_time = seconds

    def query_data(self, start_time: datetime, end_time: datetime, metric: str = "cpu") -> list:
        time.sleep(self._query_time)
        duration_seconds = int((end_time - start_time).total_seconds())
        points = []
        step = max(1, duration_seconds // 60)
        current = start_time
        value = 30.0
        while current <= end_time:
            value = min(100.0, max(5.0, value + (hash(current.isoformat()) % 20 - 10)) / 10.0)
            points.append({
                "timestamp": current.isoformat(),
                "value": round(value, 2),
                "metric": metric,
            })
            current += timedelta(seconds=step)
        return points

    def get_supported_presets(self) -> list:
        return ["1h", "6h", "24h", "7d", "custom"]


class MockChartRenderer:
    """模拟图表渲染器"""

    def __init__(self):
        self.rendered_data = None
        self.render_count = 0

    def render(self, data: list) -> dict:
        self.render_count += 1
        if not data:
            return {"status": "empty"}
        self.rendered_data = {
            "points_count": len(data),
            "start_time": data[0]["timestamp"],
            "end_time": data[-1]["timestamp"],
            "min_value": min(p["value"] for p in data),
            "max_value": max(p["value"] for p in data),
            "trending_up": data[-1]["value"] > data[0]["value"],
        }
        return self.rendered_data


@pytest.fixture
def monitoring_service():
    return MockMonitoringService()


@pytest.fixture
def chart_renderer():
    return MockChartRenderer()


@pytest.fixture
def now():
    return datetime(2026, 7, 16, 12, 0, 0)


class TestTimeRangePresets:
    """测试5种预设时间范围"""

    def _build_range(self, preset: str, now: datetime) -> tuple:
        ranges = {
            "1h": (now - timedelta(hours=1), now),
            "6h": (now - timedelta(hours=6), now),
            "24h": (now - timedelta(hours=24), now),
            "7d": (now - timedelta(days=7), now),
        }
        if preset not in ranges:
            raise ValueError(f"不支持的预设: {preset}")
        return ranges[preset]

    def test_presets_support_five_types(self, monitoring_service):
        presets = monitoring_service.get_supported_presets()
        assert len(presets) == 5
        assert "1h" in presets
        assert "6h" in presets
        assert "24h" in presets
        assert "7d" in presets
        assert "custom" in presets

    def test_query_1_hour_range(self, monitoring_service, now):
        start, end = self._build_range("1h", now)
        data = monitoring_service.query_data(start, end)
        assert len(data) > 0
        assert all("timestamp" in p for p in data)
        assert all("value" in p for p in data)
        assert all("metric" in p for p in data)

    def test_query_6_hours_range(self, monitoring_service, now):
        start, end = self._build_range("6h", now)
        data = monitoring_service.query_data(start, end)
        assert len(data) > 6

    def test_query_24_hours_range(self, monitoring_service, now):
        start, end = self._build_range("24h", now)
        data = monitoring_service.query_data(start, end)
        assert len(data) > 60

    def test_query_7_days_range(self, monitoring_service, now):
        start, end = self._build_range("7d", now)
        data = monitoring_service.query_data(start, end)
        assert len(data) >= 60

    def test_invalid_preset_raises(self, now):
        with pytest.raises(ValueError, match="不支持的预设"):
            self._build_range("30d", now)


class TestQueryPerformance:
    """测试数据更新 ≤3秒"""

    def test_query_within_3_seconds(self, monitoring_service, now):
        start = now - timedelta(hours=1)
        end = now
        elapsed = time.time()
        monitoring_service.query_data(start, end)
        elapsed = time.time() - elapsed
        assert elapsed < 3.0, f"查询耗时 {elapsed:.2f}s 超过 3 秒限制"

    def test_fast_preset_switch(self, monitoring_service, now):
        presets = ["1h", "6h", "24h", "7d"]
        for preset in presets:
            start, end = {
                "1h": (now - timedelta(hours=1), now),
                "6h": (now - timedelta(hours=6), now),
                "24h": (now - timedelta(hours=24), now),
                "7d": (now - timedelta(days=7), now),
            }[preset]
            elapsed = time.time()
            monitoring_service.query_data(start, end)
            elapsed = time.time() - elapsed
            assert elapsed < 3.0, f"预设 {preset} 切换耗时 {elapsed:.2f}s 超过 3 秒"

    def test_slow_service_flagged(self, monitoring_service, now):
        monitoring_service.set_query_time(3.5)
        start = now - timedelta(hours=1)
        end = now
        with pytest.raises(AssertionError):
            elapsed = time.time()
            monitoring_service.query_data(start, end)
            elapsed = time.time() - elapsed
            assert elapsed < 3.0


class TestCustomTimeRange:
    """测试自定义时间范围"""

    def test_custom_range_valid(self, monitoring_service):
        start = datetime(2026, 7, 15, 8, 0, 0)
        end = datetime(2026, 7, 15, 18, 0, 0)
        data = monitoring_service.query_data(start, end)
        assert len(data) > 0
        assert data[0]["timestamp"] >= start.isoformat()
        assert data[-1]["timestamp"] <= end.isoformat()

    def test_custom_range_start_before_end(self, monitoring_service):
        start = datetime(2026, 7, 15, 8, 0, 0)
        end = datetime(2026, 7, 15, 8, 0, 0)
        data = monitoring_service.query_data(start, end)
        assert len(data) >= 1

    def test_custom_range_crosses_midnight(self, monitoring_service):
        start = datetime(2026, 7, 15, 22, 0, 0)
        end = datetime(2026, 7, 16, 2, 0, 0)
        data = monitoring_service.query_data(start, end)
        assert len(data) > 0


class TestChartTrendDisplay:
    """测试图表趋势展示"""

    def test_chart_renders_with_data(self, chart_renderer, monitoring_service, now):
        start = now - timedelta(hours=6)
        end = now
        data = monitoring_service.query_data(start, end)
        result = chart_renderer.render(data)
        assert result["points_count"] == len(data)
        assert result["start_time"] is not None
        assert result["end_time"] is not None
        assert "min_value" in result
        assert "max_value" in result
        assert "trending_up" in result

    def test_chart_renders_empty_data(self, chart_renderer):
        result = chart_renderer.render([])
        assert result["status"] == "empty"

    def test_chart_trend_up(self, chart_renderer):
        data = [
            {"timestamp": "2026-07-16T10:00:00", "value": 30.0},
            {"timestamp": "2026-07-16T10:10:00", "value": 50.0},
            {"timestamp": "2026-07-16T10:20:00", "value": 70.0},
        ]
        result = chart_renderer.render(data)
        assert result["trending_up"] is True
        assert result["min_value"] == 30.0
        assert result["max_value"] == 70.0

    def test_chart_trend_down(self, chart_renderer):
        data = [
            {"timestamp": "2026-07-16T10:00:00", "value": 80.0},
            {"timestamp": "2026-07-16T10:10:00", "value": 50.0},
            {"timestamp": "2026-07-16T10:20:00", "value": 20.0},
        ]
        result = chart_renderer.render(data)
        assert result["trending_up"] is False
        assert result["min_value"] == 20.0
        assert result["max_value"] == 80.0

    def test_chart_render_count_increments(self, chart_renderer):
        assert chart_renderer.render_count == 0
        chart_renderer.render([{"timestamp": "a", "value": 1}])
        assert chart_renderer.render_count == 1
        chart_renderer.render([{"timestamp": "b", "value": 2}])
        assert chart_renderer.render_count == 2


class TestFullWorkflow:
    """端到端工作流测试"""

    def test_full_flow_preset_switch(self, monitoring_service, chart_renderer, now):
        presets = ["1h", "6h", "24h", "7d"]
        for preset in presets:
            start, end = {
                "1h": (now - timedelta(hours=1), now),
                "6h": (now - timedelta(hours=6), now),
                "24h": (now - timedelta(hours=24), now),
                "7d": (now - timedelta(days=7), now),
            }[preset]
            data = monitoring_service.query_data(start, end)
            result = chart_renderer.render(data)
            assert result["points_count"] > 0

    def test_full_flow_custom_range(self, monitoring_service, chart_renderer):
        start = datetime(2026, 7, 10, 0, 0, 0)
        end = datetime(2026, 7, 16, 0, 0, 0)
        data = monitoring_service.query_data(start, end)
        result = chart_renderer.render(data)
        assert result["points_count"] >= 60
        assert result["min_value"] >= 0.5
        assert result["max_value"] <= 10.0
