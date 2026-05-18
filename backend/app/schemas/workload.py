#!/usr/bin/env python3
"""负载相关 Pydantic 模式"""
from pydantic import BaseModel, Field
from typing import Optional


class WorkloadMemberResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str] = None
    task_count: int = 0
    status: str = "idle"  # idle, normal, busy, overloaded
    color: str = "green"
    has_alert: bool = False
    alert_level: Optional[str] = None  # yellow, red
    task_breakdown: dict = Field(default_factory=lambda: {
        "todo": 0, "in_progress": 0, "review": 0, "done": 0
    })


class AutoAssignRequest(BaseModel):
    task_id: str
    auto_assign: bool = True


class WorkloadResponse(BaseModel):
    members: list[WorkloadMemberResponse] = []
    team: dict = Field(default_factory=lambda: {
        "total_members": 0,
        "total_tasks": 0,
        "avg_load": 0.0,
        "status_distribution": {"idle": 0, "normal": 0, "busy": 0, "overloaded": 0}
    })


class TeamStatsResponse(BaseModel):
    total_tasks: int
    tasks_by_status: dict
    tasks_by_user: list
    completion_rate: float
    overdue_count: int


class WorkloadTrendResponse(BaseModel):
    trend: list
    history: list
    days: int
