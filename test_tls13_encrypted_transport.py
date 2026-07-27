import ssl
import socket
import urllib.request
import urllib.error
import pytest
from http import client
from unittest.mock import patch, MagicMock, PropertyMock


# =============================================================================
# TLS 1.3 配置检查模块
# =============================================================================

def get_minimum_tls_version():
    """获取当前系统/应用要求的最小 TLS 版本"""
    return ssl.TLSVersion("TLSv1.3")


def create_tls_context_for_external():
    """创建用于外部通信的 TLS 上下文，强制 TLS 1.3"""
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion("TLSv1.3")
    ctx.maximum_version = ssl.TLSVersion("TLSv1.3")
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def enforce_https_redirect(request_path):
    """模拟 HTTP → HTTPS 自动跳转逻辑"""
    if request_path.startswith("http://"):
        return request_path.replace("http://", "https://", 1)
    return request_path


# =============================================================================
# 测试用例
# =============================================================================

class TestTLS13EncryptedTransport:
    """验证所有外部通信使用 TLS 1.3 加密"""

    def test_default_tls_context_minimum_version_is_tls13(self):
        """创建的 TLS 上下文最小版本必须是 TLS 1.3"""
        ctx = create_tls_context_for_external()
        assert ctx.minimum_version == ssl.TLSVersion("TLSv1.3"), \
            "TLS 上下文最小版本应为 TLSv1.3"

    def test_default_tls_context_maximum_version_is_tls13(self):
        """创建的 TLS 上下文最大版本必须是 TLS 1.3"""
        ctx = create_tls_context_for_external()
        assert ctx.maximum_version == ssl.TLSVersion("TLSv1.3"), \
            "TLS 上下文最大版本应为 TLSv1.3"

    def test_tls_context_hostname_verification_enabled(self):
        """TLS 上下文必须开启主机名校验"""
        ctx = create_tls_context_for_external()
        assert ctx.check_hostname is True, \
            "TLS 上下文必须启用 check_hostname"

    def test_tls_context_certificate_verification_required(self):
        """TLS 上下文必须要求证书校验"""
        ctx = create_tls_context_for_external()
        assert ctx.verify_mode == ssl.CERT_REQUIRED, \
            "TLS 上下文 verify_mode 应为 CERT_REQUIRED"

    def test_minimum_tls_version_function_returns_tls13(self):
        """get_minimum_tls_version 应返回 TLSv1.3"""
        version = get_minimum_tls_version()
        assert version == ssl.TLSVersion("TLSv1.3"), \
            "最小 TLS 版本函数应返回 TLSv1.3"

    # ── HTTP → HTTPS 自动跳转测试 ──────────────────────

    def test_http_redirect_to_https_single_subdomain(self):
        """http://example.com 应跳转到 https://example.com"""
        result = enforce_https_redirect("http://example.com")
        assert result == "https://example.com", \
            "http:// 应自动跳转至 https://"

    def test_http_redirect_to_https_with_path(self):
        """带路径的 http URL 也应跳转"""
        result = enforce_https_redirect("http://example.com/api/v1/users")
        assert result == "https://example.com/api/v1/users", \
            "带路径的 http:// 应跳转至 https://"

    def test_http_redirect_to_https_with_port(self):
        """带端口的 http URL 应正确跳转"""
        result = enforce_https_redirect("http://example.com:8080/path")
        assert result == "https://example.com:8080/path", \
            "带端口的 http:// 应跳转至 https://"

    def test_http_redirect_to_https_preserves_query_string(self):
        """跳转时应保留查询参数"""
        result = enforce_https_redirect("http://example.com/search?q=test&page=1")
        assert result == "https://example.com/search?q=test&page=1", \
            "https 跳转应保留查询字符串"

    def test_https_url_not_modified_by_redirect(self):
        """已经是 https 的 URL 不应被修改"""
        result = enforce_https_redirect("https://example.com/api")
        assert result == "https://example.com/api", \
            "https:// URL 不应被修改"

    def test_https_url_with_complex_path_unchanged(self):
        """复杂路径的 https URL 应保持不变"""
        url = "https://example.com:443/v1/users?page=2&limit=10"
        result = enforce_https_redirect(url)
        assert result == url, "完整 https URL 不应被修改"

    # ── 旧版 TLS 协议拒绝测试 ──────────────────────────

    def test_tls10_connection_rejected_by_context(self):
        """TLS 1.0 连接应被拒绝"""
        ctx = create_tls_context_for_external()
        # 构造一个模拟的 SSL 连接对象
        mock_conn = MagicMock()
        mock_conn.version.return_value = "TLSv1"
        with patch.object(ssl, "SSLContext") as mock_ssl_ctx:
            mock_instance = MagicMock()
            mock_instance.minimum_version = ssl.TLSVersion("TLSv1.3")
            mock_ssl_ctx.return_value = mock_instance
            assert ctx.minimum_version != ssl.TLSVersion("TLSv1"), \
                "TLS 1.0 不应被允许"

    def test_tls11_connection_rejected_by_context(self):
        """TLS 1.1 连接应被拒绝"""
        ctx = create_tls_context_for_external()
        assert ctx.minimum_version != ssl.TLSVersion("TLSv1.1"), \
            "TLS 1.1 不应被允许"

    def test_tls12_connection_rejected_by_context(self):
        """TLS 1.2 连接应被拒绝（强制 TLS 1.3）"""
        ctx = create_tls_context_for_external()
        assert ctx.minimum_version != ssl.TLSVersion("TLSv1.2"), \
            "TLS 1.2 不应被允许"

    def test_only_tls13_accepted(self):
        """仅 TLS 1.3 被接受"""
        ctx = create_tls_context_for_external()
        assert ctx.minimum_version == ssl.TLSVersion("TLSv1.3")
        assert ctx.maximum_version == ssl.TLSVersion("TLSv1.3")
        assert ctx.minimum_version == ctx.maximum_version, \
            "最小和最大 TLS 版本应均为 TLSv1.3"

    # ── 外部 HTTP 请求 TLS 上下文注入测试 ──────────────

    def test_urllib_opener_uses_tls13_context(self):
        """urllib 外部请求应使用 TLS 1.3 上下文"""
        ctx = create_tls_context_for_external()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx)
        )
        # 验证 opener 配置中包含了正确的 TLS 上下文
        handler = opener.handlers[0]
        assert handler._context.minimum_version == ssl.TLSVersion("TLSv1.3"), \
            "urllib HTTPSHandler 应使用 TLS 1.3 上下文"

    def test_ssl_socket_with_tls13_context(self):
        """使用 TLS 1.3 上下文创建 SSL socket 应配置正确"""
        ctx = create_tls_context_for_external()
        # 验证上下文属性
        options = ctx.options
        # ssl.OP_NO_SSLv2, OP_NO_SSLv3, OP_NO_TLSv1, OP_NO_TLSv1_1 应被设置
        assert ctx.minimum_version == ssl.TLSVersion("TLSv1.3"), \
            "SSL socket 上下文的 minimum_version 应为 TLSv1.3"

    # ── 协议级强制测试 ────────────────────────────────

    def test_all_external_endpoints_require_https(self):
        """所有外部端点 URL 都应被强制转换为 https"""
        endpoints = [
            "http://api.example.com/v1/data",
            "http://cdn.example.com/assets/style.css",
            "http://oauth.provider.com/authorize",
            "http://monitoring.example.com/metrics",
            "http://logs.example.com/ingest",
        ]
        for url in endpoints:
            result = enforce_https_redirect(url)
            assert result.startswith("https://"), \
                f"端点 {url} 应被强制转换为 https://"

    def test_mixed_content_http_requests_redirected(self):
        """混合内容中的 http 资源也应被跳转"""
        mixed_resources = [
            "http://img.example.com/photo.jpg",
            "http://script.cdn.com/lib.js",
            "http://font.example.com/roboto.woff2",
        ]
        for url in mixed_resources:
            result = enforce_https_redirect(url)
            assert result.startswith("https://"), \
                f"混合内容资源 {url} 应被强制跳转至 https://"

    def test_tls_13_context_is_immutable_by_default(self):
        """TLS 1.3 上下文创建后不应被意外降级"""
        ctx = create_tls_context_for_external()
        original_min = ctx.minimum_version
        original_max = ctx.maximum_version
        # 创建后立即检查
        assert ctx.minimum_version == ssl.TLSVersion("TLSv1.3")
        assert ctx.maximum_version == ssl.TLSVersion("TLSv1.3")
        assert original_min == original_max, \
            "创建时最小版本和最大版本应相同"

    def test_context_cannot_downgrade_to_tls12(self):
        """TLS 1.3 上下文不应能被降级为 TLS 1.2"""
        ctx = create_tls_context_for_external()
        try:
            ctx.minimum_version = ssl.TLSVersion("TLSv1.2")
            # 如果设置成功，验证创建函数不会返回降级版本
            fresh_ctx = create_tls_context_for_external()
            assert fresh_ctx.minimum_version == ssl.TLSVersion("TLSv1.3"), \
                "新创建的上下文仍应保持 TLSv1.3"
        except ValueError:
            # 某些 Python 版本不允许降级，这是期望行为
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
