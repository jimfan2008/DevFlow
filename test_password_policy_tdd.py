import pytest
import time
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from fastapi.exceptions import RequestValidationError

_registered_users: list = []

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    for e in errors:
        if e.get("type") == "value_error" and "VALID-001" in str(e.get("msg", "")):
            return JSONResponse(status_code=400, content={"error": {"code": "VALID-001"}})
    return JSONResponse(status_code=422, content={"detail": errors})

class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("VALID-001")
        return v

@app.post("/register")
def register(body: RegisterRequest):
    _registered_users.append({"username": body.username, "password": body.password})
    return {"ok": True}

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db():
    _registered_users.clear()
    yield

def test_short_password_returns_400_with_valid_001():
    resp = client.post("/register", json={"username": "user1", "password": "abc"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"

def test_short_password_response_time_within_200ms():
    start = time.monotonic()
    resp = client.post("/register", json={"username": "user1", "password": "abc"})
    elapsed_ms = (time.monotonic() - start) * 1000
    assert resp.status_code == 400
    assert elapsed_ms <= 200

def test_short_password_does_not_create_record():
    initial_count = len(_registered_users)
    client.post("/register", json={"username": "user1", "password": "abc"})
    assert len(_registered_users) == initial_count

def test_eight_char_password_returns_200():
    resp = client.post("/register", json={"username": "user1", "password": "a" * 8})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

def test_seven_char_password_returns_400():
    resp = client.post("/register", json={"username": "user1", "password": "a" * 7})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"

def test_eight_char_password_creates_record():
    client.post("/register", json={"username": "user1", "password": "a" * 8})
    assert len(_registered_users) == 1

def test_empty_password_returns_400_with_valid_001():
    resp = client.post("/register", json={"username": "user1", "password": ""})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"

def test_null_password_returns_422():
    resp = client.post("/register", json={"username": "user1", "password": None})
    assert resp.status_code == 422

def test_non_string_password_returns_422():
    resp = client.post("/register", json={"username": "user1", "password": 12345})
    assert resp.status_code == 422
