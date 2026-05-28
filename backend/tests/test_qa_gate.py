"""v4.0 QA Gate Service Tests"""
import pytest
from app.services.qa_gate_service import QAGateService


class TestQAGateService:

    def test_inspection_dimensions_count(self):
        service = QAGateService()
        assert len(service.INSPECTION_DIMENSIONS) == 11

    def test_inspection_dimensions_keys(self):
        service = QAGateService()
        expected_keys = {
            "core_goal", "srs", "design", "dev_env", "tdd_plan",
            "tdd_code", "code_plan", "function_code", "test_report",
            "security_audit", "project_docs"
        }
        assert set(service.INSPECTION_DIMENSIONS.keys()) == expected_keys

    def test_srs_dimensions(self):
        service = QAGateService()
        dims = service.INSPECTION_DIMENSIONS["srs"]
        assert "完整性" in dims
        assert "一致性" in dims
        assert "可验证性" in dims
        assert "无歧义性" in dims

    def test_design_dimensions(self):
        service = QAGateService()
        dims = service.INSPECTION_DIMENSIONS["design"]
        assert "设计完整性" in dims
        assert "需求覆盖度" in dims
        assert "技术可行性" in dims
        assert "架构合理性" in dims

    def test_tdd_plan_dimensions(self):
        service = QAGateService()
        dims = service.INSPECTION_DIMENSIONS["tdd_plan"]
        assert "覆盖率" in dims
        assert "原子化程度" in dims
        assert "验收标准可量化性" in dims

    def test_code_plan_dimensions(self):
        service = QAGateService()
        dims = service.INSPECTION_DIMENSIONS["code_plan"]
        assert "任务原子化" in dims
        assert "测试用例对应完整性" in dims
        assert "依赖关系正确性" in dims

    def test_security_audit_dimensions(self):
        service = QAGateService()
        dims = service.INSPECTION_DIMENSIONS["security_audit"]
        assert "漏洞修复率" in dims
        assert "合规达标" in dims
        assert "渗透测试通过情况" in dims

    def test_inspect_pass(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="srs",
            project_id="proj-1",
            workflow_step_id=3,
        )
        assert record["status"] == "passed"
        assert len(record["review_dimensions"]) == 4

    def test_inspect_fail_with_reason(self):
        service = QAGateService()
        record = service.inspect(
            artifact_type="srs",
            project_id="proj-1",
            workflow_step_id=3,
            result="failed",
            reason="需求不完整，缺少非功能需求",
            suggestions=["补充非功能需求", "添加性能指标"],
        )
        assert record["status"] == "failed"
        assert "非功能需求" in record["problem_details"]
        assert len(record["fix_suggestions"]) == 2

    def test_rollback_creates_fail_record(self):
        service = QAGateService()
        record = service.rollback(
            task_id="task-1",
            project_id="proj-1",
            workflow_step_id=3,
            reason="代码质量不达标",
            suggestions=["重构模块", "补充单元测试"],
        )
        assert record["status"] == "failed"
        assert record["task_id"] == "task-1"

    def test_rollback_returns_suggestions(self):
        service = QAGateService()
        record = service.rollback(
            task_id="task-2",
            project_id="proj-1",
            workflow_step_id=7,
            reason="测试用例覆盖率不足",
            suggestions=["增加边界测试", "增加异常场景测试", "增加并发测试"],
        )
        assert len(record["fix_suggestions"]) == 3
        assert "覆盖率" in record["problem_details"]

    def test_invalid_artifact_type(self):
        service = QAGateService()
        with pytest.raises(ValueError, match="未知的产出类型"):
            service.inspect(artifact_type="unknown_type", project_id="p", workflow_step_id=1)

    def test_get_inspection_status(self):
        service = QAGateService()
        status = service.get_inspection_status(task_id="task-1")
        assert "task_id" in status
        assert "records_count" in status
        assert "latest_status" in status

    def test_multiple_inspections_same_task(self):
        service = QAGateService()
        service.inspect("srs", "proj-1", 3, result="failed", reason="第一次不合格")
        service.inspect("srs", "proj-1", 3, result="passed")
        status = service.get_inspection_status(task_id=None, step_id=3)
        assert status["records_count"] == 2
        assert status["latest_status"] == "passed"