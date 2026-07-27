# DevFlow 架构设计文档 V10.0

**项目**: DevFlow 项目管理平台
**版本**: 10.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: V9.0 修订 (根据后荣 QA 检验报告修订)

**变更日志**:
- V10.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 【严重问题1】文档完整性: 确认 V9.0 实际完整 (2158 行)，V10.0 保持完整并补充缺失设计
  - 【严重问题2】命名 Agent 部署模型不一致: 将 "分布式组件均为独立容器" 修正为 "混合部署模式"，明确 Docker 容器 + 宿主机进程共存，统一运维管理方案
  - 【严重问题3】Swarm Executor 宿主机访问权限: 补充 nsenter + bind mount 方案，明确容器访问宿主机文件系统和 CLI 工具的具体机制
  - 【中等问题1】GPU 资源分配: 补充 Ollama 并发推理队列机制、峰值显存风险评估、模型卸载/重载策略
  - 【中等问题2】内存预算分配表: 新增详细的内存预算分配表，逐项计算 96GB 生产配置的来源
  - 【中等问题3】单点故障可用性: 修正可用性目标为 95-97% (单实例实际水平)，99% 标注为 HA 扩展后的目标
  - 【中等问题4】数据一致性保障: 新增 12 节数据一致性保障设计，补充各步骤失败处理和补偿机制

- V9.0 (2026-06-13): 根据后荣 QA 检验报告修订 (GPU 硬件规格、Redis Stream、docker-socket-proxy、Celery 健康检查、内存规格、cgroup 限制、API 速率限制、优雅关停脚本、API 分页、Jaeger 保留期、数据库连接池、Ollama 预热、Git 分支命名)
- V8.0 (2026-06-13): 根据后荣 QA 检验报告修订 (文档完整性、可用性声明、GPU 规格补全、命名 Agent 部署模型、架构术语统一、服务间认证、优雅关停、Celery 并发度、Redis 持久化、Swarm Executor 角色、16 步映射、Jaeger 追踪、内存规格、编程工具生命周期、通知机制)
- V7.0 (2026-06-13): 根据后荣 QA 检验报告修订 (docker-compose 端口安全、Ollama entrypoint、Redis 持久化、Celery 并发度等)
- V6.0 (2026-06-13): 根据后荣 QA 检验报告修订 (架构描述修正、Ollama 部署、Gitea 数据库隔离等)

---

## 1. 系统架构概述

### 1.1 架构目标

DevFlow 采用 **单体后端 + 分布式组件 + 混合部署** 架构，核心设计理念：

- **单体后端**: FastAPI 为单一进程应用，各业务模块通过 Python 包结构划分，非独立部署的微服务。Celery Worker、WebSocket Worker 为后端的辅助进程，共享代码库和数据模型
- **分布式组件**: 数据库 (PostgreSQL)、缓存 (Redis)、代码托管 (Gitea)、推理引擎 (Ollama)、监控 (Prometheus/Jaeger/ELK) 为独立 Docker 容器；9 个命名 Agent 进程、编程工具 (Claude Code/Codex 等) 为宿主机进程
- **混合部署模式**: 系统同时使用 Docker 容器 (后端、数据库、中间件、监控) 和宿主机进程 (命名 Agent、编程工具) 两种部署方式。Docker 容器通过 `docker compose` 统一管理，宿主机进程通过 `systemd` 统一管理。日志收集、健康监控、优雅关停分别通过 Filebeat/systemd-journald 和 shutdown.sh 脚本实现统一自动化
- **实际进程数**: 完整部署包含 20+ 个进程 (FastAPI、Celery Worker、Celery Beat、WebSocket Worker、Swarm Executor、9 个命名 Agent、Nginx、PostgreSQL×2、Redis、Gitea、Ollama、Prometheus、Jaeger、Elasticsearch、Kibana、Filebeat)
- **可用性**: 当前为单实例部署，实际可用性目标 95-97% (每年约 365-876 小时停机)。高可用扩展后可达 99% 以上，详见 5.1 节
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
│         Docker 容器 (docker compose 管理) + 宿主机进程 (systemd 管理)    │
│               [混合部署模式]                                            │
│                                                                        │
│  ┌─ Docker 容器 (docker compose) ───────────────────────────────────┐  │
│  │  Nginx, backend, ws-worker, celery-worker, celery-beat,          │  │
│  │  swarm-executor, postgres(x2), redis, gitea, ollama,             │  │
│  │  prometheus, jaeger, elasticsearch, kibana, filebeat,            │  │
│  │  docker-socket-proxy                                             │  │
│  │  管理: docker compose up/down, healthcheck, 日志: Filebeat→ELK   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─ 宿主机进程 (systemd) ───────────────────────────────────────────┐  │
│  │  9个命名Agent: 海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华         │  │
│  │  端口: 8765-8773 (绑定 127.0.0.1)                                 │  │
│  │  编程工具: Claude Code/Codex/Opencode 等 (Swarm Executor 触发)    │  │
│  │  管理: systemd service, 自动重启, 日志: journald→Filebeat→ELK     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              Swarm Executor (容器: swarm-executor)                     │
│  职责: 接收 Celery 任务, 选择并触发编程工具, 监控执行, 上报结果         │
│  与命名 Agent 关系: 命名 Agent (后发/后达) 提交任务→Celery→Swarm Executor│
│  宿主机访问方式:                                                        │
│  - 项目文件: bind mount (/DevFlow/projects)                            │
│  - CLI 工具: nsenter 进入宿主机 PID 命名空间执行                        │
│  - Docker API: docker-socket-proxy (受限子集)                          │
└────────────────────────────────────────────────────────────────────────┘
              │ 触发 (nsenter → 宿主机 PID 命名空间 → 子进程)
┌─────────────▼─────────────────────────────────────────────────────────┐
│              编程Agent工具 (宿主机 CLI 工具)                            │
│  Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma  │
│  hermes子agent / pi-codeing-agent子agent                               │
│  生命周期: Swarm Executor 管理启动/运行/停止/清理                       │
│  资源限制: 单 Agent 4 核 CPU / 8GB 内存 (systemd slice 预配置)          │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              数据持久层 (容器)                                          │
│  PostgreSQL (devflow) + PostgreSQL (gitea)                             │
│  Redis (AOF持久化 + Stream可靠队列) + 文件存储 + Gitea (代码仓库)       │
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
- "混合部署模式" 指 Docker 容器 (后端、数据库、中间件、监控) 与宿主机进程 (命名 Agent、编程工具) 共存。Docker 容器由 `docker compose` 编排，宿主机进程由 `systemd` 管理。两种部署方式各有其运维自动化方案 (详见 4.1 和 4.3 节)
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
- slowapi (API 速率限制中间件)

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

**API 速率限制 (slowapi)**:
- 采用 `slowapi` 中间件，基于 Redis 的令牌桶算法
- 按端点类型配置不同限额:
  - 认证端点 (`/api/v1/auth/*`): 5 次/分钟 (防暴力破解)
  - 项目管理端点 (`/api/v1/projects/*`): 60 次/分钟
  - Agent 对话端点 (`/api/v1/agents/*/chat`): 30 次/分钟 (避免 Ollama 过载)
  - 群聊 WebSocket: 不受限制 (长连接)
  - Webhook 回调端点: 120 次/分钟
- 超限返回 `429 Too Many Requests`，响应头包含 `Retry-After`

**API 分页/过滤/排序机制**:
- 列表端点统一支持分页参数: `?page=1&page_size=20` (默认 20 条/页，最大 100)
- 过滤参数: `?status=RUNNING&created_after=2026-06-01` (按端点定义可选过滤字段)
- 排序参数: `?sort_by=created_at&sort_order=desc` (支持 `asc`/`desc`)
- 响应格式: `{"data": [...], "total": 150, "page": 1, "page_size": 20, "total_pages": 8}`

### 2.4 集成层 (Integration Layer)

**职责**: 外部系统集成通信

**集成的外部系统**:

| 系统 | 通信方式 | 用途 | 部署位置 |
|------|----------|------|----------|
| Hermes Agent (9个命名角色) | HTTP REST + WebSocket (Gateway API) | Agent对话、任务执行 | 宿主机进程 (systemd管理) |
| Ollama | HTTP REST (容器内: `ollama:11434`) | 本地模型推理服务 | Docker 容器 (GPU) |
| Gitea | REST API (容器内: `gitea:3000`) | 代码仓库管理、Git操作 | Docker 容器 |
| 编程Agent工具 (蜂群) | Swarm Executor→nsenter→子进程调用 | 任务分发、进度上报、成果交付 | 宿主机 CLI 工具 |
| Prometheus | HTTP Push | 指标上报 | Docker 容器 |
| Jaeger | gRPC | 链路追踪上报 | Docker 容器 |

### 2.5 数据层 (Data Layer)

**职责**: 数据持久化、缓存、会话管理

| 组件 | 用途 | 配置 |
|------|------|------|
| PostgreSQL (devflow) | DevFlow主数据库，存储项目、用户、任务、QA记录等 | 连接池见 2.5.1 节 |
| PostgreSQL (gitea) | Gitea独立数据库，存储Gitea元数据 | 独立用户 gitea_admin |
| Redis 6+ | 缓存、Celery Broker、WebSocket会话、Stream可靠队列 | 内存: 2GB, 持久化: AOF (everysec fsync) |
| 文件存储 | 项目文件夹、文档、报告 | /DevFlow/projects/ |

**2.5.1 数据库连接池细化配置**:

| 组件 | 连接池大小 (pool_size) | 最大溢出 (max_overflow) | 说明 |
|------|----------------------|----------------------|------|
| FastAPI backend | 10 | 10 | HTTP 请求同步数据库操作，workers=2，每 worker 分配 5 连接 |
| Celery Worker | 5 | 5 | 异步任务数据库操作，concurrency=8，复用连接池 |
| Swarm Executor | 3 | 3 | 蜂群任务状态上报，轻量级数据库访问 |
| WebSocket Worker | 2 | 2 | 群聊消息读写，低频数据库操作 |

连接池配置示例 (SQLAlchemy):
```python
# backend 连接池
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=10, pool_pre_ping=True)

# celery worker 连接池 (独立引擎)
celery_engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=5, pool_pre_ping=True)

# swarm executor 连接池
swarm_engine = create_engine(DATABASE_URL, pool_size=3, max_overflow=3, pool_pre_ping=True)
```

`pool_pre_ping=True` 确保连接在每次使用前进行健康检查，避免僵死连接。

**数据库隔离说明**: DevFlow 和 Gitea 使用独立的 PostgreSQL 容器和独立用户，避免权限交叉和数据污染。

**Redis 持久化策略**:
- AOF-only 模式: `--appendonly yes --appendfsync everysec`
- 放弃 RDB 快照，避免双持久化的 I/O 开销
- 定期全量备份由 cron 任务执行 `redis-cli BGSAVE` + 文件归档
- AOF 重写: `--auto-aof-rewrite-percentage 100 --auto-aof-rewrite-min-size 64mb`

**Redis Stream 可靠队列 (关键通知)**:
- 普通 WebSocket 消息 (群聊) 仍使用 Pub/Sub (低延迟、可接受丢失)
- 关键通知 (告警、任务完成、QA 结果) 改用 Redis Stream:
  - Stream 命名: `critical:notifications`
  - 消费者组: `ws-workers`
  - 消息持久化至 Stream，WebSocket Worker 消费后 ACK 确认
  - Worker 宕机期间消息保留在 Stream 中，恢复后从 last-delivered ID 继续消费
  - Stream 保留策略: `MAXLEN ~10000` (近似长度，自动淘汰旧消息)
- 写入端: FastAPI 后端 `XADD critical:notifications * type ... data ...`
- 读取端: WebSocket Worker `XREADGROUP G ws-workers ws-1 0 critical:notifications COUNT 100 BLOCK 5000`

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
        4. Swarm Executor 通过 nsenter 进入宿主机 PID 命名空间启动编程工具
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
- **资源限制**: 单编程 Agent 4 核 CPU / 8GB 内存 (通过 systemd slice 预配置)
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

**进程间通信机制**:

```
┌──────────────────┐         Redis Pub/Sub + Stream       ┌──────────────────────┐
│  backend (主后端) │ ◄──────────────────────────────►  │ ws-worker (WebSocket)│
│  (workers=2)      │                                      │  (单Worker,ws专用)   │
└──────────────────┘                                      └──────────────────────┘
         │                                              │
         │  普通消息 (群聊聊天): Redis Pub/Sub (低延迟)    │
         │  关键通知 (告警/QA/任务): Redis Stream (可靠)   │
         │                                              │
         │  正向流程: 人类用户→Nginx→backend 处理        │
         │  1. backend 处理消息逻辑                     │
         │  2. 普通消息: 发布到 Redis Pub/Sub Channel   │
         │  3. 关键通知: 写入 Redis Stream              │
         │  4. ws-worker 消费 Channel/Stream 消息       │
         │  5. ws-worker 推送给在线 WebSocket 客户端     │
         │                                              │
         │  可靠性保证:                                 │
         │  - Pub/Sub: fire-and-forget, 可接受短暂丢失   │
         │  - Stream: 消费者组 ACK 确认, 宕机可重放      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Redis Pub/Sub 设计 (普通消息)**:
- Channel 命名: `group:{group_id}:messages` (按群组分频道)
- Channel 命名: `global:notifications` (全局非关键通知)
- 消息格式: JSON (sender_id, sender_type, content, timestamp, group_id)
- backend 和 ws-worker 启动时订阅所有活跃群组的 Channel
- 消息写入 PostgreSQL 由 backend 负责，ws-worker 仅负责实时推送

**Redis Stream 设计 (关键通知)**:
- Stream 命名: `critical:notifications`
- 消费者组: `ws-workers` (支持多 Worker 消费扩展)
- 消费者: `ws-1` (当前单实例)
- 写入: `XADD critical:notifications * type event_type data '{json}' priority high`
- 消费: `XREADGROUP G ws-workers ws-1 0 critical:notifications COUNT 100 BLOCK 5000`
- ACK: 消费成功后 `XACK critical:notifications ws-workers {message_id}`
- 未 ACK 消息在 Worker 恢复后自动重送
- 保留策略: `MAXLEN ~10000`

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
      test: ["CMD", "curl", "-sf", "http://localhost:8002/celery-health"]
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
      - DOCKER_PROXY_URL=http://docker-socket-proxy:2375
      - HOST_PID_NS=/proc/1/ns/pid_for_children
    volumes:
      - ../../projects:/DevFlow/projects
      - ./swarm-config:/etc/swarm
      - /proc/1/ns/pid_for_children:/host/pid_ns:ro
    # 通过 nsenter 进入宿主机 PID 命名空间执行编程工具
    # 不再直接挂载 docker.sock，改为通过 socket 代理通信
    depends_on:
      - redis
      - backend
      - docker-socket-proxy
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:9100/health\")'"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net

  docker-socket-proxy:
    image: abhgh/go-docker-socket-proxy:latest
    ports: []
    environment:
      # 仅允许 Swarm Executor 使用的 Docker API 子集
      - CONTAINERS_CREATE=true
      - CONTAINERS_START=true
      - CONTAINERS_STOP=true
      - CONTAINERS_REMOVE=true
      - CONTAINERS_LIST=true
      - CONTAINERS_LOGS=true
      - IMAGES_PULL=true
      - INFO=true
      - VERSION=true
      # 明确禁止特权操作
      - CONTAINERS_COMMIT=false
      - AUTH=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
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
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
      - STORAGE_ESROLLOVER_MAX_AGE=14d
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
      - /var/log/journal:/var/log/journal:ro
      - /run/log/journal:/run/log/journal:ro
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
    image: elastic/elasticsearch:8.11.0
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

# 预热模型 (执行一次空推理, 确保模型完全加载到显存)
echo "Warming up model..."
ollama run qwen2.5:72b-instruct-q4_K_M "warmup" &
WARMUP_PID=$!
sleep 5
kill $WARMUP_PID 2>/dev/null || true

# 启动 Ollama 服务 (前台运行, 保持容器存活)
echo "Starting Ollama server..."
exec ollama serve
```

**Ollama 模型预热策略**:
- Entrypoint 脚本在启动 Ollama serve 前执行 `ollama pull` 拉取模型
- 拉取完成后执行一次 `ollama run` 空推理预热，确保模型权重完全加载到 GPU 显存
- 预热完成后杀掉预热进程，启动正式的 Ollama serve
- 好处: 首次用户请求无需等待模型加载 (通常需 30-60 秒)，冷启动延迟降至 < 1 秒
- Celery Beat 定时任务每 30 分钟检查模型加载状态，如模型被卸载则重新预热

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

**Celery 健康检查 (HTTP 端点)**:
- V8.0 使用 `celery inspect ping` (RPC 调用)，高负载下可能超时导致 Docker 误判
- V9.0 改为轻量级 HTTP 健康端点:
  - Celery Worker 容器内启动轻量 HTTP 服务器 (端口 8002)
  - `GET /celery-health` 返回 200 如果 Worker 进程存活且能响应
  - Docker healthcheck: `curl -sf http://localhost:8002/celery-health`
  - 超时时间保持 10 秒，但 HTTP 端点响应 < 100ms，不会受 Celery 任务负载影响

**编程 Agent 容器资源限制**:
- Swarm Executor 启动编程 Agent 时通过 nsenter 进入宿主机 PID 命名空间，以宿主机用户身份启动 CLI 工具
- 资源限制通过宿主机预配置的 systemd slice 实现:
  - 创建 `swarm-tools.slice` 设置 CPU 和内存上限
  - 每个编程工具启动时分配到独立 systemd scope
  - CPU 限制: 4 核 (CPUQuota=400%)
  - 内存限制: 8GB (MemoryMax=8G)
- 同一项目蜂群最多并发 4 个 Agent，总资源上限 16 核 CPU / 32GB 内存

**Swarm Executor 宿主机访问机制**:
- **项目文件访问**: 通过 bind mount 挂载 `../../projects:/DevFlow/projects`，Swarm Executor 容器内可直接读写项目文件
- **CLI 工具执行**: Swarm Executor 容器挂载宿主机 PID 命名空间 (`/proc/1/ns/pid_for_children`)，通过 `nsenter --target 1 --pid --mount --walt` 进入宿主机环境后执行编程工具 CLI
- **具体实现** (Python 伪代码):
  ```python
  import subprocess
  
  def run_host_tool(tool_path: str, args: list, workdir: str):
      # 通过 nsenter 进入宿主机 PID+mount 命名空间执行
      cmd = ["nsenter", "--target", "1", "--pid", "--mount", "--walt",
             tool_path] + args
      return subprocess.Popen(cmd, cwd=workdir,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  ```
- **安全边界**:
  - nsenter 仅进入 PID 和 mount 命名空间，不进入 network 命名空间 (容器保留自身网络)
  - 编程工具以宿主机用户 `jim` 身份运行，受 systemd slice 资源限制
  - 编程工具仅可访问 `/DevFlow/projects/` 下的项目目录
  - 容器内 Swarm Executor 进程本身无法直接执行宿主机命令，必须通过 nsenter 桥接

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
- **混合部署运维管理方案**:
  - Docker 容器: `docker compose ps/logs/up/down` 统一命令管理
  - 宿主机进程: `systemctl list-units 'hermes-*.service'` 统一查看，`systemctl restart hermes-{profile}` 统一重启
  - 日志收集: Filebeat 同时采集 Docker 容器日志 (`container` input) 和 systemd 日志 (`systemd` input)，统一推入 Elasticsearch
  - 健康监控: Celery Beat 定时任务统一检查 Docker 容器健康端点和宿主机 Agent 端口
  - 优雅关停: `scripts/shutdown.sh` 脚本同时关停 Docker 容器和 systemd 服务

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
| GPU 型号 | NVIDIA GPU 显存>=40GB (如 A100 40GB) | NVIDIA A100 80GB / RTX 6000 Ada 48GB | 必须支持 CUDA 12+ |
| 显存 (VRAM) | >=40GB | 48GB+ | qwen2.5:72b Q4_K_M 约需 36-40GB 显存 |
| CUDA 版本 | 12.0+ | 12.2+ | Ollama 容器需要 |
| 驱动版本 | 535+ | 545+ | NVIDIA 官方驱动 |
| RTX 4090 (24GB) | 可选 (仅使用 14b 或更小模型) | - | 24GB 不足以加载 72b 模型 |

**说明**: Qwen2.5-72B-Instruct Q4_K_M 量化模型在 GPU 上的显存需求约 36-40GB。最低要求为显存 >= 40GB 的 GPU (如 A100 40GB / RTX 6000 Ada 48GB)。RTX 4090 (24GB) 仅在使用较小模型 (如 qwen2.5:14b-instruct-q4_K_M，约需 8GB 显存) 时可用。

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
| Docker Socket Proxy | 0.5核 | 256MB | 1GB |
| **基础设施小计** | **20.5核** | **33.3GB** | **237GB** |

**Ollama 模型推理资源 (GPU 显存)**:

| 组件 | GPU 显存 | 磁盘 |
|------|---------|------|
| qwen2.5:72b-instruct-q4_K_M (INT4量化) | ~36-40GB VRAM | ~40GB |
| **模型推理小计** | **~40GB VRAM** | **40GB** |

**说明**:
- Ollama 服务进程本身仅需 0.5GB 内存
- 加载 qwen2.5:72b-instruct-q4_K_M 模型需额外 ~36-40GB GPU 显存
- GPU 显存与系统内存分开核算: 系统内存 33.3GB + GPU 显存 40GB

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

**详细内存预算分配表 (生产配置 96GB)**:

| 类别 | 组件 | 内存 (GB) | 说明 |
|------|------|----------|------|
| 基础设施 (Docker) | FastAPI backend | 4.0 | workers=2, 每 worker 约 2GB |
| 基础设施 (Docker) | PostgreSQL (devflow) | 4.0 | shared_buffers=1GB + OS cache |
| 基础设施 (Docker) | PostgreSQL (gitea) | 2.0 | shared_buffers=512MB + OS cache |
| 基础设施 (Docker) | Redis | 2.0 | maxmemory=2GB, AOF-only |
| 基础设施 (Docker) | Gitea | 2.0 | Go 进程 + OS cache |
| 基础设施 (Docker) | Celery Worker | 4.0 | concurrency=8, 每 worker 约 500MB |
| 基础设施 (Docker) | Nginx | 0.5 | 轻量级反向代理 |
| 基础设施 (Docker) | Prometheus | 2.0 | 指标存储 |
| 基础设施 (Docker) | Jaeger | 2.0 | 追踪数据 |
| 基础设施 (Docker) | Elasticsearch | 4.0 | ES_JAVA_OPTS=-Xmx1g + heap overhead |
| 基础设施 (Docker) | Kibana | 2.0 | Node.js 进程 |
| 基础设施 (Docker) | Ollama (服务进程) | 0.5 | 不含模型显存 |
| 基础设施 (Docker) | Swarm Executor | 1.0 | Python 进程 |
| 基础设施 (Docker) | WebSocket Worker | 1.0 | uvicorn 单 worker |
| 基础设施 (Docker) | Celery Beat | 0.5 | 轻量级调度器 |
| 基础设施 (Docker) | Docker Socket Proxy | 0.256 | Go 进程 |
| 基础设施小计 | | **32.8GB** | |
| 宿主机进程 | 9个命名 Agent | 4.5 | 每个 512MB × 9 |
| 宿主机进程 | Swarm 编程工具 | 16.0 | 4个并发 × 4GB (峰值) |
| 宿主机进程小计 | | **20.5GB** | |
| 系统预留 | 操作系统 + 内核 | 6.0 | WSL2/Linux 内核、文件系统缓存 |
| 总计 | | **59.3GB** | 峰值使用 |
| 余量 | | **36.7GB** | 96GB - 59.3GB = 36.7GB |

**总计 (峰值)**:

| 维度 | 总计 | 计算明细 |
|------|------|----------|
| CPU | 35核 | 20.5 (基础设施) + 2 (模型推理) + 4.5 (Agent 进程) + 8 (蜂群) = 35核 |
| 系统内存 (RAM) | 59.3GB | 32.8 (基础设施) + 4.5 (Agent 进程) + 16 (蜂群) + 6.0 (系统预留) = 59.3GB |
| GPU 显存 (VRAM) | 40GB | Ollama 模型推理独占 |
| 磁盘 | 277GB | 237 (基础设施) + 40 (模型磁盘) = 277GB |

**生产部署建议配置**:
- CPU: 32 核
- 系统内存 (RAM): 96GB (生产最低) / 128GB (推荐)
- GPU: NVIDIA GPU, 显存 >= 40GB (如 A100 40GB / RTX 6000 Ada 48GB)
- 磁盘: 300GB+ SSD
- **余量说明**: 96GB 配置下峰值使用 59.3GB，余量 36.7GB (38%)，足够应对突发负载和 Elasticsearch 堆内存扩展

**开发/测试环境配置**:
- CPU: 16 核
- 系统内存 (RAM): 64GB (开发/测试仅用, 余量紧张)
- GPU: NVIDIA GPU, 显存 >= 24GB (RTX 4090, 需使用 14b 或更小模型)
- 磁盘: 200GB+ SSD

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
│  docker-socket-proxy 仅在 devflow_net 内可达          │
│  Swarm Executor 通过 nsenter 访问宿主机编程工具       │
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
│  │  日志: systemd journald → Filebeat → ELK      │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  编程 Agent 工具 (CLI 工具, 安装在宿主机)       │  │
│  │  Claude Code / Codex / Opencode / 等          │  │
│  │  Swarm Executor 通过 nsenter 进入宿主机执行    │  │
│  │  资源限制: systemd slice (CPU 4核/内存 8GB)    │  │
│  │  生命周期: Swarm Executor 管理                  │  │
│  │  日志: 重定向至日志文件 → Filebeat → ELK       │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**跨网络通信说明**:
- Docker 内部网络 `devflow_net`: 所有容器通过该网络通信，使用容器名作为主机名
- Ollama 容器端口 11434 映射到宿主机
- 宿主机上的 Hermes Agent 通过 `http://localhost:11434` 访问 Ollama
- FastAPI 后端与 Hermes Agent 通过宿主机端口 8765-8773 通信 (Gateway API)
- Swarm Executor 容器:
  - 通过 Docker 网络与 Celery/Redis 通信
  - 通过 bind mount 访问项目文件 (`/DevFlow/projects`)
  - 通过 nsenter 进入宿主机 PID 命名空间执行编程工具 CLI
  - 通过 `docker-socket-proxy` 容器访问 Docker API (受限制子集)
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
│  │  3. 通过 nsenter 进入宿主机 PID 命名空间               │  │
│  │     执行编程工具 CLI                                   │  │
│  │  4. 监控执行进度, 收集输出                             │  │
│  │  5. 通过 Webhook 上报结果给 FastAPI 后端               │  │
│  │  6. 任务完成后清理资源                                 │  │
│  │                                                      │  │
│  │  与宿主机交互方式:                                     │  │
│  │  - bind mount: /DevFlow/projects (读写项目文件)        │  │
│  │  - nsenter: 进入宿主机 PID 命名空间执行 CLI 工具        │  │
│  │  - docker-socket-proxy: 访问受限 Docker API            │  │
│  │                                                      │  │
│  │  挂载卷:                                              │  │
│  │  - ../../projects:/DevFlow/projects                   │  │
│  │  - /proc/1/ns/pid_for_children:/host/pid_ns:ro        │  │
│  └──────────────────────────┬───────────────────────────┘  │
│                             │                              │
│  ┌──────────────────────────┴──────────────────────────┐  │
│  │  Docker Socket Proxy (docker-socket-proxy 容器)      │  │
│  │  允许的 API: containers create/start/stop/remove/    │  │
│  │             list/logs, images pull, info, version    │  │
│  │  禁止的 API: 特权容器创建、网络修改、卷挂载等          │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────┘
                               │ nsenter → 宿主机 PID 命名空间
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
│  $ nsenter --target 1 --pid --mount --walt                   │
│      /usr/local/bin/claude-code                              │
│      --project /DevFlow/projects/{project_id}/               │
│      --task "{task_description}"                             │
│      --output /DevFlow/projects/{project_id}/                │
│                                                             │
│  进程隔离:                                                   │
│  - 每个编程工具在独立子进程中运行                              │
│  - 工作目录隔离: /DevFlow/projects/{project_id}/swarm/{id}/  │
│  - 文件锁: 共享资源使用 fcntl.flock() 防止并发冲突            │
│  - 最大并发: 同一项目最多 4 个编程工具同时运行                 │
│  - 资源限制: systemd slice (CPU 4核/内存 8GB)               │
└─────────────────────────────────────────────────────────────┘
```

**Docker Socket 代理安全设计**:
- Swarm Executor 不再直接挂载 `docker.sock`
- 通过 `docker-socket-proxy` 容器访问 Docker API
- 代理仅允许 Swarm Executor 所需的 API 子集:
  - 容器管理: create, start, stop, remove, list, logs
  - 镜像管理: pull
  - 信息查询: info, version
- 明确禁止: 特权容器创建 (`--privileged`)、网络修改、卷挂载到宿主机敏感路径
- 即使编程工具执行恶意代码，也无法通过 Docker API 创建特权容器逃逸

**nsenter 安全边界**:
- Swarm Executor 容器仅挂载宿主机的 PID 命名空间 (`/proc/1/ns/pid_for_children`)
- `nsenter` 命令仅进入 PID 和 mount 命名空间，不进入 network 命名空间
- 编程工具以宿主机用户 `jim` 身份运行，受以下限制:
  - 文件系统: 仅可访问 `/DevFlow/projects/` 目录
  - 资源: systemd slice 限制 CPU 4 核 / 内存 8GB
  - 网络: 编程工具继承宿主机网络命名空间，但受防火墙规则限制
- 容器内 Swarm Executor 进程本身无法直接执行宿主机命令，必须显式通过 `nsenter` 桥接

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

**峰值显存风险评估**:
- qwen2.5:72b-instruct-q4_K_M 模型加载占用 ~36-40GB 显存
- Ollama 单模型实例模式下，无论多少并发请求，模型权重只加载一次
- 并发推理时，Ollama 会为每个请求分配 KV cache (约 0.5-2GB/请求，取决于上下文长度)
- 48GB 显存的 GPU: 模型 40GB + KV cache 余量 8GB，可支持约 4-8 个并发推理请求
- 40GB 显存的 GPU (A100 40GB): 模型 40GB + KV cache 余量 0GB，可能出现 OOM
- **OOM 防护措施**:
  - Ollama 内部队列: 当显存不足时，新请求进入队列等待而非直接 OOM
  - KV cache 限制: 配置 `OLLAMA_MAX_LOADED_MODELS=1` 和 `OLLAMA_NUM_PARALLEL=4` 限制最大并发
  - 请求超时: Agent 侧配置 60 秒超时，超时后自动重试或由 Celery 重新调度
  - 紧急降级: 如持续 OOM，自动切换部分 Agent 到云端模型 (OpenAI/Anthropic)

**推理队列机制**:
- Ollama 内部维护请求队列，按到达顺序处理
- 命名 Agent 侧配置请求超时为 60 秒
- 后端 Gateway Client 使用 `asyncio.Semaphore(5)` 限制对同一 Agent 的并发请求
- 高峰时段策略:
  - 非紧急任务 (文档生成、报告编写) 可延迟执行
  - 紧急任务 (QA 检验、流程调度) 优先调度
  - Celery 任务队列天然支持排队，不会丢失请求

**模型卸载/重载策略**:
- 默认不卸载: 模型常驻显存，避免频繁加载/卸载的开销 (每次加载约 30-60 秒)
- 空闲卸载 (可选): Celery Beat 检测 Ollama 空闲超过 15 分钟时，可选择 `ollama stop` 释放显存
- 重新加载: 下次请求时 Ollama 自动重新加载模型，entrypoint 预热机制确保首次加载后不再冷启动
- 推荐: 生产环境保持模型常驻，开发环境可启用空闲卸载

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
- **单实例实际可用性**: 95-97% (每年约 365-876 小时停机)
  - 单实例 PostgreSQL、Redis、Gitea、Ollama 均为单点故障
  - 任何一个核心组件宕机都导致系统完全不可用
  - 硬件故障、系统更新、电力中断等不可控因素影响可用性
  - 单实例部署的实际可用性取决于硬件可靠性，通常在 95-97% 范围
- **高可用扩展后目标**: 99% 以上 (每年停机 < 87.6 小时)
  - 需要实施 5.1 节高可用扩展方案
  - 99% 可用性基于: 计划内维护 (每月约 8 小时)、硬件故障年均 1-2 次 (每次恢复约 2-4 小时)

**单点故障分析**:

| 组件 | 单点风险 | 影响 | 缓解措施 |
|------|---------|------|----------|
| PostgreSQL (devflow) | 是 | 系统完全不可用 | 自动备份 + 快速恢复 (< 2 小时 RTO) |
| PostgreSQL (gitea) | 是 | 代码托管不可用 | 独立于主库，故障不影响开发 |
| Redis | 是 | 任务队列暂停、WebSocket 断开 | AOF 持久化 + 自动重连 |
| Ollama | 是 | Agent 推理不可用 | 模型预热 + 云端模型降级 |
| Gitea | 是 | 代码仓库不可用 | Git 历史备份 |
| FastAPI 后端 | 是 | API 不可用 | Docker 自动重启 |
| 命名 Agent | 部分 | 单个 Agent 不可用 | systemd 自动重启 + 备用 Agent |
| Swarm Executor | 是 | 编程工具不可调度 | Docker 自动重启 |

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
- `celery-worker`: `curl -sf http://localhost:8002/celery-health` (30s 间隔, HTTP 端点)
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

**优雅关停自动化脚本** (`scripts/shutdown.sh`):
```bash
#!/bin/bash
set -euo pipefail

echo "=== DevFlow 优雅关停 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# Step 1: Nginx 停止接收新请求
echo "[1/8] 配置 Nginx 返回 503..."
cp ./nginx/conf.d/503-maintenance.conf ./nginx/conf.d/devflow.conf
docker exec nginx nginx -s reload 2>/dev/null || true
sleep 5

# Step 2: 关停 Celery Beat (停止新任务调度)
echo "[2/8] 关停 Celery Beat..."
docker compose stop celery-beat
sleep 3

# Step 3: 关停 Swarm Executor (等待正在运行的编程工具)
echo "[3/8] 关停 Swarm Executor..."
docker compose stop swarm-executor
sleep 10

# Step 4: 关停 Celery Worker (完成当前任务)
echo "[4/8] 关停 Celery Worker..."
docker compose stop celery-worker
sleep 15

# Step 5: 关停 WebSocket Worker
echo "[5/8] 关停 WebSocket Worker..."
docker compose stop dedicated-websocket-worker
sleep 5

# Step 6: 关停 FastAPI 后端
echo "[6/8] 关停 FastAPI 后端..."
docker compose stop backend
sleep 5

# Step 7: 关停命名 Agent (systemd)
echo "[7/8] 关停命名 Agent 进程..."
for profile in haimei houxing houwang houfa houda houfu hougui houro houhua; do
    systemctl stop "hermes-${profile}" 2>/dev/null || true
done
sleep 5

# Step 8: 关停依赖组件 (按顺序)
echo "[8/8] 关停依赖组件 (Ollama→Gitea→Redis→PostgreSQL)..."
docker compose stop ollama gitea redis gitea-postgres postgres
sleep 10

# 完全停止所有容器
echo "完全停止所有容器..."
docker compose down

# 恢复 Nginx 配置 (如果重新部署)
echo "优雅关停完成。"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
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
  - WebSocket Worker 重新订阅 Channel 和 Stream 消费者组
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
- 编程工具由 Swarm Executor 通过 nsenter + 子进程调用启动，无需网络认证
- 进程级隔离: Swarm Executor 验证任务合法性后再启动子进程
- 文件级隔离: 编程工具仅可访问分配的工作目录
- 资源级限制: CPU/内存上限防止资源耗尽 (systemd slice)
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
  - Docker Socket Proxy (2375)
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
  - 服务器总资源: 35 核 CPU、59.3GB 系统内存 (峰值) + 40GB GPU 显存 (峰值)
  - 基础设施持续占用: 20.5 核 CPU、32.8GB 内存
  - Ollama 模型推理占用: 40GB GPU 显存
  - 可用资源: 约 12.5 核 CPU、约 57.2GB 内存 (96GB 配置扣除基础设施后)
  - 单个项目平均占用: CPU 0.8 核、内存 2GB
  - 按 80% 资源利用率上限: CPU 可支撑约 15 个项目, 内存可支撑约 28 个项目
  - 取 CPU 为瓶颈 (考虑蜂群并发): 保守估计 10 个并发项目
- **Agent 并发限制**: 同 Profile 同一时间仅执行 1 个任务
- **WebSocket 并发**: 单群组支持 10+ Agent 在线，由专用 WebSocket Worker 处理
- **API 并发**: 信号量限制 5 个/Agent
- **Ollama 并发**: 单模型实例 + 内部请求队列, 约 5-10 QPS (GPU 模式)
- **API 速率限制**: slowapi 中间件，按端点类型配置不同限额 (详见 2.3 节)

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
- 保留 14 天 (hot 存储)
- 14-90 天数据归档至冷存储 (ES 索引生命周期管理 ILM)
- 90 天以上数据可删除或迁移至对象存储
- Span 命名规范: `{service}.{operation}` (如 `backend.workflow.execute_step`)

### 8.3 日志管理 (ELK Stack)

- **组件部署**: Elasticsearch + Logstash (由 Filebeat 替代) + Kibana
- **采集方式**: Filebeat 采集各容器日志和 systemd 日志, 推送至 Elasticsearch
- **日志来源**:
  - Docker 容器日志: Filebeat `container` input 采集 `/var/lib/docker/containers/` 下的 JSON 日志
  - 宿主机 Agent 日志: Filebeat `systemd` input 采集 `hermes-*.service` 的 journald 日志
  - 编程工具日志: 重定向至 `/DevFlow/projects/{project_id}/swarm/{id}/logs/`，Filebeat `file` input 采集
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
- `GET /api/v1/projects` — 项目列表 (支持 `?page=&page_size=&status=&sort_by=&sort_order=`)
- `GET /api/v1/projects/{id}` — 项目详情
- `GET /api/v1/projects/{id}/workflow` — 16 步流程状态

**Agent 管理**:
- `GET /api/v1/agents` — Agent 列表和状态 (支持 `?status=` 过滤)
- `GET /api/v1/agents/{profile}/status` — 单个 Agent 状态
- `POST /api/v1/agents/{profile}/chat` — 与 Agent 对话

**蜂群管理**:
- `POST /api/v1/swarms` — 创建蜂群
- `GET /api/v1/swarms/{id}` — 蜂群状态
- `GET /api/v1/swarms/{id}/tasks` — 蜂群任务列表 (支持 `?page=&page_size=&status=`)

**QA 门控**:
- `POST /api/v1/qa/inspect` — 触发 QA 检验
- `GET /api/v1/qa/results/{id}` — QA 检验结果

**群聊协作**:
- `GET /ws/group/{id}` — WebSocket 群聊连接

**API 分页/过滤/排序通用规范**:
- 分页参数: `page` (默认 1), `page_size` (默认 20, 最大 100)
- 过滤参数: 各端点定义可用过滤字段 (如 `status`, `created_after`, `created_before`)
- 排序参数: `sort_by` (字段名), `sort_order` (`asc` 或 `desc`, 默认 `desc`)
- 响应 envelope: `{"data": [...], "total": N, "page": P, "page_size": S, "total_pages": T}`
- 速率限制由 slowapi 中间件统一处理，超限返回 429

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
    → nsenter 进入宿主机执行编程工具
    → 编程工具执行 → 产出代码
    → Swarm Executor 收集结果 → Webhook 回调 FastAPI
    → 后荣 QA 检验
```

### 9.3 Git 分支命名策略

**分支命名规范**:
- **主分支**: `main` (受保护，仅允许 QA 检验通过的合并)
- **开发分支**: `dev/{project_id}` (项目开发主分支)
- **功能分支**: `feature/{project_id}/{step}-{brief_desc}`
  - 示例: `feature/prj-001/step3-requirements`
  - 示例: `feature/prj-001/step9-auth-module`
- **QA 分支**: `qa/{project_id}/{step}` (QA 检验专用分支)
  - 示例: `qa/prj-001/step3`
- **热修复分支**: `hotfix/{project_id}/{issue-desc}`
  - 示例: `hotfix/prj-001/login-crash`

**分支流转**:
```
main ← qa/{project_id}/{step} ← feature/{project_id}/{step}-{desc}
       (QA检验通过合并)        (功能开发完成合并)
```

**分支保护规则**:
- `main`: 禁止直接推送，仅允许从 `qa/*` 分支合并，需 QA 检验通过记录
- `dev/{project_id}`: 允许从 `feature/*` 分支合并
- `feature/*`: 开发完成后合并到 `dev/{project_id}` 或 `qa/{project_id}/{step}`
- `qa/*`: 仅由后荣 (HouRong) 创建和管理

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
- **INITIALIZING**: Swarm Executor 正在通过 nsenter 启动子进程，准备执行环境
- **RUNNING**: 工具正在执行任务
- **COMPLETING**: 任务完成，正在收集输出
- **CLEANING**: 清理临时文件和资源
- **FAILED**: 执行失败，记录错误并回滚
- **TIMEOUT**: 执行超时 (默认 30 分钟)，发送 SIGTERM 终止

**管理策略**:
- **进程隔离**: 每个编程工具在独立子进程中运行，通过 `nsenter` + `subprocess.Popen` 启动
- **工作目录隔离**: 每个工具分配独立目录 `/DevFlow/projects/{project_id}/swarm/{tool_id}/`
- **资源限制**: CPU 4 核 / 内存 8GB
  - 实现方式: 宿主机预配置 systemd slice (`swarm-tools.slice`)
  - Swarm Executor 启动子进程时通过 `systemd-run --scope -p CPUQuota=400% -p MemoryMax=8G` 分配
  - Swarm Executor 为容器内 Python 进程，无法直接对宿主机子进程设置 cgroup，故需预配置
- **超时控制**: 默认 30 分钟超时，超时后发送 SIGTERM，5 秒后 SIGKILL
- **文件锁**: 共享资源使用 `fcntl.flock()` 防止并发冲突
- **最大并发**: 同一项目最多 4 个编程工具同时运行
- **空闲清理**: 工具空闲超过 10 分钟自动释放资源
- **日志采集**: 工具 stdout/stderr 重定向到日志文件，Filebeat 采集至 ELK

**宿主机 cgroup 预配置** (`/etc/systemd/system/swarm-tools.slice`):
```ini
[Unit]
Description=Swarm Programming Tools Resource Slice

[Slice]
CPUQuota=640%        # 4个工具 × 4核 = 16核上限
MemoryMax=32G        # 4个工具 × 8GB = 32GB上限
```

**冲突解决**:
- 代码文件冲突: Swarm Executor 检测到文件锁冲突时，将任务排入队列等待
- 合并冲突: 由后发/后达命名 Agent 进行代码审查和合并
- 资源竞争: systemd slice 限制防止单个工具耗尽资源

### 10.2 通知机制

**通知渠道**:

| 渠道 | 用途 | 实现方式 |
|------|------|----------|
| WebSocket 实时推送 | 群聊消息、进度更新、即时告警 | WebSocket 连接 + Redis Pub/Sub/Stream |
| 邮件通知 | 重要事件通知、日报/周报 | SMTP + 邮件模板 |
| 站内通知 | 系统消息、任务分派通知 | 数据库存储 + WebSocket 推送 |

**WebSocket 推送流程**:
1. FastAPI 后端产生通知事件
2. 写入 PostgreSQL `notifications` 表
3. 普通消息: 发布到 Redis Pub/Sub `global:notifications` Channel
4. 关键通知: 写入 Redis Stream `critical:notifications`
5. WebSocket Worker 消费 Pub/Sub + Stream 消息
6. 推送给所有在线的 WebSocket 客户端

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

系统优雅关停流程已在 5.5 节详细描述，包括各组件的关停顺序、shutdown.sh 自动化脚本实现和工作流中断处理。

---

## 12. 数据一致性保障

### 12.1 一致性设计原则

16 步流程涉及多个组件协同 (FastAPI → 命名 Agent → 后荣 QA → Swarm Executor → 编程工具 → Git → Gitea)，任一环节失败都可能导致数据不一致。本设计采用 **最终一致性** 模型，结合 checkpoint、事务日志和补偿机制保障数据完整性。

**一致性级别**:

| 操作 | 一致性要求 | 实现方式 |
|------|-----------|----------|
| 数据库写入 (DevFlow) | 强一致性 | PostgreSQL 事务 (ACID) |
| Git 提交 | 强一致性 | Git 原子操作 (commit 要么成功要么失败) |
| Gitea 写入 | 最终一致性 | Gitea REST API + 重试机制 |
| Redis 缓存 | 最终一致性 | 缓存失效 + 从数据库重新加载 |
| 通知推送 | 最终一致性 | Redis Stream 可靠队列 + ACK |
| 文件写入 | 最终一致性 | 写入临时文件 → 原子重命名 |

### 12.2 各步骤失败处理与补偿机制

**Step 1-6 (文档类产出)**:

| 失败场景 | 影响 | 补偿机制 |
|----------|------|----------|
| 命名 Agent 执行失败 | 产出文档未生成 | RetryManager 自动重试 3 次，仍失败则海梅介入 |
| QA 检验失败 | 产出退回重做 | 不提交代码库，保持上一步状态不变 |
| Gitea 写入失败 | 文档未入库 | 本地文件已保存，Gitea API 重试 3 次 (指数退避 30s/60s/120s) |
| 数据库写入失败 | 步骤状态未更新 | PostgreSQL 事务回滚，checkpoint 保留上一步状态 |

**Step 7/9/11 (代码类产出，涉及编程工具)**:

| 失败场景 | 影响 | 补偿机制 |
|----------|------|----------|
| Swarm Executor 调度失败 | 编程工具未启动 | Celery 任务重试，Swarm Executor 重新选择工具 |
| 编程工具执行失败 | 代码未生成或部分生成 | 1. 检查本地工作目录是否有部分产出 2. 如有，Git add 已完成的文件 3. 如无，标记 FAIL 并通知后发/后达 |
| 编程工具已完成但 Git 提交失败 | 代码存在于本地但未提交 | 1. 本地文件保留在 `/DevFlow/projects/{project_id}/swarm/{id}/` 2. Git 提交重试 3 次 3. 仍失败则标记 NEED_REVIEW，海梅手动介入 |
| Git 提交成功但 Gitea 写入失败 | 代码已在本地 Git 仓库但 Gitea 未同步 | 1. 本地 Git 仓库已保存 (git commit 已执行) 2. Gitea push 重试 3 次 3. 仍失败则记录待同步状态，恢复后自动重推 |
| QA 检验失败 (代码类) | 代码退回重做 | 1. 撤销未合并到 main 的 Git 提交 2. 保留 feature 分支供调试 3. 重新执行步骤 |

**Step 12-16 (部署和交付类)**:

| 失败场景 | 影响 | 补偿机制 |
|----------|------|----------|
| 生产部署失败 | 环境未更新 | 1. 部署脚本回滚到上一个稳定版本 2. 记录部署失败原因 3. 通知后富重新部署 |
| 文档完善失败 | 文档未更新 | 同 Step 1-6 的补偿机制 |
| 交付报告生成失败 | 报告未生成 | RetryManager 重试，仍失败则海梅手动生成 |
| 用户不满意 (Step 16) | 项目回到 Step 3 | 保留所有已完成产出的 Git 分支，从 Step 3 重新开始 |

### 12.3 事务边界与补偿事务

**事务边界定义**:

```
┌───────────────────────────────────────────────────────────┐
│  事务 1: 步骤状态更新 (数据库)                              │
│  开始: StepExecutor.execute() 入口                         │
│  操作: 更新 workflow_steps 状态为 RUNNING                   │
│  保存: checkpoint 记录                                      │
│  提交: 状态更新成功                                         │
│  回滚: 更新失败则保持上一步状态                              │
└───────────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────┐
│  事务 2: Agent 执行 (不可回滚)                              │
│  操作: 命名 Agent 生成产出                                  │
│  特点: Agent 执行是外部调用，无法事务回滚                    │
│  补偿: 如后续步骤失败，产出保留在本地文件系统                 │
│         下次重试时可复用已生成的产出                          │
└───────────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────┐
│  事务 3: QA 检验 (可重试)                                  │
│  操作: 后荣执行 QA 检验                                      │
│  通过: 进入事务 4                                           │
│  不通过: 回退到事务 2，重新执行 Agent                       │
└───────────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────┐
│  事务 4: 代码提交 (Git + Gitea)                            │
│  操作 4a: git add + git commit (本地原子操作)               │
│  操作 4b: git push → Gitea (网络操作，可能失败)             │
│  补偿: 4a 成功但 4b 失败 → 记录待同步状态 → 自动重推        │
│  补偿: 4a 失败 → 代码保留在本地工作目录 → 重试              │
└───────────────────────────────────────────────────────────┘
```

**补偿事务实现** (Python 伪代码):

```python
class CompensationManager:
    """补偿事务管理器"""

    async def execute_with_compensation(self, step_number: int,
                                        project_id: str) -> StepResult:
        # 事务 1: 更新步骤状态
        async with database.transaction() as tx:
            await update_step_status(step_number, 'RUNNING', tx)
            await save_checkpoint(step_number, 'step_started', tx)

        # 事务 2: 执行 Agent (不可回滚)
        artifact = await execute_agent(step_number, project_id)

        # 事务 3: QA 检验
        qa_result = await qa_inspect(artifact, step_number)
        if not qa_result.passed:
            return await self.handle_qa_failure(step_number, qa_result)

        # 事务 4: 代码提交
        try:
            await git_commit(project_id, artifact)  # 4a: 本地原子操作
            await git_push_with_retry(project_id)     # 4b: 网络操作 + 重试
        except GitPushError as e:
            # 补偿: 本地 commit 已成功，Gitea push 失败
            await self.record_pending_sync(project_id, step_number, e)
            # 不标记步骤失败，记录待同步状态
            # Celery Beat 定时任务会定期检查并重推

        # 更新步骤状态为 SUCCESS
        async with database.transaction() as tx:
            await update_step_status(step_number, 'SUCCESS', tx)
            await save_checkpoint(step_number, 'step_completed', tx)

        return StepResult(status='SUCCESS', artifact=artifact)

    async def handle_pending_syncs(self) -> None:
        """Celery Beat 定时任务: 检查并重推待同步的 Git 提交"""
        pending = await get_pending_syncs()
        for item in pending:
            try:
                await git_push(item.project_id)
                await clear_pending_sync(item.id)
            except GitPushError:
                await increment_retry_count(item.id)
                if item.retry_count >= 3:
                    await notify_haimei(f"Git push 失败, 需人工介入: {item}")
```

### 12.4 文件写入原子性

编程工具生成的代码文件采用原子写入策略，防止部分写入导致文件损坏:

```python
import os
import tempfile

def atomic_write(file_path: str, content: str) -> None:
    """原子写入文件: 先写入临时文件，再重命名"""
    dir_name = os.path.dirname(file_path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, file_path)  # 原子重命名
    except:
        os.unlink(tmp_path)  # 清理临时文件
        raise
```

### 12.5 数据一致性验证

**每日一致性检查** (Celery Beat 定时任务):

| 检查项 | 方法 | 频率 |
|--------|------|------|
| 步骤状态 vs Git 提交 | 对比 workflow_steps 状态与 Gitea 分支提交记录 | 每日 1 次 |
| 待同步队列 | 检查 pending_syncs 表是否有未完成的 Git push | 每 30 分钟 |
| Checkpoint 完整性 | 扫描 RUNNING 状态但无 checkpoint 的步骤 | 每日 1 次 |
| 文件完整性 | 检查项目目录与数据库记录是否一致 | 每日 1 次 |

**一致性告警**:
- 发现不一致时记录到 `consistency_issues` 表
- 触发 WebSocket 告警通知管理员
- 严重不一致 (如代码丢失) 自动创建海梅待办事项

---

文档结束
