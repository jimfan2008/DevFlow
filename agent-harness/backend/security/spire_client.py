import re
from typing import Optional


SPIFFE_PATTERN = re.compile(r"^spiffe://([^/]+)(/.*)?$")


class SPIREIdentity:
    @staticmethod
    def parse_spiffe_id(spiffe_id: str) -> Optional[dict]:
        match = SPIFFE_PATTERN.match(spiffe_id)
        if not match:
            return None
        return {
            "trust_domain": match.group(1),
            "path": match.group(2) or "/",
        }

    @staticmethod
    def is_valid(spiffe_id: str) -> bool:
        return SPIFFE_PATTERN.match(spiffe_id) is not None

    @staticmethod
    def make_spiffe_id(trust_domain: str, path: str) -> str:
        return f"spiffe://{trust_domain}{path}"
