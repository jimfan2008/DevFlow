#!/usr/bin/env python3
"""
DevFlow 附件模型
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_url = Column(String(1000))
    size = Column(Integer, default=0)
    type = Column(String(100), default="application/octet-stream")
    uploaded_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="attachments")

    __table_args__ = (
        Index("idx_attachments_task", "task_id"),
        Index("idx_attachments_uploaded_by", "uploaded_by"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "file_path": self.file_path,
            "file_url": self.file_url,
            "size": self.size,
            "type": self.type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
