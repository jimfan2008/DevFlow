import time
import pytest
from typing import Callable, Dict, Tuple


class LazyRoute:
    """模拟一个懒加载路由：组件仅在首次访问时加载（对应前端的代码分割/懒加载）"""

    def __init__(self, path: str, loader: Callable[[], object], simulate_delay: float = 0.0):
        self.path = path
        self._loader = loader
        self._simulate_delay = simulate_delay
        self._loaded = False
        self._component = None
        self.load_count = 0
        self.last_load_duration = 0.0

    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> object:
        if self._loaded:
            return self._component
        start = time.perf_counter()
        if self._simulate_delay > 0:
            time.sleep(self._simulate_delay)
        component = self._loader()
        self.last_load_duration = time.perf_counter() - start
        self.load_count += 1
        self._loaded = True
        self._component = component
        return component

    def reset(self) -> None:
        self._loaded = False
        self._component = None
        self.load_count = 0
        self.last_load_duration = 0.0


class LazyRouter:
    """支持懒加载的路由表：所有已知路由都懒加载，未知路由渲染404页面"""

    HOME_PATH = "/home"
    LAZY_LOAD_THRESHOLD_SECONDS = 2.0

    def __init__(self):
        self._routes: Dict[str, LazyRoute] = {}
        self._not_found_rendered = False

    def register(self, path: str, loader: Callable[[], object], delay: float = 0.0) -> LazyRoute:
        route = LazyRoute(path, loader, delay)
        self._routes[path] = route
        return route

    def resolve(self, path: str) -> Tuple[int, object]:
        if path in self._routes:
            component = self._routes[path].load()
            return 200, component
        return 404, self._render_404()

    def _render_404(self) -> str:
        self._not_found_rendered = True
        return (
            "<!DOCTYPE html>"
            "<html lang=\"zh-CN\"><head><title>404 - 页面未找到</title></head>"
            "<body>"
            "<h1>404</h1>"
            "<h2>页面不存在</h2>"
            "<p>您访问的页面不存在或已被移除</p>"
            "<a href=\"/home\" id=\"back-home-btn\">返回首页</a>"
            "</body></html>"
        )

    def is_lazy_registered(self, path: str) -> bool:
        return path in self._routes and isinstance(self._routes[path], LazyRoute)


@pytest.fixture
def router() -> LazyRouter:
    r = LazyRouter()
    r.register(r.HOME_PATH, lambda: "<HomePage/>")
    r.register("/about", lambda: "<AboutPage/>")
    r.register("/projects", lambda: "<ProjectsPage/>", delay=0.05)
    r.register("/settings", lambda: "<SettingsPage/>", delay=0.08)
    return r


def test_unknown_route_returns_404(router: LazyRouter):
    status, _ = router.resolve("/this-route-does-not-exist")
    assert status == 404


def test_404_page_contains_back_to_home_button(router: LazyRouter):
    _, body = router.resolve("/unknown-path")
    assert "404" in body
    assert "返回首页" in body
    assert 'href="/home"' in body


def test_404_page_back_home_button_is_clickable(router: LazyRouter):
    _, body = router.resolve("/missing")
    assert "返回首页" in body
    assert "button" in body or 'href="/home"' in body


def test_404_page_is_not_blank(router: LazyRouter):
    _, body = router.resolve("/typo-page")
    assert len(body.strip()) > 50
    assert "<html" in body.lower()


def test_all_routes_support_lazy_loading(router: LazyRouter):
    for path in router._routes:
        assert not router._routes[path].is_loaded(), f"路由 {path} 在首次访问前不应被加载（非懒加载）"
    assert all(router.is_lazy_registered(p) for p in router._routes)


def test_lazy_route_first_load_triggers_loader(router: LazyRouter):
    route = router._routes["/about"]
    assert route.load_count == 0
    status, component = router.resolve("/about")
    assert status == 200
    assert component == "<AboutPage/>"
    assert route.load_count == 1
    assert route.is_loaded()


def test_lazy_route_second_access_uses_cache(router: LazyRouter):
    route = router._routes["/projects"]
    router.resolve("/projects")
    first_count = route.load_count
    router.resolve("/projects")
    router.resolve("/projects")
    assert route.load_count == first_count == 1, "重复访问懒加载路由不应重复加载"


def test_lazy_route_first_load_within_2_seconds(router: LazyRouter):
    start = time.perf_counter()
    router.resolve("/settings")
    elapsed = time.perf_counter() - start
    assert elapsed <= LazyRouter.LAZY_LOAD_THRESHOLD_SECONDS, (
        f"懒加载路由首次加载耗时 {elapsed:.3f}s 超过 {LazyRouter.LAZY_LOAD_THRESHOLD_SECONDS}s 上限"
    )
    assert router._routes["/settings"].last_load_duration <= LazyRouter.LAZY_LOAD_THRESHOLD_SECONDS


def test_known_route_returns_200(router: LazyRouter):
    status, _ = router.resolve(router.HOME_PATH)
    assert status == 200


def test_multiple_unknown_routes_all_return_404(router: LazyRouter):
    unknown_paths = [
        "/nonexistent",
        "/some/random/path",
        "/typo-page",
        "/old-feature/removed",
        "/a/b/c/d/e",
        "/unknown?foo=bar",
    ]
    for path in unknown_paths:
        status, _ = router.resolve(path)
        assert status == 404, f"未知路由 {path} 未返回404"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
