"""v4.0 - Agent 蜂群管理服务"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


SUPPORTED_SWARM_AGENTS = [
    "claude_code", "codex", "opencode", "cursor",
    "codearts", "trae", "lingma", "hermes_sub_agent",
    "pi_coding_agent", "reasonix",
]

WRITER_AGENT_TYPES = [
    "pi_coding_agent", "opencode", "claude_code", "cursor",
    "lingma", "codearts", "trae", "codebuddy", "reasonix",
]

TESTER_AGENT_TYPES = [
    "reasonix", "claude_code", "codex", "devika", "hermes",
]

WRITER_PREFERENCE = ["pi_coding_agent", "opencode"]
TESTER_PREFERENCE = ["reasonix", "claude_code"]

MANAGER_PURPOSE_MAP = {
    "houfa": "code_writing",
    "houda": "test_execution",
}


class SwarmService:
    def __init__(self):
        self._swarms: Dict[int, Dict[str, Any]] = {}
        self._next_swarm_id = 1
        self._assignments: Dict[int, List[Dict[str, Any]]] = {}

    def create_swarm(self, project_id: str, name: str, purpose: str,
                     step_number: int, manager_role: str) -> Dict[str, Any]:
        expected_purpose = MANAGER_PURPOSE_MAP.get(manager_role)
        if expected_purpose is None:
            raise ValueError(f"无效的管理者角色: {manager_role}")
        if manager_role == "houfa" and purpose != "code_writing":
            raise ValueError("后发只能建立代码编写蜂群")
        if manager_role == "houda" and purpose != "test_execution":
            raise ValueError("后达只能建立测试蜂群")

        swarm = {
            "id": self._next_swarm_id,
            "project_id": project_id,
            "name": name,
            "purpose": purpose,
            "step_number": step_number,
            "manager_role": manager_role,
            "members": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "disbanded_at": None,
        }
        self._swarms[self._next_swarm_id] = swarm
        self._assignments[self._next_swarm_id] = []
        self._next_swarm_id += 1
        return dict(swarm)

    def add_member(self, swarm_id: int, agent_type: str, agent_id: str) -> Dict[str, Any]:
        if agent_type not in SUPPORTED_SWARM_AGENTS:
            raise ValueError(f"不支持的Agent类型: {agent_type}")

        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        member = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        swarm["members"].append(member)
        return dict(swarm)

    def remove_member(self, swarm_id: int, agent_id: str) -> Dict[str, Any]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        swarm["members"] = [m for m in swarm["members"] if m["agent_id"] != agent_id]
        return dict(swarm)

    def dispatch_tasks(self, swarm_id: int, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        members = swarm["members"]
        if not members:
            raise ValueError("蜂群没有成员，无法分发任务")

        assignments = []
        round_robin_index = 0

        for task in tasks:
            task_deps = task.get("depends_on", [])

            if task_deps:
                dep_assignments = [a for a in assignments if a["task_id"] in task_deps]
                used_agents = {a["assigned_agent_id"] for a in dep_assignments}
                available = [m for m in members if m["agent_id"] not in used_agents]
                if not available:
                    available = members
                chosen = available[round_robin_index % len(available)]
            else:
                chosen = members[round_robin_index % len(members)]

            assignment = {
                "swarm_id": swarm_id,
                "task_id": task["task_id"],
                "task_name": task.get("name", ""),
                "assigned_agent_id": chosen["agent_id"],
                "assigned_agent_type": chosen["agent_type"],
                "status": "assigned",
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            }
            assignments.append(assignment)
            round_robin_index += 1

        self._assignments[swarm_id].extend(assignments)
        return assignments

    def get_progress(self, swarm_id: int) -> Dict[str, Any]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        assignments = self._assignments.get(swarm_id, [])
        total = len(assignments)
        completed = sum(1 for a in assignments if a["status"] == "completed")

        return {
            "swarm_id": swarm_id,
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": total - completed,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
        }

    def disband_swarm(self, swarm_id: int) -> Dict[str, Any]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        swarm["status"] = "disbanded"
        swarm["disbanded_at"] = datetime.now(timezone.utc).isoformat()
        return dict(swarm)

    def get_swarm(self, swarm_id: int) -> Optional[Dict[str, Any]]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            return None
        result = dict(swarm)
        result["assignments"] = self._assignments.get(swarm_id, [])
        return result

    @staticmethod
    def get_online_agents_by_types(db, agent_types: list) -> list:
        from app.models.agent import Agent
        return (
            db.query(Agent)
            .filter(Agent.agent_type.in_(agent_types), Agent.status == "online")
            .all()
        )

    @staticmethod
    def get_online_writer_agents(db) -> list:
        return SwarmService.get_online_agents_by_types(db, WRITER_AGENT_TYPES)

    @staticmethod
    def get_online_tester_agents(db) -> list:
        return SwarmService.get_online_agents_by_types(db, TESTER_AGENT_TYPES)

    @staticmethod
    def get_preferred_writer_agents(db) -> list:
        """获取在线编写Agent，按偏好排序：PI > OpenCode > 其他"""
        agents = SwarmService.get_online_agents_by_types(db, WRITER_AGENT_TYPES)
        def _sort_key(a):
            try:
                return WRITER_PREFERENCE.index(a.agent_type)
            except ValueError:
                return len(WRITER_PREFERENCE)
        agents.sort(key=_sort_key)
        return agents

    @staticmethod
    def get_preferred_tester_agents(db) -> list:
        """获取在线测试Agent，按偏好排序：Reasonix > Claude Code > 其他"""
        agents = SwarmService.get_online_agents_by_types(db, TESTER_AGENT_TYPES)
        def _sort_key(a):
            try:
                return TESTER_PREFERENCE.index(a.agent_type)
            except ValueError:
                return len(TESTER_PREFERENCE)
        agents.sort(key=_sort_key)
        return agents