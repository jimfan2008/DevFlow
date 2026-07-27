import asyncio
import time
import pytest


class LazyRoute:
    def __init__(self, path: str, component_name: str, load_delay: float = 0.5):
        self.path = path
        self.component_name = component_name
        self.load_delay = load_delay
        self._loaded = False
        self._component = None

    async def load_component(self) -> str:
        start = time.monotonic()
        await asyncio.sleep(self.load_delay)
        self._component = f"<{self.component_name}>rendered</{self.component_name}>"
        self._loaded = True
        elapsed = time.monotonic() - start
        return self._component, elapsed

    @property
    def is_loaded(self) -> bool:
        return self._loaded


class RouteManager:
    def __init__(self):
        self.routes: list[LazyRoute] = []
        self._active_route: str | None = None
        self._route_cache: dict[str, str] = {}

    def add_route(self, route: LazyRoute) -> None:
        self.routes.append(route)

    async def navigate_to(self, path: str) -> float:
        route = next((r for r in self.routes if r.path == path), None)
        if route is None:
            raise ValueError(f"Route not found: {path}")
        start = time.monotonic()
        if path not in self._route_cache:
            component, _ = await route.load_component()
            self._route_cache[path] = component
        else:
            await asyncio.sleep(0.05)
        self._active_route = path
        return time.monotonic() - start

    def get_active_route(self) -> str | None:
        return self._active_route

    def is_route_cached(self, path: str) -> bool:
        return path in self._route_cache


@pytest.fixture
def route_manager():
    manager = RouteManager()
    manager.add_route(LazyRoute("/home", "HomePage", 0.3))
    manager.add_route(LazyRoute("/about", "AboutPage", 0.5))
    manager.add_route(LazyRoute("/dashboard", "DashboardPage", 1.2))
    manager.add_route(LazyRoute("/settings", "SettingsPage", 0.8))
    manager.add_route(LazyRoute("/profile", "ProfilePage", 1.8))
    return manager


@pytest.mark.asyncio
async def test_first_load_within_2_seconds(route_manager):
    durations = []
    for route in route_manager.routes:
        elapsed = await route_manager.navigate_to(route.path)
        durations.append(elapsed)
        assert elapsed <= 2.0, (
            f"Route {route.path} first load took {elapsed:.3f}s, "
            f"exceeds 2s limit"
        )
    for path, duration in zip([r.path for r in route_manager.routes], durations):
        assert duration <= 2.0, (
            f"Route {path} first load took {duration:.3f}s, exceeds 2s limit"
        )


@pytest.mark.asyncio
async def test_route_switch_time_within_300ms(route_manager):
    for route in route_manager.routes:
        await route_manager.navigate_to(route.path)
    switch_durations = []
    paths = ["/home", "/about", "/dashboard", "/settings", "/profile"]
    for i in range(len(paths) - 1):
        elapsed = await route_manager.navigate_to(paths[i + 1])
        switch_durations.append(elapsed)
        assert elapsed <= 0.3, (
            f"Switch from {paths[i]} to {paths[i + 1]} took {elapsed:.3f}s, "
            f"exceeds 300ms limit"
        )


@pytest.mark.asyncio
async def test_cached_route_loads_fast(route_manager):
    for route in route_manager.routes:
        await route_manager.navigate_to(route.path)
    for route in route_manager.routes:
        assert route_manager.is_route_cached(route.path)
    for route in route_manager.routes:
        elapsed = await route_manager.navigate_to(route.path)
        assert elapsed <= 0.3, (
            f"Cached route {route.path} took {elapsed:.3f}s, exceeds 300ms limit"
        )


@pytest.mark.asyncio
async def test_all_routes_loaded_individually_within_2s():
    manager = RouteManager()
    manager.add_route(LazyRoute("/slow", "SlowPage", 1.9))
    manager.add_route(LazyRoute("/fast", "FastPage", 0.1))
    durations = []
    for route in manager.routes:
        elapsed = await manager.navigate_to(route.path)
        durations.append(elapsed)
    assert durations[0] <= 2.0
    assert durations[1] <= 2.0


@pytest.mark.asyncio
async def test_concurrent_first_load_respects_limit():
    manager = RouteManager()
    manager.add_route(LazyRoute("/a", "PageA", 1.5))
    manager.add_route(LazyRoute("/b", "PageB", 1.6))
    manager.add_route(LazyRoute("/c", "PageC", 0.2))

    async def load_route(path: str) -> float:
        return await manager.navigate_to(path)

    results = await asyncio.gather(
        load_route("/a"), load_route("/b"), load_route("/c")
    )
    for path, elapsed in zip(["/a", "/b", "/c"], results):
        assert elapsed <= 2.0, (
            f"Concurrent load of {path} took {elapsed:.3f}s, exceeds 2s limit"
        )


@pytest.mark.asyncio
async def test_navigation_to_nonexistent_route_raises_error(route_manager):
    with pytest.raises(ValueError, match="Route not found: /nonexistent"):
        await route_manager.navigate_to("/nonexistent")


@pytest.mark.asyncio
async def test_route_not_loaded_before_first_navigation(route_manager):
    for route in route_manager.routes:
        assert not route.is_loaded, (
            f"Route {route.path} should not be loaded before navigation"
        )


@pytest.mark.asyncio
async def test_route_loaded_after_first_navigation(route_manager):
    for route in route_manager.routes:
        await route_manager.navigate_to(route.path)
        assert route.is_loaded, (
            f"Route {route.path} should be loaded after navigation"
        )


@pytest.mark.asyncio
async def test_active_route_tracking(route_manager):
    assert route_manager.get_active_route() is None
    await route_manager.navigate_to("/home")
    assert route_manager.get_active_route() == "/home"
    await route_manager.navigate_to("/about")
    assert route_manager.get_active_route() == "/about"


@pytest.mark.asyncio
async def test_repeated_switch_stays_under_300ms():
    manager = RouteManager()
    for i in range(5):
        manager.add_route(LazyRoute(f"/page{i}", f"Page{i}", 0.3))
    for route in manager.routes:
        await manager.navigate_to(route.path)
    for _ in range(3):
        for route in manager.routes:
            elapsed = await manager.navigate_to(route.path)
            assert elapsed <= 0.3, (
                f"Repeated switch to {route.path} took {elapsed:.3f}s, "
                f"exceeds 300ms limit"
            )
