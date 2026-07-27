#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - GitHub OAuth 第三方登录 TDD 测试
验证用户通过 GitHub OAuth 授权登录系统的完整流程

验收标准：
  1. HTTP 302/307 重定向至 GitHub 授权页面，回调后 HTTP 200 返回有效 JWT Token
  2. 响应时间 ≤ 1 秒
  3. 用户首次登录自动创建账户，role='viewer'
"""

import pytest
import sys
import os
import time
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

# ── 路径设置 ──────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.config import get_settings
from app.services.auth_service import AuthService
from jose import jwt as pyjwt


# ──────────────────────────────────────────────────────────
# 常量
# ──────────────────────────────────────────────────────────

FAKE_GITHUB_ACCESS_TOKEN = "gho_fake_token_1234567890abcdef"
FAKE_AUTH_CODE = "fake_auth_code_abcdef123456"
GITHUB_CLIENT_ID = "test-github-client-id"
GITHUB_CLIENT_SECRET = "test-github-client-secret"

FAKE_GITHUB_USER_INFO = {
    "id": 99887766,
    "login": "test-github-user",
    "email": "github-user-oauth@example.com",
    "name": "Test GitHub User",
    "avatar_url": "https://avatars.githubusercontent.com/u/99887766?v=4",
}


# ──────────────────────────────────────────────────────────
# 测试数据库 Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_engine():
    """创建独立的内存 SQLite 引擎，整个测试模块共用"""
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    # 清理：逆序删除所有表
    for table in reversed(Base.metadata.sorted_tables):
        try:
            table.drop(engine, checkfirst=True)
        except Exception:
            pass


@pytest.fixture
def db_session(test_engine):
    """每个测试用例获得独立的数据库会话，用后清空所有数据"""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = Session()
    yield session
    # 关闭前：删除所有表数据（commit 过的行无法通过 rollback 清除）
    session.commit()
    for table in reversed(Base.metadata.sorted_tables):
        try:
            session.execute(table.delete())
        except Exception:
            pass
    session.commit()
    session.close()


@pytest.fixture
def client(db_session):
    """FastAPI TestClient，注入测试数据库会话"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, follow_redirects=False) as tc:
        yield tc

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────
# Mock GitHub OAuth HTTP 请求
# ──────────────────────────────────────────────────────────

def _mock_github_token_exchange(request):
    """模拟 GitHub OAuth: 授权码换取 access_token"""
    return (200, {"content-type": "application/json"},
            '{"access_token":"' + FAKE_GITHUB_ACCESS_TOKEN + '", "token_type": "bearer", "scope": ""}')


def _mock_github_user_info(request):
    """模拟 GitHub API: 获取用户信息"""
    import json
    return (200, {"content-type": "application/json"},
            json.dumps(FAKE_GITHUB_USER_INFO))


def _mock_github_token_error(request):
    """模拟 GitHub OAuth: 换取 token 失败"""
    return (200, {"content-type": "text/plain"},
            "error=bad_verification&error_description=bad+credentials")


def _mock_github_api_error(request):
    """模拟 GitHub API: 获取用户信息失败"""
    import json
    return (500, {"content-type": "application/json"},
            json.dumps({"message": "Internal Server Error"}))


@pytest.fixture
def with_github_mock_success(monkeypatch):
    """Mock 成功的 GitHub OAuth 全流程"""
    import httpx as _httpx

    original_request = _httpx.Client.request

    def fake_request(self, method, url, **kwargs):
        if "github.com/login/oauth/access_token" in str(url):
            return _httpx.Response(200, json={
                "access_token": FAKE_GITHUB_ACCESS_TOKEN,
                "token_type": "bearer",
                "scope": "",
            })
        if "api.github.com/user" in str(url):
            return _httpx.Response(200, json=FAKE_GITHUB_USER_INFO)
        return original_request(self, method, url, **kwargs)

    monkeypatch.setattr(_httpx.Client, "request", fake_request)


@pytest.fixture
def with_github_mock_token_error(monkeypatch):
    """Mock GitHub OAuth token 交换失败"""
    import httpx as _httpx

    original_request = _httpx.Client.request

    def fake_request(self, method, url, **kwargs):
        if "github.com/login/oauth/access_token" in str(url):
            return _httpx.Response(200, text="error=bad_verification&error_description=bad+credentials")
        return original_request(self, method, url, **kwargs)

    monkeypatch.setattr(_httpx.Client, "request", fake_request)


@pytest.fixture
def with_github_mock_api_error(monkeypatch):
    """Mock GitHub API 获取用户信息失败"""
    import httpx as _httpx

    original_request = _httpx.Client.request

    def fake_request(self, method, url, **kwargs):
        if "github.com/login/oauth/access_token" in str(url):
            return _httpx.Response(200, json={
                "access_token": FAKE_GITHUB_ACCESS_TOKEN,
                "token_type": "bearer",
                "scope": "",
            })
        if "api.github.com/user" in str(url):
            return _httpx.Response(500, json={"message": "Internal Server Error"})
        return original_request(self, method, url, **kwargs)

    monkeypatch.setattr(_httpx.Client, "request", fake_request)


# ──────────────────────────────────────────────────────────
# 环境配置 Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def set_github_env(monkeypatch):
    """所有测试自动注入 GitHub OAuth 环境变量"""
    monkeypatch.setenv("GITHUB_CLIENT_ID", GITHUB_CLIENT_ID)
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", GITHUB_CLIENT_SECRET)


# ──────────────────────────────────────────────────────────
# 核心测试类：GitHub OAuth 第三方登录
# ──────────────────────────────────────────────────────────

class TestGitHubOAuthInitiate:
    """
    测试 OAuth 发起流程
    验证标准 1: HTTP 302/307 重定向至 GitHub 授权页面
    """

    def test_oauth_initiate_returns_redirect(self, client):
        """发起 GitHub OAuth 登录 -> 返回 307 重定向"""
        resp = client.get(f"/api/auth/oauth/github?client_id={GITHUB_CLIENT_ID}")

        assert resp.status_code in (302, 307), \
            f"期望 302 或 307，实际 {resp.status_code}"

    def test_redirect_url_contains_github_authorize_endpoint(self, client):
        """重定向地址必须指向 GitHub 授权端点"""
        resp = client.get(f"/api/auth/oauth/github?client_id={GITHUB_CLIENT_ID}")

        location = resp.headers.get("location", "")
        assert "github.com/login/oauth/authorize" in location, \
            f"重定向地址未包含 GitHub 授权端点: {location}"

    def test_redirect_url_contains_client_id(self, client):
        """重定向地址必须包含 client_id 参数"""
        resp = client.get(f"/api/auth/oauth/github?client_id={GITHUB_CLIENT_ID}")

        location = resp.headers.get("location", "")
        assert f"client_id={GITHUB_CLIENT_ID}" in location, \
            f"重定向地址未包含正确的 client_id: {location}"

    def test_redirect_url_contains_callback_redirect_uri(self, client):
        """重定向地址必须包含本项目回调地址"""
        resp = client.get(f"/api/auth/oauth/github?client_id={GITHUB_CLIENT_ID}")

        location = resp.headers.get("location", "")
        # 回调地址应包含 github/callback 或 oauth/callback
        assert "github/callback" in location or "oauth/callback" in location, \
            f"重定向地址未包含回调 redirect_uri: {location}"

    def test_redirect_url_contains_state_parameter(self, client):
        """重定向地址必须包含 state 参数（CSRF 防护）"""
        resp = client.get(f"/api/auth/oauth/github?client_id={GITHUB_CLIENT_ID}")

        location = resp.headers.get("location", "")
        assert "state=" in location, \
            f"重定向地址未包含 state 参数: {location}"

    def test_redirect_url_contains_scope_parameter(self, client):
        """重定向地址应包含 scope 参数（请求的权限范围）"""
        resp = client.get(f"/api/auth/oauth/github?client_id={GITHUB_CLIENT_ID}")

        location = resp.headers.get("location", "")
        assert "scope=" in location, \
            f"重定向地址未包含 scope 参数: {location}"


class TestGitHubOAuthCallback:
    """
    测试 OAuth 回调流程
    验收标准 2: 回调后 HTTP 200 返回有效 JWT Token
    """

    def test_callback_returns_200_with_valid_response(self, client, with_github_mock_success):
        """回调成功 -> HTTP 200"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        assert resp.status_code == 200

    def test_callback_response_contains_jwt_tokens(self, client, with_github_mock_success):
        """回调成功 -> 响应体包含 access_token 和 refresh_token"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        data = resp.json()
        assert data["code"] == 0
        assert "tokens" in data.get("data", {})
        tokens = data["data"]["tokens"]
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "Bearer"

    def test_access_token_is_valid_jwt(self, client, with_github_mock_success):
        """返回的 access_token 必须是有效的 JWT"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        tokens = resp.json()["data"]["tokens"]
        access_token = tokens["access_token"]

        settings = get_settings()
        decoded = pyjwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert "sub" in decoded, "JWT 缺少 sub 声明"
        assert "exp" in decoded, "JWT 缺少 exp 声明"
        assert decoded["type"] == "access", "JWT type 应为 access"

    def test_token_sub_matches_created_user_id(self, client, db_session, with_github_mock_success):
        """JWT 的 sub 字段必须等于数据库中创建的用户 ID"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        tokens = resp.json()["data"]["tokens"]
        access_token = tokens["access_token"]
        settings = get_settings()

        decoded = pyjwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = decoded["sub"]

        # 验证该用户存在于数据库
        user = db_session.query(User).filter(User.id == user_id).first()
        assert user is not None, "JWT sub 对应的用户不存在于数据库"
        assert user.id == user_id

    def test_callback_returns_user_info(self, client, with_github_mock_success):
        """回调成功 -> 响应体包含用户信息"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        data = resp.json()
        assert data["code"] == 0
        user_data = data["data"]["user"]
        assert "id" in user_data
        assert "username" in user_data
        assert "email" in user_data
        assert "role" in user_data

    def test_callback_response_time_under_1_second(self, client, with_github_mock_success):
        """回调响应时间 ≤ 1 秒"""
        start = time.perf_counter()
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 1.0, f"响应时间 {elapsed:.3f}s 超过 1 秒上限"

    def test_callback_missing_code_returns_400_or_422(self, client):
        """缺少 code 参数 -> 返回 400 或 422"""
        resp = client.get("/api/auth/oauth/github/callback")

        assert resp.status_code in (400, 422)

    def test_callback_invalid_auth_code_returns_error(self, client, with_github_mock_token_error):
        """无效的授权码 -> 返回错误"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code=invalid_bad_code&client_id={GITHUB_CLIENT_ID}"
        )

        assert resp.status_code in (400, 401, 500)

    def test_callback_github_api_failure_returns_error(self, client, with_github_mock_api_error):
        """GitHub API 调用失败 -> 返回错误而非崩溃"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        assert resp.status_code != 200


class TestGitHubOAuthUserCreation:
    """
    测试首次登录自动创建用户
    验收标准 3: 首次登录自动创建账户，role='viewer'
    """

    def test_first_login_creates_new_user(self, client, db_session, with_github_mock_success):
        """首次 OAuth 登录 -> 自动创建用户记录"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        # 确认用户不存在
        existing = db_session.query(User).filter(User.email == github_email).first()
        assert existing is None, "测试前该用户应不存在"

        # 执行 OAuth 登录
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )
        assert resp.status_code == 200

        # 验证用户已创建
        user = db_session.query(User).filter(User.email == github_email).first()
        assert user is not None, "首次登录后用户应被自动创建"

    def test_new_user_has_viewer_role(self, client, db_session, with_github_mock_success):
        """新创建的用户角色必须是 'viewer'"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )
        assert resp.status_code == 200

        user = db_session.query(User).filter(User.email == github_email).first()
        assert user.role == "viewer", f"新用户角色应为 'viewer'，实际: {user.role}"

    def test_response_user_also_has_viewer_role(self, client, with_github_mock_success):
        """响应体中返回的用户信息也必须是 'viewer' 角色"""
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        user_data = resp.json()["data"]["user"]
        assert user_data["role"] == "viewer"

    def test_new_user_has_auto_generated_username(self, client, db_session, with_github_mock_success):
        """新用户应自动生成用户名"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )
        assert resp.status_code == 200

        user = db_session.query(User).filter(User.email == github_email).first()
        assert user.username is not None
        assert len(user.username) > 0

    def test_new_user_has_github_avatar_url(self, client, db_session, with_github_mock_success):
        """新用户应从 GitHub 获取头像 URL"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )
        assert resp.status_code == 200

        user = db_session.query(User).filter(User.email == github_email).first()
        assert user.avatar_url == FAKE_GITHUB_USER_INFO["avatar_url"]


class TestGitHubOAuthExistingUser:
    """
    测试已存在用户再次通过 GitHub OAuth 登录
    """

    def test_existing_user_returns_same_user(self, client, db_session, with_github_mock_success):
        """已存在的用户再次登录 -> 返回该用户，不创建新记录"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        # 先手动创建用户（模拟已有账户）
        existing_user = User(
            id=str(uuid.uuid4()),
            username="existing-github-user",
            email=github_email,
            password_hash=AuthService(db_session).hash_password("SecurePass1!"),
            role="admin",
        )
        db_session.add(existing_user)
        db_session.commit()
        original_id = existing_user.id
        original_role = existing_user.role

        # 通过 OAuth 登录
        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        assert resp.status_code == 200
        user_data = resp.json()["data"]["user"]
        assert user_data["id"] == original_id, "应返回原有用户 ID"
        assert user_data["role"] == original_role, "原有角色不应被覆盖"

    def test_existing_user_role_not_downgraded(self, client, db_session, with_github_mock_success):
        """已有用户角色不应被降级为 viewer"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        existing_user = User(
            id=str(uuid.uuid4()),
            username="admin-github-user",
            email=github_email,
            password_hash=AuthService(db_session).hash_password("SecurePass1!"),
            role="admin",
        )
        db_session.add(existing_user)
        db_session.commit()

        resp = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        user_data = resp.json()["data"]["user"]
        assert user_data["role"] == "admin", "管理员角色不应被降级"

    def test_no_duplicate_user_created(self, client, db_session, with_github_mock_success):
        """同一邮箱不应创建重复用户"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        # 先创建用户
        existing_user = User(
            id=str(uuid.uuid4()),
            username="pre-existing-user",
            email=github_email,
            password_hash=AuthService(db_session).hash_password("SecurePass1!"),
            role="admin",
        )
        db_session.add(existing_user)
        db_session.commit()

        # 通过 OAuth 登录
        client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )

        # 数据库中仍只有 1 条记录
        count = db_session.query(User).filter(User.email == github_email).count()
        assert count == 1, f"不应有重复用户，实际: {count}"


class TestGitHubOAuthIdempotency:
    """
    测试 OAuth 流程的幂等性
    """

    def test_same_auth_code_used_twice_returns_existing_user(
        self, client, db_session, with_github_mock_success
    ):
        """同一授权码使用两次 -> 第二次也成功，返回同一用户"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        # 第一次
        resp1 = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )
        assert resp1.status_code == 200
        user_id_1 = resp1.json()["data"]["user"]["id"]

        # 第二次
        resp2 = client.get(
            f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
        )
        assert resp2.status_code == 200
        user_id_2 = resp2.json()["data"]["user"]["id"]

        assert user_id_1 == user_id_2, "两次登录应返回同一用户"

    def test_multiple_logins_create_only_one_user(self, client, db_session, with_github_mock_success):
        """多次 OAuth 登录只创建一条用户记录"""
        github_email = FAKE_GITHUB_USER_INFO["email"]

        for _ in range(3):
            resp = client.get(
                f"/api/auth/oauth/github/callback?code={FAKE_AUTH_CODE}&client_id={GITHUB_CLIENT_ID}"
            )
            assert resp.status_code == 200

        count = db_session.query(User).filter(User.email == github_email).count()
        assert count == 1, f"3 次登录只应创建 1 条用户记录，实际: {count}"
