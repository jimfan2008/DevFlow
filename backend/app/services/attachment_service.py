#!/usr/bin/env python3
"""附件服务"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid
import os


class AttachmentService:
    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def _import_models(self):
        from app.models.attachment import Attachment
        from app.models.task import Task
        return Attachment, Task

    def add_attachment(self, task_id: str, name: str, file_path: str,
                       size=0, type="application/octet-stream") -> dict:
        Attachment, Task = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        attachment = Attachment(
            id=str(uuid.uuid4()),
            task_id=task_id,
            name=name,
            file_path=file_path,
            file_url=None,
            size=size,
            type=type,
            uploaded_by=self.current_user_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment.to_dict()

    def get_attachments(self, task_id: str) -> list:
        Attachment, = self._import_models()[:1]
        attachments = self.db.query(Attachment).filter(
            Attachment.task_id == task_id
        ).all()
        return [a.to_dict() for a in attachments]

    def delete_attachment(self, attachment_id: str) -> bool:
        Attachment, = self._import_models()[:1]
        attachment = self.db.query(Attachment).filter(Attachment.id == attachment_id).first()
        if not attachment:
            raise ValueError("附件不存在")
        self.db.delete(attachment)
        self.db.commit()
        return True
