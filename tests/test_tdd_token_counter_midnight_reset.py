"""TDD 测试用例：Token计数器次日零点重置"""

from datetime import date
from freezegun import freeze_time
import pytest


class TokenCounter:
    """Token消耗计数器，次日零点自动重置。"""

    def __init__(self):
        self._daily_total = 0
        self._current_date = date.today()

    def record_tokens(self, count: int) -> int:
        """记录token消耗，返回累计值。"""
        self._check_midnight_reset()
        self._daily_total += count
        return self._daily_total

    def get_daily_total(self) -> int:
        """获取当日累计token数。"""
        self._check_midnight_reset()
        return self._daily_total

    def force_reset(self) -> None:
        """强制重置（用于测试）。"""
        self._daily_total = 0

    def _check_midnight_reset(self):
        """如果日期已变更，重置计数器。"""
        today = date.today()
        if today != self._current_date:
            self._daily_total = 0
            self._current_date = today


class TestTokenCounterMidnightReset:
    """验证Token消耗计数器在次日零点自动重置。"""

    def test_midnight_resets_counter_to_zero(self):
        """验收标准1：次日零点Token计数器值重置为0。"""
        with freeze_time("2026-07-19 23:59:59"):
            counter = TokenCounter()
            counter.record_tokens(500)
            assert counter.get_daily_total() == 500

        with freeze_time("2026-07-20 00:00:00"):
            assert counter.get_daily_total() == 0

    def test_new_requests_accumulate_from_zero_after_reset(self):
        """验收标准2：重置后新的推理请求从0开始累加。"""
        with freeze_time("2026-07-19 12:00:00"):
            counter = TokenCounter()
            counter.record_tokens(1000)
            assert counter.get_daily_total() == 1000

        with freeze_time("2026-07-20 00:00:00"):
            assert counter.get_daily_total() == 0
            counter.record_tokens(200)
            assert counter.get_daily_total() == 200
            counter.record_tokens(300)
            assert counter.get_daily_total() == 500

    def test_midnight_boundary_multi_operations(self):
        """午夜边界多次操作的正确性验证。"""
        with freeze_time("2026-07-19 23:59:58"):
            counter = TokenCounter()
            counter.record_tokens(100)
            assert counter.get_daily_total() == 100

        with freeze_time("2026-07-19 23:59:59"):
            counter.record_tokens(50)
            assert counter.get_daily_total() == 150

        with freeze_time("2026-07-20 00:00:00"):
            assert counter.get_daily_total() == 0
            counter.record_tokens(30)
            assert counter.get_daily_total() == 30

        with freeze_time("2026-07-20 00:00:01"):
            counter.record_tokens(20)
            assert counter.get_daily_total() == 50

    def test_consecutive_days_reset(self):
        """连续多天的重置行为验证。"""
        counter = TokenCounter()

        with freeze_time("2026-07-19 08:00:00"):
            counter.record_tokens(800)
            assert counter.get_daily_total() == 800

        with freeze_time("2026-07-20 00:00:00"):
            assert counter.get_daily_total() == 0
            counter.record_tokens(1200)
            assert counter.get_daily_total() == 1200

        with freeze_time("2026-07-21 00:00:00"):
            assert counter.get_daily_total() == 0
            counter.record_tokens(300)
            assert counter.get_daily_total() == 300

    def test_same_day_no_reset(self):
        """同一天内操作不应触发重置。"""
        with freeze_time("2026-07-20 08:00:00"):
            counter = TokenCounter()
            counter.record_tokens(100)
            assert counter.get_daily_total() == 100

        with freeze_time("2026-07-20 12:00:00"):
            counter.record_tokens(200)
            assert counter.get_daily_total() == 300

        with freeze_time("2026-07-20 23:59:59"):
            counter.record_tokens(50)
            assert counter.get_daily_total() == 350

    def test_init_daily_total_is_zero(self):
        """新初始化的计数器初始值为0。"""
        with freeze_time("2026-07-20 00:00:00"):
            counter = TokenCounter()
            assert counter.get_daily_total() == 0

    def test_reset_only_at_date_boundary(self):
        """时间未跨越日期边界时不应重置。"""
        with freeze_time("2026-07-20 12:00:00"):
            counter = TokenCounter()
            counter.record_tokens(500)
            assert counter.get_daily_total() == 500

        with freeze_time("2026-07-20 12:30:00"):
            counter.record_tokens(100)
            assert counter.get_daily_total() == 600

        with freeze_time("2026-07-20 23:30:00"):
            counter.record_tokens(50)
            assert counter.get_daily_total() == 650
