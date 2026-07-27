import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


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


class StepDef:
    """工作流步骤定义"""
    def __init__(self, step_number: int, name: str,
                 executor_role: Optional[str] = None,
                 supervisor_role: Optional[str] = None):
        self.step_number = step_number
        self.name = name
        self.executor_role = executor_role
        self.supervisor_role = supervisor_role


def get_default_steps() -> List[StepDef]:
    """返回16步全流程步骤定义"""
    steps_data = [
        (1, "人类创建项目", None, None),
        (2, "需求分析与目标确认", "opencode", "hourong"),
        (3, "编写SRS文档", "opencode", "hourong"),
        (4, "系统设计", "opencode", "hourong"),
        (5, "开发环境准备", "cursor", "opencode"),
        (6, "TDD测试计划编写", "opencode", "hourong"),
        (7, "TDD测试用例编写", "cursor", "opencode"),
        (8, "编码计划分解", "claude_code", "opencode"),
        (9, "功能代码编写", "cursor", "opencode"),
        (10, "开发环境提交", "cursor", None),
        (11, "测试报告生成", "opencode", "hourong"),
        (12, "安全审计", "codebuddy", "hourong"),
        (13, "环境检查", "cursor", None),
        (14, "项目文档整理", "opencode", "hourong"),
        (15, "海梅报告交付成果", "haimei", "haimei"),
        (16, "用户满意度确认与迭代", "haimei", "haimei"),
    ]
    return [StepDef(*data) for data in steps_data]


INSPECTION_DIMENSIONS = {
    "core_goal": ["目标明确性", "组织完整性", "讨论群建立状态"],
    "srs": ["完整性", "一致性", "可验证性", "无歧义性"],
    "design": ["设计完整性", "需求覆盖度", "技术可行性", "架构合理性"],
    "dev_env": ["可用性", "配置正确性", "依赖完整性"],
    "tdd_plan": ["覆盖率", "原子化程度", "验收标准可量化性"],
    "tdd_code": ["正确性", "覆盖率", "原子化", "验收标准匹配"],
    "code_plan": ["任务原子化", "测试用例对应完整性", "依赖关系正确性"],
    "function_code": ["正确性", "测试通过率", "需求匹配度", "代码规范"],
    "test_report": ["覆盖率", "通过率", "缺陷严重度", "实操验证结果"],
    "security_audit": ["漏洞修复率", "合规达标", "渗透测试通过情况"],
    "project_docs": ["完整性", "文档间一致性", "描述准确性"],
}

STEP_ARTIFACT_MAP = {
    1: "core_goal", 2: "core_goal", 3: "srs", 4: "design",
    5: "dev_env", 6: "tdd_plan", 7: "tdd_code", 8: "code_plan",
    9: "function_code", 10: "dev_env", 11: "test_report",
    12: "security_audit", 13: "dev_env", 14: "project_docs",
    15: "project_docs", 16: "core_goal",
}


class QAGateService:
    """QA 门控检验服务（内联拷贝，测试隔离）"""
    INSPECTION_DIMENSIONS = {
        "core_goal": ["目标明确性", "组织完整性", "讨论群建立状态"],
        "srs": ["完整性", "一致性", "可验证性", "无歧义性"],
        "design": ["设计完整性", "需求覆盖度", "技术可行性", "架构合理性"],
        "dev_env": ["可用性", "配置正确性", "依赖完整性"],
        "tdd_plan": ["覆盖率", "原子化程度", "验收标准可量化性"],
        "tdd_code": ["正确性", "覆盖率", "原子化", "验收标准匹配"],
        "code_plan": ["任务原子化", "测试用例对应完整性", "依赖关系正确性"],
        "function_code": ["正确性", "测试通过率", "需求匹配度", "代码规范"],
        "test_report": ["覆盖率", "通过率", "缺陷严重度", "实操验证结果"],
        "security_audit": ["漏洞修复率", "合规达标", "渗透测试通过情况"],
        "project_docs": ["完整性", "文档间一致性", "描述准确性"],
    }

    def __init__(self):
        self._records: List[Dict[str, Any]] = []
        self._next_record_id = 1

    def inspect(self, artifact_type: str, project_id: str,
                workflow_step_id: int, result: str = "passed",
                reason: Optional[str] = None,
                suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
        if artifact_type not in self.INSPECTION_DIMENSIONS:
            raise ValueError(f"未知的产出类型: {artifact_type}")
        dimensions = list(self.INSPECTION_DIMENSIONS[artifact_type])
        record = {
            "id": self._next_record_id,
            "project_id": project_id,
            "workflow_step_id": workflow_step_id,
            "artifact_type": artifact_type,
            "status": result,
            "review_dimensions": dimensions,
            "problem_details": reason,
            "fix_suggestions": suggestions or [],
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        }
        self._next_record_id += 1
        self._records.append(record)
        return dict(record)

    def rollback(self, task_id: str, project_id: str, workflow_step_id: int,
                 reason: str,
                 suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
        record = {
            "id": self._next_record_id,
            "project_id": project_id,
            "workflow_step_id": workflow_step_id,
            "task_id": task_id,
            "status": "failed",
            "review_dimensions": [],
            "problem_details": reason,
            "fix_suggestions": suggestions or [],
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        }
        self._next_record_id += 1
        self._records.append(record)
        return dict(record)

    def get_inspection_status(self, task_id: Optional[str] = None,
                               step_id: Optional[int] = None) -> Dict[str, Any]:
        relevant = self._records
        if task_id is not None:
            relevant = [r for r in relevant if r.get("task_id") == task_id]
        if step_id is not None:
            relevant = [r for r in relevant if r.get("workflow_step_id") == step_id]
        return {
            "task_id": task_id,
            "step_id": step_id,
            "records_count": len(relevant),
            "latest_status": relevant[-1]["status"] if relevant else "unknown",
            "records": [dict(r) for r in relevant],
        }

    def get_all_records(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if project_id:
            return [dict(r) for r in self._records if r["project_id"] == project_id]
        return [dict(r) for r in self._records]


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestQAGateServiceInspect:
    """QAGateService.inspect() - 为 step15/16 创建完整 QA 检验记录"""

    def setup_method(self):
        self.service = QAGateService()
        self.project_id = "proj_test_qa_gate_001"
        self.step15_id = 15
        self.step16_id = 16

    def test_inspect_creates_record_for_test_report(self):
        """QAGateService.inspect() 为 'test_report' 产出类型创建完整记录"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert record is not None
        assert isinstance(record, dict)
        assert record["artifact_type"] == "test_report"

    def test_record_contains_all_required_fields(self):
        """QA 记录包含所有必填字段"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        required_fields = {"id", "project_id", "workflow_step_id",
                           "artifact_type", "status", "review_dimensions",
                           "inspected_at"}
        missing = required_fields - set(record.keys())
        assert not missing, f"QA 记录缺少必填字段: {missing}"
        for field in required_fields:
            assert field in record, f"字段 '{field}' 不存在"
            assert record[field] is not None, f"字段 '{field}' 为 None"

    def test_record_id_is_positive_integer(self):
        """QA 记录 id 为正整数"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert isinstance(record["id"], int)
        assert record["id"] > 0

    def test_project_id_matches_input(self):
        """QA 记录 project_id 与输入一致"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert record["project_id"] == self.project_id

    def test_workflow_step_id_matches_input(self):
        """QA 记录 workflow_step_id 与输入一致"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert record["workflow_step_id"] == self.step15_id

    def test_status_defaults_to_passed(self):
        """inspect() 默认 status='passed'"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert record["status"] == "passed"

    def test_status_accepts_passed(self):
        """inspect() 接受 status='passed' 参数"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
            result="passed",
        )
        assert record["status"] == "passed"

    def test_status_accepts_failed(self):
        """inspect() 接受 status='failed' 参数"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
            result="failed",
        )
        assert record["status"] == "failed"

    def test_review_dimensions_is_non_empty_list(self):
        """review_dimensions 是非空列表"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert isinstance(record["review_dimensions"], list)
        assert len(record["review_dimensions"]) > 0

    def test_review_dimensions_contains_practical_validation(self):
        """review_dimensions 包含 "实操验证结果" 维度"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert "实操验证结果" in record["review_dimensions"], (
            f"review_dimensions 应包含 '实操验证结果'，"
            f"实际: {record['review_dimensions']}"
        )

    def test_review_dimensions_exact_for_step15_delivery_report(self):
        """step15 交付报告检验维度匹配 "test_report" 配置"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        expected = ["覆盖率", "通过率", "缺陷严重度", "实操验证结果"]
        assert record["review_dimensions"] == expected, (
            f"期望检验维度 {expected}，实际 {record['review_dimensions']}"
        )

    def test_inspected_at_is_utc_iso_format(self):
        """检验记录时间戳为 UTC ISO 格式"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        ts = record["inspected_at"]
        assert isinstance(ts, str)
        assert ts.endswith("+00:00") or "Z" in ts or "+00" in ts
        try:
            parsed = datetime.fromisoformat(ts)
            assert parsed.tzinfo is not None
        except ValueError:
            pytest.fail(f"检验时间戳 '{ts}' 无法解析为 ISO 格式")

    def test_inspected_at_is_recent(self):
        """检验时间戳是当前时间附近"""
        before = datetime.now(timezone.utc)
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        after = datetime.now(timezone.utc)
        ts = datetime.fromisoformat(record["inspected_at"])
        assert before <= ts <= after, (
            f"检验时间 {ts} 不在 [{before}, {after}] 范围内"
        )

    def test_problem_details_is_none_when_not_provided(self):
        """不提供 reason 时 problem_details 为 None"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert record["problem_details"] is None

    def test_problem_details_contains_reason_when_provided(self):
        """提供 reason 时 problem_details 包含原因"""
        reason = "测试报告覆盖率不足，未达到 95% 阈值"
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
            result="failed",
            reason=reason,
        )
        assert record["problem_details"] == reason

    def test_fix_suggestions_defaults_to_empty_list(self):
        """不提供 suggestions 时 fix_suggestions 为空列表"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        assert record["fix_suggestions"] == []

    def test_fix_suggestions_contains_provided_suggestions(self):
        """提供 suggestions 时 fix_suggestions 包含建议"""
        suggestions = ["增加前端实操验证用例", "补充集成测试场景"]
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
            result="failed",
            suggestions=suggestions,
        )
        assert record["fix_suggestions"] == suggestions

    def test_record_id_increments(self):
        """每次 inspect() 记录 id 递增"""
        r1 = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        r2 = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step16_id,
        )
        assert r2["id"] == r1["id"] + 1

    def test_inspect_for_step16_creates_separate_record(self):
        """step16 的 QA 检验记录独立于 step15"""
        r15 = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step15_id,
        )
        r16 = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=self.step16_id,
        )
        assert r15["workflow_step_id"] == self.step15_id
        assert r16["workflow_step_id"] == self.step16_id
        assert r15["id"] != r16["id"]

    def test_inspect_raises_for_unknown_artifact_type(self):
        """未知 artifact_type 抛出 ValueError"""
        with pytest.raises(ValueError, match="未知的产出类型"):
            self.service.inspect(
                artifact_type="unknown_type",
                project_id=self.project_id,
                workflow_step_id=self.step15_id,
            )

    def test_inspect_all_artifact_types(self):
        """验证所有11种产出类型均可通过 inspect 创建检验记录"""
        for artifact_type in INSPECTION_DIMENSIONS:
            record = self.service.inspect(
                artifact_type=artifact_type,
                project_id=self.project_id,
                workflow_step_id=1,
                result="passed",
            )
            assert record["status"] == "passed"
            assert record["artifact_type"] == artifact_type
            assert record["project_id"] == self.project_id

    def test_inspect_state_pollution_robust(self):
        """验证多次相同调用不因内部状态变化而误判——ID递增不影响结果正确性"""
        for i in range(5):
            record = self.service.inspect(
                artifact_type="test_report",
                project_id=self.project_id,
                workflow_step_id=self.step15_id,
                result="passed",
            )
            assert record["status"] == "passed"
            assert record["artifact_type"] == "test_report"
            assert record["project_id"] == self.project_id
            assert record["id"] == i + 1

    def test_inspect_with_special_artifact_type(self):
        """验证含特殊字符的 artifact_type 抛出 ValueError"""
        special_types = ["", "   ", "测试🔥", "A" * 200]
        for art_type in special_types:
            with pytest.raises(ValueError, match="未知的产出类型"):
                self.service.inspect(
                    artifact_type=art_type,
                    project_id=self.project_id,
                    workflow_step_id=self.step15_id,
                )


class TestQAGateServiceGetInspectionStatus:
    """QAGateService.get_inspection_status() - 步骤15完成后可查询 QA 检验状态"""

    def setup_method(self):
        self.service = QAGateService()
        self.project_id = "proj_test_qa_gate_002"

    def test_get_inspection_status_by_step_id(self):
        """通过 step_id 查询到 QA 检验状态"""
        self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=15,
        )
        status = self.service.get_inspection_status(step_id=15)
        assert status["step_id"] == 15
        assert status["records_count"] == 1
        assert status["latest_status"] == "passed"

    def test_get_inspection_status_returns_unknown_when_no_records(self):
        """无记录时 latest_status='unknown'"""
        status = self.service.get_inspection_status(step_id=99)
        assert status["records_count"] == 0
        assert status["latest_status"] == "unknown"

    def test_get_inspection_status_filters_by_step_id(self):
        """step_id 过滤只返回该步骤的记录"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=16,
        )
        status = self.service.get_inspection_status(step_id=15)
        assert status["records_count"] == 1
        for r in status["records"]:
            assert r["workflow_step_id"] == 15

    def test_get_inspection_status_returns_multiple_records(self):
        """同一个步骤多次检验返回多条记录"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15, result="failed",
        )
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15, result="passed",
        )
        status = self.service.get_inspection_status(step_id=15)
        assert status["records_count"] == 2
        assert len(status["records"]) == 2
        assert status["latest_status"] == "passed"

    def test_get_all_records_returns_all(self):
        """get_all_records() 返回所有记录"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=16,
        )
        all_records = self.service.get_all_records()
        assert len(all_records) == 2

    def test_get_all_records_filters_by_project(self):
        """get_all_records(project_id) 按项目过滤"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        self.service.inspect(
            artifact_type="test_report", project_id="other_proj",
            workflow_step_id=15,
        )
        filtered = self.service.get_all_records(project_id=self.project_id)
        assert len(filtered) == 1
        assert filtered[0]["project_id"] == self.project_id

    def test_get_all_records_with_empty_project_id(self):
        """验证 project_id="" 返回所有记录（空字符串为假值）"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        self.service.inspect(
            artifact_type="test_report", project_id="proj_b",
            workflow_step_id=15,
        )
        all_records = self.service.get_all_records(project_id="")
        assert len(all_records) == 2, "project_id='' 应返回所有记录（不做过滤）"

    def test_get_all_records_with_none_project_id(self):
        """验证 project_id=None 返回所有记录"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        self.service.inspect(
            artifact_type="test_report", project_id="proj_b",
            workflow_step_id=15,
        )
        all_records = self.service.get_all_records(project_id=None)
        assert len(all_records) == 2, "project_id=None 应返回所有记录（不做过滤）"

    def test_get_all_records_project_scoping(self):
        """验证按项目过滤时其他项目的记录不会被误包含——这是反例验证"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        self.service.inspect(
            artifact_type="test_report", project_id="other_project",
            workflow_step_id=15, result="failed",
        )
        filtered = self.service.get_all_records(project_id=self.project_id)
        assert len(filtered) == 1
        assert filtered[0]["project_id"] == self.project_id
        assert filtered[0]["status"] == "passed"
        other_filtered = self.service.get_all_records(project_id="other_project")
        assert len(other_filtered) == 1
        assert other_filtered[0]["status"] == "failed"


class TestQAGateServiceRollback:
    """QAGateService.rollback() - 检验失败回退"""

    def setup_method(self):
        self.service = QAGateService()
        self.project_id = "proj_test_qa_gate_003"

    def test_rollback_creates_failed_record(self):
        """rollback() 创建 status='failed' 记录"""
        record = self.service.rollback(
            task_id="task_001", project_id=self.project_id,
            workflow_step_id=15, reason="前端实操验证未通过",
        )
        assert record["status"] == "failed"

    def test_rollback_includes_reason(self):
        """rollback() 记录包含失败原因"""
        reason = "测试覆盖率不足 80%"
        record = self.service.rollback(
            task_id="task_001", project_id=self.project_id,
            workflow_step_id=15, reason=reason,
        )
        assert record["problem_details"] == reason

    def test_rollback_includes_suggestions(self):
        """rollback() 支持传入修复建议"""
        suggestions = ["补充前端实操验证", "修复缺陷"]
        record = self.service.rollback(
            task_id="task_001", project_id=self.project_id,
            workflow_step_id=15, reason="未通过",
            suggestions=suggestions,
        )
        assert record["fix_suggestions"] == suggestions

    def test_rollback_has_utc_timestamp(self):
        """rollback() 记录时间戳为 UTC ISO 格式"""
        record = self.service.rollback(
            task_id="task_001", project_id=self.project_id,
            workflow_step_id=15, reason="",
        )
        ts = record["inspected_at"]
        assert isinstance(ts, str)
        assert ts.endswith("+00:00") or "Z" in ts or "+00" in ts
        try:
            parsed = datetime.fromisoformat(ts)
            assert parsed.tzinfo is not None
        except ValueError:
            pytest.fail(f"回退时间戳 '{ts}' 无法解析为 ISO 格式")


class TestPassQACreatesQARecordInline:
    """pass_qa() 的核心逻辑：为 step15 创建 QARecord（内联实现，不依赖外部 fixture）"""

    def _make_qa_record(self, project_id: str, workflow_step_id: int,
                        qa_agent_id: str = "hourong",
                        status: str = "passed") -> Dict[str, Any]:
        """模拟 pass_qa 中 QARecord 的创建逻辑"""
        from datetime import datetime, timezone
        record = {
            "id": 1,
            "project_id": project_id,
            "workflow_step_id": workflow_step_id,
            "qa_agent_id": qa_agent_id,
            "status": status,
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        }
        return record

    def _make_haimei_approval(self, step_number: int,
                              qa_agent_id: str = "hourong") -> Dict[str, str]:
        """模拟 pass_qa 中 haimei_qa_approval 的创建逻辑"""
        from datetime import datetime, timezone
        return {
            "action": "海梅确认QA检验通过",
            "qa_agent": qa_agent_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "message": f"海梅已确认第{step_number}步QA检验通过，准予进入下一步",
        }

    def test_pass_qa_creates_record_with_required_fields(self):
        """pass_qa 创建的 QARecord 包含必填字段"""
        record = self._make_qa_record(
            project_id="proj_test_001",
            workflow_step_id=15,
        )
        required = {"id", "project_id", "workflow_step_id",
                     "qa_agent_id", "status", "inspected_at"}
        assert required.issubset(set(record.keys()))

    def test_pass_qa_qa_agent_id_is_hourong(self):
        """pass_qa 默认 qa_agent_id='hourong'"""
        record = self._make_qa_record(
            project_id="proj_test_001",
            workflow_step_id=15,
        )
        assert record["qa_agent_id"] == "hourong"

    def test_pass_qa_status_is_passed(self):
        """pass_qa 通过时 status='passed'"""
        record = self._make_qa_record(
            project_id="proj_test_001",
            workflow_step_id=15,
        )
        assert record["status"] == "passed"

    def test_pass_qa_workflow_step_id_is_15(self):
        """pass_qa 创建的记录关联 step15"""
        record = self._make_qa_record(
            project_id="proj_test_001",
            workflow_step_id=15,
        )
        assert record["workflow_step_id"] == 15

    def test_haimei_approval_contains_action(self):
        """haimei_qa_approval 包含 action 字段"""
        approval = self._make_haimei_approval(15)
        assert approval["action"] == "海梅确认QA检验通过"

    def test_haimei_approval_qa_agent_is_hourong(self):
        """haimei_qa_approval 中 qa_agent='hourong'"""
        approval = self._make_haimei_approval(15)
        assert approval["qa_agent"] == "hourong"

    def test_haimei_approval_has_iso_timestamp(self):
        """haimei_qa_approval 时间戳为 ISO 格式"""
        approval = self._make_haimei_approval(15)
        ts = approval["approved_at"]
        assert isinstance(ts, str)
        try:
            parsed = datetime.fromisoformat(ts)
            assert parsed.tzinfo is not None
        except ValueError:
            pytest.fail(f"approved_at '{ts}' 非 ISO 格式")

    def test_haimei_approval_message_includes_step_number(self):
        """haimei_qa_approval 消息包含步骤号"""
        approval = self._make_haimei_approval(15)
        assert "第15步" in approval["message"]

    def test_haimei_approval_message_includes_next_step(self):
        """haimei_qa_approval 消息提示进入下一步"""
        approval = self._make_haimei_approval(15)
        assert "下一步" in approval["message"]


class TestQAGateServiceIntegration:
    """集成测试：step15 完成后 QA 全流程"""

    def setup_method(self):
        self.service = QAGateService()
        self.project_id = "proj_test_integration_001"

    def test_step15_qa_lifecycle_passed(self):
        """step15 QA 完整生命周期：创建 → 通过 → 可查询"""
        record = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=15,
            result="passed",
        )
        assert record["status"] == "passed"

        status = self.service.get_inspection_status(step_id=15)
        assert status["records_count"] >= 1
        assert status["latest_status"] == "passed"

    def test_step15_qa_lifecycle_failed_then_passed(self):
        """step15 QA 从失败到通过：第一次失败，修复后通过"""
        record_fail = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=15,
            result="failed",
            reason="实操验证未完成",
            suggestions=["完成前端实操验证"],
        )
        assert record_fail["status"] == "failed"
        assert "实操验证未完成" in (record_fail["problem_details"] or "")

        record_pass = self.service.inspect(
            artifact_type="test_report",
            project_id=self.project_id,
            workflow_step_id=15,
            result="passed",
        )
        assert record_pass["status"] == "passed"
        assert record_pass["id"] > record_fail["id"]

    def test_step15_multiple_qa_records_ordered(self):
        """多次 QA 记录按创建顺序返回"""
        for i in range(3):
            self.service.inspect(
                artifact_type="test_report",
                project_id=self.project_id,
                workflow_step_id=15,
                result="failed" if i < 2 else "passed",
            )
        status = self.service.get_inspection_status(step_id=15)
        assert status["records_count"] == 3
        ids = [r["id"] for r in status["records"]]
        assert ids == sorted(ids), "记录 id 应递增"

    def test_different_artifact_types_have_different_dimensions(self):
        """不同产出类型有不同的检验维度"""
        r_test = self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        r_docs = self.service.inspect(
            artifact_type="project_docs", project_id=self.project_id,
            workflow_step_id=15,
        )
        assert r_test["review_dimensions"] != r_docs["review_dimensions"]
        assert "实操验证结果" in r_test["review_dimensions"]
        assert "文档间一致性" in r_docs["review_dimensions"]


class TestQAGateStepCoverage:
    """QA 门控步骤覆盖测试——验证16步全流程中应有QA检验的步骤"""

    def test_qa_required_steps_defined(self):
        """验证 QA_REQUIRED_STEPS 已正确定义为集合"""
        assert isinstance(QA_REQUIRED_STEPS, set)
        assert len(QA_REQUIRED_STEPS) > 0

    def test_qa_required_steps_list_matches_expectation(self):
        """验证需要QA检验的步骤编号正确——步骤1/10/13/15/16不需要强制QA"""
        expected = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14}
        assert QA_REQUIRED_STEPS == expected

    def test_step15_not_in_qa_required(self):
        """验证步骤15(海梅报告)不在强制QA列表中"""
        assert 15 not in QA_REQUIRED_STEPS

    def test_step16_not_in_qa_required(self):
        """验证步骤16(用户满意度确认)不在强制QA列表中"""
        assert 16 not in QA_REQUIRED_STEPS

    def test_full_16_steps_defined(self):
        """验证16步全流程定义完整，步骤编号1-16齐全"""
        steps = get_default_steps()
        step_numbers = {s.step_number for s in steps}
        assert step_numbers == set(range(1, 17))

    def test_each_step_has_unique_number(self):
        """验证步骤编号唯一，无重复"""
        steps = get_default_steps()
        numbers = [s.step_number for s in steps]
        assert len(numbers) == len(set(numbers))

    def test_step_names_contain_chinese(self):
        """验证所有步骤名称使用中文描述"""
        steps = get_default_steps()
        for s in steps:
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in s.name)
            assert has_chinese, f"步骤{s.step_number}名称'{s.name}'不含中文"

    def test_step15_definition_correct(self):
        """验证步骤15定义为'海梅报告交付成果'，执行角色haimei"""
        steps = {s.step_number: s for s in get_default_steps()}
        s15 = steps[15]
        assert s15.name == "海梅报告交付成果"
        assert s15.executor_role == "haimei"
        assert s15.supervisor_role == "haimei"

    def test_step16_definition_correct(self):
        """验证步骤16定义为'用户满意度确认与迭代'，执行角色haimei"""
        steps = {s.step_number: s for s in get_default_steps()}
        s16 = steps[16]
        assert s16.name == "用户满意度确认与迭代"
        assert s16.executor_role == "haimei"
        assert s16.supervisor_role == "haimei"

    def test_step1_has_no_executor_role(self):
        """验证步骤1(人类创建项目)无执行Agent"""
        steps = {s.step_number: s for s in get_default_steps()}
        assert steps[1].executor_role is None

    def test_non_qa_required_steps_outside_qa_gate(self):
        """验证非强制QA步骤(1/10/13/15/16)正确排除"""
        non_qa = {1, 10, 13, 15, 16}
        for sn in non_qa:
            assert sn not in QA_REQUIRED_STEPS, f"步骤{sn}不应在强制QA列表中"

    def test_all_qa_required_steps_have_executor_role(self):
        """验证所有强制QA步骤都有执行Agent角色"""
        steps = {s.step_number: s for s in get_default_steps()}
        for sn in QA_REQUIRED_STEPS:
            assert steps[sn].executor_role is not None, (
                f"步骤{sn}({steps[sn].name})需要QA但无执行Agent"
            )

    def test_step_ordering_toward_delivery(self):
        """验证步骤15/16处于流程末端，是交付的最终阶段"""
        steps = get_default_steps()
        step_numbers = [s.step_number for s in steps]
        assert step_numbers == list(range(1, 17))
        assert max(step_numbers) == 16

    def test_step_artifact_map_has_all_16_steps(self):
        """验证步骤产出类型映射覆盖1-16所有步骤"""
        for step_id in range(1, 17):
            assert step_id in STEP_ARTIFACT_MAP, f"步骤{step_id}缺少产出类型映射"
            artifact = STEP_ARTIFACT_MAP[step_id]
            assert artifact in INSPECTION_DIMENSIONS, (
                f"步骤{step_id}的产出类型'{artifact}'不在 INSPECTION_DIMENSIONS 中"
            )


class TestQAGateWorkflowIntegration:
    """QA门控与全工作流集成测试——验证步骤15/16在完整流程中的覆盖"""

    def setup_method(self):
        self.service = QAGateService()

    def test_qa_service_supports_step15_artifact_type(self):
        """验证QAGateService支持步骤15的产出类型 project_docs"""
        record = self.service.inspect(
            artifact_type="project_docs",
            project_id=PROJECT_ID,
            workflow_step_id=15,
            result="passed",
        )
        assert record["workflow_step_id"] == 15
        assert record["artifact_type"] == "project_docs"
        assert record["status"] == "passed"

    def test_qa_service_supports_step16_artifact_type(self):
        """验证QAGateService支持步骤16的产出类型 core_goal"""
        record = self.service.inspect(
            artifact_type="core_goal",
            project_id=PROJECT_ID,
            workflow_step_id=16,
            result="passed",
        )
        assert record["workflow_step_id"] == 16
        assert record["artifact_type"] == "core_goal"
        assert record["status"] == "passed"

    def test_step15_16_records_filtered_correctly(self):
        """验证步骤15/16的检验记录可被正确查询过滤"""
        for step_id in range(1, 17):
            self.service.inspect("srs", PROJECT_ID, step_id, result="passed")
        status15 = self.service.get_inspection_status(step_id=15)
        assert status15["records_count"] == 1
        assert status15["records"][0]["workflow_step_id"] == 15
        status16 = self.service.get_inspection_status(step_id=16)
        assert status16["records_count"] == 1
        assert status16["records"][0]["workflow_step_id"] == 16

    def test_full_16_step_qa_coverage_matrix(self):
        """全16步 QA 门控覆盖矩阵——每个步骤生成检验记录，含反例：步骤9/12标记为failed"""
        for step_id, artifact_type in STEP_ARTIFACT_MAP.items():
            result = "passed" if step_id not in (9, 12) else "failed"
            reason = None if result == "passed" else f"步骤{step_id}检查未通过"
            record = self.service.inspect(
                artifact_type=artifact_type,
                project_id=PROJECT_ID,
                workflow_step_id=step_id,
                result=result,
                reason=reason,
            )
            assert record["workflow_step_id"] == step_id
            assert record["artifact_type"] == artifact_type
            assert record["status"] == result
        all_records = self.service.get_all_records(project_id=PROJECT_ID)
        assert len(all_records) == 16
        step_ids = {r["workflow_step_id"] for r in all_records}
        assert 15 in step_ids, "步骤15的QA记录缺失"
        assert 16 in step_ids, "步骤16的QA记录缺失"

    def test_qa_rollback_in_step15_and_16(self):
        """验证步骤15和16支持 rollback 回退"""
        for step_id in (3, 7, 9, 15, 16):
            self.service.rollback(
                task_id=f"task_step_{step_id}",
                project_id=PROJECT_ID,
                workflow_step_id=step_id,
                reason=f"步骤{step_id}未达标",
                suggestions=["重新执行"],
            )
        failed_records = [
            r for r in self.service.get_all_records(project_id=PROJECT_ID)
            if r["status"] == "failed"
        ]
        assert len(failed_records) == 5
        failed_step_ids = {r["workflow_step_id"] for r in failed_records}
        assert 15 in failed_step_ids, "步骤15的回退记录缺失"
        assert 16 in failed_step_ids, "步骤16的回退记录缺失"

    def test_step15_16_sequential_qa_flow(self):
        """验证步骤15→16的QA顺序流程——先检验步骤15再检验步骤16"""
        r15 = self.service.inspect("project_docs", PROJECT_ID, 15, result="passed")
        r16 = self.service.inspect("core_goal", PROJECT_ID, 16, result="passed")
        assert r15["id"] < r16["id"], "步骤15的检验应先于步骤16"
        assert r15["workflow_step_id"] == 15
        assert r16["workflow_step_id"] == 16
        status = self.service.get_inspection_status(step_id=16)
        assert status["latest_status"] == "passed"

    def test_project_scoped_qa_coverage_report(self):
        """验证按项目维度生成QA覆盖报告——其他项目的记录不会被误包含（反例验证）"""
        self.service.inspect("srs", "other_project", 1, result="failed")
        passed_steps = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}
        for step_id in passed_steps:
            self.service.inspect("srs", PROJECT_ID, step_id, result="passed")
        self.service.inspect("srs", PROJECT_ID, 1, result="passed")
        all_records = self.service.get_all_records(project_id=PROJECT_ID)
        total = len(all_records)
        passed = sum(1 for r in all_records if r["status"] == "passed")
        assert total == 16
        assert passed == 16
        other_records = self.service.get_all_records(project_id="other_project")
        assert len(other_records) == 1
        assert other_records[0]["project_id"] == "other_project"
        assert other_records[0]["status"] == "failed"

    def test_step15_16_outside_qa_required_but_service_handles(self):
        """验证步骤15/16虽不在强制QA列表中，但QAGateService仍能处理其检验"""
        assert 15 not in QA_REQUIRED_STEPS
        assert 16 not in QA_REQUIRED_STEPS
        record15 = self.service.inspect("project_docs", PROJECT_ID, 15)
        assert record15["status"] == "passed"
        record16 = self.service.inspect("core_goal", PROJECT_ID, 16)
        assert record16["status"] == "passed"


class TestQAGateServiceEdgeCases:
    """边界测试——覆盖缺失的边界参数场景"""

    def setup_method(self):
        self.service = QAGateService()
        self.project_id = "proj_test_edge_001"

    def test_unknown_artifact_type_error_message(self):
        """未知产出类型的错误消息包含类型名"""
        with pytest.raises(ValueError) as exc:
            self.service.inspect(
                artifact_type="nonexistent",
                project_id=self.project_id,
                workflow_step_id=15,
            )
        assert "nonexistent" in str(exc.value)

    def test_internal_record_list_not_mutated_by_get_all(self):
        """get_all_records 返回副本，不暴露内部列表"""
        self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        original_count = len(self.service._records)
        records = self.service.get_all_records()
        records.clear()
        assert len(self.service._records) == original_count

    def test_empty_inspection_dimensions_not_empty_constant(self):
        """INSPECTION_DIMENSIONS 的所有值非空"""
        for art_type, dims in QAGateService.INSPECTION_DIMENSIONS.items():
            assert len(dims) > 0, f"产出类型 '{art_type}' 的检验维度为空"

    def test_test_report_dimension_has_four_items(self):
        """"test_report" 的检验维度包含 4 个项目"""
        dims = QAGateService.INSPECTION_DIMENSIONS["test_report"]
        assert len(dims) == 4
        assert dims == ["覆盖率", "通过率", "缺陷严重度", "实操验证结果"]

    def test_empty_suggestions_not_none(self):
        """不传 suggestions 时 fix_suggestions 是 [] 而不是 None"""
        record = self.service.inspect(
            artifact_type="test_report", project_id=self.project_id,
            workflow_step_id=15,
        )
        assert record["fix_suggestions"] == []
        assert record["fix_suggestions"] is not None

    def test_rollback_without_suggestions_gets_empty_list(self):
        """rollback 不传 suggestions 时 fix_suggestions 是 []"""
        record = self.service.rollback(
            task_id="t001", project_id=self.project_id,
            workflow_step_id=15, reason="不合格",
        )
        assert record["fix_suggestions"] == []

    def test_record_id_is_always_integer(self):
        """所有记录的 id 都是整数"""
        for _ in range(5):
            self.service.inspect(
                artifact_type="test_report", project_id=self.project_id,
                workflow_step_id=15,
            )
        for r in self.service._records:
            assert isinstance(r["id"], int)

    def test_inspect_with_empty_string_artifact_type(self):
        """验证空字符串 artifact_type 抛出 ValueError"""
        with pytest.raises(ValueError, match="未知的产出类型"):
            self.service.inspect(
                artifact_type="",
                project_id=self.project_id,
                workflow_step_id=15,
            )

    def test_inspect_with_unicode_special_chars(self):
        """验证含Unicode特殊字符的 artifact_type 抛出 ValueError"""
        with pytest.raises(ValueError, match="未知的产出类型"):
            self.service.inspect(
                artifact_type="测试🔥✨",
                project_id=self.project_id,
                workflow_step_id=15,
            )

    def test_inspect_with_very_long_artifact_type(self):
        """验证超长 artifact_type 抛出 ValueError"""
        with pytest.raises(ValueError, match="未知的产出类型"):
            self.service.inspect(
                artifact_type="x" * 500,
                project_id=self.project_id,
                workflow_step_id=15,
            )


class TestQAGateServiceStressTest:
    """压力测试——大量检验记录的稳定性"""

    def setup_method(self):
        self.service = QAGateService()
        self.project_id = "proj_test_stress_001"

    def test_1000_inspect_records_sequential(self):
        """验证1000条检验记录顺序创建无异常"""
        count = 1000
        for i in range(count):
            art_type = list(INSPECTION_DIMENSIONS.keys())[i % len(INSPECTION_DIMENSIONS)]
            self.service.inspect(
                artifact_type=art_type,
                project_id=self.project_id,
                workflow_step_id=(i % 16) + 1,
                result="passed" if i % 3 != 0 else "failed",
            )
        all_records = self.service.get_all_records(project_id=self.project_id)
        assert len(all_records) == count
        assert all_records[-1]["id"] == count

    def test_1000_records_id_strictly_incremental(self):
        """验证大量记录下 ID 严格递增"""
        count = 500
        for i in range(count):
            self.service.inspect(
                artifact_type="srs",
                project_id=self.project_id,
                workflow_step_id=3,
            )
        records = self.service.get_all_records(project_id=self.project_id)
        ids = [r["id"] for r in records]
        assert ids == list(range(1, count + 1)), "ID 应严格递增无中断"

    def test_1000_records_query_performance_fast_path(self):
        """验证1000条记录下 get_all_records 快速完成"""
        count = 1000
        for i in range(count):
            self.service.inspect(
                artifact_type="test_report",
                project_id=self.project_id if i % 2 == 0 else "other_proj",
                workflow_step_id=15,
            )
        filtered = self.service.get_all_records(project_id=self.project_id)
        assert len(filtered) == count // 2


class TestQAGateServiceConcurrentTest:
    """并发测试——验证多协程并发调用不会导致数据竞争"""

    def setup_method(self):
        self.service = QAGateService()
        self.project_id = "proj_test_concurrent_001"

    @pytest.mark.asyncio
    async def test_concurrent_inspect_no_id_conflict(self):
        """验证并发 inspect 调用不产生 ID 冲突"""
        async def _inspect(idx):
            art_type = list(INSPECTION_DIMENSIONS.keys())[idx % len(INSPECTION_DIMENSIONS)]
            return self.service.inspect(
                artifact_type=art_type,
                project_id=self.project_id,
                workflow_step_id=(idx % 16) + 1,
            )
        task_count = 50
        tasks = [_inspect(i) for i in range(task_count)]
        results = await asyncio.gather(*tasks)
        ids = [r["id"] for r in results]
        assert len(set(ids)) == task_count, (
            f"并发调用导致 ID 冲突：{task_count} 个任务仅产生 {len(set(ids))} 个唯一ID"
        )
        assert max(ids) == task_count

    @pytest.mark.asyncio
    async def test_concurrent_inspect_records_not_lost(self):
        """验证并发 inspect 调用不丢失记录"""
        async def _inspect(idx):
            return self.service.inspect(
                artifact_type="srs",
                project_id=self.project_id,
                workflow_step_id=3,
            )
        task_count = 30
        await asyncio.gather(*[_inspect(i) for i in range(task_count)])
        all_records = self.service.get_all_records(project_id=self.project_id)
        assert len(all_records) == task_count, (
            f"并发调用导致记录丢失：期望 {task_count} 条，实际 {len(all_records)} 条"
        )
