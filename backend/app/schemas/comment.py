#!/usr/bin/env python3
"""评论相关 Pydantic 模式"""
from pydantic import BaseModel, Field
from typing import Optional


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: Optional[str] = None
    content: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    total: int
