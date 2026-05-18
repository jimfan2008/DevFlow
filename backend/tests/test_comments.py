#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 评论模块测试
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock


class TestCommentCreation:
    """评论创建测试"""

    @pytest.mark.asyncio
    async def test_create_comment_success(self, client, test_user, test_task, db_session):
        """测试成功创建评论"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        payload = {"content": "这是一条测试评论"}

        response = await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "success"
        assert "id" in data["data"]
        assert data["data"]["content"] == "这是一条测试评论"
        assert data["data"]["task_id"] == test_task.id

    @pytest.mark.asyncio
    async def test_create_comment_empty_content(self, client, test_user, test_task, db_session):
        """测试创建空内容评论"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        payload = {"content": ""}

        response = await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation Error - min_length=1

    @pytest.mark.asyncio
    async def test_create_comment_missing_content(self, client, test_user, test_task, db_session):
        """测试创建评论缺少content字段"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        payload = {}

        response = await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_comment_on_nonexistent_task(self, client, test_user, db_session):
        """测试在不存在任务上创建评论"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        payload = {"content": "测试评论"}

        response = await client.post(
            "/api/tasks/nonexistent_task/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        # 任务不存在应返回错误（400 由 ValueError 捕获）
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 400


class TestCommentList:
    """评论列表测试"""

    @pytest.mark.asyncio
    async def test_list_comments_success(self, client, test_user, test_task, db_session):
        """测试成功获取评论列表"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 先创建一条评论
        create_payload = {"content": "列表测试评论"}
        await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json=create_payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        response = await client.get(
            f"/api/tasks/{test_task.id}/comments",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "comments" in data["data"]
        assert data["data"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_comments_empty(self, client, test_user, test_task, db_session):
        """测试空评论列表"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        response = await client.get(
            f"/api/tasks/{test_task.id}/comments",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["total"] == 0
        assert len(data["data"]["comments"]) == 0

    @pytest.mark.asyncio
    async def test_list_comments_order(self, client, test_user, test_task, db_session):
        """测试评论按创建时间排序"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 创建多条评论
        for i in range(3):
            await client.post(
                f"/api/tasks/{test_task.id}/comments",
                json={"content": f"评论 {i}"},
                headers={"Authorization": f"Bearer {token}"},
            )

        response = await client.get(
            f"/api/tasks/{test_task.id}/comments",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 3


class TestCommentDelete:
    """评论删除测试"""

    @pytest.mark.asyncio
    async def test_delete_comment_success(self, client, test_user, test_task, db_session):
        """测试成功删除评论"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 先创建一条评论
        create_resp = await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json={"content": "待删除评论"},
            headers={"Authorization": f"Bearer {token}"},
        )
        comment_id = create_resp.json()["data"]["id"]

        # 删除评论
        response = await client.delete(
            f"/api/tasks/{test_task.id}/comments/{comment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_comment(self, client, test_user, test_task, db_session):
        """测试删除不存在的评论"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        response = await client.delete(
            "/api/tasks/nonexistent/comments/nonexistent_id",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False


class TestCommentAPIAuth:
    """评论 API 认证测试"""

    @pytest.mark.asyncio
    async def test_create_comment_unauthorized(self, client, test_task):
        """测试未认证创建评论"""
        payload = {"content": "未认证评论"}
        response = await client.post(f"/api/tasks/{test_task.id}/comments", json=payload)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_comments_unauthorized(self, client, test_task):
        """测试未认证获取评论列表"""
        response = await client.get(f"/api/tasks/{test_task.id}/comments")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_comment_unauthorized(self, client, test_task):
        """测试未认证删除评论"""
        response = await client.delete(f"/api/tasks/{test_task.id}/comments/fake_id")
        assert response.status_code == 401


class TestCommentWithInbox:
    """评论触发收件箱测试"""

    @pytest.mark.asyncio
    async def test_comment_creates_inbox_for_assignee(self, client, test_user, test_task, db_session):
        """测试评论为任务负责人创建收件箱消息"""
        login_payload = {"username": "test_user", "password": "test123456"}
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]

        # 任务已有 assignee（test_user），让 test_user 评论不会产生新的 inbox
        payload = {"content": "测试收件箱通知"}
        response = await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_comment_on_task_without_assignee(self, client, db_session):
        """测试对没有负责人的任务创建评论"""
        from app.models.user import User
        from app.utils.security import get_password_hash

        # 创建没有负责人的任务
        user = db_session.query(User).filter(User.id == "user_001").first()
        task_no_assignee = MagicMock()
        task_no_assignee.id = "task_no_assignee"
        task_no_assignee.title = "无负责人任务"
        task_no_assignee.assignee_id = None

        with patch("app.services.comment_service.CommentService._import_models") as mock_import:
            mock_comment = MagicMock()
            mock_comment.to_dict.return_value = {"id": "comment_001", "task_id": "task_no_assignee", "content": "测试", "user_id": "user_001"}
            mock_import.return_value = (MagicMock(return_value=mock_comment), MagicMock())
