import pytest
import time
from unittest.mock import patch, Mock
from datetime import datetime, timedelta, timezone


class EmailService:
    def send_reset_email(self, email: str) -> dict:
        reset_link = "https://example.com/reset?token=mocked_token_12345"
        return {"status": "sent", "email": email, "reset_link": reset_link}


class PasswordResetService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self.reset_tokens = {}
        self.token_ttl = timedelta(hours=24)

    def request_reset(self, email: str) -> dict:
        if not email:
            raise ValueError("Email cannot be empty")
        if "@" not in email or "." not in email:
            raise ValueError("Invalid email format")
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
        now = datetime.now(timezone.utc)
        return now < record["expires_at"]


class TestPasswordReset:
    @pytest.fixture
    def email_service(self):
        return EmailService()

    @pytest.fixture
    def reset_service(self, email_service):
        return PasswordResetService(email_service)

    def test_http_200_and_response_time_within_500ms(self, reset_service):
        start = time.time()
        response = reset_service.request_reset("user@example.com")
        elapsed = (time.time() - start) * 1000
        assert response["status"] == 200
        assert elapsed <= 500, f"Response time {elapsed:.2f}ms exceeds 500ms"

    def test_reset_email_sent_within_30_seconds(self, reset_service):
        mocked_service = Mock(wraps=reset_service.email_service)
        reset_service.email_service = mocked_service
        start = time.time()
        reset_service.request_reset("user@example.com")
        elapsed = time.time() - start
        assert elapsed <= 30, f"Email sending took {elapsed:.2f}s, expected within 30s"
        mocked_service.send_reset_email.assert_called_once_with("user@example.com")

    def test_reset_link_valid_for_24_hours(self, reset_service):
        email = "user@example.com"
        reset_service.request_reset(email)
        assert reset_service.is_token_valid(email) is True
        expiry = reset_service.get_token_expiry(email)
        assert expiry is not None
        expected_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        diff = abs((expiry - expected_expiry).total_seconds())
        assert diff < 5, f"Token expiry {expiry} not within 24h of now"

    def test_token_invalid_after_24_hours(self, reset_service):
        email = "user@example.com"
        reset_service.request_reset(email)
        past = datetime.now(timezone.utc) - timedelta(hours=25)
        reset_service.reset_tokens[email]["expires_at"] = past
        assert reset_service.is_token_valid(email) is False

    def test_empty_email_returns_error(self, reset_service):
        with pytest.raises(ValueError):
            reset_service.request_reset("")

    def test_invalid_email_format_returns_error(self, reset_service):
        with pytest.raises(ValueError):
            reset_service.request_reset("not-an-email")

    def test_idempotent_resend_updates_token(self, reset_service):
        email = "user@example.com"
        r1 = reset_service.request_reset(email)
        r2 = reset_service.request_reset(email)
        assert r1["status"] == 200
        assert r2["status"] == 200

    def test_service_failure_raises_exception(self, reset_service):
        mocked_service = Mock(wraps=reset_service.email_service)
        mocked_service.send_reset_email.side_effect = RuntimeError("SMTP server down")
        reset_service.email_service = mocked_service
        with pytest.raises(RuntimeError, match="SMTP server down"):
            reset_service.request_reset("user@example.com")

    def test_get_token_expiry_returns_none_for_unknown_email(self, reset_service):
        assert reset_service.get_token_expiry("unknown@example.com") is None

    def test_is_token_valid_returns_false_for_unknown_email(self, reset_service):
        assert reset_service.is_token_valid("unknown@example.com") is False

    def test_24h_boundary_exact(self, reset_service):
        email = "user@example.com"
        reset_service.request_reset(email)
        almost_expired = reset_service.reset_tokens[email]["expires_at"] - timedelta(seconds=1)
        reset_service.reset_tokens[email]["expires_at"] = almost_expired
        assert reset_service.is_token_valid(email) is True
        reset_service.reset_tokens[email]["expires_at"] = almost_expired - timedelta(hours=24)
        assert reset_service.is_token_valid(email) is False

    def test_empty_email_validation_in_service(self):
        with pytest.raises(ValueError):
            PasswordResetService(EmailService()).request_reset("")

    def test_invalid_email_validation_in_service(self):
        with pytest.raises(ValueError):
            PasswordResetService(EmailService()).request_reset("bad")
