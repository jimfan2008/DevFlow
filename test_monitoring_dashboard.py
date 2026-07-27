"""项目级监控面板测试"""

import pytest
from enum import Enum
from typing import List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict


class AgentStatus(Enum):
    IDLE = "空闲"
    RUNNING = "执行中"
    WAITING = "等待中"
    ERROR = "异常"


class Agent:
    """Agent 执行状态模型"""

    def __init__(self, name: str, status: AgentStatus, current_task: str = None, started_at: datetime = None):
        self.name = name
        self.status = status
        self.current_task = current_task
        self.started_at = started_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "status_key": self.status.name,
            "current_task": self.current_task,
            "started_at": self.started_at.isoformat(),
        }


class Project:
    """运行中的项目模型"""

    def __init__(self, project_id: str, name: str, agents: List[Agent], flow_stages: List[str]):
        self.project_id = project_id
        self.name = name
        self.agents = agents
        self.flow_stages = flow_stages

    @property
    def active_agents_count(self) -> int:
        return sum(1 for a in self.agents if a.status in (AgentStatus.RUNNING, AgentStatus.WAITING))

    @property
    def error_agents_count(self) -> int:
        return sum(1 for a in self.agents if a.status == AgentStatus.ERROR)

    @property
    def idle_agents_count(self) -> int:
        return sum(1 for a in self.agents if a.status == AgentStatus.IDLE)


class FlowProgress:
    """流程进度分布"""

    def __init__(self):
        self._distribution: Dict[str, int] = defaultdict(int)

    def record(self, stage: str):
        self._distribution[stage] += 1

    @property
    def distribution(self) -> Dict[str, int]:
        return dict(self._distribution)

    @property
    def total_flows(self) -> int:
        return sum(self._distribution.values())

    @property
    def completion_rate(self) -> float:
        if self.total_flows == 0:
            return 0.0
        completed = self._distribution.get("completed", 0)
        return completed / self.total_flows

    def get_stage_percentages(self) -> Dict[str, float]:
        if self.total_flows == 0:
            return {}
        return {stage: (count / self.total_flows) * 100 for stage, count in self._distribution.items()}


class MonitoringDashboard:
    """项目级监控面板"""

    def __init__(self):
        self._projects: List[Project] = []
        self._flow_progress = FlowProgress()

    def add_project(self, project: Project):
        self._projects.append(project)

    @property
    def running_projects_count(self) -> int:
        return len(self._projects)

    @property
    def agent_status_summary(self) -> Dict[AgentStatus, int]:
        summary: Dict[AgentStatus, int] = defaultdict(int)
        for project in self._projects:
            for agent in project.agents:
                summary[agent.status] += 1
        return dict(summary)

    @property
    def all_agents(self) -> List[Agent]:
        agents = []
        for project in self._projects:
            agents.extend(project.agents)
        return agents

    def get_agents_by_status(self, status: AgentStatus) -> List[Dict[str, Any]]:
        agents = [a for a in self.all_agents if a.status == status]
        return [a.to_dict() for a in agents]

    @property
    def flow_progress(self) -> FlowProgress:
        return self._flow_progress

    def get_dashboard_data(self) -> Dict[str, Any]:
        return {
            "running_projects_count": self.running_projects_count,
            "agent_status_summary": {s.value: count for s, count in self.agent_status_summary.items()},
            "agents_by_status": {
                status.value: self.get_agents_by_status(status)
                for status in AgentStatus
            },
            "flow_distribution": self._flow_progress.distribution,
            "flow_completion_rate": self._flow_progress.completion_rate,
            "flow_stage_percentages": self._flow_progress.get_stage_percentages(),
        }


@pytest.fixture
def sample_agents() -> List[Agent]:
    return [
        Agent("agent-alpha", AgentStatus.RUNNING, current_task="数据处理"),
        Agent("agent-beta", AgentStatus.RUNNING, current_task="模型训练"),
        Agent("agent-gamma", AgentStatus.WAITING, current_task="队列等待"),
        Agent("agent-delta", AgentStatus.IDLE),
        Agent("agent-epsilon", AgentStatus.ERROR, current_task="资源请求"),
    ]


@pytest.fixture
def dashboard(sample_agents: List[Agent]) -> MonitoringDashboard:
    dash = MonitoringDashboard()

    agents_a = sample_agents[:3]
    agents_b = sample_agents[3:]
    agents_c = [Agent("agent-zeta", AgentStatus.RUNNING, "特征工程")]

    project_a = Project("proj-001", "数据管道A", agents_a, ["completed", "in_progress", "pending"])
    project_b = Project("proj-002", "模型训练B", agents_b, ["completed", "in_progress"])
    project_c = Project("proj-003", "特征工程C", agents_c, ["pending"])

    dash.add_project(project_a)
    dash.add_project(project_b)
    dash.add_project(project_c)

    dash._flow_progress.record("completed")
    dash._flow_progress.record("completed")
    dash._flow_progress.record("completed")
    dash._flow_progress.record("in_progress")
    dash._flow_progress.record("in_progress")
    dash._flow_progress.record("pending")
    dash._flow_progress.record("pending")
    dash._flow_progress.record("pending")

    return dash


class TestRunningProjectsCount:
    """验收标准：显示当前运行项目数量（≥2）"""

    def test_running_projects_count_is_at_least_2(self, dashboard: MonitoringDashboard):
        count = dashboard.running_projects_count
        assert count >= 2, f"运行项目数量应为 >= 2，实际为 {count}"

    def test_running_projects_count_is_correct(self, dashboard: MonitoringDashboard):
        count = dashboard.running_projects_count
        assert count == 3, f"运行项目数量应为 3，实际为 {count}"

    def test_empty_dashboard_has_zero_projects(self):
        dash = MonitoringDashboard()
        assert dash.running_projects_count == 0

    def test_add_single_project_increments_count(self):
        dash = MonitoringDashboard()
        proj = Project("p1", "Test", [], [])
        dash.add_project(proj)
        assert dash.running_projects_count == 1

    def test_add_multiple_projects_increments_count(self):
        dash = MonitoringDashboard()
        for i in range(5):
            dash.add_project(Project(f"p{i}", f"Project {i}", [], []))
        assert dash.running_projects_count == 5


class TestAgentExecutionStatus:
    """验收标准：展示各Agent执行状态（空闲/执行中/等待中/异常）"""

    def test_status_summary_contains_all_statuses(self, dashboard: MonitoringDashboard):
        summary = dashboard.agent_status_summary
        for status in AgentStatus:
            assert status in summary, f"状态摘要中缺少状态: {status.value}"

    def test_status_summary_counts_are_correct(self, dashboard: MonitoringDashboard):
        summary = dashboard.agent_status_summary
        assert summary[AgentStatus.RUNNING] == 3, f"执行中数量应为 3，实际为 {summary[AgentStatus.RUNNING]}"
        assert summary[AgentStatus.WAITING] == 1, f"等待中数量应为 1，实际为 {summary[AgentStatus.WAITING]}"
        assert summary[AgentStatus.IDLE] == 1, f"空闲数量应为 1，实际为 {summary[AgentStatus.IDLE]}"
        assert summary[AgentStatus.ERROR] == 1, f"异常数量应为 1，实际为 {summary[AgentStatus.ERROR]}"

    def test_status_summary_totals_match_all_agents(self, dashboard: MonitoringDashboard):
        summary = dashboard.agent_status_summary
        total_from_summary = sum(summary.values())
        total_all_agents = len(dashboard.all_agents)
        assert total_from_summary == total_all_agents, (
            f"状态汇总总数 {total_from_summary} 与 Agent 总数 {total_all_agents} 不一致"
        )

    def test_get_agents_by_status_running(self, dashboard: MonitoringDashboard):
        running = dashboard.get_agents_by_status(AgentStatus.RUNNING)
        assert len(running) == 3
        for agent in running:
            assert agent["status"] == "执行中"

    def test_get_agents_by_status_idle(self, dashboard: MonitoringDashboard):
        idle_agents = dashboard.get_agents_by_status(AgentStatus.IDLE)
        assert len(idle_agents) == 1
        assert idle_agents[0]["status"] == "空闲"

    def test_get_agents_by_status_waiting(self, dashboard: MonitoringDashboard):
        waiting = dashboard.get_agents_by_status(AgentStatus.WAITING)
        assert len(waiting) == 1
        assert waiting[0]["status"] == "等待中"

    def test_get_agents_by_status_error(self, dashboard: MonitoringDashboard):
        error = dashboard.get_agents_by_status(AgentStatus.ERROR)
        assert len(error) == 1
        assert error[0]["status"] == "异常"

    def test_agent_dict_contains_required_fields(self, dashboard: MonitoringDashboard):
        agents = dashboard.all_agents
        for agent in agents:
            d = agent.to_dict()
            assert "name" in d
            assert "status" in d
            assert "status_key" in d
            assert "current_task" in d
            assert "started_at" in d

    def test_error_agent_has_current_task(self, dashboard: MonitoringDashboard):
        error_agents = dashboard.get_agents_by_status(AgentStatus.ERROR)
        assert len(error_agents) > 0
        assert error_agents[0]["current_task"] is not None

    def test_idle_agent_current_task_can_be_none(self, dashboard: MonitoringDashboard):
        idle_agents = dashboard.get_agents_by_status(AgentStatus.IDLE)
        assert len(idle_agents) > 0
        assert idle_agents[0]["current_task"] is None


class TestFlowProgressVisualization:
    """验收标准：流程进度分布可视化"""

    def test_flow_distribution_has_stages(self, dashboard: MonitoringDashboard):
        dist = dashboard.flow_progress.distribution
        expected_stages = {"completed", "in_progress", "pending"}
        actual_stages = set(dist.keys())
        assert expected_stages.issubset(actual_stages), (
            f"流程阶段应包含 {expected_stages}，实际为 {actual_stages}"
        )

    def test_flow_distribution_counts_are_positive(self, dashboard: MonitoringDashboard):
        dist = dashboard.flow_progress.distribution
        for stage, count in dist.items():
            assert count > 0, f"阶段 {stage} 的计数应为正数，实际为 {count}"

    def test_flow_distribution_counts_are_correct(self, dashboard: MonitoringDashboard):
        dist = dashboard.flow_progress.distribution
        assert dist["completed"] == 3
        assert dist["in_progress"] == 2
        assert dist["pending"] == 3

    def test_flow_total_is_correct(self, dashboard: MonitoringDashboard):
        total = dashboard.flow_progress.total_flows
        expected = 8
        assert total == expected, f"总流程数应为 {expected}，实际为 {total}"

    def test_flow_completion_rate_is_correct(self, dashboard: MonitoringDashboard):
        rate = dashboard.flow_progress.completion_rate
        expected = 3 / 8  # 3 completed out of 8 total
        assert abs(rate - expected) < 1e-9, f"完成率应为 {expected}，实际为 {rate}"

    def test_flow_completion_rate_is_between_zero_and_one(self, dashboard: MonitoringDashboard):
        rate = dashboard.flow_progress.completion_rate
        assert 0.0 <= rate <= 1.0, f"完成率应在 [0, 1] 之间，实际为 {rate}"

    def test_stage_percentages_sum_to_near_100(self, dashboard: MonitoringDashboard):
        percentages = dashboard.flow_progress.get_stage_percentages()
        total_pct = sum(percentages.values())
        assert abs(total_pct - 100.0) < 0.01, (
            f"各阶段百分比之和应接近 100%，实际为 {total_pct}%"
        )

    def test_stage_percentages_are_positive(self, dashboard: MonitoringDashboard):
        percentages = dashboard.flow_progress.get_stage_percentages()
        for stage, pct in percentages.items():
            assert pct > 0, f"阶段 {stage} 的百分比应为正数，实际为 {pct}%"

    def test_empty_flow_progress_has_zero_completion(self):
        fp = FlowProgress()
        assert fp.total_flows == 0
        assert fp.completion_rate == 0.0
        assert fp.get_stage_percentages() == {}

    def test_dashboard_data_includes_all_sections(self, dashboard: MonitoringDashboard):
        data = dashboard.get_dashboard_data()
        required_keys = [
            "running_projects_count",
            "agent_status_summary",
            "agents_by_status",
            "flow_distribution",
            "flow_completion_rate",
            "flow_stage_percentages",
        ]
        for key in required_keys:
            assert key in data, f"面板数据中缺少字段: {key}"


class TestDashboardDataIntegrity:
    """面板数据整体一致性校验"""

    def test_dashboard_data_projects_count_matches_property(self, dashboard: MonitoringDashboard):
        data = dashboard.get_dashboard_data()
        assert data["running_projects_count"] == dashboard.running_projects_count

    def test_dashboard_data_agent_status_matches_summary(self, dashboard: MonitoringDashboard):
        data = dashboard.get_dashboard_data()
        summary_total = sum(data["agent_status_summary"].values())
        expected_total = len(dashboard.all_agents)
        assert summary_total == expected_total

    def test_dashboard_data_agents_by_status_totals_match(self, dashboard: MonitoringDashboard):
        data = dashboard.get_dashboard_data()
        agents_total = sum(
            len(agents_list)
            for agents_list in data["agents_by_status"].values()
        )
        summary_total = sum(data["agent_status_summary"].values())
        assert agents_total == summary_total

    def test_dashboard_data_flow_distribution_matches_progress(self, dashboard: MonitoringDashboard):
        data = dashboard.get_dashboard_data()
        assert data["flow_distribution"] == dashboard.flow_progress.distribution

    def test_dashboard_data_flow_completion_rate_matches_progress(self, dashboard: MonitoringDashboard):
        data = dashboard.get_dashboard_data()
        assert data["flow_completion_rate"] == dashboard.flow_progress.completion_rate

    def test_dashboard_data_flow_percentages_matches_progress(self, dashboard: MonitoringDashboard):
        data = dashboard.get_dashboard_data()
        assert data["flow_stage_percentages"] == dashboard.flow_progress.get_stage_percentages()


class TestEdgeCases:
    """边界情况测试"""

    def test_single_project_with_no_agents(self):
        dash = MonitoringDashboard()
        proj = Project("p1", "Empty", [], [])
        dash.add_project(proj)
        assert dash.running_projects_count == 1
        assert dash.all_agents == []
        summary = dash.agent_status_summary
        for status in AgentStatus:
            assert summary.get(status, 0) == 0

    def test_single_project_with_one_agent_each_status(self):
        agents = [
            Agent("a1", AgentStatus.IDLE),
            Agent("a2", AgentStatus.RUNNING, "task1"),
            Agent("a3", AgentStatus.WAITING, "task2"),
            Agent("a4", AgentStatus.ERROR, "task3"),
        ]
        dash = MonitoringDashboard()
        dash.add_project(Project("p1", "All statuses", agents, []))
        summary = dash.agent_status_summary
        for status in AgentStatus:
            assert summary[status] == 1

    def test_all_agents_idle(self):
        agents = [Agent(f"idle-{i}", AgentStatus.IDLE) for i in range(5)]
        dash = MonitoringDashboard()
        dash.add_project(Project("p1", "All idle", agents, []))
        summary = dash.agent_status_summary
        assert summary[AgentStatus.IDLE] == 5
        for status in (AgentStatus.RUNNING, AgentStatus.WAITING, AgentStatus.ERROR):
            assert summary.get(status, 0) == 0

    def test_all_agents_error(self):
        agents = [Agent(f"err-{i}", AgentStatus.ERROR, "failed task") for i in range(3)]
        dash = MonitoringDashboard()
        dash.add_project(Project("p1", "All errors", agents, []))
        summary = dash.agent_status_summary
        assert summary[AgentStatus.ERROR] == 3
        for status in (AgentStatus.IDLE, AgentStatus.RUNNING, AgentStatus.WAITING):
            assert summary.get(status, 0) == 0

    def test_flow_with_only_completed(self):
        fp = FlowProgress()
        fp.record("completed")
        fp.record("completed")
        assert fp.completion_rate == 1.0
        assert fp.get_stage_percentages() == {"completed": 100.0}

    def test_flow_with_no_completed(self):
        fp = FlowProgress()
        fp.record("in_progress")
        fp.record("pending")
        assert fp.completion_rate == 0.0
        assert "completed" not in fp.distribution
