from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    channel = Column(String(20), nullable=False, default="platform")
    is_read = Column(Boolean, nullable=False, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user", "user_id"),
        Index("idx_notifications_read", "user_id", "is_read"),
        Index("idx_notifications_project", "project_id"),
        CheckConstraint("channel IN ('platform','email','sms')", name="ck_notifications_channel"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "channel": self.channel,
            "is_read": self.is_read,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

