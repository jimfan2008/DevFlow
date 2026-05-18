#!/usr/bin/env python3
"""依赖服务 - 依赖关系CRUD、循环检测"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid


class DependencyService:
    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def _import_models(self):
        from app.models.dependency import TaskDependency
        from app.models.task import Task
        return TaskDependency, Task

    def create_dependency(self, source_task_id: str, target_task_id: str) -> dict:
        TaskDependency, Task = self._import_models()
        if source_task_id == target_task_id:
            raise ValueError("任务不能依赖自身")
        source = self.db.query(Task).filter(Task.id == source_task_id).first()
        target = self.db.query(Task).filter(Task.id == target_task_id).first()
        if not source or not target:
            raise ValueError("任务不存在")
        # Check for cycle
        if self._would_create_cycle(source_task_id, target_task_id):
            raise ValueError("检测到循环依赖")
        # Check if already exists
        existing = self.db.query(TaskDependency).filter(
            TaskDependency.source_task_id == source_task_id,
            TaskDependency.target_task_id == target_task_id
        ).first()
        if existing:
            raise ValueError("依赖关系已存在")
        dep = TaskDependency(
            id=str(uuid.uuid4()),
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            dependency_type="finishes_to_starts",
        )
        self.db.add(dep)
        # Update target task blocked status
        target.blocked_by_count += 1
        target.is_blocked = True
        self.db.commit()
        self.db.refresh(dep)
        return dep.to_dict()

    def delete_dependency(self, source_task_id: str, target_task_id: str) -> bool:
        TaskDependency, = self._import_models()[:1]
        dep = self.db.query(TaskDependency).filter(
            TaskDependency.source_task_id == source_task_id,
            TaskDependency.target_task_id == target_task_id
        ).first()
        if not dep:
            raise ValueError("依赖关系不存在")
        self.db.delete(dep)
        target = self.db.query(Task).filter(Task.id == target_task_id).first()
        if target:
            target.blocked_by_count = max(0, target.blocked_by_count - 1)
            if target.blocked_by_count == 0:
                target.is_blocked = False
        self.db.commit()
        return True

    def get_dependencies(self, task_id: str) -> list:
        TaskDependency, Task = self._import_models()
        deps = self.db.query(TaskDependency).filter(
            (TaskDependency.source_task_id == task_id) |
            (TaskDependency.target_task_id == task_id)
        ).all()
        result = []
        for dep in deps:
            d = dep.to_dict()
            source_task = self.db.query(Task).filter(Task.id == dep.source_task_id).first()
            target_task = self.db.query(Task).filter(Task.id == dep.target_task_id).first()
            if source_task:
                d["source_task_title"] = source_task.title
            if target_task:
                d["target_task_title"] = target_task.title
            result.append(d)
        return result

    def get_dependency_graph(self, task_id: str) -> dict:
        TaskDependency, Task = self._import_models()
        predecessors = set()
        successors = set()
        self._find_predecessors(task_id, predecessors)
        self._find_successors(task_id, successors)
        all_deps = self.get_dependencies(task_id)
        return {
            "task_id": task_id,
            "predecessors": list(predecessors),
            "successors": list(successors),
            "all_dependencies": all_deps,
            "has_cycle": False,
        }

    def _would_create_cycle(self, source_id: str, target_id: str) -> bool:
        """Check if adding source->target would create a cycle"""
        TaskDependency, _ = self._import_models()
        if source_id == target_id:
            return True
        # Check if target can reach source
        visited = set()
        stack = [target_id]
        while stack:
            current = stack.pop()
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            deps = self.db.query(TaskDependency).filter(
                TaskDependency.source_task_id == current
            ).all()
            for dep in deps:
                stack.append(dep.target_task_id)
        return False

    def _find_predecessors(self, task_id: str, visited: set):
        TaskDependency = self._import_models()[0]
        deps = self.db.query(TaskDependency).filter(
            TaskDependency.target_task_id == task_id
        ).all()
        for dep in deps:
            if dep.source_task_id not in visited:
                visited.add(dep.source_task_id)
                self._find_predecessors(dep.source_task_id, visited)

    def _find_successors(self, task_id: str, visited: set):
        TaskDependency = self._import_models()[0]
        deps = self.db.query(TaskDependency).filter(
            TaskDependency.source_task_id == task_id
        ).all()
        for dep in deps:
            if dep.target_task_id not in visited:
                visited.add(dep.target_task_id)
                self._find_successors(dep.target_task_id, visited)
