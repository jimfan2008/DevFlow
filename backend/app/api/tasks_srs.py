# 任务执行 & 验收 API - SRS §3.3 & §3.4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.task import Task
from app.models.task_execution import TaskExecution
from app.models.board import Board
from app.models.project import Project
from app.services.agent_scheduler_service import AgentSchedulerService
from app.services.acceptance_service import AcceptanceService
from app.services.delivery_service import DeliveryService
from app.schemas.agent import TaskDeliverRequest
from app.schemas.acceptance import AcceptanceResult, FinalAcceptanceResponse

router = APIRouter()


@router.post("/tasks/{task_id}/deliver", response_model=dict)
def deliver_task_result(
    task_id: str,
    data: TaskDeliverRequest,
    db: Session = Depends(get_db),
):
    """SRS §3.3.2 - 编程 Agent 交付任务成果"""
    scheduler = AgentSchedulerService(db=db)
    execution = db.query(TaskExecution).filter(
        TaskExecution.task_id == task_id,
        TaskExecution.status.in_(["pending", "running"]),
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="No active execution found for task")

    execution = scheduler.complete_execution(execution.id, data.result)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "execution_id": execution.id,
            "task_id": task_id,
            "status": execution.status,
            "delivered_at": execution.delivered_at.isoformat() if execution.delivered_at else None,
        },
    }


@router.post("/tasks/{task_id}/accept", response_model=dict)
def accept_task_result(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.4.1 - Hermes Agent 验收任务成果"""
    execution = db.query(TaskExecution).filter(
        TaskExecution.task_id == task_id,
        TaskExecution.status == "delivered",
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="No delivered execution found for task")

    acceptance = AcceptanceService(db=db)
    try:
        result = acceptance.verify_delivery(execution.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 通知用户
    delivery = DeliveryService(db=db)
    task = db.query(Task).filter(Task.id == task_id).first()
    if task and task.assignee_id:
        delivery.notify_acceptance_result(
            user_id=task.assignee_id,
            task_title=task.title,
            passed=result["result"] == "pass",
            detail=result.get("suggestions", ["验收完成"])[0] if result["suggestions"] else "全部检查项通过",
        )

    return {
        "code": 0,
        "message": "success",
        "data": result,
    }


@router.get("/tasks/{task_id}/executions", response_model=dict)
def get_task_executions(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.3.2 - 获取任务执行记录"""
    executions = db.query(TaskExecution).filter(
        TaskExecution.task_id == task_id,
    ).order_by(TaskExecution.created_at.desc()).all()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "executions": [
                {
                    "id": e.id,
                    "agent_id": e.agent_id,
                    "status": e.status,
                    "result_summary": e.result_summary,
                    "problem_details": e.problem_details,
                    "delivered_at": e.delivered_at.isoformat() if e.delivered_at else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in executions
            ],
            "total": len(executions),
        },
    }