import pytest
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserProjectRole:
    user_id: str
    project_id: str
    role: str


class RoleManager:
    def __init__(self):
        self._store: Dict[str, UserProjectRole] = {}

    def assign_role(self, user_id: str, project_id: str, role: str) -> None:
        key = f"{user_id}:{project_id}"
        self._store[key] = UserProjectRole(
            user_id=user_id,
            project_id=project_id,
            role=role,
        )

    def get_role(self, user_id: str, project_id: str) -> Optional[str]:
        key = f"{user_id}:{project_id}"
        entry = self._store.get(key)
        return entry.role if entry else None


@pytest.fixture
def role_manager() -> RoleManager:
    return RoleManager()


class TestRoleByProject:
    def test_same_user_different_roles_in_different_projects(self, role_manager: RoleManager):
        user_id = "user-001"
        project_p1 = "project-p1"
        project_p2 = "project-p2"

        role_manager.assign_role(user_id, project_p1, "manager")
        role_manager.assign_role(user_id, project_p2, "developer")

        assert role_manager.get_role(user_id, project_p1) == "manager"
        assert role_manager.get_role(user_id, project_p2) == "developer"

    def test_role_independence_across_projects(self, role_manager: RoleManager):
        user_id = "user-002"

        role_manager.assign_role(user_id, "project-alpha", "viewer")
        role_manager.assign_role(user_id, "project-beta", "admin")

        alpha_role = role_manager.get_role(user_id, "project-alpha")
        beta_role = role_manager.get_role(user_id, "project-beta")

        assert alpha_role == "viewer"
        assert beta_role == "admin"
        assert alpha_role != beta_role

    def test_role_lookup_for_nonexistent_project_returns_none(self, role_manager: RoleManager):
        role_manager.assign_role("user-003", "project-existing", "editor")
        result = role_manager.get_role("user-003", "project-nonexistent")
        assert result is None

    def test_different_users_same_project_have_own_roles(self, role_manager: RoleManager):
        role_manager.assign_role("user-a", "project-common", "lead")
        role_manager.assign_role("user-b", "project-common", "contributor")

        assert role_manager.get_role("user-a", "project-common") == "lead"
        assert role_manager.get_role("user-b", "project-common") == "contributor"

    def test_response_time_within_200ms(self, role_manager: RoleManager):
        user_id = "perf-user"
        role_manager.assign_role(user_id, "perf-project", "manager")

        start = time.perf_counter()
        for _ in range(1000):
            role_manager.get_role(user_id, "perf-project")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2
