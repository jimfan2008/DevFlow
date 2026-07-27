import time
import pytest
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as StarletteHTTPException

AUTH_ERROR_CODE = "AUTH-001"
PROTECTED_PATH = "/api/protected"


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


async def http_exception_handler(request, exc: StarletteHTTPException):
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

    def test_returns_401_when_no_auth_header(self, client):
        response = client.get(PROTECTED_PATH)
        assert response.status_code == 401

    def test_returns_401_when_invalid_token(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer invalid_token_xxxxx"},
        )
        assert response.status_code == 401

    def test_returns_401_when_empty_bearer_token(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    def test_returns_401_when_wrong_auth_scheme(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )
        assert response.status_code == 401

    def test_error_code_is_auth_001(self, client):
        response = client.get(PROTECTED_PATH)
        body = response.json()
        assert response.status_code == 401
        assert "error" in body
        assert body["error"]["code"] == AUTH_ERROR_CODE

    def test_error_message_present(self, client):
        response = client.get(PROTECTED_PATH)
        body = response.json()
        assert "error" in body
        assert "message" in body["error"]
        assert len(body["error"]["message"]) > 0

    def test_response_time_within_100ms(self, client):
        start = time.perf_counter()
        client.get(PROTECTED_PATH)
        elapsed = time.perf_counter() - start
        assert elapsed <= 0.1

    def test_authorized_request_succeeds(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer valid_token_abc123"},
        )
        assert response.status_code == 200
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
            assert response.status_code == 401
            assert response.json()["error"]["code"] == AUTH_ERROR_CODE

    def test_www_authenticate_header_present(self, client):
        response = client.get(PROTECTED_PATH)
        assert response.status_code == 401
        assert "www-authenticate" in response.headers
        assert "Bearer" in response.headers["www-authenticate"]

    def test_response_time_stays_under_100ms_across_scenarios(self, client):
        scenarios = [
            {},
            {"Authorization": "Bearer invalid_token_xxxxx"},
            {"Authorization": "Basic dGVzdDp0ZXN0"},
        ]
        for headers in scenarios:
            start = time.perf_counter()
            client.get(PROTECTED_PATH, headers=headers)
            elapsed = time.perf_counter() - start
            assert elapsed <= 0.1

    def test_malformed_token_returns_401(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "NotBearer something"},
        )
        assert response.status_code == 401

    def test_token_with_extra_whitespace_returns_401(self, client):
        response = client.get(
            PROTECTED_PATH,
            headers={"Authorization": "Bearer   "},
        )
        assert response.status_code == 401
