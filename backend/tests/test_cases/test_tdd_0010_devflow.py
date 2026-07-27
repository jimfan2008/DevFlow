import uuid
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

app = FastAPI()
sessions: dict = {}


@app.post("/api/auth/login")
def login(username: str, password: str):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"user_id": username, "active": True}
    return {"session_id": session_id}


@app.get("/api/me")
def me(token: str = None):
    if not token or token not in sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session = sessions[token]
    if not session["active"]:
        raise HTTPException(status_code=401, detail="Session inactive")
    return {"user_id": session["user_id"], "session_id": token}


@app.post("/api/auth/logout")
def logout(token: str = None):
    if token and token in sessions:
        sessions[token]["active"] = False
    return {"code": 0, "message": "Logout successful", "data": None}


@pytest.fixture(autouse=True)
def _reset_sessions():
    sessions.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


class TestMultiDeviceLogin:
    def test_same_user_can_login_on_multiple_devices(self, client):
        r_a = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        r_b = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        assert r_a.status_code == 200
        assert r_b.status_code == 200
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        assert sid_a != sid_b

    def test_device_b_access_returns_200(self, client):
        r_b = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        sid_b = r_b.json()["session_id"]
        resp = client.get("/api/me", params={"token": sid_b})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "testuser"

    def test_device_b_session_independent_from_device_a(self, client):
        r_a = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        r_b = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        assert sid_a != sid_b
        resp_a = client.get("/api/me", params={"token": sid_a})
        resp_b = client.get("/api/me", params={"token": sid_b})
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["user_id"] == "testuser"
        assert resp_b.json()["user_id"] == "testuser"

    def test_device_a_logout_only_clears_device_a_session(self, client):
        r_a = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        r_b = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        logout_resp = client.post("/api/auth/logout", params={"token": sid_a})
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Logout successful"
        resp_a = client.get("/api/me", params={"token": sid_a})
        assert resp_a.status_code == 401
        resp_b = client.get("/api/me", params={"token": sid_b})
        assert resp_b.status_code == 200
        assert resp_b.json()["user_id"] == "testuser"

    def test_logout_idempotency(self, client):
        r_a = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
        sid_a = r_a.json()["session_id"]
        client.post("/api/auth/logout", params={"token": sid_a})
        resp2 = client.post("/api/auth/logout", params={"token": sid_a})
        assert resp2.status_code == 200
        resp = client.get("/api/me", params={"token": sid_a})
        assert resp.status_code == 401

    def test_multiple_logins_produce_distinct_tokens(self, client):
        tokens = set()
        for _ in range(5):
            r = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
            tokens.add(r.json()["session_id"])
        assert len(tokens) == 5

    def test_different_tokens_are_all_active(self, client):
        tokens = []
        for _ in range(3):
            r = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
            tokens.append(r.json()["session_id"])
        for sid in tokens:
            resp = client.get("/api/me", params={"token": sid})
            assert resp.status_code == 200

    def test_logout_only_affects_specified_session(self, client):
        tokens = []
        for _ in range(3):
            r = client.post("/api/auth/login", params={"username": "testuser", "password": "pass123"})
            tokens.append(r.json()["session_id"])
        client.post("/api/auth/logout", params={"token": tokens[1]})
        for i, sid in enumerate(tokens):
            resp = client.get("/api/me", params={"token": sid})
            if i == 1:
                assert resp.status_code == 401
            else:
                assert resp.status_code == 200

    def test_no_token_returns_401(self, client):
        resp = client.get("/api/me", params={"token": None})
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get("/api/me", params={"token": "invalid-token"})
        assert resp.status_code == 401

    def test_empty_token_returns_401(self, client):
        resp = client.get("/api/me", params={"token": ""})
        assert resp.status_code == 401

    def test_logout_nonexistent_token_succeeds(self, client):
        resp = client.post("/api/auth/logout", params={"token": "nonexistent"})
        assert resp.status_code == 200

    def test_three_devices_logout_middle_one(self, client):
        r_a = client.post("/api/auth/login", params={"username": "alice", "password": "p"})
        r_b = client.post("/api/auth/login", params={"username": "alice", "password": "p"})
        r_c = client.post("/api/auth/login", params={"username": "alice", "password": "p"})
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        sid_c = r_c.json()["session_id"]
        client.post("/api/auth/logout", params={"token": sid_b})
        resp_a = client.get("/api/me", params={"token": sid_a})
        resp_b = client.get("/api/me", params={"token": sid_b})
        resp_c = client.get("/api/me", params={"token": sid_c})
        assert resp_a.status_code == 200
        assert resp_b.status_code == 401
        assert resp_c.status_code == 200
        assert resp_a.json()["user_id"] == "alice"
        assert resp_c.json()["user_id"] == "alice"

    def test_session_count_after_logout(self, client):
        r_a = client.post("/api/auth/login", params={"username": "u1", "password": "p"})
        r_b = client.post("/api/auth/login", params={"username": "u1", "password": "p"})
        r_c = client.post("/api/auth/login", params={"username": "u1", "password": "p"})
        sid_b = r_b.json()["session_id"]
        client.post("/api/auth/logout", params={"token": sid_b})
        active_count = sum(1 for s in sessions.values() if s["active"])
        assert active_count == 2

    def test_different_users_have_isolated_sessions(self, client):
        r_a = client.post("/api/auth/login", params={"username": "alice", "password": "p"})
        r_b = client.post("/api/auth/login", params={"username": "bob", "password": "p"})
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        client.post("/api/auth/logout", params={"token": sid_a})
        resp_a = client.get("/api/me", params={"token": sid_a})
        resp_b = client.get("/api/me", params={"token": sid_b})
        assert resp_a.status_code == 401
        assert resp_b.status_code == 200
        assert resp_b.json()["user_id"] == "bob"

    def test_rapid_multi_login_all_active(self, client):
        sids = []
        for i in range(10):
            r = client.post("/api/auth/login", params={"username": f"user{i % 3}", "password": "p"})
            assert r.status_code == 200
            sids.append(r.json()["session_id"])
        for sid in sids:
            resp = client.get("/api/me", params={"token": sid})
            assert resp.status_code == 200
