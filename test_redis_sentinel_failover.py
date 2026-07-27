#!/usr/bin/env python3
"""
TDD 测试：Redis Sentinel 故障转移
验收标准：
  1. Redis 主节点故障时，Sentinel 自动选举新主节点
  2. 故障转移后未完成任务从 AOF 日志中恢复
"""

import json
import time
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


# ============================================================
# 被测试的业务代码
# ============================================================

class NodeRole(Enum):
    MASTER = "master"
    SLAVE = "slave"
    FAILED = "failed"


class MockAOFLog:
    """模拟 Redis AOF 日志"""

    def __init__(self):
        self._entries: List[Dict] = []

    def append(self, command: str, key: str, value: str):
        entry = {
            "command": command,
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "ack": False,
        }
        self._entries.append(entry)
        return entry

    def acknowledge(self, index: int):
        if 0 <= index < len(self._entries):
            self._entries[index]["ack"] = True

    def get_unfinished_entries(self) -> List[Dict]:
        return [e for e in self._entries if not e["ack"]]

    def get_all_entries(self) -> List[Dict]:
        return list(self._entries)

    def clear(self):
        self._entries.clear()


class MockRedisNode:
    """模拟 Redis 节点"""

    def __init__(self, name: str, host: str, port: int, role: NodeRole = NodeRole.MASTER):
        self.name = name
        self.host = host
        self.port = port
        self.role = role
        self._store: Dict[str, str] = {}
        self._aof = MockAOFLog()
        self._alive = True
        self._failover_time: Optional[datetime] = None

    @property
    def is_alive(self) -> bool:
        return self._alive

    @property
    def aof_log(self) -> MockAOFLog:
        return self._aof

    def simulate_crash(self):
        self._alive = False
        self.role = NodeRole.FAILED

    def recover(self):
        self._alive = True
        self.role = NodeRole.SLAVE
        self._store.clear()

    def set(self, key: str, value: str) -> bool:
        if not self._alive or self.role != NodeRole.MASTER:
            return False
        self._store[key] = value
        self._aof.append("SET", key, value)
        return True

    def get(self, key: str) -> Optional[str]:
        if not self._alive:
            return None
        return self._store.get(key)

    def get_unfinished_tasks(self) -> List[Dict]:
        return self._aof.get_unfinished_entries()

    def replicate_from(self, source: "MockRedisNode"):
        """从源节点复制数据和未完成的AOF条目"""
        # 复制已存储的数据
        self._store.update(source._store)
        # 只复制未确认的AOF条目（未完成任务）
        for entry in source._aof.get_unfinished_entries():
            self._aof.append(entry["command"], entry["key"], entry["value"])

    def acknowledge_aof_entries(self):
        entries = self._aof.get_all_entries()
        for i in range(len(entries)):
            self._aof.acknowledge(i)


class RedisSentinelMonitor:
    """Redis Sentinel 监控器 - 负责故障检测和自动转移"""

    def __init__(self, master_node: MockRedisNode, slave_nodes: List[MockRedisNode],
                 quorum: int = 2, failover_timeout: int = 30):
        self.master = master_node
        self.slaves = list(slave_nodes)  # 使用副本，避免污染原始列表
        self.quorum = quorum
        self.failover_timeout = failover_timeout
        self._current_master: Optional[MockRedisNode] = master_node
        self._failover_history: List[Dict] = []
        self._monitoring = True

    def get_master(self) -> Optional[MockRedisNode]:
        return self._current_master

    def get_slaves(self) -> List[MockRedisNode]:
        return self.slaves

    def check_master_health(self) -> bool:
        """检查主节点健康状态"""
        if not self._monitoring:
            return False
        return self.master.is_alive and self.master.role == NodeRole.MASTER

    def detect_failure(self) -> bool:
        """检测故障，返回是否需要故障转移"""
        if not self.check_master_health():
            return True
        return False

    def elect_new_master(self) -> Optional[MockRedisNode]:
        """选举新主节点"""
        available_slaves = [s for s in self.slaves if s.is_alive and s.role == NodeRole.SLAVE]
        if not available_slaves:
            return None
        # 简单策略：选择第一个可用的从节点
        new_master = available_slaves[0]
        new_master.role = NodeRole.MASTER
        new_master._failover_time = datetime.now()
        self._current_master = new_master
        # 其他从节点保持不变
        self._failover_history.append({
            "old_master": self.master.name,
            "new_master": new_master.name,
            "timestamp": new_master._failover_time.isoformat(),
            "reason": "master_crash",
        })
        return new_master

    def perform_failover(self) -> Dict:
        """执行完整的故障转移流程"""
        result = {
            "success": False,
            "old_master": self.master.name,
            "new_master": None,
            "failed_tasks": [],
            "recovered_tasks": [],
            "timestamp": datetime.now().isoformat(),
        }

        # 步骤1：确认主节点故障
        if not self.detect_failure():
            result["error"] = "master_still_alive"
            return result

        # 步骤2：收集未完成任务
        old_master = self.master
        unfinished = old_master.get_unfinished_tasks()
        result["failed_tasks"] = unfinished

        # 步骤3：选举新主节点
        new_master = self.elect_new_master()
        if not new_master:
            result["error"] = "no_available_slave"
            return result

        result["new_master"] = new_master.name
        # 更新 master 引用，将旧主加入从节点列表
        old_master.role = NodeRole.FAILED
        if old_master not in self.slaves:
            self.slaves.append(old_master)
        self.master = new_master

        # 步骤4：数据复制
        new_master.replicate_from(old_master)

        # 步骤5：从AOF恢复未完成任务
        recovered = new_master.get_unfinished_tasks()
        result["recovered_tasks"] = recovered

        result["success"] = True
        result["recovery_count"] = len(recovered)
        return result

    def get_failover_history(self) -> List[Dict]:
        return list(self._failover_history)


# ============================================================
# 测试用例
# ============================================================

@pytest.fixture
def master_node():
    """创建主节点"""
    return MockRedisNode("master-1", "127.0.0.1", 6379, NodeRole.MASTER)


@pytest.fixture
def slave_nodes():
    """创建从节点列表"""
    return [
        MockRedisNode("slave-1", "127.0.0.1", 6380, NodeRole.SLAVE),
        MockRedisNode("slave-2", "127.0.0.1", 6381, NodeRole.SLAVE),
    ]


@pytest.fixture
def sentinel(master_node, slave_nodes):
    """创建 Sentinel 监控器"""
    return RedisSentinelMonitor(master_node, slave_nodes, quorum=2)


class TestMasterHealthCheck:
    """测试组：主节点健康检查"""

    def test_master_alive_returns_true(self, sentinel, master_node):
        """主节点正常时，健康检查返回 True"""
        assert sentinel.check_master_health() is True

    def test_master_crash_detected(self, sentinel, master_node):
        """主节点崩溃时，健康检查返回 False"""
        master_node.simulate_crash()
        assert sentinel.check_master_health() is False

    def test_failure_detection_triggers_on_crash(self, sentinel, master_node):
        """故障检测在节点崩溃时触发"""
        master_node.simulate_crash()
        assert sentinel.detect_failure() is True

    def test_no_failure_when_master_healthy(self, sentinel, master_node):
        """主节点健康时，不会触发故障检测"""
        assert sentinel.detect_failure() is False


class TestAutomaticFailover:
    """测试组：自动故障转移"""

    def test_failover_success_when_master_crashes(self, sentinel, master_node, slave_nodes):
        """验收标准1：主节点故障时自动选举新主节点"""
        # 模拟主节点崩溃
        master_node.simulate_crash()

        # 执行故障转移
        result = sentinel.perform_failover()

        # 验证故障转移成功
        assert result["success"] is True, f"故障转移失败: {result.get('error', '未知错误')}"
        assert result["new_master"] is not None
        assert result["new_master"] != master_node.name

    def test_new_master_is_elected_from_slaves(self, sentinel, master_node, slave_nodes):
        """新主节点从可用从节点中选举"""
        master_node.simulate_crash()
        result = sentinel.perform_failover()

        new_master = sentinel.get_master()
        assert new_master is not None
        assert new_master.role == NodeRole.MASTER
        assert new_master in slave_nodes

    def test_failover_selects_first_available_slave(self, sentinel, master_node, slave_nodes):
        """故障转移选择第一个可用的从节点"""
        master_node.simulate_crash()
        result = sentinel.perform_failover()

        new_master = sentinel.get_master()
        assert new_master.name == slave_nodes[0].name

    def test_failover_fails_when_no_slaves_available(self, sentinel, master_node, slave_nodes):
        """所有从节点不可用时，故障转移失败"""
        master_node.simulate_crash()
        slave_nodes[0].simulate_crash()
        slave_nodes[1].simulate_crash()

        result = sentinel.perform_failover()

        assert result["success"] is False
        assert result["error"] == "no_available_slave"

    def test_failover_no_action_when_master_alive(self, sentinel, master_node):
        """主节点正常时，不执行故障转移"""
        result = sentinel.perform_failover()
        assert result["success"] is False
        assert result["error"] == "master_still_alive"
        assert sentinel.get_master() == master_node

    def test_failover_history_records_event(self, sentinel, master_node, slave_nodes):
        """故障转移事件被记录到历史"""
        master_node.simulate_crash()
        sentinel.perform_failover()

        history = sentinel.get_failover_history()
        assert len(history) == 1
        record = history[0]
        assert record["old_master"] == master_node.name
        assert record["new_master"] == slave_nodes[0].name
        assert record["reason"] == "master_crash"
        assert "timestamp" in record


class TestAOFRecovery:
    """测试组：AOF日志恢复未完成任务"""

    def test_unfinished_tasks_recorded_in_aof(self, master_node):
        """未确认的任务记录在AOF日志中"""
        master_node.set("task:1", "process_order_1001")
        master_node.set("task:2", "process_order_1002")
        master_node.set("task:3", "process_order_1003")

        unfinished = master_node.get_unfinished_tasks()
        assert len(unfinished) == 3
        assert all(not e["ack"] for e in unfinished)

    def test_aof_recovery_after_failover(self, sentinel, master_node, slave_nodes):
        """验收标准2：故障转移后未完成任务从AOF恢复"""
        # 在主节点上写入数据（模拟未完成任务）
        master_node.set("order:1001", "pending_payment")
        master_node.set("order:1002", "pending_shipping")
        master_node.set("order:1003", "pending_confirm")

        # 模拟主节点崩溃
        master_node.simulate_crash()

        # 执行故障转移
        result = sentinel.perform_failover()

        # 验证未完成任务被恢复
        assert result["success"] is True
        assert len(result["recovered_tasks"]) == 3, f"应恢复3个任务，实际恢复 {len(result['recovered_tasks'])} 个"

        # 验证新主节点上有恢复的数据
        new_master = sentinel.get_master()
        assert new_master.get("order:1001") == "pending_payment"
        assert new_master.get("order:1002") == "pending_shipping"
        assert new_master.get("order:1003") == "pending_confirm"

    def test_committed_data_replicated_to_new_master(self, sentinel, master_node, slave_nodes):
        """已提交的数据在故障转移后复制到新主节点"""
        master_node.set("user:100", "alice_data")
        master_node.set("config:theme", "dark_mode")
        master_node.acknowledge_aof_entries()  # 模拟已提交

        master_node.simulate_crash()
        sentinel.perform_failover()

        new_master = sentinel.get_master()
        assert new_master.get("user:100") == "alice_data"
        assert new_master.get("config:theme") == "dark_mode"

    def test_partial_acknowledge_recovery(self, sentinel, master_node, slave_nodes):
        """部分确认的任务只恢复未确认的部分"""
        master_node.set("task:a", "job_1")
        master_node.set("task:b", "job_2")
        master_node.set("task:c", "job_3")
        # 只确认前两个
        master_node.aof_log.acknowledge(0)
        master_node.aof_log.acknowledge(1)

        master_node.simulate_crash()
        result = sentinel.perform_failover()

        # 只恢复未确认的 task:c
        assert len(result["recovered_tasks"]) == 1
        assert result["recovered_tasks"][0]["key"] == "task:c"

    def test_empty_aof_no_recovery_needed(self, sentinel, master_node, slave_nodes):
        """AOF为空时，无需恢复"""
        master_node.simulate_crash()
        result = sentinel.perform_failover()

        assert result["success"] is True
        assert len(result["recovered_tasks"]) == 0
        assert len(result["failed_tasks"]) == 0


class TestFailoverPerformance:
    """测试组：故障转移性能"""

    def test_failover_completes_within_5_seconds(self, sentinel, master_node, slave_nodes):
        """故障转移操作在5秒内完成"""
        # 准备一些数据
        for i in range(50):
            master_node.set(f"item:{i}", f"value_{i}")

        master_node.simulate_crash()

        start = time.time()
        result = sentinel.perform_failover()
        elapsed = time.time() - start

        assert result["success"] is True
        assert elapsed <= 5.0, f"故障转移耗时 {elapsed:.4f} 秒，超过 5 秒限制"

    def test_failover_with_large_aof_completes_in_time(self, sentinel, master_node, slave_nodes):
        """大量AOF条目时故障转移仍在时限内"""
        for i in range(200):
            master_node.set(f"bulk:item:{i}", f"bulk_value_{i}")

        master_node.simulate_crash()

        start = time.time()
        result = sentinel.perform_failover()
        elapsed = time.time() - start

        assert result["success"] is True
        assert len(result["recovered_tasks"]) == 200
        assert elapsed <= 5.0, f"故障转移耗时 {elapsed:.4f} 秒，超过 5 秒限制"


class TestFailoverDataIntegrity:
    """测试组：故障转移数据完整性"""

    def test_all_master_data_available_on_new_master(self, sentinel, master_node, slave_nodes):
        """故障转移后新主节点包含原主节点所有数据"""
        test_data = {
            f"key:{i}": f"value_{i}" for i in range(10)
        }
        for k, v in test_data.items():
            master_node.set(k, v)

        master_node.simulate_crash()
        sentinel.perform_failover()

        new_master = sentinel.get_master()
        for k, v in test_data.items():
            assert new_master.get(k) == v, f"数据不一致: {k} = {new_master.get(k)}, 期望 {v}"

    def test_new_master_accepts_write_after_failover(self, sentinel, master_node, slave_nodes):
        """故障转移后新主节点可接受写入"""
        master_node.set("existing", "old_value")
        master_node.simulate_crash()
        sentinel.perform_failover()

        new_master = sentinel.get_master()
        result = new_master.set("new_key", "new_value")

        assert result is True
        assert new_master.get("new_key") == "new_value"
        assert new_master.get("existing") == "old_value"

    def test_old_master_becomes_slave_after_recovery(self, sentinel, master_node, slave_nodes):
        """原主节点恢复后成为从节点"""
        master_node.simulate_crash()
        sentinel.perform_failover()

        # 原主节点恢复
        master_node.recover()

        assert master_node.role == NodeRole.SLAVE
        assert master_node.is_alive is True
        assert not master_node.set("test", "value")  # 从节点不应接受写入


class TestMultipleFailovers:
    """测试组：多次故障转移"""

    def test_second_failover_works_after_first(self, master_node, slave_nodes):
        """第一次故障转移后，第二次故障转移仍能正常工作"""
        sentinel = RedisSentinelMonitor(master_node, slave_nodes, quorum=2)

        # 第一次故障转移
        master_node.simulate_crash()
        result1 = sentinel.perform_failover()
        assert result1["success"] is True
        first_new_master = sentinel.get_master()

        # 新主节点也崩溃
        first_new_master.simulate_crash()
        result2 = sentinel.perform_failover()

        assert result2["success"] is True
        assert result2["new_master"] == slave_nodes[1].name

    def test_failover_history_tracks_multiple_events(self, master_node, slave_nodes):
        """故障转移历史跟踪多次事件"""
        sentinel = RedisSentinelMonitor(master_node, slave_nodes, quorum=2)

        master_node.simulate_crash()
        sentinel.perform_failover()
        new_master_1 = sentinel.get_master()

        new_master_1.simulate_crash()
        sentinel.perform_failover()

        history = sentinel.get_failover_history()
        assert len(history) == 2
        assert history[0]["old_master"] == master_node.name
        assert history[1]["old_master"] == new_master_1.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
