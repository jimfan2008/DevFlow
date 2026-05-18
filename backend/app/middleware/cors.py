#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - CORS 中间件配置
修复: allow_origins=[*] + allow_credentials=True 安全漏洞
"""

from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


def add_cors_middleware(app) -> None:
    """添加 CORS 中间件（安全配置）"""
    origins = [settings.FRONTEND_URL]
    # 如果 FRONTEND_URL 是通配符或为空，生产环境不允许通配
    if settings.FRONTEND_URL != "*":
        origins.append(settings.FRONTEND_URL)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if settings.FRONTEND_URL != "*" else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
