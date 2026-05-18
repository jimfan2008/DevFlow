from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class AcceptanceRecord(Base):
    __tablename__ = "acceptance_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    reviewer_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=False)
    result = Column(String(20), nullable=False)
    problem_details = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="acceptance_records")
    reviewer_agent = relationship("Agent", foreign_keys=[reviewer_agent_id])

    __table_args__ = (
        Index("idx_acceptance_task", "task_id"),
        CheckConstraint("result IN ('accepted','rejected')", name="ck_acceptance_result"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "reviewer_agent_id": self.reviewer_agent_id,
            "result": self.result,
            "problem_details": self.problem_details,
            "suggestions": self.suggestions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
