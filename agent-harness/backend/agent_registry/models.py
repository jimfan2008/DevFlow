from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    ERROR = "error"


class AgentCard(BaseModel):
    agent_id: str
    name: str
    version: str
    description: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    auth_spiffe_id: Optional[str] = None
    endpoints: dict[str, str] = Field(default_factory=dict)
    status: AgentStatus = AgentStatus.INACTIVE
    metadata: dict[str, str] = Field(default_factory=dict)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthStatus(BaseModel):
    agent_id: str
    status: AgentStatus
    last_heartbeat: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    message: Optional[str] = None
    metrics: dict[str, float] = Field(default_factory=dict)


class RegisterAgentRequest(BaseModel):
    agent_id: str
    name: str
    version: str
    description: Optional[str] = None
    capabilities: Optional[list[str]] = None
    endpoints: Optional[dict[str, str]] = None


class HeartbeatRequest(BaseModel):
    status: AgentStatus
    message: Optional[str] = None
    metrics: Optional[dict[str, float]] = None


class StatusUpdateRequest(BaseModel):
    status: AgentStatus
