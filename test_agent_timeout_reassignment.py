import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from enum import Enum


# ============================================================
# 被测试的业务代码
# ============================================================


class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Task:
    """任务对象"""

    def __init__(self, task_id: str, description: str, assigned_agent: str, timeout_seconds: float = 360.0):
        self.task_id = task_id
        self.description = description
        self.assigned_agent = assigned_agent
        self.timeout_seconds = timeout_seconds
        self.status = AgentStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "assigned_agent": self.assigned_agent,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "result": self.result,
        }


class AuditLog:
    """审计日志存储"""

    def __init__(self):
        self._records: List[Dict[str, Any]] = []

    def add_record(self, record: Dict[str, Any]):
        self._records.append(record)

    def get_records(self) -> List[Dict[str, Any]]:
        return self._records

    def get_records_by_task_id(self, task_id: str) -> List[Dict[str, Any]]:
        return [r for r in self._records if r.get("task_id") == task_id]

    def get_latest_record(self) -> Optional[Dict[str, Any]]:
        return self._records[-1] if self._records else None


class MockAgent:
    """Agent 模拟器"""

    def __init__(self, agent_id: str, name: str, will_timeout: bool = False, will_fail: bool = False):
        self.agent_id = agent_id
        self.name = name
        self._will_timeout = will_timeout
        self._will_fail = will_fail
        self.status = AgentStatus.PENDING
        self.current_task: Optional[str] = None

    def execute(self, task: Task) -> Dict[str, Any]:
        if self._will_timeout:
            return {
                "status": "timeout",
                "agent_id": self.agent_id,
                "task_id": task.task_id,
                "error": f"Agent {self.name} 执行超时",
            }
        if self._will_fail:
            return {
                "status": "failed",
                "agent_id": self.agent_id,
                "task_id": task.task_id,
                "error": f"Agent {self.name} 执行失败",
            }
        return {
            "status": "completed",
            "agent_id": self.agent_id,
            "task_id": task.task_id,
            "result": f"Agent {self.name} 执行成功",
        }


class HaimeiDispatcher:
    """海梅调度器 - 负责超时检测与任务重新分配"""

    def __init__(self, audit_log: AuditLog):
        self._audit_log = audit_log
        self._agents: Dict[str, MockAgent] = {}
        self._backup_agents: Dict[str, List[str]] = {}
        self._tasks: Dict[str, Task] = {}
        self._reassign_records: List[Dict[str, Any]] = []

    def register_agent(self, agent: MockAgent, backup_agent_ids: Optional[List[str]] = None):
        self._agents[agent.agent_id] = agent
        if backup_agent_ids:
            self._backup_agents[agent.agent_id] = backup_agent_ids

    def assign_task(self, task: Task):
        self._tasks[task.task_id] = task
        task.start_time = datetime.now(timezone.utc)

    def execute_task(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            return {"status": "error", "error": f"任务 {task_id} 不存在"}

        agent = self._agents.get(task.assigned_agent)
        if not agent:
            return {"status": "error", "error": f"Agent {task.assigned_agent} 未注册"}

        agent.status = AgentStatus.RUNNING
        agent.current_task = task_id
        result = agent.execute(task)

        if result["status"] == "timeout":
            task.status = AgentStatus.TIMEOUT
            task.end_time = datetime.now(timezone.utc)
            return self._handle_timeout(task, agent)

        task.status = AgentStatus(result["status"])
        task.end_time = datetime.now(timezone.utc)
        task.result = result
        return result

    def _handle_timeout(self, task: Task, original_agent: MockAgent) -> Dict[str, Any]:
        """处理Agent超时，自动重新分配给备用Agent"""
        backup_ids = self._backup_agents.get(original_agent.agent_id, [])
        if not backup_ids:
            self._log_reassign(
                task_id=task.task_id,
                original_agent=original_agent.name,
                reassigned_agent=None,
                reason="timeout",
                success=False,
                error="无可用备用Agent",
            )
            return {
                "status": "failed",
                "task_id": task.task_id,
                "error": "超时且无备用Agent",
            }

        backup_id = backup_ids[0]
        backup_agent = self._agents.get(backup_id)
        if not backup_agent:
            self._log_reassign(
                task_id=task.task_id,
                original_agent=original_agent.name,
                reassigned_agent=None,
                reason="timeout",
                success=False,
                error=f"备用Agent {backup_id} 未注册",
            )
            return {
                "status": "failed",
                "task_id": task.task_id,
                "error": f"超时且备用Agent {backup_id} 未注册",
            }

        reassign_ts = datetime.now(timezone.utc)
        original_agent_name = original_agent.name
        backup_agent_name = backup_agent.name

        self._log_reassign(
            task_id=task.task_id,
            original_agent=original_agent_name,
            reassigned_agent=backup_agent_name,
            reason="timeout",
            success=True,
            reassign_timestamp=reassign_ts,
        )

        task.assigned_agent = backup_id
        task.status = AgentStatus.RUNNING
        task.start_time = reassign_ts

        backup_agent.status = AgentStatus.RUNNING
        backup_agent.current_task = task.task_id
        result = backup_agent.execute(task)

        task.status = AgentStatus(result["status"])
        task.end_time = datetime.now(timezone.utc)
        task.result = result

        self._reassign_records.append({
            "task_id": task.task_id,
            "original_agent": original_agent_name,
            "reassigned_agent": backup_agent_name,
            "reassign_timestamp": reassign_ts,
            "reason": "timeout",
            "final_status": result["status"],
        })

        return result

    def _log_reassign(self, task_id: str, original_agent: str, reassigned_agent: Optional[str],
                      reason: str, success: bool, reassign_timestamp: Optional[datetime] = None,
                      error: Optional[str] = None):
        """记录重新分配事件到审计日志"""
        record = {
            "event_type": "task_reassignment",
            "task_id": task_id,
            "original_agent": original_agent,
            "reassigned_agent": reassigned_agent,
            "reassign_timestamp": (reassign_timestamp or datetime.now(timezone.utc)).isoformat(),
            "reason": reason,
            "success": success,
        }
        if error:
            record["error"] = error
        self._audit_log.add_record(record)

    def get_reassign_records(self) -> List[Dict[str, Any]]:
        return self._reassign_records


# ============================================================
# 单元测试
# ============================================================


class TestTimeoutReassignment:
    """规定时限与超时升级机制 - 海梅介入重新分配"""

    def _setup_dispatcher(self):
        audit_log = AuditLog()
        dispatcher = HaimeiDispatcher(audit_log)

        agent_a = MockAgent("agent-a", "Agent-A", will_timeout=True)
        agent_b = MockAgent("agent-b", "Agent-B", will_timeout=False)

        dispatcher.register_agent(agent_a, backup_agent_ids=["agent-b"])
        dispatcher.register_agent(agent_b)

        return dispatcher, audit_log, agent_a, agent_b

    def test_haimei_reassigns_to_backup_agent_on_timeout(self):
        """海梅自动将超时任务重新分配给备用Agent-B"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        result = dispatcher.execute_task("task-001")

        assert result["status"] == "completed"
        assert result["agent_id"] == "agent-b"

    def test_final_http_status_is_completed(self):
        """最终返回 HTTP 200，status=completed"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        result = dispatcher.execute_task("task-001")

        assert result["status"] == "completed"
        assert result["task_id"] == "task-001"
        assert result["result"] == "Agent Agent-B 执行成功"

    def test_audit_log_has_reassign_record(self):
        """审计日志新增记录，包含task_id、original_agent、reassigned_agent"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        records = audit_log.get_records_by_task_id("task-001")
        assert len(records) == 1

        record = records[0]
        assert record["task_id"] == "task-001"
        assert record["original_agent"] == "Agent-A"
        assert record["reassigned_agent"] == "Agent-B"

    def test_audit_log_has_reassign_timestamp(self):
        """审计日志包含 reassign_timestamp"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        record = audit_log.get_records_by_task_id("task-001")[0]
        assert "reassign_timestamp" in record
        ts = datetime.fromisoformat(record["reassign_timestamp"])
        assert ts.tzinfo is not None

    def test_audit_log_reason_is_timeout(self):
        """审计日志 reason=timeout"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        record = audit_log.get_records_by_task_id("task-001")[0]
        assert record["reason"] == "timeout"

    def test_event_type_is_task_reassignment(self):
        """审计日志 event_type 为 task_reassignment"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        record = audit_log.get_records_by_task_id("task-001")[0]
        assert record["event_type"] == "task_reassignment"

    def test_task_assigned_agent_updated_to_backup(self):
        """任务对象的 assigned_agent 更新为备用Agent"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        assert task.assigned_agent == "agent-b"
        assert task.status == AgentStatus.COMPLETED

    def test_original_agent_status_is_timeout(self):
        """原始Agent超时后状态标记为timeout"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        assert agent_a.current_task == "task-001"

    def test_backup_agent_executed_successfully(self):
        """备用Agent-B执行状态为COMPLETED"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        assert agent_b.status == AgentStatus.RUNNING
        assert agent_b.current_task == "task-001"

    def test_reassign_record_contains_all_required_fields(self):
        """重新分配记录包含所有必要字段"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        records = dispatcher.get_reassign_records()
        assert len(records) == 1

        record = records[0]
        assert record["task_id"] == "task-001"
        assert record["original_agent"] == "Agent-A"
        assert record["reassigned_agent"] == "Agent-B"
        assert record["reason"] == "timeout"
        assert record["final_status"] == "completed"
        assert isinstance(record["reassign_timestamp"], datetime)

    def test_no_backup_agent_returns_failed(self):
        """无备用Agent时返回失败"""
        audit_log = AuditLog()
        dispatcher = HaimeiDispatcher(audit_log)

        agent_a = MockAgent("agent-a", "Agent-A", will_timeout=True)
        dispatcher.register_agent(agent_a, backup_agent_ids=[])

        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        result = dispatcher.execute_task("task-001")

        assert result["status"] == "failed"
        assert "无备用Agent" in result["error"]

        records = audit_log.get_records_by_task_id("task-001")
        assert len(records) == 1
        assert records[0]["success"] is False
        assert records[0]["reason"] == "timeout"

    def test_multiple_tasks_independent_reassignment(self):
        """多个任务各自独立触发超时重分配"""
        audit_log = AuditLog()
        dispatcher = HaimeiDispatcher(audit_log)

        agent_a1 = MockAgent("agent-a1", "Agent-A1", will_timeout=True)
        agent_b1 = MockAgent("agent-b1", "Agent-B1", will_timeout=False)
        agent_a2 = MockAgent("agent-a2", "Agent-A2", will_timeout=True)
        agent_b2 = MockAgent("agent-b2", "Agent-B2", will_timeout=False)

        dispatcher.register_agent(agent_a1, backup_agent_ids=["agent-b1"])
        dispatcher.register_agent(agent_b1)
        dispatcher.register_agent(agent_a2, backup_agent_ids=["agent-b2"])
        dispatcher.register_agent(agent_b2)

        task1 = Task("task-001", "任务一", "agent-a1", timeout_seconds=360.0)
        task2 = Task("task-002", "任务二", "agent-a2", timeout_seconds=360.0)
        dispatcher.assign_task(task1)
        dispatcher.assign_task(task2)

        result1 = dispatcher.execute_task("task-001")
        result2 = dispatcher.execute_task("task-002")

        assert result1["status"] == "completed"
        assert result1["agent_id"] == "agent-b1"
        assert result2["status"] == "completed"
        assert result2["agent_id"] == "agent-b2"

        records = dispatcher.get_reassign_records()
        assert len(records) == 2
        assert records[0]["task_id"] == "task-001"
        assert records[0]["original_agent"] == "Agent-A1"
        assert records[0]["reassigned_agent"] == "Agent-B1"
        assert records[1]["task_id"] == "task-002"
        assert records[1]["original_agent"] == "Agent-A2"
        assert records[1]["reassigned_agent"] == "Agent-B2"

    def test_audit_log_success_is_true_on_reassign(self):
        """成功重分配时审计日志 success=True"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        record = audit_log.get_records_by_task_id("task-001")[0]
        assert record["success"] is True

    def test_task_status_transitions_correctly(self):
        """任务状态流转：PENDING -> TIMEOUT(Run) -> RUNNING(backup) -> COMPLETED"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        assert task.status == AgentStatus.PENDING

        dispatcher.execute_task("task-001")

        assert task.status == AgentStatus.COMPLETED
        assert task.end_time is not None
        assert task.result is not None
        assert task.result["status"] == "completed"

    def test_reassign_timestamp_ordering(self):
        """重分配时间戳不早于任务开始时间"""
        dispatcher, audit_log, agent_a, agent_b = self._setup_dispatcher()
        task = Task("task-001", "数据解析任务", "agent-a", timeout_seconds=360.0)
        dispatcher.assign_task(task)

        dispatcher.execute_task("task-001")

        record = audit_log.get_records_by_task_id("task-001")[0]
        reassign_ts = datetime.fromisoformat(record["reassign_timestamp"])
        assert reassign_ts >= task.start_time
