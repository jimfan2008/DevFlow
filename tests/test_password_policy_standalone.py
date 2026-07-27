import pytest
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db, Base
from app.models.user import User


TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

Base.metadata.create_all(bind=TEST_ENGINE)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class TestPasswordPolicyValidation:
    REGISTER_URL = "/api/auth/register"

    def _count_users(self) -> int:
        session = TestSessionLocal()
        try:
            return session.query(User).count()
        finally:
            session.close()

    def test_short_password_rejected(self):
        initial_count = self._count_users()

        payload = {
            "username": "shortpwduser",
            "email": "short@example.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        }

        client = TestClient(app)
        start = time.monotonic()
        resp = client.post(self.REGISTER_URL, json=payload)
        elapsed = (time.monotonic() - start) * 1000

        assert resp.status_code == 400
        resp_data = resp.json()
        assert resp_data["error"]["code"] == "VALID-001"

        assert elapsed <= 200, f"Response time {elapsed:.1f}ms exceeded 200ms"

        final_count = self._count_users()
        assert final_count == initial_count

    def test_empty_password_rejected(self):
        initial_count = self._count_users()

        payload = {
            "username": "emptypwduser",
            "email": "empty@example.com",
            "password": "",
            "confirm_password": "",
        }

        client = TestClient(app)
        start = time.monotonic()
        resp = client.post(self.REGISTER_URL, json=payload)
        elapsed = (time.monotonic() - start) * 1000

        assert resp.status_code == 400
        resp_data = resp.json()
        assert resp_data["error"]["code"] == "VALID-001"

        assert elapsed <= 200, f"Response time {elapsed:.1f}ms exceeded 200ms"

        final_count = self._count_users()
        assert final_count == initial_count

    def test_seven_char_password_rejected(self):
        initial_count = self._count_users()

        payload = {
            "username": "boundaryuser",
            "email": "boundary@example.com",
            "password": "Abcdef1",
            "confirm_password": "Abcdef1",
        }

        client = TestClient(app)
        start = time.monotonic()
        resp = client.post(self.REGISTER_URL, json=payload)
        elapsed = (time.monotonic() - start) * 1000

        assert resp.status_code == 400
        resp_data = resp.json()
        assert resp_data["error"]["code"] == "VALID-001"

        assert elapsed <= 200, f"Response time {elapsed:.1f}ms exceeded 200ms"

        final_count = self._count_users()
        assert final_count == initial_count

    def test_eight_char_password_not_rejected_with_valid_001(self):
        payload = {
            "username": "validpwduser",
            "email": "valid@example.com",
            "password": "Abcdef12",
            "confirm_password": "Abcdef12",
        }

        client = TestClient(app)
        resp = client.post(self.REGISTER_URL, json=payload)

        if resp.status_code == 400:
            resp_data = resp.json()
            error = resp_data.get("error", {})
            assert error.get("code") != "VALID-001", "Valid password should not trigger VALID-001"
