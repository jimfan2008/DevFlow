import pytest
import time
from unittest.mock import Mock, patch, PropertyMock


class RedisCacheMonitor:
    def __init__(self, redis_client):
        self._redis = redis_client
        self._last_stats = {}

    def collect_stats(self):
        info = self._redis.info("stats")
        memory_info = self._redis.info("memory")
        keyspace_info = self._redis.info("keyspace")
        clients_info = self._redis.info("clients")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0.0
        used_memory = memory_info.get("used_memory", 0)
        max_memory = memory_info.get("max_memory", 0)
        memory_ratio = (used_memory / max_memory * 100) if max_memory > 0 else 0.0
        total_keys = sum(
            db.get("keys", 0) for db in keyspace_info.values()
        ) if keyspace_info else 0
        connected_clients = clients_info.get("connected_clients", 0)
        self._last_stats = {
            "hit_rate": round(hit_rate, 2),
            "memory_used_bytes": used_memory,
            "max_memory_bytes": max_memory,
            "memory_ratio": round(memory_ratio, 2),
            "total_keys": total_keys,
            "connected_clients": connected_clients,
            "collected_at": time.time(),
        }
        return self._last_stats

    def get_stats(self):
        return self._last_stats


class TestRedisCacheMonitor:
    @pytest.fixture
    def mock_redis(self):
        redis_mock = Mock()
        redis_mock.info.side_effect = lambda section: {
            "stats": {"keyspace_hits": 900, "keyspace_misses": 100},
            "memory": {"used_memory": 52428800, "max_memory": 104857600},
            "keyspace": {"db0": {"keys": 1500}, "db1": {"keys": 500}},
            "clients": {"connected_clients": 42},
        }.get(section, {})
        return redis_mock

    def test_cache_hit_rate_meets_threshold(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["hit_rate"] >= 90.0

    def test_cache_hit_rate_exact_value(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        expected_rate = 900 / (900 + 100) * 100
        assert stats["hit_rate"] == pytest.approx(expected_rate, rel=1e-6)

    def test_cache_hit_rate_when_no_requests(self, mock_redis):
        mock_redis.info.side_effect = lambda section: {
            "stats": {"keyspace_hits": 0, "keyspace_misses": 0},
            "memory": {"used_memory": 0, "max_memory": 104857600},
            "keyspace": {},
            "clients": {"connected_clients": 0},
        }.get(section, {})
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["hit_rate"] == 0.0

    def test_memory_usage_and_ratio(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["memory_used_bytes"] == 52428800
        assert stats["max_memory_bytes"] == 104857600
        expected_ratio = 52428800 / 104857600 * 100
        assert stats["memory_ratio"] == pytest.approx(expected_ratio, rel=1e-6)

    def test_memory_ratio_when_max_memory_zero(self, mock_redis):
        mock_redis.info.side_effect = lambda section: {
            "stats": {"keyspace_hits": 900, "keyspace_misses": 100},
            "memory": {"used_memory": 52428800, "max_memory": 0},
            "keyspace": {"db0": {"keys": 1500}},
            "clients": {"connected_clients": 42},
        }.get(section, {})
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["memory_ratio"] == 0.0

    def test_key_count_statistics(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["total_keys"] == 2000

    def test_key_count_when_no_keyspace(self, mock_redis):
        mock_redis.info.side_effect = lambda section: {
            "stats": {"keyspace_hits": 900, "keyspace_misses": 100},
            "memory": {"used_memory": 52428800, "max_memory": 104857600},
            "keyspace": {},
            "clients": {"connected_clients": 42},
        }.get(section, {})
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["total_keys"] == 0

    def test_connection_count_monitoring(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["connected_clients"] == 42

    def test_connection_count_when_zero(self, mock_redis):
        mock_redis.info.side_effect = lambda section: {
            "stats": {"keyspace_hits": 900, "keyspace_misses": 100},
            "memory": {"used_memory": 52428800, "max_memory": 104857600},
            "keyspace": {"db0": {"keys": 1500}},
            "clients": {"connected_clients": 0},
        }.get(section, {})
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        assert stats["connected_clients"] == 0

    def test_data_refreshes_within_5_seconds(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        t1 = time.time()
        monitor.collect_stats()
        t2 = time.time()
        elapsed = t2 - t1
        assert elapsed <= 5.0

    def test_collect_stats_returns_expected_structure(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        stats = monitor.collect_stats()
        expected_keys = {
            "hit_rate", "memory_used_bytes", "max_memory_bytes",
            "memory_ratio", "total_keys", "connected_clients", "collected_at",
        }
        assert set(stats.keys()) == expected_keys

    def test_get_stats_returns_cached_data(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        assert monitor.get_stats() == {}
        monitor.collect_stats()
        cached = monitor.get_stats()
        assert cached["hit_rate"] == 90.0
