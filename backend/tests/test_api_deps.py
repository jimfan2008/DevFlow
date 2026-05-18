#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 认证依赖模块测试 (deps.py)
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock


class TestGetCurrentUser:
    """获取当前用户依赖测试"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client, test_user, db_session):
        """测试成功获取当前用户"""
        from app.utils.security import create_access_token

        token = create_access_token(user_id=test_user.id)

        response = await client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token}"},
        )

        # 应该需要认证但不返回 401
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_get_current_user_missing_token(self, client):
        """测试缺少认证 token"""
        response = await client.get("/api/tasks")
        assert response.status_code == 401
        data = response.json()
        assert "auth" in data.get("error", "").lower() or "missing" in data.get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client):
        """测试无效 token"""
        response = await client.get("/api/tasks", headers={"Authorization": "Bearer invalid_token_here"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, client, test_user, db_session):
        """测试过期 token"""
        from datetime import datetime, timedelta
        import jwt
        from app.config import settings

        payload = {"sub": test_user.id, "exp": datetime.utcnow() - timedelta(hours=1)}
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        response = await client.get("/api/tasks", headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_missing_bearer_prefix(self, client):
        """测试缺少 Bearer 前缀"""
        from app.utils.security import create_access_token
        token = create_access_token(user_id="user_001")

        response = await client.get("/api/tasks", headers={"Authorization": token})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_wrong_token_format(self, client):
        """测试 token 格式错误"""
        response = await client.get("/api/tasks", headers={"Authorization": "InvalidFormat token"})
        assert response.status_code == 401


class TestAuthDependencyMocked:
    """认证依赖 Mock 测试"""

    @pytest.mark.asyncio
    async def test_auth_dependency_no_auth_header(self, client):
        """测试没有 Authorization header"""
        response = await client.get("/api/tasks")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_dependency_empty_bearer(self, client):
        """测试空 Bearer token"""
        response = await client.get("/api/tasks", headers={"Authorization": "Bearer "})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_dependency_multiple_tokens(self, client):
        """测试多个 token 头"""
        response = await client.get("/api/tasks", headers={"Authorization": ["Bearer token1", "Bearer token2"]})
        # FastAPI 可能会解析失败或只取第一个
        assert response.status_code == 401 or response.status_code == 422
