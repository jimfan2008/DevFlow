#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - JWT 黑名单中间件
使用 Redis 存储已注销的 token，支持 token 撤销。
"""

import redis
from app.config import settings

# ── Redis 客户端 ─────────────────────────────────────────
_redis_client = None


def get_redis_client():
    """获取 Redis 客户端（惰性初始化）"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            _redis_client = None
    return _redis_client


def add_to_blacklist(token: str, expire_seconds: int = None) -> bool:
    """将 token 加入黑名单"""
    client = get_redis_client()
    if client is None:
        return False
    client.setex(token, expire_seconds or 3600, "blacklisted")
    return True


def is_blacklisted(token: str) -> bool:
    """检查 token 是否在黑名单中"""
    client = get_redis_client()
    if client is None:
        return False
    return client.exists(token) > 0


def remove_from_blacklist(token: str) -> bool:
    """从黑名单移除 token"""
    client = get_redis_client()
    if client is None:
        return False
    client.delete(token)
    return True


def blacklist_size() -> int:
    """获取黑名单大小（调试用）"""
    client = get_redis_client()
    if client is None:
        return 0
    return client.dbsize()


class JWTBlacklistMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
