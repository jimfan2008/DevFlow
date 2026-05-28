# Hermes Agent 发现、对接、对话集成 — 实现方案

> **方案决策**：采用 **方案 A（Hermes API Server 通信）** 为主，**方案 B（hermes-web-ui Socket.IO）** 为可选增强。
>
> **理由**：
> 1. DevFlow 后端运行在 Docker 容器（Linux）中，**无法 spawn Windows 宿主机上的 Python 子进程**（agent bridge 的 `manager.ts` 必须在 Hermes 同 OS 上运行）
> 2. Hermes API Server 已验证可用（`http://localhost:8642/v1`），且 `model=hermes-agent` 走完整 agent runtime（SOUL.md + 记忆 + 工具）
> 3. 方案 B 需在 Windows 宿主机上额外部署 hermes-web-ui BFF 服务器，作为前端可选增强
>
> **重写范围**：原有 `gateway_client.py`、`hermes_acp_client.py`、`hermes_discovery.py`、`hermes_fs.py`、`hermes_service.py`、`llm_client.py`、`hermes.py`(API router) 全部废弃，按 hermes-web-ui 真实架构重写。

# **1. 实现模型**

## **1.1 上下文视图**

### 1.1.1 系统上下文

```plantuml
@startuml
!define INTERNAL #E3F2FD
!define EXTERNAL #FFF8E1
!define INFRA #F3E5F5

skinparam componentStyle rectangle
skinparam defaultFontSize 11

rectangle "DevFlow 前端\n(Vue3 + Element Plus + Pinia)" as fe #INTERNAL {
  rectangle "HermesChatView\n(对话界面)" as chat_view
  rectangle "useHermesChatStore\n(Pinia 状态)" as chat_store
  rectangle "SSEClient\n(EventSource)" as sse_client
  rectangle "WSStatusClient\n(状态推送)" as ws_status
}

rectangle "DevFlow 后端\n(FastAPI + Docker Linux)" as be #INTERNAL {
  rectangle "HermesDiscoveryService\n(运行时发现)" as discovery
  rectangle "HermesAPIClient\n(OpenAI 兼容客户端)" as api_client
  rectangle "HermesChatService\n(流式对话)" as chat_svc
  rectangle "HermesSessionManager\n(会话管理)" as session_mgr
  rectangle "HermesHealthChecker\n(心跳检测)" as health
  rectangle "SSEEndpoint\n(/hermes/chat/stream)" as sse_ep
}

rectangle "Hermes Agent\n(Windows 宿主机)" as hermes #EXTERNAL {
  rectangle "API Server\n(:8642/v1)" as api_srv
  rectangle "Agent Runtime\n(SOUL.md+记忆+工具)" as runtime
}

rectangle "Hermes 配置\n(C:/Users/.../AppData/Local/hermes)" as cfg #EXTERNAL {
  rectangle "config.yaml" as config
  rectangle "auth.json" as auth
  rectangle "profiles/" as profiles
}

rectangle "AI Provider\n(OpenAI/DeepSeek/...)" as provider #EXTERNAL

rectangle "hermes-web-ui BFF\n(可选, Windows 宿主机)" as bff #F3E5F5 {
  rectangle "Socket.IO /chat-run\n(:8648)" as socketio
}

rectangle "基础设施" as infra #INFRA {
  rectangle "PostgreSQL" as pg
  rectangle "Redis" as redis
}

chat_view --> chat_store : 读写对话状态
chat_store --> sse_client : SSE 流式请求
chat_store --> ws_status : 连接状态监听
sse_client --> sse_ep : POST /hermes/chat/stream
ws_status --> be : WS /hermes/ws (状态)
sse_ep --> chat_svc : 调用流式对话
chat_svc --> api_client : OpenAI /v1/chat/completions
api_client --> api_srv : HTTP stream=true
api_srv --> runtime : model=hermes-agent
runtime --> provider : 模型推理
discovery --> cfg : 读取配置 (挂载卷)
health --> api_srv : GET /health
session_mgr --> pg : 持久化
session_mgr --> redis : 缓存/限流

chat_view ..> socketio : (可选) 直连 BFF Socket.IO

note right of api_client
  核心通信路径：
  Docker → host.docker.internal:8642
  → Hermes API Server
  → Agent Runtime (完整流程)
end note

note right of bff
  可选增强：前端直连
  hermes-web-ui BFF Socket.IO
  获得 tool.started/completed
  reasoning.delta 等细粒度事件
end note

@enduml
```

### 1.1.2 Docker 容器与宿主机通信

```
┌──────────────────────────────────────────────────────────────┐
│  Docker 容器 (devflow-backend, Linux)                        │
│                                                              │
│  ┌──────────────────┐                                        │
│  │  HermesAPIClient │ ──host.docker.internal:8642────────►  │
│  │  (httpx async)   │    → Hermes API Server /v1/*         │
│  └──────────────────┘    (model=hermes-agent 走 agent 流程) │
│         │                                                    │
│         │  /hermes-home (只读挂载)                            │
│         ▼                                                    │
│  ┌──────────────────┐                                        │
│  │  HermesDiscovery │    /c/Users/Lenovo/AppData/           │
│  │  Service         │ ──Local/hermes → /hermes-home─────►   │
│  └──────────────────┘    读取 config.yaml / auth.json       │
│                                                              │
│  环境变量：                                                   │
│  HERMES_API_BASE=http://host.docker.internal:8642/v1         │
│  HERMES_API_KEY=devflow-hermes-2026                          │
│  HERMES_PROFILES_PATH=/hermes-home                           │
└──────────────────────────────────────────────────────────────┘
          │ extra_hosts: host.docker.internal:host-gateway
          │ volumes: /c/Users/Lenovo/AppData/Local/hermes:/hermes-home:ro
          ▼
┌──────────────────────────────────────────────────────────────┐
│  宿主机 (Windows)                                            │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐                │
│  │ Hermes Agent     │    │ hermes-web-ui    │                │
│  │ API Server       │    │ BFF (:8648)      │                │
│  │ (:8642/v1)       │    │ Socket.IO        │                │
│  │                  │    │ (可选部署)        │                │
│  └──────────────────┘    └──────────────────┘                │
│  ┌──────────────────┐                                       │
│  │ C:/Users/Lenovo/ │  config.yaml, auth.json, profiles/   │
│  │ AppData/Local/   │  hermes-agent/ (源码)                 │
│  │ hermes/          │  venv/Scripts/hermes.exe (CLI)        │
│  └──────────────────┘                                       │
└──────────────────────────────────────────────────────────────┘
```

**关键约束**：
- Docker 容器（Linux）**无法** `spawn` Windows 上的 `hermes_bridge.py` 或 `hermes.exe`
- agent bridge 的 `Manager`（`manager.ts`）必须在 Hermes 同 OS 上运行，用于 spawn Python 子进程
- 因此 **Docker 后端只能通过 HTTP/TCP 网络协议** 与 Hermes 通信
- Hermes API Server 是唯一从 Docker 可达的 agent runtime 入口

## **1.2 服务/组件总体架构**

### 1.2.1 后端模块架构（重写后）

```plantuml
@startuml
skinparam componentStyle rectangle
skinparam defaultFontSize 11

package "app/services/hermes/" {
  rectangle "HermesDiscoveryService" as discovery #E3F2FD {
    note right: 三级发现策略\n源码目录 → CLI → 系统Python\n+ API Server 检测\n+ Windows 路径适配\n+ Docker 挂载检测
  }
  rectangle "HermesAPIClient" as api_client #E8F5E9 {
    note right: OpenAI 兼容 HTTP 客户端\n/v1/chat/completions (stream)\n/v1/models\n/health\nhttpx.AsyncClient 连接池
  }
  rectangle "HermesChatService" as chat_svc #E8F5E9 {
    note right: 流式对话核心\nSSE 代理转发\n思考过程分离\n工具调用识别\n对话中断处理\n并发限流
  }
  rectangle "HermesSessionManager" as session_mgr #FFF8E1 {
    note right: 会话 CRUD\n消息持久化\n上下文管理\n历史截断
  }
  rectangle "HermesHealthChecker" as health #F3E5F5 {
    note right: 定期心跳\n状态防抖\n自动重连\n诊断接口
  }
  rectangle "HermesConfigReader" as config_reader #E3F2FD {
    note right: config.yaml 解析\nauth.json 凭证池\nProfile 扫描\n密钥脱敏\n.env 读取
  }
}

package "app/api/hermes_router.py" {
  rectangle "hermes_router" as router #E3F2FD {
    note right: /hermes/chat/stream (SSE)\n/hermes/chat/cancel\n/hermes/sessions (CRUD)\n/hermes/models (发现)\n/hermes/profiles (管理)\n/hermes/status (状态)\n/hermes/diagnose (诊断)\n/hermes/ws (WebSocket)
  }
}

package "app/models/" {
  rectangle "HermesSession" as sess_model #F3E5F5
  rectangle "HermesMessage" as msg_model #F3E5F5
}

discovery --> config_reader : 读取配置
api_client --> discovery : 获取 API Server URL/Key
chat_svc --> api_client : 流式请求
chat_svc --> session_mgr : 读写会话/消息
health --> api_client : GET /health
router --> chat_svc : 流式对话
router --> session_mgr : 会话管理
router --> discovery : 发现/诊断
router --> health : 状态查询
session_mgr --> sess_model : ORM
session_mgr --> msg_model : ORM

@enduml
```

### 1.2.2 前端模块架构（重写后）

```plantuml
@startuml
skinparam componentStyle rectangle
skinparam defaultFontSize 11

package "views/" {
  rectangle "HermesChatView" as chat_view #E3F2FD {
    note right: 对话界面（重写）\n流式气泡渲染\n停止生成按钮\n工具调用卡片\n思考过程折叠\n会话列表侧栏
  }
}

package "stores/" {
  rectangle "useHermesChatStore" as chat_store #E8F5E9 {
    note right: 会话列表管理\n当前会话消息\n流式消息缓冲\nSSE 连接管理\n发送/中断控制
  }
  rectangle "useHermesStatusStore" as status_store #FFF8E1 {
    note right: Hermes 连接状态\nWebSocket 监听\n状态变更通知
  }
}

package "api/modules/" {
  rectangle "hermesApi" as api #E3F2FD {
    note right: chatStream (SSE)\nsessions CRUD\nmodels 发现\nprofiles 管理\ndiagnose 诊断
  }
}

package "composables/" {
  rectangle "useSSE" as sse #F3E5F5 {
    note right: EventSource 封装\n自动重连\n消息解析\n连接生命周期
  }
  rectangle "useWebSocket" as ws #F3E5F5 {
    note right: WebSocket 封装\n心跳检测\n状态事件监听
  }
}

package "components/" {
  rectangle "ChatBubble" as bubble #E3F2FD {
    note right: Markdown 渲染\n流式打字效果\n工具调用卡片\n思考过程折叠
  }
  rectangle "ToolCallCard" as tool_card #E3F2FD
  rectangle "ThinkingBlock" as think_block #E3F2FD
}

chat_view --> chat_store : 状态绑定
chat_view --> status_store : 状态指示
chat_store --> api : API 调用
chat_store --> sse : 流式连接
status_store --> ws : 状态监听
chat_view --> bubble : 消息渲染
bubble --> tool_card : 工具调用
bubble --> think_block : 思考过程

@enduml
```

## **1.3 实现设计文档**

### 1.3.1 Hermes 配置读取 — 实现

**新增模块**：`app/services/hermes/hermes_config.py`（替代原 `hermes_fs.py`）

```python
class HermesConfigReader:
    """Hermes 配置文件统一读取 — 替代原 hermes_fs.py 分散逻辑"""

    def __init__(self, hermes_home: Path):
        self._home = hermes_home

    # ── config.yaml ──────────────────────────────
    def read_config(self, profile_name: str = "default") -> Optional[HermesConfig]:
        """读取 Profile 的 config.yaml，返回结构化 HermesConfig"""
        if profile_name == "default":
            path = self._home / "config.yaml"
        else:
            path = self._home / "profiles" / profile_name / "config.yaml"
        if not path.exists():
            return None
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return HermesConfig.from_raw(raw) if isinstance(raw, dict) else None

    # ── auth.json 凭证池 ──────────────────────────
    def read_auth_pool(self) -> list[ProviderCredential]:
        """读取 ~/.hermes/auth.json，返回 Provider 凭证列表"""
        auth_path = self._home / "auth.json"
        if not auth_path.exists():
            return []
        raw = json.loads(auth_path.read_text(encoding="utf-8"))
        return [
            ProviderCredential(
                provider_name=name,
                api_key=creds.get("api_key", ""),
                base_url=creds.get("base_url", ""),
            )
            for name, creds in raw.items()
            if isinstance(creds, dict) and creds.get("api_key")
        ]

    # ── .env ─────────────────────────────────────
    def read_env(self) -> dict[str, str]:
        """读取 ~/.hermes/.env（密钥不写入日志）"""
        ...

    # ── Profile 扫描 ─────────────────────────────
    def scan_profiles(self) -> list[ProfileInfo]:
        """扫描所有 Profile，返回配置摘要"""
        ...

    # ── SOUL.md ──────────────────────────────────
    def read_soul(self, profile_name: str) -> Optional[str]:
        """读取人格描述（前 300 字）"""
        ...

    # ── API Server 配置提取 ───────────────────────
    def extract_api_server_config(self, config: HermesConfig) -> APIServerConfig:
        """从 config.yaml 提取 platforms.api_server 配置"""
        ...

    # ── 密钥脱敏 ─────────────────────────────────
    @staticmethod
    def mask_api_key(key: str) -> str:
        """脱敏：sk-abc...xyz → sk-abc...xyz（保留前3后3）"""
        if len(key) <= 8:
            return "***"
        return f"{key[:3]}...{key[-3:]}"
```

**数据类型**：

```python
@dataclass(frozen=True)
class HermesConfig:
    """config.yaml 结构化配置"""
    model_default: str
    model_provider: str
    api_server_port: Optional[int]
    api_server_key: Optional[str]
    api_server_enabled: bool
    raw: dict  # 原始配置（不暴露给前端）

    @classmethod
    def from_raw(cls, raw: dict) -> "HermesConfig":
        model = raw.get("model", {}) or {}
        platforms = raw.get("platforms", {}) or {}
        api_server = platforms.get("api_server", {}) or {}
        extra = api_server.get("extra", {}) or {}
        return cls(
            model_default=model.get("default", ""),
            model_provider=model.get("provider", ""),
            api_server_port=int(extra["port"]) if extra.get("port") else None,
            api_server_key=api_server.get("key"),
            api_server_enabled=api_server.get("enabled", False),
            raw=raw,
        )

@dataclass(frozen=True)
class ProviderCredential:
    provider_name: str
    api_key: str
    base_url: str

@dataclass(frozen=True)
class APIServerConfig:
    port: int
    key: str
    host: str = "localhost"
    enabled: bool = True

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def v1_url(self) -> str:
        return f"{self.base_url}/v1"
```

### 1.3.2 Hermes Agent 运行时发现 — 实现

**重写模块**：`app/services/hermes/hermes_discovery.py`（替代原 `hermes_discovery.py`）

**核心变化**：
- Docker 容器内无法执行 `subprocess` 查找 Windows 进程，改为通过 `host.docker.internal` 网络检测
- Windows 路径发现适配 hermes-web-ui 真实逻辑（`LOCALAPPDATA/hermes`）
- 移除所有 `subprocess.Popen`/`subprocess.run` 调用（禁止自动启动）

```python
class HermesDiscoveryService:
    """三级发现策略 — 基于文件系统检测 + 网络可达性检测"""

    def __init__(self, config_reader: HermesConfigReader):
        self._config_reader = config_reader
        self._diagnostic_log: list[DiagnosticStep] = []
        self._result: Optional[DiscoveryResult] = None

    async def discover(self) -> DiscoveryResult:
        """执行完整发现流程"""
        # 1. 确定配置目录
        hermes_home = self._resolve_hermes_home()
        self._log("resolve_home", str(hermes_home), hermes_home.exists())

        # 2. 读取 API Server 配置
        config = self._config_reader.read_config("default")
        api_config = self._extract_api_server_config(config) if config else None

        # 3. 检测 API Server 可达性（核心）
        api_server_info = await self._check_api_server(api_config)

        # 4. 运行时类型检测（仅文件系统，不执行进程）
        runtime_info = self._detect_runtime_type(hermes_home)

        # 5. 确定连接方式
        connection_mode = self._determine_connection_mode(api_server_info)

        self._result = DiscoveryResult(
            hermes_home=hermes_home,
            runtime_type=runtime_info,
            installation_path=str(hermes_home) if hermes_home.exists() else None,
            api_server_url=api_server_info.url if api_server_info else None,
            api_server_port=api_server_info.port if api_server_info else None,
            api_server_healthy=api_server_info.healthy if api_server_info else False,
            connection_mode=connection_mode,
            health_status="online" if api_server_info and api_server_info.healthy else "offline",
            diagnostic_steps=self._diagnostic_log,
            hermes_version=self._detect_version(hermes_home),
        )
        return self._result

    def _resolve_hermes_home(self) -> Path:
        """确定配置目录：环境变量 > Docker 挂载 > 默认路径"""
        # 1. HERMES_PROFILES_PATH 环境变量
        env_path = os.environ.get("HERMES_PROFILES_PATH")
        if env_path:
            p = Path(env_path)
            if p.exists():
                return p

        # 2. Docker 挂载检测
        docker_mount = Path("/hermes-home")
        if docker_mount.exists() and (docker_mount / "config.yaml").exists():
            return docker_mount

        # 3. Windows 路径（hermes-web-ui 真实逻辑）
        if platform.system() == "Windows":
            local_app = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if local_app:
                p = Path(local_app) / "hermes"
                if p.exists():
                    return p

        # 4. 默认 ~/.hermes
        return Path.home() / ".hermes"

    async def _check_api_server(self, api_config: Optional[APIServerConfig]) -> Optional[APIServerInfo]:
        """检测 Hermes API Server 可达性"""
        # 确定检测目标
        candidates = []
        if api_config:
            candidates.append(api_config)
        # 环境变量回退
        env_base = os.environ.get("HERMES_API_BASE", "")
        if env_base:
            parsed = urlparse(env_base)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8642
            # Docker 容器中 localhost 应替换为 host.docker.internal
            if host == "localhost" and os.path.exists("/.dockerenv"):
                host = "host.docker.internal"
            candidates.append(APIServerConfig(port=port, key=os.environ.get("HERMES_API_KEY", ""), host=host))

        for candidate in candidates:
            url = f"http://{candidate.host}:{candidate.port}/health"
            self._log("check_api_server", url, True)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        self._log("api_server_healthy", url, True)
                        return APIServerInfo(
                            url=f"http://{candidate.host}:{candidate.port}",
                            port=candidate.port,
                            key=candidate.key,
                            healthy=True,
                        )
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                self._log("api_server_unreachable", url, False, str(e))

        return None

    def _detect_runtime_type(self, hermes_home: Path) -> str:
        """检测运行时类型（仅文件系统检测，不执行进程）"""
        # ① 源码安装
        run_agent = hermes_home / "hermes-agent" / "run_agent.py"
        if run_agent.exists():
            self._log("check_source_install", str(run_agent), True)
            return "source_install"

        # ② CLI 命令（仅检测路径存在性）
        venv_scripts = hermes_home / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
        venv_bin = hermes_home / "hermes-agent" / "venv" / "bin" / "hermes"
        if venv_scripts.exists() or venv_bin.exists():
            self._log("check_cli", str(venv_scripts if venv_scripts.exists() else venv_bin), True)
            return "cli_command"

        self._log("runtime_not_found", str(hermes_home), False)
        return "not_found"

    def _determine_connection_mode(self, api_info: Optional[APIServerInfo]) -> str:
        """确定连接方式：API Server > Socket.IO > CLI"""
        if api_info and api_info.healthy:
            return "api_server"
        # Socket.IO 检测（hermes-web-ui BFF :8648）
        # 在 Docker 中无法直接检测 Windows 上的 BFF，通过环境变量配置
        if os.environ.get("HERMES_BFF_URL"):
            return "socket_io"
        return "cli_fallback"
```

**数据类型**：

```python
@dataclass
class DiscoveryResult:
    hermes_home: Path
    runtime_type: Literal["source_install", "cli_command", "system_python", "not_found"]
    installation_path: Optional[str]
    api_server_url: Optional[str]       # http://host.docker.internal:8642
    api_server_port: Optional[int]      # 8642
    api_server_healthy: bool
    connection_mode: Literal["api_server", "socket_io", "cli_fallback"]
    health_status: Literal["online", "offline", "degraded", "unknown"]
    diagnostic_steps: list[DiagnosticStep]
    hermes_version: Optional[str]

@dataclass
class APIServerInfo:
    url: str           # http://host.docker.internal:8642
    port: int          # 8642
    key: str           # devflow-hermes-2026
    healthy: bool

@dataclass
class DiagnosticStep:
    action: str
    path: str
    success: bool
    detail: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
```

### 1.3.3 Hermes API Client — 实现

**新增模块**：`app/services/hermes/hermes_api_client.py`（替代原 `gateway_client.py`）

**核心变化**：
- 移除 CLI fallback（Docker 容器无法执行 Windows exe）
- 使用 `model=hermes-agent` 确保走完整 agent runtime
- httpx.AsyncClient 连接池复用
- 完整的 SSE 流式解析（对齐 OpenAI 格式）

```python
class HermesAPIClient:
    """Hermes API Server 客户端 — OpenAI 兼容，stream 优先"""

    def __init__(
        self,
        base_url: str,                  # http://host.docker.internal:8642/v1
        api_key: str,                   # devflow-hermes-2026
        timeout: float = 360.0,
        max_connections: int = 10,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(max_connections=max_connections),
        )
        self._model_cache: Optional[list[ModelInfo]] = None
        self._model_cache_ts: float = 0

    async def close(self) -> None:
        await self._client.aclose()

    # ── 流式对话 ─────────────────────────────────
    async def chat_completions_stream(
        self,
        messages: list[dict],
        model: str = "hermes-agent",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[ChatChunk, None]:
        """
        流式对话 — POST /v1/chat/completions (stream=true)
        model=hermes-agent 时走完整 agent runtime
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
            if resp.status_code != 200:
                error_body = await resp.aread()
                raise HermesAPIError(resp.status_code, error_body.decode())
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk_json = json.loads(data)
                    yield self._parse_chunk(chunk_json)
                except json.JSONDecodeError:
                    continue

    # ── 非流式对话 ───────────────────────────────
    async def chat_completions(
        self,
        messages: list[dict],
        model: str = "hermes-agent",
        **kwargs,
    ) -> ChatCompletionResult:
        """非流式对话 — POST /v1/chat/completions (stream=false)"""
        payload = {"model": model, "messages": messages, "stream": False, **kwargs}
        resp = await self._client.post("/chat/completions", json=payload)
        if resp.status_code != 200:
            raise HermesAPIError(resp.status_code, resp.text)
        return ChatCompletionResult.from_json(resp.json())

    # ── 模型发现 ─────────────────────────────────
    async def list_models(self, use_cache: bool = True) -> list[ModelInfo]:
        """GET /v1/models — 含 8s 超时缓存"""
        now = time.time()
        if use_cache and self._model_cache and (now - self._model_cache_ts) < 8:
            return self._model_cache
        try:
            resp = await self._client.get("/models", timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [
                    ModelInfo(
                        model_id=m["id"],
                        provider="hermes",
                        display_name=m.get("id", ""),
                        is_available=True,
                        owned_by=m.get("owned_by", "hermes"),
                    )
                    for m in data.get("data", [])
                ]
                self._model_cache = models
                self._model_cache_ts = now
                return models
        except (httpx.TimeoutException, httpx.ConnectError):
            pass
        return self._model_cache or []

    # ── 健康检测 ─────────────────────────────────
    async def health_check(self) -> bool:
        """GET /health"""
        try:
            resp = await self._client.get("/../health", timeout=5.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    # ── chunk 解析 ───────────────────────────────
    @staticmethod
    def _parse_chunk(chunk_json: dict) -> ChatChunk:
        """解析 OpenAI SSE chunk，分离 content/thinking/tool_calls"""
        choice = chunk_json.get("choices", [{}])[0]
        delta = choice.get("delta", {})
        content = delta.get("content", "") or ""

        # 检查 tool_calls
        tool_calls = delta.get("tool_calls")

        # 检查 reasoning_content（部分模型）
        reasoning_content = delta.get("reasoning_content", "")

        finish_reason = choice.get("finish_reason")

        return ChatChunk(
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )
```

**数据类型**：

```python
@dataclass
class ChatChunk:
    """单次流式 chunk"""
    content: str = ""
    reasoning_content: str = ""     # 推理思考（DeepSeek 风格）
    tool_calls: Optional[list] = None
    finish_reason: Optional[str] = None

@dataclass
class ChatCompletionResult:
    """非流式完成结果"""
    content: str
    model: str
    usage: Optional[dict] = None

    @classmethod
    def from_json(cls, data: dict) -> "ChatCompletionResult":
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        return cls(
            content=message.get("content", ""),
            model=data.get("model", ""),
            usage=data.get("usage"),
        )

@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    provider: str
    display_name: str
    is_available: bool
    owned_by: str
    context_window: Optional[int] = None

class HermesAPIError(Exception):
    """Hermes API 调用错误"""
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Hermes API error {status_code}: {body[:200]}")
```

### 1.3.4 流式对话 — 实现

**重写模块**：`app/services/hermes/hermes_chat.py`（替代原 `hermes_service.py` + `gateway_client.py` 中的对话逻辑）

```python
class HermesChatService:
    """流式对话服务 — SSE 代理转发 + 思考过程分离 + 工具调用识别"""

    def __init__(
        self,
        api_client: HermesAPIClient,
        session_mgr: HermesSessionManager,
        show_thinking: bool = False,
    ):
        self._api = api_client
        self._session = session_mgr
        self._show_thinking = show_thinking
        self._thinking_filter = ThinkingFilter()
        self._concurrency_sem = asyncio.Semaphore(5)  # 最多 5 并发

    async def stream_chat(
        self,
        session_id: str,
        message: str,
        model: str = "hermes-agent",
        profile_name: str = "default",
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        流式对话主入口，yield SSEEvent 供 FastAPI StreamingResponse 消费

        SSEEvent 格式:
          event: content     — 正式回复内容 chunk
          event: thinking    — 思考过程 chunk（仅 show_thinking=True）
          event: reasoning   — 推理过程 chunk
          event: tool_call   — 工具调用事件
          event: done        — 生成完成
          event: error       — 错误消息
        """
        async with self._concurrency_sem:
            # 1. 读取会话历史
            session = await self._session.get_session(session_id)
            if not session:
                yield SSEEvent(event="error", data=json.dumps({"code": "NOT_FOUND", "message": "会话不存在"}))
                return

            history = await self._session.get_messages(session_id)

            # 2. 追加用户消息
            await self._session.add_message(session_id, role="user", content=message)

            # 3. 构建 OpenAI messages 数组
            messages = self._session.build_openai_messages(history, message)

            # 4. 上下文截断检查
            messages = await self._session.truncate_context_if_needed(messages)

            # 5. 调用 Hermes API Server 流式对话
            full_content: list[str] = []
            full_thinking: list[str] = []
            full_reasoning: list[str] = []
            tool_calls_collected: list[dict] = []

            try:
                async for chunk in self._api.chat_completions_stream(
                    messages=messages, model=model,
                ):
                    # 5a. 思考过程分离（<think>...</think> 标签）
                    filtered = self._thinking_filter.filter_chunk(chunk)

                    # 5b. 分离不同类型的内容
                    if filtered.reasoning_content:
                        full_reasoning.append(filtered.reasoning_content)
                        yield SSEEvent(event="reasoning", data=filtered.reasoning_content)

                    if filtered.thinking_content:
                        full_thinking.append(filtered.thinking_content)
                        if self._show_thinking:
                            yield SSEEvent(event="thinking", data=filtered.thinking_content)

                    if filtered.content:
                        full_content.append(filtered.content)
                        yield SSEEvent(event="content", data=filtered.content)

                    if filtered.tool_calls:
                        tool_calls_collected.extend(filtered.tool_calls)
                        yield SSEEvent(event="tool_call", data=json.dumps(filtered.tool_calls))

                # 6. 生成完成，持久化 assistant 消息
                merged_content = "".join(full_content)
                merged_thinking = "".join(full_thinking) if full_thinking else None
                await self._session.add_message(
                    session_id, role="assistant", content=merged_content,
                    thinking_content=merged_thinking,
                    tool_calls=tool_calls_collected or None,
                    model=model,
                )
                yield SSEEvent(event="done", data=json.dumps({"status": "complete"}))

            except HermesAPIError as e:
                error_msg = self._format_error(e)
                yield SSEEvent(event="error", data=json.dumps(error_msg))

            except httpx.TimeoutException:
                # 保留已接收内容
                merged_content = "".join(full_content)
                if merged_content:
                    await self._session.add_message(
                        session_id, role="assistant", content=merged_content,
                        is_interrupted=True,
                    )
                yield SSEEvent(event="error", data=json.dumps({"code": "TIMEOUT", "message": "响应超时，已保留已接收内容"}))

            except httpx.ConnectError:
                yield SSEEvent(event="error", data=json.dumps({"code": "DISCONNECTED", "message": "Hermes 连接中断，请检查 Agent 运行状态"}))

            except asyncio.CancelledError:
                # 用户中断
                merged_content = "".join(full_content)
                await self._session.add_message(
                    session_id, role="assistant", content=merged_content,
                    is_interrupted=True,
                )
                yield SSEEvent(event="done", data=json.dumps({"status": "interrupted"}))
```

**思考过程过滤器**：

```python
class ThinkingFilter:
    """识别并分离 AI 模型输出的思考内容（不丢弃，仅分离）"""

    # <think>...</think> 标签（DeepSeek/QwQ 风格）
    THINK_TAG_OPEN = re.compile(r"<think>")
    THINK_TAG_CLOSE = re.compile(r"</think>")

    def __init__(self):
        self._in_think = False
        self._think_buffer: list[str] = []

    def filter_chunk(self, chunk: ChatChunk) -> ChatChunk:
        """对流式 chunk 进行思考内容分离（状态机模式，跨 chunk 处理）"""
        content = chunk.content or ""
        thinking_parts: list[str] = []
        content_parts: list[str] = []

        # 处理 <think>...</think> 标签
        for char in content:
            if not self._in_think:
                # 检测 <think> 开始
                self._think_buffer.append(char)
                buf = "".join(self._think_buffer)
                if "<think>" in buf:
                    self._in_think = True
                    self._think_buffer = []
                    continue
                if len(self._think_buffer) > 7:
                    content_parts.append(self._think_buffer.pop(0))
            else:
                # 在 think 块内
                self._think_buffer.append(char)
                buf = "".join(self._think_buffer)
                if "</think>" in buf:
                    self._in_think = False
                    # 提取思考内容（去掉 </think> 标签）
                    think_content = buf.replace("</think>", "")
                    thinking_parts.append(think_content)
                    self._think_buffer = []
                    continue
                if len(self._think_buffer) > 8:
                    thinking_parts.append(self._think_buffer.pop(0))

        return ChatChunk(
            content="".join(content_parts),
            thinking_content="".join(thinking_parts) if thinking_parts else None,
            reasoning_content=chunk.reasoning_content,
            tool_calls=chunk.tool_calls,
            finish_reason=chunk.finish_reason,
        )

    def flush(self) -> Optional[str]:
        """流结束时刷新缓冲区"""
        remaining = "".join(self._think_buffer)
        self._think_buffer = []
        return remaining if remaining else None
```

**SSE 端点实现**（`app/api/hermes_router.py`）：

```python
@router.post("/hermes/chat/stream")
async def hermes_chat_stream(
    request: HermesChatRequest,
    chat_svc: HermesChatService = Depends(get_chat_service),
):
    """SSE 流式对话端点"""
    async def event_generator():
        async for event in chat_svc.stream_chat(
            session_id=request.session_id,
            message=request.message,
            model=request.model or "hermes-agent",
            profile_name=request.profile_name or "default",
        ):
            yield f"event: {event.event}\ndata: {event.data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/hermes/chat/cancel")
async def cancel_chat(
    request: CancelChatRequest,
    current_user: User = Depends(get_current_user),
):
    """取消正在进行的流式对话"""
    task = _active_stream_tasks.get(request.session_id)
    if task and not task.done():
        task.cancel()
        return {"code": 0, "message": "对话已取消"}
    return {"code": 1, "message": "无正在进行的对话"}
```

**错误消息格式化**：

```python
@staticmethod
def _format_error(e: HermesAPIError) -> dict:
    """将 Hermes API 错误格式化为用户可读提示"""
    error_map = {
        401: {"code": "UNAUTHORIZED", "message": "API 密钥无效，请检查配置"},
        429: {"code": "RATE_LIMITED", "message": "请求过于频繁，请稍后重试"},
        500: {"code": "SERVER_ERROR", "message": "Hermes Agent 内部错误"},
        503: {"code": "UNAVAILABLE", "message": "Hermes Agent 服务暂不可用"},
    }
    return error_map.get(e.status_code, {
        "code": "UNKNOWN",
        "message": f"Hermes 返回错误 ({e.status_code})",
    })
```

### 1.3.5 会话管理 — 实现

**新增模块**：`app/services/hermes/hermes_session.py`

```python
class HermesSessionManager:
    """会话 CRUD + 消息持久化 + 上下文管理"""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── 会话 CRUD ────────────────────────────────
    async def create_session(
        self, user_id: str, profile_name: str, model_id: str
    ) -> HermesSession:
        """创建新会话"""
        session = HermesSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            profile_name=profile_name,
            model_id=model_id,
        )
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_session(self, session_id: str) -> Optional[HermesSession]:
        """获取会话"""
        return await self._db.get(HermesSession, session_id)

    async def list_sessions(
        self, user_id: str, limit: int = 50
    ) -> list[HermesSession]:
        """列出用户的所有会话"""
        result = await self._db.execute(
            select(HermesSession)
            .where(HermesSession.user_id == user_id)
            .order_by(HermesSession.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_session(self, session_id: str) -> bool:
        """删除会话及所有消息"""
        session = await self.get_session(session_id)
        if not session:
            return False
        await self._db.execute(
            delete(HermesMessage).where(HermesMessage.session_id == session_id)
        )
        await self._db.delete(session)
        await self._db.commit()
        return True

    # ── 消息管理 ─────────────────────────────────
    async def get_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> list[HermesMessage]:
        """按时间分页加载消息"""
        result = await self._db.execute(
            select(HermesMessage)
            .where(HermesMessage.session_id == session_id)
            .order_by(HermesMessage.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self, session_id: str, role: str, content: str,
        thinking_content: str = None, tool_calls: list = None,
        model: str = None, is_interrupted: bool = False,
    ) -> HermesMessage:
        """追加消息并更新会话统计"""
        msg = HermesMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            thinking_content=thinking_content,
            tool_calls=tool_calls,
            model=model,
            is_interrupted=is_interrupted,
        )
        self._db.add(msg)
        # 更新会话 message_count 和 updated_at
        await self._db.execute(
            update(HermesSession)
            .where(HermesSession.id == session_id)
            .values(
                message_count=HermesSession.message_count + 1,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self._db.commit()
        return msg

    # ── 上下文构建 ───────────────────────────────
    def build_openai_messages(
        self, history: list[HermesMessage], new_message: str
    ) -> list[dict]:
        """将持久化消息 + 新消息构建为 OpenAI API 的 messages 数组"""
        messages = []
        for msg in history:
            entry: dict = {"role": msg.role, "content": msg.content}
            if msg.role == "assistant" and msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            messages.append(entry)
        messages.append({"role": "user", "content": new_message})
        return messages

    async def truncate_context_if_needed(
        self, messages: list[dict], max_tokens: int = 128_000
    ) -> list[dict]:
        """上下文截断：估算 token 数，超过限制时保留最近 10 轮"""
        estimated_tokens = sum(len(m.get("content", "")) // 3 for m in messages)
        if estimated_tokens <= max_tokens:
            return messages
        recent: list[dict] = []
        user_count = 0
        for m in reversed(messages):
            recent.insert(0, m)
            if m.get("role") == "user":
                user_count += 1
                if user_count >= 10:
                    break
        return recent
```

### 1.3.6 连接状态管理 — 实现

**新增模块**：`app/services/hermes/hermes_health.py`

```python
class HermesHealthChecker:
    """定期心跳 + 状态防抖 + 自动重连 + 诊断接口"""

    def __init__(self, api_client: HermesAPIClient):
        self._api = api_client
        self._status: Literal["online", "offline", "degraded", "unknown"] = "unknown"
        self._check_interval: float = 30.0
        self._debounce_count: int = 0
        self._debounce_threshold: int = 3
        self._pending_status: str = "unknown"
        self._reconnect_attempts: int = 0
        self._max_reconnect: int = 12
        self._status_callbacks: list[Callable] = []
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动心跳循环（后台 asyncio.Task）"""
        self._task = asyncio.create_task(self._health_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _health_loop(self) -> None:
        while True:
            try:
                new_status = await self._check_health()
                self._apply_debounced_status(new_status)
                if new_status != "online":
                    await self._try_reconnect()
            except Exception:
                self._apply_debounced_status("unknown")
                await asyncio.sleep(60)
            await asyncio.sleep(self._check_interval)

    async def _check_health(self) -> str:
        """调用 /health 端点"""
        healthy = await self._api.health_check()
        return "online" if healthy else "offline"

    def _apply_debounced_status(self, new_status: str) -> None:
        """防抖：连续 3 次检测结果一致才更新"""
        if new_status == self._pending_status:
            self._debounce_count += 1
        else:
            self._pending_status = new_status
            self._debounce_count = 1
        if self._debounce_count >= self._debounce_threshold:
            if new_status != self._status:
                old = self._status
                self._status = new_status
                for cb in self._status_callbacks:
                    cb(old, new_status)

    async def _try_reconnect(self) -> None:
        """自动重连：每 10 秒尝试，最多 12 次"""
        if self._reconnect_attempts >= self._max_reconnect:
            return
        self._reconnect_attempts += 1
        await asyncio.sleep(10)

    @property
    def status(self) -> str:
        return self._status

    def on_status_change(self, callback: Callable) -> None:
        self._status_callbacks.append(callback)

    async def get_diagnostic_info(self) -> DiagnosticInfo:
        """诊断接口"""
        return DiagnosticInfo(
            current_status=self._status,
            reconnect_attempts=self._reconnect_attempts,
            api_server_url=self._api._base_url,
            last_check_time=datetime.now(timezone.utc).isoformat(),
        )
```

### 1.3.7 前端实现

#### Pinia Store：`useHermesChatStore`

**重写文件**：`frontend/src/stores/useHermesChatStore.ts`

```typescript
interface HermesChatState {
  sessions: HermesSession[]
  currentSessionId: string | null
  messages: HermesMessage[]
  streamingMessage: string          // 正在流式接收的消息
  isStreaming: boolean
  isLoading: boolean
  error: string | null
}

export const useHermesChatStore = defineStore('hermesChat', () => {
  const sessions = ref<HermesSession[]>([])
  const currentSessionId = ref<string | null>(null)
  const messages = ref<HermesMessage[]>([])
  const streamingMessage = ref('')
  const isStreaming = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // SSE 连接管理
  let eventSource: EventSource | null = null

  async function sendMessage(content: string, model = 'hermes-agent') {
    if (!currentSessionId.value) return

    // 追加用户消息到列表
    messages.value.push({
      id: crypto.randomUUID(),
      session_id: currentSessionId.value,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    })

    // 重置流式状态
    streamingMessage.value = ''
    isStreaming.value = true

    // 建立 SSE 连接
    eventSource = new EventSource(`/api/hermes/chat/stream`, {
      // POST 无法用 EventSource，需用 fetch + ReadableStream
    })

    // 使用 fetch + ReadableStream（因为 SSE 需 POST）
    const response = await fetch('/api/hermes/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        message: content,
        session_id: currentSessionId.value,
        model,
      }),
    })

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7)
        } else if (line.startsWith('data: ')) {
          handleSSEEvent(currentEvent, line.slice(6))
        }
      }
    }

    isStreaming.value = false
  }

  function handleSSEEvent(event: string, data: string) {
    switch (event) {
      case 'content':
        streamingMessage.value += data
        break
      case 'thinking':
        // 追加到思考过程缓冲
        thinkingBuffer.value += data
        break
      case 'tool_call':
        // 解析工具调用事件
        currentToolCalls.value.push(JSON.parse(data))
        break
      case 'done':
        // 流结束，将 streamingMessage 持久化为 assistant 消息
        messages.value.push({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: streamingMessage.value,
          timestamp: new Date().toISOString(),
        })
        streamingMessage.value = ''
        break
      case 'error':
        error.value = JSON.parse(data).message
        break
    }
  }

  async function cancelStream() {
    // POST /hermes/chat/cancel
    if (currentSessionId.value) {
      await hermesApi.cancelChat(currentSessionId.value)
    }
    isStreaming.value = false
  }

  return {
    sessions, currentSessionId, messages, streamingMessage,
    isStreaming, isLoading, error,
    sendMessage, cancelStream, /* ... */
  }
})
```

#### SSE Composable：`useSSE`

**新增文件**：`frontend/src/composables/useSSE.ts`

```typescript
export function useSSE() {
  async function postSSE(
    url: string,
    body: Record<string, unknown>,
    handlers: {
      onContent?: (data: string) => void
      onThinking?: (data: string) => void
      onReasoning?: (data: string) => void
      onToolCall?: (data: unknown) => void
      onDone?: (data: unknown) => void
      onError?: (data: { code: string; message: string }) => void
    },
    signal?: AbortSignal,
  ): Promise<void> {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
      signal,
    })

    if (!response.ok || !response.body) {
      throw new Error(`SSE request failed: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event: ')) currentEvent = line.slice(7)
        else if (line.startsWith('data: ')) {
          const data = line.slice(6)
          switch (currentEvent) {
            case 'content': handlers.onContent?.(data); break
            case 'thinking': handlers.onThinking?.(data); break
            case 'reasoning': handlers.onReasoning?.(data); break
            case 'tool_call': handlers.onToolCall?.(JSON.parse(data)); break
            case 'done': handlers.onDone?.(JSON.parse(data)); break
            case 'error': handlers.onError?.(JSON.parse(data)); break
          }
        }
      }
    }
  }

  return { postSSE }
}
```

#### 前端组件

**ChatBubble 组件** — 支持 Markdown 渲染、流式打字效果、工具调用卡片、思考过程折叠：

```vue
<template>
  <div :class="['chat-bubble', `chat-bubble--${message.role}`]">
    <!-- 思考过程（可折叠） -->
    <div v-if="message.thinking_content" class="chat-bubble__thinking">
      <el-collapse>
        <el-collapse-item title="思考过程">
          <div class="thinking-content" v-html="renderMarkdown(message.thinking_content)" />
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 工具调用 -->
    <div v-if="message.tool_calls?.length" class="chat-bubble__tools">
      <ToolCallCard v-for="tc in message.tool_calls" :key="tc.id" :tool-call="tc" />
    </div>

    <!-- 正式内容 -->
    <div class="chat-bubble__content" v-html="renderMarkdown(displayContent)" />

    <!-- 流式光标 -->
    <span v-if="isStreaming" class="chat-bubble__cursor">▌</span>

    <!-- 中断标记 -->
    <el-tag v-if="message.is_interrupted" size="small" type="warning">已中断</el-tag>
  </div>
</template>
```

### 1.3.8 模型发现 — 实现

**方法**：`HermesAPIClient.list_models()` + `HermesConfigReader.read_auth_pool()`

```python
class HermesModelDiscovery:
    """4 级模型发现策略（对齐 hermes-web-ui 真实逻辑）"""

    def __init__(self, api_client: HermesAPIClient, config_reader: HermesConfigReader):
        self._api = api_client
        self._config = config_reader

    async def discover_models(self) -> list[ModelInfo]:
        """合并所有来源的模型列表"""
        all_models: list[ModelInfo] = []

        # 1. Hermes API Server /v1/models（含 hermes-agent 模型）
        api_models = await self._api.list_models()
        all_models.extend(api_models)

        # 2. auth.json 凭证池 → 各 Provider /v1/models
        credentials = self._config.read_auth_pool()
        for cred in credentials:
            try:
                provider_models = await self._fetch_provider_models(cred)
                all_models.extend(provider_models)
            except Exception as e:
                logger.warning(f"Provider {cred.provider_name} models fetch failed: {e}")
                all_models.append(ModelInfo(
                    model_id=f"{cred.provider_name}-offline",
                    provider=cred.provider_name,
                    display_name=f"{cred.provider_name} (离线)",
                    is_available=False,
                    owned_by=cred.provider_name,
                ))

        # 3. .env 环境变量中的模型
        env_models = self._discover_from_env()
        all_models.extend(env_models)

        # 4. 合并去重
        return self._deduplicate_models(all_models)

    async def _fetch_provider_models(self, cred: ProviderCredential) -> list[ModelInfo]:
        """调用 Provider 的 /v1/models"""
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{cred.base_url.rstrip('/')}/v1/models",
                headers={"Authorization": f"Bearer {cred.api_key}"},
            )
            if resp.status_code != 200:
                raise Exception(f"Status {resp.status_code}")
            return [
                ModelInfo(
                    model_id=m["id"],
                    provider=cred.provider_name,
                    display_name=m.get("id", ""),
                    is_available=True,
                    owned_by=m.get("owned_by", cred.provider_name),
                )
                for m in resp.json().get("data", [])
            ]
```

# **2. 接口设计**

## **2.1 总体设计**

DevFlow 后端提供 RESTful API + SSE 流式 + WebSocket 状态推送三类接口。

```
前端 ←──SSE──→ 后端 ←──HTTP/SSE──→ Hermes API Server
前端 ←──WS───→ 后端 (状态推送)
前端 ←──(可选)Socket.IO──→ hermes-web-ui BFF (细粒度事件)
```

## **2.2 接口清单**

### 后端 API 端点

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/hermes/chat/stream` | SSE 流式对话 | `{message, session_id, model?, profile?}` | SSE stream |
| POST | `/hermes/chat/cancel` | 取消对话 | `{session_id}` | `{code, message}` |
| GET | `/hermes/sessions` | 列出会话 | - | `{sessions[]}` |
| POST | `/hermes/sessions` | 创建会话 | `{profile_name, model_id}` | `{session}` |
| GET | `/hermes/sessions/{id}` | 获取会话 | - | `{session}` |
| DELETE | `/hermes/sessions/{id}` | 删除会话 | - | `{code, message}` |
| GET | `/hermes/sessions/{id}/messages` | 获取消息 | `?limit=100&offset=0` | `{messages[]}` |
| GET | `/hermes/models` | 模型发现 | - | `{models[]}` |
| GET | `/hermes/profiles` | Profile 列表 | - | `{profiles[]}` |
| GET | `/hermes/status` | 连接状态 | - | `{status, mode, ...}` |
| GET | `/hermes/diagnose` | 诊断信息 | - | `{diagnostic_info}` |
| GET | `/hermes/health` | 健康检查 | - | `{healthy}` |
| WS | `/hermes/ws` | 状态 WebSocket | - | 状态事件 |

### SSE 事件格式

```
event: content
data: 你好

event: thinking
data: 我需要分析用户的需求...

event: reasoning
data: 首先检查...

event: tool_call
data: {"tool_call_id":"tc_1","function":{"name":"read_file","arguments":"{\"path\":\"/tmp/a.py\"}"}}

event: done
data: {"status":"complete"}

event: error
data: {"code":"TIMEOUT","message":"响应超时"}
```

### WebSocket 状态事件

| 事件 | 方向 | 数据 | 说明 |
|------|------|------|------|
| `hermes.status` | 服务端→客户端 | `{status: "online"}` | 连接状态变更 |
| `hermes.health` | 服务端→客户端 | `{healthy: true}` | 健康检查结果 |

### 可选：hermes-web-ui Socket.IO 事件（前端直连 BFF 时）

若部署了 hermes-web-ui BFF 服务器，前端可直接连接其 Socket.IO `/chat-run`，获得更细粒度的事件：

| 事件 | 方向 | 说明 |
|------|------|------|
| `run` | 客户端→服务端 | 发起对话 |
| `abort` | 客户端→服务端 | 中断运行 |
| `message.delta` | 服务端→客户端 | 流式增量文本 |
| `run.completed` | 服务端→客户端 | 运行完成 |
| `run.failed` | 服务端→客户端 | 运行失败 |
| `tool.started` | 服务端→客户端 | 工具开始 |
| `tool.completed` | 服务端→客户端 | 工具完成 |
| `reasoning.delta` | 服务端→客户端 | 推理思考增量 |
| `thinking.delta` | 服务端→客户端 | 思考增量 |
| `approval.requested` | 服务端→客户端 | 请求用户审批 |

# **3. 数据模型**

## **3.1 设计目标**

1. 会话和消息持久化存储，支持页面刷新不丢失
2. 与 Hermes SQLite 会话数据独立（DevFlow 维护自己的会话模型）
3. 支持消息分页加载，避免大历史记录性能问题

## **3.2 模型实现**

### 后端 ORM 模型

```python
class HermesSession(Base):
    """对话会话"""
    __tablename__ = "hermes_sessions"

    id = Column(String(36), primary_key=True)                # UUID v4
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    profile_name = Column(String(100), nullable=False, default="default")
    model_id = Column(String(100), nullable=False, default="hermes-agent")
    display_name = Column(String(200), nullable=True)
    message_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HermesMessage(Base):
    """对话消息"""
    __tablename__ = "hermes_messages"

    id = Column(String(36), primary_key=True)                # UUID v4
    session_id = Column(String(36), ForeignKey("hermes_sessions.id"), nullable=False, index=True)
    role = Column(Enum("user", "assistant", "system", "tool", name="hermes_msg_role"), nullable=False)
    content = Column(Text, nullable=False)                    # 最大 100000 字符
    thinking_content = Column(Text, nullable=True)            # 思考过程
    tool_calls = Column(JSON, nullable=True)                  # 工具调用列表
    model = Column(String(100), nullable=True)                # 生成模型
    is_streaming = Column(Boolean, default=False)
    is_interrupted = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

### 前端 TypeScript 类型

```typescript
interface HermesSession {
  id: string
  user_id: string
  profile_name: string
  model_id: string
  display_name: string | null
  message_count: number
  is_active: boolean
  created_at: string
  updated_at: string
}

interface HermesMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  thinking_content?: string
  tool_calls?: ToolCall[]
  model?: string
  is_streaming: boolean
  is_interrupted: boolean
  timestamp: string
}

interface ToolCall {
  tool_call_id: string
  function: {
    name: string
    arguments: string
  }
  result?: unknown
}

interface ModelInfo {
  model_id: string
  provider: string
  display_name: string
  is_available: boolean
  owned_by: string
  context_window?: number
}

interface ProfileInfo {
  name: string
  model_default: string
  model_provider: string
  gateway_port: number | null
  is_running: boolean
  config_path: string
  personality?: string
}

interface DiscoveryResult {
  runtime_type: 'source_install' | 'cli_command' | 'system_python' | 'not_found'
  installation_path: string | null
  api_server_url: string | null
  api_server_port: number | null
  api_server_healthy: boolean
  connection_mode: 'api_server' | 'socket_io' | 'cli_fallback'
  health_status: 'online' | 'offline' | 'degraded' | 'unknown'
  hermes_version: string | null
}
```

### Alembic 迁移

```python
def upgrade():
    op.create_table(
        "hermes_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("profile_name", sa.String(100), nullable=False, server_default="default"),
        sa.Column("model_id", sa.String(100), nullable=False, server_default="hermes-agent"),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("message_count", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hermes_sessions_user_id", "hermes_sessions", ["user_id"])

    op.create_table(
        "hermes_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("hermes_sessions.id"), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", "system", "tool", name="hermes_msg_role"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("thinking_content", sa.Text, nullable=True),
        sa.Column("tool_calls", sa.JSON, nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("is_streaming", sa.Boolean, server_default="false"),
        sa.Column("is_interrupted", sa.Boolean, server_default="false"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hermes_messages_session_id", "hermes_messages", ["session_id"])
    op.create_index("ix_hermes_messages_timestamp", "hermes_messages", ["timestamp"])
```

# **4. 部署设计**

## **4.1 Docker Compose 配置**

```yaml
# docker-compose.yml（新增/修改部分）
services:
  backend:
    environment:
      # Hermes Agent 通信配置
      - HERMES_API_BASE=http://host.docker.internal:8642/v1
      - HERMES_API_KEY=devflow-hermes-2026
      - HERMES_PROFILES_PATH=/hermes-home
      - HERMES_MODEL=hermes-agent
      # 可选：hermes-web-ui BFF 地址
      - HERMES_BFF_URL=
    volumes:
      # Hermes 配置目录只读挂载
      - /c/Users/Lenovo/AppData/Local/hermes:/hermes-home:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## **4.2 Windows 宿主机 Hermes Agent 启动**

Hermes Agent 必须在 Windows 宿主机上运行，API Server 监听 `0.0.0.0:8642`（不仅限 localhost，以便 Docker 容器可达）：

```bash
# 在 Windows 宿主机上启动 Hermes Agent（确保 API Server 启用）
# config.yaml 中应包含：
# platforms:
#   api_server:
#     enabled: true
#     key: devflow-hermes-2026
#     extra:
#       port: 8642
#       host: "0.0.0.0"    # 重要：监听所有接口，Docker 可达

# 启动命令
hermes --serve
```

## **4.3 可选：hermes-web-ui BFF 部署**

若需前端直连 Socket.IO 获得细粒度事件，需在 Windows 宿主机上部署 hermes-web-ui：

```bash
# 1. 安装 hermes-web-ui
git clone <hermes-web-ui-repo>
cd hermes-web-ui
npm install

# 2. 启动 BFF 服务器（默认端口 8648）
PORT=8648 HERMES_AGENT_ROOT="C:/Users/Lenovo/AppData/Local/hermes/hermes-agent" npm run dev
```

前端配置（环境变量）：
```
VITE_HERMES_BFF_URL=http://localhost:8648
```

# **5. 与现有 DevFlow 代码的集成点**

## **5.1 废弃的模块**

以下模块将被**完全删除**，由新模块替代：

| 废弃模块 | 替代模块 | 说明 |
|---------|---------|------|
| `app/services/gateway_client.py` | `app/services/hermes/hermes_api_client.py` | 粗糙的 HTTP+CLI 混合客户端 → 纯 httpx AsyncClient |
| `app/services/gateway_health.py` | `app/services/hermes/hermes_health.py` | 简单健康检查 → 防抖+重连+诊断 |
| `app/services/hermes_acp_client.py` | 删除 | ACP 协议在 Docker 中不可用 |
| `app/services/hermes_discovery.py` | `app/services/hermes/hermes_discovery.py` | 分散逻辑 → 统一发现服务 |
| `app/services/hermes_service.py` | `app/services/hermes/hermes_chat.py` | 非流式+粗糙过滤 → 流式+思考分离 |
| `app/services/llm_client.py` | `app/services/hermes/hermes_api_client.py` | 同步阻塞 → 异步流式 |
| `app/utils/hermes_fs.py` | `app/services/hermes/hermes_config.py` | 分散函数 → 结构化配置读取 |
| `app/api/hermes.py` | `app/api/hermes_router.py` | 旧端点 → 新 SSE 流式端点 |

## **5.2 新增的模块**

```
app/services/hermes/
├── __init__.py
├── hermes_config.py          # 配置读取（替代 hermes_fs.py）
├── hermes_discovery.py       # 运行时发现（替代 hermes_discovery.py）
├── hermes_api_client.py      # OpenAI 兼容客户端（替代 gateway_client.py + llm_client.py）
├── hermes_chat.py            # 流式对话（替代 hermes_service.py）
├── hermes_session.py         # 会话管理（新增）
├── hermes_health.py          # 连接状态（替代 gateway_health.py）
├── hermes_model_discovery.py # 模型发现（新增）
└── types.py                  # 数据类型定义

app/api/hermes_router.py      # API 路由（替代 hermes.py + hermes_integration.py）
app/models/hermes_session.py  # ORM 模型
app/models/hermes_message.py  # ORM 模型
alembic/versions/004_hermes_sessions.py  # 数据库迁移
```

## **5.3 前端改动**

```
frontend/src/
├── stores/useHermesChatStore.ts    # 新增：Hermes 对话状态管理
├── stores/useHermesStatusStore.ts  # 新增：连接状态管理
├── api/modules/hermes.ts           # 新增：Hermes API 模块
├── composables/useSSE.ts           # 新增：SSE 请求封装
├── views/HermesChatView.vue        # 重写：对话界面
├── components/ChatBubble.vue       # 重写：消息气泡
├── components/ToolCallCard.vue     # 新增：工具调用卡片
└── components/ThinkingBlock.vue    # 新增：思考过程折叠
```

## **5.4 config.py 新增配置项**

```python
class Settings(BaseSettings):
    # ── Hermes Agent（重写后）────────────────────
    HERMES_API_BASE: str = os.getenv("HERMES_API_BASE", "http://host.docker.internal:8642/v1")
    HERMES_API_KEY: str = os.getenv("HERMES_API_KEY", "")
    HERMES_MODEL: str = os.getenv("HERMES_MODEL", "hermes-agent")
    HERMES_PROFILES_PATH: str = os.getenv("HERMES_PROFILES_PATH", "/hermes-home")
    HERMES_BFF_URL: str = os.getenv("HERMES_BFF_URL", "")         # 可选 Socket.IO BFF
    HERMES_HEALTH_INTERVAL: int = int(os.getenv("HERMES_HEALTH_INTERVAL", "30"))
    HERMES_MAX_CONCURRENT_CHATS: int = int(os.getenv("HERMES_MAX_CONCURRENT_CHATS", "5"))
    HERMES_SHOW_THINKING: bool = os.getenv("HERMES_SHOW_THINKING", "false").lower() == "true"
```

## **5.5 依赖其他 DevFlow 模块**

| 依赖模块 | 集成方式 | 说明 |
|---------|---------|------|
| `app/models/user.py` | FK 引用 | HermesSession 关联用户 |
| `app/models/agent.py` | 状态同步 | 发现结果写入 Agent 表 |
| `app/database.py` | get_db | 数据库会话 |
| `app/api/deps.py` | get_current_user | 用户鉴权 |
| `app/ws/` | WebSocket 推送 | 状态变更通知前端 |

# **6. 方案 A vs 方案 B 详细对比**

| 维度 | 方案 A（API Server） | 方案 B（Socket.IO BFF） |
|------|---------------------|------------------------|
| 通信路径 | Docker→`host.docker.internal:8642`→API Server | 前端→`localhost:8648`→BFF→agent bridge→Agent |
| Agent Runtime | `model=hermes-agent` 走完整流程 | agent bridge → AIAgent 实例（同样完整） |
| 流式事件粒度 | content chunk + tool_calls | message.delta + tool.started/completed + reasoning.delta + thinking.delta + approval.requested |
| 部署复杂度 | 低（仅 Hermes Agent） | 高（需额外部署 hermes-web-ui BFF） |
| Docker 兼容性 | 完全兼容（HTTP 通信） | 前端直连 BFF 可行，但 BFF 需在 Windows 运行 |
| 思考过程 | `<think>` 标签解析（后端过滤） | `thinking.delta` 事件（原生支持） |
| 工具调用审批 | 不支持（自动批准） | `approval.requested` 事件 |
| 中断/steer | HTTP 连接断开 | `abort` + `steer` 事件 |
| 推荐场景 | 日常对话、需求分析 | 需要工具审批、精细推理展示 |

**推荐**：先实现方案 A（最小改动），后续按需增加方案 B 支持（前端可选连接 BFF Socket.IO）。
