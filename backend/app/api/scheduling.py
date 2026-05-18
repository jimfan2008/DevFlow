# Agent 调度 API - 处理任务分配、执行监控和验收
# SRS §3.4 - Project-nested routes for project-level task management
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from app.database import get_db
from app.services.agent_scheduling_service import AgentSchedulingService
from app.services.acceptance_service import AcceptanceService
from app.schemas.scheduling import (
    TaskAssignRequest, TaskExecutionResponse,
    TaskDeliveryRequest,
    TaskAcceptanceRequest,
)
from app.models.task_execution import TaskExecution

router = APIRouter(prefix="/projects/{project_id}", tags=["scheduling"])


@router.post("/tasks/decompose", response_model=List[TaskExecutionResponse])
def decompose_tasks(
    project_id: str,
    db: Session = Depends(get_db)
):
    """SRS §3.2.1 - 触发任务拆解：根据需求自动拆解为原子任务"""
    from app.services.task_decomposition_service import TaskDecompositionService
    service = TaskDecompositionService(db)
    tasks = service.decompose_tasks(project_id)
    return [
        TaskExecutionResponse(
            id=task.id,
            task_id=task.id,
            agent_id=None,
            status=task.status,
            execution_log=None,
            result_summary=None,
            problem_details=None,
            delivered_at=None,
            created_at=task.created_at,
            updated_at=task.updated_at
        ) for task in tasks
    ]


@router.post("/tasks/{task_id}/assign", response_model=TaskExecutionResponse)
def assign_task(
    project_id: str,
    task_id: str,
    request: TaskAssignRequest,
    db: Session = Depends(get_db)
):
    """SRS §3.4.1 - 分配 Agent 执行指定任务"""
    service = AgentSchedulingService(db)
    execution = service.assign_task(task_id, request.agent_type)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assign task {task_id}"
        )
    return execution


@router.get("/tasks/{task_id}/executions", response_model=List[TaskExecutionResponse])
def get_task_executions(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db)
):
    """SRS §3.4.2 - 获取任务的所有执行记录"""
    executions = db.query(TaskExecution).filter(
        TaskExecution.task_id == task_id
    ).order_by(TaskExecution.created_at.desc()).all()
    return executions


@router.post("/tasks/{task_id}/deliver", response_model=TaskExecutionResponse)
def deliver_task(
    project_id: str,
    task_id: str,
    request: TaskDeliveryRequest,
    db: Session = Depends(get_db)
):
    """SRS §3.4.2 - Agent 交付任务成果"""
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
    return execution


@router.post("/tasks/{task_id}/accept", response_model=dict)
def accept_task(
    project_id: str,
    task_id: str,
    request: TaskAcceptanceRequest,
    db: Session = Depends(get_db)
):
    """SRS §3.5.1 - Hermes 验收任务成果"""
    service = AcceptanceService(db)
    acceptance = service.accept_delivery(
        execution_id=request.execution_id,
        result=request.result,
        problem_details=request.problem_details
    )
    return acceptance


@router.get("/progress", response_model=dict)
def get_project_progress(
    project_id: str,
    db: Session = Depends(get_db)
):
    """SRS §3.4.2 - 获取项目的整体进度"""
    service = AgentSchedulingService(db)
    progress = service.get_task_progress(project_id)
    return progress
