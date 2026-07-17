"""v4.0 TDD测试用例模块 - 单元测试
覆盖 SRS 8.1.6 (第六步 TDD测试用例计划) 和 8.1.7 (第七步 TDD测试用例编写) 验收标准
"""
import pytest
from datetime import datetime, timezone
from app.models.tdd_test_case import TDDTestCase
from app.services.workflow_engine import WorkflowEngine, get_default_steps
from app.api.workflow.core import (
    TDD_PLAN_DIMENSIONS, TDD_TESTCASE_DIMENSIONS,
    CODE_PLAN_DIMENSIONS,
)
from app.services.qa_gate_service import QAGateService


class TestTDDTestCaseModel:
    """TDDTestCase 模型 CRUD 测试"""

    @pytest.mark.asyncio
    async def test_create_tdd_test_case(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-001",
            title="用户注册 - 有效输入测试",
            description="验证用户注册功能在有效输入下的行为",
            precondition="项目已创建，数据库已初始化",
            test_steps="1. 输入有效用户名\n2. 输入有效密码\n3. 点击注册按钮",
            expected_result="用户注册成功，返回200状态码",
            priority="P0",
            category="用户模块",
            source_section="3.1 用户管理",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        assert case.id is not None
        assert case.case_id == "TC-001"
        assert case.project_id == test_project.id
        assert case.round_number == 1
        assert case.qa_status == "pending"
        assert case.fix_attempts == 0

    @pytest.mark.asyncio
    async def test_tdd_test_case_to_dict(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-001",
            title="用户注册测试",
            description="验证用户注册功能",
            precondition="系统正常运行",
            test_steps="1. 输入信息\n2. 提交",
            expected_result="注册成功",
            priority="P0",
            category="用户模块",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        result = case.to_dict()
        assert result["case_id"] == "TC-001"
        assert result["title"] == "用户注册测试"
        assert result["priority"] == "P0"
        assert "created_at" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_tdd_test_case_defaults(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-002",
            title="订单创建测试",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        assert case.qa_status == "pending"
        assert case.fix_attempts == 0
        assert case.created_at is not None
        assert case.updated_at is not None

    @pytest.mark.asyncio
    async def test_tdd_test_case_update_qc_status(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-003",
            title="支付流程测试",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        case.qa_status = "passed"
        case.qa_score = 95
        case.qa_feedback = "测试用例完整，覆盖边界条件"
        db_session.commit()
        db_session.refresh(case)
        assert case.qa_status == "passed"
        assert case.qa_score == 95

    @pytest.mark.asyncio
    async def test_tdd_test_case_fix_attempts_increment(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-004",
            title="失败后重试测试",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        case.fix_attempts = 1
        db_session.commit()
        db_session.refresh(case)
        assert case.fix_attempts == 1
        case.fix_attempts = 2
        db_session.commit()
        db_session.refresh(case)
        assert case.fix_attempts == 2

    @pytest.mark.asyncio
    async def test_tdd_test_case_query_by_project_and_round(self, db_session, test_project):
        for i in range(3):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=1,
                case_index=i,
                case_id=f"TC-R1-{i:03d}",
                title=f"测试用例 {i}",
            )
            db_session.add(case)
        for i in range(2):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=2,
                case_index=i,
                case_id=f"TC-R2-{i:03d}",
                title=f"第二轮测试用例 {i}",
            )
            db_session.add(case)
        db_session.commit()
        from sqlalchemy import func
        rounds = db_session.query(
            TDDTestCase.round_number,
            func.count(TDDTestCase.id).label("total"),
        ).filter(
            TDDTestCase.project_id == test_project.id,
        ).group_by(TDDTestCase.round_number).all()
        round_map = {r.round_number: r.total for r in rounds}
        assert round_map[1] == 3
        assert round_map[2] == 2

    @pytest.mark.asyncio
    async def test_tdd_test_case_cascade_delete(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-CASCADE",
            title="级联删除测试",
        )
        db_session.add(case)
        db_session.commit()
        case_id = case.id
        db_session.delete(test_project)
        db_session.commit()
        remaining = db_session.query(TDDTestCase).filter(TDDTestCase.id == case_id).first()
        assert remaining is None

    @pytest.mark.asyncio
    async def test_tdd_test_case_metadata_json(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-META",
            title="元数据测试",
            metadata_json={
                "swarm_agent": "claude_code",
                "generation_time_seconds": 12.5,
                "source_doc": "docs/srs_v1.md",
            },
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        assert case.metadata_json["swarm_agent"] == "claude_code"
        assert case.metadata_json["generation_time_seconds"] == 12.5

    @pytest.mark.asyncio
    async def test_tdd_test_case_bulk_create(self, db_session, test_project):
        cases = []
        for i in range(10):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=1,
                case_index=i,
                case_id=f"TC-BULK-{i:03d}",
                title=f"批量创建测试 {i}",
            )
            db_session.add(case)
            cases.append(case)
        db_session.commit()
        count = db_session.query(TDDTestCase).filter(
            TDDTestCase.project_id == test_project.id,
        ).count()
        assert count == 10

    @pytest.mark.asyncio
    async def test_tdd_test_case_qa_detail(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-QA-DTL",
            title="QA详情测试",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        case.qa_detail = (
            "检验结果：\n"
            "- 正确性: 95分 ✓\n"
            "- 覆盖率: 100分 ✓\n"
            "- 原子化: 90分 ✓\n"
            "- 验收标准匹配度: 85分 ✗ 验收标准与用例不完全匹配\n"
            "建议：验收标准补充具体的预期输出值"
        )
        case.qa_score = 92
        case.qa_status = "failed"
        db_session.commit()
        db_session.refresh(case)
        assert case.qa_score == 92
        assert case.qa_status == "failed"
        assert "验收标准" in case.qa_detail


class TestTDDPlanDimensions:
    """第六步 TDD测试用例计划 - 检验维度测试 (SRS 8.1.6)"""

    def test_tdd_plan_dimensions_count(self):
        assert len(TDD_PLAN_DIMENSIONS) == 3

    def test_tdd_plan_dimension_keys(self):
        keys = {d["key"] for d in TDD_PLAN_DIMENSIONS}
        expected = {"coverage", "atomicity", "measurability"}
        assert keys == expected

    def test_tdd_plan_coverage_dimension(self):
        coverage = next(d for d in TDD_PLAN_DIMENSIONS if d["key"] == "coverage")
        assert "覆盖率" in coverage["label"]
        assert "覆盖" in coverage["description"]

    def test_tdd_plan_atomicity_dimension(self):
        atomicity = next(d for d in TDD_PLAN_DIMENSIONS if d["key"] == "atomicity")
        assert "原子化" in atomicity["label"]
        assert "最小不可再分" in atomicity["description"]

    def test_tdd_plan_measurability_dimension(self):
        measurability = next(d for d in TDD_PLAN_DIMENSIONS if d["key"] == "measurability")
        assert "可量化" in measurability["label"]
        assert "可验证" in measurability["description"]

    def test_tdd_plan_all_dimensions_have_label_and_description(self):
        for d in TDD_PLAN_DIMENSIONS:
            assert "key" in d
            assert "label" in d
            assert "description" in d
            assert len(d["label"]) > 0
            assert len(d["description"]) > 0


class TestTDDTestCaseDimensions:
    """第七步 TDD测试用例 - 检验维度测试 (SRS 8.1.7)"""

    def test_tdd_testcase_dimensions_count(self):
        assert len(TDD_TESTCASE_DIMENSIONS) == 4

    def test_tdd_testcase_dimension_keys(self):
        keys = {d["key"] for d in TDD_TESTCASE_DIMENSIONS}
        expected = {"correctness", "coverage", "atomicity", "acceptance_match"}
        assert keys == expected

    def test_tdd_testcase_correctness_dimension(self):
        correctness = next(d for d in TDD_TESTCASE_DIMENSIONS if d["key"] == "correctness")
        assert "正确性" in correctness["label"]
        assert "逻辑" in correctness["description"]

    def test_tdd_testcase_coverage_dimension(self):
        coverage = next(d for d in TDD_TESTCASE_DIMENSIONS if d["key"] == "coverage")
        assert "覆盖率" in coverage["label"]

    def test_tdd_testcase_atomicity_dimension(self):
        atomicity = next(d for d in TDD_TESTCASE_DIMENSIONS if d["key"] == "atomicity")
        assert "原子化" in atomicity["label"]

    def test_tdd_testcase_acceptance_match_dimension(self):
        acceptance = next(d for d in TDD_TESTCASE_DIMENSIONS if d["key"] == "acceptance_match")
        assert "验收标准匹配度" in acceptance["label"]
        assert "验收标准" in acceptance["description"]

    def test_tdd_testcase_all_dimensions_have_full_structure(self):
        for d in TDD_TESTCASE_DIMENSIONS:
            assert "key" in d
            assert "label" in d
            assert "description" in d
            assert len(d["key"]) > 0
            assert len(d["label"]) > 0


class TestTDDPlanInspection:
    """第六步 TDD测试用例计划 - QA检验逻辑测试"""

    def test_tdd_plan_inspect_pass_all_dimensions(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="tdd_plan",
            project_id="proj-1",
            workflow_step_id=6,
        )
        assert record["status"] == "passed"
        assert len(record["review_dimensions"]) == 3

    def test_tdd_plan_inspect_fail_with_reason(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="tdd_plan",
            project_id="proj-1",
            workflow_step_id=6,
            result="failed",
            reason="需求覆盖率不足，缺少对核心功能的测试计划",
            suggestions=["补充用户模块测试计划", "增加边界条件覆盖"],
        )
        assert record["status"] == "failed"
        assert "覆盖率不足" in record["problem_details"]
        assert len(record["fix_suggestions"]) == 2

    def test_tdd_plan_rollback_creates_fail_record(self):
        service = QAGateService()
        record = service.rollback(
            task_id="tdd-plan-task-1",
            project_id="proj-1",
            workflow_step_id=6,
            reason="原子化程度不足，测试用例粒度过大",
            suggestions=["将复合测试用例拆分为多个原子用例"],
        )
        assert record["status"] == "failed"
        assert record["task_id"] == "tdd-plan-task-1"
        assert record["project_id"] == "proj-1"

    def test_tdd_plan_inspect_dimensions_passed_all(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="tdd_plan",
            project_id="proj-1",
            workflow_step_id=6,
            result="passed",
        )
        assert record["status"] == "passed"
        dims = record["review_dimensions"]
        all_passed = all(dim.get("score", 0) >= 90 for dim in dims)
        assert all_passed

    def test_tdd_plan_inspect_single_dimension_failed(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="tdd_plan",
            project_id="proj-1",
            workflow_step_id=6,
            result="failed",
            reason="验收标准不可量化",
            suggestions=["为每个测试用例添加具体的数值指标"],
        )
        assert record["status"] == "failed"

    def test_tdd_plan_qa_gate_rejects_incomplete_plan(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(6)
        engine.complete_step(6)
        record = engine.fail_qa(6, reason="计划不完整，缺少验收标准", suggestions=["补充验收标准"])
        assert record.status == "failed"
        assert "不完整" in record.problem_details

    def test_tdd_plan_qa_gate_passes_complete_plan(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(6)
        engine.complete_step(6)
        record = engine.pass_qa(6)
        assert record.status == "passed"


class TestTDDTestCaseInspection:
    """第七步 TDD测试用例代码 - QA检验逻辑测试"""

    def test_tdd_testcase_inspect_pass_all_dimensions(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="tdd_code",
            project_id="proj-1",
            workflow_step_id=7,
        )
        assert record["status"] == "passed"

    def test_tdd_testcase_inspect_fail_with_reason(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="tdd_code",
            project_id="proj-1",
            workflow_step_id=7,
            result="failed",
            reason="测试用例正确性不足，断言逻辑有误",
            suggestions=["修正断言条件", "增加异常场景测试"],
        )
        assert record["status"] == "failed"
        assert "正确性不足" in record["problem_details"]
        assert len(record["fix_suggestions"]) == 2

    def test_tdd_testcase_inspect_pass_all_four_dimensions(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="tdd_code",
            project_id="proj-1",
            workflow_step_id=7,
            result="passed",
        )
        assert record["status"] == "passed"
        dims = record["review_dimensions"]
        assert len(dims) == 4

    def test_tdd_testcase_rollback_with_feedback(self):
        service = QAGateService()
        record = service.rollback(
            task_id="tdd-code-task-1",
            project_id="proj-1",
            workflow_step_id=7,
            reason="代码覆盖率不足，缺少边界测试",
            suggestions=["添加空值输入测试", "添加大数据量测试"],
        )
        assert record["status"] == "failed"
        assert "覆盖率不足" in record["problem_details"]

    def test_tdd_testcase_qa_gate_passes_after_fix(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(7)
        engine.complete_step(7)
        engine.fail_qa(7, reason="用例不正确", suggestions=["修正断言"])
        assert engine._step_states[7].status == "qa_review"
        engine.reset_step(7)
        engine.advance_step(7)
        engine.complete_step(7)
        record = engine.pass_qa(7)
        assert record.status == "passed"


class TestTDDPlanGeneration:
    """TDD测试用例计划生成测试"""

    def test_tdd_plan_step_definition(self):
        steps = get_default_steps()
        step6 = next(s for s in steps if s.step_number == 6)
        assert step6.executor_role == "haimei"
        assert "TDD" in step6.name
        assert "测试用例计划" in step6.name

    def test_tdd_plan_required_inputs(self):
        steps = get_default_steps()
        step6 = next(s for s in steps if s.step_number == 6)
        assert "software_requirements" in step6.required_inputs

    def test_tdd_plan_step_6_is_qa_required(self):
        engine = WorkflowEngine(project_id="test-project")
        assert 6 in engine.QA_REQUIRED_STEPS

    def test_tdd_plan_artifacts_save_and_retrieve(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.save_step6_artifacts({
            "tdd_plan": "# TDD计划\n\n1. 用户模块测试\n2. 订单模块测试",
            "filename": "tdd-plan-20260601.md",
        })
        artifacts = engine.get_step6_artifacts()
        assert artifacts.get("tdd_plan") is not None
        assert "用户模块" in artifacts["tdd_plan"]
        assert artifacts.get("filename") == "tdd-plan-20260601.md"

    def test_tdd_plan_with_empty_artifacts(self):
        engine = WorkflowEngine(project_id="test-project")
        artifacts = engine.get_step6_artifacts()
        assert artifacts == {}

    def test_tdd_plan_status_tracking(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.save_step6_artifacts({"status": "generating"})
        artifacts = engine.get_step6_artifacts()
        assert artifacts.get("status") == "generating"
        engine.save_step6_artifacts({"status": "done", "qa_passed": True})
        artifacts = engine.get_step6_artifacts()
        assert artifacts.get("status") == "done"
        assert artifacts.get("qa_passed") is True


class TestTDDTestCaseSwarmExecution:
    """第七步 TDD测试用例蜂群执行测试"""

    def test_tdd_step_7_definition(self):
        steps = get_default_steps()
        step7 = next(s for s in steps if s.step_number == 7)
        assert step7.executor_role == "houfa"
        assert "蜂群" in step7.name
        assert "TDD" in step7.name

    def test_tdd_step_7_is_qa_required(self):
        engine = WorkflowEngine(project_id="test-project")
        assert 7 in engine.QA_REQUIRED_STEPS

    def test_tdd_step_7_is_code_repo_commit_step(self):
        engine = WorkflowEngine(project_id="test-project")
        assert 7 in engine.CODE_REPO_COMMIT_STEPS

    def test_tdd_step_7_artifacts_save_and_retrieve(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.save_step7_artifacts({
            "swarm_summary": {"total": 10, "passed": 8, "failed": 2},
            "qa_passed": False,
        })
        artifacts = engine.get_step7_artifacts()
        assert artifacts.get("swarm_summary")["total"] == 10
        assert artifacts.get("qa_passed") is False

    def test_tdd_step_7_full_flow_with_qa(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(7)
        engine.complete_step(7, artifacts={
            "tdd_test_cases": "所有TDD测试用例代码",
            "swarm_summary": {"total": 5, "passed": 5, "failed": 0},
        })
        assert engine._step_states[7].status == "qa_review"
        record = engine.pass_qa(7)
        assert record.status == "passed"
        assert engine._step_states[7].status == "completed"

    def test_tdd_step_7_flow_with_qa_fail_and_retry(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(7)
        engine.complete_step(7, artifacts={"tdd_test_cases": "有缺陷的测试用例代码"})
        assert engine._step_states[7].status == "qa_review"
        engine.fail_qa(7, reason="测试用例错误", suggestions=["修复断言逻辑"])
        assert engine._step_states[7].status == "qa_review"
        engine.reset_step(7)
        engine.advance_step(7)
        engine.complete_step(7, artifacts={"tdd_test_cases": "修正后的测试用例代码"})
        record = engine.pass_qa(7)
        assert record.status == "passed"
        assert engine._step_states[7].status == "completed"

    def test_tdd_step_7_advance_from_step_6(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(6)
        engine.complete_step(6, artifacts={"tdd_plan": "TDD计划"})
        engine.pass_qa(6)
        engine.advance_step(7)
        assert engine.current_step == 7

    def test_tdd_step_7_cannot_advance_without_step_6_qa(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(6)
        engine.complete_step(6)
        with pytest.raises(ValueError):
            engine.advance_step(7)

    def test_tdd_step_7_complete_saves_artifacts(self):
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(7)
        engine.complete_step(7, artifacts={
            "tdd_test_cases": "测试代码",
            "spec_coverage": "100%",
        })
        artifacts = engine.get_step7_artifacts()
        assert artifacts.get("tdd_test_cases") == "测试代码"
        assert artifacts.get("spec_coverage") == "100%"


class TestTDDTestCaseAPI:
    """TDD测试用例 API 端点测试"""

    @pytest.mark.asyncio
    async def test_list_tdd_test_cases_empty(self, client, test_project, auth_headers):
        resp = await client.get(
            f"/api/v1/workflow/{test_project.id}/step6/test-cases",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["test_cases"] == []

    @pytest.mark.asyncio
    async def test_list_tdd_test_cases_with_data(self, client, db_session, test_project, auth_headers):
        for i in range(3):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=1,
                case_index=i,
                case_id=f"TC-{i:03d}",
                title=f"测试用例 {i}",
            )
            db_session.add(case)
        db_session.commit()
        resp = await client.get(
            f"/api/v1/workflow/{test_project.id}/step6/test-cases",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]["test_cases"]) == 3

    @pytest.mark.asyncio
    async def test_list_tdd_test_cases_by_round(self, client, db_session, test_project, auth_headers):
        for i in range(2):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=1,
                case_index=i,
                case_id=f"TC-R1-{i:03d}",
                title=f"第一轮 {i}",
            )
            db_session.add(case)
        for i in range(2):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=2,
                case_index=i,
                case_id=f"TC-R2-{i:03d}",
                title=f"第二轮 {i}",
            )
            db_session.add(case)
        db_session.commit()
        resp = await client.get(
            f"/api/v1/workflow/{test_project.id}/step6/test-cases?round_number=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        cases = data["data"]["test_cases"]
        assert len(cases) == 2
        for c in cases:
            assert c["round_number"] == 2

    @pytest.mark.asyncio
    async def test_tdd_test_cases_summary(self, client, db_session, test_project, auth_headers):
        for i in range(5):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=1,
                case_index=i,
                case_id=f"TC-{i:03d}",
                title=f"用例 {i}",
                qa_status="passed" if i < 3 else "failed",
            )
            db_session.add(case)
        db_session.commit()
        resp = await client.get(
            f"/api/v1/workflow/{test_project.id}/step6/test-cases/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        rounds = data["data"]["rounds"]
        assert len(rounds) >= 1
        r1 = next(r for r in rounds if r["round_number"] == 1)
        assert r1["total"] == 5
        assert r1["passed"] == 3
        assert r1["failed"] == 2

    @pytest.mark.asyncio
    async def test_tdd_test_cases_summary_multi_round(self, client, db_session, test_project, auth_headers):
        for rnd in range(1, 4):
            for i in range(2):
                case = TDDTestCase(
                    project_id=test_project.id,
                    round_number=rnd,
                    case_index=i,
                    case_id=f"TC-R{rnd}-{i:03d}",
                    title=f"第{rnd}轮用例{i}",
                    qa_status="passed",
                )
                db_session.add(case)
        db_session.commit()
        resp = await client.get(
            f"/api/v1/workflow/{test_project.id}/step6/test-cases/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]["rounds"]) == 3


class TestTDDPlanIntegration:
    """TDD测试用例计划与编写集成测试"""

    def test_tdd_plan_to_testcase_flow(self):
        """验证从第6步TDD计划到第7步测试用例编写的完整流程"""
        engine = WorkflowEngine(project_id="test-project")
        engine.advance_step(6)
        engine.complete_step(6, artifacts={
            "tdd_plan": "TDD测试用例编写计划",
            "plan_details": {
                "modules": ["用户模块", "订单模块", "支付模块"],
                "total_cases": 15,
                "coverage_requirement": "100%功能覆盖",
            },
        })
        record = engine.pass_qa(6)
        assert record.status == "passed"
        engine.advance_step(7)
        engine.complete_step(7, artifacts={
            "tdd_test_cases": "15个测试用例代码",
            "summary": {"total": 15, "passed": 15},
        })
        record = engine.pass_qa(7)
        assert record.status == "passed"
        engine.advance_step(8)
        assert engine.current_step == 8

    def test_multiple_tdd_rounds_with_iteration(self):
        """验证迭代修改闭环中TDD多轮改进"""
        engine = WorkflowEngine(project_id="test-project")
        for step_num in [2, 3, 4, 5, 6, 7]:
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={f"step{step_num}_output": "done"})
            engine.pass_qa(step_num)
        result = engine.user_dissatisfied("TDD用例需要扩展")
        assert result["reset_from_step"] == 3
        engine.advance_step(6)
        engine.complete_step(6, artifacts={"tdd_plan": "第二轮TDD计划"})
        engine.pass_qa(6)
        engine.advance_step(7)
        engine.complete_step(7, artifacts={"tdd_test_cases": "第二轮TDD用例"})
        engine.pass_qa(7)
        assert engine.current_step >= 8

    def test_tdd_plan_with_code_plan_dependency(self):
        """验证TDD计划与代码编写计划的依赖关系"""
        steps = get_default_steps()
        step8 = next(s for s in steps if s.step_number == 8)
        assert "tdd_test_cases" in step8.required_inputs
        assert "code_writing_plan" in step8.expected_outputs

    def test_tdd_step5_env_before_tdd(self):
        """验证开发环境搭建（第5步）在TDD计划（第6步）之前"""
        steps = get_default_steps()
        step5 = next(s for s in steps if s.step_number == 5)
        step6 = next(s for s in steps if s.step_number == 6)
        assert step5.step_number < step6.step_number
        assert step5.executor_role == "houfu"
        assert step6.executor_role == "haimei"


class TestTDDTestCaseEdgeCases:
    """TDD测试用例边界情况测试"""

    @pytest.mark.asyncio
    async def test_tdd_test_case_empty_title(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-EMPTY",
            title="",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        assert case.title == ""

    @pytest.mark.asyncio
    async def test_tdd_test_case_long_title(self, db_session, test_project):
        long_title = "A" * 500
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-LONG",
            title=long_title,
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        assert len(case.title) == 500

    @pytest.mark.asyncio
    async def test_tdd_test_case_missing_optional_fields(self, db_session, test_project):
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-OPT",
            title="仅必填字段测试",
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        assert case.description is None
        assert case.precondition is None
        assert case.test_steps is None
        assert case.expected_result is None
        assert case.priority is None

    @pytest.mark.asyncio
    async def test_tdd_test_case_max_round_number(self, db_session, test_project):
        for rnd in range(1, 6):
            case = TDDTestCase(
                project_id=test_project.id,
                round_number=rnd,
                case_index=0,
                case_id=f"TC-RND-{rnd}",
                title=f"第{rnd}轮测试",
            )
            db_session.add(case)
        db_session.commit()
        count = db_session.query(TDDTestCase).filter(
            TDDTestCase.project_id == test_project.id,
        ).count()
        assert count == 5

    @pytest.mark.asyncio
    async def test_tdd_test_case_large_metadata(self, db_session, test_project):
        large_meta = {"data": "x" * 10000}
        case = TDDTestCase(
            project_id=test_project.id,
            round_number=1,
            case_index=0,
            case_id="TC-LG-META",
            title="大元数据测试",
            metadata_json=large_meta,
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)
        assert len(case.metadata_json["data"]) == 10000


class TestCodePlanDimensions:
    """第八步 代码编写计划 - TDD关联的测试 (SRS 8.1.8)"""

    def test_code_plan_dimensions_count(self):
        assert len(CODE_PLAN_DIMENSIONS) == 3

    def test_code_plan_dimension_keys(self):
        keys = {d["key"] for d in CODE_PLAN_DIMENSIONS}
        expected = {"task_atomicity", "test_mapping", "dependency_correctness"}
        assert keys == expected

    def test_code_plan_task_atomicity(self):
        dim = next(d for d in CODE_PLAN_DIMENSIONS if d["key"] == "task_atomicity")
        assert "原子化" in dim["label"]

    def test_code_plan_test_mapping(self):
        dim = next(d for d in CODE_PLAN_DIMENSIONS if d["key"] == "test_mapping")
        assert "测试用例对应" in dim["label"]
        assert "一一对应" in dim["description"]

    def test_code_plan_dependency_correctness(self):
        dim = next(d for d in CODE_PLAN_DIMENSIONS if d["key"] == "dependency_correctness")
        assert "依赖关系" in dim["label"]
        assert "无循环" in dim["description"]


class TestTDDFullSwarmIntegration:
    """TDD完整蜂群集成测试 (SRS 8.1.7 + 8.3)"""

    def test_tdd_swarm_creation_for_step7(self):
        from app.services.swarm_service import SwarmService, SUPPORTED_SWARM_AGENTS
        service = SwarmService()
        swarm = service.create_swarm(
            project_id="proj-tdd",
            name="TDD测试用例编写蜂群",
            purpose="code_writing",
            step_number=7,
            manager_role="houfa",
        )
        assert swarm["purpose"] == "code_writing"
        assert swarm["step_number"] == 7
        assert swarm["manager_role"] == "houfa"

    def test_tdd_swarm_add_writer_agents(self):
        from app.services.swarm_service import SwarmService
        service = SwarmService()
        swarm = service.create_swarm("proj-tdd", "TDD蜂群", "code_writing", 7, "houfa")
        service.add_member(swarm["id"], agent_type="houfa", agent_id="hf-tdd-1")
        updated = service.add_member(swarm["id"], agent_type="houfa", agent_id="hf-tdd-2")
        assert len(updated["members"]) == 2

    def test_tdd_swarm_dispatch_tasks(self):
        from app.services.swarm_service import SwarmService
        service = SwarmService()
        swarm = service.create_swarm("proj-tdd", "TDD蜂群", "code_writing", 7, "houfa")
        service.add_member(swarm["id"], agent_type="houfa", agent_id="hf-1")
        service.add_member(swarm["id"], agent_type="houfa", agent_id="hf-2")
        tasks = [
            {"task_id": "tc-1", "name": "用户注册测试用例"},
            {"task_id": "tc-2", "name": "订单创建测试用例"},
            {"task_id": "tc-3", "name": "支付流程测试用例"},
        ]
        assignments = service.dispatch_tasks(swarm["id"], tasks)
        assert len(assignments) == 3

    def test_tdd_swarm_disband_after_completion(self):
        from app.services.swarm_service import SwarmService
        service = SwarmService()
        swarm = service.create_swarm("proj-tdd", "TDD蜂群", "code_writing", 7, "houfa")
        service.add_member(swarm["id"], agent_type="houfa", agent_id="hf-1")
        result = service.disband_swarm(swarm["id"])
        assert result["status"] == "disbanded"

    def test_tdd_swarm_supported_agents(self):
        from app.services.swarm_service import SUPPORTED_SWARM_AGENTS
        assert "houfa" in SUPPORTED_SWARM_AGENTS
        assert len(SUPPORTED_SWARM_AGENTS) >= 1

    def test_tdd_swarm_writer_agent_types(self):
        pass  # 已改为按名字查询，不再使用 WRITER_AGENT_TYPES

    def test_tdd_swarm_invalid_manager_raises(self):
        from app.services.swarm_service import SwarmService
        service = SwarmService()
        with pytest.raises(ValueError, match="只能建立代码编写蜂群"):
            service.create_swarm("proj-tdd", "test", "test_execution", 7, "houfa")
