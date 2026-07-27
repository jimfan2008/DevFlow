import pytest
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    id: str
    name: str


@dataclass
class Project:
    id: str
    name: str


class ProjectRoleStore:
    def __init__(self):
        self._roles: dict[tuple[str, str], str] = {}

    def assign_role(self, user_id: str, project_id: str, role: str) -> None:
        self._roles[(user_id, project_id)] = role

    def get_role(self, user_id: str, project_id: str) -> Optional[str]:
        return self._roles.get((user_id, project_id), None)


class RoleService:
    def __init__(self, store: ProjectRoleStore):
        self._store = store

    def get_user_role_in_project(self, user_id: str, project_id: str) -> Optional[str]:
        return self._store.get_role(user_id, project_id)


@pytest.fixture
def role_store():
    return ProjectRoleStore()


@pytest.fixture
def alice():
    return User(id="u001", name="Alice")


@pytest.fixture
def project_p1():
    return Project(id="p001", name="Project Alpha")


@pytest.fixture
def project_p2():
    return Project(id="p002", name="Project Beta")


@pytest.fixture
def role_service(role_store):
    return RoleService(role_store)


class TestUserProjectRoles:
    def test_same_user_different_roles_in_different_projects(
        self, alice, project_p1, project_p2, role_store, role_service
    ):
        role_store.assign_role(alice.id, project_p1.id, "manager")
        role_store.assign_role(alice.id, project_p2.id, "developer")

        role_p1 = role_service.get_user_role_in_project(alice.id, project_p1.id)
        role_p2 = role_service.get_user_role_in_project(alice.id, project_p2.id)

        assert role_p1 == "manager", f"Expected 'manager' for Alice in P1, got {role_p1}"
        assert role_p2 == "developer", f"Expected 'developer' for Alice in P2, got {role_p2}"

    def test_roles_independent_across_projects(
        self, alice, project_p1, project_p2, role_store, role_service
    ):
        role_store.assign_role(alice.id, project_p1.id, "manager")

        role_p1 = role_service.get_user_role_in_project(alice.id, project_p1.id)
        role_p2 = role_service.get_user_role_in_project(alice.id, project_p2.id)

        assert role_p1 == "manager"
        assert role_p2 is None, "Role in P2 should be independent and None"

    def test_response_time_within_200ms(
        self, alice, project_p1, project_p2, role_store, role_service
    ):
        role_store.assign_role(alice.id, project_p1.id, "manager")
        role_store.assign_role(alice.id, project_p2.id, "developer")

        start = time.perf_counter()
        for _ in range(100):
            role_service.get_user_role_in_project(alice.id, project_p1.id)
            role_service.get_user_role_in_project(alice.id, project_p2.id)
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 200) * 1000

        assert avg_ms <= 200, f"Average response time {avg_ms:.2f}ms exceeds 200ms"
