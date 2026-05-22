#!/usr/bin/env python3
"""DevFlow 看板管理模块测试"""
import pytest


class TestBoardCreation:
    @pytest.mark.asyncio
    async def test_create_board_success(self, client, test_user, test_project, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {
            "project_id": test_project.id,
            "name": "新看板",
            "slug": "new-board",
            "color": "#10b981",
            "position": 1
        }
        response = await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_create_board_missing_name(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {"project_id": "project_001", "color": "#10b981"}
        response = await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422


class TestBoardUpdate:
    @pytest.mark.asyncio
    async def test_update_board_not_found(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {"name": "新名称"}
        response = await client.put(
            "/api/boards/nonexistent_id",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


class TestBoardDelete:
    @pytest.mark.asyncio
    async def test_delete_board_not_found(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.delete(
            "/api/boards/nonexistent_id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
