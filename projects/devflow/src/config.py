#!/usr/bin/env python3
"""
DevFlow 子项目配置管理
继承主项目 Settings，添加子项目特有配置。
"""

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class SubProjectSettings(BaseSettings):
    """子项目配置"""

    PROJECT_NAME: str = "devflow"
    PROJECT_SLUG: str = "devflow"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = True

    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://devflow_user:devflow_password@localhost:5432/devflow_db",
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    PROJECTS_BASE_DIR: str = os.getenv(
        "PROJECTS_BASE_DIR",
        os.path.join(os.path.expanduser("~"), "DevFlow", "projects"),
    )
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/devflow_uploads")

    HERMES_API_BASE: str = os.getenv("HERMES_API_BASE", "http://localhost:8642/v1")
    HERMES_API_KEY: str = os.getenv("HERMES_API_KEY", "")
    HERMES_PROFILES_PATH: str = os.getenv("HERMES_PROFILES_PATH", os.path.expanduser("~/.hermes"))

    SWARM_MAX_CONCURRENCY: int = int(os.getenv("SWARM_MAX_CONCURRENCY", "12"))
    SWARM_WRITER_TIMEOUT: int = int(os.getenv("SWARM_WRITER_TIMEOUT", "600"))
    SWARM_TESTER_TIMEOUT: int = int(os.getenv("SWARM_TESTER_TIMEOUT", "300"))
    SWARM_MAX_RETRIES: int = int(os.getenv("SWARM_MAX_RETRIES", "5"))

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_sub_project_settings() -> SubProjectSettings:
    return SubProjectSettings()


settings = get_sub_project_settings()
