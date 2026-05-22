#!/usr/bin/env python3
"""Scheduling schema"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class TaskAssignRequest(BaseModel):
    agent_type: str  # opencode/cursor/claude_code/codebuddy

class TaskExecutionResponse(BaseModel):
    id: str
    task_id: str
    agent_id: Optional[str] = None
    status: str  # pending/running/delivered/accepted/rejected
    execution_log: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    problem_details: Optional[Dict[str, Any]] = None
    delivered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class TaskProgressResponse(BaseModel):
    total: int
    todo: int
    in_progress: int
    review: int
    done: int
    completed: int
    progress_percent: int

class TaskDeliveryRequest(BaseModel):
    execution_id: str
    execution_log: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None

class TaskAcceptanceRequest(BaseModel):
    execution_id: str
    result: str  # pass/fail
    problem_details: Optional[Dict[str, Any]] = None

class AcceptanceResponse(BaseModel):
    id: str
    task_execution_id: str
    result: str  # pass/fail
    problem_details: Optional[Dict[str, Any]] = None
    reviewer: str
    created_at: datetime

    class Config:
        orm_mode = True
