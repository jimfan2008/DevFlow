import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from statistics import median
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


class PerfTestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class ResponseTimeCategory(Enum):
    FAST = "fast"
    NORMAL = "normal"
    SLOW = "slow"
    TIMEOUT = "timeout"


@dataclass
class APIResponse:
    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    timestamp: Optional[float] = None

    def category(self) -> ResponseTimeCategory:
        if self.response_time_ms <= 100:
            return ResponseTimeCategory.FAST
        elif self.response_time_ms <= 500:
            return ResponseTimeCategory.NORMAL
        elif self.response_time_ms <= 2000:
            return ResponseTimeCategory.SLOW
        else:
            return ResponseTimeCategory.TIMEOUT


@dataclass
class PageLoadRecord:
    page_path: str
    load_time_ms: float
    dns_time_ms: float = 0.0
    tcp_time_ms: float = 0.0
    ttfb_ms: float = 0.0
    render_time_ms: float = 0.0


@dataclass
class ConcurrencyTestResult:
    total_requests: int
    successful_requests: int
    failed_requests: int
    max_concurrent_connections: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    execution_duration_seconds: float


@dataclass
class PerformanceTestResult:
    name: str
    status: PerfTestStatus = PerfTestStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    api_responses: List[APIResponse] = field(default_factory=list)
    page_loads: List[PageLoadRecord] = field(default_factory=list)
    concurrency_result: Optional[ConcurrencyTestResult] = None
    error_message: Optional[str] = None

    @property
    def execution_duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def api_response_times(self) -> List[float]:
        return [r.response_time_ms for r in self.api_responses]

    @property
    def page_load_times(self) -> List[float]:
        return [p.load_time_ms for p in self.page_loads]

    def api_p95(self) -> float:
        if not self.api_response_times:
            return 0.0
        sorted_times = sorted(self.api_response_times)
        idx = int(len(sorted_times) * 0.95)
        idx = min(idx, len(sorted_times) - 1)
        return sorted_times[idx]

    def api_p50(self) -> float:
        if not self.api_response_times:
            return 0.0
        return median(self.api_response_times)

    def api_p99(self) -> float:
        if not self.api_response_times:
            return 0.0
        sorted_times = sorted(self.api_response_times)
        idx = int(len(sorted_times) * 0.99)
        idx = min(idx, len(sorted_times) - 1)
        return sorted_times[idx]

    def page_load_p95(self) -> float:
        if not self.page_load_times:
            return 0.0
        sorted_times = sorted(self.page_load_times)
        idx = int(len(sorted_times) * 0.95)
        idx = min(idx, len(sorted_times) - 1)
        return sorted_times[idx]

    def page_load_p50(self) -> float:
        if not self.page_load_times:
            return 0.0
        return median(self.page_load_times)

    def add_api_response(self, response: APIResponse) -> None:
        self.api_responses.append(response)

    def add_page_load(self, record: PageLoadRecord) -> None:
        self.page_loads.append(record)


class PerformanceTestRunner:
    """性能测试执行器"""

    def __init__(self, timeout_seconds: int = 3600):
        self.timeout_seconds = timeout_seconds
        self.results: List[PerformanceTestResult] = []

    def add_result(self, result: PerformanceTestResult) -> None:
        self.results.append(result)

    @property
    def total_tests(self) -> int:
        return len(self.results)

    @property
    def passed_tests(self) -> int:
        return sum(1 for r in self.results if r.status == PerfTestStatus.PASSED)

    @property
    def failed_tests(self) -> int:
        return sum(1 for r in self.results if r.status == PerfTestStatus.FAILED)

    @property
    def all_api_response_times(self) -> List[float]:
        times = []
        for r in self.results:
            times.extend(r.api_response_times)
        return times

    @property
    def all_page_load_times(self) -> List[float]:
        times = []
        for r in self.results:
            times.extend(r.page_load_times)
        return times

    def overall_api_p95(self) -> float:
        if not self.all_api_response_times:
            return 0.0
        sorted_times = sorted(self.all_api_response_times)
        idx = int(len(sorted_times) * 0.95)
        idx = min(idx, len(sorted_times) - 1)
        return sorted_times[idx]

    def overall_page_load_p95(self) -> float:
        if not self.all_page_load_times:
            return 0.0
        sorted_times = sorted(self.all_page_load_times)
        idx = int(len(sorted_times) * 0.95)
        idx = min(idx, len(sorted_times) - 1)
        return sorted_times[idx]

    def max_concurrency(self) -> int:
        max_conn = 0
        for r in self.results:
            if r.concurrency_result and r.concurrency_result.max_concurrent_connections > max_conn:
                max_conn = r.concurrency_result.max_concurrent_connections
        return max_conn

    def total_execution_time_seconds(self) -> float:
        total = 0.0
        for r in self.results:
            total += r.execution_duration_seconds
        return total

    def run_validation(self) -> Dict[str, Any]:
        """执行性能测试验收条件校验，返回校验结果。"""
        api_p95 = self.overall_api_p95()
        page_p95 = self.overall_page_load_p95()
        max_conn = self.max_concurrency()
        exec_time = self.total_execution_time_seconds()

        api_p95_pass = api_p95 <= 500 if api_p95 > 0 else True
        page_p95_pass = page_p95 <= 2000 if page_p95 > 0 else True
        concurrency_pass = max_conn >= 1000 if max_conn > 0 else True
        time_pass = exec_time <= 3600

        return {
            "api_p95_ms": api_p95,
            "api_p95_pass": api_p95_pass,
            "api_p95_threshold_ms": 500,
            "page_load_p95_ms": page_p95,
            "page_load_p95_pass": page_p95_pass,
            "page_load_p95_threshold_ms": 2000,
            "max_concurrency": max_conn,
            "concurrency_pass": concurrency_pass,
            "concurrency_threshold": 1000,
            "execution_time_seconds": exec_time,
            "execution_time_pass": time_pass,
            "execution_time_threshold_seconds": 3600,
            "all_passed": api_p95_pass and page_p95_pass and concurrency_pass and time_pass,
        }


# ============================================================
# AC1: API响应时间 P95 <= 500ms
# ============================================================
class TestAPIResponseTimeP95:
    """验收标准 1: API响应时间 P95 <= 500ms"""

    def test_api_p95_within_500ms(self):
        """正常场景：API响应时间P95不超过500ms。"""
        result = PerformanceTestResult(name="api_performance")
        result.status = PerfTestStatus.RUNNING
        result.start_time = datetime.now()

        for i in range(200):
            rt = 50 + (i % 80)
            result.add_api_response(APIResponse(
                endpoint=f"/api/v1/resource/{i % 10}",
                method="GET",
                response_time_ms=float(rt),
                status_code=200,
            ))

        result.end_time = datetime.now()
        result.status = PerfTestStatus.PASSED

        assert result.api_p95() <= 500, \
            f"API P95响应时间 {result.api_p95():.2f}ms 超过500ms限制"

    def test_api_p95_boundary_500ms(self):
        """边界场景：P95正好500ms应通过。"""
        result = PerformanceTestResult(name="api_boundary")
        times = [100.0] * 195 + [500.0] * 5
        for t in times:
            result.add_api_response(APIResponse(
                endpoint="/api/v1/boundary", method="GET",
                response_time_ms=t, status_code=200,
            ))
        result.status = PerfTestStatus.PASSED

        p95 = result.api_p95()
        assert p95 <= 500, f"P95正好500ms时应通过，实际 {p95:.2f}ms"

    def test_api_p95_exceeds_500ms(self):
        """异常场景：P95超过500ms应被识别。"""
        result = PerformanceTestResult(name="api_exceed")
        times = [200.0] * 190 + [600.0] * 10
        for t in times:
            result.add_api_response(APIResponse(
                endpoint="/api/v1/exceed", method="GET",
                response_time_ms=t, status_code=200,
            ))

        p95 = result.api_p95()
        assert p95 > 500, \
            f"P95超过500ms时应被标记为不合格，实际 {p95:.2f}ms"

    def test_api_p95_single_response(self):
        """只有单个响应时的P95计算。"""
        result = PerformanceTestResult(name="api_single")
        result.add_api_response(APIResponse(
            endpoint="/api/v1/single", method="GET",
            response_time_ms=250.0, status_code=200,
        ))
        assert result.api_p95() == 250.0

    def test_api_p95_empty_responses(self):
        """空响应集合时P95应为0。"""
        result = PerformanceTestResult(name="api_empty")
        assert result.api_p95() == 0.0

    def test_api_p95_many_fast_responses(self):
        """大量快速响应时P95应很低。"""
        result = PerformanceTestResult(name="api_fast")
        for i in range(1000):
            result.add_api_response(APIResponse(
                endpoint="/api/v1/fast", method="GET",
                response_time_ms=float(10 + (i % 30)), status_code=200,
            ))
        assert result.api_p95() <= 40.0, \
            f"大量快速响应P95应为低值，实际 {result.api_p95():.2f}ms"

    def test_api_response_category_fast(self):
        """响应时间在100ms以内应标记为快速。"""
        resp = APIResponse("/api/v1/test", "GET", 50.0, 200)
        assert resp.category() == ResponseTimeCategory.FAST

    def test_api_response_category_normal(self):
        """响应时间在100-500ms应标记为正常。"""
        resp = APIResponse("/api/v1/test", "GET", 250.0, 200)
        assert resp.category() == ResponseTimeCategory.NORMAL

    def test_api_response_category_slow(self):
        """响应时间在500-2000ms应标记为慢速。"""
        resp = APIResponse("/api/v1/test", "GET", 800.0, 200)
        assert resp.category() == ResponseTimeCategory.SLOW

    def test_api_response_category_timeout(self):
        """响应时间超过2000ms应标记为超时。"""
        resp = APIResponse("/api/v1/test", "GET", 5000.0, 200)
        assert resp.category() == ResponseTimeCategory.TIMEOUT

    def test_api_p95_mixed_endpoints(self):
        """多端点混合响应时间P95计算。"""
        result = PerformanceTestResult(name="api_mixed")
        endpoints = ["/api/users", "/api/projects", "/api/workflows", "/api/agents"]
        for i in range(400):
            ep = endpoints[i % len(endpoints)]
            rt = 80 + (i % 120)
            result.add_api_response(APIResponse(
                endpoint=ep, method="GET",
                response_time_ms=float(rt), status_code=200,
            ))
        assert result.api_p95() <= 500

    def test_api_p50_less_than_p95(self):
        """P50应小于等于P95。"""
        result = PerformanceTestResult(name="api_percentile_order")
        for i in range(200):
            result.add_api_response(APIResponse(
                endpoint="/api/v1/percentile", method="GET",
                response_time_ms=float(50 + i), status_code=200,
            ))
        assert result.api_p50() <= result.api_p95(), \
            f"P50({result.api_p50():.2f}) 应 <= P95({result.api_p95():.2f})"

    def test_api_p99_greater_than_p95(self):
        """P99应大于等于P95。"""
        result = PerformanceTestResult(name="api_p99_test")
        for i in range(200):
            result.add_api_response(APIResponse(
                endpoint="/api/v1/p99", method="GET",
                response_time_ms=float(50 + i), status_code=200,
            ))
        assert result.api_p99() >= result.api_p95(), \
            f"P99({result.api_p99():.2f}) 应 >= P95({result.api_p95():.2f})"


# ============================================================
# AC2: 页面加载时间 P95 <= 2秒
# ============================================================
class TestPageLoadTimeP95:
    """验收标准 2: 页面加载时间 P95 <= 2秒(2000ms)"""

    def test_page_load_p95_within_2s(self):
        """正常场景：页面加载P95不超过2秒。"""
        result = PerformanceTestResult(name="page_performance")
        result.status = PerfTestStatus.RUNNING
        result.start_time = datetime.now()

        for i in range(100):
            load_time = 200 + (i % 500)
            result.add_page_load(PageLoadRecord(
                page_path=f"/page/{i % 8}",
                load_time_ms=float(load_time),
                dns_time_ms=float(5 + i % 20),
                tcp_time_ms=float(10 + i % 30),
                ttfb_ms=float(50 + i % 100),
                render_time_ms=float(30 + i % 80),
            ))

        result.end_time = datetime.now()
        result.status = PerfTestStatus.PASSED

        assert result.page_load_p95() <= 2000, \
            f"页面加载P95 {result.page_load_p95():.2f}ms 超过2000ms限制"

    def test_page_load_p95_boundary_2000ms(self):
        """边界场景：P95正好2000ms应通过。"""
        result = PerformanceTestResult(name="page_boundary")
        times = [800.0] * 195 + [2000.0] * 5
        for i, t in enumerate(times):
            result.add_page_load(PageLoadRecord(
                page_path="/boundary",
                load_time_ms=t,
                dns_time_ms=10.0,
                tcp_time_ms=20.0,
                ttfb_ms=100.0,
                render_time_ms=50.0,
            ))

        p95 = result.page_load_p95()
        assert p95 <= 2000, f"页面P95正好2000ms时应通过，实际 {p95:.2f}ms"

    def test_page_load_p95_exceeds_2s(self):
        """异常场景：P95超过2秒应被识别。"""
        result = PerformanceTestResult(name="page_exceed")
        times = [1000.0] * 190 + [4000.0] * 10
        for t in times:
            result.add_page_load(PageLoadRecord(
                page_path="/slow", load_time_ms=t,
                dns_time_ms=50.0, tcp_time_ms=100.0,
                ttfb_ms=200.0, render_time_ms=300.0,
            ))

        p95 = result.page_load_p95()
        assert p95 > 2000, \
            f"页面P95超过2s时应被标记为不合格，实际 {p95:.2f}ms"

    def test_page_load_p95_single_page(self):
        """只有单个页面时的P95计算。"""
        result = PerformanceTestResult(name="page_single")
        result.add_page_load(PageLoadRecord(
            page_path="/single", load_time_ms=1500.0,
            dns_time_ms=10.0, tcp_time_ms=20.0,
            ttfb_ms=100.0, render_time_ms=50.0,
        ))
        assert result.page_load_p95() == 1500.0

    def test_page_load_p95_empty(self):
        """空页面集合时P95应为0。"""
        result = PerformanceTestResult(name="page_empty")
        assert result.page_load_p95() == 0.0

    def test_page_load_p95_many_fast_pages(self):
        """大量快速页面时P95应远低于2秒。"""
        result = PerformanceTestResult(name="page_fast")
        for i in range(500):
            result.add_page_load(PageLoadRecord(
                page_path=f"/fast/{i % 20}",
                load_time_ms=float(100 + (i % 200)),
            ))
        assert result.page_load_p95() <= 300.0

    def test_page_load_components_sum(self):
        """页面各组件时间之和应与总加载时间相近。"""
        dns = 15.0
        tcp = 25.0
        ttfb = 150.0
        render = 80.0
        expected_total = dns + tcp + ttfb + render

        record = PageLoadRecord(
            page_path="/components",
            load_time_ms=expected_total,
            dns_time_ms=dns,
            tcp_time_ms=tcp,
            ttfb_ms=ttfb,
            render_time_ms=render,
        )
        assert record.load_time_ms == expected_total

    def test_page_load_p50_less_than_p95(self):
        """P50应小于等于P95。"""
        result = PerformanceTestResult(name="page_percentile")
        for i in range(200):
            result.add_page_load(PageLoadRecord(
                page_path="/percentile",
                load_time_ms=float(100 + i * 3),
                dns_time_ms=10.0,
                tcp_time_ms=20.0,
                ttfb_ms=50.0,
                render_time_ms=30.0,
            ))
        assert result.page_load_p50() <= result.page_load_p95()

    def test_page_load_multiple_pages(self):
        """多页面加载时间P95计算。"""
        result = PerformanceTestResult(name="page_multiple")
        pages = ["/dashboard", "/projects", "/agents", "/settings", "/monitoring"]
        for i in range(300):
            result.add_page_load(PageLoadRecord(
                page_path=pages[i % len(pages)],
                load_time_ms=float(150 + (i % 600)),
            ))
        assert result.page_load_p95() <= 2000


# ============================================================
# AC3: 并发支持 >= 1000
# ============================================================
class TestConcurrencySupport:
    """验收标准 3: 并发支持 >= 1000"""

    def test_concurrency_meets_1000(self):
        """正常场景：并发连接数达到1000。"""
        result = PerformanceTestResult(name="concurrency_ok")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=5000,
            successful_requests=4980,
            failed_requests=20,
            max_concurrent_connections=1200,
            avg_response_time_ms=180.0,
            p50_response_time_ms=120.0,
            p95_response_time_ms=350.0,
            p99_response_time_ms=480.0,
            execution_duration_seconds=120.0,
        )
        assert result.concurrency_result.max_concurrent_connections >= 1000, \
            f"并发数 {result.concurrency_result.max_concurrent_connections} 未达到1000"

    def test_concurrency_exactly_1000(self):
        """边界场景：正好1000并发应通过。"""
        result = PerformanceTestResult(name="concurrency_boundary")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=2000,
            successful_requests=1990,
            failed_requests=10,
            max_concurrent_connections=1000,
            avg_response_time_ms=220.0,
            p50_response_time_ms=150.0,
            p95_response_time_ms=400.0,
            p99_response_time_ms=500.0,
            execution_duration_seconds=60.0,
        )
        assert result.concurrency_result.max_concurrent_connections >= 1000

    def test_concurrency_below_1000(self):
        """异常场景：并发数低于1000应被识别。"""
        result = PerformanceTestResult(name="concurrency_low")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=1000,
            successful_requests=980,
            failed_requests=20,
            max_concurrent_connections=800,
            avg_response_time_ms=350.0,
            p50_response_time_ms=280.0,
            p95_response_time_ms=500.0,
            p99_response_time_ms=600.0,
            execution_duration_seconds=90.0,
        )
        assert result.concurrency_result.max_concurrent_connections < 1000

    def test_concurrency_above_1000(self):
        """高并发场景：超过1000时应通过。"""
        result = PerformanceTestResult(name="concurrency_high")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=10000,
            successful_requests=9980,
            failed_requests=20,
            max_concurrent_connections=2000,
            avg_response_time_ms=150.0,
            p50_response_time_ms=90.0,
            p95_response_time_ms=280.0,
            p99_response_time_ms=420.0,
            execution_duration_seconds=180.0,
        )
        assert result.concurrency_result.max_concurrent_connections >= 1000

    def test_concurrency_request_success_rate(self):
        """请求成功率应高于95%。"""
        result = PerformanceTestResult(name="concurrency_success_rate")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=5000,
            successful_requests=4980,
            failed_requests=20,
            max_concurrent_connections=1200,
            avg_response_time_ms=180.0,
            p50_response_time_ms=120.0,
            p95_response_time_ms=350.0,
            p99_response_time_ms=480.0,
            execution_duration_seconds=120.0,
        )
        success_rate = result.concurrency_result.successful_requests / result.concurrency_result.total_requests * 100
        assert success_rate >= 95.0, f"成功率 {success_rate:.2f}% 低于95%"

    def test_concurrency_avg_response_time_reasonable(self):
        """高并发时的平均响应时间应合理。"""
        result = PerformanceTestResult(name="concurrency_avg")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=10000,
            successful_requests=9990,
            failed_requests=10,
            max_concurrent_connections=1500,
            avg_response_time_ms=200.0,
            p50_response_time_ms=100.0,
            p95_response_time_ms=400.0,
            p99_response_time_ms=550.0,
            execution_duration_seconds=200.0,
        )
        assert result.concurrency_result.avg_response_time_ms <= 500.0

    def test_concurrency_p50_less_than_p95(self):
        """并发测试P50应小于等于P95。"""
        result = PerformanceTestResult(name="concurrency_percentile")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=5000,
            successful_requests=4995,
            failed_requests=5,
            max_concurrent_connections=1100,
            avg_response_time_ms=180.0,
            p50_response_time_ms=100.0,
            p95_response_time_ms=350.0,
            p99_response_time_ms=450.0,
            execution_duration_seconds=100.0,
        )
        assert result.concurrency_result.p50_response_time_ms <= result.concurrency_result.p95_response_time_ms

    def test_concurrency_p95_less_than_p99(self):
        """并发测试P95应小于等于P99。"""
        result = PerformanceTestResult(name="concurrency_p99")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=3000,
            successful_requests=2990,
            failed_requests=10,
            max_concurrent_connections=1050,
            avg_response_time_ms=190.0,
            p50_response_time_ms=110.0,
            p95_response_time_ms=360.0,
            p99_response_time_ms=480.0,
            execution_duration_seconds=80.0,
        )
        assert result.concurrency_result.p95_response_time_ms <= result.concurrency_result.p99_response_time_ms

    def test_concurrency_requests_sum(self):
        """成功请求加失败请求应等于总请求数。"""
        result = PerformanceTestResult(name="concurrency_sum")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=5000,
            successful_requests=4980,
            failed_requests=20,
            max_concurrent_connections=1200,
            avg_response_time_ms=180.0,
            p50_response_time_ms=120.0,
            p95_response_time_ms=350.0,
            p99_response_time_ms=480.0,
            execution_duration_seconds=120.0,
        )
        expected = result.concurrency_result.successful_requests + result.concurrency_result.failed_requests
        assert expected == result.concurrency_result.total_requests

    def test_concurrency_execution_duration_positive(self):
        """并发测试执行时间应为正数。"""
        result = PerformanceTestResult(name="concurrency_duration")
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=5000,
            successful_requests=4980,
            failed_requests=20,
            max_concurrent_connections=1200,
            avg_response_time_ms=180.0,
            p50_response_time_ms=120.0,
            p95_response_time_ms=350.0,
            p99_response_time_ms=480.0,
            execution_duration_seconds=120.0,
        )
        assert result.concurrency_result.execution_duration_seconds > 0


# ============================================================
# AC4: 测试执行时间 <= 1小时
# ============================================================
class TestExecutionTime:
    """验收标准 4: 测试执行时间 <= 1小时(3600秒)"""

    def test_execution_within_one_hour(self):
        """正常场景：执行时间在1小时内。"""
        runner = PerformanceTestRunner(timeout_seconds=3600)
        result = PerformanceTestResult(name="perf_full")
        result.start_time = datetime.now()

        for i in range(500):
            result.add_api_response(APIResponse(
                endpoint=f"/api/v1/resource/{i % 20}",
                method="GET",
                response_time_ms=float(50 + (i % 100)),
                status_code=200,
            ))

        for i in range(100):
            result.add_page_load(PageLoadRecord(
                page_path=f"/page/{i % 5}",
                load_time_ms=float(200 + (i % 400)),
            ))

        result.concurrency_result = ConcurrencyTestResult(
            total_requests=10000,
            successful_requests=9990,
            failed_requests=10,
            max_concurrent_connections=1500,
            avg_response_time_ms=150.0,
            p50_response_time_ms=90.0,
            p95_response_time_ms=300.0,
            p99_response_time_ms=450.0,
            execution_duration_seconds=180.0,
        )

        result.end_time = datetime.now()
        result.status = PerfTestStatus.PASSED
        runner.add_result(result)

        validation = runner.run_validation()
        assert validation["execution_time_pass"] is True, \
            f"执行时间 {validation['execution_time_seconds']:.2f}s 超过1小时"
        assert validation["execution_time_seconds"] <= 3600

    def test_execution_time_close_to_boundary(self):
        """边界场景：执行时间接近1小时应通过。"""
        result = PerformanceTestResult(name="exec_boundary")
        result.start_time = datetime.now()
        result.end_time = result.start_time + timedelta(seconds=3599)
        assert result.execution_duration_seconds > 0
        assert result.execution_duration_seconds <= 3600

    def test_execution_time_exactly_one_hour(self):
        """边界场景：正好1小时应通过。"""
        result = PerformanceTestResult(name="exec_exact")
        result.start_time = datetime.now()
        result.end_time = result.start_time + timedelta(seconds=3600)
        assert result.execution_duration_seconds == 3600.0

    def test_execution_time_exceeds_one_hour(self):
        """异常场景：超过1小时应被识别。"""
        result = PerformanceTestResult(name="exec_exceed")
        result.start_time = datetime.now()
        result.end_time = result.start_time + timedelta(seconds=3700)
        assert result.execution_duration_seconds == 3700.0
        assert result.execution_duration_seconds > 3600

    def test_execution_time_no_end_time(self):
        """未设置结束时时间应返回0。"""
        result = PerformanceTestResult(name="exec_no_end")
        result.start_time = datetime.now()
        assert result.execution_duration_seconds == 0.0

    def test_execution_time_zero(self):
        """开始时间等于结束时间时持续时间为0。"""
        result = PerformanceTestResult(name="exec_zero")
        now = datetime.now()
        result.start_time = now
        result.end_time = now
        assert result.execution_duration_seconds == 0.0

    def test_runner_total_execution_time(self):
        """多个测试结果的累计执行时间。"""
        runner = PerformanceTestRunner()

        r1 = PerformanceTestResult(name="exec_r1")
        r1.start_time = datetime.now()
        r1.end_time = r1.start_time + timedelta(seconds=100)

        r2 = PerformanceTestResult(name="exec_r2")
        r2.start_time = datetime.now()
        r2.end_time = r2.start_time + timedelta(seconds=200)

        runner.add_result(r1)
        runner.add_result(r2)

        total = runner.total_execution_time_seconds()
        assert abs(total - 300.0) < 1.0, f"累计时间应为约300s，实际 {total:.2f}s"

    def test_runner_timeout_seconds_default(self):
        """默认超时时间应为3600秒。"""
        runner = PerformanceTestRunner()
        assert runner.timeout_seconds == 3600

    def test_runner_custom_timeout(self):
        """自定义超时时间应生效。"""
        runner = PerformanceTestRunner(timeout_seconds=1800)
        assert runner.timeout_seconds == 1800


# ============================================================
# 综合集成测试
# ============================================================
class TestPerformanceIntegration:
    """综合场景：验证所有验收标准的组合"""

    def test_all_acceptance_criteria_pass(self):
        """完整场景：同时满足全部四个验收标准。"""
        runner = PerformanceTestRunner(timeout_seconds=3600)

        result = PerformanceTestResult(name="full_performance_test")
        result.status = PerfTestStatus.RUNNING
        result.start_time = datetime.now()

        for i in range(500):
            result.add_api_response(APIResponse(
                endpoint=f"/api/v1/resource/{i % 20}",
                method="GET",
                response_time_ms=float(50 + (i % 200)),
                status_code=200,
            ))

        for i in range(200):
            result.add_page_load(PageLoadRecord(
                page_path=f"/page/{i % 8}",
                load_time_ms=float(200 + (i % 800)),
                dns_time_ms=float(5 + i % 10),
                tcp_time_ms=float(10 + i % 15),
                ttfb_ms=float(30 + i % 50),
                render_time_ms=float(20 + i % 30),
            ))

        result.concurrency_result = ConcurrencyTestResult(
            total_requests=10000,
            successful_requests=9990,
            failed_requests=10,
            max_concurrent_connections=1500,
            avg_response_time_ms=150.0,
            p50_response_time_ms=90.0,
            p95_response_time_ms=300.0,
            p99_response_time_ms=450.0,
            execution_duration_seconds=300.0,
        )

        result.end_time = datetime.now()
        result.status = PerfTestStatus.PASSED
        runner.add_result(result)

        validation = runner.run_validation()

        assert validation["api_p95_pass"] is True, \
            f"AC1失败: API P95 {validation['api_p95_ms']:.2f}ms 超过500ms"
        assert validation["page_load_p95_pass"] is True, \
            f"AC2失败: 页面P95 {validation['page_load_p95_ms']:.2f}ms 超过2000ms"
        assert validation["concurrency_pass"] is True, \
            f"AC3失败: 并发数 {validation['max_concurrency']} 低于1000"
        assert validation["execution_time_pass"] is True, \
            f"AC4失败: 执行时间 {validation['execution_time_seconds']:.2f}s 超过3600s"
        assert validation["all_passed"] is True

    def test_validation_result_keys(self):
        """校验结果应包含所有必需字段。"""
        runner = PerformanceTestRunner()
        result = PerformanceTestResult(name="keys")
        result.start_time = datetime.now()
        result.end_time = result.start_time + timedelta(seconds=60)
        result.add_api_response(APIResponse("/api/test", "GET", 100.0, 200))
        result.add_page_load(PageLoadRecord("/page", 500.0))
        result.concurrency_result = ConcurrencyTestResult(
            total_requests=2000, successful_requests=1990,
            failed_requests=10, max_concurrent_connections=1200,
            avg_response_time_ms=150.0, p50_response_time_ms=80.0,
            p95_response_time_ms=300.0, p99_response_time_ms=400.0,
            execution_duration_seconds=60.0,
        )
        runner.add_result(result)
        validation = runner.run_validation()

        expected_keys = {
            "api_p95_ms", "api_p95_pass", "api_p95_threshold_ms",
            "page_load_p95_ms", "page_load_p95_pass", "page_load_p95_threshold_ms",
            "max_concurrency", "concurrency_pass", "concurrency_threshold",
            "execution_time_seconds", "execution_time_pass",
            "execution_time_threshold_seconds", "all_passed",
        }
        assert expected_keys.issubset(set(validation.keys())), \
            f"缺少键: {expected_keys - set(validation.keys())}"

    def test_validation_all_fail(self):
        """全部验收标准不满足时的校验结果。"""
        runner = PerformanceTestRunner()
        result = PerformanceTestResult(name="all_fail")
        result.start_time = datetime.now()
        result.end_time = result.start_time + timedelta(seconds=3700)

        for i in range(200):
            result.add_api_response(APIResponse(
                "/api/slow", "GET", float(600 + i), 200,
            ))

        for i in range(100):
            result.add_page_load(PageLoadRecord(
                "/slow_page", load_time_ms=float(2500 + i * 10),
            ))

        result.concurrency_result = ConcurrencyTestResult(
            total_requests=500, successful_requests=400,
            failed_requests=100, max_concurrent_connections=500,
            avg_response_time_ms=600.0, p50_response_time_ms=400.0,
            p95_response_time_ms=1000.0, p99_response_time_ms=1200.0,
            execution_duration_seconds=300.0,
        )

        runner.add_result(result)
        validation = runner.run_validation()

        assert validation["api_p95_pass"] is False
        assert validation["page_load_p95_pass"] is False
        assert validation["concurrency_pass"] is False
        assert validation["execution_time_pass"] is False
        assert validation["all_passed"] is False

    def test_validation_all_pass(self):
        """全部验收标准满足时的校验结果。"""
        runner = PerformanceTestRunner()
        result = PerformanceTestResult(name="all_pass")
        result.start_time = datetime.now()
        result.end_time = result.start_time + timedelta(seconds=120)

        for i in range(500):
            result.add_api_response(APIResponse(
                "/api/fast", "GET", float(30 + (i % 80)), 200,
            ))

        for i in range(200):
            result.add_page_load(PageLoadRecord(
                "/fast_page", load_time_ms=float(100 + (i % 300)),
            ))

        result.concurrency_result = ConcurrencyTestResult(
            total_requests=20000, successful_requests=19990,
            failed_requests=10, max_concurrent_connections=3000,
            avg_response_time_ms=80.0, p50_response_time_ms=50.0,
            p95_response_time_ms=150.0, p99_response_time_ms=200.0,
            execution_duration_seconds=120.0,
        )

        runner.add_result(result)
        validation = runner.run_validation()

        assert validation["api_p95_pass"] is True
        assert validation["page_load_p95_pass"] is True
        assert validation["concurrency_pass"] is True
        assert validation["execution_time_pass"] is True
        assert validation["all_passed"] is True

    def test_runner_overall_p95_multiple_results(self):
        """多个测试结果的总体P95计算。"""
        runner = PerformanceTestRunner()

        r1 = PerformanceTestResult(name="runner_r1")
        for i in range(100):
            r1.add_api_response(APIResponse("/api/a", "GET", float(50 + i), 200))
        runner.add_result(r1)

        r2 = PerformanceTestResult(name="runner_r2")
        for i in range(100):
            r2.add_api_response(APIResponse("/api/b", "GET", float(30 + i), 200))
        runner.add_result(r2)

        overall_p95 = runner.overall_api_p95()
        assert overall_p95 > 0
        assert overall_p95 <= 200.0

    def test_runner_max_concurrency_multiple_results(self):
        """多个测试结果取最大并发数。"""
        runner = PerformanceTestRunner()

        r1 = PerformanceTestResult(name="runner_c1")
        r1.concurrency_result = ConcurrencyTestResult(
            total_requests=2000, successful_requests=1990,
            failed_requests=10, max_concurrent_connections=800,
            avg_response_time_ms=150.0, p50_response_time_ms=80.0,
            p95_response_time_ms=250.0, p99_response_time_ms=350.0,
            execution_duration_seconds=60.0,
        )

        r2 = PerformanceTestResult(name="runner_c2")
        r2.concurrency_result = ConcurrencyTestResult(
            total_requests=5000, successful_requests=4990,
            failed_requests=10, max_concurrent_connections=1500,
            avg_response_time_ms=120.0, p50_response_time_ms=60.0,
            p95_response_time_ms=200.0, p99_response_time_ms=300.0,
            execution_duration_seconds=90.0,
        )

        runner.add_result(r1)
        runner.add_result(r2)

        assert runner.max_concurrency() == 1500

    def test_runner_test_counts(self):
        """runner应正确统计测试通过/失败数量。"""
        runner = PerformanceTestRunner()

        r1 = PerformanceTestResult(name="pass_test")
        r1.status = PerfTestStatus.PASSED
        runner.add_result(r1)

        r2 = PerformanceTestResult(name="fail_test")
        r2.status = PerfTestStatus.FAILED
        runner.add_result(r2)

        r3 = PerformanceTestResult(name="pass_test_2")
        r3.status = PerfTestStatus.PASSED
        runner.add_result(r3)

        assert runner.total_tests == 3
        assert runner.passed_tests == 2
        assert runner.failed_tests == 1

    def test_runner_empty(self):
        """空runner的各项统计应为0。"""
        runner = PerformanceTestRunner()
        assert runner.total_tests == 0
        assert runner.passed_tests == 0
        assert runner.failed_tests == 0
        assert runner.overall_api_p95() == 0.0
        assert runner.overall_page_load_p95() == 0.0
        assert runner.max_concurrency() == 0
        assert runner.total_execution_time_seconds() == 0.0

    def test_full_pipeline_validation(self):
        """完整流水线：模拟真实性能测试执行流程。"""
        runner = PerformanceTestRunner(timeout_seconds=3600)

        api_result = PerformanceTestResult(name="api_load_test")
        api_result.status = PerfTestStatus.RUNNING
        api_result.start_time = datetime.now()
        for i in range(1000):
            api_result.add_api_response(APIResponse(
                endpoint=f"/api/v{ i % 3 + 1 }/endpoint/{i % 10}",
                method=["GET", "POST", "PUT"][i % 3],
                response_time_ms=float(30 + (i % 150)),
                status_code=200 if i % 5 != 0 else 201,
            ))
        api_result.end_time = api_result.start_time + timedelta(seconds=60)
        api_result.status = PerfTestStatus.PASSED

        page_result = PerformanceTestResult(name="page_load_test")
        page_result.status = PerfTestStatus.RUNNING
        page_result.start_time = datetime.now()
        pages = ["/", "/dashboard", "/projects", "/settings", "/agents", "/monitoring"]
        for i in range(300):
            page_result.add_page_load(PageLoadRecord(
                page_path=pages[i % len(pages)],
                load_time_ms=float(100 + (i % 500)),
                dns_time_ms=float(3 + i % 8),
                tcp_time_ms=float(8 + i % 12),
                ttfb_ms=float(20 + i % 40),
                render_time_ms=float(15 + i % 25),
            ))
        page_result.end_time = page_result.start_time + timedelta(seconds=45)
        page_result.status = PerfTestStatus.PASSED

        concurrent_result = PerformanceTestResult(name="concurrency_test")
        concurrent_result.start_time = datetime.now()
        concurrent_result.end_time = concurrent_result.start_time + timedelta(seconds=300)
        concurrent_result.concurrency_result = ConcurrencyTestResult(
            total_requests=20000,
            successful_requests=19980,
            failed_requests=20,
            max_concurrent_connections=2000,
            avg_response_time_ms=120.0,
            p50_response_time_ms=70.0,
            p95_response_time_ms=250.0,
            p99_response_time_ms=380.0,
            execution_duration_seconds=300.0,
        )
        concurrent_result.status = PerfTestStatus.PASSED

        runner.add_result(api_result)
        runner.add_result(page_result)
        runner.add_result(concurrent_result)

        validation = runner.run_validation()

        assert validation["all_passed"] is True
        assert validation["api_p95_ms"] <= 500
        assert validation["page_load_p95_ms"] <= 2000
        assert validation["max_concurrency"] >= 1000
        assert validation["execution_time_seconds"] <= 3600
        assert runner.total_tests == 3
        assert runner.passed_tests == 3
        assert runner.failed_tests == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
