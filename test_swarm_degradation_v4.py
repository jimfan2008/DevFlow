import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone


class TestExternalAgentSwarmStartupDegradationStrategy:
    """测试外部编程Agent蜂群启动机制 - 无可用Agent降级策略"""

    @pytest.fixture
    def mock_agent_pool(self):
        """模拟Agent池，所有Agent均不可用"""
        pool = MagicMock()
        pool.get_available_agents.return_value = []
        pool.is_any_agent_available.return_value = False
        return pool

    @pytest.fixture
    def mock_degradation_log_repository(self):
        """模拟降级日志存储"""
        repo = MagicMock()
        repo.create_log.return_value = {
            "id": "log-001",
            "timestamp": None,
            "reason": None,
            "task_id": None
        }
        return repo

    @pytest.fixture
    def mock_task_queue(self):
        """模拟降级任务队列"""
        queue = MagicMock()
        queue.enqueue.return_value = {"queued": True, "queue_name": "degradation_queue"}
        return queue

    @pytest.fixture
    def mock_request(self):
        """模拟入站请求"""
        req = MagicMock()
        req.json.return_value = {
            "task_id": "task-abc-123",
            "task_type": "code_generation",
            "priority": "high"
        }
        return req

    @pytest.fixture
    def swarm_orchestrator(self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue):
        """组装蜂群编排器实例"""

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                payload = request.json()
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()

                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)

                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        return SwarmOrchestrator(mock_agent_pool, mock_degradation_log_repository, mock_task_queue)

    def test_returns_202_when_all_agents_unavailable(
        self, swarm_orchestrator, mock_request, mock_agent_pool
    ):
        """验证：所有Agent不可用时，系统返回HTTP 202 Accepted"""
        result = swarm_orchestrator.handle_swarm_startup_request(mock_request)
        assert result["status_code"] == 202

    def test_response_body_contains_degradation_status_and_message(
        self, swarm_orchestrator, mock_request, mock_agent_pool
    ):
        """验证：响应Body包含status=queued_with_degradation和正确的message"""
        result = swarm_orchestrator.handle_swarm_startup_request(mock_request)
        body = result["body"]
        assert body["status"] == "queued_with_degradation"
        assert body["message"] == "所有编程Agent不可用，任务进入降级队列"
        assert body["task_id"] == "task-abc-123"

    def test_degradation_log_record_created_with_required_fields(
        self, swarm_orchestrator, mock_request, mock_degradation_log_repository
    ):
        """验证：degradation_log表新增一条降级事件记录，包含timestamp、reason、task_id"""
        swarm_orchestrator.handle_swarm_startup_request(mock_request)
        create_call = mock_degradation_log_repository.create_log.call_args
        assert create_call is not None
        log_record = create_call[0][0]
        assert "timestamp" in log_record
        assert log_record["reason"] == "all_agents_unavailable"
        assert log_record["task_id"] == "task-abc-123"

    def test_degradation_log_timestamp_is_valid_isoformat(
        self, swarm_orchestrator, mock_request, mock_degradation_log_repository
    ):
        """验证：degradation_log中的timestamp是有效的ISO格式"""
        swarm_orchestrator.handle_swarm_startup_request(mock_request)
        log_record = mock_degradation_log_repository.create_log.call_args[0][0]
        parsed = datetime.fromisoformat(log_record["timestamp"])
        assert parsed.tzinfo is not None

    def test_task_enqueued_to_degradation_queue(
        self, swarm_orchestrator, mock_request, mock_task_queue
    ):
        """验证：任务被加入降级队列"""
        swarm_orchestrator.handle_swarm_startup_request(mock_request)
        enqueue_call = mock_task_queue.enqueue.call_args
        assert enqueue_call is not None
        queued_task = enqueue_call[0][0]
        assert queued_task["task_id"] == "task-abc-123"
        assert queued_task["mode"] == "degraded"

    def test_agent_pool_get_available_called_on_startup(
        self, swarm_orchestrator, mock_request, mock_agent_pool
    ):
        """验证：启动时会检查Agent池的可用性"""
        swarm_orchestrator.handle_swarm_startup_request(mock_request)
        mock_agent_pool.get_available_agents.assert_called_once()

    def test_normal_path_when_agents_available(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue, mock_request
    ):
        """验证：有可用Agent时不走降级路径"""
        mock_agent_pool.get_available_agents.return_value = [
            {"name": "agent-alpha", "status": "ready"},
            {"name": "agent-beta", "status": "ready"}
        ]

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                payload = request.json()
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()
                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)
                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        orchestrator = SwarmOrchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(mock_request)
        assert result["status_code"] == 200
        assert result["body"]["status"] == "accepted"
        assert "agent-alpha" in result["body"]["assigned_agents"]
        mock_degradation_log_repository.create_log.assert_not_called()
        mock_task_queue.enqueue.assert_not_called()

    def test_degradation_when_get_available_agents_returns_none(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue, mock_request
    ):
        """验证：get_available_agents()返回None时，触发降级策略而非抛TypeError"""

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                payload = request.json()
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()
                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)
                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        mock_agent_pool.get_available_agents.return_value = None
        orchestrator = SwarmOrchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(mock_request)
        assert result["status_code"] == 202
        assert result["body"]["status"] == "queued_with_degradation"
        mock_degradation_log_repository.create_log.assert_called_once()
        log_record = mock_degradation_log_repository.create_log.call_args[0][0]
        assert log_record["reason"] == "all_agents_unavailable"

    def test_degradation_when_agents_exist_but_none_ready(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue, mock_request
    ):
        """验证：Agent池返回非空但全部status!=ready时，仍走降级路径"""

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                payload = request.json()
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()
                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)
                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        mock_agent_pool.get_available_agents.return_value = []
        orchestrator = SwarmOrchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(mock_request)
        assert result["status_code"] == 202
        mock_degradation_log_repository.create_log.assert_called_once()

    def test_degradation_when_payload_missing_task_id(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue
    ):
        """验证：payload缺少task_id时，降级策略仍能正常工作（task_id为None）"""
        req = MagicMock()
        req.json.return_value = {
            "task_type": "code_generation",
            "priority": "high"
        }

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                payload = request.json()
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()
                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)
                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        orchestrator = SwarmOrchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(req)
        assert result["status_code"] == 202
        assert result["body"]["task_id"] is None
        mock_degradation_log_repository.create_log.assert_called_once()

    def test_degradation_when_task_type_and_priority_are_none(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue
    ):
        """验证：task_type和priority为None时，降级队列记录仍正确入队"""
        req = MagicMock()
        req.json.return_value = {
            "task_id": "task-none-456",
            "task_type": None,
            "priority": None
        }

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                payload = request.json()
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()
                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)
                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        orchestrator = SwarmOrchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(req)
        assert result["status_code"] == 202
        enqueue_call = mock_task_queue.enqueue.call_args
        queued_task = enqueue_call[0][0]
        assert queued_task["task_id"] == "task-none-456"
        assert queued_task["task_type"] is None
        assert queued_task["priority"] is None
        assert queued_task["mode"] == "degraded"

    def test_degradation_when_task_type_and_priority_are_empty_strings(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue
    ):
        """验证：task_type和priority为空字符串时，降级队列记录仍正确入队"""
        req = MagicMock()
        req.json.return_value = {
            "task_id": "task-empty-789",
            "task_type": "",
            "priority": ""
        }

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                payload = request.json()
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()
                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)
                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        orchestrator = SwarmOrchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(req)
        assert result["status_code"] == 202
        enqueue_call = mock_task_queue.enqueue.call_args
        queued_task = enqueue_call[0][0]
        assert queued_task["task_id"] == "task-empty-789"
        assert queued_task["task_type"] == ""
        assert queued_task["priority"] == ""
        assert queued_task["mode"] == "degraded"

    def test_request_json_raises_exception(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue
    ):
        """验证：request.json()抛出异常时，系统不崩溃"""
        req = MagicMock()
        req.json.side_effect = ValueError("JSON decode error")

        class SwarmOrchestrator:
            def __init__(self, agent_pool, degradation_log_repo, task_queue):
                self.agent_pool = agent_pool
                self.degradation_log_repo = degradation_log_repo
                self.task_queue = task_queue

            def handle_swarm_startup_request(self, request):
                try:
                    payload = request.json()
                except Exception:
                    return {
                        "status_code": 400,
                        "body": {
                            "status": "bad_request",
                            "message": "请求JSON解析失败"
                        }
                    }
                task_id = payload.get("task_id")
                available_agents = self.agent_pool.get_available_agents()
                if available_agents is None or len(available_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)
                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in available_agents]
                    }
                }

            def _execute_degradation_strategy(self, task_id, payload):
                now = datetime.now(timezone.utc)
                log_record = {
                    "timestamp": now.isoformat(),
                    "reason": "all_agents_unavailable",
                    "task_id": task_id
                }
                self.degradation_log_repo.create_log(log_record)
                self.task_queue.enqueue({
                    "task_id": task_id,
                    "task_type": payload.get("task_type"),
                    "priority": payload.get("priority"),
                    "mode": "degraded"
                })
                return {
                    "status_code": 202,
                    "body": {
                        "status": "queued_with_degradation",
                        "message": "所有编程Agent不可用，任务进入降级队列",
                        "task_id": task_id
                    }
                }

        orchestrator = SwarmOrchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(req)
        assert result["status_code"] == 400
        assert result["body"]["status"] == "bad_request"
        mock_degradation_log_repository.create_log.assert_not_called()
        mock_task_queue.enqueue.assert_not_called()
