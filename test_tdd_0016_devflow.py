import pytest
import asyncio
from unittest.mock import patch, MagicMock


class MockRequest:
    def __init__(self, url, headers=None, method="GET"):
        self.url = url
        self.headers = headers or {}
        self.method = method


class MockResponse:
    def __init__(self, status_code, json_data, elapsed_ms=0):
        self.status_code = status_code
        self._json_data = json_data
        self.elapsed_ms = elapsed_ms

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class AuthMiddleware:
    def __init__(self, excluded_paths=None):
        self.excluded_paths = excluded_paths or []

    async def authenticate(self, request):
        token = request.headers.get("Authorization")
        if not token:
            return None, {"error": {"code": "AUTH-001", "message": "Missing authorization token"}}
        if not token.startswith("Bearer "):
            return None, {"error": {"code": "AUTH-001", "message": "Invalid authorization scheme"}}
        return {"user_id": 1, "role": "user"}, None

    async def __call__(self, request):
        path = request.url
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return None
        user, error = await self.authenticate(request)
        if error:
            return error
        return None


class MockFastAPIApp:
    def __init__(self):
        self.auth_middleware = AuthMiddleware(excluded_paths=["/api/v1/auth/login", "/api/v1/auth/register"])
        self.routes = {}

    def add_route(self, method, path, handler, auth_required=True):
        self.routes[(method, path)] = {"handler": handler, "auth_required": auth_required}

    async def dispatch(self, request):
        auth_result = await self.auth_middleware(request)
        if auth_result is not None:
            return MockResponse(401, auth_result, elapsed_ms=15)
        route_key = (request.method, request.url)
        route = self.routes.get(route_key)
        if not route:
            return MockResponse(404, {"error": {"code": "NOT_FOUND", "message": "Not found"}}, elapsed_ms=5)
        if not request.headers.get("Authorization"):
            return MockResponse(401, {"error": {"code": "AUTH-001", "message": "Missing authorization token"}}, elapsed_ms=15)
        handler = route["handler"]
        result = await handler(request)
        return result


@pytest.fixture
def app():
    return MockFastAPIApp()


@pytest.fixture
def protected_routes(app):
    async def get_profile(request):
        return MockResponse(200, {"data": {"user_id": 1, "name": "Test User"}}, elapsed_ms=10)

    async def create_project(request):
        return MockResponse(201, {"data": {"id": 1, "name": "Project"}}, elapsed_ms=20)

    async def delete_project(request):
        return MockResponse(204, None, elapsed_ms=5)

    app.add_route("GET", "/api/v1/user/profile", get_profile)
    app.add_route("POST", "/api/v1/projects", create_project)
    app.add_route("DELETE", "/api/v1/projects/1", delete_project)
    return app


@pytest.mark.asyncio
async def test_unauthenticated_get_profile_returns_401(app, protected_routes):
    request = MockRequest("/api/v1/user/profile", method="GET")
    response = await app.dispatch(request)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    json_data = response.json()
    assert json_data["error"]["code"] == "AUTH-001", (
        f"Expected error code AUTH-001, got {json_data['error']['code']}"
    )


@pytest.mark.asyncio
async def test_unauthenticated_post_project_returns_401(app, protected_routes):
    request = MockRequest("/api/v1/projects", method="POST")
    response = await app.dispatch(request)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    json_data = response.json()
    assert json_data["error"]["code"] == "AUTH-001", (
        f"Expected error code AUTH-001, got {json_data['error']['code']}"
    )


@pytest.mark.asyncio
async def test_unauthenticated_delete_project_returns_401(app, protected_routes):
    request = MockRequest("/api/v1/projects/1", method="DELETE")
    response = await app.dispatch(request)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    json_data = response.json()
    assert json_data["error"]["code"] == "AUTH-001", (
        f"Expected error code AUTH-001, got {json_data['error']['code']}"
    )


@pytest.mark.asyncio
async def test_expired_token_returns_401(app, protected_routes):
    request = MockRequest(
        "/api/v1/user/profile",
        headers={"Authorization": "Bearer expired_token_abc123"},
        method="GET"
    )
    response = await app.dispatch(request)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    json_data = response.json()
    assert json_data["error"]["code"] == "AUTH-001", (
        f"Expected error code AUTH-001, got {json_data['error']['code']}"
    )


@pytest.mark.asyncio
async def test_invalid_token_format_returns_401(app, protected_routes):
    request = MockRequest(
        "/api/v1/user/profile",
        headers={"Authorization": "Token invalid_format"},
        method="GET"
    )
    response = await app.dispatch(request)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    json_data = response.json()
    assert json_data["error"]["code"] == "AUTH-001", (
        f"Expected error code AUTH-001, got {json_data['error']['code']}"
    )


@pytest.mark.asyncio
async def test_empty_authorization_header_returns_401(app, protected_routes):
    request = MockRequest(
        "/api/v1/user/profile",
        headers={"Authorization": ""},
        method="GET"
    )
    response = await app.dispatch(request)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    json_data = response.json()
    assert json_data["error"]["code"] == "AUTH-001", (
        f"Expected error code AUTH-001, got {json_data['error']['code']}"
    )


@pytest.mark.asyncio
async def test_authenticated_request_succeeds(app, protected_routes):
    request = MockRequest(
        "/api/v1/user/profile",
        headers={"Authorization": "Bearer valid_token_xyz789"},
        method="GET"
    )
    response = await app.dispatch(request)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


@pytest.mark.asyncio
async def test_response_time_within_limit(app, protected_routes):
    request = MockRequest("/api/v1/user/profile", method="GET")
    response = await app.dispatch(request)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert response.elapsed_ms <= 100, (
        f"Response time {response.elapsed_ms}ms exceeded 100ms limit"
    )


@pytest.mark.asyncio
async def test_auth_error_body_structure(app, protected_routes):
    request = MockRequest("/api/v1/user/profile", method="GET")
    response = await app.dispatch(request)
    json_data = response.json()
    assert "error" in json_data, "Response must contain 'error' field"
    assert "code" in json_data["error"], "Error object must contain 'code' field"
    assert "message" in json_data["error"], "Error object must contain 'message' field"
    assert json_data["error"]["code"] == "AUTH-001", (
        f"Expected error code AUTH-001, got {json_data['error']['code']}"
    )


@pytest.mark.asyncio
async def test_public_endpoint_accessible_without_token(app, protected_routes):
    request = MockRequest("/api/v1/auth/login", method="POST")
    result = await app.auth_middleware(request)
    assert result is None, "Public endpoint should bypass authentication"
