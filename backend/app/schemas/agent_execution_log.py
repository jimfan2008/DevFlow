from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.enums import SkillType


class AgentExecutionLogCreate(BaseModel):
    task_id: str
    agent_id: str
    execution_content: Optional[str] = None
    result: Optional[str] = None
    via_skill_type: Optional[str] = None


class AgentExecutionLogResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    execution_content: Optional[str] = None
    result: Optional[str] = None
    via_skill_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentExecutionLogListResponse(BaseModel):
    logs: list[AgentExecutionLogResponse]
    total: int
