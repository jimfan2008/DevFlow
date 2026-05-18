from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class NotificationCreate(BaseModel):
    user_id: str
    project_id: Optional[str] = None
    type: str
    title: str = Field(..., max_length=200)
    content: str
    channel: str = "platform"


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str] = None
    type: str
    title: str
    content: str
    channel: str
    is_read: bool
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int
