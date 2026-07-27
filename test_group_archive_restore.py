from __future__ import annotations

import pytest
import time
import json
import copy
import threading
from dataclasses import dataclass, field
from typing import Optional, List
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
    mentioned_agents: List[str]
    timestamp: datetime
    edited_at: Optional[datetime] = None


@dataclass
class GroupArchive:
    """群归档数据"""
    group_id: str
    name: str
    members: List[Member]
    messages: List[Message]
    archived_at: datetime
    message_count: int


class GroupArchiveService:
    """群归档服务"""

    def __init__(self):
        self._archives: dict[str, GroupArchive] = {}
        self._lock = threading.Lock()

    def archive_group(self, group: "DiscussionGroup") -> GroupArchive:
        """归档群组"""
        with group._lock:
            messages_copy = list(group._messages)
        members_copy = [
            Member(agent_id=aid, name=m.name, role=m.role)
            for aid, m in group.members.items()
        ]
        archive = GroupArchive(
            group_id=group.group_id,
            name=group.name,
            members=members_copy,
            messages=messages_copy,
            archived_at=datetime.now(timezone.utc),
            message_count=len(messages_copy),
        )
        with self._lock:
            self._archives[group.group_id] = archive
        return archive

    def get_archive(self, group_id: str) -> Optional[GroupArchive]:
        """获取归档数据"""
        with self._lock:
            archive = self._archives.get(group_id)
        if archive is None:
            return None
        return copy.deepcopy(archive)

    def restore_group(self, archive: GroupArchive) -> "DiscussionGroup":
        """从归档恢复群组"""
        group = DiscussionGroup(archive.group_id, archive.name)
        for member in archive.members:
            group.add_member(member)
            if member.role == "admin":
                group.set_admin(member.agent_id)
        for msg in archive.messages:
            restored_msg = Message(
                id=msg.id,
                sender=msg.sender,
                content=msg.content,
                msg_type=msg.msg_type,
                mentioned_agents=list(msg.mentioned_agents),
                timestamp=msg.timestamp,
                edited_at=msg.edited_at,
            )
            with group._lock:
                group._messages.append(restored_msg)
                if restored_msg.id >= group._next_id:
                    group._next_id = restored_msg.id + 1
        return group

    def archive_exists(self, group_id: str) -> bool:
        """检查是否存在归档"""
        with self._lock:
            return group_id in self._archives


class DiscussionGroup:
    def __init__(self, group_id: str, name: str):
        self.group_id = group_id
        self.name = name
        self.members: dict[str, Member] = {}
        self._messages: List[Message] = []
        self._next_id: int = 1
        self._lock = threading.Lock()
        self._pending_notifications: List = []
        self._notification_callbacks: List = []
        self._admins: set[str] = set()

    def add_member(self, member: Member):
        self.members[member.agent_id] = member
        if member.role == "admin":
            self._admins.add(member.agent_id)

    def set_admin(self, agent_id: str):
        if agent_id in self.members:
            self.members[agent_id].role = "admin"
            self._admins.add(agent_id)

    def send_message(self, sender: str, content: str, mentioned_agents: Optional[List[str]] = None) -> dict:
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
        elapsed = time.monotonic() - start
        return {"message_id": msg.id, "elapsed_seconds": elapsed}

    def get_history(self, page: int = 1, page_size: int = 20) -> List[Message]:
        with self._lock:
            reversed_msgs = list(reversed(self._messages))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            return reversed_msgs[start_idx:end_idx]

    def get_all_messages(self) -> List[Message]:
        with self._lock:
            return list(self._messages)

    def get_member_ids(self) -> List[str]:
        return list(self.members.keys())


def _build_group_with_messages(count: int) -> DiscussionGroup:
    """构建含指定数量消息的群组（用于性能测试）"""
    g = DiscussionGroup("g_perf", "性能测试群")
    g.add_member(Member("agent_a", "Alice", role="admin"))
    g.add_member(Member("agent_b", "Bob"))
    g.add_member(Member("agent_c", "Charlie"))

    base_time = datetime.now(timezone.utc)
    for i in range(count):
        msg = Message(
            id=i + 1,
            sender=["agent_a", "agent_b", "agent_c"][i % 3],
            content=f"消息内容 {i + 1}",
            msg_type=MessageType.TEXT,
            mentioned_agents=[],
            timestamp=base_time,
        )
        with g._lock:
            g._messages.append(msg)
        g._next_id = count + 1
    return g


@pytest.fixture
def archive_service():
    return GroupArchiveService()


@pytest.fixture
def group():
    g = DiscussionGroup("g001", "项目Alpha讨论群")
    g.add_member(Member("agent_alice", "Alice", role="admin"))
    g.add_member(Member("agent_bob", "Bob"))
    g.add_member(Member("agent_charlie", "Charlie"))
    return g


@pytest.fixture
def group_with_messages(group):
    group.send_message("agent_alice", "大家好，欢迎进群")
    group.send_message("agent_bob", "收到，我会跟进接口文档")
    group.send_message("agent_charlie", "我负责前端部分")
    return group


class TestGroupArchiveRestore:
    """群组归档恢复 — 验收标准：
    1. 消息量 10 万条以下，恢复时间 ≤ 30 秒
    2. 消息量 100 万条以下，恢复时间 ≤ 2 分钟
    3. 恢复后群继承归档时的历史消息和成员列表
    """

    # ---- 归档基础功能 ----

    def test_archive_creates_archive_record(self, archive_service, group):
        archive = archive_service.archive_group(group)
        assert archive.group_id == "g001"
        assert archive.name == "项目Alpha讨论群"
        assert archive.message_count == 0
        assert len(archive.members) == 3

    def test_archive_contains_all_members(self, archive_service, group):
        archive = archive_service.archive_group(group)
        member_ids = [m.agent_id for m in archive.members]
        assert "agent_alice" in member_ids
        assert "agent_bob" in member_ids
        assert "agent_charlie" in member_ids

    def test_archive_preserves_member_roles(self, archive_service, group):
        archive = archive_service.archive_group(group)
        roles = {m.agent_id: m.role for m in archive.members}
        assert roles["agent_alice"] == "admin"
        assert roles["agent_bob"] == "member"
        assert roles["agent_charlie"] == "member"

    def test_archive_contains_all_messages(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        assert archive.message_count == 3
        contents = [m.content for m in archive.messages]
        assert "大家好，欢迎进群" in contents
        assert "收到，我会跟进接口文档" in contents
        assert "我负责前端部分" in contents

    def test_archive_stores_message_order(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        assert archive.messages[0].content == "大家好，欢迎进群"
        assert archive.messages[1].content == "收到，我会跟进接口文档"
        assert archive.messages[2].content == "我负责前端部分"

    def test_archive_stores_message_senders(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        assert archive.messages[0].sender == "agent_alice"
        assert archive.messages[1].sender == "agent_bob"
        assert archive.messages[2].sender == "agent_charlie"

    def test_archive_stores_message_ids(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        assert archive.messages[0].id == 1
        assert archive.messages[1].id == 2
        assert archive.messages[2].id == 3

    def test_archive_recorded_at_valid_time(self, archive_service, group):
        before = datetime.now(timezone.utc)
        archive = archive_service.archive_group(group)
        after = datetime.now(timezone.utc)
        assert archive.archived_at >= before
        assert archive.archived_at <= after

    def test_archive_exists_returns_true_after_archive(self, archive_service, group):
        archive_service.archive_group(group)
        assert archive_service.archive_exists("g001") is True

    def test_archive_exists_returns_false_before_archive(self, archive_service):
        assert archive_service.archive_exists("g_nonexistent") is False

    def test_get_archive_returns_archive_data(self, archive_service, group):
        archive_service.archive_group(group)
        retrieved = archive_service.get_archive("g001")
        assert retrieved is not None
        assert retrieved.group_id == "g001"

    def test_get_archive_returns_none_for_missing_group(self, archive_service):
        retrieved = archive_service.get_archive("g_missing")
        assert retrieved is None

    def test_get_archive_returns_deep_copy(self, archive_service, group):
        archive_service.archive_group(group)
        a1 = archive_service.get_archive("g001")
        a2 = archive_service.get_archive("g001")
        a1.messages.append(Message(99, "x", "fake", MessageType.TEXT, [], datetime.now(timezone.utc)))
        assert len(a2.messages) == 0

    # ---- 恢复后继承历史消息 ----

    def test_restored_group_has_correct_group_id(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        assert restored.group_id == "g001"

    def test_restored_group_has_correct_name(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        assert restored.name == "项目Alpha讨论群"

    def test_restored_group_has_all_messages(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        assert len(all_msgs) == 3

    def test_restored_group_messages_preserve_content(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        contents = [m.content for m in all_msgs]
        assert "大家好，欢迎进群" in contents
        assert "收到，我会跟进接口文档" in contents
        assert "我负责前端部分" in contents

    def test_restored_group_messages_preserve_senders(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        assert all_msgs[0].sender == "agent_alice"
        assert all_msgs[1].sender == "agent_bob"
        assert all_msgs[2].sender == "agent_charlie"

    def test_restored_group_messages_preserve_ids(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        assert all_msgs[0].id == 1
        assert all_msgs[1].id == 2
        assert all_msgs[2].id == 3

    def test_restored_group_messages_preserve_order(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        assert all_msgs[0].content == "大家好，欢迎进群"
        assert all_msgs[1].content == "收到，我会跟进接口文档"
        assert all_msgs[2].content == "我负责前端部分"

    def test_restored_group_messages_preserve_timestamps(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        for i in range(3):
            assert all_msgs[i].timestamp == archive.messages[i].timestamp

    def test_restored_group_messages_preserve_types(self, archive_service, group):
        group.send_message("agent_alice", "普通消息")
        group.send_message("agent_bob", "@Charlie 看一下", mentioned_agents=["agent_charlie"])
        archive = archive_service.archive_group(group)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        assert all_msgs[0].msg_type == MessageType.TEXT
        assert all_msgs[1].msg_type == MessageType.MENTION

    def test_restored_group_messages_preserve_mentions(self, archive_service, group):
        group.send_message("agent_alice", "普通消息")
        group.send_message("agent_bob", "@Charlie 看一下", mentioned_agents=["agent_charlie"])
        archive = archive_service.archive_group(group)
        restored = archive_service.restore_group(archive)
        all_msgs = restored.get_all_messages()
        assert all_msgs[0].mentioned_agents == []
        assert all_msgs[1].mentioned_agents == ["agent_charlie"]

    def test_restored_group_can_send_new_messages(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        result = restored.send_message("agent_alice", "恢复后发送的新消息")
        assert result["message_id"] == 4
        all_msgs = restored.get_all_messages()
        assert len(all_msgs) == 4
        assert all_msgs[-1].content == "恢复后发送的新消息"

    def test_restored_group_new_message_id_does_not_conflict(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        restored.send_message("agent_bob", "新消息 1")
        restored.send_message("agent_charlie", "新消息 2")
        all_msgs = restored.get_all_messages()
        ids = [m.id for m in all_msgs]
        assert len(ids) == len(set(ids))

    # ---- 恢复后继承成员列表 ----

    def test_restored_group_has_all_members(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        member_ids = restored.get_member_ids()
        assert "agent_alice" in member_ids
        assert "agent_bob" in member_ids
        assert "agent_charlie" in member_ids

    def test_restored_group_member_count_matches_archive(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        assert len(restored.members) == len(archive.members)

    def test_restored_group_preserves_member_names(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        assert restored.members["agent_alice"].name == "Alice"
        assert restored.members["agent_bob"].name == "Bob"
        assert restored.members["agent_charlie"].name == "Charlie"

    def test_restored_group_preserves_admin_role(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        assert restored.members["agent_alice"].role == "admin"
        assert "agent_alice" in restored._admins

    def test_restored_group_preserves_member_role(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        assert restored.members["agent_bob"].role == "member"
        assert "agent_bob" not in restored._admins

    def test_restored_group_non_member_cannot_send(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        with pytest.raises(ValueError, match="不是本群成员"):
            restored.send_message("agent_nonexistent", "我不在群里")

    # ---- 空群归档恢复 ----

    def test_restore_empty_group_has_no_messages(self, archive_service, group):
        archive = archive_service.archive_group(group)
        restored = archive_service.restore_group(archive)
        assert len(restored.get_all_messages()) == 0

    def test_restore_empty_group_has_members(self, archive_service, group):
        archive = archive_service.archive_group(group)
        restored = archive_service.restore_group(archive)
        assert len(restored.members) == 3

    def test_restore_empty_group_can_send_first_message(self, archive_service, group):
        archive = archive_service.archive_group(group)
        restored = archive_service.restore_group(archive)
        result = restored.send_message("agent_alice", "第一条消息")
        assert result["message_id"] == 1

    # ---- 性能：10 万条以下 ≤ 30 秒 ----

    def test_restore_10k_messages_within_30_seconds(self, archive_service):
        g = _build_group_with_messages(10_000)
        archive = archive_service.archive_group(g)
        start = time.monotonic()
        restored = archive_service.restore_group(archive)
        elapsed = time.monotonic() - start
        assert elapsed <= 30.0
        assert len(restored.get_all_messages()) == 10_000

    def test_restore_50k_messages_within_30_seconds(self, archive_service):
        g = _build_group_with_messages(50_000)
        archive = archive_service.archive_group(g)
        start = time.monotonic()
        restored = archive_service.restore_group(archive)
        elapsed = time.monotonic() - start
        assert elapsed <= 30.0
        assert len(restored.get_all_messages()) == 50_000

    def test_restore_100k_messages_within_30_seconds(self, archive_service):
        g = _build_group_with_messages(100_000)
        archive = archive_service.archive_group(g)
        start = time.monotonic()
        restored = archive_service.restore_group(archive)
        elapsed = time.monotonic() - start
        assert elapsed <= 30.0
        assert len(restored.get_all_messages()) == 100_000

    # ---- 性能：100 万条以下 ≤ 2 分钟 ----

    def test_restore_200k_messages_within_2_minutes(self, archive_service):
        g = _build_group_with_messages(200_000)
        archive = archive_service.archive_group(g)
        start = time.monotonic()
        restored = archive_service.restore_group(archive)
        elapsed = time.monotonic() - start
        assert elapsed <= 120.0
        assert len(restored.get_all_messages()) == 200_000

    def test_restore_500k_messages_within_2_minutes(self, archive_service):
        g = _build_group_with_messages(500_000)
        archive = archive_service.archive_group(g)
        start = time.monotonic()
        restored = archive_service.restore_group(archive)
        elapsed = time.monotonic() - start
        assert elapsed <= 120.0
        assert len(restored.get_all_messages()) == 500_000

    def test_restore_1m_messages_within_2_minutes(self, archive_service):
        g = _build_group_with_messages(1_000_000)
        archive = archive_service.archive_group(g)
        start = time.monotonic()
        restored = archive_service.restore_group(archive)
        elapsed = time.monotonic() - start
        assert elapsed <= 120.0
        assert len(restored.get_all_messages()) == 1_000_000

    # ---- 恢复后消息完整性校验 ----

    def test_restored_messages_first_last_content_match(self, archive_service):
        g = _build_group_with_messages(1000)
        archive = archive_service.archive_group(g)
        restored = archive_service.restore_group(archive)
        restored_msgs = restored.get_all_messages()
        assert restored_msgs[0].content == "消息内容 1"
        assert restored_msgs[-1].content == "消息内容 1000"

    def test_restored_messages_random_sample_match(self, archive_service):
        g = _build_group_with_messages(5000)
        archive = archive_service.archive_group(g)
        restored = archive_service.restore_group(archive)
        restored_msgs = restored.get_all_messages()
        for i in [0, 100, 2500, 4999]:
            assert restored_msgs[i].content == f"消息内容 {i + 1}"

    def test_restored_members_can_all_send_messages(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        restored = archive_service.restore_group(archive)
        for agent_id in ["agent_alice", "agent_bob", "agent_charlie"]:
            result = restored.send_message(agent_id, "测试消息")
            assert result["elapsed_seconds"] >= 0

    def test_restore_preserves_edited_at_on_messages(self, archive_service, group):
        group.send_message("agent_alice", "原始内容")
        msgs = group.get_all_messages()
        msgs[0].edited_at = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        archive = archive_service.archive_group(group)
        restored = archive_service.restore_group(archive)
        restored_msgs = restored.get_all_messages()
        assert restored_msgs[0].edited_at == datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    # ---- 端到端：归档 → 恢复完整流程 ----

    def test_full_archive_restore_workflow(self, archive_service):
        g = DiscussionGroup("g_e2e", "端到端测试群")
        g.add_member(Member("user1", "用户一", role="admin"))
        g.add_member(Member("user2", "用户二"))
        g.add_member(Member("user3", "用户三"))

        g.send_message("user1", "项目启动")
        g.send_message("user2", "确认收到")
        g.send_message("user3", "我来跟进")

        archive = archive_service.archive_group(g)
        assert archive.message_count == 3
        assert len(archive.members) == 3

        restored = archive_service.restore_group(archive)
        assert restored.group_id == "g_e2e"
        assert restored.name == "端到端测试群"

        all_msgs = restored.get_all_messages()
        assert len(all_msgs) == 3
        assert all_msgs[0].content == "项目启动"
        assert all_msgs[1].content == "确认收到"
        assert all_msgs[2].content == "我来跟进"

        member_ids = restored.get_member_ids()
        assert set(member_ids) == {"user1", "user2", "user3"}
        assert restored.members["user1"].role == "admin"

        result = restored.send_message("user1", "恢复后新消息")
        assert result["message_id"] == 4

        final_msgs = restored.get_all_messages()
        assert len(final_msgs) == 4
        assert final_msgs[-1].content == "恢复后新消息"

    def test_archive_then_restore_multiple_times(self, archive_service, group_with_messages):
        archive = archive_service.archive_group(group_with_messages)
        r1 = archive_service.restore_group(archive)
        r2 = archive_service.restore_group(archive)
        assert len(r1.get_all_messages()) == len(r2.get_all_messages())
        assert len(r1.members) == len(r2.members)
        r2.send_message("agent_alice", "只在 r2 的消息")
        assert len(r1.get_all_messages()) == 3
        assert len(r2.get_all_messages()) == 4

    def test_archive_after_member_change_preserves_new_state(self, archive_service, group):
        group.add_member(Member("agent_new", "NewMember"))
        archive = archive_service.archive_group(group)
        assert len(archive.members) == 4
        restored = archive_service.restore_group(archive)
        assert "agent_new" in restored.get_member_ids()
