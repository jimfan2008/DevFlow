from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.enums import SkillType, SkillStatus, ConnectionStatus


class HermesSkillCreate(BaseModel):
    hermes_agent_id: str
    skill_type: str
    status: str = "active"
    config: Optional[Dict[str, Any]] = None
    coding_agent_id: Optional[str] = None
    task_id: Optional[str] = None
    connection_status: Optional[str] = None


class HermesSkillUpdate(BaseModel):
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    last_executed_at: Optional[datetime] = None
    execution_stats: Optional[Dict[str, Any]] = None
    coding_agent_id: Optional[str] = None
    task_id: Optional[str] = None
    connection_status: Optional[str] = None


class HermesSkillResponse(BaseModel):
    id: str
    hermes_agent_id: str
    skill_type: str
    status: str
    config: Optional[Dict[str, Any]] = None
    last_executed_at: Optional[datetime] = None
    execution_stats: Optional[Dict[str, Any]] = None
    coding_agent_id: Optional[str] = None
    task_id: Optional[str] = None
    connection_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HermesSkillListResponse(BaseModel):
    skills: list[HermesSkillResponse]
    total: int
