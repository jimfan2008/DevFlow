import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import time
import re


class ResetToken:
    def __init__(self, email: str):
        self.email = email
        self.token = "reset-token-abc123"
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        self.created_at = datetime.now(timezone.utc)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


class EmailService:
    def send_reset_email(self, email: str, reset_link: str) -> bool:
        return True


class ForgotPasswordHandler:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self.tokens: dict[str, ResetToken] = {}

    def _validate_email(self, email: str) -> str | None:
        if not email:
            return "Email is required"
        if len(email) > 254:
            return "Email too long"
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return "Invalid email format"
        return None

    def handle_request(self, email: str) -> dict:
        error = self._validate_email(email)
        if error:
            return {"status_code": 400, "message": error}
        normalized = email.lower()
        token = ResetToken(normalized)
        self.tokens[normalized] = token
        reset_link = f"https://example.com/reset?token={token.token}"
        sent = self.email_service.send_reset_email(normalized, reset_link)
        if sent:
            return {"status_code": 200, "message": "Reset email sent"}
        return {"status_code": 500, "message": "Failed to send email"}

    def get_token_expiry(self, email: str) -> datetime | None:
        token = self.tokens.get(email.lower())
        if token:
            return token.expires_at
        return None

    def is_token_expired(self, email: str) -> bool:
        token = self.tokens.get(email.lower())
        if token:
            return token.is_expired()
        return True


class TestForgotPassword:
    @pytest.fixture
    def email_service(self):
        return EmailService()

    @pytest.fixture
    def handler(self, email_service):
        return ForgotPasswordHandler(email_service)

    def test_reset_email_sent_returns_200(self, handler):
        result = handler.handle_request("user@example.com")
        assert result["status_code"] == 200
        assert result["message"] == "Reset email sent"

    def test_response_time(self, handler):
        start = time.perf_counter()
        handler.handle_request("fast@example.com")
        elapsed = (time.perf_counter() - start) * 1000

    def test_reset_email_delivered_within_30s(self, handler):
        with patch.object(handler.email_service, "send_reset_email", return_value=True) as mock_send:
            start = time.perf_counter()
            handler.handle_request("deliver@example.com")
            elapsed = time.perf_counter() - start
            assert elapsed <= 30, f"Email delivery took {elapsed:.2f}s, expected ≤30s"
            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            assert args[0] == "deliver@example.com"
            assert "reset" in args[1].lower()

    def test_reset_link_expires_in_24h(self, handler):
        handler.handle_request("expiry@example.com")
        expiry = handler.get_token_expiry("expiry@example.com")
        assert expiry is not None
        expected = datetime.now(timezone.utc) + timedelta(hours=24)
        assert abs((expiry - expected).total_seconds()) < 5

    def test_reset_link_not_expired_within_24h(self, handler):
        handler.handle_request("valid@example.com")
        expiry = handler.get_token_expiry("valid@example.com")
        assert expiry is not None
        assert not expiry - timedelta(hours=24) > datetime.now(timezone.utc)

    def test_invalid_email_returns_400(self, handler):
        result = handler.handle_request("not-an-email")
        assert result["status_code"] == 400

    def test_email_service_failure_returns_500(self, handler):
        handler.email_service.send_reset_email = Mock(return_value=False)
        result = handler.handle_request("fail@example.com")
        assert result["status_code"] == 500

    def test_send_reset_email_called_with_correct_link(self, handler):
        with patch.object(handler.email_service, "send_reset_email", return_value=True) as mock_send:
            handler.handle_request("linkcheck@example.com")
            mock_send.assert_called_once()
            email_arg, link_arg = mock_send.call_args[0]
            assert email_arg == "linkcheck@example.com"
            assert link_arg.startswith("https://example.com/reset?token=")

    def test_multiple_requests_different_emails(self, handler):
        emails = ["a@example.com", "b@example.com", "c@example.com"]
        for email in emails:
            result = handler.handle_request(email)
            assert result["status_code"] == 200
            assert handler.tokens[email] is not None

    def test_token_expiry_precision(self, handler):
        handler.handle_request("precision@example.com")
        expiry = handler.get_token_expiry("precision@example.com")
        assert expiry is not None
        expected = datetime.now(timezone.utc) + timedelta(hours=24)
        diff = abs((expiry - expected).total_seconds())
        assert diff < 1

    def test_empty_email_returns_400(self, handler):
        result = handler.handle_request("")
        assert result["status_code"] == 400

    def test_invalid_email_format_abc_returns_400(self, handler):
        result = handler.handle_request("abc")
        assert result["status_code"] == 400

    def test_invalid_email_format_at_dot_com_returns_400(self, handler):
        result = handler.handle_request("@.com")
        assert result["status_code"] == 400

    def test_oversized_email_returns_400(self, handler):
        long_email = "user@" + "x" * 250 + ".com"
        result = handler.handle_request(long_email)
        assert result["status_code"] == 400

    def test_case_insensitive_email_normalization(self, handler):
        result = handler.handle_request("User@Example.COM")
        assert result["status_code"] == 200
        assert "user@example.com" in handler.tokens

    def test_repeated_send_returns_200(self, handler):
        email = "repeat@example.com"
        result1 = handler.handle_request(email)
        assert result1["status_code"] == 200
        result2 = handler.handle_request(email)
        assert result2["status_code"] == 200
        assert handler.tokens[email] is not None

    def test_expired_token_rejected(self, handler):
        email = "old@example.com"
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        with patch("test_forgot_password.datetime") as mock_dt:
            mock_dt.now.return_value = past
            handler.handle_request(email)
        future = past + timedelta(days=2)
        with patch("test_forgot_password.datetime") as mock_dt:
            mock_dt.now.return_value = future
            assert handler.is_token_expired(email) is True
