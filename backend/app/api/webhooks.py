from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.agent import Agent
from app.schemas.agent import HermesStatusWebhook, HermesTaskCompletedWebhook

router = APIRouter(redirect_slashes=False)


@router.post("/webhooks/hermes/status", response_model=dict)
def hermes_status_webhook(
    data: HermesStatusWebhook,
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.name == data.agent_name).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{data.agent_name}' not found")

    event = data.event
    if event in ("online", "offline", "busy"):
        agent.status = event

    db.commit()
    return {
        "code": 0,
        "message": "status webhook processed",
        "data": {"agent": agent.name, "event": event},
    }


@router.post("/webhooks/hermes/task-completed", response_model=dict)
def hermes_task_completed_webhook(
    data: HermesTaskCompletedWebhook,
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.name == data.agent_name).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{data.agent_name}' not found")

    return {
        "code": 0,
        "message": "task completed webhook received",
        "data": {
            "agent_name": data.agent_name,
            "task_id": data.task_id,
            "status": data.status,
            "result": data.result,
        },
    }
