from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.enums import TaskStatus, TaskPriority


class TaskCreate(BaseModel):
    project_id: Optional[str] = None
    board_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    priority: str = "medium"
    assignee_id: Optional[str] = None
    agent_type_preference: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    deadline: Optional[datetime] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    column_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    agent_type_preference: Optional[str] = None
    assignee_agent_id: Optional[str] = None
    assigned_by_skill_id: Optional[str] = None
    status: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    deadline: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    progress_message: Optional[str] = None
    rejection_count: Optional[int] = None
    result_summary: Optional[str] = None
    artifacts: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    type: str
    priority: str
    agent_type_preference: Optional[str] = None
    assignee_agent_id: Optional[str] = None
    assigned_by_skill_id: Optional[str] = None
    status: str
    acceptance_criteria: Optional[str] = None
    deadline: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None
    progress: int
    progress_message: Optional[str] = None
    rejection_count: int
    result_summary: Optional[str] = None
    artifacts: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


class TaskStatusUpdate(BaseModel):
    status: str


class TaskMoveRequest(BaseModel):
    status: Optional[str] = None
    column_id: Optional[str] = None
    order_in_column: Optional[int] = None
