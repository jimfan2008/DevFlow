import time
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError


CUSTOM_404_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>404 - Not Found</title></head>
<body style="text-align:center;padding:80px 20px;font-family:sans-serif;">
  <h1>404</h1>
  <p>Page Not Found</p>
  <div class="actions">
    <a href="/" class="btn-home">Home</a>
    <div class="search-entry">
      <form action="/search" method="get">
        <input type="text" name="q" placeholder="search..." />
        <button type="submit">Search</button>
      </form>
    </div>
  </div>
</body>
</html>"""


def build_test_app() -> FastAPI:
    test_app = FastAPI(title="TestApp")

    @test_app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return HTMLResponse(
                status_code=404,
                content=CUSTOM_404_HTML,
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": f"HTTP_{exc.status_code}", "message": str(exc.detail), "details": {}},
        )

    @test_app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": "Validation failed", "details": {}})

    @test_app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {}})

    @test_app.get("/")
    def root():
        return {"message": "OK"}

    @test_app.get("/api/v1/health")
    def health():
        return {"status": "healthy"}

    @test_app.get("/search")
    def search(q: str = ""):
        return {"results": []}

    return test_app


@pytest_asyncio.fixture(scope="function")
async def client():
    test_app = build_test_app()
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


UNKNOWN_GET_ROUTES = [
    "/nonexistent",
    "/api/unknown",
    "/api/v1/notfound",
    "/this/path/does/not/exist",
    "/api/boards/99999",
    "/api/tasks/nonexistent-task-id",
    "/random-page-123",
    "/api/v99/unknown",
    "/api/v2/undefined",
    "/page/not/found/here",
]


@pytest.mark.asyncio
class Test404UnknownRoute:

    async def test_unknown_root_path_returns_404(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404

    async def test_unknown_api_path_returns_404(self, client):
        for route in UNKNOWN_GET_ROUTES:
            response = await client.get(route)
            assert response.status_code == 404, f"unknown route {route} returned {response.status_code}, expected 404"

    async def test_unknown_post_returns_404(self, client):
        response = await client.post("/api/nonexistent-resource")
        assert response.status_code == 404

    async def test_unknown_put_returns_404(self, client):
        response = await client.put("/api/unknown-item-999")
        assert response.status_code == 404

    async def test_unknown_delete_returns_404(self, client):
        response = await client.delete("/api/v1/unknown-delete")
        assert response.status_code == 404

    async def test_unknown_patch_returns_404(self, client):
        response = await client.patch("/api/unknown-patch-target")
        assert response.status_code == 404

    async def test_deeply_nested_unknown_path_returns_404(self, client):
        deep_routes = [
            "/a/b/c/d/e/f/g",
            "/api/v1/workflow/unknown-step-99",
            "/api/projects/unknown/sprints/backlog",
            "/api/boards/not-a-board/tasks/nonexistent",
            "/x/y/z/1/2/3/4/5",
        ]
        for route in deep_routes:
            response = await client.get(route)
            assert response.status_code == 404, f"deep unknown route {route} returned {response.status_code}, expected 404"

    async def test_unknown_path_response_is_html(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type, f"404 Content-Type is not text/html: {content_type}"

    async def test_404_response_not_blank(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        body = response.text.strip()
        assert len(body) > 0, "404 response body is empty (blank)"

    async def test_custom_404_page_displays_404_text(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        assert "404" in response.text, "custom 404 page does not display 404 text"

    async def test_custom_404_page_contains_return_home_button(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        assert "Home" in response.text, "custom 404 page missing home button"
        assert "btn-home" in response.text or 'href="/"' in response.text, "custom 404 page missing home link"

    async def test_custom_404_page_contains_search_entry(self, client):
        response = await client.get("/api/v99/invalid-path")
        assert response.status_code == 404
        search_keywords = ["Search", "search", "search-entry"]
        found = any(kw in response.text for kw in search_keywords)
        assert found, "custom 404 page missing search entry"

    async def test_custom_404_page_not_blank(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        assert len(response.text.strip()) > 0, "404 page content is empty (blank screen)"
        assert response.text != "", "404 page should not be empty string"

    async def test_known_routes_do_not_return_404(self, client):
        known_routes = ["/", "/api/v1/health", "/search"]
        for route in known_routes:
            response = await client.get(route)
            assert response.status_code != 404, f"known route {route} incorrectly returned 404"

    async def test_non_ascii_unknown_path_returns_404(self, client):
        response = await client.get("/%E8%B7%AF%E5%BE%84/%E4%B8%8D%E5%AD%98%E5%9C%A8")
        assert response.status_code == 404

    async def test_unknown_path_with_query_string_returns_404(self, client):
        response = await client.get("/nonexistent?foo=bar&baz=1")
        assert response.status_code == 404

    async def test_404_response_time_within_500ms(self, client):
        for route in UNKNOWN_GET_ROUTES:
            start = time.perf_counter()
            response = await client.get(route)
            elapsed = time.perf_counter() - start
            assert response.status_code == 404
            assert elapsed <= 0.5, f"route {route} 404 response took {elapsed:.3f}s, exceeds 500ms"

    async def test_404_response_time_within_500ms_on_second_call(self, client):
        for route in UNKNOWN_GET_ROUTES:
            await client.get(route)
        for route in UNKNOWN_GET_ROUTES:
            start = time.perf_counter()
            response = await client.get(route)
            elapsed = time.perf_counter() - start
            assert response.status_code == 404
            assert elapsed <= 0.5, f"route {route} second 404 call took {elapsed:.3f}s, exceeds 500ms"

    async def test_known_prefix_unknown_resource_returns_404(self, client):
        known_prefixes = ["/api", "/api/v1", "/api/auth"]
        for prefix in known_prefixes:
            route = prefix + "/non-existent-resource"
            response = await client.get(route)
            assert response.status_code == 404, f"known prefix {prefix} unknown path returned {response.status_code}, expected 404"

    async def test_404_renders_valid_html(self, client):
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        assert response.text.strip().startswith("<!DOCTYPE html>") or response.text.strip().startswith("<html"), "404 page should be valid HTML"
        assert "</html>" in response.text, "404 page missing closing html tag"

    async def test_cors_headers_on_404_response(self, client):
        response = await client.get("/nonexistent", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 404

    async def test_multiple_concurrent_404_requests_all_return_404(self, client):
        async def check_route(route):
            resp = await client.get(route)
            return resp.status_code == 404 and len(resp.text.strip()) > 0
        results = await asyncio.gather(*[check_route(r) for r in UNKNOWN_GET_ROUTES[:5]])
        assert all(results), "not all concurrent 404 requests returned valid 404"
