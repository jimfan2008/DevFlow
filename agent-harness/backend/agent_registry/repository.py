from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from backend.agent_registry.db import CREATE_AGENTS_TABLE, CREATE_HEARTBEATS_TABLE
from backend.agent_registry.models import AgentCard, AgentStatus, HealthStatus


class RegistryRepository:
    def __init__(self, db_url: str):
        self._db_url = db_url
        self._conn: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        path = self._db_url.replace("sqlite+aiosqlite:///", "")
        self._conn = await aiosqlite.connect(path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute(CREATE_AGENTS_TABLE)
        await self._conn.execute(CREATE_HEARTBEATS_TABLE)
        await self._conn.commit()

    async def register(self, card: AgentCard) -> AgentCard:
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """INSERT OR REPLACE INTO agents
               (agent_id, name, version, description, capabilities,
                auth_spiffe_id, endpoints, status, metadata, registered_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card.agent_id,
                card.name,
                card.version,
                card.description,
                json.dumps(card.capabilities),
                card.auth_spiffe_id,
                json.dumps(card.endpoints),
                card.status.value,
                json.dumps(card.metadata),
                card.registered_at.isoformat(),
                now,
            ),
        )
        await self._conn.commit()
        card.updated_at = datetime.fromisoformat(now)
        return card

    async def get(self, agent_id: str) -> Optional[AgentCard]:
        cursor = await self._conn.execute(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        )
        row = await cursor.fetchone()
        return self._row_to_card(row) if row else None

    async def list(self, status: Optional[AgentStatus] = None) -> list[AgentCard]:
        if status:
            cursor = await self._conn.execute(
                "SELECT * FROM agents WHERE status = ?", (status.value,)
            )
        else:
            cursor = await self._conn.execute("SELECT * FROM agents")
        rows = await cursor.fetchall()
        return [self._row_to_card(r) for r in rows]

    async def update_status(self, agent_id: str, status: AgentStatus) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._conn.execute(
            "UPDATE agents SET status = ?, updated_at = ? WHERE agent_id = ?",
            (status.value, now, agent_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def delete(self, agent_id: str) -> bool:
        cursor = await self._conn.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        await self._conn.execute("DELETE FROM heartbeats WHERE agent_id = ?", (agent_id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    async def record_heartbeat(self, hs: HealthStatus) -> None:
        await self._conn.execute(
            """INSERT INTO heartbeats (agent_id, status, last_heartbeat, message, metrics)
               VALUES (?, ?, ?, ?, ?)""",
            (
                hs.agent_id,
                hs.status.value,
                hs.last_heartbeat,
                hs.message,
                json.dumps(hs.metrics),
            ),
        )
        await self._conn.commit()

    async def get_health_history(self, agent_id: str, limit: int = 20) -> list[HealthStatus]:
        cursor = await self._conn.execute(
            """SELECT * FROM heartbeats WHERE agent_id = ?
               ORDER BY id DESC LIMIT ?""",
            (agent_id, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_health(r) for r in rows]

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _row_to_card(self, row) -> AgentCard:
        return AgentCard(
            agent_id=row["agent_id"],
            name=row["name"],
            version=row["version"],
            description=row["description"],
            capabilities=json.loads(row["capabilities"]),
            auth_spiffe_id=row["auth_spiffe_id"],
            endpoints=json.loads(row["endpoints"]),
            status=AgentStatus(row["status"]),
            metadata=json.loads(row["metadata"]),
            registered_at=datetime.fromisoformat(row["registered_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_health(self, row) -> HealthStatus:
        return HealthStatus(
            agent_id=row["agent_id"],
            status=AgentStatus(row["status"]),
            last_heartbeat=row["last_heartbeat"],
            message=row["message"],
            metrics=json.loads(row["metrics"]),
        )
