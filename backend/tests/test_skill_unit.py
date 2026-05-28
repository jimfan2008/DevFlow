import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch, MagicMock

from app.database import Base
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.models.task import Task
from app.models.project import Project
from app.models.user import User
from app.models.enums import ProjectStatus
from app.services.skill_scheduler import SkillSchedulerService
from app.services.skill_crud import ensure_four_skills, get_skill_by_type
from app.core.exceptions import SkillNoAgentError, SkillConnectError, SkillOverloadedError

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


def _make_hermes_agent(db):
    agent = Agent(id=str(uuid.uuid4()), name="Hermes-1", agent_type="hermes",
                  status="online", config={"gateway_port": 8080, "api_key": "test-key"})
    db.add(agent)
    db.commit()
    return agent


def _make_coding_agent(db, name="OpenCode-1", agent_type="opencode"):
    agent = Agent(id=str(uuid.uuid4()), name=name, agent_type=agent_type,
                  status="online", api_endpoint="http://localhost:9001", config={})
    db.add(agent)
    db.commit()
    return agent


def _make_user(db):
    from app.utils.security import get_password_hash
    uid = str(uuid.uuid4())
    user = User(id=uid, username=f"user_{uid[:8]}", email=f"{uid[:8]}@test.com",
                password_hash=get_password_hash("test123"), role="user")
    db.add(user)
    db.commit()
    return user


class TestSkillDiscover:
    @pytest.mark.asyncio
    async def test_discover_no_hermes_agent(self, db):
        svc = SkillSchedulerService(db)
        with pytest.raises(SkillNoAgentError):
            await svc.discover_coding_agents()

    @pytest.mark.asyncio
    async def test_discover_with_hermes_agent(self, db):
        hermes = _make_hermes_agent(db)
        _make_coding_agent(db)
        svc = SkillSchedulerService(db)
        with patch.object(svc, '_scan_coding_agents_from_db', return_value=[
            {"name": "OpenCode-1", "agent_type": "opencode", "status": "online", "api_endpoint": "http://localhost:9001"}
        ]):
            result = await svc.discover_coding_agents(hermes_agent_id=hermes.id)
            assert result["status"] == "success"


class TestSkillConnect:
    @pytest.mark.asyncio
    async def test_connect_agent_not_found(self, db):
        hermes = _make_hermes_agent(db)
        svc = SkillSchedulerService(db)
        with pytest.raises(SkillConnectError):
            await svc.connect_coding_agent(hermes.id, "nonexistent-id")

    @pytest.mark.asyncio
    async def test_connect_success(self, db):
        hermes = _make_hermes_agent(db)
        coding = _make_coding_agent(db)
        svc = SkillSchedulerService(db)
        with patch('app.services.skill_scheduler.GatewayClient') as MockGW:
            mock_client = AsyncMock()
            mock_client.send_message_non_stream = AsyncMock(return_value="connected")
            MockGW.return_value = mock_client
            result = await svc.connect_coding_agent(hermes.id, coding.id)
            assert result["connection_status"] == "connected"


class TestSkillAssign:
    @pytest.mark.asyncio
    async def test_assign_task_not_found(self, db):
        hermes = _make_hermes_agent(db)
        svc = SkillSchedulerService(db)
        with pytest.raises(ValueError):
            await svc.assign_task(hermes.id, "nonexistent-task")

    @pytest.mark.asyncio
    async def test_assign_all_agents_overloaded(self, db):
        hermes = _make_hermes_agent(db)
        user = _make_user(db)
        project = Project(id=str(uuid.uuid4()), name="OverloadProj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Overload Task",
                    description="coding", type="coding", priority="medium",
                    status="todo", acceptance_criteria="works")
        db.add(task)
        db.commit()
        svc = SkillSchedulerService(db)
        with pytest.raises(SkillOverloadedError):
            await svc.assign_task(hermes.id, task.id)


class TestSkillReceive:
    @pytest.mark.asyncio
    async def test_handle_progress_message(self, db):
        user = _make_user(db)
        project = Project(id=str(uuid.uuid4()), name="RecvProj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        coding = _make_coding_agent(db)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Progress Task",
                    description="task", type="coding", priority="medium",
                    status="assigned", acceptance_criteria="works",
                    assignee_agent_id=coding.id)
        db.add(task)
        db.commit()

        svc = SkillSchedulerService(db)
        result = await svc.handle_skill_message({
            "type": "progress",
            "agent_id": coding.id,
            "task_id": task.id,
            "content": {"progress": 50, "message": "working"},
        })
        assert result["status"] == "processed"
        assert result["task_status"] == "running"

    @pytest.mark.asyncio
    async def test_handle_deliver_message(self, db):
        user = _make_user(db)
        project = Project(id=str(uuid.uuid4()), name="DeliverProj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        coding = _make_coding_agent(db)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Deliver Task",
                    description="task", type="coding", priority="medium",
                    status="assigned", acceptance_criteria="works",
                    assignee_agent_id=coding.id)
        db.add(task)
        db.commit()

        svc = SkillSchedulerService(db)
        result = await svc.handle_skill_message({
            "type": "deliver",
            "agent_id": coding.id,
            "task_id": task.id,
            "content": {"result_summary": "done", "artifacts": {}, "test_results": {}},
        })
        assert result["status"] == "processed"
        assert result["task_status"] == "delivered"

    @pytest.mark.asyncio
    async def test_handle_fail_message(self, db):
        user = _make_user(db)
        project = Project(id=str(uuid.uuid4()), name="FailProj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        coding = _make_coding_agent(db)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Fail Task",
                    description="task", type="coding", priority="medium",
                    status="assigned", acceptance_criteria="works",
                    assignee_agent_id=coding.id)
        db.add(task)
        db.commit()

        svc = SkillSchedulerService(db)
        result = await svc.handle_skill_message({
            "type": "fail",
            "agent_id": coding.id,
            "task_id": task.id,
            "content": {"error_message": "something broke"},
        })
        assert result["task_status"] == "failed"


class TestSkillCRUD:
    def test_ensure_four_skills(self, db):
        hermes = _make_hermes_agent(db)
        skills = ensure_four_skills(db, hermes.id)
        db.commit()
        assert len(skills) == 4
        types = {s.skill_type for s in skills}
        assert types == {"discover_agent", "connect_agent", "assign_task", "receive_message"}

    def test_get_skill_by_type(self, db):
        hermes = _make_hermes_agent(db)
        ensure_four_skills(db, hermes.id)
        db.commit()
        skill = get_skill_by_type(db, hermes.id, "discover_agent")
        assert skill is not None
        assert skill.skill_type == "discover_agent"


class TestWebhookCallback:
    @pytest.mark.asyncio
    async def test_webhook_progress_callback(self, db):
        user = _make_user(db)
        project = Project(id=str(uuid.uuid4()), name="WHProj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        coding = _make_coding_agent(db)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="WH Task",
                    description="task", type="coding", priority="medium",
                    status="assigned", acceptance_criteria="works",
                    assignee_agent_id=coding.id)
        db.add(task)
        db.commit()

        svc = SkillSchedulerService(db)
        result = await svc.handle_skill_message({
            "type": "progress",
            "agent_id": coding.id,
            "task_id": task.id,
            "content": {"progress": 30, "message": "coding..."},
        })
        assert result["status"] == "processed"


class TestReconnectAndLoadBalance:
    @pytest.mark.asyncio
    async def test_reconnect_on_failure(self, db):
        hermes = _make_hermes_agent(db)
        coding = _make_coding_agent(db)
        svc = SkillSchedulerService(db)
        with patch('app.services.skill_scheduler.GatewayClient') as MockGW:
            mock_client = MagicMock()
            mock_client.send_message_non_stream = AsyncMock(side_effect=Exception("connection refused"))
            mock_client._api_key = "test-key"
            MockGW.return_value = mock_client
            with pytest.raises(SkillConnectError):
                await svc.connect_coding_agent(hermes.id, coding.id)

    def test_load_balance_selects_least_loaded(self, db):
        user = _make_user(db)
        hermes = _make_hermes_agent(db)
        agent1 = _make_coding_agent(db, "Agent1", "opencode")
        agent2 = _make_coding_agent(db, "Agent2", "opencode")

        project = Project(id=str(uuid.uuid4()), name="LBProj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)

        busy_task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Busy Task",
                         description="task", type="coding", priority="medium",
                         status="running", acceptance_criteria="works",
                         assignee_agent_id=agent1.id)
        db.add(busy_task)

        new_task = Task(id=str(uuid.uuid4()), project_id=project.id, name="New Task",
                        description="task", type="coding", priority="medium",
                        status="todo", acceptance_criteria="works",
                        agent_type_preference="opencode")
        db.add(new_task)
        db.commit()

        svc = SkillSchedulerService(db)
        selected = svc._select_best_agent(new_task, hermes.id)
        assert selected == agent2.id
