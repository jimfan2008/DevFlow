import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time


# ---- Domain classes ----

class AlertLevel:
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DNSSettings:
    """Do-Not-Disturb settings per user."""

    def __init__(self, start_hour: int, end_hour: int, enabled: bool = True):
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.enabled = enabled

    def is_dnd_active(self, at: datetime) -> bool:
        if not self.enabled:
            return False
        hour = at.hour
        if self.start_hour < self.end_hour:
            return self.start_hour <= hour < self.end_hour
        else:
            return hour >= self.start_hour or hour < self.end_hour


class Alert:
    def __init__(self, level: str, message: str):
        self.level = level
        self.message = message


class NotificationService:
    def __init__(self, dnd_settings: DNSSettings):
        self.dnd_settings = dnd_settings
        self.sent_notifications: list[Alert] = []

    def send(self, alert: Alert, at: datetime | None = None) -> bool:
        now = at or datetime.now()
        if self.dnd_settings.is_dnd_active(now):
            if alert.level == AlertLevel.CRITICAL:
                self.sent_notifications.append(alert)
                return True
            return False
        self.sent_notifications.append(alert)
        return True


# ---- Fixtures ----

@pytest.fixture
def dnd_settings() -> DNSSettings:
    return DNSSettings(start_hour=22, end_hour=8)


@pytest.fixture
def notification_service(dnd_settings) -> NotificationService:
    return NotificationService(dnd_settings)


# ---- Tests ----

class TestDNDBlockingWarning:
    def test_warning_not_sent_during_dnd(self, notification_service: NotificationService):
        alert = Alert(AlertLevel.WARNING, "磁盘使用率超过80%")
        with freeze_time("2026-07-16 23:00:00"):
            result = notification_service.send(alert)
        assert result is False
        assert len(notification_service.sent_notifications) == 0

    def test_warning_sent_outside_dnd(self, notification_service: NotificationService):
        alert = Alert(AlertLevel.WARNING, "磁盘使用率超过80%")
        with freeze_time("2026-07-16 14:00:00"):
            result = notification_service.send(alert)
        assert result is True
        assert len(notification_service.sent_notifications) == 1


class TestDNDAllowsCritical:
    def test_critical_sent_during_dnd(self, notification_service: NotificationService):
        alert = Alert(AlertLevel.CRITICAL, "数据库宕机")
        with freeze_time("2026-07-16 02:00:00"):
            result = notification_service.send(alert)
        assert result is True
        assert len(notification_service.sent_notifications) == 1
        assert notification_service.sent_notifications[0].level == AlertLevel.CRITICAL

    def test_critical_sent_outside_dnd(self, notification_service: NotificationService):
        alert = Alert(AlertLevel.CRITICAL, "数据库宕机")
        with freeze_time("2026-07-16 10:00:00"):
            result = notification_service.send(alert)
        assert result is True
        assert len(notification_service.sent_notifications) == 1


class TestDNDSettingsManagement:
    def test_dnd_disabled_allows_all(self):
        settings = DNSSettings(start_hour=22, end_hour=8, enabled=False)
        service = NotificationService(settings)
        alert = Alert(AlertLevel.WARNING, "磁盘使用率超过80%")
        with freeze_time("2026-07-16 23:00:00"):
            result = service.send(alert)
        assert result is True

    def test_user_can_update_dnd_hours(self):
        settings = DNSSettings(start_hour=22, end_hour=8)
        assert settings.start_hour == 22
        assert settings.end_hour == 8
        settings.start_hour = 23
        settings.end_hour = 7
        assert settings.start_hour == 23
        assert settings.end_hour == 7

    def test_wrapping_dnd_range(self):
        settings = DNSSettings(start_hour=22, end_hour=8)
        assert settings.is_dnd_active(datetime(2026, 7, 16, 23, 0)) is True
        assert settings.is_dnd_active(datetime(2026, 7, 17, 1, 0)) is True
        assert settings.is_dnd_active(datetime(2026, 7, 17, 7, 59)) is True
        assert settings.is_dnd_active(datetime(2026, 7, 17, 8, 0)) is False
        assert settings.is_dnd_active(datetime(2026, 7, 16, 21, 59)) is False
