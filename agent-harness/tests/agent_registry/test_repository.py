import pytest
from datetime import datetime, timezone
from backend.agent_registry.models import AgentCard, AgentStatus, HealthStatus
from backend.agent_registry.repository import RegistryRepository


@pytest.fixture
async def repo():
    r = RegistryRepository(":memory:")
    await r.initialize()
    yield r
    await r.close()


@pytest.mark.asyncio
class TestRegistryRepository:
    async def test_register_and_get_agent(self, repo):
        card = AgentCard(
            agent_id="test-1",
            name="test-agent",
            version="1.0.0",
            capabilities=["search"],
        )
        await repo.register(card)
        retrieved = await repo.get("test-1")
        assert retrieved is not None
        assert retrieved.agent_id == "test-1"
        assert retrieved.name == "test-agent"

    async def test_get_nonexistent_agent(self, repo):
        result = await repo.get("nonexistent")
        assert result is None

    async def test_list_agents(self, repo):
        cards = [
            AgentCard(agent_id=f"agent-{i}", name=f"Agent {i}", version="1.0.0")
            for i in range(3)
        ]
        for c in cards:
            await repo.register(c)
        all_agents = await repo.list()
        assert len(all_agents) == 3

    async def test_list_agents_with_status_filter(self, repo):
        active = AgentCard(agent_id="a1", name="Active", version="1.0.0", status=AgentStatus.ACTIVE)
        inactive = AgentCard(agent_id="a2", name="Inactive", version="1.0.0", status=AgentStatus.INACTIVE)
        await repo.register(active)
        await repo.register(inactive)
        result = await repo.list(status=AgentStatus.ACTIVE)
        assert len(result) == 1
        assert result[0].agent_id == "a1"

    async def test_update_status(self, repo):
        card = AgentCard(agent_id="test-1", name="test", version="1.0.0")
        await repo.register(card)
        await repo.update_status("test-1", AgentStatus.ACTIVE)
        retrieved = await repo.get("test-1")
        assert retrieved.status == AgentStatus.ACTIVE

    async def test_record_and_get_health(self, repo):
        card = AgentCard(agent_id="test-1", name="test", version="1.0.0")
        await repo.register(card)
        hs = HealthStatus(agent_id="test-1", status=AgentStatus.ACTIVE)
        await repo.record_heartbeat(hs)
        history = await repo.get_health_history("test-1", limit=10)
        assert len(history) == 1
        assert history[0].status == AgentStatus.ACTIVE

    async def test_register_duplicate_updates(self, repo):
        card1 = AgentCard(agent_id="dup", name="v1", version="1.0.0")
        card2 = AgentCard(agent_id="dup", name="v2", version="2.0.0")
        await repo.register(card1)
        await repo.register(card2)
        retrieved = await repo.get("dup")
        assert retrieved.name == "v2"

    async def test_delete_agent(self, repo):
        card = AgentCard(agent_id="del-me", name="delete", version="1.0.0")
        await repo.register(card)
        await repo.delete("del-me")
        assert await repo.get("del-me") is None
