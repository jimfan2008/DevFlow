"""外部编程Agent蜂群启动机制 - Agent实例化（CLI命令/Gateway API）"""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.agent import Agent
from app.models.enums import AgentType
from app.schemas.agent import AgentRegister
from app.services.agent_scheduler_service import AgentSchedulerService
from app.services.gateway_client import GatewayClient


EXTERNAL_AGENT_TYPES = [
    "opencode", "cursor", "claude_code", "codebuddy",
    "lingma", "codearts", "trae", "codex",
    "pi_coding_agent", "reasonix",
]


class TestAgentApiRegistration:
    """通过 Gateway API 注册外部编程 Agent"""

    @pytest.mark.asyncio
    async def test_register_opencode_agent_via_api(self, client, db_session):
        payload = {
            "name": "OpenCode-CLI-1",
            "agent_type": "opencode",
            "api_endpoint": "http://localhost:8080/agents/opencode",
            "config": {"capabilities": ["coding", "refactoring"], "max_concurrent_tasks": 3},
        }
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["agent"]["name"] == "OpenCode-CLI-1"
        assert data["data"]["agent"]["agent_type"] == "opencode"
        assert data["data"]["agent"]["status"] == "offline"
        assert data["data"]["agent"]["api_endpoint"] == "http://localhost:8080/agents/opencode"

    @pytest.mark.asyncio
    async def test_register_cursor_agent_via_api(self, client, db_session):
        payload = {
            "name": "Cursor-Gateway-1",
            "agent_type": "cursor",
            "api_endpoint": "http://localhost:18765/cursor",
            "config": {"capabilities": ["coding", "deployment"], "max_concurrent_tasks": 2},
        }
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["agent"]["agent_type"] == "cursor"

    @pytest.mark.asyncio
    async def test_register_claude_code_agent_via_api(self, client, db_session):
        payload = {
            "name": "ClaudeCode-Gateway-1",
            "agent_type": "claude_code",
            "api_endpoint": "http://localhost:8080/agents/claude",
            "config": {"capabilities": ["test_case_writing", "code_review"], "max_concurrent_tasks": 4},
        }
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["agent"]["agent_type"] == "claude_code"
        assert data["data"]["agent"]["config"]["max_concurrent_tasks"] == 4

    @pytest.mark.asyncio
    async def test_register_all_external_agent_types(self, client, db_session):
        for i, agent_type in enumerate(EXTERNAL_AGENT_TYPES):
            payload = {
                "name": f"Agent-{agent_type}-{i}",
                "agent_type": agent_type,
                "api_endpoint": f"http://localhost:8080/agents/{agent_type}",
                "config": {"capabilities": ["coding"], "max_concurrent_tasks": 1},
            }
            response = await client.post("/api/agents/register", json=payload)
            assert response.status_code == 200, f"Failed for {agent_type}: {response.text}"
            assert response.json()["data"]["agent"]["agent_type"] == agent_type

    @pytest.mark.asyncio
    async def test_register_agent_without_api_endpoint(self, client, db_session):
        payload = {
            "name": "NoEndpoint-Agent",
            "agent_type": "opencode",
        }
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 200
        assert response.json()["data"]["agent"]["api_endpoint"] is None

    @pytest.mark.asyncio
    async def test_register_agent_duplicate_name_rejected(self, client, db_session):
        payload = {"name": "Unique-Agent", "agent_type": "opencode"}
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 200

        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_agent_invalid_type_rejected(self, client, db_session):
        payload = {"name": "Bad-Agent", "agent_type": "unknown_type"}
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_agent_empty_name_rejected(self, client, db_session):
        payload = {"name": "", "agent_type": "opencode"}
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 422


class TestAgentCliRegistration:
    """通过 CLI (AgentSchedulerService) 注册外部编程 Agent"""

    def test_register_opencode_agent_via_cli(self, db_session):
        svc = AgentSchedulerService(db_session)
        agent = svc.register_agent(
            name="CLI-OpenCode-1",
            agent_type="opencode",
            api_endpoint="http://localhost:8080/cli/opencode",
            config={"capabilities": ["coding"], "source": "cli"},
        )
        assert agent.name == "CLI-OpenCode-1"
        assert agent.agent_type == "opencode"
        assert agent.status == "offline"
        assert agent.api_endpoint == "http://localhost:8080/cli/opencode"
        assert agent.config["source"] == "cli"

    def test_register_cursor_agent_via_cli(self, db_session):
        svc = AgentSchedulerService(db_session)
        agent = svc.register_agent(
            name="CLI-Cursor-1",
            agent_type="cursor",
            api_endpoint="http://localhost:18765/cli/cursor",
        )
        assert agent.agent_type == "cursor"

    def test_register_multiple_agents_via_cli(self, db_session):
        svc = AgentSchedulerService(db_session)
        names = []
        for i, agent_type in enumerate(EXTERNAL_AGENT_TYPES[:5]):
            name = f"CLI-Batch-{agent_type}-{i}"
            agent = svc.register_agent(name=name, agent_type=agent_type)
            names.append(name)
            assert agent.id is not None

        all_agents = svc.get_available_agents()
        assert len(all_agents) == 0

    def test_register_agent_then_bring_online_via_cli(self, db_session):
        svc = AgentSchedulerService(db_session)
        agent = svc.register_agent(name="CLI-BringOnline", agent_type="opencode")
        assert agent.status == "offline"

        agent.status = "online"
        db_session.commit()
        db_session.refresh(agent)
        assert agent.status == "online"

        available = svc.get_available_agents()
        assert len(available) == 1
        assert available[0].name == "CLI-BringOnline"

    def test_register_agent_via_cli_persists_to_db(self, db_session):
        svc = AgentSchedulerService(db_session)
        svc.register_agent(name="CLI-PersistTest", agent_type="cursor")
        db_session.commit()

        fetched = db_session.query(Agent).filter(Agent.name == "CLI-PersistTest").first()
        assert fetched is not None
        assert fetched.agent_type == "cursor"

    def test_register_agent_via_cli_without_config(self, db_session):
        svc = AgentSchedulerService(db_session)
        agent = svc.register_agent(name="CLI-NoConfig", agent_type="claude_code")
        assert agent.config == {}


class TestGatewayClientInitialization:
    """Gateway 客户端初始化与外部 Agent 连接"""

    def test_gateway_client_default_initialization(self):
        client = GatewayClient()
        assert client.profile_name == "default"
        assert client.port is None
        assert client.timeout == 120

    def test_gateway_client_custom_profile(self):
        client = GatewayClient(profile_name="work-profile")
        assert client.profile_name == "work-profile"

    def test_gateway_client_custom_port(self):
        client = GatewayClient(port=18765)
        assert client.port == 18765

    @pytest.mark.asyncio
    async def test_gateway_client_resolve_profile_no_gateway(self):
        client = GatewayClient(profile_name="nonexistent_profile")
        with pytest.raises(ValueError, match="Gateway not available"):
            await client._resolve_profile()

    def test_gateway_client_get_base_url(self):
        with patch.dict("os.environ", {"HERMES_GATEWAY_HOST": "192.168.1.100"}):
            client = GatewayClient(port=18765)
            url = client._get_base_url()
            assert url == "http://192.168.1.100:18765"

    def test_gateway_client_get_headers_with_api_key(self):
        client = GatewayClient()
        headers = client._get_headers(api_key="sk-test-key")
        assert headers["Authorization"] == "Bearer sk-test-key"
        assert headers["Content-Type"] == "application/json"

    def test_gateway_client_get_headers_without_api_key(self):
        client = GatewayClient()
        headers = client._get_headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_gateway_client_health_check_no_gateway(self):
        client = GatewayClient(profile_name="nonexistent")
        result = await client.health_check()
        assert result is False


class TestAgentStatusLifecycle:
    """外部 Agent 从注册到在线的完整生命周期"""

    @pytest.mark.asyncio
    async def test_agent_registered_offline_by_default(self, client, db_session):
        payload = {"name": "Lifecycle-Agent", "agent_type": "opencode"}
        response = await client.post("/api/agents/register", json=payload)
        assert response.json()["data"]["agent"]["status"] == "offline"

    @pytest.mark.asyncio
    async def test_agent_heartbeat_brings_online(self, client, db_session):
        register_payload = {"name": "Heartbeat-Agent", "agent_type": "cursor"}
        reg_resp = await client.post("/api/agents/register", json=register_payload)
        agent_id = reg_resp.json()["data"]["agent"]["id"]

        heartbeat_payload = {"load_level": 0.5, "status_detail": "ready"}
        beat_resp = await client.post(f"/api/agents/{agent_id}/heartbeat", json=heartbeat_payload)
        assert beat_resp.status_code == 200

        detail_resp = await client.get(f"/api/agents/{agent_id}")
        assert detail_resp.json()["data"]["agent"]["status"] == "online"

    @pytest.mark.asyncio
    async def test_agent_load_query_after_heartbeat(self, client, db_session):
        register_payload = {"name": "LoadCheck-Agent", "agent_type": "opencode"}
        reg_resp = await client.post("/api/agents/register", json=register_payload)
        agent_id = reg_resp.json()["data"]["agent"]["id"]

        await client.post(f"/api/agents/{agent_id}/heartbeat", json={"load_level": 0.8})

        load_resp = await client.get(f"/api/agents/{agent_id}/load")
        assert load_resp.json()["data"]["load"]["load_level"] == 0.8
        assert load_resp.json()["data"]["load"]["status"] == "online"

    @pytest.mark.asyncio
    async def test_agent_status_update_via_api(self, client, db_session):
        register_payload = {"name": "StatusUpdate-Agent", "agent_type": "claude_code"}
        reg_resp = await client.post("/api/agents/register", json=register_payload)
        agent_id = reg_resp.json()["data"]["agent"]["id"]

        status_resp = await client.put(
            f"/api/agents/{agent_id}/status",
            json={"status": "busy"},
        )
        assert status_resp.json()["data"]["agent"]["status"] == "busy"

    @pytest.mark.asyncio
    async def test_agent_available_filter(self, client, db_session):
        opencode_resp = await client.post("/api/agents/register", json={
            "name": "Avail-OpenCode", "agent_type": "opencode",
        })
        cursor_resp = await client.post("/api/agents/register", json={
            "name": "Avail-Cursor", "agent_type": "cursor",
        })
        oc_id = opencode_resp.json()["data"]["agent"]["id"]
        await client.post(f"/api/agents/{oc_id}/heartbeat", json={"load_level": 0})

        avail_resp = await client.get("/api/agents/available?agent_type=opencode")
        assert avail_resp.json()["data"]["total"] == 1
        assert avail_resp.json()["data"]["agents"][0]["agent_type"] == "opencode"

        all_avail = await client.get("/api/agents/available")
        assert all_avail.json()["data"]["total"] >= 1


class TestAgentRegistrationValidation:
    """Agent 注册的边界条件和验证"""

    @pytest.mark.asyncio
    async def test_register_agent_long_name(self, client, db_session):
        long_name = "A" * 100
        payload = {"name": long_name, "agent_type": "opencode"}
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 200
        assert response.json()["data"]["agent"]["name"] == long_name

    @pytest.mark.asyncio
    async def test_register_agent_name_too_long(self, client, db_session):
        payload = {"name": "A" * 101, "agent_type": "opencode"}
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_agent_config_empty_object(self, client, db_session):
        payload = {"name": "EmptyConfig-Agent", "agent_type": "opencode", "config": {}}
        response = await client.post("/api/agents/register", json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_register_agent_with_capabilities_in_config(self, client, db_session):
        payload = {
            "name": "Capable-Agent",
            "agent_type": "opencode",
            "config": {
                "capabilities": ["coding", "refactoring", "debugging", "code_review"],
                "max_concurrent_tasks": 5,
                "current_load": 0,
            },
        }
        response = await client.post("/api/agents/register", json=payload)
        data = response.json()
        assert data["data"]["agent"]["config"]["capabilities"] == [
            "coding", "refactoring", "debugging", "code_review",
        ]
        assert data["data"]["agent"]["config"]["max_concurrent_tasks"] == 5
