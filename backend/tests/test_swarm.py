"""v4.0 Swarm Service Tests"""
import pytest
from app.services.swarm_service import SwarmService, SUPPORTED_SWARM_AGENTS


class TestSwarmService:

    def test_supported_swarm_agents_count(self):
        assert len(SUPPORTED_SWARM_AGENTS) == 9

    def test_supported_agents_include_all_types(self):
        expected = {"claude_code", "codex", "opencode", "cursor",
                    "codearts", "trae", "lingma", "hermes_sub_agent", "pi_coding_agent"}
        assert set(SUPPORTED_SWARM_AGENTS) == expected

    def test_create_code_swarm(self):
        service = SwarmService()
        swarm = service.create_swarm(
            project_id="proj-1",
            name="TDD测试用例编写蜂群",
            purpose="code_writing",
            step_number=7,
            manager_role="houfa",
        )
        assert swarm["name"] == "TDD测试用例编写蜂群"
        assert swarm["purpose"] == "code_writing"
        assert swarm["manager_role"] == "houfa"
        assert swarm["step_number"] == 7
        assert swarm["status"] == "active"
        assert len(swarm["members"]) == 0

    def test_create_test_swarm(self):
        service = SwarmService()
        swarm = service.create_swarm(
            project_id="proj-1",
            name="全面测试蜂群",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        assert swarm["purpose"] == "test_execution"
        assert swarm["manager_role"] == "houda"
        assert swarm["step_number"] == 11

    def test_add_swarm_member(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群A", "code_writing", 7, "houfa")
        updated = service.add_member(swarm["id"], agent_type="claude_code", agent_id="cc-1")
        assert len(updated["members"]) == 1
        assert updated["members"][0]["agent_type"] == "claude_code"

    def test_add_multiple_members(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群B", "code_writing", 9, "houfa")
        service.add_member(swarm["id"], agent_type="claude_code", agent_id="cc-1")
        service.add_member(swarm["id"], agent_type="codex", agent_id="cx-1")
        updated = service.add_member(swarm["id"], agent_type="opencode", agent_id="oc-1")
        assert len(updated["members"]) == 3

    def test_remove_swarm_member(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群C", "code_writing", 7, "houfa")
        service.add_member(swarm["id"], agent_type="claude_code", agent_id="cc-1")
        service.add_member(swarm["id"], agent_type="codex", agent_id="cx-1")
        updated = service.remove_member(swarm["id"], agent_id="cc-1")
        assert len(updated["members"]) == 1

    def test_dispatch_tasks_to_members(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群D", "code_writing", 9, "houfa")
        service.add_member(swarm["id"], agent_type="claude_code", agent_id="cc-1")
        service.add_member(swarm["id"], agent_type="codex", agent_id="cx-1")

        tasks = [
            {"task_id": "task-1", "name": "用户模块"},
            {"task_id": "task-2", "name": "订单模块"},
            {"task_id": "task-3", "name": "支付模块"},
            {"task_id": "task-4", "name": "通知模块"},
        ]
        assignments = service.dispatch_tasks(swarm["id"], tasks)
        assert len(assignments) == 4
        assigned_agents = {a["assigned_agent_id"] for a in assignments}
        assert len(assigned_agents) == 2

    def test_dispatch_dependent_tasks_different_agents(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群E", "code_writing", 9, "houfa")
        service.add_member(swarm["id"], agent_type="claude_code", agent_id="cc-1")
        service.add_member(swarm["id"], agent_type="codex", agent_id="cx-1")

        tasks = [
            {"task_id": "task-a", "name": "前置任务A", "depends_on": []},
            {"task_id": "task-b", "name": "后继任务B", "depends_on": ["task-a"]},
        ]
        assignments = service.dispatch_tasks(swarm["id"], tasks)

        a_agent = next(a["assigned_agent_id"] for a in assignments if a["task_id"] == "task-a")
        b_agent = next(a["assigned_agent_id"] for a in assignments if a["task_id"] == "task-b")
        assert a_agent != b_agent

    def test_disband_swarm(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群F", "code_writing", 7, "houfa")
        result = service.disband_swarm(swarm["id"])
        assert result["status"] == "disbanded"
        assert result["disbanded_at"] is not None

    def test_get_swarm_progress_empty(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群G", "code_writing", 7, "houfa")
        progress = service.get_progress(swarm["id"])
        assert progress["total_tasks"] == 0
        assert progress["completed_tasks"] == 0

    def test_invalid_manager_for_purpose(self):
        service = SwarmService()
        with pytest.raises(ValueError, match="只能建立代码编写蜂群"):
            service.create_swarm("proj-1", "test", "test_execution", 11, "houfa")

        with pytest.raises(ValueError, match="只能建立测试蜂群"):
            service.create_swarm("proj-1", "test", "code_writing", 7, "houda")

    def test_invalid_agent_type(self):
        service = SwarmService()
        swarm = service.create_swarm("proj-1", "蜂群H", "code_writing", 7, "houfa")
        with pytest.raises(ValueError, match="不支持的Agent类型"):
            service.add_member(swarm["id"], agent_type="unknown_agent", agent_id="ua-1")