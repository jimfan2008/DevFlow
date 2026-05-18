#!/usr/bin/env python3
"""
Agent 调度服务 - 负责分配任务给 Agent、监控执行进度、处理依赖联动和超时重试
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
import json

def _import_models():
    from app.models.agent import Agent
    from app.models.task import Task
    from app.models.task_execution import TaskExecution
    from app.models.acceptance_record import AcceptanceRecord
    from app.models.dependency import TaskDependency
    return Agent, Task, TaskExecution, AcceptanceRecord, TaskDependency

class AgentSchedulingService:
    def __init__(self, db: Session):
        self.db = db

    def assign_task(self, task_id: str, agent_type: str) -> Optional['TaskExecution']:
        """
        分配给定类型的可用 Agent 执行任务
        创建 TaskExecution 记录，状态设为 pending
        """
        Agent, Task, TaskExecution, _, _ = _import_models()
        
        # 获取任务
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # 查找可用的 Agent
        agent = self.db.query(Agent).filter(
            and_(
                Agent.agent_type == agent_type,
                Agent.status == "online"
            )
        ).first()
        
        if not agent:
            # 如果没有可用的 Agent，仍然创建执行记录但 agent_id 为 None
            agent_id = None
        else:
            agent_id = agent.id
            # 可选：将 Agent 状态设为 busy
            # agent.status = "busy"
            # self.db.add(agent)
        
        # 创建任务执行记录
        execution = TaskExecution(
            task_id=task_id,
            agent_id=agent_id,
            status="pending"
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        return execution

    def monitor_execution(self, task_id: str) -> Optional['TaskExecution']:
        """
        监控任务执行状态
        返回最新的 TaskExecution 记录
        """
        _, _, TaskExecution, _, _ = _import_models()
        # 获取任务的最新执行记录
        execution = self.db.query(TaskExecution).filter(
            TaskExecution.task_id == task_id
        ).order_by(TaskExecution.created_at.desc()).first()
        return execution

    def update_execution_status(self, execution_id: str, status: str, 
                              execution_log: Optional[str] = None,
                              result_summary: Optional[dict] = None) -> Optional['TaskExecution']:
        """
        更新任务执行状态和相关信息
        """
        _, _, TaskExecution, _, _ = _import_models()
        execution = self.db.query(TaskExecution).filter(
            TaskExecution.id == execution_id
        ).first()
        if execution:
            execution.status = status
            if execution_log is not None:
                execution.execution_log = execution_log
            if result_summary is not None:
                execution.result_summary = result_summary
            if status in ["delivered", "accepted", "rejected"]:
                execution.delivered_at = datetime.now(timezone.utc)
            execution.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(execution)
        return execution

    def retry_failed_task(self, task_id: str) -> Optional['TaskExecution']:
        """
        重试之前失败的任务（状态为 rejected 的执行）
        创建新的执行记录
        """
        Agent, Task, TaskExecution, _, _ = _import_models()
        
        # 获取任务
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # 查看之前的执行记录，如果有 rejected 状态的，则允许重试
        last_execution = self.db.query(TaskExecution).filter(
            and_(
                TaskExecution.task_id == task_id,
                TaskExecution.status == "rejected"
            )
        ).order_by(TaskExecution.created_at.desc()).first()
        
        # 即使没有 rejected 状态，也可以重试？这里我们允许重试任何状态的任务，但最好只在失败时重试
        # 为了简单，我们总是允许创建新的执行记录
        
        # 尝试找到之前使用的 agent_type
        agent_type = None
        if last_execution and last_execution.agent_id:
            agent = self.db.query(Agent).filter(Agent.id == last_execution.agent_id).first()
            if agent:
                agent_type = agent.agent_type
        
        # 如果没有之前的执行，则从任务本身获取推荐的 agent_type
        if not agent_type:
            agent_type = task.agent_type
        
        # 创建新的执行记录
        execution = self.assign_task(task_id, agent_type)
        return execution

    def get_task_progress(self, project_id: str) -> Dict:
        """
        获取项目的整体进度信息
        返回包含各种状态任务数量的字典
        """
        _, Task, _, _, TaskDependency = _import_models()
        
        # 获取项目的所有任务
        tasks = self.db.query(Task).join(Task.board).join(Task.board.project).filter(
            Task.board.project_id == project_id
        ).all()
        
        if not tasks:
            return {
                "total": 0,
                "todo": 0,
                "in_progress": 0,
                "review": 0,
                "done": 0,
                "completed": 0,
                "progress_percent": 0
            }
        
        # 统计各种状态
        status_counts = {
            "todo": 0,
            "in_progress": 0,
            "review": 0,
            "done": 0,
        }
        
        for task in tasks:
            status = task.status
            if status in status_counts:
                status_counts[status] += 1
            # 如果状态是 done，也算作 completed
        
        total = len(tasks)
        completed = status_counts["done"]
        progress_percent = int((completed / total) * 100) if total > 0 else 0
        
        return {
            "total": total,
            "todo": status_counts["todo"],
            "in_progress": status_counts["in_progress"],
            "review": status_counts["review"],
            "done": status_counts["done"],
            "completed": completed,
            "progress_percent": progress_percent
        }

    def check_dependency_readiness(self, task_id: str) -> bool:
        """
        检查任务的所有前置任务是否都已完成（状态为 done）
        如果前置任务都完成，则返回 True，表示可以开始执行此任务
        """
        _, Task, _, _, TaskDependency = _import_models()
        
        # 获取所有指向此任务的依赖（即前置任务）
        dependencies = self.db.query(TaskDependency).filter(
            TaskDependency.target_task_id == task_id
        ).all()
        
        if not dependencies:
            # 没有前置依赖，随时可以开始
            return True
        
        # 检查所有前置任务是否都已完成
        for dep in dependencies:
            source_task = self.db.query(Task).filter(Task.id == dep.source_task_id).first()
            if not source_task or source_task.status != "done":
                return False
        
        return True

    def get_ready_tasks(self, project_id: str) -> List['Task']:
        """
        获取项目中所有前置任务已完成且当前状态为 todo 的任务
        这些任务可以被调度执行
        """
        _, Task, _, _, TaskDependency = _import_models()
        
        # 获取项目的所有任务
        tasks = self.db.query(Task).join(Task.board).join(Task.board.project).filter(
            Task.board.project_id == project_id
        ).all()
        
        ready_tasks = []
        for task in tasks:
            # 只考虑状态为 todo 的任务
            if task.status != "todo":
                continue
            
            # 检查依赖是否都已完成
            if self.check_dependency_readiness(task.id):
                ready_tasks.append(task)
        
        return ready_tasks