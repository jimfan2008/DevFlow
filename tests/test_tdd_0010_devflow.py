import pytest
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
    with pytest.raises(HTTPException) as exc_info:
        validate_session(token_a)
    assert exc_info.value.status_code == 401
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

# 修复1：3台及以上设备并发验证
def test_three_or_more_devices_concurrent_login():
    token_a = create_session("user1")
    token_b = create_session("user1")
    token_c = create_session("user1")
    token_d = create_session("user1")
    tokens = {token_a, token_b, token_c, token_d}
    assert len(tokens) == 4, "4台设备应生成4个不同的token"
    for token in tokens:
        response = client.get("/me", params={"token": token})
        assert response.status_code == 200
        assert response.json() == {"user_id": "user1"}
    logout_session(token_b)
    with pytest.raises(HTTPException):
        validate_session(token_b)
    for token in tokens - {token_b}:
        session = validate_session(token)
        assert session["user_id"] == "user1"

# 修复2：重新登录场景
def test_device_relogin_after_logout():
    token_a = create_session("user1")
    client.post("/logout", params={"token": token_a})
    response = client.get("/me", params={"token": token_a})
    assert response.status_code == 401
    new_token = create_session("user1")
    assert new_token != token_a
    response = client.get("/me", params={"token": new_token})
    assert response.status_code == 200
    assert response.json() == {"user_id": "user1"}

# 修复3：created_at 字段断言
def test_session_created_at_field():
    before_time = time.time()
    token = create_session("user1")
    after_time = time.time()
    session = sessions[token]
    assert "created_at" in session
    assert isinstance(session["created_at"], float)
    assert before_time <= session["created_at"] <= after_time

# 修复4a：空 token 的 401 处理
def test_empty_token_returns_401():
    response = client.get("/me", params={"token": ""})
    assert response.status_code == 401

# 修复4b：非法 token 的 401 处理
def test_invalid_token_returns_401():
    response = client.get("/me", params={"token": "not-a-valid-token"})
    assert response.status_code == 401

# 修复4c：已持有 token 的设备重复 create_session
def test_device_with_existing_token_creates_new_session():
    token_a = create_session("user1")
    token_b = create_session("user1")
    assert token_a != token_b
    session_a = validate_session(token_a)
    session_b = validate_session(token_b)
    assert session_a["user_id"] == "user1"
    assert session_b["user_id"] == "user1"
    assert isinstance(session_a["created_at"], float)
    assert isinstance(session_b["created_at"], float)

# 修复4d：token 格式（有效 UUID）断言
def test_token_is_valid_uuid():
    token = create_session("user1")
    assert uuid.UUID(token)
    assert isinstance(token, str)
    assert len(token) == 36

# 修复4e：大量并发 session 测试
def test_large_number_of_concurrent_sessions():
    num_sessions = 1000
    tokens = []
    for i in range(num_sessions):
        token = create_session(f"user{i % 10}")
        tokens.append(token)
    assert len(set(tokens)) == num_sessions
    for i, token in enumerate(tokens):
        session = validate_session(token)
        assert session["user_id"] == f"user{i % 10}"
    logout_session(tokens[500])
    with pytest.raises(HTTPException):
        validate_session(tokens[500])
    for i, token in enumerate(tokens):
        if i != 500:
            session = validate_session(token)
            assert session["user_id"] == f"user{i % 10}"
