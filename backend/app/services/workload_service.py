#!/usr/bin/env python3
"""负载服务 - 负载分析、自动分配"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta


class WorkloadService:
    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def _import_models(self):
        from app.models.task import Task
        from app.models.board import Board
        from app.models.user import User
        from app.models.agent import Agent
        return Task, Board, User, Agent

    def get_workload(self, project_id: str, user_id: str = None) -> dict:
        Task, Board, User, Agent = self._import_models()
        query = self.db.query(Task).filter(Task.project_id == project_id)
        if user_id:
            query = query.filter(Task.assignee_agent_id == user_id)
        tasks = query.all()
        user_tasks = {}
        for task in tasks:
            uid = task.assignee_agent_id or "unassigned"
            if uid not in user_tasks:
                user_tasks[uid] = {"pending": 0, "assigned": 0, "running": 0, "delivered": 0, "accepted": 0, "total": 0}
            status_key = task.status if task.status in user_tasks[uid] else "pending"
            user_tasks[uid][status_key] = user_tasks[uid].get(status_key, 0) + 1
            user_tasks[uid]["total"] += 1
        member_list = []
        for uid, counts in user_tasks.items():
            total = counts["total"]
            if total <= 2:
                status, color = "idle", "green"
            elif total <= 5:
                status, color = "normal", "yellow"
            else:
                status, color = "busy", "red"
            member = {"user_id": uid, "task_count": total, "status": status, "color": color, "has_alert": False}
            if total > 5:
                member["has_alert"] = True
                member["alert_level"] = "yellow" if total <= 10 else "red"
            member["task_breakdown"] = {k: v for k, v in counts.items() if k != "total"}
            if uid != "unassigned":
                agent = self.db.query(Agent).filter(Agent.id == uid).first()
                if agent:
                    member["name"] = agent.name
                    member["agent_type"] = agent.agent_type
            else:
                member["name"] = "未分配"
            member_list.append(member)
        total_tasks = len(tasks)
        total_members = len([m for m in member_list if m["user_id"] != "unassigned"])
        avg_load = total_tasks / max(total_members, 1)
        status_dist = {"idle": 0, "normal": 0, "busy": 0, "overloaded": 0}
        for m in member_list:
            s = m["status"]
            if s in status_dist:
                status_dist[s] += 1
            else:
                status_dist["overloaded"] += 1
        return {
            "members": member_list,
            "team": {
                "total_members": total_members,
                "total_tasks": total_tasks,
                "avg_load": round(avg_load, 2),
                "status_distribution": status_dist,
            }
        }

    def auto_assign_task(self, task_id: str) -> dict:
        Task, Board, User, Agent = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        all_agents = self.db.query(Agent).filter(Agent.status == "online").all()
        min_load = float("inf")
        best_agent = None
        for agent in all_agents:
            count = self.db.query(Task).filter(
                Task.assignee_agent_id == agent.id,
                Task.status.in_(["pending", "assigned", "running"])
            ).count()
            if count < min_load:
                min_load = count
                best_agent = agent
        if best_agent:
            task.assignee_agent_id = best_agent.id
            task.status = "assigned"
            self.db.commit()
            self.db.refresh(task)
            return {"task_id": task.id, "assigned_to": best_agent.id}
        raise ValueError("没有可用Agent")

    def _task_to_dict(self, task):
        return {
            "id": task.id,
            "name": task.name,
            "project_id": task.project_id,
            "status": task.status,
            "priority": task.priority,
            "assignee_agent_id": task.assignee_agent_id,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
