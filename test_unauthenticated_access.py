import time
import pytest
from unittest.mock import patch, MagicMock


class MockResponse:
    """Mock HTTP response for FastAPI/Flask style API."""

    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


class AuthMiddleware:
    """Simulates authentication middleware that protects API routes."""

    def __init__(self, require_auth=True):
        self.require_auth = require_auth

    def process_request(self, headers):
        if not self.require_auth:
            return None
        auth_header = headers.get("Authorization")
        if not auth_header:
            return MockResponse(
                401,
                {
                    "error": {
                        "code": "AUTH-001",
                        "message": "Authentication required",
                    }
                },
            )
        if not auth_header.startswith("Bearer "):
            return MockResponse(
                401,
                {
                    "error": {
                        "code": "AUTH-002",
                        "message": "Invalid token format",
                    }
                },
            )
        return None  # Auth passed


def call_protected_api(headers=None):
    """Simulate calling a protected API endpoint."""
    middleware = AuthMiddleware(require_auth=True)
    result = middleware.process_request(headers or {})
    if result is not None:
        return result
    return MockResponse(200, {"data": "protected resource"})


def test_unauthenticated_access_returns_401():
    """未认证访问受保护API应返回401状态码。"""
    response = call_protected_api(headers={})
    assert response.status_code == 401


def test_unauthenticated_access_error_code_is_AUTH_001():
    """未认证访问受保护API应返回 error.code = AUTH-001。"""
    response = call_protected_api(headers={})
    body = response.json()
    assert body["error"]["code"] == "AUTH-001"


def test_unauthenticated_access_response_time_under_100ms():
    """未认证访问受保护API响应时间应小于等于100ms。"""
    start = time.perf_counter()
    call_protected_api(headers={})
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms <= 100


def test_valid_token_accesses_protected_api_successfully():
    """携带有效Token应能正常访问受保护API。"""
    response = call_protected_api(headers={"Authorization": "Bearer valid-token-123"})
    assert response.status_code == 200
    assert response.json()["data"] == "protected resource"


def test_no_token_header_returns_401():
    """完全不传Authorization头也应返回401。"""
    response = call_protected_api(headers=None)
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "AUTH-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
