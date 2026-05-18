from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Index, CheckConstraint
from app.models.types import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    members = Column(JSONB, nullable=False, server_default="[]")
    host_agent = Column(String(100), nullable=True)
    mode = Column(String(20), nullable=False, default="discussion")
    project_id = Column(String, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("GroupMessage", back_populates="group", cascade="all, delete-orphan")
    meeting_outcomes = relationship("MeetingOutcome", back_populates="group", cascade="all, delete-orphan")
    group_tasks = relationship("GroupTask", back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_groups_project", "project_id"),
        Index("idx_groups_mode", "mode"),
        CheckConstraint("mode IN ('discussion','meeting')", name="ck_groups_mode"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "members": self.members or [],
            "host_agent": self.host_agent,
            "mode": self.mode,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GroupMessage(Base):
    __tablename__ = "group_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_streaming = Column(Boolean, nullable=False, default=False)
    msg_metadata = Column(JSONB, server_default="{}")

    group = relationship("Group", back_populates="messages")

    __table_args__ = (
        Index("idx_group_msgs_group", "group_id"),
        Index("idx_group_msgs_timestamp", "group_id", "timestamp"),
        CheckConstraint("role IN ('user','assistant','system')", name="ck_group_msgs_role"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "sender": self.sender,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_streaming": self.is_streaming,
            "metadata": self.msg_metadata or {},
        }


class MeetingOutcome(Base):
    __tablename__ = "meeting_outcomes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    meeting_topic = Column(String(500), nullable=False)
    meeting_type = Column(String(30), nullable=False)
    host_agent = Column(String(100), nullable=False)
    agenda = Column(JSONB, server_default="[]")
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    minutes = Column(Text, nullable=True)
    decisions = Column(JSONB, server_default="[]")
    todos = Column(JSONB, server_default="[]")
    risks = Column(JSONB, server_default="[]")
    open_issues = Column(JSONB, server_default="[]")

    group = relationship("Group", back_populates="meeting_outcomes")

    __table_args__ = (
        Index("idx_meeting_outcomes_group", "group_id"),
        Index("idx_meeting_outcomes_type", "meeting_type"),
        CheckConstraint(
            "meeting_type IN ('requirement_review','tech_solution','daily_standup','incident_postmortem')",
            name="ck_meeting_type",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "meeting_topic": self.meeting_topic,
            "meeting_type": self.meeting_type,
            "host_agent": self.host_agent,
            "agenda": self.agenda or [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "minutes": self.minutes,
            "decisions": self.decisions or [],
            "todos": self.todos or [],
            "risks": self.risks or [],
            "open_issues": self.open_issues or [],
        }


class GroupTask(Base):
    __tablename__ = "group_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(String, ForeignKey("meeting_outcomes.id", ondelete="SET NULL"), nullable=True)
    assignee = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    result = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    group = relationship("Group", back_populates="group_tasks")

    __table_args__ = (
        Index("idx_group_tasks_group", "group_id"),
        Index("idx_group_tasks_meeting", "meeting_id"),
        Index("idx_group_tasks_assignee", "assignee"),
        CheckConstraint("status IN ('pending','in_progress','completed')", name="ck_group_tasks_status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "meeting_id": self.meeting_id,
            "assignee": self.assignee,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
