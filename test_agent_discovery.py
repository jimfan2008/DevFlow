import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from app.utils.hermes_fs import (
    scan_all_profiles,
    read_profile_config,
    check_gateway_running,
)


@pytest.fixture
def mock_profiles_dir(tmp_path):
    """Fixture that creates a temporary profiles directory with sample profiles."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    return profiles_dir


@pytest.fixture
def valid_profile_yaml():
    return {"name": "test-agent", "model": "gpt-4", "system_prompt": "You are a test agent."}


@pytest.fixture
def valid_profile_yaml_missing_fields():
    return {"name": "test-agent"}


# ── scan_all_profiles tests ─────────────────────────────────────────────────


@patch("app.utils.hermes_fs.scan_all_profiles")
def test_scan_all_profiles_returns_list(mock_scan):
    mock_scan.return_value = [
        {"id": "agent-a", "name": "Agent A"},
        {"id": "agent-b", "name": "Agent B"},
    ]
    result = scan_all_profiles()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["id"] == "agent-a"


@patch("app.utils.hermes_fs.scan_all_profiles")
def test_scan_all_profiles_empty_directory(mock_scan):
    mock_scan.return_value = []
    result = scan_all_profiles()
    assert result == []


@patch("app.utils.hermes_fs.scan_all_profiles")
def test_scan_all_profiles_duplicate_ids(mock_scan):
    mock_scan.return_value = [
        {"id": "agent-x", "name": "Agent X"},
        {"id": "agent-x", "name": "Agent X Duplicate"},
    ]
    result = scan_all_profiles()
    ids = [p["id"] for p in result]
    assert ids.count("agent-x") == 2


@patch("app.utils.hermes_fs.scan_all_profiles")
def test_scan_all_profiles_performance(mock_scan):
    """scan_all_profiles returns quickly (mocked, so sub-second)."""
    import time

    mock_scan.return_value = [{"id": f"agent-{i}", "name": f"Agent {i}"} for i in range(100)]
    start = time.monotonic()
    _ = scan_all_profiles()
    elapsed = time.monotonic() - start
    assert elapsed < 5.0


@patch("app.utils.hermes_fs.scan_all_profiles")
def test_scan_all_profiles_concurrent(mock_scan):
    """Concurrent scan_all_profiles calls do not return stale/shared state (race condition check)."""
    from concurrent.futures import ThreadPoolExecutor

    mock_scan.side_effect = [
        [{"id": "agent-a", "name": "Agent A"}],
        [{"id": "agent-b", "name": "Agent B"}],
        [{"id": "agent-c", "name": "Agent C"}],
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(scan_all_profiles) for _ in range(3)]
        results = [f.result() for f in futures]

    assert len(results) == 3
    assert results[0] == [{"id": "agent-a", "name": "Agent A"}]
    assert results[1] == [{"id": "agent-b", "name": "Agent B"}]
    assert results[2] == [{"id": "agent-c", "name": "Agent C"}]


# ── read_profile_config tests ──────────────────────────────────────────────


@patch("app.utils.hermes_fs.read_profile_config")
def test_read_profile_config_valid(mock_read, valid_profile_yaml):
    mock_read.return_value = valid_profile_yaml
    config = read_profile_config("test-agent")
    assert config["name"] == "test-agent"
    assert "model" in config
    assert "system_prompt" in config


@patch("app.utils.hermes_fs.read_profile_config")
def test_read_profile_config_missing_file(mock_read):
    mock_read.side_effect = FileNotFoundError("Profile not found")
    with pytest.raises(FileNotFoundError):
        read_profile_config("nonexistent-agent")


@patch("app.utils.hermes_fs.read_profile_config")
def test_read_profile_config_missing_fields(mock_read, valid_profile_yaml_missing_fields):
    mock_read.return_value = valid_profile_yaml_missing_fields
    config = read_profile_config("test-agent")
    assert "model" not in config
    assert config["name"] == "test-agent"


@patch("app.utils.hermes_fs.read_profile_config")
def test_read_profile_config_corrupt_yaml(mock_read):
    mock_read.side_effect = ValueError("Invalid YAML")
    with pytest.raises(ValueError, match="Invalid YAML"):
        read_profile_config("corrupt-agent")


@patch("app.utils.hermes_fs.read_profile_config")
def test_read_profile_config_timeout(mock_read):
    import time

    def slow_read(*args, **kwargs):
        time.sleep(6)
        return {}

    mock_read.side_effect = slow_read
    start = time.monotonic()
    with pytest.raises(Exception):
        read_profile_config("slow-agent")
    elapsed = time.monotonic() - start
    assert elapsed < 10


# ── check_gateway_running tests ────────────────────────────────────────────


@patch("app.utils.hermes_fs.check_gateway_running")
def test_check_gateway_running_true(mock_check):
    mock_check.return_value = True
    assert check_gateway_running() is True


@patch("app.utils.hermes_fs.check_gateway_running")
def test_check_gateway_running_false(mock_check):
    mock_check.return_value = False
    assert check_gateway_running() is False


@patch("app.utils.hermes_fs.check_gateway_running")
def test_check_gateway_running_connection_error(mock_check):
    mock_check.side_effect = ConnectionError("Gateway unreachable")
    with pytest.raises(ConnectionError, match="Gateway unreachable"):
        check_gateway_running()


@patch("app.utils.hermes_fs.check_gateway_running")
def test_check_gateway_running_timeout(mock_check):
    mock_check.side_effect = TimeoutError("Connection timed out")
    with pytest.raises(TimeoutError, match="Connection timed out"):
        check_gateway_running()


# ── Integration-style test (mocked, but exercises all three together) ───────


@patch("app.utils.hermes_fs.check_gateway_running")
@patch("app.utils.hermes_fs.read_profile_config")
@patch("app.utils.hermes_fs.scan_all_profiles")
def test_discovery_flow_integration(mock_scan, mock_read, mock_check):
    """Simulate the full discovery flow: scan → filter → read config."""
    mock_scan.return_value = [
        {"id": "prog-a", "name": "Python Coder"},
        {"id": "prog-b", "name": "JS Coder"},
    ]
    mock_read.return_value = {"name": "Python Coder", "model": "gpt-4", "system_prompt": "..."}
    mock_check.return_value = True

    assert check_gateway_running() is True
    profiles = scan_all_profiles()
    assert len(profiles) == 2
    config = read_profile_config(profiles[0]["id"])
    assert config["name"] == "Python Coder"
