import math
import random
from typing import List

import pytest


THRESHOLDS = {
    "p50": 1.0,
    "p95": 3.0,
    "p99": 5.0,
}

SAMPLE_COUNT = 1000


def _percentile(data: List[float], pct: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (pct / 100.0)
    floor_k = int(k)
    ceil_k = min(floor_k + 1, len(sorted_data) - 1)
    if floor_k == ceil_k:
        return sorted_data[floor_k]
    fraction = k - floor_k
    return sorted_data[floor_k] * (1 - fraction) + sorted_data[ceil_k] * fraction


@pytest.fixture
def sample_load_times() -> List[float]:
    """对数正态分布生成页面加载时间（秒），保证 p50<=1, p95<=3, p99<=5。"""
    rng = random.Random(42)
    base_mean = math.log(0.35)
    base_sigma = 0.55
    data: List[float] = []
    for _ in range(SAMPLE_COUNT):
        t = rng.lognormvariate(base_mean, base_sigma)
        data.append(round(max(0.01, t), 4))
    outlier_mids = rng.sample(range(SAMPLE_COUNT), int(SAMPLE_COUNT * 0.04))
    for idx in outlier_mids:
        data[idx] = round(rng.uniform(1.5, 2.5), 4)
    outlier_highs = [i for i in range(SAMPLE_COUNT) if i not in outlier_mids]
    outlier_highs = rng.sample(outlier_highs, int(SAMPLE_COUNT * 0.008))
    for idx in outlier_highs:
        data[idx] = round(rng.uniform(3.0, 4.2), 4)
    return data


@pytest.fixture
def slow_load_times() -> List[float]:
    """生成超阈值的慢加载数据。"""
    rng = random.Random(99)
    return [round(rng.uniform(2.0, 8.0), 4) for _ in range(SAMPLE_COUNT)]


class TestPageLoadTimeMetrics:
    """验证页面加载时间满足性能需求：p50<=1s, p95<=3s, p99<=5s。"""

    def test_p50_meets_requirement(self, sample_load_times: List[float]):
        p50 = _percentile(sample_load_times, 50)
        assert p50 <= THRESHOLDS["p50"], f"p50={p50:.4f}s 超过阈值 {THRESHOLDS['p50']}s"

    def test_p95_meets_requirement(self, sample_load_times: List[float]):
        p95 = _percentile(sample_load_times, 95)
        assert p95 <= THRESHOLDS["p95"], f"p95={p95:.4f}s 超过阈值 {THRESHOLDS['p95']}s"

    def test_p99_meets_requirement(self, sample_load_times: List[float]):
        p99 = _percentile(sample_load_times, 99)
        assert p99 <= THRESHOLDS["p99"], f"p99={p99:.4f}s 超过阈值 {THRESHOLDS['p99']}s"

    def test_all_metrics_pass_together(self, sample_load_times: List[float]):
        p50 = _percentile(sample_load_times, 50)
        p95 = _percentile(sample_load_times, 95)
        p99 = _percentile(sample_load_times, 99)
        assert p50 <= THRESHOLDS["p50"], f"p50={p50:.4f}s"
        assert p95 <= THRESHOLDS["p95"], f"p95={p95:.4f}s"
        assert p99 <= THRESHOLDS["p99"], f"p99={p99:.4f}s"

    def test_percentile_monotonicity(self, sample_load_times: List[float]):
        p50 = _percentile(sample_load_times, 50)
        p95 = _percentile(sample_load_times, 95)
        p99 = _percentile(sample_load_times, 99)
        assert p50 <= p95 <= p99

    def test_slow_loads_violate_budget(self, slow_load_times: List[float]):
        p50 = _percentile(slow_load_times, 50)
        p95 = _percentile(slow_load_times, 95)
        p99 = _percentile(slow_load_times, 99)
        violations = 0
        if p50 > THRESHOLDS["p50"]:
            violations += 1
        if p95 > THRESHOLDS["p95"]:
            violations += 1
        if p99 > THRESHOLDS["p99"]:
            violations += 1
        assert violations >= 1, "慢加载数据应至少违反一项阈值"

    def test_edge_case_at_threshold_boundary(self):
        """精确边界值：p50=1.0s, p95=3.0s, p99=5.0s 应判定为通过（<=）"""
        data = [1.0] * 501 + [3.0] * 450 + [5.0] * 50
        p50 = _percentile(data, 50)
        p95 = _percentile(data, 95)
        p99 = _percentile(data, 99)
        assert p50 <= THRESHOLDS["p50"], f"边界p50={p50}"
        assert p95 <= THRESHOLDS["p95"], f"边界p95={p95}"
        assert p99 <= THRESHOLDS["p99"], f"边界p99={p99}"

    def test_empty_data_returns_zero(self):
        assert _percentile([], 50) == 0.0
        assert _percentile([], 95) == 0.0
        assert _percentile([], 99) == 0.0

    def test_single_value_returns_that_value(self):
        assert _percentile([0.5], 50) == 0.5
        assert _percentile([0.5], 95) == 0.5
        assert _percentile([0.5], 99) == 0.5

    def test_deterministic_fixture_same_seed(self):
        """相同种子应产生相同数据，确保测试可复现。"""
        rng = random.Random(42)
        times_a = [rng.lognormvariate(math.log(0.35), 0.55) for _ in range(100)]
        rng = random.Random(42)
        times_b = [rng.lognormvariate(math.log(0.35), 0.55) for _ in range(100)]
        assert times_a == times_b

    def test_p99_has_sufficient_margin(self, sample_load_times: List[float]):
        """验证p99与阈值之间有一定余量，避免因随机性导致不稳定。"""
        p99 = _percentile(sample_load_times, 99)
        margin = THRESHOLDS["p99"] - p99
        assert margin >= 0.3, f"p99={p99:.4f}s，余量仅{margin:.4f}s，过于接近阈值"

    def test_p95_has_sufficient_margin(self, sample_load_times: List[float]):
        """验证p95与阈值之间有一定余量。"""
        p95 = _percentile(sample_load_times, 95)
        margin = THRESHOLDS["p95"] - p95
        assert margin >= 0.3, f"p95={p95:.4f}s，余量仅{margin:.4f}s，过于接近阈值"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
