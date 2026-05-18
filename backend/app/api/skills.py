from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.services.skill_schedule_service import SkillScheduleService

router = APIRouter()


class HeartbeatRequest(BaseModel):
    load_level: int = 0
    status_detail: Optional[dict] = None
    via_skill: Optional[str] = None


@router.get("/matching-rules", response_model=dict)
def get_matching_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SkillScheduleService(db)
    return {"code": 0, "message": "success", "data": svc.get_skill_matching_rules()}


@router.post("/agents/{agent_id}/heartbeat", response_model=dict)
def register_heartbeat(
    agent_id: str,
    data: HeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SkillScheduleService(db)
    try:
        agent = svc.register_heartbeat(
            agent_id=agent_id,
            load_level=data.load_level,
            status_detail=data.status_detail,
            via_skill=data.via_skill,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "message": "success", "data": {"agent_id": agent.id, "status": agent.status}}


@router.post("/check-offline", response_model=dict)
def check_offline_agents(
    timeout_minutes: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SkillScheduleService(db)
    offline = svc.check_offline_agents(timeout_minutes=timeout_minutes)
    return {"code": 0, "message": "success", "data": {"offline_agents": [{"id": a.id, "name": a.name} for a in offline]}}
