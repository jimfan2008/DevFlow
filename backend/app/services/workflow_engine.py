"""v4.0 - 16步 AI Agent 全自动开发流程状态机引擎（DB持久化）"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json
import uuid


@dataclass
class StepDefinition:
    step_number: int
    name: str
    executor_role: Optional[str]
    required_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)


def get_default_steps() -> List[StepDefinition]:
    return [
        StepDefinition(1, "人类用户创建项目", None),
        StepDefinition(2, "海梅确认核心目标与搭建组织架构", "haimei"),
        StepDefinition(3, "后兴需求分析", "houxing"),
        StepDefinition(4, "后旺架构设计", "houwang"),
        StepDefinition(5, "后富建立开发环境", "houfu"),
        StepDefinition(6, "海梅制订TDD测试用例计划", "haimei"),
        StepDefinition(7, "后发蜂群编写TDD测试用例", "houfa"),
        StepDefinition(8, "海梅制订代码编写计划", "haimei"),
        StepDefinition(9, "后发蜂群编写功能代码", "houfa"),
        StepDefinition(10, "后富部署到测试环境", "houfu"),
        StepDefinition(11, "后达蜂群全面测试", "houda"),
        StepDefinition(12, "后华安全审计", "houhua"),
        StepDefinition(13, "后富部署到生产环境", "houfu"),
        StepDefinition(14, "后贵完善项目文档", "hougui"),
        StepDefinition(15, "海梅报告交付成果", "haimei"),
        StepDefinition(16, "用户满意度确认与迭代", "haimei"),
    ]


QA_REQUIRED_STEPS = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14}


class WorkflowEngine:
    def __init__(self, project_id: str, db=None):
        self.project_id = project_id
        self.db = db
        self.steps = get_default_steps()
        self.current_step = 1
        self._cached_step2_artifacts: dict = {}
        self._cached_step3_artifacts: dict = {}
        self._cached_step4_artifacts: dict = {}
        self._load_from_db()

    def _load_from_db(self):
        if not self.db:
            return
        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all()

        if not rows:
            self._init_default_steps()
            return

        max_step = 1
        for r in rows:
            if r.status == "in_progress" or r.status == "completed":
                max_step = max(max_step, r.step_number)
            if r.step_number == 2 and r.output_artifacts:
                self._cached_step2_artifacts = r.output_artifacts
            if r.step_number == 3 and r.output_artifacts:
                self._cached_step3_artifacts = r.output_artifacts
            if r.step_number == 4 and r.output_artifacts:
                self._cached_step4_artifacts = r.output_artifacts

        from app.models.project import Project
        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        if project and project.current_step > max_step:
            max_step = project.current_step

        self.current_step = max_step

    def _init_default_steps(self):
        from app.models.workflow_step import WorkflowStep
        from app.models.project import Project

        for s in self.steps:
            row = WorkflowStep(
                project_id=self.project_id,
                step_number=s.step_number,
                step_name=s.name,
                executor_agent_id=s.executor_role,
                status="completed" if s.step_number == 1 else "pending",
            )
            self.db.add(row)
        self.db.query(Project).filter(Project.id == self.project_id).update(
            {"current_step": 1}
        )
        self.db.commit()

    def _ensure_steps(self):
        from app.models.workflow_step import WorkflowStep
        row = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).first()
        if not row:
            self._init_default_steps()

    def _get_step_row(self, step_number: int):
        from app.models.workflow_step import WorkflowStep
        return self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id,
            WorkflowStep.step_number == step_number,
        ).first()

    def _generate_step_handover(self, step_number: int):
        """生成步骤 N → N+1 交接文档并存入 DB（跳过已存在 handover_doc 的步骤）"""
        row = self._get_step_row(step_number)
        if not row:
            return
        existing = row.output_artifacts or {}
        if existing.get("handover_doc"):
            return

        next_step = step_number + 1
        step_defs = {s.step_number: s for s in self.steps}
        step_name = step_defs[step_number].name if step_number in step_defs else f"步骤{step_number}"
        next_name = step_defs[next_step].name if next_step in step_defs else f"步骤{next_step}"

        include_keys = [k for k in existing.keys()
                        if k not in ("status", "message", "saved_at",
                                     "qa_passed", "qa_checked", "qa_inspections",
                                     "handover_path", "handover_doc")]
        lines = [
            f"# 步骤 {step_number} → 步骤 {next_step} 交接文档",
            "",
            f"## 完成步骤",
            f"{step_name}",
            "",
            f"## 下一步",
            f"{next_name}",
            "",
            f"## 完成时间",
            f"{datetime.now(timezone.utc).isoformat()}",
            "",
            "## 关键产物",
        ]
        for k in include_keys:
            v = existing[k]
            if isinstance(v, str) and len(v) > 200:
                lines.append(f"- {k}: {v[:200]}...")
            elif isinstance(v, str):
                lines.append(f"- {k}: {v}")
            elif isinstance(v, (dict, list)):
                import json as _j
                short = _j.dumps(v, ensure_ascii=False)[:200]
                lines.append(f"- {k}: {short}")
            else:
                lines.append(f"- {k}: {v}")
        lines += [
            "",
            "## 交接说明",
            f"{step_name} 已完成并通过检验。{next_name} 请基于以上产出成果推进下一步。",
        ]
        handover = "\n".join(lines)
        row.output_artifacts = {**existing, "handover_doc": handover}
        self.db.commit()

    def advance_step(self, target_step: int):
        if target_step > 16 or target_step < 2:
            raise ValueError(f"步骤号必须在2-16之间，当前: {target_step}")

        self._ensure_steps()

        current = self.current_step
        if target_step > current:
            for s in range(current, target_step):
                row = self._get_step_row(s)
                if row and row.status != "completed":
                    raise ValueError(f"第{s}步必须通过QA检验才能进入下一步")

        self.current_step = target_step
        row = self._get_step_row(target_step)
        if row:
            row.status = "in_progress"
            row.started_at = datetime.now(timezone.utc)
            self.db.commit()

    def complete_step(self, step_number: int, artifacts: Optional[Dict] = None) -> dict:
        self._ensure_steps()
        row = self._get_step_row(step_number)
        if not row:
            raise ValueError(f"步骤 {step_number} 不存在")

        if step_number in QA_REQUIRED_STEPS:
            row.status = "qa_review"
        else:
            row.status = "completed"
            row.completed_at = datetime.now(timezone.utc)
            self._generate_step_handover(step_number)

        if artifacts:
            row.output_artifacts = artifacts

        if step_number == 2:
            from app.models.project import Project
            core_goal = (artifacts or {}).get("core_goal", "")
            if core_goal:
                self.db.query(Project).filter(Project.id == self.project_id).update(
                    {"core_goal": core_goal, "current_step": 2}
                )
            self._cached_step2_artifacts = artifacts

        self.db.commit()
        return row.to_dict() if row else {}

    def reset_step(self, step_number: int):
        """将步骤重置为 pending 状态（用于执行失败时回滚）"""
        self._ensure_steps()
        row = self._get_step_row(step_number)
        if row:
            row.status = "pending"
            row.started_at = None
            row.output_artifacts = None
            self.db.commit()

    def pass_qa(self, step_number: int, qa_agent_id: str = "hourong") -> dict:
        self._ensure_steps()
        row = self._get_step_row(step_number)
        if not row:
            raise ValueError(f"步骤 {step_number} 不存在")
        if row.status != "qa_review":
            raise ValueError(f"第{step_number}步必须先完成步骤再进行QA检验")

        row.status = "completed"
        row.completed_at = datetime.now(timezone.utc)
        self.current_step = step_number + 1
        self._generate_step_handover(step_number)

        from app.models.project import Project
        self.db.query(Project).filter(Project.id == self.project_id).update(
            {"current_step": self.current_step}
        )

        from app.models.qa_record import QARecord
        qa = QARecord(
            project_id=self.project_id,
            workflow_step_id=row.id,
            qa_agent_id=qa_agent_id,
            status="passed",
            inspected_at=datetime.now(timezone.utc),
        )
        self.db.add(qa)
        self.db.commit()
        return qa.to_dict()

    def fail_qa(self, step_number: int, qa_agent_id: str = "hourong",
                reason: str = "", suggestions: Optional[List[str]] = None) -> dict:
        self._ensure_steps()
        row = self._get_step_row(step_number)
        if not row:
            raise ValueError(f"步骤 {step_number} 不存在")

        row.status = "rejected"

        from app.models.qa_record import QARecord
        qa = QARecord(
            project_id=self.project_id,
            workflow_step_id=row.id,
            qa_agent_id=qa_agent_id,
            status="failed",
            problem_details=reason or None,
            fix_suggestions="\n".join(suggestions) if suggestions else None,
            inspected_at=datetime.now(timezone.utc),
        )
        self.db.add(qa)
        self.db.commit()
        return qa.to_dict()

    def user_dissatisfied(self, feedback: str = "") -> dict:
        """用户不满意，回到第三步重新迭代"""
        self._ensure_steps()

        # 重置步骤 4-16 为 pending
        for step_num in range(4, 17):
            row = self._get_step_row(step_num)
            if row:
                row.status = "pending"
                row.started_at = None
                row.completed_at = None
                row.output_artifacts = None

        # 清除步骤4的缓存产物
        self._cached_step4_artifacts = {}

        # 保持步骤 2-3 的结果（核心目标和需求分析）
        # 步骤 3 重新进入 in_progress
        row = self._get_step_row(3)
        if row:
            row.status = "in_progress"
            row.started_at = datetime.now(timezone.utc)

        self.current_step = 3

        from app.models.project import Project
        self.db.query(Project).filter(Project.id == self.project_id).update(
            {"current_step": 3}
        )

        self.db.commit()

        return {
            "feedback": feedback,
            "reset_to_step": 3,
            "message": f"用户反馈: {feedback}，已回到第三步重新迭代",
        }

    def save_step2_artifacts(self, artifacts: dict):
        self._cached_step2_artifacts = artifacts
        self._ensure_steps()
        row = self._get_step_row(2)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step2_artifacts(self) -> dict:
        if hasattr(self, '_cached_step2_artifacts') and self._cached_step2_artifacts:
            return self._cached_step2_artifacts
        self._ensure_steps()
        row = self._get_step_row(2)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step3_artifacts(self, artifacts: dict):
        self._cached_step3_artifacts = artifacts
        self._ensure_steps()
        row = self._get_step_row(3)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step3_artifacts(self) -> dict:
        if hasattr(self, '_cached_step3_artifacts') and self._cached_step3_artifacts:
            return self._cached_step3_artifacts
        self._ensure_steps()
        row = self._get_step_row(3)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step4_artifacts(self, artifacts: dict):
        self._cached_step4_artifacts = artifacts
        self._ensure_steps()
        row = self._get_step_row(4)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step4_artifacts(self) -> dict:
        if hasattr(self, '_cached_step4_artifacts') and self._cached_step4_artifacts:
            return self._cached_step4_artifacts
        self._ensure_steps()
        row = self._get_step_row(4)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    # --- Step 5 artifact methods ---
    def save_step5_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(5)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step5_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(5)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    # --- Step 6 artifact methods ---
    def save_step6_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(6)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step6_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(6)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    # --- Step 7 artifact methods ---
    def save_step7_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(7)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step7_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(7)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    # --- Step 8 artifact methods ---
    def save_step8_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(8)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step8_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(8)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step9_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(9)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step9_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(9)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step10_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(10)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step10_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(10)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step11_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(11)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step11_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(11)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step12_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(12)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step12_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(12)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step13_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(13)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step13_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(13)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step14_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(14)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step14_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(14)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step15_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(15)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step15_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(15)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def save_step16_artifacts(self, artifacts: dict):
        self._ensure_steps()
        row = self._get_step_row(16)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step16_artifacts(self) -> dict:
        self._ensure_steps()
        row = self._get_step_row(16)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    def get_current_status(self) -> Dict[str, Any]:
        self._ensure_steps()
        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all()

        steps = {}
        for r in rows:
            steps[str(r.step_number)] = {
                "step_name": r.step_name,
                "executor_role": r.executor_agent_id,
                "status": r.status,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }

        from app.models.qa_record import QARecord
        qa_count = self.db.query(QARecord).filter(
            QARecord.project_id == self.project_id
        ).count()

        step2 = self.get_step2_artifacts()
        step3 = self.get_step3_artifacts()
        step4 = self.get_step4_artifacts()
        step5 = self.get_step5_artifacts()
        step6 = self.get_step6_artifacts()
        step7 = self.get_step7_artifacts()
        step8 = self.get_step8_artifacts()

        return {
            "project_id": self.project_id,
            "current_step": self.current_step,
            "steps": steps,
            "qa_records_count": qa_count,
            "step2": step2,
            "step3": step3,
            "step4": step4,
            "step5": step5,
            "step6": step6,
            "step7": step7,
            "step8": step8,
        }
