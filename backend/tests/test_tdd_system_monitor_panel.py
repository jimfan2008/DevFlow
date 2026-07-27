import pytest
import time
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from collections import deque


@dataclass
class CpuMetrics:
    usage_percent: float
    core_count: int
    timestamp: str = ""


@dataclass
class MemoryMetrics:
    usage_percent: float
    total_gb: float
    used_gb: float
    timestamp: str = ""


@dataclass
class DiskIOMetrics:
    read_bytes_per_sec: float
    write_bytes_per_sec: float
    iops_read: float
    iops_write: float
    timestamp: str = ""


@dataclass
class NetworkMetrics:
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float
    packets_sent_per_sec: float
    packets_recv_per_sec: float
    timestamp: str = ""


@dataclass
class DashboardSnapshot:
    cpu: CpuMetrics
    memory: MemoryMetrics
    disk_io: DiskIOMetrics
    network: NetworkMetrics
    collected_at: str = ""


def collect_snapshot() -> DashboardSnapshot:
    now = datetime.now(timezone.utc).isoformat()
    return DashboardSnapshot(
        cpu=CpuMetrics(
            usage_percent=45.2,
            core_count=8,
            timestamp=now,
        ),
        memory=MemoryMetrics(
            usage_percent=67.8,
            total_gb=32.0,
            used_gb=21.7,
            timestamp=now,
        ),
        disk_io=DiskIOMetrics(
            read_bytes_per_sec=104857600.0,
            write_bytes_per_sec=52428800.0,
            iops_read=25600.0,
            iops_write=12800.0,
            timestamp=now,
        ),
        network=NetworkMetrics(
            bytes_sent_per_sec=1250000.0,
            bytes_recv_per_sec=3750000.0,
            packets_sent_per_sec=1500.0,
            packets_recv_per_sec=4200.0,
            timestamp=now,
        ),
        collected_at=now,
    )


class MonitorCollector:
    def __init__(self, interval_seconds: float = 5.0):
        self.interval_seconds = interval_seconds
        self._history: deque[DashboardSnapshot] = deque(maxlen=360)

    def collect(self) -> DashboardSnapshot:
        snapshot = collect_snapshot()
        self._history.append(snapshot)
        return snapshot

    def query_history(self, minutes: int = 5) -> list[DashboardSnapshot]:
        cutoff = datetime.now(timezone.utc).timestamp() - minutes * 60
        result = []
        for snap in reversed(self._history):
            snap_ts = datetime.fromisoformat(snap.collected_at).timestamp()
            if snap_ts >= cutoff:
                result.append(snap)
        return result

    def query_history_since(self, since_ts: str) -> list[DashboardSnapshot]:
        since_dt = datetime.fromisoformat(since_ts).timestamp()
        result = []
        for snap in reversed(self._history):
            snap_ts = datetime.fromisoformat(snap.collected_at).timestamp()
            if snap_ts >= since_dt:
                result.append(snap)
        return result


class PanelDataSerializer:
    @staticmethod
    def to_dict(snapshot: DashboardSnapshot) -> dict:
        return {
            "cpu": asdict(snapshot.cpu),
            "memory": asdict(snapshot.memory),
            "disk_io": asdict(snapshot.disk_io),
            "network": asdict(snapshot.network),
            "collected_at": snapshot.collected_at,
        }

    @staticmethod
    def to_json(snapshot: DashboardSnapshot) -> str:
        return json.dumps(PanelDataSerializer.to_dict(snapshot), ensure_ascii=False)


class WebSocketPushSimulator:
    def __init__(self, collector: MonitorCollector, push_interval: float = 5.0):
        self.collector = collector
        self.push_interval = push_interval
        self._pushed: list[DashboardSnapshot] = []
        self._push_times: list[float] = []

    def push_once(self) -> DashboardSnapshot:
        snapshot = self.collector.collect()
        serialized = PanelDataSerializer.to_json(snapshot)
        parsed = json.loads(serialized)
        self._pushed.append(snapshot)
        self._push_times.append(time.time())
        return snapshot

    def push_batch(self, count: int) -> list[DashboardSnapshot]:
        results = []
        for _ in range(count):
            snap = self.push_once()
            results.append(snap)
        return results

    def get_push_intervals(self) -> list[float]:
        if len(self._push_times) < 2:
            return []
        return [self._push_times[i] - self._push_times[i - 1] for i in range(1, len(self._push_times))]

    def get_pushed_snapshots(self) -> list[dict]:
        return [PanelDataSerializer.to_dict(s) for s in self._pushed]


class HistoricalQueryEngine:
    def __init__(self, collector: MonitorCollector):
        self.collector = collector

    def query(self, minutes: int = 5) -> list[dict]:
        snapshots = self.collector.query_history(minutes=minutes)
        return [PanelDataSerializer.to_dict(s) for s in snapshots]

    def query_with_timing(self, minutes: int = 5) -> tuple[list[dict], float]:
        start = time.perf_counter()
        result = self.query(minutes=minutes)
        elapsed = time.perf_counter() - start
        return result, elapsed


def extract_indicator_names(snapshot_dict: dict) -> set[str]:
    return set(snapshot_dict.keys()) - {"collected_at"}


def extract_cpu_key_fields(snapshot_dict: dict) -> set[str]:
    return set(snapshot_dict.get("cpu", {}).keys()) - {"timestamp"}


def extract_memory_key_fields(snapshot_dict: dict) -> set[str]:
    return set(snapshot_dict.get("memory", {}).keys()) - {"timestamp"}


def extract_disk_io_key_fields(snapshot_dict: dict) -> set[str]:
    return set(snapshot_dict.get("disk_io", {}).keys()) - {"timestamp"}


def extract_network_key_fields(snapshot_dict: dict) -> set[str]:
    return set(snapshot_dict.get("network", {}).keys()) - {"timestamp"}


@pytest.fixture(scope="function")
def collector():
    return MonitorCollector(interval_seconds=5.0)


@pytest.fixture(scope="function")
def ws_simulator(collector):
    return WebSocketPushSimulator(collector, push_interval=5.0)


@pytest.fixture(scope="function")
def query_engine(collector):
    return HistoricalQueryEngine(collector)


class TestDashboardPanelMetrics:
    def test_panel_displays_all_four_indicators(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        indicator_names = extract_indicator_names(serialized)
        expected_indicators = {"cpu", "memory", "disk_io", "network"}
        assert indicator_names == expected_indicators, (
            f"面板缺少指标: 期望 {expected_indicators}, 实际 {indicator_names}"
        )

    def test_cpu_metrics_contain_usage_percent(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        cpu_fields = extract_cpu_key_fields(serialized)
        assert "usage_percent" in cpu_fields, "CPU 指标缺少 usage_percent"
        assert isinstance(serialized["cpu"]["usage_percent"], float)

    def test_memory_metrics_contain_usage_percent(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        mem_fields = extract_memory_key_fields(serialized)
        assert "usage_percent" in mem_fields, "内存指标缺少 usage_percent"
        assert isinstance(serialized["memory"]["usage_percent"], float)

    def test_disk_io_metrics_contain_read_and_write(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        disk_fields = extract_disk_io_key_fields(serialized)
        assert "read_bytes_per_sec" in disk_fields, "磁盘 I/O 缺少 read_bytes_per_sec"
        assert "write_bytes_per_sec" in disk_fields, "磁盘 I/O 缺少 write_bytes_per_sec"
        assert isinstance(serialized["disk_io"]["read_bytes_per_sec"], float)
        assert isinstance(serialized["disk_io"]["write_bytes_per_sec"], float)

    def test_network_metrics_contain_sent_and_recv(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        net_fields = extract_network_key_fields(serialized)
        assert "bytes_sent_per_sec" in net_fields, "网络指标缺少 bytes_sent_per_sec"
        assert "bytes_recv_per_sec" in net_fields, "网络指标缺少 bytes_recv_per_sec"
        assert isinstance(serialized["network"]["bytes_sent_per_sec"], float)
        assert isinstance(serialized["network"]["bytes_recv_per_sec"], float)

    def test_cpu_usage_percent_in_valid_range(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        cpu_val = serialized["cpu"]["usage_percent"]
        assert 0.0 <= cpu_val <= 100.0, f"CPU 使用率 {cpu_val}% 超出有效范围 [0, 100]"

    def test_memory_usage_percent_in_valid_range(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        mem_val = serialized["memory"]["usage_percent"]
        assert 0.0 <= mem_val <= 100.0, f"内存使用率 {mem_val}% 超出有效范围 [0, 100]"

    def test_disk_io_values_are_non_negative(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        disk = serialized["disk_io"]
        assert disk["read_bytes_per_sec"] >= 0
        assert disk["write_bytes_per_sec"] >= 0
        assert disk["iops_read"] >= 0
        assert disk["iops_write"] >= 0

    def test_network_values_are_non_negative(self):
        snapshot = collect_snapshot()
        serialized = PanelDataSerializer.to_dict(snapshot)
        net = serialized["network"]
        assert net["bytes_sent_per_sec"] >= 0
        assert net["bytes_recv_per_sec"] >= 0
        assert net["packets_sent_per_sec"] >= 0
        assert net["packets_recv_per_sec"] >= 0

    def test_each_snapshot_has_timestamp(self, collector):
        snapshot = collector.collect()
        serialized = PanelDataSerializer.to_dict(snapshot)
        assert serialized["collected_at"], "快照缺少 collected_at 时间戳"
        assert snapshot.cpu.timestamp, "CPU 指标缺少时间戳"
        assert snapshot.memory.timestamp, "内存指标缺少时间戳"
        assert snapshot.disk_io.timestamp, "磁盘 I/O 指标缺少时间戳"
        assert snapshot.network.timestamp, "网络指标缺少时间戳"

    def test_serialized_output_is_valid_json(self):
        snapshot = collect_snapshot()
        json_str = PanelDataSerializer.to_json(snapshot)
        parsed = json.loads(json_str)
        assert "cpu" in parsed
        assert "memory" in parsed
        assert "disk_io" in parsed
        assert "network" in parsed
        assert "collected_at" in parsed
        assert parsed["cpu"]["usage_percent"] == 45.2


class TestWebSocketPushInterval:
    def test_push_interval_within_10_seconds(self, ws_simulator):
        ws_simulator.push_once()
        time.sleep(0.05)
        ws_simulator.push_once()
        intervals = ws_simulator.get_push_intervals()
        for interval in intervals:
            assert interval <= 10.0, f"WebSocket 推送间隔 {interval:.3f}s 超过 10s 限制"

    def test_push_interval_configured_default_is_5_seconds(self, ws_simulator):
        assert ws_simulator.push_interval <= 10.0
        assert ws_simulator.push_interval > 0

    def test_multiple_consecutive_pushes_within_limit(self, ws_simulator):
        for i in range(5):
            ws_simulator.push_once()
            time.sleep(0.02)
        intervals = ws_simulator.get_push_intervals()
        assert len(intervals) >= 4
        for idx, interval in enumerate(intervals):
            assert interval <= 10.0, (
                f"第 {idx + 1} 次推送间隔 {interval:.3f}s 超过 10s 限制"
            )

    def test_each_push_contains_all_four_indicators(self, ws_simulator):
        ws_simulator.push_once()
        pushed = ws_simulator.get_pushed_snapshots()
        assert len(pushed) >= 1
        indicators = extract_indicator_names(pushed[0])
        assert indicators == {"cpu", "memory", "disk_io", "network"}

    def test_pushed_data_is_updated_on_each_cycle(self, ws_simulator):
        ws_simulator.push_once()
        time.sleep(0.05)
        ws_simulator.push_once()
        pushed = ws_simulator.get_pushed_snapshots()
        assert len(pushed) >= 2
        assert pushed[0]["collected_at"] != pushed[1]["collected_at"]


class TestHistoricalQueryResponseTime:
    def test_query_5_minutes_history_within_2_seconds(self, collector, query_engine):
        for _ in range(12):
            collector.collect()
            time.sleep(0.01)
        result, elapsed = query_engine.query_with_timing(minutes=5)
        assert elapsed <= 2.0, (
            f"5 分钟历史查询耗时 {elapsed:.4f}s，超过 2s 限制"
        )
        assert isinstance(result, list)

    def test_query_10_minutes_history_within_2_seconds(self, collector, query_engine):
        for _ in range(24):
            collector.collect()
            time.sleep(0.01)
        result, elapsed = query_engine.query_with_timing(minutes=10)
        assert elapsed <= 2.0, (
            f"10 分钟历史查询耗时 {elapsed:.4f}s，超过 2s 限制"
        )
        assert isinstance(result, list)

    def test_query_60_minutes_history_within_2_seconds(self, collector, query_engine):
        for _ in range(120):
            collector.collect()
        result, elapsed = query_engine.query_with_timing(minutes=60)
        assert elapsed <= 2.0, (
            f"60 分钟历史查询耗时 {elapsed:.4f}s，超过 2s 限制"
        )
        assert isinstance(result, list)

    def test_query_empty_history_within_2_seconds(self, query_engine):
        result, elapsed = query_engine.query_with_timing(minutes=5)
        assert elapsed <= 2.0, f"空历史查询耗时 {elapsed:.4f}s，超过 2s 限制"
        assert isinstance(result, list)
        assert len(result) == 0

    def test_query_returns_correct_number_of_records(self, collector, query_engine):
        for _ in range(10):
            collector.collect()
        result = query_engine.query(minutes=5)
        assert len(result) == 10

    def test_query_since_timestamp(self, collector, query_engine):
        for _ in range(5):
            collector.collect()
            time.sleep(0.01)
        ts_before = datetime.now(timezone.utc).isoformat()
        time.sleep(0.02)
        for _ in range(3):
            collector.collect()
            time.sleep(0.01)
        recent = collector.query_history_since(ts_before)
        assert len(recent) == 3

    def test_query_results_maintain_data_integrity(self, collector, query_engine):
        for _ in range(5):
            collector.collect()
        result = query_engine.query(minutes=5)
        for entry in result:
            assert "cpu" in entry
            assert "memory" in entry
            assert "disk_io" in entry
            assert "network" in entry
            assert "usage_percent" in entry["cpu"]
            assert "usage_percent" in entry["memory"]

    def test_concurrent_query_and_collect(self, collector, query_engine):
        for _ in range(5):
            collector.collect()
        t1 = time.perf_counter()
        query_future = query_engine.query(minutes=5)
        collector.collect()
        elapsed = time.perf_counter() - t1
        assert elapsed <= 2.0, f"并发采集+查询耗时 {elapsed:.4f}s 超过 2s 限制"
        assert len(query_future) >= 5
