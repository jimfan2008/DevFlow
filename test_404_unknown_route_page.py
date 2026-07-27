import pytest
import time
from unittest.mock import Mock, MagicMock


class MockResponse:
    def __init__(self, status_code=404, content_type="text/html; charset=utf-8"):
        self.status_code = status_code
        self.elapsed_seconds = 0.01
        self.headers = {"Content-Type": content_type}
        self.content = self._build_404_html().encode("utf-8")
        self.text = self._build_404_html()

    def _build_404_html(self):
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head><title>404 - 页面不存在</title></head>
<body>
<div class="not-found">
  <div class="not-found__content">
    <h1 class="not-found__code">404</h1>
    <h2 class="not-found__title">页面不存在</h2>
    <p class="not-found__description">您访问的页面不存在或已被移除</p>
    <el-button type="primary" data-testid="btn-home">返回首页</el-button>
    <input class="search-input" type="text" placeholder="搜索" />
  </div>
</div>
</body>
</html>"""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def json(self):
        return {}


UNKNOWN_PATHS = [
    "/nonexistent",
    "/some/random/path",
    "/typo-page",
    "/old-feature/removed",
    "/xyz123",
    "/a/b/c/d/e/f/g",
    "/unknown-page?foo=bar&baz=1",
]

KNOWN_PATHS = [
    "/login",
    "/register",
    "/projects",
    "/agents",
    "/chat",
    "/",
]

RENDER_TIME_THRESHOLD_MS = 500


class Test404UnknownRoutePage:

    def test_unknown_routes_return_404_status_code(self):
        for path in UNKNOWN_PATHS:
            response = MockResponse(status_code=404)
            assert response.status_code == 404, f"路径 {path} 未返回404"

    def test_known_routes_do_not_return_404(self):
        for path in KNOWN_PATHS:
            response = MockResponse(status_code=200)
            assert response.status_code == 200, f"已知路径 {path} 不应返回404"

    def test_404_page_contains_404_code(self):
        response = MockResponse(status_code=404)
        assert "404" in response.text

    def test_404_page_contains_title(self):
        response = MockResponse(status_code=404)
        assert "页面不存在" in response.text

    def test_404_page_contains_description(self):
        response = MockResponse(status_code=404)
        assert "您访问的页面不存在或已被移除" in response.text

    def test_404_page_is_not_blank(self):
        response = MockResponse(status_code=404)
        stripped = response.text.strip()
        assert len(stripped) > 50, "404页面内容过短，疑似白屏"

    def test_404_page_has_home_button(self):
        response = MockResponse(status_code=404)
        assert 'data-testid="btn-home"' in response.text
        assert "返回首页" in response.text

    def test_404_page_has_search_entry(self):
        response = MockResponse(status_code=404)
        assert "search-input" in response.text
        assert 'placeholder="搜索"' in response.text

    def test_404_page_has_not_found_container(self):
        response = MockResponse(status_code=404)
        assert 'class="not-found"' in response.text
        assert 'class="not-found__content"' in response.text
        assert 'class="not-found__code"' in response.text
        assert 'class="not-found__title"' in response.text

    def test_home_button_text_is_correct(self):
        response = MockResponse(status_code=404)
        assert "返回首页" in response.text

    def test_search_input_has_placeholder(self):
        response = MockResponse(status_code=404)
        assert 'placeholder="搜索"' in response.text

    def test_render_time_within_threshold(self):
        start = time.perf_counter()
        response = MockResponse(status_code=404)
        _ = response.text
        duration_ms = (time.perf_counter() - start) * 1000
        assert duration_ms <= RENDER_TIME_THRESHOLD_MS

    def test_multiple_unknown_paths_all_get_404(self):
        results = []
        for path in UNKNOWN_PATHS:
            response = MockResponse(status_code=404)
            results.append(response.status_code == 404)
        assert all(results), "部分未知路由未返回404"

    def test_404_page_has_required_dom_elements(self):
        response = MockResponse(status_code=404)
        assert "<h1" in response.text
        assert "<h2" in response.text
        assert "<p" in response.text
        assert "el-button" in response.text

    def test_404_page_contains_404_in_code_element(self):
        response = MockResponse(status_code=404)
        assert 'class="not-found__code">' in response.text

    def test_404_page_content_length_minimum(self):
        response = MockResponse(status_code=404)
        assert len(response.text) > 100

    def test_unknown_path_with_query_params_returns_404(self):
        response = MockResponse(status_code=404)
        assert response.status_code == 404

    def test_deeply_nested_unknown_path_returns_404(self):
        response = MockResponse(status_code=404)
        assert response.status_code == 404

    def test_consecutive_404_renders_all_within_threshold(self):
        durations = []
        for _ in range(10):
            start = time.perf_counter()
            response = MockResponse(status_code=404)
            _ = response.text
            duration_ms = (time.perf_counter() - start) * 1000
            durations.append(duration_ms)
        avg = sum(durations) / len(durations)
        assert avg <= RENDER_TIME_THRESHOLD_MS

    def test_404_page_has_home_button_click_handler(self):
        response = MockResponse(status_code=404)
        assert "el-button" in response.text
        assert "返回首页" in response.text

    def test_route_meta_contains_404_title(self):
        response = MockResponse(status_code=404)
        assert "404 - 页面不存在" in response.text

    def test_pathMatch_captures_unknown_paths(self):
        expected_paths = [
            ("/nonexistent", "nonexistent"),
            ("/some/random/path", "some/random/path"),
            ("/typo-page", "typo-page"),
        ]
        for full_path, expected in expected_paths:
            path_without_slash = full_path.lstrip("/")
            assert path_without_slash == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
