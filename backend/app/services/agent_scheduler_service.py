# Agent 调度服务 - 编程 Agent 注册、状态管理、任务分配
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.models.task_execution import TaskExecution
from app.models.task import Task

logger = logging.getLogger("devflow.scheduler")


class AgentSchedulerService:
    def __init__(self, db: Session):
        self.db = db

    def register_agent(self, name: str, agent_type: str, api_endpoint: Optional[str] = None, config: Optional[dict] = None) -> Agent:
        """注册一个新的编程 Agent。"""
        agent = Agent(
            id=str(uuid.uuid4()),
            name=name,
            agent_type=agent_type,
            status="offline",
            api_endpoint=api_endpoint,
            config=config or {},
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def get_available_agents(self, agent_type: Optional[str] = None) -> list[Agent]:
        """获取当前在线且有负载能力的 Agent。"""
        query = self.db.query(Agent).filter(Agent.status == "online")
        if agent_type:
            query = query.filter(Agent.agent_type == agent_type)
        return query.all()

    def assign_task(self, task_id: str, agent_id: str) -> TaskExecution:
        """分配任务给指定的编程 Agent。"""
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        if agent.status == "offline":
            raise ValueError(f"Agent {agent.name} is offline")

        execution = TaskExecution(
            id=str(uuid.uuid4()),
            task_id=task_id,
            agent_id=agent_id,
            status="pending",
        )

        agent.status = "busy"
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def auto_assign(self, task_id: str) -> Optional[TaskExecution]:
        """根据任务类型自动匹配可用的编程 Agent。"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        agent_type = self._match_agent_type(task)
        agents = self.get_available_agents(agent_type)

        if not agents:
            agents = self.get_available_agents()
        if not agents:
            logger.warning("No available agents for task %s", task_id)
            return None

        agent = agents[0]
        return self.assign_task(task_id, agent.id)

    def _match_agent_type(self, task: Task) -> str:
        """根据任务类型匹配 Agent 类型。"""
        if task.acceptance_criteria and "test" in (task.acceptance_criteria or "").lower():
            return "claude_code"
        if task.description and "deploy" in (task.description or "").lower():
            return "cursor"
        if task.description and "frontend" in (task.description or "").lower():
            return "cursor"
        return "opencode"

    def complete_execution(self, execution_id: str, result: dict) -> TaskExecution:
        """标记任务执行为已交付。"""
        execution = self.db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.status = "delivered"
        execution.result_summary = result
        execution.delivered_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(execution)
        return execution

    def get_agent_load(self, agent_id: str) -> dict:
        """查询 Agent 负载信息。"""
        active = self.db.query(TaskExecution).filter(
            TaskExecution.agent_id == agent_id,
            TaskExecution.status.in_(["pending", "running"]),
        ).count()

        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        return {
            "agent_id": agent_id,
            "agent_name": agent.name if agent else "unknown",
            "active_tasks": active,
            "status": agent.status if agent else "unknown",
            "available": agent.status == "online" and active < 3 if agent else False,
        }