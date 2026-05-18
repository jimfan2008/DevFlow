#!/usr/bin/env python3
"""任务服务 - 处理任务CRUD、状态流转、依赖、评论、附件"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import uuid
import json


class TaskService:
    STATUS_TRANSITIONS = {
        "todo": ["in_progress", "done"],
        "in_progress": ["review", "done", "todo"],
        "review": ["in_progress", "done"],
        "done": ["todo"],
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

    def create_task(self, board_id: str, title: str, description=None,
                    status="todo", priority="medium", assignee_id=None,
                    due_date=None, estimated_hours=None, column_id=None) -> dict:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        board = self.db.query(Board).filter(Board.id == board_id).first()
        if not board:
            raise ValueError("看板不存在")
        task = Task(
            id=str(uuid.uuid4()),
            board_id=board_id,
            title=title,
            description=description or "",
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            creator_id=self.current_user_id,
            watcher_ids="[]",
            column_id=column_id,
            due_date=due_date,
            estimated_hours=estimated_hours,
            actual_hours=0,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        result = self._task_to_dict(task)
        result["inbox_created"] = False
        if assignee_id and assignee_id != self.current_user_id:
            inbox = InboxItem(
                id=str(uuid.uuid4()),
                user_id=assignee_id,
                task_id=task.id,
                type="assigned",
                title=f"任务已分配: {title}",
                content=f"您被分配了任务: {title}",
                is_read=False,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(inbox)
            self.db.commit()
            result["inbox_created"] = True
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
        old_assignee = task.assignee_id
        for key, value in kwargs.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        result = self._task_to_dict(task)
        # Check if status changed
        if old_status != task.status:
            result["board_update"] = {"status_changed": True, "old_status": old_status, "new_status": task.status}
            # Create inbox item for status change
            if task.assignee_id and task.assignee_id != self.current_user_id:
                inbox = InboxItem(
                    id=str(uuid.uuid4()),
                    user_id=task.assignee_id,
                    task_id=task.id,
                    type="status_change",
                    title=f"任务状态变更: {task.title}",
                    content=f"任务状态已从 {old_status} 变更为 {task.status}",
                    is_read=False,
                    created_at=datetime.now(timezone.utc),
                )
                self.db.add(inbox)
                self.db.commit()
                result["inbox_created"] = True
            else:
                result["inbox_created"] = False
        else:
            result["board_update"] = None
            result["inbox_created"] = False
        # Update blocked status for dependent tasks
        self._update_dependent_blocked_status(task_id)
        return result

    def delete_task(self, task_id: str) -> bool:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        self.db.delete(task)
        self.db.commit()
        return True

    def list_tasks(self, board_id=None, status=None, assignee_id=None,
                   page=1, per_page=20) -> dict:
        Task, Board, BoardColumn, Comment, Attachment, User, InboxItem, *_ = self._import_models()
        query = self.db.query(Task)
        if board_id:
            query = query.filter(Task.board_id == board_id)
        if status:
            query = query.filter(Task.status == status)
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)
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
        if status not in self.STATUS_TRANSITIONS.get(task.status, []):
            raise ValueError(f"从 {task.status} 到 {status} 的状态转换不合法")
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        if column_id:
            task.column_id = column_id
        if order_in_column is not None:
            task.order_in_column = order_in_column
        if status == "in_progress" and not task.started_at:
            task.started_at = datetime.now(timezone.utc)
        if status == "done":
            task.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        result = self._task_to_dict(task)
        result["board_update"] = {"status_changed": True, "old_status": status, "new_status": status}
        result["inbox_created"] = True
        return result

    def _update_dependent_blocked_status(self, task_id: str):
        from app.models.dependency import TaskDependency
        Task, = self._import_models()[:1]
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or task.status != "done":
            return
        deps = self.db.query(TaskDependency).filter(
            TaskDependency.source_task_id == task_id
        ).all()
        for dep in deps:
            target = self.db.query(Task).filter(Task.id == dep.target_task_id).first()
            if target:
                target.is_blocked = False
                target.blocked_by_count = max(0, target.blocked_by_count - 1)
        self.db.commit()

    def _task_to_dict(self, task) -> dict:
        def _user_brief(u):
            return {"id": u.id, "username": u.username, "display_name": u.full_name or u.username} if u else None
        result = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "board_id": task.board_id,
            "column_id": task.column_id,
            "status": task.status,
            "priority": task.priority,
            "is_blocked": task.is_blocked,
            "blocked": task.is_blocked,
            "blocked_by_count": task.blocked_by_count,
            "assignee_id": task.assignee_id,
            "assignee": _user_brief(task.assignee),
            "creator_id": task.creator_id,
            "creator": _user_brief(task.creator) or {"id": task.creator_id, "username": "system", "display_name": "System"},
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "due_overdue": bool(task.due_date and task.due_date < datetime.now(timezone.utc)) if task.due_date else False,
            "estimated_hours": task.estimated_hours,
            "actual_hours": task.actual_hours,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "order_in_column": task.order_in_column,
            "is_visible": task.is_visible,
            "acceptance_criteria": task.acceptance_criteria,
            "agent_type": task.agent_type,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "tags": [],
            "comments_count": len(task.comments) if task.comments else 0,
            "attachments_count": len(task.attachments) if task.attachments else 0,
            "predecessors": [],
            "successors": [],
            "attachments": [a.to_dict() if hasattr(a, 'to_dict') else {"id": a.id, "filename": getattr(a, 'name', a.id)} for a in (task.attachments or [])],
        }
        if task.source_dependencies:
            result["predecessors"] = [
                {"id": d.source_task.id, "title": d.source_task.title, "status": d.source_task.status}
                for d in task.source_dependencies if d.source_task
            ]
        if task.target_dependencies:
            result["successors"] = [
                {"id": d.target_task.id, "title": d.target_task.title, "status": d.target_task.status}
                for d in task.target_dependencies if d.target_task
            ]
        if task.watcher_ids:
            try:
                result["watcher_ids"] = json.loads(task.watcher_ids) if isinstance(task.watcher_ids, str) else task.watcher_ids
            except:
                result["watcher_ids"] = []
        else:
            result["watcher_ids"] = []
        return result
