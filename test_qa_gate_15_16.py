import pytest
import re
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch


STEP15_STEP_DEF = {
    "step_number": 15,
    "name": "海梅报告交付成果",
    "executor_role": "haimei",
    "supervisor_role": "haimei",
}

STEP16_STEP_DEF = {
    "step_number": 16,
    "name": "用户满意度确认与迭代",
    "executor_role": "haimei",
    "supervisor_role": "haimei",
}

QA_REQUIRED_STEPS = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14}

PROJECT_ID = "tdd_qa_gate_project_001"


def is_qa_required(step_number: int) -> bool:
    return step_number in QA_REQUIRED_STEPS


def build_step_context(step_def: dict, project_id: str = PROJECT_ID, **overrides) -> dict:
    context = {
        "project_id": project_id,
        "step_number": step_def["step_number"],
        "step_name": step_def["name"],
        "executor_role": step_def["executor_role"],
        "supervisor_role": step_def["supervisor_role"],
    }
    context.update(overrides)
    return context


def check_step15_qa_gate(context: dict) -> dict:
    """QA gate check for step 15: 海梅报告交付成果"""
    result = {
        "step": 15,
        "passed": True,
        "checks": [],
    }
    required_keys = ["deliverable_type", "deliverable_path", "review_status"]
    for key in required_keys:
        check = {
            "check": f"deliverable_{key}",
            "passed": context.get(key) is not None,
        }
        result["checks"].append(check)
        if not check["passed"]:
            result["passed"] = False
    if context.get("review_status") != "approved":
        result["checks"].append({
            "check": "review_status_approved",
            "passed": False,
        })
        result["passed"] = False
    return result


def check_step16_qa_gate(context: dict) -> dict:
    """QA gate check for step 16: 用户满意度确认与迭代"""
    result = {
        "step": 16,
        "passed": True,
        "checks": [],
    }
    required_keys = ["feedback_received", "satisfaction_level", "iteration_plan"]
    for key in required_keys:
        check = {
            "check": f"user_{key}",
            "passed": context.get(key) is not None,
        }
        result["checks"].append(check)
        if not check["passed"]:
            result["passed"] = False
    if context.get("satisfaction_level", 0) < 3:
        result["checks"].append({
            "check": "satisfaction_level_minimum",
            "passed": False,
        })
        result["passed"] = False
    return result


def run_full_qa_pipeline(project_steps: List[dict]) -> dict:
    """Run QA gate for all steps in a project pipeline."""
    results = {}
    all_passed = True
    for step in project_steps:
        step_num = step["step_number"]
        if is_qa_required(step_num):
            if step_num == 15:
                result = check_step15_qa_gate(step)
            elif step_num == 16:
                result = check_step16_qa_gate(step)
            else:
                result = {"step": step_num, "passed": True, "checks": []}
            results[step_num] = result
            if not result["passed"]:
                all_passed = False
    return {
        "project_id": PROJECT_ID,
        "steps_checked": sorted(results.keys()),
        "all_passed": all_passed,
        "step_results": results,
    }


def generate_qa_coverage_report(steps: List[dict], project_id: str = PROJECT_ID) -> dict:
    """Generate a QA coverage report for the full pipeline."""
    qa_required = {s["step_number"] for s in steps if is_qa_required(s["step_number"])}
    qa_covered = set()
    for s in steps:
        sn = s["step_number"]
        if is_qa_required(sn):
            if sn == 15:
                r = check_step15_qa_gate(s)
                if r["passed"]:
                    qa_covered.add(sn)
            elif sn == 16:
                r = check_step16_qa_gate(s)
                if r["passed"]:
                    qa_covered.add(sn)
            else:
                qa_covered.add(sn)
    uncovered = qa_required - qa_covered
    return {
        "project_id": project_id,
        "total_qa_steps": len(qa_required),
        "covered": len(qa_covered),
        "uncovered": sorted(uncovered),
        "coverage_pct": round(len(qa_covered) / len(qa_required) * 100, 1) if qa_required else 100.0,
        "all_covered": len(uncovered) == 0,
    }


class TestQAGateStep15:
    """QA gate tests for step 15: 海梅报告交付成果"""

    @pytest.fixture
    def valid_step15_context(self):
        return build_step_context(
            STEP15_STEP_DEF,
            deliverable_type="report",
            deliverable_path="/tmp/report.pdf",
            review_status="approved",
        )

    @pytest.fixture
    def invalid_step15_context_missing_deliverable(self):
        return build_step_context(
            STEP15_STEP_DEF,
            deliverable_type=None,
            deliverable_path="/tmp/report.pdf",
            review_status="approved",
        )

    @pytest.fixture
    def invalid_step15_context_not_approved(self):
        return build_step_context(
            STEP15_STEP_DEF,
            deliverable_type="report",
            deliverable_path="/tmp/report.pdf",
            review_status="pending",
        )

    def test_valid_deliverable_passes_qa(self, valid_step15_context):
        result = check_step15_qa_gate(valid_step15_context)
        assert result["passed"] is True

    def test_missing_deliverable_type_fails_qa(self, invalid_step15_context_missing_deliverable):
        result = check_step15_qa_gate(invalid_step15_context_missing_deliverable)
        assert result["passed"] is False
        assert any(not c["passed"] for c in result["checks"])

    def test_not_approved_fails_qa(self, invalid_step15_context_not_approved):
        result = check_step15_qa_gate(invalid_step15_context_not_approved)
        assert result["passed"] is False
        assert any(not c["passed"] for c in result["checks"])

    def test_all_context_keys_missing_fails(self):
        ctx = build_step_context(STEP15_STEP_DEF)
        result = check_step15_qa_gate(ctx)
        assert result["passed"] is False
        assert len([c for c in result["checks"] if not c["passed"]]) >= 3

    def test_edge_case_empty_deliverable_path(self):
        ctx = build_step_context(
            STEP15_STEP_DEF,
            deliverable_type="report",
            deliverable_path="",
            review_status="approved",
        )
        result = check_step15_qa_gate(ctx)
        assert result["passed"] is True


class TestQAGateStep16:
    """QA gate tests for step 16: 用户满意度确认与迭代"""

    @pytest.fixture
    def valid_step16_context(self):
        return build_step_context(
            STEP16_STEP_DEF,
            feedback_received=True,
            satisfaction_level=5,
            iteration_plan="iteration_v2.md",
        )

    @pytest.fixture
    def low_satisfaction_context(self):
        return build_step_context(
            STEP16_STEP_DEF,
            feedback_received=True,
            satisfaction_level=2,
            iteration_plan="iteration_v2.md",
        )

    @pytest.fixture
    def missing_feedback_context(self):
        return build_step_context(
            STEP16_STEP_DEF,
            feedback_received=None,
            satisfaction_level=5,
            iteration_plan="iteration_v2.md",
        )

    def test_valid_feedback_passes_qa(self, valid_step16_context):
        result = check_step16_qa_gate(valid_step16_context)
        assert result["passed"] is True

    def test_low_satisfaction_fails_qa(self, low_satisfaction_context):
        result = check_step16_qa_gate(low_satisfaction_context)
        assert result["passed"] is False

    def test_missing_feedback_fails_qa(self, missing_feedback_context):
        result = check_step16_qa_gate(missing_feedback_context)
        assert result["passed"] is False

    def test_boundary_satisfaction_level_3(self):
        ctx = build_step_context(
            STEP16_STEP_DEF,
            feedback_received=True,
            satisfaction_level=3,
            iteration_plan="plan.md",
        )
        result = check_step16_qa_gate(ctx)
        assert result["passed"] is True

    def test_boundary_satisfaction_level_0(self):
        ctx = build_step_context(
            STEP16_STEP_DEF,
            feedback_received=True,
            satisfaction_level=0,
            iteration_plan="plan.md",
        )
        result = check_step16_qa_gate(ctx)
        assert result["passed"] is False


class TestQAGatePipeline:
    """Integration tests for the full QA pipeline."""

    @pytest.fixture
    def full_valid_pipeline(self):
        steps = []
        for sn in range(1, 17):
            step = {"step_number": sn}
            if sn == 15:
                step.update(
                    deliverable_type="report",
                    deliverable_path="/tmp/r.pdf",
                    review_status="approved",
                )
            elif sn == 16:
                step.update(
                    feedback_received=True,
                    satisfaction_level=5,
                    iteration_plan="plan.md",
                )
            steps.append(step)
        return steps

    @pytest.fixture
    def pipeline_with_failing_step15(self):
        steps = []
        for sn in range(1, 17):
            step = {"step_number": sn}
            if sn == 15:
                step.update(
                    deliverable_type=None,
                    deliverable_path="/tmp/r.pdf",
                    review_status="approved",
                )
            elif sn == 16:
                step.update(
                    feedback_received=True,
                    satisfaction_level=5,
                    iteration_plan="plan.md",
                )
            steps.append(step)
        return steps

    @patch(f"{__name__}.QA_REQUIRED_STEPS", {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16})
    def test_full_pipeline_all_passes(self, full_valid_pipeline):
        result = run_full_qa_pipeline(full_valid_pipeline)
        assert result["all_passed"] is True
        assert 15 in result["step_results"]
        assert 16 in result["step_results"]

    @patch(f"{__name__}.QA_REQUIRED_STEPS", {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16})
    def test_pipeline_with_failing_step(self, pipeline_with_failing_step15):
        result = run_full_qa_pipeline(pipeline_with_failing_step15)
        assert result["all_passed"] is False
        assert result["step_results"][15]["passed"] is False
        assert result["step_results"][16]["passed"] is True

    def test_non_qa_steps_ignored(self):
        steps = [{"step_number": 1}, {"step_number": 10}, {"step_number": 13}]
        result = run_full_qa_pipeline(steps)
        assert result["all_passed"] is True
        assert len(result["step_results"]) == 0

    def test_empty_pipeline(self):
        result = run_full_qa_pipeline([])
        assert result["all_passed"] is True
        assert result["step_results"] == {}


class TestQACoverageReport:
    """Tests for QA coverage report generation."""

    @pytest.fixture
    def all_steps_with_valid_qa(self):
        steps = []
        for sn in range(1, 17):
            step = {"step_number": sn}
            if sn == 15:
                step.update(
                    deliverable_type="report",
                    deliverable_path="/tmp/r.pdf",
                    review_status="approved",
                )
            elif sn == 16:
                step.update(
                    feedback_received=True,
                    satisfaction_level=5,
                    iteration_plan="plan.md",
                )
            steps.append(step)
        return steps

    @pytest.fixture
    def steps_with_uncovered_step15(self):
        steps = []
        for sn in range(1, 17):
            step = {"step_number": sn}
            if sn == 15:
                step.update(
                    deliverable_type=None,
                    deliverable_path=None,
                    review_status="pending",
                )
            elif sn == 16:
                step.update(
                    feedback_received=True,
                    satisfaction_level=5,
                    iteration_plan="plan.md",
                )
            steps.append(step)
        return steps

    @patch(f"{__name__}.QA_REQUIRED_STEPS", {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16})
    def test_full_coverage(self, all_steps_with_valid_qa):
        report = generate_qa_coverage_report(all_steps_with_valid_qa)
        assert report["all_covered"] is True
        assert report["coverage_pct"] == 100.0

    @patch(f"{__name__}.QA_REQUIRED_STEPS", {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16})
    def test_partial_coverage(self, steps_with_uncovered_step15):
        report = generate_qa_coverage_report(steps_with_uncovered_step15)
        assert report["all_covered"] is False
        assert 15 in report["uncovered"]
        assert report["coverage_pct"] < 100.0

    def test_no_qa_steps(self):
        steps = [{"step_number": 1}, {"step_number": 10}]
        report = generate_qa_coverage_report(steps)
        assert report["all_covered"] is True
        assert report["coverage_pct"] == 100.0

    @patch(f"{__name__}.QA_REQUIRED_STEPS", {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16})
    def test_project_scoped_qa_coverage_negative(self):
        steps_qa_ok = []
        for sn in range(1, 17):
            step = {"step_number": sn}
            if sn == 15:
                step.update(
                    deliverable_type="report",
                    deliverable_path="/tmp/r.pdf",
                    review_status="approved",
                )
            elif sn == 16:
                step.update(
                    feedback_received=True,
                    satisfaction_level=5,
                    iteration_plan="plan.md",
                )
            steps_qa_ok.append(step)

        report_default = generate_qa_coverage_report(steps_qa_ok)
        assert report_default["project_id"] == PROJECT_ID
        assert report_default["all_covered"] is True

        other_steps_deficient = [{"step_number": s["step_number"]} for s in steps_qa_ok]
        report_other = generate_qa_coverage_report(other_steps_deficient, project_id="other_project_002")
        assert report_other["project_id"] == "other_project_002"
        assert report_other["all_covered"] is False
        assert report_other["coverage_pct"] < 100.0


class TestConcurrencyAndStress:
    """Concurrency, stress, and large-volume tests."""

    def test_concurrent_qa_checks(self):
        contexts = []
        for i in range(20):
            if i % 4 == 0:
                # Step 15 with missing deliverable_type → should fail
                ctx = build_step_context(
                    STEP15_STEP_DEF,
                    deliverable_type=None,
                    deliverable_path=f"/tmp/r_{i}.pdf",
                    review_status="approved",
                )
            elif i % 4 == 1:
                # Step 15 with valid data → should pass
                ctx = build_step_context(
                    STEP15_STEP_DEF,
                    deliverable_type="report",
                    deliverable_path=f"/tmp/r_{i}.pdf",
                    review_status="approved",
                )
            elif i % 4 == 2:
                # Step 16 with low satisfaction → should fail
                ctx = build_step_context(
                    STEP16_STEP_DEF,
                    feedback_received=True,
                    satisfaction_level=1,
                    iteration_plan="plan.md",
                )
            else:
                # Step 16 with valid data → should pass
                ctx = build_step_context(
                    STEP16_STEP_DEF,
                    feedback_received=True,
                    satisfaction_level=5,
                    iteration_plan="plan.md",
                )
            contexts.append(ctx)

        async def run_all():
            async def check_one(ctx):
                if ctx["step_number"] == 15:
                    return check_step15_qa_gate(ctx)
                return check_step16_qa_gate(ctx)
            return await asyncio.gather(*[check_one(ctx) for ctx in contexts])

        results = asyncio.run(run_all())
        passed_count = sum(1 for r in results if r["passed"])
        failed_count = sum(1 for r in results if not r["passed"])
        assert passed_count + failed_count == 20
        assert passed_count > 0
        assert failed_count > 0

    def test_large_volume_pipeline(self):
        steps = []
        for i in range(1000):
            sn = (i % 16) + 1
            step = {"step_number": sn}
            if sn == 15:
                step.update(
                    deliverable_type="report",
                    deliverable_path=f"/tmp/r_{i}.pdf",
                    review_status="approved",
                )
            elif sn == 16:
                step.update(
                    feedback_received=True,
                    satisfaction_level=4,
                    iteration_plan=f"plan_{i}.md",
                )
            steps.append(step)
        result = run_full_qa_pipeline(steps)
        assert result["all_passed"] is True
        assert len(result["step_results"]) > 0

    def test_boundary_step_numbers(self):
        test_steps = [
            {"step_number": 0},
            {"step_number": 17},
            {"step_number": 100},
            {"step_number": -1},
        ]
        for step in test_steps:
            result = run_full_qa_pipeline([step])
            assert result["all_passed"] is True


class TestEdgeCases:
    """Edge case tests."""

    def test_missing_optional_fields(self):
        ctx = build_step_context(
            STEP15_STEP_DEF,
            deliverable_type="report",
            deliverable_path="/tmp/r.pdf",
            review_status="approved",
        )
        result = check_step15_qa_gate(ctx)
        assert result["passed"] is True

    def test_unicode_deliverable_path(self):
        ctx = build_step_context(
            STEP15_STEP_DEF,
            deliverable_type="报告",
            deliverable_path="文档/海梅报告.pdf",
            review_status="approved",
        )
        result = check_step15_qa_gate(ctx)
        assert result["passed"] is True

    @pytest.mark.parametrize("satisfaction", [3, 4, 5, 10, -1, 0])
    def test_parametrized_boundary_satisfaction(self, satisfaction):
        ctx = build_step_context(
            STEP16_STEP_DEF,
            feedback_received=True,
            satisfaction_level=satisfaction,
            iteration_plan="plan.md",
        )
        result = check_step16_qa_gate(ctx)
        if satisfaction >= 3:
            assert result["passed"] is True
        else:
            assert result["passed"] is False
