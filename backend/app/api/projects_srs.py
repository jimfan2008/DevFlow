# 项目级 SRS API - 创建、任务查看、通知、完成
import uuid
import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.board import Board, BoardColumn
from app.models.group import Group
from app.models.enums import ProjectStatus
from app.services.decomposition_service import DecompositionService
from app.services.delivery_service import DeliveryService
from app.config import settings
from app.schemas.project_srs import (
    ProjectCreate, ProjectTaskListResponse,
    NotificationItem, NotificationListResponse,
    ProjectCompleteResponse,
)

logger = logging.getLogger("devflow.projects")

router = APIRouter(redirect_slashes=False)


@router.post("", response_model=dict)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.1.1 - 人类用户创建项目
    
    创建项目时同时初始化：
    1. 项目数据库记录
    2. 项目文件夹结构
    3. Gitea 代码仓库
    4. 工作流步骤（16步）
    5. 默认看板
    """
    existing = db.query(Project).filter(Project.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project name already exists")

    # 1. 创建项目数据库记录（含创建者成员、评审群组、状态）
    project = Project(
        id=str(uuid.uuid4()),
        name=data.name,
        slug=data.name.lower().replace(" ", "-").replace("_", "-"),
        description=data.description or "",
        creator_id=current_user.id,
        status=ProjectStatus.created.value,
    )
    db.add(project)
    db.flush()

    # 创建创建者成员记录
    member = ProjectMember(
        id=str(uuid.uuid4()),
        project_id=project.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(member)

    # 创建需求评审群组
    review_group = Group(
        id=str(uuid.uuid4()),
        name=f"{data.name}-需求评审",
        description=f"项目 {data.name} 的需求评审群组",
        members=[current_user.id],
        mode="discussion",
        project_id=project.id,
    )
    db.add(review_group)
    project.review_group_id = review_group.id

    db.commit()
    db.refresh(project)

    project_dir = None
    repo_created = False
    workflow_initialized = False
    board_created = False

    # 2. 附加初始化（文件夹、工作流、看板、仓库）
    # 如果失败不影响核心项目记录，但返回对应标记
    try:
        # 2a. 创建项目文件夹结构
        from app.config import settings
        project_dir = os.path.join(settings.PROJECTS_BASE_DIR, project.slug)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(os.path.join(project_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "tests"), exist_ok=True)

        readme_path = os.path.join(project_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# {project.name}\n\n")
            if project.description:
                f.write(f"{project.description}\n\n")
            f.write(f"Created: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n")
        logger.info(f"Project directory created: {project_dir}")

        # 2b. 初始化工作流步骤（16步）
        from app.services.workflow_engine import WorkflowEngine
        engine = WorkflowEngine(project_id=project.id, db=db)
        workflow_initialized = True
        logger.info(f"Workflow steps initialized for project {project.id}")

        # 2c. 创建默认看板
        board = Board(
            id=str(uuid.uuid4()),
            project_id=project.id,
            name=f"{project.name} - 开发看板",
            slug="default",
        )
        db.add(board)
        db.flush()
        db.refresh(board)

        column = BoardColumn(
            id=str(uuid.uuid4()),
            board_id=board.id,
            name="待办",
            slug="todo",
            position=0,
        )
        db.add(column)
        board_created = True
        logger.info(f"Default board created for project {project.id}")

        # 2d. 创建 Gitea 代码仓库（如果 Gitea 不可用，不影响项目创建）
        try:
            import asyncio
            from app.services.repo_service import RepoService
            repo_svc = RepoService(db)
            repo = asyncio.run(repo_svc.create_project_repo(project.id, project.name))
            repo_created = True
            logger.info(f"Gitea repo created for project {project.id}: {repo.name}")
        except Exception as e:
            logger.warning(f"Failed to create Gitea repo for project {project.id}: {e}")

        db.commit()

    except Exception as e:
        logger.error(f"Project initialization partially failed for {project.id}: {e}", exc_info=True)
        db.rollback()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "project": {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "status": project.status,
                "project_dir": project_dir or "",
                "workflow_initialized": workflow_initialized,
                "board_created": board_created,
                "repo_created": repo_created,
            }
        },
    }


@router.get("/{project_id}/tasks", response_model=dict)
def get_project_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.2 - 获取项目任务清单"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(Task).filter(Task.project_id == project_id).all()

    return {
        "code": 0,
        "message": "success",
        "data": {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.name,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority or "medium",
                    "assignee_id": t.assignee_agent_id,
                    "acceptance_criteria": t.acceptance_criteria,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
            "total": len(tasks),
            "project_id": project_id,
            "project_name": project.name,
        },
    }


@router.post("/{project_id}/decompose", response_model=dict)
def decompose_project_tasks(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.2.1 - 按开发流程自动拆解任务"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 获取需求内容
    from app.models.requirement import Requirement
    req = db.query(Requirement).filter(
        Requirement.project_id == project_id,
        Requirement.is_locked == True,
    ).first()
    if not req:
        raise HTTPException(status_code=400, detail="请先确认需求文档")

    # 获取或创建默认 Board
    board = db.query(Board).filter(Board.project_id == project_id).first()
    if not board:
        board = Board(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=f"{project.name} - 开发看板",
            slug="default",
        )
        db.add(board)
        db.commit()
        db.refresh(board)

    column = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).first()
    if not column:
        column = BoardColumn(
            id=str(uuid.uuid4()),
            board_id=board.id,
            name="待办",
            slug="todo",
            position=0,
        )
        db.add(column)
        db.commit()
        db.refresh(column)

    decomposition = DecompositionService(db=db)
    task_list = decomposition.decompose(project_id, req.content)
    decomposition.apply_priorities(task_list, project_id)
    created = decomposition.persist_tasks(task_list, board.id, column.id)

    return {
        "code": 0,
        "message": "success",
        "data": {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                }
                for t in created
            ],
            "total": len(created),
        },
    }


@router.get("/{project_id}/notifications", response_model=dict)
def get_project_notifications(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.5.1 - 获取项目通知列表"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    items = []
    unread = 0

    return {
        "code": 0,
        "message": "success",
        "data": {
            "notifications": [i.to_dict() for i in items],
            "total": len(items),
            "unread_count": unread,
        },
    }


@router.post("/{project_id}/complete", response_model=dict)
def complete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SRS §3.5.2 - 确认项目完成并发送通知"""
    from app.services.acceptance_service import AcceptanceService
    from app.services.delivery_service import DeliveryService

    # 先执行最终验收
    acceptance = AcceptanceService(db=db)
    final_result = acceptance.final_acceptance(project_id)

    if not final_result["passed"]:
        raise HTTPException(
            status_code=400,
            detail=f"项目有 {final_result['pending_tasks']} 个待处理任务和 {final_result['rejected_tasks']} 个驳回任务，请先处理",
        )

    # 完成项目交付
    delivery = DeliveryService(db=db)
    report = delivery.complete_project(project_id)

    return {
        "code": 0,
        "message": "success",
        "data": report,
    }