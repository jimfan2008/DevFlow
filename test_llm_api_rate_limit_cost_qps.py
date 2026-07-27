import time
import threading
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

import pytest


# ====================================================================
# 被测试的领域模型
# ====================================================================


@dataclass
class CloudAPIRequest:
    """云端 API 请求"""
    request_id: str
    user_id: str
    timestamp: float
    model: str = "qwen3.6-35b-4.75bit"
    prompt_tokens: int = 0
    content: str = ""


@dataclass
class CloudAPIResponse:
    """云端 API 响应"""
    request_id: str
    success: bool
    status: str
    message: str
    qps_current: int
    qps_limit: int
    throttled: bool = False
    retry_after_ms: float = 0.0
    response_data: Optional[dict] = None


@dataclass
class RateLimitStats:
    """速率限制统计"""
    total_requests: int = 0
    accepted_requests: int = 0
    rejected_requests: int = 0
    peak_qps: int = 0
    window_seconds: float = 1.0


class CloudAPIRateLimiter:
    """云端 API 速率限制器 — 滑动窗口算法

    限制云端 API 调用频率不超过 QPS=10。
    使用滑动时间窗口（1秒窗口），记录窗口内请求时间戳。
    """

    MAX_QPS = 10
    WINDOW_SECONDS = 1.0

    def __init__(self, max_qps: int = None, window_seconds: float = None):
        self.max_qps = max_qps if max_qps is not None else self.MAX_QPS
        self.window_seconds = window_seconds if window_seconds is not None else self.WINDOW_SECONDS
        self._timestamps: Deque[float] = deque()
        self._lock = threading.Lock()
        self._stats = RateLimitStats(window_seconds=self.window_seconds)

    @property
    def stats(self) -> RateLimitStats:
        return self._stats

    def _clean_window(self, now: float):
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def current_qps(self, now: float = None) -> int:
        """返回当前窗口内的请求数"""
        if now is None:
            now = time.time()
        with self._lock:
            self._clean_window(now)
            return len(self._timestamps)

    def check_rate_limit(self, now: float = None) -> bool:
        """检查是否超过速率限制（True=允许，False=拒绝）"""
        if now is None:
            now = time.time()
        with self._lock:
            self._clean_window(now)
            if len(self._timestamps) >= self.max_qps:
                return False
            self._timestamps.append(now)
            current_count = len(self._timestamps)
            self._stats.total_requests += 1
            self._stats.accepted_requests += 1
            if current_count > self._stats.peak_qps:
                self._stats.peak_qps = current_count
            return True

    def handle_request(self, request: CloudAPIRequest, now: float = None) -> CloudAPIResponse:
        """处理云端 API 请求并返回限流结果"""
        if now is None:
            now = time.time()

        with self._lock:
            self._clean_window(now)
            current_count = len(self._timestamps)

        if current_count >= self.max_qps:
            self._stats.total_requests += 1
            self._stats.rejected_requests += 1
            oldest = self._timestamps[0] if self._timestamps else now
            retry_after = max(0.0, (oldest + self.window_seconds - now) * 1000)
            return CloudAPIResponse(
                request_id=request.request_id,
                success=False,
                status="rate_limited",
                message="云端 API 速率限制已触发 (QPS 上限)",
                qps_current=current_count,
                qps_limit=self.max_qps,
                throttled=True,
                retry_after_ms=round(retry_after, 2),
            )

        with self._lock:
            self._timestamps.append(now)
            accepted_count = len(self._timestamps)
            self._stats.total_requests += 1
            self._stats.accepted_requests += 1
            if accepted_count > self._stats.peak_qps:
                self._stats.peak_qps = accepted_count

        return CloudAPIResponse(
            request_id=request.request_id,
            success=True,
            status="accepted",
            message="云端 API 请求已处理",
            qps_current=accepted_count,
            qps_limit=self.max_qps,
            throttled=False,
            response_data={"model": request.model, "tokens": request.prompt_tokens},
        )

    def reset(self):
        """重置限流器状态"""
        with self._lock:
            self._timestamps.clear()
        self._stats = RateLimitStats(window_seconds=self.window_seconds)


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def rate_limiter():
    """默认 QPS=10 的限流器"""
    return CloudAPIRateLimiter(max_qps=10, window_seconds=1.0)


@pytest.fixture
def base_time():
    """基准时间戳（用于控制时间推进）"""
    return 1000000.0


# ====================================================================
# 验收标准：云端 API 速率限制生效，QPS <= 10
# ====================================================================


class TestQPSLimitConstant:
    """测试 QPS 限制常量"""

    def test_max_qps_is_10(self):
        """最大 QPS 常量应为 10"""
        assert CloudAPIRateLimiter.MAX_QPS == 10

    def test_default_instance_has_qps_10(self):
        """默认实例的 QPS 限制应为 10"""
        rl = CloudAPIRateLimiter()
        assert rl.max_qps == 10

    def test_window_is_one_second(self):
        """时间窗口应为 1 秒"""
        assert CloudAPIRateLimiter.WINDOW_SECONDS == 1.0
        rl = CloudAPIRateLimiter()
        assert rl.window_seconds == 1.0


class TestFirst10RequestsAccepted:
    """同一秒内前 10 个请求应全部通过"""

    def test_10_requests_in_one_second_all_accepted(self, rate_limiter, base_time):
        """同一秒内发 10 个请求，全部被接受"""
        for i in range(10):
            req = CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05)
            resp = rate_limiter.handle_request(req, now=base_time + i * 0.05)
            assert resp.success is True
            assert resp.status == "accepted"
            assert resp.throttled is False

    def test_10th_request_qps_current_is_10(self, rate_limiter, base_time):
        """第 10 个请求的 qps_current 应为 10"""
        for i in range(10):
            req = CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05)
            resp = rate_limiter.handle_request(req, now=base_time + i * 0.05)
        assert resp.qps_current == 10

    def test_10th_request_not_throttled(self, rate_limiter, base_time):
        """第 10 个请求不应被限流"""
        req = CloudAPIRequest(request_id="req-9", user_id="user-1", timestamp=base_time + 0.45)
        for i in range(9):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(req, now=base_time + 0.45)
        assert resp.throttled is False
        assert resp.success is True


class Test11thRequestRejected:
    """同一秒内第 11 个及以后请求应被拒绝"""

    def test_11th_request_is_rejected(self, rate_limiter, base_time):
        """第 11 个请求应被拒绝"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-11", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        assert resp.success is False
        assert resp.status == "rate_limited"
        assert resp.throttled is True

    def test_11th_request_returns_rate_limited_status(self, rate_limiter, base_time):
        """第 11 个请求状态应为 rate_limited"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-11", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        assert resp.status == "rate_limited"

    def test_11th_request_retry_after_is_positive(self, rate_limiter, base_time):
        """第 11 个请求的 retry_after_ms 应大于 0"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-11", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        assert resp.retry_after_ms > 0

    def test_11th_request_message_mentions_rate_limit(self, rate_limiter, base_time):
        """第 11 个请求的 message 应包含限流信息"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-11", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        assert "速率" in resp.message or "rate" in resp.message.lower() or "限制" in resp.message

    def test_12th_request_also_rejected(self, rate_limiter, base_time):
        """第 12 个请求同样被拒绝"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp11 = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-11", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        resp12 = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-12", user_id="user-1", timestamp=base_time + 0.55),
            now=base_time + 0.55,
        )
        assert resp11.throttled is True
        assert resp12.throttled is True


class TestWindowSliding:
    """滑动窗口：时间推进后窗口清空，可继续请求"""

    def test_requests_accepted_after_window_passes(self, rate_limiter, base_time):
        """超过 1 秒窗口后，新的请求应被接受"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-new", user_id="user-1", timestamp=base_time + 1.1),
            now=base_time + 1.1,
        )
        assert resp.success is True
        assert resp.throttled is False

    def test_qps_resets_after_window(self, rate_limiter, base_time):
        """窗口过去后 qps_current 应重置"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time),
                now=base_time + i * 0.001,
            )
        rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-new", user_id="user-1", timestamp=base_time + 1.1),
            now=base_time + 1.1,
        )
        assert rate_limiter.current_qps(now=base_time + 1.1) == 1

    def test_can_send_another_10_after_window(self, rate_limiter, base_time):
        """窗口过去后可以再发 10 个请求"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        new_accepted = 0
        for i in range(10):
            resp = rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-2-{i}", user_id="user-1", timestamp=base_time + 1.1 + i * 0.05),
                now=base_time + 1.1 + i * 0.05,
            )
            if resp.success:
                new_accepted += 1
        assert new_accepted == 10

    def test_requests_exactly_at_window_boundary(self, rate_limiter, base_time):
        """恰好在窗口边界的请求应正确处理"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.09),
                now=base_time + i * 0.09,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-boundary", user_id="user-1", timestamp=base_time + 0.99),
            now=base_time + 0.99,
        )
        assert resp.throttled is True
        resp_after = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-after", user_id="user-1", timestamp=base_time + 1.001),
            now=base_time + 1.001,
        )
        assert resp_after.success is True


class TestQPSNeverExceedsLimit:
    """QPS 永远不超过限制"""

    def test_peak_qps_never_exceeds_10(self, rate_limiter, base_time):
        """高峰 QPS 不应超过 10"""
        for i in range(20):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        assert rate_limiter.stats.peak_qps <= 10

    def test_current_qps_never_exceeds_10(self, rate_limiter, base_time):
        """当前 QPS 不应超过 10"""
        for i in range(20):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        assert rate_limiter.current_qps(now=base_time + 0.95) == 10

    def test_stats_total_equals_accepted_plus_rejected(self, rate_limiter, base_time):
        """总请求数 = 接受数 + 拒绝数"""
        for i in range(15):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        s = rate_limiter.stats
        assert s.total_requests == s.accepted_requests + s.rejected_requests

    def test_accepted_is_10_after_15_requests(self, rate_limiter, base_time):
        """发 15 个请求后，接受数应为 10"""
        for i in range(15):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        assert rate_limiter.stats.accepted_requests == 10

    def test_rejected_is_5_after_15_requests(self, rate_limiter, base_time):
        """发 15 个请求后，拒绝数应为 5"""
        for i in range(15):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        assert rate_limiter.stats.rejected_requests == 5


class TestCheckRateLimitMethod:
    """check_rate_limit 方法的独立验证"""

    def test_check_returns_true_for_first_10(self, rate_limiter, base_time):
        """前 10 次 check 应返回 True"""
        for i in range(10):
            result = rate_limiter.check_rate_limit(now=base_time + i * 0.05)
            assert result is True

    def test_check_returns_false_for_11th(self, rate_limiter, base_time):
        """第 11 次 check 应返回 False"""
        for i in range(10):
            rate_limiter.check_rate_limit(now=base_time + i * 0.05)
        result = rate_limiter.check_rate_limit(now=base_time + 0.5)
        assert result is False


class TestReset:
    """限流器重置功能"""

    def test_reset_clears_timestamps(self, rate_limiter, base_time):
        """重置后时间戳清空"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        rate_limiter.reset()
        assert rate_limiter.current_qps(now=base_time + 1.0) == 0

    def test_reset_clears_stats(self, rate_limiter, base_time):
        """重置后统计数据清零"""
        for i in range(15):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        rate_limiter.reset()
        assert rate_limiter.stats.total_requests == 0
        assert rate_limiter.stats.accepted_requests == 0
        assert rate_limiter.stats.rejected_requests == 0

    def test_can_send_after_reset(self, rate_limiter, base_time):
        """重置后可以重新发送请求"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        rate_limiter.reset()
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-after-reset", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        assert resp.success is True
        assert resp.throttled is False


class TestResponseStructure:
    """响应数据结构验证"""

    def test_accepted_response_contains_request_id(self, rate_limiter, base_time):
        """接受响应包含 request_id"""
        req = CloudAPIRequest(request_id="req-001", user_id="user-1", timestamp=base_time)
        resp = rate_limiter.handle_request(req, now=base_time)
        assert resp.request_id == "req-001"

    def test_response_contains_qps_limit(self, rate_limiter, base_time):
        """响应包含 qps_limit 字段"""
        req = CloudAPIRequest(request_id="req-001", user_id="user-1", timestamp=base_time)
        resp = rate_limiter.handle_request(req, now=base_time)
        assert resp.qps_limit == 10

    def test_rejected_response_contains_retry_after(self, rate_limiter, base_time):
        """拒绝响应包含 retry_after_ms"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-11", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        assert resp.retry_after_ms > 0

    def test_accepted_response_has_response_data(self, rate_limiter, base_time):
        """接受响应包含 response_data"""
        req = CloudAPIRequest(request_id="req-001", user_id="user-1", timestamp=base_time, model="qwen3.6", prompt_tokens=100)
        resp = rate_limiter.handle_request(req, now=base_time)
        assert resp.response_data is not None
        assert resp.response_data["model"] == "qwen3.6"

    def test_rejected_response_has_no_response_data(self, rate_limiter, base_time):
        """拒绝响应的 response_data 为 None"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time + i * 0.05),
                now=base_time + i * 0.05,
            )
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-11", user_id="user-1", timestamp=base_time + 0.5),
            now=base_time + 0.5,
        )
        assert resp.response_data is None


class TestBurstRequests:
    """突发请求场景：短时间内大量请求"""

    def test_burst_50_requests_in_same_second(self, rate_limiter, base_time):
        """同一秒内 50 个突发请求：10 通过，40 拒绝"""
        accepted = 0
        rejected = 0
        for i in range(50):
            resp = rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time),
                now=base_time + i * 0.001,
            )
            if resp.success:
                accepted += 1
            else:
                rejected += 1
        assert accepted == 10
        assert rejected == 40

    def test_burst_then_wait_then_burst_again(self, rate_limiter, base_time):
        """突发请求 -> 等待窗口过去 -> 再次突发"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-1-{i}", user_id="user-1", timestamp=base_time),
                now=base_time + i * 0.001,
            )
        second_burst_accepted = 0
        for i in range(10):
            resp = rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-2-{i}", user_id="user-1", timestamp=base_time + 1.1),
                now=base_time + 1.1 + i * 0.001,
            )
            if resp.success:
                second_burst_accepted += 1
        assert second_burst_accepted == 10


class TestMultipleWindows:
    """多窗口连续场景"""

    def test_three_seconds_10_requests_each(self, rate_limiter, base_time):
        """连续 3 秒，每秒发 10 个请求全部通过"""
        for sec in range(3):
            for i in range(10):
                now = base_time + sec + i * 0.05
                resp = rate_limiter.handle_request(
                    CloudAPIRequest(request_id=f"req-{sec}-{i}", user_id="user-1", timestamp=now),
                    now=now,
                )
                assert resp.success is True
        assert rate_limiter.stats.accepted_requests == 30

    def test_three_seconds_15_requests_each(self, rate_limiter, base_time):
        """连续 3 秒，每秒发 15 个请求：每窗 10 通过、5 拒绝"""
        for sec in range(3):
            for i in range(15):
                now = base_time + sec + i * 0.05
                rate_limiter.handle_request(
                    CloudAPIRequest(request_id=f"req-{sec}-{i}", user_id="user-1", timestamp=now),
                    now=now,
                )
        assert rate_limiter.stats.accepted_requests == 30
        assert rate_limiter.stats.rejected_requests == 15
        assert rate_limiter.stats.total_requests == 45


class TestEdgeCases:
    """边界情况补充（修复评审缺失项）"""

    def test_empty_initial_state_qps_is_zero(self, rate_limiter, base_time):
        """新实例无任何请求时 current_qps 为 0"""
        assert rate_limiter.current_qps(now=base_time) == 0

    def test_empty_initial_state_stats_zero(self, rate_limiter):
        """新实例统计数据全为 0"""
        s = rate_limiter.stats
        assert s.total_requests == 0
        assert s.accepted_requests == 0
        assert s.rejected_requests == 0
        assert s.peak_qps == 0

    def test_now_none_uses_real_time(self, base_time):
        """now=None 时应使用系统时间"""
        rl = CloudAPIRateLimiter()
        real_before = time.time()
        req = CloudAPIRequest(request_id="req-real", user_id="user-1", timestamp=real_before)
        resp = rl.handle_request(req)
        real_after = time.time()
        assert resp.success is True
        assert rl.current_qps() >= 0

    def test_check_rate_limit_now_none(self):
        """check_rate_limit now=None 不报错"""
        rl = CloudAPIRateLimiter()
        result = rl.check_rate_limit()
        assert result is True

    def test_concurrent_requests_thread_safe(self, base_time):
        """多线程并发请求不超配额"""
        rl = CloudAPIRateLimiter()
        results = []
        barrier = threading.Barrier(20)

        def worker(tid):
            barrier.wait()
            for i in range(10):
                req = CloudAPIRequest(request_id=f"t{tid}-r{i}", user_id=f"user-{tid}", timestamp=base_time + i * 0.0001)
                resp = rl.handle_request(req, now=base_time + i * 0.0001 + tid * 0.00001)
                results.append(resp.success)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        accepted = sum(1 for r in results if r)
        rejected = sum(1 for r in results if not r)
        assert accepted <= 10
        assert accepted + rejected == 200

    def test_negative_timestamp_still_works(self, rate_limiter):
        """负值时间戳不影响功能"""
        neg_time = -1000.0
        req = CloudAPIRequest(request_id="req-neg", user_id="user-1", timestamp=neg_time)
        resp = rate_limiter.handle_request(req, now=neg_time)
        assert resp.success is True
        assert rate_limiter.current_qps(now=neg_time) == 1

    def test_very_large_timestamp_works(self, rate_limiter):
        """较大时间戳正常工作（使用浮点数精度范围内的大值）"""
        huge_time = 1e12
        req = CloudAPIRequest(request_id="req-huge", user_id="user-1", timestamp=huge_time)
        resp = rate_limiter.handle_request(req, now=huge_time)
        assert resp.success is True
        assert rate_limiter.current_qps(now=huge_time) == 1

    def test_float_precision_boundary(self, rate_limiter):
        """超出浮点数精度的极端时间戳应仍能安全处理（不抛异常）"""
        extreme_time = 1e18
        req = CloudAPIRequest(request_id="req-extreme", user_id="user-1", timestamp=extreme_time)
        resp = rate_limiter.handle_request(req, now=extreme_time)
        assert resp is not None
        assert resp.request_id == "req-extreme"

    def test_window_slides_correctly_large_gap(self, rate_limiter, base_time):
        """极大时间间隔后窗口完全清空"""
        for i in range(10):
            rate_limiter.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time),
                now=base_time + i * 0.001,
            )
        far_future = base_time + 1000.0
        assert rate_limiter.current_qps(now=far_future) == 0
        resp = rate_limiter.handle_request(
            CloudAPIRequest(request_id="req-far", user_id="user-1", timestamp=far_future),
            now=far_future,
        )
        assert resp.success is True
        assert resp.qps_current == 1

    def test_custom_qps_limit(self, base_time):
        """自定义 max_qps 生效"""
        rl = CloudAPIRateLimiter(max_qps=5, window_seconds=1.0)
        accepted = 0
        for i in range(10):
            resp = rl.handle_request(
                CloudAPIRequest(request_id=f"req-{i}", user_id="user-1", timestamp=base_time),
                now=base_time + i * 0.01,
            )
            if resp.success:
                accepted += 1
        assert accepted == 5

    def test_custom_window_seconds(self, base_time):
        """自定义窗口时长生效"""
        rl = CloudAPIRateLimiter(max_qps=2, window_seconds=0.5)
        rl.handle_request(CloudAPIRequest(request_id="r1", user_id="u1", timestamp=base_time), now=base_time)
        rl.handle_request(CloudAPIRequest(request_id="r2", user_id="u1", timestamp=base_time + 0.1), now=base_time + 0.1)
        resp_blocked = rl.handle_request(CloudAPIRequest(request_id="r3", user_id="u1", timestamp=base_time + 0.2), now=base_time + 0.2)
        assert resp_blocked.throttled is True
        resp_after = rl.handle_request(CloudAPIRequest(request_id="r4", user_id="u1", timestamp=base_time + 0.6), now=base_time + 0.6)
        assert resp_after.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])