# DevFlow 架构设计文档 V8.0

**项目**: DevFlow 项目管理平台
**版本**: 8.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: V7.0 修订 (根据后荣 QA 检验报告修订)

**变更日志**:
- V8.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 【严重问题1】文档完整性补全: 补全 V7.0 中缺失的章节，包括 API 契约 (9.1)、数据流与 16 步完整映射 (9.2)、编程工具生命周期管理 (10.1)、通知机制 (10.2)、优雅关停与灾难恢复 (11.3)
  - 【严重问题2】可用性声明修正: 将 "99%可用性" 修正为 "99% 单实例目标"，明确单实例部署的实际限制，移除不切实际的 HA 承诺，高可用扩展方案标注为可选
  - 【严重问题3】GPU 硬件规格补全: 在 4.4 节新增 GPU 硬件规格表，明确 NVIDIA GPU 最低要求 (RTX 4090 24GB 显存或更高)，补充 WSL2 GPU 直通配置步骤
  - 【严重问题4】命名 Agent 部署模型修正: 在 4.3 节明确命名 Agent 为宿主机进程的原因 (Hermes Profile 依赖完整系统环境)，补充 systemd 服务管理、健康检查、自动重启机制
  - 【严重问题5】架构术语统一: 将 "单体应用" 修正为 "单体后端 + 分布式组件" 架构，在 1.1/1.2/1.3 节统一术语，明确 FastAPI 为单体后端，其余 20+ 进程为分布式组件
  - 【中等问题6】服务间认证详细设计: 在 6.1 节新增 6.1.1-6.1.4 小节，分别详述命名 Agent 认证、Swarm Executor 认证、编程工具认证、Gitea Webhook 验证
  - 【中等问题7】优雅关停与灾难恢复: 新增 11.3 节，描述系统优雅关停流程、16 步工作流中断处理、崩溃后恢复方案、工作流状态持久化策略
  - 【中等问题8】Celery 并发度与资源分配: 在 4.1 节补充 Celery concurrency=8 的详细计算依据，按任务类型划分专用队列
  - 【中等问题9】Redis 持久化策略调整: 由 RDB+AOF 双持久化调整为 AOF-only (everysec fsync)，定期全量备份由 cron 任务执行 pg_dump/RDB dump
  - 【中等问题10】Swarm Executor 角色定义: 在 4.6 节和 9.2 节明确 Swarm Executor 与命名 Agent 的关系和执行边界
  - 【建议改进11】16 步 Step 13-16 映射: 在 9.2 节补充完整 16 步流程映射，含 Step 13-16 的 Agent 角色和执行详情
  - 【建议改进12】Jaeger 分布式追踪上下文传播: 在 8.2 节补充 trace ID 传播机制，FastAPI→Celery→命名 Agent→Swarm Executor 的全链路追踪
  - 【建议改进13】内存/RAM 规格补全: 在 4.4 节补充完整的内存规格，区分系统内存和 GPU 显存
  - 【建议改进14】编程工具生命周期管理: 新增 10.1 节，描述 9 个编程工具的生命周期管理、进程隔离、资源限制、冲突解决
  - 【建议改进15】通知机制描述: 新增 10.2 节，描述 WebSocket 实时推送 + 邮件通知 + 站内通知三种通知渠道

- V7.0 (2026-06-13): 根据后荣 QA 检验报告修订 (docker-compose 端口安全、Ollama entrypoint、Redis 持久化、Celery 并发度等)
- V6.0 (2026-06-13): 根据后荣 QA 检验报告修订 (架构描述修正、Ollama 部署、Gitea 数据库隔离等)

---

## 1. 系统架构概述

### 1.1 架构目标

DevFlow 采用 **单体后端 + 分布式组件** 架构，核心设计理念：

- **单体后端**: FastAPI 为单一进程应用，各业务模块通过 Python 包结构划分，非独立部署的微服务。Celery Worker、WebSocket Worker 为后端的辅助进程，共享代码库和数据模型
- **分布式组件**: 数据库 (PostgreSQL)、缓存 (Redis)、代码托管 (Gitea)、推理引擎 (Ollama)、监控 (Prometheus/Jaeger/ELK)、9 个命名 Agent 进程、编程工具 (Claude Code/Codex 等) 均为独立运行的进程或容器，通过 Docker 网络或宿主机端口与后端通信
- **实际进程数**: 完整部署包含 20+ 个进程 (FastAPI、Celery Worker、Celery Beat、WebSocket Worker、Swarm Executor、9 个命名 Agent、Nginx、PostgreSQL×2、Redis、Gitea、Ollama、Prometheus、Jaeger、Elasticsearch、Kibana、Filebeat)
- **可用性**: 当前为单实例部署，可用性目标 99% (每年约 87.6 小时停机)。高可用扩展方案见 5.1 节
- **可扩展**: 模块化设计支持新增 Agent 类型和功能模块快速接入
- **可观测**: 全链路监控、日志、告警体系覆盖系统运行状态

### 1.2 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        人类用户 (Client)                                 │
│              浏览器 / 移动端 (需求/进度/群聊/会议)                        │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │ HTTP/HTTPS + WebSocket
┌───────────────────────────────────────▼─────────────────────────────────┐
│                          Nginx 反向代理 (容器: nginx)                     │
│              (静态资源 / SSL终止 / WebSocket代理)                         │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────┐
│              FastAPI 单体后端 (容器: backend + 辅助进程)                   │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  backend (uvicorn, workers=2) — HTTP API 请求处理                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  dedicated-websocket-worker (uvicorn, workers=1) — WebSocket     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  celery-worker (concurrency=8) — 异步任务调度 / Agent 执行编排     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  celery-beat — 定时任务调度                                        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  swarm-executor — 编程 Agent 蜂群调度与执行                         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  内部模块 (Python 包结构，非微服务):                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 16步流程调度  │  │ Agent蜂群调度 │  │ QA门控检验   │  │ 群聊协作   │ │
│  │ 引擎模块     │  │ 管理模块     │  │ 引擎模块     │  │ 模块       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Profile扫描  │  │ Gateway通信  │  │ Gitea代码库  │  │ 通知推送   │ │
│  │ 同步模块     │  │ 客户端模块   │  │ 集成模块     │  │ 模块       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└───────────────────────────┬─────────────────────────────────────────────┘
              │                    │                    │
   ┌──────────▼──────────┐ ┌──────▼───────┐ ┌─────────▼──────────┐
   │ Gitea (容器)        │ │ Redis (容器) │ │ Ollama (容器+GPU)  │
   │ 代码托管服务        │ │ 缓存/队列    │ │ 本地模型推理       │
   └─────────────────────┘ └──────────────┘ └────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              9个命名Agent角色 (宿主机进程, systemd 管理)                 │
│  海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华                           │
│  端口: 8765-8773 (绑定 127.0.0.1)                                     │
│  默认模型: Ollama 容器 + qwen2.5:72b-instruct-q4_K_M (需GPU)          │
│  可选模型: 云端 API (OpenAI/Anthropic 等) — 通过 config.yaml 切换      │
│  管理方式: systemd 服务, 自动重启, 健康检查                            │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              Swarm Executor (容器: swarm-executor)                     │
│  职责: 接收 Celery 任务, 选择并触发编程工具, 监控执行, 上报结果         │
│  与命名 Agent 关系: 命名 Agent (后发/后达) 提交任务→Celery→Swarm Executor│
└────────────────────────────────────────────────────────────────────────┘
              │ 触发 (通过子进程调用宿主机路径)
┌─────────────▼─────────────────────────────────────────────────────────┐
│              编程Agent工具 (宿主机 CLI 工具)                            │
│  Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma  │
│  hermes子agent / pi-codeing-agent子agent                               │
│  生命周期: Swarm Executor 管理启动/运行/停止/清理                       │
│  资源限制: 单 Agent 4 核 CPU / 8GB 内存                                │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              数据持久层 (容器)                                          │
│  PostgreSQL (devflow) + PostgreSQL (gitea)                             │
│  Redis (AOF持久化) + 文件存储 (/DevFlow/projects/) + Gitea (代码仓库)  │
│  数据流: 人类用户→Nginx→FastAPI→命名Agent (Step1-12)→后荣QA检验→       │
│        检验通过→Swarm Executor→编程工具→Git提交→Gitea→通知用户          │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.3 架构层次说明

| 层次 | 职责 | 技术选型 | 部署方式 |
|------|------|----------|----------|
| 表示层 | 用户界面交互、实时通信 | Vue 3 + Element Plus + WebSocket | Nginx 容器 (静态文件) |
| 网关层 | 反向代理、SSL、WebSocket 代理 | Nginx | Nginx 容器 |
| 应用层 (单体后端) | 业务逻辑、任务调度、Agent 协调 | FastAPI + Celery + asyncio | Docker 容器 (backend 及辅助进程) |
| 集成层 | 代码托管、Agent 通信、消息队列、推理引擎 | Gitea API + Hermes Gateway + Redis + Ollama | 独立容器 / 宿主机进程 |
| 数据层 | 持久化存储、缓存 | PostgreSQL + Redis + 文件存储 | Docker 容器 |

**术语说明**:
- "单体后端" 指 FastAPI 为单一应用进程，Celery Worker、WebSocket Worker、Swarm Executor 为同一代码库的辅助进程
- "分布式组件" 指数据库、缓存、代码托管、监控、推理引擎、命名 Agent 等独立运行的服务
- 整个系统包含 20+ 个进程，是分布式部署的单体后端应用，非微服务架构

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

**Nginx 配置**:
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

    # 静态资源 (前端 SPA)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # FastAPI 后端 API
    location /api/ {
        proxy_pass http://devflow_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 群聊 (独立 Worker)
    location /ws/ {
        proxy_pass http://devflow_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Gitea (内部代理, 不直接暴露端口)
    location /gitea/ {
        proxy_pass http://gitea;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
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

**说明**: FastAPI 后端为单体应用, 各模块在同一代码库中运行, 通过 Python 包结构进行逻辑划分。Celery Worker、WebSocket Worker、Swarm Executor 为同一代码库的辅助进程，各自独立运行但共享数据模型和业务逻辑。

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
| Hermes Agent (9个命名角色) | HTTP REST + WebSocket (Gateway API) | Agent对话、任务执行 | 宿主机进程 (systemd管理) |
| Ollama | HTTP REST (容器内: `ollama:11434`) | 本地模型推理服务 | Docker 容器 (GPU) |
| Gitea | REST API (容器内: `gitea:3000`) | 代码仓库管理、Git操作 | Docker 容器 |
| 编程Agent工具 (蜂群) | Swarm Executor→子进程调用 | 任务分发、进度上报、成果交付 | 宿主机 CLI 工具 |
| Prometheus | HTTP Push | 指标上报 | Docker 容器 |
| Jaeger | gRPC | 链路追踪上报 | Docker 容器 |

### 2.5 数据层 (Data Layer)

**职责**: 数据持久化、缓存、会话管理

| 组件 | 用途 | 配置 |
|------|------|------|
| PostgreSQL (devflow) | DevFlow主数据库，存储项目、用户、任务、QA记录等 | 连接池: 20, 最大连接: 100 |
| PostgreSQL (gitea) | Gitea独立数据库，存储Gitea元数据 | 独立用户 gitea_admin |
| Redis 6+ | 缓存、Celery Broker、WebSocket会话 | 内存: 2GB, 持久化: AOF (everysec fsync) |
| 文件存储 | 项目文件夹、文档、报告 | /DevFlow/projects/ |

**数据库隔离说明**: DevFlow 和 Gitea 使用独立的 PostgreSQL 容器和独立用户，避免权限交叉和数据污染。

**Redis 持久化策略**:
- AOF-only 模式: `--appendonly yes --appendfsync everysec`
- 放弃 RDB 快照，避免双持久化的 I/O 开销
- 定期全量备份由 cron 任务执行 `redis-cli BGSAVE` + 文件归档
- AOF 重写: `--auto-aof-rewrite-percentage 100 --auto-aof-rewrite-min-size 64mb`

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
        注: Step 13-16 为部署、文档、交付、确认阶段
        编程Agent工具由后发/后达调度, Swarm Executor 容器触发
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

    async def save_checkpoint(self, stage: str, state: dict) -> None:
        """
        保存中间状态到数据库,支持断点续传和崩溃恢复
        checkpoint 粒度: 步骤级别 + 步骤内关键阶段级别
        """
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
每步完成后保存 checkpoint 到数据库
步骤内关键操作前也保存 checkpoint (如代码编写开始、测试执行开始)
支持断电/异常后从最近 checkpoint 恢复
```

### 3.2 Agent蜂群调度模块

**职责**: 管理蜂群Agent的生命周期、任务分发、负载均衡

**核心类**:
```python
class SwarmManager:
    """蜂群管理器 (FastAPI 后端模块)"""

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
        3. 发送任务到 Swarm Executor 容器
        4. Swarm Executor 通过子进程调用宿主机上的编程工具
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
- **进程隔离**: 每个编程 Agent 在独立子进程中运行
- **目录隔离**: 每个 Agent 分配独立的工作目录 `/DevFlow/projects/{project_id}/swarm/{agent_id}/`
- **文件锁机制**: 对共享资源使用 `fcntl.flock()` 文件锁
- **任务分配**: Celery 按任务依赖图进行调度, 无依赖的任务可并行执行
- **资源上限**: 同一项目蜂群最多并发 4 个编程 Agent
- **资源限制**: 单编程 Agent 4 核 CPU / 8GB 内存
- **冲突解决**: 代码文件合并冲突时, 由后发/后达进行人工审查和合并

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
        self.base_url = f"http://127.0.0.1:{port}"
        self.semaphore = asyncio.Semaphore(5)  # 并发控制
        self.api_key = os.environ["HERMES_AGENT_API_KEY"]

    async def chat(self, messages: List[Message],
                   stream: bool = False) -> Response:
        """与Agent对话 (携带 API Key 认证)"""
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
- WebSocket 长连接需要稳定的 Worker 绑定
- 群聊消息需要在多个进程间共享状态

**解决方案**: 专用 WebSocket Worker

- 新增 `dedicated-websocket-worker` 服务，独立 uvicorn 进程，专用于处理 WebSocket 连接
- 主后端 `backend` workers 降为 2，专注于 HTTP API 请求
- Nginx 通过独立的 upstream `devflow_ws` 将 `/ws/` 请求路由到 WebSocket Worker
- WebSocket Worker 为单 Worker 进程，避免多 Worker 路由导致连接断开

**进程间通信机制 (Redis Pub/Sub)**:

```
┌──────────────────┐         Redis Pub/Sub          ┌──────────────────────┐
│  backend (主后端) │ ◄──────────────────────────►  │ ws-worker (WebSocket)│
│  (workers=2)      │   Channel: group:{group_id}:  │  (单Worker,ws专用)   │
└──────────────────┘   messages                    └──────────────────────┘
         │                                              │
         │  正向流程: 人类用户→Nginx→backend 处理        │
         │  1. backend 处理消息逻辑                     │
         │  2. backend 发布到 Redis Channel             │
         │  3. ws-worker 订阅 Channel 收到消息           │
         │  4. ws-worker 推送给在线 WebSocket 客户端     │
         │                                              │
         │  反向流程: 人类用户→Nginx→ws-worker           │
         │  1. ws-worker 发布到 Redis Channel            │
         │  2. backend 订阅 Channel 收到消息             │
         │  3. backend 处理业务逻辑                      │
         │  4. 如需推送, 再由 backend 发布回 Channel     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Redis Pub/Sub 设计**:
- Channel 命名: `group:{group_id}:messages` (按群组分频道)
- Channel 命名: `global:notifications` (全局通知)
- 消息格式: JSON (sender_id, sender_type, content, timestamp, group_id)
- backend 和 ws-worker 启动时订阅所有活跃群组的 Channel
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
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes --appendfsync everysec --auto-aof-rewrite-percentage 100 --auto-aof-rewrite-min-size 64mb
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

# 启动 Ollama 服务 (前台运行, 保持容器存活)
echo "Starting Ollama server..."
exec ollama serve
```

**Redis 持久化说明 (AOF-only)**:
- AOF 模式: `--appendonly yes --appendfsync everysec` (每秒 fsync, 最多丢失 1 秒数据)
- 不启用 RDB 快照，避免双持久化的 I/O 开销和恢复歧义
- AOF 自动重写: 当 AOF 文件大小增长 100% 且大于 64MB 时触发重写
- 定期全量备份: cron 任务每日执行 `redis-cli BGSAVE` + 归档 `dump.rdb` 到备份存储
- 恢复策略: AOF 文件支持增量恢复，崩溃后从 AOF 恢复未持久化的最后 1 秒数据

**Celery Worker 并发度说明 (concurrency=8)**:
- 计算依据: 8 个并发 worker 处理以下任务类型:
  - 命名 Agent 任务 (Step 1-12 执行): 平均 2-3 个并发
  - 蜂群编排任务 (Swarm Executor 调度): 平均 1-2 个并发
  - 定时任务 (健康检查、备份、巡检): 平均 1-2 个并发
  - 通知推送、文档同步等辅助任务: 平均 1-2 个并发
- 8 个 worker 在 10 个并发项目场景下足够使用，因 16 步流程为顺序执行
- 如需进一步分离任务类型，可配置专用 Worker 队列:
  - `celery-worker-named`: 命名 Agent 任务 (concurrency=4)
  - `celery-worker-swarm`: 蜂群编排任务 (concurrency=4)
  - `celery-worker-scheduled`: 定时任务和巡检 (concurrency=2)

**编程 Agent 容器资源限制**:
- Swarm Executor 启动编程 Agent 时设置资源上限:
  - CPU 限制: 4 核 (`--cpus=4`)
  - 内存限制: 8GB (`--memory=8g`)
  - 只读文件系统: `--read-only`
  - 能力限制: `--cap-drop=ALL`
- 同一项目蜂群最多并发 4 个 Agent，总资源上限 16 核 CPU / 32GB 内存

### 4.2 .env 文件示例

```env
# DevFlow 数据库
POSTGRES_USER=devflow
POSTGRES_PASSWORD=<生成随机强密码>

# Gitea 数据库 (独立用户, 与DevFlow隔离)
GITEA_DB_USER=gitea_admin
GITEA_DB_PASSWORD=<生成随机强密码>

# Redis (Celery Broker 与缓存共用同一密码)
REDIS_PASSWORD=<生成随机强密码>

# JWT 签名密钥
SECRET_KEY=<生成随机密钥, 用于JWT签名>

# Hermes Agent API Key (后端与Agent间认证)
HERMES_AGENT_API_KEY=<生成随机API密钥>

# Agent蜂群 Webhook 签名密钥
SWARM_WEBHOOK_SECRET=<生成随机Webhook签名密钥>

# Swarm Executor 内部认证 Token
SWARM_EXECUTOR_TOKEN=<生成随机Token>
```

**.env 安全**: 添加到 `.gitignore`，不纳入版本控制。文件权限 `600`。

### 4.3 Hermes Agent 部署 (宿主机进程)

9个命名Agent角色采用独立 Profile 部署为宿主机进程:

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

**为何命名 Agent 为宿主机进程而非容器**:
- Hermes Agent 依赖完整系统环境: Python 运行环境、Hermes CLI、Profile 配置、Skills 目录、插件系统
- 每个 Agent Profile 包含独立的 skills/、plugins/、cron/、memories/ 目录结构
- Profile 配置 (config.yaml) 动态加载，容器化需挂载多个目录，增加复杂性
- 编程工具 (Claude Code/Codex 等) 也安装在宿主机，命名 Agent 需直接调用

**systemd 服务管理**:
每个命名 Agent 配置为 systemd 服务，实现自动启动、重启和日志管理:

```ini
# /etc/systemd/system/hermes-haimei.service
[Unit]
Description=Hermes Agent - HaiMei (Project Manager)
After=network.target

[Service]
Type=simple
User=jim
WorkingDirectory=/home/jim
ExecStart=/home/jim/.hermes/bin/hermes serve --profile haimei --port 8765
Restart=always
RestartSec=10
EnvironmentFile=/home/jim/.hermes/profiles/haimei/.env

[Install]
WantedBy=multi-user.target
```

**健康检查与自动重启**:
- `Restart=always`: 进程异常退出时自动重启
- `RestartSec=10`: 重启间隔 10 秒，防止快速重启循环
- Celery 定时任务每 30 秒检查 Agent Gateway 端口可达性
- 不可达时触发 alert 并通过 systemd restart 重启

**Agent 通信路径**:
- Agent 访问 Ollama: `http://localhost:11434` (Ollama 容器端口映射到宿主机)
- FastAPI 后端访问 Ollama: `http://ollama:11434` (Docker 内部网络)
- FastAPI 后端访问 Agent: `http://127.0.0.1:8765-8773` (Gateway API, 绑定 127.0.0.1)
- Agent Gateway 端口绑定 `127.0.0.1`，仅宿主机本地可达，外部网络无法访问

### 4.4 资源需求

**GPU 硬件规格 (必需)**:

| 规格 | 最低要求 | 推荐配置 | 说明 |
|------|---------|---------|------|
| GPU 型号 | NVIDIA RTX 4090 | NVIDIA A100 80GB | 必须支持 CUDA 12+ |
| 显存 (VRAM) | 24GB | 48GB+ | qwen2.5:72b Q4_K_M 约需 36-40GB 显存 |
| CUDA 版本 | 12.0+ | 12.2+ | Ollama 容器需要 |
| 驱动版本 | 535+ | 545+ | NVIDIA 官方驱动 |

**说明**: Qwen2.5-72B-Instruct Q4_K_M 量化模型在 GPU 上的显存需求约 36-40GB。RTX 4090 (24GB) 显存不足，需使用显存 ≥ 48GB 的 GPU (如 RTX 6000 Ada / A100 40GB 或以上)。如仅有 24GB 显存，需改用更小的模型 (如 qwen2.5:14b-instruct-q4_K_M，约需 8GB 显存)。

**WSL2 GPU 直通配置**:
- 宿主机安装 NVIDIA Driver + CUDA Toolkit
- 安装 `nvidia-container-toolkit`: `sudo nvidia-ctk runtime configure --runtime=docker`
- Docker 启动时通过 `deploy.resources.reservations.devices` 声明 GPU (已在 docker-compose 中配置)
- 确认 WSL2 中 `nvidia-smi` 可用且 GPU 显存可被容器识别
- 确认 Ollama 容器内 `ollama list` 可加载模型并执行推理

**基础设施组件资源**:

| 组件 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| FastAPI 后端 | 2核 | 4GB | 5GB |
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

**Ollama 模型推理资源 (GPU 显存)**:

| 组件 | GPU 显存 | 磁盘 |
|------|---------|------|
| qwen2.5:72b-instruct-q4_K_M (INT4量化) | ~36-40GB VRAM | ~40GB |
| **模型推理小计** | **~40GB VRAM** | **40GB** |

**说明**:
- Ollama 服务进程本身仅需 0.5GB 内存
- 加载 qwen2.5:72b-instruct-q4_K_M 模型需额外 ~36-40GB GPU 显存
- GPU 显存与系统内存分开核算: 系统内存 33GB + GPU 显存 40GB

**Hermes Agent 进程资源 (宿主机)**:

| 组件 | CPU (单个) | 内存 (单个) | 最多并发 | CPU (总计) | 内存 (总计) |
|------|-----------|-------------|---------|-----------|-------------|
| 命名 Agent 进程 | 0.5核 | 512MB | 9个 | 4.5核 | 4.5GB |
| **Agent 进程小计** | **4.5核** | **4.5GB** | - |

**Agent 蜂群运行时资源**:

| 组件 | CPU (单个) | 内存 (单个) | 最大并发 | CPU (总计) | 内存 (总计) |
|------|-----------|-------------|----------|-----------|-------------|
| 编程 Agent (Claude Code/Codex 等) | 2核 | 4GB | 4个 | 8核 | 16GB |
| 编程 Agent 资源上限 | 4核/个 | 8GB/个 | 4个 | 16核 (上限) | 32GB (上限) |
| **蜂群小计** | **8核** | **16GB** | - |

**总计 (峰值)**:

| 维度 | 总计 | 计算明细 |
|------|------|----------|
| CPU | 35核 | 20 (基础设施) + 2 (模型推理) + 4.5 (Agent 进程) + 8 (蜂群) = 34.5核, 取整 35核 |
| 系统内存 (RAM) | 54GB | 33 (基础设施) + 4.5 (Agent 进程) + 16 (蜂群) = 53.5GB, 取整 54GB |
| GPU 显存 (VRAM) | 40GB | Ollama 模型推理独占 |
| 磁盘 | 276GB | 236 (基础设施) + 40 (模型磁盘) = 276GB |

**生产部署建议配置**:
- CPU: 32 核
- 系统内存 (RAM): 64GB (基础) / 96GB (推荐)
- GPU: NVIDIA GPU, 显存 ≥ 48GB (如 RTX 6000 Ada / A100 40GB 或以上)
- 磁盘: 300GB+ SSD

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
│  │(devflow) │  │(AOF-only)│  └──────────────┘   │
│  └──────────┘  └──────────┘                      │
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
│  │  9个 Hermes Agent 进程 (systemd 管理)          │  │
│  │  端口: 8765-8773 (绑定 127.0.0.1)             │  │
│  │  访问 Ollama: http://localhost:11434           │  │
│  │  (Ollama 容器端口映射到宿主机)                  │  │
│  │  健康检查: Celery 定时任务 + systemd Restart   │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  编程 Agent 工具 (CLI 工具, 安装在宿主机)       │  │
│  │  Claude Code / Codex / Opencode / 等          │  │
│  │  Swarm Executor 通过子进程调用触发              │  │
│  │  资源限制: 单 Agent 4 核 CPU / 8GB 内存        │  │
│  │  生命周期: Swarm Executor 管理                  │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**跨网络通信说明**:
- Docker 内部网络 `devflow_net`: 所有容器通过该网络通信，使用容器名作为主机名
- Ollama 容器端口 11434 映射到宿主机
- 宿主机上的 Hermes Agent 通过 `http://localhost:11434` 访问 Ollama
- FastAPI 后端与 Hermes Agent 通过宿主机端口 8765-8773 通信 (Gateway API)
- Swarm Executor 容器通过 Docker 网络与 Celery/Redis 通信，通过子进程调用宿主机上的编程工具
- 仅端口 80/443 (Nginx)、11434 (Ollama) 映射到宿主机
- Gitea 不直接映射端口，统一通过 Nginx `location /gitea/` 代理访问
- 其余管理端口仅在 `devflow_net` 内可达

### 4.6 蜂群 Agent 执行环境

**Swarm Executor 角色定义**:
- **定位**: Swarm Executor 是编程 Agent 工具的执行调度器，不直接编写代码
- **与命名 Agent 的关系**:
  - 命名 Agent (后发/后达) 负责任务分析和任务拆分
  - 命名 Agent 通过 Celery 提交蜂群任务
  - Swarm Executor 接收任务，选择合适的编程工具并启动执行
  - Swarm Executor 监控执行进度，收集输出，通过 Webhook 上报结果
- **执行边界**:
  - Step 1-12: 由命名 Agent 直接执行 (通过 Gateway API)
  - Step 9 (功能代码编写): 后发拆分任务→Celery→Swarm Executor→编程工具
  - Step 11 (全面测试): 后达拆分任务→Celery→Swarm Executor→编程工具
  - Step 13-16: 由命名 Agent 直接执行

**部署架构**:

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
│  │  3. 通过子进程调用宿主机上的编程工具 CLI                │  │
│  │  4. 监控执行进度, 收集输出                             │  │
│  │  5. 通过 Webhook 上报结果给 FastAPI 后端               │  │
│  │  6. 任务完成后清理资源                                 │  │
│  │                                                      │  │
│  │  与宿主机交互方式:                                     │  │
│  │  - 挂载 /DevFlow/projects (读写项目文件)               │  │
│  │  - 挂载 /var/run/docker.sock (ro, 管理容器)           │  │
│  │  - 子进程调用宿主机上的编程工具 CLI                     │  │
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
│  - 资源限制: 单 Agent 4 核 CPU / 8GB 内存                    │
└─────────────────────────────────────────────────────────────┘
```

### 4.7 Ollama 并发推理说明

**并发场景**:
- 10 个并发项目 × 9 个命名 Agent = 最多 90 个命名 Agent 进程
- 所有 Agent 共享同一个 Ollama 容器实例和同一个模型

**Ollama 并发处理能力**:
- Ollama 内置请求队列机制，当并发请求超过处理能力时自动排队
- qwen2.5:72b-instruct-q4_K_M (INT4 量化) 在 GPU (48GB 显存) 下单请求推理延迟约 200-500ms
- 典型 QPS 估算:
  - GPU 模式 (48GB 显存): 约 5-10 QPS
  - CPU 模式 (不推荐): 约 1-2 QPS (极其缓慢)
- 采用单模型实例 + 队列模式，避免多副本重复占用显存

**推理队列机制**:
- Ollama 内部维护请求队列，按到达顺序处理
- 命名 Agent 侧配置请求超时为 60 秒
- 后端 Gateway Client 使用 `asyncio.Semaphore(5)` 限制对同一 Agent 的并发请求
- 高峰时段策略:
  - 非紧急任务 (文档生成、报告编写) 可延迟执行
  - 紧急任务 (QA 检验、流程调度) 优先调度
  - Celery 任务队列天然支持排队，不会丢失请求

**资源瓶颈与优化**:
- 90 个 Agent 并非同时活跃，实际并发推理请求通常 < 10 个
- 如瓶颈明显:
  - 为 Agent 分组分配云端模型 (OpenAI/Anthropic) 作为分流
  - 增大 GPU 显存 (如 A100 80GB) 提升单模型并发能力
  - 对轻量任务使用更小的本地模型 (如 qwen2.5:7b-instruct)

---

## 5. 容灾与高可用

### 5.1 可用性目标

**当前部署模式**: 单实例部署

**可用性声明**:
- 目标可用性: 99% (单实例目标, 每年约 87.6 小时停机)
- 实际限制: 单实例 PostgreSQL、Redis、Gitea、Ollama 存在单点故障风险
- 99% 可用性基于以下假设: 计划内维护 (每月约 8 小时)、硬件故障年均 1-2 次 (每次恢复约 2-4 小时)
- 当前架构不支持 99.9% 或更高 SLA

**高可用扩展方案 (可选, 按需实施)**:
- **PostgreSQL**: 流复制 + Patroni 自动故障转移 (主从架构, 2-3 节点)
- **Redis**: Redis Sentinel 集群 (3 节点), 自动选举主节点
- **Gitea**: 多实例 + 共享存储 (NFS/分布式文件系统), 前端 Nginx 负载均衡
- **Ollama**: 多副本 + 模型缓存共享存储, 前端 Nginx 负载均衡
- **FastAPI**: 多副本 + Nginx 负载均衡, 健康检查自动剔除故障节点
- **预期可用性**: 扩展后可达 99.5%~99.9%

### 5.2 备份策略

| 数据 | 频率 | 保留 | 存储位置 |
|------|------|------|----------|
| PostgreSQL (devflow) | 每日全量 + 每6h增量 | 30天/90天/365天 | /data/backups/ |
| PostgreSQL (gitea) | 每日全量 | 30天 | /data/backups/ |
| 文件存储 | 每日全量 | 30天 | /data/backups/ |
| Gitea | Git历史 + 每日归档 | 永久 | 内置 + /data/backups/ |
| Ollama 模型 | 首次部署拉取 | 永久 | ollama_data 卷 |
| Redis (AOF 文件) | AOF 实时追加 + 每日归档 | 最新3份 | redis_data 卷 |

### 5.3 恢复目标

- **RTO** (恢复时间目标): < 2 小时
- **RPO** (恢复点目标): < 1 小时

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
- `check_hermes_agents()`: 检查 9 个 Agent Gateway API 端口可达性
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
- `swarm-executor`: 健康检查 HTTP 端点 (30s 间隔)
- `prometheus`: `curl -sf http://localhost:9090/-/healthy` (30s 间隔)
- `jaeger`: `curl -sf http://localhost:14269` (30s 间隔)
- `filebeat`: `filebeat test output` (30s 间隔)

### 5.5 优雅关停与灾难恢复

**优雅关停流程**:

```
1. 收到关停信号 (SIGTERM)
2. FastAPI 后端:
   a. 停止接收新请求 (Nginx 返回 503)
   b. 等待正在处理的请求完成 (最长 30 秒)
   c. 关闭 WebSocket 连接 (发送 close frame)
   d.  flush Redis 缓存
   e. 关闭数据库连接池
3. Celery Worker:
   a. 完成当前正在执行的任务
   b. 不再领取新任务
   c. 保存未完成任务的 checkpoint 到数据库
   d. 优雅退出
4. Celery Beat:
   a. 停止调度新定时任务
   b. 等待当前任务完成
   c. 优雅退出
5. Swarm Executor:
   a. 停止接收新蜂群任务
   b. 等待正在运行的编程工具完成 (最长 5 分钟)
   c. 超时未完成的编程工具发送 SIGTERM
   d. 保存任务状态到数据库
   e. 优雅退出
6. WebSocket Worker:
   a. 向所有连接发送关闭通知
   b. 等待连接关闭 (最长 10 秒)
   c. 优雅退出
7. 命名 Agent (systemd):
   a. 收到 SIGTERM
   b. 完成当前对话轮次
   c. 保存对话状态到 Profile 存储
   d. 优雅退出
8. 依赖组件 (PostgreSQL/Redis/Gitea/Ollama):
   a. 按顺序关停: Ollama → Gitea → Redis → PostgreSQL
   b. 确保数据已持久化
```

**16 步工作流中断处理**:
- 工作流状态持久化: 每一步执行前保存 checkpoint 到 `workflow_checkpoints` 表
- Checkpoint 粒度:
  - 步骤级别: Step 开始/结束时保存
  - 阶段级别: 步骤内关键操作前保存 (如代码编写开始、测试执行开始、QA 检验开始)
- 中断后恢复:
  1. 系统重启后, WorkflowEngine 扫描 `RUNNING` 状态的任务
  2. 加载最近 checkpoint 状态
  3. 从 checkpoint 处继续执行，而非从头开始
  4. 如果 checkpoint 数据不完整, 标记为 NEED_REVIEW, 通知海梅介入

**PostgreSQL 故障恢复**:
- PostgreSQL 故障时, 所有依赖数据库的操作立即暂停
- Celery 任务进入重试队列 (自动重试 3 次, 间隔指数退避)
- PostgreSQL 恢复后, 暂停的任务自动从 checkpoint 恢复
- RPO: < 1 小时 (基于 WAL 日志恢复)

**Redis 故障恢复**:
- Redis 故障时, Celery 任务队列暂停
- WebSocket 连接断开，前端自动重连
- Redis 恢复后:
  - Celery 从 AOF 恢复未持久化的任务
  - WebSocket Worker 重新订阅 Channel
  - 缓存数据从数据库重新加载

**崩溃后恢复流程**:
1. 系统监控检测到故障组件
2. 触发告警通知 (WebSocket + 邮件)
3. systemd/Docker 自动重启故障进程
4. WorkflowEngine 扫描中断的工作流
5. 从 checkpoint 恢复每个中断的工作流
6. 海梅介入处理无法自动恢复的工作流

---

## 6. 安全架构

### 6.1 认证与授权

**人类用户认证**:
- **认证**: JWT Token (Access Token 30 分钟 + Refresh Token 7 天)
- **授权**: RBAC (基于角色的访问控制)
- **项目隔离**: 用户仅可访问自身创建的项目

**RBAC 角色定义**:

| 角色 | 权限 | 说明 |
|------|------|------|
| admin (管理员) | 全部权限 | 系统管理、用户管理、项目创建、Agent 配置、部署管理 |
| developer (项目成员) | 项目读写、群聊、进度查看 | 可参与项目开发、查看进度、群聊讨论 |
| viewer (只读) | 项目只读、群聊只读 | 仅查看项目进度和群聊历史, 不可修改 |

**6.1.1 命名 Agent 认证**:
- 9 个命名 Agent 通过 API Key 向后端认证
- API Key 存储在 `.env` 的 `HERMES_AGENT_API_KEY` 变量中
- 后端通过自定义中间件验证请求头 `X-Hermes-API-Key`
- 每个 Agent Profile 配置中注入 API Key，通过 Gateway 请求头传递
- 认证流程:
  1. FastAPI 后端发起请求到 Agent Gateway (如 `http://127.0.0.1:8765/chat`)
  2. 请求头携带 `X-Hermes-API-Key: <key>`
  3. Agent Gateway 验证 API Key 是否匹配 Profile 配置中的密钥
  4. 验证通过则处理请求，否则返回 401
- 反向认证 (Agent 回调后端):
  1. Agent 完成后回调 FastAPI 后端上报结果
  2. 请求头携带 `X-Hermes-API-Key` + `X-Agent-Profile: haimei`
  3. 后端验证 API Key 和 Profile 名称的映射关系
  4. 验证通过后处理回调数据

**6.1.2 Swarm Executor 认证**:
- Swarm Executor 与 FastAPI 后端通信使用内部 Token
- Token 存储在 `.env` 的 `SWARM_EXECUTOR_TOKEN` 变量中
- Swarm Executor 上报结果时携带请求头 `X-Swarm-Token: <token>`
- 后端验证 Token 有效性
- Swarm Executor 仅在 Docker 内部网络 `devflow_net` 中运行，不暴露到外部网络

**6.1.3 编程工具认证**:
- 编程工具由 Swarm Executor 通过子进程调用启动，无需网络认证
- 进程级隔离: Swarm Executor 验证任务合法性后再启动子进程
- 文件级隔离: 编程工具仅可访问分配的工作目录
- 资源级限制: CPU/内存上限防止资源耗尽
- 编程工具完成后，Swarm Executor 通过 Webhook 回调 FastAPI 后端，携带 `X-Webhook-Signature` (HMAC-SHA256)

**6.1.4 Gitea Webhook 验证**:
- Gitea 代码推送事件通过 Webhook 通知 FastAPI 后端
- Webhook 配置时生成随机 Secret Token
- Gitea 发送请求时携带 `X-Gitea-Token` 头
- 后端验证 Token 匹配，否则丢弃请求
- Webhook 事件类型: `push` (代码推送)、`pull_request` (PR 创建/更新)

**内部 Docker 网络策略**:
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
- Agent 通信数据脱敏存储
- 内部 Docker 网络通信不加密 (同一宿主机内，信任边界内)

### 6.3 敏感信息管理

- 所有密码、密钥存储在 `.env` 文件中, 不纳入版本控制
- `.env` 文件权限设置为 `600` (仅属主可读)
- 容器内通过 `env_file` 注入环境变量, 不暴露为 Docker 明文
- 数据库密码、Redis 密码、JWT 密钥、API Key、Webhook Secret、Swarm Token 均通过 `.env` 管理

### 6.4 审计日志

所有关键操作记录日志:
- Agent 任务分派
- QA 检验结果
- 代码提交
- 错误和异常
- 用户登录/登出
- Agent 认证失败事件
- 蜂群 Webhook 签名验证失败事件
- Gitea Webhook 验证失败事件

---

## 7. 性能设计

### 7.1 性能指标目标

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 页面加载 | < 2秒 | Lighthouse 3次平均 |
| API 响应 | < 3秒 (P95) | curl 10次请求 |
| 蜂群任务分发 | < 500ms | 接口计时 |
| QA 检验处理 | < 1分钟/产出 | 计时统计 |
| 数据库查询 | < 100ms | pg_stat_statements |
| 群聊消息延迟 | < 100ms | WebSocket 端到端 |

### 7.2 并发处理

- **并发项目数**: 10 个
- **容量规划依据**:
  - 服务器总资源: 35 核 CPU、54GB 系统内存 + 40GB GPU 显存 (峰值)
  - 基础设施持续占用: 20 核 CPU、33GB 内存
  - Ollama 模型推理占用: 40GB GPU 显存
  - 可用资源: 约 13 核 CPU、21GB 内存 (扣除基础设施后)
  - 单个项目平均占用: CPU 0.8 核、内存 2GB
  - 按 80% 资源利用率上限: CPU 可支撑约 16 个项目, 内存可支撑约 10 个项目
  - 取内存为瓶颈: 保守估计 10 个并发项目
- **Agent 并发限制**: 同 Profile 同一时间仅执行 1 个任务
- **WebSocket 并发**: 单群组支持 10+ Agent 在线，由专用 WebSocket Worker 处理
- **API 并发**: 信号量限制 5 个/Agent
- **Ollama 并发**: 单模型实例 + 内部请求队列, 约 5-10 QPS (GPU 模式)

### 7.3 缓存策略

| 缓存内容 | TTL | 存储 |
|----------|-----|------|
| 用户 Session | 30分钟 | Redis |
| 项目进度 | 5分钟 | Redis |
| Agent 状态 | 1分钟 | Redis |
| 群聊消息 | 24小时 | Redis + PostgreSQL |
| 静态资源 | 1年 | Nginx + 浏览器 |

---

## 8. 监控与可观测性

### 8.1 指标采集 (Prometheus)

- **系统级**: CPU/内存/磁盘/网络 (30 秒间隔)
- **应用级**: API 响应时间/QPS/错误率 (10 秒间隔)
- **Agent 级**: 任务时长/成功率/负载 (30 秒间隔)
- **业务级**: 项目数/QA 通过率/步骤耗时 (实时)

### 8.2 链路追踪 (Jaeger)

**Trace Context 传播机制**:

```
人类用户请求
    │
    ▼
Nginx (注入 X-Trace-ID 头)
    │
    ▼
FastAPI 后端 (接收/生成 Trace ID)
    │
    ├──→ Celery Worker (通过 task context 传递 trace_id)
    │       │
    │       ├──→ Gateway Client 调用命名 Agent
    │       │       │
    │       │       ▼
    │       │  命名 Agent (通过 HTTP 头 X-Trace-ID 传递)
    │       │       │
    │       │       ▼
    │       │  Ollama 推理 (记录为 span)
    │       │
    │       └──→ Swarm Executor (通过 task context 传递 trace_id)
    │               │
    │               ▼
    │          编程工具 (记录为 span, 通过日志附带 trace_id)
    │
    └──→ WebSocket Worker (通过 Redis Pub/Sub 消息传递 trace_id)
```

**传播方式**:
- **FastAPI → Celery**: Celery task 的 `context` 中携带 `trace_id`，通过 `current_task.request.headers` 传递
- **Celery → Gateway Client**: Gateway Client 调用 Agent 时在 HTTP 请求头中注入 `X-Trace-ID`
- **Celery → Swarm Executor**: Swarm Executor 接收任务时携带 `trace_id`，子进程调用编程工具时在环境变量中传递 `TRACE_ID`
- **编程工具 → Jaeger**: 编程工具日志中附带 `trace_id`，Swarm Executor 完成后上报 span 到 Jaeger
- **WebSocket → Jaeger**: WebSocket 消息中携带 `trace_id`，WebSocket Worker 上报 span

**Jaeger 配置**:
- 每个 Agent 任务分配唯一 Trace ID (UUID)
- 追踪全链路: 分派 → 执行 → 检验 → 提交
- 保留 7 天
- Span 命名规范: `{service}.{operation}` (如 `backend.workflow.execute_step`)

### 8.3 日志管理 (ELK Stack)

- **组件部署**: Elasticsearch + Logstash (由 Filebeat 替代) + Kibana
- **采集方式**: Filebeat 采集各容器日志, 推送至 Elasticsearch
- **日志格式**: JSON 结构化日志
- **保留策略**: 本地保留 30 天 + ELK 保留 90 天
- **关键操作**: 所有关键操作必记日志, Kibana 配置实时告警查询

### 8.4 告警规则

| 告警类型 | 条件 | 通知方式 |
|----------|------|----------|
| CPU 告警 | >85% 持续 5 分钟 | WebSocket + 邮件 |
| 内存告警 | >90% 持续 3 分钟 | WebSocket + 邮件 |
| API 错误率 | >5% | WebSocket + 邮件 |
| Agent 宕机 | 进程停止 | WebSocket + 邮件 |
| 任务超时 | >30 分钟 | WebSocket + 邮件 |
| Ollama 服务不可用 | /api/tags 无响应 | WebSocket + 邮件 |

---

## 9. API 契约与数据流

### 9.1 核心 API 端点

**认证**:
- `POST /api/v1/auth/login` — 用户登录, 返回 JWT Token
- `POST /api/v1/auth/refresh` — 刷新 Access Token

**项目管理**:
- `POST /api/v1/projects` — 创建项目 (Step 1, 人类用户执行)
- `GET /api/v1/projects` — 项目列表
- `GET /api/v1/projects/{id}` — 项目详情
- `GET /api/v1/projects/{id}/workflow` — 16 步流程状态

**Agent 管理**:
- `GET /api/v1/agents` — Agent 列表和状态
- `GET /api/v1/agents/{profile}/status` — 单个 Agent 状态
- `POST /api/v1/agents/{profile}/chat` — 与 Agent 对话

**蜂群管理**:
- `POST /api/v1/swarms` — 创建蜂群
- `GET /api/v1/swarms/{id}` — 蜂群状态
- `GET /api/v1/swarms/{id}/tasks` — 蜂群任务列表

**QA 门控**:
- `POST /api/v1/qa/inspect` — 触发 QA 检验
- `GET /api/v1/qa/results/{id}` — QA 检验结果

**群聊协作**:
- `GET /ws/group/{id}` — WebSocket 群聊连接

### 9.2 16 步完整数据流映射

**Step 1-12 (命名 Agent 执行阶段)**:

| 步骤 | 执行者 | 执行方式 | 产出 | QA 检验 | 代码提交 |
|------|--------|----------|------|---------|----------|
| Step 1: 项目创建 | 人类用户 | 前端界面 | 项目基本信息 | 无需 QA | 创建 Gitea 仓库 |
| Step 2: 海梅确认 | 海梅 | Gateway API | 项目确认报告 | 无需 QA | 提交项目文档 |
| Step 3: 需求分析 | 后兴 | Gateway API | 需求规格说明书 | 后荣检验 | 检验通过后提交 |
| Step 4: 架构设计 | 后旺 | Gateway API | 架构设计文档 | 后荣检验 | 检验通过后提交 |
| Step 5: 环境搭建 | 后富 | Gateway API | 环境配置文档 | 后荣检验 | 检验通过后提交 |
| Step 6: TDD 计划 | 后达 | Gateway API | TDD 计划文档 | 后荣检验 | 检验通过后提交 |
| Step 7: TDD 用例 | 后发 | Gateway API + 编程工具 | 测试用例代码 | 后荣检验 | 检验通过后提交 |
| Step 8: 代码计划 | 后发 | Gateway API | 代码编写计划 | 后荣检验 | 检验通过后提交 |
| Step 9: 功能代码 | 后发 | Gateway API + Swarm Executor + 编程工具 | 功能代码 | 后荣检验 | 检验通过后提交 |
| Step 10: 测试部署 | 后富 | Gateway API | 测试环境部署 | 后荣检验 | 检验通过后提交 |
| Step 11: 全面测试 | 后达 | Gateway API + Swarm Executor + 编程工具 | 测试报告 | 后荣检验 | 检验通过后提交 |
| Step 12: 安全审计 | 后华 | Gateway API | 安全审计报告 | 后荣检验 | 检验通过后提交 |

**Step 13-16 (部署与交付阶段)**:

| 步骤 | 执行者 | 执行方式 | 产出 | QA 检验 | 代码提交 |
|------|--------|----------|------|---------|----------|
| Step 13: 生产部署 | 后富 | Gateway API | 生产环境部署报告 | 后荣检验 | 检验通过后提交 |
| Step 14: 文档完善 | 后贵 | Gateway API | 完整项目文档 | 后荣检验 | 检验通过后提交 |
| Step 15: 交付报告 | 海梅 | Gateway API | 项目交付报告 | 后荣检验 | 检验通过后提交 |
| Step 16: 满意度确认 | 人类用户 | 前端界面 | 满意度反馈 | 无需 QA | 满意则归档, 不满意则回到 Step 3 |

**数据流闭环**:
```
人类用户 → Nginx → FastAPI 后端
    → Celery Worker → 命名 Agent (Gateway API)
    → 命名 Agent 执行任务
    → 后荣 QA 检验 (Gateway API)
    → 检验通过 → Git 提交 → Gitea
    → 检验不通过 → 退回重做 (RetryManager)
    → 通知用户 (WebSocket + 邮件)

Step 7/9/11 (涉及编程工具):
    → Celery Worker → Swarm Executor
    → Swarm Executor 选择编程工具
    → 子进程调用宿主机上的编程工具
    → 编程工具执行 → 产出代码
    → Swarm Executor 收集结果 → Webhook 回调 FastAPI
    → 后荣 QA 检验
```

---

## 10. 生命周期与通知机制

### 10.1 编程工具生命周期管理

**编程工具列表**:
- Claude Code (Claude CLI)
- Codex (OpenAI Codex CLI)
- Opencode (OpenCode CLI)
- Cursor (Cursor CLI, 如可用)
- CodeArts (华为 CodeArts)
- Trae (Trae CLI)
- Lingma (通义灵码)
- Hermes 子 Agent
- pi-codeing-agent 子 Agent

**生命周期状态机**:
```
IDLE → INITIALIZING → RUNNING → COMPLETING → CLEANING → IDLE
                 │                                │
                 ▼                                ▼
            FAILED ←────────────────── TIMEOUT
```

**状态说明**:
- **IDLE**: 工具就绪，等待任务分配
- **INITIALIZING**: Swarm Executor 正在启动子进程，准备执行环境
- **RUNNING**: 工具正在执行任务
- **COMPLETING**: 任务完成，正在收集输出
- **CLEANING**: 清理临时文件和资源
- **FAILED**: 执行失败，记录错误并回滚
- **TIMEOUT**: 执行超时 (默认 30 分钟)，发送 SIGTERM 终止

**管理策略**:
- **进程隔离**: 每个编程工具在独立子进程中运行，通过 `subprocess.Popen` 启动
- **工作目录隔离**: 每个工具分配独立目录 `/DevFlow/projects/{project_id}/swarm/{tool_id}/`
- **资源限制**: CPU 4 核 / 内存 8GB (通过 cgroup 或 `--cpus`/`--memory` 参数)
- **超时控制**: 默认 30 分钟超时，超时后发送 SIGTERM，5 秒后 SIGKILL
- **文件锁**: 共享资源使用 `fcntl.flock()` 防止并发冲突
- **最大并发**: 同一项目最多 4 个编程工具同时运行
- **空闲清理**: 工具空闲超过 10 分钟自动释放资源
- **日志采集**: 工具 stdout/stderr 重定向到日志文件，Filebeat 采集至 ELK

**冲突解决**:
- 代码文件冲突: Swarm Executor 检测到文件锁冲突时，将任务排入队列等待
- 合并冲突: 由后发/后达命名 Agent 进行代码审查和合并
- 资源竞争: cgroup 限制防止单个工具耗尽资源

### 10.2 通知机制

**通知渠道**:

| 渠道 | 用途 | 实现方式 |
|------|------|----------|
| WebSocket 实时推送 | 群聊消息、进度更新、即时告警 | WebSocket 连接 + Redis Pub/Sub |
| 邮件通知 | 重要事件通知、日报/周报 | SMTP + 邮件模板 |
| 站内通知 | 系统消息、任务分派通知 | 数据库存储 + WebSocket 推送 |

**WebSocket 推送流程**:
1. FastAPI 后端产生通知事件
2. 写入 PostgreSQL `notifications` 表
3. 发布到 Redis `global:notifications` Channel
4. WebSocket Worker 订阅 Channel 收到消息
5. 推送给所有在线的 WebSocket 客户端

**邮件通知触发条件**:
- 项目创建成功
- QA 检验不通过 (需重做)
- 任务超时
- Agent 宕机
- 生产部署完成
- 每日项目进展汇总

**通知事件类型**:
- `project.created` — 项目创建
- `workflow.step.completed` — 步骤完成
- `workflow.step.failed` — 步骤失败
- `qa.inspection.failed` — QA 检验不通过
- `swarm.task.started` — 蜂群任务开始
- `swarm.task.completed` — 蜂群任务完成
- `agent.crashed` — Agent 进程崩溃
- `deployment.completed` — 部署完成

---

## 11. 补充设计

### 11.1 分布式追踪上下文传播

(详见 8.2 节 Jaeger 链路追踪)

### 11.2 工作流状态持久化

**workflow_checkpoints 表结构**:
```sql
CREATE TABLE workflow_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    step_number INTEGER NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    state_json JSONB NOT NULL,
    trace_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_wf_checkpoint_project_step ON workflow_checkpoints(project_id, step_number);
```

**Checkpoint 保存时机**:
- Step 开始时: 保存初始状态
- Step 内关键阶段前: 保存中间状态 (如代码编写开始、测试执行开始)
- Step 完成时: 保存最终状态
- 任务提交 Celery 时: 保存任务提交状态

**崩溃恢复流程**:
1. 系统重启, WorkflowEngine 初始化
2. 扫描 `workflow_steps` 表中状态为 `RUNNING` 的记录
3. 按 `workflow_checkpoints` 表加载最近的 checkpoint
4. 判断 checkpoint 完整性:
   - 完整: 从 checkpoint 处继续执行
   - 不完整: 标记为 `NEED_REVIEW`, 通知海梅
5. 恢复执行后更新步骤状态

### 11.3 优雅关停 (详见 5.5 节)

系统优雅关停流程已在 5.5 节详细描述，包括各组件的关停顺序和工作流中断处理。

---

文档结束
