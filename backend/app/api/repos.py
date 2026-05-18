from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.repo import Repo, RepoBranch, PullRequest, Commit
from app.schemas.repo import (
    RepoCreate, RepoResponse, RepoBranchCreate, RepoBranchResponse,
    PullRequestCreate, PullRequestResponse, CommitResponse,
)

router = APIRouter()


@router.get("", response_model=dict)
def list_repos(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    if project_id:
        repos = svc.get_project_repos(project_id)
    else:
        repos = db.query(Repo).all()
    return {"code": 0, "message": "success", "data": {"repos": [r.to_dict() for r in repos], "total": len(repos)}}


@router.get("/{repo_id}", response_model=dict)
def get_repo(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    repo = svc.get_repo(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repo not found")
    return {"code": 0, "message": "success", "data": {"repo": repo.to_dict()}}


@router.get("/{repo_id}/branches", response_model=dict)
def list_branches(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    branches = svc.get_branches(repo_id)
    return {"code": 0, "message": "success", "data": {"branches": [b.to_dict() for b in branches]}}


@router.post("/{repo_id}/branches", response_model=dict)
async def create_branch(
    repo_id: str,
    data: RepoBranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    try:
        branch = await svc.create_branch(repo_id, data.name, data.branch_type, data.source_branch or "develop")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"branch": branch.to_dict()}}


@router.get("/{repo_id}/pulls", response_model=dict)
def list_prs(
    repo_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    prs = svc.get_prs(repo_id, status=status)
    return {"code": 0, "message": "success", "data": {"pull_requests": [p.to_dict() for p in prs], "total": len(prs)}}


@router.post("/{repo_id}/pulls", response_model=dict)
async def create_pr(
    repo_id: str,
    data: PullRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    try:
        pr = await svc.create_pr(repo_id, data.title, data.source_branch, data.target_branch, data.description or "", data.author)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"pull_request": pr.to_dict()}}


@router.post("/{repo_id}/pulls/{pr_id}/merge", response_model=dict)
async def merge_pr(
    repo_id: str,
    pr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    try:
        pr = await svc.merge_pr(repo_id, pr_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"pull_request": pr.to_dict()}}


@router.get("/{repo_id}/commits", response_model=dict)
def list_commits(
    repo_id: str,
    branch: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    commits = svc.get_commits(repo_id, branch=branch)
    return {"code": 0, "message": "success", "data": {"commits": [c.to_dict() for c in commits], "total": len(commits)}}


@router.post("/{repo_id}/sync-commits", response_model=dict)
async def sync_commits(
    repo_id: str,
    branch: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    try:
        synced = await svc.sync_commits(repo_id, branch=branch)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": {"synced_count": len(synced)}}


@router.get("/{repo_id}/validate-commits", response_model=dict)
async def validate_commits(
    repo_id: str,
    branch: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    try:
        result = await svc.validate_conventional_commits(repo_id, branch=branch)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": result}


@router.post("/{repo_id}/link-commit", response_model=dict)
def link_commit_to_task(
    repo_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task_id = data.get("task_id")
    commit_id = data.get("commit_id")
    if not task_id or not commit_id:
        raise HTTPException(status_code=400, detail="task_id and commit_id required")
    from app.services.repo_service import RepoService
    svc = RepoService(db)
    tc = svc.link_commit_to_task(task_id, commit_id)
    return {"code": 0, "message": "success", "data": {"task_commit": tc.to_dict()}}
