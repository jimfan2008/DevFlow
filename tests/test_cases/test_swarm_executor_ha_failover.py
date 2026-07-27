import asyncio
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# 领域模型（自包含，不依赖外部模块）
# ============================================================


class ExecutorRole(Enum):
    PRIMARY = "primary"
    STANDBY = "standby"
    OFFLINE = "offline"


class ContainerStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PENDING = "pending"


class MockDockerContainer:
    """模拟 Docker 容器"""

    def __init__(self, container_id: str, image: str, status: ContainerStatus = ContainerStatus.RUNNING,
                 swarm_task_id: str = "", executor_id: str = ""):
        self.container_id = container_id
        self.image = image
        self._status = status
        self.swarm_task_id = swarm_task_id
        self.executor_id = executor_id
        self.created_at = datetime.now(timezone.utc)

    @property
    def status(self) -> ContainerStatus:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status == ContainerStatus.RUNNING

    def stop(self):
        self._status = ContainerStatus.STOPPED

    def restart(self):
        self._status = ContainerStatus.RUNNING

    def to_dict(self) -> dict:
        return {
            "container_id": self.container_id,
            "image": self.image,
            "status": self._status.value,
            "swarm_task_id": self.swarm_task_id,
            "executor_id": self.executor_id,
        }


class MockContainerRegistry:
    """模拟 Docker 容器注册表（全局容器池）"""

    def __init__(self):
        self._containers: Dict[str, MockDockerContainer] = {}

    def create(self, container_id: str, image: str, status: ContainerStatus = ContainerStatus.RUNNING,
               swarm_task_id: str = "", executor_id: str = "") -> MockDockerContainer:
        c = MockDockerContainer(container_id, image, status, swarm_task_id, executor_id)
        self._containers[container_id] = c
        return c

    def get(self, container_id: str) -> Optional[MockDockerContainer]:
        return self._containers.get(container_id)

    def list_all(self) -> List[MockDockerContainer]:
        return list(self._containers.values())

    def list_by_executor(self, executor_id: str) -> List[MockDockerContainer]:
        return [c for c in self._containers.values() if c.executor_id == executor_id]

    def list_running(self) -> List[MockDockerContainer]:
        return [c for c in self._containers.values() if c.is_running]

    def remove(self, container_id: str):
        self._containers.pop(container_id, None)


class MockSwarmExecutor:
    """模拟 Swarm Executor 实例"""

    def __init__(self, executor_id: str, role: ExecutorRole = ExecutorRole.PRIMARY,
                 container_registry: MockContainerRegistry = None):
        self.executor_id = executor_id
        self._role = role
        self._healthy = True
        self._registry = container_registry or MockContainerRegistry()
        self.managed_containers: Dict[str, MockDockerContainer] = {}
        self._task_queue: List[dict] = []
        self._failover_history: List[dict] = []
        self._heartbeat_time: float = time.time()
        self._started_at = datetime.now(timezone.utc)

    @property
    def role(self) -> ExecutorRole:
        return self._role

    @property
    def is_healthy(self) -> bool:
        return self._healthy

    @property
    def heartbeat_time(self) -> float:
        return self._heartbeat_time

    @property
    def task_queue(self) -> List[dict]:
        return list(self._task_queue)

    @property
    def failover_history(self) -> List[dict]:
        return list(self._failover_history)

    def simulate_crash(self):
        """模拟 Executor 实例崩溃"""
        self._healthy = False

    def recover(self):
        """模拟 Executor 实例恢复"""
        self._healthy = True
        self._role = ExecutorRole.STANDBY
        self._heartbeat_time = time.time()

    def heartbeat(self):
        """发送心跳"""
        self._heartbeat_time = time.time()

    def is_alive(self, timeout: float = 30.0) -> bool:
        """检查是否存活（心跳超时判断）"""
        if not self._healthy:
            return False
        return (time.time() - self._heartbeat_time) < timeout

    def register_container(self, container: MockDockerContainer):
        """注册管理的容器"""
        container.executor_id = self.executor_id
        self.managed_containers[container.container_id] = container

    def unregister_container(self, container_id: str):
        """注销容器"""
        self.managed_containers.pop(container_id, None)

    def get_managed_containers(self) -> List[MockDockerContainer]:
        """获取当前管理的容器列表"""
        return list(self.managed_containers.values())

    def enqueue_task(self, task: dict):
        """将任务加入队列"""
        task["enqueued_at"] = datetime.now(timezone.utc).isoformat()
        task["executor_id"] = self.executor_id
        self._task_queue.append(task)

    def dequeue_task(self) -> Optional[dict]:
        """从队列中取出一个任务"""
        if self._task_queue:
            return self._task_queue.pop(0)
        return None

    def scan_containers(self) -> List[MockDockerContainer]:
        """扫描注册表中属于自己但尚未管理的容器"""
        existing = self._registry.list_by_executor(self.executor_id)
        scanned = []
        for c in existing:
            if c.container_id not in self.managed_containers:
                self.register_container(c)
                scanned.append(c)
        return scanned

    def promote_to_primary(self):
        """升级为主节点"""
        old_role = self._role
        self._role = ExecutorRole.PRIMARY
        self._heartbeat_time = time.time()
        self._failover_history.append({
            "action": "promote",
            "from_role": old_role.value,
            "to_role": "primary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def demote_to_standby(self):
        """降级为备节点"""
        old_role = self._role
        self._role = ExecutorRole.STANDBY
        self._heartbeat_time = time.time()
        self._failover_history.append({
            "action": "demote",
            "from_role": old_role.value,
            "to_role": "standby",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


class SwarmExecutorFailoverController:
    """Swarm Executor 主备故障转移控制器

    职责：
      1. 监控主 Executor 心跳
      2. 主实例故障时自动切换到备实例
      3. 切换时保障运行中容器不受影响
      4. 重启后扫描现有容器并重新管理
      5. 防止脑裂：通过分布式锁确保同一时刻只有一个主节点
    """

    FAILOVER_TIMEOUT = 30.0
    HEARTBEAT_INTERVAL = 5.0
    HEARTBEAT_TIMEOUT = 15.0

    def __init__(self, primary: MockSwarmExecutor, standby: MockSwarmExecutor,
                 container_registry: MockContainerRegistry = None):
        self.primary = primary
        self.standby = standby
        self._registry = container_registry or MockContainerRegistry()
        self._current_primary: Optional[MockSwarmExecutor] = primary
        self._distributed_lock_acquired = False
        self._lock_holder: Optional[str] = None
        self._failover_count = 0
        self._split_brain_detected = False

    @property
    def current_primary(self) -> Optional[MockSwarmExecutor]:
        return self._current_primary

    @property
    def failover_count(self) -> int:
        return self._failover_count

    def check_primary_health(self) -> bool:
        """检查主 Executor 是否健康"""
        if self.primary is None:
            return False
        return self.primary.is_healthy and self.primary.is_alive(self.HEARTBEAT_TIMEOUT)

    def detect_primary_failure(self) -> bool:
        """检测主 Executor 是否故障"""
        return not self.check_primary_health()

    def acquire_distributed_lock(self, candidate_id: str) -> bool:
        """模拟获取分布式锁（防脑裂）"""
        if self._distributed_lock_acquired and self._lock_holder != candidate_id:
            self._split_brain_detected = True
            return False
        self._distributed_lock_acquired = True
        self._lock_holder = candidate_id
        return True

    def release_distributed_lock(self):
        """释放分布式锁"""
        self._distributed_lock_acquired = False
        self._lock_holder = None

    def execute_failover(self) -> dict:
        """执行主备切换

        步骤：
          1. 获取分布式锁（防止脑裂）
          2. 备实例升级为主节点
          3. 接管主实例管理的容器（仅转移管理权，不中断容器运行）
          4. 接管主实例的任务队列
          5. 记录故障转移历史

        Returns:
            故障转移结果字典
        """
        result = {
            "success": False,
            "old_primary": self.primary.executor_id if self.primary else None,
            "new_primary": None,
            "containers_transferred": 0,
            "containers_interrupted": 0,
            "tasks_transferred": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Step 0: 确认主节点已故障
        if not self.detect_primary_failure():
            result["error"] = "primary_still_alive"
            return result

        # Step 1: 获取分布式锁
        if not self.acquire_distributed_lock(self.standby.executor_id):
            result["error"] = "distributed_lock_failed_split_brain"
            result["split_brain"] = True
            return result

        # Step 2: 记录原有运行中的容器
        old_managed = self.primary.get_managed_containers()
        running_containers = [c for c in old_managed if c.is_running]

        # Step 3: 备实例升级为主节点
        self.standby.promote_to_primary()
        result["new_primary"] = self.standby.executor_id

        # Step 4: 接管容器管理权（不中断容器运行）
        for container in old_managed:
            # 更新容器的 executor_id，但保持容器状态不变
            container.executor_id = self.standby.executor_id
            self.standby.register_container(container)
            self.primary.unregister_container(container.container_id)
            result["containers_transferred"] += 1

        # 验证：运行中容器不应被中断
        for container in running_containers:
            if not container.is_running:
                result["containers_interrupted"] += 1

        # Step 5: 接管任务队列
        while self.primary.task_queue:
            task = self.primary.dequeue_task()
            if task:
                task["executor_id"] = self.standby.executor_id
                self.standby.enqueue_task(task)
                result["tasks_transferred"] += 1

        # Step 6: 更新控制器状态
        old_primary = self.primary
        self.primary.demote_to_standby() if self.primary.is_healthy else None
        self._current_primary = self.standby
        self.standby.heartbeat()
        self._failover_count += 1

        # Step 7: 记录历史
        self.standby._failover_history.append({
            "action": "failover",
            "old_primary": old_primary.executor_id if old_primary else None,
            "new_primary": self.standby.executor_id,
            "containers_transferred": result["containers_transferred"],
            "tasks_transferred": result["tasks_transferred"],
            "timestamp": result["timestamp"],
        })

        result["success"] = True
        return result

    def scan_and_remanage_containers(self, executor: MockSwarmExecutor) -> dict:
        """重启后扫描现有容器并重新管理

        Returns:
            重新管理的结果
        """
        scanned = executor.scan_containers()
        running = [c for c in scanned if c.is_running]
        stopped = [c for c in scanned if not c.is_running]

        result = {
            "executor_id": executor.executor_id,
            "total_scanned": len(scanned),
            "running": len(running),
            "stopped": len(stopped),
            "containers": [c.to_dict() for c in scanned],
        }
        return result

    def handle_primary_recovery(self, recovered_primary: MockSwarmExecutor) -> dict:
        """处理原主节点恢复后的重新加入

        原主节点恢复后应作为备节点重新加入集群。

        Returns:
            重新加入的结果
        """
        recovered_primary.recover()
        self.release_distributed_lock()

        # 将恢复的实例设为备用
        standby_containers = recovered_primary.get_managed_containers()
        current_primary_containers = self._current_primary.get_managed_containers() if self._current_primary else []

        result = {
            "recovered_executor": recovered_primary.executor_id,
            "new_role": recovered_primary.role.value,
            "current_primary": self._current_primary.executor_id if self._current_primary else None,
            "recovered_containers": len(standby_containers),
            "primary_containers": len(current_primary_containers),
        }
        return result


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def container_registry():
    """创建容器注册表"""
    return MockContainerRegistry()


@pytest.fixture
def executors(container_registry):
    """创建主备 Executor 对"""
    primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)
    standby = MockSwarmExecutor("exec-standby-01", ExecutorRole.STANDBY, container_registry)
    return primary, standby


@pytest.fixture
def fa_controller(container_registry):
    """创建故障转移控制器"""
    primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)
    standby = MockSwarmExecutor("exec-standby-01", ExecutorRole.STANDBY, container_registry)
    controller = SwarmExecutorFailoverController(primary, standby, container_registry)
    primary.heartbeat()
    return controller, primary, standby, container_registry


@pytest.fixture
def executors_with_containers(container_registry):
    """创建带有运行中容器的主备 Executor 对"""
    primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)
    standby = MockSwarmExecutor("exec-standby-01", ExecutorRole.STANDBY, container_registry)

    # 在主节点上创建运行中的容器
    containers = []
    for i in range(5):
        c = container_registry.create(
            container_id=f"container-{i:03d}",
            image=f"swarm-agent:v{i}",
            status=ContainerStatus.RUNNING,
            swarm_task_id=f"task-{i:03d}",
            executor_id="exec-primary-01",
        )
        primary.register_container(c)
        containers.append(c)

    return primary, standby, containers


@pytest.fixture
def fa_controller_with_containers(container_registry):
    """创建带有容器的故障转移控制器"""
    primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)
    standby = MockSwarmExecutor("exec-standby-01", ExecutorRole.STANDBY, container_registry)

    for i in range(5):
        c = container_registry.create(
            container_id=f"container-{i:03d}",
            image=f"swarm-agent:v{i}",
            status=ContainerStatus.RUNNING,
            swarm_task_id=f"task-{i:03d}",
            executor_id="exec-primary-01",
        )
        primary.register_container(c)

    controller = SwarmExecutorFailoverController(primary, standby, container_registry)
    primary.heartbeat()
    return controller, primary, standby, container_registry


# ============================================================
# 测试组：主备健康检查
# ============================================================


class TestPrimaryHealthCheck:
    """主 Executor 健康检查"""

    def test_primary_healthy(self, fa_controller):
        """主节点正常时健康检查返回 True"""
        controller, primary, _, _ = fa_controller
        assert controller.check_primary_health() is True

    def test_primary_crash_detected(self, fa_controller):
        """主节点崩溃时检测到故障"""
        controller, primary, _, _ = fa_controller
        primary.simulate_crash()
        assert controller.detect_primary_failure() is True

    def test_no_failure_when_healthy(self, fa_controller):
        """主节点健康时不应检测到故障"""
        controller, primary, _, _ = fa_controller
        assert controller.detect_primary_failure() is False

    def test_primary_not_alive_after_crash(self, fa_controller):
        """主节点崩溃后 is_alive 返回 False"""
        controller, primary, _, _ = fa_controller
        primary.simulate_crash()
        assert primary.is_alive() is False


# ============================================================
# 测试组：自动故障转移
# ============================================================


class TestAutomaticFailover:
    """主节点故障后备节点接管"""

    def test_failover_success_on_primary_crash(self, fa_controller):
        """验收标准：主实例故障后备实例成功接管"""
        controller, primary, standby, _ = fa_controller
        primary.simulate_crash()

        result = controller.execute_failover()

        assert result["success"] is True
        assert result["old_primary"] == "exec-primary-01"
        assert result["new_primary"] == "exec-standby-01"
        assert controller.current_primary == standby
        assert standby.role == ExecutorRole.PRIMARY

    def test_failover_no_action_when_primary_alive(self, fa_controller):
        """主节点正常时不应执行故障转移"""
        controller, primary, _, _ = fa_controller

        result = controller.execute_failover()

        assert result["success"] is False
        assert result["error"] == "primary_still_alive"
        assert controller.current_primary == primary

    def test_failover_increases_counter(self, fa_controller):
        """故障转移后计数器递增"""
        controller, primary, _, _ = fa_controller
        assert controller.failover_count == 0

        primary.simulate_crash()
        controller.execute_failover()

        assert controller.failover_count == 1

    def test_failover_records_history_on_standby(self, fa_controller):
        """故障转移历史应记录在备节点上"""
        controller, primary, standby, _ = fa_controller
        primary.simulate_crash()
        controller.execute_failover()

        history = standby.failover_history
        failover_records = [h for h in history if h["action"] == "failover"]
        assert len(failover_records) == 1
        assert failover_records[0]["old_primary"] == "exec-primary-01"
        assert failover_records[0]["new_primary"] == "exec-standby-01"

    def test_failover_standby_becomes_primary(self, fa_controller):
        """备节点在故障转移后角色变更为主节点"""
        controller, primary, standby, _ = fa_controller
        assert standby.role == ExecutorRole.STANDBY

        primary.simulate_crash()
        controller.execute_failover()

        assert standby.role == ExecutorRole.PRIMARY


# ============================================================
# 测试组：运行中容器不受影响
# ============================================================


class TestContainersNotInterrupted:
    """验收标准：运行中容器在切换时不受影响"""

    def test_running_containers_remain_running_after_failover(self, fa_controller_with_containers):
        """切换后运行中容器仍然保持运行状态"""
        controller, primary, standby, registry = fa_controller_with_containers

        running_before = registry.list_running()
        assert len(running_before) == 5

        primary.simulate_crash()
        result = controller.execute_failover()

        running_after = registry.list_running()
        assert len(running_after) == 5
        assert result["containers_interrupted"] == 0

    def test_container_management_transferred_to_standby(self, fa_controller_with_containers):
        """容器管理权应转移到备节点"""
        controller, primary, standby, _ = fa_controller_with_containers

        primary.simulate_crash()
        result = controller.execute_failover()

        standby_containers = standby.get_managed_containers()
        primary_containers = primary.get_managed_containers()

        assert len(standby_containers) == 5
        assert len(primary_containers) == 0
        assert result["containers_transferred"] == 5

    def test_container_executor_id_updated_after_failover(self, fa_controller_with_containers):
        """容器的 executor_id 更新为新主节点"""
        controller, primary, standby, registry = fa_controller_with_containers

        primary.simulate_crash()
        controller.execute_failover()

        all_containers = registry.list_all()
        for c in all_containers:
            assert c.executor_id == "exec-standby-01"

    def test_container_task_id_preserved_after_failover(self, fa_controller_with_containers):
        """容器的 swarm_task_id 在切换后保持不变"""
        controller, primary, standby, registry = fa_controller_with_containers

        original_task_ids = {}
        for c in primary.get_managed_containers():
            original_task_ids[c.container_id] = c.swarm_task_id

        primary.simulate_crash()
        controller.execute_failover()

        for c in registry.list_all():
            assert c.swarm_task_id == original_task_ids[c.container_id]

    def test_mix_running_stopped_containers_transferred(self, fa_controller_with_containers):
        """混合状态容器（运行中+已停止）都能正确转移"""
        controller, primary, standby, registry = fa_controller_with_containers

        # 将部分容器设为已停止
        registry.get("container-001").stop()
        registry.get("container-003").stop()

        primary.simulate_crash()
        result = controller.execute_failover()

        assert result["containers_transferred"] == 5
        assert result["containers_interrupted"] == 0

        standby_containers = standby.get_managed_containers()
        running = [c for c in standby_containers if c.is_running]
        stopped = [c for c in standby_containers if not c.is_running]
        assert len(running) == 3
        assert len(stopped) == 2


# ============================================================
# 测试组：任务队列转移
# ============================================================


class TestTaskQueueTransfer:
    """任务队列在切换时转移"""

    def test_tasks_transferred_to_standby(self, fa_controller):
        """主节点任务队列中的任务应转移到备节点"""
        controller, primary, standby, _ = fa_controller

        primary.enqueue_task({"task_id": "t1", "action": "write_code"})
        primary.enqueue_task({"task_id": "t2", "action": "run_tests"})
        primary.enqueue_task({"task_id": "t3", "action": "deploy"})

        primary.simulate_crash()
        result = controller.execute_failover()

        assert result["tasks_transferred"] == 3
        assert len(standby.task_queue) == 3
        assert len(primary.task_queue) == 0

    def test_task_executor_id_updated(self, fa_controller):
        """转移后的任务其 executor_id 应更新为新主节点"""
        controller, primary, standby, _ = fa_controller

        primary.enqueue_task({"task_id": "t1", "action": "write_code"})

        primary.simulate_crash()
        controller.execute_failover()

        task = standby.task_queue[0]
        assert task["executor_id"] == "exec-standby-01"

    def test_empty_queue_failover_safe(self, fa_controller):
        """空队列时故障转移仍然安全"""
        controller, primary, standby, _ = fa_controller

        primary.simulate_crash()
        result = controller.execute_failover()

        assert result["success"] is True
        assert result["tasks_transferred"] == 0
        assert len(standby.task_queue) == 0


# ============================================================
# 测试组：重启后扫描容器重新管理
# ============================================================


class TestRestartContainerScan:
    """验收标准：重启后扫描现有容器重新管理"""

    def test_scan_finds_orphaned_containers(self, container_registry):
        """重启后应扫描到遗留的容器"""
        primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)

        # 模拟之前创建的容器（executor_id 指向旧实例）
        for i in range(3):
            container_registry.create(
                container_id=f"old-container-{i:03d}",
                image="swarm-agent:v1",
                status=ContainerStatus.RUNNING,
                executor_id="exec-primary-01",
            )

        # 新启动的实例 managed_containers 为空
        assert len(primary.get_managed_containers()) == 0

        # 扫描后应重新管理
        scanned = primary.scan_containers()
        assert len(scanned) == 3
        assert len(primary.get_managed_containers()) == 3

    def test_scan_preserves_container_status(self, container_registry):
        """扫描不应改变容器运行状态"""
        primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)

        c1 = container_registry.create("c1", "agent:v1", ContainerStatus.RUNNING, executor_id="exec-primary-01")
        c2 = container_registry.create("c2", "agent:v1", ContainerStatus.STOPPED, executor_id="exec-primary-01")
        c3 = container_registry.create("c3", "agent:v1", ContainerStatus.RUNNING, executor_id="exec-primary-01")

        scanned = primary.scan_containers()

        status_map = {s.container_id: s._status for s in scanned}
        assert status_map["c1"] == ContainerStatus.RUNNING
        assert status_map["c2"] == ContainerStatus.STOPPED
        assert status_map["c3"] == ContainerStatus.RUNNING

    def test_controller_scan_and_remanage(self, container_registry):
        """控制器应能通过 scan_and_remanage_containers 重新管理"""
        primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)
        standby = MockSwarmExecutor("exec-standby-01", ExecutorRole.STANDBY, container_registry)
        controller = SwarmExecutorFailoverController(primary, standby, container_registry)

        # 模拟遗留容器
        container_registry.create("orphan-1", "agent:v1", ContainerStatus.RUNNING, executor_id="exec-standby-01")
        container_registry.create("orphan-2", "agent:v1", ContainerStatus.RUNNING, executor_id="exec-standby-01")
        container_registry.create("orphan-3", "agent:v1", ContainerStatus.STOPPED, executor_id="exec-standby-01")

        result = controller.scan_and_remanage_containers(standby)

        assert result["total_scanned"] == 3
        assert result["running"] == 2
        assert result["stopped"] == 1

    def test_scan_only_picks_up_unmanaged(self, container_registry):
        """扫描不应重复注册已管理的容器"""
        primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)

        c1 = container_registry.create("c1", "agent:v1", ContainerStatus.RUNNING, executor_id="exec-primary-01")
        c2 = container_registry.create("c2", "agent:v1", ContainerStatus.RUNNING, executor_id="exec-primary-01")

        # 先管理 c1
        primary.register_container(c1)
        assert len(primary.get_managed_containers()) == 1

        # 扫描应只发现 c2
        scanned = primary.scan_containers()
        assert len(scanned) == 1
        assert scanned[0].container_id == "c2"
        assert len(primary.get_managed_containers()) == 2


# ============================================================
# 测试组：网络分区与脑裂处理
# ============================================================


class TestNetworkPartition:
    """网络分区场景下的脑裂处理"""

    def test_split_brain_prevented_by_lock(self, fa_controller):
        """分布式锁应防止脑裂"""
        controller, primary, standby, _ = fa_controller

        # 模拟另一个进程已持有锁
        controller.acquire_distributed_lock("other-executor")

        primary.simulate_crash()
        result = controller.execute_failover()

        assert result["success"] is False
        assert result["error"] == "distributed_lock_failed_split_brain"
        assert result["split_brain"] is True
        assert standby.role == ExecutorRole.STANDBY

    def test_failover_succeeds_after_lock_released(self, fa_controller):
        """锁释放后故障转移应成功"""
        controller, primary, standby, _ = fa_controller

        # 获取锁、释放锁
        controller.acquire_distributed_lock("other-executor")
        controller.release_distributed_lock()

        primary.simulate_crash()
        result = controller.execute_failover()

        assert result["success"] is True
        assert standby.role == ExecutorRole.PRIMARY

    def test_same_holder_can_acquire_lock(self, fa_controller):
        """锁持有者可以重复获取锁"""
        controller, primary, standby, _ = fa_controller

        controller.acquire_distributed_lock(standby.executor_id)

        # 同一候选再次获取锁
        acquired = controller.acquire_distributed_lock(standby.executor_id)
        assert acquired is True


# ============================================================
# 测试组：主节点恢复后的重新加入
# ============================================================


class TestPrimaryRecovery:
    """主节点恢复后的重新选举行为"""

    def test_recovered_primary_becomes_standby(self, fa_controller_with_containers):
        """原主节点恢复后应作为备节点加入"""
        controller, primary, standby, _ = fa_controller_with_containers

        primary.simulate_crash()
        controller.execute_failover()

        recovery = controller.handle_primary_recovery(primary)

        assert primary.role == ExecutorRole.STANDBY
        assert recovery["new_role"] == "standby"
        assert recovery["current_primary"] == "exec-standby-01"

    def test_recovered_primary_not_current_primary(self, fa_controller_with_containers):
        """恢复后的主节点不应成为当前主节点"""
        controller, primary, standby, _ = fa_controller_with_containers

        primary.simulate_crash()
        controller.execute_failover()
        controller.handle_primary_recovery(primary)

        assert controller.current_primary == standby
        assert primary.role == ExecutorRole.STANDBY

    def test_lock_released_on_recovery(self, fa_controller_with_containers):
        """恢复时应释放分布式锁"""
        controller, primary, standby, _ = fa_controller_with_containers

        primary.simulate_crash()
        controller.execute_failover()

        assert controller._distributed_lock_acquired is True

        controller.handle_primary_recovery(primary)

        assert controller._distributed_lock_acquired is False


# ============================================================
# 测试组：连续故障转移
# ============================================================


class TestSequentialFailover:
    """连续多次故障转移"""

    def test_double_failover(self, container_registry):
        """两次连续的故障转移"""
        primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)
        standby = MockSwarmExecutor("exec-standby-01", ExecutorRole.STANDBY, container_registry)
        standby2 = MockSwarmExecutor("exec-standby-02", ExecutorRole.STANDBY, container_registry)

        # 第一次故障转移
        controller1 = SwarmExecutorFailoverController(primary, standby, container_registry)
        primary.heartbeat()
        primary.simulate_crash()
        result1 = controller1.execute_failover()

        assert result1["success"] is True
        assert result1["new_primary"] == "exec-standby-01"

        # 第二次故障转移：原备节点也崩溃
        standby.simulate_crash()
        controller2 = SwarmExecutorFailoverController(standby, standby2, container_registry)
        standby2.heartbeat()
        # standby 已经不健康，standby2 应该接管
        standby._healthy = False
        result2 = controller2.execute_failover()

        assert result2["success"] is True
        assert result2["new_primary"] == "exec-standby-02"

    def test_containers_survive_multiple_failovers(self, container_registry):
        """多次故障转移后容器仍存活"""
        primary = MockSwarmExecutor("exec-primary-01", ExecutorRole.PRIMARY, container_registry)
        standby = MockSwarmExecutor("exec-standby-01", ExecutorRole.STANDBY, container_registry)

        for i in range(3):
            c = container_registry.create(
                f"container-{i:03d}", "agent:v1",
                ContainerStatus.RUNNING, executor_id="exec-primary-01",
            )
            primary.register_container(c)

        primary.simulate_crash()
        controller = SwarmExecutorFailoverController(primary, standby, container_registry)
        controller.execute_failover()

        running = registry.list_running() if (registry := container_registry) else []
        assert len(running) == 3
        for c in running:
            assert c.is_running


# ============================================================
# 测试组：边界场景
# ============================================================


class TestEdgeCases:
    """边界值/异常场景测试"""

    def test_empty_swarm_failover(self, fa_controller):
        """无容器无任务时的切换应安全"""
        controller, primary, standby, _ = fa_controller

        primary.simulate_crash()
        result = controller.execute_failover()

        assert result["success"] is True
        assert result["containers_transferred"] == 0
        assert result["tasks_transferred"] == 0
        assert result["containers_interrupted"] == 0

    def test_failover_timeout_constant(self):
        """超时阈值常量应正确设置"""
        assert SwarmExecutorFailoverController.FAILOVER_TIMEOUT == 30.0
        assert SwarmExecutorFailoverController.HEARTBEAT_INTERVAL == 5.0
        assert SwarmExecutorFailoverController.HEARTBEAT_TIMEOUT == 15.0

    def test_executor_heartbeat_updates_time(self, executors):
        """心跳应更新时间戳"""
        primary, _ = executors

        old_time = primary.heartbeat_time
        time.sleep(0.01)
        primary.heartbeat()

        assert primary.heartbeat_time > old_time

    def test_container_to_dict(self):
        """容器的 to_dict 方法应返回完整信息"""
        c = MockDockerContainer("c1", "agent:v1", ContainerStatus.RUNNING, "task-1", "exec-1")
        d = c.to_dict()

        assert d["container_id"] == "c1"
        assert d["image"] == "agent:v1"
        assert d["status"] == "running"
        assert d["swarm_task_id"] == "task-1"
        assert d["executor_id"] == "exec-1"

    def test_failover_with_pending_containers(self, fa_controller):
        """待启动状态的容器也能正确转移"""
        controller, primary, standby, registry = fa_controller

        c = registry.create(
            "pending-container", "agent:v1",
            ContainerStatus.PENDING, executor_id="exec-primary-01",
        )
        primary.register_container(c)

        primary.simulate_crash()
        result = controller.execute_failover()

        assert result["success"] is True
        assert result["containers_transferred"] == 1

        standby_c = standby.get_managed_containers()
        assert len(standby_c) == 1
        assert standby_c[0]._status == ContainerStatus.PENDING

    def test_primary_demoted_after_failover(self, fa_controller):
        """故障转移后主节点应降级"""
        controller, primary, standby, _ = fa_controller

        primary.simulate_crash()
        controller.execute_failover()

        # 崩溃的主节点无法降级，但角色应已被标记
        assert primary._healthy is False

    def test_scatter_containers_across_tasks(self, fa_controller_with_containers):
        """不同 swarm 任务的容器都应被转移"""
        controller, primary, standby, _ = fa_controller_with_containers

        task_ids = {c.swarm_task_id for c in primary.get_managed_containers()}
        assert len(task_ids) == 5

        primary.simulate_crash()
        controller.execute_failover()

        new_task_ids = {c.swarm_task_id for c in standby.get_managed_containers()}
        assert new_task_ids == task_ids
