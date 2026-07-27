import uuid
from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone, date, timedelta
from dataclasses import dataclass, field

import pytest


# ====================================================================
# 被测试的领域模型
# ====================================================================

class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    TRIPPED = "tripped"


class RequestStatus(str, Enum):
    ACCEPTED = "accepted"
    QUEUED_RATE_LIMITED = "queued_rate_limited"


FallbackLevel = Enum("FallbackLevel", "PRIMARY BACKUP CLOUD QUEUE")


@dataclass
class CloudAPIBudgetRecord:
    date_str: str
    daily_tokens_used: int
    daily_hard_limit: int
    circuit_breaker_state: CircuitBreakerState
    tripped_at: Optional[datetime] = None


@dataclass
class QueuedRequest:
    request_id: str
    user_id: str
    estimated_tokens: int
    enqueued_at: datetime
    priority: int = 0
    status: str = "waiting"


@dataclass
class QueueResponse:
    status_code: int
    status: str
    queue_position: int
    estimated_wait_time: float
    request_id: str
    message: str
    fallback_level: str


class RequestQueue:
    def __init__(self, max_queue_size: int = 100):
        self._queue: List[QueuedRequest] = []
        self._max_queue_size = max_queue_size

    def enqueue(self, request: QueuedRequest) -> int:
        if len(self._queue) >= self._max_queue_size:
            raise QueueFullError("队列已满")
        self._queue.append(request)
        return len(self._queue)

    def dequeue(self) -> Optional[QueuedRequest]:
        if not self._queue:
            return None
        self._queue.sort(key=lambda r: (r.priority, r.enqueued_at))
        return self._queue.pop(0)

    def get_queue_length(self) -> int:
        return len(self._queue)

    def clear(self):
        self._queue.clear()


class QueueFullError(Exception):
    pass


class CloudAPIBudgetManager:
    def __init__(self, daily_hard_limit: int = 10000, current_date: Optional[date] = None):
        self.daily_hard_limit = daily_hard_limit
        self._current_date = current_date

    @property
    def current_date(self) -> date:
        return self._current_date if self._current_date is not None else datetime.now(timezone.utc).date()

    def check_and_consume(self, record: CloudAPIBudgetRecord, estimated_tokens: int) -> bool:
        today = self.current_date.isoformat()
        if today != record.date_str:
            record.daily_tokens_used = 0
            record.date_str = today
            record.circuit_breaker_state = CircuitBreakerState.CLOSED
            record.tripped_at = None
        if record.daily_tokens_used + estimated_tokens > record.daily_hard_limit:
            record.circuit_breaker_state = CircuitBreakerState.TRIPPED
            record.tripped_at = datetime.now(timezone.utc)
            return False
        record.daily_tokens_used += estimated_tokens
        return True


class CloudAPICircuitBreaker:
    def __init__(self, budget_manager: CloudAPIBudgetManager):
        self.budget_manager = budget_manager

    def should_trip(self, record: CloudAPIBudgetRecord) -> bool:
        if record.circuit_breaker_state == CircuitBreakerState.TRIPPED:
            return True
        if record.daily_tokens_used >= record.daily_hard_limit:
            record.circuit_breaker_state = CircuitBreakerState.TRIPPED
            record.tripped_at = datetime.now(timezone.utc)
            return True
        return False

    def trip(self, record: CloudAPIBudgetRecord):
        record.circuit_breaker_state = CircuitBreakerState.TRIPPED
        record.tripped_at = datetime.now(timezone.utc)


class QueueRateLimiter:
    ESTIMATED_WAIT_PER_REQUEST = 3.0

    def __init__(self, queue: RequestQueue):
        self.queue = queue

    def handle_degraded_request(self, user_id: str, estimated_tokens: int, priority: int = 0) -> QueueResponse:
        request_id = str(uuid.uuid4())
        request = QueuedRequest(
            request_id=request_id, user_id=user_id, estimated_tokens=estimated_tokens,
            enqueued_at=datetime.now(timezone.utc), priority=priority,
        )
        queue_position = self.queue.enqueue(request)
        estimated_wait = self.ESTIMATED_WAIT_PER_REQUEST * queue_position
        return QueueResponse(
            status_code=202, status=RequestStatus.QUEUED_RATE_LIMITED.value,
            queue_position=queue_position, estimated_wait_time=round(estimated_wait, 2),
            request_id=request_id, message="云端 API 熔断，请求已进入排队队列",
            fallback_level=FallbackLevel.QUEUE.name,
        )

    def process_next(self) -> Optional[QueuedRequest]:
        return self.queue.dequeue()


class CloudAPIHandler:
    def __init__(self, budget_manager, circuit_breaker, queue_rate_limiter, fallback_level=None):
        self.budget_manager = budget_manager
        self.circuit_breaker = circuit_breaker
        self.queue_rate_limiter = queue_rate_limiter
        self.fallback_level = fallback_level or FallbackLevel.CLOUD
        self._record: Optional[CloudAPIBudgetRecord] = None

    def initialize_record(self, record: CloudAPIBudgetRecord):
        self._record = record

    def handle_request(self, user_id: str, estimated_tokens: int, priority: int = 0) -> QueueResponse:
        if self._record is None:
            raise RuntimeError("未初始化预算记录")
        record = self._record
        today = self.budget_manager.current_date.isoformat()
        if today != record.date_str:
            return self._reset_and_accept(record, user_id, estimated_tokens)
        if record.circuit_breaker_state == CircuitBreakerState.TRIPPED:
            return self.queue_rate_limiter.handle_degraded_request(user_id, estimated_tokens, priority)
        consumed = self.budget_manager.check_and_consume(record, estimated_tokens)
        if not consumed:
            self.circuit_breaker.trip(record)
            return self.queue_rate_limiter.handle_degraded_request(user_id, estimated_tokens, priority)
        return QueueResponse(
            status_code=200, status=RequestStatus.ACCEPTED.value,
            queue_position=0, estimated_wait_time=0.0,
            request_id=str(uuid.uuid4()), message="云端 API 请求已处理",
            fallback_level=self.fallback_level.name,
        )

    def _reset_and_accept(self, record: CloudAPIBudgetRecord, user_id: str, estimated_tokens: int) -> QueueResponse:
        today = self.budget_manager.current_date.isoformat()
        record.daily_tokens_used = 0
        record.date_str = today
        record.circuit_breaker_state = CircuitBreakerState.CLOSED
        record.tripped_at = None
        record.daily_tokens_used = estimated_tokens
        return QueueResponse(
            status_code=200, status=RequestStatus.ACCEPTED.value,
            queue_position=0, estimated_wait_time=0.0,
            request_id=str(uuid.uuid4()), message="新日期自动恢复，云端 API 请求已处理",
            fallback_level=self.fallback_level.name,
        )


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def budget_manager():
    return CloudAPIBudgetManager(daily_hard_limit=10000)

@pytest.fixture
def circuit_breaker(budget_manager):
    return CloudAPICircuitBreaker(budget_manager)

@pytest.fixture
def request_queue():
    return RequestQueue(max_queue_size=100)

@pytest.fixture
def queue_rate_limiter(request_queue):
    return QueueRateLimiter(queue=request_queue)

@pytest.fixture
def handler(budget_manager, circuit_breaker, queue_rate_limiter):
    return CloudAPIHandler(
        budget_manager=budget_manager, circuit_breaker=circuit_breaker,
        queue_rate_limiter=queue_rate_limiter, fallback_level=FallbackLevel.CLOUD,
    )

@pytest.fixture
def normal_record(budget_manager):
    return CloudAPIBudgetRecord(
        date_str=budget_manager.current_date.isoformat(), daily_tokens_used=3000,
        daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.CLOSED,
    )

@pytest.fixture
def tripped_record(budget_manager):
    return CloudAPIBudgetRecord(
        date_str=budget_manager.current_date.isoformat(), daily_tokens_used=10000,
        daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.TRIPPED,
        tripped_at=datetime.now(timezone.utc),
    )


# ====================================================================
# 验收标准 1：熔断后降级至排队限流
# ====================================================================

class TestCloudAPIBreakerDegradesToQueue:

    def test_tripped_request_returns_queued_rate_limited(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.status == "queued_rate_limited"

    def test_tripped_request_returns_http_202(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.status_code == 202

    def test_tripped_request_enters_queue(self, handler, tripped_record, request_queue):
        handler.initialize_record(tripped_record)
        handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert request_queue.get_queue_length() == 1

    def test_tripped_request_not_rejected_429(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.status_code != 429
        assert response.status != "rejected"

    def test_tripped_response_contains_queue_position(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.queue_position >= 1

    def test_tripped_response_contains_wait_time(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.estimated_wait_time > 0

    def test_tripped_response_contains_request_id(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.request_id is not None
        assert len(response.request_id) > 0

    def test_tripped_response_contains_message(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.message is not None
        assert len(response.message) > 0

    def test_tripped_response_fallback_level_is_queue(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.fallback_level == FallbackLevel.QUEUE.name

    def test_token_exceeded_triggers_trip_then_degrades(self, handler, normal_record, request_queue):
        handler.initialize_record(normal_record)
        handler.handle_request(user_id="user-001", estimated_tokens=7000)
        response = handler.handle_request(user_id="user-002", estimated_tokens=500)
        assert response.status == "queued_rate_limited"
        assert response.status_code == 202
        assert normal_record.circuit_breaker_state == CircuitBreakerState.TRIPPED
        assert normal_record.tripped_at is not None
        assert request_queue.get_queue_length() >= 1


# ====================================================================
# 验收标准 2：次日自动恢复
# ====================================================================

class TestNextDayAutoRecovery:

    def test_crossing_midnight_resets_budget(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=10000, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.TRIPPED, tripped_at=datetime.now(timezone.utc))
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 20)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert record.daily_tokens_used == 500
        assert response.status == "accepted"
        assert response.status_code == 200

    def test_crossing_midnight_resets_circuit_breaker(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=10000, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.TRIPPED, tripped_at=datetime.now(timezone.utc))
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 20)
        handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert record.circuit_breaker_state == CircuitBreakerState.CLOSED
        assert record.tripped_at is None

    def test_crossing_midnight_allows_normal_request(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=10000, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.TRIPPED)
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 20)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.status == "accepted"
        assert response.status_code == 200
        assert request_queue.get_queue_length() == 0

    def test_crossing_midnight_resets_date_str(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=10000, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.TRIPPED)
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 20)
        handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert record.date_str == "2025-07-20"

    def test_multiple_days_sequential(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=0, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.CLOSED)
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 19)
        handler.handle_request(user_id="u", estimated_tokens=10000)
        resp = handler.handle_request(user_id="u", estimated_tokens=1)
        assert resp.status == "queued_rate_limited"
        budget_manager._current_date = date(2025, 7, 20)
        request_queue.clear()
        resp = handler.handle_request(user_id="u", estimated_tokens=5000)
        assert resp.status == "accepted"
        assert record.date_str == "2025-07-20"
        assert record.circuit_breaker_state == CircuitBreakerState.CLOSED
        handler.handle_request(user_id="u", estimated_tokens=5000)
        resp = handler.handle_request(user_id="u", estimated_tokens=1)
        assert resp.status == "queued_rate_limited"
        budget_manager._current_date = date(2025, 7, 21)
        request_queue.clear()
        resp = handler.handle_request(user_id="u", estimated_tokens=1)
        assert resp.status == "accepted"
        assert record.date_str == "2025-07-21"

    def test_same_day_stays_tripped(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=10000, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.TRIPPED)
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 19)
        response = handler.handle_request(user_id="user-001", estimated_tokens=500)
        assert response.status == "queued_rate_limited"
        assert record.circuit_breaker_state == CircuitBreakerState.TRIPPED


# ====================================================================
# 排队位置与预估等待
# ====================================================================

class TestQueuePositionAndEstimate:

    def test_queue_positions_increment(self, handler, tripped_record, request_queue):
        handler.initialize_record(tripped_record)
        r1 = handler.handle_request(user_id="u1", estimated_tokens=500)
        r2 = handler.handle_request(user_id="u2", estimated_tokens=600)
        r3 = handler.handle_request(user_id="u3", estimated_tokens=700)
        assert r1.queue_position == 1
        assert r2.queue_position == 2
        assert r3.queue_position == 3

    def test_wait_time_scales_with_position(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        r1 = handler.handle_request(user_id="u1", estimated_tokens=500)
        r2 = handler.handle_request(user_id="u2", estimated_tokens=600)
        r3 = handler.handle_request(user_id="u3", estimated_tokens=700)
        assert r1.estimated_wait_time < r2.estimated_wait_time < r3.estimated_wait_time

    def test_first_request_wait_time(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        response = handler.handle_request(user_id="u1", estimated_tokens=500)
        assert response.estimated_wait_time == pytest.approx(QueueRateLimiter.ESTIMATED_WAIT_PER_REQUEST * 1)

    def test_third_request_wait_time(self, handler, tripped_record):
        handler.initialize_record(tripped_record)
        handler.handle_request(user_id="u1", estimated_tokens=500)
        handler.handle_request(user_id="u2", estimated_tokens=500)
        r3 = handler.handle_request(user_id="u3", estimated_tokens=500)
        assert r3.estimated_wait_time == pytest.approx(QueueRateLimiter.ESTIMATED_WAIT_PER_REQUEST * 3)


# ====================================================================
# 正常请求不进入排队
# ====================================================================

class TestNormalRequestNotQueued:

    def test_normal_request_accepted(self, handler, normal_record, request_queue):
        handler.initialize_record(normal_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=1000)
        assert response.status == "accepted"
        assert response.status_code == 200

    def test_normal_request_zero_queue_position(self, handler, normal_record):
        handler.initialize_record(normal_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=1000)
        assert response.queue_position == 0

    def test_normal_request_zero_wait_time(self, handler, normal_record):
        handler.initialize_record(normal_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=1000)
        assert response.estimated_wait_time == 0.0

    def test_normal_request_not_in_queue(self, handler, normal_record, request_queue):
        handler.initialize_record(normal_record)
        handler.handle_request(user_id="user-001", estimated_tokens=1000)
        assert request_queue.get_queue_length() == 0

    def test_normal_request_fallback_level_is_cloud(self, handler, normal_record):
        handler.initialize_record(normal_record)
        response = handler.handle_request(user_id="user-001", estimated_tokens=1000)
        assert response.fallback_level == FallbackLevel.CLOUD.name


# ====================================================================
# 端到端完整流程
# ====================================================================

class TestFullE2EFlow:

    def test_normal_to_exhaust_to_tripped_to_queued(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=0, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.CLOSED)
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 19)
        r1 = handler.handle_request(user_id="u1", estimated_tokens=5000)
        assert r1.status == "accepted"
        assert r1.fallback_level == FallbackLevel.CLOUD.name
        r2 = handler.handle_request(user_id="u2", estimated_tokens=4000)
        assert r2.status == "accepted"
        r3 = handler.handle_request(user_id="u3", estimated_tokens=3000)
        assert r3.status == "queued_rate_limited"
        assert r3.fallback_level == FallbackLevel.QUEUE.name
        assert record.circuit_breaker_state == CircuitBreakerState.TRIPPED
        assert record.tripped_at is not None

    def test_full_cycle_include_next_day_recovery(self, budget_manager, circuit_breaker, request_queue, queue_rate_limiter):
        handler = CloudAPIHandler(budget_manager=budget_manager, circuit_breaker=circuit_breaker, queue_rate_limiter=queue_rate_limiter)
        record = CloudAPIBudgetRecord(date_str="2025-07-19", daily_tokens_used=0, daily_hard_limit=10000, circuit_breaker_state=CircuitBreakerState.CLOSED)
        handler.initialize_record(record)
        budget_manager._current_date = date(2025, 7, 19)
        handler.handle_request(user_id="u1", estimated_tokens=10000)
        r1 = handler.handle_request(user_id="u2", estimated_tokens=1)
        assert r1.status == "queued_rate_limited"
        assert record.circuit_breaker_state == CircuitBreakerState.TRIPPED
        budget_manager._current_date = date(2025, 7, 20)
        request_queue.clear()
        r2 = handler.handle_request(user_id="u1", estimated_tokens=3000)
        assert r2.status == "accepted"
        assert r2.fallback_level == FallbackLevel.CLOUD.name
        assert record.circuit_breaker_state == CircuitBreakerState.CLOSED
        assert record.date_str == "2025-07-20"
        assert record.daily_tokens_used == 3000
        r3 = handler.handle_request(user_id="u2", estimated_tokens=2000)
        assert r3.status == "accepted"
        assert record.daily_tokens_used == 5000
        r4 = handler.handle_request(user_id="u3", estimated_tokens=6000)
        assert r4.status == "queued_rate_limited"
        assert record.circuit_breaker_state == CircuitBreakerState.TRIPPED
        budget_manager._current_date = date(2025, 7, 21)
        request_queue.clear()
        r5 = handler.handle_request(user_id="u1", estimated_tokens=100)
        assert r5.status == "accepted"
        assert record.circuit_breaker_state == CircuitBreakerState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])