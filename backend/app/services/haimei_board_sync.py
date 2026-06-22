"""海梅(HaiMei) 看板数据同步服务
海梅负责采集16步工作流数据，实时同步到项目看板"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session


STEP_STATUS_MAP = {
    "pending": {"column": "todo", "progress": 0, "label": "待开始"},
    "in_progress": {"column": "in_progress", "progress": 40, "label": "执行中"},
    "qa_review": {"column": "review", "progress": 70, "label": "QA检验中"},
    "completed": {"column": "done", "progress": 100, "label": "已完成"},
    "rejected": {"column": "review", "progress": 30, "label": "已驳回"},
}

STEP_PRIORITIES = {2: "high", 3: "high", 4: "high", 6: "high", 8: "high",
                   15: "high", 16: "high", 1: "medium", 5: "medium",
                   7: "medium", 9: "medium", 10: "medium", 11: "medium",
                   12: "medium", 13: "medium", 14: "medium"}

AGENT_NAMES = {
    "haimei": "海梅", "houxing": "后兴", "houwang": "后旺",
    "houfa": "后发", "houda": "后达", "houfu": "后富",
    "hougui": "后贵", "hourong": "后荣", "houhua": "后华",
}

AGENT_ICONS = {
    "haimei": "👩‍💼", "houxing": "📋", "houwang": "🏗️",
    "houfa": "🐝", "houda": "🧪", "houfu": "🚀",
    "hougui": "📝", "hourong": "✅", "houhua": "🔒",
}

HEALTH_LABELS = {
    "healthy": "健康", "busy": "忙碌", "error": "异常", "offline": "离线", "recovering": "恢复中"
}


class HaimeiBoardSyncService:
    def __init__(self, db: Session):
        self.db = db

    def get_workflow_board_data(self, project_id: str, board_id: Optional[str] = None) -> Dict[str, Any]:
        from app.services.workflow_engine import WorkflowEngine, get_default_steps
        engine = WorkflowEngine(project_id=project_id, db=self.db)
        status = engine.get_current_status()
        progress = engine.haimei_check_project_progress()
        agent_statuses = engine.haimei_get_all_agent_statuses()
        steps_def = get_default_steps()

        board_steps = []
        for s in steps_def:
            step_info = status.get("steps", {}).get(str(s.step_number), {})
            board_steps.append(self._build_step_card(s, step_info, project_id))

        agent_cards = self._build_agent_cards(agent_statuses)
        summary = self._build_summary(progress, status)

        return {
            "project_id": project_id,
            "board_id": board_id,
            "summary": summary,
            "steps": board_steps,
            "agents": agent_cards,
            "haimei_supervised_at": datetime.now(timezone.utc).isoformat(),
            "haimei_message": self._generate_haimei_message(progress, agent_statuses),
        }

    def sync_workflow_to_board(self, project_id: str, board_id: str) -> Dict[str, Any]:
        from app.services.workflow_engine import WorkflowEngine
        from app.models.task import Task
        engine = WorkflowEngine(project_id=project_id, db=self.db)
        status = engine.get_current_status()
        steps_def = engine.steps

        synced = []
        for s in steps_def:
            if s.step_number == 1:
                continue
            step_info = status.get("steps", {}).get(str(s.step_number), {})
            card = self._build_step_card(s, step_info, project_id)
            task = self._upsert_step_task(project_id, board_id, s, step_info)
            card["task_id"] = task.get("id") if task else None
            synced.append(card)

        return {
            "project_id": project_id,
            "board_id": board_id,
            "synced_count": len(synced),
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "haimei_message": "海梅已完成看板数据同步",
        }

    def _build_step_card(self, step_def, step_info: dict, project_id: str) -> Dict[str, Any]:
        step_num = step_def.step_number
        step_status = step_info.get("status", "pending")
        mapping = STEP_STATUS_MAP.get(step_status, STEP_STATUS_MAP["pending"])
        executor = step_def.executor_role or "user"
        executor_name = AGENT_NAMES.get(executor, executor)
        executor_icon = AGENT_ICONS.get(executor, "👤")

        return {
            "step_number": step_num,
            "step_name": step_def.name,
            "status": step_status,
            "column": mapping["column"],
            "progress": mapping["progress"],
            "status_label": mapping["label"],
            "executor_role": executor,
            "executor_name": executor_name,
            "executor_icon": executor_icon,
            "supervisor": "haimei" if step_def.supervisor_role == "haimei" else None,
            "completed_at": step_info.get("completed_at"),
            "qa_required": step_num in {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14},
        }

    def _build_agent_cards(self, agent_statuses: dict) -> List[Dict[str, Any]]:
        cards = []
        for agent_name, info in agent_statuses.items():
            health = info.get("health", "healthy")
            cards.append({
                "agent": agent_name,
                "name": AGENT_NAMES.get(agent_name, agent_name),
                "icon": AGENT_ICONS.get(agent_name, "🤖"),
                "health": health,
                "health_label": HEALTH_LABELS.get(health, health),
                "in_progress_step": info.get("in_progress_step"),
                "is_haimei": agent_name == "haimei",
            })
        return cards

    def _build_summary(self, progress: dict, status: dict) -> Dict[str, Any]:
        steps_data = status.get("steps", {})
        total = len(steps_data)
        completed = sum(1 for s in steps_data.values() if s.get("status") == "completed")
        in_progress = sum(1 for s in steps_data.values() if s.get("status") == "in_progress")
        qa_review = sum(1 for s in steps_data.values() if s.get("status") == "qa_review")
        rejected = sum(1 for s in steps_data.values() if s.get("status") == "rejected")

        return {
            "total_steps": total or 16,
            "completed": completed,
            "in_progress": in_progress,
            "qa_review": qa_review,
            "rejected": rejected,
            "progress_pct": progress.get("progress_pct", 0),
            "current_step": progress.get("current_step", 1),
            "blocked_steps": progress.get("blocked_steps", []),
        }

    def _upsert_step_task(self, project_id: str, board_id: str, step_def, step_info: dict) -> Optional[dict]:
        from app.models.task import Task
        step_num = step_def.step_number
        step_status = step_info.get("status", "pending")

        existing = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.type == "workflow_step",
            Task.name == f"步骤{step_num}: {step_def.name}",
        ).first()

        mapping = STEP_STATUS_MAP.get(step_status, STEP_STATUS_MAP["pending"])
        task_status_map = {
            "pending": "pending", "in_progress": "running",
            "qa_review": "delivered", "completed": "accepted", "rejected": "rejected",
        }

        executor = step_def.executor_role or "user"
        now = datetime.now(timezone.utc)

        if existing:
            existing.status = task_status_map.get(step_status, "pending")
            existing.progress = mapping["progress"]
            existing.progress_message = f"海梅: {step_def.name} - {mapping['label']}"
            existing.assignee_agent_id = executor if executor != "user" else existing.assignee_agent_id
            existing.updated_at = now
            if step_status == "completed" and not existing.completed_at:
                existing.completed_at = now
            if step_status == "in_progress" and not existing.started_at:
                existing.started_at = now
            ctx = existing.context or {}
            ctx["haimei_board_sync"] = {
                "step_number": step_num,
                "supervisor": "haimei",
                "synced_at": now.isoformat(),
            }
            existing.context = ctx
            self.db.commit()
            self.db.refresh(existing)
            return {"id": existing.id, "action": "updated"}
        else:
            import uuid
            task = Task(
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=f"步骤{step_num}: {step_def.name}",
                description=f"海梅工作流步骤 - {step_def.name}\n执行Agent: {AGENT_NAMES.get(executor, executor)}",
                type="workflow_step",
                status=task_status_map.get(step_status, "pending"),
                priority=STEP_PRIORITIES.get(step_num, "medium"),
                assignee_agent_id=executor if executor != "user" else None,
                progress=mapping["progress"],
                progress_message=f"海梅: {step_def.name} - {mapping['label']}",
                context={
                    "haimei_board_sync": {
                        "step_number": step_num,
                        "supervisor": "haimei",
                        "board_id": board_id,
                        "synced_at": now.isoformat(),
                    }
                },
                created_at=now,
                updated_at=now,
            )
            if step_status == "in_progress":
                task.started_at = now
            self.db.add(task)
            self.db.commit()
            return {"id": task.id, "action": "created"}

    def _generate_haimei_message(self, progress: dict, agent_statuses: dict) -> str:
        error_agents = [a for a, info in agent_statuses.items()
                        if info.get("health") == "error"]
        blocked = progress.get("blocked_steps", [])
        if error_agents:
            names = [AGENT_NAMES.get(a, a) for a in error_agents]
            return f"⚠️ 海梅监测到Agent异常: {', '.join(names)}，正在恢复中"
        if blocked:
            return f"⏳ 海梅等待第{blocked[0]}步QA检验通过"
        pct = progress.get("progress_pct", 0)
        cur = progress.get("current_step", 1)
        return f"📊 海梅全程监控中 | 进度 {pct}% | 当前第{cur}步"
