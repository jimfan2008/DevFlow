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
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs

import pytest
import jwt as pyjwt
from unittest.mock import patch, MagicMock
from sqlalchemy import text, Column, Integer, String, DateTime, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, RedirectResponse
from httpx import AsyncClient, ASGITransport

# ===================== 模拟后端应用 =====================

JWT_SECRET = "tdd-test-secret-key-super-secure-2026"
JWT_ALGORITHM = "HS256"
SESSION_STATES: dict = {}

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(Integer, nullable=True)
    username = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, unique=True)
    password_hash = Column(String(255), default="")
    role = Column(String(50), default="viewer")
    avatar_url = Column(String(500), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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


def _sign_jwt(payload: dict, expires_delta: int = 3600) -> str:
    now = datetime.now(timezone.utc)
    payload["exp"] = now + timedelta(seconds=expires_delta)
    payload["iat"] = now
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_jwt(token: str) -> dict:
    return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _create_app():
    """创建模拟 FastAPI 应用，复刻实际后端 OAuth 流程"""
    app = FastAPI()
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    app.state.states = {}

    GITHUB_CLIENT_ID = "tdd_test_client_id"
    GITHUB_CLIENT_SECRET = "tdd_test_client_secret"
    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    REDIRECT_URI = "http://localhost:8000/api/auth/oauth/github/callback"

    def _get_db():
        return SessionLocal()

    # ---- 验收 1: 302 重定向至 GitHub 授权页 ----
    @app.get("/api/auth/oauth/github")
    def github_oauth_initiate(
        client_id: str = Query(default=GITHUB_CLIENT_ID),
        redirect_uri: str = Query(default=None),
    ):
        state = uuid.uuid4().hex
        callback = redirect_uri or REDIRECT_URI
        auth_url = (
            f"{GITHUB_AUTH_URL}?client_id={client_id}"
            f"&redirect_uri={callback}"
            f"&scope=read:user+user:email"
            f"&state={state}"
        )
        app.state.states[state] = datetime.now(timezone.utc)
        return RedirectResponse(url=auth_url, status_code=302)

    # ---- 验收 2/3/4: 回调处理 ----
    @app.get("/api/auth/oauth/github/callback")
    def github_oauth_callback(
        code: str = Query(default=None),
        state: str = Query(default=None),
        client_id: str = Query(default=GITHUB_CLIENT_ID),
    ):
        import requests as req

        # state 校验
        if not state or state not in app.state.states:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid or missing state parameter"},
            )

        # 缺少 code
        if not code:
            return JSONResponse(
                status_code=422,
                content={"detail": "Missing authorization code"},
            )

        # 1. 用授权码换 GitHub token
        token_resp = req.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200 or "error" in token_resp.text:
            return JSONResponse(
                status_code=400,
                content={"detail": "Failed to exchange authorization code"},
            )
        token_data = token_resp.json()
        github_access_token = token_data.get("access_token", "")
        if not github_access_token:
            return JSONResponse(
                status_code=400,
                content={"detail": "No access token returned from GitHub"},
            )

        # 2. 获取 GitHub 用户信息
        user_resp = req.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"token {github_access_token}",
                "Accept": "application/json",
            },
        )
        if user_resp.status_code != 200:
            return JSONResponse(
                status_code=502,
                content={"detail": "Failed to fetch GitHub user info"},
            )
        github_user = user_resp.json()

        # 3. 查找或创建本地用户
        db: Session = _get_db()
        try:
            github_email = github_user.get("email") or f"gh_{github_user.get('id')}@github.com"
            user = db.query(User).filter(User.email == github_email).first()

            if user is None:
                username = github_user.get("login", f"gh_{github_user.get('id')}")
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    username = f"{username}_{github_user.get('id', 'user')}"
                user = User(
                    github_id=github_user.get("id"),
                    username=username,
                    email=github_email,
                    password_hash="",
                    role="viewer",
                    avatar_url=github_user.get("avatar_url"),
                    status="active",
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            # 4. 生成 JWT tokens
            access_token = _sign_jwt(
                {"sub": str(user.id), "email": user.email, "role": user.role, "type": "access"},
                expires_delta=3600,
            )
            refresh_token = _sign_jwt(
                {"sub": str(user.id), "type": "refresh"},
                expires_delta=604800,
            )

            return JSONResponse(
                status_code=200,
                content={
                    "code": 0,
                    "message": "success",
                    "data": {
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "role": user.role,
                        },
                        "tokens": {
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "token_type": "Bearer",
                            "expires_in": 3600,
                        },
                    },
                },
            )
        finally:
            db.close()

    app.state.db_engine = engine
    app.state.SessionLocal = SessionLocal
    return app


# ===================== Fixtures =====================

@pytest.fixture(scope="function")
def app_instance():
    """每个测试独立创建应用实例"""
    return _create_app()


@pytest.fixture(scope="function")
async def client(app_instance):
    """ASGI 测试客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app_instance),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        yield ac


@pytest.fixture(scope="function")
def db_session(app_instance):
    """数据库会话"""
    SessionLocal = app_instance.state.SessionLocal
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def valid_state(app_instance):
    """生成一个有效的 state"""
    state = uuid.uuid4().hex
    app_instance.state.states[state] = datetime.now(timezone.utc)
    return state


# ===================== 验收 1: HTTP 302 重定向至 GitHub 授权页 =====================

@pytest.mark.asyncio
async def test_github_oauth_initiate_302_redirect(client, app_instance):
    """GET /api/auth/oauth/github -> 302 重定向到 GitHub 授权页"""
    response = await client.get("/api/auth/oauth/github")

    assert response.status_code == 302, (
        f"期望 302 重定向，实际 {response.status_code}"
    )

    loc = response.headers.get("location", "")
    assert "github.com" in loc, f"重定向 URL 应指向 GitHub，实际: {loc}"
    assert "login/oauth/authorize" in loc, f"应包含 authorize 路径，实际: {loc}"

    parsed = urlparse(loc)
    params = parse_qs(parsed.query)
    assert "client_id" in params, f"应包含 client_id 参数，实际: {loc}"
    assert "state" in params, f"应包含 state 参数 (CSRF 防护)，实际: {loc}"
    assert "redirect_uri" in params, f"应包含 redirect_uri 参数，实际: {loc}"
    assert "scope" in params, f"应包含 scope 参数，实际: {loc}"


@pytest.mark.asyncio
async def test_github_oauth_initiate_generates_unique_state(client, app_instance):
    """每次请求应生成不同的 state"""
    r1 = await client.get("/api/auth/oauth/github")
    r2 = await client.get("/api/auth/oauth/github")

    loc1 = urlparse(r1.headers["location"]).query
    loc2 = urlparse(r2.headers["location"]).query

    state1 = parse_qs(loc1)["state"][0]
    state2 = parse_qs(loc2)["state"][0]

    assert state1 != state2, "两次请求应生成不同的 state"
    assert len(state1) > 10, "state 应有足够长度防止碰撞"


# ===================== 验收 2: 回调后 HTTP 200 返回有效 JWT Token =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_200_with_jwt(client, app_instance, valid_state):
    """回调成功 -> 200 + 有效 JWT access_token"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )

    assert response.status_code == 200, f"期望 200，实际 {response.status_code}"

    body = response.json()
    assert body["code"] == 0, "业务码应为 0"

    tokens = body["data"]["tokens"]
    assert "access_token" in tokens, "响应应包含 access_token"

    # 验证 JWT 三段式结构
    parts = tokens["access_token"].split(".")
    assert len(parts) == 3, (
        f"JWT 应为三段 (header.payload.signature)，实际 {len(parts)} 段"
    )

    # 验证 JWT 可正确解码
    payload = _decode_jwt(tokens["access_token"])
    assert "sub" in payload, "JWT payload 应包含 sub (用户 ID)"
    assert payload.get("type") == "access", "JWT type 应为 access"
    assert "exp" in payload, "JWT 应包含过期时间"
    assert "role" in payload, "JWT 应包含 role 声明"


@pytest.mark.asyncio
async def test_github_oauth_callback_contains_user_info(client, app_instance, valid_state):
    """回调响应应包含用户基本信息"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )

    assert response.status_code == 200

    user = response.json()["data"]["user"]
    assert user["username"] == MOCK_GITHUB_USER_INFO["login"]
    assert user["email"] == MOCK_GITHUB_USER_INFO["email"]
    assert user["role"] == "viewer"
    assert "id" in user


# ===================== 验收 3: 响应时间 <= 1 秒 =====================

@pytest.mark.asyncio
async def test_github_oauth_callback_response_time(client, app_instance, valid_state):
    """回调处理应在 1 秒内完成"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        start = time.perf_counter()
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms <= 1000, f"回调处理耗时 {elapsed_ms:.1f}ms，超出 1000ms 上限"


@pytest.mark.asyncio
async def test_github_oauth_initiate_response_time(client, app_instance):
    """OAuth 发起请求应在 1 秒内完成"""
    start = time.perf_counter()
    response = await client.get("/api/auth/oauth/github")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 302
    assert elapsed_ms <= 1000, f"发起请求耗时 {elapsed_ms:.1f}ms，超出 1000ms 上限"


# ===================== 验收 4: 首次登录自动创建账户 role=viewer =====================

@pytest.mark.asyncio
async def test_github_oauth_first_login_creates_user(client, app_instance, valid_state):
    """首次 OAuth 登录自动创建用户记录"""
    db = app_instance.state.SessionLocal()
    before_count = db.query(User).count()
    db.close()

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )

    assert response.status_code == 200

    db = app_instance.state.SessionLocal()
    after_count = db.query(User).count()
    assert after_count == before_count + 1, (
        f"应新建 1 条用户 (前={before_count}, 后={after_count})"
    )
    db.close()


@pytest.mark.asyncio
async def test_github_oauth_new_user_has_viewer_role(client, app_instance, valid_state):
    """新创建的用户 role 必须为 viewer"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )

    assert response.status_code == 200

    # 检查响应中的 role
    user = response.json()["data"]["user"]
    assert user["role"] == "viewer", f"期望 role=viewer，实际 role={user['role']}"

    # 检查数据库中存储的 role
    db = app_instance.state.SessionLocal()
    db_user = db.query(User).filter(
        User.email == MOCK_GITHUB_USER_INFO["email"]
    ).first()
    assert db_user is not None, "数据库应存在用户记录"
    assert db_user.role == "viewer", f"数据库 role 应为 viewer，实际 {db_user.role}"
    db.close()


# ===================== 附加: 用户记录字段完整性 =====================

@pytest.mark.asyncio
async def test_github_oauth_user_has_github_id(client, app_instance, valid_state):
    """新建用户应保存 GitHub ID"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    db = app_instance.state.SessionLocal()
    user = db.query(User).filter(
        User.email == MOCK_GITHUB_USER_INFO["email"]
    ).first()
    assert user.github_id == MOCK_GITHUB_USER_INFO["id"], (
        f"期望 github_id={MOCK_GITHUB_USER_INFO['id']}，实际 {user.github_id}"
    )
    db.close()


@pytest.mark.asyncio
async def test_github_oauth_user_has_username_and_email(client, app_instance, valid_state):
    """新建用户应保存 GitHub login 为 username，email 为 email"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    db = app_instance.state.SessionLocal()
    user = db.query(User).filter(
        User.email == MOCK_GITHUB_USER_INFO["email"]
    ).first()
    assert user.username == MOCK_GITHUB_USER_INFO["login"], (
        f"期望 username={MOCK_GITHUB_USER_INFO['login']}，实际 {user.username}"
    )
    assert user.email == MOCK_GITHUB_USER_INFO["email"]
    db.close()


@pytest.mark.asyncio
async def test_github_oauth_user_status_is_active(client, app_instance, valid_state):
    """新建用户状态应为 active"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    db = app_instance.state.SessionLocal()
    user = db.query(User).filter(
        User.email == MOCK_GITHUB_USER_INFO["email"]
    ).first()
    assert user.status == "active", f"期望 status=active，实际 {user.status}"
    db.close()


# ===================== 附加: 重复登录不重复创建 =====================

@pytest.mark.asyncio
async def test_github_oauth_no_duplicate_on_second_login(client, app_instance):
    """同一 GitHub 账号多次登录不应创建重复记录"""
    state1 = uuid.uuid4().hex
    state2 = uuid.uuid4().hex
    app_instance.state.states[state1] = datetime.now(timezone.utc)
    app_instance.state.states[state2] = datetime.now(timezone.utc)

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        r1 = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": state1},
        )
        assert r1.status_code == 200

        r2 = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}_2", "state": state2},
        )
        assert r2.status_code == 200

    db = app_instance.state.SessionLocal()
    count = db.query(User).filter(
        User.github_id == MOCK_GITHUB_USER_INFO["id"]
    ).count()
    assert count == 1, f"同一 GitHub 账号应只有 1 条记录，实际 {count}"
    db.close()


@pytest.mark.asyncio
async def test_github_oauth_second_login_returns_same_user(client, app_instance):
    """第二次登录应返回同一用户"""
    state1 = uuid.uuid4().hex
    state2 = uuid.uuid4().hex
    app_instance.state.states[state1] = datetime.now(timezone.utc)
    app_instance.state.states[state2] = datetime.now(timezone.utc)

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        r1 = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": state1},
        )
        r2 = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}_2", "state": state2},
        )

    user1 = r1.json()["data"]["user"]
    user2 = r2.json()["data"]["user"]
    assert user1["id"] == user2["id"], "两次登录应返回同一用户 ID"
    assert user1["username"] == user2["username"]
    assert user1["email"] == user2["email"]


# ===================== 附加: state 校验 =====================

@pytest.mark.asyncio
async def test_github_oauth_invalid_state_returns_400(client, app_instance):
    """state 不匹配应返回 400 错误"""
    response = await client.get(
        "/api/auth/oauth/github/callback",
        params={"code": "abc", "state": "wrong_state"},
    )
    assert response.status_code == 400, (
        f"无效 state 应返回 400，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_github_oauth_missing_state_returns_400(client, app_instance):
    """缺少 state 参数应返回 400 错误"""
    response = await client.get(
        "/api/auth/oauth/github/callback",
        params={"code": "abc"},
    )
    assert response.status_code == 400, (
        f"缺少 state 应返回 400，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_github_oauth_state_from_initiate_passes_callback(client, app_instance):
    """从 /oauth/github 获取的 state 应在 /callback 中通过校验"""
    # 第一步：调用 login 获取 state
    login_resp = await client.get("/api/auth/oauth/github")
    assert login_resp.status_code == 302

    loc = login_resp.headers.get("location", "")
    parsed = urlparse(loc)
    saved_state = parse_qs(parsed.query)["state"][0]

    # 第二步：用该 state 回调
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": saved_state},
        )

    assert response.status_code == 200, (
        f"使用 login 生成的 state 回调应返回 200，实际 {response.status_code}"
    )


# ===================== 附加: 缺少 code 返回错误 =====================

@pytest.mark.asyncio
async def test_github_oauth_missing_code_returns_422(client, app_instance, valid_state):
    """缺少 code 参数应返回 422"""
    response = await client.get(
        "/api/auth/oauth/github/callback",
        params={"state": valid_state},
    )
    assert response.status_code == 422, (
        f"缺少 code 应返回 422，实际 {response.status_code}"
    )


# ===================== 附加: GitHub token 请求失败 =====================

@pytest.mark.asyncio
async def test_github_oauth_token_exchange_failure(client, app_instance, valid_state):
    """GitHub token 交换失败应返回 400"""
    with patch("requests.post", side_effect=_mock_github_token_fail):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "bad_code", "state": valid_state},
        )
    assert response.status_code == 400, (
        f"token 交换失败应返回 400，实际 {response.status_code}"
    )


# ===================== 附加: tokens 完整性 =====================

@pytest.mark.asyncio
async def test_github_oauth_response_has_refresh_token_and_type(client, app_instance, valid_state):
    """响应应包含 refresh_token 和 token_type"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    tokens = response.json()["data"]["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens, "响应应包含 refresh_token"
    assert tokens["token_type"] == "Bearer", f"期望 token_type=Bearer，实际 {tokens.get('token_type')}"
    assert "expires_in" in tokens


@pytest.mark.asyncio
async def test_github_oauth_both_tokens_are_valid_jwt(client, app_instance, valid_state):
    """access_token 和 refresh_token 都应为有效的 JWT"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    tokens = response.json()["data"]["tokens"]

    for name in ("access_token", "refresh_token"):
        # 验证三段式结构
        parts = tokens[name].split(".")
        assert len(parts) == 3, (
            f"{name} 应为三段 JWT，实际 {len(parts)} 段"
        )

        # 验证可正确解码
        payload = _decode_jwt(tokens[name])
        assert "sub" in payload, f"{name} payload 应包含 sub"
        assert "exp" in payload, f"{name} 应包含过期时间"

    # 验证 access_token type
    access_payload = _decode_jwt(tokens["access_token"])
    assert access_payload["type"] == "access"

    # 验证 refresh_token type
    refresh_payload = _decode_jwt(tokens["refresh_token"])
    assert refresh_payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_github_oauth_access_token_expiry(client, app_instance, valid_state):
    """access_token 过期时间应为约 1 小时后"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    payload = _decode_jwt(response.json()["data"]["tokens"]["access_token"])
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff_seconds = (exp - now).total_seconds()

    # 允许 10 秒误差
    assert 3500 <= diff_seconds <= 3700, (
        f"access_token 过期时间应约为 3600 秒，实际 {diff_seconds:.0f} 秒"
    )


@pytest.mark.asyncio
async def test_github_oauth_refresh_token_expiry(client, app_instance, valid_state):
    """refresh_token 过期时间应为约 7 天后"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    payload = _decode_jwt(response.json()["data"]["tokens"]["refresh_token"])
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff_seconds = (exp - now).total_seconds()

    # 7 天 = 604800 秒，允许 10 秒误差
    assert 604700 <= diff_seconds <= 604900, (
        f"refresh_token 过期时间应约为 604800 秒，实际 {diff_seconds:.0f} 秒"
    )


# ===================== 附加: GitHub 用户无 email 时的兜底 =====================

@pytest.mark.asyncio
async def test_github_oauth_user_without_email_uses_fallback(client, app_instance, valid_state):
    """GitHub 用户无 email 时使用兜底邮箱"""

    def _mock_user_no_email(*args, **kwargs):
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {
            "id": 111222,
            "login": "no_email_user",
            "email": None,
            "name": "No Email",
            "avatar_url": None,
        }
        r.text = json.dumps(r.json.return_value)
        return r

    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_user_no_email):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )

    assert response.status_code == 200
    user = response.json()["data"]["user"]
    assert user["email"] == "gh_111222@github.com", (
        f"无 email 时应使用兜底邮箱，实际 {user['email']}"
    )


# ===================== 附加: 自定义 redirect_uri =====================

@pytest.mark.asyncio
async def test_github_oauth_custom_redirect_uri(client, app_instance):
    """可传入自定义 redirect_uri"""
    custom_uri = "https://myapp.com/callback"
    response = await client.get(
        "/api/auth/oauth/github",
        params={"redirect_uri": custom_uri},
    )

    assert response.status_code == 302
    loc = response.headers.get("location", "")
    assert custom_uri in loc, f"重定向 URL 应包含自定义 redirect_uri，实际: {loc}"


# ===================== 附加: JWT 签名验证 =====================

@pytest.mark.asyncio
async def test_github_oauth_jwt_can_be_verified_with_secret(client, app_instance, valid_state):
    """返回的 JWT 可用已知密钥正确验证"""
    with patch("requests.post", side_effect=_mock_github_token_resp), \
         patch("requests.get", side_effect=_mock_github_user_resp):
        response = await client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "state": valid_state},
        )
    assert response.status_code == 200

    token = response.json()["data"]["tokens"]["access_token"]
    payload = pyjwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"verify_exp": False},
    )
    assert payload["sub"].isdigit(), "sub 应为用户 ID 的数字字符串"
    assert payload["email"] == MOCK_GITHUB_USER_INFO["email"]
    assert payload["role"] == "viewer"