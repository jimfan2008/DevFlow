import pytest
from unittest.mock import AsyncMock, patch
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


VALID_SPIFFE = "spiffe://example.org/agent"


@pytest.mark.asyncio
class TestAuthMiddleware:
    async def test_no_auth_header_returns_401(self, client):
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 401

    async def test_invalid_spiffe_id_returns_401(self, client):
        resp = await client.get(
            "/api/v1/agents", headers={"X-SPIFFE-ID": "not-valid"}
        )
        assert resp.status_code == 401

    async def test_valid_spiffe_id_passes(self, client):
        with patch(
            "backend.security.opa_client.OPAClient.check_permission",
            new=AsyncMock(return_value=True),
        ):
            resp = await client.get(
                "/api/v1/agents", headers={"X-SPIFFE-ID": VALID_SPIFFE}
            )
            assert resp.status_code == 200

    async def test_health_endpoint_bypasses_auth(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
