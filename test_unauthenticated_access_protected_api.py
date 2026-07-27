import time
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException

AUTH_ERROR_CODE = "AUTH-001"
PROTECTED_PATH = "/api/v1/protected"


def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权：缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权：认证方案无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("Bearer "):]
    if not token or token == "invalid_token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权：令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": "user_001", "username": "testuser"}


def _auth_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": AUTH_ERROR_CODE if exc.status_code == 401 else f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
            }
        },
        headers=getattr(exc, "headers", None),
    )


app = FastAPI()
app.add_exception_handler(StarletteHTTPException, _auth_exception_handler)


@app.get(PROTECTED_PATH)
def protected_endpoint(current_user=Depends(get_current_user)):
    return {"user": current_user}


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_unauthenticated_access_returns_401(client):
    """未携带认证令牌访问受保护API应返回HTTP 401"""
    resp = await client.get(PROTECTED_PATH)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_access_returns_auth_error_code(client):
    """未认证响应体中 error.code 应为 AUTH-001"""
    resp = await client.get(PROTECTED_PATH)
    body = resp.json()
    assert body["error"]["code"] == AUTH_ERROR_CODE


@pytest.mark.asyncio
async def test_unauthenticated_access_response_time_within_100ms(client):
    """未认证请求的响应时间应不超过 100ms"""
    start = time.perf_counter()
    await client.get(PROTECTED_PATH)
    elapsed = time.perf_counter() - start
    assert elapsed <= 0.1, f"响应耗时 {elapsed * 1000:.1f}ms 超过 100ms 限制"


@pytest.mark.asyncio
async def test_invalid_token_returns_401(client):
    """携带无效令牌访问受保护API应返回401"""
    resp = await client.get(
        PROTECTED_PATH, headers={"Authorization": "Bearer invalid_token"}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == AUTH_ERROR_CODE


@pytest.mark.asyncio
async def test_wrong_auth_scheme_returns_401(client):
    """使用错误认证方案（如 Basic）应返回401"""
    resp = await client.get(
        PROTECTED_PATH, headers={"Authorization": "Basic dGVzdA=="}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == AUTH_ERROR_CODE


@pytest.mark.asyncio
async def test_empty_bearer_returns_401(client):
    """Bearer 后无令牌值应返回401"""
    resp = await client.get(
        PROTECTED_PATH, headers={"Authorization": "Bearer "}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == AUTH_ERROR_CODE


@pytest.mark.asyncio
async def test_www_authenticate_header_contains_bearer(client):
    """401 响应应包含 WWW-Authenticate: Bearer 头"""
    resp = await client.get(PROTECTED_PATH)
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("www-authenticate", "")


@pytest.mark.asyncio
async def test_error_message_is_not_empty(client):
    """401 响应的 error.message 字段不应为空"""
    resp = await client.get(PROTECTED_PATH)
    body = resp.json()
    assert body["error"]["message"]
    assert len(body["error"]["message"]) > 0


@pytest.mark.asyncio
async def test_valid_token_returns_200(client):
    """携带有效令牌应正常访问受保护API并返回200"""
    resp = await client.get(
        PROTECTED_PATH, headers={"Authorization": "Bearer valid_token_abc"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["user_id"] == "user_001"


@pytest.mark.asyncio
async def test_consecutive_unauthenticated_requests_all_return_401(client):
    """连续多次未认证请求应每次都返回401和正确错误码"""
    for _ in range(5):
        resp = await client.get(PROTECTED_PATH)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == AUTH_ERROR_CODE


@pytest.fixture(autouse=True)
async def cleanup(client):
    yield
    await client.aclose()
