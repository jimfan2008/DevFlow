#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 配置管理
基于 pydantic-settings，支持环境变量与默认值。
"""

import os
from functools import lru_cache
from typing import Optional, List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置 (合并自 legacy app/config.py)"""

    # ── 应用 ──────────────────────────────────────────────
    APP_NAME: str = "DevFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True  # 兼容旧版 env var

    # 从环境变量读取，开发环境 fallback 安全默认值
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "devflow-secret-key-change-in-production",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # ── JWT (兼容旧版命名) ──────────────────────────────
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

    # ── CORS ──────────────────────────────────────────────
    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL", "http://localhost:5173"
    )

    # ── 数据库 ────────────────────────────────────────────
    # 生产环境: DATABASE_URL 指向 PostgreSQL
    # 开发环境: 也可通过环境变量覆盖为 SQLite
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://devflow_user:devflow_password@localhost:5432/devflow_db",
    )
    SQLITE_DATABASE_URL: str = "sqlite+aiosqlite:///./devflow.db"

    # ── 连接池 (兼容旧版) ─────────────────────────────────
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )

    # ── Hermes Agent ──────────────────────────────────────
    HERMES_API_BASE: str = os.getenv(
        "HERMES_API_BASE", "http://host.docker.internal:8642/v1"
    )
    HERMES_API_KEY: str = os.getenv("HERMES_API_KEY", "")
    HERMES_MODEL: str = os.getenv("HERMES_MODEL", "hermes-agent")
    HERMES_PROFILES_PATH: str = os.getenv(
        "HERMES_PROFILES_PATH", os.path.expanduser("~/.hermes")
    )
    HERMES_BFF_URL: str = os.getenv("HERMES_BFF_URL", "")
    HERMES_HEALTH_INTERVAL: int = int(os.getenv("HERMES_HEALTH_INTERVAL", "30"))
    HERMES_MAX_CONCURRENT_CHATS: int = int(os.getenv("HERMES_MAX_CONCURRENT_CHATS", "5"))
    HERMES_SHOW_THINKING: bool = os.getenv("HERMES_SHOW_THINKING", "false").lower() in ("true", "1", "yes")

    # ── Celery ─────────────────────────────────────────────
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL", "redis://localhost:6379/1"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
    )
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]

    # ── Gitea ──────────────────────────────────────────────
    GITEA_URL: str = os.getenv("GITEA_URL", "http://gitea:3000")
    GITEA_API_TOKEN: str = os.getenv("GITEA_API_TOKEN", "")
    GITEA_ADMIN_USER: str = os.getenv("GITEA_ADMIN_USER", "devflow")
    GITEA_ADMIN_PASSWORD: str = os.getenv("GITEA_ADMIN_PASSWORD", "")
    GITEA_DB_HOST: str = os.getenv("GITEA_DB_HOST", "gitea-db")
    GITEA_DB_PORT: int = int(os.getenv("GITEA_DB_PORT", "5432"))
    GITEA_DB_NAME: str = os.getenv("GITEA_DB_NAME", "gitea")
    GITEA_DB_USER: str = os.getenv("GITEA_DB_USER", "gitea")
    GITEA_DB_PASSWORD: str = os.getenv("GITEA_DB_PASSWORD", "gitea_password")

    # ── 项目存储 ───────────────────────────────────────────
    PROJECTS_BASE_DIR: str = os.getenv(
        "PROJECTS_BASE_DIR",
        "/home/jim/projects",
    )

    # ── 项目存储（重复定义，同时修改）──
    PROJECTS_BASE_DIR: str = os.getenv(
        "PROJECTS_BASE_DIR",
        "/home/jim/projects",
    )

    # ── 文件上传 ──────────────────────────────────────────
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/attachments")
    MAX_UPLOAD_SIZE_MB: int = int(
        os.getenv("MAX_UPLOAD_SIZE_MB", "10")
    )
    ALLOWED_EXTENSIONS: List[str] = [
        ext.strip()
        for ext in os.getenv(
            "ALLOWED_EXTENSIONS",
            ".pdf,.doc,.docx,.txt,.csv,.png,.jpg,.jpeg,.gif,.zip",
        ).split(",")
    ]

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    """获取单例配置"""
    return Settings()


settings = get_settings()  # 模块级单例，方便 utils/security.py 等直接引用
