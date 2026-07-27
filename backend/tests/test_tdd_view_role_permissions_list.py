import pytest
import time
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

ALL_PERMISSIONS = [
    {"key": "project_create", "label": "创建项目", "description": "允许创建新项目"},
    {"key": "project_delete", "label": "删除项目", "description": "允许删除已有项目"},
    {"key": "project_read", "label": "查看项目", "description": "允许查看项目详情"},
    {"key": "project_update", "label": "更新项目", "description": "允许更新项目信息"},
    {"key": "workflow_start", "label": "启动工作流", "description": "允许启动项目工作流"},
    {"key": "workflow_stop", "label": "停止工作流", "description": "允许停止运行中的工作流"},
    {"key": "workflow_view", "label": "查看工作流", "description": "允许查看工作流状态"},
    {"key": "workflow_edit", "label": "编辑工作流", "description": "允许编辑工作流配置"},
    {"key": "agent_manage", "label": "管理Agent", "description": "允许管理Agent配置"},
    {"key": "agent_assign", "label": "分配Agent", "description": "允许分配Agent到任务"},
    {"key": "agent_monitor", "label": "监控Agent", "description": "允许监控Agent运行状态"},
    {"key": "task_create", "label": "创建任务", "description": "允许创建新任务"},
    {"key": "task_delete", "label": "删除任务", "description": "允许删除已有任务"},
    {"key": "task_assign", "label": "分配任务", "description": "允许分配任务给Agent"},
    {"key": "task_review", "label": "审查任务", "description": "允许审查任务完成情况"},
    {"key": "requirement_read", "label": "查看需求", "description": "允许查看需求文档"},
    {"key": "requirement_edit", "label": "编辑需求", "description": "允许编辑需求文档"},
    {"key": "requirement_approve", "label": "审批需求", "description": "允许审批需求变更"},
    {"key": "code_review", "label": "代码审查", "description": "允许审查代码变更"},
    {"key": "qa_inspect", "label": "QA检验", "description": "允许执行QA检验"},
    {"key": "repo_manage", "label": "仓库管理", "description": "允许管理代码仓库"},
    {"key": "notification_manage", "label": "通知管理", "description": "允许管理通知设置"},
    {"key": "setting_manage", "label": "系统设置", "description": "允许管理系统设置"},
    {"key": "audit_log_view", "label": "审计日志", "description": "允许查看审计日志"},
]

ROLE_PERMISSIONS_MAP = {
    "haimei": ["project_create", "project_delete", "project_read", "project_update",
               "workflow_start", "workflow_stop", "workflow_view", "workflow_edit",
               "agent_manage", "agent_assign", "agent_monitor",
               "task_create", "task_delete", "task_assign", "task_review",
               "requirement_read", "requirement_edit", "requirement_approve",
               "code_review", "qa_inspect", "repo_manage",
               "notification_manage", "setting_manage", "audit_log_view"],
    "houxing": ["project_read", "requirement_read", "requirement_edit", "requirement_approve", "task_create"],
    "houwang": ["project_read", "workflow_view", "workflow_edit", "task_review", "code_review"],
    "houfa": ["project_read", "task_create", "task_assign", "workflow_start", "workflow_view", "code_review"],
    "houda": ["project_read", "task_review", "qa_inspect", "workflow_view"],
    "houfu": ["project_read", "repo_manage", "workflow_start", "workflow_stop", "setting_manage"],
    "hougui": ["project_read", "requirement_read", "workflow_view", "notification_manage"],
    "hourong": ["project_read", "qa_inspect", "audit_log_view", "workflow_view", "code_review", "task_review"],
    "houhua": ["project_read", "code_review", "audit_log_view", "setting_manage", "repo_manage"],
}

NAMED_ROLES = [
    {"role_name": "haimei", "chinese_name": "海梅", "role_type": "project_manager",
     "description": "默认Hermes Agent，项目经理，负责任务分派，对项目交付成果负责"},
    {"role_name": "houxing", "chinese_name": "后兴", "role_type": "requirement_analyst",
     "description": "需求分析师，负责需求分析，产出完整准确的软件需求说明书"},
    {"role_name": "houwang", "chinese_name": "后旺", "role_type": "architect",
     "description": "架构设计师，负责架构设计、后端设计、前端设计、数据库设计"},
    {"role_name": "houfa", "chinese_name": "后发", "role_type": "programmer",
     "description": "程序员，负责建立代码编写Agent蜂群，监督蜂群完成TDD测试用例和代码编写"},
    {"role_name": "houda", "chinese_name": "后达", "role_type": "tester",
     "description": "测试员，负责建立代码测试Agent蜂群，执行全面测试"},
    {"role_name": "houfu", "chinese_name": "后富", "role_type": "cicd_engineer",
     "description": "CI/CD工程师，负责开发环境搭建和代码部署"},
    {"role_name": "hougui", "chinese_name": "后贵", "role_type": "doc_manager",
     "description": "文档管理员，负责项目文档一致性管理"},
    {"role_name": "hourong", "chinese_name": "后荣", "role_type": "qa",
     "description": "QA，检验每个Agent产出，未达标退回重做，达标放行并提交代码库"},
    {"role_name": "houhua", "chinese_name": "后华", "role_type": "security_officer",
     "description": "安全员，负责代码审计、合规审查、渗透测试、漏洞修复"},
]


def _build_app():
    app = FastAPI(title="Role Permissions Test API")

    @app.get("/api/roles")
    def list_all_roles():
        result = []
        for role_def in NAMED_ROLES:
            role_name = role_def["role_name"]
            perm_keys = ROLE_PERMISSIONS_MAP.get(role_name, [])
            permissions = [p for p in ALL_PERMISSIONS if p["key"] in perm_keys]
            result.append({
                "role_name": role_def["role_name"],
                "chinese_name": role_def["chinese_name"],
                "role_type": role_def["role_type"],
                "description": role_def["description"],
                "permissions": permissions,
            })
        return {"code": 0, "roles": result}

    @app.get("/api/roles/{role_name}")
    def get_role_permissions(role_name: str):
        role_def = None
        for r in NAMED_ROLES:
            if r["role_name"] == role_name:
                role_def = r
                break
        if role_def is None:
            raise HTTPException(status_code=404, detail=f"角色 {role_name} 不存在")
        perm_keys = ROLE_PERMISSIONS_MAP.get(role_name, [])
        permissions = [p for p in ALL_PERMISSIONS if p["key"] in perm_keys]
        return {
            "code": 0,
            "role_name": role_def["role_name"],
            "chinese_name": role_def["chinese_name"],
            "role_type": role_def["role_type"],
            "description": role_def["description"],
            "permissions": permissions,
        }

    return app


@pytest.fixture
def client():
    app = _build_app()
    with TestClient(app) as c:
        yield c


class TestViewRolePermissions:

    def test_get_role_returns_http_200(self, client):
        resp = client.get("/api/roles/haimei")
        assert resp.status_code == 200

    def test_response_time_under_100ms(self, client):
        start = time.perf_counter()
        resp = client.get("/api/roles/haimei")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 100, f"响应时间 {elapsed_ms:.2f}ms 超过 100ms"

    def test_returns_role_name_and_description(self, client):
        resp = client.get("/api/roles/haimei")
        data = resp.json()
        assert data["role_name"] == "haimei"
        assert isinstance(data["description"], str)
        assert len(data["description"]) > 0

    def test_permissions_include_required_keys(self, client):
        resp = client.get("/api/roles/haimei")
        data = resp.json()
        keys = [p["key"] for p in data["permissions"]]
        assert "project_create" in keys
        assert "project_delete" in keys
        assert "workflow_start" in keys

    def test_permissions_list_is_complete_for_haimei(self, client):
        resp = client.get("/api/roles/haimei")
        data = resp.json()
        keys = {p["key"] for p in data["permissions"]}
        expected = {
            "project_create", "project_delete", "project_read", "project_update",
            "workflow_start", "workflow_stop", "workflow_view", "workflow_edit",
            "agent_manage", "agent_assign", "agent_monitor",
            "task_create", "task_delete", "task_assign", "task_review",
            "requirement_read", "requirement_edit", "requirement_approve",
            "code_review", "qa_inspect", "repo_manage",
            "notification_manage", "setting_manage", "audit_log_view",
        }
        assert keys == expected

    def test_each_permission_has_key_label_description(self, client):
        resp = client.get("/api/roles/haimei")
        data = resp.json()
        for perm in data["permissions"]:
            assert "key" in perm
            assert "label" in perm
            assert "description" in perm

    def test_nonexistent_role_returns_404(self, client):
        resp = client.get("/api/roles/nonexistent_role_xyz")
        assert resp.status_code == 404

    def test_all_named_roles_return_data(self, client):
        resp = client.get("/api/roles")
        data = resp.json()
        assert data["code"] == 0
        roles = data["roles"]
        assert len(roles) == len(NAMED_ROLES)
        for role in roles:
            assert "role_name" in role
            assert "description" in role
            assert isinstance(role["permissions"], list)
            assert len(role["permissions"]) > 0

    def test_different_roles_have_different_permission_sets(self, client):
        pm_resp = client.get("/api/roles/haimei")
        qa_resp = client.get("/api/roles/hourong")
        dev_resp = client.get("/api/roles/houfa")
        pm_keys = {p["key"] for p in pm_resp.json()["permissions"]}
        qa_keys = {p["key"] for p in qa_resp.json()["permissions"]}
        dev_keys = {p["key"] for p in dev_resp.json()["permissions"]}
        assert pm_keys != qa_keys
        assert pm_keys != dev_keys
        assert qa_keys != dev_keys

    def test_permission_keys_are_unique_within_role(self, client):
        resp = client.get("/api/roles/haimei")
        data = resp.json()
        keys = [p["key"] for p in data["permissions"]]
        assert len(keys) == len(set(keys))
