from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from backend.agent_registry.service import RegistryService
from backend.agent_registry.models import (
    AgentStatus, HeartbeatRequest, RegisterAgentRequest, StatusUpdateRequest,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _ok(data: dict | list | str) -> dict:
    return {"status": "ok", "data": data}


def _get_svc(request: Request) -> RegistryService:
    return request.app.state.registry_service


@router.post("")
async def register_agent(body: RegisterAgentRequest, request: Request):
    svc = _get_svc(request)
    card = await svc.register_agent(
        agent_id=body.agent_id,
        name=body.name,
        version=body.version,
        description=body.description,
        capabilities=body.capabilities,
        endpoints=body.endpoints,
    )
    return _ok(card.model_dump(mode="json"))


@router.get("")
async def list_agents(
    request: Request, status: Optional[str] = None
):
    svc = _get_svc(request)
    status_filter = AgentStatus(status) if status else None
    agents = await svc.list_agents(status=status_filter)
    return _ok([a.model_dump(mode="json") for a in agents])


@router.get("/{agent_id}")
async def get_agent(agent_id: str, request: Request):
    svc = _get_svc(request)
    card = await svc.get_agent(agent_id)
    if not card:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _ok(card.model_dump(mode="json"))


@router.patch("/{agent_id}/status")
async def update_agent_status(agent_id: str, body: StatusUpdateRequest, request: Request):
    svc = _get_svc(request)
    updated = await svc.update_agent_status(agent_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Agent not found")
    card = await svc.get_agent(agent_id)
    return _ok(card.model_dump(mode="json"))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, request: Request):
    svc = _get_svc(request)
    deleted = await svc.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _ok({"deleted": agent_id})


@router.post("/{agent_id}/heartbeat")
async def report_heartbeat(agent_id: str, body: HeartbeatRequest, request: Request):
    svc = _get_svc(request)
    try:
        hs = await svc.report_health(
            agent_id=agent_id,
            status=body.status,
            message=body.message,
            metrics=body.metrics,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _ok(hs.model_dump(mode="json"))
