from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill

router = APIRouter(redirect_slashes=False)


class PairRequest(BaseModel):
    agent_id: str
    channel_config: Optional[dict] = None


class AssignRequest(BaseModel):
    task_id: str
    subtask_config: Optional[dict] = None


@router.get("", response_model=dict)
def list_skills(
    hermes_agent_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(HermesSkill)
    if hermes_agent_id:
        query = query.filter(HermesSkill.hermes_agent_id == hermes_agent_id)
    if status:
        query = query.filter(HermesSkill.status == status)
    skills = query.all()
    return {"code": 0, "message": "success", "data": {"skills": [s.to_dict() for s in skills], "total": len(skills)}}


@router.get("/{skill_id}", response_model=dict)
def get_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(HermesSkill).filter(HermesSkill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"code": 0, "message": "success", "data": {"skill": skill.to_dict()}}


@router.post("/{skill_id}/discover", response_model=dict)
def discover_agents(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(HermesSkill).filter(HermesSkill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    agents = db.query(Agent).filter(Agent.agent_type == "programming", Agent.status == "online").all()
    return {"code": 0, "message": "success", "data": {"discovered": [a.to_dict() for a in agents]}}


@router.post("/{skill_id}/pair", response_model=dict)
def pair_agent(
    skill_id: str,
    data: PairRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(HermesSkill).filter(HermesSkill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    agent = db.query(Agent).filter(Agent.id == data.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    skill.paired_agent_id = data.agent_id
    skill.status = "paired"
    db.commit()
    db.refresh(skill)
    return {"code": 0, "message": "success", "data": {"pairing": skill.to_dict()}}


@router.post("/{skill_id}/assign", response_model=dict)
def assign_task(
    skill_id: str,
    data: AssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(HermesSkill).filter(HermesSkill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.status = "executing"
    db.commit()
    db.refresh(skill)
    return {"code": 0, "message": "success", "data": {"assignment": {"skill_id": skill_id, "task_id": data.task_id}}}


@router.get("/history", response_model=dict)
def get_execution_history(
    skill_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"code": 0, "message": "success", "data": {"records": [], "total": 0}}


@router.get("/{skill_id}/channel", response_model=dict)
def get_channel_status(
    skill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(HermesSkill).filter(HermesSkill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"code": 0, "message": "success", "data": {"channel": {"status": "connected" if skill.paired_agent_id else "disconnected"}}}
