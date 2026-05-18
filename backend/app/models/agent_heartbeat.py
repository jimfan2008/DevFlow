from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, CheckConstraint
from app.models.types import JSONB
from datetime import datetime, timezone
import uuid
from app.database import Base


class AgentHeartbeat(Base):
    __tablename__ = "agent_heartbeats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    heartbeat_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    load_level = Column(Integer, nullable=False, default=0)
    status_detail = Column(JSONB, server_default="{}")
    via_skill = Column(String(30), nullable=True)

    __table_args__ = (
        Index("idx_heartbeats_agent", "agent_id"),
        Index("idx_heartbeats_time", "agent_id", "heartbeat_at"),
        CheckConstraint("load_level >= 0 AND load_level <= 100", name="ck_heartbeats_load"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "heartbeat_at": self.heartbeat_at.isoformat() if self.heartbeat_at else None,
            "load_level": self.load_level,
            "status_detail": self.status_detail,
            "via_skill": self.via_skill,
        }
