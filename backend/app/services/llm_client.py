import json
import logging
from typing import Optional, List, Dict

from app.services.gateway_client import GatewayClient

logger = logging.getLogger("devflow.llm_client")


class HermesUnavailableError(Exception):
    pass


class LLMClient:
    def __init__(self, profile_name: str = None, port: int = None):
        self._gateway = GatewayClient(profile_name=profile_name, port=port)

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        import asyncio
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, self._chat_async(messages, max_tokens, temperature)).result()
            return result
        return asyncio.run(self._chat_async(messages, max_tokens, temperature))

    async def _chat_async(self, messages, max_tokens, temperature):
        chunks = []
        async for chunk in self._gateway.chat_completions(
            messages=messages, stream=False, max_tokens=max_tokens, temperature=temperature
        ):
            chunks.append(chunk)
        return "".join(chunks)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> dict:
        text = self.chat(messages, system_prompt=system_prompt, max_tokens=max_tokens, temperature=temperature)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            return {"reply": text}


_llm_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient()
    return _llm_client_instance
