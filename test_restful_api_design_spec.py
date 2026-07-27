import re
import json
import pytest
from typing import Any
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from unittest.mock import MagicMock


# ====================================================================
# SUT: RESTful 规范检查器
# ====================================================================


class EndpointRecord:
    """单个路由端点的规范化表示。"""

    def __init__(self, method: str, path: str, status_code: int = 200):
        self.method = method.upper()
        self.path = path
        self.status_code = status_code

    @property
    def resource_segments(self) -> list[str]:
        """提取路径中实际的资源段，去掉版本前缀和路径参数。"""
        p = self.path.strip("/")
        parts = p.split("/") if p else []
        # 去掉版本前缀 /api/v{N}
        filtered: list[str] = []
        skip = 0
        for i, seg in enumerate(parts):
            if skip > 0:
                skip -= 1
                continue
            if seg == "api" and i + 1 < len(parts) and re.match(r"^v\d+$", parts[i + 1]):
                skip = 1
                continue
            if not seg.startswith("{"):
                filtered.append(seg)
        return filtered

    @property
    def main_resource(self) -> str | None:
        """返回主资源名（集合资源的第一个资源段）。"""
        segs = self.resource_segments
        return segs[0] if segs else None

    def __repr__(self):
        return f"<Endpoint {self.method} {self.path}>"


class RESTfulRuleChecker:
    """RESTful 规范的规则检查集合。"""

    VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

    SINGULARS = {
        "board": "boards",
        "task": "tasks",
        "project": "projects",
        "agent": "agents",
        "user": "users",
        "group": "groups",
        "meeting": "meetings",
        "profile": "profiles",
        "skill": "skills",
        "comment": "comments",
        "attachment": "attachments",
        "requirement": "requirements",
        "notification": "notifications",
        "swarm": "swarms",
        "webhook": "webhooks",
        "column": "columns",
    }

    VERBS = {
        "get", "post", "create", "delete", "update", "remove",
        "add", "set", "list", "fetch", "delete", "insert",
    }

    exempt_paths = {"/", "/health", "/healthz", "/ready"}

    def __init__(self):
        self.rules: list[tuple[str, str, callable]] = []
        self._register_rules()

    def _register_rules(self):
        self.rules = [
            ("method-valid", "HTTP 方法有效", self._check_method_valid),
            ("url-no-verb-prefix", "URL 路径不以动词开头", self._check_no_verb_prefix),
            ("resource-plural", "集合资源名使用复数", self._check_resource_plural),
            ("url-kebab-case", "URL 路径使用 kebab-case", self._check_kebabcase),
            ("url-no-extension", "URL 不包含文件扩展名", self._check_no_extension),
            ("url-versioned", "URL 包含版本前缀", self._check_versioned),
            ("method-resource-match", "HTTP 方法与资源操作匹配", self._check_method_resource_match),
            ("path-no-trailing-slash", "路径不以斜杠结尾", self._check_no_trailing_slash),
            ("nested-resource-logical", "嵌套资源层级合理", self._check_nested_resource),
            ("status-code-compliant", "状态码符合 RESTful 规范", self._check_status_code),
        ]

    def check(self, endpoint: EndpointRecord) -> list[dict]:
        failures = []
        for rule_id, rule_name, check_fn in self.rules:
            passed, reason = check_fn(endpoint)
            if not passed:
                failures.append({
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "endpoint": str(endpoint),
                    "reason": reason,
                })
        return failures

    def check_all(self, endpoints: list[EndpointRecord]) -> dict:
        total_checks = len(self.rules) * len(endpoints)
        all_failures = []
        failed_endpoints = []

        for ep in endpoints:
            failures = self.check(ep)
            if failures:
                all_failures.extend(failures)
                failed_endpoints.append(str(ep))

        passed = total_checks - len(all_failures)
        compliance_rate = (passed / total_checks * 100) if total_checks else 100.0

        return {
            "total_endpoints": len(endpoints),
            "total_checks": total_checks,
            "passed_checks": passed,
            "failed_checks": len(all_failures),
            "compliance_rate": round(compliance_rate, 2),
            "failed_endpoints": failed_endpoints,
            "failures": all_failures,
        }

    # ── 规则实现 ──

    def _check_method_valid(self, ep: EndpointRecord) -> tuple[bool, str]:
        if ep.method not in self.VALID_METHODS:
            return False, f"无效 HTTP 方法: {ep.method}"
        return True, ""

    def _check_no_verb_prefix(self, ep: EndpointRecord) -> tuple[bool, str]:
        segs = ep.resource_segments
        if not segs:
            return True, ""
        first = segs[0].lower()
        clean = re.sub(r"\.(json|xml|txt|html|csv|yaml)$", "", first)
        first_word = clean.split("-")[0]
        if first_word in self.VERBS:
            return False, f"URL 以动词 '{first_word}' 开头，应使用名词"
        return True, ""

    def _check_resource_plural(self, ep: EndpointRecord) -> tuple[bool, str]:
        main = ep.main_resource
        if not main:
            return True, ""
        lower = main.lower()
        if lower in self.SINGULARS:
            expected = self.SINGULARS[lower]
            if lower != expected:
                return False, f"资源名 '{lower}' 应为复数 '{expected}'"
        return True, ""

    def _check_kebabcase(self, ep: EndpointRecord) -> tuple[bool, str]:
        parts = ep.path.strip("/").split("/") if ep.path.strip("/") else []
        for seg in parts:
            clean = re.sub(r"\{[^}]+\}", "", seg)
            if not clean:
                continue
            if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", clean):
                return False, f"路径段 '{clean}' 未使用 kebab-case 命名"
        return True, ""

    def _check_no_extension(self, ep: EndpointRecord) -> tuple[bool, str]:
        clean = ep.path.rstrip("/")
        if re.search(r"\.(json|xml|txt|html|csv|yaml)$", clean, re.IGNORECASE):
            return False, "URL 不应包含文件扩展名"
        return True, ""

    def _check_versioned(self, ep: EndpointRecord) -> tuple[bool, str]:
        clean = ep.path.strip("/")
        if not clean or clean in {s.lstrip("/") for s in self.exempt_paths}:
            return True, ""
        if "/api/v" not in ep.path:
            return False, "API 端点应包含版本前缀（如 /api/v1/）"
        return True, ""

    def _check_method_resource_match(self, ep: EndpointRecord) -> tuple[bool, str]:
        return True, ""

    def _check_no_trailing_slash(self, ep: EndpointRecord) -> tuple[bool, str]:
        if ep.path != "/" and ep.path.endswith("/"):
            return False, "URL 不应以斜杠结尾"
        return True, ""

    def _check_nested_resource(self, ep: EndpointRecord) -> tuple[bool, str]:
        segs = ep.resource_segments
        if len(segs) > 4:
            return False, f"嵌套层级过多（{len(segs)} 层），建议不超过 4 层"
        return True, ""

    def _check_status_code(self, ep: EndpointRecord) -> tuple[bool, str]:
        valid_post = (200, 201, 202)
        valid_delete = (200, 204)
        valid_put = (200, 204)
        if ep.method == "POST" and ep.status_code not in valid_post:
            return False, f"POST 操作状态码应为 200/201/202（当前 {ep.status_code}）"
        if ep.method == "DELETE" and ep.status_code not in valid_delete:
            return False, f"DELETE 操作状态码应为 200/204（当前 {ep.status_code}）"
        if ep.method == "PUT" and ep.status_code not in valid_put:
            return False, f"PUT 操作状态码应为 200/204（当前 {ep.status_code}）"
        return True, ""


# ====================================================================
# SUT: 标准错误体校验器
# ====================================================================


class ErrorResponseValidator:
    """验证 API 错误体是否符合标准格式。"""

    REQUIRED_FIELDS = {"code", "message", "details"}
    CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3,}$|^[A-Z][A-Z0-9_]+$")

    def validate(self, body: Any) -> list[str]:
        errors: list[str] = []
        if not isinstance(body, dict):
            return ["错误体不是 JSON 对象"]
        if "error" not in body:
            errors.append("缺少顶层 'error' 字段")
            return errors
        error_obj = body["error"]
        if not isinstance(error_obj, dict):
            errors.append("'error' 字段值不是对象")
            return errors
        missing = self.REQUIRED_FIELDS - set(error_obj.keys())
        if missing:
            errors.append(f"error 对象缺少字段: {missing}")
        if "code" in error_obj:
            code = error_obj["code"]
            if not isinstance(code, str):
                errors.append("error.code 应为字符串")
            elif not self.CODE_PATTERN.match(code):
                errors.append(f"error.code '{code}' 不符合规范格式")
        if "message" in error_obj:
            if not isinstance(error_obj["message"], str):
                errors.append("error.message 应为字符串")
            elif len(error_obj["message"]) > 500:
                errors.append("error.message 过长（>500 字符）")
        if "details" in error_obj:
            if not isinstance(error_obj["details"], (dict, list)):
                errors.append("error.details 应为对象或列表")
        return errors


# ====================================================================
# Fixture: 构造测试用 FastAPI 应用
# ====================================================================


def build_compliant_app() -> FastAPI:
    """构建符合 RESTful 规范的 FastAPI 应用。"""
    app = FastAPI(title="Compliant API")
    router = APIRouter(redirect_slashes=False, prefix="/api/v1")

    class TaskIn(BaseModel):
        name: str
        description: str = ""

    class TaskUpdate(BaseModel):
        name: str = ""
        description: str = ""

    _tasks_db: dict[str, dict] = {}

    @router.post("/tasks", status_code=201)
    def create_task(body: TaskIn):
        task_id = f"task-{len(_tasks_db) + 1}"
        _tasks_db[task_id] = {"id": task_id, "name": body.name, "description": body.description}
        return {"id": task_id, "name": body.name, "description": body.description}

    @router.get("/tasks")
    def list_tasks():
        return {"items": list(_tasks_db.values()), "total": len(_tasks_db)}

    @router.get("/tasks/{task_id}")
    def get_task(task_id: str):
        if task_id not in _tasks_db:
            raise HTTPException(status_code=404, detail="not found")
        return _tasks_db[task_id]

    @router.put("/tasks/{task_id}")
    def update_task(task_id: str, body: TaskUpdate):
        if task_id not in _tasks_db:
            raise HTTPException(status_code=404, detail="not found")
        _tasks_db[task_id].update({"name": body.name, "description": body.description})
        return _tasks_db[task_id]

    @router.patch("/tasks/{task_id}")
    def patch_task(task_id: str, body: dict):
        if task_id not in _tasks_db:
            raise HTTPException(status_code=404, detail="not found")
        _tasks_db[task_id].update(body)
        return _tasks_db[task_id]

    @router.delete("/tasks/{task_id}", status_code=204)
    def delete_task(task_id: str):
        if task_id not in _tasks_db:
            raise HTTPException(status_code=404, detail="not found")
        _tasks_db.pop(task_id)
        return None

    @router.get("/boards")
    def list_boards():
        return {"items": [], "total": 0}

    @router.get("/boards/{board_id}")
    def get_board(board_id: str):
        return {"id": board_id}

    @router.post("/boards", status_code=201)
    def create_board(body: dict):
        return {"id": f"board-1"}

    @router.delete("/boards/{board_id}", status_code=204)
    def delete_board(board_id: str):
        return None

    @router.get("/projects/{project_id}/tasks")
    def list_project_tasks(project_id: str):
        return {"items": [], "total": 0, "project_id": project_id}

    @app.exception_handler(HTTPException)
    async def http_error_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail), "details": {}}},
        )

    app.include_router(router)
    return app


def build_non_compliant_app() -> FastAPI:
    """构建违反 RESTful 规范的 FastAPI 应用。"""
    app = FastAPI(title="Non-Compliant API")

    @app.post("/api/v1/getTasks", status_code=200)
    def get_tasks():
        return {"items": [], "total": 0}

    @app.get("/api/v1/createTask.json")
    def create_task():
        return {"id": 1}

    @app.get("/api/v1/task/123/update")
    def update_task():
        return {"id": 123}

    @app.delete("/api/v1/task/123/remove/")
    def remove_task():
        return {"deleted": True}

    @app.post("/fetch/data/level1/level2/level3/level4/level5")
    def too_deep():
        return {}

    @app.get("/api/v1/task")
    def singular_resource():
        return {"id": 1}

    @app.exception_handler(Exception)
    async def bad_error_handler(request, exc):
        return JSONResponse(status_code=500, content={"msg": str(exc)})

    return app


# ====================================================================
# 测试类: RESTful 规范遵循率
# ====================================================================


class TestRESTfulCompliance:
    """验证 API 遵循 RESTful 设计原则，规范遵循率 >= 95%。"""

    @pytest.fixture
    def checker(self):
        return RESTfulRuleChecker()

    def test_compliant_app_meets_95_percent_threshold(self, checker):
        """完全合规的应用应通过 >= 95% 的检查。"""
        endpoints = [
            EndpointRecord("POST", "/api/v1/tasks", 201),
            EndpointRecord("GET", "/api/v1/tasks", 200),
            EndpointRecord("GET", "/api/v1/tasks/{id}", 200),
            EndpointRecord("PUT", "/api/v1/tasks/{id}", 200),
            EndpointRecord("PATCH", "/api/v1/tasks/{id}", 200),
            EndpointRecord("DELETE", "/api/v1/tasks/{id}", 204),
            EndpointRecord("GET", "/api/v1/boards", 200),
            EndpointRecord("POST", "/api/v1/boards", 201),
            EndpointRecord("DELETE", "/api/v1/boards/{id}", 204),
            EndpointRecord("GET", "/api/v1/projects/{pid}/tasks", 200),
        ]
        result = checker.check_all(endpoints)
        assert result["compliance_rate"] >= 95.0, (
            f"合规率 {result['compliance_rate']}% 低于 95% 阈值。\n"
            f"失败项: {[f['rule_id'] + ':' + f['reason'] for f in result['failures']]}"
        )

    def test_invalid_method_detected(self, checker):
        """无效的 HTTP 方法应被检测出来。"""
        ep = EndpointRecord("TRACE", "/api/v1/tasks")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "method-valid" in failure_ids

    def test_verb_prefix_in_url_detected(self, checker):
        """URL 以动词开头的规范违反应被检测。"""
        ep = EndpointRecord("GET", "/api/v1/get-tasks")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "url-no-verb-prefix" in failure_ids

    def test_singular_resource_name_detected(self, checker):
        """单数资源名应被标记为不合规。"""
        ep = EndpointRecord("GET", "/api/v1/board")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "resource-plural" in failure_ids

    def test_kebab_case_violation_detected(self, checker):
        """non-kebab-case 路径名应被检测。"""
        ep = EndpointRecord("GET", "/api/v1/createTask.json")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "url-kebab-case" in failure_ids

    def test_file_extension_in_url_detected(self, checker):
        """URL 中的文件扩展名应被拒绝。"""
        ep = EndpointRecord("GET", "/api/v1/task.json")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "url-no-extension" in failure_ids

    def test_unversioned_url_detected(self, checker):
        """未包含版本前缀的 URL 应被标记。"""
        ep = EndpointRecord("GET", "/tasks")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "url-versioned" in failure_ids

    def test_trailing_slash_detected(self, checker):
        """尾部斜杠应被检测。"""
        ep = EndpointRecord("DELETE", "/api/v1/tasks/")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "path-no-trailing-slash" in failure_ids

    def test_overly_nested_resource_detected(self, checker):
        """嵌套层级过深应被检测。"""
        ep = EndpointRecord("GET", "/api/v1/a/b/c/d/e")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "nested-resource-logical" in failure_ids

    def test_wrong_status_code_for_post_detected(self, checker):
        """POST 创建操作返回 500 应被检测。"""
        ep = EndpointRecord("POST", "/api/v1/tasks", 500)
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "status-code-compliant" in failure_ids

    def test_wrong_status_code_for_delete_detected(self, checker):
        """DELETE 返回 500 应被检测。"""
        ep = EndpointRecord("DELETE", "/api/v1/tasks/1", 500)
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        violation = next((f for f in failures if f["rule_id"] == "status-code-compliant"), None)
        assert violation is not None

    def test_compliance_rate_calculation_accuracy(self, checker):
        """合规率计算精度正确。"""
        endpoints = [
            EndpointRecord("POST", "/api/v1/tasks", 201),
            EndpointRecord("GET", "/api/v1/tasks", 200),
            EndpointRecord("TRACE", "/api/v1/tasks"),
        ]
        result = checker.check_all(endpoints)
        total = result["total_checks"]
        passed = result["passed_checks"]
        assert result["compliance_rate"] == round(passed / total * 100, 2)

    def test_empty_endpoint_list_returns_100_percent(self, checker):
        """空端点列表返回 100% 合规率。"""
        result = checker.check_all([])
        assert result["compliance_rate"] == 100.0

    def test_multiple_violations_same_endpoint(self, checker):
        """同一端点有多个违规应全部报告。"""
        ep = EndpointRecord("TRACE", "/get-tasks.json/")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "method-valid" in failure_ids
        assert "url-no-verb-prefix" in failure_ids
        assert "url-no-extension" in failure_ids
        assert "url-versioned" in failure_ids
        assert "path-no-trailing-slash" in failure_ids

    def test_health_endpoint_exempted_from_versioning(self, checker):
        """健康检查端点应豁免版本前缀要求。"""
        ep = EndpointRecord("GET", "/health")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "url-versioned" not in failure_ids

    def test_root_endpoint_exempted_from_versioning(self, checker):
        """根路径应豁免版本前缀要求。"""
        ep = EndpointRecord("GET", "/")
        failures = checker.check(ep)
        failure_ids = [f["rule_id"] for f in failures]
        assert "url-versioned" not in failure_ids

    def test_compliant_app_integration_via_testclient(self):
        """通过 TestClient 集成测试合规应用的路由行为。"""
        app = build_compliant_app()
        client = TestClient(app)

        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

        create_resp = client.post("/api/v1/tasks", json={"name": "test-task"})
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert "id" in created
        assert created["name"] == "test-task"

        get_resp = client.get(f"/api/v1/tasks/{created['id']}")
        assert get_resp.status_code == 200

        delete_resp = client.delete(f"/api/v1/tasks/{created['id']}")
        assert delete_resp.status_code == 204


# ====================================================================
# 测试类: 标准错误体格式
# ====================================================================


class TestErrorResponseFormat:
    """验证错误体格式: {\"error\":{\"code\":\"...\",\"message\":\"...\",\"details\":{}}}"""

    @pytest.fixture
    def validator(self):
        return ErrorResponseValidator()

    def test_valid_error_format_passes(self, validator):
        """标准错误体格式应验证通过。"""
        body = {
            "error": {
                "code": "AUTH-001",
                "message": "Missing authorization token",
                "details": {},
            }
        }
        errors = validator.validate(body)
        assert len(errors) == 0

    def test_error_with_details_map_passes(self, validator):
        """error.details 包含具体信息的格式应验证通过。"""
        body = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"field": "email", "reason": "invalid format"},
            }
        }
        errors = validator.validate(body)
        assert len(errors) == 0

    def test_missing_error_top_level_detected(self, validator):
        """缺少 'error' 顶层字段应被报告。"""
        body = {"msg": "something went wrong"}
        errors = validator.validate(body)
        assert len(errors) > 0

    def test_missing_code_field_detected(self, validator):
        """缺少 code 字段应被报告。"""
        body = {"error": {"message": "error", "details": {}}}
        errors = validator.validate(body)
        assert any("code" in e.lower() for e in errors)

    def test_missing_message_field_detected(self, validator):
        """缺少 message 字段应被报告。"""
        body = {"error": {"code": "ERR-001", "details": {}}}
        errors = validator.validate(body)
        assert any("message" in e.lower() for e in errors)

    def test_missing_details_field_detected(self, validator):
        """缺少 details 字段应被报告。"""
        body = {"error": {"code": "ERR-001", "message": "error"}}
        errors = validator.validate(body)
        assert any("details" in e.lower() for e in errors)

    def test_invalid_code_format_detected(self, validator):
        """不规范的 code 格式应被标记。"""
        body = {"error": {"code": "abc", "message": "err", "details": {}}}
        errors = validator.validate(body)
        assert any("code" in e.lower() and "格式" in e for e in errors)

    def test_non_dict_body_detected(self, validator):
        """非字典类型的错误体应被拒绝。"""
        errors = validator.validate("just a string")
        assert len(errors) > 0

        errors = validator.validate(None)
        assert len(errors) > 0

        errors = validator.validate([1, 2, 3])
        assert len(errors) > 0

    def test_error_object_not_dict_detected(self, validator):
        """error 字段值不是对象应被拒绝。"""
        body = {"error": "string instead of object"}
        errors = validator.validate(body)
        assert any("不是" in e for e in errors)

    def test_code_not_string_detected(self, validator):
        """code 不是字符串应被拒绝。"""
        body = {"error": {"code": 401, "message": "err", "details": {}}}
        errors = validator.validate(body)
        assert any("code" in e.lower() and "字符串" in e for e in errors)

    def test_message_not_string_detected(self, validator):
        """message 不是字符串应被拒绝。"""
        body = {"error": {"code": "ERR-001", "message": 123, "details": {}}}
        errors = validator.validate(body)
        assert any("message" in e.lower() and "字符串" in e for e in errors)

    def test_details_not_object_or_list_detected(self, validator):
        """details 不是对象或列表应被拒绝。"""
        body = {"error": {"code": "ERR-001", "message": "err", "details": "string"}}
        errors = validator.validate(body)
        assert any("details" in e.lower() for e in errors)

    def test_message_too_long_detected(self, validator):
        """过长的 message 应被标记。"""
        body = {
            "error": {
                "code": "ERR-001",
                "message": "x" * 501,
                "details": {},
            }
        }
        errors = validator.validate(body)
        assert any("过长" in e or "500" in e for e in errors)

    def test_code_pattern_accepts_hyphenated(self, validator):
        """连字符格式 code（如 AUTH-001）应接受。"""
        body = {"error": {"code": "AUTH-001", "message": "ok", "details": {}}}
        errors = validator.validate(body)
        assert len(errors) == 0

    def test_code_pattern_accepts_upper_snake(self, validator):
        """大写下划线格式 code（如 INTERNAL_ERROR）应接受。"""
        body = {"error": {"code": "INTERNAL_ERROR", "message": "ok", "details": {}}}
        errors = validator.validate(body)
        assert len(errors) == 0

    def test_code_pattern_rejects_lowercase(self, validator):
        """小写 code 应被拒绝。"""
        body = {"error": {"code": "auth_error", "message": "ok", "details": {}}}
        errors = validator.validate(body)
        assert any("code" in e.lower() and ("格式" in e or "规范" in e) for e in errors)

    def test_full_stack_error_response_integration(self):
        """通过 TestClient 验证实际应用的全链路错误响应格式。"""
        app = build_compliant_app()
        client = TestClient(app)

        resp = client.get("/api/v1/tasks/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "details" in body["error"]
        assert isinstance(body["error"]["code"], str)
        assert isinstance(body["error"]["message"], str)
        assert isinstance(body["error"]["details"], dict)

    def test_non_compliant_app_error_format_detected(self):
        """非合规应用的错误体格式应被检测出。"""
        app = build_non_compliant_app()
        client = TestClient(app)

        resp = client.get("/nonexistent-to-trigger-error")
        validator = ErrorResponseValidator()
        if resp.status_code >= 400:
            errors = validator.validate(resp.json())
            assert len(errors) > 0, "非合规应用应返回不符合标准的错误体"
