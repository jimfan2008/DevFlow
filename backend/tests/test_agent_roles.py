"""v4.0 Agent Role Service Tests"""
import pytest
from app.services.agent_role_service import AgentRoleService, NAMED_ROLES


class TestAgentRoleService:

    def test_named_roles_count(self):
        assert len(NAMED_ROLES) == 9

    def test_all_role_names_present(self):
        names = {r["role_name"] for r in NAMED_ROLES}
        expected = {"haimei", "houxing", "houwang", "houfa", "houda",
                    "houfu", "hougui", "hourong", "houhua"}
        assert names == expected

    def test_haimei_is_project_manager(self):
        haimei = next(r for r in NAMED_ROLES if r["role_name"] == "haimei")
        assert haimei["role_type"] == "project_manager"
        assert haimei["chinese_name"] == "海梅"
        assert "项目经理" in haimei["description"]

    def test_houxing_is_requirement_analyst(self):
        houxing = next(r for r in NAMED_ROLES if r["role_name"] == "houxing")
        assert houxing["role_type"] == "requirement_analyst"
        assert houxing["chinese_name"] == "后兴"

    def test_houwang_is_architect(self):
        houwang = next(r for r in NAMED_ROLES if r["role_name"] == "houwang")
        assert houwang["role_type"] == "architect"
        assert houwang["chinese_name"] == "后旺"

    def test_houfa_is_programmer(self):
        houfa = next(r for r in NAMED_ROLES if r["role_name"] == "houfa")
        assert houfa["role_type"] == "programmer"
        assert houfa["chinese_name"] == "后发"
        assert "蜂群" in houfa["description"]

    def test_houda_is_tester(self):
        houda = next(r for r in NAMED_ROLES if r["role_name"] == "houda")
        assert houda["role_type"] == "tester"
        assert houda["chinese_name"] == "后达"

    def test_houfu_is_cicd_engineer(self):
        houfu = next(r for r in NAMED_ROLES if r["role_name"] == "houfu")
        assert houfu["role_type"] == "cicd_engineer"
        assert houfu["chinese_name"] == "后富"

    def test_hougui_is_doc_manager(self):
        hougui = next(r for r in NAMED_ROLES if r["role_name"] == "hougui")
        assert hougui["role_type"] == "doc_manager"
        assert hougui["chinese_name"] == "后贵"

    def test_hourong_is_qa(self):
        hourong = next(r for r in NAMED_ROLES if r["role_name"] == "hourong")
        assert hourong["role_type"] == "qa"
        assert hourong["chinese_name"] == "后荣"

    def test_houhua_is_security_officer(self):
        houhua = next(r for r in NAMED_ROLES if r["role_name"] == "houhua")
        assert houhua["role_type"] == "security_officer"
        assert houhua["chinese_name"] == "后华"

    def test_get_role_by_name(self):
        service = AgentRoleService()
        role = service.get_role_by_name("haimei")
        assert role["chinese_name"] == "海梅"

    def test_get_role_by_name_not_found(self):
        service = AgentRoleService()
        assert service.get_role_by_name("nonexistent") is None

    def test_get_roles_by_type(self):
        service = AgentRoleService()
        pm_roles = service.get_roles_by_type("project_manager")
        assert len(pm_roles) == 1
        assert pm_roles[0]["role_name"] == "haimei"

    def test_get_swarm_managers(self):
        service = AgentRoleService()
        managers = service.get_swarm_managers()
        manager_names = {m["role_name"] for m in managers}
        assert manager_names == {"houfa", "houda"}

    def test_get_qa_role(self):
        service = AgentRoleService()
        qa = service.get_qa_role()
        assert qa["role_name"] == "hourong"

    def test_all_chinese_names_unique(self):
        names = [r["chinese_name"] for r in NAMED_ROLES]
        assert len(names) == len(set(names))

    def test_all_role_names_lowercase(self):
        for r in NAMED_ROLES:
            assert r["role_name"] == r["role_name"].lower()