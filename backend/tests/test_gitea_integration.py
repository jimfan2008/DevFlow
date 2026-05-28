import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch

from app.database import Base
from app.models.user import User
from app.models.project import Project
from app.models.agent import Agent
from app.models.task import Task
from app.models.group import Group
from app.models.enums import ProjectStatus, GroupMode
from app.services.gitea_client import GiteaClient, CONVENTIONAL_COMMIT_PATTERN
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


class TestGiteaRepoCreation:
    @pytest.mark.asyncio
    async def test_create_org_repo(self):
        client = GiteaClient()
        mock_response = {"id": 1, "name": "test-repo", "html_url": "http://gitea:3000/org/test-repo"}
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            result = await client.create_org_repo("org", "test-repo", "test description")
            assert result["name"] == "test-repo"

    @pytest.mark.asyncio
    async def test_create_user_repo(self):
        client = GiteaClient()
        mock_response = {"id": 2, "name": "user-repo", "html_url": "http://gitea:3000/user/user-repo"}
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            result = await client.create_user_repo("user", "user-repo", "user description")
            assert result["name"] == "user-repo"


class TestGiteaBranchManagement:
    @pytest.mark.asyncio
    async def test_list_branches(self):
        client = GiteaClient()
        mock_response = [{"name": "main"}, {"name": "develop"}]
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            branches = await client.list_branches("owner", "repo")
            assert len(branches) == 2
            assert branches[0]["name"] == "main"

    @pytest.mark.asyncio
    async def test_create_branch(self):
        client = GiteaClient()
        mock_response = {"name": "feature/login"}
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            result = await client.create_branch("owner", "repo", "feature/login", "develop")
            assert result["name"] == "feature/login"

    @pytest.mark.asyncio
    async def test_init_git_flow(self):
        client = GiteaClient()
        with patch.object(client, 'list_branches', new_callable=AsyncMock, return_value=[{"name": "main"}]):
            with patch.object(client, 'create_branch', new_callable=AsyncMock, return_value={"name": "develop"}):
                with patch.object(client, 'protect_branch', new_callable=AsyncMock, return_value={}):
                    result = await client.init_git_flow("owner", "repo")
                    assert result["main"] == "protected"
                    assert result["develop"] == "created_and_protected"


class TestGiteaPRFlow:
    @pytest.mark.asyncio
    async def test_create_pr(self):
        client = GiteaClient()
        mock_response = {"number": 1, "title": "Feature PR", "state": "open"}
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            result = await client.create_pr("owner", "repo", "Feature PR", "feature/x", "develop")
            assert result["number"] == 1

    @pytest.mark.asyncio
    async def test_merge_pr(self):
        client = GiteaClient()
        mock_response = {}
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            result = await client.merge_pr("owner", "repo", 1)
            assert result is not None

    @pytest.mark.asyncio
    async def test_list_prs(self):
        client = GiteaClient()
        mock_response = [{"number": 1, "state": "open"}, {"number": 2, "state": "merged"}]
        with patch.object(client, '_request', new_callable=AsyncMock, return_value=mock_response):
            prs = await client.list_prs("owner", "repo")
            assert len(prs) == 2


class TestConventionalCommitValidation:
    def test_valid_commits(self):
        valid_messages = [
            "feat: add user login",
            "fix(auth): resolve token refresh issue",
            "docs: update API documentation",
            "refactor(core): simplify config loading",
            "test: add unit tests for auth service",
            "chore: update dependencies",
        ]
        for msg in valid_messages:
            assert CONVENTIONAL_COMMIT_PATTERN.match(msg) is not None, f"Should match: {msg}"

    def test_invalid_commits(self):
        invalid_messages = [
            "add feature",
            "fix",
            "feat:",
            "random commit message",
            "feat:add login",
        ]
        for msg in invalid_messages:
            assert CONVENTIONAL_COMMIT_PATTERN.match(msg) is None, f"Should not match: {msg}"

    @pytest.mark.asyncio
    async def test_validate_conventional_commit(self):
        client = GiteaClient()
        mock_commits = [
            {"sha": "abc123", "commit": {"message": "feat: add login"}},
            {"sha": "def456", "commit": {"message": "fix: resolve bug"}},
            {"sha": "ghi789", "commit": {"message": "invalid commit msg"}},
        ]
        with patch.object(client, 'list_commits', new_callable=AsyncMock, return_value=mock_commits):
            result = await client.validate_conventional_commit("owner", "repo")
            assert result["valid"] is False
            assert len(result["invalid_commits"]) == 1
            assert result["invalid_commits"][0]["sha"] == "ghi789"

    @pytest.mark.asyncio
    async def test_validate_all_valid_commits(self):
        client = GiteaClient()
        mock_commits = [
            {"sha": "abc123", "commit": {"message": "feat: add login"}},
            {"sha": "def456", "commit": {"message": "fix: resolve bug"}},
        ]
        with patch.object(client, 'list_commits', new_callable=AsyncMock, return_value=mock_commits):
            result = await client.validate_conventional_commit("owner", "repo")
            assert result["valid"] is True
            assert len(result["invalid_commits"]) == 0
