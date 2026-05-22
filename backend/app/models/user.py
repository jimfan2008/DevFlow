from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index, CheckConstraint
from app.models.types import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    avatar_url = Column(String(500), nullable=True)
    notification_config = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="creator", foreign_keys="Project.creator_id")
    comments = relationship("Comment", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
    )

    def to_dict(self, include_relations=False):
        d = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "notification_config": self.notification_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        return d
