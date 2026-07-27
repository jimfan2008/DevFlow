import uuid
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import pytest


def _default_current_time() -> datetime:
    return datetime.now(timezone.utc)


# ====================================================================
# 被测试的领域模型
# ====================================================================


class InferenceStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMED_OUT = "timeout"
    FAILED = "failed"


class InferenceErrorCode(str, Enum):
    REQUEST_TIMEOUT = "request_timeout"
    INFERENCE_ERROR = "inference_error"


@dataclass
class InferenceRequest:
    """单次推理请求"""
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

    def mark_completed(self, now: datetime = None):
        t = now or self._current_time_fn()
        self.status = InferenceStatus.COMPLETED.value
        self.completed_at = t

    def mark_timed_out(self, now: datetime = None):
        t = now or self._current_time_fn()
        self.status = InferenceStatus.TIMED_OUT.value
        self.error = InferenceErrorCode.REQUEST_TIMEOUT.value
        self.completed_at = t


@dataclass
class InferenceResponse:
    """推理请求响应"""
    status_code: int
    request_id: str
    error: Optional[str] = None
    status: Optional[str] = None
    duration_seconds: Optional[float] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "request_id": self.request_id,
            "error": self.error,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 2) if self.duration_seconds is not None else None,
            "message": self.message,
        }


class InferenceTimeoutError(Exception):
    """推理超时异常"""

    def __init__(self, request_id: str, duration_seconds: float, timeout_seconds: float = 120.0):
        self.request_id = request_id
        self.duration_seconds = duration_seconds
        self.timeout_seconds = timeout_seconds
        self.message = f"推理请求 {request_id} 超时（持续 {duration_seconds:.1f} 秒，超时阈值 {timeout_seconds:.0f} 秒）"
        super().__init__(self.message)


class InferenceManager:
    """推理请求管理器：创建请求、超时检查、升级机制"""

    HTTP_STATUS_GATEWAY_TIMEOUT = 504
    DEFAULT_TIMEOUT_SECONDS = 120.0

    def __init__(
        self,
        timeout_seconds: float = None,
        current_time_fn: Callable[[], datetime] = None,
    ):
        self._timeout_seconds = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS
        self._current_time_fn = current_time_fn or _default_current_time
        self._requests: Dict[str, InferenceRequest] = {}
        self._completed_requests: List[InferenceRequest] = []

    def create_request(
        self, user_id: str, model: str, prompt: str
    ) -> InferenceRequest:
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

    def get_request(self, request_id: str) -> Optional[InferenceRequest]:
        return self._requests.get(request_id)

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
                message=f"推理请求超时（持续 {duration:.1f} 秒，超时阈值 {req.timeout_seconds:.0f} 秒）",
            )
        return None

    def complete_request(self, request_id: str) -> Optional[InferenceResponse]:
        now = self._current_time_fn()
        req = self._requests.get(request_id)
        if req is None:
            return InferenceResponse(
                status_code=404,
                request_id=request_id,
                message=f"请求 {request_id} 不存在",
            )
        if req.is_timed_out(now):
            return self.check_timeout(request_id)
        req.mark_completed(now)
        duration = req.elapsed_seconds(now)
        self._completed_requests.append(req)
        del self._requests[request_id]
        return InferenceResponse(
            status_code=200,
            request_id=request_id,
            status=InferenceStatus.COMPLETED.value,
            duration_seconds=duration,
            message="推理请求完成",
        )

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
def manager(fake_clock):
    return InferenceManager(
        timeout_seconds=120.0,
        current_time_fn=fake_clock,
    )


@pytest.fixture
def manager_short_timeout(fake_clock):
    return InferenceManager(
        timeout_seconds=10.0,
        current_time_fn=fake_clock,
    )


@pytest.fixture
def active_request(manager, fake_clock):
    return manager.create_request(
        user_id="user-001",
        model="gpt-4",
        prompt="Explain quantum computing",
    )


# ====================================================================
# 测试：单次推理 >120 秒触发超时
# ====================================================================

class TestInferenceTimeoutAt120Seconds:
    """验证单次推理请求持续时间超过 120 秒时，系统标记为超时"""

    def test_request_status_switches_to_timeout_at_120s(self, manager, active_request, fake_clock):
        """请求在第 120 秒时状态从 in_progress 切换为 timeout"""
        assert active_request.status == "in_progress"

        fake_clock.advance(120)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status == "timeout"

    def test_return_http_504_at_120s(self, manager, active_request, fake_clock):
        """返回 HTTP 504"""
        fake_clock.advance(120)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504

    def test_response_body_contains_error_request_timeout(self, manager, active_request, fake_clock):
        """响应 Body 包含 error=request_timeout"""
        fake_clock.advance(120)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.error == "request_timeout"

    def test_response_body_contains_duration_seconds_120(self, manager, active_request, fake_clock):
        """响应 Body 包含 duration_seconds=120"""
        fake_clock.advance(120)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.duration_seconds == pytest.approx(120.0)

    def test_request_removed_from_active_after_timeout(self, manager, active_request, fake_clock):
        """超时后请求从活跃列表中移除"""
        assert manager.active_requests == 1

        fake_clock.advance(120)
        manager.check_timeout(active_request.request_id)

        assert manager.active_requests == 0
        assert active_request.request_id not in manager._requests

    def test_request_added_to_completed_after_timeout(self, manager, active_request, fake_clock):
        """超时后请求加入已完成列表"""
        fake_clock.advance(120)
        manager.check_timeout(active_request.request_id)

        completed = manager.completed_requests
        assert len(completed) == 1
        assert completed[0].request_id == active_request.request_id
        assert completed[0].status == "timeout"

    def test_request_error_is_request_timeout(self, manager, active_request, fake_clock):
        """请求对象的 error 字段为 request_timeout"""
        fake_clock.advance(120)
        manager.check_timeout(active_request.request_id)

        completed = manager.completed_requests[0]
        assert completed.error == "request_timeout"

    def test_to_dict_contains_all_required_fields(self, manager, active_request, fake_clock):
        """to_dict 包含所有必需字段"""
        fake_clock.advance(120)

        response = manager.check_timeout(active_request.request_id)
        body = response.to_dict()

        assert body["status_code"] == 504
        assert body["error"] == "request_timeout"
        assert body["status"] == "timeout"
        assert body["duration_seconds"] == 120.0
        assert "request_id" in body
        assert "message" in body


# ── 边界：120 秒前后 ──

class TestTimeoutBoundary:
    """超时边界值测试"""

    def test_119_seconds_not_timed_out(self, manager, active_request, fake_clock):
        """119 秒时不应超时"""
        fake_clock.advance(119)

        response = manager.check_timeout(active_request.request_id)

        assert response is None
        assert manager.active_requests == 1

    def test_119_9_seconds_not_timed_out(self, manager, active_request, fake_clock):
        """119.9 秒时不应超时"""
        fake_clock.advance(119.9)

        response = manager.check_timeout(active_request.request_id)

        assert response is None
        assert active_request.status == "in_progress"

    def test_exactly_120_seconds_is_timed_out(self, manager, active_request, fake_clock):
        """恰好 120 秒时应超时"""
        fake_clock.advance(120)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.error == "request_timeout"

    def test_120_1_seconds_is_timed_out(self, manager, active_request, fake_clock):
        """120.1 秒时应超时"""
        fake_clock.advance(120.1)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.duration_seconds == pytest.approx(120.1)

    def test_200_seconds_is_timed_out(self, manager, active_request, fake_clock):
        """200 秒时应超时"""
        fake_clock.advance(200)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.duration_seconds == pytest.approx(200.0)

    def test_300_seconds_is_timed_out(self, manager, active_request, fake_clock):
        """300 秒时应超时"""
        fake_clock.advance(300)

        response = manager.check_timeout(active_request.request_id)

        assert response is not None
        assert response.duration_seconds == pytest.approx(300.0)


# ── 正常完成不在超时内的请求 ──

class TestNormalCompletion:
    """推理在超时前正常完成"""

    def test_complete_before_120s(self, manager, active_request, fake_clock):
        """60 秒时正常完成"""
        fake_clock.advance(60)

        response = manager.complete_request(active_request.request_id)

        assert response is not None
        assert response.status_code == 200
        assert response.status == "completed"
        assert response.duration_seconds == pytest.approx(60.0)

    def test_complete_at_119s(self, manager, active_request, fake_clock):
        """119 秒时正常完成（未到超时）"""
        fake_clock.advance(119)

        response = manager.complete_request(active_request.request_id)

        assert response is not None
        assert response.status_code == 200
        assert response.status == "completed"

    def test_complete_after_timeout_returns_504(self, manager, active_request, fake_clock):
        """即使调用 complete_request，超时了仍返回 504"""
        fake_clock.advance(130)

        response = manager.complete_request(active_request.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.error == "request_timeout"

    def test_completed_request_not_in_active(self, manager, active_request, fake_clock):
        """正常完成后不在活跃列表中"""
        fake_clock.advance(30)
        manager.complete_request(active_request.request_id)

        assert manager.active_requests == 0
        completed = manager.completed_requests[0]
        assert completed.status == "completed"


# ── 不存在的请求 ──

class TestNonexistentRequest:
    """对不存在的 request_id 操作"""

    def test_check_timeout_nonexistent_returns_404(self, manager):
        """检查不存在的请求返回 404"""
        response = manager.check_timeout("nonexistent-id")

        assert response is not None
        assert response.status_code == 404

    def test_complete_nonexistent_returns_404(self, manager):
        """完成不存在的请求返回 404"""
        response = manager.complete_request("nonexistent-id")

        assert response is not None
        assert response.status_code == 404

    def test_get_nonexistent_returns_none(self, manager):
        """获取不存在的请求返回 None"""
        assert manager.get_request("nonexistent-id") is None


# ── 重复超时检查 ──

class TestRepeatedTimeoutCheck:
    """对已超时的请求重复检查"""

    def test_check_timeout_after_already_timed_out(self, manager, active_request, fake_clock):
        """超时后再检查返回 None（已从活跃列表移除）"""
        fake_clock.advance(120)
        manager.check_timeout(active_request.request_id)

        response = manager.check_timeout(active_request.request_id)

        assert response.status_code == 404


# ── 多个请求独立超时 ──

class TestMultipleRequests:
    """多个推理请求独立超时"""

    def test_two_requests_timeout_independently(self, manager, fake_clock):
        """两个请求各自独立超时"""
        req1 = manager.create_request("user-001", "gpt-4", "Prompt A")
        fake_clock.advance(0.1)
        req2 = manager.create_request("user-002", "claude-3", "Prompt B")

        assert manager.active_requests == 2

        fake_clock.advance(120)
        resp1 = manager.check_timeout(req1.request_id)
        assert resp1 is not None
        assert resp1.status_code == 504
        assert manager.active_requests == 1

        resp2 = manager.check_timeout(req2.request_id)
        assert resp2 is not None
        assert resp2.status_code == 504
        assert manager.active_requests == 0

    def test_one_times_out_other_completes(self, manager, fake_clock):
        """一个超时，另一个正常完成"""
        req1 = manager.create_request("user-001", "gpt-4", "Prompt A")
        req2 = manager.create_request("user-002", "claude-3", "Prompt B")

        fake_clock.advance(60)
        resp2 = manager.complete_request(req2.request_id)
        assert resp2.status_code == 200
        assert manager.active_requests == 1

        fake_clock.advance(65)
        resp1 = manager.check_timeout(req1.request_id)
        assert resp1 is not None
        assert resp1.status_code == 504
        assert manager.active_requests == 0

    def test_three_requests_all_timeout(self, manager, fake_clock):
        """三个请求全部超时"""
        requests = []
        for i in range(3):
            fake_clock.advance(0.01)
            req = manager.create_request(f"user-{i}", "gpt-4", f"Prompt {i}")
            requests.append(req)

        assert manager.active_requests == 3

        fake_clock.advance(120)
        for req in requests:
            resp = manager.check_timeout(req.request_id)
            assert resp is not None
            assert resp.status_code == 504

        assert manager.active_requests == 0
        assert len(manager.completed_requests) == 3


# ── 自定义超时 ──

class TestCustomTimeout:
    """自定义超时时间"""

    def test_short_timeout_10_seconds(self, manager_short_timeout, fake_clock):
        """短超时（10 秒），10 秒后触发"""
        req = manager_short_timeout.create_request("user-001", "gpt-4", "Prompt")

        fake_clock.advance(9)
        assert manager_short_timeout.check_timeout(req.request_id) is None

        fake_clock.advance(1)
        response = manager_short_timeout.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.duration_seconds == pytest.approx(10.0)

    def test_custom_timeout_response_duration_matches(self, manager_short_timeout, fake_clock):
        """自定义超时的 duration_seconds 正确反映实际持续时间"""
        req = manager_short_timeout.create_request("user-001", "gpt-4", "Prompt")

        fake_clock.advance(15)
        response = manager_short_timeout.check_timeout(req.request_id)

        assert response is not None
        assert response.duration_seconds == pytest.approx(15.0)


# ── 领域对象测试 ──

class TestInferenceRequest:
    """InferenceRequest 领域对象测试"""

    def test_new_request_status_is_in_progress(self, base_time):
        """新请求状态为 in_progress"""
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

    def test_is_timed_out_at_120_seconds(self, base_time):
        """120 秒时 is_timed_out 为 True"""
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        now = base_time + timedelta(seconds=120)
        assert req.is_timed_out(now) is True

    def test_is_not_timed_out_at_119_seconds(self, base_time):
        """119 秒时 is_timed_out 为 False"""
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        now = base_time + timedelta(seconds=119)
        assert req.is_timed_out(now) is False

    def test_mark_timed_out_sets_fields(self, base_time):
        """mark_timed_out 正确设置字段"""
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        now = base_time + timedelta(seconds=120)
        req.mark_timed_out(now)

        assert req.status == "timeout"
        assert req.error == "request_timeout"
        assert req.completed_at == now

    def test_mark_completed_sets_fields(self, base_time):
        """mark_completed 正确设置字段"""
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        now = base_time + timedelta(seconds=60)
        req.mark_completed(now)

        assert req.status == "completed"
        assert req.completed_at == now

    def test_elapsed_seconds_correct(self, base_time):
        """elapsed_seconds 计算正确"""
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            prompt="Test",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        assert req.elapsed_seconds(base_time + timedelta(seconds=45)) == 45.0


class TestInferenceResponse:
    """InferenceResponse 响应体测试"""

    def test_timeout_response_to_dict(self):
        """超时响应 to_dict 格式正确"""
        resp = InferenceResponse(
            status_code=504,
            request_id="req-001",
            error="request_timeout",
            status="timeout",
            duration_seconds=120.0,
            message="推理请求超时",
        )
        body = resp.to_dict()

        assert body["status_code"] == 504
        assert body["error"] == "request_timeout"
        assert body["status"] == "timeout"
        assert body["duration_seconds"] == 120.0

    def test_success_response_to_dict(self):
        """成功响应 to_dict 格式正确"""
        resp = InferenceResponse(
            status_code=200,
            request_id="req-001",
            status="completed",
            duration_seconds=60.5,
            message="推理请求完成",
        )
        body = resp.to_dict()

        assert body["status_code"] == 200
        assert body["error"] is None
        assert body["status"] == "completed"
        assert body["duration_seconds"] == 60.5

    def test_duration_seconds_rounded_to_two_decimals(self):
        """duration_seconds 保留两位小数"""
        resp = InferenceResponse(
            status_code=504,
            request_id="req-001",
            error="request_timeout",
            status="timeout",
            duration_seconds=120.12345,
        )
        body = resp.to_dict()

        assert body["duration_seconds"] == 120.12


class TestInferenceTimeoutError:
    """InferenceTimeoutError 异常测试"""

    def test_exception_contains_fields(self):
        """异常包含所有字段"""
        err = InferenceTimeoutError(
            request_id="req-001",
            duration_seconds=120.5,
            timeout_seconds=120.0,
        )
        assert err.request_id == "req-001"
        assert err.duration_seconds == 120.5
        assert err.timeout_seconds == 120.0
        assert "req-001" in str(err)

    def test_exception_can_be_raised_and_caught(self):
        """异常可正常抛掷和捕获"""
        with pytest.raises(InferenceTimeoutError) as exc_info:
            raise InferenceTimeoutError(
                request_id="req-001",
                duration_seconds=120.5,
                timeout_seconds=120.0,
            )
        assert exc_info.value.request_id == "req-001"
        assert exc_info.value.duration_seconds == 120.5


# ── 完整流程集成测试 ──

class TestFullFlowIntegration:
    """完整流程集成测试"""

    def test_full_flow_request_timeout(self, manager, fake_clock):
        """完整流程：创建 -> 等待120秒 -> 超时检查 -> 返回504"""
        req = manager.create_request("user-001", "gpt-4", "Explain AI")
        assert req.status == "in_progress"
        assert manager.active_requests == 1

        fake_clock.advance(60)
        assert manager.check_timeout(req.request_id) is None
        assert req.status == "in_progress"

        fake_clock.advance(60)
        response = manager.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.error == "request_timeout"
        assert response.status == "timeout"
        assert response.duration_seconds == pytest.approx(120.0)
        assert manager.active_requests == 0

    def test_full_flow_request_completes_before_timeout(self, manager, fake_clock):
        """完整流程：创建 -> 等待60秒 -> 正常完成 -> 返回200"""
        req = manager.create_request("user-001", "gpt-4", "Explain AI")

        fake_clock.advance(60)
        response = manager.complete_request(req.request_id)

        assert response is not None
        assert response.status_code == 200
        assert response.status == "completed"
        assert response.duration_seconds == pytest.approx(60.0)
        assert manager.active_requests == 0

    def test_full_flow_request_exceeds_timeout_then_checked(self, manager, fake_clock):
        """完整流程：创建 -> 等待200秒 -> 超时检查 -> duration_seconds=200"""
        req = manager.create_request("user-001", "gpt-4", "Explain AI")

        fake_clock.advance(200)
        response = manager.check_timeout(req.request_id)

        assert response is not None
        assert response.status_code == 504
        assert response.duration_seconds == pytest.approx(200.0)

    def test_full_flow_multiple_requests_mixed_outcome(self, manager, fake_clock):
        """完整流程：3 个请求，2 个正常完成，1 个超时"""
        req1 = manager.create_request("user-001", "gpt-4", "A")
        req2 = manager.create_request("user-002", "gpt-4", "B")
        req3 = manager.create_request("user-003", "gpt-4", "C")

        assert manager.active_requests == 3

        fake_clock.advance(30)
        resp1 = manager.complete_request(req1.request_id)
        assert resp1.status_code == 200
        assert resp1.duration_seconds == pytest.approx(30.0)
        assert manager.active_requests == 2

        fake_clock.advance(85)
        resp2 = manager.complete_request(req2.request_id)
        assert resp2.status_code == 200
        assert resp2.duration_seconds == pytest.approx(115.0)
        assert manager.active_requests == 1

        fake_clock.advance(5)
        resp3 = manager.check_timeout(req3.request_id)
        assert resp3 is not None
        assert resp3.status_code == 504
        assert resp3.error == "request_timeout"
        assert resp3.duration_seconds == pytest.approx(120.0)
        assert manager.active_requests == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
