"""v4.0 - 10个命名 Agent 角色初始化服务"""

NAMED_ROLES = [
    {
        "role_name": "haimei",
        "chinese_name": "海梅",
        "role_type": "project_manager",
        "description": "默认Hermes Agent，项目经理，负责任务分派，对项目交付成果负责",
    },
    {
        "role_name": "houxing",
        "chinese_name": "后兴",
        "role_type": "requirement_analyst",
        "description": "需求分析师，负责需求分析，产出完整准确的软件需求说明书",
    },
    {
        "role_name": "houwang",
        "chinese_name": "后旺",
        "role_type": "architect",
        "description": "架构设计师，负责架构设计、后端设计、前端设计、数据库设计",
    },
    {
        "role_name": "houfa",
        "chinese_name": "后发",
        "role_type": "programmer",
        "description": "程序员，负责建立代码编写Agent蜂群，监督蜂群完成TDD测试用例和代码编写",
    },
    {
        "role_name": "houda",
        "chinese_name": "后达",
        "role_type": "tester",
        "description": "测试员，负责建立代码测试Agent蜂群，执行全面测试",
    },
    {
        "role_name": "houfu",
        "chinese_name": "后富",
        "role_type": "cicd_engineer",
        "description": "CI/CD工程师，负责开发环境搭建和代码部署",
    },
    {
        "role_name": "hougui",
        "chinese_name": "后贵",
        "role_type": "doc_manager",
        "description": "文档管理员，负责项目文档一致性管理",
    },
    {
        "role_name": "hourong",
        "chinese_name": "后荣",
        "role_type": "qa",
        "description": "QA，检验每个Agent产出，未达标退回重做，达标放行并提交代码库",
    },
    {
        "role_name": "houhua",
        "chinese_name": "后华",
        "role_type": "security_officer",
        "description": "安全员，负责代码审计、合规审查、渗透测试、漏洞修复",
    },
]


class AgentRoleService:
    def get_role_by_name(self, role_name: str):
        for role in NAMED_ROLES:
            if role["role_name"] == role_name:
                return dict(role)
        return None

    def get_roles_by_type(self, role_type: str):
        return [dict(r) for r in NAMED_ROLES if r["role_type"] == role_type]

    def get_swarm_managers(self):
        return [dict(r) for r in NAMED_ROLES if r["role_type"] in ("programmer", "tester")]

    def get_qa_role(self):
        return self.get_role_by_name("hourong")

    def get_security_role(self):
        return self.get_role_by_name("houhua")

    def get_doc_manager_role(self):
        return self.get_role_by_name("hougui")

    def get_project_manager_role(self):
        return self.get_role_by_name("haimei")

    def get_supervisor_role(self):
        """返回海梅（Haimei）- 项目经理/全程监督者"""
        return self.get_role_by_name("haimei")

    def get_all_supervised_steps(self) -> list:
        """返回海梅需要监督的所有步骤列表"""
        from app.services.workflow_engine import get_default_steps
        return [s for s in get_default_steps() if s.supervisor_role == "haimei"]

    def get_all_executor_roles_except_haimei(self) -> list:
        """返回除海梅外的所有执行Agent角色"""
        return [dict(r) for r in NAMED_ROLES if r["role_name"] != "haimei"]

    def get_roles_managed_by_haimei(self) -> list:
        """返回海梅需要管理的所有执行Agent角色"""
        return self.get_all_executor_roles_except_haimei()

    def get_haimei_capabilities(self) -> dict:
        """返回海梅的能力描述，用于项目管理"""
        return {
            "role_name": "haimei",
            "chinese_name": "海梅",
            "role_type": "project_manager",
            "capabilities": [
                "调动所有执行Agent",
                "检查Agent健康状态",
                "恢复异常Agent",
                "步骤前置监督审查",
                "项目整体进度跟踪",
                "QA检验审核",
                "迭代流程管理",
                "异常检测与自动恢复",
            ],
            "supervised_roles": [r["role_name"] for r in NAMED_ROLES if r["role_name"] != "haimei"],
        }

    def get_all_roles(self):
        return [dict(r) for r in NAMED_ROLES]

    def is_named_role(self, role_name: str) -> bool:
        return self.get_role_by_name(role_name) is not None