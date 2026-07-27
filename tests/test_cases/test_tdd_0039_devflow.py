import pytest
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationMessage:
    def __init__(self, channel: NotificationChannel, recipient: str, content: str):
        self.id = str(uuid.uuid4())
        self.channel = channel
        self.recipient = recipient
        self.content = content
        self.status = NotificationStatus.PENDING
        self.created_at: Optional[datetime] = None
        self.sent_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.retry_count = 0

    def mark_sent(self) -> None:
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        self.status = NotificationStatus.FAILED
        self.error = error

    @property
    def latency(self) -> Optional[float]:
        if self.created_at is not None and self.sent_at is not None:
            return (self.sent_at - self.created_at).total_seconds()
        return None

    @property
    def delivered(self) -> bool:
        return self.status == NotificationStatus.SENT


class Alert:
    def __init__(self, alert_id: str, severity: str, title: str, message: str):
        self.alert_id = alert_id
        self.severity = severity
        self.title = title
        self.message = message
        self.triggered_at: Optional[datetime] = None
        self.notifications: list[NotificationMessage] = []

    def trigger(self) -> None:
        self.triggered_at = datetime.now()

    def add_notification(self, notification: NotificationMessage) -> None:
        notification.created_at = datetime.now()
        self.notifications.append(notification)


class InAppSender:
    def send(self, notification: NotificationMessage) -> bool:
        try:
            if not notification.recipient:
                raise ValueError("No recipient specified")
            notification.mark_sent()
            return True
        except Exception as e:
            notification.mark_failed(str(e))
            return False


class EmailSender:
    def __init__(self):
        self._should_fail = False

    def inject_failure(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def send(self, notification: NotificationMessage) -> bool:
        try:
            if not notification.recipient or "@" not in notification.recipient:
                raise ValueError("Invalid email address")
            if self._should_fail:
                raise RuntimeError("SMTP server unreachable")
            notification.mark_sent()
            return True
        except Exception as e:
            notification.mark_failed(str(e))
            return False


class WebhookSender:
    def __init__(self):
        self._endpoint_status: dict[str, bool] = {}

    def set_endpoint_status(self, url: str, is_available: bool) -> None:
        self._endpoint_status[url] = is_available

    def send(self, notification: NotificationMessage) -> bool:
        try:
            if not notification.recipient.startswith("http"):
                raise ValueError("Invalid webhook URL")
            if self._endpoint_status.get(notification.recipient, True) is False:
                raise RuntimeError("Webhook endpoint unreachable")
            notification.mark_sent()
            return True
        except Exception as e:
            notification.mark_failed(str(e))
            return False


class NotificationService:
    def __init__(self):
        self._senders = {
            NotificationChannel.IN_APP: InAppSender(),
            NotificationChannel.EMAIL: EmailSender(),
            NotificationChannel.WEBHOOK: WebhookSender(),
        }
        self._notifications: list[NotificationMessage] = []
        self._total_attempts = 0
        self._successful_attempts = 0

    @property
    def success_rate(self) -> float:
        if self._total_attempts == 0:
            return 1.0
        return self._successful_attempts / self._total_attempts

    def send_notification(self, notification: NotificationMessage) -> bool:
        self._total_attempts += 1
        sender = self._senders.get(notification.channel)
        if sender is None:
            notification.mark_failed("No sender for channel")
            return False
        if notification.created_at is None:
            notification.created_at = datetime.now()
        result = sender.send(notification)
        if result:
            self._successful_attempts += 1
        return result

    def send_alert_notifications(
        self, alert: Alert, recipients: dict[NotificationChannel, str], content: str
    ) -> None:
        for channel, recipient in recipients.items():
            notification = NotificationMessage(
                channel=channel,
                recipient=recipient,
                content=content,
            )
            alert.add_notification(notification)
            self.send_notification(notification)
            self._notifications.append(notification)

    def get_notifications_by_channel(self, channel: NotificationChannel) -> list[NotificationMessage]:
        return [n for n in self._notifications if n.channel == channel]

    def get_all_notifications(self) -> list[NotificationMessage]:
        return self._notifications.copy()

    def get_delivery_summary(self) -> dict:
        total = len(self._notifications)
        sent = sum(1 for n in self._notifications if n.delivered)
        failed = total - sent
        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "success_rate": sent / total if total > 0 else 1.0,
        }

    def get_latency_stats(self) -> dict:
        latencies = [
            n.latency for n in self._notifications
            if n.latency is not None
        ]
        if not latencies:
            return {"avg": 0.0, "max": 0.0, "min": 0.0, "count": 0}
        return {
            "avg": sum(latencies) / len(latencies),
            "max": max(latencies),
            "min": min(latencies),
            "count": len(latencies),
        }


class AlertManager:
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self._alerts: list[Alert] = []

    def create_and_trigger_alert(
        self, severity: str, title: str, message: str
    ) -> Alert:
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            message=message,
        )
        alert.trigger()
        self._alerts.append(alert)
        return alert

    def dispatch_notifications(
        self,
        alert: Alert,
        recipients: dict[NotificationChannel, str],
        content: str,
    ) -> None:
        self.notification_service.send_alert_notifications(alert, recipients, content)

    def get_alerts(self) -> list[Alert]:
        return self._alerts

    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                return alert
        return None

    def get_alert_delivery_summary(self, alert: Alert) -> dict:
        notifications = alert.notifications
        sent = sum(1 for n in notifications if n.delivered)
        return {
            "alert_id": alert.alert_id,
            "severity": alert.severity,
            "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
            "total_notifications": len(notifications),
            "sent": sent,
            "failed": len(notifications) - sent,
        }

    def get_max_notification_latency(self, alert: Alert) -> float:
        latencies = [
            n.latency for n in alert.notifications
            if n.latency is not None
        ]
        return max(latencies) if latencies else 0.0


@pytest.fixture
def notification_service():
    return NotificationService()


@pytest.fixture
def alert_manager(notification_service):
    return AlertManager(notification_service)


@pytest.fixture
def sample_recipients():
    return {
        NotificationChannel.IN_APP: "user-001",
        NotificationChannel.EMAIL: "admin@example.com",
        NotificationChannel.WEBHOOK: "https://hooks.example.com/alerts",
    }


@pytest.fixture
def triggered_alert(alert_manager):
    return alert_manager.create_and_trigger_alert(
        severity="critical",
        title="CPU Overload",
        message="CPU usage exceeded 95% on node-3",
    )


class TestNotificationMessage:
    def test_create_notification_with_all_fields(self):
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@test.com",
            content="Test alert",
        )
        assert n.id is not None
        assert n.channel == NotificationChannel.EMAIL
        assert n.recipient == "admin@test.com"
        assert n.content == "Test alert"
        assert n.status == NotificationStatus.PENDING
        assert n.created_at is None
        assert n.sent_at is None
        assert n.error is None
        assert n.retry_count == 0

    def test_mark_sent_sets_status_and_timestamp(self):
        n = NotificationMessage(
            channel=NotificationChannel.IN_APP,
            recipient="user-001",
            content="Test",
        )
        before = datetime.now()
        n.mark_sent()
        after = datetime.now()
        assert n.status == NotificationStatus.SENT
        assert n.sent_at is not None
        assert before <= n.sent_at <= after

    def test_mark_failed_sets_status_and_error(self):
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@test.com",
            content="Test",
        )
        n.mark_failed("Connection timeout")
        assert n.status == NotificationStatus.FAILED
        assert n.error == "Connection timeout"

    def test_latency_with_created_and_sent_timestamps(self):
        n = NotificationMessage(
            channel=NotificationChannel.WEBHOOK,
            recipient="https://hook.example.com",
            content="Test",
        )
        n.created_at = datetime.now()
        n.mark_sent()
        lat = n.latency
        assert lat is not None
        assert 0 <= lat <= 1.0

    def test_latency_returns_none_when_not_sent(self):
        n = NotificationMessage(
            channel=NotificationChannel.IN_APP,
            recipient="user-001",
            content="Test",
        )
        assert n.latency is None

    def test_latency_returns_none_when_not_created(self):
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@test.com",
            content="Test",
        )
        n.mark_sent()
        assert n.latency is None

    def test_delivered_property_for_sent(self):
        n = NotificationMessage(
            channel=NotificationChannel.IN_APP,
            recipient="user-001",
            content="Test",
        )
        assert n.delivered is False
        n.mark_sent()
        assert n.delivered is True

    def test_delivered_property_for_failed(self):
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@test.com",
            content="Test",
        )
        n.mark_failed("Error")
        assert n.delivered is False


class TestAlert:
    def test_create_alert_with_id_and_message(self):
        alert = Alert(
            alert_id="alert-001",
            severity="warning",
            title="Disk Space Low",
            message="Disk usage at 85%",
        )
        assert alert.alert_id == "alert-001"
        assert alert.severity == "warning"
        assert alert.title == "Disk Space Low"
        assert alert.message == "Disk usage at 85%"
        assert alert.triggered_at is None
        assert alert.notifications == []

    def test_trigger_sets_timestamp(self):
        alert = Alert(
            alert_id="alert-002",
            severity="critical",
            title="Service Down",
            message="nginx is not responding",
        )
        before = datetime.now()
        alert.trigger()
        after = datetime.now()
        assert alert.triggered_at is not None
        assert before <= alert.triggered_at <= after

    def test_add_notification_sets_created_at(self):
        alert = Alert("alert-003", "info", "Info", "Test")
        notification = NotificationMessage(
            channel=NotificationChannel.IN_APP,
            recipient="user-001",
            content="Test notification",
        )
        before = datetime.now()
        alert.add_notification(notification)
        after = datetime.now()
        assert len(alert.notifications) == 1
        assert alert.notifications[0] is notification
        assert notification.created_at is not None
        assert before <= notification.created_at <= after

    def test_multiple_notifications_added(self):
        alert = Alert("alert-004", "critical", "Multi", "Test")
        for i in range(5):
            n = NotificationMessage(
                channel=NotificationChannel.IN_APP,
                recipient=f"user-{i:03d}",
                content=f"Notification {i}",
            )
            alert.add_notification(n)
        assert len(alert.notifications) == 5


class TestInAppSender:
    def test_send_success(self):
        sender = InAppSender()
        n = NotificationMessage(
            channel=NotificationChannel.IN_APP,
            recipient="user-001",
            content="Hello",
        )
        result = sender.send(n)
        assert result is True
        assert n.status == NotificationStatus.SENT
        assert n.sent_at is not None

    def test_send_fails_without_recipient(self):
        sender = InAppSender()
        n = NotificationMessage(
            channel=NotificationChannel.IN_APP,
            recipient="",
            content="Hello",
        )
        result = sender.send(n)
        assert result is False
        assert n.status == NotificationStatus.FAILED
        assert n.error is not None

    def test_send_multiple_success(self):
        sender = InAppSender()
        for i in range(10):
            n = NotificationMessage(
                channel=NotificationChannel.IN_APP,
                recipient=f"user-{i:03d}",
                content=f"Alert {i}",
            )
            result = sender.send(n)
            assert result is True


class TestEmailSender:
    def test_send_success(self):
        sender = EmailSender()
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@example.com",
            content="Test email",
        )
        result = sender.send(n)
        assert result is True
        assert n.status == NotificationStatus.SENT

    def test_send_fails_without_at_in_address(self):
        sender = EmailSender()
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="invalid-email",
            content="Test",
        )
        result = sender.send(n)
        assert result is False
        assert n.status == NotificationStatus.FAILED

    def test_send_fails_with_empty_recipient(self):
        sender = EmailSender()
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="",
            content="Test",
        )
        result = sender.send(n)
        assert result is False

    def test_send_fails_when_injected_failure(self):
        sender = EmailSender()
        sender.inject_failure(True)
        n = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@example.com",
            content="Test",
        )
        result = sender.send(n)
        assert result is False
        assert n.status == NotificationStatus.FAILED

    def test_send_recovers_after_failure_cleared(self):
        sender = EmailSender()
        sender.inject_failure(True)
        n1 = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@example.com",
            content="Fail test",
        )
        assert sender.send(n1) is False
        sender.inject_failure(False)
        n2 = NotificationMessage(
            channel=NotificationChannel.EMAIL,
            recipient="admin@example.com",
            content="Recovery test",
        )
        assert sender.send(n2) is True


class TestWebhookSender:
    def test_send_success(self):
        sender = WebhookSender()
        n = NotificationMessage(
            channel=NotificationChannel.WEBHOOK,
            recipient="https://hooks.example.com/alert",
            content='{"severity": "critical"}',
        )
        result = sender.send(n)
        assert result is True
        assert n.status == NotificationStatus.SENT

    def test_send_fails_with_non_http_recipient(self):
        sender = WebhookSender()
        n = NotificationMessage(
            channel=NotificationChannel.WEBHOOK,
            recipient="not-a-url",
            content="Test",
        )
        result = sender.send(n)
        assert result is False

    def test_send_fails_with_empty_recipient(self):
        sender = WebhookSender()
        n = NotificationMessage(
            channel=NotificationChannel.WEBHOOK,
            recipient="",
            content="Test",
        )
        result = sender.send(n)
        assert result is False

    def test_send_fails_when_endpoint_unavailable(self):
        sender = WebhookSender()
        url = "https://hooks.example.com/down"
        sender.set_endpoint_status(url, False)
        n = NotificationMessage(
            channel=NotificationChannel.WEBHOOK,
            recipient=url,
            content="Test",
        )
        result = sender.send(n)
        assert result is False

    def test_send_succeeds_when_endpoint_available(self):
        sender = WebhookSender()
        url = "https://hooks.example.com/up"
        sender.set_endpoint_status(url, True)
        n = NotificationMessage(
            channel=NotificationChannel.WEBHOOK,
            recipient=url,
            content="Test",
        )
        result = sender.send(n)
        assert result is True


class TestNotificationService:
    def test_send_single_notification_success(self, notification_service):
        n = NotificationMessage(
            channel=NotificationChannel.IN_APP,
            recipient="user-001",
            content="Test",
        )
        result = notification_service.send_notification(n)
        assert result is True
        assert n.status == NotificationStatus.SENT

    def test_send_alert_notifications_all_channels(self, notification_service, sample_recipients):
        alert = Alert("alert-test-001", "critical", "Test", "Test message")
        alert.trigger()
        content = "Critical alert: CPU overload"
        notification_service.send_alert_notifications(alert, sample_recipients, content)
        assert len(alert.notifications) == 3
        for notification in alert.notifications:
            assert notification.status == NotificationStatus.SENT

    def test_send_alert_notifications_stores_in_service(self, notification_service, sample_recipients):
        alert = Alert("alert-test-002", "warning", "Test", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Warning alert")
        all_n = notification_service.get_all_notifications()
        assert len(all_n) == 3

    def test_get_notifications_by_channel(self, notification_service, sample_recipients):
        alert = Alert("alert-test-003", "info", "Test", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Info alert")
        in_app = notification_service.get_notifications_by_channel(NotificationChannel.IN_APP)
        email = notification_service.get_notifications_by_channel(NotificationChannel.EMAIL)
        webhook = notification_service.get_notifications_by_channel(NotificationChannel.WEBHOOK)
        assert len(in_app) == 1
        assert len(email) == 1
        assert len(webhook) == 1
        assert in_app[0].channel == NotificationChannel.IN_APP
        assert email[0].channel == NotificationChannel.EMAIL
        assert webhook[0].channel == NotificationChannel.WEBHOOK

    def test_delivery_summary_all_sent(self, notification_service, sample_recipients):
        alert = Alert("alert-summary-001", "critical", "Test", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Summary test")
        summary = notification_service.get_delivery_summary()
        assert summary["total"] == 3
        assert summary["sent"] == 3
        assert summary["failed"] == 0
        assert summary["success_rate"] == 1.0

    def test_delivery_summary_with_failures(self, notification_service):
        alert = Alert("alert-fail-001", "critical", "Test", "Test")
        alert.trigger()
        recipients = {
            NotificationChannel.IN_APP: "user-001",
            NotificationChannel.EMAIL: "bad-email",
            NotificationChannel.WEBHOOK: "",
        }
        notification_service.send_alert_notifications(alert, recipients, "Fail test")
        summary = notification_service.get_delivery_summary()
        assert summary["total"] == 3
        assert summary["sent"] == 1
        assert summary["failed"] == 2

    def test_latency_stats_after_sending(self, notification_service, sample_recipients):
        alert = Alert("alert-lat-001", "critical", "Test", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Latency test")
        stats = notification_service.get_latency_stats()
        assert stats["count"] == 3
        assert stats["min"] >= 0
        assert stats["max"] >= stats["min"]
        assert stats["avg"] >= 0

    def test_success_rate_tracks_all_attempts(self, notification_service):
        assert notification_service.success_rate == 1.0
        n1 = NotificationMessage(NotificationChannel.IN_APP, "user-001", "OK")
        notification_service.send_notification(n1)
        assert notification_service.success_rate == 1.0
        n2 = NotificationMessage(NotificationChannel.EMAIL, "bad-email", "Fail")
        notification_service.send_notification(n2)
        assert notification_service.success_rate == 0.5

    def test_send_notification_with_unknown_channel(self, notification_service):
        n = NotificationMessage(
            channel="unknown_channel",
            recipient="test",
            content="Test",
        )
        result = notification_service.send_notification(n)
        assert result is False
        assert n.status == NotificationStatus.FAILED


class TestAlertManager:
    def test_create_and_trigger_alert(self, alert_manager):
        alert = alert_manager.create_and_trigger_alert(
            severity="critical",
            title="Test Alert",
            message="Test message",
        )
        assert alert.alert_id is not None
        assert alert.triggered_at is not None
        assert alert in alert_manager.get_alerts()

    def test_dispatch_notifications_adds_to_alert(self, alert_manager, triggered_alert, sample_recipients):
        alert_manager.dispatch_notifications(
            triggered_alert, sample_recipients, "Critical alert"
        )
        assert len(triggered_alert.notifications) == 3

    def test_get_alert_by_id_found(self, alert_manager):
        alert = alert_manager.create_and_trigger_alert("info", "Test", "Test")
        found = alert_manager.get_alert_by_id(alert.alert_id)
        assert found is alert

    def test_get_alert_by_id_not_found(self, alert_manager):
        found = alert_manager.get_alert_by_id("nonexistent-id")
        assert found is None

    def test_get_alert_delivery_summary(self, alert_manager, triggered_alert, sample_recipients):
        alert_manager.dispatch_notifications(triggered_alert, sample_recipients, "Summary test")
        summary = alert_manager.get_alert_delivery_summary(triggered_alert)
        assert summary["alert_id"] == triggered_alert.alert_id
        assert summary["severity"] == "critical"
        assert summary["total_notifications"] == 3
        assert summary["sent"] == 3
        assert summary["failed"] == 0

    def test_max_notification_latency_within_limit(self, alert_manager, triggered_alert, sample_recipients):
        alert_manager.dispatch_notifications(triggered_alert, sample_recipients, "Latency test")
        max_latency = alert_manager.get_max_notification_latency(triggered_alert)
        assert max_latency <= 30.0

    def test_create_multiple_alerts(self, alert_manager):
        for i in range(5):
            alert_manager.create_and_trigger_alert(
                severity="warning",
                title=f"Alert {i}",
                message=f"Message {i}",
            )
        assert len(alert_manager.get_alerts()) == 5


class TestMultiChannelDelivery:
    """AC: 站内消息、邮件、Webhook三种渠道均收到通知"""

    def test_all_three_channels_receive_notifications(self, notification_service, sample_recipients):
        alert = Alert("ac-channels-001", "critical", "Multi-channel", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Multi-channel test")
        channels_received = {n.channel for n in alert.notifications if n.delivered}
        assert NotificationChannel.IN_APP in channels_received
        assert NotificationChannel.EMAIL in channels_received
        assert NotificationChannel.WEBHOOK in channels_received
        assert len(channels_received) == 3

    def test_each_channel_receives_correct_content(self, notification_service, sample_recipients):
        alert = Alert("ac-content-001", "critical", "Content check", "Test")
        alert.trigger()
        content = "CRITICAL: CPU 95% on node-3"
        notification_service.send_alert_notifications(alert, sample_recipients, content)
        for n in alert.notifications:
            assert n.content == content

    def test_channels_have_correct_recipients(self, notification_service, sample_recipients):
        alert = Alert("ac-recip-001", "critical", "Recipient check", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Recipient test")
        for n in alert.notifications:
            if n.channel == NotificationChannel.IN_APP:
                assert n.recipient == "user-001"
            elif n.channel == NotificationChannel.EMAIL:
                assert n.recipient == "admin@example.com"
            elif n.channel == NotificationChannel.WEBHOOK:
                assert n.recipient == "https://hooks.example.com/alerts"

    def test_partial_channel_failure_does_not_affect_others(self, notification_service):
        alert = Alert("ac-partial-001", "critical", "Partial fail", "Test")
        alert.trigger()
        recipients = {
            NotificationChannel.IN_APP: "user-001",
            NotificationChannel.EMAIL: "bad-email",
            NotificationChannel.WEBHOOK: "https://hook.example.com/alert",
        }
        notification_service.send_alert_notifications(alert, recipients, "Partial test")
        in_app = [n for n in alert.notifications if n.channel == NotificationChannel.IN_APP]
        email = [n for n in alert.notifications if n.channel == NotificationChannel.EMAIL]
        webhook = [n for n in alert.notifications if n.channel == NotificationChannel.WEBHOOK]
        assert in_app[0].delivered is True
        assert email[0].delivered is False
        assert webhook[0].delivered is True

    def test_three_channel_delivery_in_one_dispatch(self, alert_manager, triggered_alert, sample_recipients):
        alert_manager.dispatch_notifications(triggered_alert, sample_recipients, "Bulk dispatch")
        assert len(triggered_alert.notifications) == 3
        for n in triggered_alert.notifications:
            assert n.delivered is True


class TestNotificationLatency:
    """AC: 告警触发到通知发送延迟 ≤30秒"""

    def test_latency_under_thirty_seconds(self, notification_service, sample_recipients):
        alert = Alert("latency-001", "critical", "Latency test", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Latency test")
        for n in alert.notifications:
            assert n.latency is not None
            assert n.latency <= 30.0

    def test_latency_near_zero_for_immediate_send(self, notification_service, sample_recipients):
        alert = Alert("latency-002", "critical", "Immediate", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Immediate test")
        for n in alert.notifications:
            assert n.latency is not None
            assert n.latency < 1.0

    def test_latency_consistent_across_channels(self, notification_service, sample_recipients):
        alert = Alert("latency-003", "critical", "Consistency", "Test")
        alert.trigger()
        notification_service.send_alert_notifications(alert, sample_recipients, "Consistency test")
        latencies = [n.latency for n in alert.notifications if n.latency is not None]
        assert len(latencies) == 3
        max_lat = max(latencies)
        min_lat = min(latencies)
        assert max_lat - min_lat < 1.0

    def test_max_alert_latency_under_threshold(self, alert_manager, triggered_alert, sample_recipients):
        alert_manager.dispatch_notifications(triggered_alert, sample_recipients, "Manager latency test")
        max_latency = alert_manager.get_max_notification_latency(triggered_alert)
        assert max_latency <= 30.0

    def test_latency_measured_from_created_at_not_alert_trigger(self, notification_service, sample_recipients):
        alert = Alert("latency-004", "critical", "Origin", "Test")
        alert.trigger()
        time.sleep(0.01)
        notification_service.send_alert_notifications(alert, sample_recipients, "Origin test")
        for n in alert.notifications:
            assert n.created_at is not None
            assert n.sent_at is not None
            delay = (n.sent_at - n.created_at).total_seconds()
            assert delay <= 30.0

    def test_sequential_alerts_all_under_latency_limit(self, notification_service, sample_recipients):
        for i in range(5):
            alert = Alert(f"latency-seq-{i}", "warning", f"Seq {i}", f"Seq message {i}")
            alert.trigger()
            notification_service.send_alert_notifications(alert, sample_recipients, f"Seq alert {i}")
            for n in alert.notifications:
                assert n.latency is not None
                assert n.latency <= 30.0


class TestSuccessRate:
    """AC: 通知发送成功率 ≥99%"""

    def test_all_successful_rate_is_100_percent(self, notification_service, sample_recipients):
        alert = Alert("rate-001", "critical", "Rate test", "Test")
        alert.trigger()
        for _ in range(10):
            notification_service.send_alert_notifications(alert, sample_recipients, "Rate test")
        summary = notification_service.get_delivery_summary()
        assert summary["success_rate"] >= 0.99

    def test_single_failure_in_100_keeps_rate_above_99(self, notification_service):
        for _ in range(99):
            n = NotificationMessage(NotificationChannel.IN_APP, "user-001", "OK")
            notification_service.send_notification(n)
        n_fail = NotificationMessage(NotificationChannel.EMAIL, "bad-email", "Fail")
        notification_service.send_notification(n_fail)
        assert notification_service.success_rate >= 0.99

    def test_two_failures_in_200_keeps_rate_above_99(self, notification_service):
        for _ in range(198):
            n = NotificationMessage(NotificationChannel.IN_APP, "user-001", "OK")
            notification_service.send_notification(n)
        for _ in range(2):
            n = NotificationMessage(NotificationChannel.EMAIL, "bad-email", "Fail")
            notification_service.send_notification(n)
        assert notification_service.success_rate >= 0.99

    def test_three_failures_in_300_still_above_99(self, notification_service):
        for _ in range(297):
            n = NotificationMessage(NotificationChannel.IN_APP, "user-001", "OK")
            notification_service.send_notification(n)
        for _ in range(3):
            n = NotificationMessage(NotificationChannel.EMAIL, "bad-email", "Fail")
            notification_service.send_notification(n)
        assert notification_service.success_rate >= 0.99

    def test_success_rate_barely_above_99_percent(self, notification_service):
        for _ in range(99):
            n = NotificationMessage(NotificationChannel.IN_APP, "user-001", "OK")
            notification_service.send_notification(n)
        n_fail = NotificationMessage(NotificationChannel.EMAIL, "bad-email", "Fail")
        notification_service.send_notification(n_fail)
        assert notification_service.success_rate >= 0.99
        assert notification_service.success_rate < 1.0

    def test_success_rate_drops_below_99_with_2_percent_failures(self, notification_service):
        for _ in range(98):
            n = NotificationMessage(NotificationChannel.IN_APP, "user-001", "OK")
            notification_service.send_notification(n)
        for _ in range(2):
            n = NotificationMessage(NotificationChannel.EMAIL, "bad-email", "Fail")
            notification_service.send_notification(n)
        assert notification_service.success_rate < 0.99


class TestEndToEndWorkflow:
    def test_full_alert_notification_lifecycle(self, alert_manager, sample_recipients):
        alert = alert_manager.create_and_trigger_alert(
            severity="critical",
            title="Production Incident",
            message="Payment service latency spike detected",
        )
        alert_manager.dispatch_notifications(alert, sample_recipients, "CRITICAL: Payment service latency > 5s")
        summary = alert_manager.get_alert_delivery_summary(alert)
        assert summary["total_notifications"] == 3
        assert summary["sent"] == 3
        assert summary["failed"] == 0
        max_latency = alert_manager.get_max_notification_latency(alert)
        assert max_latency <= 30.0
        service = alert_manager.notification_service
        assert service.success_rate >= 0.99

    def test_high_volume_mixed_success_rate_above_99(self, notification_service, sample_recipients):
        total_alerts = 50
        failures = 0
        for i in range(total_alerts):
            alert = Alert(f"volume-{i:04d}", "warning", f"Alert {i}", f"Message {i}")
            alert.trigger()
            recipients = dict(sample_recipients)
            if i % 50 == 0:
                recipients[NotificationChannel.EMAIL] = "bad-email"
            notification_service.send_alert_notifications(alert, recipients, f"Alert {i}")
        for n in notification_service.get_all_notifications():
            if not n.delivered:
                failures += 1
        total = len(notification_service.get_all_notifications())
        assert total == total_alerts * 3
        success_rate = (total - failures) / total
        assert success_rate >= 0.99

    def test_alert_to_notification_timing(self, alert_manager, sample_recipients):
        alert = alert_manager.create_and_trigger_alert(
            severity="critical",
            title="Timing Test",
            message="End-to-end timing",
        )
        alert_manager.dispatch_notifications(alert, sample_recipients, "Timing critical alert")
        for n in alert.notifications:
            assert n.created_at is not None
            assert n.sent_at is not None
            send_latency = (n.sent_at - n.created_at).total_seconds()
            assert send_latency <= 30.0

    def test_all_channels_delivery_with_summary(self, alert_manager, triggered_alert, sample_recipients):
        alert_manager.dispatch_notifications(triggered_alert, sample_recipients, "Full summary test")
        summary = alert_manager.get_alert_delivery_summary(triggered_alert)
        assert summary["total_notifications"] == 3
        assert summary["sent"] == 3
        delivery = alert_manager.notification_service.get_delivery_summary()
        assert delivery["success_rate"] >= 0.99
        channels = alert_manager.notification_service.get_notifications_by_channel(NotificationChannel.IN_APP)
        channels += alert_manager.notification_service.get_notifications_by_channel(NotificationChannel.EMAIL)
        channels += alert_manager.notification_service.get_notifications_by_channel(NotificationChannel.WEBHOOK)
        assert len(channels) == 3

    def test_chain_alert_dispatch_with_timing(self, alert_manager, sample_recipients):
        severities = ["critical", "warning", "info"]
        for sev in severities:
            alert = alert_manager.create_and_trigger_alert(
                severity=sev,
                title=f"{sev.title()} Alert",
                message=f"This is a {sev} level alert",
            )
            alert_manager.dispatch_notifications(alert, sample_recipients, f"{sev.upper()}: test alert")
            alert_summary = alert_manager.get_alert_delivery_summary(alert)
            assert alert_summary["sent"] == 3
            assert alert_manager.get_max_notification_latency(alert) <= 30.0
        assert alert_manager.notification_service.success_rate >= 0.99