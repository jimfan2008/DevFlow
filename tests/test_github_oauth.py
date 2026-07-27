#!/usr/bin/env python3
"""
TDD-0005: GitHub OAuth Third-party Login

Acceptance Criteria:
  1. HTTP 302 redirect to GitHub OAuth authorization page
  2. Callback returns HTTP 200 with valid JWT Token
  3. Response time <= 1 second
  4. First login auto-creates account with role='viewer'
"""

import os
import sys
import time
import json
import uuid

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

_BACKEND_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", "backend"
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ===================== Mock Data =====================

MOCK_GITHUB_USER_INFO = {
    "id": 998877,
    "login": "tdd_github_user",
    "email": "tdd_github_user@example.com",
    "name": "TDD GitHub User",
    "avatar_url": "https://github.com/avatars/tdd_github_user.png",
}

MOCK_GITHUB_TOKEN_RESPONSE = {
    "access_token": "gho_abcdef1234567890abcdef1234567890abcdef12",
    "token_type": "bearer",
    "scope": "user:email",
}

MOCK_STATE = uuid.uuid4().hex


def _mock_github_token_resp(*args, **kwargs):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = MOCK_GITHUB_TOKEN_RESPONSE
    r.text = json.dumps(MOCK_GITHUB_TOKEN_RESPONSE)
    return r


def _mock_github_user_resp(*args, **kwargs):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = MOCK_GITHUB_USER_INFO
    r.text = json.dumps(MOCK_GITHUB_USER_INFO)
    return r


def _mock_github_token_fail(*args, **kwargs):
    r = MagicMock()
    r.status_code = 401
    r.json.return_value = {"error": "bad_verification_code"}
    r.text = '{"error": "bad_verification_code"}'
    return r


def _uid():
    return uuid.uuid4().hex[:8]


# ===================== Acceptance 1: 302 Redirect =====================

@pytest.mark.asyncio
async def test_github_oauth_initiate_302_redirect(client, db_session):
    """GET /api/auth/github/login -> 302 to GitHub authorization page"""
    response = await client.get("/api/auth/github/login", follow_redirects=False)

    assert response.status_code == 302, (
        f"Expected 302, got {response.status_code}"
    )

    loc = response.headers.get("location", "")
    assert "github.com" in loc, f"Redirect should point to GitHub, got: {loc}"
    assert "login/oauth/authorize" in loc, f"Should contain authorize path, got: {loc}"
    assert "client_id=" in loc, f"Should contain client_id, got: {loc}"
    assert "state=" in loc, f"Should contain state (CSRF), got: {loc}"


# ===================== Acceptance 2: 200 + JWT =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_200_with_jwt(client, db_session):
    """Callback success -> 200 + three-part JWT access_token"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    body = response.json()
    assert "access_token" in body, "Response should contain access_token"

    parts = body["access_token"].split(".")
    assert len(parts) == 3, (
        f"JWT should have 3 parts (header.payload.signature), got {len(parts)} parts"
    )


# ===================== Acceptance 3: Response time <= 1s =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_response_time(client, db_session):
    """Callback processing should complete within 1 second"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        start = time.perf_counter()
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )
        elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed <= 1000, f"Elapsed {elapsed:.1f}ms exceeds 1000ms"


# ===================== Acceptance 4: First login creates user role=viewer =====================

@pytest.mark.asyncio
async def test_github_oauth_first_login_creates_viewer(client, db_session):
    """First OAuth login auto-creates user with role viewer"""
    before = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )

    assert response.status_code == 200

    after = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    assert after == before + 1, f"Should create 1 new user (before={before}, after={after})"

    role = db_session.execute(
        text("SELECT role FROM users ORDER BY created_at DESC LIMIT 1")
    ).scalar()
    assert role == "viewer", f"Expected role=viewer, got role={role}"


# ===================== Additional: User record has github_id =====================

@pytest.mark.asyncio
async def test_github_oauth_user_has_github_id(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )
    assert response.status_code == 200

    row = db_session.execute(
        text("SELECT github_id FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None, "User record should exist"
    assert row[0] == MOCK_GITHUB_USER_INFO["id"], (
        f"Expected github_id={MOCK_GITHUB_USER_INFO['id']}, got {row[0]}"
    )


# ===================== Additional: User record has username + email =====================

@pytest.mark.asyncio
async def test_github_oauth_user_has_username_and_email(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )
    assert response.status_code == 200

    row = db_session.execute(
        text("SELECT username, email FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None
    assert row[0] == MOCK_GITHUB_USER_INFO["login"], (
        f"Expected username={MOCK_GITHUB_USER_INFO['login']}, got {row[0]}"
    )
    assert row[1] == MOCK_GITHUB_USER_INFO["email"]


# ===================== Additional: No duplicate on second login =====================

@pytest.mark.asyncio
async def test_github_oauth_no_duplicate_on_second_login(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        r1 = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )
        assert r1.status_code == 200

        r2 = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}_2", "state": uuid.uuid4().hex},
        )
        assert r2.status_code == 200

    count = db_session.execute(
        text("SELECT COUNT(*) FROM users WHERE github_id = :gid"),
        {"gid": MOCK_GITHUB_USER_INFO["id"]},
    ).scalar()
    assert count == 1, f"Same GitHub account should have only 1 record, got {count}"


# ===================== Additional: Invalid state returns error =====================

@pytest.mark.asyncio
async def test_github_oauth_invalid_state(client, db_session):
    response = await client.get(
        "/api/auth/github/callback",
        params={"code": "abc", "state": "wrong_state"},
    )
    assert response.status_code in (400, 401, 403), (
        f"Invalid state should return error, got {response.status_code}"
    )


# ===================== Additional: Missing code returns error =====================

@pytest.mark.asyncio
async def test_github_oauth_missing_code(client, db_session):
    response = await client.get(
        "/api/auth/github/callback",
        params={"state": MOCK_STATE},
    )
    assert response.status_code in (400, 422), (
        f"Missing code should return 400/422, got {response.status_code}"
    )


# ===================== Additional: GitHub token request failure =====================

@pytest.mark.asyncio
async def test_github_oauth_token_request_failure(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_fail):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": "bad_code", "state": MOCK_STATE},
        )
    assert response.status_code in (400, 401, 502), (
        f"Token request failure should return error, got {response.status_code}"
    )


# ===================== Additional: Response has refresh_token + token_type =====================

@pytest.mark.asyncio
async def test_github_oauth_response_has_refresh_token_and_type(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )
    assert response.status_code == 200

    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body, "Response should contain refresh_token"

    tt = body.get("token_type", "")
    assert tt.lower() == "bearer", f"Expected token_type=Bearer, got {tt}"


# ===================== Additional: Both tokens are JWT =====================

@pytest.mark.asyncio
async def test_github_oauth_both_tokens_are_jwt(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": MOCK_STATE},
        )
    assert response.status_code == 200

    body = response.json()
    for name in ("access_token", "refresh_token"):
        parts = body[name].split(".")
        assert len(parts) == 3, (
            f"{name} should be 3-part JWT, got {len(parts)} parts"
        )
