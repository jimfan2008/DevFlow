import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.models.task import Task
from app.models.agent_execution_log import AgentExecutionLog
from app.services.skill_crud import (
    get_skill_by_type,
    ensure_four_skills,
    update_skill,
    update_skill_connection_status,
    update_skill_execution,
    get_skill_execution_history,
)
from app.services.gateway_client import GatewayClient
from app.core.exceptions import SkillNoAgentError, SkillConnectError, SkillOverloadedError

logger = logging.getLogger("devflow.skill_scheduler")

SKILL_TYPES = ["discover_agent", "connect_agent", "assign_task", "receive_message"]
CODING_AGENT_TYPES = ["trae", "codearts", "opencode", "cursor", "claude_code", "codebuddy", "lingma"]
TASK_SKILL_MAP = {
    "requirement_analysis": "discover_agent",
    "tech_design": "connect_agent",
    "coding": "assign_task",
    "unit_test": "assign_task",
    "integration_test": "assign_task",
    "code_review": "assign_task",
    "deployment": "assign_task",
    "bug_fix": "assign_task",
    "documentation": "assign_task",
}
MAX_LOAD_THRESHOLD = 80
MAX_RECONNECT_ATTEMPTS = 3


class SkillSchedulerService:
    def __init__(self, db: Session):
        self.db = db

    def _get_hermes_agents(self) -> List[Agent]:
        return self.db.query(Agent).filter(Agent.agent_type == "hermes").all()

    def _get_online_hermes_agent(self) -> Optional[Agent]:
        return self.db.query(Agent).filter(
            Agent.agent_type == "hermes",
            Agent.status == "online",
        ).first()

    def _get_coding_agents(self, online_only: bool = True) -> List[Agent]:
        query = self.db.query(Agent).filter(Agent.agent_type.in_(CODING_AGENT_TYPES))
        if online_only:
            query = query.filter(Agent.status.in_(["online", "busy"]))
        return query.all()

    async def discover_coding_agents(self, hermes_agent_id: str = None) -> Dict[str, Any]:
        if hermes_agent_id:
            hermes_agent = self.db.query(Agent).filter(Agent.id == hermes_agent_id).first()
        else:
            hermes_agent = self._get_online_hermes_agent()

        if not hermes_agent:
            raise SkillNoAgentError()

        skill = get_skill_by_type(self.db, hermes_agent.id, "discover_agent")
        if not skill:
            ensure_four_skills(self.db, hermes_agent.id)
            self.db.flush()
            skill = get_skill_by_type(self.db, hermes_agent.id, "discover_agent")

        try:
            config = hermes_agent.config or {}
            port = config.get("gateway_port")
            api_key = config.get("api_key")

            if port:
                client = GatewayClient(port=port)
                client._api_key = api_key
                prompt = "请扫描并列出所有可用的编程Agent，包括它们的名称、类型和当前状态。"
                messages = [{"role": "user", "content": prompt}]

                try:
                    response = await client.send_message_non_stream(prompt)
                    discovered_agents = self._parse_discovery_response(response)
                except Exception as e:
                    logger.warning(f"Gateway discover failed, using DB scan: {e}")
                    discovered_agents = self._scan_coding_agents_from_db()

                for agent_info in discovered_agents:
                    self._sync_discovered_agent(agent_info, hermes_agent.id)

            update_skill_execution(self.db, skill.id, stats={"last_discover": datetime.now(timezone.utc).isoformat()})
            self.db.commit()

            return {
                "hermes_agent_id": hermes_agent.id,
                "discovered_count": len(discovered_agents) if 'discovered_agents' in dir() else 0,
                "status": "success",
            }
        except SkillNoAgentError:
            raise
        except Exception as e:
            logger.error(f"Discover coding agents failed: {e}")
            return {"status": "error", "error": str(e)}

    def _scan_coding_agents_from_db(self) -> List[Dict[str, Any]]:
        agents = self._get_coding_agents(online_only=False)
        return [
            {
                "name": a.name,
                "agent_type": a.agent_type,
                "status": a.status,
                "api_endpoint": a.api_endpoint,
            }
            for a in agents
        ]

    def _parse_discovery_response(self, response: str) -> List[Dict[str, Any]]:
        try:
            result = json.loads(response)
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "agents" in result:
                return result["agents"]
        except json.JSONDecodeError:
            pass
        return []

    def _sync_discovered_agent(self, agent_info: Dict[str, Any], hermes_agent_id: str) -> Optional[Agent]:
        name = agent_info.get("name")
        agent_type = agent_info.get("agent_type", "trae")
        if not name:
            return None

        existing = self.db.query(Agent).filter(Agent.name == name).first()
        if existing:
            existing.status = agent_info.get("status", existing.status)
            existing.discovered_by = "skill_discover"
            existing.hermes_agent_id = hermes_agent_id
            return existing
        else:
            agent = Agent(
                name=name,
                agent_type=agent_type,
                status=agent_info.get("status", "offline"),
                api_endpoint=agent_info.get("api_endpoint"),
                discovered_by="skill_discover",
                hermes_agent_id=hermes_agent_id,
            )
            self.db.add(agent)
            self.db.flush()
            return agent

    async def connect_coding_agent(
        self,
        hermes_agent_id: str,
        coding_agent_id: str,
    ) -> Dict[str, Any]:
        hermes_agent = self.db.query(Agent).filter(Agent.id == hermes_agent_id).first()
        if not hermes_agent:
            raise SkillConnectError("Hermes agent not found")

        coding_agent = self.db.query(Agent).filter(Agent.id == coding_agent_id).first()
        if not coding_agent:
            raise SkillConnectError("Coding agent not found")

        skill = get_skill_by_type(self.db, hermes_agent.id, "connect_agent")
        if not skill:
            ensure_four_skills(self.db, hermes_agent.id)
            self.db.flush()
            skill = get_skill_by_type(self.db, hermes_agent.id, "connect_agent")

        config = hermes_agent.config or {}
        port = config.get("gateway_port")
        api_key = config.get("api_key")

        connected = False
        reconnect_attempts = 0

        if port:
            for attempt in range(MAX_RECONNECT_ATTEMPTS):
                try:
                    client = GatewayClient(port=port)
                    client._api_key = api_key
                    prompt = f"请建立与编程Agent '{coding_agent.name}' (类型: {coding_agent.agent_type}) 的通信通道。"
                    response = await client.send_message_non_stream(prompt)
                    connected = True
                    break
                except Exception as e:
                    reconnect_attempts += 1
                    if attempt < MAX_RECONNECT_ATTEMPTS - 1:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                    logger.warning(f"Connect attempt {attempt + 1} failed: {e}")

        if connected:
            connection_status = "connected"
            skill = update_skill_connection_status(self.db, skill.id, connection_status)
            skill = update_skill(self.db, skill.id, coding_agent_id=coding_agent_id)
            update_skill_execution(self.db, skill.id, stats={"connected_at": datetime.now(timezone.utc).isoformat()})
        else:
            connection_status = "disconnected"
            update_skill_connection_status(self.db, skill.id, connection_status)
            if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                logger.warning(f"Gateway unavailable for agent {hermes_agent_id}, marking as disconnected")

        self.db.commit()

        return {
            "hermes_agent_id": hermes_agent_id,
            "coding_agent_id": coding_agent_id,
            "connection_status": connection_status,
            "reconnect_attempts": reconnect_attempts,
        }

    async def assign_task(
        self,
        hermes_agent_id: str,
        task_id: str,
        coding_agent_id: str = None,
    ) -> Dict[str, Any]:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        hermes_agent = self.db.query(Agent).filter(Agent.id == hermes_agent_id).first()
        if not hermes_agent:
            raise ValueError("Hermes agent not found")

        skill = get_skill_by_type(self.db, hermes_agent.id, "assign_task")
        if not skill:
            ensure_four_skills(self.db, hermes_agent.id)
            self.db.flush()
            skill = get_skill_by_type(self.db, hermes_agent.id, "assign_task")

        if not coding_agent_id:
            coding_agent_id = self._select_best_agent(task, hermes_agent_id)
            if not coding_agent_id:
                raise SkillOverloadedError()

        coding_agent = self.db.query(Agent).filter(Agent.id == coding_agent_id).first()
        if not coding_agent:
            raise ValueError(f"Coding agent {coding_agent_id} not found")

        config = hermes_agent.config or {}
        port = config.get("gateway_port")
        api_key = config.get("api_key")

        assignment_result = {"status": "assigned"}

        if port:
            try:
                client = GatewayClient(port=port)
                client._api_key = api_key
                prompt = (
                    f"请将以下任务分配给编程Agent '{coding_agent.name}' (类型: {coding_agent.agent_type}):\n"
                    f"任务名称: {task.name}\n"
                    f"任务描述: {task.description or 'N/A'}\n"
                    f"优先级: {task.priority}\n"
                    f"验收标准: {task.acceptance_criteria or 'N/A'}"
                )
                response = await client.send_message_non_stream(prompt)
                assignment_result["gateway_response"] = response
            except Exception as e:
                logger.error(f"Gateway assign failed: {e}")
                assignment_result["status"] = "gateway_error"
                assignment_result["error"] = str(e)

        task.status = "assigned"
        task.assignee_agent_id = coding_agent_id
        task.assigned_by_skill_id = skill.id
        task.started_at = datetime.now(timezone.utc)

        skill = update_skill(self.db, skill.id, coding_agent_id=coding_agent_id, task_id=task_id)
        update_skill_execution(self.db, skill.id, stats={"assigned_task": task_id})

        log = AgentExecutionLog(
            task_id=task_id,
            agent_id=coding_agent_id,
            execution_content=f"Task assigned via skill assign_task to {coding_agent.name}",
            via_skill_type="assign_task",
        )
        self.db.add(log)

        self.db.commit()

        return {
            "task_id": task_id,
            "coding_agent_id": coding_agent_id,
            "coding_agent_name": coding_agent.name,
            "status": assignment_result["status"],
            "skill_id": skill.id,
        }

    def _select_best_agent(self, task: Task, hermes_agent_id: str) -> Optional[str]:
        task_type = task.type or ""
        preferred_agent_type = task.agent_type_preference

        matching_skill_type = TASK_SKILL_MAP.get(task_type, "assign_task")
        coding_agents = self._get_coding_agents(online_only=True)

        if not coding_agents:
            return None

        candidates = coding_agents
        if preferred_agent_type:
            type_matched = [a for a in candidates if a.agent_type == preferred_agent_type]
            if type_matched:
                candidates = type_matched

        previous_agent_id = None
        if task.project_id:
            previous_task = self.db.query(Task).filter(
                Task.project_id == task.project_id,
                Task.assignee_agent_id.isnot(None),
                Task.id != task.id,
            ).order_by(Task.updated_at.desc()).first()
            if previous_task:
                previous_agent_id = previous_task.assignee_agent_id

        candidates.sort(key=lambda a: self._get_agent_load(a.id))

        if previous_agent_id and len(candidates) > 1:
            non_previous = [a for a in candidates if a.id != previous_agent_id]
            if non_previous:
                candidates = non_previous

        for candidate in candidates:
            load = self._get_agent_load(candidate.id)
            if load < MAX_LOAD_THRESHOLD:
                return candidate.id

        return None

    def _get_agent_load(self, agent_id: str) -> int:
        running_tasks = self.db.query(Task).filter(
            Task.assignee_agent_id == agent_id,
            Task.status.in_(["assigned", "running"]),
        ).count()
        return running_tasks * 20

    async def handle_skill_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        message_type = message.get("type", "")
        agent_id = message.get("agent_id")
        task_id = message.get("task_id")
        content = message.get("content", {})

        if not message_type or not task_id:
            return {"status": "error", "error": "Missing message type or task_id"}

        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"status": "error", "error": f"Task {task_id} not found"}

        if message_type == "progress":
            progress = content.get("progress", 0)
            progress_message = content.get("message", "")
            task.progress = min(100, max(0, progress))
            task.progress_message = progress_message
            if task.status == "assigned":
                task.status = "running"

            if agent_id:
                log = AgentExecutionLog(
                    task_id=task_id,
                    agent_id=agent_id,
                    execution_content=f"Progress: {progress}% - {progress_message}",
                    via_skill_type="receive_message",
                )
                self.db.add(log)

        elif message_type == "deliver":
            task.status = "delivered"
            task.progress = 100
            task.result_summary = content.get("result_summary", "")
            task.artifacts = content.get("artifacts", {})
            task.test_results = content.get("test_results", {})
            task.completed_at = datetime.now(timezone.utc)

            if agent_id:
                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.status = "online"

            if agent_id:
                log = AgentExecutionLog(
                    task_id=task_id,
                    agent_id=agent_id,
                    execution_content="Task delivered",
                    result=content.get("result_summary", ""),
                    via_skill_type="receive_message",
                )
                self.db.add(log)

        elif message_type == "fail":
            task.status = "failed"
            task.progress_message = content.get("error_message", "Task failed")

            if agent_id:
                log = AgentExecutionLog(
                    task_id=task_id,
                    agent_id=agent_id,
                    execution_content=f"Task failed: {content.get('error_message', '')}",
                    via_skill_type="receive_message",
                )
                self.db.add(log)

        self.db.commit()

        return {
            "status": "processed",
            "task_id": task_id,
            "task_status": task.status,
            "message_type": message_type,
        }

    def get_skill_channel_status(self, hermes_agent_id: str) -> List[Dict[str, Any]]:
        skills = self.db.query(HermesSkill).filter(
            HermesSkill.hermes_agent_id == hermes_agent_id,
        ).all()
        return [
            {
                "skill_id": s.id,
                "skill_type": s.skill_type,
                "connection_status": s.connection_status,
                "coding_agent_id": s.coding_agent_id,
                "task_id": s.task_id,
                "last_executed_at": s.last_executed_at.isoformat() if s.last_executed_at else None,
            }
            for s in skills
        ]

    def get_available_coding_agents(self, hermes_agent_id: str = None) -> List[Dict[str, Any]]:
        agents = self._get_coding_agents(online_only=True)
        result = []
        for agent in agents:
            load = self._get_agent_load(agent.id)
            result.append({
                "id": agent.id,
                "name": agent.name,
                "agent_type": agent.agent_type,
                "status": agent.status,
                "load": load,
                "hermes_agent_id": agent.hermes_agent_id,
            })
        return result

    def get_skill_history(self, skill_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return get_skill_execution_history(self.db, skill_id, limit)
