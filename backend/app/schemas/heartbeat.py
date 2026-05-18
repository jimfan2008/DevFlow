from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class HeartbeatCreate(BaseModel):
    load_level: int = Field(default=0, ge=0, le=100)
    status_detail: Optional[Dict[str, Any]] = None
    via_skill: Optional[str] = None


class HeartbeatResponse(BaseModel):
    id: str
    agent_id: str
    heartbeat_at: datetime
    load_level: int
    status_detail: Optional[Dict[str, Any]] = None
    via_skill: Optional[str] = None

    class Config:
        from_attributes = True
