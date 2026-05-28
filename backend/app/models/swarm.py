from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
from app.models.types import JSONB


class Swarm(Base):
    __tablename__ = "swarms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    manager_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=False)
    name = Column(String(200), nullable=False)
    purpose = Column(String(20), nullable=False)
    step_number = Column(Integer, nullable=False)
    members = Column(JSONB, nullable=False, server_default="[]")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    disbanded_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", foreign_keys=[project_id])
    manager = relationship("Agent", foreign_keys=[manager_agent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "manager_agent_id": self.manager_agent_id,
            "name": self.name,
            "purpose": self.purpose,
            "step_number": self.step_number,
            "members": self.members,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "disbanded_at": self.disbanded_at.isoformat() if self.disbanded_at else None,
        }


class SwarmTask(Base):
    __tablename__ = "swarm_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    swarm_id = Column(Integer, ForeignKey("swarms.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    assigned_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    swarm = relationship("Swarm", foreign_keys=[swarm_id])
    assigned_agent = relationship("Agent", foreign_keys=[assigned_agent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "swarm_id": self.swarm_id,
            "task_id": self.task_id,
            "assigned_agent_id": self.assigned_agent_id,
            "status": self.status,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }