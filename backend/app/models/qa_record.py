from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
from app.models.types import JSONB


class QARecord(Base):
    __tablename__ = "qa_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_step_id = Column(Integer, ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    qa_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    review_dimensions = Column(JSONB, nullable=True)
    problem_details = Column(Text, nullable=True)
    fix_suggestions = Column(Text, nullable=True)
    inspected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
    workflow_step = relationship("WorkflowStep", foreign_keys=[workflow_step_id])
    qa_agent = relationship("Agent", foreign_keys=[qa_agent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "workflow_step_id": self.workflow_step_id,
            "task_id": self.task_id,
            "qa_agent_id": self.qa_agent_id,
            "status": self.status,
            "review_dimensions": self.review_dimensions,
            "problem_details": self.problem_details,
            "fix_suggestions": self.fix_suggestions,
            "inspected_at": self.inspected_at.isoformat() if self.inspected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }