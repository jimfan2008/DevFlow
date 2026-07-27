import pytest
import uuid
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Optional


class AlertSeverity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "info"
    DEBUG = "debug"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"


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

    def mark_sent(self) -> None:
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.now()

    def mark_skipped(self, reason: str) -> None:
        self.status = NotificationStatus.SKIPPED
        self.error = reason

    def mark_failed(self, error: str) -> None:
        self.status = NotificationStatus.FAILED
        self.error = error

    @property
    def delivered(self) -> bool:
        return self.status == NotificationStatus.SENT


class DNDConfig:
    def __init__(self, config_id: str, start_time: str, end_time: str, days_of_week: Optional[list[int]] = None):
        self.config_id = config_id
        self.start_time = start_time
        self.end_time = end_time
        self.days_of_week = days_of_week
        self.enabled = True

    def _parse_time(self, t: str) -> time:
        parts = t.split(":")
        return time(int(parts[0]), int(parts[1]))

    def is_in_dnd(self, dt: Optional[datetime] = None) -> bool:
        if not self.enabled:
            return False
        if dt is None:
            dt = datetime.now()
        if self.days_of_week is not None and dt.weekday() not in self.days_of_week:
            return False
        dnd_start = self._parse_time(self.start_time)
        dnd_end = self._parse_time(self.end_time)
        current = dt.time()
        if dnd_start <= dnd_end:
            return dnd_start <= current <= dnd_end
        else:
            return current >= dnd_start or current <= dnd_end

    def toggle(self, enabled: bool) -> None:
        self.enabled = enabled


class UserDNDSettings:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.enabled = False
        self._configs: list[DNDConfig] = []

    def add_config(self, config: DNDConfig) -> None:
        self._configs.append(config)

    def remove_config(self, config_id: str) -> None:
        self._configs = [c for c in self._configs if c.config_id != config_id]

    def get_configs(self) -> list[DNDConfig]:
        return self._configs.copy()

    def get_config_by_id(self, config_id: str) -> Optional[DNDConfig]:
        for c in self._configs:
            if c.config_id == config_id:
                return c
        return None

    def toggle_dnd(self, enabled: bool) -> None:
        self.enabled = enabled

    def is_in_dnd(self, dt: Optional[datetime] = None) -> bool:
        if not self.enabled:
            return False
        return any(c.is_in_dnd(dt) for c in self._configs if c.enabled)

    def clear_configs(self) -> None:
        self._configs.clear()


class Alert:
    def __init__(self, alert_id: str, severity: AlertSeverity, title: str, message: str):
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


class DNDNotificationService:
    CRITICAL_SEVERITIES = {AlertSeverity.CRITICAL}

    def __init__(self):
        self._sender = InAppSender()
        self._user_settings: dict[str, UserDNDSettings] = {}
        self._sent_notifications: list[NotificationMessage] = []

    def set_user_settings(self, user_id: str, settings: UserDNDSettings) -> None:
        self._user_settings[user_id] = settings

    def get_user_settings(self, user_id: str) -> Optional[UserDNDSettings]:
        return self._user_settings.get(user_id)

    def should_send(self, user_id: str, severity: AlertSeverity, now: Optional[datetime] = None) -> bool:
        if severity in self.CRITICAL_SEVERITIES:
            return True
        settings = self._user_settings.get(user_id)
        if settings is None:
            return True
        if not settings.enabled:
            return True
        if settings.is_in_dnd(now):
            return False
        return True

    def dispatch_alert(self, user_id: str, alert: Alert, recipients: dict[NotificationChannel, str]) -> list[NotificationMessage]:
        results: list[NotificationMessage] = []
        for channel, recipient in recipients.items():
            notification = NotificationMessage(
                channel=channel,
                recipient=recipient,
                content=f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}",
            )
            alert.add_notification(notification)
            if self.should_send(user_id, alert.severity):
                self._sender.send(notification)
            else:
                notification.mark_skipped("DND period active")
            self._sent_notifications.append(notification)
            results.append(notification)
        return results

    def get_sent_notifications(self) -> list[NotificationMessage]:
        return self._sent_notifications.copy()

    def get_notifications_by_status(self, status: NotificationStatus) -> list[NotificationMessage]:
        return [n for n in self._sent_notifications if n.status == status]


@pytest.fixture
def dnd_service():
    return DNDNotificationService()


@pytest.fixture
def user_id():
    return "user-001"


@pytest.fixture
def default_recipients():
    return {
        NotificationChannel.IN_APP: "user-001",
        NotificationChannel.EMAIL: "admin@example.com",
    }


@pytest.fixture
def warning_alert():
    alert = Alert(
        alert_id=str(uuid.uuid4()),
        severity=AlertSeverity.WARNING,
        title="Disk Space Low",
        message="Disk usage at 85%",
    )
    alert.trigger()
    return alert


@pytest.fixture
def critical_alert():
    alert = Alert(
        alert_id=str(uuid.uuid4()),
        severity=AlertSeverity.CRITICAL,
        title="Service Down",
        message="nginx is not responding",
    )
    alert.trigger()
    return alert


@pytest.fixture
def dnd_settings_in_period(user_id):
    settings = UserDNDSettings(user_id)
    settings.toggle_dnd(True)
    settings.add_config(DNDConfig(
        config_id="dnd-001",
        start_time="00:00",
        end_time="23:59",
        days_of_week=None,
    ))
    return settings


class TestDNDConfig:
    def test_create_dnd_config_with_time_range(self):
        config = DNDConfig(
            config_id="dnd-001",
            start_time="22:00",
            end_time="08:00",
            days_of_week=[0, 1, 2, 3, 4],
        )
        assert config.config_id == "dnd-001"
        assert config.start_time == "22:00"
        assert config.end_time == "08:00"
        assert config.days_of_week == [0, 1, 2, 3, 4]
        assert config.enabled is True

    def test_dnd_config_within_same_day(self):
        config = DNDConfig("dnd-002", "09:00", "17:00")
        dt_in = datetime(2025, 1, 15, 12, 0)
        dt_out = datetime(2025, 1, 15, 8, 0)
        assert config.is_in_dnd(dt_in) is True
        assert config.is_in_dnd(dt_out) is False

    def test_dnd_config_wrapping_midnight(self):
        config = DNDConfig("dnd-003", "22:00", "06:00")
        dt_after_midnight = datetime(2025, 1, 15, 2, 0)
        dt_before_start = datetime(2025, 1, 15, 21, 0)
        dt_within = datetime(2025, 1, 15, 23, 30)
        assert config.is_in_dnd(dt_after_midnight) is True
        assert config.is_in_dnd(dt_within) is True
        assert config.is_in_dnd(dt_before_start) is False

    def test_dnd_config_respects_days_of_week(self):
        config = DNDConfig("dnd-004", "09:00", "17:00", days_of_week=[0, 1, 2, 3, 4])
        monday = datetime(2025, 1, 13, 12, 0)
        saturday = datetime(2025, 1, 18, 12, 0)
        assert monday.weekday() == 0
        assert saturday.weekday() == 5
        assert config.is_in_dnd(monday) is True
        assert config.is_in_dnd(saturday) is False

    def test_dnd_config_disabled_returns_false(self):
        config = DNDConfig("dnd-005", "00:00", "23:59")
        config.toggle(False)
        dt = datetime(2025, 1, 15, 12, 0)
        assert config.is_in_dnd(dt) is False

    def test_dnd_config_defaults_to_all_days(self):
        config = DNDConfig("dnd-006", "00:00", "23:59")
        sunday = datetime(2025, 1, 12, 12, 0)
        saturday = datetime(2025, 1, 18, 12, 0)
        assert config.is_in_dnd(sunday) is True
        assert config.is_in_dnd(saturday) is True

    def test_dnd_config_at_boundary_start(self):
        config = DNDConfig("dnd-007", "22:00", "06:00")
        dt = datetime(2025, 1, 15, 22, 0)
        assert config.is_in_dnd(dt) is True

    def test_dnd_config_at_boundary_end(self):
        config = DNDConfig("dnd-008", "22:00", "06:00")
        dt = datetime(2025, 1, 15, 6, 0)
        assert config.is_in_dnd(dt) is True

    def test_dnd_config_outside_range(self):
        config = DNDConfig("dnd-009", "22:00", "06:00")
        dt = datetime(2025, 1, 15, 12, 0)
        assert config.is_in_dnd(dt) is False

    def test_dnd_config_enable_after_disabled(self):
        config = DNDConfig("dnd-010", "00:00", "23:59")
        config.toggle(False)
        assert config.is_in_dnd(datetime.now()) is False
        config.toggle(True)
        assert config.is_in_dnd(datetime.now()) is True


class TestUserDNDSettings:
    def test_default_settings_disabled_and_empty(self, user_id):
        settings = UserDNDSettings(user_id)
        assert settings.user_id == user_id
        assert settings.enabled is False
        assert settings.get_configs() == []

    def test_toggle_dnd_enable_disable(self, user_id):
        settings = UserDNDSettings(user_id)
        assert settings.enabled is False
        settings.toggle_dnd(True)
        assert settings.enabled is True
        settings.toggle_dnd(False)
        assert settings.enabled is False

    def test_add_config_to_settings(self, user_id):
        settings = UserDNDSettings(user_id)
        config = DNDConfig("dnd-001", "22:00", "08:00")
        settings.add_config(config)
        assert len(settings.get_configs()) == 1
        assert settings.get_configs()[0] is config

    def test_remove_config_from_settings(self, user_id):
        settings = UserDNDSettings(user_id)
        config = DNDConfig("dnd-001", "22:00", "08:00")
        settings.add_config(config)
        settings.remove_config("dnd-001")
        assert settings.get_configs() == []

    def test_get_config_by_id_found(self, user_id):
        settings = UserDNDSettings(user_id)
        config = DNDConfig("dnd-001", "22:00", "08:00")
        settings.add_config(config)
        assert settings.get_config_by_id("dnd-001") is config

    def test_get_config_by_id_not_found(self, user_id):
        settings = UserDNDSettings(user_id)
        assert settings.get_config_by_id("nonexistent") is None

    def test_add_multiple_configs(self, user_id):
        settings = UserDNDSettings(user_id)
        for i in range(3):
            settings.add_config(DNDConfig(f"dnd-{i:03d}", "22:00", "08:00"))
        assert len(settings.get_configs()) == 3

    def test_clear_configs(self, user_id):
        settings = UserDNDSettings(user_id)
        settings.add_config(DNDConfig("dnd-001", "22:00", "08:00"))
        settings.add_config(DNDConfig("dnd-002", "12:00", "14:00"))
        settings.clear_configs()
        assert settings.get_configs() == []

    def test_is_in_dnd_disabled_returns_false(self, user_id):
        settings = UserDNDSettings(user_id)
        settings.add_config(DNDConfig("dnd-001", "00:00", "23:59"))
        assert settings.enabled is False
        assert settings.is_in_dnd(datetime.now()) is False

    def test_is_in_dnd_enabled_within_period(self, user_id):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(True)
        config = DNDConfig("dnd-001", "00:00", "23:59")
        settings.add_config(config)
        dt = datetime(2025, 1, 15, 12, 0)
        assert settings.is_in_dnd(dt) is True

    def test_is_in_dnd_enabled_outside_period(self, user_id):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(True)
        config = DNDConfig("dnd-001", "09:00", "17:00")
        settings.add_config(config)
        dt = datetime(2025, 1, 15, 20, 0)
        assert settings.is_in_dnd(dt) is False

    def test_is_in_dnd_matches_any_config(self, user_id):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(True)
        settings.add_config(DNDConfig("dnd-001", "00:00", "08:00"))
        settings.add_config(DNDConfig("dnd-002", "22:00", "23:59"))
        dt1 = datetime(2025, 1, 15, 3, 0)
        dt2 = datetime(2025, 1, 15, 23, 0)
        dt3 = datetime(2025, 1, 15, 12, 0)
        assert settings.is_in_dnd(dt1) is True
        assert settings.is_in_dnd(dt2) is True
        assert settings.is_in_dnd(dt3) is False


class TestDNDNotificationServiceWARNING:
    """AC: WARNING级别在免打扰时段不发送通知"""

    def test_warning_during_dnd_not_sent(self, dnd_service, user_id, warning_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        assert len(results) == 2
        for n in results:
            assert n.status == NotificationStatus.SKIPPED
            assert n.error == "DND period active"

    def test_warning_outside_dnd_sent_normally(self, dnd_service, user_id, warning_alert, default_recipients):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(True)
        settings.add_config(DNDConfig("dnd-001", "22:00", "08:00"))
        dnd_service.set_user_settings(user_id, settings)
        dt = datetime(2025, 1, 15, 12, 0)
        assert settings.is_in_dnd(dt) is False
        results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        for n in results:
            assert n.status == NotificationStatus.SENT

    def test_warning_when_dnd_disabled_sent_normally(self, dnd_service, user_id, warning_alert, default_recipients):
        settings = UserDNDSettings(user_id)
        settings.add_config(DNDConfig("dnd-001", "00:00", "23:59"))
        dnd_service.set_user_settings(user_id, settings)
        results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        for n in results:
            assert n.status == NotificationStatus.SENT

    def test_warning_when_no_settings_sent_normally(self, dnd_service, user_id, warning_alert, default_recipients):
        results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        for n in results:
            assert n.status == NotificationStatus.SENT

    def test_warning_dnd_multiple_channels_all_skipped(self, dnd_service, user_id, warning_alert, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        recipients = {
            NotificationChannel.IN_APP: "user-001",
            NotificationChannel.EMAIL: "admin@example.com",
        }
        results = dnd_service.dispatch_alert(user_id, warning_alert, recipients)
        assert all(n.status == NotificationStatus.SKIPPED for n in results)

    def test_warning_dnd_no_notification_in_sent_list(self, dnd_service, user_id, warning_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        sent = dnd_service.get_notifications_by_status(NotificationStatus.SENT)
        assert len(sent) == 0

    def test_warning_dnd_notifications_in_skipped_list(self, dnd_service, user_id, warning_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        skipped = dnd_service.get_notifications_by_status(NotificationStatus.SKIPPED)
        assert len(skipped) == 2

    def test_warning_dnd_alert_still_triggered(self, dnd_service, user_id, warning_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        assert len(results) == 2
        assert warning_alert.triggered_at is not None
        assert len(warning_alert.notifications) == 2


class TestDNDNotificationServiceCRITICAL:
    """AC: CRITICAL级别在免打扰时段正常发送通知"""

    def test_critical_during_dnd_sent_normally(self, dnd_service, user_id, critical_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        results = dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        assert len(results) == 2
        for n in results:
            assert n.status == NotificationStatus.SENT

    def test_critical_outside_dnd_sent_normally(self, dnd_service, user_id, critical_alert, default_recipients):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(True)
        settings.add_config(DNDConfig("dnd-001", "22:00", "08:00"))
        dnd_service.set_user_settings(user_id, settings)
        results = dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        for n in results:
            assert n.status == NotificationStatus.SENT

    def test_critical_dnd_disabled_sent_normally(self, dnd_service, user_id, critical_alert, default_recipients):
        settings = UserDNDSettings(user_id)
        settings.add_config(DNDConfig("dnd-001", "00:00", "23:59"))
        dnd_service.set_user_settings(user_id, settings)
        results = dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        for n in results:
            assert n.status == NotificationStatus.SENT

    def test_critical_dnd_all_channels_sent(self, dnd_service, user_id, critical_alert, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        recipients = {
            NotificationChannel.IN_APP: "user-001",
            NotificationChannel.EMAIL: "admin@example.com",
        }
        results = dnd_service.dispatch_alert(user_id, critical_alert, recipients)
        assert all(n.status == NotificationStatus.SENT for n in results)
        assert len(results) == 2

    def test_critical_dnd_in_sent_list(self, dnd_service, user_id, critical_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        sent = dnd_service.get_notifications_by_status(NotificationStatus.SENT)
        assert len(sent) == 2

    def test_critical_dnd_not_in_skipped_list(self, dnd_service, user_id, critical_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        skipped = dnd_service.get_notifications_by_status(NotificationStatus.SKIPPED)
        assert len(skipped) == 0

    def test_critical_dnd_multiple_alerts_all_sent(self, dnd_service, user_id, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        for i in range(5):
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                severity=AlertSeverity.CRITICAL,
                title=f"Critical Alert {i}",
                message=f"Critical message {i}",
            )
            alert.trigger()
            results = dnd_service.dispatch_alert(user_id, alert, default_recipients)
            assert all(n.status == NotificationStatus.SENT for n in results)

    def test_critical_dnd_notifications_attached_to_alert(self, dnd_service, user_id, critical_alert, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        assert len(critical_alert.notifications) == 2
        for n in critical_alert.notifications:
            assert n.status == NotificationStatus.SENT


class TestDNDMixedSeverity:
    """AC: 同一用户同时处理WARNING和CRITICAL告警"""

    def test_mixed_severity_dnd_warning_skipped_critical_sent(self, dnd_service, user_id, default_recipients, dnd_settings_in_period):
        dnd_service.set_user_settings(user_id, dnd_settings_in_period)
        warning_alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=AlertSeverity.WARNING,
            title="Warning Alert",
            message="Warning message",
        )
        warning_alert.trigger()
        critical_alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=AlertSeverity.CRITICAL,
            title="Critical Alert",
            message="Critical message",
        )
        critical_alert.trigger()
        warning_results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        critical_results = dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        assert all(n.status == NotificationStatus.SKIPPED for n in warning_results)
        assert all(n.status == NotificationStatus.SENT for n in critical_results)

    def test_mixed_severity_dnd_off_both_sent(self, dnd_service, user_id, warning_alert, critical_alert, default_recipients):
        settings = UserDNDSettings(user_id)
        settings.add_config(DNDConfig("dnd-001", "00:00", "23:59"))
        dnd_service.set_user_settings(user_id, settings)
        w_results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        c_results = dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        assert all(n.status == NotificationStatus.SENT for n in w_results)
        assert all(n.status == NotificationStatus.SENT for n in c_results)

    def test_mixed_severity_outside_dnd_both_sent(self, dnd_service, user_id, warning_alert, critical_alert, default_recipients):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(True)
        settings.add_config(DNDConfig("dnd-001", "22:00", "08:00"))
        dnd_service.set_user_settings(user_id, settings)
        dt = datetime(2025, 1, 15, 12, 0)
        assert settings.is_in_dnd(dt) is False
        w_results = dnd_service.dispatch_alert(user_id, warning_alert, default_recipients)
        c_results = dnd_service.dispatch_alert(user_id, critical_alert, default_recipients)
        assert all(n.status == NotificationStatus.SENT for n in w_results)
        assert all(n.status == NotificationStatus.SENT for n in c_results)

    def test_mixed_severity_multiple_users_independent_dnd(self, dnd_service, default_recipients):
        user_a = "user-a"
        user_b = "user-b"
        settings_a = UserDNDSettings(user_a)
        settings_a.toggle_dnd(True)
        settings_a.add_config(DNDConfig("dnd-a-001", "00:00", "23:59"))
        settings_b = UserDNDSettings(user_b)
        settings_b.toggle_dnd(True)
        settings_b.add_config(DNDConfig("dnd-b-001", "08:00", "12:00"))
        dnd_service.set_user_settings(user_a, settings_a)
        dnd_service.set_user_settings(user_b, settings_b)
        dt = datetime(2025, 1, 15, 10, 0)
        assert settings_a.is_in_dnd(dt) is True
        assert settings_b.is_in_dnd(dt) is True
        warn_a = Alert(str(uuid.uuid4()), AlertSeverity.WARNING, "W-A", "W-A msg")
        warn_a.trigger()
        crit_b = Alert(str(uuid.uuid4()), AlertSeverity.CRITICAL, "C-B", "C-B msg")
        crit_b.trigger()
        r_a = dnd_service.dispatch_alert(user_a, warn_a, default_recipients)
        r_b = dnd_service.dispatch_alert(user_b, crit_b, default_recipients)
        assert all(n.status == NotificationStatus.SKIPPED for n in r_a)
        assert all(n.status == NotificationStatus.SENT for n in r_b)


class TestDNDUserSettingsManagement:
    """AC: 用户可在个人设置中管理免打扰时段"""

    def test_create_dnd_settings_with_config(self, user_id):
        settings = UserDNDSettings(user_id)
        config = DNDConfig("dnd-001", "22:00", "08:00", days_of_week=[0, 1, 2, 3, 4])
        settings.add_config(config)
        assert settings.get_config_by_id("dnd-001") is config
        assert config.enabled is True

    def test_update_dnd_config_toggle(self, user_id):
        settings = UserDNDSettings(user_id)
        config = DNDConfig("dnd-001", "22:00", "08:00")
        settings.add_config(config)
        config.toggle(False)
        assert config.enabled is False
        config.toggle(True)
        assert config.enabled is True

    def test_delete_dnd_config(self, user_id):
        settings = UserDNDSettings(user_id)
        settings.add_config(DNDConfig("dnd-001", "22:00", "08:00"))
        settings.add_config(DNDConfig("dnd-002", "12:00", "14:00"))
        settings.remove_config("dnd-001")
        assert settings.get_config_by_id("dnd-001") is None
        assert settings.get_config_by_id("dnd-002") is not None

    def test_enable_dnd_toggle_in_service(self, dnd_service, user_id):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(False)
        dnd_service.set_user_settings(user_id, settings)
        retrieved = dnd_service.get_user_settings(user_id)
        assert retrieved is not None
        assert retrieved.enabled is False
        retrieved.toggle_dnd(True)
        assert retrieved.enabled is True

    def test_get_user_settings_not_found(self, dnd_service, user_id):
        assert dnd_service.get_user_settings("nonexistent-user") is None

    def test_user_can_add_multiple_dnd_periods(self, user_id):
        settings = UserDNDSettings(user_id)
        periods = [
            ("22:00", "08:00", None),
            ("12:00", "14:00", [0, 1, 2, 3, 4]),
            ("00:00", "06:00", [5, 6]),
        ]
        for i, (start, end, days) in enumerate(periods):
            settings.add_config(DNDConfig(f"dnd-{i}", start, end, days))
        assert len(settings.get_configs()) == 3

    def test_user_can_clear_all_dnd_periods(self, user_id):
        settings = UserDNDSettings(user_id)
        settings.add_config(DNDConfig("dnd-001", "22:00", "08:00"))
        settings.add_config(DNDConfig("dnd-002", "12:00", "14:00"))
        settings.clear_configs()
        assert settings.get_configs() == []

    def test_should_send_reflects_dnd_settings(self, dnd_service, user_id):
        settings = UserDNDSettings(user_id)
        settings.toggle_dnd(True)
        settings.add_config(DNDConfig("dnd-001", "00:00", "23:59"))
        dnd_service.set_user_settings(user_id, settings)
        dt_in_dnd = datetime(2025, 1, 15, 12, 0)
        assert dnd_service.should_send(user_id, AlertSeverity.WARNING, dt_in_dnd) is False
        assert dnd_service.should_send(user_id, AlertSeverity.CRITICAL, dt_in_dnd) is True
        settings.toggle_dnd(False)
        assert dnd_service.should_send(user_id, AlertSeverity.WARNING, dt_in_dnd) is True
