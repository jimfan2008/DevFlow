import pytest
from datetime import datetime, timezone
from typing import Optional


class MockProject:
    def __init__(self, project_id: str, name: str, status: str = "running",
                 progress: float = 0.0, current_step: int = 1, total_steps: int = 16):
        self.project_id = project_id
        self.name = name
        self.status = status
        self.progress = progress
        self.current_step = current_step
        self.total_steps = total_steps
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "created_at": self.created_at.isoformat(),
        }


class MockAgent:
    def __init__(self, agent_id: str, name: str, agent_type: str,
                 status: str = "idle", current_project_id: Optional[str] = None,
                 task_count: int = 0):
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.status = status
        self.current_project_id = current_project_id
        self.task_count = task_count

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "agent_type": self.agent_type,
            "status": self.status,
            "current_project_id": self.current_project_id,
            "task_count": self.task_count,
        }


class MockStepProgress:
    def __init__(self, step_number: int, step_name: str,
                 status: str = "pending", executor: str = ""):
        self.step_number = step_number
        self.step_name = step_name
        self.status = status
        self.executor = executor

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "status": self.status,
            "executor": self.executor,
        }


class ProjectMonitorDashboard:
    def __init__(self):
        self._projects: list[MockProject] = []
        self._agents: list[MockAgent] = []
        self._step_progresses: list[MockStepProgress] = []

    def set_projects(self, projects: list[MockProject]):
        self._projects = projects

    def set_agents(self, agents: list[MockAgent]):
        self._agents = agents

    def set_step_progresses(self, progresses: list[MockStepProgress]):
        self._step_progresses = progresses

    def get_running_project_count(self) -> int:
        return sum(1 for p in self._projects if p.status == "running")

    def get_all_projects(self) -> list[dict]:
        return [p.to_dict() for p in self._projects]

    def get_agent_status_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {"idle": 0, "running": 0, "waiting": 0, "error": 0}
        for a in self._agents:
            status = a.status
            if status in summary:
                summary[status] += 1
        return summary

    def get_all_agents(self) -> list[dict]:
        return [a.to_dict() for a in self._agents]

    def get_progress_distribution(self) -> list[dict]:
        buckets: dict[str, list[dict]] = {
            "0-25": [], "26-50": [], "51-75": [], "76-99": [], "100": [],
        }
        for p in self._projects:
            prog = p.progress
            if prog == 100:
                buckets["100"].append(p.to_dict())
            elif prog >= 76:
                buckets["76-99"].append(p.to_dict())
            elif prog >= 51:
                buckets["51-75"].append(p.to_dict())
            elif prog >= 26:
                buckets["26-50"].append(p.to_dict())
            else:
                buckets["0-25"].append(p.to_dict())
        return [
            {"range": k, "count": len(v), "projects": v}
            for k, v in buckets.items()
        ]

    def get_step_status_overview(self) -> dict[str, int]:
        overview: dict[str, int] = {"pending": 0, "in_progress": 0, "completed": 0, "rejected": 0}
        for s in self._step_progresses:
            status = s.status
            if status in overview:
                overview[status] += 1
        return overview

    def get_dashboard_data(self) -> dict:
        return {
            "running_project_count": self.get_running_project_count(),
            "projects": self.get_all_projects(),
            "agent_status_summary": self.get_agent_status_summary(),
            "agents": self.get_all_agents(),
            "progress_distribution": self.get_progress_distribution(),
            "step_status_overview": self.get_step_status_overview(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


@pytest.fixture
def sample_dashboard():
    dashboard = ProjectMonitorDashboard()
    projects = [
        MockProject("proj-1", "智能客服系统", progress=45.0, current_step=5),
        MockProject("proj-2", "电商平台重构", progress=78.0, current_step=10),
        MockProject("proj-3", "数据中台建设", progress=12.0, current_step=2),
    ]
    agents = [
        MockAgent("agent-1", "海梅", "haimei", "running", "proj-1", 3),
        MockAgent("agent-2", "后兴", "houxing", "idle", None, 0),
        MockAgent("agent-3", "后旺", "houwang", "running", "proj-2", 2),
        MockAgent("agent-4", "后发", "houfa", "waiting", "proj-3", 1),
        MockAgent("agent-5", "后达", "houda", "error", None, 0),
    ]
    steps = [
        MockStepProgress(1, "需求分析", "completed", "houxing"),
        MockStepProgress(2, "架构设计", "completed", "houwang"),
        MockStepProgress(3, "任务拆分", "in_progress", "haimei"),
        MockStepProgress(4, "编码实现", "pending", "houfa"),
        MockStepProgress(5, "测试验证", "pending", "houda"),
    ]
    dashboard.set_projects(projects)
    dashboard.set_agents(agents)
    dashboard.set_step_progresses(steps)
    return dashboard


class TestProjectCount:
    def test_running_project_count_greater_than_or_equal_2(self, sample_dashboard):
        count = sample_dashboard.get_running_project_count()
        assert count >= 2

    def test_all_projects_included_in_list(self, sample_dashboard):
        projects = sample_dashboard.get_all_projects()
        assert len(projects) >= 2

    def test_project_has_required_fields(self, sample_dashboard):
        for p in sample_dashboard.get_all_projects():
            assert "project_id" in p
            assert "name" in p
            assert "status" in p
            assert "progress" in p

    def test_non_running_project_not_counted(self, sample_dashboard):
        dashboard = ProjectMonitorDashboard()
        dashboard.set_projects([
            MockProject("p1", "已完成项目", status="completed", progress=100.0),
            MockProject("p2", "已取消项目", status="cancelled", progress=0.0),
        ])
        assert dashboard.get_running_project_count() == 0

    def test_zero_projects_returns_zero_count(self):
        dashboard = ProjectMonitorDashboard()
        assert dashboard.get_running_project_count() == 0

    def test_only_running_status_counts(self):
        dashboard = ProjectMonitorDashboard()
        dashboard.set_projects([
            MockProject("p1", "运行中", status="running"),
            MockProject("p2", "暂停", status="paused"),
            MockProject("p3", "运行中2", status="running"),
            MockProject("p4", "已完成", status="completed"),
        ])
        assert dashboard.get_running_project_count() == 2


class TestAgentExecutionStatus:
    def test_all_four_statuses_present(self, sample_dashboard):
        summary = sample_dashboard.get_agent_status_summary()
        for status in ("idle", "running", "waiting", "error"):
            assert status in summary

    def test_agent_statuses_are_correct_types(self, sample_dashboard):
        summary = sample_dashboard.get_agent_status_summary()
        for status, count in summary.items():
            assert isinstance(count, int)
            assert count >= 0

    def test_running_agent_detected(self, sample_dashboard):
        summary = sample_dashboard.get_agent_status_summary()
        assert summary["running"] >= 1

    def test_idle_agent_detected(self, sample_dashboard):
        summary = sample_dashboard.get_agent_status_summary()
        assert summary["idle"] >= 1

    def test_waiting_agent_detected(self, sample_dashboard):
        summary = sample_dashboard.get_agent_status_summary()
        assert summary["waiting"] >= 1

    def test_error_agent_detected(self, sample_dashboard):
        summary = sample_dashboard.get_agent_status_summary()
        assert summary["error"] >= 1

    def test_total_agent_count_matches(self, sample_dashboard):
        summary = sample_dashboard.get_agent_status_summary()
        total = sum(summary.values())
        assert total == len(sample_dashboard._agents)

    def test_agent_has_required_fields(self, sample_dashboard):
        for a in sample_dashboard.get_all_agents():
            assert "agent_id" in a
            assert "name" in a
            assert "agent_type" in a
            assert "status" in a

    def test_empty_agents_returns_zero_counts(self):
        dashboard = ProjectMonitorDashboard()
        summary = dashboard.get_agent_status_summary()
        assert all(v == 0 for v in summary.values())

    def test_all_agents_same_status_shows_correct_summary(self):
        dashboard = ProjectMonitorDashboard()
        dashboard.set_agents([
            MockAgent("a1", "A1", "type1", "running"),
            MockAgent("a2", "A2", "type2", "running"),
            MockAgent("a3", "A3", "type3", "running"),
        ])
        summary = dashboard.get_agent_status_summary()
        assert summary["running"] == 3
        assert summary["idle"] == 0
        assert summary["waiting"] == 0
        assert summary["error"] == 0


class TestProgressDistribution:
    def test_progress_distribution_has_five_buckets(self, sample_dashboard):
        dist = sample_dashboard.get_progress_distribution()
        assert len(dist) == 5

    def test_bucket_ranges_cover_all_projects(self, sample_dashboard):
        dist = sample_dashboard.get_progress_distribution()
        total = sum(b["count"] for b in dist)
        assert total == len(sample_dashboard._projects)

    def test_each_bucket_has_range_and_count(self, sample_dashboard):
        for bucket in sample_dashboard.get_progress_distribution():
            assert "range" in bucket
            assert "count" in bucket
            assert isinstance(bucket["count"], int)

    def test_bucket_ranges_are_correct_labels(self, sample_dashboard):
        expected = ["0-25", "26-50", "51-75", "76-99", "100"]
        dist = sample_dashboard.get_progress_distribution()
        ranges = [b["range"] for b in dist]
        assert ranges == expected

    def test_project_in_correct_bucket(self, sample_dashboard):
        dist = sample_dashboard.get_progress_distribution()
        for bucket in dist:
            for p in bucket["projects"]:
                prog = p["progress"]
                r = bucket["range"]
                if r == "0-25":
                    assert 0 <= prog <= 25
                elif r == "26-50":
                    assert 26 <= prog <= 50
                elif r == "51-75":
                    assert 51 <= prog <= 75
                elif r == "76-99":
                    assert 76 <= prog <= 99
                elif r == "100":
                    assert prog == 100

    def test_project_at_boundary_25(self):
        dashboard = ProjectMonitorDashboard()
        dashboard.set_projects([MockProject("p1", "边界项目", progress=25.0)])
        dist = dashboard.get_progress_distribution()
        assert dist[0]["count"] == 1
        assert dist[1]["count"] == 0

    def test_project_at_boundary_26(self):
        dashboard = ProjectMonitorDashboard()
        dashboard.set_projects([MockProject("p1", "边界项目", progress=26.0)])
        dist = dashboard.get_progress_distribution()
        assert dist[0]["count"] == 0
        assert dist[1]["count"] == 1

    def test_project_at_boundary_100(self):
        dashboard = ProjectMonitorDashboard()
        dashboard.set_projects([MockProject("p1", "完成项目", progress=100.0)])
        dist = dashboard.get_progress_distribution()
        assert dist[4]["count"] == 1
        assert dist[3]["count"] == 0

    def test_no_projects_returns_empty_buckets(self):
        dashboard = ProjectMonitorDashboard()
        dist = dashboard.get_progress_distribution()
        assert all(b["count"] == 0 for b in dist)

    def test_multiple_projects_same_bucket(self):
        dashboard = ProjectMonitorDashboard()
        dashboard.set_projects([
            MockProject("p1", "项目A", progress=10.0),
            MockProject("p2", "项目B", progress=15.0),
            MockProject("p3", "项目C", progress=20.0),
        ])
        dist = dashboard.get_progress_distribution()
        assert dist[0]["count"] == 3


class TestDashboardDataIntegrity:
    def test_dashboard_data_has_all_sections(self, sample_dashboard):
        data = sample_dashboard.get_dashboard_data()
        assert "running_project_count" in data
        assert "projects" in data
        assert "agent_status_summary" in data
        assert "agents" in data
        assert "progress_distribution" in data
        assert "step_status_overview" in data
        assert "updated_at" in data

    def test_running_project_count_matches_projects_list(self, sample_dashboard):
        data = sample_dashboard.get_dashboard_data()
        running_in_list = sum(1 for p in data["projects"] if p["status"] == "running")
        assert data["running_project_count"] == running_in_list

    def test_agent_status_summary_matches_agents_list(self, sample_dashboard):
        data = sample_dashboard.get_dashboard_data()
        expected = {"idle": 0, "running": 0, "waiting": 0, "error": 0}
        for a in data["agents"]:
            s = a["status"]
            if s in expected:
                expected[s] += 1
        assert data["agent_status_summary"] == expected

    def test_progress_distribution_total_matches_project_count(self, sample_dashboard):
        data = sample_dashboard.get_dashboard_data()
        dist_total = sum(b["count"] for b in data["progress_distribution"])
        assert dist_total == len(data["projects"])

    def test_updated_at_is_iso_format(self, sample_dashboard):
        data = sample_dashboard.get_dashboard_data()
        ts = datetime.fromisoformat(data["updated_at"])
        assert ts is not None

    def test_step_status_overview_present(self, sample_dashboard):
        data = sample_dashboard.get_dashboard_data()
        overview = data["step_status_overview"]
        assert isinstance(overview, dict)
        assert "pending" in overview
        assert "in_progress" in overview
        assert "completed" in overview
        assert "rejected" in overview
        total_steps = sum(overview.values())
        assert total_steps == len(sample_dashboard._step_progresses)

    def test_dashboard_data_is_serializable(self, sample_dashboard):
        import json
        data = sample_dashboard.get_dashboard_data()
        serialized = json.dumps(data, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized["running_project_count"] == data["running_project_count"]
        assert deserialized["agent_status_summary"] == data["agent_status_summary"]
