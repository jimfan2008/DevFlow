import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from pydantic import BaseModel, field_validator

app = FastAPI()

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

@pytest.mark.parametrize("password,error_type,error_substr", [
    ("abc", "value_error", "VALID-001"),
    ("", "value_error", "VALID-001"),
    ("a" * 7, "value_error", "VALID-001"),
    (123, "string_type", "Input should be a valid string"),
    (None, "string_type", "Input should be a valid string"),
])
def test_short_password_returns_422_with_valid_001(password, error_type, error_substr):
    resp = client.post("/register", json={"username": "user1", "password": password})
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"][0]["type"] == error_type
    assert error_substr in body["detail"][0]["msg"]

@pytest.mark.parametrize("password", ["a" * 8, "a" * 20])
def test_valid_password_returns_200(password):
    resp = client.post("/register", json={"username": "user1", "password": password})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
