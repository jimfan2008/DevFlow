from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, HTTPException
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

def test_device_b_access_returns_200():
    token_b = create_session("user1")
    response = client.get("/me", params={"token": token_b})
    assert response.status_code == 200
    assert response.json() == {"user_id": "user1"}

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
