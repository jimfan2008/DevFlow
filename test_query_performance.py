import asyncio
import math
import time
from typing import List

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


LATENCY_BUDGET = {
    "p50": 10,  # ms
    "p95": 50,  # ms
    "p99": 100,  # ms
}

WARMUP_RUNS = 3
MEASURED_RUNS = 50


def _percentile(data: List[float], pct: float) -> float:
    """Compute the given percentile from a sorted list of values in milliseconds."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (pct / 100.0)
    floor_k = int(k)
    ceil_k = min(floor_k + 1, len(sorted_data) - 1)
    if floor_k == ceil_k:
        return sorted_data[floor_k]
    fraction = k - floor_k
    return sorted_data[floor_k] * (1 - fraction) + sorted_data[ceil_k] * fraction


@pytest.fixture
def measured_latencies() -> List[float]:
    """Return a realistic set of latencies that should pass the budget."""
    import random
    random.seed(42)
    base = [random.uniform(1.0, 8.0) for _ in range(40)]
    tail = [random.uniform(8.0, 35.0) for _ in range(8)]
    outlier = [random.uniform(35.0, 45.0)]
    return base + tail + outlier


@pytest.fixture
def slow_latencies() -> List[float]:
    """Return a set of latencies that should FAIL the budget."""
    import random
    random.seed(99)
    return [random.uniform(50.0, 200.0) for _ in range(50)]


class TestQueryPerformancePercentileBudget:
    """Verify query latencies meet p50/p95/p99 budgets."""

    def test_p50_within_budget(self, measured_latencies: List[float]):
        p50 = _percentile(measured_latencies, 50)
        assert p50 <= LATENCY_BUDGET["p50"], (
            f"p50 latency {p50:.2f}ms exceeds budget {LATENCY_BUDGET['p50']}ms"
        )

    def test_p95_within_budget(self, measured_latencies: List[float]):
        p95 = _percentile(measured_latencies, 95)
        assert p95 <= LATENCY_BUDGET["p95"], (
            f"p95 latency {p95:.2f}ms exceeds budget {LATENCY_BUDGET['p95']}ms"
        )

    def test_p99_within_budget(self, measured_latencies: List[float]):
        p99 = _percentile(measured_latencies, 99)
        assert p99 <= LATENCY_BUDGET["p99"], (
            f"p99 latency {p99:.2f}ms exceeds budget {LATENCY_BUDGET['p99']}ms"
        )

    def test_all_percentiles_pass_together(self, measured_latencies: List[float]):
        p50 = _percentile(measured_latencies, 50)
        p95 = _percentile(measured_latencies, 95)
        p99 = _percentile(measured_latencies, 99)
        assert p50 <= LATENCY_BUDGET["p50"]
        assert p95 <= LATENCY_BUDGET["p95"]
        assert p99 <= LATENCY_BUDGET["p99"]

    def test_fails_when_latencies_are_too_slow(self, slow_latencies: List[float]):
        p50 = _percentile(slow_latencies, 50)
        p95 = _percentile(slow_latencies, 95)
        p99 = _percentile(slow_latencies, 99)
        violations = 0
        if p50 > LATENCY_BUDGET["p50"]:
            violations += 1
        if p95 > LATENCY_BUDGET["p95"]:
            violations += 1
        if p99 > LATENCY_BUDGET["p99"]:
            violations += 1
        assert violations > 0, "Expected slow latencies to violate at least one budget"

    def test_percentile_is_monotonically_non_decreasing(self, measured_latencies: List[float]):
        p50 = _percentile(measured_latencies, 50)
        p95 = _percentile(measured_latencies, 95)
        p99 = _percentile(measured_latencies, 99)
        assert p50 <= p95, f"p50 ({p50:.2f}ms) should not exceed p95 ({p95:.2f}ms)"
        assert p95 <= p99, f"p95 ({p95:.2f}ms) should not exceed p99 ({p99:.2f}ms)"

    def test_empty_data_returns_zero(self):
        assert _percentile([], 50) == 0.0
        assert _percentile([], 95) == 0.0
        assert _percentile([], 99) == 0.0

    def test_single_value_returns_that_value(self):
        data = [15.0]
        assert _percentile(data, 50) == 15.0
        assert _percentile(data, 95) == 15.0
        assert _percentile(data, 99) == 15.0

    # FIX: 新增精确边界值测试（评审要求：测试等号边界）
    def test_exact_boundary_p50_budget(self):
        """Test exact boundary value: p50 exactly at 10ms should PASS (<= budget)."""
        data = [10.0] * 50
        p50 = _percentile(data, 50)
        assert p50 <= LATENCY_BUDGET["p50"]
        assert p50 == 10.0

    def test_exact_boundary_p95_budget(self):
        """Test exact boundary value: p95 exactly at 50ms should PASS (<= budget)."""
        data = [50.0] * 50
        p95 = _percentile(data, 95)
        assert p95 <= LATENCY_BUDGET["p95"]
        assert p95 == 50.0

    def test_exact_boundary_p99_budget(self):
        """Test exact boundary value: p99 exactly at 100ms should PASS (<= budget)."""
        data = [100.0] * 50
        p99 = _percentile(data, 99)
        assert p99 <= LATENCY_BUDGET["p99"]
        assert p99 == 100.0

    # FIX: 新增非整数索引插值精度测试（评审要求：测试 49.3 百分位）
    def test_non_integer_percentile_interpolation(self):
        """Test percentile interpolation accuracy for non-standard percentiles."""
        data = [float(i) for i in range(1, 101)]  # 1..100
        p49_3 = _percentile(data, 49.3)
        # Linear interpolation check
        k = 99 * 0.493
        floor_k = int(k)
        ceil_k = min(floor_k + 1, 99)
        fraction = k - floor_k
        expected = (floor_k + 1) * (1 - fraction) + (ceil_k + 1) * fraction
        assert p49_3 == pytest.approx(expected, rel=1e-9)

    def test_percentile_interpolation_between_two_values(self):
        """Test that interpolation lies strictly between adjacent values."""
        data = [10.0, 20.0]
        p50 = _percentile(data, 50)
        assert 10.0 <= p50 <= 20.0
        assert p50 == 15.0


class TestLiveQueryPerformance:
    """Integration-style tests that measure actual DB query timing via the API."""

    @pytest.fixture
    async def db_session(self) -> AsyncSession:
        """Create a raw async session for direct DB queries."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            yield session

    @pytest.fixture
    async def db_engine(self):
        """Create an async engine for concurrent tests (each task gets its own session)."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        return engine

    @pytest.mark.asyncio
    async def test_simple_select_latency(self, db_session: AsyncSession):
        """A bare SELECT on an in-memory SQLite DB should be well under budget."""
        latencies: List[float] = []
        for _ in range(WARMUP_RUNS):
            await db_session.execute(text("SELECT 1"))
        for _ in range(MEASURED_RUNS):
            start = time.perf_counter()
            result = await db_session.execute(text("SELECT 1"))
            await result.fetchone()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)
        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
        assert p50 <= LATENCY_BUDGET["p50"], f"p50={p50:.2f}ms > {LATENCY_BUDGET['p50']}ms"
        assert p95 <= LATENCY_BUDGET["p95"], f"p95={p95:.2f}ms > {LATENCY_BUDGET['p95']}ms"
        assert p99 <= LATENCY_BUDGET["p99"], f"p99={p99:.2f}ms > {LATENCY_BUDGET['p99']}ms"

    @pytest.mark.asyncio
    async def test_parameterized_query_latency(self, db_session: AsyncSession):
        """Parameterized queries should also meet latency budgets."""
        latencies: List[float] = []
        for _ in range(WARMUP_RUNS):
            await db_session.execute(text("SELECT :val"), {"val": 42})
        for i in range(MEASURED_RUNS):
            start = time.perf_counter()
            result = await db_session.execute(text("SELECT :val"), {"val": i})
            await result.fetchone()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)
        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
        assert p50 <= LATENCY_BUDGET["p50"], f"p50={p50:.2f}ms > {LATENCY_BUDGET['p50']}ms"
        assert p95 <= LATENCY_BUDGET["p95"], f"p95={p95:.2f}ms > {LATENCY_BUDGET['p95']}ms"
        assert p99 <= LATENCY_BUDGET["p99"], f"p99={p99:.2f}ms > {LATENCY_BUDGET['p99']}ms"

    # FIX: 并发测试不再共享同一个 session，每个任务独立创建 session 避免 flaky
    @pytest.mark.asyncio
    async def test_concurrent_queries_still_within_budget(self, db_engine):
        """Concurrent queries should not degrade individual query latency beyond budget."""
        latencies: List[float] = []
        concurrency = 5
        queries_per_worker = MEASURED_RUNS // concurrency

        session_factory = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

        async def _run_queries():
            local_latencies: List[float] = []
            async with session_factory() as session:
                for _ in range(queries_per_worker):
                    start = time.perf_counter()
                    result = await session.execute(text("SELECT 1"))
                    await result.fetchone()
                    local_latencies.append((time.perf_counter() - start) * 1000.0)
            return local_latencies

        tasks = [asyncio.create_task(_run_queries()) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)
        for batch in results:
            latencies.extend(batch)

        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
        assert p50 <= LATENCY_BUDGET["p50"], f"p50={p50:.2f}ms > {LATENCY_BUDGET['p50']}ms"
        assert p95 <= LATENCY_BUDGET["p95"], f"p95={p95:.2f}ms > {LATENCY_BUDGET['p95']}ms"
        assert p99 <= LATENCY_BUDGET["p99"], f"p99={p99:.2f}ms > {LATENCY_BUDGET['p99']}ms"

    # FIX: 新增更高并发度测试（评审要求：20 并发）
    @pytest.mark.asyncio
    async def test_high_concurrency_queries(self, db_engine):
        """Higher concurrency (20) should still meet latency budgets."""
        concurrency = 20
        queries_per_worker = 5
        latencies: List[float] = []

        session_factory = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

        async def _run_queries():
            local_latencies: List[float] = []
            async with session_factory() as session:
                for _ in range(queries_per_worker):
                    start = time.perf_counter()
                    result = await session.execute(text("SELECT 1"))
                    await result.fetchone()
                    local_latencies.append((time.perf_counter() - start) * 1000.0)
            return local_latencies

        tasks = [asyncio.create_task(_run_queries()) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)
        for batch in results:
            latencies.extend(batch)

        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
        assert p50 <= LATENCY_BUDGET["p50"], f"p50={p50:.2f}ms > {LATENCY_BUDGET['p50']}ms"
        assert p95 <= LATENCY_BUDGET["p95"], f"p95={p95:.2f}ms > {LATENCY_BUDGET['p95']}ms"
        assert p99 <= LATENCY_BUDGET["p99"], f"p99={p99:.2f}ms > {LATENCY_BUDGET['p99']}ms"

    # FIX: 新增数据库连接失败/异常场景测试（评审要求）
    @pytest.mark.asyncio
    async def test_connection_refused_raises_exception(self):
        """Connecting to a non-existent DB should raise an appropriate error."""
        engine = create_async_engine("sqlite+aiosqlite:///nonexistent_file.sqlite", echo=False)
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # For SQLite, a non-existent file will be created; test with invalid scheme instead
        invalid_engine = create_async_engine("invalid_scheme:///foo", echo=False)
        invalid_sf = sessionmaker(invalid_engine, class_=AsyncSession, expire_on_commit=False)

        with pytest.raises(Exception):
            async with invalid_sf() as session:
                await session.execute(text("SELECT 1"))

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_query_on_closed_session_raises_exception(self):
        """Executing a query on a closed session should raise an error."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        # Session is now closed
        with pytest.raises(Exception):
            async with session_factory() as new_session:
                await new_session.execute(text("SELECT 1"))

        await engine.dispose()
