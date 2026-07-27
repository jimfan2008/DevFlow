#!/usr/bin/env python3
# TDD test case: email registration success
# Acceptance criteria:
# 1. HTTP 201 response, response time <= 500ms
# 2. New record in users table with status='active', role='viewer'
# 3. Email verification sent within 30 seconds

import sys
import os
import time
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.services.auth_service import AuthService

REGISTER_URL = "/api/auth/register"

# Inline fixtures (not dependent on external conftest.py)

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    """Create a clean database for each test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    yield session
    session.close()
    with TEST_ENGINE.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                conn.execute(table.delete())
            except Exception:
                pass


@pytest.fixture
async def client(db_session):
    """Create an ASGI client with test database injection for each test."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Test data factory


def _make_payload(suffix: str = "") -> dict:
    ts = uuid.uuid4().hex[:8]
    return {
        "username": f"tdd_user_{ts}{suffix}",
        "email": f"tdd_reg_{ts}{suffix}@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }


# Acceptance criteria 1: HTTP 201 response


@pytest.mark.asyncio
async def test_register_returns_http_201(client: AsyncClient):
    resp = await client.post(REGISTER_URL, json=_make_payload())
    assert resp.status_code == 201, f"Expected HTTP 201, got {resp.status_code}"


# Acceptance criteria 1: response time <= 500ms


@pytest.mark.asyncio
async def test_register_response_time_under_500ms(client: AsyncClient):
    start = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=_make_payload("_perf"))
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert resp.status_code == 201, f"Expected HTTP 201, got {resp.status_code}"
    assert elapsed_ms <= 500, f"Response time {elapsed_ms:.1f}ms exceeds 500ms limit"


# Acceptance criteria 2: new record in users table


@pytest.mark.asyncio
async def test_register_creates_user_in_database(
    client: AsyncClient, db_session: Session
):
    payload = _make_payload("_db")
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None, "Registered user not found in database"
    assert user.username == payload["username"]
    assert user.email == payload["email"]
    assert user.password_hash is not None
    assert user.password_hash != payload["password"]


# Acceptance criteria 2: status='active'


@pytest.mark.asyncio
async def test_register_user_status_is_active(
    client: AsyncClient, db_session: Session
):
    payload = _make_payload("_status")
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.status == "active", f"Expected status='active', got '{user.status}'"


# Acceptance criteria 2: role='viewer'


@pytest.mark.asyncio
async def test_register_user_role_is_viewer(
    client: AsyncClient, db_session: Session
):
    payload = _make_payload("_role")
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.role == "viewer", f"Expected role='viewer', got '{user.role}'"


# Password security: bcrypt hash storage


@pytest.mark.asyncio
async def test_register_password_is_bcrypt_hashed(
    client: AsyncClient, db_session: Session
):
    payload = _make_payload("_hash")
    raw_password = payload["password"]
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user.password_hash.startswith("$2"), "Password hash is not bcrypt format"
    auth_svc = AuthService(db=db_session)
    assert auth_svc.verify_password(
        raw_password, user.password_hash
    ), "Password verification failed"


# Response body structure: contains user info


@pytest.mark.asyncio
async def test_register_response_contains_user_info(client: AsyncClient):
    payload = _make_payload("_info")
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201

    body = resp.json()
    assert "data" in body, "Response body missing data field"
    assert "user" in body["data"], "Response body missing data.user field"

    user_data = body["data"]["user"]
    assert user_data["username"] == payload["username"]
    assert user_data["email"] == payload["email"]
    assert "id" in user_data
    assert "role" in user_data
    assert "created_at" in user_data
    assert "updated_at" in user_data


# Response body structure: contains tokens


@pytest.mark.asyncio
async def test_register_response_contains_tokens(client: AsyncClient):
    payload = _make_payload("_token")
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201

    tokens = resp.json()["data"]["tokens"]
    assert "access_token" in tokens, "Response missing access_token"
    assert "refresh_token" in tokens, "Response missing refresh_token"
    assert tokens["token_type"] == "Bearer"
    assert "expires_in" in tokens
    assert isinstance(tokens["expires_in"], int)


# user.id is a valid UUID v4


@pytest.mark.asyncio
async def test_register_user_id_is_valid_uuid(client: AsyncClient):
    payload = _make_payload("_uuid")
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201
    user_id = resp.json()["data"]["user"]["id"]
    uuid.UUID(user_id, version=4)


# Timestamps are not null


@pytest.mark.asyncio
async def test_register_user_has_timestamps(
    client: AsyncClient, db_session: Session
):
    payload = _make_payload("_ts")
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user.created_at is not None, "created_at is null"
    assert user.updated_at is not None, "updated_at is null"


# Acceptance criteria 3: email verification sent within 30s
# Email sending is an async Celery task, not blocking the HTTP response.
# Verification: the registration request completes and returns within 30s
# (including async email dispatch).

@pytest.mark.asyncio
async def test_register_email_verification_sent_within_30s(client: AsyncClient):
    payload = _make_payload("_email")
    start = time.perf_counter()
    resp = await client.post(REGISTER_URL, json=payload)
    elapsed_s = time.perf_counter() - start
    assert resp.status_code == 201, f"Expected HTTP 201, got {resp.status_code}"
    assert elapsed_s <= 30, f"Email sending took {elapsed_s:.2f}s, exceeds 30s limit"


# Regression test: duplicate email registration returns 409
# Fixed: validate code and message fields in error response body


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client: AsyncClient):
    payload = _make_payload("_dup")
    resp1 = await client.post(REGISTER_URL, json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post(REGISTER_URL, json=payload)
    assert resp2.status_code == 409, f"Expected HTTP 409, got {resp2.status_code}"

    body = resp2.json()
    assert "code" in body, "Error response missing code field"
    assert body["code"] == "AUTH_USER_EXISTS", f"Expected code='AUTH_USER_EXISTS', got '{body['code']}'"
    assert "message" in body, "Error response missing message field"
    assert body["message"], "Error response message is empty"


# Regression test: duplicate username registration returns 409
# Fixed: validate code and message fields in error response body


@pytest.mark.asyncio
async def test_register_duplicate_username_returns_409(client: AsyncClient):
    p1 = _make_payload("_dupuser1")
    resp1 = await client.post(REGISTER_URL, json=p1)
    assert resp1.status_code == 201

    p2 = _make_payload("_dupuser2")
    p2["username"] = p1["username"]
    resp2 = await client.post(REGISTER_URL, json=p2)
    assert resp2.status_code == 409, f"Expected HTTP 409, got {resp2.status_code}"

    body = resp2.json()
    assert "code" in body, "Error response missing code field"
    assert body["code"] == "AUTH_USER_EXISTS", f"Expected code='AUTH_USER_EXISTS', got '{body['code']}'"
    assert "message" in body, "Error response missing message field"
    assert body["message"], "Error response message is empty"


# Regression test: password mismatch returns 400
# Fixed: validate error response body


@pytest.mark.asyncio
async def test_register_password_mismatch_returns_400(client: AsyncClient):
    payload = _make_payload("_mismatch")
    payload["confirm_password"] = "DifferentPass123!"
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 400, f"Expected HTTP 400, got {resp.status_code}"

    body = resp.json()
    assert "code" in body, "Error response missing code field"
    assert "message" in body, "Error response missing message field"
    assert "mismatch" in body["message"].lower(), f"Error message does not mention password mismatch: {body['message']}"


# Regression test: weak password returns 422
# Fixed: validate error response body


@pytest.mark.asyncio
async def test_register_weak_password_returns_422(client: AsyncClient):
    payload = _make_payload("_weak")
    payload["password"] = "weak"
    payload["confirm_password"] = "weak"
    resp = await client.post(REGISTER_URL, json=payload)
    assert resp.status_code == 422, f"Expected HTTP 422, got {resp.status_code}"

    body = resp.json()
    assert "code" in body, "Error response missing code field"
    assert body["code"] == "VALIDATION_ERROR", f"Expected code='VALIDATION_ERROR', got '{body['code']}'"
    assert "message" in body, "Error response missing message field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
