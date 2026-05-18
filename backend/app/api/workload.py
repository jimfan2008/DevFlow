#!/usr/bin/env python3
"""负载 API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.workload_service import WorkloadService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/{board_id}/workload", tags=["workload"])
def get_workload(board_id: str, user_id: str = None, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkloadService(db=db)
    try:
        return service.get_workload(board_id, user_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

@router.get("/{board_id}/workload/trend", tags=["workload"])
def get_workload_trend(board_id: str, days: int = 7, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timezone, timedelta
    from app.models.task import Task
    service = WorkloadService(db=db)
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        tasks = db.query(Task).filter(
            Task.board_id == board_id,
            Task.created_at >= start_date,
            Task.status != "done"
        ).all()
        trend = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_tasks = [t for t in tasks if t.created_at and t.created_at.date() == day.date()]
            trend.append({
                "date": day.isoformat(),
                "created": len([t for t in day_tasks if t.status != "done"]),
                "completed": len([t for t in day_tasks if t.status == "done"]),
            })
        return {"success": True, "trend": trend, "history": trend, "days": days}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/auto-assign", tags=["workload"])
def auto_assign(board_id: str, data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkloadService(db=db)
    try:
        result = service.auto_assign_task(data["task_id"])
        return {"success": True, "task": result["task"], "assigned_to": result["assigned_to"]}
    except Exception as e:
        return {"success": False, "error": str(e)}
