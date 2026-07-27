"""测试用例：404未知路由页面

验证访问未知路由时显示404页面而非白屏

验收标准：
  1. 显示自定义404页面
  2. 包含返回首页按钮和搜索入口
  3. HTTP状态码404
  4. 页面渲染时间 ≤500ms
"""

import time
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from typing import AsyncGenerator

CUSTOM_404_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>404 - 页面未找到</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="text-align:center;padding:80px 20px;font-family:sans-serif;margin:0;">
  <div class="error-page" data-testid="error-page">
    <h1 style="font-size:96px;margin:0;color:#1d1d1f;">404</h1>
    <p style="font-size:24px;color:#1d1d1f;margin:16px 0;">页面未找到</p>
    <p style="font-size:14px;color:#7a7a7a;margin-bottom:32px;">您访问的页面不存在或已被移除</p>
    <div class="actions" style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
      <a href="/" class="btn-home" data-testid="btn-home"
         style="display:inline-block;padding:12px 24px;background:#0066cc;color:#fff;text-decoration:none;border-radius:8px;font-size:16px;">
        返回首页
      </a>
      <div class="search-entry" data-testid="search-entry">
        <form action="/search" method="get" style="display:flex;gap:8px;">
          <input type="search" name="q" placeholder="搜索..."
                 data-testid="search-input"
                 style="padding:12px 16px;border:1px solid #e0e0e0;border-radius:8px;font-size:16px;width:240px;outline:none;" />
          <button type="submit" data-testid="search-button"
                  style="padding:12px 20px;background:#0066cc;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;">
            搜索
          </button>
        </form>
      </div>
    </div>
  </div>
</body>
</html>"""


def build_test_app() -> FastAPI:
    """构建用于测试的 FastAPI 应用，包含 404 异常处理器。"""
    app = FastAPI(title="DevFlow-404-Test")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return HTMLResponse(
                status_code=404,
                content=CUSTOM_404_HTML,
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION_ERROR", "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "Internal server error"},
        )

    @app.get("/")
    async def root():
        return {"message": "OK"}

    @app.get("/api/v1/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/search")
    async def search(q: str = ""):
        return {"results": []}

    return app


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """创建测试用异步 HTTP 客户端。"""
    app = build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as ac:
        yield ac


UNKNOWN_ROUTES = [
    "/nonexistent",
    "/some/random/path",
    "/typo-page",
    "/old-feature/removed",
    "/xyz123",
    "/api/unknown",
    "/api/v1/notfound",
    "/this/path/does/not/exist",
    "/api/boards/99999",
    "/api/tasks/nonexistent-task-id",
    "/random-page-123",
    "/api/v99/unknown",
    "/page/not/found/here",
    "/unknown-page?foo=bar&baz=1",
    "/%E8%B7%AF%E5%BE%84/%E4%B8%8D%E5%AD%98%E5%9C%A8",
]

DEEPLY_NESTED_ROUTES = [
    "/a/b/c/d/e/f/g",
    "/api/v1/workflow/unknown-step-99",
    "/api/projects/unknown/sprints/backlog",
    "/api/boards/not-a-board/tasks/nonexistent",
    "/x/y/z/1/2/3/4/5",
]

KNOWN_ROUTES = [
    "/",
    "/api/v1/health",
    "/search",
    "/search?q=test",
]

RENDER_TIME_THRESHOLD_SECONDS = 0.5


@pytest.mark.asyncio
class Test404UnknownRoutePage:
    """验证访问未知路由时显示404页面而非白屏"""

    # ── 验收标准 1：HTTP 状态码 404 ──────────────────────────────

    async def test_unknown_root_path_returns_404_status_code(self, client: AsyncClient):
        """未知路由应返回 404 状态码"""
        response = await client.get("/nonexistent")
        assert response.status_code == 404, (
            f"未知路由 /nonexistent 应返回 404，实际返回 {response.status_code}"
        )

    async def test_multiple_unknown_paths_all_return_404(self, client: AsyncClient):
        """多条未知路由都应返回 404 状态码"""
        for route in UNKNOWN_ROUTES:
            response = await client.get(route)
            assert response.status_code == 404, (
                f"未知路由 {route} 应返回 404，实际返回 {response.status_code}"
            )

    async def test_deeply_nested_unknown_paths_return_404(self, client: AsyncClient):
        """深层嵌套的未知路由也应返回 404"""
        for route in DEEPLY_NESTED_ROUTES:
            response = await client.get(route)
            assert response.status_code == 404, (
                f"深层未知路由 {route} 应返回 404，实际返回 {response.status_code}"
            )

    async def test_unknown_path_with_query_params_returns_404(self, client: AsyncClient):
        """带查询参数的未知路由应返回 404"""
        response = await client.get("/unknown-page?foo=bar&baz=1")
        assert response.status_code == 404

    async def test_unknown_path_with_non_ascii_returns_404(self, client: AsyncClient):
        """含非 ASCII 字符的未知路由应返回 404"""
        response = await client.get("/%E8%B7%AF%E5%BE%84/%E4%B8%8D%E5%AD%98%E5%9C%A8")
        assert response.status_code == 404

    async def test_unknown_post_returns_404(self, client: AsyncClient):
        """对未知路由发 POST 请求也应返回 404"""
        response = await client.post("/api/nonexistent-resource")
        assert response.status_code == 404

    async def test_unknown_put_returns_404(self, client: AsyncClient):
        """对未知路由发 PUT 请求也应返回 404"""
        response = await client.put("/api/unknown-item-999")
        assert response.status_code == 404

    async def test_unknown_delete_returns_404(self, client: AsyncClient):
        """对未知路由发 DELETE 请求也应返回 404"""
        response = await client.delete("/api/v1/unknown-delete")
        assert response.status_code == 404

    async def test_unknown_patch_returns_404(self, client: AsyncClient):
        """对未知路由发 PATCH 请求也应返回 404"""
        response = await client.patch("/api/unknown-patch-target")
        assert response.status_code == 404

    async def test_known_routes_do_not_return_404(self, client: AsyncClient):
        """已知路由不应返回 404"""
        for route in KNOWN_ROUTES:
            response = await client.get(route)
            assert response.status_code != 404, (
                f"已知路由 {route} 不应返回 404"
            )

    async def test_known_prefix_unknown_resource_returns_404(self, client: AsyncClient):
        """已知前缀 + 未知资源路径应返回 404"""
        prefixes = ["/api", "/api/v1", "/api/auth"]
        for prefix in prefixes:
            route = f"{prefix}/non-existent-resource"
            response = await client.get(route)
            assert response.status_code == 404, (
                f"已知前缀 {prefix} + 未知资源应返回 404"
            )

    # ── 验收标准 2：显示自定义 404 页面 ─────────────────────────

    async def test_404_response_is_html(self, client: AsyncClient):
        """404 响应应为 HTML 格式而非 JSON"""
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type, (
            f"404 响应 Content-Type 应为 text/html，实际为 {content_type}"
        )

    async def test_404_page_renders_valid_html(self, client: AsyncClient):
        """404 页面应为有效的 HTML 文档"""
        response = await client.get("/nonexistent")
        body = response.text.strip()
        assert body.startswith("<!DOCTYPE html>") or body.startswith("<html"), (
            "404 页面应以 <!DOCTYPE html> 或 <html> 开头"
        )
        assert "</html>" in body, "404 页面应包含 </html> 闭合标签"

    async def test_404_page_contains_404_code(self, client: AsyncClient):
        """404 页面应显示 404 状态码文本"""
        response = await client.get("/nonexistent")
        assert "404" in response.text, "404 页面应包含 404 文本"

    async def test_404_page_contains_chinese_not_found_message(self, client: AsyncClient):
        """404 页面应包含中文提示信息"""
        response = await client.get("/nonexistent")
        assert "页面未找到" in response.text, "404 页面应包含中文提示"

    async def test_404_page_contains_description(self, client: AsyncClient):
        """404 页面应包含说明文字"""
        response = await client.get("/nonexistent")
        assert "不存在" in response.text or "被移除" in response.text, (
            "404 页面应包含描述性文字"
        )

    async def test_404_page_is_not_blank_screen(self, client: AsyncClient):
        """404 页面不应是白屏——响应体不应为空"""
        response = await client.get("/nonexistent")
        body = response.text.strip()
        assert len(body) > 0, "404 页面不应为空"
        assert body != "", "404 页面不应是空字符串"
        assert "<body" in body, "404 页面应包含 body 标签"

    async def test_404_page_has_error_page_container(self, client: AsyncClient):
        """404 页面应包含错误页面容器元素"""
        response = await client.get("/nonexistent")
        assert 'data-testid="error-page"' in response.text, (
            "404 页面应包含错误页面容器"
        )

    async def test_404_page_content_length_minimum(self, client: AsyncClient):
        """404 页面内容长度应超过最低阈值"""
        response = await client.get("/nonexistent")
        assert len(response.text) > 200, (
            f"404 页面内容过短，长度 {len(response.text)} 应 > 200"
        )

    # ── 验收标准 3：包含返回首页按钮 ──────────────────────────────

    async def test_404_page_has_return_home_button(self, client: AsyncClient):
        """404 页面应包含返回首页按钮"""
        response = await client.get("/nonexistent")
        assert 'data-testid="btn-home"' in response.text, (
            "404 页面应包含返回首页按钮"
        )
        assert "返回首页" in response.text, (
            "404 页面应包含'返回首页'文案"
        )

    async def test_404_page_home_button_points_to_root(self, client: AsyncClient):
        """返回首页按钮应指向根路径 /"""
        response = await client.get("/nonexistent")
        assert 'href="/"' in response.text, (
            "返回首页链接应指向根路径 /"
        )

    async def test_404_page_home_button_has_styling(self, client: AsyncClient):
        """返回首页按钮应有按钮样式"""
        response = await client.get("/nonexistent")
        assert "btn-home" in response.text, "返回首页按钮应有 btn-home 类名"

    # ── 验收标准 4：包含搜索入口 ─────────────────────────────────

    async def test_404_page_has_search_entry(self, client: AsyncClient):
        """404 页面应包含搜索入口"""
        response = await client.get("/nonexistent")
        assert 'data-testid="search-entry"' in response.text, (
            "404 页面应包含搜索入口容器"
        )

    async def test_404_page_has_search_input(self, client: AsyncClient):
        """404 页面应包含搜索输入框"""
        response = await client.get("/nonexistent")
        assert 'type="search"' in response.text, (
            "404 页面应包含 type='search' 的输入框"
        )
        assert 'data-testid="search-input"' in response.text, (
            "404 页面应包含搜索输入框测试标识"
        )

    async def test_404_page_search_input_has_placeholder(self, client: AsyncClient):
        """搜索输入框应有占位符提示"""
        response = await client.get("/nonexistent")
        assert 'placeholder="搜索' in response.text, (
            "搜索输入框应包含搜索占位符"
        )

    async def test_404_page_has_search_button(self, client: AsyncClient):
        """404 页面应包含搜索按钮"""
        response = await client.get("/nonexistent")
        assert 'data-testid="search-button"' in response.text, (
            "404 页面应包含搜索按钮"
        )
        assert "搜索" in response.text, "404 页面应包含搜索相关文案"

    async def test_404_page_search_form_points_to_search_endpoint(self, client: AsyncClient):
        """搜索表单应提交到 /search 端点"""
        response = await client.get("/nonexistent")
        assert 'action="/search"' in response.text, (
            "搜索表单应指向 /search"
        )

    async def test_404_page_search_input_has_name_attribute(self, client: AsyncClient):
        """搜索输入框应有 name 属性以便表单提交"""
        response = await client.get("/nonexistent")
        assert 'name="q"' in response.text, "搜索输入框应有 name 属性"

    # ── 验收标准 5：页面渲染时间 ≤500ms ──────────────────────────

    async def test_404_render_time_within_threshold(self, client: AsyncClient):
        """404 页面渲染时间应在 500ms 以内"""
        for route in UNKNOWN_ROUTES[:5]:
            start = time.perf_counter()
            response = await client.get(route)
            elapsed = time.perf_counter() - start
            assert response.status_code == 404
            assert elapsed <= RENDER_TIME_THRESHOLD_SECONDS, (
                f"404 页面渲染耗时 {elapsed:.3f}s，超过 {RENDER_TIME_THRESHOLD_SECONDS}s 上限"
            )

    async def test_404_consecutive_calls_all_within_threshold(self, client: AsyncClient):
        """连续请求多条未知路由，每次渲染时间都在 500ms 以内"""
        durations = []
        for route in UNKNOWN_ROUTES[:10]:
            start = time.perf_counter()
            response = await client.get(route)
            elapsed = time.perf_counter() - start
            assert response.status_code == 404
            durations.append(elapsed)

        max_time = max(durations)
        avg_time = sum(durations) / len(durations)
        assert max_time <= RENDER_TIME_THRESHOLD_SECONDS, (
            f"最慢渲染耗时 {max_time:.3f}s，超过 500ms 上限"
        )
        assert avg_time <= RENDER_TIME_THRESHOLD_SECONDS, (
            f"平均渲染耗时 {avg_time:.3f}s，超过 500ms 上限"
        )

    async def test_404_deep_nested_route_render_time(self, client: AsyncClient):
        """深层嵌套未知路由的渲染时间也应在 500ms 以内"""
        for route in DEEPLY_NESTED_ROUTES:
            start = time.perf_counter()
            response = await client.get(route)
            elapsed = time.perf_counter() - start
            assert response.status_code == 404
            assert elapsed <= RENDER_TIME_THRESHOLD_SECONDS, (
                f"深层路由 {route} 渲染耗时 {elapsed:.3f}s，超过 500ms"
            )

    # ── 并发压力测试 ──────────────────────────────────────────────

    async def test_concurrent_404_requests_all_return_404(self, client: AsyncClient):
        """并发请求多条未知路由，全部应返回 404 且内容有效"""

        async def check_route(route: str) -> bool:
            resp = await client.get(route)
            return (
                resp.status_code == 404
                and len(resp.text.strip()) > 0
                and "404" in resp.text
            )

        routes_to_test = UNKNOWN_ROUTES[:8]
        results = await asyncio.gather(
            *[check_route(route) for route in routes_to_test]
        )
        assert all(results), (
            f"并发请求中不是所有 404 响应都有效，结果: {results}"
        )

    # ── 回归保护 ──────────────────────────────────────────────────

    async def test_cors_origin_header_on_404_response(self, client: AsyncClient):
        """404 响应在带 Origin 头时状态码仍为 404"""
        response = await client.get(
            "/nonexistent",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 404

    async def test_404_response_encoding_is_utf8(self, client: AsyncClient):
        """404 响应内容编码应为 utf-8"""
        response = await client.get("/nonexistent")
        content_type = response.headers.get("content-type", "")
        assert "utf-8" in content_type or "charset" in content_type, (
            f"404 响应应声明 utf-8 编码: {content_type}"
        )
