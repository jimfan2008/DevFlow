import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


SESSION_TIMEOUT_MINUTES = 30
SESSION_WARNING_MINUTES = 5


class SessionManager:
    """Session manager: create, refresh, check session expiry."""

    def __init__(self, redis_client, timeout_minutes: int = SESSION_TIMEOUT_MINUTES):
        self.redis = redis_client
        self.timeout_minutes = timeout_minutes

    def create_session(self, session_id: str, user_id: str, now: datetime | None = None) -> dict:
        current = now or datetime.now(timezone.utc)
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": current.isoformat(),
            "last_activity": current.isoformat(),
            "expires_at": (current + timedelta(minutes=self.timeout_minutes)).isoformat(),
        }
        ttl_seconds = int(timedelta(minutes=self.timeout_minutes).total_seconds())
        self.redis.set(f"session:{session_id}", json.dumps(session_data))
        self.redis.expire(f"session:{session_id}", ttl_seconds)
        return session_data

    def refresh_session(self, session_id: str, now: datetime | None = None) -> dict | None:
        raw = self.redis.get(f"session:{session_id}")
        if raw is None:
            return None
        session_data = json.loads(raw)
        current = now or datetime.now(timezone.utc)
        session_data["last_activity"] = current.isoformat()
        session_data["expires_at"] = (current + timedelta(minutes=self.timeout_minutes)).isoformat()
        ttl_seconds = int(timedelta(minutes=self.timeout_minutes).total_seconds())
        self.redis.set(f"session:{session_id}", json.dumps(session_data))
        self.redis.expire(f"session:{session_id}", ttl_seconds)
        return session_data

    def check_session(self, session_id: str, now: datetime | None = None) -> dict | None:
        raw = self.redis.get(f"session:{session_id}")
        if raw is None:
            return None
        session_data = json.loads(raw)
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        current = now or datetime.now(timezone.utc)
        if current >= expires_at:
            self.redis.delete(f"session:{session_id}")
            return None
        return session_data

    def get_remaining_time(self, session_id: str, now: datetime | None = None) -> int:
        raw = self.redis.get(f"session:{session_id}")
        if raw is None:
            return 0
        session_data = json.loads(raw)
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        current = now or datetime.now(timezone.utc)
        delta = expires_at - current
        return max(0, int(delta.total_seconds()))

    def cleanup_expired_sessions(self, now: datetime | None = None) -> list:
        keys = self.redis.keys("session:*")
        cleaned = []
        current = now or datetime.now(timezone.utc)
        for key in keys:
            raw = self.redis.get(key)
            if raw is None:
                continue
            session_data = json.loads(raw)
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            if current >= expires_at:
                self.redis.delete(key)
                cleaned.append(session_data["session_id"])
        return cleaned


class SessionMiddleware:
    """WSGI/middleware layer session interception."""

    def __init__(self, session_manager: SessionManager):
        self.sm = session_manager

    def handle_request(self, session_id: str | None, now: datetime | None = None) -> tuple:
        if not session_id:
            return (401, {"error": "not logged in", "redirect": "/login"})
        session_data = self.sm.check_session(session_id, now=now)
        if session_data is None:
            return (401, {"error": "session expired", "redirect": "/login"})
        return (200, {"status": "ok", "user_id": session_data["user_id"]})


class SessionFrontendService:
    """Frontend session expiry warning service."""

    def __init__(self, session_manager: SessionManager):
        self.sm = session_manager

    def check_expiring_warning(self, session_id: str, now: datetime | None = None) -> dict:
        remaining = self.sm.get_remaining_time(session_id, now=now)
        warning_threshold = SESSION_WARNING_MINUTES * 60
        if remaining > 0 and remaining <= warning_threshold:
            return {
                "warning": True,
                "message": "session about to expire",
                "remaining_seconds": remaining,
            }
        if remaining > warning_threshold:
            return {"warning": False, "remaining_seconds": remaining}
        return {"warning": True, "message": "session expired", "remaining_seconds": 0}


class MockRedis:
    """In-memory Redis DB2 mock."""

    def __init__(self):
        self._store: dict = {}
        self._expiry: dict = {}
        self._clock: datetime | None = None

    def set(self, key: str, value: str):
        self._store[key] = value

    def get(self, key: str):
        if key in self._expiry:
            now = self._clock or datetime.now(timezone.utc)
            if now >= self._expiry[key]:
                del self._store[key]
                del self._expiry[key]
                return None
        return self._store.get(key)

    def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            if key in self._expiry:
                del self._expiry[key]
            return 1
        return 0

    def expire(self, key: str, ttl: int):
        now = self._clock or datetime.now(timezone.utc)
        self._expiry[key] = now + timedelta(seconds=ttl)

    def keys(self, pattern: str) -> list:
        import fnmatch
        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    def set_clock(self, dt: datetime):
        self._clock = dt

    def reset(self):
        self._store.clear()
        self._expiry.clear()
        self._clock = None


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
def session_manager(mock_redis):
    return SessionManager(mock_redis, timeout_minutes=SESSION_TIMEOUT_MINUTES)


@pytest.fixture
def middleware(session_manager):
    return SessionMiddleware(session_manager)


@pytest.fixture
def frontend_service(session_manager):
    return SessionFrontendService(session_manager)


@pytest.fixture
def active_session(session_manager, mock_redis):
    mock_redis.reset()
    t0 = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
    mock_redis.set_clock(t0)
    sid = "test-session-001"
    session_manager.create_session(sid, "user-42", now=t0)
    return sid, t0


class TestSessionTimeoutAutoLogout:

    def test_return_http_401_when_session_expired(self, session_manager, mock_redis, active_session):
        sid, t0 = active_session
        future = t0 + timedelta(minutes=31)
        result = session_manager.check_session(sid, now=future)
        assert result is None, "expired session should return None"

    def test_redirect_to_login_page_on_401(self, middleware, active_session):
        sid, t0 = active_session
        future = t0 + timedelta(minutes=31)
        status_code, body = middleware.handle_request(sid, now=future)
        assert status_code == 401
        assert body["redirect"] == "/login"

    def test_no_session_returns_401_and_redirect(self, middleware):
        status_code, body = middleware.handle_request(None)
        assert status_code == 401
        assert body["redirect"] == "/login"

    def test_frontend_warning_5_minutes_before_expiry(self, session_manager, mock_redis, frontend_service):
        mock_redis.reset()
        t0 = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_redis.set_clock(t0)
        sid = "warning-test-session"
        session_manager.create_session(sid, "user-42", now=t0)
        t_check = t0 + timedelta(minutes=25, seconds=1)
        mock_redis.set_clock(t_check)
        result = frontend_service.check_expiring_warning(sid, now=t_check)
        assert result["warning"] is True
        assert result["message"] == "session about to expire"
        assert result["remaining_seconds"] <= 300

    def test_frontend_no_warning_when_plenty_of_time_left(self, frontend_service, active_session):
        sid, t0 = active_session
        result = frontend_service.check_expiring_warning(sid, now=t0)
        assert result["warning"] is False

    def test_frontend_warning_at_exactly_5_minutes(self, session_manager, mock_redis, frontend_service):
        mock_redis.reset()
        t0 = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_redis.set_clock(t0)
        sid = "exact-5min-session"
        session_manager.create_session(sid, "user-42", now=t0)
        t_check = t0 + timedelta(minutes=25)
        mock_redis.set_clock(t_check)
        result = frontend_service.check_expiring_warning(sid, now=t_check)
        assert result["warning"] is True
        assert result["message"] == "session about to expire"

    def test_redis_db2_session_cleared_on_expiry(self, session_manager, mock_redis, active_session):
        sid, t0 = active_session
        future = t0 + timedelta(minutes=31)
        mock_redis.set_clock(future)
        session_manager.check_session(sid, now=future)
        raw = mock_redis.get(f"session:{sid}")
        assert raw is None, "expired session should be removed from Redis"

    def test_cleanup_expired_sessions_removes_all_expired(self, session_manager, mock_redis):
        mock_redis.reset()
        t0 = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        session_manager.create_session("sess-a", "user-a", now=t0)
        session_manager.create_session("sess-b", "user-b", now=t0)
        old_data = {
            "session_id": "sess-a",
            "user_id": "user-a",
            "created_at": (t0 - timedelta(hours=1)).isoformat(),
            "last_activity": (t0 - timedelta(hours=1)).isoformat(),
            "expires_at": (t0 - timedelta(minutes=1)).isoformat(),
        }
        mock_redis.set("session:sess-a", json.dumps(old_data))
        cleaned = session_manager.cleanup_expired_sessions(now=t0)
        assert "sess-a" in cleaned
        assert "sess-b" not in cleaned
        assert mock_redis.get("session:sess-a") is None
        assert mock_redis.get("session:sess-b") is not None

    def test_refresh_session_extends_expiry(self, session_manager, mock_redis, active_session):
        sid, t0 = active_session
        t10 = t0 + timedelta(minutes=10)
        refreshed = session_manager.refresh_session(sid, now=t10)
        assert refreshed is not None
        t30 = t10 + timedelta(minutes=20)
        still_valid = session_manager.check_session(sid, now=t30)
        assert still_valid is not None, "refreshed session should still be valid after 20 minutes"

    def test_valid_session_returns_200(self, middleware, active_session):
        sid, t0 = active_session
        status_code, body = middleware.handle_request(sid, now=t0)
        assert status_code == 200
        assert body["user_id"] == "user-42"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
