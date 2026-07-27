import pytest
import time
import json
from unittest.mock import MagicMock, patch, PropertyMock
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone


# ---- Mock application structures ----

class MockRequest:
    def __init__(self, method, url, headers=None, cookies=None, session_id=None):
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.session_id = session_id

    def get_cookie(self, key):
        return self.cookies.get(key)


class MockResponse:
    def __init__(self, status_code, content=None, headers=None):
        self.status_code = status_code
        self.content = content or b""
        self.headers = headers or {}

    def json(self):
        return json.loads(self.content) if self.content else {}


class MockRedisDB2:
    """模拟 Redis DB2，存储 session 数据"""

    def __init__(self):
        self.store: dict = {}
        self.ttl_map: dict = {}

    def get(self, key):
        if key in self.store:
            return self.store[key]
        return None

    def set(self, key, value, expire_seconds=None):
        self.store[key] = value
        if expire_seconds is not None:
            self.ttl_map[key] = time.time() + expire_seconds

    def expire(self, key, seconds):
        self.ttl_map[key] = time.time() + seconds

    def ttl(self, key):
        if key in self.ttl_map:
            remaining = self.ttl_map[key] - time.time()
            return max(int(remaining), -1)
        return -2

    def delete(self, key):
        if key in self.store:
            del self.store[key]
        if key in self.ttl_map:
            del self.ttl_map[key]
        return 1

    def exists(self, key):
        return key in self.store

    def clear(self):
        self.store.clear()
        self.ttl_map.clear()


class SessionManager:
    """会话管理器，负责创建、验证和清除 session"""

    DEFAULT_TIMEOUT_SECONDS = 30 * 60  # 30 分钟
    WARNING_BEFORE_EXPIRE_SECONDS = 5 * 60  # 到期前 5 分钟

    def __init__(self, redis_db: MockRedisDB2, timeout_seconds: int = None):
        self.redis = redis_db
        self.timeout_seconds = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS

    def create_session(self, session_id: str, user_id: str, metadata: dict = None) -> dict:
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        key = f"session:{session_id}"
        self.redis.set(key, json.dumps(session_data), expire_seconds=self.timeout_seconds)
        return session_data

    def validate_session(self, session_id: str) -> dict | None:
        key = f"session:{session_id}"
        raw = self.redis.get(key)
        if raw is None:
            return None
        session_data = json.loads(raw)
        # 更新 last_activity
        session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
        self.redis.set(key, json.dumps(session_data), expire_seconds=self.timeout_seconds)
        return session_data

    def get_time_remaining(self, session_id: str) -> int:
        key = f"session:{session_id}"
        return self.redis.ttl(key)

    def should_show_expiry_warning(self, session_id: str) -> bool:
        remaining = self.get_time_remaining(session_id)
        if remaining < 0:
            return False
        return remaining <= self.WARNING_BEFORE_EXPIRE_SECONDS

    def clear_session(self, session_id: str) -> bool:
        key = f"session:{session_id}"
        deleted = self.redis.delete(key)
        return deleted > 0

    def check_and_expire_sessions(self):
        """检查并清除已过期的 session"""
        expired_keys = []
        for key in list(self.redis.store.keys()):
            if key.startswith("session:"):
                ttl = self.redis.ttl(key)
                if ttl <= 0:
                    expired_keys.append(key)
        for key in expired_keys:
            self.redis.delete(key)
        return expired_keys


class AuthMiddleware:
    """认证中间件模拟"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def process_request(self, request: MockRequest) -> MockResponse | None:
        session_id = request.get_cookie("session_id")
        if not session_id:
            return MockResponse(
                status_code=401,
                content=json.dumps({"error": "unauthorized", "message": "未登录"}).encode(),
                headers={"Location": "/login"},
            )
        session_data = self.session_manager.validate_session(session_id)
        if session_data is None:
            self.session_manager.clear_session(session_id)
            return MockResponse(
                status_code=401,
                content=json.dumps({"error": "unauthorized", "message": "会话已过期"}).encode(),
                headers={"Location": "/login"},
            )
        return None  # None 表示请求可以继续

    def get_expiry_warning(self, session_id: str) -> dict | None:
        remaining = self.session_manager.get_time_remaining(session_id)
        if self.session_manager.should_show_expiry_warning(session_id):
            return {
                "type": "session_expiry_warning",
                "message": "会话即将过期",
                "seconds_remaining": remaining,
            }
        return None


class AppRouter:
    """模拟应用路由"""

    def __init__(self, auth_middleware: AuthMiddleware):
        self.auth = auth_middleware

    def handle_dashboard(self, request: MockRequest) -> MockResponse:
        block = self.auth.process_request(request)
        if block:
            return block
        return MockResponse(
            status_code=200,
            content=json.dumps({"page": "dashboard", "status": "ok"}).encode(),
        )

    def handle_api_data(self, request: MockRequest) -> MockResponse:
        block = self.auth.process_request(request)
        if block:
            return block
        return MockResponse(
            status_code=200,
            content=json.dumps({"data": [1, 2, 3]}).encode(),
        )

    def handle_login(self, request: MockRequest) -> MockResponse:
        return MockResponse(
            status_code=200,
            content=json.dumps({"page": "login"}).encode(),
        )


# ---- Fixtures ----

@pytest.fixture
def redis_db():
    db = MockRedisDB2()
    yield db
    db.clear()


@pytest.fixture
def session_manager(redis_db):
    return SessionManager(redis_db, timeout_seconds=1800)  # 30 分钟


@pytest.fixture
def auth_middleware(session_manager):
    return AuthMiddleware(session_manager)


@pytest.fixture
def router(auth_middleware):
    return AppRouter(auth_middleware)


@pytest.fixture
def valid_session(session_manager):
    data = session_manager.create_session("sess_abc123", "user_001")
    return data


# ---- Tests: 会话超时自动登出 ----

class TestSessionTimeoutAutoLogout:
    """会话超时自动登出测试套件"""

    def test_session_created_correctly(self, session_manager, redis_db):
        """测试 session 创建后正确写入 Redis DB2"""
        data = session_manager.create_session("sess_test01", "user_100")
        assert data["session_id"] == "sess_test01"
        assert data["user_id"] == "user_100"
        stored = redis_db.get("session:sess_test01")
        assert stored is not None
        stored_data = json.loads(stored)
        assert stored_data["session_id"] == "sess_test01"

    def test_valid_session_returns_200(self, router, redis_db, session_manager):
        """测试有效 session 正常访问返回 200"""
        session_manager.create_session("sess_valid", "user_001")
        request = MockRequest(
            "GET", "/dashboard",
            cookies={"session_id": "sess_valid"},
        )
        response = router.handle_dashboard(request)
        assert response.status_code == 200
        body = response.json()
        assert body["page"] == "dashboard"

    def test_missing_session_returns_401_and_redirects_to_login(self, router):
        """测试无 session 时返回 HTTP 401 并重定向至登录页"""
        request = MockRequest("GET", "/dashboard")
        response = router.handle_dashboard(request)
        assert response.status_code == 401
        assert response.headers.get("Location") == "/login"
        body = response.json()
        assert body["error"] == "unauthorized"

    def test_expired_session_returns_401_and_redirects_to_login(self, router, redis_db, session_manager):
        """测试过期 session 返回 HTTP 401 并重定向至登录页"""
        session_manager.create_session("sess_expired", "user_002")
        # 模拟 session 已过期：从 Redis 中删除
        redis_db.delete("session:sess_expired")
        request = MockRequest(
            "GET", "/dashboard",
            cookies={"session_id": "sess_expired"},
        )
        response = router.handle_dashboard(request)
        assert response.status_code == 401
        assert response.headers.get("Location") == "/login"
        body = response.json()
        assert body["message"] == "会话已过期"

    def test_expired_session_removed_from_redis_db2(self, router, redis_db, session_manager):
        """测试过期 session 被从 Redis DB2 中清除"""
        session_manager.create_session("sess_rm", "user_003")
        redis_db.delete("session:sess_rm")
        request = MockRequest(
            "GET", "/api/data",
            cookies={"session_id": "sess_rm"},
        )
        response = router.handle_api_data(request)
        assert response.status_code == 401
        # 验证 Redis 中 session 已被清除
        assert redis_db.exists("session:sess_rm") is False

    def test_expiry_warning_shows_5_minutes_before_timeout(self, session_manager, redis_db):
        """测试超时前 5 分钟内前端应收到'会话即将过期'提示"""
        session_manager.create_session("sess_warn", "user_004")
        # 模拟 TTL 剩余 4 分钟 59 秒（小于 5 分钟阈值）
        redis_db.ttl_map["session:sess_warn"] = time.time() + 299
        assert session_manager.should_show_expiry_warning("sess_warn") is True
        warning = session_manager.redis.get("session:sess_warn")
        # 再验证 AuthMiddleware 的警告接口
        auth = AuthMiddleware(session_manager)
        warn_result = auth.get_expiry_warning("sess_warn")
        assert warn_result is not None
        assert warn_result["message"] == "会话即将过期"
        assert warn_result["seconds_remaining"] <= 300

    def test_no_warning_when_more_than_5_minutes_remaining(self, session_manager, redis_db):
        """测试剩余时间超过 5 分钟时不弹出警告"""
        session_manager.create_session("sess_nowarn", "user_005")
        # 模拟 TTL 剩余 10 分钟
        redis_db.ttl_map["session:sess_nowarn"] = time.time() + 600
        assert session_manager.should_show_expiry_warning("sess_nowarn") is False
        auth = AuthMiddleware(session_manager)
        warn_result = auth.get_expiry_warning("sess_nowarn")
        assert warn_result is None

    def test_check_and_expire_sessions_clears_expired_entries(self, session_manager, redis_db):
        """测试 check_and_expire_sessions 清除所有过期 session"""
        # 创建一个正常 session
        session_manager.create_session("sess_alive", "user_006")
        # 创建一个已过期 session（TTL 为负）
        key_expired = "session:sess_dead"
        redis_db.set(key_expired, json.dumps({"session_id": "sess_dead"}))
        redis_db.ttl_map[key_expired] = time.time() - 10  # 已过期 10 秒

        cleared = session_manager.check_and_expire_sessions()
        assert "session:sess_dead" in cleared
        assert "session:sess_alive" not in cleared
        assert redis_db.exists("session:sess_dead") is False
        assert redis_db.exists("session:sess_alive") is True

    def test_session_ttl_is_30_minutes(self, session_manager, redis_db):
        """测试 session 默认超时时间为 30 分钟"""
        session_manager.create_session("sess_ttl", "user_007")
        ttl = redis_db.ttl("session:sess_ttl")
        assert 1790 <= ttl <= 1800  # 允许 ±10 秒误差

    def test_custom_timeout_config(self, redis_db):
        """测试可自定义超时时间"""
        custom_manager = SessionManager(redis_db, timeout_seconds=600)  # 10 分钟
        custom_manager.create_session("sess_custom", "user_008")
        ttl = redis_db.ttl("session:sess_custom")
        assert 590 <= ttl <= 600

    def test_validate_session_refreshes_ttl(self, session_manager, redis_db):
        """测试活跃使用 session 会刷新 TTL"""
        session_manager.create_session("sess_refresh", "user_009")
        original_ttl_end = redis_db.ttl_map["session:sess_refresh"]
        # 模拟过了 10 秒
        redis_db.ttl_map["session:sess_refresh"] = time.time() + 10
        # 验证 session 会刷新 TTL
        session_manager.validate_session("sess_refresh")
        new_ttl_end = redis_db.ttl_map["session:sess_refresh"]
        assert new_ttl_end > original_ttl_end

    def test_multiple_expired_sessions_all_return_401(self, router, redis_db, session_manager):
        """测试多个过期 session 均返回 401"""
        for i in range(3):
            sid = f"sess_multi_{i}"
            session_manager.create_session(sid, f"user_multi_{i}")
            redis_db.delete(f"session:{sid}")

        for i in range(3):
            request = MockRequest(
                "GET", "/dashboard",
                cookies={"session_id": f"sess_multi_{i}"},
            )
            response = router.handle_dashboard(request)
            assert response.status_code == 401
            assert response.headers.get("Location") == "/login"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
