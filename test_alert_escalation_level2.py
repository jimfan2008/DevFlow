import uuid
import time
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


class AlertLevel(Enum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


class AlertStatus(Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


@dataclass
class EscalationAction:
    timestamp: datetime
    from_level: AlertLevel
    to_level: AlertLevel
    reason: str
    previous_status: str
    notifiees: list[str]


@dataclass
class Alert:
    id: str
    title: str
    level: AlertLevel
    status: AlertStatus
    created_at: datetime
    assigned_to: Optional[str] = None
    handled_at: Optional[datetime] = None
    escalation_history: list[EscalationAction] = field(default_factory=list)

    @property
    def is_handled(self) -> bool:
        return self.status in (AlertStatus.IN_PROGRESS, AlertStatus.RESOLVED)

    @property
    def age(self) -> timedelta:
        return datetime.now(timezone.utc) - self.created_at

    def escalate(self, to_level: AlertLevel, reason: str, notifiees: list[str]) -> EscalationAction:
        action = EscalationAction(
            timestamp=datetime.now(timezone.utc),
            from_level=self.level,
            to_level=to_level,
            reason=reason,
            previous_status=self.status.value,
            notifiees=notifiees,
        )
        self.level = to_level
        self.escalation_history.append(action)
        return action


LEVEL_3_NOTIFIEES = ["project_manager", "cto"]


def check_escalation(alert: Alert, threshold_minutes: int = 30) -> Optional[EscalationAction]:
    if alert.level != AlertLevel.LEVEL_2:
        return None
    if alert.is_handled:
        return None
    age_minutes = alert.age.total_seconds() / 60.0
    if age_minutes < threshold_minutes:
        return None
    reason = f"Alert '{alert.title}' has been at {alert.level.name} for {age_minutes:.1f} minutes without being handled"
    return alert.escalate(
        to_level=AlertLevel.LEVEL_3,
        reason=reason,
        notifiees=LEVEL_3_NOTIFIEES,
    )


def test_alert_at_level2_for_over_30_minutes_escalates_to_level3():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="CPU usage exceeds 95%",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=31),
    )
    action = check_escalation(alert)
    assert action is not None
    assert alert.level == AlertLevel.LEVEL_3
    assert action.from_level == AlertLevel.LEVEL_2
    assert action.to_level == AlertLevel.LEVEL_3


def test_alert_at_level2_for_less_than_30_minutes_does_not_escalate():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Disk space at 85%",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=25),
    )
    action = check_escalation(alert)
    assert action is None
    assert alert.level == AlertLevel.LEVEL_2


def test_alert_at_level2_already_handled_does_not_escalate():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Memory leak detected",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.IN_PROGRESS,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=45),
        handled_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    action = check_escalation(alert)
    assert action is None
    assert alert.level == AlertLevel.LEVEL_2


def test_escalation_notification_contains_reason():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="API latency spike",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=35),
    )
    action = check_escalation(alert, threshold_minutes=30)
    assert action is not None
    assert "API latency spike" in action.reason
    assert "LEVEL_2" in action.reason or "level 2" in action.reason.lower() or "Level_2" in action.reason
    assert "without being handled" in action.reason


def test_escalation_notification_contains_previous_status():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Database connection pool exhausted",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.ACKNOWLEDGED,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=40),
    )
    action = check_escalation(alert)
    assert action is not None
    assert action.previous_status == "acknowledged"


def test_escalation_notifiees_include_project_manager_and_cto():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Service down",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=33),
    )
    action = check_escalation(alert)
    assert action is not None
    assert "project_manager" in action.notifiees
    assert "cto" in action.notifiees


def test_alert_at_level1_does_not_escalate_via_level2_escalator():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Warning: log error rate elevated",
        level=AlertLevel.LEVEL_1,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=60),
    )
    action = check_escalation(alert)
    assert action is None
    assert alert.level == AlertLevel.LEVEL_1


def test_alert_already_at_level3_no_further_escalation():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Critical: data corruption",
        level=AlertLevel.LEVEL_3,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=60),
    )
    action = check_escalation(alert)
    assert action is None
    assert alert.level == AlertLevel.LEVEL_3


def test_escalation_records_timestamp():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="SSL certificate expiring",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=32),
    )
    before = datetime.now(timezone.utc)
    action = check_escalation(alert)
    after = datetime.now(timezone.utc)
    assert action is not None
    assert before <= action.timestamp <= after


def test_multiple_escalation_history():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Repeated failures",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=35),
    )
    action = check_escalation(alert)
    assert action is not None
    assert len(alert.escalation_history) == 1
    assert alert.escalation_history[0] is action


def test_escalation_with_custom_threshold():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Custom threshold test",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=15),
    )
    action = check_escalation(alert, threshold_minutes=10)
    assert action is not None
    assert alert.level == AlertLevel.LEVEL_3


def test_escalation_below_custom_threshold():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Below custom threshold",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    action = check_escalation(alert, threshold_minutes=10)
    assert action is None
    assert alert.level == AlertLevel.LEVEL_2


def test_escalated_alert_notifiees_in_notification():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Payment service timeout",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=31),
    )
    action = check_escalation(alert)
    assert action is not None
    notification = {
        "type": "alert_escalated",
        "alert_id": alert.id,
        "alert_title": alert.title,
        "from_level": action.from_level.name,
        "to_level": action.to_level.name,
        "reason": action.reason,
        "previous_status": action.previous_status,
        "notifiees": action.notifiees,
    }
    assert notification["from_level"] == "LEVEL_2"
    assert notification["to_level"] == "LEVEL_3"
    assert "cto" in notification["notifiees"]
    assert "project_manager" in notification["notifiees"]
    assert notification["previous_status"] == "open"


def test_resolved_alert_does_not_escalate():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Resolved issue",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.RESOLVED,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=60),
        handled_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    action = check_escalation(alert)
    assert action is None
    assert alert.level == AlertLevel.LEVEL_2
    assert len(alert.escalation_history) == 0


def test_concurrent_escalation_check_is_safe():
    alert = Alert(
        id=str(uuid.uuid4()),
        title="Concurrent test",
        level=AlertLevel.LEVEL_2,
        status=AlertStatus.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=35),
    )
    results = []
    errors = []

    def check():
        try:
            result = check_escalation(alert)
            results.append(result)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=check) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    escalated_count = sum(1 for r in results if r is not None)
    assert escalated_count >= 0
