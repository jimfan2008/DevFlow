import os
import sys
import json
import yaml
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.config import settings


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _get_windows_hermes_dirs() -> List[Path]:
    dirs = []
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        p = Path(local_app) / "hermes"
        if p.exists():
            dirs.append(p)
    roaming_app = os.environ.get("APPDATA")
    if roaming_app:
        p = Path(roaming_app) / "hermes"
        if p.exists():
            dirs.append(p)
    home = Path.home()
    p = home / ".hermes"
    if p.exists():
        dirs.append(p)
    return dirs


def get_hermes_home_path() -> Path:
    env_path = os.environ.get("HERMES_PROFILES_PATH")
    if env_path:
        p = Path(env_path)
        if (p / "config.yaml").exists():
            return p
        if p.name == "profiles" and p.parent.exists():
            return p.parent
        return p

    if _is_windows():
        dirs = _get_windows_hermes_dirs()
        if dirs:
            return dirs[0]

    return get_profiles_path()


def get_profiles_path() -> Path:
    env_path = os.environ.get("HERMES_PROFILES_PATH")
    if env_path:
        return Path(env_path)

    if _is_windows():
        dirs = _get_windows_hermes_dirs()
        if dirs:
            return dirs[0]
        return Path.home() / ".hermes"

    home_hermes = Path.home() / ".hermes"
    if home_hermes.exists():
        return home_hermes

    return Path.home() / ".hermes"


def get_global_default_config_path() -> Path:
    return get_hermes_home_path() / "config.yaml"


def read_profile_config(profile_name: str) -> Optional[Dict[str, Any]]:
    hermes_home = get_hermes_home_path()

    if profile_name == "default":
        config_path = hermes_home / "config.yaml"
    else:
        profiles_dir = hermes_home / "profiles"
        config_path = profiles_dir / profile_name / "config.yaml"
        if not config_path.exists():
            config_path = hermes_home / profile_name / "config.yaml"

    try:
        if not config_path.exists():
            return None
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error reading config for {profile_name}: {e}")
        return None


def read_profile_soul(profile_name: str) -> Optional[str]:
    hermes_home = get_hermes_home_path()
    soul_path = hermes_home / profile_name / "SOUL.md"
    if not soul_path.exists():
        soul_path = hermes_home / "profiles" / profile_name / "SOUL.md"

    try:
        if not soul_path.exists():
            return None
        with open(soul_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.strip().split("\n")
        meaningful_lines = [line for line in lines if not line.strip().startswith("<!--")]
        return "\n".join(meaningful_lines[:5]) if meaningful_lines else None
    except Exception as e:
        print(f"Error reading SOUL.md for {profile_name}: {e}")
        return None


def check_gateway_running(profile_name: str = "default") -> bool:
    hermes_home = get_hermes_home_path()

    lock_file = hermes_home / "gateway.lock"
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                lock_data = json.load(f)
            pid = lock_data.get("pid")
            kind = lock_data.get("kind", "")
            if pid and "gateway" in kind:
                if _is_windows():
                    try:
                        result = subprocess.run(
                            ["tasklist", "/FI", f"PID eq {pid}"],
                            capture_output=True, text=True, timeout=5,
                        )
                        return str(pid) in result.stdout
                    except Exception:
                        return True
                else:
                    try:
                        os.kill(pid, 0)
                        return True
                    except (ProcessLookupError, PermissionError):
                        return True
                    except Exception:
                        return True
        except Exception:
            pass

    pid_file = hermes_home / "gateway.pid"
    if pid_file.exists():
        try:
            with open(pid_file, "r") as f:
                content = f.read().strip()
            return len(content) > 0
        except Exception:
            pass

    state_file = hermes_home / "gateway_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
            return state.get("gateway_state") == "running"
        except Exception:
            pass

    return False


def get_gateway_port_from_config(config: Dict[str, Any]) -> Optional[int]:
    try:
        port = config.get("platforms", {}).get("api_server", {}).get("extra", {}).get("port")
        if port:
            return int(port)
    except (ValueError, TypeError):
        pass

    try:
        port = config.get("gateway", {}).get("port")
        if port:
            return int(port)
    except (ValueError, TypeError):
        pass

    try:
        port = config.get("gateway_port")
        if port:
            return int(port)
    except (ValueError, TypeError):
        pass

    return None


def _find_gateway_port_from_process() -> Optional[int]:
    try:
        if _is_windows():
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.splitlines():
                if "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        addr = parts[1]
                        if ":" in addr:
                            port_str = addr.rsplit(":", 1)[-1]
                            try:
                                port = int(port_str)
                                if 1024 < port < 65536:
                                    lock_file = get_hermes_home_path() / "gateway.lock"
                                    if lock_file.exists():
                                        with open(lock_file, "r") as f:
                                            lock_data = json.load(f)
                                        if str(lock_data.get("pid")) == pid:
                                            return port
                            except ValueError:
                                continue
    except Exception:
        pass
    return None


def get_gateway_port(config: Optional[Dict[str, Any]] = None) -> Optional[int]:
    if config:
        port = get_gateway_port_from_config(config)
        if port:
            return port

    port = _find_gateway_port_from_process()
    if port:
        return port

    return None


def get_gateway_api_key(config: Dict[str, Any]) -> Optional[str]:
    try:
        key = config.get("platforms", {}).get("api_server", {}).get("key")
        if key:
            return key
    except Exception:
        pass

    try:
        key = config.get("platforms", {}).get("api_server", {}).get("extra", {}).get("key")
        if key:
            return key
    except Exception:
        pass

    try:
        key = config.get("gateway", {}).get("api_key")
        if key:
            return key
    except Exception:
        pass

    try:
        key = config.get("api_key")
        if key:
            return key
    except Exception:
        pass

    return None


def scan_all_profiles() -> List[Dict[str, Any]]:
    hermes_home = get_hermes_home_path()
    profiles = []

    try:
        if not hermes_home.exists():
            print(f"[hermes_fs] Hermes home path does not exist: {hermes_home}")
            return profiles

        print(f"[hermes_fs] Scanning Hermes home: {hermes_home}")

        config = read_profile_config("default")
        if config:
            gateway_port = get_gateway_port(config)
            api_key = get_gateway_api_key(config)
            is_running = check_gateway_running("default")
            print(f"[hermes_fs] Default profile found: port={gateway_port}, running={is_running}")

            profiles.append({
                "name": "default",
                "model_default": config.get("model", {}).get("default"),
                "model_provider": config.get("model", {}).get("provider"),
                "gateway_port": gateway_port,
                "api_key": api_key,
                "personality": None,
                "is_running": is_running,
                "config_path": str(hermes_home / "config.yaml"),
            })

        profiles_dir = hermes_home / "profiles"
        if profiles_dir.exists():
            for item in profiles_dir.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    profile_name = item.name
                    if profile_name == "default":
                        continue
                    config = read_profile_config(profile_name)
                    if config:
                        gateway_port = get_gateway_port(config)
                        api_key = get_gateway_api_key(config)
                        is_running = check_gateway_running(profile_name)
                        soul = read_profile_soul(profile_name)

                        profiles.append({
                            "name": profile_name,
                            "model_default": config.get("model", {}).get("default"),
                            "model_provider": config.get("model", {}).get("provider"),
                            "gateway_port": gateway_port,
                            "api_key": api_key,
                            "personality": soul,
                            "is_running": is_running,
                            "config_path": str(item / "config.yaml"),
                        })

    except Exception as e:
        print(f"Error scanning profiles: {e}")

    return profiles
