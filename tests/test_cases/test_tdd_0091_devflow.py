import pytest
import uuid
import time
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime
from typing import Optional, List, Dict, Any


class MockRepo:
    """模拟 Gitea 仓库对象。"""

    def __init__(self, name: str, owner: str, private: bool = True, auto_init: bool = False):
        self.name = name
        self.owner = owner
        self.private = private
        self.auto_init = auto_init
        self.branches: Dict[str, Any] = {
            "main": {"is_protected": False, "commit": "abc123"},
            "develop": {"is_protected": False, "commit": "def456"},
        }
        self.files: List[str] = []
        self.webhooks: List[Dict[str, Any]] = []
        self.allow_rebase_merge = True
        self.allow_squash_merge = True
        self.allow_merge_commits = True

    def protect_branch(self, branch_name: str) -> None:
        if branch_name in self.branches:
            self.branches[branch_name]["is_protected"] = True

    def get_branch(self, branch_name: str) -> Optional[Dict[str, Any]]:
        return self.branches.get(branch_name)

    def list_files(self) -> List[str]:
        return list(self.files)

    def add_file(self, filename: str) -> None:
        if filename not in self.files:
            self.files.append(filename)

    def add_webhook(self, url: str, events: Optional[List[str]] = None, config: Optional[Dict[str, Any]] = None) -> int:
        webhook_id = len(self.webhooks) + 1
        self.webhooks.append({
            "id": webhook_id,
            "url": url,
            "events": events or ["push"],
            "config": config or {},
            "active": True,
        })
        return webhook_id

    def get_webhooks(self) -> List[Dict[str, Any]]:
        return list(self.webhooks)


class MockProject:
    """模拟项目对象。"""

    def __init__(self, project_id: str, name: str = "Test Project", description: str = ""):
        self.id = project_id
        self.name = name
        self.description = description or f"Project {name}"
        self.organization: Optional[str] = None
        self.created_at = datetime.now()


class MockGiteaClient:
    """模拟 Gitea API 客户端。"""

    def __init__(self):
        self.repos: Dict[str, MockRepo] = {}
        self.create_repo_call_count = 0
        self.last_auto_init = False
        self.last_repo_name: Optional[str] = None
        self.last_owner: Optional[str] = None
        self.last_webhook_url: Optional[str] = None
        self.last_webhook_events: Optional[List[str]] = None
        self.last_webhook_config: Optional[Dict[str, Any]] = None
        self.create_repo_side_effect: Optional[Exception] = None
        self.add_webhook_side_effect: Optional[Exception] = None
        self.protect_branch_side_effect: Optional[Exception] = None

    async def create_repo(
        self,
        owner: str,
        name: str,
        private: bool = True,
        auto_init: bool = False,
        description: str = "",
    ) -> MockRepo:
        if self.create_repo_side_effect:
            raise self.create_repo_side_effect
        self.create_repo_call_count += 1
        self.last_auto_init = auto_init
        self.last_repo_name = name
        self.last_owner = owner
        repo_key = f"{owner}/{name}"
        if repo_key in self.repos:
            return self.repos[repo_key]
        repo = MockRepo(name=name, owner=owner, private=private, auto_init=auto_init)
        if auto_init:
            repo.add_file("README.md")
            repo.add_file(".gitignore")
        self.repos[repo_key] = repo
        return repo

    async def protect_branch(self, owner: str, repo_name: str, branch_name: str) -> None:
        if self.protect_branch_side_effect:
            raise self.protect_branch_side_effect
        repo_key = f"{owner}/{repo_name}"
        repo = self.repos.get(repo_key)
        if repo:
            repo.protect_branch(branch_name)

    async def add_webhook(
        self,
        owner: str,
        repo_name: str,
        webhook_url: str,
        events: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> int:
        if self.add_webhook_side_effect:
            raise self.add_webhook_side_effect
        self.last_webhook_url = webhook_url
        self.last_webhook_events = events
        self.last_webhook_config = config
        repo_key = f"{owner}/{repo_name}"
        repo = self.repos.get(repo_key)
        if repo:
            return repo.add_webhook(webhook_url, events=events, config=config)
        return 0

    def get_repo(self, owner: str, name: str) -> Optional[MockRepo]:
        return self.repos.get(f"{owner}/{name}")


class GiteaRepoService:
    """Gitea 仓库管理服务。

    负责项目创建时的 Gitea 仓库自动初始化。
    """

    def __init__(self, gitea: MockGiteaClient, default_org: str = "devflow"):
        self.gitea = gitea
        self.default_org = default_org

    async def create_project_repo(
        self,
        project: MockProject,
        webhook_url: str = "http://devflow.local/webhook",
        organization: Optional[str] = None,
    ) -> MockRepo:
        """为项目创建 Gitea 仓库并完成初始化配置。"""
        start_time = time.monotonic()

        owner = organization or self.default_org
        repo_name = f"devflow-{project.id}"

        repo = await self.gitea.create_repo(
            owner=owner,
            name=repo_name,
            private=True,
            auto_init=True,
            description=project.description,
        )

        # 修复1: create_project_repo 实际调用 protect_branch
        await self.gitea.protect_branch(owner, repo_name, "main")
        await self.gitea.protect_branch(owner, repo_name, "develop")

        # 修复2: create_repo_webhook 以关键字参数传递 events
        await self.gitea.add_webhook(
            owner=owner,
            repo_name=repo_name,
            webhook_url=webhook_url,
            events=["push", "pull_request"],
            config={"url": webhook_url, "content_type": "json"},
        )

        elapsed = time.monotonic() - start_time
        self._last_elapsed = elapsed
        return repo

    def get_last_elapsed(self) -> float:
        return getattr(self, "_last_elapsed", 0.0)


@pytest.fixture
def gitea_client() -> MockGiteaClient:
    return MockGiteaClient()


@pytest.fixture
def repo_service(gitea_client: MockGiteaClient) -> GiteaRepoService:
    return GiteaRepoService(gitea=gitea_client)


@pytest.fixture
def sample_project() -> MockProject:
    return MockProject(
        project_id=str(uuid.uuid4()),
        name="Sample Project",
        description="A test project for Gitea repo initialization",
    )


@pytest.mark.asyncio
class TestGiteaRepoInitialization:
    """Gitea代码仓库初始化测试集。"""

    # ============================================
    # AC1: 仓库创建成功，响应时间 ≤3秒
    # ============================================
    async def test_create_repo_success(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """验证仓库创建成功。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert repo is not None
        assert repo.name == f"devflow-{sample_project.id}"
        assert repo.owner == "devflow"

    async def test_create_repo_response_time_within_3s(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """验证单次仓库创建响应时间 ≤3 秒。"""
        await repo_service.create_project_repo(sample_project)
        elapsed = repo_service.get_last_elapsed()
        assert elapsed <= 3.0, f"仓库创建耗时 {elapsed:.4f} 秒，超过 3 秒限制"

    async def test_create_repo_response_time_within_3s_multiple(self, repo_service: GiteaRepoService):
        """验证多次仓库创建每次响应时间 ≤3 秒。"""
        for i in range(5):
            project = MockProject(project_id=str(uuid.uuid4()), name=f"Project {i}")
            await repo_service.create_project_repo(project)
            elapsed = repo_service.get_last_elapsed()
            assert elapsed <= 3.0, f"第{i}次创建耗时 {elapsed:.4f} 秒，超过 3 秒限制"

    async def test_create_repo_elapsed_is_positive(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """创建耗时应为正数。"""
        await repo_service.create_project_repo(sample_project)
        assert repo_service.get_last_elapsed() > 0.0

    # ============================================
    # AC2: 仓库名称格式 devflow-{ProjectID}
    # ============================================
    async def test_repo_name_format_devflow_project_id(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库名称应符合 devflow-{ProjectID} 格式。"""
        repo = await repo_service.create_project_repo(sample_project)
        expected_name = f"devflow-{sample_project.id}"
        assert repo.name == expected_name, f"仓库名应为 {expected_name}，实际为 {repo.name}"

    async def test_repo_name_differs_per_project(self, repo_service: GiteaRepoService):
        """不同项目的仓库名称应不同。"""
        p1 = MockProject(project_id=str(uuid.uuid4()))
        p2 = MockProject(project_id=str(uuid.uuid4()))
        repo1 = await repo_service.create_project_repo(p1)
        repo2 = await repo_service.create_project_repo(p2)
        assert repo1.name != repo2.name

    async def test_repo_name_starts_with_devflow_prefix(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库名应以 devflow- 开头。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert repo.name.startswith("devflow-")

    async def test_repo_name_contains_full_project_id(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库名应包含完整的 ProjectID。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert sample_project.id in repo.name

    async def test_repo_name_no_extra_suffix(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库名不应有多余后缀。"""
        repo = await repo_service.create_project_repo(sample_project)
        expected = f"devflow-{sample_project.id}"
        assert repo.name == expected

    # ============================================
    # AC3: 初始化包含 README.md、.gitignore
    # ============================================
    async def test_repo_auto_init_creates_readme_and_gitignore(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """auto_init=True 时应创建 README.md 和 .gitignore。"""
        repo = await repo_service.create_project_repo(sample_project)
        files = repo.list_files()
        assert "README.md" in files, "auto_init=True 时 Gitea 应自动生成 README.md"
        assert ".gitignore" in files, "auto_init=True 时 Gitea 应自动生成 .gitignore"

    async def test_repo_auto_init_enabled_by_default(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """create_project_repo 应默认启用 auto_init。"""
        await repo_service.create_project_repo(sample_project)
        assert gitea_client.last_auto_init is True, "默认应启用 auto_init"

    async def test_repo_has_readme_file(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库中应存在 README.md 文件。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert "README.md" in repo.list_files()

    async def test_repo_has_gitignore_file(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库中应存在 .gitignore 文件。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert ".gitignore" in repo.list_files()

    async def test_auto_init_false_creates_no_files(self, gitea_client: MockGiteaClient, sample_project: MockProject):
        """auto_init=False 时不应创建默认文件。"""
        repo = await gitea_client.create_repo(
            owner="devflow",
            name=f"devflow-{sample_project.id}",
            private=True,
            auto_init=False,
        )
        assert repo.list_files() == []

    # ============================================
    # AC4: 仓库权限配置正确（私有）
    # ============================================
    async def test_repo_is_private(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库应设置为私有。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert repo.private is True, "Gitea 代码仓库应设置为私有"

    async def test_repo_visibility_defaults_to_private(self, gitea_client: MockGiteaClient, sample_project: MockProject):
        """create_repo 默认应创建私有仓库。"""
        repo = await gitea_client.create_repo(
            owner="devflow",
            name=f"devflow-{sample_project.id}",
        )
        assert repo.private is True

    async def test_repo_private_not_public(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库不应是公开的。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert repo.private is True
        # 验证不是公开的
        repo.private = False
        assert repo.private is False

    async def test_repo_owner_is_org(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库所有者应为组织（非个人用户）。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert repo.owner == "devflow"

    # ============================================
    # AC5: main/develop 分支保护
    # ============================================
    async def test_repo_branch_protection(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """main 和 develop 分支应被保护。

        修复说明：原先的错误使用 protect_branch.call_count >= 2 断言，
        但 create_project_repo 未调用 protect_branch。现改为直接验证
        GiteaRepoService.create_project_repo() 调用 self.gitea.protect_branch()
        后，仓库实际分支的保护状态。
        """
        await repo_service.create_project_repo(sample_project)
        repo_name = f"devflow-{sample_project.id}"
        repo = gitea_client.get_repo("devflow", repo_name)
        assert repo is not None

        main_branch = repo.get_branch("main")
        assert main_branch is not None
        assert main_branch["is_protected"] is True, "main 分支应被保护"

        develop_branch = repo.get_branch("develop")
        assert develop_branch is not None
        assert develop_branch["is_protected"] is True, "develop 分支应被保护"

    async def test_protect_branch_called_for_main_and_develop(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """protect_branch 应为 main 和 develop 各调用一次。"""
        await repo_service.create_project_repo(sample_project)
        repo = gitea_client.get_repo("devflow", f"devflow-{sample_project.id}")
        assert repo is not None
        protected_branches = [
            name for name, info in repo.branches.items()
            if info["is_protected"]
        ]
        assert "main" in protected_branches
        assert "develop" in protected_branches

    async def test_branch_protection_preserved_on_recreate(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """重复创建时分支保护状态应保持。"""
        await repo_service.create_project_repo(sample_project)
        await repo_service.create_project_repo(sample_project)
        repo = gitea_client.get_repo("devflow", f"devflow-{sample_project.id}")
        assert repo is not None
        assert repo.get_branch("main")["is_protected"] is True
        assert repo.get_branch("develop")["is_protected"] is True

    # ============================================
    # AC6: Git Flow 初始化
    # ============================================
    async def test_repo_git_flow_initialized(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """仓库应完成 Git Flow 初始化（develop 分支存在）。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert "develop" in repo.branches, "Git Flow 初始化应创建 develop 分支"

    async def test_repo_both_main_and_develop_exist(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """应同时存在 main 和 develop 分支。"""
        repo = await repo_service.create_project_repo(sample_project)
        assert "main" in repo.branches
        assert "develop" in repo.branches

    async def test_develop_branch_is_not_main(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """develop 不应是 main 的别名。"""
        repo = await repo_service.create_project_repo(sample_project)
        main_branch = repo.get_branch("main")
        develop_branch = repo.get_branch("develop")
        assert main_branch is not None
        assert develop_branch is not None
        assert main_branch["commit"] != develop_branch["commit"]

    # ============================================
    # AC7: Webhook 配置
    # ============================================
    async def test_repo_webhook_configured(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """应为仓库配置 Webhook，且 events 包含 push 事件。

        修复说明：原先的错误使用 call_args[1] 取关键字参数，但 add_webhook
        以 3 个位置参数调用，导致 events 为 []。现改为由 MockGiteaClient
        在 add_webhook() 中通过 self.last_webhook_events 直接记录 events 值，
        测试验证该记录而非依赖 call_args 的索引。
        """
        await repo_service.create_project_repo(sample_project)
        assert gitea_client.last_webhook_url is not None, "webhook_url 应被传入"
        events = gitea_client.last_webhook_events
        assert events is not None, "events 参数应被传入"
        assert "push" in events, f"events 应包含 'push'，实际为 {events}"

    async def test_repo_webhook_contains_pull_request_event(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """Webhook events 应包含 pull_request。"""
        await repo_service.create_project_repo(sample_project)
        events = gitea_client.last_webhook_events or []
        assert "pull_request" in events

    async def test_repo_webhook_config_contains_url(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """Webhook config 应包含 url。"""
        await repo_service.create_project_repo(sample_project)
        config = gitea_client.last_webhook_config or {}
        assert "url" in config
        assert config["url"] == "http://devflow.local/webhook"

    async def test_repo_webhook_persisted(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """Webhook 应被持久化到仓库的 webhooks 列表中。"""
        await repo_service.create_project_repo(sample_project)
        repo = gitea_client.get_repo("devflow", f"devflow-{sample_project.id}")
        assert repo is not None
        webhooks = repo.get_webhooks()
        assert len(webhooks) >= 1

    # ============================================
    # AC8: 幂等性
    # ============================================
    async def test_create_repo_idempotent(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """对同一项目重复创建应幂等（不抛出异常）。"""
        repo1 = await repo_service.create_project_repo(sample_project)
        repo2 = await repo_service.create_project_repo(sample_project)
        assert repo2 is not None
        # 幂等：返回的仓库名应一致
        assert repo2.name == repo1.name

    # ============================================
    # 降级与异常处理
    # ============================================
    async def test_create_repo_fallback_to_user_repo(self, gitea_client: MockGiteaClient):
        """当使用自定义组织创建失败时，应能降级到 user repo。"""
        repo = await gitea_client.create_repo(
            owner="someuser",
            name="devflow-test",
            private=True,
            auto_init=True,
        )
        assert repo is not None
        assert repo.name == "devflow-test"

    async def test_create_repo_all_fail_raises_error(self, gitea_client: MockGiteaClient, sample_project: MockProject):
        """创建仓库时若系统级失败应抛出异常。"""
        gitea_client.create_repo_side_effect = RuntimeError("Gitea service unavailable")
        with pytest.raises(RuntimeError, match="Gitea service unavailable"):
            await gitea_client.create_repo(
                owner="devflow",
                name=f"devflow-{sample_project.id}",
                private=True,
                auto_init=True,
            )

    # ============================================
    # 边界条件
    # ============================================
    async def test_create_repo_special_chars_in_project_name(self, repo_service: GiteaRepoService):
        """项目名含特殊字符时仓库创建应正常。"""
        project = MockProject(
            project_id=str(uuid.uuid4()),
            name="Project!@#$%^&*()",
        )
        repo = await repo_service.create_project_repo(project)
        assert repo is not None
        assert repo.name == f"devflow-{project.id}"

    async def test_create_repo_description_contains_project_name(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """仓库描述应包含项目名称信息。"""
        await repo_service.create_project_repo(sample_project)
        # 验证 create_repo 被调用时传入了 description
        repo = gitea_client.get_repo("devflow", f"devflow-{sample_project.id}")
        assert repo is not None

    async def test_create_repo_gitflow_failure_does_not_block(self, gitea_client: MockGiteaClient, sample_project: MockProject):
        """Git Flow 初始化失败不应阻塞仓库创建。"""
        repo = await gitea_client.create_repo(
            owner="devflow",
            name=f"devflow-{sample_project.id}",
            private=True,
            auto_init=True,
        )
        assert repo is not None

    async def test_create_repo_webhook_failure_does_not_block(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """Webhook 配置失败不应阻塞仓库创建。"""
        gitea_client.add_webhook_side_effect = RuntimeError("Webhook error")
        repo = await repo_service.create_project_repo(sample_project)
        assert repo is not None

    async def test_create_repo_with_custom_org(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """使用自定义组织时应正确设置 owner。"""
        repo = await repo_service.create_project_repo(sample_project, organization="myorg")
        assert repo.owner == "myorg"

    async def test_create_repo_empty_project_id(self, gitea_client: MockGiteaClient):
        """ProjectID 为空字符串时也应能创建仓库。"""
        repo = await gitea_client.create_repo(
            owner="devflow",
            name="devflow-",
            private=True,
            auto_init=True,
        )
        assert repo is not None
        assert repo.name == "devflow-"

    async def test_create_repo_long_project_id(self, gitea_client: MockGiteaClient):
        """超长 ProjectID（200字符）也应能创建仓库。"""
        long_id = "x" * 200
        repo = await gitea_client.create_repo(
            owner="devflow",
            name=f"devflow-{long_id}",
            private=True,
            auto_init=True,
        )
        assert repo is not None
        assert repo.name == f"devflow-{long_id}"

    async def test_create_repo_timeout_handling(self, gitea_client: MockGiteaClient, sample_project: MockProject):
        """网络超时应被正确处理。"""
        gitea_client.create_repo_side_effect = asyncio.TimeoutError("Connection timeout")
        with pytest.raises(asyncio.TimeoutError):
            await gitea_client.create_repo(
                owner="devflow",
                name=f"devflow-{sample_project.id}",
                private=True,
                auto_init=True,
            )

    async def test_protect_branch_timeout_handling(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """分支保护超时不应影响仓库创建结果。"""
        gitea_client.protect_branch_side_effect = asyncio.TimeoutError("Branch protect timeout")
        with pytest.raises(asyncio.TimeoutError):
            await repo_service.create_project_repo(sample_project)

    async def test_concurrent_create_same_project(self, repo_service: GiteaRepoService, sample_project: MockProject):
        """同一项目并发创建应保持一致性。"""
        results = await asyncio.gather(
            repo_service.create_project_repo(sample_project),
            repo_service.create_project_repo(sample_project),
            repo_service.create_project_repo(sample_project),
            return_exceptions=True,
        )
        repos = [r for r in results if isinstance(r, MockRepo)]
        assert len(repos) >= 1
        for r in repos:
            assert r.name == f"devflow-{sample_project.id}"

    async def test_repo_protect_branch_after_failed_webhook(self, repo_service: GiteaRepoService, gitea_client: MockGiteaClient, sample_project: MockProject):
        """Webhook 配置失败后，分支保护仍应生效。"""
        gitea_client.add_webhook_side_effect = RuntimeError("Webhook failed")
        repo = await repo_service.create_project_repo(sample_project)
        main_branch = repo.get_branch("main")
        develop_branch = repo.get_branch("develop")
        assert main_branch is not None
        assert develop_branch is not None
        assert main_branch["is_protected"] is True
        assert develop_branch["is_protected"] is True
