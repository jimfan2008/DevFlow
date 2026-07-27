import uuid
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import pytest


def _default_current_time() -> datetime:
    return datetime.now(timezone.utc)


# ====================================================================
# 被测试的领域模型
# ===================================================================


class InferenceStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMED_OUT = "timeout"
    FAILED = "failed"


class InferenceErrorCode(str, Enum):
    REQUEST_TIMEOUT = "request_timeout"
    INFERENCE_ERROR = "inference_error"
    RETRIES_EXHAUSTED = "retries_exhausted"


@dataclass
class InferenceRequest:
    request_id: str
    user_id: str
    model: str
    prompt: str
    started_at: datetime
    status: str = InferenceStatus.IN_PROGRESS.value
    timeout_seconds: float = 120.0
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    _current_time_fn: Callable[[], datetime] = field(
        default_factory=lambda: _default_current_time, repr=False
    )

    def elapsed_seconds(self, now: datetime = None) -> float:
        t = now or self._current_time_fn()
        return (t - self.started_at).total_seconds()

    def is_timed_out(self, now: datetime = None) -> bool:
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def mark_timed_out(self, now: datetime = None):
        t = now or self._current_time_fn()
        self.status = InferenceStatus.TIMED_OUT.value
        self.error = InferenceErrorCode.REQUEST_TIMEOUT.value
        self.completed_at = t

    def mark_completed(self, now: datetime = None):
        t = now or self._current_time_fn()
        self.status = InferenceStatus.COMPLETED.value
        self.completed_at = t


@dataclass
class InferenceResponse:
    status_code: int
    request_id: str
    error: Optional[str] = None
    status: Optional[str] = None
    duration_seconds: Optional[float] = None
    timeout_seconds: Optional[float] = None
    retries_attempts: int = 0
    retries_max: int = 0
    retries_exhausted: bool = False
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "request_id": self.request_id,
            "error": self.error,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 2) if self.duration_seconds is not None else None,
            "timeout_seconds": self.timeout_seconds,
            "retries_attempts": self.retries_attempts,
            "retries_max": self.retries_max,
            "retries_exhausted": self.retries_exhausted,
            "message": self.message,
        }


class InferenceTimeoutError(Exception):
    def __init__(self, request_id: str, duration_seconds: float, timeout_seconds: float = 120.0):
        self.request_id = request_id
        self.duration_seconds = duration_seconds
        self.timeout_seconds = timeout_seconds
        self.message = f"推理请求 {request_id} 超时（持续 {duration_seconds:.1f} 秒，超时阈值 {timeout_seconds:.0f} 秒）"
        super().__init__(self.message)


class LLMInferenceClient:
    """LLM推理客户端：管理请求、超时检查、重试"""

    HTTP_STATUS_GATEWAY_TIMEOUT = 504
    DEFAULT_TIMEOUT_SECONDS = 120.0
    DEFAULT_MAX_RETRIES = 1

    def __init__(
        self,
        timeout_seconds: float = None,
        max_retries: int = None,
        current_time_fn: Callable[[], datetime] = None,
        llm_always_timeout: bool = False,
    ):
        self._timeout_seconds = timeout_seconds if timeout_seconds is not None else self.DEFAULT_TIMEOUT_SECONDS
        self._max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self._current_time_fn = current_time_fn or _default_current_time
        self._requests: Dict[str, InferenceRequest] = {}
        self._completed_requests: List[InferenceRequest] = []
        self._llm_always_timeout = llm_always_timeout

    def create_request(self, user_id: str, model: str, prompt: str) -> InferenceRequest:
        now = self._current_time_fn()
        request_id = str(uuid.uuid4())
        req = InferenceRequest(
            request_id=request_id,
            user_id=user_id,
            model=model,
            prompt=prompt,
            started_at=now,
            timeout_seconds=self._timeout_seconds,
            _current_time_fn=self._current_time_fn,
        )
        self._requests[request_id] = req
        return req

    def check_timeout(self, request_id: str) -> Optional[InferenceResponse]:
        now = self._current_time_fn()
        req = self._requests.get(request_id)
        if req is None:
            return InferenceResponse(
                status_code=404,
                request_id=request_id,
                message=f"请求 {request_id} 不存在",
            )
        if req.status != InferenceStatus.IN_PROGRESS.value:
            return None
        if req.is_timed_out(now):
            duration = req.elapsed_seconds(now)
            req.mark_timed_out(now)
            self._completed_requests.append(req)
            del self._requests[request_id]
            return InferenceResponse(
                status_code=self.HTTP_STATUS_GATEWAY_TIMEOUT,
                request_id=request_id,
                error=InferenceErrorCode.REQUEST_TIMEOUT.value,
                status=InferenceStatus.TIMED_OUT.value,
                duration_seconds=duration,
                timeout_seconds=req.timeout_seconds,
                message=f"推理请求超时（持续 {duration:.1f} 秒，超时阈值 {req.timeout_seconds:.0f} 秒）",
            )
        return None

    def send_with_retry(
        self,
        user_id: str,
        model: str,
        prompt: str,
        max_retries: int = None,
    ) -> InferenceResponse:
        retries = max_retries if max_retries is not None else self._max_retries
        last_response: Optional[InferenceResponse] = None
        total_attempts = retries + 1

        for attempt in range(total_attempts):
            if self._llm_always_timeout:
                req = self.create_request(user_id, model, prompt)
                req.mark_timed_out(req.started_at + timedelta(seconds=self._timeout_seconds))
                self._completed_requests.append(req)
                self._requests.pop(req.request_id, None)
                last_response = InferenceResponse(
                    status_code=self.HTTP_STATUS_GATEWAY_TIMEOUT,
                    request_id=req.request_id,
                    error=InferenceErrorCode.REQUEST_TIMEOUT.value,
                    status=InferenceStatus.TIMED_OUT.value,
                    duration_seconds=self._timeout_seconds,
                    timeout_seconds=self._timeout_seconds,
                    message=f"推理请求超时（持续 {self._timeout_seconds:.0f} 秒，超时阈值 {self._timeout_seconds:.0f} 秒）",
                )
                if attempt < retries:
                    continue
            else:
                req = self.create_request(user_id, model, prompt)
                now = self._current_time_fn()
                req.mark_completed(now)
                duration = req.elapsed_seconds(now)
                self._completed_requests.append(req)
                self._requests.pop(req.request_id, None)
                return InferenceResponse(
                    status_code=200,
                    request_id=req.request_id,
                    status=InferenceStatus.COMPLETED.value,
                    duration_seconds=duration,
                    timeout_seconds=self._timeout_seconds,
                    retries_attempts=attempt,
                    retries_max=retries,
                    retries_exhausted=False,
                    message="推理请求完成",
                )

        if last_response is not None:
            last_response.retries_attempts = total_attempts
            last_response.retries_max = retries
            last_response.retries_exhausted = True
            last_response.error = InferenceErrorCode.RETRIES_EXHAUSTED.value
            last_response.message = (
                f"客户端重试{retries}次后仍超时，最终返回超时错误"
                f"（持续 {last_response.duration_seconds:.0f} 秒，超时阈值 {last_response.timeout_seconds:.0f} 秒）"
            )
        return last_response

    @property
    def active_requests(self) -> int:
        return len(self._requests)

    @property
    def completed_requests(self) -> List[InferenceRequest]:
        return list(self._completed_requests)


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def base_time():
    return datetime(2025, 7, 20, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_clock(base_time):
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
def client(fake_clock):
    return LLMInferenceClient(
        timeout_seconds=120.0,
        max_retries=1,
        current_time_fn=fake_clock,
        llm_always_timeout=False,
    )


@pytest.fixture
def client_always_timeout(fake_clock):
    return LLMInferenceClient(
        timeout_seconds=120.0,
        max_retries=1,
        current_time_fn=fake_clock,
        llm_always_timeout=True,
    )


@pytest.fixture
def client_short_timeout(fake_clock):
    return LLMInferenceClient(
        timeout_seconds=10.0,
        max_retries=1,
        current_time_fn=fake_clock,
        llm_always_timeout=False,
    )


@pytest.fixture
def client_no_retry(fake_clock):
    return LLMInferenceClient(
        timeout_seconds=120.0,
        max_retries=0,
        current_time_fn=fake_clock,
        llm_always_timeout=False,
    )


@pytest.fixture
def active_request(client, fake_clock):
    return client.create_request(
        user_id="user-001",
        model="gpt-4",
        prompt="Explain quantum computing",
    )


# ====================================================================
# 验收标准 1：单次推理 >120 秒时正确终止并返回超时错误
# ====================================================================


class TestSingleTimeoutAt120Seconds:
    """系统在120秒时终止请求，返回HTTP504 Gateway Timeout"""

    def test_request_terminated_at_120_seconds(self, client, active_request, fake_clock):
        """系统在120秒时终止请求"""
        assert active_request.status == "in_progress"

        fake_clock.advance(120)

        response = client.check_timeout(active_request.request_id)

        assert response is not None
        assert active_request.status == "timeout"
        assert client.active_requests == 0

    def test_return_http_504_gateway_timeout(self, client, active_request, fake_clock):
        """返回HTTP 504"""
        fake_clock.advance(120)

        response = client.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504

    def test_response_body_error_is_request_timeout(self, client, active_request, fake_clock):
        """响应Body包含 error=request_timeout"""
        fake_clock.advance(120)

        response = client.check_timeout(active_request.request_id)

        assert response is not None
        assert response.error == "request_timeout"

    def test_response_body_timeout_seconds_is_120(self, client, active_request, fake_clock):
        """响应Body包含 timeout_seconds=120"""
        fake_clock.advance(120)

        response = client.check_timeout(active_request.request_id)

        assert response is not None
        assert response.timeout_seconds == 120.0

    def test_response_to_dict_has_error_and_timeout_seconds(self, client, active_request, fake_clock):
        """to_dict 包含 error=request_timeout 和 timeout_seconds=120"""
        fake_clock.advance(120)

        response = client.check_timeout(active_request.request_id)
        body = response.to_dict()

        assert body["error"] == "request_timeout"
        assert body["timeout_seconds"] == 120.0
        assert body["status_code"] == 504

    def test_response_to_dict_all_required_fields(self, client, active_request, fake_clock):
        """to_dict 包含所有必需字段"""
        fake_clock.advance(120)

        response = client.check_timeout(active_request.request_id)
        body = response.to_dict()

        assert body["status_code"] == 504
        assert body["error"] == "request_timeout"
        assert body["timeout_seconds"] == 120.0
        assert body["status"] == "timeout"
        assert "request_id" in body
        assert "message" in body
        assert "duration_seconds" in body


# ── 边界：120 秒前后 ──


class TestTimeout120Boundary:
    """超时边界值：120 秒前后"""

    def test_119_seconds_not_timed_out(self, client, active_request, fake_clock):
        fake_clock.advance(119)

        response = client.check_timeout(active_request.request_id)

        assert response is None
        assert client.active_requests == 1

    def test_119_9_seconds_not_timed_out(self, client, active_request, fake_clock):
        fake_clock.advance(119.9)

        response = client.check_timeout(active_request.request_id)

        assert response is None
        assert active_request.status == "in_progress"

    def test_exactly_120_seconds_timed_out(self, client, active_request, fake_clock):
        fake_clock.advance(120)

        response = client.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.error == "request_timeout"
        assert response.timeout_seconds == 120.0

    def test_120_1_seconds_timed_out(self, client, active_request, fake_clock):
        fake_clock.advance(120.1)

        response = client.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.duration_seconds == pytest.approx(120.1)

    def test_200_seconds_timed_out(self, client, active_request, fake_clock):
        fake_clock.advance(200)

        response = client.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.duration_seconds == pytest.approx(200.0)


# ── 正常完成 ──


class TestNormalCompletionBeforeTimeout:
    """推理在超时前正常完成"""

    def test_complete_at_60_seconds(self, client, active_request, fake_clock):
        fake_clock.advance(60)

        req = active_request
        now = fake_clock.current
        req.mark_completed(now)
        client._completed_requests.append(req)
        del client._requests[req.request_id]

        assert client.active_requests == 0
        assert req.status == "completed"

    def test_complete_at_119_seconds(self, client, active_request, fake_clock):
        fake_clock.advance(119)

        req = active_request
        now = fake_clock.current
        req.mark_completed(now)
        client._completed_requests.append(req)
        del client._requests[req.request_id]

        assert client.active_requests == 0
        assert req.status == "completed"


# ====================================================================
# 验收标准 2：客户端重试1次后仍超时，最终返回 HTTP504 + retries_exhausted=true
# ====================================================================


class TestClientRetryExhausted:
    """客户端重试1次后仍超时，最终返回HTTP504，retries_exhausted=true"""

    def test_retry_1_time_still_timeout(self, client_always_timeout, fake_clock):
        """重试1次后仍超时"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.retries_exhausted is True
        assert response.status_code == 504

    def test_retry_final_status_code_is_504(self, client_always_timeout, fake_clock):
        """最终返回 HTTP 504"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.status_code == 504

    def test_retry_retries_exhausted_is_true(self, client_always_timeout, fake_clock):
        """retries_exhausted=true"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.retries_exhausted is True

    def test_retry_total_attempts_is_2(self, client_always_timeout, fake_clock):
        """总共尝试2次（1次原始 + 1次重试）"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.retries_attempts == 2
        assert response.retries_max == 1

    def test_retry_error_is_retries_exhausted(self, client_always_timeout, fake_clock):
        """最终 error 为 retries_exhausted"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.error == "retries_exhausted"

    def test_retry_timeout_seconds_is_120(self, client_always_timeout, fake_clock):
        """重试耗尽后 timeout_seconds 仍为 120"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.timeout_seconds == 120.0

    def test_retry_created_requests_count(self, client_always_timeout, fake_clock):
        """重试1次共产生2个已完成的请求"""
        client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert len(client_always_timeout.completed_requests) == 2

    def test_retry_to_dict_contains_all_fields(self, client_always_timeout, fake_clock):
        """to_dict 包含 retries_exhausted=true 和 timeout_seconds=120"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")
        body = response.to_dict()

        assert body["status_code"] == 504
        assert body["retries_exhausted"] is True
        assert body["retries_attempts"] == 2
        assert body["retries_max"] == 1
        assert body["timeout_seconds"] == 120.0
        assert body["error"] == "retries_exhausted"

    def test_retry_message_contains_retry_count(self, client_always_timeout, fake_clock):
        """重试耗尽的消息包含重试次数"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert "重试" in response.message
        assert "1" in response.message

    def test_retry_max_0_no_retry(self, fake_clock):
        """max_retries=0 时不重试"""
        svc = LLMInferenceClient(
            timeout_seconds=120.0,
            max_retries=0,
            current_time_fn=fake_clock,
            llm_always_timeout=True,
        )
        response = svc.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.retries_exhausted is True
        assert response.status_code == 504
        assert response.retries_attempts == 1
        assert response.retries_max == 0
        assert len(svc.completed_requests) == 1


# ── 重试成功后场景 ──


class TestClientRetrySuccess:
    """重试机制在正常场景下的行为"""

    def test_no_retry_needed_on_success(self, client, fake_clock):
        """不超时的情况，首次即成功"""
        response = client.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.status_code == 200
        assert response.retries_exhausted is False
        assert response.retries_attempts == 0

    def test_no_retry_created_requests_count(self, client, fake_clock):
        """成功时只创建1个请求"""
        client.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert len(client.completed_requests) == 1
        assert client.active_requests == 0


# ── 自定义超时时间 ──


class TestCustomTimeout:
    """自定义超时时间"""

    def test_short_timeout_10_seconds(self, client_short_timeout, fake_clock):
        """短超时（10 秒），10 秒后触发，timeout_seconds=10"""
        req = client_short_timeout.create_request("user-001", "gpt-4", "Prompt")

        fake_clock.advance(9)
        assert client_short_timeout.check_timeout(req.request_id) is None

        fake_clock.advance(1)
        response = client_short_timeout.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.timeout_seconds == 10.0
        assert response.duration_seconds == pytest.approx(10.0)

    def test_short_timeout_retry(self, fake_clock):
        """短超时 + 重试：10秒超时，重试1次"""
        svc = LLMInferenceClient(
            timeout_seconds=10.0,
            max_retries=1,
            current_time_fn=fake_clock,
            llm_always_timeout=True,
        )
        response = svc.send_with_retry("user-001", "gpt-4", "Prompt")

        assert response.status_code == 504
        assert response.retries_exhausted is True
        assert response.timeout_seconds == 10.0


# ── 领域对象测试 ──


class TestInferenceRequestDomain:
    """InferenceRequest 领域对象测试"""

    def test_new_request_status(self, base_time):
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        assert req.status == "in_progress"
        assert req.error is None

    def test_is_timed_out_at_exactly_120(self, base_time):
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        assert req.is_timed_out(base_time + timedelta(seconds=120)) is True

    def test_is_not_timed_out_at_119(self, base_time):
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        assert req.is_timed_out(base_time + timedelta(seconds=119)) is False

    def test_mark_timed_out_sets_fields(self, base_time):
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        req.mark_timed_out(base_time + timedelta(seconds=120))

        assert req.status == "timeout"
        assert req.error == "request_timeout"
        assert req.completed_at == base_time + timedelta(seconds=120)

    def test_elapsed_seconds(self, base_time):
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        assert req.elapsed_seconds(base_time + timedelta(seconds=45)) == 45.0


class TestInferenceResponseDomain:
    """InferenceResponse 响应体测试"""

    def test_timeout_response_to_dict(self):
        resp = InferenceResponse(
            status_code=504,
            request_id="req-001",
            error="request_timeout",
            status="timeout",
            duration_seconds=120.0,
            timeout_seconds=120.0,
        )
        body = resp.to_dict()

        assert body["status_code"] == 504
        assert body["error"] == "request_timeout"
        assert body["timeout_seconds"] == 120.0
        assert body["status"] == "timeout"

    def test_retries_exhausted_response_to_dict(self):
        resp = InferenceResponse(
            status_code=504,
            request_id="req-001",
            error="retries_exhausted",
            status="timeout",
            duration_seconds=120.0,
            timeout_seconds=120.0,
            retries_attempts=2,
            retries_max=1,
            retries_exhausted=True,
        )
        body = resp.to_dict()

        assert body["retries_exhausted"] is True
        assert body["retries_attempts"] == 2
        assert body["retries_max"] == 1
        assert body["timeout_seconds"] == 120.0

    def test_success_response_to_dict(self):
        resp = InferenceResponse(
            status_code=200,
            request_id="req-001",
            status="completed",
            duration_seconds=60.5,
            timeout_seconds=120.0,
            retries_attempts=0,
            retries_max=1,
            retries_exhausted=False,
        )
        body = resp.to_dict()

        assert body["status_code"] == 200
        assert body["retries_exhausted"] is False


class TestInferenceTimeoutErrorDomain:
    """InferenceTimeoutError 异常测试"""

    def test_exception_fields(self):
        err = InferenceTimeoutError(
            request_id="req-001",
            duration_seconds=120.5,
            timeout_seconds=120.0,
        )
        assert err.request_id == "req-001"
        assert err.duration_seconds == 120.5
        assert err.timeout_seconds == 120.0
        assert "req-001" in str(err)

    def test_exception_raise_and_catch(self):
        with pytest.raises(InferenceTimeoutError) as exc_info:
            raise InferenceTimeoutError(
                request_id="req-001",
                duration_seconds=120.5,
                timeout_seconds=120.0,
            )
        assert exc_info.value.request_id == "req-001"


# ====================================================================
# 完整流程集成测试
# ====================================================================


class TestFullFlowIntegration:
    """完整流程集成测试"""

    def test_full_flow_timeout_at_120s(self, client, fake_clock):
        """完整流程：创建 -> 等待120秒 -> 超时检查 -> 504 + error=request_timeout + timeout_seconds=120"""
        req = client.create_request("user-001", "gpt-4", "Explain AI")
        assert req.status == "in_progress"
        assert client.active_requests == 1

        fake_clock.advance(60)
        assert client.check_timeout(req.request_id) is None
        assert req.status == "in_progress"
        assert client.active_requests == 1

        fake_clock.advance(60)
        response = client.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.error == "request_timeout"
        assert response.timeout_seconds == 120.0
        assert response.status == "timeout"
        assert response.duration_seconds == pytest.approx(120.0)
        assert client.active_requests == 0

    def test_full_flow_retry_exhausted(self, client_always_timeout, fake_clock):
        """完整流程：send_with_retry -> 超时 -> 重试1次 -> 仍超时 -> 504 + retries_exhausted"""
        response = client_always_timeout.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.status_code == 504
        assert response.retries_exhausted is True
        assert response.retries_attempts == 2
        assert response.retries_max == 1
        assert response.timeout_seconds == 120.0
        assert len(client_always_timeout.completed_requests) == 2

    def test_full_flow_success_no_retry(self, client, fake_clock):
        """完整流程：send_with_retry -> 成功 -> 无需重试"""
        response = client.send_with_retry("user-001", "gpt-4", "Explain AI")

        assert response.status_code == 200
        assert response.status == "completed"
        assert response.retries_exhausted is False
        assert response.retries_attempts == 0
        assert len(client.completed_requests) == 1

    def test_full_flow_multiple_requests_one_timeout(self, client, fake_clock):
        """多个请求：一个正常完成，一个超时"""
        req1 = client.create_request("user-001", "gpt-4", "Prompt A")
        req2 = client.create_request("user-002", "claude-3", "Prompt B")

        assert client.active_requests == 2

        fake_clock.advance(60)
        req1.mark_completed(fake_clock.current)
        client._completed_requests.append(req1)
        del client._requests[req1.request_id]
        assert client.active_requests == 1

        fake_clock.advance(65)
        response = client.check_timeout(req2.request_id)
        assert response is not None
        assert response.status_code == 504
        assert response.error == "request_timeout"
        assert response.timeout_seconds == 120.0
        assert client.active_requests == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
