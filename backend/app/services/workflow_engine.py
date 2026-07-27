"""v4.0 - 16步 AI Agent 全自动开发流程状态机引擎（DB持久化）
海梅(HaiMei)全程担任项目经理总控，负责：
1. 每个步骤前：调动指定Agent、检查Agent健康状态
2. 每个步骤中：监控Agent运行状态，检测异常
3. 每个步骤后：审核Agent产出，确认可以进入下一步
4. 全项目周期：持续检查所有Agent状态，异常时自动恢复
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timezone
import json
import uuid
import logging

logger = logging.getLogger("devflow.engine")


@dataclass
class StepDefinition:
    step_number: int
    name: str
    executor_role: Optional[str]
    supervisor_role: Optional[str] = "haimei"
    required_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)


def get_default_steps() -> List[StepDefinition]:
    return [
        StepDefinition(1, "人类用户创建项目", None, supervisor_role=None),
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

# Agent健康状态枚举
AGENT_HEALTHY = "healthy"
AGENT_BUSY = "busy"
AGENT_ERROR = "error"
AGENT_OFFLINE = "offline"
AGENT_RECOVERING = "recovering"


def _get_default_agent_health() -> Dict[str, str]:
    """所有Agent的初始健康状态"""
    return {
        "haimei": AGENT_HEALTHY,
        "houxing": AGENT_HEALTHY,
        "houwang": AGENT_HEALTHY,
        "houfu": AGENT_HEALTHY,
        "houfa": AGENT_HEALTHY,
        "houda": AGENT_HEALTHY,
        "houhua": AGENT_HEALTHY,
        "hougui": AGENT_HEALTHY,
        "hourong": AGENT_HEALTHY,
    }


class WorkflowEngine:
    def __init__(self, project_id: str, db=None, auto_supervise: bool = True):
        self.project_id = project_id
        self.db = db
        self.steps = get_default_steps()
        self.current_step = 1
        self._cached_step2_artifacts: dict = {}
        self._cached_step3_artifacts: dict = {}
        self._cached_step4_artifacts: dict = {}
        self.agent_health: Dict[str, str] = dict(_get_default_agent_health())
        self._load_from_db()
        # 海梅自主监控：初始化时自动推进项目
        if auto_supervise and self.db:
            try:
                self.haimei_auto_advance()
            except Exception as e:
                logger.error(f"[HAIMEI_DEBUG] __init__ haimei_auto_advance failed: {e}")
                pass

    def _load_from_db(self):
        if not self.db:
            return
        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all()

        if not rows:
            self._init_default_steps()
            # 海梅：初始化后生成任务清单
            try:
                self.haimei_auto_advance()
            except Exception:
                pass
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

        # 海梅：加载后自动检查Agent状态并推进
        try:
            self.haimei_auto_advance()
        except Exception as e:
            logger.error(f"[HAIMEI_DEBUG] _load_from_db haimei_auto_advance failed: {e}")
            pass

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
        """生成步骤 N → N+1 交接文档并存入 DB（跳过已存在 handover_doc 的步骤）
        同时提取并保存 handover_doc_path 到 output_artifacts。
        """
        row = self._get_step_row(step_number)
        if not row:
            return
        existing = row.output_artifacts or {}

        if not existing.get("handover_doc"):
            next_step = step_number + 1
            step_defs = {s.step_number: s for s in self.steps}
            step_name = step_defs[step_number].name if step_number in step_defs else f"步骤{step_number}"
            next_name = step_defs[next_step].name if next_step in step_defs else f"步骤{next_step}"

            include_keys = [k for k in existing.keys()
                            if k not in ("status", "message", "saved_at",
                                         "qa_passed", "qa_checked", "qa_inspections",
                                         "handover_path", "handover_doc", "handover_doc_path")]
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
            existing["handover_doc"] = handover

        # ── 提取 handover_doc_path ──
        if not existing.get("handover_doc_path"):
            handover_doc_path = ""
            if existing.get("doc_path") and isinstance(existing["doc_path"], str):
                # 步骤3/5_1: 单个文档路径
                handover_doc_path = existing["doc_path"]
            elif existing.get("doc_paths") and isinstance(existing["doc_paths"], dict):
                # 步骤4: 多文档路径字典 → 取第一个
                paths = [v for v in existing["doc_paths"].values() if v]
                if paths:
                    handover_doc_path = paths[0]
            elif existing.get("docs_dir"):
                # 步骤4: docs_dir 作为文档目录
                handover_doc_path = existing["docs_dir"]
            # 对于步骤6-14 (dispatch_step_n 通用模式)，content 保存到 output_artifacts
            # 没有物理文件路径，用逻辑路径 step{N}://{artifact_key}
            elif existing.get("status") == "done":
                artifact_key_candidates = [
                    "tdd_plan", "tdd_cases", "code_plan", "code",
                    "deployment_log", "test_report", "security_report",
                    "production_log", "project_docs", "env_info",
                ]
                for ak in artifact_key_candidates:
                    if existing.get(ak):
                        handover_doc_path = f"step{step_number}://{ak}"
                        break

            if handover_doc_path:
                existing["handover_doc_path"] = handover_doc_path

        row.output_artifacts = existing
        self.db.commit()

    def advance_step(self, target_step: int):
        if target_step > 16 or target_step < 2:
            raise ValueError(f"步骤号必须在2-16之间，当前: {target_step}")

        self._ensure_steps()

        # 海梅前置监督：检查前一步完成状态和Agent就绪
        supervision = self.haimei_supervise_step(target_step)
        if not supervision["approved"]:
            raise ValueError(f"海梅监督未通过: {supervision['message']}")

        current = self.current_step
        if target_step > current:
            for s in range(current, target_step):
                row = self._get_step_row(s)
                if row and row.status != "completed":
                    raise ValueError(f"第{s}步必须通过QA检验才能进入下一步")

        # 海梅调动执行Agent
        self.haimei_mobilize_agent(target_step)

        self.current_step = target_step
        row = self._get_step_row(target_step)
        if row:
            row.status = "in_progress"
            row.started_at = datetime.now(timezone.utc)
            existing = row.output_artifacts or {}
            existing["haimei_supervision"] = supervision
            row.output_artifacts = existing
            self.db.commit()

    def complete_step(self, step_number: int, artifacts: Optional[Dict] = None) -> dict:
        self._ensure_steps()
        row = self._get_step_row(step_number)
        if not row:
            raise ValueError(f"步骤 {step_number} 不存在")

        # 海梅标记该步骤的Agent工作完成，恢复Agent为健康状态
        if row.executor_agent_id and row.executor_agent_id in self.agent_health:
            self.agent_health[row.executor_agent_id] = AGENT_HEALTHY

        # 海梅审核：将监督记录写入产物
        haimei_review = {
            "haimei_reviewed_at": datetime.now(timezone.utc).isoformat(),
            "haimei_review_action": "海梅已审核该步骤产出，准备进入下一步",
            "haimei_supervisor": "haimei",
        }

        # 如果步骤内部已通过 hourong QA（如步骤6-14的收敛循环），直接标记完成
        existing_artifacts = artifacts or row.output_artifacts or {}
        if step_number in QA_REQUIRED_STEPS:
            if existing_artifacts.get("qa_passed"):
                row.status = "completed"
                row.completed_at = datetime.now(timezone.utc)
            else:
                row.status = "qa_review"
        else:
            row.status = "completed"
            row.completed_at = datetime.now(timezone.utc)

        # 所有步骤都生成交接文档（含 handover_doc_path），QA步骤在 pass_qa 时也会生成一次
        self._generate_step_handover(step_number)

        if artifacts:
            artifacts.update(haimei_review)
            row.output_artifacts = artifacts
        else:
            existing = row.output_artifacts or {}
            existing.update(haimei_review)
            row.output_artifacts = existing

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
            # 海梅记录重置原因
            existing = row.output_artifacts or {}
            existing["haimei_reset"] = {
                "action": "海梅重置该步骤",
                "previous_status": row.status,
                "reset_at": datetime.now(timezone.utc).isoformat(),
            }
            row.status = "pending"
            row.started_at = None
            row.output_artifacts = existing
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

        # 海梅记录QA通过
        existing = row.output_artifacts or {}
        existing["haimei_qa_approval"] = {
            "action": "海梅确认QA检验通过",
            "qa_agent": qa_agent_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "message": f"海梅已确认第{step_number}步QA检验通过，准予进入下一步",
        }
        row.output_artifacts = existing

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

        # 海梅记录QA失败，标记异常
        existing = row.output_artifacts or {}
        existing["haimei_qa_rejection"] = {
            "action": "海梅记录QA检验未通过",
            "qa_agent": qa_agent_id,
            "reason": reason or "未提供原因",
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "message": f"海梅已记录第{step_number}步QA未通过，等待修复后重新提交",
        }
        row.output_artifacts = existing

        # 海梅记录执行Agent异常
        if row.executor_agent_id:
            self.haimei_report_agent_error(
                row.executor_agent_id,
                f"第{step_number}步QA未通过: {reason}"
            )

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

        # 海梅记录用户不满意反馈
        haimei_iteration_note = {
            "haimei_iteration": {
                "action": "海梅启动迭代流程",
                "feedback": feedback,
                "iterated_at": datetime.now(timezone.utc).isoformat(),
                "reset_from_step": 3,
                "message": "海梅已记录用户反馈，启动迭代循环",
            }
        }

        # 重置步骤 4-16 为 pending
        for step_num in range(4, 17):
            row = self._get_step_row(step_num)
            if row:
                existing = row.output_artifacts or {}
                existing["haimei_iteration_reset"] = {
                    "action": "海梅因用户不满意重置该步骤",
                    "reset_at": datetime.now(timezone.utc).isoformat(),
                }
                row.status = "pending"
                row.started_at = None
                row.completed_at = None
                row.output_artifacts = existing

        # 清除步骤4的缓存产物
        self._cached_step4_artifacts = {}

        # 保持步骤 2-3 的结果（核心目标和需求分析）
        # 步骤 3 重新进入 in_progress
        row = self._get_step_row(3)
        if row:
            row.status = "in_progress"
            row.started_at = datetime.now(timezone.utc)
            existing = row.output_artifacts or {}
            existing.update(haimei_iteration_note)
            row.output_artifacts = existing

        self.current_step = 3

        # 恢复所有Agent健康状态
        for agent_name in self.agent_health:
            if self.agent_health[agent_name] == AGENT_ERROR:
                self.agent_health[agent_name] = AGENT_HEALTHY

        from app.models.project import Project
        self.db.query(Project).filter(Project.id == self.project_id).update(
            {"current_step": 3}
        )

        self.db.commit()

        return {
            "feedback": feedback,
            "reset_to_step": 3,
            "message": f"用户反馈: {feedback}，海梅已带领团队回到第三步重新迭代",
            "haimei_supervision": haimei_iteration_note,
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
        self._ensure_steps()
        row = self._get_step_row(4)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step4_artifacts(self) -> dict:
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

    # ============================================================
    # Generic step artifact access
    # ============================================================

    def save_step_artifacts(self, step_number: int, artifacts: dict):
        """通用步骤产物保存（支持任意步骤）"""
        self._ensure_steps()
        row = self._get_step_row(step_number)
        if row:
            existing = row.output_artifacts or {}
            existing.update(artifacts)
            row.output_artifacts = existing
            self.db.commit()

    def get_step_artifacts(self, step_number: int) -> dict:
        """通用步骤产物读取（支持任意步骤）"""
        self._ensure_steps()
        row = self._get_step_row(step_number)
        if row and row.output_artifacts:
            return row.output_artifacts
        return {}

    # ============================================================
    # 海梅(HaiMei) 项目经理全程监控方法
    # ============================================================

    def haimei_get_all_agent_statuses(self) -> Dict[str, Dict]:
        """海梅获取所有Agent实时状态"""
        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all() if self.db else []

        busy_agents: Set[str] = set()
        for r in rows:
            if r.executor_agent_id and r.status == "in_progress":
                busy_agents.add(r.executor_agent_id)

        now = datetime.now(timezone.utc)
        result = {}
        for agent_name, health in self.agent_health.items():
            if agent_name in busy_agents:
                current_status = AGENT_BUSY
            else:
                current_status = health

            result[agent_name] = {
                "agent": agent_name,
                "health": current_status,
                "in_progress_step": next(
                    (r.step_number for r in rows
                     if r.executor_agent_id == agent_name and r.status == "in_progress"),
                    None
                ),
                "checked_at": now.isoformat(),
            }
        return result

    def haimei_check_agent_health(self, agent_role: str) -> str:
        """海梅检查单个Agent是否健康可用"""
        return self.agent_health.get(agent_role, AGENT_OFFLINE)

    def haimei_report_agent_error(self, agent_role: str, error_info: str = ""):
        """海梅记录Agent异常状态"""
        self.agent_health[agent_role] = AGENT_ERROR
        if self.db:
            from app.models.workflow_step import WorkflowStep
            rows = self.db.query(WorkflowStep).filter(
                WorkflowStep.project_id == self.project_id,
                WorkflowStep.executor_agent_id == agent_role,
                WorkflowStep.status == "in_progress",
            ).all()
            for r in rows:
                existing = r.output_artifacts or {}
                existing["haimei_error"] = error_info
                existing["haimei_error_at"] = datetime.now(timezone.utc).isoformat()
                existing["haimei_action"] = "海梅已标记该Agent异常，准备恢复"
                r.output_artifacts = existing
            self.db.commit()

    def haimei_restore_agent(self, agent_role: str) -> dict:
        """海梅恢复异常Agent到正常工作状态"""
        was_error = self.agent_health.get(agent_role) == AGENT_ERROR
        self.agent_health[agent_role] = AGENT_HEALTHY

        if self.db and was_error:
            from app.models.workflow_step import WorkflowStep
            rows = self.db.query(WorkflowStep).filter(
                WorkflowStep.project_id == self.project_id,
                WorkflowStep.executor_agent_id == agent_role,
                WorkflowStep.status == "in_progress",
            ).all()
            for r in rows:
                existing = r.output_artifacts or {}
                existing["haimei_restored_at"] = datetime.now(timezone.utc).isoformat()
                existing["haimei_message"] = f"海梅已恢复{agent_role}到正常工作状态"
                r.output_artifacts = existing
            self.db.commit()

        return {
            "agent": agent_role,
            "previous_health": AGENT_ERROR if was_error else AGENT_HEALTHY,
            "current_health": AGENT_HEALTHY,
            "message": f"海梅已将{agent_role}恢复到正常状态" if was_error else f"{agent_role}状态正常，无需恢复",
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }

    def haimei_mobilize_agent(self, step_number: int) -> dict:
        """海梅在步骤执行前调动指定Agent，检查其是否就绪"""
        step_defs = {s.step_number: s for s in self.steps}
        step_def = step_defs.get(step_number)
        if not step_def:
            return {"ready": False, "message": f"步骤{step_number}不存在"}

        agent_role = step_def.executor_role
        if not agent_role:
            return {"ready": True, "message": "该步骤无需Agent执行"}

        health = self.haimei_check_agent_health(agent_role)
        if health == AGENT_OFFLINE:
            return {"ready": False, "message": f"Agent {agent_role} 处于离线状态，无法调动", "health": health}
        if health == AGENT_ERROR:
            self.haimei_restore_agent(agent_role)
            return {"ready": True, "message": f"Agent {agent_role} 曾有异常，海梅已将其恢复并调动", "health": AGENT_HEALTHY}

        return {
            "ready": True,
            "message": f"海梅已调动 {agent_role} 执行第{step_number}步",
            "health": health,
            "mobilized_at": datetime.now(timezone.utc).isoformat(),
        }

    def haimei_supervise_step(self, step_number: int) -> dict:
        """海梅对即将执行的步骤进行全面监督审查"""
        step_defs = {s.step_number: s for s in self.steps}
        step_def = step_defs.get(step_number)
        if not step_def:
            return {"approved": False, "message": f"步骤{step_number}不存在"}

        if self.db:
            row = self._get_step_row(step_number)
            if not row:
                return {"approved": False, "message": f"步骤{step_number}未初始化"}

            # 1. 检查前一步是否完成
            if step_number > 1:
                prev_row = self._get_step_row(step_number - 1)
                if prev_row and prev_row.status not in ("completed",):
                    return {
                        "approved": False,
                        "message": f"第{step_number-1}步尚未完成，海梅不允许执行第{step_number}步",
                        "blocking_step": step_number - 1,
                    }

            # 3. 检查输入产物是否齐全
            for req_input in step_def.required_inputs:
                found = False
                for check_step in range(1, step_number):
                    check_row = self._get_step_row(check_step)
                    if check_row and check_row.output_artifacts:
                        if req_input in check_row.output_artifacts:
                            found = True
                            break
                if not found:
                    return {
                        "approved": False,
                        "message": f"海梅检查发现缺少必要输入: {req_input}",
                        "missing_input": req_input,
                    }

        # 2. 调动执行Agent
        mobilization = self.haimei_mobilize_agent(step_number)
        if not mobilization["ready"]:
            return {"approved": False, "message": mobilization["message"]}

        return {
            "approved": True,
            "message": f"海梅审核通过，可以执行第{step_number}步",
            "supervisor": "haimei",
            "supervised_at": datetime.now(timezone.utc).isoformat(),
            "mobilization": mobilization,
        }

    def haimei_check_project_progress(self) -> Dict[str, Any]:
        """海梅主动检查整个项目推进状态，返回完整进度报告
        【增强】每次检查时自主推进项目，恢复异常Agent，持续推动直到项目完成"""
        if self.db:
            self._ensure_steps()

        # 海梅自主推进项目（自动恢复Agent、推进就绪步骤、重置已驳回步骤）
        auto_result = self.haimei_auto_advance()

        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all() if self.db else []

        steps_status = {}
        blocked_steps = []
        for r in rows:
            s_def = next((s for s in self.steps if s.step_number == r.step_number), None)
            step_info = {
                "step_name": r.step_name,
                "executor_role": r.executor_agent_id,
                "status": r.status,
                "supervisor": s_def.supervisor_role if s_def else None,
            }
            if r.status == "in_progress":
                action_needed = "等待执行中"
                if r.executor_agent_id:
                    agent_health = self.agent_health.get(r.executor_agent_id, AGENT_HEALTHY)
                    if agent_health == AGENT_ERROR:
                        action_needed = f"海梅需要恢复Agent: {r.executor_agent_id}"
                    elif agent_health == AGENT_OFFLINE:
                        action_needed = f"Agent {r.executor_agent_id} 离线，等待上线"
                    elif agent_health == AGENT_BUSY:
                        action_needed = f"Agent {r.executor_agent_id} 忙碌中"
                step_info["action_needed"] = action_needed

            if r.status == "qa_review":
                blocked_steps.append(r.step_number)

            steps_status[str(r.step_number)] = step_info

        agent_statuses = self.haimei_get_all_agent_statuses()

        # 计算整体完成百分比
        completed = sum(1 for r in rows if r.status == "completed")
        total = len(rows) if rows else 16
        progress_pct = round(completed / total * 100, 1) if total > 0 else 0

        haimei_message = auto_result.get("haimei_phase", "海梅持续监控中，一切正常")
        if auto_result.get("all_completed"):
            haimei_message = "🎉 海梅宣布：项目全部16步已完成！交付成果准备就绪"
        elif auto_result.get("qa_blocked_steps"):
            haimei_message = f"海梅等待第{auto_result['qa_blocked_steps'][0]}步QA检验通过"
        elif auto_result.get("restored_agents"):
            haimei_message = f"海梅已恢复Agent: {', '.join(auto_result['restored_agents'])}"

        return {
            "project_id": self.project_id,
            "current_step": self.current_step,
            "progress_pct": progress_pct,
            "completed_steps": completed,
            "total_steps": total,
            "blocked_steps": blocked_steps,
            "steps": steps_status,
            "agent_statuses": agent_statuses,
            "haimei_auto_actions": auto_result.get("actions", []),
            "haimei_message": haimei_message,
            "haimei_phase": auto_result.get("haimei_phase", ""),
            "next_action": haimei_message,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def haimei_force_restart_step(self, step_number: int) -> dict:
        """海梅强制重启异常步骤（恢复Agent并重置步骤状态）"""
        if self.db:
            self._ensure_steps()
        row = self._get_step_row(step_number) if self.db else None
        if not row:
            # DB-less mode: just return the restart info
            agent_role = None
            step_name = f"第{step_number}步"
        else:
            agent_role = row.executor_agent_id
            step_name = row.step_name
            if agent_role:
                self.haimei_restore_agent(agent_role)
            row.status = "pending"
            row.started_at = None
            row.completed_at = None
            row.output_artifacts = None
            if self.db:
                self.db.commit()

        return {
            "step_number": step_number,
            "step_name": step_name,
            "new_status": "pending",
            "agent_role": agent_role,
            "message": f"海梅已强制重启第{step_number}步，Agent {agent_role} 已恢复就绪",
            "restarted_at": datetime.now(timezone.utc).isoformat(),
        }

    def haimei_sync_tasks(self) -> int:
        """海梅将16步工作流任务同步到项目任务列表（写入Task表，实时显示在看板）
        自动查找项目的看板并将工作流步骤创建/更新为Task记录"""
        if not self.db:
            return 0
        from app.models.board import Board
        from app.models.workflow_step import WorkflowStep
        from app.models.task import Task
        from datetime import datetime, timezone
        import uuid

        # 查找项目的第一个看板
        board = self.db.query(Board).filter(
            Board.project_id == self.project_id,
            Board.is_active == True
        ).first()
        if not board:
            return 0

        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all() if self.db else []
        step_map = {r.step_number: r for r in rows}

        step_status_map = {
            "pending": {"task_status": "pending", "progress": 0, "label": "待开始"},
            "in_progress": {"task_status": "in_progress", "progress": 40, "label": "执行中"},
            "qa_review": {"task_status": "delivered", "progress": 70, "label": "QA检验中"},
            "completed": {"task_status": "accepted", "progress": 100, "label": "已完成"},
            "rejected": {"task_status": "rejected", "progress": 30, "label": "已驳回"},
        }
        step_priorities = {2: "high", 3: "high", 4: "high", 6: "high", 8: "high",
                           15: "high", 16: "high", 1: "medium", 5: "medium",
                           7: "medium", 9: "medium", 10: "medium", 11: "medium",
                           12: "medium", 13: "medium", 14: "medium"}
        agent_names = {
            "haimei": "海梅", "houxing": "后兴", "houwang": "后旺",
            "houfa": "后发", "houda": "后达", "houfu": "后富",
            "hougui": "后贵", "hourong": "后荣", "houhua": "后华",
        }

        synced_count = 0
        for s in self.steps:
            if s.step_number == 1:
                continue
            row = step_map.get(s.step_number)
            step_status = row.status if row else "pending"
            mapping = step_status_map.get(step_status, step_status_map["pending"])
            executor = s.executor_role or "user"

            task_name = f"步骤{s.step_number}: {s.name}"
            existing = self.db.query(Task).filter(
                Task.project_id == self.project_id,
                Task.type == "workflow_step",
                Task.name == task_name,
            ).first()

            now = datetime.now(timezone.utc)
            if existing:
                existing.status = mapping["task_status"]
                existing.progress = mapping["progress"]
                existing.progress_message = f"海梅: {s.name} - {mapping['label']}"
                existing.assignee_agent_id = executor if executor != "user" else existing.assignee_agent_id
                existing.updated_at = now
                if step_status == "completed" and not existing.completed_at:
                    existing.completed_at = now
                if step_status == "in_progress" and not existing.started_at:
                    existing.started_at = now
                ctx = existing.context or {}
                ctx["haimei_auto_sync"] = {
                    "step_number": s.step_number,
                    "supervisor": "haimei",
                    "synced_at": now.isoformat(),
                }
                existing.context = ctx
            else:
                task = Task(
                    id=str(uuid.uuid4()),
                    project_id=self.project_id,
                    name=task_name,
                    description=f"海梅工作流步骤 - {s.name}\n执行Agent: {agent_names.get(executor, executor)}",
                    type="workflow_step",
                    status=mapping["task_status"],
                    priority=step_priorities.get(s.step_number, "medium"),
                    assignee_agent_id=executor if executor != "user" else None,
                    progress=mapping["progress"],
                    progress_message=f"海梅: {s.name} - {mapping['label']}",
                    context={
                        "haimei_auto_sync": {
                            "step_number": s.step_number,
                            "supervisor": "haimei",
                            "synced_at": now.isoformat(),
                        }
                    },
                    created_at=now,
                    updated_at=now,
                )
                if step_status == "in_progress":
                    task.started_at = now
                if step_status == "completed":
                    task.completed_at = now
                self.db.add(task)
            synced_count += 1

        if synced_count:
            self.db.commit()
        return synced_count

    def haimei_generate_task_list(self) -> List[Dict[str, Any]]:
        """海梅生成项目任务清单（基于16步流程，包含每步的状态、执行人、输入输出）
        【增强】自动同步到任务系统，实时显示在看板"""
        self._ensure_steps()

        # 同步到任务数据库（Task表）
        try:
            self.haimei_sync_tasks()
        except Exception:
            pass

        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all() if self.db else []

        step_rows = {r.step_number: r for r in rows}
        task_list = []
        for s in self.steps:
            row = step_rows.get(s.step_number)
            status = row.status if row else "pending"
            task_list.append({
                "step_number": s.step_number,
                "task_name": s.name,
                "status": status,
                "executor_role": s.executor_role,
                "executor_name": {
                    "haimei": "海梅", "houxing": "后兴", "houwang": "后旺",
                    "houfa": "后发", "houda": "后达", "houfu": "后富",
                    "hougui": "后贵", "hourong": "后荣", "houhua": "后华",
                }.get(s.executor_role, s.executor_role or "用户"),
                "supervisor_role": s.supervisor_role,
                "required_inputs": s.required_inputs,
                "expected_outputs": s.expected_outputs,
                "qa_required": s.step_number in QA_REQUIRED_STEPS,
                "handover_doc": row.output_artifacts.get("handover_doc") if row and row.output_artifacts else None,
                "started_at": row.started_at.isoformat() if row and row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row and row.completed_at else None,
            })
        return task_list

    def haimei_auto_advance(self, autodispatch: bool = False) -> Dict[str, Any]:
        """海梅自主推进项目：自动检查所有步骤状态，推进到下一个就绪的步骤，
        恢复异常Agent，生成任务清单，确保持续推进直到项目完成"""
        self._ensure_steps()
        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all() if self.db else []

        step_map = {r.step_number: r for r in rows}
        actions = []
        advanced = False
        restored_agents = []
        haimei_phase_msg = ""

        # Phase 1: 检查并恢复所有异常Agent
        for agent_name in list(self.agent_health.keys()):
            if self.agent_health.get(agent_name) == AGENT_ERROR:
                self.haimei_restore_agent(agent_name)
                restored_agents.append(agent_name)
                actions.append(f"海梅已恢复异常Agent: {agent_name}")

        if restored_agents:
            haimei_phase_msg = f"阶段1: 海梅恢复了{len(restored_agents)}个异常Agent"

        # Phase 2: 检查in_progress步骤，确保Agent健康
        for r in rows:
            if r.status == "in_progress":
                if r.executor_agent_id:
                    health = self.agent_health.get(r.executor_agent_id, AGENT_HEALTHY)
                    if health == AGENT_ERROR:
                        self.haimei_restore_agent(r.executor_agent_id)
                        actions.append(f"海梅在第{r.step_number}步中发现Agent {r.executor_agent_id}异常并已恢复")
                        restored_agents.append(r.executor_agent_id)
                    elif health == AGENT_OFFLINE:
                        actions.append(f"海梅发现Agent {r.executor_agent_id}离线，等待上线")
                haimei_phase_msg = haimei_phase_msg or f"阶段2: 第{r.step_number}步正在执行中，海梅持续监控"

        # Phase 3: 检查qa_review阻塞步骤
        qa_blocked = [r for r in rows if r.status == "qa_review"]
        if qa_blocked:
            blocked_nums = [r.step_number for r in qa_blocked]
            actions.append(f"海梅等待步骤 {blocked_nums} 的QA检验通过")
            haimei_phase_msg = haimei_phase_msg or f"阶段3: 步骤{blocked_nums[0]}等待QA检验"

        # Phase 4: 检查rejected步骤 - 海梅自动恢复并重置
        rejected_steps = [r for r in rows if r.status == "rejected"]
        for r in rejected_steps:
            actions.append(f"海梅标记步骤{r.step_number}被驳回，准备恢复Agent后重启")
            if r.executor_agent_id:
                self.haimei_restore_agent(r.executor_agent_id)
                restored_agents.append(r.executor_agent_id)
            r.status = "pending"
            r.started_at = None
            r.completed_at = None
            advanced = True
            actions.append(f"海梅已重置被驳回的步骤{r.step_number}为待执行状态")
        if rejected_steps and self.db:
            self.db.commit()

        # Phase 5: 推进下一个就绪的步骤并调度Agent执行
        for s in self.steps:
            if s.step_number == 1:
                continue
            r = step_map.get(s.step_number)
            if not r:
                continue
            if r.status == "pending":
                # 步骤4-14由前端触发执行，海梅不自动推进
                if 4 <= s.step_number <= 14:
                    continue
                prev_row = step_map.get(s.step_number - 1)
                if prev_row and prev_row.status == "completed":
                    try:
                        # 检查执行Agent是否可用
                        agent_role = s.executor_role
                        if agent_role:
                            agent_health = self.agent_health.get(agent_role, AGENT_HEALTHY)
                            if agent_health == AGENT_ERROR:
                                self.haimei_restore_agent(agent_role)
                                actions.append(f"海梅已恢复Agent {agent_role} 准备执行第{s.step_number}步")
                            elif agent_health == AGENT_OFFLINE:
                                actions.append(f"海梅发现Agent {agent_role} 离线，第{s.step_number}步暂缓")
                                break
                        self.advance_step(s.step_number)
                        actions.append(f"海梅自主推进到第{s.step_number}步: {s.name}")
                        advanced = True
                        haimei_phase_msg = haimei_phase_msg or f"阶段5: 海梅推进到第{s.step_number}步"

                        # 步骤 4-14 由前端WS处理器执行，海梅只推进不调度
                        if 4 <= s.step_number <= 14:
                            actions.append(f"海梅已推进到第{s.step_number}步，等待前端触发执行")
                        else:
                            actions.append(f"海梅已推进第{s.step_number}步，等待执行")
                        break
                    except ValueError as e:
                        actions.append(f"海梅尝试推进第{s.step_number}步但条件不满足: {e}")
                        break
            elif r.status == "in_progress":
                # 检查是否有后台任务在运行（防止僵尸状态）
                from app.services.haimei_executor import HaimeiStepExecutor
                has_task = HaimeiStepExecutor.is_running(self.project_id, s.step_number)
                task_key = f"{self.project_id}:step{s.step_number}"
                logger.info(f"[ZOMBIE_DEBUG] step{s.step_number} in_progress, has_task={has_task}, _tasks_keys={list(HaimeiStepExecutor._tasks.keys())}")
                if not has_task:
                    # 无后台任务 = 僵尸状态，尝试重启
                    artifacts = self.get_step_artifacts(s.step_number) or {}
                    logger.info(f"[ZOMBIE_DEBUG] step{s.step_number} in_progress no task, artifacts={str(artifacts)[:100]}, has_status={bool(artifacts.get('status'))}, status_val={artifacts.get('status','')}")
                    # 只有完全无产物（status 为空 且 无文档 且 无环境配置）才视为僵尸
                    # status="generating" 表示正在执行，不应重启
                    if (not artifacts.get("status") and
                        not artifacts.get("design_doc") and
                        not artifacts.get("env_info")):
                        agent_role = s.executor_role
                        if agent_role:
                            self.haimei_restore_agent(agent_role)
                        # 重启后台任务（使用自动执行模块）
                        if 4 <= s.step_number <= 14:
                            actions.append(f"海梅检测到第{s.step_number}步处于僵尸状态，重置后等待前端触发执行")
                            self.reset_step(s.step_number)
                        else:
                            actions.append(f"海梅检测到第{s.step_number}步处于僵尸状态，等待前端触发执行")
                    elif artifacts.get("status") in ("generating",):
                        # status="generating" 但无后台任务
                        # 给新生任务 120 秒宽限期，让后台任务有时间注册
                        is_fresh = False
                        if r.started_at:
                            from datetime import datetime, timezone
                            _start = r.started_at
                            # 兼容 started_at 可能是 ISO 字符串或 naive datetime
                            if isinstance(_start, str):
                                try:
                                    _start = datetime.fromisoformat(_start)
                                except Exception:
                                    _start = datetime.now(timezone.utc)
                            if _start.tzinfo is None:
                                _start = _start.replace(tzinfo=timezone.utc)
                            elapsed = (datetime.now(timezone.utc) - _start).total_seconds()
                            if elapsed < 120:
                                is_fresh = True
                        if not has_task and not is_fresh:
                            logger.info(f"[ZOMBIE] step{s.step_number} status=generating but no task, resetting")
                            if 4 <= s.step_number <= 14:
                                self.reset_step(s.step_number)
                                actions.append(f"海梅检测到第{s.step_number}步任务已完成但状态未更新，已重置")
                            else:
                                actions.append(f"海梅检测到第{s.step_number}步任务已完成但状态未更新，等待前端触发执行")
                        else:
                            actions.append(f"海梅检测到第{s.step_number}步正在执行中（status={artifacts.get('status')}），跳过")
                    break
            elif r.status == "completed":
                continue

        # Phase 6: 检查项目是否全部完成
        all_done = all(
            step_map.get(s.step_number) and step_map[s.step_number].status == "completed"
            for s in self.steps
        )
        if all_done:
            actions.append("🎉 海梅宣布：项目全部16步已完成！")

        # Phase 7: 同步任务到看板（Task表）确保任务面板实时显示
        try:
            synced = self.haimei_sync_tasks()
            if synced:
                actions.append(f"海梅同步了{synced}项任务到任务面板")
        except Exception:
            pass

        if not advanced and not qa_blocked and not restored_agents and not rejected_steps:
            current_r = step_map.get(self.current_step)
            if current_r:
                actions.append(f"海梅正在监控第{self.current_step}步执行中，无需额外操作")

        return {
            "haimei_auto_advanced": advanced,
            "advanced_to_step": self.current_step if advanced else None,
            "restored_agents": restored_agents,
            "qa_blocked_steps": [r.step_number for r in qa_blocked] if qa_blocked else [],
            "rejected_steps_reset": [r.step_number for r in rejected_steps] if rejected_steps else [],
            "all_completed": all_done,
            "actions": actions,
            "haimei_phase": haimei_phase_msg or "海梅持续监控中，一切正常",
        }

    def haimei_get_report(self) -> Dict[str, Any]:
        """海梅生成项目状态的完整报告（自然语言描述）"""
        progress = self.haimei_check_project_progress()
        agent_statuses = self.haimei_get_all_agent_statuses()
        task_list = self.haimei_generate_task_list()

        completed = [t for t in task_list if t["status"] == "completed"]
        in_progress = [t for t in task_list if t["status"] == "in_progress"]
        pending = [t for t in task_list if t["status"] == "pending"]
        qa_review = [t for t in task_list if t["status"] == "qa_review"]
        rejected = [t for t in task_list if t["status"] == "rejected"]

        agent_health_summary = {
            name: info["health"]
            for name, info in agent_statuses.items()
        }
        error_agents = [name for name, h in agent_health_summary.items() if h == "error"]
        offline_agents = [name for name, h in agent_health_summary.items() if h == "offline"]

        report_lines = [
            "📋 海梅项目推进报告",
            f"项目进度: {progress['progress_pct']}% ({progress['completed_steps']}/{progress['total_steps']})",
            f"当前步骤: 第{progress['current_step']}步",
        ]
        if completed:
            report_lines.append(f"已完成: {len(completed)}步 - {', '.join(t['task_name'] for t in completed[:5])}")
        if in_progress:
            report_lines.append(f"执行中: {len(in_progress)}步 - {in_progress[0]['task_name']}")
        if qa_review:
            report_lines.append(f"待QA检验: {len(qa_review)}步 - {qa_review[0]['task_name']}")
        if rejected:
            report_lines.append(f"已驳回待修复: {len(rejected)}步")
        if error_agents:
            report_lines.append(f"⚠️ 异常Agent: {', '.join(error_agents)}（海梅将自动恢复）")
        if offline_agents:
            report_lines.append(f"💤 离线Agent: {', '.join(offline_agents)}")

        report_lines.append(f"Agent健康概览: {sum(1 for h in agent_health_summary.values() if h == 'healthy')}健康 / {sum(1 for h in agent_health_summary.values() if h == 'busy')}忙碌 / {len(error_agents)}异常 / {len(offline_agents)}离线")

        next_action = progress.get("next_action", "海梅持续推进中")
        report_lines.append(f"下一步行动: {next_action}")

        return {
            "project_id": self.project_id,
            "report": "\n".join(report_lines),
            "progress": progress,
            "agent_statuses": agent_statuses,
            "task_list": task_list,
            "haimei_supervisor": "haimei",
        }

    def get_current_status(self) -> Dict[str, Any]:
        self._ensure_steps()
        from app.models.workflow_step import WorkflowStep
        rows = self.db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all()

        steps = {}
        for r in rows:
            effective_status = r.status
            if effective_status == "qa_review":
                artifacts = r.output_artifacts or {}
                if artifacts.get("qa_passed"):
                    effective_status = "completed"
            steps[str(r.step_number)] = {
                "step_name": r.step_name,
                "executor_role": r.executor_agent_id,
                "status": effective_status,
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

        agent_statuses = self.haimei_get_all_agent_statuses()

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
            "agent_statuses": agent_statuses,
            "haimei_supervisor": "haimei",
            "haimei_message": "海梅全程监督中，所有Agent状态正常" if all(
                s["health"] in (AGENT_HEALTHY, AGENT_BUSY)
                for s in agent_statuses.values()
            ) else "海梅正在处理异常Agent",
        }
