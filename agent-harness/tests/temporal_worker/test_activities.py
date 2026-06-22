import pytest
from backend.temporal_worker.activities import (
    register_agent_activity,
    check_agent_health_activity,
    AgentInput,
    HealthCheckResult,
)


@pytest.mark.asyncio
class TestActivities:
    async def test_register_agent_activity(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/api/v1/agents",
            method="POST",
            json={
                "status": "ok",
                "data": {
                    "agent_id": "wf-1",
                    "name": "WF Agent",
                    "version": "1.0.0",
                    "status": "active",
                    "capabilities": [],
                    "endpoints": {},
                },
            },
        )
        result = await register_agent_activity(
            AgentInput(agent_id="wf-1", name="WF Agent", version="1.0.0")
        )
        assert result["agent_id"] == "wf-1"
        assert result["status"] == "active"

    async def test_health_check_failed(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8000/api/v1/agents/nonexistent-agent",
            method="GET",
            status_code=404,
            json={"detail": "Agent not found"},
        )
        result = await check_agent_health_activity("nonexistent-agent")
        assert result.status == "error"
        assert "not found" in result.message
