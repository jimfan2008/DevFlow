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
class TestAuthMiddleware:
    async def test_no_auth_header(self, client):
        resp = await client.get("/api/v1/agents")
        # Without middleware, should still work (middleware not enabled yet)
        assert resp.status_code == 200
