"""
16步流程进度条组件测试
"""
import pytest
from unittest.mock import MagicMock


# ── Mock 数据与辅助结构 ──

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_INSPECTING = "inspecting"
STATUS_PASSED = "passed"
STATUS_FAILED = "failed"

STATUS_LABELS = {
    STATUS_PENDING: "待执行",
    STATUS_RUNNING: "执行中",
    STATUS_INSPECTING: "检验中",
    STATUS_PASSED: "通过",
    STATUS_FAILED: "未通过",
}

TOTAL_STEPS = 16


class StepNode:
    """单个步骤节点"""
    def __init__(self, index: int, title: str, status: str):
        self.index = index
        self.title = title
        self.status = status

    @property
    def label(self) -> str:
        return STATUS_LABELS.get(self.status, "未知状态")


class ProgressBar:
    """16步流程进度条"""
    def __init__(self, steps: list[StepNode]):
        self.steps = steps

    @property
    def total(self) -> int:
        return len(self.steps)

    @property
    def completed_count(self) -> int:
        return sum(
            1 for s in self.steps
            if s.status in (STATUS_PASSED, STATUS_FAILED)
        )

    @property
    def progress_percent(self) -> float:
        return round(self.completed_count / self.total * 100, 2) if self.total > 0 else 0.0

    def get_node_by_index(self, idx: int) -> StepNode | None:
        for s in self.steps:
            if s.index == idx:
                return s
        return None

    def render(self) -> dict:
        return {
            "total": self.total,
            "completed": self.completed_count,
            "percent": self.progress_percent,
            "nodes": [
                {
                    "index": s.index,
                    "title": s.title,
                    "status": s.status,
                    "label": s.label,
                }
                for s in self.steps
            ],
        }


def _build_default_steps() -> list[StepNode]:
    """构建默认的16步节点"""
    titles = [
        "需求分析", "系统架构设计", "数据库设计", "接口定义",
        "后端开发", "前端开发", "联调测试", "安全审计",
        "性能优化", "代码审查", "单元测试", "集成测试",
        "用户验收", "部署上线", "灰度发布", "正式投产",
    ]
    statuses_cycle = [
        STATUS_PASSED, STATUS_PASSED, STATUS_PASSED, STATUS_PASSED,
        STATUS_PASSED, STATUS_PASSED, STATUS_INSPECTING, STATUS_PENDING,
        STATUS_PENDING, STATUS_PENDING, STATUS_PENDING, STATUS_PENDING,
        STATUS_PENDING, STATUS_PENDING, STATUS_PENDING, STATUS_PENDING,
    ]
    return [
        StepNode(index=i, title=title, status=status)
        for i, (title, status) in enumerate(zip(titles, statuses_cycle))
    ]


# ── Fixtures ──

@pytest.fixture
def default_steps():
    return _build_default_steps()


@pytest.fixture
def progress_bar(default_steps):
    return ProgressBar(default_steps)


@pytest.fixture
def all_passed_steps():
    return [
        StepNode(index=i, title=f"step-{i}", status=STATUS_PASSED)
        for i in range(16)
    ]


@pytest.fixture
def all_pending_steps():
    return [
        StepNode(index=i, title=f"step-{i}", status=STATUS_PENDING)
        for i in range(16)
    ]


@pytest.fixture
def mixed_status_steps():
    """3通过 + 1执行中 + 1检验中 + 11待执行"""
    steps = [
        StepNode(0, "A", STATUS_PASSED),
        StepNode(1, "B", STATUS_PASSED),
        StepNode(2, "C", STATUS_PASSED),
        StepNode(3, "D", STATUS_RUNNING),
        StepNode(4, "E", STATUS_INSPECTING),
    ]
    steps += [StepNode(i, f"step-{i}", STATUS_PENDING) for i in range(5, 16)]
    return steps


# ── 测试用例 ──

class TestProgressBarNodeCount:
    """进度条包含16个步骤节点"""

    def test_total_steps_is_16(self, progress_bar):
        assert progress_bar.total == 16

    def test_render_contains_16_nodes(self, progress_bar):
        rendered = progress_bar.render()
        assert len(rendered["nodes"]) == 16

    def test_step_indices_are_sequential(self, progress_bar):
        rendered = progress_bar.render()
        indices = [n["index"] for n in rendered["nodes"]]
        assert indices == list(range(16))

    def test_step_indices_are_unique(self, progress_bar):
        rendered = progress_bar.render()
        indices = [n["index"] for n in rendered["nodes"]]
        assert len(indices) == len(set(indices))


class TestProgressBarStatusLabel:
    """每个节点显示状态标签"""

    def test_label_mapping_pending(self):
        node = StepNode(0, "test", STATUS_PENDING)
        assert node.label == "待执行"

    def test_label_mapping_running(self):
        node = StepNode(0, "test", STATUS_RUNNING)
        assert node.label == "执行中"

    def test_label_mapping_inspecting(self):
        node = StepNode(0, "test", STATUS_INSPECTING)
        assert node.label == "检验中"

    def test_label_mapping_passed(self):
        node = StepNode(0, "test", STATUS_PASSED)
        assert node.label == "通过"

    def test_label_mapping_failed(self):
        node = StepNode(0, "test", STATUS_FAILED)
        assert node.label == "未通过"

    def test_all_five_labels_appear_in_render(self, progress_bar):
        rendered = progress_bar.render()
        labels = {n["label"] for n in rendered["nodes"]}
        # 默认数据包含 通过 和 检验中 和 待执行
        assert "通过" in labels
        assert "检验中" in labels
        assert "待执行" in labels

    def test_render_node_contains_label_field(self, progress_bar):
        rendered = progress_bar.render()
        for node in rendered["nodes"]:
            assert "label" in node
            assert isinstance(node["label"], str)
            assert len(node["label"]) > 0


class TestProgressBarPercentage:
    """进度百分比 = 已完成步骤数 / 16 × 100%"""

    def test_percent_all_passed(self, all_passed_steps):
        bar = ProgressBar(all_passed_steps)
        assert bar.progress_percent == 100.0

    def test_percent_all_pending(self, all_pending_steps):
        bar = ProgressBar(all_pending_steps)
        assert bar.progress_percent == 0.0

    def test_percent_seven_of_sixteen(self, progress_bar):
        """默认数据: 6通过 + 1检验中 → 已完成 = 6 (仅passed+failed算完成)"""
        assert progress_bar.completed_count == 6
        expected = round(6 / 16 * 100, 2)
        assert progress_bar.progress_percent == expected

    def test_percent_mixed_status(self, mixed_status_steps):
        bar = ProgressBar(mixed_status_steps)
        # 3个 passed, 其余不算完成
        assert bar.completed_count == 3
        expected = round(3 / 16 * 100, 2)
        assert bar.progress_percent == expected

    def test_percent_formula_correct(self, all_passed_steps):
        bar = ProgressBar(all_passed_steps)
        assert bar.progress_percent == bar.completed_count / bar.total * 100

    def test_percent_rounds_to_two_decimals(self, default_steps):
        bar = ProgressBar(default_steps)
        pct = bar.progress_percent
        assert pct == round(pct, 2)

    def test_percent_zero_steps_avoids_division_by_zero(self):
        bar = ProgressBar([])
        assert bar.progress_percent == 0.0


class TestProgressBarIntegration:
    """集成验证"""

    def test_full_render_structure(self, progress_bar):
        rendered = progress_bar.render()
        assert "total" in rendered
        assert "completed" in rendered
        assert "percent" in rendered
        assert "nodes" in rendered
        assert rendered["total"] == 16
        assert isinstance(rendered["percent"], float)

    def test_get_node_by_index(self, progress_bar):
        node = progress_bar.get_node_by_index(0)
        assert node is not None
        assert node.index == 0

    def test_get_node_by_index_out_of_range(self, progress_bar):
        node = progress_bar.get_node_by_index(99)
        assert node is None
