import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.project import Project, ProjectMember
from app.models.requirement import Requirement
from app.models.task import Task
from app.models.agent import Agent
from app.models.task_execution import TaskExecution
from app.models.acceptance_record import AcceptanceRecord
from app.models.dependency import TaskDependency
from app.models.enums import ProjectStatus
from app.services.project_service import ProjectService
from app.services.agent_scheduler_service import AgentSchedulerService
from app.services.acceptance_service import AcceptanceService
from app.utils.graph import has_cycle, topological_sort, detect_cycle_in_tasks

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


def _make_user(db, user_id=None):
    from app.models.user import User
    from app.utils.security import get_password_hash
    uid = user_id or str(uuid.uuid4())
    user = User(id=uid, username=f"user_{uid[:8]}", email=f"{uid[:8]}@test.com",
                password_hash=get_password_hash("test123"), role="user")
    db.add(user)
    db.commit()
    return user


class TestProjectService:
    def test_create_project(self, db):
        user = _make_user(db)
        svc = ProjectService(db)
        project = svc.create_project("TestProject", user.id, "desc")
        assert project.id is not None
        assert project.name == "TestProject"
        assert project.status == ProjectStatus.created.value

    def test_create_project_duplicate_name(self, db):
        user = _make_user(db)
        svc = ProjectService(db)
        svc.create_project("DupProject", user.id)
        with pytest.raises(ValueError):
            svc.create_project("DupProject", user.id)

    def test_transition_status(self, db):
        user = _make_user(db)
        svc = ProjectService(db)
        project = svc.create_project("TransProject", user.id)
        updated = svc.transition_status(project.id, ProjectStatus.in_progress.value)
        assert updated.status == ProjectStatus.in_progress.value

    def test_transition_invalid(self, db):
        user = _make_user(db)
        svc = ProjectService(db)
        project = svc.create_project("InvProject", user.id)
        with pytest.raises(ValueError):
            svc.transition_status(project.id, ProjectStatus.completed.value)


class TestRequirementLock:
    def test_submit_and_lock_requirement(self, db):
        user = _make_user(db)
        svc = ProjectService(db)
        project = svc.create_project("ReqProject", user.id)
        req = svc.submit_requirement(project.id, "Initial requirement content")
        assert req.is_locked is False
        locked = svc.confirm_and_lock_requirement(project.id, user.id)
        assert locked.is_locked is True

    def test_lock_without_requirement(self, db):
        user = _make_user(db)
        svc = ProjectService(db)
        project = svc.create_project("NoReqProject", user.id)
        with pytest.raises(ValueError):
            svc.confirm_and_lock_requirement(project.id, user.id)


class TestAgentMatching:
    def test_auto_assign_with_available_agent(self, db):
        user = _make_user(db)
        svc = AgentSchedulerService(db)
        agent = svc.register_agent("TestAgent", "opencode", "http://localhost:8080")
        agent.status = "online"
        db.commit()

        project = Project(id=str(uuid.uuid4()), name="AssignProj", slug="assignproj", description="",
                          creator_id=user.id, status=ProjectStatus.created.value)
        db.add(project)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Test Task",
                    description="coding task", type="coding", priority="medium",
                    status="pending", acceptance_criteria="works")
        db.add(task)
        db.commit()

        execution = svc.auto_assign(task.id)
        assert execution is not None
        assert execution.agent_id == agent.id

    def test_auto_assign_no_available_agent(self, db):
        user = _make_user(db)
        svc = AgentSchedulerService(db)

        project = Project(id=str(uuid.uuid4()), name="NoAgentProj", slug="noagentproj", description="",
                          creator_id=user.id, status=ProjectStatus.created.value)
        db.add(project)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Orphan Task",
                    description="coding task", type="coding", priority="medium",
                    status="pending", acceptance_criteria="works")
        db.add(task)
        db.commit()

        result = svc.auto_assign(task.id)
        assert result is None


class TestAcceptanceFlow:
    def test_verify_delivery_pass(self, db):
        user = _make_user(db)
        agent = Agent(id=str(uuid.uuid4()), name="AccAgent", agent_type="opencode",
                      status="online", api_endpoint="http://localhost:8081", config={})
        db.add(agent)

        project = Project(id=str(uuid.uuid4()), name="AccProj", slug="accproj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Acc Task",
                    description="task", type="coding", priority="medium",
                    status="delivered", acceptance_criteria="works")
        db.add(task)

        execution = TaskExecution(id=str(uuid.uuid4()), task_id=task.id, agent_id=agent.id,
                                  status="delivered",
                                  result_summary={"coverage": 85, "test_pass_rate": 95, "output": "files"})
        db.add(execution)

        record = AcceptanceRecord(
            id=str(uuid.uuid4()),
            task_id=task.id,
            reviewer_agent_id=agent.id,
            result="accepted",
        )
        db.add(record)
        db.commit()

        assert record.result == "accepted"

    def test_verify_delivery_fail(self, db):
        user = _make_user(db)
        agent = Agent(id=str(uuid.uuid4()), name="FailAgent", agent_type="opencode",
                      status="online", api_endpoint="http://localhost:8082", config={})
        db.add(agent)

        project = Project(id=str(uuid.uuid4()), name="FailProj", slug="failproj", description="",
                          creator_id=user.id, status=ProjectStatus.in_progress.value)
        db.add(project)
        task = Task(id=str(uuid.uuid4()), project_id=project.id, name="Fail Task",
                    description="task", type="coding", priority="medium",
                    status="delivered", acceptance_criteria="works")
        db.add(task)

        execution = TaskExecution(id=str(uuid.uuid4()), task_id=task.id, agent_id=agent.id,
                                  status="delivered",
                                  result_summary={"coverage": 50, "test_pass_rate": 60})
        db.add(execution)

        record = AcceptanceRecord(
            id=str(uuid.uuid4()),
            task_id=task.id,
            reviewer_agent_id=agent.id,
            result="rejected",
            problem_details="coverage and test pass rate below threshold",
        )
        db.add(record)
        db.commit()

        assert record.result == "rejected"
        assert record.problem_details is not None


class TestDAGValidation:
    def test_no_cycle(self):
        adj = {"A": ["B"], "B": ["C"], "C": []}
        assert has_cycle(adj) is False

    def test_cycle_detected(self):
        adj = {"A": ["B"], "B": ["C"], "C": ["A"]}
        assert has_cycle(adj) is True

    def test_topological_sort(self):
        adj = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        result = topological_sort(adj)
        assert result.index("A") < result.index("B")
        assert result.index("A") < result.index("C")
        assert result.index("B") < result.index("D")
        assert result.index("C") < result.index("D")

    def test_detect_cycle_in_tasks(self):
        edges = [("A", "B"), ("B", "C"), ("C", "A")]
        assert detect_cycle_in_tasks(edges) is True

    def test_no_cycle_in_tasks(self):
        edges = [("A", "B"), ("B", "C")]
        assert detect_cycle_in_tasks(edges) is False


class TestCommitValidation:
    def test_conventional_commit_pattern(self):
        import re
        pattern = re.compile(
            r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
            r"(\(.+\))?: .{1,}"
        )
        assert pattern.match("feat: add login") is not None
        assert pattern.match("fix(auth): fix token expiry") is not None
        assert pattern.match("invalid commit") is None
        assert pattern.match("feat: ") is None
