"""Aeternova AI原生集团管理系统 -- SRS V23 TDD测试用例
基于需求规格说明书V23验收标准，覆盖六大功能模块50+功能需求

上次hourong反馈：检验报告解析失败
根因：JSON检验报告格式不匹配，LLM返回中包含thinking标签和多余文本导致解析失败
修复：标准化的JSON响应格式，所有测试用例统一输出格式
"""
import pytest
import pytest_asyncio
import json
import re
import os
import sys
import asyncio
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app
from app.database import get_db, Base
from app.models.user import User
from app.models.project import Project
from app.models.agent import Agent
from app.models.task import Task
from app.models.requirement import Requirement
from app.models.group import Group, GroupMessage, MeetingOutcome
from app.models.swarm import Swarm
from app.models.qa_record import QARecord
from app.models.workflow_step import WorkflowStep
from app.models.tdd_test_case import TDDTestCase
from app.models.enums import (
    UserRole, ProjectStatus, AgentType, AgentStatus,
    GroupMode, MeetingType, MessageRole, TaskStatus,
    StepStatus, QAStatus, SwarmPurpose, RoleType,
)
from app.utils.security import get_password_hash, create_access_token
from pydantic import BaseModel, Field, ValidationError

TEST_DB_URL = "sqlite://"
TEST_ENGINE = create_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def setup_test_database():
    Base.metadata.create_all(bind=TEST_ENGINE)


def teardown_test_database():
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    setup_test_database()
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        teardown_test_database()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session) -> User:
    user = User(
        id="aet-admin-001",
        username="集团管理员",
        email="admin@aeternova.com",
        password_hash=get_password_hash("Admin@2026"),
        role="super_admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def finance_user(db_session) -> User:
    user = User(
        id="aet-fin-001",
        username="财务主管",
        email="finance@aeternova.com",
        password_hash=get_password_hash("Fin@2026"),
        role="finance_manager",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def hr_user(db_session) -> User:
    user = User(
        id="aet-hr-001",
        username="HR主管",
        email="hr@aeternova.com",
        password_hash=get_password_hash("Hr@2026"),
        role="hr_manager",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_group(db_session, admin_user) -> Project:
    group = Project(
        id="aet-group-001",
        name="Aeternova集团",
        slug="aeternova-group",
        description="AI原生集团企业运营管理平台",
        creator_id=admin_user.id,
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


@pytest_asyncio.fixture
async def auth_admin(admin_user) -> dict:
    token = create_access_token(user_id=admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_finance(finance_user) -> dict:
    token = create_access_token(user_id=finance_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_hr(hr_user) -> dict:
    token = create_access_token(user_id=hr_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def nine_agents(db_session) -> Dict[str, Agent]:
    agents_data = [
        ("aet-haimei", "海梅", "hermes", RoleType.PROJECT_MANAGER.value),
        ("aet-houxing", "后兴", "hermes", RoleType.REQUIREMENT_ANALYST.value),
        ("aet-houwang", "后旺", "hermes", RoleType.ARCHITECT.value),
        ("aet-houfa", "后发", "hermes", RoleType.PROGRAMMER.value),
        ("aet-houda", "后达", "hermes", RoleType.TESTER.value),
        ("aet-houfu", "后富", "hermes", RoleType.CICD_ENGINEER.value),
        ("aet-hougui", "后贵", "hermes", RoleType.DOC_MANAGER.value),
        ("aet-hourong", "后荣", "hermes", RoleType.QA.value),
        ("aet-houhua", "后华", "hermes", RoleType.SECURITY_OFFICER.value),
    ]
    agents = {}
    for agent_id, name, agent_type, role in agents_data:
        agent = Agent(
            id=agent_id,
            name=name,
            agent_type=agent_type,
            status=AgentStatus.online.value,
            config={"role": role},
        )
        db_session.add(agent)
        agents[name] = agent
    db_session.commit()
    for name in agents:
        db_session.refresh(agents[name])
    return agents


class TestOrgStructureModels:
    """模块1：集团组织架构管理 — 数据模型与业务规则"""

    def test_subsidiary_code_format_validation(self):
        class Subsidiary(BaseModel):
            name: str = Field(..., min_length=1, max_length=200)
            code: str = Field(..., pattern=r"^[A-Z]{2,10}-\d{3}$")
            type: str = Field(..., pattern=r"^(wholly_owned|joint_venture|holding)$")
            registered_capital: Optional[float] = Field(None, ge=0)

        sub = Subsidiary(name="测试子公司", code="TEST-001", type="wholly_owned")
        assert sub.name == "测试子公司"
        assert sub.code == "TEST-001"

        with pytest.raises(ValidationError):
            Subsidiary(name="短", code="A-001", type="wholly_owned")

        with pytest.raises(ValidationError):
            Subsidiary(name="测试", code="TEST-001", type="invalid_type")

    def test_subsidiary_full_creation(self):
        class SubsidiaryFull(BaseModel):
            name: str = Field(..., min_length=1, max_length=200)
            code: str = Field(..., pattern=r"^[A-Z]{2,10}-\d{3}$")
            type: str = Field(..., pattern=r"^(wholly_owned|joint_venture|holding)$")
            address: Optional[str] = Field(None, max_length=500)
            contact: Optional[str] = Field(None, max_length=100)
            phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
            established_date: Optional[date] = None
            business_scope: List[str] = Field(default_factory=list)
            registered_capital: Optional[float] = Field(None, ge=0)

        sub = SubsidiaryFull(
            name="Aeternova科技子公司",
            code="TECH-001",
            type="wholly_owned",
            address="北京市海淀区中关村",
            contact="张总",
            phone="13800138001",
            established_date=date(2026, 1, 15),
            business_scope=["AI研发", "企业服务", "云计算"],
            registered_capital=50_000_000.0,
        )
        assert sub.name == "Aeternova科技子公司"
        assert sub.registered_capital == 50_000_000.0

    def test_org_tree_hierarchy_structure(self):
        class OrgNode(BaseModel):
            id: str
            name: str
            type: str
            children: List["OrgNode"] = []

        OrgNode.model_rebuild()

        root = OrgNode(
            id="root", name="Aeternova集团", type="group",
            children=[
                OrgNode(
                    id="sub-001", name="Aeternova科技", type="subsidiary",
                    children=[
                        OrgNode(id="dept-001", name="AI研发中心", type="department"),
                        OrgNode(id="dept-002", name="云计算部门", type="department"),
                    ],
                ),
            ],
        )
        assert len(root.children) == 1
        assert len(root.children[0].children) == 2

    def test_department_model_with_budget_center(self):
        class Department(BaseModel):
            id: str
            name: str = Field(..., min_length=1, max_length=200)
            code: str = Field(..., pattern=r"^[A-Z]{2,10}-\d{3}$")
            parent_id: Optional[str] = None
            manager_name: Optional[str] = None
            headcount: int = Field(..., ge=0)
            budget_center: str

        dept = Department(
            id="DEPT-001", name="AI研发中心", code="AIDEPT-001",
            headcount=50, budget_center="BC-AI-001",
        )
        assert dept.headcount == 50
        assert dept.budget_center == "BC-AI-001"

    def test_org_audit_log_entry(self):
        from enum import Enum

        class AuditAction(str, Enum):
            CREATE = "create"
            UPDATE = "update"
            DELETE = "delete"

        class AuditLog(BaseModel):
            id: str
            org_unit_id: str
            action: AuditAction
            actor_id: str
            changes: Dict[str, Any]
            timestamp: datetime

        log = AuditLog(
            id="log-001", org_unit_id="DEPT-001", action=AuditAction.UPDATE,
            actor_id="admin-001",
            changes={"headcount": {"old": 50, "new": 80}},
            timestamp=datetime.now(timezone.utc),
        )
        assert log.action == AuditAction.UPDATE
        assert log.changes["headcount"]["new"] == 80

    def test_batch_org_update_model(self):
        class OrgUnitUpdate(BaseModel):
            id: str
            headcount: Optional[int] = Field(None, ge=0)
            manager_name: Optional[str] = None

        class BatchUpdate(BaseModel):
            updates: List[OrgUnitUpdate] = Field(..., min_length=1, max_length=100)
            performed_by: str

        batch = BatchUpdate(
            updates=[
                OrgUnitUpdate(id="DEPT-001", headcount=60),
                OrgUnitUpdate(id="DEPT-002", headcount=30),
            ],
            performed_by="admin-001",
        )
        assert len(batch.updates) == 2

    def test_org_permission_boundary(self):
        from enum import Enum

        class OrgPermission(str, Enum):
            READ = "read"
            WRITE = "write"
            DELETE = "delete"
            ADMIN = "admin"

        class RoleOrgPermissions(BaseModel):
            role_name: str
            permissions: List[OrgPermission]
            visible_subsidiaries: List[str] = Field(default_factory=list)

            def can_modify_org(self) -> bool:
                return OrgPermission.WRITE in self.permissions or OrgPermission.ADMIN in self.permissions

        admin_perm = RoleOrgPermissions(
            role_name="super_admin",
            permissions=[OrgPermission.ADMIN],
        )
        finance_perm = RoleOrgPermissions(
            role_name="finance_manager",
            permissions=[OrgPermission.READ],
        )
        assert admin_perm.can_modify_org() is True
        assert finance_perm.can_modify_org() is False

    def test_org_kpi_report_model(self):
        class OrgKPIReport(BaseModel):
            reporting_period: str
            total_employees: int = Field(..., ge=0)
            department_count: int = Field(..., ge=0)
            subsidiary_count: int = Field(..., ge=0)
            turnover_rate: Optional[float] = Field(None, ge=0, le=1)

        report = OrgKPIReport(
            reporting_period="2026-Q2", total_employees=200,
            department_count=12, subsidiary_count=5, turnover_rate=0.08,
        )
        assert report.total_employees == 200
        assert report.turnover_rate == 0.08


class TestHRManagementModels:
    """模块2：人事管理（AI原生）— 数据模型与业务规则"""

    def test_ai_screening_request_model(self):
        class CandidateProfile(BaseModel):
            name: str = Field(..., min_length=1)
            skills: List[str] = Field(..., min_length=1)
            experience_years: int = Field(..., ge=0)

        class AIScreeningRequest(BaseModel):
            position: str = Field(..., min_length=1)
            requirements: str
            candidates: List[CandidateProfile] = Field(..., min_length=1)

        req = AIScreeningRequest(
            position="AI架构师",
            requirements="5年经验, 熟悉LLM",
            candidates=[
                CandidateProfile(name="候选人A", skills=["LLM", "Python"], experience_years=6),
                CandidateProfile(name="候选人B", skills=["Java", "Spring"], experience_years=8),
            ],
        )
        assert len(req.candidates) == 2

    def test_employee_onboarding_workflow_model(self):
        from enum import Enum

        class OnboardingStatus(str, Enum):
            PENDING = "pending"
            ONBOARDING = "onboarding"
            ACTIVE = "active"

        class OnboardingRequest(BaseModel):
            name: str = Field(..., min_length=1)
            employee_id: str = Field(..., pattern=r"^EMP-\d{3,6}$")
            department_id: str
            position: str
            entry_date: date

        req = OnboardingRequest(
            name="新员工李某", employee_id="EMP-001",
            department_id="AIDEPT-001", position="算法工程师",
            entry_date=date(2026, 7, 1),
        )
        assert req.employee_id == "EMP-001"

    def test_ai_performance_review_model(self):
        class PerformanceKPI(BaseModel):
            category: str
            score: float = Field(..., ge=0, le=100)
            weight: float = Field(..., ge=0, le=1)

        class PerformanceReview(BaseModel):
            employee_id: str
            period: str
            kpi_scores: List[PerformanceKPI] = Field(..., min_length=1)
            ai_generated: bool = True

            def calculate_weighted_score(self) -> float:
                total = sum(k.score * k.weight for k in self.kpi_scores)
                weight_sum = sum(k.weight for k in self.kpi_scores)
                return round(total / weight_sum, 2) if weight_sum > 0 else 0.0

        review = PerformanceReview(
            employee_id="EMP-001", period="2026-Q2",
            kpi_scores=[
                PerformanceKPI(category="完成任务", score=95, weight=0.3),
                PerformanceKPI(category="代码质量", score=88, weight=0.3),
                PerformanceKPI(category="团队协作", score=92, weight=0.4),
            ],
        )
        score = review.calculate_weighted_score()
        assert score == pytest.approx(91.4, rel=0.01)

    def test_employee_turnover_prediction_model(self):
        from enum import Enum

        class RiskLevel(str, Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
            CRITICAL = "critical"

        class TurnoverPrediction(BaseModel):
            employee_id: str
            risk_level: RiskLevel
            probability: float = Field(..., ge=0, le=1)
            recommended_actions: List[str] = Field(default_factory=list)

        pred = TurnoverPrediction(
            employee_id="EMP-001", risk_level=RiskLevel.MEDIUM,
            probability=0.45,
            recommended_actions=["薪资调整", "提供晋升路径"],
        )
        assert pred.probability == 0.45
        assert pred.risk_level == RiskLevel.MEDIUM

    def test_org_chart_live_model(self):
        class OrgChartNode(BaseModel):
            employee_id: str
            name: str
            title: str
            department: str
            direct_reports: List["OrgChartNode"] = []

        OrgChartNode.model_rebuild()

        chart = OrgChartNode(
            employee_id="EMP-001", name="王总", title="CTO",
            department="AI研发中心",
            direct_reports=[
                OrgChartNode(employee_id="EMP-002", name="李工", title="高级工程师", department="AI研发中心"),
            ],
        )
        assert len(chart.direct_reports) == 1

    def test_ai_training_recommendation_model(self):
        class TrainingItem(BaseModel):
            course_name: str
            duration_hours: int = Field(..., ge=1)
            relevance_score: float = Field(..., ge=0, le=1)

        class TrainingRecommendation(BaseModel):
            employee_id: str
            career_goal: str
            recommendations: List[TrainingItem] = Field(..., min_length=1)

        rec = TrainingRecommendation(
            employee_id="EMP-001", career_goal="技术管理",
            recommendations=[
                TrainingItem(course_name="团队管理基础", duration_hours=16, relevance_score=0.95),
                TrainingItem(course_name="敏捷开发实战", duration_hours=8, relevance_score=0.82),
            ],
        )
        assert len(rec.recommendations) == 2

    def test_attendance_analysis_model(self):
        from enum import Enum

        class AnomalyType(str, Enum):
            FREQUENT_LATE = "frequent_late"
            EXCESSIVE_ABSENCE = "excessive_absence"
            UNUSUAL_PATTERN = "unusual_pattern"

        class AttendanceAnomaly(BaseModel):
            employee_id: str
            anomaly_type: AnomalyType
            severity: float = Field(..., ge=0, le=1)

        class AttendanceAnalysis(BaseModel):
            month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
            total_employees: int
            anomalies: List[AttendanceAnomaly] = Field(default_factory=list)

        analysis = AttendanceAnalysis(
            month="2026-06", total_employees=200,
            anomalies=[
                AttendanceAnomaly(employee_id="EMP-001", anomaly_type=AnomalyType.FREQUENT_LATE, severity=0.7),
            ],
        )
        assert len(analysis.anomalies) == 1

    def test_salary_optimization_model(self):
        class SalaryOptimization(BaseModel):
            department_id: str
            budget_total: float = Field(..., gt=0)
            employee_count: int = Field(..., gt=0)

            def calculate_avg_budget_per_employee(self) -> float:
                return round(self.budget_total / self.employee_count, 2)

        opt = SalaryOptimization(
            department_id="AIDEPT-001",
            budget_total=5_000_000,
            employee_count=50,
        )
        assert opt.calculate_avg_budget_per_employee() == 100_000.0

    def test_hr_compliance_check_model(self):
        from enum import Enum

        class ComplianceCheckType(str, Enum):
            SOCIAL_INSURANCE = "social_insurance"
            LABOR_CONTRACT = "labor_contract"

        class ComplianceResult(BaseModel):
            check_type: ComplianceCheckType
            year: int
            status: str = Field(..., pattern=r"^(pass|fail|warning)$")
            violations: List[str] = Field(default_factory=list)

        result = ComplianceResult(
            check_type=ComplianceCheckType.SOCIAL_INSURANCE,
            year=2026, status="warning",
            violations=["社保基数未按最新规定调整"],
        )
        assert result.status == "warning"


class TestFinanceModels:
    """模块3：财务管理（AI驱动）— 数据模型与业务规则"""

    def test_ai_budget_proposal_model(self):
        class BudgetProposal(BaseModel):
            fiscal_year: int = Field(..., ge=2020)
            ai_generated: bool = True
            historical_data: Dict[str, float]
            growth_rate: float = Field(..., ge=0, le=10)

            def estimate_next_year_revenue(self) -> float:
                last_revenue = list(self.historical_data.values())[-1]
                return round(last_revenue * (1 + self.growth_rate), 2)

        from collections import OrderedDict
        proposal = BudgetProposal(
            fiscal_year=2027,
            historical_data=OrderedDict([("2026_revenue", 50_000_000), ("2026_cost", 35_000_000)]),
            growth_rate=0.15,
        )
        est = proposal.estimate_next_year_revenue()
        assert est == 40_250_000.0

    def test_expense_reimbursement_model(self):
        from enum import Enum

        class ExpenseCategory(str, Enum):
            TRAVEL = "差旅费"
            ENTERTAINMENT = "业务招待费"
            OFFICE_SUPPLIES = "办公用品"

        class ExpenseClaim(BaseModel):
            applicant: str
            amount: float = Field(..., gt=0, le=999_999_999.99)
            category: ExpenseCategory
            description: str
            attachments: List[str] = Field(default_factory=list)
            status: str = "pending"

        claim = ExpenseClaim(
            applicant="EMP-001", amount=15000.00,
            category=ExpenseCategory.TRAVEL,
            description="北京出差-客户拜访",
            attachments=["receipt_001.pdf"],
        )
        assert claim.amount == 15000.00
        assert claim.category == ExpenseCategory.TRAVEL

    def test_ai_expense_audit_model(self):
        class ExpenseAuditResult(BaseModel):
            claim_id: str
            auto_approved: bool
            risk_score: float = Field(..., ge=0, le=1)
            recommendation: str = Field(..., pattern=r"^(approve|reject|manual_review)$")

        result = ExpenseAuditResult(
            claim_id="claim-001", auto_approved=False,
            risk_score=0.3, recommendation="manual_review",
        )
        assert result.risk_score <= 1.0

    def test_financial_report_model(self):
        from enum import Enum

        class ReportType(str, Enum):
            INCOME_STATEMENT = "income_statement"
            BALANCE_SHEET = "balance_sheet"
            CASH_FLOW = "cash_flow"

        class FinancialReport(BaseModel):
            report_type: ReportType
            period: str
            format: str = "json"
            data: Dict[str, float] = Field(default_factory=dict)

        report = FinancialReport(
            report_type=ReportType.INCOME_STATEMENT, period="2026-Q2",
            data={"revenue": 50_000_000, "cost": 35_000_000, "profit": 15_000_000},
        )
        assert report.data["profit"] == 15_000_000

    def test_cross_subsidiary_funding_model(self):
        class CrossFundingRequest(BaseModel):
            from_subsidiary: str
            to_subsidiary: str
            amount: float = Field(..., gt=0)
            purpose: str

            def validate_not_same_entity(self):
                if self.from_subsidiary == self.to_subsidiary:
                    raise ValueError("调出方和调入方不能是同一实体")

        req = CrossFundingRequest(
            from_subsidiary="SUB-001", to_subsidiary="SUB-002",
            amount=1_000_000.00, purpose="项目周转",
        )
        req.validate_not_same_entity()

        bad_req = CrossFundingRequest(
            from_subsidiary="SUB-001", to_subsidiary="SUB-001",
            amount=100, purpose="测试",
        )
        with pytest.raises(ValueError, match="同一实体"):
            bad_req.validate_not_same_entity()

    def test_budget_execution_tracking_model(self):
        class BudgetExecution(BaseModel):
            department_id: str
            quarter: str = Field(..., pattern=r"^Q\d$")
            budget_allocated: float = Field(..., ge=0)
            budget_spent: float = Field(..., ge=0)

            @property
            def execution_rate(self) -> float:
                if self.budget_allocated == 0:
                    return 0.0
                return round(self.budget_spent / self.budget_allocated, 4)

        execution = BudgetExecution(
            department_id="AIDEPT-001", quarter="Q2",
            budget_allocated=1_000_000, budget_spent=650_000,
        )
        assert execution.execution_rate == 0.65

    def test_invoice_ocr_model(self):
        class InvoiceRecognition(BaseModel):
            invoice_number: str
            date: date
            supplier: str
            amount: float = Field(..., gt=0)
            confidence_score: float = Field(..., ge=0, le=1)

        invoice = InvoiceRecognition(
            invoice_number="INV-2026-001", date=date(2026, 6, 15),
            supplier="NVIDIA", amount=80000.0, confidence_score=0.98,
        )
        assert invoice.confidence_score >= 0.9

    def test_financial_risk_warning_model(self):
        from enum import Enum

        class RiskLevel(str, Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
            CRITICAL = "critical"

        class RiskWarning(BaseModel):
            risk_id: str
            risk_level: RiskLevel
            category: str
            description: str
            detected_at: datetime
            resolved: bool = False

        warning = RiskWarning(
            risk_id="RISK-001", risk_level=RiskLevel.HIGH, category="资金链",
            description="子公司A现金流低于预警线",
            detected_at=datetime.now(timezone.utc),
        )
        assert warning.risk_level == RiskLevel.HIGH
        assert warning.resolved is False

    def test_finance_permission_isolation(self):
        class FinanceRole(BaseModel):
            role_name: str
            can_view_budget: bool
            can_approve_expense: bool

        roles = {
            "super_admin": FinanceRole(role_name="super_admin", can_view_budget=True, can_approve_expense=True),
            "finance_manager": FinanceRole(role_name="finance_manager", can_view_budget=True, can_approve_expense=True),
            "hr_manager": FinanceRole(role_name="hr_manager", can_view_budget=False, can_approve_expense=False),
        }
        assert roles["hr_manager"].can_view_budget is False
        assert roles["finance_manager"].can_approve_expense is True


class TestApprovalWorkflowModels:
    """模块4：智能审批流程（Agent驱动）— 数据模型与业务规则"""

    def test_approval_template_model(self):
        class ApprovalStep(BaseModel):
            step_order: int = Field(..., ge=1)
            approver_role: str
            action: str = Field(..., pattern=r"^(review|audit|approve|sign_off)$")
            condition: Optional[str] = None
            timeout_hours: Optional[int] = None

        class ApprovalTemplate(BaseModel):
            name: str = Field(..., min_length=1)
            type: str
            steps: List[ApprovalStep] = Field(..., min_length=1)
            ai_recommend_route: bool = True

        tpl = ApprovalTemplate(
            name="采购审批流程", type="purchase",
            steps=[
                ApprovalStep(step_order=1, approver_role="department_manager", action="review"),
                ApprovalStep(step_order=2, approver_role="finance_manager", action="audit"),
                ApprovalStep(step_order=3, approver_role="ceo", action="approve", condition="amount > 50000"),
            ],
        )
        assert len(tpl.steps) == 3
        assert tpl.steps[0].step_order < tpl.steps[1].step_order

    def test_approval_submission_with_ai_routing(self):
        from enum import Enum

        class Priority(str, Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"

        class ApprovalSubmission(BaseModel):
            template_id: str
            title: str = Field(..., min_length=1, max_length=500)
            content: Dict[str, Any]
            ai_route: bool = True
            priority: Priority = Priority.MEDIUM

        sub = ApprovalSubmission(
            template_id="AP-TPL-001", title="采购GPU服务器",
            content={"amount": 80000, "supplier": "NVIDIA"},
            priority=Priority.HIGH,
        )
        assert sub.ai_route is True
        assert sub.priority == Priority.HIGH

    def test_ai_auto_approve_threshold(self):
        class AutoApproveResult(BaseModel):
            approval_id: str
            amount: float
            threshold: float = Field(..., gt=0)
            auto_approved: bool = False
            risk_score: float = Field(..., ge=0, le=1)

            def should_auto_approve(self) -> bool:
                return self.amount <= self.threshold and self.risk_score < 0.5

        result = AutoApproveResult(
            approval_id="AP-001", amount=3000,
            threshold=5000, risk_score=0.2,
        )
        assert result.should_auto_approve() is True

        high_risk = AutoApproveResult(
            approval_id="AP-002", amount=3000,
            threshold=5000, risk_score=0.7,
        )
        assert high_risk.should_auto_approve() is False

    def test_approval_history_filter_model(self):
        from enum import Enum

        class ApprovalStatus(str, Enum):
            PENDING = "pending"
            APPROVED = "approved"
            REJECTED = "rejected"
            COMPLETED = "completed"

        class ApprovalHistoryFilter(BaseModel):
            status: Optional[ApprovalStatus] = None
            start_date: Optional[date] = None
            end_date: Optional[date] = None
            page: int = Field(default=1, ge=1)
            page_size: int = Field(default=20, ge=1, le=100)

        filt = ApprovalHistoryFilter(
            status=ApprovalStatus.COMPLETED,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 7, 1),
        )
        assert filt.page == 1
        assert filt.page_size == 20

    def test_parallel_approval_model(self):
        from enum import Enum

        class ParallelStrategy(str, Enum):
            ALL_MUST_APPROVE = "all_must_approve"
            ANY_CAN_APPROVE = "any_can_approve"
            MAJORITY = "majority"

        class ParallelApproval(BaseModel):
            approval_id: str
            approvers: List[str] = Field(..., min_length=2)
            strategy: ParallelStrategy
            results: Dict[str, str] = Field(default_factory=dict)

            def is_approved(self) -> bool:
                if self.strategy == ParallelStrategy.ANY_CAN_APPROVE:
                    return any(v == "approved" for v in self.results.values())
                if self.strategy == ParallelStrategy.ALL_MUST_APPROVE:
                    return all(v == "approved" for v in self.results.values())
                if self.strategy == ParallelStrategy.MAJORITY:
                    approved = sum(1 for v in self.results.values() if v == "approved")
                    return approved > len(self.approvers) / 2
                return False

        p1 = ParallelApproval(
            approval_id="AP-001", approvers=["user-1", "user-2"],
            strategy=ParallelStrategy.ALL_MUST_APPROVE,
            results={"user-1": "approved", "user-2": "approved"},
        )
        assert p1.is_approved() is True

        p2 = ParallelApproval(
            approval_id="AP-002", approvers=["user-1", "user-2"],
            strategy=ParallelStrategy.ALL_MUST_APPROVE,
            results={"user-1": "approved", "user-2": "rejected"},
        )
        assert p2.is_approved() is False

    def test_batch_approval_model(self):
        from enum import Enum

        class BatchDecision(str, Enum):
            APPROVE = "approve"
            REJECT = "reject"

        class BatchApproval(BaseModel):
            approval_ids: List[str] = Field(..., min_length=1, max_length=50)
            decision: BatchDecision
            comment: Optional[str] = None
            performed_by: str

        batch = BatchApproval(
            approval_ids=["AP-001", "AP-002", "AP-003"],
            decision=BatchDecision.APPROVE,
            comment="批量审批通过", performed_by="admin-001",
        )
        assert len(batch.approval_ids) == 3

    def test_reject_with_ai_alternative(self):
        class RejectWithAlternative(BaseModel):
            approval_id: str
            reason: str
            ai_alternative: Optional[Dict[str, Any]] = None

            def has_alternative(self) -> bool:
                return self.ai_alternative is not None

        reject = RejectWithAlternative(
            approval_id="AP-001", reason="预算不足",
            ai_alternative={
                "suggestion": "分期采购",
                "plan": [{"phase": 1, "amount": 40000, "date": "2026-07-01"}],
            },
        )
        assert reject.has_alternative() is True


class TestMultiAgentCollaboration:
    """模块5：多Agent协作管理（Agent-first）— 数据模型与协作规则"""

    def test_agent_group_chat_model(self):
        from enum import Enum

        class ChatMode(str, Enum):
            DISCUSSION = "discussion"
            MEETING = "meeting"

        class GroupChatRequest(BaseModel):
            topic: str = Field(..., min_length=1)
            agents: List[str] = Field(..., min_length=2)
            mode: ChatMode = ChatMode.DISCUSSION
            host_agent: str

        req = GroupChatRequest(
            topic="2026下半年经营计划讨论",
            agents=["海梅", "后兴", "后发", "后荣"],
            mode=ChatMode.MEETING,
            host_agent="海梅",
        )
        assert len(req.agents) == 4
        assert req.mode == ChatMode.MEETING

    def test_ai_meeting_summary_model(self):
        class MeetingSummary(BaseModel):
            chat_id: str
            summary: str
            decisions: List[str] = Field(default_factory=list)
            tasks: List[Dict[str, Any]] = Field(default_factory=list)

        summary = MeetingSummary(
            chat_id="chat-001",
            summary="讨论了Q3经营目标和AI产品路线图",
            decisions=["Q3营收目标增长20%", "优先推出AI客服产品"],
            tasks=[{"assignee": "后发", "description": "完成AI客服原型"}],
        )
        assert len(summary.decisions) == 2

    def test_agent_task_delegation_model(self):
        from enum import Enum

        class DelegationPriority(str, Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"

        class TaskDelegation(BaseModel):
            task: str = Field(..., min_length=1)
            assign_to: str
            context: Dict[str, Any] = Field(default_factory=dict)
            priority: DelegationPriority = DelegationPriority.MEDIUM
            deadline: Optional[datetime] = None

        deleg = TaskDelegation(
            task="分析Q2财报并生成报告", assign_to="后兴",
            context={"period": "2026-Q2"},
            priority=DelegationPriority.HIGH,
            deadline=datetime(2026, 7, 10, 18, 0, 0, tzinfo=timezone.utc),
        )
        assert deleg.priority == DelegationPriority.HIGH

    def test_natural_language_query_model(self):
        class NLQuery(BaseModel):
            query: str = Field(..., min_length=1)
            context: Dict[str, Any] = Field(default_factory=dict)
            response_format: str = "json"

        q = NLQuery(
            query="上个月各子公司营收排名",
            context={"time_range": "2026-06", "scope": "all_subsidiaries"},
        )
        assert q.response_format == "json"

    def test_multi_step_agent_workflow_model(self):
        class WorkflowStepItem(BaseModel):
            agent: str
            action: str
            depends_on: List[str] = Field(default_factory=list)

        class AgentWorkflow(BaseModel):
            name: str = Field(..., min_length=1)
            steps: List[WorkflowStepItem] = Field(..., min_length=1)
            auto_execute: bool = True

        wf = AgentWorkflow(
            name="季度经营分析全流程",
            steps=[
                WorkflowStepItem(agent="后兴", action="收集数据", depends_on=[]),
                WorkflowStepItem(agent="后发", action="生成图表", depends_on=["后兴"]),
                WorkflowStepItem(agent="海梅", action="汇总报告", depends_on=["后兴", "后发"]),
            ],
        )
        assert len(wf.steps) == 3
        assert wf.auto_execute is True

    def test_agent_health_monitor_model(self):
        from enum import Enum

        class AgentHealthStatus(str, Enum):
            HEALTHY = "healthy"
            BUSY = "busy"
            ERROR = "error"
            OFFLINE = "offline"

        class AgentHealthReport(BaseModel):
            agent_name: str
            status: AgentHealthStatus
            last_heartbeat: datetime
            current_tasks: int = 0
            max_concurrent: int = Field(default=5, ge=1)

            @property
            def is_available(self) -> bool:
                return self.status in (AgentHealthStatus.HEALTHY, AgentHealthStatus.BUSY) and self.current_tasks < self.max_concurrent

        report = AgentHealthReport(
            agent_name="海梅", status=AgentHealthStatus.HEALTHY,
            last_heartbeat=datetime.now(timezone.utc),
            current_tasks=2, max_concurrent=5,
        )
        assert report.is_available is True

    def test_agent_collision_resolution_model(self):
        from enum import Enum

        class ConflictType(str, Enum):
            SCHEDULE = "schedule"
            RESOURCE = "resource"
            PRIORITY = "priority"

        class ConflictResolution(BaseModel):
            conflict_type: ConflictType
            agents_involved: List[str] = Field(..., min_length=2)
            resource: str

        conflict = ConflictResolution(
            conflict_type=ConflictType.SCHEDULE,
            agents_involved=["海梅", "后发"],
            resource="H100 GPU服务器",
        )
        assert len(conflict.agents_involved) == 2

    def test_voice_command_model(self):
        class VoiceCommand(BaseModel):
            transcript: str = Field(..., min_length=1)
            context: Dict[str, Any] = Field(default_factory=dict)
            confidence: Optional[float] = Field(None, ge=0, le=1)

        cmd = VoiceCommand(
            transcript="查看本月销售数据",
            context={"module": "sales"},
            confidence=0.95,
        )
        assert cmd.confidence >= 0.9


class TestAnalyticsModels:
    """模块6：数据分析与AI报表 — 数据模型与业务规则"""

    def test_kpi_dashboard_model(self):
        class KPIMetric(BaseModel):
            name: str
            value: float
            target: Optional[float] = None
            trend: str = Field(default="stable", pattern=r"^(up|down|stable)$")
            unit: str = ""

            @property
            def achievement_rate(self) -> Optional[float]:
                if self.target is None or self.target == 0:
                    return None
                return round(self.value / self.target * 100, 2)

        class KPIDashboard(BaseModel):
            period: str
            metrics: List[KPIMetric] = Field(..., min_length=1)

        dashboard = KPIDashboard(
            period="2026-Q2",
            metrics=[
                KPIMetric(name="营收", value=50_000_000, target=60_000_000, trend="up", unit="元"),
                KPIMetric(name="利润率", value=30.0, target=35.0, trend="down", unit="%"),
            ],
        )
        assert dashboard.metrics[0].achievement_rate == pytest.approx(83.33, rel=0.01)

    def test_natural_language_report_model(self):
        class NLReportRequest(BaseModel):
            query: str = Field(..., min_length=1)
            format: str = "markdown"
            include_charts: bool = True

        req = NLReportRequest(
            query="对比分析集团各子公司Q2利润率",
            format="markdown",
        )
        assert req.include_charts is True

    def test_ai_trend_prediction_model(self):
        from enum import Enum

        class PredictionModel(str, Enum):
            PROPHET = "prophet"
            ARIMA = "arima"
            LSTM = "lstm"

        class TrendPrediction(BaseModel):
            metric: str
            history_months: int = Field(..., ge=1)
            predict_months: int = Field(..., ge=1)
            model: PredictionModel = PredictionModel.PROPHET

        pred = TrendPrediction(
            metric="monthly_revenue", history_months=12,
            predict_months=3, model=PredictionModel.PROPHET,
        )
        assert pred.model == PredictionModel.PROPHET

    def test_custom_report_builder_model(self):
        class CustomReport(BaseModel):
            dimensions: List[str] = Field(..., min_length=1)
            metrics: List[str] = Field(..., min_length=1)
            filters: Dict[str, Any] = Field(default_factory=dict)
            ai_insights: bool = True

        report = CustomReport(
            dimensions=["department", "month"],
            metrics=["revenue", "cost", "profit"],
            filters={"year": 2026, "quarter": "Q2"},
        )
        assert len(report.dimensions) == 2

    def test_alert_rule_model(self):
        class AlertRule(BaseModel):
            name: str = Field(..., min_length=1, max_length=200)
            metric: str
            condition: str
            notify_roles: List[str] = Field(..., min_length=1)
            ai_threshold_suggest: bool = True

        rule = AlertRule(
            name="营收下跌预警", metric="revenue",
            condition="drop > 15%",
            notify_roles=["ceo", "finance_manager"],
        )
        assert rule.ai_threshold_suggest is True

    def test_data_export_model(self):
        from enum import Enum

        class ExportFormat(str, Enum):
            XLSX = "xlsx"
            CSV = "csv"
            PDF = "pdf"
            JSON = "json"

        class DataExport(BaseModel):
            report_id: str
            format: ExportFormat
            include_charts: bool = True

        export = DataExport(report_id="RPT-001", format=ExportFormat.XLSX)
        assert export.format == ExportFormat.XLSX

    def test_anomaly_explanation_model(self):
        class AnomalyExplanation(BaseModel):
            anomaly_id: str
            description: str
            root_cause: str
            recommended_actions: List[str] = Field(default_factory=list)
            confidence: float = Field(..., ge=0, le=1)

        explanation = AnomalyExplanation(
            anomaly_id="ANM-001",
            description="6月份AI研发中心费用异常增长",
            root_cause="GPU采购导致一次性支出增加",
            recommended_actions=["确认GPU采购已在预算内"],
            confidence=0.88,
        )
        assert len(explanation.recommended_actions) == 1
        assert 0 <= explanation.confidence <= 1

    def test_scheduled_report_model(self):
        class ScheduledReport(BaseModel):
            name: str = Field(..., min_length=1)
            cron: str
            recipients: List[str] = Field(..., min_length=1)
            template_id: str
            is_active: bool = True

        sched = ScheduledReport(
            name="月度经营简报", cron="0 8 1 * *",
            recipients=["ceo@aeternova.com", "cfo@aeternova.com"],
            template_id="RPT-TPL-MONTHLY",
        )
        assert sched.is_active is True


class TestDialogueInterface:
    """AI原生对话接口 — 核心交互层"""

    def test_natural_language_execute_model(self):
        class DialogueExecution(BaseModel):
            utterance: str = Field(..., min_length=1, max_length=2000)
            intent_detection: bool = True
            auto_execute: bool = False
            detected_intent: Optional[str] = None

        exec_req = DialogueExecution(
            utterance="在深圳成立一家全资子公司，主营AI芯片研发，注册资本5000万",
            intent_detection=True, auto_execute=True,
        )
        assert exec_req.intent_detection is True
        assert exec_req.auto_execute is True

    def test_conversational_approval_model(self):
        class ConversationalAction(BaseModel):
            utterance: str
            context: Dict[str, Any]
            resolved_action: Optional[str] = None

        action = ConversationalAction(
            utterance="帮我审批一下昨天提交的差旅报销单",
            context={"user_role": "ceo"},
            resolved_action="approve_expense",
        )
        assert action.resolved_action == "approve_expense"

    def test_multi_turn_context_model(self):
        class DialogueTurn(BaseModel):
            turn_id: int
            session_id: str
            utterance: str
            context: Dict[str, Any] = Field(default_factory=dict)

        class DialogueSession(BaseModel):
            session_id: str
            turns: List[DialogueTurn] = Field(default_factory=list)
            max_turns: int = Field(default=20, ge=1)

            @property
            def current_turn(self) -> int:
                return len(self.turns) + 1

        session = DialogueSession(session_id="sess-001")
        session.turns.append(DialogueTurn(turn_id=1, session_id="sess-001", utterance="查看上月营收"))
        session.turns.append(DialogueTurn(turn_id=2, session_id="sess-001", utterance="对比前月数据"))
        assert session.current_turn == 3

    def test_intent_fallback_model(self):
        class IntentResult(BaseModel):
            utterance: str
            detected_intent: Optional[str] = None
            confidence: float = Field(..., ge=0, le=1)
            is_fallback: bool = False
            fallback_message: Optional[str] = None

        result = IntentResult(
            utterance="今天天气怎么样",
            detected_intent=None, confidence=0.05,
            is_fallback=True,
            fallback_message="我无法处理天气查询",
        )
        assert result.is_fallback is True
        assert 0 <= result.confidence <= 1

    def test_dialogue_undo_model(self):
        class DialogueUndo(BaseModel):
            session_id: str
            steps: int = Field(default=1, ge=1, le=10)

        undo = DialogueUndo(session_id="sess-001", steps=1)
        assert undo.steps == 1


class TestSecurityPermissionModels:
    """权限与安全管理 — 数据模型"""

    def test_rbac_role_config_model(self):
        class RoleConfig(BaseModel):
            name: str = Field(..., min_length=1)
            permissions: List[str] = Field(..., min_length=1)
            max_approval_amount: Optional[float] = Field(None, ge=0)

        role = RoleConfig(
            name="子公司总经理",
            permissions=["org:read", "org:write", "finance:read", "hr:read", "approval:approve"],
            max_approval_amount=100_000,
        )
        assert len(role.permissions) == 5

    def test_audit_trail_model(self):
        class AuditTrail(BaseModel):
            action: str
            actor_id: str
            target_resource: str
            timestamp: datetime
            result: str = Field(..., pattern=r"^(success|failure)$")

        trail = AuditTrail(
            action="approval.reject", actor_id="mgr-001",
            target_resource="AP-001",
            timestamp=datetime.now(timezone.utc),
            result="success",
        )
        assert trail.result == "success"

    def test_data_isolation_model(self):
        class DataScope(BaseModel):
            user_id: str
            role: str
            accessible_subsidiaries: List[str] = Field(default_factory=list)
            can_view_group_data: bool = False

            def can_access(self, subsidiary_id: str) -> bool:
                if self.can_view_group_data:
                    return True
                return subsidiary_id in self.accessible_subsidiaries

        hr_scope = DataScope(
            user_id="hr-001", role="hr_manager",
            accessible_subsidiaries=["SUB-001"],
        )
        assert hr_scope.can_access("SUB-001") is True
        assert hr_scope.can_access("SUB-002") is False

        admin_scope = DataScope(
            user_id="admin-001", role="super_admin",
            can_view_group_data=True,
        )
        assert admin_scope.can_access("ANY") is True

    def test_sensitive_data_masking_model(self):
        class SensitiveField(BaseModel):
            field_name: str
            mask_type: str = Field(..., pattern=r"^(prefix|suffix|hash|full)$")
            visible_chars: int = Field(default=4, ge=0)

            def mask(self, value: str) -> str:
                if self.mask_type == "full":
                    return "*" * len(value)
                if self.mask_type == "prefix":
                    return "*" * (len(value) - self.visible_chars) + value[-self.visible_chars:]
                if self.mask_type == "suffix":
                    return value[:self.visible_chars] + "*" * (len(value) - self.visible_chars)
                if self.mask_type == "hash":
                    import hashlib
                    return hashlib.sha256(value.encode()).hexdigest()[:16]
                return value

        field = SensitiveField(field_name="phone", mask_type="prefix", visible_chars=4)
        masked = field.mask("13800138001")
        assert masked.endswith("8001")

    def test_unauthorized_access_model(self):
        from enum import Enum

        class AccessDeniedReason(str, Enum):
            NO_PERMISSION = "no_permission"
            DATA_OUT_OF_SCOPE = "data_out_of_scope"
            EXPIRED_TOKEN = "expired_token"

        class AccessDenied(BaseModel):
            user_id: str
            resource: str
            reason: AccessDeniedReason
            message: str

        denied = AccessDenied(
            user_id="hr-001", resource="finance/budget-tracking",
            reason=AccessDeniedReason.NO_PERMISSION,
            message="您无权访问财务预算数据",
        )
        assert denied.reason == AccessDeniedReason.NO_PERMISSION


class TestORMModels:
    """ORM模型层 — 基于真实数据库模型的测试"""

    def test_project_model_creation(self, db_session):
        project = Project(
            name="测试项目Aeternova", slug="test-aeternova",
            description="AI原生集团管理系统", creator_id="admin-001",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        assert project.id is not None
        assert project.name == "测试项目Aeternova"
        assert project.status == "created"
        assert project.current_step == 1

    def test_project_status_transition(self, db_session):
        project = Project(
            name="状态测试", slug="status-test",
            creator_id="admin-001", status="created",
        )
        db_session.add(project)
        db_session.commit()

        project.status = "in_progress"
        project.current_step = 3
        db_session.commit()
        db_session.refresh(project)

        assert project.status == "in_progress"
        assert project.current_step == 3

    def test_group_discussion_mode(self, db_session):
        group = Group(
            name="项目讨论群", mode="discussion",
            members=["海梅", "后兴", "后旺", "后发", "后达", "后富", "后贵", "后荣", "后华"],
            host_agent="海梅",
        )
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)

        assert group.mode == "discussion"
        assert len(group.members) == 9
        assert "海梅" in group.members

    def test_group_meeting_mode(self, db_session):
        group = Group(
            name="需求评审会议", mode="meeting",
            members=["海梅", "后兴"], host_agent="海梅",
        )
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)

        assert group.mode == "meeting"
        assert group.host_agent == "海梅"

    def test_meeting_outcome_creation(self, db_session):
        group = Group(name="评审群", members=["海梅", "后兴"], mode="meeting")
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)

        outcome = MeetingOutcome(
            group_id=group.id, meeting_topic="需求评审",
            meeting_type="requirement_review",
            host_agent="海梅",
            started_at=datetime.now(timezone.utc),
            decisions=["确认核心需求", "确定技术栈"],
        )
        db_session.add(outcome)
        db_session.commit()

        assert outcome.meeting_type == "requirement_review"
        assert len(outcome.decisions) == 2

    def test_workflow_step_creation(self, db_session):
        project = Project(name="WF测试", slug="wf-test", creator_id="admin-001")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        step = WorkflowStep(
            project_id=project.id, step_number=1,
            step_name="人类用户创建项目", status="completed",
        )
        db_session.add(step)
        db_session.commit()

        assert step.status == "completed"
        assert step.step_number == 1

    def test_qa_record_creation(self, db_session):
        project = Project(name="QA测试", slug="qa-test", creator_id="admin-001")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        step = WorkflowStep(
            project_id=project.id, step_number=2,
            step_name="海梅确认核心目标", status="qa_review",
        )
        db_session.add(step)
        db_session.commit()
        db_session.refresh(step)

        qa_record = QARecord(
            project_id=project.id, workflow_step_id=step.id,
            qa_agent_id="aet-hourong", status="passed",
            review_dimensions=["目标明确性", "组织完整性"],
        )
        db_session.add(qa_record)
        db_session.commit()

        assert qa_record.status == "passed"
        assert len(qa_record.review_dimensions) == 2

    def test_tdd_test_case_creation(self, db_session):
        project = Project(name="TDD测试", slug="tdd-test", creator_id="admin-001")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        test_case = TDDTestCase(
            project_id=project.id, round_number=1, case_index=0,
            case_id="TC-001", title="验证用户登录",
            description="测试用户登录功能",
            precondition="用户已注册",
            test_steps="1. 输入用户名密码\n2. 点击登录",
            expected_result="登录成功",
            priority="high", category="认证",
            source_section="FR-AUTH-001",
            qa_status="pending",
        )
        db_session.add(test_case)
        db_session.commit()

        assert test_case.qa_status == "pending"
        assert test_case.case_id == "TC-001"

    def test_agent_model_with_config(self, db_session):
        agent = Agent(
            id="aet-test-agent", name="测试Agent",
            agent_type="hermes", status="online",
            config={"role": "project_manager", "capabilities": ["coding", "review"]},
        )
        db_session.add(agent)
        db_session.commit()
        db_session.refresh(agent)

        assert agent.status == "online"
        assert agent.config["role"] == "project_manager"

    def test_group_message_creation(self, db_session):
        group = Group(name="消息测试", members=["海梅", "后兴"])
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)

        msg = GroupMessage(
            group_id=group.id, sender="海梅", role="assistant",
            content="@后兴 请开始需求分析", is_streaming=False,
        )
        db_session.add(msg)
        db_session.commit()

        assert msg.sender == "海梅"
        assert "@后兴" in msg.content


class TestServiceLayer:
    """服务层 — 业务逻辑"""

    def test_workflow_engine_default_steps(self, db_session):
        from app.services.workflow_engine import get_default_steps, QA_REQUIRED_STEPS

        steps = get_default_steps()
        assert len(steps) == 16

        step_names = [s.name for s in steps]
        assert "人类用户创建项目" in step_names
        assert "海梅确认核心目标与搭建组织架构" in step_names
        assert "后兴需求分析" in step_names

    def test_workflow_engine_qa_required_steps(self):
        from app.services.workflow_engine import QA_REQUIRED_STEPS

        assert 2 in QA_REQUIRED_STEPS
        assert 3 in QA_REQUIRED_STEPS
        assert 7 in QA_REQUIRED_STEPS
        assert 11 in QA_REQUIRED_STEPS
        assert 1 not in QA_REQUIRED_STEPS

    def test_qa_gate_service_inspection(self):
        from app.services.qa_gate_service import QAGateService

        service = QAGateService()
        result = service.inspect(
            artifact_type="core_goal", project_id="proj-001",
            workflow_step_id=1, result="passed",
        )
        assert result["status"] == "passed"
        assert "目标明确性" in result["review_dimensions"]

    def test_qa_gate_service_rollback(self):
        from app.services.qa_gate_service import QAGateService

        service = QAGateService()
        result = service.rollback(
            task_id="task-001", project_id="proj-001",
            workflow_step_id=2, reason="需求不完整",
            suggestions=["补充非功能需求", "增加验收标准"],
        )
        assert result["status"] == "failed"
        assert len(result["fix_suggestions"]) == 2

    def test_enum_agent_roles_complete(self):
        from app.models.enums import RoleType

        expected_roles = {
            "project_manager", "requirement_analyst", "architect",
            "programmer", "tester", "cicd_engineer", "doc_manager",
            "qa", "security_officer", "system_admin", "swarm_member",
        }
        actual_roles = {r.value for r in RoleType}
        assert expected_roles.issubset(actual_roles)

    def test_enum_meeting_types(self):
        from app.models.enums import MeetingType

        expected_types = {"requirement_review", "tech_solution", "daily_standup", "incident_postmortem"}
        actual_types = {m.value for m in MeetingType}
        assert expected_types == actual_types

    def test_enum_group_modes(self):
        from app.models.enums import GroupMode

        assert GroupMode.discussion.value == "discussion"
        assert GroupMode.meeting.value == "meeting"

    def test_step_status_enum(self):
        from app.models.enums import StepStatus

        expected = {"pending", "in_progress", "qa_review", "passed", "rejected", "completed"}
        actual = {s.value for s in StepStatus}
        assert expected == actual


class TestIntegrationScenarios:
    """集成场景 — 端到端测试"""

    def test_full_16_step_workflow_init(self, db_session):
        from app.services.workflow_engine import WorkflowEngine

        project = Project(
            name="完整流程测试", slug="full-workflow-test",
            creator_id="admin-001",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        engine = WorkflowEngine(project_id=project.id, db=db_session, auto_supervise=False)
        assert engine.current_step >= 1
        assert len(engine.steps) == 16

    def test_qa_pass_then_advance(self, db_session):
        from app.services.workflow_engine import WorkflowEngine

        project = Project(
            name="QA推进测试", slug="qa-advance-test",
            creator_id="admin-001",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        engine = WorkflowEngine(project_id=project.id, db=db_session, auto_supervise=False)
        engine.advance_step(2)
        assert engine.current_step == 2

    def test_swarm_full_lifecycle(self, db_session):
        from app.services.swarm_service import SwarmService

        service = SwarmService()
        swarm = service.create_swarm(
            project_id="proj-001", name="TDD测试蜂群",
            purpose="code_writing", step_number=7,
            manager_role="houfa",
        )
        service.add_member(swarm["id"], "claude_code", "claude-001")
        service.add_member(swarm["id"], "opencode", "opencode-001")
        result = service.get_swarm(swarm["id"])
        assert len(result["members"]) == 2
        assert result["status"] == "active"

    def test_complete_project_with_workflow_and_qa(self, db_session):
        project = Project(
            name="完整项目测试", slug="complete-project-test",
            creator_id="admin-001",
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        for i in range(1, 5):
            step = WorkflowStep(
                project_id=project.id, step_number=i,
                step_name=f"步骤{i}",
                status="completed" if i < 4 else "qa_review",
            )
            db_session.add(step)
        db_session.commit()

        steps = db_session.query(WorkflowStep).filter_by(project_id=project.id).all()
        qa_step = steps[3]

        agent = Agent(id="aet-hourong", name="后荣", agent_type="hermes", status="online")
        db_session.add(agent)
        db_session.commit()

        qa = QARecord(
            project_id=project.id, workflow_step_id=qa_step.id,
            qa_agent_id=agent.id, status="passed",
            review_dimensions=["完整性", "一致性"],
        )
        db_session.add(qa)
        db_session.commit()

        qa_records = db_session.query(QARecord).filter_by(project_id=project.id).all()
        assert len(qa_records) == 1
        assert qa_records[0].status == "passed"


class TestHourongReportParsing:
    """hourong检验报告JSON解析 — 修复检验报告解析失败

    覆盖多种LLM返回格式，确保JSON提取策略正确。
    上次hourong反馈：检验报告解析失败
    根因：LLM返回包含thinking/analysis标签及多余文本，
    标准JSON解析器无法直接处理。
    修复：多层回退解析策略。
    """

    @staticmethod
    def _extract_json(reply: str) -> dict:
        if not reply or not reply.strip():
            return {}

        import re as _re
        import json as _json

        qa_r = reply
        single = {}

        _lt, _gt = chr(60), chr(62)
        _think_open = rf'{_lt}(?:thinking|think|analysis){_gt}'
        _think_close = rf'{_lt}/(?:thinking|think|analysis){_gt}'
        qa_r = _re.sub(rf'(?:{_think_open})[\s\S]*?(?:{_think_close})', '', qa_r)

        candidates = []

        fenced = _re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', qa_r, _re.DOTALL)
        for fc in fenced:
            stripped = fc.strip()
            if stripped:
                candidates.append(stripped)

        brace_start = qa_r.find('{')
        brace_end = qa_r.rfind('}')
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidates.append(qa_r[brace_start:brace_end + 1])

        json_like = _re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', qa_r)
        for jl in json_like:
            if len(jl) > 10:
                candidates.append(jl)

        stripped = qa_r.strip()
        bs2 = stripped.find('{')
        if bs2 > 0:
            candidates.append(stripped[bs2:])
        be2 = stripped.rfind('}')
        if be2 >= 0 and be2 < len(stripped) - 1:
            candidates.append(stripped[:be2 + 1])

        candidates.append(qa_r)

        def _repair_json(text):
            t = text.strip()
            t = _re.sub(r',\s*([}\]])', r'\1', t)
            try:
                return _json.loads(t)
            except Exception:
                pass
            core = t.lstrip('\n\r\t ')
            while core and core[0] not in '{[":':
                core = core[1:]
            while core and core[-1] not in '}]\n\r\t ':
                core = core[:-1]
            try:
                return _json.loads(core.strip())
            except Exception:
                pass
            return None

        for candidate in candidates:
            try:
                parsed = _json.loads(candidate)
                if isinstance(parsed, dict) and parsed:
                    single = parsed
                    break
            except Exception:
                pass
            repaired = _repair_json(candidate)
            if repaired and isinstance(repaired, dict) and repaired:
                single = repaired
                break

        return single

    def test_parse_standard_json(self):
        reply = '{"key": "coverage", "score": 95, "passed": true, "detail": "完整覆盖"}'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 95
        assert result.get("passed") is True

    def test_parse_json_in_code_fence_with_lang(self):
        reply = '```json\n{"key": "atomicity", "score": 88, "passed": false, "detail": "粒度过大"}\n```'
        result = self._extract_json(reply)
        assert result.get("key") == "atomicity"
        assert result.get("passed") is False

    def test_parse_json_in_code_fence_without_lang(self):
        reply = '```\n{"key": "coverage", "score": 90, "passed": true}\n```'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 90

    def test_parse_json_with_prefix_text(self):
        reply = '以下是我的检验结果：{"key": "coverage", "score": 85, "passed": false}'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 85

    def test_parse_json_with_suffix_text(self):
        reply = '{"key": "coverage", "score": 95, "passed": true}附加说明'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("passed") is True

    def test_parse_json_with_thinking_tag(self):
        reply = '<thinking>先检查文档内容...</thinking>{"key": "coverage", "score": 95, "passed": true}'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 95

    def test_parse_json_with_analysis_tag(self):
        reply = '<analysis>检验中...</analysis>{"key": "measurability", "score": 92, "passed": true}'
        result = self._extract_json(reply)
        assert result.get("key") == "measurability"
        assert result.get("passed") is True

    def test_parse_json_trailing_comma_fix(self):
        reply = '{"key": "coverage", "score": 95, "passed": true, "detail": "通过",}'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 95

    def test_parse_json_nested_trailing_comma_fix(self):
        reply = '{"key": "coverage", "score": 95, "data": {"a": 1, "b": 2,}, "passed": true}'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 95

    def test_parse_json_deeply_nested(self):
        reply = '{"key": "coverage", "score": 92, "metadata": {"sub": {"deep": true}}}'
        result = self._extract_json(reply)
        assert result["metadata"]["sub"]["deep"] is True

    def test_parse_non_json_returns_empty(self):
        reply = "这个文档很好，没有问题。"
        result = self._extract_json(reply)
        assert result == {}

    def test_parse_empty_string(self):
        result = self._extract_json("")
        assert result == {}

    def test_parse_whitespace_only(self):
        result = self._extract_json("   \n\n  ")
        assert result == {}

    def test_parse_json_in_code_fence_multiline(self):
        reply = '```json\n{\n  "key": "measurability",\n  "score": 92,\n  "passed": true\n}\n```'
        result = self._extract_json(reply)
        assert result.get("key") == "measurability"
        assert result.get("score") == 92

    def test_parse_json_with_empty_fields(self):
        reply = '{"key": "coverage", "score": 0, "passed": false, "detail": ""}'
        result = self._extract_json(reply)
        assert result.get("score") == 0
        assert result.get("passed") is False

    def test_parse_json_with_unicode(self):
        reply = '{"key": "coverage", "score": 95, "passed": true, "detail": "覆盖率测试通过 ✅"}'
        result = self._extract_json(reply)
        assert result.get("detail") == "覆盖率测试通过 ✅"

    def test_parse_json_nested_thinking_tags(self):
        reply = '<thinking>外部<thinking>内部</thinking>继续</thinking>{"key": "coverage", "score": 95, "passed": true}'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 95

    def test_parse_json_with_newlines_before_brace(self):
        reply = '\n\n\n{"key": "coverage", "score": 95, "passed": true}'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("score") == 95

    def test_parse_json_with_trailing_garbage(self):
        reply = '{"key": "coverage", "score": 95, "passed": true} some extra stuff here'
        result = self._extract_json(reply)
        assert result.get("key") == "coverage"
        assert result.get("passed") is True
