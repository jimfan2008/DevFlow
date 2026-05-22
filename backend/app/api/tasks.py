#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 任务 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.task_service import TaskService
from app.services.comment_service import CommentService
from app.services.attachment_service import AttachmentService
from app.services.dependency_service import DependencyService
from app.services.workload_service import WorkloadService
from app.api.deps import get_current_user
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskStatusUpdate, TaskMoveRequest,
)

router = APIRouter(redirect_slashes=False)


def _task_service(db: Session, current_user) -> TaskService:
    return TaskService(db=db, current_user_id=current_user.id)


def _comment_service(db: Session, current_user) -> CommentService:
    return CommentService(db=db, current_user_id=current_user.id)


def _attachment_service(db: Session, current_user) -> AttachmentService:
    return AttachmentService(db=db, current_user_id=current_user.id)


# ── 任务 CRUD ────────────────────────────────────────────
@router.post("", tags=["tasks"])
def create_task(
    data: TaskCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建任务"""
    try:
        service = _task_service(db, current_user)
        result = service.create_task(
            project_id=data.project_id or "",
            name=data.name or data.title or "",
            type=data.type or "coding",
            description=data.description,
            status=data.status or "pending",
            priority=data.priority or "medium",
            agent_type_preference=data.agent_type_preference,
            assignee_agent_id=data.assignee_id,
            acceptance_criteria=data.acceptance_criteria,
            deadline=data.deadline or data.due_date,
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", tags=["tasks"])
def list_tasks(
    project_id: str = Query(None),
    board_id: str = Query(None),
    status: str = Query(None),
    assignee_id: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出任务"""
    try:
        service = _task_service(db, current_user)
        return {
            "code": 0,
            "message": "success",
            "data": service.list_tasks(
                project_id=project_id or board_id, status=status,
                assignee_agent_id=assignee_id, page=page, per_page=per_page
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", tags=["tasks"])
def get_task(
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取任务详情"""
    try:
        service = _task_service(db, current_user)
        return {
            "code": 0,
            "message": "success",
            "data": service.get_task(task_id, include_comments=True),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{task_id}", tags=["tasks"])
def update_task(
    task_id: str,
    data: TaskUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新任务"""
    try:
        service = _task_service(db, current_user)
        result = service.update_task(
            task_id, **data.model_dump(exclude_unset=True)
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{task_id}", tags=["tasks"])
def update_task_patch(
    task_id: str,
    data: TaskUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新任务（部分更新）"""
    try:
        service = _task_service(db, current_user)
        result = service.update_task(
            task_id, **data.model_dump(exclude_unset=True)
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{task_id}/status", tags=["tasks"])
def update_status(
    task_id: str,
    data: TaskStatusUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新任务状态"""
    try:
        service = _task_service(db, current_user)
        result = service.update_task(task_id, status=data.status)
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{task_id}/move", tags=["tasks"])
def move_task(
    task_id: str,
    data: TaskMoveRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移动任务（拖拽）"""
    try:
        service = _task_service(db, current_user)
        result = service.move_task(
            task_id, data.status, data.column_id, data.order_in_column
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}", tags=["tasks"])
def delete_task(
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除任务"""
    try:
        service = _task_service(db, current_user)
        service.delete_task(task_id)
        return {
            "code": 0,
            "message": "任务已删除",
            "data": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── 任务操作 ─────────────────────────────────────────────
@router.post("/{task_id}/assign", tags=["tasks"])
def auto_assign(
    task_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """自动分配任务"""
    from app.models.user import User

    assignee_name = data.get("assignee")
    if assignee_name:
        user = db.query(User).filter(User.username == assignee_name).first()
        if not user:
            user = current_user
        service = _task_service(db, current_user)
        result = service.update_task(task_id, assignee_id=user.id)
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }

    if not data.get("auto_assign", False):
        raise HTTPException(status_code=400, detail="auto_assign must be True or provide assignee")
    ws = WorkloadService(db=db)
    try:
        result = ws.auto_assign_task(task_id)
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 评论 ──────────────────────────────────────────────────
@router.post("/{task_id}/comments", tags=["tasks"])
def create_comment(
    task_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加评论"""
    try:
        service = _comment_service(db, current_user)
        result = service.create_comment(task_id, data["content"])
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/comments", tags=["tasks"])
def list_comments(
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看评论"""
    try:
        service = _comment_service(db, current_user)
        comments = service.get_comments(task_id)
        return {
            "code": 0,
            "message": "success",
            "data": {"comments": comments, "total": len(comments)},
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── 附件 ──────────────────────────────────────────────────
@router.post("/{task_id}/attachments", tags=["tasks"])
def add_attachment(
    task_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加附件"""
    try:
        service = _attachment_service(db, current_user)
        result = service.add_attachment(
            task_id=task_id,
            name=data["name"],
            file_path=f"/tmp/attachments/{task_id}/{data['name']}",
            size=data.get("size", 0),
            type=data.get("type", "application/octet-stream"),
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/attachments", tags=["tasks"])
def list_attachments(
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列附件"""
    try:
        service = _attachment_service(db, current_user)
        attachments = service.get_attachments(task_id)
        return {
            "code": 0,
            "message": "success",
            "data": {"attachments": attachments, "total": len(attachments)},
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── 依赖 ──────────────────────────────────────────────────
@router.post("/{task_id}/depend", tags=["tasks"])
def create_dependency(
    task_id: str,
    data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建依赖"""
    try:
        service = DependencyService(db=db)
        source = data.get("depends_on_task_id") or data["source_task_id"]
        target = data.get("target_task_id", task_id)
        result = service.create_dependency(
            source_task_id=source,
            target_task_id=target,
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=400, detail="Missing required field: source_task_id or depends_on_task_id")


@router.get("/{task_id}/depend", tags=["tasks"])
def list_dependencies(
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看依赖"""
    try:
        service = DependencyService(db=db)
        return {
            "code": 0,
            "message": "success",
            "data": {"dependencies": service.get_dependencies(task_id)},
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}/depend/graph", tags=["tasks"])
def get_dependency_graph(
    task_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取依赖图"""
    try:
        service = DependencyService(db=db)
        return {
            "code": 0,
            "message": "success",
            "data": service.get_dependency_graph(task_id),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}/depend/{target_id}", tags=["tasks"])
def delete_dependency(
    task_id: str,
    target_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除依赖"""
    try:
        service = DependencyService(db=db)
        service.delete_dependency(task_id, target_id)
        return {
            "code": 0,
            "message": "success",
            "data": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
