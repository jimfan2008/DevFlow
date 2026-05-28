#!/usr/bin/env python3
"""DevFlow 群聊模块测试"""
import pytest


class TestGroupChat:
    @pytest.mark.asyncio
    async def test_list_groups_unauthorized(self, client):
        response = await client.get("/api/groups")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_groups(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            "/api/groups",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (200, 404)
