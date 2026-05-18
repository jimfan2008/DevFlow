#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 集成测试
"""

import pytest
from httpx import AsyncClient


class TestFullWorkflow:
    """完整工作流程测试"""
    
    @pytest.mark.asyncio
    async def test_user_registration_login_workflow(self, client, db_session):
        """测试用户注册 - 登录完整流程"""
        # 1. 注册新用户
        register_payload = {
            "username": "workflow_user",
            "email": "workflow@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!"
        }
        
        response = await client.post("/api/auth/register", json=register_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 2. 登录新用户
        login_payload = {
            "username": "workflow_user",
            "password": "SecurePass123!"
        }
        
        response = await client.post("/api/auth/login", json=login_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_create_board_and_tasks_workflow(self, client, test_user, db_session):
        """测试创建看板和工作流程"""
        # 1. 登录
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 2. 创建看板列
        board_payload = {
            "project_id": "project_001",
            "name": "测试列",
            "color": "#10b981"
        }
        
        response = await client.post(
            "/api/boards",
            json=board_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        board_id = data["board"]["id"]
        
        # 3. 创建任务
        task_payload = {
            "board_id": board_id,
            "title": "工作流测试任务",
            "description": "测试任务创建"
        }
        
        response = await client.post(
            "/api/tasks",
            json=task_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        task_id = data["task"]["id"]
        
        # 4. 更新任务状态
        update_payload = {"status": "in_progress"}
        
        response = await client.put(
            f"/api/tasks/{task_id}",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_task_dependency_workflow(self, client, test_user, test_board, db_session):
        """测试任务依赖工作流"""
        # 1. 登录
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 2. 创建两个任务
        from app.models.task import Task
        
        task1 = Task(
            id="task_dep_1",
            title="前置任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task1)
        
        task2 = Task(
            id="task_dep_2",
            title="后置任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        
        db_session.commit()
        
        # 3. 创建依赖关系
        dep_payload = {
            "source_task_id": task1.id,
            "target_task_id": task2.id
        }
        
        response = await client.post(
            f"/api/tasks/{task1.id}/depend",
            json=dep_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # 4. 尝试循环依赖
        reverse_dep_payload = {
            "source_task_id": task2.id,
            "target_task_id": task1.id
        }
        
        response = await client.post(
            f"/api/tasks/{task2.id}/depend",
            json=reverse_dep_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        
        # 清理
        db_session.delete(task1)
        db_session.delete(task2)
        db_session.commit()


class TestCrossModuleIntegration:
    """跨模块集成测试"""
    
    @pytest.mark.asyncio
    async def test_task_update_triggers_inbox(self, client, test_user, test_board, db_session):
        """测试任务更新触发收件箱通知"""
        # 1. 创建另一个用户
        from app.models.user import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("test123456")
        
        another_user = User(
            id="user_inbox_integration",
            username="integration_user",
            email="integration@example.com",
            password_hash=hashed_password,
            role="member"
        )
        db_session.add(another_user)
        db_session.commit()
        
        # 2. 登录
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 3. 创建任务分配给另一个用户
        from app.models.task import Task
        
        task = Task(
            id="task_integration_inbox",
            title="集成测试任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            assignee_id=another_user.id,
            creator_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        
        # 4. 更新任务状态
        update_payload = {"status": "in_progress"}
        
        response = await client.put(
            f"/api/tasks/{task.id}",
            json=update_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # 5. 检查收件箱 (模拟另一个用户的登录)
        login_payload2 = {
            "username": "integration_user",
            "password": "test123456"
        }
        login_response2 = await client.post("/api/auth/login", json=login_payload2)
        token2 = login_response2.json()["access_token"]
        
        response = await client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        assert response.status_code == 200
        
        # 清理
        db_session.delete(another_user)
        db_session.delete(task)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_workload_update_on_task_assignment(self, client, test_user, test_board, db_session):
        """测试任务指派更新负载"""
        # 1. 登录
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 2. 创建未分配的任务
        from app.models.task import Task
        
        task = Task(
            id="task_workload_assign",
            title="负载测试任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        
        # 3. 初始负载检查
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        initial_data = response.json()
        assert initial_data["success"] is True
        
        # 4. 分配任务
        assign_payload = {"assignee_id": test_user.id}
        
        response = await client.put(
            f"/api/tasks/{task.id}",
            json=assign_payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # 5. 检查负载更新
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        updated_data = response.json()
        assert updated_data["success"] is True
        
        # 清理
        db_session.delete(task)
        db_session.commit()


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_invalid_token_handling(self, client):
        """测试无效 token 处理"""
        response = await client.get(
            "/api/tasks",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "auth" in data["error"]
    
    @pytest.mark.asyncio
    async def test_not_found_resource_handling(self, client, test_user, db_session):
        """测试资源不存在处理"""
        # 先登录
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 访问不存在的任务
        response = await client.get(
            "/api/tasks/nonexistent_id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, client, test_user, db_session):
        """测试验证错误处理"""
        # 先登录
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建无效任务
        payload = {
            # 缺少必填字段
        }
        
        response = await client.post(
            "/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_duplicate_resource_handling(self, client, test_user, test_board, db_session):
        """测试重复资源处理"""
        # 先登录
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建重复看板列
        payload = {
            "project_id": "project_001",
            "name": "测试看板",  # 与测试看板同名
            "color": "#3b82f6"
        }
        
        response = await client.post(
            "/api/boards",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
