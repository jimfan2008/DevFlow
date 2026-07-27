import time
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime


class NotificationError(Exception):
    pass


class Notification:
    def __init__(self, recipient: str, message: str):
        self.recipient = recipient
        self.message = message
        self.status = "pending"
        self.retry_count = 0
        self.retry_records = []


class NotificationService:
    RETRY_INTERVALS = [1, 5, 15]

    def __init__(self, sender):
        self._sender = sender

    def send_with_retry(self, notification: Notification) -> bool:
        for attempt, interval in enumerate(self.RETRY_INTERVALS, start=1):
            notification.retry_count = attempt
            try:
                self._sender.send(notification.recipient, notification.message)
                notification.status = "sent"
                notification.retry_records.append({
                    "attempt": attempt,
                    "interval": interval,
                    "timestamp": datetime.now(),
                    "result": "success"
                })
                return True
            except NotificationError as e:
                notification.retry_records.append({
                    "attempt": attempt,
                    "interval": interval,
                    "timestamp": datetime.now(),
                    "result": "failed",
                    "error": str(e)
                })
                if attempt < len(self.RETRY_INTERVALS):
                    time.sleep(interval * 60)
        notification.status = "failed"
        return False


class TestNotificationRetry:

    @pytest.fixture(autouse=True)
    def mock_time_sleep(self):
        with patch.object(time, "sleep"):
            yield

    def setup_method(self):
        self.sender = Mock()
        self.service = NotificationService(self.sender)
        self.notification = Notification("user@example.com", "Hello")

    def test_retry_on_failure(self):
        self.sender.send.side_effect = NotificationError("SMTP timeout")
        result = self.service.send_with_retry(self.notification)
        assert result is False
        assert self.notification.status == "failed"
        assert self.sender.send.call_count == 3

    def test_retry_records_count(self):
        self.sender.send.side_effect = NotificationError("SMTP timeout")
        self.service.send_with_retry(self.notification)
        assert len(self.notification.retry_records) == 3
        for record in self.notification.retry_records:
            assert record["result"] == "failed"

    def test_retry_records_contain_attempt_numbers(self):
        self.sender.send.side_effect = NotificationError("SMTP timeout")
        self.service.send_with_retry(self.notification)
        attempt_numbers = [r["attempt"] for r in self.notification.retry_records]
        assert attempt_numbers == [1, 2, 3]

    def test_retry_records_contain_interval(self):
        self.sender.send.side_effect = NotificationError("SMTP timeout")
        self.service.send_with_retry(self.notification)
        intervals = [r["interval"] for r in self.notification.retry_records]
        assert intervals == [1, 5, 15]

    def test_retry_records_contain_timestamp(self):
        self.sender.send.side_effect = NotificationError("SMTP timeout")
        self.service.send_with_retry(self.notification)
        for record in self.notification.retry_records:
            assert isinstance(record["timestamp"], datetime)

    def test_retry_records_contain_error_message(self):
        self.sender.send.side_effect = NotificationError("SMTP timeout")
        self.service.send_with_retry(self.notification)
        for record in self.notification.retry_records:
            assert record["error"] == "SMTP timeout"

    def test_retry_records_contain_result_field(self):
        self.sender.send.side_effect = NotificationError("SMTP timeout")
        self.service.send_with_retry(self.notification)
        for record in self.notification.retry_records:
            assert "result" in record

    def test_third_failure_marks_as_failed(self):
        self.sender.send.side_effect = NotificationError("Connection refused")
        self.service.send_with_retry(self.notification)
        assert self.notification.status == "failed"

    def test_success_on_first_attempt_no_retry(self):
        self.sender.send.return_value = True
        result = self.service.send_with_retry(self.notification)
        assert result is True
        assert self.notification.status == "sent"
        assert self.sender.send.call_count == 1

    def test_success_on_second_attempt(self):
        self.sender.send.side_effect = [
            NotificationError("Timeout"),
            True
        ]
        result = self.service.send_with_retry(self.notification)
        assert result is True
        assert self.notification.status == "sent"
        assert self.sender.send.call_count == 2
        assert len(self.notification.retry_records) == 2

    def test_retry_count_tracks_properly(self):
        self.sender.send.side_effect = NotificationError("Error")
        self.service.send_with_retry(self.notification)
        assert self.notification.retry_count == 3

    def test_uses_increasing_intervals(self):
        self.sender.send.side_effect = NotificationError("Error")
        with patch.object(time, "sleep") as mock_sleep:
            self.service.send_with_retry(self.notification)
            mock_sleep.assert_has_calls([
                call(1 * 60),
                call(5 * 60),
            ])

    def test_retry_does_not_call_sleep_on_last_attempt(self):
        self.sender.send.side_effect = NotificationError("Error")
        with patch.object(time, "sleep") as mock_sleep:
            self.service.send_with_retry(self.notification)
            assert mock_sleep.call_count == 2

    def test_initial_notification_state(self):
        assert self.notification.status == "pending"
        assert self.notification.retry_count == 0
        assert self.notification.retry_records == []

    def test_successful_send_has_success_record(self):
        self.sender.send.return_value = True
        self.service.send_with_retry(self.notification)
        assert len(self.notification.retry_records) == 1
        assert self.notification.retry_records[0]["result"] == "success"
        assert self.notification.retry_records[0]["attempt"] == 1

    def test_sender_raises_non_notification_error_propagates(self):
        self.sender.send.side_effect = ConnectionError("connection lost")
        with pytest.raises(ConnectionError):
            self.service.send_with_retry(self.notification)

    def test_sender_returns_none_fails(self):
        self.sender.send.return_value = None
        result = self.service.send_with_retry(self.notification)
        assert result is True
        assert self.notification.status == "sent"

    def test_empty_recipient_handled(self):
        notification = Notification("", "Hello")
        self.sender.send.return_value = True
        result = self.service.send_with_retry(notification)
        assert result is True

    def test_none_recipient_handled(self):
        notification = Notification(None, "Hello")
        self.sender.send.return_value = True
        result = self.service.send_with_retry(notification)
        assert result is True

    def test_empty_message_handled(self):
        notification = Notification("user@example.com", "")
        self.sender.send.return_value = True
        result = self.service.send_with_retry(notification)
        assert result is True

    def test_none_message_handled(self):
        notification = Notification("user@example.com", None)
        self.sender.send.return_value = True
        result = self.service.send_with_retry(notification)
        assert result is True
