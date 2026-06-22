import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from main import create_app


@pytest.fixture
async def client():
    app = create_app(db_url=":memory:")
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


@pytest.mark.asyncio
class TestAgentAPI:
    async def test_register_agent(self, client):
        resp = await client.post(
            "/api/v1/agents",
            json={
                "agent_id": "api-1",
                "name": "API Agent",
                "version": "1.0.0",
                "capabilities": ["search"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["data"]["agent_id"] == "api-1"
        assert data["data"]["status"] == "active"

    async def test_list_agents(self, client):
        await client.post(
            "/api/v1/agents",
            json={"agent_id": "l1", "name": "L1", "version": "1.0.0"},
        )
        await client.post(
            "/api/v1/agents",
            json={"agent_id": "l2", "name": "L2", "version": "1.0.0"},
        )
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    async def test_get_agent(self, client):
        await client.post(
            "/api/v1/agents",
            json={"agent_id": "get-1", "name": "Getter", "version": "1.0.0"},
        )
        resp = await client.get("/api/v1/agents/get-1")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Getter"

    async def test_get_agent_not_found(self, client):
        resp = await client.get("/api/v1/agents/nope")
        assert resp.status_code == 404

    async def test_heartbeat(self, client):
        await client.post(
            "/api/v1/agents",
            json={"agent_id": "hb-api", "name": "HB", "version": "1.0.0"},
        )
        resp = await client.post(
            "/api/v1/agents/hb-api/heartbeat",
            json={"status": "active", "metrics": {"cpu": 0.5}},
        )
        assert resp.status_code == 200
        # verify agent status updated
        get_resp = await client.get("/api/v1/agents/hb-api")
        assert get_resp.json()["data"]["status"] == "active"

    async def test_delete_agent(self, client):
        await client.post(
            "/api/v1/agents",
            json={"agent_id": "del", "name": "Del", "version": "1.0.0"},
        )
        resp = await client.delete("/api/v1/agents/del")
        assert resp.status_code == 200
        get_resp = await client.get("/api/v1/agents/del")
        assert get_resp.status_code == 404
