#!/usr/bin/env python3
"""
TDD 测试：群组资源释放
验收标准：
  1. 资源释放执行时间 ≤10 秒
  2. 对其他群组的正常运行零影响
  3. WebSocket连接、消息队列、缓存数据均被清理
"""

from __future__ import annotations

import pytest
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# 模拟资源类
# ---------------------------------------------------------------------------

@dataclass
class WebSocketConnection:
    """模拟 WebSocket 连接"""
    conn_id: str
    agent_id: str
    group_id: str
    connected: bool = True
    closed_at: Optional[datetime] = None

    def close(self):
        self.connected = False
        self.closed_at = datetime.now(timezone.utc)

    @property
    def is_active(self) -> bool:
        return self.connected


@dataclass
class QueueMessage:
    """模拟消息队列中的消息"""
    msg_id: int
    sender: str
    content: str
    group_id: str
    timestamp: datetime


@dataclass
class CacheEntry:
    """模拟缓存数据"""
    key: str
    value: str
    group_id: str
    created_at: datetime
    ttl_seconds: int = 3600


# ---------------------------------------------------------------------------
# 资源持有者（群组的内部资源）
# ---------------------------------------------------------------------------

class GroupResources:
    """群组的资源集合"""

    def __init__(self, group_id: str):
        self.group_id = group_id
        self.websocket_connections: dict[str, WebSocketConnection] = {}
        self.message_queue: List[QueueMessage] = []
        self.cache_entries: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def add_websocket(self, conn: WebSocketConnection):
        with self._lock:
            self.websocket_connections[conn.conn_id] = conn

    def add_queue_message(self, msg: QueueMessage):
        with self._lock:
            self.message_queue.append(msg)

    def add_cache_entry(self, entry: CacheEntry):
        with self._lock:
            self.cache_entries[entry.key] = entry

    def release_all(self) -> dict:
        """释放所有资源，返回释放统计"""
        with self._lock:
            ws_count = len(self.websocket_connections)
            queue_count = len(self.message_queue)
            cache_count = len(self.cache_entries)
            for conn in self.websocket_connections.values():
                conn.close()
            self.websocket_connections.clear()
            self.message_queue.clear()
            self.cache_entries.clear()
        return {
            "websocket_connections_closed": ws_count,
            "queue_messages_cleared": queue_count,
            "cache_entries_cleared": cache_count,
        }

    @property
    def websocket_count(self) -> int:
        with self._lock:
            return len(self.websocket_connections)

    @property
    def queue_message_count(self) -> int:
        with self._lock:
            return len(self.message_queue)

    @property
    def cache_entry_count(self) -> int:
        with self._lock:
            return len(self.cache_entries)

    @property
    def all_websockets_closed(self) -> bool:
        with self._lock:
            return all(not c.is_active for c in self.websocket_connections.values()) if self.websocket_connections else True

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return (
                len(self.websocket_connections) == 0
                and len(self.message_queue) == 0
                and len(self.cache_entries) == 0
            )


# ---------------------------------------------------------------------------
# 群组
# ---------------------------------------------------------------------------

@dataclass
class Member:
    agent_id: str
    name: str
    role: str = "member"


class DiscussionGroup:
    def __init__(self, group_id: str, name: str):
        self.group_id = group_id
        self.name = name
        self.members: dict[str, Member] = {}
        self._lock = threading.Lock()
        self._resources = GroupResources(group_id)
        self._disbanded = False
        self._disband_time: Optional[datetime] = None

    def add_member(self, member: Member):
        with self._lock:
            self.members[member.agent_id] = member

    def add_websocket(self, agent_id: str, conn_id: Optional[str] = None) -> WebSocketConnection:
        if agent_id not in self.members:
            raise ValueError(f"连接者 {agent_id} 不是本群成员")
        cid = conn_id or f"ws-{self.group_id}-{agent_id}"
        conn = WebSocketConnection(conn_id=cid, agent_id=agent_id, group_id=self.group_id)
        self._resources.add_websocket(conn)
        return conn

    def enqueue_message(self, sender: str, content: str, msg_id: Optional[int] = None) -> QueueMessage:
        if sender not in self.members:
            raise ValueError(f"发送者 {sender} 不是本群成员")
        mid = msg_id or (self._resources.queue_message_count + 1)
        msg = QueueMessage(
            msg_id=mid,
            sender=sender,
            content=content,
            group_id=self.group_id,
            timestamp=datetime.now(timezone.utc),
        )
        self._resources.add_queue_message(msg)
        return msg

    def set_cache(self, key: str, value: str, ttl_seconds: int = 3600) -> CacheEntry:
        entry = CacheEntry(
            key=f"{self.group_id}:{key}",
            value=value,
            group_id=self.group_id,
            created_at=datetime.now(timezone.utc),
            ttl_seconds=ttl_seconds,
        )
        self._resources.add_cache_entry(entry)
        return entry

    def get_cache(self, key: str) -> Optional[CacheEntry]:
        full_key = f"{self.group_id}:{key}"
        return self._resources.cache_entries.get(full_key)

    @property
    def is_disbanded(self) -> bool:
        return self._disbanded

    def disband(self, admin_id: str) -> dict:
        start = time.monotonic()
        if admin_id not in self.members:
            raise ValueError(f"发起者 {admin_id} 不是本群成员")
        if self.members[admin_id].role != "admin":
            raise ValueError("只有管理员可以解散群组")
        if self._disbanded:
            raise ValueError("群组已经解散")
        with self._lock:
            self._disbanded = True
            self._disband_time = datetime.now(timezone.utc)
        stats = self._resources.release_all()
        elapsed = time.monotonic() - start
        stats["elapsed_seconds"] = elapsed
        return stats

    # 查询属性
    @property
    def websocket_count(self) -> int:
        return self._resources.websocket_count

    @property
    def queue_message_count(self) -> int:
        return self._resources.queue_message_count

    @property
    def cache_entry_count(self) -> int:
        return self._resources.cache_entry_count

    @property
    def resources_empty(self) -> bool:
        return self._resources.is_empty


# ---------------------------------------------------------------------------
# 群组管理器（管理多个群组）
# ---------------------------------------------------------------------------

class GroupManager:
    def __init__(self):
        self._groups: dict[str, DiscussionGroup] = {}
        self._lock = threading.Lock()

    def create_group(self, group_id: str, name: str, admin: Member) -> DiscussionGroup:
        g = DiscussionGroup(group_id, name)
        g.add_member(admin)
        with self._lock:
            self._groups[group_id] = g
        return g

    def get_group(self, group_id: str) -> Optional[DiscussionGroup]:
        with self._lock:
            return self._groups.get(group_id)

    def disband_group(self, group_id: str, admin_id: str) -> dict:
        with self._lock:
            group = self._groups.get(group_id)
        if group is None:
            raise ValueError(f"群组 {group_id} 不存在")
        return group.disband(admin_id)

    @property
    def active_group_count(self) -> int:
        with self._lock:
            return len(self._groups)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def group_manager():
    return GroupManager()


@pytest.fixture
def group_with_resources(group_manager):
    admin = Member("agent_admin", "Admin", role="admin")
    g = group_manager.create_group("g001", "项目讨论群", admin)
    g.add_member(Member("agent_alice", "Alice"))
    g.add_member(Member("agent_bob", "Bob"))

    # 添加 WebSocket 连接
    g.add_websocket("agent_admin")
    g.add_websocket("agent_alice")
    g.add_websocket("agent_bob")

    # 添加消息队列消息
    g.enqueue_message("agent_alice", "你好大家好")
    g.enqueue_message("agent_bob", "收到")

    # 添加缓存数据
    g.set_cache("topic", "项目进展讨论")
    g.set_cache("status", "进行中")
    g.set_cache("config", '{"timeout": 30}')

    return g


@pytest.fixture
def two_groups(group_manager):
    admin1 = Member("admin1", "Admin1", role="admin")
    admin2 = Member("admin2", "Admin2", role="admin")
    g1 = group_manager.create_group("g001", "群组一", admin1)
    g1.add_member(Member("alice", "Alice"))
    g1.add_websocket("admin1")
    g1.add_websocket("alice")
    g1.enqueue_message("alice", "群组一的消息")
    g1.set_cache("g1_key", "群组一的缓存")

    g2 = group_manager.create_group("g002", "群组二", admin2)
    g2.add_member(Member("bob", "Bob"))
    g2.add_websocket("admin2")
    g2.add_websocket("bob")
    g2.enqueue_message("bob", "群组二的消息")
    g2.set_cache("g2_key", "群组二的缓存")

    return g1, g2


@pytest.fixture
def large_group_resources(group_manager):
    """大量资源的群组，用于压力测试"""
    admin = Member("admin_large", "Admin", role="admin")
    g = group_manager.create_group("g_large", "大型群组", admin)
    num_members = 200
    for i in range(num_members):
        g.add_member(Member(f"agent_{i}", f"Agent{i}"))
        g.add_websocket(f"agent_{i}")

    num_messages = 5000
    for i in range(num_messages):
        sender = f"agent_{i % num_members}"
        g.enqueue_message(sender, f"消息{i}")

    num_caches = 1000
    for i in range(num_caches):
        g.set_cache(f"cache_{i}", f"value_{i}")

    return g


# ---------------------------------------------------------------------------
# 测试：资源释放执行时间 ≤10 秒
# ---------------------------------------------------------------------------

class TestResourceReleaseExecutionTime:

    def test_disband_release_time_within_10s_small_group(self, group_with_resources):
        start = time.monotonic()
        result = group_with_resources.disband("agent_admin")
        elapsed = time.monotonic() - start
        assert result["elapsed_seconds"] <= 10.0, f"资源释放耗时 {result['elapsed_seconds']:.3f}s 超过 10s"
        assert elapsed <= 10.0

    def test_disband_release_time_within_10s_large_group(self, large_group_resources):
        """大量资源（200连接 + 5000消息 + 1000缓存）下释放时间仍 ≤10s"""
        start = time.monotonic()
        result = large_group_resources.disband("admin_large")
        elapsed = time.monotonic() - start
        assert result["elapsed_seconds"] <= 10.0, f"资源释放耗时 {result['elapsed_seconds']:.3f}s 超过 10s"
        assert elapsed <= 10.0

    def test_disband_release_time_very_small_group(self, group_manager):
        """最小群组（仅1个admin）释放时间"""
        g = group_manager.create_group("g_min", "最小群", Member("admin", "A", role="admin"))
        start = time.monotonic()
        result = g.disband("admin")
        elapsed = time.monotonic() - start
        assert result["elapsed_seconds"] <= 10.0
        assert elapsed <= 10.0

    def test_disband_report_contains_elapsed(self, group_with_resources):
        result = group_with_resources.disband("agent_admin")
        assert "elapsed_seconds" in result
        assert isinstance(result["elapsed_seconds"], float)
        assert result["elapsed_seconds"] >= 0


# ---------------------------------------------------------------------------
# 测试：WebSocket 连接被清理
# ---------------------------------------------------------------------------

class TestWebSocketConnectionsCleared:

    def test_websockets_closed_after_disband(self, group_with_resources):
        g = group_with_resources
        pre_count = g.websocket_count
        assert pre_count == 3
        g.disband("agent_admin")
        assert g.websocket_count == 0

    def test_each_websocket_connection_is_closed(self, group_with_resources):
        g = group_with_resources
        conns = []
        for aid in ["agent_admin", "agent_alice", "agent_bob"]:
            conn = g.add_websocket(aid, f"ws-dup-{aid}")
            conns.append(conn)
        g.disband("agent_admin")
        for conn in conns:
            assert conn.is_active is False
            assert conn.closed_at is not None

    def test_websocket_count_reported_in_stats(self, group_with_resources):
        result = group_with_resources.disband("agent_admin")
        assert result["websocket_connections_closed"] == 3

    def test_websockets_empty_for_group_with_no_connections(self, group_manager):
        g = group_manager.create_group("g_empty", "空群", Member("admin", "A", role="admin"))
        result = g.disband("admin")
        assert result["websocket_connections_closed"] == 0
        assert g.websocket_count == 0

    def test_websocket_connections_dict_is_cleared(self, group_with_resources):
        g = group_with_resources
        assert len(g._resources.websocket_connections) == 3
        g.disband("agent_admin")
        assert len(g._resources.websocket_connections) == 0


# ---------------------------------------------------------------------------
# 测试：消息队列被清理
# ---------------------------------------------------------------------------

class TestMessageQueueCleared:

    def test_queue_messages_cleared_after_disband(self, group_with_resources):
        g = group_with_resources
        pre_count = g.queue_message_count
        assert pre_count == 2
        g.disband("agent_admin")
        assert g.queue_message_count == 0

    def test_queue_count_reported_in_stats(self, group_with_resources):
        result = group_with_resources.disband("agent_admin")
        assert result["queue_messages_cleared"] == 2

    def test_queue_empty_for_group_with_no_messages(self, group_manager):
        g = group_manager.create_group("g_no_msg", "无消息群", Member("admin", "A", role="admin"))
        result = g.disband("admin")
        assert result["queue_messages_cleared"] == 0
        assert g.queue_message_count == 0

    def test_queue_messages_list_is_cleared(self, group_with_resources):
        g = group_with_resources
        assert len(g._resources.message_queue) == 2
        g.disband("agent_admin")
        assert len(g._resources.message_queue) == 0

    def test_queue_messages_in_large_group_cleared(self, large_group_resources):
        g = large_group_resources
        assert g.queue_message_count == 5000
        result = g.disband("admin_large")
        assert g.queue_message_count == 0
        assert result["queue_messages_cleared"] == 5000


# ---------------------------------------------------------------------------
# 测试：缓存数据被清理
# ---------------------------------------------------------------------------

class TestCacheDataCleared:

    def test_cache_entries_cleared_after_disband(self, group_with_resources):
        g = group_with_resources
        pre_count = g.cache_entry_count
        assert pre_count == 3
        g.disband("agent_admin")
        assert g.cache_entry_count == 0

    def test_cache_count_reported_in_stats(self, group_with_resources):
        result = group_with_resources.disband("agent_admin")
        assert result["cache_entries_cleared"] == 3

    def test_cache_empty_for_group_with_no_cache(self, group_manager):
        g = group_manager.create_group("g_no_cache", "无缓存群", Member("admin", "A", role="admin"))
        result = g.disband("admin")
        assert result["cache_entries_cleared"] == 0
        assert g.cache_entry_count == 0

    def test_cache_dict_is_cleared(self, group_with_resources):
        g = group_with_resources
        assert len(g._resources.cache_entries) == 3
        g.disband("agent_admin")
        assert len(g._resources.cache_entries) == 0

    def test_cache_entries_in_large_group_cleared(self, large_group_resources):
        g = large_group_resources
        assert g.cache_entry_count == 1000
        result = g.disband("admin_large")
        assert g.cache_entry_count == 0
        assert result["cache_entries_cleared"] == 1000

    def test_cache_get_returns_none_after_disband(self, group_with_resources):
        g = group_with_resources
        entry_before = g.get_cache("topic")
        assert entry_before is not None
        g.disband("agent_admin")
        entry_after = g.get_cache("topic")
        assert entry_after is None


# ---------------------------------------------------------------------------
# 测试：对其他群组的正常运行零影响
# ---------------------------------------------------------------------------

class TestNoImpactOnOtherGroups:

    def test_other_group_websockets_unchanged(self, two_groups):
        g1, g2 = two_groups
        g2_ws_before = g2.websocket_count
        g1.disband("admin1")
        assert g2.websocket_count == g2_ws_before

    def test_other_group_queue_messages_unchanged(self, two_groups):
        g1, g2 = two_groups
        g2_queue_before = g2.queue_message_count
        g1.disband("admin1")
        assert g2.queue_message_count == g2_queue_before

    def test_other_group_cache_unchanged(self, two_groups):
        g1, g2 = two_groups
        g2_cache_before = g2.cache_entry_count
        g1.disband("admin1")
        assert g2.cache_entry_count == g2_cache_before

    def test_other_group_can_still_add_websocket(self, two_groups):
        g1, g2 = two_groups
        g1.disband("admin1")
        g2.add_member(Member("new_member", "New"))
        conn = g2.add_websocket("new_member")
        assert conn.is_active is True

    def test_other_group_can_still_enqueue_message(self, two_groups):
        g1, g2 = two_groups
        g1.disband("admin1")
        g2.enqueue_message("admin2", "解散后群二仍可用")
        assert g2.queue_message_count == 2

    def test_other_group_can_still_set_cache(self, two_groups):
        g1, g2 = two_groups
        g1.disband("admin1")
        g2.set_cache("new_cache", "新缓存值")
        entry = g2.get_cache("new_cache")
        assert entry is not None
        assert entry.value == "新缓存值"

    def test_other_group_resources_not_empty(self, two_groups):
        g1, g2 = two_groups
        g1.disband("admin1")
        assert g2.resources_empty is False

    def test_disbanded_group_resources_empty_but_other_not(self, two_groups):
        g1, g2 = two_groups
        g1.disband("admin1")
        assert g1.resources_empty is True
        assert g2.resources_empty is False

    def test_other_group_websocket_connections_still_active(self, two_groups):
        g1, g2 = two_groups
        active_conns = []
        for conn_id in list(g2._resources.websocket_connections.values()):
            active_conns.append(conn_id)
        g1.disband("admin1")
        for conn in active_conns:
            assert conn.is_active is True

    def test_three_groups_disband_one_others_unchanged(self, group_manager):
        g1 = group_manager.create_group("g1", "群1", Member("a1", "A1", role="admin"))
        g1.add_websocket("a1")
        g1.enqueue_message("a1", "m1")
        g1.set_cache("k1", "v1")

        g2 = group_manager.create_group("g2", "群2", Member("a2", "A2", role="admin"))
        g2.add_websocket("a2")
        g2.enqueue_message("a2", "m2")
        g2.set_cache("k2", "v2")

        g3 = group_manager.create_group("g3", "群3", Member("a3", "A3", role="admin"))
        g3.add_websocket("a3")
        g3.enqueue_message("a3", "m3")
        g3.set_cache("k3", "v3")

        g1.disband("a1")

        assert g1.resources_empty is True
        assert g2.resources_empty is False
        assert g3.resources_empty is False
        assert g2.websocket_count == 1
        assert g2.queue_message_count == 1
        assert g2.cache_entry_count == 1
        assert g3.websocket_count == 1
        assert g3.queue_message_count == 1
        assert g3.cache_entry_count == 1

    def test_other_group_member_list_unchanged(self, two_groups):
        g1, g2 = two_groups
        g2_members_before = set(g2.members.keys())
        g1.disband("admin1")
        assert set(g2.members.keys()) == g2_members_before

    def test_other_group_not_marked_disbanded(self, two_groups):
        g1, g2 = two_groups
        assert g2.is_disbanded is False
        g1.disband("admin1")
        assert g2.is_disbanded is False


# ---------------------------------------------------------------------------
# 测试：资源释放统计准确性
# ---------------------------------------------------------------------------

class TestResourceReleaseStats:

    def test_stats_websocket_count_matches(self, group_with_resources):
        result = group_with_resources.disband("agent_admin")
        assert result["websocket_connections_closed"] == 3

    def test_stats_queue_count_matches(self, group_with_resources):
        result = group_with_resources.disband("agent_admin")
        assert result["queue_messages_cleared"] == 2

    def test_stats_cache_count_matches(self, group_with_resources):
        result = group_with_resources.disband("agent_admin")
        assert result["cache_entries_cleared"] == 3

    def test_stats_total_for_large_group(self, large_group_resources):
        result = large_group_resources.disband("admin_large")
        assert result["websocket_connections_closed"] == 200
        assert result["queue_messages_cleared"] == 5000
        assert result["cache_entries_cleared"] == 1000

    def test_stats_for_empty_group(self, group_manager):
        g = group_manager.create_group("g_empty", "空群", Member("admin", "A", role="admin"))
        result = g.disband("admin")
        assert result["websocket_connections_closed"] == 0
        assert result["queue_messages_cleared"] == 0
        assert result["cache_entries_cleared"] == 0


# ---------------------------------------------------------------------------
# 测试：边缘情况
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_disband_nonexistent_group(self, group_manager):
        with pytest.raises(ValueError, match="群组.*不存在"):
            group_manager.disband_group("g_nonexistent", "admin")

    def test_disband_twice_raises(self, group_with_resources):
        group_with_resources.disband("agent_admin")
        with pytest.raises(ValueError, match="群组已经解散"):
            group_with_resources.disband("agent_admin")

    def test_disband_by_non_admin_raises(self, group_with_resources):
        with pytest.raises(ValueError, match="只有管理员可以解散群组"):
            group_with_resources.disband("agent_alice")

    def test_disband_by_non_member_raises(self, group_with_resources):
        with pytest.raises(ValueError, match="不是本群成员"):
            group_with_resources.disband("agent_unknown")

    def test_disband_preserves_disband_time(self, group_with_resources):
        before = datetime.now(timezone.utc)
        group_with_resources.disband("agent_admin")
        after = datetime.now(timezone.utc)
        assert group_with_resources._disband_time is not None
        assert before <= group_with_resources._disband_time <= after

    def test_disband_sets_disbanded_flag(self, group_with_resources):
        assert group_with_resources.is_disbanded is False
        group_with_resources.disband("agent_admin")
        assert group_with_resources.is_disbanded is True

    def test_resources_released_atomically(self, group_with_resources):
        g = group_with_resources
        g.disband("agent_admin")
        assert g.websocket_count == 0
        assert g.queue_message_count == 0
        assert g.cache_entry_count == 0


# ---------------------------------------------------------------------------
# 测试：并发解散（多群组并发操作互不干扰）
# ---------------------------------------------------------------------------

class TestConcurrentDisband:

    def test_concurrent_disband_two_groups(self, group_manager):
        g1 = group_manager.create_group("gc1", "并发群1", Member("ca1", "CA1", role="admin"))
        g2 = group_manager.create_group("gc2", "并发群2", Member("ca2", "CA2", role="admin"))
        for i in range(50):
            aid = f"m{i}"
            g1.add_member(Member(aid, f"Member{i}"))
            g1.add_websocket(aid)
            g1.enqueue_message(aid, f"消息{i}")
            g1.set_cache(f"k{i}", f"v{i}")

            aid2 = f"m2_{i}"
            g2.add_member(Member(aid2, f"Member2_{i}"))
            g2.add_websocket(aid2)
            g2.enqueue_message(aid2, f"消息2_{i}")
            g2.set_cache(f"k2_{i}", f"v2_{i}")

        errors = []

        def disband_g1():
            try:
                g1.disband("ca1")
            except Exception as e:
                errors.append(("g1", e))

        def disband_g2():
            try:
                g2.disband("ca2")
            except Exception as e:
                errors.append(("g2", e))

        t1 = threading.Thread(target=disband_g1)
        t2 = threading.Thread(target=disband_g2)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        assert errors == [], f"并发解散出现错误: {errors}"
        assert g1.resources_empty is True
        assert g2.resources_empty is True
        assert g1.is_disbanded is True
        assert g2.is_disbanded is True

    def test_disband_one_group_while_other_adds_resources(self, group_manager):
        g1 = group_manager.create_group("gc_mix1", "混合群1", Member("cm1", "CM1", role="admin"))
        g2 = group_manager.create_group("gc_mix2", "混合群2", Member("cm2", "CM2", role="admin"))
        g2.add_member(Member("cm2_user", "User"))

        errors = []
        barrier = threading.Barrier(2)

        def disband_g1_and_wait():
            try:
                barrier.wait()
                g1.disband("cm1")
            except Exception as e:
                errors.append(("g1", e))

        def wait_and_add_to_g2():
            try:
                barrier.wait()
                for i in range(100):
                    g2.add_websocket("cm2_user", f"ws-wait-{i}")
                    g2.enqueue_message("cm2_user", f"wait_msg_{i}")
                    g2.set_cache(f"wait_k{i}", f"wait_v{i}")
            except Exception as e:
                errors.append(("g2", e))

        t1 = threading.Thread(target=disband_g1_and_wait)
        t2 = threading.Thread(target=wait_and_add_to_g2)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        assert errors == [], f"并发操作出现错误: {errors}"
        assert g1.resources_empty is True
        assert g1.is_disbanded is True
        assert g2.websocket_count == 100  # 仅并发线程添加的100个连接
        assert g2.queue_message_count == 100
        assert g2.cache_entry_count == 100
        assert g2.is_disbanded is False
