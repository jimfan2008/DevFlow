import pytest
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class SwarmAgent:
    agent_id: str
    name: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    last_updated: float = field(default_factory=time.time)
    task_count: int = 0

    def update_status(self, status: AgentStatus, task: Optional[str] = None) -> None:
        self.status = status
        self.current_task = task
        self.last_updated = time.time()
        if status == AgentStatus.BUSY:
            self.task_count += 1


@dataclass
class SwarmTask:
    task_id: str
    description: str
    assigned_agent: Optional[str] = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class SwarmMonitor:
    def __init__(self, agents: Optional[List[SwarmAgent]] = None):
        self.agents: Dict[str, SwarmAgent] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.task_queue: List[str] = []
        self._status_history: Dict[str, list] = {}
        self._callbacks: List[Callable] = []
        if agents:
            for agent in agents:
                self.agents[agent.agent_id] = agent
                self._status_history[agent.agent_id] = []

    def register_agent(self, agent: SwarmAgent) -> None:
        self.agents[agent.agent_id] = agent
        self._status_history[agent.agent_id] = []

    def remove_agent(self, agent_id: str) -> None:
        self.agents.pop(agent_id, None)
        self._status_history.pop(agent_id, None)

    def add_task(self, task: SwarmTask) -> None:
        self.tasks[task.task_id] = task
        self.task_queue.append(task.task_id)

    def dispatch_task(self, task_id: str, agent_id: str) -> bool:
        task = self.tasks.get(task_id)
        agent = self.agents.get(agent_id)
        if not task or not agent:
            return False
        if agent.status != AgentStatus.IDLE:
            return False
        agent.update_status(AgentStatus.BUSY, task.description)
        task.assigned_agent = agent_id
        task.status = "running"
        task.started_at = time.time()
        self.task_queue.remove(task_id)
        self._record_status(agent_id, agent.status)
        self._notify()
        return True

    def complete_task(self, task_id: str) -> bool:
        for agent in self.agents.values():
            if agent.current_task and any(
                t.task_id == task_id for t in [self.tasks.get(task_id)]
            ):
                task = self.tasks[task_id]
                task.status = "completed"
                task.completed_at = time.time()
                agent.update_status(AgentStatus.IDLE)
                self._record_status(agent.agent_id, agent.status)
                self._notify()
                return True
        task = self.tasks.get(task_id)
        if task:
            task.status = "completed"
            task.completed_at = time.time()
        return True

    def mark_agent_offline(self, agent_id: str) -> None:
        agent = self.agents.get(agent_id)
        if agent:
            agent.update_status(AgentStatus.OFFLINE)
            self._record_status(agent_id, AgentStatus.OFFLINE)
            self._notify()

    def bring_agent_online(self, agent_id: str) -> None:
        agent = self.agents.get(agent_id)
        if agent and agent.status == AgentStatus.OFFLINE:
            agent.update_status(AgentStatus.IDLE)
            self._record_status(agent_id, AgentStatus.IDLE)
            self._notify()

    def get_active_count(self) -> int:
        return sum(
            1 for a in self.agents.values() if a.status == AgentStatus.BUSY
        )

    def get_parallelism(self) -> int:
        return self.get_active_count()

    def get_status_summary(self) -> Dict[str, int]:
        summary = {s.value: 0 for s in AgentStatus}
        for agent in self.agents.values():
            summary[agent.status.value] += 1
        return summary

    def get_task_distribution(self) -> Dict[str, list]:
        dist: Dict[str, list] = {}
        for agent in self.agents.values():
            dist[agent.agent_id] = []
        for task in self.tasks.values():
            if task.assigned_agent:
                if task.assigned_agent not in dist:
                    dist[task.assigned_agent] = []
                dist[task.assigned_agent].append(task.task_id)
        return dist

    def get_pending_tasks(self) -> List[SwarmTask]:
        return [
            t for t in self.tasks.values()
            if t.status == "pending"
        ]

    def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        agent = self.agents.get(agent_id)
        return agent.status if agent else None

    def get_recent_status_changes(
        self, agent_id: str, window_seconds: float = 60
    ) -> List[tuple]:
        now = time.time()
        raw = self._status_history.get(agent_id, [])
        return [
            (ts, s) for ts, s in raw
            if now - ts <= window_seconds
        ]

    def _record_status(self, agent_id: str, status: AgentStatus) -> None:
        if agent_id in self._status_history:
            self._status_history[agent_id].append((time.time(), status))

    def on_status_change(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def _notify(self) -> None:
        for cb in self._callbacks:
            try:
                cb(self)
            except Exception:
                pass

    def get_status_staleness(self, agent_id: str) -> Optional[float]:
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        return time.time() - agent.last_updated


@pytest.fixture
def sample_agents():
    return [
        SwarmAgent(agent_id="agent-1", name="Alpha"),
        SwarmAgent(agent_id="agent-2", name="Beta"),
        SwarmAgent(agent_id="agent-3", name="Gamma"),
    ]


@pytest.fixture
def monitor(sample_agents):
    return SwarmMonitor(agents=sample_agents)


@pytest.fixture
def populated_monitor(monitor):
    tasks = [
        SwarmTask(task_id="task-1", description="Analyze logs"),
        SwarmTask(task_id="task-2", description="Generate report"),
        SwarmTask(task_id="task-3", description="Scan network"),
        SwarmTask(task_id="task-4", description="Backup database"),
    ]
    for task in tasks:
        monitor.add_task(task)
    return monitor


class TestSwarmInitialization:
    def test_create_monitor_with_agents(self, sample_agents):
        m = SwarmMonitor(agents=sample_agents)
        assert len(m.agents) == 3
        assert all(a.agent_id in m.agents for a in sample_agents)

    def test_create_empty_monitor(self):
        m = SwarmMonitor()
        assert len(m.agents) == 0

    def test_register_agent(self, monitor):
        agent = SwarmAgent(agent_id="agent-4", name="Delta")
        monitor.register_agent(agent)
        assert "agent-4" in monitor.agents
        assert monitor.agents["agent-4"].name == "Delta"

    def test_remove_agent(self, monitor):
        monitor.remove_agent("agent-1")
        assert "agent-1" not in monitor.agents

    def test_initial_status_all_idle(self, monitor):
        for agent in monitor.agents.values():
            assert agent.status == AgentStatus.IDLE


class TestSwarmParallelism:
    def test_initial_parallelism_zero(self, monitor):
        assert monitor.get_parallelism() == 0

    def test_parallelism_increases_on_dispatch(self, populated_monitor):
        result = populated_monitor.dispatch_task("task-1", "agent-1")
        assert result is True
        assert populated_monitor.get_parallelism() == 1

    def test_parallelism_multiple_agents(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.dispatch_task("task-2", "agent-2")
        assert populated_monitor.get_parallelism() == 2

    def test_parallelism_decreases_on_completion(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.dispatch_task("task-2", "agent-2")
        populated_monitor.complete_task("task-1")
        assert populated_monitor.get_parallelism() == 1

    def test_parallelism_all_complete(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.dispatch_task("task-2", "agent-2")
        populated_monitor.dispatch_task("task-3", "agent-3")
        populated_monitor.complete_task("task-1")
        populated_monitor.complete_task("task-2")
        populated_monitor.complete_task("task-3")
        assert populated_monitor.get_parallelism() == 0

    def test_busy_agent_rejects_dispatch(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        result = populated_monitor.dispatch_task("task-2", "agent-1")
        assert result is False
        assert populated_monitor.get_parallelism() == 1

    def test_parallelism_ignores_offline(self, populated_monitor):
        populated_monitor.mark_agent_offline("agent-1")
        assert populated_monitor.get_parallelism() == 0


class TestTaskDistribution:
    def test_task_distribution_empty(self, monitor):
        dist = monitor.get_task_distribution()
        assert all(len(tasks) == 0 for tasks in dist.values())

    def test_task_distribution_after_dispatch(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        dist = populated_monitor.get_task_distribution()
        assert "task-1" in dist["agent-1"]

    def test_task_distribution_multi_agent(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.dispatch_task("task-2", "agent-2")
        dist = populated_monitor.get_task_distribution()
        assert "task-1" in dist["agent-1"]
        assert "task-2" in dist["agent-2"]

    def test_task_distribution_after_completion(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.complete_task("task-1")
        dist = populated_monitor.get_task_distribution()
        assert "task-1" in dist["agent-1"]

    def test_pending_tasks(self, populated_monitor):
        pending = populated_monitor.get_pending_tasks()
        assert len(pending) == 4

    def test_pending_tasks_after_dispatch(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        pending = populated_monitor.get_pending_tasks()
        assert len(pending) == 3
        assert all(t.status == "pending" for t in pending)

    def test_new_agents_in_distribution(self, monitor):
        monitor.add_task(SwarmTask(task_id="t1", description="test"))
        agent = SwarmAgent(agent_id="new-agent", name="NewOne")
        monitor.register_agent(agent)
        dist = monitor.get_task_distribution()
        assert "new-agent" in dist


class TestAgentStatusRealtime:
    def test_status_starts_idle(self, monitor):
        assert monitor.get_agent_status("agent-1") == AgentStatus.IDLE

    def test_status_changes_to_busy(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        assert populated_monitor.get_agent_status("agent-1") == AgentStatus.BUSY

    def test_status_returns_to_idle(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.complete_task("task-1")
        assert populated_monitor.get_agent_status("agent-1") == AgentStatus.IDLE

    def test_status_offline(self, monitor):
        monitor.mark_agent_offline("agent-1")
        assert monitor.get_agent_status("agent-1") == AgentStatus.OFFLINE

    def test_status_offline_to_idle(self, monitor):
        monitor.mark_agent_offline("agent-1")
        monitor.bring_agent_online("agent-1")
        assert monitor.get_agent_status("agent-1") == AgentStatus.IDLE

    def test_unknown_agent_returns_none(self, monitor):
        assert monitor.get_agent_status("ghost") is None

    def test_all_statuses_tracked(self, monitor, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        monitor.mark_agent_offline("agent-3")
        summary = monitor.get_status_summary()
        assert summary["busy"] == 1
        assert summary["idle"] == 1
        assert summary["offline"] == 1

    def test_busy_agent_has_task_info(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        agent = populated_monitor.agents["agent-1"]
        assert agent.current_task == "Analyze logs"

    def test_idle_agent_no_task(self, monitor):
        agent = monitor.agents["agent-1"]
        assert agent.current_task is None


class TestStatusUpdateLatency:
    def test_last_updated_on_idle(self, monitor):
        before = time.time()
        agent = monitor.agents["agent-1"]
        assert agent.last_updated >= before - 0.1

    def test_last_updated_on_status_change(self, populated_monitor):
        before = time.time()
        populated_monitor.dispatch_task("task-1", "agent-1")
        agent = populated_monitor.agents["agent-1"]
        assert agent.last_updated >= before
        assert time.time() - agent.last_updated <= 5

    def test_latency_within_five_seconds(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        staleness = populated_monitor.get_status_staleness("agent-1")
        assert staleness is not None
        assert staleness <= 5

    def test_staleness_offline(self, monitor):
        before = time.time()
        monitor.mark_agent_offline("agent-1")
        staleness = monitor.get_status_staleness("agent-1")
        assert staleness is not None
        assert staleness <= 5

    def test_staleness_unknown_agent(self, monitor):
        assert monitor.get_status_staleness("nobody") is None

    def test_recent_status_changes_count(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.complete_task("task-1")
        changes = populated_monitor.get_recent_status_changes("agent-1", 300)
        assert len(changes) >= 2

    def test_recent_status_changes_outside_window(self, populated_monitor):
        changes = populated_monitor.get_recent_status_changes("agent-1", -1)
        assert len(changes) == 0

    def test_task_count_increments(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.complete_task("task-1")
        populated_monitor.dispatch_task("task-2", "agent-1")
        assert populated_monitor.agents["agent-1"].task_count == 2


class TestSwarmTaskLifecycle:
    def test_add_task(self, monitor):
        task = SwarmTask(task_id="new-task", description="test")
        monitor.add_task(task)
        assert "new-task" in monitor.tasks

    def test_dispatch_sets_task_running(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        assert populated_monitor.tasks["task-1"].status == "running"

    def test_complete_task_updates_status(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.complete_task("task-1")
        assert populated_monitor.tasks["task-1"].status == "completed"

    def test_complete_task_sets_timestamp(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        before = time.time()
        populated_monitor.complete_task("task-1")
        assert populated_monitor.tasks["task-1"].completed_at is not None
        assert populated_monitor.tasks["task-1"].completed_at >= before - 0.1

    def test_dispatch_to_offline_agent_fails(self, monitor):
        monitor.mark_agent_offline("agent-1")
        task = SwarmTask(task_id="t1", description="test")
        monitor.add_task(task)
        result = monitor.dispatch_task("t1", "agent-1")
        assert result is False

    def test_complete_unassigned_task(self, monitor):
        task = SwarmTask(task_id="orphan", description="lost")
        monitor.add_task(task)
        result = monitor.complete_task("orphan")
        assert result is True
        assert monitor.tasks["orphan"].status == "completed"

    def test_dispatch_nonexistent_task(self, monitor):
        result = monitor.dispatch_task("no-such-task", "agent-1")
        assert result is False

    def test_dispatch_to_nonexistent_agent(self, populated_monitor):
        result = populated_monitor.dispatch_task("task-1", "ghost")
        assert result is False

    def test_task_queue_order(self, populated_monitor):
        assert populated_monitor.task_queue == ["task-1", "task-2", "task-3", "task-4"]

    def test_task_removed_from_queue_on_dispatch(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        assert "task-1" not in populated_monitor.task_queue

    def test_task_can_be_redispatched_after_completion(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.complete_task("task-1")
        populated_monitor.dispatch_task("task-2", "agent-1")
        assert populated_monitor.agents["agent-1"].status == AgentStatus.BUSY

    def test_all_tasks_dispatched_eventually(self, populated_monitor):
        agents = list(populated_monitor.agents.keys())
        for i, tid in enumerate(["task-1", "task-2", "task-3", "task-4"]):
            populated_monitor.dispatch_task(tid, agents[i % len(agents)])
        for tid in ["task-1", "task-2", "task-3", "task-4"]:
            assert populated_monitor.tasks[tid].status == "running"

    def test_dispatch_returns_false_when_all_busy(self, populated_monitor):
        for agent_id in populated_monitor.agents:
            populated_monitor.mark_agent_offline(agent_id)
        result = populated_monitor.dispatch_task("task-1", "agent-1")
        assert result is False


class TestCallbackNotification:
    def test_callback_invoked_on_dispatch(self, populated_monitor):
        invoked = []
        def cb(swarm):
            invoked.append(True)
        populated_monitor.on_status_change(cb)
        populated_monitor.dispatch_task("task-1", "agent-1")
        assert len(invoked) == 1

    def test_callback_invoked_on_completion(self, populated_monitor):
        invoked = []
        def cb(swarm):
            invoked.append(True)
        populated_monitor.on_status_change(cb)
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.complete_task("task-1")
        assert len(invoked) >= 2

    def test_callback_invoked_on_offline(self, monitor):
        invoked = []
        def cb(swarm):
            invoked.append(True)
        monitor.on_status_change(cb)
        monitor.mark_agent_offline("agent-1")
        assert len(invoked) == 1

    def test_callback_invoked_on_online(self, monitor):
        monitor.mark_agent_offline("agent-1")
        invoked = []
        def cb(swarm):
            invoked.append(True)
        monitor.on_status_change(cb)
        monitor.bring_agent_online("agent-1")
        assert len(invoked) == 1

    def test_multiple_callbacks(self, populated_monitor):
        invoked = []
        def cb1(swarm):
            invoked.append("cb1")
        def cb2(swarm):
            invoked.append("cb2")
        populated_monitor.on_status_change(cb1)
        populated_monitor.on_status_change(cb2)
        populated_monitor.dispatch_task("task-1", "agent-1")
        assert invoked == ["cb1", "cb2"]

    def test_callback_error_does_not_crash(self, populated_monitor):
        def cb(swarm):
            raise RuntimeError("boom")
        populated_monitor.on_status_change(cb)
        populated_monitor.dispatch_task("task-1", "agent-1")


class TestConcurrencySimulation:
    @pytest.mark.asyncio
    async def test_concurrent_dispatch_and_complete(self, populated_monitor):
        async def worker(agent_id, task_id, delay):
            populated_monitor.dispatch_task(task_id, agent_id)
            await asyncio.sleep(delay)
            populated_monitor.complete_task(task_id)
        await asyncio.gather(
            worker("agent-1", "task-1", 0.05),
            worker("agent-2", "task-2", 0.03),
            worker("agent-3", "task-3", 0.07),
        )
        assert populated_monitor.get_parallelism() == 0
        dist = populated_monitor.get_task_distribution()
        assert len(dist["agent-1"]) >= 1
        assert len(dist["agent-2"]) >= 1
        assert len(dist["agent-3"]) >= 1

    @pytest.mark.asyncio
    async def test_parallelism_peaks_correctly(self, populated_monitor):
        populated_monitor.dispatch_task("task-1", "agent-1")
        populated_monitor.dispatch_task("task-2", "agent-2")
        assert populated_monitor.get_parallelism() == 2
        await asyncio.sleep(0.01)
        populated_monitor.complete_task("task-1")
        await asyncio.sleep(0.01)
        assert populated_monitor.get_parallelism() == 1

    @pytest.mark.asyncio
    async def test_rapid_status_changes(self, populated_monitor):
        for i in range(10):
            populated_monitor.dispatch_task("task-1", "agent-1")
            populated_monitor.complete_task("task-1")
            populated_monitor.dispatch_task("task-2", "agent-2")
            populated_monitor.complete_task("task-2")
        await asyncio.sleep(0.01)
        assert populated_monitor.agents["agent-1"].task_count == 10
        assert populated_monitor.agents["agent-2"].task_count == 10

    @pytest.mark.asyncio
    async def test_status_latency_under_load(self, populated_monitor):
        async def hammer(agent_id, base_task_id, count):
            for i in range(count):
                tid = f"{base_task_id}-{i}"
                populated_monitor.add_task(
                    SwarmTask(task_id=tid, description=f"task {i}")
                )
                populated_monitor.dispatch_task(tid, agent_id)
                populated_monitor.complete_task(tid)
                await asyncio.sleep(0.005)
        await asyncio.gather(
            hammer("agent-1", "a", 5),
            hammer("agent-2", "b", 5),
        )
        assert populated_monitor.agents["agent-1"].task_count >= 5
        staleness = populated_monitor.get_status_staleness("agent-1")
        assert staleness is not None
        assert staleness <= 5
