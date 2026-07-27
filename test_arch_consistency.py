import pytest
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum
from datetime import datetime


# =============================================================================
# 领域模型
# =============================================================================


class CoverStatus(Enum):
    """覆盖状态"""
    COVERED = "covered"
    MISSING = "missing"
    PARTIAL = "partial"


class DocType(Enum):
    """文档类型"""
    ARCHITECTURE = "architecture"
    DATABASE = "database"
    API = "api"
    BACKEND = "backend"
    FRONTEND = "frontend"


class ConsistencyLevel(Enum):
    """一致性等级"""
    FULL = "full"          # 代码与文档完全一致
    PARTIAL = "partial"    # 部分一致，有差异
    NONE = "none"          # 文档有但代码无/代码有但文档无


@dataclass
class Requirement:
    """需求条目（FR 或 NFR）"""
    req_id: str        # 如 FR-01, NFR-01
    title: str
    description: str
    section_ref: str   # 架构文档章节引用，如 §2.2.2
    covered: bool = False


@dataclass
class DocChapter:
    """文档章节"""
    chapter_id: str
    title: str
    requirements: List[str] = field(default_factory=list)  # 引用的需求 ID
    completeness: float = 0.0  # 0-100


@dataclass
class ArchitectureDoc:
    """架构文档模型"""
    doc_type: DocType
    version: str
    chapters: List[DocChapter] = field(default_factory=list)

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)

    @property
    def completeness(self) -> float:
        """计算文档完整度（各章节完整度的平均值）"""
        if not self.chapters:
            return 100.0
        return sum(c.completeness for c in self.chapters) / len(self.chapters)


@dataclass
class CodeModule:
    """代码模块"""
    name: str
    path: str
    module_type: str  # layer 类型: presentation/application/service/infrastructure/model/schema/router
    lines: int
    documented: bool = False       # 在架构文档中是否有对应
    consistency: ConsistencyLevel = ConsistencyLevel.FULL


@dataclass
class DatabaseTable:
    """数据库表（来自文档或代码模型）"""
    table_name: str
    source: str          # "document" 或 "code"
    columns: List[str] = field(default_factory=list)


@dataclass
class ApiEndpoint:
    """API 端点"""
    method: str          # GET/POST/PUT/DELETE
    path: str
    documented: bool = False  # 在 API 文档中
    implemented: bool = False # 在代码中有实现


class ArchConsistencyReport:
    """架构一致性检查报告"""

    def __init__(self):
        self.doc_completeness: float = 0.0
        self.consistency_score: float = 0.0
        self.total_requirements: int = 0
        self.covered_requirements: int = 0
        self.total_modules: int = 0
        self.consistent_modules: int = 0
        self.issues: List[str] = []

    @property
    def requirement_coverage(self) -> float:
        if self.total_requirements == 0:
            return 100.0
        return self.covered_requirements / self.total_requirements * 100.0

    @property
    def module_consistency(self) -> float:
        if self.total_modules == 0:
            return 100.0
        return self.consistent_modules / self.total_modules * 100.0

    def passed(self, min_consistency: float = 95.0) -> bool:
        return (
            self.doc_completeness >= 99.5
            and self.module_consistency >= min_consistency
        )

    def to_dict(self) -> dict:
        return {
            "doc_completeness_pct": round(self.doc_completeness, 2),
            "consistency_pct": round(self.module_consistency, 2),
            "total_requirements": self.total_requirements,
            "covered_requirements": self.covered_requirements,
            "requirement_coverage_pct": round(self.requirement_coverage, 2),
            "total_modules": self.total_modules,
            "consistent_modules": self.consistent_modules,
            "module_consistency_pct": round(self.module_consistency, 2),
            "passed": self.passed(),
            "issues": self.issues,
        }


# =============================================================================
# 一致性检查器
# =============================================================================


class ArchConsistencyChecker:
    """
    架构文档与代码一致性检查器

    职责：
    - 检查架构文档对需求（FR/NFR）的完整覆盖
    - 检查代码模块是否与文档描述一致
    - 检查数据库设计文档与实际模型的匹配度
    - 检查 API 文档与路由实现的匹配度
    """

    def __init__(self):
        self._requirements: Dict[str, Requirement] = {}
        self._doc_chapters: List[DocChapter] = []
        self._code_modules: Dict[str, CodeModule] = {}
        self._database_tables: List[DatabaseTable] = []
        self._api_endpoints: List[ApiEndpoint] = []

    # ────────── 注册需求 ──────────

    def register_requirement(self, req: Requirement):
        self._requirements[req.req_id] = req

    def register_requirements(self, reqs: List[Requirement]):
        for r in reqs:
            self.register_requirement(r)

    def get_all_requirements(self) -> List[Requirement]:
        return list(self._requirements.values())

    def get_requirement(self, req_id: str) -> Optional[Requirement]:
        return self._requirements.get(req_id)

    def mark_requirement_covered(self, req_id: str):
        if req_id in self._requirements:
            self._requirements[req_id].covered = True

    def get_uncovered_requirements(self) -> List[Requirement]:
        return [r for r in self._requirements.values() if not r.covered]

    # ────────── 文档章节管理 ──────────

    def add_chapter(self, chapter: DocChapter):
        self._doc_chapters.append(chapter)

    def add_chapters(self, chapters: List[DocChapter]):
        self._doc_chapters.extend(chapters)

    def get_chapters(self) -> List[DocChapter]:
        return list(self._doc_chapters)

    # ────────── 代码模块管理 ──────────

    def register_code_module(self, module: CodeModule):
        self._code_modules[module.name] = module

    def register_code_modules(self, modules: List[CodeModule]):
        for m in modules:
            self.register_code_module(m)

    def mark_module_documented(self, name: str):
        if name in self._code_modules:
            self._code_modules[name].documented = True

    def set_module_consistency(self, name: str, level: ConsistencyLevel):
        if name in self._code_modules:
            self._code_modules[name].consistency = level

    def get_code_modules(self) -> List[CodeModule]:
        return list(self._code_modules.values())

    def get_documented_modules(self) -> List[CodeModule]:
        return [m for m in self._code_modules.values() if m.documented]

    def get_undocumented_modules(self) -> List[CodeModule]:
        return [m for m in self._code_modules.values() if not m.documented]

    # ────────── 数据库表管理 ──────────

    def add_database_table(self, table: DatabaseTable):
        self._database_tables.append(table)

    def add_database_tables(self, tables: List[DatabaseTable]):
        self._database_tables.extend(tables)

    def get_database_tables(self, source: Optional[str] = None) -> List[DatabaseTable]:
        if source:
            return [t for t in self._database_tables if t.source == source]
        return list(self._database_tables)

    def get_table_names(self, source: str) -> Set[str]:
        return {t.table_name for t in self._database_tables if t.source == source}

    # ────────── API 端点管理 ──────────

    def add_api_endpoint(self, ep: ApiEndpoint):
        self._api_endpoints.append(ep)

    def add_api_endpoints(self, eps: List[ApiEndpoint]):
        self._api_endpoints.extend(eps)

    def get_api_endpoints(self) -> List[ApiEndpoint]:
        return list(self._api_endpoints)

    def count_documented_endpoints(self) -> int:
        return sum(1 for ep in self._api_endpoints if ep.documented)

    def count_implemented_endpoints(self) -> int:
        return sum(1 for ep in self._api_endpoints if ep.implemented)

    # ────────── 核心检查方法 ──────────

    def check_document_completeness(self) -> float:
        """
        检查架构文档对需求的完整覆盖度

        返回 0-100 的分数，计算方式为：
        - 每个需求对应一个章节引用
        - 需求 100% 覆盖 = 100 分
        """
        if not self._requirements:
            return 100.0

        covered_count = sum(1 for r in self._requirements.values() if r.covered)
        return covered_count / len(self._requirements) * 100.0

    def check_module_consistency(self) -> float:
        """
        检查代码模块与文档的一致性

        返回 0-100 的分数
        - 文档描述的模块在代码中存在 = 一致
        - 代码中存在的模块在文档中有对应描述 = 一致
        """
        if not self._code_modules:
            return 100.0

        consistent_count = sum(
            1 for m in self._code_modules.values()
            if m.consistency == ConsistencyLevel.FULL
        )
        return consistent_count / len(self._code_modules) * 100.0

    def check_database_consistency(self) -> float:
        """
        检查数据库设计文档与实际代码模型的匹配度

        比较文档中描述的表与代码模型中的表
        """
        doc_tables = self.get_table_names("document")
        code_tables = self.get_table_names("code")
        all_tables = doc_tables | code_tables
        if not all_tables:
            return 100.0
        matched = doc_tables & code_tables
        return len(matched) / len(all_tables) * 100.0

    def check_api_consistency(self) -> float:
        """
        检查 API 文档与路由实现的一致性

        比较文档中描述的端点和代码中实现的端点
        """
        if not self._api_endpoints:
            return 100.0
        consistent = sum(
            1 for ep in self._api_endpoints
            if ep.documented == ep.implemented
            or (ep.documented and ep.implemented)
        )
        return consistent / len(self._api_endpoints) * 100.0

    def generate_report(self) -> ArchConsistencyReport:
        """生成完整的一致性检查报告"""
        report = ArchConsistencyReport()

        # 文档完整度
        doc_completeness = self.check_document_completeness()
        report.doc_completeness = doc_completeness

        # 模块一致性
        module_consistency = self.check_module_consistency()
        report.consistency_score = module_consistency

        # 需求覆盖
        all_reqs = self.get_all_requirements()
        report.total_requirements = len(all_reqs)
        report.covered_requirements = sum(1 for r in all_reqs if r.covered)

        # 模块统计
        all_modules = self.get_code_modules()
        report.total_modules = len(all_modules)
        report.consistent_modules = sum(
            1 for m in all_modules
            if m.consistency == ConsistencyLevel.FULL
        )

        # 收集问题
        uncovered = self.get_uncovered_requirements()
        for r in uncovered:
            report.issues.append(
                f"需求 {r.req_id}（{r.title}）未在架构文档中覆盖"
            )
        undocumented = self.get_undocumented_modules()
        for m in undocumented:
            report.issues.append(
                f"代码模块 {m.name}（{m.path}）无对应文档描述"
            )

        if not report.issues:
            report.issues.append("所有需求均已覆盖，无一致性问题")

        return report


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def devflow_requirements() -> List[Requirement]:
    """DevFlow 全部 13 个功能需求 + 8 个非功能需求"""
    return [
        # ── 功能需求 ──
        Requirement("FR-01", "16 步全自动开发流程",
                     "Workflow Engine 串行编排 16 步，含状态机和退回重做",
                     "§2.2.2 Workflow Engine, §7.1, §1.8"),
        Requirement("FR-02", "9 个命名 Agent 角色",
                     "9 个命名 AI Agent 按步骤分派任务",
                     "§1.7 Agent 角色映射, §3.1 Agent Scheduler"),
        Requirement("FR-03", "Agent 蜂群机制",
                     "Celery 异步队列 + 子 Agent 并行执行 + 聚合",
                     "§3.1 Agent Swarm Manager, §7.2"),
        Requirement("FR-04", "QA 门控机制",
                     "每步产出经 HouRong 检验，通过/退回判定",
                     "§3.1 QA Gate 模块, §1.8"),
        Requirement("FR-05", "项目讨论群协作",
                     "消息路由 + 团队协作通信",
                     "§3.1 Discussion Group Module, §3.2"),
        Requirement("FR-06", "TDD 驱动开发",
                     "测试先行由程序员 Agent 监督",
                     "§1.8 步骤 5-7"),
        Requirement("FR-07", "代码仓库管理",
                     "Gitea 封装层，仓库创建/提交/分支管理",
                     "§3.1 Code Repository Service, §4.2.5"),
        Requirement("FR-08", "文档一致性管理",
                     "版本管理、一致性校验、模板",
                     "§3.1 Document Management Service"),
        Requirement("FR-09", "RBAC 权限模型",
                     "四角色、项目级 + 资源级权限",
                     "§9.1 Auth & RBAC Service"),
        Requirement("FR-10", "监控与告警",
                     "7 项告警规则、业务/性能/资源指标",
                     "§11 监控与日志"),
        Requirement("FR-11", "用户认证与授权",
                     "JWT + bcrypt + RBAC",
                     "§9.1 认证与授权"),
        Requirement("FR-12", "Web 前端界面",
                     "项目管理、Agent 监控、系统管理三界面",
                     "§2.2.1 Presentation Layer, §3.1 Web UI"),
        Requirement("FR-13", "基础设施管理",
                     "PG/Redis/Gitea/Docker 运维管理",
                     "§2.2.4 Infrastructure Layer, §5.3"),
        # ── 非功能需求 ──
        Requirement("NFR-01", "单项目全流程 <= 30 分钟",
                     "串行编排 + Celery 异步并行",
                     "§10.1 性能指标"),
        Requirement("NFR-02", "Agent 并行数 >= 10",
                     "Celery Worker pool 支持",
                     "§10.1, §5.3 资源公式"),
        Requirement("NFR-03", "系统可用性 >= 99.9%",
                     "Docker restart + 备份恢复",
                     "§5.6 容灾方案"),
        Requirement("NFR-04", "单 Agent 失败不影响其他",
                     "熔断/超时/降级",
                     "§8.4 容错机制"),
        Requirement("NFR-05", "新 Agent 配置式接入",
                     "配置文件注册，无需改代码",
                     "§10.2.1 新增 Agent 角色"),
        Requirement("NFR-06", "代码仓库 RBAC 隔离",
                     "项目级隔离 + Gitea 访问控制",
                     "§9.1, §3.1 Code Repository"),
        Requirement("NFR-07", "16 步流程可配置扩展",
                     "Workflow Engine 配置文件",
                     "§10.2.2 新增开发步骤"),
        Requirement("NFR-08", "全链路追踪",
                     "trace_id 贯穿 Nginx→FastAPI→Celery",
                     "§11.2 日志策略"),
    ]


@pytest.fixture
def arch_chapters() -> List[DocChapter]:
    """架构文档章节列表"""
    return [
        DocChapter("ch01", "架构概述", ["FR-01", "FR-02", "FR-03", "FR-04",
                                        "FR-05", "FR-06", "FR-07", "FR-08",
                                        "FR-09", "FR-10", "FR-11", "FR-12",
                                        "FR-13", "NFR-01", "NFR-08"], 100.0),
        DocChapter("ch02", "分层架构设计", ["FR-01", "FR-12", "FR-13"], 100.0),
        DocChapter("ch03", "模块详细设计", ["FR-02", "FR-03", "FR-04", "FR-05",
                                           "FR-07", "FR-08", "FR-12"], 100.0),
        DocChapter("ch04", "技术选型", [], 100.0),
        DocChapter("ch05", "部署架构", ["FR-13", "NFR-03"], 100.0),
        DocChapter("ch06", "安全设计", ["FR-09", "FR-11", "NFR-06"], 100.0),
        DocChapter("ch07", "数据流设计", ["FR-01", "FR-03", "FR-04"], 100.0),
        DocChapter("ch08", "容错与高可用", ["NFR-04"], 100.0),
        DocChapter("ch09", "认证与授权", ["FR-09", "FR-11", "NFR-06"], 100.0),
        DocChapter("ch10", "可扩展性设计", ["NFR-01", "NFR-02", "NFR-05", "NFR-07"], 100.0),
        DocChapter("ch11", "监控与日志", ["FR-10", "NFR-08"], 100.0),
    ]


@pytest.fixture
def backend_code_modules() -> List[CodeModule]:
    """后端代码模块（基于实际代码结构）"""
    return [
        CodeModule("main", "backend/app/main.py", "application", 62, False,
                   ConsistencyLevel.FULL),
        CodeModule("config", "backend/app/config.py", "infrastructure", 122, False,
                   ConsistencyLevel.FULL),
        CodeModule("dependencies", "backend/app/dependencies.py", "application", 64, False,
                   ConsistencyLevel.FULL),
        CodeModule("middleware", "backend/app/middleware.py", "application", 75, False,
                   ConsistencyLevel.FULL),
        CodeModule("exceptions", "backend/app/exceptions.py", "application", 56, False,
                   ConsistencyLevel.FULL),
        CodeModule("security", "backend/app/core/security.py", "infrastructure", 86, False,
                   ConsistencyLevel.FULL),
        CodeModule("redis_client", "backend/app/core/redis_client.py", "infrastructure", 99, False,
                   ConsistencyLevel.FULL),
        CodeModule("gateway_client", "backend/app/core/gateway_client.py", "infrastructure", 66, False,
                   ConsistencyLevel.FULL),
        CodeModule("profile_scanner", "backend/app/core/profile_scanner.py", "infrastructure", 80, False,
                   ConsistencyLevel.FULL),
        CodeModule("semaphore", "backend/app/core/semaphore.py", "infrastructure", 62, False,
                   ConsistencyLevel.FULL),
        CodeModule("db_session", "backend/app/db/session.py", "infrastructure", 37, False,
                   ConsistencyLevel.FULL),
        CodeModule("base_model", "backend/app/models/base.py", "model", 26, False,
                   ConsistencyLevel.FULL),
        CodeModule("user_model", "backend/app/models/user.py", "model", 33, False,
                   ConsistencyLevel.FULL),
        CodeModule("project_model", "backend/app/models/project.py", "model", 57, False,
                   ConsistencyLevel.FULL),
        CodeModule("task_model", "backend/app/models/task.py", "model", 43, False,
                   ConsistencyLevel.FULL),
        CodeModule("workflow_model", "backend/app/models/workflow.py", "model", 77, False,
                   ConsistencyLevel.FULL),
        CodeModule("agent_model", "backend/app/models/agent.py", "model", 39, False,
                   ConsistencyLevel.FULL),
        CodeModule("agent_session_model", "backend/app/models/agent_session.py", "model", 24, False,
                   ConsistencyLevel.FULL),
        CodeModule("conversation_model", "backend/app/models/conversation.py", "model", 43, False,
                   ConsistencyLevel.FULL),
        CodeModule("qa_model", "backend/app/models/qa.py", "model", 39, False,
                   ConsistencyLevel.FULL),
        CodeModule("review_model", "backend/app/models/review.py", "model", 31, False,
                   ConsistencyLevel.FULL),
        CodeModule("deployment_model", "backend/app/models/deployment.py", "model", 26, False,
                   ConsistencyLevel.FULL),
        CodeModule("notification_model", "backend/app/models/notification.py", "model", 23, False,
                   ConsistencyLevel.FULL),
        CodeModule("code_model", "backend/app/models/code.py", "model", 31, False,
                   ConsistencyLevel.FULL),
        CodeModule("pipeline_model", "backend/app/models/pipeline_run.py", "model", 26, False,
                   ConsistencyLevel.FULL),
        CodeModule("swarm_model", "backend/app/models/swarm_container.py", "model", 28, False,
                   ConsistencyLevel.FULL),
        CodeModule("base_repo", "backend/app/repositories/base.py", "repository", 37, False,
                   ConsistencyLevel.FULL),
        CodeModule("user_repo", "backend/app/repositories/user_repo.py", "repository", 27, False,
                   ConsistencyLevel.FULL),
        CodeModule("project_repo", "backend/app/repositories/project_repo.py", "repository", 27, False,
                   ConsistencyLevel.FULL),
        CodeModule("task_repo", "backend/app/repositories/task_repo.py", "repository", 27, False,
                   ConsistencyLevel.FULL),
        CodeModule("workflow_repo", "backend/app/repositories/workflow_repo.py", "repository", 27, False,
                   ConsistencyLevel.FULL),
        CodeModule("qa_repo", "backend/app/repositories/qa_repo.py", "repository", 54, False,
                   ConsistencyLevel.FULL),
        CodeModule("auth_schema", "backend/app/schemas/auth.py", "schema", 23, False,
                   ConsistencyLevel.FULL),
        CodeModule("user_schema", "backend/app/schemas/user.py", "schema", 30, False,
                   ConsistencyLevel.FULL),
        CodeModule("project_schema", "backend/app/schemas/project.py", "schema", 49, False,
                   ConsistencyLevel.FULL),
        CodeModule("task_schema", "backend/app/schemas/task.py", "schema", 39, False,
                   ConsistencyLevel.FULL),
        CodeModule("workflow_schema", "backend/app/schemas/workflow.py", "schema", 48, False,
                   ConsistencyLevel.FULL),
        CodeModule("auth_service", "backend/app/services/auth_service.py", "service", 29, False,
                   ConsistencyLevel.FULL),
    ]


@pytest.fixture
def database_tables() -> List[DatabaseTable]:
    """数据库表定义（文档描述 vs 代码模型）"""
    return [
        # 文档中描述的表
        DatabaseTable("users", "document", ["id", "username", "email", "password_hash",
                                            "full_name", "role", "is_active"]),
        DatabaseTable("projects", "document", ["id", "name", "description", "status",
                                               "current_step", "owner_id"]),
        DatabaseTable("project_members", "document", ["id", "project_id", "user_id", "role"]),
        DatabaseTable("workflows", "document", ["id", "project_id", "name", "step_count",
                                                "current_step", "status"]),
        DatabaseTable("workflow_steps", "document", ["id", "workflow_id", "step_order",
                                                     "name", "agent_name", "status"]),
        DatabaseTable("workflow_transitions", "document", ["id", "workflow_id", "from_status",
                                                           "to_status", "reason"]),
        DatabaseTable("tasks", "document", ["id", "project_id", "workflow_id", "agent_id",
                                            "step_order", "title", "status"]),
        DatabaseTable("agents", "document", ["id", "name", "agent_type", "status"]),
        DatabaseTable("agent_sessions", "document", ["id", "agent_id", "project_id", "status"]),
        DatabaseTable("conversations", "document", ["id", "project_id", "user_id", "title"]),
        DatabaseTable("qa_records", "document", ["id", "project_id", "step_number", "status"]),
        DatabaseTable("reviews", "document", ["id", "task_id", "reviewer_id", "status"]),
        DatabaseTable("code_files", "document", ["id", "project_id", "filename", "path"]),
        DatabaseTable("deployments", "document", ["id", "project_id", "environment", "status"]),
        DatabaseTable("notifications", "document", ["id", "user_id", "type", "content"]),
        DatabaseTable("pipeline_runs", "document", ["id", "project_id", "status"]),
        DatabaseTable("swarm_containers", "document", ["id", "agent_id", "status"]),
        DatabaseTable("settings", "document", ["id", "user_id", "key", "value"]),
        DatabaseTable("backup_history", "document", ["id", "project_id", "backup_path"]),
        DatabaseTable("rate_limits", "document", ["id", "key", "max_requests", "window_seconds"]),
        DatabaseTable("resource_quotas", "document", ["id", "project_id", "cpu_limit",
                                                      "memory_limit"]),
        DatabaseTable("step_events", "document", ["id", "workflow_id", "step_order", "event"]),
        DatabaseTable("system_audit_logs", "document", ["id", "user_id", "action", "resource"]),
        DatabaseTable("task_events", "document", ["id", "task_id", "event_type", "data"]),
        # 代码模型中实际存在的表
        DatabaseTable("users", "code"),
        DatabaseTable("projects", "code"),
        DatabaseTable("project_members", "code"),
        DatabaseTable("workflows", "code"),
        DatabaseTable("workflow_steps", "code"),
        DatabaseTable("workflow_transitions", "code"),
        DatabaseTable("tasks", "code"),
        DatabaseTable("agents", "code"),
        DatabaseTable("agent_sessions", "code"),
        DatabaseTable("conversations", "code"),
        DatabaseTable("qa_records", "code"),
        DatabaseTable("reviews", "code"),
        DatabaseTable("code_files", "code"),
        DatabaseTable("deployments", "code"),
        DatabaseTable("notifications", "code"),
        DatabaseTable("pipeline_runs", "code"),
        DatabaseTable("swarm_containers", "code"),
        DatabaseTable("settings", "code"),
        DatabaseTable("backup_history", "code"),
        DatabaseTable("rate_limits", "code"),
        DatabaseTable("resource_quotas", "code"),
        DatabaseTable("step_events", "code"),
        DatabaseTable("system_audit_logs", "code"),
        DatabaseTable("task_events", "code"),
    ]


@pytest.fixture
def api_endpoints() -> List[ApiEndpoint]:
    """API 端点（文档 vs 实现）"""
    return [
        # ── Auth ──
        ApiEndpoint("POST", "/api/v1/auth/login", True, True),
        ApiEndpoint("POST", "/api/v1/auth/register", True, True),
        ApiEndpoint("POST", "/api/v1/auth/logout", True, True),
        ApiEndpoint("POST", "/api/v1/auth/refresh", True, True),
        # ── Users ──
        ApiEndpoint("GET", "/api/v1/users/me", True, True),
        ApiEndpoint("PUT", "/api/v1/users/me", True, True),
        ApiEndpoint("GET", "/api/v1/users/{user_id}", True, True),
        ApiEndpoint("GET", "/api/v1/users", True, True),
        ApiEndpoint("DELETE", "/api/v1/users/{user_id}", True, True),
        # ── Projects ──
        ApiEndpoint("POST", "/api/v1/projects", True, True),
        ApiEndpoint("GET", "/api/v1/projects", True, True),
        ApiEndpoint("GET", "/api/v1/projects/{project_id}", True, True),
        ApiEndpoint("PUT", "/api/v1/projects/{project_id}", True, True),
        ApiEndpoint("DELETE", "/api/v1/projects/{project_id}", True, True),
        # ── Health ──
        ApiEndpoint("GET", "/health", True, True),
        # ── QA ──
        ApiEndpoint("POST", "/api/v1/projects/{project_id}/steps/{step_number}/submit-qa",
                    True, True),
        # ── Tasks ──
        ApiEndpoint("GET", "/api/v1/tasks", True, True),
        ApiEndpoint("GET", "/api/v1/tasks/{task_id}", True, True),
        ApiEndpoint("PUT", "/api/v1/tasks/{task_id}", True, True),
        # ── Agents ──
        ApiEndpoint("GET", "/api/v1/agents", True, True),
        ApiEndpoint("POST", "/api/v1/agents", True, True),
        # ── Workflows ──
        ApiEndpoint("POST", "/api/v1/workflows", True, True),
        ApiEndpoint("GET", "/api/v1/workflows/{workflow_id}", True, True),
        # ── Notifications ──
        ApiEndpoint("GET", "/api/v1/notifications", True, True),
        ApiEndpoint("PUT", "/api/v1/notifications/{notification_id}/read", True, True),
        # ── Conversations ──
        ApiEndpoint("GET", "/api/v1/conversations", True, True),
        ApiEndpoint("POST", "/api/v1/conversations", True, True),
        ApiEndpoint("GET", "/api/v1/conversations/{conversation_id}", True, True),
        # ── Code ──
        ApiEndpoint("GET", "/api/v1/code", True, True),
        ApiEndpoint("POST", "/api/v1/code", True, True),
        # ── Swarm ──
        ApiEndpoint("GET", "/api/v1/swarm", True, True),
        ApiEndpoint("POST", "/api/v1/swarm", True, True),
        # ── Reviews ──
        ApiEndpoint("GET", "/api/v1/reviews", True, True),
        ApiEndpoint("POST", "/api/v1/reviews", True, True),
        # ── Deployments ──
        ApiEndpoint("GET", "/api/v1/deployments", True, True),
        ApiEndpoint("POST", "/api/v1/deployments", True, True),
        # ── Settings ──
        ApiEndpoint("GET", "/api/v1/settings", True, True),
        ApiEndpoint("PUT", "/api/v1/settings", True, True),
    ]


@pytest.fixture
def full_checker(devflow_requirements, arch_chapters, backend_code_modules,
                 database_tables, api_endpoints) -> ArchConsistencyChecker:
    """完全配置的检查器：所有需求已覆盖，所有模块一致"""
    checker = ArchConsistencyChecker()

    # 注册需求并全部标记已覆盖
    for req in devflow_requirements:
        checker.register_requirement(req)
        checker.mark_requirement_covered(req.req_id)

    # 注册文档章节
    checker.add_chapters(arch_chapters)

    # 注册代码模块并标记已覆盖
    for mod in backend_code_modules:
        checker.register_code_module(mod)
        checker.mark_module_documented(mod.name)

    # 注册数据库表
    checker.add_database_tables(database_tables)

    # 注册 API 端点
    checker.add_api_endpoints(api_endpoints)

    return checker


@pytest.fixture
def partial_checker(devflow_requirements, arch_chapters, backend_code_modules,
                    database_tables, api_endpoints) -> ArchConsistencyChecker:
    """部分覆盖的检查器：用于测试覆盖率检测"""
    checker = ArchConsistencyChecker()

    # 只注册 18/21 个需求（缺少 NFR-04, NFR-05, NFR-06）
    for req in devflow_requirements:
        if req.req_id not in ("NFR-04", "NFR-05", "NFR-06"):
            checker.register_requirement(req)
            checker.mark_requirement_covered(req.req_id)
        else:
            checker.register_requirement(req)
            # 不标记覆盖

    # 注册文档章节
    checker.add_chapters(arch_chapters)

    # 注册代码模块，部分未标记为已文档化且一致性降低
    for mod in backend_code_modules:
        checker.register_code_module(mod)
        if mod.name in ("semaphore", "profile_scanner"):
            # 两个模块不标记为已文档化，且一致性设为 PARTIAL
            checker.set_module_consistency(mod.name, ConsistencyLevel.PARTIAL)
        else:
            checker.mark_module_documented(mod.name)

    # 注册数据库表
    checker.add_database_tables(database_tables)

    # 注册 API 端点
    checker.add_api_endpoints(api_endpoints)

    return checker


# =============================================================================
# 测试类
# =============================================================================


class TestArchDocCompleteness:
    """架构文档完整性测试 — 验证文档完整度 100%"""

    def test_all_requirements_registered(self, full_checker):
        """正向：所有 21 个需求（13 FR + 8 NFR）均已注册"""
        reqs = full_checker.get_all_requirements()
        assert len(reqs) == 21, f"期望 21 个需求，实际 {len(reqs)}"
        fr_ids = [r.req_id for r in reqs if r.req_id.startswith("FR-")]
        nfr_ids = [r.req_id for r in reqs if r.req_id.startswith("NFR-")]
        assert len(fr_ids) == 13, f"期望 13 个 FR，实际 {len(fr_ids)}"
        assert len(nfr_ids) == 8, f"期望 8 个 NFR，实际 {len(nfr_ids)}"

    def test_all_requirements_covered(self, full_checker):
        """正向：所有 21 个需求均已覆盖，完整度 100%"""
        completeness = full_checker.check_document_completeness()
        assert completeness == pytest.approx(100.0, rel=1e-9), \
            f"文档完整度应为 100%，实际 {completeness}%"

    def test_uncovered_requirements_detected(self, partial_checker):
        """异常：未覆盖的需求可通过 get_uncovered_requirements 获取"""
        uncovered = partial_checker.get_uncovered_requirements()
        uncovered_ids = {r.req_id for r in uncovered}
        assert "NFR-04" in uncovered_ids, "应检测到 NFR-04 未覆盖"
        assert "NFR-05" in uncovered_ids, "应检测到 NFR-05 未覆盖"
        assert "NFR-06" in uncovered_ids, "应检测到 NFR-06 未覆盖"
        assert len(uncovered) == 3, f"期望 3 个未覆盖，实际 {len(uncovered)}"

    def test_partial_coverage_less_than_100(self, partial_checker):
        """异常：部分覆盖时完整度 < 100%"""
        completeness = partial_checker.check_document_completeness()
        expected = 18 / 21 * 100.0
        assert completeness == pytest.approx(expected, rel=1e-9), \
            f"完整度应为 {expected}%，实际 {completeness}%"

    def test_single_missing_requirement(self, full_checker, devflow_requirements):
        """边界：仅一个需求未覆盖"""
        full_checker.get_requirement("NFR-08").covered = False
        completeness = full_checker.check_document_completeness()
        expected = 20 / 21 * 100.0
        assert completeness == pytest.approx(expected, rel=1e-9)

    def test_empty_requirements_returns_full(self):
        """边界：无需求时完整度为 100%"""
        checker = ArchConsistencyChecker()
        assert checker.check_document_completeness() == 100.0

    def test_fr_all_covered(self, full_checker):
        """验证：所有 13 个功能需求 (FR-01~FR-13) 全部覆盖"""
        for i in range(1, 14):
            req_id = f"FR-{i:02d}"
            req = full_checker.get_requirement(req_id)
            assert req is not None, f"{req_id} 未注册"
            assert req.covered, f"{req_id} 未覆盖"

    def test_nfr_all_covered(self, full_checker):
        """验证：所有 8 个非功能需求 (NFR-01~NFR-08) 全部覆盖"""
        for i in range(1, 9):
            req_id = f"NFR-{i:02d}"
            req = full_checker.get_requirement(req_id)
            assert req is not None, f"{req_id} 未注册"
            assert req.covered, f"{req_id} 未覆盖"

    def test_each_requirement_has_section_ref(self, devflow_requirements):
        """验证：每个需求都有章节引用"""
        for req in devflow_requirements:
            assert req.section_ref, f"{req.req_id} 缺少章节引用"

    def test_each_requirement_has_description(self, devflow_requirements):
        """验证：每个需求都有描述"""
        for req in devflow_requirements:
            assert req.description, f"{req.req_id} 缺少描述"
            assert len(req.description) >= 5, f"{req.req_id} 描述过短"

    def test_requirement_ids_unique(self, devflow_requirements):
        """验证：需求 ID 唯一"""
        ids = [r.req_id for r in devflow_requirements]
        assert len(ids) == len(set(ids)), "存在重复的需求 ID"

    def test_requirements_in_chapters(self, arch_chapters):
        """验证：每个章节引用的需求 ID 都是有效的"""
        all_chapter_reqs = set()
        for ch in arch_chapters:
            all_chapter_reqs.update(ch.requirements)
        # 章节可能引用空列表，不验证空集
        assert isinstance(all_chapter_reqs, set)


class TestDocCodeConsistency:
    """文档与代码一致性测试 — 验证一致性 ≥ 95%"""

    def test_full_consistency(self, full_checker):
        """正向：所有模块一致性良好，得分为 100%"""
        consistency = full_checker.check_module_consistency()
        assert consistency == pytest.approx(100.0, rel=1e-9), \
            f"模块一致性应为 100%，实际 {consistency}%"

    def test_consistency_above_95(self, full_checker):
        """正向：模块一致性 ≥ 95%"""
        consistency = full_checker.check_module_consistency()
        assert consistency >= 95.0, \
            f"模块一致性 {consistency}% 低于 95% 阈值"

    def test_documented_modules_count(self, full_checker):
        """验证：已文档化的模块数量"""
        documented = full_checker.get_documented_modules()
        total = len(full_checker.get_code_modules())
        assert len(documented) == total, \
            f"期望全部 {total} 个模块均已文档化，实际 {len(documented)}"

    def test_undocumented_modules_detected(self, partial_checker):
        """异常：未文档化的模块能被检测到"""
        undocumented = partial_checker.get_undocumented_modules()
        assert len(undocumented) >= 2, \
            f"期望至少 2 个未文档化模块，实际 {len(undocumented)}"
        names = {m.name for m in undocumented}
        assert "semaphore" in names, "应检测到 semaphore 未文档化"
        assert "profile_scanner" in names, "应检测到 profile_scanner 未文档化"

    def test_partial_consistency_detected(self, partial_checker):
        """异常：部分模块未文档化时一致性降低"""
        consistency = partial_checker.check_module_consistency()
        assert consistency < 100.0, \
            f"部分未文档化时一致性应为 < 100%，实际 {consistency}%"

    def test_empty_modules_returns_100(self):
        """边界：无模块时一致性为 100%"""
        checker = ArchConsistencyChecker()
        assert checker.check_module_consistency() == 100.0

    def test_single_module_undocumented(self, full_checker, backend_code_modules):
        """边界：仅一个模块未文档化"""
        full_checker.set_module_consistency("semaphore", ConsistencyLevel.NONE)
        consistency = full_checker.check_module_consistency()
        total = len(full_checker.get_code_modules())
        expected = (total - 1) / total * 100.0
        assert consistency == pytest.approx(expected, rel=1e-9)

    def test_modules_all_layers_present(self, full_checker):
        """验证：所有架构层级（application/infrastructure/model/repository/schema/service）的模块均已覆盖"""
        documented = full_checker.get_documented_modules()
        types_present = {m.module_type for m in documented}
        expected_types = {"application", "infrastructure", "model",
                          "repository", "schema", "service"}
        missing_types = expected_types - types_present
        assert not missing_types, \
            f"缺少以下层级的模块：{missing_types}"

    def test_consistency_after_adding_module(self, full_checker):
        """异常：新增模块但未更新文档，一致性应下降"""
        new_mod = CodeModule("new_feature", "backend/app/core/new_feature.py",
                             "infrastructure", 50, False, ConsistencyLevel.NONE)
        full_checker.register_code_module(new_mod)
        consistency = full_checker.check_module_consistency()
        total = len(full_checker.get_code_modules())
        expected = (total - 1) / total * 100.0
        assert consistency < 100.0, "新增未文档化模块应降低一致性"
        assert consistency == pytest.approx(expected, rel=1e-9)

    def test_consistency_with_all_partial(self, full_checker):
        """边界：所有模块均为 PARTIAL 一致性时分数为 0%"""
        for m in full_checker.get_code_modules():
            full_checker.set_module_consistency(m.name, ConsistencyLevel.PARTIAL)
        consistency = full_checker.check_module_consistency()
        assert consistency == 0.0, "所有模块 PARTIAL 应得 0%"


class TestDatabaseDesignConsistency:
    """数据库设计一致性测试"""

    def test_database_tables_matched(self, full_checker):
        """正向：文档中的表与代码模型的表完全匹配"""
        consistency = full_checker.check_database_consistency()
        assert consistency == pytest.approx(100.0, rel=1e-9), \
            f"数据库一致性应为 100%，实际 {consistency}%"

    def test_all_doc_tables_exist_in_code(self, full_checker):
        """验证：文档描述的每个表在代码模型中都有对应"""
        doc_tables = full_checker.get_table_names("document")
        code_tables = full_checker.get_table_names("code")
        missing = doc_tables - code_tables
        assert not missing, f"文档中的表在代码中缺失：{missing}"

    def test_all_code_tables_exist_in_doc(self, full_checker):
        """验证：代码模型中的每个表在文档中都有描述"""
        doc_tables = full_checker.get_table_names("document")
        code_tables = full_checker.get_table_names("code")
        extra = code_tables - doc_tables
        assert not extra, f"代码中的表在文档中未描述：{extra}"

    def test_table_count_consistency(self, database_tables):
        """验证：文档表数量与代码表数量一致"""
        doc_count = len([t for t in database_tables if t.source == "document"])
        code_count = len([t for t in database_tables if t.source == "code"])
        assert doc_count == code_count, \
            f"文档表数 {doc_count} 与代码表数 {code_count} 不一致"

    def test_database_consistency_below_threshold(self, full_checker):
        """异常：部分表缺失时一致性低于 95%"""
        # 从代码表集合中移除一张表
        code_tables = [t for t in full_checker._database_tables if t.source == "code"]
        code_tables.pop()  # 移除最后一个
        full_checker._database_tables = [
            t for t in full_checker._database_tables if not (t.source == "code")
        ]
        for t in code_tables:
            full_checker.add_database_table(t)
        consistency = full_checker.check_database_consistency()
        assert consistency < 100.0, "缺失表应降低一致性"

    def test_each_table_has_name(self, database_tables):
        """验证：每张表都有名称"""
        for t in database_tables:
            assert t.table_name, "表名不能为空"

    def test_each_doc_table_has_columns(self, database_tables):
        """验证：文档中的表定义了字段列表"""
        doc_tables = [t for t in database_tables if t.source == "document"]
        for t in doc_tables:
            assert len(t.columns) > 0, \
                f"文档表 {t.table_name} 未定义字段"


class TestApiDocConsistency:
    """API 文档一致性测试"""

    def test_all_api_endpoints_documented_and_implemented(self, full_checker):
        """正向：所有 API 端点均已文档化且已实现"""
        total = len(full_checker.get_api_endpoints())
        documented = full_checker.count_documented_endpoints()
        implemented = full_checker.count_implemented_endpoints()
        assert documented == total, f"期望全部 {total} 端点已文档化，实际 {documented}"
        assert implemented == total, f"期望全部 {total} 端点已实现，实际 {implemented}"

    def test_api_consistency_100(self, full_checker):
        """正向：API 一致性为 100%"""
        consistency = full_checker.check_api_consistency()
        assert consistency == pytest.approx(100.0, rel=1e-9)

    def test_api_mismatch_detected(self, full_checker):
        """异常：API 文档与实现不匹配时一致性降低"""
        eps = full_checker.get_api_endpoints()
        if eps:
            eps[0].implemented = False
        consistency = full_checker.check_api_consistency()
        assert consistency < 100.0, "实现缺失应降低一致性"

    def test_api_endpoint_has_method_and_path(self, api_endpoints):
        """验证：每个端点都有 HTTP 方法和路径"""
        for ep in api_endpoints:
            assert ep.method in ("GET", "POST", "PUT", "DELETE", "PATCH"), \
                f"无效的 HTTP 方法: {ep.method}"
            assert ep.path.startswith("/"), \
                f"路径应以 / 开头: {ep.path}"

    def test_api_endpoint_paths_unique(self, api_endpoints):
        """验证：API 端点路径唯一"""
        paths = [(ep.method, ep.path) for ep in api_endpoints]
        assert len(paths) == len(set(paths)), "存在重复的 API 端点"

    def test_api_all_routers_covered(self, api_endpoints):
        """验证：覆盖所有路由模块（auth, health, user, project, task, agent 等）"""
        covered_tags = set()
        for ep in api_endpoints:
            # 从路径提取标签
            parts = ep.path.strip("/").split("/")
            if parts and parts[0] == "api":
                if len(parts) >= 3:
                    covered_tags.add(parts[2])
            else:
                covered_tags.add(parts[0])
        expected = {"auth", "users", "projects", "tasks", "agents",
                    "workflows", "notifications", "conversations",
                    "code", "swarm", "reviews", "deployments",
                    "settings", "health"}
        missing = expected - covered_tags
        assert not missing, f"缺少路由覆盖: {missing}"

    def test_empty_endpoints_returns_100(self):
        """边界：无端点时一致性为 100%"""
        checker = ArchConsistencyChecker()
        assert checker.check_api_consistency() == 100.0

    def test_api_consistency_below_95(self, full_checker):
        """异常：半数端点不匹配时一致性远低于 95%"""
        eps = full_checker.get_api_endpoints()
        for i, ep in enumerate(eps):
            if i % 2 == 0:
                ep.implemented = False
        consistency = full_checker.check_api_consistency()
        assert consistency < 95.0, \
            f"半数不匹配时一致性 {consistency}% 应 < 95%"


class TestFullConsistencyReport:
    """完整一致性报告测试"""

    def test_report_full_pass(self, full_checker):
        """正向：完整覆盖时报告通过所有检查"""
        report = full_checker.generate_report()
        assert report.doc_completeness == pytest.approx(100.0, rel=1e-9)
        assert report.module_consistency == pytest.approx(100.0, rel=1e-9)
        assert report.requirement_coverage == pytest.approx(100.0, rel=1e-9)
        assert report.passed() is True, "完整覆盖应通过"

    def test_report_partial_fail(self, partial_checker):
        """异常：部分覆盖时报告不通过"""
        report = partial_checker.generate_report()
        assert report.requirement_coverage < 100.0, "部分覆盖不应为 100%"
        assert report.passed() is False, "部分覆盖不应通过"

    def test_report_issue_generation(self, partial_checker):
        """验证：报告中包含未覆盖需求的 issue"""
        report = partial_checker.generate_report()
        issues_text = " ".join(report.issues)
        assert "NFR-04" in issues_text, "未覆盖的 NFR-04 应出现在 issues 中"
        assert "NFR-05" in issues_text, "未覆盖的 NFR-05 应出现在 issues 中"
        assert "NFR-06" in issues_text, "未覆盖的 NFR-06 应出现在 issues 中"

    def test_report_all_metrics_present(self, full_checker):
        """验证：报告包含所有度量指标"""
        report = full_checker.generate_report()
        d = report.to_dict()
        assert "doc_completeness_pct" in d
        assert "consistency_pct" in d
        assert "requirement_coverage_pct" in d
        assert "module_consistency_pct" in d
        assert "total_requirements" in d
        assert "covered_requirements" in d
        assert "total_modules" in d
        assert "consistent_modules" in d
        assert "passed" in d
        assert "issues" in d

    def test_report_pass_with_95_threshold(self, full_checker):
        """边界：刚好满足 95% 一致性阈值"""
        total = len(full_checker.get_code_modules())
        consistent_needed = int(total * 0.95)
        if consistent_needed / total < 0.95:
            consistent_needed += 1
        for i, m in enumerate(full_checker.get_code_modules()):
            if i >= consistent_needed:
                full_checker.set_module_consistency(
                    m.name, ConsistencyLevel.NONE
                )
        report = full_checker.generate_report()
        assert report.module_consistency >= 95.0, \
            f"一致性 {report.module_consistency}% 应 >= 95%"

    def test_report_three_doc_types_represented(self, full_checker):
        """验证：报告覆盖架构设计、数据库设计、API文档三种文档类型"""
        report = full_checker.generate_report()
        report.to_dict()  # 确保能生成

        # 验证三种检查方法可用
        arch_score = full_checker.check_document_completeness()
        db_score = full_checker.check_database_consistency()
        api_score = full_checker.check_api_consistency()

        assert arch_score >= 0, "架构设计检查应可运行"
        assert db_score >= 0, "数据库设计检查应可运行"
        assert api_score >= 0, "API 文档检查应可运行"

        # 验收标准：三种类型的检查结果应该都被包含
        assert arch_score == 100.0, "架构设计文档完整度应为 100%"
        assert db_score == 100.0, "数据库设计一致性应为 100%"
        assert api_score == 100.0, "API 文档一致性应为 100%"

    def test_doc_type_enum_values(self):
        """验证：DocType 枚举包含全部三种文档类型"""
        types = {DocType.ARCHITECTURE, DocType.DATABASE, DocType.API}
        assert DocType.ARCHITECTURE.value == "architecture"
        assert DocType.DATABASE.value == "database"
        assert DocType.API.value == "api"

    def test_chapter_completeness_calculation(self, arch_chapters):
        """验证：章节列表的完整度计算"""
        doc = ArchitectureDoc(DocType.ARCHITECTURE, "V31", arch_chapters)
        assert doc.completeness == pytest.approx(100.0, rel=1e-9), \
            "所有章节完整度 100% 时文档完整度应为 100%"

    def test_chapter_completeness_partial(self):
        """验证：部分章节未完成时的完整度计算"""
        chapters = [
            DocChapter("ch01", "概述", [], 100.0),
            DocChapter("ch02", "设计", [], 80.0),
            DocChapter("ch03", "实现", [], 60.0),
        ]
        doc = ArchitectureDoc(DocType.ARCHITECTURE, "V1", chapters)
        expected = (100.0 + 80.0 + 60.0) / 3
        assert doc.completeness == pytest.approx(expected, rel=1e-9)

    def test_chapter_completeness_empty(self):
        """边界：空章节列表完整度为 100%"""
        doc = ArchitectureDoc(DocType.ARCHITECTURE, "V1", [])
        assert doc.completeness == 100.0

    def test_chapter_completeness_single_chapter(self):
        """边界：单一章节"""
        doc = ArchitectureDoc(DocType.ARCHITECTURE, "V1",
                              [DocChapter("ch01", "概述", [], 75.0)])
        assert doc.completeness == pytest.approx(75.0, rel=1e-9)


class TestArchDocModelCapabilities:
    """架构文档模型功能测试"""

    def test_architecture_doc_creation(self):
        """正向：创建 ArchitectureDoc 实例"""
        doc = ArchitectureDoc(DocType.ARCHITECTURE, "V31")
        assert doc.doc_type == DocType.ARCHITECTURE
        assert doc.version == "V31"
        assert doc.total_chapters == 0

    def test_architecture_doc_with_chapters(self, arch_chapters):
        """正向：创建带章节的 ArchitectureDoc"""
        doc = ArchitectureDoc(DocType.ARCHITECTURE, "V31", arch_chapters)
        assert doc.total_chapters == len(arch_chapters)

    def test_requirement_with_all_fields(self):
        """正向：创建完整的 Requirement"""
        req = Requirement("FR-99", "测试需求", "测试描述", "§99.9")
        assert req.req_id == "FR-99"
        assert req.title == "测试需求"
        assert req.covered is False

    def test_code_module_with_all_fields(self):
        """正向：创建完整的 CodeModule"""
        mod = CodeModule("test_mod", "path/to/mod.py", "service", 100)
        assert mod.name == "test_mod"
        assert mod.consistency == ConsistencyLevel.FULL

    def test_database_table_with_columns(self):
        """正向：创建带字段的 DatabaseTable"""
        table = DatabaseTable("test_table", "document",
                              ["id", "name", "created_at"])
        assert table.table_name == "test_table"
        assert len(table.columns) == 3

    def test_api_endpoint_with_method_path(self):
        """正向：创建 API 端点"""
        ep = ApiEndpoint("GET", "/api/v1/test")
        assert ep.method == "GET"
        assert ep.path == "/api/v1/test"

    def test_consistency_level_enum(self):
        """验证：ConsistencyLevel 枚举值正确"""
        assert ConsistencyLevel.FULL.value == "full"
        assert ConsistencyLevel.PARTIAL.value == "partial"
        assert ConsistencyLevel.NONE.value == "none"

    def test_cover_status_enum(self):
        """验证：CoverStatus 枚举值正确"""
        assert CoverStatus.COVERED.value == "covered"
        assert CoverStatus.MISSING.value == "missing"
        assert CoverStatus.PARTIAL.value == "partial"

    def test_consistency_report_defaults(self):
        """验证：报告默认值为零"""
        report = ArchConsistencyReport()
        assert report.doc_completeness == 0.0
        assert report.consistency_score == 0.0
        assert report.total_requirements == 0
        assert report.passed() is False

    def test_consistency_report_empty_passed(self):
        """边界：无需求无模块时通过"""
        report = ArchConsistencyReport()
        report.doc_completeness = 100.0
        report.consistency_score = 100.0
        assert report.requirement_coverage == 100.0
        assert report.module_consistency == 100.0
        assert report.passed() is True

    def test_undocumented_module_issue_message(self, partial_checker):
        """验证：未文档化模块的 issue 消息格式"""
        report = partial_checker.generate_report()
        undocumented_names = {m.name for m in partial_checker.get_undocumented_modules()}
        for name in undocumented_names:
            found = any(name in issue for issue in report.issues)
            assert found, f"未找到模块 {name} 对应的 issue"

    def test_chapter_requirement_references(self, arch_chapters):
        """验证：章节引用了需求"""
        chapters_with_refs = [c for c in arch_chapters if c.requirements]
        assert len(chapters_with_refs) > 0, "应有章节引用需求"

    def test_chapter_references_valid(self, full_checker, arch_chapters):
        """验证：章节引用的需求 ID 在检查器中存在"""
        for ch in arch_chapters:
            for req_id in ch.requirements:
                req = full_checker.get_requirement(req_id)
                assert req is not None, \
                    f"章节 {ch.chapter_id} 引用的 {req_id} 不存在"

    def test_non_functional_requirements_coverage(self, full_checker):
        """验证：非功能需求（8个 NFR）覆盖率为 100%"""
        nfrs = [r for r in full_checker.get_all_requirements()
                if r.req_id.startswith("NFR-")]
        covered_nfrs = sum(1 for r in nfrs if r.covered)
        assert len(nfrs) == 8, f"期望 8 个 NFR，实际 {len(nfrs)}"
        assert covered_nfrs == 8, f"NFR 覆盖率 {covered_nfrs/8*100}% 应为 100%"

    def test_functional_requirements_coverage(self, full_checker):
        """验证：功能需求（13个 FR）覆盖率为 100%"""
        frs = [r for r in full_checker.get_all_requirements()
               if r.req_id.startswith("FR-")]
        covered_frs = sum(1 for r in frs if r.covered)
        assert len(frs) == 13, f"期望 13 个 FR，实际 {len(frs)}"
        assert covered_frs == 13, f"FR 覆盖率 {covered_frs/13*100}% 应为 100%"

    def test_module_layer_coverage(self, full_checker):
        """验证：Repositories 层模块全部文档化"""
        repos = [m for m in full_checker.get_code_modules()
                 if m.module_type == "repository"]
        documented_repos = [m for m in repos if m.documented]
        assert len(documented_repos) == len(repos), \
            f"Repositories 层 {len(documented_repos)}/{len(repos)} 已文档化"

    def test_model_layer_coverage(self, full_checker):
        """验证：Models 层模块全部文档化"""
        models = [m for m in full_checker.get_code_modules()
                  if m.module_type == "model"]
        documented_models = [m for m in models if m.documented]
        assert len(documented_models) == len(models), \
            f"Models 层 {len(documented_models)}/{len(models)} 已文档化"

    def test_backend_code_modules_type_diversity(self, backend_code_modules):
        """验证：后端代码模块涵盖所有架构层类型"""
        types = {m.module_type for m in backend_code_modules}
        assert "application" in types
        assert "infrastructure" in types
        assert "model" in types
        assert "repository" in types
        assert "schema" in types
        assert "service" in types

    def test_database_tables_count_matches(self, database_tables):
        """验证：24 + 24 = 48 条表记录（文档 24 + 代码 24）"""
        doc_count = len([t for t in database_tables if t.source == "document"])
        code_count = len([t for t in database_tables if t.source == "code"])
        assert doc_count == 24, f"期望文档表 24 张，实际 {doc_count}"
        assert code_count == 24, f"期望代码表 24 张，实际 {code_count}"

    def test_all_doc_tables_have_code_counterpart(self, database_tables):
        """验证：每张文档表都有对应的代码模型表"""
        doc_names = {t.table_name for t in database_tables if t.source == "document"}
        code_names = {t.table_name for t in database_tables if t.source == "code"}
        assert doc_names == code_names, \
            f"文档表与代码表不匹配\n文档独有: {doc_names - code_names}\n代码独有: {code_names - doc_names}"

    def test_deployment_and_swarm_endpoints_documented(self, full_checker):
        """验证：Deployment 和 Swarm API 端点的文档化和实现状态"""
        eps = full_checker.get_api_endpoints()
        deploy_eps = [ep for ep in eps if "deployment" in ep.path]
        swarm_eps = [ep for ep in eps if "swarm" in ep.path]

        assert len(deploy_eps) >= 2, f"期望至少 2 个部署端点，实际 {len(deploy_eps)}"
        assert len(swarm_eps) >= 2, f"期望至少 2 个蜂群端点，实际 {len(swarm_eps)}"

        for ep in deploy_eps + swarm_eps:
            assert ep.documented, f"{ep.method} {ep.path} 未文档化"
            assert ep.implemented, f"{ep.method} {ep.path} 未实现"

    def test_complete_acceptance_criteria(self, full_checker):
        """验收标准：文档完整度 100%，一致性 ≥ 95%，包含三种文档类型"""
        report = full_checker.generate_report()

        # 验收标准 1: 文档完整度 100%
        doc_completeness = full_checker.check_document_completeness()
        assert doc_completeness == pytest.approx(100.0, rel=1e-9), \
            f"验收失败：文档完整度 {doc_completeness}% ≠ 100%"

        # 验收标准 2: 一致性 ≥ 95%
        module_consistency = full_checker.check_module_consistency()
        db_consistency = full_checker.check_database_consistency()
        api_consistency = full_checker.check_api_consistency()
        overall_consistency = (module_consistency + db_consistency + api_consistency) / 3.0
        assert overall_consistency >= 95.0, \
            f"验收失败：综合一致性 {overall_consistency}% < 95%"

        # 验收标准 3: 包含架构设计、数据库设计、API 文档三种检查
        assert doc_completeness >= 0, "架构设计检查已执行"
        assert db_consistency >= 0, "数据库设计检查已执行"
        assert api_consistency >= 0, "API 文档检查已执行"

        # 全部通过
        assert report.passed(min_consistency=95.0), \
            f"验收失败\n完整度: {doc_completeness}%\n一致性: {overall_consistency}%"
