from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from app.models.project import Project, ProjectMember
from app.models.requirement import Requirement
from app.models.group import Group
from app.models.enums import ProjectStatus

logger = logging.getLogger("devflow.project")


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, name: str, creator_id: str, description: str = "",
                       tech_stack: str = None, deadline=None) -> Project:
        existing = self.db.query(Project).filter(Project.name == name).first()
        if existing:
            raise ValueError(f"Project name '{name}' already exists")

        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            creator_id=creator_id,
            tech_stack=tech_stack,
            deadline=deadline,
            status=ProjectStatus.created.value,
        )
        self.db.add(project)
        self.db.flush()

        member = ProjectMember(
            id=str(uuid.uuid4()),
            project_id=project.id,
            user_id=creator_id,
            role="owner",
        )
        self.db.add(member)

        review_group = Group(
            id=str(uuid.uuid4()),
            name=f"{name}-需求评审",
            description=f"项目 {name} 的需求评审群组",
            members=[creator_id],
            mode="discussion",
            project_id=project.id,
        )
        self.db.add(review_group)

        project.review_group_id = review_group.id
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_projects(self, creator_id: str = None, status: str = None) -> List[Project]:
        query = self.db.query(Project)
        if creator_id:
            query = query.filter(Project.creator_id == creator_id)
        if status:
            query = query.filter(Project.status == status)
        return query.order_by(Project.created_at.desc()).all()

    def update_project(self, project_id: str, **kwargs) -> Optional[Project]:
        project = self.get_project(project_id)
        if not project:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)
        project.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(project)
        return project

    def transition_status(self, project_id: str, target_status: str) -> Optional[Project]:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        valid_transitions = {
            ProjectStatus.created.value: [ProjectStatus.in_progress.value],
            ProjectStatus.in_progress.value: [ProjectStatus.completed.value],
        }
        allowed = valid_transitions.get(project.status, [])
        if target_status not in allowed:
            raise ValueError(f"Cannot transition from {project.status} to {target_status}")

        project.status = target_status
        project.updated_at = datetime.now(timezone.utc)
        if target_status == ProjectStatus.completed.value:
            project.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(project)
        return project

    def add_member(self, project_id: str, user_id: str, role: str = "member") -> ProjectMember:
        existing = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        ).first()
        if existing:
            return existing
        member = ProjectMember(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, project_id: str, user_id: str) -> bool:
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        ).first()
        if not member:
            return False
        self.db.delete(member)
        self.db.commit()
        return True

    def submit_requirement(self, project_id: str, content: str, user_id: str = None) -> Requirement:
        existing = self.db.query(Requirement).filter(
            Requirement.project_id == project_id,
            Requirement.is_locked == False,
        ).first()

        if existing:
            existing.content = content
            existing.version += 1
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        req = Requirement(
            id=str(uuid.uuid4()),
            project_id=project_id,
            content=content,
            version=1,
            is_locked=False,
        )
        self.db.add(req)
        self.db.commit()
        self.db.refresh(req)
        return req

    def confirm_and_lock_requirement(self, project_id: str, user_id: str = None) -> Requirement:
        req = self.db.query(Requirement).filter(
            Requirement.project_id == project_id,
            Requirement.is_locked == False,
        ).order_by(Requirement.version.desc()).first()

        if not req:
            raise ValueError("No unlocked requirement found")

        req.is_locked = True
        req.confirmed_at = datetime.now(timezone.utc)
        req.confirmed_by = user_id
        self.db.commit()
        self.db.refresh(req)

        logger.info(f"Requirement locked for project {project_id}, triggering async decomposition and repo creation")
        try:
            from app.services.celery_tasks import decompose_tasks_task, create_project_repo_task
            decompose_tasks_task.delay(project_id)
            create_project_repo_task.delay(project_id)
        except Exception as e:
            logger.warning(f"Celery not available, skipping async tasks: {e}")

        return req

    def update_requirement_if_unlocked(self, project_id: str, content: str, user_id: str = None) -> Requirement:
        req = self.db.query(Requirement).filter(
            Requirement.project_id == project_id,
        ).order_by(Requirement.version.desc()).first()

        if not req:
            raise ValueError("No requirement found")

        if req.is_locked and user_id != req.confirmed_by:
            raise ValueError("REQ_001: Requirement is locked, modification denied")

        req.content = content
        req.version += 1
        req.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(req)
        return req

    def generate_prd(self, project_id: str) -> dict:
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        req = self.db.query(Requirement).filter(
            Requirement.project_id == project_id,
        ).order_by(Requirement.version.desc()).first()

        if not req:
            raise ValueError("No requirement found for project")

        prd = {
            "title": f"PRD - {project.name}",
            "version": req.version,
            "project_id": project_id,
            "overview": project.description or "",
            "requirements": req.content,
            "tech_stack": project.tech_stack or "",
            "deadline": project.deadline.isoformat() if project.deadline else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return prd
