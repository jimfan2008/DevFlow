#!/usr/bin/env python3
"""
DevFlow Redis 缓存层 - 核心缓存管理器
支持 get/set/delete/clear/exists/ttl 操作
"""

import json
import logging
from typing import Any, Optional, List, Union

from redis import Redis, RedisError
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

from app.config import settings

logger = logging.getLogger("devflow.caches")


class RedisCacheManager:
    """Redis 缓存管理器，提供统一的缓存操作接口"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "devflow",
    ):
        """
        初始化缓存管理器。

        Args:
            redis_url: Redis 连接 URL，默认使用 settings.REDIS_URL
            default_ttl: 默认缓存过期时间（秒），默认 3600
            key_prefix: 缓存 key 前缀，默认 "devflow"
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

        self._redis: Optional[Redis] = None
        self._connected = False

    def _connect(self) -> Redis:
        """建立 Redis 连接"""
        if self._redis is not None:
            try:
                self._redis.ping()
                return self._redis
            except (RedisConnectionError, RedisTimeoutError):
                self._redis = None

        try:
            self._redis = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            self._redis.ping()
            self._connected = True
            logger.info("Redis cache connected: %s", self.redis_url)
        except RedisConnectionError as e:
            logger.warning("Redis connection failed, cache will be disabled: %s", e)
            self._connected = False
            raise
        return self._redis

    @property
    def is_connected(self) -> bool:
        """检查 Redis 是否已连接"""
        if self._connected and self._redis is not None:
            try:
                self._redis.ping()
                return True
            except (RedisConnectionError, RedisTimeoutError):
                self._connected = False
        return False

    def _full_key(self, key: str) -> str:
        """生成带前缀的完整 key"""
        return f"{self.key_prefix}:{key}"

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值。

        Args:
            key: 缓存键
            default: 缓存不存在时的默认值

        Returns:
            缓存值（自动反序列化），不存在时返回 default
        """
        if not self.is_connected:
            return default
        try:
            self._connect()
            raw = self._redis.get(self._full_key(key))
            if raw is None:
                return default
            return self._deserialize(raw)
        except RedisError as e:
            logger.error("Redis GET error for key '%s': %s", key, e)
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True,
    ) -> bool:
        """
        设置缓存值。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），使用默认值如果为 None
            serialize: 是否自动序列化

        Returns:
            是否成功写入
        """
        if not self.is_connected:
            return False
        try:
            self._connect()
            full_key = self._full_key(key)
            if serialize:
                data = json.dumps(value, default=str, ensure_ascii=False)
            else:
                data = value
            return bool(self._redis.set(full_key, data, ex=ttl or self.default_ttl))
        except RedisError as e:
            logger.error("Redis SET error for key '%s': %s", key, e)
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存。

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        if not self.is_connected:
            return False
        try:
            self._connect()
            return bool(self._redis.delete(self._full_key(key)))
        except RedisError as e:
            logger.error("Redis DELETE error for key '%s': %s", key, e)
            return False

    def exists(self, key: str) -> bool:
        """
        检查 key 是否存在。

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if not self.is_connected:
            return False
        try:
            self._connect()
            return bool(self._redis.exists(self._full_key(key)))
        except RedisError as e:
            logger.error("Redis EXISTS error for key '%s': %s", key, e)
            return False

    def ttl(self, key: str) -> int:
        """
        获取 key 的剩余生存时间（秒）。

        Args:
            key: 缓存键

        Returns:
            剩余秒数，-1 表示无 TTL，-2 表示 key 不存在
        """
        if not self.is_connected:
            return -2
        try:
            self._connect()
            return self._redis.ttl(self._full_key(key))
        except RedisError as e:
            logger.error("Redis TTL error for key '%s': %s", key, e)
            return -2

    def set_ttl(self, key: str, ttl: int) -> bool:
        """
        设置或更新 key 的 TTL。

        Args:
            key: 缓存键
            ttl: 剩余生存时间（秒）

        Returns:
            是否成功设置
        """
        if not self.is_connected:
            return False
        try:
            self._connect()
            return bool(self._redis.expire(self._full_key(key), ttl))
        except RedisError as e:
            logger.error("Redis SET_TTL error for key '%s': %s", key, e)
            return False

    def clear(self, pattern: str = f"{self.key_prefix}:*") -> int:
        """
        清除匹配的缓存 key。

        Args:
            pattern: 匹配模式，默认清除所有 devflow 缓存

        Returns:
            删除的 key 数量
        """
        if not self.is_connected:
            return 0
        try:
            self._connect()
            deleted = 0
            for key in self._redis.scan_iter(match=pattern):
                self._redis.delete(key)
                deleted += 1
            return deleted
        except RedisError as e:
            logger.error("Redis CLEAR error with pattern '%s': %s", pattern, e)
            return 0

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        原子自增计数。

        Args:
            key: 缓存键
            amount: 自增值

        Returns:
            自增后的值，失败时返回 None
        """
        if not self.is_connected:
            return None
        try:
            self._connect()
            return self._redis.incr(self._full_key(key), amount)
        except RedisError as e:
            logger.error("Redis INCR error for key '%s': %s", key, e)
            return None

    def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        原子自减计数。

        Args:
            key: 缓存键
            amount: 自减值

        Returns:
            自减后的值，失败时返回 None
        """
        if not self.is_connected:
            return None
        try:
            self._connect()
            return self._redis.decr(self._full_key(key), amount)
        except RedisError as e:
            logger.error("Redis DECR error for key '%s': %s", key, e)
            return None

    def set_if_not_exists(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        仅当 key 不存在时设置（SETNX）。

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）

        Returns:
            True 如果设置了新值，False 如果 key 已存在
        """
        if not self.is_connected:
            return False
        try:
            self._connect()
            data = json.dumps(value, default=str, ensure_ascii=False)
            full_key = self._full_key(key)
            return bool(self._redis.set(full_key, data, nx=True, ex=ttl or self.default_ttl))
        except RedisError as e:
            logger.error("Redis SETNX error for key '%s': %s", key, e)
            return False

    def get_set(
        self, key: str, *values: str
    ) -> List[str]:
        """获取集合中的所有成员"""
        if not self.is_connected:
            return []
        try:
            self._connect()
            return self._redis.smembers(self._full_key(key))
        except RedisError as e:
            logger.error("Redis SMEMBERS error for key '%s': %s", key, e)
            return []

    def add_to_set(self, key: str, *values: str) -> int:
        """向集合添加成员"""
        if not self.is_connected:
            return 0
        try:
            self._connect()
            return self._redis.sadd(self._full_key(key), *values)
        except RedisError as e:
            logger.error("Redis SADD error for key '%s': %s", key, e)
            return 0

    def remove_from_set(self, key: str, *values: str) -> int:
        """从集合移除成员"""
        if not self.is_connected:
            return 0
        try:
            self._connect()
            return self._redis.srem(self._full_key(key), *values)
        except RedisError as e:
            logger.error("Redis SREM error for key '%s': %s", key, e)
            return 0

    def get_list(self, key: str) -> List[str]:
        """获取列表中的所有元素"""
        if not self.is_connected:
            return []
        try:
            self._connect()
            return self._redis.lrange(self._full_key(key), 0, -1)
        except RedisError as e:
            logger.error("Redis LRANGE error for key '%s': %s", key, e)
            return []

    def push_to_list(self, key: str, *values: str) -> int:
        """向列表右侧添加元素"""
        if not self.is_connected:
            return 0
        try:
            self._connect()
            return self._redis.rpush(self._full_key(key), *values)
        except RedisError as e:
            logger.error("Redis RPUSH error for key '%s': %s", key, e)
            return 0

    def push_left(self, key: str, *values: str) -> int:
        """向列表左侧添加元素"""
        if not self.is_connected:
            return 0
        try:
            self._connect()
            return self._redis.lpush(self._full_key(key), *values)
        except RedisError as e:
            logger.error("Redis LPUSH error for key '%s': %s", key, e)
            return 0

    def _serialize(self, value: Any) -> str:
        """将值序列化为 JSON 字符串"""
        return json.dumps(value, default=str, ensure_ascii=False)

    def _deserialize(self, raw: str) -> Any:
        """将 JSON 字符串反序列化回原值"""
        return json.loads(raw)

    def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            try:
                self._redis.close()
            except Exception:
                pass
            self._redis = None
            self._connected = False
            logger.info("Redis cache connection closed")


# 全局单例
_cache_manager: Optional[RedisCacheManager] = None


def get_cache_manager(
    redis_url: Optional[str] = None,
    default_ttl: int = 3600,
    key_prefix: str = "devflow",
) -> RedisCacheManager:
    """
    获取全局缓存管理器单例。

    Args:
        redis_url: Redis 连接 URL
        default_ttl: 默认 TTL（秒）
        key_prefix: key 前缀

    Returns:
        RedisCacheManager 实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = RedisCacheManager(
            redis_url=redis_url,
            default_ttl=default_ttl,
            key_prefix=key_prefix,
        )
    return _cache_manager
