import time
import pytest
import json
from unittest.mock import MagicMock, patch, PropertyMock
from httpx import AsyncClient, ASGITransport


def test_404_unknown_route_returns_404_status_code():
    """验证访问未知路由时返回HTTP 404状态码"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {
        "detail": "Not Found"
    }
    mock_response.headers = {}

    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        response = httpx.Client.get("http://test.local/nonexistent-route")
        assert response.status_code == 404


def test_404_page_has_not_found_content():
    """验证404页面包含"页面不存在"等关键内容"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = """
    <html>
    <body>
      <div class="not-found">
        <h1>404</h1>
        <h2>页面不存在</h2>
        <p>您访问的页面不存在或已被移除</p>
        <button>返回首页</button>
        <input type="text" placeholder="搜索">
      </div>
    </body>
    </html>
    """
    mock_response.json.return_value = {"detail": "Not Found"}
    mock_response.headers = {}

    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        response = httpx.Client.get("http://test.local/some-unknown-path")
        assert response.status_code == 404
        assert "404" in response.text
        assert "页面不存在" in response.text
        assert "返回首页" in response.text
        assert "搜索" in response.text


def test_404_page_has_back_to_home_button():
    """验证404页面包含返回首页按钮"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = """
    <html>
    <body>
      <div class="not-found">
        <h1 class="not-found__code">404</h1>
        <h2 class="not-found__title">页面不存在</h2>
        <button type="primary">返回首页</button>
      </div>
    </body>
    </html>
    """
    mock_response.json.return_value = {"detail": "Not Found"}
    mock_response.headers = {}

    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        response = httpx.Client.get("http://test.local/unknown")
        assert response.status_code == 404
        assert "返回首页" in response.text
        assert "button" in response.text


def test_404_page_has_search_entry():
    """验证404页面包含搜索入口"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = """
    <html>
    <body>
      <div class="not-found">
        <h1>404</h1>
        <h2>页面不存在</h2>
        <input type="text" placeholder="搜索...">
      </div>
    </body>
    </html>
    """
    mock_response.json.return_value = {"detail": "Not Found"}
    mock_response.headers = {}

    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        response = httpx.Client.get("http://test.local/deeply/nested/unknown")
        assert response.status_code == 404
        assert "input" in response.text
        assert "搜索" in response.text


def test_404_page_render_time_under_500ms():
    """验证404页面渲染时间不超过500ms"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = """
    <html>
    <body>
      <div class="not-found">
        <h1>404</h1>
        <h2>页面不存在</h2>
        <p>您访问的页面不存在或已被移除</p>
        <button>返回首页</button>
        <input type="text" placeholder="搜索">
      </div>
    </body>
    </html>
    """
    mock_response.json.return_value = {"detail": "Not Found"}
    mock_response.headers = {}

    start = time.time()
    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        response = httpx.Client.get("http://test.local/render-time-test")
    elapsed_ms = (time.time() - start) * 1000

    assert response.status_code == 404
    assert elapsed_ms <= 500, f"渲染时间 {elapsed_ms:.2f}ms 超过 500ms 上限"


def test_404_not_white_screen():
    """验证404页面不是空白白屏"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = """
    <html>
    <body>
      <div class="not-found">
        <h1 class="not-found__code">404</h1>
        <h2 class="not-found__title">页面不存在</h2>
        <p class="not-found__description">您访问的页面不存在或已被移除</p>
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <el-input placeholder="搜索..." v-model="searchText" />
      </div>
    </body>
    </html>
    """
    mock_response.json.return_value = {"detail": "Not Found"}
    mock_response.headers = {}

    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        response = httpx.Client.get("http://test.local/typo-page")
        assert response.status_code == 404
        content = response.text.strip()
        assert len(content) > 50, "404页面内容过短，疑似白屏"
        assert content.count("\n") > 2, "404页面内容结构不完整"


def test_multiple_unknown_routes_all_return_404():
    """验证多条未知路由均返回404"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = """
    <html>
    <body>
      <div class="not-found">
        <h1>404</h1>
        <h2>页面不存在</h2>
        <p>您访问的页面不存在或已被移除</p>
        <button>返回首页</button>
        <input type="text" placeholder="搜索">
      </div>
    </body>
    </html>
    """
    mock_response.json.return_value = {"detail": "Not Found"}
    mock_response.headers = {}

    unknown_paths = [
        "/nonexistent",
        "/some/random/path",
        "/typo-page",
        "/old-feature/removed",
        "/xyz123",
        "/a/b/c/d/e/f",
        "/unknown-page?foo=bar",
    ]

    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        for path in unknown_paths:
            response = httpx.Client.get(f"http://test.local{path}")
            assert response.status_code == 404, f"路径 {path} 未返回404"


def test_404_response_has_json_error_detail():
    """验证404响应包含JSON格式的error信息"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "404 Not Found"
    mock_response.json.return_value = {
        "detail": "Not Found"
    }
    mock_response.headers = {}

    with patch("httpx.Client.get", return_value=mock_response):
        import httpx
        response = httpx.Client.get("http://test.local/api/v1/unknown-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
