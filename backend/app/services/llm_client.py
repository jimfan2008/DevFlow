import json
import logging
import os
from typing import Optional, List, Dict

import httpx

from app.services.gateway_client import GatewayClient
from app.utils.hermes_fs import get_hermes_home_path

logger = logging.getLogger("devflow.llm_client")


class HermesUnavailableError(Exception):
    pass


def _load_hermes_llm_config() -> Dict:
    try:
        home = get_hermes_home_path()
        config_path = home / "config.yaml"
        if config_path.exists():
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            model_cfg = config.get("model", {})
            base_url = model_cfg.get("base_url", "")
            api_key = model_cfg.get("api_key", "")
            model_name = model_cfg.get("default", "")
            if base_url:
                return {"base_url": base_url.rstrip("/"), "api_key": api_key, "model": model_name}
    except Exception as e:
        logger.debug(f"Could not load Hermes LLM config: {e}")
    return {}


class LLMClient:
    def __init__(self, profile_name: str = None, port: int = None):
        self._gateway = GatewayClient(profile_name=profile_name, port=port)
        self._direct_llm: Optional[Dict] = None
        self._init_direct_llm()

    def _init_direct_llm(self):
        api_server_url = os.environ.get("HERMES_API_SERVER_URL", "")
        api_server_key = os.environ.get("HERMES_API_SERVER_KEY", "")
        if api_server_url:
            self._direct_llm = {
                "base_url": api_server_url.rstrip("/"),
                "api_key": api_server_key,
                "model": os.environ.get("HERMES_API_SERVER_MODEL", "hermes-agent"),
            }
            logger.info(f"LLMClient using Hermes API Server: {api_server_url} (model=hermes-agent)")
            return
        env_base = os.environ.get("LLM_API_BASE", "")
        env_key = os.environ.get("LLM_API_KEY", "")
        env_model = os.environ.get("LLM_MODEL", "")
        if env_base:
            self._direct_llm = {"base_url": env_base.rstrip("/"), "api_key": env_key, "model": env_model}
            logger.info(f"LLMClient using env LLM_API_BASE={env_base}, model={env_model}")
            return
        hermes_cfg = _load_hermes_llm_config()
        if hermes_cfg:
            self._direct_llm = hermes_cfg
            logger.info(f"LLMClient using Hermes config: base_url={hermes_cfg['base_url']}, model={hermes_cfg['model']}")
            return
        logger.info("LLMClient: no direct LLM config, will use GatewayClient")

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        if self._direct_llm:
            return self._direct_chat(messages, max_tokens, temperature)
        import asyncio
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

    def _direct_chat(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        cfg = self._direct_llm
        url = f"{cfg['base_url']}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        payload = {
            "model": cfg.get("model", ""),
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            with httpx.Client(timeout=60) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    raise HermesUnavailableError(f"LLM API error {resp.status_code}: {resp.text[:200]}")
                result = resp.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content
        except httpx.ConnectError as e:
            raise HermesUnavailableError(f"Cannot connect to LLM at {url}: {e}")
        except httpx.TimeoutException:
            raise HermesUnavailableError(f"LLM request timed out")

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
        import re
        text = re.sub(r'<tool_call>.*?👉', '', text, flags=re.DOTALL)
        text = re.sub(r'^Thinking Process:.*?\n(?=[A-Z\u4e00-\u9fff{])', '', text, flags=re.DOTALL | re.IGNORECASE)
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
