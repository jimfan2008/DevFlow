import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from fastapi.exceptions import RequestValidationError

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    for e in errors:
        if e.get("type") == "value_error" and "VALID-001" in str(e.get("msg", "")):
            return JSONResponse(status_code=400, content={"error": {"code": "VALID-001"}})
    safe_errors = []
    for e in errors:
        safe = dict(e)
        if "ctx" in safe:
            safe["ctx"] = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in safe["ctx"].items()}
        safe_errors.append(safe)
    return JSONResponse(status_code=422, content={"detail": safe_errors})

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
    return {"ok": True}

client = TestClient(app)

def test_short_password_returns_400_with_valid_001():
    resp = client.post("/register", json={"username": "user1", "password": "abc"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"

def test_empty_password_returns_400():
    resp = client.post("/register", json={"username": "user1", "password": ""})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"

def test_seven_char_password_returns_400():
    resp = client.post("/register", json={"username": "user1", "password": "a" * 7})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"

def test_eight_char_password_returns_200():
    resp = client.post("/register", json={"username": "user1", "password": "a" * 8})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

def test_long_password_returns_200():
    resp = client.post("/register", json={"username": "user1", "password": "a" * 20})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

def test_excessive_length_password_returns_200():
    resp = client.post("/register", json={"username": "user1", "password": "a" * 1001})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

def test_unicode_chinese_password_returns_200():
    resp = client.post("/register", json={"username": "user1", "password": "密码策略测试密码"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

def test_unicode_chinese_short_password_returns_400():
    resp = client.post("/register", json={"username": "user1", "password": "密码短"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"

def test_emoji_password_returns_200():
    resp = client.post("/register", json={"username": "user1", "password": "😀😀😀😀😀😀😀😀"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

def test_emoji_short_password_returns_400():
    resp = client.post("/register", json={"username": "user1", "password": "😀😀😀"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "VALID-001"