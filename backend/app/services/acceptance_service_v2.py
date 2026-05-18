from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.task import Task
from app.models.acceptance_record import AcceptanceRecord
from app.models.agent import Agent
from app.models.enums import TaskStatus

logger = logging.getLogger("devflow.acceptance_v2")

ACCEPTANCE_TIMEOUT_HOURS = 48
MAX_CONSECUTIVE_REJECTIONS = 3


class AcceptanceServiceV2:
    def __init__(self, db: Session):
        self.db = db

    def run_acceptance(self, task_id: str, reviewer_agent_id: str) -> dict:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status != TaskStatus.delivered.value:
            raise ValueError(f"Task must be delivered for acceptance, current: {task.status}")

        checks = self._run_checks(task)
        passed = all(c["passed"] for c in checks.values())

        from app.services.task_state_service import TaskStateService
        state_svc = TaskStateService(self.db)

        if passed:
            task = state_svc.accept_task(task_id, reviewer_agent_id)
            result = "accepted"
            suggestions = None
        else:
            task = state_svc.reject_task(
                task_id, reviewer_agent_id,
                problem_details=str(checks),
                suggestions=self._generate_suggestions(checks),
            )
            result = "rejected"
            suggestions = self._generate_suggestions(checks)

            if task.rejection_count >= MAX_CONSECUTIVE_REJECTIONS:
                logger.warning(f"Task {task_id} has been rejected {task.rejection_count} times, escalating")
                try:
                    from app.services.notification_service import NotificationService
                    notif_svc = NotificationService(self.db)
                    if task.project_id:
                        from app.models.project import Project
                        project = self.db.query(Project).filter(Project.id == task.project_id).first()
                        if project and project.creator_id:
                            notif_svc.notify_rejection_escalation(
                                task_id=task_id, task_name=task.name,
                                rejection_count=task.rejection_count,
                                user_id=project.creator_id,
                                project_id=task.project_id,
                            )
                except Exception as e:
                    logger.warning(f"Failed to send escalation notification: {e}")

        if passed:
            self._trigger_downstream_assignment(task_id, reviewer_agent_id)

        return {
            "task_id": task_id,
            "result": result,
            "checks": checks,
            "suggestions": suggestions,
            "rejection_count": task.rejection_count,
        }

    def _run_checks(self, task: Task) -> dict:
        artifacts = task.artifacts or {}
        coverage = artifacts.get("coverage", 0)
        test_pass_rate = artifacts.get("test_pass_rate", 0)
        has_output = bool(artifacts.get("output") or task.result_summary)

        return {
            "coverage_check": {
                "passed": coverage >= 80 if coverage else False,
                "detail": f"代码覆盖度: {coverage}% (>=80%)",
            },
            "test_pass_rate_check": {
                "passed": test_pass_rate >= 90 if test_pass_rate else False,
                "detail": f"测试通过率: {test_pass_rate}% (>=90%)",
            },
            "output_check": {
                "passed": has_output,
                "detail": "交付成果存在" if has_output else "缺少交付成果",
            },
        }

    def _generate_suggestions(self, checks: dict) -> List[str]:
        suggestions = []
        for name, check in checks.items():
            if not check["passed"]:
                suggestions.append(check["detail"])
        return suggestions

    def _trigger_downstream_assignment(self, task_id: str, reviewer_agent_id: str):
        from app.models.dependency import TaskDependency
        downstream_deps = self.db.query(TaskDependency).filter(
            TaskDependency.source_task_id == task_id
        ).all()

        for dep in downstream_deps:
            downstream_task = self.db.query(Task).filter(Task.id == dep.target_task_id).first()
            if not downstream_task:
                continue
            if downstream_task.status != TaskStatus.pending.value:
                continue

            from app.services.task_state_service import TaskStateService
            state_svc = TaskStateService(self.db)
            if state_svc.check_dependency_readiness(downstream_task.id):
                logger.info(f"Triggering skill-assignment for downstream task {downstream_task.id}")
                try:
                    from app.services.celery_tasks import auto_assign_task
                    auto_assign_task.delay(downstream_task.id)
                except Exception as e:
                    logger.warning(f"Celery not available for auto-assign: {e}")

    def final_acceptance(self, project_id: str) -> dict:
        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        total = len(tasks)
        pending = [t for t in tasks if t.status not in (
            TaskStatus.accepted.value, TaskStatus.delivered.value
        )]
        rejected = [t for t in tasks if t.status == TaskStatus.rejected.value]
        failed = [t for t in tasks if t.status == TaskStatus.failed.value]
        accepted = [t for t in tasks if t.status == TaskStatus.accepted.value]

        passed_all = len(pending) == 0 and len(rejected) == 0 and len(failed) == 0

        return {
            "project_id": project_id,
            "passed": passed_all,
            "total_tasks": total,
            "accepted_tasks": len(accepted),
            "pending_tasks": len(pending),
            "rejected_tasks": len(rejected),
            "failed_tasks": len(failed),
            "progress_percent": int(len(accepted) / total * 100) if total > 0 else 0,
        }

    def check_acceptance_timeout(self, project_id: str) -> List[Task]:
        threshold = datetime.now(timezone.utc) - timedelta(hours=ACCEPTANCE_TIMEOUT_HOURS)
        timeout_tasks = self.db.query(Task).filter(
            and_(
                Task.project_id == project_id,
                Task.status == TaskStatus.delivered.value,
                Task.updated_at < threshold,
            )
        ).all()
        return timeout_tasks
