"""
项目级监控面板测试用例
验证项目级监控面板展示运行项目数量和Agent执行状态
"""

import pytest
from datetime import datetime, timedelta


# ===== Mock Data Classes =====

class MockAgent:
    def __init__(self, name, status, current_task=None):
        self.name = name
        self.status = status
        self.current_task = current_task
        self.last_updated = datetime.now()


class MockProject:
    def __init__(self, project_id, name, is_running, agents=None):
        self.project_id = project_id
        self.name = name
        self.is_running = is_running
        self.agents = agents or []


class MockDashboardService:
    """模拟项目级监控面板服务"""

    def __init__(self, projects, agents):
        self.projects = projects
        self.agents = agents

    def get_running_projects_count(self):
        return sum(1 for p in self.projects if p.is_running)

    def get_agent_statuses(self):
        return {agent.name: agent.status for agent in self.agents}

    def get_progress_distribution(self):
        """返回流程进度分布"""
        distribution = {
            "空闲": 0,
            "执行中": 0,
            "等待中": 0,
            "异常": 0,
        }
        for agent in self.agents:
            if agent.status in distribution:
                distribution[agent.status] += 1
        return distribution

    def get_dashboard_snapshot(self):
        return {
            "running_projects_count": self.get_running_projects_count(),
            "agent_statuses": self.get_agent_statuses(),
            "progress_distribution": self.get_progress_distribution(),
            "timestamp": datetime.now().isoformat(),
        }


# ===== Fixtures =====

@pytest.fixture
def sample_agents():
    return [
        MockAgent("agent-alpha", "执行中", "数据处理任务"),
        MockAgent("agent-beta", "空闲", None),
        MockAgent("agent-gamma", "等待中", "资源等待"),
        MockAgent("agent-delta", "异常", "连接超时"),
        MockAgent("agent-epsilon", "执行中", "模型训练"),
    ]


@pytest.fixture
def sample_projects(sample_agents):
    return [
        MockProject("proj-001", "数据分析平台", True, [sample_agents[0], sample_agents[1]]),
        MockProject("proj-002", "智能客服系统", True, [sample_agents[2], sample_agents[3]]),
        MockProject("proj-003", "推荐引擎", True, [sample_agents[4]]),
        MockProject("proj-004", "旧版爬虫", False, []),
    ]


@pytest.fixture
def dashboard(sample_projects, sample_agents):
    return MockDashboardService(sample_projects, sample_agents)


# ===== Tests =====

class TestRunningProjectsCount:
    """显示当前运行项目数量（>=2）"""

    def test_running_projects_count_is_at_least_two(self, dashboard):
        count = dashboard.get_running_projects_count()
        assert count >= 2, f"运行项目数应为 >= 2，实际为 {count}"

    def test_running_projects_count_matches_actual(self, dashboard):
        count = dashboard.get_running_projects_count()
        expected = 3
        assert count == expected, f"期望 {expected} 个运行项目，实际为 {count}"

    def test_stopped_projects_not_counted(self, dashboard):
        running = [p for p in dashboard.projects if p.is_running]
        count = dashboard.get_running_projects_count()
        assert count == len(running), "未运行项目不应计入"


class TestAgentStatusDisplay:
    """展示各Agent执行状态（空闲/执行中/等待中/异常）"""

    def test_all_agent_statuses_present(self, dashboard):
        statuses = dashboard.get_agent_statuses()
        agent_names = ["agent-alpha", "agent-beta", "agent-gamma", "agent-delta", "agent-epsilon"]
        for name in agent_names:
            assert name in statuses, f"Agent '{name}' 的状态缺失"

    def test_agent_statuses_are_valid(self, dashboard):
        statuses = dashboard.get_agent_statuses()
        valid_statuses = {"空闲", "执行中", "等待中", "异常"}
        for agent_name, status in statuses.items():
            assert status in valid_statuses, f"Agent '{agent_name}' 的状态 '{status}' 无效"

    def test_specific_agent_status_correct(self, dashboard):
        statuses = dashboard.get_agent_statuses()
        expected = {
            "agent-alpha": "执行中",
            "agent-beta": "空闲",
            "agent-gamma": "等待中",
            "agent-delta": "异常",
            "agent-epsilon": "执行中",
        }
        for agent_name, expected_status in expected.items():
            assert statuses[agent_name] == expected_status, \
                f"Agent '{agent_name}' 期望状态 '{expected_status}'，实际 '{statuses[agent_name]}'"

    def test_status_counts_match(self, dashboard):
        statuses = dashboard.get_agent_statuses()
        status_count = {}
        for s in statuses.values():
            status_count[s] = status_count.get(s, 0) + 1
        assert status_count.get("执行中", 0) == 2
        assert status_count.get("空闲", 0) == 1
        assert status_count.get("等待中", 0) == 1
        assert status_count.get("异常", 0) == 1


class TestProgressDistributionVisualization:
    """流程进度分布可视化"""

    def test_distribution_has_all_categories(self, dashboard):
        dist = dashboard.get_progress_distribution()
        expected_keys = {"空闲", "执行中", "等待中", "异常"}
        assert set(dist.keys()) == expected_keys, \
            f"进度分布类别应为 {expected_keys}，实际为 {set(dist.keys())}"

    def test_distribution_values_sum_to_total_agents(self, dashboard):
        dist = dashboard.get_progress_distribution()
        total = sum(dist.values())
        expected_total = len(dashboard.agents)
        assert total == expected_total, \
            f"进度分布总数 {total} 应与 Agent 总数 {expected_total} 一致"

    def test_distribution_values_are_non_negative(self, dashboard):
        dist = dashboard.get_progress_distribution()
        for category, count in dist.items():
            assert count >= 0, f"类别 '{category}' 的计数不应为负数，实际为 {count}"

    def test_distribution_values_are_integers(self, dashboard):
        dist = dashboard.get_progress_distribution()
        for category, count in dist.items():
            assert isinstance(count, int), \
                f"类别 '{category}' 的计数应为整数，实际类型为 {type(count)}"

    def test_distribution_matches_actual_status_counts(self, dashboard):
        dist = dashboard.get_progress_distribution()
        expected = {"空闲": 1, "执行中": 2, "等待中": 1, "异常": 1}
        for category, expected_count in expected.items():
            assert dist[category] == expected_count, \
                f"类别 '{category}' 期望 {expected_count}，实际 {dist[category]}"


class TestDashboardSnapshot:
    """验证完整快照数据结构"""

    def test_snapshot_contains_all_fields(self, dashboard):
        snapshot = dashboard.get_dashboard_snapshot()
        required_keys = {"running_projects_count", "agent_statuses", "progress_distribution", "timestamp"}
        assert set(snapshot.keys()) == required_keys, \
            f"快照应包含 {required_keys}，实际为 {set(snapshot.keys())}"

    def test_snapshot_running_count_matches(self, dashboard):
        snapshot = dashboard.get_dashboard_snapshot()
        count = dashboard.get_running_projects_count()
        assert snapshot["running_projects_count"] == count

    def test_snapshot_agent_statuses_match(self, dashboard):
        snapshot = dashboard.get_dashboard_snapshot()
        expected = dashboard.get_agent_statuses()
        assert snapshot["agent_statuses"] == expected

    def test_snapshot_progress_distribution_matches(self, dashboard):
        snapshot = dashboard.get_dashboard_snapshot()
        expected = dashboard.get_progress_distribution()
        assert snapshot["progress_distribution"] == expected

    def test_snapshot_timestamp_is_iso_format(self, dashboard):
        snapshot = dashboard.get_dashboard_snapshot()
        timestamp = snapshot["timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None, "时间戳应为有效的 ISO 格式"


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_agents_list(self):
        dashboard = MockDashboardService([], [])
        count = dashboard.get_running_projects_count()
        assert count == 0

    def test_empty_projects_list(self):
        dashboard = MockDashboardService([], [])
        statuses = dashboard.get_agent_statuses()
        assert statuses == {}

    def test_all_agents_idle(self):
        agents = [MockAgent(f"idle-agent-{i}", "空闲") for i in range(3)]
        dashboard = MockDashboardService([], agents)
        dist = dashboard.get_progress_distribution()
        assert dist["空闲"] == 3
        assert dist["执行中"] == 0
        assert dist["等待中"] == 0
        assert dist["异常"] == 0

    def test_all_agents_abnormal(self):
        agents = [MockAgent(f"error-agent-{i}", "异常") for i in range(5)]
        dashboard = MockDashboardService([], agents)
        dist = dashboard.get_progress_distribution()
        assert dist["异常"] == 5
        assert dist["空闲"] == 0

    def test_no_running_projects(self):
        projects = [
            MockProject("p1", "项目一", False),
            MockProject("p2", "项目二", False),
        ]
        dashboard = MockDashboardService(projects, [])
        count = dashboard.get_running_projects_count()
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
