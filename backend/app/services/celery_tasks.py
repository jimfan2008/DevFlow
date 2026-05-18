from __future__ import annotations

import logging

from celery import Celery
from app.config import settings

logger = logging.getLogger("devflow.celery")

celery_app = Celery(
    "devflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
)


@celery_app.task(name="decompose_tasks_task")
def decompose_tasks_task(project_id: str):
    logger.info(f"Starting task decomposition for project {project_id}")
    try:
        from app.database import sync_session_maker
        from app.models.project import Project
        from app.models.requirement import Requirement
        from app.models.task import Task
        from app.models.board import Board, BoardColumn
        from app.services.decomposition_service import DecompositionService
        from app.services.notification_service import NotificationService

        db = sync_session_maker()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                logger.error(f"Project {project_id} not found")
                return

            req = db.query(Requirement).filter(
                Requirement.project_id == project_id,
                Requirement.is_locked == True,
            ).first()
            if not req:
                logger.error(f"No confirmed requirement for project {project_id}")
                return

            board = db.query(Board).filter(Board.project_id == project_id).first()
            if not board:
                board = Board(
                    id=__import__('uuid').uuid4().hex,
                    project_id=project_id,
                    name=f"{project.name} - 开发看板",
                )
                db.add(board)
                db.commit()
                db.refresh(board)

            column = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).first()
            if not column:
                column = BoardColumn(
                    id=__import__('uuid').uuid4().hex,
                    board_id=board.id,
                    name="待办",
                    position=0,
                )
                db.add(column)
                db.commit()
                db.refresh(column)

            decomposition = DecompositionService(db=db)
            task_list = decomposition.decompose(project_id, req.content)
            decomposition.apply_priorities(task_list, project_id)
            created = decomposition.persist_tasks(task_list, board.id, column.id)

            notif_svc = NotificationService(db)
            if project.creator_id:
                notif_svc.notify_task_decomposed(project_id, project.creator_id, len(created))

            logger.info(f"Decomposed {len(created)} tasks for project {project_id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Task decomposition failed: {e}", exc_info=True)


@celery_app.task(name="create_project_repo_task")
def create_project_repo_task(project_id: str):
    logger.info(f"Creating repo for project {project_id}")
    try:
        import asyncio
        from app.database import sync_session_maker
        from app.models.project import Project
        from app.services.repo_service import RepoService

        db = sync_session_maker()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                logger.error(f"Project {project_id} not found")
                return

            repo_svc = RepoService(db)
            repo = asyncio.run(repo_svc.create_project_repo(project_id, project.name))
            logger.info(f"Created repo {repo.id} for project {project_id}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Repo creation failed: {e}", exc_info=True)


@celery_app.task(name="auto_assign_task")
def auto_assign_task(task_id: str):
    logger.info(f"Auto-assigning task {task_id} via Skill layer")
    try:
        from app.database import sync_session_maker
        from app.services.skill_schedule_service import SkillScheduleService

        db = sync_session_maker()
        try:
            svc = SkillScheduleService(db)
            result = svc.auto_assign_via_skill(task_id)
            if result:
                logger.info(f"Task {task_id} assigned to agent {result.assignee_agent_id}")
            else:
                logger.warning(f"Failed to assign task {task_id}, no available agents")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Auto-assign failed: {e}", exc_info=True)


@celery_app.task(name="run_acceptance_task")
def run_acceptance_task(task_id: str, reviewer_agent_id: str):
    logger.info(f"Running acceptance for task {task_id}")
    try:
        from app.database import sync_session_maker
        from app.services.acceptance_service_v2 import AcceptanceServiceV2

        db = sync_session_maker()
        try:
            svc = AcceptanceServiceV2(db)
            result = svc.run_acceptance(task_id, reviewer_agent_id)
            logger.info(f"Acceptance result for task {task_id}: {result['result']}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Acceptance task failed: {e}", exc_info=True)


@celery_app.task(name="send_notification_task")
def send_notification_task(user_id: str, type: str, title: str, content: str,
                           project_id: str = None, channels: list = None):
    logger.info(f"Sending notification to user {user_id}: {title}")
    try:
        from app.database import sync_session_maker
        from app.services.notification_service import NotificationService

        db = sync_session_maker()
        try:
            svc = NotificationService(db)
            svc.send_multi_channel(
                user_id=user_id, type=type, title=title, content=content,
                project_id=project_id, channels=channels,
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Notification task failed: {e}", exc_info=True)
