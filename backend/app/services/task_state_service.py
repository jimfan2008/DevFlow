from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.task import Task
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.models.acceptance_record import AcceptanceRecord
from app.models.enums import TaskStatus

logger = logging.getLogger("devflow.task_state")

TASK_TIMEOUT_HOURS = 24
MAX_REJECTION_COUNT = 3


class TaskStateService:
    def __init__(self, db: Session):
        self.db = db

    VALID_TRANSITIONS = {
        TaskStatus.pending.value: [TaskStatus.assigned.value],
        TaskStatus.assigned.value: [TaskStatus.running.value],
        TaskStatus.running.value: [TaskStatus.delivered.value, TaskStatus.failed.value],
        TaskStatus.delivered.value: [TaskStatus.accepted.value, TaskStatus.rejected.value],
        TaskStatus.failed.value: [TaskStatus.reassigned.value],
        TaskStatus.rejected.value: [TaskStatus.reassigned.value],
        TaskStatus.reassigned.value: [TaskStatus.assigned.value, TaskStatus.pending.value],
    }

    def transition(self, task_id: str, target_status: str,
                   skill_id: str = None, agent_id: str = None) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        current = task.status
        allowed = self.VALID_TRANSITIONS.get(current, [])
        if target_status not in allowed:
            raise ValueError(f"Invalid transition from {current} to {target_status}")

        if target_status == TaskStatus.assigned.value and not skill_id:
            raise ValueError("Skill-assignment required for assigned transition")

        if target_status in (TaskStatus.delivered.value, TaskStatus.failed.value) and not skill_id:
            raise ValueError("Skill-receive required for delivered/failed transition")

        task.status = target_status
        task.updated_at = datetime.now(timezone.utc)

        if target_status == TaskStatus.assigned.value:
            task.assigned_by_skill_id = skill_id
            task.assignee_agent_id = agent_id
        elif target_status == TaskStatus.running.value:
            task.started_at = datetime.now(timezone.utc)
        elif target_status == TaskStatus.accepted.value:
            task.completed_at = datetime.now(timezone.utc)
            task.progress = 100
        elif target_status == TaskStatus.delivered.value:
            pass
        elif target_status == TaskStatus.rejected.value:
            task.rejection_count = (task.rejection_count or 0) + 1
        elif target_status == TaskStatus.reassigned.value:
            task.assignee_agent_id = None
            task.assigned_by_skill_id = None

        self.db.commit()
        self.db.refresh(task)
        return task

    def skill_assign(self, task_id: str, skill_id: str, agent_id: str) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status == TaskStatus.pending.value:
            task = self.transition(task_id, TaskStatus.assigned.value,
                                   skill_id=skill_id, agent_id=agent_id)
            task = self.transition(task_id, TaskStatus.running.value,
                                   skill_id=skill_id, agent_id=agent_id)
        elif task.status == TaskStatus.reassigned.value:
            task = self.transition(task_id, TaskStatus.assigned.value,
                                   skill_id=skill_id, agent_id=agent_id)
            task = self.transition(task_id, TaskStatus.running.value,
                                   skill_id=skill_id, agent_id=agent_id)
        return task

    def skill_receive_delivery(self, task_id: str, skill_id: str,
                               result_summary: str = None,
                               artifacts: dict = None) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task = self.transition(task_id, TaskStatus.delivered.value, skill_id=skill_id)
        if result_summary:
            task.result_summary = result_summary
        if artifacts:
            task.artifacts = artifacts
        self.db.commit()
        self.db.refresh(task)
        return task

    def skill_receive_failure(self, task_id: str, skill_id: str,
                              error_detail: str = None) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task = self.transition(task_id, TaskStatus.failed.value, skill_id=skill_id)
        if error_detail:
            task.progress_message = error_detail
        self.db.commit()
        self.db.refresh(task)
        return task

    def accept_task(self, task_id: str, reviewer_agent_id: str,
                    suggestions: str = None) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task = self.transition(task_id, TaskStatus.accepted.value)

        record = AcceptanceRecord(
            id=str(uuid.uuid4()),
            task_id=task_id,
            reviewer_agent_id=reviewer_agent_id,
            result="accepted",
            suggestions=suggestions,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(task)
        return task

    def reject_task(self, task_id: str, reviewer_agent_id: str,
                    problem_details: str = None, suggestions: str = None) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task = self.transition(task_id, TaskStatus.rejected.value)

        record = AcceptanceRecord(
            id=str(uuid.uuid4()),
            task_id=task_id,
            reviewer_agent_id=reviewer_agent_id,
            result="rejected",
            problem_details=problem_details,
            suggestions=suggestions,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(task)
        return task

    def check_dependency_readiness(self, task_id: str) -> bool:
        from app.models.dependency import TaskDependency
        deps = self.db.query(TaskDependency).filter(
            TaskDependency.target_task_id == task_id
        ).all()
        if not deps:
            return True
        for dep in deps:
            source = self.db.query(Task).filter(Task.id == dep.source_task_id).first()
            if not source or source.status != TaskStatus.accepted.value:
                return False
        return True

    def get_ready_tasks_for_skill_assignment(self, project_id: str) -> List[Task]:
        tasks = self.db.query(Task).filter(
            and_(
                Task.project_id == project_id,
                Task.status == TaskStatus.pending.value,
            )
        ).all()

        ready = []
        for task in tasks:
            if self.check_dependency_readiness(task.id):
                ready.append(task)
        return ready

    def handle_timeout(self, task_id: str) -> Optional[Task]:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        if task.status != TaskStatus.running.value:
            return None
        if not task.started_at:
            return None

        elapsed = datetime.now(timezone.utc) - task.started_at
        if elapsed > timedelta(hours=TASK_TIMEOUT_HOURS):
            task = self.transition(task_id, TaskStatus.failed.value,
                                   skill_id=task.assigned_by_skill_id)
            task.progress_message = f"Task timed out after {TASK_TIMEOUT_HOURS} hours"
            self.db.commit()
            self.db.refresh(task)
            return task
        return None

    def reassign_failed_task(self, task_id: str, new_skill_id: str = None,
                             new_agent_id: str = None) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status not in (TaskStatus.failed.value, TaskStatus.rejected.value):
            raise ValueError(f"Task status {task.status} cannot be reassigned")

        task = self.transition(task_id, TaskStatus.reassigned.value)
        if new_skill_id and new_agent_id:
            task = self.skill_assign(task_id, new_skill_id, new_agent_id)
        return task

    def check_rejection_escalation(self, task_id: str) -> bool:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        return (task.rejection_count or 0) >= MAX_REJECTION_COUNT

    def get_tasks_by_status(self, project_id: str, status: str = None) -> List[Task]:
        query = self.db.query(Task).filter(Task.project_id == project_id)
        if status:
            query = query.filter(Task.status == status)
        return query.order_by(Task.created_at.desc()).all()
