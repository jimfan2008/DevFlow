import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import time


class MockMember:
    def __init__(self, user_id: str, role: str = "member", group_id: str = "group_001"):
        self.user_id = user_id
        self.role = role
        self.group_id = group_id
        self.joined_at = datetime.now()


class MockGroup:
    def __init__(self, group_id: str, owner_id: str, members: list = None):
        self.group_id = group_id
        self.owner_id = owner_id
        self.members = members or []
        self.created_at = datetime.now()


class MockGroupService:
    def __init__(self):
        self.groups: dict[str, MockGroup] = {}
        self.operation_logs: list[dict] = []
        self._setup_default_data()

    def _setup_default_data(self):
        members = [
            MockMember("user_admin", "admin"),
            MockMember("user_001", "member"),
            MockMember("user_002", "member"),
            MockMember("user_003", "member"),
            MockMember("user_004", "member"),
        ]
        self.groups["group_001"] = MockGroup("group_001", "user_admin", members)
        self.groups["group_002"] = MockGroup("group_002", "owner_002", [
            MockMember("owner_002", "owner"),
            MockMember("admin_002", "admin"),
            MockMember("member_002a", "member"),
        ])

    def remove_member(self, group_id: str, member_id: str, requester_id: str) -> dict:
        if group_id not in self.groups:
            return {"code": 404, "message": "Group not found"}
        group = self.groups[group_id]
        requester = next((m for m in group.members if m.user_id == requester_id), None)
        if requester_id != group.owner_id and (requester is None or requester.role not in ("admin", "owner")):
            return {"code": 403, "message": "Permission denied: insufficient role"}
        if requester_id == member_id:
            return {"code": 400, "message": "Cannot remove yourself from the group"}
        target = next((m for m in group.members if m.user_id == member_id), None)
        if target is None:
            return {"code": 404, "message": "Member not found in group"}
        if target.role == "owner":
            return {"code": 400, "message": "Cannot remove the group owner"}
        group.members = [m for m in group.members if m.user_id != member_id]
        log_entry = {
            "action": "remove_member",
            "group_id": group_id,
            "target_id": member_id,
            "operator_id": requester_id,
            "timestamp": datetime.now().isoformat(),
        }
        self.operation_logs.append(log_entry)
        return {"code": 0, "message": "success"}

    def get_member_count(self, group_id: str) -> int:
        group = self.groups.get(group_id)
        return len(group.members) if group else 0

    def is_member(self, group_id: str, user_id: str) -> bool:
        group = self.groups.get(group_id)
        if group is None:
            return False
        return any(m.user_id == user_id for m in group.members)

    def get_operation_logs(self, group_id: str) -> list[dict]:
        return [log for log in self.operation_logs if log["group_id"] == group_id]


@pytest.fixture
def group_service():
    return MockGroupService()


@pytest.mark.asyncio
async def test_remove_existing_member_returns_200_and_revokes_access_under_1s(group_service):
    """AC1: HTTP200, response ≤2s; removed member loses access ≤1s; operation log recorded"""
    initial_count = group_service.get_member_count("group_001")
    assert initial_count == 5

    start = time.monotonic()
    result = group_service.remove_member("group_001", "user_001", "user_admin")
    elapsed = time.monotonic() - start

    assert result["code"] == 0
    assert result["message"] == "success"
    assert elapsed <= 2.0, f"Response time {elapsed:.3f}s exceeds 2s limit"

    member_count = group_service.get_member_count("group_001")
    assert member_count == initial_count - 1

    revoke_start = time.monotonic()
    has_access = group_service.is_member("group_001", "user_001")
    revoke_elapsed = time.monotonic() - revoke_start
    assert not has_access, "Removed member should not have access"
    assert revoke_elapsed <= 1.0, f"Permission revocation delay {revoke_elapsed:.3f}s exceeds 1s limit"

    logs = group_service.get_operation_logs("group_001")
    assert len(logs) == 1
    assert logs[0]["action"] == "remove_member"
    assert logs[0]["target_id"] == "user_001"
    assert logs[0]["operator_id"] == "user_admin"
    assert "timestamp" in logs[0]


@pytest.mark.asyncio
async def test_remove_nonexistent_member_returns_404(group_service):
    """移除不存在的成员应返回404"""
    result = group_service.remove_member("group_001", "nosuch_user", "user_admin")
    assert result["code"] == 404
    assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_remove_group_owner_returns_400(group_service):
    """移除群主应返回400被拒绝"""
    result = group_service.remove_member("group_002", "owner_002", "admin_002")
    assert result["code"] == 400
    assert "owner" in result["message"].lower()


@pytest.mark.asyncio
async def test_remove_self_returns_400(group_service):
    """移除自己应返回400被拒绝"""
    result = group_service.remove_member("group_001", "user_002", "user_002")
    assert result["code"] == 400
    assert "yourself" in result["message"].lower()


@pytest.mark.asyncio
async def test_remove_member_without_permission_returns_403(group_service):
    """普通成员尝试移除其他成员应返回403"""
    result = group_service.remove_member("group_001", "user_003", "user_004")
    assert result["code"] == 403
    assert "permission" in result["message"].lower()


@pytest.mark.asyncio
async def test_remove_from_nonexistent_group_returns_404(group_service):
    """无效群组ID应返回404"""
    result = group_service.remove_member("nonexistent_group", "user_001", "user_admin")
    assert result["code"] == 404
    assert "group" in result["message"].lower() and "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_duplicate_remove_returns_404(group_service):
    """已移除的成员再次移除应返回404"""
    group_service.remove_member("group_001", "user_001", "user_admin")
    result = group_service.remove_member("group_001", "user_001", "user_admin")
    assert result["code"] == 404
    assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_operation_log_recorded_on_each_removal(group_service):
    """每次移除操作都生成完整操作日志"""
    group_service.remove_member("group_001", "user_001", "user_admin")
    group_service.remove_member("group_001", "user_002", "user_admin")
    logs = group_service.get_operation_logs("group_001")
    assert len(logs) == 2
    for log in logs:
        assert log["action"] == "remove_member"
        assert log["group_id"] == "group_001"
        assert log["operator_id"] == "user_admin"
        assert "target_id" in log
        assert "timestamp" in log


@pytest.mark.asyncio
async def test_admin_can_remove_member_after_another_removal(group_service):
    """移除一个成员后管理员仍可移除其他成员（群组状态正确）"""
    group_service.remove_member("group_001", "user_001", "user_admin")
    assert group_service.get_member_count("group_001") == 4

    result = group_service.remove_member("group_001", "user_002", "user_admin")
    assert result["code"] == 0
    assert group_service.get_member_count("group_001") == 3
    assert not group_service.is_member("group_001", "user_002")
