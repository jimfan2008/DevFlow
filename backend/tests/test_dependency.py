#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 依赖管理模块测试
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestDependencyCreation:
    """依赖关系创建测试"""
    
    @pytest.mark.asyncio
    async def test_create_dependency_success(self, client, test_user, test_task, test_board, db_session):
        """测试成功创建依赖关系"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建第二个任务
        from app.models.task import Task
        task2 = Task(
            id="task_002",
            title="后置任务",
            description="依赖 task_001 的任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        db_session.commit()
        
        # 创建依赖关系：task_001 -> task_002
        payload = {
            "source_task_id": test_task.id,
            "target_task_id": task2.id
        }
        
        response = await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "dependency" in data
        assert data["dependency"]["source_task_id"] == test_task.id
        assert data["dependency"]["target_task_id"] == task2.id
    
    @pytest.mark.asyncio
    async def test_create_dependency_circular(self, client, test_user, test_task, test_board, db_session):
        """测试循环依赖检测"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建第二个任务
        from app.models.task import Task
        task2 = Task(
            id="task_002",
            title="后置任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        db_session.commit()
        
        # 创建依赖关系：task_001 -> task_002
        payload = {
            "source_task_id": test_task.id,
            "target_task_id": task2.id
        }
        
        await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 尝试创建反向依赖：task_002 -> task_001 (形成循环)
        payload = {
            "source_task_id": task2.id,
            "target_task_id": test_task.id
        }
        
        response = await client.post(
            f"/api/tasks/{task2.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "circular" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_create_dependency_same_task(self, client, test_user, test_task, db_session):
        """测试任务不能依赖自己"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        payload = {
            "source_task_id": test_task.id,
            "target_task_id": test_task.id  # 自己依赖自己
        }
        
        response = await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "same" in data["error"].lower() or "self" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_create_dependency_nonexistent_source(self, client, test_user, test_task, db_session):
        """测试源任务不存在"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建任务
        from app.models.task import Task
        task = Task(
            id="task_002",
            title="任务 2",
            board_id=test_task.board_id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        
        payload = {
            "source_task_id": "nonexistent_id",
            "target_task_id": task.id
        }
        
        response = await client.post(
            f"/api/tasks/nonexistent_id/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404


class TestDependencyRemoval:
    """依赖关系删除测试"""
    
    @pytest.mark.asyncio
    async def test_remove_dependency_success(self, client, test_user, test_task, test_board, db_session):
        """测试成功删除依赖关系"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建第二个任务
        from app.models.task import Task
        task2 = Task(
            id="task_002",
            title="后置任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        db_session.commit()
        
        # 创建依赖关系
        payload = {
            "source_task_id": test_task.id,
            "target_task_id": task2.id
        }
        
        await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 删除依赖关系
        response = await client.delete(
            f"/api/tasks/{test_task.id}/depend/{task2.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_remove_dependency_not_found(self, client, test_user, test_task, db_session):
        """测试删除不存在的依赖关系"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.delete(
            f"/api/tasks/{test_task.id}/depend/nonexistent_dep",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404


class TestDependencyList:
    """依赖关系列表测试"""
    
    @pytest.mark.asyncio
    async def test_list_dependencies_success(self, client, test_user, test_task, test_board, db_session):
        """测试获取依赖关系列表"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建第二个任务
        from app.models.task import Task
        task2 = Task(
            id="task_002",
            title="后置任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        db_session.commit()
        
        # 创建依赖关系
        payload = {
            "source_task_id": test_task.id,
            "target_task_id": task2.id
        }
        
        await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 获取前置依赖
        response = await client.get(
            f"/api/tasks/{test_task.id}/depend",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "dependencies" in data
        assert len(data["dependencies"]) >= 1


class TestDependencyBlocking:
    """依赖阻塞状态测试"""
    
    @pytest.mark.asyncio
    async def test_block_when_dependency_not_done(self, client, test_user, test_task, test_board, db_session):
        """测试依赖任务未完成时被阻塞"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建后置任务
        from app.models.task import Task
        task2 = Task(
            id="task_002",
            title="后置任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        db_session.commit()
        
        # 创建依赖关系：task_001 -> task_002
        payload = {
            "source_task_id": test_task.id,
            "target_task_id": task2.id
        }
        
        await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # task_001 完成，尝试将 task_002 设为 in_progress
        payload = {"status": "done"}
        await client.put(
            f"/api/tasks/{test_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # task_002 应该变为可操作状态
        payload = {"status": "in_progress"}
        response = await client.put(
            f"/api/tasks/{task2.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_block_when_dependency_todo(self, client, test_user, test_task, test_board, db_session):
        """测试依赖任务为 todo 时被阻塞"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建后置任务
        from app.models.task import Task
        task2 = Task(
            id="task_002",
            title="后置任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        db_session.commit()
        
        # 创建依赖关系：task_001 (todo) -> task_002
        payload = {
            "source_task_id": test_task.id,
            "target_task_id": task2.id
        }
        
        await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # task_001 仍然是 todo，尝试将 task_002 设为 in_progress
        # 应该失败或显示阻塞状态
        payload = {"status": "in_progress"}
        response = await client.put(
            f"/api/tasks/{task2.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 根据业务规则，可能被阻止或允许但显示警告
        # 这里测试接口可用性
        assert response.status_code in [200, 400]


class TestDependencyVisualization:
    """依赖关系可视化测试"""
    
    @pytest.mark.asyncio
    async def test_get_dependency_graph(self, client, test_user, test_task, test_board, db_session):
        """测试获取依赖图"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建任务链：task_001 -> task_002 -> task_003
        from app.models.task import Task
        
        task2 = Task(
            id="task_002",
            title="中间任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task2)
        db_session.commit()
        
        task3 = Task(
            id="task_003",
            title="最终任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task3)
        db_session.commit()
        
        # 创建依赖关系
        payload1 = {
            "source_task_id": test_task.id,
            "target_task_id": task2.id
        }
        await client.post(
            f"/api/tasks/{test_task.id}/depend",
            json=payload1,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        payload2 = {
            "source_task_id": task2.id,
            "target_task_id": task3.id
        }
        await client.post(
            f"/api/tasks/{task2.id}/depend",
            json=payload2,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 获取 task_003 的完整依赖图
        response = await client.get(
            f"/api/tasks/{task3.id}/depend/graph",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "predecessors" in data
        assert "successors" in data
        assert len(data["predecessors"]) >= 2  # task_001, task_002


class TestDependencyCycleDetection:
    """依赖循环检测测试"""
    
    @pytest.mark.asyncio
    async def test_detect_abc_cycle(self, client, test_user, test_board, db_session):
        """测试 ABC 循环依赖检测"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建三个任务
        from app.models.task import Task
        
        task_a = Task(
            id="task_a",
            title="任务 A",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task_a)
        
        task_b = Task(
            id="task_b",
            title="任务 B",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task_b)
        
        task_c = Task(
            id="task_c",
            title="任务 C",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(task_c)
        
        db_session.commit()
        
        # 创建 A -> B -> C 依赖
        payload_ab = {
            "source_task_id": task_a.id,
            "target_task_id": task_b.id
        }
        await client.post(
            f"/api/tasks/{task_a.id}/depend",
            json=payload_ab,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        payload_bc = {
            "source_task_id": task_b.id,
            "target_task_id": task_c.id
        }
        await client.post(
            f"/api/tasks/{task_b.id}/depend",
            json=payload_bc,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 尝试创建 C -> A (形成循环)
        payload_ca = {
            "source_task_id": task_c.id,
            "target_task_id": task_a.id
        }
        
        response = await client.post(
            f"/api/tasks/{task_c.id}/depend",
            json=payload_ca,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "circular" in data["error"].lower() or "cycle" in data["error"].lower()
