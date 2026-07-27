import time
import pytest


class AlertManager:
    def __init__(self, cooldown_seconds=300, time_func=None):
        self.cooldown_seconds = cooldown_seconds
        self.time_func = time_func or time.time
        self._last_alert_time = {}

    def can_trigger(self, alert_type):
        now = self.time_func()
        last_time = self._last_alert_time.get(alert_type)
        if last_time is None:
            return True
        return now - last_time >= self.cooldown_seconds

    def trigger(self, alert_type):
        self._last_alert_time[alert_type] = self.time_func()


class FakeTime:
    def __init__(self, start=0.0):
        self._now = start

    def advance(self, seconds):
        self._now += seconds

    def __call__(self):
        return self._now


class TestAlertCooldown:
    def test_first_alert_triggers_normally(self):
        clock = FakeTime(0)
        manager = AlertManager(cooldown_seconds=300, time_func=clock)
        assert manager.can_trigger('cpu_high') is True

    def test_second_alert_within_cooldown_does_not_trigger(self):
        clock = FakeTime(0)
        manager = AlertManager(cooldown_seconds=300, time_func=clock)
        manager.trigger('cpu_high')
        clock.advance(120)
        assert manager.can_trigger('cpu_high') is False

    def test_alert_triggers_again_after_cooldown_ends(self):
        clock = FakeTime(0)
        manager = AlertManager(cooldown_seconds=300, time_func=clock)
        manager.trigger('cpu_high')
        clock.advance(300)
        assert manager.can_trigger('cpu_high') is True

    def test_different_alert_types_are_independent(self):
        clock = FakeTime(0)
        manager = AlertManager(cooldown_seconds=300, time_func=clock)
        manager.trigger('cpu_high')
        clock.advance(60)
        assert manager.can_trigger('memory_high') is True
