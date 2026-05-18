#!/usr/bin/env python3
"""附件相关 Pydantic 模式"""
from pydantic import BaseModel, Field
from typing import Optional


class AttachmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    size: Optional[int] = 0
    type: Optional[str] = "application/octet-stream"


class AttachmentResponse(BaseModel):
    id: str
    task_id: str
    name: str
    file_path: str
    file_url: Optional[str] = None
    size: int
    type: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class AttachmentListResponse(BaseModel):
    attachments: list[AttachmentResponse]
    total: int
