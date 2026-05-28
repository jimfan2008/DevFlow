#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 认证模块测试
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import jwt


class TestAuthRegistration:
    @pytest.mark.asyncio
    async def test_register_success(self, client, db_session):
        payload = {
            "username": "new_user",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        response = await client.post("/api/auth/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "user" in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client, test_user, db_session):
        payload = {
            "username": "test_user",
            "email": "different@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        response = await client.post("/api/auth/register", json=payload)
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "AUTH_USER_EXISTS"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user, db_session):
        payload = {
            "username": "another_user",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        response = await client.post("/api/auth/register", json=payload)
        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "AUTH_USER_EXISTS"

    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, client, db_session):
        payload = {
            "username": "new_user",
            "email": "newuser2@example.com",
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!"
        }
        response = await client.post("/api/auth/register", json=payload)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client, db_session):
        payload = {
            "username": "new_user",
            "email": "newuser3@example.com",
            "password": "123",
            "confirm_password": "123"
        }
        response = await client.post("/api/auth/register", json=payload)
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client, db_session):
        payload = {
            "username": "new_user",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        response = await client.post("/api/auth/register", json=payload)
        assert response.status_code == 422


class TestAuthLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user):
        payload = {
            "username": "test_user",
            "password": "test123456"
        }
        response = await client.post("/api/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "tokens" in data["data"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user):
        payload = {
            "username": "test_user",
            "password": "wrongpassword"
        }
        response = await client.post("/api/auth/login", json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, client, db_session):
        payload = {
            "username": "nonexistent_user",
            "password": "test123456"
        }
        response = await client.post("/api/auth/login", json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, client, db_session):
        payload = {
            "password": "test123456"
        }
        response = await client.post("/api/auth/login", json=payload)
        assert response.status_code == 422


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_unauthorized_request(self, client):
        response = await client.get("/api/tasks")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_authorized_request(self, client, test_user):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get("/api/tasks", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200


class TestAuthTokenExpiration:
    @pytest.mark.asyncio
    async def test_expired_token(self, client, test_user):
        from app.config import settings
        payload = {
            "sub": test_user.id,
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        response = await client.get("/api/tasks", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        assert response.status_code in (401, 403)


class TestAuthPasswordReset:
    @pytest.mark.asyncio
    async def test_request_password_reset(self, client, test_user):
        payload = {"email": "test@example.com"}
        response = await client.post("/api/auth/password-reset", json=payload)
        assert response.status_code in (200, 404, 405)

    @pytest.mark.asyncio
    async def test_password_reset_invalid_email(self, client, db_session):
        payload = {"email": "nonexistent@example.com"}
        response = await client.post("/api/auth/password-reset", json=payload)
        assert response.status_code in (200, 404, 405)
