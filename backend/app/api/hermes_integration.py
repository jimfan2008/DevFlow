from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.dependencies import require_admin
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.models.user import User
from app.services.skill_scheduler import SkillSchedulerService
from app.services.profile_scanner_service import profile_scanner
from app.services.gateway_client import GatewayClient
from app.services.skill_crud import ensure_four_skills
from app.core.exceptions import SkillNoAgentError, SkillConnectError, SkillOverloadedError
import logging

logger = logging.getLogger("devflow.hermes")
router = APIRouter(redirect_slashes=False)


class ChatRequest(BaseModel):
    message: str
    profile_name: Optional[str] = None
    session_id: Optional[str] = None


class DecomposeRequest(BaseModel):
    requirement: str
    profile_name: Optional[str] = None


class SkillDiscoverRequest(BaseModel):
    hermes_agent_id: Optional[str] = None


class SkillConnectRequest(BaseModel):
    hermes_agent_id: str
    coding_agent_id: str


class SkillAssignRequest(BaseModel):
    hermes_agent_id: str
    task_id: str
    coding_agent_id: Optional[str] = None


class SkillMessageWebhook(BaseModel):
    type: str
    agent_id: Optional[str] = None
    task_id: str
    content: Dict[str, Any] = {}


@router.get("/hermes/health")
async def hermes_health(profile_name: str = Query(None, description="指定profile名称检查")):
    try:
        if profile_name:
            status = await profile_scanner.get_profile_status(profile_name)
            return {"code": 0, "message": "success", "data": status}
        else:
            profiles = await profile_scanner.get_all_profiles()
            running = [p for p in profiles if p.is_running]
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "total_profiles": len(profiles),
                    "running_profiles": len(running),
                    "profiles": [p.model_dump() for p in running[:5]],
                },
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.post("/hermes/skills/discover", response_model=dict)
async def skill_discover(
    data: SkillDiscoverRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service = SkillSchedulerService(db)
        result = await service.discover_coding_agents(data.hermes_agent_id)
        return {"code": 0, "message": "success", "data": result}
    except SkillNoAgentError as e:
        raise HTTPException(status_code=e.status_code, detail={"error_code": e.error_code, "message": e.detail})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hermes/skills/agents", response_model=dict)
def skill_get_agents(
    hermes_agent_id: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SkillSchedulerService(db)
    agents = service.get_available_coding_agents(hermes_agent_id)
    return {
        "code": 0,
        "message": "success",
        "data": {"agents": agents, "total": len(agents)},
    }


@router.post("/hermes/skills/connect", response_model=dict)
async def skill_connect(
    data: SkillConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service = SkillSchedulerService(db)
        result = await service.connect_coding_agent(data.hermes_agent_id, data.coding_agent_id)
        return {"code": 0, "message": "success", "data": result}
    except SkillConnectError as e:
        raise HTTPException(status_code=e.status_code, detail={"error_code": e.error_code, "message": e.detail})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hermes/skills/assign", response_model=dict)
async def skill_assign(
    data: SkillAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service = SkillSchedulerService(db)
        result = await service.assign_task(data.hermes_agent_id, data.task_id, data.coding_agent_id)
        return {"code": 0, "message": "success", "data": result}
    except SkillOverloadedError as e:
        raise HTTPException(status_code=e.status_code, detail={"error_code": e.error_code, "message": e.detail})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hermes/skills/status", response_model=dict)
def skill_status(
    hermes_agent_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SkillSchedulerService(db)
    channels = service.get_skill_channel_status(hermes_agent_id)
    return {
        "code": 0,
        "message": "success",
        "data": {"channels": channels},
    }


@router.get("/hermes/skills/{skill_id}/history", response_model=dict)
def skill_history(
    skill_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SkillSchedulerService(db)
    history = service.get_skill_history(skill_id, limit)
    return {
        "code": 0,
        "message": "success",
        "data": {"history": history, "total": len(history)},
    }


@router.post("/webhooks/hermes/skill-message", response_model=dict)
async def skill_message_webhook(
    data: SkillMessageWebhook,
    db: Session = Depends(get_db),
):
    try:
        service = SkillSchedulerService(db)
        result = await service.handle_skill_message(data.model_dump())
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
