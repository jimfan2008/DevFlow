import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import verify_password, get_password_hash
import time


class TestChangePasswordVerifyOldV3:
    @pytest_asyncio.fixture(scope="function")
    async def test_user_pass123(self, db_session) -> User:
        user = User(
            id="user_test_pass123_v3",
            username="test_user_pass123_v3",
            email="test_pass123_v3@example.com",
            password_hash=get_password_hash("TestPass123"),
            role="user",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        yield user
        from conftest import _safe_delete
        _safe_delete(db_session, user)

    @pytest_asyncio.fixture(scope="function")
    async def auth_headers_pass123(self, test_user_pass123: User) -> dict:
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user_pass123.id)
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_change_password_verify_old_password(
        self,
        client: AsyncClient,
        test_user_pass123: User,
        auth_headers_pass123: dict,
        db_session: Session,
    ):
        old_password = "TestPass123"
        new_password = "NewPass123!@#456"

        start = time.monotonic()
        response = await client.post("/api/auth/change-password", json={
            "current_password": old_password,
            "new_password": new_password,
        }, headers=auth_headers_pass123)
        elapsed = (time.monotonic() - start) * 1000

        assert response.status_code == 200
        assert elapsed <= 300, f"Response time {elapsed:.0f}ms exceeds 300ms"
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "Password changed successfully"

        db_session.refresh(test_user_pass123)
        assert verify_password(new_password, test_user_pass123.password_hash) is True
        assert test_user_pass123.password_hash.startswith("$2b$") or test_user_pass123.password_hash.startswith("$2a$") or test_user_pass123.password_hash.startswith("$2y$")

        login_resp_old = await client.post("/api/auth/login", json={
            "username": test_user_pass123.username,
            "password": old_password,
        })
        assert login_resp_old.status_code == 401

        login_resp_new = await client.post("/api/auth/login", json={
            "username": test_user_pass123.username,
            "password": new_password,
        })
        assert login_resp_new.status_code == 200
