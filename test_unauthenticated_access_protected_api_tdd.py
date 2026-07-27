import time
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException

AUTH_ERROR_CODE = "AUTH-001"
PROTECTED_PATH = "/api/protected"


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
class TestUnauthenticatedAccessProtectedAPI:

    async def test_无认证头返回401(self, client):
        resp = await client.get(PROTECTED_PATH)
        assert resp.status_code == 401

    async def test_无效令牌返回401(self, client):
        resp = await client.get(
            PROTECTED_PATH, headers={"Authorization": "Bearer invalid_token"}
        )
        assert resp.status_code == 401

    async def test_错误认证方案返回401(self, client):
        resp = await client.get(
            PROTECTED_PATH, headers={"Authorization": "Basic dGVzdA=="}
        )
        assert resp.status_code == 401

    async def test_空Bearer返回401(self, client):
        resp = await client.get(
            PROTECTED_PATH, headers={"Authorization": "Bearer "}
        )
        assert resp.status_code == 401

    async def test_返回error_code为AUTH_001(self, client):
        resp = await client.get(PROTECTED_PATH)
        body = resp.json()
        assert body["error"]["code"] == AUTH_ERROR_CODE

    async def test_返回error_message非空(self, client):
        resp = await client.get(PROTECTED_PATH)
        body = resp.json()
        assert body["error"]["message"]
        assert len(body["error"]["message"]) > 0

    async def test_响应时间不超过100ms(self, client):
        start = time.perf_counter()
        await client.get(PROTECTED_PATH)
        elapsed = time.perf_counter() - start
        assert elapsed <= 0.1

    async def test_有效令牌正常返回200(self, client):
        resp = await client.get(
            PROTECTED_PATH, headers={"Authorization": "Bearer valid_token_abc"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["user_id"] == "user_001"

    async def test_连续未认证请求均返回401(self, client):
        for _ in range(5):
            resp = await client.get(PROTECTED_PATH)
            assert resp.status_code == 401
            assert resp.json()["error"]["code"] == AUTH_ERROR_CODE

    async def test_WWW_Authenticate头包含Bearer(self, client):
        resp = await client.get(PROTECTED_PATH)
        assert resp.status_code == 401
        assert "Bearer" in resp.headers.get("www-authenticate", "")

    async def test_未认证后再认证仍正常(self, client):
        await client.get(PROTECTED_PATH)
        resp = await client.get(
            PROTECTED_PATH, headers={"Authorization": "Bearer valid_token_abc"}
        )
        assert resp.status_code == 200


@pytest.fixture(autouse=True)
async def cleanup(client):
    yield
    await client.aclose()
