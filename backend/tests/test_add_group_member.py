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

    def can_receive_messages(self, agent_id: str) -> bool:
        return agent_id in self.members

    def can_access_resources(self, agent_id: str) -> bool:
        return agent_id in self.members

    def add_member_by_admin(self, admin_id: str, new_member: Member) -> dict:
        start = time.monotonic()

        if admin_id not in self._admins:
            raise PermissionError(f"用户 {admin_id} 不是管理员，无法添加成员")

        if new_member.agent_id in self.members:
            raise ValueError(f"成员 {new_member.agent_id} 已在群中")

        self.members[new_member.agent_id] = new_member
        if new_member.role == "admin":
            self._admins.add(new_member.agent_id)

        log = OperationLog(
            id=self._log_next_id,
            operator_id=admin_id,
            action="add_member",
            target_id=new_member.agent_id,
            details=f"管理员 {admin_id} 添加了成员 {new_member.agent_id} ({new_member.name})",
            timestamp=datetime.now(timezone.utc),
        )
        self._operation_logs.append(log)
        self._log_next_id += 1

        elapsed = time.monotonic() - start

        return {
            "status": "success",
            "added_member_id": new_member.agent_id,
            "added_member_name": new_member.name,
            "elapsed_seconds": elapsed,
            "log_id": log.id,
        }

    def get_operation_logs(self, action: Optional[str] = None) -> list[OperationLog]:
        if action:
            return [log for log in self._operation_logs if log.action == action]
        return list(self._operation_logs)


@pytest.fixture
def group_with_admin():
    g = DiscussionGroup("g001", "项目Alpha讨论群")
    g.add_member(Member("admin_x", "AdminX", role="admin"))
    g.add_member(Member("member_y", "MemberY", role="member"))
    return g


class TestAddGroupMember:
    """添加群成员 -- 验收标准：
    1. HTTP 201 返回，响应时间 <= 2 秒
    2. 新成员入群后 3 秒内可查看群历史消息
    3. 操作日志记录完整
    """

    def test_add_member_returns_status_success(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        assert result["status"] == "success"

    def test_add_member_http_201_simulation(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        assert result["status"] == "success"

    def test_add_member_response_time_under_2s(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        assert result["elapsed_seconds"] <= 2.0

    def test_add_member_response_time_under_0_5s_typical(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        assert result["elapsed_seconds"] <= 0.5

    def test_add_member_result_contains_added_member_id(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        assert result["added_member_id"] == "member_z"

    def test_add_member_result_contains_added_member_name(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        assert result["added_member_name"] == "MemberZ"

    def test_add_member_result_contains_log_id(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        assert "log_id" in result
        assert result["log_id"] >= 1

    def test_new_member_added_to_members_dict(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        assert "member_z" in group_with_admin.members
        assert group_with_admin.members["member_z"].name == "MemberZ"

    def test_new_member_can_receive_messages_immediately(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        assert group_with_admin.can_receive_messages("member_z") is True

    def test_new_member_can_access_resources_immediately(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        assert group_with_admin.can_access_resources("member_z") is True

    def test_new_member_can_send_message(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        result = group_with_admin.send_message("member_z", "大家好，我是新成员")
        assert result["message_id"] >= 1

    def test_new_member_can_view_history_within_3s(self, group_with_admin):
        group_with_admin.send_message("admin_x", "欢迎新成员")
        group_with_admin.send_message("member_y", "大家好")

        new_member = Member("member_z", "MemberZ", role="member")
        join_start = time.monotonic()
        group_with_admin.add_member_by_admin("admin_x", new_member)
        join_end = time.monotonic()

        history = group_with_admin.get_history(page=1, page_size=20)
        view_end = time.monotonic()

        total_elapsed = (join_end - join_start) + (view_end - join_end)
        assert total_elapsed <= 3.0
        assert len(history) == 2

    def test_new_member_sees_all_history(self, group_with_admin):
        group_with_admin.send_message("admin_x", "第一周进展")
        group_with_admin.send_message("member_y", "已完成任务")
        group_with_admin.send_message("admin_x", "下周计划")

        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)

        history = group_with_admin.get_history(page=1, page_size=20)
        assert len(history) == 3

    def test_new_member_sees_correct_history_order(self, group_with_admin):
        group_with_admin.send_message("admin_x", "最早消息")
        group_with_admin.send_message("member_y", "中间消息")
        group_with_admin.send_message("admin_x", "最新消息")

        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)

        history = group_with_admin.get_history(page=1, page_size=20)
        assert history[0].content == "最新消息"
        assert history[2].content == "最早消息"

    def test_new_member_history_access_timing_under_3s(self, group_with_admin):
        for i in range(10):
            group_with_admin.send_message("admin_x", f"历史消息{i+1}")

        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)

        view_start = time.monotonic()
        history = group_with_admin.get_history(page=1, page_size=20)
        view_elapsed = time.monotonic() - view_start

        assert view_elapsed <= 3.0
        assert len(history) == 10

    def test_add_member_creates_operation_log(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        logs = group_with_admin.get_operation_logs(action="add_member")
        assert len(logs) == 1

    def test_operation_log_contains_operator_id(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        logs = group_with_admin.get_operation_logs(action="add_member")
        assert logs[0].operator_id == "admin_x"

    def test_operation_log_contains_target_id(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        logs = group_with_admin.get_operation_logs(action="add_member")
        assert logs[0].target_id == "member_z"

    def test_operation_log_contains_action_type(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        logs = group_with_admin.get_operation_logs(action="add_member")
        assert logs[0].action == "add_member"

    def test_operation_log_contains_meaningful_details(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        logs = group_with_admin.get_operation_logs(action="add_member")
        details = logs[0].details
        assert "admin_x" in details
        assert "member_z" in details
        assert "MemberZ" in details

    def test_operation_log_has_valid_timestamp(self, group_with_admin):
        before = datetime.now(timezone.utc)
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        after = datetime.now(timezone.utc)
        logs = group_with_admin.get_operation_logs(action="add_member")
        assert logs[0].timestamp >= before
        assert logs[0].timestamp <= after

    def test_operation_log_has_unique_id(self, group_with_admin):
        m1 = Member("member_z", "MemberZ", role="member")
        m2 = Member("member_w", "MemberW", role="member")
        group_with_admin.add_member_by_admin("admin_x", m1)
        group_with_admin.add_member_by_admin("admin_x", m2)
        logs = group_with_admin.get_operation_logs(action="add_member")
        assert len(logs) == 2
        assert logs[0].id != logs[1].id

    def test_non_admin_cannot_add_member(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        with pytest.raises(PermissionError, match="不是管理员"):
            group_with_admin.add_member_by_admin("member_y", new_member)

    def test_cannot_add_duplicate_member(self, group_with_admin):
        new_member = Member("member_y", "MemberY", role="member")
        with pytest.raises(ValueError, match="已在群中"):
            group_with_admin.add_member_by_admin("admin_x", new_member)

    def test_cannot_add_existing_member_with_same_id(self, group_with_admin):
        dup = Member("member_y", "DifferentName", role="member")
        with pytest.raises(ValueError, match="已在群中"):
            group_with_admin.add_member_by_admin("admin_x", dup)

    def test_member_count_increases_after_add(self, group_with_admin):
        initial_count = len(group_with_admin.members)
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        assert len(group_with_admin.members) == initial_count + 1

    def test_multiple_adds_all_logged(self, group_with_admin):
        m1 = Member("member_z", "MemberZ", role="member")
        m2 = Member("member_w", "MemberW", role="member")
        group_with_admin.add_member_by_admin("admin_x", m1)
        group_with_admin.add_member_by_admin("admin_x", m2)
        logs = group_with_admin.get_operation_logs(action="add_member")
        assert len(logs) == 2

    def test_add_admin_member_grants_admin_privilege(self, group_with_admin):
        new_admin = Member("admin_z", "AdminZ", role="admin")
        group_with_admin.add_member_by_admin("admin_x", new_admin)
        assert "admin_z" in group_with_admin._admins
        assert group_with_admin.members["admin_z"].role == "admin"

    def test_added_admin_can_add_others(self, group_with_admin):
        new_admin = Member("admin_z", "AdminZ", role="admin")
        group_with_admin.add_member_by_admin("admin_x", new_admin)

        another = Member("member_w", "MemberW", role="member")
        result = group_with_admin.add_member_by_admin("admin_z", another)
        assert result["status"] == "success"

    def test_other_members_unaffected_after_add(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        assert group_with_admin.can_receive_messages("admin_x") is True
        assert group_with_admin.can_receive_messages("member_y") is True

    def test_added_member_can_mention_others(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        notifs = []
        group_with_admin.on_notification(lambda n: notifs.append(n))
        result = group_with_admin.send_message("member_z", "@AdminX 你好", mentioned_agents=["admin_x"])
        assert result["message_id"] >= 1
        member_notifs = [n for n in notifs if n.target_agent == "admin_x"]
        assert len(member_notifs) == 1

    def test_fresh_group_history_accessible_by_new_member(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        history = group_with_admin.get_history(page=1, page_size=20)
        assert history == []

    def test_new_member_history_includes_own_messages_after_joining(self, group_with_admin):
        new_member = Member("member_z", "MemberZ", role="member")
        group_with_admin.add_member_by_admin("admin_x", new_member)
        group_with_admin.send_message("member_z", "我加入了")
        history = group_with_admin.get_history(page=1, page_size=20)
        assert len(history) == 1
        assert history[0].sender == "member_z"
        assert history[0].content == "我加入了"

    def test_full_add_workflow_end_to_end(self, group_with_admin):
        group_with_admin.send_message("admin_x", "会议记录 v1")
        group_with_admin.send_message("member_y", "已上传文档")

        new_member = Member("new_guy", "NewGuy", role="member")

        add_start = time.monotonic()
        result = group_with_admin.add_member_by_admin("admin_x", new_member)
        add_elapsed = time.monotonic() - add_start

        assert result["status"] == "success"
        assert result["added_member_id"] == "new_guy"
        assert result["added_member_name"] == "NewGuy"
        assert result["elapsed_seconds"] <= 2.0
        assert add_elapsed <= 2.0

        assert "new_guy" in group_with_admin.members
        assert group_with_admin.can_receive_messages("new_guy") is True
        assert group_with_admin.can_access_resources("new_guy") is True

        history = group_with_admin.get_history(page=1, page_size=20)
        assert len(history) == 2
        contents = [m.content for m in history]
        assert "会议记录 v1" in contents
        assert "已上传文档" in contents

        send_result = group_with_admin.send_message("new_guy", "我来报道了")
        assert send_result["message_id"] >= 1

        logs = group_with_admin.get_operation_logs(action="add_member")
        assert len(logs) == 1
        assert logs[0].operator_id == "admin_x"
        assert logs[0].target_id == "new_guy"
        assert logs[0].action == "add_member"

    def test_sequential_adds_all_independently_logged(self, group_with_admin):
        m1 = Member("z1", "Z1", role="member")
        m2 = Member("z2", "Z2", role="member")
        m3 = Member("z3", "Z3", role="member")

        group_with_admin.add_member_by_admin("admin_x", m1)
        group_with_admin.add_member_by_admin("admin_x", m2)
        group_with_admin.add_member_by_admin("admin_x", m3)

        logs = group_with_admin.get_operation_logs(action="add_member")
        assert len(logs) == 3
        assert logs[0].target_id == "z1"
        assert logs[1].target_id == "z2"
        assert logs[2].target_id == "z3"
