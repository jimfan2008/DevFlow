import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest


# ==============================================================================
# 被测模块
# ==============================================================================

TIME_PRESETS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}

PRESET_KEYS = ["1h", "6h", "24h", "7d", "custom"]


class MonitorDataStore:
    """监控数据存储（内存实现）"""

    def __init__(self):
        self._records: list[dict] = []

    def bulk_insert(self, records: list[dict]):
        self._records.extend(records)

    def query(self, start: datetime, end: datetime, metric: str = None) -> list[dict]:
        results = []
        for r in self._records:
            ts = r["timestamp"]
            if start <= ts <= end:
                if metric is None or r["metric"] == metric:
                    results.append(r)
        return results


class ChartRenderer:
    """图表渲染器"""

    def __init__(self):
        self.render_calls: list[dict] = []
        self.last_data: list[dict] = None

    def render(self, data: list[dict], range_type: str) -> dict:
        self.render_calls.append({"data": data, "range_type": range_type})
        self.last_data = data
        return {"rendered_points": len(data), "range_type": range_type}


class MonitorQueryService:
    """监控数据查询服务"""

    PRESET_KEYS = PRESET_KEYS

    def __init__(self, store: MonitorDataStore = None, chart_renderer: ChartRenderer = None):
        self._store = store or MonitorDataStore()
        self.chart = chart_renderer or ChartRenderer()

    # ------------------------------------------------------------------
    # 预设时间范围查询
    # ------------------------------------------------------------------

    def get_available_presets(self) -> list[str]:
        return list(self.PRESET_KEYS)

    def query_by_preset(self, key: str, metric: str = None) -> dict:
        if key not in TIME_PRESETS:
            raise ValueError(f"不支持的预设时间范围: {key}")
        now = datetime.now(timezone.utc)
        start = now - TIME_PRESETS[key]
        return self._execute_query(start, now, key, metric)

    # ------------------------------------------------------------------
    # 自定义时间范围查询
    # ------------------------------------------------------------------

    def query_custom_range(self, start: datetime, end: datetime, metric: str = None) -> dict:
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError("开始时间和结束时间必须是 datetime 对象")
        if start >= end:
            raise ValueError("开始时间必须早于结束时间")
        span_seconds = (end - start).total_seconds()
        if span_seconds > 365 * 24 * 3600:
            raise ValueError("自定义时间范围不能超过 365 天")
        return self._execute_query(start, end, "custom", metric)

    # ------------------------------------------------------------------
    # 图表趋势接口
    # ------------------------------------------------------------------

    def get_chart_trend(self, key: str, metric: str = None) -> dict:
        if key not in TIME_PRESETS:
            raise ValueError(f"不支持的预设时间范围: {key}")
        result = self.query_by_preset(key, metric)
        result["trend"] = self._compute_trend(result["data"])
        return result

    def get_chart_trend_custom(self, start: datetime, end: datetime, metric: str = None) -> dict:
        result = self.query_custom_range(start, end, metric)
        result["trend"] = self._compute_trend(result["data"])
        return result

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _execute_query(self, start: datetime, end: datetime, key: str, metric: str = None) -> dict:
        t0 = time.perf_counter()
        data = self._store.query(start, end, metric)
        cost_ms = round((time.perf_counter() - t0) * 1000, 2)
        self.chart.render(data, key)
        return {
            "range_type": key,
            "start": start,
            "end": end,
            "count": len(data),
            "data": data,
            "query_time_ms": cost_ms,
        }

    @staticmethod
    def _compute_trend(records: list[dict]) -> list[dict]:
        if not records:
            return []
        buckets: dict[str, list[float]] = {}
        for r in records:
            ts = r["timestamp"]
            bucket_key = ts.replace(second=0, microsecond=0).isoformat()
            buckets.setdefault(bucket_key, []).append(r.get("value", 0))
        trend: list[dict] = []
        for ts_str, vals in sorted(buckets.items()):
            trend.append({
                "timestamp": ts_str,
                "value": round(sum(vals) / len(vals), 2),
                "count": len(vals),
            })
        return trend


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def store():
    """注入跨越 200 分钟的模拟数据（cpu + memory）"""
    s = MonitorDataStore()
    now = datetime.now(timezone.utc)
    records = []
    for i in range(200):
        ts = now - timedelta(minutes=200 - i)
        records.append({"timestamp": ts, "metric": "cpu", "value": 30 + (i % 50)})
        records.append({"timestamp": ts, "metric": "memory", "value": 50 + (i % 30)})
    s.bulk_insert(records)
    return s


@pytest.fixture
def svc(store):
    return MonitorQueryService(store)


@pytest.fixture
def now():
    return datetime.now(timezone.utc)


@pytest.fixture
def empty_svc():
    return MonitorQueryService()


@pytest.fixture
def large_store():
    """注入跨越 7 天的数据（10080 条）"""
    s = MonitorDataStore()
    now = datetime.now(timezone.utc)
    records = []
    for i in range(10080):
        ts = now - timedelta(minutes=10080 - i)
        records.append({"timestamp": ts, "metric": "cpu", "value": 20 + (i % 60)})
    s.bulk_insert(records)
    return s


# ==============================================================================
# 验收标准 1：每种时间范围切换后数据在 ≤3 秒内更新
# ==============================================================================

class TestQueryPerformanceWithin3Seconds:

    def test_1h_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_by_preset("1h")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"1h 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_6h_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_by_preset("6h")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"6h 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_24h_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_by_preset("24h")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"24h 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_7d_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_by_preset("7d")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"7d 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_custom_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        now = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        svc.query_custom_range(now - timedelta(days=3), now)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"自定义查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_rapid_switch_all_presets_each_under_3s(self, large_store):
        svc = MonitorQueryService(large_store)
        for key in ("1h", "6h", "24h", "7d"):
            t0 = time.perf_counter()
            r = svc.query_by_preset(key)
            elapsed = time.perf_counter() - t0
            assert elapsed <= 3.0, f"{key} 切换耗时 {elapsed:.4f}s 超过 3 秒"
            assert r["range_type"] == key

    def test_response_contains_query_time_ms(self, svc):
        r = svc.query_by_preset("1h")
        assert "query_time_ms" in r
        assert isinstance(r["query_time_ms"], (int, float))
        assert r["query_time_ms"] >= 0


# ==============================================================================
# 验收标准 2：支持最近1小时/6小时/24小时/7天/自定义 5 种预设
# ==============================================================================

class TestFivePresetsSupported:

    def test_presets_count_is_five(self, svc):
        presets = svc.get_available_presets()
        assert len(presets) == 5

    def test_presets_include_1h(self, svc):
        assert "1h" in svc.get_available_presets()

    def test_presets_include_6h(self, svc):
        assert "6h" in svc.get_available_presets()

    def test_presets_include_24h(self, svc):
        assert "24h" in svc.get_available_presets()

    def test_presets_include_7d(self, svc):
        assert "7d" in svc.get_available_presets()

    def test_presets_include_custom(self, svc):
        assert "custom" in svc.get_available_presets()

    def test_1h_returns_correct_range(self, svc, now):
        r = svc.query_by_preset("1h")
        expected_start = now - timedelta(hours=1)
        diff = abs((r["start"] - expected_start).total_seconds())
        assert diff < 2.0
        assert r["range_type"] == "1h"

    def test_6h_returns_correct_range(self, svc, now):
        r = svc.query_by_preset("6h")
        expected_start = now - timedelta(hours=6)
        diff = abs((r["start"] - expected_start).total_seconds())
        assert diff < 2.0
        assert r["range_type"] == "6h"

    def test_24h_returns_correct_range(self, svc, now):
        r = svc.query_by_preset("24h")
        expected_start = now - timedelta(hours=24)
        diff = abs((r["start"] - expected_start).total_seconds())
        assert diff < 2.0
        assert r["range_type"] == "24h"

    def test_7d_returns_correct_range(self, svc, now):
        r = svc.query_by_preset("7d")
        expected_start = now - timedelta(days=7)
        diff = abs((r["start"] - expected_start).total_seconds())
        assert diff < 2.0
        assert r["range_type"] == "7d"

    def test_custom_range_uses_provided_boundaries(self, svc, now):
        custom_start = now - timedelta(days=15)
        custom_end = now - timedelta(days=2)
        r = svc.query_custom_range(custom_start, custom_end)
        assert r["start"] == custom_start
        assert r["end"] == custom_end
        assert r["range_type"] == "custom"

    def test_custom_range_with_only_start_raises(self, svc, now):
        with pytest.raises(ValueError, match="必须是 datetime"):
            svc.query_custom_range(now, None)

    def test_custom_range_with_only_end_raises(self, svc, now):
        with pytest.raises(ValueError, match="必须是 datetime"):
            svc.query_custom_range(None, now)

    def test_invalid_preset_raises_value_error(self, svc):
        with pytest.raises(ValueError, match="不支持的预设时间范围"):
            svc.query_by_preset("30d")

    def test_wider_range_returns_more_or_equal_data(self, svc):
        c1 = svc.query_by_preset("1h")["count"]
        c6 = svc.query_by_preset("6h")["count"]
        c24 = svc.query_by_preset("24h")["count"]
        c7d = svc.query_by_preset("7d")["count"]
        assert c1 <= c6 <= c24 <= c7d

    def test_preset_durations_are_correct(self):
        assert abs(TIME_PRESETS["1h"].total_seconds() - 3600) < 0.01
        assert abs(TIME_PRESETS["6h"].total_seconds() - 6 * 3600) < 0.01
        assert abs(TIME_PRESETS["24h"].total_seconds() - 24 * 3600) < 0.01
        assert abs(TIME_PRESETS["7d"].total_seconds() - 7 * 24 * 3600) < 0.01

    def test_custom_start_after_end_raises(self, svc, now):
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            svc.query_custom_range(now, now - timedelta(hours=1))

    def test_custom_equal_start_end_raises(self, svc, now):
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            svc.query_custom_range(now, now)

    def test_custom_span_over_365_days_raises(self, svc, now):
        with pytest.raises(ValueError, match="不能超过"):
            svc.query_custom_range(now - timedelta(days=400), now)

    def test_custom_non_datetime_raises(self, svc, now):
        with pytest.raises(ValueError, match="必须是 datetime"):
            svc.query_custom_range("not-a-date", now)

    def test_custom_with_metric_filter(self, svc, now):
        r = svc.query_custom_range(now - timedelta(hours=1), now, metric="cpu")
        for rec in r["data"]:
            assert rec["metric"] == "cpu"

    def test_custom_response_structure_complete(self, svc, now):
        r = svc.query_custom_range(now - timedelta(hours=3), now)
        for field in ("range_type", "start", "end", "count", "data", "query_time_ms"):
            assert field in r, f"缺少字段: {field}"

    def test_empty_store_custom_returns_zero_count(self, empty_svc, now):
        r = empty_svc.query_custom_range(now - timedelta(hours=1), now)
        assert r["data"] == []
        assert r["count"] == 0


# ==============================================================================
# 验收标准 3：图表趋势展示正常
# ==============================================================================

class TestChartTrendDisplay:

    def test_chart_receives_data_on_preset_query(self, svc):
        svc.query_by_preset("1h")
        assert svc.chart.last_data is not None
        assert len(svc.chart.last_data) > 0

    def test_chart_receives_data_on_custom_query(self, svc, now):
        svc.query_custom_range(now - timedelta(hours=2), now)
        assert svc.chart.last_data is not None

    def test_chart_renders_on_each_switch(self, svc):
        svc.query_by_preset("1h")
        svc.query_by_preset("6h")
        svc.query_by_preset("24h")
        assert len(svc.chart.render_calls) == 3

    def test_trend_field_present_in_chart_response(self, svc):
        r = svc.get_chart_trend("1h")
        assert "trend" in r
        assert isinstance(r["trend"], list)

    def test_trend_non_empty_when_data_exists(self, svc):
        r = svc.get_chart_trend("1h")
        assert len(r["trend"]) > 0, "有数据时趋势列表不应为空"

    def test_trend_empty_when_no_data(self, empty_svc):
        r = empty_svc.get_chart_trend("1h")
        assert r["trend"] == []

    def test_trend_entry_has_required_fields(self, svc):
        r = svc.get_chart_trend("1h")
        entry = r["trend"][0]
        assert "timestamp" in entry
        assert "value" in entry
        assert "count" in entry
        assert isinstance(entry["timestamp"], str)
        assert isinstance(entry["value"], (int, float))
        assert isinstance(entry["count"], int) and entry["count"] > 0

    def test_trend_sorted_by_timestamp_ascending(self, svc):
        r = svc.get_chart_trend("6h")
        trend = r["trend"]
        if len(trend) >= 2:
            for i in range(1, len(trend)):
                ts_prev = datetime.fromisoformat(trend[i - 1]["timestamp"])
                ts_curr = datetime.fromisoformat(trend[i]["timestamp"])
                assert ts_prev < ts_curr

    def test_trend_with_metric_filter(self, svc):
        r = svc.get_chart_trend("1h", metric="cpu")
        assert r["range_type"] == "1h"
        assert isinstance(r["trend"], list)

    def test_trend_available_for_all_presets(self, svc):
        for key in ("1h", "6h", "24h", "7d"):
            r = svc.get_chart_trend(key)
            assert "trend" in r
            assert r["range_type"] == key

    def test_custom_trend(self, svc, now):
        r = svc.get_chart_trend_custom(now - timedelta(hours=2), now)
        assert "trend" in r
        assert r["range_type"] == "custom"

    def test_custom_trend_invalid_range_raises(self, svc, now):
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            svc.get_chart_trend_custom(now, now - timedelta(hours=1))

    def test_trend_response_preserves_all_fields(self, svc):
        r = svc.get_chart_trend("7d")
        expected = {"data", "trend", "count", "range_type", "start", "end", "query_time_ms"}
        assert expected.issubset(set(r.keys()))

    def test_trend_values_show_variation(self, svc):
        r = svc.get_chart_trend("6h", metric="cpu")
        values = [t["value"] for t in r["trend"]]
        assert len(set(values)) > 1, "趋势值应有变化"

    def test_chart_data_points_have_timestamp_and_value(self, svc):
        r = svc.query_by_preset("1h")
        for pt in r["data"]:
            assert "timestamp" in pt
            assert "value" in pt

    def test_chart_data_points_ordered_by_time(self, svc):
        r = svc.query_by_preset("24h")
        timestamps = [p["timestamp"] for p in r["data"]]
        assert timestamps == sorted(timestamps)

    def test_chart_data_length_scales_with_range(self, svc):
        r1h = svc.query_by_preset("1h")
        r24h = svc.query_by_preset("24h")
        assert len(r24h["data"]) > len(r1h["data"])


# ==============================================================================
# 边界与异常场景
# ==============================================================================

class TestEdgeCases:

    def test_empty_store_returns_empty_data(self, empty_svc):
        r = empty_svc.query_by_preset("1h")
        assert r["data"] == []
        assert r["count"] == 0

    def test_future_range_returns_empty(self, empty_svc, now):
        r = empty_svc.query_custom_range(
            now + timedelta(days=1),
            now + timedelta(days=2),
        )
        assert r["data"] == []
        assert r["count"] == 0

    def test_one_minute_range(self, svc, now):
        r = svc.query_custom_range(now - timedelta(minutes=1), now)
        assert r["range_type"] == "custom"
        assert isinstance(r["data"], list)

    def test_metric_none_returns_all_metrics(self, svc):
        r = svc.query_by_preset("1h", metric=None)
        metrics = set(rec["metric"] for rec in r["data"])
        assert len(metrics) >= 2

    def test_cpu_values_within_0_to_100(self, svc):
        r = svc.query_by_preset("24h", metric="cpu")
        for rec in r["data"]:
            assert 0 <= rec["value"] <= 100

    def test_memory_values_within_0_to_100(self, svc):
        r = svc.query_by_preset("24h", metric="memory")
        for rec in r["data"]:
            assert 0 <= rec["value"] <= 100

    def test_data_sorted_by_timestamp_ascending(self, svc):
        r = svc.query_by_preset("6h")
        timestamps = [p["timestamp"] for p in r["data"]]
        assert timestamps == sorted(timestamps)

    def test_custom_range_data_sorted(self, svc, now):
        r = svc.query_custom_range(now - timedelta(hours=2), now)
        timestamps = [p["timestamp"] for p in r["data"]]
        assert timestamps == sorted(timestamps)

    def test_all_five_presets_return_valid_data(self, svc):
        for key in ("1h", "6h", "24h", "7d"):
            r = svc.query_by_preset(key)
            assert isinstance(r["data"], list)
            assert "count" in r
            assert "start" in r
            assert "end" in r
            assert "range_type" in r

    def test_chart_renderer_recorded_range_type(self, svc):
        svc.query_by_preset("6h")
        assert svc.chart.render_calls[-1]["range_type"] == "6h"

    def test_chart_renderer_recorded_custom_range_type(self, svc, now):
        svc.query_custom_range(now - timedelta(hours=3), now)
        assert svc.chart.render_calls[-1]["range_type"] == "custom"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
