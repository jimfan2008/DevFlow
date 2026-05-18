# 任务自动拆解服务 - 按开发流程将需求拆分为原子任务
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.project import Project
from app.models.board import Board, BoardColumn


class DecompositionService:
    def __init__(self, db: Session):
        self.db = db

    def decompose(self, project_id: str, requirement_content: str) -> list[dict]:
        """按软件开发流程将需求拆解为原子任务清单。"""
        features = self._extract_features(requirement_content)
        tasks = []

        for feature in features:
            tasks.extend(self._generate_tasks_for_feature(project_id, feature))

        return tasks

    def _extract_features(self, content: str) -> list[dict]:
        """从需求文档中提取核心功能模块。"""
        lines = content.split("\n")
        features = []
        current = None

        for line in lines:
            line = line.strip()
            if line.startswith("## ") or line.startswith("### "):
                if current:
                    features.append(current)
                current = {"name": line.lstrip("#").strip(), "description": "", "priority": "medium"}
            elif current and line:
                current["description"] += line + "\n"

        if current:
            features.append(current)

        if not features:
            features.append({"name": "默认功能模块", "description": content[:200], "priority": "medium"})

        return features

    def _generate_tasks_for_feature(self, project_id: str, feature: dict) -> list[dict]:
        """为单个功能模块生成完整的开发任务链路。"""
        name = feature["name"]
        priority = feature.get("priority", "medium")

        workflow_tasks = [
            {
                "title": f"{name} - 需求分析与细化",
                "description": f"细化功能模块 '{name}' 的需求细节，明确输入输出和边界条件",
                "type": "requirement_analysis",
                "priority": "high",
                "acceptance_criteria": "需求分析文档完成，包含功能点列表和验收标准",
            },
            {
                "title": f"{name} - 测试用例编写",
                "description": f"为功能模块 '{name}' 编写完整的测试用例",
                "type": "test_case",
                "priority": "high",
                "acceptance_criteria": "测试用例覆盖正常路径和异常路径",
            },
            {
                "title": f"{name} - 功能代码开发",
                "description": f"实现功能模块 '{name}' 的核心业务逻辑",
                "type": "feature_code",
                "priority": priority,
                "acceptance_criteria": "功能实现完整，通过对应测试用例",
            },
            {
                "title": f"{name} - 单元测试执行",
                "description": f"对功能模块 '{name}' 执行单元测试，确保代码质量",
                "type": "unit_test",
                "priority": "high",
                "acceptance_criteria": "单元测试通过率 >= 90%",
            },
            {
                "title": f"{name} - 集成测试",
                "description": f"对功能模块 '{name}' 进行集成测试，验证模块间交互",
                "type": "integration_test",
                "priority": "medium",
                "acceptance_criteria": "集成测试全部通过",
            },
            {
                "title": f"{name} - 部署环境准备",
                "description": f"准备功能模块 '{name}' 的生产部署环境",
                "type": "deployment",
                "priority": "medium",
                "acceptance_criteria": "部署环境可用，配置正确",
            },
        ]

        for i, t in enumerate(workflow_tasks):
            t["project_id"] = project_id
            t["feature_name"] = name
            t["order"] = i
            t["agent_type"] = self._select_agent(t["type"])

            if i > 0:
                t["dependency_on_prev"] = True

        return workflow_tasks

    def _select_agent(self, task_type: str) -> str:
        mapping = {
            "requirement_analysis": "hermes",
            "test_case": "claude_code",
            "feature_code": "opencode",
            "unit_test": "claude_code",
            "integration_test": "claude_code",
            "deployment": "cursor",
        }
        return mapping.get(task_type, "opencode")

    def apply_priorities(self, tasks: list[dict], project_id: str) -> list[dict]:
        """为任务设置优先级并标记核心/辅助/优化。"""
        for t in tasks:
            if t["type"] in ("requirement_analysis", "test_case", "feature_code"):
                t["priority"] = "high"
            elif t["type"] in ("unit_test", "deployment"):
                t["priority"] = "medium"
            else:
                t["priority"] = "low"
        return tasks

    def persist_tasks(self, tasks: list[dict], board_id: str, column_id: str) -> list[Task]:
        """将拆解后的任务持久化到数据库。"""
        from app.models.user import User
        creator_id = None
        admin = self.db.query(User).filter(User.role == "admin").first()
        if admin:
            creator_id = admin.id
        created = []
        for t in tasks:
            task = Task(
                id=str(uuid.uuid4()),
                title=t["title"],
                description=t["description"],
                acceptance_criteria=t.get("acceptance_criteria", ""),
                board_id=board_id,
                column_id=column_id,
                creator_id=creator_id or "system",
                status="todo",
                priority=t.get("priority", "medium"),
            )
            self.db.add(task)
            created.append(task)
        self.db.commit()
        return created