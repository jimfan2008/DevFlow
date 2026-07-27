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
    """验证错误密码登录返回 HTTP 401 + error.code='AUTH-004' + 响应时间 <=200ms + 不创建会话"""

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
    login_payload = {
        "username": email,
        "password": wrong_password,
    }

    start = time.perf_counter()
    response = await client.post("/api/auth/login", json=login_payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # -- 验收标准 (1): HTTP 401 --
    assert response.status_code == 401, (
        f"Expected 401 for wrong password, got {response.status_code}"
    )

    # -- 验收标准 (2): error.code = 'AUTH-004' --
    body = response.json()
    assert "error" in body, "Response body missing 'error' field"
    assert "code" in body["error"], "Response error missing 'code' field"
    assert body["error"]["code"] == "AUTH-004", (
        f"Expected error.code='AUTH-004', got '{body['error'].get('code')}'"
    )

    # -- 验收标准 (3): 响应时间 <=200ms --
    assert elapsed_ms <= 200, (
        f"Response time {elapsed_ms:.1f}ms exceeds 200ms limit"
    )

    # -- 验收标准 (4): 不创建会话 / 数据未被修改 --
    user_count_after = db_session.query(User).count()
    assert user_count_after == user_count_before, (
        f"User count changed: before={user_count_before}, after={user_count_after}. "
        "Wrong password login should NOT create or modify user records."
    )

    db_session.refresh(user)
    assert user.password_hash == original_hash, (
        "Password hash was modified by a failed login attempt."
    )
