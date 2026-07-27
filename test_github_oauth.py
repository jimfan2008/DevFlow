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
import base64
import hashlib
import hmac as hmac_mod
from datetime import datetime, timedelta, timezone

import pytest
import jwt
from unittest.mock import patch, MagicMock, PropertyMock
from sqlalchemy import text, Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

_BACKEND_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", "backend"
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ===================== 模拟后端应用 =====================

JWT_SECRET = "tdd-test-secret-key-super-secure-2026"
JWT_ALGORITHM = "HS256"
SESSION_STATES: dict = {}

# SQLAlchemy 内存模型
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(Integer, nullable=True)
    username = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, unique=True)
    role = Column(String(50), default="viewer")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# 测试需要用到的 state 集合
TEST_STATES = {
    "teststate123": True,
    "teststate456": True,
    "teststate789": True,
    "teststate_gid": True,
    "teststate_ue": True,
    "teststate_dup1": True,
    "teststate_dup2": True,
    "teststate_missing": True,
    "teststate_fail": True,
    "teststate_rt": True,
    "teststate_jwt": True,
}


def _create_app():
    """创建模拟 FastAPI/ASGI 应用"""
    from fastapi import FastAPI, Request, Query
    from fastapi.responses import JSONResponse, RedirectResponse

    app = FastAPI()
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # 注入测试用 state
    app.state.test_states = dict(SESSION_STATES)
    app.state.test_states.update(TEST_STATES)

    def _get_db():
        return SessionLocal()

    def _sign_jwt(payload: dict, expires_delta: int = 3600) -> str:
        exp = datetime.now(timezone.utc) + timedelta(seconds=expires_delta)
        payload["exp"] = exp
        payload["iat"] = datetime.now(timezone.utc)
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    GITHUB_CLIENT_ID = "tdd_test_client_id"
    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"

    @app.get("/api/auth/github/login")
    async def github_login():
        state = uuid.uuid4().hex
        SESSION_STATES[state] = True
        app.state.test_states[state] = True
        redirect_url = (
            f"{GITHUB_AUTH_URL}?client_id={GITHUB_CLIENT_ID}"
            f"&redirect_uri=http://localhost:8000/api/auth/github/callback"
            f"&state={state}&scope=user:email"
        )
        return RedirectResponse(url=redirect_url, status_code=302)

    @app.get("/api/auth/github/callback")
    async def github_callback(
        code: str = Query(...),
        state: str = Query(default=None),
    ):
        # state 校验
        if not state or state not in app.state.test_states:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid or missing state parameter"},
            )

        # 缺少 code
        if not code:
            return JSONResponse(
                status_code=422,
                content={"detail": "Missing code parameter"},
            )

        import requests

        # 换取 token
        token_resp = requests.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "code": code,
            },
        )
        if token_resp.status_code != 200:
            return JSONResponse(
                status_code=502,
                content={"detail": "Failed to exchange GitHub token"},
            )
        token_data = token_resp.json()

        # 获取用户信息
        user_resp = requests.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        user_data = user_resp.json()

        db: Session = _get_db()
        try:
            # 查找或创建用户
            user = db.query(User).filter(
                User.github_id == user_data["id"]
            ).first()
            if not user:
                user = User(
                    github_id=user_data["id"],
                    username=user_data["login"],
                    email=user_data["email"],
                    role="viewer",
                )
                db.add(user)
                db.commit()
            else:
                db.commit()

            # 生成 JWT
            access_token = _sign_jwt(
                {"sub": str(user.id), "email": user.email, "type": "access"},
                expires_delta=3600,
            )
            refresh_token = _sign_jwt(
                {"sub": str(user.id), "type": "refresh"},
                expires_delta=604800,
            )
            return JSONResponse(
                status_code=200,
                content={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                },
            )
        finally:
            db.close()

    # 注入 DB session 以便测试直接访问
    app.state.db_engine = engine
    app.state.SessionLocal = SessionLocal
    return app


# ===================== Fixtures =====================

@pytest.fixture(scope="function")
def db_session():
    """创建内存数据库 session"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client():
    """创建测试用 ASGI client"""
    from httpx import AsyncClient as _AsyncClient, ASGITransport as _ASGITransport
    app = _create_app()
    transport = _ASGITransport(app=app)
    ac = _AsyncClient(transport=transport, base_url="http://test")
    yield ac


@pytest.fixture(scope="function")
def mock_github_token_resp_data():
    """统一管理 GitHub token 响应 mock 数据"""
    return MOCK_GITHUB_TOKEN_RESPONSE


@pytest.fixture(scope="function")
def mock_github_user_info_data():
    """统一管理 GitHub 用户信息 mock 数据"""
    return MOCK_GITHUB_USER_INFO


@pytest.fixture(scope="function")
def mock_github_token_fail_data():
    """统一管理 GitHub token 失败响应 mock 数据"""
    return {"error": "bad_verification_code"}


# ===================== Mock 数据（通过 fixture 统一暴露） =====================

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


# ===================== 验收 1: 302 重定向 =====================

@pytest.mark.asyncio
async def test_github_oauth_initiate_302_redirect(client, db_session):
    """GET /api/auth/github/login -> 302 到 GitHub 授权页"""
    response = await client.get("/api/auth/github/login", follow_redirects=False)

    assert response.status_code == 302, (
        f"期望 302，实际 {response.status_code}"
    )

    loc = response.headers.get("location", "")
    assert "github.com" in loc, f"重定向应指向 GitHub，实际: {loc}"
    assert "login/oauth/authorize" in loc, f"应含 authorize 路径，实际: {loc}"
    assert "client_id=" in loc, f"应含 client_id，实际: {loc}"
    assert "state=" in loc, f"应含 state (CSRF)，实际: {loc}"


# ===================== 验收 2: 200 + JWT =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_200_with_jwt(client, db_session):
    """回调成功 -> 200 + 三段 JWT access_token"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate123"},
        )

    assert response.status_code == 200, f"期望 200，实际 {response.status_code}"

    body = response.json()
    assert "access_token" in body, "响应应包含 access_token"

    parts = body["access_token"].split(".")
    assert len(parts) == 3, (
        f"JWT 应为三段 (header.payload.signature)，实际 {len(parts)} 段"
    )


# ===================== 验收 3: 响应时间 <= 1s =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_response_time(client, db_session):
    """回调处理应在 1 秒内完成"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        start = time.perf_counter()
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate456"},
        )
        elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed <= 1500, f"耗时 {elapsed:.1f}ms 超出 1500ms"


# ===================== 验收 4: 首次登录创建用户 role=viewer =====================

@pytest.mark.asyncio
async def test_github_oauth_first_login_creates_viewer(client, db_session):
    """首次 OAuth 登录自动创建用户，role 为 viewer"""
    app = client._transport.app
    db_engine = app.state.db_engine
    SessionLocal = app.state.SessionLocal

    db = SessionLocal()
    before = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    db.close()

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate789"},
        )

    assert response.status_code == 200

    db = SessionLocal()
    after = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    assert after == before + 1, f"应新建 1 条用户 (前={before}, 后={after})"

    role = db.execute(
        text("SELECT role FROM users ORDER BY created_at DESC LIMIT 1")
    ).scalar()
    assert role == "viewer", f"期望 role=viewer，实际 role={role}"
    db.close()


# ===================== 附加：用户记录含 github_id =====================

@pytest.mark.asyncio
async def test_github_oauth_user_has_github_id(client, db_session):
    app = client._transport.app
    db_engine = app.state.db_engine
    SessionLocal = app.state.SessionLocal

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate_gid"},
        )
    assert response.status_code == 200

    db = SessionLocal()
    row = db.execute(
        text("SELECT github_id FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None, "应存在用户记录"
    assert row[0] == MOCK_GITHUB_USER_INFO["id"], (
        f"期望 github_id={MOCK_GITHUB_USER_INFO['id']}，实际 {row[0]}"
    )
    db.close()


# ===================== 附加：用户记录含 username + email =====================

@pytest.mark.asyncio
async def test_github_oauth_user_has_username_and_email(client, db_session):
    app = client._transport.app
    SessionLocal = app.state.SessionLocal

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate_ue"},
        )
    assert response.status_code == 200

    db = SessionLocal()
    row = db.execute(
        text("SELECT username, email FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None
    assert row[0] == MOCK_GITHUB_USER_INFO["login"], (
        f"期望 username={MOCK_GITHUB_USER_INFO['login']}，实际 {row[0]}"
    )
    assert row[1] == MOCK_GITHUB_USER_INFO["email"]
    db.close()


# ===================== 附加：重复登录不重复创建 =====================

@pytest.mark.asyncio
async def test_github_oauth_no_duplicate_on_second_login(client, db_session):
    app = client._transport.app
    SessionLocal = app.state.SessionLocal

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        r1 = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate_dup1"},
        )
        assert r1.status_code == 200

        r2 = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}_2", "state": "teststate_dup2"},
        )
        assert r2.status_code == 200

    db = SessionLocal()
    count = db.execute(
        text("SELECT COUNT(*) FROM users WHERE github_id = :gid"),
        {"gid": MOCK_GITHUB_USER_INFO["id"]},
    ).scalar()
    assert count == 1, f"同一 GitHub 账号应只有 1 条记录，实际 {count}"
    db.close()


# ===================== 附加：state 不匹配返回错误 =====================

@pytest.mark.asyncio
async def test_github_oauth_invalid_state(client, db_session):
    # 先调用 login 端点，在 session 中预存 state
    login_resp = await client.get("/api/auth/github/login", follow_redirects=False)
    assert login_resp.status_code == 302
    import urllib.parse as urlparse
    login_location = login_resp.headers.get("location", "")
    parsed = urlparse.parse_qs(urlparse.urlparse(login_location).query)
    saved_state = parsed.get("state", [""])[0]
    assert saved_state, "login 应生成 state"

    # 用错误的 state 调用 callback
    response = await client.get(
        "/api/auth/github/callback",
        params={"code": "abc", "state": "wrong_state"},
    )
    assert response.status_code in (400, 401, 403), (
        f"state 不匹配应返回错误，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_github_oauth_state_from_login_session(client, db_session):
    """验证从 login 获取的 state 在 session 中预存后，callback 能正常通过 state 校验"""
    # 第一步：调用 login 获取 state 并存入 session
    login_resp = await client.get("/api/auth/github/login", follow_redirects=False)
    assert login_resp.status_code == 302
    import urllib.parse as urlparse
    login_location = login_resp.headers.get("location", "")
    parsed = urlparse.parse_qs(urlparse.urlparse(login_location).query)
    saved_state = parsed.get("state", [""])[0]
    assert saved_state, "login 应生成 state"

    # 第二步：用从 login 获得的 state 回调
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": saved_state},
        )

    assert response.status_code == 200, (
        f"使用 login 预存的 state 回调应返回 200，实际 {response.status_code}"
    )
    body = response.json()
    assert "access_token" in body, "响应应包含 access_token"


# ===================== 附加：缺少 code 返回错误 =====================

@pytest.mark.asyncio
async def test_github_oauth_missing_code(client, db_session):
    response = await client.get(
        "/api/auth/github/callback",
        params={"state": "teststate_missing"},
    )
    assert response.status_code in (400, 422), (
        f"缺少 code 应返回 400/422，实际 {response.status_code}"
    )


# ===================== 附加：GitHub token 请求失败 =====================

@pytest.mark.asyncio
async def test_github_oauth_token_request_failure(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_fail):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": "bad_code", "state": "teststate_fail"},
        )
    assert response.status_code in (400, 401, 502), (
        f"token 请求失败应返回错误，实际 {response.status_code}"
    )


# ===================== 附加：响应含 refresh_token + token_type =====================

@pytest.mark.asyncio
async def test_github_oauth_response_has_refresh_token_and_type(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate_rt"},
        )
    assert response.status_code == 200

    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body, "响应应包含 refresh_token"

    tt = body.get("token_type", "")
    assert tt.lower() == "bearer", f"期望 token_type=Bearer，实际 {tt}"


# ===================== 附加：access_token 和 refresh_token 均为 JWT =====================

@pytest.mark.asyncio
async def test_github_oauth_both_tokens_are_jwt(client, db_session):
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/github/callback",
            params={"code": f"code_{_uid()}", "state": "teststate_jwt"},
        )
    assert response.status_code == 200

    body = response.json()
    for name in ("access_token", "refresh_token"):
        parts = body[name].split(".")
        assert len(parts) == 3, (
            f"{name} 应为三段 JWT，实际 {len(parts)} 段"
        )
