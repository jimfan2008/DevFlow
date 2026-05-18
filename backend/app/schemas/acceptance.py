from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.enums import AcceptanceResult


class AcceptanceCreate(BaseModel):
    task_id: str
    reviewer_agent_id: str
    result: str
    problem_details: Optional[str] = None
    suggestions: Optional[str] = None


class AcceptanceUpdate(BaseModel):
    result: Optional[str] = None
    problem_details: Optional[str] = None
    suggestions: Optional[str] = None


class AcceptanceRecordResponse(BaseModel):
    id: str
    task_id: str
    reviewer_agent_id: str
    result: str
    problem_details: Optional[str] = None
    suggestions: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AcceptanceRecordListResponse(BaseModel):
    records: list[AcceptanceRecordResponse]
    total: int


class AcceptanceResult(BaseModel):
    result: str
    checks: Dict[str, Any] = {}
    suggestions: List[str] = []
    acceptance_id: Optional[str] = None


class FinalAcceptanceRequest(BaseModel):
    project_id: str


class FinalAcceptanceResponse(BaseModel):
    project_id: str
    passed: bool
    pending_tasks: int = 0
    rejected_tasks: int = 0
    summary: str = ""
