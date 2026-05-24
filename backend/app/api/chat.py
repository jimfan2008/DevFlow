from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.project import Project
from app.services.gateway_client import GatewayClient
import logging

router = APIRouter(prefix="/api", tags=["chat"])

chat_logger = logging.getLogger("devflow.chat")


class AgentChatRequest(BaseModel):
    message: str


@router.post("/agents/{agent_id}/chat", response_model=dict)
async def agent_chat_endpoint(
    agent_id: str,
    data: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_logger.info(f"Agent chat: agent_id={agent_id}, message={data.message[:50]}")
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    config = agent.config or {}
    port = config.get("gateway_port")
    use_cli = config.get("use_cli", False)

    if port:
        client = GatewayClient(port=port)
        api_key = config.get("api_key")
        if api_key:
            client._api_key = api_key
    elif use_cli:
        client = GatewayClient(profile_name=agent.name)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{agent.name}' has no gateway port configured and CLI mode is not enabled"
        )

    try:
        result = await client.send_message_non_stream(data.message)
        chat_logger.info(f"Agent chat response received, length={len(result)}")
        return {"code": 0, "message": "success", "data": {"reply": result}}
    except Exception as e:
        chat_logger.error(f"Agent chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/chat/test")
async def chat_test_endpoint():
    """Test endpoint to verify routing"""
    chat_logger.info("chat_test_endpoint called")
    return {"code": 0, "message": "success", "data": "Test endpoint works"}


@router.post("/projects/chat", response_model=dict)
async def chat_endpoint(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chat endpoint that connects to real Hermes Agent"""
    chat_logger.info(f"chat_endpoint called: message={data.get('message', '')[:50]}, project_id={data.get('project_id')}")

    project_id = data.get('project_id')
    message = data.get('message', '')

    project = db.query(Project).filter(Project.id == project_id).first()
    chat_logger.info(f"Project found: {project.id if project else None}")

    agent = db.query(Agent).filter(Agent.agent_type == 'hermes', Agent.status == 'online').first()
    chat_logger.info(f"Agent found: {agent.name if agent else None}")

    if not agent:
        raise HTTPException(status_code=404, detail="No available Hermes agent")

    config = agent.config or {}
    port = config.get("gateway_port")
    use_cli = config.get("use_cli", False)

    if port:
        client = GatewayClient(port=port)
        api_key = config.get("api_key")
        if api_key:
            client._api_key = api_key
    elif use_cli:
        client = GatewayClient(profile_name=agent.name)
    else:
        raise HTTPException(status_code=400, detail="Agent has no gateway port and CLI mode is not enabled")

    try:
        result = await client.send_message_non_stream(message)
        chat_logger.info(f"Received response from Hermes, length: {len(result)}")
        return {"code": 0, "message": "success", "data": {"reply": result}}
    except Exception as e:
        chat_logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))