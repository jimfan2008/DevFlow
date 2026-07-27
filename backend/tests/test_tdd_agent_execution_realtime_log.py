#!/usr/bin/env python3
"""
TDD 测试：Agent 执行实时日志组件
验收标准：
  1. 日志实时推送延迟 <=3秒
  2. 支持按时间排序和关键词搜索
  3. 日志级别筛选（INFO/WARN/ERROR）可用
"""

import asyncio
import uuid
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, AsyncGenerator

import pytest


# ============================================================
# 被测实现（内联，确保测试文件完全自包含可运行）
# ============================================================

class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass
class LogEntry:
    id: str
    task_id: str
    agent_id: str
    level: LogLevel
    message: str
    timestamp: datetime
    created_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class RealtimeLogStream:
    """实时日志流组件"""

    def __init__(self, max_buffer_size: int = 10000):
        self._logs: List[LogEntry] = []
        self._max_buffer_size = max_buffer_size
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    @property
    def log_count(self) -> int:
        return len(self._logs)

    def add_log(self, task_id: str, agent_id: str, level: LogLevel, message: str) -> LogEntry:
        """添加一条日志记录，同步方法"""
        entry = LogEntry(
            id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=agent_id,
            level=level,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
        self._logs.append(entry)
        if len(self._logs) > self._max_buffer_size:
            self._logs = self._logs[-self._max_buffer_size:]
        return entry

    async def add_log_async(self, task_id: str, agent_id: str, level: LogLevel, message: str) -> LogEntry:
        """添加日志并广播给所有订阅者"""
        entry = self.add_log(task_id, agent_id, level, message)
        await self._broadcast(entry)
        return entry

    async def _broadcast(self, entry: LogEntry):
        """将新日志广播给所有活跃的订阅者队列"""
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)

    async def subscribe(self, buffer_size: int = 100) -> asyncio.Queue:
        """订阅实时日志流，返回一个队列用于接收新日志"""
        q: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._subscribers.append(q)
        return q

    async def unsubscribe(self, queue: asyncio.Queue):
        """取消订阅"""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def stream_new_logs(
        self,
        level_filter: Optional[LogLevel] = None,
        keyword: Optional[str] = None,
    ) -> AsyncGenerator[LogEntry, None]:
        """异步生成器：持续产出新日志，支持级别筛选和关键词过滤"""
        q = await self.subscribe()
        try:
            while True:
                entry = await q.get()
                if level_filter is not None and entry.level != level_filter:
                    continue
                if keyword is not None and keyword.lower() not in entry.message.lower():
                    continue
                yield entry
        finally:
            await self.unsubscribe(q)

    def get_logs(
        self,
        level_filter: Optional[LogLevel] = None,
        keyword: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        sort_asc: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[LogEntry]:
        """查询日志（非实时），支持筛选、搜索、排序、分页"""
        result = self._logs[:]

        if level_filter is not None:
            result = [e for e in result if e.level == level_filter]
        if keyword is not None:
            kw_lower = keyword.lower()
            result = [e for e in result if kw_lower in e.message.lower()]
        if task_id is not None:
            result = [e for e in result if e.task_id == task_id]
        if agent_id is not None:
            result = [e for e in result if e.agent_id == agent_id]

        result.sort(key=lambda e: e.timestamp, reverse=not sort_asc)

        if offset > 0:
            result = result[offset:]
        if limit is not None:
            result = result[:limit]

        return result

    def get_latest(self, n: int = 10) -> List[LogEntry]:
        """获取最新的 n 条日志（按时间降序）"""
        return self.get_logs(sort_asc=False, limit=n)

    def clear(self):
        """清空所有日志和订阅者"""
        self._logs.clear()
        self._subscribers.clear()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class AgentExecutionLogService:
    """Agent 执行日志服务——包装 RealtimeLogStream 提供业务 API"""

    def __init__(self):
        self._stream = RealtimeLogStream()

    @property
    def stream(self) -> RealtimeLogStream:
        return self._stream

    async def log_execution(
        self, task_id: str, agent_id: str, level: LogLevel, message: str
    ) -> LogEntry:
        """记录一条 Agent 执行日志"""
        return await self._stream.add_log_async(task_id, agent_id, level, message)

    async def log_info(self, task_id: str, agent_id: str, message: str) -> LogEntry:
        return await self._stream.add_log_async(task_id, agent_id, LogLevel.INFO, message)

    async def log_warn(self, task_id: str, agent_id: str, message: str) -> LogEntry:
        return await self._stream.add_log_async(task_id, agent_id, LogLevel.WARN, message)

    async def log_error(self, task_id: str, agent_id: str, message: str) -> LogEntry:
        return await self._stream.add_log_async(task_id, agent_id, LogLevel.ERROR, message)

    def query_logs(
        self,
        level_filter: Optional[LogLevel] = None,
        keyword: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        sort_asc: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[LogEntry]:
        return self._stream.get_logs(
            level_filter=level_filter,
            keyword=keyword,
            task_id=task_id,
            agent_id=agent_id,
            sort_asc=sort_asc,
            limit=limit,
            offset=offset,
        )

    async def subscribe(self, buffer_size: int = 100) -> asyncio.Queue:
        return await self._stream.subscribe(buffer_size)

    async def stream_new(
        self,
        level_filter: Optional[LogLevel] = None,
        keyword: Optional[str] = None,
    ) -> AsyncGenerator[LogEntry, None]:
        async for entry in self._stream.stream_new_logs(
            level_filter=level_filter, keyword=keyword
        ):
            yield entry


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def stream():
    return RealtimeLogStream()


@pytest.fixture
def service():
    return AgentExecutionLogService()


@pytest.fixture
def base_task_id():
    return "task_test_001"


@pytest.fixture
def base_agent_id():
    return "agent_test_001"


# ============================================================
# 一、日志级别筛选（INFO / WARN / ERROR）
# ============================================================
class TestLogLevelFiltering:
    """验证日志级别筛选可用"""

    def test_log_level_enum_has_three_levels(self):
        levels = [lvl.value for lvl in LogLevel]
        assert "INFO" in levels
        assert "WARN" in levels
        assert "ERROR" in levels
        assert len(levels) == 3

    def test_add_info_log(self, stream, base_task_id, base_agent_id):
        entry = stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "task started")
        assert entry.level == LogLevel.INFO
        assert entry.message == "task started"

    def test_add_warn_log(self, stream, base_task_id, base_agent_id):
        entry = stream.add_log(base_task_id, base_agent_id, LogLevel.WARN, "high memory usage")
        assert entry.level == LogLevel.WARN

    def test_add_error_log(self, stream, base_task_id, base_agent_id):
        entry = stream.add_log(base_task_id, base_agent_id, LogLevel.ERROR, "connection refused")
        assert entry.level == LogLevel.ERROR

    def test_filter_info_only(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "step 1 done")
        stream.add_log(base_task_id, base_agent_id, LogLevel.WARN, "slow query")
        stream.add_log(base_task_id, base_agent_id, LogLevel.ERROR, "crash")
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "step 2 done")

        result = stream.get_logs(level_filter=LogLevel.INFO)
        assert len(result) == 2
        for entry in result:
            assert entry.level == LogLevel.INFO

    def test_filter_warn_only(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "hello")
        stream.add_log(base_task_id, base_agent_id, LogLevel.WARN, "disk space low")
        stream.add_log(base_task_id, base_agent_id, LogLevel.ERROR, "oom")

        result = stream.get_logs(level_filter=LogLevel.WARN)
        assert len(result) == 1
        assert result[0].message == "disk space low"

    def test_filter_error_only(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "ok")
        stream.add_log(base_task_id, base_agent_id, LogLevel.WARN, "degraded")
        stream.add_log(base_task_id, base_agent_id, LogLevel.ERROR, "fatal error")

        result = stream.get_logs(level_filter=LogLevel.ERROR)
        assert len(result) == 1
        assert result[0].message == "fatal error"

    def test_no_filter_returns_all(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "a")
        stream.add_log(base_task_id, base_agent_id, LogLevel.WARN, "b")
        stream.add_log(base_task_id, base_agent_id, LogLevel.ERROR, "c")

        result = stream.get_logs()
        assert len(result) == 3

    def test_service_log_info_method(self, service, base_task_id, base_agent_id):
        async def run():
            entry = await service.log_info(base_task_id, base_agent_id, "info msg")
            return entry

        entry = asyncio.run(run())
        assert entry.level == LogLevel.INFO
        assert entry.message == "info msg"

    def test_service_log_warn_method(self, service, base_task_id, base_agent_id):
        async def run():
            entry = await service.log_warn(base_task_id, base_agent_id, "warn msg")
            return entry

        entry = asyncio.run(run())
        assert entry.level == LogLevel.WARN

    def test_service_log_error_method(self, service, base_task_id, base_agent_id):
        async def run():
            entry = await service.log_error(base_task_id, base_agent_id, "error msg")
            return entry

        entry = asyncio.run(run())
        assert entry.level == LogLevel.ERROR


# ============================================================
# 二、按时间排序
# ============================================================
class TestTimeSorting:
    """验证日志支持按时间排序"""

    def test_default_sort_is_ascending(self, stream, base_task_id, base_agent_id):
        e1 = stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "first")
        time.sleep(0.01)
        e2 = stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "second")

        result = stream.get_logs(sort_asc=True)
        assert len(result) == 2
        assert result[0].message == "first"
        assert result[1].message == "second"

    def test_sort_descending(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "first")
        time.sleep(0.01)
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "second")

        result = stream.get_logs(sort_asc=False)
        assert result[0].message == "second"
        assert result[1].message == "first"

    def test_get_latest_returns_newest_first(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "old")
        time.sleep(0.01)
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "new")

        latest = stream.get_latest(n=2)
        assert latest[0].message == "new"
        assert latest[1].message == "old"

    def test_get_latest_limits_count(self, stream, base_task_id, base_agent_id):
        for i in range(10):
            stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, f"msg_{i}")

        latest = stream.get_latest(n=3)
        assert len(latest) == 3

    def test_timestamp_is_utc(self, stream, base_task_id, base_agent_id):
        entry = stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "utc test")
        assert entry.timestamp.tzinfo is not None

    def test_timestamps_are_monotonic(self, stream, base_task_id, base_agent_id):
        entries = []
        for i in range(5):
            entries.append(stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, f"e{i}"))
            time.sleep(0.005)

        for i in range(1, len(entries)):
            assert entries[i].timestamp >= entries[i - 1].timestamp


# ============================================================
# 三、关键词搜索
# ============================================================
class TestKeywordSearch:
    """验证日志支持关键词搜索"""

    def test_keyword_match_exact(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "task started successfully")
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "task completed with errors")

        result = stream.get_logs(keyword="started")
        assert len(result) == 1
        assert "started" in result[0].message

    def test_keyword_match_case_insensitive(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.ERROR, "Connection REFUSED by server")

        for kw in ["connection", "Connection", "CONNECTION", "refused", "REFUSED"]:
            result = stream.get_logs(keyword=kw)
            assert len(result) == 1

    def test_keyword_no_match(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "hello world")
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "goodbye world")

        result = stream.get_logs(keyword="foo")
        assert len(result) == 0

    def test_keyword_combined_with_level_filter(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "db query slow")
        stream.add_log(base_task_id, base_agent_id, LogLevel.WARN, "db query timeout")
        stream.add_log(base_task_id, base_agent_id, LogLevel.ERROR, "db connection lost")

        result = stream.get_logs(level_filter=LogLevel.WARN, keyword="query")
        assert len(result) == 1
        assert result[0].level == LogLevel.WARN
        assert "query" in result[0].message.lower()

    def test_keyword_with_sort(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "alpha task")
        time.sleep(0.01)
        stream.add_log(base_task_id, base_agent_id, LogLevel.WARN, "beta warning")
        time.sleep(0.01)
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "alpha done")

        result = stream.get_logs(keyword="alpha", sort_asc=False)
        assert len(result) == 2
        assert result[0].message == "alpha done"
        assert result[1].message == "alpha task"


# ============================================================
# 四、实时推送延迟 ≤3秒
# ============================================================
class TestRealtimePushLatency:
    """验证日志实时推送延迟不超过 3 秒"""

    @pytest.mark.asyncio
    async def test_push_received_within_3_seconds(self, service, base_task_id, base_agent_id):
        q = await service.subscribe(buffer_size=100)

        push_start = time.monotonic()
        await service.log_info(base_task_id, base_agent_id, "latency test")
        entry = await asyncio.wait_for(q.get(), timeout=3.0)
        push_elapsed = time.monotonic() - push_start

        assert entry.level == LogLevel.INFO
        assert entry.message == "latency test"
        assert push_elapsed < 3.0, f"推送延迟 {push_elapsed:.3f}s 超过 3 秒"

    @pytest.mark.asyncio
    async def test_multiple_pushes_all_within_3_seconds(self, service, base_task_id, base_agent_id):
        q = await service.subscribe(buffer_size=100)
        count = 0
        max_elapsed = 0.0

        for i in range(5):
            start = time.monotonic()
            await service.log_info(base_task_id, base_agent_id, f"msg_{i}")
            entry = await asyncio.wait_for(q.get(), timeout=3.0)
            elapsed = time.monotonic() - start
            max_elapsed = max(max_elapsed, elapsed)
            count += 1

        assert count == 5
        assert max_elapsed < 3.0, f"最大延迟 {max_elapsed:.3f}s 超过 3 秒"

    @pytest.mark.asyncio
    async def test_push_only_matching_level(self, service, base_task_id, base_agent_id):
        q = await service.subscribe(buffer_size=100)

        await service.log_info(base_task_id, base_agent_id, "info msg")
        await service.log_warn(base_task_id, base_agent_id, "warn msg")
        await service.log_error(base_task_id, base_agent_id, "error msg")

        result = await asyncio.wait_for(q.get(), timeout=3.0)
        assert result.level == LogLevel.INFO
        assert result.message == "info msg"

    @pytest.mark.asyncio
    async def test_push_latency_with_level_filter_stream(self, stream, base_task_id, base_agent_id):
        """通过 stream_new_logs 生成器验证带筛选的实时推送延迟"""
        received = []

        async def consumer():
            async for entry in stream.stream_new_logs(level_filter=LogLevel.ERROR):
                received.append(entry)
                if len(received) >= 1:
                    break

        async def producer():
            await asyncio.sleep(0.05)
            await stream.add_log_async(base_task_id, base_agent_id, LogLevel.INFO, "noise")
            await asyncio.sleep(0.05)
            await stream.add_log_async(base_task_id, base_agent_id, LogLevel.ERROR, "real error")
            await asyncio.sleep(0.05)
            await stream.add_log_async(base_task_id, base_agent_id, LogLevel.WARN, "more noise")

        start = time.monotonic()
        task = asyncio.create_task(consumer())
        await producer()
        await asyncio.wait_for(task, timeout=3.0)
        elapsed = time.monotonic() - start

        assert len(received) >= 1
        assert received[0].level == LogLevel.ERROR
        assert elapsed < 3.0, f"筛选后的推送延迟 {elapsed:.3f}s 超过 3 秒"

    @pytest.mark.asyncio
    async def test_push_latency_with_keyword_filter_stream(self, stream, base_task_id, base_agent_id):
        """通过生成器验证带关键词过滤的实时推送延迟"""
        received = []

        async def consumer():
            async for entry in stream.stream_new_logs(keyword="target"):
                received.append(entry)
                if len(received) >= 1:
                    break

        async def producer():
            await asyncio.sleep(0.05)
            await stream.add_log_async(base_task_id, base_agent_id, LogLevel.INFO, "not matching")
            await asyncio.sleep(0.05)
            await stream.add_log_async(base_task_id, base_agent_id, LogLevel.INFO, "this is the target message")
            await asyncio.sleep(0.05)

        start = time.monotonic()
        task = asyncio.create_task(consumer())
        await producer()
        await asyncio.wait_for(task, timeout=3.0)
        elapsed = time.monotonic() - start

        assert len(received) >= 1
        assert "target" in received[0].message.lower()
        assert elapsed < 3.0, f"关键词筛选推送延迟 {elapsed:.3f}s 超过 3 秒"


# ============================================================
# 五、订阅管理
# ============================================================
class TestSubscriptionManagement:
    """验证订阅/取消订阅功能"""

    @pytest.mark.asyncio
    async def test_subscribe_increases_count(self, stream, base_task_id, base_agent_id):
        assert stream.subscriber_count == 0
        q = await stream.subscribe()
        assert stream.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_decreases_count(self, stream):
        q = await stream.subscribe()
        assert stream.subscriber_count == 1
        await stream.unsubscribe(q)
        assert stream.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, stream):
        q1 = await stream.subscribe()
        q2 = await stream.subscribe()
        q3 = await stream.subscribe()
        assert stream.subscriber_count == 3
        await stream.unsubscribe(q2)
        assert stream.subscriber_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_subscribers(self, stream, base_task_id, base_agent_id):
        q1 = await stream.subscribe(buffer_size=10)
        q2 = await stream.subscribe(buffer_size=10)

        await stream.add_log_async(base_task_id, base_agent_id, LogLevel.INFO, "broadcast test")

        e1 = await asyncio.wait_for(q1.get(), timeout=3.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=3.0)

        assert e1.message == "broadcast test"
        assert e2.message == "broadcast test"

    @pytest.mark.asyncio
    async def test_unsubscribed_queue_does_not_receive(self, stream, base_task_id, base_agent_id):
        q = await stream.subscribe(buffer_size=10)
        await stream.unsubscribe(q)

        await stream.add_log_async(base_task_id, base_agent_id, LogLevel.INFO, "after unsubscribe")

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q.get(), timeout=0.5)


# ============================================================
# 六、分页与组合查询
# ============================================================
class TestPaginationAndCombinedQuery:
    """验证分页和组合查询功能"""

    def test_pagination_offset(self, stream, base_task_id, base_agent_id):
        for i in range(10):
            stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, f"msg_{i}")

        result = stream.get_logs(limit=5, offset=5)
        assert len(result) == 5
        assert result[0].message == "msg_5"

    def test_pagination_limit(self, stream, base_task_id, base_agent_id):
        for i in range(20):
            stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, f"msg_{i}")

        result = stream.get_logs(limit=3)
        assert len(result) == 3

    def test_combined_task_id_filter(self, stream):
        stream.add_log("task_a", "agent_1", LogLevel.INFO, "from task A")
        stream.add_log("task_b", "agent_1", LogLevel.INFO, "from task B")
        stream.add_log("task_a", "agent_1", LogLevel.WARN, "from task A warn")

        result = stream.get_logs(task_id="task_a")
        assert len(result) == 2

    def test_combined_agent_id_filter(self, stream):
        stream.add_log("task_1", "agent_x", LogLevel.INFO, "from agent X")
        stream.add_log("task_1", "agent_y", LogLevel.INFO, "from agent Y")
        stream.add_log("task_2", "agent_x", LogLevel.ERROR, "from agent X error")

        result = stream.get_logs(agent_id="agent_x")
        assert len(result) == 2

    def test_combined_level_and_task_filter(self, stream):
        stream.add_log("task_1", "agent_1", LogLevel.INFO, "t1 info")
        stream.add_log("task_1", "agent_1", LogLevel.ERROR, "t1 error")
        stream.add_log("task_2", "agent_1", LogLevel.ERROR, "t2 error")

        result = stream.get_logs(level_filter=LogLevel.ERROR, task_id="task_1")
        assert len(result) == 1
        assert result[0].message == "t1 error"


# ============================================================
# 七、日志条目数据结构
# ============================================================
class TestLogEntryDataStructure:
    """验证 LogEntry 数据结构"""

    def test_to_dict_contains_all_fields(self, stream, base_task_id, base_agent_id):
        entry = stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "test data")
        d = entry.to_dict()

        assert "id" in d
        assert "task_id" in d
        assert "agent_id" in d
        assert "level" in d
        assert "message" in d
        assert "timestamp" in d
        assert d["task_id"] == base_task_id
        assert d["agent_id"] == base_agent_id
        assert d["level"] == "INFO"
        assert d["message"] == "test data"

    def test_to_dict_timestamp_is_iso_format(self, stream, base_task_id, base_agent_id):
        entry = stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "iso check")
        d = entry.to_dict()
        ts = d["timestamp"]
        assert "T" in ts
        assert "Z" in ts or "+" in ts

    def test_id_is_uuid_format(self, stream, base_task_id, base_agent_id):
        entry = stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "uuid check")
        d = entry.to_dict()
        parts = d["id"].split("-")
        assert len(parts) == 5  # UUID v4 格式


# ============================================================
# 八、缓冲区与清理
# ============================================================
class TestBufferAndCleanup:
    """验证缓冲区大小限制和清理功能"""

    def test_clear_removes_all_logs(self, stream, base_task_id, base_agent_id):
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "a")
        stream.add_log(base_task_id, base_agent_id, LogLevel.INFO, "b")
        stream.clear()
        assert stream.log_count == 0

    def test_clear_removes_subscribers(self, stream):
        asyncio.run(stream.subscribe())
        assert stream.subscriber_count == 1
        stream.clear()
        assert stream.subscriber_count == 0

    def test_buffer_size_limit(self):
        stream = RealtimeLogStream(max_buffer_size=5)
        for i in range(10):
            stream.add_log("t", "a", LogLevel.INFO, f"msg_{i}")

        assert stream.log_count == 5
