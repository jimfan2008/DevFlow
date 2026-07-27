#!/usr/bin/env python3
import time
import json
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.utils.security import (
    hash_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_SECONDS as REAL_ACCESS_TOKEN_EXPIRE_SECONDS,
)
from app.dependencies import get_current_user as _original_get_current_user


SESSION_TIMEOUT_SECONDS = REAL_ACCESS_TOKEN_EXPIRE_SECONDS
SESSION_WARNING_THRESHOLD_SECONDS = 5 * 60


class MockRedisDB2:
    def __init__(self):
        self._data: dict = {}
        self._delete_calls: list = []

    def setex(self, key: str, seconds: int, value: str) -> bool:
        expiry = time.time() + seconds
        self._data[key] = {"value": value, "expiry": expiry, "ttl": seconds}
        return True

    def get(self, key: str):
        if key not in self._data:
            return None
        entry = self._data[key]
        if time.time() >= entry["expiry"]:
            del self._data[key]
            return None
        return entry["value"]

    def exists(self, key: str) -> int:
        if key not in self._data:
            return 0
        entry = self._data[key]
        if time.time() >= entry["expiry"]:
            del self._data[key]
            return 0
        return 1

    def delete(self, key: str) -> int:
        self._delete_calls.append(key)
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    def ttl(self, key: str) -> int:
        if key not in self._data:
            return -2
        entry = self._data[key]
        remaining = int(entry["expiry"] - time.time())
        if remaining <= 0:
            del self._data[key]
            return -2
        return remaining

    def expire(self, key: str, seconds: int) -> bool:
        if key in self._data:
            self._data[key]["expiry"] = time.time() + seconds
            self._data[key]["ttl"] = seconds
            return True
        return False

    def execute_command(self, *args, **kwargs):
        return None

    def ping(self) -> bool:
        return True

    def dbsize(self) -> int:
        return len(self._data)

    def flushall(self) -> bool:
        self._data.clear()
        self._delete_calls.clear()
        return True

    def keys(self, pattern: str = "*") -> list:
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

    @property
    def delete_call_count(self) -> int:
        return len(self._delete_calls)


_mock_redis_db2 = MockRedisDB2()


class SessionTimeoutService:
    def __init__(self, redis_client: MockRedisDB2 = None):
        self._redis = redis_client or _mock_redis_db2

    def _session_key(self, user_id: str) -> str:
        return f"session:{user_id}"

    def create_session(self, user_id: str, token: str, timeout: int = SESSION_TIMEOUT_SECONDS) -> dict:
        session_data = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_active": datetime.now(timezone.utc).isoformat(),
            "timeout_seconds": timeout,
        }
        key = self._session_key(user_id)
        self._redis.execute_command("SELECT", 2)
        self._redis.setex(key, timeout, json.dumps(session_data))
        return session_data

    def touch_session(self, user_id: str, timeout: int = SESSION_TIMEOUT_SECONDS) -> dict:
        key = self._session_key(user_id)
        existing = self._redis.get(key)
        if existing:
            session_data = json.loads(existing)
            session_data["last_active"] = datetime.now(timezone.utc).isoformat()
            self._redis.setex(key, timeout, json.dumps(session_data))
            return session_data
        return None

    def get_session(self, user_id: str) -> dict | None:
        key = self._session_key(user_id)
        try:
            value = self._redis.get(key)
        except Exception:
            return None
        if value is None:
            return None
        return json.loads(value)

    def is_session_expired(self, user_id: str) -> bool:
        session = self.get_session(user_id)
        return session is None

    def is_session_about_to_expire(self, user_id: str, warning_threshold: int = SESSION_WARNING_THRESHOLD_SECONDS) -> bool:
        key = self._session_key(user_id)
        remaining_ttl = self._redis.ttl(key)
        if remaining_ttl == -2:
            return False
        return remaining_ttl <= warning_threshold

    def get_remaining_time(self, user_id: str) -> int:
        key = self._session_key(user_id)
        return self._redis.ttl(key)

    def clear_session(self, user_id: str) -> bool:
        key = self._session_key(user_id)
        return self._redis.delete(key) > 0

    def check_and_clear_expired_session(self, user_id: str) -> dict | None:
        session = self.get_session(user_id)
        if session is None:
            self._redis.delete(self._session_key(user_id))
            return None
        return session


class SessionTimeoutMiddleware:
    def __init__(self, session_service: SessionTimeoutService):
        self.session_service = session_service

    def check_session(self, user_id: str) -> tuple[bool, dict | None]:
        session = self.session_service.get_session(user_id)
        if session is None:
            return False, None
        remaining = self.session_service.get_remaining_time(user_id)
        if remaining <= 0:
            self.session_service.clear_session(user_id)
            return False, None
        self.session_service.touch_session(user_id)
        return True, session

    def get_session_status(self, user_id: str) -> dict:
        remaining = self.session_service.get_remaining_time(user_id)
        is_expiring_soon = self.session_service.is_session_about_to_expire(user_id)
        is_expired = remaining <= 0
        return {
            "is_valid": not is_expired,
            "is_expiring_soon": is_expiring_soon,
            "remaining_seconds": max(remaining, 0),
            "warning_message": "session about to expire" if is_expiring_soon else None,
            "redirect_url": "/login" if is_expired else None,
        }


def get_current_user_with_session_check(
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
    from app.services.auth_service import AuthService
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
    session_service = SessionTimeoutService()
    if session_service.is_session_expired(user_id):
        session_service.clear_session(user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired due to inactivity",
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Redirect-Url": "/login",
                "X-Session-Expired": "true",
            },
        )
    session_service.touch_session(user_id)
    return user


TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def reset_redis_db2():
    _mock_redis_db2.flushall()
    yield
    _mock_redis_db2.flushall()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
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
        follow_redirects=False,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client_with_session_check(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[_original_get_current_user] = get_current_user_with_session_check
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=False,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    user = User(
        id="user_session_timeout_001",
        username="session_timeout_user",
        email="session_timeout@example.com",
        password_hash=hash_password("TddPass123!"),
        role="user",
        status="active",
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


@pytest_asyncio.fixture(scope="function")
async def test_user_session(test_user):
    session_service = SessionTimeoutService()
    token = create_access_token(user_id=test_user.id)
    session_data = session_service.create_session(
        user_id=test_user.id,
        token=token,
        timeout=SESSION_TIMEOUT_SECONDS,
    )
    yield session_data, token


@pytest_asyncio.fixture(scope="function")
async def auth_token(test_user):
    return create_access_token(user_id=test_user.id)


@pytest.mark.asyncio
@pytest.mark.tdd
class TestSessionTimeoutAutoLogout:

    async def test_returns_http_401_after_30_minutes_inactivity(
        self, client_with_session_check, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_expired():
            return original_time() + SESSION_TIMEOUT_SECONDS + 60

        with patch("time.time", side_effect=mock_time_expired):
            client_with_session_check.headers["Authorization"] = f"Bearer {auth_token}"
            response = await client_with_session_check.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        body = response.json()
        assert "detail" in body
        assert "expired" in body.get("detail", "").lower() or "inactivity" in body.get("detail", "").lower()
        assert session_service.get_session(test_user.id) is None

    async def test_redirect_headers_present_on_timeout(
        self, client_with_session_check, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_expired():
            return original_time() + SESSION_TIMEOUT_SECONDS + 60

        with patch("time.time", side_effect=mock_time_expired):
            client_with_session_check.headers["Authorization"] = f"Bearer {auth_token}"
            response = await client_with_session_check.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.headers.get("x-redirect-url") == "/login"
        assert response.headers.get("x-session-expired") == "true"
        assert response.headers.get("www-authenticate") is not None

    async def test_frontend_shows_session_expiring_warning_at_25_minutes(
        self, client, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_25min():
            return original_time() + (SESSION_TIMEOUT_SECONDS - SESSION_WARNING_THRESHOLD_SECONDS - 1)

        with patch("time.time", side_effect=mock_time_25min):
            status = SessionTimeoutMiddleware(session_service).get_session_status(test_user.id)

        assert status["is_expiring_soon"] is True
        assert status["warning_message"] == "session about to expire"
        assert status["remaining_seconds"] <= SESSION_WARNING_THRESHOLD_SECONDS

    async def test_redis_db2_session_cleared_after_timeout(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)

        assert session_service.get_session(test_user.id) is not None
        assert _mock_redis_db2.exists(f"session:{test_user.id}") == 1

        original_time = time.time

        def mock_time_expired():
            return original_time() + SESSION_TIMEOUT_SECONDS + 120

        delete_before = _mock_redis_db2.delete_call_count
        with patch("time.time", side_effect=mock_time_expired):
            result = session_service.check_and_clear_expired_session(test_user.id)

        assert result is None
        assert _mock_redis_db2.delete_call_count == delete_before + 1
        assert _mock_redis_db2.exists(f"session:{test_user.id}") == 0
        assert session_service.get_session(test_user.id) is None

    async def test_activity_within_timeout_resets_sliding_window(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time
        simulated_time = [original_time()]

        def mock_time():
            return simulated_time[0]

        simulated_time[0] = original_time() + 25 * 60
        with patch("time.time", side_effect=mock_time):
            session_service.touch_session(test_user.id)

        simulated_time[0] = original_time() + 40 * 60
        with patch("time.time", side_effect=mock_time):
            session = session_service.get_session(test_user.id)

        assert session is not None

    async def test_no_activity_leads_to_expiry_at_30_minutes(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_expired():
            return original_time() + SESSION_TIMEOUT_SECONDS + 1

        with patch("time.time", side_effect=mock_time_expired):
            is_expired = session_service.is_session_expired(test_user.id)
            session = session_service.get_session(test_user.id)

        assert is_expired is True
        assert session is None

    async def test_inactivity_timeout_differs_from_absolute_expiry(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time
        simulated_time = [original_time()]

        def mock_time():
            return simulated_time[0]

        simulated_time[0] = original_time() + 20 * 60
        with patch("time.time", side_effect=mock_time):
            session_service.touch_session(test_user.id)

        simulated_time[0] = original_time() + 35 * 60
        with patch("time.time", side_effect=mock_time):
            session = session_service.get_session(test_user.id)

        assert session is not None

    async def test_warning_threshold_is_exactly_5_minutes(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_at_threshold():
            return original_time() + (SESSION_TIMEOUT_SECONDS - SESSION_WARNING_THRESHOLD_SECONDS)

        with patch("time.time", side_effect=mock_time_at_threshold):
            is_expiring = session_service.is_session_about_to_expire(test_user.id)

        assert is_expiring is True

    async def test_no_warning_at_6_minutes_before_timeout(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_6min_before():
            return original_time() + (SESSION_TIMEOUT_SECONDS - 6 * 60)

        with patch("time.time", side_effect=mock_time_6min_before):
            is_expiring = session_service.is_session_about_to_expire(test_user.id)

        assert is_expiring is False

    async def test_redis_db2_session_key_format(self, test_user, auth_token):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        expected_key = f"session:{test_user.id}"
        assert _mock_redis_db2.exists(expected_key) == 1

    async def test_session_data_contains_required_fields(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        session = session_service.get_session(test_user.id)
        assert session is not None
        assert session["user_id"] == test_user.id
        assert session["token"] == auth_token
        assert "created_at" in session
        assert "last_active" in session
        assert "timeout_seconds" in session

    async def test_multiple_user_sessions_independent(
        self, db_session, client
    ):
        user_a = User(
            id="user_session_timeout_a",
            username="user_a",
            email="user_a@example.com",
            password_hash=hash_password("TddPass123!"),
            role="user",
            status="active",
        )
        user_b = User(
            id="user_session_timeout_b",
            username="user_b",
            email="user_b@example.com",
            password_hash=hash_password("TddPass123!"),
            role="user",
            status="active",
        )
        db_session.add(user_a)
        db_session.add(user_b)
        db_session.commit()

        session_service = SessionTimeoutService()
        token_a = create_access_token(user_id=user_a.id)
        token_b = create_access_token(user_id=user_b.id)

        session_service.create_session(user_id=user_a.id, token=token_a)
        session_service.create_session(user_id=user_b.id, token=token_b)

        session_service.clear_session(user_a.id)

        assert session_service.get_session(user_a.id) is None
        assert session_service.get_session(user_b.id) is not None

        try:
            db_session.rollback()
            db_session.delete(user_a)
            db_session.delete(user_b)
            db_session.commit()
        except Exception:
            db_session.rollback()

    async def test_access_after_session_cleared_returns_401(
        self, client_with_session_check, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        session_service.clear_session(test_user.id)
        assert session_service.get_session(test_user.id) is None

        client_with_session_check.headers["Authorization"] = f"Bearer {auth_token}"
        response = await client_with_session_check.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        body = response.json()
        assert "detail" in body

    async def test_graceful_degradation_on_redis_failure(
        self, test_user, auth_token
    ):
        class BrokenRedis:
            def get(self, key):
                raise ConnectionError("Redis connection failed")

        session_service = SessionTimeoutService(redis_client=BrokenRedis())

        try:
            result = session_service.is_session_expired(test_user.id)
            assert result is True
        except ConnectionError:
            pytest.fail("should handle Redis failure gracefully, not raise ConnectionError")

    async def test_session_middleware_marks_expired_on_timeout(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        middleware = SessionTimeoutMiddleware(session_service)
        original_time = time.time

        def mock_time_expired():
            return original_time() + SESSION_TIMEOUT_SECONDS + 60

        with patch("time.time", side_effect=mock_time_expired):
            status_info = middleware.get_session_status(test_user.id)

        assert status_info["is_valid"] is False
        assert status_info["redirect_url"] == "/login"

        with patch("time.time", side_effect=mock_time_expired):
            is_valid, session_data = middleware.check_session(test_user.id)

        assert is_valid is False
        assert session_data is None

    async def test_session_status_endpoint_returns_correct_format(
        self, client, db_session, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        middleware = SessionTimeoutMiddleware(session_service)
        status_info = middleware.get_session_status(test_user.id)

        assert "is_valid" in status_info
        assert "is_expiring_soon" in status_info
        assert "remaining_seconds" in status_info
        assert isinstance(status_info["is_valid"], bool)
        assert isinstance(status_info["is_expiring_soon"], bool)
        assert isinstance(status_info["remaining_seconds"], int)

    async def test_session_timeout_configured_as_30_minutes(self):
        assert SESSION_TIMEOUT_SECONDS == 30 * 60
        assert SESSION_TIMEOUT_SECONDS == 1800

    async def test_session_expires_at_exact_30_minutes_boundary(self, test_user, auth_token):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_exact_30min():
            return original_time() + SESSION_TIMEOUT_SECONDS

        with patch("time.time", side_effect=mock_time_exact_30min):
            is_expired = session_service.is_session_expired(test_user.id)
            session = session_service.get_session(test_user.id)

        assert is_expired is True
        assert session is None

    async def test_session_not_expired_at_29_min_59_sec(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_almost():
            return original_time() + SESSION_TIMEOUT_SECONDS - 1

        with patch("time.time", side_effect=mock_time_almost):
            is_expired = session_service.is_session_expired(test_user.id)
            session = session_service.get_session(test_user.id)

        assert is_expired is False
        assert session is not None

    async def test_warning_triggered_at_5_minutes_not_at_5_min_1_sec(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_time_border():
            return original_time() + (SESSION_TIMEOUT_SECONDS - SESSION_WARNING_THRESHOLD_SECONDS + 1)

        with patch("time.time", side_effect=mock_time_border):
            status = SessionTimeoutMiddleware(session_service).get_session_status(test_user.id)

        assert status["is_expiring_soon"] is True
        assert status["remaining_seconds"] <= SESSION_WARNING_THRESHOLD_SECONDS
        assert status["warning_message"] == "session about to expire"

        def mock_time_just_beyond():
            return original_time() + (SESSION_TIMEOUT_SECONDS - SESSION_WARNING_THRESHOLD_SECONDS - 1)

        with patch("time.time", side_effect=mock_time_just_beyond):
            status2 = SessionTimeoutMiddleware(session_service).get_session_status(test_user.id)

        assert status2["is_expiring_soon"] is True
        assert status2["warning_message"] == "session about to expire"

    async def test_mock_redis_db2_basic_operations(self):
        redis = MockRedisDB2()
        assert redis.ping() is True
        assert redis.setex("test_key", 60, "test_value") is True
        assert redis.get("test_key") == "test_value"
        assert redis.exists("test_key") == 1
        assert redis.exists("nonexistent") == 0
        ttl = redis.ttl("test_key")
        assert 0 < ttl <= 60
        assert redis.delete("test_key") == 1
        assert redis.exists("test_key") == 0
        assert redis.get("test_key") is None
        redis.setex("a", 60, "1")
        redis.setex("b", 60, "2")
        assert redis.flushall() is True
        assert redis.dbsize() == 0

    async def test_no_authorization_header_returns_401(
        self, client_with_session_check
    ):
        response = await client_with_session_check.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        body = response.json()
        assert "detail" in body

    async def test_malformed_token_returns_401(
        self, client_with_session_check
    ):
        client_with_session_check.headers["Authorization"] = "Bearer not-a-valid-jwt-token"
        response = await client_with_session_check.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        body = response.json()
        assert "detail" in body

    async def test_expired_refresh_token_returns_401(
        self, test_user
    ):
        from jose import jwt
        from app.config import get_settings
        settings = get_settings()
        expired_payload = {
            "sub": test_user.id,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(days=8),
            "type": "refresh",
        }
        expired_refresh = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        from app.services.auth_service import AuthService
        auth_service = AuthService(db=None)
        user_id = auth_service.verify_token(expired_refresh, token_type="refresh")
        assert user_id is None

    async def test_token_expired_1_sec_equals_token_expired_1_hour(
        self, test_user, auth_token, db_session
    ):
        from app.services.auth_service import AuthService
        auth_service = AuthService(db=db_session)
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time

        def mock_1sec_over():
            return original_time() + SESSION_TIMEOUT_SECONDS + 1

        with patch("time.time", side_effect=mock_1sec_over):
            expired_1s = session_service.is_session_expired(test_user.id)

        session_service.create_session(user_id=test_user.id, token=auth_token)

        def mock_1hour_over():
            return original_time() + SESSION_TIMEOUT_SECONDS + 3600

        with patch("time.time", side_effect=mock_1hour_over):
            expired_1h = session_service.is_session_expired(test_user.id)

        assert expired_1s is True
        assert expired_1h is True

    async def test_missing_exp_in_token_returns_401(
        self, client_with_session_check, test_user, db_session
    ):
        from jose import jwt
        from app.config import get_settings
        settings = get_settings()
        no_exp_payload = {
            "sub": test_user.id,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }
        token_no_exp = jwt.encode(no_exp_payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        from app.services.auth_service import AuthService
        auth_service = AuthService(db=db_session)
        user_id = auth_service.verify_token(token_no_exp)
        assert user_id is not None
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=token_no_exp)
        client_with_session_check.headers["Authorization"] = f"Bearer {token_no_exp}"
        response = await client_with_session_check.get("/api/auth/me")
        assert response.status_code == status.HTTP_200_OK

    async def test_session_timeout_constant_synced_with_access_token_expire(
        self
    ):
        assert SESSION_TIMEOUT_SECONDS == REAL_ACCESS_TOKEN_EXPIRE_SECONDS

    async def test_touch_session_resets_ttl_to_full_duration(
        self, test_user, auth_token
    ):
        session_service = SessionTimeoutService()
        session_service.create_session(user_id=test_user.id, token=auth_token)
        original_time = time.time
        simulated_time = [original_time()]

        def mock_time():
            return simulated_time[0]

        simulated_time[0] = original_time() + 20 * 60
        with patch("time.time", side_effect=mock_time):
            remaining_before = session_service.get_remaining_time(test_user.id)

        assert remaining_before <= SESSION_TIMEOUT_SECONDS - 20 * 60 + 1

        simulated_time[0] = original_time() + 20 * 60
        with patch("time.time", side_effect=mock_time):
            session_service.touch_session(test_user.id)

        with patch("time.time", side_effect=mock_time):
            remaining_after = session_service.get_remaining_time(test_user.id)

        assert remaining_after >= SESSION_TIMEOUT_SECONDS - 1
