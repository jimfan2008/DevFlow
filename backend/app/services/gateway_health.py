import httpx
import asyncio
import os
import logging
from typing import Dict, Optional
from app.config import settings

logger = logging.getLogger("devflow.gateway_health")

_health_cache: Dict[str, dict] = {}
_HEALTH_CHECK_INTERVAL = 30


async def check_gateway_health(port: int, api_key: str = None, timeout: float = 5.0) -> dict:
    host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
    url = f"http://{host}:{port}/health"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            is_healthy = resp.status_code == 200
            result = {
                "port": port,
                "healthy": is_healthy,
                "status_code": resp.status_code,
            }
            if is_healthy:
                try:
                    result["data"] = resp.json()
                except Exception:
                    pass
            return result
    except httpx.TimeoutException:
        return {"port": port, "healthy": False, "error": "timeout"}
    except httpx.ConnectError:
        return {"port": port, "healthy": False, "error": "connection_refused"}
    except Exception as e:
        return {"port": port, "healthy": False, "error": str(e)}


async def check_agent_online(port: int, api_key: str = None) -> bool:
    result = await check_gateway_health(port, api_key)
    return result.get("healthy", False)


async def periodic_health_check(agents_config: list) -> Dict[str, dict]:
    results = {}
    for agent_conf in agents_config:
        port = agent_conf.get("gateway_port")
        api_key = agent_conf.get("api_key")
        name = agent_conf.get("name", str(port))
        if port:
            result = await check_gateway_health(port, api_key)
            results[name] = result
            _health_cache[name] = result
    return results


def get_cached_health(name: str) -> Optional[dict]:
    return _health_cache.get(name)


def get_all_cached_health() -> Dict[str, dict]:
    return _health_cache.copy()
