import pytest
import time
import random
from typing import Callable


def create_simulated_api(base_latency_ms: float = 30.0, jitter_ms: float = 20.0, error_rate: float = 0.0):
    """创建模拟API，返回 (latency_ms, response) 或抛出异常模拟超时/错误"""
    def api_handler(request: str) -> dict:
        latency = base_latency_ms + random.uniform(0, jitter_ms)
        if error_rate > 0 and random.random() < error_rate:
            raise ConnectionError("模拟服务端错误")
        if latency > 5000:
            raise TimeoutError("模拟请求超时")
        time.sleep(latency / 1000.0)
        return {"status": "ok", "request": request, "latency_ms": latency}
    return api_handler


def measure_latencies(api: Callable, requests: list, timeout_ms: float = 5000.0) -> list:
    """对一组请求发起调用，返回每个请求的延迟（毫秒），超时或异常记为 -1"""
    latencies = []
    for req in requests:
        start = time.perf_counter()
        try:
            api(req)
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
        except (ConnectionError, TimeoutError, Exception):
            latencies.append(-1.0)
    return latencies


def compute_percentile(data: list, p: float) -> float:
    """计算百分位值，p 为 0-100"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = max(0, min(len(sorted_data) - 1, int(len(sorted_data) * p / 100)))
    return sorted_data[index]


class TestPerformanceApiResponseTime:

    @pytest.fixture
    def normal_api(self):
        return create_simulated_api(base_latency_ms=30.0, jitter_ms=20.0)

    @pytest.fixture
    def slow_api(self):
        return create_simulated_api(base_latency_ms=300.0, jitter_ms=100.0)

    @pytest.fixture
    def error_prone_api(self):
        return create_simulated_api(base_latency_ms=30.0, jitter_ms=10.0, error_rate=0.3)

    @pytest.fixture
    def sample_requests(self):
        return [f"request-{i}" for i in range(100)]

    def test_p50_within_50ms(self, normal_api, sample_requests):
        """验收标准：p50 <= 50ms"""
        latencies = measure_latencies(normal_api, sample_requests)
        valid = [l for l in latencies if l >= 0]
        p50 = compute_percentile(valid, 50)
        assert p50 <= 50.0, f"p50={p50}ms 超过 50ms 阈值"

    def test_p95_within_200ms(self, normal_api, sample_requests):
        """验收标准：p95 <= 200ms"""
        latencies = measure_latencies(normal_api, sample_requests)
        valid = [l for l in latencies if l >= 0]
        p95 = compute_percentile(valid, 95)
        assert p95 <= 200.0, f"p95={p95}ms 超过 200ms 阈值"

    def test_p99_within_500ms(self, normal_api, sample_requests):
        """验收标准：p99 <= 500ms"""
        latencies = measure_latencies(normal_api, sample_requests)
        valid = [l for l in latencies if l >= 0]
        p99 = compute_percentile(valid, 99)
        assert p99 <= 500.0, f"p99={p99}ms 超过 500ms 阈值"

    def test_all_metrics_satisfied(self, normal_api, sample_requests):
        """一次性验证 p50/p95/p99 全部达标"""
        latencies = measure_latencies(normal_api, sample_requests)
        valid = [l for l in latencies if l >= 0]
        p50 = compute_percentile(valid, 50)
        p95 = compute_percentile(valid, 95)
        p99 = compute_percentile(valid, 99)
        assert p50 <= 50.0, f"p50={p50}ms > 50ms"
        assert p95 <= 200.0, f"p95={p95}ms > 200ms"
        assert p99 <= 500.0, f"p99={p99}ms > 500ms"

    def test_slow_api_exceeds_p50_threshold(self, slow_api, sample_requests):
        """慢API的p50应超过50ms，验证阈值检测有效"""
        latencies = measure_latencies(slow_api, sample_requests)
        valid = [l for l in latencies if l >= 0]
        p50 = compute_percentile(valid, 50)
        assert p50 > 50.0, f"慢API的p50={p50}ms 应超过50ms阈值"

    def test_error_prone_api_handles_errors_gracefully(self, error_prone_api):
        """错误率高的API应正确处理异常，不崩溃"""
        requests = [f"req-{i}" for i in range(50)]
        latencies = measure_latencies(error_prone_api, requests)
        error_count = sum(1 for l in latencies if l < 0)
        assert error_count > 0, "应有部分请求因错误返回-1"
        valid = [l for l in latencies if l >= 0]
        assert len(valid) > 0, "应有部分请求成功"

    def test_timeout_detection(self):
        """超时请求应被正确检测并返回-1"""
        api = create_simulated_api(base_latency_ms=6000.0, jitter_ms=0)
        latencies = measure_latencies(api, ["timeout-test"])
        # 模拟超时请求返回 -1
        assert latencies[0] == -1.0, "超时请求应返回 -1"

    def test_high_volume_within_tolerance(self, normal_api):
        """大量请求（200次）下性能指标仍应达标"""
        requests = [f"vol-{i}" for i in range(200)]
        latencies = measure_latencies(normal_api, requests)
        valid = [l for l in latencies if l >= 0]
        assert len(valid) == 200, f"应有200个成功请求，实际{len(valid)}"
        p95 = compute_percentile(valid, 95)
        p99 = compute_percentile(valid, 99)
        assert p95 <= 200.0, f"高流量下p95={p95}ms > 200ms"
        assert p99 <= 500.0, f"高流量下p99={p99}ms > 500ms"

    def test_empty_request_list_does_not_crash(self, normal_api):
        """空请求列表不应导致崩溃"""
        latencies = measure_latencies(normal_api, [])
        assert latencies == [], "空请求应返回空列表"

    def test_percentile_edge_cases(self):
        """百分位计算边界情况"""
        assert compute_percentile([], 50) == 0.0, "空列表应返回0"
        assert compute_percentile([10.0], 50) == 10.0, "单元素p50=自身"
        assert compute_percentile([10.0], 99) == 10.0, "单元素p99=自身"
        data = [1, 2, 3, 4, 5]
        assert compute_percentile(data, 0) == 1, "p0应为最小值"
        assert compute_percentile(data, 100) == 5, "p100应为最大值"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
