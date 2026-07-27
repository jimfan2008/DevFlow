import pytest


class ProgressStep:
    PENDING = "待执行"
    IN_PROGRESS = "执行中"
    REVIEWING = "检验中"
    PASSED = "通过"
    FAILED = "未通过"

    STATUS_LABELS = [PENDING, IN_PROGRESS, REVIEWING, PASSED, FAILED]

    def __init__(self, name: str, status: str = PENDING):
        self.name = name
        self.status = status


class ProgressBar:
    TOTAL_STEPS = 16

    STEP_NAMES = [
        "需求分析",
        "系统设计",
        "数据库设计",
        "接口设计",
        "模型层开发",
        "服务层开发",
        "控制器层开发",
        "前端组件开发",
        "前端页面开发",
        "状态管理",
        "单元测试",
        "集成测试",
        "代码审查",
        "部署配置",
        "功能验收",
        "上线发布",
    ]

    def __init__(self):
        self.steps = [ProgressStep(name) for name in self.STEP_NAMES]

    def get_step_count(self) -> int:
        return len(self.steps)

    def get_step(self, index: int) -> ProgressStep:
        return self.steps[index]

    def get_completed_count(self) -> int:
        return sum(1 for step in self.steps if step.status == ProgressStep.PASSED)

    def get_progress_percentage(self) -> float:
        return (self.get_completed_count() / self.TOTAL_STEPS) * 100.0

    def set_step_status(self, index: int, status: str) -> None:
        self.steps[index].status = status

    def get_status_counts(self) -> dict:
        counts = {}
        for label in ProgressStep.STATUS_LABELS:
            counts[label] = sum(1 for s in self.steps if s.status == label)
        return counts


class TestProgressBar16Steps:
    def test_has_16_steps(self):
        bar = ProgressBar()
        assert bar.get_step_count() == 16

    def test_all_steps_have_names(self):
        bar = ProgressBar()
        for i, step in enumerate(bar.steps):
            assert step.name == ProgressBar.STEP_NAMES[i]

    def test_default_status_is_pending(self):
        bar = ProgressBar()
        for step in bar.steps:
            assert step.status == ProgressStep.PENDING

    def test_each_step_status_is_valid_label(self):
        bar = ProgressBar()
        for step in bar.steps:
            assert step.status in ProgressStep.STATUS_LABELS

    def test_all_status_labels_defined(self):
        assert len(ProgressStep.STATUS_LABELS) == 5
        assert ProgressStep.PENDING == "待执行"
        assert ProgressStep.IN_PROGRESS == "执行中"
        assert ProgressStep.REVIEWING == "检验中"
        assert ProgressStep.PASSED == "通过"
        assert ProgressStep.FAILED == "未通过"

    def test_progress_percentage_zero_when_none_completed(self):
        bar = ProgressBar()
        assert bar.get_progress_percentage() == 0.0

    def test_progress_percentage_25_when_4_steps_completed(self):
        bar = ProgressBar()
        for i in range(4):
            bar.set_step_status(i, ProgressStep.PASSED)
        assert bar.get_progress_percentage() == 25.0

    def test_progress_percentage_50_when_8_steps_completed(self):
        bar = ProgressBar()
        for i in range(8):
            bar.set_step_status(i, ProgressStep.PASSED)
        assert bar.get_progress_percentage() == 50.0

    def test_progress_percentage_100_when_all_completed(self):
        bar = ProgressBar()
        for i in range(16):
            bar.set_step_status(i, ProgressStep.PASSED)
        assert bar.get_progress_percentage() == 100.0

    def test_set_step_status_updates_correct_step(self):
        bar = ProgressBar()
        bar.set_step_status(5, ProgressStep.IN_PROGRESS)
        assert bar.get_step(5).status == ProgressStep.IN_PROGRESS
        assert bar.get_step(4).status == ProgressStep.PENDING

    def test_step_can_be_marked_as_failed(self):
        bar = ProgressBar()
        bar.set_step_status(2, ProgressStep.FAILED)
        assert bar.get_step(2).status == ProgressStep.FAILED

    def test_step_can_be_marked_as_reviewing(self):
        bar = ProgressBar()
        bar.set_step_status(3, ProgressStep.REVIEWING)
        assert bar.get_step(3).status == ProgressStep.REVIEWING

    def test_status_counts_empty_initial_state(self):
        bar = ProgressBar()
        counts = bar.get_status_counts()
        assert counts[ProgressStep.PENDING] == 16
        assert counts[ProgressStep.PASSED] == 0
        assert counts[ProgressStep.FAILED] == 0

    def test_status_counts_after_mixed_statuses(self):
        bar = ProgressBar()
        for i in range(10):
            bar.set_step_status(i, ProgressStep.PASSED)
        bar.set_step_status(10, ProgressStep.IN_PROGRESS)
        bar.set_step_status(11, ProgressStep.FAILED)
        counts = bar.get_status_counts()
        assert counts[ProgressStep.PASSED] == 10
        assert counts[ProgressStep.IN_PROGRESS] == 1
        assert counts[ProgressStep.FAILED] == 1
        assert counts[ProgressStep.PENDING] == 4

    def test_get_step_out_of_range_raises_error(self):
        bar = ProgressBar()
        with pytest.raises(IndexError):
            bar.get_step(99)

    def test_progress_percentage_rounded_correctly(self):
        bar = ProgressBar()
        for i in range(3):
            bar.set_step_status(i, ProgressStep.PASSED)
        expected = (3 / 16) * 100.0
        assert bar.get_progress_percentage() == pytest.approx(expected)

    def test_all_steps_independent_of_each_other(self):
        bar = ProgressBar()
        bar.set_step_status(0, ProgressStep.PASSED)
        bar.set_step_status(1, ProgressStep.FAILED)
        bar.set_step_status(2, ProgressStep.IN_PROGRESS)
        bar.set_step_status(3, ProgressStep.REVIEWING)
        assert bar.get_step(0).status == ProgressStep.PASSED
        assert bar.get_step(1).status == ProgressStep.FAILED
        assert bar.get_step(2).status == ProgressStep.IN_PROGRESS
        assert bar.get_step(3).status == ProgressStep.REVIEWING
        for i in range(4, 16):
            assert bar.get_step(i).status == ProgressStep.PENDING
