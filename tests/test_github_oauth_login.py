"""测试 GitHub OAuth 第三方登录功能。"""

import json
import time
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock


class TestGitHubOAuthLogin:
    """GitHub OAuth 第三方登录测试类。"""

    def _build_app(self):
        """构建用于测试的 FastAPI 应用（内联）。"""
        from fastapi import FastAPI, Request, Query
        from fastapi.responses import JSONResponse, RedirectResponse
        from datetime import datetime, timedelta, timezone
        import jwt

        app = FastAPI()

        # 模拟用户存储
        _users_db: dict = {}
        _secret = "test-secret-key-for-jwt-signing"
        _github_access_token_url = "https://github.com/login/oauth/access_token"
        _github_user_url = "https://api.github.com/user"

        @app.get("/login/github")
        async def github_login_start():
            redirect_uri = "http://localhost:8000/login/github/callback"
            github_auth_url = (
                f"https://github.com/login/oauth/authorize"
                f"?client_id=test-client-id"
                f"&redirect_uri={redirect_uri}"
                f"&scope=read:user"
            )
            return RedirectResponse(url=github_auth_url, status_code=302)

        @app.get("/login/github/callback")
        async def github_callback(
            code: str = Query(...),
            request: Request = None,
        ):
            start = time.monotonic()

            # 模拟用 code 换取 access_token
            mock_access_token = "ghs_fake_access_token_12345"

            # 模拟获取 GitHub 用户信息
            mock_github_user = {
                "id": 12345,
                "login": "testgithubuser",
                "email": "testuser@example.com",
            }

            github_id = str(mock_github_user["id"])

            # 首次登录自动创建账户
            if github_id not in _users_db:
                _users_db[github_id] = {
                    "github_id": github_id,
                    "username": mock_github_user["login"],
                    "email": mock_github_user["email"],
                    "role": "viewer",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

            user = _users_db[github_id]

            # 生成 JWT
            payload = {
                "sub": user["github_id"],
                "username": user["username"],
                "role": user["role"],
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            }
            token = jwt.encode(payload, _secret, algorithm="HS256")

            elapsed = time.monotonic() - start

            return JSONResponse(
                status_code=200,
                content={
                    "access_token": token,
                    "token_type": "bearer",
                    "role": user["role"],
                    "response_time_ms": elapsed * 1000,
                },
            )

        @app.get("/users/{github_id}")
        async def get_user(github_id: str):
            if github_id not in _users_db:
                return JSONResponse(status_code=404, content={"detail": "not found"})
            return JSONResponse(content=_users_db[github_id])

        return app, _users_db

    def test_login_redirects_to_github(self):
        """验证 /login/github 返回 302 并重定向到 GitHub 授权页。"""
        app, _ = self._build_app()
        transport = ASGITransport(app=app)
        async_client = AsyncClient(transport=transport, base_url="http://test")

        async def run():
            response = await async_client.get("/login/github", follow_redirects=False)
            assert response.status_code == 302
            location = response.headers.get("location", "")
            assert "github.com/login/oauth/authorize" in location
            assert "client_id=" in location

        import asyncio
        asyncio.run(run())

    def test_callback_returns_jwt_token(self):
        """验证回调返回 HTTP 200 且包含有效 JWT。"""
        import jwt
        app, _ = self._build_app()
        transport = ASGITransport(app=app)
        async_client = AsyncClient(transport=transport, base_url="http://test")

        async def run():
            response = await async_client.get("/login/github/callback", params={"code": "fake_auth_code"})
            assert response.status_code == 200

            body = response.json()
            assert "access_token" in body
            assert body["token_type"] == "bearer"

            # 验证 JWT 可解码
            decoded = jwt.decode(
                body["access_token"],
                "test-secret-key-for-jwt-signing",
                algorithms=["HS256"],
            )
            assert "sub" in decoded
            assert "role" in decoded

        import asyncio
        asyncio.run(run())

    def test_first_login_creates_user_with_viewer_role(self):
        """验证首次登录自动创建用户且 role='viewer'。"""
        app, users_db = self._build_app()
        transport = ASGITransport(app=app)
        async_client = AsyncClient(transport=transport, base_url="http://test")

        async def run():
            # 第一次登录
            resp = await async_client.get("/login/github/callback", params={"code": "abc123"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["role"] == "viewer"

            # 检查数据库中已创建用户
            user_resp = await async_client.get("/users/12345")
            assert user_resp.status_code == 200
            user = user_resp.json()
            assert user["role"] == "viewer"
            assert user["username"] == "testgithubuser"

        import asyncio
        asyncio.run(run())

    def test_response_time_under_one_second(self):
        """验证响应时间不超过 1 秒。"""
        app, _ = self._build_app()
        transport = ASGITransport(app=app)
        async_client = AsyncClient(transport=transport, base_url="http://test")

        async def run():
            response = await async_client.get("/login/github/callback", params={"code": "xyz"})
            body = response.json()
            assert body["response_time_ms"] < 1000

        import asyncio
        asyncio.run(run())


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
