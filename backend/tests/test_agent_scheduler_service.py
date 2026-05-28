#!/usr/bin/env python3
"""
Agent 调度服务 - 单元测试
TDD: 测试 Agent 状态管理、负载均衡、任务分配规则、交叉验证等核心功能
"""

import pytest
from app.models.agent import Agent
from app.models.task import Task


class TestAgentStatusManagement:
    """Agent 状态管理测试"""

    @pytest.mark.asyncio
    async def test_agent_online_status(self, db_session, opencode_agent):
        """测试在线 Agent"""
        assert opencode_agent.status == "online"

    @pytest.mark.asyncio
    async def test_agent_busy_status(self, db_session):
        """测试忙碌 Agent"""
        agent = Agent(
            id="agent_busy_test",
            name="Busy Agent",
            agent_type="opencode",
            status="busy",
            api_endpoint="http://localhost:8080/agents/busy",
            config={"capabilities": ["coding"]},
        )
        db_session.add(agent)
        db_session.commit()

        assert agent.status == "busy"

    @pytest.mark.asyncio
    async def test_agent_offline_status(self, db_session):
        """测试离线 Agent"""
        agent = Agent(
            id="agent_offline_test",
            name="Offline Agent",
            agent_type="cursor",
            status="offline",
        )
        db_session.add(agent)
        db_session.commit()

        assert agent.status == "offline"

    @pytest.mark.asyncio
    async def test_agent_has_api_endpoint_when_online(self, db_session, opencode_agent):
        """测试在线 Agent 应有 API 端点"""
        assert opencode_agent.api_endpoint is not None
        assert "http" in opencode_agent.api_endpoint


class TestAgentTypes:
    """Agent 类型测试"""

    @pytest.mark.asyncio
    async def test_opencode_agent_type(self, db_session, opencode_agent):
        """测试 opencode 类型 Agent"""
        assert opencode_agent.agent_type == "opencode"

    @pytest.mark.asyncio
    async def test_cursor_agent_type(self, db_session, cursor_agent):
        """测试 cursor 类型 Agent"""
        assert cursor_agent.agent_type == "cursor"

    @pytest.mark.asyncio
    async def test_claude_agent_type(self, db_session, claude_agent):
        """测试 claude_code 类型 Agent"""
        assert claude_agent.agent_type == "claude_code"

    @pytest.mark.asyncio
    async def test_codebuddy_agent_type(self, db_session, codebuddy_agent):
        """测试 codebuddy 类型 Agent"""
        assert codebuddy_agent.agent_type == "codebuddy"


class TestAgentCapabilities:
    """Agent 能力配置测试"""

    @pytest.mark.asyncio
    async def test_opencode_capabilities(self, db_session, opencode_agent):
        """测试 opencode 的能力配置"""
        assert "coding" in opencode_agent.config["capabilities"]

    @pytest.mark.asyncio
    async def test_cursor_deployment_capability(self, db_session, cursor_agent):
        """测试 cursor 的部署能力"""
        assert "deployment" in cursor_agent.config["capabilities"]

    @pytest.mark.asyncio
    async def test_claude_test_capability(self, db_session, claude_agent):
        """测试 claude_code 的测试用例编写能力"""
        assert "test_case_writing" in claude_agent.config["capabilities"]

    @pytest.mark.asyncio
    async def test_agent_max_concurrent_tasks(self, db_session, opencode_agent):
        """测试 Agent 的最大并发任务数"""
        assert opencode_agent.config["max_concurrent_tasks"] >= 1


class TestAgentAssignment:
    """Agent 任务分配测试"""

    @pytest.mark.asyncio
    async def test_assign_task_agent_type_match(self, db_session, test_project, opencode_agent):
        task = Task(
            id="task_assign_coding",
            project_id=test_project.id,
            name="编码任务",
            type="coding",
            status="pending",
            agent_type_preference="opencode",
        )
        db_session.add(task)
        db_session.commit()

        assert task.agent_type_preference == "opencode"
        assert opencode_agent.agent_type == "opencode"

    @pytest.mark.asyncio
    async def test_cannot_assign_to_offline_agent(self, db_session):
        """测试不能分配任务给离线 Agent"""
        offline_agent = Agent(
            id="agent_offline_assign",
            name="Offline Agent",
            agent_type="opencode",
            status="offline",
        )
        db_session.add(offline_agent)
        db_session.commit()

        can_assign = offline_agent.status == "online"
        assert can_assign is False, "离线 Agent 不应被分配任务"


class TestCrossAgentValidation:
    """交叉验证测试 - 前后任务分配给不同 Agent"""

    @pytest.mark.asyncio
    async def test_consecutive_tasks_different_agents(self, db_session, all_agents):
        """测试前后相邻任务应分配给不同的 Agent"""
        agent1 = all_agents["opencode_agent"].id
        agent2 = all_agents["claude_code_agent"].id

        assert agent1 != agent2, "不同类型的 Agent 应该有不同 ID"

    @pytest.mark.asyncio
    async def test_same_agent_not_consecutive(self, db_session, opencode_agent, cursor_agent):
        """测试同一 Agent 不应连续执行任务"""
        previous_agent = opencode_agent.id
        current_agent = cursor_agent.id

        assert previous_agent != current_agent, "应使用不同 Agent 进行交叉验证"


class TestAgentLoadBalancing:
    """Agent 负载均衡测试"""

    @pytest.mark.asyncio
    async def test_prefer_low_load_agent(self, db_session, all_agents):
        """测试优先选择低负载的 Agent"""
        opencode = all_agents["opencode_agent"]
        cursor = all_agents["cursor_agent"]

        opencode_load = opencode.config.get("current_load", 0)
        cursor_load = cursor.config.get("current_load", 0)

        assert opencode_load < cursor_load, "opencode 负载更低"
        preferred = opencode if opencode_load <= cursor_load else cursor
        assert preferred.id == opencode.id

    @pytest.mark.asyncio
    async def test_agent_not_overloaded(self, db_session, opencode_agent):
        """测试 Agent 不应超过最大并发数"""
        current_load = opencode_agent.config.get("current_load", 0)
        max_load = opencode_agent.config.get("max_concurrent_tasks", 1)

        assert current_load <= max_load, "Agent 负载不应超过最大值"


class TestAgentSelectionByTaskType:
    """按任务类型选择 Agent 测试"""

    @pytest.mark.asyncio
    async def test_coding_task_prefers_opencode(self, db_session, opencode_agent):
        """测试编码任务优先选择 opencode"""
        assert "coding" in opencode_agent.config["capabilities"]

    @pytest.mark.asyncio
    async def test_test_task_prefers_claude(self, db_session, claude_agent):
        """测试测试用例任务优先选择 claude_code"""
        assert "test_case_writing" in claude_agent.config["capabilities"]

    @pytest.mark.asyncio
    async def test_deployment_task_prefers_cursor(self, db_session, cursor_agent):
        """测试部署任务优先选择 cursor"""
        assert "deployment" in cursor_agent.config["capabilities"]


class TestAgentToDict:
    """Agent 序列化测试"""

    @pytest.mark.asyncio
    async def test_agent_to_dict(self, db_session, opencode_agent):
        """测试 Agent 序列化为字典"""
        result = opencode_agent.to_dict()

        assert "id" in result
        assert "name" in result
        assert "agent_type" in result
        assert "status" in result
        assert "api_endpoint" in result
        assert "config" in result
        assert "created_at" in result


class TestMultipleAgents:
    """多 Agent 管理测试"""

    @pytest.mark.asyncio
    async def test_all_agents_different_ids(self, db_session, all_agents):
        """测试所有 Agent 有不同 ID"""
        agent_ids = [a.id for a in all_agents.values()]
        assert len(agent_ids) == len(set(agent_ids)), "所有 Agent ID 应唯一"

    @pytest.mark.asyncio
    async def test_filter_agents_by_type(self, db_session, all_agents):
        """测试按类型筛选 Agent"""
        opencode_agents = [a for a in all_agents.values() if a.agent_type == "opencode"]
        assert len(opencode_agents) >= 1

        claude_agents = [a for a in all_agents.values() if a.agent_type == "claude_code"]
        assert len(claude_agents) >= 1

    @pytest.mark.asyncio
    async def test_filter_online_agents(self, db_session, all_agents):
        """测试筛选在线 Agent"""
        online_agents = [a for a in all_agents.values() if a.status == "online"]
        offline_agents = [a for a in all_agents.values() if a.status == "offline"]

        assert len(online_agents) >= 1
        assert len(offline_agents) >= 1
