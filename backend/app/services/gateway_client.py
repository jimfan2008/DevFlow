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

MAX_CONCURRENT = 20
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
            api_key = get_gateway_api_key(config) or ""

            if port:
                # 检查 api_server 是否已连接
                import json, os
                gw_state_path = os.path.join(
                    get_hermes_home_path(), "profiles", self.profile_name, "gateway_state.json"
                )
                api_server_connected = False
                try:
                    with open(gw_state_path) as f:
                        state = json.load(f)
                    api_server_connected = (state.get("platforms", {})
                                            .get("api_server", {})
                                            .get("state") == "connected")
                except Exception:
                    pass

                if api_server_connected:
                    self.port = port
                    self._api_key = api_key
                    return port, api_key

                # api_server 未标记 connected，尝试直接连接端口
                import httpx as _httpx
                try:
                    test_url = f"http://localhost:{port}/v1/chat/completions"
                    with _httpx.Client(timeout=5) as _client:
                        _resp = _client.post(
                            test_url,
                            json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                            headers={"Content-Type": "application/json"}
                            | ({"Authorization": f"Bearer {api_key}"} if api_key else {}),
                        )
                        if _resp.status_code in (200, 201, 401, 422):
                            self.port = port
                            self._api_key = api_key
                            logger.info(f"Port {port} reachable for profile '{self.profile_name}', using gateway HTTP")
                            return port, api_key
                except Exception:
                    pass
                logger.warning(f"Port {port} unreachable for profile '{self.profile_name}', will try other methods")

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
            logger.info(f"用hermes CLI调用Agent profile '{self.profile_name}'")
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

        def _run_cli():
            return subprocess.run(
                [HERMES_CLI_PATH, "chat", "-q", message, "--profile", self.profile_name, "-Q"],
                capture_output=True, text=True, timeout=self.timeout,
            )

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_run_cli),
                timeout=self.timeout
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                raise Exception(f"hermes CLI error: {result.stderr}")
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
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return check_gateway_running(self.profile_name)

    async def chat_isolated(
        self,
        messages: List[Dict[str, str]],
        project_id: str,
        project_name: str,
        project_description: str = "",
        core_goal: str = "",
        agent_name: str = "",
        stream: bool = False,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        """项目隔离的对话模式
        
        核心问题：Hermes gateway 在每次请求时加载 profile 的 memory.md/user.md，
        导致 A 项目的上下文会泄漏到 B 项目。
        
        解决方案：
        1. 构建强力的项目隔离系统消息，明确指定当前项目
        2. 指示 LLM 忽略记忆中其他项目的信息
        3. 使用 HTTP API 模式（无状态请求）
        """
        # 构建项目隔离的系统消息
        system_content_parts = []
        
        if agent_name:
            system_content_parts.append(
                f"你是{agent_name}，DevFlow 16步开发流程中的专业角色。"
            )
        
        system_content_parts.append(
            f"\n【当前项目上下文】\n"
            f"项目名称: {project_name}\n"
            f"项目ID: {project_id}"
        )
        
        if project_description:
            system_content_parts.append(f"项目描述: {project_description}")
        
        if core_goal:
            system_content_parts.append(f"核心目标: {core_goal}")
        
        system_content_parts.append(
            "\n【重要工作规则 - 项目隔离】\n"
            "1. 你正在为上述「当前项目」工作\n"
            "2. 请只引用上述项目信息，不要引用其他任何项目的上下文\n"
            "3. 如果你的记忆中存在其他项目的信息，请完全忽略它们\n"
            "4. 所有回答、分析、设计都只针对当前项目\n"
            "5. 不得将其他项目的数据、需求、设计带入当前项目"
        )
        
        system_message = {"role": "system", "content": "\n".join(system_content_parts)}
        
        # 将系统消息作为第一条消息
        isolated_messages = [system_message]
        
        # 过滤并添加用户提供的消息
        for msg in messages:
            # 跳过用户可能传入的旧系统消息，使用我们构建的新系统消息
            if msg.get("role") == "system":
                continue
            isolated_messages.append(msg)
        
        # 使用 HTTP API 模式发送（无状态，不加载 profile 的会话历史）
        port, api_key = await self._resolve_profile()
        
        if self._use_cli:
            # CLI 模式：将所有消息合并为单条消息（包含系统提示）
            combined = "\n".join(m.get("content", "") for m in isolated_messages if m.get("content"))
            result = await self._cli_send(combined)
            yield result
            return
        
        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)

        # Try to get model from profile config, fallback to gpt-4o
        model = "gpt-4o"
        try:
            config = read_profile_config(self.profile_name)
            if config:
                default_model = config.get("model", {})
                if isinstance(default_model, dict):
                    model = default_model.get("default", "gpt-4o")
                elif isinstance(default_model, str):
                    model = default_model
        except Exception:
            pass

        payload = {
            "model": model,
            "messages": isolated_messages,
            "stream": stream,
            "temperature": 0.7,
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


gateway_client = GatewayClient()
