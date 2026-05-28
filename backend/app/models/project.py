from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index, CheckConstraint, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), unique=True, nullable=False)
    slug = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    tech_stack = Column(String(100), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="created")
    current_step = Column(Integer, nullable=False, default=1)
    core_goal = Column(Text, nullable=True)
    review_group_id = Column(String, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", back_populates="projects", foreign_keys=[creator_id])
    boards = relationship("Board", back_populates="project")
    members = relationship("ProjectMember", back_populates="project")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    repos = relationship("Repo", back_populates="project", cascade="all, delete-orphan")
    workflow_steps = relationship("WorkflowStep", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_projects_creator", "creator_id"),
        Index("idx_projects_status", "status"),
        Index("idx_projects_name", "name"),
        CheckConstraint("status IN ('created', 'in_progress', 'completed')", name="ck_projects_status"),
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member")
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        Index("idx_project_members_project", "project_id"),
        Index("idx_project_members_user", "user_id"),
    )
