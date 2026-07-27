import time
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse


# --- Minimal FastAPI app under test ---
app = FastAPI()


def get_current_user():
    raise HTTPException(
        status_code=401,
        detail={"code": "AUTH-001", "message": "未认证"},
    )


@app.get("/protected")
def protected_resource(_user=Depends(get_current_user)):
    return {"data": "secret"}


# --- Tests ---

@pytest.mark.asyncio
async def test_unauthenticated_access_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = time.perf_counter()
        response = await client.get("/protected")
        elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["code"] == "AUTH-001"
    assert elapsed_ms <= 100, f"响应时间 {elapsed_ms:.1f}ms 超过 100ms"
