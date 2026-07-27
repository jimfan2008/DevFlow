import uuid
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import pytest
from pydantic import BaseModel


# ====================================================================
# 被测试的领域模型
# ====================================================================

def _default_current_time() -> datetime:
    return datetime.now(timezone.utc)


class RequestStatus(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


class QueueErrorCode(str, Enum):
    QUEUE_TIMEOUT = "queue_timeout"
    QUEUE_FULL = "queue_full"
    REQUEST_NOT_FOUND = "request_not_found"


@dataclass
class QueuedRequest:
    """排队中的请求"""
    request_id: str
    user_id: str
    payload: Dict[str, Any]
    enqueued_at: datetime
    timeout_seconds: float = 60.0
    priority: int = 0
    status: str = RequestStatus.WAITING.value
    processed_at: Optional[datetime] = None
    error: Optional[str] = None
    waited_seconds: float = 0.0
    _current_time_fn: Callable[[], datetime] = field(
        default=_default_current_time, repr=False
    )

    def elapsed_seconds(self, now: datetime = None) -> float:
        """计算从入队到现在经过的秒数"""
        t = now or self._current_time_fn()
        return (t - self.enqueued_at).total_seconds()

    def is_timed_out(self, now: datetime = None) -> bool:
        """判断是否已超时"""
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def remaining_seconds(self, now: datetime = None) -> float:
        """剩余等待时间"""
        return max(0.0, self.timeout_seconds - self.elapsed_seconds(now))

    def mark_timed_out(self, now: datetime = None):
        """标记为超时"""
        self.status = RequestStatus.TIMED_OUT.value
        self.error = QueueErrorCode.QUEUE_TIMEOUT.value
        self.waited_seconds = self.elapsed_seconds(now)
        self.processed_at = now or self._current_time_fn()


@dataclass
class TimeoutResponse:
    """超时响应"""
    status_code: int
    error: str
    waited_seconds: float
    request_id: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "error": self.error,
            "waited_seconds": round(self.waited_seconds, 2),
            "request_id": self.request_id,
            "message": self.message,
        }


class QueueTimeoutError(Exception):
    """排队超时异常"""

    def __init__(self, request_id: str, waited_seconds: float, message: str = None):
        self.request_id = request_id
        self.waited_seconds = waited_seconds
        self.message = message or f"请求 {request_id} 排队超时，已等待 {waited_seconds:.1f} 秒"
        super().__init__(self.message)


class RequestQueue:
    """请求排队队列"""

    def __init__(self, max_queue_size: int = 100, default_timeout: float = 60.0):
        self._queue: List[QueuedRequest] = []
        self._max_queue_size = max_queue_size
        self._default_timeout = default_timeout
        self._removed_requests: List[QueuedRequest] = []

    def enqueue(
        self,
        request_id: str,
        user_id: str,
        payload: Dict[str, Any],
        enqueued_at: datetime,
        timeout_seconds: float = None,
        priority: int = 0,
    ) -> QueuedRequest:
        """将请求加入队列"""
        if len(self._queue) >= self._max_queue_size:
            raise QueueFullError(
                f"队列已满，当前大小 {len(self._queue)}，最大 {self._max_queue_size}"
            )
        request = QueuedRequest(
            request_id=request_id,
            user_id=user_id,
            payload=payload,
            enqueued_at=enqueued_at,
            timeout_seconds=timeout_seconds or self._default_timeout,
            priority=priority,
        )
        self._queue.append(request)
        return request

    def dequeue(self, now: datetime = None) -> Optional[QueuedRequest]:
        """从队列头部取出一个请求（按优先级+时间排序）"""
        if not self._queue:
            return None
        self._queue.sort(key=lambda r: (r.priority, r.enqueued_at))
        return self._queue.pop(0)

    def get_request(self, request_id: str) -> Optional[QueuedRequest]:
        """根据 request_id 查找请求"""
        for req in self._queue:
            if req.request_id == request_id:
                return req
        return None

    def remove_request(self, request_id: str) -> Optional[QueuedRequest]:
        """从队列中移除请求"""
        for i, req in enumerate(self._queue):
            if req.request_id == request_id:
                removed = self._queue.pop(i)
                self._removed_requests.append(removed)
                return removed
        return None

    def get_timed_out_requests(self, now: datetime) -> List[QueuedRequest]:
        """获取所有已超时的请求"""
        return [req for req in self._queue if req.is_timed_out(now)]

    def cleanup_timed_out(self, now: datetime) -> List[QueuedRequest]:
        """清理超时请求：标记为超时并从队列中移除"""
        timed_out = self.get_timed_out_requests(now)
        for req in timed_out:
            req.mark_timed_out(now)
            self._removed_requests.append(req)
            self._queue.remove(req)
        return timed_out

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def is_full(self) -> bool:
        return len(self._queue) >= self._max_queue_size

    def clear(self):
        self._queue.clear()


class QueueFullError(Exception):
    """队列已满异常"""
    pass


class LlmApiQueueService:
    """LLM API 排队服务：处理请求排队、超时检查、响应生成"""

    DEFAULT_TIMEOUT_SECONDS = 60.0
    HTTP_STATUS_SERVICE_UNAVAILABLE = 503

    def __init__(
        self,
        queue: RequestQueue = None,
        default_timeout: float = None,
        current_time_fn: Callable[[], datetime] = None,
    ):
        self.queue = queue or RequestQueue(
            default_timeout=default_timeout or self.DEFAULT_TIMEOUT_SECONDS
        )
        self._default_timeout = default_timeout or self.DEFAULT_TIMEOUT_SECONDS
        self._current_time_fn = current_time_fn or _default_current_time

    def submit_request(
        self,
        user_id: str,
        payload: Dict[str, Any],
        timeout_seconds: float = None,
        priority: int = 0,
    ) -> QueuedRequest:
        """提交请求到排队队列"""
        request_id = str(uuid.uuid4())
        now = self._current_time_fn()
        return self.queue.enqueue(
            request_id=request_id,
            user_id=user_id,
            payload=payload,
            enqueued_at=now,
            timeout_seconds=timeout_seconds,
            priority=priority,
        )

    def check_timeout(self, request_id: str) -> Optional[TimeoutResponse]:
        """
        检查指定请求是否超时。

        如果已超时：
        - 标记为 timed_out
        - 从队列中移除
        - 返回 503 超时响应

        如果未超时：返回 None
        """
        now = self._current_time_fn()
        request = self.queue.get_request(request_id)
        if request is None:
            return TimeoutResponse(
                status_code=404,
                error=QueueErrorCode.REQUEST_NOT_FOUND.value,
                waited_seconds=0.0,
                request_id=request_id,
                message=f"请求 {request_id} 不在排队队列中",
            )

        if not request.is_timed_out(now):
            return None

        request.mark_timed_out(now)
        self.queue.remove_request(request_id)

        return TimeoutResponse(
            status_code=self.HTTP_STATUS_SERVICE_UNAVAILABLE,
            error=QueueErrorCode.QUEUE_TIMEOUT.value,
            waited_seconds=request.waited_seconds,
            request_id=request.request_id,
            message=f"请求排队超时（等待 {request.waited_seconds:.1f} 秒，超时阈值 {request.timeout_seconds:.0f} 秒）",
        )

    def cleanup_all_timeouts(self) -> List[TimeoutResponse]:
        """批量清理所有超时请求，返回超时响应列表"""
        now = self._current_time_fn()
        timed_out_requests = self.queue.cleanup_timed_out(now)
        return [
            TimeoutResponse(
                status_code=self.HTTP_STATUS_SERVICE_UNAVAILABLE,
                error=QueueErrorCode.QUEUE_TIMEOUT.value,
                waited_seconds=req.waited_seconds,
                request_id=req.request_id,
                message=f"请求排队超时（等待 {req.waited_seconds:.1f} 秒）",
            )
            for req in timed_out_requests
        ]

    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取请求当前状态"""
        now = self._current_time_fn()
        request = self.queue.get_request(request_id)
        if request is None:
            for req in self.queue._removed_requests:
                if req.request_id == request_id:
                    return {
                        "request_id": request_id,
                        "status": req.status,
                        "error": req.error,
                        "waited_seconds": req.waited_seconds,
                    }
            return None
        return {
            "request_id": request.request_id,
            "status": request.status,
            "waited_seconds": request.elapsed_seconds(now),
            "remaining_seconds": request.remaining_seconds(now),
            "priority": request.priority,
        }


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def base_time():
    """固定的基准时间"""
    return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_clock(base_time):
    """可控制的可调用对象，返回 base_time"""
    class FakeClock:
        def __init__(self):
            self._time = base_time

        def __call__(self):
            return self._time

        def advance(self, seconds: float):
            self._time += timedelta(seconds=seconds)

        @property
        def current(self):
            return self._time
    return FakeClock()


@pytest.fixture
def queue(base_time):
    return RequestQueue(max_queue_size=100, default_timeout=60.0)


@pytest.fixture
def service(fake_clock):
    q = RequestQueue(max_queue_size=100, default_timeout=60.0)
    return LlmApiQueueService(queue=q, default_timeout=60.0, current_time_fn=fake_clock)


@pytest.fixture
def mock_payload():
    return {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100,
    }


# ====================================================================
# 测试用例：LLM API 排队超时 60 秒返回 503
# ====================================================================

class TestQueueTimeoutReturns503:
    """排队超时 60 秒后返回 503 错误"""

    def test_return_http_503_on_timeout(self, service, fake_clock):
        """排队超时返回 HTTP 503 Service Unavailable"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 503

    def test_response_error_is_queue_timeout(self, service, fake_clock):
        """响应 Body 包含 error=queue_timeout"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.error == "queue_timeout"

    def test_waited_seconds_gte_60(self, service, fake_clock):
        """响应 Body 包含 waited_seconds >= 60"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(65)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.waited_seconds >= 60

    def test_request_removed_from_queue_on_timeout(self, service, fake_clock):
        """超时后请求从排队队列中移除"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        assert service.queue.size == 1

        fake_clock.advance(61)
        service.check_timeout(req.request_id)

        assert service.queue.size == 0
        assert service.queue.get_request(req.request_id) is None

    def test_request_status_is_timed_out(self, service, fake_clock):
        """超时后请求 status=timed_out"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)
        service.check_timeout(req.request_id)

        status = service.get_request_status(req.request_id)
        assert status is not None
        assert status["status"] == "timed_out"

    # ── 60 秒边界条件 ──

    def test_exactly_60_seconds_is_timed_out(self, service, fake_clock):
        """恰好在 60 秒时也视为超时"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(60)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 503
        assert response.error == "queue_timeout"

    def test_59_seconds_not_timed_out(self, service, fake_clock):
        """59 秒时不应超时"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(59)

        response = service.check_timeout(req.request_id)

        assert response is None

    def test_59_9_seconds_not_timed_out(self, service, fake_clock):
        """59.9 秒时不应超时"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(59.9)

        response = service.check_timeout(req.request_id)

        assert response is None

    def test_60_1_seconds_is_timed_out(self, service, fake_clock):
        """60.1 秒时应超时"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(60.1)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 503

    # ── 响应体完整性 ──

    def test_response_contains_request_id(self, service, fake_clock):
        """响应 Body 包含 request_id"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.request_id == req.request_id
        assert len(response.request_id) > 0

    def test_response_contains_message(self, service, fake_clock):
        """响应 Body 包含描述性消息"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.message is not None
        assert len(response.message) > 0

    def test_response_to_dict_format(self, service, fake_clock):
        """response.to_dict() 格式正确"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)

        response = service.check_timeout(req.request_id)
        body = response.to_dict()

        assert body["status_code"] == 503
        assert body["error"] == "queue_timeout"
        assert body["waited_seconds"] >= 60
        assert "request_id" in body
        assert "message" in body

    # ── 自定义超时时间 ──

    def test_custom_timeout_30_seconds(self, base_time):
        """自定义超时 30 秒，31 秒后超时"""
        clock = type("FakeClock", (), {"_time": base_time})()
        def clock_fn():
            return clock._time

        q = RequestQueue(default_timeout=30.0)
        svc = LlmApiQueueService(queue=q, default_timeout=30.0, current_time_fn=clock_fn)

        req = svc.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
            timeout_seconds=30.0,
        )
        clock._time = base_time + timedelta(seconds=31)

        response = svc.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 503
        assert response.error == "queue_timeout"
        assert response.waited_seconds >= 30

    def test_custom_timeout_120_seconds_not_timeout_at_90(self, base_time):
        """自定义超时 120 秒，90 秒时不应超时"""
        clock = type("FakeClock", (), {"_time": base_time})()
        def clock_fn():
            return clock._time

        q = RequestQueue(default_timeout=120.0)
        svc = LlmApiQueueService(queue=q, default_timeout=120.0, current_time_fn=clock_fn)

        req = svc.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
            timeout_seconds=120.0,
        )
        clock._time = base_time + timedelta(seconds=90)

        response = svc.check_timeout(req.request_id)

        assert response is None

    # ── 多个请求的超时处理 ──

    def test_multiple_requests_timeout_independently(self, service, fake_clock):
        """多个请求独立超时互不影响"""
        req1 = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(0.1)
        req2 = service.submit_request(
            user_id="user-002",
            payload={"model": "gpt-3.5"},
        )
        fake_clock.advance(0.1)
        req3 = service.submit_request(
            user_id="user-003",
            payload={"model": "claude-3"},
        )
        assert service.queue.size == 3

        # 让所有请求都超过 60 秒
        fake_clock.advance(60)

        response = service.check_timeout(req2.request_id)

        assert response is not None
        assert response.status_code == 503
        assert service.queue.size == 2
        assert service.queue.get_request(req1.request_id) is not None
        assert service.queue.get_request(req3.request_id) is not None

    def test_cleanup_all_timeouts_removes_multiple(self, service, fake_clock):
        """批量清理超时请求"""
        req1 = service.submit_request(user_id="u1", payload={})
        fake_clock.advance(0.1)
        req2 = service.submit_request(user_id="u2", payload={})
        fake_clock.advance(0.1)
        req3 = service.submit_request(user_id="u3", payload={})

        fake_clock.advance(70)

        responses = service.cleanup_all_timeouts()

        assert len(responses) == 3
        assert service.queue.size == 0
        for resp in responses:
            assert resp.status_code == 503
            assert resp.error == "queue_timeout"
            assert resp.waited_seconds >= 60

    # ── 查询不存在或已处理的请求 ──

    def test_check_nonexistent_request_returns_404(self, service):
        """检查不存在的请求返回 404"""
        response = service.check_timeout("nonexistent-id")

        assert response is not None
        assert response.status_code == 404
        assert response.error == "request_not_found"

    def test_check_already_removed_request(self, service, fake_clock):
        """检查已移除的请求"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)
        service.check_timeout(req.request_id)

        response = service.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 404

    # ── 请求状态查询 ──

    def test_get_status_of_waiting_request(self, service, fake_clock):
        """获取等待中请求的状态"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(30)

        status = service.get_request_status(req.request_id)

        assert status is not None
        assert status["status"] == "waiting"
        assert status["remaining_seconds"] == pytest.approx(30.0, abs=0.1)

    def test_get_status_of_timed_out_request(self, service, fake_clock):
        """获取已超时请求的状态"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(61)
        service.check_timeout(req.request_id)

        status = service.get_request_status(req.request_id)

        assert status is not None
        assert status["status"] == "timed_out"
        assert status["error"] == "queue_timeout"

    # ── waited_seconds 精确值验证 ──

    def test_waited_seconds_is_exact_70_after_70_seconds(self, service, fake_clock):
        """70 秒后 waited_seconds 等于 70"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(70)

        response = service.check_timeout(req.request_id)

        assert response.waited_seconds == pytest.approx(70.0)

    def test_waited_seconds_is_exact_100_after_100_seconds(self, service, fake_clock):
        """100 秒后 waited_seconds 等于 100"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        fake_clock.advance(100)

        response = service.check_timeout(req.request_id)

        assert response.waited_seconds == pytest.approx(100.0)


class TestQueuedRequestTimeout:
    """QueuedRequest 超时相关属性测试"""

    def test_is_timed_out_at_exactly_60_seconds(self, base_time):
        """60 秒时 is_timed_out 为 True"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            payload={},
            enqueued_at=base_time,
            timeout_seconds=60.0,
        )
        now = base_time + timedelta(seconds=60)
        assert req.is_timed_out(now) is True

    def test_is_not_timed_out_before_60_seconds(self, base_time):
        """60 秒前 is_timed_out 为 False"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            payload={},
            enqueued_at=base_time,
            timeout_seconds=60.0,
        )
        now = base_time + timedelta(seconds=59)
        assert req.is_timed_out(now) is False

    def test_remaining_seconds_at_30_seconds(self, base_time):
        """等待 30 秒后剩余时间约 30 秒"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            payload={},
            enqueued_at=base_time,
            timeout_seconds=60.0,
        )
        now = base_time + timedelta(seconds=30)
        assert req.remaining_seconds(now) == pytest.approx(30.0)

    def test_mark_timed_out_sets_fields(self, base_time):
        """mark_timed_out 正确设置字段"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            payload={},
            enqueued_at=base_time,
            timeout_seconds=60.0,
        )
        now = base_time + timedelta(seconds=61)
        req.mark_timed_out(now)

        assert req.status == "timed_out"
        assert req.error == "queue_timeout"
        assert req.waited_seconds == pytest.approx(61.0)
        assert req.processed_at == now

    def test_elapsed_seconds_zero_at_start(self, base_time):
        """入队瞬间 elapsed_seconds 为 0"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            payload={},
            enqueued_at=base_time,
            timeout_seconds=60.0,
        )
        assert req.elapsed_seconds(base_time) == 0.0

    def test_elapsed_seconds_30_after_30_seconds(self, base_time):
        """30 秒后 elapsed_seconds 为 30"""
        req = QueuedRequest(
            request_id="req-001",
            user_id="user-001",
            payload={},
            enqueued_at=base_time,
            timeout_seconds=60.0,
        )
        now = base_time + timedelta(seconds=30)
        assert req.elapsed_seconds(now) == 30.0


class TestRequestQueueTimeout:
    """RequestQueue 超时清理测试"""

    def test_cleanup_timed_out_marks_and_removes(self, base_time):
        """cleanup_timed_out 标记并移除超时请求"""
        q = RequestQueue(default_timeout=60.0)
        q.enqueue("r1", "u1", {}, base_time)
        q.enqueue("r2", "u2", {}, base_time + timedelta(seconds=1))

        now = base_time + timedelta(seconds=61)
        cleaned = q.cleanup_timed_out(now)

        assert len(cleaned) == 2
        for removed in cleaned:
            assert removed.status == "timed_out"
            assert removed.error == "queue_timeout"
        assert q.size == 0

    def test_cleanup_only_removes_timed_out_requests(self, base_time):
        """cleanup 只移除超时请求，不移除未超时请求"""
        q = RequestQueue(default_timeout=60.0)
        q.enqueue("old", "u1", {}, base_time)
        q.enqueue("new", "u2", {}, base_time + timedelta(seconds=50))

        now = base_time + timedelta(seconds=61)
        cleaned = q.cleanup_timed_out(now)

        assert q.size == 1
        assert q.get_request("new") is not None
        assert len(cleaned) == 1
        assert cleaned[0].request_id == "old"

    def test_get_timed_out_requests(self, base_time):
        """get_timed_out_requests 返回超时请求列表"""
        q = RequestQueue(default_timeout=60.0)
        r1 = q.enqueue("r1", "u1", {}, base_time)
        q.enqueue("r2", "u2", {}, base_time + timedelta(seconds=30))

        now = base_time + timedelta(seconds=61)
        timed_out = q.get_timed_out_requests(now)

        assert len(timed_out) == 1
        assert r1 in timed_out

    def test_remove_request_success(self, base_time):
        """成功移除指定请求"""
        q = RequestQueue(default_timeout=60.0)
        q.enqueue("r1", "u1", {}, base_time)
        assert q.size == 1

        removed = q.remove_request("r1")

        assert removed is not None
        assert removed.request_id == "r1"
        assert q.size == 0

    def test_remove_nonexistent_request(self, base_time):
        """移除不存在的请求返回 None"""
        q = RequestQueue(default_timeout=60.0)
        removed = q.remove_request("nonexistent")
        assert removed is None


class TestTimeoutResponse:
    """TimeoutResponse 响应体测试"""

    def test_to_dict_has_all_fields(self):
        """to_dict 包含所有必要字段"""
        resp = TimeoutResponse(
            status_code=503,
            error="queue_timeout",
            waited_seconds=61.5,
            request_id="req-001",
            message="排队超时",
        )
        body = resp.to_dict()

        assert body["status_code"] == 503
        assert body["error"] == "queue_timeout"
        assert body["waited_seconds"] == pytest.approx(61.5)
        assert body["request_id"] == "req-001"
        assert body["message"] == "排队超时"

    def test_to_dict_waited_seconds_rounded(self):
        """to_dict 中 waited_seconds 保留两位小数"""
        resp = TimeoutResponse(
            status_code=503,
            error="queue_timeout",
            waited_seconds=61.12345,
            request_id="req-001",
            message="排队超时",
        )
        body = resp.to_dict()
        assert body["waited_seconds"] == 61.12

    def test_response_is_dataclass(self):
        """TimeoutResponse 是 dataclass"""
        resp = TimeoutResponse(
            status_code=503,
            error="queue_timeout",
            waited_seconds=61.0,
            request_id="req-001",
            message="排队超时",
        )
        assert resp.status_code == 503
        assert resp.error == "queue_timeout"
        assert resp.waited_seconds == 61.0
        assert resp.request_id == "req-001"
        assert resp.message == "排队超时"


class TestQueueTimeoutError:
    """QueueTimeoutError 异常测试"""

    def test_exception_contains_request_id(self):
        """异常包含 request_id"""
        err = QueueTimeoutError(request_id="req-001", waited_seconds=61.0)
        assert err.request_id == "req-001"
        assert err.waited_seconds == 61.0
        assert "req-001" in str(err)

    def test_exception_message_includes_waited_seconds(self):
        """异常消息包含等待时间"""
        err = QueueTimeoutError(request_id="req-001", waited_seconds=61.0)
        assert "61.0" in err.message

    def test_exception_can_be_raised_and_caught(self):
        """异常可正常抛掷和捕获"""
        with pytest.raises(QueueTimeoutError) as exc_info:
            raise QueueTimeoutError(request_id="req-001", waited_seconds=61.0)
        assert exc_info.value.request_id == "req-001"
        assert exc_info.value.waited_seconds == 61.0


class TestQueueFullError:
    """队列满异常测试"""

    def test_enqueue_to_full_queue_raises(self, base_time):
        """满队列入队抛出异常"""
        q = RequestQueue(max_queue_size=1, default_timeout=60.0)
        q.enqueue("r1", "u1", {}, base_time)

        with pytest.raises(QueueFullError, match="队列已满"):
            q.enqueue("r2", "u2", {}, base_time + timedelta(seconds=1))

    def test_is_full_after_capacity(self, base_time):
        """满队列 is_full 为 True"""
        q = RequestQueue(max_queue_size=1, default_timeout=60.0)
        assert q.is_full is False
        q.enqueue("r1", "u1", {}, base_time)
        assert q.is_full is True


class TestServiceIntegration:
    """完整流程集成测试"""

    def test_full_flow_submit_wait_timeout_remove(self, service, fake_clock):
        """完整流程：提交 -> 等待 -> 超时 -> 移除"""
        req = service.submit_request(
            user_id="user-001",
            payload={"model": "gpt-4"},
        )
        assert service.queue.size == 1
        assert service.get_request_status(req.request_id)["status"] == "waiting"

        fake_clock.advance(50)
        assert service.check_timeout(req.request_id) is None
        assert service.queue.size == 1

        fake_clock.advance(15)
        response = service.check_timeout(req.request_id)
        assert response is not None
        assert response.status_code == 503
        assert response.error == "queue_timeout"
        assert response.waited_seconds >= 60
        assert service.queue.size == 0
        assert service.get_request_status(req.request_id)["status"] == "timed_out"

    def test_multiple_users_sequential_timeout(self, service, fake_clock):
        """多个用户依次超时"""
        req1 = service.submit_request(user_id="u1", payload={"model": "gpt-4"})
        fake_clock.advance(0.5)
        req2 = service.submit_request(user_id="u2", payload={"model": "gpt-3.5"})
        fake_clock.advance(0.5)
        req3 = service.submit_request(user_id="u3", payload={"model": "claude"})

        assert service.queue.size == 3

        fake_clock.advance(59)
        resp1 = service.check_timeout(req1.request_id)
        assert resp1.status_code == 503

        resp2 = service.check_timeout(req2.request_id)
        assert resp2.status_code == 503

        assert service.check_timeout(req3.request_id) is None
        assert service.queue.size == 1

        fake_clock.advance(0.5)
        resp3 = service.check_timeout(req3.request_id)
        assert resp3.status_code == 503
        assert service.queue.size == 0

    def test_priority_does_not_affect_timeout(self, service, fake_clock):
        """优先级不影响超时时间"""
        low = service.submit_request(
            user_id="u1",
            payload={},
            priority=10,
        )
        high = service.submit_request(
            user_id="u2",
            payload={},
            priority=1,
        )

        fake_clock.advance(61)

        low_resp = service.check_timeout(low.request_id)
        high_resp = service.check_timeout(high.request_id)

        assert low_resp.status_code == 503
        assert high_resp.status_code == 503
        assert service.queue.size == 0
