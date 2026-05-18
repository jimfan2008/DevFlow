#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 测试配置 (TDD 版本)
提供完整的 pytest 配置、Fixtures、测试数据工厂
"""

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport
import asyncio
from typing import AsyncGenerator, Dict, Any
from datetime import datetime, timezone
import json
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.models.task import Task
from app.models.board import Board, BoardColumn
from app.models.dependency import TaskDependency
from app.models.project import Project, ProjectMember
from app.models.comment import Comment
from app.models.agent import Agent
from app.models.requirement import Requirement
from app.models.acceptance_record import AcceptanceRecord
from app.models.task_execution import TaskExecution
from app.utils.security import get_password_hash

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "fixtures")

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_devflow.db")
TEST_ENGINE = create_engine(TEST_DB_URL, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def setup_test_database():
    Base.metadata.create_all(bind=TEST_ENGINE)


def teardown_test_database():
    Base.metadata.drop_all(bind=TEST_ENGINE)


def load_fixture_data(name: str) -> Dict[str, Any]:
    filepath = os.path.join(TEST_DATA_DIR, f"{name}.json")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Fixture file not found: {filepath}")
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator:
    setup_test_database()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        teardown_test_database()


@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncGenerator:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def load_fixture():
    def _load(name: str) -> Dict[str, Any]:
        return load_fixture_data(name)
    return _load


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session) -> User:
    data = load_fixture_data("users")["test_user"]
    user = User(
        id=data["id"],
        username=data["username"],
        email=data["email"],
        password_hash=get_password_hash(data["password"]),
        full_name=data["full_name"],
        role=data["role"],
        is_active=data["is_active"],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_admin(db_session) -> User:
    data = load_fixture_data("users")["test_admin"]
    admin = User(
        id=data["id"],
        username=data["username"],
        email=data["email"],
        password_hash=get_password_hash(data["password"]),
        full_name=data["full_name"],
        role=data["role"],
        is_active=data["is_active"],
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    yield admin
    db_session.delete(admin)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_project_owner(db_session) -> User:
    data = load_fixture_data("users")["project_owner"]
    owner = User(
        id=data["id"],
        username=data["username"],
        email=data["email"],
        password_hash=get_password_hash(data["password"]),
        full_name=data["full_name"],
        role=data["role"],
        is_active=data["is_active"],
    )
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    yield owner
    db_session.delete(owner)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_project(test_project_owner: User, db_session) -> Project:
    data = load_fixture_data("projects")["ecommerce_project"]
    project = Project(
        id=data["id"],
        name=data["name"],
        slug=data["slug"],
        description=data["description"],
        creator_id=test_project_owner.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    yield project
    db_session.delete(project)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_board(test_project: Project, test_user: User, db_session) -> Board:
    board = Board(
        id="board_001",
        project_id=test_project.id,
        name="测试看板",
        slug="test-board",
        description="测试看板描述",
        position=0,
        color="#3b82f6",
        is_default=True,
        is_active=True,
    )
    db_session.add(board)
    db_session.commit()
    db_session.refresh(board)

    columns_data = [
        ("待处理", "todo", "#f59e0b", 0),
        ("进行中", "in_progress", "#3b82f6", 1),
        ("测试中", "testing", "#8b5cf6", 2),
        ("已完成", "done", "#10b981", 3),
    ]
    columns = []
    for name, slug, color, pos in columns_data:
        col = BoardColumn(
            id=f"col_{test_project.slug}_{slug}",
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

    for col in columns:
        db_session.delete(col)
    db_session.commit()
    db_session.delete(board)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_column(test_board: Board, db_session) -> BoardColumn:
    column = db_session.query(BoardColumn).filter_by(board_id=test_board.id, is_default=True).first()
    if not column:
        column = BoardColumn(
            id="col_default",
            board_id=test_board.id,
            name="默认列",
            slug="default",
            color="#3b82f6",
            position=0,
            is_default=True,
            is_active=True,
        )
        db_session.add(column)
        db_session.commit()
        db_session.refresh(column)
    yield column


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: User) -> dict:
    from app.utils.security import create_access_token
    token = create_access_token(data={"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def opencode_agent(db_session) -> Agent:
    data = load_fixture_data("agents")["opencode_agent"]
    agent = Agent(
        id=data["id"],
        name=data["name"],
        agent_type=data["agent_type"],
        status=data["status"],
        api_endpoint=data["api_endpoint"],
        config=data["config"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    yield agent
    db_session.delete(agent)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def cursor_agent(db_session) -> Agent:
    data = load_fixture_data("agents")["cursor_agent"]
    agent = Agent(
        id=data["id"],
        name=data["name"],
        agent_type=data["agent_type"],
        status=data["status"],
        api_endpoint=data["api_endpoint"],
        config=data["config"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    yield agent
    db_session.delete(agent)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def claude_agent(db_session) -> Agent:
    data = load_fixture_data("agents")["claude_code_agent"]
    agent = Agent(
        id=data["id"],
        name=data["name"],
        agent_type=data["agent_type"],
        status=data["status"],
        api_endpoint=data["api_endpoint"],
        config=data["config"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    yield agent
    db_session.delete(agent)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def codebuddy_agent(db_session) -> Agent:
    data = load_fixture_data("agents")["codebuddy_agent"]
    agent = Agent(
        id=data["id"],
        name=data["name"],
        agent_type=data["agent_type"],
        status=data["status"],
        api_endpoint=data["api_endpoint"],
        config=data["config"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    yield agent
    db_session.delete(agent)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def all_agents(db_session) -> Dict[str, Agent]:
    fixture_agents = load_fixture_data("agents")
    created_agents = {}
    for key, data in fixture_agents.items():
        agent = Agent(
            id=data["id"],
            name=data["name"],
            agent_type=data["agent_type"],
            status=data["status"],
            api_endpoint=data.get("api_endpoint"),
            config=data.get("config"),
        )
        db_session.add(agent)
        created_agents[key] = agent
    db_session.commit()
    for key in created_agents:
        db_session.refresh(created_agents[key])
    yield created_agents
    for key in created_agents:
        db_session.delete(created_agents[key])
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_requirement(test_project: Project, db_session) -> Requirement:
    data = load_fixture_data("requirements")["ecommerce_requirement_v1"]
    req = Requirement(
        id=data["id"],
        project_id=test_project.id,
        content=data["content"],
        version=data["version"],
        is_locked=data["is_locked"],
        confirmed_at=None,
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    yield req
    db_session.delete(req)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def locked_requirement(test_project: Project, db_session) -> Requirement:
    data = load_fixture_data("requirements")["ecommerce_requirement_locked"]
    req = Requirement(
        id=data["id"],
        project_id=test_project.id,
        content=data["content"],
        version=data["version"],
        is_locked=data["is_locked"],
        confirmed_at=datetime.now(timezone.utc),
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    yield req
    db_session.delete(req)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_task_ai(test_project: Project, test_board: Board, test_column: BoardColumn, test_user: User, opencode_agent: Agent, db_session) -> Task:
    data = load_fixture_data("tasks")["user_management_task"]
    task = Task(
        id=data["id"],
        title=data["name"],
        description=data["description"],
        board_id=test_board.id,
        column_id=test_column.id,
        status=data["status"],
        priority=data["priority"],
        agent_type=data["agent_type"],
        is_blocked=data["is_blocked"],
        acceptance_criteria=data["acceptance_criteria"],
        creator_id=test_user.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    yield task
    db_session.delete(task)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def assigned_task(test_project: Project, test_board: Board, test_column: BoardColumn, test_user: User, opencode_agent: Agent, db_session) -> Task:
    data = load_fixture_data("tasks")["product_management_task"]
    task = Task(
        id=data["id"],
        title=data["name"],
        description=data["description"],
        board_id=test_board.id,
        column_id=test_column.id,
        status=data["status"],
        priority=data["priority"],
        agent_type=data["agent_type"],
        is_blocked=data["is_blocked"],
        acceptance_criteria=data["acceptance_criteria"],
        creator_id=test_user.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    yield task
    db_session.delete(task)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def delivered_task(test_project: Project, test_board: Board, test_column: BoardColumn, test_user: User, opencode_agent: Agent, db_session) -> Task:
    data = load_fixture_data("tasks")["delivered_task"]
    task = Task(
        id=data["id"],
        title=data["name"],
        description=data["description"],
        board_id=test_board.id,
        column_id=test_column.id,
        status=data["status"],
        priority=data["priority"],
        agent_type=data["agent_type"],
        is_blocked=data["is_blocked"],
        acceptance_criteria=data["acceptance_criteria"],
        creator_id=test_user.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    yield task
    db_session.delete(task)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def test_task_execution(delivered_task: Task, opencode_agent: Agent, db_session) -> TaskExecution:
    data = load_fixture_data("task_executions")["successful_execution"]
    execution = TaskExecution(
        id=data["id"],
        task_id=delivered_task.id,
        agent_id=data["agent_id"],
        status=data["status"],
        result_summary=data["result_summary"],
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)
    yield execution
    db_session.delete(execution)
    db_session.commit()


@pytest_asyncio.fixture(scope="function")
async def passed_acceptance(test_task_execution: TaskExecution, db_session) -> AcceptanceRecord:
    data = load_fixture_data("acceptance_records")["passed_acceptance"]
    record = AcceptanceRecord(
        id=data["id"],
        task_execution_id=test_task_execution.id,
        result=data["result"],
        problem_details=data["problem_details"],
        reviewer=data["reviewer"],
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    yield record
    db_session.delete(record)
    db_session.commit()


@pytest.fixture
def task_factory():
    def _create_task_data(overrides: dict = None):
        data = {
            "title": "默认任务标题",
            "description": "默认任务描述",
            "priority": "medium",
            "agent_type": "opencode",
            "acceptance_criteria": "功能正常运行",
        }
        if overrides:
            data.update(overrides)
        return data
    return _create_task_data


@pytest.fixture
def project_factory():
    def _create_project_data(overrides: dict = None):
        data = {
            "name": "默认项目",
            "slug": "default-project",
            "description": "默认项目描述",
        }
        if overrides:
            data.update(overrides)
        return data
    return _create_project_data


@pytest.fixture
def agent_factory():
    def _create_agent_data(overrides: dict = None):
        data = {
            "name": "新 Agent",
            "agent_type": "opencode",
            "status": "online",
            "api_endpoint": "http://localhost:8080/agents/new",
            "config": {
                "capabilities": ["coding"],
                "max_concurrent_tasks": 3,
                "current_load": 0,
            },
        }
        if overrides:
            data.update(overrides)
        return data
    return _create_agent_data
