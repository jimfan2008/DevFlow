import pytest
from datetime import datetime, timedelta


# ── Mock Data & Classes ──────────────────────────────────────────────

class AgentStatus:
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"

    ALL = [IDLE, RUNNING, WAITING, ERROR]
    LABELS = {
        IDLE: "空闲",
        RUNNING: "执行中",
        WAITING: "等待中",
        ERROR: "异常",
    }


class MockAgent:
    def __init__(self, name: str, status: str, current_task: str = "", progress: float = 0.0):
        self.name = name
        self.status = status
        self.current_task = current_task
        self.progress = max(0.0, min(100.0, progress))
        self.last_heartbeat = datetime.now() - timedelta(seconds=5)


class MockProject:
    def __init__(self, project_id: str, name: str, status: str = "running", agents=None):
        self.project_id = project_id
        self.name = name
        self.status = status
        self.agents = agents or []


class MockDataStore:
    """模拟后端数据源，提供项目和 Agent 数据"""

    def __init__(self):
        self._projects = []
        self._agents = []

    def add_project(self, project: MockProject):
        self._projects.append(project)

    def add_agent(self, agent: MockAgent):
        self._agents.append(agent)
        # 自动关联到第一个项目
        if self._projects:
            self._projects[0].agents.append(agent)

    def get_running_projects(self):
        return [p for p in self._projects if p.status == "running"]

    def get_all_agents(self):
        return self._agents

    def get_agents_by_status(self, status: str):
        return [a for a in self._agents if a.status == status]


class ProjectMonitoringDashboard:
    """项目级监控面板核心逻辑"""

    def __init__(self, data_store: MockDataStore):
        self._store = data_store

    def get_running_project_count(self) -> int:
        return len(self._store.get_running_projects())

    def get_agent_status_summary(self) -> dict:
        """返回各状态的 Agent 数量统计"""
        summary = {}
        for status in AgentStatus.ALL:
            agents = self._store.get_agents_by_status(status)
            summary[status] = {
                "label": AgentStatus.LABELS[status],
                "count": len(agents),
                "agents": agents,
            }
        return summary

    def get_progress_distribution(self) -> dict:
        """返回 Agent 流程进度分布"""
        buckets = {
            "0-25%": [],
            "25-50%": [],
            "50-75%": [],
            "75-100%": [],
        }
        for agent in self._store.get_all_agents():
            p = agent.progress
            if p <= 25.0:
                buckets["0-25%"].append(agent)
            elif p <= 50.0:
                buckets["25-50%"].append(agent)
            elif p <= 75.0:
                buckets["50-75%"].append(agent)
            else:
                buckets["75-100%"].append(agent)
        return {k: len(v) for k, v in buckets.items()}

    def get_dashboard_data(self) -> dict:
        """聚合所有面板数据"""
        return {
            "running_projects_count": self.get_running_project_count(),
            "running_projects": [
                {"id": p.project_id, "name": p.name}
                for p in self._store.get_running_projects()
            ],
            "agent_status_summary": {
                k: {"label": v["label"], "count": v["count"]}
                for k, v in self.get_agent_status_summary().items()
            },
            "progress_distribution": self.get_progress_distribution(),
        }


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def data_store_with_projects():
    """创建包含 3 个运行中项目的数据源"""
    store = MockDataStore()
    store.add_project(MockProject("proj-001", "电商平台重构", status="running"))
    store.add_project(MockProject("proj-002", "数据分析平台", status="running"))
    store.add_project(MockProject("proj-003", "移动端 App", status="stopped"))
    return store


@pytest.fixture
def data_store_with_agents():
    """创建包含多种状态 Agent 的数据源"""
    store = MockDataStore()
    store.add_project(MockProject("proj-001", "测试项目", status="running"))

    # 空闲 Agent
    store.add_agent(MockAgent("agent-alpha", AgentStatus.IDLE))
    store.add_agent(MockAgent("agent-beta", AgentStatus.IDLE))

    # 执行中 Agent
    store.add_agent(MockAgent("agent-gamma", AgentStatus.RUNNING, "数据迁移", 65.0))
    store.add_agent(MockAgent("agent-delta", AgentStatus.RUNNING, "接口测试", 30.0))
    store.add_agent(MockAgent("agent-epsilon", AgentStatus.RUNNING, "代码审查", 90.0))

    # 等待中 Agent
    store.add_agent(MockAgent("agent-zeta", AgentStatus.WAITING, "等待审批", 45.0))

    # 异常 Agent
    store.add_agent(MockAgent("agent-eta", AgentStatus.ERROR, "模型推理", 10.0))
    store.add_agent(MockAgent("agent-theta", AgentStatus.ERROR, "数据清洗", 0.0))

    return store


@pytest.fixture
def full_data_store():
    """包含完整数据和多项目多 Agent 的数据源"""
    store = MockDataStore()

    projects = [
        MockProject("proj-001", "电商平台重构", status="running"),
        MockProject("proj-002", "数据分析平台", status="running"),
        MockProject("proj-003", "用户增长系统", status="running"),
        MockProject("proj-004", "旧系统维护", status="stopped"),
    ]
    for p in projects:
        store.add_project(p)

    agents = [
        MockAgent("architect-01", AgentStatus.RUNNING, "需求分析", 80.0),
        MockAgent("coder-01", AgentStatus.RUNNING, "功能开发", 45.0),
        MockAgent("coder-02", AgentStatus.RUNNING, "单元测试", 60.0),
        MockAgent("tester-01", AgentStatus.WAITING, "集成测试", 35.0),
        MockAgent("reviewer-01", AgentStatus.IDLE),
        MockAgent("deployer-01", AgentStatus.ERROR, "部署发布", 95.0),
        MockAgent("monitor-01", AgentStatus.IDLE),
        MockAgent("optimizer-01", AgentStatus.RUNNING, "性能调优", 15.0),
    ]
    for a in agents:
        store.add_agent(a)

    return store


# ── Tests: 运行项目数量 ──────────────────────────────────────────────

class TestRunningProjectCount:

    def test_count_equals_projects_when_all_running(self, data_store_with_projects):
        dashboard = ProjectMonitoringDashboard(data_store_with_projects)
        count = dashboard.get_running_project_count()
        assert count == 2

    def test_count_greater_or_equal_two(self, full_data_store):
        """验收标准：显示当前运行项目数量（≥2）"""
        dashboard = ProjectMonitoringDashboard(full_data_store)
        count = dashboard.get_running_project_count()
        assert count >= 2

    def test_count_excludes_stopped_projects(self, data_store_with_projects):
        dashboard = ProjectMonitoringDashboard(data_store_with_projects)
        count = dashboard.get_running_project_count()
        total = len(data_store_with_projects._projects)
        assert count < total  # stopped 项目不应计入
        assert count == 2

    def test_count_is_zero_when_no_running_projects(self):
        store = MockDataStore()
        store.add_project(MockProject("p1", "A", status="stopped"))
        store.add_project(MockProject("p2", "B", status="stopped"))
        dashboard = ProjectMonitoringDashboard(store)
        assert dashboard.get_running_project_count() == 0

    def test_dashboard_data_includes_running_project_details(self, full_data_store):
        dashboard = ProjectMonitoringDashboard(full_data_store)
        data = dashboard.get_dashboard_data()
        assert "running_projects" in data
        assert isinstance(data["running_projects"], list)
        for proj in data["running_projects"]:
            assert "id" in proj
            assert "name" in proj


# ── Tests: Agent 执行状态 ───────────────────────────────────────────

class TestAgentExecutionStatus:

    def test_summary_contains_all_statuses(self, data_store_with_agents):
        """验收标准：展示各 Agent 执行状态（空闲/执行中/等待中/异常）"""
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        assert set(summary.keys()) == set(AgentStatus.ALL)

    def test_idle_agents_count(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        assert summary[AgentStatus.IDLE]["count"] == 2
        assert summary[AgentStatus.IDLE]["label"] == "空闲"

    def test_running_agents_count(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        assert summary[AgentStatus.RUNNING]["count"] == 3
        assert summary[AgentStatus.RUNNING]["label"] == "执行中"

    def test_waiting_agents_count(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        assert summary[AgentStatus.WAITING]["count"] == 1
        assert summary[AgentStatus.WAITING]["label"] == "等待中"

    def test_error_agents_count(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        assert summary[AgentStatus.ERROR]["count"] == 2
        assert summary[AgentStatus.ERROR]["label"] == "异常"

    def test_total_agents_matches_sum_of_statuses(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        total = sum(v["count"] for v in summary.values())
        all_agents = data_store_with_agents.get_all_agents()
        assert total == len(all_agents)

    def test_each_status_contains_correct_agents(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        running_agents = summary[AgentStatus.RUNNING]["agents"]
        for agent in running_agents:
            assert agent.status == AgentStatus.RUNNING
            assert agent.current_task != ""

    def test_dashboard_data_includes_status_summary(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        data = dashboard.get_dashboard_data()
        assert "agent_status_summary" in data
        summary = data["agent_status_summary"]
        for status in AgentStatus.ALL:
            assert status in summary
            assert "label" in summary[status]
            assert "count" in summary[status]


# ── Tests: 流程进度分布可视化 ───────────────────────────────────────

class TestProgressDistribution:

    def test_distribution_has_four_buckets(self, data_store_with_agents):
        """验收标准：流程进度分布可视化"""
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        dist = dashboard.get_progress_distribution()
        expected_keys = {"0-25%", "25-50%", "50-75%", "75-100%"}
        assert set(dist.keys()) == expected_keys

    def test_distribution_values_are_integers(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        dist = dashboard.get_progress_distribution()
        for bucket, count in dist.items():
            assert isinstance(count, int)
            assert count >= 0

    def test_distribution_total_equals_agent_count(self, data_store_with_agents):
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        dist = dashboard.get_progress_distribution()
        total = sum(dist.values())
        all_agents = data_store_with_agents.get_all_agents()
        assert total == len(all_agents)

    def test_agents_at_zero_progress_fall_in_first_bucket(self, data_store_with_agents):
        """progress=0 的 Agent 应归入 0-25% 桶"""
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        dist = dashboard.get_progress_distribution()
        # agent-theta progress=0.0, agent-eta progress=10.0, agent-optimizer-01 progress=15.0
        # 至少有 2 个在 0-25%
        assert dist["0-25%"] >= 2

    def test_agents_at_hundred_percent_fall_in_last_bucket(self):
        store = MockDataStore()
        store.add_project(MockProject("p1", "Test", status="running"))
        store.add_agent(MockAgent("a1", AgentStatus.RUNNING, "done", 100.0))
        store.add_agent(MockAgent("a2", AgentStatus.RUNNING, "almost", 99.9))
        dashboard = ProjectMonitoringDashboard(store)
        dist = dashboard.get_progress_distribution()
        assert dist["75-100%"] == 2

    def test_boundary_value_at_25_goes_to_first_bucket(self):
        """边界值：progress=25.0 应归入 0-25%"""
        store = MockDataStore()
        store.add_project(MockProject("p1", "Test", status="running"))
        store.add_agent(MockAgent("a1", AgentStatus.RUNNING, "boundary", 25.0))
        store.add_agent(MockAgent("a2", AgentStatus.RUNNING, "just_over", 25.1))
        dashboard = ProjectMonitoringDashboard(store)
        dist = dashboard.get_progress_distribution()
        assert dist["0-25%"] == 1
        assert dist["25-50%"] == 1

    def test_boundary_value_at_50_goes_to_second_bucket(self):
        """边界值：progress=50.0 应归入 25-50%"""
        store = MockDataStore()
        store.add_project(MockProject("p1", "Test", status="running"))
        store.add_agent(MockAgent("a1", AgentStatus.RUNNING, "boundary", 50.0))
        dashboard = ProjectMonitoringDashboard(store)
        dist = dashboard.get_progress_distribution()
        assert dist["25-50%"] == 1

    def test_boundary_value_at_75_goes_to_third_bucket(self):
        """边界值：progress=75.0 应归入 50-75%"""
        store = MockDataStore()
        store.add_project(MockProject("p1", "Test", status="running"))
        store.add_agent(MockAgent("a1", AgentStatus.RUNNING, "boundary", 75.0))
        dashboard = ProjectMonitoringDashboard(store)
        dist = dashboard.get_progress_distribution()
        assert dist["50-75%"] == 1

    def test_distribution_empty_when_no_agents(self):
        store = MockDataStore()
        dashboard = ProjectMonitoringDashboard(store)
        dist = dashboard.get_progress_distribution()
        for bucket, count in dist.items():
            assert count == 0


# ── Tests: 完整面板数据聚合 ─────────────────────────────────────────

class TestDashboardDataAggregation:

    def test_dashboard_data_has_all_required_keys(self, full_data_store):
        dashboard = ProjectMonitoringDashboard(full_data_store)
        data = dashboard.get_dashboard_data()
        required_keys = {
            "running_projects_count",
            "running_projects",
            "agent_status_summary",
            "progress_distribution",
        }
        assert set(data.keys()) >= required_keys

    def test_running_projects_count_matches_projects_list_length(self, full_data_store):
        dashboard = ProjectMonitoringDashboard(full_data_store)
        data = dashboard.get_dashboard_data()
        assert data["running_projects_count"] == len(data["running_projects"])

    def test_dashboard_data_is_consistent(self, full_data_store):
        dashboard = ProjectMonitoringDashboard(full_data_store)
        data = dashboard.get_dashboard_data()
        # 项目数 ≥ 2
        assert data["running_projects_count"] >= 2
        # Agent 状态总和 = Agent 总数
        agent_total = sum(
            v["count"] for v in data["agent_status_summary"].values()
        )
        assert agent_total == len(full_data_store.get_all_agents())
        # 进度分布总和 = Agent 总数
        progress_total = sum(data["progress_distribution"].values())
        assert progress_total == agent_total

    def test_dashboard_data_types(self, full_data_store):
        dashboard = ProjectMonitoringDashboard(full_data_store)
        data = dashboard.get_dashboard_data()
        assert isinstance(data["running_projects_count"], int)
        assert isinstance(data["running_projects"], list)
        assert isinstance(data["agent_status_summary"], dict)
        assert isinstance(data["progress_distribution"], dict)


# ── Tests: 边界与异常场景 ───────────────────────────────────────────

class TestEdgeCases:

    def test_empty_store(self):
        store = MockDataStore()
        dashboard = ProjectMonitoringDashboard(store)
        data = dashboard.get_dashboard_data()
        assert data["running_projects_count"] == 0
        assert data["running_projects"] == []
        for status in AgentStatus.ALL:
            assert data["agent_status_summary"][status]["count"] == 0
        for bucket in data["progress_distribution"]:
            assert data["progress_distribution"][bucket] == 0

    def test_all_agents_in_same_status(self):
        store = MockDataStore()
        store.add_project(MockProject("p1", "Test", status="running"))
        for i in range(5):
            store.add_agent(MockAgent(f"agent-{i}", AgentStatus.IDLE))
        dashboard = ProjectMonitoringDashboard(store)
        summary = dashboard.get_agent_status_summary()
        assert summary[AgentStatus.IDLE]["count"] == 5
        for status in AgentStatus.ALL:
            if status != AgentStatus.IDLE:
                assert summary[status]["count"] == 0

    def test_single_running_project_still_valid(self):
        store = MockDataStore()
        store.add_project(MockProject("p1", "Solo", status="running"))
        store.add_agent(MockAgent("solo-agent", AgentStatus.RUNNING, "working", 50.0))
        dashboard = ProjectMonitoringDashboard(store)
        assert dashboard.get_running_project_count() == 1
        data = dashboard.get_dashboard_data()
        assert len(data["running_projects"]) == 1
        assert data["running_projects"][0]["name"] == "Solo"

    def test_agent_progress_clamped_to_valid_range(self):
        """Agent progress 超出 0-100 范围时应被钳制"""
        a1 = MockAgent("a1", AgentStatus.RUNNING, "x", -10.0)
        assert a1.progress == 0.0
        a2 = MockAgent("a2", AgentStatus.RUNNING, "y", 200.0)
        assert a2.progress == 100.0

    def test_agent_labels_are_chinese(self, data_store_with_agents):
        """状态标签必须为中文"""
        dashboard = ProjectMonitoringDashboard(data_store_with_agents)
        summary = dashboard.get_agent_status_summary()
        expected_labels = {"空闲", "执行中", "等待中", "异常"}
        actual_labels = {v["label"] for v in summary.values()}
        assert actual_labels == expected_labels
