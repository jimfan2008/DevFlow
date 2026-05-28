# Agent 调度 API - 处理任务分配、执行监控和验收
# SRS §3.4 - Project-nested routes for project-level task management
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.agent_scheduling_service import AgentSchedulingService
from app.services.acceptance_service import AcceptanceService
from app.schemas.scheduling import (
    TaskAssignRequest, TaskExecutionResponse,
    TaskDeliveryRequest,
    TaskAcceptanceRequest,
)
from app.models.task_execution import TaskExecution

router = APIRouter(prefix="/api/projects/{project_id}", tags=["scheduling"], redirect_slashes=False)


@router.post("/tasks/decompose", response_model=dict)
def decompose_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.task_decomposition_service import TaskDecompositionService
    service = TaskDecompositionService(db)
    try:
        tasks = service.decompose_tasks(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "code": 0,
        "message": "success",
        "data": [
            {
                "id": task.id,
                "task_id": task.id,
                "agent_id": None,
                "status": task.status,
                "execution_log": None,
                "result_summary": None,
                "problem_details": None,
                "delivered_at": None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
            for task in tasks
        ],
    }


@router.post("/tasks/{task_id}/assign", response_model=dict)
def assign_task(
    project_id: str,
    task_id: str,
    request: TaskAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentSchedulingService(db)
    execution = service.assign_task(task_id, request.agent_type)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assign task {task_id}"
        )
    return {
        "code": 0,
        "message": "success",
        "data": execution.to_dict(),
    }


@router.get("/tasks/{task_id}/executions", response_model=dict)
def get_task_executions(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    executions = db.query(TaskExecution).filter(
        TaskExecution.task_id == task_id
    ).order_by(TaskExecution.created_at.desc()).all()
    return {
        "code": 0,
        "message": "success",
        "data": [e.to_dict() for e in executions],
    }


@router.post("/tasks/{task_id}/deliver", response_model=dict)
def deliver_task(
    project_id: str,
    task_id: str,
    request: TaskDeliveryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentSchedulingService(db)
    execution = service.update_execution_status(
        execution_id=request.execution_id,
        status="delivered",
        execution_log=request.execution_log,
        result_summary=request.result_summary
    )
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {request.execution_id} not found"
        )
    return {
        "code": 0,
        "message": "success",
        "data": execution.to_dict(),
    }


@router.post("/tasks/{task_id}/accept", response_model=dict)
def accept_task(
    project_id: str,
    task_id: str,
    request: TaskAcceptanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AcceptanceService(db)
    try:
        acceptance = service.verify_delivery(
            execution_id=request.execution_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "code": 0,
        "message": "success",
        "data": acceptance,
    }


@router.get("/progress", response_model=dict)
def get_project_progress(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AgentSchedulingService(db)
    progress = service.get_task_progress(project_id)
    return progress
