# WebSocket 消息广播器
from typing import Optional
from .manager import WebSocketManager


class MessageBroadcaster:
    """提供高层次的广播方法，封装业务事件类型。"""

    def __init__(self, manager: WebSocketManager):
        self.manager = manager

    async def task_assigned(self, task_id: str, board_id: str, assignee_id: str, title: str):
        """任务被分配给 Agent 时广播 (SRS §6.2: task.assigned)"""
        await self.manager.broadcast_to_board(board_id, {
            "type": "task.assigned",
            "task_id": task_id,
            "assignee_id": assignee_id,
            "title": title,
        })

    async def task_status_changed(self, task_id: str, board_id: str, status: str, user_id: Optional[str] = None):
        """任务状态变更时广播 (SRS §6.2: task.status.changed)"""
        message = {
            "type": "task.status.changed",
            "task_id": task_id,
            "status": status,
        }
        await self.manager.broadcast_to_board(board_id, message)
        if user_id:
            await self.manager.broadcast_to_user(user_id, message)

    async def requirement_updated(self, project_id: str):
        """需求更新时广播 (SRS §6.2: project.requirement.updated)"""
        await self.manager.broadcast_all({
            "type": "project.requirement.updated",
            "project_id": project_id,
        })

    async def acceptance_result(self, task_id: str, board_id: str, result: str, user_id: Optional[str] = None):
        """验收结果推送 (SRS §6.2: acceptance.result)"""
        message = {
            "type": "acceptance.result",
            "task_id": task_id,
            "result": result,
        }
        await self.manager.broadcast_to_board(board_id, message)
        if user_id:
            await self.manager.broadcast_to_user(user_id, message)

    async def project_completed(self, project_id: str, user_id: str):
        """项目完成广播 (SRS §6.2: project.completed)"""
        message = {
            "type": "project.completed",
            "project_id": project_id,
        }
        await self.manager.broadcast_all(message)
        await self.manager.broadcast_to_user(user_id, message)