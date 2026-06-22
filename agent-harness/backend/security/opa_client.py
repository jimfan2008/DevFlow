from dataclasses import dataclass
from typing import Optional
import httpx


@dataclass
class OPARequest:
    action: str
    subject: str
    resource: str
    context: Optional[dict] = None


class OPAClient:
    def __init__(self, opa_url: str, policy_path: str = "agent_harness/authz"):
        self._opa_url = opa_url.rstrip("/")
        self._policy_path = policy_path

    async def check_permission(self, req: OPARequest) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._opa_url}/v1/data/{self._policy_path}",
                    json=self._prepare_input(
                        req.action, req.subject, req.resource
                    ),
                    timeout=5,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("result", {}).get("allow", False)
                return False
        except (httpx.RequestError, httpx.TimeoutException):
            return self._default_decision()

    def _default_decision(self) -> bool:
        return False

    def _prepare_input(self, action: str, subject: str, resource: str) -> dict:
        return {
            "input": {
                "action": action,
                "subject": subject,
                "resource": resource,
            }
        }
