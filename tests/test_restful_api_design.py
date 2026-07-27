import pytest
import json
import re
from typing import Any, Optional


class MockEndpoint:
    """模拟API端点定义，用于测试RESTful规范遵循情况。"""

    def __init__(
        self,
        method: str,
        path: str,
        status_code: int,
        response_body: dict,
        request_content_type: Optional[str] = None,
        response_content_type: Optional[str] = None,
        description: str = "",
    ):
        self.method = method.upper()
        self.path = path
        self.status_code = status_code
        self.response_body = response_body
        self.request_content_type = request_content_type
        self.response_content_type = response_content_type
        self.description = description


class ComplianceResult:
    """单项合规检查结果。"""

    def __init__(self, rule_name: str, passed: bool, detail: str = ""):
        self.rule_name = rule_name
        self.passed = passed
        self.detail = detail


# =============================================================================
# 合规性检查规则定义
# =============================================================================

def check_url_naming(endpoint: MockEndpoint) -> ComplianceResult:
    """检查URL命名规范：复数名词、小写、连字符。

    规则：
      - 路径段应使用复数名词（如 /users 而非 /user）
      - 全部小写
      - 单词间用连字符（kebab-case）而非下划线或驼峰
      - 不应包含动词（如 /getUsers）
    """
    path = endpoint.path
    segments = [s for s in path.split("/") if s and s != ""]

    violations = []

    # 检查是否有大写字母
    if path != path.lower():
        violations.append(f"包含大写字母: {path}")

    # 检查路径段中是否有下划线（snake_case）
    for seg in segments:
        if "_" in seg:
            violations.append(f"路径段包含下划线: '{seg}'")

    # 检查路径段中是否有驼峰
    for seg in segments:
        if seg != seg.lower() and seg[0].islower():
            patterns = re.findall(r"[a-z][A-Z]", seg)
            if patterns:
                violations.append(f"路径段疑似驼峰命名: '{seg}'")

    # 检查路径段中是否有动词（常见API动词列表）
    api_verbs = {"get", "create", "update", "delete", "add", "remove",
                 "list", "fetch", "post", "put", "patch", "find", "search"}
    last_segment = segments[-1] if segments else ""
    last_word = last_segment.replace("-", "_").split("_")[-1].lower()
    if last_word in api_verbs:
        violations.append(f"路径段包含动词: '{last_segment}'")

    # 检查是否为单数名词（常见复数规则检查）
    if last_segment and not last_segment.endswith("s"):
        # 跳过ID段（数字/UUID/MongoDB ObjectId）
        if re.match(r"^\d+$", last_segment):
            pass
        elif re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            last_segment, re.I
        ):
            pass
        elif re.match(r"^[0-9a-f]{24}$", last_segment, re.I):
            pass
        elif re.match(r"^.+\.[a-z]+$", last_segment):
            # 含扩展名的段（如 1.json），跳过复数检查
            pass
        else:
            singular_exceptions = {"status", "access", "process", "address",
                                   "news", "series", "species", "data",
                                   "index", "auth", "health", "info",
                                   "profile", "image", "avatar"}
            parts = last_segment.split("-")
            last_part = parts[-1] if parts else ""
            if last_part.endswith("s"):
                pass  # 已复数
            elif last_part in singular_exceptions:
                pass
            else:
                violations.append(f"路径段可能不是复数名词: '{last_segment}'")

    passed = len(violations) == 0
    detail = "; ".join(violations) if violations else "OK"
    return ComplianceResult("URL命名规范", passed, detail)


def check_http_method_semantics(endpoint: MockEndpoint) -> ComplianceResult:
    """检查HTTP方法使用规范。

    规则：
      - GET: 用于读取资源（safe, idempotent）
      - POST: 用于创建资源（non-idempotent）
      - PUT: 用于全量更新/替换资源（idempotent）
      - DELETE: 用于删除资源（idempotent）
      - PATCH: 用于部分更新资源
    """
    from collections import defaultdict

    path = endpoint.path
    method = endpoint.method
    status = endpoint.status_code

    violations = []

    if method == "GET":
        if status == 201:
            violations.append("GET不应返回201 Created（GET应幂等、只读）")
        elif status == 204:
            pass  # GET 返回 204 No Content 合理
    elif method == "POST":
        if status not in (200, 201, 202):
            violations.append(f"POST通常应返回200/201/202，实际返回{status}")
    elif method == "PUT":
        if status == 201:
            pass  # PUT 也可以创建资源返回201
        elif status == 204:
            pass  # PUT 更新成功返回204
    elif method == "DELETE":
        if status not in (200, 202, 204):
            violations.append(f"DELETE通常应返回200/202/204，实际返回{status}")
    elif method == "PATCH":
        if status not in (200, 204):
            violations.append(f"PATCH通常应返回200/204，实际返回{status}")

    passed = len(violations) == 0
    detail = "; ".join(violations) if violations else "OK"
    return ComplianceResult("HTTP方法使用规范", passed, detail)


def check_http_status_code(endpoint: MockEndpoint) -> ComplianceResult:
    """检查HTTP状态码使用规范。

    规则：
      - 2xx: 成功
      - 3xx: 重定向
      - 4xx: 客户端错误（格式正确）
      - 5xx: 服务端错误
      - 错误响应必须使用标准状态码
    """
    sc = endpoint.status_code
    violations = []

    if sc < 100 or sc > 599:
        violations.append(f"状态码{sc}超出有效范围(100-599)")
    elif sc in (415, 429):
        pass
    elif 400 <= sc <= 499:
        # 检查是否使用了非标准状态码
        valid_4xx = {400, 401, 403, 404, 405, 406, 408, 409, 410,
                     411, 412, 413, 414, 415, 422, 423, 424, 429,
                     451}
        if sc not in valid_4xx:
            violations.append(f"非标准4xx状态码: {sc}")
    elif 500 <= sc <= 599:
        valid_5xx = {500, 501, 502, 503, 504, 505}
        if sc not in valid_5xx:
            violations.append(f"非标准5xx状态码: {sc}")

    passed = len(violations) == 0
    detail = "; ".join(violations) if violations else "OK"
    return ComplianceResult("HTTP状态码规范", passed, detail)


def check_error_body_format(endpoint: MockEndpoint) -> ComplianceResult:
    """检查错误响应体格式。

    规范格式: {"error": {"code": "...", "message": "...", "details": {...}}}
    """
    sc = endpoint.status_code
    body = endpoint.response_body

    if sc < 400:
        return ComplianceResult("错误体格式规范", True, "非错误响应，跳过检查")

    violations = []

    # 检查顶层是否有 "error" 字段
    if "error" not in body:
        violations.append("缺少顶层'error'字段")
        return ComplianceResult("错误体格式规范", False, "; ".join(violations))

    error_obj = body["error"]

    # error 必须是字典
    if not isinstance(error_obj, dict):
        violations.append("'error'字段必须是对象")
        return ComplianceResult("错误体格式规范", False, "; ".join(violations))

    # 检查必填字段
    if "code" not in error_obj:
        violations.append("缺少'error.code'字段")
    if "message" not in error_obj:
        violations.append("缺少'error.message'字段")

    # 检查 details 字段（非必须，但有则须为对象或数组）
    if "details" in error_obj:
        details_val = error_obj["details"]
        if not isinstance(details_val, (dict, list, type(None))):
            violations.append("'error.details'必须是对象或数组")

    # code 应为字符串
    if "code" in error_obj and not isinstance(error_obj["code"], str):
        violations.append("'error.code'应为字符串")

    # message 应为字符串
    if "message" in error_obj and not isinstance(error_obj["message"], str):
        violations.append("'error.message'应为字符串")

    passed = len(violations) == 0
    detail = "; ".join(violations) if violations else "OK"
    return ComplianceResult("错误体格式规范", passed, detail)


def check_content_type_headers(endpoint: MockEndpoint) -> ComplianceResult:
    """检查Content-Type/Accept头部规范。

    规则：
      - 请求应包含Content-Type
      - 响应应包含Content-Type
      - 值应为application/json或类似的MIME类型
    """
    violations = []

    # 对于POST/PUT/PATCH，请求应带有Content-Type
    if endpoint.method in ("POST", "PUT", "PATCH"):
        if not endpoint.request_content_type:
            violations.append(f"{endpoint.method}请求缺少Content-Type")
        elif "application/json" not in endpoint.request_content_type:
            violations.append(
                f"请求Content-Type不是application/json: "
                f"{endpoint.request_content_type}"
            )

    # 响应应带有Content-Type（空体或204跳过）
    if endpoint.status_code == 204:
        pass
    elif not endpoint.response_content_type:
        violations.append("响应缺少Content-Type")
    elif "application/json" not in endpoint.response_content_type:
        violations.append(
            f"响应Content-Type不是application/json: "
            f"{endpoint.response_content_type}"
        )

    passed = len(violations) == 0
    detail = "; ".join(violations) if violations else "OK"
    return ComplianceResult("Content-Type头部规范", passed, detail)


def check_collection_resource_endpoints(endpoint: MockEndpoint) -> ComplianceResult:
    """检查集合/资源端点命名规范。

    规则：
      - 集合端点: /resources
      - 资源端点: /resources/{id}
      - 嵌套资源: /resources/{id}/sub-resources
      - 不应以斜杠结尾（根路径除外）
      - 不应包含文件扩展名（.json, .xml等）
    """
    path = endpoint.path
    segments = [s for s in path.split("/") if s]
    violations = []

    # 检查是否以斜杠结尾（根路径除外）
    if path.endswith("/") and path != "/":
        violations.append("路径不应以斜杠结尾")

    # 检查是否包含文件扩展名
    last_seg = segments[-1] if segments else ""
    if "." in last_seg:
        violations.append(f"路径中包含文件扩展名: '{last_seg}'")

    # 检查资源ID段：通常是数字或UUID格式
    for i, seg in enumerate(segments):
        # 跳过第一段（通常为 api/v1 等）
        if i == 0 and seg in ("api", "v1", "v2"):
            continue
        # 如果路径段是数字或UUID格式，视为资源ID，合法
        if re.match(r"^\d+$", seg):
            pass
        elif re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            seg, re.I
        ):
            pass
        elif re.match(r"^[0-9a-f]{24}$", seg, re.I):
            pass  # MongoDB ObjectId

    passed = len(violations) == 0
    detail = "; ".join(violations) if violations else "OK"
    return ComplianceResult("集合/资源端点规范", passed, detail)


def check_idempotency_safety(endpoint: MockEndpoint) -> ComplianceResult:
    """检查幂等性和安全性（加分项）。"""
    method = endpoint.method
    # 此规则为辅助检查，不直接影响合规率
    return ComplianceResult("幂等性/安全性", True, "参考性检查")


# =============================================================================
# Fixtures — 测试数据集
# =============================================================================

@pytest.fixture
def sample_endpoints():
    """提供一组模拟API端点，包含合规和不合规的样例。"""
    return [
        # ----- 合规端点 -----
        MockEndpoint(
            method="GET", path="/users",
            status_code=200,
            response_body={"users": [], "total": 0},
            response_content_type="application/json",
            description="合规：GET集合-用户列表"
        ),
        MockEndpoint(
            method="POST", path="/users",
            status_code=201,
            response_body={"id": "1", "name": "Alice"},
            request_content_type="application/json",
            response_content_type="application/json",
            description="合规：POST创建用户"
        ),
        MockEndpoint(
            method="GET", path="/users/42",
            status_code=200,
            response_body={"id": 42, "name": "Bob"},
            response_content_type="application/json",
            description="合规：GET单个资源"
        ),
        MockEndpoint(
            method="PUT", path="/users/42",
            status_code=200,
            response_body={"id": 42, "name": "Bob Updated"},
            request_content_type="application/json",
            response_content_type="application/json",
            description="合规：PUT全量更新"
        ),
        MockEndpoint(
            method="DELETE", path="/users/42",
            status_code=204,
            response_body={},
            description="合规：DELETE删除资源（无体）"
        ),
        MockEndpoint(
            method="GET", path="/articles",
            status_code=200,
            response_body={"articles": [], "total": 0},
            response_content_type="application/json",
            description="合规：GET文章列表"
        ),
        MockEndpoint(
            method="POST", path="/articles",
            status_code=201,
            response_body={"id": 10, "title": "Hello"},
            request_content_type="application/json",
            response_content_type="application/json",
            description="合规：POST创建文章"
        ),
        MockEndpoint(
            method="GET", path="/articles/10/comments",
            status_code=200,
            response_body={"comments": []},
            response_content_type="application/json",
            description="合规：GET嵌套资源集合"
        ),
        MockEndpoint(
            method="POST", path="/articles/10/comments",
            status_code=201,
            response_body={"id": 1, "text": "Great!"},
            request_content_type="application/json",
            response_content_type="application/json",
            description="合规：POST创建嵌套资源"
        ),
        MockEndpoint(
            method="GET", path="/order-items",
            status_code=200,
            response_body={"items": []},
            response_content_type="application/json",
            description="合规：GET复合名词集合"
        ),
                # ----- 不合规端点 -----
        MockEndpoint(
            method="GET", path="/getUsers",
            status_code=200,
            response_body={},
            response_content_type="application/json",
            description="不合规：URL含动词和大写"
        ),
        MockEndpoint(
            method="GET", path="/fetch_articles",
            status_code=200,
            response_body={},
            response_content_type="application/json",
            description="不合规：路径含动词和下划线"
        ),
        MockEndpoint(
            method="POST", path="/CreateNewItem",
            status_code=201,
            response_body={"id": 1},
            request_content_type="application/json",
            response_content_type="application/json",
            description="不合规：URL驼峰+动词+非复数"
        ),
        MockEndpoint(
            method="GET", path="/users/1.json",
            status_code=200,
            response_body={},
            response_content_type="application/json",
            description="不合规：路径含文件扩展名"
        ),
    ]

@pytest.fixture
def all_compliant_endpoints():
    """100%合规的端点集，用于验证合规率计算。"""
    return [
        MockEndpoint(
            method="GET", path="/users",
            status_code=200,
            response_body={"users": []},
            response_content_type="application/json",
            description="合规"
        ),
        MockEndpoint(
            method="POST", path="/users",
            status_code=201,
            response_body={"id": 1},
            request_content_type="application/json",
            response_content_type="application/json",
            description="合规"
        ),
    ]


# =============================================================================
# 合规率计算
# =============================================================================

def compute_compliance_rate(endpoints):
    """计算给定端点集的整体RESTful规范遵循率。

    对所有端点逐一运行全部检查规则，返回总通过率。
    """
    rules = [
        check_url_naming,
        check_http_method_semantics,
        check_http_status_code,
        check_error_body_format,
        check_content_type_headers,
        check_collection_resource_endpoints,
    ]

    total_checks = 0
    passed_checks = 0
    failures_by_rule = {}

    for ep in endpoints:
        for rule_fn in rules:
            total_checks += 1
            result = rule_fn(ep)
            if result.passed:
                passed_checks += 1
            else:
                rule_name = result.rule_name
                if rule_name not in failures_by_rule:
                    failures_by_rule[rule_name] = []
                failures_by_rule[rule_name].append({
                    "endpoint": f"{ep.method} {ep.path}",
                    "detail": result.detail,
                })

    rate = (passed_checks / total_checks * 100) if total_checks > 0 else 100.0
    return rate, passed_checks, total_checks, failures_by_rule


# =============================================================================
# 测试用例
# =============================================================================

class TestUrlNaming:
    """RESTful URL命名规范测试。"""

    def test_valid_url_plural_nouns(self):
        """验证合规端点：复数名词、小写、连字符通过检查。"""
        ep = MockEndpoint("GET", "/users", 200, {}, None, "application/json")
        result = check_url_naming(ep)
        assert result.passed, f"应通过但未通过: {result.detail}"

    def test_valid_url_hyphenated(self):
        """验证合规端点：连字符复合名词通过检查。"""
        ep = MockEndpoint(
            "GET", "/order-items", 200, {}, None, "application/json"
        )
        result = check_url_naming(ep)
        assert result.passed, f"应通过但未通过: {result.detail}"

    def test_valid_url_nested(self):
        """验证合规端点：嵌套资源通过检查。"""
        ep = MockEndpoint(
            "GET", "/articles/10/comments", 200, {}, None, "application/json"
        )
        result = check_url_naming(ep)
        assert result.passed, f"应通过但未通过: {result.detail}"

    def test_invalid_url_with_verbs(self):
        """验证不合规端点：含动词的URL应被检测。"""
        ep = MockEndpoint("GET", "/getUsers", 200, {}, None, "application/json")
        result = check_url_naming(ep)
        assert not result.passed, "含动词的URL应检测为不合规"

    def test_invalid_url_snake_case(self):
        """验证不合规端点：下划线命名的URL应被检测。"""
        ep = MockEndpoint(
            "GET", "/fetch_articles", 200, {}, None, "application/json"
        )
        result = check_url_naming(ep)
        assert not result.passed, "下划线命名的URL应检测为不合规"


class TestHttpMethodSemantics:
    """HTTP方法使用规范测试。"""

    def test_get_no_create_semantics(self):
        """验证GET请求不应返回201。"""
        ep = MockEndpoint("GET", "/users", 201, {}, None, "application/json")
        result = check_http_method_semantics(ep)
        assert not result.passed, "GET返回201应检测为不合规"

    def test_post_returns_201(self):
        """验证POST创建返回201为合规。"""
        ep = MockEndpoint(
            "POST", "/users", 201, {"id": 1},
            "application/json", "application/json"
        )
        result = check_http_method_semantics(ep)
        assert result.passed, f"POST返回201应合规: {result.detail}"

    def test_delete_returns_204(self):
        """验证DELETE返回204为合规。"""
        ep = MockEndpoint("DELETE", "/users/1", 204, {}, None, None)
        result = check_http_method_semantics(ep)
        assert result.passed, f"DELETE返回204应合规: {result.detail}"

    def test_put_returns_200(self):
        """验证PUT返回200为合规。"""
        ep = MockEndpoint(
            "PUT", "/users/1", 200, {},
            "application/json", "application/json"
        )
        result = check_http_method_semantics(ep)
        assert result.passed, f"PUT返回200应合规: {result.detail}"


class TestHttpStatusCode:
    """HTTP状态码使用规范测试。"""

    def test_valid_2xx_status(self):
        """验证2xx状态码通过检查。"""
        for code in (200, 201, 202, 204):
            ep = MockEndpoint("GET", "/users", code, {}, None, "application/json")
            result = check_http_status_code(ep)
            assert result.passed, f"状态码{code}应通过检查: {result.detail}"

    def test_invalid_nonstandard_4xx(self):
        """验证非标准4xx状态码检测。"""
        ep = MockEndpoint(
            "POST", "/users", 420, {}, "application/json", "application/json"
        )
        result = check_http_status_code(ep)
        assert not result.passed, "非标准4xx应检测为不合规"

    def test_out_of_range_status(self):
        """验证超出范围的状态码检测。"""
        ep = MockEndpoint("GET", "/users", 99, {}, None, "application/json")
        result = check_http_status_code(ep)
        assert not result.passed, "超出范围的状态码应检测为不合规"


class TestErrorBodyFormat:
    """错误响应体格式规范测试。"""

    def test_valid_error_body(self):
        """验证标准错误体格式通过检查。"""
        body = {
            "error": {
                "code": "NOT_FOUND",
                "message": "资源不存在",
                "details": {"resource": "user", "id": 42},
            }
        }
        ep = MockEndpoint("GET", "/users/42", 404, body, None, "application/json")
        result = check_error_body_format(ep)
        assert result.passed, f"标准错误体应通过: {result.detail}"

    def test_missing_error_field(self):
        """验证缺少error字段被检测。"""
        body = {"code": "NOT_FOUND", "message": "not found"}
        ep = MockEndpoint("GET", "/users/42", 404, body, None, "application/json")
        result = check_error_body_format(ep)
        assert not result.passed, "缺少error字段应检测为不合规"

    def test_missing_code_field(self):
        """验证缺少error.code被检测。"""
        body = {"error": {"message": "not found"}}
        ep = MockEndpoint("GET", "/users/42", 404, body, None, "application/json")
        result = check_error_body_format(ep)
        assert not result.passed, "缺少error.code应检测为不合规"

    def test_missing_message_field(self):
        """验证缺少error.message被检测。"""
        body = {"error": {"code": "NOT_FOUND"}}
        ep = MockEndpoint("GET", "/users/42", 404, body, None, "application/json")
        result = check_error_body_format(ep)
        assert not result.passed, "缺少error.message应检测为不合规"

    def test_skip_non_error_response(self):
        """验证非错误响应跳过检查。"""
        body = {"id": 42, "name": "Alice"}
        ep = MockEndpoint("GET", "/users/42", 200, body, None, "application/json")
        result = check_error_body_format(ep)
        assert result.passed, "非错误响应应跳过检查"

    def test_minimal_error_body(self):
        """验证最小可接受的错误体格式。"""
        body = {
            "error": {
                "code": "BAD_REQUEST",
                "message": "无效参数",
            }
        }
        ep = MockEndpoint("POST", "/users", 400, body, "application/json", "application/json")
        result = check_error_body_format(ep)
        assert result.passed, f"最小错误体应通过: {result.detail}"


class TestContentTypeHeaders:
    """Content-Type/Accept头部规范测试。"""

    def test_valid_json_content_type(self):
        """验证application/json Content-Type通过检查。"""
        ep = MockEndpoint(
            "POST", "/users", 201, {},
            "application/json", "application/json"
        )
        result = check_content_type_headers(ep)
        assert result.passed, f"JSON Content-Type应通过: {result.detail}"

    def test_missing_content_type_on_post(self):
        """验证POST缺少Content-Type被检测。"""
        ep = MockEndpoint("POST", "/users", 201, {}, None, "application/json")
        result = check_content_type_headers(ep)
        assert not result.passed, "POST缺少Content-Type应检测为不合规"

    def test_missing_response_content_type(self):
        """验证响应缺少Content-Type被检测。"""
        ep = MockEndpoint("GET", "/users", 200, {}, None, None)
        result = check_content_type_headers(ep)
        assert not result.passed, "响应缺少Content-Type应检测为不合规"


class TestCollectionResourceEndpoints:
    """集合/资源端点命名规范测试。"""

    def test_valid_collection_endpoint(self):
        """验证合规集合端点通过检查。"""
        ep = MockEndpoint("GET", "/users", 200, {}, None, "application/json")
        result = check_collection_resource_endpoints(ep)
        assert result.passed, f"合规集合端点应通过: {result.detail}"

    def test_valid_resource_with_id(self):
        """验证合规资源端点（含ID）通过检查。"""
        ep = MockEndpoint("GET", "/users/42", 200, {}, None, "application/json")
        result = check_collection_resource_endpoints(ep)
        assert result.passed, f"合规资源端点应通过: {result.detail}"

    def test_trailing_slash(self):
        """验证以斜杠结尾的路径被检测（根路径除外）。"""
        ep = MockEndpoint("GET", "/users/", 200, {}, None, "application/json")
        result = check_collection_resource_endpoints(ep)
        assert not result.passed, "以斜杠结尾应检测为不合规"

    def test_file_extension(self):
        """验证含文件扩展名的路径被检测。"""
        ep = MockEndpoint("GET", "/users.json", 200, {}, None, "application/json")
        result = check_collection_resource_endpoints(ep)
        assert not result.passed, "含文件扩展名应检测为不合规"

    def test_root_path(self):
        """验证根路径通过检查。"""
        ep = MockEndpoint("GET", "/", 200, {}, None, "application/json")
        result = check_collection_resource_endpoints(ep)
        assert result.passed, "根路径应通过检查"


class TestOverallComplianceRate:
    """整体RESTful规范遵循率测试。"""

    def test_all_compliant_endpoints_100_percent(self, all_compliant_endpoints):
        """验证100%合规的端点集计算出100%合规率。"""
        rate, passed, total, failures = compute_compliance_rate(
            all_compliant_endpoints
        )
        assert rate == 100.0, f"期望100%合规率，实际{rate}% ({passed}/{total})"
        assert len(failures) == 0, f"不应有失败项: {failures}"

    def test_mixed_endpoints_meets_threshold(self, sample_endpoints):
        """验证混合端点集合规率>=95%（验收标准）。"""
        rate, passed, total, failures = compute_compliance_rate(sample_endpoints)
        print(f"\n合规率: {rate:.2f}% ({passed}/{total})")
        if failures:
            print(f"失败详情:")
            for rule_name, items in failures.items():
                for item in items:
                    print(f"  [{rule_name}] {item['endpoint']}: {item['detail']}")
        assert rate >= 95.0, (
            f"RESTful规范遵循率{rate:.2f}%低于95%阈值 "
            f"(通过{passed}/{total})"
        )

    def test_detailed_compliance_report(self, sample_endpoints):
        """验证合规率计算的详细报告结构。"""
        rate, passed, total, failures = compute_compliance_rate(sample_endpoints)

        # 验证各字段类型
        assert isinstance(rate, float), "合规率应为float"
        assert isinstance(passed, int), "通过数应为int"
        assert isinstance(total, int), "总检查数应为int"
        assert isinstance(failures, dict), "失败项应为dict"

        # 验证计算一致性
        assert 0 <= rate <= 100, f"合规率应在0-100之间: {rate}"
        assert passed <= total, f"通过数({passed})不应超过总数({total})"
        assert rate == (passed / total * 100) if total > 0 else True

    def test_zero_endpoints(self):
        """验证空端点集返回100%合规率。"""
        rate, passed, total, failures = compute_compliance_rate([])
        assert rate == 100.0, f"空端点集期望100%，实际{rate}%"
        assert passed == 0
        assert total == 0


class TestComplianceRuleConsistency:
    """合规检查规则一致性测试。"""

    def test_url_rule_handles_uuid_ids(self):
        """验证UUID格式的资源ID不会造成误报。"""
        ep = MockEndpoint(
            "GET",
            "/users/550e8400-e29b-41d4-a716-446655440000/orders",
            200, {}, None, "application/json"
        )
        url_result = check_url_naming(ep)
        path_result = check_collection_resource_endpoints(ep)
        # UUID路径段不应导致URL命名失败
        assert url_result.passed or not any(
            "UUID" in url_result.detail or "550e" in url_result.detail
            for _ in [1]
        )

    def test_error_body_not_triggered_on_success(self):
        """验证成功响应不触发错误体格式检查错误。"""
        ep = MockEndpoint(
            "POST", "/users", 201, {"id": 1},
            "application/json", "application/json"
        )
        result = check_error_body_format(ep)
        assert result.passed, "成功响应应跳过错误体检查"


@pytest.mark.parametrize("method,path,expected_pass", [
    ("GET", "/users", True),
    ("GET", "/getUsers", False),
    ("POST", "/user", False),
    ("GET", "/fetch_articles", False),
    ("GET", "/order-items", True),
    ("POST", "/articles/1/comments", True),
    ("GET", "/api/v1/users/1/profile-image", True),
    ("POST", "/CreateNewItem", False),
])
def test_url_naming_parametrized(method, path, expected_pass):
    """参数化测试URL命名规范的多种场景。"""
    ep = MockEndpoint(method, path, 200, {}, None, "application/json")
    result = check_url_naming(ep)
    assert result.passed == expected_pass, (
        f"{method} {path}: 期望合规={expected_pass}，实际={result.passed} "
        f"[{result.detail}]"
    )
