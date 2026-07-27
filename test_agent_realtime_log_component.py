"""Agent执行实时日志组件 - TDD 测试用例"""

import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Callable


@dataclass
class LogEntry:
    """单条日志记录"""
    timestamp: datetime
    level: str
    message: str
    agent_id: str = ""

    def matches_keyword(self, keyword: str) -> bool:
        return keyword.lower() in self.message.lower()

    def matches_level(self, level: str) -> bool:
        return self.level == level


class AgentRealtimeLogComponent:
    """Agent执行实时日志组件 - 支持实时推送、时间排序、关键词搜索、级别筛选"""

    def __init__(self):
        self._logs: List[LogEntry] = []
        self._subscribers: List[Callable] = []
        self._lock = threading.Lock()

    def add_log(self, level: str, message: str, agent_id: str = "") -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            agent_id=agent_id,
        )
        with self._lock:
            self._logs.append(entry)
        self._notify_subscribers(entry)
        return entry

    def subscribe(self, callback: Callable):
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, entry: LogEntry):
        for cb in self._subscribers:
            try:
                cb(entry)
            except Exception:
                pass

    def get_logs(
        self,
        level: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_by_time: bool = True,
    ) -> List[LogEntry]:
        with self._lock:
            logs = list(self._logs)

        if level:
            logs = [e for e in logs if e.matches_level(level)]
        if keyword:
            logs = [e for e in logs if e.matches_keyword(keyword)]
        if sort_by_time:
            logs.sort(key=lambda e: e.timestamp)
        return logs

    def get_latest(self, n: int = 10) -> List[LogEntry]:
        with self._lock:
            logs = list(self._logs)
        logs.sort(key=lambda e: e.timestamp, reverse=True)
        return logs[:n]

    def get_log_count(self) -> int:
        with self._lock:
            return len(self._logs)

    def clear(self):
        with self._lock:
            self._logs.clear()


import pytest


@pytest.fixture
def log_component():
    return AgentRealtimeLogComponent()


@pytest.fixture
def component_with_data(log_component):
    """预置测试数据的组件"""
    base = datetime(2026, 7, 16, 10, 0, 0)
    entries = [
        ("INFO", "Agent started successfully"),
        ("WARN", "High memory usage detected"),
        ("ERROR", "Connection timeout to database"),
        ("INFO", "Task completed with status OK"),
        ("DEBUG", "Debug trace message"),
    ]
    for i, (level, msg) in enumerate(entries):
        entry = log_component.add_log(level, msg)
        entry.timestamp = base + timedelta(seconds=i)
    return log_component


# =============================================================================
# 验收标准 1: 日志实时推送延迟 ≤3 秒
# =============================================================================

class TestRealtimePushLatency:

    def test_single_push_latency_under_3s(self, log_component):
        received: List[LogEntry] = []
        start = time.monotonic()

        def on_log(entry: LogEntry):
            received.append(entry)

        log_component.subscribe(on_log)
        log_component.add_log("INFO", "realtime test msg")
        elapsed = time.monotonic() - start

        assert len(received) == 1
        assert received[0].message == "realtime test msg"
        assert elapsed < 3.0, f"推送延迟 {elapsed:.4f}s 超过 3s 上限"

    def test_batch_push_latency_under_3s(self, log_component):
        received: List[LogEntry] = []
        start = time.monotonic()

        def on_log(entry: LogEntry):
            received.append(entry)

        log_component.subscribe(on_log)
        for i in range(20):
            log_component.add_log("INFO", f"batch-msg-{i}")
        elapsed = time.monotonic() - start

        assert len(received) == 20
        assert elapsed < 3.0, f"20条批量推送延迟 {elapsed:.4f}s 超过 3s"

    def test_push_preserves_log_level(self, log_component):
        received: List[LogEntry] = []

        def on_log(entry: LogEntry):
            received.append(entry)

        log_component.subscribe(on_log)
        log_component.add_log("ERROR", "critical failure")

        assert received[0].level == "ERROR"
        assert received[0].message == "critical failure"

    def test_multiple_subscribers_all_receives(self, log_component):
        buf_a: List[LogEntry] = []
        buf_b: List[LogEntry] = []

        def cb_a(entry: LogEntry):
            buf_a.append(entry)

        def cb_b(entry: LogEntry):
            buf_b.append(entry)

        log_component.subscribe(cb_a)
        log_component.subscribe(cb_b)
        log_component.add_log("INFO", "shared msg")

        assert len(buf_a) == 1
        assert len(buf_b) == 1
        assert buf_a[0].message == buf_b[0].message == "shared msg"


# =============================================================================
# 验收标准 2: 支持按时间排序
# =============================================================================

class TestTimeSorting:

    def test_default_sort_by_time_ascending(self, component_with_data):
        logs = component_with_data.get_logs()
        timestamps = [e.timestamp for e in logs]
        assert timestamps == sorted(timestamps), "默认应按时间正序排列"

    def test_explicit_sort_by_time_true(self, log_component):
        base = datetime(2026, 7, 16, 12, 0, 0)
        log_component.add_log("INFO", "z-last")
        log_component._logs[0].timestamp = base + timedelta(seconds=30)
        log_component.add_log("INFO", "a-first")
        log_component._logs[1].timestamp = base
        log_component.add_log("INFO", "m-middle")
        log_component._logs[2].timestamp = base + timedelta(seconds=15)

        result = log_component.get_logs(sort_by_time=True)
        assert [e.message for e in result] == ["a-first", "m-middle", "z-last"]

    def test_sort_by_time_disabled_preserves_insertion_order(self, log_component):
        base = datetime(2026, 7, 16, 12, 0, 0)
        log_component.add_log("INFO", "first-inserted")
        log_component._logs[0].timestamp = base + timedelta(seconds=10)
        log_component.add_log("INFO", "second-inserted")
        log_component._logs[1].timestamp = base

        result = log_component.get_logs(sort_by_time=False)
        assert result[0].message == "first-inserted"
        assert result[1].message == "second-inserted"

    def test_get_latest_returns_most_recent(self, log_component):
        base = datetime(2026, 7, 16, 12, 0, 0)
        for i in range(10):
            entry = log_component.add_log("INFO", f"msg-{i}")
            entry.timestamp = base + timedelta(seconds=i)

        latest = log_component.get_latest(3)
        assert len(latest) == 3
        assert latest[0].message == "msg-9"
        assert latest[1].message == "msg-8"
        assert latest[2].message == "msg-7"

    def test_empty_logs_returns_empty_list(self, log_component):
        assert log_component.get_logs() == []
        assert log_component.get_latest() == []


# =============================================================================
# 验收标准 2: 关键词搜索
# =============================================================================

class TestKeywordSearch:

    def test_keyword_match_case_insensitive(self, component_with_data):
        logs = component_with_data.get_logs(keyword="TIMEOUT")
        assert len(logs) == 1
        assert "timeout" in logs[0].message.lower()

    def test_keyword_no_match_returns_empty(self, component_with_data):
        logs = component_with_data.get_logs(keyword="nonexistent_xyz")
        assert len(logs) == 0

    def test_keyword_matches_partial_word(self, component_with_data):
        logs = component_with_data.get_logs(keyword="memory")
        assert len(logs) == 1
        assert "memory" in logs[0].message.lower()

    def test_keyword_special_characters(self, log_component):
        log_component.add_log("INFO", "Error: connection refused (host: 127.0.0.1)")
        log_component.add_log("INFO", "Normal operation continued")

        logs = log_component.get_logs(keyword="127.0.0.1")
        assert len(logs) == 1
        assert "127.0.0.1" in logs[0].message


# =============================================================================
# 验收标准 3: 日志级别筛选（INFO / WARN / ERROR）
# =============================================================================

class TestLogLevelFilter:

    def test_filter_info_only(self, component_with_data):
        logs = component_with_data.get_logs(level="INFO")
        assert all(e.level == "INFO" for e in logs)
        assert len(logs) == 2

    def test_filter_warn_only(self, component_with_data):
        logs = component_with_data.get_logs(level="WARN")
        assert all(e.level == "WARN" for e in logs)
        assert len(logs) == 1
        assert "memory" in logs[0].message.lower()

    def test_filter_error_only(self, component_with_data):
        logs = component_with_data.get_logs(level="ERROR")
        assert all(e.level == "ERROR" for e in logs)
        assert len(logs) == 1
        assert "timeout" in logs[0].message.lower()

    def test_no_filter_returns_all(self, component_with_data):
        logs = component_with_data.get_logs()
        assert len(logs) == 5

    def test_unknown_level_returns_empty(self, component_with_data):
        logs = component_with_data.get_logs(level="TRACE")
        assert len(logs) == 0


# =============================================================================
# 组合场景
# =============================================================================

class TestCombinedFilters:

    def test_level_plus_keyword(self, component_with_data):
        logs = component_with_data.get_logs(level="INFO", keyword="completed")
        assert len(logs) == 1
        assert logs[0].level == "INFO"
        assert "completed" in logs[0].message.lower()

    def test_level_plus_keyword_no_match(self, component_with_data):
        logs = component_with_data.get_logs(level="WARN", keyword="database")
        assert len(logs) == 0

    def test_combined_filters_sorted_by_time(self, log_component):
        base = datetime(2026, 7, 16, 14, 0, 0)
        log_component.add_log("INFO", "task-3")
        log_component._logs[0].timestamp = base + timedelta(seconds=30)
        log_component.add_log("INFO", "task-1")
        log_component._logs[1].timestamp = base
        log_component.add_log("WARN", "task-2")
        log_component._logs[2].timestamp = base + timedelta(seconds=15)
        log_component.add_log("INFO", "other")
        log_component._logs[3].timestamp = base + timedelta(seconds=5)

        result = log_component.get_logs(level="INFO", keyword="task", sort_by_time=True)
        assert len(result) == 2
        assert result[0].message == "task-1"
        assert result[1].message == "task-3"


# =============================================================================
# 订阅管理
# =============================================================================

class TestSubscriberManagement:

    def test_unsubscribe_stops_delivery(self, log_component):
        received: List[LogEntry] = []

        def on_log(entry: LogEntry):
            received.append(entry)

        log_component.subscribe(on_log)
        log_component.add_log("INFO", "before")
        log_component.unsubscribe(on_log)
        log_component.add_log("ERROR", "after")

        assert len(received) == 1
        assert received[0].message == "before"

    def test_unsubscribe_nonexistent_no_error(self, log_component):
        def dummy(entry: LogEntry):
            pass

        log_component.unsubscribe(dummy)
        log_component.add_log("INFO", "should not crash")
        assert log_component.get_log_count() == 1

    def test_subscriber_exception_does_not_crash(self, log_component):
        def bad_cb(entry: LogEntry):
            raise RuntimeError("intentional crash")

        def good_cb(entry: LogEntry):
            pass

        log_component.subscribe(bad_cb)
        log_component.subscribe(good_cb)
        log_component.add_log("INFO", "crash test")
        assert log_component.get_log_count() == 1


# =============================================================================
# 并发安全
# =============================================================================

class TestConcurrency:

    def test_concurrent_writes(self, log_component):
        errors: List[Exception] = []

        def writer(prefix: str):
            try:
                for i in range(50):
                    log_component.add_log("INFO", f"{prefix}-{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"t{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert log_component.get_log_count() == 250

    def test_concurrent_read_write(self, log_component):
        stop = threading.Event()
        read_errors: List[Exception] = []

        def writer():
            for i in range(100):
                log_component.add_log("INFO", f"write-{i}")
                time.sleep(0.001)

        def reader():
            while not stop.is_set():
                try:
                    log_component.get_logs(level="INFO")
                except Exception as e:
                    read_errors.append(e)

        t_write = threading.Thread(target=writer)
        t_read = threading.Thread(target=reader)
        t_read.start()
        t_write.start()
        t_write.join()
        stop.set()
        t_read.join()

        assert len(read_errors) == 0


# =============================================================================
# 辅助功能
# =============================================================================

class TestUtilityMethods:

    def test_get_log_count(self, log_component):
        assert log_component.get_log_count() == 0
        log_component.add_log("INFO", "one")
        assert log_component.get_log_count() == 1
        log_component.add_log("ERROR", "two")
        assert log_component.get_log_count() == 2

    def test_clear_removes_all_logs(self, log_component):
        log_component.add_log("INFO", "msg1")
        log_component.add_log("WARN", "msg2")
        log_component.clear()
        assert log_component.get_log_count() == 0
        assert log_component.get_logs() == []

    def test_agent_id_field(self, log_component):
        entry = log_component.add_log("INFO", "agent-task", agent_id="agent-001")
        assert entry.agent_id == "agent-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
