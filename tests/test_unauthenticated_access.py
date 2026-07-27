import pytest
import time
from fastapi import FastAPI, HTTPException, Depends


def create_app():
    """创建模拟 FastAPI 应用，包含受保护的路由"""
    app = FastAPI()

    def get_current_user(authorization: str = None):
        """模拟认证依赖：无 token 或 token 无效时抛出 401"""
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "AUTH-001",
                    "message": "未认证，请先登录",
                },
            )
        token = authorization[len("Bearer "):]
        if not token or token == "invalid_token_xyz":
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "AUTH-001",
                    "message": "未认证，请先登录",
                },
            )
        return {"user_id": 1, "username": "testuser"}

    @app.get("/api/protected")
    def protected_endpoint(user: dict = Depends(get_current_user)):
        return {"message": "success", "user": user}

    return app


class TestUnauthenticatedAccessProtectedAPI:
    """验证未登录用户访问需要认证的API时返回401"""

    @pytest.fixture
    def app(self):
        return create_app()

    @pytest.mark.asyncio
    async def test_unauthenticated_access_returns_401(self, app):
        """未携带 token 访问受保护接口应返回 401"""
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.monotonic()
            response = await client.get("/api/protected")
            elapsed_ms = (time.monotonic() - start) * 1000

            assert response.status_code == 401
            body = response.json()
            detail = body.get("detail", {})
            if isinstance(detail, dict):
                assert detail["code"] == "AUTH-001"
            assert elapsed_ms <= 100

    @pytest.mark.asyncio
    async def test_unauthenticated_access_with_invalid_token_returns_401(self, app):
        """携带无效 token 访问受保护接口应返回 401"""
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.monotonic()
            response = await client.get(
                "/api/protected",
                headers={"Authorization": "Bearer invalid_token_xyz"},
            )
            elapsed_ms = (time.monotonic() - start) * 1000

            assert response.status_code == 401
            body = response.json()
            detail = body.get("detail", {})
            if isinstance(detail, dict):
                assert detail["code"] == "AUTH-001"
            assert elapsed_ms <= 100

    @pytest.mark.asyncio
    async def test_unauthenticated_access_without_authorization_header_returns_401(self, app):
        """完全不携带 Authorization 头访问受保护接口应返回 401"""
        from httpx import AsyncClient, ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.monotonic()
            response = await client.get("/api/protected", headers={})
            elapsed_ms = (time.monotonic() - start) * 1000

            assert response.status_code == 401
            body = response.json()
            detail = body.get("detail", {})
            if isinstance(detail, dict):
                assert detail["code"] == "AUTH-001"
            assert elapsed_ms <= 100
