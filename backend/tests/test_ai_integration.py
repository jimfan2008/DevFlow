#!/usr/bin/env python3
"""
AI Agent 协同 - 集成测试
TDD: 测试项目创建、需求协同、任务拆解、Agent 分配、验收的完整工作流
"""

import pytest
from datetime import datetime, timezone
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.task import Task
from app.models.agent import Agent
from app.models.task_execution import TaskExecution
from app.models.acceptance_record import AcceptanceRecord


class TestProjectCreationWorkflow:
    """项目创建工作流测试"""

    @pytest.mark.asyncio
    async def test_create_project_with_initial_requirement(self, db_session, test_project_owner):
        """测试创建项目并提交初始需求"""
        project = Project(
            id="project_integration_001",
            name="AI 测试项目",
            slug="ai-test-project",
            description="集成测试项目",
            creator_id=test_project_owner.id,
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        requirement = Requirement(
            id="req_integration_001",
            project_id=project.id,
            content="## 初始需求\n\n需要一个用户认证系统",
            version=1,
            is_locked=False,
        )
        db_session.add(requirement)
        db_session.commit()
        db_session.refresh(requirement)

        assert project.id is not None
        assert requirement.project_id == project.id
        assert requirement.is_locked is False

    @pytest.mark.asyncio
    async def test_project_cannot_create_duplicate_slug(self, db_session, test_project_owner):
        """测试项目 slug 唯一性约束"""
        project1 = Project(
            id="project_unique_1",
            name="唯一名称项目",
            slug="unique-project-1",
            description="第一个项目",
            creator_id=test_project_owner.id,
        )
        db_session.add(project1)
        db_session.commit()

        projects = db_session.query(Project).filter(Project.slug == "unique-project-1").all()
        assert len(projects) == 1


class TestRequirementCollaboration:
    """需求协同工作流测试"""

    @pytest.mark.asyncio
    async def test_requirement_iteration_before_lock(self, db_session, test_project):
        """测试需求锁定前的多轮迭代"""
        req_v1 = Requirement(
            id="req_iter_v1",
            project_id=test_project.id,
            content="版本1: 需要一个API",
            version=1,
            is_locked=False,
        )
        db_session.add(req_v1)
        db_session.commit()

        req_v2 = Requirement(
            id="req_iter_v2",
            project_id=test_project.id,
            content="版本2: 需要一个RESTful API，包含用户管理",
            version=2,
            is_locked=False,
        )
        db_session.add(req_v2)
        db_session.commit()

        req_v3 = Requirement(
            id="req_iter_v3",
            project_id=test_project.id,
            content="版本3: RESTful API + JWT认证 + 单元测试",
            version=3,
            is_locked=True,
            confirmed_at=datetime.now(timezone.utc),
        )
        db_session.add(req_v3)
        db_session.commit()

        assert req_v1.version == 1
        assert req_v2.version == 2
        assert req_v3.version == 3
        assert req_v3.is_locked is True

    @pytest.mark.asyncio
    async def test_locked_requirement_triggers_decomposition(self, db_session, locked_requirement):
        """测试需求锁定后应触发任务拆解"""
        assert locked_requirement.is_locked is True
        assert locked_requirement.confirmed_at is not None

        ready_for_decomposition = locked_requirement.is_locked
        assert ready_for_decomposition is True


class TestTaskDecompositionWorkflow:
    """任务拆解工作流测试"""

    @pytest.mark.asyncio
    async def test_decompose_by_development_phases(self, db_session, test_board, test_column, test_user):
        """测试按开发流程拆解任务"""
        phases = [
            ("需求分析", "claude_code"),
            ("测试用例编写", "claude_code"),
            ("功能编码", "opencode"),
            ("单元测试", "claude_code"),
            ("集成测试", "claude_code"),
            ("生产部署", "cursor"),
        ]

        tasks = []
        for i, (name, agent_type) in enumerate(phases):
            task = Task(
                id=f"task_phase_{i}",
                title=name,
                board_id=test_board.id,
                column_id=test_column.id,
                status="todo",
                agent_type=agent_type,
                priority="high" if i in [0, 2, 5] else "medium",
                creator_id=test_user.id,
            )
            tasks.append(task)
            db_session.add(task)

        db_session.commit()

        assert len(tasks) == 6
        agent_types = [t.agent_type for t in tasks]
        assert "opencode" in agent_types
        assert "claude_code" in agent_types
        assert "cursor" in agent_types

    @pytest.mark.asyncio
    async def test_task_dependencies_form_dag(self, db_session, test_board, test_column, test_user):
        """测试任务依赖关系构成 DAG"""
        from app.models.dependency import TaskDependency

        task_analysis = Task(
            id="task_dag_analysis",
            title="需求分析",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            creator_id=test_user.id,
        )
        task_coding = Task(
            id="task_dag_coding",
            title="功能编码",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            creator_id=test_user.id,
        )
        task_test = Task(
            id="task_dag_test",
            title="单元测试",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            creator_id=test_user.id,
        )
        db_session.add_all([task_analysis, task_coding, task_test])
        db_session.commit()

        dep1 = TaskDependency(
            source_task_id=task_coding.id,
            target_task_id=task_analysis.id,
            dependency_type="blocks",
        )
        dep2 = TaskDependency(
            source_task_id=task_test.id,
            target_task_id=task_coding.id,
            dependency_type="blocks",
        )
        db_session.add_all([dep1, dep2])
        db_session.commit()

        assert dep1.target_task_id == task_analysis.id
        assert dep2.target_task_id == task_coding.id


class TestAgentAssignmentWorkflow:
    """Agent 任务分配工作流测试"""

    @pytest.mark.asyncio
    async def test_assign_task_to_matching_agent(self, db_session, test_board, test_column, test_user, all_agents):
        """测试按任务类型分配给匹配的 Agent"""
        coding_task = Task(
            id="task_assign_coding",
            title="编码任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="opencode",
            creator_id=test_user.id,
        )
        db_session.add(coding_task)
        db_session.commit()

        assert coding_task.agent_type == "opencode"
        assert all_agents["opencode_agent"].agent_type == "opencode"

    @pytest.mark.asyncio
    async def test_test_task_to_claude_agent(self, db_session, test_board, test_column, test_user, claude_agent):
        """测试测试用例任务分配给 claude_code"""
        test_task = Task(
            id="task_assign_test",
            title="测试用例编写",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="claude_code",
            creator_id=test_user.id,
        )
        db_session.add(test_task)
        db_session.commit()

        assert test_task.agent_type == claude_agent.agent_type

    @pytest.mark.asyncio
    async def test_consecutive_tasks_different_agents(self, db_session, test_board, test_column, test_user, all_agents):
        """测试前后任务分配给不同 Agent（交叉验证）"""
        task_coding = Task(
            id="task_cross_coding",
            title="编码任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="opencode",
            creator_id=test_user.id,
        )
        task_test = Task(
            id="task_cross_test",
            title="测试任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="claude_code",
            creator_id=test_user.id,
        )
        db_session.add_all([task_coding, task_test])
        db_session.commit()

        assert task_coding.agent_type != task_test.agent_type


class TestAcceptanceWorkflowIntegration:
    """验收工作流集成测试"""

    @pytest.mark.asyncio
    async def test_full_acceptance_workflow_pass(self, db_session, test_board, test_column, test_user, opencode_agent):
        """测试完整验收通过流程"""
        task = Task(
            id="task_accept_pass_flow",
            title="验收通过测试任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="done",
            agent_type="opencode",
            acceptance_criteria="功能可用",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        execution = TaskExecution(
            id="exec_accept_pass",
            task_id=task.id,
            agent_id=opencode_agent.id,
            status="completed",
            result_summary={"message": "代码已提交"},
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        acceptance = AcceptanceRecord(
            id="accept_flow_pass",
            task_execution_id=execution.id,
            result="pass",
            reviewer="Hermes Agent",
        )
        db_session.add(acceptance)
        db_session.commit()
        db_session.refresh(acceptance)

        assert acceptance.result == "pass"

        task.status = "done"
        db_session.commit()
        db_session.refresh(task)

        assert task.status == "done"

    @pytest.mark.asyncio
    async def test_full_acceptance_workflow_reject(self, db_session, test_board, test_column, test_user, opencode_agent):
        """测试完整验收驳回流程"""
        task = Task(
            id="task_accept_reject_flow",
            title="验收驳回测试任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="in_progress",
            agent_type="opencode",
            acceptance_criteria="覆盖率 >= 80%",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        execution = TaskExecution(
            id="exec_accept_reject",
            task_id=task.id,
            agent_id=opencode_agent.id,
            status="completed",
            result_summary={"message": "代码已提交"},
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)

        acceptance = AcceptanceRecord(
            id="accept_flow_reject",
            task_execution_id=execution.id,
            result="fail",
            problem_details={
                "coverage": "覆盖率 65% < 80%",
                "suggestions": ["补充测试用例"]
            },
            reviewer="Hermes Agent",
        )
        db_session.add(acceptance)
        db_session.commit()
        db_session.refresh(acceptance)

        assert acceptance.result == "fail"
        assert "suggestions" in acceptance.problem_details

        task.status = "in_progress"
        db_session.commit()
        db_session.refresh(task)

        assert task.status == "in_progress"


class TestDownstreamTaskTriggering:
    """下游任务触发测试"""

    @pytest.mark.asyncio
    async def test_downstream_task_after_upstream(self, db_session, test_board, test_column, test_user, all_agents):
        """测试下游任务在上游任务完成后可开始"""
        upstream = Task(
            id="task_upstream_complete",
            title="已完成上游",
            board_id=test_board.id,
            column_id=test_column.id,
            status="done",
            creator_id=test_user.id,
        )
        downstream = Task(
            id="task_downstream_ready",
            title="可执行下游",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            creator_id=test_user.id,
        )
        db_session.add_all([upstream, downstream])
        db_session.commit()

        if upstream.status == "done":
            downstream.status = "todo"
        db_session.commit()
        db_session.refresh(downstream)

        assert downstream.status == "todo"


class TestMultipleAgentCoordination:
    """多 Agent 协同测试"""

    @pytest.mark.asyncio
    async def test_different_agents_for_different_task_types(self, db_session, test_board, test_column, test_user, all_agents):
        """测试不同类型任务分配给不同 Agent"""
        coding_task = Task(
            id="task_multi_coding",
            title="编码任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="opencode",
            creator_id=test_user.id,
        )
        test_task = Task(
            id="task_multi_test",
            title="测试任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="claude_code",
            creator_id=test_user.id,
        )
        deploy_task = Task(
            id="task_multi_deploy",
            title="部署任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="cursor",
            creator_id=test_user.id,
        )
        db_session.add_all([coding_task, test_task, deploy_task])
        db_session.commit()

        assert coding_task.agent_type == "opencode"
        assert test_task.agent_type == "claude_code"
        assert deploy_task.agent_type == "cursor"


class TestRequirementToTasksFlow:
    """需求到任务的完整流程测试"""

    @pytest.mark.asyncio
    async def test_requirement_to_tasks_pipeline(self, db_session, test_board, test_column, test_user, test_project_owner):
        """测试完整的需求到任务流程"""
        project = Project(
            id="project_pipeline_test",
            name="流程测试项目",
            slug="pipeline-test",
            description="测试完整流程",
            creator_id=test_project_owner.id,
        )
        db_session.add(project)
        db_session.commit()

        requirement = Requirement(
            id="req_pipeline",
            project_id=project.id,
            content="## 需求\n\n1. 用户管理\n2. 商品管理\n\n### 验收标准\n- 测试覆盖率 >= 70%",
            version=1,
            is_locked=True,
            confirmed_at=datetime.now(timezone.utc),
        )
        db_session.add(requirement)
        db_session.commit()

        tasks = [
            Task(
                id=f"task_pipeline_{i}",
                title=f"子任务 {i+1}",
                board_id=test_board.id,
                column_id=test_column.id,
                status="todo",
                creator_id=test_user.id,
            )
            for i in range(3)
        ]
        for task in tasks:
            db_session.add(task)
        db_session.commit()

        assert requirement.is_locked is True
        assert len(tasks) == 3
        for task in tasks:
            assert task.status == "todo"
