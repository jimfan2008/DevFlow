#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 任务管理模块测试
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestTaskCreation:
    @pytest.mark.asyncio
    async def test_create_task_success(self, client, test_user, test_project, opencode_agent, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {
            "project_id": test_project.id,
            "name": "新任务",
            "description": "这是一个新任务的描述",
            "type": "coding",
            "priority": "high",
            "acceptance_criteria": "功能正常运行",
        }
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "name" in data["data"]
        assert data["data"]["name"] == "新任务"

    @pytest.mark.asyncio
    async def test_create_task_missing_name(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {
            "project_id": "some_project",
            "description": "这是一个没有名称的任务"
        }
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422


class TestTaskUpdate:
    @pytest.mark.asyncio
    async def test_update_task_not_found(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        payload = {"name": "新名称"}
        response = await client.put(
            "/api/tasks/nonexistent_id",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


class TestTaskDelete:
    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, client, test_user, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.delete(
            "/api/tasks/nonexistent_id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404


class TestTaskList:
    @pytest.mark.asyncio
    async def test_list_tasks_success(self, client, test_user, test_task_ai, test_project, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, client, test_user, test_task_ai, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            "/api/tasks?status=pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestTaskDetail:
    @pytest.mark.asyncio
    async def test_get_task_detail_success(self, client, test_user, test_task_ai, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            f"/api/tasks/{test_task_ai.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["id"] == test_task_ai.id
