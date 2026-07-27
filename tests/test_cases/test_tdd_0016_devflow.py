import pytest
import time
from fastapi import FastAPI, HTTPException, Depends, status, Header
from httpx import AsyncClient, ASGITransport


AUTH_ERROR_CODE = "AUTH-001"
ERROR_RESPONSE_401 = {
    "error": {
        "code": AUTH_ERROR_CODE,
        "message": "Authentication required. Please provide a valid Bearer token.",
    }
}
PROTECTED_GET_PATH = "/api/protected"
PROTECTED_POST_PATH = "/api/protected"
PROTECTED_DELETE_PATH = "/api/protected/resource/1"

# CI-safe time limit (ms) — avoids flakiness in low-performance environments
_TIME_LIMIT_MS = 500


def _create_test_app():
    app = FastAPI()

    def verify_token(authorization: str | None = Header(None)):
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_RESPONSE_401,
            )
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_RESPONSE_401,
            )
        return {"user_id": 1, "username": "testuser"}

    @app.get(PROTECTED_GET_PATH)
    def protected_get_route(current_user: dict = Depends(verify_token)):
        return {"data": "protected resource", "user": current_user}

    @app.post(PROTECTED_POST_PATH)
    def protected_post_route(current_user: dict = Depends(verify_token)):
        return {"data": "protected resource created", "user": current_user}

    @app.delete(PROTECTED_DELETE_PATH)
    def protected_delete_route(current_user: dict = Depends(verify_token)):
        return {"data": "protected resource deleted", "user": current_user}

    return app


@pytest.fixture(name="test_app")
def fixture_test_app():
    return _create_test_app()


@pytest.fixture(name="client")
def fixture_client(test_app):
    transport = ASGITransport(app=test_app)
    return AsyncClient(transport=transport, base_url="http://test")


def _assert_unauthorized(response, elapsed_ms: float):
    """Shared assertions for 401 + AUTH-001 + response structure."""
    assert response.status_code == 401, (
        f"expected 401, got {response.status_code}"
    )
    body = response.json()
    assert "error" in body, f"response missing 'error' key: {body}"
    assert body["error"]["code"] == AUTH_ERROR_CODE, (
        f"expected error.code={AUTH_ERROR_CODE!r}, got {body['error']['code']!r}"
    )
    assert "message" in body["error"], (
        f"error object missing 'message' key: {body['error']}"
    )
    assert elapsed_ms <= _TIME_LIMIT_MS, (
        f"response took {elapsed_ms:.2f}ms, expected <= {_TIME_LIMIT_MS}ms"
    )


@pytest.mark.asyncio
async def test_unauthenticated_get_returns_401(client):
    start = time.monotonic()
    response = await client.get(PROTECTED_GET_PATH)
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_unauthenticated_post_returns_401(client):
    start = time.monotonic()
    response = await client.post(PROTECTED_POST_PATH)
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_unauthenticated_delete_returns_401(client):
    start = time.monotonic()
    response = await client.delete(PROTECTED_DELETE_PATH)
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_without_authorization_header_returns_401(client):
    start = time.monotonic()
    response = await client.get(PROTECTED_GET_PATH, headers={})
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_with_invalid_token_format_returns_401(client):
    start = time.monotonic()
    response = await client.get(
        PROTECTED_GET_PATH, headers={"Authorization": "InvalidFormat token123"}
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_with_empty_bearer_token_returns_401(client):
    start = time.monotonic()
    response = await client.get(
        PROTECTED_GET_PATH, headers={"Authorization": "Bearer "}
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_bearer_only_no_space_returns_401(client):
    """Authorization: 'Bearer' (no space, no token) — partition yields empty token."""
    start = time.monotonic()
    response = await client.get(
        PROTECTED_GET_PATH, headers={"Authorization": "Bearer"}
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_authorization_empty_string_returns_401(client):
    """Authorization: '' (empty string) — falsy, triggers no-auth path."""
    start = time.monotonic()
    response = await client.get(
        PROTECTED_GET_PATH, headers={"Authorization": ""}
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    _assert_unauthorized(response, elapsed_ms)


@pytest.mark.asyncio
async def test_with_sql_like_token_succeeds(client):
    """Special characters / SQL injection payload in token — must be accepted as valid Bearer token."""
    start = time.monotonic()
    sql_payload = "' OR 1=1; DROP TABLE users; --"
    response = await client.get(
        PROTECTED_GET_PATH,
        headers={"Authorization": f"Bearer {sql_payload}"},
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    assert response.status_code == 200, (
        f"expected 200 for token with SQL-like payload, got {response.status_code}"
    )
    assert elapsed_ms <= _TIME_LIMIT_MS


@pytest.mark.asyncio
async def test_lowercase_bearer_prefix_succeeds(client):
    """Lowercase 'bearer ' prefix — code uses .lower() comparison, should be accepted."""
    start = time.monotonic()
    response = await client.get(
        PROTECTED_GET_PATH, headers={"Authorization": "bearer valid-token-abc123"}
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    assert response.status_code == 200, (
        f"expected 200 for lowercase bearer prefix, got {response.status_code}"
    )
    assert elapsed_ms <= _TIME_LIMIT_MS


@pytest.mark.asyncio
async def test_xss_payload_token_succeeds(client):
    """XSS payload in token — must be accepted as opaque token value."""
    start = time.monotonic()
    xss_payload = "<script>alert('xss')</script>"
    response = await client.get(
        PROTECTED_GET_PATH,
        headers={"Authorization": f"Bearer {xss_payload}"},
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    assert response.status_code == 200, (
        f"expected 200 for XSS-like token, got {response.status_code}"
    )
    assert elapsed_ms <= _TIME_LIMIT_MS


@pytest.mark.asyncio
async def test_valid_token_succeeds(client):
    start = time.monotonic()
    response = await client.get(
        PROTECTED_GET_PATH, headers={"Authorization": "Bearer valid-token-abc123"}
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == "protected resource"
    assert elapsed_ms <= _TIME_LIMIT_MS


@pytest.mark.asyncio
async def test_all_unauthenticated_variants_under_time_limit(client):
    scenarios = [
        ("GET", PROTECTED_GET_PATH, {}),
        ("POST", PROTECTED_POST_PATH, {}),
        ("DELETE", PROTECTED_DELETE_PATH, {}),
        ("GET", PROTECTED_GET_PATH, {"Authorization": ""}),
        ("GET", PROTECTED_GET_PATH, {"Authorization": "Bearer "}),
        ("GET", PROTECTED_GET_PATH, {"Authorization": "Bearer"}),
        ("GET", PROTECTED_GET_PATH, {"Authorization": "Basic dGVzdDp0ZXN0"}),
        ("GET", PROTECTED_GET_PATH, {"Authorization": "InvalidFormat token"}),
        ("POST", PROTECTED_POST_PATH, {"Authorization": "Bearer "}),
        ("POST", PROTECTED_POST_PATH, {"Authorization": ""}),
        ("DELETE", PROTECTED_DELETE_PATH, {"Authorization": ""}),
    ]
    for method, path, headers in scenarios:
        start = time.monotonic()
        if method == "GET":
            response = await client.get(path, headers=headers)
        elif method == "POST":
            response = await client.post(path, headers=headers)
        elif method == "DELETE":
            response = await client.delete(path, headers=headers)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert response.status_code == 401, (
            f"{method} {path} headers={headers} expected 401, got {response.status_code}"
        )
        assert elapsed_ms <= _TIME_LIMIT_MS, (
            f"{method} {path} took {elapsed_ms:.2f}ms, expected <= {_TIME_LIMIT_MS}ms"
        )
        body = response.json()
        assert "error" in body, (
            f"{method} {path} response missing 'error' key: {body}"
        )
        assert body["error"]["code"] == AUTH_ERROR_CODE, (
            f"{method} {path} expected error.code={AUTH_ERROR_CODE!r}, got {body['error']['code']!r}"
        )
