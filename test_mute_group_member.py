from __future__ import annotations

import pytest
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone, timedelta
from enum import Enum


class MessageType(Enum):
    TEXT = "text"
    MENTION = "mention"


class MuteDuration(Enum):
    FIFTEEN_MIN = 15 * 60
    ONE_HOUR = 60 * 60
    SIX_HOURS = 6 * 60 * 60
    TWENTY_FOUR_HOURS = 24 * 60 * 60


@dataclass
class Member:
    agent_id: str
    name: str
    role: str = "member"


@dataclass
class MuteInfo:
    member_id: str
    muted_by: str
    muted_at: datetime
    duration_seconds: int

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.muted_at + timedelta(seconds=self.duration_seconds)

    @property
    def remaining_seconds(self) -> float:
        remaining = self.duration_seconds - (datetime.now(timezone.utc) - self.muted_at).total_seconds()
        return max(0.0, remaining)


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
        self._muted_members: dict[str, MuteInfo] = {}
        self._moderators: set[str] = set()

    def add_member(self, member: Member):
        self.members[member.agent_id] = member
        if member.role == "admin":
            self._admins.add(member.agent_id)
        if member.role == "moderator":
            self._moderators.add(member.agent_id)

    def set_admin(self, agent_id: str):
        if agent_id in self.members:
            self.members[agent_id].role = "admin"
            self._admins.add(agent_id)

    def set_moderator(self, agent_id: str):
        if agent_id in self.members:
            self.members[agent_id].role = "moderator"
            self._moderators.add(agent_id)

    def _can_mute(self, agent_id: str) -> bool:
        return agent_id in self._admins or agent_id in self._moderators

    def mute_member(self, operator_id: str, target_id: str, duration_seconds: int) -> dict:
        start = time.monotonic()
        if not self._can_mute(operator_id):
            raise PermissionError(f"用户 {operator_id} 不是管理员或主持人，无法禁言成员")
        if operator_id == target_id:
            raise ValueError("不能禁言自己")
        if target_id not in self.members:
            raise ValueError(f"成员 {target_id} 不在群中")
        if target_id in self._muted_members and not self._muted_members[target_id].is_expired:
            raise ValueError(f"成员 {target_id} 已被禁言")
        mute_info = MuteInfo(
            member_id=target_id,
            muted_by=operator_id,
            muted_at=datetime.now(timezone.utc),
            duration_seconds=duration_seconds,
        )
        self._muted_members[target_id] = mute_info
        log = OperationLog(
            id=self._log_next_id,
            operator_id=operator_id,
            action="mute_member",
            target_id=target_id,
            details=f"{operator_id} 禁言了成员 {target_id}，时长 {duration_seconds} 秒",
            timestamp=datetime.now(timezone.utc),
        )
        self._operation_logs.append(log)
        self._log_next_id += 1
        elapsed = time.monotonic() - start
        return {
            "status": "success",
            "muted_member_id": target_id,
            "duration_seconds": duration_seconds,
            "elapsed_seconds": elapsed,
            "log_id": log.id,
        }

    def unmute_member(self, operator_id: str, target_id: str) -> dict:
        start = time.monotonic()
        if not self._can_mute(operator_id):
            raise PermissionError(f"用户 {operator_id} 不是管理员或主持人，无法解除禁言")
        if target_id not in self.members:
            raise ValueError(f"成员 {target_id} 不在群中")
        if target_id not in self._muted_members or self._muted_members[target_id].is_expired:
            raise ValueError(f"成员 {target_id} 未被禁言")
        del self._muted_members[target_id]
        log = OperationLog(
            id=self._log_next_id,
            operator_id=operator_id,
            action="unmute_member",
            target_id=target_id,
            details=f"{operator_id} 解除了对 {target_id} 的禁言",
            timestamp=datetime.now(timezone.utc),
        )
        self._operation_logs.append(log)
        self._log_next_id += 1
        elapsed = time.monotonic() - start
        return {"status": "success", "unmuted_member_id": target_id, "elapsed_seconds": elapsed, "log_id": log.id}

    def is_muted(self, agent_id: str) -> bool:
        if agent_id not in self.members:
            self._muted_members.pop(agent_id, None)
            return False
        if agent_id not in self._muted_members:
            return False
        if self._muted_members[agent_id].is_expired:
            del self._muted_members[agent_id]
            return False
        return True

    def send_message(self, sender: str, content: str, mentioned_agents: Optional[list[str]] = None) -> dict:
        start = time.monotonic()
        if not content.strip():
            raise ValueError("消息内容不能为空")
        if sender not in self.members:
            raise ValueError(f"发送者 {sender} 不是本群成员")
        if self.is_muted(sender):
            raise PermissionError("您已被禁言")
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
                    if agent_id in self.members and not self.is_muted(agent_id):
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

    def get_operation_logs(self, action: Optional[str] = None) -> list[OperationLog]:
        if action:
            return [log for log in self._operation_logs if log.action == action]
        return list(self._operation_logs)

    def can_receive_messages(self, agent_id: str) -> bool:
        return agent_id in self.members

    def can_access_resources(self, agent_id: str) -> bool:
        return agent_id in self.members


@pytest.fixture
def group():
    g = DiscussionGroup("g003", "禁言测试群")
    g.add_member(Member("admin_x", "AdminX", role="admin"))
    g.add_member(Member("mod_m", "ModM", role="moderator"))
    g.add_member(Member("member_y", "MemberY", role="member"))
    g.add_member(Member("member_z", "MemberZ", role="member"))
    return g


class TestMuteGroupMember:
    def test_admin_can_mute_member(self, group):
        result = group.mute_member("admin_x", "member_y", 900)
        assert result["status"] == "success"
        assert result["muted_member_id"] == "member_y"

    def test_moderator_can_mute_member(self, group):
        result = group.mute_member("mod_m", "member_y", 900)
        assert result["status"] == "success"
        assert result["muted_member_id"] == "member_y"

    def test_mute_response_time_under_1s(self, group):
        result = group.mute_member("admin_x", "member_y", 900)
        assert result["elapsed_seconds"] <= 1.0

    def test_mute_effect_takes_effect_immediately(self, group):
        mute_start = time.monotonic()
        group.mute_member("admin_x", "member_y", 900)
        mute_end = time.monotonic()
        is_muted = group.is_muted("member_y")
        check_end = time.monotonic()
        total_delay = (mute_end - mute_start) + (check_end - mute_end)
        assert is_muted is True
        assert total_delay <= 1.0

    def test_muted_member_send_message_returns_muted_error(self, group):
        group.mute_member("admin_x", "member_y", 900)
        with pytest.raises(PermissionError, match="您已被禁言"):
            group.send_message("member_y", "测试消息")

    def test_muted_member_message_not_delivered_to_history(self, group):
        group.mute_member("admin_x", "member_y", 900)
        with pytest.raises(PermissionError):
            group.send_message("member_y", "这条不会出现在历史")
        history = group.get_history(page=1, page_size=20)
        assert all(m.content != "这条不会出现在历史" for m in history)

    def test_unmuted_member_can_send_again(self, group):
        group.mute_member("admin_x", "member_y", 900)
        with pytest.raises(PermissionError, match="您已被禁言"):
            group.send_message("member_y", "禁言中")
        group.unmute_member("admin_x", "member_y")
        result = group.send_message("member_y", "终于可以说话了")
        assert result["message_id"] >= 1

    def test_mute_duration_fifteen_min(self, group):
        result = group.mute_member("admin_x", "member_y", MuteDuration.FIFTEEN_MIN.value)
        assert result["duration_seconds"] == 900

    def test_mute_duration_one_hour(self, group):
        result = group.mute_member("admin_x", "member_y", MuteDuration.ONE_HOUR.value)
        assert result["duration_seconds"] == 3600

    def test_mute_duration_six_hours(self, group):
        result = group.mute_member("admin_x", "member_y", MuteDuration.SIX_HOURS.value)
        assert result["duration_seconds"] == 21600

    def test_mute_duration_twenty_four_hours(self, group):
        result = group.mute_member("admin_x", "member_y", MuteDuration.TWENTY_FOUR_HOURS.value)
        assert result["duration_seconds"] == 86400

    def test_mute_duration_custom(self, group):
        result = group.mute_member("admin_x", "member_y", 7200)
        assert result["duration_seconds"] == 7200

    def test_muted_member_auto_unmute_after_expiry(self, group):
        group.mute_member("admin_x", "member_y", 1)
        time.sleep(1.1)
        assert group.is_muted("member_y") is False

    def test_muted_member_can_send_after_expiry(self, group):
        group.mute_member("admin_x", "member_y", 1)
        time.sleep(1.1)
        assert group.is_muted("member_y") is False
        result = group.send_message("member_y", "禁言过期了")
        assert result["message_id"] >= 1

    def test_non_admin_moderator_cannot_mute(self, group):
        with pytest.raises(PermissionError, match="不是管理员或主持人"):
            group.mute_member("member_y", "member_z", 900)

    def test_admin_cannot_mute_self(self, group):
        with pytest.raises(ValueError, match="不能禁言自己"):
            group.mute_member("admin_x", "admin_x", 900)

    def test_moderator_cannot_mute_self(self, group):
        with pytest.raises(ValueError, match="不能禁言自己"):
            group.mute_member("mod_m", "mod_m", 900)

    def test_cannot_mute_nonexistent_member(self, group):
        with pytest.raises(ValueError, match="不在群中"):
            group.mute_member("admin_x", "nonexistent", 900)

    def test_cannot_mute_already_muted_member(self, group):
        group.mute_member("admin_x", "member_y", 900)
        with pytest.raises(ValueError, match="已被禁言"):
            group.mute_member("admin_x", "member_y", 900)

    def test_mute_operation_log_recorded(self, group):
        group.mute_member("admin_x", "member_y", 900)
        logs = group.get_operation_logs(action="mute_member")
        assert len(logs) == 1

    def test_mute_log_contains_operator_id(self, group):
        group.mute_member("admin_x", "member_y", 900)
        logs = group.get_operation_logs(action="mute_member")
        assert logs[0].operator_id == "admin_x"

    def test_mute_log_contains_target_id(self, group):
        group.mute_member("admin_x", "member_y", 900)
        logs = group.get_operation_logs(action="mute_member")
        assert logs[0].target_id == "member_y"

    def test_mute_log_contains_duration_in_details(self, group):
        group.mute_member("admin_x", "member_y", 900)
        logs = group.get_operation_logs(action="mute_member")
        assert "900" in logs[0].details

    def test_unmute_log_recorded(self, group):
        group.mute_member("admin_x", "member_y", 900)
        group.unmute_member("admin_x", "member_y")
        unmute_logs = group.get_operation_logs(action="unmute_member")
        assert len(unmute_logs) == 1

    def test_unmute_log_contains_operator_id(self, group):
        group.mute_member("admin_x", "member_y", 900)
        group.unmute_member("admin_x", "member_y")
        logs = group.get_operation_logs(action="unmute_member")
        assert logs[0].operator_id == "admin_x"

    def test_unmute_restores_send_ability(self, group):
        group.mute_member("admin_x", "member_y", 900)
        with pytest.raises(PermissionError):
            group.send_message("member_y", "被禁言")
        group.unmute_member("admin_x", "member_y")
        result = group.send_message("member_y", "已解除禁言")
        assert result["message_id"] >= 1

    def test_unmute_not_muted_member_raises(self, group):
        with pytest.raises(ValueError, match="未被禁言"):
            group.unmute_member("admin_x", "member_y")

    def test_non_admin_moderator_cannot_unmute(self, group):
        group.mute_member("admin_x", "member_y", 900)
        with pytest.raises(PermissionError, match="不是管理员或主持人"):
            group.unmute_member("member_y", "member_z")

    def test_other_members_not_affected_by_one_mute(self, group):
        group.mute_member("admin_x", "member_y", 900)
        result_z = group.send_message("member_z", "我还能发消息")
        assert result_z["message_id"] >= 1

    def test_muted_member_cannot_mention_others(self, group):
        group.mute_member("admin_x", "member_y", 900)
        with pytest.raises(PermissionError, match="您已被禁言"):
            group.send_message("member_y", "@mod_m 你好", mentioned_agents=["mod_m"])

    def test_muted_member_mentioned_by_others_message_delivered(self, group):
        group.mute_member("admin_x", "member_y", 900)
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        result = group.send_message("member_z", "@MemberY 你好", mentioned_agents=["member_y"])
        assert result["message_id"] >= 1
        notif = group.get_notification_for("member_y")
        assert notif is None

    def test_admin_or_moderator_can_mute_other_admin(self, group):
        group.add_member(Member("admin_w", "AdminW", role="admin"))
        result = group.mute_member("admin_x", "admin_w", 900)
        assert result["status"] == "success"
        assert group.is_muted("admin_w") is True

    def test_multiple_members_can_be_muted_separately(self, group):
        group.mute_member("admin_x", "member_y", 3600)
        group.mute_member("admin_x", "member_z", 3600)
        assert group.is_muted("member_y") is True
        assert group.is_muted("member_z") is True

    def test_mute_info_contains_correct_duration(self, group):
        group.mute_member("admin_x", "member_y", 1800)
        assert group._muted_members["member_y"].duration_seconds == 1800

    def test_mute_info_contains_muted_by(self, group):
        group.mute_member("admin_x", "member_y", 900)
        assert group._muted_members["member_y"].muted_by == "admin_x"

    def test_mute_info_remaining_seconds_decreases(self, group):
        group.mute_member("admin_x", "member_y", 5)
        remaining_before = group._muted_members["member_y"].remaining_seconds
        time.sleep(0.5)
        remaining_after = group._muted_members["member_y"].remaining_seconds
        assert remaining_after < remaining_before

    def test_re_mute_after_expiry_allowed(self, group):
        group.mute_member("admin_x", "member_y", 1)
        time.sleep(1.1)
        assert group.is_muted("member_y") is False
        result = group.mute_member("admin_x", "member_y", 3600)
        assert result["status"] == "success"

    def test_muted_member_notification_not_delivered_when_muted(self, group):
        group.mute_member("admin_x", "member_y", 900)
        notifs = []
        group.on_notification(lambda n: notifs.append(n))
        group.send_message("member_z", "@MemberY 注意", mentioned_agents=["member_y"])
        targeted = [n for n in notifs if n.target_agent == "member_y"]
        assert len(targeted) == 0

    def test_removed_muted_member_clears_mute_info(self, group):
        group.mute_member("admin_x", "member_y", 900)
        assert group.is_muted("member_y") is True
        group.members.pop("member_y")
        assert group.is_muted("member_y") is False

    def test_mute_then_unmute_then_mute_again(self, group):
        group.mute_member("admin_x", "member_y", 3600)
        group.unmute_member("admin_x", "member_y")
        result = group.mute_member("admin_x", "member_y", 7200)
        assert result["status"] == "success"
        assert group.is_muted("member_y") is True
