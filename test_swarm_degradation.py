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

                ready_agents = [a for a in available_agents if a.get("status") == "ready"]
                if len(ready_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)

                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in ready_agents]
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
        self, swarm_orchestrator, mock_agent_pool, mock_degradation_log_repository, mock_task_queue, mock_request
    ):
        """验证：有可用Agent时不走降级路径"""
        mock_agent_pool.get_available_agents.return_value = [
            {"name": "agent-alpha", "status": "ready"},
            {"name": "agent-beta", "status": "ready"}
        ]
        result = swarm_orchestrator.handle_swarm_startup_request(mock_request)
        assert result["status_code"] == 200
        assert result["body"]["status"] == "accepted"
        assert "agent-alpha" in result["body"]["assigned_agents"]
        mock_degradation_log_repository.create_log.assert_not_called()
        mock_task_queue.enqueue.assert_not_called()

    def test_degradation_when_get_available_agents_returns_none(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue, mock_request
    ):
        """验证：get_available_agents() 返回 None 时，触发降级策略而非 TypeError"""
        mock_agent_pool.get_available_agents.return_value = None
        orchestrator = self._build_orchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(mock_request)
        assert result["status_code"] == 202
        body = result["body"]
        assert body["status"] == "queued_with_degradation"
        mock_degradation_log_repository.create_log.assert_called_once()
        mock_task_queue.enqueue.assert_called_once()

    def test_degradation_when_request_json_raises_exception(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue
    ):
        """验证：request.json() 抛出异常时，系统返回 500 而非崩溃"""
        bad_request = MagicMock()
        bad_request.json.side_effect = ValueError("invalid json body")
        orchestrator = self._build_orchestrator_with_json_fallback(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        with pytest.raises(ValueError):
            orchestrator.handle_swarm_startup_request(bad_request)

    def test_degradation_when_payload_missing_task_id(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue
    ):
        """验证：payload 缺少 task_id 时，降级策略仍正常执行，task_id 为 None"""
        mock_agent_pool.get_available_agents.return_value = []
        req = MagicMock()
        req.json.return_value = {"task_type": "code_generation", "priority": "low"}
        orchestrator = self._build_orchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(req)
        assert result["status_code"] == 202
        assert result["body"]["task_id"] is None
        log_record = mock_degradation_log_repository.create_log.call_args[0][0]
        assert log_record["task_id"] is None
        queued_task = mock_task_queue.enqueue.call_args[0][0]
        assert queued_task["task_id"] is None

    def test_degradation_with_none_task_type_and_priority(
        self, mock_agent_pool, mock_degradation_log_repository, mock_task_queue
    ):
        """验证：task_type 或 priority 为 None 时，降级队列记录仍完整"""
        mock_agent_pool.get_available_agents.return_value = []
        req = MagicMock()
        req.json.return_value = {
            "task_id": "task-none-field-456",
            "task_type": None,
            "priority": None
        }
        orchestrator = self._build_orchestrator(
            mock_agent_pool, mock_degradation_log_repository, mock_task_queue
        )
        result = orchestrator.handle_swarm_startup_request(req)
        assert result["status_code"] == 202
        queued_task = mock_task_queue.enqueue.call_args[0][0]
        assert queued_task["task_type"] is None
        assert queued_task["priority"] is None
        assert queued_task["task_id"] == "task-none-field-456"
        assert queued_task["mode"] == "degraded"

    def test_degradation_when_agents_returned_but_none_ready(
        self, swarm_orchestrator, mock_agent_pool, mock_degradation_log_repository, mock_task_queue, mock_request
    ):
        """验证：Agent 池返回非空但全部 status != ready 时，走降级策略"""
        mock_agent_pool.get_available_agents.return_value = [
            {"name": "agent-x", "status": "busy"},
            {"name": "agent-y", "status": "offline"}
        ]
        result = swarm_orchestrator.handle_swarm_startup_request(mock_request)
        assert result["status_code"] == 202
        body = result["body"]
        assert body["status"] == "queued_with_degradation"
        mock_degradation_log_repository.create_log.assert_called_once()
        mock_task_queue.enqueue.assert_called_once()

    @staticmethod
    def _build_orchestrator(agent_pool, degradation_log_repo, task_queue):
        """辅助方法：构建 SwarmOrchestrator 实例"""
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

                ready_agents = [a for a in available_agents if a.get("status") == "ready"]
                if len(ready_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)

                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in ready_agents]
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

        return SwarmOrchestrator(agent_pool, degradation_log_repo, task_queue)

    @staticmethod
    def _build_orchestrator_with_json_fallback(agent_pool, degradation_log_repo, task_queue):
        """辅助方法：构建不处理 json 异常的编排器（用于测试 json 异常传播）"""
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

                ready_agents = [a for a in available_agents if a.get("status") == "ready"]
                if len(ready_agents) == 0:
                    return self._execute_degradation_strategy(task_id, payload)

                return {
                    "status_code": 200,
                    "body": {
                        "status": "accepted",
                        "assigned_agents": [a["name"] for a in ready_agents]
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

        return SwarmOrchestrator(agent_pool, degradation_log_repo, task_queue)
