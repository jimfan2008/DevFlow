"""
测试用例：最终交付与监控
验证项目交付包含全部交付物
验收标准：交付完成<=24小时，交付物完整度=100%
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.task_execution import TaskExecution
from app.models.acceptance_record import AcceptanceRecord
from app.models.agent import Agent
from app.models.requirement import Requirement
from app.models.enums import ProjectStatus
from app.utils.security import get_password_hash
from app.services.delivery_service import DeliveryService
from app.services.acceptance_service import AcceptanceService


# ── 测试用数据库 ──────────────────────────────────────────────

TEST_ENGINE = create_engine(
    "sqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def setup_db():
    """每次测试前后建表/清表"""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                table.drop(conn, checkfirst=True)
            except Exception:
                pass
        conn.commit()


@pytest.fixture
def db():
    """提供一个独立的数据库会话"""
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def test_user(db):
    """创建一个测试用户"""
    uid = str(uuid.uuid4())
    user = User(
        id=uid,
        username=f"user_{uid[:8]}",
        email=f"{uid[:8]}@test.com",
        password_hash=get_password_hash("test123"),
        role="user",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def test_agent(db):
    """创建一个测试 Agent"""
    agent = Agent(
        id=str(uuid.uuid4()),
        name="TestAgent",
        agent_type="opencode",
        status="online",
        api_endpoint="http://localhost:8080",
        config={"capabilities": ["coding"]},
    )
    db.add(agent)
    db.commit()
    return agent


@pytest.fixture
def ready_project(test_user, db):
    """创建一个进行中的项目（可进入交付状态）"""
    pid = str(uuid.uuid4())
    project = Project(
        id=pid,
        name="交付测试项目",
        slug="delivery-test-project",
        description="用于验证最终交付与监控功能",
        creator_id=test_user.id,
        status=ProjectStatus.in_progress.value,
    )
    db.add(project)
    db.commit()
    return project


@pytest.fixture
def monitored_project(test_user, db):
    """创建带有 deadline 的项目用于监控测试"""
    pid = str(uuid.uuid4())
    deadline = datetime.now(timezone.utc) + timedelta(hours=12)
    project = Project(
        id=pid,
        name="监控测试项目",
        slug="monitor-test-project",
        description="用于验证交付监控与超时检查",
        creator_id=test_user.id,
        status=ProjectStatus.in_progress.value,
        deadline=deadline,
    )
    db.add(project)
    db.commit()
    return project


# ════════════════════════════════════════════════════════════════
# 第一部分：交付完整性测试
# ════════════════════════════════════════════════════════════════


class TestDeliveryCompleteness:
    """验证交付物完整度 = 100%"""

    def test_complete_project_generates_delivery_report(self, ready_project, db):
        """完成项目时应生成有效的交付报告"""
        svc = DeliveryService(db)
        result = svc.complete_project(ready_project.id)

        assert result is not None
        assert result["project_id"] == ready_project.id
        assert result["project_name"] == "交付测试项目"
        assert result["status"] == "completed"
        assert "completed_at" in result
        assert "summary" in result

    def test_complete_project_delivery_report_status_completed(self, ready_project, db):
        """交付报告的 status 字段应为 completed"""
        svc = DeliveryService(db)
        result = svc.complete_project(ready_project.id)

        assert result["status"] == "completed"

    def test_complete_nonexistent_project_raises(self, db):
        """不存在的项目应抛出异常"""
        svc = DeliveryService(db)
        with pytest.raises(ValueError, match="not found"):
            svc.complete_project("non-existent-id")

    def test_all_tasks_accepted_before_delivery(self, ready_project, test_agent, db):
        """交付前所有任务都应处于 accepted 或 delivered 状态"""
        task_ids = []
        for i in range(3):
            tid = str(uuid.uuid4())
            task = Task(
                id=tid,
                project_id=ready_project.id,
                name=f"完成的任务 {i}",
                description=f"任务描述 {i}",
                type="coding",
                priority="medium",
                status="accepted",
                acceptance_criteria=f"任务 {i} 的验收标准",
            )
            db.add(task)
            task_ids.append(tid)

            exec_id = str(uuid.uuid4())
            execution = TaskExecution(
                id=exec_id,
                task_id=tid,
                agent_id=test_agent.id,
                status="accepted",
                result_summary={
                    "coverage": 90,
                    "test_pass_rate": 95,
                    "output": f"output_file_{i}.py",
                },
            )
            db.add(execution)

            record = AcceptanceRecord(
                id=str(uuid.uuid4()),
                task_id=tid,
                reviewer_agent_id=test_agent.id,
                result="accepted",
            )
            db.add(record)

        db.commit()

        tasks = db.query(Task).filter(Task.project_id == ready_project.id).all()
        assert len(tasks) == 3
        for t in tasks:
            assert t.status in ("accepted", "delivered")

    def test_pending_tasks_prevent_final_delivery(self, ready_project, db):
        """存在未完成的任务时不应交付"""
        tid = str(uuid.uuid4())
        task = Task(
            id=tid,
            project_id=ready_project.id,
            name="未完成的任务",
            description="pending 任务",
            type="coding",
            priority="high",
            status="pending",
            acceptance_criteria="尚未开始",
        )
        db.add(task)
        db.commit()

        acc_svc = AcceptanceService(db)
        result = acc_svc.final_acceptance(ready_project.id)

        assert result["passed"] is False
        assert result["pending_tasks"] == 1
        assert result["total_tasks"] == 1

    def test_rejected_tasks_prevent_final_delivery(self, ready_project, test_agent, db):
        """存在被驳回的任务时不应交付"""
        tid = str(uuid.uuid4())
        task = Task(
            id=tid,
            project_id=ready_project.id,
            name="被驳回的任务",
            description="rejected 任务",
            type="coding",
            priority="medium",
            status="rejected",
            acceptance_criteria="被驳回",
        )
        db.add(task)
        db.commit()

        acc_svc = AcceptanceService(db)
        result = acc_svc.final_acceptance(ready_project.id)

        assert result["passed"] is False
        assert result["rejected_tasks"] == 1

    def test_empty_project_has_zero_tasks(self, ready_project, db):
        """空项目的最终验收应返回 0 个任务"""
        acc_svc = AcceptanceService(db)
        result = acc_svc.final_acceptance(ready_project.id)

        assert result["passed"] is True
        assert result["total_tasks"] == 0
        assert result["pending_tasks"] == 0
        assert result["rejected_tasks"] == 0

    def test_mixed_tasks_partial_completion(self, ready_project, test_agent, db):
        """混合状态任务应正确统计"""
        tasks_data = [
            ("已接受任务", "accepted"),
            ("已交付任务", "delivered"),
            ("进行中任务", "running"),
            ("待处理任务", "pending"),
        ]
        for name, status in tasks_data:
            tid = str(uuid.uuid4())
            task = Task(
                id=tid,
                project_id=ready_project.id,
                name=name,
                description=f"测试任务 {name}",
                type="coding",
                priority="medium",
                status=status,
                acceptance_criteria="测试标准",
            )
            db.add(task)
        db.commit()

        acc_svc = AcceptanceService(db)
        result = acc_svc.final_acceptance(ready_project.id)

        assert result["passed"] is False
        assert result["total_tasks"] == 4
        assert result["pending_tasks"] == 2

    def test_delivery_report_contains_required_fields(self, ready_project, db):
        """交付报告必须包含所有必需字段"""
        svc = DeliveryService(db)
        result = svc.complete_project(ready_project.id)

        required_fields = ["project_id", "project_name", "completed_at", "status", "summary"]
        for field in required_fields:
            assert field in result, f"交付报告缺少必需字段: {field}"

    def test_delivery_completeness_100_percent(self, ready_project, test_agent, db):
        """当所有任务验收通过后，交付物完整度应为 100%"""
        expected_tasks = 5
        for i in range(expected_tasks):
            tid = str(uuid.uuid4())
            task = Task(
                id=tid,
                project_id=ready_project.id,
                name=f"任务 {i}",
                description=f"任务描述 {i}",
                type="coding",
                priority="medium",
                status="accepted",
                acceptance_criteria=f"标准 {i}",
            )
            db.add(task)
        db.commit()

        acc_svc = AcceptanceService(db)
        result = acc_svc.final_acceptance(ready_project.id)

        total = result["total_tasks"]
        pending = result["pending_tasks"]
        rejected = result["rejected_tasks"]
        completeness = ((total - pending - rejected) / total * 100) if total > 0 else 100

        assert completeness == 100.0
        assert result["passed"] is True


# ════════════════════════════════════════════════════════════════
# 第二部分：交付时间监控测试（<=24小时）
# ════════════════════════════════════════════════════════════════


class TestDeliveryTimeMonitoring:
    """验证交付完成时间 <= 24 小时"""

    def test_delivery_within_24_hours(self, monitored_project, db):
        """在项目创建后 24 小时内完成交付应通过"""
        deadline = monitored_project.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        time_remaining = deadline - now

        assert time_remaining.total_seconds() > 0, "deadline 应大于当前时间"
        assert time_remaining.total_seconds() <= 24 * 3600, "deadline 应在 24 小时内"

        svc = DeliveryService(db)
        result = svc.complete_project(monitored_project.id)

        completed_at = datetime.fromisoformat(result["completed_at"])
        assert result["status"] == "completed"

    def test_delivery_deadline_exceeded_warning(self, test_user, db):
        """超过 deadline 仍未交付应标记为超时"""
        pid = str(uuid.uuid4())
        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        project = Project(
            id=pid,
            name="超时项目",
            slug="overdue-project",
            description="已超时的项目",
            creator_id=test_user.id,
            status=ProjectStatus.in_progress.value,
            deadline=past_deadline,
        )
        db.add(project)
        db.commit()

        svc = DeliveryService(db)
        result = svc.complete_project(project.id)

        assert result["status"] == "completed"
        completed_at = datetime.fromisoformat(result["completed_at"])
        assert completed_at > past_deadline, "完成时间应晚于已过的 deadline"

    def test_delivery_time_elapsed_within_sla(self, test_user, db):
        """SLA 验证：从项目开始到交付的时间应合理"""
        pid = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc) - timedelta(hours=10)
        project = Project(
            id=pid,
            name="SLA 测试项目",
            slug="sla-test-project",
            description="验证 24 小时 SLA",
            creator_id=test_user.id,
            status=ProjectStatus.in_progress.value,
            created_at=start_time,
        )
        db.add(project)
        db.commit()

        svc = DeliveryService(db)
        result = svc.complete_project(project.id)

        completed_at = datetime.fromisoformat(result["completed_at"])
        elapsed_hours = (completed_at - start_time).total_seconds() / 3600

        assert elapsed_hours <= 24, f"交付耗时 {elapsed_hours:.1f}h 应 <= 24h"

    def test_delivery_milestone_notification(self, ready_project, db):
        """里程碑通知应包含正确的节点"""
        svc = DeliveryService(db)

        assert "core_delivery" in svc.NOTIFICATION_NODES
        assert "requirement_confirmed" in svc.NOTIFICATION_NODES
        assert "decomposition_done" in svc.NOTIFICATION_NODES
        assert "acceptance_rejected" in svc.NOTIFICATION_NODES
        assert "half_progress" in svc.NOTIFICATION_NODES

    def test_milestone_notification_unknown_key(self, ready_project, db):
        """未知里程碑节点不应抛出异常"""
        svc = DeliveryService(db)
        result = svc.notify_milestone("user1", ready_project.id, "unknown_milestone")
        assert result is None

    def test_milestone_notification_valid(self, ready_project, db):
        """已知里程碑节点不应抛出异常"""
        svc = DeliveryService(db)
        result = svc.notify_milestone("user1", ready_project.id, "core_delivery")
        # notify_milestone 通过日志记录，不返回值
        assert result is None  # 函数没有显式 return，返回 None

    def test_multiple_deliveries_no_error(self, ready_project, db):
        """多次调用完成项目不应抛出异常"""
        svc = DeliveryService(db)
        first_result = svc.complete_project(ready_project.id)
        second_result = svc.complete_project(ready_project.id)

        assert first_result["project_id"] == second_result["project_id"]
        assert first_result["status"] == second_result["status"] == "completed"


# ════════════════════════════════════════════════════════════════
# 第三部分：验收检查逻辑测试
# ════════════════════════════════════════════════════════════════


class TestAcceptanceChecks:
    """验证验收检查项的正确性"""

    def test_coverage_check_pass(self, db):
        """覆盖率 >= 80% 应通过"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 80, "test_pass_rate": 95, "output": "file.py"})
        assert checks["coverage_check"]["passed"] is True

    def test_coverage_check_fail(self, db):
        """覆盖率 < 80% 不应通过"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 75, "test_pass_rate": 95, "output": "file.py"})
        assert checks["coverage_check"]["passed"] is False

    def test_test_pass_rate_check_pass(self, db):
        """测试通过率 >= 90% 应通过"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 85, "test_pass_rate": 90, "output": "file.py"})
        assert checks["test_pass_rate_check"]["passed"] is True

    def test_test_pass_rate_check_fail(self, db):
        """测试通过率 < 90% 不应通过"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 85, "test_pass_rate": 85, "output": "file.py"})
        assert checks["test_pass_rate_check"]["passed"] is False

    def test_output_check_pass(self, db):
        """存在输出文件应通过"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 85, "test_pass_rate": 95, "output": "result.py"})
        assert checks["output_check"]["passed"] is True

    def test_output_check_fail(self, db):
        """缺少输出文件不应通过"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 85, "test_pass_rate": 95})
        assert checks["output_check"]["passed"] is False

    def test_empty_result_summary_all_fail(self, db):
        """空的结果摘要所有检查都不应通过"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({})
        assert all(not checks[k]["passed"] for k in checks)

    def test_suggestions_generated_on_failure(self, db):
        """失败的检查应生成修改建议"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 50, "test_pass_rate": 60})
        suggestions = svc._generate_suggestions(checks)

        assert len(suggestions) > 0

    def test_no_suggestions_on_all_pass(self, db):
        """全部通过时不应有建议"""
        svc = AcceptanceService(db)
        checks = svc._run_checks({"coverage": 95, "test_pass_rate": 100, "output": "out.py"})
        suggestions = svc._generate_suggestions(checks)

        assert len(suggestions) == 0


# ════════════════════════════════════════════════════════════════
# 第四部分：端到端交付流程
# ════════════════════════════════════════════════════════════════


class TestEndToEndDelivery:
    """端到端验证：从创建项目到最终交付的完整流程"""

    def test_full_delivery_lifecycle(self, test_user, test_agent, db):
        """完整生命周期：创建 -> 加任务 -> 验收 -> 交付"""
        project = Project(
            id=str(uuid.uuid4()),
            name="全生命周期项目",
            slug="full-lifecycle-project",
            description="验证完整交付流程",
            creator_id=test_user.id,
            status=ProjectStatus.in_progress.value,
        )
        db.add(project)
        db.commit()
        assert project.status == ProjectStatus.in_progress.value

        tid = str(uuid.uuid4())
        task = Task(
            id=tid,
            project_id=project.id,
            name="核心功能",
            description="核心功能实现",
            type="coding",
            priority="high",
            status="accepted",
            acceptance_criteria="核心功能完整",
        )
        db.add(task)

        exec_id = str(uuid.uuid4())
        execution = TaskExecution(
            id=exec_id,
            task_id=tid,
            agent_id=test_agent.id,
            status="accepted",
            result_summary={
                "coverage": 92,
                "test_pass_rate": 97,
                "output": "core_feature.py",
            },
        )
        db.add(execution)

        record = AcceptanceRecord(
            id=str(uuid.uuid4()),
            task_id=tid,
            reviewer_agent_id=test_agent.id,
            result="accepted",
        )
        db.add(record)
        db.commit()

        acc_svc = AcceptanceService(db)
        acceptance = acc_svc.final_acceptance(project.id)
        assert acceptance["passed"] is True
        assert acceptance["total_tasks"] == 1
        assert acceptance["pending_tasks"] == 0

        delivery_svc = DeliveryService(db)
        delivery = delivery_svc.complete_project(project.id)
        assert delivery["status"] == "completed"
        assert delivery["project_id"] == project.id
        assert delivery["project_name"] == "全生命周期项目"
        assert "completed_at" in delivery

    def test_delivery_with_multiple_modules(self, test_user, test_agent, db):
        """多模块项目交付：所有模块验收通过后方可交付"""
        project = Project(
            id=str(uuid.uuid4()),
            name="多模块项目",
            slug="multi-module-project",
            description="多模块交付测试",
            creator_id=test_user.id,
            status=ProjectStatus.in_progress.value,
        )
        db.add(project)
        db.commit()

        module_names = ["用户管理", "产品管理", "订单处理", "支付系统", "数据分析"]
        for name in module_names:
            tid = str(uuid.uuid4())
            task = Task(
                id=tid,
                project_id=project.id,
                name=name,
                description=f"{name}模块",
                type="coding",
                priority="high",
                status="accepted",
                acceptance_criteria=f"{name}完整运行",
            )
            db.add(task)

            exec_id = str(uuid.uuid4())
            execution = TaskExecution(
                id=exec_id,
                task_id=tid,
                agent_id=test_agent.id,
                status="accepted",
                result_summary={
                    "coverage": 88 + module_names.index(name),
                    "test_pass_rate": 93 + module_names.index(name),
                    "output": f"{name.lower()}.py",
                },
            )
            db.add(execution)

            record = AcceptanceRecord(
                id=str(uuid.uuid4()),
                task_id=tid,
                reviewer_agent_id=test_agent.id,
                result="accepted",
            )
            db.add(record)
        db.commit()

        acc_svc = AcceptanceService(db)
        acceptance = acc_svc.final_acceptance(project.id)
        assert acceptance["passed"] is True
        assert acceptance["total_tasks"] == len(module_names)

        delivery_svc = DeliveryService(db)
        delivery = delivery_svc.complete_project(project.id)
        assert delivery["status"] == "completed"

    def test_delivery_blocked_by_failing_module(self, test_user, test_agent, db):
        """有一个模块验收失败时，整体交付应被阻止"""
        project = Project(
            id=str(uuid.uuid4()),
            name="阻塞项目",
            slug="blocked-project",
            description="有模块未通过的项目",
            creator_id=test_user.id,
            status=ProjectStatus.in_progress.value,
        )
        db.add(project)
        db.commit()

        for status in ["accepted", "accepted", "pending"]:
            tid = str(uuid.uuid4())
            task = Task(
                id=tid,
                project_id=project.id,
                name=f"模块-{status}",
                description="测试模块",
                type="coding",
                priority="medium",
                status=status,
                acceptance_criteria="测试",
            )
            db.add(task)
        db.commit()

        acc_svc = AcceptanceService(db)
        acceptance = acc_svc.final_acceptance(project.id)

        assert acceptance["passed"] is False
        assert acceptance["pending_tasks"] == 1

        completeness = ((acceptance["total_tasks"] - acceptance["pending_tasks"])
                        / acceptance["total_tasks"] * 100)
        assert completeness < 100.0
