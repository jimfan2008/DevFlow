import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import JSONResponse
from enum import Enum
from typing import List, Dict, Optional
import time


# ============================================================
# 被测试的业务代码（模拟实现）
# ============================================================

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TokenBudgetManager:
    """Token预算管理"""

    def __init__(self, daily_limit: int = 10000):
        self.daily_limit = daily_limit
        self.used_tokens = 0

    def consume(self, tokens: int) -> bool:
        if self.used_tokens + tokens > self.daily_limit:
            return False
        self.used_tokens += tokens
        return True

    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used_tokens)

    def reset(self):
        self.used_tokens = 0


class CircuitBreaker:
    """熔断器"""

    def __init__(self, token_manager: TokenBudgetManager, threshold_ratio: float = 0.95):
        self.token_manager = token_manager
        self.threshold_ratio = threshold_ratio
        self.state = CircuitState.CLOSED
        self._trip_time: Optional[datetime] = None
        self.cooldown_seconds = 30

    def is_allowed(self) -> bool:
        if self.state == CircuitState.OPEN:
            if self._trip_time and (datetime.now() - self._trip_time).total_seconds() >= self.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        if self.token_manager.remaining() <= self.token_manager.daily_limit * (1 - self.threshold_ratio):
            self._trip()
            return False
        return True

    def _trip(self):
        self.state = CircuitState.OPEN
        self._trip_time = datetime.now()


class QueueRateLimiter:
    """排队限流器"""

    def __init__(self, max_queue_size: int = 100, avg_wait_seconds: float = 15.0):
        self.queue: List[Dict] = []
        self.max_queue_size = max_queue_size
        self.avg_wait_seconds = avg_wait_seconds

    def enqueue(self, request_id: str) -> Optional[Dict]:
        if len(self.queue) >= self.max_queue_size:
            return None
        position = len(self.queue) + 1
        estimated_wait = position * self.avg_wait_seconds
        entry = {
            "request_id": request_id,
            "position": position,
            "enqueued_at": datetime.now().isoformat(),
            "estimated_wait_time": estimated_wait,
        }
        self.queue.append(entry)
        return entry

    def dequeue(self) -> Optional[Dict]:
        if not self.queue:
            return None
        return self.queue.pop(0)


class LLMRequestHandler:
    """LLM请求处理器 - 核心被测类"""

    def __init__(self, circuit_breaker: CircuitBreaker, queue_limiter: QueueRateLimiter):
        self.circuit_breaker = circuit_breaker
        self.queue_limiter = queue_limiter

    async def handle_request(self, request_id: str, prompt: str, estimated_tokens: int = 100) -> Dict:
        if self.circuit_breaker.is_allowed():
            # 正常处理
            consumed = self.circuit_breaker.token_manager.consume(estimated_tokens)
            if not consumed:
                return self._fallback_to_queue(request_id)
            return {
                "status": "processed",
                "request_id": request_id,
                "result": f"LLM response for: {prompt[:50]}",
            }
        # 熔断触发，降级至排队限流
        return self._fallback_to_queue(request_id)

    def _fallback_to_queue(self, request_id: str) -> Dict:
        entry = self.queue_limiter.enqueue(request_id)
        if entry is None:
            return {
                "status": "rejected",
                "reason": "queue_full",
                "request_id": request_id,
            }
        return {
            "status": "queued_rate_limited",
            "request_id": request_id,
            "queue_position": entry["position"],
            "estimated_wait_time": entry["estimated_wait_time"],
        }


# FastAPI 应用用于集成测试
app = FastAPI()

_circuit_breaker = CircuitBreaker(TokenBudgetManager(daily_limit=100))
_queue_limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
_handler = LLMRequestHandler(_circuit_breaker, _queue_limiter)


@app.post("/v1/chat/completions")
async def chat_completions(request: dict):
    request_id = request.get("request_id", "default-req")
    prompt = request.get("prompt", "")
    tokens = request.get("estimated_tokens", 100)
    result = await _handler.handle_request(request_id, prompt, tokens)
    if result["status"] == "queued_rate_limited":
        return JSONResponse(status_code=202, content=result)
    elif result["status"] == "rejected":
        return JSONResponse(status_code=503, content=result)
    else:
        return JSONResponse(status_code=200, content=result)


# ============================================================
# 单元测试
# ============================================================

class TestCircuitBreakerTrips:
    """测试：Token预算接近上限时，熔断器正确打开"""

    def test_circuit_opens_when_budget_exceeded(self):
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        # 消耗 960 tokens，超过阈值 950
        manager.used_tokens = 960
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_allowed() is False
        assert breaker.state == CircuitState.OPEN

    def test_circuit_closes_below_threshold(self):
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        manager.used_tokens = 900
        assert breaker.is_allowed() is True
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_opens_at_exact_threshold_boundary(self):
        """精确阈值边界：used=950, remaining=50, threshold=50 (95% of 1000)"""
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        # remaining = 50, threshold = 1000 * (1 - 0.95) = 50
        # remaining <= threshold 为 True，应触发熔断
        manager.used_tokens = 950
        assert breaker.is_allowed() is False
        assert breaker.state == CircuitState.OPEN

    def test_circuit_does_not_open_just_below_threshold(self):
        """精确阈值边界：used=949, remaining=51, threshold=50"""
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        # remaining = 51 > threshold = 50，不应触发
        manager.used_tokens = 949
        assert breaker.is_allowed() is True
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerCooldown:
    """测试：OPEN→HALF_OPEN 冷却超时转换"""

    def test_open_to_half_open_after_cooldown(self):
        """冷却时间过后，OPEN 自动转为 HALF_OPEN 并允许请求"""
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.state = CircuitState.OPEN
        breaker._trip_time = datetime.now() - timedelta(seconds=31)  # 冷却已过
        assert breaker.is_allowed() is True
        assert breaker.state == CircuitState.HALF_OPEN

    def test_open_stays_open_before_cooldown(self):
        """冷却时间未到，保持 OPEN 状态并拒绝请求"""
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.state = CircuitState.OPEN
        breaker._trip_time = datetime.now() - timedelta(seconds=5)  # 冷却未到
        assert breaker.is_allowed() is False
        assert breaker.state == CircuitState.OPEN

    def test_open_to_half_open_at_exact_cooldown_boundary(self):
        """精确冷却时间边界：刚好等于 cooldown_seconds"""
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.cooldown_seconds = 10
        breaker.state = CircuitState.OPEN
        breaker._trip_time = datetime.now() - timedelta(seconds=10)
        assert breaker.is_allowed() is True
        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_allows_request(self):
        """HALF_OPEN 状态下 is_allowed 返回 True"""
        manager = TokenBudgetManager(daily_limit=1000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.state = CircuitState.HALF_OPEN
        assert breaker.is_allowed() is True


class TestTokenBudgetManager:
    """测试：Token 预算管理"""

    def test_reset_clears_used_tokens(self):
        """reset() 后 used_tokens 归零"""
        manager = TokenBudgetManager(daily_limit=1000)
        manager.used_tokens = 800
        manager.reset()
        assert manager.used_tokens == 0
        assert manager.remaining() == 1000

    def test_consume_returns_false_when_exceeds_limit(self):
        """consume 请求的 token 超出剩余时返回 False"""
        manager = TokenBudgetManager(daily_limit=100)
        manager.used_tokens = 90
        result = manager.consume(20)  # 90 + 20 > 100
        assert result is False
        assert manager.used_tokens == 90  # 不会增加

    def test_consume_returns_true_and_increments_when_within_limit(self):
        """consume 在限额内时返回 True 并增加计数"""
        manager = TokenBudgetManager(daily_limit=1000)
        manager.used_tokens = 500
        result = manager.consume(200)
        assert result is True
        assert manager.used_tokens == 700

    def test_consume_returns_false_at_exact_boundary(self):
        """consume 刚好等于剩余时返回 True"""
        manager = TokenBudgetManager(daily_limit=100)
        manager.used_tokens = 50
        result = manager.consume(50)  # 50 + 50 == 100
        assert result is True
        assert manager.used_tokens == 100

    def test_consume_returns_false_when_one_over(self):
        """consume 刚好超出 1 时返回 False"""
        manager = TokenBudgetManager(daily_limit=100)
        manager.used_tokens = 50
        result = manager.consume(51)  # 50 + 51 > 100
        assert result is False
        assert manager.used_tokens == 50


class TestQueueRateLimiterEnqueue:
    """测试：排队限流器正确入队"""

    def test_enqueue_returns_position_and_wait_time(self):
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        result = limiter.enqueue("req-001")
        assert result is not None
        assert result["position"] == 1
        assert result["estimated_wait_time"] == 5.0

    def test_multiple_enqueues_increment_position(self):
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        r1 = limiter.enqueue("req-001")
        r2 = limiter.enqueue("req-002")
        r3 = limiter.enqueue("req-003")
        assert r1["position"] == 1
        assert r2["position"] == 2
        assert r3["position"] == 3
        assert r3["estimated_wait_time"] == 15.0

    def test_enqueue_returns_none_when_queue_full(self):
        limiter = QueueRateLimiter(max_queue_size=2, avg_wait_seconds=5.0)
        limiter.enqueue("req-001")
        limiter.enqueue("req-002")
        result = limiter.enqueue("req-003")
        assert result is None

    def test_dequeue_removes_first_element(self):
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        limiter.enqueue("req-001")
        limiter.enqueue("req-002")
        first = limiter.dequeue()
        assert first["request_id"] == "req-001"
        second = limiter.dequeue()
        assert second["request_id"] == "req-002"


class TestLLMRequestHandlerFallbackToQueue:
    """测试：熔断后请求正确降级至排队限流"""

    @pytest.mark.asyncio
    async def test_request_falls_back_to_queue_when_circuit_open(self):
        manager = TokenBudgetManager(daily_limit=1000)
        manager.used_tokens = 990  # 超过阈值
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        # 先触发一次让熔断器打开
        breaker.is_allowed()
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        handler = LLMRequestHandler(breaker, limiter)
        result = await handler.handle_request("req-test", "hello world", 50)
        assert result["status"] == "queued_rate_limited"
        assert "queue_position" in result
        assert "estimated_wait_time" in result
        assert result["queue_position"] == 1

    @pytest.mark.asyncio
    async def test_request_not_rejected_when_circuit_open_and_queue_has_space(self):
        manager = TokenBudgetManager(daily_limit=1000)
        manager.used_tokens = 990
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.is_allowed()
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        handler = LLMRequestHandler(breaker, limiter)
        result = await handler.handle_request("req-test", "prompt", 50)
        assert result["status"] != "rejected"
        assert result["status"] == "queued_rate_limited"

    @pytest.mark.asyncio
    async def test_request_rejected_only_when_queue_full(self):
        manager = TokenBudgetManager(daily_limit=1000)
        manager.used_tokens = 990
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.is_allowed()
        limiter = QueueRateLimiter(max_queue_size=2, avg_wait_seconds=5.0)
        limiter.enqueue("req-pre1")
        limiter.enqueue("req-pre2")
        handler = LLMRequestHandler(breaker, limiter)
        result = await handler.handle_request("req-test", "prompt", 50)
        assert result["status"] == "rejected"
        assert result["reason"] == "queue_full"

    @pytest.mark.asyncio
    async def test_normal_request_succeeds_when_circuit_closed(self):
        manager = TokenBudgetManager(daily_limit=10000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        handler = LLMRequestHandler(breaker, limiter)
        result = await handler.handle_request("req-normal", "hello", 100)
        assert result["status"] == "processed"
        assert "result" in result

    @pytest.mark.asyncio
    async def test_response_contains_all_required_fields(self):
        """验证响应体包含 status, queue_position, estimated_wait_time"""
        manager = TokenBudgetManager(daily_limit=1000)
        manager.used_tokens = 990
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.is_allowed()
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=10.0)
        handler = LLMRequestHandler(breaker, limiter)
        result = await handler.handle_request("req-full-check", "test prompt", 50)
        assert result["status"] == "queued_rate_limited"
        assert isinstance(result["queue_position"], int)
        assert result["queue_position"] > 0
        assert isinstance(result["estimated_wait_time"], (int, float))
        assert result["estimated_wait_time"] > 0

    @pytest.mark.asyncio
    async def test_half_open_state_allows_normal_processing(self):
        """HALF_OPEN 状态下请求正常处理而非降级排队"""
        manager = TokenBudgetManager(daily_limit=10000)
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        # 手动设置 HALF_OPEN 状态
        breaker.state = CircuitState.HALF_OPEN
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        handler = LLMRequestHandler(breaker, limiter)
        result = await handler.handle_request("req-half-open", "hello", 100)
        assert result["status"] == "processed"
        assert len(limiter.queue) == 0  # 不应入队

    @pytest.mark.asyncio
    async def test_fallback_when_consume_fails_in_half_open(self):
        """HALF_OPEN 下 consume 失败时仍降级至排队"""
        manager = TokenBudgetManager(daily_limit=100)
        manager.used_tokens = 90
        breaker = CircuitBreaker(manager, threshold_ratio=0.95)
        breaker.state = CircuitState.HALF_OPEN  # 手动设置
        limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        handler = LLMRequestHandler(breaker, limiter)
        result = await handler.handle_request("req-consume-fail", "hello", 50)
        assert result["status"] == "queued_rate_limited"
        assert result["queue_position"] == 1


# ============================================================
# 集成测试（HTTP 层）
# ============================================================

class TestHTTPEndpointFallback:
    """测试：HTTP端点在熔断后返回202和正确响应体"""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        """每个测试前重置状态"""
        global _circuit_breaker, _queue_limiter, _handler
        _circuit_breaker = CircuitBreaker(TokenBudgetManager(daily_limit=100))
        _queue_limiter = QueueRateLimiter(max_queue_size=100, avg_wait_seconds=5.0)
        _handler = LLMRequestHandler(_circuit_breaker, _queue_limiter)

    @pytest.mark.asyncio
    async def test_http_202_on_circuit_breaker_tripped(self):
        """熔断触发后，HTTP端点返回202状态码"""
        # 手动让熔断器进入打开状态
        _circuit_breaker.token_manager.used_tokens = 98
        _circuit_breaker.is_allowed()  # 触发熔断
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/chat/completions",
                json={"request_id": "http-req-001", "prompt": "hello", "estimated_tokens": 10},
            )
        assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_http_response_body_contains_required_fields(self):
        """响应体包含 status=queued_rate_limited, queue_position, estimated_wait_time"""
        _circuit_breaker.token_manager.used_tokens = 98
        _circuit_breaker.is_allowed()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/chat/completions",
                json={"request_id": "http-req-002", "prompt": "test", "estimated_tokens": 10},
            )
        body = resp.json()
        assert body["status"] == "queued_rate_limited"
        assert "queue_position" in body
        assert "estimated_wait_time" in body
        assert body["queue_position"] >= 1
        assert body["estimated_wait_time"] > 0

    @pytest.mark.asyncio
    async def test_multiple_requests_get_sequential_positions(self):
        """多个熔断后的请求获得递增的排队位置"""
        _circuit_breaker.token_manager.used_tokens = 98
        _circuit_breaker.is_allowed()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post("/v1/chat/completions", json={"request_id": "seq-1", "prompt": "a", "estimated_tokens": 5})
            r2 = await client.post("/v1/chat/completions", json={"request_id": "seq-2", "prompt": "b", "estimated_tokens": 5})
            r3 = await client.post("/v1/chat/completions", json={"request_id": "seq-3", "prompt": "c", "estimated_tokens": 5})
        b1, b2, b3 = r1.json(), r2.json(), r3.json()
        assert b1["queue_position"] == 1
        assert b2["queue_position"] == 2
        assert b3["queue_position"] == 3
        assert r1.status_code == r2.status_code == r3.status_code == 202

    @pytest.mark.asyncio
    async def test_normal_request_returns_200_not_202(self):
        """未触发熔断的请求正常返回200"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/chat/completions",
                json={"request_id": "normal-req", "prompt": "hello", "estimated_tokens": 10},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "processed"
