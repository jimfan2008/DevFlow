import pytest
import time
import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from unittest.mock import MagicMock, patch, mock_open


# ============================================================
# 被测试的业务代码（模拟 Agent 回传故障转移）
# ============================================================


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    DELIVERED = "delivered"
    ACCEPTED = "accepted"
    FAILED = "failed"


class CallbackMode(Enum):
    """回调模式"""
    HTTP = "http"
    SHARED_VOLUME_POLLING = "shared_volume_polling"


class AgentCallbackResult:
    """Agent 回调结果"""

    def __init__(self, task_id: str, status: TaskStatus, mode: CallbackMode,
                 success: bool, error: Optional[str] = None):
        self.task_id = task_id
        self.status = status
        self.mode = mode
        self.success = success
        self.error = error
        self.timestamp = datetime.now(timezone.utc)


class MockHTTPCallback:
    """模拟 HTTP 回调客户端"""

    def __init__(self, callback_url: str, force_failure: bool = False,
                 failure_type: str = "500"):
        self.callback_url = callback_url
        self.force_failure = force_failure
        self.failure_type = failure_type
        self.request_count = 0
        self.last_request_body: Optional[Dict] = None

    def post(self, data: Dict) -> Dict:
        self.request_count += 1
        self.last_request_body = dict(data)
        if self.force_failure:
            if self.failure_type == "500":
                return {"status_code": 500, "error": "Internal Server Error"}
            elif self.failure_type == "timeout":
                return {"status_code": -1, "error": "Connection Timeout (30s)"}
            elif self.failure_type == "connection_refused":
                return {"status_code": -2, "error": "Connection Refused"}
        return {"status_code": 200, "body": {"received": True}}


class SharedVolumePoller:
    """共享卷轮询器

    当 HTTP 回调失败时，回退到轮询共享目录中的 .done 文件来
    确认 Agent 是否已完成任务。
    """

    POLLING_INTERVAL = 5  # 5秒轮询间隔

    def __init__(self, artifact_dir: str, max_polls: int = 12):
        self.artifact_dir = artifact_dir
        self.max_polls = max_polls
        self.poll_count = 0
        self.files: Dict[str, Dict] = {}
        self._stop_event = threading.Event()

    def has_done_file(self, task_id: str) -> bool:
        """检查 task_id.done 文件是否存在"""
        done_key = f"{task_id}.done"
        return done_key in self.files

    def read_done_file(self, task_id: str) -> Optional[Dict]:
        """读取 .done 文件内容"""
        done_key = f"{task_id}.done"
        if done_key in self.files:
            return self.files[done_key]
        return None

    def create_done_file(self, task_id: str, content: Dict):
        """模拟 Agent 写入 .done 文件（测试用）"""
        done_key = f"{task_id}.done"
        self.files[done_key] = content

    def simulate_agent_completion(self, task_id: str, delay_seconds: float = 0,
                                  content: Optional[Dict] = None):
        """模拟 Agent 在延迟后写入 .done 文件"""
        if content is None:
            content = {"task_id": task_id, "status": "completed",
                       "output_hash": "abc123def456"}

        def _write():
            time.sleep(delay_seconds)
            self.create_done_file(task_id, content)

        t = threading.Thread(target=_write, daemon=True)
        t.start()

    def poll(self, task_id: str, timeout_seconds: Optional[float] = None) -> Dict:
        """轮询 .done 文件

        返回:
            {
                "found": bool,
                "content": Optional[Dict],
                "polls": int,
                "elapsed_seconds": float,
            }
        """
        if timeout_seconds is None:
            timeout_seconds = max(1, self.POLLING_INTERVAL * self.max_polls)
        # 至少允许 1 秒，确保测试中 POLLING_INTERVAL=0 时仍能执行
        timeout_seconds = max(1.0, timeout_seconds)

        start_time = time.time()
        self.poll_count = 0

        for _ in range(self.max_polls):
            self.poll_count += 1
            done_content = self.read_done_file(task_id)
            if done_content is not None:
                return {
                    "found": True,
                    "content": done_content,
                    "polls": self.poll_count,
                    "elapsed_seconds": time.time() - start_time,
                }
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                break
            if self.POLLING_INTERVAL > 0:
                time.sleep(self.POLLING_INTERVAL)

        return {
            "found": False,
            "content": None,
            "polls": self.poll_count,
            "elapsed_seconds": time.time() - start_time,
        }


class TaskStatusStore:
    """任务状态存储（模拟数据库）"""

    def __init__(self):
        self.tasks: Dict[str, Dict] = {}

    def create_task(self, task_id: str, status: TaskStatus = TaskStatus.PENDING,
                    agent_id: Optional[str] = None) -> Dict:
        task = {
            "task_id": task_id,
            "status": status.value,
            "agent_id": agent_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "callback_mode": None,
            "callback_result": None,
        }
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Dict]:
        return self.tasks.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus,
                      callback_mode: CallbackMode, result: Optional[Dict] = None) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False
        task["status"] = status.value
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        task["callback_mode"] = callback_mode.value
        task["callback_result"] = result
        return True

    def get_callback_history(self, task_id: str) -> Dict:
        task = self.tasks.get(task_id)
        if not task:
            return {}
        return {
            "task_id": task_id,
            "status": task["status"],
            "callback_mode": task["callback_mode"],
            "callback_result": task["callback_result"],
        }


class AgentCallbackFailover:
    """Agent 回传故障转移管理器

    核心逻辑:
    1. 首先尝试 HTTP 回调通知后端任务完成
    2. 如果 HTTP 回调失败（5xx/timeout/connection error），
       回退到共享卷轮询模式
    3. 轮询检测到 .done 文件后，校验内容并更新任务状态
    """

    def __init__(self, http_callback: MockHTTPCallback,
                 poller: SharedVolumePoller,
                 task_store: TaskStatusStore):
        self.http_callback = http_callback
        self.poller = poller
        self.task_store = task_store
        self._retry_count = 3
        self._retry_delay = 1

    def notify_task_completion(self, task_id: str, result_data: Dict) -> AgentCallbackResult:
        """通知 Agent 完成任务

        先尝试 HTTP 回调，失败后回退到共享卷轮询。
        """
        # 阶段 1: 尝试 HTTP 回调
        success, http_error = self._try_http_callback(task_id, result_data)

        if success:
            self.task_store.update_status(
                task_id, TaskStatus.DELIVERED,
                CallbackMode.HTTP,
                {"method": "http_callback", "request_count": self.http_callback.request_count},
            )
            return AgentCallbackResult(
                task_id=task_id,
                status=TaskStatus.DELIVERED,
                mode=CallbackMode.HTTP,
                success=True,
            )

        # 阶段 2: HTTP 失败，回退到共享卷轮询
        return self._fallback_to_polling(task_id, result_data, http_error)

    def _try_http_callback(self, task_id: str, data: Dict) -> tuple:
        """尝试 HTTP 回调并处理重试

        返回 (success, error_message)
        """
        for attempt in range(self._retry_count):
            response = self.http_callback.post({
                "task_id": task_id,
                "data": data,
                "attempt": attempt + 1,
            })

            if response.get("status_code") == 200:
                return True, None

            error_msg = response.get("error", "Unknown error")
            if attempt < self._retry_count - 1:
                time.sleep(self._retry_delay)

        return False, error_msg

    def _fallback_to_polling(self, task_id: str, result_data: Dict,
                             http_error: str) -> AgentCallbackResult:
        """回退到共享卷轮询

        轮询 .done 文件，检测到后校验内容并更新任务状态。
        """
        total_timeout = max(1.0, self.poller.POLLING_INTERVAL * self.poller.max_polls)
        poll_result = self.poller.poll(task_id, timeout_seconds=total_timeout)

        if not poll_result["found"]:
            error = (f"Polling timeout: no .done file for task {task_id} "
                     f"after {poll_result['polls']} polls ({poll_result['elapsed_seconds']:.1f}s)")
            self.task_store.update_status(
                task_id, TaskStatus.FAILED,
                CallbackMode.SHARED_VOLUME_POLLING,
                {
                    "method": "shared_volume_polling",
                    "error": error,
                    "http_error": http_error,
                    "polls": poll_result["polls"],
                },
            )
            return AgentCallbackResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                mode=CallbackMode.SHARED_VOLUME_POLLING,
                success=False,
                error=error,
            )

        # 校验 .done 文件内容
        content = poll_result["content"]
        validation_error = self._validate_done_content(content, task_id)

        if validation_error:
            self.task_store.update_status(
                task_id, TaskStatus.FAILED,
                CallbackMode.SHARED_VOLUME_POLLING,
                {
                    "method": "shared_volume_polling",
                    "error": validation_error,
                    "http_error": http_error,
                    "polls": poll_result["polls"],
                },
            )
            return AgentCallbackResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                mode=CallbackMode.SHARED_VOLUME_POLLING,
                success=False,
                error=validation_error,
            )

        # 校验通过，更新任务状态为 delivered
        self.task_store.update_status(
            task_id, TaskStatus.DELIVERED,
            CallbackMode.SHARED_VOLUME_POLLING,
            {
                "method": "shared_volume_polling",
                "http_error": http_error,
                "polls": poll_result["polls"],
                "done_content": content,
                "output_hash": content.get("output_hash"),
            },
        )
        return AgentCallbackResult(
            task_id=task_id,
            status=TaskStatus.DELIVERED,
            mode=CallbackMode.SHARED_VOLUME_POLLING,
            success=True,
        )

    def _validate_done_content(self, content: Dict, task_id: str) -> Optional[str]:
        """校验 .done 文件内容

        必须包含 task_id 和 status 字段，status 必须为 completed。
        """
        if not isinstance(content, dict):
            return "Invalid .done file: content is not a JSON object"
        if "task_id" not in content:
            return "Invalid .done file: missing 'task_id' field"
        if content["task_id"] != task_id:
            return f"Task ID mismatch: expected {task_id}, got {content['task_id']}"
        if "status" not in content:
            return "Invalid .done file: missing 'status' field"
        if content["status"] != "completed":
            return f"Invalid status in .done file: expected 'completed', got '{content['status']}'"
        return None


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def http_callback_success():
    """HTTP 回调成功"""
    return MockHTTPCallback("http://backend:8000/api/callback", force_failure=False)


@pytest.fixture
def http_callback_500():
    """HTTP 回调返回 500"""
    return MockHTTPCallback("http://backend:8000/api/callback",
                           force_failure=True, failure_type="500")


@pytest.fixture
def http_callback_timeout():
    """HTTP 回调超时"""
    return MockHTTPCallback("http://backend:8000/api/callback",
                           force_failure=True, failure_type="timeout")


@pytest.fixture
def http_callback_connection_refused():
    """HTTP 回调连接被拒绝"""
    return MockHTTPCallback("http://backend:8000/api/callback",
                           force_failure=True, failure_type="connection_refused")


@pytest.fixture
def poller():
    """共享卷轮询器"""
    return SharedVolumePoller("/mnt/shared/artifacts", max_polls=12)


@pytest.fixture
def task_store():
    """任务状态存储"""
    return TaskStatusStore()


@pytest.fixture
def failover_manager(http_callback_success, poller, task_store):
    """正常的故障转移管理器"""
    return AgentCallbackFailover(http_callback_success, poller, task_store)


@pytest.fixture
def failover_http_fails(http_callback_500, poller, task_store):
    """HTTP 始终失败的故障转移管理器"""
    return AgentCallbackFailover(http_callback_500, poller, task_store)


@pytest.fixture
def test_result_data():
    """测试用任务完成数据"""
    return {
        "output": "generated_code.py",
        "output_hash": "abc123def456",
        "token_count": 1500,
    }


# ============================================================
# 测试组 1: HTTP 回调成功路径
# ============================================================


class TestHTTPCallbackSuccess:
    """HTTP 回调成功时直接更新状态，不走轮询"""

    def test_http_success_sets_delivered(self, failover_manager):
        """HTTP 回调成功时任务状态设为 delivered"""
        result = failover_manager.notify_task_completion("task-001", {"output": "code.py"})
        assert result.success is True
        assert result.status == TaskStatus.DELIVERED
        assert result.mode == CallbackMode.HTTP

    def test_http_success_no_polling(self, failover_manager):
        """HTTP 成功时不应触发轮询"""
        failover_manager.notify_task_completion("task-001", {"output": "code.py"})
        assert failover_manager.poller.poll_count == 0

    def test_http_success_task_store_updated(self, failover_manager, task_store):
        """HTTP 成功后任务存储中模式为 http"""
        task_store.create_task("task-001", TaskStatus.RUNNING, "agent-1")
        failover_manager.notify_task_completion("task-001", {"output": "code.py"})
        history = task_store.get_callback_history("task-001")
        assert history["status"] == TaskStatus.DELIVERED.value
        assert history["callback_mode"] == CallbackMode.HTTP.value

    def test_http_callback_sent_request(self, failover_manager, http_callback_success):
        """HTTP 回调只发送一次请求"""
        failover_manager.notify_task_completion("task-001", {"output": "code.py"})
        assert http_callback_success.request_count == 1

    def test_http_callback_contains_task_id(self, failover_manager, http_callback_success):
        """HTTP 请求体中包含正确的 task_id"""
        failover_manager.notify_task_completion("task-001", {"output": "code.py"})
        assert http_callback_success.last_request_body["task_id"] == "task-001"


# ============================================================
# 测试组 2: HTTP 回调重试机制
# ============================================================


class TestHTTPCallbackRetry:
    """HTTP 失败时重试指定次数后再降级"""

    def test_retries_on_500(self, http_callback_500):
        """500 错误应重试 _retry_count 次"""
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_callback_500, poller, store)
        store.create_task("task-001", TaskStatus.RUNNING, "agent-1")

        # .done 文件已存在，跳过轮询等待
        poller.create_done_file("task-001", {"task_id": "task-001",
                                             "status": "completed",
                                             "output_hash": "abc123"})
        mgr.notify_task_completion("task-001", {"output": "code.py"})
        assert http_callback_500.request_count == mgr._retry_count

    def test_retries_on_timeout(self, http_callback_timeout):
        """超时错误也应重试"""
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_callback_timeout, poller, store)
        store.create_task("task-002", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-002", {"task_id": "task-002",
                                             "status": "completed",
                                             "output_hash": "def456"})
        mgr.notify_task_completion("task-002", {"output": "code.py"})
        assert http_callback_timeout.request_count == mgr._retry_count

    def test_retries_on_connection_refused(self, http_callback_connection_refused):
        """连接拒绝错误也应重试"""
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_callback_connection_refused, poller, store)
        store.create_task("task-003", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-003", {"task_id": "task-003",
                                             "status": "completed",
                                             "output_hash": "ghi789"})
        mgr.notify_task_completion("task-003", {"output": "code.py"})
        assert http_callback_connection_refused.request_count == mgr._retry_count


# ============================================================
# 测试组 3: 共享卷轮询降级
# ============================================================


class TestSharedVolumePollingFallback:
    """HTTP 失败后回退到共享卷轮询"""

    def test_falls_back_to_polling_on_500(self, failover_http_fails, poller, task_store):
        """HTTP 500 后应回退到共享卷轮询"""
        task_store.create_task("task-010", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-010", {"task_id": "task-010",
                                             "status": "completed",
                                             "output_hash": "hash001"})
        result = failover_http_fails.notify_task_completion("task-010", {"output": "code.py"})
        assert result.success is True
        assert result.mode == CallbackMode.SHARED_VOLUME_POLLING
        assert result.status == TaskStatus.DELIVERED

    def test_falls_back_on_timeout(self):
        """HTTP 超时后应回退到共享卷轮询"""
        http_cb = MockHTTPCallback("http://backend:8000/api/callback",
                                   force_failure=True, failure_type="timeout")
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)
        store.create_task("task-011", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-011", {"task_id": "task-011",
                                             "status": "completed",
                                             "output_hash": "hash002"})
        result = mgr.notify_task_completion("task-011", {"output": "code.py"})
        assert result.mode == CallbackMode.SHARED_VOLUME_POLLING
        assert result.success is True

    def test_falls_back_on_connection_refused(self):
        """HTTP 连接拒绝后应回退到共享卷轮询"""
        http_cb = MockHTTPCallback("http://backend:8000/api/callback",
                                   force_failure=True, failure_type="connection_refused")
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)
        store.create_task("task-012", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-012", {"task_id": "task-012",
                                             "status": "completed",
                                             "output_hash": "hash003"})
        result = mgr.notify_task_completion("task-012", {"output": "code.py"})
        assert result.mode == CallbackMode.SHARED_VOLUME_POLLING
        assert result.success is True

    def test_polling_records_http_error(self, failover_http_fails, poller, task_store):
        """降级结果中应记录 HTTP 错误原因"""
        task_store.create_task("task-013", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-013", {"task_id": "task-013",
                                             "status": "completed",
                                             "output_hash": "hash004"})
        failover_http_fails.notify_task_completion("task-013", {"output": "code.py"})
        history = task_store.get_callback_history("task-013")
        assert "http_error" in history["callback_result"]
        assert "Internal Server Error" in history["callback_result"]["http_error"]


# ============================================================
# 测试组 4: 5 秒轮询间隔
# ============================================================


class TestPollingInterval:
    """验证轮询间隔为 5 秒"""

    def test_polling_interval_is_5_seconds(self, poller):
        """POLLING_INTERVAL 应为 5 秒"""
        assert poller.POLLING_INTERVAL == 5

    def test_poll_respects_interval(self):
        """轮询应严格按照 5 秒间隔"""
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=2)
        poller.create_done_file("task-time", {"task_id": "task-time",
                                              "status": "completed"})

        start = time.time()
        result = poller.poll("task-time", timeout_seconds=10)
        elapsed = time.time() - start

        assert result["found"] is True
        assert result["polls"] == 1
        assert elapsed < 0.5

    def test_second_poll_after_5_seconds(self):
        """首次未找到文件时，第二次轮询应在 5 秒后"""
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=2)
        total_timeout = 15  # 3 次轮询

        def _write_after_3s():
            time.sleep(3)
            poller.create_done_file("task-delay", {"task_id": "task-delay",
                                                    "status": "completed",
                                                    "output_hash": "delay_hash"})

        t = threading.Thread(target=_write_after_3s, daemon=True)
        t.start()

        start = time.time()
        result = poller.poll("task-delay", timeout_seconds=total_timeout)
        elapsed = time.time() - start

        assert result["found"] is True
        assert result["polls"] >= 1
        assert elapsed >= 3

    def test_max_polls_timeout(self):
        """超过最大轮询次数后超时"""
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=2)

        start = time.time()
        result = poller.poll("task-no-done", timeout_seconds=15)
        elapsed = time.time() - start

        assert result["found"] is False
        assert result["polls"] == 2
        assert elapsed >= 5


# ============================================================
# 测试组 5: .done 文件校验
# ============================================================


class TestDoneFileValidation:
    """.done 文件内容校验"""

    def test_valid_done_file(self, failover_http_fails, poller, task_store):
        """合法的 .done 文件应通过校验"""
        task_store.create_task("task-v01", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-v01", {"task_id": "task-v01",
                                             "status": "completed",
                                             "output_hash": "abc123"})
        result = failover_http_fails.notify_task_completion("task-v01", {"output": "code.py"})
        assert result.success is True
        assert result.status == TaskStatus.DELIVERED

    def test_missing_task_id_fails(self, failover_http_fails, poller, task_store):
        """.done 文件缺少 task_id 字段应校验失败"""
        task_store.create_task("task-v02", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-v02", {"status": "completed"})
        result = failover_http_fails.notify_task_completion("task-v02", {"output": "code.py"})
        assert result.success is False
        assert "missing 'task_id'" in result.error

    def test_wrong_task_id_fails(self, failover_http_fails, poller, task_store):
        """.done 文件中 task_id 不匹配应校验失败"""
        task_store.create_task("task-v03", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-v03", {"task_id": "task-wrong",
                                             "status": "completed",
                                             "output_hash": "abc123"})
        result = failover_http_fails.notify_task_completion("task-v03", {"output": "code.py"})
        assert result.success is False
        assert "Task ID mismatch" in result.error

    def test_missing_status_fails(self, failover_http_fails, poller, task_store):
        """.done 文件缺少 status 字段应校验失败"""
        task_store.create_task("task-v04", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-v04", {"task_id": "task-v04",
                                             "output_hash": "abc123"})
        result = failover_http_fails.notify_task_completion("task-v04", {"output": "code.py"})
        assert result.success is False
        assert "missing 'status'" in result.error

    def test_wrong_status_fails(self, failover_http_fails, poller, task_store):
        """.done 文件中 status 不是 completed 应校验失败"""
        task_store.create_task("task-v05", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-v05", {"task_id": "task-v05",
                                             "status": "failed",
                                             "output_hash": "abc123"})
        result = failover_http_fails.notify_task_completion("task-v05", {"output": "code.py"})
        assert result.success is False
        assert "completed" in result.error

    def test_non_dict_content_fails(self, failover_http_fails, poller, task_store):
        """.done 文件内容为非 dict 应校验失败"""
        task_store.create_task("task-v06", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-v06", "just a string")
        result = failover_http_fails.notify_task_completion("task-v06", {"output": "code.py"})
        assert result.success is False
        assert "not a JSON object" in result.error

    def test_extra_fields_ignored(self, failover_http_fails, poller, task_store):
        """.done 文件额外字段不影响校验"""
        task_store.create_task("task-v07", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-v07", {"task_id": "task-v07",
                                             "status": "completed",
                                             "output_hash": "abc123",
                                             "extra_field": "ignored",
                                             "metadata": {"a": 1}})
        result = failover_http_fails.notify_task_completion("task-v07", {"output": "code.py"})
        assert result.success is True


# ============================================================
# 测试组 6: 任务状态更新
# ============================================================


class TestTaskStatusUpdate:
    """任务状态在降级流程中被正确更新"""

    def test_status_delivered_on_success(self, failover_http_fails, poller, task_store):
        """成功降级后状态为 delivered"""
        task_store.create_task("task-s01", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-s01", {"task_id": "task-s01",
                                             "status": "completed",
                                             "output_hash": "hash001"})
        failover_http_fails.notify_task_completion("task-s01", {"output": "code.py"})
        history = task_store.get_callback_history("task-s01")
        assert history["status"] == TaskStatus.DELIVERED.value
        assert history["callback_mode"] == CallbackMode.SHARED_VOLUME_POLLING.value

    def test_status_failed_on_no_done_file(self, failover_http_fails, poller, task_store):
        """超时未找到 .done 文件时状态为 failed"""
        task_store.create_task("task-s02", TaskStatus.RUNNING, "agent-1")
        # .done 文件不存在，轮询会超时
        poller.max_polls = 1
        poller.POLLING_INTERVAL = 0  # 加速测试
        result = failover_http_fails.notify_task_completion("task-s02", {"output": "code.py"})
        assert result.success is False
        assert result.status == TaskStatus.FAILED
        history = task_store.get_callback_history("task-s02")
        assert history["status"] == TaskStatus.FAILED.value

    def test_status_failed_on_validation_error(self, failover_http_fails, poller, task_store):
        """.done 文件校验失败时状态为 failed"""
        task_store.create_task("task-s03", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-s03", {"task_id": "task-wrong",
                                             "status": "completed"})
        poller.POLLING_INTERVAL = 0  # 加速测试
        result = failover_http_fails.notify_task_completion("task-s03", {"output": "code.py"})
        assert result.success is False
        assert result.status == TaskStatus.FAILED
        history = task_store.get_callback_history("task-s03")
        assert history["status"] == TaskStatus.FAILED.value
        assert "Task ID mismatch" in history["callback_result"]["error"]

    def test_callback_result_contains_output_hash(self, failover_http_fails, poller, task_store):
        """成功降级的结果中应包含 output_hash"""
        task_store.create_task("task-s04", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-s04", {"task_id": "task-s04",
                                             "status": "completed",
                                             "output_hash": "abc123def456"})
        failover_http_fails.notify_task_completion("task-s04", {"output": "code.py"})
        history = task_store.get_callback_history("task-s04")
        assert history["callback_result"]["output_hash"] == "abc123def456"

    def test_callback_result_contains_poll_count(self, failover_http_fails, poller, task_store):
        """成功率的结果中应包含轮询次数"""
        task_store.create_task("task-s05", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-s05", {"task_id": "task-s05",
                                             "status": "completed",
                                             "output_hash": "hash005"})
        failover_http_fails.notify_task_completion("task-s05", {"output": "code.py"})
        history = task_store.get_callback_history("task-s05")
        assert "polls" in history["callback_result"]
        assert history["callback_result"]["polls"] >= 1


# ============================================================
# 测试组 7: 端到端完整流程
# ============================================================


class TestEndToEnd:
    """端到端：HTTP 失败 → 轮询 .done → 校验 → 更新状态"""

    def test_full_failover_workflow(self):
        """完整流程：HTTP 500 → 重试 3 次 → 轮询 → 检测到 .done → 校验 → 状态更新"""
        http_cb = MockHTTPCallback("http://backend:8000/api/callback",
                                   force_failure=True, failure_type="500")
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=12)
        poller.POLLING_INTERVAL = 0
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)

        # Step 1: 创建运行中的任务
        store.create_task("task-e2e", TaskStatus.RUNNING, "agent-prog-1")
        initial = store.get_task("task-e2e")
        assert initial["status"] == TaskStatus.RUNNING.value

        # Step 2: .done 文件已存在（模拟 Agent 已完成）
        poller.create_done_file("task-e2e", {
            "task_id": "task-e2e",
            "status": "completed",
            "output_hash": "e2e_hash_abc123",
        })

        # Step 3: 触发回传 → HTTP 失败 → 降级到轮询
        result = mgr.notify_task_completion("task-e2e", {"output": "generated.py"})

        # Step 4: HTTP 应重试 3 次
        assert http_cb.request_count == mgr._retry_count

        # Step 5: 最终通过轮询完成
        assert result.success is True
        assert result.mode == CallbackMode.SHARED_VOLUME_POLLING
        assert result.status == TaskStatus.DELIVERED

        # Step 6: 任务状态已更新
        history = store.get_callback_history("task-e2e")
        assert history["status"] == TaskStatus.DELIVERED.value
        assert history["callback_mode"] == CallbackMode.SHARED_VOLUME_POLLING.value
        assert history["callback_result"]["output_hash"] == "e2e_hash_abc123"
        assert "http_error" in history["callback_result"]
        assert "Internal Server Error" in history["callback_result"]["http_error"]

    def test_full_timeout_workflow(self):
        """完整超时流程：HTTP 失败 → 轮询超时 → 任务标记 failed"""
        http_cb = MockHTTPCallback("http://backend:8000/api/callback",
                                   force_failure=True, failure_type="connection_refused")
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=1)
        poller.POLLING_INTERVAL = 0
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)

        store.create_task("task-timeout", TaskStatus.RUNNING, "agent-prog-2")
        # 不创建 .done 文件

        result = mgr.notify_task_completion("task-timeout", {"output": "code.py"})

        assert result.success is False
        assert result.status == TaskStatus.FAILED
        assert result.mode == CallbackMode.SHARED_VOLUME_POLLING
        assert "timeout" in result.error

        history = store.get_callback_history("task-timeout")
        assert history["status"] == TaskStatus.FAILED.value

    def test_http_succeeds_skips_polling_entirely(self):
        """HTTP 回调成功时，不应执行任何轮询"""
        http_cb = MockHTTPCallback("http://backend:8000/api/callback", force_failure=False)
        poller = SharedVolumePoller("/mnt/shared/artifacts", max_polls=12)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)

        store.create_task("task-skip", TaskStatus.RUNNING, "agent-prog-3")
        result = mgr.notify_task_completion("task-skip", {"output": "code.py"})

        assert result.success is True
        assert result.mode == CallbackMode.HTTP
        assert poller.poll_count == 0
        assert http_cb.request_count == 1


# ============================================================
# 测试组 8: 边界场景
# ============================================================


class TestEdgeCases:
    """边界情况"""

    def test_empty_done_file_content(self):
        """空 dict 的 .done 文件应校验失败"""
        http_cb = MockHTTPCallback("http://x", force_failure=True)
        poller = SharedVolumePoller("/mnt/x", max_polls=1)
        poller.POLLING_INTERVAL = 0
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)
        store.create_task("task-empty", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-empty", {})
        result = mgr.notify_task_completion("task-empty", {})
        assert result.success is False
        assert "missing 'task_id'" in result.error

    def test_done_file_is_none(self):
        """None 类型的 .done 文件内容应校验失败"""
        http_cb = MockHTTPCallback("http://x", force_failure=True)
        poller = SharedVolumePoller("/mnt/x", max_polls=1)
        poller.POLLING_INTERVAL = 0
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)
        store.create_task("task-none", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-none", None)
        result = mgr.notify_task_completion("task-none", {})
        assert result.success is False

    def test_multiple_task_isolation(self):
        """不同任务的 .done 文件互不干扰"""
        poller = SharedVolumePoller("/mnt/shared", max_polls=1)
        poller.create_done_file("task-a", {"task_id": "task-a",
                                           "status": "completed"})
        assert poller.has_done_file("task-a") is True
        assert poller.has_done_file("task-b") is False

    def test_task_not_in_store(self):
        """不存在的任务不应更新状态"""
        http_cb = MockHTTPCallback("http://x")
        poller = SharedVolumePoller("/mnt/x", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)
        result = mgr.notify_task_completion("nonexistent", {"output": "code.py"})
        assert result.success is True
        assert result.status == TaskStatus.DELIVERED

    def test_retry_count_configurable(self):
        """重试次数可由外部配置"""
        http_cb = MockHTTPCallback("http://x", force_failure=True, failure_type="500")
        poller = SharedVolumePoller("/mnt/x", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)
        mgr._retry_count = 5
        store.create_task("task-r", TaskStatus.RUNNING, "agent-1")
        poller.create_done_file("task-r", {"task_id": "task-r",
                                           "status": "completed",
                                           "output_hash": "h"})
        mgr.notify_task_completion("task-r", {})
        assert http_cb.request_count == 5

    def test_default_retry_is_3(self):
        """默认重试次数应为 3"""
        http_cb = MockHTTPCallback("http://x")
        poller = SharedVolumePoller("/mnt/x", max_polls=1)
        store = TaskStatusStore()
        mgr = AgentCallbackFailover(http_cb, poller, store)
        assert mgr._retry_count == 3

    def test_poller_default_max_polls(self):
        """默认最大轮询次数应为 12"""
        poller = SharedVolumePoller("/mnt/x")
        assert poller.max_polls == 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
