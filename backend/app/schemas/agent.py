from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.enums import AgentType, AgentStatus, DiscoveredBy


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    agent_type: str
    api_endpoint: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    discovered_by: str = "profile_scan"
    hermes_agent_id: Optional[str] = None
    profile_path: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    agent_type: Optional[str] = None
    status: Optional[str] = None
    api_endpoint: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    hermes_agent_id: Optional[str] = None
    profile_path: Optional[str] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
    api_endpoint: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    discovered_by: str
    hermes_agent_id: Optional[str] = None
    profile_path: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


class AgentAssignRequest(BaseModel):
    task_id: str
    agent_id: str


class AgentAssignResponse(BaseModel):
    execution_id: str
    task_id: str
    agent_id: str
    status: str


class TaskDeliverRequest(BaseModel):
    result: Dict[str, Any]


class AgentLoadResponse(BaseModel):
    agent_id: str
    current_load: int
    max_load: int
    running_tasks: list[str]


class TaskExecutionResponse(BaseModel):
    id: str
    task_id: str
    agent_id: Optional[str] = None
    status: str
    execution_log: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    problem_details: Optional[Dict[str, Any]] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    agent_type: str
    api_endpoint: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class HeartbeatCreate(BaseModel):
    load_level: float = 0.0
    status_detail: Optional[str] = None


class HeartbeatResponse(BaseModel):
    id: str
    agent_id: str
    load_level: float
    status_detail: Optional[str] = None
    heartbeat_at: datetime

    class Config:
        from_attributes = True


class AgentStatusUpdate(BaseModel):
    status: str


class HermesStatusWebhook(BaseModel):
    agent_name: str
    event: str


class HermesTaskCompletedWebhook(BaseModel):
    agent_name: str
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
