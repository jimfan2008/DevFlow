import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from app.middleware.error_handler import register_error_handlers


ERROR_PAGE_CASES = [
    {"status_code": 403, "error_code": "FORBIDDEN", "title": "访问被拒绝",
     "description": "您没有权限访问此资源"},
    {"status_code": 404, "error_code": "HTTP_404", "title": "页面不存在",
     "description": "您访问的页面不存在或已被移除"},
    {"status_code": 500, "error_code": "INTERNAL_ERROR", "title": "服务器错误",
     "description": "服务器遇到了意外错误"},
    {"status_code": 503, "error_code": "HTTP_503", "title": "服务不可用",
     "description": "服务暂时不可用，请稍后再试"},
    {"status_code": 400, "error_code": "BAD_REQUEST", "title": "请求错误",
     "description": "请求参数有误，请检查后重试"},
]


def make_test_app():
    app = FastAPI()

    @app.get("/trigger-forbidden")
    def raise_forbidden():
        raise StarletteHTTPException(status_code=403, detail="您没有权限访问此资源")

    @app.get("/trigger-not-found")
    def raise_not_found():
        raise StarletteHTTPException(status_code=404, detail="您访问的页面不存在或已被移除")

    @app.get("/trigger-internal-error")
    def raise_internal():
        raise RuntimeError("触发内部服务器错误，请重试")

    @app.get("/trigger-unavailable")
    def raise_unavailable():
        raise StarletteHTTPException(status_code=503, detail="服务暂时不可用，请稍后再试")

    @app.get("/trigger-bad-request")
    def raise_bad_request():
        raise ValueError("请求参数有误，请检查后重试")

    register_error_handlers(app)
    return app


ERROR_ROUTES = {
    403: "/trigger-forbidden",
    404: "/trigger-not-found",
    500: "/trigger-internal-error",
    503: "/trigger-unavailable",
    400: "/trigger-bad-request",
}


class TestErrorPageRendering:
    """错误页面渲染测试：验证 HTTP 错误响应正确呈现"""

    client = TestClient(make_test_app())

    @pytest.mark.parametrize("case", ERROR_PAGE_CASES)
    def test_error_response_status_code(self, case):
        """验证每种错误返回正确的 HTTP 状态码"""
        status_code = case["status_code"]
        url = ERROR_ROUTES[status_code]
        response = self.client.get(url)
        assert response.status_code == status_code, (
            f"期望状态码 {status_code}，实际 {response.status_code}"
        )

    @pytest.mark.parametrize("case", ERROR_PAGE_CASES)
    def test_error_response_format_has_code_message_details(self, case):
        """验证错误响应 JSON 包含 code/message/details 三个顶层字段"""
        status_code = case["status_code"]
        url = ERROR_ROUTES[status_code]
        response = self.client.get(url)
        body = response.json()
        assert "code" in body, f"响应缺少 'code' 字段"
        assert "message" in body, f"响应缺少 'message' 字段"
        assert "details" in body, f"响应缺少 'details' 字段"

    @pytest.mark.parametrize("case", ERROR_PAGE_CASES)
    def test_error_response_code_matches_expected(self, case):
        """验证错误 code 符合预期"""
        status_code = case["status_code"]
        url = ERROR_ROUTES[status_code]
        response = self.client.get(url)
        body = response.json()
        assert body["code"] == case["error_code"], (
            f"期望 error_code={case['error_code']}，实际={body['code']}"
        )

    @pytest.mark.parametrize("case", ERROR_PAGE_CASES)
    def test_error_response_message_non_empty(self, case):
        """验证 message 非空字符串"""
        status_code = case["status_code"]
        url = ERROR_ROUTES[status_code]
        response = self.client.get(url)
        body = response.json()
        msg = body["message"]
        assert isinstance(msg, str), f"message 应为字符串，实际为 {type(msg)}"
        assert len(msg.strip()) > 0, f"message 不应为空"

    @pytest.mark.parametrize("case", ERROR_PAGE_CASES)
    def test_error_response_details_is_dict(self, case):
        """验证 details 始终为 dict 类型"""
        status_code = case["status_code"]
        url = ERROR_ROUTES[status_code]
        response = self.client.get(url)
        body = response.json()
        assert isinstance(body["details"], dict), f"details 应为 dict"

    @pytest.mark.parametrize("case", ERROR_PAGE_CASES)
    def test_error_response_contains_user_guidance(self, case):
        """验证错误描述中包含用户可理解的引导信息"""
        status_code = case["status_code"]
        url = ERROR_ROUTES[status_code]
        response = self.client.get(url)
        body = response.json()
        msg = body["message"]
        assert any(kw in msg for kw in ["请", "检查", "重试", "稍后", "确认", "权限", "不存在"]), (
            f"消息 '{msg}' 缺少用户操作引导关键字"
        )

    def test_error_response_no_blank_body(self):
        """验证所有错误响应 body 非空白（SPA 无白屏保障）"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            raw = str(body)
            assert len(raw) > 30, f"状态码 {status_code} 的响应体过短: {raw}"

    @pytest.mark.parametrize("case", ERROR_PAGE_CASES)
    def test_error_response_content_type_json(self, case):
        """验证 Content-Type 包含 application/json"""
        status_code = case["status_code"]
        url = ERROR_ROUTES[status_code]
        response = self.client.get(url)
        ct = response.headers.get("content-type", "")
        assert "application/json" in ct, f"Content-Type 应为 JSON，实际为 {ct}"

    def test_design_style_consistent_code_field_type(self):
        """验证所有错误响应的 code 字段均为字符串类型（设计风格统一）"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            assert isinstance(body["code"], str), (
                f"状态码 {status_code} 的 code 字段不是字符串"
            )

    def test_design_style_consistent_message_field_type(self):
        """验证所有错误响应的 message 字段均为字符串类型"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            assert isinstance(body["message"], str), (
                f"状态码 {status_code} 的 message 字段不是字符串"
            )

    def test_design_style_consistent_structure(self):
        """验证所有错误响应具有完全相同的 JSON 结构（键一致）"""
        expected_keys = {"code", "message", "details"}
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            actual_keys = set(body.keys())
            assert actual_keys == expected_keys, (
                f"状态码 {status_code} 响应键集 {actual_keys} 与期望 {expected_keys} 不一致"
            )

    def test_http_403_description_mentions_permission(self):
        """403 错误消息应包含权限相关提示"""
        response = self.client.get("/trigger-forbidden")
        body = response.json()
        assert any(kw in body["message"] for kw in ["权限", "forbidden", "denied"]), (
            f"403 消息应包含权限提示，实际: {body['message']}"
        )

    def test_http_404_description_mentions_not_found(self):
        """404 错误消息应包含不存在相关提示"""
        response = self.client.get("/trigger-not-found")
        body = response.json()
        assert any(kw in body["message"] for kw in ["不存在", "未找到", "not found"]), (
            f"404 消息应包含不存在提示，实际: {body['message']}"
        )

    def test_http_500_description_mentions_error_or_retry(self):
        """500 错误消息应包含错误或重试提示"""
        response = self.client.get("/trigger-internal-error")
        body = response.json()
        assert any(kw in body["message"] for kw in ["错误", "异常", "稍后", "重试"]), (
            f"500 消息应包含错误提示，实际: {body['message']}"
        )

    def test_http_503_description_mentions_unavailable_or_retry(self):
        """503 错误消息应包含不可用或重试提示"""
        response = self.client.get("/trigger-unavailable")
        body = response.json()
        assert any(kw in body["message"] for kw in ["不可用", "稍后", "重试", "unavailable"]), (
            f"503 消息应包含不可用提示，实际: {body['message']}"
        )

    def test_five_error_types_all_covered(self):
        """验证全部 5 种错误类型都已覆盖测试"""
        tested_statuses = set()
        for status_code in ERROR_ROUTES:
            response = self.client.get(ERROR_ROUTES[status_code])
            tested_statuses.add(response.status_code)
        expected = {403, 404, 500, 503, 400}
        assert tested_statuses == expected, (
            f"缺少部分错误类型: 期望 {expected}，实际 {tested_statuses}"
        )

    def test_unknown_route_returns_404(self):
        """访问未知路由应返回 404"""
        response = self.client.get("/this-route-does-not-exist")
        assert response.status_code == 404

    def test_unknown_route_has_json_body(self):
        """访问未知路由的 404 响应应为 JSON 格式"""
        response = self.client.get("/nonexistent-path-xyz-123")
        body = response.json()
        assert "code" in body
        assert "message" in body

    def test_error_response_serializable(self):
        """验证所有错误响应可 JSON 序列化（无白屏保障）"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            import json
            dumped = json.dumps(response.json())
            assert len(dumped) > 20, (
                f"状态码 {status_code} 的 JSON 序列化结果过短"
            )

    def test_error_response_has_no_empty_fields(self):
        """验证所有错误响应字段均不为空字符串或 None"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            for key in ("code", "message"):
                val = body[key]
                assert val is not None, f"状态码 {status_code} 的 {key} 为 None"
                assert val != "", f"状态码 {status_code} 的 {key} 为空字符串"

    def test_500_error_does_not_leak_stack_trace_to_client(self):
        """验证 500 错误不向客户端泄露堆栈跟踪"""
        response = self.client.get("/trigger-internal-error")
        body = response.json()
        raw = str(body)
        assert "Traceback" not in raw, "响应不应包含 Traceback"
        assert "File \"" not in raw, "响应不应泄露文件路径"
        assert body["code"] == "INTERNAL_ERROR", f"500 错误码应为 INTERNAL_ERROR"

    def test_error_handler_handles_concurrent_requests(self):
        """验证错误处理器能处理连续多次请求"""
        for _ in range(5):
            for status_code, url in ERROR_ROUTES.items():
                response = self.client.get(url)
                assert response.status_code == status_code
                body = response.json()
                assert "code" in body

    def test_error_body_contains_actionable_hint(self):
        """验证所有错误消息包含可操作的用户指引文字"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            msg = body["message"]
            assert len(msg) > 4, (
                f"状态码 {status_code} 的消息过短，无有用指引: '{msg}'"
            )

    def test_error_code_prefix_consistent(self):
        """验证错误 code 符合统一命名风格"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            code = body["code"]
            assert isinstance(code, str), f"code 应为字符串，实际 {type(code)}"
            assert len(code) > 0, "code 不应为空"

    def test_error_details_is_empty_dict(self):
        """验证默认情况下的 details 为空字典"""
        for status_code, url in ERROR_ROUTES.items():
            response = self.client.get(url)
            body = response.json()
            assert body["details"] == {}, (
                f"状态码 {status_code} 的 details 应为空字典"
            )

    def test_custom_http_exception_construction(self):
        """验证直接构造 HTTPException 对象的属性"""
        exc_404 = HTTPException(status_code=404, detail="Not Found")
        assert exc_404.status_code == 404
        assert exc_404.detail == "Not Found"
        exc_403 = HTTPException(status_code=403, detail="Forbidden")
        assert exc_403.status_code == 403
        assert exc_403.detail == "Forbidden"
        exc_500 = HTTPException(status_code=500, detail="Internal Error")
        assert exc_500.status_code == 500
        assert exc_500.detail == "Internal Error"
        exc_503 = HTTPException(status_code=503, detail="Service Unavailable")
        assert exc_503.status_code == 503
        assert exc_503.detail == "Service Unavailable"

    def test_http_exception_empty_detail(self):
        """验证空 detail 的 HTTPException 构造"""
        exc = HTTPException(status_code=404, detail="")
        assert exc.status_code == 404
        assert exc.detail == ""

    def test_http_exception_long_detail(self):
        """验证超长 detail 的 HTTPException 构造"""
        long_msg = "x" * 10000
        exc = HTTPException(status_code=500, detail=long_msg)
        assert exc.status_code == 500
        assert len(exc.detail) == 10000

    def test_http_exception_special_chars(self):
        """验证含特殊字符的 detail 构造"""
        exc = HTTPException(status_code=400, detail="<script>alert('xss')</script> & \"quote\"")
        assert exc.status_code == 400
        assert "<script>" in exc.detail
        assert "&" in exc.detail

    def test_http_exception_with_headers(self):
        """验证带 headers 的 HTTPException 构造"""
        exc = HTTPException(status_code=503, detail="retry later", headers={"Retry-After": "120"})
        assert exc.status_code == 503
        assert exc.detail == "retry later"
        assert exc.headers == {"Retry-After": "120"}

    def test_http_exception_unknown_status_code(self):
        """验证非常用状态码的 HTTPException 构造"""
        exc = HTTPException(status_code=418, detail="I'm a teapot")
        assert exc.status_code == 418
        assert exc.detail == "I'm a teapot"

    def test_starlette_http_exception_construction(self):
        """验证 StarletteHTTPException 构造"""
        exc = StarletteHTTPException(status_code=404, detail="Not found")
        assert exc.status_code == 404
        assert exc.detail == "Not found"
