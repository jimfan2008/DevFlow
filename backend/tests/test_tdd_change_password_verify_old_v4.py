import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import verify_password, hash_password, create_access_token
import time


class TestChangePasswordVerifyOld:
    @pytest.mark.asyncio
    async def test_change_password_verify_old_password(
        self, client: AsyncClient, db_session: Session
    ):
        old_password = "TestPass123"
        new_password = "NewPass123!@#456"

        user = User(
            id="test_change_pw_verify_v4",
            username="change_pw_verify_v4",
            email="change_pw_verify_v4@test.com",
            password_hash=hash_password(old_password),
            role="user",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        token = create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {token}"}

        start = time.monotonic()
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": old_password,
                "new_password": new_password,
            },
            headers=headers,
        )
        elapsed = (time.monotonic() - start) * 1000

        assert response.status_code == 200
        assert elapsed <= 1000, f"Response time {elapsed:.0f}ms exceeds 1000ms"
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "Password changed successfully"

        db_session.refresh(user)
        assert verify_password(new_password, user.password_hash) is True
        assert user.password_hash.startswith(("$2b$", "$2a$", "$2y$"))

        login_resp_old = await client.post(
            "/api/auth/login",
            json={
                "username": user.username,
                "password": old_password,
            },
        )
        assert login_resp_old.status_code == 401

        login_resp_new = await client.post(
            "/api/auth/login",
            json={
                "username": user.username,
                "password": new_password,
            },
        )
        assert login_resp_new.status_code == 200
