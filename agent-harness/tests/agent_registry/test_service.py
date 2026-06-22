import pytest
from backend.agent_registry.models import AgentCard, AgentStatus, HealthStatus
from backend.agent_registry.service import RegistryService


@pytest.fixture
async def service():
    s = RegistryService(":memory:")
    await s.initialize()
    yield s
    await s.close()


@pytest.mark.asyncio
class TestRegistryService:
    async def test_register_lifecycle(self, service):
        card = await service.register_agent(
            agent_id="srv-1",
            name="Service Agent",
            version="1.0.0",
            capabilities=["monitor"],
            endpoints={"a2a": "a2a://srv-1"},
        )
        assert card.status == AgentStatus.ACTIVE

    async def test_double_register_updates(self, service):
        c1 = await service.register_agent(agent_id="srv-2", name="v1", version="1.0.0")
        c2 = await service.register_agent(agent_id="srv-2", name="v2", version="2.0.0")
        assert c2.version == "2.0.0"

    async def test_heartbeat_updates_status(self, service):
        await service.register_agent(agent_id="hb-1", name="hb", version="1.0.0")
        hs = await service.report_health(
            agent_id="hb-1", status=AgentStatus.ACTIVE, metrics={"cpu": 0.3}
        )
        assert hs.agent_id == "hb-1"
        card = await service.get_agent("hb-1")
        assert card.status == AgentStatus.ACTIVE

    async def test_heartbeat_degraded(self, service):
        await service.register_agent(agent_id="deg", name="deg", version="1.0.0")
        await service.report_health(
            agent_id="deg", status=AgentStatus.DEGRADED, message="High memory"
        )
        card = await service.get_agent("deg")
        assert card.status == AgentStatus.DEGRADED

    async def test_get_nonexistent(self, service):
        result = await service.get_agent("no-exist")
        assert result is None

    async def test_list_default_all(self, service):
        a = await service.register_agent(agent_id="a", name="A", version="1.0.0")
        b = await service.register_agent(agent_id="b", name="B", version="1.0.0")
        await service._repo.update_status("b", AgentStatus.INACTIVE)
        result = await service.list_agents()
        assert len(result) == 2
