from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.services.project_service import ProjectService
from app.schemas.project_srs import ProjectCreate

router = APIRouter()


@router.post("", response_model=dict)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    try:
        project = svc.create_project(
            name=data.name,
            creator_id=current_user.id,
            description=data.description or "",
            tech_stack=str(data.tech_stack) if data.tech_stack else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"project": {"id": project.id, "name": project.name, "status": project.status}}}


@router.get("", response_model=dict)
def list_projects(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    projects = svc.list_projects(creator_id=current_user.id, status=status)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "projects": [
                {
                    "id": p.id, "name": p.name, "description": p.description,
                    "status": p.status, "review_group_id": p.review_group_id,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in projects
            ],
            "total": len(projects),
        },
    }


@router.get("/{project_id}", response_model=dict)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    project = svc.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"code": 0, "message": "success", "data": {"project": {
        "id": project.id, "name": project.name, "description": project.description,
        "status": project.status, "tech_stack": project.tech_stack,
        "review_group_id": project.review_group_id, "creator_id": project.creator_id,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
    }}}


@router.put("/{project_id}", response_model=dict)
def update_project(
    project_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    allowed_fields = {"name", "description", "tech_stack", "deadline"}
    update_data = {k: v for k, v in data.items() if k in allowed_fields and v is not None}
    project = svc.update_project(project_id, **update_data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"code": 0, "message": "success", "data": {"project": {"id": project.id, "name": project.name, "status": project.status}}}


@router.post("/{project_id}/transition", response_model=dict)
def transition_project_status(
    project_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_status = data.get("status")
    if not target_status:
        raise HTTPException(status_code=400, detail="status field required")
    svc = ProjectService(db)
    try:
        project = svc.transition_status(project_id, target_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"project": {"id": project.id, "status": project.status}}}


@router.post("/{project_id}/requirements", response_model=dict)
def submit_requirement(
    project_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = data.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    svc = ProjectService(db)
    try:
        req = svc.submit_requirement(project_id, content, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"requirement": req.to_dict()}}


@router.post("/{project_id}/requirements/confirm", response_model=dict)
def confirm_requirement(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    try:
        req = svc.confirm_and_lock_requirement(project_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"requirement": req.to_dict(), "message": "需求已确认锁定，将开始任务拆解流程"}}


@router.put("/{project_id}/requirements", response_model=dict)
def update_requirement(
    project_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = data.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    svc = ProjectService(db)
    try:
        req = svc.update_requirement_if_unlocked(project_id, content, user_id=current_user.id)
    except ValueError as e:
        error_detail = str(e)
        if "REQ_001" in error_detail:
            raise HTTPException(status_code=403, detail=error_detail)
        raise HTTPException(status_code=400, detail=error_detail)
    return {"code": 0, "message": "success", "data": {"requirement": req.to_dict()}}


@router.get("/{project_id}/prd", response_model=dict)
def generate_prd(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    try:
        prd = svc.generate_prd(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"prd": prd}}


@router.post("/{project_id}/members", response_model=dict)
def add_project_member(
    project_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = data.get("user_id")
    role = data.get("role", "member")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    svc = ProjectService(db)
    member = svc.add_member(project_id, user_id, role)
    return {"code": 0, "message": "success", "data": {"member": {"id": member.id, "user_id": member.user_id, "role": member.role}}}


@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService(db)
    success = svc.remove_member(project_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"code": 0, "message": "success"}
