#!/usr/bin/env python3
"""
DevFlow Redis 缓存层 - 缓存装饰器
支持基于函数的自动缓存，支持自定义 key 生成和失效策略
"""

import functools
import hashlib
import inspect
import logging
from typing import Optional, Callable, Any

from app.caches.manager import RedisCacheManager, get_cache_manager

logger = logging.getLogger("devflow.caches.decorator")


def _generate_key(prefix: str, args: tuple, kwargs: dict, **extra) -> str:
    """
    根据函数签名生成缓存 key。

    Args:
        prefix: 缓存前缀
        args: 函数位置参数
        kwargs: 函数关键字参数
        **extra: 额外的 key 组件

    Returns:
        完整的缓存 key
    """
    # 将参数转换为字符串
    arg_str = ":".join(
        [repr(a) for a in args]
        + [f"{k}={repr(v)}" for k, v in sorted(kwargs.items())]
        + [f"{k}={repr(v)}" for k, v in extra.items()]
    )

    # 使用 MD5 哈希缩短 key 长度
    key_hash = hashlib.md5(arg_str.encode()).hexdigest()[:16]
    return f"{prefix}:{key_hash}"


def cache(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_func: Optional[Callable] = None,
    prefix: str = "cache",
    cache_manager: Optional[RedisCacheManager] = None,
):
    """
    缓存装饰器，自动缓存函数返回值。

    Args:
        ttl: 缓存过期时间（秒），使用默认值如果为 None
        key_prefix: 缓存 key 前缀，如果为 None 则使用函数名
        key_func: 自定义 key 生成函数，签名: func(func_name, args, kwargs) -> key
        prefix: 全局缓存前缀
        cache_manager: 可选的自定义缓存管理器

    Returns:
        装饰后的函数

    Example:
        @cache(ttl=300, key_prefix="tasks")
        def get_tasks(board_id):
            ...

        @cache(key_func=lambda name, args, kwargs: f"task:{args[0]}")
        def get_task(task_id):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cm = cache_manager or get_cache_manager()
            if not cm.is_connected:
                return func(*args, **kwargs)

            # 生成缓存 key
            if key_func:
                cache_key = key_func(func.__name__, args, kwargs)
            else:
                effective_prefix = key_prefix or func.__name__
                cache_key = _generate_key(
                    f"{prefix}:{effective_prefix}", args, kwargs
                )

            # 尝试从缓存获取
            cached = cm.get(cache_key)
            if cached is not None:
                return cached

            # 缓存未命中，执行函数
            result = func(*args, **kwargs)

            # 写入缓存
            if ttl is not None:
                cm.set(cache_key, result, ttl=ttl)
            else:
                cm.set(cache_key, result)

            return result

        # 附加缓存清除方法
        def clear(*args, **kwargs):
            """清除该函数的缓存"""
            if key_func:
                cache_key = key_func(func.__name__, args, kwargs)
            else:
                effective_prefix = key_prefix or func.__name__
                cache_key = _generate_key(
                    f"{prefix}:{effective_prefix}", args, kwargs
                )
            return cm.delete(cache_key)

        # 附加通配清除方法
        def clear_all():
            """清除该函数所有缓存"""
            pattern = f"{prefix}:{key_prefix or func.__name__}:*"
            return cm.clear(pattern)

        wrapper.clear = clear
        wrapper.clear_all = clear_all
        wrapper.cache_key = cache_key  # 原始 key 模板，用于调试

        return wrapper

    return decorator


def invalidate_cache(pattern: str) -> Callable:
    """
    缓存失效装饰器。在函数执行后自动清除匹配模式的缓存。

    Args:
        pattern: 缓存 key 匹配模式（Redis glob 风格）

    Example:
        @invalidate_cache("tasks:*")
        def update_task(task_id, **kwargs):
            ...
    """

    def decorator(func: Callable) -> Callable:
        cm = get_cache_manager()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # 异步执行缓存清除（不阻塞）
            try:
                cm.clear(pattern)
            except Exception as e:
                logger.warning("Cache invalidation failed for pattern '%s': %s", pattern, e)
            return result

        return wrapper

    return decorator


def cache_with_prefix(prefix: str) -> Callable:
    """
    通用缓存装饰器工厂，使用指定前缀。

    Args:
        prefix: 缓存 key 前缀

    Returns:
        装饰器

    Example:
        task_cache = cache_with_prefix("tasks")

        @task_cache(ttl=60)
        def list_tasks(board_id):
            ...
    """

    def decorator(func: Callable) -> Callable:
        return cache(prefix=prefix, key_prefix=prefix)(func)

    return decorator
