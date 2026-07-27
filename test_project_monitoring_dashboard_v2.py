import pytest
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict


class AgentStatus(Enum):
    """Agent 执行状态"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"


class FlowStage(Enum):
    """流程阶段"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Agent:
    """Agent 信息"""
    name: str
    status: AgentStatus
    current_task: str = ""


@dataclass
class Project:
    """项目信息"""
    name: str
    is_running: bool
    agents: List[Agent] = field(default_factory=list)


@dataclass
class FlowProgress:
    """流程进度统计"""
    stage: FlowStage
    count: int


@dataclass
class DashboardData:
    """监控面板导出数据"""
    running_project_count: int
    agent_statuses: Dict[str, List[Agent]]
    flow_distribution: List[FlowProgress]


class ProjectMonitoringDashboard:
    """项目级监控面板"""

    def __init__(self, projects: List[Project], flow_distribution: List[FlowProgress]):
        self.projects = projects
        self.flow_distribution = flow_distribution

    def get_running_project_count(self) -> int:
        """获取当前运行中的项目数量"""
        return sum(1 for p in self.projects if p.is_running)

    def get_agent_statuses_by_project(self) -> Dict[str, List[Agent]]:
        """按项目分组的 Agent 执行状态"""
        result: Dict[str, List[Agent]] = {}
        for project in self.projects:
            result[project.name] = list(project.agents)
        return result

    def get_status_summary(self) -> Dict[str, int]:
        """所有 Agent 的状态汇总统计"""
        summary = {s.value: 0 for s in AgentStatus}
        for project in self.projects:
            for agent in project.agents:
                summary[agent.status.value] += 1
        return summary

    def get_flow_distribution(self) -> List[FlowProgress]:
        """流程进度分布"""
        return list(self.flow_distribution)

    def to_dashboard_data(self) -> DashboardData:
        """导出完整面板数据"""
        return DashboardData(
            running_project_count=self.get_running_project_count(),
            agent_statuses=self.get_agent_statuses_by_project(),
            flow_distribution=self.get_flow_distribution(),
        )


@pytest.fixture
def sample_projects():
    """构造测试项目数据：3个项目，其中2个运行中"""
    agents_alpha = [
        Agent(name="alpha-worker-1", status=AgentStatus.RUNNING, current_task="etl-pipeline"),
        Agent(name="alpha-worker-2", status=AgentStatus.IDLE),
        Agent(name="alpha-reviewer", status=AgentStatus.WAITING, current_task="pending-approval"),
    ]
    agents_beta = [
        Agent(name="beta-trainer", status=AgentStatus.ERROR, current_task="model-finetune"),
        Agent(name="beta-extractor", status=AgentStatus.RUNNING, current_task="feature-extract"),
    ]
    agents_gamma = [
        Agent(name="gamma-idle-1", status=AgentStatus.IDLE),
    ]

    return [
        Project(name="project-alpha", is_running=True, agents=agents_alpha),
        Project(name="project-beta", is_running=True, agents=agents_beta),
        Project(name="project-gamma", is_running=False, agents=agents_gamma),
    ]


@pytest.fixture
def sample_flow_distribution():
    """构造测试流程进度分布数据"""
    return [
        FlowProgress(stage=FlowStage.PENDING, count=5),
        FlowProgress(stage=FlowStage.IN_PROGRESS, count=3),
        FlowProgress(stage=FlowStage.COMPLETED, count=12),
        FlowProgress(stage=FlowStage.FAILED, count=1),
    ]


@pytest.fixture
def dashboard(sample_projects, sample_flow_distribution):
    """创建监控面板实例"""
    return ProjectMonitoringDashboard(sample_projects, sample_flow_distribution)


# =============================================================================
# 验收标准一：显示当前运行项目数量（≥2）
# =============================================================================

class TestRunningProjectCount:

    def test_running_count_at_least_two(self, dashboard):
        count = dashboard.get_running_project_count()
        assert count >= 2, f"运行项目数量应 >= 2，实际为 {count}"

    def test_running_count_exact(self, dashboard):
        count = dashboard.get_running_project_count()
        assert count == 2, f"预期运行项目数为 2，实际为 {count}"

    def test_dashboard_data_contains_running_count(self, dashboard):
        data = dashboard.to_dashboard_data()
        assert data.running_project_count == 2
        assert data.running_project_count >= 2

    def test_non_running_project_not_counted(self):
        """已停止的项目不应计入运行项目"""
        projects = [
            Project(name="p1", is_running=False),
            Project(name="p2", is_running=False),
            Project(name="p3", is_running=False),
        ]
        dist = []
        dashboard = ProjectMonitoringDashboard(projects, dist)
        assert dashboard.get_running_project_count() == 0

    def test_all_projects_running(self):
        """全部项目运行时计数正确"""
        projects = [
            Project(name="a", is_running=True),
            Project(name="b", is_running=True),
            Project(name="c", is_running=True),
        ]
        dashboard = ProjectMonitoringDashboard(projects, [])
        assert dashboard.get_running_project_count() == 3


# =============================================================================
# 验收标准二：展示各 Agent 执行状态（空闲/执行中/等待中/异常）
# =============================================================================

class TestAgentExecutionStatus:

    def test_all_four_status_types_present(self, dashboard):
        summary = dashboard.get_status_summary()
        expected_keys = {"idle", "running", "waiting", "error"}
        assert set(summary.keys()) == expected_keys, \
            f"状态键应为 {expected_keys}，实际为 {set(summary.keys())}"

    def test_idle_count_correct(self, dashboard):
        summary = dashboard.get_status_summary()
        assert summary["idle"] == 2

    def test_running_count_correct(self, dashboard):
        summary = dashboard.get_status_summary()
        assert summary["running"] == 2

    def test_waiting_count_correct(self, dashboard):
        summary = dashboard.get_status_summary()
        assert summary["waiting"] == 1

    def test_error_count_correct(self, dashboard):
        summary = dashboard.get_status_summary()
        assert summary["error"] == 1

    def test_agents_grouped_by_project(self, dashboard):
        statuses = dashboard.get_agent_statuses_by_project()
        assert len(statuses) == 3
        assert len(statuses["project-alpha"]) == 3
        assert len(statuses["project-beta"]) == 2
        assert len(statuses["project-gamma"]) == 1

    def test_each_agent_has_valid_status(self, dashboard):
        statuses = dashboard.get_agent_statuses_by_project()
        for project_name, agents in statuses.items():
            for agent in agents:
                assert agent.status in AgentStatus, \
                    f"Agent {agent.name} 状态 {agent.status} 不是有效枚举值"

    def test_error_agents_have_task_info(self, dashboard):
        """异常状态的 Agent 应带有任务信息"""
        statuses = dashboard.get_agent_statuses_by_project()
        error_agents = [
            a for agents in statuses.values()
            for a in agents if a.status == AgentStatus.ERROR
        ]
        assert len(error_agents) > 0
        for agent in error_agents:
            assert agent.current_task != "", \
                f"异常状态 Agent {agent.name} 应有任务信息"

    def test_at_least_one_idle_agent(self, dashboard):
        summary = dashboard.get_status_summary()
        assert summary["idle"] > 0, "应至少存在一个空闲 Agent"

    def test_at_least_one_running_agent(self, dashboard):
        summary = dashboard.get_status_summary()
        assert summary["running"] > 0, "应至少存在一个执行中 Agent"

    def test_status_summary_total_matches_agent_total(self, dashboard):
        """状态汇总的总数应等于 Agent 总数"""
        summary = dashboard.get_status_summary()
        statuses = dashboard.get_agent_statuses_by_project()
        summary_total = sum(summary.values())
        agent_total = sum(len(agents) for agents in statuses.values())
        assert summary_total == agent_total, \
            f"状态汇总总数 {summary_total} 应等于 Agent 总数 {agent_total}"


# =============================================================================
# 验收标准三：流程进度分布可视化
# =============================================================================

class TestFlowProgressDistribution:

    def test_distribution_covers_all_stages(self, dashboard):
        dist = dashboard.get_flow_distribution()
        stage_keys = {d.stage.value for d in dist}
        expected = {s.value for s in FlowStage}
        assert stage_keys == expected, \
            f"应包含所有阶段 {expected}，实际为 {stage_keys}"

    def test_each_stage_count_is_positive(self, dashboard):
        dist = dashboard.get_flow_distribution()
        for item in dist:
            assert item.count > 0, \
                f"阶段 {item.stage.value} 数量应 > 0，实际为 {item.count}"

    def test_total_flows_is_correct(self, dashboard):
        dist = dashboard.get_flow_distribution()
        total = sum(item.count for item in dist)
        assert total == 21, f"总流程数应为 21，实际为 {total}"

    def test_distribution_order_is_consistent(self, dashboard):
        """流程分布应按固定顺序排列"""
        dist = dashboard.get_flow_distribution()
        expected_order = [
            FlowStage.PENDING,
            FlowStage.IN_PROGRESS,
            FlowStage.COMPLETED,
            FlowStage.FAILED,
        ]
        for i, expected_stage in enumerate(expected_order):
            assert dist[i].stage == expected_stage, \
                f"第 {i} 项阶段应为 {expected_stage.value}"

    def test_dashboard_data_contains_flow_distribution(self, dashboard):
        data = dashboard.to_dashboard_data()
        assert len(data.flow_distribution) == 4
        total = sum(item.count for item in data.flow_distribution)
        assert total == 21


# =============================================================================
# 集成测试：面板数据完整性
# =============================================================================

class TestDashboardDataIntegration:

    def test_dashboard_data_structure(self, dashboard):
        data = dashboard.to_dashboard_data()
        assert isinstance(data.running_project_count, int)
        assert isinstance(data.agent_statuses, dict)
        assert isinstance(data.flow_distribution, list)
        assert len(data.flow_distribution) > 0

    def test_total_agent_count_is_six(self, dashboard):
        statuses = dashboard.get_agent_statuses_by_project()
        total = sum(len(agents) for agents in statuses.values())
        assert total == 6, f"总 Agent 数应为 6，实际为 {total}"

    def test_empty_projects_returns_zeros(self):
        """空项目列表应返回零值"""
        dashboard = ProjectMonitoringDashboard([], [])
        assert dashboard.get_running_project_count() == 0
        assert len(dashboard.get_agent_statuses_by_project()) == 0
        assert len(dashboard.get_flow_distribution()) == 0

    def test_empty_dashboard_data_structure(self):
        """空面板数据仍应保持结构完整"""
        dashboard = ProjectMonitoringDashboard([], [])
        data = dashboard.to_dashboard_data()
        assert data.running_project_count == 0
        assert data.agent_statuses == {}
        assert data.flow_distribution == []

    def test_single_project_single_agent(self):
        """单一项目单一 Agent 场景"""
        agent = Agent(name="solo", status=AgentStatus.RUNNING, current_task="task-1")
        project = Project(name="solo-project", is_running=True, agents=[agent])
        dist = [FlowProgress(stage=FlowStage.COMPLETED, count=1)]
        dashboard = ProjectMonitoringDashboard([project], dist)

        assert dashboard.get_running_project_count() == 1
        summary = dashboard.get_status_summary()
        assert summary["running"] == 1
        assert sum(v for k, v in summary.items() if k != "running") == 0

    def test_to_dashboard_data_is_complete(self, dashboard):
        """导出的面板数据应包含三项核心指标"""
        data = dashboard.to_dashboard_data()
        assert data.running_project_count >= 2
        assert len(data.agent_statuses) == 3
        assert len(data.flow_distribution) == 4
        total_agents = sum(len(agents) for agents in data.agent_statuses.values())
        assert total_agents == 6
