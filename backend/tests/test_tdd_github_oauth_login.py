#!/usr/bin/env python3
# TDD-0005: GitHub OAuth 第三方登录
#
# 验收标准：
#   1. HTTP 307 重定向至 GitHub OAuth 授权页
#   2. 回调后 HTTP 200 返回有效 JWT Token
#   3. 响应时间 <= 1 秒
#   4. 首次登录自动创建账户，role = 'viewer'
#
# 根因修复说明：
#   - 原测试 mock 了 requests.post/get，但 auth_service 实际使用 httpx.Client
#   - 原测试 URL 为 /api/auth/github/login，实际路由为 /api/auth/oauth/github
#   - 原测试断言 302，实际 RedirectResponse status_code=307
#   - 原测试断言 github_id 列，User 模型中不存在该列
#   - 原测试断言扁平 response.access_token，实际嵌套在 data.tokens 下
#   - callback 需要 client_id 查询参数
#   - 原测试用 @pytest.mark.asyncio 但路由是同步函数
#   - 原测试 _BACKEND_DIR 路径向上走了 5 层，实际只需 1 层

import os
import sys
import time
import json
import uuid

import pytest
from unittest.mock import patch, MagicMock, Mock
from sqlalchemy import text

# 根因修复：测试文件在 backend/tests/ 下，只需加入 backend 目录
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ===================== Mock 数据 =====================

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
    """创建模拟的 httpx.Client 上下文管理器。

    根因修复：auth_service.github_oauth_login 内部使用 httpx.Client()，
    不是 requests.post/get。因此必须 mock httpx.Client 本身。
    """
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
    """Token 交换失败"""
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"error": "bad_verification_code"}
    mock_resp.text = '{"error": "bad_verification_code"}'

    mock_client = Mock()
    mock_client.post.return_value = mock_resp
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    return mock_client


def _make_mock_httpx_client_user_fail():
    """用户信息获取失败"""
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


def _uid():
    return uuid.uuid4().hex[:8]


# ===================== Fixtures =====================

from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass= StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def db_session():
    """每个测试独立的数据库会话"""
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
    """同步 TestClient，follow_redirects=False 以捕获 307"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, follow_redirects=False) as tc:
        yield tc

    app.dependency_overrides.clear()


# ===================== 验收 1: 307 重定向 =====================

def test_github_oauth_initiate_307_redirect(client):
    """GET /api/auth/oauth/github -> 307 到 GitHub 授权页

    根因修复：
      - 原 URL /api/auth/github/login -> 实际 /api/auth/oauth/github
      - 原断言 302 -> 实际 RedirectResponse status_code=307
      - 去掉 db_session 依赖（此端点不操作数据库）
      - 去掉 @pytest.mark.asyncio（路由是同步函数）
    """
    response = client.get(
        "/api/auth/oauth/github",
        params={"client_id": MOCK_CLIENT_ID},
    )

    assert response.status_code == 307, (
        f"期望 307，实际 {response.status_code}"
    )

    loc = response.headers.get("location", "")
    assert "github.com" in loc, f"重定向应指向 GitHub，实际: {loc}"
    assert "login/oauth/authorize" in loc, f"应含 authorize 路径，实际: {loc}"
    assert "client_id=" in loc, f"应含 client_id，实际: {loc}"
    assert "state=" in loc, f"应含 state (CSRF)，实际: {loc}"


# ===================== 验收 2: 200 + JWT =====================

def test_github_oauth_callback_200_with_jwt(client, db_session):
    """回调成功 -> 200 + 三段 JWT access_token

    根因修复：
      - 原 mock requests.post/get -> 实际 mock httpx.Client
      - 原 URL /api/auth/github/callback -> 实际 /api/auth/oauth/github/callback
      - 原断言 body['access_token'] -> 实际 body['data']['tokens']['access_token']
      - 增加 client_id 查询参数
    """
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )

    assert response.status_code == 200, f"期望 200，实际 {response.status_code}"

    body = response.json()
    assert body.get("code") == 0, f"期望 code=0，实际 {body.get('code')}"
    assert "data" in body, "响应应包含 data"
    assert "tokens" in body["data"], "data 中应包含 tokens"

    tokens = body["data"]["tokens"]
    assert "access_token" in tokens, "tokens 中应包含 access_token"

    parts = tokens["access_token"].split(".")
    assert len(parts) == 3, (
        f"JWT 应为三段 (header.payload.signature)，实际 {len(parts)} 段"
    )


# ===================== 验收 3: 响应时间 <= 1s =====================

def test_github_oauth_callback_response_time(client, db_session):
    """回调处理应在 1 秒内完成"""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        start = time.perf_counter()
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
        elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed <= 1000, f"耗时 {elapsed:.1f}ms 超出 1000ms"


# ===================== 验收 4: 首次登录创建用户 role=viewer =====================

def test_github_oauth_first_login_creates_viewer(client, db_session):
    """首次 OAuth 登录自动创建用户，role 为 viewer

    根因修复：
      - mock httpx.Client 替代 requests
      - 增加 client_id 查询参数
      - 去掉 @pytest.mark.asyncio
    """
    before = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0

    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )

    assert response.status_code == 200

    after = db_session.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    assert after == before + 1, f"应新建 1 条用户 (前={before}, 后={after})"

    row = db_session.execute(
        text("SELECT role FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None, "应存在用户记录"
    assert row[0] == "viewer", f"期望 role=viewer，实际 role={row[0]}"


# ===================== 附加：用户记录含 username + email =====================

def test_github_oauth_user_has_username_and_email(client, db_session):
    """用户记录包含正确的 username 和 email

    根因修复：User 模型无 github_id 列，通过 email 查询
    """
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
    assert row is not None, "应存在用户记录"
    assert row[0] == MOCK_GITHUB_USER_INFO["login"], (
        f"期望 username={MOCK_GITHUB_USER_INFO['login']}，实际 {row[0]}"
    )
    assert row[1] == MOCK_GITHUB_USER_INFO["email"]


# ===================== 附加：重复登录不重复创建 =====================

def test_github_oauth_no_duplicate_on_second_login(client, db_session):
    """同一用户重复登录不会创建重复记录"""
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
    assert count == 1, f"同一 GitHub 账号应只有 1 条记录，实际 {count}"


# ===================== 附加：GitHub token 请求失败 =====================

def test_github_oauth_token_request_failure(client, db_session):
    """token 交换失败时应返回错误"""
    with patch("httpx.Client", return_value=_make_mock_httpx_client_token_fail()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": "bad_code", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code in (400, 401), (
        f"token 请求失败应返回错误，实际 {response.status_code}"
    )


# ===================== 附加：GitHub 用户信息请求失败 =====================

def test_github_oauth_user_info_request_failure(client, db_session):
    """GitHub 用户信息请求失败时应返回错误"""
    with patch("httpx.Client", return_value=_make_mock_httpx_client_user_fail()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code in (400, 401), (
        f"用户信息请求失败应返回错误，实际 {response.status_code}"
    )


# ===================== 附加：code 过期/无效 =====================

def test_github_oauth_expired_code(client, db_session):
    """code 已过期/无效时 token 交换失败"""
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
        f"code 过期应返回错误，实际 {response.status_code}"
    )


# ===================== 附加：缺少 code 返回错误 =====================

def test_github_oauth_missing_code(client, db_session):
    """缺少 code 应返回 422（FastAPI Query 校验）"""
    response = client.get(
        "/api/auth/oauth/github/callback",
        params={"client_id": MOCK_CLIENT_ID},
    )
    assert response.status_code in (400, 422), (
        f"缺少 code 应返回 400/422，实际 {response.status_code}"
    )


# ===================== 附加：响应含 refresh_token + token_type =====================

def test_github_oauth_response_has_refresh_token_and_type(client, db_session):
    """响应包含 refresh_token 和 token_type"""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        response = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert response.status_code == 200

    tokens = response.json()["data"]["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens, "响应应包含 refresh_token"

    tt = tokens.get("token_type", "")
    assert tt.lower() == "bearer", f"期望 token_type=Bearer，实际 {tt}"


# ===================== 附加：access_token 和 refresh_token 均为 JWT =====================

def test_github_oauth_both_tokens_are_jwt(client, db_session):
    """access_token 和 refresh_token 均为三段 JWT 格式"""
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
            f"{name} 应为三段 JWT，实际 {len(parts)} 段"
        )


# ===================== 附加：已存在用户再次登录 =====================

def test_github_oauth_existing_user_relogin(client, db_session):
    """已存在用户再次 OAuth 登录，应返回已有用户而非创建新用户"""
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        r1 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}", "client_id": MOCK_CLIENT_ID},
        )
    assert r1.status_code == 200

    # 记录创建时间
    row = db_session.execute(
        text("SELECT created_at FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row is not None
    created_at = row[0]

    # 第二次登录同一用户
    with patch("httpx.Client", return_value=_make_mock_httpx_client()):
        r2 = client.get(
            "/api/auth/oauth/github/callback",
            params={"code": f"code_{_uid()}_relogin", "client_id": MOCK_CLIENT_ID},
        )
    assert r2.status_code == 200

    # 验证创建时间未改变
    row_after = db_session.execute(
        text("SELECT created_at FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).fetchone()
    assert row_after is not None
    assert row_after[0] == created_at, (
        "再次登录不应改变用户的创建时间"
    )

    # 验证用户数量未增加
    count = db_session.execute(
        text("SELECT COUNT(*) FROM users WHERE email = :email"),
        {"email": MOCK_GITHUB_USER_INFO["email"]},
    ).scalar()
    assert count == 1, f"应只有 1 条用户记录，实际 {count}"


# ===================== 附加：响应包含用户信息 =====================

def test_github_oauth_response_contains_user_info(client, db_session):
    """回调响应包含完整的用户信息"""
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


# ===================== 附加：自定义 redirect_uri =====================

def test_github_oauth_custom_redirect_uri(client):
    """发起 OAuth 时可自定义 redirect_uri"""
    custom_uri = "http://custom.callback.example.com/callback"
    response = client.get(
        "/api/auth/oauth/github",
        params={"client_id": MOCK_CLIENT_ID, "redirect_uri": custom_uri},
    )
    assert response.status_code == 307
    loc = response.headers.get("location", "")
    assert custom_uri in loc, f"应使用自定义 redirect_uri，实际: {loc}"


# ===================== 附加：网络超时 =====================

def test_github_oauth_network_timeout(client, db_session):
    """GitHub API 网络超时时应返回错误"""
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
        f"网络超时应返回错误，实际 {response.status_code}"
    )


# ===================== 附加：GitHub 用户邮箱为空时的处理 =====================

def test_github_oauth_user_no_email(client, db_session):
    """GitHub 用户没有公开邮箱时，系统应生成默认邮箱"""
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
    assert user["email"] is not None, "即使 GitHub 无邮箱，系统也应分配默认邮箱"
    assert "gh_" in user["email"] or "@github.com" in user["email"]