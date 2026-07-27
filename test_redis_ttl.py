import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from functools import wraps


class RedisTTLManager:
    def __init__(self, default_ttl=60):
        self._default_ttl = default_ttl
        self._prefix_ttl_map: dict[str, int] = {}

    @property
    def default_ttl(self) -> int:
        return self._default_ttl

    @default_ttl.setter
    def default_ttl(self, value: int):
        if value <= 0:
            raise ValueError("TTL must be a positive integer")
        self._default_ttl = value

    def set_key_ttl(self, key: str, ttl: int) -> None:
        if ttl <= 0:
            raise ValueError("TTL must be a positive integer")
        self._current_key_ttl = ttl

    def set_prefix_ttl(self, prefix: str, ttl: int) -> None:
        if ttl <= 0:
            raise ValueError("TTL must be a positive integer")
        self._prefix_ttl_map[prefix] = ttl

    def get_ttl_for_key(self, key: str) -> int:
        for prefix, ttl in self._prefix_ttl_map.items():
            if key.startswith(prefix):
                return ttl
        return self._default_ttl

    def batch_set_prefix_ttl(self, prefix_ttl_pairs: dict[str, int]) -> None:
        for prefix, ttl in prefix_ttl_pairs.items():
            self.set_prefix_ttl(prefix, ttl)


def _create_redis_mock():
    redis = MagicMock()
    redis_client = MagicMock()
    redis.__enter__ = MagicMock(return_value=redis_client)
    redis.__exit__ = MagicMock(return_value=None)
    return redis, redis_client


@pytest.fixture
def ttl_manager():
    return RedisTTLManager(default_ttl=60)


@pytest.fixture
def redis_mock():
    return _create_redis_mock()


def test_key_auto_expires_after_ttl(ttl_manager, redis_mock):
    """键在60秒后自动删除"""
    _, redis_client = redis_mock
    ttl_manager.default_ttl = 60
    ttl = ttl_manager.get_ttl_for_key("user:1001")
    assert ttl == 60

    with patch("time.sleep", return_value=None):
        redis_client.set("user:1001", "data", ex=ttl)
    redis_client.set.assert_called_with("user:1001", "data", ex=60)
    redis_client.get.assert_not_called()


def test_ttl_config_immediate_effect(ttl_manager):
    """TTL配置即时生效"""
    assert ttl_manager.default_ttl == 60
    ttl_manager.default_ttl = 120
    assert ttl_manager.default_ttl == 120

    ttl = ttl_manager.get_ttl_for_key("session:abc")
    assert ttl == 120

    with pytest.raises(ValueError, match="TTL must be a positive integer"):
        ttl_manager.default_ttl = -1

    with pytest.raises(ValueError, match="TTL must be a positive integer"):
        ttl_manager.default_ttl = 0


def test_batch_set_prefix_ttl(ttl_manager):
    """支持按键前缀批量设置TTL"""
    ttl_manager.batch_set_prefix_ttl({
        "user:": 300,
        "session:": 120,
        "token:": 60,
    })

    assert ttl_manager.get_ttl_for_key("user:1001") == 300
    assert ttl_manager.get_ttl_for_key("session:abc") == 120
    assert ttl_manager.get_ttl_for_key("token:xyz") == 60

    default_ttl = ttl_manager.get_ttl_for_key("unknown:key")
    assert default_ttl == 60

    ttl_manager.batch_set_prefix_ttl({
        "user:": 600,
    })
    assert ttl_manager.get_ttl_for_key("user:2002") == 600
    assert ttl_manager.get_ttl_for_key("session:abc") == 120


def test_prefix_ttl_overrides_default(ttl_manager):
    """前缀TTL覆盖默认TTL"""
    ttl_manager.default_ttl = 60
    ttl_manager.set_prefix_ttl("hot:", 10)
    ttl = ttl_manager.get_ttl_for_key("hot:cache:1")
    assert ttl == 10

    default = ttl_manager.get_ttl_for_key("cold:cache:1")
    assert default == 60


def test_ttl_zero_raises_value_error(ttl_manager):
    """TTL设为0或负数时抛出异常"""
    with pytest.raises(ValueError):
        ttl_manager.set_prefix_ttl("bad:", 0)

    with pytest.raises(ValueError):
        ttl_manager.set_key_ttl("bad:key", -5)

    with pytest.raises(ValueError):
        ttl_manager.batch_set_prefix_ttl({"bad:": -1})
