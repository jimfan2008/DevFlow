from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.repo import Repo, RepoBranch, PullRequest, Commit, TaskCommit
from app.models.task import Task
from app.services.gitea_client import gitea_client

logger = logging.getLogger("devflow.repo")


class RepoService:
    def __init__(self, db: Session):
        self.db = db

    async def create_project_repo(self, project_id: str, project_name: str,
                                  org: str = None) -> Repo:
        existing = self.db.query(Repo).filter(Repo.project_id == project_id).first()
        if existing:
            return existing

        owner = org or settings.GITEA_ADMIN_USER
        from app.config import settings

        try:
            repo_data = await gitea_client.create_org_repo(
                org=owner, name=project_name,
                description=f"DevFlow project: {project_name}",
                private=True, auto_init=True,
            )
        except Exception:
            try:
                repo_data = await gitea_client.create_user_repo(
                    username=owner, name=project_name,
                    description=f"DevFlow project: {project_name}",
                    private=True, auto_init=True,
                )
            except Exception as e:
                logger.error(f"Failed to create repo: {e}")
                raise ValueError(f"Failed to create Gitea repo: {e}")

        repo = Repo(
            id=str(uuid.uuid4()),
            project_id=project_id,
            gitea_repo_id=repo_data.get("id", 0),
            name=project_name,
            url=await gitea_client.get_repo_url(owner, project_name),
            ssh_url=repo_data.get("ssh_url"),
            http_url=repo_data.get("html_url"),
            default_branch="main",
            is_private=True,
        )
        self.db.add(repo)
        self.db.flush()

        main_branch = RepoBranch(
            id=str(uuid.uuid4()),
            repo_id=repo.id,
            name="main",
            branch_type="main",
            is_protected=True,
        )
        self.db.add(main_branch)

        try:
            await gitea_client.init_git_flow(owner, project_name)

            develop_branch = RepoBranch(
                id=str(uuid.uuid4()),
                repo_id=repo.id,
                name="develop",
                branch_type="develop",
                source_branch="main",
                is_protected=True,
            )
            self.db.add(develop_branch)
        except Exception as e:
            logger.warning(f"Git flow init failed: {e}")

        try:
            webhook_url = f"{settings.APP_HOST}:{settings.APP_PORT}/api/webhooks/gitea"
            await gitea_client.add_webhook(owner, project_name, webhook_url)
        except Exception as e:
            logger.warning(f"Webhook setup failed: {e}")

        self.db.commit()
        self.db.refresh(repo)
        return repo

    async def create_branch(self, repo_id: str, branch_name: str,
                            branch_type: str, source_branch: str = "develop") -> RepoBranch:
        repo = self.db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")

        owner = self._get_owner()
        try:
            await gitea_client.create_branch(owner, repo.name, branch_name, source_branch)
        except Exception as e:
            logger.warning(f"Create branch in Gitea failed: {e}")

        branch = RepoBranch(
            id=str(uuid.uuid4()),
            repo_id=repo_id,
            name=branch_name,
            branch_type=branch_type,
            source_branch=source_branch,
        )
        self.db.add(branch)
        self.db.commit()
        self.db.refresh(branch)
        return branch

    async def create_pr(self, repo_id: str, title: str, head: str,
                        base: str, body: str = "", author: str = "") -> PullRequest:
        repo = self.db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")

        owner = self._get_owner()
        pr_data = await gitea_client.create_pr(owner, repo.name, title, head, base, body)

        pr = PullRequest(
            id=str(uuid.uuid4()),
            repo_id=repo_id,
            number=pr_data.get("number", 0),
            title=title,
            description=body,
            source_branch=head,
            target_branch=base,
            author=author,
            status="open",
        )
        self.db.add(pr)
        self.db.commit()
        self.db.refresh(pr)
        return pr

    async def merge_pr(self, repo_id: str, pr_id: str) -> PullRequest:
        pr = self.db.query(PullRequest).filter(PullRequest.id == pr_id).first()
        if not pr:
            raise ValueError(f"PR {pr_id} not found")

        repo = self.db.query(Repo).filter(Repo.id == repo_id).first()
        owner = self._get_owner()

        await gitea_client.merge_pr(owner, repo.name, pr.number)

        pr.status = "merged"
        pr.merged_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(pr)
        return pr

    async def sync_commits(self, repo_id: str, branch: str = None) -> List[Commit]:
        repo = self.db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")

        owner = self._get_owner()
        commits_data = await gitea_client.list_commits(owner, repo.name, branch)

        synced = []
        for c in commits_data:
            sha = c.get("sha", "")
            existing = self.db.query(Commit).filter(
                Commit.repo_id == repo_id, Commit.sha == sha
            ).first()
            if existing:
                continue

            commit_obj = Commit(
                id=str(uuid.uuid4()),
                repo_id=repo_id,
                sha=sha,
                message=c.get("commit", {}).get("message", ""),
                author=c.get("commit", {}).get("author", {}).get("name", ""),
                author_email=c.get("commit", {}).get("author", {}).get("email"),
                branch=branch,
            )
            self.db.add(commit_obj)
            synced.append(commit_obj)

        if synced:
            self.db.commit()
        return synced

    async def validate_conventional_commits(self, repo_id: str, branch: str = None) -> dict:
        repo = self.db.query(Repo).filter(Repo.id == repo_id).first()
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")
        owner = self._get_owner()
        return await gitea_client.validate_conventional_commit(owner, repo.name, branch)

    def link_commit_to_task(self, task_id: str, commit_id: str) -> TaskCommit:
        tc = TaskCommit(
            id=str(uuid.uuid4()),
            task_id=task_id,
            commit_id=commit_id,
        )
        self.db.add(tc)
        self.db.commit()
        self.db.refresh(tc)
        return tc

    def get_repo(self, repo_id: str) -> Optional[Repo]:
        return self.db.query(Repo).filter(Repo.id == repo_id).first()

    def get_project_repos(self, project_id: str) -> list:
        return self.db.query(Repo).filter(Repo.project_id == project_id).all()

    def get_branches(self, repo_id: str) -> list:
        return self.db.query(RepoBranch).filter(RepoBranch.repo_id == repo_id).all()

    def get_prs(self, repo_id: str, status: str = None) -> list:
        query = self.db.query(PullRequest).filter(PullRequest.repo_id == repo_id)
        if status:
            query = query.filter(PullRequest.status == status)
        return query.order_by(PullRequest.created_at.desc()).all()

    def get_commits(self, repo_id: str, branch: str = None) -> list:
        query = self.db.query(Commit).filter(Commit.repo_id == repo_id)
        if branch:
            query = query.filter(Commit.branch == branch)
        return query.order_by(Commit.created_at.desc()).all()

    def _get_owner(self) -> str:
        from app.config import settings
        return settings.GITEA_ADMIN_USER
