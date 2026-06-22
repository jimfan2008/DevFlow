import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator


@asynccontextmanager
async def get_connection(db_url: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    path = db_url.replace("sqlite+aiosqlite:///", "")
    async with aiosqlite.connect(path) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn


CREATE_AGENTS_TABLE = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    capabilities TEXT NOT NULL DEFAULT '[]',
    auth_spiffe_id TEXT,
    endpoints TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'inactive',
    metadata TEXT NOT NULL DEFAULT '{}',
    registered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

CREATE_HEARTBEATS_TABLE = """
CREATE TABLE IF NOT EXISTS heartbeats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    last_heartbeat TEXT NOT NULL,
    message TEXT,
    metrics TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
)
"""
