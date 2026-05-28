import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch

from app.database import Base
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.requirement import Requirement
from app.models.task import Task
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.models.task_execution import TaskExecution
from app.models.acceptance_record import AcceptanceRecord
from app.models.group import Group, GroupMessage
from app.models.enums import ProjectStatus, GroupMode
from app.services.project_service import ProjectService
from app.services.agent_scheduler_service import AgentSchedulerService
from app.services.acceptance_service import AcceptanceService
from app.services.meeting_service import MeetingService
from app.services.notification_service import NotificationService
from app.utils.security import get_password_hash

TEST_ENGINE = create_engine(
    "sqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


@pytest.fixture
def db():
    session = TestSessionLocal()
    yield session
    session.close()


def _make_user(db):
    uid = str(uuid.uuid4())
    user = User(id=uid, username=f"owner_{uid[:8]}", email=f"{uid[:8]}@test.com",
                password_hash=get_password_hash("test123"), role="user")
    db.add(user)
    db.commit()
    return user


def _make_hermes(db):
    agent = Agent(id=str(uuid.uuid4()), name="Hermes-Main", agent_type="hermes",
                  status="online", config={"gateway_port": 8080, "api_key": "key"})
    db.add(agent)
    db.commit()
    return agent


def _make_coding_agent(db, name="OpenCode-1"):
    agent = Agent(id=str(uuid.uuid4()), name=name, agent_type="opencode",
                  status="online", api_endpoint="http://localhost:9001", config={})
    db.add(agent)
    db.commit()
    return agent


class TestFullFlowIntegration:
    def test_create_project_to_acceptance(self, db):
        user = _make_user(db)
        hermes = _make_hermes(db)
        coding = _make_coding_agent(db)

        project_svc = ProjectService(db)
        project = project_svc.create_project("FullFlowProject", user.id, "A complete flow test")
        assert project.status == ProjectStatus.created.value

        group = db.query(Group).filter(Group.project_id == project.id).first()
        assert group is not None

        meeting_svc = MeetingService(db)
        meeting = meeting_svc.start_meeting(
            group.id, "需求评审会议", "Hermes-Main",
            meeting_type="requirement_review"
        )
        assert meeting.mode == GroupMode.meeting.value

        outcome = meeting_svc.stop_meeting(
            group.id,
            minutes="需求评审完成，确认需求",
            decisions=[{"decision": "需求确认"}],
        )
        assert outcome is not None

        req = project_svc.submit_requirement(project.id, "用户登录功能，支持OAuth2")
        assert req.is_locked is False

        locked = project_svc.confirm_and_lock_requirement(project.id, user.id)
        assert locked.is_locked is True

        project_svc.transition_status(project.id, ProjectStatus.in_progress.value)
        db.refresh(project)
        assert project.status == ProjectStatus.in_progress.value

        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="实现登录功能",
                    description="coding", type="coding", priority="high",
                    status="pending", acceptance_criteria="登录成功",
                    agent_type_preference="opencode")
        db.add(task)
        db.commit()

        scheduler_svc = AgentSchedulerService(db)
        execution = scheduler_svc.assign_task(task.id, coding.id)
        assert execution.status == "pending"

        task.status = "assigned"
        task.assignee_agent_id = coding.id
        db.commit()

        task.status = "delivered"
        execution.status = "delivered"
        execution.result_summary = {"coverage": 90, "test_pass_rate": 95, "output": "src/"}
        db.commit()

        record = AcceptanceRecord(
            id=str(uuid.uuid4()),
            task_id=task.id,
            reviewer_agent_id=coding.id,
            result="accepted",
        )
        db.add(record)
        db.commit()

        assert record.result == "accepted"

        notification_svc = NotificationService(db)
        notification_svc.notify_requirement_confirmed(project.id, user.id, project.name)
        unread = notification_svc.get_unread_count(user.id)
        assert unread > 0


class TestCommunicationConstraint:
    def test_devflow_only_via_hermes_skills(self, db):
        user = _make_user(db)
        hermes = _make_hermes(db)
        coding = _make_coding_agent(db)

        project = Project(id=str(uuid.uuid4()), name="CommProj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Comm Task",
                    description="task", type="coding", priority="medium",
                    status="pending", acceptance_criteria="works")
        db.add(task)
        db.commit()

        skill = HermesSkill(
            id=str(uuid.uuid4()),
            hermes_agent_id=hermes.id,
            skill_type="assign_task",
            status="active",
            coding_agent_id=coding.id,
            task_id=task.id,
            connection_status="connected",
        )
        db.add(skill)
        db.commit()

        assert task.assignee_agent_id is None or task.assignee_agent_id == coding.id
        assert coding.hermes_agent_id is None or coding.hermes_agent_id == hermes.id

        direct_endpoints = ["/api/agents/direct-command", "/api/agents/send-task"]
        all_routes = []
        from app.main import app
        for route in app.routes:
            if hasattr(route, 'path'):
                all_routes.append(route.path)
        for endpoint in direct_endpoints:
            assert endpoint not in all_routes, f"DevFlow不应有直接与编程Agent通信的路由: {endpoint}"


class TestWebSocketIntegration:
    def test_group_chat_message_flow(self, db):
        user = _make_user(db)
        group = Group(id=str(uuid.uuid4()), name="ChatGroup", description="test",
                      members=[user.id], mode=GroupMode.discussion.value)
        db.add(group)
        db.commit()

        msg1 = GroupMessage(id=str(uuid.uuid4()), group_id=group.id,
                            sender=user.username, role="user",
                            content="Hello team!", is_streaming=False)
        db.add(msg1)

        msg2 = GroupMessage(id=str(uuid.uuid4()), group_id=group.id,
                            sender="Hermes-Main", role="assistant",
                            content="Welcome! Let's start.", is_streaming=False)
        db.add(msg2)
        db.commit()

        messages = db.query(GroupMessage).filter(GroupMessage.group_id == group.id).all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_meeting_start_and_stop(self, db):
        user = _make_user(db)
        hermes = _make_hermes(db)

        group = Group(id=str(uuid.uuid4()), name="MeetingGroup", description="test",
                      members=[user.id], mode=GroupMode.discussion.value,
                      project_id=None)
        db.add(group)
        db.commit()

        meeting_svc = MeetingService(db)
        updated_group = meeting_svc.start_meeting(
            group.id, "技术方案评审", "Hermes-Main",
            meeting_type="tech_solution"
        )
        assert updated_group.mode == GroupMode.meeting.value

        outcome = meeting_svc.stop_meeting(
            group.id,
            minutes="方案确定",
            decisions=[{"decision": "采用微服务架构"}],
            todos=[{"assignee": "OpenCode-1", "description": "搭建微服务框架"}],
        )
        assert outcome.meeting_type == "tech_solution"

        db.refresh(group)
        assert group.mode == GroupMode.discussion.value
