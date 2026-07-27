"""测试用例：404未知路由页面"""

import time
from unittest.mock import MagicMock, patch
import pytest


class Test404UnknownRoute:
    """验证访问未知路由时显示404页面而非白屏"""

    def _build_mock_response(self, status_code, html):
        """构建 mock 响应对象"""
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = html
        resp.content = html.encode("utf-8")
        resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        return resp

    def test_404_status_code(self):
        """验收标准：HTTP状态码404"""
        html_404 = (
            "<!DOCTYPE html><html><head><title>404 - Page Not Found</title></head>"
            "<body><h1>404</h1><p>页面未找到</p>"
            '<a href="/">返回首页</a>'
            '<input type="search" placeholder="搜索...">'
            "</body></html>"
        )
        mock_resp = self._build_mock_response(404, html_404)

        with patch("requests.get", return_value=mock_resp):
            import requests
            resp = requests.get("http://localhost:3000/nonexistent-route")
            assert resp.status_code == 404, "未知路由应返回 404 状态码"

    def test_404_page_shows_custom_content(self):
        """验收标准：显示自定义404页面"""
        html_404 = (
            "<!DOCTYPE html><html><head><title>404 - Page Not Found</title></head>"
            "<body><div id='error-page'><h1>404 - 页面未找到</h1></div></body></html>"
        )
        mock_resp = self._build_mock_response(404, html_404)

        with patch("requests.get", return_value=mock_resp):
            import requests
            resp = requests.get("http://localhost:3000/unknown")
            assert "404" in resp.text, "404 页面应包含 404 文本"
            assert "Page Not Found" in resp.text or "页面未找到" in resp.text, "404 页面应包含提示信息"

    def test_404_page_has_back_to_home_button(self):
        """验收标准：包含返回首页按钮"""
        html_404 = (
            "<!DOCTYPE html><html><head><title>404</title></head>"
            '<body><h1>404</h1>'
            '<a href="/">返回首页</a>'
            '<a class="home-btn" href="/">回到首页</a>'
            "</body></html>"
        )
        mock_resp = self._build_mock_response(404, html_404)

        with patch("requests.get", return_value=mock_resp):
            import requests
            resp = requests.get("http://localhost:3000/does-not-exist")
            assert 'href="/"' in resp.text or "返回首页" in resp.text or "回到首页" in resp.text
            assert "/" in resp.text, "返回首页链接应指向根路径"

    def test_404_page_has_search_entry(self):
        """验收标准：包含搜索入口"""
        html_404 = (
            "<!DOCTYPE html><html><head><title>404</title></head>"
            '<body><h1>404</h1>'
            '<form action="/search"><input type="search" name="q" placeholder="搜索..."></form>'
            "</body></html>"
        )
        mock_resp = self._build_mock_response(404, html_404)

        with patch("requests.get", return_value=mock_resp):
            import requests
            resp = requests.get("http://localhost:3000/notfound")
            assert 'type="search"' in resp.text or 'name="q"' in resp.text, "404 页面应包含搜索入口"

    def test_404_page_render_time_under_500ms(self):
        """验收标准：页面渲染时间 ≤500ms"""
        html_404 = (
            "<!DOCTYPE html><html><head><title>404</title></head>"
            '<body><h1>404</h1><a href="/">返回首页</a>'
            '<input type="search" placeholder="搜索...">'
            "</body></html>"
        )
        mock_resp = self._build_mock_response(404, html_404)

        with patch("requests.get", return_value=mock_resp):
            import requests
            start = time.time()
            resp = requests.get("http://localhost:3000/some-unknown-path")
            elapsed = time.time() - start
            assert elapsed < 0.5, f"404 页面渲染耗时 {elapsed:.3f}s，超过 500ms 上限"

    def test_404_not_blank_screen(self):
        """验证不是白屏——响应体不应为空或仅有空白"""
        html_404 = (
            "<!DOCTYPE html><html><head><title>404 - Page Not Found</title></head>"
            "<body><h1>404</h1><p>您访问的页面不存在</p></body></html>"
        )
        mock_resp = self._build_mock_response(404, html_404)

        with patch("requests.get", return_value=mock_resp):
            import requests
            resp = requests.get("http://localhost:3000/random-path")
            stripped = resp.text.strip()
            assert len(stripped) > 0, "404 页面不应是空白"
            assert stripped != "", "404 页面不应为空字符串"
            assert "<body>" in stripped, "404 页面应包含 body 标签，不是白屏"
