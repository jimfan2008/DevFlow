import pytest
import time
import threading
import re
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field
from uuid import uuid4
from collections import defaultdict


@dataclass
class Message:
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    sender: str = ""
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mentions: list[str] = field(default_factory=list)


class NotificationService:
    def __init__(self):
        self._notifications: dict[str, list[tuple[str, datetime]]] = defaultdict(list)

    def notify(self, user: str, message_id: str):
        self._notifications[user].append((message_id, datetime.now(timezone.utc)))

    def get_notification_time(self, user: str, message_id: str) -> Optional[datetime]:
        for mid, ts in self._notifications.get(user, []):
            if mid == message_id:
                return ts
        return None

    def has_user_received(self, user: str, message_id: str) -> bool:
        return self.get_notification_time(user, message_id) is not None


@dataclass
class ArchiveRecord:
    group_id: str
    filename: str
    messages: list[Message]
    archived_at: datetime


class DiscussionGroup:
    def __init__(self, group_id: str, notification_service: Optional[NotificationService] = None):
        self.group_id = group_id
        self._messages: list[Message] = []
        self._lock = threading.Lock()
        self._notification_service = notification_service or NotificationService()
        self._members: list[str] = []
        self._dissolved = False

    def add_member(self, user: str):
        with self._lock:
            self._members.append(user)

    @property
    def members(self) -> list[str]:
        with self._lock:
            return list(self._members)

    def send_message(self, sender: str, content: str) -> Message:
        mentions = []
        for word in content.split():
            if word.startswith("@"):
                mentions.append(word[1:])
        msg = Message(sender=sender, content=content, mentions=mentions)
        with self._lock:
            self._messages.append(msg)
        for user in mentions:
            self._notification_service.notify(user, msg.id)
        return msg

    def get_history(self, page: int = 1, page_size: int = 20) -> list[Message]:
        with self._lock:
            total = len(self._messages)
            start = max(0, total - page * page_size)
            end = total - (page - 1) * page_size
            if start < 0:
                start = 0
            if end <= start:
                return []
            return list(reversed(self._messages[start:end]))

    def dissolve(self, admin: str) -> ArchiveRecord:
        with self._lock:
            self._dissolved = True
            all_messages = list(self._messages)
            now = datetime.now(timezone.utc)
            filename = f"archive-{self.group_id}-{now.strftime('%Y%m%d%H%M%S')}"
            record = ArchiveRecord(
                group_id=self.group_id,
                filename=filename,
                messages=all_messages,
                archived_at=now,
            )
            for member in self._members:
                self._notification_service.notify(member, f"DISSOLVE:{self.group_id}")
            return record

    def is_dissolved(self) -> bool:
        with self._lock:
            return self._dissolved

    @property
    def notification_service(self) -> NotificationService:
        return self._notification_service


class TestGroupDissolve:
    def test_dissolve_notification_all_members_within_3s(self):
        group = DiscussionGroup(group_id="g001")
        for user in ["alice", "bob", "carol", "dave"]:
            group.add_member(user)
        group.send_message("alice", "hello everyone")
        start = time.monotonic()
        archive = group.dissolve("alice")
        elapsed = time.monotonic() - start
        assert elapsed < 3.0
        for user in ["alice", "bob", "carol", "dave"]:
            assert group.notification_service.has_user_received(user, f"DISSOLVE:{group.group_id}")

    def test_dissolve_archives_all_messages(self):
        group = DiscussionGroup(group_id="g002")
        group.add_member("alice")
        group.add_member("bob")
        m1 = group.send_message("alice", "first message")
        m2 = group.send_message("bob", "second message")
        m3 = group.send_message("alice", "third message")
        archive = group.dissolve("alice")
        archived_ids = [m.id for m in archive.messages]
        assert m1.id in archived_ids
        assert m2.id in archived_ids
        assert m3.id in archived_ids
        assert len(archive.messages) == 3

    def test_dissolve_archive_includes_all_history(self):
        group = DiscussionGroup(group_id="g003")
        group.add_member("alice")
        sent = []
        for i in range(10):
            msg = group.send_message("alice", f"msg_{i}")
            sent.append(msg)
        archive = group.dissolve("alice")
        archived_ids = {m.id for m in archive.messages}
        sent_ids = {m.id for m in sent}
        assert archived_ids == sent_ids
        assert len(archive.messages) == 10

    def test_archive_filename_format(self):
        group = DiscussionGroup(group_id="g004")
        group.add_member("alice")
        group.send_message("alice", "test")
        archive = group.dissolve("alice")
        pattern = r"^archive-g004-\d{14}$"
        assert re.match(pattern, archive.filename), f"Filename {archive.filename} does not match pattern {pattern}"

    def test_archive_contains_group_id(self):
        group = DiscussionGroup(group_id="g005")
        group.add_member("alice")
        group.send_message("alice", "test")
        archive = group.dissolve("alice")
        assert archive.group_id == "g005"

    def test_dissolve_makes_group_inactive(self):
        group = DiscussionGroup(group_id="g006")
        group.add_member("alice")
        group.send_message("alice", "test")
        assert not group.is_dissolved()
        group.dissolve("alice")
        assert group.is_dissolved()

    def test_dissolve_notification_to_all_members_includes_admin(self):
        group = DiscussionGroup(group_id="g007")
        group.add_member("alice")
        group.add_member("bob")
        group.dissolve("alice")
        assert group.notification_service.has_user_received("alice", f"DISSOLVE:g007")
        assert group.notification_service.has_user_received("bob", f"DISSOLVE:g007")

    def test_archive_contains_timestamp(self):
        group = DiscussionGroup(group_id="g008")
        group.add_member("alice")
        group.send_message("alice", "test")
        archive = group.dissolve("alice")
        assert archive.archived_at is not None
        assert isinstance(archive.archived_at, datetime)
