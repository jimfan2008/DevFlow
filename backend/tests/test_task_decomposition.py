#!/usr/bin/env python3
"""任务拆解模块 - 单元测试"""
import pytest
from app.models.task import Task
from app.models.dependency import TaskDependency


class TestTaskBasics:
    @pytest.mark.asyncio
    async def test_create_task(self, db_session, test_project):
        task = Task(
            id="task_basic_test",
            project_id=test_project.id,
            name="测试任务",
            description="这是一个测试任务",
            type="coding",
            status="pending",
            priority="medium",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.id == "task_basic_test"
        assert task.name == "测试任务"
        assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_task_to_dict(self, db_session, test_project):
        task = Task(
            id="task_serialize",
            project_id=test_project.id,
            name="序列化测试",
            type="coding",
            status="pending",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        result = task.to_dict()
        assert "id" in result
        assert "name" in result
        assert "status" in result


class TestTaskTypes:
    @pytest.mark.asyncio
    async def test_task_with_agent_type_preference(self, db_session, test_project):
        task = Task(
            id="task_agent_type",
            project_id=test_project.id,
            name="编码任务",
            type="coding",
            status="pending",
            agent_type_preference="opencode",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.agent_type_preference == "opencode"


class TestTaskPriorities:
    @pytest.mark.asyncio
    async def test_high_priority_task(self, db_session, test_project):
        task = Task(
            id="task_priority_high",
            project_id=test_project.id,
            name="核心功能",
            type="coding",
            status="pending",
            priority="high",
        )
        db_session.add(task)
        db_session.commit()
        assert task.priority == "high"

    @pytest.mark.asyncio
    async def test_medium_priority_task(self, db_session, test_project):
        task = Task(
            id="task_priority_medium",
            project_id=test_project.id,
            name="优化功能",
            type="coding",
            status="pending",
            priority="medium",
        )
        db_session.add(task)
        db_session.commit()
        assert task.priority == "medium"

    @pytest.mark.asyncio
    async def test_low_priority_task(self, db_session, test_project):
        task = Task(
            id="task_priority_low",
            project_id=test_project.id,
            name="可选功能",
            type="coding",
            status="pending",
            priority="low",
        )
        db_session.add(task)
        db_session.commit()
        assert task.priority == "low"


class TestTaskAcceptanceCriteria:
    @pytest.mark.asyncio
    async def test_task_with_acceptance_criteria(self, db_session, test_project):
        task = Task(
            id="task_acceptance_1",
            project_id=test_project.id,
            name="带验收标准的任务",
            type="coding",
            status="pending",
            acceptance_criteria="1. 功能可用\n2. 无明显bug",
        )
        db_session.add(task)
        db_session.commit()
        assert task.acceptance_criteria is not None


class TestTaskStatusFlow:
    VALID_STATUSES = ["pending", "assigned", "running", "delivered", "accepted", "rejected", "failed"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", VALID_STATUSES)
    async def test_valid_task_statuses(self, db_session, test_project, status):
        task = Task(
            id=f"task_status_{status}",
            project_id=test_project.id,
            name=f"{status} 状态任务",
            type="coding",
            status=status,
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.status == status

    @pytest.mark.asyncio
    async def test_task_status_transition_pending_to_assigned(self, db_session, test_project):
        task = Task(
            id="task_flow_1",
            project_id=test_project.id,
            name="流转测试",
            type="coding",
            status="pending",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        assert task.status == "pending"
        task.status = "assigned"
        db_session.commit()
        db_session.refresh(task)
        assert task.status == "assigned"

    @pytest.mark.asyncio
    async def test_delivered_task(self, db_session, test_project):
        task = Task(
            id="task_delivered_test",
            project_id=test_project.id,
            name="已交付任务",
            type="coding",
            status="delivered",
        )
        db_session.add(task)
        db_session.commit()
        assert task.status == "delivered"


class TestTaskDependencies:
    @pytest.mark.asyncio
    async def test_create_task_dependency(self, db_session, test_project):
        task_a = Task(
            id="task_dep_a",
            project_id=test_project.id,
            name="前置任务A",
            type="coding",
            status="pending",
        )
        task_b = Task(
            id="task_dep_b",
            project_id=test_project.id,
            name="后置任务B",
            type="coding",
            status="pending",
        )
        db_session.add_all([task_a, task_b])
        db_session.commit()
        dependency = TaskDependency(
            source_task_id=task_b.id,
            target_task_id=task_a.id,
        )
        db_session.add(dependency)
        db_session.commit()
        db_session.refresh(dependency)
        assert dependency.source_task_id == task_b.id
        assert dependency.target_task_id == task_a.id


class TestTaskDecomposition:
    @pytest.mark.asyncio
    async def test_decompose_by_development_phases(self, db_session, test_project):
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
                project_id=test_project.id,
                name=name,
                type="coding",
                status="pending",
                agent_type_preference=agent_type,
                priority="high" if i in [0, 2, 5] else "medium",
            )
            tasks.append(task)
            db_session.add(task)
        db_session.commit()
        assert len(tasks) == 6
        agent_types = [t.agent_type_preference for t in tasks]
        assert "opencode" in agent_types
        assert "claude_code" in agent_types
        assert "cursor" in agent_types
