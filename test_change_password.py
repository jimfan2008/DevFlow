import pytest
import time
import bcrypt
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()


def _make_fake_db():
    return {
        "testuser": {
            "username": "testuser",
            "password_hash": bcrypt.hashpw(
                b"TestPass123", bcrypt.gensalt()
            ).decode("utf-8"),
        }
    }


fake_users_db = _make_fake_db()


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


def get_current_user(username: str):
    user = fake_users_db.get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/change-password")
def change_password(req: ChangePasswordRequest):
    user = get_current_user(req.username)
    if not bcrypt.checkpw(
        req.old_password.encode("utf-8"),
        user["password_hash"].encode("utf-8"),
    ):
        raise HTTPException(status_code=403, detail="Old password is incorrect")
    new_hash = bcrypt.hashpw(
        req.new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    fake_users_db[req.username]["password_hash"] = new_hash
    return {"message": "Password changed successfully"}


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    """每个测试前后重置数据库，保证测试独立."""
    global fake_users_db
    fake_users_db = _make_fake_db()
    yield
    fake_users_db = _make_fake_db()


class TestChangePassword:
    def test_change_password_success_within_time_limit(self):
        start = time.time()
        response = client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
        )
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 0.3
        assert response.json()["message"] == "Password changed successfully"

    def test_password_hash_updated_to_bcrypt(self):
        client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
        )
        stored_hash = fake_users_db["testuser"]["password_hash"]
        assert stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$") or stored_hash.startswith("$2y$")
        assert bcrypt.checkpw(b"NewPass456", stored_hash.encode("utf-8"))

    def test_old_password_no_longer_valid(self):
        client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
        )
        assert not bcrypt.checkpw(
            b"TestPass123",
            fake_users_db["testuser"]["password_hash"].encode("utf-8"),
        )

    def test_wrong_old_password_rejected(self):
        response = client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "WrongPassword",
                "new_password": "NewPass456",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Old password is incorrect"
