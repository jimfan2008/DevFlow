import time
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class AgentNode:
    """Agent节点模型"""

    def __init__(self, agent_id: str, name: str, status: str = "running"):
        self.agent_id = agent_id
        self.name = name
        self.status = status
        self.error_message = ""
        self.error_log = ""
        self.started_at: datetime | None = None
        self.failed_at: datetime | None = None

    def mark_failed(self, reason: str, log: str):
        self.status = "failed"
        self.error_message = reason
        self.error_log = log
        self.failed_at = datetime.now()


class MonitorPanel:
    """监控面板模型"""

    def __init__(self):
        self.nodes: dict[str, AgentNode] = {}
        self.highlight_config = {
            "failed": {"color": "red", "border": "2px solid red"},
        }

    def add_node(self, node: AgentNode):
        self.nodes[node.agent_id] = node

    def get_failed_nodes(self):
        return [n for n in self.nodes.values() if n.status == "failed"]

    def get_highlight_style(self, node: AgentNode):
        if node.status == "failed":
            return self.highlight_config["failed"]
        return {}

    def get_error_display(self, node: AgentNode):
        if node.status == "failed":
            return {
                "reason": node.error_message,
                "log": node.error_log,
            }
        return {}


class AnomalyDetector:
    """异常检测器"""

    def __init__(self, panel: MonitorPanel, check_interval_seconds: float = 10.0):
        self.panel = panel
        self.check_interval_seconds = check_interval_seconds
        self.detected_failures: list[dict] = []
        self.last_check_time: datetime | None = None

    def run_check(self, current_time: datetime | None = None):
        now = current_time or datetime.now()
        self.last_check_time = now
        failed = self.panel.get_failed_nodes()
        for node in failed:
            already = any(d["agent_id"] == node.agent_id for d in self.detected_failures)
            if not already:
                self.detected_failures.append({
                    "agent_id": node.agent_id,
                    "agent_name": node.name,
                    "reason": node.error_message,
                    "detected_at": now,
                })
        return self.detected_failures

    def get_detection_latency(self, node: AgentNode) -> timedelta:
        if node.failed_at is None:
            return timedelta.max
        detected = next(
            (d for d in self.detected_failures if d["agent_id"] == node.agent_id),
            None,
        )
        if detected is None:
            return timedelta.max
        return detected["detected_at"] - node.failed_at


# ── pytest tests ──


def test_failed_node_highlighted_in_red():
    """失败Agent节点在面板上高亮（红色标记）"""
    panel = MonitorPanel()
    node = AgentNode("agent-001", "DataProcessor")
    node.mark_failed("Out of memory", "java.lang.OutOfMemoryError: heap space")
    panel.add_node(node)

    style = panel.get_highlight_style(node)

    assert style is not None, "失败节点应返回高亮样式"
    assert style["color"] == "red", f"颜色应为红色，实际为 {style['color']}"
    assert style["border"] == "2px solid red", f"边框应为红色，实际为 {style['border']}"


def test_failed_node_shows_error_reason_and_log():
    """显示失败原因和错误日志"""
    panel = MonitorPanel()
    reason = "Connection timeout to database server"
    log = "Traceback (most recent call last):\n  File 'db.py', line 42, in connect\nTimeoutError: Connection refused"
    node = AgentNode("agent-002", "DBConnector")
    node.mark_failed(reason, log)
    panel.add_node(node)

    display = panel.get_error_display(node)

    assert display["reason"] == reason, f"原因不匹配: {display['reason']}"
    assert display["log"] == log, f"日志不匹配: {display['log']}"


def test_non_failed_node_has_no_highlight_or_error():
    """正常节点不应有高亮或错误信息"""
    panel = MonitorPanel()
    node = AgentNode("agent-003", "HealthyAgent", status="running")
    panel.add_node(node)

    style = panel.get_highlight_style(node)
    display = panel.get_error_display(node)

    assert style == {}, "正常节点不应有高亮样式"
    assert display == {}, "正常节点不应有错误信息"


def test_detection_latency_within_one_minute():
    """异常检测时间 ≤1分钟"""
    panel = MonitorPanel()
    base_time = datetime(2026, 7, 16, 10, 0, 0)

    node = AgentNode("agent-004", "BatchWorker")
    node.mark_failed("Task queue overflow", "QueueFullError: max size 10000 reached")
    node.failed_at = base_time
    panel.add_node(node)

    detector = AnomalyDetector(panel, check_interval_seconds=30.0)

    check_time = base_time + timedelta(seconds=45)
    detector.run_check(current_time=check_time)

    failures = detector.detected_failures
    assert len(failures) == 1, f"应检测到1个失败，实际 {len(failures)}"
    assert failures[0]["agent_id"] == "agent-004"
    assert failures[0]["reason"] == "Task queue overflow"

    latency = detector.get_detection_latency(node)
    max_allowed = timedelta(minutes=1)
    assert latency <= max_allowed, f"检测延迟 {latency} 超过1分钟上限"


def test_multiple_failed_nodes_all_detected():
    """多个失败节点都能被检测和报告"""
    panel = MonitorPanel()
    base_time = datetime(2026, 7, 16, 12, 0, 0)

    nodes = []
    for i in range(3):
        n = AgentNode(f"agent-{100 + i}", f"Worker-{i}")
        n.mark_failed(f"Error {i}", f"Log entry {i}")
        n.failed_at = base_time
        panel.add_node(n)
        nodes.append(n)

    detector = AnomalyDetector(panel, check_interval_seconds=15.0)
    detector.run_check(current_time=base_time + timedelta(seconds=30))

    failures = detector.detected_failures
    assert len(failures) == 3, f"应检测到3个失败节点，实际 {len(failures)}"
    ids = {f["agent_id"] for f in failures}
    assert ids == {f"agent-{100 + i}" for i in range(3)}, f"ID集合不匹配: {ids}"


def test_no_duplicate_detection_on_recheck():
    """重复检测不会产生重复报告"""
    panel = MonitorPanel()
    base_time = datetime(2026, 7, 16, 14, 0, 0)

    node = AgentNode("agent-005", "Schedular")
    node.mark_failed("Cron parse error", "Invalid cron expression: '*/abc * * * *'")
    node.failed_at = base_time
    panel.add_node(node)

    detector = AnomalyDetector(panel, check_interval_seconds=10.0)
    detector.run_check(current_time=base_time + timedelta(seconds=15))
    detector.run_check(current_time=base_time + timedelta(seconds=30))
    detector.run_check(current_time=base_time + timedelta(seconds=60))

    assert len(detector.detected_failures) == 1, "重复检测不应产生重复条目"


def test_failed_nodes_list_only_contains_failed():
    """get_failed_nodes 只返回失败的节点"""
    panel = MonitorPanel()
    panel.add_node(AgentNode("a", "Alpha", "running"))
    panel.add_node(AgentNode("b", "Beta", "completed"))
    panel.add_node(AgentNode("c", "Charlie"))
    panel.nodes["c"].mark_failed("Crash", "segfault")
    panel.add_node(AgentNode("d", "Delta"))
    panel.nodes["d"].mark_failed("Timeout", "http 504")

    failed = panel.get_failed_nodes()

    assert len(failed) == 2, f"应有2个失败节点，实际 {len(failed)}"
    assert {n.agent_id for n in failed} == {"c", "d"}


def test_error_display_contains_all_required_fields():
    """错误展示包含 reason 和 log 两个必要字段"""
    panel = MonitorPanel()
    node = AgentNode("agent-006", "Reporter")
    node.mark_failed("Report generation failed", "TemplateError: missing field 'summary'")
    panel.add_node(node)

    display = panel.get_error_display(node)

    assert "reason" in display, "缺少 reason 字段"
    assert "log" in display, "缺少 log 字段"
    assert isinstance(display["reason"], str), "reason 应为字符串"
    assert isinstance(display["log"], str), "log 应为字符串"
    assert len(display["reason"]) > 0, "reason 不应为空"
    assert len(display["log"]) > 0, "log 不应为空"


def test_detection_at_exact_one_minute_boundary():
    """检测延迟恰好为1分钟时仍应通过（≤1分钟）"""
    panel = MonitorPanel()
    base_time = datetime(2026, 7, 16, 16, 0, 0)

    node = AgentNode("agent-007", "BoundaryTest")
    node.mark_failed("Boundary error", "edge case log")
    node.failed_at = base_time
    panel.add_node(node)

    detector = AnomalyDetector(panel, check_interval_seconds=60.0)
    check_time = base_time + timedelta(minutes=1)
    detector.run_check(current_time=check_time)

    latency = detector.get_detection_latency(node)
    max_allowed = timedelta(minutes=1)
    assert latency <= max_allowed, f"恰好在边界上不应失败，延迟 {latency}"


def test_detection_over_one_minute_fails():
    """检测延迟超过1分钟时应判定不通过"""
    panel = MonitorPanel()
    base_time = datetime(2026, 7, 16, 18, 0, 0)

    node = AgentNode("agent-008", "SlowDetector")
    node.mark_failed("Critical failure", "fatal error log")
    node.failed_at = base_time
    panel.add_node(node)

    detector = AnomalyDetector(panel, check_interval_seconds=120.0)
    check_time = base_time + timedelta(minutes=2)
    detector.run_check(current_time=check_time)

    latency = detector.get_detection_latency(node)
    max_allowed = timedelta(minutes=1)
    assert latency > max_allowed, f"超过1分钟应判定失败，延迟 {latency}"
