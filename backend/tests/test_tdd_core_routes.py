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
        id="user_cr_001",
        username="cr_test_user",
        email="cr_test@example.com",
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


PUBLIC_GET_ROUTES = [
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
]

PROTECTED_GET_ROUTES = [
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


@pytest.mark.asyncio
@pytest.mark.tdd
class TestCoreRoutesAccessibility:

    async def test_root_returns_200(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_docs_returns_200(self, client):
        response = await client.get("/docs")
        assert response.status_code == 200

    async def test_redoc_returns_200(self, client):
        response = await client.get("/redoc")
        assert response.status_code == 200

    async def test_openapi_json_returns_200(self, client):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "openapi" in data

    async def test_all_public_routes_return_200(self, client):
        for route in PUBLIC_GET_ROUTES:
            response = await client.get(route)
            assert response.status_code == 200, (
                f"公共路由 {route} 返回 {response.status_code}，期望 200"
            )

    async def test_protected_routes_return_401_without_auth(self, client):
        for route in PROTECTED_GET_ROUTES:
            response = await client.get(route)
            assert response.status_code in (401, 403), (
                f"受保护路由 {route} 无认证返回 {response.status_code}，期望 401/403"
            )

    async def test_protected_routes_return_200_with_auth(self, authorized_client):
        for route in PROTECTED_GET_ROUTES:
            response = await authorized_client.get(route)
            assert response.status_code in (200, 201, 204), (
                f"受保护路由 {route} 有认证返回 {response.status_code}，期望 200/201/204"
            )

    async def test_first_route_load_within_2s(self, client):
        start = time.perf_counter()
        response = await client.get("/health")
        elapsed = time.perf_counter() - start
        assert response.status_code == 200
        assert elapsed <= FIRST_LOAD_TIMEOUT, (
            f"首屏加载耗时 {elapsed:.3f}s，超过 {FIRST_LOAD_TIMEOUT}s"
        )

    async def test_consecutive_routes_within_300ms(self, client, authorized_client):
        routes = [r for r in (PUBLIC_GET_ROUTES + PROTECTED_GET_ROUTES) if r not in ROUTE_SWITCH_SKIP]
        for route in routes:
            cl = authorized_client if route in PROTECTED_GET_ROUTES else client
            _ = await cl.get(route)
        for route in routes:
            cl = authorized_client if route in PROTECTED_GET_ROUTES else client
            start = time.perf_counter()
            response = await cl.get(route)
            elapsed = time.perf_counter() - start
            assert elapsed <= ROUTE_SWITCH_TIMEOUT, (
                f"路由 {route} 切换耗时 {elapsed:.3f}s，超过 {ROUTE_SWITCH_TIMEOUT}s"
            )

    async def test_discover_endpoint_within_1s(self, client):
        await client.get("/api/v1/discover")
        start = time.perf_counter()
        response = await client.get("/api/v1/discover")
        elapsed = time.perf_counter() - start
        assert response.status_code == 200
        assert elapsed <= 1.0, (
            f"路由 /api/v1/discover 耗时 {elapsed:.3f}s，超过 1s"
        )

    async def test_openapi_contains_all_expected_paths(self, client):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        missing = [p for p in PROTECTED_GET_ROUTES if p not in paths]
        assert not missing, f"OpenAPI 定义中缺少路径: {missing}"

    async def test_all_registered_routes_are_in_openapi(self, client):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json().get("paths", {})
        registered_paths = {
            r.path for r in app.routes if hasattr(r, "methods") and "GET" in r.methods
        }
        registered_clean = {p for p in registered_paths if "{param" not in p and p not in ("/", "/health", "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect")}
        missing_from_openapi = {p for p in registered_clean if p not in paths}
        assert not missing_from_openapi, (
            f"以下已注册路由不在 OpenAPI 定义中: {missing_from_openapi}"
        )
