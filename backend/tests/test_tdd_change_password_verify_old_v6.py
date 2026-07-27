import pytest
import pytest_asyncio
import time
from httpx import AsyncClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import get_password_hash, verify_password, create_access_token

OLD_PASSWORD = "TestPass123"
NEW_PASSWORD = "NewSecurePass456!"


@pytest_asyncio.fixture
async def test_user_custom(db_session: Session) -> User:
    user = User(
        id="user_pwd_test_001",
        username="test_user_pwd",
        email="test_pwd@example.com",
        password_hash=get_password_hash(OLD_PASSWORD),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    try:
        db_session.delete(user)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture
async def auth_headers_custom(test_user_custom: User) -> dict:
    token = create_access_token(user_id=test_user_custom.id)
    return {"Authorization": f"Bearer {token}"}


class TestChangePasswordVerifyOld:
    @pytest.mark.asyncio
    async def test_change_password_verify_old_success(
        self,
        client: AsyncClient,
        test_user_custom: User,
        auth_headers_custom: dict,
        db_session: Session,
    ):
        start = time.monotonic()
        response = await client.post(
            "/api/auth/change-password",
            json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
            headers=auth_headers_custom,
        )
        elapsed = (time.monotonic() - start) * 1000

        assert response.status_code == 200
        assert elapsed <= 300, f"Response time {elapsed:.0f}ms exceeds 300ms"
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "Password changed successfully"

        db_session.refresh(test_user_custom)
        assert test_user_custom.password_hash.startswith("$2b$")
        assert verify_password(NEW_PASSWORD, test_user_custom.password_hash) is True

    @pytest.mark.asyncio
    async def test_old_password_no_longer_works_after_change(
        self,
        client: AsyncClient,
        test_user_custom: User,
        auth_headers_custom: dict,
    ):
        change_resp = await client.post(
            "/api/auth/change-password",
            json={"current_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
            headers=auth_headers_custom,
        )
        assert change_resp.status_code == 200

        login_resp = await client.post(
            "/api/auth/login",
            json={"username": test_user_custom.username, "password": OLD_PASSWORD},
        )
        assert login_resp.status_code == 401

        login_resp_new = await client.post(
            "/api/auth/login",
            json={"username": test_user_custom.username, "password": NEW_PASSWORD},
        )
        assert login_resp_new.status_code == 200
