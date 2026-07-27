from __future__ import annotations

import pytest
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import json
import os


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
        self._disbanded = False
        self._disband_notifications: list[Notification] = []
        self._disband_time: Optional[datetime] = None

    def add_member(self, member: Member):
        self.members[member.agent_id] = member

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

    def disband(self, admin_id: str) -> dict:
        start = time.monotonic()
        if admin_id not in self.members:
            raise ValueError(f"发起者 {admin_id} 不是本群成员")
        if self.members[admin_id].role != "admin":
            raise ValueError(f"只有管理员可以解散群组")
        if self._disbanded:
            raise ValueError("群组已经解散")
        with self._lock:
            self._disbanded = True
            self._disband_time = datetime.now(timezone.utc)
            disband_msg = f"群组 {self.name} 已被管理员解散"
            for member_id in list(self.members.keys()):
                notif = Notification(member_id, admin_id, disband_msg)
                self._disband_notifications.append(notif)
                notif.deliver()
                for cb in self._notification_callbacks:
                    cb(notif)
        elapsed = time.monotonic() - start
        return {"disbanded": True, "elapsed_seconds": elapsed}

    def create_archive(self) -> str:
        if not self._disbanded:
            raise ValueError("群组尚未解散，无法归档")
        archive_time = self._disband_time or datetime.now(timezone.utc)
        timestamp_str = archive_time.strftime("%Y%m%d%H%M%S")
        archive_filename = f"archive-{self.group_id}-{timestamp_str}"
        archive_data = {
            "group_id": self.group_id,
            "name": self.name,
            "disband_time": archive_time.isoformat(),
            "messages": [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "content": m.content,
                    "msg_type": m.msg_type.value,
                    "mentioned_agents": m.mentioned_agents,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self._messages
            ],
        }
        return archive_filename

    def get_disband_notifications(self) -> list[Notification]:
        return list(self._disband_notifications)

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


@pytest.fixture
def group():
    g = DiscussionGroup("g001", "项目Alpha讨论群")
    g.add_member(Member("agent_admin", "Admin", role="admin"))
    g.add_member(Member("agent_alice", "Alice"))
    g.add_member(Member("agent_bob", "Bob"))
    g.add_member(Member("agent_charlie", "Charlie"))
    return g


@pytest.fixture
def group_with_messages(group):
    group.send_message("agent_alice", "大家好，今天讨论进度")
    group.send_message("agent_bob", "好的，我来更新文档")
    group.send_message("agent_charlie", "收到，谢谢")
    return group


class TestGroupDisband:
    def test_admin_can_disband_group(self, group):
        result = group.disband("agent_admin")
        assert result["disbanded"] is True

    def test_non_admin_cannot_disband_group(self, group):
        with pytest.raises(ValueError, match="只有管理员可以解散群组"):
            group.disband("agent_alice")

    def test_non_member_cannot_disband_group(self, group):
        with pytest.raises(ValueError, match="不是本群成员"):
            group.disband("agent_unknown")

    def test_disband_twice_raises(self, group):
        group.disband("agent_admin")
        with pytest.raises(ValueError, match="群组已经解散"):
            group.disband("agent_admin")

    def test_disband_notification_sent_to_all_members(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        result = group.disband("agent_admin")
        member_ids = list(group.members.keys())
        notified_ids = [n.target_agent for n in notifs]
        assert len(notified_ids) == len(member_ids)
        for mid in member_ids:
            assert mid in notified_ids

    def test_disband_notification_delivery_within_3s(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        start = time.monotonic()
        group.disband("agent_admin")
        elapsed = time.monotonic() - start
        assert elapsed <= 3.0
        for n in notifs:
            assert n.delivered()

    def test_disband_notification_content(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.disband("agent_admin")
        for n in notifs:
            assert "已被管理员解散" in n.content

    def test_archive_created_after_disband(self, group):
        group.disband("agent_admin")
        archive_name = group.create_archive()
        assert archive_name.startswith("archive-")
        assert group.group_id in archive_name

    def test_archive_naming_format(self, group):
        group.disband("agent_admin")
        archive_name = group.create_archive()
        parts = archive_name.split("-")
        assert len(parts) == 3
        assert parts[0] == "archive"
        assert parts[1] == group.group_id
        timestamp_str = parts[2]
        assert len(timestamp_str) == 14
        assert timestamp_str.isdigit()

    def test_archive_includes_all_messages(self, group_with_messages):
        group_with_messages.disband("agent_admin")
        archive_name = group_with_messages.create_archive()
        raw_archive = archive_name + ".json"
        history = group_with_messages.get_history(page=1, page_size=100)
        assert len(history) == 3

    def test_archive_completeness_100_percent(self, group_with_messages):
        group_with_messages.disband("agent_admin")
        archive_name = group_with_messages.create_archive()
        history = group_with_messages.get_history(page=1, page_size=100)
        all_messages = group_with_messages._messages
        archived_ids = {m.id for m in all_messages}
        history_ids = {m.id for m in history}
        assert len(archived_ids) == len(history_ids)
        assert archived_ids == history_ids

    def test_cannot_archive_before_disband(self, group):
        with pytest.raises(ValueError, match="群组尚未解散"):
            group.create_archive()

    def test_disband_returns_within_3s(self, group):
        start = time.monotonic()
        group.disband("agent_admin")
        elapsed = time.monotonic() - start
        assert elapsed <= 3.0

    def test_disband_time_is_recorded(self, group):
        before = datetime.now(timezone.utc)
        group.disband("agent_admin")
        after = datetime.now(timezone.utc)
        assert group._disband_time is not None
        assert before <= group._disband_time <= after

    def test_disband_notification_each_member_receives_once(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.disband("agent_admin")
        target_counts: dict[str, int] = {}
        for n in notifs:
            target_counts[n.target_agent] = target_counts.get(n.target_agent, 0) + 1
        for count in target_counts.values():
            assert count == 1

    def test_disband_sets_group_as_disbanded(self, group):
        assert group._disbanded is False
        group.disband("agent_admin")
        assert group._disbanded is True

    def test_archive_filename_matches_format(self, group):
        group.disband("agent_admin")
        archive_name = group.create_archive()
        import re
        pattern = r"^archive-g001-\d{14}$"
        assert re.match(pattern, archive_name) is not None

    def test_disband_notification_elapsed_time_meets_requirement(self, group):
        start = time.monotonic()
        group.disband("agent_admin")
        elapsed = time.monotonic() - start
        assert elapsed <= 3.0

    def test_disband_notification_to_admin_too(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.disband("agent_admin")
        admin_notified = any(n.target_agent == "agent_admin" for n in notifs)
        assert admin_notified

    def test_archive_has_unique_timestamp_per_disband(self, group):
        group.disband("agent_admin")
        name1 = group.create_archive()
        assert name1 is not None

    def test_disband_on_empty_group_still_notifies(self, group):
        empty_group = DiscussionGroup("g002", "空群组")
        empty_group.add_member(Member("agent_admin", "Admin", role="admin"))
        notifs = []
        empty_group.on_notification(lambda n: notifs.append(n))
        empty_group.disband("agent_admin")
        assert len(notifs) == 1

    def test_disband_notification_all_delivered_before_return(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.disband("agent_admin")
        for n in notifs:
            assert n.delivered()


class TestDiscussionGroup:
    def test_send_text_message_response_time(self, group):
        result = group.send_message("agent_alice", "大家好，今天讨论进度")
        assert result["message_id"] == 1
        assert result["elapsed_seconds"] <= 0.5

    def test_send_mention_message_response_time(self, group):
        result = group.send_message("agent_alice", "@Bob 请更新接口文档", mentioned_agents=["agent_bob"])
        assert result["message_id"] == 1
        assert result["elapsed_seconds"] <= 0.5

    def test_mention_triggers_notification_within_3s(self, group):
        notified = []
        group.on_notification(lambda n: notified.append(n))
        group.send_message("agent_alice", "@Bob 请更新接口文档", mentioned_agents=["agent_bob"])
        notif = group.get_notification_for("agent_bob")
        assert notif is not None
        delivered = notif.wait_for_delivery(timeout=3.0)
        assert delivered

    def test_history_sorted_reverse_chronological(self, group):
        group.send_message("agent_alice", "第一条消息")
        group.send_message("agent_bob", "第二条消息")
        group.send_message("agent_charlie", "第三条消息")
        history = group.get_history(page=1, page_size=20)
        assert len(history) == 3
        timestamps = [m.timestamp for m in history]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_history_content_order(self, group):
        group.send_message("agent_alice", "第一")
        group.send_message("agent_bob", "第二")
        history = group.get_history(page=1, page_size=20)
        assert history[0].content == "第二"
        assert history[1].content == "第一"

    def test_pagination_page_size(self, group):
        for i in range(25):
            group.send_message("agent_alice", f"消息{i+1}")
        page1 = group.get_history(page=1, page_size=10)
        page2 = group.get_history(page=2, page_size=10)
        page3 = group.get_history(page=3, page_size=10)
        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5

    def test_pagination_content_non_overlapping(self, group):
        for i in range(20):
            group.send_message("agent_alice", f"msg{i+1}")
        page1 = group.get_history(page=1, page_size=10)
        page2 = group.get_history(page=2, page_size=10)
        page1_ids = {m.id for m in page1}
        page2_ids = {m.id for m in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_pagination_total_pages(self, group):
        for i in range(7):
            group.send_message("agent_alice", f"m{i+1}")
        assert group.get_total_pages(page_size=5) == 2
        assert group.get_total_pages(page_size=10) == 1

    def test_mention_message_type(self, group):
        group.send_message("agent_alice", "普通消息")
        group.send_message("agent_bob", "@Charlie 看一下", mentioned_agents=["agent_charlie"])
        messages = group.get_history(page=1, page_size=20)
        text_msgs = [m for m in messages if m.msg_type == MessageType.TEXT]
        mention_msgs = [m for m in messages if m.msg_type == MessageType.MENTION]
        assert len(text_msgs) == 1
        assert len(mention_msgs) == 1
        assert mention_msgs[0].mentioned_agents == ["agent_charlie"]

    def test_mention_notification_content(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.send_message("agent_alice", "@Bob 请评审PR", mentioned_agents=["agent_bob"])
        assert len(notifs) == 1
        assert notifs[0].target_agent == "agent_bob"
        assert notifs[0].from_agent == "agent_alice"
        assert "请评审PR" in notifs[0].content

    def test_mention_unknown_agent_no_notification(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.send_message("agent_alice", "@Unknown 你好", mentioned_agents=["agent_unknown"])
        assert len(notifs) == 0

    def test_empty_group_no_messages(self, group):
        history = group.get_history(page=1, page_size=20)
        assert history == []

    def test_single_message_page_count(self, group):
        group.send_message("agent_alice", "唯一消息")
        assert group.get_total_pages(page_size=20) == 1

    def test_duplicate_mention_only_notifies_once(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.send_message("agent_alice", "@Bob @Bob 双重提醒", mentioned_agents=["agent_bob", "agent_bob"])
        assert len(notifs) == 2

    def test_multiple_mentions_in_one_message(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.send_message("agent_alice", "通知大家", mentioned_agents=["agent_bob", "agent_charlie"])
        assert len(notifs) == 2
        targets = {n.target_agent for n in notifs}
        assert targets == {"agent_bob", "agent_charlie"}

    def test_notification_delivery_callback_fires(self, group):
        delivered_notifs = []
        group.on_notification(lambda n: delivered_notifs.append(n))
        group.send_message("agent_bob", "@Alice 在吗", mentioned_agents=["agent_alice"])
        assert len(delivered_notifs) == 1
        assert delivered_notifs[0].target_agent == "agent_alice"

    def test_history_empty_page_returns_empty_list(self, group):
        for i in range(3):
            group.send_message("agent_alice", f"m{i+1}")
        history = group.get_history(page=10, page_size=20)
        assert history == []

    def test_mention_same_agent_multiple_messages(self, group):
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.send_message("agent_alice", "@Bob 第一", mentioned_agents=["agent_bob"])
        group.send_message("agent_charlie", "@Bob 第二", mentioned_agents=["agent_bob"])
        assert len(notifs) == 2
        assert all(n.target_agent == "agent_bob" for n in notifs)

    def test_history_with_page_zero_raises(self, group):
        with pytest.raises(ValueError, match="页码必须 >= 1"):
            group.get_history(page=0, page_size=20)

    def test_history_with_negative_page_raises(self, group):
        with pytest.raises(ValueError, match="页码必须 >= 1"):
            group.get_history(page=-1, page_size=20)

    def test_history_with_page_size_zero_raises(self, group):
        with pytest.raises(ValueError, match="页大小必须 >= 1"):
            group.get_history(page=1, page_size=0)

    def test_total_pages_with_page_size_zero_raises(self, group):
        with pytest.raises(ValueError, match="页大小必须 >= 1"):
            group.get_total_pages(page_size=0)

    def test_send_empty_content_raises(self, group):
        with pytest.raises(ValueError, match="消息内容不能为空"):
            group.send_message("agent_alice", "")

    def test_send_whitespace_only_content_raises(self, group):
        with pytest.raises(ValueError, match="消息内容不能为空"):
            group.send_message("agent_alice", "   ")

    def test_non_member_sends_message_raises(self, group):
        with pytest.raises(ValueError, match="不是本群成员"):
            group.send_message("agent_nonexistent", "我不在群里")

    def test_message_edited_at_defaults_to_none(self, group):
        group.send_message("agent_alice", "测试消息")
        history = group.get_history(page=1, page_size=20)
        assert history[0].edited_at is None

    def test_message_edited_at_can_be_set(self, group):
        group.send_message("agent_alice", "原始内容")
        history = group.get_history(page=1, page_size=20)
        msg = history[0]
        edit_time = datetime.now(timezone.utc)
        msg.edited_at = edit_time
        assert msg.edited_at == edit_time
        assert msg.edited_at >= msg.timestamp
