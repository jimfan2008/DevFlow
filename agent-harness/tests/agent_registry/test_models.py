import pytest
from pydantic import ValidationError
from backend.agent_registry.models import AgentStatus, AgentCard, HealthStatus


class TestAgentStatus:
    def test_enum_values(self):
        assert AgentStatus.ACTIVE.value == "active"
        assert AgentStatus.INACTIVE.value == "inactive"
        assert AgentStatus.DEGRADED.value == "degraded"
        assert AgentStatus.ERROR.value == "error"


class TestAgentCard:
    def test_valid_agent_card(self):
        card = AgentCard(
            agent_id="test-agent-1",
            name="test-agent",
            version="1.0.0",
            capabilities=["search", "parse"],
            auth_spiffe_id="spiffe://prod/test/agent",
            endpoints={"a2a": "a2a://registry/test/agent"},
            status=AgentStatus.ACTIVE,
        )
        assert card.agent_id == "test-agent-1"
        assert card.status == AgentStatus.ACTIVE

    def test_agent_card_missing_required_fields(self):
        with pytest.raises(ValidationError):
            AgentCard()

    def test_agent_card_invalid_endpoints(self):
        with pytest.raises(ValidationError):
            AgentCard(
                agent_id="test",
                name="test",
                version="1.0.0",
                capabilities=[],
                endpoints="not-a-dict",
            )


class TestHealthStatus:
    def test_valid_health_status(self):
        hs = HealthStatus(
            agent_id="test-1",
            status=AgentStatus.ACTIVE,
            last_heartbeat="2026-06-22T00:00:00Z",
            metrics={"cpu": 0.5, "memory": 128},
        )
        assert hs.agent_id == "test-1"

    def test_health_status_defaults(self):
        hs = HealthStatus(agent_id="test-2", status=AgentStatus.ACTIVE)
        assert hs.last_heartbeat is not None
        assert hs.metrics == {}
