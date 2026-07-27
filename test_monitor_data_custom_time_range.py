"""监控数据自定义时间范围查询 — TDD 测试用例"""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest

# ==============================================================================
# 被测模块（可独立运行）
# ==============================================================================

# 5 种预设时间范围常量
TIME_PRESETS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


class MonitorDataStore:
    """监控数据仓储（内存实现）"""

    def __init__(self):
        self._records: list[dict] = []

    def bulk_insert(self, records: list[dict]):
        self._records.extend(records)

    def query(self, start: datetime, end: datetime, metric: str = None) -> list[dict]:
        """按时间范围查询，可选指标过滤"""
        results = []
        for r in self._records:
            ts = r["timestamp"]
            if start <= ts <= end:
                if metric is None or r["metric"] == metric:
                    results.append(r)
        return results

    def get_all(self) -> list[dict]:
        return list(self._records)


class MonitorQueryService:
    """监控数据查询服务"""

    PRESET_KEYS = ["1h", "6h", "24h", "7d", "custom"]

    def __init__(self, store: MonitorDataStore = None):
        self._store = store or MonitorDataStore()

    # ------------------------------------------------------------------
    # 预设查询
    # ------------------------------------------------------------------

    def get_presets(self) -> list[str]:
        return list(self.PRESET_KEYS)

    def query_preset(self, key: str, metric: str = None) -> dict:
        if key not in TIME_PRESETS:
            raise ValueError(f"不支持的预设时间范围: {key}")
        now = datetime.now()
        start = now - TIME_PRESETS[key]
        return self._execute_query(start, now, key, metric)

    # ------------------------------------------------------------------
    # 自定义时间范围查询
    # ------------------------------------------------------------------

    def query_custom(self, start: datetime, end: datetime, metric: str = None) -> dict:
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            raise ValueError("开始时间和结束时间必须是 datetime 对象")
        if start >= end:
            raise ValueError("开始时间必须早于结束时间")
        span_seconds = (end - start).total_seconds()
        if span_seconds > 365 * 24 * 3600:
            raise ValueError("时间范围不能超过 365 天")
        return self._execute_query(start, end, "custom", metric)

    # ------------------------------------------------------------------
    # 图表趋势
    # ------------------------------------------------------------------

    def get_trend(self, key: str, metric: str = None) -> dict:
        if key not in TIME_PRESETS:
            raise ValueError(f"不支持的预设时间范围: {key}")
        result = self.query_preset(key, metric)
        result["trend"] = self._aggregate_to_trend(result["data"])
        return result

    def get_trend_custom(self, start: datetime, end: datetime, metric: str = None) -> dict:
        result = self.query_custom(start, end, metric)
        result["trend"] = self._aggregate_to_trend(result["data"])
        return result

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _execute_query(self, start: datetime, end: datetime, key: str, metric: str = None) -> dict:
        t0 = time.perf_counter()
        data = self._store.query(start, end, metric)
        cost_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "range_type": key,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "count": len(data),
            "data": data,
            "query_time_ms": cost_ms,
        }

    @staticmethod
    def _aggregate_to_trend(records: list[dict]) -> list[dict]:
        """将原始记录按分钟聚合为趋势数据点"""
        if not records:
            return []
        buckets: dict[datetime, list[float]] = {}
        for r in records:
            ts = r["timestamp"]
            bucket = ts.replace(second=0, microsecond=0)
            buckets.setdefault(bucket, []).append(r.get("value", 0))
        trend = []
        for ts, vals in sorted(buckets.items()):
            trend.append({
                "timestamp": ts.isoformat(),
                "value": round(sum(vals) / len(vals), 2),
                "count": len(vals),
            })
        return trend


# ==============================================================================
# Fixtures（测试数据自包含）
# ==============================================================================

@pytest.fixture
def store():
    """注入跨越 200 分钟的模拟监控数据（cpu + memory）"""
    s = MonitorDataStore()
    now = datetime.now()
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
    return datetime.now()


@pytest.fixture
def empty_svc():
    """无数据的空服务"""
    return MonitorQueryService()


@pytest.fixture
def large_store():
    """注入跨越 7 天（10080 分钟）的大数据仓储"""
    s = MonitorDataStore()
    now = datetime.now()
    records = []
    for i in range(10080):
        ts = now - timedelta(minutes=10080 - i)
        records.append({"timestamp": ts, "metric": "cpu", "value": 20 + (i % 60)})
    s.bulk_insert(records)
    return s


# ==============================================================================
# 验收标准 1：支持 5 种预设
# ==============================================================================

class TestFivePresetsSupported:

    def test_presets_count_is_five(self, svc):
        presets = svc.get_presets()
        assert len(presets) == 5

    def test_presets_contain_1h(self, svc):
        assert "1h" in svc.get_presets()

    def test_presets_contain_6h(self, svc):
        assert "6h" in svc.get_presets()

    def test_presets_contain_24h(self, svc):
        assert "24h" in svc.get_presets()

    def test_presets_contain_7d(self, svc):
        assert "7d" in svc.get_presets()

    def test_presets_contain_custom(self, svc):
        assert "custom" in svc.get_presets()

    def test_each_preset_returns_valid_response(self, svc):
        for key in ("1h", "6h", "24h", "7d"):
            r = svc.query_preset(key)
            assert r["range_type"] == key
            assert isinstance(r["data"], list)
            assert "count" in r
            assert "start" in r
            assert "end" in r

    def test_wider_range_returns_more_or_equal_data(self, svc):
        c1 = svc.query_preset("1h")["count"]
        c6 = svc.query_preset("6h")["count"]
        c24 = svc.query_preset("24h")["count"]
        c7d = svc.query_preset("7d")["count"]
        assert c1 <= c6 <= c24 <= c7d

    def test_invalid_preset_raises_value_error(self, svc):
        with pytest.raises(ValueError, match="不支持的预设时间范围"):
            svc.query_preset("30d")


# ==============================================================================
# 验收标准 2：自定义时间范围查询
# ==============================================================================

class TestCustomTimeRange:

    def test_custom_range_returns_valid_response(self, svc, now):
        r = svc.query_custom(now - timedelta(hours=2), now)
        assert r["range_type"] == "custom"
        assert isinstance(r["data"], list)
        assert "count" in r

    def test_custom_respects_start_boundary(self, svc, now):
        start = now - timedelta(minutes=30)
        r = svc.query_custom(start, now)
        for rec in r["data"]:
            assert rec["timestamp"] >= start

    def test_custom_respects_end_boundary(self, svc, now):
        end = now - timedelta(minutes=30)
        r = svc.query_custom(now - timedelta(hours=2), end)
        for rec in r["data"]:
            assert rec["timestamp"] <= end

    def test_start_after_end_raises(self, svc, now):
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            svc.query_custom(now, now - timedelta(hours=1))

    def test_equal_start_and_end_raises(self, svc, now):
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            svc.query_custom(now, now)

    def test_span_over_365_days_raises(self, svc, now):
        with pytest.raises(ValueError, match="不能超过"):
            svc.query_custom(now - timedelta(days=400), now)

    def test_non_datetime_raises(self, svc, now):
        with pytest.raises(ValueError, match="必须是 datetime"):
            svc.query_custom("not-a-date", now)

    def test_custom_with_metric_filter(self, svc, now):
        r = svc.query_custom(now - timedelta(hours=1), now, metric="cpu")
        for rec in r["data"]:
            assert rec["metric"] == "cpu"

    def test_custom_response_has_iso_datetime(self, svc, now):
        start = now - timedelta(hours=3)
        r = svc.query_custom(start, now)
        assert datetime.fromisoformat(r["start"]) == start
        assert datetime.fromisoformat(r["end"]) == now

    def test_custom_empty_range_returns_zero_count(self, empty_svc, now):
        r = empty_svc.query_custom(now - timedelta(hours=1), now)
        assert r["data"] == []
        assert r["count"] == 0


# ==============================================================================
# 验收标准 3：数据在 ≤3 秒内更新
# ==============================================================================

class TestQueryPerformance:

    def test_1h_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_preset("1h")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"1h 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_6h_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_preset("6h")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"6h 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_24h_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_preset("24h")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"24h 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_7d_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        t0 = time.perf_counter()
        svc.query_preset("7d")
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"7d 查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_custom_query_under_3_seconds(self, large_store):
        svc = MonitorQueryService(large_store)
        now = datetime.now()
        t0 = time.perf_counter()
        svc.query_custom(now - timedelta(days=3), now)
        elapsed = time.perf_counter() - t0
        assert elapsed <= 3.0, f"自定义查询耗时 {elapsed:.4f}s 超过 3 秒"

    def test_rapid_switch_all_presets_each_under_3s(self, large_store):
        svc = MonitorQueryService(large_store)
        for key in ("1h", "6h", "24h", "7d"):
            t0 = time.perf_counter()
            r = svc.query_preset(key)
            elapsed = time.perf_counter() - t0
            assert elapsed <= 3.0, f"{key} 切换耗时 {elapsed:.4f}s 超过 3 秒"
            assert r["range_type"] == key

    def test_response_includes_query_time_ms(self, svc):
        r = svc.query_preset("1h")
        assert "query_time_ms" in r
        assert isinstance(r["query_time_ms"], (int, float))
        assert r["query_time_ms"] >= 0


# ==============================================================================
# 验收标准 4：图表趋势展示正常
# ==============================================================================

class TestChartTrendDisplay:

    def test_trend_field_present_in_response(self, svc):
        r = svc.get_trend("1h")
        assert "trend" in r
        assert isinstance(r["trend"], list)

    def test_trend_non_empty_when_data_exists(self, svc):
        r = svc.get_trend("1h")
        assert len(r["trend"]) > 0, "有数据时趋势列表不应为空"

    def test_trend_empty_when_no_data(self, empty_svc):
        r = empty_svc.get_trend("1h")
        assert r["trend"] == []

    def test_trend_entry_has_required_fields(self, svc):
        r = svc.get_trend("1h")
        entry = r["trend"][0]
        assert "timestamp" in entry
        assert "value" in entry
        assert "count" in entry
        assert isinstance(entry["timestamp"], str)
        assert isinstance(entry["value"], (int, float))
        assert isinstance(entry["count"], int) and entry["count"] > 0

    def test_trend_sorted_by_timestamp_ascending(self, svc):
        r = svc.get_trend("6h")
        trend = r["trend"]
        if len(trend) >= 2:
            for i in range(1, len(trend)):
                ts_prev = datetime.fromisoformat(trend[i - 1]["timestamp"])
                ts_curr = datetime.fromisoformat(trend[i]["timestamp"])
                assert ts_prev < ts_curr, "趋势数据应按时间升序排列"

    def test_trend_with_metric_filter(self, svc):
        r = svc.get_trend("1h", metric="cpu")
        assert r["range_type"] == "1h"
        assert isinstance(r["trend"], list)

    def test_trend_available_for_all_presets(self, svc):
        for key in ("1h", "6h", "24h", "7d"):
            r = svc.get_trend(key)
            assert "trend" in r
            assert r["range_type"] == key

    def test_custom_trend(self, svc, now):
        r = svc.get_trend_custom(now - timedelta(hours=2), now)
        assert "trend" in r
        assert r["range_type"] == "custom"

    def test_custom_trend_invalid_range_raises(self, svc, now):
        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            svc.get_trend_custom(now, now - timedelta(hours=1))

    def test_trend_response_preserves_all_fields(self, svc):
        r = svc.get_trend("7d")
        expected_fields = {"data", "trend", "count", "range_type", "start", "end", "query_time_ms"}
        actual_fields = set(r.keys())
        assert expected_fields.issubset(actual_fields)

    def test_trend_values_show_variation(self, svc):
        r = svc.get_trend("6h", metric="cpu")
        values = [t["value"] for t in r["trend"]]
        unique_values = set(values)
        assert len(unique_values) > 1, "趋势值应有变化，不应全部相同"


# ==============================================================================
# 边界与异常场景
# ==============================================================================

class TestEdgeCases:

    def test_empty_store_returns_empty_data(self, empty_svc):
        r = empty_svc.query_preset("1h")
        assert r["data"] == []
        assert r["count"] == 0

    def test_future_range_returns_empty(self, empty_svc, now):
        r = empty_svc.query_custom(
            now + timedelta(days=1),
            now + timedelta(days=2),
        )
        assert r["data"] == []
        assert r["count"] == 0

    def test_one_minute_range(self, svc, now):
        r = svc.query_custom(now - timedelta(minutes=1), now)
        assert r["range_type"] == "custom"
        assert isinstance(r["data"], list)

    def test_metric_none_returns_all_metrics(self, svc):
        r = svc.query_preset("1h", metric=None)
        metrics = set(rec["metric"] for rec in r["data"])
        assert len(metrics) >= 2, "不传 metric 时应返回所有指标"

    def test_preset_1h_duration_correct(self):
        delta = TIME_PRESETS["1h"]
        assert abs(delta.total_seconds() - 3600) < 0.01

    def test_preset_6h_duration_correct(self):
        delta = TIME_PRESETS["6h"]
        assert abs(delta.total_seconds() - 6 * 3600) < 0.01

    def test_preset_24h_duration_correct(self):
        delta = TIME_PRESETS["24h"]
        assert abs(delta.total_seconds() - 24 * 3600) < 0.01

    def test_preset_7d_duration_correct(self):
        delta = TIME_PRESETS["7d"]
        assert abs(delta.total_seconds() - 7 * 24 * 3600) < 0.01


# ==============================================================================
# 数据值合理性校验
# ==============================================================================

class TestDataValidity:

    def test_cpu_values_within_0_to_100(self, svc):
        r = svc.query_preset("24h", metric="cpu")
        for rec in r["data"]:
            assert 0 <= rec["value"] <= 100, f"cpu 值 {rec['value']} 超出 0~100 范围"

    def test_memory_values_within_0_to_100(self, svc):
        r = svc.query_preset("24h", metric="memory")
        for rec in r["data"]:
            assert 0 <= rec["value"] <= 100, f"memory 值 {rec['value']} 超出 0~100 范围"

    def test_timestamps_are_valid(self, svc):
        r = svc.query_preset("6h")
        for rec in r["data"]:
            ts = rec["timestamp"]
            assert isinstance(ts, (datetime, str)), f"timestamp 类型 {type(ts).__name__} 不合法"

    def test_data_sorted_by_timestamp_ascending(self, svc):
        r = svc.query_preset("6h")
        timestamps = [p["timestamp"] for p in r["data"]]
        assert timestamps == sorted(timestamps), "数据应按时间戳升序排列"

    def test_custom_range_data_sorted(self, svc, now):
        r = svc.query_custom(now - timedelta(hours=2), now)
        timestamps = [p["timestamp"] for p in r["data"]]
        assert timestamps == sorted(timestamps), "自定义范围数据应按时间戳升序"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
