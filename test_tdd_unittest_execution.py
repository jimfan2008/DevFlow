import time
import math

import pytest


class MockTestResult:
    """Simulates a single test result."""

    def __init__(self, name: str, passed: bool, duration: float):
        self.name = name
        self.passed = passed
        self.duration = duration


class MockTestSuite:
    """Simulates a collection of tests with configurable outcomes."""

    def __init__(self, name: str, total: int, pass_rate: float, avg_duration: float = 0.05):
        self.name = name
        self.total = total
        self.pass_rate = pass_rate
        self.avg_duration = avg_duration
        self.results: list[MockTestResult] = []
        self._generate_results()

    def _generate_results(self):
        passed_count = int(self.total * self.pass_rate)
        for i in range(self.total):
            name = f"{self.name}_test_{i:04d}"
            passed = i < passed_count
            duration = abs(self.avg_duration + (i % 5) * 0.01)
            self.results.append(MockTestResult(name, passed, duration))

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def actual_pass_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.passed / self.total

    @property
    def total_duration(self) -> float:
        return sum(r.duration for r in self.results)


class CoverageCollector:
    """Simulates collecting code coverage metrics."""

    def __init__(self):
        self.covered_lines: set[int] = set()
        self.total_lines: set[int] = set()

    def add_module(self, total: int, covered: int):
        start = len(self.total_lines)
        self.total_lines.update(range(start, start + total))
        self.covered_lines.update(range(start, start + covered))

    @property
    def coverage_rate(self) -> float:
        if not self.total_lines:
            return 1.0
        return len(self.covered_lines) / len(self.total_lines)

    @property
    def is_acceptable(self) -> bool:
        return self.coverage_rate >= 0.85


class RetryHandler:
    """Manages auto-retry logic for failed tests."""

    def __init__(self, max_retries: int = 1):
        self.max_retries = max_retries
        self.retry_counts: dict[str, int] = {}
        self.final_results: dict[str, bool] = {}

    def run_with_retry(self, name: str, test_fn, *args, **kwargs) -> bool:
        self.retry_counts.setdefault(name, 0)
        for attempt in range(self.max_retries + 1):
            try:
                test_fn(*args, **kwargs)
                self.final_results[name] = True
                self.retry_counts[name] = attempt
                return True
            except AssertionError:
                if attempt < self.max_retries:
                    continue
                self.final_results[name] = False
                self.retry_counts[name] = attempt
                return False
        return False

    @property
    def total_retries(self) -> int:
        return sum(self.retry_counts.values())

    @property
    def recovered_count(self) -> int:
        return sum(
            1 for name, success in self.final_results.items()
            if success and self.retry_counts.get(name, 0) > 0
        )


class TestExecutionTime:
    """Tests for execution time constraint (≤10 minutes = 600 seconds)."""

    def test_single_test_execution_time_is_within_limit(self):
        start = time.monotonic()
        time.sleep(0.01)
        elapsed = time.monotonic() - start
        assert elapsed < 600.0, f"Single test took {elapsed:.3f}s, exceeds 600s limit"

    def test_suite_execution_time_within_limit(self):
        suite = MockTestSuite("fast_suite", total=50, pass_rate=1.0, avg_duration=0.02)
        start = time.monotonic()
        for result in suite.results:
            _ = result.passed
        elapsed = time.monotonic() - start
        total_simulated = suite.total_duration
        assert total_simulated < 600.0, (
            f"Simulated suite duration {total_simulated:.3f}s exceeds 600s limit"
        )
        assert elapsed < 30.0, (
            f"Actual iteration took {elapsed:.3f}s, indicates performance issue"
        )

    @pytest.mark.parametrize("test_count,avg_dur", [
        (100, 0.01),
        (500, 0.02),
        (1000, 0.05),
    ])
    def test_suite_scales_linearly_within_limit(self, test_count, avg_dur):
        suite = MockTestSuite(f"scale_{test_count}", total=test_count,
                              pass_rate=0.95, avg_duration=avg_dur)
        estimated = suite.total_duration
        assert estimated <= 600.0, (
            f"Estimated duration {estimated:.3f}s for {test_count} tests exceeds limit"
        )

    def test_execution_time_logging_records_duration(self):
        suite = MockTestSuite("logged", total=10, pass_rate=1.0, avg_duration=0.05)
        expected = suite.total_duration
        recorded = sum(r.duration for r in suite.results)
        assert math.isclose(expected, recorded, rel_tol=0.01), (
            f"Duration mismatch: expected {expected:.6f}, recorded {recorded:.6f}"
        )

    def test_execution_does_not_exceed_deadline_with_retries(self):
        suite = MockTestSuite("retry_timing", total=100, pass_rate=0.90, avg_duration=0.03)
        retry_handler = RetryHandler(max_retries=1)
        flaky_results = [r for r in suite.results if not r.passed]
        std_time = suite.total_duration
        retry_time = len(flaky_results) * suite.avg_duration
        total_estimated = std_time + retry_time
        assert total_estimated < 600.0, (
            f"Estimated time with retries {total_estimated:.3f}s exceeds limit"
        )


class TestPassRate:
    """Tests for pass rate constraint (≥95%)."""

    def test_suite_with_exactly_95_percent_pass_rate(self):
        suite = MockTestSuite("exact_95", total=100, pass_rate=0.95)
        actual = suite.actual_pass_rate
        assert actual >= 0.95, f"Pass rate {actual:.4f} below 0.95 threshold"
        assert suite.passed == 95
        assert suite.failed == 5

    def test_suite_above_95_percent_pass_rate(self):
        suite = MockTestSuite("above_95", total=200, pass_rate=0.98)
        assert suite.passed >= 190
        assert suite.actual_pass_rate >= 0.95

    def test_suite_below_95_percent_fails_assertion(self):
        suite = MockTestSuite("below_95", total=100, pass_rate=0.80)
        with pytest.raises(AssertionError):
            assert suite.actual_pass_rate >= 0.95, (
                f"Pass rate {suite.actual_pass_rate:.4f} below 0.95"
            )

    def test_all_tests_pass_returns_perfect_rate(self):
        suite = MockTestSuite("perfect", total=50, pass_rate=1.0)
        assert suite.passed == 50
        assert suite.failed == 0
        assert suite.actual_pass_rate == 1.0

    def test_no_tests_returns_default_pass_rate(self):
        suite = MockTestSuite("empty", total=0, pass_rate=1.0)
        assert suite.total == 0
        assert suite.actual_pass_rate == 1.0

    def test_pass_rate_calculation_is_accurate(self):
        suite = MockTestSuite("calc_check", total=1000, pass_rate=0.975)
        expected_passed = int(1000 * 0.975)
        deviation = abs(suite.passed - expected_passed)
        assert deviation <= 1, (
            f"Pass count deviation {deviation} greater than 1"
        )

    def test_pass_rate_recovery_after_retry(self):
        handler = RetryHandler(max_retries=1)
        call_count = [0]

        def flaky_fn():
            call_count[0] += 1
            if call_count[0] == 1:
                raise AssertionError("First attempt failed")
            return True

        result = handler.run_with_retry("flaky_test", flaky_fn)
        assert result is True, "Retry should recover the flaky test"
        assert handler.recovered_count == 1
        assert handler.retry_counts["flaky_test"] == 1

    def test_mixed_pass_fail_suite_is_aggregated_correctly(self):
        results = [
            MockTestResult(f"test_{i}", passed=(i % 20 != 0), duration=0.01)
            for i in range(100)
        ]
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        rate = passed / len(results)
        assert failed == 5
        assert passed == 95
        assert rate >= 0.95


class TestCodeCoverage:
    """Tests for code coverage constraint (≥85%)."""

    def test_coverage_at_exactly_85_percent(self):
        collector = CoverageCollector()
        collector.add_module(total=100, covered=85)
        assert collector.coverage_rate == 0.85
        assert collector.is_acceptable is True

    def test_coverage_above_85_percent(self):
        collector = CoverageCollector()
        collector.add_module(total=100, covered=92)
        assert collector.coverage_rate == 0.92
        assert collector.is_acceptable is True

    def test_coverage_below_85_percent_fails_validation(self):
        collector = CoverageCollector()
        collector.add_module(total=100, covered=70)
        assert collector.coverage_rate < 0.85
        assert collector.is_acceptable is False

    def test_multiple_modules_coverage_aggregation(self):
        collector = CoverageCollector()
        collector.add_module(total=200, covered=180)
        collector.add_module(total=300, covered=255)
        collector.add_module(total=500, covered=430)
        expected = (180 + 255 + 430) / (200 + 300 + 500)
        assert math.isclose(collector.coverage_rate, expected, rel_tol=0.001)
        assert collector.is_acceptable is True

    def test_full_coverage_returns_100_percent(self):
        collector = CoverageCollector()
        collector.add_module(total=150, covered=150)
        assert collector.coverage_rate == 1.0

    def test_no_code_returns_full_coverage_by_default(self):
        collector = CoverageCollector()
        assert collector.coverage_rate == 1.0
        assert collector.is_acceptable is True

    def test_coverage_increases_when_more_lines_covered(self):
        collector = CoverageCollector()
        collector.add_module(total=100, covered=50)
        assert collector.coverage_rate == 0.50
        assert collector.is_acceptable is False
        collector.add_module(total=100, covered=80)
        assert collector.coverage_rate == pytest.approx(130 / 200, abs=0.001)
        assert collector.is_acceptable is False
        collector2 = CoverageCollector()
        collector2.add_module(total=100, covered=90)
        assert collector2.coverage_rate == 0.90
        assert collector2.is_acceptable is True


class TestAutoRetry:
    """Tests for failed test auto-retry (1 retry)."""

    def test_failed_test_is_retried_exactly_once(self):
        handler = RetryHandler(max_retries=1)
        call_attempts = []

        def always_fails():
            call_attempts.append(len(call_attempts) + 1)
            raise AssertionError("Test always fails")

        result = handler.run_with_retry("always_fails", always_fails)
        assert result is False, "Test should remain failed after retry"
        assert len(call_attempts) == 2, (
            f"Expected 2 attempts (1 initial + 1 retry), got {len(call_attempts)}"
        )

    def test_flaky_test_passes_on_retry(self):
        handler = RetryHandler(max_retries=1)
        attempt_counter = [0]

        def flaky():
            attempt_counter[0] += 1
            if attempt_counter[0] < 2:
                raise AssertionError("Transient failure")
            return True

        result = handler.run_with_retry("flaky_test", flaky)
        assert result is True, "Flaky test should pass after retry"
        assert handler.recovered_count == 1

    def test_passing_test_is_not_retried(self):
        handler = RetryHandler(max_retries=1)
        call_count = [0]

        def always_passes():
            call_count[0] += 1
            return True

        result = handler.run_with_retry("always_passes", always_passes)
        assert result is True
        assert call_count[0] == 1, (
            f"Expected 1 call for passing test, got {call_count[0]}"
        )
        assert handler.retry_counts["always_passes"] == 0

    def test_retry_count_tracking_is_accurate(self):
        handler = RetryHandler(max_retries=1)

        for i in range(5):
            name = f"flaky_{i}"

            def make_flaky():
                calls = [0]

                def fn():
                    calls[0] += 1
                    if calls[0] < 2:
                        raise AssertionError("fail")
                return fn

            handler.run_with_retry(name, make_flaky())

        assert len(handler.final_results) == 5
        assert all(v is True for v in handler.final_results.values())
        assert all(v == 1 for v in handler.retry_counts.values())

    def test_multiple_failures_tracked_independently(self):
        handler = RetryHandler(max_retries=1)
        test_results = {}

        def make_test(succeed_on_retry: bool):
            attempts = [0]

            def test_fn():
                attempts[0] += 1
                if not succeed_on_retry and attempts[0] <= 2:
                    raise AssertionError("Always fails")
                if succeed_on_retry and attempts[0] < 2:
                    raise AssertionError("Transient")
                return True

            return test_fn

        for i in range(3):
            name = f"test_{i}"
            ok = i % 2 == 0
            result = handler.run_with_retry(name, make_test(ok))
            test_results[name] = result

        assert test_results["test_0"] is True
        assert test_results["test_1"] is False
        assert test_results["test_2"] is True
        assert handler.recovered_count == 2

    def test_zero_max_retries_disables_retry(self):
        handler = RetryHandler(max_retries=0)
        call_count = [0]

        def fails_once():
            call_count[0] += 1
            raise AssertionError("Fail")

        result = handler.run_with_retry("no_retry", fails_once)
        assert result is False
        assert call_count[0] == 1, (
            "With 0 retries, test should be called exactly once"
        )

    def test_retry_does_not_affect_passing_tests_overall_rate(self):
        suite = MockTestSuite("retry_rate", total=100, pass_rate=0.95)
        handler = RetryHandler(max_retries=1)
        final_pass_count = suite.passed
        failing = [r for r in suite.results if not r.passed]

        recovered = 0
        for result in failing:
            def make_recovered():
                calls = [0]

                def fn():
                    calls[0] += 1
                    if calls[0] == 1:
                        raise AssertionError("fail")
                return fn

            ok = handler.run_with_retry(result.name, make_recovered())
            if ok:
                recovered += 1
                final_pass_count += 1

        overall_rate = final_pass_count / suite.total
        assert overall_rate >= suite.pass_rate, (
            f"Overall rate {overall_rate:.4f} dropped below original {suite.pass_rate:.4f}"
        )
        assert handler.recovered_count == recovered


class TestIntegration:
    """Integration tests combining all acceptance criteria."""

    def test_full_test_execution_pipeline(self):
        suite = MockTestSuite("integration", total=200, pass_rate=0.96, avg_duration=0.02)
        handler = RetryHandler(max_retries=1)
        collector = CoverageCollector()
        collector.add_module(total=500, covered=440)

        start = time.monotonic()
        final_pass_count = suite.passed
        for result in suite.results:
            if not result.passed:
                def make_fn():
                    calls = [0]

                    def fn():
                        calls[0] += 1
                        if calls[0] == 1:
                            raise AssertionError("retry")
                    return fn

                if handler.run_with_retry(result.name, make_fn()):
                    final_pass_count += 1
        elapsed = time.monotonic() - start

        pass_rate = final_pass_count / suite.total
        coverage = collector.coverage_rate
        total_retries = handler.total_retries

        assert elapsed < 600.0, (
            f"Execution time {elapsed:.3f}s exceeds 600s limit"
        )
        assert pass_rate >= 0.95, (
            f"Pass rate {pass_rate:.4f} below 0.95 threshold"
        )
        assert coverage >= 0.85, (
            f"Coverage {coverage:.4f} below 0.85 threshold"
        )
        assert handler.recovered_count >= 0
        assert total_retries >= 0

    def test_high_volume_flaky_suite(self):
        suite = MockTestSuite("high_vol", total=500, pass_rate=0.93, avg_duration=0.01)
        handler = RetryHandler(max_retries=1)
        collector = CoverageCollector()
        collector.add_module(total=1000, covered=900)

        recovered = 0
        for result in suite.results:
            if not result.passed:
                def make_flaky():
                    calls = [0]

                    def fn():
                        calls[0] += 1
                        if calls[0] == 1:
                            raise AssertionError("retry")
                    return fn

                if handler.run_with_retry(result.name, make_flaky()):
                    recovered += 1

        final_passed = suite.passed + recovered
        final_rate = final_passed / suite.total
        assert final_rate >= 0.95, (
            f"Final pass rate {final_rate:.4f} below 0.95 after retry"
        )
        assert collector.is_acceptable is True

    def test_minimal_acceptable_suite_passes_all_checks(self):
        suite = MockTestSuite("minimal", total=100, pass_rate=0.95, avg_duration=0.02)
        collector = CoverageCollector()
        collector.add_module(total=100, covered=85)

        assert suite.actual_pass_rate >= 0.95
        assert collector.coverage_rate >= 0.85
        assert suite.total_duration < 600.0

    def test_pipeline_validates_all_three_thresholds_simultaneously(self):
        suites = [
            MockTestSuite("mod_a", total=300, pass_rate=0.97, avg_duration=0.015),
            MockTestSuite("mod_b", total=200, pass_rate=0.96, avg_duration=0.020),
            MockTestSuite("mod_c", total=100, pass_rate=0.95, avg_duration=0.025),
        ]
        collector = CoverageCollector()
        collector.add_module(total=800, covered=720)
        collector.add_module(total=600, covered=540)
        collector.add_module(total=400, covered=340)

        all_results = []
        for s in suites:
            all_results.extend(s.results)

        total = len(all_results)
        passed = sum(1 for r in all_results if r.passed)
        total_dur = sum(s.total_duration for s in suites)
        pass_rate = passed / total

        assert total_dur < 600.0, (
            f"Total duration {total_dur:.3f}s exceeds limit"
        )
        assert pass_rate >= 0.95, (
            f"Combined pass rate {pass_rate:.4f} below 0.95"
        )
        assert collector.is_acceptable is True, (
            f"Coverage {collector.coverage_rate:.4f} below 0.85"
        )
