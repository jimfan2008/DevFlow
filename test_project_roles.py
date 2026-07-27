import pytest
import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class UserProjectRole:
    user_id: str
    project_id: str
    role: str


class ProjectRoleService:
    def __init__(self):
        self._store: Dict[str, str] = {}

    def assign_role(self, user_id: str, project_id: str, role: str) -> None:
        key = f"{user_id}:{project_id}"
        self._store[key] = role

    def get_role(self, user_id: str, project_id: str) -> str:
        key = f"{user_id}:{project_id}"
        return self._store.get(key, "")


@pytest.fixture
def role_service():
    service = ProjectRoleService()
    service.assign_role("user_001", "P1", "manager")
    service.assign_role("user_001", "P2", "developer")
    return service


class TestProjectRoleAssignment:
    def test_same_user_different_roles_across_projects(self, role_service):
        role_p1 = role_service.get_role("user_001", "P1")
        role_p2 = role_service.get_role("user_001", "P2")
        assert role_p1 == "manager"
        assert role_p2 == "developer"

    def test_roles_are_independent_per_project(self, role_service):
        original_p1 = role_service.get_role("user_001", "P1")
        original_p2 = role_service.get_role("user_001", "P2")
        role_service.assign_role("user_001", "P1", "viewer")
        assert role_service.get_role("user_001", "P1") == "viewer"
        assert role_service.get_role("user_001", "P2") == original_p2

    def test_response_time_within_limit(self, role_service):
        start = time.perf_counter()
        for _ in range(100):
            role_service.get_role("user_001", "P1")
            role_service.get_role("user_001", "P2")
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 200) * 1000
        assert avg_ms <= 200, f"Average response time {avg_ms:.2f}ms exceeds 200ms"

    def test_different_users_same_project(self, role_service):
        role_service.assign_role("user_002", "P1", "admin")
        assert role_service.get_role("user_001", "P1") == "manager"
        assert role_service.get_role("user_002", "P1") == "admin"

    def test_unknown_user_returns_empty(self, role_service):
        role = role_service.get_role("nonexistent", "P1")
        assert role == ""
