#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 数据库配置
Async SQLAlchemy (SQLAlchemy 2.0 风格) + 同步兼容层。

生产环境使用 PostgreSQL + asyncpg:
    DATABASE_URL=postgresql://postgres:password@localhost:5432/devflow

同步兼容层同样使用 PostgreSQL（与异步引擎保持一致）。
"""

import os
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from app.config import settings


def _make_async_url(url: str) -> str:
    """将同步数据库 URL 转换为异步驱动 URL。"""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


# ── 异步引擎 (PostgreSQL + asyncpg) ─────────────
engine = create_async_engine(
    _make_async_url(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

# ── 同步引擎 (仅测试 / 迁移脚本使用) ─────────────────────
# 同步引擎同样使用 PostgreSQL，与异步引擎保持一致
_sync_url = settings.DATABASE_URL
if "+asyncpg" in _sync_url:
    _sync_url = _sync_url.replace("+asyncpg", "")
if "+aiosqlite" in _sync_url:
    _sync_url = _sync_url.replace("+aiosqlite", "")

sync_engine = create_engine(
    _sync_url,
    pool_pre_ping=True,
)
sync_session_maker = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

SessionLocal = sync_session_maker

# ── SQLAlchemy Base ─────────────────────────────────────
Base = declarative_base()

# ── 异步 Session 工厂 (用于异步路由) ──────────────────────
async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """异步依赖注入: 获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── 同步 Session 工厂 (向后兼容) ─────────────────────────
def get_db() -> Session:
    """同步依赖注入: 获取数据库会话 (向后兼容)"""
    db = sync_session_maker()
    try:
        yield db
    finally:
        db.close()
