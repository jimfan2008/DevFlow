from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.acceptance_service_v2 import AcceptanceServiceV2

router = APIRouter()


class RunAcceptanceRequest(BaseModel):
    reviewer_agent_id: str


@router.post("/tasks/{task_id}/run", response_model=dict)
def run_acceptance(
    task_id: str,
    data: RunAcceptanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AcceptanceServiceV2(db)
    try:
        result = svc.run_acceptance(task_id, data.reviewer_agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": result}


@router.post("/projects/{project_id}/final", response_model=dict)
def final_acceptance(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AcceptanceServiceV2(db)
    result = svc.final_acceptance(project_id)
    return {"code": 0, "message": "success", "data": result}


@router.get("/projects/{project_id}/timeout-tasks", response_model=dict)
def get_timeout_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AcceptanceServiceV2(db)
    tasks = svc.check_acceptance_timeout(project_id)
    return {"code": 0, "message": "success", "data": {"tasks": [t.to_dict() for t in tasks], "total": len(tasks)}}
