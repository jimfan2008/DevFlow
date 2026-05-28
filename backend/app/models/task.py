from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, Index, CheckConstraint
from app.models.types import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)
    priority = Column(String(10), nullable=False, default="medium")
    agent_type_preference = Column(String(20), nullable=True)
    assignee_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    assigned_by_skill_id = Column(String, ForeignKey("hermes_skills.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    acceptance_criteria = Column(Text, nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    context = Column(JSONB, server_default="{}")
    progress = Column(Integer, nullable=False, default=0)
    progress_message = Column(Text, nullable=True)
    rejection_count = Column(Integer, nullable=False, default=0)
    result_summary = Column(Text, nullable=True)
    artifacts = Column(JSONB, server_default="{}")
    test_results = Column(JSONB, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="tasks")
    assignee = relationship("Agent", foreign_keys=[assignee_agent_id])
    assigned_by_skill = relationship("HermesSkill", foreign_keys=[assigned_by_skill_id])
    source_dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.source_task_id", back_populates="source_task")
    target_dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.target_task_id", back_populates="target_task")
    execution_logs = relationship("AgentExecutionLog", back_populates="task", cascade="all, delete-orphan")
    acceptance_records = relationship("AcceptanceRecord", back_populates="task", cascade="all, delete-orphan")
    task_commits = relationship("TaskCommit", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tasks_project", "project_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_assignee", "assignee_agent_id"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_type", "type"),
        Index("idx_tasks_assigned_skill", "assigned_by_skill_id"),
        CheckConstraint("priority IN ('high','medium','low')", name="ck_tasks_priority"),
        CheckConstraint(
            "status IN ('pending','assigned','running','in_progress','delivered','accepted','failed','rejected','reassigned')",
            name="ck_tasks_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_tasks_progress"),
    )

    def to_dict(self, include_relations=False):
        d = {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "priority": self.priority,
            "agent_type_preference": self.agent_type_preference,
            "assignee_agent_id": self.assignee_agent_id,
            "assigned_by_skill_id": self.assigned_by_skill_id,
            "status": self.status,
            "acceptance_criteria": self.acceptance_criteria,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "result_summary": self.result_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        return d
