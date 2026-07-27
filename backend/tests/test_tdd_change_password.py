import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import verify_password, hash_password


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, test_user: User, auth_headers: dict, db_session: Session):
        old_password = "test123456"
        new_password = "NewPass123!456"

        response = await client.post("/api/auth/change-password", json={
            "current_password": old_password,
            "new_password": new_password,
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "Password changed successfully"

        db_session.refresh(test_user)
        assert verify_password(new_password, test_user.password_hash) is True

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self, client: AsyncClient, test_user: User, auth_headers: dict, db_session: Session):
        response = await client.post("/api/auth/change-password", json={
            "current_password": "wrong_password_123",
            "new_password": "NewPass123!456",
        }, headers=auth_headers)

        assert response.status_code == 400
        data = response.json()
        assert "Incorrect password" in str(data.get("message", "")) or "Incorrect password" in str(data.get("detail", ""))

        db_session.refresh(test_user)
        assert verify_password("test123456", test_user.password_hash) is True

    @pytest.mark.asyncio
    async def test_change_password_response_time(self, client: AsyncClient, test_user: User, auth_headers: dict):
        import time

        start = time.monotonic()
        response = await client.post("/api/auth/change-password", json={
            "current_password": "test123456",
            "new_password": "NewPass123!456",
        }, headers=auth_headers)
        elapsed = (time.monotonic() - start) * 1000

        assert response.status_code == 200
        assert elapsed <= 1000, f"Response time {elapsed:.0f}ms exceeds 1000ms"

    @pytest.mark.asyncio
    async def test_old_password_no_longer_works_after_change(self, client: AsyncClient, test_user: User, auth_headers: dict):
        old_password = "test123456"
        new_password = "NewPass123!456"

        change_resp = await client.post("/api/auth/change-password", json={
            "current_password": old_password,
            "new_password": new_password,
        }, headers=auth_headers)
        assert change_resp.status_code == 200

        login_resp = await client.post("/api/auth/login", json={
            "username": test_user.username,
            "password": old_password,
        })
        assert login_resp.status_code == 401

        login_resp_new = await client.post("/api/auth/login", json={
            "username": test_user.username,
            "password": new_password,
        })
        assert login_resp_new.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_updates_bcrypt_hash(self, client: AsyncClient, test_user: User, auth_headers: dict, db_session: Session):
        old_hash = test_user.password_hash

        response = await client.post("/api/auth/change-password", json={
            "current_password": "test123456",
            "new_password": "NewPass123!456",
        }, headers=auth_headers)
        assert response.status_code == 200

        db_session.refresh(test_user)
        new_hash = test_user.password_hash

        assert new_hash != old_hash
        assert new_hash.startswith("$2b$") or new_hash.startswith("$2a$") or new_hash.startswith("$2y$")
