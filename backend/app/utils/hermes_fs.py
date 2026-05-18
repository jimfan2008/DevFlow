import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from app.config import settings


def get_hermes_home_path() -> Path:
    return get_profiles_path().parent


def get_global_default_config_path() -> Path:
    return get_hermes_home_path() / "config.yaml"


def get_profiles_path() -> Path:
    path = settings.HERMES_PROFILES_PATH
    import platform
    if platform.system() == 'Windows' and path.startswith('/home/'):
        wsl_distro = settings.WSL_DISTRO_NAME
        windows_path = f"\\\\wsl.localhost\\{wsl_distro}{path.replace('/', '\\')}"
        return Path(windows_path)
    return Path(path)


def read_profile_config(profile_name: str) -> Optional[Dict[str, Any]]:
    config_path = get_profiles_path() / profile_name / "config.yaml"
    if profile_name == "default" and not config_path.exists():
        config_path = get_global_default_config_path()

    try:
        if not config_path.exists():
            return None

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config
    except Exception as e:
        print(f"Error reading config for {profile_name}: {e}")
        return None


def read_profile_soul(profile_name: str) -> Optional[str]:
    soul_path = get_profiles_path() / profile_name / "SOUL.md"

    try:
        if not soul_path.exists():
            return None

        with open(soul_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.strip().split('\n')
        meaningful_lines = [line for line in lines if not line.strip().startswith('<!--')]
        return '\n'.join(meaningful_lines[:5]) if meaningful_lines else None
    except Exception as e:
        print(f"Error reading SOUL.md for {profile_name}: {e}")
        return None


def check_gateway_running(profile_name: str) -> bool:
    if profile_name == "default":
        hermes_home = get_hermes_home_path()
        state_file = hermes_home / "gateway_state.json"
        pid_file = hermes_home / "gateway.pid"
    else:
        state_file = get_profiles_path() / profile_name / "gateway_state.json"
        pid_file = get_profiles_path() / profile_name / "gateway.pid"

    try:
        if state_file.exists():
            import json
            with open(state_file, 'r') as f:
                state = json.load(f)
            return state.get('gateway_state') == 'running'

        if pid_file.exists():
            with open(pid_file, 'r') as f:
                content = f.read().strip()
            return len(content) > 0

        return False
    except Exception:
        return False


def get_gateway_port_from_config(config: Dict[str, Any]) -> Optional[int]:
    try:
        port = config.get('platforms', {}).get('api_server', {}).get('extra', {}).get('port')
        return int(port) if port else None
    except (ValueError, TypeError):
        return None


def get_gateway_api_key(config: Dict[str, Any]) -> Optional[str]:
    try:
        return config.get('platforms', {}).get('api_server', {}).get('key', '')
    except Exception:
        return None


def scan_all_profiles() -> list:
    profiles_path = get_profiles_path()
    profiles = []

    try:
        if not profiles_path.exists():
            print(f"Profiles path does not exist: {profiles_path}")
            return profiles

        existing_names = set()

        for item in profiles_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                profile_name = item.name
                config = read_profile_config(profile_name)

                if config:
                    existing_names.add(profile_name)
                    gateway_port = get_gateway_port_from_config(config)
                    api_key = get_gateway_api_key(config)
                    is_running = check_gateway_running(profile_name)
                    soul = read_profile_soul(profile_name)

                    profiles.append({
                        'name': profile_name,
                        'model_default': config.get('model', {}).get('default'),
                        'model_provider': config.get('model', {}).get('provider'),
                        'gateway_port': gateway_port,
                        'api_key': api_key,
                        'personality': soul,
                        'is_running': is_running,
                        'config_path': str(item / 'config.yaml')
                    })

        if "default" not in existing_names:
            default_config = read_profile_config("default")
            if default_config:
                profiles.append({
                    'name': 'default',
                    'model_default': default_config.get('model', {}).get('default'),
                    'model_provider': default_config.get('model', {}).get('provider'),
                    'gateway_port': get_gateway_port_from_config(default_config),
                    'api_key': get_gateway_api_key(default_config),
                    'personality': None,
                    'is_running': check_gateway_running("default"),
                    'config_path': str(get_global_default_config_path())
                })

    except Exception as e:
        print(f"Error scanning profiles: {e}")

    return profiles
