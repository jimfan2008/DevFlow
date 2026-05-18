#!/usr/bin/env python3
"""收件箱相关 Pydantic 模式"""
from pydantic import BaseModel, Field
from typing import Optional


class InboxItemResponse(BaseModel):
    id: str
    user_id: str
    task_id: Optional[str] = None
    type: str
    title: str
    content: str
    is_read: bool
    metadata: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class InboxListResponse(BaseModel):
    items: list[InboxItemResponse]
    total: int
    unread_count: int


class NotificationPreferencesCreate(BaseModel):
    frequency: Optional[str] = None
    notify_types: Optional[list[str]] = None
    suppress_watch: Optional[bool] = None


class NotificationPreferencesResponse(BaseModel):
    id: str
    user_id: str
    frequency: str
    notify_types: list[str]
    suppress_watch: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    count: int


class ReminderResponse(BaseModel):
    task_id: str
    task_title: str
    due_date: str
    days_remaining: int
    priority: str
    assignee_id: Optional[str] = None
