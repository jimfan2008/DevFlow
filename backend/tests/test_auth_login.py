#!/usr/bin/env python3
"""
测试套件：登录认证
TDD 测试用例 — 登录失败（错误密码）
"""

import time
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.utils.security import get_password_hash
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

# ── 本地内存数据库，隔离运行 ─────────────────────────────

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)


def teardown_db():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    setup_db()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        teardown_db()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def existing_user(db_session):
    """预置已注册用户（密码：CorrectPass1）"""
    user = User(
        id="user_test_auth_001",
        username="auth_test_user",
        email="auth_test@example.com",
        password_hash=get_password_hash("CorrectPass1"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    try:
        db_session.rollback()
        db_session.delete(user)
        db_session.commit()
    except Exception:
        db_session.rollback()


# ═══════════════════════════════════════════════════════════
# 测试用例：登录失败——错误密码
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.tdd
class TestLoginWrongPassword:
    """验证输入错误密码时返回认证失败响应"""

    async def test_returns_401_on_wrong_password(self, client, existing_user):
        """使用错误密码登录应返回 HTTP 401"""
        payload = {"username": "auth_test_user", "password": "WrongPass999"}
        response = await client.post("/api/auth/login", json=payload)

        assert response.status_code == 401, (
            f"期望 401，实际得到 {response.status_code}: {response.text}"
        )

    async def test_response_contains_auth004_error_code(self, client, existing_user):
        """错误响应体包含 error.code='AUTH-004'"""
        payload = {"username": "auth_test_user", "password": "WrongPass999"}
        response = await client.post("/api/auth/login", json=payload)
        body = response.json()

        # 验收标准：层级路径 error.code == "AUTH-004"
        assert "error" in body, f"响应体缺少 'error' 字段: {body}"
        assert body["error"].get("code") == "AUTH-004", (
            f"期望 error.code='AUTH-004'，实际得到: {body['error'].get('code')}"
        )

    async def test_response_time_within_200ms(self, client, existing_user):
        """响应时间不超过 200ms"""
        payload = {"username": "auth_test_user", "password": "WrongPass999"}
        start = time.perf_counter()
        await client.post("/api/auth/login", json=payload)
        elapsed = time.perf_counter() - start

        assert elapsed <= 0.2, f"响应超时: {elapsed:.3f}s > 200ms"

    async def test_no_session_created_on_failure(self, client, existing_user):
        """登录失败后响应中不包含令牌，即不创建会话"""
        payload = {"username": "auth_test_user", "password": "WrongPass999"}
        response = await client.post("/api/auth/login", json=payload)
        body = response.json()

        # 不应返回任何会话凭证
        for token_field in ("access_token", "refresh_token", "token"):
            assert token_field not in body, (
                f"错误登录响应不应包含 '{token_field}': {body}"
            )

        # data 字段不应包含 tokens
        data = body.get("data")
        if data is not None:
            if isinstance(data, dict):
                assert "tokens" not in data, f"错误登录响应 data 中不应包含 tokens: {data}"
                assert "access_token" not in data, f"错误登录响应 data 中不应包含 access_token: {data}"
