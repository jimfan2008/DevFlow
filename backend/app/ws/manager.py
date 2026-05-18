# WebSocket 连接管理器
from fastapi import WebSocket
from typing import Optional


class WebSocketManager:
    """管理所有 WebSocket 连接，支持按 board/user 维度操作。"""

    def __init__(self):
        self._board_connections: dict[str, set[WebSocket]] = {}
        self._user_connections: dict[str, set[WebSocket]] = {}

    def connect_board(self, board_id: str, ws: WebSocket):
        if board_id not in self._board_connections:
            self._board_connections[board_id] = set()
        self._board_connections[board_id].add(ws)

    def connect_user(self, user_id: str, ws: WebSocket):
        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(ws)

    def disconnect_board(self, board_id: str, ws: WebSocket):
        self._board_connections.get(board_id, set()).discard(ws)
        if board_id in self._board_connections and not self._board_connections[board_id]:
            del self._board_connections[board_id]

    def disconnect_user(self, user_id: str, ws: WebSocket):
        self._user_connections.get(user_id, set()).discard(ws)
        if user_id in self._user_connections and not self._user_connections[user_id]:
            del self._user_connections[user_id]

    async def broadcast_to_board(self, board_id: str, message: dict):
        for ws in list(self._board_connections.get(board_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                self._board_connections[board_id].discard(ws)

    async def broadcast_to_user(self, user_id: str, message: dict):
        for ws in list(self._user_connections.get(user_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                self._user_connections[user_id].discard(ws)

    async def broadcast_all(self, message: dict):
        for board_id in list(self._board_connections.keys()):
            await self.broadcast_to_board(board_id, message)

    @property
    def board_count(self) -> int:
        return len(self._board_connections)

    @property
    def active_connections(self) -> int:
        total = sum(len(ws_set) for ws_set in self._board_connections.values())
        total += sum(len(ws_set) for ws_set in self._user_connections.values())
        return total