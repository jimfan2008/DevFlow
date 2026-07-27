from __future__ import annotations

import pytest
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum


class MessageType(Enum):
    TEXT = "text"
    MENTION = "mention"


@dataclass
class Member:
    agent_id: str
    name: str
    role: str = "member"


@dataclass
class Message:
    id: int
    sender: str
    content: str
    msg_type: MessageType
    mentioned_agents: list[str]
    timestamp: datetime
    edited_at: Optional[datetime] = None


@dataclass
class OperationLog:
    id: int
    operator_id: str
    action: str
    target_id: str
    details: str
    timestamp: datetime


class Notification:
    def __init__(self, target_agent: str, from_agent: str, content: str):
        self.target_agent = target_agent
        self.from_agent = from_agent
        self.content = content
        self.created_at = time.monotonic()
        self._delivered = threading.Event()

    def deliver(self):
        self._delivered.set()

    def delivered(self) -> bool:
        return self._delivered.is_set()

    def wait_for_delivery(self, timeout: float) -> bool:
        return self._delivered.wait(timeout=timeout)


class DiscussionGroup:
    def __init__(self, group_id: str, name: str):
        self.group_id = group_id
        self.name = name
        self.members: dict[str, Member] = {}
        self._messages: list[Message] = []
        self._next_id = 1
        self._lock = threading.Lock()
        self._pending_notifications: list[Notification] = []
        self._notification_callbacks: list = []
        self._operation_logs: list[OperationLog] = []
        self._log_next_id = 1
        self._admins: set[str] = set()

    def add_member(self, member: Member):
        self.members[member.agent_id] = member
        if member.role == "admin":
            self._admins.add(member.agent_id)

    def set_admin(self, agent_id: str):
        if agent_id in self.members:
            self.members[agent_id].role = "admin"
            self._admins.add(agent_id)

    def send_message(self, sender: str, content: str, mentioned_agents: Optional[list[str]] = None) -> dict:
        start = time.monotonic()
        if not content.strip():
            raise ValueError("消息内容不能为空")
        if sender not in self.members:
            raise ValueError(f"发送者 {sender} 不是本群成员")
        msg_type = MessageType.MENTION if mentioned_agents else MessageType.TEXT
        msg = Message(
            id=self._next_id,
            sender=sender,
            content=content,
            msg_type=msg_type,
            mentioned_agents=mentioned_agents or [],
            timestamp=datetime.now(timezone.utc),
        )
        with self._lock:
            self._messages.append(msg)
            self._next_id += 1
            if mentioned_agents:
                for agent_id in mentioned_agents:
                    if agent_id in self.members:
                        notif = Notification(agent_id, sender, content)
                        self._pending_notifications.append(notif)
                        notif.deliver()
                        for cb in self._notification_callbacks:
                            cb(notif)
        elapsed = time.monotonic() - start
        return {"message_id": msg.id, "elapsed_seconds": elapsed}

    def get_history(self, page: int = 1, page_size: int = 20) -> list[Message]:
        if page < 1:
            raise ValueError(f"页码必须 >= 1，当前值: {page}")
        if page_size < 1:
            raise ValueError(f"页大小必须 >= 1，当前值: {page_size}")
        with self._lock:
            reversed_msgs = list(reversed(self._messages))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            return reversed_msgs[start_idx:end_idx]

    def get_total_pages(self, page_size: int = 20) -> int:
        if page_size < 1:
            raise ValueError(f"页大小必须 >= 1，当前值: {page_size}")
        with self._lock:
            return max(1, (len(self._messages) + page_size - 1) // page_size)

    def on_notification(self, callback):
        self._notification_callbacks.append(callback)

    def get_notification_for(self, agent_id: str) -> Optional[Notification]:
        for n in self._pending_notifications:
            if n.target_agent == agent_id:
                return n
        return None

    def remove_member(self, admin_id: str, target_id: str) -> dict:
        """管理员移除群成员"""
        start = time.monotonic()

        if admin_id not in self._admins:
            raise PermissionError(f"用户 {admin_id} 不是管理员，无法移除成员")

        if admin_id == target_id:
            raise ValueError("管理员不能移除自己")

        if target_id not in self.members:
            raise ValueError(f"成员 {target_id} 不在群中")

        removed_member = self.members.pop(target_id)
        if target_id in self._admins:
            self._admins.discard(target_id)

        with self._lock:
            self._pending_notifications = [
                n for n in self._pending_notifications
                if n.target_agent != target_id
            ]

        log = OperationLog(
            id=self._log_next_id,
            operator_id=admin_id,
            action="remove_member",
            target_id=target_id,
            details=f"管理员 {admin_id} 移除了成员 {target_id} ({removed_member.name})",
            timestamp=datetime.now(timezone.utc),
        )
        self._operation_logs.append(log)
        self._log_next_id += 1

        elapsed = time.monotonic() - start

        return {
            "status": "success",
            "removed_member_id": target_id,
            "removed_member_name": removed_member.name,
            "elapsed_seconds": elapsed,
            "log_id": log.id,
        }

    def get_operation_logs(self, action: Optional[str] = None) -> list[OperationLog]:
        """获取操作日志"""
        if action:
            return [log for log in self._operation_logs if log.action == action]
        return list(self._operation_logs)

    def can_receive_messages(self, agent_id: str) -> bool:
        """检查某成员是否还能接收群消息"""
        return agent_id in self.members

    def can_access_resources(self, agent_id: str) -> bool:
        """检查某成员是否还能访问群资源"""
        return agent_id in self.members


@pytest.fixture
def group_with_admin():
    g = DiscussionGroup("g002", "项目Beta讨论群")
    g.add_member(Member("admin_x", "AdminX", role="admin"))
    g.add_member(Member("member_y", "MemberY", role="member"))
    g.add_member(Member("member_z", "MemberZ", role="member"))
    return g


class TestRemoveGroupMember:
    """移除群成员 — 验收标准：
    1. HTTP 200 返回，响应时间 ≤ 2 秒
    2. 被移除成员立即失去群消息接收和资源访问权限，权限回收延迟 ≤ 1 秒
    3. 操作日志完整
    """

    def test_remove_member_returns_success_status(self, group_with_admin):
        result = group_with_admin.remove_member("admin_x", "member_y")
        assert result["status"] == "success"

    def test_remove_member_response_time_under_2s(self, group_with_admin):
        result = group_with_admin.remove_member("admin_x", "member_y")
        assert result["elapsed_seconds"] <= 2.0

    def test_remove_member_response_time_under_0_5s_typical(self, group_with_admin):
        result = group_with_admin.remove_member("admin_x", "member_y")
        assert result["elapsed_seconds"] <= 0.5

    def test_remove_member_includes_removed_member_id(self, group_with_admin):
        result = group_with_admin.remove_member("admin_x", "member_y")
        assert result["removed_member_id"] == "member_y"

    def test_remove_member_includes_removed_member_name(self, group_with_admin):
        result = group_with_admin.remove_member("admin_x", "member_y")
        assert result["removed_member_name"] == "MemberY"

    def test_remove_member_includes_log_id(self, group_with_admin):
        result = group_with_admin.remove_member("admin_x", "member_y")
        assert "log_id" in result
        assert result["log_id"] >= 1

    def test_removed_member_cannot_send_messages(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        with pytest.raises(ValueError, match="不是本群成员"):
            group_with_admin.send_message("member_y", "我已被移除还能发消息吗")

    def test_removed_member_cannot_receive_messages_immediately(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        assert group_with_admin.can_receive_messages("member_y") is False

    def test_removed_member_cannot_access_resources_immediately(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        assert group_with_admin.can_access_resources("member_y") is False

    def test_permission_revocation_delay_under_1s(self, group_with_admin):
        remove_start = time.monotonic()
        group_with_admin.remove_member("admin_x", "member_y")
        remove_end = time.monotonic()

        check_start = time.monotonic()
        can_receive = group_with_admin.can_receive_messages("member_y")
        can_access = group_with_admin.can_access_resources("member_y")
        check_end = time.monotonic()

        total_delay = (remove_end - remove_start) + (check_end - check_start)
        assert can_receive is False
        assert can_access is False
        assert total_delay <= 1.0

    def test_removed_member_notifications_cleared(self, group_with_admin):
        group_with_admin.send_message("admin_x", "@MemberY 请查看", mentioned_agents=["member_y"])
        notif_before = group_with_admin.get_notification_for("member_y")
        assert notif_before is not None

        group_with_admin.remove_member("admin_x", "member_y")

        notif_after = group_with_admin.get_notification_for("member_y")
        assert notif_after is None

    def test_remaining_members_still_functional_after_removal(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        result = group_with_admin.send_message("member_z", "大家好")
        assert result["message_id"] == 1
        assert result["elapsed_seconds"] >= 0

        assert group_with_admin.can_receive_messages("admin_x") is True
        assert group_with_admin.can_receive_messages("member_z") is True

    def test_operation_log_recorded_on_removal(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert len(logs) == 1

    def test_operation_log_contains_operator_id(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert logs[0].operator_id == "admin_x"

    def test_operation_log_contains_target_id(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert logs[0].target_id == "member_y"

    def test_operation_log_contains_action_type(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert logs[0].action == "remove_member"

    def test_operation_log_contains_meaningful_details(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        logs = group_with_admin.get_operation_logs(action="remove_member")
        details = logs[0].details
        assert "admin_x" in details
        assert "member_y" in details
        assert "MemberY" in details

    def test_operation_log_has_valid_timestamp(self, group_with_admin):
        before = datetime.now(timezone.utc)
        group_with_admin.remove_member("admin_x", "member_y")
        after = datetime.now(timezone.utc)
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert logs[0].timestamp >= before
        assert logs[0].timestamp <= after

    def test_operation_log_has_unique_id(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        group_with_admin.remove_member("admin_x", "member_z")
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert len(logs) == 2
        assert logs[0].id != logs[1].id

    def test_non_admin_cannot_remove_member(self, group_with_admin):
        with pytest.raises(PermissionError, match="不是管理员"):
            group_with_admin.remove_member("member_y", "member_z")

    def test_admin_cannot_remove_self(self, group_with_admin):
        with pytest.raises(ValueError, match="不能移除自己"):
            group_with_admin.remove_member("admin_x", "admin_x")

    def test_cannot_remove_nonexistent_member(self, group_with_admin):
        with pytest.raises(ValueError, match="不在群中"):
            group_with_admin.remove_member("admin_x", "nonexistent_agent")

    def test_multiple_removals_log_separately(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        group_with_admin.remove_member("admin_x", "member_z")
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert len(logs) == 2
        assert logs[0].target_id == "member_y"
        assert logs[1].target_id == "member_z"

    def test_removal_of_admin_member_removes_admin_privilege(self, group_with_admin):
        group_with_admin.add_member(Member("admin_w", "AdminW", role="admin"))
        group_with_admin.add_member(Member("admin_v", "AdminV", role="admin"))
        group_with_admin.remove_member("admin_w", "admin_v")
        assert group_with_admin.can_access_resources("admin_v") is False
        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert len(logs) == 1
        assert logs[0].target_id == "admin_v"

    def test_member_count_decreases_after_removal(self, group_with_admin):
        initial_count = len(group_with_admin.members)
        group_with_admin.remove_member("admin_x", "member_y")
        assert len(group_with_admin.members) == initial_count - 1

    def test_removed_member_not_in_member_dict(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        assert "member_y" not in group_with_admin.members

    def test_can_re_add_removed_member(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        assert "member_y" not in group_with_admin.members
        group_with_admin.add_member(Member("member_y", "MemberY", role="member"))
        assert "member_y" in group_with_admin.members
        assert group_with_admin.can_receive_messages("member_y") is True

    def test_removal_does_not_affect_message_history(self, group_with_admin):
        group_with_admin.send_message("member_y", "这是我的消息")
        group_with_admin.send_message("admin_x", "这是管理员的消息")
        group_with_admin.remove_member("admin_x", "member_y")
        history = group_with_admin.get_history(page=1, page_size=20)
        assert len(history) == 2
        contents = [m.content for m in history]
        assert "这是我的消息" in contents
        assert "这是管理员的消息" in contents

    def test_full_removal_workflow_end_to_end(self, group_with_admin):
        group_with_admin.send_message("member_y", "Y 说你好")
        group_with_admin.send_message("member_z", "Z 说你好")

        result = group_with_admin.remove_member("admin_x", "member_y")

        assert result["status"] == "success"
        assert result["removed_member_id"] == "member_y"
        assert result["elapsed_seconds"] <= 2.0

        assert group_with_admin.can_receive_messages("member_y") is False
        assert group_with_admin.can_access_resources("member_y") is False

        with pytest.raises(ValueError):
            group_with_admin.send_message("member_y", "已被移除")

        ok = group_with_admin.send_message("member_z", "Z 还能发")
        assert ok["message_id"] == 3

        logs = group_with_admin.get_operation_logs(action="remove_member")
        assert len(logs) == 1
        assert logs[0].operator_id == "admin_x"
        assert logs[0].target_id == "member_y"
        assert logs[0].action == "remove_member"

    def test_sequential_removals_all_logged(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        group_with_admin.remove_member("admin_x", "member_z")
        logs = group_with_admin.get_operation_logs()
        remove_logs = [l for l in logs if l.action == "remove_member"]
        assert len(remove_logs) == 2

    def test_removed_member_mentioned_by_others_no_notification(self, group_with_admin):
        group_with_admin.remove_member("admin_x", "member_y")
        notifs = []
        group_with_admin.on_notification(lambda n: notifs.append(n))
        group_with_admin.send_message("member_z", "@MemberY 你好", mentioned_agents=["member_y"])
        assert len(notifs) == 0

    def test_http_status_simulation_200(self, group_with_admin):
        """模拟 HTTP 200 响应状态"""
        result = group_with_admin.remove_member("admin_x", "member_y")
        assert result["status"] == "success"
