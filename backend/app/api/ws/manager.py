import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.group_subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        for group_id in self.group_subscriptions:
            self.group_subscriptions[group_id].discard(client_id)

    def subscribe_to_group(self, client_id: str, group_id: str):
        if group_id not in self.group_subscriptions:
            self.group_subscriptions[group_id] = set()
        self.group_subscriptions[group_id].add(client_id)

    def unsubscribe_from_group(self, client_id: str, group_id: str):
        if group_id in self.group_subscriptions:
            self.group_subscriptions[group_id].discard(client_id)

    async def send_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            ws = self.active_connections[client_id]
            await ws.send_json(message)

    async def broadcast_to_group(self, group_id: str, message: dict):
        if group_id in self.group_subscriptions:
            for client_id in self.group_subscriptions[group_id]:
                await self.send_to_client(client_id, message)


manager = ConnectionManager()
