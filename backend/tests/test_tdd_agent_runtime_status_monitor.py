#!/usr/bin/env python3

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime, timezone

import pytest


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class AgentRuntimeInfo:
    agent_id: str
    agent_name: str
    status: AgentStatus
    current_task: Optional[str] = None
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    updated_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "current_task": self.current_task,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
        }


@dataclass
class HistoricalTask:
    task_id: str
    agent_id: str
    task_name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    cpu_peak: float = 0.0
    memory_peak: float = 0.0


class AgentRuntimeMonitor:
    def __init__(self):
        self._agents: Dict[str, AgentRuntimeInfo] = {}
        self._subscribers: List[asyncio.Queue] = []
        self._history: List[HistoricalTask] = []
        self._lock = asyncio.Lock()

    def register_agent(self, agent_id: str, agent_name: str) -> AgentRuntimeInfo:
        info = AgentRuntimeInfo(
            agent_id=agent_id,
            agent_name=agent_name,
            status=AgentStatus.IDLE,
        )
        self._agents[agent_id] = info
        return info

    def get_agent(self, agent_id: str) -> Optional[AgentRuntimeInfo]:
        return self._agents.get(agent_id)

    def get_all_agents(self) -> List[AgentRuntimeInfo]:
        return list(self._agents.values())

    def update_status(self, agent_id: str, status: AgentStatus, current_task: Optional[str] = None,
                      cpu_percent: Optional[float] = None, memory_percent: Optional[float] = None) -> Optional[AgentRuntimeInfo]:
        info = self._agents.get(agent_id)
        if info is None:
            return None
        info.status = status
        info.updated_at = time.monotonic()
        if current_task is not None:
            info.current_task = current_task
        if cpu_percent is not None:
            info.cpu_percent = cpu_percent
        if memory_percent is not None:
            info.memory_percent = memory_percent
        return info

    async def update_status_async(self, agent_id: str, status: AgentStatus, current_task: Optional[str] = None,
                                   cpu_percent: Optional[float] = None, memory_percent: Optional[float] = None) -> Optional[AgentRuntimeInfo]:
        result = self.update_status(agent_id, status, current_task, cpu_percent, memory_percent)
        await self._broadcast(agent_id)
        return result

    async def _broadcast(self, agent_id: str):
        dead = []
        for q in self._subscribers:
            try:
                info = self._agents.get(agent_id)
                if info:
                    q.put_nowait(AgentRuntimeInfo(
                        agent_id=info.agent_id,
                        agent_name=info.agent_name,
                        status=info.status,
                        current_task=info.current_task,
                        cpu_percent=info.cpu_percent,
                        memory_percent=info.memory_percent,
                        updated_at=info.updated_at,
                    ))
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)

    async def subscribe(self, buffer_size: int = 100) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=buffer_size)
        self._subscribers.append(q)
        return q

    async def unsubscribe(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def add_task_history(self, task: HistoricalTask):
        self._history.append(task)

    def query_task_history(self, agent_id: Optional[str] = None,
                           status_filter: Optional[str] = None,
                           sort_asc: bool = True,
                           limit: Optional[int] = None,
                           offset: int = 0) -> List[HistoricalTask]:
        result = self._history[:]
        if agent_id is not None:
            result = [t for t in result if t.agent_id == agent_id]
        if status_filter is not None:
            result = [t for t in result if t.status == status_filter]
        result.sort(key=lambda t: t.started_at, reverse=not sort_asc)
        if offset > 0:
            result = result[offset:]
        if limit is not None:
            result = result[:limit]
        return result

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @property
    def history_count(self) -> int:
        return len(self._history)


@pytest.fixture
def monitor():
    return AgentRuntimeMonitor()


@pytest.fixture
def sample_agents(monitor):
    a1 = monitor.register_agent("agent_001", "CodeGenerator")
    a2 = monitor.register_agent("agent_002", "TestRunner")
    a3 = monitor.register_agent("agent_003", "Deployer")
    return [a1, a2, a3]


class TestAgentRegistration:
    def test_register_agent_returns_info(self, monitor):
        info = monitor.register_agent("a1", "AgentOne")
        assert info.agent_id == "a1"
        assert info.agent_name == "AgentOne"
        assert info.status == AgentStatus.IDLE

    def test_register_multiple_agents(self, monitor, sample_agents):
        assert monitor.agent_count == 3

    def test_get_agent_by_id(self, monitor, sample_agents):
        info = monitor.get_agent("agent_002")
        assert info is not None
        assert info.agent_name == "TestRunner"

    def test_get_nonexistent_agent(self, monitor):
        info = monitor.get_agent("nonexistent")
        assert info is None

    def test_get_all_agents(self, monitor, sample_agents):
        all_agents = monitor.get_all_agents()
        assert len(all_agents) == 3

    def test_agent_default_values(self, monitor):
        info = monitor.register_agent("a_default", "DefaultAgent")
        assert info.current_task is None
        assert info.cpu_percent == 0.0
        assert info.memory_percent == 0.0


class TestStatusUpdate:
    def test_update_to_running(self, monitor, sample_agents):
        monitor.update_status("agent_001", AgentStatus.RUNNING, current_task="generate code")
        info = monitor.get_agent("agent_001")
        assert info.status == AgentStatus.RUNNING
        assert info.current_task == "generate code"

    def test_update_to_waiting(self, monitor, sample_agents):
        monitor.update_status("agent_002", AgentStatus.WAITING, current_task="waiting for input")
        info = monitor.get_agent("agent_002")
        assert info.status == AgentStatus.WAITING

    def test_update_to_error(self, monitor, sample_agents):
        monitor.update_status("agent_003", AgentStatus.ERROR, current_task="deploy failed")
        info = monitor.get_agent("agent_003")
        assert info.status == AgentStatus.ERROR

    def test_update_to_idle(self, monitor, sample_agents):
        monitor.update_status("agent_001", AgentStatus.RUNNING)
        monitor.update_status("agent_001", AgentStatus.IDLE)
        info = monitor.get_agent("agent_001")
        assert info.status == AgentStatus.IDLE

    def test_update_nonexistent_agent(self, monitor):
        result = monitor.update_status("no_such_agent", AgentStatus.RUNNING)
        assert result is None

    def test_update_cpu_and_memory(self, monitor, sample_agents):
        monitor.update_status("agent_001", AgentStatus.RUNNING, cpu_percent=45.5, memory_percent=62.3)
        info = monitor.get_agent("agent_001")
        assert info.cpu_percent == 45.5
        assert info.memory_percent == 62.3

    def test_update_without_changing_resources(self, monitor, sample_agents):
        monitor.update_status("agent_001", AgentStatus.RUNNING, cpu_percent=30.0, memory_percent=50.0)
        monitor.update_status("agent_001", AgentStatus.WAITING)
        info = monitor.get_agent("agent_001")
        assert info.status == AgentStatus.WAITING
        assert info.cpu_percent == 30.0
        assert info.memory_percent == 50.0

    def test_status_round_trip_all_states(self, monitor, sample_agents):
        aid = "agent_001"
        for status in AgentStatus:
            monitor.update_status(aid, status)
            assert monitor.get_agent(aid).status == status

    def test_updated_at_changes_on_update(self, monitor, sample_agents):
        info = monitor.get_agent("agent_001")
        old_ts = info.updated_at
        time.sleep(0.001)
        monitor.update_status("agent_001", AgentStatus.RUNNING)
        assert info.updated_at > old_ts


class TestStatusUpdateDelay:
    @pytest.mark.asyncio
    async def test_status_update_delay_within_5_seconds(self, monitor, sample_agents):
        q = await monitor.subscribe(buffer_size=100)
        start = time.monotonic()
        await monitor.update_status_async("agent_001", AgentStatus.RUNNING, current_task="heavy task")
        received = await asyncio.wait_for(q.get(), timeout=5.0)
        elapsed = time.monotonic() - start
        assert received.agent_id == "agent_001"
        assert received.status == AgentStatus.RUNNING
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_multiple_updates_all_within_5_seconds(self, monitor, sample_agents):
        q = await monitor.subscribe(buffer_size=100)
        max_elapsed = 0.0
        for i, status in enumerate([AgentStatus.RUNNING, AgentStatus.WAITING, AgentStatus.IDLE, AgentStatus.ERROR]):
            start = time.monotonic()
            await monitor.update_status_async("agent_001", status, current_task=f"task_{i}")
            received = await asyncio.wait_for(q.get(), timeout=5.0)
            elapsed = time.monotonic() - start
            max_elapsed = max(max_elapsed, elapsed)
        assert max_elapsed < 5.0

    @pytest.mark.asyncio
    async def test_concurrent_agents_all_receive_updates(self, monitor, sample_agents):
        q = await monitor.subscribe(buffer_size=200)
        async def update_agent(aid):
            await monitor.update_status_async(aid, AgentStatus.RUNNING, current_task=f"task_{aid}")
        start = time.monotonic()
        await asyncio.gather(update_agent("agent_001"), update_agent("agent_002"), update_agent("agent_003"))
        received = []
        for _ in range(3):
            info = await asyncio.wait_for(q.get(), timeout=5.0)
            received.append(info)
        elapsed = time.monotonic() - start
        assert len(received) == 3
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_subscriber_receives_all_updates_in_order(self, monitor, sample_agents):
        q = await monitor.subscribe(buffer_size=100)
        statuses = [AgentStatus.RUNNING, AgentStatus.WAITING, AgentStatus.ERROR, AgentStatus.IDLE]
        for s in statuses:
            await monitor.update_status_async("agent_001", s)
        for expected in statuses:
            received = await asyncio.wait_for(q.get(), timeout=5.0)
            assert received.status == expected


class TestStatusFields:
    def test_to_dict_contains_all_fields(self, monitor, sample_agents):
        monitor.update_status("agent_001", AgentStatus.RUNNING, current_task="build",
                              cpu_percent=55.0, memory_percent=70.0)
        info = monitor.get_agent("agent_001")
        d = info.to_dict()
        assert "agent_id" in d
        assert "agent_name" in d
        assert "status" in d
        assert "current_task" in d
        assert "cpu_percent" in d
        assert "memory_percent" in d
        assert d["agent_id"] == "agent_001"
        assert d["agent_name"] == "CodeGenerator"
        assert d["status"] == "running"
        assert d["current_task"] == "build"
        assert d["cpu_percent"] == 55.0
        assert d["memory_percent"] == 70.0

    def test_agent_name_preserved(self, monitor, sample_agents):
        info = monitor.get_agent("agent_001")
        assert info.agent_name == "CodeGenerator"

    def test_status_enum_values(self):
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.WAITING.value == "waiting"
        assert AgentStatus.ERROR.value == "error"


class TestTaskHistory:
    def test_add_task_record(self, monitor):
        task = HistoricalTask(
            task_id="task_100",
            agent_id="agent_001",
            task_name="code review",
            status="completed",
            started_at=datetime.now(timezone.utc),
        )
        monitor.add_task_history(task)
        assert monitor.history_count == 1

    def test_query_history_by_agent(self, monitor):
        t1 = HistoricalTask("t1", "agent_001", "build", "completed", datetime.now(timezone.utc))
        t2 = HistoricalTask("t2", "agent_002", "test", "failed", datetime.now(timezone.utc))
        t3 = HistoricalTask("t3", "agent_001", "deploy", "completed", datetime.now(timezone.utc))
        monitor.add_task_history(t1)
        monitor.add_task_history(t2)
        monitor.add_task_history(t3)

        result = monitor.query_task_history(agent_id="agent_001")
        assert len(result) == 2

    def test_query_history_by_status(self, monitor):
        t1 = HistoricalTask("t1", "agent_001", "build", "completed", datetime.now(timezone.utc))
        t2 = HistoricalTask("t2", "agent_002", "test", "failed", datetime.now(timezone.utc))
        monitor.add_task_history(t1)
        monitor.add_task_history(t2)

        result = monitor.query_task_history(status_filter="failed")
        assert len(result) == 1
        assert result[0].task_id == "t2"

    def test_query_history_sort_descending(self, monitor):
        now = datetime.now(timezone.utc)
        t1 = HistoricalTask("t1", "agent_001", "first", "completed", now)
        t2 = HistoricalTask("t2", "agent_001", "second", "completed",
                            datetime.fromtimestamp(now.timestamp() + 10, tz=timezone.utc))
        monitor.add_task_history(t1)
        monitor.add_task_history(t2)

        result = monitor.query_task_history(sort_asc=False)
        assert result[0].task_id == "t2"
        assert result[1].task_id == "t1"

    def test_query_history_pagination(self, monitor):
        for i in range(20):
            t = HistoricalTask(f"t{i}", "agent_001", f"task_{i}", "completed",
                               datetime.now(timezone.utc))
            monitor.add_task_history(t)

        result = monitor.query_task_history(limit=5, offset=10)
        assert len(result) == 5

    def test_query_history_with_all_filters(self, monitor):
        t1 = HistoricalTask("t1", "agent_001", "build", "completed", datetime.now(timezone.utc))
        t2 = HistoricalTask("t2", "agent_001", "build", "failed", datetime.now(timezone.utc))
        t3 = HistoricalTask("t3", "agent_002", "build", "completed", datetime.now(timezone.utc))
        monitor.add_task_history(t1)
        monitor.add_task_history(t2)
        monitor.add_task_history(t3)

        result = monitor.query_task_history(agent_id="agent_001", status_filter="completed")
        assert len(result) == 1
        assert result[0].task_id == "t1"


class TestTaskHistoryQueryPerformance:
    def test_query_response_within_2_seconds(self, monitor):
        now = datetime.now(timezone.utc)
        for i in range(1000):
            t = HistoricalTask(f"t{i}", "agent_001" if i % 2 == 0 else "agent_002",
                               f"task_{i}", "completed" if i % 3 == 0 else "failed",
                               datetime.fromtimestamp(now.timestamp() + i))
            monitor.add_task_history(t)

        start = time.monotonic()
        result = monitor.query_task_history(agent_id="agent_001", status_filter="completed", limit=10)
        elapsed = time.monotonic() - start
        assert len(result) > 0
        assert elapsed < 2.0

    def test_query_all_history_within_2_seconds(self, monitor):
        now = datetime.now(timezone.utc)
        for i in range(1000):
            t = HistoricalTask(f"t{i}", "agent_001", f"task_{i}", "completed",
                               datetime.fromtimestamp(now.timestamp() + i))
            monitor.add_task_history(t)

        start = time.monotonic()
        result = monitor.query_task_history()
        elapsed = time.monotonic() - start
        assert len(result) == 1000
        assert elapsed < 2.0

    def test_query_with_pagination_within_2_seconds(self, monitor):
        now = datetime.now(timezone.utc)
        for i in range(1000):
            t = HistoricalTask(f"t{i}", "agent_001", f"task_{i}", "completed",
                               datetime.fromtimestamp(now.timestamp() + i))
            monitor.add_task_history(t)

        start = time.monotonic()
        result = monitor.query_task_history(agent_id="agent_001", sort_asc=False, limit=50, offset=200)
        elapsed = time.monotonic() - start
        assert len(result) == 50
        assert elapsed < 2.0

    def test_concurrent_query_performance(self, monitor):
        now = datetime.now(timezone.utc)
        for i in range(500):
            t = HistoricalTask(f"t{i}", "agent_001", f"task_{i}", "completed",
                               datetime.fromtimestamp(now.timestamp() + i))
            monitor.add_task_history(t)

        start = time.monotonic()
        r1 = monitor.query_task_history(agent_id="agent_001", limit=10)
        r2 = monitor.query_task_history(status_filter="completed", limit=10)
        r3 = monitor.query_task_history(sort_asc=False, limit=10)
        elapsed = time.monotonic() - start
        assert len(r1) > 0
        assert len(r2) > 0
        assert len(r3) > 0
        assert elapsed < 2.0


class TestSubscription:
    @pytest.mark.asyncio
    async def test_subscribe_increases_count(self, monitor, sample_agents):
        assert monitor.subscriber_count == 0
        q = await monitor.subscribe()
        assert monitor.subscriber_count == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_decreases_count(self, monitor, sample_agents):
        q = await monitor.subscribe()
        assert monitor.subscriber_count == 1
        await monitor.unsubscribe(q)
        assert monitor.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, monitor, sample_agents):
        q1 = await monitor.subscribe()
        q2 = await monitor.subscribe()
        q3 = await monitor.subscribe()
        assert monitor.subscriber_count == 3
        await monitor.unsubscribe(q2)
        assert monitor.subscriber_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_subscribers(self, monitor, sample_agents):
        q1 = await monitor.subscribe(buffer_size=10)
        q2 = await monitor.subscribe(buffer_size=10)
        await monitor.update_status_async("agent_001", AgentStatus.RUNNING)
        e1 = await asyncio.wait_for(q1.get(), timeout=5.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=5.0)
        assert e1.status == AgentStatus.RUNNING
        assert e2.status == AgentStatus.RUNNING

    @pytest.mark.asyncio
    async def test_unsubscribed_queue_does_not_receive(self, monitor, sample_agents):
        q = await monitor.subscribe(buffer_size=10)
        await monitor.unsubscribe(q)
        await monitor.update_status_async("agent_001", AgentStatus.RUNNING)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q.get(), timeout=0.5)

    @pytest.mark.asyncio
    async def test_subscriber_counter_agents(self, monitor, sample_agents):
        q = await monitor.subscribe(buffer_size=100)
        await monitor.update_status_async("agent_001", AgentStatus.RUNNING, cpu_percent=80.0, memory_percent=90.0)
        info = await asyncio.wait_for(q.get(), timeout=5.0)
        assert info.cpu_percent == 80.0
        assert info.memory_percent == 90.0


class TestAgentInfoDataStructure:
    def test_agent_info_to_dict(self, monitor, sample_agents):
        info = monitor.get_agent("agent_001")
        d = info.to_dict()
        assert isinstance(d["cpu_percent"], float)
        assert isinstance(d["memory_percent"], float)

    def test_all_agent_fields_present(self, monitor, sample_agents):
        info = monitor.get_agent("agent_001")
        d = info.to_dict()
        expected_keys = {"agent_id", "agent_name", "status", "current_task", "cpu_percent", "memory_percent"}
        assert set(d.keys()) == expected_keys

    def test_task_history_fields(self):
        now = datetime.now(timezone.utc)
        task = HistoricalTask("tid", "aid", "test build", "completed", now,
                              datetime.fromtimestamp(now.timestamp() + 100), 95.5, 88.3)
        assert task.task_id == "tid"
        assert task.agent_id == "aid"
        assert task.task_name == "test build"
        assert task.status == "completed"
        assert task.cpu_peak == 95.5
        assert task.memory_peak == 88.3
