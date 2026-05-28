from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
from app.models.types import JSONB


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(200), nullable=False)
    executor_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    input_artifacts = Column(JSONB, nullable=True)
    output_artifacts = Column(JSONB, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="workflow_steps")
    executor = relationship("Agent", foreign_keys=[executor_agent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "step_number": self.step_number,
            "step_name": self.step_name,
            "executor_agent_id": self.executor_agent_id,
            "status": self.status,
            "input_artifacts": self.input_artifacts,
            "output_artifacts": self.output_artifacts,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }