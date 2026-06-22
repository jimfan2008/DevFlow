#!/usr/bin/env python3
"""评论服务"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid


class CommentService:
    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def _import_models(self):
        from app.models.comment import Comment
        from app.models.task import Task
        return Comment, Task

    def create_comment(self, task_id: str, content: str) -> dict:
        Comment, Task = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        comment = Comment(
            id=str(uuid.uuid4()),
            task_id=task_id,
            user_id=self.current_user_id,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment.to_dict()

    def get_comments(self, task_id: str) -> list:
        Comment, = self._import_models()[:1]
        comments = self.db.query(Comment).filter(
            Comment.task_id == task_id
        ).order_by(Comment.created_at).all()
        return [c.to_dict() for c in comments]

    def delete_comment(self, comment_id: str) -> bool:
        Comment, = self._import_models()[:1]
        comment = self.db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise ValueError("评论不存在")
        self.db.delete(comment)
        self.db.commit()
        return True
