import uuid
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

import pytest


# ====================================================================
# 被测试的领域模型
# ====================================================================


class StreamStatus(str, Enum):
    PENDING = "pending"
    STREAMING = "streaming"
    TIMEOUT = "timeout"
    COMPLETED = "completed"
    CLOSED = "closed"


class StreamErrorType(str, Enum):
    FIRST_TOKEN_TIMEOUT = "first_token_timeout"


@dataclass
class StreamConnection:
    connection_id: str
    user_id: str
    model: str
    started_at: datetime
    status: str = StreamStatus.PENDING.value
    first_token_at: Optional[datetime] = None
    timeout_seconds: float = 30.0
    error: Optional[str] = None
    _clock: Callable[[], datetime] = None

    def __post_init__(self):
        if self._clock is None:
            self._clock = lambda: datetime.now(timezone.utc)

    @property
    def elapsed(self) -> float:
        return (self._clock() - self.started_at).total_seconds()

    def is_first_token_timed_out(self) -> bool:
        return self.first_token_at is None and self.elapsed >= self.timeout_seconds

    def on_first_token(self, token: str):
        self.first_token_at = self._clock()
        self.status = StreamStatus.STREAMING.value

    def on_timeout(self):
        self.status = StreamStatus.TIMEOUT.value
        self.error = StreamErrorType.FIRST_TOKEN_TIMEOUT.value

    def close(self):
        self.status = StreamStatus.CLOSED.value


@dataclass
class StreamErrorResponse:
    status_code: int = 504
    error: str = "first_token_timeout"
    wait_seconds: float = 30.0
    connection_id: str = ""
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "error": self.error,
            "wait_seconds": self.wait_seconds,
            "connection_id": self.connection_id,
            "message": self.message,
        }


class StreamTimeoutError(Exception):
    def __init__(self, connection_id: str, waited: float):
        self.connection_id = connection_id
        self.waited = waited
        super().__init__(f"首token超时: {connection_id}, 等待 {waited}s")


class StreamGateway:
    HTTP_504 = 504

    def __init__(self, timeout_seconds: float = 30.0, clock: Callable[[], datetime] = None):
        self.timeout_seconds = timeout_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._active: Dict[str, StreamConnection] = {}
        self._closed: List[StreamConnection] = []

    def create_stream(self, user_id: str, model: str) -> StreamConnection:
        conn = StreamConnection(
            connection_id=str(uuid.uuid4()),
            user_id=user_id,
            model=model,
            started_at=self._clock(),
            timeout_seconds=self.timeout_seconds,
            _clock=self._clock,
        )
        self._active[conn.connection_id] = conn
        return conn

    def check_timeout(self, connection_id: str) -> Optional[StreamErrorResponse]:
        conn = self._active.get(connection_id)
        if conn is None:
            return None
        if conn.first_token_at is not None:
            return None
        if conn.is_first_token_timed_out():
            waited = conn.elapsed
            conn.on_timeout()
            self._closed.append(conn)
            del self._active[connection_id]
            return StreamErrorResponse(
                status_code=self.HTTP_504,
                error=StreamErrorType.FIRST_TOKEN_TIMEOUT.value,
                wait_seconds=waited,
                connection_id=connection_id,
                message=f"首token超时，已等待 {waited:.0f} 秒",
            )
        return None

    def feed_token(self, connection_id: str, token: str) -> Optional[StreamErrorResponse]:
        conn = self._active.get(connection_id)
        if conn is None:
            return None
        timeout_resp = self.check_timeout(connection_id)
        if timeout_resp is not None:
            return timeout_resp
        if conn.first_token_at is None:
            conn.on_first_token(token)
        return None

    @property
    def active_count(self) -> int:
        return len(self._active)


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def t0():
    return datetime(2025, 7, 20, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def clock(t0):
    class _:
        def __init__(self):
            self.now = t0
        def __call__(self):
            return self.now
        def tick(self, seconds: float):
            self.now += timedelta(seconds=seconds)
    return _()


@pytest.fixture
def gw(clock):
    return StreamGateway(timeout_seconds=30.0, clock=clock)


# ====================================================================
# 测试用例
# ====================================================================

class TestStreamFirstTokenTimeout:

    def test_status_transitions_to_timeout_at_30s(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        assert conn.status == "pending"
        clock.tick(30)
        gw.check_timeout(conn.connection_id)
        closed = gw._closed
        assert len(closed) == 1
        assert closed[0].status == StreamStatus.TIMEOUT.value
        assert closed[0].error == "first_token_timeout"

    def test_returns_http_504_on_timeout(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(30)
        resp = gw.check_timeout(conn.connection_id)
        assert resp.status_code == 504

    def test_response_body_contains_error_first_token_timeout(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(30)
        resp = gw.check_timeout(conn.connection_id)
        assert resp.error == "first_token_timeout"

    def test_response_body_contains_wait_seconds_30(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(30)
        resp = gw.check_timeout(conn.connection_id)
        assert resp.wait_seconds == 30.0

    def test_response_to_dict_has_error_and_wait_seconds(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(30)
        resp = gw.check_timeout(conn.connection_id)
        body = resp.to_dict()
        assert body["error"] == "first_token_timeout"
        assert body["wait_seconds"] == 30.0

    def test_active_connection_removed_after_timeout(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        assert gw.active_count == 1
        clock.tick(30)
        gw.check_timeout(conn.connection_id)
        assert gw.active_count == 0

    def test_no_timeout_before_30s(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(29.9)
        resp = gw.check_timeout(conn.connection_id)
        assert resp is None
        assert conn.status == "pending"

    def test_no_timeout_after_first_token_arrives(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(10)
        gw.feed_token(conn.connection_id, "hello")
        assert conn.status == "streaming"
        clock.tick(25)
        resp = gw.check_timeout(conn.connection_id)
        assert resp is None

    def test_feed_token_after_timeout_returns_504(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(31)
        resp = gw.feed_token(conn.connection_id, "hello")
        assert resp is not None
        assert resp.status_code == 504
        assert resp.error == "first_token_timeout"

    def test_streaming_connection_independent_of_timeout_connection(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(10)
        gw.feed_token(conn.connection_id, "hello")
        assert conn.status == "streaming"
        conn2 = gw.create_stream("user2", "claude")
        clock.tick(35)
        resp = gw.check_timeout(conn2.connection_id)
        assert resp is not None
        assert resp.status_code == 504
        assert conn.status == "streaming"

    def test_timeout_at_30s_exactly(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(30)
        resp = gw.check_timeout(conn.connection_id)
        assert resp is not None
        assert resp.wait_seconds == 30.0

    def test_timeout_at_31s(self, gw, clock):
        conn = gw.create_stream("user1", "gpt-4")
        clock.tick(31)
        resp = gw.check_timeout(conn.connection_id)
        assert resp is not None
        assert resp.wait_seconds == 31.0

    def test_unknown_connection_id_returns_none(self, gw):
        resp = gw.check_timeout("nonexistent")
        assert resp is None

    def test_stream_timeout_exception_fields(self):
        err = StreamTimeoutError("c1", 30.5)
        assert err.connection_id == "c1"
        assert err.waited == 30.5

    def test_stream_timeout_exception_can_be_raised(self):
        with pytest.raises(StreamTimeoutError) as info:
            raise StreamTimeoutError("c1", 30.0)
        assert info.value.connection_id == "c1"
        assert info.value.waited == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
