import pytest
import time
import threading
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict
from uuid import uuid4


@dataclass
class GroupMessage:
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    sender: str = ""
    role: str = "user"
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GroupState:
    """Snapshot of a group at a point in time (archive entry)."""
    group_id: str
    name: str
    description: str
    members: list
    messages: list
    archived_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ArchiveRecord:
    """Represents a stored archive entry for a group."""

    def __init__(self, group_id: str, state: GroupState):
        self.archive_id = uuid4().hex[:12]
        self.group_id = group_id
        self.state = state
        self.created_at = datetime.now(timezone.utc)
        self.message_count = len(state.messages)

    def to_dict(self) -> dict:
        return {
            "archive_id": self.archive_id,
            "group_id": self.group_id,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat(),
            "state": {
                "name": self.state.name,
                "description": self.state.description,
                "members": list(self.state.members),
                "message_count": len(self.state.messages),
            },
        }


class GroupArchiveManager:
    """Manages group archival and restore operations."""

    def __init__(self):
        self._archives: dict[str, ArchiveRecord] = {}
        self._lock = threading.Lock()

    def archive_group(self, group_id: str, name: str, description: str,
                      members: list, messages: list) -> ArchiveRecord:
        """Create an archive snapshot of the group's current state."""
        state = GroupState(
            group_id=group_id,
            name=name,
            description=description,
            members=list(members),
            messages=list(messages),
        )
        record = ArchiveRecord(group_id=group_id, state=state)
        with self._lock:
            self._archives[record.archive_id] = record
        return record

    def get_archive(self, archive_id: str) -> Optional[ArchiveRecord]:
        """Retrieve an archive record by ID."""
        with self._lock:
            return self._archives.get(archive_id)

    def restore_group(self, archive_id: str) -> Optional[dict]:
        """Restore a group from archive. Returns the restored group state."""
        with self._lock:
            record = self._archives.get(archive_id)
        if record is None:
            return None
        state = record.state
        return {
            "id": state.group_id,
            "name": state.name,
            "description": state.description,
            "members": list(state.members),
            "messages": [asdict(m) for m in state.messages],
            "restored_from": archive_id,
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }

    def list_archives(self, group_id: Optional[str] = None) -> list:
        """List all archives, optionally filtered by group_id."""
        with self._lock:
            results = list(self._archives.values())
        if group_id:
            results = [r for r in results if r.group_id == group_id]
        return sorted(results, key=lambda r: r.created_at, reverse=True)

    def archive_count(self) -> int:
        with self._lock:
            return len(self._archives)


def _make_messages(count: int, group_id: str = "g1") -> list:
    """Helper to generate a list of GroupMessage objects."""
    msgs = []
    for i in range(count):
        msgs.append(GroupMessage(
            sender="alice" if i % 2 == 0 else "bob",
            role="user",
            content=f"test message number {i}",
        ))
    return msgs


class TestGroupArchiveCreation:
    """Verify group archives can be created and metadata is correct."""

    def test_archive_creates_snapshot(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(5)
        record = manager.archive_group(
            group_id="g1",
            name="test-group",
            description="a test group",
            members=["alice", "bob"],
            messages=msgs,
        )
        assert record is not None
        assert record.group_id == "g1"
        assert record.message_count == 5

    def test_archive_assigns_unique_id(self):
        manager = GroupArchiveManager()
        r1 = manager.archive_group("g1", "g1", "", ["alice"], [])
        r2 = manager.archive_group("g2", "g2", "", ["bob"], [])
        assert r1.archive_id != r2.archive_id

    def test_archive_records_message_count(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(10)
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        assert record.message_count == 10

    def test_archive_records_member_list(self):
        manager = GroupArchiveManager()
        members = ["alice", "bob", "carol"]
        record = manager.archive_group("g1", "g", "", members, [])
        assert record.state.members == ["alice", "bob", "carol"]

    def test_archive_to_dict_includes_all_fields(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(3)
        record = manager.archive_group("g1", "name", "desc", ["a", "b"], msgs)
        d = record.to_dict()
        assert d["archive_id"] == record.archive_id
        assert d["group_id"] == "g1"
        assert d["message_count"] == 3
        assert d["state"]["members"] == ["a", "b"]
        assert "created_at" in d
        assert "state" in d

    def test_list_archives_newest_first(self):
        manager = GroupArchiveManager()
        r1 = manager.archive_group("g1", "g1", "", ["a"], [])
        r2 = manager.archive_group("g1", "g1", "", ["a"], [])
        archives = manager.list_archives()
        assert archives[0].archive_id == r2.archive_id
        assert archives[1].archive_id == r1.archive_id

    def test_list_archives_filter_by_group(self):
        manager = GroupArchiveManager()
        manager.archive_group("g1", "g1", "", ["a"], [])
        manager.archive_group("g2", "g2", "", ["b"], [])
        manager.archive_group("g1", "g1", "", ["c"], [])
        g1_archives = manager.list_archives(group_id="g1")
        assert len(g1_archives) == 2
        for a in g1_archives:
            assert a.group_id == "g1"

    def test_archive_multiple_times_isolation(self):
        manager = GroupArchiveManager()
        msgs1 = _make_messages(3)
        msgs2 = _make_messages(5)
        r1 = manager.archive_group("g1", "g1", "", ["alice"], msgs1)
        r2 = manager.archive_group("g1", "g1", "", ["alice", "bob"], msgs2)
        assert r1.message_count == 3
        assert r2.message_count == 5
        assert r1.state.members == ["alice"]
        assert r2.state.members == ["alice", "bob"]


class TestGroupRestore:
    """Verify groups can be restored from archives with full fidelity."""

    def test_restore_returns_group_state(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(5)
        record = manager.archive_group("g1", "test-group", "desc",
                                        ["alice", "bob"], msgs)
        restored = manager.restore_group(record.archive_id)
        assert restored is not None
        assert restored["id"] == "g1"
        assert restored["name"] == "test-group"
        assert restored["description"] == "desc"

    def test_restore_preserves_members(self):
        manager = GroupArchiveManager()
        members = ["alice", "bob", "carol"]
        record = manager.archive_group("g1", "g", "", members, [])
        restored = manager.restore_group(record.archive_id)
        assert restored["members"] == ["alice", "bob", "carol"]

    def test_restore_preserves_all_messages(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(10)
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        restored = manager.restore_group(record.archive_id)
        assert len(restored["messages"]) == 10
        restored_contents = [m["content"] for m in restored["messages"]]
        for i in range(10):
            assert f"test message number {i}" in restored_contents

    def test_restore_marks_restored_from(self):
        manager = GroupArchiveManager()
        record = manager.archive_group("g1", "g", "", ["a"], [])
        restored = manager.restore_group(record.archive_id)
        assert restored["restored_from"] == record.archive_id

    def test_restore_marks_restored_at_timestamp(self):
        manager = GroupArchiveManager()
        record = manager.archive_group("g1", "g", "", ["a"], [])
        before = datetime.now(timezone.utc)
        restored = manager.restore_group(record.archive_id)
        after = datetime.now(timezone.utc)
        restored_at = datetime.fromisoformat(restored["restored_at"])
        assert before <= restored_at <= after

    def test_restore_nonexistent_archive_returns_none(self):
        manager = GroupArchiveManager()
        result = manager.restore_group("nonexistent-archive-id")
        assert result is None

    def test_restore_messages_order_is_original(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(5)
        original_ids = [m.id for m in msgs]
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        restored = manager.restore_group(record.archive_id)
        restored_ids = [m["id"] for m in restored["messages"]]
        assert restored_ids == original_ids

    def test_restore_message_role_preserved(self):
        manager = GroupArchiveManager()
        msg = GroupMessage(sender="haimei", role="assistant", content="hello")
        record = manager.archive_group("g1", "g", "", ["alice"], [msg])
        restored = manager.restore_group(record.archive_id)
        assert restored["messages"][0]["role"] == "assistant"
        assert restored["messages"][0]["sender"] == "haimei"

    def test_restore_twice_from_same_archive(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(3)
        record = manager.archive_group("g1", "g", "", ["a", "b"], msgs)
        r1 = manager.restore_group(record.archive_id)
        r2 = manager.restore_group(record.archive_id)
        assert r1 is not None
        assert r2 is not None
        assert len(r1["messages"]) == 3
        assert len(r2["messages"]) == 3
        assert r1["members"] == r2["members"]

    def test_restore_latest_archive_version(self):
        manager = GroupArchiveManager()
        msgs_v1 = _make_messages(2)
        msgs_v2 = _make_messages(7)
        r1 = manager.archive_group("g1", "g1", "", ["alice"], msgs_v1)
        r2 = manager.archive_group("g1", "g1", "", ["alice", "bob"], msgs_v2)
        restored = manager.restore_group(r2.archive_id)
        assert len(restored["messages"]) == 7
        assert restored["members"] == ["alice", "bob"]

    def test_restore_from_first_archive_after_multiple_archives(self):
        manager = GroupArchiveManager()
        msgs_v1 = _make_messages(2)
        msgs_v2 = _make_messages(5)
        r1 = manager.archive_group("g1", "g1", "", ["alice"], msgs_v1)
        manager.archive_group("g1", "g1", "", ["alice", "bob"], msgs_v2)
        restored = manager.restore_group(r1.archive_id)
        assert len(restored["messages"]) == 2
        assert restored["members"] == ["alice"]


class TestArchiveRestorePerformance:
    """Verify restore performance meets time bounds."""

    def test_restore_under_10k_messages_within_30s(self):
        manager = GroupArchiveManager()
        count = 5000
        msgs = _make_messages(count)
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        start = time.monotonic()
        restored = manager.restore_group(record.archive_id)
        elapsed = time.monotonic() - start
        assert restored is not None
        assert len(restored["messages"]) == count
        assert elapsed < 30.0, (
            f"Restore {count} messages took {elapsed:.3f}s, expected <30s"
        )

    def test_restore_under_100k_messages_within_30s(self):
        manager = GroupArchiveManager()
        count = 100000
        msgs = _make_messages(count)
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        start = time.monotonic()
        restored = manager.restore_group(record.archive_id)
        elapsed = time.monotonic() - start
        assert restored is not None
        assert len(restored["messages"]) == count
        assert elapsed < 30.0, (
            f"Restore {count} messages took {elapsed:.3f}s, expected <30s"
        )

    def test_restore_under_1M_messages_within_2min(self):
        manager = GroupArchiveManager()
        count = 500000
        msgs = _make_messages(count)
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        start = time.monotonic()
        restored = manager.restore_group(record.archive_id)
        elapsed = time.monotonic() - start
        assert restored is not None
        assert len(restored["messages"]) == count
        assert elapsed < 120.0, (
            f"Restore {count} messages took {elapsed:.3f}s, expected <120s"
        )

    def test_restore_empty_archive_is_instant(self):
        manager = GroupArchiveManager()
        record = manager.archive_group("g1", "g", "", ["alice"], [])
        start = time.monotonic()
        restored = manager.restore_group(record.archive_id)
        elapsed = time.monotonic() - start
        assert restored is not None
        assert len(restored["messages"]) == 0
        assert elapsed < 1.0

    def test_restore_10000_messages_under_5s_fast_path(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(10000)
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        start = time.monotonic()
        manager.restore_group(record.archive_id)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, (
            f"Restore 10000 messages took {elapsed:.3f}s, expected <5s"
        )


class TestArchiveIsolation:
    """Verify archives are isolated and do not interfere with each other."""

    def test_archives_between_different_groups_independent(self):
        manager = GroupArchiveManager()
        msgs_a = _make_messages(3, "g1")
        msgs_b = _make_messages(7, "g2")
        ra = manager.archive_group("g1", "g1", "", ["alice"], msgs_a)
        rb = manager.archive_group("g2", "g2", "", ["bob"], msgs_b)
        restored_a = manager.restore_group(ra.archive_id)
        restored_b = manager.restore_group(rb.archive_id)
        assert len(restored_a["messages"]) == 3
        assert restored_a["members"] == ["alice"]
        assert len(restored_b["messages"]) == 7
        assert restored_b["members"] == ["bob"]

    def test_archiving_does_not_mutate_original_messages(self):
        manager = GroupArchiveManager()
        original_msgs = _make_messages(5)
        msgs_copy = list(original_msgs)
        record = manager.archive_group("g1", "g", "", ["alice"], original_msgs)
        original_msgs.append(GroupMessage(sender="eve", role="user", content="extra"))
        restored = manager.restore_group(record.archive_id)
        assert len(restored["messages"]) == 5
        assert len(original_msgs) == 6

    def test_restore_does_not_delete_archive(self):
        manager = GroupArchiveManager()
        record = manager.archive_group("g1", "g", "", ["alice"], [])
        manager.restore_group(record.archive_id)
        assert manager.get_archive(record.archive_id) is not None

    def test_concurrent_archives_dont_interfere(self):
        manager = GroupArchiveManager()
        results = []
        errors = []

        def archive_worker(gid: str, count: int):
            try:
                msgs = _make_messages(count, gid)
                rec = manager.archive_group(gid, gid, "", ["user"], msgs)
                results.append((gid, rec.archive_id, count))
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=archive_worker, args=("g1", 100)),
            threading.Thread(target=archive_worker, args=("g2", 200)),
            threading.Thread(target=archive_worker, args=("g3", 300)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(results) == 3
        assert manager.archive_count() == 3

    def test_concurrent_restores_same_archive(self):
        manager = GroupArchiveManager()
        msgs = _make_messages(50)
        record = manager.archive_group("g1", "g", "", ["alice"], msgs)
        restores = []
        errors = []

        def restorer():
            try:
                r = manager.restore_group(record.archive_id)
                restores.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=restorer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(restores) == 5
        for r in restores:
            assert len(r["messages"]) == 50
            assert r["members"] == ["alice"]


class TestArchiveEdgeCases:
    """Edge cases around archive and restore behavior."""

    def test_archive_with_no_members(self):
        manager = GroupArchiveManager()
        record = manager.archive_group("g1", "g", "", [], [])
        assert record.state.members == []

    def test_restore_empty_members(self):
        manager = GroupArchiveManager()
        record = manager.archive_group("g1", "g", "", [], [])
        restored = manager.restore_group(record.archive_id)
        assert restored["members"] == []

    def test_archive_with_long_description(self):
        manager = GroupArchiveManager()
        desc = "x" * 10000
        record = manager.archive_group("g1", "g", desc, ["alice"], [])
        restored = manager.restore_group(record.archive_id)
        assert restored["description"] == desc

    def test_archive_with_many_members(self):
        manager = GroupArchiveManager()
        members = [f"user{i}" for i in range(100)]
        record = manager.archive_group("g1", "g", "", members, [])
        restored = manager.restore_group(record.archive_id)
        assert len(restored["members"]) == 100

    def test_get_archive_returns_none_for_missing(self):
        manager = GroupArchiveManager()
        assert manager.get_archive("does-not-exist") is None

    def test_list_archives_empty_initially(self):
        manager = GroupArchiveManager()
        assert manager.list_archives() == []
        assert manager.archive_count() == 0
