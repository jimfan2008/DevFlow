import pytest
from datetime import datetime, timezone
from unittest.mock import Mock


class TokenCounter:
    """模拟 Token 消耗计数器，每日零点自动重置。"""

    def __init__(self, now_fn=None):
        self._count = 0
        self._current_date = None
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._sync_date()

    def _sync_date(self):
        now = self._now_fn()
        today = now.date()
        if self._current_date is not None and today != self._current_date:
            self._count = 0
        self._current_date = today

    @property
    def count(self) -> int:
        return self._count

    def add(self, tokens: int) -> None:
        self._sync_date()
        self._count += tokens


# ---------------------------------------------------------------------------
# 测试：当日零点重置（00:00:00.000000）
# ---------------------------------------------------------------------------

def test_initial_count_zero():
    """零点创建计数器时，计数应为 0。"""
    clock = Mock(return_value=datetime(2026, 7, 20, 0, 0, 0, 0, tzinfo=timezone.utc))
    counter = TokenCounter(now_fn=clock)
    assert counter.count == 0


def test_add_after_midnight_creation():
    """零点创建后 add，从 0 开始累积。"""
    clock = Mock(return_value=datetime(2026, 7, 20, 0, 0, 0, 0, tzinfo=timezone.utc))
    counter = TokenCounter(now_fn=clock)
    counter.add(100)
    assert counter.count == 100


# ---------------------------------------------------------------------------
# 测试：跨日零点重置（23:59:59 → 00:00:00）
# ---------------------------------------------------------------------------

def test_reset_across_days_boundary():
    """前一天 23:59:59 消耗后，跨日 add 应重置再累积。"""
    clock_values = [
        datetime(2026, 7, 20, 23, 59, 59, 0, tzinfo=timezone.utc),  # init
        datetime(2026, 7, 20, 23, 59, 59, 0, tzinfo=timezone.utc),  # 第1次 add
        datetime(2026, 7, 21, 0, 0, 0, 0, tzinfo=timezone.utc),     # 第2次 add（跨日）
    ]
    clock = Mock(side_effect=clock_values)
    counter = TokenCounter(now_fn=clock)
    counter.add(100)   # 第1天
    assert counter.count == 100
    counter.add(50)    # 第2天 → 重置后再加
    assert counter.count == 50, f"跨日应重置为 0 再加 50，实际为 {counter.count}"


def test_no_reset_within_same_day():
    """同一日内连续消耗不应重置。"""
    clock_values = [
        datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc),      # init
        datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc),      # add 200
        datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc),     # add 300
        datetime(2026, 7, 20, 23, 59, 58, tzinfo=timezone.utc),   # add 100
    ]
    clock = Mock(side_effect=clock_values)
    counter = TokenCounter(now_fn=clock)
    counter.add(200)
    counter.add(300)
    counter.add(100)
    assert counter.count == 600, "同一天内不应重置"


# ---------------------------------------------------------------------------
# 测试：跨年 / 跨月零点重置
# ---------------------------------------------------------------------------

def test_reset_across_months():
    """月末 → 下月初，计数器重置。"""
    clock_values = [
        datetime(2026, 1, 31, 23, 59, 59, 0, tzinfo=timezone.utc),  # init
        datetime(2026, 1, 31, 23, 59, 59, 0, tzinfo=timezone.utc),  # add 999
        datetime(2026, 2, 1, 0, 0, 0, 0, tzinfo=timezone.utc),      # add 10
    ]
    clock = Mock(side_effect=clock_values)
    counter = TokenCounter(now_fn=clock)
    counter.add(999)
    assert counter.count == 999
    counter.add(10)
    assert counter.count == 10, f"跨月应重置为 0 再加 10，实际为 {counter.count}"


def test_reset_across_years():
    """12月31日 → 1月1日，计数器重置。"""
    clock_values = [
        datetime(2025, 12, 31, 23, 59, 59, 0, tzinfo=timezone.utc),  # init
        datetime(2025, 12, 31, 23, 59, 59, 0, tzinfo=timezone.utc),  # add 2000
        datetime(2026, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc),       # add 1
    ]
    clock = Mock(side_effect=clock_values)
    counter = TokenCounter(now_fn=clock)
    counter.add(2000)
    assert counter.count == 2000
    counter.add(1)
    assert counter.count == 1, f"跨年应重置为 0 再加 1，实际为 {counter.count}"


# ---------------------------------------------------------------------------
# 测试：重置后从 0 开始累加
# ---------------------------------------------------------------------------

def test_counting_from_zero_after_reset():
    """重置后多次 add 从 0 开始累计。"""
    clock_values = [
        datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc),       # init
        datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc),       # add 500（第1天）
        datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc),        # add 0（第2天，触发重置）
        datetime(2026, 7, 21, 0, 0, 1, tzinfo=timezone.utc),        # add 100
        datetime(2026, 7, 21, 0, 0, 2, tzinfo=timezone.utc),        # add 200
    ]
    clock = Mock(side_effect=clock_values)
    counter = TokenCounter(now_fn=clock)

    counter.add(500)          # 第1天
    assert counter.count == 500

    counter.add(0)            # 触发重置
    assert counter.count == 0, f"跨日重置后应为 0，实际为 {counter.count}"

    counter.add(100)          # 从0开始
    assert counter.count == 100

    counter.add(200)
    assert counter.count == 300, f"累计应为 300，实际为 {counter.count}"


# ---------------------------------------------------------------------------
# 测试：多次跨日循环
# ---------------------------------------------------------------------------

def test_multiple_day_reset_cycle():
    """连续多日，每天消耗后次日重置。"""
    clock_values = [
        datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc),   # init
        datetime(2026, 7, 20, 10, 0, 0, tzinfo=timezone.utc),   # add 300
        datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc),   # add 200
        datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc),    # add 150（第2天）
        datetime(2026, 7, 22, 0, 0, 0, tzinfo=timezone.utc),    # add 75（第3天）
    ]
    clock = Mock(side_effect=clock_values)
    counter = TokenCounter(now_fn=clock)

    counter.add(300)
    counter.add(200)
    assert counter.count == 500, f"第1天累计应为 500，实际为 {counter.count}"

    counter.add(150)
    assert counter.count == 150, f"第2天重置后应为 150，实际为 {counter.count}"

    counter.add(75)
    assert counter.count == 75, f"第3天重置后应为 75，实际为 {counter.count}"


# ---------------------------------------------------------------------------
# 测试：边界值 — 秒级边界
# ---------------------------------------------------------------------------

def test_boundary_23_59_59_to_00_00_00():
    """23:59:59 → 00:00:00 的秒级边界。"""
    clock_first = Mock(return_value=datetime(2026, 7, 20, 23, 59, 59, 0, tzinfo=timezone.utc))
    counter = TokenCounter(now_fn=clock_first)
    counter.add(888)
    assert counter.count == 888

    # 下一瞬间跨日
    clock_second = Mock(return_value=datetime(2026, 7, 21, 0, 0, 0, 0, tzinfo=timezone.utc))
    counter._now_fn = clock_second
    counter.add(1)
    assert counter.count == 1, f"23:59:59→00:00:00 应重置为 0 再加 1，实际为 {counter.count}"


def test_boundary_midnight_exact_then_immediate():
    """零点整 add 后，同一日第二次 add 不应重置。"""
    clock_values = [
        datetime(2026, 8, 15, 0, 0, 0, 0, tzinfo=timezone.utc),  # init
        datetime(2026, 8, 15, 0, 0, 0, 0, tzinfo=timezone.utc),  # add 50
        datetime(2026, 8, 15, 0, 0, 1, 0, tzinfo=timezone.utc),  # add 25（同一日）
    ]
    clock = Mock(side_effect=clock_values)
    counter = TokenCounter(now_fn=clock)
    counter.add(50)
    assert counter.count == 50
    counter.add(25)
    assert counter.count == 75, "同一日不应重置"


# ---------------------------------------------------------------------------
# 测试：没有外部依赖 — 不使用任何外部文件或网络
# ---------------------------------------------------------------------------

def test_self_contained_no_external_deps():
    """所有测试数据内联，不依赖外部文件。"""
    clock = Mock(return_value=datetime(2026, 12, 1, 12, 0, 0, tzinfo=timezone.utc))
    counter = TokenCounter(now_fn=clock)
    counter.add(42)
    assert counter.count == 42
