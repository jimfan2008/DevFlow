import time
import pytest
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException

AUTH_ERROR_CODE = "AUTH-001"
PROTECTED_PATH = "/api/auth/me"


def get_current_user(authorization: str = Header(None)):
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


async def auth_exception_handler(request, exc: StarletteHTTPException):
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
app.add_exception_handler(StarletteHTTPException, auth_exception_handler)


@app.get(PROTECTED_PATH)
def protected_endpoint(current_user=Depends(get_current_user)):
    return {"user": current_user}


class TestUnauthorizedAccessToProtectedAPI:

    def setup_method(self):
        self.client = TestClient(app)

    def test_returns_401_when_no_auth_header(self):
        response = self.client.get(PROTECTED_PATH)
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_returns_401_when_invalid_token(self):
        response = self.client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer invalid_token_xxxxx"},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_returns_401_when_empty_bearer_token(self):
        response = self.client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_returns_401_when_wrong_auth_scheme(self):
        response = self.client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    def test_error_code_is_auth_001(self):
        response = self.client.get(PROTECTED_PATH)
        body = response.json()
        assert response.status_code == 401
        assert "error" in body, f"response missing 'error' key: {body}"
        assert body["error"]["code"] == AUTH_ERROR_CODE, (
            f"expected error.code={AUTH_ERROR_CODE!r}, "
            f"got {body['error']['code']!r}"
        )

    def test_error_message_present(self):
        response = self.client.get(PROTECTED_PATH)
        body = response.json()
        assert "error" in body
        assert "message" in body["error"], (
            f"error object missing 'message' key: {body['error']}"
        )
        assert len(body["error"]["message"]) > 0

    def test_response_time_within_100ms(self):
        self.client.get(PROTECTED_PATH)
        start = time.perf_counter()
        self.client.get(PROTECTED_PATH)
        elapsed = time.perf_counter() - start
        assert elapsed <= 0.1, (
            f"response time {elapsed * 1000:.1f}ms exceeded 100ms"
        )

    def test_authorized_request_succeeds(self):
        response = self.client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer valid_token_abc123"},
        )
        assert response.status_code == 200, (
            f"expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["user"]["user_id"] == "user_valid_001"
        assert body["user"]["username"] == "testuser"

    def test_authorized_request_not_affected_by_unauthorized(self):
        self.client.get(PROTECTED_PATH)
        response = self.client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer valid_token_abc123"},
        )
        assert response.status_code == 200

    def test_consecutive_unauthorized_requests_all_return_401(self):
        for _ in range(5):
            response = self.client.get(PROTECTED_PATH)
            assert response.status_code == 401, (
                f"expected 401 on consecutive call, got {response.status_code}"
            )
            assert response.json()["error"]["code"] == AUTH_ERROR_CODE

    def test_response_header_contains_www_authenticate(self):
        response = self.client.get(PROTECTED_PATH)
        assert response.status_code == 401
        assert "www-authenticate" in response.headers, (
            f"missing WWW-Authenticate header: {dict(response.headers)}"
        )
        assert "Bearer" in response.headers["www-authenticate"]