from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
from app.models.types import JSONB


class TDDTestCase(Base):
    __tablename__ = "tdd_test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_step_id = Column(Integer, ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=True)
    round_number = Column(Integer, nullable=False, default=1)
    case_index = Column(Integer, nullable=False, default=0)
    case_id = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    precondition = Column(Text, nullable=True)
    test_steps = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=True)
    priority = Column(String(20), nullable=True)
    category = Column(String(100), nullable=True)
    source_section = Column(String(200), nullable=True)
    qa_status = Column(String(20), nullable=False, default="pending")
    qa_score = Column(Integer, nullable=True)
    qa_feedback = Column(Text, nullable=True)
    qa_detail = Column(Text, nullable=True)
    fix_attempts = Column(Integer, nullable=False, default=0)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
    workflow_step = relationship("WorkflowStep", foreign_keys=[workflow_step_id])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "workflow_step_id": self.workflow_step_id,
            "round_number": self.round_number,
            "case_index": self.case_index,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description,
            "precondition": self.precondition,
            "test_steps": self.test_steps,
            "expected_result": self.expected_result,
            "priority": self.priority,
            "category": self.category,
            "source_section": self.source_section,
            "qa_status": self.qa_status,
            "qa_score": self.qa_score,
            "qa_feedback": self.qa_feedback,
            "qa_detail": self.qa_detail,
            "fix_attempts": self.fix_attempts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
