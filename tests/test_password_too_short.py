from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from datetime import datetime, timezone

app = FastAPI()

MOCK_USERS_DB = []

class RegisterBody(BaseModel):
    username: str
    password: str
    email: str

@app.post("/api/v1/auth/register")
async def register(body: RegisterBody):
    if len(body.password) < 8:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "VALID-001", "message": "密码长度不能少于8位"}}
        )
    record = {"username": body.username, "password": body.password, "email": body.email, "created_at": datetime.now(timezone.utc)}
    MOCK_USERS_DB.append(record)
    return {"code": 0, "message": "ok"}


class TestPasswordTooShort:
    def setup_method(self):
        MOCK_USERS_DB.clear()

    def test_short_password_returns_400(self):
        client = TestClient(app)
        body = {"username": "testuser", "password": "Ab1#", "email": "test@example.com"}
        resp = client.post("/api/v1/auth/register", json=body)
        assert resp.status_code == 400

    def test_short_password_contains_valid_001_code(self):
        client = TestClient(app)
        body = {"username": "testuser", "password": "Ab1#", "email": "test@example.com"}
        resp = client.post("/api/v1/auth/register", json=body)
        payload = resp.json()
        assert payload["detail"]["error"]["code"] == "VALID-001"

    def test_short_password_response_within_200ms(self):
        client = TestClient(app)
        body = {"username": "testuser", "password": "Ab1#", "email": "test@example.com"}
        import time
        start = time.perf_counter()
        resp = client.post("/api/v1/auth/register", json=body)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed <= 200

    def test_short_password_does_not_insert_into_db(self):
        client = TestClient(app)
        body = {"username": "testuser", "password": "Ab1#", "email": "test@example.com"}
        before = len(MOCK_USERS_DB)
        resp = client.post("/api/v1/auth/register", json=body)
        after = len(MOCK_USERS_DB)
        assert after == before

    def test_valid_password_succeeds(self):
        client = TestClient(app)
        body = {"username": "testuser", "password": "Ab1@cdef", "email": "test@example.com"}
        resp = client.post("/api/v1/auth/register", json=body)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["code"] == 0
