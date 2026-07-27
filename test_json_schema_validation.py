import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple, Type
import pytest
from pydantic import BaseModel, Field, ValidationError
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError


# ============================================================================
# 模拟后端验证中间件
# ============================================================================

app = FastAPI(title="JSON Schema 校验测试")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """验证失败时返回 422 及详细校验错误"""
    errors = exc.errors()
    serializable_errors = []
    for e in errors:
        se: Dict[str, Any] = {
            "type": e.get("type"),
            "loc": list(e.get("loc", [])),
            "msg": e.get("msg"),
            "input": e.get("input"),
        }
        if "ctx" in e and e["ctx"]:
            se["ctx"] = {k: str(v) for k, v in e["ctx"].items()}
        serializable_errors.append(se)
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求数据校验失败",
            "details": {"errors": serializable_errors},
        },
    )


# ============================================================================
# Schema 模块导入与注册
# ============================================================================

SCHEMA_MODULES: List[Path] = [
    Path("backend/app/schemas/auth.py"),
    Path("backend/app/schemas/user.py"),
    Path("backend/app/schemas/project.py"),
    Path("backend/app/schemas/board.py"),
    Path("backend/app/schemas/task.py"),
    Path("backend/app/schemas/comment.py"),
    Path("backend/app/schemas/attachment.py"),
    Path("backend/app/schemas/dependency.py"),
    Path("backend/app/schemas/workload.py"),
    Path("backend/app/schemas/requirement.py"),
    Path("backend/app/schemas/agent.py"),
    Path("backend/app/schemas/hermes_skill.py"),
    Path("backend/app/schemas/agent_execution_log.py"),
    Path("backend/app/schemas/acceptance.py"),
    Path("backend/app/schemas/notification.py"),
    Path("backend/app/schemas/group.py"),
    Path("backend/app/schemas/repo.py"),
    Path("backend/app/schemas/heartbeat.py"),
    Path("backend/app/schemas/project_srs.py"),
    Path("backend/app/schemas/scheduling.py"),
]


def _load_schema_classes(module_path: Path) -> List[Tuple[str, Type[BaseModel]]]:
    """从 schema 模块文件中提取所有 Pydantic BaseModel 子类"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        f"schema_mod_{module_path.name}", module_path
    )
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return []
    result = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, BaseModel)
            and obj is not BaseModel
        ):
            result.append((name, obj))
    return result


def _get_all_schema_classes() -> List[Tuple[str, str, Type[BaseModel]]]:
    """获取所有 schema 模块中的 BaseModel 类"""
    project_root = Path(__file__).resolve().parent
    all_classes: List[Tuple[str, str, Type[BaseModel]]] = []
    for mod_path in SCHEMA_MODULES:
        full_path = project_root / mod_path
        if not full_path.exists():
            continue
        classes = _load_schema_classes(mod_path)
        for cls_name, cls in classes:
            all_classes.append((mod_path.name, cls_name, cls))
    return all_classes


# 识别哪些 Schema 类用于请求体（Create/Update/Request/Submit/Answer 结尾的类）
BODY_SCHEMA_SUFFIXES = ("Create", "Update", "Request", "Submit", "Answer")


def _is_body_schema(cls_name: str) -> bool:
    return any(cls_name.endswith(suffix) for suffix in BODY_SCHEMA_SUFFIXES)


def _safe_route_name(cls_name: str) -> str:
    """将 Schema 类名转为可用的路由路径名"""
    s = re.sub(r"(?<!^)(?=[A-Z])", "-", cls_name).lower()
    return s


_all_schema_classes = _get_all_schema_classes()
_body_schemas: List[Tuple[str, str, Type[BaseModel]]] = [
    (mod, name, cls) for mod, name, cls in _all_schema_classes if _is_body_schema(name)
]
_non_body_schemas: List[Tuple[str, str, Type[BaseModel]]] = [
    (mod, name, cls) for mod, name, cls in _all_schema_classes if not _is_body_schema(name)
]


for mod_name, cls_name, cls in _body_schemas:
    route_path = f"/test-schema/{_safe_route_name(cls_name)}"

    @app.post(route_path, status_code=201)
    def _make_handler(model=cls):
        async def handler(data: model):
            return {
                "code": 0,
                "message": "校验通过",
                "data": data.model_dump(),
            }
        return handler


client = TestClient(app)


# ============================================================================
# 测试类 1：JSON Schema 覆盖率 = 100%
# ============================================================================

class TestJSONSchemaCoverage:
    """JSON Schema 覆盖率 = 100%"""

    def test_all_schema_modules_exist(self):
        """所有 schema 模块文件必须存在"""
        project_root = Path(__file__).resolve().parent
        for mod_path in SCHEMA_MODULES:
            full_path = project_root / mod_path
            assert full_path.exists(), f"Schema 模块不存在: {mod_path}"

    def test_all_schema_classes_have_json_schema(self):
        """每个 Pydantic Schema 类都能生成 JSON Schema"""
        all_classes = _get_all_schema_classes()
        assert len(all_classes) > 0, "未找到任何 Schema 类"
        for mod_name, cls_name, cls in all_classes:
            schema = cls.model_json_schema()
            assert isinstance(schema, dict), f"{mod_name}:{cls_name} 无法生成 JSON Schema"
            assert (
                "$defs" in schema or "properties" in schema or "type" in schema
            ), f"{mod_name}:{cls_name} 的 JSON Schema 结构不完整"

    def test_coverage_is_100_percent(self):
        """JSON Schema 覆盖率必须达到 100%"""
        all_classes = _get_all_schema_classes()
        total = len(all_classes)
        success = 0
        for mod_name, cls_name, cls in all_classes:
            try:
                schema = cls.model_json_schema()
                assert isinstance(schema, dict)
                success += 1
            except Exception:
                pass
        assert success == total, (
            f"覆盖率不足 100%: {success}/{total} 个 Schema 能生成 JSON Schema"
        )

    def test_body_schemas_discovered(self):
        """所有 Create/Update/Request 类都能被识别为请求体 Schema"""
        assert len(_body_schemas) > 0, "未找到任何请求体 Schema"
        names = [cls_name for _, cls_name, _ in _body_schemas]
        expected_minimal = {"LoginRequest", "RegisterRequest", "TaskCreate", "ProjectCreate"}
        found = set(names)
        for expected in expected_minimal:
            assert expected in found, f"关键 Schema '{expected}' 未被发现"

    def test_response_schemas_discovered(self):
        """Response 结尾的类也能生成 JSON Schema"""
        assert len(_non_body_schemas) > 0, "未找到任何响应 Schema"
        for mod_name, cls_name, cls in _non_body_schemas:
            schema = cls.model_json_schema()
            assert isinstance(schema, dict), f"{cls_name} 无法生成 JSON Schema"

    def test_schema_has_properties(self):
        """每个 Schema 的 JSON Schema 都包含 properties 字段"""
        all_classes = _get_all_schema_classes()
        for mod_name, cls_name, cls in all_classes:
            schema = cls.model_json_schema()
            if cls.model_fields:
                assert "properties" in schema, (
                    f"{mod_name}:{cls_name} 有字段但 JSON Schema 缺少 properties"
                )

    def test_schema_fields_match_model_fields(self):
        """JSON Schema 中的字段与 Pydantic 模型字段一致"""
        all_classes = _get_all_schema_classes()
        for mod_name, cls_name, cls in all_classes:
            pydantic_fields = set(cls.model_fields.keys())
            schema = cls.model_json_schema()
            if "properties" in schema:
                schema_fields = set(schema["properties"].keys())
                assert pydantic_fields == schema_fields, (
                    f"{mod_name}:{cls_name} 字段不匹配: "
                    f"Pydantic={pydantic_fields}, Schema={schema_fields}"
                )


# ============================================================================
# 测试类 2：不符合 Schema 的请求返回 422 及详细校验错误
# ============================================================================

class TestRequestValidation:
    """不符合 Schema 的请求返回 422 及详细校验错误"""

    # --- 认证相关 ---

    def test_login_missing_password_returns_422(self):
        """登录缺少 password 字段返回 422"""
        resp = client.post("/test-schema/login-request", json={"username": "admin"})
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert "errors" in body["details"]
        errors = body["details"]["errors"]
        assert any("password" in str(e.get("loc", [])) for e in errors)

    def test_login_password_too_short_returns_422(self):
        """登录密码长度不足返回 422"""
        resp = client.post("/test-schema/login-request", json={
            "username": "admin", "password": "123"
        })
        assert resp.status_code == 422

    def test_register_missing_fields_returns_422(self):
        """注册缺少必填字段返回 422"""
        resp = client.post("/test-schema/register-request", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert "errors" in body["details"]

    def test_register_username_too_short_returns_422(self):
        """注册用户名长度不足返回 422"""
        resp = client.post("/test-schema/register-request", json={
            "username": "ab",
            "email": "a@b.com",
            "password": "Ab123456",
            "confirm_password": "Ab123456",
        })
        assert resp.status_code == 422

    def test_register_password_no_uppercase_returns_422(self):
        """注册密码缺少大写字母返回 422"""
        resp = client.post("/test-schema/register-request", json={
            "username": "testuser",
            "email": "a@b.com",
            "password": "abc123456",
            "confirm_password": "abc123456",
        })
        assert resp.status_code == 422

    def test_register_password_no_digit_returns_422(self):
        """注册密码缺少数字返回 422"""
        resp = client.post("/test-schema/register-request", json={
            "username": "testuser",
            "email": "a@b.com",
            "password": "Abcdefghi",
            "confirm_password": "Abcdefghi",
        })
        assert resp.status_code == 422

    def test_register_password_too_short_returns_422(self):
        """注册密码长度不足返回 422"""
        resp = client.post("/test-schema/register-request", json={
            "username": "testuser",
            "email": "a@b.com",
            "password": "Ab1",
            "confirm_password": "Ab1",
        })
        assert resp.status_code == 422

    # --- 任务相关 ---

    def test_task_create_missing_name_returns_422(self):
        """创建任务缺少 name 字段返回 422"""
        resp = client.post("/test-schema/task-create", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "VALIDATION_ERROR"

    def test_task_create_empty_name_returns_422(self):
        """创建任务 name 为空字符串返回 422"""
        resp = client.post("/test-schema/task-create", json={"name": ""})
        assert resp.status_code == 422

    def test_task_create_name_too_long_returns_422(self):
        """创建任务 name 超过最大长度返回 422"""
        resp = client.post("/test-schema/task-create", json={
            "name": "x" * 201
        })
        assert resp.status_code == 422

    def test_task_create_valid_request_returns_201(self):
        """创建任务合法请求返回 201"""
        resp = client.post("/test-schema/task-create", json={
            "name": "Test Task"
        })
        assert resp.status_code == 201

    # --- 项目相关 ---

    def test_project_create_missing_name_returns_422(self):
        """创建项目缺少 name 返回 422"""
        resp = client.post("/test-schema/project-create", json={})
        assert resp.status_code == 422

    def test_project_create_valid_returns_201(self):
        """创建项目合法请求返回 201"""
        resp = client.post("/test-schema/project-create", json={"name": "MyProject"})
        assert resp.status_code == 201

    # --- 看板相关 ---

    def test_board_create_missing_name_returns_422(self):
        """创建看板缺少 name 返回 422"""
        resp = client.post("/test-schema/board-create", json={})
        assert resp.status_code == 422

    def test_board_create_valid_returns_201(self):
        """创建看板合法请求返回 201"""
        resp = client.post("/test-schema/board-create", json={"name": "Board1"})
        assert resp.status_code == 201

    # --- 评论相关 ---

    def test_comment_create_missing_content_returns_422(self):
        """创建评论缺少 content 返回 422"""
        resp = client.post("/test-schema/comment-create", json={})
        assert resp.status_code == 422

    def test_comment_create_empty_content_returns_422(self):
        """创建评论 content 为空返回 422"""
        resp = client.post("/test-schema/comment-create", json={"content": ""})
        assert resp.status_code == 422

    def test_comment_create_valid_returns_201(self):
        """创建评论合法请求返回 201"""
        resp = client.post("/test-schema/comment-create", json={"content": "Hello"})
        assert resp.status_code == 201

    # --- 附件相关 ---

    def test_attachment_create_missing_name_returns_422(self):
        """创建附件缺少 name 返回 422"""
        resp = client.post("/test-schema/attachment-create", json={})
        assert resp.status_code == 422

    # --- 依赖相关 ---

    def test_dependency_create_missing_source_returns_422(self):
        """创建依赖缺少 source_task_id 返回 422"""
        resp = client.post("/test-schema/dependency-create", json={})
        assert resp.status_code == 422

    def test_dependency_create_both_empty_returns_422(self):
        """创建依赖两个字段为空返回 422"""
        resp = client.post("/test-schema/dependency-create", json={
            "source_task_id": "", "target_task_id": ""
        })
        assert resp.status_code == 422

    # --- 通知相关 ---

    def test_notification_create_missing_required_returns_422(self):
        """创建通知缺少必填字段返回 422"""
        resp = client.post("/test-schema/notification-create", json={})
        assert resp.status_code == 422

    def test_notification_create_title_too_long_returns_422(self):
        """创建通知 title 过长返回 422"""
        resp = client.post("/test-schema/notification-create", json={
            "user_id": "u1", "type": "info",
            "title": "x" * 201, "content": "ok"
        })
        assert resp.status_code == 422

    # --- 需求相关 ---

    def test_requirement_create_missing_project_id_returns_422(self):
        """创建需求缺少 project_id 返回 422"""
        resp = client.post("/test-schema/requirement-create", json={})
        assert resp.status_code == 422

    def test_requirement_create_empty_content_returns_422(self):
        """创建需求 content 为空返回 422"""
        resp = client.post("/test-schema/requirement-create", json={
            "project_id": "p1", "content": ""
        })
        assert resp.status_code == 422

    # --- Agent 相关 ---

    def test_agent_create_missing_name_returns_422(self):
        """创建 Agent 缺少 name 返回 422"""
        resp = client.post("/test-schema/agent-create", json={})
        assert resp.status_code == 422

    def test_agent_create_empty_name_returns_422(self):
        """创建 Agent name 为空返回 422"""
        resp = client.post("/test-schema/agent-create", json={"name": "", "agent_type": "test"})
        assert resp.status_code == 422

    # --- Group 相关 ---

    def test_group_create_missing_name_returns_422(self):
        """创建群组缺少 name 返回 422"""
        resp = client.post("/test-schema/group-create", json={})
        assert resp.status_code == 422

    # --- Repo 相关 ---

    def test_repo_create_missing_required_returns_422(self):
        """创建仓库缺少必填字段返回 422"""
        resp = client.post("/test-schema/repo-create", json={})
        assert resp.status_code == 422

    # --- 验收相关 ---

    def test_acceptance_create_missing_required_returns_422(self):
        """创建验收记录缺少必填字段返回 422"""
        resp = client.post("/test-schema/acceptance-create", json={})
        assert resp.status_code == 422


# ============================================================================
# 测试类 3：校验错误响应包含详细信息
# ============================================================================

class TestValidationErrorDetails:
    """校验错误响应包含详细信息"""

    def test_error_has_code_field(self):
        """校验错误响应包含 code 字段"""
        resp = client.post("/test-schema/task-create", json={})
        body = resp.json()
        assert "code" in body
        assert body["code"] == "VALIDATION_ERROR"

    def test_error_has_message_field(self):
        """校验错误响应包含 message 字段"""
        resp = client.post("/test-schema/task-create", json={})
        body = resp.json()
        assert "message" in body
        assert isinstance(body["message"], str)
        assert len(body["message"]) > 0

    def test_error_has_details_field(self):
        """校验错误响应包含 details 字段"""
        resp = client.post("/test-schema/task-create", json={})
        body = resp.json()
        assert "details" in body
        assert isinstance(body["details"], dict)

    def test_error_details_contains_errors_list(self):
        """details 包含 errors 列表"""
        resp = client.post("/test-schema/task-create", json={})
        body = resp.json()
        assert "errors" in body["details"]
        assert isinstance(body["details"]["errors"], list)
        assert len(body["details"]["errors"]) > 0

    def test_each_error_has_type(self):
        """每个错误项包含 type 字段"""
        resp = client.post("/test-schema/task-create", json={})
        errors = resp.json()["details"]["errors"]
        for err in errors:
            assert "type" in err, f"错误项缺少 type 字段: {err}"

    def test_each_error_has_loc(self):
        """每个错误项包含 loc 字段（指出出错字段路径）"""
        resp = client.post("/test-schema/task-create", json={})
        errors = resp.json()["details"]["errors"]
        for err in errors:
            assert "loc" in err, f"错误项缺少 loc 字段: {err}"
            assert isinstance(err["loc"], list)
            assert len(err["loc"]) > 0

    def test_each_error_has_msg(self):
        """每个错误项包含 msg 字段（人类可读的错误描述）"""
        resp = client.post("/test-schema/task-create", json={})
        errors = resp.json()["details"]["errors"]
        for err in errors:
            assert "msg" in err, f"错误项缺少 msg 字段: {err}"
            assert isinstance(err["msg"], str)
            assert len(err["msg"]) > 0

    def test_error_loc_points_to_missing_field(self):
        """loc 字段准确指向缺失的字段名"""
        resp = client.post("/test-schema/task-create", json={})
        errors = resp.json()["details"]["errors"]
        locs = [tuple(e["loc"]) for e in errors]
        assert ("body", "name") in locs, f"未找到缺失字段 'name': {locs}"

    def test_multiple_validation_errors_returned(self):
        """多个字段同时出错时返回多个错误项"""
        resp = client.post("/test-schema/dependency-create", json={})
        errors = resp.json()["details"]["errors"]
        assert len(errors) >= 2, "应返回至少 2 个错误（source_task_id 和 target_task_id）"

    def test_valid_request_does_not_have_validation_error(self):
        """合法请求不返回校验错误"""
        resp = client.post("/test-schema/comment-create", json={"content": "test"})
        body = resp.json()
        assert body["code"] == 0
        assert "errors" not in body.get("details", {})


# ============================================================================
# 测试类 4：Schema JSON Schema 内容正确性
# ============================================================================

class TestSchemaJSONSchemaContent:
    """Schema 生成的 JSON Schema 内容正确性"""

    def test_required_fields_in_schema(self):
        """JSON Schema 正确标记 required 字段"""
        for mod_name, cls_name, cls in _body_schemas:
            schema = cls.model_json_schema()
            required_in_schema = set(schema.get("required", []))
            required_in_model = {
                name for name, field in cls.model_fields.items()
                if field.is_required()
            }
            assert required_in_model.issubset(required_in_schema), (
                f"{mod_name}:{cls_name} required 不匹配: "
                f"model={required_in_model}, schema={required_in_schema}"
            )

    def test_field_types_in_schema(self):
        """JSON Schema 中字段类型正确"""
        all_classes = _get_all_schema_classes()
        for mod_name, cls_name, cls in all_classes:
            schema = cls.model_json_schema()
            if "properties" not in schema:
                continue
            for field_name, field_info in cls.model_fields.items():
                if field_name not in schema["properties"]:
                    continue
                prop_schema = schema["properties"][field_name]
                assert (
                    "type" in prop_schema or "$ref" in prop_schema or "anyOf" in prop_schema
                ), f"{mod_name}:{cls_name}.{field_name} 缺少类型定义"

    def test_string_constraints_in_schema(self):
        """字符串字段的 min_length/max_length 约束在 Schema 中"""
        all_classes = _get_all_schema_classes()
        for mod_name, cls_name, cls in all_classes:
            schema = cls.model_json_schema()
            if "properties" not in schema:
                continue
            for field_name, field_info in cls.model_fields.items():
                prop = schema.get("properties", {}).get(field_name)
                if not prop:
                    continue
                if hasattr(field_info, "constraints"):
                    if "min_length" in field_info.constraints:
                        assert prop.get("minLength") == field_info.constraints["min_length"], (
                            f"{cls_name}.{field_name} minLength 不匹配"
                        )
                    if "max_length" in field_info.constraints:
                        assert prop.get("maxLength") == field_info.constraints["max_length"], (
                            f"{cls_name}.{field_name} maxLength 不匹配"
                        )

    def test_field_description_in_schema(self):
        """字段有 description 时 JSON Schema 也包含描述"""
        all_classes = _get_all_schema_classes()
        for mod_name, cls_name, cls in all_classes:
            schema = cls.model_json_schema()
            if "properties" not in schema:
                continue
            for field_name, field_info in cls.model_fields.items():
                prop = schema.get("properties", {}).get(field_name)
                if not prop:
                    continue
                if field_info.description:
                    assert prop.get("description") == field_info.description, (
                        f"{cls_name}.{field_name} description 不匹配"
                    )


# ============================================================================
# 测试类 5：每个 API 端点都有 JSON Schema 定义
# ============================================================================

class TestAllEndpointsHaveSchemaDefinition:
    """每个 API 端点都有 JSON Schema 定义"""

    def test_all_body_schemas_registered_as_endpoints(self):
        """所有请求体 Schema 都注册为测试端点"""
        openapi = app.openapi()
        paths = openapi.get("paths", {})
        for mod_name, cls_name, cls in _body_schemas:
            route_path = f"/test-schema/{_safe_route_name(cls_name)}"
            assert route_path in paths, (
                f"Schema '{cls_name}' ({mod_name}) 未注册为端点"
            )
            assert "post" in paths[route_path], (
                f"端点 {route_path} 缺少 POST 方法"
            )
            post_op = paths[route_path]["post"]
            request_body = post_op.get("requestBody", {})
            assert "content" in request_body, (
                f"端点 {route_path} 的请求体缺少 content 定义"
            )

    def test_openapi_schema_references_are_valid(self):
        """OpenAPI Schema 引用都指向有效的定义"""
        openapi = app.openapi()
        defs = openapi.get("$defs", {})
        paths = openapi.get("paths", {})
        for path, methods in paths.items():
            for method, op in methods.items():
                if method not in ("get", "post", "put", "delete", "patch"):
                    continue
                request_body = op.get("requestBody", {})
                content = request_body.get("content", {})
                for media_type, media in content.items():
                    schema = media.get("schema", {})
                    ref = schema.get("$ref")
                    if ref and ref.startswith("#/$defs/"):
                        def_name = ref.split("/")[-1]
                        assert def_name in defs, (
                            f"Schema 引用 {ref} 在 $defs 中不存在"
                        )

    def test_each_endpoint_has_request_body_schema(self):
        """每个 POST 端点都有明确的请求体 Schema"""
        openapi = app.openapi()
        paths = openapi.get("paths", {})
        for path, methods in paths.items():
            if not path.startswith("/test-schema/"):
                continue
            post_op = methods.get("post")
            if not post_op:
                continue
            request_body = post_op.get("requestBody", {})
            content = request_body.get("content", {})
            assert len(content) > 0, f"端点 {path} 的请求体 content 为空"
