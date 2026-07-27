import pytest
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum


# ═══════════════════════════════════════════
# 领域模型
# ═══════════════════════════════════════════

class AgentStatus(Enum):
    """Agent 执行状态"""
    IDLE = "空闲"
    RUNNING = "执行中"
    WAITING = "等待中"
    ERROR = "异常"


class ProjectStatus(Enum):
    """项目运行状态"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"


@dataclass
class AgentInfo:
    """Agent 信息"""
    name: str
    status: AgentStatus
    current_task: str = ""
    project_id: str = ""


@dataclass
class ProjectInfo:
    """项目信息"""
    project_id: str
    name: str
    status: ProjectStatus = ProjectStatus.RUNNING
    agents: List[AgentInfo] = field(default_factory=list)


@dataclass
class FlowProgress:
    """流程进度"""
    flow_id: str
    flow_name: str
    progress_percent: float
    stage: str


# ═══════════════════════════════════════════
# 被测模块
# ═══════════════════════════════════════════

class ProjectMonitorPanel:
    """项目级监控面板"""

    def __init__(self):
        self._projects: List[ProjectInfo] = []
        self._flow_progresses: List[FlowProgress] = []

    def add_project(self, project: ProjectInfo) -> None:
        self._projects.append(project)

    def add_flow_progress(self, progress: FlowProgress) -> None:
        self._flow_progresses.append(progress)

    def clear(self) -> None:
        self._projects.clear()
        self._flow_progresses.clear()

    # ── 验收标准一：显示当前运行项目数量 ──

    def get_running_project_count(self) -> int:
        return sum(1 for p in self._projects if p.status == ProjectStatus.RUNNING)

    def get_total_project_count(self) -> int:
        return len(self._projects)

    def get_all_projects(self) -> List[ProjectInfo]:
        return list(self._projects)

    # ── 验收标准二：展示各 Agent 执行状态 ──

    def get_agent_status_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {s.value: 0 for s in AgentStatus}
        for project in self._projects:
            for agent in project.agents:
                summary[agent.status.value] += 1
        return summary

    def get_all_agents(self) -> List[AgentInfo]:
        agents: List[AgentInfo] = []
        for project in self._projects:
            for agent in project.agents:
                agents.append(agent)
        return agents

    def get_agents_by_status(self, status: AgentStatus) -> List[AgentInfo]:
        return [
            agent
            for project in self._projects
            for agent in project.agents
            if agent.status == status
        ]

    # ── 验收标准三：流程进度分布可视化 ──

    def get_flow_progress_list(self) -> List[FlowProgress]:
        return list(self._flow_progresses)

    def get_progress_distribution(self) -> Dict[str, int]:
        buckets: Dict[str, int] = {
            "0-25%": 0,
            "26-50%": 0,
            "51-75%": 0,
            "76-100%": 0,
        }
        for fp in self._flow_progresses:
            pct = fp.progress_percent
            if pct <= 25:
                buckets["0-25%"] += 1
            elif pct <= 50:
                buckets["26-50%"] += 1
            elif pct <= 75:
                buckets["51-75%"] += 1
            else:
                buckets["76-100%"] += 1
        return buckets

    def get_progress_in_range(self, min_pct: float, max_pct: float) -> List[FlowProgress]:
        return [
            fp for fp in self._flow_progresses
            if min_pct <= fp.progress_percent <= max_pct
        ]

    def get_progress_bar(self, progress: FlowProgress, width: int = 20) -> str:
        filled = int(round(progress.progress_percent / 100.0 * width))
        filled = max(0, min(filled, width))
        return "\u2588" * filled + "\u2591" * (width - filled)

    # ── 面板汇总 ──

    def get_panel_data(self) -> dict:
        return {
            "running_project_count": self.get_running_project_count(),
            "total_project_count": self.get_total_project_count(),
            "agent_status_summary": self.get_agent_status_summary(),
            "agent_details": self.get_all_agents(),
            "flow_progress_list": self.get_flow_progress_list(),
            "progress_distribution": self.get_progress_distribution(),
        }


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def panel() -> ProjectMonitorPanel:
    return ProjectMonitorPanel()


@pytest.fixture
def panel_with_data() -> ProjectMonitorPanel:
    p = ProjectMonitorPanel()

    # 项目 1：运行中
    p.add_project(ProjectInfo(
        project_id="proj-a",
        name="智能客服系统",
        status=ProjectStatus.RUNNING,
        agents=[
            AgentInfo("海梅", AgentStatus.RUNNING, "数据清洗", "proj-a"),
            AgentInfo("后兴", AgentStatus.IDLE, "", "proj-a"),
            AgentInfo("后旺", AgentStatus.WAITING, "等待审批", "proj-a"),
        ],
    ))

    # 项目 2：运行中
    p.add_project(ProjectInfo(
        project_id="proj-b",
        name="电商平台重构",
        status=ProjectStatus.RUNNING,
        agents=[
            AgentInfo("后发", AgentStatus.RUNNING, "接口迁移", "proj-b"),
            AgentInfo("后达", AgentStatus.ERROR, "数据库连接超时", "proj-b"),
        ],
    ))

    # 项目 3：已停止
    p.add_project(ProjectInfo(
        project_id="proj-c",
        name="数据中台",
        status=ProjectStatus.STOPPED,
        agents=[
            AgentInfo("后宁", AgentStatus.IDLE, "", "proj-c"),
        ],
    ))

    # 流程进度
    p.add_flow_progress(FlowProgress("flow-1", "需求评审", 10.0, "初始化"))
    p.add_flow_progress(FlowProgress("flow-2", "架构设计", 35.0, "设计阶段"))
    p.add_flow_progress(FlowProgress("flow-3", "开发实施", 58.0, "编码阶段"))
    p.add_flow_progress(FlowProgress("flow-4", "测试验证", 72.0, "测试阶段"))
    p.add_flow_progress(FlowProgress("flow-5", "部署上线", 90.0, "部署阶段"))
    p.add_flow_progress(FlowProgress("flow-6", "运维监控", 99.5, "收尾阶段"))

    return p


# ═══════════════════════════════════════════
# 验收标准一：显示当前运行项目数量（≥2）
# ═══════════════════════════════════════════

class TestRunningProjectCount:

    def test_running_count_at_least_two(self, panel_with_data):
        count = panel_with_data.get_running_project_count()
        assert count >= 2, f"运行项目数应 >= 2，实际为 {count}"

    def test_running_count_exact(self, panel_with_data):
        assert panel_with_data.get_running_project_count() == 2

    def test_stopped_project_not_counted(self, panel_with_data):
        count = panel_with_data.get_running_project_count()
        all_projects = panel_with_data.get_all_projects()
        stopped_count = sum(1 for p in all_projects if p.status == ProjectStatus.STOPPED)
        assert count == len(all_projects) - stopped_count

    def test_empty_panel_zero_count(self, panel):
        assert panel.get_running_project_count() == 0

    def test_all_stopped_returns_zero(self, panel):
        panel.add_project(ProjectInfo("p1", "项目一", ProjectStatus.STOPPED))
        panel.add_project(ProjectInfo("p2", "项目二", ProjectStatus.PAUSED))
        assert panel.get_running_project_count() == 0

    def test_all_running_count_matches_total(self, panel):
        for i in range(5):
            panel.add_project(ProjectInfo(f"p{i}", f"项目{i}", ProjectStatus.RUNNING))
        assert panel.get_running_project_count() == 5

    def test_total_project_count(self, panel_with_data):
        assert panel_with_data.get_total_project_count() == 3

    def test_panel_data_running_count_consistent(self, panel_with_data):
        data = panel_with_data.get_panel_data()
        assert data["running_project_count"] >= 2
        assert data["running_project_count"] == panel_with_data.get_running_project_count()


# ═══════════════════════════════════════════
# 验收标准二：展示各 Agent 执行状态
# ═══════════════════════════════════════════

class TestAgentExecutionStatus:

    def test_all_four_status_keys_present(self, panel_with_data):
        summary = panel_with_data.get_agent_status_summary()
        expected_keys = {"空闲", "执行中", "等待中", "异常"}
        assert set(summary.keys()) == expected_keys

    def test_idle_count(self, panel_with_data):
        summary = panel_with_data.get_agent_status_summary()
        assert summary["空闲"] == 2

    def test_running_count(self, panel_with_data):
        summary = panel_with_data.get_agent_status_summary()
        assert summary["执行中"] == 2

    def test_waiting_count(self, panel_with_data):
        summary = panel_with_data.get_agent_status_summary()
        assert summary["等待中"] == 1

    def test_error_count(self, panel_with_data):
        summary = panel_with_data.get_agent_status_summary()
        assert summary["异常"] == 1

    def test_summary_total_matches_agent_total(self, panel_with_data):
        summary = panel_with_data.get_agent_status_summary()
        total_from_summary = sum(summary.values())
        total_from_agents = len(panel_with_data.get_all_agents())
        assert total_from_summary == total_from_agents

    def test_each_status_has_at_least_one_agent(self, panel_with_data):
        summary = panel_with_data.get_agent_status_summary()
        for status_label, count in summary.items():
            assert count > 0, f"状态 {status_label} 应有至少一个 Agent"

    def test_agents_by_status_running(self, panel_with_data):
        agents = panel_with_data.get_agents_by_status(AgentStatus.RUNNING)
        assert len(agents) == 2
        for a in agents:
            assert a.status == AgentStatus.RUNNING

    def test_agents_by_status_error(self, panel_with_data):
        agents = panel_with_data.get_agents_by_status(AgentStatus.ERROR)
        assert len(agents) == 1
        assert agents[0].current_task == "数据库连接超时"

    def test_agents_by_status_idle(self, panel_with_data):
        agents = panel_with_data.get_agents_by_status(AgentStatus.IDLE)
        assert len(agents) == 2

    def test_agents_by_status_waiting(self, panel_with_data):
        agents = panel_with_data.get_agents_by_status(AgentStatus.WAITING)
        assert len(agents) == 1
        assert agents[0].current_task == "等待审批"

    def test_empty_panel_all_zero(self, panel):
        summary = panel.get_agent_status_summary()
        assert all(v == 0 for v in summary.values())

    def test_panel_data_agent_details_complete(self, panel_with_data):
        data = panel_with_data.get_panel_data()
        assert len(data["agent_details"]) == 6
        for agent in data["agent_details"]:
            assert isinstance(agent, AgentInfo)
            assert agent.status in AgentStatus

    def test_agent_status_labels_are_chinese(self):
        assert AgentStatus.IDLE.value == "空闲"
        assert AgentStatus.RUNNING.value == "执行中"
        assert AgentStatus.WAITING.value == "等待中"
        assert AgentStatus.ERROR.value == "异常"


# ═══════════════════════════════════════════
# 验收标准三：流程进度分布可视化
# ═══════════════════════════════════════════

class TestFlowProgressVisualization:

    def test_distribution_has_four_buckets(self, panel_with_data):
        dist = panel_with_data.get_progress_distribution()
        expected_keys = {"0-25%", "26-50%", "51-75%", "76-100%"}
        assert set(dist.keys()) == expected_keys

    def test_bucket_counts_correct(self, panel_with_data):
        dist = panel_with_data.get_progress_distribution()
        assert dist["0-25%"] == 1
        assert dist["26-50%"] == 1
        assert dist["51-75%"] == 2
        assert dist["76-100%"] == 2

    def test_distribution_total_matches_flow_count(self, panel_with_data):
        dist = panel_with_data.get_progress_distribution()
        assert sum(dist.values()) == len(panel_with_data.get_flow_progress_list())

    def test_empty_panel_distribution_all_zero(self, panel):
        dist = panel.get_progress_distribution()
        assert all(v == 0 for v in dist.values())

    def test_boundary_at_25(self, panel):
        panel.add_flow_progress(FlowProgress("f1", "边界", 25.0, "测试"))
        dist = panel.get_progress_distribution()
        assert dist["0-25%"] == 1

    def test_boundary_at_26(self, panel):
        panel.add_flow_progress(FlowProgress("f1", "边界", 26.0, "测试"))
        dist = panel.get_progress_distribution()
        assert dist["26-50%"] == 1

    def test_boundary_at_75(self, panel):
        panel.add_flow_progress(FlowProgress("f1", "边界", 75.0, "测试"))
        dist = panel.get_progress_distribution()
        assert dist["51-75%"] == 1

    def test_boundary_at_76(self, panel):
        panel.add_flow_progress(FlowProgress("f1", "边界", 76.0, "测试"))
        dist = panel.get_progress_distribution()
        assert dist["76-100%"] == 1

    def test_boundary_at_100(self, panel):
        panel.add_flow_progress(FlowProgress("f1", "完成", 100.0, "完成"))
        dist = panel.get_progress_distribution()
        assert dist["76-100%"] == 1

    def test_progress_in_range(self, panel_with_data):
        flows = panel_with_data.get_progress_in_range(50.0, 80.0)
        assert len(flows) == 2
        for f in flows:
            assert 50.0 <= f.progress_percent <= 80.0

    def test_progress_in_range_empty(self, panel_with_data):
        flows = panel_with_data.get_progress_in_range(0.0, 5.0)
        assert len(flows) == 0

    def test_progress_bar_full(self, panel_with_data):
        flows = panel_with_data.get_flow_progress_list()
        near_complete = next(f for f in flows if f.flow_id == "flow-6")
        bar = panel_with_data.get_progress_bar(near_complete, width=20)
        assert len(bar) == 20
        assert bar.count("\u2588") == 20

    def test_progress_bar_empty(self, panel):
        panel.add_flow_progress(FlowProgress("f0", "未开始", 0.0, "初始"))
        bar = panel.get_progress_bar(
            panel.get_flow_progress_list()[0], width=20
        )
        assert len(bar) == 20
        assert bar.count("\u2588") == 0
        assert bar.count("\u2591") == 20

    def test_progress_bar_half(self, panel):
        panel.add_flow_progress(FlowProgress("f0", "一半", 50.0, "中期"))
        bar = panel.get_progress_bar(
            panel.get_flow_progress_list()[0], width=20
        )
        assert len(bar) == 20
        assert bar.count("\u2588") == 10
        assert bar.count("\u2591") == 10

    def test_panel_data_distribution_matches(self, panel_with_data):
        data = panel_with_data.get_panel_data()
        direct = panel_with_data.get_progress_distribution()
        assert data["progress_distribution"] == direct

    def test_flow_progress_values_valid_range(self, panel_with_data):
        flows = panel_with_data.get_flow_progress_list()
        for f in flows:
            assert 0 <= f.progress_percent <= 100


# ═══════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════

class TestPanelDataIntegration:

    def test_panel_data_has_all_fields(self, panel_with_data):
        data = panel_with_data.get_panel_data()
        assert isinstance(data["running_project_count"], int)
        assert isinstance(data["total_project_count"], int)
        assert isinstance(data["agent_status_summary"], dict)
        assert isinstance(data["agent_details"], list)
        assert isinstance(data["flow_progress_list"], list)
        assert isinstance(data["progress_distribution"], dict)

    def test_panel_data_consistency(self, panel_with_data):
        data = panel_with_data.get_panel_data()
        assert data["running_project_count"] >= 2
        assert sum(data["agent_status_summary"].values()) == len(data["agent_details"])
        assert sum(data["progress_distribution"].values()) == len(data["flow_progress_list"])
        assert data["total_project_count"] == 3

    def test_clear_resets_panel(self, panel_with_data):
        panel_with_data.clear()
        data = panel_with_data.get_panel_data()
        assert data["running_project_count"] == 0
        assert data["total_project_count"] == 0
        assert all(v == 0 for v in data["agent_status_summary"].values())
        assert len(data["agent_details"]) == 0
        assert len(data["flow_progress_list"]) == 0
        assert all(v == 0 for v in data["progress_distribution"].values())

    def test_single_project_single_agent(self, panel):
        agent = AgentInfo("solo", AgentStatus.RUNNING, "唯一任务", "p1")
        project = ProjectInfo("p1", "单项目", ProjectStatus.RUNNING, agents=[agent])
        panel.add_project(project)
        panel.add_flow_progress(FlowProgress("f1", "单流程", 50.0, "中期"))

        data = panel.get_panel_data()
        assert data["running_project_count"] == 1
        assert data["total_project_count"] == 1
        assert data["agent_status_summary"]["执行中"] == 1
        assert data["agent_status_summary"]["空闲"] == 0
        assert data["progress_distribution"]["26-50%"] == 1

    def test_panel_data_json_serializable(self, panel_with_data):
        import json
        data = panel_with_data.get_panel_data()
        serializable = {
            "running_project_count": data["running_project_count"],
            "total_project_count": data["total_project_count"],
            "agent_status_summary": data["agent_status_summary"],
            "agent_details": [
                {"name": a.name, "status": a.status.value, "current_task": a.current_task}
                for a in data["agent_details"]
            ],
            "flow_progress_count": len(data["flow_progress_list"]),
            "progress_distribution": data["progress_distribution"],
        }
        result = json.dumps(serializable, ensure_ascii=False)
        parsed = json.loads(result)
        assert parsed["running_project_count"] >= 2
        assert parsed["total_project_count"] == 3
        assert parsed["flow_progress_count"] == 6

    def test_completely_empty_panel(self, panel):
        data = panel.get_panel_data()
        assert data["running_project_count"] == 0
        assert data["total_project_count"] == 0
        assert all(v == 0 for v in data["agent_status_summary"].values())
        assert len(data["agent_details"]) == 0
        assert len(data["flow_progress_list"]) == 0
        assert all(v == 0 for v in data["progress_distribution"].values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
