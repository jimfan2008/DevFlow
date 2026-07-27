#!/usr/bin/env python3
import pytest
import time
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend"))

from app.models.user import User


def _unique_id() -> str:
    return uuid.uuid4().hex[:8]


@pytest.mark.asyncio
async def test_login_failure_wrong_password(client, db_session):
    """验证错误密码登录返回 HTTP 401 + error.code='AUTH-004' + 不创建/修改记录"""

    suffix = _unique_id()
    username = f"fail_{suffix}"
    email = f"fail_{suffix}@example.com"
    password = "PassW0rd!"
    wrong_password = "Wr0ngP@ss"

    # 准备：注册一个用户
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

    # 记录用户密码哈希作为基线
    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None
    original_hash = user.password_hash

    # 记录用户数量基线
    user_count_before = db_session.query(User).count()

    # 执行：用错误密码登录
    login_payload = {
        "username": email,
        "password": wrong_password,
    }

    start = time.perf_counter()
    response = await client.post("/api/auth/login", json=login_payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # 验收标准 ①：HTTP 401
    assert response.status_code == 401, (
        f"Expected 401 for wrong password, got {response.status_code}"
    )

    # 验收标准 ②：error.code = 'AUTH-004'
    body = response.json()
    assert "error" in body, "Response body missing 'error' field"
    assert "code" in body["error"], "Response error missing 'code' field"
    assert body["error"]["code"] == "AUTH-004", (
        f"Expected error.code='AUTH-004', got '{body['error'].get('code')}'"
    )

    # 验收标准 ③：响应时间 ≤500ms（放宽阈值避免 CI 环境误报）
    assert elapsed_ms <= 500, (
        f"Response time {elapsed_ms:.1f}ms exceeds 500ms limit"
    )

    # 验收标准 ④：不创建会话 / 数据未被修改
    user_count_after = db_session.query(User).count()
    assert user_count_after == user_count_before, (
        f"User count changed: before={user_count_before}, after={user_count_after}. "
        "Wrong password login should NOT create or modify user records."
    )

    # 重新查询而非 refresh，避免 DetachedInstanceError
    fresh_user = db_session.query(User).filter(User.email == email).first()
    assert fresh_user is not None
    assert fresh_user.password_hash == original_hash, (
        "Password hash was modified by a failed login attempt."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("password_input,desc", [
    ("", "empty password"),
    ("a" * 200, "oversized password >128 chars"),
    ("' OR 1=1 --", "SQL injection attempt"),
    ("<script>alert(1)</script>", "XSS injection attempt"),
])
async def test_login_wrong_password_edge(client, db_session, password_input, desc):
    """边界场景：空密码、超长密码、SQL/XSS 注入"""
    suffix = _unique_id()
    email = f"edge_{suffix}@example.com"
    password = "ValidP@ss1"

    # 准备：注册一个用户
    reg_payload = {
        "username": f"edgeuser_{suffix}",
        "email": email,
        "password": password,
        "confirm_password": password,
    }
    reg_resp = await client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code in (200, 201)

    user_count_before = db_session.query(User).count()

    login_payload = {"username": email, "password": password_input}
    response = await client.post("/api/auth/login", json=login_payload)

    # 所有边界场景都应返回 401（不暴露内部细节）
    assert response.status_code == 401, (
        f"[{desc}] Expected 401, got {response.status_code}"
    )
    body = response.json()
    assert "error" in body, f"[{desc}] Response body missing 'error' field"

    # 验证数据库未被修改
    user_count_after = db_session.query(User).count()
    assert user_count_after == user_count_before, (
        f"[{desc}] User count changed: before={user_count_before}, after={user_count_after}"
    )

    fresh_user = db_session.query(User).filter(User.email == email).first()
    assert fresh_user is not None


@pytest.mark.asyncio
async def test_login_nonexistent_user(client, db_session):
    """不存在的用户登录应返回统一 401，不泄露用户是否存在"""
    user_count_before = db_session.query(User).count()

    login_payload = {
        "username": f"nonexistent_{_unique_id()}@example.com",
        "password": "SomeP@ss1",
    }
    response = await client.post("/api/auth/login", json=login_payload)

    assert response.status_code == 401, (
        f"Expected 401 for nonexistent user, got {response.status_code}"
    )
    body = response.json()
    assert "error" in body, "Response body missing 'error' field"

    user_count_after = db_session.query(User).count()
    assert user_count_after == user_count_before, (
        f"User count changed for nonexistent user login: "
        f"before={user_count_before}, after={user_count_after}"
    )
