#!/usr/bin/env python3
"""任务服务 - 处理任务CRUD、状态流转、依赖、评论、附件"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import uuid
import json


class TaskService:
    STATUS_TRANSITIONS = {
        "pending": ["assigned", "running"],
        "assigned": ["running", "pending", "reassigned"],
        "running": ["delivered", "failed", "assigned"],
        "delivered": ["accepted", "rejected", "running"],
        "accepted": [],
        "rejected": ["running", "assigned"],
        "failed": ["running", "assigned"],
        "reassigned": ["assigned", "running"],
    }

    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def _import_models(self):
        from app.models.task import Task
        from app.models.board import Board, BoardColumn
        from app.models.comment import Comment
        from app.models.attachment import Attachment
        from app.models.user import User
        from app.models.notification import InboxItem
        from app.models.dependency import TaskDependency
        return Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, TaskDependency

    def create_task(self, project_id: str, name: str, type: str = "coding",
                    description=None, status="pending", priority="medium",
                    agent_type_preference=None, assignee_agent_id=None,
                    acceptance_criteria=None, deadline=None) -> dict:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description or "",
            type=type,
            status=status,
            priority=priority,
            agent_type_preference=agent_type_preference,
            assignee_agent_id=assignee_agent_id,
            acceptance_criteria=acceptance_criteria,
            deadline=deadline,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        result = self._task_to_dict(task)
        result["inbox_created"] = False
        if assignee_agent_id and status == "assigned":
            try:
                inbox = InboxItem(
                    id=str(uuid.uuid4()),
                    user_id=assignee_agent_id,
                    task_id=task.id,
                    type="assigned",
                    title=f"任务已分配: {name}",
                    content=f"您被分配了任务: {name}",
                    is_read=False,
                    created_at=datetime.now(timezone.utc),
                )
                self.db.add(inbox)
                self.db.commit()
                result["inbox_created"] = True
            except Exception:
                pass
        return result

    def get_task(self, task_id: str, include_comments=False) -> dict:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, TaskDependency = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        result = self._task_to_dict(task)
        if include_comments:
            comments = self.db.query(Comment).filter(
                Comment.task_id == task_id
            ).order_by(Comment.created_at).all()
            result["comments"] = [c.to_dict() for c in comments]
        deps = self.db.query(
            TaskDependency
        ).filter(
            (TaskDependency.source_task_id == task_id) |
            (TaskDependency.target_task_id == task_id)
        ).all()
        result["dependencies"] = [d.to_dict() for d in deps]
        return result

    def update_task(self, task_id: str, **kwargs) -> dict:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        old_status = task.status
        for key, value in kwargs.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        result = self._task_to_dict(task)
        if old_status != task.status:
            result["board_update"] = {"status_changed": True, "old_status": old_status, "new_status": task.status}
        else:
            result["board_update"] = None
        result["inbox_created"] = False
        return result

    def delete_task(self, task_id: str) -> bool:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        self.db.delete(task)
        self.db.commit()
        return True

    def list_tasks(self, project_id=None, status=None, assignee_agent_id=None,
                   page=1, per_page=20) -> dict:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        query = self.db.query(Task)
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if status:
            query = query.filter(Task.status == status)
        if assignee_agent_id:
            query = query.filter(Task.assignee_agent_id == assignee_agent_id)
        total = query.count()
        tasks = query.order_by(Task.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        return {
            "tasks": [self._task_to_dict(t) for t in tasks],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def move_task(self, task_id: str, status: str, column_id=None, order_in_column=None) -> dict:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        if status == "running" and not task.started_at:
            task.started_at = datetime.now(timezone.utc)
        if status == "accepted":
            task.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        result = self._task_to_dict(task)
        result["board_update"] = {"status_changed": True, "new_status": status}
        result["inbox_created"] = False
        return result

    def _task_to_dict(self, task) -> dict:
        result = {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "project_id": task.project_id,
            "type": task.type,
            "status": task.status,
            "priority": task.priority,
            "agent_type_preference": task.agent_type_preference,
            "assignee_agent_id": task.assignee_agent_id,
            "assigned_by_skill_id": task.assigned_by_skill_id,
            "acceptance_criteria": task.acceptance_criteria,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "progress": task.progress,
            "progress_message": task.progress_message,
            "rejection_count": task.rejection_count,
            "result_summary": task.result_summary,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
        if task.source_dependencies:
            result["predecessors"] = [
                {"id": d.source_task.id, "name": d.source_task.name, "status": d.source_task.status}
                for d in task.source_dependencies if d.source_task
            ]
        if task.target_dependencies:
            result["successors"] = [
                {"id": d.target_task.id, "name": d.target_task.name, "status": d.target_task.status}
                for d in task.target_dependencies if d.target_task
            ]
        return result
