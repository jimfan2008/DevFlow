import pytest
import uuid
import json
import time
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field


# ====================================================================
# 被测试的领域模型
# ====================================================================

def _default_current_time() -> datetime:
    return datetime.now(timezone.utc)


class SessionStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    EXPIRED = "expired"


@dataclass
class LlmSession:
    """LLM API 会话"""
    session_id: str
    user_id: str
    started_at: datetime
    timeout_seconds: float = 1800.0  # 30 分钟
    status: str = SessionStatus.ACTIVE.value
    _current_time_fn: callable = field(
        default_factory=lambda: _default_current_time, repr=False
    )

    def elapsed_seconds(self, now: datetime = None) -> float:
        """计算从会话开始到现在经过的秒数"""
        t = now or self._current_time_fn()
        return (t - self.started_at).total_seconds()

    def is_timed_out(self, now: datetime = None) -> bool:
        """判断会话是否已超过 30 分钟超时阈值"""
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def remaining_seconds(self, now: datetime = None) -> float:
        """剩余可用时间"""
        return max(0.0, self.timeout_seconds - self.elapsed_seconds(now))

    def block(self, now: datetime = None):
        """将会话标记为 blocked"""
        self.status = SessionStatus.BLOCKED.value

    def is_blocked(self) -> bool:
        """检查会话是否已被阻塞"""
        return self.status == SessionStatus.BLOCKED.value


@dataclass
class SessionTimeoutResponse:
    """会话超时响应"""
    status_code: int
    error: str
    status: str
    session_id: str
    waited_seconds: float
    message: str
    retries_exhausted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "error": self.error,
            "status": self.status,
            "session_id": self.session_id,
            "waited_seconds": round(self.waited_seconds, 2),
            "message": self.message,
            "retries_exhausted": self.retries_exhausted,
        }


class SessionTimeoutError(Exception):
    """会话超时异常"""

    def __init__(
        self, session_id: str, waited_seconds: float, message: str = None
    ):
        self.session_id = session_id
        self.waited_seconds = waited_seconds
        self.message = message or (
            f"会话 {session_id} 超时，已持续 {waited_seconds:.1f} 秒"
        )
        super().__init__(self.message)


class LlmSessionManager:
    """LLM API 会话管理器"""

    DEFAULT_TIMEOUT_SECONDS = 1800.0  # 30 分钟
    MAX_RETRY_COUNT = 3
    RETRY_INTERVAL_SECONDS = 5.0
    HTTP_STATUS_REQUEST_TIMEOUT = 408

    def __init__(
        self,
        timeout_seconds: float = None,
        current_time_fn: callable = None,
        max_retries: int = None,
        retry_interval: float = None,
    ):
        self._sessions: Dict[str, LlmSession] = {}
        self._timeout_seconds = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS
        self._current_time_fn = current_time_fn or _default_current_time
        self._max_retries = max_retries if max_retries is not None else self.MAX_RETRY_COUNT
        self._retry_interval = (
            retry_interval if retry_interval is not None else self.RETRY_INTERVAL_SECONDS
        )
        # 记录每个 session 的重试次数
        self._retry_counts: Dict[str, int] = {}

    def create_session(self, user_id: str, payload: Dict[str, Any] = None) -> LlmSession:
        """创建新的 LLM API 会话"""
        session_id = str(uuid.uuid4())
        now = self._current_time_fn()
        session = LlmSession(
            session_id=session_id,
            user_id=user_id,
            started_at=now,
            timeout_seconds=self._timeout_seconds,
            _current_time_fn=self._current_time_fn,
        )
        self._sessions[session_id] = session
        self._retry_counts[session_id] = 0
        return session

    def get_session(self, session_id: str) -> Optional[LlmSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def check_session_timeout(self, session_id: str) -> Optional[SessionTimeoutResponse]:
        """
        检查会话是否超时。

        如果已超时：
        - 将会话标记为 blocked
        - 返回 HTTP 408 超时响应

        如果未超时：返回 None
        """
        now = self._current_time_fn()
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if not session.is_timed_out(now):
            return None

        # 会话已超时，标记为 blocked
        session.block(now)

        return SessionTimeoutResponse(
            status_code=self.HTTP_STATUS_REQUEST_TIMEOUT,
            error="session_timeout",
            status=SessionStatus.BLOCKED.value,
            session_id=session_id,
            waited_seconds=session.elapsed_seconds(now),
            message=f"会话超时（已持续 {session.elapsed_seconds(now):.1f} 秒，超时阈值 {session.timeout_seconds:.0f} 秒）",
        )

    def handle_client_retry(
        self, session_id: str
    ) -> Optional[SessionTimeoutResponse]:
        """
        处理客户端重试请求。

        如果会话已被 blocked，每次重试都返回 status=blocked。
        当重试次数达到最大值时，返回 retries_exhausted=true。
        """
        now = self._current_time_fn()
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if not session.is_blocked():
            # 会话未被阻塞，返回 None 表示可以正常处理
            return None

        # 增加重试计数
        current_retries = self._retry_counts.get(session_id, 0) + 1
        self._retry_counts[session_id] = current_retries

        retries_exhausted = current_retries >= self._max_retries

        return SessionTimeoutResponse(
            status_code=self.HTTP_STATUS_REQUEST_TIMEOUT,
            error="session_timeout",
            status=SessionStatus.BLOCKED.value,
            session_id=session_id,
            waited_seconds=session.elapsed_seconds(now),
            message=f"会话已被阻塞（第 {current_retries} 次重试）",
            retries_exhausted=retries_exhausted,
        )

    def get_retry_count(self, session_id: str) -> int:
        """获取指定会话的重试次数"""
        return self._retry_counts.get(session_id, 0)

    def reset_retry_count(self, session_id: str) -> None:
        """重置指定会话的重试计数"""
        self._retry_counts[session_id] = 0

    def cleanup_expired_sessions(self, now: datetime = None) -> List[str]:
        """清理已过期的会话，返回被清理的 session_id 列表"""
        t = now or self._current_time_fn()
        expired = [
            sid
            for sid, sess in self._sessions.items()
            if sess.is_timed_out(t) and sess.is_blocked()
        ]
        for sid in expired:
            del self._sessions[sid]
            self._retry_counts.pop(sid, None)
        return expired


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def base_time():
    """固定的基准时间"""
    return datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_clock(base_time):
    """可控制的可调用对象"""
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
    """使用 fake_clock 的会话管理器（超时 30 分钟 = 1800 秒）"""
    return LlmSessionManager(
        timeout_seconds=1800.0,
        current_time_fn=fake_clock,
        max_retries=3,
        retry_interval=5.0,
    )


@pytest.fixture
def active_session(manager, fake_clock):
    """创建一个活跃会话"""
    return manager.create_session(user_id="user-001")


# ====================================================================
# 测试用例：LLM API 需求 - 超时处理（会话 30 分钟）
# ====================================================================

class TestSessionTimeoutAt30Minutes:
    """会话在 30 分钟时终止，返回 HTTP 408 Request Timeout"""

    def test_session_timeout_at_exactly_30_minutes(self, manager, active_session, fake_clock):
        """恰好在 30 分钟（1800 秒）时，会话超时"""
        fake_clock.advance(1800)

        response = manager.check_session_timeout(active_session.session_id)

        assert response is not None
        assert response.status_code == 408

    def test_session_not_timeout_before_30_minutes(self, manager, active_session, fake_clock):
        """在 30 分钟内（1799 秒），会话不应超时"""
        fake_clock.advance(1799)

        response = manager.check_session_timeout(active_session.session_id)

        assert response is None

    def test_session_timeout_at_30_minutes_plus_1(self, manager, active_session, fake_clock):
        """超过 30 分钟 1 秒（1801 秒），会话超时"""
        fake_clock.advance(1801)

        response = manager.check_session_timeout(active_session.session_id)

        assert response is not None
        assert response.status_code == 408

    def test_session_marked_as_blocked_on_timeout(self, manager, active_session, fake_clock):
        """超时后，会话状态被标记为 blocked"""
        fake_clock.advance(1800)

        manager.check_session_timeout(active_session.session_id)
        session = manager.get_session(active_session.session_id)

        assert session is not None
        assert session.status == SessionStatus.BLOCKED.value

    def test_timeout_response_error_is_session_timeout(self, manager, active_session, fake_clock):
        """响应 Body 包含 error=session_timeout"""
        fake_clock.advance(1800)

        response = manager.check_session_timeout(active_session.session_id)

        assert response is not None
        assert response.error == "session_timeout"

    def test_timeout_response_status_is_blocked(self, manager, active_session, fake_clock):
        """响应 Body 包含 status=blocked"""
        fake_clock.advance(1800)

        response = manager.check_session_timeout(active_session.session_id)

        assert response is not None
        assert response.status == "blocked"

    def test_timeout_response_contains_session_id(self, manager, active_session, fake_clock):
        """响应 Body 包含 session_id"""
        fake_clock.advance(1800)

        response = manager.check_session_timeout(active_session.session_id)

        assert response is not None
        assert response.session_id == active_session.session_id

    def test_timeout_response_waited_seconds_is_1800(self, manager, active_session, fake_clock):
        """响应 Body 中 waited_seconds 等于 1800"""
        fake_clock.advance(1800)

        response = manager.check_session_timeout(active_session.session_id)

        assert response is not None
        assert response.waited_seconds == pytest.approx(1800.0)

    def test_http_408_returned_not_503_or_500(self, manager, active_session, fake_clock):
        """超时返回 HTTP 408，不是 503 或 500"""
        fake_clock.advance(1800)

        response = manager.check_session_timeout(active_session.session_id)

        assert response.status_code == 408
        assert response.status_code != 503
        assert response.status_code != 500

    def test_to_dict_contains_all_required_fields(self, manager, active_session, fake_clock):
        """to_dict 包含所有必需字段"""
        fake_clock.advance(1800)

        response = manager.check_session_timeout(active_session.session_id)
        body = response.to_dict()

        assert body["status_code"] == 408
        assert body["error"] == "session_timeout"
        assert body["status"] == "blocked"
        assert "session_id" in body
        assert "waited_seconds" in body
        assert "message" in body
        assert body["retries_exhausted"] is False


class TestClientRetryThreeTimes:
    """客户端重试 3 次（每次间隔 5 秒），每次均返回 status=blocked"""

    def test_first_retry_returns_blocked(self, manager, active_session, fake_clock):
        """第 1 次重试返回 status=blocked"""
        # 先让会话超时并标记为 blocked
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        # 模拟 5 秒后第 1 次重试
        fake_clock.advance(5)
        response = manager.handle_client_retry(active_session.session_id)

        assert response is not None
        assert response.status == "blocked"

    def test_second_retry_returns_blocked(self, manager, active_session, fake_clock):
        """第 2 次重试返回 status=blocked"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        # 第 1 次重试
        fake_clock.advance(5)
        manager.handle_client_retry(active_session.session_id)

        # 第 2 次重试
        fake_clock.advance(5)
        response = manager.handle_client_retry(active_session.session_id)

        assert response is not None
        assert response.status == "blocked"

    def test_third_retry_returns_blocked(self, manager, active_session, fake_clock):
        """第 3 次重试返回 status=blocked"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        # 第 1 次重试
        fake_clock.advance(5)
        manager.handle_client_retry(active_session.session_id)

        # 第 2 次重试
        fake_clock.advance(5)
        manager.handle_client_retry(active_session.session_id)

        # 第 3 次重试
        fake_clock.advance(5)
        response = manager.handle_client_retry(active_session.session_id)

        assert response is not None
        assert response.status == "blocked"

    def test_each_retry_returns_408(self, manager, active_session, fake_clock):
        """每次重试都返回 HTTP 408"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        for i in range(3):
            fake_clock.advance(5)
            response = manager.handle_client_retry(active_session.session_id)
            assert response is not None
            assert response.status_code == 408, f"第 {i + 1} 次重试应返回 408"

    def test_each_retry_error_is_session_timeout(self, manager, active_session, fake_clock):
        """每次重试的 error 都是 session_timeout"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        for i in range(3):
            fake_clock.advance(5)
            response = manager.handle_client_retry(active_session.session_id)
            assert response is not None
            assert response.error == "session_timeout", f"第 {i + 1} 次重试 error 应为 session_timeout"

    def test_retry_count_increments_correctly(self, manager, active_session, fake_clock):
        """重试计数每次递增 1"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        assert manager.get_retry_count(active_session.session_id) == 0

        fake_clock.advance(5)
        manager.handle_client_retry(active_session.session_id)
        assert manager.get_retry_count(active_session.session_id) == 1

        fake_clock.advance(5)
        manager.handle_client_retry(active_session.session_id)
        assert manager.get_retry_count(active_session.session_id) == 2

        fake_clock.advance(5)
        manager.handle_client_retry(active_session.session_id)
        assert manager.get_retry_count(active_session.session_id) == 3


class TestRetriesExhausted:
    """最终返回 retries_exhausted=true"""

    def test_third_retry_returns_retries_exhausted_true(self, manager, active_session, fake_clock):
        """第 3 次重试（最后一次）返回 retries_exhausted=true"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        # 第 1 次重试
        fake_clock.advance(5)
        resp1 = manager.handle_client_retry(active_session.session_id)
        assert resp1.retries_exhausted is False

        # 第 2 次重试
        fake_clock.advance(5)
        resp2 = manager.handle_client_retry(active_session.session_id)
        assert resp2.retries_exhausted is False

        # 第 3 次重试（最后一次）
        fake_clock.advance(5)
        resp3 = manager.handle_client_retry(active_session.session_id)
        assert resp3.retries_exhausted is True

    def test_retries_exhausted_false_for_first_two_retries(self, manager, active_session, fake_clock):
        """前两次重试 retries_exhausted 为 false"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        fake_clock.advance(5)
        resp1 = manager.handle_client_retry(active_session.session_id)
        assert resp1.retries_exhausted is False

        fake_clock.advance(5)
        resp2 = manager.handle_client_retry(active_session.session_id)
        assert resp2.retries_exhausted is False

    def test_retry_beyond_max_returns_retries_exhausted(self, manager, active_session, fake_clock):
        """超出最大重试次数后仍返回 retries_exhausted=true"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        for _ in range(3):
            fake_clock.advance(5)
            manager.handle_client_retry(active_session.session_id)

        # 第 4 次重试（超出限制）
        fake_clock.advance(5)
        resp = manager.handle_client_retry(active_session.session_id)
        assert resp is not None
        assert resp.retries_exhausted is True
        assert resp.status == "blocked"

    def test_to_dict_retries_exhausted_true(self, manager, active_session, fake_clock):
        """to_dict 中 retries_exhausted=true"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        for _ in range(2):
            fake_clock.advance(5)
            manager.handle_client_retry(active_session.session_id)

        fake_clock.advance(5)
        resp = manager.handle_client_retry(active_session.session_id)
        body = resp.to_dict()

        assert body["retries_exhausted"] is True

    def test_to_dict_retries_exhausted_false_for_first_retry(self, manager, active_session, fake_clock):
        """to_dict 中前两次重试 retries_exhausted=false"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        fake_clock.advance(5)
        resp = manager.handle_client_retry(active_session.session_id)
        body = resp.to_dict()

        assert body["retries_exhausted"] is False


class TestFullFlowIntegration:
    """完整流程集成测试"""

    def test_full_flow_create_wait_timeout_retry_exhaust(self, manager, fake_clock):
        """完整流程：创建 → 等待30分钟 → 超时 → 重试3次 → 耗尽"""
        # 1. 创建会话
        session = manager.create_session(user_id="user-integration")
        assert session.status == SessionStatus.ACTIVE.value

        # 2. 等待 30 分钟内，未超时
        fake_clock.advance(1799)
        assert manager.check_session_timeout(session.session_id) is None

        # 3. 到达 30 分钟，触发超时
        fake_clock.advance(1)
        timeout_resp = manager.check_session_timeout(session.session_id)
        assert timeout_resp is not None
        assert timeout_resp.status_code == 408
        assert timeout_resp.error == "session_timeout"
        assert timeout_resp.status == "blocked"

        # 验证会话已被标记为 blocked
        sess = manager.get_session(session.session_id)
        assert sess.status == SessionStatus.BLOCKED.value

        # 4. 客户端重试 3 次
        responses = []
        for i in range(3):
            fake_clock.advance(5)  # 每次间隔 5 秒
            resp = manager.handle_client_retry(session.session_id)
            responses.append(resp)
            assert resp is not None
            assert resp.status_code == 408
            assert resp.error == "session_timeout"
            assert resp.status == "blocked"

        # 5. 前两次重试 retries_exhausted=false
        assert responses[0].retries_exhausted is False
        assert responses[1].retries_exhausted is False

        # 6. 第 3 次重试 retries_exhausted=true
        assert responses[2].retries_exhausted is True

        # 7. 重试计数为 3
        assert manager.get_retry_count(session.session_id) == 3

    def test_active_session_can_retry_normally(self, manager, active_session, fake_clock):
        """未超时的活跃会话不会被 handle_client_retry 阻塞"""
        fake_clock.advance(100)  # 仅过了 100 秒，远未到 30 分钟

        response = manager.handle_client_retry(active_session.session_id)

        assert response is None

    def test_nonexistent_session_returns_none(self, manager):
        """不存在的会话返回 None"""
        assert manager.check_session_timeout("nonexistent") is None
        assert manager.handle_client_retry("nonexistent") is None

    def test_multiple_sessions_timeout_independently(self, manager, fake_clock):
        """多个会话独立超时互不影响"""
        sess_a = manager.create_session(user_id="user-a")
        fake_clock.advance(0.1)
        sess_b = manager.create_session(user_id="user-b")

        # 让 sess_a 超时（1800 秒后）
        fake_clock.advance(1800)
        resp_a = manager.check_session_timeout(sess_a.session_id)
        assert resp_a is not None
        assert resp_a.status_code == 408

        # sess_b 未超时（仅过了约 1799.9 秒）
        resp_b = manager.check_session_timeout(sess_b.session_id)
        assert resp_b is None

        # 让 sess_b 也超时
        fake_clock.advance(1)
        resp_b = manager.check_session_timeout(sess_b.session_id)
        assert resp_b is not None
        assert resp_b.status_code == 408

    def test_cleanup_expired_sessions(self, manager, active_session, fake_clock):
        """清理已过期的 blocked 会话"""
        fake_clock.advance(1800)
        manager.check_session_timeout(active_session.session_id)

        cleaned = manager.cleanup_expired_sessions()

        assert active_session.session_id in cleaned
        assert manager.get_session(active_session.session_id) is None
        assert manager.get_retry_count(active_session.session_id) == 0


class TestLlmSession:
    """LlmSession 领域对象测试"""

    def test_session_initial_status_is_active(self, base_time):
        """新创建的会话状态为 active"""
        session = LlmSession(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        assert session.status == SessionStatus.ACTIVE.value

    def test_session_not_timed_out_before_30_minutes(self, base_time):
        """30 分钟前 is_timed_out 返回 False"""
        session = LlmSession(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        now = base_time + timedelta(seconds=1799)
        assert session.is_timed_out(now) is False

    def test_session_timed_out_at_30_minutes(self, base_time):
        """恰好在 30 分钟时 is_timed_out 返回 True"""
        session = LlmSession(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        now = base_time + timedelta(seconds=1800)
        assert session.is_timed_out(now) is True

    def test_session_timed_out_after_30_minutes(self, base_time):
        """超过 30 分钟 is_timed_out 返回 True"""
        session = LlmSession(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        now = base_time + timedelta(seconds=2000)
        assert session.is_timed_out(now) is True

    def test_session_remaining_seconds_at_15_minutes(self, base_time):
        """15 分钟后剩余时间约 15 分钟（900 秒）"""
        session = LlmSession(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        now = base_time + timedelta(seconds=900)
        assert session.remaining_seconds(now) == pytest.approx(900.0)

    def test_session_block_sets_status_to_blocked(self, base_time):
        """block() 方法将状态设为 blocked"""
        session = LlmSession(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        assert session.is_blocked() is False
        session.block(base_time)
        assert session.is_blocked() is True
        assert session.status == SessionStatus.BLOCKED.value

    def test_elapsed_seconds_at_1800(self, base_time):
        """1800 秒后 elapsed_seconds 为 1800"""
        session = LlmSession(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        now = base_time + timedelta(seconds=1800)
        assert session.elapsed_seconds(now) == pytest.approx(1800.0)


class TestSessionTimeoutResponse:
    """SessionTimeoutResponse 响应体测试"""

    def test_to_dict_contains_status_code_408(self):
        """to_dict 中 status_code 为 408"""
        resp = SessionTimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="blocked",
            session_id="sess-001",
            waited_seconds=1800.0,
            message="会话超时",
        )
        body = resp.to_dict()
        assert body["status_code"] == 408

    def test_to_dict_error_is_session_timeout(self):
        """to_dict 中 error 为 session_timeout"""
        resp = SessionTimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="blocked",
            session_id="sess-001",
            waited_seconds=1800.0,
            message="会话超时",
        )
        body = resp.to_dict()
        assert body["error"] == "session_timeout"

    def test_to_dict_status_is_blocked(self):
        """to_dict 中 status 为 blocked"""
        resp = SessionTimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="blocked",
            session_id="sess-001",
            waited_seconds=1800.0,
            message="会话超时",
        )
        body = resp.to_dict()
        assert body["status"] == "blocked"

    def test_to_dict_retries_exhausted_default_false(self):
        """to_dict 中 retries_exhausted 默认为 false"""
        resp = SessionTimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="blocked",
            session_id="sess-001",
            waited_seconds=1800.0,
            message="会话超时",
        )
        body = resp.to_dict()
        assert body["retries_exhausted"] is False

    def test_to_dict_retries_exhausted_true_when_set(self):
        """to_dict 中 retries_exhausted=true 当设置为 true"""
        resp = SessionTimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="blocked",
            session_id="sess-001",
            waited_seconds=1800.0,
            message="会话超时",
            retries_exhausted=True,
        )
        body = resp.to_dict()
        assert body["retries_exhausted"] is True

    def test_to_dict_waited_seconds_rounded_to_two_decimals(self):
        """to_dict 中 waited_seconds 保留两位小数"""
        resp = SessionTimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="blocked",
            session_id="sess-001",
            waited_seconds=1800.12345,
            message="会话超时",
        )
        body = resp.to_dict()
        assert body["waited_seconds"] == 1800.12


class TestSessionTimeoutError:
    """SessionTimeoutError 异常测试"""

    def test_exception_contains_session_id(self):
        """异常包含 session_id"""
        err = SessionTimeoutError(session_id="sess-001", waited_seconds=1800.0)
        assert err.session_id == "sess-001"
        assert err.waited_seconds == 1800.0
        assert "sess-001" in str(err)

    def test_exception_message_includes_waited_seconds(self):
        """异常消息包含等待秒数"""
        err = SessionTimeoutError(session_id="sess-001", waited_seconds=1800.0)
        assert "1800.0" in err.message

    def test_exception_can_be_raised_and_caught(self):
        """异常可正常抛掷和捕获"""
        with pytest.raises(SessionTimeoutError) as exc_info:
            raise SessionTimeoutError(session_id="sess-001", waited_seconds=1800.0)
        assert exc_info.value.session_id == "sess-001"
        assert exc_info.value.waited_seconds == 1800.0

    def test_custom_exception_message(self):
        """可使用自定义消息"""
        err = SessionTimeoutError(
            session_id="sess-001",
            waited_seconds=1800.0,
            message="自定义超时消息",
        )
        assert err.message == "自定义超时消息"


class TestCustomTimeout:
    """自定义超时时间测试"""

    def test_custom_timeout_5_minutes(self, base_time):
        """自定义超时 5 分钟（300 秒），301 秒后超时"""
        clock = type("FakeClock", (), {"_time": base_time})()
        def clock_fn():
            return clock._time

        mgr = LlmSessionManager(
            timeout_seconds=300.0,
            current_time_fn=clock_fn,
        )
        session = mgr.create_session(user_id="user-custom")

        clock._time = base_time + timedelta(seconds=299)
        assert mgr.check_session_timeout(session.session_id) is None

        clock._time = base_time + timedelta(seconds=300)
        resp = mgr.check_session_timeout(session.session_id)
        assert resp is not None
        assert resp.status_code == 408

    def test_custom_max_retries_5(self, base_time):
        """自定义最大重试次数为 5，第 5 次才返回 retries_exhausted"""
        clock = type("FakeClock", (), {"_time": base_time})()
        def clock_fn():
            return clock._time

        mgr = LlmSessionManager(
            timeout_seconds=1800.0,
            current_time_fn=clock_fn,
            max_retries=5,
        )
        session = mgr.create_session(user_id="user-custom")

        clock._time = base_time + timedelta(seconds=1800)
        mgr.check_session_timeout(session.session_id)

        for i in range(4):
            clock._time += timedelta(seconds=5)
            resp = mgr.handle_client_retry(session.session_id)
            assert resp.retries_exhausted is False, f"第 {i + 1} 次重试应未耗尽"

        clock._time += timedelta(seconds=5)
        resp = mgr.handle_client_retry(session.session_id)
        assert resp.retries_exhausted is True, "第 5 次重试应耗尽"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
