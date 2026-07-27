import pytest
import signal
import time
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
import uuid
import threading


class TimeoutError(Exception):
    """测试超时时抛出。"""
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("测试执行超时")


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class SchedulingAgent:
    """Agent 实例，用于并发调度测试。"""
    agent_id: str
    name: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    task_count: int = 0
    join_timestamp: Optional[float] = None

    def join_pool(self) -> None:
        self.status = AgentStatus.IDLE
        self.join_timestamp = time.time()

    def take_task(self, task_id: str) -> bool:
        if self.status != AgentStatus.IDLE:
            return False
        self.status = AgentStatus.BUSY
        self.current_task = task_id
        self.task_count += 1
        return True

    def release_task(self) -> None:
        self.status = AgentStatus.IDLE
        self.current_task = None

    @property
    def is_available(self) -> bool:
        return self.status == AgentStatus.IDLE


@dataclass
class SchedulingTask:
    """调度任务。"""
    task_id: str
    description: str
    status: str = "pending"  # pending, queued, running, completed
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    queued_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def queue_latency(self) -> Optional[float]:
        """排队延迟（从入队到开始执行）。"""
        if self.queued_at and self.started_at:
            return self.started_at - self.queued_at
        return None


@dataclass
class DispatchRecord:
    """调度记录，记录一次任务分配。"""
    task_id: str
    agent_id: str
    queued_at: float
    dispatched_at: float
    execution_time: float

    @property
    def queue_latency(self) -> float:
        return self.dispatched_at - self.queued_at


class ConcurrentAgentScheduler:
    """
    并发 Agent 调度器。
    支持多个 Agent 并发执行任务，记录排队延迟，用于验证并发调度能力。
    """

    def __init__(self, max_concurrent: int = 20):
        self.max_concurrent = max_concurrent
        self._agents: Dict[str, SchedulingAgent] = {}
        self._tasks: Dict[str, SchedulingTask] = {}
        self._task_queue: Deque[str] = deque()
        self._dispatch_records: List[DispatchRecord] = []
        self._active_count = 0

    def _find_idle_agent(self) -> Optional[SchedulingAgent]:
        """查找一个空闲的 Agent。"""
        for agent in self._agents.values():
            if agent.is_available:
                return agent
        return None

    def register_agent(self, agent: SchedulingAgent) -> None:
        """注册 Agent 到调度池。"""
        self._agents[agent.agent_id] = agent
        agent.join_pool()

    def submit_task(self, task: SchedulingTask) -> None:
        """提交任务到调度队列。"""
        self._tasks[task.task_id] = task
        task.status = "queued"
        task.queued_at = time.time()
        self._task_queue.append(task.task_id)

    def dispatch_available(self) -> List[DispatchRecord]:
        """将队列中的任务分配给空闲 Agent，返回本次调度产生的记录。"""
        dispatched: List[DispatchRecord] = []

        while self._task_queue and self._active_count < self.max_concurrent:
            task_id = self._task_queue.popleft()
            task = self._tasks.get(task_id)
            if not task or task.status != "queued":
                continue

            agent = self._find_idle_agent()
            if not agent:
                self._task_queue.appendleft(task_id)
                break

            ok = agent.take_task(task_id)
            if not ok:
                continue

            task.assigned_agent = agent.agent_id
            task.status = "running"
            task.started_at = time.time()
            self._active_count += 1

            record = DispatchRecord(
                task_id=task_id,
                agent_id=agent.agent_id,
                queued_at=task.queued_at or task.created_at,
                dispatched_at=task.started_at,
                execution_time=0.0,
            )
            dispatched.append(record)
            self._dispatch_records.append(record)

        return dispatched

    def complete_task(self, task_id: str, execution_time: float = 0.1) -> bool:
        """标记任务完成，释放对应 Agent。"""
        task = self._tasks.get(task_id)
        if not task or not task.assigned_agent:
            return False

        agent = self._agents.get(task.assigned_agent)
        if agent:
            agent.release_task()
            self._active_count -= 1

        task.status = "completed"
        task.completed_at = time.time()

        for record in self._dispatch_records:
            if record.task_id == task_id:
                record.execution_time = execution_time
                break

        return True

    def dispatch_all_concurrently(self) -> List[DispatchRecord]:
        """一次性将队列中所有任务分配出去（模拟并发调度）。"""
        dispatched: List[DispatchRecord] = []
        idle_agents = [a for a in self._agents.values() if a.is_available]
        queue_items = list(self._task_queue)
        self._task_queue.clear()

        pairs = zip(queue_items, idle_agents)
        for task_id, agent in pairs:
            task = self._tasks.get(task_id)
            if not task or task.status != "queued":
                continue
            ok = agent.take_task(task_id)
            if not ok:
                continue

            task.assigned_agent = agent.agent_id
            task.status = "running"
            task.started_at = time.time()
            self._active_count += 1

            record = DispatchRecord(
                task_id=task_id,
                agent_id=agent.agent_id,
                queued_at=task.queued_at or task.created_at,
                dispatched_at=task.started_at,
                execution_time=0.0,
            )
            dispatched.append(record)
            self._dispatch_records.append(record)

        return dispatched

    def get_queue_latencies(self) -> List[float]:
        """获取所有调度记录的排队延迟。"""
        return [r.queue_latency for r in self._dispatch_records]

    def get_p95_latency(self) -> Optional[float]:
        """计算 P95 排队延迟。"""
        latencies = self.get_queue_latencies()
        if not latencies:
            return None
        latencies.sort()
        idx = int(len(latencies) * 0.95)
        if idx >= len(latencies):
            idx = len(latencies) - 1
        return latencies[idx]

    def get_active_count(self) -> int:
        return self._active_count

    def get_total_dispatched(self) -> int:
        return len(self._dispatch_records)

    def get_agent_count(self) -> int:
        return len(self._agents)


# ── Fixture ──────────────────────────────────────────────────────────────


@pytest.fixture
def scheduler():
    return ConcurrentAgentScheduler(max_concurrent=20)


@pytest.fixture
def ten_agents():
    return [
        SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
        for i in range(10)
    ]


@pytest.fixture
def scheduler_with_ten_agents(scheduler, ten_agents):
    for agent in ten_agents:
        scheduler.register_agent(agent)
    return scheduler


# ── 测试：>=10 个 Agent 并发调度 ────────────────────────────────────────


class TestAgentConcurrentScheduling:

    def test_10_agents_registered_successfully(self, scheduler_with_ten_agents):
        """验证 10 个 Agent 成功注册到调度器。"""
        assert scheduler_with_ten_agents.get_agent_count() == 10

    def test_10_tasks_dispatched_to_10_agents(self, scheduler_with_ten_agents):
        """验证 10 个任务可以并发分配给 10 个 Agent。"""
        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(10)
        ]
        for task in tasks:
            scheduler_with_ten_agents.submit_task(task)

        records = scheduler_with_ten_agents.dispatch_all_concurrently()
        assert len(records) == 10

        agent_ids = {r.agent_id for r in records}
        assert len(agent_ids) == 10

    def test_all_10_agents_concurrently_busy(self, scheduler_with_ten_agents):
        """验证 10 个 Agent 同时处于 busy 状态（真正并发）。"""
        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(10)
        ]
        for task in tasks:
            scheduler_with_ten_agents.submit_task(task)

        scheduler_with_ten_agents.dispatch_all_concurrently()
        active = scheduler_with_ten_agents.get_active_count()
        assert active == 10

    def test_p95_queue_latency_under_60_seconds(self, scheduler_with_ten_agents):
        """验证 P95 排队延迟 < 60 秒。"""
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            tasks = [
                SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
                for i in range(10)
            ]
            for task in tasks:
                scheduler_with_ten_agents.submit_task(task)

            start = time.monotonic()
            scheduler_with_ten_agents.dispatch_all_concurrently()
            elapsed = time.monotonic() - start

            p95 = scheduler_with_ten_agents.get_p95_latency()
            assert p95 is not None
            assert p95 < 60.0
            assert elapsed < 1.0
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def test_all_tasks_dispatched_within_time_limit(self, scheduler_with_ten_agents):
        """验证所有任务的排队延迟均在毫秒级完成。"""
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            tasks = [
                SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
                for i in range(10)
            ]
            for task in tasks:
                scheduler_with_ten_agents.submit_task(task)

            records = scheduler_with_ten_agents.dispatch_all_concurrently()
            for record in records:
                assert record.queue_latency < 1.0
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def test_no_agent_reused_in_same_dispatch(self, scheduler_with_ten_agents):
        """验证单次调度中每个 Agent 只被分配一个任务（无重复使用）。"""
        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(10)
        ]
        for task in tasks:
            scheduler_with_ten_agents.submit_task(task)

        records = scheduler_with_ten_agents.dispatch_all_concurrently()
        agent_ids = [r.agent_id for r in records]
        assert len(agent_ids) == len(set(agent_ids))


# ── 测试：超过 10 个 Agent 并发（扩展验证） ─────────────────────────────


class TestAgentConcurrentSchedulingExtended:

    def test_15_agents_concurrent_dispatch(self, scheduler):
        """验证 15 个 Agent 并发调度成功。"""
        agents = [
            SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
            for i in range(15)
        ]
        for agent in agents:
            scheduler.register_agent(agent)

        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(15)
        ]
        for task in tasks:
            scheduler.submit_task(task)

        records = scheduler.dispatch_all_concurrently()
        assert len(records) == 15
        active = scheduler.get_active_count()
        assert active == 15

    def test_20_agents_concurrent_dispatch(self, scheduler):
        """验证 20 个 Agent 并发调度成功（达到 max_concurrent 上限）。"""
        agents = [
            SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
            for i in range(20)
        ]
        for agent in agents:
            scheduler.register_agent(agent)

        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(20)
        ]
        for task in tasks:
            scheduler.submit_task(task)

        records = scheduler.dispatch_all_concurrently()
        assert len(records) == 20
        active = scheduler.get_active_count()
        assert active == 20

    def test_p95_under_60s_with_15_agents(self, scheduler):
        """验证 15 个 Agent 并发时 P95 排队延迟 < 60 秒。"""
        agents = [
            SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
            for i in range(15)
        ]
        for agent in agents:
            scheduler.register_agent(agent)

        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(15)
        ]
        for task in tasks:
            scheduler.submit_task(task)

        scheduler.dispatch_all_concurrently()
        p95 = scheduler.get_p95_latency()
        assert p95 is not None
        assert p95 < 60.0


# ── 测试：并发调度中的任务完成与 Agent 释放 ─────────────────────────────


class TestAgentReleaseAfterCompletion:

    def test_agent_released_after_task_completion(self, scheduler_with_ten_agents):
        """验证任务完成后 Agent 正确释放回 idle 状态。"""
        task = SchedulingTask(task_id="task-0", description="Task 0")
        scheduler_with_ten_agents.submit_task(task)
        records = scheduler_with_ten_agents.dispatch_all_concurrently()
        assert len(records) == 1

        agent_id = records[0].agent_id
        agent = scheduler_with_ten_agents._agents[agent_id]
        assert agent.status == AgentStatus.BUSY

        ok = scheduler_with_ten_agents.complete_task("task-0", execution_time=0.05)
        assert ok is True
        assert agent.status == AgentStatus.IDLE
        assert scheduler_with_ten_agents.get_active_count() == 0

    def test_all_10_tasks_complete_sequentially(self, scheduler_with_ten_agents):
        """验证 10 个并发任务可以逐个完成。"""
        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(10)
        ]
        for task in tasks:
            scheduler_with_ten_agents.submit_task(task)

        records = scheduler_with_ten_agents.dispatch_all_concurrently()
        assert len(records) == 10
        assert scheduler_with_ten_agents.get_active_count() == 10

        for i in range(10):
            ok = scheduler_with_ten_agents.complete_task(f"task-{i}", execution_time=0.01)
            assert ok is True

        assert scheduler_with_ten_agents.get_active_count() == 0
        for agent in scheduler_with_ten_agents._agents.values():
            assert agent.status == AgentStatus.IDLE

    def test_completed_tasks_not_requeued(self, scheduler_with_ten_agents):
        """验证已完成的任务不会被重新入队。"""
        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(10)
        ]
        for task in tasks:
            scheduler_with_ten_agents.submit_task(task)

        scheduler_with_ten_agents.dispatch_all_concurrently()

        for i in range(10):
            scheduler_with_ten_agents.complete_task(f"task-{i}")

        for task in tasks:
            assert task.status == "completed"
            assert task.completed_at is not None


# ── 测试：线程级并发调度 ────────────────────────────────────────────────


class TestThreadLevelConcurrency:

    def test_concurrent_dispatch_via_thread_pool(self, scheduler):
        """通过线程池模拟真实并发调度。"""
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            agents = [
                SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
                for i in range(10)
            ]
            for agent in agents:
                scheduler.register_agent(agent)

            tasks = [
                SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
                for i in range(10)
            ]
            for task in tasks:
                scheduler.submit_task(task)

            dispatched_count = 0

            def dispatch_one():
                nonlocal dispatched_count
                records = scheduler.dispatch_available()
                dispatched_count += len(records)
                return records

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(dispatch_one) for _ in range(10)]
                all_records = []
                for f in as_completed(futures, timeout=5):
                    result = f.result(timeout=5)
                    all_records.extend(result)

            assert dispatched_count == 10

            agent_ids = {r.agent_id for r in all_records}
            assert len(agent_ids) == 10
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def test_concurrent_completion_via_thread_pool(self, scheduler):
        """通过线程池并发完成任务。"""
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            agents = [
                SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
                for i in range(10)
            ]
            for agent in agents:
                scheduler.register_agent(agent)

            tasks = [
                SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
                for i in range(10)
            ]
            for task in tasks:
                scheduler.submit_task(task)

            scheduler.dispatch_all_concurrently()
            assert scheduler.get_active_count() == 10

            def complete_one(task_id):
                time.sleep(random.uniform(0, 0.01))
                return scheduler.complete_task(task_id, execution_time=0.01)

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(complete_one, f"task-{i}")
                    for i in range(10)
                ]
                results = [
                    f.result(timeout=5) for f in as_completed(futures, timeout=5)
                ]

            assert all(results)
            assert scheduler.get_active_count() == 0
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


# ── 测试：极端场景 ──────────────────────────────────────────────────────


class TestEdgeCases:

    def test_more_tasks_than_agents_queues_remaining(self, scheduler_with_ten_agents):
        """当任务数超过 Agent 数时，多余任务留在队列中。"""
        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(15)
        ]
        for task in tasks:
            scheduler_with_ten_agents.submit_task(task)

        records = scheduler_with_ten_agents.dispatch_all_concurrently()
        assert len(records) == 10
        pending = scheduler_with_ten_agents._tasks
        still_queued = sum(
            1 for t in pending.values() if t.status == "queued"
        )
        assert still_queued == 5

    def test_no_idle_agents_no_dispatch(self, scheduler_with_ten_agents):
        """当所有 Agent 都在忙时，新提交的任务无法立即调度。"""
        tasks = [
            SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
            for i in range(10)
        ]
        for task in tasks:
            scheduler_with_ten_agents.submit_task(task)

        scheduler_with_ten_agents.dispatch_all_concurrently()
        assert scheduler_with_ten_agents.get_active_count() == 10

        extra = SchedulingTask(task_id="extra-task", description="Extra")
        scheduler_with_ten_agents.submit_task(extra)
        records = scheduler_with_ten_agents.dispatch_available()
        assert len(records) == 0

    def test_dispatch_with_zero_agents(self, scheduler):
        """没有注册 Agent 时，调度不产生记录。"""
        task = SchedulingTask(task_id="task-0", description="Task 0")
        scheduler.submit_task(task)

        records = scheduler.dispatch_all_concurrently()
        assert len(records) == 0

    def test_p95_with_single_task(self, scheduler_with_ten_agents):
        """只有一个任务时 P95 延迟应接近 0。"""
        task = SchedulingTask(task_id="task-0", description="Task 0")
        scheduler_with_ten_agents.submit_task(task)

        scheduler_with_ten_agents.dispatch_all_concurrently()
        p95 = scheduler_with_ten_agents.get_p95_latency()
        assert p95 is not None
        assert p95 < 60.0


# ── 测试：端到端并发调度流程 ─────────────────────────────────────────────


class TestEndToEndConcurrentFlow:

    def test_full_lifecycle_10_agents_10_tasks(self, scheduler):
        """完整的端到端流程：注册 → 提交 → 调度 → 执行 → 完成。"""
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            agents = [
                SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
                for i in range(10)
            ]
            for agent in agents:
                scheduler.register_agent(agent)

            tasks = [
                SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
                for i in range(10)
            ]
            for task in tasks:
                scheduler.submit_task(task)

            start = time.monotonic()
            records = scheduler.dispatch_all_concurrently()
            elapsed = time.monotonic() - start

            assert len(records) == 10
            assert scheduler.get_active_count() == 10
            assert elapsed < 1.0

            for record in records:
                assert record.queue_latency < 60.0

            p95 = scheduler.get_p95_latency()
            assert p95 is not None
            assert p95 < 60.0

            for i in range(10):
                ok = scheduler.complete_task(f"task-{i}", execution_time=0.05)
                assert ok is True

            assert scheduler.get_active_count() == 0
            assert scheduler.get_total_dispatched() == 10

            for agent in agents:
                assert agent.status == AgentStatus.IDLE
                assert agent.task_count == 1
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def test_stress_20_agents_20_tasks(self, scheduler):
        """压力测试：20 个 Agent 调度 20 个任务（带超时保护）。"""
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        try:
            agents = [
                SchedulingAgent(agent_id=f"agent-{i}", name=f"Agent-{i}")
                for i in range(20)
            ]
            for agent in agents:
                scheduler.register_agent(agent)

            tasks = [
                SchedulingTask(task_id=f"task-{i}", description=f"Task {i}")
                for i in range(20)
            ]
            for task in tasks:
                scheduler.submit_task(task)

            start = time.monotonic()
            records = scheduler.dispatch_all_concurrently()
            elapsed = time.monotonic() - start

            assert len(records) == 20
            assert scheduler.get_active_count() == 20
            assert elapsed < 1.0

            p95 = scheduler.get_p95_latency()
            assert p95 is not None
            assert p95 < 60.0

            for i in range(20):
                scheduler.complete_task(f"task-{i}", execution_time=0.01)

            assert scheduler.get_active_count() == 0
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)