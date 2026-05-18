#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 负载分析模块测试
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestWorkloadHeatmap:
    """负载热力图测试"""
    
    @pytest.mark.asyncio
    async def test_get_workload_heatmap_success(self, client, test_user, test_board, db_session):
        """测试获取负载热力图"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            f"/api/boards/{test_board.id}/workload",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "members" in data
        assert "team" in data
    
    @pytest.mark.asyncio
    async def test_workload_idle_status(self, client, test_user, test_board, db_session):
        """测试空闲状态 (任务数 <= 2)"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取负载数据
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 找到该成员的负载数据
        member_data = next((m for m in data["members"] if m["user_id"] == test_user.id), None)
        assert member_data is not None
        assert member_data["task_count"] <= 2
        assert member_data["status"] == "idle"
        assert member_data["color"] == "green"
    
    @pytest.mark.asyncio
    async def test_workload_normal_status(self, client, test_user, test_board, db_session):
        """测试正常状态 (任务数 3-5)"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建 4 个任务分配给测试用户
        for i in range(4):
            from app.models.task import Task
            task = Task(
                id=f"task_normal_{i}",
                title=f"任务{i+1}",
                board_id=test_board.id,
                status="todo",
                priority="medium",
                assignee_id=test_user.id,
                creator_id=test_user.id
            )
            db_session.add(task)
        db_session.commit()
        
        # 获取负载数据
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 找到该成员的负载数据
        member_data = next((m for m in data["members"] if m["user_id"] == test_user.id), None)
        assert member_data is not None
        assert 3 <= member_data["task_count"] <= 5
        assert member_data["status"] == "normal"
        assert member_data["color"] == "yellow"
        
        # 清理
        for i in range(4):
            task = db_session.query(Task).filter_by(id=f"task_normal_{i}").first()
            if task:
                db_session.delete(task)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_workload_busy_status(self, client, test_user, test_board, db_session):
        """测试忙碌状态 (任务数 > 5)"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建 6 个任务分配给测试用户
        for i in range(6):
            from app.models.task import Task
            task = Task(
                id=f"task_busy_{i}",
                title=f"任务{i+1}",
                board_id=test_board.id,
                status="todo",
                priority="medium",
                assignee_id=test_user.id,
                creator_id=test_user.id
            )
            db_session.add(task)
        db_session.commit()
        
        # 获取负载数据
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 找到该成员的负载数据
        member_data = next((m for m in data["members"] if m["user_id"] == test_user.id), None)
        assert member_data is not None
        assert member_data["task_count"] > 5
        assert member_data["status"] == "busy"
        assert member_data["color"] == "red"
        
        # 清理
        for i in range(6):
            task = db_session.query(Task).filter_by(id=f"task_busy_{i}").first()
            if task:
                db_session.delete(task)
        db_session.commit()


class TestTaskAssignment:
    """任务指派测试"""
    
    @pytest.mark.asyncio
    async def test_manual_assignment_success(self, client, test_user, test_board, db_session):
        """测试手动指派任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建测试用户
        from app.models.user import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("test123456")
        
        another_user = User(
            id="user_another",
            username="another_member",
            email="another@example.com",
            password_hash=hashed_password,
            role="member"
        )
        db_session.add(another_user)
        db_session.commit()
        
        # 创建未分配的任务
        from app.models.task import Task
        unassigned_task = Task(
            id="task_unassigned",
            title="未分配任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(unassigned_task)
        db_session.commit()
        
        # 手动指派
        payload = {
            "assignee_id": another_user.id
        }
        
        response = await client.put(
            f"/api/tasks/{unassigned_task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task"]["assignee_id"] == another_user.id
        
        # 清理
        db_session.delete(another_user)
        db_session.delete(unassigned_task)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_automatic_assignment_lowest_load(self, client, test_user, test_board, db_session):
        """测试自动指派给负载最低成员"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建测试用户
        from app.models.user import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("test123456")
        
        user_light = User(
            id="user_light",
            username="light_user",
            email="light@example.com",
            password_hash=hashed_password,
            role="member"
        )
        user_heavy = User(
            id="user_heavy",
            username="heavy_user",
            email="heavy@example.com",
            password_hash=hashed_password,
            role="member"
        )
        
        db_session.add(user_light)
        db_session.add(user_heavy)
        db_session.commit()
        
        # 给 heavy_user 分配 5 个任务
        for i in range(5):
            from app.models.task import Task
            task = Task(
                id=f"task_heavy_{i}",
                title=f"Heavy 任务{i+1}",
                board_id=test_board.id,
                status="todo",
                priority="medium",
                assignee_id=user_heavy.id,
                creator_id=test_user.id
            )
            db_session.add(task)
        db_session.commit()
        
        # 创建未分配的任务
        from app.models.task import Task
        new_task = Task(
            id="task_new_auto",
            title="新任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id
        )
        db_session.add(new_task)
        db_session.commit()
        
        # 自动指派
        payload = {
            "auto_assign": True
        }
        
        response = await client.put(
            f"/api/tasks/{new_task.id}/assign",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["task"]["assignee_id"] == user_light.id  # 应该指派给负载最低的成员
        
        # 清理
        db_session.delete(user_light)
        db_session.delete(user_heavy)
        for i in range(5):
            task = db_session.query(Task).filter_by(id=f"task_heavy_{i}").first()
            if task:
                db_session.delete(task)
        db_session.delete(new_task)
        db_session.commit()


class TestWorkloadAlert:
    """负载预警测试"""
    
    @pytest.mark.asyncio
    async def test_yellow_alert(self, client, test_user, test_board, db_session):
        """测试黄色预警 (任务数 > 5)"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建 6 个任务
        for i in range(6):
            from app.models.task import Task
            task = Task(
                id=f"task_yellow_{i}",
                title=f"预警任务{i+1}",
                board_id=test_board.id,
                status="todo",
                priority="medium",
                assignee_id=test_user.id,
                creator_id=test_user.id
            )
            db_session.add(task)
        db_session.commit()
        
        # 获取负载数据
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        member_data = next((m for m in data["members"] if m["user_id"] == test_user.id), None)
        assert member_data is not None
        assert member_data["has_alert"] is True
        assert member_data["alert_level"] == "yellow"
        
        # 清理
        for i in range(6):
            task = db_session.query(Task).filter_by(id=f"task_yellow_{i}").first()
            if task:
                db_session.delete(task)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_red_alert(self, client, test_user, test_board, db_session):
        """测试红色预警 (任务数 > 10)"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建 11 个任务
        for i in range(11):
            from app.models.task import Task
            task = Task(
                id=f"task_red_{i}",
                title=f"红色预警任务{i+1}",
                board_id=test_board.id,
                status="todo",
                priority="medium",
                assignee_id=test_user.id,
                creator_id=test_user.id
            )
            db_session.add(task)
        db_session.commit()
        
        # 获取负载数据
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        member_data = next((m for m in data["members"] if m["user_id"] == test_user.id), None)
        assert member_data is not None
        assert member_data["has_alert"] is True
        assert member_data["alert_level"] == "red"
        
        # 清理
        for i in range(11):
            task = db_session.query(Task).filter_by(id=f"task_red_{i}").first()
            if task:
                db_session.delete(task)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_no_alert(self, client, test_user, test_board, db_session):
        """测试无预警"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取负载数据 (测试用户只有测试任务)
        response = await client.get(
            f"/api/boards/{test_board.id}/workload?user_id={test_user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        member_data = next((m for m in data["members"] if m["user_id"] == test_user.id), None)
        assert member_data is not None
        assert member_data["has_alert"] is False


class TestWorkloadTrend:
    """负载趋势分析测试"""
    
    @pytest.mark.asyncio
    async def test_get_workload_trend(self, client, test_user, test_board, db_session):
        """测试获取负载趋势"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建不同时间的任务
        from app.models.task import Task
        
        # 7 天前的任务
        for i in range(3):
            task = Task(
                id=f"task_trend_old_{i}",
                title=f"旧任务{i+1}",
                board_id=test_board.id,
                status="done",
                priority="medium",
                assignee_id=test_user.id,
                creator_id=test_user.id
            )
            db_session.add(task)
        db_session.commit()
        
        # 获取趋势数据
        response = await client.get(
            f"/api/boards/{test_board.id}/workload/trend?days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "trend" in data
        assert "history" in data


class TestTeamStats:
    """团队统计测试"""
    
    @pytest.mark.asyncio
    async def test_get_team_stats(self, client, test_user, test_board, db_session):
        """测试获取团队统计"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            f"/api/boards/{test_board.id}/workload/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_members" in data
        assert "total_tasks" in data
        assert "average_workload" in data
