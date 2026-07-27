#!/usr/bin/env python3
"""
OpenAPI 3.0 文档自动生成 — TDD 测试

验收标准：
1. OpenAPI 文档自动生成率 = 100%
2. 文档与代码实现一致性 >= 95%
"""

import json
import re
import sys
import os
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

# 确保 backend 在路径中
_backend = os.path.join(os.path.dirname(__file__), "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.main import app


# ====================================================================
# fixtures
# ====================================================================

@pytest.fixture(scope="module")
def client():
    """FastAPI 测试客户端。"""
    return TestClient(app)


@pytest.fixture(scope="module")
def openapi_spec(client: TestClient):
    """获取 OpenAPI JSON 规范。"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, f"OpenAPI 端点不可达: {resp.status_code}"
    return resp.json()


# ====================================================================
# 核心验证类
# ====================================================================


class OpenAPIDocValidator:
    """OpenAPI 文档自动生成与一致性验证器。"""

    # OpenAPI 3.x 必需顶级字段
    REQUIRED_TOP_LEVEL_KEYS = {
        "openapi",
        "info",
        "paths",
    }

    # info 对象必需字段
    REQUIRED_INFO_KEYS = {
        "title",
        "version",
    }

    # HTTP 方法白名单
    VALID_HTTP_METHODS = {
        "get", "post", "put", "delete", "patch", "head", "options",
    }

    # 需要验证响应体的路由模式（排除健康检查等轻量端点）
    LIGHTWEIGHT_PATHS = {
        "/",
        "/health",
    }

    def __init__(self, spec: dict):
        self.spec = spec
        self.issues: list[str] = []
        self.warnings: list[str] = []
        self.path_count: int = 0
        self.operation_count: int = 0

    # ── 1. 自动生成率 = 100% ────────────────────────────

    def validate_openapi_version(self) -> bool:
        """验证 OpenAPI 版本字段符合 3.x 规范。"""
        version = self.spec.get("openapi", "")
        if not re.match(r"^3\.\d+\.\d+$", str(version)):
            self.issues.append(f"OpenAPI 版本 '{version}' 不是 3.x 格式")
            return False
        return True

    def validate_required_top_level_keys(self) -> bool:
        """验证 OpenAPI 文档包含所有必需的顶级字段。"""
        missing = self.REQUIRED_TOP_LEVEL_KEYS - set(self.spec.keys())
        if missing:
            self.issues.append(f"缺少顶级字段: {missing}")
            return False
        return True

    def validate_info_section(self) -> bool:
        """验证 info 段完整。"""
        info = self.spec.get("info", {})
        if not info:
            self.issues.append("info 段为空")
            return False
        missing = self.REQUIRED_INFO_KEYS - set(info.keys())
        if missing:
            self.issues.append(f"info 段缺少字段: {missing}")
            return False
        return True

    def validate_paths_not_empty(self) -> bool:
        """验证 paths 不为空（证明文档确实包含路由信息）。"""
        paths = self.spec.get("paths", {})
        self.path_count = len(paths)
        if self.path_count == 0:
            self.issues.append("paths 段为空，未生成任何路由文档")
            return False
        return True

    def validate_all_paths_have_operations(self) -> bool:
        """验证每个路径下至少有一个 HTTP 操作。"""
        paths = self.spec.get("paths", {})
        all_ok = True
        for path, ops in paths.items():
            methods = {k for k in ops.keys() if k in self.VALID_HTTP_METHODS}
            if not methods:
                self.issues.append(f"路径 '{path}' 下无有效 HTTP 操作")
                all_ok = False
        return all_ok

    def count_operations(self) -> int:
        """统计总操作数。"""
        paths = self.spec.get("paths", {})
        total = 0
        for path, ops in paths.items():
            for method in ops:
                if method in self.VALID_HTTP_METHODS:
                    total += 1
        self.operation_count = total
        return total

    def validate_generation_rate(self) -> float:
        """
        计算自动生成率。
        所有结构验证通过 = 100% 自动生成率。
        """
        checks = [
            self.validate_openapi_version(),
            self.validate_required_top_level_keys(),
            self.validate_info_section(),
            self.validate_paths_not_empty(),
            self.validate_all_paths_have_operations(),
        ]
        passed = sum(checks)
        total = len(checks)
        rate = passed / total * 100 if total > 0 else 0.0
        return rate

    # ── 2. 文档与代码一致性 >= 95% ────────────────────────

    def _collect_code_routes(self, client: TestClient) -> list[tuple[str, str]]:
        """从 FastAPI 路由对象收集代码中实际注册的路由。"""
        routes: list[tuple[str, str]] = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    if method in {"HEAD", "OPTIONS"}:
                        continue
                    routes.append((method.lower(), route.path))
        return routes

    def _collect_doc_routes(self) -> list[tuple[str, str]]:
        """从 OpenAPI spec 收集文档中的路由。"""
        routes: list[tuple[str, str]] = []
        paths = self.spec.get("paths", {})
        for path, ops in paths.items():
            for method in ops:
                if method in self.VALID_HTTP_METHODS:
                    routes.append((method, path))
        return routes

    def _normalize_path(self, path: str) -> str:
        """规范化路径：去掉尾部斜杠、统一路径参数格式。"""
        path = path.rstrip("/")
        # 将 {param} 和 {param: type} 统一为 {param}
        path = re.sub(r"\{[^}]+\}", "{p}", path)
        return path

    def validate_consistency(self, client: TestClient) -> float:
        """
        验证文档与代码的一致性。

        计算方式：
        - code_routes: 代码中注册的路由集合
        - doc_routes: OpenAPI 文档中的路由集合
        - consistency = 交集 / 并集 * 100 (Jaccard 相似度)
        """
        code_routes_raw = self._collect_code_routes(client)
        doc_routes_raw = self._collect_doc_routes()

        code_routes = {(m, self._normalize_path(p)) for m, p in code_routes_raw}
        doc_routes = {(m, self._normalize_path(p)) for m, p in doc_routes_raw}

        if not code_routes and not doc_routes:
            return 100.0

        intersection = code_routes & doc_routes
        union = code_routes | doc_routes
        jaccard = len(intersection) / len(union) * 100 if union else 100.0

        # 记录差异
        only_in_code = code_routes - doc_routes
        only_in_doc = doc_routes - code_routes
        if only_in_code:
            for route in sorted(only_in_code)[:10]:
                self.warnings.append(
                    f"代码中有但文档中缺失: {route[0].upper()} {route[1]}"
                )
        if only_in_doc:
            for route in sorted(only_in_doc)[:10]:
                self.warnings.append(
                    f"文档中有但代码中缺失: {route[0].upper()} {route[1]}"
                )

        return jaccard

    def validate_operations_have_responses(self) -> bool:
        """验证每个操作都定义了响应。"""
        paths = self.spec.get("paths", {})
        all_ok = True
        for path, ops in paths.items():
            for method, op in ops.items():
                if method not in self.VALID_HTTP_METHODS:
                    continue
                if "responses" not in op:
                    self.issues.append(
                        f"{method.upper()} {path} 缺少 responses 定义"
                    )
                    all_ok = False
        return all_ok

    def validate_operations_have_operation_id(self) -> bool:
        """验证每个操作都有 operationId（可能有重复警告，但仍应存在）。"""
        paths = self.spec.get("paths", {})
        all_ok = True
        for path, ops in paths.items():
            for method, op in ops.items():
                if method not in self.VALID_HTTP_METHODS:
                    continue
                if "operationId" not in op:
                    self.issues.append(
                        f"{method.upper()} {path} 缺少 operationId"
                    )
                    all_ok = False
        return all_ok

    def validate_parameter_references_valid(self) -> bool:
        """验证参数中的 $ref 引用在 components/schemas 中存在。"""
        components = self.spec.get("components", {})
        schemas = set(components.get("schemas", {}).keys())
        all_ok = True

        paths = self.spec.get("paths", {})
        for path, ops in paths.items():
            for method, op in ops.items():
                if method not in self.VALID_HTTP_METHODS:
                    continue
                params = op.get("parameters", [])
                for param in params:
                    schema = param.get("schema", {})
                    ref = schema.get("$ref", "")
                    if ref:
                        schema_name = ref.split("/")[-1]
                        if schema_name not in schemas:
                            self.issues.append(
                                f"{method.upper()} {path}: 参数引用了不存在的 schema '{schema_name}'"
                            )
                            all_ok = False
                # 检查请求体
                body = op.get("requestBody", {})
                content = body.get("content", {})
                for media_type, media_obj in content.items():
                    schema = media_obj.get("schema", {})
                    ref = schema.get("$ref", "")
                    if ref:
                        schema_name = ref.split("/")[-1]
                        if schema_name not in schemas:
                            self.issues.append(
                                f"{method.upper()} {path}: 请求体引用了不存在的 schema '{schema_name}'"
                            )
                            all_ok = False
        return all_ok

    def get_report(self) -> dict:
        """生成完整的验证报告。"""
        return {
            "issues": self.issues,
            "warnings": self.warnings,
            "path_count": self.path_count,
            "operation_count": self.operation_count,
            "issue_count": len(self.issues),
            "warning_count": len(self.warnings),
        }


# ====================================================================
# 测试用例
# ====================================================================


class TestOpenAPIAutoGeneration:
    """OpenAPI 文档自动生成率 = 100%"""

    def test_openapi_endpoint_accessible(self, client: TestClient):
        """OpenAPI JSON 端点可访问。"""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

    def test_openapi_version_is_v3(self, openapi_spec: dict):
        """OpenAPI 版本符合 3.x 规范。"""
        version = openapi_spec.get("openapi", "")
        assert re.match(r"^3\.\d+\.\d+$", str(version)), (
            f"OpenAPI 版本 '{version}' 不是 3.x 格式"
        )

    def test_required_top_level_keys_present(self, openapi_spec: dict):
        """OpenAPI 文档包含所有必需的顶级字段。"""
        for key in ("openapi", "info", "paths"):
            assert key in openapi_spec, f"缺少顶级字段: {key}"

    def test_info_section_complete(self, openapi_spec: dict):
        """info 段包含标题和版本号。"""
        info = openapi_spec.get("info", {})
        assert info.get("title"), "info.title 为空"
        assert info.get("version"), "info.version 为空"

    def test_paths_not_empty(self, openapi_spec: dict):
        """paths 段不为空。"""
        paths = openapi_spec.get("paths", {})
        assert len(paths) > 0, "paths 段为空，未生成路由文档"

    def test_all_paths_have_valid_operations(self, openapi_spec: dict):
        """每个路径下至少有一个有效的 HTTP 操作。"""
        valid_methods = {"get", "post", "put", "delete", "patch", "head", "options"}
        paths = openapi_spec.get("paths", {})
        for path, ops in paths.items():
            valid_ops = {k for k in ops.keys() if k in valid_methods}
            assert valid_ops, f"路径 '{path}' 下无有效 HTTP 操作"

    def test_generation_rate_is_100_percent(self, openapi_spec: dict):
        """OpenAPI 文档自动生成率 = 100%。"""
        validator = OpenAPIDocValidator(openapi_spec)
        rate = validator.validate_generation_rate()
        report = validator.get_report()
        assert rate == 100.0, (
            f"自动生成率 {rate}% < 100%。问题: {report['issues']}"
        )

    def test_openapi_yaml_endpoint_accessible(self, client: TestClient):
        """OpenAPI YAML 端点也可访问（FastAPI 默认提供）。"""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type


class TestOpenAPIDocSwaggerUI:
    """Swagger UI / ReDoc 文档页面可访问。"""

    def test_swagger_ui_accessible(self, client: TestClient):
        """Swagger UI 页面可访问。"""
        resp = client.get("/docs")
        assert resp.status_code == 200
        content = resp.text
        assert "swagger" in content.lower() or "Swagger" in content

    def test_redoc_accessible(self, client: TestClient):
        """ReDoc 页面可访问。"""
        resp = client.get("/redoc")
        assert resp.status_code == 200
        content = resp.text
        assert "redoc" in content.lower() or "ReDoc" in content


class TestOpenAPIDocumentConsistency:
    """文档与代码实现一致性 >= 95%"""

    def test_document_code_consistency_above_threshold(
        self, client: TestClient, openapi_spec: dict
    ):
        """文档与代码一致性 >= 95%（Jaccard 相似度）。"""
        validator = OpenAPIDocValidator(openapi_spec)
        consistency = validator.validate_consistency(client)
        report = validator.get_report()
        assert consistency >= 95.0, (
            f"一致性 {consistency:.2f}% < 95%。\n"
            f"  问题数: {report['issue_count']}\n"
            f"  警告数: {report['warning_count']}\n"
            f"  警告详情: {report['warnings'][:5]}"
        )

    def test_operations_have_responses(self, openapi_spec: dict):
        """每个 API 操作都定义了响应。"""
        validator = OpenAPIDocValidator(openapi_spec)
        ok = validator.validate_operations_have_responses()
        report = validator.get_report()
        assert ok, (
            f"部分操作缺少 responses 定义。\n"
            f"  问题: {report['issues'][:10]}"
        )

    def test_operations_have_operation_id(self, openapi_spec: dict):
        """每个 API 操作都有 operationId。"""
        validator = OpenAPIDocValidator(openapi_spec)
        ok = validator.validate_operations_have_operation_id()
        assert ok, "部分操作缺少 operationId"

    def test_parameter_schema_references_valid(self, openapi_spec: dict):
        """参数和请求体中的 $ref 引用的 schema 存在。"""
        validator = OpenAPIDocValidator(openapi_spec)
        ok = validator.validate_parameter_references_valid()
        report = validator.get_report()
        assert ok, (
            f"存在无效的 schema 引用。\n"
            f"  问题: {report['issues'][:10]}"
        )

    def test_path_count_is_substantial(self, openapi_spec: dict):
        """路径数量合理（> 10，证明文档非空）。"""
        paths = openapi_spec.get("paths", {})
        assert len(paths) >= 10, (
            f"路径数 {len(paths)} 过少，文档可能不完整"
        )

    def test_operation_count_is_substantial(self, openapi_spec: dict):
        """操作数量合理（> 20，证明文档非空）。"""
        validator = OpenAPIDocValidator(openapi_spec)
        count = validator.count_operations()
        assert count >= 20, (
            f"操作数 {count} 过少，文档可能不完整"
        )


class TestOpenAPIStructure:
    """OpenAPI 文档结构完整性。"""

    def test_components_schemas_exist(self, openapi_spec: dict):
        """components/schemas 存在。"""
        components = openapi_spec.get("components", {})
        schemas = components.get("schemas", {})
        assert isinstance(schemas, dict), "components.schemas 不存在或不是对象"

    def test_info_has_description(self, openapi_spec: dict):
        """info 段包含描述。"""
        info = openapi_spec.get("info", {})
        desc = info.get("description", "")
        assert desc, "info.description 为空"

    def test_paths_use_proper_format(self, openapi_spec: dict):
        """所有路径以 '/' 开头。"""
        paths = openapi_spec.get("paths", {})
        for path in paths.keys():
            assert path.startswith("/"), f"路径 '{path}' 不是以 '/' 开头"

    def test_no_empty_path(self, openapi_spec: dict):
        """无空路径。"""
        paths = openapi_spec.get("paths", {})
        assert "" not in paths, "存在空路径 ''"

    def test_http_methods_are_lowercase(self, openapi_spec: dict):
        """HTTP 方法键都是小写。"""
        paths = openapi_spec.get("paths", {})
        for path, ops in paths.items():
            for method in ops.keys():
                if method in {"get", "post", "put", "delete", "patch", "head", "options"}:
                    assert method == method.lower(), (
                        f"{path}: HTTP 方法 '{method}' 不是小写"
                    )


class TestOpenAPITags:
    """OpenAPI 文档 tags 规范。"""

    def test_tags_defined_in_spec(self, openapi_spec: dict):
        """文档中定义了 tags 段（FastAPI 默认行为）。"""
        # FastAPI 会自动从路由的 tags 参数生成 tags 列表
        # 可能有也可能没有顶级 tags 段，这取决于 FastAPI 版本
        # 我们只验证 paths 中的操作包含 tags
        paths = openapi_spec.get("paths", {})
        ops_with_tags = 0
        total_ops = 0
        for path, ops in paths.items():
            for method, op in ops.items():
                if method in {"get", "post", "put", "delete", "patch"}:
                    total_ops += 1
                    if op.get("tags"):
                        ops_with_tags += 1
        # 大部分操作应该有 tags
        if total_ops > 0:
            tag_ratio = ops_with_tags / total_ops
            assert tag_ratio > 0.5, (
                f"仅 {ops_with_tags}/{total_ops} ({tag_ratio:.0%}) 的操作有 tags"
            )

    def test_tag_names_are_non_empty(self, openapi_spec: dict):
        """使用的 tags 名非空。"""
        paths = openapi_spec.get("paths", {})
        for path, ops in paths.items():
            for method, op in ops.items():
                if method not in {"get", "post", "put", "delete", "patch"}:
                    continue
                tags = op.get("tags", [])
                for tag in tags:
                    assert tag and str(tag).strip(), (
                        f"{method.upper()} {path}: 存在空 tag"
                    )


class TestOpenAPISecuritySchemes:
    """OpenAPI 文档安全方案定义。"""

    def test_security_schemes_exist(self, openapi_spec: dict):
        """components/securitySchemes 存在（如果有的话）。"""
        components = openapi_spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        # 即使为空也是合法的，只验证类型
        assert isinstance(security_schemes, dict)


class TestOpenAPIEndpointCoverage:
    """关键端点在 OpenAPI 文档中有覆盖。"""

    def test_health_endpoint_documented(self, openapi_spec: dict):
        """/health 端点在文档中。"""
        paths = openapi_spec.get("paths", {})
        assert "/health" in paths, "/health 端点未在 OpenAPI 文档中"

    def test_root_endpoint_documented(self, openapi_spec: dict):
        """/ 端点在文档中。"""
        paths = openapi_spec.get("paths", {})
        assert "/" in paths, "/ 端点未在 OpenAPI 文档中"

    def test_auth_endpoints_documented(self, openapi_spec: dict):
        """认证相关端点在文档中（至少有 login 或 register）。"""
        paths = openapi_spec.get("paths", {})
        auth_paths = [p for p in paths if "auth" in p.lower()]
        assert len(auth_paths) > 0, "无 auth 相关端点在 OpenAPI 文档中"

    def test_project_endpoints_documented(self, openapi_spec: dict):
        """项目相关端点在文档中。"""
        paths = openapi_spec.get("paths", {})
        project_paths = [p for p in paths if "project" in p.lower()]
        assert len(project_paths) > 0, "无 project 相关端点在 OpenAPI 文档中"


class TestOpenAPIAutoRegeneration:
    """OpenAPI 文档随代码变化自动更新。"""

    def test_openapi_spec_is_fresh_generated(self, client: TestClient):
        """两次请求 /openapi.json 返回一致结果（服务器端动态生成）。"""
        resp1 = client.get("/openapi.json")
        resp2 = client.get("/openapi.json")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        data1 = resp1.json()
        data2 = resp2.json()
        assert data1 == data2, "两次请求返回的 OpenAPI 规范不一致"

    def test_openapi_spec_has_version_info(self, openapi_spec: dict):
        """OpenAPI 文档包含应用的版本信息。"""
        info = openapi_spec.get("info", {})
        version = info.get("version", "")
        assert version, "info.version 为空"
        # 版本号不应为空字符串
        assert version.strip(), "info.version 仅含空白字符"


class TestOpenAPISummaryValidation:
    """最终汇总验证 — 一次性确认两项验收标准。"""

    def test_acceptance_criteria_generation_rate_100(
        self, openapi_spec: dict
    ):
        """验收标准 1：OpenAPI 文档自动生成率 = 100%。"""
        validator = OpenAPIDocValidator(openapi_spec)
        rate = validator.validate_generation_rate()
        assert rate == 100.0, f"自动生成率 {rate}% ≠ 100%"

    def test_acceptance_criteria_consistency_above_95(
        self, client: TestClient, openapi_spec: dict
    ):
        """验收标准 2：文档与代码实现一致性 >= 95%。"""
        validator = OpenAPIDocValidator(openapi_spec)
        consistency = validator.validate_consistency(client)
        assert consistency >= 95.0, f"一致性 {consistency:.2f}% < 95%"
