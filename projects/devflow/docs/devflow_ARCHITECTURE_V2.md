# DevFlow 架构设计文档 V2.0

**项目**: DevFlow 项目管理平台
**版本**: 2.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: V1.0 修订 (根据后荣 QA 检验报告修改)

**变更日志**:
- V2.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 架构描述由"分层微服务架构"修正为"分层单体架构"
  - 9个命名Agent默认模型由 gpt-4o 改为本地部署模型 (Ollama + Qwen2.5-72B-Instruct),云端模型作为可选配置
  - docker-compose 中所有敏感配置迁移至 .env 文件引用
  - 可用性目标由 99.5% 下调至 99%,并补充高可用扩展方案说明
  - 补充完整数据流闭环: 人类用户→Nginx→FastAPI→Hermes Agent→编程Agent→代码库→QA检验→代码提交
  - 补充 16 步流程容错与回滚机制: 重试策略、断点续传、级联回滚方案
  - 修正 4.2 表格 Agent 数量与 4.4 网络拓扑注释不一致问题 (统一为 9 个)
  - 修正 Profile 名称拼写错误: 'houfl' → 'houfu'
  - 补充日志采集组件部署定义 (Filebeat + Elasticsearch + Kibana)
  - 补充数据库迁移方案 (Alembic)
  - 补充蜂群 Agent 并发执行技术实现说明 (进程隔离 + 文件锁)
  - 补充性能指标容量规划依据

---

## 1. 系统架构概述

### 1.1 架构目标

DevFlow 采用分层单体架构，核心设计理念：
- **职责单一**: 各层职责清晰分离，前端负责交互、后端负责业务逻辑、数据库负责持久化
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
│                          Nginx 反向代理                                  │
│              (静态资源 / SSL终止 / WebSocket代理 / 负载均衡)               │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────┐
│                      FastAPI 后端单体应用 (DevFlow Server)
│              (内部模块划分,非独立微服务,同一进程部署)                 │
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
   │ Gitea REST API      │ │ Redis        │ │ Prometheus         │
   │ (代码托管服务)       │ │ (缓存/队列)  │ │ (指标采集)         │
   └─────────────────────┘ └──────────────┘ └────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              9个命名Agent角色 (独立Hermes Profile实例)                  │
│  海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华 (Gateway API通信)         │
│  默认模型: 本地部署 (Ollama + Qwen2.5-72B-Instruct)                    │
│  可选模型: 云端 API (OpenAI/Anthropic 等) — 通过 config.yaml 配置切换   │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              Agent蜂群层 (编程Agent集群)                               │
│  Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma  │
│  hermes子agent / pi-codeing-agent子agent                               │
│  交互方式: Celery回调上报 + 轮询进度 + Webhook事件通知                   │
│  隔离方式: 独立进程 + 项目目录隔离 + 文件锁机制                         │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              数据持久层                                                 │
│  PostgreSQL (主数据库) + 文件存储 (项目文件夹) + Gitea (代码仓库)       │
│  数据流闭环: 人类用户→Nginx→FastAPI→Hermes Agent→编程Agent→           │
│            代码编写→Git提交→Gitea→QA检验→通过后入库→通知用户             │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.3 架构层次说明

| 层次 | 职责 | 技术选型 |
|------|------|----------|
| 表示层 | 用户界面交互、实时通信 | Vue 3 + Element Plus + WebSocket |
| 网关层 | 反向代理、SSL、负载均衡 | Nginx |
| 应用层 | 业务逻辑、任务调度、Agent协调 (单体应用内部模块) | FastAPI + Celery + asyncio |
| 集成层 | 代码托管、Agent通信、消息队列 | Gitea API + Hermes Gateway + Redis |
| 数据层 | 持久化存储、缓存 | PostgreSQL + Redis + 文件存储 |

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
    server 127.0.0.1:8000;
}

upstream gitea {
    server 127.0.0.1:3000;
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
        proxy_pass http://devflow_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /gitea/ {
        proxy_pass http://gitea;
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

| 系统 | 通信方式 | 用途 |
|------|----------|------|
| Hermes Agent (9个命名角色) | HTTP REST + WebSocket (Gateway API) | Agent对话、任务执行 |
| Gitea | REST API | 代码仓库管理、Git操作 |
| 编程Agent蜂群 | Celery回调 + 轮询进度 + Webhook事件通知 | 任务分发、进度上报、成果交付 |
| Prometheus | HTTP Push | 指标上报 |
| Jaeger | gRPC | 链路追踪上报 |

### 2.5 数据层 (Data Layer)

**职责**: 数据持久化、缓存、会话管理

| 组件 | 用途 | 配置 |
|------|------|------|
| PostgreSQL 14+ | 主数据库，存储项目、用户、任务、QA记录等 | 连接池: 20, 最大连接: 100 |
| Redis 6+ | 缓存、Celery Broker、WebSocket会话 | 内存: 2GB, 持久化: AOF |
| 文件存储 | 项目文件夹、文档、报告 | /DevFlow/projects/ |

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
        1. 海梅分派任务给对应Agent
        2. Agent执行任务
        3. 后荣进行QA检验
        4. 检验合格提交代码库
        5. 检验不合格退回重做
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
Step 1 (人类创建) → Step 2 (海梅确认) → Step 3 (需求分析)
    → Step 4 (架构设计) → Step 5 (环境搭建) → Step 6 (TDD计划)
    → Step 7 (TDD用例) → Step 8 (代码计划) → Step 9 (功能代码)
    → Step 10 (测试部署) → Step 11 (全面测试) → Step 12 (安全审计)
    → Step 13 (生产部署) → Step 14 (文档完善) → Step 15 (交付报告)
    → Step 16 (满意度确认) → [满意: 完成 / 不满意: 回到Step 3]
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
        3. 发送任务到Agent
        4. 监控执行进度
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
- **资源上限**: 同一项目蜂群最多并发 4 个编程 Agent,超过时进入队列等待
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

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - GITEA_URL=http://gitea:3000
      - SECRET_KEY=${SECRET_KEY}
      - CELERY_BROKER_URL=redis://${CELERY_BROKER_PASSWORD}@redis:6379/1
    depends_on:
      - postgres
      - redis
    volumes:
      - /DevFlow/projects:/DevFlow/projects

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=4
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - redis
      - postgres

  celery-beat:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    env_file:
      - .env
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - CELERY_BROKER_URL=redis://:${CELERY_BROKER_PASSWORD}@redis:6379/1
    depends_on:
      - redis

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=devflow
      - POSTGRES_USER=devflow
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  gitea:
    image: gitea/gitea:latest
    environment:
      - DATABASE_TYPE=postgres
      - DATABASE_HOST=postgres:5432
      - DATABASE_NAME=gitea
      - DATABASE_USER=${POSTGRES_USER}
      - DATABASE_PASSWD=${GITEA_DB_PASSWORD}
    volumes:
      - gitea_data:/data
    ports:
      - "3000:3000"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"

  filebeat:
    image: elastic/filebeat:8.11.0
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - elasticsearch

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  kibana:
    image: kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch


### 6.4 .env 文件示例

SHELL=/bin/bash
TRAE_INSTALL_DIR=/home/jim/trae-install
HERMES_MEDIA_TRUST_RECENT_FILES=1
DISCORD_REACTIONS=true
NVM_INC=/home/jim/.nvm/versions/node/v24.15.0/include/node
TERMINAL_DOCKER_FORWARD_ENV=[]
WSL2_GUI_APPS_ENABLED=1
HERMES_EXEC_ASK=1
GTK_IM_MODULE=fcitx5
CONDA_EXE=/home/jim/anaconda3/bin/conda
_CE_M=
WSL_DISTRO_NAME=Ubuntu-24.04
CURSOR_API_BASE_URL=http://127.0.0.1:4000
WT_SESSION=35d37cb5-8002-4c05-94a4-222a08ac3dcb
TERMINAL_CONTAINER_CPU=1
TERMINAL_ENV=local
HERMES_AGENT_NOTIFY_INTERVAL=600
group_sessions_per_user=True
FEISHU_ALLOWED_USERS=
LOCAL_OLLAMA_API_KEY=ollama-local
XMODIFIERS=@im=fcitx5
TERMINAL_CONTAINER_MEMORY=5120
FEISHU_CONNECTION_MODE=websocket
GBM_SZ_API_KEY=VLLM_API_KEY
NAME=Jim-GBM
PWD=/home/jim/DevFlow/projects/devflow/docs
GSETTINGS_SCHEMA_DIR=/home/jim/anaconda3/share/glib-2.0/schemas
LOGNAME=jim
SLACK_ALLOWED_CHANNELS=
CONDA_PREFIX=/home/jim/anaconda3
BROWSER_SESSION_TIMEOUT=300
timezone=
PNPM_HOME=/home/jim/.local/share/pnpm
WEB_TOOLS_DEBUG=false
GSETTINGS_SCHEMA_DIR_CONDA_BACKUP=
FEISHU_APP_SECRET=9HUOjve4Fks0aj7QOv2VifiT2ftwmH5k
MATRIX_ALLOWED_ROOMS=
TRAE_CN_BIN=/home/jim/trae-install/trae-cn/trae-cn
DISCORD_THREAD_REQUIRE_MENTION=false
HOME=/home/jim/.hermes/profiles/houwang/home
DISCORD_ALLOWED_CHANNELS=
DISCORD_HISTORY_BACKFILL_LIMIT=50
IMAGE_TOOLS_DEBUG=false
LANG=zh_CN.UTF-8
HERMES_SESSION_ID=api-7ca48f7e83433c64
WSL_INTEROP=/run/WSL/2415_interop
LS_COLORS=rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:mi=00:su=37;41:sg=30;43:ca=00:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arc=01;31:*.arj=01;31:*.taz=01;31:*.lha=01;31:*.lz4=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.tzo=01;31:*.t7z=01;31:*.zip=01;31:*.z=01;31:*.dz=01;31:*.gz=01;31:*.lrz=01;31:*.lz=01;31:*.lzo=01;31:*.xz=01;31:*.zst=01;31:*.tzst=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.alz=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.cab=01;31:*.wim=01;31:*.swm=01;31:*.dwm=01;31:*.esd=01;31:*.avif=01;35:*.jpg=01;35:*.jpeg=01;35:*.mjpg=01;35:*.mjpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.webp=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.m4a=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.oga=00;36:*.opus=00;36:*.spx=00;36:*.xspf=00;36:*~=00;90:*#=00;90:*.bak=00;90:*.crdownload=00;90:*.dpkg-dist=00;90:*.dpkg-new=00;90:*.dpkg-old=00;90:*.dpkg-tmp=00;90:*.old=00;90:*.orig=00;90:*.part=00;90:*.rej=00;90:*.rpmnew=00;90:*.rpmorig=00;90:*.rpmsave=00;90:*.swp=00;90:*.tmp=00;90:*.ucf-dist=00;90:*.ucf-new=00;90:*.ucf-old=00;90:
TERMINAL_DOCKER_RUN_AS_HOST_USER=False
TERMINAL_CONTAINER_DISK=51200
FEISHU_ALLOW_ALL_USERS=true
WAYLAND_DISPLAY=wayland-0
TENCENT_API_KEY=GBM LLM
CONDA_PROMPT_MODIFIER=(base) 
HERMES_ACP_BACKEND=opencode
DISCORD_HISTORY_BACKFILL=true
TERMINAL_TIMEOUT=180
TELEGRAM_REACTIONS=false
GBM_CQ_API_KEY=VLLM_API_KEY
SILICONFLOW_API_KEY=sk-kwnzpkscqihpqsizfhnbdkkbcimitshmkbsannwczzgsojxt
paste_collapse_threshold=5
BROWSERBASE_PROXIES=true
FEISHU_APP_ID=cli_a96b4d8794f85bc0
VISION_TOOLS_DEBUG=false
GEMINI_API_BASE=http://127.0.0.1:4000
TERMINAL_DOCKER_ENV={}
SLACK_FREE_RESPONSE_CHANNELS=
HERMES_QUIET=1
NVM_DIR=/home/jim/.nvm
HERMES_GATEWAY_TOKEN=54f1eba62398a14620c048b056853804b7a5b9c365f7ee9b
LESSCLOSE=/usr/bin/lesspipe %s %s
HERMES_GATEWAY_BUSY_INPUT_MODE=interrupt
BROWSER_INACTIVITY_TIMEOUT=120
TERM=xterm-256color
_CE_CONDA=
LESSOPEN=| /usr/bin/lesspipe %s
USER=jim
TERMINAL_SINGULARITY_IMAGE=docker://nikolaik/python-nodejs:python3.11-nodejs20
CONDA_SHLVL=1
HERMES_MEDIA_TRUST_RECENT_SECONDS=600
file_read_max_chars=100000
FEISHU_GROUP_POLICY=open
DISPLAY=:0
HERMES_AGENT_TIMEOUT_WARNING=900
SHLVL=2
NVM_CD_FLAGS=
HERMES_MEDIA_DELIVERY_STRICT=0
TELEGRAM_ALLOWED_CHATS=
QT_IM_MODULE=fcitx5
TERMINAL_DAYTONA_IMAGE=nikolaik/python-nodejs:python3.11-nodejs20
HERMES_RESTART_DRAIN_TIMEOUT=60
TERMINAL_MODAL_IMAGE=nikolaik/python-nodejs:python3.11-nodejs20
TERMINAL_PERSISTENT_SHELL=True
HERMES_AGENT_TIMEOUT=1800
TERMINAL_CWD=/home/jim
paste_collapse_char_threshold=2000
ZHIPU_API_KEY=cdba54f33686447f8c56f9515e7cbcee.Rwnxc2xSsLBUyhKq
CONDA_PYTHON_EXE=/home/jim/anaconda3/bin/python
prefill_messages_file=
IFLOW_API_KEY=sk-2195cea309453ffe4711f75e379346de
XDG_RUNTIME_DIR=/run/user/1000/
_config_version=16
SSL_CERT_FILE=/home/jim/.hermes/hermes-agent/venv/lib/python3.11/site-packages/certifi/cacert.pem
hooks_auto_accept=False
CONDA_DEFAULT_ENV=base
WSLENV=WT_SESSION:WT_PROFILE_ID:
TERMINAL_DOCKER_VOLUMES=[]
_HERMES_GATEWAY=1
LC_ALL=zh_CN.UTF-8
HERMES_REDACT_SECRETS=true
TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE=False
XDG_DATA_DIRS=/usr/local/share:/usr/share:/var/lib/snapd/desktop
HERMES_MAX_ITERATIONS=90
PATH=/home/jim/.local/bin:/home/jim/bin:/home/jim/.local/bin:/home/jim/trae-install/usr/share/trae-cn:/home/jim/.opencode/bin:/home/jim/.local/share/pnpm:/home/jim/.cargo/bin:/home/jim/.nvm/versions/node/v24.15.0/bin:/home/jim/.local/bin:/home/jim/anaconda3/bin:/home/jim/anaconda3/condabin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/usr/lib/wsl/lib:/mnt/d/Program Files/Java/jdk-23/bin:/mnt/c/Program Files/Common Files/Oracle/Java/javapath:/mnt/c/WINDOWS/system32:/mnt/c/WINDOWS:/mnt/c/WINDOWS/System32/Wbem:/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0:/mnt/c/WINDOWS/System32/OpenSSH:/mnt/d/Program Files (x86)/GTK2-Runtime/bin:/mnt/d/Program Files/GTK3-Runtime Win64/bin:/mnt/c/Program Files (x86)/Windows Kits/10/Windows Performance Toolkit:/mnt/d/ProgramData/miniconda3:/mnt/d/ProgramData/miniconda3/Scripts:/mnt/d/ProgramData/miniconda3/Library/bin:/mnt/d/flutter/bin:/mnt/d/gradle/bin:/mnt/c/bin/geckodriver:/mnt/d/Android/sdk/cmdline-tools/bin:/mnt/c/Program Files (x86)/Microsoft SQL Server/160/DTS/Binn:/mnt/d/Program Files/Go/bin:/mnt/d/Program Files/PuTTY:/mnt/d/Program Files/gs/gs10.06.0/bin:/mnt/c/Users/Lenovo/AppData/Local/Programs/cursor/resources/app/bin:/mnt/d/Program Files/CodeArts Agent/bin:/mnt/d/Program Files/Git/cmd:/mnt/c/Program Files/Docker/Docker/resources/bin:/mnt/d/Program Files/nodejs:/mnt/c/Users/Lenovo/AppData/Local/Programs/Python/Python314/Scripts:/mnt/c/Users/Lenovo/AppData/Local/Programs/Python/Python314:/mnt/c/Users/Lenovo/AppData/Local/Programs/Python/Launcher:/mnt/c/Users/Lenovo/AppData/Local/hermes/hermes-agent/venv/Scripts:/mnt/c/Users/Lenovo/.cargo/bin:/mnt/c/Users/Lenovo/AppData/Local/pnpm:/mnt/c/Users/Lenovo/.copaw/bin:/mnt/c/Users/Lenovo/Tools/node/node-v23.9.0-win-x64:/mnt/c/Users/Lenovo/Tools/dotnet:/mnt/c/Users/Lenovo/flutter/bin:/mnt/d/ProgramData/miniconda3:/mnt/d/ProgramData/miniconda3/envs/agent:/mnt/d/ProgramData/miniconda3/Library/usr/bin:/mnt/d/ProgramData/miniconda3/Library/bin:/mnt/d/ProgramData/miniconda3/Scripts:/mnt/d/ProgramData/miniconda3/bin:/mnt/d/ProgramData/miniconda3/condabin:/mnt/d/Program Files/Java/jdk-23/bin:/mnt/c/Program Files/Common Files/Oracle/Java/javapath:/mnt/c/WINDOWS/system32:/mnt/c/WINDOWS:/mnt/c/WINDOWS/System32/Wbem:/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0:/mnt/c/WINDOWS/System32/OpenSSH:/mnt/c/Program Files (x86)/Microsoft SQL Server/160/DTS/Binn:/mnt/c/Program Files/Azure Data Studio/bin:/mnt/d/Program Files/Git/cmd:/mnt/c/Users/Lenovo/AppData/Roaming/Python/Python312/Scripts:/mnt/d/Program Files (x86)/GTK2-Runtime/bin:/mnt/d/Program Files/GTK3-Runtime Win64/bin:/mnt/c/Program Files/Docker/Docker/resources/bin:/mnt/c/Program Files (x86)/Windows Kits/10/Windows Performance Toolkit:/mnt/d/flutter/bin:/mnt/d/gradle/bin:/mnt/c/ProgramData/chocolatey/bin:/mnt/c/ProgramData/chocolatey/lib/maven/apache-maven-3.9.9/bin:/mnt/c/bin/geckodriver:/mnt/d/Users/Lenovo/AppData/Local/Programs/Trae CN/bin:/mnt/c/Users/Lenovo/.local/bin:/mnt/c/Users/Lenovo/AppData/Local/Microsoft/WindowsApps:/mnt/c/Users/Lenovo/AppData/Local/Programs/Microsoft VS Code/bin:/mnt/c/Users/Lenovo/AppData/Local/Programs/Ollama:/mnt/c/Users/Lenovo/.lmstudio/bin:/mnt/c/Users/Lenovo/go/bin:/mnt/d/Users/Lenovo/AppData/Local/Programs/Lingma/bin:/mnt/c/Users/Lenovo/AppData/Local/Microsoft/WinGet/Links:/mnt/c/Users/Lenovo/AppData/Roaming/npm:/snap/bin:/tmp/bytedance-trae/.venv/bin:/home/jim/trae-install/trae-cn
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
BROWSERBASE_ADVANCED_STEALTH=false
NVM_BIN=/home/jim/.nvm/versions/node/v24.15.0/bin
HOSTTYPE=x86_64
TERMINAL_CONTAINER_PERSISTENT=True
TERMINAL_DOCKER_IMAGE=nikolaik/python-nodejs:python3.11-nodejs20
FEISHU_DOMAIN=feishu
SLACK_REQUIRE_MENTION=true
MOA_TOOLS_DEBUG=false
paste_collapse_threshold_fallback=5
PCB_CY_PASSWORD=openclaw2026!
PULSE_SERVER=unix:/mnt/wslg/PulseServer
TERMINAL_LIFETIME_SECONDS=300
WT_PROFILE_ID={d8e96812-b789-5068-a5ae-10b2fb53e95f}
PCB_CY_USERNAME=fzy
OLDPWD=/home/jim/DevFlow/projects/devflow/docs
HERMES_AUTO_CONTINUE_FRESHNESS=3600
HERMES_HOME=/home/jim/.hermes/profiles/houwang
CURSOR_API_KEY=any-value
_=/usr/bin/env

**注意**:  文件应添加到 ，不纳入版本控制。
volumes:
  pg_data:
  redis_data:
  gitea_data:
  prometheus_data:
  es_data:
```

### 4.2 Hermes Agent 部署

9个命名Agent角色采用独立Profile部署:

| Agent | Profile | Gateway端口 | 默认模型 (本地) | 可选模型 (云端) |
|-------|---------|-------------|----------------|----------------|
| 海梅 | haimei | 8765 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后兴 | houxing | 8766 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后旺 | houwang | 8767 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后发 | houfa | 8768 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后达 | houda | 8769 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后富 | houfu | 8770 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后贵 | hougui | 8771 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后荣 | houro | 8772 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |
| 后华 | houhua | 8773 | Qwen2.5-72B-Instruct (Ollama) | gpt-4o |

### 4.3 资源需求

| 组件 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| FastAPI后端 | 2核 | 4GB | 5GB |
| PostgreSQL | 2核 | 4GB | 50GB |
| Redis | 1核 | 2GB | 5GB |
| Gitea | 1核 | 2GB | 50GB |
| Celery Worker | 2核 | 4GB | 5GB |
| Nginx | 1核 | 512MB | 1GB |
| Prometheus | 1核 | 2GB | 20GB |
| Jaeger | 1核 | 2GB | 10GB |
| Elasticsearch | 2核 | 4GB | 50GB |
| Kibana | 1核 | 2GB | 5GB |
| **总计** | **15核** | **32.5GB** | **216GB** |

### 4.4 网络拓扑

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
│                  内部网络 (Docker Network)            │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ FastAPI  │  │ Celery   │  │  Redis   │         │
│  │ :8000    │  │ Worker   │  │ :6379    │         │
│  └────┬─────┘  └────┬─────┘  └──────────┘         │
│       │              │                              │
│  ┌────▼──────────────▼──────────┐                  │
│  │        PostgreSQL :5432      │                  │
│  └──────────────────────────────┘                  │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Gitea   │  │Prometheus│  │  Jaeger  │         │
│  │ :3000    │  │ :9090    │  │ :16686   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐        │
│  │Filebeat  │  │Elastic    │  │ Kibana   │        │
│  │ :5044    │  │ :9200     │  │ :5601    │        │
│  └──────────┘  └───────────┘  └──────────┘        │
└─────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│              Hermes Agent (宿主机)                   │
│  9个Agent通过Gateway API与后端通信                   │
│  端口范围: 8765-8773                                 │
│  Ollama服务 (本地模型推理): 端口 11434                │
└─────────────────────────────────────────────────────┘
```

---

## 5. 容灾与高可用

### 5.1 可用性目标

- **当前部署模式**: 单实例部署,可用性目标 99%
- **限制说明**: 单实例 PostgreSQL、Redis、Gitea 存在单点故障风险,无法支撑 99% 以上 SLA
- **高可用扩展方案** (可选,按需实施):
  - **PostgreSQL**: 流复制 + Patroni 自动故障转移 (主从架构,2-3 节点)
  - **Redis**: Redis Sentinel 集群 (3 节点),自动选举主节点
  - **Gitea**: 多实例 + 共享存储 (NFS/分布式文件系统),前端 Nginx 负载均衡
  - **FastAPI**: 多副本 + Nginx 负载均衡,健康检查自动剔除故障节点
  - **预期可用性**: 扩展后可达 99.5%~99.9%

### 5.2 备份策略

| 数据 | 频率 | 保留 | 存储位置 |
|------|------|------|----------|
| PostgreSQL | 每日全量 + 每6h增量 | 30天/90天/365天 | /data/backups/ |
| 文件存储 | 每日全量 | 30天 | /data/backups/ |
| Gitea | Git历史 + 每日归档 | 永久 | 内置 + /data/backups/ |

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
    }
    return {"status": "healthy" if all(checks.values()) else "degraded",
            "checks": checks}
```

---

## 6. 安全架构

### 6.1 认证与授权

- **认证**: JWT Token (Access Token 30分钟 + Refresh Token 7天)
- **授权**: RBAC (基于角色的访问控制)
- **项目隔离**: 用户仅可访问自身创建的项目
- **敏感信息**: 所有密码、密钥存储在 .env 文件中,不纳入版本控制

### 6.2 数据传输

- 全站 HTTPS (TLS 1.3)
- WebSocket wss:// 加密
- Agent通信数据脱敏存储

### 6.3 审计日志

所有关键操作记录日志:
- Agent任务分派
- QA检验结果
- 代码提交
- 错误和异常
- 用户登录/登出

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

- **并发项目数**: 20个
- **容量规划依据**: 基于以下负载模型计算得出:
  - 单个项目平均占用: CPU 0.3核、内存 1.5GB (含 Agent 执行期间峰值)
  - 服务器总资源: 15核 CPU、32.5GB 内存 (扣除基础设施组件占用后约 10核/20GB 可用于项目)
  - 按 80% 资源利用率上限: CPU 可支撑约 26 个项目,内存可支撑约 13 个项目
  - 取内存为瓶颈: 13 个项目,考虑项目间资源复用和空闲时段,保守估计 20 个并发项目
- **Agent并发限制**: 同Profile同一时间仅执行1个任务
- **WebSocket并发**: 单群组支持10+ Agent在线
- **API并发**: 信号量限制5个/Agent

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

---

文档结束
