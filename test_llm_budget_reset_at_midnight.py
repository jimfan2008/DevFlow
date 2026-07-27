from datetime import datetime, timezone, date
from enum import Enum
from typing import Optional

import pytest


# ====================================================================
# 领域模型
# ====================================================================

class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    TRIPPED = "tripped"


class TokenBudgetTracker:
    """Token 预算计数器，支持按日统计"""

    def __init__(self, daily_limit: int, current_date: Optional[date] = None):
        self.daily_limit = daily_limit
        self._current_date = current_date
        self._tracked_date: Optional[date] = None
        self._usage = 0

    @property
    def usage(self) -> int:
        return self._usage

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self._usage)

    @property
    def is_exhausted(self) -> bool:
        return self._usage >= self.daily_limit

    def set_date(self, d: date):
        """注入日期（测试用）"""
        self._current_date = d
        self._check_new_day()

    def consume(self, tokens: int):
        """消耗 token"""
        self._check_new_day()
        self._usage += tokens

    def _check_new_day(self):
        """检测是否跨日，若跨日则重置计数器"""
        now = self._get_date()
        if self._tracked_date is None:
            self._tracked_date = now
            return
        if now > self._tracked_date:
            self._reset()
            self._tracked_date = now

    def _reset(self):
        self._usage = 0

    def reset(self):
        """手动重置"""
        self._reset()

    def _get_date(self) -> date:
        if self._current_date is not None:
            return self._current_date
        return datetime.now(timezone.utc).date()


class TokenCircuitBreaker:
    """基于 token 预算的熔断器"""

    def __init__(self):
        self._state = CircuitBreakerState.CLOSED
        self._tripped_at: Optional[datetime] = None

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    @property
    def is_tripped(self) -> bool:
        return self._state == CircuitBreakerState.TRIPPED

    def should_allow(self) -> bool:
        return self._state in (CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN)

    def trip(self):
        self._state = CircuitBreakerState.TRIPPED
        self._tripped_at = datetime.now(timezone.utc)

    def close(self):
        self._state = CircuitBreakerState.CLOSED
        self._tripped_at = None

    def reset(self):
        self.close()


class LLMBudgetManager:
    """LLM API Token 预算管理：整合预算计数 + 熔断 + 按日重置"""

    def __init__(self, daily_limit: int = 1000000, current_date: Optional[date] = None):
        self.tracker = TokenBudgetTracker(daily_limit, current_date)
        self.breaker = TokenCircuitBreaker()

    @property
    def remaining(self) -> int:
        return self.tracker.remaining

    @property
    def usage(self) -> int:
        return self.tracker.usage

    @property
    def circuit_breaker_state(self) -> CircuitBreakerState:
        return self.breaker.state

    def submit_request(self, estimated_tokens: int = 100) -> dict:
        """提交 LLM 请求

        返回:
            {"status": "accepted"} — 请求通过
            {"status": "rejected", "reason": "..."} — 请求被拒
        """
        # 检测新日期 → 重置
        self.tracker.set_date(self.tracker._get_date())

        # 熔断器拒绝
        if not self.breaker.should_allow():
            return {"status": "rejected", "reason": "circuit_breaker_tripped"}

        # 预算不足 → 熔断
        if self.tracker.remaining < estimated_tokens:
            self.breaker.trip()
            return {"status": "rejected", "reason": "budget_exhausted"}

        # 消耗 budget
        self.tracker.consume(estimated_tokens)
        return {"status": "accepted"}

    def advance_to_next_day(self, next_date: date):
        """模拟跨日（测试用）"""
        self.tracker.set_date(next_date)
        self.breaker.reset()

    def force_trip(self):
        """强制触发熔断（测试用）"""
        self.breaker.trip()


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def budget_manager():
    """默认 daily_limit=1000"""
    return LLMBudgetManager(daily_limit=1000)


@pytest.fixture
def budget_manager_with_small_limit():
    """daily_limit=500，便于快速触达极限"""
    return LLMBudgetManager(daily_limit=500)


@pytest.fixture
def budget_manager_with_date():
    """预置日期 2026-07-20"""
    mgr = LLMBudgetManager(daily_limit=1000, current_date=date(2026, 7, 20))
    return mgr


# ====================================================================
# 测试 — 预算耗尽后熔断器 tripped
# ====================================================================

class TestBudgetExhaustionTripsBreaker:
    """验证预算耗尽时熔断器进入 tripped 状态"""

    def test_initial_state_is_closed(self, budget_manager):
        assert budget_manager.circuit_breaker_state == CircuitBreakerState.CLOSED

    def test_requests_accepted_when_budget_available(self, budget_manager):
        result = budget_manager.submit_request(100)
        assert result["status"] == "accepted"
        assert budget_manager.usage == 100

    def test_budget_exhaustion_triggers_tripped_breaker(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        # 5 次 * 100 = 500 = limit
        for _ in range(5):
            result = mgr.submit_request(100)
        # 第 5 次刚好用完，第 6 次应该被拒绝并熔断
        result = mgr.submit_request(100)
        assert result["status"] == "rejected"
        assert result["reason"] == "budget_exhausted"
        assert mgr.circuit_breaker_state == CircuitBreakerState.TRIPPED

    def test_subsequent_requests_rejected_when_tripped(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        for _ in range(6):
            mgr.submit_request(100)
        # 此时已熔断
        for _ in range(3):
            result = mgr.submit_request(100)
            assert result["status"] == "rejected"
            assert result["reason"] == "circuit_breaker_tripped"


# ====================================================================
# 测试 — 验收标准1：Token 预算计数器重置为 0
# ====================================================================

class TestAcceptanceCounterResetsToZero:
    """次日零点 Token 预算计数器重置为 0"""

    def test_counter_resets_to_zero_on_new_day(self, budget_manager_with_date):
        mgr = budget_manager_with_date
        # 当日消耗大量预算
        mgr.submit_request(800)
        assert mgr.usage == 800

        # 跨日到次日
        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.usage == 0

    def test_remaining_after_reset_equals_daily_limit(self, budget_manager_with_date):
        mgr = budget_manager_with_date
        mgr.submit_request(500)
        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.usage == 0
        assert mgr.remaining == 1000

    def test_counter_resets_to_zero_across_month_boundary(self):
        mgr = LLMBudgetManager(daily_limit=1000, current_date=date(2026, 1, 31))
        mgr.submit_request(999)
        assert mgr.usage == 999
        mgr.advance_to_next_day(date(2026, 2, 1))
        assert mgr.usage == 0

    def test_counter_resets_to_zero_across_year_boundary(self):
        mgr = LLMBudgetManager(daily_limit=1000, current_date=date(2025, 12, 31))
        mgr.submit_request(1000)
        assert mgr.usage == 1000
        mgr.advance_to_next_day(date(2026, 1, 1))
        assert mgr.usage == 0

    def test_counter_stays_nonzero_within_same_day(self, budget_manager_with_date):
        mgr = budget_manager_with_date
        mgr.submit_request(300)
        assert mgr.usage == 300
        # 同一天不重置
        mgr.submit_request(200)
        assert mgr.usage == 500


# ====================================================================
# 测试 — 验收标准2：熔断器状态从 tripped 恢复为 closed
# ====================================================================

class TestAcceptanceBreakerRecoversToClosed:
    """次日零点熔断器状态从 tripped 恢复为 closed"""

    def test_breaker_recovers_from_tripped_to_closed_on_new_day(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        # 耗尽预算 → 熔断
        for _ in range(6):
            mgr.submit_request(100)
        assert mgr.circuit_breaker_state == CircuitBreakerState.TRIPPED

        # 跨日
        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED

    def test_breaker_is_not_tripped_after_reset(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        for _ in range(6):
            mgr.submit_request(100)
        assert mgr.breaker.is_tripped is True

        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.breaker.is_tripped is False

    def test_breaker_should_allow_after_reset(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        for _ in range(6):
            mgr.submit_request(100)
        assert mgr.breaker.should_allow() is False

        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.breaker.should_allow() is True

    def test_breaker_state_transition_tripped_to_closed(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        mgr.force_trip()
        assert mgr.circuit_breaker_state == CircuitBreakerState.TRIPPED
        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED


# ====================================================================
# 测试 — 验收标准3：新请求可正常提交
# ====================================================================

class TestAcceptanceNewRequestAllowed:
    """次日重置后新请求可正常提交"""

    def test_new_request_accepted_after_midnight_reset(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        # 当日耗尽
        for _ in range(6):
            mgr.submit_request(100)
        assert mgr.breaker.is_tripped is True

        # 跨日后新请求可提交
        mgr.advance_to_next_day(date(2026, 7, 21))
        result = mgr.submit_request(100)
        assert result["status"] == "accepted"

    def test_new_request_consumes_from_fresh_budget(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        for _ in range(6):
            mgr.submit_request(100)
        mgr.advance_to_next_day(date(2026, 7, 21))

        result = mgr.submit_request(200)
        assert result["status"] == "accepted"
        assert mgr.usage == 200
        assert mgr.remaining == 300

    def test_multiple_new_requests_after_reset(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        for _ in range(6):
            mgr.submit_request(100)
        mgr.advance_to_next_day(date(2026, 7, 21))

        # 连续提交多个请求
        for _ in range(5):
            result = mgr.submit_request(100)
            assert result["status"] == "accepted"
        assert mgr.usage == 500

    def test_full_cycle_exhaust_and_reset_and_exhaust_again(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        # Day 1: 耗尽并熔断
        for _ in range(6):
            mgr.submit_request(100)
        assert mgr.circuit_breaker_state == CircuitBreakerState.TRIPPED
        assert mgr.usage == 500

        # Day 2: 重置后正常（1+4=5次请求，刚好用完500）
        mgr.advance_to_next_day(date(2026, 7, 21))
        result = mgr.submit_request(100)
        assert result["status"] == "accepted"
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED

        # Day 2: 再发4次，累计500
        for _ in range(4):
            mgr.submit_request(100)
        assert mgr.usage == 500
        # 第6次请求 → 预算耗尽 → 熔断
        result = mgr.submit_request(100)
        assert result["status"] == "rejected"
        assert result["reason"] == "budget_exhausted"
        assert mgr.circuit_breaker_state == CircuitBreakerState.TRIPPED

    def test_new_request_rejected_only_if_budget_exhausted_on_new_day(self, budget_manager_with_small_limit):
        mgr = budget_manager_with_small_limit
        # Day 1: 耗尽
        for _ in range(6):
            mgr.submit_request(100)

        # Day 2: 重置后立即用尽预算
        mgr.advance_to_next_day(date(2026, 7, 21))
        for _ in range(5):
            result = mgr.submit_request(100)
            assert result["status"] == "accepted"
        # 第 6 次 → 新一天也耗尽了
        result = mgr.submit_request(100)
        assert result["status"] == "rejected"
        assert result["reason"] == "budget_exhausted"


# ====================================================================
# 测试 — 完整端到端场景
# ====================================================================

class TestEndToEndMidnightReset:
    """完整端到端场景：耗尽 → 熔断 → 跨日 → 重置 → 正常提交"""

    def test_end_to_end_scenario(self):
        """完整流程：
        Day 1: 发送请求耗尽预算 → 熔断器 tripped → 后续请求被拒
        Day 2: 跨日零点 → 计数器归零 + 熔断器 closed → 新请求正常
        """
        mgr = LLMBudgetManager(daily_limit=1000, current_date=date(2026, 7, 20))

        # === Day 1 ===
        # 10 次 * 100 = 1000，刚好用完
        for i in range(10):
            result = mgr.submit_request(100)
            assert result["status"] == "accepted", f"Day 1 request {i+1} should be accepted"

        assert mgr.usage == 1000
        assert mgr.remaining == 0

        # 第 11 次 → 预算耗尽 → 熔断
        result = mgr.submit_request(100)
        assert result["status"] == "rejected"
        assert result["reason"] == "budget_exhausted"
        assert mgr.circuit_breaker_state == CircuitBreakerState.TRIPPED

        # 第 12 次 → 熔断拒绝
        result = mgr.submit_request(100)
        assert result["status"] == "rejected"
        assert result["reason"] == "circuit_breaker_tripped"

        # === Day 2: 零点重置 ===
        mgr.advance_to_next_day(date(2026, 7, 21))

        # 验收标准1：计数器归零
        assert mgr.usage == 0
        assert mgr.remaining == 1000

        # 验收标准2：熔断器恢复 closed
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED
        assert mgr.breaker.is_tripped is False
        assert mgr.breaker.should_allow() is True

        # 验收标准3：新请求正常提交
        result = mgr.submit_request(100)
        assert result["status"] == "accepted"
        assert mgr.usage == 100

        # 连续多个请求也可正常提交
        for i in range(9):
            result = mgr.submit_request(100)
            assert result["status"] == "accepted"

        assert mgr.usage == 1000

    def test_three_day_cycle(self):
        """三天循环验证"""
        mgr = LLMBudgetManager(daily_limit=500, current_date=date(2026, 7, 20))

        # Day 1: 耗尽
        for _ in range(6):
            mgr.submit_request(100)
        assert mgr.breaker.is_tripped is True

        # Day 2: 重置 → 正常 → 再耗尽
        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.usage == 0
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED

        for _ in range(5):
            result = mgr.submit_request(100)
            assert result["status"] == "accepted"
        result = mgr.submit_request(100)
        assert result["status"] == "rejected"
        assert mgr.circuit_breaker_state == CircuitBreakerState.TRIPPED

        # Day 3: 再次重置 → 正常
        mgr.advance_to_next_day(date(2026, 7, 22))
        assert mgr.usage == 0
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED
        result = mgr.submit_request(100)
        assert result["status"] == "accepted"
        assert mgr.usage == 100

    def test_partial_consumption_then_new_day(self):
        """未耗尽的预算跨日后也重置"""
        mgr = LLMBudgetManager(daily_limit=1000, current_date=date(2026, 7, 20))
        mgr.submit_request(300)
        assert mgr.usage == 300
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED  # 未耗尽，未熔断

        mgr.advance_to_next_day(date(2026, 7, 21))
        assert mgr.usage == 0
        assert mgr.circuit_breaker_state == CircuitBreakerState.CLOSED
        result = mgr.submit_request(100)
        assert result["status"] == "accepted"
        assert mgr.usage == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
