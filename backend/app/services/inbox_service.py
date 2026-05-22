#!/usr/bin/env python3
"""收件箱服务 - 通知聚合、搜索、偏好设置"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import json


class InboxService:
    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def _import_models(self):
        from app.models.notification import InboxItem, Notification
        from app.models.task import Task
        from app.models.user import User
        return InboxItem, Notification, Task, User

    def get_inbox(self, user_id: str, category: str = None, page: int = 1, per_page: int = 20) -> dict:
        InboxItem, Notification, Task, User = self._import_models()
        query = self.db.query(InboxItem).filter(InboxItem.user_id == user_id)
        if category:
            query = query.filter(InboxItem.type == category)
        total = query.count()
        items = query.order_by(InboxItem.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        unread = self.db.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.is_read == False
        ).count()
        return {
            "items": [self._item_to_dict(item) for item in items],
            "total": total,
            "unread_count": unread,
        }

    def mark_as_read(self, item_id: str) -> dict:
        InboxItem, = self._import_models()[:1]
        item = self.db.query(InboxItem).filter(InboxItem.id == item_id).first()
        if not item:
            raise ValueError("收件箱消息不存在")
        item.is_read = True
        self.db.commit()
        self.db.refresh(item)
        return item.to_dict()

    def mark_all_as_read(self, user_id: str) -> dict:
        InboxItem, = self._import_models()[:1]
        items = self.db.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.is_read == False
        ).all()
        count = len(items)
        for item in items:
            item.is_read = True
        self.db.commit()
        return {"marked_count": count}

    def get_unread_count(self, user_id: str) -> dict:
        InboxItem, = self._import_models()[:1]
        count = self.db.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.is_read == False
        ).count()
        return {"count": count}

    def get_search_results(self, user_id: str, query: str) -> dict:
        InboxItem, Notification, Task, User = self._import_models()
        items = self.db.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.title.like(f"%{query}%") |
            InboxItem.content.like(f"%{query}%")
        ).order_by(InboxItem.created_at.desc()).all()
        return {
            "items": [self._item_to_dict(item) for item in items],
            "total": len(items),
        }

    def get_preferences(self, user_id: str) -> dict:
        InboxItem, Notification, Task, User = self._import_models()
        prefs = self.db.query(Notification).filter(
            Notification.user_id == user_id
        ).first()
        if not prefs:
            prefs = Notification(
                id=str(__import__("uuid").uuid4()),
                user_id=user_id,
                frequency="realtime",
                notify_types=json.dumps(["assigned", "commented", "status_change"]),
                suppress_watch=False,
            )
            self.db.add(prefs)
            self.db.commit()
        return prefs.to_dict()

    def update_preferences(self, user_id: str, **kwargs) -> dict:
        InboxItem, Notification, Task, User = self._import_models()
        prefs = self.db.query(Notification).filter(
            Notification.user_id == user_id
        ).first()
        if not prefs:
            prefs = Notification(
                id=str(__import__("uuid").uuid4()),
                user_id=user_id,
                frequency="realtime",
                notify_types=json.dumps(["assigned", "commented", "status_change"]),
                suppress_watch=False,
            )
            self.db.add(prefs)
        for key, value in kwargs.items():
            if value is not None and hasattr(prefs, key):
                if key == "notify_types" and isinstance(value, list):
                    setattr(prefs, key, json.dumps(value))
                else:
                    setattr(prefs, key, value)
        prefs.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(prefs)
        return prefs.to_dict()

    def get_reminders(self, user_id: str) -> list:
        InboxItem, Notification, Task, User = self._import_models()
        now = datetime.now(timezone.utc)
        tasks = self.db.query(Task).filter(
            Task.assignee_agent_id == user_id,
            Task.status != "accepted",
            Task.deadline != None
        ).all()
        reminders = []
        for task in tasks:
            if task.deadline:
                days_remaining = (task.deadline - now).days
                if days_remaining <= 0:
                    reminders.append({
                        "task_id": task.id,
                        "task_name": task.name,
                        "deadline": task.deadline.isoformat(),
                        "days_remaining": days_remaining,
                        "priority": task.priority,
                        "level": "urgent",
                    })
                elif days_remaining <= 1:
                    reminders.append({
                        "task_id": task.id,
                        "task_name": task.name,
                        "deadline": task.deadline.isoformat(),
                        "days_remaining": days_remaining,
                        "priority": task.priority,
                        "level": "soon",
                    })
                elif days_remaining <= 3:
                    reminders.append({
                        "task_id": task.id,
                        "task_name": task.name,
                        "deadline": task.deadline.isoformat(),
                        "days_remaining": days_remaining,
                        "priority": task.priority,
                        "level": "upcoming",
                    })
        return reminders

    def watch_task(self, user_id: str, task_id: str) -> dict:
        InboxItem, Notification, Task, User = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        # Create or update watch entry
        existing = self.db.query(InboxItem).filter(
            InboxItem.user_id == user_id,
            InboxItem.task_id == task_id,
            InboxItem.type == "watched"
        ).first()
        if existing:
            existing.is_read = False
            self.db.commit()
            return self._item_to_dict(existing)
        item = InboxItem(
            id=str(__import__("uuid").uuid4()),
            user_id=user_id,
            task_id=task_id,
            type="watched",
            title=f"开始关注: {task.name}",
            content="",
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return self._item_to_dict(item)

    def _item_to_dict(self, item):
        d = item.to_dict()
        if item.task_id:
            Task, = self._import_models()[2:3]
            task = self.db.query(Task).filter(Task.id == item.task_id).first()
            if task:
                d["task_name"] = task.name
                d["task_status"] = task.status
        return d
