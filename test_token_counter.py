from datetime import datetime, timezone
from unittest.mock import patch
import pytest


class TokenCounter:
    """模拟 Token 计数器，支持次日零点重置"""

    def __init__(self):
        self._reset_date = None
        self._count = 0

    def _today(self):
        """返回今天的日期（不含时间），可被子类/测试覆写"""
        return datetime.now(timezone.utc).date()

    @property
    def count(self):
        return self._count

    def add(self, amount):
        now_date = self._today()
        if self._reset_date is None:
            self._reset_date = now_date
        elif now_date > self._reset_date:
            self._count = 0
            self._reset_date = now_date
        self._count += amount

    def reset_if_new_day(self):
        now_date = self._today()
        if self._reset_date is None:
            self._reset_date = now_date
            return False
        if now_date > self._reset_date:
            self._count = 0
            self._reset_date = now_date
            return True
        return False


def test_initial_count_is_zero():
    counter = TokenCounter()
    assert counter.count == 0


def test_count_increases_after_add():
    counter = TokenCounter()
    counter.add(100)
    assert counter.count == 100
    counter.add(50)
    assert counter.count == 150


def test_no_reset_within_same_day():
    counter = TokenCounter()
    counter.add(100)
    assert counter.reset_if_new_day() is False
    assert counter.count == 100


def test_reset_triggered_when_day_changes():
    counter = TokenCounter()
    fake_today = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=fake_today):
        counter.add(300)
        assert counter.count == 300
    next_day = datetime(2026, 7, 21, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=next_day):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


def test_add_cross_day_triggers_reset():
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=day1):
        counter.add(200)
        assert counter.count == 200
    with patch.object(counter, '_today', return_value=day2):
        counter.add(50)
        assert counter.count == 50


def test_after_reset_count_starts_from_zero():
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=day1):
        counter.add(999)
        assert counter.count == 999
    with patch.object(counter, '_today', return_value=day2):
        counter.add(1)
        assert counter.count == 1


def test_multiple_adds_after_reset():
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=day1):
        counter.add(100)
    with patch.object(counter, '_today', return_value=day2):
        counter.add(10)
        counter.add(20)
        counter.add(30)
        assert counter.count == 60


def test_midnight_exact_reset():
    counter = TokenCounter()
    with patch.object(counter, '_today', return_value=datetime(2026, 7, 20, tzinfo=timezone.utc).date()):
        counter.add(500)
    with patch.object(counter, '_today', return_value=datetime(2026, 7, 21, tzinfo=timezone.utc).date()):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


def test_cross_second_boundary():
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=day1):
        counter.add(100)
    with patch.object(counter, '_today', return_value=day2):
        counter.add(1)
        assert counter.count == 1
        counter.add(0)
        assert counter.count == 1


def test_cross_month_boundary():
    counter = TokenCounter()
    month_end = datetime(2026, 1, 31, tzinfo=timezone.utc).date()
    month_start = datetime(2026, 2, 1, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=month_end):
        counter.add(888)
    with patch.object(counter, '_today', return_value=month_start):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


def test_cross_year_boundary():
    counter = TokenCounter()
    year_end = datetime(2025, 12, 31, tzinfo=timezone.utc).date()
    year_start = datetime(2026, 1, 1, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=year_end):
        counter.add(9999)
    with patch.object(counter, '_today', return_value=year_start):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


def test_immediate_count_after_reset():
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=day1):
        counter.add(777)
        assert counter.count == 777
    with patch.object(counter, '_today', return_value=day2):
        counter.reset_if_new_day()
        assert counter.count == 0
        counter.add(1)
        assert counter.count == 1
