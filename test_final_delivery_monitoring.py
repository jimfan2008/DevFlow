import time
import pytest
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional


class DeliverableStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWING = "reviewing"


@dataclass
class Deliverable:
    """交付物"""
    name: str
    description: str
    status: DeliverableStatus = DeliverableStatus.PENDING
    completed_at: Optional[datetime] = None


@dataclass
class DeliveryRecord:
    """项目交付记录"""
    project_id: str
    project_name: str
    deliverables: List[Deliverable] = field(default_factory=list)
    delivery_start_time: Optional[datetime] = None
    delivery_end_time: Optional[datetime] = None
    delivery_status: str = "pending"

    def add_deliverable(self, deliverable: Deliverable):
        self.deliverables.append(deliverable)

    def complete_deliverable(self, index: int):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index].status = DeliverableStatus.COMPLETED
            self.deliverables[index].completed_at = datetime.now()

    def start_delivery(self):
        self.delivery_start_time = datetime.now()
        self.delivery_status = "in_progress"

    def end_delivery(self):
        self.delivery_end_time = datetime.now()
        self.delivery_status = "completed"

    def get_completion_duration_hours(self) -> Optional[float]:
        if self.delivery_start_time and self.delivery_end_time:
            delta = self.delivery_end_time - self.delivery_start_time
            return delta.total_seconds() / 3600
        return None

    def get_deliverable_completeness(self) -> float:
        if not self.deliverables:
            return 0.0
        completed = sum(
            1 for d in self.deliverables
            if d.status == DeliverableStatus.COMPLETED
        )
        return (completed / len(self.deliverables)) * 100.0

    def is_complete(self) -> bool:
        return self.get_deliverable_completeness() == 100.0

    def is_within_time_limit(self, max_hours: float = 24.0) -> bool:
        duration = self.get_completion_duration_hours()
        if duration is None:
            return False
        return duration <= max_hours


class DeliveryVerifier:
    """交付验证器"""

    def __init__(self, max_hours: float = 24.0):
        self.max_hours = max_hours

    def verify(self, record: DeliveryRecord) -> dict:
        completeness = record.get_deliverable_completeness()
        duration = record.get_completion_duration_hours()
        within_time = record.is_within_time_limit(self.max_hours)
        is_complete = record.is_complete()

        passed = within_time and is_complete

        return {
            "passed": passed,
            "deliverable_completeness": completeness,
            "completion_duration_hours": duration,
            "within_time_limit": within_time,
            "all_deliverables_complete": is_complete,
            "max_hours": self.max_hours,
        }


@pytest.fixture
def verifier():
    return DeliveryVerifier(max_hours=24.0)


@pytest.fixture
def delivery_record():
    now = datetime.now()
    record = DeliveryRecord(
        project_id="proj-001",
        project_name="DevFlow平台交付",
        delivery_start_time=now - timedelta(hours=2),
    )
    return record


class TestDeliveryTimeLimit:
    """验证交付完成时间不超过24小时"""

    def test_delivery_within_24_hours(self, delivery_record):
        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=12)
        )
        assert delivery_record.is_within_time_limit(24.0) is True

    def test_delivery_exactly_24_hours(self, delivery_record):
        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=24)
        )
        assert delivery_record.is_within_time_limit(24.0) is True

    def test_delivery_exceeds_24_hours(self, delivery_record):
        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=25)
        )
        assert delivery_record.is_within_time_limit(24.0) is False

    def test_delivery_not_completed_no_end_time(self, delivery_record):
        delivery_record.delivery_end_time = None
        assert delivery_record.is_within_time_limit(24.0) is False

    def test_completion_duration_calculation(self, delivery_record):
        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=6, minutes=30)
        )
        duration = delivery_record.get_completion_duration_hours()
        assert duration == 6.5


class TestDeliverableCompleteness:
    """验证交付物完整度达到100%"""

    def test_all_deliverables_complete_is_100_percent(self, delivery_record):
        d1 = Deliverable("需求文档", "SRS v2.0", DeliverableStatus.COMPLETED)
        d2 = Deliverable("设计文档", "Architecture Design", DeliverableStatus.COMPLETED)
        d3 = Deliverable("源代码", "Source Code", DeliverableStatus.COMPLETED)
        d4 = Deliverable("测试报告", "QA Report", DeliverableStatus.COMPLETED)
        for d in [d1, d2, d3, d4]:
            delivery_record.add_deliverable(d)

        assert delivery_record.get_deliverable_completeness() == 100.0
        assert delivery_record.is_complete() is True

    def test_partial_deliverables_not_complete(self, delivery_record):
        d1 = Deliverable("需求文档", "SRS v2.0", DeliverableStatus.COMPLETED)
        d2 = Deliverable("设计文档", "Architecture Design", DeliverableStatus.COMPLETED)
        d3 = Deliverable("源代码", "Source Code", DeliverableStatus.IN_PROGRESS)
        d4 = Deliverable("测试报告", "QA Report", DeliverableStatus.PENDING)
        for d in [d1, d2, d3, d4]:
            delivery_record.add_deliverable(d)

        assert delivery_record.get_deliverable_completeness() == 50.0
        assert delivery_record.is_complete() is False

    def test_no_deliverables_returns_zero(self, delivery_record):
        assert delivery_record.get_deliverable_completeness() == 0.0
        assert delivery_record.is_complete() is False

    def test_single_deliverable_complete(self, delivery_record):
        d1 = Deliverable("需求文档", "SRS v2.0", DeliverableStatus.COMPLETED)
        delivery_record.add_deliverable(d1)
        assert delivery_record.get_deliverable_completeness() == 100.0

    def test_single_deliverable_incomplete(self, delivery_record):
        d1 = Deliverable("需求文档", "SRS v2.0", DeliverableStatus.PENDING)
        delivery_record.add_deliverable(d1)
        assert delivery_record.get_deliverable_completeness() == 0.0

    def test_deliverable_status_transitions(self, delivery_record):
        d1 = Deliverable("需求文档", "SRS v2.0")
        delivery_record.add_deliverable(d1)
        assert d1.status == DeliverableStatus.PENDING
        assert delivery_record.get_deliverable_completeness() == 0.0

        delivery_record.complete_deliverable(0)
        assert d1.status == DeliverableStatus.COMPLETED
        assert d1.completed_at is not None
        assert delivery_record.get_deliverable_completeness() == 100.0


class TestDeliveryVerification:
    """验证最终交付检查器"""

    def test_full_pass_all_deliverables_and_within_time(self, delivery_record, verifier):
        for name, desc in [
            ("需求文档", "SRS"),
            ("设计文档", "Design"),
            ("源代码", "Code"),
            ("测试报告", "QA"),
            ("部署文档", "Deploy Guide"),
        ]:
            d = Deliverable(name, desc, DeliverableStatus.COMPLETED)
            delivery_record.add_deliverable(d)

        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=18)
        )

        result = verifier.verify(delivery_record)
        assert result["passed"] is True
        assert result["deliverable_completeness"] == 100.0
        assert result["completion_duration_hours"] == 18.0
        assert result["within_time_limit"] is True
        assert result["all_deliverables_complete"] is True

    def test_fail_due_to_incomplete_deliverables(self, delivery_record, verifier):
        d1 = Deliverable("需求文档", "SRS", DeliverableStatus.COMPLETED)
        d2 = Deliverable("设计文档", "Design", DeliverableStatus.PENDING)
        delivery_record.add_deliverable(d1)
        delivery_record.add_deliverable(d2)
        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=10)
        )

        result = verifier.verify(delivery_record)
        assert result["passed"] is False
        assert result["deliverable_completeness"] == 50.0
        assert result["within_time_limit"] is True
        assert result["all_deliverables_complete"] is False

    def test_fail_due_to_exceeding_time(self, delivery_record, verifier):
        d1 = Deliverable("需求文档", "SRS", DeliverableStatus.COMPLETED)
        d2 = Deliverable("设计文档", "Design", DeliverableStatus.COMPLETED)
        delivery_record.add_deliverable(d1)
        delivery_record.add_deliverable(d2)
        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=30)
        )

        result = verifier.verify(delivery_record)
        assert result["passed"] is False
        assert result["deliverable_completeness"] == 100.0
        assert result["within_time_limit"] is False
        assert result["all_deliverables_complete"] is True

    def test_fail_both_conditions(self, delivery_record, verifier):
        d1 = Deliverable("需求文档", "SRS", DeliverableStatus.COMPLETED)
        d2 = Deliverable("设计文档", "Design", DeliverableStatus.IN_PROGRESS)
        delivery_record.add_deliverable(d1)
        delivery_record.add_deliverable(d2)
        delivery_record.delivery_end_time = (
            delivery_record.delivery_start_time + timedelta(hours=48)
        )

        result = verifier.verify(delivery_record)
        assert result["passed"] is False
        assert result["deliverable_completeness"] == 50.0
        assert result["completion_duration_hours"] == 48.0
        assert result["within_time_limit"] is False
        assert result["all_deliverables_complete"] is False

    def test_custom_time_limit(self):
        verifier_12h = DeliveryVerifier(max_hours=12.0)
        record = DeliveryRecord(
            project_id="proj-002",
            project_name="快速交付项目",
            delivery_start_time=datetime.now() - timedelta(hours=10),
            delivery_end_time=datetime.now(),
        )
        d = Deliverable("交付物", "描述", DeliverableStatus.COMPLETED)
        record.add_deliverable(d)

        result = verifier_12h.verify(record)
        assert result["passed"] is True
        assert result["max_hours"] == 12.0

    def test_edge_case_just_under_24h(self, verifier):
        start = datetime(2026, 7, 19, 10, 0, 0)
        end = datetime(2026, 7, 20, 9, 59, 59)
        record = DeliveryRecord(
            project_id="proj-003",
            project_name="边缘测试项目",
            delivery_start_time=start,
            delivery_end_time=end,
        )
        d = Deliverable("交付物", "描述", DeliverableStatus.COMPLETED)
        record.add_deliverable(d)

        result = verifier.verify(record)
        duration = result["completion_duration_hours"]
        assert duration < 24.0
        assert result["within_time_limit"] is True
        assert result["passed"] is True
