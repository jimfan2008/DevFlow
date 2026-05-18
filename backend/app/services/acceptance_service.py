# 成果验收服务 - 对编程 Agent 交付的成果进行自动化验收
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.acceptance_record import AcceptanceRecord
from app.models.task_execution import TaskExecution
from app.models.task import Task

logger = logging.getLogger("devflow.acceptance")


class AcceptanceService:
    def __init__(self, db: Session):
        self.db = db

    def verify_delivery(self, execution_id: str) -> dict:
        """对编程 Agent 交付的成果进行自动验收。"""
        execution = self.db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        result_summary = execution.result_summary or {}
        checks = self._run_checks(result_summary)
        passed = all(c["passed"] for c in checks.values())

        record = AcceptanceRecord(
            id=str(uuid.uuid4()),
            task_execution_id=execution_id,
            result="pass" if passed else "fail",
            problem_details=checks,
            reviewer="Hermes Agent",
        )
        self.db.add(record)

        execution.status = "accepted" if passed else "rejected"
        if passed:
            execution.problem_details = None
        else:
            execution.problem_details = checks

        self.db.commit()
        self.db.refresh(record)

        return {
            "acceptance_id": record.id,
            "result": record.result,
            "checks": checks,
            "suggestions": self._generate_suggestions(checks) if not passed else [],
        }

    def _run_checks(self, result: dict) -> dict:
        """执行验收检查项。"""
        coverage = result.get("coverage", 0)
        test_pass_rate = result.get("test_pass_rate", 0)
        has_output = bool(result.get("output"))

        return {
            "coverage_check": {
                "passed": coverage >= 80 if coverage else False,
                "detail": f"代码覆盖度: {coverage}% (要求 >= 80%)",
            },
            "test_pass_rate_check": {
                "passed": test_pass_rate >= 90 if test_pass_rate else False,
                "detail": f"测试通过率: {test_pass_rate}% (要求 >= 90%)",
            },
            "output_check": {
                "passed": has_output,
                "detail": "交付成果文件存在" if has_output else "缺少交付成果文件",
            },
        }

    def _generate_suggestions(self, checks: dict) -> list[str]:
        """生成驳回修改建议。"""
        suggestions = []
        for name, check in checks.items():
            if not check["passed"]:
                suggestions.append(check["detail"])
        return suggestions

    def final_acceptance(self, project_id: str) -> dict:
        """全项目最终验收 - 验证所有任务均验收通过。"""
        from app.models.board import Board

        tasks = self.db.query(Task).join(Board).filter(Board.project_id == project_id).all()

        total = len(tasks)
        pending = [t for t in tasks if t.status not in ("done", "accepted")]
        rejected = [t for t in tasks if t.status == "rejected"]

        passed_all = len(pending) == 0 and len(rejected) == 0
        return {
            "project_id": project_id,
            "passed": passed_all,
            "total_tasks": total,
            "pending_tasks": len(pending),
            "rejected_tasks": len(rejected),
            "pending_details": [{"id": t.id, "title": t.title, "status": t.status} for t in pending[:20]],
            "rejected_details": [{"id": t.id, "title": t.title, "status": t.status} for t in rejected[:20]],
        }