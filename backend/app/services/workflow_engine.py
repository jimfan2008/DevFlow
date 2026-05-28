"""v4.0 - 16步 AI Agent 全自动开发流程状态机引擎"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class StepDefinition:
    step_number: int
    name: str
    executor_role: Optional[str]
    required_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)


def get_default_steps() -> List[StepDefinition]:
    return [
        StepDefinition(1, "人类用户创建项目", None,
                       required_inputs=[],
                       expected_outputs=["project_created", "gitea_repo_initialized"]),
        StepDefinition(2, "海梅确认核心目标与搭建组织架构", "haimei",
                       required_inputs=["project_info"],
                       expected_outputs=["core_goal_confirmed", "org_structure", "discussion_group_created"]),
        StepDefinition(3, "后兴需求分析", "houxing",
                       required_inputs=["core_goal", "user_initial_requirements"],
                       expected_outputs=["software_requirements_specification"]),
        StepDefinition(4, "后旺架构设计", "houwang",
                       required_inputs=["core_goal", "software_requirements"],
                       expected_outputs=["architecture_design", "backend_design", "frontend_design", "database_design"]),
        StepDefinition(5, "后富建立开发环境", "houfu",
                       required_inputs=["software_requirements", "architecture_design", "backend_design", "frontend_design", "database_design"],
                       expected_outputs=["dev_environment_ready"]),
        StepDefinition(6, "海梅制订TDD测试用例计划", "haimei",
                       required_inputs=["software_requirements", "architecture_design", "backend_design", "frontend_design", "database_design"],
                       expected_outputs=["tdd_test_case_plan"]),
        StepDefinition(7, "后发蜂群编写TDD测试用例", "houfa",
                       required_inputs=["tdd_test_case_plan"],
                       expected_outputs=["tdd_test_cases_completed"]),
        StepDefinition(8, "海梅制订代码编写计划", "haimei",
                       required_inputs=["software_requirements", "architecture_design", "backend_design", "frontend_design", "database_design", "tdd_test_case_plan"],
                       expected_outputs=["code_writing_plan", "task_dependency_graph"]),
        StepDefinition(9, "后发蜂群编写功能代码", "houfa",
                       required_inputs=["tdd_test_cases", "code_writing_plan", "task_dependency_graph"],
                       expected_outputs=["function_code_completed"]),
        StepDefinition(10, "后富部署到测试环境", "houfu",
                       required_inputs=["function_code"],
                       expected_outputs=["test_environment_deployed"]),
        StepDefinition(11, "后达蜂群全面测试", "houda",
                       required_inputs=["test_environment_url", "tdd_test_cases"],
                       expected_outputs=["unit_test_report", "module_test_report", "integration_test_report", "frontend_verification_report"]),
        StepDefinition(12, "后华安全审计", "houhua",
                       required_inputs=["function_code", "test_reports"],
                       expected_outputs=["security_audit_report"]),
        StepDefinition(13, "后富部署到生产环境", "houfu",
                       required_inputs=["function_code", "security_audit_report"],
                       expected_outputs=["production_environment_deployed"]),
        StepDefinition(14, "后贵完善项目文档", "hougui",
                       required_inputs=["all_project_artifacts"],
                       expected_outputs=["deployment_manual", "operation_manual", "api_documentation", "user_manual"]),
        StepDefinition(15, "海梅报告交付成果", "haimei",
                       required_inputs=["all_project_artifacts"],
                       expected_outputs=["delivery_report"]),
        StepDefinition(16, "用户满意度确认与迭代", "haimei",
                       required_inputs=["delivery_report"],
                       expected_outputs=["user_satisfaction_confirmed"]),
    ]


@dataclass
class QARecordResult:
    id: Optional[int] = None
    project_id: str = ""
    workflow_step_id: int = 0
    task_id: Optional[str] = None
    qa_agent_id: str = ""
    status: str = "pending"
    review_dimensions: Optional[List[str]] = None
    problem_details: Optional[str] = None
    fix_suggestions: Optional[str] = None
    inspected_at: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class StepRecord:
    step_number: int
    step_name: str
    executor_role: Optional[str]
    status: str
    output_artifacts: Optional[Dict] = None
    completed_at: Optional[str] = None


class WorkflowEngine:
    QA_REQUIRED_STEPS = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14}
    CODE_REPO_COMMIT_STEPS = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15}

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.steps = get_default_steps()
        self.current_step = 1
        self._step_states: Dict[int, StepRecord] = {}
        self._step_history: List[Dict] = []
        self._preserved_artifacts: Dict[str, Any] = {}
        self._qa_records: List[QARecordResult] = []
        self._next_qa_record_id = 1

        for step in self.steps:
            status = "completed" if step.step_number == 1 else "pending"
            self._step_states[step.step_number] = StepRecord(
                step_number=step.step_number,
                step_name=step.name,
                executor_role=step.executor_role,
                status=status,
            )

    def advance_step(self, target_step: int):
        if target_step > 16 or target_step < 2:
            raise ValueError(f"步骤号必须在2-16之间，当前: {target_step}")

        current = self.current_step
        if target_step > current:
            for s in range(current, target_step):
                if s in self.QA_REQUIRED_STEPS:
                    step_record = self._step_states[s]
                    if step_record.status != "completed":
                        raise ValueError(f"第{s}步必须通过QA检验才能进入下一步")

        self.current_step = target_step
        self._step_states[target_step].status = "in_progress"

    def complete_step(self, step_number: int, artifacts: Optional[Dict] = None) -> StepRecord:
        if step_number not in self._step_states:
            raise ValueError(f"步骤 {step_number} 不存在")

        step = self._step_states[step_number]
        if step_number in self.QA_REQUIRED_STEPS:
            step.status = "qa_review"
        else:
            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()

        if artifacts:
            step.output_artifacts = artifacts

        self._step_history.append({
            "step_number": step_number,
            "step_name": step.step_name,
            "status": step.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return step

    def pass_qa(self, step_number: int, qa_agent_id: str = "hourong") -> QARecordResult:
        if step_number not in self._step_states:
            raise ValueError(f"步骤 {step_number} 不存在")
        if self._step_states[step_number].status != "qa_review":
            raise ValueError(f"第{step_number}步必须先完成步骤再进行QA检验")

        self._step_states[step_number].status = "completed"
        self._step_states[step_number].completed_at = datetime.now(timezone.utc).isoformat()

        if self._step_states[step_number].output_artifacts:
            self._preserved_artifacts[f"step_{step_number}"] = self._step_states[step_number].output_artifacts

        record = QARecordResult(
            id=self._next_qa_record_id,
            project_id=self.project_id,
            workflow_step_id=step_number,
            qa_agent_id=qa_agent_id,
            status="passed",
            inspected_at=datetime.now(timezone.utc).isoformat(),
        )
        self._next_qa_record_id += 1
        self._qa_records.append(record)

        self._step_history.append({
            "step_number": step_number,
            "step_name": self._step_states[step_number].step_name,
            "status": "completed",
            "qa_result": "passed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return record

    def fail_qa(self, step_number: int, qa_agent_id: str = "hourong",
                reason: str = "", suggestions: Optional[List[str]] = None) -> QARecordResult:
        if step_number not in self._step_states:
            raise ValueError(f"步骤 {step_number} 不存在")

        self._step_states[step_number].status = "rejected"

        fix_text = "\n".join(suggestions) if suggestions else ""
        record = QARecordResult(
            id=self._next_qa_record_id,
            project_id=self.project_id,
            workflow_step_id=step_number,
            qa_agent_id=qa_agent_id,
            status="failed",
            problem_details=reason if reason else None,
            fix_suggestions=fix_text if fix_text else None,
            inspected_at=datetime.now(timezone.utc).isoformat(),
        )
        self._next_qa_record_id += 1
        self._qa_records.append(record)
        return record

    def user_dissatisfied(self, feedback: str) -> Dict[str, Any]:
        self.current_step = 3
        for step_num in range(3, 17):
            if step_num in self._step_states:
                self._step_states[step_num].status = "pending"
                self._step_states[step_num].completed_at = None
                self._step_states[step_num].output_artifacts = None

        self._step_history.append({
            "step_number": 16,
            "status": "iterating",
            "feedback": feedback,
            "reset_to_step": 3,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "message": "用户不满意，收集意见后回到第三步重新迭代",
            "feedback": feedback,
            "reset_from_step": 3,
            "current_step": 3,
        }

    def get_preserved_artifacts(self) -> Dict[str, Any]:
        return dict(self._preserved_artifacts)

    def get_step_history(self) -> List[Dict]:
        return list(self._step_history)

    def get_current_status(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "current_step": self.current_step,
            "steps": {
                sn: {
                    "step_name": sr.step_name,
                    "executor_role": sr.executor_role,
                    "status": sr.status,
                    "completed_at": sr.completed_at,
                }
                for sn, sr in self._step_states.items()
            },
            "qa_records_count": len(self._qa_records),
            "preserved_artifacts_count": len(self._preserved_artifacts),
        }