"""PostgreSQL Patroni 高可用 — TDD 测试套件

验证场景：
  1. 主库故障后 < 30 秒内自动切换到从库
  2. 原主库恢复后以从库身份重新加入集群
"""

import json
import time
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Mock 类
# =============================================================================

class MockPatroniMember:
    """模拟 Patroni 集群成员"""

    def __init__(self, name: str, role: str = "replica",
                 address: str = "localhost", port: int = 5432,
                 healthy: bool = True, lsn: int = 1000):
        self.name = name
        self._role = role
        self.address = address
        self.port = port
        self._healthy = healthy
        self.lsn = lsn

    @property
    def role(self) -> str:
        return self._role

    @property
    def state(self) -> str:
        if not self._healthy:
            return "stopped"
        return self._role

    @property
    def healthy(self) -> bool:
        return self._healthy

    def set_role(self, role: str):
        self._role = role

    def set_healthy(self, healthy: bool):
        self._healthy = healthy

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self._role,
            "state": self.state,
            "address": f"{self.address}:{self.port}",
            "healthy": self._healthy,
        }


class MockDcs:
    """模拟 Patroni 的 DCS（etcd / ZooKeeper / Consul）"""

    def __init__(self, members: list):
        self._members = {m.name: m for m in members}
        self._leader_key = None
        self._failover_history: list = []

    @property
    def members(self) -> list:
        return list(self._members.values())

    @property
    def leader(self):
        if self._leader_key and self._leader_key in self._members:
            return self._members[self._leader_key]
        return None

    def set_leader(self, name: str):
        self._leader_key = name

    def remove_leader(self):
        self._leader_key = None

    def get_member(self, name: str):
        return self._members.get(name)

    def record_failover(self, from_member: str, to_member: str, elapsed: float):
        self._failover_history.append({
            "from": from_member,
            "to": to_member,
            "elapsed": elapsed,
        })

    @property
    def failover_history(self) -> list:
        return self._failover_history


class MockPostgreSQL:
    """模拟 PostgreSQL 实例"""

    def __init__(self, is_primary: bool = False):
        self._is_primary = is_primary
        self._running = True
        self._wal_position = 1000

    @property
    def is_primary(self) -> bool:
        return self._is_primary

    @property
    def running(self) -> bool:
        return self._running

    def promote(self):
        """提升为 Primary"""
        self._is_primary = True
        self._wal_position += 100

    def stop(self):
        self._running = False

    def start(self):
        self._running = True
        self._is_primary = False
        self._wal_position = 0  # 恢复后作为从库，wal 从 0 开始

    def sync_from(self, primary_wal: int):
        """模拟流式复制，同步到 primary 的 WAL 位置"""
        self._wal_position = primary_wal

    @property
    def wal_position(self) -> int:
        return self._wal_position


class MockTaskRunner:
    """模拟 Patroni 后台任务"""

    def __init__(self):
        self._tasks: list = []

    def run(self, task_name: str, callback, on_success=None, on_error=None):
        """提交后台任务"""
        task = {
            "name": task_name,
            "callback": callback,
            "on_success": on_success,
            "on_error": on_error,
            "status": "pending",
        }
        self._tasks.append(task)
        return task

    def execute_pending(self):
        """执行所有挂起的任务"""
        results = []
        for task in self._tasks:
            if task["status"] == "pending":
                try:
                    result = task["callback"]()
                    task["status"] = "success"
                    if task["on_success"]:
                        task["on_success"]()
                    results.append(result)
                except Exception as e:
                    task["status"] = "failed"
                    if task["on_error"]:
                        task["on_error"](e)
        return results

    @property
    def completed_tasks(self) -> list:
        return [t for t in self._tasks if t["status"] == "success"]

    @property
    def failed_tasks(self) -> list:
        return [t for t in self._tasks if t["status"] == "failed"]


# =============================================================================
# 被测核心类
# =============================================================================

class PatroniFailoverController:
    """Patroni 故障转移控制器

    职责：
      1. 定期健康检查
      2. 检测主库故障
      3. 选举新的主库（从 LSN 最高的从库中选出）
      4. 记录故障转移耗时
      5. 处理原主库重新加入
    """

    FAILOVER_TIMEOUT = 30.0  # 最大允许的故障转移时间（秒）

    def __init__(self, dcs: MockDcs, local_pg: MockPostgreSQL,
                 local_member: MockPatroniMember,
                 task_runner: MockTaskRunner = None):
        self.dcs = dcs
        self.local_pg = local_pg
        self.local_member = local_member
        self.task_runner = task_runner or MockTaskRunner()
        self._cluster_cache: list = []
        self._last_leader: str = None

    def reload_cluster(self):
        """重新加载集群成员状态"""
        self._cluster_cache = list(self.dcs.members)
        leader = self.dcs.leader
        if leader:
            self._last_leader = leader.name

    def get_cluster_status(self) -> dict:
        """获取集群状态摘要"""
        return {
            "leader": self.dcs.leader.name if self.dcs.leader else None,
            "members": [m.to_dict() for m in self._cluster_cache],
            "member_count": len(self._cluster_cache),
        }

    def check_leader_health(self) -> bool:
        """检查 Leader 是否健康

        Returns:
            True 如果 Leader 健康且可达，False 否则
        """
        leader = self.dcs.leader
        if leader is None:
            return False
        return leader.healthy and leader.state != "stopped"

    def detect_leader_failure(self) -> bool:
        """检测 Leader 是否故障

        Returns:
            True 如果检测到 Leader 故障
        """
        return not self.check_leader_health()

    def elect_new_leader(self) -> MockPatroniMember:
        """选举新的 Leader

        策略：选择 LSN 最高的健康非 Leader 成员

        Returns:
            当选的新 Leader 成员

        Raises:
            RuntimeError: 没有合适的候选成员
        """
        current_leader_name = (
            self.dcs.leader.name if self.dcs.leader else None
        )
        candidates = [
            m for m in self._cluster_cache
            if m.healthy and m.state != "stopped"
            and m.name != current_leader_name
        ]
        if not candidates:
            raise RuntimeError("没有可用的候选成员进行选举")
        # 选择 LSN 最高的
        candidates.sort(key=lambda m: m.lsn, reverse=True)
        return candidates[0]

    def execute_failover(self, new_leader: MockPatroniMember,
                         start_time: float = None) -> dict:
        """执行故障转移

        步骤：
          1. 清除 DCS 中的 Leader 锁
          2. 提升新 Leader 的 PostgreSQL
          3. 更新 DCS 中的 Leader 记录
          4. 记录故障转移信息

        Returns:
            包含故障转移详情的字典
        """
        old_leader_name = (
            self.dcs.leader.name if self.dcs.leader else "unknown"
        )
        if start_time is None:
            start_time = time.time()

        # Step 1: 清除 Leader 锁
        self.dcs.remove_leader()

        # Step 2: 提升新 Leader
        new_leader_pg = MockPostgreSQL(is_primary=False)
        new_leader_pg.promote()

        # Step 3: 更新 DCS
        self.dcs.set_leader(new_leader.name)
        new_leader.set_role("primary")

        # Step 4: 计算耗时并记录
        elapsed = time.time() - start_time
        self.dcs.record_failover(old_leader_name, new_leader.name, elapsed)

        return {
            "old_leader": old_leader_name,
            "new_leader": new_leader.name,
            "elapsed": elapsed,
            "within_timeout": elapsed < self.FAILOVER_TIMEOUT,
        }

    def handle_failover(self, start_time: float = None) -> dict:
        """完整故障转移流程

        1. 检测 Leader 故障
        2. 选举新 Leader
        3. 执行切换

        Returns:
            故障转移结果字典
        """
        self.reload_cluster()
        if not self.detect_leader_failure():
            return {"error": "Leader 健康，无需故障转移"}

        new_leader = self.elect_new_leader()
        return self.execute_failover(new_leader, start_time)

    def rejoin_as_replica(self, old_leader_name: str) -> dict:
        """原主库恢复后以从库身份重新加入

        步骤：
          1. 找到恢复的成员
          2. 找到当前 Leader
          3. 恢复成员以 replica 角色加入
          4. 同步 WAL

        Returns:
            重新加入的详情
        """
        member = self.dcs.get_member(old_leader_name)
        if member is None:
            return {"error": f"未找到成员 {old_leader_name}"}

        current_leader = self.dcs.leader
        if current_leader is None:
            return {"error": "集群中没有 Leader，无法同步"}

        # 恢复成员作为 replica
        member.set_healthy(True)
        member.set_role("replica")

        # 模拟 WAL 同步
        member.lsn = current_leader.lsn

        return {
            "rejoined_member": old_leader_name,
            "role": "replica",
            "synced_from": current_leader.name,
            "wal_position": member.lsn,
        }

    def full_failover_and_recovery(
        self, old_leader_name: str, failover_start: float = None,
    ) -> dict:
        """完整演练：故障转移 + 原主库恢复重加入

        Returns:
            包含两个阶段的完整结果
        """
        if failover_start is None:
            failover_start = time.time()

        # Phase 1: 故障转移
        failover_result = self.handle_failover(failover_start)

        # Phase 2: 原主库重新加入
        recovery_result = self.rejoin_as_replica(old_leader_name)

        return {
            "failover": failover_result,
            "recovery": recovery_result,
        }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def cluster_3_members():
    """创建一个 3 节点 Patroni 集群"""
    members = [
        MockPatroniMember("pg-1", role="primary", address="10.0.0.1", port=5432, lsn=5000),
        MockPatroniMember("pg-2", role="replica", address="10.0.0.2", port=5432, lsn=4800),
        MockPatroniMember("pg-3", role="replica", address="10.0.0.3", port=5432, lsn=4500),
    ]
    dcs = MockDcs(members)
    dcs.set_leader("pg-1")
    return dcs, members


@pytest.fixture
def failover_controller(cluster_3_members):
    """创建故障转移控制器"""
    dcs, members = cluster_3_members
    pg = MockPostgreSQL(is_primary=True)
    controller = PatroniFailoverController(dcs, pg, members[0])
    controller.reload_cluster()
    return controller, dcs, members


# =============================================================================
# 测试：集群状态
# =============================================================================

class TestClusterStatus:
    """集群状态查询"""

    def test_initial_cluster_has_leader(self, failover_controller):
        """初始集群应有一个 Leader"""
        controller, dcs, _ = failover_controller
        status = controller.get_cluster_status()
        assert status["leader"] == "pg-1"

    def test_cluster_member_count(self, failover_controller):
        """集群成员数量应为 3"""
        controller, _, _ = failover_controller
        status = controller.get_cluster_status()
        assert status["member_count"] == 3

    def test_member_roles(self, failover_controller):
        """成员角色：1 个 primary + 2 个 replica"""
        controller, _, _ = failover_controller
        status = controller.get_cluster_status()
        roles = [m["role"] for m in status["members"]]
        assert roles.count("primary") == 1
        assert roles.count("replica") == 2


# =============================================================================
# 测试：Leader 健康检查
# =============================================================================

class TestLeaderHealthCheck:
    """Leader 健康检查"""

    def test_healthy_leader(self, failover_controller):
        """Leader 健康时返回 True"""
        controller, _, _ = failover_controller
        assert controller.check_leader_health() is True

    def test_leader_stopped(self, failover_controller):
        """Leader 停止时返回 False"""
        controller, _, members = failover_controller
        members[0].set_healthy(False)
        assert controller.check_leader_health() is False

    def test_no_leader(self, cluster_3_members):
        """没有 Leader 时返回 False"""
        dcs, members = cluster_3_members
        dcs.remove_leader()
        pg = MockPostgreSQL()
        controller = PatroniFailoverController(dcs, pg, members[0])
        assert controller.check_leader_health() is False

    def test_detect_failure_when_leader_down(self, failover_controller):
        """Leader 故障时 detect_leader_failure 返回 True"""
        controller, _, members = failover_controller
        members[0].set_healthy(False)
        assert controller.detect_leader_failure() is True

    def test_no_failure_when_healthy(self, failover_controller):
        """Leader 健康时 detect_leader_failure 返回 False"""
        controller, _, _ = failover_controller
        assert controller.detect_leader_failure() is False


# =============================================================================
# 测试：选举
# =============================================================================

class TestLeaderElection:
    """新 Leader 选举"""

    def test_elect_highest_lsn_replica(self, failover_controller):
        """应选举 LSN 最高的健康从库"""
        controller, _, _ = failover_controller
        candidate = controller.elect_new_leader()
        assert candidate.name == "pg-2"  # pg-2 的 LSN=4800 最高

    def test_elect_raises_when_no_candidates(self, failover_controller):
        """所有成员都不健康时应抛出异常"""
        controller, _, members = failover_controller
        for m in members:
            m.set_healthy(False)
        with pytest.raises(RuntimeError, match="没有可用的候选成员"):
            controller.elect_new_leader()

    def test_elect_skips_stopped_members(self, failover_controller):
        """选举应跳过已停止的成员"""
        controller, _, members = failover_controller
        # pg-2 也停止，只能选 pg-3
        members[1].set_healthy(False)
        candidate = controller.elect_new_leader()
        assert candidate.name == "pg-3"


# =============================================================================
# 测试：故障转移执行
# =============================================================================

class TestFailoverExecution:
    """故障转移执行"""

    def test_failover_changes_leader(self, failover_controller):
        """故障转移后 Leader 应变更"""
        controller, dcs, members = failover_controller
        # 模拟 Leader 故障
        members[0].set_healthy(False)
        controller.reload_cluster()

        result = controller.handle_failover()
        assert result["new_leader"] == "pg-2"
        assert dcs.leader.name == "pg-2"

    def test_failover_within_timeout(self, failover_controller):
        """故障转移耗时应 < 30 秒"""
        controller, _, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()

        result = controller.handle_failover()
        assert result["within_timeout"] is True
        assert result["elapsed"] < 30.0

    def test_failover_records_history(self, failover_controller):
        """故障转移应记录到 DCS 历史"""
        controller, dcs, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()

        controller.handle_failover()
        history = dcs.failover_history
        assert len(history) == 1
        assert history[0]["from"] == "pg-1"
        assert history[0]["to"] == "pg-2"

    def test_failover_promotes_new_leader_role(self, failover_controller):
        """故障转移后新 Leader 角色应为 primary"""
        controller, dcs, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()

        controller.handle_failover()
        assert dcs.leader.role == "primary"

    def test_failover_clears_old_leader(self, failover_controller):
        """故障转移后旧 Leader 不应再是 leader"""
        controller, dcs, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()

        controller.handle_failover()
        # pg-1 不再是 leader
        assert dcs.get_member("pg-1").name == "pg-1"
        assert dcs.leader.name != "pg-1"

    def test_no_failover_when_leader_healthy(self, failover_controller):
        """Leader 健康时不应执行故障转移"""
        controller, _, _ = failover_controller
        result = controller.handle_failover()
        assert "error" in result
        assert "无需故障转移" in result["error"]


# =============================================================================
# 测试：故障转移超时校验
# =============================================================================

class TestFailoverTimeout:
    """故障转移超时边界"""

    def test_failover_elapsed_is_below_30_seconds(self, failover_controller):
        """实际故障转移耗时远小于 30 秒"""
        controller, _, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()

        start = time.time()
        controller.handle_failover()
        elapsed = time.time() - start
        assert elapsed < 30.0

    def test_failover_timeout_constant_is_30(self):
        """超时阈值常量应为 30 秒"""
        assert PatroniFailoverController.FAILOVER_TIMEOUT == 30.0

    def test_within_timeout_flag_true_for_fast_failover(self, failover_controller):
        """快速故障转移 within_timeout 应为 True"""
        controller, _, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()

        result = controller.handle_failover(start_time=time.time())
        assert result["within_timeout"] is True


# =============================================================================
# 测试：原主库恢复后以从库身份重新加入
# =============================================================================

class TestRejoinAsReplica:
    """原主库重新加入"""

    def test_rejoin_sets_role_to_replica(self, failover_controller):
        """重新加入的角色应为 replica"""
        controller, dcs, members = failover_controller
        # 先执行故障转移
        members[0].set_healthy(False)
        controller.reload_cluster()
        controller.handle_failover()

        # 模拟原主库恢复
        members[0].set_healthy(True)
        result = controller.rejoin_as_replica("pg-1")
        assert result["role"] == "replica"

    def test_rejoin_syncs_wal(self, failover_controller):
        """重新加入时应同步 WAL 位置"""
        controller, dcs, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()
        controller.handle_failover()

        members[0].set_healthy(True)
        result = controller.rejoin_as_replica("pg-1")
        # WAL 位置应与当前 Leader 一致
        assert result["wal_position"] == members[1].lsn

    def test_rejoin_syncs_from_current_leader(self, failover_controller):
        """重新加入应从当前 Leader 同步"""
        controller, dcs, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()
        controller.handle_failover()

        members[0].set_healthy(True)
        result = controller.rejoin_as_replica("pg-1")
        assert result["synced_from"] == "pg-2"

    def test_rejoin_member_is_healthy(self, failover_controller):
        """重新加入后成员状态应为健康"""
        controller, dcs, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()
        controller.handle_failover()

        members[0].set_healthy(True)
        controller.rejoin_as_replica("pg-1")
        assert members[0].healthy is True

    def test_rejoin_fails_if_member_not_found(self, failover_controller):
        """不存在的成员无法重新加入"""
        controller, _, _ = failover_controller
        result = controller.rejoin_as_replica("pg-99")
        assert "error" in result
        assert "未找到成员" in result["error"]

    def test_rejoin_fails_if_no_leader(self, failover_controller):
        """集群无 Leader 时无法重新加入"""
        controller, dcs, members = failover_controller
        dcs.remove_leader()
        members[0].set_healthy(True)
        result = controller.rejoin_as_replica("pg-1")
        assert "error" in result
        assert "没有 Leader" in result["error"]

    def test_rejoined_member_is_not_leader(self, failover_controller):
        """重新加入的成员不应成为 Leader"""
        controller, dcs, members = failover_controller
        members[0].set_healthy(False)
        controller.reload_cluster()
        controller.handle_failover()

        members[0].set_healthy(True)
        controller.rejoin_as_replica("pg-1")
        # pg-2 仍然是 Leader
        assert dcs.leader.name == "pg-2"
        assert members[0].role == "replica"


# =============================================================================
# 测试：端到端演练
# =============================================================================

class TestEndToEndFailoverAndRecovery:
    """端到端：故障转移 + 原主库恢复"""

    def test_full_failover_and_recovery(self, failover_controller):
        """完整流程：主库故障 → 切换 → 原主库恢复为从库"""
        controller, dcs, members = failover_controller

        # Phase 1: pg-1 故障
        members[0].set_healthy(False)
        controller.reload_cluster()

        result = controller.full_failover_and_recovery("pg-1")

        # 验证故障转移
        assert result["failover"]["new_leader"] == "pg-2"
        assert result["failover"]["within_timeout"] is True

        # 验证原主库恢复
        assert result["recovery"]["rejoined_member"] == "pg-1"
        assert result["recovery"]["role"] == "replica"
        assert result["recovery"]["synced_from"] == "pg-2"

    def test_cluster_state_after_full_cycle(self, failover_controller):
        """完整循环后集群应有 1 primary + 2 replica"""
        controller, dcs, members = failover_controller

        members[0].set_healthy(False)
        controller.reload_cluster()
        controller.full_failover_and_recovery("pg-1")

        status = controller.get_cluster_status()
        roles = [m["role"] for m in status["members"]]
        assert roles.count("primary") == 1
        assert roles.count("replica") == 2
        assert status["leader"] == "pg-2"

    def test_failover_history_after_full_cycle(self, failover_controller):
        """完整循环后 DCS 应记录一次故障转移"""
        controller, dcs, members = failover_controller

        members[0].set_healthy(False)
        controller.reload_cluster()
        controller.full_failover_and_recovery("pg-1")

        history = dcs.failover_history
        assert len(history) == 1
        assert history[0]["from"] == "pg-1"
        assert history[0]["to"] == "pg-2"
        assert history[0]["elapsed"] < 30.0

    def test_sequential_failover(self, failover_controller):
        """连续两次故障转移（pg-1 → pg-2 故障 → pg-3）"""
        controller, dcs, members = failover_controller

        # 第一次故障转移：pg-1 故障 → pg-2 当选
        members[0].set_healthy(False)
        controller.reload_cluster()
        result1 = controller.handle_failover()
        assert result1["new_leader"] == "pg-2"

        # 第二次故障转移：pg-2 也故障 → pg-3 当选
        members[1].set_healthy(False)
        controller.reload_cluster()
        result2 = controller.handle_failover()
        assert result2["new_leader"] == "pg-3"

        # 验证历史
        history = dcs.failover_history
        assert len(history) == 2
        assert history[0]["from"] == "pg-1"
        assert history[0]["to"] == "pg-2"
        assert history[1]["from"] == "pg-2"
        assert history[1]["to"] == "pg-3"
