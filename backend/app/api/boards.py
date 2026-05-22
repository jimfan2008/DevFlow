#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 看板 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.board_service import BoardService
from app.services.workload_service import WorkloadService
from app.api.deps import get_current_user
from app.schemas.board import (
    BoardCreate, BoardUpdate, BoardColumnCreate, BoardColumnUpdate,
)
from app.models.board import Board, BoardColumn
from app.models.task import Task

from datetime import datetime, timezone, timedelta

router = APIRouter(redirect_slashes=False)


def _get_service(db: Session, current_user):
    return BoardService(db=db, current_user_id=current_user.id)


@router.post("", tags=["boards"])
def create_board(
    data: BoardCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建看板"""
    try:
        service = _get_service(db, current_user)
        result = service.create_board(
            name=data.name,
            project_id=data.project_id,
            description=data.description,
            color=data.color,
            position=data.position,
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", tags=["boards"])
def list_boards(
    project_id: str = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出看板"""
    service = _get_service(db, current_user)
    boards = service.list_boards(project_id or "")
    return {
        "code": 0,
        "message": "success",
        "data": {"boards": boards, "total": len(boards)},
    }


@router.get("/{board_id}", tags=["boards"])
def get_board(
    board_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取看板详情"""
    try:
        service = _get_service(db, current_user)
        return {
            "code": 0,
            "message": "success",
            "data": service.get_board(board_id),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{board_id}", tags=["boards"])
def update_board(
    board_id: str,
    data: BoardUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新看板"""
    try:
        service = _get_service(db, current_user)
        result = service.update_board(
            board_id, **data.model_dump(exclude_unset=True)
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{board_id}", tags=["boards"])
def update_board_patch(
    board_id: str,
    data: BoardUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新看板（部分更新）"""
    try:
        service = _get_service(db, current_user)
        result = service.update_board(
            board_id, **data.model_dump(exclude_unset=True)
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{board_id}", tags=["boards"])
def delete_board(
    board_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除看板"""
    try:
        service = _get_service(db, current_user)
        service.delete_board(board_id)
        return {
            "code": 0,
            "message": "看板已删除",
            "data": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{board_id}/columns", tags=["boards"])
def get_columns(
    board_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取看板列列表"""
    try:
        service = _get_service(db, current_user)
        return {
            "code": 0,
            "message": "success",
            "data": {"columns": service.get_board_columns(board_id)},
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{board_id}/columns", tags=["boards"])
def create_column(
    board_id: str,
    data: BoardColumnCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建看板列"""
    try:
        service = _get_service(db, current_user)
        result = service.create_column(
            board_id=board_id,
            name=data.name,
            color=data.color,
            position=data.position,
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{board_id}/columns/{column_id}", tags=["boards"])
def update_column(
    board_id: str,
    column_id: str,
    data: BoardColumnUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新看板列"""
    try:
        service = _get_service(db, current_user)
        result = service.update_column(
            column_id, **data.model_dump(exclude_unset=True)
        )
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{board_id}/columns/{column_id}", tags=["boards"])
def delete_column(
    board_id: str,
    column_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除看板列"""
    try:
        service = _get_service(db, current_user)
        service.delete_column(column_id)
        return {
            "code": 0,
            "message": "看板列已删除",
            "data": None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{board_id}/workload", tags=["workload"])
def get_workload(
    board_id: str,
    user_id: str = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取看板负载"""
    try:
        service = WorkloadService(db=db)
        result = service.get_workload(board_id, user_id)
        return {
            "code": 0,
            "message": "success",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{board_id}/workload/trend", tags=["workload"])
def get_workload_trend(
    board_id: str,
    days: int = Query(7, ge=1, le=90),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取任务趋势"""
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        tasks = db.query(Task).filter(
            Task.project_id == board_id,
            Task.created_at >= start_date,
        ).all()

        trend = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_tasks = [
                t for t in tasks
                if t.created_at and t.created_at.date() == day.date()
            ]
            trend.append({
                "date": day.isoformat(),
                "created": len([t for t in day_tasks if t.status not in ("accepted", "delivered")]),
                "completed": len([t for t in day_tasks if t.status in ("accepted", "delivered")]),
            })
        return {
            "code": 0,
            "message": "success",
            "data": {"trend": trend, "history": trend, "days": days},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
