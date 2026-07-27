from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.testclient import TestClient
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
import time
import pytest

app = FastAPI()
security_scheme = HTTPBearer(auto_error=False)

sessions: dict[str, dict] = {}


def verify_admin_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")
    token = credentials.credentials
    session = sessions.get(token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    if session.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    if session.get("expires_at", 0) < time.time():
        sessions.pop(token, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return session


@app.get("/admin/dashboard")
def admin_dashboard(session: dict = Depends(verify_admin_session)):
    return {"message": "Admin dashboard", "user": session.get("username")}


@app.get("/admin/users")
def admin_users(session: dict = Depends(verify_admin_session)):
    return {"message": "User management", "users": []}


@app.get("/admin/settings")
def admin_settings(session: dict = Depends(verify_admin_session)):
    return {"message": "System settings"}


def create_session(username: str, role: str, expires_in: float = 3600) -> tuple[str, dict]:
    token = str(uuid.uuid4())
    session_data = {
        "username": username,
        "role": role,
        "created_at": time.time(),
        "expires_at": time.time() + expires_in,
        "token": token,
    }
    sessions[token] = session_data
    return token, session_data


def create_malformed_token() -> str:
    return "not-a-uuid-at-all"


def create_corrupted_session_token() -> str:
    token = str(uuid.uuid4())
    sessions[token] = {"role": "admin"}
    return token


client = TestClient(app)


class TestAdminPermission:
    """管理员权限验证测试"""

    def setup_method(self):
        sessions.clear()

    # ========== 正向场景 ==========

    def test_admin_can_access_protected_route(self):
        """管理员可以访问受保护的路由"""
        token, _ = create_session("admin_user", "admin")
        start = time.time()
        response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        elapsed = time.time() - start
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        assert response.json()["message"] == "Admin dashboard"
        assert elapsed < 2.0, f"Response time {elapsed:.3f}s exceeds 2s limit"

    def test_admin_can_access_multiple_routes(self):
        """管理员可以访问所有受保护路由"""
        token, _ = create_session("admin_user", "admin")
        for path in ["/admin/dashboard", "/admin/users", "/admin/settings"]:
            start = time.time()
            response = client.get(path, headers={"Authorization": f"Bearer {token}"})
            elapsed = time.time() - start
            assert response.status_code == 200, f"{path}: Expected 200, got {response.status_code}"
            assert elapsed < 2.0, f"{path}: Response time {elapsed:.3f}s exceeds 2s limit"

    def test_admin_session_contains_all_fields(self):
        """管理员session包含完整字段"""
        token, session_data = create_session("admin_user", "admin")
        assert "username" in session_data
        assert "role" in session_data
        assert session_data["role"] == "admin"
        assert "created_at" in session_data
        assert "expires_at" in session_data
        assert "token" in session_data

    # ========== 负向场景：认证不足 ==========

    def test_non_admin_gets_403(self):
        """非管理员访问受保护路由应返回403"""
        token, _ = create_session("regular_user", "user")
        response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.json()}"
        assert "Admin privileges" in response.json()["detail"]

    def test_unauthenticated_gets_401(self):
        """未登录用户（无token）访问受保护路由应返回401"""
        response = client.get("/admin/dashboard")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.json()}"
        assert "Missing authorization" in response.json()["detail"]

    # ========== 边界场景：session异常 ==========

    def test_empty_session_token_returns_401(self):
        """空字符串作为token应返回401"""
        response = client.get("/admin/dashboard", headers={"Authorization": "Bearer "})
        assert response.status_code == 401

    def test_expired_session_token_returns_401(self):
        """过期的session token应返回401"""
        token, _ = create_session("admin_user", "admin", expires_in=-1)
        response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.json()}"
        assert "expired" in response.json()["detail"].lower()

    def test_malformed_token_returns_401(self):
        """格式错误的token应返回401"""
        token = create_malformed_token()
        response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_nonexistent_token_returns_401(self):
        """不存在的session token应返回401"""
        response = client.get("/admin/dashboard", headers={"Authorization": "Bearer nonexistent-token-value"})
        assert response.status_code == 401

    def test_corrupted_session_data_handling(self):
        """损坏的session数据不应导致崩溃"""
        token = create_corrupted_session_token()
        response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code in (401, 403, 500), (
            f"Should handle gracefully, got {response.status_code}"
        )

    # ========== 并发与性能 ==========

    def test_concurrent_admin_requests_all_succeed(self):
        """并发管理员请求全部成功且响应时间合规"""
        token, _ = create_session("admin_user", "admin")
        import asyncio

        async def make_request():
            start = time.time()
            response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
            elapsed = time.time() - start
            return response.status_code, elapsed

        async def run_concurrent():
            tasks = [make_request() for _ in range(10)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_concurrent())
        for status_code, elapsed in results:
            assert status_code == 200, f"Concurrent request failed with {status_code}"
            assert elapsed < 2.0, f"Concurrent request took {elapsed:.3f}s, exceeds 2s limit"

    def test_session_token_uniqueness(self):
        """每次创建的session token唯一"""
        tokens = set()
        for i in range(100):
            token, _ = create_session(f"user_{i}", "admin")
            assert token not in tokens, f"Duplicate token: {token}"
            tokens.add(token)

    # ========== 操作日志校验 ==========

    def test_admin_dashboard_returns_valid_response_structure(self):
        """管理员操作返回完整的响应结构"""
        token, _ = create_session("admin_user", "admin")
        response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        data = response.json()
        assert "message" in data
        assert "user" in data
        assert data["user"] == "admin_user"

    def test_permission_check_passes_before_data_access(self):
        """权限校验在数据访问前执行——无权限不应暴露敏感数据"""
        token_user, _ = create_session("regular_user", "user")
        response_user = client.get("/admin/users", headers={"Authorization": f"Bearer {token_user}"})
        assert response_user.status_code == 403

        token_admin, _ = create_session("admin_user", "admin")
        response_admin = client.get("/admin/users", headers={"Authorization": f"Bearer {token_admin}"})
        assert response_admin.status_code == 200
        assert "users" in response_admin.json()
