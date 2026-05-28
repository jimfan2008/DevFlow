# 项目级 SRS API - 创建、任务查看、通知、完成
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.board import Board, BoardColumn
from app.models.notification import InboxItem
from app.services.decomposition_service import DecompositionService
from app.services.delivery_service import DeliveryService
from app.schemas.project_srs import (
    ProjectCreate, ProjectTaskListResponse,
    NotificationItem, NotificationListResponse,
    ProjectCompleteResponse,
)

router = APIRouter(redirect_slashes=False)


@router.get("", response_model=dict)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出所有项目"""
    projects = db.query(Project).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug if hasattr(p, 'slug') else p.name.lower().replace(" ", "-"),
                    "description": p.description,
                    "status": p.status if hasattr(p, 'status') else "draft",
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in projects
            ],
            "total": len(projects),
        },
    }


@router.post("", response_model=dict)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.1.1 - 人类用户创建项目"""
    existing = db.query(Project).filter(Project.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project name already exists")

    project = Project(
        id=str(uuid.uuid4()),
        name=data.name,
        slug=data.name.lower().replace(" ", "-").replace("_", "-"),
        description=data.description or "",
        creator_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {
        "code": 0,
        "message": "success",
        "data": {"project": {"id": project.id, "name": project.name, "slug": project.slug}},
    }


@router.get("/{project_id}/tasks", response_model=dict)
def get_project_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.2 - 获取项目任务清单"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Task -> board_id -> Board.project_id
    tasks = db.query(Task).join(Board).filter(Board.project_id == project_id).all()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "assignee_id": t.assignee_id,
                    "acceptance_criteria": t.acceptance_criteria,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
            "total": len(tasks),
            "project_id": project_id,
            "project_name": project.name,
        },
    }


@router.post("/{project_id}/decompose", response_model=dict)
def decompose_project_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.2.1 - 按开发流程自动拆解任务"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 获取需求内容
    from app.models.requirement import Requirement
    req = db.query(Requirement).filter(
        Requirement.project_id == project_id,
        Requirement.is_locked == True,
    ).first()
    if not req:
        raise HTTPException(status_code=400, detail="请先确认需求文档")

    # 获取或创建默认 Board
    board = db.query(Board).filter(Board.project_id == project_id).first()
    if not board:
        board = Board(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=f"{project.name} - 开发看板",
            slug="default",
        )
        db.add(board)
        db.commit()
        db.refresh(board)

    column = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).first()
    if not column:
        column = BoardColumn(
            id=str(uuid.uuid4()),
            board_id=board.id,
            name="待办",
            slug="todo",
            position=0,
        )
        db.add(column)
        db.commit()
        db.refresh(column)

    decomposition = DecompositionService(db=db)
    task_list = decomposition.decompose(project_id, req.content)
    decomposition.apply_priorities(task_list, project_id)
    created = decomposition.persist_tasks(task_list, board.id, column.id)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                }
                for t in created
            ],
            "total": len(created),
        },
    }


@router.get("/{project_id}/notifications", response_model=dict)
def get_project_notifications(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.5.1 - 获取项目通知列表"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    items = db.query(InboxItem).filter(
        InboxItem.user_id == current_user.id,
        InboxItem.metadata_json.like(f'%"project_id": "{project_id}"%'),
    ).order_by(InboxItem.created_at.desc()).all()

    unread = sum(1 for i in items if not i.is_read)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "notifications": [i.to_dict() for i in items],
            "total": len(items),
            "unread_count": unread,
        },
    }


@router.post("/{project_id}/complete", response_model=dict)
def complete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.5.2 - 确认项目完成并发送通知"""
    from app.services.acceptance_service import AcceptanceService
    from app.services.delivery_service import DeliveryService

    # 先执行最终验收
    acceptance = AcceptanceService(db=db)
    final_result = acceptance.final_acceptance(project_id)

    if not final_result["passed"]:
        raise HTTPException(
            status_code=400,
            detail=f"项目有 {final_result['pending_tasks']} 个待处理任务和 {final_result['rejected_tasks']} 个驳回任务，请先处理",
        )

    # 完成项目交付
    delivery = DeliveryService(db=db)
    report = delivery.complete_project(project_id)

    return {
        "code": 0,
        "message": "success",
        "data": report,
    }