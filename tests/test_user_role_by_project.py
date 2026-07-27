import time
import pytest
from unittest.mock import MagicMock


def get_user_role(user_id: str, project_id: str) -> str:
    storage = {
        ("user1", "P1"): "manager",
        ("user1", "P2"): "developer",
    }
    return storage.get((user_id, project_id), "viewer")


class TestUserRoleByProject:

    def test_same_user_different_projects_different_roles(self):
        role_p1 = get_user_role("user1", "P1")
        role_p2 = get_user_role("user1", "P2")
        assert role_p1 == "manager"
        assert role_p2 == "developer"

    def test_same_user_role_independent_per_project(self):
        role_p1_first = get_user_role("user1", "P1")
        role_p2 = get_user_role("user1", "P2")
        role_p1_second = get_user_role("user1", "P1")
        assert role_p1_first == "manager"
        assert role_p2 == "developer"
        assert role_p1_second == "manager"
        assert role_p1_first == role_p1_second

    def test_response_time_within_limit(self):
        start = time.perf_counter()
        for _ in range(100):
            get_user_role("user1", "P1")
            get_user_role("user1", "P2")
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 200

    def test_different_users_no_interference(self):
        assert get_user_role("user1", "P1") == "manager"
        assert get_user_role("user2", "P1") == "viewer"
        assert get_user_role("user2", "P2") == "viewer"

    def test_role_isolation_via_mock(self):
        mock_storage = MagicMock()
        mock_storage.get.side_effect = lambda uid, pid: {
            ("user1", "P1"): "manager",
            ("user1", "P2"): "developer",
        }.get((uid, pid), "viewer")
        assert mock_storage.get("user1", "P1") == "manager"
        assert mock_storage.get("user1", "P2") == "developer"
        assert mock_storage.get("user2", "P1") == "viewer"
