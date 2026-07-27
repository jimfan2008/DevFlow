import pytest
from fastapi import FastAPI, HTTPException, Form
from fastapi.testclient import TestClient

app = FastAPI()

sessions: dict = {}


@app.post("/login")
def login(user_id: str = Form(default="")):
    import uuid
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"user_id": user_id, "active": True}
    return {"session_id": session_id}


@app.get("/me")
def me(token: str):
    session = sessions.get(token)
    if not session or not session["active"]:
        raise HTTPException(status_code=401, detail="Invalid or inactive session")
    return {"user_id": session["user_id"]}


@app.post("/logout")
def logout(token: str):
    if token in sessions:
        sessions[token]["active"] = False
    return {"ok": True}


@pytest.fixture(autouse=True)
def _reset_sessions():
    sessions.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ---------- 核心场景 ----------

class TestMultiDeviceLogin:
    def test_user_can_login_on_multiple_devices(self, client):
        r_a = client.post("/login", data={"user_id": "user123"})
        r_b = client.post("/login", data={"user_id": "user123"})
        assert r_a.status_code == 200
        assert r_b.status_code == 200
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        assert sid_a != sid_b

    def test_device_b_access_returns_200(self, client):
        r_b = client.post("/login", data={"user_id": "user123"})
        sid_b = r_b.json()["session_id"]
        resp = client.get("/me", params={"token": sid_b})
        assert resp.status_code == 200

    def test_device_b_session_independent_from_device_a(self, client):
        r_a = client.post("/login", data={"user_id": "user123"})
        r_b = client.post("/login", data={"user_id": "user123"})
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        assert sid_a != sid_b
        resp_a = client.get("/me", params={"token": sid_a})
        resp_b = client.get("/me", params={"token": sid_b})
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["user_id"] == "user123"
        assert resp_b.json()["user_id"] == "user123"

    def test_device_a_logout_does_not_affect_device_b(self, client):
        r_a = client.post("/login", data={"user_id": "user123"})
        r_b = client.post("/login", data={"user_id": "user123"})
        sid_a = r_a.json()["session_id"]
        sid_b = r_b.json()["session_id"]
        client.post("/logout", params={"token": sid_a})
        resp_a = client.get("/me", params={"token": sid_a})
        assert resp_a.status_code == 401
        resp_b = client.get("/me", params={"token": sid_b})
        assert resp_b.status_code == 200
        assert resp_b.json()["user_id"] == "user123"

    def test_active_sessions_count_after_single_logout(self, client):
        r_a = client.post("/login", data={"user_id": "user123"})
        r_b = client.post("/login", data={"user_id": "user123"})
        r_c = client.post("/login", data={"user_id": "user123"})
        sid_b = r_b.json()["session_id"]
        client.post("/logout", params={"token": sid_b})
        active = [sid for sid, data in sessions.items()
                   if data["user_id"] == "user123" and data["active"]]
        assert len(active) == 2


# ---------- 边界 / 异常场景 ----------

class TestEdgeCases:
    def test_invalid_token_returns_401(self, client):
        resp = client.get("/me", params={"token": "invalid"})
        assert resp.status_code == 401

    def test_empty_string_token_returns_401(self, client):
        resp = client.get("/me", params={"token": ""})
        assert resp.status_code == 401

    def test_empty_user_id_creates_session(self, client):
        r = client.post("/login", data={"user_id": ""})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        resp = client.get("/me", params={"token": sid})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == ""

    def test_logout_nonexistent_token_does_not_error(self, client):
        resp = client.post("/logout", params={"token": "nonexistent"})
        assert resp.status_code == 200

    def test_logout_already_logged_out_token_is_idempotent(self, client):
        r = client.post("/login", data={"user_id": "user123"})
        sid = r.json()["session_id"]
        client.post("/logout", params={"token": sid})
        resp2 = client.post("/logout", params={"token": sid})
        assert resp2.status_code == 200
        resp_me = client.get("/me", params={"token": sid})
        assert resp_me.status_code == 401

    def test_multiple_logins_same_user_produce_distinct_tokens(self, client):
        tokens = set()
        for _ in range(5):
            r = client.post("/login", data={"user_id": "user123"})
            tokens.add(r.json()["session_id"])
        assert len(tokens) == 5

    def test_token_missing_returns_422(self, client):
        resp = client.get("/me")
        assert resp.status_code == 422
