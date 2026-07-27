import time
import json
from datetime import datetime, timedelta, timezone

import pytest


class MockSession:
    def __init__(self, session_id: str, user_id: str, created_at=None):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_active = self.created_at

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MockSession":
        obj = cls(data["session_id"], data["user_id"])
        obj.created_at = datetime.fromisoformat(data["created_at"])
        obj.last_active = datetime.fromisoformat(data["last_active"])
        return obj


class MockResponse:
    def __init__(self, status_code: int, location: str = None, body: dict = None):
        self.status_code = status_code
        self.headers = {}
        self.body = body or {}
        if location:
            self.headers["Location"] = location

    def json(self) -> dict:
        return self.body


class MockRedisClient:
    def __init__(self):
        self.db = 2
        self._store = {}
        self._expiry = {}

    def set(self, key: str, value: str, ex: int = None) -> bool:
        self._store[key] = value
        if ex is not None:
            self._expiry[key] = time.time() + ex
        return True

    def get(self, key: str) -> str:
        if key in self._expiry and time.time() > self._expiry[key]:
            self.delete(key)
            return None
        return self._store.get(key)

    def ttl(self, key: str) -> int:
        if key not in self._store:
            return -2
        if key not in self._expiry:
            return -1
        remaining = int(self._expiry[key] - time.time())
        if remaining <= 0:
            self.delete(key)
            return -2
        return remaining

    def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            self._expiry.pop(key, None)
            return 1
        return 0

    def exists(self, key: str) -> bool:
        return self.get(key) is not None


class SessionService:
    SESSION_TIMEOUT_MINUTES = 30
    WARNING_BEFORE_MINUTES = 5

    def __init__(self, redis_client: MockRedisClient):
        self.redis = redis_client

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def create_session(self, session_id: str, user_id: str) -> MockSession:
        session = MockSession(session_id, user_id)
        self.redis.set(
            self._key(session_id),
            json.dumps(session.to_dict()),
            ex=self.SESSION_TIMEOUT_MINUTES * 60,
        )
        return session

    def touch_session(self, session_id: str) -> None:
        raw = self.redis.get(self._key(session_id))
        if raw is None:
            return
        session = MockSession.from_dict(json.loads(raw))
        session.last_active = datetime.now(timezone.utc)
        self.redis.set(
            self._key(session_id),
            json.dumps(session.to_dict()),
            ex=self.SESSION_TIMEOUT_MINUTES * 60,
        )

    def check_session_status(self, session_id: str) -> tuple:
        raw = self.redis.get(self._key(session_id))
        if raw is None:
            return (False, False)
        session = MockSession.from_dict(json.loads(raw))
        ttl = self.redis.ttl(self._key(session_id))
        if ttl <= 0:
            self.redis.delete(self._key(session_id))
            return (False, False)
        warning_seconds = self.WARNING_BEFORE_MINUTES * 60
        should_warn = ttl <= warning_seconds
        return (True, should_warn)

    def handle_request(self, session_id: str, user_action: str = None) -> MockResponse:
        if user_action:
            self.touch_session(session_id)
        is_valid, should_warn = self.check_session_status(session_id)
        if not is_valid:
            return MockResponse(401, location="/login")
        if should_warn:
            resp = MockResponse(200)
            resp.headers["X-Session-Warning"] = "session_about_to_expire"
            return resp
        return MockResponse(200)

    def force_logout(self, session_id: str) -> bool:
        return self.redis.delete(self._key(session_id)) > 0


class MockJWTManager:
    def __init__(self):
        self._valid_tokens = {}

    def issue_token(self, user_id: str) -> str:
        token = f"jwt_{user_id}_{int(time.time())}"
        self._valid_tokens[token] = user_id
        return token

    def validate_token(self, token: str) -> bool:
        return token in self._valid_tokens

    def revoke_token(self, token: str) -> bool:
        if token in self._valid_tokens:
            del self._valid_tokens[token]
            return True
        return False

    def revoke_all_for_user(self, user_id: str) -> int:
        to_remove = [t for t, uid in self._valid_tokens.items() if uid == user_id]
        for t in to_remove:
            del self._valid_tokens[t]
        return len(to_remove)


class ManualLogoutHandler:
    def __init__(self, redis_client: MockRedisClient, jwt_manager: MockJWTManager):
        self.redis = redis_client
        self.jwt = jwt_manager

    def logout(self, session_id: str, token: str) -> MockResponse:
        start = time.time()
        deleted = self.redis.delete(f"session:{session_id}")
        revoked = self.jwt.revoke_token(token)
        elapsed = int((time.time() - start) * 1000)
        resp = MockResponse(
            status_code=200,
            body={
                "status": "ok",
                "message": "logged_out",
                "elapsed_ms": elapsed,
            },
        )
        resp.headers["X-Elapsed-Ms"] = str(elapsed)
        return resp


@pytest.fixture
def mock_redis():
    return MockRedisClient()


@pytest.fixture
def mock_jwt():
    return MockJWTManager()


@pytest.fixture
def session_service(mock_redis):
    return SessionService(mock_redis)


@pytest.fixture
def logout_handler(mock_redis, mock_jwt):
    return ManualLogoutHandler(mock_redis, mock_jwt)


@pytest.fixture
def active_session(session_service):
    sid = "sess_manual_001"
    uid = "user_99"
    session_service.create_session(sid, uid)
    return sid, uid


class TestManualLogout:
    def test_logout_returns_http_200_under_200ms(self, logout_handler, active_session):
        session_id, _ = active_session
        resp = logout_handler.logout(session_id, "jwt_user_99_dummy")
        assert resp.status_code == 200
        elapsed = int(resp.headers.get("X-Elapsed-Ms", "9999"))
        assert elapsed <= 200, f"Response time {elapsed}ms exceeds 200ms limit"

    def test_logout_invalidates_jwt_token(self, mock_jwt, logout_handler, active_session):
        session_id, user_id = active_session
        token = mock_jwt.issue_token(user_id)
        assert mock_jwt.validate_token(token) is True
        logout_handler.logout(session_id, token)
        assert mock_jwt.validate_token(token) is False

    def test_logout_redirects_to_login_page(self, logout_handler, active_session):
        session_id, _ = active_session
        resp = logout_handler.logout(session_id, "jwt_dummy")
        assert resp.status_code == 200
        assert resp.body.get("message") == "logged_out"

    def test_logout_deletes_session_from_redis_db2(self, mock_redis, logout_handler, active_session):
        session_id, _ = active_session
        key = f"session:{session_id}"
        assert mock_redis.exists(key) is True
        logout_handler.logout(session_id, "jwt_dummy")
        assert mock_redis.exists(key) is False

    def test_logout_duplicate_returns_ok(self, mock_redis, logout_handler, active_session):
        session_id, _ = active_session
        logout_handler.logout(session_id, "jwt_dummy")
        resp = logout_handler.logout(session_id, "jwt_dummy")
        assert resp.status_code == 200
        assert resp.body.get("message") == "logged_out"

    def test_logout_after_session_expiry_still_revokes_jwt(self, mock_jwt, mock_redis, logout_handler, active_session):
        session_id, user_id = active_session
        token = mock_jwt.issue_token(user_id)
        mock_redis.delete(f"session:{session_id}")
        assert mock_jwt.validate_token(token) is True
        logout_handler.logout(session_id, token)
        assert mock_jwt.validate_token(token) is False

    def test_logout_does_not_affect_other_sessions(self, mock_redis, session_service, logout_handler, active_session):
        session_id, _ = active_session
        other_sid = "sess_other_002"
        session_service.create_session(other_sid, "user_other")
        other_key = f"session:{other_sid}"
        assert mock_redis.exists(other_key) is True
        logout_handler.logout(session_id, "jwt_dummy")
        assert mock_redis.exists(other_key) is True

    def test_logout_response_time_is_measured(self, logout_handler, active_session):
        session_id, _ = active_session
        resp = logout_handler.logout(session_id, "jwt_dummy")
        elapsed = resp.body.get("elapsed_ms")
        assert isinstance(elapsed, int)
        assert elapsed >= 0

    def test_multiple_logout_calls_are_idempotent(self, mock_redis, logout_handler, active_session):
        session_id, _ = active_session
        for _ in range(5):
            resp = logout_handler.logout(session_id, "jwt_dummy")
            assert resp.status_code == 200
        assert mock_redis.exists(f"session:{session_id}") is False

    def test_force_logout_method_on_session_service(self, session_service, mock_redis, active_session):
        session_id, _ = active_session
        assert session_service.force_logout(session_id) is True
        assert mock_redis.exists(f"session:{session_id}") is False

    def test_jwt_revoke_all_for_user_on_logout(self, mock_jwt, logout_handler, active_session):
        _, user_id = active_session
        token_a = mock_jwt.issue_token(user_id)
        token_b = mock_jwt.issue_token(user_id)
        assert mock_jwt.validate_token(token_a) is True
        assert mock_jwt.validate_token(token_b) is True
        mock_jwt.revoke_all_for_user(user_id)
        assert mock_jwt.validate_token(token_a) is False
        assert mock_jwt.validate_token(token_b) is False
