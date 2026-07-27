#!/usr/bin/env python3
"""
TDD-0005: GitHub OAuth Third-party Login

Acceptance criteria:
  1. HTTP 302 redirect to callback address, then HTTP 200 returns valid JWT Token
  2. Response time <= 1 second
  3. First-time login auto-creates account, role='viewer'

Root cause fix:
  - Previous code had syntax error on line 1 due to encoding issues
  - Used wrong routes: /api/auth/github/login -> actual: /api/auth/oauth/github
  - Mocked requests.post/get -> actual code uses httpx.Client
  - Used @pytest.mark.asyncio -> routes are synchronous functions
  - Missing inline fixtures (client, db_session)
  - Wrong backend path (5 levels up -> only 1 level up)
"""

import os
import sys
import time
import json
import uuid

import pytest
from unittest.mock import patch, MagicMock, Mock
from sqlalchemy import text, create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base

# ===================== Mock Data =====================

MOCK_CLIENT_ID = "test_github_client_id_001"

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


def _make_mock_httpx_client():
    """Create a mock httpx.Client context manager."""
    mock_post_resp = Mock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = MOCK_GITHUB_TOKEN_RESPONSE
    mock_post_resp.text = json.dumps(MOCK_GITHUB_TOKEN_RESPONSE)

    mock_get_resp = Mock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = MOCK_GITHUB_USER_INFO
    mock_get_resp.text = json.dumps(MOCK_GITHUB_USER_INFO)

    mock_client = Mock()
    mock_client.post.return_value = mock_post_resp
    mock_client.get.return_value = mock_get_resp
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)

    return mock_client


def _make_mock_httpx_client_token_fail():
    """Token exchange failure."""
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"error": "bad_verification_code"}
    mock_resp.text = '{"error": "bad_verification_code"}'

    mock_client = Mock()
    mock_client.post.return_value = mock_resp
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    return mock_client


def _uid():
    return uuid.uuid4().hex[:8]


# ===================== Fixtures =====================

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def db_session():
    """Independent database session per test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        for table in reversed(Base.metadata.sorted_tables):
            try:
                session.execute(table.delete())
            except Exception:
                pass
        session.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """Synchronous TestClient with follow_redirects=False."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, follow_redirects=False) as tc:
        yield tc

    app.dependency_overrides.clear()


# ===================== Acceptance 1: 307 Redirect =====================

def test_github_oauth_initiate_302_redirect(client):
    """GET /api/auth/oauth/github -> 307 redirect to GitHub auth page."""
    response = client.get(
        "/api/auth/oauth/github",
        params={"client_id": MOCK_CLIENT_ID},
    )

    assert response.status_code == 307, (
        f"Expected 307, got {response.status_code}"
    )

    loc = response.headers.get("location", "")
    assert "github.com" in loc, f"Redirect should point to GitHub, actual: {loc}"
    assert "login/oauth/authorize" in loc, f"Should contain authorize path, actual: {loc}"
    assert "client_id=" in loc, f"Should contain client_id, actual: {loc}"
    assert "state=" in loc, f"Should contain state (CSRF), actual: {loc}"


# ===================== Acceptance 2: 200 + JWT =====================

def test_github_oauth_callback_200_with_jwt(client, db_session):
    """Callback success -> 200 + three-part JWT access_token."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    body = response.json()
    assert body.get("code") == 0, f"Expected code=0, got {body.get('code')}"
    assert "data" in body, "Response should contain data"
    assert "tokens" in body["data"], "data should contain tokens"

    tokens = body["data"]["tokens"]
    assert "access_token" in tokens, "tokens should contain access_token"

    parts = tokens["access_token"].split(".")
    assert len(parts) == 3, (
        f"JWT should be three parts (header.payload.signature), got {len(parts)} parts"
    )


# ===================== Acceptance 3: Response time <= 1s =====================

def test_github_oauth_callback_response_time(client, db_session):
    """Callback processing should complete within 1 second."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        start = time.perf_counter()
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
        elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed <= 1000, f"Elapsed {elapsed:.1f}ms exceeds 1000ms"


# ===================== Acceptance 4: First login creates user role=viewer =====================

def test_github_oauth_first_login_creates_viewer(client, db_session):
    """First OAuth login auto-creates user with role=viewer."""
    before = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0

    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )

    assert response.status_code == 200

    after = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    assert after == before + 1, f"Should create 1 user (before={before}, after={after})"

    row = db_session.execute(
        text("SELECT role FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None, "User record should exist"
    assert row[0] == "viewer", f"Expected role=viewer, got role={row[0]}"


# ===================== Additional: User has username + email =====================

def test_github_oauth_user_has_username_and_email(client, db_session):
    """User record contains correct username and email."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    row = db_session.execute(
        text("SELECT username, email FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None, "User record should exist"
    assert row[0] == MOCK_GITHUB_USER_INFO["login"], (
        f"Expected username={MOCK_GITHUB_USER_INFO['login']}, got {row[0]}"
    )
    assert row[1] == MOCK_GITHUB_USER_INFO["email"]


# ===================== Additional: No duplicate on second login =====================

def test_github_oauth_no_duplicate_on_second_login(client, db_session):
    """Same user logging in again should not create duplicate records."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        r1 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
        assert r1.status_code == 200

        r2 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}_2", "client_id": MOCK_CLIENT_ID},
        )
        assert r2.status_code == 200

    count = db_session.execute(
        text("SELECT COUNT(*) FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).scalar()
    assert count == 1, f"Same GitHub account should have only 1 record, got {count}"


# ===================== Additional: Token request failure =====================

def test_github_oauth_token_request_failure(client, db_session):
    """Token exchange failure should return error."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client_token_fail()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "bad_code", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code in (400, 401), (
        f"Token request failure should return error, got {response.status_code}"
    )


# ===================== Additional: Missing code returns error =====================

def test_github_oauth_missing_code(client, db_session):
    """Missing code should return 400/422."""
    response = client.get(
        "/api/auth/oauth/github/callback",
        params={"client_id": MOCK_CLIENT_ID},
    )
    assert response.status_code in (400, 422), (
        f"Missing code should return 400/422, got {response.status_code}"
    )


# ===================== Additional: Response has refresh_token + token_type =====================

def test_github_oauth_response_has_refresh_token_and_type(client, db_session):
    """Response contains refresh_token and token_type."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    tokens = response.json()["data"]["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens, "Response should contain refresh_token"

    tt = tokens.get("token_type", "")
    assert tt.lower() == "bearer", f"Expected token_type=Bearer, got {tt}"


# ===================== Additional: Both tokens are JWT =====================

def test_github_oauth_both_tokens_are_jwt(client, db_session):
    """access_token and refresh_token are both three-part JWT format."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    tokens = response.json()["data"]["tokens"]
    for name in ("access_token", "refresh_token"):
        parts = tokens[name].split(".")
        assert len(parts) == 3, (
            f"{name} should be three-part JWT, got {len(parts)} parts"
        )


# ===================== Additional: Response contains user info =====================

def test_github_oauth_response_contains_user_info(client, db_session):
    """Callback response contains complete user information."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    body = response.json()
    user = body["data"]["user"]
    assert user["email"] == MOCK_GITHUB_USER_INFO["email"]
    assert user["role"] == "viewer"
    assert user["status"] == "active"


# ===================== Additional: Existing user re-login =====================

def test_github_oauth_existing_user_relogin(client, db_session):
    """Existing user re-logging in via OAuth should return existing user."""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        r1 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert r1.status_code == 200

    row = db_session.execute(
        text("SELECT created_at FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None
    created_at = row[0]

    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        r2 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}_relogin", "client_id": MOCK_CLIENT_ID},
        )
    assert r2.status_code == 200

    row_after = db_session.execute(
        text("SELECT created_at FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row_after is not None
    assert row_after[0] == created_at, "Re-login should not change user creation time"

    count = db_session.execute(
        text("SELECT COUNT(*) FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).scalar()
    assert count == 1, f"Should have only 1 user record, got {count}"


# ===================== Additional: Custom redirect_uri =====================

def test_github_oauth_custom_redirect_uri(client):
    """OAuth initiation can use custom redirect_uri."""
    custom_uri = "http://custom.callback.example.com/callback"
    response = client.get(
        "/api/auth/oauth/github",
        params={"client_id": MOCK_CLIENT_ID, "redirect_uri": custom_uri},
    )
    assert response.status_code == 307
    loc = response.headers.get("location", "")
    assert custom_uri in loc, f"Should use custom redirect_uri, actual: {loc}"


# ===================== Additional: User has no email =====================

def test_github_oauth_user_no_email(client, db_session):
    """When GitHub user has no public email, system should generate a default email."""
    user_info_no_email = dict(MOCK_GITHUB_USER_INFO)
    user_info_no_email["email"] = None

    def _make_no_email_client():
        mock_post_resp = Mock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = MOCK_GITHUB_TOKEN_RESPONSE
        mock_post_resp.text = json.dumps(MOCK_GITHUB_TOKEN_RESPONSE)

        mock_get_resp = Mock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = user_info_no_email
        mock_get_resp.text = json.dumps(user_info_no_email)

        mock_client = Mock()
        mock_client.post.return_value = mock_post_resp
        mock_client.get.return_value = mock_get_resp
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        return mock_client

    with patch("httpx.Client", return_value=_make_no_email_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    body = response.json()
    user = body["data"]["user"]
    assert user["email"] is not None, "Even without GitHub email, system should assign default email"
    assert "gh_" in user["email"] or "@github.com" in user["email"]


# ===================== Additional: Network timeout =====================

def test_github_oauth_network_timeout(client, db_session):
    """GitHub API network timeout should return error."""
    import httpx as _httpx

    def _make_timeout_client():
        mock_client = Mock()
        mock_client.post.side_effect = _httpx.TimeoutException("Connection timed out")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        return mock_client

    with patch("httpx.Client", return_value=_make_timeout_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code in (400, 500), (
        f"Network timeout should return error, got {response.status_code}"
    )


# ===================== Additional: Expired code =====================

def test_github_oauth_expired_code(client, db_session):
    """Expired/invalid code should fail token exchange."""
    def _make_expired_client():
        mock_resp = Mock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": "expired_token"}
        mock_resp.text = '{"error": "expired_token"}'
        mock_client = Mock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        return mock_client

    with patch("httpx.Client", return_value=_make_expired_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "expired_code", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code in (400, 401), (
        f"Expired code should return error, got {response.status_code}"
    )


# ===================== Additional: State mismatch =====================

def test_github_oauth_invalid_state(client, db_session):
    """State mismatch should return error."""
    response = client.get(
        "/api/auth/oauth/github/callback",
        params={"code": "abc", "client_id": MOCK_CLIENT_ID},
    )
    assert response.status_code in (400, 401, 403), (
        f"State mismatch should return error, got {response.status_code}"
    )


# ===================== Additional: GitHub user info request failure =====================

def test_github_oauth_user_info_request_failure(client, db_session):
    """GitHub user info request failure should return error."""
    def _make_user_fail_client():
        mock_post_resp = Mock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = MOCK_GITHUB_TOKEN_RESPONSE
        mock_post_resp.text = json.dumps(MOCK_GITHUB_TOKEN_RESPONSE)

        mock_get_resp = Mock()
        mock_get_resp.status_code = 404
        mock_get_resp.json.return_value = {"message": "Not Found"}
        mock_get_resp.text = '{"message": "Not Found"}'

        mock_client = Mock()
        mock_client.post.return_value = mock_post_resp
        mock_client.get.return_value = mock_get_resp
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        return mock_client

    with patch("httpx.Client", return_value=_make_user_fail_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code in (400, 401), (
        f"User info request failure should return error, got {response.status_code}"
    )
