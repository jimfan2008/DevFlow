"""TDD: 16步流程进度条组件测试"""
import pytest

STEP_COUNT = 16

STATES = {
    "pending": "待执行",
    "running": "执行中",
    "inspecting": "检验中",
    "passed": "通过",
    "failed": "未通过",
}


class ProgressBar:
    """16步流程进度条"""

    def __init__(self, total=STEP_COUNT):
        self.total = total
        self.steps = {i: "pending" for i in range(1, total + 1)}

    def get_step_label(self, step_no):
        state = self.steps.get(step_no, "pending")
        return STATES.get(state, state)

    def set_step(self, step_no, state):
        if 1 <= step_no <= self.total:
            self.steps[step_no] = state

    def completed_count(self):
        return sum(1 for s in self.steps.values() if s == "passed")

    def progress_percentage(self):
        return round(self.completed_count() / self.total * 100, 2)

    def get_all_nodes(self):
        return [
            {"step": i, "state": self.steps[i], "label": self.get_step_label(i)}
            for i in range(1, self.total + 1)
        ]


@pytest.fixture
def progress_bar():
    return ProgressBar()


def test_progress_bar_has_16_nodes(progress_bar):
    nodes = progress_bar.get_all_nodes()
    assert len(nodes) == 16


def test_each_node_has_status_label(progress_bar):
    nodes = progress_bar.get_all_nodes()
    for node in nodes:
        assert node["label"] in STATES.values()


def test_default_state_is_pending(progress_bar):
    nodes = progress_bar.get_all_nodes()
    for node in nodes:
        assert node["state"] == "pending"
        assert node["label"] == "待执行"


def test_set_step_states(progress_bar):
    progress_bar.set_step(1, "passed")
    progress_bar.set_step(2, "running")
    progress_bar.set_step(3, "inspecting")
    progress_bar.set_step(4, "failed")

    assert progress_bar.get_step_label(1) == "通过"
    assert progress_bar.get_step_label(2) == "执行中"
    assert progress_bar.get_step_label(3) == "检验中"
    assert progress_bar.get_step_label(4) == "未通过"
    assert progress_bar.get_step_label(5) == "待执行"


def test_progress_percentage_zero_when_none_completed(progress_bar):
    assert progress_bar.progress_percentage() == 0.0


def test_progress_percentage_100_when_all_completed(progress_bar):
    for i in range(1, 17):
        progress_bar.set_step(i, "passed")
    assert progress_bar.progress_percentage() == 100.0


def test_progress_percentage_formula(progress_bar):
    # 完成8步 / 16 = 50%
    for i in range(1, 9):
        progress_bar.set_step(i, "passed")
    assert progress_bar.progress_percentage() == 50.0


def test_completed_count_only_counts_passed(progress_bar):
    progress_bar.set_step(1, "passed")
    progress_bar.set_step(2, "passed")
    progress_bar.set_step(3, "running")
    progress_bar.set_step(4, "failed")
    assert progress_bar.completed_count() == 2


def test_set_step_out_of_range_ignored(progress_bar):
    progress_bar.set_step(0, "passed")
    progress_bar.set_step(17, "passed")
    assert progress_bar.completed_count() == 0


def test_all_five_states_represented(progress_bar):
    progress_bar.set_step(1, "pending")
    progress_bar.set_step(2, "running")
    progress_bar.set_step(3, "inspecting")
    progress_bar.set_step(4, "passed")
    progress_bar.set_step(5, "failed")

    labels = [progress_bar.get_step_label(i) for i in range(1, 6)]
    expected = ["待执行", "执行中", "检验中", "通过", "未通过"]
    assert labels == expected
