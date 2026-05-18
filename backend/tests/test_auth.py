#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 认证模块测试
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import jwt


class TestAuthRegistration:
    """用户注册测试"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client, db_session):
        """测试成功注册用户"""
        payload = {
            "username": "new_user",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        response = await client.post("/api/auth/register", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data["user"]
        assert data["user"]["username"] == "new_user"
        assert data["user"]["email"] == "newuser@example.com"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client, test_user, db_session):
        """测试重复用户名注册"""
        payload = {
            "username": "test_user",  # 已存在
            "email": "different@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        response = await client.post("/api/auth/register", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "username" in data["error"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user, db_session):
        """测试重复邮箱注册"""
        payload = {
            "username": "another_user",
            "email": "test@example.com",  # 已存在
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        response = await client.post("/api/auth/register", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "email" in data["error"]
    
    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, client, db_session):
        """测试密码不一致"""
        payload = {
            "username": "new_user",
            "email": "newuser2@example.com",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!"
        }
        
        response = await client.post("/api/auth/register", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "password" in data["error"]
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, client, db_session):
        """测试弱密码"""
        payload = {
            "username": "new_user",
            "email": "newuser3@example.com",
            "password": "123",
            "confirm_password": "123"
        }
        
        response = await client.post("/api/auth/register", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "password" in data["error"]
    
    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client, db_session):
        """测试必填字段缺失"""
        payload = {
            "username": "new_user",
            # email 缺失
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        response = await client.post("/api/auth/register", json=payload)
        
        assert response.status_code == 422  # Validation Error


class TestAuthLogin:
    """用户登录测试"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user):
        """测试成功登录"""
        payload = {
            "username": "test_user",
            "password": "test123456"
        }
        
        response = await client.post("/api/auth/login", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user):
        """测试密码错误"""
        payload = {
            "username": "test_user",
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/auth/login", json=payload)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "credentials" in data["error"]
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(self, client, db_session):
        """测试用户不存在"""
        payload = {
            "username": "nonexistent_user",
            "password": "test123456"
        }
        
        response = await client.post("/api/auth/login", json=payload)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "credentials" in data["error"]
    
    @pytest.mark.asyncio
    async def test_login_missing_fields(self, client, db_session):
        """测试登录字段缺失"""
        payload = {
            # username 缺失
            "password": "test123456"
        }
        
        response = await client.post("/api/auth/login", json=payload)
        
        assert response.status_code == 422


class TestAuthMiddleware:
    """认证中间件测试"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_request(self, client):
        """测试未授权请求"""
        # 不携带 token 访问需要认证的路由
        response = await client.get("/api/tasks")
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "auth" in data["error"]
    
    @pytest.mark.asyncio
    async def test_authorized_request(self, client, test_user):
        """测试授权请求"""
        # 获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 使用 token 访问需要认证的路由
        response = await client.get("/api/tasks", headers={
            "Authorization": f"Bearer {token}"
        })
        
        assert response.status_code == 200


class TestAuthTokenExpiration:
    """Token 过期测试"""
    
    @pytest.mark.asyncio
    async def test_expired_token(self, client, test_user):
        """测试过期 token"""
        # 创建过期 token
        from app.config import settings
        
        payload = {
            "user_id": test_user.id,
            "username": test_user.username,
            "role": test_user.role
        }
        
        expired_token = jwt.encode(
            payload,
            settings.secret_key,
            algorithm="HS256",
            expires=datetime.utcnow() - timedelta(hours=1)  # 1 小时前过期
        )
        
        response = await client.get("/api/tasks", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "auth" in data["error"]


class TestAuthPasswordReset:
    """密码重置测试"""
    
    @pytest.mark.asyncio
    async def test_request_password_reset(self, client, test_user):
        """测试请求密码重置"""
        payload = {
            "email": "test@example.com"
        }
        
        response = await client.post("/api/auth/password-reset", json=payload)
        
        # 实际生产中应该发送邮件，这里测试接口可用性
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "email" in data["message"] or "reset_link" in data["message"]
    
    @pytest.mark.asyncio
    async def test_password_reset_invalid_email(self, client, db_session):
        """测试无效的邮箱"""
        payload = {
            "email": "nonexistent@example.com"
        }
        
        response = await client.post("/api/auth/password-reset", json=payload)
        
        # 出于安全考虑，不提示邮箱是否存在
        assert response.status_code == 200
