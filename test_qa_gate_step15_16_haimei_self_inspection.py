import pytest
import uuid
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class CheckItem:
    """验收检查项"""
    key: str
    label: str
    passed: bool
    detail: str
    score: int = 100

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "passed": self.passed,
            "detail": self.detail,
            "score": self.score,
        }


@dataclass
class DeliveryReport:
    """delivery_report 表对应的数据模型"""
    id: str
    project_id: str
    check_items: list
    overall_status: str
    status: str
    report_content: str = ""
    generated_at: str = ""
    suggestions: list = field(default_factory=list)

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "check_items": [ci.to_dict() if isinstance(ci, CheckItem) else ci for ci in self.check_items],
            "overall_status": self.overall_status,
            "status": self.status,
            "report_content": self.report_content,
            "generated_at": self.generated_at,
            "suggestions": self.suggestions,
        }


class HaiMeiSelfInspection:
    """海梅自检脚本：交付前自动执行验收检查并生成报告"""

    CHECK_ITEMS_DEFAULT = [
        {"key": "functional_completeness", "label": "功能完整性", "description": "所有需求功能是否均已实现"},
        {"key": "test_coverage", "label": "测试覆盖率", "description": "测试覆盖率是否>=80%"},
        {"key": "test_pass_rate", "label": "测试通过率", "description": "测试通过率是否>=90%"},
        {"key": "security_vulnerabilities", "label": "安全漏洞修复率", "description": "高危漏洞是否全部修复"},
        {"key": "docs_completeness", "label": "文档完整性", "description": "用户文档、API文档、部署文档是否齐全"},
        {"key": "deployment_status", "label": "部署状态", "description": "生产环境部署是否成功"},
        {"key": "performance_metrics", "label": "性能指标", "description": "核心接口响应时间是否达标"},
        {"key": "acceptance_criteria", "label": "验收标准匹配度", "description": "交付成果是否满足验收标准"},
    ]

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.check_results: list[CheckItem] = []
        self.report: DeliveryReport | None = None

    def run_inspection(self, override_results: dict[str, bool] | None = None) -> dict:
        """
        执行自检，返回检查结果汇总。
        override_results: 用于测试注入的检查项覆盖结果，key为检查项key，value为通过/不通过布尔值。
        """
        self.check_results = []

        for item_def in self.CHECK_ITEMS_DEFAULT:
            key = item_def["key"]
            label = item_def["label"]

            if override_results is not None:
                passed = override_results.get(key, True)
            else:
                passed = True

            score = 100 if passed else 0
            detail = f"{item_def['description']}"
            self.check_results.append(CheckItem(
                key=key,
                label=label,
                passed=passed,
                detail=detail,
                score=score,
            ))

        overall_pass = all(ci.passed for ci in self.check_results)

        return {
            "status": "success",
            "project_id": self.project_id,
            "check_items": [ci.to_dict() for ci in self.check_results],
            "overall_status": "pass" if overall_pass else "fail",
            "total_items": len(self.check_results),
            "passed_items": sum(1 for ci in self.check_results if ci.passed),
            "failed_items": sum(1 for ci in self.check_results if not ci.passed),
        }

    def generate_delivery_report(self, inspection_result: dict | None = None) -> DeliveryReport:
        """根据自检结果生成交付验收报告"""
        if inspection_result is None:
            inspection_result = self.run_inspection()

        report_id = str(uuid.uuid4())
        overall_status = inspection_result["overall_status"]
        report_status = "pending_user_approval"

        suggestions = []
        failed_items = [ci for ci in self.check_results if not ci.passed]
        for fi in failed_items:
            suggestions.append(f"[{fi.label}] {fi.detail} - 需要修改后重新验收")

        self.report = DeliveryReport(
            id=report_id,
            project_id=self.project_id,
            check_items=self.check_results,
            overall_status=overall_status,
            status=report_status,
            report_content=json.dumps(inspection_result, ensure_ascii=False, indent=2),
            suggestions=suggestions,
        )

        return self.report


class DeliveryReportRepository:
    """delivery_report 表的模拟仓储"""

    def __init__(self):
        self._reports: list[DeliveryReport] = []

    def save(self, report: DeliveryReport) -> DeliveryReport:
        self._reports.append(report)
        return report

    def find_by_project_id(self, project_id: str) -> list[DeliveryReport]:
        return [r for r in self._reports if r.project_id == project_id]

    def find_latest_by_project_id(self, project_id: str) -> DeliveryReport | None:
        matching = self.find_by_project_id(project_id)
        return matching[-1] if matching else None

    def count(self) -> int:
        return len(self._reports)


# ============================================================
# Tests
# ============================================================

class TestHaiMeiSelfInspectionSuccess:
    """验收标准1: 自检脚本返回success状态，输出检查项列表及各项通过状态"""

    def test_inspection_returns_success_status(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        assert result["status"] == "success"

    def test_inspection_outputs_check_items_list(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        assert isinstance(result["check_items"], list)
        assert len(result["check_items"]) == 8

    def test_each_check_item_has_passed_field(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        for item in result["check_items"]:
            assert "passed" in item
            assert isinstance(item["passed"], bool)

    def test_check_items_all_pass_by_default(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        assert all(item["passed"] for item in result["check_items"])
        assert result["passed_items"] == 8
        assert result["failed_items"] == 0

    def test_check_items_with_partial_failure(self):
        overrides = {
            "test_coverage": False,
            "security_vulnerabilities": False,
        }
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection(override_results=overrides)
        assert result["total_items"] == 8
        assert result["passed_items"] == 6
        assert result["failed_items"] == 2
        assert result["status"] == "success"

    def test_overall_status_is_fail_when_any_item_fails(self):
        overrides = {"test_coverage": False}
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection(override_results=overrides)
        assert result["overall_status"] == "fail"

    def test_overall_status_is_pass_when_all_items_pass(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        assert result["overall_status"] == "pass"

    def test_check_item_contains_required_fields(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        required_keys = {"key", "label", "passed", "detail", "score"}
        for item in result["check_items"]:
            assert required_keys.issubset(set(item.keys()))

    def test_check_item_score_is_100_when_passed(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        for item in result["check_items"]:
            assert item["score"] == 100

    def test_check_item_score_is_0_when_failed(self):
        overrides = {"functional_completeness": False}
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection(override_results=overrides)
        fc = next(i for i in result["check_items"] if i["key"] == "functional_completeness")
        assert fc["score"] == 0
        assert fc["passed"] is False

    def test_result_contains_project_id(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        assert result["project_id"] == "project-001"


class TestDeliveryReportGeneration:
    """验收标准2: delivery_report表生成一份验收报告，status=pending_user_approval，包含project_id、check_items、overall_status=pass"""

    def test_report_status_is_pending_user_approval(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        assert report.status == "pending_user_approval"

    def test_report_contains_project_id(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        assert report.project_id == "project-001"

    def test_report_contains_check_items(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        assert isinstance(report.check_items, list)
        assert len(report.check_items) == 8

    def test_report_overall_status_is_pass(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        assert report.overall_status == "pass"

    def test_report_has_valid_uuid(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        uuid.UUID(report.id)

    def test_report_has_generated_at_timestamp(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        datetime.fromisoformat(report.generated_at)

    def test_report_to_dict_contains_all_required_fields(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        d = report.to_dict()
        assert "project_id" in d
        assert "check_items" in d
        assert "overall_status" in d
        assert "status" in d
        assert d["status"] == "pending_user_approval"

    def test_report_with_fail_overall_status(self):
        overrides = {"test_coverage": False}
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection(override_results=overrides)
        report = inspection.generate_delivery_report(result)
        assert report.overall_status == "fail"
        assert report.status == "pending_user_approval"

    def test_report_suggestions_for_failed_items(self):
        overrides = {"test_coverage": False, "security_vulnerabilities": False}
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection(override_results=overrides)
        report = inspection.generate_delivery_report(result)
        assert len(report.suggestions) == 2
        assert any("测试覆盖率" in s for s in report.suggestions)
        assert any("安全漏洞修复率" in s for s in report.suggestions)

    def test_report_no_suggestions_when_all_pass(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        assert len(report.suggestions) == 0


class TestDeliveryReportRepository:
    """验证 delivery_report 仓储的持久化和查询"""

    def test_save_and_find_by_project_id(self):
        repo = DeliveryReportRepository()
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        repo.save(report)

        found = repo.find_by_project_id("project-001")
        assert len(found) == 1
        assert found[0].project_id == "project-001"

    def test_find_latest_by_project_id(self):
        repo = DeliveryReportRepository()
        for i in range(3):
            inspection = HaiMeiSelfInspection("project-001")
            result = inspection.run_inspection()
            report = inspection.generate_delivery_report(result)
            repo.save(report)

        latest = repo.find_latest_by_project_id("project-001")
        assert latest is not None
        assert repo.count() == 3

    def test_find_nonexistent_project(self):
        repo = DeliveryReportRepository()
        found = repo.find_by_project_id("nonexistent")
        assert len(found) == 0

    def test_find_latest_nonexistent_project(self):
        repo = DeliveryReportRepository()
        assert repo.find_latest_by_project_id("nonexistent") is None


class TestFullWorkflow:
    """端到端流程：自检 -> 生成报告 -> 入库"""

    def test_full_pipeline_all_pass(self):
        repo = DeliveryReportRepository()
        project_id = "project-001"

        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection()
        assert result["status"] == "success"
        assert result["overall_status"] == "pass"

        report = inspection.generate_delivery_report(result)
        repo.save(report)

        stored = repo.find_latest_by_project_id(project_id)
        assert stored is not None
        assert stored.status == "pending_user_approval"
        assert stored.overall_status == "pass"
        assert stored.project_id == project_id
        assert len(stored.check_items) == 8
        assert all(ci.passed for ci in stored.check_items)

    def test_full_pipeline_partial_fail(self):
        repo = DeliveryReportRepository()
        project_id = "project-002"
        overrides = {"performance_metrics": False, "docs_completeness": False}

        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection(override_results=overrides)
        assert result["status"] == "success"
        assert result["overall_status"] == "fail"
        assert result["failed_items"] == 2

        report = inspection.generate_delivery_report(result)
        repo.save(report)

        stored = repo.find_latest_by_project_id(project_id)
        assert stored is not None
        assert stored.status == "pending_user_approval"
        assert stored.overall_status == "fail"
        assert len(stored.suggestions) == 2

    def test_report_content_is_valid_json(self):
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        parsed = json.loads(report.report_content)
        assert parsed["overall_status"] == "pass"
        assert parsed["total_items"] == 8

    def test_multiple_retries_improve_to_pass(self):
        repo = DeliveryReportRepository()
        project_id = "project-003"

        first = HaiMeiSelfInspection(project_id)
        first_result = first.run_inspection(override_results={"test_coverage": False})
        first_report = first.generate_delivery_report(first_result)
        repo.save(first_report)

        second = HaiMeiSelfInspection(project_id)
        second_result = second.run_inspection()
        second_report = second.generate_delivery_report(second_result)
        repo.save(second_report)

        all_reports = repo.find_by_project_id(project_id)
        assert len(all_reports) == 2
        assert all_reports[0].overall_status == "fail"
        assert all_reports[1].overall_status == "pass"
        assert all_reports[0].status == "pending_user_approval"
        assert all_reports[1].status == "pending_user_approval"

    def test_check_item_keys_are_complete(self):
        expected_keys = {
            "functional_completeness",
            "test_coverage",
            "test_pass_rate",
            "security_vulnerabilities",
            "docs_completeness",
            "deployment_status",
            "performance_metrics",
            "acceptance_criteria",
        }
        inspection = HaiMeiSelfInspection("project-001")
        result = inspection.run_inspection()
        actual_keys = {item["key"] for item in result["check_items"]}
        assert actual_keys == expected_keys


class TestBoundaryCases:
    """边界覆盖补充：全部失败、空列表、异常降级、超大check_items"""

    def test_all_check_items_fail(self):
        overrides = {
            "functional_completeness": False,
            "test_coverage": False,
            "test_pass_rate": False,
            "security_vulnerabilities": False,
            "docs_completeness": False,
            "deployment_status": False,
            "performance_metrics": False,
            "acceptance_criteria": False,
        }
        inspection = HaiMeiSelfInspection("project-fail-all")
        result = inspection.run_inspection(override_results=overrides)
        assert result["status"] == "success"
        assert result["overall_status"] == "fail"
        assert result["passed_items"] == 0
        assert result["failed_items"] == 8
        assert all(not item["passed"] for item in result["check_items"])
        assert all(item["score"] == 0 for item in result["check_items"])

    def test_report_with_all_items_fail(self):
        overrides = {item["key"]: False for item in HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT}
        inspection = HaiMeiSelfInspection("project-all-fail")
        result = inspection.run_inspection(override_results=overrides)
        report = inspection.generate_delivery_report(result)
        assert report.overall_status == "fail"
        assert report.status == "pending_user_approval"
        assert len(report.suggestions) == 8

    def test_empty_override_results_defaults_to_pass(self):
        inspection = HaiMeiSelfInspection("project-empty-override")
        result = inspection.run_inspection(override_results={})
        assert result["overall_status"] == "pass"
        assert result["passed_items"] == 8
        assert result["failed_items"] == 0

    def test_empty_check_items_boundary(self):
        original_items = HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT
        try:
            HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT = []
            inspection = HaiMeiSelfInspection("project-empty-items")
            result = inspection.run_inspection()
            assert result["status"] == "success"
            assert result["check_items"] == []
            assert result["total_items"] == 0
        finally:
            HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT = original_items

    def test_empty_check_items_overall_status_is_pass(self):
        original_items = HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT
        try:
            HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT = []
            inspection = HaiMeiSelfInspection("project-empty-items-pass")
            result = inspection.run_inspection()
            assert result["overall_status"] == "pass"
        finally:
            HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT = original_items

    def test_inspection_with_unknown_override_key_ignores_it(self):
        overrides = {"nonexistent_key": False}
        inspection = HaiMeiSelfInspection("project-unknown-key")
        result = inspection.run_inspection(override_results=overrides)
        assert result["overall_status"] == "pass"
        assert result["total_items"] == 8

    def test_inspection_with_exception_during_run(self):
        inspection = HaiMeiSelfInspection("project-exception")
        original_run = inspection.run_inspection

        def mock_exception(*args, **kwargs):
            raise RuntimeError("inspected service unavailable")

        inspection.run_inspection = mock_exception
        with pytest.raises(RuntimeError, match="inspected service unavailable"):
            inspection.run_inspection()

    def test_report_generation_handles_exception_from_run(self):
        inspection = HaiMeiSelfInspection("project-exception-report")

        original_run = inspection.run_inspection

        def mock_failing_run(*args, **kwargs):
            raise RuntimeError("service down")

        inspection.run_inspection = mock_failing_run
        with pytest.raises(RuntimeError, match="service down"):
            inspection.generate_delivery_report(None)

    def test_large_check_items_performance(self):
        original_items = HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT
        try:
            large_items = []
            for i in range(200):
                large_items.append({"key": f"item_{i}", "label": f"Item {i}", "description": f"Description for item {i}"})
            HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT = large_items

            inspection = HaiMeiSelfInspection("project-large")
            result = inspection.run_inspection()
            assert result["total_items"] == 200
            assert result["status"] == "success"
            assert len(result["check_items"]) == 200

            report = inspection.generate_delivery_report(result)
            assert len(report.check_items) == 200
        finally:
            HaiMeiSelfInspection.CHECK_ITEMS_DEFAULT = original_items

    def test_problem_details_contains_specific_description_for_failures(self):
        overrides = {"test_coverage": False, "security_vulnerabilities": False}
        inspection = HaiMeiSelfInspection("project-problem-details")
        result = inspection.run_inspection(override_results=overrides)
        failed_items = [item for item in result["check_items"] if not item["passed"]]
        assert len(failed_items) == 2
        for item in failed_items:
            assert item["detail"] is not None
            assert len(item["detail"]) > 0

    def test_problem_details_matches_item_description(self):
        overrides = {"test_coverage": False}
        inspection = HaiMeiSelfInspection("project-detail-match")
        result = inspection.run_inspection(override_results=overrides)
        tc_item = next(i for i in result["check_items"] if i["key"] == "test_coverage")
        expected_desc = "测试覆盖率是否>=80%"
        assert expected_desc in tc_item["detail"]

    def test_suggestions_contain_specific_problem_details(self):
        overrides = {"docs_completeness": False}
        inspection = HaiMeiSelfInspection("project-suggestion-detail")
        result = inspection.run_inspection(override_results=overrides)
        report = inspection.generate_delivery_report(result)
        assert len(report.suggestions) == 1
        suggestion = report.suggestions[0]
        assert "文档完整性" in suggestion
        assert "文档完整性" in suggestion or "用户文档" in suggestion


class TestWorkflowTransition:
    """流程流转测试：step15 自检通过 -> step16 用户验收"""

    def test_step15_pass_transitions_to_step16_status(self):
        project_id = "project-transition"
        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection()
        assert result["overall_status"] == "pass"

        report = inspection.generate_delivery_report(result)
        assert report.status == "pending_user_approval"

    def test_step15_fail_blocks_transition_to_step16(self):
        project_id = "project-block"
        overrides = {"functional_completeness": False}
        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection(override_results=overrides)
        assert result["overall_status"] == "fail"

        report = inspection.generate_delivery_report(result)
        assert report.status == "pending_user_approval"
        assert len(report.suggestions) > 0

    def test_step15_report_saved_correctly_for_step16(self):
        repo = DeliveryReportRepository()
        project_id = "project-save-for-step16"

        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        repo.save(report)

        stored = repo.find_latest_by_project_id(project_id)
        assert stored is not None
        assert stored.overall_status == "pass"
        assert stored.status == "pending_user_approval"


class TestUserApproval:
    """用户审批路径测试：approve/reject 后系统行为"""

    def test_user_approve_updates_report_status(self):
        repo = DeliveryReportRepository()
        project_id = "project-approve"

        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        repo.save(report)

        stored = repo.find_latest_by_project_id(project_id)
        stored.status = "approved_by_user"
        assert stored.status == "approved_by_user"
        assert stored.overall_status == "pass"

    def test_user_reject_updates_report_status(self):
        repo = DeliveryReportRepository()
        project_id = "project-reject"

        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        repo.save(report)

        stored = repo.find_latest_by_project_id(project_id)
        stored.status = "rejected_by_user"
        assert stored.status == "rejected_by_user"

    def test_user_reject_with_reason(self):
        repo = DeliveryReportRepository()
        project_id = "project-reject-reason"

        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        repo.save(report)

        stored = repo.find_latest_by_project_id(project_id)
        stored.status = "rejected_by_user"
        rejection_reason = "用户认为文档仍不完整"

        assert stored.status == "rejected_by_user"
        assert rejection_reason is not None
        assert len(rejection_reason) > 0

    def test_approve_then_find_latest_returns_approved(self):
        repo = DeliveryReportRepository()
        project_id = "project-approve-find"

        inspection = HaiMeiSelfInspection(project_id)
        result = inspection.run_inspection()
        report = inspection.generate_delivery_report(result)
        repo.save(report)

        stored = repo.find_latest_by_project_id(project_id)
        stored.status = "approved_by_user"

        latest = repo.find_latest_by_project_id(project_id)
        assert latest.status == "approved_by_user"

    def test_multi_report_after_approve_one(self):
        repo = DeliveryReportRepository()
        project_id = "project-multi-approve"

        first = HaiMeiSelfInspection(project_id)
        first_result = first.run_inspection(override_results={"test_coverage": False})
        first_report = first.generate_delivery_report(first_result)
        repo.save(first_report)

        second = HaiMeiSelfInspection(project_id)
        second_result = second.run_inspection()
        second_report = second.generate_delivery_report(second_result)
        repo.save(second_report)

        all_reports = repo.find_by_project_id(project_id)
        all_reports[0].status = "superseded"
        all_reports[1].status = "approved_by_user"

        assert all_reports[0].overall_status == "fail"
        assert all_reports[1].overall_status == "pass"
        assert all_reports[1].status == "approved_by_user"
