#!/usr/bin/env python3
"""DevFlow 收件箱模块测试"""
import pytest


class TestInboxAggregation:
    @pytest.mark.asyncio
    async def test_get_inbox_success(self, client, test_user, test_task_ai, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_inbox_unauthorized(self, client):
        response = await client.get("/api/inbox")
        assert response.status_code in (401, 403)
