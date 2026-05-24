from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx

from app.services.hermes.types import (
    APIServerConfig,
    APIServerInfo,
    DiagnosticStep,
    DiscoveryResult,
    HermesConfig,
)
from app.services.hermes.hermes_config import HermesConfigReader

logger = logging.getLogger("devflow.hermes.discovery")


class HermesDiscoveryService:
    def __init__(self, config_reader: HermesConfigReader = None):
        self._reader = config_reader or HermesConfigReader()

    def discover(self) -> DiscoveryResult:
        steps: list[DiagnosticStep] = []
        hermes_home = str(self._reader.home)

        step_start = time.time()
        home_exists = Path(hermes_home).exists()
        steps.append(DiagnosticStep(
            step="resolve_hermes_home",
            success=home_exists,
            detail=f"home={hermes_home}, exists={home_exists}",
            duration_ms=(time.time() - step_start) * 1000,
        ))

        config: Optional[HermesConfig] = None
        if home_exists:
            step_start = time.time()
            config = self._reader.read_config()
            config_ok = config is not None
            steps.append(DiagnosticStep(
                step="read_config",
                success=config_ok,
                detail=f"config.yaml found={config_ok}",
                duration_ms=(time.time() - step_start) * 1000,
            ))

        api_info = self._check_api_server(config, steps)
        runtime_type = self._detect_runtime_type(steps)

        if api_info.reachable:
            connection_mode: str = "api_server"
        elif os.environ.get("HERMES_BFF_URL", ""):
            connection_mode = "socketio_bff"
        else:
            connection_mode = "cli_fallback"

        steps.append(DiagnosticStep(
            step="determine_connection_mode",
            success=True,
            detail=f"mode={connection_mode}",
        ))

        return DiscoveryResult(
            hermes_home=hermes_home,
            config_found=config is not None,
            api_server_info=api_info,
            connection_mode=connection_mode,
            diagnostic_steps=steps,
            runtime_type=runtime_type,
            config=config,
        )

    def _check_api_server(self, config: Optional[HermesConfig], steps: list[DiagnosticStep]) -> APIServerInfo:
        candidates = self._build_api_server_candidates(config)

        for base_url, api_key in candidates:
            step_start = time.time()
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.get(f"{base_url}/health")
                    latency = (time.time() - step_start) * 1000
                    if resp.status_code == 200:
                        models_resp = client.get(f"{base_url}/models", headers=self._auth_header(api_key))
                        model = ""
                        if models_resp.status_code == 200:
                            data = models_resp.json().get("data", [])
                            if data:
                                model = data[0].get("id", "")
                        steps.append(DiagnosticStep(
                            step="check_api_server",
                            success=True,
                            detail=f"base_url={base_url}, model={model}, latency={latency:.0f}ms",
                            duration_ms=latency,
                        ))
                        return APIServerInfo(reachable=True, base_url=base_url, model=model, health_ok=True, latency_ms=latency)
            except Exception as e:
                steps.append(DiagnosticStep(
                    step="check_api_server",
                    success=False,
                    detail=f"base_url={base_url}, error={str(e)[:100]}",
                    duration_ms=(time.time() - step_start) * 1000,
                ))

        return APIServerInfo(reachable=False)

    def _build_api_server_candidates(self, config: Optional[HermesConfig]) -> list[tuple[str, str]]:
        candidates = []

        env_base = os.environ.get("HERMES_API_BASE", "")
        env_key = os.environ.get("HERMES_API_KEY", "")
        if env_base:
            base = env_base.rstrip("/")
            if not base.endswith("/v1"):
                base = base + "/v1"
            candidates.append((base, env_key))

        if config and config.api_server.enabled:
            cfg = config.api_server
            host = cfg.host
            if host in ("0.0.0.0", "::", "localhost", "127.0.0.1"):
                host = self._resolve_host_for_docker(host)
            candidates.append((f"http://{host}:{cfg.port}/v1", cfg.api_key))

        return candidates

    def _detect_runtime_type(self, steps: list[DiagnosticStep]) -> str:
        step_start = time.time()
        home = self._reader.home

        if (home / "hermes-agent" / "run_agent.py").exists():
            runtime = "source"
            detail = "run_agent.py found in hermes-agent/"
        elif (home / "hermes-agent" / "venv" / "Scripts" / "hermes.exe").exists():
            runtime = "cli_windows"
            detail = "hermes.exe found in venv/Scripts/"
        elif (home / "hermes-agent" / "venv" / "bin" / "hermes").exists():
            runtime = "cli_linux"
            detail = "hermes found in venv/bin/"
        else:
            runtime = "not_found"
            detail = "no hermes runtime found"

        steps.append(DiagnosticStep(
            step="detect_runtime_type",
            success=runtime != "not_found",
            detail=detail,
            duration_ms=(time.time() - step_start) * 1000,
        ))
        return runtime

    @staticmethod
    def _resolve_host_for_docker(host: str) -> str:
        try:
            with open("/proc/1/cgroup", "r") as f:
                if "docker" in f.read() or "containerd" in f.read():
                    return "host.docker.internal"
        except Exception:
            pass
        if os.path.exists("/.dockerenv"):
            return "host.docker.internal"
        return host

    @staticmethod
    def _auth_header(api_key: str) -> dict:
        if api_key:
            return {"Authorization": f"Bearer {api_key}"}
        return {}
