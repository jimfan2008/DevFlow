from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.task import Task
from app.models.project import Project
from app.models.board import Board
import uuid

router = APIRouter(redirect_slashes=False)


class ApproveRequest(BaseModel):
    comment: Optional[str] = None


class RejectRequest(BaseModel):
    issues: list[str] = []
    comment: Optional[str] = None


@router.get("", response_model=dict)
def list_reports(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task)
    if project_id:
        boards = db.query(Board).filter(Board.project_id == project_id).all()
        board_ids = [b.id for b in boards]
        query = query.filter(Task.board_id.in_(board_ids))
    if status == "pending":
        query = query.filter(Task.status == "review")
    elif status == "approved":
        query = query.filter(Task.status == "done")
    elif status == "rejected":
        query = query.filter(Task.status == "rejected")
    tasks = query.offset((page - 1) * page_size).limit(page_size).all()
    total = query.count()
    reports = []
    for t in tasks:
        reports.append({
            "id": t.id,
            "task_id": t.id,
            "status": "approved" if t.status == "done" else "rejected" if t.status == "rejected" else "pending",
            "reviewer": None,
            "issues": [],
            "suggestions": [],
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"code": 0, "message": "success", "data": {"reports": reports, "total": total}}


@router.get("/{report_id}", response_model=dict)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == report_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Report not found")
    report_status = "approved" if task.status == "done" else "rejected" if task.status == "rejected" else "pending"
    return {"code": 0, "message": "success", "data": {"report": {
        "id": task.id,
        "task_id": task.id,
        "status": report_status,
        "reviewer": None,
        "issues": [],
        "suggestions": [],
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }}}


@router.post("/{report_id}/approve", response_model=dict)
def approve_report(
    report_id: str,
    data: Optional[ApproveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == report_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "done"
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "success", "data": {"report": {"id": task.id, "status": "approved"}}}


@router.post("/{report_id}/reject", response_model=dict)
def reject_report(
    report_id: str,
    data: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == report_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "rejected"
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "success", "data": {"report": {"id": task.id, "status": "rejected", "issues": data.issues}}}


@router.get("/notifications", response_model=dict)
def get_notifications(
    unread_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"code": 0, "message": "success", "data": {"notifications": [], "total": 0, "unread_count": 0}}


@router.put("/notifications/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"code": 0, "message": "success", "data": {"id": notification_id}}


@router.put("/notifications/read-all", response_model=dict)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"code": 0, "message": "success", "data": {"marked_count": 0}}


@router.post("/projects/{project_id}/deliver", response_model=dict)
def deliver_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "completed"
    project.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return {"code": 0, "message": "success", "data": {"delivery": {
        "project_id": project.id,
        "status": "completed",
        "summary": f"Project {project.name} delivered successfully",
    }}}


@router.get("/projects/{project_id}/delivery", response_model=dict)
def get_delivery_status(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"code": 0, "message": "success", "data": {"delivery": {
        "project_id": project.id,
        "status": project.status,
    }}}
