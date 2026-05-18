#!/usr/bin/env python3
"""Alembic 环境配置"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.database import Base
from app.models import *  # noqa: F401, F403

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 允许通过环境变量 DATABASE_URL 覆盖 sqlalchemy.url
# Alembic 使用同步连接，需将 asyncpg 驱动替换为 psycopg2
db_url = os.getenv("DATABASE_URL")
if db_url:
    sync_url = db_url.replace("+asyncpg", "+psycopg2").replace("asyncpg://", "psycopg2://")
    config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
