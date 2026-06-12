from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.project import Project
from app.services.gateway_client import GatewayClient
from app.services.hermes.hermes_api_client import HermesAPIClient
from app.config import settings
import logging

router = APIRouter(prefix="/api", tags=["chat"])

chat_logger = logging.getLogger("devflow.chat")

_fallback_client: HermesAPIClient | None = None


def _get_fallback_client() -> HermesAPIClient:
    global _fallback_client
    if _fallback_client is None:
        _fallback_client = HermesAPIClient(
            base_url=settings.HERMES_API_BASE,
            api_key=settings.HERMES_API_KEY,
            model=settings.HERMES_MODEL,
        )
    return _fallback_client


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

    last_error = None

    # Try 1: Gateway via HTTP port
    if port:
        try:
            client = GatewayClient(port=port)
            api_key = config.get("api_key")
            if api_key:
                client._api_key = api_key
            result = await client.send_message_non_stream(data.message)
            chat_logger.info(f"Agent chat response received via gateway, length={len(result)}")
            return {"code": 0, "message": "success", "data": {"reply": result}}
        except Exception as e:
            chat_logger.warning(f"Gateway port chat failed: {e}")
            last_error = e

    # Try 2: CLI mode
    if use_cli or (not port and not last_error):
        try:
            client = GatewayClient(profile_name=agent.name)
            result = await client.send_message_non_stream(data.message)
            chat_logger.info(f"Agent chat response received via CLI, length={len(result)}")
            return {"code": 0, "message": "success", "data": {"reply": result}}
        except Exception as e:
            chat_logger.warning(f"CLI chat failed: {e}")
            last_error = e

    # Try 3: Fallback via global HermesAPIClient (uses HERMES_API_BASE)
    try:
        client = _get_fallback_client()
        messages = [{"role": "user", "content": data.message}]
        result = await client.chat_completions(messages)
        reply = result.content or ""
        chat_logger.info(f"Agent chat response received via fallback API, length={len(reply)}")
        return {"code": 0, "message": "success", "data": {"reply": reply}}
    except Exception as e:
        chat_logger.error(f"Fallback API chat also failed: {e}")
        last_error = e

    raise HTTPException(
        status_code=503,
        detail=f"与 Hermes Agent '{agent.name}' 通信失败: {last_error or '所有连接方式均不可用'}"
    )


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