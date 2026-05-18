from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.enums import UserRole


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    avatar_url: Optional[str] = None
    notification_config: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    avatar_url: Optional[str] = None
    notification_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
