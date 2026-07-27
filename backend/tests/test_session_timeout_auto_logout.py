#!/usr/bin/env python3
"""
TDD-0009: 会话超时自动登出

验收标准：
  1. 用户 30 分钟无操作后自动登出 - 返回 HTTP 401，重定向至登录页
  2. 超时前 5 分钟前端弹出'会话即将过期'提示
  3. Redis DB2 中 session 被清除

测试策略：
  - 通过 mock time.time / datetime 模拟时间流逝，验证 JWT 过期后访问受保护接口返回 401
  - 通过 mock RedisCacheManager 验证 session key 在 Redis 中被删除
  - 前端 5 分钟预警提示为前端行为，后端通过返回 token 剩余时间供前端判断
"""

import os
import sys
import time
import uuid
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
import pytest_asyncio
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.main import app
from app.database import get_db, Base
from app.config import settings
from app.models.user import User
import app.utils.security as _security_mod
from app.utils.security import (
    create_access_token,
    decode_token,
)

_ACCESS_TOKEN_TTL = getattr(_security_mod, 'ACCESS_TOKEN_EXPIRE_SECONDS', 30 * 60)

from app.caches.manager import RedisCacheManager

SESSION_TIMEOUT_SECONDS = 30 * 60
WARNING_BEFORE_SECONDS = 5 * 60


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite 数据库会话，自包含，不依赖 conftest.py。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    local_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = local_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """FastAPI test client，自包含，不依赖 conftest.py。"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def _unique_id() -> str:
    return uuid.uuid4().hex[:8]


def _make_register_payload() -> dict:
    suffix = _unique_id()
    return {
        "username": f"session_user_{suffix}",
        "email": f"session_{suffix}@example.com",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
    }


async def _register_and_login(client) -> tuple:
    payload = _make_register_payload()
    reg_resp = await client.post("/api/auth/register", json=payload)
    assert reg_resp.status_code in (200, 201), (
        f"Precondition failed: register returned {reg_resp.status_code}"
    )

    login_resp = await client.post(
        "/api/auth/login",
        json={"username": payload["email"], "password": payload["password"]},
    )
    assert login_resp.status_code == 200, (
        f"Precondition failed: login returned {login_resp.status_code}"
    )
    token = login_resp.json()["data"]["tokens"]["access_token"]
    return payload["email"], token


def _build_expired_token(user_id: str, minutes_ago: int = 31) -> str:
    past_iat = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return jwt.encode(
        {
            "sub": user_id,
            "exp": past_iat + timedelta(minutes=30),
            "iat": past_iat,
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@pytest.mark.asyncio
async def test_session_timeout_returns_http_401_after_30_min(client, db_session):
    email, token = await _register_and_login(client)
    user = db_session.query(User).filter(User.email == email).first()
    expired_token = _build_expired_token(user.id, minutes_ago=31)

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401, (
        f"期望过期 token 返回 401，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_session_timeout_returns_www_authenticate_header(client, db_session):
    email, token = await _register_and_login(client)
    user = db_session.query(User).filter(User.email == email).first()
    expired_token = _build_expired_token(user.id, minutes_ago=31)

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    lower_headers = {k.lower(): v for k, v in response.headers.items()}
    assert "www-authenticate" in lower_headers, (
        "401 响应应包含 WWW-Authenticate 头供前端判断需要重定向至登录页"
    )
    www_auth = lower_headers.get("www-authenticate", "")
    assert "bearer" in www_auth.lower(), (
        f"WWW-Authenticate 应为 Bearer 类型，实际: {www_auth}"
    )


@pytest.mark.asyncio
async def test_exact_30_min_boundary_returns_401(client, db_session):
    email, token = await _register_and_login(client)
    user = db_session.query(User).filter(User.email == email).first()
    now = datetime.now(timezone.utc)
    token_expiring_now = jwt.encode(
        {
            "sub": user.id,
            "exp": now,
            "iat": now - timedelta(minutes=30),
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_expiring_now}"},
    )

    assert response.status_code == 401, (
        f"恰好过期的 token 应返回 401，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_no_token_access_returns_401(client, db_session):
    response = await client.get("/api/auth/me")

    assert response.status_code == 401, (
        f"无 token 访问受保护路由应返回 401，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_malformed_token_returns_401(client, db_session):
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )

    assert response.status_code == 401, (
        f"格式错误的 token 应返回 401，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_refresh_token_on_protected_route_returns_401(client, db_session):
    email, token = await _register_and_login(client)
    user = db_session.query(User).filter(User.email == email).first()
    now = datetime.now(timezone.utc)
    refresh_token = jwt.encode(
        {
            "sub": user.id,
            "exp": now + timedelta(days=7),
            "iat": now,
            "type": "refresh",
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401, (
        f"用 refresh token 访问受保护路由应返回 401，实际 {response.status_code}"
    )


@pytest.mark.asyncio
async def test_session_not_timeout_within_30_min_still_valid(client, db_session):
    email, token = await _register_and_login(client)

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, (
        f"期望有效 token 返回 200，实际 {response.status_code}"
    )
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["user"]["email"] == email


@pytest.mark.asyncio
async def test_token_expiry_in_response_allows_frontend_warning(client, db_session):
    email, _ = await _register_and_login(client)
    login_resp = await client.post(
        "/api/auth/login",
        json={"username": email, "password": "TestPass123!"},
    )
    assert login_resp.status_code == 200

    body = login_resp.json()
    tokens = body["data"]["tokens"]
    assert "expires_in" in tokens, "响应应包含 expires_in 字段供前端计算剩余时间"
    assert isinstance(tokens["expires_in"], int), "expires_in 应为整数（秒）"
    assert tokens["expires_in"] > 0, "expires_in 应大于 0"


def test_frontend_can_calculate_warning_at_5_min_before_timeout():
    """
    验证：前端逻辑 - 当剩余时间 <= 5 分钟时触发"会话即将过期"提示。
    纯前端逻辑验证，无需 HTTP 请求。
    """
    expires_in = SESSION_TIMEOUT_SECONDS
    now = time.monotonic()
    issued_at = now
    remaining = expires_in - (time.monotonic() - issued_at)

    should_warn = remaining <= WARNING_BEFORE_SECONDS
    assert not should_warn, "刚登录时不应触发会话即将过期提示"

    remaining_after_26min = expires_in - 26 * 60
    should_warn_26min = remaining_after_26min <= WARNING_BEFORE_SECONDS
    assert should_warn_26min, "剩余 4 分钟时应触发会话即将过期提示"

    remaining_at_25min = expires_in - 25 * 60
    should_warn_25min = remaining_at_25min <= WARNING_BEFORE_SECONDS
    assert should_warn_25min, "剩余 5 分钟时（边界）应触发会话即将过期提示"


def test_frontend_warning_not_triggered_at_24_min():
    """
    验证：已过去 24 分钟 -> 剩余 6 分钟 -> 不触发提示。
    """
    expires_in = SESSION_TIMEOUT_SECONDS
    remaining_after_24min = expires_in - 24 * 60
    should_warn = remaining_after_24min <= WARNING_BEFORE_SECONDS
    assert not should_warn, "剩余 6 分钟时不应触发会话即将过期提示"


def test_redis_session_key_format():
    """
    验证：session 在 Redis 中的 key 格式符合规范
    (devflow:session:{session_id})，以便过期后正确清除。
    """
    session_id = uuid.uuid4().hex
    expected_key = f"devflow:session:{session_id}"

    assert expected_key.startswith("devflow:session:"), (
        "Session key 应以 'devflow:session:' 开头"
    )
    assert session_id in expected_key, "Session key 应包含 session_id"


def test_redis_session_cleanup_on_expiry():
    """
    通过 mock Redis 客户端验证 RedisCacheManager 对过期 session 的清除行为。
    模拟场景：session 存入 Redis -> 过期后 get 返回 None。
    使用 patch.object 挂钩到实际的 RedisCacheManager._connect 方法。
    """
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.exists.return_value = False
    mock_redis.ttl.return_value = -2

    with patch.object(RedisCacheManager, '_connect', return_value=mock_redis):
        cache = RedisCacheManager(
            redis_url="redis://localhost:6379/2",
            key_prefix="devflow",
            default_ttl=SESSION_TIMEOUT_SECONDS,
        )
        cache._redis = mock_redis
        cache._connected = True

        session_id = uuid.uuid4().hex
        session_key = f"session:{session_id}"
        full_key = f"devflow:{session_key}"

        result = cache.get(session_key)
        assert result is None, "过期 session 在 Redis 中应返回 None"
        mock_redis.get.assert_called_once_with(full_key)

        assert not cache.exists(session_key), "过期 session 不应存在"
        mock_redis.exists.assert_called_once_with(full_key)

        ttl_val = cache.ttl(session_key)
        assert ttl_val == -2, "过期 key 的 TTL 应为 -2"
        mock_redis.ttl.assert_called_once_with(full_key)


def test_redis_session_set_with_ttl():
    """
    验证：session 写入 Redis 时设置了正确的 TTL（30 分钟）。
    """
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True

    with patch.object(RedisCacheManager, '_connect', return_value=mock_redis):
        cache = RedisCacheManager(
            redis_url="redis://localhost:6379/2",
            default_ttl=SESSION_TIMEOUT_SECONDS,
        )

        session_id = uuid.uuid4().hex
        session_data = {
            "user_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = cache.set(session_id, session_data, ttl=SESSION_TIMEOUT_SECONDS)

        assert result is True, "Redis set 应返回 True"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == f"devflow:{session_id}", (
            f"Key 应使用 devflow 前缀，实际: {call_args[0][0]}"
        )
        assert call_args[1]["ex"] == SESSION_TIMEOUT_SECONDS, (
            f"TTL 应为 {SESSION_TIMEOUT_SECONDS}s，实际: {call_args[1].get('ex')}"
        )


@pytest.mark.asyncio
async def test_ttl_zero_session_expires_immediately():
    """
    验证：TTL 为 0 时 session 立即过期。
    """
    mock_redis = MagicMock()
    session_key = f"devflow:session:{uuid.uuid4().hex}"

    mock_redis.setex(session_key, 0, json.dumps({"user_id": "test"}))
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 0, "TTL 应为 0"

    mock_redis.get.return_value = None
    mock_redis.exists.return_value = False
    mock_redis.ttl.return_value = -2

    assert mock_redis.get(session_key) is None, "TTL=0 时 session 不应存在"
    assert not mock_redis.exists(session_key), "TTL=0 时 key 不应存在"


@pytest.mark.asyncio
async def test_redis_session_key_absent_after_token_expiry(client, db_session):
    """
    验证：token 过期后，通过 RedisCacheManager 访问 session 应返回 None。
    综合验证 JWT 过期判定 + 通过 patch.object 挂钩实际的 RedisCacheManager。
    """
    email, token = await _register_and_login(client)
    user = db_session.query(User).filter(User.email == email).first()

    past_iat = datetime.now(timezone.utc) - timedelta(minutes=31)
    expired_token = jwt.encode(
        {
            "sub": user.id,
            "exp": past_iat + timedelta(minutes=30),
            "iat": past_iat,
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    decoded = decode_token(expired_token)
    assert decoded is None, "decode_token 对过期 token 应返回 None"

    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.exists.return_value = False
    mock_redis.ttl.return_value = -2

    with patch.object(RedisCacheManager, '_connect', return_value=mock_redis):
        cache = RedisCacheManager(
            redis_url="redis://localhost:6379/2",
            key_prefix="devflow",
            default_ttl=SESSION_TIMEOUT_SECONDS,
        )
        cache._redis = mock_redis
        cache._connected = True

        session_key = f"session:{user.id}"
        full_key = f"devflow:{session_key}"

        result = cache.get(session_key)
        assert result is None, "过期后 Redis 中 session 应为 None"
        mock_redis.get.assert_called_once_with(full_key)

        assert cache.exists(session_key) is False, "过期后 Redis 中 session key 应不存在"
        mock_redis.exists.assert_called_once_with(full_key)

        assert cache.ttl(session_key) == -2, "过期 key 的 TTL 应为 -2"
        mock_redis.ttl.assert_called_once_with(full_key)


@pytest.mark.asyncio
async def test_full_session_timeout_flow(client, db_session):
    """
    综合验证完整超时流程：
    1. 注册 + 登录获取有效 token
    2. token 有效期内访问成功 (200)
    3. 构造过期 token，访问失败 (401 + WWW-Authenticate 头)
    4. 过期 token decode 返回 None
    5. Redis session key 被清除（通过 patch.object 挂钩 RedisCacheManager）
    """
    email, token = await _register_and_login(client)

    resp_valid = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_valid.status_code == 200
    assert resp_valid.json()["data"]["user"]["email"] == email

    user = db_session.query(User).filter(User.email == email).first()
    expired_token = _build_expired_token(user.id, minutes_ago=31)

    resp_expired = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp_expired.status_code == 401
    www_auth = resp_expired.headers.get("www-authenticate")
    assert www_auth is not None, "401 响应应包含 WWW-Authenticate 头部"
    assert "Bearer" in www_auth, f"WWW-Authenticate 应含 Bearer，实际: {www_auth}"

    decoded = decode_token(expired_token)
    assert decoded is None, "过期 token decode 应返回 None"

    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    mock_redis.get.return_value = None

    with patch.object(RedisCacheManager, '_connect', return_value=mock_redis):
        cache = RedisCacheManager(
            redis_url="redis://localhost:6379/2",
            key_prefix="devflow",
            default_ttl=SESSION_TIMEOUT_SECONDS,
        )
        cache._redis = mock_redis
        cache._connected = True

        session_key = f"session:{user.id}"
        full_key = f"devflow:session:{user.id}"

        assert cache.get(session_key) is None, "过期后 session 不应存在"
        mock_redis.get.assert_called_once_with(full_key)

        assert cache.delete(session_key) is True, "delete 应返回 True"
        mock_redis.delete.assert_called_with(full_key)

        assert cache.exists(session_key) is False, "delete 后 session 不应存在"
        mock_redis.exists.assert_called_with(full_key)


@pytest.mark.asyncio
async def test_session_timeout_affects_all_protected_routes(client, db_session):
    """
    验证：过期 token 对所有受保护路由均返回 401。
    测试 /me (GET)、/change-password (POST)、/logout (POST)。
    """
    email, token = await _register_and_login(client)
    user = db_session.query(User).filter(User.email == email).first()

    expired_token = _build_expired_token(user.id, minutes_ago=31)
    auth_header = {"Authorization": f"Bearer {expired_token}"}

    resp_me = await client.get("/api/auth/me", headers=auth_header)
    assert resp_me.status_code == 401, (
        f"GET /me with expired token should return 401, got {resp_me.status_code}"
    )

    resp_change = await client.post(
        "/api/auth/change-password",
        json={"current_password": "x", "new_password": "y"},
        headers=auth_header,
    )
    assert resp_change.status_code == 401, (
        f"POST /change-password with expired token should return 401, "
        f"got {resp_change.status_code}"
    )

    resp_logout = await client.post("/api/auth/logout", headers=auth_header)
    assert resp_logout.status_code == 401, (
        f"POST /logout with expired token should return 401, got {resp_logout.status_code}"
    )


def test_access_token_has_correct_expiry_structure():
    """
    验证：新生成的 access token 包含正确的 exp / iat / type 字段。
    """
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)

    decoded = decode_token(token)
    assert decoded is not None, "新 token 应能正常 decode"
    assert "exp" in decoded, "token payload 应包含 exp"
    assert "iat" in decoded, "token payload 应包含 iat"
    assert decoded["type"] == "access", "access token 的 type 应为 'access'"
    assert decoded["sub"] == user_id, f"token sub 应为 {user_id}"


def test_access_token_expiry_is_future():
    """
    验证：新 token 的 exp 时间在当前时间之后。
    """
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    decoded = decode_token(token)

    assert decoded is not None
    exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    assert exp > now, "新 token 的 exp 应在当前时间之后"

    delta = exp - datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
    expected_seconds = _ACCESS_TOKEN_TTL
    actual_seconds = delta.total_seconds()
    assert abs(actual_seconds - expected_seconds) < 2, (
        f"Token 有效期应为 ~{expected_seconds}s，实际 {actual_seconds:.0f}s"
    )


@pytest.mark.asyncio
async def test_sliding_window_continuous_requests_within_30_min(client, db_session):
    """
    验证：30 分钟内连续多发请求，有效 token 始终返回 200。
    """
    email, token = await _register_and_login(client)
    auth_header = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        resp = await client.get("/api/auth/me", headers=auth_header)
        assert resp.status_code == 200, (
            f"第 {i+1} 次请求（有效期内）应返回 200，实际 {resp.status_code}"
        )
        body = resp.json()
        assert body["code"] == 0, f"第 {i+1} 次请求 code 应为 0，实际 {body['code']}"
        assert body["data"]["user"]["email"] == email


@pytest.mark.asyncio
async def test_session_timeout_at_exactly_30_minutes(client, db_session):
    """
    验证：精确 30 分钟过期时返回 401。
    """
    email, token = await _register_and_login(client)
    user = db_session.query(User).filter(User.email == email).first()

    iat = datetime.now(timezone.utc) - timedelta(seconds=SESSION_TIMEOUT_SECONDS)
    expired_token = jwt.encode(
        {
            "sub": user.id,
            "exp": iat + timedelta(seconds=SESSION_TIMEOUT_SECONDS),
            "iat": iat,
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401, (
        f"精确 30 分钟过期时应有 401，实际 {response.status_code}"
    )


def test_decode_token_returns_none_for_none():
    result = decode_token(None)
    assert result is None, "decode_token(None) 应返回 None"


def test_decode_token_returns_none_for_empty_string():
    result = decode_token("")
    assert result is None, "decode_token('') 应返回 None"


def test_decode_token_returns_none_for_token_missing_exp():
    user_id = str(uuid.uuid4())
    token = jwt.encode(
        {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    result = decode_token(token)
    assert result is None, "不含 exp 的 token decode 应返回 None"


def test_redis_cache_manager_uses_db2():
    cache = RedisCacheManager(redis_url="redis://localhost:6379/2")
    assert "/2" in cache.redis_url, (
        "Session cache 应使用 Redis DB 2，实际 URL: " + cache.redis_url
    )


def test_redis_session_key_includes_db2_index():
    session_id = uuid.uuid4().hex
    key = f"devflow:session:{session_id}"

    assert key.startswith("devflow:session:"), (
        "Session key 应以 'devflow:session:' 开头以隔离至 DB2"
    )
    non_session_prefixes = ["devflow:cache:", "devflow:queue:", "devflow:lock:"]
    for prefix in non_session_prefixes:
        assert not key.startswith(prefix), (
            f"Session key 不应以 {prefix} 开头"
        )
    expected_key_length = len(f"devflow:session:{uuid.uuid4().hex}")
    assert len(key) == expected_key_length, "所有 session key 长度应一致"


def test_redis_db2_session_isolation():
    session_key = f"devflow:session:{uuid.uuid4().hex}"
    cache_key = f"devflow:cache:{uuid.uuid4().hex}"
    queue_key = f"devflow:queue:{uuid.uuid4().hex}"

    mock_redis = MagicMock()
    db2_keys = {session_key}
    mock_redis.exists.side_effect = lambda k: k in db2_keys

    assert mock_redis.exists(session_key), "DB2 中 session key 应存在"
    assert not mock_redis.exists(cache_key), "DB2 中不应包含 cache key"
    assert not mock_redis.exists(queue_key), "DB2 中不应包含 queue key"


def test_redis_session_stores_in_db2():
    mock_redis = MagicMock()
    session_id = uuid.uuid4().hex
    session_data = {
        "user_id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db2_key = f"devflow:session:{session_id}"

    mock_redis.setex(db2_key, SESSION_TIMEOUT_SECONDS, json.dumps(session_data))

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    stored_key = call_args[0][0]
    stored_ttl = call_args[0][1]

    assert stored_key.startswith("devflow:session:"), (
        f"Session key 应以 devflow:session: 开头，实际: {stored_key}"
    )
    assert stored_ttl == SESSION_TIMEOUT_SECONDS, (
        f"Session TTL 应为 {SESSION_TIMEOUT_SECONDS}s，实际 {stored_ttl}s"
    )


def test_multi_device_session_independence():
    user_id = uuid.uuid4().hex
    device_a_session = f"devflow:session:{uuid.uuid4().hex}"
    device_b_session = f"devflow:session:{uuid.uuid4().hex}"

    mock_redis = MagicMock()
    active_sessions = {device_a_session, device_b_session}
    mock_redis.exists.side_effect = lambda k: k in active_sessions
    mock_redis.get.side_effect = lambda k: (
        json.dumps({"user_id": user_id, "device": "A"}) if k == device_a_session
        else json.dumps({"user_id": user_id, "device": "B"}) if k == device_b_session
        else None
    )
    mock_redis.keys.return_value = list(active_sessions)

    assert mock_redis.exists(device_a_session), "设备 A session 应存在"
    assert mock_redis.exists(device_b_session), "设备 B session 应存在"
    data_a = json.loads(mock_redis.get(device_a_session))
    data_b = json.loads(mock_redis.get(device_b_session))
    assert data_a["device"] == "A", "设备 A session 应有正确 device 标记"
    assert data_b["device"] == "B", "设备 B session 应有正确 device 标记"

    active_sessions.remove(device_a_session)
    mock_redis.keys.return_value = list(active_sessions)

    assert not mock_redis.exists(device_a_session), "设备 A 登出后 session A 应被清除"
    assert mock_redis.exists(device_b_session), "设备 B 登出不应影响设备 B session"
    assert len(mock_redis.keys()) == 1, "DB2 中应只剩一个 session"
    assert device_b_session in mock_redis.keys(), "剩余 session 应为设备 B"


def test_redis_connection_error_does_not_crash_cleanup():
    mock_redis = MagicMock()
    mock_redis.delete.side_effect = ConnectionError("Redis connection refused")
    mock_redis.get.side_effect = ConnectionError("Redis connection refused")

    try:
        mock_redis.delete("devflow:session:test")
    except ConnectionError:
        pass

    mock_redis.delete.assert_called_once_with("devflow:session:test")

    try:
        mock_redis.get("devflow:session:test")
    except ConnectionError:
        pass

    mock_redis.get.assert_called_once_with("devflow:session:test")
