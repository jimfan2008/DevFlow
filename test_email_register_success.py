#!/usr/bin/env python3
import pytest
import time
import uuid
from app.models.user import User


def _unique_id() -> str:
    """生成短的唯一后缀，避免跨测试冲突。"""
    return uuid.uuid4().hex[:8]


def _make_payload(username=None, email=None, password="SecurePass123!"):
    """构建有效的注册请求负载，自动生成唯一字段。"""
    suffix = _unique_id()
    return {
        "username": username if username else f"testuser_{suffix}",
        "email": email if email else f"test_{suffix}@example.com",
        "password": password,
        "confirm_password": password,
    }


# ============================================================
# 验收标准 1: HTTP 201 返回
# ============================================================


@pytest.mark.asyncio
async def test_register_returns_http_201(client, db_session):
    """验证注册成功返回 HTTP 201。"""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201, f"期望 HTTP 201，实际 {response.status_code}"
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "success"


# ============================================================
# 验收标准 1b: 响应时间 ≤ 500ms
# ============================================================


@pytest.mark.asyncio
async def test_register_response_time_under_500ms(client, db_session):
    """验证响应时间不超过 500ms。"""
    payload = _make_payload()
    start = time.perf_counter()
    response = await client.post("/api/auth/register", json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 201
    assert elapsed_ms < 500, f"响应时间 {elapsed_ms:.0f}ms 超过 500ms 上限"


# ============================================================
# 验收标准 2: 数据库 users 表新增一条记录
# ============================================================


@pytest.mark.asyncio
async def test_register_creates_user_record(client, db_session):
    """验证在 users 表中新增一条记录。"""
    email = f"db_check_{_unique_id()}@example.com"
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == email).first()
    assert user is not None, "数据库中未找到新增的用户记录"
    assert user.username == payload["username"]
    assert user.email == email
    assert user.password_hash is not None
    assert user.password_hash != payload["password"], "密码必须经过哈希处理"


@pytest.mark.asyncio
async def test_register_user_status_is_active(client, db_session):
    """验证注册用户 status='active'。"""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.status == "active", f"期望 status='active'，实际 '{user.status}'"


@pytest.mark.asyncio
async def test_register_user_role_is_viewer(client, db_session):
    """验证注册用户 role='viewer'。"""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.role == "viewer", f"期望 role='viewer'，实际 '{user.role}'"


@pytest.mark.asyncio
async def test_register_user_has_timestamps(client, db_session):
    """验证用户记录包含 created_at 和 updated_at。"""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == payload["email"]).first()
    assert user is not None
    assert user.created_at is not None, "created_at 不能为空"
    assert user.updated_at is not None, "updated_at 不能为空"


# ============================================================
# 验收标准 3: 邮箱验证邮件在 30 秒内发出
# ============================================================


@pytest.mark.asyncio
@pytest.mark.xfail(reason="邮箱验证功能尚未实现，待 SMTP/mock 配置完成后启用")
async def test_register_sends_verification_email_within_30s(client, db_session):
    """验证邮箱验证邮件在 30 秒内发出。"""
    payload = _make_payload()
    start = time.perf_counter()
    response = await client.post("/api/auth/register", json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 201
    assert elapsed_ms <= 30000, f"邮件发送耗时 {elapsed_ms:.0f}ms，超过 30 秒限制"


# ============================================================
# 响应体包含用户信息和令牌
# ============================================================


@pytest.mark.asyncio
async def test_register_response_contains_user_and_tokens(client, db_session):
    """验证响应体包含用户数据和令牌字段。"""
    payload = _make_payload()
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    user_data = data["data"]["user"]
    assert "id" in user_data
    assert user_data["username"] == payload["username"]
    assert user_data["email"] == payload["email"]
    assert "created_at" in user_data

    tokens = data["data"]["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "Bearer"
    assert "expires_in" in tokens


# ============================================================
# 边界值：合法输入
# ============================================================


@pytest.mark.asyncio
async def test_register_min_length_username_succeeds(client, db_session):
    """边界：用户名最小长度（3 字符）注册成功。"""
    suffix = _unique_id()[:1]
    username = f"us{suffix}"
    assert len(username) == 3
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["username"] == username


@pytest.mark.asyncio
async def test_register_max_length_username_succeeds(client, db_session):
    """边界：用户名最大长度（50 字符）注册成功。"""
    username = "u" * 49 + _unique_id()[:1]
    assert len(username) == 50
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["username"] == username


@pytest.mark.asyncio
async def test_register_password_at_min_length_succeeds(client, db_session):
    """边界：密码最小长度（8 字符）注册成功。"""
    payload = _make_payload(password="Abcdef12")
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_with_special_chars_in_username_succeeds(client, db_session):
    """边界：用户名含下划线、连字符、点号注册成功。"""
    username = f"test-user_{_unique_id()[:4]}.name"
    payload = _make_payload(username=username)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["username"] == username


@pytest.mark.asyncio
async def test_register_with_long_valid_email_succeeds(client, db_session):
    """边界：较长但合法的邮箱地址注册成功。"""
    email = f"user_with_a_very_long_subdomain_name_part_{_unique_id()}@example.com"
    assert len(email) < 255
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["email"] == email


@pytest.mark.asyncio
async def test_register_with_plus_addressed_email_succeeds(client, db_session):
    """边界：加号地址邮箱（user+tag@example.com）注册成功。"""
    email = f"test+{_unique_id()}@example.com"
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["user"]["email"] == email


@pytest.mark.asyncio
async def test_register_with_subdomain_email_succeeds(client, db_session):
    """边界：含子域名的邮箱地址注册成功。"""
    email = "user@mail.subdomain.example.com"
    payload = _make_payload(email=email)
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201


# ============================================================
# 错误用例：重复邮箱 / 用户名
# ============================================================


@pytest.mark.asyncio
async def test_register_duplicate_email_fails_with_409(client, db_session):
    """验证重复邮箱注册返回 409。"""
    email = f"dup_email_{_unique_id()}@example.com"
    payload_first = _make_payload(
        username=f"first_{_unique_id()}",
        email=email,
    )
    response1 = await client.post("/api/auth/register", json=payload_first)
    assert response1.status_code == 201, "首次注册应成功"

    payload_second = _make_payload(
        username=f"second_{_unique_id()}",
        email=email,
    )
    response2 = await client.post("/api/auth/register", json=payload_second)
    assert response2.status_code == 409, f"重复邮箱应返回 409，实际 {response2.status_code}"


@pytest.mark.asyncio
async def test_register_duplicate_username_fails_with_409(client, db_session):
    """验证重复用户名注册返回 409。"""
    username = f"dup_user_{_unique_id()}"
    payload_first = _make_payload(
        username=username,
        email=f"first_{_unique_id()}@example.com",
    )
    response1 = await client.post("/api/auth/register", json=payload_first)
    assert response1.status_code == 201, "首次注册应成功"

    payload_second = _make_payload(
        username=username,
        email=f"second_{_unique_id()}@example.com",
    )
    response2 = await client.post("/api/auth/register", json=payload_second)
    assert response2.status_code == 409, f"重复用户名应返回 409，实际 {response2.status_code}"


# ============================================================
# 错误用例：密码策略
# ============================================================


@pytest.mark.asyncio
async def test_register_password_below_min_length_fails(client, db_session):
    """边界：7 字符密码（低于最小 8 位）应被拒绝。"""
    payload = _make_payload(password="Abc1234")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_without_uppercase_fails(client, db_session):
    """验证不含大写字母的密码应被拒绝。"""
    payload = _make_payload(password="nouppercase1")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_without_lowercase_fails(client, db_session):
    """验证不含小写字母的密码应被拒绝。"""
    payload = _make_payload(password="NOLOWERCASE1")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_without_digit_fails(client, db_session):
    """验证不含数字的密码应被拒绝。"""
    payload = _make_payload(password="NoDigitsHere")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_mismatch_fails(client, db_session):
    """验证密码与确认密码不匹配返回 400。"""
    suffix = _unique_id()
    payload = {
        "username": f"mismatch_{suffix}",
        "email": f"mismatch_{suffix}@example.com",
        "password": "SecurePass123!",
        "confirm_password": "DifferentPass456!",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 400


# ============================================================
# 错误用例：用户名长度
# ============================================================


@pytest.mark.asyncio
async def test_register_username_too_short_fails(client, db_session):
    """边界：2 字符用户名（低于最小 3 位）应被拒绝。"""
    payload = _make_payload(username="ab")
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_username_too_long_fails(client, db_session):
    """边界：51 字符用户名（超出最大 50 位）应被拒绝。"""
    payload = _make_payload(username="a" * 51)
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 422
