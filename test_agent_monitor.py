import time
import threading
import pytest
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class AgentMonitor:
    name: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    _history: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def update_status(self, status: AgentStatus, task: Optional[str] = None, cpu: float = 0.0, memory: float = 0.0):
        with self._lock:
            self.status = status
            self.current_task = task
            self.cpu_usage = cpu
            self.memory_usage = memory
            self._history.append({
                "status": status.value,
                "task": task,
                "cpu": cpu,
                "memory": memory,
                "timestamp": time.time(),
            })

    def get_history(self) -> list:
        with self._lock:
            return list(self._history)

    def query_history(self, task_name: str) -> list:
        with self._lock:
            return [h for h in self._history if h["task"] == task_name]


class FakeMonitorSubscriber:
    def __init__(self):
        self.last_status = None
        self.received_at = 0.0

    def on_update(self, monitor: AgentMonitor):
        self.last_status = (monitor.status, monitor.current_task, monitor.cpu_usage, monitor.memory_usage)
        self.received_at = time.time()


@pytest.fixture
def monitor():
    return AgentMonitor(name="agent-1")


@pytest.fixture
def subscriber():
    return FakeMonitorSubscriber()


class TestAgentStatusMonitoring:

    def test_initial_status_is_idle(self, monitor):
        assert monitor.status == AgentStatus.IDLE
        assert monitor.name == "agent-1"
        assert monitor.current_task is None

    def test_status_update_to_running(self, monitor):
        monitor.update_status(AgentStatus.RUNNING, "data_process", 45.2, 1024.0)
        assert monitor.status == AgentStatus.RUNNING
        assert monitor.current_task == "data_process"
        assert monitor.cpu_usage == 45.2
        assert monitor.memory_usage == 1024.0

    def test_status_update_to_waiting(self, monitor):
        monitor.update_status(AgentStatus.WAITING, "db_query", 12.0, 512.0)
        assert monitor.status == AgentStatus.WAITING
        assert monitor.current_task == "db_query"

    def test_status_update_to_error(self, monitor):
        monitor.update_status(AgentStatus.ERROR, None, 0.0, 0.0)
        assert monitor.status == AgentStatus.ERROR
        assert monitor.current_task is None

    def test_status_update_lag_within_5_seconds(self, monitor, subscriber):
        monitor.update_status(AgentStatus.RUNNING, "train_model", 78.3, 2048.0)
        subscriber.on_update(monitor)
        lag = time.time() - subscriber.received_at
        assert lag <= 5.0, f"Status update lag {lag:.2f}s exceeds 5s limit"

    def test_status_transition_idle_to_running(self, monitor):
        monitor.update_status(AgentStatus.RUNNING, "compute", 60.0, 1024.0)
        monitor.update_status(AgentStatus.IDLE, None, 5.0, 256.0)
        assert monitor.status == AgentStatus.IDLE
        assert monitor.current_task is None

    def test_history_records_all_updates(self, monitor):
        monitor.update_status(AgentStatus.RUNNING, "task_a", 30.0, 512.0)
        monitor.update_status(AgentStatus.WAITING, "task_b", 10.0, 256.0)
        monitor.update_status(AgentStatus.ERROR, None, 0.0, 0.0)
        history = monitor.get_history()
        assert len(history) == 3
        assert history[0]["task"] == "task_a"
        assert history[1]["task"] == "task_b"
        assert history[2]["status"] == AgentStatus.ERROR.value

    def test_query_history_by_task_name(self, monitor):
        monitor.update_status(AgentStatus.RUNNING, "train", 80.0, 2048.0)
        monitor.update_status(AgentStatus.WAITING, "train", 40.0, 1024.0)
        monitor.update_status(AgentStatus.RUNNING, "infer", 60.0, 1536.0)
        results = monitor.query_history("train")
        assert len(results) == 2
        for r in results:
            assert r["task"] == "train"

    def test_query_history_response_within_2_seconds(self, monitor):
        for i in range(1000):
            monitor.update_status(AgentStatus.RUNNING, f"task_{i}", float(i), float(i * 2))
        start = time.time()
        results = monitor.query_history("task_500")
        elapsed = time.time() - start
        assert elapsed <= 2.0, f"History query took {elapsed:.3f}s, exceeds 2s limit"
        assert len(results) == 1
        assert results[0]["task"] == "task_500"

    def test_cpu_and_memory_usage_tracked(self, monitor):
        monitor.update_status(AgentStatus.RUNNING, "heavy_job", 95.5, 4096.0)
        assert monitor.cpu_usage == 95.5
        assert monitor.memory_usage == 4096.0

    def test_concurrent_updates_are_thread_safe(self, monitor):
        errors = []

        def updater(task_id: int):
            try:
                monitor.update_status(AgentStatus.RUNNING, f"task_{task_id}", float(task_id), float(task_id * 2))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=updater, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        history = monitor.get_history()
        assert len(history) == 100
        assert len(errors) == 0

    def test_status_enum_values(self):
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.WAITING.value == "waiting"
        assert AgentStatus.ERROR.value == "error"
