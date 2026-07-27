#!/usr/bin/env python3
"""TDD 测试用例：未认证访问受保护API

验证未登录用户访问需要认证的API时返回401，
错误码为 AUTH-001，响应时间 <=100ms。
"""

import time
import pytest
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException

AUTH_ERROR_CODE = "AUTH-001"
PROTECTED_PATH = "/api/protected"


def get_current_user(authorization: str = Header(None)):
    """模拟认证依赖：无 token / 无效 token 时抛出 401。"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("Bearer "):]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token == "invalid_token_xxxxx":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": "user_valid_001", "username": "testuser"}


async def http_exception_handler(request, exc: StarletteHTTPException):
    """全局异常处理器：将 HTTPException 统一包装为 {error: {code, message}}。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": AUTH_ERROR_CODE,
                "message": str(exc.detail),
            }
        },
        headers=getattr(exc, "headers", None),
    )


app = FastAPI()
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


@app.get(PROTECTED_PATH)
def protected_endpoint(current_user=Depends(get_current_user)):
    return {"user": current_user}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestUnauthenticatedAccessProtectedAPI:
    """未认证用户访问受保护 API 应返回 401 + AUTH-001，响应时间 <=100ms。"""

    def test_returns_401_when_no_auth_header(self, client):
        response = client.get(PROTECTED_PATH)
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_returns_401_when_invalid_token(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer invalid_token_xxxxx"},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_returns_401_when_empty_bearer_token(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_returns_401_when_wrong_auth_scheme(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_error_code_is_auth_001(self, client):
        response = client.get(PROTECTED_PATH)
        body = response.json()
        assert response.status_code == 401
        assert "error" in body, f"response missing 'error' key: {body}"
        assert body["error"]["code"] == AUTH_ERROR_CODE, (
            f"expected error.code='{AUTH_ERROR_CODE}', "
            f"got '{body['error']['code']}'"
        )

    def test_error_message_present(self, client):
        response = client.get(PROTECTED_PATH)
        body = response.json()
        assert "error" in body
        assert "message" in body["error"], (
            f"error object missing 'message' key: {body['error']}"
        )
        assert len(body["error"]["message"]) > 0

    def test_response_time_within_100ms(self, client):
        client.get(PROTECTED_PATH)
        start = time.perf_counter()
        client.get(PROTECTED_PATH)
        elapsed = time.perf_counter() - start
        assert elapsed <= 0.1, (
            f"response time {elapsed * 1000:.1f}ms exceeded 100ms"
        )

    def test_authorized_request_succeeds(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer valid_token_abc123"},
        )
        assert response.status_code == 200, (
            f"expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["user"]["user_id"] == "user_valid_001"
        assert body["user"]["username"] == "testuser"

    def test_authorized_not_affected_by_unauthorized(self, client):
        client.get(PROTECTED_PATH)
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer valid_token_abc123"},
        )
        assert response.status_code == 200

    def test_consecutive_unauthorized_all_return_401(self, client):
        for _ in range(5):
            response = client.get(PROTECTED_PATH)
            assert response.status_code == 401, (
                f"expected 401 on consecutive call, got {response.status_code}"
            )
            assert response.json()["error"]["code"] == AUTH_ERROR_CODE

    def test_www_authenticate_header_present(self, client):
        response = client.get(PROTECTED_PATH)
        assert response.status_code == 401
        assert "www-authenticate" in response.headers, (
            f"missing WWW-Authenticate header: {dict(response.headers)}"
        )
        assert "Bearer" in response.headers["www-authenticate"]
