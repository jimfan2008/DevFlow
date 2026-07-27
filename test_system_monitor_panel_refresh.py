"""系统监控面板数据刷新 - TDD 测试用例

验收标准：
1. 面板显示 CPU使用率、内存使用率、磁盘 I/O、网络流量四项指标
2. WebSocket 推送刷新间隔 小于等于 10 秒
3. 历史数据查询响应 小于等于 2 秒
"""

import json
import time
import asyncio
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest


# ==============================================================================
# Mock WebSocket - 同步版（用于线程场景）
# ==============================================================================

class SyncMockWebSocket:
    """模拟 WebSocket 连接（同步、线程安全）"""

    def __init__(self):
        self.messages = []
        self.connected = False
        self._lock = threading.Lock()

    def connect(self):
        self.connected = True

    def send(self, data: str):
        with self._lock:
            self.messages.append({
                "direction": "outbound",
                "data": data,
                "timestamp": time.time(),
            })

    def push(self, data: str):
        with self._lock:
            self.messages.append({
                "direction": "inbound",
                "data": data,
                "timestamp": time.time(),
            })

    def close(self):
        self.connected = False

    def get_inbound(self):
        with self._lock:
            return [m for m in self.messages if m["direction"] == "inbound"]


# ==============================================================================
# Mock WebSocket - 异步版（用于 asyncio 场景）
# ==============================================================================

class AsyncMockWebSocket:
    """模拟 WebSocket 连接（异步）"""

    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages: list[dict] = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data: dict):
        self.sent_messages.append(data)

    async def close(self, code=1000):
        self.closed = True


# ==============================================================================
# 被测类 - 系统指标采集器
# ==============================================================================

class SystemMetricsCollector:
    """系统指标采集器

    负责采集 CPU、内存、磁盘 I/O、网络四项指标，
    通过 WebSocket 推送给前端面板。
    """

    REQUIRED_METRICS = ["cpu_usage", "memory_usage", "disk_io", "network_traffic"]

    def __init__(self, cpu=45.0, memory=72.0, disk_read_mbps=120.0,
                 disk_write_mbps=45.0, net_in_mbps=200.0, net_out_mbps=80.0,
                 refresh_interval: float = 5.0):
        self.refresh_interval = refresh_interval
        self._cpu = cpu
        self._memory = memory
        self._disk_read = disk_read_mbps
        self._disk_write = disk_write_mbps
        self._net_in = net_in_mbps
        self._net_out = net_out_mbps
        self._history: list[dict] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._ws: SyncMockWebSocket | None = None

    def collect(self) -> dict:
        """采集当前指标快照"""
        snapshot = {
            "cpu_usage": round(self._cpu, 2),
            "memory_usage": round(self._memory, 2),
            "disk_io": {
                "read_mbps": round(self._disk_read, 2),
                "write_mbps": round(self._disk_write, 2),
            },
            "network_traffic": {
                "inbound_mbps": round(self._net_in, 2),
                "outbound_mbps": round(self._net_out, 2),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(snapshot)
        return snapshot

    def get_current_metrics(self) -> dict:
        """获取当前指标"""
        return self.collect()

    def start_refresh(self, ws: SyncMockWebSocket):
        """启动定时采集和推送"""
        self._ws = ws
        self._running = True
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def stop_refresh(self):
        """停止推送"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def _refresh_loop(self):
        """定时采集循环"""
        while self._running:
            snapshot = self.collect()
            if self._ws:
                self._ws.push(json.dumps(snapshot))
            time.sleep(self.refresh_interval)

    def get_history(self, since: datetime | None = None) -> list[dict]:
        """查询历史数据"""
        if since is None:
            return list(self._history)
        return [
            item for item in self._history
            if datetime.fromisoformat(item["timestamp"]) >= since
        ]


# ==============================================================================
# 被测类 - 异步版采集器（用于 WebSocket 广播）
# ==============================================================================

class AsyncMetricsCollector:
    """异步指标采集器 - 支持多订阅者广播"""

    def __init__(self, refresh_interval: float = 5.0):
        self.refresh_interval = refresh_interval
        self._subscribers: set = set()
        self._history: list[dict] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._collector = SystemMetricsCollector()

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._collect_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def subscribe(self, ws: AsyncMockWebSocket):
        await ws.accept()
        self._subscribers.add(ws)

    async def unsubscribe(self, ws: AsyncMockWebSocket):
        self._subscribers.discard(ws)

    async def _collect_loop(self):
        while self._running:
            snapshot = self._collector.collect()
            self._history.append(snapshot)
            await self._broadcast(snapshot)
            await asyncio.sleep(self.refresh_interval)

    async def _broadcast(self, snapshot: dict):
        dead = set()
        for ws in self._subscribers:
            try:
                await ws.send_json({
                    "type": "metrics_update",
                    "data": snapshot,
                })
            except Exception:
                dead.add(ws)
        self._subscribers -= dead

    def get_current_metrics(self) -> dict:
        return self._collector.get_current_metrics()

    def get_history(self, metric_key: str, start: datetime,
                    end: datetime, limit: int = 1000) -> list[dict]:
        """按指标键和时间范围查询历史"""
        results = []
        for snap in self._history:
            ts = datetime.fromisoformat(snap["timestamp"])
            if start <= ts <= end:
                if metric_key == "cpu":
                    results.append({"timestamp": snap["timestamp"], "value": snap["cpu_usage"]})
                elif metric_key == "memory":
                    results.append({"timestamp": snap["timestamp"], "value": snap["memory_usage"]})
                elif metric_key == "disk_io":
                    results.append({"timestamp": snap["timestamp"], "value": snap["disk_io"]})
                elif metric_key == "network":
                    results.append({"timestamp": snap["timestamp"], "value": snap["network_traffic"]})
        return results[:limit]


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def collector():
    return SystemMetricsCollector(refresh_interval=0.05)


@pytest.fixture
def sync_ws():
    return SyncMockWebSocket()


@pytest.fixture
async def async_collector():
    c = AsyncMetricsCollector(refresh_interval=0.05)
    await c.start()
    yield c
    await c.stop()
    await asyncio.sleep(0.01)


@pytest.fixture
def async_ws():
    return AsyncMockWebSocket()


# ==============================================================================
# 验收标准 1：面板显示四项指标
# ==============================================================================

class TestPanelDisplaysFourMetrics:
    """面板显示 CPU使用率、内存使用率、磁盘 I/O、网络流量"""

    def test_cpu_usage_present_and_valid(self, collector):
        data = collector.get_current_metrics()
        assert "cpu_usage" in data
        assert isinstance(data["cpu_usage"], (int, float))
        assert 0 <= data["cpu_usage"] <= 100

    def test_memory_usage_present_and_valid(self, collector):
        data = collector.get_current_metrics()
        assert "memory_usage" in data
        assert isinstance(data["memory_usage"], (int, float))
        assert 0 <= data["memory_usage"] <= 100

    def test_disk_io_present_and_valid(self, collector):
        data = collector.get_current_metrics()
        assert "disk_io" in data
        disk = data["disk_io"]
        assert "read_mbps" in disk
        assert "write_mbps" in disk
        assert disk["read_mbps"] >= 0
        assert disk["write_mbps"] >= 0

    def test_network_traffic_present_and_valid(self, collector):
        data = collector.get_current_metrics()
        assert "network_traffic" in data
        net = data["network_traffic"]
        assert "inbound_mbps" in net
        assert "outbound_mbps" in net
        assert net["inbound_mbps"] >= 0
        assert net["outbound_mbps"] >= 0

    def test_all_four_metrics_in_single_snapshot(self, collector):
        """单次采集返回的数据必须包含全部四项指标"""
        data = collector.get_current_metrics()
        for key in SystemMetricsCollector.REQUIRED_METRICS:
            assert key in data, f"缺少指标: {key}"

    def test_snapshot_contains_timestamp(self, collector):
        data = collector.get_current_metrics()
        assert "timestamp" in data
        ts = datetime.fromisoformat(data["timestamp"])
        assert ts is not None

    def test_multiple_snapshots_are_independent(self, collector):
        m1 = collector.get_current_metrics()
        m2 = collector.get_current_metrics()
        assert m1 is not m2

    def test_cpu_zero_boundary(self):
        c = SystemMetricsCollector(cpu=0.0)
        assert c.collect()["cpu_usage"] == 0.0

    def test_cpu_hundred_boundary(self):
        c = SystemMetricsCollector(cpu=100.0)
        assert c.collect()["cpu_usage"] == 100.0

    def test_memory_zero_boundary(self):
        c = SystemMetricsCollector(memory=0.0)
        assert c.collect()["memory_usage"] == 0.0

    def test_disk_io_all_zero(self):
        c = SystemMetricsCollector(disk_read_mbps=0, disk_write_mbps=0)
        snap = c.collect()
        assert snap["disk_io"]["read_mbps"] == 0
        assert snap["disk_io"]["write_mbps"] == 0

    def test_network_all_zero(self):
        c = SystemMetricsCollector(net_in_mbps=0, net_out_mbps=0)
        snap = c.collect()
        assert snap["network_traffic"]["inbound_mbps"] == 0
        assert snap["network_traffic"]["outbound_mbps"] == 0

    def test_large_values_no_overflow(self):
        c = SystemMetricsCollector(net_in_mbps=9999999.99, net_out_mbps=8888888.88)
        snap = c.collect()
        assert snap["network_traffic"]["inbound_mbps"] == 9999999.99
        assert snap["network_traffic"]["outbound_mbps"] == 8888888.88


# ==============================================================================
# 验收标准 2：WebSocket 推送刷新间隔 小于等于 10 秒
# ==============================================================================

class TestWebSocketPushInterval:
    """WebSocket 推送刷新间隔 小于等于 10 秒"""

    def test_push_contains_all_four_metrics(self, collector, sync_ws):
        """推送的 JSON 消息必须包含四项指标"""
        collector.start_refresh(sync_ws)
        time.sleep(0.2)
        collector.stop_refresh()

        inbound = sync_ws.get_inbound()
        assert len(inbound) >= 1
        parsed = json.loads(inbound[0]["data"])
        for key in SystemMetricsCollector.REQUIRED_METRICS:
            assert key in parsed, f"推送消息缺少指标: {key}"

    def test_push_interval_within_10_seconds(self, sync_ws):
        """连续两次推送间隔必须 小于等于 10 秒"""
        c = SystemMetricsCollector(refresh_interval=2.0)
        c.start_refresh(sync_ws)
        time.sleep(5.0)
        c.stop_refresh()

        inbound = sync_ws.get_inbound()
        assert len(inbound) >= 2
        timestamps = [m["timestamp"] for m in inbound]
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i - 1]
            assert gap <= 10.0, f"推送间隔 {gap:.2f}s 超过 10 秒"

    def test_push_interval_matches_config(self, sync_ws):
        """推送间隔应与配置值大致一致（容差 50%）"""
        interval = 0.3
        c = SystemMetricsCollector(refresh_interval=interval)
        c.start_refresh(sync_ws)
        time.sleep(interval * 3.5)
        c.stop_refresh()

        inbound = sync_ws.get_inbound()
        assert len(inbound) >= 2
        timestamps = [m["timestamp"] for m in inbound]
        gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
        avg_gap = sum(gaps) / len(gaps)
        assert avg_gap >= interval * 0.5, f"平均间隔 {avg_gap:.2f}s 远低于配置值 {interval}s"
        assert avg_gap <= interval * 1.5, f"平均间隔 {avg_gap:.2f}s 远高于配置值 {interval}s"

    def test_no_push_after_stop(self, collector, sync_ws):
        """停止后不应再产生推送"""
        collector.start_refresh(sync_ws)
        time.sleep(0.2)
        count_before = len(sync_ws.get_inbound())
        collector.stop_refresh()
        time.sleep(0.3)
        count_after = len(sync_ws.get_inbound())
        assert count_after == count_before, \
            f"停止后仍收到推送: {count_before} -> {count_after}"

    def test_push_resumes_after_restart(self, sync_ws):
        """停止再启动后应恢复推送"""
        c = SystemMetricsCollector(refresh_interval=0.05)
        c.start_refresh(sync_ws)
        time.sleep(0.15)
        c.stop_refresh()
        count_mid = len(sync_ws.get_inbound())
        time.sleep(0.1)
        assert len(sync_ws.get_inbound()) == count_mid
        c.start_refresh(sync_ws)
        time.sleep(0.15)
        assert len(sync_ws.get_inbound()) > count_mid


# ==============================================================================
# 异步 WebSocket 广播测试
# ==============================================================================

class TestAsyncWebSocketBroadcast:
    """异步 WebSocket 广播场景"""

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_all_subscribers(self, async_collector):
        ws1 = AsyncMockWebSocket()
        ws2 = AsyncMockWebSocket()
        await async_collector.subscribe(ws1)
        await async_collector.subscribe(ws2)
        await asyncio.sleep(0.15)

        assert len(ws1.sent_messages) >= 1
        assert len(ws2.sent_messages) >= 1
        assert ws1.sent_messages[0]["type"] == "metrics_update"
        assert ws2.sent_messages[0]["type"] == "metrics_update"

    @pytest.mark.asyncio
    async def test_broadcast_message_has_all_metrics(self, async_collector):
        ws = AsyncMockWebSocket()
        await async_collector.subscribe(ws)
        await asyncio.sleep(0.15)

        assert len(ws.sent_messages) >= 1
        data = ws.sent_messages[0]["data"]
        for key in SystemMetricsCollector.REQUIRED_METRICS:
            assert key in data

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_delivery(self, async_collector):
        ws = AsyncMockWebSocket()
        await async_collector.subscribe(ws)
        await asyncio.sleep(0.1)
        count_before = len(ws.sent_messages)
        await async_collector.unsubscribe(ws)
        await asyncio.sleep(0.15)
        count_after = len(ws.sent_messages)
        assert count_before == count_after

    @pytest.mark.asyncio
    async def test_dead_subscriber_removed_on_error(self):
        """发送失败的订阅者应被自动移除"""
        c = AsyncMetricsCollector(refresh_interval=0.05)
        broken = AsyncMockWebSocket()
        broken.send_json = AsyncMock(side_effect=ConnectionError("lost"))
        good = AsyncMockWebSocket()

        await c.start()
        c._subscribers.add(broken)
        await c.subscribe(good)
        await asyncio.sleep(0.15)
        await c.stop()

        assert broken not in c._subscribers
        assert good in c._subscribers
        assert len(good.sent_messages) >= 1

    @pytest.mark.asyncio
    async def test_concurrent_subscribers_no_race(self, async_collector):
        ws_list = [AsyncMockWebSocket() for _ in range(10)]
        tasks = [async_collector.subscribe(ws) for ws in ws_list]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.15)

        for ws in ws_list:
            assert len(ws.sent_messages) >= 1

    @pytest.mark.asyncio
    async def test_stop_cancels_task_cleanly(self):
        c = AsyncMetricsCollector(refresh_interval=0.05)
        await c.start()
        assert c._task is not None
        await c.stop()
        assert c._task is None


# ==============================================================================
# 验收标准 3：历史数据查询响应 小于等于 2 秒
# ==============================================================================

class TestHistoryQueryPerformance:
    """历史数据查询响应 小于等于 2 秒"""

    def test_full_history_query_within_2_seconds(self, collector, sync_ws):
        """全量历史数据查询 小于等于 2 秒"""
        collector.start_refresh(sync_ws)
        time.sleep(0.5)
        collector.stop_refresh()

        t0 = time.perf_counter()
        result = collector.get_history()
        elapsed = time.perf_counter() - t0

        assert len(result) >= 4
        assert elapsed <= 2.0, f"查询耗时 {elapsed:.4f}s 超过 2 秒"

    def test_filtered_history_query_within_2_seconds(self, collector, sync_ws):
        """带时间过滤的历史查询 小于等于 2 秒"""
        collector.start_refresh(sync_ws)
        time.sleep(0.5)
        collector.stop_refresh()

        since = datetime.now(timezone.utc) - timedelta(seconds=1)
        t0 = time.perf_counter()
        result = collector.get_history(since=since)
        elapsed = time.perf_counter() - t0

        assert len(result) >= 1
        assert elapsed <= 2.0, f"过滤查询耗时 {elapsed:.4f}s 超过 2 秒"
        for item in result:
            item_ts = datetime.fromisoformat(item["timestamp"])
            assert item_ts >= since

    def test_empty_history_returns_quickly(self, collector):
        """空历史查询应快速返回"""
        t0 = time.perf_counter()
        result = collector.get_history()
        elapsed = time.perf_counter() - t0

        assert result == []
        assert elapsed < 0.1

    def test_history_entries_have_timestamp_and_all_metrics(self, collector):
        """历史条目应包含 timestamp 和全部指标"""
        collector.collect()
        collector.collect()
        history = collector.get_history()

        assert len(history) == 2
        for entry in history:
            assert "timestamp" in entry
            for key in SystemMetricsCollector.REQUIRED_METRICS:
                assert key in entry

    def test_history_preserves_insertion_order(self, collector):
        """历史记录应保持插入顺序"""
        collector.collect()
        ts1 = collector._history[-1]["timestamp"]
        time.sleep(0.01)
        collector.collect()
        ts2 = collector._history[-1]["timestamp"]

        history = collector.get_history()
        assert history[0]["timestamp"] <= history[1]["timestamp"]


# ==============================================================================
# 异步版历史查询
# ==============================================================================

class TestAsyncHistoryQuery:
    """异步采集器历史查询"""

    def test_async_history_cpu_within_2_seconds(self, async_collector):
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        t0 = time.perf_counter()
        result = async_collector.get_history("cpu", start, now)
        elapsed = time.perf_counter() - t0

        assert isinstance(result, list)
        assert elapsed <= 2.0

    def test_async_history_memory_within_2_seconds(self, async_collector):
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=2)

        t0 = time.perf_counter()
        result = async_collector.get_history("memory", start, now)
        elapsed = time.perf_counter() - t0

        assert isinstance(result, list)
        assert elapsed <= 2.0

    def test_async_history_disk_io_within_2_seconds(self, async_collector):
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=6)

        t0 = time.perf_counter()
        result = async_collector.get_history("disk_io", start, now)
        elapsed = time.perf_counter() - t0

        assert isinstance(result, list)
        assert elapsed <= 2.0

    def test_async_history_network_within_2_seconds(self, async_collector):
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=1)

        t0 = time.perf_counter()
        result = async_collector.get_history("network", start, now)
        elapsed = time.perf_counter() - t0

        assert isinstance(result, list)
        assert elapsed <= 2.0

    def test_async_history_with_limit(self, async_collector):
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=1)

        result = async_collector.get_history("cpu", start, now, limit=3)
        assert len(result) <= 3

    def test_async_history_empty_when_no_data(self, async_collector):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        result = async_collector.get_history(
            "cpu", future, future + timedelta(hours=1)
        )
        assert result == []

    def test_async_history_unknown_metric(self, async_collector):
        now = datetime.now(timezone.utc)
        result = async_collector.get_history(
            "gpu", now - timedelta(hours=1), now
        )
        assert result == []

    def test_async_history_entry_structure(self, async_collector):
        now = datetime.now(timezone.utc)
        start = now - timedelta(seconds=5)
        result = async_collector.get_history("cpu", start, now)

        if result:
            entry = result[0]
            assert "timestamp" in entry
            assert "value" in entry
            assert isinstance(entry["value"], (int, float))
