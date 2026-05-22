#!/usr/bin/env python3
"""DevFlow 依赖管理模块测试"""
import pytest


class TestDependencyCreation:
    @pytest.mark.asyncio
    async def test_create_dependency_success(self, client, test_user, test_task_ai, test_project, db_session):
        from app.utils.security import create_access_token
        from app.models.task import Task
        token = create_access_token(user_id=test_user.id)
        task2 = Task(
            id="task_002",
            project_id=test_project.id,
            name="后置任务",
            description="依赖前任务",
            type="coding",
            priority="medium",
            status="pending",
        )
        db_session.add(task2)
        db_session.commit()
        payload = {"source_task_id": test_task_ai.id, "target_task_id": task2.id}
        response = await client.post(
            f"/api/tasks/{test_task_ai.id}/depend",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        from app.models.dependency import TaskDependency
        deps = db_session.query(TaskDependency).filter(
            TaskDependency.source_task_id == test_task_ai.id,
            TaskDependency.target_task_id == task2.id,
        ).all()
        for dep in deps:
            db_session.delete(dep)
        db_session.commit()
        db_session.delete(task2)
        db_session.commit()


class TestDependencyList:
    @pytest.mark.asyncio
    async def test_list_dependencies(self, client, test_user, test_task_ai, db_session):
        from app.utils.security import create_access_token
        token = create_access_token(user_id=test_user.id)
        response = await client.get(
            f"/api/tasks/{test_task_ai.id}/depend",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
