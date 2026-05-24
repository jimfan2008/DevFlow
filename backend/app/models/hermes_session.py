import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class HermesSession(Base):
    __tablename__ = "hermes_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    profile_name = Column(String(100), nullable=False, default="default")
    model_id = Column(String(200), nullable=False, default="hermes-agent")
    display_name = Column(String(500), nullable=True)
    message_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("HermesMessage", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_hermes_sessions_user_id", "user_id"),
        Index("ix_hermes_sessions_updated_at", "updated_at"),
    )


class HermesMessage(Base):
    __tablename__ = "hermes_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("hermes_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False, default="")
    thinking_content = Column(Text, nullable=True)
    tool_calls = Column(Text, nullable=True)
    model = Column(String(200), nullable=True)
    is_streaming = Column(Boolean, nullable=False, default=False)
    is_interrupted = Column(Boolean, nullable=False, default=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    session = relationship("HermesSession", back_populates="messages")

    __table_args__ = (
        Index("ix_hermes_messages_session_id", "session_id"),
        Index("ix_hermes_messages_timestamp", "timestamp"),
    )
