"""Agent执行实时日志组件 - TDD 测试用例"""
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    message: str
    source: str = ""


class AgentExecutionLog:
    """Agent执行实时日志组件"""

    def __init__(self):
        self._logs: List[LogEntry] = []
        self._lock = threading.Lock()
        self._listeners: List = []
        self._stop_event = threading.Event()

    def add_log(self, level: LogLevel, message: str, source: str = ""):
        entry = LogEntry(timestamp=datetime.now(), level=level, message=message, source=source)
        with self._lock:
            self._logs.append(entry)
        self._notify_listeners(entry)

    def subscribe(self, callback):
        self._listeners.append(callback)

    def _notify_listeners(self, entry: LogEntry):
        for cb in self._listeners:
            try:
                cb(entry)
            except Exception:
                pass

    def get_logs(self, level_filter: Optional[LogLevel] = None,
                 keyword: Optional[str] = None,
                 sort_by_time: bool = True) -> List[LogEntry]:
        with self._lock:
            result = list(self._logs)
        if level_filter:
            result = [e for e in result if e.level == level_filter]
        if keyword:
            result = [e for e in result if keyword.lower() in e.message.lower()]
        if sort_by_time:
            result.sort(key=lambda e: e.timestamp)
        return result

    def get_log_count(self) -> int:
        with self._lock:
            return len(self._logs)

    def clear(self):
        with self._lock:
            self._logs.clear()

    def start_streaming(self):
        self._stop_event.clear()

    def stop_streaming(self):
        self._stop_event.set()


# ── Tests ──

def test_log_add_and_retrieve():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "Agent started")
    log.add_log(LogLevel.WARN, "Slow response detected")
    log.add_log(LogLevel.ERROR, "Connection timeout")
    assert log.get_log_count() == 3


def test_log_level_filter_info_only():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "msg1")
    log.add_log(LogLevel.WARN, "msg2")
    log.add_log(LogLevel.ERROR, "msg3")
    log.add_log(LogLevel.INFO, "msg4")
    result = log.get_logs(level_filter=LogLevel.INFO)
    assert len(result) == 2
    assert all(e.level == LogLevel.INFO for e in result)


def test_log_level_filter_warn_only():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "msg1")
    log.add_log(LogLevel.WARN, "msg2")
    log.add_log(LogLevel.WARN, "msg3")
    log.add_log(LogLevel.ERROR, "msg4")
    result = log.get_logs(level_filter=LogLevel.WARN)
    assert len(result) == 2
    assert all(e.level == LogLevel.WARN for e in result)


def test_log_level_filter_error_only():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "msg1")
    log.add_log(LogLevel.ERROR, "msg2")
    log.add_log(LogLevel.ERROR, "msg3")
    result = log.get_logs(level_filter=LogLevel.ERROR)
    assert len(result) == 2
    assert all(e.level == LogLevel.ERROR for e in result)


def test_keyword_search_case_insensitive():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "Agent started successfully")
    log.add_log(LogLevel.WARN, "High memory usage")
    log.add_log(LogLevel.ERROR, "Connection to agent failed")
    result = log.get_logs(keyword="agent")
    assert len(result) == 2
    result2 = log.get_logs(keyword="AGENT")
    assert len(result2) == 2


def test_keyword_search_no_match():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "hello world")
    result = log.get_logs(keyword="xyz123")
    assert len(result) == 0


def test_time_sorting_asc():
    log = AgentExecutionLog()
    base = datetime(2026, 7, 16, 12, 0, 0)
    log.add_log(LogLevel.INFO, "third", source="")
    time.sleep(0.01)
    log.add_log(LogLevel.WARN, "first", source="")
    time.sleep(0.01)
    log.add_log(LogLevel.ERROR, "second", source="")
    result = log.get_logs(sort_by_time=True)
    assert len(result) == 3
    for i in range(len(result) - 1):
        assert result[i].timestamp <= result[i + 1].timestamp


def test_combined_filter_level_and_keyword():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "Agent started")
    log.add_log(LogLevel.WARN, "Agent slow response")
    log.add_log(LogLevel.ERROR, "Connection timeout")
    log.add_log(LogLevel.ERROR, "Agent crash detected")
    result = log.get_logs(level_filter=LogLevel.ERROR, keyword="agent")
    assert len(result) == 1
    assert "crash" in result[0].message.lower()


def test_realtime_push_delay_within_threshold():
    """验证日志实时推送延迟 <= 3秒"""
    log = AgentExecutionLog()
    received: List = []
    log.subscribe(lambda e: received.append(e))

    start = time.monotonic()
    log.add_log(LogLevel.INFO, "realtime test message")
    elapsed = time.monotonic() - start

    assert len(received) == 1
    assert received[0].message == "realtime test message"
    assert elapsed <= 3.0, f"Push delay {elapsed:.3f}s exceeds 3 second threshold"


def test_realtime_multiple_pushes_delay():
    """验证多条日志推送延迟均 <= 3秒"""
    log = AgentExecutionLog()
    received: List = []
    log.subscribe(lambda e: received.append(e))

    times: List = []
    for i in range(5):
        start = time.monotonic()
        log.add_log(LogLevel.INFO, f"message {i}")
        elapsed = time.monotonic() - start
        times.append(elapsed)

    assert len(received) == 5
    for i, t in enumerate(times):
        assert t <= 3.0, f"Push {i} delay {t:.3f}s exceeds 3 second threshold"


def test_multiple_subscribers_receive_logs():
    log = AgentExecutionLog()
    sub_a: List = []
    sub_b: List = []
    log.subscribe(lambda e: sub_a.append(e))
    log.subscribe(lambda e: sub_b.append(e))

    log.add_log(LogLevel.INFO, "broadcast")
    assert len(sub_a) == 1
    assert len(sub_b) == 1
    assert sub_a[0].message == "broadcast"
    assert sub_b[0].message == "broadcast"


def test_clear_removes_all_logs():
    log = AgentExecutionLog()
    log.add_log(LogLevel.INFO, "a")
    log.add_log(LogLevel.WARN, "b")
    log.clear()
    assert log.get_log_count() == 0
    assert len(log.get_logs()) == 0


def test_thread_safety_concurrent_writes():
    log = AgentExecutionLog()
    errors: List = []

    def writer(prefix: str):
        try:
            for i in range(50):
                log.add_log(LogLevel.INFO, f"{prefix}-{i}")
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=writer, args=("t1",))
    t2 = threading.Thread(target=writer, args=("t2",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert len(errors) == 0
    assert log.get_log_count() == 100


def test_streaming_start_stop():
    log = AgentExecutionLog()
    log.start_streaming()
    log.stop_streaming()
    assert log._stop_event.is_set()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
