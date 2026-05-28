import json
import httpx
import asyncio
import subprocess
import shutil
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.utils.hermes_fs import (
    read_profile_config,
    get_gateway_port_from_config,
    get_gateway_api_key,
    check_gateway_running,
    get_hermes_home_path,
)
import logging

logger = logging.getLogger("devflow.gateway_client")

MAX_CONCURRENT = 5
REQUEST_TIMEOUT = 360
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)

HERMES_CLI_PATH = shutil.which("hermes")


class GatewayClient:
    def __init__(self, profile_name: str = None, port: int = None, timeout: int = REQUEST_TIMEOUT):
        self.profile_name = profile_name or "default"
        self.port = port
        self.timeout = timeout
        self._api_key: Optional[str] = None
        self._use_cli = False
        effective_profile = profile_name or "default"
        if not port:
            self._use_cli = True
            logger.info(f"Using CLI mode for profile '{effective_profile}'")

    def _get_base_url(self) -> str:
        if self.port:
            import os
            host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
            return f"http://{host}:{self.port}"
        return ""

    def _get_headers(self, api_key: str = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key = api_key or self._api_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def _resolve_profile(self) -> tuple:
        if self.port:
            return self.port, self._api_key
        config = read_profile_config(self.profile_name)
        if config:
            port = get_gateway_port_from_config(config)
            if port:
                api_key = get_gateway_api_key(config) or ""
                self.port = port
                self._api_key = api_key
                return port, api_key

        # Fallback: extract port from HERMES_API_BASE env var
        import os
        api_base = os.environ.get("HERMES_API_BASE", "")
        if api_base:
            from urllib.parse import urlparse
            parsed = urlparse(api_base)
            if parsed.port:
                api_key = os.environ.get("HERMES_API_KEY", "")
                test_url = f"http://{parsed.hostname}:{parsed.port}/v1/chat/completions"
                try:
                    import httpx as _httpx
                    with _httpx.Client(timeout=5) as _client:
                        _resp = _client.post(test_url, json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"} if api_key else {"Content-Type": "application/json"})
                        if _resp.status_code not in (200, 201, 401, 422):
                            logger.warning(f"HERMES_API_BASE port {parsed.port} returned {_resp.status_code} for /v1/chat/completions, falling back to CLI")
                            self._use_cli = True
                            return 0, ""
                except Exception as e:
                    logger.warning(f"HERMES_API_BASE port {parsed.port} unreachable: {e}, falling back to CLI")
                    self._use_cli = True
                    return 0, ""
                self.port = parsed.port
                self._api_key = api_key or None
                logger.info(f"Using HERMES_API_BASE port {parsed.port} for profile '{self.profile_name}'")
                return parsed.port, api_key

        if check_gateway_running(self.profile_name):
            self._use_cli = True
            logger.info(f"Gateway running but no HTTP port, will use CLI fallback for profile '{self.profile_name}'")
            return 0, ""

        raise ValueError(f"Gateway not available for profile '{self.profile_name}'. Ensure Hermes Gateway is running with API server enabled or install hermes CLI.")

    async def _cli_send(self, message: str) -> str:
        global HERMES_CLI_PATH
        if not HERMES_CLI_PATH:
            hermes_home = get_hermes_home_path()
            cli_candidates = [
                str(hermes_home / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"),
                str(hermes_home / "hermes-agent" / "venv" / "bin" / "hermes"),
                "hermes",
            ]
            for candidate in cli_candidates:
                if shutil.which(candidate):
                    HERMES_CLI_PATH = candidate
                    break

        if not HERMES_CLI_PATH:
            raise ConnectionError("Hermes CLI not found. Install hermes or enable Gateway API server.")

        try:
            proc = await asyncio.create_subprocess_exec(
                HERMES_CLI_PATH, "chat", "-q", message, "--profile", self.profile_name, "-Q",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            if proc.returncode == 0:
                return stdout.decode("utf-8", errors="replace").strip()
            else:
                raise Exception(f"hermes CLI error: {stderr.decode('utf-8', errors='replace')}")
        except asyncio.TimeoutError:
            raise TimeoutError(f"hermes CLI timed out after {self.timeout}s")

    async def chat_completions(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        model: str = "hermes-agent",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        if self._use_cli:
            combined = "\n".join(m.get("content", "") for m in messages if m.get("content"))
            result = await self._cli_send(combined)
            yield result
            return

        port, api_key = await self._resolve_profile()
        
        if self._use_cli:
            combined = "\n".join(m.get("content", "") for m in messages if m.get("content"))
            result = await self._cli_send(combined)
            yield result
            return
            
        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with _semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if stream:
                        async with client.stream("POST", url, headers=headers, json=payload) as response:
                            if response.status_code != 200:
                                error_text = await response.aread()
                                raise Exception(f"Gateway error {response.status_code}: {error_text.decode()}")
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    if data == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data)
                                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if content:
                                            yield content
                                    except json.JSONDecodeError:
                                        continue
                    else:
                        response = await client.post(url, headers=headers, json=payload)
                        if response.status_code != 200:
                            raise Exception(f"Gateway error {response.status_code}: {response.text}")
                        result = response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        yield content
            except httpx.TimeoutException:
                raise TimeoutError(f"Request timed out after {self.timeout}s")
            except httpx.ConnectError:
                raise ConnectionError(f"Cannot connect to gateway at port {port}")
            except Exception as e:
                raise

    async def send_message(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        messages = conversation_history or []
        messages.append({"role": "user", "content": message})
        async for chunk in self.chat_completions(messages=messages, stream=stream):
            yield chunk

    async def send_message_non_stream(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> str:
        logger.info(f"send_message_non_stream: _use_cli={self._use_cli}, port={self.port}, profile={self.profile_name}")
        if self._use_cli:
            logger.info("send_message_non_stream: Using CLI mode")
            result = await self._cli_send(message)
            logger.info(f"CLI send result length: {len(result) if result else 0}")
            return result
        logger.info("send_message_non_stream: Using HTTP mode")
        full_response = []
        async for chunk in self.send_message(message, conversation_history, stream=False):
            full_response.append(chunk)
        return "".join(full_response)

    async def stream_message(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.send_message(message, conversation_history, stream=True):
            yield chunk

    async def health_check(self) -> bool:
        if self._use_cli:
            return check_gateway_running(self.profile_name)
        try:
            port, api_key = await self._resolve_profile()
        except Exception:
            return check_gateway_running(self.profile_name)
        if self._use_cli:
            return check_gateway_running(self.profile_name)
        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/health"
        headers = self._get_headers(api_key)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return check_gateway_running(self.profile_name)


gateway_client = GatewayClient()
