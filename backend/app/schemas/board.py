#!/usr/bin/env python3
"""看板相关 Pydantic 模式"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BoardColumnCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = "#E5E7EB"
    position: Optional[int] = None
    max_tasks: Optional[int] = None


class BoardColumnUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = None
    position: Optional[int] = None
    max_tasks: Optional[int] = None
    is_active: Optional[bool] = None


class BoardColumnResponse(BaseModel):
    id: str
    board_id: str
    name: str
    slug: str
    color: str
    position: int
    max_tasks: Optional[int] = None
    is_swimlane: bool
    is_default: bool
    is_active: bool
    task_count: Optional[int] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    project_id: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = "#3B82F6"
    position: Optional[int] = 0
    columns: Optional[list[BoardColumnCreate]] = None


class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = None
    position: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class BoardResponse(BaseModel):
    id: str
    project_id: str
    name: str
    slug: str
    description: Optional[str] = None
    position: int
    color: str
    is_default: bool
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class BoardDetailResponse(BaseModel):
    id: str
    project_id: str
    name: str
    slug: str
    description: Optional[str] = None
    position: int
    color: str
    is_default: bool
    is_active: bool
    columns: list[BoardColumnResponse] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class BoardWithColumnsResponse(BaseModel):
    board: BoardResponse
    columns: list[BoardColumnResponse]


class BoardListResponse(BaseModel):
    boards: list[BoardResponse]
    total: int
    page: int
    page_size: int


class BoardColumnListResponse(BaseModel):
    columns: list[BoardColumnResponse]
    total: int


class BoardColumnDetailResponse(BaseModel):
    column: BoardColumnResponse
    task_count: int
