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
        id="user_cpr_001",
        username="cpr_test_user",
        email="cpr_test@example.com",
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


CORE_PAGE_ROUTES = [
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/discover",
    "/api/v1/hermes/status",
    "/api/hermes/health",
    "/api/profiles",
    "/api/v1/qa/status",
    "/api/projects/chat/test",
    "/api/auth/me",
    "/api/boards",
    "/api/tasks",
    "/api/projects",
    "/api/agents",
    "/api/hermes/status",
    "/api/hermes/diagnose",
    "/api/groups",
    "/api/repos",
    "/api/notifications",
    "/api/notifications/unread-count",
    "/api/task-states",
    "/api/skills",
    "/api/acceptance",
]

FIRST_LOAD_TIMEOUT = 2.0
ROUTE_SWITCH_TIMEOUT = 0.3
ROUTE_SWITCH_SKIP = {"/api/v1/discover"}

PUBLIC_ROUTES = {"/", "/health", "/docs", "/redoc", "/openapi.json", "/api/v1/discover", "/api/v1/hermes/status", "/api/hermes/health", "/api/profiles", "/api/v1/qa/status", "/api/projects/chat/test"}
PROTECTED_ROUTES = {"/api/auth/me", "/api/boards", "/api/tasks", "/api/projects", "/api/agents", "/api/hermes/status", "/api/hermes/diagnose", "/api/groups", "/api/repos", "/api/notifications", "/api/notifications/unread-count", "/api/task-states", "/api/skills", "/api/acceptance"}


@pytest.mark.asyncio
@pytest.mark.tdd
class TestCorePageRoutesAccessible:

    async def test_all_core_routes_return_200_with_auth(self, authorized_client):
        for route in CORE_PAGE_ROUTES:
            response = await authorized_client.get(route)
            assert response.status_code in (200, 201, 204), (
                f"核心路由 {route} 返回 {response.status_code}，期望 200/201/204"
            )

    async def test_first_screen_load_within_2s(self, client):
        start = time.perf_counter()
        response = await client.get("/")
        elapsed = time.perf_counter() - start
        assert response.status_code == 200
        assert elapsed <= FIRST_LOAD_TIMEOUT, (
            f"首屏加载耗时 {elapsed:.3f}s，超过 {FIRST_LOAD_TIMEOUT}s"
        )

    async def test_root_returns_valid_json(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    async def test_public_routes_within_300ms(self, client):
        for route in PUBLIC_ROUTES:
            _ = await client.get(route)
        for route in PUBLIC_ROUTES:
            start = time.perf_counter()
            response = await client.get(route)
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            assert elapsed <= ROUTE_SWITCH_TIMEOUT, (
                f"公共路由 {route} 切换耗时 {elapsed:.3f}s，超过 {ROUTE_SWITCH_TIMEOUT}s"
            )

    async def test_protected_routes_switch_within_300ms(self, authorized_client):
        warmed = list(PROTECTED_ROUTES)
        for route in warmed:
            _ = await authorized_client.get(route)
        for route in warmed:
            start = time.perf_counter()
            response = await authorized_client.get(route)
            elapsed = time.perf_counter() - start
            assert response.status_code in (200, 201, 204)
            assert elapsed <= ROUTE_SWITCH_TIMEOUT, (
                f"受保护路由 {route} 切换耗时 {elapsed:.3f}s，超过 {ROUTE_SWITCH_TIMEOUT}s"
            )

    async def test_health_endpoint_healthy(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_openapi_contains_core_paths(self, client):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        for route in CORE_PAGE_ROUTES:
            assert route in paths, (
                f"OpenAPI 定义中缺少核心路由: {route}"
            )
