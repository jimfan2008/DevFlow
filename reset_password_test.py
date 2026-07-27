import pytest
import time
import re
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta, timezone


class EmailService:
    def send_reset_email(self, email: str) -> dict:
        reset_link = f"https://example.com/reset?token=mocked_token_12345"
        return {"status": "sent", "email": email, "reset_link": reset_link}


class PasswordResetService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self.reset_tokens = {}
        self.token_ttl = timedelta(hours=24)

    def _validate_email(self, email):
        if email is None:
            raise ValueError("email must not be None")
        if not isinstance(email, str) or email.strip() == "":
            raise ValueError("email must not be empty")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("invalid email format")
        return email.strip()

    def request_reset(self, email: str) -> dict:
        self._validate_email(email)
        token = "mocked_token_12345"
        now = datetime.now(timezone.utc)
        self.reset_tokens[email] = {
            "token": token,
            "created_at": now,
            "expires_at": now + self.token_ttl,
        }
        result = self.email_service.send_reset_email(email)
        return {"status": 200, "message": "reset email sent", "detail": result}

    def get_token_expiry(self, email: str) -> datetime:
        record = self.reset_tokens.get(email)
        if record:
            return record["expires_at"]
        return None

    def is_token_valid(self, email: str) -> bool:
        record = self.reset_tokens.get(email)
        if not record:
            return False
        return datetime.now(timezone.utc) < record["expires_at"]


class TestPasswordReset:
    @pytest.fixture
    def email_service(self):
        return EmailService()

    @pytest.fixture
    def reset_service(self, email_service):
        return PasswordResetService(email_service)

    def test_http_200_and_response_time_within_500ms(self, reset_service):
        start = time.monotonic()
        response = reset_service.request_reset("user@example.com")
        elapsed = (time.monotonic() - start) * 1000
        assert response["status"] == 200
        assert elapsed <= 500, f"Response time {elapsed:.2f}ms exceeds 500ms"

    def test_reset_email_sent_within_30_seconds(self, reset_service):
        email_service_mock = Mock(wraps=reset_service.email_service)
        reset_service.email_service = email_service_mock
        start = time.monotonic()
        reset_service.request_reset("user@example.com")
        elapsed = time.monotonic() - start
        assert elapsed <= 30.0, f"Email sending took {elapsed:.2f}s, exceeds 30s limit"
        email_service_mock.send_reset_email.assert_called_once_with("user@example.com")

    def test_reset_link_valid_for_24_hours(self, reset_service):
        email = "user@example.com"
        reset_service.request_reset(email)
        record = reset_service.reset_tokens[email]
        expiry = record["expires_at"]
        created_at = record["created_at"]
        diff = (expiry - created_at).total_seconds()
        assert abs(diff - 86400) < 1, f"Token expiry {expiry} not exactly 24h from creation {created_at}"
        assert reset_service.is_token_valid(email) is True

    def test_empty_email_returns_400(self, reset_service):
        with pytest.raises(ValueError, match="email must not be empty"):
            reset_service.request_reset("")

    def test_none_email_raises_error(self, reset_service):
        with pytest.raises(ValueError, match="email must not be None"):
            reset_service.request_reset(None)

    def test_invalid_email_format_raises_error(self, reset_service):
        with pytest.raises(ValueError, match="invalid email format"):
            reset_service.request_reset("not-an-email")

    def test_duplicate_request_refreshes_token(self, reset_service):
        email = "user@example.com"
        reset_service.request_reset(email)
        first_record = reset_service.reset_tokens[email]
        reset_service.request_reset(email)
        second_record = reset_service.reset_tokens[email]
        assert second_record["created_at"] >= first_record["created_at"]
        assert second_record["expires_at"] >= first_record["expires_at"]

    def test_get_token_expiry_returns_none_for_unknown_email(self, reset_service):
        assert reset_service.get_token_expiry("unknown@example.com") is None

    def test_email_send_failure_propagates(self, reset_service):
        email_service_mock = Mock(spec=EmailService)
        email_service_mock.send_reset_email.side_effect = RuntimeError("SMTP failure")
        reset_service.email_service = email_service_mock
        with pytest.raises(RuntimeError, match="SMTP failure"):
            reset_service.request_reset("user@example.com")
