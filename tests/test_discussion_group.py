import pytest
import time
import threading
from datetime import datetime, timedelta, timezone
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


class DiscussionGroup:
    def __init__(self, notification_service: Optional[NotificationService] = None):
        self._messages: list[Message] = []
        self._lock = threading.Lock()
        self._notification_service = notification_service or NotificationService()

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


class TestMessageSendPerformance:
    def test_send_message_response_within_500ms(self):
        group = DiscussionGroup()
        start = time.monotonic()
        group.send_message("alice", "hello everyone")
        elapsed = time.monotonic() - start
        assert elapsed < 0.5

    def test_send_message_returns_message_object(self):
        group = DiscussionGroup()
        msg = group.send_message("alice", "hello everyone")
        assert isinstance(msg, Message)
        assert msg.sender == "alice"
        assert msg.content == "hello everyone"

    def test_send_message_assigns_unique_id(self):
        group = DiscussionGroup()
        m1 = group.send_message("alice", "first")
        m2 = group.send_message("bob", "second")
        assert m1.id != m2.id

    def test_send_message_records_timestamp(self):
        group = DiscussionGroup()
        before = datetime.now(timezone.utc)
        msg = group.send_message("alice", "hello")
        after = datetime.now(timezone.utc)
        assert before <= msg.timestamp <= after


class TestAtMentionNotification:
    def test_mention_notifies_within_3s(self):
        notifier = NotificationService()
        group = DiscussionGroup(notification_service=notifier)
        start = time.monotonic()
        msg = group.send_message("alice", "hey @bob check this")
        notif_time = notifier.get_notification_time("bob", msg.id)
        elapsed = time.monotonic() - start
        assert notif_time is not None
        assert elapsed < 3.0

    def test_mention_notifies_correct_user(self):
        notifier = NotificationService()
        group = DiscussionGroup(notification_service=notifier)
        msg = group.send_message("alice", "@bob @carol hi")
        assert notifier.get_notification_time("bob", msg.id) is not None
        assert notifier.get_notification_time("carol", msg.id) is not None

    def test_no_mention_no_notification(self):
        notifier = NotificationService()
        group = DiscussionGroup(notification_service=notifier)
        msg = group.send_message("alice", "hello everyone")
        assert notifier.get_notification_time("bob", msg.id) is None

    def test_multiple_mentions_in_one_message(self):
        notifier = NotificationService()
        group = DiscussionGroup(notification_service=notifier)
        msg = group.send_message("alice", "@bob @carol @dave all hands")
        for user in ("bob", "carol", "dave"):
            assert notifier.get_notification_time(user, msg.id) is not None


class TestHistoryOrdering:
    def test_history_returns_reverse_chronological(self):
        group = DiscussionGroup()
        group.send_message("alice", "first")
        group.send_message("bob", "second")
        group.send_message("carol", "third")
        history = group.get_history()
        timestamps = [m.timestamp for m in history]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_history_includes_all_messages(self):
        group = DiscussionGroup()
        group.send_message("alice", "a")
        group.send_message("bob", "b")
        group.send_message("carol", "c")
        history = group.get_history()
        assert len(history) == 3

    def test_newest_message_first(self):
        group = DiscussionGroup()
        group.send_message("alice", "old")
        msg2 = group.send_message("bob", "new")
        history = group.get_history()
        assert history[0].id == msg2.id

    def test_history_empty_when_no_messages(self):
        group = DiscussionGroup()
        assert group.get_history() == []


class TestPagination:
    def test_page_one_returns_newest_first(self):
        group = DiscussionGroup()
        for i in range(5):
            group.send_message("user", str(i))
        page = group.get_history(page=1, page_size=3)
        assert len(page) == 3
        assert [m.content for m in page] == ["4", "3", "2"]

    def test_page_two_returns_older_messages(self):
        group = DiscussionGroup()
        for i in range(5):
            group.send_message("user", str(i))
        page = group.get_history(page=2, page_size=3)
        assert len(page) == 2
        assert [m.content for m in page] == ["1", "0"]

    def test_page_exceeding_total_returns_empty(self):
        group = DiscussionGroup()
        group.send_message("user", "only one")
        page = group.get_history(page=100, page_size=10)
        assert page == []

    def test_page_size_controls_count(self):
        group = DiscussionGroup()
        for i in range(20):
            group.send_message("user", str(i))
        small = group.get_history(page=1, page_size=5)
        large = group.get_history(page=1, page_size=15)
        assert len(small) == 5
        assert len(large) == 15

    def test_pagination_returns_all_messages_across_pages(self):
        group = DiscussionGroup()
        for i in range(7):
            group.send_message("user", str(i))
        p1 = group.get_history(page=1, page_size=3)
        p2 = group.get_history(page=2, page_size=3)
        p3 = group.get_history(page=3, page_size=3)
        contents = [m.content for m in p1] + [m.content for m in p2] + [m.content for m in p3]
        assert sorted(contents, key=int) == ["0", "1", "2", "3", "4", "5", "6"]


class TestThreadSafety:
    def test_concurrent_sends_dont_corrupt_history(self):
        group = DiscussionGroup()
        errors = []

        def send(n):
            try:
                for _ in range(n):
                    group.send_message("user", "msg")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=send, args=(50,))
        t2 = threading.Thread(target=send, args=(50,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert not errors
        assert len(group.get_history(page=1, page_size=200)) == 100

    def test_read_during_write(self):
        group = DiscussionGroup()
        group.send_message("alice", "first")

        def writer():
            for i in range(100):
                group.send_message("bob", str(i))

        def reader(results):
            for _ in range(50):
                results.append(len(group.get_history()))

        r1, r2 = [], []
        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader, args=(r1,))
        t3 = threading.Thread(target=reader, args=(r2,))
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()
        total = len(group.get_history(page=1, page_size=200))
        assert total == 101
