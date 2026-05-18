#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 任务管理模块测试
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestTaskCreation:
    """任务创建测试"""
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, client, test_user, test_board, db_session):
        """测试成功创建任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建任务
        payload = {
            "board_id": test_board.id,
            "title": "新任务",
            "description": "这是一个新任务的描述",
            "priority": "high",
            "assignee_id": test_user.id,
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data["task"]
        assert data["task"]["title"] == "新任务"
        assert data["task"]["description"] == "这是一个新任务的描述"
        assert data["task"]["status"] == "todo"
        assert data["task"]["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_create_task_missing_title(self, client, test_user, test_board, db_session):
        """测试创建任务缺少标题"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建无标题任务
        payload = {
            "board_id": test_board.id,
            "description": "这是一个没有标题的任务"
        }
        
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation Error
    
    @pytest.mark.asyncio
    async def test_create_task_missing_board(self, client, test_user, db_session):
        """测试创建任务缺少看板"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建无看板任务
        payload = {
            "title": "无看板任务"
        }
        
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_task_with_comment(self, client, test_user, test_board, db_session):
        """测试创建任务时附带评论"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建任务附带评论
        payload = {
            "board_id": test_board.id,
            "title": "带评论的任务",
            "comments": [
                {"content": "第一条评论"},
                {"content": "第二条评论"}
            ]
        }
        
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "task" in data
        assert "comments" in data


class TestTaskUpdate:
    """任务更新测试"""
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, client, test_user, test_task, db_session):
        """测试成功更新任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 更新任务
        payload = {
            "title": "更新后的任务标题",
            "description": "更新后的任务描述",
            "priority": "critical"
        }
        
        response = await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task"]["title"] == "更新后的任务标题"
        assert data["task"]["priority"] == "critical"
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, client, test_user, test_task, db_session):
        """测试更新任务状态"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 更新状态
        payload = {
            "status": "in_progress"
        }
        
        response = await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_update_task_not_found(self, client, test_user, db_session):
        """测试更新不存在的任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 更新不存在的任务
        payload = {
            "title": "新标题"
        }
        
        response = await client.put(
            "/api/tasks/nonexistent_id",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_task_add_assignee(self, client, test_user, test_board, db_session):
        """测试为任务分配负责人"""
        # 创建另一个用户
        from app.models.user import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("test123456")
        
        another_user = User(
            id="user_002",
            username="another_user",
            email="another@example.com",
            password_hash=hashed_password,
            role="member"
        )
        
        db_session.add(another_user)
        db_session.commit()
        
        # 创建未分配的任务
        task = Task(
            id="task_002",
            title="未分配任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 分配任务
        payload = {
            "assignee_id": another_user.id
        }
        
        response = await client.put(
            f"/api/tasks/{task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["assignee_id"] == another_user.id
        
        # 清理
        db_session.delete(another_user)
        db_session.delete(task)
        db_session.commit()


class TestTaskDelete:
    """任务删除测试"""
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, client, test_user, test_task, db_session):
        """测试成功删除任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.delete(
            f"/api/tasks/{test_task.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, client, test_user, db_session):
        """测试删除不存在的任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.delete(
            "/api/tasks/nonexistent_id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404


class TestTaskList:
    """任务列表查询测试"""
    
    @pytest.mark.asyncio
    async def test_list_tasks_success(self, client, test_user, test_task, test_board, db_session):
        """测试获取任务列表"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            f"/api/boards/{test_board.id}/tasks",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tasks" in data
        assert any(t["id"] == test_task.id for t in data["tasks"])
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, client, test_user, test_task, test_board, db_session):
        """测试按状态筛选任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取 todo 状态的任务
        response = await client.get(
            f"/api/boards/{test_board.id}/tasks?status=todo",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for task in data["tasks"]:
            assert task["status"] == "todo"
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_priority(self, client, test_user, test_task, test_board, db_session):
        """测试按优先级筛选任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取高优先级任务
        response = await client.get(
            f"/api/boards/{test_board.id}/tasks?priority=high",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for task in data["tasks"]:
            assert task["priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_list_tasks_assigned_to_me(self, client, test_user, test_task, test_board, db_session):
        """测试获取分配给我的任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取分配给我的任务
        response = await client.get(
            f"/api/boards/{test_board.id}/tasks?assignee_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for task in data["tasks"]:
            assert task["assignee_id"] == test_user.id


class TestTaskDetail:
    """任务详情查询测试"""
    
    @pytest.mark.asyncio
    async def test_get_task_detail_success(self, client, test_user, test_task, db_session):
        """测试获取任务详情"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            f"/api/tasks/{test_task.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task"]["id"] == test_task.id
        assert data["task"]["title"] == "测试任务"
        assert "comments" in data
        assert "dependencies" in data


class TestTaskStatusTransition:
    """任务状态流转测试"""
    
    @pytest.mark.asyncio
    async def test_transition_todo_to_in_progress(self, client, test_user, test_task, db_session):
        """测试状态流转：Todo -> In Progress"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 更新状态
        payload = {
            "status": "in_progress"
        }
        
        response = await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_transition_in_progress_to_review(self, client, test_user, test_task, db_session):
        """测试状态流转：In Progress -> Review"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 先转为 in_progress
        payload = {"status": "in_progress"}
        await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 再转为 review
        payload = {"status": "review"}
        
        response = await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "review"
    
    @pytest.mark.asyncio
    async def test_transition_review_to_done(self, client, test_user, test_task, db_session):
        """测试状态流转：Review -> Done"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 转为 done
        payload = {
            "status": "done"
        }
        
        response = await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["status"] == "done"
    
    @pytest.mark.asyncio
    async def test_invalid_status_transition(self, client, test_user, test_task, db_session):
        """测试无效状态流转"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 尝试非法状态
        payload = {
            "status": "invalid_status"
        }
        
        response = await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation Error


class TestTaskComments:
    """任务评论测试"""
    
    @pytest.mark.asyncio
    async def test_add_comment_success(self, client, test_user, test_task, db_session):
        """测试添加评论"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 添加评论
        payload = {
            "content": "这是一条测试评论"
        }
        
        response = await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "comment" in data
        assert data["comment"]["content"] == "这是一条测试评论"
    
    @pytest.mark.asyncio
    async def test_list_comments_success(self, client, test_user, test_task, db_session):
        """测试获取评论列表"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 添加几条评论
        for i in range(3):
            await client.post(
                f"/api/tasks/{test_task.id}/comments",
                json={"content": f"第{i+1}条评论"},
                headers={"Authorization": f"Bearer {token}"}
            )
        
        # 获取评论列表
        response = await client.get(
            f"/api/tasks/{test_task.id}/comments",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "comments" in data
        assert len(data["comments"]) == 3


class TestTaskAttachments:
    """任务附件测试"""
    
    @pytest.mark.asyncio
    async def test_add_attachment_success(self, client, test_user, test_task, db_session):
        """测试添加附件"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 添加附件
        payload = {
            "name": "测试文件.txt",
            "size": 1024,
            "type": "text/plain"
        }
        
        response = await client.post(
            f"/api/tasks/{test_task.id}/attachments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "attachment" in data
        assert data["attachment"]["name"] == "测试文件.txt"
