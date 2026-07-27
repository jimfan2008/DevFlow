import time
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

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


@pytest.mark.asyncio
@pytest.mark.tdd
class TestUnauthenticatedAccess:
    async def test_returns_401_when_no_auth_header(self, client):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401, (
            f"Expected 401, got {response.status_code}: {response.text}"
        )

    async def test_error_code_is_auth_001(self, client):
        response = await client.get("/api/auth/me")
        body = response.json()
        error_obj = body.get("error", body)
        assert error_obj.get("code") == "AUTH-001", (
            f"Expected error.code='AUTH-001', got: {error_obj.get('code')}"
        )

    async def test_response_time_within_100ms(self, client):
        start = time.perf_counter()
        await client.get("/api/auth/me")
        elapsed = time.perf_counter() - start
        assert elapsed <= 0.1, f"Response time {elapsed:.3f}s exceeded 100ms limit"
