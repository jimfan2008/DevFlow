"""测试用例：Agent执行实时日志组件"""

import time
import json
import threading
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
from typing import List, Optional, Callable


# ---- 被测试的组件代码 ----

class LogLevel(Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class LogEntry:
    def __init__(self, level: LogLevel, message: str, timestamp: Optional[datetime] = None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class RealtimeLogComponent:
    def __init__(self, max_entries: int = 10000):
        self._logs: deque = deque(maxlen=max_entries)
        self._subscribers: List[Callable] = []
        self._lock = threading.Lock()

    def add_log(self, level: LogLevel, message: str, timestamp: Optional[datetime] = None) -> LogEntry:
        entry = LogEntry(level=level, message=message, timestamp=timestamp)
        with self._lock:
            self._logs.append(entry)
        for callback in self._subscribers:
            callback(entry)
        return entry

    def subscribe(self, callback: Callable) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        self._subscribers.remove(callback)

    def get_logs(
        self,
        level: Optional[LogLevel] = None,
        keyword: Optional[str] = None,
        sort_by_time: bool = True,
    ) -> List[LogEntry]:
        with self._lock:
            result = list(self._logs)

        if level is not None:
            result = [e for e in result if e.level == level]
        if keyword is not None:
            result = [e for e in result if keyword.lower() in e.message.lower()]
        if sort_by_time:
            result = sorted(result, key=lambda e: e.timestamp)
        return result

    def get_logs_since(self, since: datetime) -> List[LogEntry]:
        return [e for e in self.get_logs() if e.timestamp >= since]

    def clear(self) -> None:
        with self._lock:
            self._logs.clear()


# ---- 测试代码 ----

import pytest


class TestRealtimeLogPushDelay:
    """验证日志实时推送延迟 ≤ 3秒"""

    def test_push_delay_under_3_seconds(self):
        component = RealtimeLogComponent()
        received: List[LogEntry] = []

        def on_new(entry: LogEntry):
            received.append(entry)

        component.subscribe(on_new)

        start = time.monotonic()
        component.add_log(LogLevel.INFO, "test message")
        elapsed = time.monotonic() - start

        assert len(received) == 1
        assert received[0].message == "test message"
        assert elapsed < 3.0, f"推送延迟 {elapsed:.4f}s 超过 3 秒"

    def test_push_delay_under_3_seconds_concurrent(self):
        component = RealtimeLogComponent()
        received: List[LogEntry] = []
        lock = threading.Lock()

        def on_new(entry: LogEntry):
            with lock:
                received.append(entry)

        component.subscribe(on_new)

        def producer():
            for i in range(50):
                component.add_log(LogLevel.INFO, f"msg-{i}")

        start = time.monotonic()
        t = threading.Thread(target=producer)
        t.start()
        t.join(timeout=10)
        elapsed = time.monotonic() - start

        assert len(received) == 50
        assert elapsed < 3.0, f"并发推送总耗时 {elapsed:.4f}s 超过 3 秒"


class TestSortAndSearch:
    """验证支持按时间排序和关键词搜索"""

    def test_sort_by_time_asc(self):
        component = RealtimeLogComponent()
        base = datetime(2026, 7, 15, 10, 0, 0)

        component.add_log(LogLevel.INFO, "third", timestamp=base + timedelta(seconds=3))
        component.add_log(LogLevel.WARN, "first", timestamp=base + timedelta(seconds=1))
        component.add_log(LogLevel.ERROR, "second", timestamp=base + timedelta(seconds=2))

        result = component.get_logs(sort_by_time=True)
        assert len(result) == 3
        assert result[0].message == "first"
        assert result[1].message == "second"
        assert result[2].message == "third"

    def test_sort_disabled_preserves_insertion_order(self):
        component = RealtimeLogComponent()
        base = datetime(2026, 7, 15, 10, 0, 0)

        component.add_log(LogLevel.INFO, "a", timestamp=base + timedelta(seconds=3))
        component.add_log(LogLevel.WARN, "b", timestamp=base + timedelta(seconds=1))

        result = component.get_logs(sort_by_time=False)
        assert result[0].message == "a"
        assert result[1].message == "b"

    def test_keyword_search_case_insensitive(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.INFO, "Connection established")
        component.add_log(LogLevel.WARN, "connection timeout")
        component.add_log(LogLevel.ERROR, "Disk full")

        result = component.get_logs(keyword="connection")
        assert len(result) == 2
        assert all("connection" in e.message.lower() for e in result)

    def test_keyword_search_no_match(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.INFO, "hello world")

        result = component.get_logs(keyword="xyz123")
        assert len(result) == 0

    def test_combined_keyword_and_sort(self):
        component = RealtimeLogComponent()
        base = datetime(2026, 7, 15, 10, 0, 0)

        component.add_log(LogLevel.INFO, "error in module A", timestamp=base + timedelta(seconds=3))
        component.add_log(LogLevel.WARN, "error in module B", timestamp=base + timedelta(seconds=1))
        component.add_log(LogLevel.ERROR, "other message", timestamp=base + timedelta(seconds=2))

        result = component.get_logs(keyword="module", sort_by_time=True)
        assert len(result) == 2
        assert result[0].message == "error in module B"
        assert result[1].message == "error in module A"


class TestLogLevelFilter:
    """验证日志级别筛选（INFO/WARN/ERROR）可用"""

    def test_filter_info_only(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.INFO, "info msg")
        component.add_log(LogLevel.WARN, "warn msg")
        component.add_log(LogLevel.ERROR, "error msg")

        result = component.get_logs(level=LogLevel.INFO)
        assert len(result) == 1
        assert result[0].level == LogLevel.INFO
        assert result[0].message == "info msg"

    def test_filter_warn_only(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.INFO, "info msg")
        component.add_log(LogLevel.WARN, "warn msg 1")
        component.add_log(LogLevel.WARN, "warn msg 2")
        component.add_log(LogLevel.ERROR, "error msg")

        result = component.get_logs(level=LogLevel.WARN)
        assert len(result) == 2
        assert all(e.level == LogLevel.WARN for e in result)

    def test_filter_error_only(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.ERROR, "critical failure")
        component.add_log(LogLevel.INFO, "normal")

        result = component.get_logs(level=LogLevel.ERROR)
        assert len(result) == 1
        assert result[0].message == "critical failure"

    def test_filter_no_level_returns_all(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.INFO, "a")
        component.add_log(LogLevel.WARN, "b")
        component.add_log(LogLevel.ERROR, "c")

        result = component.get_logs()
        assert len(result) == 3

    def test_filter_combined_with_keyword(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.ERROR, "disk error")
        component.add_log(LogLevel.ERROR, "network error")
        component.add_log(LogLevel.WARN, "disk warning")

        result = component.get_logs(level=LogLevel.ERROR, keyword="disk")
        assert len(result) == 1
        assert result[0].message == "disk error"


class TestLogEntryStructure:
    """验证日志条目结构完整"""

    def test_log_entry_to_dict(self):
        ts = datetime(2026, 7, 15, 10, 30, 0)
        entry = LogEntry(LogLevel.WARN, "test warning", timestamp=ts)

        d = entry.to_dict()
        assert d["level"] == "WARN"
        assert d["message"] == "test warning"
        assert d["timestamp"] == "2026-07-15T10:30:00"

    def test_log_entry_default_timestamp(self):
        before = datetime.now()
        entry = LogEntry(LogLevel.INFO, "now")
        after = datetime.now()

        assert before <= entry.timestamp <= after


class TestClearAndSubscriberManagement:
    """验证清除和订阅管理功能"""

    def test_clear_removes_all_logs(self):
        component = RealtimeLogComponent()
        component.add_log(LogLevel.INFO, "msg1")
        component.add_log(LogLevel.WARN, "msg2")
        component.clear()

        assert len(component.get_logs()) == 0

    def test_unsubscribe_stops_receiving(self):
        component = RealtimeLogComponent()
        received: List[LogEntry] = []

        def cb(entry: LogEntry):
            received.append(entry)

        component.subscribe(cb)
        component.add_log(LogLevel.INFO, "before unsubscribe")
        component.unsubscribe(cb)
        component.add_log(LogLevel.WARN, "after unsubscribe")

        assert len(received) == 1
        assert received[0].message == "before unsubscribe"

    def test_multiple_subscribers(self):
        component = RealtimeLogComponent()
        rec1: List[LogEntry] = []
        rec2: List[LogEntry] = []

        def cb1(e: LogEntry):
            rec1.append(e)

        def cb2(e: LogEntry):
            rec2.append(e)

        component.subscribe(cb1)
        component.subscribe(cb2)
        component.add_log(LogLevel.INFO, "shared")

        assert len(rec1) == 1
        assert len(rec2) == 1
        assert rec1[0].message == rec2[0].message == "shared"
