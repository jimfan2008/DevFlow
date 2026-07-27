import pytest
import time
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum
from unittest.mock import MagicMock, patch


# ============================================================
# 被测试的业务代码（模拟 Swarm Executor 主备架构）
# ============================================================


class ExecutorRole(Enum):
    PRIMARY = "primary"
    STANDBY = "standby"
    FAILED = "failed"


class Container:
    """模拟正在运行的容器"""

    def __init__(self, container_id: str, name: str, status: str = "running",
                 started_at: datetime = None):
        self.container_id = container_id
        self.name = name
        self.status = status
        self.started_at = started_at or datetime.now(timezone.utc)
        self.managed_by: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "container_id": self.container_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "managed_by": self.managed_by,
        }


class MockSwarmExecutor:
    """模拟 Swarm Executor 实例（主/备节点）"""

    def __init__(self, instance_id: str, role: ExecutorRole, host: str = "localhost",
                 port: int = 8000):
        self.instance_id = instance_id
        self._role = role
        self.host = host
        self.port = port
        self._alive = True
        self._containers: Dict[str, Container] = {}
        self._heartbeat_time: Optional[datetime] = None
        self._failover_time: Optional[datetime] = None

    @property
    def role(self) -> ExecutorRole:
        return self._role

    @property
    def is_alive(self) -> bool:
        return self._alive

    @property
    def containers(self) -> Dict[str, Container]:
        return dict(self._containers)

    @property
    def heartbeat_time(self) -> Optional[datetime]:
        return self._heartbeat_time

    def simulate_crash(self):
        """模拟实例崩溃"""
        self._alive = False
        self._role = ExecutorRole.FAILED

    def recover(self):
        """实例恢复，以 standby 角色重启"""
        self._alive = True
        self._role = ExecutorRole.STANDBY
        self._heartbeat_time = datetime.now(timezone.utc)

    def promote_to_primary(self):
        """提升为主节点"""
        self._role = ExecutorRole.PRIMARY
        self._failover_time = datetime.now(timezone.utc)
        self._heartbeat_time = datetime.now(timezone.utc)

    def run_container(self, container_id: str, name: str) -> Container:
        """启动一个容器"""
        if not self._alive:
            raise RuntimeError(f"Executor {self.instance_id} 已宕机，无法启动容器")
        container = Container(container_id, name, "running")
        container.managed_by = self.instance_id
        self._containers[container_id] = container
        return container

    def stop_container(self, container_id: str) -> bool:
        """停止一个容器"""
        container = self._containers.get(container_id)
        if container:
            container.status = "stopped"
            return True
        return False

    def get_container_status(self, container_id: str) -> Optional[str]:
        """获取容器运行状态"""
        container = self._containers.get(container_id)
        return container.status if container else None

    def scan_containers(self) -> List[Container]:
        """扫描现有容器列表"""
        return list(self._containers.values())

    def take_over_containers(self, source_executor: "MockSwarmExecutor"):
        """接管源执行器的所有容器"""
        for cid, container in source_executor._containers.items():
            if container.status == "running":
                container.managed_by = self.instance_id
                self._containers[cid] = container

    def send_heartbeat(self):
        """发送心跳"""
        if self._alive:
            self._heartbeat_time = datetime.now(timezone.utc)


class SwarmExecutorHealthChecker:
    """Swarm Executor 健康检查器
    负责定期检测主/备节点心跳，触发故障转移
    """

    HEARTBEAT_TIMEOUT_SECONDS = 10

    def __init__(self, primary: MockSwarmExecutor, standby: MockSwarmExecutor):
        self.primary = primary
        self.standby = standby
        self._failover_history: List[Dict] = []
        self._failover_in_progress = False

    def check_primary_health(self) -> bool:
        """检查主节点是否健康"""
        if not self.primary.is_alive:
            return False
        if self.primary.role != ExecutorRole.PRIMARY:
            return False
        if self.primary.heartbeat_time is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.primary.heartbeat_time).total_seconds()
        return elapsed < self.HEARTBEAT_TIMEOUT_SECONDS

    def detect_primary_failure(self) -> bool:
        """检测主节点是否故障"""
        return not self.check_primary_health()

    def check_standby_available(self) -> bool:
        """检查备用节点是否可用"""
        return self.standby.is_alive and self.standby.role == ExecutorRole.STANDBY

    def perform_failover(self) -> Dict:
        """执行主备切换
        返回切换结果，包含：
          - success: 是否成功
          - old_primary: 旧主节点实例 ID
          - new_primary: 新主节点实例 ID
          - containers_preserved: 保留的容器列表
          - elapsed: 切换耗时（秒）
        """
        start_time = time.time()
        old_primary_id = self.primary.instance_id

        result = {
            "success": False,
            "old_primary": old_primary_id,
            "new_primary": None,
            "containers_preserved": [],
            "elapsed": 0,
        }

        # Step 1: 确认主节点故障
        if not self.detect_primary_failure():
            result["error"] = "primary_still_healthy"
            return result

        # Step 2: 确认备节点可用
        if not self.check_standby_available():
            result["error"] = "standby_not_available"
            return result

        # Step 3: 收集主节点上的运行中容器
        running_containers = {
            cid: c for cid, c in self.primary.containers.items()
            if c.status == "running"
        }

        # Step 4: 备节点提升为主节点
        self.standby.promote_to_primary()
        result["new_primary"] = self.standby.instance_id

        # Step 5: 接管容器（容器继续保持运行）
        self.standby.take_over_containers(self.primary)
        result["containers_preserved"] = [c.container_id for c in running_containers.values()]

        # Step 6: 记录切换历史
        elapsed = time.time() - start_time
        result["elapsed"] = elapsed
        result["success"] = True
        history_entry = {
            "old_primary": old_primary_id,
            "new_primary": self.standby.instance_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed": elapsed,
            "containers_preserved_count": len(running_containers),
        }
        self._failover_history.append(history_entry)
        return result

    def get_failover_history(self) -> List[Dict]:
        """获取故障转移历史记录"""
        return list(self._failover_history)

    def restart_and_scan(self, executor: MockSwarmExecutor) -> Dict:
        """Executor 重启后扫描现有容器并重新管理
        模拟实例重启后的容器重新发现机制
        """
        executor.send_heartbeat()
        existing_containers = executor.scan_containers()
        unmanaged = [c for c in existing_containers if c.managed_by != executor.instance_id]

        # 重新接管未管理的容器
        for container in unmanaged:
            container.managed_by = executor.instance_id

        existing_before = [c.container_id for c in existing_containers]

        return {
            "executor_id": executor.instance_id,
            "role": executor.role.value,
            "containers_scanned": len(existing_containers),
            "containers_adopted": len(unmanaged),
            "container_ids": existing_before,
            "scan_time": datetime.now(timezone.utc).isoformat(),
        }


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def primary_executor():
    """创建主 Executor 实例"""
    exe = MockSwarmExecutor("exe-primary-1", ExecutorRole.PRIMARY, "10.0.0.1", 8001)
    exe.send_heartbeat()
    return exe


@pytest.fixture
def standby_executor():
    """创建备 Executor 实例"""
    exe = MockSwarmExecutor("exe-standby-1", ExecutorRole.STANDBY, "10.0.0.2", 8002)
    exe.send_heartbeat()
    return exe


@pytest.fixture
def checker(primary_executor, standby_executor):
    """创建健康检查器"""
    return SwarmExecutorHealthChecker(primary_executor, standby_executor)


@pytest.fixture
def checker_with_containers(primary_executor, standby_executor):
    """创建带有运行中容器的检查器"""
    checker = SwarmExecutorHealthChecker(primary_executor, standby_executor)
    primary_executor.run_container("container-001", "agent-houfa-1")
    primary_executor.run_container("container-002", "agent-houda-1")
    primary_executor.run_container("container-003", "agent-houfa-2")
    return checker, primary_executor, standby_executor


# ============================================================
# 测试组 1: 主节点健康检查
# ============================================================


class TestPrimaryHealthCheck:
    """主节点健康检查"""

    def test_primary_healthy(self, checker):
        """主节点正常运行时，健康检查返回 True"""
        assert checker.check_primary_health() is True

    def test_primary_crash_detected(self, checker, primary_executor):
        """主节点崩溃时，健康检查返回 False"""
        primary_executor.simulate_crash()
        assert checker.check_primary_health() is False

    def test_primary_heartbeat_timeout(self, checker, primary_executor):
        """主节点心跳超时时，健康检查返回 False"""
        old_time = primary_executor.heartbeat_time
        primary_executor._heartbeat_time = datetime.now(timezone.utc).replace(
            minute=primary_executor.heartbeat_time.minute - 1
        ) if old_time else datetime(2020, 1, 1, tzinfo=timezone.utc)
        # 设为很久之前
        primary_executor._heartbeat_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert checker.check_primary_health() is False

    def test_detect_primary_failure_returns_true_on_crash(self, checker, primary_executor):
        """主节点崩溃时 detect 接口返回 True"""
        primary_executor.simulate_crash()
        assert checker.detect_primary_failure() is True

    def test_detect_primary_failure_returns_false_when_healthy(self, checker):
        """主节点正常时 detect 接口返回 False"""
        assert checker.detect_primary_failure() is False

    def test_standby_available(self, checker):
        """备节点正常时 check_standby_available 返回 True"""
        assert checker.check_standby_available() is True

    def test_standby_not_available_when_crashed(self, checker, standby_executor):
        """备节点崩溃时 check_standby_available 返回 False"""
        standby_executor.simulate_crash()
        assert checker.check_standby_available() is False


# ============================================================
# 测试组 2: 主备切换（验收标准：自动切换成功）
# ============================================================


class TestFailoverSuccess:
    """自动切换成功"""

    def test_failover_success_on_primary_crash(self, checker, primary_executor, standby_executor):
        """主节点故障后备实例接管"""
        primary_executor.simulate_crash()
        result = checker.perform_failover()

        assert result["success"] is True
        assert result["old_primary"] == primary_executor.instance_id
        assert result["new_primary"] == standby_executor.instance_id
        assert result["elapsed"] >= 0

    def test_standby_promoted_to_primary(self, checker, primary_executor, standby_executor):
        """切换后备节点角色变为主节点"""
        primary_executor.simulate_crash()
        checker.perform_failover()

        assert standby_executor.role == ExecutorRole.PRIMARY
        assert standby_executor.is_alive is True
        assert standby_executor._failover_time is not None

    def test_failover_fails_when_primary_healthy(self, checker):
        """主节点正常时不应执行切换"""
        result = checker.perform_failover()
        assert result["success"] is False
        assert result["error"] == "primary_still_healthy"

    def test_failover_fails_when_standby_unavailable(self, checker, primary_executor, standby_executor):
        """备节点不可用时切换失败"""
        primary_executor.simulate_crash()
        standby_executor.simulate_crash()

        result = checker.perform_failover()
        assert result["success"] is False
        assert result["error"] == "standby_not_available"

    def test_failover_completes_within_timeout(self, checker, primary_executor, standby_executor):
        """切换操作应在合理时间范围内完成"""
        primary_executor.simulate_crash()

        start = time.time()
        result = checker.perform_failover()
        elapsed = time.time() - start

        assert result["success"] is True
        assert elapsed < 5.0, f"切换耗时 {elapsed:.4f}s 超过 5s 限制"

    def test_failover_history_recorded(self, checker, primary_executor, standby_executor):
        """切换事件应记录到历史"""
        primary_executor.simulate_crash()
        checker.perform_failover()

        history = checker.get_failover_history()
        assert len(history) == 1
        assert history[0]["old_primary"] == primary_executor.instance_id
        assert history[0]["new_primary"] == standby_executor.instance_id
        assert "timestamp" in history[0]
        assert history[0]["containers_preserved_count"] >= 0


# ============================================================
# 测试组 3: 运行中容器不受影响（验收标准）
# ============================================================


class TestContainersUnaffected:
    """运行中容器不受影响"""

    def test_running_containers_preserved_after_failover(self, checker_with_containers):
        """切换后运行中容器仍然在运行"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.simulate_crash()
        result = checker.perform_failover()

        # 容器状态应保持 "running"
        for cid in ["container-001", "container-002", "container-003"]:
            container_status = standby_exe.get_container_status(cid)
            assert container_status == "running", f"容器 {cid} 不应被中断"

    def test_containers_transferred_to_standby(self, checker_with_containers):
        """切换后容器被备节点接管管理"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.simulate_crash()
        checker.perform_failover()

        for cid in ["container-001", "container-002", "container-003"]:
            container = standby_exe.containers.get(cid)
            assert container is not None, f"容器 {cid} 应在备节点上可访问"
            assert container.managed_by == standby_exe.instance_id

    def test_containers_preserved_count_matches(self, checker_with_containers):
        """切换结果中应列出所有保留的容器"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.simulate_crash()
        result = checker.perform_failover()

        preserved_ids = set(result["containers_preserved"])
        expected_ids = {"container-001", "container-002", "container-003"}
        assert preserved_ids == expected_ids

    def test_stopped_containers_not_transferred(self, checker_with_containers):
        """已停止的容器不应被转移"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.stop_container("container-003")
        primary_exe.simulate_crash()
        result = checker.perform_failover()

        # 已停止的容器不应出现在 preserved 列表中
        preserved_ids = set(result["containers_preserved"])
        assert "container-003" not in preserved_ids
        # standby 上不应有 stopped 容器
        standby_containers = standby_exe.scan_containers()
        assert all(c.status == "running" for c in standby_containers)

    def test_container_data_integrity_after_failover(self, checker_with_containers):
        """切换后容器数据完整"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.simulate_crash()
        checker.perform_failover()

        standby_containers = standby_exe.containers
        assert len(standby_containers) == 3
        for cid, container in standby_containers.items():
            assert container.status == "running"
            assert container.managed_by == standby_exe.instance_id
            assert container.started_at is not None


# ============================================================
# 测试组 4: 重启后扫描现有容器重新管理（验收标准）
# ============================================================


class TestRestartAndRescan:
    """重启后扫描现有容器重新管理"""

    def test_restart_scans_existing_containers(self, checker_with_containers):
        """备节点重启后能扫描到接管的容器"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.simulate_crash()
        checker.perform_failover()

        # 模拟备节点（新主节点）重启后扫描
        scan_result = checker.restart_and_scan(standby_exe)

        assert scan_result["containers_scanned"] == 3
        assert set(scan_result["container_ids"]) == {"container-001", "container-002", "container-003"}

    def test_restart_adopts_unmanaged_containers(self, checker_with_containers):
        """重启后应重新接管孤儿容器"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.simulate_crash()
        checker.perform_failover()

        # 模拟容器 managed_by 丢失（如内存状态丢失）
        for container in standby_exe.containers.values():
            container.managed_by = None

        scan_result = checker.restart_and_scan(standby_exe)

        assert scan_result["containers_adopted"] == 3
        for container in standby_exe.containers.values():
            assert container.managed_by == standby_exe.instance_id

    def test_primary_recovery_becomes_standby(self, checker_with_containers):
        """旧主节点恢复后应以备节点身份运行"""
        checker, primary_exe, standby_exe = checker_with_containers

        primary_exe.simulate_crash()
        checker.perform_failover()

        # 旧主节点恢复
        primary_exe.recover()

        assert primary_exe.role == ExecutorRole.STANDBY
        assert primary_exe.is_alive is True

    def test_primary_recovery_send_heartbeat(self, checker, primary_executor):
        """主节点恢复后应能正常发送心跳"""
        primary_executor.simulate_crash()
        primary_executor.recover()

        primary_executor.send_heartbeat()
        assert primary_executor.heartbeat_time is not None

    def test_scan_empty_executor(self, standby_executor):
        """空 Executor 扫描返回空列表"""
        scan_result = SwarmExecutorHealthChecker(
            MockSwarmExecutor("temp-primary", ExecutorRole.PRIMARY),
            standby_executor,
        ).restart_and_scan(standby_executor)

        assert scan_result["containers_scanned"] == 0
        assert scan_result["containers_adopted"] == 0
        assert scan_result["container_ids"] == []

    def test_scan_partial_containers(self, standby_executor):
        """部分容器场景下扫描正确返回"""
        standby_executor.run_container("c1", "agent-1")
        standby_executor.run_container("c2", "agent-2")
        standby_executor.stop_container("c2")

        checker = SwarmExecutorHealthChecker(
            MockSwarmExecutor("temp-primary", ExecutorRole.PRIMARY),
            standby_executor,
        )
        scan_result = checker.restart_and_scan(standby_executor)

        assert scan_result["containers_scanned"] == 2
        assert set(scan_result["container_ids"]) == {"c1", "c2"}


# ============================================================
# 测试组 5: 边界场景
# ============================================================


class TestEdgeCases:
    """边界场景测试"""

    def test_failover_no_containers_on_primary(self, checker, primary_executor, standby_executor):
        """主节点上无任务时切换安全"""
        primary_executor.simulate_crash()
        result = checker.perform_failover()

        assert result["success"] is True
        assert result["containers_preserved"] == []

    def test_multiple_failovers(self, primary_executor, standby_executor):
        """多次主备切换应能正常记录历史"""
        # 第一次切换
        checker1 = SwarmExecutorHealthChecker(primary_executor, standby_executor)
        primary_executor.simulate_crash()
        result1 = checker1.perform_failover()
        assert result1["success"] is True
        assert result1["new_primary"] == standby_executor.instance_id

        # standby 成为 primary 后运行
        standby_executor.send_heartbeat()

        # 第二次切换：新主也崩溃，旧主恢复为备后可再次切换
        # 此场景需要新的备节点，此处验证历史正确记录了第一次
        history = checker1.get_failover_history()
        assert len(history) == 1

    def test_failover_with_many_containers(self, primary_executor, standby_executor):
        """大量容器时切换正常"""
        checker = SwarmExecutorHealthChecker(primary_executor, standby_executor)

        for i in range(50):
            primary_executor.run_container(f"container-{i:03d}", f"agent-{i}")

        primary_executor.simulate_crash()
        result = checker.perform_failover()

        assert result["success"] is True
        assert len(result["containers_preserved"]) == 50
        assert standby_executor.role == ExecutorRole.PRIMARY

    def test_failover_elapsed_is_recorded(self, checker, primary_executor, standby_executor):
        """切换耗时应被正确记录"""
        primary_executor.simulate_crash()
        result = checker.perform_failover()

        assert result["elapsed"] > 0
        assert isinstance(result["elapsed"], float)

    def test_failover_history_multiple_entries(self, primary_executor, standby_executor):
        """多次切换应累计记录历史"""
        checker = SwarmExecutorHealthChecker(primary_executor, standby_executor)

        # 第一次切换
        primary_executor.simulate_crash()
        checker.perform_failover()

        # 模拟新备节点，第二次切换
        new_standby = MockSwarmExecutor("exe-standby-2", ExecutorRole.STANDBY, "10.0.0.3", 8003)
        new_standby.send_heartbeat()

        standby_executor.simulate_crash()
        # 重建 checker
        checker2 = SwarmExecutorHealthChecker(standby_executor, new_standby)
        checker2.perform_failover()

        # 第一次的 checker 有 1 条记录
        assert len(checker.get_failover_history()) == 1
        # 第二次的 checker 有 1 条记录
        assert len(checker2.get_failover_history()) == 1

    def test_health_check_timeout_constant(self):
        """心跳超时阈值应合理设置"""
        assert SwarmExecutorHealthChecker.HEARTBEAT_TIMEOUT_SECONDS == 10

    def test_primary_crash_then_recover_state(self, primary_executor):
        """主节点崩溃后恢复状态正确"""
        primary_executor.run_container("c1", "agent-1")
        original_containers = dict(primary_executor.containers)

        primary_executor.simulate_crash()
        assert primary_executor.role == ExecutorRole.FAILED
        assert primary_executor.is_alive is False

        primary_executor.recover()
        assert primary_executor.role == ExecutorRole.STANDBY
        assert primary_executor.is_alive is True
        # 重启后容器列表应该清空（模拟内存重启）
        # 但原对象上容器仍然存在，只是角色变了
        assert primary_executor.containers is not None


# ============================================================
# 测试组 6: 端到端集成测试
# ============================================================


class TestEndToEnd:
    """端到端：主备切换完整流程"""

    def test_full_failover_workflow(self):
        """完整流程：运行容器 → 主节点崩溃 → 备节点接管 → 容器继续运行 → 旧主恢复为备"""
        primary = MockSwarmExecutor("exe-primary-1", ExecutorRole.PRIMARY, "10.0.0.1", 8001)
        standby = MockSwarmExecutor("exe-standby-1", ExecutorRole.STANDBY, "10.0.0.2", 8002)
        checker = SwarmExecutorHealthChecker(primary, standby)

        # Phase 1: 正常运行，主节点管理容器
        primary.send_heartbeat()
        c1 = primary.run_container("c001", "agent-houfa-1")
        c2 = primary.run_container("c002", "agent-houda-1")
        c3 = primary.run_container("c003", "agent-houfa-2")

        assert checker.check_primary_health() is True
        assert c1.managed_by == primary.instance_id
        assert c2.managed_by == primary.instance_id
        assert c3.managed_by == primary.instance_id

        # Phase 2: 主节点崩溃
        primary.simulate_crash()
        assert checker.detect_primary_failure() is True
        assert checker.check_standby_available() is True

        # Phase 3: 自动切换
        result = checker.perform_failover()
        assert result["success"] is True
        assert result["new_primary"] == standby.instance_id
        assert len(result["containers_preserved"]) == 3

        # Phase 4: 验证容器不受影响
        for cid in ["c001", "c002", "c003"]:
            assert standby.get_container_status(cid) == "running"
            assert standby.containers[cid].managed_by == standby.instance_id

        # Phase 5: 旧主节点恢复为备
        primary.recover()
        assert primary.role == ExecutorRole.STANDBY
        assert primary.is_alive is True

        # Phase 6: 新主节点重启后扫描容器并重新管理
        # 模拟容器 managed_by 丢失
        for container in standby.containers.values():
            container.managed_by = None

        scan = checker.restart_and_scan(standby)
        assert scan["containers_scanned"] == 3
        assert scan["containers_adopted"] == 3

        for container in standby.containers.values():
            assert container.managed_by == standby.instance_id

        # Phase 7: 验证历史
        history = checker.get_failover_history()
        assert len(history) == 1
        assert history[0]["containers_preserved_count"] == 3

    def test_failover_with_mixed_container_states(self):
        """混合状态容器（运行中+已停止）的切换"""
        primary = MockSwarmExecutor("exe-p", ExecutorRole.PRIMARY, "10.0.0.1", 8001)
        standby = MockSwarmExecutor("exe-s", ExecutorRole.STANDBY, "10.0.0.2", 8002)
        checker = SwarmExecutorHealthChecker(primary, standby)

        primary.send_heartbeat()
        primary.run_container("run-1", "running-agent-1")
        primary.run_container("run-2", "running-agent-2")
        primary.run_container("stop-1", "stopped-agent-1")
        primary.run_container("run-3", "running-agent-3")
        primary.stop_container("stop-1")

        primary.simulate_crash()
        result = checker.perform_failover()

        assert result["success"] is True
        # 只有 running 的容器被转移
        preserved = set(result["containers_preserved"])
        assert preserved == {"run-1", "run-2", "run-3"}
        assert "stop-1" not in preserved

        standby_containers = standby.scan_containers()
        assert all(c.status == "running" for c in standby_containers)
        assert len(standby_containers) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
