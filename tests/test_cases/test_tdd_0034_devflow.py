import pytest
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class SubAgent:
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.last_status_change: datetime = datetime.now()
        self.task_history: list[dict] = []

    def assign_task(self, task_id: str, task_desc: str) -> None:
        self.status = AgentStatus.BUSY
        self.current_task = task_id
        self.last_status_change = datetime.now()
        self.task_history.append({
            "task_id": task_id,
            "task_desc": task_desc,
            "assigned_at": datetime.now().isoformat(),
        })

    def complete_task(self) -> None:
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.last_status_change = datetime.now()

    def go_offline(self) -> None:
        self.status = AgentStatus.OFFLINE
        self.current_task = None
        self.last_status_change = datetime.now()


class AgentSwarm:
    def __init__(self, swarm_id: str):
        self.swarm_id = swarm_id
        self.agents: dict[str, SubAgent] = {}
        self.task_queue: list[dict] = []
        self.completed_tasks: list[dict] = []

    def add_agent(self, agent: SubAgent) -> None:
        self.agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str) -> None:
        if agent_id in self.agents:
            del self.agents[agent_id]

    def get_active_agents(self) -> list[SubAgent]:
        return [a for a in self.agents.values() if a.status != AgentStatus.OFFLINE]

    def get_busy_agents(self) -> list[SubAgent]:
        return [a for a in self.agents.values() if a.status == AgentStatus.BUSY]

    def get_idle_agents(self) -> list[SubAgent]:
        return [a for a in self.agents.values() if a.status == AgentStatus.IDLE]

    def get_offline_agents(self) -> list[SubAgent]:
        return [a for a in self.agents.values() if a.status == AgentStatus.OFFLINE]

    @property
    def parallelism(self) -> int:
        return len(self.get_busy_agents())

    @property
    def total_agents(self) -> int:
        return len(self.agents)

    def enqueue_task(self, task_id: str, task_desc: str, required_agent_type: Optional[str] = None) -> None:
        self.task_queue.append({
            "task_id": task_id,
            "task_desc": task_desc,
            "required_agent_type": required_agent_type,
            "enqueued_at": datetime.now().isoformat(),
            "status": "queued",
        })

    def dispatch_next_task(self) -> Optional[str]:
        if not self.task_queue:
            return None
        idle_agents = self.get_idle_agents()
        if not idle_agents:
            return None
        task = self.task_queue.pop(0)
        agent = idle_agents[0]
        agent.assign_task(task["task_id"], task["task_desc"])
        return task["task_id"]

    def complete_task_for_agent(self, agent_id: str) -> Optional[str]:
        agent = self.agents.get(agent_id)
        if agent is None or agent.current_task is None:
            return None
        task_id = agent.current_task
        self.completed_tasks.append({
            "task_id": task_id,
            "agent_id": agent_id,
            "completed_at": datetime.now().isoformat(),
        })
        agent.complete_task()
        return task_id

    def get_task_distribution(self) -> dict:
        return {
            "queued": len(self.task_queue),
            "in_progress": len(self.get_busy_agents()),
            "completed": len(self.completed_tasks),
            "total": len(self.task_queue) + len(self.get_busy_agents()) + len(self.completed_tasks),
        }

    def get_agent_status_summary(self) -> dict:
        return {
            "total": self.total_agents,
            "idle": len(self.get_idle_agents()),
            "busy": len(self.get_busy_agents()),
            "offline": len(self.get_offline_agents()),
            "parallelism": self.parallelism,
        }


class SwarmMonitor:
    def __init__(self, swarm: AgentSwarm, status_check_interval: float = 1.0):
        self.swarm = swarm
        self.status_check_interval = status_check_interval
        self._status_history: list[dict] = []
        self._last_update: Optional[datetime] = None

    def snapshot(self) -> dict:
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "parallelism": self.swarm.parallelism,
            "agent_statuses": {
                aid: agent.status.value
                for aid, agent in self.swarm.agents.items()
            },
            "task_distribution": self.swarm.get_task_distribution(),
        }
        self._status_history.append(snapshot)
        self._last_update = datetime.now()
        return snapshot

    def get_status_latency(self) -> float:
        if self._last_update is None:
            return 0.0
        return (datetime.now() - self._last_update).total_seconds()

    def get_history(self) -> list[dict]:
        return self._status_history

    def check_status_update_lag(self, max_lag_seconds: float = 5.0) -> bool:
        return self.get_status_latency() <= max_lag_seconds


@pytest.fixture
def swarm_with_agents():
    swarm = AgentSwarm("test-swarm-001")
    for i in range(5):
        agent = SubAgent(agent_id=f"agent-{i+1}", name=f"Worker-{i+1}")
        swarm.add_agent(agent)
    return swarm


@pytest.fixture
def monitor(swarm_with_agents):
    return SwarmMonitor(swarm_with_agents)


class TestAgentSwarmInitialization:
    def test_swarm_creation_with_id(self):
        swarm = AgentSwarm("swarm-alpha")
        assert swarm.swarm_id == "swarm-alpha"
        assert swarm.total_agents == 0
        assert swarm.parallelism == 0
        assert swarm.task_queue == []
        assert swarm.completed_tasks == []

    def test_add_agent_to_swarm(self):
        swarm = AgentSwarm("swarm-beta")
        agent = SubAgent("a1", "Agent-One")
        swarm.add_agent(agent)
        assert swarm.total_agents == 1
        assert swarm.agents["a1"] is agent

    def test_remove_agent_from_swarm(self):
        swarm = AgentSwarm("swarm-gamma")
        agent = SubAgent("a1", "Agent-One")
        swarm.add_agent(agent)
        swarm.remove_agent("a1")
        assert swarm.total_agents == 0

    def test_initial_agent_status_is_idle(self):
        agent = SubAgent("a1", "Agent-One")
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None


class TestAgentStatusTransitions:
    def test_assign_task_sets_busy(self, swarm_with_agents):
        swarm = swarm_with_agents
        agent = swarm.agents["agent-1"]
        agent.assign_task("task-001", "Process data batch A")
        assert agent.status == AgentStatus.BUSY
        assert agent.current_task == "task-001"

    def test_complete_task_returns_to_idle(self, swarm_with_agents):
        swarm = swarm_with_agents
        agent = swarm.agents["agent-1"]
        agent.assign_task("task-001", "Process data batch A")
        agent.complete_task()
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None

    def test_go_offline_sets_offline(self, swarm_with_agents):
        swarm = swarm_with_agents
        agent = swarm.agents["agent-1"]
        agent.go_offline()
        assert agent.status == AgentStatus.OFFLINE
        assert agent.current_task is None

    def test_task_history_is_recorded(self, swarm_with_agents):
        swarm = swarm_with_agents
        agent = swarm.agents["agent-1"]
        agent.assign_task("task-001", "Process data batch A")
        assert len(agent.task_history) == 1
        assert agent.task_history[0]["task_id"] == "task-001"


class TestSwarmParallelism:
    def test_parallelism_zero_when_no_busy_agents(self, swarm_with_agents):
        swarm = swarm_with_agents
        assert swarm.parallelism == 0

    def test_parallelism_counts_busy_agents(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        swarm.agents["agent-2"].assign_task("t2", "Task 2")
        assert swarm.parallelism == 2

    def test_parallelism_updates_when_task_completed(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        swarm.agents["agent-2"].assign_task("t2", "Task 2")
        assert swarm.parallelism == 2
        swarm.agents["agent-1"].complete_task()
        assert swarm.parallelism == 1

    def test_parallelism_excludes_offline_agents(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        swarm.agents["agent-2"].go_offline()
        assert swarm.parallelism == 1

    def test_max_parallelism_with_all_agents_busy(self, swarm_with_agents):
        swarm = swarm_with_agents
        for i in range(1, 6):
            swarm.agents[f"agent-{i}"].assign_task(f"t{i}", f"Task {i}")
        assert swarm.parallelism == 5


class TestTaskDistribution:
    def test_initial_distribution_all_zero(self, swarm_with_agents):
        swarm = swarm_with_agents
        dist = swarm.get_task_distribution()
        assert dist["queued"] == 0
        assert dist["in_progress"] == 0
        assert dist["completed"] == 0
        assert dist["total"] == 0

    def test_distribution_with_queued_tasks(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.enqueue_task("t1", "Task 1")
        swarm.enqueue_task("t2", "Task 2")
        swarm.enqueue_task("t3", "Task 3")
        dist = swarm.get_task_distribution()
        assert dist["queued"] == 3
        assert dist["in_progress"] == 0

    def test_distribution_with_dispatched_tasks(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.enqueue_task("t1", "Task 1")
        swarm.enqueue_task("t2", "Task 2")
        swarm.dispatch_next_task()
        swarm.dispatch_next_task()
        dist = swarm.get_task_distribution()
        assert dist["queued"] == 0
        assert dist["in_progress"] == 2
        assert dist["completed"] == 0

    def test_distribution_with_completed_tasks(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.enqueue_task("t1", "Task 1")
        swarm.dispatch_next_task()
        swarm.complete_task_for_agent("agent-1")
        dist = swarm.get_task_distribution()
        assert dist["queued"] == 0
        assert dist["in_progress"] == 0
        assert dist["completed"] == 1

    def test_task_dispatch_uses_idle_agent(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t0", "Prior task")
        swarm.enqueue_task("t1", "Task 1")
        dispatched_id = swarm.dispatch_next_task()
        assert dispatched_id == "t1"
        assert swarm.agents["agent-2"].current_task == "t1"

    def test_no_dispatch_when_all_busy(self, swarm_with_agents):
        swarm = swarm_with_agents
        for i in range(1, 6):
            swarm.agents[f"agent-{i}"].assign_task(f"t{i}", f"Task {i}")
        swarm.enqueue_task("t-extra", "Extra task")
        result = swarm.dispatch_next_task()
        assert result is None


class TestAgentStatusSummary:
    def test_summary_all_idle(self, swarm_with_agents):
        swarm = swarm_with_agents
        summary = swarm.get_agent_status_summary()
        assert summary["total"] == 5
        assert summary["idle"] == 5
        assert summary["busy"] == 0
        assert summary["offline"] == 0

    def test_summary_mixed_statuses(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        swarm.agents["agent-2"].assign_task("t2", "Task 2")
        swarm.agents["agent-3"].go_offline()
        summary = swarm.get_agent_status_summary()
        assert summary["total"] == 5
        assert summary["idle"] == 2
        assert summary["busy"] == 2
        assert summary["offline"] == 1

    def test_summary_parallelism_matches_busy_count(self, swarm_with_agents):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        swarm.agents["agent-2"].assign_task("t2", "Task 2")
        swarm.agents["agent-3"].assign_task("t3", "Task 3")
        summary = swarm.get_agent_status_summary()
        assert summary["parallelism"] == 3
        assert summary["parallelism"] == summary["busy"]


class TestSwarmMonitor:
    def test_monitor_snapshot_contains_parallelism(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        snap = monitor.snapshot()
        assert "parallelism" in snap
        assert snap["parallelism"] == 1

    def test_monitor_snapshot_contains_agent_statuses(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        swarm.agents["agent-2"].go_offline()
        snap = monitor.snapshot()
        assert snap["agent_statuses"]["agent-1"] == "busy"
        assert snap["agent_statuses"]["agent-2"] == "offline"
        assert snap["agent_statuses"]["agent-3"] == "idle"

    def test_monitor_snapshot_contains_task_distribution(self, monitor):
        snap = monitor.snapshot()
        assert "task_distribution" in snap
        assert snap["task_distribution"]["queued"] == 0
        assert snap["task_distribution"]["in_progress"] == 0
        assert snap["task_distribution"]["completed"] == 0

    def test_monitor_records_history(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        monitor.snapshot()
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        monitor.snapshot()
        swarm.agents["agent-1"].complete_task()
        monitor.snapshot()
        assert len(monitor.get_history()) == 3
        assert monitor.get_history()[0]["parallelism"] == 0
        assert monitor.get_history()[1]["parallelism"] == 1
        assert monitor.get_history()[2]["parallelism"] == 0

    def test_monitor_tracks_last_update_time(self, monitor):
        before = datetime.now()
        monitor.snapshot()
        after = datetime.now()
        assert before <= monitor._last_update <= after

    def test_status_latency_within_limit(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        monitor.snapshot()
        assert monitor.check_status_update_lag(max_lag_seconds=5.0) is True
        assert monitor.get_status_latency() <= 5.0

    def test_status_latency_zero_before_first_snapshot(self, monitor):
        assert monitor.get_status_latency() == 0.0

    def test_rapid_status_updates_latency(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        for i in range(10):
            agent_id = f"agent-{(i % 5) + 1}"
            swarm.agents[agent_id].assign_task(f"t{i}", f"Task {i}")
            monitor.snapshot()
            swarm.agents[agent_id].complete_task()
            monitor.snapshot()
        assert monitor.get_status_latency() <= 5.0
        assert len(monitor.get_history()) == 20


class TestFullWorkflow:
    def test_swarm_full_lifecycle(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        for i in range(7):
            swarm.enqueue_task(f"task-{i+1}", f"Work item {i+1}")
        dist = swarm.get_task_distribution()
        assert dist["queued"] == 7
        dispatched = 0
        while True:
            result = swarm.dispatch_next_task()
            if result is None:
                break
            dispatched += 1
            if dispatched <= 5:
                assert swarm.parallelism == dispatched
        assert dispatched == 5
        dist = swarm.get_task_distribution()
        assert dist["queued"] == 2
        assert dist["in_progress"] == 5
        snap = monitor.snapshot()
        assert snap["parallelism"] == 5
        assert snap["task_distribution"]["in_progress"] == 5
        for i in range(1, 6):
            swarm.complete_task_for_agent(f"agent-{i}")
        snap = monitor.snapshot()
        assert snap["parallelism"] == 0
        assert snap["task_distribution"]["completed"] == 5
        assert snap["task_distribution"]["queued"] == 2
        for i in range(6, 8):
            swarm.dispatch_next_task()
        for i in range(1, 3):
            swarm.complete_task_for_agent(f"agent-{i}")
        snap = monitor.snapshot()
        assert snap["task_distribution"]["completed"] == 7
        assert snap["task_distribution"]["queued"] == 0
        assert snap["task_distribution"]["in_progress"] == 0

    def test_real_time_status_update_within_5s(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        monitor.snapshot()
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        monitor.snapshot()
        latency_after_busy = monitor.get_status_latency()
        assert latency_after_busy <= 5.0
        swarm.agents["agent-2"].assign_task("t2", "Task 2")
        swarm.agents["agent-3"].assign_task("t3", "Task 3")
        monitor.snapshot()
        latency_after_multi_busy = monitor.get_status_latency()
        assert latency_after_multi_busy <= 5.0
        swarm.agents["agent-1"].complete_task()
        swarm.agents["agent-2"].go_offline()
        monitor.snapshot()
        latency_after_change = monitor.get_status_latency()
        assert latency_after_change <= 5.0
        summary = swarm.get_agent_status_summary()
        assert summary["busy"] == 1
        assert summary["idle"] == 2
        assert summary["offline"] == 2
        assert monitor.check_status_update_lag(5.0) is True

    def test_parallelism_display_accuracy(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        assert swarm.parallelism == 0
        snap = monitor.snapshot()
        assert snap["parallelism"] == 0
        busied = []
        for i in range(1, 6):
            swarm.agents[f"agent-{i}"].assign_task(f"t{i}", f"Task {i}")
            busied.append(f"agent-{i}")
            assert swarm.parallelism == len(busied)
            snap = monitor.snapshot()
            assert snap["parallelism"] == len(busied)
        for i in range(1, 6):
            swarm.agents[f"agent-{i}"].complete_task()
            busied.pop(0)
            assert swarm.parallelism == len(busied)
            snap = monitor.snapshot()
            assert snap["parallelism"] == len(busied)

    def test_all_status_transitions_monitored(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        monitor.snapshot()
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        monitor.snapshot()
        assert monitor.get_history()[-1]["agent_statuses"]["agent-1"] == "busy"
        swarm.agents["agent-1"].complete_task()
        monitor.snapshot()
        assert monitor.get_history()[-1]["agent_statuses"]["agent-1"] == "idle"
        swarm.agents["agent-1"].go_offline()
        monitor.snapshot()
        assert monitor.get_history()[-1]["agent_statuses"]["agent-1"] == "offline"

    def test_multiple_agents_simultaneous_busy(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        for i in range(1, 6):
            swarm.agents[f"agent-{i}"].assign_task(f"t{i}", f"Task {i}")
        snap = monitor.snapshot()
        for i in range(1, 6):
            assert snap["agent_statuses"][f"agent-{i}"] == "busy"
        assert snap["parallelism"] == 5
        assert snap["task_distribution"]["in_progress"] == 5

    def test_parallelism_excludes_idle_and_offline(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        swarm.agents["agent-1"].assign_task("t1", "Task 1")
        swarm.agents["agent-2"].assign_task("t2", "Task 2")
        swarm.agents["agent-3"].go_offline()
        snap = monitor.snapshot()
        assert snap["parallelism"] == 2
        assert snap["agent_statuses"]["agent-1"] == "busy"
        assert snap["agent_statuses"]["agent-2"] == "busy"
        assert snap["agent_statuses"]["agent-3"] == "offline"
        assert snap["agent_statuses"]["agent-4"] == "idle"

    def test_status_change_propagation_delays(self, swarm_with_agents, monitor):
        swarm = swarm_with_agents
        for i in range(5):
            agent_id = f"agent-{i+1}"
            swarm.agents[agent_id].assign_task(f"t_cycle_{i}", f"Cycle task {i}")
            snap = monitor.snapshot()
            assert snap["agent_statuses"][agent_id] == "busy"
            assert monitor.get_status_latency() <= 5.0
            swarm.agents[agent_id].complete_task()
            snap = monitor.snapshot()
            assert snap["agent_statuses"][agent_id] == "idle"
            assert monitor.get_status_latency() <= 5.0

    def test_large_scale_swarm_monitoring(self):
        swarm = AgentSwarm("large-swarm")
        for i in range(50):
            agent = SubAgent(f"agent-{i+1}", f"Worker-{i+1}")
            swarm.add_agent(agent)
        monitor = SwarmMonitor(swarm)
        for i in range(30):
            swarm.enqueue_task(f"bulk-task-{i+1}", f"Bulk work {i+1}")
        monitor.snapshot()
        dispatched = 0
        while True:
            result = swarm.dispatch_next_task()
            if result is None:
                break
            dispatched += 1
        assert dispatched == 30
        snap = monitor.snapshot()
        assert snap["parallelism"] == 30
        assert snap["task_distribution"]["in_progress"] == 30
        assert snap["task_distribution"]["queued"] == 0
        for i in range(1, 31):
            swarm.complete_task_for_agent(f"agent-{i}")
        snap = monitor.snapshot()
        assert snap["parallelism"] == 0
        assert snap["task_distribution"]["completed"] == 30
        assert len(monitor.get_history()) == 3
