"""
Agent执行实时日志组件 - TDD 测试用例
验证 Agent 执行日志组件支持实时滚动查看
"""

import time
import threading
import queue
from datetime import datetime, timedelta
from typing import List, Optional

import pytest


# ============================================================
# 被测试代码（生产代码）
# ============================================================

class LogLevel:
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class LogEntry:
    def __init__(self, level: str, message: str, timestamp: Optional[datetime] = None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        return f"LogEntry(level={self.level}, message={self.message}, timestamp={self.timestamp})"


class RealtimeLogComponent:
    """Agent 执行实时日志组件"""

    def __init__(self):
        self._log_queue: queue.Queue = queue.Queue()
        self._logs: List[LogEntry] = []
        self._lock = threading.Lock()
        self._consumers: List[queue.Queue] = []

    def add_log(self, level: str, message: str):
        entry = LogEntry(level=level, message=message)
        with self._lock:
            self._logs.append(entry)
        for consumer in self._consumers:
            consumer.put(entry)

    def subscribe(self) -> queue.Queue:
        consumer: queue.Queue = queue.Queue()
        self._consumers.append(consumer)
        return consumer

    def get_logs(self, level_filter: Optional[str] = None,
                 keyword: Optional[str] = None,
                 sort_by_time: bool = True) -> List[LogEntry]:
        with self._lock:
            result = list(self._logs)

        if level_filter:
            result = [e for e in result if e.level == level_filter]
        if keyword:
            result = [e for e in result if keyword.lower() in e.message.lower()]
        if sort_by_time:
            result = sorted(result, key=lambda e: e.timestamp)
        return result

    def get_logs_since(self, since: datetime, level_filter: Optional[str] = None) -> List[LogEntry]:
        with self._lock:
            result = [e for e in self._logs if e.timestamp >= since]
        if level_filter:
            result = [e for e in result if e.level == level_filter]
        return sorted(result, key=lambda e: e.timestamp)


# ============================================================
# 测试用例
# ============================================================

class TestRealtimeLogPushDelay:
    """验收标准：日志实时推送延迟 <= 3 秒"""

    def test_push_delay_within_3_seconds(self):
        component = RealtimeLogComponent()
        consumer = component.subscribe()

        start_time = time.monotonic()
        component.add_log(LogLevel.INFO, "test message")
        entry = consumer.get(timeout=3.0)
        elapsed = time.monotonic() - start_time

        assert entry is not None
        assert entry.level == LogLevel.INFO
        assert entry.message == "test message"
        assert elapsed <= 3.0, f"推送延迟 {elapsed:.3f}s 超过 3 秒上限"

    def test_push_delay_under_load(self):
        component = RealtimeLogComponent()
        consumer = component.subscribe()

        num_logs = 50
        for i in range(num_logs):
            component.add_log(LogLevel.INFO, f"log message {i}")

        received = []
        deadline = time.monotonic() + 3.0
        while len(received) < num_logs and time.monotonic() < deadline:
            try:
                entry = consumer.get(timeout=0.1)
                received.append(entry)
            except queue.Empty:
                continue

        assert len(received) == num_logs, f"只收到 {len(received)}/{num_logs} 条日志"


class TestTimeSorting:
    """验收标准：支持按时间排序"""

    def test_logs_sorted_by_time_ascending(self):
        component = RealtimeLogComponent()
        base = datetime(2026, 7, 16, 10, 0, 0)

        component.add_log(LogLevel.INFO, "third")
        time.sleep(0.01)
        component.add_log(LogLevel.WARN, "first")
        time.sleep(0.01)
        component.add_log(LogLevel.ERROR, "second")

        logs = component.get_logs(sort_by_time=True)
        for i in range(1, len(logs)):
            assert logs[i - 1].timestamp <= logs[i].timestamp

    def test_logs_without_sorting_preserves_insertion_order(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "msg1")
        component.add_log(LogLevel.WARN, "msg2")
        component.add_log(LogLevel.ERROR, "msg3")

        logs = component.get_logs(sort_by_time=False)
        assert [e.message for e in logs] == ["msg1", "msg2", "msg3"]


class TestKeywordSearch:
    """验收标准：支持关键词搜索"""

    def test_keyword_search_finds_matching_logs(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "User login successful")
        component.add_log(LogLevel.WARN, "Disk space low")
        component.add_log(LogLevel.ERROR, "Login failed for admin")

        results = component.get_logs(keyword="login")
        assert len(results) == 2
        assert all("login" in e.message.lower() for e in results)

    def test_keyword_search_case_insensitive(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "Connection established")
        component.add_log(LogLevel.WARN, "CONNECTION timeout")
        component.add_log(LogLevel.ERROR, "connection reset")

        results = component.get_logs(keyword="connection")
        assert len(results) == 3

    def test_keyword_search_no_match(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "All systems normal")
        component.add_log(LogLevel.WARN, "CPU usage high")

        results = component.get_logs(keyword="network")
        assert len(results) == 0


class TestLogLevelFilter:
    """验收标准：日志级别筛选（INFO/WARN/ERROR）可用"""

    def test_filter_info_only(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "info msg 1")
        component.add_log(LogLevel.WARN, "warn msg 1")
        component.add_log(LogLevel.ERROR, "error msg 1")
        component.add_log(LogLevel.INFO, "info msg 2")

        results = component.get_logs(level_filter=LogLevel.INFO)
        assert len(results) == 2
        assert all(e.level == LogLevel.INFO for e in results)

    def test_filter_warn_only(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "info msg")
        component.add_log(LogLevel.WARN, "warn msg 1")
        component.add_log(LogLevel.WARN, "warn msg 2")
        component.add_log(LogLevel.ERROR, "error msg")

        results = component.get_logs(level_filter=LogLevel.WARN)
        assert len(results) == 2
        assert all(e.level == LogLevel.WARN for e in results)

    def test_filter_error_only(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "info msg")
        component.add_log(LogLevel.WARN, "warn msg")
        component.add_log(LogLevel.ERROR, "error msg 1")
        component.add_log(LogLevel.ERROR, "error msg 2")
        component.add_log(LogLevel.ERROR, "error msg 3")

        results = component.get_logs(level_filter=LogLevel.ERROR)
        assert len(results) == 3
        assert all(e.level == LogLevel.ERROR for e in results)

    def test_no_filter_returns_all(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "info msg")
        component.add_log(LogLevel.WARN, "warn msg")
        component.add_log(LogLevel.ERROR, "error msg")

        results = component.get_logs()
        assert len(results) == 3


class TestCombinedFilterAndSearch:
    """组合筛选：级别 + 关键词"""

    def test_level_and_keyword_combined(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "User login ok")
        component.add_log(LogLevel.ERROR, "Login failed")
        component.add_log(LogLevel.WARN, "Login slow")
        component.add_log(LogLevel.ERROR, "Disk full")

        results = component.get_logs(level_filter=LogLevel.ERROR, keyword="login")
        assert len(results) == 1
        assert results[0].message == "Login failed"

    def test_level_filter_with_sorting(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.ERROR, "late error")
        time.sleep(0.01)
        component.add_log(LogLevel.ERROR, "early error")
        time.sleep(0.01)
        component.add_log(LogLevel.INFO, "some info")

        results = component.get_logs(level_filter=LogLevel.ERROR, sort_by_time=True)
        assert len(results) == 2
        assert results[0].message == "late error"
        assert results[1].message == "early error"


class TestGetLogsSince:
    """按时间范围获取日志"""

    def test_logs_since_timestamp(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "old log")
        time.sleep(0.05)
        mid_time = datetime.now()
        time.sleep(0.05)
        component.add_log(LogLevel.ERROR, "new log")

        results = component.get_logs_since(mid_time)
        assert len(results) == 1
        assert results[0].message == "new log"

    def test_logs_since_with_level_filter(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "old info")
        time.sleep(0.05)
        mid_time = datetime.now()
        time.sleep(0.05)
        component.add_log(LogLevel.INFO, "new info")
        component.add_log(LogLevel.ERROR, "new error")

        results = component.get_logs_since(mid_time, level_filter=LogLevel.ERROR)
        assert len(results) == 1
        assert results[0].message == "new error"


class TestMultipleSubscribers:
    """多订阅者同时接收日志"""

    def test_multiple_subscribers_receive_same_logs(self):
        component = RealtimeLogComponent()

        consumer1 = component.subscribe()
        consumer2 = component.subscribe()

        component.add_log(LogLevel.INFO, "broadcast message")

        entry1 = consumer1.get(timeout=3.0)
        entry2 = consumer2.get(timeout=3.0)

        assert entry1.message == "broadcast message"
        assert entry2.message == "broadcast message"

    def test_subscriber_added_after_logs_gets_new_logs_only(self):
        component = RealtimeLogComponent()

        component.add_log(LogLevel.INFO, "old log")
        consumer = component.subscribe()

        component.add_log(LogLevel.WARN, "new log")
        entry = consumer.get(timeout=3.0)

        assert entry.message == "new log"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
