#!/usr/bin/env python3
"""
TDD-0005: GitHub OAuth 第三方登录

验收标准：
  1. HTTP 302 重定向至 GitHub OAuth 授权页
  2. 回调后 HTTP 200 返回有效 JWT Token
  3. 响应时间 <= 1 秒
  4. 首次登录自动创建账户，role = 'viewer'
"""

import os
import sys
import time
import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.main import app
from app.database import get_db, Base

# ===================== Mock 数据 =====================

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

MOCK_CLIENT_ID = "test_github_client_id_12345"


def _mock_httpx_post(*args, **kwargs):
    """Mock httpx.Client.post for GitHub token exchange."""
    r = MagicMock()
    r.status_code = 200
    r.text = json.dumps(MOCK_GITHUB_TOKEN_RESPONSE)
    r.json.return_value = MOCK_GITHUB_TOKEN_RESPONSE
    return r


def _mock_httpx_get(*args, **kwargs):
    """Mock httpx.Client.get for GitHub user info."""
    r = MagicMock()
    r.status_code = 200
    r.text = json.dumps(MOCK_GITHUB_USER_INFO)
    r.json.return_value = MOCK_GITHUB_USER_INFO
    return r


def _mock_httpx_post_fail(*args, **kwargs):
    """Mock httpx.Client.post failure for GitHub token exchange."""
    r = MagicMock()
    r.status_code = 401
    r.text = '{"error": "bad_verification_code"}'
    r.json.return_value = {"error": "bad_verification_code"}
    return r


def _uid():
    return uuid.uuid4().hex[:8]


# ===================== 数据库测试引擎 =====================

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)


def _teardown_db():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


# ===================== Fixtures =====================

@pytest_asyncio.fixture(scope="function")
async def db_session():
    _setup_db()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        _teardown_db()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=False,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ===================== 验收 1: 重定向至 GitHub OAuth 授权页 =====================

@pytest.mark.asyncio
async def test_github_oauth_initiate_redirect(client, db_session):
    """GET /api/auth/oauth/github -> 307 到 GitHub 授权页"""
    response = await client.get(
        "/api/auth/oauth/github",
        params={"client_id": MOCK_CLIENT_ID},
    )

    assert response.status_code in (302, 303, 307), (
        f"期望重定向状态码 302/303/307，实际 {response.status_code}"
    )

    loc = response.headers.get("location", "")
    assert "github.com" in loc, f"重定向应指向 GitHub，实际: {loc}"
    assert "login/oauth/authorize" in loc, f"应含 authorize 路径，实际: {loc}"
    assert MOCK_CLIENT_ID in loc, f"应含 client_id，实际: {loc}"
    assert "state=" in loc, f"应含 state (CSRF)，实际: {loc}"


# ===================== 验收 2: 200 + JWT =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_200_with_jwt(client, db_session):
    """回调成功 -> 200 + 三段 JWT access_token"""
    with patch("httpx.Client.post", side_effect=_mock_httpx_post), \
         patch("httpx.Client.get", side_effect=_mock_httpx_get):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )

    assert response.status_code == 200, f"期望 200，实际 {response.status_code}"

    body = response.json()
    assert body.get("code") == 0, f"期望 code=0，实际 {body.get('code')}"

    tokens = body.get("data", {}).get("tokens", {})
    assert "access_token" in tokens, "tokens 中应包含 access_token"

    parts = tokens["access_token"].split(".")
    assert len(parts) == 3, (
        f"JWT 应为三段 (header.payload.signature)，实际 {len(parts)} 段"
    )


# ===================== 验收 3: 响应时间 <= 1s =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_response_time(client, db_session):
    """回调处理应在 1 秒内完成"""
    with patch("httpx.Client.post", side_effect=_mock_httpx_post), \
         patch("httpx.Client.get", side_effect=_mock_httpx_get):
        start = time.perf_counter()
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
        elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed <= 1000, f"耗时 {elapsed:.1f}ms 超出 1000ms"


# ===================== 验收 4: 首次登录创建用户 role=viewer =====================

@pytest.mark.asyncio
async def test_github_oauth_first_login_creates_viewer(client, db_session):
    """首次 OAuth 登录自动创建用户，role 为 viewer"""
    before = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0

    with patch("httpx.Client.post", side_effect=_mock_httpx_post), \
         patch("httpx.Client.get", side_effect=_mock_httpx_get):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )

    assert response.status_code == 200

    after = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    assert after == before + 1, f"应新建 1 条用户 (前={before}, 后={after})"

    role = db_session.execute(
        text("SELECT role FROM users ORDER BY created_at DESC LIMIT 1")
    ).scalar()
    assert role == "viewer", f"期望 role=viewer，实际 role={role}"


# ===================== 附加：用户记录含 username + email =====================

@pytest.mark.asyncio
async def test_github_oauth_user_has_username_and_email(client, db_session):
    with patch("httpx.Client.post", side_effect=_mock_httpx_post), \
         patch("httpx.Client.get", side_effect=_mock_httpx_get):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    row = db_session.execute(
        text("SELECT username, email FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None
    assert row[0] == MOCK_GITHUB_USER_INFO["login"], (
        f"期望 username={MOCK_GITHUB_USER_INFO['login']}，实际 {row[0]}"
    )
    assert row[1] == MOCK_GITHUB_USER_INFO["email"]


# ===================== 附加：重复登录不重复创建 =====================

@pytest.mark.asyncio
async def test_github_oauth_no_duplicate_on_second_login(client, db_session):
    with patch("httpx.Client.post", side_effect=_mock_httpx_post), \
         patch("httpx.Client.get", side_effect=_mock_httpx_get):
        r1 = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
        assert r1.status_code == 200

        r2 = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}_2", "client_id": MOCK_CLIENT_ID},
        )
        assert r2.status_code == 200

    count = db_session.execute(
        text("SELECT COUNT(*) FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).scalar()
    assert count == 1, f"同一 GitHub 账号应只有 1 条记录，实际 {count}"


# ===================== 附加：缺少 code 返回错误 =====================

@pytest.mark.asyncio
async def test_github_oauth_missing_code(client, db_session):
    response = await client.get(
        "/api/auth/oauth/github/callback",
        params={"client_id": MOCK_CLIENT_ID},
    )
    assert response.status_code in (400, 422), (
        f"缺少 code 应返回 400/422，实际 {response.status_code}"
    )


# ===================== 附加：缺少 client_id 返回错误 =====================

@pytest.mark.asyncio
async def test_github_oauth_missing_client_id(client, db_session):
    response = await client.get(
        "/api/auth/oauth/github/callback",
        params={"code": "abc"},
    )
    assert response.status_code in (400, 422), (
        f"缺少 client_id 应返回 400/422，实际 {response.status_code}"
    )


# ===================== 附加：GitHub token 请求失败 =====================

@pytest.mark.asyncio
async def test_github_oauth_token_request_failure(client, db_session):
    with patch("httpx.Client.post", side_effect=_mock_httpx_post_fail):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "bad_code", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code in (400, 401, 500), (
        f"token 请求失败应返回错误，实际 {response.status_code}"
    )


# ===================== 附加：响应含 refresh_token + token_type =====================

@pytest.mark.asyncio
async def test_github_oauth_response_has_refresh_token_and_type(client, db_session):
    with patch("httpx.Client.post", side_effect=_mock_httpx_post), \
         patch("httpx.Client.get", side_effect=_mock_httpx_get):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    tokens = response.json().get("data", {}).get("tokens", {})
    assert "access_token" in tokens
    assert "refresh_token" in tokens, "响应应包含 refresh_token"

    tt = tokens.get("token_type", "")
    assert tt.lower() == "bearer", f"期望 token_type=Bearer，实际 {tt}"


# ===================== 附加：access_token 和 refresh_token 均为 JWT =====================

@pytest.mark.asyncio
async def test_github_oauth_both_tokens_are_jwt(client, db_session):
    with patch("httpx.Client.post", side_effect=_mock_httpx_post), \
         patch("httpx.Client.get", side_effect=_mock_httpx_get):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    tokens = response.json().get("data", {}).get("tokens", {})
    for name in ("access_token", "refresh_token"):
        parts = tokens[name].split(".")
        assert len(parts) == 3, (
            f"{name} 应为三段 JWT，实际 {len(parts)} 段"
        )
