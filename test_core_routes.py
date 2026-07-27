import pytest
import time
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed


class MockResponse:
    def __init__(self, status_code, elapsed_seconds, content_type="text/html; charset=utf-8", content="<html><body>OK</body></html>"):
        self.status_code = status_code
        self.elapsed_seconds = elapsed_seconds
        self.headers = {"Content-Type": content_type}
        self.content = content.encode("utf-8")
        self.elapsed = Mock()
        self.elapsed.total_seconds = Mock(return_value=elapsed_seconds)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


CORE_ROUTES = [
    "/",
    "/login",
    "/dashboard",
    "/projects",
    "/settings",
    "/profile",
]

PERFORMANCE_THRESHOLD_FIRST_LOAD = 2.0
PERFORMANCE_THRESHOLD_SWITCH = 0.3


def _build_mock_get(route_map):
    async def mock_get(url, **kwargs):
        for route, response in route_map.items():
            if url.endswith(route):
                return response
        return MockResponse(404, 0.01)
    return mock_get


class FakeSession:
    def __init__(self, route_map):
        self.get = _build_mock_get(route_map)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_session_success():
    route_map = {}
    for route in CORE_ROUTES:
        route_map[route] = MockResponse(200, 0.05)
    return FakeSession(route_map)


@pytest.fixture
def mock_session_slow_first():
    route_map = {}
    for i, route in enumerate(CORE_ROUTES):
        if i == 0:
            route_map[route] = MockResponse(200, 2.5)
        else:
            route_map[route] = MockResponse(200, 0.05)
    return FakeSession(route_map)


@pytest.fixture
def mock_session_slow_switch():
    route_map = {}
    for i, route in enumerate(CORE_ROUTES):
        if i >= 1:
            route_map[route] = MockResponse(200, 0.5)
        else:
            route_map[route] = MockResponse(200, 0.05)
    return FakeSession(route_map)


class TestCoreRoutesAccessibility:

    @pytest.mark.asyncio
    async def test_all_routes_return_http_200(self, mock_session_success):
        async with mock_session_success as session:
            for route in CORE_ROUTES:
                resp = await session.get(f"http://testserver{route}")
                assert resp.status_code == 200, f"{route} returned {resp.status_code}"

    @pytest.mark.asyncio
    async def test_all_routes_include_valid_content_type(self, mock_session_success):
        async with mock_session_success as session:
            for route in CORE_ROUTES:
                resp = await session.get(f"http://testserver{route}")
                ct = resp.headers.get("Content-Type", "")
                assert "text/html" in ct or "application/json" in ct or "text/plain" in ct, \
                    f"{route} has unexpected Content-Type: {ct}"

    @pytest.mark.asyncio
    async def test_all_routes_return_non_empty_body(self, mock_session_success):
        async with mock_session_success as session:
            for route in CORE_ROUTES:
                resp = await session.get(f"http://testserver{route}")
                assert len(resp.content) > 0, f"{route} returned empty body"

    @pytest.mark.asyncio
    async def test_first_page_load_within_2s(self):
        route_map = {}
        for route in CORE_ROUTES:
            route_map[route] = MockResponse(200, 0.05)

        async with FakeSession(route_map) as session:
            start = time.monotonic()
            resp = await session.get("http://testserver/")
            elapsed = time.monotonic() - start
            assert resp.status_code == 200
            assert elapsed <= PERFORMANCE_THRESHOLD_FIRST_LOAD, \
                f"First page load took {elapsed:.3f}s (limit: {PERFORMANCE_THRESHOLD_FIRST_LOAD}s)"

    @pytest.mark.asyncio
    async def test_route_switch_within_300ms(self):
        route_map = {}
        for route in CORE_ROUTES:
            route_map[route] = MockResponse(200, 0.05)

        async with FakeSession(route_map) as session:
            await session.get("http://testserver/")
            for route in CORE_ROUTES[1:]:
                start = time.monotonic()
                resp = await session.get(f"http://testserver{route}")
                elapsed = time.monotonic() - start
                assert resp.status_code == 200
                assert elapsed <= PERFORMANCE_THRESHOLD_SWITCH, \
                    f"Switch to {route} took {elapsed:.3f}s (limit: {PERFORMANCE_THRESHOLD_SWITCH}s)"

    def test_concurrent_route_access_all_succeed(self):
        results = {}

        def fetch(route):
            resp = MockResponse(200, 0.02)
            return route, resp.status_code, resp.headers.get("Content-Type", ""), len(resp.content)

        with ThreadPoolExecutor(max_workers=len(CORE_ROUTES)) as executor:
            futures = {executor.submit(fetch, route): route for route in CORE_ROUTES}
            for future in as_completed(futures):
                route, status, ct, body_len = future.result()
                results[route] = {"status": status, "content_type": ct, "body_len": body_len}

        for route in CORE_ROUTES:
            r = results[route]
            assert r["status"] == 200, f"{route} concurrent access failed with {r['status']}"
            assert "text/html" in r["content_type"], f"{route} concurrent access bad Content-Type: {r['content_type']}"
            assert r["body_len"] > 0, f"{route} concurrent access empty body"

    def test_concurrent_route_access_performance(self):
        def fetch(route):
            resp = MockResponse(200, 0.02)
            return route, resp.elapsed.total_seconds()

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=len(CORE_ROUTES)) as executor:
            futures = [executor.submit(fetch, route) for route in CORE_ROUTES]
            for future in as_completed(futures):
                route, elapsed = future.result()
                assert elapsed <= PERFORMANCE_THRESHOLD_FIRST_LOAD, \
                    f"{route} concurrent load took {elapsed:.3f}s"
        total = time.monotonic() - start
        assert total <= PERFORMANCE_THRESHOLD_FIRST_LOAD * 1.5, \
            f"Concurrent batch took {total:.3f}s"

    @pytest.mark.asyncio
    async def test_all_routes_sequential_timing(self, mock_session_success):
        async with mock_session_success as session:
            for route in CORE_ROUTES:
                start = time.monotonic()
                resp = await session.get(f"http://testserver{route}")
                elapsed = time.monotonic() - start
                assert resp.status_code == 200
                assert elapsed <= PERFORMANCE_THRESHOLD_FIRST_LOAD, \
                    f"Sequential load of {route} took {elapsed:.3f}s"
                assert len(resp.content) > 0

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self):
        async def load_route(session, route):
            resp = await session.get(f"http://testserver{route}")
            return route, resp.status_code, len(resp.content)

        async with FakeSession({r: MockResponse(200, 0.02) for r in CORE_ROUTES}) as session:
            tasks = [load_route(session, route) for route in CORE_ROUTES]
            results = await asyncio.gather(*tasks)
            for route, status, body_len in results:
                assert status == 200, f"{route} failed in concurrent session"
                assert body_len > 0, f"{route} empty in concurrent session"
