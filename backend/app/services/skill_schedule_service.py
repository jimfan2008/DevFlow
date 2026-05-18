from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.task import Task
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.models.acceptance_record import AcceptanceRecord
from app.models.enums import TaskStatus, SkillType

logger = logging.getLogger("devflow.skill_schedule")

SKILL_TYPE_ENUMS = [
    SkillType.discover_agent.value,
    SkillType.connect_agent.value,
    SkillType.assign_task.value,
    SkillType.receive_message.value,
    "execute_task",
    "review_result",
    "generate_report",
    "manage_repo",
    "coordinate_meeting",
]

AGENT_TYPE_ENUMS = [
    "hermes", "trae", "codearts", "opencode",
    "cursor", "claude_code", "codebuddy", "lingma",
    "devika",
]

SKILL_AGENT_MATCHING = {
    "requirement_analysis": "hermes",
    "test_case": "claude_code",
    "feature_code": "opencode",
    "unit_test": "claude_code",
    "integration_test": "claude_code",
    "deployment": "cursor",
    "code_review": "codearts",
    "documentation": "trae",
    "refactoring": "codebuddy",
}

AGENT_TYPE_MATCHING = {
    "requirement_analysis": ["hermes", "trae"],
    "test_case": ["claude_code", "codearts"],
    "feature_code": ["opencode", "cursor", "claude_code"],
    "unit_test": ["claude_code", "codearts"],
    "integration_test": ["claude_code", "opencode"],
    "deployment": ["cursor", "codebuddy"],
}


class SkillScheduleService:
    def __init__(self, db: Session):
        self.db = db

    def auto_assign_via_skill(self, task_id: str) -> Optional[Task]:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status != TaskStatus.pending.value:
            raise ValueError(f"Task {task_id} is not pending, current status: {task.status}")

        preferred_type = self._match_skill_to_agent(task.type, task.agent_type_preference)

        hermes_agents = self.db.query(Agent).filter(
            and_(Agent.agent_type == "hermes", Agent.status == "online")
        ).all()

        if not hermes_agents:
            logger.warning("No online Hermes agent available for skill assignment")
            return None

        hermes_agent = self._select_least_loaded(hermes_agents)

        coding_agent = None
        if preferred_type:
            candidates = self.db.query(Agent).filter(
                and_(Agent.agent_type == preferred_type, Agent.status == "online")
            ).all()
            if not candidates:
                candidates = self.db.query(Agent).filter(
                    Agent.status == "online",
                    Agent.agent_type.in_(AGENT_TYPE_MATCHING.get(task.type, [])),
                ).all()
            if candidates:
                coding_agent = self._select_least_loaded(candidates)

        skill = HermesSkill(
            id=str(uuid.uuid4()),
            hermes_agent_id=hermes_agent.id,
            skill_type=SkillType.assign_task.value,
            status="active",
            config={"task_type": task.type, "preferred_agent_type": preferred_type},
            coding_agent_id=coding_agent.id if coding_agent else None,
            task_id=task_id,
            connection_status="connected",
        )
        self.db.add(skill)
        self.db.flush()

        task.assigned_by_skill_id = skill.id
        task.assignee_agent_id = coding_agent.id if coding_agent else None
        task.status = TaskStatus.assigned.value
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"Task {task_id} assigned via skill {skill.id} to agent {coding_agent.id if coding_agent else 'none'}")
        return task

    def _match_skill_to_agent(self, task_type: str, agent_preference: str = None) -> Optional[str]:
        if agent_preference and agent_preference in AGENT_TYPE_ENUMS:
            return agent_preference
        return SKILL_AGENT_MATCHING.get(task_type, "opencode")

    def _select_least_loaded(self, agents: List[Agent]) -> Agent:
        if not agents:
            return None

        load_map = {}
        for agent in agents:
            active_count = self.db.query(Task).filter(
                and_(
                    Task.assignee_agent_id == agent.id,
                    Task.status.in_([TaskStatus.assigned.value, TaskStatus.running.value]),
                )
            ).count()
            load_map[agent.id] = active_count

        return min(agents, key=lambda a: load_map.get(a.id, 0))

    def register_heartbeat(self, agent_id: str, load_level: int = 0,
                           status_detail: dict = None, via_skill: str = None) -> Agent:
        from app.models.agent_heartbeat import AgentHeartbeat

        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        heartbeat = AgentHeartbeat(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            load_level=load_level,
            status_detail=status_detail or {},
            via_skill=via_skill,
        )
        self.db.add(heartbeat)

        agent.last_heartbeat = datetime.now(timezone.utc)
        if load_level >= 90:
            agent.status = "busy"
        elif load_level > 0:
            agent.status = "online"
        else:
            agent.status = "online"
        agent.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(agent)
        return agent

    def check_offline_agents(self, timeout_minutes: int = 5) -> List[Agent]:
        threshold = datetime.now(timezone.utc) - __import__('datetime').timedelta(minutes=timeout_minutes)
        agents = self.db.query(Agent).filter(
            and_(
                Agent.status != "offline",
                Agent.last_heartbeat < threshold,
            )
        ).all()

        for agent in agents:
            agent.status = "offline"
            agent.updated_at = datetime.now(timezone.utc)

        if agents:
            self.db.commit()
        return agents

    def get_skill_matching_rules(self) -> dict:
        return {
            "skill_agent_matching": SKILL_AGENT_MATCHING,
            "agent_type_matching": AGENT_TYPE_MATCHING,
            "skill_types": SKILL_TYPE_ENUMS,
            "agent_types": AGENT_TYPE_ENUMS,
        }
