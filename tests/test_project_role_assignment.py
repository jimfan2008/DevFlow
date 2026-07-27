import time
import pytest
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserProjectRole:
    user_id: str
    project_id: str
    role: str


class RoleManager:
    def __init__(self):
        self._assignments: Dict[str, UserProjectRole] = {}

    def assign_role(self, user_id: str, project_id: str, role: str) -> None:
        key = f"{user_id}:{project_id}"
        self._assignments[key] = UserProjectRole(
            user_id=user_id,
            project_id=project_id,
            role=role,
        )

    def get_role(self, user_id: str, project_id: str) -> Optional[str]:
        key = f"{user_id}:{project_id}"
        assignment = self._assignments.get(key)
        return assignment.role if assignment else None


class TestProjectRoleAssignment:
    @pytest.fixture
    def role_manager(self):
        return RoleManager()

    def test_same_user_different_roles_in_different_projects(self, role_manager):
        user_id = "user-001"
        project_a = "P1"
        project_b = "P2"

        role_manager.assign_role(user_id, project_a, "manager")
        role_manager.assign_role(user_id, project_b, "developer")

        role_in_p1 = role_manager.get_role(user_id, project_a)
        role_in_p2 = role_manager.get_role(user_id, project_b)

        assert role_in_p1 == "manager"
        assert role_in_p2 == "developer"

    def test_role_is_independent_per_project(self, role_manager):
        user_id = "user-002"
        project_a = "P1"
        project_b = "P2"

        role_manager.assign_role(user_id, project_a, "admin")

        role_in_p1 = role_manager.get_role(user_id, project_a)
        role_in_p2 = role_manager.get_role(user_id, project_b)

        assert role_in_p1 == "admin"
        assert role_in_p2 is None

    def test_role_assignment_response_time_within_200ms(self, role_manager):
        user_id = "user-003"
        project_a = "P1"
        project_b = "P2"

        role_manager.assign_role(user_id, project_a, "manager")
        role_manager.assign_role(user_id, project_b, "developer")

        start = time.perf_counter()
        role_manager.get_role(user_id, project_a)
        role_manager.get_role(user_id, project_b)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed <= 200
