import pytest
from httpx import AsyncClient, ASGITransport
from time import perf_counter


class Mock404App:
    """模拟 FastAPI/Starlette 应用，包含 404 处理"""

    def __init__(self):
        self.routes = [("/home", self._home_handler)]

    async def __call__(self, scope):
        if scope["type"] != "http":
            return

        path = scope["path"]
        matched = False
        for route_path, handler in self.routes:
            if path == route_path:
                matched = True
                break

        if not matched:
            await self._not_found_handler(scope)
        else:
            for route_path, handler in self.routes:
                if path == route_path:
                    await handler(scope)
                    return

    async def _home_handler(self, scope):
        scope["response"] = {
            "status": 200,
            "body": b"<html><body>Home Page</body></html>",
            "headers": [(b"content-type", b"text/html; charset=utf-8")],
        }

    async def _not_found_handler(self, scope):
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head><title>404 - 页面未找到</title></head>
<body>
  <h1>404 - 页面未找到</h1>
  <p>您访问的页面不存在</p>
  <a href="/home" id="back-home-btn">返回首页</a>
  <form action="/search" id="search-form">
    <input type="text" name="q" placeholder="搜索..." />
    <button type="submit">搜索</button>
  </form>
</body>
</html>"""
        scope["response"] = {
            "status": 404,
            "body": html.encode("utf-8"),
            "headers": [(b"content-type", b"text/html; charset=utf-8")],
        }


@pytest.fixture
def app():
    return Mock404App()


class MockRequest:
    def __init__(self, path, app):
        self.path = path
        self.app = app
        self.scope = {"type": "http", "path": path}
        self.status_code = None
        self.body = None
        self.headers = None

    async def send(self):
        import asyncio
        await self.app(self.scope)
        resp = self.scope.get("response", {})
        self.status_code = resp.get("status", 200)
        self.body = resp.get("body", b"")
        self.headers = resp.get("headers", [])

    def text(self):
        return self.body.decode("utf-8")


@pytest.fixture
def request_factory(app):
    def _factory(path):
        return MockRequest(path, app)
    return _factory


def test_404_status_code(request_factory):
    req = request_factory("/unknown-route")
    import asyncio
    asyncio.run(req.send())
    assert req.status_code == 404


def test_404_page_contains_custom_content(request_factory):
    req = request_factory("/nonexistent-page")
    import asyncio
    asyncio.run(req.send())
    html = req.text()
    assert "404" in html
    assert "页面未找到" in html or "Not Found" in html


def test_404_page_has_back_home_button(request_factory):
    req = request_factory("/does-not-exist")
    import asyncio
    asyncio.run(req.send())
    html = req.text()
    assert 'href="/home"' in html
    assert "返回首页" in html


def test_404_page_has_search_input(request_factory):
    req = request_factory("/missing")
    import asyncio
    asyncio.run(req.send())
    html = req.text()
    assert 'id="search-form"' in html or "搜索" in html
    assert "search" in html.lower() or "搜索" in html


def test_404_rendering_time_under_500ms(request_factory):
    req = request_factory("/slow-render-test")
    start = perf_counter()
    import asyncio
    asyncio.run(req.send())
    elapsed_ms = (perf_counter() - start) * 1000
    assert elapsed_ms <= 500, f"渲染耗时 {elapsed_ms:.2f}ms 超过 500ms"


def test_known_route_returns_200(request_factory):
    req = request_factory("/home")
    import asyncio
    asyncio.run(req.send())
    assert req.status_code == 200


def test_404_content_type_is_html(request_factory):
    req = request_factory("/any-unknown-path")
    import asyncio
    asyncio.run(req.send())
    header_dict = {k.decode(): v.decode() for k, v in req.headers}
    assert "text/html" in header_dict.get("content-type", "")
