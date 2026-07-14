import json
import httpx
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.utils.hermes_fs import (
    read_profile_config,
    get_gateway_port_from_config,
    get_gateway_api_key,
)
import logging

logger = logging.getLogger("devflow.gateway_client")

MAX_CONCURRENT = 20
REQUEST_TIMEOUT = 120
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


class GatewayClient:
    def __init__(self, profile_name: str = None, port: int = None, timeout: int = REQUEST_TIMEOUT):
        self.profile_name = profile_name or "default"
        self.port = port
        self.timeout = timeout
        self._api_key: Optional[str] = None

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
                logger.warning(f"Port {port} unreachable for profile '{self.profile_name}'")

        import os
        api_base = os.environ.get("HERMES_API_BASE", "")
        if api_base:
            from urllib.parse import urlparse
            parsed = urlparse(api_base)
            if parsed.port:
                api_key = os.environ.get("HERMES_API_KEY", "")
                import httpx as _httpx
                try:
                    test_url = f"http://{parsed.hostname}:{parsed.port}/v1/chat/completions"
                    with _httpx.Client(timeout=5) as _client:
                        _resp = _client.post(test_url, json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"} if api_key else {"Content-Type": "application/json"})
                        if _resp.status_code in (200, 201, 401, 422):
                            self.port = parsed.port
                            self._api_key = api_key or None
                            logger.info(f"Using HERMES_API_BASE port {parsed.port} for profile '{self.profile_name}'")
                            return parsed.port, api_key
                except Exception:
                    pass

        if config:
            port = get_gateway_port_from_config(config)
            api_key = get_gateway_api_key(config) or ""
            if port:
                import httpx as _httpx
                try:
                    host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
                    test_url = f"http://{host}:{port}/v1/chat/completions"
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
                            logger.info(f"[fallback] Port {port} reachable for '{self.profile_name}', using gateway HTTP")
                            return port, api_key
                except Exception:
                    pass

        logger.warning(f"Gateway not reachable for profile '{self.profile_name}', attempting auto-start (up to 60s)...")
        try:
            import subprocess, os
            subprocess.Popen(
                ["hermes", "-p", self.profile_name, "gateway", "run", "--replace", "--accept-hooks"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            for _ in range(30):
                await asyncio.sleep(2)
                if config and port:
                    try:
                        test_url = f"http://localhost:{port}/v1/chat/completions"
                        with httpx.Client(timeout=3) as _client:
                            _resp = _client.post(
                                test_url,
                                json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                                headers={"Content-Type": "application/json"}
                                | ({"Authorization": f"Bearer {api_key}"} if api_key else {}),
                            )
                            if _resp.status_code in (200, 201, 401, 422):
                                self.port = port
                                self._api_key = api_key
                                logger.info(f"Auto-started gateway on port {port} for '{self.profile_name}'")
                                return port, api_key
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Auto-start gateway failed: {e}")

        raise ValueError(
            f"Gateway not available for profile '{self.profile_name}'. "
            "Ensure Hermes Gateway is running with API server enabled."
        )

    async def direct_chat_completions(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.3,
        max_tokens: int = 32000,
    ) -> AsyncGenerator[str, None]:
        """绕过 hermes agent 网关，直接调用底层 LLM 的 chat/completions API"""
        config = read_profile_config(self.profile_name)
        if not config:
            raise ValueError(f"Profile '{self.profile_name}' not found")

        base_url = config.get("model", {}).get("base_url", "")
        api_key = config.get("model", {}).get("api_key", "")
        model_name = config.get("model", {}).get("default", "")

        if not base_url or not model_name:
            raise ValueError(f"Profile '{self.profile_name}' has no model provider config")

        # 如果 model 在 custom_providers 中有对应条目，优先使用它的 base_url 和 api_key
        custom_providers = config.get("custom_providers", [])
        if isinstance(custom_providers, list):
            for cp in custom_providers:
                if cp.get("model") == model_name:
                    cp_base = cp.get("base_url", "")
                    cp_key = cp.get("api_key", "")
                    if cp_base:
                        base_url = cp_base
                    if cp_key:
                        api_key = cp_key
                    break

        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model_name,
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
                                raise Exception(f"Provider error {response.status_code}: {error_text.decode()}")
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
                            raise Exception(f"Provider error {response.status_code}: {response.text}")
                        result = response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        yield content
            except httpx.TimeoutException:
                raise TimeoutError(f"Request timed out after {self.timeout}s")
            except httpx.ConnectError:
                raise ConnectionError(f"Cannot connect to provider {base_url}")
            except Exception as e:
                raise

    async def chat_completions(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        model: str = "hermes-agent",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        port, api_key = await self._resolve_profile()

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
        try:
            port, api_key = await self._resolve_profile()
        except Exception:
            return False
        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return False

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
        cacheable_system_parts: List[str] = None,
        project_slug: str = "",
    ) -> AsyncGenerator[str, None]:
        """项目隔离的对话模式

        支持 cache_control：将稳定不变的上下文片段（如项目规则、文档分片摘要）标记
        为缓存，避免重复编辑/检验时重复传输相同内容，大幅减少输入 Token。
        """
        system_content_parts = []
        system_cache_parts = []

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

        if cacheable_system_parts:
            for part in cacheable_system_parts:
                system_cache_parts.append(part)

        full_content_parts = []
        base_text = "\n".join(system_content_parts)
        full_content_parts.append({"type": "text", "text": base_text})

        for cp in system_cache_parts:
            full_content_parts.append({
                "type": "text",
                "text": cp,
                "cache_control": {"type": "ephemeral"},
            })

        system_message = {"role": "system", "content": full_content_parts}

        isolated_messages = [system_message]

        for msg in messages:
            if msg.get("role") == "system":
                continue
            isolated_messages.append(msg)

        port, api_key = await self._resolve_profile()

        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)

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
