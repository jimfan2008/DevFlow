#!/usr/bin/env python3
"""
DevFlow Redis 缓存层 - 缓存失效策略
提供自动缓存失效和手动缓存清理功能
"""

import logging
from typing import Optional, List, Dict, Set

from app.caches.manager import RedisCacheManager, get_cache_manager

logger = logging.getLogger("devflow.caches.invalidation")


# ── 缓存命名空间常量 ──────────────────────────────────────
NAMESPACE_TASKS = "tasks"
NAMESPACE_TASK_BY_ID = "task"
NAMESPACE_BOARD = "boards"
NAMESPACE_USER = "users"
NAMESPACE_COMMENTS = "comments"
NAMESPACE_ATTACHMENTS = "attachments"
NAMESPACE_DEPS = "dependencies"
NAMESPACE_WORKLOAD = "workload"
# ── 命名空间 -> 全局通配符 映射 ──────────────────────────
NAMESPACE_PATTERNS = {
    NAMESPACE_TASKS: "tasks:*",
    NAMESPACE_TASK_BY_ID: "task:*",
    NAMESPACE_BOARD: "boards:*",
    NAMESPACE_USER: "users:*",
    NAMESPACE_COMMENTS: "comments:*",
    NAMESPACE_ATTACHMENTS: "attachments:*",
    NAMESPACE_DEPS: "dependencies:*",
    NAMESPACE_WORKLOAD: "workload:*",
}


class CacheInvalidator:
    """
    缓存失效策略管理器。
    基于命名空间（namespace）统一管理缓存失效，
    在 Service 层调用时自动清理相关缓存。
    """

    def __init__(self, cache_manager: Optional[RedisCacheManager] = None):
        """
        Args:
            cache_manager: 缓存管理器实例，默认使用全局单例
        """
        self.cm = cache_manager or get_cache_manager()
        self._namespace_keys: Dict[str, Set[str]] = {}

    def register_namespace(self, namespace: str, key: str) -> None:
        """
        注册命名空间与 key 的关联。
        当命名空间失效时，只清除关联的 key。

        Args:
            namespace: 命名空间名称
            key: 缓存 key
        """
        if namespace not in self._namespace_keys:
            self._namespace_keys[namespace] = set()
        self._namespace_keys[namespace].add(key)

    def invalidate_namespace(self, namespace: str) -> int:
        """
        失效整个命名空间的所有缓存。

        Args:
            namespace: 命名空间名称

        Returns:
            清除的缓存数量
        """
        pattern = NAMESPACE_PATTERNS.get(namespace, f"{namespace}:*")
        return self.cm.clear(pattern)

    def invalidate_keys(self, keys: List[str]) -> int:
        """
        失效指定的缓存 key。

        Args:
            keys: 需要失效的 key 列表

        Returns:
            清除的缓存数量
        """
        deleted = 0
        for key in keys:
            if self.cm.delete(key):
                deleted += 1
        return deleted

    def invalidate_pattern(self, pattern: str) -> int:
        """
        按模式失效缓存。

        Args:
            pattern: Redis glob 匹配模式

        Returns:
            清除的缓存数量
        """
        return self.cm.clear(pattern)

    def invalidate_task(self, task_id: str) -> int:
        """
        失效任务相关的所有缓存。

        Args:
            task_id: 任务 ID

        Returns:
            清除的缓存数量
        """
        count = 0
        # 清除该任务详情
        count += self.cm.delete(f"{NAMESPACE_TASK_BY_ID}:{task_id}")
        # 清除任务列表（看板级别）
        count += self.invalidate_namespace(NAMESPACE_TASKS)
        # 清除相关评论
        count += self.cm.clear(f"comments:task:{task_id}:*")
        # 清除相关依赖
        count += self.cm.clear(f"dependencies:task:{task_id}:*")
        return count

    def invalidate_board(self, board_id: str) -> int:
        """
        失效看板相关的所有缓存。

        Args:
            board_id: 看板 ID

        Returns:
            清除的缓存数量
        """
        count = 0
        # 看板详情
        count += self.cm.delete(f"{NAMESPACE_BOARD}:{board_id}")
        # 看板任务
        count += self.cm.clear(f"tasks:board:{board_id}:*")
        # 看板工作负载
        count += self.cm.clear(f"workload:board:{board_id}:*")
        # 该看板所有评论
        count += self.cm.clear(f"comments:board:{board_id}:*")
        return count

    def invalidate_user(self, user_id: str) -> int:
        """
        失效用户相关的所有缓存。

        Args:
            user_id: 用户 ID

        Returns:
            清除的缓存数量
        """
        count = 0
        # 用户详情
        count += self.cm.delete(f"{NAMESPACE_USER}:{user_id}")
        # 用户收件箱
        return count

    def invalidate_comments(self, task_id: str) -> int:
        """
        失效任务评论缓存。

        Args:
            task_id: 任务 ID

        Returns:
            清除的缓存数量
        """
        return self.cm.clear(f"comments:task:{task_id}:*")

    def invalidate_all(self) -> int:
        """
        清除所有 devflow 缓存（危险操作，慎用）。

        Returns:
            清除的缓存数量
        """
        return self.cm.clear()


# 全局单例
_invalidator: Optional[CacheInvalidator] = None


def get_invalidator(cache_manager: Optional[RedisCacheManager] = None) -> CacheInvalidator:
    """
    获取全局缓存失效管理器单例。

    Args:
        cache_manager: 可选的缓存管理器实例

    Returns:
        CacheInvalidator 实例
    """
    global _invalidator
    if _invalidator is None:
        _invalidator = CacheInvalidator(cache_manager=cache_manager)
    return _invalidator


# ── 便捷函数 ──────────────────────────────────────────────
def invalidate_all_cache():
    """快速清除所有 devflow 缓存"""
    return get_invalidator().invalidate_all()


def clear_task_cache(task_id: str):
    """快速清除任务相关缓存"""
    return get_invalidator().invalidate_task(task_id)


def clear_board_cache(board_id: str):
    """快速清看板相关缓存"""
    return get_invalidator().invalidate_board(board_id)
