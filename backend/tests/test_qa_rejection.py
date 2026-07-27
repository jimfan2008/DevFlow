import pytest
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from app.services.qa_gate_service import QAGateService


class QATaskStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    REJECTED = "rejected"
    FIXING = "fixing"
    RESUBMITTED = "resubmitted"
    ESCALATED = "escalated"


@dataclass
class QATask:
    task_id: str
    project_id: str
    step_id: int
    status: QATaskStatus = QATaskStatus.PENDING
    rejected_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    escalated_at: Optional[datetime] = None
    escalation_notified_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    fix_deadline_hours: int = 24


def reject_task(task: QATask, now: Optional[datetime] = None) -> QATask:
    """Reject a task and set its fix deadline."""
    if now is None:
        now = datetime.now(timezone.utc)
    task.status = QATaskStatus.REJECTED
    task.rejected_at = now
    task.deadline = now + timedelta(hours=task.fix_deadline_hours)
    task.retry_count = 0
    return task


def resubmit_task(task: QATask, now: Optional[datetime] = None) -> QATask:
    """Resubmit a rejected task for re-review."""
    if now is None:
        now = datetime.now(timezone.utc)
    if task.status != QATaskStatus.REJECTED and task.status != QATaskStatus.FIXING:
        raise ValueError(f"Cannot resubmit task in status: {task.status}")
    if task.deadline and now > task.deadline:
        raise ValueError("Task deadline has passed, cannot resubmit")
    task.status = QATaskStatus.RESUBMITTED
    task.retry_count += 1
    return task


def check_timeout(task: QATask, now: Optional[datetime] = None, on_escalate: Optional[Callable[[QATask], None]] = None) -> bool:
    """Check if a rejected task has exceeded its fix deadline.
    
    Returns True if escalation was triggered (first time), False otherwise.
    Idempotent: subsequent calls after escalation do not overwrite escalated_at.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if task.status != QATaskStatus.REJECTED and task.status != QATaskStatus.FIXING:
        return False
    if task.deadline is None:
        return False
    if now <= task.deadline:
        return False
    if task.escalated_at is not None:
        return False
    task.status = QATaskStatus.ESCALATED
    task.escalated_at = now
    if on_escalate:
        on_escalate(task)
    return True


def return_to_agent(task: QATask, now: Optional[datetime] = None) -> QATask:
    """Return a rejected task back to the agent for fixing."""
    if now is None:
        now = datetime.now(timezone.utc)
    if task.status == QATaskStatus.REJECTED:
        task.status = QATaskStatus.FIXING
    return task


def escalate_and_notify(task: QATask, now: Optional[datetime] = None) -> None:
    """Escalate callback that records notification time."""
    if now is None:
        now = datetime.now(timezone.utc)
    task.escalation_notified_at = now


class TestQATaskRejection:

    def test_reject_sets_deadline_24h(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-001", project_id="p-1", step_id=3)
        reject_task(task, now)
        assert task.status == QATaskStatus.REJECTED
        assert task.deadline == now + timedelta(hours=24)

    def test_reject_records_rejected_at(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-002", project_id="p-1", step_id=3)
        reject_task(task, now)
        assert task.rejected_at == now

    def test_return_to_agent_changes_status_to_fixing(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-003", project_id="p-1", step_id=3)
        reject_task(task, now)
        return_to_agent(task)
        assert task.status == QATaskStatus.FIXING

    def test_resubmit_within_deadline_succeeds(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-004", project_id="p-1", step_id=3)
        reject_task(task, now)
        return_to_agent(task)
        resubmit_time = now + timedelta(hours=12)
        resubmit_task(task, resubmit_time)
        assert task.status == QATaskStatus.RESUBMITTED
        assert task.retry_count == 1

    def test_resubmit_after_deadline_raises(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-005", project_id="p-1", step_id=3)
        reject_task(task, now)
        return_to_agent(task)
        past_deadline = now + timedelta(hours=25)
        with pytest.raises(ValueError, match="deadline has passed"):
            resubmit_task(task, past_deadline)

    def test_check_timeout_before_deadline_returns_false(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-006", project_id="p-1", step_id=3)
        reject_task(task, now)
        check_at = now + timedelta(hours=23)
        result = check_timeout(task, check_at)
        assert result is False
        assert task.status == QATaskStatus.REJECTED

    def test_check_timeout_after_deadline_escalates(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-007", project_id="p-1", step_id=3)
        reject_task(task, now)
        check_at = now + timedelta(hours=24, minutes=1)
        result = check_timeout(task, check_at)
        assert result is True
        assert task.status == QATaskStatus.ESCALATED
        assert task.escalated_at == check_at

    def test_check_timeout_invokes_escalation_callback(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-008", project_id="p-1", step_id=3)
        reject_task(task, now)
        check_at = now + timedelta(hours=25)

        callback_called = False
        captured_task = None

        def _callback(t):
            nonlocal callback_called, captured_task
            callback_called = True
            captured_task = t

        result = check_timeout(task, check_at, on_escalate=_callback)
        assert result is True
        assert callback_called is True
        assert captured_task is task

    def test_check_timeout_idempotent_same_time(self):
        """Same-time repeated call does not double-escalate."""
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-009", project_id="p-1", step_id=3)
        reject_task(task, now)
        check_at = now + timedelta(hours=25)

        first = check_timeout(task, check_at)
        second = check_timeout(task, check_at)
        assert first is True
        assert second is False
        assert task.escalated_at == check_at

    def test_check_timeout_idempotent_does_not_re_set_escalated_at(self):
        """T2 > T1: escalated_at set at T1 must not be overwritten by later check."""
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-010", project_id="p-1", step_id=3)
        reject_task(task, now)

        t1 = now + timedelta(hours=25)
        t2 = t1 + timedelta(minutes=30)

        first_result = check_timeout(task, t1)
        assert first_result is True
        assert task.escalated_at == t1

        second_result = check_timeout(task, t2)
        assert second_result is False
        assert task.escalated_at == t1, f"escalated_at was overwritten from {t1} to {task.escalated_at}"

    def test_escalation_notification_within_one_hour(self):
        """Escalation callback records notification; verify response time ≤1h."""
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-011", project_id="p-1", step_id=3)
        reject_task(task, now)
        check_at = now + timedelta(hours=25)

        check_timeout(task, check_at, on_escalate=escalate_and_notify)
        assert task.escalation_notified_at is not None
        response_time = task.escalation_notified_at - task.escalated_at
        assert response_time <= timedelta(hours=1)

    def test_reject_then_return_to_agent_sets_fixing(self):
        """Rejected output is returned to the agent for re-execution."""
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-012", project_id="p-1", step_id=3)
        reject_task(task, now)
        assert task.status == QATaskStatus.REJECTED
        return_to_agent(task)
        assert task.status == QATaskStatus.FIXING

    def test_multiple_rejections_increment_retries(self):
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-013", project_id="p-1", step_id=3)
        reject_task(task, now)
        return_to_agent(task)
        resubmit_time_1 = now + timedelta(hours=2)
        resubmit_task(task, resubmit_time_1)
        assert task.retry_count == 1

        reject_task(task, resubmit_time_1 + timedelta(minutes=5))
        return_to_agent(task)
        resubmit_time_2 = now + timedelta(hours=6)
        resubmit_task(task, resubmit_time_2)
        assert task.retry_count == 2

    def test_check_timeout_not_applicable_for_resubmitted(self):
        """Tasks in RESUBMITTED status should not trigger timeout."""
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        task = QATask(task_id="t-014", project_id="p-1", step_id=3)
        reject_task(task, now)
        return_to_agent(task)
        resubmit_task(task, now + timedelta(hours=1))
        assert task.status == QATaskStatus.RESUBMITTED
        result = check_timeout(task, now + timedelta(hours=48))
        assert result is False

    def test_check_timeout_with_no_deadline_returns_false(self):
        task = QATask(task_id="t-015", project_id="p-1", step_id=3, status=QATaskStatus.REJECTED)
        result = check_timeout(task, datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc))
        assert result is False
