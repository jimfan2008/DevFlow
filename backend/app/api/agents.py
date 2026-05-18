from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.dependencies import require_admin
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.models.user import User
from app.models.agent_heartbeat import AgentHeartbeat
from app.services.profile_scanner_service import profile_scanner
from app.services.profile_sync import sync_profiles_to_db, update_agent_online_status
from app.schemas.agent import (
    AgentRegister, AgentResponse, AgentListResponse,
    AgentAssignRequest, AgentAssignResponse,
    TaskDeliverRequest, AgentLoadResponse, TaskExecutionResponse,
    HeartbeatCreate, HeartbeatResponse, AgentStatusUpdate,
)
import logging

logger = logging.getLogger("devflow.agents")
router = APIRouter()


@router.get("/agents", response_model=dict)
def list_agents(
    agent_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Agent)
    if agent_type:
        query = query.filter(Agent.agent_type == agent_type)
    agents = query.all()
    return {
        "code": 0,
        "message": "success",
        "data": {"agents": [a.to_dict() for a in agents], "total": len(agents)},
    }


@router.get("/agents/{agent_id}", response_model=dict)
def get_agent_detail(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    latest_heartbeat = (
        db.query(AgentHeartbeat)
        .filter(AgentHeartbeat.agent_id == agent_id)
        .order_by(AgentHeartbeat.heartbeat_at.desc())
        .first()
    )

    skills = db.query(HermesSkill).filter(HermesSkill.hermes_agent_id == agent_id).all()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "agent": agent.to_dict(),
            "latest_heartbeat": latest_heartbeat.to_dict() if latest_heartbeat else None,
            "skills": [s.to_dict() for s in skills],
        },
    }


@router.delete("/agents/{agent_id}", response_model=dict)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.query(AgentHeartbeat).filter(AgentHeartbeat.agent_id == agent_id).delete()
    db.delete(agent)
    db.commit()
    return {"code": 0, "message": "success", "data": {"deleted": agent_id}}


@router.get("/agents/discover", response_model=dict)
async def discover_hermes_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        profiles = await profile_scanner.get_all_profiles()
        return {
            "code": 0,
            "message": "success",
            "data": {
                "profiles": [p.model_dump() for p in profiles],
                "total": len(profiles),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to discover profiles: {str(e)}")


@router.post("/agents/sync-hermes", response_model=dict)
async def sync_hermes_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await sync_profiles_to_db(db)
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync profiles: {str(e)}")


@router.post("/agents/register", response_model=dict)
def register_agent(
    data: AgentRegister,
    db: Session = Depends(get_db),
):
    agent = Agent(
        name=data.name,
        agent_type=data.agent_type,
        status="offline",
        api_endpoint=data.api_endpoint,
        config=data.config or {},
    )
    db.add(agent)
    try:
        db.commit()
        db.refresh(agent)
        return {"code": 0, "message": "success", "data": {"agent": agent.to_dict()}}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents/available", response_model=dict)
def get_available_agents(
    agent_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Agent).filter(Agent.status == "online")
    if agent_type:
        query = query.filter(Agent.agent_type == agent_type)
    agents = query.all()
    return {
        "code": 0,
        "message": "success",
        "data": {"agents": [a.to_dict() for a in agents], "total": len(agents)},
    }


@router.post("/agents/{agent_id}/heartbeat", response_model=dict)
def report_heartbeat(
    agent_id: str,
    data: HeartbeatCreate,
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = "online"
    heartbeat = AgentHeartbeat(
        agent_id=agent_id,
        load_level=data.load_level,
        status_detail=data.status_detail,
    )
    db.add(heartbeat)
    db.commit()
    db.refresh(heartbeat)
    return {
        "code": 0,
        "message": "success",
        "data": {"heartbeat": heartbeat.to_dict()},
    }


@router.put("/agents/{agent_id}/status", response_model=dict)
def update_agent_status(
    agent_id: str,
    data: AgentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = data.status
    db.commit()
    db.refresh(agent)
    return {
        "code": 0,
        "message": "success",
        "data": {"agent": agent.to_dict()},
    }
