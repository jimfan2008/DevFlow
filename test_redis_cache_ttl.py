import time
import pytest
from unittest.mock import MagicMock, patch
import json


class RedisCacheTTLManager:
    """Redis缓存TTL管理器"""

    def __init__(self, redis_client, default_ttl=60):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.ttl_overrides = {}

    def set_with_ttl(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.default_ttl
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self.redis.setex(key, ttl, value)

    def get(self, key):
        value = self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def set_ttl_override(self, prefix, ttl):
        self.ttl_overrides[prefix] = ttl

    def get_ttl_for_key(self, key):
        for prefix, ttl in self.ttl_overrides.items():
            if key.startswith(prefix):
                return ttl
        return self.default_ttl

    def batch_set_ttl_by_prefix(self, prefix, ttl):
        """按前缀批量设置TTL"""
        self.set_ttl_override(prefix, ttl)
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match=f"{prefix}*")
            for key in keys:
                self.redis.expire(key, ttl)
            if cursor == 0:
                break


class MockRedis:
    """模拟Redis用于测试"""

    def __init__(self):
        self.store = {}
        self.ttls = {}

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = time.time() + ttl

    def get(self, key):
        if key in self.ttls and time.time() > self.ttls[key]:
            del self.store[key]
            del self.ttls[key]
            return None
        return self.store.get(key)

    def expire(self, key, ttl):
        if key in self.store:
            self.ttls[key] = time.time() + ttl

    def scan(self, cursor=0, match=None):
        keys = []
        for k in self.store:
            if match and k.startswith(match.rstrip("*")):
                keys.append(k)
        return (0, keys)


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
def ttl_manager(mock_redis):
    return RedisCacheTTLManager(mock_redis, default_ttl=60)


def test_key_auto_expires_after_ttl(mock_redis):
    """验证键在TTL秒后自动删除"""
    mgr = RedisCacheTTLManager(mock_redis, default_ttl=60)
    mgr.set_with_ttl("test:key1", "value1", ttl=2)
    assert mgr.get("test:key1") == "value1"

    mock_redis.ttls["test:key1"] = time.time() - 1
    result = mgr.get("test:key1")
    assert result is None


def test_default_ttl_is_60_seconds(ttl_manager, mock_redis):
    """验证默认TTL为60秒"""
    ttl_manager.set_with_ttl("test:key2", "value2")
    ttl = mock_redis.ttls.get("test:key2", 0)
    expected_min = time.time() + 59
    expected_max = time.time() + 61
    assert expected_min <= ttl <= expected_max


def test_ttl_config_takes_effect_immediately(ttl_manager, mock_redis):
    """验证TTL配置即时生效"""
    ttl_manager.default_ttl = 120
    ttl_manager.set_with_ttl("test:key3", "value3")
    ttl = mock_redis.ttls.get("test:key3", 0)
    expected_min = time.time() + 119
    expected_max = time.time() + 121
    assert expected_min <= ttl <= expected_max


def test_batch_set_ttl_by_prefix(ttl_manager, mock_redis):
    """支持按键前缀批量设置TTL"""
    ttl_manager.set_with_ttl("user:1001", {"name": "alice"})
    ttl_manager.set_with_ttl("user:1002", {"name": "bob"})
    ttl_manager.set_with_ttl("order:2001", {"item": "book"})

    ttl_manager.batch_set_ttl_by_prefix("user:", 300)

    ttl1 = mock_redis.ttls.get("user:1001", 0)
    ttl2 = mock_redis.ttls.get("user:1002", 0)
    order_ttl = mock_redis.ttls.get("order:2001", 0)

    expected_min = time.time() + 299
    expected_max = time.time() + 301
    assert expected_min <= ttl1 <= expected_max
    assert expected_min <= ttl2 <= expected_max
    assert order_ttl < time.time() + 100


def test_ttl_override_per_prefix(ttl_manager):
    """验证前缀覆盖的TTL优先级"""
    ttl_manager.set_ttl_override("session:", 30)
    ttl_manager.set_ttl_override("token:", 900)

    assert ttl_manager.get_ttl_for_key("session:abc") == 30
    assert ttl_manager.get_ttl_for_key("token:xyz") == 900
    assert ttl_manager.get_ttl_for_key("other:data") == 60


def test_serialized_value_storage(ttl_manager):
    """验证字典/列表值正确序列化存储"""
    ttl_manager.set_with_ttl("data:config", {"theme": "dark", "lang": "zh"})
    result = ttl_manager.get("data:config")
    assert result == {"theme": "dark", "lang": "zh"}

    ttl_manager.set_with_ttl("data:list", [1, 2, 3])
    result = ttl_manager.get("data:list")
    assert result == [1, 2, 3]
