#!/usr/bin/env python3
"""
任务分解服务 - 根据需求自动拆解为可执行的原子任务
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from typing import List, Optional, Dict
import json

def _import_models():
    from app.models.requirement import Requirement
    from app.models.task import Task
    from app.models.project import Project
    from app.models.agent import Agent
    return Requirement, Task, Project, Agent

class TaskDecompositionService:
    def __init__(self, db: Session):
        self.db = db

    def decompose_tasks(self, project_id: str) -> List['Task']:
        """
        根据项目的确认需求，按软件开发流程拆解为原子任务
        按 SRS 3.2 节的拆解维度：
        - 需求分析细化任务
        - 测试用例编写任务
        - 功能模块编码任务
        - 单元/集成测试任务
        - 生产部署环境搭建任务
        - 整体联调任务
        """
        Requirement, Task, Project, Agent = _import_models()
        
        # 获取项目的确认需求
        requirement = self.db.query(Requirement).filter(
            and_(
                Requirement.project_id == project_id,
                Requirement.is_locked == True
            )
        ).first()
        
        if not requirement:
            raise ValueError(f"No confirmed requirement found for project {project_id}")
        
        # 获取项目信息
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # 定义任务模板：(名称, 描述模板, 建议的 agent_type, 依赖的前置任务名称)
        # 注意：依赖将在创建所有任务后通过名称映射来建立
        task_templates = [
            (
                "需求分析细化",
                "基于需求\"{requirement_content}\"进行详细分析，明确功能点、边界和验收标准",
                "opencode",  # 需求分析可以由 opencode 处理
                []  # 无前置依赖
            ),
            (
                "测试用例编写",
                "根据需求\"{requirement_content}\"编写详细的测试用例，包括单元测试、集成测试和验收测试",
                "claude_code",  # 测试用例编写优先分配 claude_code
                ["需求分析细化"]  # 依赖于需求分析
            ),
            (
                "功能模块编码",
                "根据需求\"{requirement_content}\"和测试用例，编写功能实现代码",
                "opencode",  # 功能代码编写支持 opencode/cursor/claude_code
                ["测试用例编写"]  # 依赖于测试用例（先写测试后写代码）
            ),
            (
                "单元/集成测试任务",
                "根据编写的功能代码和测试用例，执行单元和集成测试，确保代码质量",
                "claude_code",  # 集成测试优先分配 claude_code
                ["功能模块编码"]  # 依赖于功能编码
            ),
            (
                "生产部署环境搭建任务",
                "搭建能够生产部署的环境，包括数据库、缓存、服务器等基础设施",
                "cursor",  # 环境部署优先分配 cursor
                []  # 可以独立进行，但最好在需求分析后开始
            ),
            (
                "整体联调任务",
                "将所有功能模块集成进行整体联调，验证系统整体功能和性能",
                "opencode",  # 整体联调可以由 opencode 处理
                ["功能模块编码", "单元/集成测试任务", "生产部署环境搭建任务"]  # 依赖于编码、测试和环境
            )
        ]
        
        # 创建任务字典，以名称作为键，以便建立依赖关系
        created_tasks = {}
        
        # 先创建所有任务（不设置依赖）
        for name, desc_template, agent_type, _ in task_templates:
            task = Task(
                title=name,
                description=desc_template.format(requirement_content=requirement.content[:200]),  # 限制长度
                board_id=None,  # 临时没有 board，后续需要分配到项目的默认看板
                column_id=None,
                status="todo",
                priority="high" if "需求" in name or "测试" in name else "medium",
                agent_type=agent_type,
                acceptance_criteria=f"完成 {name}，并满足需求中相应的验收标准",
                creator_id=project.creator_id,  # 由项目创建者创建任务
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(task)
            self.db.flush()  # 获取 ID 但不提交
            created_tasks[name] = task
        
        # 现在建立依赖关系
        from app.models.dependency import TaskDependency
        for name, _, _, dependency_names in task_templates:
            task = created_tasks[name]
            for dep_name in dependency_names:
                if dep_name in created_tasks:
                    dep_task = created_tasks[dep_name]
                    # 创建依赖：dep_task -> task (dep_task 必须在 task 之前完成)
                    dependency = TaskDependency(
                        source_task_id=dep_task.id,  # 前置任务
                        target_task_id=task.id,      # 后置任务
                    )
                    self.db.add(dependency)
        
        # 提交所有更改
        self.db.commit()
        
        # 刷新所有任务对象以获取生成的字段
        for task in created_tasks.values():
            self.db.refresh(task)
        
        return list(created_tasks.values())