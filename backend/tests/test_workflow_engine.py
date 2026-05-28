"""v4.0 Workflow Engine Tests"""
import pytest
from datetime import datetime, timezone
from app.services.workflow_engine import WorkflowEngine, StepDefinition, get_default_steps


class TestWorkflowEngine:
    """16步流程状态机引擎测试"""

    def test_step_definitions_count(self):
        steps = get_default_steps()
        assert len(steps) == 16
        assert steps[0].step_number == 1
        assert steps[0].executor_role is None
        assert steps[1].step_number == 2
        assert steps[1].executor_role == "haimei"
        assert steps[2].executor_role == "houxing"
        assert steps[3].executor_role == "houwang"

    def test_step_name_accuracy(self):
        steps = get_default_steps()
        assert "用户创建" in steps[0].name
        assert "海梅" in steps[1].name and "核心目标" in steps[1].name
        assert "后兴" in steps[2].name and "需求" in steps[2].name
        assert "后旺" in steps[3].name and "架构" in steps[3].name
        assert "TDD" in steps[5].name and "测试用例计划" in steps[5].name
        assert "蜂群" in steps[6].name and "TDD" in steps[6].name
        assert "代码编写计划" in steps[7].name
        assert "后华" in steps[11].name and "安全" in steps[11].name

    def test_step_executor_mapping(self):
        steps = get_default_steps()
        executor_map = {
            1: None,         # 人类用户
            2: "haimei",
            3: "houxing",
            4: "houwang",
            5: "houfu",
            6: "haimei",
            7: "houfa",
            8: "haimei",
            9: "houfa",
            10: "houfu",
            11: "houda",
            12: "houhua",
            13: "houfu",
            14: "hougui",
            15: "haimei",
            16: "haimei",
        }
        for step in steps:
            assert step.executor_role == executor_map[step.step_number], \
                f"Step {step.step_number} should be {executor_map[step.step_number]}, got {step.executor_role}"

    def test_qa_required_steps(self):
        engine = WorkflowEngine(project_id="test-project")
        expected_qa_steps = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14}
        assert engine.QA_REQUIRED_STEPS == expected_qa_steps

    def test_no_qa_required_steps(self):
        engine = WorkflowEngine(project_id="test-project")
        no_qa_steps = {1, 10, 13, 15, 16}
        for s in no_qa_steps:
            assert s not in engine.QA_REQUIRED_STEPS, f"Step {s} should not require QA"

    def test_code_repo_commit_steps(self):
        engine = WorkflowEngine(project_id="test-project")
        commit_steps = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15}
        assert engine.CODE_REPO_COMMIT_STEPS == commit_steps
        assert 10 not in engine.CODE_REPO_COMMIT_STEPS
        assert 13 not in engine.CODE_REPO_COMMIT_STEPS
        assert 16 not in engine.CODE_REPO_COMMIT_STEPS

    def test_step_definition_required_inputs(self):
        steps = get_default_steps()
        # Step 4 (architecture design) should require SRS
        assert "software_requirements" in steps[3].required_inputs
        # Step 6 (TDD plan) should require SRS and designs
        assert "software_requirements" in steps[5].required_inputs
        # Step 9 (code writing) should require TDD test cases and code plan
        assert "tdd_test_cases" in steps[8].required_inputs
        assert "code_writing_plan" in steps[8].required_inputs

    def test_get_preserved_artifacts_starts_empty(self):
        engine = WorkflowEngine(project_id="test-project")
        preserved = engine.get_preserved_artifacts()
        assert preserved == {}

    def test_user_dissatisfied_preserves_project_repo(self):
        engine = WorkflowEngine(project_id="test-project")
        engine._preserved_artifacts["step_1"] = {"project_repo": "repo_url"}
        engine._preserved_artifacts["step_2"] = {"core_goal": "test_goal"}
        feedback = engine.user_dissatisfied(feedback="功能不完整")
        assert feedback["reset_from_step"] == 3
        assert len(engine.get_preserved_artifacts()) > 0

    def test_user_dissatisfied_returns_feedback(self):
        engine = WorkflowEngine(project_id="test-project")
        result = engine.user_dissatisfied(feedback="需要增加导出功能")
        assert result["message"] == "用户不满意，收集意见后回到第三步重新迭代"
        assert result["feedback"] == "需要增加导出功能"
        assert result["reset_from_step"] == 3


class TestStepProgress:
    """步骤推进逻辑测试"""

    def test_current_step_initialization(self):
        engine = WorkflowEngine(project_id="test-project")
        assert engine.current_step == 1

    def test_advance_step_to_2(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(2)
        assert engine.current_step == 2

    def test_advance_step_blocked_without_qa(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(2)
        engine.complete_step(2)
        with pytest.raises(ValueError, match="必须通过QA检验"):
            engine.advance_step(3)

    def test_advance_step_success_after_qa(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)
        engine.advance_step(3)
        assert engine.current_step == 3

    def test_complete_step_marks_qa_review(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(2)
        step = engine.complete_step(2)
        assert step.status == "qa_review"

    def test_complete_step_no_qa_marks_completed(self):
        engine = WorkflowEngine(project_id="test-project")
        step = engine.complete_step(1)
        assert step.status == "completed"

    def test_pass_qa_marks_completed(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(2)
        engine.complete_step(2)
        record = engine.pass_qa(2, qa_agent_id="qa-1")
        assert record.status == "passed"
        assert record.qa_agent_id == "qa-1"

    def test_fail_qa_marks_rejected(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(2)
        engine.complete_step(2)
        record = engine.fail_qa(2, qa_agent_id="qa-1", reason="不完整", suggestions=["请补充"])
        assert record.status == "failed"
        assert record.problem_details == "不完整"

    def test_cannot_pass_qa_before_complete(self):
        engine = WorkflowEngine(project_id="test-project")
        with pytest.raises(ValueError, match="必须先完成步骤"):
            engine.pass_qa(2)

    def test_step_history_tracks_changes(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)
        engine.advance_step(3)
        history = engine.get_step_history()
        assert len(history) >= 2
        statuses = [h["status"] for h in history if h["step_number"] == 2]
        assert "completed" in statuses


class TestIterationLoop:
    """迭代修改闭环测试"""

    def test_user_dissatisfied_resets_to_step_3(self):
        engine = WorkflowEngine(project_id="test-project")
        # 模拟完成前两步
        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)
        engine.advance_step(3)
        engine.complete_step(3)
        engine.pass_qa(3)
        engine.advance_step(4)

        result = engine.user_dissatisfied("不满意")
        assert result["reset_from_step"] == 3
        assert result["current_step"] == 3

    def test_preserved_artifacts_after_iteration(self):
        engine = WorkflowEngine(project_id="test-project")
        engine._preserved_artifacts["step_1"] = {"repo": "gitea_url"}
        engine._preserved_artifacts["step_2"] = {"core_goal": "goal", "org_structure": "structure"}

        engine.user_dissatisfied("不满意")
        preserved = engine.get_preserved_artifacts()
        assert "step_1" in preserved
        assert "step_2" in preserved

    def test_multiple_iterations(self):
        engine = WorkflowEngine(project_id="test-project")
        result1 = engine.user_dissatisfied("第一次")
        assert result1["reset_from_step"] == 3

        engine.advance_step(3)
        engine.complete_step(3)
        engine.pass_qa(3)

        result2 = engine.user_dissatisfied("第二次")
        assert result2["reset_from_step"] == 3