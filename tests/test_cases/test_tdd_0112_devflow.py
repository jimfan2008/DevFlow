from app.models.user import User
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import asyncio
from typing import AsyncGenerator, Dict, Any
from datetime import datetime, timezone
import uuid

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
if os.path.isdir(_backend_dir):
    sys.path.insert(0, _backend_dir)

from app.database import Base
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.agent import Agent
from app.models.board import Board, BoardColumn
from app.models.workflow_step import WorkflowStep

TEST_ENGINE = create_engine(
    "sqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)


def _teardown_db():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    _setup_db()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        _teardown_db()


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        id="user_intg_001",
        username="integ_user",
        email="integ_user@test.com",
        password_hash="hashed_placeholder",
        role="user",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    try:
        db_session.rollback()
        db_session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def test_admin(db_session):
    admin = User(
        id="user_adm_001",
        username="integ_admin",
        email="integ_admin@test.com",
        password_hash="hashed_admin",
        role="admin",
        status="active",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    yield admin
    try:
        db_session.rollback()
        db_session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": admin.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def test_agent(db_session):
    agent = Agent(
        id="agent_intg_001",
        name="IntegrationAgent",
        agent_type="opencode",
        status="online",
        api_endpoint="http://localhost:9000/agent",
        config={"capabilities": ["coding"], "max_concurrent_tasks": 3, "current_load": 0},
        discovered_by="profile_scan",
        is_named_role=False,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    yield agent
    try:
        db_session.rollback()
        db_session.execute(text("DELETE FROM agents WHERE id = :aid"), {"aid": agent.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def test_project(test_user, db_session):
    project = Project(
        id="proj_intg_001",
        name="IntegrationTestProject",
        slug="integ-test-proj",
        description="Integration test project",
        creator_id=test_user.id,
        current_step=1,
        status="created",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    yield project
    try:
        db_session.rollback()
        db_session.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": project.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def test_task(test_project, db_session):
    task = Task(
        id="task_intg_001",
        project_id=test_project.id,
        name="IntegrationTask",
        description="Integration test task",
        type="coding",
        priority="high",
        status="pending",
        progress=0,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    yield task
    try:
        db_session.rollback()
        db_session.execute(text("DELETE FROM tasks WHERE id = :tid"), {"tid": task.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def test_assigned_task(test_project, test_agent, db_session):
    task = Task(
        id="task_intg_asgn_001",
        project_id=test_project.id,
        name="AssignedTask",
        description="Task assigned to agent",
        type="coding",
        priority="medium",
        assignee_agent_id=test_agent.id,
        status="assigned",
        progress=0,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    yield task
    try:
        db_session.rollback()
        db_session.execute(text("DELETE FROM tasks WHERE id = :tid"), {"tid": task.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def test_board(test_project, db_session):
    board = Board(
        id="board_intg_001",
        project_id=test_project.id,
        name="IntegBoard",
        slug="integ-board",
        description="Integration test board",
        position=0,
        color="#3b82f6",
        is_default=True,
        is_active=True,
    )
    db_session.add(board)
    db_session.commit()
    db_session.refresh(board)
    columns = []
    for name, slug, color, pos in [
        ("To Do", "todo", "#f59e0b", 0),
        ("In Progress", "in_progress", "#3b82f6", 1),
        ("Done", "done", "#10b981", 2),
    ]:
        col = BoardColumn(
            id=f"col_{slug}_{uuid.uuid4().hex[:6]}",
            board_id=board.id,
            name=name,
            slug=slug,
            color=color,
            position=pos,
            is_default=(pos == 0),
            is_active=True,
        )
        db_session.add(col)
        columns.append(col)
    db_session.commit()
    for col in columns:
        db_session.refresh(col)
    yield board
    try:
        db_session.rollback()
        for col in columns:
            db_session.execute(text("DELETE FROM board_columns WHERE id = :cid"), {"cid": col.id})
        db_session.execute(text("DELETE FROM boards WHERE id = :bid"), {"bid": board.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def test_workflow_step(test_project, test_agent, db_session):
    step = WorkflowStep(
        project_id=test_project.id,
        step_number=2,
        step_name="AgentConfirmsGoal",
        executor_agent_id=test_agent.id,
        status="pending",
        input_artifacts={"core_goal": "Build an e-commerce platform"},
        output_artifacts={},
    )
    db_session.add(step)
    db_session.commit()
    db_session.refresh(step)
    yield step
    try:
        db_session.rollback()
        db_session.execute(text("DELETE FROM workflow_steps WHERE id = :sid"), {"sid": step.id})
        db_session.commit()
    except Exception:
        db_session.rollback()


class TestUserModel:
    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        uid = str(uuid.uuid4())
        user = User(
            id=uid,
            username=f"newuser_{uuid.uuid4().hex[:6]}",
            email=f"newuser_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash123",
            role="user",
            status="active",
        )
        db_session.add(user)
        db_session.commit()
        fetched = db_session.query(User).filter(User.id == uid).first()
        assert fetched is not None
        assert fetched.role == "user"
        assert fetched.status == "active"
        assert fetched.to_dict() is not None
        assert fetched.to_dict().get("id") == uid
        db_session.delete(fetched)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_user_default_notification_config(self, db_session):
        uid = str(uuid.uuid4())
        user = User(
            id=uid,
            username=f"default_{uuid.uuid4().hex[:6]}",
            email=f"default_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
            role="user",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.notification_config is not None
        db_session.delete(user)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_user_to_dict_structure(self, db_session, test_user):
        d = test_user.to_dict()
        assert isinstance(d, dict)
        assert "id" in d
        assert "username" in d
        assert "email" in d
        assert "role" in d
        assert "status" in d
        assert d["id"] == test_user.id
        assert d["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_query_nonexistent_user(self, db_session):
        user = db_session.query(User).filter(User.id == "nonexistent_user_id").first()
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user_email(self, db_session, test_user):
        new_email = f"updated_{uuid.uuid4().hex[:6]}@test.com"
        test_user.email = new_email
        db_session.commit()
        db_session.refresh(test_user)
        assert test_user.email == new_email

    @pytest.mark.asyncio
    async def test_delete_user_cascade_check(self, db_session, test_user, test_project):
        before_count = db_session.query(Project).filter(Project.creator_id == test_user.id).count()
        assert before_count >= 1
        db_session.delete(test_user)
        db_session.commit()
        after_count = db_session.query(Project).filter(Project.creator_id == test_user.id).count()
        assert after_count == 0


class TestUserProjectRelationship:
    @pytest.mark.asyncio
    async def test_user_creates_multiple_projects(self, db_session, test_user):
        projects = [
            Project(id=f"p_multi_{i}", name=f"MultiProj{i}", slug=f"multi-{i}", creator_id=test_user.id)
            for i in range(3)
        ]
        db_session.add_all(projects)
        db_session.commit()
        count = db_session.query(Project).filter(Project.creator_id == test_user.id).count()
        assert count >= 3
        for p in projects:
            db_session.delete(p)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_user_admin_has_different_role(self, db_session, test_user, test_admin):
        assert test_user.role == "user"
        assert test_admin.role == "admin"
        users = db_session.query(User).filter(User.role == "admin").all()
        admin_ids = [u.id for u in users]
        assert test_admin.id in admin_ids

    @pytest.mark.asyncio
    async def test_project_has_correct_creator(self, db_session, test_user, test_project):
        project = db_session.query(Project).filter(Project.id == test_project.id).first()
        assert project.creator_id == test_user.id
        creator = db_session.query(User).filter(User.id == project.creator_id).first()
        assert creator is not None
        assert creator.username == "integ_user"

    @pytest.mark.asyncio
    async def test_duplicate_username_raises(self, db_session, test_user):
        dup = User(
            id=str(uuid.uuid4()),
            username=test_user.username,
            email=f"dup_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
            role="user",
        )
        db_session.add(dup)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.asyncio
    async def test_duplicate_email_raises(self, db_session, test_user):
        dup = User(
            id=str(uuid.uuid4()),
            username=f"dup_email_{uuid.uuid4().hex[:6]}",
            email=test_user.email,
            password_hash="hash",
            role="user",
        )
        db_session.add(dup)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


class TestProjectTaskAgentFlow:
    @pytest.mark.asyncio
    async def test_full_flow_user_project_task_agent(self, db_session, test_user, test_agent):
        project = Project(
            id="p_full_flow_001",
            name="FullFlowProject",
            slug="full-flow",
            creator_id=test_user.id,
            status="created",
        )
        db_session.add(project)
        db_session.commit()
        task = Task(
            id="t_full_flow_001",
            project_id=project.id,
            name="FullFlowTask",
            description="Task in full flow",
            type="coding",
            priority="high",
            assignee_agent_id=test_agent.id,
            status="assigned",
            progress=0,
        )
        db_session.add(task)
        db_session.commit()
        fetched_task = db_session.query(Task).filter(Task.id == "t_full_flow_001").first()
        assert fetched_task is not None
        assert fetched_task.project_id == project.id
        assert fetched_task.assignee_agent_id == test_agent.id
        fetched_agent = db_session.query(Agent).filter(Agent.id == test_agent.id).first()
        assert fetched_agent is not None
        db_session.delete(fetched_task)
        db_session.delete(project)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_task_status_update_flow(self, db_session, test_task):
        task = db_session.query(Task).filter(Task.id == test_task.id).first()
        assert task.status == "pending"
        assert task.progress == 0
        task.status = "running"
        task.progress = 50
        db_session.commit()
        db_session.refresh(task)
        assert task.status == "running"
        assert task.progress == 50
        task.status = "delivered"
        task.progress = 100
        db_session.commit()
        db_session.refresh(task)
        assert task.status == "delivered"
        assert task.progress == 100

    @pytest.mark.asyncio
    async def test_task_assignee_relationship(self, db_session, test_assigned_task, test_agent):
        task = db_session.query(Task).filter(Task.id == test_assigned_task.id).first()
        assert task.assignee_agent_id == test_agent.id
        assert task.status == "assigned"
        agent = db_session.query(Agent).filter(Agent.id == test_agent.id).first()
        assert agent is not None
        assert agent.status == "online"

    @pytest.mark.asyncio
    async def test_project_task_count(self, db_session, test_project, test_task, test_assigned_task):
        count = db_session.query(Task).filter(Task.project_id == test_project.id).count()
        assert count >= 2

    @pytest.mark.asyncio
    async def test_delete_task_and_check_project(self, db_session, test_project, test_task):
        before = db_session.query(Task).filter(Task.project_id == test_project.id).count()
        assert before >= 1
        db_session.delete(test_task)
        db_session.commit()
        after = db_session.query(Task).filter(Task.project_id == test_project.id).count()
        assert after == before - 1
        deleted = db_session.query(Task).filter(Task.id == test_task.id).first()
        assert deleted is None


class TestBoardWorkflowFlow:
    @pytest.mark.asyncio
    async def test_board_has_columns(self, db_session, test_project, test_board):
        board = db_session.query(Board).filter(Board.id == test_board.id).first()
        assert board is not None
        assert board.project_id == test_project.id
        columns = db_session.query(BoardColumn).filter(BoardColumn.board_id == board.id).all()
        assert len(columns) == 3
        slugs = [c.slug for c in columns]
        assert "todo" in slugs
        assert "in_progress" in slugs
        assert "done" in slugs

    @pytest.mark.asyncio
    async def test_workflow_step_status_progression(self, db_session, test_project, test_agent):
        steps_data = [
            (1, "Step1", "completed"),
            (2, "Step2", "in_progress"),
            (3, "Step3", "pending"),
        ]
        steps = []
        for num, name, status in steps_data:
            step = WorkflowStep(
                project_id=test_project.id,
                step_number=num,
                step_name=name,
                executor_agent_id=test_agent.id if num == 2 else None,
                status=status,
            )
            db_session.add(step)
            steps.append(step)
        db_session.commit()
        fetched = db_session.query(WorkflowStep).filter(
            WorkflowStep.project_id == test_project.id,
            WorkflowStep.step_number.in_([1, 2, 3]),
        ).order_by(WorkflowStep.step_number).all()
        assert len(fetched) == 3
        assert fetched[0].status == "completed"
        assert fetched[1].status == "in_progress"
        assert fetched[2].status == "pending"
        for s in steps:
            db_session.delete(s)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_workflow_step_with_agent_executor(self, db_session, test_workflow_step, test_agent):
        step = db_session.query(WorkflowStep).filter(
            WorkflowStep.id == test_workflow_step.id
        ).first()
        assert step is not None
        assert step.executor_agent_id == test_agent.id
        assert step.status == "pending"
        assert step.input_artifacts.get("core_goal") == "Build an e-commerce platform"

    @pytest.mark.asyncio
    async def test_workflow_step_mark_in_progress(self, db_session, test_workflow_step):
        step = db_session.query(WorkflowStep).filter(
            WorkflowStep.id == test_workflow_step.id
        ).first()
        step.status = "in_progress"
        step.started_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(step)
        assert step.status == "in_progress"
        assert step.started_at is not None


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_query_nonexistent_project(self, db_session):
        project = db_session.query(Project).filter(Project.id == "nonexistent_project").first()
        assert project is None

    @pytest.mark.asyncio
    async def test_query_nonexistent_task(self, db_session):
        task = db_session.query(Task).filter(Task.id == "nonexistent_task").first()
        assert task is None

    @pytest.mark.asyncio
    async def test_query_nonexistent_agent(self, db_session):
        agent = db_session.query(Agent).filter(Agent.id == "nonexistent_agent").first()
        assert agent is None

    @pytest.mark.asyncio
    async def test_query_nonexistent_workflow_step(self, db_session):
        step = db_session.query(WorkflowStep).filter(WorkflowStep.id == 99999).first()
        assert step is None

    @pytest.mark.asyncio
    async def test_project_with_zero_current_step(self, db_session, test_user):
        project = Project(
            id="p_zero_step",
            name="ZeroStepProject",
            slug="zero-step",
            creator_id=test_user.id,
            current_step=0,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        assert project.current_step == 0
        db_session.delete(project)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_task_with_empty_name(self, db_session, test_project):
        task = Task(
            id="task_empty_name",
            project_id=test_project.id,
            name="",
            type="coding",
            priority="low",
            status="pending",
            progress=0,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.name == ""
        db_session.delete(task)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_task_with_long_name(self, db_session, test_project):
        long_name = "x" * 200
        task = Task(
            id="task_long_name",
            project_id=test_project.id,
            name=long_name,
            type="coding",
            priority="low",
            status="pending",
            progress=0,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert len(task.name) == 200
        db_session.delete(task)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_invalid_task_priority_raises(self, db_session, test_project):
        task = Task(
            id="task_bad_priority",
            project_id=test_project.id,
            name="BadPriority",
            type="coding",
            priority="invalid_priority",
            status="pending",
            progress=0,
        )
        db_session.add(task)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.asyncio
    async def test_invalid_task_status_raises(self, db_session, test_project):
        task = Task(
            id="task_bad_status",
            project_id=test_project.id,
            name="BadStatus",
            type="coding",
            priority="medium",
            status="invalid_status_xyz",
            progress=0,
        )
        db_session.add(task)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.asyncio
    async def test_invalid_agent_type_raises(self, db_session):
        agent = Agent(
            id="agent_bad_type",
            name="BadTypeAgent",
            agent_type="invalid_agent_type_xyz",
            status="online",
            discovered_by="profile_scan",
        )
        db_session.add(agent)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.asyncio
    async def test_invalid_project_status_raises(self, db_session, test_user):
        project = Project(
            id="p_bad_status",
            name="BadStatusProject",
            slug="bad-status",
            creator_id=test_user.id,
            status="invalid_status",
        )
        db_session.add(project)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    @pytest.mark.asyncio
    async def test_rollback_on_constraint_violation(self, db_session, test_project):
        original_name = test_project.name
        try:
            test_project.name = None
            db_session.commit()
        except Exception:
            db_session.rollback()
        db_session.refresh(test_project)
        assert test_project.name == original_name

    @pytest.mark.asyncio
    async def test_agent_status_transition(self, db_session):
        agent = Agent(
            id="agent_status_test",
            name="StatusTestAgent",
            agent_type="cursor",
            status="offline",
            discovered_by="profile_scan",
        )
        db_session.add(agent)
        db_session.commit()
        agent.status = "online"
        db_session.commit()
        db_session.refresh(agent)
        assert agent.status == "online"
        agent.status = "busy"
        db_session.commit()
        db_session.refresh(agent)
        assert agent.status == "busy"
        db_session.delete(agent)
        db_session.commit()


class TestModuleDataFlow:
    @pytest.mark.asyncio
    async def test_user_project_task_agent_data_chain(self, db_session):
        uid = str(uuid.uuid4())
        user = User(
            id=uid,
            username=f"chain_user_{uuid.uuid4().hex[:6]}",
            email=f"chain_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
            role="user",
        )
        db_session.add(user)
        db_session.commit()
        project = Project(
            id="p_chain_001",
            name="ChainProject",
            slug="chain-project",
            creator_id=user.id,
            status="created",
        )
        db_session.add(project)
        db_session.commit()
        task = Task(
            id="t_chain_001",
            project_id=project.id,
            name="ChainTask",
            type="coding",
            priority="high",
            status="pending",
        )
        db_session.add(task)
        db_session.commit()
        assert db_session.query(User).filter(User.id == uid).count() == 1
        assert db_session.query(Project).filter(Project.id == "p_chain_001").count() == 1
        assert db_session.query(Task).filter(Task.id == "t_chain_001").count() == 1
        db_session.delete(task)
        db_session.delete(project)
        db_session.delete(user)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_agent_without_project_independent(self, db_session):
        agent = Agent(
            id="agent_independent",
            name="IndependentAgent",
            agent_type="codearts",
            status="offline",
            discovered_by="profile_scan",
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)
        assert agent.id == "agent_independent"
        assert agent.status == "offline"
        db_session.delete(agent)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_project_without_tasks(self, db_session, test_user):
        project = Project(
            id="p_no_tasks",
            name="ProjectNoTasks",
            slug="no-tasks",
            creator_id=test_user.id,
        )
        db_session.add(project)
        db_session.commit()
        tasks = db_session.query(Task).filter(Task.project_id == project.id).all()
        assert len(tasks) == 0
        db_session.delete(project)
        db_session.commit()
