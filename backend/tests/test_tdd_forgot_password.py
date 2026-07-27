#!/usr/bin/env python3
import time
import uuid
import secrets
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from httpx import AsyncClient, ASGITransport
from pydantic import BaseModel, Field, field_validator

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI()

FORGOT_PASSWORD_URL = "/api/auth/forgot-password"


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError("email must not be empty")
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("email must contain @")
        parts = v.split("@")
        if len(parts) != 2:
            raise ValueError("invalid email format")
        local, domain = parts
        if not local:
            raise ValueError("email must have local part before @")
        if not domain:
            raise ValueError("email must have domain after @")
        if "." not in domain:
            raise ValueError("email domain must contain a dot")
        tld = domain.rsplit(".", 1)[-1]
        if len(tld) < 2:
            raise ValueError("email TLD must be at least 2 characters")
        if len(v) > 254:
            raise ValueError("email too long")
        allowed = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
        if not allowed.match(v):
            raise ValueError("invalid email format")
        return v


class ForgotPasswordResponse(BaseModel):
    code: int = 0
    message: str = "If the email is registered, a reset link has been sent"
    data: Optional[dict] = None


class PasswordResetToken:
    def __init__(self, email: str, token: str, expires_at: datetime):
        self.email = email
        self.token = token
        self.expires_at = expires_at


class InMemoryTokenStore:
    def __init__(self):
        self._store: dict[str, PasswordResetToken] = {}
        self._lock = threading.Lock()

    def create_token(self, email: str) -> PasswordResetToken:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        reset_token = PasswordResetToken(email=email, token=token, expires_at=expires_at)
        with self._lock:
            self._store[email] = reset_token
        return reset_token

    def get_token(self, email: str) -> Optional[PasswordResetToken]:
        with self._lock:
            return self._store.get(email)

    def consume_token(self, email: str) -> Optional[PasswordResetToken]:
        with self._lock:
            return self._store.pop(email, None)

    def get_token_by_value(self, token: str) -> Optional[PasswordResetToken]:
        with self._lock:
            for t in self._store.values():
                if t.token == token:
                    return t
        return None


class RateLimiter:
    def __init__(self, cooldown_seconds: int = 60):
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()
        self.cooldown_seconds = cooldown_seconds

    def is_allowed(self, email: str) -> bool:
        with self._lock:
            last = self._last_request.get(email)
            if last is None:
                self._last_request[email] = time.time()
                return True
            elapsed = time.time() - last
            if elapsed >= self.cooldown_seconds:
                self._last_request[email] = time.time()
                return True
            return False

    def reset(self, email: str):
        with self._lock:
            self._last_request.pop(email, None)


token_store = InMemoryTokenStore()
rate_limiter = RateLimiter(cooldown_seconds=60)


send_reset_email_state = {"fail": False}


async def send_reset_email(email: str, token: str) -> bool:
    if send_reset_email_state["fail"]:
        return False
    return True


@app.post(FORGOT_PASSWORD_URL, status_code=status.HTTP_200_OK)
async def forgot_password(request: ForgotPasswordRequest):
    email = request.email.strip().lower()

    if not rate_limiter.is_allowed(email):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )

    token_obj = token_store.create_token(email)
    sent = await send_reset_email(email, token_obj.token)
    if not sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send reset email. Please try again later.",
        )

    return ForgotPasswordResponse(
        code=0,
        message="If the email is registered, a reset link has been sent",
        data={"email": email},
    )


@pytest.fixture(autouse=True)
def reset_state():
    token_store._store.clear()
    rate_limiter._last_request.clear()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
    ) as ac:
        yield ac


def _valid_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@example.com"


@pytest.mark.asyncio
async def test_forgot_password_returns_200(client: AsyncClient):
    payload = {"email": _valid_email()}
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}"


@pytest.mark.asyncio
async def test_forgot_password_response_time_under_500ms(client: AsyncClient):
    payload = {"email": _valid_email()}
    start = time.perf_counter()
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert resp.status_code == 200, f"Expected HTTP 200, got {resp.status_code}"
    assert elapsed_ms <= 500, f"Response time {elapsed_ms:.1f}ms exceeds 500ms limit"


@pytest.mark.asyncio
async def test_forgot_password_creates_token(client: AsyncClient):
    email = _valid_email()
    payload = {"email": email}
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp.status_code == 200

    stored = token_store.get_token(email.lower())
    assert stored is not None, "Token was not stored"
    assert stored.email == email.lower()
    assert len(stored.token) > 0
    assert stored.expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_forgot_password_token_uses_urlsafe_base64(client: AsyncClient):
    email = _valid_email()
    payload = {"email": email}
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp.status_code == 200

    stored = token_store.get_token(email.lower())
    assert stored is not None
    assert re.match(r"^[A-Za-z0-9\-_]+$", stored.token), f"Token contains invalid characters: {stored.token}"
    assert len(stored.token) == 43, f"Expected token length 43, got {len(stored.token)}"


@pytest.mark.asyncio
async def test_forgot_password_token_expires_in_24h(client: AsyncClient):
    email = _valid_email()
    payload = {"email": email}
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp.status_code == 200

    stored = token_store.get_token(email.lower())
    assert stored is not None
    max_expiry = datetime.now(timezone.utc) + timedelta(hours=24, minutes=1)
    assert stored.expires_at <= max_expiry, f"Token expiry {stored.expires_at} exceeds 24h limit"
    assert stored.expires_at > datetime.now(timezone.utc), "Token already expired"


@pytest.mark.asyncio
async def test_forgot_password_response_contains_email(client: AsyncClient):
    email = _valid_email()
    payload = {"email": email}
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp.status_code == 200

    body = resp.json()
    assert "data" in body
    assert body["data"]["email"] == email.lower()


@pytest.mark.asyncio
async def test_forgot_password_same_email_multiple_tokens(client: AsyncClient):
    email = _valid_email()
    payload = {"email": email}

    resp1 = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp1.status_code == 200
    token1 = token_store.get_token(email.lower())
    assert token1 is not None

    rate_limiter.reset(email.lower())

    resp2 = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp2.status_code == 200
    token2 = token_store.get_token(email.lower())
    assert token2 is not None
    assert token2.token != token1.token, "Second request should generate a different token"


@pytest.mark.asyncio
async def test_case_insensitive_email(client: AsyncClient):
    email = f"User_{uuid.uuid4().hex[:8]}@Example.COM"
    payload = {"email": email}
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp.status_code == 200, f"Expected 200 for case-variant email, got {resp.status_code}"

    stored = token_store.get_token(email.lower())
    assert stored is not None, "Token should be stored under lowercased email"
    assert stored.email == email.lower()


@pytest.mark.asyncio
async def test_email_send_failure_returns_500(client: AsyncClient):
    import sys
    mod = sys.modules[__name__]
    original = mod.send_reset_email_state["fail"]
    mod.send_reset_email_state["fail"] = True
    try:
        payload = {"email": _valid_email()}
        resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
        assert resp.status_code == 500, f"Expected 500 on email failure, got {resp.status_code}"
    finally:
        mod.send_reset_email_state["fail"] = original


@pytest.mark.asyncio
async def test_rate_limit_blocks_second_request(client: AsyncClient):
    email = _valid_email()
    payload = {"email": email}

    resp1 = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp1.status_code == 200

    resp2 = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp2.status_code == 429, f"Expected 429 for rate-limited request, got {resp2.status_code}"


@pytest.mark.asyncio
async def test_rate_limit_recovers_after_cooldown(client: AsyncClient):
    email = _valid_email()
    payload = {"email": email}

    resp1 = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp1.status_code == 200

    resp2 = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp2.status_code == 429

    rate_limiter.reset(email.lower())

    resp3 = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp3.status_code == 200, f"Expected 200 after rate limit reset, got {resp3.status_code}"


@pytest.mark.asyncio
async def test_empty_email_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_no_at_symbol_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "notanemail"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_plain_at_symbol_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "@"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_at_with_no_local_part_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "@domain.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_at_with_no_domain_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "user@"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_email_without_dot_in_domain_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "user@domain"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_very_long_email_returns_422(client: AsyncClient):
    local = "a" * 250
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": f"{local}@b.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unicode_email_is_rejected_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "üser@exämple.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_whitespace_only_email_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_email_with_spaces_inside_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "user @ example.com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_email_with_plus_tag_is_accepted(client: AsyncClient):
    payload = {"email": f"user+tag_{uuid.uuid4().hex[:8]}@example.com"}
    resp = await client.post(FORGOT_PASSWORD_URL, json=payload)
    assert resp.status_code == 200, f"Expected 200 for plus-tag email, got {resp.status_code}"


@pytest.mark.asyncio
async def test_short_tld_is_rejected_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": "user@domain.c"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_non_string_email_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": 12345})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_json_body_returns_422(client: AsyncClient):
    resp = await client.post(FORGOT_PASSWORD_URL, content=b"not json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_max_valid_email_length_returns_200(client: AsyncClient):
    local_max = 254 - len("@b.co")
    local_part = "a" * local_max
    email = f"{local_part}@b.co"
    assert len(email) == 254
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": email})
    assert resp.status_code == 200, f"Expected 200 for 254-char email, got {resp.status_code}"


@pytest.mark.asyncio
async def test_email_one_char_over_max_returns_422(client: AsyncClient):
    local_max = 254 - len("@b.co")
    local_part = "a" * (local_max + 1)
    email = f"{local_part}@b.co"
    assert len(email) == 255
    resp = await client.post(FORGOT_PASSWORD_URL, json={"email": email})
    assert resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
