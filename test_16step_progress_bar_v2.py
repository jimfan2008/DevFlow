from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict

import pytest


class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    QA_REVIEW = "qa_review"
    COMPLETED = "completed"
    REJECTED = "rejected"


_STATUS_LABEL_MAP: Dict[StepStatus, str] = {
    StepStatus.PENDING: "待执行",
    StepStatus.IN_PROGRESS: "执行中",
    StepStatus.QA_REVIEW: "检验中",
    StepStatus.COMPLETED: "通过",
    StepStatus.REJECTED: "未通过",
}

_STEP_NAME_MAP: Dict[int, str] = {
    1: "人类用户创建项目",
    2: "海梅确认核心目标与搭建组织架构",
    3: "后兴需求分析",
    4: "后旺架构设计",
    5: "后富建立开发环境",
    6: "海梅制订TDD测试用例计划",
    7: "后发蜂群编写TDD测试用例",
    8: "海梅制订代码编写计划",
    9: "后发蜂群编写功能代码",
    10: "后富部署到测试环境",
    11: "后达蜂群全面测试",
    12: "后华安全审计",
    13: "后富部署到生产环境",
    14: "后贵完善项目文档",
    15: "海梅报告交付成果",
    16: "用户满意度确认与迭代",
}


@dataclass
class WorkflowStep:
    name: str
    executor: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    description: str = ""

    def is_completed(self) -> bool:
        return self.status == StepStatus.COMPLETED


class ProgressBar:
    """16步流程进度条组件"""

    TOTAL_STEPS = 16

    def __init__(self, steps: Optional[List[WorkflowStep]] = None):
        self.steps = steps if steps is not None else []

    def get_step_count(self) -> int:
        return len(self.steps)

    def get_step(self, index: int) -> WorkflowStep:
        if index < 0 or index >= len(self.steps):
            raise IndexError(f"步骤索引 {index} 超出范围")
        return self.steps[index]

    def get_all_steps(self) -> List[WorkflowStep]:
        return list(self.steps)

    @staticmethod
    def status_label(status: StepStatus) -> str:
        return _STATUS_LABEL_MAP[status]

    def get_step_status_label(self, index: int) -> str:
        return self.status_label(self.get_step(index).status)

    def get_all_status_labels(self) -> List[str]:
        return [self.status_label(s.status) for s in self.steps]

    def get_progress_percentage(self) -> int:
        completed = sum(1 for s in self.steps if s.is_completed())
        if not self.steps:
            return 0
        return round((completed / self.TOTAL_STEPS) * 100)

    def get_completed_count(self) -> int:
        return sum(1 for s in self.steps if s.is_completed())

    @staticmethod
    def get_step_name(index: int) -> str:
        return _STEP_NAME_MAP.get(index, f"步骤{index}")

    def set_step_status(self, index: int, new_status: StepStatus):
        step = self.get_step(index)
        step.status = new_status

    def render(self) -> str:
        pct = self.get_progress_percentage()
        lines = [f"进度: {pct}% ({self.get_completed_count()}/{self.TOTAL_STEPS})"]
        for i, step in enumerate(self.steps):
            label = self.status_label(step.status)
            lines.append(f"  [{i + 1}] {step.name:40s} | {label}")
        return "\n".join(lines)

    @classmethod
    def empty(cls) -> "ProgressBar":
        return cls([])

    @classmethod
    def default_16_steps(cls) -> "ProgressBar":
        steps = [
            WorkflowStep(name=cls.get_step_name(i + 1), status=StepStatus.PENDING)
            for i in range(cls.TOTAL_STEPS)
        ]
        return cls(steps)

    @classmethod
    def with_completed(cls, count: int) -> "ProgressBar":
        steps = []
        for i in range(cls.TOTAL_STEPS):
            status = StepStatus.COMPLETED if i < count else StepStatus.PENDING
            steps.append(WorkflowStep(name=cls.get_step_name(i + 1), status=status))
        return cls(steps)


@pytest.fixture
def empty_bar():
    return ProgressBar.empty()


@pytest.fixture
def default_bar():
    return ProgressBar.default_16_steps()


@pytest.fixture
def bar_all_completed():
    return ProgressBar.with_completed(16)


@pytest.fixture
def bar_half_completed():
    return ProgressBar.with_completed(8)


class TestStepNodeCount:

    def test_default_bar_has_16_steps(self, default_bar):
        assert default_bar.get_step_count() == 16

    def test_with_completed_zero_has_16_steps(self):
        bar = ProgressBar.with_completed(0)
        assert bar.get_step_count() == 16

    def test_with_completed_16_has_16_steps(self, bar_all_completed):
        assert bar_all_completed.get_step_count() == 16

    def test_with_completed_7_has_16_steps(self):
        bar = ProgressBar.with_completed(7)
        assert bar.get_step_count() == 16

    def test_empty_bar_has_zero_steps(self, empty_bar):
        assert empty_bar.get_step_count() == 0

    def test_get_all_steps_returns_all_16(self, default_bar):
        steps = default_bar.get_all_steps()
        assert len(steps) == 16

    def test_each_step_index_accessible(self, default_bar):
        for i in range(16):
            step = default_bar.get_step(i)
            assert step is not None

    def test_invalid_index_raises_error(self, default_bar):
        with pytest.raises(IndexError):
            default_bar.get_step(16)
        with pytest.raises(IndexError):
            default_bar.get_step(-1)


class TestStatusLabels:

    def test_pending_label(self):
        assert ProgressBar.status_label(StepStatus.PENDING) == "待执行"

    def test_in_progress_label(self):
        assert ProgressBar.status_label(StepStatus.IN_PROGRESS) == "执行中"

    def test_qa_review_label(self):
        assert ProgressBar.status_label(StepStatus.QA_REVIEW) == "检验中"

    def test_completed_label(self):
        assert ProgressBar.status_label(StepStatus.COMPLETED) == "通过"

    def test_rejected_label(self):
        assert ProgressBar.status_label(StepStatus.REJECTED) == "未通过"

    def test_all_16_pending_show_待执行(self, default_bar):
        labels = default_bar.get_all_status_labels()
        assert all(l == "待执行" for l in labels)

    def test_first_step_in_progress(self, default_bar):
        default_bar.set_step_status(0, StepStatus.IN_PROGRESS)
        assert default_bar.get_step_status_label(0) == "执行中"

    def test_third_step_qa_review(self, default_bar):
        default_bar.set_step_status(2, StepStatus.QA_REVIEW)
        assert default_bar.get_step_status_label(2) == "检验中"

    def test_first_step_completed(self, default_bar):
        default_bar.set_step_status(0, StepStatus.COMPLETED)
        assert default_bar.get_step_status_label(0) == "通过"

    def test_fifth_step_rejected(self, default_bar):
        default_bar.set_step_status(4, StepStatus.REJECTED)
        assert default_bar.get_step_status_label(4) == "未通过"

    def test_mixed_status_labels(self):
        steps = [
            WorkflowStep(name="s1", status=StepStatus.COMPLETED),
            WorkflowStep(name="s2", status=StepStatus.IN_PROGRESS),
            WorkflowStep(name="s3", status=StepStatus.QA_REVIEW),
            WorkflowStep(name="s4", status=StepStatus.REJECTED),
            WorkflowStep(name="s5", status=StepStatus.PENDING),
        ]
        bar = ProgressBar(steps)
        assert bar.get_step_status_label(0) == "通过"
        assert bar.get_step_status_label(1) == "执行中"
        assert bar.get_step_status_label(2) == "检验中"
        assert bar.get_step_status_label(3) == "未通过"
        assert bar.get_step_status_label(4) == "待执行"

    def test_all_five_status_values_covered(self):
        expected = {"待执行", "执行中", "检验中", "通过", "未通过"}
        actual = {ProgressBar.status_label(s) for s in StepStatus}
        assert actual == expected


class TestProgressPercentage:

    def test_zero_completed_is_zero_percent(self, default_bar):
        assert default_bar.get_progress_percentage() == 0

    def test_one_completed_is_six_percent(self):
        bar = ProgressBar.with_completed(1)
        assert bar.get_progress_percentage() == 6

    def test_four_completed_is_25_percent(self):
        bar = ProgressBar.with_completed(4)
        assert bar.get_progress_percentage() == 25

    def test_eight_completed_is_50_percent(self, bar_half_completed):
        assert bar_half_completed.get_progress_percentage() == 50

    def test_twelve_completed_is_75_percent(self):
        bar = ProgressBar.with_completed(12)
        assert bar.get_progress_percentage() == 75

    def test_sixteen_completed_is_100_percent(self, bar_all_completed):
        assert bar_all_completed.get_progress_percentage() == 100

    def test_only_completed_counted_not_in_progress(self):
        steps = [
            WorkflowStep(name="s1", status=StepStatus.COMPLETED),
            WorkflowStep(name="s2", status=StepStatus.COMPLETED),
            WorkflowStep(name="s3", status=StepStatus.COMPLETED),
            WorkflowStep(name="s4", status=StepStatus.IN_PROGRESS),
            WorkflowStep(name="s5", status=StepStatus.QA_REVIEW),
            WorkflowStep(name="s6", status=StepStatus.REJECTED),
        ] + [WorkflowStep(name=f"s{i}") for i in range(7, 16)]
        bar = ProgressBar(steps)
        assert bar.get_progress_percentage() == 19

    def test_in_progress_not_counted_as_completed(self):
        steps = [
            WorkflowStep(name="s1", status=StepStatus.IN_PROGRESS),
        ] + [WorkflowStep(name=f"s{i}") for i in range(2, 17)]
        bar = ProgressBar(steps)
        assert bar.get_progress_percentage() == 0

    def test_rejected_not_counted_as_completed(self):
        steps = [
            WorkflowStep(name="s1", status=StepStatus.REJECTED),
        ] + [WorkflowStep(name=f"s{i}") for i in range(2, 17)]
        bar = ProgressBar(steps)
        assert bar.get_progress_percentage() == 0

    def test_qa_review_not_counted_as_completed(self):
        steps = [
            WorkflowStep(name="s1", status=StepStatus.QA_REVIEW),
        ] + [WorkflowStep(name=f"s{i}") for i in range(2, 17)]
        bar = ProgressBar(steps)
        assert bar.get_progress_percentage() == 0

    def test_empty_bar_progress_is_zero(self, empty_bar):
        assert empty_bar.get_progress_percentage() == 0

    def test_completed_count_matches(self):
        bar = ProgressBar.with_completed(7)
        assert bar.get_completed_count() == 7
        assert bar.get_progress_percentage() == round(7 / 16 * 100)

    def test_formula_three_out_of_16(self):
        bar = ProgressBar.with_completed(3)
        assert bar.get_progress_percentage() == 19

    def test_formula_five_out_of_16(self):
        bar = ProgressBar.with_completed(5)
        assert bar.get_progress_percentage() == 31


class TestStatusChange:

    def test_change_pending_to_completed(self, default_bar):
        assert default_bar.get_step(0).status == StepStatus.PENDING
        default_bar.set_step_status(0, StepStatus.COMPLETED)
        assert default_bar.get_step(0).status == StepStatus.COMPLETED

    def test_change_pending_to_in_progress(self, default_bar):
        default_bar.set_step_status(0, StepStatus.IN_PROGRESS)
        assert default_bar.get_step(0).status == StepStatus.IN_PROGRESS

    def test_progress_updates_after_completion(self, default_bar):
        assert default_bar.get_progress_percentage() == 0
        default_bar.set_step_status(0, StepStatus.COMPLETED)
        assert default_bar.get_progress_percentage() == 6

    def test_multiple_completions_accumulate(self, default_bar):
        for i in range(8):
            default_bar.set_step_status(i, StepStatus.COMPLETED)
        assert default_bar.get_progress_percentage() == 50

    def test_reject_then_complete(self, default_bar):
        default_bar.set_step_status(0, StepStatus.REJECTED)
        assert default_bar.get_progress_percentage() == 0
        default_bar.set_step_status(0, StepStatus.COMPLETED)
        assert default_bar.get_progress_percentage() == 6


class TestRenderOutput:

    def test_render_contains_progress_percentage(self, default_bar):
        output = default_bar.render()
        assert "0%" in output

    def test_render_contains_completed_fraction(self, bar_half_completed):
        output = bar_half_completed.render()
        assert "50%" in output
        assert "8/16" in output

    def test_render_contains_status_labels(self, default_bar):
        default_bar.set_step_status(0, StepStatus.COMPLETED)
        output = default_bar.render()
        assert "通过" in output
        assert "待执行" in output

    def test_render_contains_step_numbers(self, default_bar):
        output = default_bar.render()
        for i in range(1, 17):
            assert f"[{i}]" in output

    def test_all_completed_render(self, bar_all_completed):
        output = bar_all_completed.render()
        assert "100%" in output
        assert "16/16" in output
        assert "待执行" not in output


class TestFullWorkflowProgression:

    def test_sequential_completion(self):
        bar = ProgressBar.default_16_steps()
        assert bar.get_progress_percentage() == 0
        for i in range(16):
            bar.set_step_status(i, StepStatus.COMPLETED)
            expected = round((i + 1) / 16 * 100)
            assert bar.get_progress_percentage() == expected, (
                f"步骤 {i + 1} 完成后期望 {expected}% "
                f"实际 {bar.get_progress_percentage()}%"
            )
        assert bar.get_progress_percentage() == 100

    def test_intermittent_status_changes(self):
        bar = ProgressBar.default_16_steps()
        bar.set_step_status(0, StepStatus.IN_PROGRESS)
        assert bar.get_progress_percentage() == 0
        bar.set_step_status(0, StepStatus.QA_REVIEW)
        assert bar.get_progress_percentage() == 0
        bar.set_step_status(0, StepStatus.COMPLETED)
        assert bar.get_progress_percentage() == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
