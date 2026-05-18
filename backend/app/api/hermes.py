import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.config import settings
from app.models.agent import Agent
from app.models.user import User
from app.services.gateway_client import GatewayClient
from app.services.gateway_health import check_gateway_health
import logging

logger = logging.getLogger("devflow.hermes")
router = APIRouter()


@router.get("/hermes/health", response_model=dict)
async def hermes_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hermes_agents = db.query(Agent).filter(Agent.agent_type == "hermes").all()
    results = []
    overall_healthy = False

    for agent in hermes_agents:
        config = agent.config or {}
        port = config.get("gateway_port")
        api_key = config.get("api_key")
        if port:
            health = await check_gateway_health(port, api_key)
            results.append({
                "agent_id": agent.id,
                "name": agent.name,
                "healthy": health.get("healthy", False),
                "port": port,
            })
            if health.get("healthy"):
                overall_healthy = True
        else:
            results.append({
                "agent_id": agent.id,
                "name": agent.name,
                "healthy": False,
                "port": None,
            })

    if not hermes_agents and settings.HERMES_API_BASE:
        try:
            resp = httpx.get(
                f"{settings.HERMES_API_BASE.rstrip('/v1').rstrip('/')}/health",
                timeout=5.0,
            )
            overall_healthy = resp.status_code == 200
        except Exception:
            pass

    return {
        "code": 0,
        "message": "success",
        "data": {
            "healthy": overall_healthy,
            "agents": results,
        },
    }


@router.post("/hermes/chat", response_model=dict)
async def hermes_chat(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = data.get("message", "")
    profile_name = data.get("profile_name")
    conversation_history = data.get("conversation_history")

    agent = _resolve_hermes_agent(db, profile_name)
    if not agent:
        raise HTTPException(status_code=404, detail="No available Hermes agent")

    config = agent.config or {}
    port = config.get("gateway_port")
    api_key = config.get("api_key")

    if not port:
        raise HTTPException(status_code=400, detail=f"Agent '{agent.name}' has no gateway port")

    client = GatewayClient(port=port)
    client._api_key = api_key

    try:
        response = await client.send_message_non_stream(message, conversation_history)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "reply": response,
                "agent_id": agent.id,
                "agent_name": agent.name,
            },
        }
    except (TimeoutError, ConnectionError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hermes/chat/stream")
async def hermes_chat_stream(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = data.get("message", "")
    profile_name = data.get("profile_name")
    conversation_history = data.get("conversation_history")

    agent = _resolve_hermes_agent(db, profile_name)
    if not agent:
        raise HTTPException(status_code=404, detail="No available Hermes agent")

    config = agent.config or {}
    port = config.get("gateway_port")
    api_key = config.get("api_key")

    if not port:
        raise HTTPException(status_code=400, detail=f"Agent '{agent.name}' has no gateway port")

    client = GatewayClient(port=port)
    client._api_key = api_key

    async def event_generator():
        try:
            async for chunk in client.stream_message(message, conversation_history):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {{'error': '{str(e)}'}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/hermes/status", response_model=dict)
def hermes_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hermes_agent = db.query(Agent).filter(Agent.agent_type == "hermes").first()
    if hermes_agent:
        agent_info = hermes_agent.to_dict()
    else:
        agent_info = None

    return {
        "code": 0,
        "message": "success",
        "data": {
            "agent": agent_info,
            "connected": hermes_agent.status == "online" if hermes_agent else False,
        },
    }


def _resolve_hermes_agent(db: Session, profile_name: str = None) -> Agent:
    if profile_name:
        agent = db.query(Agent).filter(Agent.name == profile_name, Agent.agent_type == "hermes").first()
        if agent:
            return agent
    agent = db.query(Agent).filter(Agent.agent_type == "hermes", Agent.status == "online").first()
    return agent
