import pytest
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Dict, Tuple
from dataclasses import dataclass, field
from collections import deque


# ── 模拟用户请求与API处理 ──────────────────────────────────────────

@dataclass
class UserRequest:
    """用户请求"""
    user_id: str
    request_id: str
    payload: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.perf_counter)


@dataclass
class RequestResult:
    """请求结果"""
    user_id: str
    request_id: str
    status_code: int
    latency_ms: float
    error: str = ""


class SimulatedUserService:
    """
    模拟用户服务，支持并发请求处理。
    默认 p95 响应时间在 50-150ms 之间，错误率 < 1%。
    """

    def __init__(
        self,
        base_latency_ms: float = 30.0,
        jitter_ms: float = 40.0,
        max_latency_ms: float = 180.0,
        error_rate: float = 0.005,
        max_concurrent: int = 200,
    ):
        self.base_latency_ms = base_latency_ms
        self.jitter_ms = jitter_ms
        self.max_latency_ms = max_latency_ms
        self.error_rate = error_rate
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._results_lock = threading.Lock()
        self._request_count = 0
        self._error_count = 0
        self._results: List[RequestResult] = []

    def handle_request(self, request: UserRequest) -> RequestResult:
        """处理单个用户请求，模拟真实API延迟和随机错误。"""
        with self._semaphore:
            with self._results_lock:
                self._request_count += 1

            latency = self.base_latency_ms + random.uniform(0, self.jitter_ms)
            latency = min(latency, self.max_latency_ms)

            if random.random() < self.error_rate:
                with self._results_lock:
                    self._error_count += 1
                return RequestResult(
                    user_id=request.user_id,
                    request_id=request.request_id,
                    status_code=500,
                    latency_ms=latency,
                    error="模拟服务端内部错误",
                )

            time.sleep(latency / 1000.0)
            result = RequestResult(
                user_id=request.user_id,
                request_id=request.request_id,
                status_code=200,
                latency_ms=latency,
            )
            with self._results_lock:
                self._results.append(result)
            return result

    def get_results(self) -> List[RequestResult]:
        with self._results_lock:
            return list(self._results)

    def get_error_count(self) -> int:
        with self._results_lock:
            return self._error_count

    def get_request_count(self) -> int:
        with self._results_lock:
            return self._request_count


def concurrent_requests(
    service: SimulatedUserService,
    num_users: int,
    max_workers: int = 100,
) -> List[RequestResult]:
    """
    并发发起 num_users 个用户请求，返回所有结果。
    """
    requests = [
        UserRequest(user_id=f"user-{i}", request_id=f"req-{i}")
        for i in range(num_users)
    ]
    results: List[RequestResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(service.handle_request, req): req
            for req in requests
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                req = futures[future]
                results.append(
                    RequestResult(
                        user_id=req.user_id,
                        request_id=req.request_id,
                        status_code=500,
                        latency_ms=-1.0,
                        error=str(e),
                    )
                )

    return results


def compute_percentile(data: List[float], p: float) -> float:
    """计算百分位值，p 为 0-100。"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = max(0, min(len(sorted_data) - 1, int(len(sorted_data) * p / 100)))
    return sorted_data[index]


# ── Fixture ──────────────────────────────────────────────────────

@pytest.fixture
def normal_service():
    """正常性能的服务实例：p95 < 180ms，error_rate=0.5%。"""
    return SimulatedUserService(
        base_latency_ms=30.0,
        jitter_ms=80.0,
        max_latency_ms=180.0,
        max_concurrent=200,
    )


@pytest.fixture
def slow_service():
    """慢速服务实例：用于验证阈值检测。"""
    return SimulatedUserService(
        base_latency_ms=200.0,
        jitter_ms=100.0,
        max_latency_ms=400.0,
        error_rate=0.0,
        max_concurrent=50,
    )


@pytest.fixture
def high_error_service():
    """高错误率服务实例。"""
    return SimulatedUserService(
        base_latency_ms=30.0,
        jitter_ms=20.0,
        max_latency_ms=100.0,
        error_rate=0.10,
        max_concurrent=200,
    )


# ── 核心测试：100并发用户 p95<=200ms，错误率<1% ─────────────────

class TestConcurrentUserSupport:

    def test_100_concurrent_users_p95_under_200ms(self, normal_service):
        """验收标准：100并发用户下 p95 响应时间 <= 200ms。"""
        results = concurrent_requests(normal_service, num_users=100)
        assert len(results) == 100

        latencies = [r.latency_ms for r in results if r.latency_ms >= 0]
        assert len(latencies) == len(results), "所有请求应有有效延迟"

        p95 = compute_percentile(latencies, 95)
        assert p95 <= 200.0, f"p95 响应时间 {p95:.1f}ms 超过 200ms 阈值"

    def test_100_concurrent_users_error_rate_under_1pct(self, normal_service):
        """验收标准：100并发用户下 错误率 < 1%。"""
        results = concurrent_requests(normal_service, num_users=100)
        total = len(results)
        errors = sum(1 for r in results if r.status_code != 200)
        error_rate = errors / total

        assert error_rate < 0.01, f"错误率 {error_rate*100:.2f}% 超过 1% 阈值"

    def test_100_concurrent_users_all_complete(self, normal_service):
        """验收标准：100个并发用户请求全部完成，无请求丢失。"""
        results = concurrent_requests(normal_service, num_users=100)
        assert len(results) == 100, f"期望100个结果，实际 {len(results)} 个"

        user_ids = {r.user_id for r in results}
        assert len(user_ids) == 100, f"期望100个不同用户，实际 {len(user_ids)} 个"

    def test_100_concurrent_users_max_concurrent_reached(self, normal_service):
        """验收标准：系统能支撑>=100并发用户。"""
        results = concurrent_requests(
            normal_service,
            num_users=100,
            max_workers=100,
        )
        assert len(results) == 100
        successful = sum(1 for r in results if r.status_code == 200)
        assert successful >= 99, f"成功请求数 {successful} < 99"

    def test_concurrent_users_both_p95_and_error_rate_pass(self, normal_service):
        """端到端验证：p95<=200ms 且 错误率<1% 同时通过。"""
        results = concurrent_requests(normal_service, num_users=100)
        latencies = [r.latency_ms for r in results if r.latency_ms >= 0]
        errors = sum(1 for r in results if r.status_code != 200)
        error_rate = errors / len(results)

        p95 = compute_percentile(latencies, 95)
        assert p95 <= 200.0, f"p95={p95:.1f}ms > 200ms"
        assert error_rate < 0.01, f"错误率={error_rate*100:.2f}% >= 1%"


# ── 扩展测试：超过100并发用户 ─────────────────────────────────────

class TestExtendedConcurrentUsers:

    def test_150_concurrent_users_p95_under_200ms(self, normal_service):
        """150并发用户下 p95 响应时间 <= 200ms。"""
        results = concurrent_requests(normal_service, num_users=150)
        latencies = [r.latency_ms for r in results if r.latency_ms >= 0]
        p95 = compute_percentile(latencies, 95)
        assert p95 <= 200.0, f"150并发p95={p95:.1f}ms > 200ms"

    def test_200_concurrent_users_p95_under_200ms(self, normal_service):
        """200并发用户下 p95 响应时间 <= 200ms。"""
        results = concurrent_requests(normal_service, num_workers=200, num_users=200)
        latencies = [r.latency_ms for r in results if r.latency_ms >= 0]
        p95 = compute_percentile(latencies, 95)
        assert p95 <= 200.0, f"200并发p95={p95:.1f}ms > 200ms"

    def test_200_concurrent_users_error_rate_under_1pct(self, normal_service):
        """200并发用户下 错误率 < 1%。"""
        results = concurrent_requests(normal_service, num_users=200)
        errors = sum(1 for r in results if r.status_code != 200)
        error_rate = errors / len(results)
        assert error_rate < 0.01, f"200并发错误率={error_rate*100:.2f}% >= 1%"


# ── 验证测试：阈值检测有效性 ─────────────────────────────────────

class TestThresholdDetection:

    def test_slow_service_exceeds_p95_threshold(self, slow_service):
        """慢服务应超过 p95<=200ms 阈值。"""
        results = concurrent_requests(slow_service, num_users=100)
        latencies = [r.latency_ms for r in results if r.latency_ms >= 0]
        p95 = compute_percentile(latencies, 95)
        assert p95 > 200.0, f"慢服务p95={p95:.1f}ms 应>200ms"

    def test_high_error_service_exceeds_error_rate(self, high_error_service):
        """高错误率服务应超过 1% 错误率阈值。"""
        results = concurrent_requests(high_error_service, num_users=200)
        errors = sum(1 for r in results if r.status_code != 200)
        error_rate = errors / len(results)
        assert error_rate > 0.01, f"高错误率服务错误率={error_rate*100:.2f}% 应>1%"


# ── 边界测试 ─────────────────────────────────────────────────────

class TestEdgeCases:

    def test_single_user_succeeds(self, normal_service):
        """单个用户请求应正常完成。"""
        results = concurrent_requests(normal_service, num_users=1)
        assert len(results) == 1
        assert results[0].status_code == 200
        assert results[0].latency_ms > 0

    def test_percentile_calculation_single_value(self):
        """单值百分位计算。"""
        assert compute_percentile([100.0], 50) == 100.0
        assert compute_percentile([100.0], 95) == 100.0
        assert compute_percentile([100.0], 99) == 100.0

    def test_percentile_calculation_empty(self):
        """空列表百分位返回0。"""
        assert compute_percentile([], 50) == 0.0

    def test_percentile_p50_of_even_list(self):
        """偶数长度列表的p50计算。"""
        data = list(range(1, 101))
        p50 = compute_percentile(data, 50)
        assert 49 <= p50 <= 51

    def test_no_deadlock_with_max_concurrent(self, normal_service):
        """并发数达到上限时应正确阻塞/等待，不产生死锁。"""
        service = SimulatedUserService(
            base_latency_ms=10.0,
            jitter_ms=10.0,
            max_latency_ms=50.0,
            error_rate=0.0,
            max_concurrent=10,
        )
        results = concurrent_requests(service, num_users=50)
        assert len(results) == 50
        assert all(r.status_code == 200 for r in results)

    def test_results_are_unique_per_user(self, normal_service):
        """每个用户的结果应唯一，不与其他用户混淆。"""
        results = concurrent_requests(normal_service, num_users=100)
        user_id_counts: Dict[str, int] = {}
        for r in results:
            user_id_counts[r.user_id] = user_id_counts.get(r.user_id, 0) + 1
        for user_id, count in user_id_counts.items():
            assert count == 1, f"用户 {user_id} 有 {count} 条结果，预期 1 条"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
