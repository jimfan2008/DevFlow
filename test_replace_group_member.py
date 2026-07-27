import pytest
import time
from datetime import datetime, timedelta
from collections import defaultdict


class DiscussionMessage:
    def __init__(self, sender_id: str, content: str, timestamp: datetime):
        self.sender_id = sender_id
        self.content = content
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "sender_id": self.sender_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


class OperationLog:
    def __init__(self):
        self.entries = []

    def add(self, action: str, details: dict):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        }
        self.entries.append(entry)

    def get_logs(self) -> list:
        return self.entries


class Group:
    def __init__(self, group_id: str, admin_id: str):
        self.group_id = group_id
        self.admin_id = admin_id
        self.members: dict[str, dict] = {}
        self.history: list[DiscussionMessage] = []
        self.operation_log = OperationLog()

    def add_member(self, member_id: str, name: str, role: str = "member"):
        self.members[member_id] = {
            "id": member_id,
            "name": name,
            "role": role,
            "joined_at": datetime.now().isoformat(),
            "status": "active",
        }

    def replace_member(self, requestor_id: str, old_member_id: str, new_member_id: str, new_member_name: str) -> dict:
        if requestor_id != self.admin_id:
            raise PermissionError(f"User {requestor_id} is not admin of group {self.group_id}")
        if old_member_id not in self.members:
            raise ValueError(f"Member {old_member_id} not found in group {self.group_id}")
        if new_member_id in self.members:
            raise ValueError(f"Member {new_member_id} already exists in group {self.group_id}")

        start_time = time.time()

        old_history = [msg for msg in self.history if msg.sender_id == old_member_id]

        old_member_info = self.members.pop(old_member_id)
        self.members[new_member_id] = {
            "id": new_member_id,
            "name": new_member_name,
            "role": old_member_info.get("role", "member"),
            "joined_at": datetime.now().isoformat(),
            "status": "active",
        }

        self.operation_log.add("replace_member", {
            "old_member_id": old_member_id,
            "old_member_name": old_member_info["name"],
            "new_member_id": new_member_id,
            "new_member_name": new_member_name,
            "replaced_by": requestor_id,
        })

        elapsed = time.time() - start_time

        return {
            "success": True,
            "old_member_id": old_member_id,
            "new_member_id": new_member_id,
            "handover_time_seconds": elapsed,
            "history_count": len(old_history),
        }

    def add_message(self, sender_id: str, content: str):
        msg = DiscussionMessage(sender_id, content, datetime.now())
        self.history.append(msg)

    def get_history(self, requester_id: str, target_id: str = None) -> list[dict]:
        if requester_id not in self.members:
            raise PermissionError(f"User {requester_id} is not a member of group {self.group_id}")

        if target_id:
            messages = [msg for msg in self.history if msg.sender_id == target_id]
        else:
            messages = self.history

        return [msg.to_dict() for msg in messages]

    def is_readonly_for_history(self, requester_id: str, target_id: str) -> bool:
        if requester_id not in self.members:
            raise PermissionError(f"User {requester_id} is not a member of group {self.group_id}")
        return requester_id != target_id


def create_test_group() -> Group:
    group = Group(group_id="group-001", admin_id="admin-001")
    group.add_member("admin-001", "AdminBot", "admin")
    group.add_member("agent-old", "OldAgent", "member")
    group.add_member("agent-b", "AgentB", "member")
    return group


class TestReplaceGroupMember:

    def test_admin_can_replace_member_success(self):
        group = create_test_group()
        result = group.replace_member("admin-001", "agent-old", "agent-new", "NewAgent")

        assert result["success"] is True
        assert result["old_member_id"] == "agent-old"
        assert result["new_member_id"] == "agent-new"
        assert "agent-old" not in group.members
        assert "agent-new" in group.members
        assert group.members["agent-new"]["name"] == "NewAgent"
        assert group.members["agent-new"]["role"] == "member"

    def test_handover_time_within_5_seconds(self):
        group = create_test_group()
        result = group.replace_member("admin-001", "agent-old", "agent-new", "NewAgent")

        assert result["handover_time_seconds"] <= 5.0

    def test_non_admin_cannot_replace_member(self):
        group = create_test_group()

        with pytest.raises(PermissionError, match="is not admin"):
            group.replace_member("agent-b", "agent-old", "agent-new", "NewAgent")

        assert "agent-old" in group.members
        assert "agent-new" not in group.members

    def test_new_member_can_view_old_member_history_readonly(self):
        group = create_test_group()
        group.add_message("agent-old", "Discussion topic A")
        group.add_message("agent-b", "Reply from B")
        group.add_message("agent-old", "Follow-up on topic A")

        group.replace_member("admin-001", "agent-old", "agent-new", "NewAgent")

        history = group.get_history("agent-new", "agent-old")
        assert len(history) == 2
        assert history[0]["content"] == "Discussion topic A"
        assert history[1]["content"] == "Follow-up on topic A"
        assert history[0]["sender_id"] == "agent-old"

        assert group.is_readonly_for_history("agent-new", "agent-old") is True

    def test_non_member_cannot_view_history(self):
        group = create_test_group()
        group.add_message("agent-old", "Some content")

        with pytest.raises(PermissionError, match="is not a member"):
            group.get_history("unknown-user", "agent-old")

    def test_operation_log_records_replacement(self):
        group = create_test_group()
        group.add_message("agent-old", "Pre-replace message")

        group.replace_member("admin-001", "agent-old", "agent-new", "NewAgent")

        logs = group.operation_log.get_logs()
        assert len(logs) == 1
        log_entry = logs[0]
        assert log_entry["action"] == "replace_member"
        assert log_entry["details"]["old_member_id"] == "agent-old"
        assert log_entry["details"]["old_member_name"] == "OldAgent"
        assert log_entry["details"]["new_member_id"] == "agent-new"
        assert log_entry["details"]["new_member_name"] == "NewAgent"
        assert log_entry["details"]["replaced_by"] == "admin-001"
        assert "timestamp" in log_entry

    def test_cannot_replace_nonexistent_member(self):
        group = create_test_group()

        with pytest.raises(ValueError, match="not found"):
            group.replace_member("admin-001", "ghost-agent", "agent-new", "NewAgent")

    def test_cannot_replace_with_existing_member(self):
        group = create_test_group()

        with pytest.raises(ValueError, match="already exists"):
            group.replace_member("admin-001", "agent-old", "agent-b", "AnotherName")

    def test_full_workflow_replace_and_verify(self):
        group = create_test_group()

        group.add_message("agent-old", "Initial discussion")
        group.add_message("agent-b", "Response")
        group.add_message("agent-old", "More discussion")
        group.add_message("agent-old", "Final note")

        result = group.replace_member("admin-001", "agent-old", "agent-new", "NewAgent")

        assert result["success"] is True
        assert result["handover_time_seconds"] <= 5.0
        assert result["history_count"] == 3

        new_history = group.get_history("agent-new", "agent-old")
        assert len(new_history) == 3
        for msg in new_history:
            assert msg["sender_id"] == "agent-old"

        logs = group.operation_log.get_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "replace_member"

        assert group.is_readonly_for_history("agent-new", "agent-old") is True
