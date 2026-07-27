from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, PropertyMock, patch
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


# ==============================
# 场景1：当日零点是否清零重置
# ==============================

def test_initial_count_is_zero():
    """初始计数器为0"""
    counter = TokenCounter()
    assert counter.count == 0


def test_count_increases_after_add():
    """同一日内 add 后计数器正确累加"""
    counter = TokenCounter()
    counter.add(100)
    assert counter.count == 100
    counter.add(50)
    assert counter.count == 150


def test_no_reset_within_same_day():
    """同一日内不会触发重置"""
    counter = TokenCounter()
    counter.add(100)
    assert counter.reset_if_new_day() is False
    assert counter.count == 100


# ==============================
# 场景2：跨日零点是否触发重置
# ==============================

def test_reset_triggered_when_day_changes():
    """跨日时 reset_if_new_day 返回 True 且计数归零"""
    counter = TokenCounter()
    # 固定当前日期
    fake_today = datetime(2026, 7, 20, tzinfo=timezone.utc).date()

    with patch.object(counter, '_today', return_value=fake_today):
        counter.add(300)
        assert counter.count == 300

    # 切换到次日
    next_day = datetime(2026, 7, 21, tzinfo=timezone.utc).date()
    with patch.object(counter, '_today', return_value=next_day):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


def test_add_cross_day_triggers_reset():
    """跨日时 add 自动触发重置然后累加"""
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()

    with patch.object(counter, '_today', return_value=day1):
        counter.add(200)
        assert counter.count == 200

    with patch.object(counter, '_today', return_value=day2):
        counter.add(50)
        assert counter.count == 50  # 先重置为0，再加50


# ==============================
# 场景3：重置后计数从0开始
# ==============================

def test_after_reset_count_starts_from_zero():
    """重置后首次 add 从0开始累加"""
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()

    with patch.object(counter, '_today', return_value=day1):
        counter.add(999)
        assert counter.count == 999

    with patch.object(counter, '_today', return_value=day2):
        counter.add(1)
        assert counter.count == 1  # 从0开始，加1


def test_multiple_adds_after_reset():
    """重置后多次 add 正常累加"""
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()

    with patch.object(counter, '_today', return_value=day1):
        counter.add(100)

    with patch.object(counter, '_today', return_value=day2):
        counter.add(10)
        counter.add(20)
        counter.add(30)
        assert counter.count == 60  # 0+10+20+30


# ==============================
# 边界测试：零点整重置瞬间
# ==============================

def test_midnight_exact_reset():
    """零点整（00:00:00）认定为新一天，触发重置"""
    counter = TokenCounter()
    # 前一天的 23:59:59
    with patch.object(counter, '_today', return_value=datetime(2026, 7, 20, tzinfo=timezone.utc).date()):
        counter.add(500)

    # 次日的 00:00:00
    with patch.object(counter, '_today', return_value=datetime(2026, 7, 21, tzinfo=timezone.utc).date()):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


# ==============================
# 边界测试：23:59:59 → 00:00:00 跨秒边界
# ==============================

def test_cross_second_boundary():
    """23:59:59 到 00:00:00 跨秒边界重置"""
    counter = TokenCounter()
    day1 = datetime(2026, 7, 20, tzinfo=timezone.utc).date()
    day2 = datetime(2026, 7, 21, tzinfo=timezone.utc).date()

    with patch.object(counter, '_today', return_value=day1):
        counter.add(100)

    with patch.object(counter, '_today', return_value=day2):
        counter.add(1)
        assert counter.count == 1  # 重置后加1
        counter.add(0)  # 加0不影响
        assert counter.count == 1


# ==============================
# 边界测试：跨月零点重置
# ==============================

def test_cross_month_boundary():
    """跨月时零点重置"""
    counter = TokenCounter()
    month_end = datetime(2026, 1, 31, tzinfo=timezone.utc).date()
    month_start = datetime(2026, 2, 1, tzinfo=timezone.utc).date()

    with patch.object(counter, '_today', return_value=month_end):
        counter.add(888)

    with patch.object(counter, '_today', return_value=month_start):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


# ==============================
# 边界测试：跨年零点重置
# ==============================

def test_cross_year_boundary():
    """跨年时零点重置"""
    counter = TokenCounter()
    year_end = datetime(2025, 12, 31, tzinfo=timezone.utc).date()
    year_start = datetime(2026, 1, 1, tzinfo=timezone.utc).date()

    with patch.object(counter, '_today', return_value=year_end):
        counter.add(9999)

    with patch.object(counter, '_today', return_value=year_start):
        assert counter.reset_if_new_day() is True
        assert counter.count == 0


# ==============================
# 边界测试：重置后立即计数
# ==============================

def test_immediate_count_after_reset():
    """重置后立即 add，从0开始"""
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
