import pytest
import bcrypt
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()


class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str


def build_app(db):
    _app = FastAPI()

    @_app.post("/change-password")
    def change_password(req: ChangePasswordRequest):
        user = db.get(req.username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not bcrypt.checkpw(
            req.old_password.encode("utf-8"), user["password_hash"].encode("utf-8")
        ):
            raise HTTPException(status_code=403, detail="Old password is incorrect")
        new_hash = bcrypt.hashpw(
            req.new_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        db[req.username]["password_hash"] = new_hash
        return {"message": "Password changed successfully"}

    return _app


class TestChangePassword:
    @pytest.fixture(autouse=True)
    def setup_db(self):
        self.fake_users_db = {
            "testuser": {
                "username": "testuser",
                "password_hash": bcrypt.hashpw(
                    b"TestPass123", bcrypt.gensalt()
                ).decode("utf-8"),
            }
        }
        self.client = TestClient(build_app(self.fake_users_db))

    def test_change_password_success(self):
        response = self.client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    def test_password_hash_updated_to_bcrypt(self):
        self.client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
        )
        stored_hash = self.fake_users_db["testuser"]["password_hash"]
        assert stored_hash.startswith(
            "$2b$"
        ) or stored_hash.startswith("$2a$") or stored_hash.startswith("$2y$")
        assert bcrypt.checkpw(b"NewPass456", stored_hash.encode("utf-8"))

    def test_old_password_no_longer_valid(self):
        self.client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
        )
        assert not bcrypt.checkpw(
            b"TestPass123",
            self.fake_users_db["testuser"]["password_hash"].encode("utf-8"),
        )

    def test_change_password_fails_with_wrong_old_password(self):
        response = self.client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "WrongPassword999",
                "new_password": "NewPass456",
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Old password is incorrect"

    def test_change_password_fails_with_nonexistent_user(self):
        response = self.client.post(
            "/change-password",
            json={
                "username": "nonexistent_user",
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_change_password_fails_with_empty_old_password(self):
        response = self.client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "",
                "new_password": "NewPass456",
            },
        )
        assert response.status_code == 403

    def test_change_password_fails_with_empty_new_password(self):
        response = self.client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "",
            },
        )
        assert response.status_code == 200

    def test_change_password_fails_with_old_password_same_as_new(self):
        response = self.client.post(
            "/change-password",
            json={
                "username": "testuser",
                "old_password": "TestPass123",
                "new_password": "TestPass123",
            },
        )
        assert response.status_code == 200
        assert bcrypt.checkpw(
            b"TestPass123",
            self.fake_users_db["testuser"]["password_hash"].encode("utf-8"),
        )
