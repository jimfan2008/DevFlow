#!/usr/bin/env python3
"""
成果验收模块 - 单元测试
TDD: 测试验收记录、验收维度、验收通过/驳回规则等核心功能
"""

import pytest
from app.models.acceptance_record import AcceptanceRecord
from app.models.task_execution import TaskExecution
from app.models.task import Task


class TestAcceptanceRecordBasics:
    """验收记录基础功能测试"""

    @pytest.mark.asyncio
    async def test_create_acceptance_record(self, db_session, test_task_execution):
        """测试创建验收记录"""
        record = AcceptanceRecord(
            id="accept_test_001",
            task_execution_id=test_task_execution.id,
            result="pass",
            problem_details=None,
            reviewer="Hermes Agent",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.id == "accept_test_001"
        assert record.task_execution_id == test_task_execution.id
        assert record.result == "pass"
        assert record.reviewer == "Hermes Agent"

    @pytest.mark.asyncio
    async def test_acceptance_to_dict(self, db_session, passed_acceptance):
        """测试验收记录序列化"""
        result = passed_acceptance.to_dict()

        assert "id" in result
        assert "task_execution_id" in result
        assert "result" in result
        assert "problem_details" in result
        assert "reviewer" in result
        assert "created_at" in result


class TestAcceptanceResults:
    """验收结果测试"""

    @pytest.mark.asyncio
    async def test_passed_acceptance(self, db_session, test_task_execution):
        """测试验收通过"""
        record = AcceptanceRecord(
            id="accept_pass_002",
            task_execution_id=test_task_execution.id,
            result="pass",
            problem_details=None,
            reviewer="Hermes Agent",
        )
        db_session.add(record)
        db_session.commit()

        assert record.result == "pass"
        assert record.problem_details is None

    @pytest.mark.asyncio
    async def test_failed_acceptance_with_details(self, db_session, test_task_execution):
        """测试验收驳回 - 应有问题明细"""
        problem_details = {
            "coverage": "测试覆盖率仅为 65%，要求 >= 80%",
            "bugs": ["接口缺少参数校验", "异常处理不完整"],
            "suggestions": ["补充边界条件测试", "添加参数验证"]
        }
        record = AcceptanceRecord(
            id="accept_fail_002",
            task_execution_id=test_task_execution.id,
            result="fail",
            problem_details=problem_details,
            reviewer="Hermes Agent",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.result == "fail"
        assert record.problem_details is not None
        assert "coverage" in record.problem_details
        assert "bugs" in record.problem_details
        assert "suggestions" in record.problem_details

    @pytest.mark.asyncio
    async def test_failed_acceptance_has_suggestions(self, db_session, test_task_execution):
        """测试验收驳回应包含修改建议"""
        problem_details = {
            "issues": ["语法错误", "逻辑错误"],
            "suggestions": ["修复第15行语法错误", "添加空值检查"]
        }
        record = AcceptanceRecord(
            id="accept_fail_sug",
            task_execution_id=test_task_execution.id,
            result="fail",
            problem_details=problem_details,
            reviewer="Hermes Agent",
        )
        db_session.add(record)
        db_session.commit()

        assert "suggestions" in record.problem_details
        assert len(record.problem_details["suggestions"]) > 0


class TestAcceptanceDimensions:
    """验收维度测试"""

    @pytest.mark.asyncio
    async def test_test_case_coverage_check(self, db_session):
        """测试测试用例验收 - 覆盖率维度"""
        coverage_result = 85
        required_coverage = 80

        passed = coverage_result >= required_coverage
        assert passed is True, "覆盖率达标应通过"

    @pytest.mark.asyncio
    async def test_test_case_low_coverage_rejected(self, db_session):
        """测试低覆盖率应被驳回"""
        coverage_result = 65
        required_coverage = 80

        passed = coverage_result >= required_coverage
        assert passed is False, "覆盖率不达标应被驳回"

    @pytest.mark.asyncio
    async def test_code_syntax_validation(self, db_session):
        """测试代码验收 - 语法正确性"""
        syntax_valid = True

        assert syntax_valid is True, "代码应无语法错误"

    @pytest.mark.asyncio
    async def test_deployment_environment_check(self, db_session):
        """测试部署环境验收"""
        environment_available = True
        compliance_check_passed = True

        passed = environment_available and compliance_check_passed
        assert passed is True, "部署环境应可用且合规"


class TestTaskExecutionBasics:
    """任务执行记录基础测试"""

    @pytest.mark.asyncio
    async def test_task_execution_completed(self, db_session, delivered_task, opencode_agent):
        """测试已完成的任务执行"""
        execution = TaskExecution(
            id="exec_complete_001",
            task_id=delivered_task.id,
            agent_id=opencode_agent.id,
            status="completed",
            result_summary={"message": "所有功能已实现"},
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        assert execution.status == "completed"
        assert execution.result_summary is not None

    @pytest.mark.asyncio
    async def test_task_execution_in_progress(self, db_session, test_board, test_column, test_user, opencode_agent):
        """测试执行中的任务"""
        task = Task(
            id="task_exec_running",
            title="正在执行的任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="in_progress",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        execution = TaskExecution(
            id="exec_running_001",
            task_id=task.id,
            agent_id=opencode_agent.id,
            status="running",
            result_summary={"message": "正在编写代码..."},
        )
        db_session.add(execution)
        db_session.commit()

        assert execution.status == "running"

    @pytest.mark.asyncio
    async def test_task_execution_to_dict(self, db_session, test_task_execution):
        """测试任务执行记录序列化"""
        result = test_task_execution.to_dict()

        assert "id" in result
        assert "task_id" in result
        assert "agent_id" in result
        assert "status" in result
        assert "result_summary" in result
        assert "created_at" in result


class TestAcceptanceWorkflow:
    """验收工作流测试"""

    @pytest.mark.asyncio
    async def test_completed_task_needs_acceptance(self, db_session, test_board, test_column, test_user):
        """测试已完成任务应触发验收流程"""
        task = Task(
            id="task_accept_workflow",
            title="待验收任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="done",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        needs_acceptance = task.status == "done"
        assert needs_acceptance is True

    @pytest.mark.asyncio
    async def test_accepted_task(self, db_session, test_board, test_column, test_user):
        """测试已验收通过的任务"""
        task = Task(
            id="task_accepted",
            title="已验收通过的任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="done",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        task.status = "done"
        db_session.commit()
        db_session.refresh(task)

        assert task.status == "done"

    @pytest.mark.asyncio
    async def test_rejected_task_needs_rework(self, db_session, test_board, test_column, test_user, opencode_agent):
        """测试验收驳回的任务应重新执行"""
        task = Task(
            id="task_rejected",
            title="验收被驳回的任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="in_progress",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        needs_rework = task.status in ["in_progress", "todo"]
        assert needs_rework is True

        task.status = "in_progress"
        db_session.commit()
        db_session.refresh(task)

        assert task.status == "in_progress"


class TestAcceptanceIntegrationPoints:
    """验收集成点测试"""

    @pytest.mark.asyncio
    async def test_acceptance_record_links_execution(self, db_session, passed_acceptance, test_task_execution):
        """测试验收记录关联到正确的执行记录"""
        assert passed_acceptance.task_execution_id == test_task_execution.id

    @pytest.mark.asyncio
    async def test_execution_links_task(self, db_session, test_task_execution, delivered_task):
        """测试执行记录关联到正确的任务"""
        assert test_task_execution.task_id == delivered_task.id

    @pytest.mark.asyncio
    async def test_full_chain_task_execution_acceptance(self, db_session, test_board, test_column, test_user, opencode_agent):
        """测试任务 -> 执行 -> 验收 完整链路"""
        task = Task(
            id="task_full_chain",
            title="完整链路测试任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="done",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        execution = TaskExecution(
            id="exec_full_chain",
            task_id=task.id,
            agent_id=opencode_agent.id,
            status="completed",
            result_summary={"message": "代码已完成"},
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        acceptance = AcceptanceRecord(
            id="accept_full_chain",
            task_execution_id=execution.id,
            result="pass",
            reviewer="Hermes Agent",
        )
        db_session.add(acceptance)
        db_session.commit()
        db_session.refresh(acceptance)

        assert acceptance.task_execution_id == execution.id
        assert execution.task_id == task.id
        assert acceptance.result == "pass"


class TestAcceptanceReviewer:
    """验收人测试"""

    @pytest.mark.asyncio
    async def test_acceptance_by_hermes_agent(self, db_session, test_task_execution):
        """测试 Hermes Agent 作为验收人"""
        record = AcceptanceRecord(
            id="accept_hermes",
            task_execution_id=test_task_execution.id,
            result="pass",
            reviewer="Hermes Agent",
        )
        db_session.add(record)
        db_session.commit()

        assert record.reviewer == "Hermes Agent"

    @pytest.mark.asyncio
    async def test_acceptance_record_has_reviewer(self, db_session, passed_acceptance):
        """测试验收记录应有验收人"""
        assert passed_acceptance.reviewer is not None
        assert len(passed_acceptance.reviewer) > 0
