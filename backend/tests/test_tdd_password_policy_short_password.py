import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db, Base
from app.models.user import User

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)


def teardown_database():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            table.drop(conn, checkfirst=True)
        conn.commit()


@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    setup_database()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        teardown_database()


@pytest_asyncio.fixture(scope="function")
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


class TestTddPasswordPolicyShortPassword:
    REGISTER_URL = "/api/auth/register"

    @pytest.mark.asyncio
    async def test_short_password_returns_400(self, client, db_session):
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        }
        resp = await client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_short_password_error_code_is_VALID_001(self, client, db_session):
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        }
        resp = await client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "VALID-001"

    @pytest.mark.asyncio
    async def test_short_password_response_within_200ms(self, client, db_session):
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        }
        start = time.perf_counter()
        resp = await client.post(self.REGISTER_URL, json=payload)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 400
        assert elapsed_ms <= 200

    @pytest.mark.asyncio
    async def test_short_password_no_new_db_record(self, client, db_session):
        initial_count = db_session.query(User).count()
        payload = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        }
        resp = await client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 400
        final_count = db_session.query(User).count()
        assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_7_char_password_rejected(self, client, db_session):
        payload = {
            "username": "user7",
            "email": "user7@test.com",
            "password": "Abcdef1",
            "confirm_password": "Abcdef1",
        }
        resp = await client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_password_rejected(self, client, db_session):
        payload = {
            "username": "user0",
            "email": "user0@test.com",
            "password": "",
            "confirm_password": "",
        }
        resp = await client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_boundary_8_char_password_accepted(self, client, db_session):
        payload = {
            "username": "boundary8",
            "email": "boundary8@test.com",
            "password": "aB3@defg",
            "confirm_password": "aB3@defg",
        }
        resp = await client.post(self.REGISTER_URL, json=payload)
        assert resp.status_code == 201
