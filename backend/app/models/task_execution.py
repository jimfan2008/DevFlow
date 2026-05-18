#!/usr/bin/env python3
"""
DevFlow 任务执行模型 - 记录编程 Agent 对任务的执行情况
"""
from sqlalchemy import Column, String, Text, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class TaskExecution(Base):
    __tablename__ = "task_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="pending")  # pending/running/delivered/accepted/rejected
    execution_log = Column(Text, nullable=True)
    result_summary = Column(JSON, nullable=True)
    problem_details = Column(JSON, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    task = relationship("Task", back_populates="executions")
    agent = relationship("Agent")
    acceptance_records = relationship("AcceptanceRecord", back_populates="execution", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "execution_log": self.execution_log,
            "result_summary": self.result_summary,
            "problem_details": self.problem_details,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }