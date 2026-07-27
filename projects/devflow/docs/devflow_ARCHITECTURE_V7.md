# DevFlow 架构设计文档 V7.0

**项目**: DevFlow 项目管理平台
**版本**: 7.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: V6.0 修订 (根据后荣 QA 检验报告修订)

**变更日志**:
- V7.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 【严重问题1】docker-compose 端口映射与安全策略矛盾修正: 确认 V6.0 中 PostgreSQL(5432) 和 Redis(6379) 已无端口映射，与 6.1 节安全策略一致；同时移除 Gitea(3000) 端口映射，统一通过 Nginx 代理访问
  - 【严重问题2】4.4 节单项目峰值 CPU 计算确认: V6.0 实际文档中总计为 32.5 核 (18+2+4.5+8)，计算正确；本次保持并补充明细说明
  - 【严重问题3】Ollama 容器 command 修正: 原 `ollama serve & sleep 5 && ollama pull...` 会导致容器退出并反复重启，改为使用 entrypoint 脚本先 pull 模型再 serve
  - 【中等问题4】补充 filebeat 健康检查: 新增 `test: ["CMD-SHELL", "filebeat test output"]` healthcheck 指令
  - 【中等问题5】WebSocket Worker 与主后端会话共享设计: 新增 dedicated-websocket-worker 服务说明，补充 Redis Pub/Sub 广播机制设计，主后端 workers 降为 2
  - 【中等问题6】Redis 持久化配置完善: 在 AOF 基础上补充 RDB 快照配置 (--save 900 1 --save 300 10 --save 60 10000)，实现 RDB+AOF 双持久化策略
  - 【中等问题7】Gitea 端口安全修正: 移除 ports 中 3000:3000 映射，统一通过 Nginx location /gitea/ 代理访问，更新 6.1 节和架构图
  - 【建议改进8】Celery Worker 并发度调整: concurrency 由 4 调整为 8，提升命名 Agent + 蜂群编排 + 定时任务的并发处理能力
  - 【建议改进9】Elasticsearch 配置完善: 补充 ulimit (nofile=65536)、内存锁定配置 (bootstrap.memory_lock=true)
  - 【建议改进10】编程 Agent 容器资源上限: 为编程 Agent 容器补充 CPU/内存限制 (单 Agent: 4 核 CPU / 8GB 内存)，防止单个 Agent 耗尽宿主机资源

- V6.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 架构描述由"分层单体架构"修正为"单体应用架构"，明确外部服务为依赖组件而非应用层模块
  - 补充 Ollama 服务部署定义 (docker-compose 新增 ollama 服务)
  - 补充 Agent 蜂群部署定义 (docker-compose 新增 swarm-executor 服务)
  - Gitea 数据库隔离: 新增独立的 gitea-postgres 容器和独立用户
  - 统一 Redis 密码变量: 移除 CELERY_BROKER_PASSWORD，统一使用 REDIS_PASSWORD
  - 资源容量规划补充: 9个Hermes Agent进程、Ollama+Qwen2.5-72B模型推理、Agent蜂群运行时资源
  - 明确 Ollama 部署位置为 Docker 容器内，修正 Hermes Agent 与 Ollama 跨网络通信方案
  - 网络拓扑图补充 Ollama 和 Agent 蜂群位置
  - 健康检查补充: Ollama、Elasticsearch、Kibana 服务健康检查
  - 安全认证补充: Hermes Agent API Key 认证、蜂群 Webhook 签名认证、RBAC 角色定义、Docker 网络策略
  - 数据流闭环修正: 体现命名Agent(Step1-12)→后荣QA检验→编程Agent蜂群的执行顺序
  - 7.2 节容量计算修正: 纳入 Hermes Agent、Ollama、蜂群资源后重新核算

---

## 1. 系统架构概述

### 1.1 架构目标

DevFlow 采用单体应用架构，核心设计理念：
- **职责单一**: DevFlow 后端为单一 FastAPI 进程，各模块通过 Python 包结构划分，非独立部署的微服务
- **外部服务隔离**: 数据库、缓存、代码托管、监控、推理引擎等均为独立的依赖组件，通过容器化部署与后端解耦
- **高可用**: 通过容器化部署和负载均衡实现99%可用性
- **可扩展**: 模块化设计支持新增Agent类型和功能模块快速接入
- **可观测**: 全链路监控、日志、告警体系覆盖系统运行状态

### 1.2 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        人类用户 (Client)                                 │
│              浏览器 / 移动端 (需求/进度/群聊/会议)                        │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │ HTTP/HTTPS + WebSocket
┌───────────────────────────────────────▼─────────────────────────────────┐
│                          Nginx 反向代理 (依赖组件)                        │
│              (静态资源 / SSL终止 / WebSocket代理 / 负载均衡)               │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────┐
│                      FastAPI 后端单体应用 (Docker 容器: backend)          │
│              (单一进程,内部模块通过Python包划分,非微服务)             │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 16步流程调度  │  │ Agent蜂群调度 │  │ QA门控检验   │  │ 群聊协作   │ │
│  │ 引擎模块     │  │ 管理模块     │  │ 引擎模块     │  │ 模块       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Profile扫描  │  │ Gateway通信  │  │ Gitea代码库  │  │ 通知推送   │ │
│  │ 同步模块     │  │ 客户端模块   │  │ 集成模块     │  │ 模块       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Celery 任务队列 (异步任务调度 / Agent执行编排)                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────────────┘
              │                    │                    │
   ┌──────────▼──────────┐ ┌──────▼───────┐ ┌─────────▼──────────┐
   │ Gitea (依赖组件)    │ │ Redis        │ │ Prometheus         │
   │ 代码托管服务        │ │ (缓存/队列)  │ │ (指标采集)         │
   └─────────────────────┘ └──────────────┘ └────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              9个命名Agent角色 (宿主机进程,独立Hermes Profile实例)       │
│  海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华 (Gateway API通信)         │
│  默认模型: 本地部署 (Ollama容器 + qwen2.5:72b-instruct-q4_K_M)        │
│  可选模型: 云端 API (OpenAI/Anthropic 等) — 通过 config.yaml 配置切换   │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              Swarm Executor (Docker 容器: swarm-executor)              │
│  职责: 接收 Celery 任务,调度编程 Agent 工具执行                        │
│  触发方式: 通过挂载宿主机路径和 Docker socket,启动宿主机上的编程工具   │
└────────────────────────────────────────────────────────────────────────┘
              │ 触发 (通过宿主机路径)
┌─────────────▼─────────────────────────────────────────────────────────┐
│              编程Agent工具 (宿主机上安装的 CLI 工具)                    │
│  Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma  │
│  hermes子agent / pi-codeing-agent子agent                               │
│  交互方式: Celery回调上报 + 轮询进度 + Webhook事件通知                   │
│  隔离方式: 独立进程 + 项目目录隔离 + 文件锁机制                         │
│  资源上限: 单Agent 4核CPU/8GB内存 (deploy.resources.limits)             │
│  由后发/后达命名Agent调度,Swarm Executor容器触发执行                    │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              数据持久层 (依赖组件)                                       │
│  PostgreSQL (DevFlow主库) + Gitea-PostgreSQL (Gitea独立库)             │
│  Redis (缓存/队列) + 文件存储 (项目文件夹) + Gitea (代码仓库)          │
│  数据流闭环: 人类用户→Nginx→FastAPI→命名Agent(Step1-12执行)→           │
│            后荣QA检验→检验通过→Swarm Executor触发编程Agent工具(宿主机)→│
│            Git提交→Gitea→通知用户                                       │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.3 架构层次说明

| 层次 | 职责 | 技术选型 | 部署方式 |
|------|------|----------|----------|
| 表示层 | 用户界面交互、实时通信 | Vue 3 + Element Plus + WebSocket | Nginx 容器 (静态文件) |
| 网关层 | 反向代理、SSL、负载均衡 | Nginx | Nginx 容器 (依赖组件) |
| 应用层 | 业务逻辑、任务调度、Agent协调 (单体应用内部模块) | FastAPI + Celery + asyncio | Docker 容器 (backend) |
| 集成层 | 代码托管、Agent通信、消息队列、推理引擎 | Gitea API + Hermes Gateway + Redis + Ollama | 各独立容器/宿主机进程 |
| 数据层 | 持久化存储、缓存 | PostgreSQL + Redis + 文件存储 | Docker 容器 (依赖组件) |

**说明**: DevFlow 后端为单体应用（单一 FastAPI 进程），Nginx、PostgreSQL、Redis、Gitea、Ollama、Prometheus、Jaeger、ELK 等均为独立的依赖组件，非应用层模块，通过 Docker 容器化或宿主机进程部署，与后端通过网络通信。Swarm Executor 为 Docker 容器服务，负责调度的编程 Agent 工具 (Claude Code/Codex/Opencode 等) 安装在宿主机上，通过挂载路径触发执行。

---

## 2. 分层架构设计

### 2.1 表示层 (Presentation Layer)

**职责**: 用户界面渲染、事件处理、实时数据展示

**技术栈**:
- Vue 3 (Composition API + `<script setup>`)
- Element Plus (UI组件库)
- Pinia (状态管理)
- Vue Router 4 (路由管理)
- Vue I18n (国际化)
- WebSocket 客户端 (实时通信)

**核心模块**:
- 项目列表页
- 项目详情/进度页
- 16步流程可视化管理
- 项目讨论群聊天界面
- 会议模式界面
- Agent蜂群监控面板
- QA检验结果展示
- 系统管理后台

### 2.2 网关层 (Gateway Layer)

**职责**: 请求路由、SSL终止、静态资源服务、WebSocket代理

**配置**:
```nginx
upstream devflow_backend {
    server backend:8000;
}

upstream devflow_ws {
    server dedicated-websocket-worker:8001;
}

upstream gitea {
    server gitea:3000;
}

server {
    listen 443 ssl;
    server_name devflow.example.com;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://devflow_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://devflow_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location /gitea/ {
        proxy_pass http://gitea;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2.3 应用层 (Application Layer)

**职责**: 核心业务逻辑实现、任务编排、Agent协调

**技术栈**:
- FastAPI (Web框架，异步支持)
- Celery (分布式任务队列)
- SQLAlchemy 2.0 (ORM)
- Pydantic 2.0 (数据验证)
- Alembic (数据库迁移管理)

**说明**: FastAPI 后端为单体应用,各模块在同一进程中运行,通过 Python 包结构进行逻辑划分,并非独立部署的微服务。

**核心模块划分**:

```
devflow/
├── api/                    # API路由层
│   ├── v1/
│   │   ├── auth.py         # 认证接口
│   │   ├── projects.py     # 项目管理接口
│   │   ├── agents.py       # Agent管理接口
│   │   ├── swarms.py       # 蜂群管理接口
│   │   ├── qa.py           # QA门控接口
│   │   ├── groups.py       # 群聊管理接口
│   │   ├── repos.py        # 代码库管理接口
│   │   └── hermes.py       # Gateway通信接口
│   └── websocket/
│       └── group_chat.py   # WebSocket群聊端点
├── core/                   # 核心业务层
│   ├── workflow/
│   │   ├── engine.py       # 16步流程调度引擎
│   │   ├── step_executor.py# 步骤执行器
│   │   ├── retry_manager.py# 重试与回滚管理
│   │   └── dependency_graph.py # 任务依赖图管理
│   ├── agent/
│   │   ├── coordinator.py  # Agent协调器
│   │   ├── profile_scanner.py # Profile扫描同步
│   │   ├── gateway_client.py  # Hermes Gateway客户端
│   │   └── swarm_manager.py   # 蜂群管理器
│   ├── qa/
│   │   ├── inspector.py    # QA检验引擎
│   │   ├── dimensions.py   # 检验维度定义
│   │   └── scorer.py       # 量化打分引擎
│   ├── collaboration/
│   │   ├── group_manager.py# 群组管理
│   │   ├── discussion.py   # 讨论模式
│   │   └── meeting.py      # 会议模式
│   ├── gitea/
│   │   ├── client.py       # Gitea API客户端
│   │   ├── repo_manager.py # 仓库管理
│   │   └── branch_manager.py# 分支管理
│   └── notification/
│       └── push.py         # 通知推送
├── models/                 # 数据模型
├── schemas/                # Pydantic Schema
├── services/               # 业务服务层
├── tasks/                  # Celery异步任务
├── utils/                  # 工具函数
├── migrations/             # Alembic 数据库迁移脚本
└── config/                 # 配置管理
```

### 2.4 集成层 (Integration Layer)

**职责**: 外部系统集成通信

**集成的外部系统**:

| 系统 | 通信方式 | 用途 | 部署位置 |
|------|----------|------|----------|
| Hermes Agent (9个命名角色) | HTTP REST + WebSocket (Gateway API) | Agent对话、任务执行 | 宿主机进程 |
| Ollama | HTTP REST (容器内: `ollama:11434`) | 本地模型推理服务 | Docker 容器 |
| Gitea | REST API (容器内: `gitea:3000`) | 代码仓库管理、Git操作 | Docker 容器 |
| 编程Agent工具 (蜂群) | Swarm Executor容器→宿主机路径触发 | 任务分发、进度上报、成果交付 | 宿主机 CLI 工具 |
| Prometheus | HTTP Push | 指标上报 | Docker 容器 |
| Jaeger | gRPC | 链路追踪上报 | Docker 容器 |

### 2.5 数据层 (Data Layer)

**职责**: 数据持久化、缓存、会话管理

| 组件 | 用途 | 配置 |
|------|------|------|
| PostgreSQL (devflow) | DevFlow主数据库，存储项目、用户、任务、QA记录等 | 连接池: 20, 最大连接: 100 |
| PostgreSQL (gitea) | Gitea独立数据库，存储Gitea元数据 | 独立用户 gitea_admin |
| Redis 6+ | 缓存、Celery Broker、WebSocket会话 | 内存: 2GB, 持久化: RDB+AOF双持久化 |
| 文件存储 | 项目文件夹、文档、报告 | /DevFlow/projects/ |

**数据库隔离说明**: DevFlow 和 Gitea 使用独立的 PostgreSQL 容器和独立用户，避免权限交叉和数据污染。

**数据库迁移策略 (Alembic)**:
- 使用 Alembic 管理数据库 Schema 变更
- 每次模型变更生成迁移脚本: `alembic revision --autogenerate -m "description"`
- 部署时自动执行迁移: `alembic upgrade head`
- 迁移脚本版本控制,禁止手动修改已应用的迁移
- 回滚支持: `alembic downgrade -1` (仅在开发环境使用)

---

## 3. 模块设计

### 3.1 16步流程调度引擎

**职责**: 编排16步标准流程的执行顺序和状态管理

**核心类**:
```python
class WorkflowEngine:
    """16步流程调度引擎"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.current_step: int = 1
        self.step_status: Dict[int, StepStatus] = {}

    async def execute_step(self, step_number: int, agent_id: str,
                          input_data: dict) -> StepResult:
        """执行指定步骤"""
        pass

    def get_dependency_graph(self) -> DirectedAcyclicGraph:
        """获取任务依赖图"""
        pass

    def check_step_prerequisites(self, step_number: int) -> bool:
        """检查步骤前置条件是否满足"""
        pass

class StepExecutor:
    """步骤执行器"""

    async def execute(self, step: int, context: ExecutionContext) -> Result:
        """
        执行流程:
        1. 海梅分派任务给对应命名Agent (Step 1-12)
        2. 命名Agent执行任务
        3. 后荣进行QA检验
        4. 检验合格提交代码库
        5. 检验不合格退回重做
        注: 编程Agent工具由后发/后达调度,Swarm Executor容器触发宿主机上的工具
        """
        pass

class RetryManager:
    """重试与回滚管理器"""

    MAX_RETRY: int = 3          # 最大重试次数
    RETRY_DELAY: int = 60       # 重试间隔（秒）,指数退避
    STEP_TIMEOUT: int = 1800    # 单步骤超时阈值（30分钟）

    async def execute_with_retry(self, step_func, step_number: int) -> Result:
        """
        重试策略:
        1. 首次执行失败后等待 60 秒重试
        2. 第二次失败后等待 120 秒重试
        3. 第三次失败后等待 240 秒重试
        4. 超过最大重试次数标记为 FAIL,触发海梅介入
        """
        pass

    async def save_checkpoint(self, step_number: int, state: dict) -> None:
        """保存中间状态到数据库,支持断点续传"""
        pass

    async def rollback_cascade(self, failed_step: int, project_id: str) -> None:
        """
        级联回滚:
        1. 将失败步骤及后续所有步骤状态重置为 PENDING
        2. 撤销失败步骤之后的所有代码提交
        3. 清理失败步骤产生的临时文件
        4. 记录回滚日志并通知海梅
        """
        pass
```

**状态机**:
```
Step 1 (人类创建) → Step 2 (海梅确认) → Step 3 (需求分析)
    → Step 4 (架构设计) → Step 5 (环境搭建) → Step 6 (TDD计划)
    → Step 7 (TDD用例) → Step 8 (代码计划) → Step 9 (功能代码)
    → Step 10 (测试部署) → Step 11 (全面测试) → Step 12 (安全审计)
    → Step 13 (生产部署) → Step 14 (文档完善) → Step 15 (交付报告)
    → Step 16 (满意度确认) → [满意: 完成 / 不满意: 回到Step 3]

步骤状态: PENDING → RUNNING → SUCCESS / FAIL / RETRYING
FAIL 状态: 触发重试 (最多3次) → 仍失败: 触发级联回滚 + 海梅介入
每一步完成后保存 checkpoint 到数据库,支持断电/异常后从 checkpoint 恢复
```

### 3.2 Agent蜂群调度模块

**职责**: 管理蜂群Agent的生命周期、任务分发、负载均衡

**核心类**:
```python
class SwarmManager:
    """蜂群管理器"""

    def __init__(self, project_id: str, manager_agent: str,
                 purpose: SwarmPurpose):
        self.project_id = project_id
        self.manager_agent = manager_agent  # 后发或后达
        self.purpose = purpose  # code_writing / test
        self.members: List[SwarmAgent] = []

    async def create_swarm(self, task_count: int) -> Swarm:
        """创建蜂群并选择合适的Agent"""
        pass

    async def dispatch_task(self, task: Task) -> Assignment:
        """
        任务分发策略:
        1. 根据任务类型匹配技能
        2. 选择负载最低的匹配Agent
        3. 发送任务到Swarm Executor容器
        4. Swarm Executor通过宿主机路径触发编程工具
        5. 监控执行进度
        """
        pass

    def get_load_balanced_agent(self, required_skills: List[str]) -> SwarmAgent:
        """负载均衡选择Agent"""
        pass
```

**Agent选择策略**:
1. 技能匹配度优先
2. 当前负载最低优先
3. 同类型Agent优先
4. 备用Agent选择: 技能匹配度≥80%

**蜂群Agent并发执行技术实现**:
- **进程隔离**: 每个编程 Agent 在独立子进程中运行,通过 `multiprocessing` 或容器化实现进程级别隔离
- **目录隔离**: 每个 Agent 分配独立的工作目录 `/DevFlow/projects/{project_id}/swarm/{agent_id}/`,避免文件系统冲突
- **文件锁机制**: 对共享资源（如项目配置文件）使用 `fcntl.flock()` 文件锁,防止并发写入冲突
- **任务分配**: Celery 按任务依赖图进行调度,无依赖的任务可并行执行,有依赖的任务串行等待
- **资源上限**: 同一项目蜂群最多并发 4 个编程 Agent，超过时进入队列等待
- **资源限制**: 每个编程 Agent 容器设置 CPU 上限 4 核、内存上限 8GB (deploy.resources.limits)，防止单个 Agent 耗尽宿主机资源
- **冲突解决**: 代码文件合并冲突时,由后发/后达进行人工审查和合并

### 3.3 QA门控检验引擎

**职责**: 执行自动化QA检验，量化打分，判定合格/不合格

**核心类**:
```python
class QAInspector:
    """QA检验引擎"""

    def __init__(self):
        self.dimensions: Dict[str, InspectionDimension] = {}

    async def inspect(self, artifact: Artifact, step: int) -> InspectionResult:
        """
        检验流程:
        1. 根据产出类型加载检验维度
        2. 逐项执行量化检验
        3. 计算综合评分
        4. 判定合格/不合格
        5. 生成检验报告
        """
        pass

class ScoringEngine:
    """打分引擎"""

    def calculate_composite_score(self, dimension_scores: List[float],
                                  weights: List[float] = None) -> float:
        """
        score = Σ(维度_i得分 × 权重_i) / Σ(权重_i)
        默认各维度权重均等
        """
        pass
```

### 3.4 项目讨论群协作模块

**职责**: 管理群组、讨论模式、会议模式

**核心类**:
```python
class GroupManager:
    """群组管理器"""

    async def create_group(self, project_id: str) -> Group:
        """第二步自动创建项目讨论群"""
        pass

    async def add_members(self, group_id: str,
                         agents: List[str], users: List[str]) -> None:
        """添加群组成员"""
        pass

class DiscussionMode:
    """讨论模式"""

    async def send_message(self, group_id: str, sender_id: str,
                          sender_type: str, content: str,
                          mentions: List[str]) -> Message:
        """发送消息并触发@mention回复"""
        pass

class MeetingMode:
    """会议模式"""

    async def start_meeting(self, group_id: str, host_agent: str,
                           meeting_type: str, agenda: List[str]) -> Meeting:
        """启动结构化会议"""
        pass
```

### 3.5 Hermes Gateway通信模块

**职责**: 与9个命名Agent角色的Gateway API通信

**核心类**:
```python
class GatewayClient:
    """Hermes Gateway客户端"""

    def __init__(self, agent_profile: str, port: int):
        self.base_url = f"http://localhost:{port}"
        self.semaphore = asyncio.Semaphore(5)  # 并发控制

    async def chat(self, messages: List[Message],
                   stream: bool = False) -> Response:
        """与Agent对话"""
        pass

    async def chat_stream(self, messages: List[Message]) -> AsyncGenerator:
        """流式对话 (SSE)"""
        pass

class ProfileScanner:
    """Profile扫描器"""

    def scan_profiles(self, profiles_dir: str) -> List[ProfileInfo]:
        """
        扫描 ~/.hermes/profiles/ 目录
        返回所有可用的Agent Profile信息
        """
        pass
```

### 3.6 WebSocket 多 Worker 通信设计

**职责**: 解决 WebSocket 长连接与多 Worker 进程路由问题

**问题说明**:
- 主后端 (backend) 使用多 Worker 处理 HTTP 请求
- WebSocket 长连接需要稳定的 Worker 绑定，多 Worker 环境下连接可能被重新路由导致断开
- 群聊消息需要在多个进程间共享状态

**解决方案**: 专用 WebSocket Worker

- 新增 `dedicated-websocket-worker` 服务，独立 uvicorn 进程，专用于处理 WebSocket 连接
- 主后端 `backend` workers 降为 2，专注于 HTTP API 请求
- Nginx 通过独立的 upstream `devflow_ws` 将 `/ws/` 请求路由到 WebSocket Worker
- 由于 WebSocket Worker 是单 Worker 进程，避免了多 Worker 路由导致连接断开的问题

**进程间通信机制**:

群聊消息需要在主后端和 WebSocket Worker 两个独立进程间共享，通过 Redis Pub/Sub 实现:

```
┌──────────────────┐         Redis Pub/Sub          ┌──────────────────────┐
│  backend (主后端) │ ◄──────────────────────────►  │ ws-worker (WebSocket)│
│  (workers=2)      │   Channel: group_messages      │  (单Worker,ws专用)   │
└──────────────────┘                                └──────────────────────┘
         │                                              │
         │  1. 人类用户发送消息→Nginx→backend            │
         │  2. backend 处理消息逻辑                     │
         │  3. backend 发布到 Redis Channel              │
         │  4. ws-worker 订阅 Channel 收到消息           │
         │  5. ws-worker 推送给在线 WebSocket 客户端     │
         │                                              │
         │  反向流程:                                    │
         │  1. 人类用户→Nginx→ws-worker                 │
         │  2. ws-worker 发布到 Redis Channel            │
         │  3. backend 订阅 Channel 收到消息             │
         │  4. backend 处理业务逻辑                      │
         │  5. 如需推送,再由 backend 发布回 Channel       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Redis Pub/Sub 设计**:
- Channel 命名规则: `group:{group_id}:messages` (按群组分频道)
- Channel 命名规则: `global:notifications` (全局通知)
- 消息格式: JSON，包含 sender_id、sender_type、content、timestamp、group_id
- backend 启动时订阅所有活跃群组的 Channel
- ws-worker 启动时订阅所有活跃群组的 Channel
- 消息写入 PostgreSQL 由 backend 负责，ws-worker 仅负责实时推送

---

## 4. 部署架构

### 4.1 容器化部署

**Docker Compose 编排**:

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./frontend/dist:/usr/share/nginx/html
    depends_on:
      - backend
      - dedicated-websocket-worker
    networks:
      - devflow_net

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:***@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - GITEA_URL=http://gitea:3000
      - SECRET_KEY=${SECRET_KEY}
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - redis
      - postgres
      - ollama
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - devflow_net

  dedicated-websocket-worker:
    build: ./backend
    command: uvicorn websocket.main:ws_app --host 0.0.0.0 --port 8001 --workers 1
    env_file:
      - .env
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - redis
      - backend
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=8
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:***@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ../../projects:/DevFlow/projects
    depends_on:
      - redis
      - postgres
    healthcheck:
      test: ["CMD-SHELL", "celery -A tasks inspect ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net

  celery-beat:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    env_file:
      - .env
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
    depends_on:
      - redis
    networks:
      - devflow_net

  swarm-executor:
    build: ./backend
    command: python -m swarm.executor --concurrency=4
    env_file:
      - .env
    environment:
      - SWARM_PROJECT_DIR=/DevFlow/projects
      - SWARM_AGENT_CONFIG=/etc/swarm/agents.yaml
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ../../projects:/DevFlow/projects
      - ./swarm-config:/etc/swarm
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - redis
      - backend
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:9100/health\")'"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=devflow
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d devflow"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - devflow_net

  gitea-postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=gitea
      - POSTGRES_USER=${GITEA_DB_USER}
      - POSTGRES_PASSWORD=${GITEA_DB_PASSWORD}
    volumes:
      - gitea_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${GITEA_DB_USER} -d gitea"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - devflow_net

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes --save 900 1 --save 300 10 --save 60 10000
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - devflow_net

  gitea:
    image: gitea/gitea:latest
    environment:
      - DATABASE_TYPE=postgres
      - DATABASE_HOST=gitea-postgres:5432
      - DATABASE_NAME=gitea
      - DATABASE_USER=${GITEA_DB_USER}
      - DATABASE_PASSWD=${GITEA_DB_PASSWORD}
    volumes:
      - gitea_data:/data
    depends_on:
      - gitea-postgres
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
      - ./scripts/ollama-entrypoint.sh:/entrypoint.sh
    ports:
      - "11434:11434"
    entrypoint: ["/entrypoint.sh"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    networks:
      - devflow_net

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    depends_on:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - devflow_net

  jaeger:
    image: jaegertracing/all-in-one:latest
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:14269"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - devflow_net

  filebeat:
    image: elastic/filebeat:8.11.0
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - elasticsearch
    healthcheck:
      test: ["CMD-SHELL", "filebeat test output"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - devflow_net

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - bootstrap.memory_lock=true
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - devflow_net

  kibana:
    image: kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:5601/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - devflow_net

volumes:
  pg_data:
  gitea_pg_data:
  redis_data:
  gitea_data:
  ollama_data:
  prometheus_data:
  es_data:

networks:
  devflow_net:
    driver: bridge
```

**Ollama Entrypoint 脚本** (`scripts/ollama-entrypoint.sh`):
```bash
#!/bin/bash
set -e

# 先拉取模型
echo "Pulling model qwen2.5:72b-instruct-q4_K_M..."
ollama pull qwen2.5:72b-instruct-q4_K_M

# 启动 Ollama 服务 (前台运行,保持容器存活)
echo "Starting Ollama server..."
exec ollama serve
```

**Redis 持久化说明**:
- RDB 快照: `--save 900 1` (900秒内至少1次写入则快照)、`--save 300 10` (300秒内至少10次写入则快照)、`--save 60 10000` (60秒内至少10000次写入则快照)
- AOF 追加: `--appendonly yes` (每条写命令追加到 appendonly.aof)
- RDB+AOF 双持久化策略: RDB 用于全量备份和快速恢复，AOF 用于增量恢复和数据完整性，灾难恢复能力显著提升

**Celery Worker 并发度说明**:
- concurrency=8，管理 9 个命名 Agent + 蜂群编排 + 定时任务 + 健康检查
- 原 concurrency=4 偏保守，可能成为瓶颈
- 如需进一步分离任务类型，可配置专用 Worker 队列:
  - `celery-worker-named`: 处理命名 Agent 任务 (concurrency=4)
  - `celery-worker-swarm`: 处理蜂群编排任务 (concurrency=4)
  - `celery-worker-scheduled`: 处理定时任务和巡检 (concurrency=2)

**编程 Agent 容器资源限制**:
- Swarm Executor 启动编程 Agent 容器时设置资源上限:
  - CPU 限制: 4 核 (`--cpus=4`)
  - 内存限制: 8GB (`--memory=8g`)
  - 只读文件系统: `--read-only`
  - 能力限制: `--cap-drop=ALL`
- 防止单个编程 Agent 耗尽宿主机资源
- 同一项目蜂群最多并发 4 个 Agent，总资源上限 16 核 CPU / 32GB 内存

### 4.2 .env 文件示例

```env
# DevFlow 数据库
POSTGRES_USER=devflow
POSTGRES_PASSWORD=<生成随机强密码>

# Gitea 数据库 (独立用户,与DevFlow隔离)
GITEA_DB_USER=gitea_admin
GITEA_DB_PASSWORD=<生成随机强密码>

# Redis (Celery Broker 与缓存共用同一密码)
REDIS_PASSWORD=<生成随机强密码>

# JWT 签名密钥
SECRET_KEY=<生成随机密钥,用于JWT签名>

# Hermes Agent API Key (后端与Agent间认证)
HERMES_AGENT_API_KEY=<生成随机API密钥>

# Agent蜂群 Webhook 签名密钥
SWARM_WEBHOOK_SECRET=<生成随机Webhook签名密钥>
```

**注意**: `.env` 文件应添加到 `.gitignore`，不纳入版本控制。

### 4.3 Hermes Agent 部署

9个命名Agent角色采用独立Profile部署:

| Agent | Profile | Gateway端口 | 默认模型 (本地) | 可选模型 (云端) |
|-------|---------|-------------|----------------|----------------|
| 海梅 | haimei | 8765 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后兴 | houxing | 8766 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后旺 | houwang | 8767 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后发 | houfa | 8768 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后达 | houda | 8769 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后富 | houfu | 8770 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后贵 | hougui | 8771 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后荣 | houro | 8772 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后华 | houhua | 8773 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |

**部署说明**:
- 9个Agent以宿主机进程方式运行，各自独立的 Hermes Profile 实例
- Agent 通过 Gateway API (端口 8765-8773) 与 FastAPI 后端通信
- Agent 访问 Ollama 推理服务: 由于 Ollama 部署在 Docker 容器内并映射端口 11434 到宿主机，Agent 通过 `http://localhost:11434` 访问
- FastAPI 后端访问 Ollama: 通过 Docker 内部网络 `http://ollama:11434`
- 默认模型为 `qwen2.5:72b-instruct-q4_K_M` (Qwen2.5-72B-Instruct INT4量化版)，通过 Ollama 容器加载推理

### 4.4 资源需求

**基础设施组件**:

| 组件 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| FastAPI后端 | 2核 | 4GB | 5GB |
| PostgreSQL (devflow) | 2核 | 4GB | 50GB |
| PostgreSQL (gitea) | 1核 | 2GB | 20GB |
| Redis | 1核 | 2GB | 5GB |
| Gitea | 1核 | 2GB | 50GB |
| Celery Worker | 2核 | 4GB | 5GB |
| Nginx | 1核 | 512MB | 1GB |
| Prometheus | 1核 | 2GB | 20GB |
| Jaeger | 1核 | 2GB | 10GB |
| Elasticsearch | 2核 | 4GB | 50GB |
| Kibana | 1核 | 2GB | 5GB |
| Ollama (服务进程) | 2核 | 0.5GB | 10GB |
| Swarm Executor | 1核 | 1GB | 2GB |
| WebSocket Worker | 1核 | 1GB | 1GB |
| **基础设施小计** | **20核** | **33GB** | **236GB** |

**Ollama 模型推理资源**:

| 组件 | CPU | 内存/显存 | 磁盘 |
|------|-----|-----------|------|
| qwen2.5:72b-instruct-q4_K_M (INT4量化) | - | ~36GB 显存/内存 | ~40GB |
| **模型推理小计** | **2核** | **36GB** | **40GB** |

**说明**:
- Ollama 服务进程本身仅需 0.5GB 内存，但加载 `qwen2.5:72b-instruct-q4_K_M` 模型后需额外 ~36GB 显存 (GPU) 或内存 (CPU 推理)
- 两者需分开核算：服务进程内存 0.5GB + 模型显存 36GB = Ollama 总占用约 36.5GB
- WSL 环境下 GPU 推理需额外配置 NVIDIA 容器工具链:
  - 宿主机安装 NVIDIA Driver + CUDA Toolkit
  - 安装 `nvidia-container-toolkit` (WSL2 下通过 `nvidia-ctk` 配置)
  - Docker 启动时附加 `--gpus all` (docker-compose 中通过 `deploy.resources.reservations.devices` 声明)
  - 确认 WSL2 中 `nvidia-smi` 可用且 GPU 内存可被容器识别

**Hermes Agent 进程资源**:

| 组件 | CPU (单个) | 内存 (单个) | 并发数 | CPU (总计) | 内存 (总计) |
|------|-----------|-------------|--------|-----------|-------------|
| 命名Agent进程 | 0.5核 | 512MB | 最多9个 | 4.5核 | 4.5GB |
| **Agent进程小计** | **4.5核** | **4.5GB** | - |

**Agent蜂群运行时资源**:

| 组件 | CPU (单个) | 内存 (单个) | 最大并发 | CPU (总计) | 内存 (总计) |
|------|-----------|-------------|----------|-----------|-------------|
| 编程Agent (Claude Code/Codex等) | 2核 | 4GB | 4个 | 8核 | 16GB |
| 编程Agent容器资源上限 | 4核/个 | 8GB/个 | 4个 | 16核(上限) | 32GB(上限) |
| **蜂群小计** | **8核** | **16GB** | - |

**总计 (峰值)**:

| 维度 | 总计 | 计算明细 |
|------|------|----------|
| CPU | 35核 | 20 (基础设施) + 2 (模型推理) + 4.5 (Agent进程) + 8 (蜂群) = 34.5核, 取整 35核 |
| 内存/显存 | 88GB | 33 (基础设施) + 36 (模型推理) + 4.5 (Agent进程) + 16 (蜂群) = 89.5GB, 取整 90GB |
| 磁盘 | 276GB | 236 (基础设施) + 40 (模型磁盘) = 276GB |

**说明**:
- 基础设施组件为持续运行资源 (含新增 WebSocket Worker 1核/1GB)
- Ollama 模型推理资源在模型加载后持续占用，`qwen2.5:72b-instruct-q4_K_M` INT4量化版约36GB显存/内存
- Hermes Agent 和蜂群资源为峰值估算，实际使用中不会所有Agent同时满载
- 生产部署建议配备：32核 CPU、96GB 内存 + 48GB GPU显存 (或 128GB 统一内存)、300GB 磁盘
- 单项目蜂群峰值: 8核 CPU/16GB 内存；10个并发项目蜂群峰值: 80核 CPU/160GB 内存 (编程 Agent 资源上限 16核/32GB 每项目)

### 4.5 网络拓扑

```
┌─────────────────────────────────────────────────────┐
│                    外部网络                           │
│              (人类用户 / 编程Agent)                   │
└───────────────────────────┬─────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │    Nginx      │
                    │  (443/80)     │
                    └───────┬───────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│         Docker 自定义网络 (devflow_net, bridge模式)    │
│                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐     │
│  │ FastAPI  │  │ WS Worker    │  │ Celery   │     │
│  │ :8000    │  │ :8001        │  │ Worker   │     │
│  │(backend) │  │(ws-worker)  │  │(celery-wk)│     │
│  │w=2       │  │w=1,ws专用   │  │c=8       │     │
│  └────┬─────┘  └────┬───────┘  └────┬─────┘     │
│       │              │                │            │
│  ┌────▼─────┐  ┌────▼─────┐  ┌──────▼───────┐   │
│  │  Postgres│  │  Redis   │  │ Celery Beat  │   │
│  │ :5432    │  │ :6379    │  │ (定时任务)    │   │
│  │(devflow) │  │(RDB+AOF) │  └──────────────┘   │
│  └──────────┘  └──────────┘                        │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Gitea   │  │  Postgres│  │  Ollama  │         │
│  │ :3000    │  │ :5432    │  │ :11434   │         │
│  │ (gitea)  │  │ (gitea)  │  │(模型推理) │         │
│  │ 仅内部   │  └──────────┘  └──────────┘         │
│  └──────────┘                                       │
│                                                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐        │
│  │Filebeat  │  │Elastic    │  │ Kibana   │        │
│  │ :5044    │  │ :9200     │  │ :5601    │        │
│  └──────────┘  └───────────┘  └──────────┘        │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│  │Prometheus│  │  Jaeger  │  │Swarm Executor│     │
│  │ :9090    │  │ :14269   │  │ (蜂群执行器)  │     │
│  └──────────┘  └──────────┘  └──────┬───────┘     │
│                                      │              │
│  注: 以上管理端口仅在 devflow_net 内可达,             │
│  不映射到宿主机 (仅 80/443/11434 对外暴露)           │
│  Gitea 通过 Nginx location /gitea/ 代理访问           │
└────────────────────────────────────────┬────────────┘
                                         │
┌────────────────────────────────────────▼────────────┐
│              宿主机 (Host)                           │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  9个Hermes Agent进程 (Gateway API)            │  │
│  │  端口: 8765-8773 (绑定127.0.0.1)              │  │
│  │  访问Ollama: http://localhost:11434           │  │
│  │  (Ollama容器端口映射到宿主机)                  │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  编程Agent工具 (CLI工具,安装在宿主机)           │  │
│  │  Claude Code / Codex / Opencode / 等          │  │
│  │  Swarm Executor容器通过挂载宿主机路径触发执行   │  │
│  │  或通过命名Agent直接调度                       │  │
│  │  资源限制: 单Agent 4核CPU/8GB内存              │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**跨网络通信说明**:
- Docker 内部网络 `devflow_net`: 所有容器通过该网络通信，使用容器名作为主机名 (如 `backend:8000`, `ollama:11434`, `gitea:3000`)
- Ollama 容器端口 11434 映射到宿主机，Docker 内部服务通过 `http://ollama:11434` 访问
- 宿主机上的 Hermes Agent 通过 `http://localhost:11434` 访问 Ollama
- FastAPI 后端与 Hermes Agent 通过宿主机端口 8765-8773 通信 (Gateway API)
- Swarm Executor 容器通过 Docker 网络与 Celery/Redis 通信，通过挂载的宿主机目录访问项目文件，通过宿主机路径触发编程 Agent 工具
- 仅端口 11434 (Ollama) 映射到宿主机，Gitea 不直接映射端口，统一通过 Nginx `location /gitea/` 代理访问
- 其余管理端口仅在 `devflow_net` 内可达

### 4.6 蜂群 Agent 执行环境

**部署架构说明**:

```
┌─────────────────────────────────────────────────────────────┐
│              Docker 容器 (devflow_net)                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Swarm Executor (swarm-executor 容器)                 │  │
│  │                                                      │  │
│  │  职责:                                                │  │
│  │  1. 接收 Celery Worker 分派的蜂群任务                  │  │
│  │  2. 根据任务类型选择合适的编程工具                      │  │
│  │  3. 通过宿主机路径启动编程工具进程                     │  │
│  │  4. 监控执行进度,收集输出                              │  │
│  │  5. 通过 Webhook 上报结果给 FastAPI 后端               │  │
│  │                                                      │  │
│  │  与宿主机交互方式:                                     │  │
│  │  - 挂载 /DevFlow/projects (读写项目文件)               │  │
│  │  - 挂载 /var/run/docker.sock (ro, 管理容器)           │  │
│  │  - 通过子进程调用宿主机上的编程工具 CLI                 │  │
│  └──────────────────────────┬───────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────┘
                               │ 子进程调用
┌──────────────────────────────▼──────────────────────────────┐
│              宿主机 (Host)                                   │
│                                                             │
│  编程工具安装路径 (示例):                                     │
│  /usr/local/bin/claude-code      (Claude Code CLI)          │
│  /usr/local/bin/codex            (OpenAI Codex CLI)         │
│  /usr/local/bin/opencode         (OpenCode CLI)             │
│  /usr/local/bin/hermes           (Hermes Agent CLI)         │
│                                                             │
│  触发示例 (Swarm Executor 容器内执行):                        │
│  $ claude-code --project /DevFlow/projects/{project_id}/    │
│                    --task "{task_description}"               │
│                    --output /DevFlow/projects/{project_id}/  │
│                                                             │
│  进程隔离:                                                   │
│  - 每个编程工具在独立子进程中运行                              │
│  - 工作目录隔离: /DevFlow/projects/{project_id}/swarm/{id}/  │
│  - 文件锁: 共享资源使用 fcntl.flock() 防止并发冲突            │
│  - 最大并发: 同一项目最多 4 个编程工具同时运行                 │
│  - 资源限制: 单Agent 4核CPU/8GB内存 (deploy.resources.limits)│
└─────────────────────────────────────────────────────────────┘
```

**关键设计决策**:
- **编程工具安装在宿主机**: Claude Code、Codex、Opencode 等工具需要完整的系统环境 (Node.js/Python/Git 等)，安装在宿主机上更可靠
- **Swarm Executor 为 Docker 容器**: 负责任务调度、工具选择、进度监控，通过挂载的宿主机路径触发编程工具
- **命名 Agent 直接调度**: 后发/后达命名 Agent 通过 Celery 任务将蜂群任务提交给 Swarm Executor，Swarm Executor 负责具体的工具启动和监控
- **结果上报**: 编程工具完成后，Swarm Executor 通过 Webhook (HMAC-SHA256 签名) 将结果上报给 FastAPI 后端
- **资源上限控制**: 编程 Agent 容器设置 CPU 上限 4 核、内存上限 8GB，防止单个 Agent 耗尽宿主机资源

### 4.7 Ollama 并发推理说明

**并发场景**:
- 10 个并发项目 × 9 个命名 Agent = 最多 90 个命名 Agent 进程
- 所有 Agent 共享同一个 Ollama 容器实例和同一个 `qwen2.5:72b-instruct-q4_K_M` 模型

**Ollama 并发处理能力**:
- Ollama 内置请求队列机制，当并发请求超过处理能力时自动排队
- `qwen2.5:72b-instruct-q4_K_M` (INT4量化) 在 GPU (48GB显存) 下单请求推理延迟约 200-500ms (取决于 prompt 长度和生成 token 数)
- 典型 QPS 估算:
  - GPU 模式 (48GB显存): 约 5-10 QPS (并发请求排队处理)
  - CPU 模式 (36GB内存): 约 1-2 QPS (显著 slower)
- Ollama 默认支持并发加载，但同一模型多副本会重复占用显存，故采用单模型实例 + 队列模式

**推理队列机制**:
- Ollama 内部维护请求队列，按到达顺序处理
- 命名 Agent 侧配置请求超时为 60 秒，避免无限等待
- 后端 Gateway Client 使用 `asyncio.Semaphore(5)` 限制对同一 Agent 的并发请求
- 高峰时段策略:
  - 非紧急任务 (文档生成、报告编写) 可延迟执行
  - 紧急任务 (QA检验、流程调度) 优先调度
  - Celery 任务队列天然支持排队，不会丢失请求

**资源瓶颈与优化**:
- 90 个 Agent 并非同时活跃，实际并发推理请求通常 < 10 个
- 如瓶颈明显，可考虑:
  - 为 Agent 分组分配云端模型 (OpenAI/Anthropic) 作为分流
  - 增大 GPU 显存 (如 A100 80GB) 提升单模型并发能力
  - 对轻量任务 (如简短回复) 使用更小的本地模型 (如 qwen2.5:7b-instruct)

---

## 5. 容灾与高可用

### 5.1 可用性目标

- **当前部署模式**: 单实例部署,可用性目标 99%
- **限制说明**: 单实例 PostgreSQL、Redis、Gitea、Ollama 存在单点故障风险,无法支撑 99% 以上 SLA
- **高可用扩展方案** (可选,按需实施):
  - **PostgreSQL**: 流复制 + Patroni 自动故障转移 (主从架构,2-3 节点)
  - **Redis**: Redis Sentinel 集群 (3 节点),自动选举主节点
  - **Gitea**: 多实例 + 共享存储 (NFS/分布式文件系统),前端 Nginx 负载均衡
  - **Ollama**: 多副本 + 模型缓存共享存储,前端 Nginx 负载均衡
  - **FastAPI**: 多副本 + Nginx 负载均衡,健康检查自动剔除故障节点
  - **预期可用性**: 扩展后可达 99.5%~99.9%

### 5.2 备份策略

| 数据 | 频率 | 保留 | 存储位置 |
|------|------|------|----------|
| PostgreSQL (devflow) | 每日全量 + 每6h增量 | 30天/90天/365天 | /data/backups/ |
| PostgreSQL (gitea) | 每日全量 | 30天 | /data/backups/ |
| 文件存储 | 每日全量 | 30天 | /data/backups/ |
| Gitea | Git历史 + 每日归档 | 永久 | 内置 + /data/backups/ |
| Ollama模型 | 首次部署拉取 | 永久 | ollama_data 卷 |
| Redis (RDB快照) | 按save规则自动 | 最新3份 | redis_data 卷 |

### 5.3 恢复目标

- **RTO** (恢复时间目标): < 2小时
- **RPO** (恢复点目标): < 1小时

### 5.4 健康检查

```python
@app.get("/health")
async def health_check():
    """系统健康检查"""
    checks = {
        "postgres": await check_postgres(),
        "redis": await check_redis(),
        "gitea": await check_gitea(),
        "hermes_agents": await check_hermes_agents(),
        "celery": await check_celery(),
        "ollama": await check_ollama(),
        "elasticsearch": await check_elasticsearch(),
        "kibana": await check_kibana(),
    }
    return {"status": "healthy" if all(checks.values()) else "degraded",
            "checks": checks}
```

**健康检查覆盖说明**:
- `check_postgres()`: 检查 DevFlow 主数据库连接和查询响应
- `check_redis()`: 检查 Redis PING 响应
- `check_gitea()`: 检查 Gitea API `/api/health` 端点
- `check_hermes_agents()`: 检查9个Agent Gateway API端口可达性
- `check_celery()`: 检查 Celery Worker 活跃状态
- `check_ollama()`: 检查 Ollama `/api/tags` 端点响应和模型加载状态
- `check_elasticsearch()`: 检查 ES `_cluster/health` 端点
- `check_kibana()`: 检查 Kibana `/api/status` 端点

**Docker 容器级健康检查** (已在 docker-compose 中配置):
- `backend`: `curl -sf http://localhost:8000/health` (30s 间隔)
- `dedicated-websocket-worker`: `curl -sf http://localhost:8001/health` (30s 间隔)
- `postgres`: `pg_isready -U ${POSTGRES_USER} -d devflow` (10s 间隔)
- `gitea-postgres`: `pg_isready -U ${GITEA_DB_USER} -d gitea` (10s 间隔)
- `redis`: `redis-cli -a ${REDIS_PASSWORD} ping` (10s 间隔)
- `gitea`: `curl -sf http://localhost:3000/api/health` (30s 间隔)
- `ollama`: `curl -sf http://localhost:11434/api/tags` (30s 间隔, 120s 启动等待)
- `elasticsearch`: `curl -sf http://localhost:9200/_cluster/health` (30s 间隔)
- `kibana`: `curl -sf http://localhost:5601/api/status` (30s 间隔)
- `celery-worker`: `celery -A tasks inspect ping` (30s 间隔)
- `swarm-executor`: `python -c 'import requests; requests.get("http://localhost:9100/health")'` (30s 间隔)
- `prometheus`: `curl -sf http://localhost:9090/-/healthy` (30s 间隔)
- `jaeger`: `curl -sf http://localhost:14269` (30s 间隔)
- `filebeat`: `filebeat test output` (30s 间隔)
- Nginx 健康检查由 Docker 容器自身 `healthcheck` 指令处理 (`curl -sf http://localhost/`)

---

## 6. 安全架构

### 6.1 认证与授权

**人类用户认证**:
- **认证**: JWT Token (Access Token 30分钟 + Refresh Token 7天)
- **授权**: RBAC (基于角色的访问控制)
- **项目隔离**: 用户仅可访问自身创建的项目

**RBAC 角色定义**:

| 角色 | 权限 | 说明 |
|------|------|------|
| admin (管理员) | 全部权限 | 系统管理、用户管理、项目创建、Agent配置、部署管理 |
| developer (项目成员) | 项目读写、群聊、进度查看 | 可参与项目开发、查看进度、群聊讨论 |
| viewer (只读) | 项目只读、群聊只读 | 仅查看项目进度和群聊历史,不可修改 |

**Hermes Agent 认证**:
- 9个命名Agent通过 API Key 向后端认证
- API Key 存储在 `.env` 的 `HERMES_AGENT_API_KEY` 变量中
- 后端通过自定义中间件验证请求头 `X-Hermes-API-Key`
- 每个 Agent Profile 配置中注入对应 API Key，通过 Gateway 请求头传递

**Agent蜂群认证**:
- 蜂群Agent通过 Webhook 签名认证上报结果
- Webhook 签名使用 HMAC-SHA256，密钥为 `.env` 中的 `SWARM_WEBHOOK_SECRET`
- 后端验证请求头 `X-Webhook-Signature` 与请求体的 HMAC 签名是否匹配
- 验证通过后处理蜂群上报的任务结果、进度和产物

**内部Docker网络策略**:
- 使用 Docker 自定义网络 `devflow_net` (bridge 模式)，非公网可达
- **仅以下端口映射到宿主机**: 80 (Nginx HTTP)、443 (Nginx HTTPS)、11434 (Ollama)
- **以下管理端口不映射到宿主机** (仅在 devflow_net 内可达):
  - PostgreSQL (5432)
  - Redis (6379)
  - Gitea (3000) — 通过 Nginx `location /gitea/` 代理访问
  - Elasticsearch (9200)
  - Kibana (5601)
  - Prometheus (9090)
  - Jaeger (16686/14268)
- Hermes Agent Gateway 端口 (8765-8773) 绑定 `127.0.0.1`，仅宿主机本地可达
- 容器间通信通过 Docker 内部网络 `devflow_net`，不受外部网络访问

### 6.2 数据传输

- 全站 HTTPS (TLS 1.3)
- WebSocket wss:// 加密
- Agent通信数据脱敏存储

### 6.3 敏感信息管理

- 所有密码、密钥存储在 `.env` 文件中,不纳入版本控制
- `.env` 文件权限设置为 `600` (仅属主可读)
- 容器内通过 `env_file` 注入环境变量,不暴露为 Docker 明文
- 数据库密码、Redis密码、JWT密钥、API Key、Webhook Secret 均通过 `.env` 管理

### 6.4 审计日志

所有关键操作记录日志:
- Agent任务分派
- QA检验结果
- 代码提交
- 错误和异常
- 用户登录/登出
- Agent认证失败事件
- 蜂群Webhook签名验证失败事件

---

## 7. 性能设计

### 7.1 性能指标目标

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 页面加载 | < 2秒 | Lighthouse 3次平均 |
| API响应 | < 3秒 (P95) | curl 10次请求 |
| 蜂群任务分发 | < 500ms | 接口计时 |
| QA检验处理 | < 1分钟/产出 | 计时统计 |
| 数据库查询 | < 100ms | pg_stat_statements |
| 群聊消息延迟 | < 100ms | WebSocket端到端 |

### 7.2 并发处理

- **并发项目数**: 10个
- **容量规划依据** (修订): 基于完整资源核算计算得出:
  - 服务器总资源: 35核 CPU、90GB 内存/显存 (峰值)
  - 基础设施持续占用: 20核 CPU、33GB 内存
  - Ollama 模型推理占用: 36GB 显存/内存 (`qwen2.5:72b-instruct-q4_K_M` INT4量化)
  - 可用资源: 约 13核 CPU、21GB 内存 (扣除基础设施和Ollama后)
  - 单个项目平均占用: CPU 0.8核 (含Agent执行峰值)、内存 2GB
  - 按 80% 资源利用率上限: CPU 可支撑约 16 个项目,内存可支撑约 10 个项目
  - 取内存为瓶颈: 保守估计 10 个并发项目
- **Agent并发限制**: 同Profile同一时间仅执行1个任务
- **WebSocket并发**: 单群组支持10+ Agent在线，由专用 WebSocket Worker 处理
- **API并发**: 信号量限制5个/Agent
- **Ollama并发**: 单模型实例 + 内部请求队列,约 5-10 QPS (GPU模式)

### 7.3 缓存策略

| 缓存内容 | TTL | 存储 |
|----------|-----|------|
| 用户Session | 30分钟 | Redis |
| 项目进度 | 5分钟 | Redis |
| Agent状态 | 1分钟 | Redis |
| 群聊消息 | 24小时 | Redis + PostgreSQL |
| 静态资源 | 1年 | Nginx + 浏览器 |

---

## 8. 监控与可观测性

### 8.1 指标采集 (Prometheus)

- **系统级**: CPU/内存/磁盘/网络 (30秒间隔)
- **应用级**: API响应时间/QPS/错误率 (10秒间隔)
- **Agent级**: 任务时长/成功率/负载 (30秒间隔)
- **业务级**: 项目数/QA通过率/步骤耗时 (实时)

### 8.2 链路追踪 (Jaeger)

- 每个Agent任务分配唯一Trace ID
- 追踪全链路: 分派→执行→检验→提交
- 保留7天

### 8.3 日志管理 (ELK Stack)

- **组件部署**: Elasticsearch + Logstash (由Filebeat替代) + Kibana
- **采集方式**: Filebeat 采集各容器日志,推送至 Elasticsearch
- **日志格式**: JSON结构化日志
- **保留策略**: 本地保留30天 + ELK保留90天
- **关键操作**: 所有关键操作必记日志,Kibana 配置实时告警查询

### 8.4 告警规则

| 告警类型 | 条件 | 通知方式 |
|----------|------|----------|
| CPU告警 | >85% 持续5分钟 | WebSocket + 邮件 |
| 内存告警 | >90% 持续3分钟 | WebSocket + 邮件 |
| API错误率 | >5% | WebSocket + 邮件 |
| Agent宕机 | 进程停止 | WebSocket + 邮件 |
| 任务超时 | >30分钟 | WebSocket + 邮件 |
| Ollama服务不可用 | /api/tags 无响应 | WebSocket + 邮件 |

---

文档结束
