from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint, Boolean
from app.models.types import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    agent_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="offline")
    api_endpoint = Column(String(500), nullable=True)
    config = Column(JSONB, server_default="{}")
    discovered_by = Column(String(20), nullable=False, default="profile_scan")
    hermes_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    profile_path = Column(String(500), nullable=True)
    role_name = Column(String(50), nullable=True, index=True)
    chinese_name = Column(String(50), nullable=True)
    role_type = Column(String(30), nullable=True)
    is_named_role = Column(Boolean, default=False)
    managed_swarms = Column(JSONB, nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    hermes_skills = relationship("HermesSkill", back_populates="hermes_agent", foreign_keys="HermesSkill.hermes_agent_id")
    hermes_parent = relationship("Agent", remote_side=[id], foreign_keys=[hermes_agent_id])

    __table_args__ = (
        Index("idx_agents_type", "agent_type"),
        Index("idx_agents_status", "status"),
        Index("idx_agents_name", "name"),
        Index("idx_agents_hermes", "hermes_agent_id"),
        Index("idx_agents_role_name", "role_name"),
        CheckConstraint(
            "agent_type IN ('hermes','trae','codearts','opencode','cursor','claude_code','codebuddy','lingma','devika','codex','pi_coding_agent','reasonix','codeium','aider-chat','openhands','goose','atom','atomcode')",
            name="ck_agents_type",
        ),
        CheckConstraint("status IN ('online','offline','busy')", name="ck_agents_status"),
        CheckConstraint("discovered_by IN ('profile_scan','skill_discover')", name="ck_agents_discovered_by"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "agent_type": self.agent_type,
            "status": self.status,
            "api_endpoint": self.api_endpoint,
            "config": self.config,
            "discovered_by": self.discovered_by,
            "hermes_agent_id": self.hermes_agent_id,
            "profile_path": self.profile_path,
            "role_name": self.role_name,
            "chinese_name": self.chinese_name,
            "role_type": self.role_type,
            "is_named_role": self.is_named_role,
            "managed_swarms": self.managed_swarms,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
