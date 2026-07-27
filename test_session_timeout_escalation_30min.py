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
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


@dataclass
class Session:
    """会话领域模型"""
    session_id: str
    user_id: str
    started_at: datetime
    timeout_minutes: float = 30.0
    status: str = SessionStatus.ACTIVE.value
    _current_time_fn: callable = field(
        default_factory=lambda: _default_current_time, repr=False
    )

    @property
    def timeout_seconds(self) -> float:
        return self.timeout_minutes * 60.0

    def elapsed_seconds(self, now: datetime = None) -> float:
        t = now or self._current_time_fn()
        return (t - self.started_at).total_seconds()

    def elapsed_minutes(self, now: datetime = None) -> float:
        return self.elapsed_seconds(now) / 60.0

    def is_timed_out(self, now: datetime = None) -> bool:
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def remaining_seconds(self, now: datetime = None) -> float:
        return max(0.0, self.timeout_seconds - self.elapsed_seconds(now))

    def mark_timeout(self, now: datetime = None):
        """将会话标记为 timeout"""
        self.status = SessionStatus.TIMEOUT.value

    def is_timeout(self) -> bool:
        return self.status == SessionStatus.TIMEOUT.value

    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE.value


@dataclass
class TimeoutResponse:
    """超时响应体"""
    status_code: int
    error: str
    status: str
    session_id: str
    duration_minutes: float
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "error": self.error,
            "status": self.status,
            "session_id": self.session_id,
            "duration_minutes": self.duration_minutes,
            "message": self.message,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class SessionTimeoutError(Exception):
    def __init__(self, session_id: str, duration_minutes: float):
        self.session_id = session_id
        self.duration_minutes = duration_minutes
        self.message = f"会话 {session_id} 超时，已持续 {duration_minutes:.1f} 分钟"
        super().__init__(self.message)


class SessionManager:
    """会话管理器 - 规定时限与超时升级机制"""

    DEFAULT_TIMEOUT_MINUTES = 30.0
    HTTP_408 = 408

    def __init__(
        self,
        timeout_minutes: float = None,
        current_time_fn: callable = None,
    ):
        self._sessions: Dict[str, Session] = {}
        self._timeout_minutes = timeout_minutes or self.DEFAULT_TIMEOUT_MINUTES
        self._current_time_fn = current_time_fn or _default_current_time

    def create_session(self, user_id: str) -> Session:
        session_id = str(uuid.uuid4())
        now = self._current_time_fn()
        session = Session(
            session_id=session_id,
            user_id=user_id,
            started_at=now,
            timeout_minutes=self._timeout_minutes,
            _current_time_fn=self._current_time_fn,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def check_and_escalate(self, session_id: str) -> Optional[TimeoutResponse]:
        """
        检查会话是否超时。

        验收标准：
        - 会话在第30分钟时状态从active切换为timeout
        - 返回HTTP408，响应Body包含error=session_timeout和duration_minutes=30
        """
        now = self._current_time_fn()
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if not session.is_timed_out(now):
            return None

        # 超时：标记状态为 timeout
        original_status = session.status
        session.mark_timeout(now)

        duration = session.elapsed_minutes(now)

        return TimeoutResponse(
            status_code=self.HTTP_408,
            error="session_timeout",
            status=SessionStatus.TIMEOUT.value,
            session_id=session_id,
            duration_minutes=duration,
            message=f"会话超时（已持续 {duration:.1f} 分钟，超时阈值 {session.timeout_minutes:.0f} 分钟）",
        )


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def base_time():
    return datetime(2025, 7, 1, 10, 0, 0, tzinfo=timezone.utc)


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
    return SessionManager(
        timeout_minutes=30.0,
        current_time_fn=fake_clock,
    )


@pytest.fixture
def active_session(manager, fake_clock):
    return manager.create_session(user_id="user-001")


# ====================================================================
# 测试：规定时限与超时升级机制 - 会话>30分钟触发超时
# ====================================================================

class TestSessionTimeoutAt30Minutes:
    """会话在第30分钟时状态从active切换为timeout"""

    def test_session_status_changes_from_active_to_timeout_at_30_minutes(
        self, manager, active_session, fake_clock
    ):
        """验收标准1：会话在第30分钟时状态从active切换为timeout"""
        # 超时前状态为 active
        assert active_session.status == SessionStatus.ACTIVE.value
        assert active_session.is_active() is True

        # 推进到恰好 30 分钟
        fake_clock.advance(30 * 60)

        # 触发超时检查
        response = manager.check_and_escalate(active_session.session_id)

        # 状态已从 active 切换为 timeout
        assert response is not None
        session = manager.get_session(active_session.session_id)
        assert session is not None
        assert session.status == SessionStatus.TIMEOUT.value
        assert session.is_timeout() is True
        assert session.is_active() is False

    def test_session_status_is_active_before_30_minutes(self, manager, active_session, fake_clock):
        """30 分钟内状态保持 active"""
        fake_clock.advance(29 * 60 + 59)  # 29 分 59 秒

        response = manager.check_and_escalate(active_session.session_id)

        assert response is None
        assert active_session.status == SessionStatus.ACTIVE.value
        assert active_session.is_active() is True

    def test_session_status_switches_at_exact_30_minute_boundary(self, manager, active_session, fake_clock):
        """恰好在 30 分钟边界（1800 秒）触发状态切换"""
        fake_clock.advance(29 * 60 + 59)  # 29 分 59 秒，未超时
        assert manager.check_and_escalate(active_session.session_id) is None
        assert active_session.status == SessionStatus.ACTIVE.value

        fake_clock.advance(1)  # 推进到 30 分钟整
        response = manager.check_and_escalate(active_session.session_id)

        assert response is not None
        assert active_session.status == SessionStatus.TIMEOUT.value

    def test_session_status_stays_timeout_after_30_minutes(self, manager, active_session, fake_clock):
        """超过 30 分钟后状态保持 timeout"""
        fake_clock.advance(30 * 60)
        manager.check_and_escalate(active_session.session_id)
        assert active_session.status == SessionStatus.TIMEOUT.value

        # 再推进 10 分钟，状态仍然为 timeout
        fake_clock.advance(10 * 60)
        session = manager.get_session(active_session.session_id)
        assert session.status == SessionStatus.TIMEOUT.value


class TestHTTP408Response:
    """返回 HTTP408，响应 Body 包含 error=session_timeout 和 duration_minutes=30"""

    def test_response_returns_http_408(self, manager, active_session, fake_clock):
        """验收标准2：返回 HTTP 408"""
        fake_clock.advance(30 * 60)
        response = manager.check_and_escalate(active_session.session_id)

        assert response is not None
        assert response.status_code == 408

    def test_response_body_contains_error_session_timeout(self, manager, active_session, fake_clock):
        """验收标准2：响应 Body 包含 error=session_timeout"""
        fake_clock.advance(30 * 60)
        response = manager.check_and_escalate(active_session.session_id)

        assert response is not None
        assert response.error == "session_timeout"

    def test_response_body_contains_duration_minutes_30(self, manager, active_session, fake_clock):
        """验收标准2：响应 Body 包含 duration_minutes=30"""
        fake_clock.advance(30 * 60)
        response = manager.check_and_escalate(active_session.session_id)

        assert response is not None
        assert response.duration_minutes == pytest.approx(30.0)

    def test_response_to_dict_contains_all_required_fields(self, manager, active_session, fake_clock):
        """响应 to_dict 包含 error 和 duration_minutes"""
        fake_clock.advance(30 * 60)
        response = manager.check_and_escalate(active_session.session_id)

        body = response.to_dict()
        assert body["status_code"] == 408
        assert body["error"] == "session_timeout"
        assert body["duration_minutes"] == pytest.approx(30.0)
        assert body["status"] == "timeout"
        assert "session_id" in body
        assert "message" in body

    def test_response_to_json_contains_error_and_duration(self, manager, active_session, fake_clock):
        """响应 to_json 序列化包含 error=session_timeout 和 duration_minutes=30"""
        fake_clock.advance(30 * 60)
        response = manager.check_and_escalate(active_session.session_id)

        json_str = response.to_json()
        parsed = json.loads(json_str)
        assert parsed["error"] == "session_timeout"
        assert parsed["duration_minutes"] == pytest.approx(30.0)
        assert parsed["status_code"] == 408

    def test_response_is_none_before_30_minutes(self, manager, active_session, fake_clock):
        """30 分钟内不返回超时响应"""
        fake_clock.advance(29 * 60 + 59)
        response = manager.check_and_escalate(active_session.session_id)

        assert response is None

    def test_response_duration_minutes_increases_after_30_minutes(self, manager, active_session, fake_clock):
        """超过 30 分钟后 duration_minutes 随之增加"""
        # 30 分钟
        fake_clock.advance(30 * 60)
        resp1 = manager.check_and_escalate(active_session.session_id)
        assert resp1.duration_minutes == pytest.approx(30.0)

        # 35 分钟（再次检查，虽然已标记 timeout）
        fake_clock.advance(5 * 60)
        session = manager.get_session(active_session.session_id)
        assert session.elapsed_minutes() == pytest.approx(35.0)


class TestTimeoutResponseStructure:
    """TimeoutResponse 响应体结构验证"""

    def test_to_dict_has_status_code_field(self):
        resp = TimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="timeout",
            session_id="sess-001",
            duration_minutes=30.0,
            message="会话超时",
        )
        body = resp.to_dict()
        assert "status_code" in body
        assert body["status_code"] == 408

    def test_to_dict_has_error_field(self):
        resp = TimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="timeout",
            session_id="sess-001",
            duration_minutes=30.0,
            message="会话超时",
        )
        body = resp.to_dict()
        assert "error" in body
        assert body["error"] == "session_timeout"

    def test_to_dict_has_duration_minutes_field(self):
        resp = TimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="timeout",
            session_id="sess-001",
            duration_minutes=30.0,
            message="会话超时",
        )
        body = resp.to_dict()
        assert "duration_minutes" in body
        assert body["duration_minutes"] == 30.0

    def test_to_json_is_valid_json(self):
        resp = TimeoutResponse(
            status_code=408,
            error="session_timeout",
            status="timeout",
            session_id="sess-001",
            duration_minutes=30.0,
            message="会话超时",
        )
        json_str = resp.to_json()
        parsed = json.loads(json_str)
        assert parsed["status_code"] == 408
        assert parsed["error"] == "session_timeout"
        assert parsed["duration_minutes"] == 30.0


class TestSessionTimeoutError:
    """SessionTimeoutError 异常验证"""

    def test_exception_contains_session_id_and_duration(self):
        err = SessionTimeoutError(session_id="sess-001", duration_minutes=30.0)
        assert err.session_id == "sess-001"
        assert err.duration_minutes == 30.0
        assert "sess-001" in str(err)
        assert "30.0" in err.message

    def test_exception_can_be_raised_and_caught(self):
        with pytest.raises(SessionTimeoutError) as exc_info:
            raise SessionTimeoutError(session_id="sess-001", duration_minutes=30.0)
        assert exc_info.value.session_id == "sess-001"
        assert exc_info.value.duration_minutes == 30.0


class TestMultipleSessions:
    """多会话场景：各会话独立超时"""

    def test_each_session_times_out_independently(self, manager, fake_clock):
        """会话 A 先创建，B 稍后创建，各自独立超时"""
        sess_a = manager.create_session(user_id="user-a")
        fake_clock.advance(2)  # A 比 B 早 2 秒
        sess_b = manager.create_session(user_id="user-b")

        # 推进 1799 秒：A 已 1801 秒超时，B 仅 1799 秒未超时
        fake_clock.advance(1799)
        resp_a = manager.check_and_escalate(sess_a.session_id)
        assert resp_a is not None
        assert resp_a.status_code == 408
        assert resp_a.error == "session_timeout"
        assert manager.get_session(sess_a.session_id).status == SessionStatus.TIMEOUT.value

        resp_b = manager.check_and_escalate(sess_b.session_id)
        assert resp_b is None
        assert manager.get_session(sess_b.session_id).status == SessionStatus.ACTIVE.value

        # 再推进 1 秒：B 也达到 1800 秒超时
        fake_clock.advance(1)
        resp_b = manager.check_and_escalate(sess_b.session_id)
        assert resp_b is not None
        assert resp_b.status_code == 408
        assert resp_b.duration_minutes == pytest.approx(30.0)


class TestFullEscalationFlow:
    """完整流程：创建 → 活跃30分钟 → 超时升级 → 返回408"""

    def test_full_flow_from_creation_to_timeout_escalation(self, manager, fake_clock):
        """
        完整流程：
        1. 创建会话，状态为 active
        2. 29 分 59 秒内检查，无超时
        3. 第 30 分钟检查，触发超时升级
        4. 状态从 active 切换为 timeout
        5. 返回 HTTP 408
        6. 响应 Body 包含 error=session_timeout 和 duration_minutes=30
        """
        # 1. 创建会话
        session = manager.create_session(user_id="user-flow")
        assert session.status == SessionStatus.ACTIVE.value
        assert session.is_active() is True

        # 2. 29 分 59 秒，未超时
        fake_clock.advance(29 * 60 + 59)
        resp_early = manager.check_and_escalate(session.session_id)
        assert resp_early is None
        assert session.status == SessionStatus.ACTIVE.value

        # 3. 第 30 分钟整，触发超时
        fake_clock.advance(1)
        response = manager.check_and_escalate(session.session_id)
        assert response is not None

        # 4. 状态从 active 切换为 timeout
        assert session.status == SessionStatus.TIMEOUT.value
        assert session.is_timeout() is True
        assert session.is_active() is False

        # 5. 返回 HTTP 408
        assert response.status_code == 408

        # 6. 响应 Body 包含 error=session_timeout 和 duration_minutes=30
        assert response.error == "session_timeout"
        assert response.duration_minutes == pytest.approx(30.0)

        # 7. 验证完整响应结构
        body = response.to_dict()
        assert body["status_code"] == 408
        assert body["error"] == "session_timeout"
        assert body["status"] == "timeout"
        assert body["duration_minutes"] == pytest.approx(30.0)
        assert body["session_id"] == session.session_id
        assert "message" in body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
