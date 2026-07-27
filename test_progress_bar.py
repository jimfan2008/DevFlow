"""16步流程进度条组件测试"""
import pytest
from dataclasses import dataclass
from enum import Enum


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "待执行"
    IN_PROGRESS = "执行中"
    INSPECTING = "检验中"
    PASSED = "通过"
    FAILED = "未通过"


@dataclass
class StepNode:
    """进度条步骤节点"""
    index: int
    label: str
    status: StepStatus


@dataclass
class ProgressBar:
    """16步流程进度条"""
    steps: list[StepNode]

    def get_progress_percentage(self) -> float:
        """计算进度百分比 = 已完成步骤数 / 16 * 100%"""
        completed_count = sum(
            1 for s in self.steps
            if s.status in (StepStatus.PASSED, StepStatus.FAILED)
        )
        return round(completed_count / len(self.steps) * 100, 2)

    def get_status_labels(self) -> list[str]:
        """获取所有节点的状态标签"""
        return [s.status.value for s in self.steps]

    def get_node_count(self) -> int:
        """获取节点总数"""
        return len(self.steps)


def _build_bar(completed: int, in_progress: int = 0, inspecting: int = 0, failed: int = 0) -> ProgressBar:
    """构建一个ProgressBar实例，前completed个为通过，接着in_progress个为执行中，接着inspecting个为检验中，接着failed个为未通过，其余为待执行"""
    steps: list[StepNode] = []
    idx = 1
    for _ in range(completed):
        steps.append(StepNode(index=idx, label=f"步骤{idx}", status=StepStatus.PASSED))
        idx += 1
    for _ in range(in_progress):
        steps.append(StepNode(index=idx, label=f"步骤{idx}", status=StepStatus.IN_PROGRESS))
        idx += 1
    for _ in range(inspecting):
        steps.append(StepNode(index=idx, label=f"步骤{idx}", status=StepStatus.INSPECTING))
        idx += 1
    for _ in range(failed):
        steps.append(StepNode(index=idx, label=f"步骤{idx}", status=StepStatus.FAILED))
        idx += 1
    while idx <= 16:
        steps.append(StepNode(index=idx, label=f"步骤{idx}", status=StepStatus.PENDING))
        idx += 1
    return ProgressBar(steps=steps)


# ── 测试：进度条包含16个步骤节点 ──

class TestNodeCount:
    def test_exactly_16_nodes(self):
        bar = _build_bar(0)
        assert bar.get_node_count() == 16

    def test_16_nodes_after_partial_completion(self):
        bar = _build_bar(8, in_progress=2, inspecting=1, failed=1)
        assert bar.get_node_count() == 16


# ── 测试：每个节点显示状态标签 ──

class TestStatusLabels:
    def test_all_pending_labels(self):
        bar = _build_bar(0)
        labels = bar.get_status_labels()
        assert all(l == "待执行" for l in labels)

    def test_all_five_status_labels_exist(self):
        bar = _build_bar(1, in_progress=1, inspecting=1, failed=1)
        labels = bar.get_status_labels()
        assert "待执行" in labels
        assert "执行中" in labels
        assert "检验中" in labels
        assert "通过" in labels
        assert "未通过" in labels

    def test_label_order_matches_step_order(self):
        bar = _build_bar(1, in_progress=1, inspecting=1, failed=1)
        labels = bar.get_status_labels()
        assert labels[0] == "通过"
        assert labels[1] == "执行中"
        assert labels[2] == "检验中"
        assert labels[3] == "未通过"
        assert labels[4] == "待执行"


# ── 测试：进度百分比 = 已完成步骤数 / 16 × 100% ──

class TestProgressPercentage:
    def test_zero_percent_when_no_completed(self):
        bar = _build_bar(0)
        assert bar.get_progress_percentage() == 0.0

    def test_100_percent_when_all_passed(self):
        bar = _build_bar(16)
        assert bar.get_progress_percentage() == 100.0

    def test_100_percent_when_all_failed(self):
        bar = _build_bar(0, failed=16)
        assert bar.get_progress_percentage() == 100.0

    def test_half_percent_when_8_completed(self):
        bar = _build_bar(8)
        assert bar.get_progress_percentage() == 50.0

    def test_one_step_completed_is_6_25_percent(self):
        bar = _build_bar(1)
        assert bar.get_progress_percentage() == 6.25

    def test_mixed_status_counts_as_completed(self):
        bar = _build_bar(5, in_progress=3, inspecting=2, failed=3)
        completed = 5 + 3  # PASSED + FAILED
        expected = round(completed / 16 * 100, 2)
        assert bar.get_progress_percentage() == expected

    def test_in_progress_and_inspecting_not_counted_as_completed(self):
        bar = _build_bar(0, in_progress=5, inspecting=5)
        assert bar.get_progress_percentage() == 0.0
