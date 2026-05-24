from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.services.hermes.types import (
    ChatChunk,
    ChatCompletionResult,
    HermesAPIError,
    ModelInfo,
)

logger = logging.getLogger("devflow.hermes.api_client")


class HermesAPIClient:
    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "hermes-agent",
        timeout: int = 360,
        max_connections: int = 10,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_model = model
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._max_connections = max_connections
        self._models_cache: Optional[List[ModelInfo]] = None
        self._models_cache_time: float = 0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._auth_headers(),
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                limits=httpx.Limits(max_connections=self._max_connections),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            base = self._base_url.replace("/v1", "").rstrip("/")
            resp = await client.get(f"{base}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self, use_cache: bool = True) -> List[ModelInfo]:
        now = time.time()
        if use_cache and self._models_cache and (now - self._models_cache_time) < 8:
            return self._models_cache
        try:
            client = await self._get_client()
            resp = await client.get("/models", timeout=8.0)
            if resp.status_code != 200:
                raise HermesAPIError(f"Models request failed: {resp.status_code}", status_code=resp.status_code)
            data = resp.json().get("data", [])
            models = [ModelInfo(id=m.get("id", ""), provider=m.get("owned_by", "")) for m in data]
            self._models_cache = models
            self._models_cache_time = now
            return models
        except HermesAPIError:
            raise
        except Exception as e:
            raise HermesAPIError(f"Cannot list models: {e}")

    async def chat_completions_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[ChatChunk, None]:
        client = await self._get_client()
        payload = {
            "model": model or self._default_model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise HermesAPIError(
                        f"Chat stream error {response.status_code}",
                        status_code=response.status_code,
                        body=error_body.decode("utf-8", errors="replace")[:500],
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    chunk = self._parse_chunk(chunk_json)
                    if chunk.content or chunk.reasoning_content or chunk.tool_calls or chunk.finish_reason:
                        yield chunk
        except HermesAPIError:
            raise
        except httpx.ConnectError as e:
            raise HermesAPIError(f"Cannot connect to Hermes API Server: {e}")
        except httpx.TimeoutException:
            raise HermesAPIError("Hermes API request timed out")

    async def chat_completions(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> ChatCompletionResult:
        client = await self._get_client()
        payload = {
            "model": model or self._default_model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = await client.post("/chat/completions", json=payload)
            if resp.status_code != 200:
                raise HermesAPIError(
                    f"Chat error {resp.status_code}",
                    status_code=resp.status_code,
                    body=resp.text[:500],
                )
            result = resp.json()
            choice = result.get("choices", [{}])[0]
            message = choice.get("message", {})
            return ChatCompletionResult(
                content=message.get("content", ""),
                reasoning_content=message.get("reasoning_content", ""),
                tool_calls=message.get("tool_calls", []),
                finish_reason=choice.get("finish_reason"),
                model=result.get("model", ""),
                usage=result.get("usage", {}),
            )
        except HermesAPIError:
            raise
        except httpx.ConnectError as e:
            raise HermesAPIError(f"Cannot connect to Hermes API Server: {e}")
        except httpx.TimeoutException:
            raise HermesAPIError("Hermes API request timed out")

    @staticmethod
    def _parse_chunk(chunk_json: Dict[str, Any]) -> ChatChunk:
        choice = chunk_json.get("choices", [{}])[0]
        delta = choice.get("delta", {})
        return ChatChunk(
            content=delta.get("content", ""),
            reasoning_content=delta.get("reasoning_content", ""),
            tool_calls=delta.get("tool_calls", []),
            finish_reason=choice.get("finish_reason"),
            model=chunk_json.get("model", ""),
            usage=chunk_json.get("usage", {}),
        )

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers
