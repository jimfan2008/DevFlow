import pytest
import time
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.models.user import User


def _unique_id() -> str:
    return uuid.uuid4().hex[:8]


@pytest.mark.asyncio
async def test_login_failure_wrong_password(client, db_session):
    """验证错误密码登录返回 HTTP 401 + error.code='AUTH-004' + 不创建会话"""

    suffix = _unique_id()
    username = f"fail_{suffix}"
    email = f"fail_{suffix}@example.com"
    password = "PassW0rd!"
    wrong_password = "Wr0ngP@ss"

    # -- 准备：注册一个用户 --
    register_payload = {
        "username": username,
        "email": email,
        "password": password,
        "confirm_password": password,
    }
    reg_resp = await client.post("/api/auth/register", json=register_payload)
    assert reg_resp.status_code in (200, 201), (
        f"Precondition failed: register returned {reg_resp.status_code}"
    )

    # -- 记录用户密码哈希作为基线 --
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None
    original_hash = user.password_hash

    # -- 记录用户数量基线 --
    user_count_before = db_session.query(User).count()

    # -- 执行：用错误密码登录 --
    # 使用 email 字段（LoginRequest 支持 username / email 分别传入）
    login_payload = {
        "email": email,
        "password": wrong_password,
    }

    response = await client.post("/api/auth/login", json=login_payload)

    # -- 验收标准 (1)：HTTP 401 --
    assert response.status_code == 401, (
        f"Expected 401 for wrong password, got {response.status_code}"
    )

    # -- 验收标准 (2)：error.code = 'AUTH-004' --
    body = response.json()
    assert "code" in body, "Response body missing 'code' field"
    assert body["code"] == "AUTH-004", (
        f"Expected error.code='AUTH-004', got '{body.get('code')}'"
    )

    # -- 验收标准 (3)：响应时间 <=200ms --
    # 硬编码时间断言从功能测试中移除（CI 环境下 flaky），移至 @pytest.mark.benchmark 测试

    # -- 验收标准 (4)：不创建会话 / 数据未被修改 --
    user_count_after = db_session.query(User).count()
    assert user_count_after == user_count_before, (
        f"User count changed: before={user_count_before}, after={user_count_after}. "
        "Wrong password login should NOT create or modify user records."
    )

    db_session.refresh(user)
    assert user.password_hash == original_hash, (
        "Password hash was modified by a failed login attempt."
    )


# -- 边界覆盖：异常密码值 --------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("wrong_password", [
    "",
    "A" * 1024,
    "' OR 1=1 --",
    "pässwörd🔐123",
    "PASSW0RD!",
], ids=[
    "empty_password",
    "oversized_1024_chars",
    "sql_injection_payload",
    "unicode_with_emoji",
    "correct_password_wrong_case",
])
async def test_login_failure_boundary(wrong_password, client, db_session):
    """边界测试：各种异常密码值应返回 401"""
    suffix = _unique_id()
    username = f"bnd_{suffix}"
    email = f"bnd_{suffix}@example.com"
    password = "PassW0rd!"

    register_payload = {
        "username": username,
        "email": email,
        "password": password,
        "confirm_password": password,
    }
    reg_resp = await client.post("/api/auth/register", json=register_payload)
    assert reg_resp.status_code in (200, 201), (
        f"Precondition failed: register returned {reg_resp.status_code}"
    )

    login_payload = {"email": email, "password": wrong_password}
    response = await client.post("/api/auth/login", json=login_payload)

    assert response.status_code == 401, (
        f"Expected 401 for password={wrong_password!r}, got {response.status_code} {response.text}"
    )


@pytest.mark.asyncio
async def test_login_failure_nonexistent_user(client, db_session):
    """双重错误：用户名不存在 + 错误密码"""
    login_payload = {
        "email": f"nobody_{_unique_id()}@example.com",
        "password": "SomeP@ss123",
    }
    response = await client.post("/api/auth/login", json=login_payload)

    assert response.status_code == 401, (
        f"Expected 401 for nonexistent user, got {response.status_code}"
    )


# -- 性能基准测试（单独标记，允许可配置阈值） -----------------


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_login_failure_response_time_within_200ms(client, db_session):
    """性能基准：错误密码登录响应时间 ≤200ms（与功能测试分离，避免 flaky）"""
    suffix = _unique_id()
    username = f"perf_{suffix}"
    email = f"perf_{suffix}@example.com"
    password = "PassW0rd!"

    register_payload = {
        "username": username,
        "email": email,
        "password": password,
        "confirm_password": password,
    }
    reg_resp = await client.post("/api/auth/register", json=register_payload)
    assert reg_resp.status_code in (200, 201)

    login_payload = {"email": email, "password": "Wr0ngP@ss"}

    start = time.perf_counter()
    await client.post("/api/auth/login", json=login_payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms <= 200, (
        f"Response time {elapsed_ms:.1f}ms exceeds 200ms limit"
    )
