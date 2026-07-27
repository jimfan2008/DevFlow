import pytest
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class User:
    id: str
    name: str


@dataclass
class Project:
    id: str
    name: str


class RoleManager:
    def __init__(self):
        self._assignments: Dict[str, Dict[str, str]] = {}

    def assign_role(self, user: User, project: Project, role: str) -> None:
        if user.id not in self._assignments:
            self._assignments[user.id] = {}
        self._assignments[user.id][project.id] = role

    def get_role(self, user: User, project: Project) -> Optional[str]:
        return self._assignments.get(user.id, {}).get(project.id)


@pytest.fixture
def role_manager():
    return RoleManager()


@pytest.fixture
def alice():
    return User(id="u1", name="Alice")


@pytest.fixture
def project_p1():
    return Project(id="P1", name="Project Alpha")


@pytest.fixture
def project_p2():
    return Project(id="P2", name="Project Beta")


class TestProjectRoleAssignment:
    def test_same_user_different_roles_in_different_projects(self, role_manager, alice, project_p1, project_p2):
        role_manager.assign_role(alice, project_p1, "manager")
        role_manager.assign_role(alice, project_p2, "developer")
        assert role_manager.get_role(alice, project_p1) == "manager"
        assert role_manager.get_role(alice, project_p2) == "developer"

    def test_role_independence_across_projects(self, role_manager, alice, project_p1, project_p2):
        role_manager.assign_role(alice, project_p1, "manager")
        role_manager.assign_role(alice, project_p2, "developer")
        role_manager.assign_role(alice, project_p1, "admin")
        assert role_manager.get_role(alice, project_p2) == "developer"

    def test_response_time_within_200ms(self, role_manager, alice, project_p1):
        role_manager.assign_role(alice, project_p1, "manager")
        start = time.perf_counter()
        for _ in range(1000):
            role_manager.get_role(alice, project_p1)
        elapsed = (time.perf_counter() - start) / 1000
        assert elapsed <= 0.2

    def test_user_with_no_role_returns_none(self, role_manager, alice, project_p1):
        assert role_manager.get_role(alice, project_p1) is None
