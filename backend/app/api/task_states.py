from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.task import Task
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.services.task_state_service import TaskStateService
from app.services.skill_schedule_service import SkillScheduleService
from app.models.enums import TaskStatus

router = APIRouter()


class SkillAssignRequest(BaseModel):
    skill_id: str
    agent_id: str


class SkillDeliverRequest(BaseModel):
    skill_id: str
    result_summary: Optional[str] = None
    artifacts: Optional[dict] = None


class SkillFailRequest(BaseModel):
    skill_id: str
    error_detail: Optional[str] = None


class AcceptRejectRequest(BaseModel):
    reviewer_agent_id: str
    problem_details: Optional[str] = None
    suggestions: Optional[str] = None


@router.get("", response_model=dict)
def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if status:
        query = query.filter(Task.status == status)
    tasks = query.order_by(Task.created_at.desc()).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "tasks": [t.to_dict() for t in tasks],
            "total": len(tasks),
        },
    }


@router.get("/{task_id}", response_model=dict)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.post("/{task_id}/skill-assign", response_model=dict)
def skill_assign_task(
    task_id: str,
    data: SkillAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    try:
        task = svc.skill_assign(task_id, data.skill_id, data.agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.post("/{task_id}/skill-deliver", response_model=dict)
def skill_deliver_task(
    task_id: str,
    data: SkillDeliverRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    try:
        task = svc.skill_receive_delivery(task_id, data.skill_id, data.result_summary, data.artifacts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.post("/{task_id}/skill-fail", response_model=dict)
def skill_fail_task(
    task_id: str,
    data: SkillFailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    try:
        task = svc.skill_receive_failure(task_id, data.skill_id, data.error_detail)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.post("/{task_id}/accept", response_model=dict)
def accept_task(
    task_id: str,
    data: AcceptRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    try:
        task = svc.accept_task(task_id, data.reviewer_agent_id, data.suggestions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.services.notification_service import NotificationService
    notif_svc = NotificationService(db)
    if task.project_id:
        from app.models.project import Project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project and project.creator_id:
            notif_svc.notify_acceptance_result(
                task_id=task_id, task_name=task.name, passed=True,
                user_id=project.creator_id, project_id=task.project_id,
                detail="任务验收通过",
            )

    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.post("/{task_id}/reject", response_model=dict)
def reject_task(
    task_id: str,
    data: AcceptRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    try:
        task = svc.reject_task(task_id, data.reviewer_agent_id, data.problem_details, data.suggestions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.services.notification_service import NotificationService
    notif_svc = NotificationService(db)
    if task.project_id:
        from app.models.project import Project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project and project.creator_id:
            notif_svc.notify_acceptance_result(
                task_id=task_id, task_name=task.name, passed=False,
                user_id=project.creator_id, project_id=task.project_id,
                detail=data.problem_details or "任务验收驳回",
            )

    if svc.check_rejection_escalation(task_id):
        if task.project_id:
            from app.models.project import Project
            project = db.query(Project).filter(Project.id == task.project_id).first()
            if project and project.creator_id:
                notif_svc.notify_rejection_escalation(
                    task_id=task_id, task_name=task.name,
                    rejection_count=task.rejection_count,
                    user_id=project.creator_id, project_id=task.project_id,
                )

    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.post("/{task_id}/reassign", response_model=dict)
def reassign_task(
    task_id: str,
    data: SkillAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    try:
        task = svc.reassign_failed_task(task_id, data.skill_id, data.agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.post("/{task_id}/auto-assign", response_model=dict)
def auto_assign_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SkillScheduleService(db)
    try:
        task = svc.auto_assign_via_skill(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not task:
        raise HTTPException(status_code=503, detail="No available agents for assignment")
    return {"code": 0, "message": "success", "data": {"task": task.to_dict()}}


@router.get("/{task_id}/dependency-ready", response_model=dict)
def check_dependency_ready(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    ready = svc.check_dependency_readiness(task_id)
    return {"code": 0, "message": "success", "data": {"task_id": task_id, "ready": ready}}


@router.get("/ready-for-assignment/{project_id}", response_model=dict)
def get_ready_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskStateService(db)
    tasks = svc.get_ready_tasks_for_skill_assignment(project_id)
    return {
        "code": 0,
        "message": "success",
        "data": {"tasks": [t.to_dict() for t in tasks], "total": len(tasks)},
    }
