#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 速率限制中间件
使用慢限 (slowapi) 实现请求限流。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.config import settings

# ── 限流器 ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


def get_rate_limit() -> str:
    """根据环境返回限流策略"""
    if settings.DEBUG:
        return "100/minute"
    return "30/minute"


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> None:
    from fastapi import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "code": 429,
            "message": "请求过于频繁，请稍后重试",
            "data": None,
        },
    )


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
