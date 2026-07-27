import pytest
import time
import asyncio


class RouteDefinition:
    def __init__(self, name, path, component_loader, is_lazy=True):
        self.name = name
        self.path = path
        self.component_loader = component_loader
        self.is_lazy = is_lazy
        self.load_time = 0.0
        self.component = None

    async def load_component(self):
        start = time.monotonic()
        if self.is_lazy:
            self.component = await self.component_loader()
        else:
            self.component = self.component_loader()
        self.load_time = time.monotonic() - start
        return self.component


class RouterRegistry:
    def __init__(self):
        self._routes = {}

    def register(self, route):
        self._routes[route.name] = route

    def get(self, name):
        return self._routes.get(name)

    def all_routes(self):
        return list(self._routes.values())

    def lazy_routes(self):
        return [r for r in self._routes.values() if r.is_lazy]

    def eager_routes(self):
        return [r for r in self._routes.values() if not r.is_lazy]


def make_async_loader(load_duration=0.05, component_data=None):
    if component_data is None:
        component_data = {"template": "<div>mock</div>", "data": lambda: {}}
    async def loader():
        if load_duration > 0:
            await asyncio.sleep(load_duration)
        return component_data
    return loader


def make_sync_loader(component_data=None):
    if component_data is None:
        component_data = {"template": "<div>mock</div>", "data": lambda: {}}
    def loader():
        return component_data
    return loader


ROUTE_DEFINITIONS = [
    ("Login", "/login", True),
    ("Register", "/register", True),
    ("ProjectList", "/projects", True),
    ("ProjectDetail", "/projects/:id", True),
    ("AgentList", "/agents", True),
    ("AgentDetail", "/agents/:id", True),
    ("SkillManagement", "/skills", True),
    ("Chat", "/chat", True),
    ("BoardList", "/boards", True),
    ("BoardDetail", "/boards/:boardId", True),
    ("TaskDetail", "/boards/:boardId/tasks/:taskId", True),
    ("TaskBoard", "/task-board", True),
    ("Repos", "/repos", True),
    ("Acceptance", "/acceptance", True),
    ("NotificationCenter", "/notifications", True),
    ("Delivery", "/delivery", True),
    ("Requirements", "/requirements", True),
    ("Profile", "/profile", True),
    ("NotFound", "/:pathMatch(.*)", True),
]


@pytest.fixture
def router_registry():
    registry = RouterRegistry()
    for name, path, is_lazy in ROUTE_DEFINITIONS:
        loader = make_async_loader(load_duration=0.05) if is_lazy else make_sync_loader()
        route = RouteDefinition(name, path, loader, is_lazy=is_lazy)
        registry.register(route)
    return registry


class TestLazyLoadingStructure:

    def test_all_routes_are_lazy_loaded(self, router_registry):
        eager = router_registry.eager_routes()
        assert len(eager) == 0, f"Found non-lazy routes: {[r.name for r in eager]}"

    def test_eager_route_detected_correctly(self):
        registry = RouterRegistry()
        lazy_route = RouteDefinition("Lazy", "/lazy", make_async_loader(), is_lazy=True)
        eager_route = RouteDefinition("Eager", "/eager", make_sync_loader(), is_lazy=False)
        registry.register(lazy_route)
        registry.register(eager_route)
        assert len(registry.lazy_routes()) == 1
        assert len(registry.eager_routes()) == 1
        assert registry.get("Eager").is_lazy is False

    def test_route_registry_lookup(self, router_registry):
        route = router_registry.get("Login")
        assert route is not None
        assert route.name == "Login"
        assert route.path == "/login"
        assert route.is_lazy is True

    def test_route_count_matches_all_definitions(self, router_registry):
        assert len(router_registry.all_routes()) == len(ROUTE_DEFINITIONS)

    def test_all_routes_have_unique_names(self, router_registry):
        names = [r.name for r in router_registry.all_routes()]
        assert len(names) == len(set(names))

    def test_all_routes_have_unique_paths(self, router_registry):
        paths = [r.path for r in router_registry.all_routes()]
        assert len(paths) == len(set(paths))


class TestLazyLoadingPerformance:

    LAZY_LOAD_LIMIT = 2.0
    SWITCH_LIMIT = 0.3

    @pytest.mark.asyncio
    async def test_lazy_route_first_load_within_2_seconds(self, router_registry):
        route = router_registry.get("ProjectList")
        component = await route.load_component()
        assert component is not None
        assert route.load_time <= self.LAZY_LOAD_LIMIT, (
            f"First load of {route.name} took {route.load_time:.3f}s, "
            f"exceeds limit of {self.LAZY_LOAD_LIMIT}s"
        )

    @pytest.mark.asyncio
    async def test_all_lazy_routes_first_load_within_2_seconds(self, router_registry):
        for route in router_registry.lazy_routes():
            component = await route.load_component()
            assert component is not None
            assert route.load_time <= self.LAZY_LOAD_LIMIT, (
                f"First load of {route.name} took {route.load_time:.3f}s, "
                f"exceeds limit of {self.LAZY_LOAD_LIMIT}s"
            )

    @pytest.mark.asyncio
    async def test_route_switch_time_within_300ms(self, router_registry):
        route_a = router_registry.get("ProjectList")
        route_b = router_registry.get("AgentList")
        await route_a.load_component()
        start = time.monotonic()
        await route_b.load_component()
        switch_time = time.monotonic() - start
        assert switch_time <= self.SWITCH_LIMIT, (
            f"Switch from {route_a.name} to {route_b.name} took {switch_time:.3f}s, "
            f"exceeds limit of {self.SWITCH_LIMIT}s"
        )

    @pytest.mark.asyncio
    async def test_consecutive_route_switches_within_limit(self, router_registry):
        routes = router_registry.lazy_routes()
        for i in range(len(routes) - 1):
            await routes[i].load_component()
            start = time.monotonic()
            await routes[i + 1].load_component()
            switch_time = time.monotonic() - start
            assert switch_time <= self.SWITCH_LIMIT, (
                f"Switch from {routes[i].name} to {routes[i+1].name} "
                f"took {switch_time:.3f}s"
            )

    @pytest.mark.asyncio
    async def test_slow_route_detected_as_exceeding_limit(self):
        slow_loader = make_async_loader(load_duration=2.5)
        route = RouteDefinition("SlowPage", "/slow", slow_loader, is_lazy=True)
        await route.load_component()
        assert route.load_time > self.LAZY_LOAD_LIMIT, (
            f"Expected slow route to exceed {self.LAZY_LOAD_LIMIT}s limit"
        )


class TestLazyLoadingParallel:

    @pytest.mark.asyncio
    async def test_parallel_load_of_multiple_routes(self, router_registry):
        routes = router_registry.lazy_routes()[:5]
        start = time.monotonic()
        results = await asyncio.gather(*[r.load_component() for r in routes])
        total_time = time.monotonic() - start
        assert all(r is not None for r in results)
        assert all(routes[i].load_time <= 2.0 for i in range(5))
        assert total_time <= 2.0

    @pytest.mark.asyncio
    async def test_parallel_load_all_routes(self, router_registry):
        routes = router_registry.lazy_routes()
        start = time.monotonic()
        results = await asyncio.gather(*[r.load_component() for r in routes])
        total_time = time.monotonic() - start
        assert all(r is not None for r in results)
        assert total_time <= 2.0, (
            f"Parallel load of all {len(routes)} routes "
            f"took {total_time:.3f}s"
        )


class TestLazyLoadingEdgeCases:

    @pytest.mark.asyncio
    async def test_component_with_minimal_load_time(self):
        async def instant_loader():
            return {"template": "<div>instant</div>"}
        route = RouteDefinition("Instant", "/instant", instant_loader, is_lazy=True)
        component = await route.load_component()
        assert component is not None
        assert component["template"] == "<div>instant</div>"
        assert route.load_time < 0.1

    @pytest.mark.asyncio
    async def test_component_data_integrity(self, router_registry):
        expected = {"template": "<div>mock</div>", "data": {}}
        loader = make_async_loader(load_duration=0.01, component_data=expected)
        route = RouteDefinition("DataTest", "/data-test", loader, is_lazy=True)
        component = await route.load_component()
        assert component == expected
        assert component["template"] == expected["template"]

    def test_route_not_found_returns_none(self, router_registry):
        assert router_registry.get("NonExistent") is None

    def test_router_registry_empty_by_default(self):
        registry = RouterRegistry()
        assert len(registry.all_routes()) == 0
        assert len(registry.lazy_routes()) == 0
        assert len(registry.eager_routes()) == 0

    def test_register_same_name_overwrites(self):
        registry = RouterRegistry()
        route1 = RouteDefinition("Same", "/v1", make_async_loader(), is_lazy=True)
        route2 = RouteDefinition("Same", "/v2", make_async_loader(), is_lazy=True)
        registry.register(route1)
        registry.register(route2)
        assert registry.get("Same").path == "/v2"
        assert len(registry.all_routes()) == 1
