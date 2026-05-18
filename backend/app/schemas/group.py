from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.enums import GroupMode, MessageRole, MeetingType, GroupTaskStatus


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    members: List[str] = []
    host_agent: Optional[str] = None
    mode: str = "discussion"
    project_id: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    members: Optional[List[str]] = None
    host_agent: Optional[str] = None
    mode: Optional[str] = None
    project_id: Optional[str] = None


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    members: List[str] = []
    host_agent: Optional[str] = None
    mode: str = "discussion"
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupMessageCreate(BaseModel):
    group_id: str
    sender: str
    role: str
    content: str
    is_streaming: bool = False
    metadata: Optional[Dict[str, Any]] = None


class GroupMessageResponse(BaseModel):
    id: str
    group_id: str
    sender: str
    role: str
    content: str
    timestamp: datetime
    is_streaming: bool
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class MeetingOutcomeCreate(BaseModel):
    group_id: str
    meeting_topic: str
    meeting_type: str
    host_agent: str
    agenda: Optional[List[Dict[str, Any]]] = None
    started_at: datetime


class MeetingOutcomeResponse(BaseModel):
    id: str
    group_id: str
    meeting_topic: str
    meeting_type: str
    host_agent: str
    agenda: List[Dict[str, Any]] = []
    started_at: datetime
    ended_at: Optional[datetime] = None
    minutes: Optional[str] = None
    decisions: List[Dict[str, Any]] = []
    todos: List[Dict[str, Any]] = []
    risks: List[Dict[str, Any]] = []
    open_issues: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class GroupTaskCreate(BaseModel):
    group_id: str
    meeting_id: Optional[str] = None
    assignee: Optional[str] = None
    description: str
    deadline: Optional[datetime] = None


class GroupTaskUpdate(BaseModel):
    assignee: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None


class GroupTaskResponse(BaseModel):
    id: str
    group_id: str
    meeting_id: Optional[str] = None
    assignee: Optional[str] = None
    description: str
    deadline: Optional[datetime] = None
    status: str = "pending"
    result: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AddMemberRequest(BaseModel):
    profile_name: str


class SetHostRequest(BaseModel):
    host_agent: str


class SendMessageRequest(BaseModel):
    sender: str
    role: str
    content: str
    is_streaming: bool = False
    metadata: Optional[Dict[str, Any]] = None
