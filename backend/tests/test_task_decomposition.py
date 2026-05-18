#!/usr/bin/env python3
"""
任务拆解模块 - 单元测试
TDD: 测试任务类型、依赖关系、优先级设置等核心功能
"""

import pytest
from app.models.task import Task
from app.models.dependency import TaskDependency
from app.models.board import BoardColumn


class TestTaskBasics:
    """任务基础功能测试"""

    @pytest.mark.asyncio
    async def test_create_task(self, db_session, test_board, test_column, test_user):
        """测试创建新任务"""
        task = Task(
            id="task_basic_test",
            title="测试任务",
            description="这是一个测试任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.id == "task_basic_test"
        assert task.title == "测试任务"
        assert task.board_id == test_board.id
        assert task.status == "todo"

    @pytest.mark.asyncio
    async def test_task_to_dict(self, db_session, test_board, test_column, test_user):
        """测试任务序列化"""
        task = Task(
            id="task_serialize",
            title="序列化测试",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        result = task.to_dict()

        assert "id" in result
        assert "title" in result
        assert "board_id" in result
        assert "status" in result
        assert "priority" in result


class TestTaskTypes:
    """任务类型测试 - 按开发流程分类"""

    @pytest.mark.asyncio
    async def test_task_with_agent_type(self, db_session, test_board, test_column, test_user):
        """测试任务的 agent_type 字段"""
        task = Task(
            id="task_agent_type",
            title="编码任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="opencode",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.agent_type == "opencode"

    @pytest.mark.asyncio
    async def test_test_case_task_agent_type(self, db_session, test_board, test_column, test_user):
        """测试测试用例任务的 agent_type"""
        task = Task(
            id="task_test_case",
            title="测试用例编写",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="claude_code",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.agent_type == "claude_code"

    @pytest.mark.asyncio
    async def test_deployment_task_agent_type(self, db_session, test_board, test_column, test_user):
        """测试部署任务的 agent_type"""
        task = Task(
            id="task_deploy",
            title="生产环境部署",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="cursor",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.agent_type == "cursor"


class TestTaskPriorities:
    """任务优先级测试"""

    @pytest.mark.asyncio
    async def test_high_priority_task(self, db_session, test_board, test_column, test_user):
        """测试高优先级任务"""
        task = Task(
            id="task_priority_high",
            title="核心功能",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            priority="high",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.priority == "high"

    @pytest.mark.asyncio
    async def test_medium_priority_task(self, db_session, test_board, test_column, test_user):
        """测试中优先级任务"""
        task = Task(
            id="task_priority_medium",
            title="优化功能",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            priority="medium",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.priority == "medium"

    @pytest.mark.asyncio
    async def test_low_priority_task(self, db_session, test_board, test_column, test_user):
        """测试低优先级任务"""
        task = Task(
            id="task_priority_low",
            title="可选功能",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            priority="low",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.priority == "low"


class TestTaskAcceptanceCriteria:
    """任务验收标准测试"""

    @pytest.mark.asyncio
    async def test_task_with_acceptance_criteria(self, db_session, test_board, test_column, test_user):
        """测试任务包含验收标准"""
        task = Task(
            id="task_acceptance_1",
            title="带验收标准的任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            acceptance_criteria="1. 功能可用\n2. 无明显bug",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.acceptance_criteria is not None
        assert "功能可用" in task.acceptance_criteria

    @pytest.mark.asyncio
    async def test_test_case_task_specific_criteria(self, db_session, test_board, test_column, test_user):
        """测试测试用例任务的特殊验收标准"""
        task = Task(
            id="task_acceptance_test",
            title="测试用例编写",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            agent_type="claude_code",
            acceptance_criteria="1. 覆盖率 >= 80%\n2. 边界条件测试",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert "覆盖率" in task.acceptance_criteria
        assert "边界条件" in task.acceptance_criteria


class TestTaskStatusFlow:
    """任务状态流转测试"""

    VALID_STATUSES = ["todo", "in_progress", "testing", "done", "delivered", "accepted", "rejected", "pending"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", VALID_STATUSES)
    async def test_valid_task_statuses(self, db_session, test_board, test_column, test_user, status):
        """测试所有有效的任务状态"""
        task = Task(
            id=f"task_status_{status}",
            title=f"{status} 状态任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status=status,
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.status == status

    @pytest.mark.asyncio
    async def test_task_status_transition_pending_to_assigned(self, db_session, test_board, test_column, test_user):
        """测试任务状态流转：待分配 -> 已分配"""
        task = Task(
            id="task_flow_1",
            title="流转测试",
            board_id=test_board.id,
            column_id=test_column.id,
            status="pending",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        assert task.status == "pending"

        task.status = "in_progress"
        db_session.commit()
        db_session.refresh(task)

        assert task.status == "in_progress"

    @pytest.mark.asyncio
    async def test_delivered_task(self, db_session, test_board, test_column, test_user):
        """测试已交付的任务"""
        task = Task(
            id="task_delivered_test",
            title="已交付任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="done",
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.status == "done"


class TestTaskBlocking:
    """任务阻塞测试"""

    @pytest.mark.asyncio
    async def test_blocked_task(self, db_session, test_board, test_column, test_user):
        """测试被阻塞的任务"""
        task = Task(
            id="task_blocked",
            title="被阻塞的任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            is_blocked=True,
            blocked_by_count=1,
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.is_blocked is True
        assert task.blocked_by_count == 1

    @pytest.mark.asyncio
    async def test_unblocked_task(self, db_session, test_board, test_column, test_user):
        """测试未被阻塞的任务"""
        task = Task(
            id="task_unblocked",
            title="可执行任务",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            is_blocked=False,
            blocked_by_count=0,
            creator_id=test_user.id,
        )
        db_session.add(task)
        db_session.commit()

        assert task.is_blocked is False
        assert task.blocked_by_count == 0


class TestTaskDependencies:
    """任务依赖关系测试"""

    @pytest.mark.asyncio
    async def test_create_task_dependency(self, db_session, test_board, test_column, test_user):
        """测试创建任务依赖关系"""
        task_a = Task(
            id="task_dep_a",
            title="前置任务A",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            creator_id=test_user.id,
        )
        task_b = Task(
            id="task_dep_b",
            title="后置任务B",
            board_id=test_board.id,
            column_id=test_column.id,
            status="todo",
            creator_id=test_user.id,
        )
        db_session.add_all([task_a, task_b])
        db_session.commit()

        dependency = TaskDependency(
            source_task_id=task_b.id,
            target_task_id=task_a.id,
            dependency_type="blocks",
        )
        db_session.add(dependency)
        db_session.commit()
        db_session.refresh(dependency)

        assert dependency.source_task_id == task_b.id
        assert dependency.target_task_id == task_a.id
        assert dependency.dependency_type == "blocks"


class TestTaskDecomposition:
    """任务拆解测试 - 按开发流程"""

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
