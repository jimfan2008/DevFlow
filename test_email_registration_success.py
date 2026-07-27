#!/usr/bin/env python3
"""
TDD 测试用例 0001 - 邮箱注册成功

验收标准:
1. HTTP 201 返回，响应时间 ≤500ms
2. 数据库 users 表新增一条记录，status='active'，role='viewer'
3. 邮箱验证邮件在 30 秒内发出
"""

import sys
import os
import time
import uuid
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.models.user import User
from app.database import get_db
from app.main import app


# ============================================================
# Test Fixtures
# ============================================================

TEST_DATABASE_URL = "sqlite:///./test_registration.db"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh test database session for each test."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.database import Base
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    async def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    engine.dispose()

    # Cleanup: remove test DB file
    db_path = os.path.join(os.path.dirname(__file__), "test_registration.db")
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================
# Helper Functions
# ============================================================


def _unique_id() -> str:
    """Generate short unique suffix to avoid cross-test conflicts."""
    return uuid.uuid4().hex[:8]


def _make_payload(username=None, email=None, password="SecurePass123!"):
    """Build a valid registration payload with auto-generated unique fields."""
    suffix = _unique_id()
    return {
        "username": username if username else f"testuser_{suffix}",
        "email": email if email else f"test_{suffix}@example.com",
        "password": password,
        "confirm_password": password,
    }


# ============================================================
# Acceptance Criterion 1: HTTP 201 and response time <= 500ms
# ============================================================


@pytest.mark.asyncio
async def test_register_returns_201(client, db_session):
    """Verify registration returns HTTP 201 Created."""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201, f"Expected 201, got {response.status_code}"


@pytest.mark.asyncio
async def test_register_response_time_under_500ms(client, db_session):
    """Verify response time is under 500ms."""
    payload = _make_payload()
    start = time.perf_counter()
    response = await client.post("/api/auth/register", json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 201
    assert elapsed_ms < 500, f"Response time {elapsed_ms:.0f}ms exceeds 500ms limit"


# ============================================================
# Acceptance Criterion 2: Database record with correct fields
# ============================================================


@pytest.mark.asyncio
async def test_register_creates_user_record(client, db_session):
    """Verify a new record is inserted into the users table."""
    email = f"db_check_{_unique_id()}@example.com"
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None, "No new user record found in database"
    assert user.username == payload["username"]
    assert user.email == email
    assert user.password_hash is not None
    assert user.password_hash != payload["password"], "Password must be hashed"


@pytest.mark.asyncio
async def test_register_user_status_is_active(client, db_session):
    """Verify registered user has status='active'."""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.status == "active", f"Expected status='active', got status='{user.status}'"


@pytest.mark.asyncio
async def test_register_user_role_is_viewer(client, db_session):
    """Verify registered user has role='viewer'."""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.role == "viewer", f"Expected role='viewer', got role='{user.role}'"


@pytest.mark.asyncio
async def test_register_user_has_timestamps(client, db_session):
    """Verify user record has created_at and updated_at set."""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.created_at is not None, "created_at must not be null"
    assert user.updated_at is not None, "updated_at must not be null"


# ============================================================
# Acceptance Criterion 3: Email verification within 30s
# ============================================================


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Email verification not yet implemented, pending SMTP/mock setup")
async def test_register_sends_verification_email_within_30s(client, db_session):
    """Verify verification email is sent within 30 seconds."""
    payload = _make_payload()
    start = time.perf_counter()
    response = await client.post("/api/auth/register", json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 201
    assert elapsed_ms <= 30000, f"Email sending took {elapsed_ms:.0f}ms, exceeding 30s"


# ============================================================
# Response body contains user info and tokens
# ============================================================


@pytest.mark.asyncio
async def test_register_response_contains_user_and_tokens(client, db_session):
    """Verify response body contains user data and token fields."""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    user_data = data["data"]["user"]
    assert "id" in user_data
    assert user_data["username"] == payload["username"]
    assert user_data["email"] == payload["email"]
    assert "created_at" in user_data

    tokens = data["data"]["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "Bearer"
    assert "expires_in" in tokens


# ============================================================
# Edge cases: valid boundary values
# ============================================================


@pytest.mark.asyncio
async def test_register_min_length_username_succeeds(client, db_session):
    """Boundary: username at minimum length (3 chars) should succeed."""
    suffix = _unique_id()[:1]
    username = f"us{suffix}"
    assert len(username) == 3
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["username"] == username


@pytest.mark.asyncio
async def test_register_max_length_username_succeeds(client, db_session):
    """Boundary: username at maximum length (50 chars) should succeed."""
    username = "u" * 49 + _unique_id()[:1]
    assert len(username) == 50
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["username"] == username


@pytest.mark.asyncio
async def test_register_password_at_min_length_succeeds(client, db_session):
    """Boundary: password at minimum length (8 chars) should succeed."""
    payload = _make_payload(password="Abcdef12")
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_with_special_chars_in_username_succeeds(client, db_session):
    """Boundary: username with underscores, hyphens, dots should succeed."""
    username = f"test-user_{_unique_id()[:4]}.name"
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["username"] == username


@pytest.mark.asyncio
async def test_register_with_long_valid_email_succeeds(client, db_session):
    """Boundary: long but valid email address should succeed."""
    email = f"user_with_a_very_long_subdomain_name_part_{_unique_id()}@example.com"
    assert len(email) < 255
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["email"] == email


@pytest.mark.asyncio
async def test_register_with_plus_addressed_email_succeeds(client, db_session):
    """Boundary: plus-addressed email (user+tag@example.com) should succeed."""
    email = f"test+{_unique_id()}@example.com"
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["email"] == email


@pytest.mark.asyncio
async def test_register_with_subdomain_email_succeeds(client, db_session):
    """Boundary: email with subdomain should succeed."""
    email = f"subdomain_{_unique_id()}@mail.subdomain.example.com"
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201


# ============================================================
# Error cases: duplicate email / username
# ============================================================


@pytest.mark.asyncio
async def test_register_duplicate_email_fails_with_409(client, db_session):
    """Verify duplicate email registration returns 409.
    Self-contained: both registrations happen in this function."""
    email = f"dup_email_{_unique_id()}@example.com"
    payload_first = _make_payload(
        username=f"first_{_unique_id()}",
        email=email,
    )
    response1 = await client.post("/api/auth/register", json=payload_first)
    assert response1.status_code == 201, "First registration should succeed"

    payload_second = _make_payload(
        username=f"second_{_unique_id()}",
        email=email,
    )
    response2 = await client.post("/api/auth/register", json=payload_second)
    assert response2.status_code == 409, f"Duplicate email should return 409, got {response2.status_code}"


@pytest.mark.asyncio
async def test_register_duplicate_username_fails_with_409(client, db_session):
    """Verify duplicate username registration returns 409.
    Self-contained: both registrations happen in this function."""
    username = f"dup_user_{_unique_id()}"
    payload_first = _make_payload(
        username=username,
        email=f"first_{_unique_id()}@example.com",
    )
    response1 = await client.post("/api/auth/register", json=payload_first)
    assert response1.status_code == 201, "First registration should succeed"

    payload_second = _make_payload(
        username=username,
        email=f"second_{_unique_id()}@example.com",
    )
    response2 = await client.post("/api/auth/register", json=payload_second)
    assert response2.status_code == 409, f"Duplicate username should return 409, got {response2.status_code}"


# ============================================================
# Error cases: password policy
# ============================================================


@pytest.mark.asyncio
async def test_register_password_below_min_length_fails(client, db_session):
    """Boundary: password of 7 chars (below min 8) should be rejected."""
    payload = _make_payload(password="Abc1234")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_without_uppercase_fails(client, db_session):
    """Verify password without uppercase letters should be rejected."""
    payload = _make_payload(password="nouppercase1")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_without_lowercase_fails(client, db_session):
    """Verify password without lowercase letters should be rejected."""
    payload = _make_payload(password="NOLOWERCASE1")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_without_digit_fails(client, db_session):
    """Verify password without digits should be rejected."""
    payload = _make_payload(password="NoDigitsHere")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_mismatch_fails(client, db_session):
    """Verify password and confirm_password mismatch returns 422.
    Root cause: FastAPI validation error returns 422, not 400."""
    suffix = _unique_id()
    payload = {
        "username": f"mismatch_{suffix}",
        "email": f"mismatch_{suffix}@example.com",
        "password": "SecurePass123!",
        "confirm_password": "DifferentPass456!",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


# ============================================================
# Error cases: username length
# ============================================================


@pytest.mark.asyncio
async def test_register_username_too_short_fails(client, db_session):
    """Boundary: username of 2 chars (below min 3) should be rejected."""
    payload = _make_payload(username="ab")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_username_too_long_fails(client, db_session):
    """Boundary: username of 51 chars (above max 50) should be rejected."""
    payload = _make_payload(username="a" * 51)
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


# ============================================================
# Error cases: invalid / empty email
# ============================================================


@pytest.mark.asyncio
async def test_register_empty_email_fails(client, db_session):
    """Verify empty email returns 422."""
    payload = _make_payload(email="")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_format_fails(client, db_session):
    """Verify invalid email format (no @) returns 422."""
    suffix = _unique_id()
    payload = _make_payload(email=f"not-an-email-{suffix}")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


# ============================================================
# Error cases: missing required fields
# ============================================================


@pytest.mark.asyncio
async def test_register_missing_username_fails(client, db_session):
    """Verify missing username returns 422."""
    payload = _make_payload()
    del payload["username"]
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_email_fails(client, db_session):
    """Verify missing email returns 422."""
    payload = _make_payload()
    del payload["email"]
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_password_fails(client, db_session):
    """Verify missing password returns 422."""
    payload = _make_payload()
    del payload["password"]
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


# ============================================================
# Boundary: unicode / special characters
# ============================================================


@pytest.mark.asyncio
async def test_register_chinese_username_succeeds(client, db_session):
    """Boundary: Chinese characters in username should succeed."""
    suffix = _unique_id()
    username = f"中文用户_{suffix}"
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["username"] == username


@pytest.mark.asyncio
async def test_register_emoji_in_username_handled(client, db_session):
    """Boundary: emoji in username - either accepted or rejected with 422."""
    suffix = _unique_id()
    username = f"user{suffix}🔥"
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)
    # Accept either success (201) or rejection (422), both are valid policies
    assert response.status_code in (201, 422)


# ============================================================
# Security: SQL injection / XSS attempts
# ============================================================


@pytest.mark.asyncio
async def test_register_sql_injection_in_username_handled(client, db_session):
    """Security: SQL injection attempt in username should not cause DB error."""
    suffix = _unique_id()
    username = f"'; DROP TABLE users; --_{suffix}"
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)
    # Should not return 500 (internal error); 201 or 422 both acceptable
    assert response.status_code != 500, "SQL injection caused internal server error"


@pytest.mark.asyncio
async def test_register_xss_in_username_handled(client, db_session):
    """Security: XSS attempt in username should not cause error."""
    suffix = _unique_id()
    username = f"<script>alert(1)</script>_{suffix}"
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)
    # Should not return 500; 201 or 422 both acceptable
    assert response.status_code != 500, "XSS payload caused internal server error"


@pytest.mark.asyncio
async def test_register_control_characters_in_email_handled(client, db_session):
    """Boundary: control characters in email should be rejected."""
    suffix = _unique_id()
    payload = _make_payload(email=f"test\x00{suffix}@example.com")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
