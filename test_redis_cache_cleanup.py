#!/usr/bin/env python3
"""
TDD 测试：Redis 缓存按模式清理
验收标准：
  1. 匹配模式的键被全部删除
  2. 不匹配的键保留
  3. 清理操作响应时间 ≤5 秒
"""

import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock, create_autospec


class MockRedis:
    """模拟 Redis 客户端，用于独立测试"""

    def __init__(self):
        self._store: dict = {}
        self._scan_keys: list = []
        self._delete_count: int = 0
        self._ping_count: int = 0

    def ping(self) -> bool:
        self._ping_count += 1
        return True

    def set(self, key: str, value: str, ex: int = None) -> bool:
        self._store[key] = value
        return True

    def get(self, key: str):
        return self._store.get(key)

    def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            self._delete_count += 1
            return 1
        return 0

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def scan_iter(self, match: str = "*"):
        import fnmatch
        keys = list(self._store.keys())
        for k in keys:
            if fnmatch.fnmatch(k, match):
                yield k

    def close(self):
        self._store.clear()

    def keys(self, pattern: str = "*") -> list:
        import fnmatch
        return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]


class RedisCacheManager:
    """Redis 缓存管理器 - 按模式清理缓存"""

    def __init__(self, redis_client=None, key_prefix: str = "devflow"):
        self._redis = redis_client
        self.key_prefix = key_prefix
        self._connected = True

    def _full_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    @property
    def is_connected(self) -> bool:
        if self._redis is not None:
            try:
                self._redis.ping()
                return self._connected
            except Exception:
                return False
        return False

    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        if not self.is_connected:
            return False
        full_key = self._full_key(key)
        return bool(self._redis.set(full_key, value, ex=ttl))

    def get(self, key: str):
        if not self.is_connected:
            return None
        return self._redis.get(self._full_key(key))

    def delete(self, key: str) -> bool:
        if not self.is_connected:
            return False
        return bool(self._redis.delete(self._full_key(key)))

    def exists(self, key: str) -> bool:
        if not self.is_connected:
            return False
        return bool(self._redis.exists(self._full_key(key)))

    def clear(self, pattern: str = None) -> int:
        """按模式清理缓存，返回删除的键数量"""
        if not self.is_connected:
            return 0
        if pattern is None:
            pattern = f"{self.key_prefix}:*"
        elif not pattern.startswith(self.key_prefix):
            pattern = f"{self.key_prefix}:{pattern}"
        deleted = 0
        for key in self._redis.scan_iter(match=pattern):
            self._redis.delete(key)
            deleted += 1
        return deleted

    def close(self):
        if self._redis:
            self._redis.close()
            self._connected = False


@pytest.fixture
def mock_redis():
    """创建模拟 Redis 客户端"""
    return MockRedis()


@pytest.fixture
def cache_manager(mock_redis):
    """创建缓存管理器实例"""
    mgr = RedisCacheManager(redis_client=mock_redis, key_prefix="devflow")
    yield mgr
    mgr.close()


class TestRedisCacheCleanupByPattern:

    def test_clear_deletes_all_matching_keys(self, cache_manager, mock_redis):
        """验收标准 1：匹配模式的键被全部删除"""
        # 准备测试数据：3 个匹配 user:* 模式的键
        cache_manager.set("user:1001", '{"name": "Alice"}')
        cache_manager.set("user:1002", '{"name": "Bob"}')
        cache_manager.set("user:1003", '{"name": "Charlie"}')

        # 清理 user:* 模式的缓存
        deleted_count = cache_manager.clear("user:*")

        # 验证所有匹配键被删除
        assert deleted_count == 3, f"应删除 3 个键，实际删除 {deleted_count} 个"
        assert cache_manager.get("user:1001") is None, "user:1001 应被删除"
        assert cache_manager.get("user:1002") is None, "user:1002 应被删除"
        assert cache_manager.get("user:1003") is None, "user:1003 应被删除"

    def test_clear_preserves_non_matching_keys(self, cache_manager, mock_redis):
        """验收标准 2：不匹配的键保留"""
        # 准备混合数据
        cache_manager.set("user:1001", '{"name": "Alice"}')
        cache_manager.set("user:1002", '{"name": "Bob"}')
        cache_manager.set("session:abc", "token_xyz")
        cache_manager.set("config:theme", "dark")

        # 只清理 user:* 模式的缓存
        deleted_count = cache_manager.clear("user:*")

        # 验证匹配的键被删除
        assert deleted_count == 2
        assert cache_manager.get("user:1001") is None
        assert cache_manager.get("user:1002") is None

        # 验证不匹配的键保留
        assert cache_manager.get("session:abc") == "token_xyz", "session:abc 应保留"
        assert cache_manager.get("config:theme") == "dark", "config:theme 应保留"
        assert cache_manager.exists("session:abc") is True
        assert cache_manager.exists("config:theme") is True

    def test_clear_response_time_within_5_seconds(self, cache_manager, mock_redis):
        """验收标准 3：清理操作响应时间 ≤5 秒"""
        # 准备 10 个匹配 user:* 模式的键
        for i in range(10):
            cache_manager.set(f"user:{i}", f'{{"id": {i}}}')

        # 计时清理操作
        start_time = time.time()
        deleted_count = cache_manager.clear("user:*")
        elapsed = time.time() - start_time

        # 验证清理结果和响应时间
        assert deleted_count == 10, f"应删除 10 个键，实际删除 {deleted_count} 个"
        assert elapsed <= 5.0, f"清理操作耗时 {elapsed:.4f} 秒，超过 5 秒限制"

    def test_clear_with_wildcard_pattern_all_keys(self, cache_manager, mock_redis):
        """清理所有 devflow 前缀的键"""
        cache_manager.set("user:1", "data1")
        cache_manager.set("session:2", "data2")
        cache_manager.set("config:3", "data3")

        deleted_count = cache_manager.clear()

        assert deleted_count == 3
        assert cache_manager.get("user:1") is None
        assert cache_manager.get("session:2") is None
        assert cache_manager.get("config:3") is None

    def test_clear_with_no_matching_keys(self, cache_manager, mock_redis):
        """清理时没有匹配键，返回 0"""
        cache_manager.set("session:abc", "token_xyz")

        deleted_count = cache_manager.clear("user:*")

        assert deleted_count == 0
        assert cache_manager.get("session:abc") == "token_xyz", "不匹配的键应保留"

    def test_clear_empty_cache(self, cache_manager, mock_redis):
        """清理空缓存"""
        deleted_count = cache_manager.clear("user:*")

        assert deleted_count == 0

    def test_clear_preserves_keys_from_other_prefix(self, cache_manager, mock_redis):
        """清理不影响其他前缀的键（通过直接操作 mock_redis 验证）"""
        # 使用 cache_manager 设置的键（devflow 前缀）
        cache_manager.set("user:1001", "Alice")

        # 直接操作 mock_redis 添加非 devflow 前缀的键
        mock_redis.set("other_prefix:user:1001", "Bob")

        # 清理 devflow:user:*
        deleted_count = cache_manager.clear("user:*")

        assert deleted_count == 1
        assert cache_manager.get("user:1001") is None
        assert mock_redis.get("other_prefix:user:1001") == "Bob", "其他前缀的键应保留"

    def test_clear_multiple_patterns_sequentially(self, cache_manager, mock_redis):
        """连续按不同模式清理"""
        cache_manager.set("user:1", "A")
        cache_manager.set("user:2", "B")
        cache_manager.set("session:1", "X")
        cache_manager.set("session:2", "Y")
        cache_manager.set("config:theme", "dark")

        # 第一次清理：user:*
        deleted1 = cache_manager.clear("user:*")
        assert deleted1 == 2
        assert cache_manager.get("user:1") is None
        assert cache_manager.get("user:2") is None

        # 第二次清理：session:*
        deleted2 = cache_manager.clear("session:*")
        assert deleted2 == 2
        assert cache_manager.get("session:1") is None
        assert cache_manager.get("session:2") is None

        # 验证 config 键始终保留
        assert cache_manager.get("config:theme") == "dark", "config:theme 应始终保留"

    def test_clear_with_prefix_auto_applied(self, cache_manager, mock_redis):
        """验证 clear 方法自动应用 key_prefix"""
        cache_manager.set("user:1001", "Alice")

        # 传入不带前缀的模式
        deleted_count = cache_manager.clear("user:*")

        assert deleted_count == 1
        assert cache_manager.get("user:1001") is None

    def test_clear_disconnected_returns_zero(self, mock_redis):
        """断连时清理返回 0"""
        mgr = RedisCacheManager(redis_client=mock_redis, key_prefix="devflow")
        mgr._connected = False

        deleted_count = mgr.clear("user:*")

        assert deleted_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
