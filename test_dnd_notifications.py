import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class AlarmLevel:
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    INFO = "INFO"


class DnDManager:
    def __init__(self):
        self.dnd_start = None
        self.dnd_end = None
        self.dnd_enabled = False
        self.notification_history = []

    def set_dnd_period(self, start_hour, end_hour):
        self.dnd_start = start_hour
        self.dnd_end = end_hour
        self.dnd_enabled = True

    def disable_dnd(self):
        self.dnd_enabled = False
        self.dnd_start = None
        self.dnd_end = None

    def is_dnd_active(self, current_time: datetime) -> bool:
        if not self.dnd_enabled:
            return False
        current_hour = current_time.hour
        if self.dnd_start <= self.dnd_end:
            return self.dnd_start <= current_hour < self.dnd_end
        else:
            return current_hour >= self.dnd_start or current_hour < self.dnd_end

    def should_send_notification(self, level: str, current_time: datetime) -> bool:
        if not self.is_dnd_active(current_time):
            return True
        if level == AlarmLevel.CRITICAL:
            return True
        return False

    def send_notification(self, level: str, message: str, current_time: datetime):
        if self.should_send_notification(level, current_time):
            self.notification_history.append({
                "level": level,
                "message": message,
                "sent_at": current_time,
            })
            return True
        return False


@pytest.fixture
def dnd_manager():
    return DnDManager()


@pytest.fixture
def dnd_manager_with_period(dnd_manager):
    dnd_manager.set_dnd_period(22, 8)
    return dnd_manager


class TestDnDNotificationBasic:
    def test_dnd_disabled_all_notifications_sent(self, dnd_manager, current_time):
        dnd_manager.disable_dnd()
        assert dnd_manager.send_notification(AlarmLevel.WARNING, "warn msg", current_time) is True
        assert dnd_manager.send_notification(AlarmLevel.CRITICAL, "crit msg", current_time) is True
        assert len(dnd_manager.notification_history) == 2

    def test_warning_blocked_during_dnd(self, dnd_manager_with_period):
        dnd_time = datetime(2026, 7, 16, 1, 30, 0)
        assert dnd_manager_with_period.is_dnd_active(dnd_time) is True
        result = dnd_manager_with_period.send_notification(
            AlarmLevel.WARNING, "warn during dnd", dnd_time
        )
        assert result is False
        assert len(dnd_manager_with_period.notification_history) == 0

    def test_critical_allowed_during_dnd(self, dnd_manager_with_period):
        dnd_time = datetime(2026, 7, 16, 1, 30, 0)
        result = dnd_manager_with_period.send_notification(
            AlarmLevel.CRITICAL, "critical during dnd", dnd_time
        )
        assert result is True
        assert len(dnd_manager_with_period.notification_history) == 1
        assert dnd_manager_with_period.notification_history[0]["level"] == AlarmLevel.CRITICAL


class TestDnDPeriodBoundaries:
    def test_dnd_active_within_range(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        midnight = datetime(2026, 7, 16, 0, 0, 0)
        assert dnd_manager.is_dnd_active(midnight) is True

    def test_dnd_inactive_at_start_boundary(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        start_time = datetime(2026, 7, 16, 22, 0, 0)
        assert dnd_manager.is_dnd_active(start_time) is True

    def test_dnd_inactive_at_end_boundary(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        end_time = datetime(2026, 7, 16, 8, 0, 0)
        assert dnd_manager.is_dnd_active(end_time) is False

    def test_dnd_active_midnight_crossing(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        late_night = datetime(2026, 7, 16, 3, 0, 0)
        assert dnd_manager.is_dnd_active(late_night) is True

    def test_dnd_inactive_during_day(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        noon = datetime(2026, 7, 16, 12, 0, 0)
        assert dnd_manager.is_dnd_active(noon) is False


class TestDnDLevelGranularity:
    def test_info_blocked_during_dnd(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        dnd_time = datetime(2026, 7, 16, 2, 0, 0)
        result = dnd_manager.send_notification(
            AlarmLevel.INFO, "info msg", dnd_time
        )
        assert result is False

    def test_all_levels_pass_when_dnd_inactive(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        noon = datetime(2026, 7, 16, 12, 0, 0)
        assert dnd_manager.send_notification(AlarmLevel.INFO, "info", noon) is True
        assert dnd_manager.send_notification(AlarmLevel.WARNING, "warn", noon) is True
        assert dnd_manager.send_notification(AlarmLevel.CRITICAL, "crit", noon) is True
        assert len(dnd_manager.notification_history) == 3


class TestDnDUserSettings:
    def test_user_can_update_dnd_period(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        midnight = datetime(2026, 7, 16, 0, 0, 0)
        assert dnd_manager.is_dnd_active(midnight) is True
        dnd_manager.set_dnd_period(1, 5)
        assert dnd_manager.is_dnd_active(midnight) is False
        assert dnd_manager.is_dnd_active(datetime(2026, 7, 16, 2, 0, 0)) is True

    def test_user_can_disable_dnd(self, dnd_manager):
        dnd_manager.set_dnd_period(22, 8)
        midnight = datetime(2026, 7, 16, 0, 0, 0)
        assert dnd_manager.is_dnd_active(midnight) is True
        dnd_manager.disable_dnd()
        assert dnd_manager.is_dnd_active(midnight) is False
        assert dnd_manager.dnd_enabled is False

    def test_user_can_toggle_dnd_on_off_repeatedly(self, dnd_manager):
        dnd_manager.set_dnd_period(23, 7)
        midnight = datetime(2026, 7, 16, 0, 0, 0)
        assert dnd_manager.is_dnd_active(midnight) is True
        dnd_manager.disable_dnd()
        assert dnd_manager.is_dnd_active(midnight) is False
        dnd_manager.set_dnd_period(23, 7)
        assert dnd_manager.is_dnd_active(midnight) is True


@pytest.fixture
def current_time():
    return datetime(2026, 7, 16, 1, 30, 0)
