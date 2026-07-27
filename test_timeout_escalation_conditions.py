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


class TimeoutType(str, Enum):
    INFERENCE = "inference_timeout"
    SESSION = "session_timeout"
    STREAM_FIRST_TOKEN = "stream_first_token_timeout"


class TimeoutStatus(str, Enum):
    NORMAL = "normal"
    TIMED_OUT = "timed_out"


@dataclass
class TimeoutThreshold:
    """超时阈值配置"""
    inference_seconds: float = 120.0
    session_seconds: float = 1800.0
    stream_first_token_seconds: float = 30.0


@dataclass
class TimeoutEvent:
    """超时事件记录"""
    event_id: str
    timeout_type: str
    entity_id: str
    waited_seconds: float
    threshold_seconds: float
    triggered_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timeout_type": self.timeout_type,
            "entity_id": self.entity_id,
            "waited_seconds": round(self.waited_seconds, 2),
            "threshold_seconds": self.threshold_seconds,
            "triggered_at": self.triggered_at.isoformat(),
        }


@dataclass
class InferenceRequest:
    """单次推理请求"""
    request_id: str
    user_id: str
    model: str
    started_at: datetime
    timeout_seconds: float = 120.0
    status: str = TimeoutStatus.NORMAL.value
    _current_time_fn: Callable[[], datetime] = field(
        default_factory=lambda: _default_current_time, repr=False
    )

    def elapsed_seconds(self, now: datetime = None) -> float:
        t = now or self._current_time_fn()
        return (t - self.started_at).total_seconds()

    def is_timed_out(self, now: datetime = None) -> bool:
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def mark_timed_out(self):
        self.status = TimeoutStatus.TIMED_OUT.value


@dataclass
class Session:
    """会话"""
    session_id: str
    user_id: str
    started_at: datetime
    timeout_seconds: float = 1800.0
    status: str = TimeoutStatus.NORMAL.value
    _current_time_fn: Callable[[], datetime] = field(
        default_factory=lambda: _default_current_time, repr=False
    )

    def elapsed_seconds(self, now: datetime = None) -> float:
        t = now or self._current_time_fn()
        return (t - self.started_at).total_seconds()

    def is_timed_out(self, now: datetime = None) -> bool:
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def mark_timed_out(self):
        self.status = TimeoutStatus.TIMED_OUT.value


@dataclass
class StreamConnection:
    """流式连接"""
    connection_id: str
    user_id: str
    model: str
    started_at: datetime
    first_token_at: Optional[datetime] = None
    timeout_seconds: float = 30.0
    status: str = TimeoutStatus.NORMAL.value
    _current_time_fn: Callable[[], datetime] = field(
        default_factory=lambda: _default_current_time, repr=False
    )

    def elapsed_seconds(self, now: datetime = None) -> float:
        t = now or self._current_time_fn()
        return (t - self.started_at).total_seconds()

    def is_first_token_timed_out(self, now: datetime = None) -> bool:
        if self.first_token_at is not None:
            return False
        return self.elapsed_seconds(now) >= self.timeout_seconds

    def mark_timed_out(self):
        self.status = TimeoutStatus.TIMED_OUT.value


class TimeoutEscalationManager:
    """
    规定时限与超时升级管理器

    统一管理三种超时条件：
    1. 单次推理 > 120 秒
    2. 会话 > 30 分钟（1800 秒）
    3. 流式首 token > 30 秒
    """

    def __init__(
        self,
        thresholds: TimeoutThreshold = None,
        current_time_fn: Callable[[], datetime] = None,
    ):
        self._thresholds = thresholds or TimeoutThreshold()
        self._current_time_fn = current_time_fn or _default_current_time
        self._inferences: Dict[str, InferenceRequest] = {}
        self._sessions: Dict[str, Session] = {}
        self._streams: Dict[str, StreamConnection] = {}
        self._timeout_events: List[TimeoutEvent] = []

    def create_inference(self, user_id: str, model: str, prompt: str = "") -> InferenceRequest:
        now = self._current_time_fn()
        req_id = str(uuid.uuid4())
        req = InferenceRequest(
            request_id=req_id,
            user_id=user_id,
            model=model,
            started_at=now,
            timeout_seconds=self._thresholds.inference_seconds,
            _current_time_fn=self._current_time_fn,
        )
        self._inferences[req_id] = req
        return req

    def create_session(self, user_id: str) -> Session:
        now = self._current_time_fn()
        sess_id = str(uuid.uuid4())
        sess = Session(
            session_id=sess_id,
            user_id=user_id,
            started_at=now,
            timeout_seconds=self._thresholds.session_seconds,
            _current_time_fn=self._current_time_fn,
        )
        self._sessions[sess_id] = sess
        return sess

    def create_stream(self, user_id: str, model: str) -> StreamConnection:
        now = self._current_time_fn()
        conn_id = str(uuid.uuid4())
        conn = StreamConnection(
            connection_id=conn_id,
            user_id=user_id,
            model=model,
            started_at=now,
            timeout_seconds=self._thresholds.stream_first_token_seconds,
            _current_time_fn=self._current_time_fn,
        )
        self._streams[conn_id] = conn
        return conn

    def _create_timeout_event(
        self, timeout_type: str, entity_id: str, waited: float, threshold: float
    ) -> TimeoutEvent:
        now = self._current_time_fn()
        return TimeoutEvent(
            event_id=str(uuid.uuid4()),
            timeout_type=timeout_type,
            entity_id=entity_id,
            waited_seconds=waited,
            threshold_seconds=threshold,
            triggered_at=now,
        )

    def check_inference_timeout(self, request_id: str) -> Optional[TimeoutEvent]:
        """检查单次推理是否超时（>120秒触发）"""
        now = self._current_time_fn()
        req = self._inferences.get(request_id)
        if req is None:
            return None
        if req.status == TimeoutStatus.TIMED_OUT.value:
            return None
        if req.is_timed_out(now):
            waited = req.elapsed_seconds(now)
            req.mark_timed_out()
            event = self._create_timeout_event(
                TimeoutType.INFERENCE.value,
                request_id,
                waited,
                self._thresholds.inference_seconds,
            )
            self._timeout_events.append(event)
            return event
        return None

    def check_session_timeout(self, session_id: str) -> Optional[TimeoutEvent]:
        """检查会话是否超时（>30分钟触发）"""
        now = self._current_time_fn()
        sess = self._sessions.get(session_id)
        if sess is None:
            return None
        if sess.status == TimeoutStatus.TIMED_OUT.value:
            return None
        if sess.is_timed_out(now):
            waited = sess.elapsed_seconds(now)
            sess.mark_timed_out()
            event = self._create_timeout_event(
                TimeoutType.SESSION.value,
                session_id,
                waited,
                self._thresholds.session_seconds,
            )
            self._timeout_events.append(event)
            return event
        return None

    def check_stream_first_token_timeout(self, connection_id: str) -> Optional[TimeoutEvent]:
        """检查流式首token是否超时（>30秒触发）"""
        now = self._current_time_fn()
        conn = self._streams.get(connection_id)
        if conn is None:
            return None
        if conn.status == TimeoutStatus.TIMED_OUT.value:
            return None
        if conn.is_first_token_timed_out(now):
            waited = conn.elapsed_seconds(now)
            conn.mark_timed_out()
            event = self._create_timeout_event(
                TimeoutType.STREAM_FIRST_TOKEN.value,
                connection_id,
                waited,
                self._thresholds.stream_first_token_seconds,
            )
            self._timeout_events.append(event)
            return event
        return None

    def check_all_timeouts(self) -> List[TimeoutEvent]:
        """一次性检查所有实体的超时状态"""
        events = []
        for req_id in list(self._inferences.keys()):
            event = self.check_inference_timeout(req_id)
            if event:
                events.append(event)
        for sess_id in list(self._sessions.keys()):
            event = self.check_session_timeout(sess_id)
            if event:
                events.append(event)
        for conn_id in list(self._streams.keys()):
            event = self.check_stream_first_token_timeout(conn_id)
            if event:
                events.append(event)
        return events

    @property
    def timeout_events(self) -> List[TimeoutEvent]:
        return list(self._timeout_events)

    @property
    def active_inferences(self) -> int:
        return sum(1 for r in self._inferences.values() if r.status == TimeoutStatus.NORMAL.value)

    @property
    def active_sessions(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == TimeoutStatus.NORMAL.value)

    @property
    def active_streams(self) -> int:
        return sum(1 for s in self._streams.values() if s.status == TimeoutStatus.NORMAL.value)


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
    return TimeoutEscalationManager(
        thresholds=TimeoutThreshold(
            inference_seconds=120.0,
            session_seconds=1800.0,
            stream_first_token_seconds=30.0,
        ),
        current_time_fn=fake_clock,
    )


@pytest.fixture
def short_thresholds(fake_clock):
    return TimeoutEscalationManager(
        thresholds=TimeoutThreshold(
            inference_seconds=10.0,
            session_seconds=60.0,
            stream_first_token_seconds=5.0,
        ),
        current_time_fn=fake_clock,
    )


# ====================================================================
# 测试：单次推理 >120 秒触发超时
# ====================================================================

class TestInferenceTimeoutAt120Seconds:
    """验证单次推理请求持续时间超过 120 秒时正确触发超时"""

    def test_inference_times_out_at_exactly_120_seconds(self, manager, fake_clock):
        """恰好在 120 秒时触发超时"""
        req = manager.create_inference("user-001", "gpt-4", "Explain quantum")
        assert manager.active_inferences == 1

        fake_clock.advance(120)

        event = manager.check_inference_timeout(req.request_id)

        assert event is not None
        assert event.timeout_type == "inference_timeout"
        assert event.waited_seconds == pytest.approx(120.0)
        assert event.threshold_seconds == 120.0
        assert manager.active_inferences == 0

    def test_inference_not_timed_out_at_119_seconds(self, manager, fake_clock):
        """119 秒时不应触发超时"""
        req = manager.create_inference("user-001", "gpt-4", "Explain quantum")

        fake_clock.advance(119)

        event = manager.check_inference_timeout(req.request_id)

        assert event is None
        assert req.status == TimeoutStatus.NORMAL.value
        assert manager.active_inferences == 1

    def test_inference_times_out_at_120_1_seconds(self, manager, fake_clock):
        """120.1 秒时应触发超时"""
        req = manager.create_inference("user-001", "gpt-4", "Explain quantum")

        fake_clock.advance(120.1)

        event = manager.check_inference_timeout(req.request_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(120.1)

    def test_inference_event_to_dict_contains_all_fields(self, manager, fake_clock):
        """超时事件 to_dict 包含所有必需字段"""
        req = manager.create_inference("user-001", "gpt-4", "Prompt")
        fake_clock.advance(120)
        event = manager.check_inference_timeout(req.request_id)
        body = event.to_dict()

        assert body["timeout_type"] == "inference_timeout"
        assert body["entity_id"] == req.request_id
        assert body["waited_seconds"] == 120.0
        assert body["threshold_seconds"] == 120.0
        assert "event_id" in body
        assert "triggered_at" in body

    def test_inference_marked_timed_out(self, manager, fake_clock):
        """超时后推理请求状态变为 timed_out"""
        req = manager.create_inference("user-001", "gpt-4", "Prompt")

        fake_clock.advance(120)
        manager.check_inference_timeout(req.request_id)

        assert req.status == TimeoutStatus.TIMED_OUT.value

    def test_inference_timeout_recorded_in_events(self, manager, fake_clock):
        """超时事件记录到全局事件列表"""
        req = manager.create_inference("user-001", "gpt-4", "Prompt")

        fake_clock.advance(120)
        manager.check_inference_timeout(req.request_id)

        events = manager.timeout_events
        assert len(events) == 1
        assert events[0].timeout_type == "inference_timeout"

    def test_inference_200_seconds_still_times_out(self, manager, fake_clock):
        """200 秒时仍触发超时"""
        req = manager.create_inference("user-001", "gpt-4", "Prompt")

        fake_clock.advance(200)

        event = manager.check_inference_timeout(req.request_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(200.0)

    def test_inference_check_nonexistent_returns_none(self, manager):
        """检查不存在的推理请求返回 None"""
        assert manager.check_inference_timeout("nonexistent") is None


# ====================================================================
# 测试：会话 >30 分钟触发超时
# ====================================================================

class TestSessionTimeoutAt30Minutes:
    """验证会话持续时间超过 30 分钟时正确触发超时"""

    def test_session_times_out_at_exactly_30_minutes(self, manager, fake_clock):
        """恰好在 30 分钟（1800 秒）时触发超时"""
        sess = manager.create_session("user-001")
        assert manager.active_sessions == 1

        fake_clock.advance(1800)

        event = manager.check_session_timeout(sess.session_id)

        assert event is not None
        assert event.timeout_type == "session_timeout"
        assert event.waited_seconds == pytest.approx(1800.0)
        assert event.threshold_seconds == 1800.0
        assert manager.active_sessions == 0

    def test_session_not_timed_out_at_29_minutes(self, manager, fake_clock):
        """29 分钟（1740 秒）时不应触发超时"""
        sess = manager.create_session("user-001")

        fake_clock.advance(1740)

        event = manager.check_session_timeout(sess.session_id)

        assert event is None
        assert sess.status == TimeoutStatus.NORMAL.value

    def test_session_not_timed_out_at_1799_seconds(self, manager, fake_clock):
        """1799 秒时不应触发超时"""
        sess = manager.create_session("user-001")

        fake_clock.advance(1799)

        event = manager.check_session_timeout(sess.session_id)

        assert event is None
        assert manager.active_sessions == 1

    def test_session_times_out_at_1801_seconds(self, manager, fake_clock):
        """1801 秒时应触发超时"""
        sess = manager.create_session("user-001")

        fake_clock.advance(1801)

        event = manager.check_session_timeout(sess.session_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(1801.0)

    def test_session_marked_timed_out(self, manager, fake_clock):
        """超时后会话状态变为 timed_out"""
        sess = manager.create_session("user-001")

        fake_clock.advance(1800)
        manager.check_session_timeout(sess.session_id)

        assert sess.status == TimeoutStatus.TIMED_OUT.value

    def test_session_timeout_event_to_dict(self, manager, fake_clock):
        """会话超时事件 to_dict 格式正确"""
        sess = manager.create_session("user-001")
        fake_clock.advance(1800)
        event = manager.check_session_timeout(sess.session_id)
        body = event.to_dict()

        assert body["timeout_type"] == "session_timeout"
        assert body["entity_id"] == sess.session_id
        assert body["waited_seconds"] == 1800.0
        assert body["threshold_seconds"] == 1800.0

    def test_session_3600_seconds_still_times_out(self, manager, fake_clock):
        """3600 秒（60 分钟）时仍触发超时"""
        sess = manager.create_session("user-001")

        fake_clock.advance(3600)

        event = manager.check_session_timeout(sess.session_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(3600.0)

    def test_session_check_nonexistent_returns_none(self, manager):
        """检查不存在的会话返回 None"""
        assert manager.check_session_timeout("nonexistent") is None


# ====================================================================
# 测试：流式首 token >30 秒触发超时
# ====================================================================

class TestStreamFirstTokenTimeoutAt30Seconds:
    """验证流式响应首 token 超过 30 秒时正确触发超时"""

    def test_stream_times_out_at_exactly_30_seconds(self, manager, fake_clock):
        """恰好在 30 秒时触发超时"""
        conn = manager.create_stream("user-001", "gpt-4")
        assert manager.active_streams == 1

        fake_clock.advance(30)

        event = manager.check_stream_first_token_timeout(conn.connection_id)

        assert event is not None
        assert event.timeout_type == "stream_first_token_timeout"
        assert event.waited_seconds == pytest.approx(30.0)
        assert event.threshold_seconds == 30.0
        assert manager.active_streams == 0

    def test_stream_not_timed_out_at_29_seconds(self, manager, fake_clock):
        """29 秒时不应触发超时"""
        conn = manager.create_stream("user-001", "gpt-4")

        fake_clock.advance(29)

        event = manager.check_stream_first_token_timeout(conn.connection_id)

        assert event is None
        assert conn.status == TimeoutStatus.NORMAL.value

    def test_stream_not_timed_out_at_29_9_seconds(self, manager, fake_clock):
        """29.9 秒时不应触发超时"""
        conn = manager.create_stream("user-001", "gpt-4")

        fake_clock.advance(29.9)

        event = manager.check_stream_first_token_timeout(conn.connection_id)

        assert event is None
        assert manager.active_streams == 1

    def test_stream_times_out_at_30_1_seconds(self, manager, fake_clock):
        """30.1 秒时应触发超时"""
        conn = manager.create_stream("user-001", "gpt-4")

        fake_clock.advance(30.1)

        event = manager.check_stream_first_token_timeout(conn.connection_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(30.1)

    def test_stream_after_first_token_no_timeout(self, manager, fake_clock):
        """首 token 到达后即使超过 30 秒也不触发超时"""
        conn = manager.create_stream("user-001", "gpt-4")
        conn.first_token_at = fake_clock.current

        fake_clock.advance(60)

        event = manager.check_stream_first_token_timeout(conn.connection_id)

        assert event is None
        assert manager.active_streams == 1

    def test_stream_marked_timed_out(self, manager, fake_clock):
        """超时后流式连接状态变为 timed_out"""
        conn = manager.create_stream("user-001", "gpt-4")

        fake_clock.advance(30)
        manager.check_stream_first_token_timeout(conn.connection_id)

        assert conn.status == TimeoutStatus.TIMED_OUT.value

    def test_stream_timeout_event_to_dict(self, manager, fake_clock):
        """流式超时事件 to_dict 格式正确"""
        conn = manager.create_stream("user-001", "gpt-4")
        fake_clock.advance(30)
        event = manager.check_stream_first_token_timeout(conn.connection_id)
        body = event.to_dict()

        assert body["timeout_type"] == "stream_first_token_timeout"
        assert body["entity_id"] == conn.connection_id
        assert body["waited_seconds"] == 30.0
        assert body["threshold_seconds"] == 30.0

    def test_stream_60_seconds_still_times_out(self, manager, fake_clock):
        """60 秒时仍触发超时"""
        conn = manager.create_stream("user-001", "gpt-4")

        fake_clock.advance(60)

        event = manager.check_stream_first_token_timeout(conn.connection_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(60.0)

    def test_stream_check_nonexistent_returns_none(self, manager):
        """检查不存在的流式连接返回 None"""
        assert manager.check_stream_first_token_timeout("nonexistent") is None


# ====================================================================
# 测试：三种超时条件综合验证
# ====================================================================

class TestAllThreeTimeoutConditions:
    """验证三种超时条件均正确触发"""

    def test_all_three_timeout_types_have_correct_thresholds(self, manager):
        """三种超时类型的阈值分别为 120s、1800s、30s"""
        thresholds = manager._thresholds

        assert thresholds.inference_seconds == 120.0
        assert thresholds.session_seconds == 1800.0
        assert thresholds.stream_first_token_seconds == 30.0

    def test_three_entities_each_timeout_at_own_threshold(self, manager, fake_clock):
        """三种实体分别在各自阈值触发超时"""
        inference = manager.create_inference("user-001", "gpt-4", "Prompt")
        session = manager.create_session("user-001")
        stream = manager.create_stream("user-001", "gpt-4")

        # 1. 30 秒时：流式超时，推理和会话未超时
        fake_clock.advance(30)
        stream_event = manager.check_stream_first_token_timeout(stream.connection_id)
        inference_event = manager.check_inference_timeout(inference.request_id)
        session_event = manager.check_session_timeout(session.session_id)

        assert stream_event is not None
        assert stream_event.timeout_type == "stream_first_token_timeout"
        assert inference_event is None
        assert session_event is None

        # 2. 120 秒时：推理超时，会话未超时
        fake_clock.advance(90)
        inference_event = manager.check_inference_timeout(inference.request_id)
        session_event = manager.check_session_timeout(session.session_id)

        assert inference_event is not None
        assert inference_event.timeout_type == "inference_timeout"
        assert inference_event.waited_seconds == pytest.approx(120.0)
        assert session_event is None

        # 3. 1800 秒时：会话超时
        fake_clock.advance(1680)
        session_event = manager.check_session_timeout(session.session_id)

        assert session_event is not None
        assert session_event.timeout_type == "session_timeout"
        assert session_event.waited_seconds == pytest.approx(1800.0)

    def test_all_three_triggered_total_three_events(self, manager, fake_clock):
        """三种条件最终产生了三个超时事件"""
        inference = manager.create_inference("user-001", "gpt-4", "Prompt")
        session = manager.create_session("user-001")
        stream = manager.create_stream("user-001", "gpt-4")

        # 推进到 1800 秒，三种条件全部满足
        fake_clock.advance(1800)

        events = manager.check_all_timeouts()

        assert len(events) == 3
        types = {e.timeout_type for e in events}
        assert types == {
            "inference_timeout",
            "session_timeout",
            "stream_first_token_timeout",
        }

    def test_check_all_timeouts_at_30_seconds_only_stream(self, manager, fake_clock):
        """在 30 秒时 check_all_timeouts 仅触发流式超时"""
        inference = manager.create_inference("user-001", "gpt-4", "Prompt")
        session = manager.create_session("user-001")
        stream = manager.create_stream("user-001", "gpt-4")

        fake_clock.advance(30)
        events = manager.check_all_timeouts()

        assert len(events) == 1
        assert events[0].timeout_type == "stream_first_token_timeout"

    def test_check_all_timeouts_at_120_seconds_inference_and_stream(self, manager, fake_clock):
        """在 120 秒时 check_all_timeouts 触发推理和流式超时"""
        inference = manager.create_inference("user-001", "gpt-4", "Prompt")
        session = manager.create_session("user-001")
        stream = manager.create_stream("user-001", "gpt-4")

        fake_clock.advance(120)
        events = manager.check_all_timeouts()

        assert len(events) == 2
        types = {e.timeout_type for e in events}
        assert types == {"inference_timeout", "stream_first_token_timeout"}

    def test_staggered_timeouts_with_check_all(self, manager, fake_clock):
        """分阶段检查：30s → 120s → 1800s"""
        inference = manager.create_inference("user-001", "gpt-4", "Prompt")
        session = manager.create_session("user-001")
        stream = manager.create_stream("user-001", "gpt-4")

        # 阶段 1：30 秒
        fake_clock.advance(30)
        events_30s = manager.check_all_timeouts()
        assert len(events_30s) == 1
        assert events_30s[0].timeout_type == "stream_first_token_timeout"

        # 阶段 2：推进至 120 秒
        fake_clock.advance(90)
        events_120s = manager.check_all_timeouts()
        assert len(events_120s) == 1
        assert events_120s[0].timeout_type == "inference_timeout"

        # 阶段 3：推进至 1800 秒
        fake_clock.advance(1680)
        events_1800s = manager.check_all_timeouts()
        assert len(events_1800s) == 1
        assert events_1800s[0].timeout_type == "session_timeout"

        # 总计 3 个事件
        assert len(manager.timeout_events) == 3


# ====================================================================
# 测试：自定义阈值
# ====================================================================

class TestCustomThresholds:
    """使用短阈值验证超时逻辑"""

    def test_short_inference_timeout(self, short_thresholds, fake_clock):
        """短超时（10 秒），10 秒后推理触发"""
        req = short_thresholds.create_inference("user-001", "gpt-4", "Prompt")

        fake_clock.advance(9)
        assert short_thresholds.check_inference_timeout(req.request_id) is None

        fake_clock.advance(1)
        event = short_thresholds.check_inference_timeout(req.request_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(10.0)

    def test_short_session_timeout(self, short_thresholds, fake_clock):
        """短超时（60 秒），60 秒后会话触发"""
        sess = short_thresholds.create_session("user-001")

        fake_clock.advance(59)
        assert short_thresholds.check_session_timeout(sess.session_id) is None

        fake_clock.advance(1)
        event = short_thresholds.check_session_timeout(sess.session_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(60.0)

    def test_short_stream_timeout(self, short_thresholds, fake_clock):
        """短超时（5 秒），5 秒后流式触发"""
        conn = short_thresholds.create_stream("user-001", "gpt-4")

        fake_clock.advance(4)
        assert short_thresholds.check_stream_first_token_timeout(conn.connection_id) is None

        fake_clock.advance(1)
        event = short_thresholds.check_stream_first_token_timeout(conn.connection_id)

        assert event is not None
        assert event.waited_seconds == pytest.approx(5.0)

    def test_all_short_thresholds_trigger(self, short_thresholds, fake_clock):
        """三种短阈值全部触发"""
        req = short_thresholds.create_inference("user-001", "gpt-4", "Prompt")
        sess = short_thresholds.create_session("user-001")
        conn = short_thresholds.create_stream("user-001", "gpt-4")

        # 推进到 60 秒（超过所有短阈值）
        fake_clock.advance(60)
        events = short_thresholds.check_all_timeouts()

        assert len(events) == 3


# ====================================================================
# 测试：领域对象
# ====================================================================

class TestInferenceRequestModel:
    """InferenceRequest 领域对象测试"""

    def test_new_inference_status_normal(self, base_time):
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        assert req.status == TimeoutStatus.NORMAL.value

    def test_inference_is_timed_out_at_120(self, base_time):
        req = InferenceRequest(
            request_id="req-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=120.0,
        )
        assert req.is_timed_out(base_time + timedelta(seconds=120)) is True
        assert req.is_timed_out(base_time + timedelta(seconds=119)) is False


class TestSessionModel:
    """Session 领域对象测试"""

    def test_new_session_status_normal(self, base_time):
        sess = Session(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        assert sess.status == TimeoutStatus.NORMAL.value

    def test_session_is_timed_out_at_1800(self, base_time):
        sess = Session(
            session_id="sess-001",
            user_id="user-001",
            started_at=base_time,
            timeout_seconds=1800.0,
        )
        assert sess.is_timed_out(base_time + timedelta(seconds=1800)) is True
        assert sess.is_timed_out(base_time + timedelta(seconds=1799)) is False


class TestStreamConnectionModel:
    """StreamConnection 领域对象测试"""

    def test_new_stream_status_normal(self, base_time):
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        assert conn.status == TimeoutStatus.NORMAL.value
        assert conn.first_token_at is None

    def test_stream_is_first_token_timed_out_at_30(self, base_time):
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        assert conn.is_first_token_timed_out(base_time + timedelta(seconds=30)) is True
        assert conn.is_first_token_timed_out(base_time + timedelta(seconds=29)) is False

    def test_stream_with_first_token_not_timed_out(self, base_time):
        conn = StreamConnection(
            connection_id="conn-001",
            user_id="user-001",
            model="gpt-4",
            started_at=base_time,
            timeout_seconds=30.0,
        )
        conn.first_token_at = base_time
        assert conn.is_first_token_timed_out(base_time + timedelta(seconds=60)) is False


class TestTimeoutEventModel:
    """TimeoutEvent 领域对象测试"""

    def test_timeout_event_to_dict(self, base_time):
        event = TimeoutEvent(
            event_id="evt-001",
            timeout_type="inference_timeout",
            entity_id="req-001",
            waited_seconds=120.0,
            threshold_seconds=120.0,
            triggered_at=base_time,
        )
        body = event.to_dict()

        assert body["event_id"] == "evt-001"
        assert body["timeout_type"] == "inference_timeout"
        assert body["entity_id"] == "req-001"
        assert body["waited_seconds"] == 120.0
        assert body["threshold_seconds"] == 120.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
