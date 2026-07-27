# DevFlow v4.0 全量重构实施方案

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于 SRS_软件需求规格说明书.md v4.0，将 DevFlow 从当前 v3.x 重构为完整的 v4.0，实现16步 AI Agent 全自动开发流程、10个命名 Agent 角色、QA 门控机制、Agent 蜂群系统等全部新增功能。

**Architecture:** 以16步流程状态机为骨架驱动整个系统，10个命名 Agent 角色通过项目讨论群协作，QA 门控（後荣）在每步间作为质量关卡，蜂群系统（後发/後达）管理下层编程 Agent 并行执行原子化任务。后端采用 FastAPI + SQLAlchemy + Celery 异步调度，前端 Vue 3 + Pinia + WebSocket 实时同步，代码托管 Gitea 作为统一成果仓库。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy 2.0 / Alembic / Celery / PostgreSQL 14+ / Redis 6+ / Vue 3 / Element Plus / Pinia / WebSocket / Docker Compose / Gitea

---

## 阶段一：数据库层 — 新增 SRS v4.0 所需的全部数据表

### Task 1.1: 创建数据库迁移 — 新增 10 个命名 Agent 角色预设数据

**Files:**
- Create: `backend/alembic/versions/003_v4_agent_roles.py`
- Modify: `backend/app/models/agent.py`

**Step 1: 扩展 Agent 模型**

在 `backend/app/models/agent.py` 中新增字段：
- `role_name`: String(50) — 角色英文名（HaiMei, HouXing, ...）
- `chinese_name`: String(50) — 角色中文名（海梅, 后兴, ...）
- `role_type`: Enum('project_manager','requirement_analyst','architect','programmer','tester','cicd_engineer','doc_manager','qa','security_officer','system_admin','swarm_member')
- `is_named_role`: Boolean — 是否为10个命名角色之一
- `managed_swarms`: JSON — 如果是後发/後达，记录管理的蜂群列表

**Step 2: 创建迁移文件**

```python
# backend/alembic/versions/003_v4_agent_roles.py
"""v4.0: Add 10 named agent roles system

Revision ID: 003
Revises: 002
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # 1. 扩展 agents 表
    op.add_column('agents', sa.Column('role_name', sa.String(50), nullable=True))
    op.add_column('agents', sa.Column('chinese_name', sa.String(50), nullable=True))
    op.add_column('agents', sa.Column('role_type', sa.String(30), nullable=True))
    op.add_column('agents', sa.Column('is_named_role', sa.Boolean(), default=False))
    op.add_column('agents', sa.Column('managed_swarms', postgresql.JSON(), nullable=True))
    
    # 创建唯一约束
    op.create_unique_constraint('uq_agent_role_name', 'agents', ['role_name'])

def downgrade():
    op.drop_constraint('uq_agent_role_name', 'agents')
    op.drop_column('agents', 'managed_swarms')
    op.drop_column('agents', 'is_named_role')
    op.drop_column('agents', 'role_type')
    op.drop_column('agents', 'chinese_name')
    op.drop_column('agents', 'role_name')
```

**Step 3: 运行迁移并验证**

```bash
cd backend && alembic upgrade head
```

**Step 4: Commit**

```bash
git add backend/app/models/agent.py backend/alembic/versions/003_v4_agent_roles.py
git commit -m "feat(db): add 10 named agent roles fields to agents table"
```

---

### Task 1.2: 创建数据库迁移 — 16步流程与 QA 门控表

**Files:**
- Create: `backend/alembic/versions/004_v4_workflow_qa.py`
- Create: `backend/app/models/workflow_step.py`
- Create: `backend/app/models/qa_record.py`

**Step 1: 创建 WorkflowStep 模型**

```python
# backend/app/models/workflow_step.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class StepStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    QA_REVIEW = "qa_review"
    PASSED = "passed"
    REJECTED = "rejected"
    COMPLETED = "completed"

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    step_number = Column(Integer, nullable=False)  # 1-16
    step_name = Column(String(200), nullable=False)  # e.g., "第二步：核心目标确认"
    executor_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    status = Column(Enum(StepStatus), default=StepStatus.PENDING)
    input_artifacts = Column(JSON, nullable=True)  # 上一步产出的引用
    output_artifacts = Column(JSON, nullable=True)  # 本步产出的引用
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="workflow_steps")
    executor = relationship("Agent")
```

**Step 2: 创建 QARecord 模型（後荣检验记录）**

```python
# backend/app/models/qa_record.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class QAStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"

class QARecord(Base):
    __tablename__ = "qa_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    workflow_step_id = Column(Integer, ForeignKey("workflow_steps.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    qa_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)  # 后荣
    status = Column(Enum(QAStatus), default=QAStatus.PENDING)
    review_dimensions = Column(JSON, nullable=True)  # 检验维度列表
    problem_details = Column(Text, nullable=True)  # 不合格时的问题说明
    fix_suggestions = Column(Text, nullable=True)  # 修改建议
    inspected_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    workflow_step = relationship("WorkflowStep")
    qa_agent = relationship("Agent")
```

**Step 3: 更新 Project 模型，添加 current_step 字段**

在 `backend/app/models/project.py` 中新增：
- `current_step`: Integer, nullable=False, default=1
- `core_goal`: Text, nullable=True
- 添加 `workflow_steps = relationship("WorkflowStep", back_populates="project")`

**Step 4: 创建迁移文件并运行**

```bash
cd backend && alembic revision --autogenerate -m "v4_workflow_qa" && alembic upgrade head
```

**Step 5: Commit**

```bash
git add backend/alembic/versions/004_*.py backend/app/models/workflow_step.py backend/app/models/qa_record.py backend/app/models/project.py
git commit -m "feat(db): add 16-step workflow and QA gating tables"
```

---

### Task 1.3: 创建数据库迁移 — Agent 蜂群、安全审计、文档一致性表

**Files:**
- Create: `backend/alembic/versions/005_v4_swarm_security_docs.py`
- Create: `backend/app/models/swarm.py`
- Create: `backend/app/models/security_audit.py`
- Create: `backend/app/models/doc_version.py`

**Step 1: 创建 Swarm 模型**

```python
# backend/app/models/swarm.py
class SwarmPurpose(str, enum.Enum):
    CODE_WRITING = "code_writing"      # 后发的代码编写蜂群
    TEST_EXECUTION = "test_execution"  # 后达的测试蜂群

class Swarm(Base):
    __tablename__ = "swarms"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    manager_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)  # 后发/后达
    name = Column(String(200), nullable=False)
    purpose = Column(Enum(SwarmPurpose), nullable=False)
    step_number = Column(Integer, nullable=False)  # 关联的流程步骤号(7或9或11)
    members = Column(JSON, nullable=False)  # [{agent_id: 1, agent_type: "claude_code", skills: [...]}]
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    disbanded_at = Column(DateTime, nullable=True)

# SwarmTask: 蜂群中的子任务
class SwarmTask(Base):
    __tablename__ = "swarm_tasks"
    id = Column(Integer, primary_key=True, index=True)
    swarm_id = Column(Integer, ForeignKey("swarms.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    assigned_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    status = Column(String(20), default="pending")
    assigned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
```

**Step 2: 创建 SecurityAudit 模型**

```python
# backend/app/models/security_audit.py
class SecurityAudit(Base):
    __tablename__ = "security_audits"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    auditor_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)  # 后华
    code_audit_result = Column(JSON, nullable=True)  # 代码审计结果
    compliance_result = Column(JSON, nullable=True)  # 合规审查结果
    penetration_test_result = Column(JSON, nullable=True)  # 渗透测试结果
    vulnerabilities_found = Column(Integer, default=0)
    vulnerabilities_fixed = Column(Integer, default=0)
    overall_status = Column(String(20), default="in_progress")  # in_progress/passed/failed
    report_content = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

**Step 3: 创建 DocVersion 模型（文档一致性）**

```python
# backend/app/models/doc_version.py
class DocVersion(Base):
    __tablename__ = "doc_versions"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # srs/architecture/backend/frontend/database/deployment/operation/api/user_manual
    version = Column(String(20), nullable=False)
    content_hash = Column(String(64), nullable=False)
    is_consistent = Column(Boolean, default=True)  # 与其他文档是否一致
    last_modified_by = Column(Integer, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

**Step 4: 创建迁移并运行**

```bash
cd backend && alembic revision --autogenerate -m "v4_swarm_security_docs" && alembic upgrade head
```

**Step 5: Commit**

```bash
git add backend/alembic/versions/005_*.py backend/app/models/swarm.py backend/app/models/security_audit.py backend/app/models/doc_version.py
git commit -m "feat(db): add swarm, security audit, and doc version tables"
```

---

## 阶段二：服务层 — 核心业务逻辑

### Task 2.1: 16步流程状态机引擎

**Files:**
- Create: `backend/app/services/workflow_engine.py`
- Test: `backend/tests/test_workflow_engine.py`

**Step 1: 编写测试用例**

```python
# backend/tests/test_workflow_engine.py
import pytest
from app.services.workflow_engine import WorkflowEngine, StepDefinition

STEPS = [
    StepDefinition(1, "人类用户创建项目", None),
    StepDefinition(2, "海梅确认核心目标与搭建组织架构", "haimei"),
    StepDefinition(3, "后兴需求分析", "houxing"),
    StepDefinition(4, "后旺架构设计", "houwang"),
    StepDefinition(5, "后富建立开发环境", "houfu"),
    StepDefinition(6, "海梅制订TDD测试用例计划", "haimei"),
    StepDefinition(7, "后发蜂群编写TDD测试用例", "houfa"),
    StepDefinition(8, "海梅制订代码编写计划", "haimei"),
    StepDefinition(9, "后发蜂群编写功能代码", "houfa"),
    StepDefinition(10, "后富部署到测试环境", "houfu"),
    StepDefinition(11, "后达蜂群全面测试", "houda"),
    StepDefinition(12, "后华安全审计", "houhua"),
    StepDefinition(13, "后富部署到生产环境", "houfu"),
    StepDefinition(14, "后贵完善项目文档", "hougui"),
    StepDefinition(15, "海梅报告交付成果", "haimei"),
    StepDefinition(16, "用户满意度确认与迭代", "haimei"),
]

def test_workflow_initialization():
    """测试流程初始化：创建项目时自动创建16步工作流"""
    engine = WorkflowEngine(project_id=1, steps=STEPS)
    steps = engine.initialize()
    assert len(steps) == 16
    assert steps[0].step_number == 1
    assert steps[0].status == "completed"  # 第一步创建项目即完成

def test_step_progression_with_qa_gate():
    """测试步骤推进：必须通过QA检验才能进入下一步"""
    engine = WorkflowEngine(project_id=1, steps=STEPS)
    engine.initialize()
    
    # 尝试跳过QA直接进入第三步 → 应失败
    with pytest.raises(ValueError, match="必须通过QA检验"):
        engine.advance_step(3)
    
    # 正常推进：第二步QA通过 → 可进入第三步
    engine.complete_step(2)
    engine.pass_qa(2, qa_agent_id=8)  # 后荣检验通过
    assert engine.get_current_step() == 3

def test_qa_rejection_rollback():
    """测试QA驳回重做"""
    engine = WorkflowEngine(project_id=1, steps=STEPS)
    engine.initialize()
    
    engine.complete_step(2)
    result = engine.fail_qa(2, qa_agent_id=8, 
                            reason="核心目标不够明确",
                            suggestions=["请细化功能边界", "补充非功能需求"])
    assert result.requires_rework == True
    assert engine.get_current_step() == 2  # 仍在第二步

def test_step_iteration():
    """测试第16步：不满意回到第三步"""
    engine = WorkflowEngine(project_id=1, steps=STEPS)
    engine.initialize()
    
    # 模拟完整流程到15步
    for step in range(2, 16):
        engine.complete_step(step)
        engine.pass_qa(step, qa_agent_id=8)
    
    # 第16步用户不满意
    engine.user_dissatisfied(feedback="功能不完整，需要增加导出功能")
    assert engine.get_current_step() == 3  # 回到第三步
    
    # 已合格的产出保留，仅修改第三步开始的部分
    preserved = engine.get_preserved_artifacts()
    assert "project_repo" in preserved  # 第一步的代码仓库保留

def test_step_2_creates_discussion_group():
    """测试第二步自动创建项目讨论群"""
    engine = WorkflowEngine(project_id=1, steps=STEPS)
    engine.initialize()
    
    engine.complete_step(2)
    group = engine.get_project_group()
    assert group is not None
    member_names = [m["role_name"] for m in group.members]
    assert "haimei" in member_names
    assert "houxing" in member_names
    assert len(group.members) == 9
```

**Step 2: 运行测试验证失败**

```bash
cd backend && pytest tests/test_workflow_engine.py -v
# Expected: 全部 FAIL (模块不存在)
```

**Step 3: 实现 WorkflowEngine**

```python
# backend/app/services/workflow_engine.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from app.models.workflow_step import WorkflowStep, StepStatus
from app.models.qa_record import QARecord, QAStatus
from app.database import get_db

@dataclass
class StepDefinition:
    step_number: int
    name: str
    executor_role: Optional[str]  # None表示人类用户执行
    required_inputs: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)

class WorkflowEngine:
    """16步流程状态机引擎"""
    
    QA_REQUIRED_STEPS = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14}
    CODE_REPO_COMMIT_STEPS = {2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15}
    
    def __init__(self, project_id: int, steps: List[StepDefinition]):
        self.project_id = project_id
        self.steps = steps
        self._preserved_artifacts: Dict[str, Any] = {}
    
    def initialize(self) -> List[WorkflowStep]:
        """初始化16步工作流"""
        db = next(get_db())
        workflow_steps = []
        for sd in self.steps:
            ws = WorkflowStep(
                project_id=self.project_id,
                step_number=sd.step_number,
                step_name=sd.name,
                status=StepStatus.COMPLETED if sd.step_number == 1 else StepStatus.PENDING
            )
            db.add(ws)
            workflow_steps.append(ws)
        db.commit()
        return workflow_steps
    
    def get_current_step(self) -> int:
        """获取当前应执行的步骤号"""
        db = next(get_db())
        steps = db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id
        ).order_by(WorkflowStep.step_number).all()
        
        for step in steps:
            if step.status in [StepStatus.PENDING, StepStatus.REJECTED]:
                return step.step_number
        return 16  # 全部完成
    
    def advance_step(self, target_step: int):
        """推进到目标步骤（必须通过QA检验）"""
        current = self.get_current_step()
        if target_step > current:
            # 检查中间的步骤是否都通过了QA
            for s in range(current, target_step):
                if s in self.QA_REQUIRED_STEPS:
                    if not self._is_qa_passed(s):
                        raise ValueError(f"第{s}步必须通过QA检验才能进入下一步")
    
    def complete_step(self, step_number: int, artifacts: Dict = None):
        """标记步骤完成"""
        db = next(get_db())
        step = db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id,
            WorkflowStep.step_number == step_number
        ).first()
        step.status = StepStatus.QA_REVIEW if step_number in self.QA_REQUIRED_STEPS else StepStatus.COMPLETED
        if artifacts:
            step.output_artifacts = artifacts
        db.commit()
    
    def pass_qa(self, step_number: int, qa_agent_id: int) -> QARecord:
        """QA检验通过"""
        db = next(get_db())
        step = db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id,
            WorkflowStep.step_number == step_number
        ).first()
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        
        record = QARecord(
            project_id=self.project_id,
            workflow_step_id=step.id,
            qa_agent_id=qa_agent_id,
            status=QAStatus.PASSED
        )
        db.add(record)
        
        # 记录已保留的产出
        if step.output_artifacts:
            self._preserved_artifacts[f"step_{step_number}"] = step.output_artifacts
        
        # 提交到代码库
        if step_number in self.CODE_REPO_COMMIT_STEPS:
            self._commit_to_repo(step)
        
        db.commit()
        return record
    
    def fail_qa(self, step_number: int, qa_agent_id: int, 
                reason: str, suggestions: List[str]) -> QARecord:
        """QA检验不通过，退回重做"""
        db = next(get_db())
        step = db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id,
            WorkflowStep.step_number == step_number
        ).first()
        step.status = StepStatus.REJECTED
        
        record = QARecord(
            project_id=self.project_id,
            workflow_step_id=step.id,
            qa_agent_id=qa_agent_id,
            status=QAStatus.FAILED,
            problem_details=reason,
            fix_suggestions="\n".join(suggestions)
        )
        db.add(record)
        db.commit()
        return record
    
    def user_dissatisfied(self, feedback: str):
        """第16步用户不满意，回到第三步"""
        db = next(get_db())
        # 重置第三步到第16步的状态为pending（保留第一、二步）
        steps = db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id,
            WorkflowStep.step_number >= 3
        ).all()
        for step in steps:
            step.status = StepStatus.PENDING
            step.completed_at = None
        db.commit()
    
    def get_preserved_artifacts(self) -> Dict[str, Any]:
        """获取迭代中保留的已合格产出"""
        return self._preserved_artifacts
    
    def _is_qa_passed(self, step_number: int) -> bool:
        db = next(get_db())
        step = db.query(WorkflowStep).filter(
            WorkflowStep.project_id == self.project_id,
            WorkflowStep.step_number == step_number
        ).first()
        return step.status == StepStatus.COMPLETED
    
    def _commit_to_repo(self, step: WorkflowStep):
        """将检验合格的产出提交到 Gitea 代码库"""
        # 调用 repo_service 提交产出
        pass
```

**Step 4: 运行测试验证通过**

```bash
cd backend && pytest tests/test_workflow_engine.py -v
# Expected: 全部 PASS
```

**Step 5: Commit**

```bash
git add backend/app/services/workflow_engine.py backend/tests/test_workflow_engine.py
git commit -m "feat: implement 16-step workflow state machine engine"
```

---

### Task 2.2: 10 个命名 Agent 角色初始化服务

**Files:**
- Create: `backend/app/services/agent_role_service.py`
- Test: `backend/tests/test_agent_roles.py`

**Step 1: 编写测试**

```python
# backend/tests/test_agent_roles.py
def test_create_all_named_roles():
    """测试创建全部10个命名Agent角色"""
    service = AgentRoleService()
    roles = service.initialize_named_roles()
    assert len(roles) == 10
    names = {r.role_name for r in roles}
    assert names == {"haimei", "houxing", "houwang", "houfa", "houda", 
                     "houfu", "hougui", "hourong", "houhua"}

def test_haimei_is_default_hermes():
    """测试海梅被标记为默认Hermes Agent"""
    service = AgentRoleService()
    haimei = service.get_role_by_name("haimei")
    assert haimei.role_type == "project_manager"
    assert haimei.chinese_name == "海梅"
    assert haimei.is_named_role == True

def test_role_responsibilities():
    """测试每个角色的职责定义正确"""
    service = AgentRoleService()
    
    # 后兴：需求分析师
    houxing = service.get_role_by_name("houxing")
    assert houxing.role_type == "requirement_analyst"
    
    # 后荣：QA
    hourong = service.get_role_by_name("hourong")
    assert hourong.role_type == "qa"
    
    # 后发/后达：可管理蜂群
    houfa = service.get_role_by_name("houfa")
    assert houfa.role_type == "programmer"
    
    houda = service.get_role_by_name("houda")
    assert houda.role_type == "tester"
```

**Step 2: 实现 AgentRoleService**

```python
# backend/app/services/agent_role_service.py
NAMED_ROLES = [
    {"role_name": "haimei", "chinese_name": "海梅", "role_type": "project_manager",
     "description": "默认Hermes Agent，项目经理，负责任务分派，对项目交付成果负责"},
    {"role_name": "houxing", "chinese_name": "后兴", "role_type": "requirement_analyst",
     "description": "需求分析师，负责需求分析，产出完整准确的软件需求说明书"},
    {"role_name": "houwang", "chinese_name": "后旺", "role_type": "architect",
     "description": "架构设计师，负责架构设计、后端设计、前端设计、数据库设计"},
    {"role_name": "houfa", "chinese_name": "后发", "role_type": "programmer",
     "description": "程序员，负责建立代码编写Agent蜂群，监督蜂群完成TDD测试用例和代码编写"},
    {"role_name": "houda", "chinese_name": "后达", "role_type": "tester",
     "description": "测试员，负责建立代码测试Agent蜂群，执行全面测试"},
    {"role_name": "houfu", "chinese_name": "后富", "role_type": "cicd_engineer",
     "description": "CI/CD工程师，负责开发环境搭建和代码部署"},
    {"role_name": "hougui", "chinese_name": "后贵", "role_type": "doc_manager",
     "description": "文档管理员，负责项目文档一致性管理"},
    {"role_name": "hourong", "chinese_name": "后荣", "role_type": "qa",
     "description": "QA，检验每个Agent产出，未达标退回重做，达标放行并提交代码库"},
    {"role_name": "houhua", "chinese_name": "后华", "role_type": "security_officer",
     "description": "安全员，负责代码审计、合规审查、渗透测试、漏洞修复"},
]
```

**Step 3: 运行测试 → Commit**

---

### Task 2.3: Agent 蜂群管理服务

**Files:**
- Create: `backend/app/services/swarm_service.py`
- Test: `backend/tests/test_swarm.py`

**核心业务逻辑：**

```python
class SwarmService:
    SUPPORTED_SWARM_AGENTS = [
        "claude_code", "codex", "opencode", "cursor", 
        "codearts", "trae", "lingma", "hermes_sub_agent", "pi_coding_agent"
    ]
    
    async def create_swarm(self, project_id: int, manager_role: str, 
                           purpose: SwarmPurpose, step_number: int) -> Swarm:
        """後发或後达建立Agent蜂群"""
        # 验证管理者权限：後发只能建代码蜂群，後达只能建测试蜂群
        # 自动匹配可用编程Agent
        # 创建 Swarm 记录，初始化成员列表
    
    async def dispatch_tasks(self, swarm_id: int, tasks: List[Task]) -> List[SwarmTask]:
        """将原子化任务分发给蜂群成员"""
        # 按技能匹配分配任务
        # 按任务依赖图排序
        # 前后依赖任务分配给不同Agent
    
    async def monitor_progress(self, swarm_id: int) -> SwarmProgress:
        """监控蜂群执行进度"""
        # 实时收集各Agent进度
        # 汇总整体进度百分比
    
    async def collect_results(self, swarm_id: int) -> List[TaskResult]:
        """收集蜂群Agent交付成果"""
```

测试用例覆盖：
- 後发创建代码编写蜂群
- 後达创建测试蜂群
- 任务按技能匹配分发
- 前后任务分配不同Agent
- 蜂群进度监控
- 成果收集与提交

---

### Task 2.4: QA 门控检验服务

**Files:**
- Create: `backend/app/services/qa_gate_service.py`
- Test: `backend/tests/test_qa_gate.py`

```python
class QAGateService:
    INSPECTION_DIMENSIONS = {
        "core_goal": ["目标明确性", "组织完整性", "讨论群建立状态"],
        "srs": ["完整性", "一致性", "可验证性", "无歧义性"],
        "design": ["设计完整性", "需求覆盖度", "技术可行性", "架构合理性"],
        "dev_env": ["可用性", "配置正确性", "依赖完整性"],
        "tdd_plan": ["覆盖率", "原子化程度", "验收标准可量化性"],
        "tdd_code": ["正确性", "覆盖率", "原子化", "验收标准匹配"],
        "code_plan": ["任务原子化", "测试用例对应完整性", "依赖关系正确性"],
        "function_code": ["正确性", "测试通过率", "需求匹配度", "代码规范"],
        "test_report": ["覆盖率", "通过率", "缺陷严重度", "实操验证结果"],
        "security_audit": ["漏洞修复率", "合规达标", "渗透测试通过情况"],
        "project_docs": ["完整性", "文档间一致性", "描述准确性"],
    }
    
    async def inspect(self, workflow_step_id: int, artifact_type: str, 
                      qa_agent_id: int) -> QARecord:
        """后荣对产出进行检验"""
    
    async def rollback(self, qa_record_id: int, reason: str, 
                       suggestions: List[str]) -> QARecord:
        """检验不通过，退回重做"""
```

---

## 阶段三：API 层 — 新增 SRS §7 要求的全部接口

### Task 3.1: 16步流程调度 API

**Files:**
- Create: `backend/app/api/workflow.py`
- Test: `backend/tests/test_api_workflow.py`

实现 SRS §7.1.3 的全部端点：

```python
router = APIRouter(prefix="/api/projects", tags=["workflow"])

@router.post("/{project_id}/step2")   # 第二步：海梅确认核心目标+搭建组织架构+建立讨论群
@router.post("/{project_id}/step3")   # 第三步：海梅→后兴需求分析（含需求评审会）
@router.post("/{project_id}/step4")   # 第四步：海梅→后旺架构设计（含4份设计文档逐份检验）
@router.post("/{project_id}/step5")   # 第五步：海梅→后富建立开发环境
@router.post("/{project_id}/step6")   # 第六步：海梅制订TDD测试用例计划（原子化+可量化）
@router.post("/{project_id}/step7")   # 第七步：海梅→后发(蜂群)编写TDD测试用例
@router.post("/{project_id}/step8")   # 第八步：海梅制订代码编写计划（含任务依赖图）
@router.post("/{project_id}/step9")   # 第九步：海梅→后发(蜂群)按依赖图编写功能代码
@router.post("/{project_id}/step10")  # 第十步：海梅→后富部署到测试环境
@router.post("/{project_id}/step11")  # 第十一步：海梅→后达(蜂群)全面测试
@router.post("/{project_id}/step12")  # 第十二步：海梅→后华安全审计
@router.post("/{project_id}/step13")  # 第十三步：海梅→后富部署到生产环境
@router.post("/{project_id}/step14")  # 第十四步：海梅→后贵完善文档（含一致性校验）
@router.post("/{project_id}/step15")  # 第十五步：海梅报告交付成果
@router.post("/{project_id}/step16")  # 第十六步：用户满意度确认/迭代回到第三步
```

---

### Task 3.2: QA 门控 API

**Files:**
- Create: `backend/app/api/qa.py`
- Test: `backend/tests/test_api_qa.py`

实现 SRS §7.1.4：

```python
router = APIRouter(prefix="/api/qa", tags=["qa"])

@router.post("/{task_id}/inspect")    # 后荣检验Agent产出
@router.get("/{project_id}/records")  # 获取项目QA检验记录列表
@router.post("/{task_id}/rollback")   # 退回重做（附带修改建议）
@router.get("/{task_id}/status")      # 获取当前检验状态
```

---

### Task 3.3: Agent 蜂群 API

**Files:**
- Create: `backend/app/api/swarms.py`
- Test: `backend/tests/test_api_swarms.py`

实现 SRS §7.1.5：

```python
router = APIRouter(prefix="/api/swarms", tags=["swarms"])

@router.post("/")                # 建立Agent蜂群（後发/後达）
@router.get("/{swarm_id}")       # 获取蜂群详情
@router.post("/{swarm_id}/dispatch")  # 蜂群调度分发任务到蜂群成员
@router.get("/{swarm_id}/progress")   # 获取蜂群整体执行进度
@router.delete("/{swarm_id}")         # 解散蜂群
```

---

### Task 3.4: 安全审计 API

**Files:**
- Create: `backend/app/api/security.py`
- Test: `backend/tests/test_api_security.py`

```python
router = APIRouter(prefix="/api/security", tags=["security"])

@router.post("/{project_id}/audit")         # 后华执行安全审计
@router.get("/{project_id}/audit/status")   # 获取审计状态
@router.get("/{project_id}/audit/report")   # 获取安全审计报告
```

---

### Task 3.5: 注册所有新路由到 main.py

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/__init__.py`

将 workflow, qa, swarms, security 路由注册到 FastAPI app。

---

## 阶段四：前端 — 新增 v4.0 核心页面

### Task 4.1: 16步流程进度视图

**Files:**
- Create: `frontend/src/views/WorkflowView.vue`
- Create: `frontend/src/components/workflow/StepCard.vue`
- Create: `frontend/src/components/workflow/StepTimeline.vue`
- Create: `frontend/src/stores/useWorkflowStore.ts`

核心组件：
- **StepTimeline**: 可视化16步流程进度条，用颜色区分状态（pending/active/qa_review/passed/rejected/completed）
- **StepCard**: 每步详情卡片，展示执行者、输入、产出、QA门控状态
- **WorkflowView**: 流程全景视图，集成 StepTimeline + StepCard + QA 操作面板

### Task 4.2: 项目讨论群视图

**Files:**
- Modify: `frontend/src/views/ChatView.vue` — 升级为项目讨论群视图
- Create: `frontend/src/components/chat/AgentMentionInput.vue`
- Create: `frontend/src/components/chat/MeetingLauncher.vue`

新增：
- Agent @mention 自动补全
- 会议模式启动面板（4种会议类型）
- 讨论模式/会议模式状态切换
- 会议纪要内嵌展示

### Task 4.3: Agent 蜂群管理视图

**Files:**
- Create: `frontend/src/views/SwarmView.vue`
- Create: `frontend/src/components/swarm/SwarmCreator.vue`
- Create: `frontend/src/components/swarm/SwarmProgress.vue`
- Create: `frontend/src/stores/useSwarmStore.ts`

功能：
- 蜂群创建面板（选择蜂群类型、成员）
- 蜂群任务分配可视化
- 蜂群进度实时监控
- 蜂群成果汇总展示

### Task 4.4: QA 门控面板

**Files:**
- Create: `frontend/src/views/QAView.vue`
- Create: `frontend/src/components/qa/InspectionForm.vue`
- Create: `frontend/src/components/qa/QAHistoryTable.vue`
- Create: `frontend/src/stores/useQAStore.ts`

### Task 4.5: 更新路由与导航

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/components/common/AppSidebar.vue`

新增路由：
- `/projects/:id/workflow` → WorkflowView
- `/projects/:id/swarm` → SwarmView
- `/projects/:id/qa` → QAView
- `/projects/:id/chat` → ChatView（升级版讨论群）
- `/projects/:id/security` → SecurityAuditView

---

## 阶段五：WebSocket — 实时事件推送

### Task 5.1: 新增 SRS §7.2 全部 WebSocket 事件

**Files:**
- Modify: `backend/app/ws/events.py`
- Modify: `backend/app/ws/manager.py`

新增事件类型：

```python
# 16步流程进展事件
PROJECT_STEP_STARTED = "project.step.started"
PROJECT_STEP_COMPLETED = "project.step.completed"
PROJECT_STEP_FAILED = "project.step.failed"

# QA门控事件
QA_INSPECTION_PASSED = "qa.inspection.passed"
QA_INSPECTION_FAILED = "qa.inspection.failed"

# 蜂群事件
SWARM_TASK_DISPATCHED = "swarm.task.dispatched"
SWARM_PROGRESS_UPDATED = "swarm.progress.updated"

# 安全审计事件
SECURITY_AUDIT_STARTED = "security.audit.started"
SECURITY_AUDIT_COMPLETED = "security.audit.completed"
```

---

## 阶段六：集成测试与验收

### Task 6.1: 全流程集成测试

**Files:**
- Create: `backend/tests/test_full_v4_workflow.py`

端到端测试覆盖全部16步：

```python
class TestFullV4Workflow:
    async def test_complete_16_step_flow(self):
        """测试：从项目创建到交付完成的完整16步流程"""
        # Step 1: Create Project
        # Step 2: HaiMei confirms core goal → QA pass
        # Step 3: HouXing SRS → QA pass → commit to repo
        # Step 4: HouWang designs → QA pass per doc → commit to repo
        # Step 5: HouFu dev env → QA pass
        # Step 6: HaiMei TDD plan → QA pass → commit to repo
        # Step 7: HouFa swarm TDD test cases → QA pass → commit to repo
        # Step 8: HaiMei code plan + dependency graph → QA pass → commit to repo
        # Step 9: HouFa swarm code → QA pass per task → commit to repo
        # Step 10: HouFu deploy to test env
        # Step 11: HouDa swarm testing → QA pass → commit to repo
        # Step 12: HouHua security audit → QA pass → commit to repo
        # Step 13: HouFu deploy to production
        # Step 14: HouGui docs → consistency check
        # Step 15: HaiMei report to user
        # Step 16: User satisfaction → project end
    
    async def test_iteration_loop(self):
        """测试：第16步不满意→回到第3步迭代"""
    
    async def test_qa_rejection_mid_flow(self):
        """测试：中间步骤QA驳回→退回重做→重新检验通过"""
    
    async def test_swarm_parallel_execution(self):
        """测试：蜂群并行执行任务"""
    
    async def test_discussion_group_communication(self):
        """测试：项目讨论群中Agent的实时沟通"""
```

### Task 6.2: 前端 E2E 测试

**Files:**
- Create: `frontend/tests/e2e/workflow.spec.ts`

用 Playwright 测试前端关键用户流程。

---

## 实施顺序总结

```
阶段一（数据库层）
  Task 1.1 → Task 1.2 → Task 1.3
         ↓
阶段二（服务层）
  Task 2.1 → Task 2.2 → Task 2.3 → Task 2.4
         ↓
阶段三（API层）
  Task 3.1 → Task 3.2 → Task 3.3 → Task 3.4 → Task 3.5
         ↓
阶段四（前端层）
  Task 4.1 → Task 4.2 → Task 4.3 → Task 4.4 → Task 4.5
         ↓
阶段五（WebSocket）
  Task 5.1
         ↓
阶段六（集成测试）
  Task 6.1 → Task 6.2
```

每个阶段内的任务可在验证无依赖冲突后并行执行。每个 Task 遵循 TDD（先写测试→验证失败→实现→验证通过→提交）。