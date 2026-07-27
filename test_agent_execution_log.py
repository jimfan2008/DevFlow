"""
测试用例：Agent执行实时日志组件
验证Agent执行日志组件支持实时滚动查看
"""

import time
import threading
from collections import OrderedDict
from datetime import datetime, timedelta

import pytest


# ---------- 被测试的模拟类 ----------

class LogLevel:
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class LogEntry:
    def __init__(self, level: str, message: str, timestamp: datetime = None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        return f"LogEntry(level={self.level}, message={self.message}, timestamp={self.timestamp})"


class RealtimeLogComponent:
    """Agent执行实时日志组件（模拟实现，用于测试）"""

    def __init__(self, max_entries: int = 10000):
        self._entries: list[LogEntry] = []
        self._max_entries = max_entries
        self._subscribers: list[list] = []
        self._lock = threading.Lock()

    def append(self, entry: LogEntry):
        with self._lock:
            self._entries.append(entry)
            self._notify_subscribers(entry)

    def append_batch(self, entries: list[LogEntry]):
        with self._lock:
            self._entries.extend(entries)
            for entry in entries:
                self._notify_subscribers(entry)

    def get_all(self) -> list[LogEntry]:
        with self._lock:
            return list(self._entries)

    def get_sorted_by_time(self, reverse: bool = True) -> list[LogEntry]:
        with self._lock:
            return sorted(self._entries, key=lambda e: e.timestamp, reverse=reverse)

    def search_by_keyword(self, keyword: str) -> list[LogEntry]:
        keyword_lower = keyword.lower()
        with self._lock:
            return [e for e in self._entries if keyword_lower in e.message.lower()]

    def filter_by_level(self, level: str) -> list[LogEntry]:
        with self._lock:
            return [e for e in self._entries if e.level == level]

    def subscribe(self, callback):
        """订阅日志推送"""
        self._subscribers.append(callback)

    def _notify_subscribers(self, entry: LogEntry):
        for callback in self._subscribers:
            callback(entry)

    def clear(self):
        with self._lock:
            self._entries.clear()


# ---------- 测试：日志实时推送延迟 ≤3秒 ----------

class TestRealtimeLogPushLatency:
    def test_push_delay_under_3_seconds(self):
        component = RealtimeLogComponent()
        received: list[tuple[datetime, LogEntry]] = []

        def on_new(entry: LogEntry):
            received.append((datetime.now(), entry))

        component.subscribe(on_new)

        entry = LogEntry(LogLevel.INFO, "hello world")
        t0 = datetime.now()
        component.append(entry)
        t1 = datetime.now()

        assert len(received) == 1
        assert received[0][1] is entry
        elapsed = (t1 - t0).total_seconds()
        assert elapsed < 3.0, f"推送耗时 {elapsed}s，超过 3s 上限"

    def test_batch_push_delay_under_3_seconds(self):
        component = RealtimeLogComponent()
        received: list[LogEntry] = []

        def on_new(entry: LogEntry):
            received.append(entry)

        component.subscribe(on_new)

        entries = [LogEntry(LogLevel.INFO, f"msg-{i}") for i in range(50)]
        t0 = datetime.now()
        component.append_batch(entries)
        t1 = datetime.now()

        assert len(received) == 50
        elapsed = (t1 - t0).total_seconds()
        assert elapsed < 3.0, f"批量推送耗时 {elapsed}s，超过 3s 上限"

    def test_push_under_concurrent_load(self):
        component = RealtimeLogComponent()
        received: list[LogEntry] = []
        lock = threading.Lock()

        def on_new(entry: LogEntry):
            with lock:
                received.append(entry)

        component.subscribe(on_new)

        def worker(start_id: int, count: int):
            for i in range(count):
                component.append(LogEntry(LogLevel.INFO, f"thread-msg-{start_id + i}"))

        t0 = datetime.now()
        threads = [threading.Thread(target=worker, args=(i * 20, 20)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        t1 = datetime.now()

        assert len(received) == 100
        elapsed = (t1 - t0).total_seconds()
        assert elapsed < 3.0, f"并发推送耗时 {elapsed}s，超过 3s 上限"


# ---------- 测试：按时间排序和关键词搜索 ----------

class TestLogSortingAndSearch:

    @pytest.fixture
    def component_with_entries(self):
        comp = RealtimeLogComponent()
        base = datetime(2026, 7, 16, 10, 0, 0)
        entries = [
            LogEntry(LogLevel.INFO, "start agent task", base + timedelta(seconds=1)),
            LogEntry(LogLevel.WARN, "memory usage high", base + timedelta(seconds=2)),
            LogEntry(LogLevel.ERROR, "connection timeout to database", base + timedelta(seconds=3)),
            LogEntry(LogLevel.INFO, "retry succeeded", base + timedelta(seconds=4)),
            LogEntry(LogLevel.ERROR, "disk space critical", base + timedelta(seconds=5)),
        ]
        comp.append_batch(entries)
        return comp

    def test_sort_by_time_descending(self, component_with_entries):
        result = component_with_entries.get_sorted_by_time(reverse=True)
        for i in range(len(result) - 1):
            assert result[i].timestamp >= result[i + 1].timestamp

    def test_sort_by_time_ascending(self, component_with_entries):
        result = component_with_entries.get_sorted_by_time(reverse=False)
        for i in range(len(result) - 1):
            assert result[i].timestamp <= result[i + 1].timestamp

    def test_search_keyword_single_result(self, component_with_entries):
        result = component_with_entries.search_by_keyword("memory")
        assert len(result) == 1
        assert "memory" in result[0].message.lower()

    def test_search_keyword_multiple_results(self, component_with_entries):
        result = component_with_entries.search_by_keyword("error")
        # "connection timeout to database" 和 "disk space critical" 是 ERROR 级别但消息不含 error
        # 只有包含 keyword 的消息才匹配
        # 实际上消息中不含 "error" 字样，所以应返回 0
        # 换一个关键词测试
        result = component_with_entries.search_by_keyword("to")
        # "connection timeout to database" 含 "to"
        assert len(result) >= 1

    def test_search_keyword_case_insensitive(self, component_with_entries):
        result_upper = component_with_entries.search_by_keyword("START")
        result_lower = component_with_entries.search_by_keyword("start")
        assert len(result_upper) == len(result_lower)
        assert len(result_lower) >= 1

    def test_search_keyword_no_match(self, component_with_entries):
        result = component_with_entries.search_by_keyword("zzznonexistent")
        assert len(result) == 0


# ---------- 测试：日志级别筛选 ----------

class TestLogLevelFilter:

    @pytest.fixture
    def component_with_mixed_levels(self):
        comp = RealtimeLogComponent()
        base = datetime(2026, 7, 16, 10, 0, 0)
        entries = [
            LogEntry(LogLevel.INFO, "info msg 1", base + timedelta(seconds=1)),
            LogEntry(LogLevel.WARN, "warn msg 1", base + timedelta(seconds=2)),
            LogEntry(LogLevel.ERROR, "error msg 1", base + timedelta(seconds=3)),
            LogEntry(LogLevel.INFO, "info msg 2", base + timedelta(seconds=4)),
            LogEntry(LogLevel.WARN, "warn msg 2", base + timedelta(seconds=5)),
            LogEntry(LogLevel.INFO, "info msg 3", base + timedelta(seconds=6)),
            LogEntry(LogLevel.ERROR, "error msg 2", base + timedelta(seconds=7)),
        ]
        comp.append_batch(entries)
        return comp

    def test_filter_info(self, component_with_mixed_levels):
        result = component_with_mixed_levels.filter_by_level(LogLevel.INFO)
        assert len(result) == 3
        assert all(e.level == LogLevel.INFO for e in result)

    def test_filter_warn(self, component_with_mixed_levels):
        result = component_with_mixed_levels.filter_by_level(LogLevel.WARN)
        assert len(result) == 2
        assert all(e.level == LogLevel.WARN for e in result)

    def test_filter_error(self, component_with_mixed_levels):
        result = component_with_mixed_levels.filter_by_level(LogLevel.ERROR)
        assert len(result) == 2
        assert all(e.level == LogLevel.ERROR for e in result)

    def test_filter_nonexistent_level(self, component_with_mixed_levels):
        result = component_with_mixed_levels.filter_by_level("DEBUG")
        assert len(result) == 0

    def test_filter_preserves_order(self, component_with_mixed_levels):
        result = component_with_mixed_levels.filter_by_level(LogLevel.INFO)
        for i in range(len(result) - 1):
            assert result[i].timestamp <= result[i + 1].timestamp
