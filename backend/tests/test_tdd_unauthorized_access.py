#!/usr/bin/env python3
import time
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.utils.security import get_password_hash

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def setup_db():
    Base.metadata.create_all(bind=TEST_ENGINE)


def teardown_db():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    setup_db()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        teardown_db()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def existing_user(db_session):
    user = User(
        id="user_unauth_001",
        username="unauth_test_user",
        email="unauth_test@example.com",
        password_hash=get_password_hash("TestPass123"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    try:
        db_session.rollback()
        db_session.delete(user)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest_asyncio.fixture(scope="function")
async def valid_token(existing_user):
    from app.utils.security import create_access_token
    return create_access_token(user_id=existing_user.id)


@pytest_asyncio.fixture(scope="function")
async def authorized_client(client, valid_token):
    client.headers["Authorization"] = f"Bearer {valid_token}"
    yield client


PROTECTED_ENDPOINT = "/api/auth/me"


@pytest.mark.asyncio
@pytest.mark.tdd
class TestUnauthorizedAccess:
    async def test_returns_401_when_no_auth_header(self, client):
        response = await client.get(PROTECTED_ENDPOINT)
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    async def test_returns_401_when_invalid_token(self, client):
        response = await client.get(
            PROTECTED_ENDPOINT,
            headers={"Authorization": "Bearer invalid_token_xxxxx"},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    async def test_returns_401_when_empty_bearer(self, client):
        response = await client.get(
            PROTECTED_ENDPOINT,
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    async def test_returns_401_when_wrong_scheme(self, client):
        response = await client.get(
            PROTECTED_ENDPOINT,
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )
        assert response.status_code == 401, (
            f"expected 401, got {response.status_code}: {response.text}"
        )

    async def test_response_contains_auth001_error_code(self, client):
        response = await client.get(PROTECTED_ENDPOINT)
        body = response.json()
        assert response.status_code == 401
        assert "error" in body, f"response missing 'error' key: {body}"
        assert body["error"].get("code") == "AUTH-001", (
            f"expected error.code='AUTH-001', got: {body['error'].get('code')}"
        )

    async def test_response_time_within_100ms(self, client):
        response = await client.get(PROTECTED_ENDPOINT)
        assert response.status_code == 401
        start = time.perf_counter()
        await client.get(PROTECTED_ENDPOINT)
        elapsed = time.perf_counter() - start
        assert elapsed <= 0.1, f"response timeout: {elapsed:.3f}s > 100ms"

    async def test_authorized_request_succeeds(self, authorized_client):
        response = await authorized_client.get(PROTECTED_ENDPOINT)
        assert response.status_code == 200, (
            f"expected 200, got {response.status_code}: {response.text}"
        )
