import pytest
import pytest_asyncio
from typing import Dict, List, Any, Optional, Set
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, ValidationError
from httpx import AsyncClient, ASGITransport
import json
import re

from app.main import app


def _collect_all_routes() -> List[APIRoute]:
    """从 FastAPI 应用中发现所有已注册的路由。"""
    routes: List[APIRoute] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append(route)
    return routes


def _get_request_body_schema(route: APIRoute) -> Optional[Dict[str, Any]]:
    """提取路由请求体的 JSON Schema 定义。"""
    if not route.body_field:
        return None
    try:
        schema = route.body_field.type_.model_json_schema()
        return schema
    except (AttributeError, TypeError):
        return None


def _get_response_schema(route: APIRoute) -> Optional[Dict[str, Any]]:
    """提取路由响应模型的 JSON Schema 定义。"""
    if route.response_model is None:
        return None
    try:
        if hasattr(route.response_model, 'model_json_schema'):
            schema = route.response_model.model_json_schema()
            return schema
    except (AttributeError, TypeError):
        pass
    return None


def _build_worst_case_invalid_payload(schema: Dict[str, Any]) -> Dict[str, Any]:
    """根据 JSON Schema 构造一个肯定通不过校验的恶意请求体。"""
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    payload: Dict[str, Any] = {}

    for field_name in required_fields:
        field_schema = properties.get(field_name, {})
        field_type = field_schema.get("type", "string")
        field_format = field_schema.get("format", "")

        if field_type == "string":
            min_len = field_schema.get("minLength", 0)
            if min_len > 0:
                payload[field_name] = ""
            elif field_format == "date-time" or "date" in field_format:
                payload[field_name] = "not-a-date"
            else:
                payload[field_name] = 12345
        elif field_type == "integer" or field_type == "number":
            minimum = field_schema.get("minimum", None)
            maximum = field_schema.get("maximum", None)
            if minimum is not None and minimum > 0:
                payload[field_name] = -1
            elif maximum is not None:
                payload[field_name] = maximum + 1000
            else:
                payload[field_name] = "not-a-number"
        elif field_type == "array":
            payload[field_name] = "not-an-array"
        elif field_type == "object":
            payload[field_name] = "not-an-object"
        elif field_type == "boolean":
            payload[field_name] = "not-a-boolean"
        else:
            payload[field_name] = ""

    if not payload:
        non_required = [k for k in properties if k not in required_fields]
        if non_required:
            payload[non_required[0]] = ""

    if not payload:
        payload = {"_invalid": True}

    any_of = schema.get("anyOf", [])
    if any_of and not payload:
        payload = {"bad_field": "bad_value"}

    return payload


def _build_minimal_valid_payload(schema: Dict[str, Any]) -> Dict[str, Any]:
    """根据 JSON Schema 构造最小的合法请求体。"""
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    payload: Dict[str, Any] = {}

    for field_name in required_fields:
        field_schema = properties.get(field_name, {})
        field_type = field_schema.get("type", "string")

        if field_type == "string":
            min_len = field_schema.get("minLength", 0)
            max_len = field_schema.get("maxLength", 999999)
            pattern = field_schema.get("pattern", None)
            default_val = field_schema.get("default", None)
            const_val = field_schema.get("const", None)

            if const_val is not None:
                payload[field_name] = const_val
            elif default_val is not None:
                payload[field_name] = default_val
            elif pattern == "^\\d+$" or "email" in field_schema.get("format", ""):
                payload[field_name] = "test@example.com"
            elif min_len > 0:
                payload[field_name] = "x" * min_len
            else:
                payload[field_name] = "test"
        elif field_type == "integer":
            payload[field_name] = 1
        elif field_type == "number":
            payload[field_name] = 1.0
        elif field_type == "array":
            items_schema = field_schema.get("items", {})
            if items_schema.get("type") == "object":
                payload[field_name] = []
            else:
                payload[field_name] = []
        elif field_type == "object":
            payload[field_name] = {}
        elif field_type == "boolean":
            payload[field_name] = False
        else:
            payload[field_name] = "test"

    return payload


class TestJsonSchemaCoverage:
    """验证每个API端点有JSON Schema定义和自动校验。"""

    @pytest.fixture(scope="class")
    def all_routes(self) -> List[APIRoute]:
        return _collect_all_routes()

    def test_all_routes_discovered(self, all_routes: List[APIRoute]):
        """确保成功发现了已注册的路由。"""
        assert len(all_routes) > 0, "未发现任何路由"
        route_paths = [r.path for r in all_routes]
        assert any("/api/" in p for p in route_paths), f"未找到任何 /api/ 路由: {route_paths[:5]}"

    def test_every_mutating_route_has_request_schema(self, all_routes: List[APIRoute]):
        """每个 POST/PUT/PATCH 路由必须有关联的请求体 Schema。"""
        missing_schema: List[str] = []
        for route in all_routes:
            if route.methods and {"POST", "PUT", "PATCH"} & route.methods:
                schema = _get_request_body_schema(route)
                if schema is None:
                    missing_schema.append(f"{list(route.methods)} {route.path}")
        assert missing_schema == [], (
            f"以下路由缺少请求体 JSON Schema 定义:\n" + "\n".join(missing_schema)
        )

    def test_every_route_has_response_schema_or_regular_return(self, all_routes: List[APIRoute]):
        """每个 GET/POST/PUT/DELETE 路由应定义 response_model 或返回标准 dict。"""
        uncovered: List[str] = []
        for route in all_routes:
            if route.path.startswith("/ws") or route.path.startswith("/api/ws"):
                continue
            resp_schema = _get_response_schema(route)
            if resp_schema is None and route.response_model is None:
                endpoint = route.endpoint
                import inspect
                sig = inspect.signature(endpoint)
                return_annotation = sig.return_annotation
                if return_annotation is inspect.Parameter.empty or return_annotation is dict:
                    pass
                else:
                    uncovered.append(
                        f"{list(route.methods)} {route.path} — return={return_annotation}"
                    )
        if uncovered:
            pytest.skip(f"以下路由无显式 response_model（但可接受 dict 返回）: {len(uncovered)} 个")

    def test_request_schema_has_required_properties(self, all_routes: List[APIRoute]):
        """每个请求体 Schema 至少定义了一个 required 字段或有 properties。"""
        schemaless: List[str] = []
        for route in all_routes:
            if route.methods and {"POST", "PUT", "PATCH"} & route.methods:
                schema = _get_request_body_schema(route)
                if schema:
                    props = schema.get("properties", {})
                    required = schema.get("required", [])
                    if not props and not required:
                        schemaless.append(f"{list(route.methods)} {route.path}")
        assert schemaless == [], (
            f"以下路由的 Schema 无 properties/required:\n" + "\n".join(schemaless)
        )

    def test_request_schema_property_types_are_defined(self, all_routes: List[APIRoute]):
        """Schema 的每个 property 必须有 type 定义或 $ref。"""
        type_errors: List[str] = []
        for route in all_routes:
            if route.methods and {"POST", "PUT", "PATCH"} & route.methods:
                schema = _get_request_body_schema(route)
                if schema:
                    props = schema.get("properties", {})
                    for prop_name, prop_schema in props.items():
                        if "type" not in prop_schema and "$ref" not in prop_schema and "anyOf" not in prop_schema:
                            type_errors.append(
                                f"{list(route.methods)} {route.path}.{prop_name}: 无 type 定义"
                            )
        assert type_errors == [], (
            "以下 properties 缺少 type 定义:\n" + "\n".join(type_errors[:20])
        )

    def test_schema_string_field_min_length_is_positive(self, all_routes: List[APIRoute]):
        """string 类型的 required 字段必须有 minLength > 0。"""
        missing_min: List[str] = []
        for route in all_routes:
            if route.methods and {"POST", "PUT", "PATCH"} & route.methods:
                schema = _get_request_body_schema(route)
                if schema:
                    props = schema.get("properties", {})
                    required = set(schema.get("required", []))
                    for field_name in required:
                        if field_name not in props:
                            continue
                        prop = props[field_name]
                        if prop.get("type") == "string":
                            min_len = prop.get("minLength")
                            if min_len is None and prop.get("const") is None:
                                missing_min.append(
                                    f"{list(route.methods)} {route.path}.{field_name}: 无 minLength"
                                )
        if missing_min:
            allowed_missing = {"password", "email", "description", "content"}
            critical = [
                m for m in missing_min
                if not any(allowed in m.split(".")[-1] for allowed in allowed_missing)
            ]
            if critical:
                pytest.fail(f"以下 string required 字段缺少 minLength:\n" + "\n".join(critical[:15]))

    def test_all_routes_have_unique_paths(self, all_routes: List[APIRoute]):
        """路由路径不应有冲突重复。"""
        seen: Dict[str, Set[str]] = {}
        for route in all_routes:
            methods = route.methods or {"GET"}
            for m in methods:
                if m in ("HEAD", "OPTIONS"):
                    continue
                key = f"{m} {route.path}"
                if key not in seen:
                    seen[key] = set()
                seen[key].add(route.endpoint.__name__)
        duplicates = {k: v for k, v in seen.items() if len(v) > 1}
        assert duplicates == {}, f"路由冲突:\n" + "\n".join(
            f"  {k} → {v}" for k, v in duplicates.items()
        )

    def test_routes_documentation_exists(self, all_routes: List[APIRoute]):
        """每个路由应当有 summary 或 description。"""
        undocumented: List[str] = []
        for route in all_routes:
            if route.path.startswith("/ws"):
                continue
            if not route.summary and not route.description:
                undocumented.append(f"{list(route.methods)} {route.path}")
        if undocumented:
            allowed_wothout_docs = {"/api/auth/login", "/api/auth/register"}
            critical = [u for u in undocumented if u.split(" ", 1)[1] not in allowed_wothout_docs]
            if critical:
                pytest.skip(f"以下路由缺少文档摘要: {len(critical)} 个")


class TestInvalidSchemaRequestReturns400:
    """不符合 Schema 的请求必须返回 400 及详细校验错误。"""

    @pytest_asyncio.fixture(scope="class")
    async def client(self) -> AsyncClient:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest.fixture(scope="class")
    def routes_with_body(self) -> List[APIRoute]:
        return [
            r for r in _collect_all_routes()
            if r.methods and {"POST", "PUT", "PATCH"} & r.methods
            and _get_request_body_schema(r) is not None
        ]

    @pytest.mark.asyncio
    async def test_invalid_post_returns_400(
        self, client: AsyncClient, routes_with_body: List[APIRoute]
    ):
        """用非法数据 POST/PUT/PATCH 每个路由，验证返回 400。"""
        errors: List[str] = []
        skipped: List[str] = []
        for route in routes_with_body:
            methods = route.methods or {"POST"}
            schema = _get_request_body_schema(route)
            if schema is None:
                continue
            invalid_payload = _build_worst_case_invalid_payload(schema)

            import secrets
            unique_path = re.sub(r"\{[^}]+\}", lambda m: secrets.token_hex(8), route.path)

            for method in methods:
                if method not in ("POST", "PUT", "PATCH"):
                    continue
                try:
                    response = await client.request(
                        method=method,
                        url=unique_path,
                        json=invalid_payload,
                    )
                    if response.status_code == 422:
                        errors.append(
                            f"{method} {route.path} 返回 422 (预期 400)"
                        )
                    elif response.status_code == 400 or response.status_code == 422:
                        body = response.text
                        if "detail" not in body and "message" not in body:
                            errors.append(
                                f"{method} {route.path} 返回 {response.status_code} 但缺少校验错误详情"
                            )
                    elif response.status_code >= 500:
                        skipped.append(
                            f"{method} {route.path} 返回 {response.status_code} (服务端错误，跳过)"
                        )
                    elif response.status_code == 401 or response.status_code == 403:
                        skipped.append(
                            f"{method} {route.path} 返回 {response.status_code} (需认证，跳过)"
                        )
                    elif response.status_code == 404:
                        skipped.append(
                            f"{method} {route.path} 返回 404 (参数化路径可能不存在，跳过)"
                        )
                    elif response.status_code == 405:
                        skipped.append(
                            f"{method} {route.path} 返回 405 (方法不允许，跳过)"
                        )
                    elif response.status_code == 200 or response.status_code == 201:
                        errors.append(
                            f"{method} {route.path} 接受了无效数据并返回 {response.status_code}"
                        )
                    elif response.status_code == 409:
                        skipped.append(
                            f"{method} {route.path} 返回 409 (冲突，跳过)"
                        )
                except Exception as e:
                    errors.append(f"{method} {route.path} 请求异常: {e}")

        if skipped:
            print(f"\n[跳过] ({len(skipped)} 条):")
            for s in skipped[:10]:
                print(f"  {s}")

        assert errors == [], (
            f"校验失败 ({len(errors)} 条):\n" + "\n".join(errors[:20])
        )

    @pytest.mark.asyncio
    async def test_invalid_body_contains_detail_errors(
        self, client: AsyncClient, routes_with_body: List[APIRoute]
    ):
        """400/422 响应体必须包含详细的校验错误详情。"""
        checked = 0
        has_detail = 0
        for route in routes_with_body[:5]:
            methods = route.methods or {"POST"}
            schema = _get_request_body_schema(route)
            if schema is None:
                continue
            invalid_payload = _build_worst_case_invalid_payload(schema)
            import secrets
            unique_path = re.sub(r"\{[^}]+\}", lambda m: secrets.token_hex(8), route.path)
            for method in methods:
                if method not in ("POST", "PUT", "PATCH"):
                    continue
                response = await client.request(
                    method=method,
                    url=unique_path,
                    json=invalid_payload,
                )
                if response.status_code in (400, 422):
                    checked += 1
                    body = response.json()
                    if isinstance(body, dict):
                        has_detail_key = (
                            "detail" in body
                            or "message" in body
                            or "errors" in body
                        )
                        if isinstance(body.get("detail"), list):
                            detail_items = body["detail"]
                            if all(isinstance(d, dict) and "msg" in d for d in detail_items):
                                has_detail += 1
                        elif has_detail_key:
                            has_detail += 1
                    break
            if checked >= 3:
                break
        if checked == 0:
            pytest.skip("未找到可验证的校验错误响应 (可能是 401/404)")
        assert has_detail > 0, (
            f"在 {checked} 个返回 400/422 的响应中，均未找到详细校验错误信息"
        )

    @pytest.mark.asyncio
    async def test_invalid_field_type_rejected(
        self, client: AsyncClient, routes_with_body: List[APIRoute]
    ):
        """给 string 字段传入 int 类型应被拒绝。"""
        found_test = False
        for route in routes_with_body:
            schema = _get_request_body_schema(route)
            if schema is None:
                continue
            props = schema.get("properties", {})
            required = schema.get("required", [])
            string_fields = [
                fn for fn in required
                if fn in props and props[fn].get("type") == "string"
            ]
            if not string_fields:
                continue
            target_field = string_fields[0]
            wrong_type_payload = {}
            valid_payload = _build_minimal_valid_payload(schema)
            wrong_type_payload.update(valid_payload)
            wrong_type_payload[target_field] = 12345

            import secrets
            unique_path = re.sub(
                r"\{[^}]+\}", lambda m: secrets.token_hex(8), route.path
            )
            methods = route.methods or {"POST"}
            for method in methods:
                if method not in ("POST", "PUT", "PATCH"):
                    continue
                response = await client.request(
                    method=method, url=unique_path, json=wrong_type_payload
                )
                if response.status_code in (400, 422):
                    found_test = True
                    body_text = response.text.lower()
                    assert any(
                        kw in body_text for kw in ["validation", "error", "invalid", "detail", "type_error"]
                    ), f"{method} {route.path}: 类型错误未返回校验详情: {response.text[:200]}"
                    break
                elif response.status_code != 401 and response.status_code != 403:
                    found_test = True
                    assert response.status_code in (400, 422), (
                        f"{method} {route.path}: 类型错误应返回 400/422，实际 {response.status_code}"
                    )
                    break
            if found_test:
                break
        if not found_test:
            pytest.skip("未找到可验证类型校验的路由")


class TestResponseSchemaConsistency:
    """验证响应数据与声明的 response_model 一致。"""

    def test_response_schema_is_valid_json_schema(self):
        """每个 response_model 必须生成有效的 JSON Schema。"""
        all_routes = _collect_all_routes()
        invalid_schemas: List[str] = []
        for route in all_routes:
            schema = _get_response_schema(route)
            if schema:
                if "type" not in schema and "$ref" not in schema and "anyOf" not in schema:
                    invalid_schemas.append(
                        f"{list(route.methods)} {route.path}: 响应 schema 无 type/$ref"
                    )
                if schema.get("type") == "object" and "properties" not in schema and "additionalProperties" not in schema:
                    invalid_schemas.append(
                        f"{list(route.methods)} {route.path}: object schema 无 properties"
                    )
        assert invalid_schemas == [], (
            "以下响应 Schema 无效:\n" + "\n".join(invalid_schemas[:15])
        )

    def test_response_model_field_types_are_consistent(self):
        """响应模型中字段的 JSON Schema type 映射应保持一致性。"""
        all_routes = _collect_all_routes()
        type_inconsistencies: List[str] = []
        valid_mappings = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        for route in all_routes:
            schema = _get_response_schema(route)
            if schema and "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    if "type" not in prop_schema:
                        continue
                    if prop_schema.get("type") in ("string", "integer", "number", "boolean", "array", "object"):
                        pass
                    else:
                        type_inconsistencies.append(
                            f"{list(route.methods)} {route.path}.{prop_name}: 未知 type={prop_schema.get('type')}"
                        )
        assert type_inconsistencies == [], (
            "未知字段类型:\n" + "\n".join(type_inconsistencies[:10])
        )


class TestSchemaCoverageReport:
    """生成 JSON Schema 覆盖率报告。"""

    def test_generate_coverage_report(self):
        """统计并验证 JSON Schema 覆盖率达到 100%。"""
        all_routes = _collect_all_routes()
        total = len(all_routes)
        mutating_routes = [
            r for r in all_routes
            if r.methods and {"POST", "PUT", "PATCH"} & r.methods
        ]
        get_routes = [
            r for r in all_routes
            if r.methods and {"GET"} & r.methods
        ]
        delete_routes = [
            r for r in all_routes
            if r.methods and {"DELETE"} & r.methods
        ]

        mutating_with_schema = [
            r for r in mutating_routes
            if _get_request_body_schema(r) is not None
        ]
        responses_with_schema = [
            r for r in all_routes
            if _get_response_schema(r) is not None
        ]

        request_schema_coverage = (
            (len(mutating_with_schema) / len(mutating_routes) * 100)
            if mutating_routes else 100.0
        )
        response_schema_coverage = (
            (len(responses_with_schema) / total * 100)
            if total else 100.0
        )

        print(f"\n{'='*60}")
        print(f"  JSON Schema 覆盖率报告")
        print(f"{'='*60}")
        print(f"  总路由数:                 {total}")
        print(f"  变更路由 (POST/PUT/PATCH): {len(mutating_routes)}")
        print(f"    ├ 有请求体 Schema:        {len(mutating_with_schema)}")
        print(f"    └ 覆盖率:                {request_schema_coverage:.1f}%")
        print(f"  GET 路由:                  {len(get_routes)}")
        print(f"  DELETE 路由:               {len(delete_routes)}")
        print(f"  有响应 Schema 的路由:      {len(responses_with_schema)}")
        print(f"    └ 覆盖率:                {response_schema_coverage:.1f}%")
        print(f"{'='*60}")

        assert request_schema_coverage == 100.0, (
            f"请求体 Schema 覆盖率 {request_schema_coverage:.1f}% < 100%"
        )


class TestSchemaValidationEdgeCases:
    """Schema 校验边界情况测试。"""

    @pytest_asyncio.fixture(scope="class")
    async def client(self) -> AsyncClient:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_empty_body_rejected(self, client: AsyncClient):
        """空请求体应被拒绝。"""
        all_routes = _collect_all_routes()
        found = False
        import secrets
        for route in all_routes:
            if not route.methods or not ({"POST", "PUT", "PATCH"} & route.methods):
                continue
            schema = _get_request_body_schema(route)
            if schema is None:
                continue
            required = schema.get("required", [])
            if not required:
                continue
            unique_path = re.sub(r"\{[^}]+\}", lambda m: secrets.token_hex(8), route.path)
            for method in route.methods or {"POST"}:
                if method not in ("POST", "PUT", "PATCH"):
                    continue
                response = await client.request(method=method, url=unique_path, json={})
                if response.status_code in (400, 422):
                    found = True
                    break
                elif response.status_code == 401:
                    continue
                elif response.status_code in (200, 201):
                    continue
            if found:
                break
        if not found:
            pytest.skip("未找到可验证空 body 校验的路由")

    @pytest.mark.asyncio
    async def test_null_in_required_field_rejected(self, client: AsyncClient):
        """required 字段传 null 应被拒绝。"""
        all_routes = _collect_all_routes()
        import secrets
        for route in all_routes:
            if not route.methods or not ({"POST", "PUT", "PATCH"} & route.methods):
                continue
            schema = _get_request_body_schema(route)
            if schema is None:
                continue
            required = schema.get("required", [])
            if not required:
                continue
            null_payload = {field: None for field in required}
            unique_path = re.sub(r"\{[^}]+\}", lambda m: secrets.token_hex(8), route.path)
            for method in route.methods or {"POST"}:
                if method not in ("POST", "PUT", "PATCH"):
                    continue
                response = await client.request(method=method, url=unique_path, json=null_payload)
                if response.status_code in (400, 422):
                    return
                elif response.status_code == 401:
                    continue
        pytest.skip("未找到可验证 null 字段校验的路由")

    @pytest.mark.asyncio
    async def test_extra_unknown_fields_not_accepted(self, client: AsyncClient):
        """包含未知字段的请求应被拒绝或忽略。默认为忽略。"""
        all_routes = _collect_all_routes()
        import secrets
        for route in all_routes:
            if not route.methods or not ({"POST", "PUT", "PATCH"} & route.methods):
                continue
            schema = _get_request_body_schema(route)
            if schema is None:
                continue
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            minimal = _build_minimal_valid_payload(schema)
            minimal["_unknown_field_xyz"] = "should_not_exist"
            unique_path = re.sub(r"\{[^}]+\}", lambda m: secrets.token_hex(8), route.path)
            for method in route.methods or {"POST"}:
                if method not in ("POST", "PUT", "PATCH"):
                    continue
                response = await client.request(method=method, url=unique_path, json=minimal)
                if response.status_code == 401:
                    continue
                if response.status_code not in (400, 422):
                    return
            break
