import pytest
import time
from app.models.user import User


class TestPasswordPolicyValidation:
    REGISTER_URL = "/api/auth/register"

    @pytest.mark.asyncio
    async def test_short_password_rejected(self, client, db_session):
        initial_count = db_session.query(User).count()

        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        }

        start = time.monotonic()
        resp = await client.post(self.REGISTER_URL, json=payload)
        elapsed = (time.monotonic() - start) * 1000

        assert resp.status_code == 400

        body = resp.json()
        assert body["error"]["code"] == "VALID-001"

        assert elapsed <= 200, f"Response time {elapsed:.1f}ms exceeded 200ms"

        final_count = db_session.query(User).count()
        assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_empty_password_rejected(self, client, db_session):
        initial_count = db_session.query(User).count()

        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "",
            "confirm_password": "",
        }

        start = time.monotonic()
        resp = await client.post(self.REGISTER_URL, json=payload)
        elapsed = (time.monotonic() - start) * 1000

        assert resp.status_code == 400

        body = resp.json()
        assert body["error"]["code"] == "VALID-001"

        assert elapsed <= 200, f"Response time {elapsed:.1f}ms exceeded 200ms"

        final_count = db_session.query(User).count()
        assert final_count == initial_count
