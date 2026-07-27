"""
System monitoring panel data refresh test cases.
Verifies CPU, memory, disk I/O, network traffic metrics and real-time refresh.
"""

import json
import time
import threading
from datetime import datetime, timedelta, timezone


# ==============================================================================
# Mock classes
# ==============================================================================

class MockWebSocket:
    """Mock WebSocket connection."""

    def __init__(self):
        self.messages = []
        self.connected = False
        self._lock = threading.Lock()

    def connect(self):
        self.connected = True

    def send(self, data):
        with self._lock:
            self.messages.append({
                "direction": "outbound",
                "data": data,
                "timestamp": time.time(),
            })

    def receive(self, timeout=5):
        end_time = time.time() + timeout
        while time.time() < end_time:
            with self._lock:
                inbound = [m for m in self.messages if m["direction"] == "inbound"]
                if inbound:
                    return inbound[-1]["data"]
            time.sleep(0.05)
        return None

    def push_message(self, data):
        with self._lock:
            self.messages.append({
                "direction": "inbound",
                "data": data,
                "timestamp": time.time(),
            })

    def close(self):
        self.connected = False

    def get_inbound_messages(self):
        with self._lock:
            return [m for m in self.messages if m["direction"] == "inbound"]


class SystemMonitorPanel:
    """System monitoring panel under test."""

    METRICS = ["cpu_usage", "memory_usage", "disk_io", "network_traffic"]

    def __init__(self, websocket=None, refresh_interval=5.0):
        self.ws = websocket or MockWebSocket()
        self.refresh_interval = refresh_interval
        self.current_data = {}
        self.history = []
        self._running = False
        self._thread = None

    def _fetch_metrics(self):
        """Fetch current metrics data."""
        return {
            "cpu_usage": 45.6,
            "memory_usage": 72.3,
            "disk_io": {"read_mbps": 120.5, "write_mbps": 45.2},
            "network_traffic": {"inbound_mbps": 200.1, "outbound_mbps": 80.3},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_current_metrics(self):
        """Get current monitoring data."""
        data = self._fetch_metrics()
        self.current_data = data
        return data

    def start_refresh(self):
        """Start periodic refresh."""
        self._running = True
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def _refresh_loop(self):
        """Periodic refresh loop."""
        while self._running:
            data = self._fetch_metrics()
            self.current_data = data
            self.history.append(data)
            self.ws.push_message(json.dumps(data))
            time.sleep(self.refresh_interval)

    def stop_refresh(self):
        """Stop periodic refresh."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def get_history(self, since=None):
        """Query historical data."""
        if since is None:
            return self.history
        return [
            item for item in self.history
            if datetime.fromisoformat(item["timestamp"]) >= since
        ]


# ==============================================================================
# Fixtures
# ==============================================================================

def create_panel(refresh_interval=5.0):
    """Create a test panel instance."""
    ws = MockWebSocket()
    panel = SystemMonitorPanel(websocket=ws, refresh_interval=refresh_interval)
    return panel


# ==============================================================================
# Test: panel displays all four metrics
# ==============================================================================

def test_panel_displays_all_four_metrics():
    """Panel shows CPU, memory, disk I/O, network traffic."""
    panel = create_panel()
    data = panel.get_current_metrics()

    assert "cpu_usage" in data, "Missing cpu_usage metric"
    assert "memory_usage" in data, "Missing memory_usage metric"
    assert "disk_io" in data, "Missing disk_io metric"
    assert "network_traffic" in data, "Missing network_traffic metric"

    assert isinstance(data["cpu_usage"], (int, float))
    assert 0 <= data["cpu_usage"] <= 100

    assert isinstance(data["memory_usage"], (int, float))
    assert 0 <= data["memory_usage"] <= 100

    assert isinstance(data["disk_io"], dict)
    assert "read_mbps" in data["disk_io"]
    assert "write_mbps" in data["disk_io"]

    assert isinstance(data["network_traffic"], dict)
    assert "inbound_mbps" in data["network_traffic"]
    assert "outbound_mbps" in data["network_traffic"]


# ==============================================================================
# Test: WebSocket push interval <= 10 seconds
# ==============================================================================

def test_websocket_push_interval_within_10_seconds():
    """WebSocket push refresh interval must be <= 10 seconds."""
    interval = 2.0
    panel = create_panel(refresh_interval=interval)
    panel.start_refresh()

    time.sleep(interval * 2.5)
    panel.stop_refresh()

    inbound = panel.ws.get_inbound_messages()
    assert len(inbound) >= 2, (
        f"Expected at least 2 push messages, got {len(inbound)}"
    )

    timestamps = [msg["timestamp"] for msg in inbound]
    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    for gap in gaps:
        assert gap <= 10.0, (
            f"Push interval {gap:.2f}s exceeds 10s limit"
        )
        assert gap >= interval * 0.8, (
            f"Push interval {gap:.2f}s is less than expected minimum {interval * 0.8}"
        )


def test_websocket_pushes_valid_json():
    """WebSocket pushes valid JSON containing all four metrics."""
    panel = create_panel(refresh_interval=1.0)
    panel.start_refresh()

    time.sleep(2.5)
    panel.stop_refresh()

    inbound = panel.ws.get_inbound_messages()
    assert len(inbound) >= 1, "No push messages received"

    for msg in inbound:
        parsed = json.loads(msg["data"])
        assert "cpu_usage" in parsed
        assert "memory_usage" in parsed
        assert "disk_io" in parsed
        assert "network_traffic" in parsed
        assert "timestamp" in parsed


# ==============================================================================
# Test: history query response time <= 2 seconds
# ==============================================================================

def test_history_query_response_time_within_2_seconds():
    """History data query response time must be <= 2 seconds."""
    panel = create_panel(refresh_interval=0.5)
    panel.start_refresh()

    time.sleep(3.0)
    panel.stop_refresh()

    start = time.time()
    result = panel.get_history()
    elapsed = time.time() - start

    assert len(result) >= 4, (
        f"Expected at least 4 history items, got {len(result)}"
    )
    assert elapsed <= 2.0, (
        f"History query took {elapsed:.4f}s, exceeding 2s limit"
    )


def test_history_query_with_since_filter():
    """History query supports since filter with response <= 2 seconds."""
    panel = create_panel(refresh_interval=0.5)
    panel.start_refresh()

    time.sleep(3.0)
    panel.stop_refresh()

    since = datetime.now(timezone.utc) - timedelta(seconds=2)
    start = time.time()
    result = panel.get_history(since=since)
    elapsed = time.time() - start

    assert len(result) >= 1, "Expected at least 1 item after since filter"
    assert elapsed <= 2.0, (
        f"Filtered history query took {elapsed:.4f}s, exceeding 2s limit"
    )

    for item in result:
        item_time = datetime.fromisoformat(item["timestamp"])
        assert item_time >= since, (
            f"Returned data {item_time} is before since={since}"
        )


# ==============================================================================
# Test: metric data validity
# ==============================================================================

def test_cpu_usage_range_valid():
    """CPU usage is in range 0-100."""
    panel = create_panel()
    data = panel.get_current_metrics()
    assert 0 <= data["cpu_usage"] <= 100


def test_memory_usage_range_valid():
    """Memory usage is in range 0-100."""
    panel = create_panel()
    data = panel.get_current_metrics()
    assert 0 <= data["memory_usage"] <= 100


def test_disk_io_has_non_negative_values():
    """Disk I/O read/write values are non-negative."""
    panel = create_panel()
    data = panel.get_current_metrics()
    assert data["disk_io"]["read_mbps"] >= 0
    assert data["disk_io"]["write_mbps"] >= 0


def test_network_traffic_has_non_negative_values():
    """Network traffic inbound/outbound values are non-negative."""
    panel = create_panel()
    data = panel.get_current_metrics()
    assert data["network_traffic"]["inbound_mbps"] >= 0
    assert data["network_traffic"]["outbound_mbps"] >= 0


# ==============================================================================
# Test: no push after stop
# ==============================================================================

def test_no_push_after_stop():
    """No new messages are pushed after stopping refresh."""
    panel = create_panel(refresh_interval=0.5)
    panel.start_refresh()

    time.sleep(1.5)
    count_before = len(panel.ws.get_inbound_messages())
    panel.stop_refresh()

    time.sleep(2.0)
    count_after = len(panel.ws.get_inbound_messages())
    assert count_after == count_before, (
        f"New messages arrived after stop: {count_before} -> {count_after}"
    )
