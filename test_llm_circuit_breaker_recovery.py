import time
import uuid
from enum import Enum
from typing import Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import pytest


# ====================================================================
# 被测试的领域模型
# ====================================================================

class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RequestStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class APIResponse:
    """API 响应"""
    status_code: int
    status: str
    request_id: str
    data: Optional[dict] = None
    message: str = ""


class CircuitBreaker:
    """熔断器：支持 closed -> open -> half_open -> closed 状态流转"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_open_time: Optional[datetime] = None

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    def record_failure(self):
        """记录一次失败"""
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN
            self._last_open_time = datetime.now(timezone.utc)

    def record_success(self):
        """记录一次成功"""
        self._failure_count = 0
        self._state = CircuitBreakerState.CLOSED

    def allow_request(self) -> bool:
        """判断是否允许请求通过"""
        if self._state == CircuitBreakerState.CLOSED:
            return True
        if self._state == CircuitBreakerState.OPEN:
            return self._transition_to_half_open()
        if self._state == CircuitBreakerState.HALF_OPEN:
            return True
        return False

    def probe_success(self):
        """探测请求成功：half_open -> closed"""
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._failure_count = 0
            self._state = CircuitBreakerState.CLOSED

    def probe_failure(self):
        """探测请求失败：half_open -> open"""
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.OPEN
            self._last_open_time = datetime.now(timezone.utc)
            self._failure_count += 1

    def _transition_to_half_open(self) -> bool:
        """若超时已到，则切换为半开状态并允许探测请求通过"""
        if (
            self._last_open_time is not None
            and self._last_failure_time is not None
        ):
            elapsed = (
                datetime.now(timezone.utc) - self._last_open_time
            ).total_seconds()
            if elapsed >= self.recovery_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
                return True
        return False


class LLMAPIService:
    """LLM API 服务：整合熔断器的推理请求处理"""

    def __init__(self, circuit_breaker: CircuitBreaker, mock_fail: bool = False):
        self.circuit_breaker = circuit_breaker
        self._mock_fail = mock_fail
        self._request_count = 0

    def inference_request(self, user_id: str, prompt: str) -> APIResponse:
        """处理推理请求"""
        self._request_count += 1

        # 熔断器检查
        if not self.circuit_breaker.allow_request():
            return APIResponse(
                status_code=503,
                status=RequestStatus.REJECTED.value,
                request_id=str(uuid.uuid4()),
                message="服务暂时不可用（熔断器打开）",
            )

        # 模拟上游 LLM 调用结果
        if self._mock_fail:
            self.circuit_breaker.record_failure()
            return APIResponse(
                status_code=500,
                status=RequestStatus.REJECTED.value,
                request_id=str(uuid.uuid4()),
                message="上游 LLM 服务调用失败",
            )

        # 成功路径
        self.circuit_breaker.record_success()
        return APIResponse(
            status_code=200,
            status=RequestStatus.ACCEPTED.value,
            request_id=str(uuid.uuid4()),
            data={"completion": f"response to: {prompt}", "tokens_used": 128},
            message="推理请求成功完成",
        )

    def probe_request(self) -> APIResponse:
        """发送探测请求：若熔断器为 open 且超时已到，先过渡为 half_open 再执行探测"""
        self._request_count += 1

        # open 状态下检查是否需要过渡到 half_open
        if not self.circuit_breaker.allow_request():
            return APIResponse(
                status_code=503,
                status=RequestStatus.REJECTED.value,
                request_id=str(uuid.uuid4()),
                message="探测请求被拒绝（熔断器打开，恢复超时未到）",
            )

        if self._mock_fail:
            self.circuit_breaker.probe_failure()
            return APIResponse(
                status_code=500,
                status=RequestStatus.REJECTED.value,
                request_id=str(uuid.uuid4()),
                message="探测请求失败",
            )

        self.circuit_breaker.probe_success()
        return APIResponse(
            status_code=200,
            status=RequestStatus.ACCEPTED.value,
            request_id=str(uuid.uuid4()),
            data={"healthy": True},
            message="探测请求成功",
        )

    @property
    def request_count(self) -> int:
        return self._request_count


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def cb_short_timeout():
    """快速恢复的熔断器（timeout=0.1s，threshold=3）"""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)


@pytest.fixture
def service_fail(cb_short_timeout):
    """模拟失败的 LLM 服务"""
    return LLMAPIService(circuit_breaker=cb_short_timeout, mock_fail=True)


@pytest.fixture
def service_success(cb_short_timeout):
    """模拟成功的 LLM 服务"""
    return LLMAPIService(circuit_breaker=cb_short_timeout, mock_fail=False)


@pytest.fixture
def service_mixed(cb_short_timeout):
    """前几次失败、后续成功的服务 — 通过 toggle_fail 控制"""
    svc = LLMAPIService(circuit_breaker=cb_short_timeout, mock_fail=True)
    return svc


# ====================================================================
# 测试：熔断恢复后 API 调用正常
# ====================================================================

class TestCircuitBreakerRecovery:
    """验证熔断器半开状态后探测成功，恢复为关闭状态，后续请求正常"""

    def test_probe_success_transitions_half_open_to_closed(self, cb_short_timeout):
        """探测请求成功：熔断器状态从 half_open 切换为 closed"""
        # 1. 触发熔断：连续 3 次失败
        for _ in range(3):
            cb_short_timeout.record_failure()

        assert cb_short_timeout.state == CircuitBreakerState.OPEN

        # 2. 等待恢复超时
        time.sleep(0.15)

        # 3. 下一个请求触发 half_open 过渡
        allowed = cb_short_timeout.allow_request()
        assert allowed is True
        assert cb_short_timeout.state == CircuitBreakerState.HALF_OPEN

        # 4. 探测请求成功
        cb_short_timeout.probe_success()

        # 5. 验证状态已恢复为 closed
        assert cb_short_timeout.state == CircuitBreakerState.CLOSED

    def test_full_flow_recover_and_normal_request(self, service_mixed):
        """完整流程：触发熔断 -> 等待恢复 -> 探测成功 -> 普通请求正常"""
        # 第 1 步：连续失败触发熔断
        for _ in range(3):
            resp = service_mixed.inference_request("user1", "fail prompt")
            assert resp.status_code == 500

        assert service_mixed.circuit_breaker.state == CircuitBreakerState.OPEN

        # 第 2 步：熔断打开时，请求被拒绝，返回 503
        resp = service_mixed.inference_request("user1", "should be rejected")
        assert resp.status_code == 503

        # 第 3 步：等待恢复超时
        time.sleep(0.15)

        # 第 4 步：切换 mock 为成功模式，发送探测请求
        service_mixed._mock_fail = False
        probe_resp = service_mixed.probe_request()

        # 验收：探测请求成功返回
        assert probe_resp.status_code == 200, f"探测请求应返回 200，实际 {probe_resp.status_code}"
        assert probe_resp.data is not None
        assert probe_resp.data.get("healthy") is True

        # 验收：熔断器状态从 half_open 切换为 closed
        assert (
            service_mixed.circuit_breaker.state == CircuitBreakerState.CLOSED
        ), f"熔断器应为 closed，实际 {service_mixed.circuit_breaker.state}"

        # 第 5 步：后续普通推理请求正常执行，返回 HTTP 200
        normal_resp = service_mixed.inference_request("user1", "test prompt")
        assert (
            normal_resp.status_code == 200
        ), f"后续普通请求应返回 200，实际 {normal_resp.status_code}"
        assert normal_resp.data is not None
        assert "completion" in normal_resp.data

    def test_probe_failure_keep_open_state(self, service_mixed):
        """探测请求失败则回到 open 状态，不恢复"""
        # 触发熔断
        for _ in range(3):
            service_mixed.inference_request("user1", "fail")

        assert service_mixed.circuit_breaker.state == CircuitBreakerState.OPEN

        # 等待超时
        time.sleep(0.15)

        # 探测请求（仍然失败模式）
        probe_resp = service_mixed.probe_request()
        assert probe_resp.status_code == 500

        # 熔断器回到 open 状态
        assert (
            service_mixed.circuit_breaker.state == CircuitBreakerState.OPEN
        ), f"探测失败后应回到 open，实际 {service_mixed.circuit_breaker.state}"

    def test_half_open_allows_only_probe(self, cb_short_timeout):
        """半开状态下只允许探测请求通过"""
        # 触发熔断
        for _ in range(3):
            cb_short_timeout.record_failure()

        assert cb_short_timeout.state == CircuitBreakerState.OPEN

        # 等待超时，allow_request 触发 half_open 过渡
        time.sleep(0.15)
        allowed = cb_short_timeout.allow_request()
        assert allowed is True
        assert cb_short_timeout.state == CircuitBreakerState.HALF_OPEN

        # 探测成功
        cb_short_timeout.probe_success()
        assert cb_short_timeout.state == CircuitBreakerState.CLOSED

        # 之后 allow_request 应直接返回 True（无需再过渡）
        assert cb_short_timeout.allow_request() is True

    def test_circuit_breaker_state_sequence(self, cb_short_timeout):
        """验证熔断器状态流转序列：closed -> open -> half_open -> closed"""
        states_seen = [cb_short_timeout.state]

        # closed -> open
        for _ in range(3):
            cb_short_timeout.record_failure()
        states_seen.append(cb_short_timeout.state)

        # open -> half_open
        time.sleep(0.15)
        cb_short_timeout.allow_request()
        states_seen.append(cb_short_timeout.state)

        # half_open -> closed
        cb_short_timeout.probe_success()
        states_seen.append(cb_short_timeout.state)

        expected = [
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
            CircuitBreakerState.CLOSED,
        ]
        assert states_seen == expected, f"状态序列不匹配：{states_seen}"

    def test_multiple_success_after_recovery(self, service_mixed):
        """熔断恢复后，连续多次请求均正常"""
        # 触发熔断
        for _ in range(3):
            service_mixed.inference_request("user1", "fail")
        assert service_mixed.circuit_breaker.state == CircuitBreakerState.OPEN

        # 等待 + 探测
        time.sleep(0.15)
        service_mixed._mock_fail = False
        service_mixed.probe_request()
        assert service_mixed.circuit_breaker.state == CircuitBreakerState.CLOSED

        # 连续 5 次请求
        for i in range(5):
            resp = service_mixed.inference_request("user1", f"prompt {i}")
            assert resp.status_code == 200, f"第 {i + 1} 次请求应返回 200"
            assert "completion" in resp.data

    def test_failure_threshold_boundary_exact(self):
        """边界：恰好达到 failure_threshold 时才熔断"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # 失败 2 次（threshold-1），不应熔断
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED, "失败次数未达阈值不应熔断"
        assert cb._failure_count == 2

        # 第 3 次（恰好==threshold），应熔断
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb._failure_count == 3

    def test_failure_threshold_boundary_exceed(self):
        """边界：超过 threshold 多次失败仍保持 open"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        for _ in range(5):
            cb.record_failure()

        assert cb.state == CircuitBreakerState.OPEN
        assert cb._failure_count == 5

    def test_recovery_timeout_not_elapsed_yet(self):
        """边界：恢复超时未到之前，不应允许请求通过"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # 仅等待 0.2s，远小于 1.0s 超时
        time.sleep(0.2)
        allowed = cb.allow_request()
        assert allowed is False, "恢复超时未到，不应允许请求"
        assert cb.state == CircuitBreakerState.OPEN

    def test_recovery_timeout_exact_boundary(self):
        """边界：恰好等于恢复超时时应触发 half_open"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # 精确等待 recovery_timeout
        time.sleep(0.12)
        allowed = cb.allow_request()
        assert allowed is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_probe_success_no_op_in_closed_state(self):
        """边界：closed 状态下调用 probe_success 不应改变状态"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        assert cb.state == CircuitBreakerState.CLOSED

        cb.probe_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_probe_failure_no_op_in_closed_state(self):
        """边界：closed 状态下调用 probe_failure 不应改变状态"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb._failure_count == 0

        cb.probe_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb._failure_count == 0

    def test_probe_failure_no_op_in_open_state(self):
        """边界：open 状态下调用 probe_failure 不应改变状态"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        cb.probe_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_record_success_resets_failure_count(self):
        """边界：成功记录重置 failure_count 为 0"""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED

    def test_open_without_last_open_time_no_transition(self):
        """边界：_last_open_time 为 None 时不应切换到 half_open"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb._state = CircuitBreakerState.OPEN
        cb._last_open_time = None  # 强制为 None
        cb._last_failure_time = None

        time.sleep(0.2)
        allowed = cb.allow_request()
        assert allowed is False, "_last_open_time 为 None 时不应允许"
        assert cb.state == CircuitBreakerState.OPEN

    def test_half_open_consecutive_probe_success(self):
        """边界：half_open 下连续 probe_success 多次应保持一致 closed"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.allow_request()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.probe_success()
        assert cb.state == CircuitBreakerState.CLOSED

        # 再次 probe_success（已在 closed 状态下）
        cb.probe_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_recover_then_fail_again_triggers_open(self, service_mixed):
        """边界：恢复后再次连续失败应重新进入 open 状态"""
        # 第一轮熔断
        for _ in range(3):
            service_mixed.inference_request("user1", "fail")
        assert service_mixed.circuit_breaker.state == CircuitBreakerState.OPEN

        # 恢复
        time.sleep(0.15)
        service_mixed._mock_fail = False
        service_mixed.probe_request()
        assert service_mixed.circuit_breaker.state == CircuitBreakerState.CLOSED

        # 第二轮再次失败
        service_mixed._mock_fail = True
        for _ in range(3):
            service_mixed.inference_request("user1", "fail again")
        assert service_mixed.circuit_breaker.state == CircuitBreakerState.OPEN

    def test_request_count_increments_correctly(self, service_mixed):
        """边界：request_count 正确统计探测请求和普通请求"""
        assert service_mixed.request_count == 0

        service_mixed.inference_request("user1", "p1")
        assert service_mixed.request_count == 1

        time.sleep(0.15)
        service_mixed._mock_fail = False
        service_mixed.probe_request()
        assert service_mixed.request_count == 2

        service_mixed.inference_request("user1", "p2")
        assert service_mixed.request_count == 3

    def test_probe_response_message_content(self, service_mixed):
        """边界：探测请求返回体的 message 字段内容正确"""
        for _ in range(3):
            service_mixed.inference_request("user1", "fail")

        time.sleep(0.15)
        service_mixed._mock_fail = False
        resp = service_mixed.probe_request()

        assert resp.status_code == 200
        assert resp.data is not None
        assert resp.data.get("healthy") is True
        assert "探测请求成功" in resp.message

    def test_probe_failure_response_message_content(self, service_mixed):
        """边界：探测请求失败时返回体的 message 字段内容正确"""
        for _ in range(3):
            service_mixed.inference_request("user1", "fail")

        time.sleep(0.15)
        resp = service_mixed.probe_request()

        assert resp.status_code == 500
        assert "探测请求失败" in resp.message

    def test_awaiting_recovery_rejects_normal_request(self, service_mixed):
        """边界：恢复等待期间普通推理请求应返回 503"""
        for _ in range(3):
            service_mixed.inference_request("user1", "fail")

        assert service_mixed.circuit_breaker.state == CircuitBreakerState.OPEN

        # 未等到超时，立刻发请求
        resp = service_mixed.inference_request("user1", "should reject")
        assert resp.status_code == 503
        assert "熔断器打开" in resp.message
        assert resp.status == RequestStatus.REJECTED.value

    def test_custom_threshold_and_timeout(self):
        """边界：自定义 threshold 和 timeout 参数生效"""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

        # threshold=1，一次失败即熔断
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # timeout=0.05s
        time.sleep(0.08)
        allowed = cb.allow_request()
        assert allowed is True
        assert cb.state == CircuitBreakerState.HALF_OPEN
