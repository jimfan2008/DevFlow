from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Index
from app.models.types import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_locked = Column(Boolean, nullable=False, default=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    meeting_id = Column(String, ForeignKey("meeting_outcomes.id", ondelete="SET NULL"), nullable=True)
    attachments = Column(JSONB, server_default="[]")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="requirements")

    __table_args__ = (
        Index("idx_requirements_project", "project_id"),
        Index("idx_requirements_locked", "is_locked"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "content": self.content,
            "version": self.version,
            "is_locked": self.is_locked,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "confirmed_by": self.confirmed_by,
            "meeting_id": self.meeting_id,
            "attachments": self.attachments or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
