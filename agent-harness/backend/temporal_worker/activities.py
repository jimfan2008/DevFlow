from dataclasses import dataclass
from typing import Optional
from temporalio import activity


@dataclass
class AgentInput:
    agent_id: str
    name: str
    version: str
    capabilities: Optional[list[str]] = None
    endpoints: Optional[dict[str, str]] = None


@dataclass
class HealthCheckResult:
    status: str
    message: str = ""
    metrics: Optional[dict[str, float]] = None


_REGISTRY_URL = "http://localhost:8000"


def _get_registry_url() -> str:
    try:
        return activity.info().headers.get("registry-url", _REGISTRY_URL)
    except RuntimeError:
        return _REGISTRY_URL


@activity.defn
async def register_agent_activity(input: AgentInput) -> dict:
    import httpx
    registry_url = _get_registry_url()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{registry_url}/api/v1/agents",
            json={
                "agent_id": input.agent_id,
                "name": input.name,
                "version": input.version,
                "capabilities": input.capabilities or [],
                "endpoints": input.endpoints or {},
            },
        )
        resp.raise_for_status()
        return resp.json()["data"]


@activity.defn
async def check_agent_health_activity(agent_id: str) -> HealthCheckResult:
    import httpx
    registry_url = _get_registry_url()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{registry_url}/api/v1/agents/{agent_id}")
            if resp.status_code == 404:
                return HealthCheckResult(status="error", message="Agent not found in registry")
            resp.raise_for_status()
            data = resp.json()["data"]
            return HealthCheckResult(
                status=data["status"],
                metrics=data.get("metadata", {}).get("metrics"),
            )
    except httpx.RequestError as e:
        return HealthCheckResult(status="error", message=str(e))
