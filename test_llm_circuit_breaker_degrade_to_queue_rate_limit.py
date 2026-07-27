import uuid
import time
import math
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import pytest
from pydantic import BaseModel


# ====================================================================
# 被测试的领域模型
# ====================================================================

class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    TRIPPED = "tripped"


class RequestStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    QUEUED_RATE_LIMITED = "queued_rate_limited"


@dataclass
class TokenBudgetRecord:
    """Token 预算记录"""
    id: str
    date_str: str
    daily_tokens_used: int
    daily_hard_limit: int
    circuit_breaker_state: CircuitBreakerState
    tripped_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.daily_hard_limit - self.daily_tokens_used)

    @property
    def utilization_ratio(self) -> float:
        if self.daily_hard_limit == 0:
            return 0.0
        return self.daily_tokens_used / self.daily_hard_limit

    def is_circuit_breaker_tripped(self) -> bool:
        return self.circuit_breaker_state == CircuitBreakerState.TRIPPED


@dataclass
class QueuedRequest:
    """排队中的请求"""
    request_id: str
    user_id: str
    estimated_tokens: int
    enqueued_at: datetime
    priority: int = 0  # 数值越小优先级越高
    status: str = "waiting"

    @property
    def wait_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.enqueued_at).total_seconds()


@dataclass
class QueueResponse:
    """排队限流响应"""
    status_code: int
    status: str
    queue_position: int
    estimated_wait_time: float
    request_id: str
    message: str


class RequestQueue:
    """请求排队队列（FIFO + 优先级）"""

    def __init__(self, max_queue_size: int = 100):
        self._queue: List[QueuedRequest] = []
        self._max_queue_size = max_queue_size

    def enqueue(self, request: QueuedRequest) -> int:
        """将请求加入队列，返回排队位置"""
        if len(self._queue) >= self._max_queue_size:
            raise QueueFullError(f"队列已满，当前大小 {len(self._queue)}，最大 {self._max_queue_size}")
        self._queue.append(request)
        return len(self._queue)

    def dequeue(self) -> Optional[QueuedRequest]:
        """从队列头部取出一个请求"""
        if not self._queue:
            return None
        self._queue.sort(key=lambda r: (r.priority, r.enqueued_at))
        return self._queue.pop(0)

    def get_queue_length(self) -> int:
        return len(self._queue)

    def get_position(self, request_id: str) -> Optional[int]:
        """获取请求在队列中的位置"""
        self._queue.sort(key=lambda r: (r.priority, r.enqueued_at))
        for i, req in enumerate(self._queue):
            if req.request_id == request_id:
                return i + 1
        return None

    def is_full(self) -> bool:
        return len(self._queue) >= self._max_queue_size

    def clear(self):
        self._queue.clear()


class QueueFullError(Exception):
    """队列已满异常"""
    pass


class TokenBudgetManager:
    """Token 预算管理器"""

    CIRCUIT_BREAKER_THRESHOLD = 1.0  # 100% 使用时熔断

    def __init__(self, daily_hard_limit: int = 100000):
        self.daily_hard_limit = daily_hard_limit

    def check_and_consume(
        self, record: TokenBudgetRecord, estimated_tokens: int
    ) -> bool:
        """检查 Token 预算并消耗"""
        if record.daily_tokens_used + estimated_tokens > record.daily_hard_limit:
            # Token 预算超限，触发熔断
            record.circuit_breaker_state = CircuitBreakerState.TRIPPED
            record.tripped_at = datetime.now(timezone.utc)
            return False  # 无法消耗
        record.daily_tokens_used += estimated_tokens
        return True


class CircuitBreaker:
    """熔断器：检测 Token 预算超限"""

    def __init__(self, budget_manager: TokenBudgetManager):
        self.budget_manager = budget_manager

    def should_trip(self, record: TokenBudgetRecord) -> bool:
        """判断是否应该熔断。若因 Token 耗尽触发，则自动将状态设为 TRIPPED"""
        if record.circuit_breaker_state == CircuitBreakerState.TRIPPED:
            return True
        if record.daily_tokens_used >= record.daily_hard_limit:
            # Token 耗尽，自动触发熔断
            record.circuit_breaker_state = CircuitBreakerState.TRIPPED
            record.tripped_at = datetime.now(timezone.utc)
            return True
        return False

    def trip(self, record: TokenBudgetRecord):
        """执行熔断"""
        record.circuit_breaker_state = CircuitBreakerState.TRIPPED
        record.tripped_at = datetime.now(timezone.utc)


class QueueRateLimiter:
    """排队限流器：熔断后降级至排队模式"""

    # 默认排队等待时间估算参数
    AVG_PROCESS_TIME_PER_REQUEST = 2.0  # 秒
    ESTIMATED_WAIT_PER_REQUEST = 3.0    # 秒

    def __init__(self, queue: RequestQueue, max_queue_size: int = 100):
        self.queue = queue
        self.max_queue_size = max_queue_size

    def handle_degraded_request(
        self,
        user_id: str,
        estimated_tokens: int,
        priority: int = 0,
    ) -> QueueResponse:
        """处理降级后的请求：加入排队队列"""
        request_id = str(uuid.uuid4())
        request = QueuedRequest(
            request_id=request_id,
            user_id=user_id,
            estimated_tokens=estimated_tokens,
            enqueued_at=datetime.now(timezone.utc),
            priority=priority,
        )

        queue_position = self.queue.enqueue(request)
        estimated_wait = self._calculate_estimated_wait(queue_position)

        return QueueResponse(
            status_code=202,
            status=RequestStatus.QUEUED_RATE_LIMITED.value,
            queue_position=queue_position,
            estimated_wait_time=round(estimated_wait, 2),
            request_id=request_id,
            message="请求已进入排队队列，请稍后查看处理结果",
        )

    def _calculate_estimated_wait(self, queue_position: int) -> float:
        """根据排队位置估算等待时间"""
        return self.ESTIMATED_WAIT_PER_REQUEST * queue_position

    def process_next(self) -> Optional[QueuedRequest]:
        """处理下一个排队中的请求"""
        return self.queue.dequeue()


class LlmApiRequestHandler:
    """LLM API 请求处理器：整合熔断器和排队限流器"""

    def __init__(
        self,
        budget_manager: TokenBudgetManager,
        circuit_breaker: CircuitBreaker,
        queue_rate_limiter: QueueRateLimiter,
    ):
        self.budget_manager = budget_manager
        self.circuit_breaker = circuit_breaker
        self.queue_rate_limiter = queue_rate_limiter

    def handle_request(
        self,
        record: TokenBudgetRecord,
        user_id: str,
        estimated_tokens: int,
        priority: int = 0,
    ) -> QueueResponse:
        """
        处理 LLM API 请求
        - 如果 Token 预算未超限：正常处理（这里只模拟正常通过）
        - 如果 Token 预算超限 / 熔断已触发：降级至排队限流
        """
        # 检查是否熔断
        if self.circuit_breaker.should_trip(record):
            # 熔断状态下，请求降级至排队限流，不直接拒绝
            return self.queue_rate_limiter.handle_degraded_request(
                user_id=user_id,
                estimated_tokens=estimated_tokens,
                priority=priority,
            )

        # 检查能否正常消耗 Token
        consumed = self.budget_manager.check_and_consume(record, estimated_tokens)
        if not consumed:
            # Token 预算超限，先触发熔断，再降级至排队
            self.circuit_breaker.trip(record)
            return self.queue_rate_limiter.handle_degraded_request(
                user_id=user_id,
                estimated_tokens=estimated_tokens,
                priority=priority,
            )

        # 正常处理（未触发熔断，Token 充足）
        # 返回一个表示正常通过的特殊响应
        return QueueResponse(
            status_code=200,
            status=RequestStatus.ACCEPTED.value,
            queue_position=0,
            estimated_wait_time=0.0,
            request_id=str(uuid.uuid4()),
            message="请求已正常处理",
        )


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def budget_manager():
    return TokenBudgetManager(daily_hard_limit=100000)


@pytest.fixture
def circuit_breaker(budget_manager):
    return CircuitBreaker(budget_manager=budget_manager)


@pytest.fixture
def request_queue():
    return RequestQueue(max_queue_size=100)


@pytest.fixture
def queue_rate_limiter(request_queue):
    return QueueRateLimiter(queue=request_queue, max_queue_size=100)


@pytest.fixture
def handler(budget_manager, circuit_breaker, queue_rate_limiter):
    return LlmApiRequestHandler(
        budget_manager=budget_manager,
        circuit_breaker=circuit_breaker,
        queue_rate_limiter=queue_rate_limiter,
    )


@pytest.fixture
def normal_budget_record():
    """Token 预算充足的记录"""
    return TokenBudgetRecord(
        id=str(uuid.uuid4()),
        date_str="2025-01-15",
        daily_tokens_used=50000,
        daily_hard_limit=100000,
        circuit_breaker_state=CircuitBreakerState.CLOSED,
    )


@pytest.fixture
def exhausted_budget_record():
    """Token 预算已耗尽的记录"""
    return TokenBudgetRecord(
        id=str(uuid.uuid4()),
        date_str="2025-01-15",
        daily_tokens_used=100000,
        daily_hard_limit=100000,
        circuit_breaker_state=CircuitBreakerState.CLOSED,
    )


@pytest.fixture
def tripped_budget_record():
    """已熔断的记录"""
    return TokenBudgetRecord(
        id=str(uuid.uuid4()),
        date_str="2025-01-15",
        daily_tokens_used=100000,
        daily_hard_limit=100000,
        circuit_breaker_state=CircuitBreakerState.TRIPPED,
        tripped_at=datetime.now(timezone.utc),
    )


# ====================================================================
# 测试用例：LLM API 熔断后降级至排队限流
# ====================================================================

class TestCircuitBreakerDegradeToQueueRateLimit:
    """熔断后降级至排队限流模式"""

    # ── 核心验收标准：请求进入排队队列，不直接拒绝 ──

    def test_request_enters_queue_when_circuit_breaker_tripped(self, handler, tripped_budget_record, request_queue):
        """请求进入排队队列"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        # 请求应该进入队列
        assert request_queue.get_queue_length() == 1

    def test_return_http_202_when_degraded(self, handler, tripped_budget_record):
        """熔断后返回 HTTP 202"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.status_code == 202

    def test_response_body_contains_status_queued_rate_limited(self, handler, tripped_budget_record):
        """响应 Body 包含 status=queued_rate_limited"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.status == "queued_rate_limited"

    def test_response_body_contains_queue_position(self, handler, tripped_budget_record):
        """响应 Body 包含 queue_position"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.queue_position is not None
        assert isinstance(response.queue_position, int)
        assert response.queue_position >= 1

    def test_response_body_contains_estimated_wait_time(self, handler, tripped_budget_record):
        """响应 Body 包含 estimated_wait_time"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.estimated_wait_time is not None
        assert isinstance(response.estimated_wait_time, (int, float))
        assert response.estimated_wait_time > 0

    def test_request_not_directly_rejected(self, handler, tripped_budget_record):
        """请求不直接拒绝（不返回 429）"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.status_code != 429
        assert response.status != "rejected"

    def test_response_contains_request_id(self, handler, tripped_budget_record):
        """响应包含 request_id"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.request_id is not None
        assert len(response.request_id) > 0

    def test_response_contains_message(self, handler, tripped_budget_record):
        """响应包含描述性消息"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.message is not None
        assert len(response.message) > 0

    # ── Token 预算刚超限时：先触发熔断再降级至排队 ──

    def test_token_exceeded_trips_circuit_breaker_then_degrades_to_queue(self, handler, normal_budget_record):
        """Token 预算超限 → 触发熔断 → 降级至排队限流"""
        # 先用完剩余 Token
        handler.handle_request(
            record=normal_budget_record,
            user_id="user-001",
            estimated_tokens=50000,
        )
        # 此时 Token 已耗尽，再发请求
        response = handler.handle_request(
            record=normal_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        # 应降级至排队限流
        assert response.status_code == 202
        assert response.status == "queued_rate_limited"
        # 熔断器应已触发
        assert normal_budget_record.circuit_breaker_state == CircuitBreakerState.TRIPPED
        assert normal_budget_record.tripped_at is not None

    def test_circuit_breaker_tripped_at_is_set_when_trip(self, handler, normal_budget_record):
        """熔断触发时 tripped_at 字段被设置"""
        handler.handle_request(
            record=normal_budget_record,
            user_id="user-001",
            estimated_tokens=50000,
        )
        handler.handle_request(
            record=normal_budget_record,
            user_id="user-002",
            estimated_tokens=500,
        )
        assert normal_budget_record.tripped_at is not None
        assert isinstance(normal_budget_record.tripped_at, datetime)

    # ── 排队位置递增 ──

    def test_queue_position_increments_for_concurrent_requests(self, handler, tripped_budget_record, request_queue):
        """多个请求排队时，位置递增"""
        resp1 = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        resp2 = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-002",
            estimated_tokens=600,
        )
        resp3 = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-003",
            estimated_tokens=700,
        )
        assert resp1.queue_position == 1
        assert resp2.queue_position == 2
        assert resp3.queue_position == 3

    def test_estimated_wait_time_scales_with_queue_position(self, handler, tripped_budget_record):
        """预估等待时间随排队位置递增"""
        resp1 = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        resp2 = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-002",
            estimated_tokens=600,
        )
        resp3 = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-003",
            estimated_tokens=700,
        )
        assert resp1.estimated_wait_time < resp2.estimated_wait_time < resp3.estimated_wait_time

    def test_first_request_estimated_wait(self, handler, tripped_budget_record):
        """第一个排队的请求，预估等待时间为 1 × ESTIMATED_WAIT_PER_REQUEST"""
        response = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.estimated_wait_time == pytest.approx(
            QueueRateLimiter.ESTIMATED_WAIT_PER_REQUEST * 1
        )

    def test_third_request_estimated_wait(self, handler, tripped_budget_record):
        """第三个排队的请求，预估等待时间为 3 × ESTIMATED_WAIT_PER_REQUEST"""
        handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
        )
        handler.handle_request(
            record=tripped_budget_record,
            user_id="user-002",
            estimated_tokens=600,
        )
        resp3 = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-003",
            estimated_tokens=700,
        )
        assert resp3.estimated_wait_time == pytest.approx(
            QueueRateLimiter.ESTIMATED_WAIT_PER_REQUEST * 3
        )

    # ── 非熔断状态下正常请求不进入排队 ──

    def test_normal_request_not_queued_when_budget_available(self, handler, normal_budget_record, request_queue):
        """Token 充足时，正常请求不进入排队队列"""
        response = handler.handle_request(
            record=normal_budget_record,
            user_id="user-001",
            estimated_tokens=1000,
        )
        assert response.status_code == 200
        assert response.status == "accepted"
        assert request_queue.get_queue_length() == 0

    def test_normal_request_has_zero_queue_position(self, handler, normal_budget_record):
        """正常请求的 queue_position 为 0"""
        response = handler.handle_request(
            record=normal_budget_record,
            user_id="user-001",
            estimated_tokens=1000,
        )
        assert response.queue_position == 0

    def test_normal_request_has_zero_estimated_wait(self, handler, normal_budget_record):
        """正常请求的 estimated_wait_time 为 0"""
        response = handler.handle_request(
            record=normal_budget_record,
            user_id="user-001",
            estimated_tokens=1000,
        )
        assert response.estimated_wait_time == 0.0

    # ── 优先级排队 ──

    def test_higher_priority_request_can_be_set(self, handler, tripped_budget_record, request_queue):
        """高优先级请求可以设置"""
        response_low = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-001",
            estimated_tokens=500,
            priority=10,
        )
        response_high = handler.handle_request(
            record=tripped_budget_record,
            user_id="user-002",
            estimated_tokens=600,
            priority=1,
        )
        # 两个请求都进入队列
        assert request_queue.get_queue_length() == 2
        assert response_low.status_code == 202
        assert response_high.status_code == 202

    # ── 队列容量边界 ──

    def test_queue_full_raises_error(self, queue_rate_limiter, request_queue):
        """队列满时抛出异常"""
        small_queue = RequestQueue(max_queue_size=2)
        limiter = QueueRateLimiter(queue=small_queue, max_queue_size=2)
        limiter.handle_degraded_request(user_id="user-001", estimated_tokens=500)
        limiter.handle_degraded_request(user_id="user-002", estimated_tokens=600)

        with pytest.raises(QueueFullError, match="队列已满"):
            limiter.handle_degraded_request(user_id="user-003", estimated_tokens=700)

    def test_dequeue_removes_from_queue(self, request_queue):
        """出队后队列大小减小"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            estimated_tokens=500,
            enqueued_at=datetime.now(timezone.utc),
        )
        request_queue.enqueue(req)
        assert request_queue.get_queue_length() == 1

        dequeued = request_queue.dequeue()
        assert dequeued is not None
        assert dequeued.request_id == "req-001"
        assert request_queue.get_queue_length() == 0

    def test_dequeue_returns_none_when_empty(self, request_queue):
        """空队列出队返回 None"""
        assert request_queue.dequeue() is None

    # ── Token 预算记录状态变化 ──

    def test_circuit_breaker_state_changes_from_closed_to_tripped(self, budget_manager, circuit_breaker, normal_budget_record):
        """熔断器状态从 closed 变为 tripped"""
        assert normal_budget_record.circuit_breaker_state == CircuitBreakerState.CLOSED
        # 用光预算
        budget_manager.check_and_consume(normal_budget_record, 50000)
        # 再请求，触发熔断
        assert circuit_breaker.should_trip(normal_budget_record) is True
        circuit_breaker.trip(normal_budget_record)
        assert normal_budget_record.circuit_breaker_state == CircuitBreakerState.TRIPPED

    def test_trip_sets_tripped_at(self, circuit_breaker, normal_budget_record):
        """熔断触发时设置 tripped_at"""
        circuit_breaker.trip(normal_budget_record)
        assert normal_budget_record.tripped_at is not None
        assert isinstance(normal_budget_record.tripped_at, datetime)

    def test_should_trip_returns_true_when_state_is_tripped(self, circuit_breaker, tripped_budget_record):
        """状态为 tripped 时 should_trip 返回 True"""
        assert circuit_breaker.should_trip(tripped_budget_record) is True

    def test_should_trip_returns_true_when_tokens_exhausted(self, circuit_breaker, exhausted_budget_record):
        """Token 耗尽时 should_trip 返回 True"""
        assert circuit_breaker.should_trip(exhausted_budget_record) is True

    def test_should_trip_returns_false_when_budget_available(self, circuit_breaker, normal_budget_record):
        """Token 充足时 should_trip 返回 False"""
        assert circuit_breaker.should_trip(normal_budget_record) is False

    # ── 完整流程：正常 → 超限 → 熔断 → 排队 ──

    def test_full_flow_normal_then_degrade(self, handler, normal_budget_record, request_queue):
        """完整流程：正常处理 → 用尽 Token → 熔断 → 降级排队"""
        # 第 1 步：正常请求
        resp1 = handler.handle_request(
            record=normal_budget_record,
            user_id="user-001",
            estimated_tokens=10000,
        )
        assert resp1.status_code == 200
        assert resp1.status == "accepted"
        assert request_queue.get_queue_length() == 0

        # 第 2 步：继续消耗直到即将超限
        handler.handle_request(
            record=normal_budget_record,
            user_id="user-002",
            estimated_tokens=40000,
        )

        # 第 3 步：再次请求，触发熔断并降级排队
        resp3 = handler.handle_request(
            record=normal_budget_record,
            user_id="user-003",
            estimated_tokens=50000,
        )
        assert resp3.status_code == 202
        assert resp3.status == "queued_rate_limited"
        assert resp3.queue_position >= 1
        assert resp3.estimated_wait_time > 0
        assert normal_budget_record.circuit_breaker_state == CircuitBreakerState.TRIPPED
        assert request_queue.get_queue_length() >= 1

    # ── 多个用户并发排队 ──

    def test_multiple_users_queued_simultaneously(self, handler, tripped_budget_record, request_queue):
        """多个用户同时排队"""
        responses = []
        for i in range(5):
            resp = handler.handle_request(
                record=tripped_budget_record,
                user_id=f"user-{i:03d}",
                estimated_tokens=500,
            )
            responses.append(resp)

        # 所有请求都应该进入排队
        assert request_queue.get_queue_length() == 5
        for i, resp in enumerate(responses):
            assert resp.status_code == 202
            assert resp.status == "queued_rate_limited"
            assert resp.queue_position == i + 1

    def test_each_queued_request_has_unique_id(self, handler, tripped_budget_record):
        """每个排队的请求有唯一 ID"""
        responses = []
        for i in range(10):
            resp = handler.handle_request(
                record=tripped_budget_record,
                user_id=f"user-{i:03d}",
                estimated_tokens=500,
            )
            responses.append(resp)

        request_ids = [r.request_id for r in responses]
        assert len(request_ids) == len(set(request_ids))


# ====================================================================
# 独立单元测试
# ====================================================================

class TestTokenBudgetManager:
    """Token 预算管理器独立测试"""

    def test_consume_success(self, budget_manager, normal_budget_record):
        """正常消耗 Token"""
        result = budget_manager.check_and_consume(normal_budget_record, 10000)
        assert result is True
        assert normal_budget_record.daily_tokens_used == 60000

    def test_consume_fails_when_exceeds_limit(self, budget_manager, normal_budget_record):
        """超出限额时消耗失败"""
        result = budget_manager.check_and_consume(normal_budget_record, 60000)
        assert result is False
        assert normal_budget_record.circuit_breaker_state == CircuitBreakerState.TRIPPED

    def test_consume_exactly_at_limit(self, budget_manager, normal_budget_record):
        """恰好在限额时消耗成功"""
        result = budget_manager.check_and_consume(normal_budget_record, 50000)
        assert result is True
        assert normal_budget_record.daily_tokens_used == 100000


class TestCircuitBreaker:
    """熔断器独立测试"""

    def test_trip_sets_state(self, circuit_breaker, normal_budget_record):
        """熔断设置状态为 tripped"""
        circuit_breaker.trip(normal_budget_record)
        assert normal_budget_record.circuit_breaker_state == CircuitBreakerState.TRIPPED

    def test_should_trip_on_exact_limit(self, circuit_breaker, exhausted_budget_record):
        """恰好等于限额时应该熔断"""
        assert circuit_breaker.should_trip(exhausted_budget_record) is True

    def test_should_trip_on_over_limit(self, circuit_breaker):
        """超过限额时应该熔断"""
        record = TokenBudgetRecord(
            id=str(uuid.uuid4()),
            date_str="2025-01-15",
            daily_tokens_used=100001,
            daily_hard_limit=100000,
            circuit_breaker_state=CircuitBreakerState.CLOSED,
        )
        assert circuit_breaker.should_trip(record) is True

    def test_should_not_trip_below_limit(self, circuit_breaker, normal_budget_record):
        """未达限额时不应熔断"""
        assert circuit_breaker.should_trip(normal_budget_record) is False


class TestRequestQueue:
    """请求队列独立测试"""

    def test_enqueue_returns_position(self, request_queue):
        """入队返回排队位置"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            estimated_tokens=500,
            enqueued_at=datetime.now(timezone.utc),
        )
        pos = request_queue.enqueue(req)
        assert pos == 1

    def test_get_position_for_existing_request(self, request_queue):
        """获取存在的请求位置"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            estimated_tokens=500,
            enqueued_at=datetime.now(timezone.utc),
        )
        request_queue.enqueue(req)
        assert request_queue.get_position("req-001") == 1

    def test_get_position_for_nonexistent_request(self, request_queue):
        """获取不存在的请求位置返回 None"""
        assert request_queue.get_position("nonexistent") is None

    def test_is_full_when_at_capacity(self):
        """达到容量时 is_full 为 True"""
        queue = RequestQueue(max_queue_size=2)
        queue.enqueue(QueuedRequest(
            request_id="r1", user_id="u1", estimated_tokens=500,
            enqueued_at=datetime.now(timezone.utc),
        ))
        queue.enqueue(QueuedRequest(
            request_id="r2", user_id="u2", estimated_tokens=600,
            enqueued_at=datetime.now(timezone.utc),
        ))
        assert queue.is_full() is True

    def test_is_not_full_when_below_capacity(self, request_queue):
        """未满时 is_full 为 False"""
        assert request_queue.is_full() is False

    def test_fifo_order(self, request_queue):
        """FIFO 顺序"""
        req1 = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            estimated_tokens=500,
            enqueued_at=datetime.now(timezone.utc),
        )
        req2 = QueuedRequest(
            request_id="req-002",
            user_id="user-002",
            estimated_tokens=600,
            enqueued_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        )
        request_queue.enqueue(req1)
        request_queue.enqueue(req2)
        assert request_queue.dequeue().request_id == "req-001"
        assert request_queue.dequeue().request_id == "req-002"


class TestQueueRateLimiter:
    """排队限流器独立测试"""

    def test_handle_degraded_returns_202(self, queue_rate_limiter):
        """降级请求返回 202"""
        response = queue_rate_limiter.handle_degraded_request(
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.status_code == 202

    def test_handle_degraded_returns_queued_status(self, queue_rate_limiter):
        """降级请求返回 queued_rate_limited 状态"""
        response = queue_rate_limiter.handle_degraded_request(
            user_id="user-001",
            estimated_tokens=500,
        )
        assert response.status == "queued_rate_limited"

    def test_process_next_removes_from_queue(self, queue_rate_limiter):
        """处理下一个请求时从队列移除"""
        queue_rate_limiter.handle_degraded_request(
            user_id="user-001",
            estimated_tokens=500,
        )
        assert queue_rate_limiter.queue.get_queue_length() == 1
        result = queue_rate_limiter.process_next()
        assert result is not None
        assert queue_rate_limiter.queue.get_queue_length() == 0

    def test_process_next_returns_none_when_empty(self, queue_rate_limiter):
        """空队列时 process_next 返回 None"""
        assert queue_rate_limiter.process_next() is None


class TestTokenBudgetRecord:
    """Token 预算记录独立测试"""

    def test_remaining_tokens(self, normal_budget_record):
        """计算剩余 Token"""
        assert normal_budget_record.remaining_tokens == 50000

    def test_utilization_ratio(self, normal_budget_record):
        """计算使用率"""
        assert normal_budget_record.utilization_ratio == 0.5

    def test_utilization_ratio_at_limit(self, exhausted_budget_record):
        """达到限额时使用率为 1.0"""
        assert exhausted_budget_record.utilization_ratio == 1.0

    def test_remaining_tokens_zero_at_limit(self, exhausted_budget_record):
        """达到限额时剩余 Token 为 0"""
        assert exhausted_budget_record.remaining_tokens == 0

    def test_is_circuit_breaker_tripped(self, tripped_budget_record):
        """判断熔断器是否已触发"""
        assert tripped_budget_record.is_circuit_breaker_tripped() is True

    def test_is_not_tripped_when_closed(self, normal_budget_record):
        """未熔断时返回 False"""
        assert normal_budget_record.is_circuit_breaker_tripped() is False
