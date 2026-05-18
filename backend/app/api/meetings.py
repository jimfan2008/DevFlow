from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.meeting_service import MeetingService

router = APIRouter()


class StartMeetingRequest(BaseModel):
    topic: str
    host_agent: str
    meeting_type: str = "tech_solution"
    pre_materials: Optional[List[str]] = None
    rules: Optional[dict] = None


class StopMeetingRequest(BaseModel):
    minutes: str = ""
    decisions: Optional[List[dict]] = None
    todos: Optional[List[dict]] = None
    risks: Optional[List[dict]] = None
    open_issues: Optional[List[dict]] = None


class InterventionRequest(BaseModel):
    content: str


@router.post("/{group_id}/start", response_model=dict)
def start_meeting(
    group_id: str,
    data: StartMeetingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService(db)
    try:
        group = svc.start_meeting(
            group_id=group_id,
            topic=data.topic,
            host_agent_name=data.host_agent,
            meeting_type=data.meeting_type,
            pre_materials=data.pre_materials,
            rules=data.rules,
        )
    except ValueError as e:
        error_detail = str(e)
        if "MEETING_001" in error_detail:
            raise HTTPException(status_code=409, detail=error_detail)
        if "MEETING_002" in error_detail:
            raise HTTPException(status_code=400, detail=error_detail)
        raise HTTPException(status_code=400, detail=error_detail)
    return {"code": 0, "message": "success", "data": {"group_id": group.id, "mode": group.mode}}


@router.post("/{group_id}/stop", response_model=dict)
def stop_meeting(
    group_id: str,
    data: StopMeetingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService(db)
    try:
        outcome = svc.stop_meeting(
            group_id=group_id,
            minutes=data.minutes,
            decisions=data.decisions,
            todos=data.todos,
            risks=data.risks,
            open_issues=data.open_issues,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"outcome": outcome.to_dict()}}


@router.post("/{group_id}/intervention", response_model=dict)
def meeting_intervention(
    group_id: str,
    data: InterventionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService(db)
    try:
        msg = svc.handle_intervention(group_id, data.content, sender=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"message": msg.to_dict()}}


@router.post("/{group_id}/dispute", response_model=dict)
def handle_dispute(
    group_id: str,
    data: InterventionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService(db)
    try:
        msg = svc.handle_dispute(group_id, data.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"message": msg.to_dict()}}


@router.get("/{group_id}/outcomes", response_model=dict)
def get_meeting_outcomes(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService(db)
    outcomes = svc.get_meeting_outcomes(group_id)
    return {"code": 0, "message": "success", "data": {"outcomes": [o.to_dict() for o in outcomes]}}


@router.get("/templates/{meeting_type}", response_model=dict)
def get_meeting_template(
    meeting_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService(db)
    template = svc.get_meeting_template(meeting_type)
    return {"code": 0, "message": "success", "data": {"template": template}}
