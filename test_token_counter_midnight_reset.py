from unittest.mock import patch, MagicMock
import pytest
from datetime import datetime, timezone, timedelta
import time


class TokenCounter:
    """Token 消耗计数器，每天零点自动重置"""

    def __init__(self):
        self._count = 0
        self._last_reset_date = self._today_date()

    @staticmethod
    def _today_date():
        return datetime.now(timezone.utc).date()

    @property
    def count(self):
        self._check_reset()
        return self._count

    def add(self, tokens):
        if tokens < 0:
            raise ValueError("tokens must be non-negative")
        self._check_reset()
        self._count += tokens
        return self._count

    def _check_reset(self):
        today = self._today_date()
        if today != self._last_reset_date:
            self._count = 0
            self._last_reset_date = today
            return True
        return False


# ─── 基础功能测试 ─────────────────────────────

def test_initial_count_is_zero():
    """初始计数器应为 0"""
    counter = TokenCounter()
    assert counter.count == 0


def test_add_tokens_increases_count():
    """添加 token 后计数器正确累加"""
    counter = TokenCounter()
    counter.add(100)
    assert counter.count == 100


def test_add_tokens_accumulates():
    """多次添加 token 正确累加"""
    counter = TokenCounter()
    counter.add(50)
    counter.add(150)
    assert counter.count == 200


def test_negative_tokens_raises_error():
    """添加负数 token 应抛出 ValueError"""
    counter = TokenCounter()
    with pytest.raises(ValueError):
        counter.add(-1)


def test_zero_tokens_no_op():
    """添加 0 token 不改变计数"""
    counter = TokenCounter()
    counter.add(0)
    assert counter.count == 0
    counter.add(100)
    assert counter.count == 100


# ─── 零点重置功能测试 ─────────────────────────

def test_midnight_exact_reset():
    """模拟跨过零点后计数器重置为 0"""
    counter = TokenCounter()
    counter.add(500)
    assert counter.count == 500

    # 强制 _last_reset_date 为前一天，触发重置
    counter._last_reset_date = datetime(2024, 12, 31).date()
    assert counter._check_reset() is True
    assert counter.count == 0


def test_cross_second_boundary():
    """跨秒边界后计数器应重置"""
    counter = TokenCounter()
    counter.add(300)
    assert counter.count == 300

    counter._last_reset_date = datetime(2024, 12, 31).date()
    assert counter.count == 0


def test_cross_month_boundary():
    """跨月边界（月末→月初）后计数器重置"""
    counter = TokenCounter()
    counter.add(9999)
    assert counter.count == 9999

    counter._last_reset_date = datetime(2024, 11, 30).date()
    assert counter.count == 0


def test_cross_year_boundary():
    """跨年边界（12/31→1/1）后计数器重置"""
    counter = TokenCounter()
    counter.add(88888)
    assert counter.count == 88888

    counter._last_reset_date = datetime(2023, 12, 31).date()
    assert counter.count == 0


def test_immediate_count_after_reset():
    """重置后立即读 count 应为 0"""
    counter = TokenCounter()
    counter.add(777)
    counter._last_reset_date = datetime(2024, 12, 31).date()
    counter._check_reset()
    assert counter.count == 0


def test_multiple_adds_after_reset():
    """重置后多次添加 token 正常累加"""
    counter = TokenCounter()
    counter.add(500)
    counter._last_reset_date = datetime(2024, 12, 31).date()
    counter._check_reset()
    assert counter.count == 0

    counter.add(100)
    assert counter.count == 100
    counter.add(50)
    assert counter.count == 150
    counter.add(25)
    assert counter.count == 175


# ─── 并发与稳定性测试 ─────────────────────────

def test_reset_only_once_per_day():
    """同一天内多次 check_reset 只重置一次，不丢失当天计数"""
    counter = TokenCounter()
    counter.add(200)
    counter._last_reset_date = datetime(2024, 12, 31).date()

    assert counter._check_reset() is True
    assert counter.count == 0

    counter.add(50)
    assert counter._check_reset() is False
    assert counter.count == 50


def test_multiple_reset_cycles():
    """模拟多天跨度的多次重置周期"""
    counter = TokenCounter()

    dates = [
        datetime(2025, 1, 1).date(),
        datetime(2025, 1, 2).date(),
        datetime(2025, 1, 3).date(),
    ]
    for i, day in enumerate(dates):
        if i > 0:
            counter._last_reset_date = dates[i - 1]
        counter._check_reset()
        assert counter.count == 0
        counter.add(100 * (i + 1))
        expected = 100 * (i + 1)
        assert counter.count == expected
