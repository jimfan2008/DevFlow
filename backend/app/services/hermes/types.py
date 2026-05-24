from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

ConnectionMode = Literal["api_server", "socketio_bff", "cli_fallback"]
HealthStatus = Literal["online", "offline", "degraded", "unknown"]


@dataclass(frozen=True)
class APIServerConfig:
    enabled: bool = False
    host: str = "localhost"
    port: int = 8642
    api_key: str = ""

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def v1_url(self) -> str:
        return f"{self.base_url}/v1"


@dataclass(frozen=True)
class ProviderCredential:
    provider: str
    api_key: str = ""
    base_url: str = ""
    is_available: bool = True


@dataclass(frozen=True)
class HermesConfig:
    model_base_url: str = ""
    model_api_key: str = ""
    model_default: str = ""
    api_server: APIServerConfig = field(default_factory=APIServerConfig)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, data: Dict[str, Any], env_data: Dict[str, str] = None) -> "HermesConfig":
        model_cfg = data.get("model", {})
        api_server_cfg = data.get("api_server", {})
        env_data = env_data or {}

        enabled = False
        if isinstance(api_server_cfg.get("enabled"), bool):
            enabled = api_server_cfg["enabled"]
        elif env_data.get("API_SERVER_ENABLED", "").lower() in ("true", "1", "yes"):
            enabled = True

        api_key = api_server_cfg.get("key", "") or env_data.get("API_SERVER_KEY", "")
        port = int(api_server_cfg.get("port", 0) or env_data.get("API_SERVER_PORT", "8642"))
        host = api_server_cfg.get("host", "") or env_data.get("API_SERVER_HOST", "0.0.0.0")

        return cls(
            model_base_url=model_cfg.get("base_url", ""),
            model_api_key=model_cfg.get("api_key", ""),
            model_default=model_cfg.get("default", ""),
            api_server=APIServerConfig(enabled=enabled, host=host, port=port, api_key=api_key),
            raw=data,
        )


@dataclass(frozen=True)
class APIServerInfo:
    reachable: bool = False
    base_url: str = ""
    model: str = ""
    health_ok: bool = False
    latency_ms: float = 0.0
    error: str = ""


@dataclass(frozen=True)
class DiagnosticStep:
    step: str
    success: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True)
class DiscoveryResult:
    hermes_home: str = ""
    config_found: bool = False
    api_server_info: APIServerInfo = field(default_factory=APIServerInfo)
    connection_mode: ConnectionMode = "cli_fallback"
    diagnostic_steps: List[DiagnosticStep] = field(default_factory=list)
    runtime_type: str = ""
    config: Optional[HermesConfig] = None


@dataclass
class ChatChunk:
    content: str = ""
    reasoning_content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: Optional[str] = None
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class ChatCompletionResult:
    content: str = ""
    reasoning_content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: Optional[str] = None
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelInfo:
    id: str
    provider: str = ""
    owned_by: str = ""
    is_available: bool = True


@dataclass(frozen=True)
class ProfileInfo:
    name: str
    path: str = ""
    is_active: bool = False
    has_config: bool = False


@dataclass
class SSEEvent:
    event: str
    data: Any = None

    def encode(self) -> str:
        import json
        data_str = json.dumps(self.data, ensure_ascii=False) if self.data is not None else ""
        return f"event: {self.event}\ndata: {data_str}\n\n"


class HermesAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
