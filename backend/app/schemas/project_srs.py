# SRS 项目相关 Pydantic 模式
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tech_stack: Optional[dict] = None
    delivery_date: Optional[str] = None


class ProjectTaskListResponse(BaseModel):
    tasks: list[dict]
    total: int
    project_id: str
    project_name: str


class NotificationItem(BaseModel):
    id: str
    title: str
    content: str
    type: str
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationItem]
    total: int
    unread_count: int


class ProjectCompleteResponse(BaseModel):
    project_id: str
    project_name: str
    completed_at: str
    status: str
    summary: str


class DecomposedTask(BaseModel):
    title: str
    description: str
    type: str
    priority: str
    acceptance_criteria: str
    agent_type: str