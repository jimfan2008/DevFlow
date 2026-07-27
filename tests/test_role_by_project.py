import pytest


class ProjectRoleManager:
    def __init__(self):
        self._store = {}

    def set_role(self, user_key, project, role):
        if not isinstance(user_key, str) or not user_key:
            raise ValueError("user_key must be a non-empty string")
        if not isinstance(project, str) or not project:
            raise ValueError("project must be a non-empty string")
        self._store.setdefault(user_key, {})[project] = role

    def get_role(self, user_key, project):
        if not isinstance(user_key, str) or not user_key:
            raise ValueError("user_key must be a non-empty string")
        if not isinstance(project, str) or not project:
            raise ValueError("project must be a non-empty string")
        return self._store.get(user_key, {}).get(project)


@pytest.fixture
def manager():
    return ProjectRoleManager()


class TestProjectRoleAssignment:
    def test_same_user_different_roles_in_different_projects(self, manager):
        manager.set_role("user1", "P1", "manager")
        manager.set_role("user1", "P2", "developer")
        assert manager.get_role("user1", "P1") == "manager"
        assert manager.get_role("user1", "P2") == "developer"

    def test_roles_are_independent_across_projects(self, manager):
        manager.set_role("user1", "P1", "manager")
        manager.set_role("user1", "P2", "developer")
        manager.set_role("user1", "P1", "admin")
        assert manager.get_role("user1", "P1") == "admin"
        assert manager.get_role("user1", "P2") == "developer"

    def test_different_users_isolated_in_same_project(self, manager):
        manager.set_role("user1", "P1", "manager")
        manager.set_role("user2", "P1", "developer")
        assert manager.get_role("user1", "P1") == "manager"
        assert manager.get_role("user2", "P1") == "developer"

    def test_get_role_returns_none_for_unassigned_role(self, manager):
        assert manager.get_role("user1", "P1") is None

    def test_empty_string_key_raises_error(self, manager):
        with pytest.raises(ValueError):
            manager.set_role("", "P1", "manager")
        with pytest.raises(ValueError):
            manager.set_role("user1", "", "manager")
        with pytest.raises(ValueError):
            manager.get_role("", "P1")
        with pytest.raises(ValueError):
            manager.get_role("user1", "")

    def test_none_user_key_raises_error(self, manager):
        with pytest.raises(ValueError):
            manager.set_role(None, "P1", "manager")
        with pytest.raises(ValueError):
            manager.get_role(None, "P1")

    def test_none_project_key_raises_error(self, manager):
        with pytest.raises(ValueError):
            manager.set_role("user1", None, "manager")
        with pytest.raises(ValueError):
            manager.get_role("user1", None)

    def test_none_role_is_allowed(self, manager):
        manager.set_role("user1", "P1", None)
        assert manager.get_role("user1", "P1") is None

    def test_very_long_role_name(self, manager):
        long_role = "a" * 1000
        manager.set_role("user1", "P1", long_role)
        assert manager.get_role("user1", "P1") == long_role

    def test_overwrite_with_same_role(self, manager):
        manager.set_role("user1", "P1", "manager")
        manager.set_role("user1", "P1", "manager")
        assert manager.get_role("user1", "P1") == "manager"

    def test_empty_dict_initial_state(self, manager):
        assert manager.get_role("user1", "P1") is None

    def test_invalid_role_value_is_stored_as_is(self, manager):
        manager.set_role("user1", "P1", "superadmin")
        assert manager.get_role("user1", "P1") == "superadmin"

    def test_role_value_case_sensitivity(self, manager):
        manager.set_role("user1", "P1", "Manager")
        manager.set_role("user1", "P2", "manager")
        role_p1 = manager.get_role("user1", "P1")
        role_p2 = manager.get_role("user1", "P2")
        assert role_p1 == "Manager"
        assert role_p2 == "manager"
        assert role_p1 != role_p2
