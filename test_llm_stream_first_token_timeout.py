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


class StreamStatus(str, Enum):
    WAITING_FIRST_TOKEN = "waiting_first_token"
    STREAMING = "streaming"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    CLOSED = "closed"


class StreamErrorCode(str, Enum):
    STREAM_FIRST_TOKEN_TIMEOUT = "stream_first_token_timeout"
    STREAM_SERVER_ERROR = "stream_server_error"
    RETRIES_EXHAUSTED = "retries_exhausted"


@dataclass
class StreamChunk:
    """流式响应片段"""
    token: str
    chunk_index: int
    timestamp: datetime


@dataclass
class StreamConnection:
    """流式连接"""
    connection_id: str
    user_id: str
    model: str
    started_at: datetime
    first_token_at: Optional[datetime] = None
    status: str = StreamStatus.WAITING_FIRST_TOKEN.value
    chunks: List[StreamChunk] = field(default_factory=list)
    timeout_seconds: float = 30.0
    error: Optional[str] = None
    _current_time_fn: Callable[[], datetime] = field(
        default=_default_current_time, repr=False
    )

    def elapsed_seconds(self, now: datetime = None) -> float:
        t = now or self._current_time_fn()
        return (t - self.started_at).total_seconds()

    def is_first_token_timed_out(self, now: datetime = None) -> bool:
        if self.first_token_at is not None:
            return False
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def receive_first_token(self, token: str, now: datetime = None):
        t = now or self._current_time_fn()
        self.first_token_at = t
        self.status = StreamStatus.STREAMING.value
        self.chunks.append(StreamChunk(token=token, chunk_index=0, timestamp=t))

    def receive_chunk(self, token: str, now: datetime = None):
        if self.status != StreamStatus.STREAMING.value:
            return
        t = now or self._current_time_fn()
        idx = len(self.chunks)
        self.chunks.append(StreamChunk(token=token, chunk_index=idx, timestamp=t))

    def mark_timed_out(self, now: datetime = None):
        self.status = StreamStatus.TIMED_OUT.value
        self.error = StreamErrorCode.STREAM_FIRST_TOKEN_TIMEOUT.value

    def close(self):
        self.status = StreamStatus.CLOSED.value


@dataclass
class StreamResponse:
    """流式响应"""
    status_code: int
    connection_id: str
    error: Optional[str] = None
    timeout_seconds: Optional[float] = None
    tokens_received: int = 0
    waited_seconds: float = 0.0
    retries_attempts: int = 0
    retries_max: int = 0
    retries_exhausted: bool = False
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "connection_id": self.connection_id,
            "error": self.error,
            "timeout_seconds": self.timeout_seconds,
            "tokens_received": self.tokens_received,
            "waited_seconds": round(self.waited_seconds, 2),
            "retries_attempts": self.retries_attempts,
            "retries_max": self.retries_max,
            "retries_exhausted": self.retries_exhausted,
            "message": self.message,
        }


class StreamFirstTokenTimeoutError(Exception):
    """流式首token超时异常"""

    def __init__(self, connection_id: str, waited_seconds: float, timeout_seconds: float = 30.0):
        self.connection_id = connection_id
        self.waited_seconds = waited_seconds
        self.timeout_seconds = timeout_seconds
        self.message = f"流式连接 {connection_id} 首token超时（等待 {waited_seconds:.1f} 秒，超时阈值 {timeout_seconds:.0f} 秒）"
        super().__init__(self.message)


class StreamClient:
    """流式客户端：管理连接、超时检查、重试逻辑"""

    HTTP_STATUS_GATEWAY_TIMEOUT = 504
    DEFAULT_FIRST_TOKEN_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 2

    def __init__(
        self,
        timeout_seconds: float = None,
        max_retries: int = None,
        current_time_fn: Callable[[], datetime] = None,
        llm_first_token_delay: float = None,
    ):
        self._timeout_seconds = timeout_seconds if timeout_seconds is not None else self.DEFAULT_FIRST_TOKEN_TIMEOUT
        self._max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self._current_time_fn = current_time_fn or _default_current_time
        self._connections: Dict[str, StreamConnection] = {}
        self._closed_connections: List[StreamConnection] = []
        self._llm_first_token_delay = llm_first_token_delay  # None = instant response

    def connect(self, user_id: str, model: str) -> StreamConnection:
        now = self._current_time_fn()
        conn_id = str(uuid.uuid4())
        conn = StreamConnection(
            connection_id=conn_id,
            user_id=user_id,
            model=model,
            started_at=now,
            timeout_seconds=self._timeout_seconds,
            _current_time_fn=self._current_time_fn,
        )
        self._connections[conn_id] = conn
        return conn

    def check_first_token_timeout(self, connection_id: str) -> Optional[StreamResponse]:
        now = self._current_time_fn()
        conn = self._connections.get(connection_id)
        if conn is None:
            return StreamResponse(
                status_code=404,
                connection_id=connection_id,
                message=f"连接 {connection_id} 不存在",
            )
        if conn.first_token_at is not None:
            return None
        waited = conn.elapsed_seconds(now)
        if waited >= conn.timeout_seconds:
            conn.mark_timed_out(now)
            self._closed_connections.append(conn)
            conn.close()
            del self._connections[connection_id]
            return StreamResponse(
                status_code=self.HTTP_STATUS_GATEWAY_TIMEOUT,
                connection_id=connection_id,
                error=StreamErrorCode.STREAM_FIRST_TOKEN_TIMEOUT.value,
                timeout_seconds=conn.timeout_seconds,
                waited_seconds=waited,
                message=f"流式首token超时（等待 {waited:.1f} 秒，阈值 {conn.timeout_seconds:.0f} 秒）",
            )
        return None

    def receive_token(self, connection_id: str, token: str) -> Optional[StreamResponse]:
        now = self._current_time_fn()
        conn = self._connections.get(connection_id)
        if conn is None:
            return StreamResponse(
                status_code=404,
                connection_id=connection_id,
                message=f"连接 {connection_id} 不存在",
            )
        if conn.first_token_at is None:
            waited = conn.elapsed_seconds(now)
            if waited >= conn.timeout_seconds:
                conn.mark_timed_out(now)
                self._closed_connections.append(conn)
                conn.close()
                del self._connections[connection_id]
                return StreamResponse(
                    status_code=self.HTTP_STATUS_GATEWAY_TIMEOUT,
                    connection_id=connection_id,
                    error=StreamErrorCode.STREAM_FIRST_TOKEN_TIMEOUT.value,
                    timeout_seconds=conn.timeout_seconds,
                    waited_seconds=waited,
                    message=f"流式首token超时（等待 {waited:.1f} 秒，阈值 {conn.timeout_seconds:.0f} 秒）",
                )
            conn.receive_first_token(token, now)
        else:
            conn.receive_chunk(token, now)
        return None

    def retry_with_backoff(
        self,
        user_id: str,
        model: str,
        max_retries: int = None,
    ) -> StreamResponse:
        retries = max_retries if max_retries is not None else self._max_retries
        delay = self._llm_first_token_delay
        last_response: Optional[StreamResponse] = None
        for attempt in range(retries + 1):
            conn = self.connect(user_id, model)
            if delay is not None and delay >= conn.timeout_seconds:
                waited = conn.timeout_seconds
                conn.mark_timed_out()
                self._closed_connections.append(conn)
                conn.close()
                self._connections.pop(conn.connection_id, None)
                last_response = StreamResponse(
                    status_code=self.HTTP_STATUS_GATEWAY_TIMEOUT,
                    connection_id=conn.connection_id,
                    error=StreamErrorCode.STREAM_FIRST_TOKEN_TIMEOUT.value,
                    timeout_seconds=conn.timeout_seconds,
                    waited_seconds=waited,
                    message=f"流式首token超时（等待 {waited:.1f} 秒，阈值 {conn.timeout_seconds:.0f} 秒）",
                )
                if attempt < retries:
                    continue
            else:
                if delay is not None:
                    conn.receive_first_token("token", conn.started_at + timedelta(seconds=delay))
                return StreamResponse(
                    status_code=200,
                    connection_id=conn.connection_id,
                    tokens_received=0,
                    retries_attempts=attempt,
                    retries_max=retries,
                    retries_exhausted=False,
                    message="流式连接成功建立",
                )
        if last_response is not None:
            last_response.retries_attempts = retries + 1
            last_response.retries_max = retries
            last_response.retries_exhausted = True
            last_response.error = StreamErrorCode.RETRIES_EXHAUSTED.value
            last_response.message = (
                f"重试{retries}次后仍超时，连接已终止（等待 {last_response.waited_seconds:.1f} 秒）"
            )
        return last_response

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    @property
    def closed_connections(self) -> List[StreamConnection]:
        return list(self._closed_connections)


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
    return StreamClient(
        timeout_seconds=30.0,
        max_retries=2,
        current_time_fn=fake_clock,
        llm_first_token_delay=None,
    )


@pytest.fixture
def client_always_timeout(fake_clock):
    """LLM 永远超时：first_token_delay=60s > timeout=30s"""
    return StreamClient(
        timeout_seconds=30.0,
        max_retries=2,
        current_time_fn=fake_clock,
        llm_first_token_delay=60.0,
    )


@pytest.fixture
def client_short_timeout(fake_clock):
    return StreamClient(
        timeout_seconds=5.0,
        max_retries=2,
        current_time_fn=fake_clock,
        llm_first_token_delay=None,
    )


@pytest.fixture
def client_no_retry(fake_clock):
    return StreamClient(
        timeout_seconds=30.0,
        max_retries=0,
        current_time_fn=fake_clock,
        llm_first_token_delay=None,
    )


# ====================================================================
# 测试：流式首token超时处理
# ====================================================================

class TestStreamFirstTokenTimeout:
    """验证流式响应首token超过30秒时正确终止并返回超时错误"""

    def test_terminate_stream_at_30_seconds(self, client, fake_clock):
        """系统在30秒时终止流式连接"""
        conn = client.connect("user-001", "gpt-4")
        assert client.active_connections == 1

        fake_clock.advance(30)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert client.active_connections == 0

    def test_return_http_504_on_timeout(self, client, fake_clock):
        """返回HTTP 504 Gateway Timeout"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.status_code == 504

    def test_response_error_is_stream_first_token_timeout(self, client, fake_clock):
        """响应Body包含 error=stream_first_token_timeout"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.error == "stream_first_token_timeout"

    def test_response_timeout_seconds_is_30(self, client, fake_clock):
        """响应Body包含 timeout_seconds=30"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.timeout_seconds == 30.0

    def test_connection_status_is_closed_after_timeout(self, client, fake_clock):
        """超时后连接状态为 closed"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)
        client.check_first_token_timeout(conn.connection_id)

        closed = client.closed_connections
        assert len(closed) == 1
        assert closed[0].status == "closed"
        assert closed[0].error == "stream_first_token_timeout"

    def test_connection_not_in_active_after_timeout(self, client, fake_clock):
        """超时后连接从活跃列表中移除"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)
        client.check_first_token_timeout(conn.connection_id)

        assert client.active_connections == 0
        assert conn.connection_id not in client._connections

    def test_waited_seconds_gte_30(self, client, fake_clock):
        """响应的 waited_seconds >= 30"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.waited_seconds >= 30.0

    def test_response_to_dict_contains_all_fields(self, client, fake_clock):
        """to_dict 包含所有必要字段"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)

        response = client.check_first_token_timeout(conn.connection_id)
        body = response.to_dict()

        assert body["status_code"] == 504
        assert body["error"] == "stream_first_token_timeout"
        assert body["timeout_seconds"] == 30.0
        assert "connection_id" in body
        assert "waited_seconds" in body

    # ── 边界：30秒前不应超时 ──

    def test_29_seconds_not_timed_out(self, client, fake_clock):
        """29 秒时不应超时"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(29)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is None

    def test_29_9_seconds_not_timed_out(self, client, fake_clock):
        """29.9 秒时不应超时"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(29.9)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is None

    def test_exactly_30_seconds_is_timed_out(self, client, fake_clock):
        """恰好 30 秒时应超时"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.status_code == 504

    def test_30_1_seconds_is_timed_out(self, client, fake_clock):
        """30.1 秒时应超时"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(30.1)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.status_code == 504
        assert response.waited_seconds == pytest.approx(30.1)

    def test_60_seconds_is_timed_out(self, client, fake_clock):
        """60 秒时应超时"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(60)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.status_code == 504
        assert response.waited_seconds == pytest.approx(60.0)

    # ── 首token到达后不再超时 ──

    def test_first_token_arrived_no_timeout(self, client, fake_clock):
        """首token到达后，即使超过30秒也不再超时"""
        conn = client.connect("user-001", "gpt-4")
        conn.receive_first_token("Hello", fake_clock.current)

        fake_clock.advance(35)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is None
        assert conn.status == "streaming"

    def test_first_token_before_timeout_normal(self, client, fake_clock):
        """首token在超时前到达，连接正常"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(10)
        conn.receive_first_token("Hello", fake_clock.current)

        fake_clock.advance(25)

        response = client.check_first_token_timeout(conn.connection_id)

        assert response is None
        assert client.active_connections == 1

    # ── 接收token时同时检查超时 ──

    def test_receive_token_after_timeout_returns_504(self, client, fake_clock):
        """超时后才收到token，仍返回 504"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(31)

        response = client.receive_token(conn.connection_id, "Hello")

        assert response is not None
        assert response.status_code == 504
        assert response.error == "stream_first_token_timeout"

    def test_receive_token_before_timeout_succeeds(self, client, fake_clock):
        """超时前收到token，正常处理"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(15)

        response = client.receive_token(conn.connection_id, "Hello")

        assert response is None
        assert conn.status == "streaming"
        assert len(conn.chunks) == 1
        assert conn.chunks[0].token == "Hello"


class TestStreamRetryExhausted:
    """客户端重试2次后仍超时，最终返回 retries_exhausted=true"""

    def test_retry_2_times_then_exhausted(self, client_always_timeout, fake_clock):
        """重试2次后仍超时，返回 retries_exhausted=true"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert response.retries_exhausted is True
        assert response.status_code == 504
        assert response.retries_attempts == 3
        assert response.retries_max == 2

    def test_retry_error_is_retries_exhausted(self, client_always_timeout, fake_clock):
        """最终 error 为 retries_exhausted"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert response.error == "retries_exhausted"

    def test_retry_response_has_timeout_seconds_30(self, client_always_timeout, fake_clock):
        """重试耗尽后 timeout_seconds 仍为 30"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert response.timeout_seconds == 30.0

    def test_retry_no_delay_succeeds(self, client, fake_clock):
        """无 LLM 延迟设置，首次连接即成功"""
        response = client.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert response.status_code == 200
        assert response.retries_exhausted is False
        assert response.retries_attempts == 0

    def test_retry_0_max_no_retry(self, client_always_timeout, fake_clock):
        """max_retries=0 时不重试"""
        svc = StreamClient(
            timeout_seconds=30.0,
            max_retries=0,
            current_time_fn=fake_clock,
            llm_first_token_delay=60.0,
        )
        response = svc.retry_with_backoff("user-001", "gpt-4")

        assert response.retries_exhausted is True
        assert response.retries_attempts == 1
        assert response.retries_max == 0

    def test_retry_closed_connections_count(self, client_always_timeout, fake_clock):
        """重试2次共产生3个已关闭连接"""
        client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert len(client_always_timeout.closed_connections) == 3

    def test_retry_to_dict_contains_retries_exhausted(self, client_always_timeout, fake_clock):
        """to_dict 包含 retries_exhausted=true"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)
        body = response.to_dict()

        assert body["retries_exhausted"] is True
        assert body["retries_attempts"] == 3
        assert body["retries_max"] == 2

    def test_retry_message_includes_retry_count(self, client_always_timeout, fake_clock):
        """重试耗尽的消息包含重试次数"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert "重试" in response.message
        assert "2" in response.message

    def test_retry_with_1_max_retries(self, client_always_timeout, fake_clock):
        """max_retries=1 时重试1次共2次尝试"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=1)

        assert response.retries_exhausted is True
        assert response.retries_attempts == 2
        assert response.retries_max == 1

    def test_retry_status_code_504_with_exhausted(self, client_always_timeout, fake_clock):
        """重试耗尽后 status_code 仍为 504"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert response.status_code == 504


class TestStreamConnection:
    """StreamConnection 模型测试"""

    def test_new_connection_waiting_first_token(self, base_time):
        """新连接状态为 waiting_first_token"""
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        assert conn.status == "waiting_first_token"
        assert conn.first_token_at is None

    def test_is_first_token_timed_out_at_30_seconds(self, base_time):
        """30 秒时 is_first_token_timed_out 为 True"""
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        now = base_time + timedelta(seconds=30)
        assert conn.is_first_token_timed_out(now) is True

    def test_is_not_timed_out_at_29_seconds(self, base_time):
        """29 秒时 is_first_token_timed_out 为 False"""
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        now = base_time + timedelta(seconds=29)
        assert conn.is_first_token_timed_out(now) is False

    def test_after_first_token_not_timed_out(self, base_time):
        """首token到达后 is_first_token_timed_out 始终为 False"""
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        now = base_time + timedelta(seconds=5)
        conn.receive_first_token("Hello", now)

        later = base_time + timedelta(seconds=60)
        assert conn.is_first_token_timed_out(later) is False

    def test_mark_timed_out_sets_fields(self, base_time):
        """mark_timed_out 正确设置字段"""
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        conn.mark_timed_out(base_time + timedelta(seconds=30))

        assert conn.status == "timed_out"
        assert conn.error == "stream_first_token_timeout"

    def test_elapsed_seconds(self, base_time):
        """elapsed_seconds 计算正确"""
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        assert conn.elapsed_seconds(base_time + timedelta(seconds=45)) == 45.0

    def test_custom_timeout_seconds(self, base_time):
        """自定义超时时间生效"""
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=10.0,
        )
        now = base_time + timedelta(seconds=10)
        assert conn.is_first_token_timed_out(now) is True
        assert conn.is_first_token_timed_out(base_time + timedelta(seconds=9)) is False


class TestStreamResponse:
    """StreamResponse 响应体测试"""

    def test_timeout_response_to_dict(self):
        """超时响应 to_dict 格式正确"""
        resp = StreamResponse(
            status_code=504,
            connection_id="conn-001",
            error="stream_first_token_timeout",
            timeout_seconds=30.0,
            waited_seconds=30.123,
        )
        body = resp.to_dict()

        assert body["status_code"] == 504
        assert body["error"] == "stream_first_token_timeout"
        assert body["timeout_seconds"] == 30.0
        assert body["waited_seconds"] == 30.12
        assert body["retries_exhausted"] is False

    def test_retries_exhausted_response_to_dict(self):
        """重试耗尽响应 to_dict 格式正确"""
        resp = StreamResponse(
            status_code=504,
            connection_id="conn-001",
            error="retries_exhausted",
            timeout_seconds=30.0,
            waited_seconds=31.0,
            retries_attempts=3,
            retries_max=2,
            retries_exhausted=True,
        )
        body = resp.to_dict()

        assert body["retries_exhausted"] is True
        assert body["retries_attempts"] == 3
        assert body["retries_max"] == 2
        assert body["error"] == "retries_exhausted"

    def test_successful_response_to_dict(self):
        """成功响应 to_dict 格式正确"""
        resp = StreamResponse(
            status_code=200,
            connection_id="conn-001",
            retries_attempts=0,
            retries_max=2,
            retries_exhausted=False,
            message="流式连接成功建立",
        )
        body = resp.to_dict()

        assert body["status_code"] == 200
        assert body["retries_exhausted"] is False
        assert body["error"] is None


class TestStreamFirstTokenTimeoutError:
    """超时异常测试"""

    def test_exception_contains_fields(self):
        """异常包含所有字段"""
        err = StreamFirstTokenTimeoutError(
            connection_id="conn-001",
            waited_seconds=30.5,
            timeout_seconds=30.0,
        )
        assert err.connection_id == "conn-001"
        assert err.waited_seconds == 30.5
        assert err.timeout_seconds == 30.0
        assert "conn-001" in str(err)

    def test_exception_can_be_raised_and_caught(self):
        """异常可正常抛掷和捕获"""
        with pytest.raises(StreamFirstTokenTimeoutError) as exc_info:
            raise StreamFirstTokenTimeoutError(
                connection_id="conn-001",
                waited_seconds=30.5,
                timeout_seconds=30.0,
            )
        assert exc_info.value.connection_id == "conn-001"
        assert exc_info.value.waited_seconds == 30.5


class TestClientIntegration:
    """完整流程集成测试"""

    def test_full_flow_connect_timeout_check(self, client, fake_clock):
        """完整流程：连接 -> 等待30秒 -> 超时检查 -> 返回504"""
        conn = client.connect("user-001", "gpt-4")
        assert conn.status == "waiting_first_token"
        assert client.active_connections == 1

        fake_clock.advance(20)
        assert client.check_first_token_timeout(conn.connection_id) is None

        fake_clock.advance(15)
        response = client.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.status_code == 504
        assert response.error == "stream_first_token_timeout"
        assert response.timeout_seconds == 30.0
        assert response.waited_seconds >= 30.0
        assert client.active_connections == 0

    def test_full_flow_retry_exhausted(self, client_always_timeout, fake_clock):
        """完整流程：重试2次 -> 全部超时 -> retries_exhausted"""
        response = client_always_timeout.retry_with_backoff("user-001", "gpt-4", max_retries=2)

        assert response.status_code == 504
        assert response.retries_exhausted is True
        assert response.retries_attempts == 3
        assert response.retries_max == 2
        assert response.error == "retries_exhausted"
        assert response.timeout_seconds == 30.0

    def test_multiple_connections_independent(self, client, fake_clock):
        """多个连接独立超时"""
        conn1 = client.connect("user-001", "gpt-4")
        fake_clock.advance(0.1)
        conn2 = client.connect("user-002", "claude-3")

        assert client.active_connections == 2

        fake_clock.advance(30)
        resp1 = client.check_first_token_timeout(conn1.connection_id)
        assert resp1 is not None
        assert resp1.status_code == 504
        assert client.active_connections == 1

        resp2 = client.check_first_token_timeout(conn2.connection_id)
        assert resp2 is not None
        assert resp2.status_code == 504
        assert client.active_connections == 0

    def test_check_nonexistent_connection(self, client):
        """检查不存在的连接返回 404"""
        response = client.check_first_token_timeout("nonexistent-id")

        assert response is not None
        assert response.status_code == 404

    def test_short_timeout_client(self, client_short_timeout, fake_clock):
        """短超时客户端（5秒）验证"""
        conn = client_short_timeout.connect("user-001", "gpt-4")

        fake_clock.advance(4)
        assert client_short_timeout.check_first_token_timeout(conn.connection_id) is None

        fake_clock.advance(2)
        response = client_short_timeout.check_first_token_timeout(conn.connection_id)

        assert response is not None
        assert response.status_code == 504
        assert response.timeout_seconds == 5.0

    def test_receive_token_normal_flow(self, client, fake_clock):
        """正常流式流程：连接 -> 收到首token -> 收到后续chunk"""
        conn = client.connect("user-001", "gpt-4")
        fake_clock.advance(5)

        timeout_resp = client.receive_token(conn.connection_id, "Hello")
        assert timeout_resp is None
        assert conn.status == "streaming"
        assert len(conn.chunks) == 1
        assert conn.chunks[0].token == "Hello"

        fake_clock.advance(2)
        client.receive_token(conn.connection_id, " world")
        assert len(conn.chunks) == 2
        assert conn.chunks[1].token == " world"

        fake_clock.advance(30)
        assert client.check_first_token_timeout(conn.connection_id) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
