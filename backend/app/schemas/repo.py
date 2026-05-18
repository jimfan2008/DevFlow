from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class RepoCreate(BaseModel):
    project_id: str
    gitea_repo_id: int
    name: str = Field(..., max_length=200)
    url: str = Field(..., max_length=500)
    ssh_url: Optional[str] = None
    http_url: Optional[str] = None
    default_branch: str = "main"
    is_private: bool = True


class RepoResponse(BaseModel):
    id: str
    project_id: str
    gitea_repo_id: int
    name: str
    url: str
    ssh_url: Optional[str] = None
    http_url: Optional[str] = None
    default_branch: str
    is_private: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepoListResponse(BaseModel):
    repos: list[RepoResponse]
    total: int


class RepoBranchCreate(BaseModel):
    repo_id: str
    name: str = Field(..., max_length=200)
    branch_type: str
    commit_sha: Optional[str] = None
    is_protected: bool = False
    source_branch: Optional[str] = None


class RepoBranchResponse(BaseModel):
    id: str
    repo_id: str
    name: str
    branch_type: str
    commit_sha: Optional[str] = None
    is_protected: bool
    source_branch: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PullRequestCreate(BaseModel):
    repo_id: str
    number: int
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    source_branch: str
    target_branch: str
    author: str
    reviewers: Optional[List[str]] = None


class PullRequestResponse(BaseModel):
    id: str
    repo_id: str
    number: int
    title: str
    description: Optional[str] = None
    source_branch: str
    target_branch: str
    author: str
    status: str
    reviewers: List[str] = []
    merged_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PullRequestListResponse(BaseModel):
    pull_requests: list[PullRequestResponse]
    total: int


class CommitCreate(BaseModel):
    repo_id: str
    sha: str = Field(..., max_length=40)
    message: str
    author: str
    author_email: Optional[str] = None
    committer: Optional[str] = None
    committer_email: Optional[str] = None
    branch: Optional[str] = None


class CommitResponse(BaseModel):
    id: str
    repo_id: str
    sha: str
    message: str
    author: str
    author_email: Optional[str] = None
    committer: Optional[str] = None
    committer_email: Optional[str] = None
    branch: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CommitListResponse(BaseModel):
    commits: list[CommitResponse]
    total: int


class TaskCommitCreate(BaseModel):
    task_id: str
    commit_id: str


class TaskCommitResponse(BaseModel):
    id: str
    task_id: str
    commit_id: str
    created_at: datetime

    class Config:
        from_attributes = True
