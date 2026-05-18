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
        return Task, Board, User

    def get_workload(self, board_id: str, user_id: str = None) -> dict:
        Task, Board, User = self._import_models()
        board = self.db.query(Board).filter(Board.id == board_id).first()
        if not board:
            raise ValueError("看板不存在")
        query = self.db.query(Task).filter(Task.board_id == board_id)
        if user_id:
            query = query.filter(Task.assignee_id == user_id)
        tasks = query.all()
        # Group by assignee
        user_tasks = {}
        for task in tasks:
            uid = task.assignee_id or "unassigned"
            if uid not in user_tasks:
                user_tasks[uid] = {"todo": 0, "in_progress": 0, "review": 0, "done": 0, "total": 0}
            user_tasks[uid][task.status] = user_tasks[uid].get(task.status, 0) + 1
            user_tasks[uid]["total"] += 1
        # Build member list
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
            # Get user details
            if uid != "unassigned":
                user = self.db.query(User).filter(User.id == uid).first()
                if user:
                    member["username"] = user.username
                    member["email"] = user.email
                    member["full_name"] = user.full_name
            else:
                member["username"] = "未分配"
                member["email"] = ""
                member["full_name"] = None
            member_list.append(member)
        # Team stats
        total_tasks = len(tasks)
        total_members = len([m for m in member_list if m["user_id"] != "unassigned"])
        avg_load = total_tasks / max(total_members, 1)
        status_dist = {"idle": 0, "normal": 0, "busy": 0, "overloaded": 0}
        for m in member_list:
            s = m["status"]
            if s == "idle":
                status_dist["idle"] += 1
            elif s == "normal":
                status_dist["normal"] += 1
            elif s == "busy":
                status_dist["busy"] += 1
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
        Task, Board, User = self._import_models()
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("任务不存在")
        # Find members with lowest load
        all_users = self.db.query(User).filter(User.is_active == True).all()
        min_load = float("inf")
        best_user = None
        for user in all_users:
            count = self.db.query(Task).filter(
                Task.assignee_id == user.id,
                Task.status != "done"
            ).count()
            if count < min_load:
                min_load = count
                best_user = user
        if best_user:
            task.assignee_id = best_user.id
            self.db.commit()
            self.db.refresh(task)
            return {"task": self._task_to_dict(task), "assigned_to": best_user.id}
        raise ValueError("没有可用成员")

    def _task_to_dict(self, task):
        return {
            "id": task.id,
            "title": task.title,
            "board_id": task.board_id,
            "status": task.status,
            "priority": task.priority,
            "assignee_id": task.assignee_id,
            "creator_id": task.creator_id,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
