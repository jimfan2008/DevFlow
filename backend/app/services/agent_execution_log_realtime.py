"""
Agent 执行实时日志组件
支持实时日志推送、按时间排序、关键词搜索、日志级别筛选
"""

import asyncio
import uuid
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, List, AsyncGenerator, Callable
from enum import Enum


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
    """
    实时日志流组件
    - 维护内存中的日志缓冲
    - 支持异步生成器方式推送新日志
    - 支持按时间排序、关键词搜索、级别筛选
    """

    def __init__(self, max_buffer_size: int = 10000):
        self._logs: List[LogEntry] = []
        self._max_buffer_size = max_buffer_size
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self._running = False

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
        """
        异步生成器：持续产出新日志
        支持级别筛选和关键词过滤
        """
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
        """
        查询日志（非实时）
        支持级别筛选、关键词搜索、按时间排序、分页
        """
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
        """清空所有日志"""
        self._logs.clear()
        self._subscribers.clear()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class AgentExecutionLogService:
    """
    Agent 执行日志服务
    包装 RealtimeLogStream 提供业务层面的 API
    """

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
