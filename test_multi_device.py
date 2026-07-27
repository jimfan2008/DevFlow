import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, Response, HTTPException
from fastapi.testclient import TestClient
import uuid
import time

app = FastAPI()

sessions: dict[str, dict] = {}

def create_session(user_id: str) -> str:
    token = str(uuid.uuid4())
    sessions[token] = {"user_id": user_id, "created_at": time.time()}
    return token

def validate_session(token: str) -> dict:
    if token not in sessions:
        raise HTTPException(status_code=401, detail="session not found")
    return sessions[token]

def logout_session(token: str) -> None:
    if token in sessions:
        del sessions[token]

@app.get("/me")
def get_me(token: str):
    session = validate_session(token)
    return {"user_id": session["user_id"]}

@app.post("/logout")
def logout(token: str):
    logout_session(token)
    return {"ok": True}

@pytest.fixture(autouse=True)
def clear_sessions():
    sessions.clear()
    yield

client = TestClient(app)

def test_multi_device_login_returns_independent_tokens():
    token_a = create_session("user1")
    token_b = create_session("user1")
    assert token_a != token_b

def test_each_device_can_access_independently():
    token_a = create_session("user1")
    token_b = create_session("user1")
    response_a = client.get("/me", params={"token": token_a})
    response_b = client.get("/me", params={"token": token_b})
    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.json() == {"user_id": "user1"}
    assert response_b.json() == {"user_id": "user1"}

def test_device_b_session_independent_from_device_a():
    token_a = create_session("user1")
    token_b = create_session("user1")
    logout_session(token_a)
    with pytest.raises(HTTPException):
        validate_session(token_a)
    session_b = validate_session(token_b)
    assert session_b["user_id"] == "user1"

def test_logout_device_a_only_clears_device_a():
    token_a = create_session("user1")
    token_b = create_session("user1")
    client.post("/logout", params={"token": token_a})
    response_a = client.get("/me", params={"token": token_a})
    assert response_a.status_code == 401
    response_b = client.get("/me", params={"token": token_b})
    assert response_b.status_code == 200
    assert response_b.json() == {"user_id": "user1"}

def test_empty_token_returns_401():
    response = client.get("/me", params={"token": ""})
    assert response.status_code == 401

def test_missing_token_returns_422():
    response = client.get("/me")
    assert response.status_code == 422

def test_invalid_token_returns_401():
    response = client.get("/me", params={"token": "fake-token-123"})
    assert response.status_code == 401

def test_double_logout_does_not_raise():
    token = create_session("user1")
    client.post("/logout", params={"token": token})
    response = client.post("/logout", params={"token": token})
    assert response.status_code == 200
    assert response.json() == {"ok": True}

def test_concurrent_session_creation():
    tokens = [create_session("user1") for _ in range(100)]
    assert len(set(tokens)) == 100
    for t in tokens:
        resp = client.get("/me", params={"token": t})
        assert resp.status_code == 200
