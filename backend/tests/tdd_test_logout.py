#!/usr/bin/env python3
"""
"""
import pytest
import pytest_asyncio
import time
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport
from typing import Set


# ── 测试数据(内联,不依赖外部文件) ───────────────────────
TEST_USER_DATA = {
    "id": "tdd_test_user_0008",
    "username": "logout_tester",
    "email": "logout_test@devflow.test",
    "password": "TestPass123",
    "role": "user",
}

TEST_LOGIN_PAYLOAD = {
    "username": TEST_USER_DATA["username"],
    "password": TEST_USER_DATA["password"],
}

# ── In-Memory Token Blacklist (替代 Redis) ──────────────
_blacklisted_tokens: Set[str] = set()


def _mock_add_to_blacklist(token: str, expire_seconds: int = None) -> bool:
    _blacklisted_tokens.add(token)
    return True


def _mock_is_blacklisted(token: str) -> bool:
    return token in _blacklisted_tokens


def _mock_remove_from_blacklist(token: str) -> bool:
    _blacklisted_tokens.discard(token)
    return True


def _mock_blacklist_size() -> int:
    return len(_blacklisted_tokens)


# ── 数据库与 App 设置 ─────────────────────────────────────
from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.utils.security import get_password_hash
from fastapi import Header, Depends
from sqlalchemy.orm import Session

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)


def teardown_database():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


def _create_test_user(session):
    """在测试数据库中创建测试用户"""
    user = User(
        id=TEST_USER_DATA["id"],
        username=TEST_USER_DATA["username"],
        email=TEST_USER_DATA["email"],
        password_hash=get_password_hash(TEST_USER_DATA["password"]),
        role=TEST_USER_DATA["role"],
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ── 自定义 get_current_user(含黑名单检查) ───────────────
def get_current_user_with_blacklist(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """替换 get_current_user 依赖，加入黑名单检查"""
    from fastapi import HTTPException, status
    from app.services.auth_service import AuthService

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )
    token = authorization.split(" ", 1)[1]

    # 黑名单检查
    if _mock_is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    auth_service = AuthService(db=db)
    user_id = auth_service.verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ── Fixtures ──────────────────────────────────────────────
@pytest.fixture(scope="module")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    setup_database()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        teardown_database()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    user = _create_test_user(db_session)
    yield user


@pytest_asyncio.fixture(scope="function")
async def client(db_session, test_user):
    """提供测试 HTTP 客户端，同时 patch jwt_blacklist 与 dependencies"""
    _blacklisted_tokens.clear()

    # 补丁: jwt_blacklist 模块函数 → 使用内存集合(字符串路径 patch，避免模块不存在时 import 失败)
    blacklist_patches = [
        patch("app.middleware.jwt_blacklist.add_to_blacklist", side_effect=_mock_add_to_blacklist),
        patch("app.middleware.jwt_blacklist.is_blacklisted", side_effect=_mock_is_blacklisted),
        patch("app.middleware.jwt_blacklist.remove_from_blacklist", side_effect=_mock_remove_from_blacklist),
        patch("app.middleware.jwt_blacklist.blacklist_size", side_effect=_mock_blacklist_size),
    ]

    # 补丁: get_db 依赖 → 使用测试 session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # 补丁: get_current_user → 含黑名单检查版本(惰性导入，避免 import 级联失败)
    from app.dependencies import get_current_user as api_get_current_user
    app.dependency_overrides[api_get_current_user] = get_current_user_with_blacklist

    for p in blacklist_patches:
        p.start()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac

    for p in blacklist_patches:
        p.stop()
    app.dependency_overrides.clear()
    _blacklisted_tokens.clear()


# ═══════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════
@pytest.mark.asyncio
class TestManualLogout:
    """手动登出 TDD 测试"""

    async def _login_and_get_token(self, client: AsyncClient) -> str:
        """辅助方法: 登录并返回 access_token"""
        resp = await client.post("/api/auth/login", json=TEST_LOGIN_PAYLOAD)
        assert resp.status_code == 200, f"登录失败: {resp.text}"
        body = resp.json()
        assert body["code"] == 0
        return body["data"]["tokens"]["access_token"]

    async def _login_as_user(self, client: AsyncClient, username: str, password: str) -> str:
        """辅助方法: 以指定用户登录并返回 access_token"""
        resp = await client.post("/api/auth/login", json={
            "username": username,
            "password": password,
        })
        assert resp.status_code == 200, f"登录失败: {resp.text}"
        body = resp.json()
        assert body["code"] == 0
        return body["data"]["tokens"]["access_token"]

    async def test_logout_returns_200(self, client: AsyncClient):
        """验收标准1: HTTP 200 响应"""
        token = await self._login_and_get_token(client)
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "Logout successful"

    @pytest.mark.slow
    async def test_logout_response_time_within_200ms(self, client: AsyncClient):
        """验收标准2: 响应时间 <=200ms (标记为 slow 以避免 CI 假阳性)"""
        token = await self._login_and_get_token(client)
        start = time.perf_counter()
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200, f"登出失败: {resp.text}"
        assert elapsed_ms <= 200, f"响应时间 {elapsed_ms:.1f}ms 超过 200ms 阈值"

    async def test_jwt_token_invalidated_after_logout(self, client: AsyncClient):
        """验收标准3: JWT Token 失效 -- 登出后使用相同 token 请求应返回 401"""
        token = await self._login_and_get_token(client)

        # 验证 token 登出前可用
        resp_before = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_before.status_code == 200, "登出前 token 应有效"

        # 执行登出
        resp_logout = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_logout.status_code == 200

        # 使用同一 token 再次请求 -> 应 401
        resp_after = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_after.status_code == 401, (
            f"登出后使用相同 token 应返回 401，实际状态码: {resp_after.status_code}"
        )
        body = resp_after.json()
        detail = body.get("detail", body.get("message", ""))
        assert "revoked" in detail.lower() or "invalid" in detail.lower() or "unauthorized" in detail.lower(), (
            f"错误信息应提示 token 已失效: {detail}"
        )

    async def test_redirect_to_login_page(self, client: AsyncClient):
        """验收标准4: 重定向至登录页面(前端路由约定 /login)"""
        token = await self._login_and_get_token(client)
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        # 后端登出响应应包含 data.redirect_url 指示前端跳转
        data = body.get("data")
        assert isinstance(data, dict), f"登出响应 data 应为 dict，实际: {type(data)}"
        redirect_url = data.get("redirect_url", "")
        assert redirect_url and "/login" in redirect_url, (
            f"登出响应应包含 redirect_url 指向 /login，实际: {redirect_url}"
        )

    async def test_token_blacklisted_after_logout(self, client: AsyncClient):
        """验收标准5: 登出后 token 被加入黑名单(等价于 Redis session 被删除)"""
        token = await self._login_and_get_token(client)

        # 登出前: token 不应在黑名单中
        assert not _mock_is_blacklisted(token), "登出前 token 不应在黑名单"

        # 执行登出
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        # 登出后: token 应在黑名单中(等价于 Redis session 被删除)
        assert _mock_is_blacklisted(token), "登出后 token 应加入黑名单"

    async def test_consecutive_logout_idempotent(self, client: AsyncClient):
        """边界: 重复登出应幂等 -- 第二次登出仍返回 200"""
        token = await self._login_and_get_token(client)

        # 第一次登出
        resp1 = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 200

        # 第二次登出(已失效 token 再次登出应返回 200，保持幂等)
        resp2 = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200, (
            f"重复登出应保持幂等返回 200，实际: {resp2.status_code}"
        )

    async def test_logout_without_token_returns_401(self, client: AsyncClient):
        """边界: 未携带 token 调用登出应返回 401"""
        resp = await client.post(
            "/api/auth/logout",
            headers={},
        )
        assert resp.status_code == 401
        body = resp.json()
        detail = body.get("detail", body.get("message", ""))
        assert "missing" in detail.lower() or "unauthorized" in detail.lower(), (
            f"缺少 token 时应提示未授权: {detail}"
        )

    # ── 新增边界测试: 空 token 字符串 ─────────────────────────
    async def test_logout_with_empty_bearer_token(self, client: AsyncClient):
        """边界: Authorization 头为 'Bearer ' (空 token) 应返回 401"""
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401
        body = resp.json()
        detail = body.get("detail", body.get("message", ""))
        assert "missing" in detail.lower() or "unauthorized" in detail.lower() or "invalid" in detail.lower(), (
            f"空 token 时应提示未授权，实际: {detail}"
        )

    # ── 新增边界测试: 格式错误的 token ───────────────────────
    async def test_logout_with_malformed_token(self, client: AsyncClient):
        """边界: 非 JWT 格式的 token 应返回 401"""
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer not-a-valid-jwt-token-string"},
        )
        assert resp.status_code == 401
        body = resp.json()
        detail = body.get("detail", body.get("message", ""))
        assert "invalid" in detail.lower() or "unauthorized" in detail.lower() or "expired" in detail.lower(), (
            f"格式错误的 token 时应提示无效，实际: {detail}"
        )

    # ── 新增边界测试: 已过期 token ───────────────────────────
    async def test_logout_with_expired_token(self, client: AsyncClient):
        """边界: 使用已过期 token 登出应返回 401"""
        from app.utils.security import create_access_token
        from datetime import timedelta

        # 创建一个已过期 token
        expired_token = create_access_token(
            data={"sub": TEST_USER_DATA["id"]},
            expires_delta=timedelta(seconds=-1),
        )
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
        body = resp.json()
        detail = body.get("detail", body.get("message", ""))
        assert "expired" in detail.lower() or "invalid" in detail.lower() or "unauthorized" in detail.lower(), (
            f"过期 token 时应提示已过期，实际: {detail}"
        )

    # ── 新增边界测试: 其他用户的 token ───────────────────────
    async def test_other_user_token_unaffected(self, client: AsyncClient, db_session):
        """边界: 用户 A 登出不影响用户 B 的 token"""
        # 创建第二个测试用户
        user_b_data = {
            "id": "tdd_test_user_0008_b",
            "username": "logout_tester_b",
            "email": "logout_test_b@devflow.test",
            "password": "UserBPass123",
            "role": "user",
        }
        user_b = User(
            id=user_b_data["id"],
            username=user_b_data["username"],
            email=user_b_data["email"],
            password_hash=get_password_hash(user_b_data["password"]),
            role=user_b_data["role"],
        )
        db_session.add(user_b)
        db_session.commit()

        # 用户 A 登录
        token_a = await self._login_as_user(
            client, TEST_USER_DATA["username"], TEST_USER_DATA["password"]
        )
        # 用户 B 登录
        token_b = await self._login_as_user(
            client, user_b_data["username"], user_b_data["password"]
        )

        # 用户 A 登出
        resp_a_logout = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a_logout.status_code == 200

        # 用户 A 的 token 应失效
        resp_a_after = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a_after.status_code == 401, "用户 A 登出后其 token 应失效"

        # 用户 B 的 token 应仍然有效
        resp_b_after = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b_after.status_code == 200, "用户 B 的 token 应不受用户 A 登出影响"
