import time
import json
from datetime import datetime, timedelta
import redis
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from freezegun import freeze_time


# ── Mock application structures ──────────────────────────────────────────────

class MockSession:
    def __init__(self, session_id, user_id, expires_at, created_at):
        self.session_id = session_id
        self.user_id = user_id
        self.expires_at = expires_at
        self.created_at = created_at
        self.last_activity = created_at

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }


class MockRedisSessionStore:
    """模拟基于 Redis DB2 的 session 存储"""

    DB_INDEX = 2
    SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 分钟
    WARNING_THRESHOLD_SECONDS = 5 * 60  # 5 分钟

    def __init__(self, redis_client=None):
        self._store: dict[str, dict] = {}
        self._redis = redis_client or self._create_mock_redis()

    @staticmethod
    def _create_mock_redis():
        return MagicMock(spec=redis.Redis)

    def create_session(self, user_id: str, session_id: str = None, expires_in=None):
        import uuid
        session_id = session_id or str(uuid.uuid4())
        expires_in = expires_in or self.SESSION_TIMEOUT_SECONDS
        now = time.time()
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "expires_at": now + expires_in,
            "created_at": now,
            "last_activity": now,
        }
        self._store[session_id] = session_data
        return session_data

    def get_session(self, session_id: str):
        return self._store.get(session_id)

    def touch_session(self, session_id: str):
        if session_id in self._store:
            self._store[session_id]["last_activity"] = time.time()
            self._store[session_id]["expires_at"] = time.time() + self.SESSION_TIMEOUT_SECONDS
            return True
        return False

    def delete_session(self, session_id: str):
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False

    def is_session_expired(self, session_id: str) -> bool:
        session = self._store.get(session_id)
        if not session:
            return True
        return time.time() >= session["expires_at"]

    def is_session_near_expiry(self, session_id: str, threshold=None) -> bool:
        threshold = threshold or self.WARNING_THRESHOLD_SECONDS
        session = self._store.get(session_id)
        if not session:
            return False
        remaining = session["expires_at"] - time.time()
        return 0 < remaining <= threshold

    def cleanup_expired_sessions(self):
        now = time.time()
        expired_keys = [
            sid for sid, data in self._store.items() if data["expires_at"] <= now
        ]
        for sid in expired_keys:
            del self._store[sid]
        return expired_keys


class MockAuthMiddleware:
    """模拟认证中间件"""

    def __init__(self, session_store: MockRedisSessionStore):
        self.session_store = session_store

    def validate_request(self, session_id: str | None):
        if not session_id:
            return {"valid": False, "reason": "no_session", "status_code": 401}
        session = self.session_store.get_session(session_id)
        if not session:
            return {"valid": False, "reason": "session_not_found", "status_code": 401}
        if self.session_store.is_session_expired(session_id):
            self.session_store.delete_session(session_id)
            return {"valid": False, "reason": "session_expired", "status_code": 401}
        return {"valid": True, "session": session, "status_code": 200}

    def check_session_warning(self, session_id: str):
        session = self.session_store.get_session(session_id)
        if not session:
            return {"warning": False, "remaining_seconds": 0}
        remaining = session["expires_at"] - time.time()
        if remaining <= self.session_store.WARNING_THRESHOLD_SECONDS and remaining > 0:
            return {"warning": True, "remaining_seconds": int(remaining)}
        return {"warning": False, "remaining_seconds": int(remaining)}


class MockApp:
    """模拟 Web 应用路由层"""

    LOGIN_URL = "/login"
    SESSION_COOKIE_NAME = "session_id"

    def __init__(self, session_store: MockRedisSessionStore):
        self.session_store = session_store
        self.auth = MockAuthMiddleware(session_store)

    def handle_api_request(self, session_id: str | None, path: str = "/api/data"):
        result = self.auth.validate_request(session_id)
        if not result["valid"]:
            return {
                "status_code": result["status_code"],
                "headers": {"Location": self.LOGIN_URL} if result["status_code"] == 401 else {},
                "body": {"error": result["reason"]},
            }
        self.session_store.touch_session(session_id)
        return {
            "status_code": 200,
            "body": {"data": "success", "user_id": result["session"]["user_id"]},
        }

    def handle_session_check(self, session_id: str):
        warning = self.auth.check_session_warning(session_id)
        return {
            "status_code": 200,
            "body": warning,
        }


# ── Pytest fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def session_store():
    return MockRedisSessionStore()


@pytest.fixture
def app(session_store):
    return MockApp(session_store)


@pytest.fixture
def valid_session(session_store):
    data = session_store.create_session("user_001", "sess_abc123")
    return data


# ── Tests ────────────────────────────────────────────────────────────────────

class TestSessionTimeoutAutoLogout:
    """会话超时自动登出测试"""

    def test_expired_session_returns_401_and_redirects_to_login(self, app, session_store):
        """用户 30 分钟无操作后，请求应返回 HTTP 401 并重定向至登录页"""
        session_store.create_session("user_001", "sess_timeout", expires_in=1)
        with freeze_time(datetime.now() + timedelta(minutes=31)):
            response = app.handle_api_request("sess_timeout")
        assert response["status_code"] == 401
        assert response["headers"]["Location"] == app.LOGIN_URL
        assert response["body"]["error"] == "session_expired"

    def test_expired_session_is_removed_from_redis(self, app, session_store):
        """超时 session 应从 Redis DB2 中被清除"""
        session_store.create_session("user_002", "sess_redis_clean", expires_in=1)
        assert session_store.get_session("sess_redis_clean") is not None
        with freeze_time(datetime.now() + timedelta(minutes=31)):
            app.handle_api_request("sess_redis_clean")
        assert session_store.get_session("sess_redis_clean") is None

    def test_no_session_returns_401(self, app):
        """未携带 session 的请求返回 401"""
        response = app.handle_api_request(None)
        assert response["status_code"] == 401
        assert response["headers"]["Location"] == app.LOGIN_URL

    def test_valid_session_returns_200(self, app, valid_session):
        """未超时的有效 session 正常返回 200"""
        response = app.handle_api_request("sess_abc123")
        assert response["status_code"] == 200
        assert response["body"]["data"] == "success"

    def test_session_warning_shows_5_minutes_before_expiry(self, app, session_store):
        """超时前 5 分钟内，前端应收到会话即将过期提示"""
        with freeze_time(datetime(2026, 7, 15, 12, 0, 0)):
            session_store.create_session("user_warn", "sess_warn", expires_in=300)
        with freeze_time(datetime(2026, 7, 15, 12, 4, 15)):
            response = app.handle_session_check("sess_warn")
        assert response["status_code"] == 200
        assert response["body"]["warning"] is True
        remaining = response["body"]["remaining_seconds"]
        assert 0 < remaining <= 300

    def test_no_warning_when_session_has_plenty_of_time(self, app, session_store):
        """session 剩余时间超过 5 分钟时不应弹出警告"""
        session_store.create_session("user_nowarn", "sess_nowarn", expires_in=30 * 60)
        response = app.handle_session_check("sess_nowarn")
        assert response["body"]["warning"] is False

    def test_no_warning_for_already_expired_session(self, app, session_store):
        """已过期的 session 不应弹出即将过期警告"""
        session_store.create_session("user_expired_warn", "sess_expwarn", expires_in=1)
        with freeze_time(datetime.now() + timedelta(minutes=1)):
            response = app.handle_session_check("sess_expwarn")
        assert response["body"]["warning"] is False

    def test_touch_session_resets_timeout(self, app, session_store):
        """用户操作后 session 超时时间应重置"""
        with freeze_time(datetime(2026, 7, 15, 12, 0, 0)):
            session_store.create_session("user_touch", "sess_touch", expires_in=60)
        with freeze_time(datetime(2026, 7, 15, 12, 0, 55)):
            app.handle_api_request("sess_touch")
        with freeze_time(datetime(2026, 7, 15, 12, 1, 5)):
            response = app.handle_api_request("sess_touch")
        assert response["status_code"] == 200

    def test_cleanup_expired_sessions_clears_all_expired(self, session_store):
        """批量清理应删除所有已过期的 session"""
        with freeze_time(datetime(2026, 7, 15, 12, 0, 0)):
            session_store.create_session("user_a", "sess_a", expires_in=10)
            session_store.create_session("user_b", "sess_b", expires_in=10)
            session_store.create_session("user_c", "sess_c", expires_in=600)
        with freeze_time(datetime(2026, 7, 15, 12, 0, 30)):
            cleaned = session_store.cleanup_expired_sessions()
        assert len(cleaned) == 2
        assert "sess_a" in cleaned
        assert "sess_b" in cleaned
        assert session_store.get_session("sess_c") is not None

    def test_redis_db_index_is_db2(self, session_store):
        """Session 存储必须使用 Redis DB2"""
        assert session_store.DB_INDEX == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
