#!/usr/bin/env python3
"""DevFlow 集成测试"""
import pytest


class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_user_registration_login_workflow(self, client, db_session):
        register_payload = {
            "username": "workflow_user",
            "email": "workflow@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        response = await client.post("/api/auth/register", json=register_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        login_payload = {"username": "workflow_user", "password": "SecurePass123!"}
        response = await client.post("/api/auth/login", json=login_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "tokens" in data["data"]


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_token_handling(self, client):
        response = await client.get(
            "/api/tasks",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_not_found_resource_handling(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            "/api/tasks/nonexistent_id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {}
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422
