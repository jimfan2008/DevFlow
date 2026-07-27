#!/usr/bin/env python3

import sys
import os
import time
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.main import app
from app.database import get_db, Base
from app.models.user import User

REGISTER_URL = "/api/auth/register"

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    yield session
    session.close()
    with TEST_ENGINE.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                conn.execute(table.delete())
            except Exception:
                pass


@pytest.fixture
async def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


def _make_short_password_payload() -> dict:
    suffix = uuid.uuid4().hex[:6]
    return {
        "username": f"user_{suffix}",
        "email": f"{suffix}@test.com",
        "password": "Ab1",
        "confirm_password": "Ab1",
    }


class TestPasswordPolicyShortPassword:

    @pytest.mark.asyncio
    async def test_short_password_returns_http_400(self, client: AsyncClient):
        payload = _make_short_password_payload()
        resp = await client.post(REGISTER_URL, json=payload)
        assert resp.status_code == 400, f"expected 400, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_short_password_error_code(self, client: AsyncClient):
        payload = _make_short_password_payload()
        resp = await client.post(REGISTER_URL, json=payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body, "response missing 'error' field"
        assert "code" in body["error"], "response error missing 'code' field"
        assert body["error"]["code"] == "VALID-001", f"expected VALID-001, got {body['error'].get('code')}"

    @pytest.mark.asyncio
    async def test_short_password_response_time(self, client: AsyncClient):
        payload = _make_short_password_payload()
        start = time.perf_counter()
        resp = await client.post(REGISTER_URL, json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 400
        assert elapsed_ms <= 200, f"response time {elapsed_ms:.1f}ms exceeds 200ms"

    @pytest.mark.asyncio
    async def test_short_password_no_db_record(self, client: AsyncClient, db_session: Session):
        initial_count = db_session.query(User).count()
        payload = _make_short_password_payload()
        resp = await client.post(REGISTER_URL, json=payload)
        assert resp.status_code == 400
        final_count = db_session.query(User).count()
        assert final_count == initial_count, f"expected {initial_count} records, found {final_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
