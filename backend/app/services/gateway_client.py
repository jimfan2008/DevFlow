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

MAX_CONCURRENT = 5
REQUEST_TIMEOUT = 360
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


class GatewayClient:
    def __init__(self, profile_name: str = None, port: int = None, timeout: int = REQUEST_TIMEOUT):
        self.profile_name = profile_name
        self.port = port
        self.timeout = timeout
        self._api_key: Optional[str] = None

    def _get_base_url(self) -> str:
        if self.port:
            return f"http://localhost:{self.port}"
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
        if not self.profile_name:
            raise ValueError("Either profile_name or port must be provided")
        config = read_profile_config(self.profile_name)
        if not config:
            raise ValueError(f"Profile '{self.profile_name}' config not found")
        port = get_gateway_port_from_config(config)
        if not port:
            raise ValueError(f"Profile '{self.profile_name}' has no gateway port configured")
        api_key = get_gateway_api_key(config) or ""
        self.port = port
        self._api_key = api_key
        return port, api_key

    async def chat_completions(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        model: str = "hermes-agent",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        port, api_key = await self._resolve_profile()
        url = f"http://localhost:{port}/v1/chat/completions"
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
        port, api_key = await self._resolve_profile()
        url = f"http://localhost:{port}/health"
        headers = self._get_headers(api_key)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return False


gateway_client = GatewayClient()
