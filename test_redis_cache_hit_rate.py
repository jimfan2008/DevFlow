import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import time
from datetime import datetime, timedelta


class RedisCacheMonitor:
    def __init__(self, redis_client):
        self.client = redis_client

    def get_hit_rate(self):
        info = self.client.info("stats")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total == 0:
            return 100.0
        return round(hits / total * 100, 2)

    def get_memory_usage_ratio(self):
        info = self.client.info("memory")
        used = info.get("used_memory", 0)
        max_mem = info.get("maxmemory", 0)
        if max_mem == 0:
            return 0.0
        return round(used / max_mem * 100, 2)

    def get_key_count(self):
        info = self.client.info("keyspace")
        total = 0
        for db_stats in info.values():
            total += db_stats.get("keys", 0)
        return total

    def get_connected_clients(self):
        info = self.client.info("clients")
        return info.get("connected_clients", 0)

    def get_all_metrics(self):
        return {
            "hit_rate": self.get_hit_rate(),
            "memory_usage_ratio": self.get_memory_usage_ratio(),
            "key_count": self.get_key_count(),
            "connected_clients": self.get_connected_clients(),
            "timestamp": datetime.now().isoformat(),
        }


@pytest.fixture
def mock_redis():
    client = MagicMock()
    info_side_effect = {
        "stats": {"keyspace_hits": 950, "keyspace_misses": 50},
        "memory": {"used_memory": 52428800, "maxmemory": 107374182},
        "keyspace": {"db0": {"keys": 1200, "expires": 100}, "db1": {"keys": 300, "expires": 50}},
        "clients": {"connected_clients": 15, "blocked_clients": 0},
    }
    client.info.side_effect = lambda section: info_side_effect.get(section, {})
    return client


@pytest.fixture
def monitor(mock_redis):
    return RedisCacheMonitor(mock_redis)


class TestRedisCacheHitRate:
    def test_hit_rate_above_90_percent(self, monitor):
        rate = monitor.get_hit_rate()
        assert rate >= 90.0, f"命中率 {rate}% 低于 90%"

    def test_hit_rate_when_no_requests(self, mock_redis):
        mock_redis.info.side_effect = {
            "stats": {"keyspace_hits": 0, "keyspace_misses": 0},
        }.get
        monitor = RedisCacheMonitor(mock_redis)
        rate = monitor.get_hit_rate()
        assert rate == 100.0

    def test_hit_rate_with_only_misses(self, mock_redis):
        mock_redis.info.side_effect = {
            "stats": {"keyspace_hits": 0, "keyspace_misses": 100},
        }.get
        monitor = RedisCacheMonitor(mock_redis)
        rate = monitor.get_hit_rate()
        assert rate == 0.0


class TestRedisMemoryUsage:
    def test_memory_usage_ratio_calculation(self, monitor):
        ratio = monitor.get_memory_usage_ratio()
        assert ratio > 0.0
        assert ratio < 100.0

    def test_memory_ratio_when_no_maxmemory(self, mock_redis):
        mock_redis.info.side_effect = {
            "memory": {"used_memory": 1024, "maxmemory": 0},
        }.get
        monitor = RedisCacheMonitor(mock_redis)
        ratio = monitor.get_memory_usage_ratio()
        assert ratio == 0.0


class TestRedisKeyCount:
    def test_key_count_summary(self, monitor):
        count = monitor.get_key_count()
        assert count == 1500

    def test_key_count_when_no_keyspace(self, mock_redis):
        mock_redis.info.side_effect = {
            "keyspace": {},
        }.get
        monitor = RedisCacheMonitor(mock_redis)
        count = monitor.get_key_count()
        assert count == 0


class TestRedisConnectionCount:
    def test_connected_clients_count(self, monitor):
        clients = monitor.get_connected_clients()
        assert clients == 15

    def test_connected_clients_zero(self, mock_redis):
        mock_redis.info.side_effect = {
            "clients": {"connected_clients": 0},
        }.get
        monitor = RedisCacheMonitor(mock_redis)
        clients = monitor.get_connected_clients()
        assert clients == 0


class TestRedisDataRefresh:
    def test_all_metrics_refresh_within_5_seconds(self, mock_redis):
        monitor = RedisCacheMonitor(mock_redis)
        start = time.time()
        metrics = monitor.get_all_metrics()
        elapsed = time.time() - start
        assert elapsed <= 5.0, f"数据刷新耗时 {elapsed:.3f}秒，超过 5 秒限制"
        assert "hit_rate" in metrics
        assert "memory_usage_ratio" in metrics
        assert "key_count" in metrics
        assert "connected_clients" in metrics
        assert "timestamp" in metrics

    def test_metrics_contain_timestamp(self, monitor):
        metrics = monitor.get_all_metrics()
        assert "timestamp" in metrics
        ts = datetime.fromisoformat(metrics["timestamp"])
        assert abs((datetime.now() - ts).total_seconds()) < 2
