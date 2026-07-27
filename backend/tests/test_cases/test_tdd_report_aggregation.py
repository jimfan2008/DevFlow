from __future__ import annotations
import time
import asyncio
from dataclasses import dataclass, field
import pytest

STAGES = ["unit", "integration", "system", "e2e"]


class TimeoutError(Exception):
    pass


@dataclass
class StageReport:
    stage_id: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass
class ComprehensiveReport:
    generated_at: float = 0.0
    elapsed_ms: float = 0.0
    stages: dict[str, StageReport] = field(default_factory=dict)
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    overall_status: str = "unknown"


def aggregate(reports: list[StageReport]) -> ComprehensiveReport:
    start = time.monotonic()
    if not isinstance(reports, list):
        raise TypeError("reports must be a list")
    for r in reports:
        if not isinstance(r, StageReport):
            raise TypeError("each report must be a StageReport instance")
        if r.total < 0 or r.passed < 0 or r.failed < 0 or r.skipped < 0:
            raise ValueError(f"negative values not allowed in report '{r.stage_id}'")
        if r.passed + r.failed + r.skipped != r.total:
            raise ValueError(
                f"passed+failed+skipped ({r.passed}+{r.failed}+{r.skipped}) "
                f"!= total ({r.total}) for report '{r.stage_id}'"
            )
    stage_ids = [r.stage_id for r in reports]
    if len(stage_ids) != len(set(stage_ids)):
        raise ValueError("duplicate stage_id found in reports")
    for r in reports:
        if r.stage_id not in STAGES:
            raise ValueError(f"unexpected stage_id '{r.stage_id}', expected one of {STAGES}")
    seen_order = [r.stage_id for r in reports if r.stage_id in STAGES]
    expected_order = [s for s in STAGES if s in seen_order]
    if seen_order != expected_order:
        raise ValueError(f"stage order mismatch: expected {expected_order}, got {seen_order}")
    report = ComprehensiveReport()
    report.generated_at = time.time()
    report.stages = {}
    report.total_tests = 0
    report.total_passed = 0
    report.total_failed = 0
    report.total_skipped = 0
    for s in STAGES:
        matching = [r for r in reports if r.stage_id == s]
        if matching:
            r = matching[0]
            report.stages[s] = r
            report.total_tests += r.total
            report.total_passed += r.passed
            report.total_failed += r.failed
            report.total_skipped += r.skipped
    if report.total_failed > 0:
        report.overall_status = "failed"
    elif report.total_tests == 0:
        report.overall_status = "empty"
    else:
        report.overall_status = "passed"
    report.elapsed_ms = (time.monotonic() - start) * 1000
    return report


async def aggregate_with_timeout(
    reports: list[StageReport], timeout_seconds: float = 60.0
) -> ComprehensiveReport:
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, aggregate, reports),
            timeout=timeout_seconds,
        )
        return result
    except asyncio.TimeoutError:
        raise TimeoutError(f"aggregation timed out after {timeout_seconds}s")


class TestAggregateBasic:
    def test_normal_aggregation_all_four_stages(self):
        r1 = StageReport(
            stage_id="unit", total=10, passed=9, failed=1, skipped=0,
            errors=["test_login failed"],
        )
        r2 = StageReport(stage_id="integration", total=5, passed=5, failed=0, skipped=0)
        r3 = StageReport(stage_id="system", total=8, passed=8, failed=0, skipped=0)
        r4 = StageReport(stage_id="e2e", total=3, passed=3, failed=0, skipped=0)
        result = aggregate([r1, r2, r3, r4])
        assert isinstance(result, ComprehensiveReport)
        assert result.total_tests == 26
        assert result.total_passed == 25
        assert result.total_failed == 1
        assert result.total_skipped == 0
        assert result.overall_status == "failed"
        assert len(result.stages) == 4
        assert list(result.stages.keys()) == STAGES
        assert result.stages["unit"].errors == ["test_login failed"]

    def test_elapsed_ms_is_positive(self):
        result = aggregate([StageReport(stage_id="unit", total=1, passed=1, failed=0, skipped=0)])
        assert result.elapsed_ms >= 0
        assert result.generated_at > 0

    def test_all_passed_sets_overall_status_passed(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0),
            StageReport(stage_id="integration", total=5, passed=5, failed=0, skipped=0),
        ]
        result = aggregate(reports)
        assert result.overall_status == "passed"
        assert result.total_failed == 0

    def test_skipped_counts_are_accumulated(self):
        result = aggregate(
            [StageReport(stage_id="unit", total=10, passed=7, failed=1, skipped=2)]
        )
        assert result.total_skipped == 2
        assert result.total_tests == 10

    def test_aggregation_completes_under_60_seconds(self):
        start = time.monotonic()
        aggregate(
            [StageReport(stage_id="unit", total=1000, passed=900, failed=50, skipped=50)]
        )
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 60000


class TestAggregateEdgeCases:
    def test_empty_list_returns_empty_report(self):
        result = aggregate([])
        assert result.total_tests == 0
        assert result.total_passed == 0
        assert result.total_failed == 0
        assert result.total_skipped == 0
        assert result.overall_status == "empty"
        assert result.stages == {}

    def test_more_than_four_reports_filters_unknown_stages(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0),
            StageReport(stage_id="integration", total=5, passed=5, failed=0, skipped=0),
            StageReport(stage_id="system", total=8, passed=8, failed=0, skipped=0),
            StageReport(stage_id="e2e", total=3, passed=3, failed=0, skipped=0),
            StageReport(stage_id="performance", total=2, passed=2, failed=0, skipped=0),
        ]
        result = aggregate(reports)
        assert len(result.stages) == 4
        assert "performance" not in result.stages

    def test_all_zero_stats_sets_overall_status_empty(self):
        result = aggregate(
            [StageReport(stage_id="unit", total=0, passed=0, failed=0, skipped=0)]
        )
        assert result.total_tests == 0
        assert result.total_passed == 0
        assert result.total_failed == 0
        assert result.total_skipped == 0
        assert result.overall_status == "empty"

    def test_duplicate_stage_id_raises_value_error(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0),
            StageReport(stage_id="unit", total=5, passed=5, failed=0, skipped=0),
        ]
        with pytest.raises(ValueError, match="duplicate stage_id"):
            aggregate(reports)

    def test_stage_order_mismatch_raises_value_error(self):
        reports = [
            StageReport(stage_id="system", total=8, passed=8, failed=0, skipped=0),
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0),
        ]
        with pytest.raises(ValueError, match="stage order mismatch"):
            aggregate(reports)

    def test_invalid_sum_passed_failed_skipped_not_equal_total(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=9, failed=0, skipped=0)
        ]
        with pytest.raises(ValueError, match="passed.*failed.*skipped.*!=.*total"):
            aggregate(reports)

    def test_negative_total_raises_value_error(self):
        reports = [
            StageReport(stage_id="unit", total=-1, passed=0, failed=0, skipped=0)
        ]
        with pytest.raises(ValueError, match="negative"):
            aggregate(reports)

    def test_negative_passed_raises_value_error(self):
        reports = [
            StageReport(stage_id="unit", total=5, passed=-1, failed=0, skipped=0)
        ]
        with pytest.raises(ValueError, match="negative"):
            aggregate(reports)

    def test_negative_failed_raises_value_error(self):
        reports = [
            StageReport(stage_id="unit", total=5, passed=0, failed=-1, skipped=0)
        ]
        with pytest.raises(ValueError, match="negative"):
            aggregate(reports)

    def test_negative_skipped_raises_value_error(self):
        reports = [
            StageReport(stage_id="unit", total=5, passed=0, failed=0, skipped=-1)
        ]
        with pytest.raises(ValueError, match="negative"):
            aggregate(reports)

    def test_unexpected_stage_id_raises_value_error(self):
        reports = [
            StageReport(stage_id="unknown_stage", total=1, passed=1, failed=0, skipped=0)
        ]
        with pytest.raises(ValueError, match="unexpected stage_id"):
            aggregate(reports)

    def test_not_a_list_raises_type_error(self):
        with pytest.raises(TypeError, match="reports must be a list"):
            aggregate("not_a_list")

    def test_non_stage_report_element_raises_type_error(self):
        with pytest.raises(TypeError, match="each report must be a StageReport"):
            aggregate([{"stage_id": "unit", "total": 10}])


class TestAggregateWithErrorsField:
    def test_errors_are_retained_in_stage_report(self):
        reports = [
            StageReport(
                stage_id="unit", total=10, passed=8, failed=2, skipped=0,
                errors=["test_a failed", "test_b crashed"],
            )
        ]
        result = aggregate(reports)
        assert len(result.stages["unit"].errors) == 2
        assert "test_a failed" in result.stages["unit"].errors
        assert "test_b crashed" in result.stages["unit"].errors

    def test_errors_is_empty_list_when_no_errors(self):
        result = aggregate(
            [StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0)]
        )
        assert result.stages["unit"].errors == []

    def test_errors_multiple_stages(self):
        reports = [
            StageReport(
                stage_id="unit", total=10, passed=7, failed=3, skipped=0,
                errors=["err1"],
            ),
            StageReport(
                stage_id="integration", total=5, passed=4, failed=1, skipped=0,
                errors=["err2"],
            ),
        ]
        result = aggregate(reports)
        assert result.stages["unit"].errors == ["err1"]
        assert result.stages["integration"].errors == ["err2"]


class TestAggregateWithTimeout:
    @pytest.mark.asyncio
    async def test_normal_completion_within_timeout(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0)
        ]
        result = await aggregate_with_timeout(reports, timeout_seconds=60.0)
        assert result.total_tests == 10
        assert result.total_passed == 10
        assert result.overall_status == "passed"

    @pytest.mark.asyncio
    async def test_timeout_triggered_with_zero_timeout(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0)
        ]
        with pytest.raises(TimeoutError):
            await aggregate_with_timeout(reports, timeout_seconds=0.0)

    @pytest.mark.asyncio
    async def test_timeout_triggered_with_extremely_small_timeout(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0)
        ]
        with pytest.raises(TimeoutError):
            await aggregate_with_timeout(reports, timeout_seconds=1e-9)

    @pytest.mark.asyncio
    async def test_default_timeout_parameter_is_60_seconds(self):
        reports = [
            StageReport(stage_id="unit", total=10, passed=10, failed=0, skipped=0)
        ]
        result = await aggregate_with_timeout(reports)
        assert result.total_tests == 10
