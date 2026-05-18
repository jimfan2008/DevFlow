from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class RequirementCreate(BaseModel):
    project_id: str
    content: str = Field(..., min_length=1)
    version: int = 1


class RequirementUpdate(BaseModel):
    content: Optional[str] = None
    is_locked: Optional[bool] = None
    confirmed_by: Optional[str] = None
    meeting_id: Optional[str] = None
    attachments: Optional[list] = None


class RequirementResponse(BaseModel):
    id: str
    project_id: str
    content: str
    version: int
    is_locked: bool
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    meeting_id: Optional[str] = None
    attachments: list = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequirementConfirm(BaseModel):
    confirmed: bool = True


class RequirementSubmit(BaseModel):
    content: str = Field(..., min_length=1)
    project_name: Optional[str] = None
    tech_stack: Optional[dict] = None


class ClarificationAnswer(BaseModel):
    project_name: str
    features: List[str]
    tech_stack: Optional[dict] = None


class RequirementDocument(BaseModel):
    title: str
    features: List[dict]
    tech_stack: dict
    acceptance_criteria: List[str]
    constraints: List[str]


class RequirementParseResult(BaseModel):
    requirements: List[str]
    ambiguities: List[str]
    suggestions: List[str]
