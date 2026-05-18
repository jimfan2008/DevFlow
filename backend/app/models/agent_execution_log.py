from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    execution_content = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    via_skill_type = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="execution_logs")
    agent = relationship("Agent")

    __table_args__ = (
        Index("idx_exec_logs_task", "task_id"),
        Index("idx_exec_logs_agent", "agent_id"),
        Index("idx_exec_logs_skill", "via_skill_type"),
        CheckConstraint(
            "via_skill_type IN ('discover_agent','connect_agent','assign_task','receive_message') OR via_skill_type IS NULL",
            name="ck_exec_logs_skill_type",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "execution_content": self.execution_content,
            "result": self.result,
            "via_skill_type": self.via_skill_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
