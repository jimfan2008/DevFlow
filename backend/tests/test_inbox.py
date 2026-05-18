#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 收件箱模块测试
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta


class TestInboxAggregation:
    """任务聚合测试"""
    
    @pytest.mark.asyncio
    async def test_get_inbox_success(self, client, test_user, test_task, db_session):
        """测试获取收件箱"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取收件箱
        response = await client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data
    
    @pytest.mark.asyncio
    async def test_inbox_assigned_tasks(self, client, test_user, test_task, db_session):
        """测试获取指派给我的任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取指派给我的任务
        response = await client.get(
            "/api/inbox?category=assigned",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data
        
        # 检查是否有相关任务
        assigned_items = [item for item in data["items"] if item["type"] == "assigned"]
        assert len(assigned_items) >= 1
    
    @pytest.mark.asyncio
    async def test_inbox_commented_tasks(self, client, test_user, test_task, db_session):
        """测试获取被评论的任务"""
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
        
        await client.post(
            f"/api/tasks/{test_task.id}/comments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 获取被评论的任务
        response = await client.get(
            "/api/inbox?category=commented",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data
        
        # 检查是否有相关评论
        commented_items = [item for item in data["items"] if item["type"] == "commented"]
        assert len(commented_items) >= 1
    
    @pytest.mark.asyncio
    async def test_inbox_watching_tasks(self, client, test_user, test_task, db_session):
        """测试获取我关注的任务"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 添加关注
        payload = {
            "task_id": test_task.id,
            "action": "watch"
        }
        
        await client.post(
            "/api/inbox/watch",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 获取关注的任务
        response = await client.get(
            "/api/inbox?category=watching",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data
        
        # 检查是否有关注的任务
        watching_items = [item for item in data["items"] if item["type"] == "watching"]
        assert len(watching_items) >= 1


class TestInboxNotification:
    """通知管理测试"""
    
    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, client, test_user, test_task, db_session):
        """测试标记为已读"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 获取收件箱 item
        response = await client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        data = response.json()
        if data["items"]:
            item_id = data["items"][0]["id"]
            
            # 标记为已读
            response = await client.put(
                f"/api/inbox/{item_id}/read",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["item"]["is_read"] is True
    
    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, client, test_user, test_task, db_session):
        """测试全部标记为已读"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.put(
            "/api/inbox/all/read",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "marked_count" in data
    
    @pytest.mark.asyncio
    async def test_get_unread_count(self, client, test_user, test_task, db_session):
        """测试获取未读数量"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        response = await client.get(
            "/api/inbox/unread/count",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "count" in data


class TestInboxFilterSearch:
    """通知过滤和搜索测试"""
    
    @pytest.mark.asyncio
    async def test_filter_by_type(self, client, test_user, test_task, db_session):
        """测试按类型过滤"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 过滤指派给我的任务
        response = await client.get(
            "/api/inbox?filter=assigned",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data
    
    @pytest.mark.asyncio
    async def test_search_by_keyword(self, client, test_user, test_task, db_session):
        """测试按关键词搜索"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 搜索包含特定关键词的任务
        response = await client.get(
            "/api/inbox/search?q=测试",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data


class TestInboxPreferences:
    """通知偏好设置测试"""
    
    @pytest.mark.asyncio
    async def test_set_notification_frequency(self, client, test_user, db_session):
        """测试设置通知频率"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 设置通知频率为汇总
        payload = {
            "frequency": "digest"
        }
        
        response = await client.put(
            "/api/inbox/preferences",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["preferences"]["frequency"] == "digest"
    
    @pytest.mark.asyncio
    async def test_set_notification_types(self, client, test_user, db_session):
        """测试设置通知类型"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 设置通知类型
        payload = {
            "notify_types": ["assigned", "commented"],
            "suppress_watch": True
        }
        
        response = await client.put(
            "/api/inbox/preferences",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notify_types" in data["preferences"]


class TestTaskReminders:
    """到期提醒测试"""
    
    @pytest.mark.asyncio
    async def test_reminder_3_days_before(self, client, test_user, test_board, db_session):
        """测试提前 3 天的第一次提醒"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建 3 天后到期的任务
        from app.models.task import Task
        from datetime import timedelta
        
        task = Task(
            id="task_reminder_3d",
            title="3 天后到期任务",
            description="提前 3 天提醒",
            board_id=test_board.id,
            status="todo",
            priority="high",
            assignee_id=test_user.id,
            creator_id=test_user.id,
            due_date=datetime.now() + timedelta(days=3)
        )
        db_session.add(task)
        db_session.commit()
        
        # 检查提醒
        response = await client.get(
            "/api/inbox/reminders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 清理
        db_session.delete(task)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_reminder_1_day_before(self, client, test_user, test_board, db_session):
        """测试提前 1 天的第二次提醒"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建 1 天后到期的任务
        from app.models.task import Task
        from datetime import timedelta
        
        task = Task(
            id="task_reminder_1d",
            title="1 天后到期任务",
            description="提前 1 天提醒",
            board_id=test_board.id,
            status="todo",
            priority="high",
            assignee_id=test_user.id,
            creator_id=test_user.id,
            due_date=datetime.now() + timedelta(days=1)
        )
        db_session.add(task)
        db_session.commit()
        
        # 检查提醒
        response = await client.get(
            "/api/inbox/reminders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 清理
        db_session.delete(task)
        db_session.commit()
    
    @pytest.mark.asyncio
    async def test_reminder_urgent_today(self, client, test_user, test_board, db_session):
        """测试当天的紧急提醒"""
        # 先登录获取 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 创建今天到期的任务
        from app.models.task import Task
        from datetime import datetime, timedelta
        
        task = Task(
            id="task_reminder_today",
            title="今天到期任务",
            description="紧急提醒",
            board_id=test_board.id,
            status="todo",
            priority="critical",
            assignee_id=test_user.id,
            creator_id=test_user.id,
            due_date=datetime.now()
        )
        db_session.add(task)
        db_session.commit()
        
        # 检查提醒
        response = await client.get(
            "/api/inbox/reminders",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 清理
        db_session.delete(task)
        db_session.commit()


class TestInboxIntegration:
    """收件箱集成测试"""
    
    @pytest.mark.asyncio
    async def test_task_update_creates_inbox_item(self, client, test_user, test_board, db_session):
        """测试任务更新创建收件箱条目"""
        # 创建测试用户
        from app.models.user import User
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("test123456")
        
        another_user = User(
            id="user_inbox_test",
            username="inbox_test_user",
            email="inbox@example.com",
            password_hash=hashed_password,
            role="member"
        )
        db_session.add(another_user)
        db_session.commit()
        
        # 创建任务
        from app.models.task import Task
        
        task = Task(
            id="task_inbox_integration",
            title="集成测试任务",
            board_id=test_board.id,
            status="todo",
            priority="medium",
            assignee_id=another_user.id,
            creator_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        
        # 先登录获取 test_user 的 token
        login_payload = {
            "username": "test_user",
            "password": "test123456"
        }
        login_response = await client.post("/api/auth/login", json=login_payload)
        token = login_response.json()["access_token"]
        
        # 更新任务状态
        payload = {
            "status": "in_progress"
        }
        
        await client.put(
            f"/api/tasks/{task.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 获取 another_user 的收件箱
        # 模拟登录 for another_user
        login_payload2 = {
            "username": "inbox_test_user",
            "password": "test123456"
        }
        login_response2 = await client.post("/api/auth/login", json=login_payload2)
        token2 = login_response2.json()["access_token"]
        
        response = await client.get(
            "/api/inbox",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 清理
        db_session.delete(another_user)
        db_session.delete(task)
        db_session.commit()
