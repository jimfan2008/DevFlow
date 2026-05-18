# Redis Pub/Sub 桥接 - 生产环境跨进程消息分发
import json
import logging
from typing import Optional, Callable
from app.config import settings

logger = logging.getLogger("devflow.ws.pubsub")


class RedisPubSubBridge:
    """在 Redis Pub/Sub 与本地 WebSocket 管理器之间桥接消息。

    MVP 阶段使用内存通道模拟；生产环境替换为真实 Redis Pub/Sub。
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._redis_available = False

    async def publish(self, channel: str, message: dict):
        """发布消息到频道。"""
        if self._redis_available:
            # 生产环境: await redis.publish(channel, json.dumps(message))
            pass
        # 本地模拟: 直接调用处理器
        await self._dispatch(channel, message)

    async def subscribe(self, channel: str, handler: Callable):
        """订阅频道。"""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    async def _dispatch(self, channel: str, message: dict):
        """分派消息给所有订阅者。"""
        for handler in self._handlers.get(channel, []):
            try:
                await handler(message)
            except Exception as e:
                logger.error("PubSub handler error on %s: %s", channel, e)

    async def connect_redis(self, redis_url: Optional[str] = None):
        """连接到真实的 Redis Pub/Sub (生产环境)。"""
        try:
            import redis.asyncio as aioredis
            url = redis_url or settings.REDIS_URL
            self._redis = await aioredis.from_url(url)
            self._pubsub = self._redis.pubsub()
            self._redis_available = True
            logger.info("Connected to Redis Pub/Sub at %s", url)
        except Exception as e:
            logger.warning("Redis Pub/Sub not available, using local mode: %s", e)
            self._redis_available = False