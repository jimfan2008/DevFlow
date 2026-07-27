import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

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

REGISTER_URL = "/api/auth/register"

class TestPasswordPolicyValidation:
    def _count_users(self):
        session = TestSessionLocal()
        try:
            return session.query(User).count()
        finally:
            session.close()

    def _register(self, username, email, password):
        return TestClient(app).post(
            REGISTER_URL,
            json={
                "username": username,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )

    def test_short_password_rejected(self):
        initial_count = self._count_users()
        resp = self._register("shortpwduser", "short@example.com", "Ab1")
        assert resp.status_code == 400
        resp_data = resp.json()
        assert resp_data["error"]["code"] == "VALID-001"
        final_count = self._count_users()
        assert final_count == initial_count

    def test_empty_password_rejected(self):
        initial_count = self._count_users()
        resp = self._register("emptypwduser", "empty@example.com", "")
        assert resp.status_code == 400
        resp_data = resp.json()
        assert resp_data["error"]["code"] == "VALID-001"
        final_count = self._count_users()
        assert final_count == initial_count

    def test_seven_char_password_rejected(self):
        initial_count = self._count_users()
        resp = self._register("boundary7user", "boundary7@example.com", "Abcdef1")
        assert resp.status_code == 400
        resp_data = resp.json()
        assert resp_data["error"]["code"] == "VALID-001"
        final_count = self._count_users()
        assert final_count == initial_count

    def test_eight_char_password_accepted(self):
        resp = self._register("eightuser", "eight@example.com", "aB3@defg")
        assert resp.status_code == 201

    def test_twelve_char_password_accepted(self):
        resp = self._register("twelveuser", "twelve@example.com", "aB3@defghijk")
        assert resp.status_code == 201

    def test_fifteen_char_password_accepted(self):
        resp = self._register("fifteenuser", "fifteen@example.com", "aB3@defghijklmno")
        assert resp.status_code == 201
