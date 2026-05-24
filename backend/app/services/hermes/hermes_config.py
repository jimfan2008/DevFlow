from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from app.services.hermes.types import (
    HermesConfig,
    APIServerConfig,
    ProviderCredential,
    ProfileInfo,
)

logger = logging.getLogger("devflow.hermes.config")


class HermesConfigReader:
    def __init__(self, hermes_home: str = None):
        if hermes_home:
            self._home = Path(hermes_home)
        else:
            self._home = Path(os.environ.get("HERMES_PROFILES_PATH", "/hermes-home"))

    @property
    def home(self) -> Path:
        return self._home

    def read_config(self, profile_name: str = "default") -> Optional[HermesConfig]:
        config_path = self._resolve_config_path(profile_name)
        if not config_path or not config_path.exists():
            logger.debug(f"config.yaml not found at {config_path}")
            return None
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            env_data = self.read_env(profile_name)
            return HermesConfig.from_raw(raw, env_data)
        except Exception as e:
            logger.error(f"Failed to parse config.yaml: {e}")
            return None

    def read_auth_pool(self, profile_name: str = "default") -> List[ProviderCredential]:
        auth_path = self._resolve_auth_path(profile_name)
        if not auth_path or not auth_path.exists():
            return []
        try:
            with open(auth_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._parse_auth_data(data)
        except Exception as e:
            logger.error(f"Failed to parse auth.json: {e}")
            return []

    def read_env(self, profile_name: str = "default") -> Dict[str, str]:
        env_path = self._resolve_env_path(profile_name)
        if not env_path or not env_path.exists():
            return {}
        result = {}
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("\"'")
                        result[key] = value
        except Exception as e:
            logger.error(f"Failed to read .env: {e}")
        return result

    def scan_profiles(self) -> List[ProfileInfo]:
        profiles_dir = self._home / "profiles"
        profiles = [ProfileInfo(name="default", path=str(self._home), is_active=True, has_config=(self._home / "config.yaml").exists())]
        if profiles_dir.exists() and profiles_dir.is_dir():
            for d in sorted(profiles_dir.iterdir()):
                if d.is_dir():
                    has_config = (d / "config.yaml").exists()
                    profiles.append(ProfileInfo(name=d.name, path=str(d), has_config=has_config))
        return profiles

    def read_soul(self, profile_name: str = "default") -> str:
        profile_dir = self._resolve_profile_dir(profile_name)
        if not profile_dir:
            return ""
        soul_path = profile_dir / "SOUL.md"
        if not soul_path.exists():
            agent_dir = profile_dir / "hermes-agent"
            soul_path = agent_dir / "SOUL.md"
        if not soul_path.exists():
            return ""
        try:
            return soul_path.read_text(encoding="utf-8")[:300]
        except Exception:
            return ""

    def extract_api_server_config(self, config: HermesConfig) -> APIServerConfig:
        return config.api_server

    @staticmethod
    def mask_api_key(key: str) -> str:
        if not key or len(key) < 8:
            return "***" if key else ""
        return f"{key[:3]}...{key[-3:]}"

    def _resolve_profile_dir(self, profile_name: str) -> Optional[Path]:
        if profile_name == "default":
            return self._home
        d = self._home / "profiles" / profile_name
        return d if d.exists() else None

    def _resolve_config_path(self, profile_name: str) -> Optional[Path]:
        d = self._resolve_profile_dir(profile_name)
        return d / "config.yaml" if d else None

    def _resolve_auth_path(self, profile_name: str) -> Optional[Path]:
        d = self._resolve_profile_dir(profile_name)
        return d / "auth.json" if d else None

    def _resolve_env_path(self, profile_name: str) -> Optional[Path]:
        d = self._resolve_profile_dir(profile_name)
        return d / ".env" if d else None

    @staticmethod
    def _parse_auth_data(data: Dict) -> List[ProviderCredential]:
        creds = []
        pool = data.get("credential_pool", {})
        if isinstance(pool, dict):
            for provider, info in pool.items():
                api_key = ""
                base_url = ""
                if isinstance(info, dict):
                    api_key = info.get("api_key", "")
                    base_url = info.get("base_url", "")
                elif isinstance(info, str):
                    api_key = info
                if api_key:
                    creds.append(ProviderCredential(provider=provider, api_key=api_key, base_url=base_url))
        providers = data.get("providers", {})
        if isinstance(providers, dict):
            for provider, info in providers.items():
                if isinstance(info, dict):
                    api_key = info.get("access_token", "") or info.get("api_key", "")
                    base_url = info.get("base_url", "")
                    if api_key:
                        creds.append(ProviderCredential(provider=provider, api_key=api_key, base_url=base_url))
        return creds
