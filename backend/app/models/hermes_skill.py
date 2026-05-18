from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from app.models.types import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class HermesSkill(Base):
    __tablename__ = "hermes_skills"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    hermes_agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    skill_type = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    config = Column(JSONB, server_default="{}")
    last_executed_at = Column(DateTime(timezone=True), nullable=True)
    execution_stats = Column(JSONB, server_default="{}")
    coding_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    connection_status = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    hermes_agent = relationship("Agent", back_populates="hermes_skills", foreign_keys=[hermes_agent_id])
    coding_agent = relationship("Agent", foreign_keys=[coding_agent_id])
    task = relationship("Task", foreign_keys=[task_id])

    __table_args__ = (
        Index("idx_hermes_skills_agent", "hermes_agent_id"),
        Index("idx_hermes_skills_type", "skill_type"),
        Index("idx_hermes_skills_status", "status"),
        Index("idx_hermes_skills_coding_agent", "coding_agent_id"),
        Index("idx_hermes_skills_task", "task_id"),
        CheckConstraint(
            "skill_type IN ('discover_agent','connect_agent','assign_task','receive_message','execute_task','review_result','generate_report','manage_repo','coordinate_meeting')",
            name="ck_hermes_skills_type",
        ),
        CheckConstraint("status IN ('active','inactive','error')", name="ck_hermes_skills_status"),
        CheckConstraint(
            "connection_status IN ('connected','disconnected','reconnecting') OR connection_status IS NULL",
            name="ck_hermes_skills_connection",
        ),
        UniqueConstraint("hermes_agent_id", "skill_type", name="uq_hermes_skills_agent_type"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "hermes_agent_id": self.hermes_agent_id,
            "skill_type": self.skill_type,
            "status": self.status,
            "config": self.config,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "execution_stats": self.execution_stats,
            "coding_agent_id": self.coding_agent_id,
            "task_id": self.task_id,
            "connection_status": self.connection_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
