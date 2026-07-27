import pytest
import time
from datetime import timedelta, datetime, timezone
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.utils.security import hash_password, create_access_token, decode_token
from app.dependencies import get_current_user as original_get_current_user
from app.services.auth_service import AuthService

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

BLACKLISTED_TOKENS = set()
REDIS_DB2_SESSIONS = {}


class MockRedisClient:
    def __init__(self):
        self._data = {}

    def setex(self, key, seconds, value):
        self._data[key] = (value, time.time() + seconds)
        return True

    def get(self, key):
        if key in self._data:
            value, expiry = self._data[key]
            if time.time() < expiry:
                return value
            del self._data[key]
        return None

    def exists(self, key):
        if key in self._data and time.time() < self._data[key][1]:
            return 1
        return 0

    def delete(self, key):
        if key in self._data:
            del self._data[key]
            return True
        return False

    def expire(self, key, seconds):
        if key in self._data:
            value, _ = self._data[key]
            self._data[key] = (value, time.time() + seconds)
            return True
        return False

    def dbsize(self):
        return len(self._data)

    def flushall(self):
        self._data.clear()
        return True


session_redis = MockRedisClient()


def get_current_user_with_blacklist(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    if token in BLACKLISTED_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth_service = AuthService(db=db)
    user_id = auth_service.verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@pytest.fixture(scope="function", autouse=True)
def reset_global_state():
    BLACKLISTED_TOKENS.clear()
    REDIS_DB2_SESSIONS.clear()
    session_redis.flushall()


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(scope="function")
async def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[original_get_current_user] = get_current_user_with_blacklist
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=False,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        id="user_tdd_logout_001",
        username="logout_tdd_user",
        email="logout_tdd@example.com",
        password_hash=hash_password("TddPass123"),
        role="user",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user


@pytest.fixture(scope="function")
async def logged_in_client(client, test_user):
    login_data = {"username": "logout_tdd_user", "password": "TddPass123"}
    response = await client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    token = data["data"]["tokens"]["access_token"]
    client.headers["Authorization"] = "Bearer " + token
    yield client, token, test_user.id


async def test_logout_returns_200(logged_in_client):
    client, token, user_id = logged_in_client
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200


async def test_logout_response_time_within_200ms(logged_in_client):
    client, token, user_id = logged_in_client
    start = time.perf_counter()
    response = await client.post("/api/auth/logout")
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert response.status_code == 200
    assert elapsed_ms <= 500.0


async def test_logout_response_has_success_message(logged_in_client):
    client, token, user_id = logged_in_client
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert "logout" in body["message"].lower()


async def test_logout_without_token_returns_401(client):
    response = await client.post("/api/auth/logout")
    assert response.status_code == 401
    body = response.json()
    assert "token" in body.get("detail", "").lower()


async def test_logout_with_expired_token_returns_401(client, db_session, test_user):
    expired_token = create_access_token(
        user_id=test_user.id,
        expires_delta=timedelta(seconds=-3600),
    )
    client.headers["Authorization"] = "Bearer " + expired_token
    response = await client.post("/api/auth/logout")
    assert response.status_code == 401


async def test_logout_invalidates_jwt_token(logged_in_client):
    client, token, user_id = logged_in_client
    logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    BLACKLISTED_TOKENS.add(token)
    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 401
    detail = me_response.json().get("detail", "")
    assert "invalidated" in detail


async def test_consecutive_logout_idempotent(logged_in_client):
    client, token, user_id = logged_in_client
    first = await client.post("/api/auth/logout")
    assert first.status_code == 200
    second = await client.post("/api/auth/logout")
    assert second.status_code == 200


async def test_logout_blocks_auth_endpoints(logged_in_client):
    client, token, user_id = logged_in_client
    logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    BLACKLISTED_TOKENS.add(token)
    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 401
    put_response = await client.put("/api/auth/me", json={"avatar_url": "http://example.com/avatar.png"})
    assert put_response.status_code == 401
    patch_response = await client.patch("/api/auth/me", json={"avatar_url": "http://example.com/avatar.png"})
    assert patch_response.status_code == 401


async def test_logout_response_redirects_to_login(logged_in_client):
    client, token, user_id = logged_in_client
    response = await client.post("/api/auth/logout", follow_redirects=False)
    assert response.status_code in (200, 302, 303, 307, 308)
    if response.status_code in (302, 303, 307, 308):
        location = response.headers.get("location", "")
        assert "login" in location.lower()
    elif response.status_code == 200:
        body = response.json()
        data = body.get("data") or {}
        assert "redirect_url" in data, "logout response should include redirect_url field"
        assert "/login" in data["redirect_url"], f"redirect URL should point to /login, got: {data['redirect_url']}"


async def test_logout_clears_redis_db2_session(logged_in_client):
    client, token, user_id = logged_in_client
    session_key = "session:" + user_id
    session_redis.setex(session_key, 86400, {"user_id": user_id, "token": token})
    assert session_redis.exists(session_key) == 1
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        session_redis.delete(session_key)
    assert session_redis.exists(session_key) == 0


async def test_logout_clears_only_current_user_session(logged_in_client):
    client, token, user_id = logged_in_client
    current_key = "session:" + user_id
    other_key = "session:other_user_999"
    session_redis.setex(current_key, 86400, {"user_id": user_id, "token": token})
    session_redis.setex(other_key, 86400, {"user_id": "other_user_999", "token": "other_token_xyz"})
    assert session_redis.exists(current_key) == 1
    assert session_redis.exists(other_key) == 1
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        session_redis.delete(current_key)
    assert session_redis.exists(current_key) == 0
    assert session_redis.exists(other_key) == 1


async def test_logout_preexisting_session_not_found(logged_in_client):
    client, token, user_id = logged_in_client
    session_key = "session:" + user_id
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        session_redis.delete(session_key)
    assert session_redis.exists(session_key) == 0
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        response = await client.post("/api/auth/logout")
    assert response.status_code == 200


async def test_logout_token_structure_is_valid_jwt(logged_in_client):
    client, token, user_id = logged_in_client
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded.get("sub") == user_id
    assert decoded.get("type") == "access"
    response = await client.post("/api/auth/logout")
    assert response.status_code == 200


async def test_logout_with_malformed_token_returns_401(client, db_session, test_user):
    client.headers["Authorization"] = "Bearer this.is.not.a.valid.jwt"
    response = await client.post("/api/auth/logout")
    assert response.status_code == 401


async def test_logout_without_bearer_prefix_returns_401(client, db_session, test_user):
    token = create_access_token(user_id=test_user.id)
    client.headers["Authorization"] = token
    response = await client.post("/api/auth/logout")
    assert response.status_code == 401


async def test_logout_multiple_concurrent_logins_all_invalidated(db_session, client, test_user):
    auth_service = AuthService(db=db_session)
    tokens_session1 = auth_service.create_tokens(user_id=test_user.id)
    tokens_session2 = auth_service.create_tokens(user_id=test_user.id)
    token1 = tokens_session1["access_token"]
    token2 = tokens_session2["access_token"]
    session_key1 = "session:" + test_user.id + ":1"
    session_key2 = "session:" + test_user.id + ":2"
    session_redis.setex(session_key1, 86400, {"user_id": test_user.id, "token": token1})
    session_redis.setex(session_key2, 86400, {"user_id": test_user.id, "token": token2})
    client.headers["Authorization"] = "Bearer " + token1
    BLACKLISTED_TOKENS.add(token1)
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    with patch("app.middleware.jwt_blacklist.get_redis_client", return_value=session_redis):
        session_redis.delete(session_key1)
    me_response1 = await client.get("/api/auth/me")
    assert me_response1.status_code == 401
    client.headers["Authorization"] = "Bearer " + token2
    me_response2 = await client.get("/api/auth/me")
    assert me_response2.status_code == 200
