import time
import pytest
from datetime import datetime, timedelta


class MockAgentNode:
    """模拟 Agent 节点"""

    def __init__(self, agent_id, name, status="running", error_message=None, error_log=None):
        self.agent_id = agent_id
        self.name = name
        self.status = status
        self.error_message = error_message
        self.error_log = error_log
        self.start_time = datetime.now()
        self.error_time = None


class MockAgentMonitorPanel:
    """模拟 Agent 监控面板"""

    HIGHLIGHT_THRESHOLD_SECONDS = 60  # 1分钟

    def __init__(self):
        self.nodes = []
        self.highlights = {}

    def add_node(self, node):
        self.nodes.append(node)

    def detect_failure(self, node):
        """检测 Agent 是否失败"""
        if node.status == "failed" and node.error_message:
            node.error_time = datetime.now()
            self.highlights[node.agent_id] = {
                "color": "red",
                "error_message": node.error_message,
                "error_log": node.error_log,
                "error_time": node.error_time,
            }
            return True
        return False

    def get_node_highlight(self, agent_id):
        return self.highlights.get(agent_id)

    def get_detection_time_seconds(self, agent_id):
        highlight = self.highlights.get(agent_id)
        if not highlight:
            return None
        node = next((n for n in self.nodes if n.agent_id == agent_id), None)
        if not node or not node.error_time:
            return None
        delta = node.error_time - node.start_time
        return delta.total_seconds()


class TestAgentFailureHighlightDisplay:
    """测试 Agent 执行失败时监控面板高亮显示并展示错误信息"""

    @pytest.fixture
    def panel(self):
        return MockAgentMonitorPanel()

    @pytest.fixture
    def failed_node(self):
        return MockAgentNode(
            agent_id="agent-001",
            name="DataProcessor",
            status="failed",
            error_message="内存溢出: 处理数据集时超出最大堆大小",
            error_log="java.lang.OutOfMemoryError: Java heap space\n\tat com.example.DataProcessor.process(DataProcessor.java:42)",
        )

    @pytest.fixture
    def running_node(self):
        return MockAgentNode(
            agent_id="agent-002",
            name="Scheduler",
            status="running",
        )

    def test_failed_node_highlighted_in_red(self, panel, failed_node):
        """失败 Agent 节点在面板上高亮（红色标记）"""
        panel.add_node(failed_node)
        panel.detect_failure(failed_node)

        highlight = panel.get_node_highlight("agent-001")
        assert highlight is not None
        assert highlight["color"] == "red"

    def test_running_node_not_highlighted(self, panel, running_node):
        """正常运行的 Agent 节点不会被高亮"""
        panel.add_node(running_node)
        detected = panel.detect_failure(running_node)

        assert detected is False
        highlight = panel.get_node_highlight("agent-002")
        assert highlight is None

    def test_failed_node_displays_error_message(self, panel, failed_node):
        """显示失败原因"""
        panel.add_node(failed_node)
        panel.detect_failure(failed_node)

        highlight = panel.get_node_highlight("agent-001")
        assert highlight["error_message"] == "内存溢出: 处理数据集时超出最大堆大小"

    def test_failed_node_displays_error_log(self, panel, failed_node):
        """显示错误日志"""
        panel.add_node(failed_node)
        panel.detect_failure(failed_node)

        highlight = panel.get_node_highlight("agent-001")
        expected_log = "java.lang.OutOfMemoryError: Java heap space\n\tat com.example.DataProcessor.process(DataProcessor.java:42)"
        assert highlight["error_log"] == expected_log

    def test_detection_time_within_threshold(self, panel, failed_node):
        """异常检测时间 ≤1分钟"""
        panel.add_node(failed_node)
        panel.detect_failure(failed_node)

        detection_seconds = panel.get_detection_time_seconds("agent-001")
        assert detection_seconds is not None
        assert detection_seconds <= MockAgentMonitorPanel.HIGHLIGHT_THRESHOLD_SECONDS

    def test_multiple_nodes_mixed_status(self, panel, failed_node, running_node):
        """多节点混合状态下，仅失败节点高亮"""
        panel.add_node(failed_node)
        panel.add_node(running_node)

        panel.detect_failure(failed_node)
        panel.detect_failure(running_node)

        highlight_failed = panel.get_node_highlight("agent-001")
        highlight_running = panel.get_node_highlight("agent-002")

        assert highlight_failed is not None
        assert highlight_failed["color"] == "red"
        assert highlight_running is None

    def test_node_without_error_message_not_highlighted(self, panel):
        """status 为 failed 但无 error_message 的节点不高亮"""
        node = MockAgentNode(
            agent_id="agent-003",
            name="EmptyError",
            status="failed",
            error_message=None,
            error_log=None,
        )
        panel.add_node(node)
        detected = panel.detect_failure(node)

        assert detected is False
        assert panel.get_node_highlight("agent-003") is None

    def test_highlight_contains_error_time(self, panel, failed_node):
        """高亮信息包含错误发生时间"""
        panel.add_node(failed_node)
        panel.detect_failure(failed_node)

        highlight = panel.get_node_highlight("agent-001")
        assert highlight["error_time"] is not None
        assert isinstance(highlight["error_time"], datetime)

    def test_multiple_failed_nodes_all_highlighted(self, panel):
        """多个失败节点全部高亮显示"""
        node_a = MockAgentNode(
            agent_id="a1",
            name="Agent A",
            status="failed",
            error_message="内存溢出",
            error_log="OutOfMemory at line 10",
        )
        node_b = MockAgentNode(
            agent_id="b1",
            name="Agent B",
            status="failed",
            error_message="空指针异常",
            error_log="NullPointerException at line 25",
        )
        node_c = MockAgentNode(
            agent_id="c1",
            name="Agent C",
            status="running",
        )
        panel.add_node(node_a)
        panel.add_node(node_b)
        panel.add_node(node_c)

        panel.detect_failure(node_a)
        panel.detect_failure(node_b)
        panel.detect_failure(node_c)

        assert panel.get_node_highlight("a1") is not None
        assert panel.get_node_highlight("a1")["color"] == "red"
        assert panel.get_node_highlight("b1") is not None
        assert panel.get_node_highlight("b1")["color"] == "red"
        assert panel.get_node_highlight("c1") is None

    def test_status_update_triggers_highlight(self, panel):
        """Agent 状态更新为失败后，立即触发高亮"""
        node = MockAgentNode(
            agent_id="x1",
            name="转换Agent",
            status="running",
        )
        panel.add_node(node)

        # 初始状态不应高亮
        assert panel.get_node_highlight("x1") is None

        # 更新为失败
        node.status = "failed"
        node.error_message = "文件解析失败"
        node.error_log = "ParseError: invalid format at line 10"
        panel.detect_failure(node)

        # 更新后应红色高亮
        highlight = panel.get_node_highlight("x1")
        assert highlight is not None
        assert highlight["color"] == "red"
        assert highlight["error_message"] == "文件解析失败"
        assert "ParseError" in highlight["error_log"]

    def test_failure_details_contain_agent_id_and_name(self, panel, failed_node):
        """失败详情包含 Agent ID 和名称"""
        panel.add_node(failed_node)
        panel.detect_failure(failed_node)

        highlight = panel.get_node_highlight("agent-001")
        assert highlight is not None
        # Agent ID 通过 highlights 的 key 存储
        assert "agent-001" in panel.highlights
        # 节点信息在 nodes 中可查
        node = next((n for n in panel.nodes if n.agent_id == "agent-001"), None)
        assert node is not None
        assert node.agent_id == "agent-001"
        assert node.name == "DataProcessor"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
