from __future__ import annotations

import logging
import re
from typing import Optional, List, Dict, Any

import httpx
from app.config import settings

logger = logging.getLogger("devflow.gitea")

CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\(.+\))?: .{1,}"
)


class GiteaClient:
    def __init__(self):
        self.base_url = settings.GITEA_URL.rstrip("/")
        self.token = settings.GITEA_API_TOKEN
        self.admin_user = settings.GITEA_ADMIN_USER
        self.admin_password = settings.GITEA_ADMIN_PASSWORD

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, json_data: dict = None,
                       params: dict = None) -> Any:
        url = f"{self.base_url}/api/v1{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method, url,
                headers=self._headers(),
                json=json_data,
                params=params,
            )
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()

    async def create_org_repo(self, org: str, name: str, description: str = "",
                              private: bool = True, auto_init: bool = True) -> Dict:
        return await self._request(
            "POST", f"/orgs/{org}/repos",
            json_data={
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
                "default_branch": "main",
            },
        )

    async def create_user_repo(self, username: str, name: str, description: str = "",
                               private: bool = True, auto_init: bool = True) -> Dict:
        return await self._request(
            "POST", f"/admin/users/{username}/repos",
            json_data={
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
                "default_branch": "main",
            },
        )

    async def get_repo(self, owner: str, repo: str) -> Dict:
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def delete_repo(self, owner: str, repo: str) -> None:
        await self._request("DELETE", f"/repos/{owner}/{repo}")

    async def list_branches(self, owner: str, repo: str) -> List[Dict]:
        return await self._request("GET", f"/repos/{owner}/{repo}/branches")

    async def create_branch(self, owner: str, repo: str, branch_name: str,
                            ref: str = "main") -> Dict:
        return await self._request(
            "POST", f"/repos/{owner}/{repo}/branches",
            json_data={"new_branch_name": branch_name, "old_ref_name": ref},
        )

    async def protect_branch(self, owner: str, repo: str, branch: str,
                             required_approvals: int = 1) -> Dict:
        return await self._request(
            "PUT", f"/repos/{owner}/{repo}/branch_protections/{branch}",
            json_data={
                "enable_push": False,
                "required_approvals": required_approvals,
                "enable_status_check": True,
            },
        )

    async def init_git_flow(self, owner: str, repo: str) -> Dict:
        branches = await self.list_branches(owner, repo)
        branch_names = [b["name"] for b in branches]

        if "develop" not in branch_names:
            await self.create_branch(owner, repo, "develop", "main")

        await self.protect_branch(owner, repo, "main", required_approvals=2)
        await self.protect_branch(owner, repo, "develop", required_approvals=1)

        return {"main": "protected", "develop": "created_and_protected"}

    async def create_pr(self, owner: str, repo: str, title: str,
                        head: str, base: str, body: str = "") -> Dict:
        return await self._request(
            "POST", f"/repos/{owner}/{repo}/pulls",
            json_data={"title": title, "head": head, "base": base, "body": body},
        )

    async def list_prs(self, owner: str, repo: str, state: str = "open") -> List[Dict]:
        return await self._request(
            "GET", f"/repos/{owner}/{repo}/pulls",
            params={"state": state},
        )

    async def merge_pr(self, owner: str, repo: str, pr_number: int) -> Dict:
        return await self._request(
            "POST", f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
            json_data={"Do": "merge"},
        )

    async def list_commits(self, owner: str, repo: str, branch: str = None,
                           limit: int = 50) -> List[Dict]:
        params = {"limit": limit}
        if branch:
            params["sha"] = branch
        return await self._request("GET", f"/repos/{owner}/{repo}/commits", params=params)

    async def validate_conventional_commit(self, owner: str, repo: str,
                                           branch: str = None) -> Dict:
        commits = await self.list_commits(owner, repo, branch=branch, limit=50)
        invalid = []
        for c in commits:
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            if not CONVENTIONAL_COMMIT_PATTERN.match(msg):
                invalid.append({"sha": c.get("sha", ""), "message": msg})

        return {
            "valid": len(invalid) == 0,
            "invalid_commits": invalid,
            "error_code": "REPO_003" if invalid else None,
        }

    async def add_webhook(self, owner: str, repo: str, url: str,
                          events: List[str] = None, secret: str = "") -> Dict:
        return await self._request(
            "POST", f"/repos/{owner}/{repo}/hooks",
            json_data={
                "type": "gitea",
                "config": {"url": url, "content_type": "json"},
                "events": events or ["push", "pull_request"],
                "active": True,
            },
        )

    async def get_repo_url(self, owner: str, repo: str) -> str:
        return f"{self.base_url}/{owner}/{repo}.git"

    async def create_file(self, owner: str, repo: str, filepath: str,
                          content: str, message: str,
                          branch: str = "main") -> Dict:
        import base64
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        return await self._request(
            "POST", f"/repos/{owner}/{repo}/contents/{filepath}",
            json_data={
                "content": encoded,
                "message": message,
                "branch": branch,
            },
        )

    async def create_release(self, owner: str, repo: str, tag_name: str,
                             title: str = "", body: str = "",
                             target: str = "main") -> Dict:
        """创建 Gitea 发布标签（Release Tag）"""
        return await self._request(
            "POST", f"/repos/{owner}/{repo}/releases",
            json_data={
                "tag_name": tag_name,
                "title": title,
                "body": body,
                "target": target,
            },
        )


gitea_client = GiteaClient()
