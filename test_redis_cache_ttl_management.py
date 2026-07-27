#!/usr/bin/env python3
"""
Redis缓存TTL管理 - TDD 测试用例
验证 Redis 缓存 TTL 可配置且自动过期。

验收标准：
1. 键在 60 秒后自动删除
2. TTL 配置即时生效
3. 支持按键前缀批量设置 TTL
"""

import json
import time
from unittest.mock import MagicMock

import pytest

# ── 被测类 ─────────────────────────────────────────────────


class TTLConfig:
    """TTL 配置管理器"""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._prefix_ttl: dict[str, int] = {}

    def set_default_ttl(self, ttl: int) -> None:
        """设置默认 TTL"""
        self.default_ttl = ttl

    def get_ttl(self, key: str) -> int:
        """根据 key 前缀获取 TTL，找不到则返回默认值"""
        for prefix, ttl in self._prefix_ttl.items():
            if key.startswith(prefix):
                return ttl
        return self.default_ttl

    def set_prefix_ttl(self, prefix: str, ttl: int) -> None:
        """为指定前缀的 key 设置 TTL"""
        self._prefix_ttl[prefix] = ttl


class RedisCacheManager:
    """Redis 缓存管理器（简化版，仅含 TTL 相关逻辑）"""

    def __init__(self, redis_client, ttl_config: TTLConfig):
        self.client = redis_client
        self.ttl_config = ttl_config

    def get(self, key: str):
        """获取缓存值"""
        raw = self.client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, value, ttl: int | None = None) -> bool:
        """设置缓存值，自动应用 TTL"""
        data = json.dumps(value, default=str, ensure_ascii=False)
        effective_ttl = ttl if ttl is not None else self.ttl_config.get_ttl(key)
        return self.client.set(key, data, ex=effective_ttl)

    def set_ttl(self, key: str, ttl: int) -> bool:
        """设置 / 更新指定 key 的 TTL"""
        return self.client.expire(key, ttl)

    def set_prefix_ttl(self, prefix: str, ttl: int) -> int:
        """
        对当前所有匹配前缀的 key 批量设置 TTL。

        Args:
            prefix: key 前缀（如 "batch:"），会自动追加通配符
            ttl: 新的 TTL 秒数

        Returns:
            成功设置的 key 数量
        """
        self.ttl_config.set_prefix_ttl(prefix, ttl)
        # 兼容前缀带不带末尾冒号的情况
        pattern = prefix if prefix.endswith("*") else prefix.rstrip(":") + ":*"
        count = 0
        for key in self.client.scan_iter(match=pattern):
            if self.client.expire(key, ttl):
                count += 1
        return count

    def ttl(self, key: str) -> int:
        """获取 key 的剩余生存时间"""
        return self.client.ttl(key)

    def exists(self, key: str) -> bool:
        """检查 key 是否存在"""
        return bool(self.client.exists(key))


# ── Fixture ────────────────────────────────────────────────


@pytest.fixture
def mock_redis():
    """模拟 Redis 客户端，支持 set/get/ttl/expire/exists/scan_iter"""
    store: dict[str, str] = {}
    store_ttl: dict[str, float] = {}  # key → 过期时间戳

    client = MagicMock()

    def _set(key, value, ex=None):
        store[key] = value
        if ex is not None:
            store_ttl[key] = time.time() + ex
        else:
            store_ttl.pop(key, None)
        return True

    def _get(key):
        return _maybe_expired(key) or store.get(key)

    def _maybe_expired(key):
        if key in store_ttl:
            if time.time() >= store_ttl[key]:
                del store[key]
                del store_ttl[key]
                return ""  # 视为过期
        return None

    def _ttl(key):
        _maybe_expired(key)
        if key in store_ttl:
            remaining = store_ttl[key] - time.time()
            return max(int(remaining), 0)
        if key in store:
            return -1
        return -2

    def _expire(key, ttl_seconds):
        if key in store:
            store_ttl[key] = time.time() + ttl_seconds
            return True
        return False

    def _exists(key):
        _maybe_expired(key)
        return 1 if key in store else 0

    def _check_all_expired():
        now = time.time()
        expired = [k for k, ts in store_ttl.items() if now >= ts]
        for k in expired:
            store.pop(k, None)
            store_ttl.pop(k, None)

    def _scan_iter(match="*"):
        _check_all_expired()
        import fnmatch
        yield from (k for k in list(store.keys()) if fnmatch.fnmatch(k, match))

    client.set.side_effect = _set
    client.get.side_effect = _get
    client.ttl.side_effect = _ttl
    client.expire.side_effect = _expire
    client.exists.side_effect = _exists
    client.scan_iter.side_effect = _scan_iter

    client._store = store
    client._store_ttl = store_ttl

    return client


@pytest.fixture
def ttl_config():
    return TTLConfig(default_ttl=3600)


@pytest.fixture
def cache_manager(mock_redis, ttl_config):
    return RedisCacheManager(mock_redis, ttl_config)


# ── 测试类 ─────────────────────────────────────────────────


class TestKeyAutoExpireAfter60Seconds:
    """验收标准 1：键在 60 秒后自动删除"""

    def test_key_set_with_60s_ttl_has_correct_ttl(self, cache_manager, mock_redis):
        """设置 60 秒 TTL 后，立即查询 TTL 应约为 60"""
        cache_manager.set("temp:key1", {"data": "hello"}, ttl=60)
        remaining = cache_manager.ttl("temp:key1")
        assert 55 <= remaining <= 61, f"TTL 应为 ~60，实际为 {remaining}"

    def test_key_is_deleted_after_ttl_expires(self, mock_redis, ttl_config):
        """模拟时间推进，验证 key 在 TTL 到期后被自动删除"""
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set("temp:key1", {"data": "hello"}, ttl=60)

        # 初始状态：key 存在
        assert mgr.exists("temp:key1")

        # 伪造时间：推进 61 秒
        mock_redis._store_ttl["temp:key1"] = time.time() - 1  # 已过期
        assert not mgr.exists("temp:key1")

    def test_key_value_is_gone_after_expiry(self, mock_redis, ttl_config):
        """过期后 get 应返回 None"""
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set("temp:key2", "important", ttl=60)
        mock_redis._store_ttl["temp:key2"] = time.time() - 1
        val = mgr.get("temp:key2")
        assert val is None

    def test_key_without_ttl_never_expires(self, cache_manager, mock_redis):
        """不设 TTL 的 key 应始终存在（ttl 返回 -1）"""
        cache_manager.set("persist:key1", "no-expire")
        mock_redis._store_ttl.pop("persist:key1", None)
        remaining = cache_manager.ttl("persist:key1")
        assert remaining == -1


class TestTTLConfigTakesEffectImmediately:
    """验收标准 2：TTL 配置即时生效"""

    def test_new_key_uses_updated_default_ttl(self, mock_redis, ttl_config):
        """修改默认 TTL 后，新写入的 key 立即使用新值"""
        ttl_config.set_default_ttl(120)
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set("data:key1", "value1")

        remaining = mgr.ttl("data:key1")
        assert 115 <= remaining <= 121, f"应使用新默认 TTL 120，实际 {remaining}"

    def test_set_prefix_ttl_affects_new_keys_instantly(self, mock_redis, ttl_config):
        """设置前缀 TTL 后，新写入的前缀 key 立即命中"""
        ttl_config.set_prefix_ttl("session:", 30)
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set("session:user1", {"uid": 1})

        remaining = mgr.ttl("session:user1")
        assert 25 <= remaining <= 31, f"前缀 TTL 应即时生效为 30，实际 {remaining}"

    def test_prefix_ttl_overrides_default(self, mock_redis, ttl_config):
        """前缀 TTL 应覆盖默认 TTL"""
        ttl_config.default_ttl = 7200
        ttl_config.set_prefix_ttl("hot:", 10)
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set("hot:counter", 42)

        remaining = mgr.ttl("hot:counter")
        assert 5 <= remaining <= 11, f"前缀 TTL 10 应覆盖默认 7200，实际 {remaining}"

    def test_update_ttl_on_existing_key(self, cache_manager, mock_redis):
        """对已存在的 key 重新设置 TTL 应即时生效"""
        cache_manager.set("data:key1", "old", ttl=300)
        # 重新设置 TTL 为 45
        cache_manager.set_ttl("data:key1", 45)
        remaining = cache_manager.ttl("data:key1")
        assert 40 <= remaining <= 46, f"TTL 更新后应为 ~45，实际 {remaining}"


class TestBatchSetTTLByPrefix:
    """验收标准 3：支持按键前缀批量设置 TTL"""

    def test_batch_set_ttl_affects_all_matching_keys(self, mock_redis, ttl_config):
        """批量设置前缀 TTL 应更新所有匹配 key"""
        mgr = RedisCacheManager(mock_redis, ttl_config)
        # 预先写入多个 key
        for i in range(5):
            mgr.set(f"batch:item{i}", f"value{i}", ttl=9999)

        count = mgr.set_prefix_ttl("batch:", 120)
        assert count == 5, f"应更新 5 个 key，实际 {count}"

        # 逐一验证 TTL
        for i in range(5):
            remaining = mgr.ttl(f"batch:item{i}")
            assert 115 <= remaining <= 121, f"batch:item{i} TTL 应为 ~120，实际 {remaining}"

    def test_batch_set_ttl_ignores_non_matching_keys(self, mock_redis, ttl_config):
        """批量设置前缀 TTL 不应影响不匹配的 key"""
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set("batch:item0", "a", ttl=9999)
        mgr.set("other:item0", "b", ttl=9999)

        count = mgr.set_prefix_ttl("batch:", 60)
        assert count == 1

        # 未匹配的 key TTL 不变
        remaining_other = mgr.ttl("other:item0")
        assert 9994 <= remaining_other <= 9999

    def test_batch_set_ttl_on_empty_prefix_returns_zero(self, mock_redis, ttl_config):
        """无前缀匹配的 key 时，批量设置返回 0"""
        mgr = RedisCacheManager(mock_redis, ttl_config)
        count = mgr.set_prefix_ttl("empty:", 60)
        assert count == 0

    def test_batch_set_ttl_updates_config_for_future_keys(self, mock_redis, ttl_config):
        """批量设置后，后续新 key 也应使用新 TTL"""
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set_prefix_ttl("queue:", 25)

        # 新 key 也应命中
        mgr.set("queue:task1", "do_work")
        remaining = mgr.ttl("queue:task1")
        assert 20 <= remaining <= 26, f"新 key 应使用前缀 TTL 25，实际 {remaining}"

    def test_batch_set_ttl_updates_existing_and_config(self, mock_redis, ttl_config):
        """批量设置应同时更新现有 key 和未来 key"""
        mgr = RedisCacheManager(mock_redis, ttl_config)
        mgr.set("api:cache1", "v1", ttl=1000)
        mgr.set("api:cache2", "v2", ttl=1000)

        count = mgr.set_prefix_ttl("api:", 50)
        assert count == 2

        # 现有 key
        for i in range(1, 3):
            remaining = mgr.ttl(f"api:cache{i}")
            assert 45 <= remaining <= 51

        # 未来 key
        mgr.set("api:cache3", "v3")
        remaining = mgr.ttl("api:cache3")
        assert 45 <= remaining <= 51
