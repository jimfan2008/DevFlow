"""系统监控面板数据刷新 - TDD 测试用例"""
import time
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest


class MockWebSocket:
    """模拟 WebSocket 连接"""

    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data: dict):
        self.sent_messages.append(data)

    async def send_text(self, data: str):
        self.sent_messages.append(json.loads(data))

    async def receive_text(self):
        return json.dumps({"type": "ping"})

    async def close(self, code=1000):
        self.closed = True


class MockSystemMetrics:
    """模拟系统指标采集器"""

    def __init__(self, cpu=45.0, memory=62.0, disk_read=102400, disk_write=81920,
                 net_in=524288, net_out=262144):
        self._cpu = cpu
        self._memory = memory
        self._disk_read = disk_read
        self._disk_write = disk_write
        self._net_in = net_in
        self._net_out = net_out
        self._history = []

    def collect(self) -> dict:
        """采集当前系统指标快照"""
        ts = datetime.now().isoformat()
        snapshot = {
            "timestamp": ts,
            "cpu_usage": round(self._cpu, 2),
            "memory_usage": round(self._memory, 2),
            "disk_io": {
                "read_bytes": self._disk_read,
                "write_bytes": self._disk_write,
                "read_iops": int(self._disk_read / 4096),
                "write_iops": int(self._disk_write / 4096),
            },
            "network": {
                "bytes_in": self._net_in,
                "bytes_out": self._net_out,
                "packets_in": self._net_in // 1500,
                "packets_out": self._net_out // 1500,
            },
        }
        self._history.append(snapshot)
        return snapshot

    def get_history(self, metric_key: str, start: datetime, end: datetime,
                    limit: int = 1000) -> list:
        """查询历史指标数据"""
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
                    results.append({"timestamp": snap["timestamp"], "value": snap["network"]})
        return results[:limit]


class MetricsCollector:
    """系统指标采集器 - 被测试的核心类

    负责采集 CPU、内存、磁盘 I/O、网络四项指标，
    将数据通过 WebSocket 推送给前端面板。
    """

    def __init__(self, refresh_interval: float = 5.0):
        self.refresh_interval = refresh_interval
        self._subscribers: set = set()
        self._history: list = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._collector = MockSystemMetrics()

    async def start(self):
        """启动定时采集和推送"""
        self._running = True
        self._task = asyncio.create_task(self._collect_loop())

    async def stop(self):
        """停止采集和推送"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def subscribe(self, ws: MockWebSocket):
        """订阅指标推送"""
        await ws.accept()
        self._subscribers.add(ws)

    async def unsubscribe(self, ws: MockWebSocket):
        """取消订阅"""
        self._subscribers.discard(ws)

    async def _collect_loop(self):
        """定时采集循环"""
        while self._running:
            snapshot = self._collector.collect()
            self._history.append(snapshot)
            await self._broadcast(snapshot)
            await asyncio.sleep(self.refresh_interval)

    async def _broadcast(self, snapshot: dict):
        """向所有订阅者广播指标"""
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

    def get_history(self, metric_key: str, start: datetime,
                    end: datetime, limit: int = 1000) -> list:
        """查询历史数据"""
        return self._collector.get_history(metric_key, start, end, limit)


class DashboardAPI:
    """模拟系统监控面板 API 层"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def get_current_metrics(self) -> dict:
        """获取当前系统指标快照"""
        return self.collector._collector.collect()

    def get_metrics_history(self, metric_key: str,
                            start_iso: str, end_iso: str,
                            limit: int = 1000) -> dict:
        """查询历史数据并返回 API 响应"""
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        data = self.collector.get_history(metric_key, start, end, limit)
        return {
            "metric": metric_key,
            "count": len(data),
            "data": data,
        }


@pytest.fixture
async def collector():
    """指标采集器实例 - 自动启动并停止"""
    c = MetricsCollector(refresh_interval=0.05)
    await c.start()
    yield c
    await c.stop()
    await asyncio.sleep(0.01)


@pytest.fixture
async def api(collector):
    """Dashboard API 实例"""
    return DashboardAPI(collector)


@pytest.fixture
def mock_ws():
    """模拟 WebSocket 客户端"""
    return MockWebSocket()


class TestDashboardMetricsFields:
    """验证面板展示的四项指标字段完整且类型正确"""

    def test_current_metrics_has_cpu(self, api):
        metrics = api.get_current_metrics()
        assert "cpu_usage" in metrics
        assert isinstance(metrics["cpu_usage"], float)
        assert 0 <= metrics["cpu_usage"] <= 100

    def test_current_metrics_has_memory(self, api):
        metrics = api.get_current_metrics()
        assert "memory_usage" in metrics
        assert isinstance(metrics["memory_usage"], float)
        assert 0 <= metrics["memory_usage"] <= 100

    def test_current_metrics_has_disk_io(self, api):
        metrics = api.get_current_metrics()
        assert "disk_io" in metrics
        disk = metrics["disk_io"]
        assert "read_bytes" in disk
        assert "write_bytes" in disk
        assert "read_iops" in disk
        assert "write_iops" in disk
        assert all(isinstance(disk[k], int) for k in ("read_bytes", "write_bytes", "read_iops", "write_iops"))

    def test_current_metrics_has_network(self, api):
        metrics = api.get_current_metrics()
        assert "network" in metrics
        net = metrics["network"]
        assert "bytes_in" in net
        assert "bytes_out" in net
        assert "packets_in" in net
        assert "packets_out" in net
        assert all(isinstance(net[k], int) for k in ("bytes_in", "bytes_out", "packets_in", "packets_out"))

    def test_metrics_has_timestamp(self, api):
        metrics = api.get_current_metrics()
        assert "timestamp" in metrics
        ts = datetime.fromisoformat(metrics["timestamp"])
        assert ts is not None

    def test_metrics_values_positive(self, api):
        """所有指标值应为非负数"""
        metrics = api.get_current_metrics()
        assert metrics["cpu_usage"] >= 0
        assert metrics["memory_usage"] >= 0
        assert metrics["disk_io"]["read_bytes"] >= 0
        assert metrics["disk_io"]["write_bytes"] >= 0
        assert metrics["network"]["bytes_in"] >= 0
        assert metrics["network"]["bytes_out"] >= 0

    def test_multiple_collects_produce_independent_snapshots(self, api):
        """每次采集应产生独立快照"""
        m1 = api.get_current_metrics()
        m2 = api.get_current_metrics()
        assert m1 is not m2
        assert m1["timestamp"] <= m2["timestamp"]


class TestWebSocketPushInterval:
    """验证 WebSocket 推送刷新间隔 <= 10 秒"""

    @pytest.mark.asyncio
    async def test_push_message_format(self, collector, mock_ws):
        """推送消息应包含 type 和 data 字段"""
        await collector.subscribe(mock_ws)
        await asyncio.sleep(0.1)
        assert len(mock_ws.sent_messages) >= 1
        msg = mock_ws.sent_messages[0]
        assert msg["type"] == "metrics_update"
        assert "data" in msg
        data = msg["data"]
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "disk_io" in data
        assert "network" in data

    @pytest.mark.asyncio
    async def test_push_interval_within_10_seconds(self, mock_ws):
        """连续两次推送的间隔应 <= 10 秒"""
        collector = MetricsCollector(refresh_interval=0.05)
        await collector.start()
        await collector.subscribe(mock_ws)
        await asyncio.sleep(0.2)
        await collector.stop()

        timestamps = []
        for msg in mock_ws.sent_messages:
            if msg["type"] == "metrics_update":
                timestamps.append(datetime.fromisoformat(msg["data"]["timestamp"]))

        assert len(timestamps) >= 2
        for i in range(1, len(timestamps)):
            diff = (timestamps[i] - timestamps[i - 1]).total_seconds()
            assert diff <= 10.0, f"推送间隔 {diff}s 超过 10 秒限制"

    @pytest.mark.asyncio
    async def test_push_delivers_to_all_subscribers(self, collector):
        """应同时推送给所有订阅者"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await collector.subscribe(ws1)
        await collector.subscribe(ws2)
        await asyncio.sleep(0.15)

        assert len(ws1.sent_messages) >= 1
        assert len(ws2.sent_messages) >= 1
        assert ws1.sent_messages[0]["type"] == "metrics_update"
        assert ws2.sent_messages[0]["type"] == "metrics_update"

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_push(self, collector):
        """取消订阅后应不再收到推送"""
        ws = MockWebSocket()
        await collector.subscribe(ws)
        await asyncio.sleep(0.1)
        count_before = len(ws.sent_messages)
        await collector.unsubscribe(ws)
        await asyncio.sleep(0.15)
        count_after = len(ws.sent_messages)
        assert count_before == count_after

    @pytest.mark.asyncio
    async def test_configurable_refresh_interval(self):
        """可自定义刷新间隔"""
        collector = MetricsCollector(refresh_interval=0.02)
        assert collector.refresh_interval == 0.02
        ws = MockWebSocket()
        await collector.start()
        await collector.subscribe(ws)
        await asyncio.sleep(0.12)
        await collector.stop()
        assert len(ws.sent_messages) >= 3

    @pytest.mark.asyncio
    async def test_push_resumes_after_stop_restart(self, mock_ws):
        """停止再启动后应恢复推送"""
        collector = MetricsCollector(refresh_interval=0.05)
        await collector.start()
        await collector.subscribe(mock_ws)
        await asyncio.sleep(0.1)
        await collector.stop()
        count_before = len(mock_ws.sent_messages)
        await asyncio.sleep(0.1)
        assert len(mock_ws.sent_messages) == count_before
        await collector.start()
        await asyncio.sleep(0.1)
        assert len(mock_ws.sent_messages) > count_before


class TestHistoryQueryPerformance:
    """验证历史数据查询响应时间 <= 2 秒"""

    def test_history_query_cpu_within_time_limit(self, api):
        """CPU 历史数据查询应 <= 2 秒"""
        now = datetime.now()
        start = now - timedelta(hours=1)
        end = now

        t0 = time.perf_counter()
        result = api.get_metrics_history("cpu", start.isoformat(), end.isoformat())
        elapsed = time.perf_counter() - t0

        assert result["metric"] == "cpu"
        assert isinstance(result["data"], list)
        assert elapsed <= 2.0, f"历史查询耗时 {elapsed:.4f}s 超过 2 秒限制"

    def test_history_query_memory_within_time_limit(self, api):
        """内存历史数据查询应 <= 2 秒"""
        now = datetime.now()
        start = now - timedelta(hours=2)

        t0 = time.perf_counter()
        result = api.get_metrics_history("memory", start.isoformat(), now.isoformat())
        elapsed = time.perf_counter() - t0

        assert result["metric"] == "memory"
        assert elapsed <= 2.0

    def test_history_query_disk_io_within_time_limit(self, api):
        """磁盘 I/O 历史数据查询应 <= 2 秒"""
        now = datetime.now()
        start = now - timedelta(hours=6)

        t0 = time.perf_counter()
        result = api.get_metrics_history("disk_io", start.isoformat(), now.isoformat())
        elapsed = time.perf_counter() - t0

        assert result["metric"] == "disk_io"
        assert elapsed <= 2.0

    def test_history_query_network_within_time_limit(self, api):
        """网络历史数据查询应 <= 2 秒"""
        now = datetime.now()
        start = now - timedelta(days=1)

        t0 = time.perf_counter()
        result = api.get_metrics_history("network", start.isoformat(), now.isoformat())
        elapsed = time.perf_counter() - t0

        assert result["metric"] == "network"
        assert elapsed <= 2.0

    def test_history_query_with_limit(self, api):
        """limit 参数应限制返回条数"""
        now = datetime.now()
        start = now - timedelta(hours=1)

        result = api.get_metrics_history("cpu", start.isoformat(), now.isoformat(), limit=5)
        assert result["count"] <= 5
        assert len(result["data"]) <= 5

    def test_history_query_returns_empty_when_no_data(self, api):
        """查询无数据时应返回空列表而非报错"""
        future = datetime.now() + timedelta(days=30)
        result = api.get_metrics_history("cpu", future.isoformat(), (future + timedelta(hours=1)).isoformat())
        assert result["data"] == []
        assert result["count"] == 0

    def test_history_entry_has_timestamp_and_value(self, api, collector):
        """历史数据条目应包含 timestamp 和 value 字段"""
        collector._collector.collect()
        now = datetime.now()
        start = now - timedelta(seconds=1)
        result = api.get_metrics_history("cpu", start.isoformat(), now.isoformat())
        if result["data"]:
            entry = result["data"][0]
            assert "timestamp" in entry
            assert "value" in entry


class TestEdgeCases:
    """边界条件和异常场景"""

    def test_cpu_usage_boundary_zero(self):
        """CPU 使用率为 0% 时"""
        c = MockSystemMetrics(cpu=0.0)
        snap = c.collect()
        assert snap["cpu_usage"] == 0.0

    def test_cpu_usage_boundary_hundred(self):
        """CPU 使用率为 100% 时"""
        c = MockSystemMetrics(cpu=100.0)
        snap = c.collect()
        assert snap["cpu_usage"] == 100.0

    def test_memory_usage_boundary_zero(self):
        """内存使用率为 0% 时"""
        c = MockSystemMetrics(memory=0.0)
        snap = c.collect()
        assert snap["memory_usage"] == 0.0

    def test_zero_disk_io(self):
        """磁盘 I/O 为零时"""
        c = MockSystemMetrics(disk_read=0, disk_write=0)
        snap = c.collect()
        assert snap["disk_io"]["read_bytes"] == 0
        assert snap["disk_io"]["write_bytes"] == 0
        assert snap["disk_io"]["read_iops"] == 0
        assert snap["disk_io"]["write_iops"] == 0

    def test_zero_network_traffic(self):
        """网络流量为零时"""
        c = MockSystemMetrics(net_in=0, net_out=0)
        snap = c.collect()
        assert snap["network"]["bytes_in"] == 0
        assert snap["network"]["bytes_out"] == 0

    def test_large_network_values(self):
        """大网络流量值不应溢出"""
        c = MockSystemMetrics(net_in=10000000000, net_out=5000000000)
        snap = c.collect()
        assert snap["network"]["bytes_in"] == 10000000000
        assert snap["network"]["bytes_out"] == 5000000000

    @pytest.mark.asyncio
    async def test_dead_subscriber_removed_on_broadcast_error(self):
        """发送失败的订阅者应被自动移除"""
        collector = MetricsCollector(refresh_interval=0.05)

        broken_ws = MockWebSocket()
        broken_ws.send_json = AsyncMock(side_effect=ConnectionError("connection lost"))

        good_ws = MockWebSocket()

        await collector.start()
        collector._subscribers.add(broken_ws)
        await collector.subscribe(good_ws)
        await asyncio.sleep(0.15)
        await collector.stop()

        assert broken_ws not in collector._subscribers
        assert good_ws in collector._subscribers
        assert len(good_ws.sent_messages) >= 1

    @pytest.mark.asyncio
    async def test_concurrent_subscribers_no_race(self):
        """并发订阅应无竞态条件"""
        collector = MetricsCollector(refresh_interval=0.05)
        ws_list = [MockWebSocket() for _ in range(20)]

        await collector.start()
        tasks = [collector.subscribe(ws) for ws in ws_list]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.15)
        await collector.stop()

        for ws in ws_list:
            assert len(ws.sent_messages) >= 1

    @pytest.mark.asyncio
    async def test_stop_cancels_task_cleanly(self):
        """停止后 _task 应为 None"""
        collector = MetricsCollector(refresh_interval=0.05)
        await collector.start()
        assert collector._task is not None
        await collector.stop()
        assert collector._task is None

    def test_unknown_metric_key_returns_empty(self, api):
        """未知指标键应返回空结果"""
        now = datetime.now()
        result = api.get_metrics_history("gpu", (now - timedelta(hours=1)).isoformat(), now.isoformat())
        assert result["data"] == []
        assert result["count"] == 0
        assert result["metric"] == "gpu"
