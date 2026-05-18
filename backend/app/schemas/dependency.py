from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DependencyCreate(BaseModel):
    source_task_id: str = Field(..., min_length=1)
    target_task_id: str = Field(..., min_length=1)


class DependencyResponse(BaseModel):
    id: str
    source_task_id: str
    target_task_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DependencyGraphResponse(BaseModel):
    task_id: str
    predecessors: list[str]
    successors: list[str]
    all_dependencies: list[DependencyResponse]
    has_cycle: bool
