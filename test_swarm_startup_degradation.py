import pytest
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel


# ─── 领域模型 ───────────────────────────────────────────


class AgentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


@dataclass
class ProgrammingAgentProfile:
    """外部编程 Agent Profile"""
    name: str
    agent_type: str
    status: AgentStatus = AgentStatus.OFFLINE
    api_endpoint: Optional[str] = None
    config: dict = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.status == AgentStatus.ONLINE


@dataclass
class DegradationLog:
    """降级事件记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    task_id: Optional[str] = None
    details: Optional[str] = None


@dataclass
class DegradationQueueEntry:
    """降级队列条目"""
    task_id: str
    project_id: str
    task_description: str
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "queued_with_degradation"


# ─── 模拟的 Profile 扫描服务 ─────────────────────────────


class MockProfileScannerService:
    """模拟 Profile 扫描服务"""

    def __init__(self):
        self._profiles: List[ProgrammingAgentProfile] = []

    def set_profiles(self, profiles: List[ProgrammingAgentProfile]) -> None:
        self._profiles = list(profiles)

    def get_all_profiles(self) -> List[ProgrammingAgentProfile]:
        return list(self._profiles)

    def get_available_programming_agents(self) -> List[ProgrammingAgentProfile]:
        return [p for p in self._profiles if p.is_available]

    def get_all_programming_agent_types(self) -> List[str]:
        return list({p.agent_type for p in self._profiles})


# ─── 降级日志存储服务 ────────────────────────────────────


class DegradationLogStore:
    """降级日志存储（内存）"""

    def __init__(self):
        self._logs: List[DegradationLog] = []

    def add(self, log: DegradationLog) -> DegradationLog:
        self._logs.append(log)
        return log

    def get_all(self) -> List[DegradationLog]:
        return list(self._logs)

    def find_by_task_id(self, task_id: str) -> Optional[DegradationLog]:
        for log in self._logs:
            if log.task_id == task_id:
                return log
        return None

    def find_by_reason(self, reason: str) -> List[DegradationLog]:
        return [log for log in self._logs if log.reason == reason]


# ─── 降级队列服务 ────────────────────────────────────────


class DegradationQueue:
    """降级任务队列"""

    def __init__(self):
        self._queue: List[DegradationQueueEntry] = []

    def enqueue(self, entry: DegradationQueueEntry) -> DegradationQueueEntry:
        self._queue.append(entry)
        return entry

    def get_all(self) -> List[DegradationQueueEntry]:
        return list(self._queue)

    def size(self) -> int:
        return len(self._queue)


# ─── 蜂群启动服务 ────────────────────────────────────────


class SwarmStartupService:
    """外部编程 Agent 蜂群启动服务"""

    # 支持的编程 Agent 类型
    SUPPORTED_PROGRAMMING_AGENT_TYPES = [
        "claude_code", "opencode", "codearts", "trae",
        "hermes_sub_agent", "pi_coding_agent", "reasonix",
        "houfa", "aider-chat", "openhands", "goose",
    ]

    def __init__(
        self,
        profile_scanner: MockProfileScannerService,
        log_store: DegradationLogStore,
        degradation_queue: DegradationQueue,
    ):
        self._scanner = profile_scanner
        self._log_store = log_store
        self._queue = degradation_queue

    def start_swarm(
        self, project_id: str, task_id: str, task_description: str
    ) -> dict:
        """
        启动外部编程 Agent 蜂群。
        当所有编程 Agent 不可用时，执行降级策略。
        """
        available_agents = self._scanner.get_available_programming_agents()
        all_profiles = self._scanner.get_all_profiles()

        # 检查是否有可用的编程 Agent
        programming_agents = [
            p for p in all_profiles
            if p.agent_type in self.SUPPORTED_PROGRAMMING_AGENT_TYPES
        ]
        available_programming_agents = [
            p for p in programming_agents if p.is_available
        ]

        if not programming_agents:
            # 没有注册任何编程 Agent Profile
            return self._handle_no_profiles(
                project_id, task_id, task_description
            )

        if not available_programming_agents:
            # 有编程 Agent Profile 但全部不可用
            return self._handle_all_unavailable(
                project_id, task_id, task_description, programming_agents
            )

        # 有可用 Agent，正常启动蜂群
        return self._handle_normal_startup(
            project_id, task_id, task_description, available_programming_agents
        )

    def _handle_no_profiles(
        self, project_id: str, task_id: str, task_description: str
    ) -> dict:
        """没有注册任何编程 Agent Profile"""
        log = DegradationLog(
            timestamp=datetime.now(timezone.utc),
            reason="no_profiles_registered",
            task_id=task_id,
            details=f"项目 {project_id} 没有注册任何编程 Agent Profile",
        )
        self._log_store.add(log)

        entry = DegradationQueueEntry(
            task_id=task_id,
            project_id=project_id,
            task_description=task_description,
        )
        self._queue.enqueue(entry)

        return {
            "status": "queued_with_degradation",
            "message": "未注册任何编程Agent Profile，任务进入降级队列",
            "task_id": task_id,
            "degradation_reason": "no_profiles_registered",
        }

    def _handle_all_unavailable(
        self,
        project_id: str,
        task_id: str,
        task_description: str,
        profiles: List[ProgrammingAgentProfile],
    ) -> dict:
        """所有编程 Agent 不可用"""
        unavailable_names = [p.name for p in profiles]
        log = DegradationLog(
            timestamp=datetime.now(timezone.utc),
            reason="all_agents_unavailable",
            task_id=task_id,
            details=f"所有编程Agent不可用: {', '.join(unavailable_names)}",
        )
        self._log_store.add(log)

        entry = DegradationQueueEntry(
            task_id=task_id,
            project_id=project_id,
            task_description=task_description,
        )
        self._queue.enqueue(entry)

        return {
            "status": "queued_with_degradation",
            "message": "所有编程Agent不可用，任务进入降级队列",
            "task_id": task_id,
            "degradation_reason": "all_agents_unavailable",
            "unavailable_agents": unavailable_names,
        }

    def _handle_normal_startup(
        self,
        project_id: str,
        task_id: str,
        task_description: str,
        available_agents: List[ProgrammingAgentProfile],
    ) -> dict:
        """正常启动蜂群"""
        agent_names = [p.name for p in available_agents]
        return {
            "status": "started",
            "message": "蜂群启动成功",
            "task_id": task_id,
            "assigned_agents": agent_names,
            "agent_count": len(available_agents),
        }


# ─── FastAPI 应用 ────────────────────────────────────────


# 全局服务实例（测试可替换）
_profile_scanner = MockProfileScannerService()
_degradation_log_store = DegradationLogStore()
_degradation_queue = DegradationQueue()
_swarm_startup_service = SwarmStartupService(
    profile_scanner=_profile_scanner,
    log_store=_degradation_log_store,
    degradation_queue=_degradation_queue,
)


app = FastAPI(title="Swarm Degradation Test API")


class SwarmStartupRequest(BaseModel):
    project_id: str
    task_id: str
    task_description: str


@app.post("/api/v1/swarms/startup")
def start_swarm(body: SwarmStartupRequest):
    """启动外部编程 Agent 蜂群"""
    result = _swarm_startup_service.start_swarm(
        project_id=body.project_id,
        task_id=body.task_id,
        task_description=body.task_description,
    )
    if result["status"] == "started":
        return JSONResponse(content=result, status_code=200)
    elif result["status"] == "queued_with_degradation":
        return JSONResponse(content=result, status_code=202)
    raise HTTPException(status_code=500, detail="未知的蜂群启动状态")


@app.get("/api/v1/swarms/degradation-logs")
def get_degradation_logs():
    """获取降级日志"""
    logs = _degradation_log_store.get_all()
    return {
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "reason": log.reason,
                "task_id": log.task_id,
                "details": log.details,
            }
            for log in logs
        ],
        "total": len(logs),
    }


@app.get("/api/v1/swarms/degradation-queue")
def get_degradation_queue():
    """获取降级队列"""
    entries = _degradation_queue.get_all()
    return {
        "entries": [
            {
                "task_id": e.task_id,
                "project_id": e.project_id,
                "task_description": e.task_description,
                "enqueued_at": e.enqueued_at.isoformat(),
                "status": e.status,
            }
            for e in entries
        ],
        "total": _degradation_queue.size(),
    }


# ─── 测试夹具 ────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_services():
    """每次测试前重置服务状态"""
    global _swarm_startup_service
    _profile_scanner.set_profiles([])
    _degradation_log_store._logs.clear()
    _degradation_queue._queue.clear()
    _swarm_startup_service = SwarmStartupService(
        profile_scanner=_profile_scanner,
        log_store=_degradation_log_store,
        degradation_queue=_degradation_queue,
    )
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ─── 测试用例 ────────────────────────────────────────────


class TestSwarmStartupAllAgentsUnavailableDegradation:
    """外部编程Agent蜂群启动机制 - 无可用Agent降级策略"""

    def test_returns_http_202_when_all_agents_unavailable(self, client):
        """验证当所有编程Agent Profile不可用时，系统返回HTTP 202 Accepted"""
        # 设置所有编程 Agent 为 offline / busy 状态
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="opencode-1",
                agent_type="opencode",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="pi-agent-1",
                agent_type="pi_coding_agent",
                status=AgentStatus.BUSY,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-001",
                "task_id": task_id,
                "task_description": "编写用户模块测试代码",
            },
        )

        assert response.status_code == 202

    def test_response_body_contains_queued_with_degradation_status(self, client):
        """验证响应Body包含status=queued_with_degradation"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-001",
                "task_id": task_id,
                "task_description": "编写用户模块测试代码",
            },
        )

        body = response.json()
        assert body["status"] == "queued_with_degradation"

    def test_response_body_contains_degradation_message(self, client):
        """验证响应Body包含message=所有编程Agent不可用，任务进入降级队列"""
        profiles = [
            ProgrammingAgentProfile(
                name="goose-1",
                agent_type="goose",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="openhands-1",
                agent_type="openhands",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-002",
                "task_id": task_id,
                "task_description": "编写订单服务接口",
            },
        )

        body = response.json()
        assert body["message"] == "所有编程Agent不可用，任务进入降级队列"

    def test_degradation_log_entry_created_with_required_fields(self, client):
        """验证degradation_log表新增一条降级事件记录，包含timestamp、reason、task_id"""
        profiles = [
            ProgrammingAgentProfile(
                name="pi-agent-1",
                agent_type="pi_coding_agent",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="reasonix-1",
                agent_type="reasonix",
                status=AgentStatus.BUSY,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-003",
                "task_id": task_id,
                "task_description": "编写登录模块",
            },
        )

        # 检查降级日志
        logs = _degradation_log_store.get_all()
        assert len(logs) == 1

        log = logs[0]
        assert log.timestamp is not None
        assert isinstance(log.timestamp, datetime)
        assert log.reason == "all_agents_unavailable"
        assert log.task_id == task_id

    def test_degradation_log_reason_is_all_agents_unavailable(self, client):
        """验证降级日志的reason字段为all_agents_unavailable"""
        profiles = [
            ProgrammingAgentProfile(
                name="trae-1",
                agent_type="trae",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-004",
                "task_id": task_id,
                "task_description": "编写支付模块",
            },
        )

        logs = _degradation_log_store.find_by_reason("all_agents_unavailable")
        assert len(logs) >= 1
        log = logs[0]
        assert log.reason == "all_agents_unavailable"

    def test_degradation_log_contains_correct_task_id(self, client):
        """验证降级日志中的task_id与请求中的task_id一致"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        expected_task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-005",
                "task_id": expected_task_id,
                "task_description": "编写注册模块",
            },
        )

        log = _degradation_log_store.find_by_task_id(expected_task_id)
        assert log is not None
        assert log.task_id == expected_task_id

    def test_degradation_log_timestamp_is_recent(self, client):
        """验证降级日志中的timestamp为当前时间（误差在5秒内）"""
        profiles = [
            ProgrammingAgentProfile(
                name="aider-1",
                agent_type="aider-chat",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        before = datetime.now(timezone.utc)
        task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-006",
                "task_id": task_id,
                "task_description": "编写搜索模块",
            },
        )
        after = datetime.now(timezone.utc)

        log = _degradation_log_store.find_by_task_id(task_id)
        assert log is not None
        assert before <= log.timestamp <= after

    def test_degradation_queue_entry_created(self, client):
        """验证降级队列中新增了对应的队列条目"""
        profiles = [
            ProgrammingAgentProfile(
                name="codearts-1",
                agent_type="codearts",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-007",
                "task_id": task_id,
                "task_description": "编写通知模块",
            },
        )

        entries = _degradation_queue.get_all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.task_id == task_id
        assert entry.project_id == "proj-007"
        assert entry.status == "queued_with_degradation"

    def test_mixed_statuses_all_unavailable(self, client):
        """验证混合状态（offline + busy）下所有 Agent 不可用"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="opencode-1",
                agent_type="opencode",
                status=AgentStatus.BUSY,
            ),
            ProgrammingAgentProfile(
                name="goose-1",
                agent_type="goose",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="pi-agent-1",
                agent_type="pi_coding_agent",
                status=AgentStatus.BUSY,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-008",
                "task_id": task_id,
                "task_description": "编写缓存模块",
            },
        )

        body = response.json()
        assert response.status_code == 202
        assert body["status"] == "queued_with_degradation"
        assert body["message"] == "所有编程Agent不可用，任务进入降级队列"

        log = _degradation_log_store.find_by_task_id(task_id)
        assert log is not None
        assert log.reason == "all_agents_unavailable"

    def test_no_programming_profiles_triggers_different_degradation(self, client):
        """验证没有注册任何编程Agent Profile时触发不同的降级原因"""
        # 只注册非编程类 Agent（如 hermes 对话 Agent）
        profiles = [
            ProgrammingAgentProfile(
                name="hermes-default",
                agent_type="hermes",
                status=AgentStatus.ONLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-009",
                "task_id": task_id,
                "task_description": "编写解析模块",
            },
        )

        body = response.json()
        assert body["status"] == "queued_with_degradation"
        assert body["degradation_reason"] == "no_profiles_registered"

        log = _degradation_log_store.find_by_task_id(task_id)
        assert log is not None
        assert log.reason == "no_profiles_registered"

    def test_empty_profiles_list_triggers_no_profiles_degradation(self, client):
        """验证 Profile 列表为空时触发 no_profiles_registered 降级"""
        _profile_scanner.set_profiles([])

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-010",
                "task_id": task_id,
                "task_description": "编写导出模块",
            },
        )

        body = response.json()
        assert body["status"] == "queued_with_degradation"
        assert body["degradation_reason"] == "no_profiles_registered"

        logs = _degradation_log_store.find_by_reason("no_profiles_registered")
        assert len(logs) >= 1

    def test_response_contains_unavailable_agents_list(self, client):
        """验证降级响应中包含不可用 Agent 的名称列表"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-prod",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="opencode-prod",
                agent_type="opencode",
                status=AgentStatus.BUSY,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-011",
                "task_id": task_id,
                "task_description": "编写导入模块",
            },
        )

        body = response.json()
        assert "unavailable_agents" in body
        assert "claude-code-prod" in body["unavailable_agents"]
        assert "opencode-prod" in body["unavailable_agents"]

    def test_normal_startup_when_agent_available(self, client):
        """验证当有可用编程 Agent 时正常启动蜂群"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="pi-agent-1",
                agent_type="pi_coding_agent",
                status=AgentStatus.ONLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-012",
                "task_id": task_id,
                "task_description": "编写分析模块",
            },
        )

        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "started"
        assert body["agent_count"] == 1

        # 不应产生降级日志
        logs = _degradation_log_store.get_all()
        assert len(logs) == 0

    def test_multiple_degradation_requests_create_multiple_logs(self, client):
        """验证多次降级请求产生多条独立的降级日志"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_ids = [str(uuid.uuid4()) for _ in range(3)]
        for task_id in task_ids:
            client.post(
                "/api/v1/swarms/startup",
                json={
                    "project_id": "proj-multi",
                    "task_id": task_id,
                    "task_description": "多次请求测试",
                },
            )

        logs = _degradation_log_store.get_all()
        assert len(logs) == 3

        for task_id in task_ids:
            log = _degradation_log_store.find_by_task_id(task_id)
            assert log is not None
            assert log.reason == "all_agents_unavailable"

    def test_degradation_log_details_contains_agent_names(self, client):
        """验证降级日志的details字段包含不可用Agent的名称信息"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
            ProgrammingAgentProfile(
                name="opencode-1",
                agent_type="opencode",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-013",
                "task_id": task_id,
                "task_description": "编写验证模块",
            },
        )

        log = _degradation_log_store.find_by_task_id(task_id)
        assert log is not None
        assert log.details is not None
        assert "claude-code-1" in log.details
        assert "opencode-1" in log.details

    def test_response_body_has_task_id_matching_request(self, client):
        """验证响应Body中的task_id与请求中的task_id一致"""
        profiles = [
            ProgrammingAgentProfile(
                name="goose-1",
                agent_type="goose",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        expected_task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-014",
                "task_id": expected_task_id,
                "task_description": "编写转换模块",
            },
        )

        body = response.json()
        assert body["task_id"] == expected_task_id

    def test_degradation_reason_in_response_body(self, client):
        """验证响应Body包含degradation_reason字段"""
        profiles = [
            ProgrammingAgentProfile(
                name="openhands-1",
                agent_type="openhands",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-015",
                "task_id": task_id,
                "task_description": "编写聚合模块",
            },
        )

        body = response.json()
        assert "degradation_reason" in body
        assert body["degradation_reason"] == "all_agents_unavailable"

    def test_only_busy_agents_considered_unavailable(self, client):
        """验证只有busy状态的Agent也被视为不可用"""
        profiles = [
            ProgrammingAgentProfile(
                name="pi-agent-1",
                agent_type="pi_coding_agent",
                status=AgentStatus.BUSY,
            ),
            ProgrammingAgentProfile(
                name="pi-agent-2",
                agent_type="pi_coding_agent",
                status=AgentStatus.BUSY,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-016",
                "task_id": task_id,
                "task_description": "编写分发模块",
            },
        )

        body = response.json()
        assert response.status_code == 202
        assert body["status"] == "queued_with_degradation"
        assert body["message"] == "所有编程Agent不可用，任务进入降级队列"

    def test_degradation_api_endpoint_returns_logs(self, client):
        """验证降级日志查询API端点正确返回日志列表"""
        profiles = [
            ProgrammingAgentProfile(
                name="claude-code-1",
                agent_type="claude_code",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-017",
                "task_id": task_id,
                "task_description": "编写路由模块",
            },
        )

        response = client.get("/api/v1/swarms/degradation-logs")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1

        log_entry = body["logs"][0]
        assert log_entry["task_id"] == task_id
        assert log_entry["reason"] == "all_agents_unavailable"
        assert "timestamp" in log_entry

    def test_degradation_queue_api_endpoint_returns_entries(self, client):
        """验证降级队列查询API端点正确返回队列条目"""
        profiles = [
            ProgrammingAgentProfile(
                name="reasonix-1",
                agent_type="reasonix",
                status=AgentStatus.OFFLINE,
            ),
        ]
        _profile_scanner.set_profiles(profiles)

        task_id = str(uuid.uuid4())
        client.post(
            "/api/v1/swarms/startup",
            json={
                "project_id": "proj-018",
                "task_id": task_id,
                "task_description": "编写中间件模块",
            },
        )

        response = client.get("/api/v1/swarms/degradation-queue")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1

        entry = body["entries"][0]
        assert entry["task_id"] == task_id
        assert entry["project_id"] == "proj-018"
        assert entry["status"] == "queued_with_degradation"
