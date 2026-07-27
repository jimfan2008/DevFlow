import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock


class Workflow:
    """Workflow under test: tracks iteration count and review status."""

    ITERATION_LIMIT = 5

    def __init__(self):
        self.iteration_count = 0
        self.status = "active"
        self._last_iteration_time = None

    def process_iteration(self):
        """Process one iteration. Bumps count, triggers review if over limit."""
        self.iteration_count += 1
        self._last_iteration_time = datetime.now()
        if self.iteration_count > self.ITERATION_LIMIT:
            self.status = "review_required"
        return self.iteration_count

    def should_trigger_review(self):
        """Whether the workflow has exceeded the iteration limit."""
        return self.iteration_count > self.ITERATION_LIMIT

    def get_time_since_last_iteration(self, reference_time):
        """Calculate time elapsed since the last iteration."""
        if self._last_iteration_time is None:
            return timedelta(0)
        return reference_time - self._last_iteration_time


def _validate_review_response_time(response_time):
    """Validate that review response time is within 24 hours."""
    return response_time <= timedelta(hours=24)


@pytest.fixture
def haimei_agent():
    """Fixture providing a mock Haimei agent with fixed timestamps."""
    agent = MagicMock()
    agent.fixed_time = datetime(2023, 1, 1, 12, 0, 0)
    return agent


@pytest.fixture
def workflow():
    """Fixture providing a fresh Workflow instance."""
    return Workflow()


class TestMaxIterationLimit:
    """Tests for the maximum iteration limit feature."""

    def test_exceeding_limit_triggers_review(self, workflow, haimei_agent):
        """Process 6 iterations — exceeds 5 → triggers review."""
        for _ in range(6):
            workflow.process_iteration()

        assert workflow.should_trigger_review() is True
        assert workflow.status == "review_required"

    def test_within_limit_no_review(self, workflow):
        """Process exactly 5 iterations — no review triggered."""
        for _ in range(5):
            workflow.process_iteration()

        assert workflow.should_trigger_review() is False
        assert workflow.status == "active"

    def test_full_scenario_workflow(self, workflow):
        """Boundary: 5 iterations OK → 6th iteration triggers review."""
        for _ in range(5):
            workflow.process_iteration()

        assert workflow.should_trigger_review() is False
        assert workflow.status == "active"

        workflow.process_iteration()

        assert workflow.should_trigger_review() is True
        assert workflow.status == "review_required"

    def test_review_response_time_within_24_hours(self):
        """Business scenario: actual time difference must be ≤ 24h."""
        last_iteration = datetime(2023, 1, 1, 12, 0, 0)

        # 22 hours later — within limit
        review_time_ok = datetime(2023, 1, 2, 10, 0, 0)
        time_diff_ok = review_time_ok - last_iteration
        assert time_diff_ok == timedelta(hours=22)
        assert _validate_review_response_time(time_diff_ok) is True

        # Exactly 24 hours — boundary, still acceptable
        review_time_boundary = datetime(2023, 1, 2, 12, 0, 0)
        time_diff_boundary = review_time_boundary - last_iteration
        assert time_diff_boundary == timedelta(hours=24)
        assert _validate_review_response_time(time_diff_boundary) is True

        # 24 hours + 1 second — exceeds limit
        review_time_exceed = datetime(2023, 1, 2, 12, 0, 1)
        time_diff_exceed = review_time_exceed - last_iteration
        assert time_diff_exceed > timedelta(hours=24)
        assert _validate_review_response_time(time_diff_exceed) is False
