#!/usr/bin/env python3
"""DevFlow 评论模块测试"""
import pytest


class TestCommentCreation:
    @pytest.mark.asyncio
    async def test_create_comment_success(self, client, test_user, test_task_ai, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {"content": "这是一条测试评论"}
        response = await client.post(
            f"/api/tasks/{test_task_ai.id}/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_create_comment_on_nonexistent_task(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {"content": "测试评论"}
        response = await client.post(
            "/api/tasks/nonexistent_task/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


class TestCommentList:
    @pytest.mark.asyncio
    async def test_list_comments_success(self, client, test_user, test_task_ai, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            f"/api/tasks/{test_task_ai.id}/comments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestCommentAPIAuth:
    @pytest.mark.asyncio
    async def test_create_comment_unauthorized(self, client, test_task_ai):
        payload = {"content": "未认证评论"}
        response = await client.post(f"/api/tasks/{test_task_ai.id}/comments", json=payload)
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_comments_unauthorized(self, client, test_task_ai):
        response = await client.get(f"/api/tasks/{test_task_ai.id}/comments")
        assert response.status_code in (401, 403)
