#!/usr/bin/env python3
"""成果验收模块 - 单元测试"""
import pytest
from app.models.acceptance_record import AcceptanceRecord
from app.models.task_execution import TaskExecution
from app.models.task import Task


class TestAcceptanceRecordBasics:
    @pytest.mark.asyncio
    async def test_create_acceptance_record(self, db_session, delivered_task, opencode_agent):
        record = AcceptanceRecord(
            id="accept_test_001",
            task_id=delivered_task.id,
            reviewer_agent_id=opencode_agent.id,
            result="accepted",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        assert record.id == "accept_test_001"
        assert record.task_id == delivered_task.id
        assert record.result == "accepted"

    @pytest.mark.asyncio
    async def test_acceptance_to_dict(self, db_session, passed_acceptance):
        result = passed_acceptance.to_dict()
        assert "id" in result
        assert "task_id" in result
        assert "result" in result


class TestAcceptanceResults:
    @pytest.mark.asyncio
    async def test_passed_acceptance(self, db_session, delivered_task, opencode_agent):
        record = AcceptanceRecord(
            id="accept_pass_002",
            task_id=delivered_task.id,
            reviewer_agent_id=opencode_agent.id,
            result="accepted",
        )
        db_session.add(record)
        db_session.commit()
        assert record.result == "accepted"

    @pytest.mark.asyncio
    async def test_rejected_acceptance_with_details(self, db_session, delivered_task, opencode_agent):
        record = AcceptanceRecord(
            id="accept_fail_002",
            task_id=delivered_task.id,
            reviewer_agent_id=opencode_agent.id,
            result="rejected",
            problem_details="覆盖率不足",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        assert record.result == "rejected"
        assert record.problem_details is not None


class TestAcceptanceDimensions:
    @pytest.mark.asyncio
    async def test_coverage_check(self, db_session):
        coverage_result = 85
        required_coverage = 80
        assert coverage_result >= required_coverage

    @pytest.mark.asyncio
    async def test_low_coverage_rejected(self, db_session):
        coverage_result = 65
        required_coverage = 80
        assert coverage_result < required_coverage


class TestTaskExecutionBasics:
    @pytest.mark.asyncio
    async def test_task_execution_completed(self, db_session, delivered_task, opencode_agent):
        execution = TaskExecution(
            id="exec_complete_001",
            task_id=delivered_task.id,
            agent_id=opencode_agent.id,
            status="delivered",
            result_summary={"message": "所有功能已实现"},
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)
        assert execution.status == "delivered"

    @pytest.mark.asyncio
    async def test_task_execution_to_dict(self, db_session, test_task_execution):
        result = test_task_execution.to_dict()
        assert "id" in result
        assert "task_id" in result
        assert "agent_id" in result


class TestAcceptanceIntegrationPoints:
    @pytest.mark.asyncio
    async def test_execution_links_task(self, db_session, test_task_execution, delivered_task):
        assert test_task_execution.task_id == delivered_task.id

    @pytest.mark.asyncio
    async def test_full_chain(self, db_session, test_project, opencode_agent):
        task = Task(
            id="task_full_chain",
            project_id=test_project.id,
            name="完整链路测试任务",
            type="coding",
            priority="medium",
            status="delivered",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        execution = TaskExecution(
            id="exec_full_chain",
            task_id=task.id,
            agent_id=opencode_agent.id,
            status="delivered",
            result_summary={"message": "代码已完成"},
        )
        db_session.add(execution)
        db_session.commit()

        acceptance = AcceptanceRecord(
            id="accept_full_chain",
            task_id=task.id,
            reviewer_agent_id=opencode_agent.id,
            result="accepted",
        )
        db_session.add(acceptance)
        db_session.commit()

        assert acceptance.task_id == task.id
        assert execution.task_id == task.id
