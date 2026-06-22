from typing import Optional
from backend.agent_registry.models import AgentCard, AgentStatus, HealthStatus
from backend.agent_registry.repository import RegistryRepository


class RegistryService:
    def __init__(self, db_url: str):
        self._repo = RegistryRepository(db_url)

    async def initialize(self) -> None:
        await self._repo.initialize()

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        version: str,
        description: Optional[str] = None,
        capabilities: Optional[list[str]] = None,
        endpoints: Optional[dict[str, str]] = None,
        auth_spiffe_id: Optional[str] = None,
    ) -> AgentCard:
        card = AgentCard(
            agent_id=agent_id,
            name=name,
            version=version,
            description=description,
            capabilities=capabilities or [],
            endpoints=endpoints or {},
            auth_spiffe_id=auth_spiffe_id,
            status=AgentStatus.ACTIVE,
        )
        return await self._repo.register(card)

    async def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        return await self._repo.get(agent_id)

    async def list_agents(
        self, status: Optional[AgentStatus] = None
    ) -> list[AgentCard]:
        return await self._repo.list(status=status)

    async def delete_agent(self, agent_id: str) -> bool:
        return await self._repo.delete(agent_id)

    async def report_health(
        self,
        agent_id: str,
        status: AgentStatus,
        message: Optional[str] = None,
        metrics: Optional[dict[str, float]] = None,
    ) -> HealthStatus:
        existing = await self._repo.get(agent_id)
        if not existing:
            raise ValueError(f"Agent {agent_id} not found")
        hs = HealthStatus(
            agent_id=agent_id,
            status=status,
            message=message,
            metrics=metrics or {},
        )
        await self._repo.record_heartbeat(hs)
        await self._repo.update_status(agent_id, status)
        return hs

    async def get_health_history(
        self, agent_id: str, limit: int = 20
    ) -> list[HealthStatus]:
        return await self._repo.get_health_history(agent_id, limit)

    async def close(self) -> None:
        await self._repo.close()

    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        return await self._repo.update_status(agent_id, status)
