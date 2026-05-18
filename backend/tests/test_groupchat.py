#!/usr/bin/env python3
"""
GroupChat 功能测试
测试内容：
1. GroupService 服务层 - CRUD 操作
2. Group 数据模型 - 序列化和关系
3. WebSocket 连接管理
4. API 路由注册
"""

import pytest
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.group import Group, GroupMessage, MeetingOutcome, GroupTask
from app.services.group_service import GroupService


FIXTURES_PATH = Path(__file__).parent / "data" / "fixtures" / "groups.json"


@pytest.fixture(scope="function")
def test_db():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="module")
def test_data():
    """加载测试数据"""
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestGroupModel:
    """Group 数据模型测试"""

    def test_group_model_creation(self, test_db: Session):
        """测试 Group 模型创建"""
        group = Group(
            id="test-group-001",
            name="Test Group",
            description="Test Description",
            members=["agent1", "agent2"],
            mode="discussion",
            host_agent=None
        )
        test_db.add(group)
        test_db.commit()
        
        retrieved = test_db.query(Group).filter(Group.id == "test-group-001").first()
        assert retrieved is not None
        assert retrieved.name == "Test Group"
        assert retrieved.description == "Test Description"
        assert retrieved.members == ["agent1", "agent2"]
        assert retrieved.mode == "discussion"

    def test_group_to_dict(self):
        """测试 Group 序列化方法"""
        group = Group(
            id="test-group-002",
            name="Serialized Group",
            description="Test serialization",
            members=["agent1"],
            mode="discussion"
        )
        data = group.to_dict()
        
        assert isinstance(data, dict)
        assert "id" in data
        assert "name" in data
        assert "description" in data
        assert "members" in data
        assert "mode" in data
        assert "created_at" in data
        assert data["name"] == "Serialized Group"

    def test_group_message_model(self, test_db: Session):
        """测试 GroupMessage 模型"""
        group = Group(id="msg-test-group", name="Message Test", members=["agent1"])
        test_db.add(group)
        test_db.commit()
        
        message = GroupMessage(
            id="msg-001",
            group_id="msg-test-group",
            sender="user",
            role="user",
            content="Hello World"
        )
        test_db.add(message)
        test_db.commit()
        
        retrieved = test_db.query(GroupMessage).filter(GroupMessage.id == "msg-001").first()
        assert retrieved is not None
        assert retrieved.content == "Hello World"
        assert retrieved.sender == "user"
        assert retrieved.role == "user"

    def test_meeting_outcome_model(self, test_db: Session):
        """测试 MeetingOutcome 模型"""
        group = Group(id="meeting-test-group", name="Meeting Test", members=["host", "agent1"])
        test_db.add(group)
        test_db.commit()
        
        outcome = MeetingOutcome(
            id="outcome-001",
            group_id="meeting-test-group",
            meeting_topic="Test Meeting",
            host_agent="host",
            minutes="Meeting completed successfully",
            decisions=[{"decision": "Approved", "reason": "Good plan"}],
            todos=[{"description": "Do something", "assignee": "agent1"}]
        )
        test_db.add(outcome)
        test_db.commit()
        
        retrieved = test_db.query(MeetingOutcome).filter(MeetingOutcome.id == "outcome-001").first()
        assert retrieved is not None
        assert retrieved.meeting_topic == "Test Meeting"
        assert len(retrieved.decisions) == 1
        assert len(retrieved.todos) == 1

    def test_group_task_model(self, test_db: Session):
        """测试 GroupTask 模型"""
        group = Group(id="task-test-group", name="Task Test", members=["agent1"])
        test_db.add(group)
        test_db.commit()
        
        task = GroupTask(
            id="task-001",
            group_id="task-test-group",
            assignee="agent1",
            description="Complete the implementation",
            status="pending",
            meeting_id="outcome-001"
        )
        test_db.add(task)
        test_db.commit()
        
        retrieved = test_db.query(GroupTask).filter(GroupTask.id == "task-001").first()
        assert retrieved is not None
        assert retrieved.assignee == "agent1"
        assert retrieved.description == "Complete the implementation"
        assert retrieved.status == "pending"


class TestGroupService:
    """GroupService 服务层测试"""

    def test_create_group(self, test_db: Session, test_data: dict):
        """测试创建群组"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        group = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        assert group is not None
        assert group.name == group_data["name"]
        assert group.description == group_data["description"]
        assert group.members == group_data["members"]

    def test_get_group(self, test_db: Session, test_data: dict):
        """测试获取群组"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        retrieved = service.get_group(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == group_data["name"]

    def test_get_all_groups(self, test_db: Session, test_data: dict):
        """测试获取所有群组"""
        service = GroupService(test_db)
        
        for group_data in test_data["test_groups"]:
            service.create_group(
                name=group_data["name"],
                description=group_data["description"],
                members=group_data["members"]
            )
        
        groups = service.get_all_groups()
        assert len(groups) == len(test_data["test_groups"])

    def test_update_group(self, test_db: Session, test_data: dict):
        """测试更新群组"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        updated = service.update_group(
            created.id,
            name="Updated Group Name",
            mode="meeting",
            host_agent="architect"
        )
        
        assert updated is not None
        assert updated.name == "Updated Group Name"
        assert updated.mode == "meeting"
        assert updated.host_agent == "architect"

    def test_add_and_remove_member(self, test_db: Session, test_data: dict):
        """测试添加和移除成员"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        original_count = len(created.members)
        
        with_added = service.add_member(created.id, "new-agent")
        assert "new-agent" in with_added.members
        assert len(with_added.members) == original_count + 1
        
        with_removed = service.remove_member(created.id, "new-agent")
        assert "new-agent" not in with_removed.members
        assert len(with_removed.members) == original_count

    def test_add_message(self, test_db: Session, test_data: dict):
        """测试添加消息"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        message_data = test_data["test_messages"][0]
        message = service.add_message(
            group_id=created.id,
            sender=message_data["sender"],
            role=message_data["role"],
            content=message_data["content"],
            metadata=message_data["metadata"]
        )
        
        assert message is not None
        assert message.group_id == created.id
        assert message.sender == message_data["sender"]
        assert message.content == message_data["content"]

    def test_get_messages(self, test_db: Session, test_data: dict):
        """测试获取消息历史"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        for msg_data in test_data["test_messages"]:
            service.add_message(
                group_id=created.id,
                sender=msg_data["sender"],
                role=msg_data["role"],
                content=msg_data["content"],
                metadata=msg_data["metadata"]
            )
        
        messages = service.get_messages(created.id, limit=10)
        assert len(messages) == len(test_data["test_messages"])

    def test_delete_group(self, test_db: Session, test_data: dict):
        """测试删除群组"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        result = service.delete_group(created.id)
        assert result is True
        
        retrieved = service.get_group(created.id)
        assert retrieved is None

    def test_save_meeting_outcome(self, test_db: Session, test_data: dict):
        """测试保存会议结果"""
        from datetime import datetime
        
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        outcome = service.save_meeting_outcome(
            group_id=created.id,
            meeting_topic=test_data["test_meeting_topic"],
            host_agent=test_data["test_host_agent"],
            started_at=datetime.now(),
            minutes="Test meeting completed",
            decisions=[{"decision": "Use microservices", "reason": "Better scalability"}],
            todos=[
                {"description": "Implement auth service", "assignee": "developer"},
                {"description": "Review architecture", "assignee": "architect"}
            ],
            risks=[],
            open_issues=[]
        )
        
        assert outcome is not None
        assert outcome.meeting_topic == test_data["test_meeting_topic"]
        assert len(outcome.decisions) == 1
        assert len(outcome.todos) == 2

    def test_create_and_update_task(self, test_db: Session, test_data: dict):
        """测试创建和更新任务"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        task = service.create_task(
            group_id=created.id,
            assignee="developer",
            description="Write unit tests",
            deadline="2025-01-31",
            meeting_id="test-meeting-001"
        )
        
        assert task is not None
        assert task.assignee == "developer"
        assert task.status == "pending"
        
        updated = service.update_task_status(
            task.id,
            status="in_progress",
            result="Started writing tests"
        )
        
        assert updated is not None
        assert updated.status == "in_progress"
        assert updated.result == "Started writing tests"

    def test_get_pending_tasks(self, test_db: Session, test_data: dict):
        """测试获取待办任务"""
        service = GroupService(test_db)
        group_data = test_data["test_groups"][0]
        
        created = service.create_group(
            name=group_data["name"],
            description=group_data["description"],
            members=group_data["members"]
        )
        
        service.create_task(
            group_id=created.id,
            assignee="developer",
            description="Task 1",
            meeting_id="m1"
        )
        service.create_task(
            group_id=created.id,
            assignee="architect",
            description="Task 2",
            meeting_id="m2"
        )
        
        pending = service.get_pending_tasks()
        assert len(pending) == 2
        
        by_assignee = service.get_pending_tasks(assignee="developer")
        assert len(by_assignee) == 1
        assert by_assignee[0].assignee == "developer"


class TestWebSocketManager:
    """WebSocket 连接管理器测试"""

    def test_connection_manager_initialization(self):
        """测试 ConnectionManager 初始化"""
        from app.api.websocket import ConnectionManager
        
        manager = ConnectionManager()
        assert isinstance(manager.active_connections, dict)
        assert isinstance(manager.group_subscriptions, dict)
        assert len(manager.active_connections) == 0
        assert len(manager.group_subscriptions) == 0

    def test_subscribe_and_unsubscribe(self):
        """测试群组订阅和取消订阅"""
        from app.api.websocket import ConnectionManager
        
        manager = ConnectionManager()
        client_id = "test-client-001"
        group_id = "test-group-001"
        
        manager.subscribe_to_group(client_id, group_id)
        assert group_id in manager.group_subscriptions
        assert client_id in manager.group_subscriptions[group_id]
        
        manager.unsubscribe_from_group(client_id, group_id)
        assert client_id not in manager.group_subscriptions[group_id]

    def test_disconnect_cleanup(self):
        """测试断开连接时的清理"""
        from app.api.websocket import ConnectionManager
        
        manager = ConnectionManager()
        client_id = "test-client-001"
        group1 = "group1"
        group2 = "group2"
        
        manager.subscribe_to_group(client_id, group1)
        manager.subscribe_to_group(client_id, group2)
        
        manager.disconnect(client_id)
        
        assert client_id not in manager.active_connections
        for group_id in [group1, group2]:
            if group_id in manager.group_subscriptions:
                assert client_id not in manager.group_subscriptions[group_id]


class TestAPIRoutes:
    """API 路由注册测试"""

    def test_main_router_includes_profiles(self):
        """测试 profiles 路由已注册"""
        from app.api import main_router
        
        routes = [r.path for r in main_router.routes]
        profile_routes = [r for r in routes if "/api/profiles" in r]
        assert len(profile_routes) > 0

    def test_main_router_includes_groups(self):
        """测试 groups 路由已注册"""
        from app.api import main_router
        
        routes = [r.path for r in main_router.routes]
        group_routes = [r for r in routes if "/api/groups" in r]
        assert len(group_routes) > 0

    def test_hermes_integration_routes(self):
        """测试 Hermes 集成路由已更新"""
        from app.api.hermes_integration import router
        
        routes = [r.path for r in router.routes]
        assert "/hermes/health" in routes
        assert "/hermes/profiles" in routes
        assert "/hermes/chat" in routes
        assert "/hermes/chat/stream" in routes
        assert "/hermes/decompose" in routes
