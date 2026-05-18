from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, Index
from app.models.types import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Repo(Base):
    __tablename__ = "repos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    gitea_repo_id = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    ssh_url = Column(String(500), nullable=True)
    http_url = Column(String(500), nullable=True)
    default_branch = Column(String(100), nullable=False, default="main")
    is_private = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="repos")
    branches = relationship("RepoBranch", back_populates="repo", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequest", back_populates="repo", cascade="all, delete-orphan")
    commits = relationship("Commit", back_populates="repo", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_repos_project", "project_id"),
        Index("idx_repos_gitea_id", "gitea_repo_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "gitea_repo_id": self.gitea_repo_id,
            "name": self.name,
            "url": self.url,
            "ssh_url": self.ssh_url,
            "http_url": self.http_url,
            "default_branch": self.default_branch,
            "is_private": self.is_private,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RepoBranch(Base):
    __tablename__ = "repo_branches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    branch_type = Column(String(20), nullable=False)
    commit_sha = Column(String(40), nullable=True)
    is_protected = Column(Boolean, nullable=False, default=False)
    source_branch = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repo = relationship("Repo", back_populates="branches")

    __table_args__ = (
        Index("idx_branches_repo", "repo_id"),
        Index("idx_branches_name", "repo_id", "name", unique=True),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "name": self.name,
            "branch_type": self.branch_type,
            "commit_sha": self.commit_sha,
            "is_protected": self.is_protected,
            "source_branch": self.source_branch,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id", ondelete="CASCADE"), nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source_branch = Column(String(200), nullable=False)
    target_branch = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    reviewers = Column(JSONB, server_default="[]")
    merged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repo = relationship("Repo", back_populates="pull_requests")

    __table_args__ = (
        Index("idx_prs_repo", "repo_id"),
        Index("idx_prs_status", "repo_id", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "number": self.number,
            "title": self.title,
            "description": self.description,
            "source_branch": self.source_branch,
            "target_branch": self.target_branch,
            "author": self.author,
            "status": self.status,
            "reviewers": self.reviewers or [],
            "merged_at": self.merged_at.isoformat() if self.merged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Commit(Base):
    __tablename__ = "commits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id = Column(String, ForeignKey("repos.id", ondelete="CASCADE"), nullable=False)
    sha = Column(String(40), nullable=False)
    message = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    author_email = Column(String(255), nullable=True)
    committer = Column(String(100), nullable=True)
    committer_email = Column(String(255), nullable=True)
    branch = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    repo = relationship("Repo", back_populates="commits")
    task_commits = relationship("TaskCommit", back_populates="commit", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_commits_repo", "repo_id"),
        Index("idx_commits_sha", "repo_id", "sha"),
        Index("idx_commits_branch", "repo_id", "branch"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "sha": self.sha,
            "message": self.message,
            "author": self.author,
            "author_email": self.author_email,
            "committer": self.committer,
            "committer_email": self.committer_email,
            "branch": self.branch,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TaskCommit(Base):
    __tablename__ = "task_commits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    commit_id = Column(String, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    task = relationship("Task", back_populates="task_commits")
    commit = relationship("Commit", back_populates="task_commits")

    __table_args__ = (
        Index("idx_task_commits_task", "task_id"),
        Index("idx_task_commits_commit", "commit_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "commit_id": self.commit_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
