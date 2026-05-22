#!/usr/bin/env python3
"""负载 API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.workload_service import WorkloadService
from app.api.deps import get_current_user

router = APIRouter(redirect_slashes=False)

@router.get("/{project_id}/workload", tags=["workload"])
def get_workload(project_id: str, user_id: str = None, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkloadService(db=db)
    try:
        return {"code": 0, "message": "success", "data": service.get_workload(project_id, user_id)}
    except ValueError as e:
        return {"code": 1, "message": str(e)}

@router.get("/{project_id}/workload/trend", tags=["workload"])
def get_workload_trend(project_id: str, days: int = 7, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timezone, timedelta
    from app.models.task import Task
    try:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        tasks = db.query(Task).filter(
            Task.project_id == project_id,
            Task.created_at >= start_date,
        ).all()
        trend = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_tasks = [t for t in tasks if t.created_at and t.created_at.date() == day.date()]
            trend.append({
                "date": day.isoformat(),
                "active": len([t for t in day_tasks if t.status not in ("accepted", "rejected")]),
                "completed": len([t for t in day_tasks if t.status == "accepted"]),
            })
        return {"code": 0, "message": "success", "data": {"trend": trend, "days": days}}
    except Exception as e:
        return {"code": 1, "message": str(e)}

@router.post("/auto-assign", tags=["workload"])
def auto_assign(data: dict, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkloadService(db=db)
    try:
        result = service.auto_assign_task(data["task_id"])
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        return {"code": 1, "message": str(e)}
