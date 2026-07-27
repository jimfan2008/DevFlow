# DevFlow 项目管理平台 - 架构设计文档

**版本**: V8

**日期**: 2026-06-16

**作者**: HouWang (后旺)

**状态**: 修订版V8（等待后荣检验）

---

## 1. 架构概述

### 1.1 设计目标

DevFlow 是一个 AI Agent 全自动软件开发项目管理平台，通过 9 个命名 Hermes Agent 角色协作完成 16 步标准开发流程。本平台架构设计的核心目标是：

1. **全流程自动化**：从需求分析到部署交付，16 步标准流程由 Agent 自动执行，每步产出经 QA 门控检验。
2. **多 Agent 协作**：9 个命名 Agent 角色通过独立 Hermes Profile 实例部署，各自独立运行，通过 Gateway API 与 DevFlow 平台通信。
3. **实时沟通**：项目讨论群作为 Agent 间协作的核心渠道，支持讨论模式和会议模式。
4. **蜂群编程**：后发（程序员）和后达（测试员）可建立编程 Agent 蜂群，调度多种编程 Agent 并行执行任务。
5. **高质量交付**：后荣（QA）作为质量门控贯穿全流程，每步产出必须检验合格方可进入下一步。
6. **容器化部署**：全部服务通过 Docker + Docker Compose 统一部署，便于运维和扩展。

### 1.2 设计原则

* **分层架构**：前端展示层、后端服务层、Agent 交互层、数据持久层清晰分离，各层职责单一。
* **松耦合通信**：平台与 Agent 之间通过标准化 Gateway API 通信，降低耦合度，支持 Agent 类型的灵活替换。
* **异步优先**：Agent 任务执行、蜂群调度、QA 检验等耗时操作采用异步处理（Celery + asyncio），不阻塞主服务线程。
* **可观测性**：全链路追踪（OpenTelemetry）、指标采集（Prometheus）、结构化日志（JSON + ELK）三位一体。
* **高可用容错**：Agent 执行失败自动重试（最多 3 次，指数退避），超时（30 分钟）后切换备用 Agent。
* **安全隔离**：项目级别资源隔离，每个项目的 Agent 执行在独立会话空间中运行，多用户数据逻辑隔离。

### 1.3 架构演进

DevFlow 架构从单体应用演进为多 Agent 协作平台，核心变化：

* V1-V3：传统项目管理平台，人工执行各阶段任务。
* V4：引入 AI Agent 概念，10 个 Agent 角色协作。
* V5-V6：重构为 9 个命名 Agent 角色，每角色独立 Hermes Profile，独立 Gateway 端口。
* V8（当前）：完善架构设计，明确通信机制、性能架构、部署架构、监控告警体系。

---

## 2. 总体架构图

### 2.1 系统总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          人类用户 (客户端层)                               │
│          浏览器 / 移动端 (Chrome 90+, Firefox 88+, Safari 14+)            │
│          功能：项目创建 / 需求沟通 / 进度查看 / 群聊 / 会议 / 成果验收      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP (REST API) + WebSocket (实时通信)
┌───────────────────────────────▼─────────────────────────────────────────┐
│                        Nginx (反向代理层)                                 │
│          负载均衡 / SSL终止 / 静态资源服务 / WebSocket 代理                 │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                     DevFlow 后端服务层 (FastAPI)                          │
│                                                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │
│  │ 16步流程    │ │ Agent蜂群   │ │ QA门控     │ │ 项目讨论群          │  │
│  │ 调度引擎    │ │ 调度管理    │ │ 检验引擎   │ │ (讨论/会议模式)    │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │
│  │ Profile    │ │ Gateway    │ │ 代码库     │ │ 通知与交付          │  │
│  │ 扫描同步    │ │ Client     │ │ Gitea集成  │ │ (WebSocket推送)    │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │
│  │ 用户认证    │ │ 任务管理    │ │ 会议管理    │ │ 监控与告警          │  │
│  │ (JWT/RBAC) │ │ (依赖图)   │ │ (议程/纪要) │ │ (Prometheus)       │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘  │
│                                                                         │
│  异步任务队列: Celery Workers + Redis Broker                             │
└──────────┬──────────────────────────────────┬──────────────────────────┘
           │                                  │
    Gitea REST API                  Gateway API (HTTP + WebSocket/SSE)
           │                                  │
┌──────────▼─────────────────────────┐  ┌────▼──────────────────────────┐
│     Gitea 代码托管层                │  │   9个命名Agent角色              │
│  (本地部署，自托管Git服务)           │  │   (Hermes Profiles, 独立进程)   │
│  代码仓库 / Git Flow / PR 审核     │  │                                │
│  统一成果存储，检验合格即刻提交      │  │  ┌────────┐ ┌────────┐       │
└────────────────────────────────────┘  │  │ HaiMei │ │HouXing │       │
                                        │  │ 海梅   │ │ 后兴   │       │
                                        │  │ 项目经理│ │ 需求分析│       │
                                        │  └───┬────┘ └───┬────┘       │
                                        │  ┌───┴────┐ ┌───┴────┐       │
                                        │  │HouWang │ │ HouFa  │       │
                                        │  │ 后旺   │ │ 后发   │       │
                                        │  │ 架构设计│ │ 程序员 │       │
                                        │  └───┬────┘ └───┬────┘       │
                                        │  ┌───┴────┐ ┌───┴────┐       │
                                        │  │ HouDa  │ │ HouFu  │       │
                                        │  │ 后达   │ │ 后富   │       │
                                        │  │ 测试员 │ │ CI/CD  │       │
                                        │  └───┬────┘ └───┬────┘       │
                                        │  ┌───┴────┐ ┌───┴────┐       │
                                        │  │HouGui  │ │HouRong │       │
                                        │  │ 后贵   │ │ 后荣   │       │
                                        │  │ 文档管理│ │ QA门控 │       │
                                        │  └───┬────┘ └───┬────┘       │
                                        │  ┌───┴────┐                   │
                                        │  │ HouHua │                   │
                                        │  │ 后华   │                   │
                                        │  │ 安全员 │                   │
                                        │  └────────┘                   │
│  端口分配: 8765(海梅) 8766(后兴) 8767(后旺) 8768(后发)                 │
│  8769(后达) 8770(后富) 8771(后贵) 8772(后荣) 8773(后华)                │
└────────────────────────────────────────────────────────────────────────┘
           │
           │ 蜂群调度
┌──────────▼─────────────────────────────────────────────────────────────┐
│                        Agent蜂群层                                      │
│  后发(第七步/第九步) 和 后达(第十一步) 可建立编程Agent蜂群               │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Claude   │ │  Codex   │ │Opencode  │ │  Cursor  │ │ CodeArts │    │
│  │  Code    │ │          │ │          │ │          │ │          │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │  Trae    │ │  Lingma  │ │ hermes子agent │ │ pi-codeing-agent │     │
│  │          │ │          │ │              │ │  子agent          │     │
│  └──────────┘ └──────────┘ └──────────────┘ └──────────────────┘     │
│                                                                         │
│  蜂群Agent通过 REST API 与 DevFlow 通信：                               │
│  任务获取 / 进度上报 / 成果交付 / 错误上报                               │
└────────────────────────────────────────────────────────────────────────┘
           │
┌──────────▼─────────────────────────────────────────────────────────────┐
│                       数据持久层                                        │
│  ┌──────────────────────────┐  ┌──────────────────────────┐            │
│  │ PostgreSQL 14+            │  │ Redis 6+                  │            │
│  │ (主数据库)                │  │ (缓存/状态/消息队列)      │            │
│  │                          │  │                          │            │
│  │ 用户/项目/任务/Agent      │  │ 会话状态/蜂群状态/        │            │
│  │ 群聊/会议/QA记录/代码库   │  │ Celery Broker/结果后端    │            │
│  └──────────────────────────┘  └──────────────────────────┘            │
└────────────────────────────────────────────────────────────────────────┘
           │
┌──────────▼─────────────────────────────────────────────────────────────┐
│                       可观测性层                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐               │
│  │ Prometheus   │ │  Jaeger      │ │  ELK Stack        │               │
│  │ (指标采集)   │ │ (链路追踪)   │ │ (日志管理)        │               │
│  └──────────────┘ └──────────────┘ └──────────────────┘               │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 架构分层说明

| 层级 | 技术组件 | 职责 |
|------|----------|------|
| 客户端层 | Vue 3 + Element Plus | 用户交互界面，项目创建、进度查看、群聊、会议参与、成果验收 |
| 反向代理层 | Nginx | 负载均衡、SSL 终止、静态资源服务、WebSocket 代理 |
| 后端服务层 | Python FastAPI + Celery + asyncio | 16 步流程调度、Agent 蜂群管理、QA 门控、项目讨论群、代码库集成、通知管理 |
| Agent 交互层 | Gateway Client + Profile Scanner + Conversation Coordinator | 与 9 个命名 Agent 通信，自动发现 Profile，协调多 Agent 对话 |
| 代码托管层 | Gitea (本地部署) | 代码仓库管理、Git Flow 分支策略、PR 审核、成果统一存储 |
| Agent 层 | 9 个 Hermes Profile 实例 | 各 Agent 独立进程运行，通过 Gateway API 暴露 REST + WebSocket 接口 |
| 蜂群层 | Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma / hermes 子 agent / pi-codeing-agent 子 agent | 编程 Agent 集群，由后发/后达调度，并行执行代码编写/测试任务 |
| 数据持久层 | PostgreSQL 14+ + Redis 6+ | 主数据存储 + 缓存/状态存储/消息队列 |
| 可观测性层 | Prometheus + Jaeger + ELK Stack | 指标采集、链路追踪、日志管理、告警 |

---

## 3. 技术选型

### 3.1 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 前端框架，组件化开发 |
| Element Plus | 2.x | UI 组件库 |
| Vue I18n | 9.x | 国际化多语言支持 |
| WebSocket 客户端 | 原生 API | 实时通信（群聊、进度推送） |
| 浏览器支持 | Chrome 90+ / Firefox 88+ / Safari 14+ | 最低浏览器要求 |

### 3.2 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ (推荐 3.11) | 后端运行时 |
| FastAPI | 0.100+ | RESTful API 框架，异步支持 |
| Celery | 5.x | 分布式任务队列，处理耗时操作（Agent 任务执行、蜂群调度、QA 检验） |
| asyncio | Python 内置 | 异步并发控制，WebSocket 连接管理 |
| Pydantic | 2.x | 数据验证和配置管理 |
| SQLAlchemy | 2.x | ORM 框架，数据库操作 |
| Alembic | 1.x | 数据库迁移管理 |
| OpenTelemetry | 1.x | 全链路追踪 |
| JWT | pyjwt | 用户认证 Token |

### 3.3 数据库与缓存

| 技术 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 14+ | 主数据库，存储用户、项目、任务、Agent、群聊、QA 记录、代码库元数据 |
| Redis | 6+ | 缓存、会话状态、蜂群状态、Celery Broker 和 Result Backend |

### 3.4 代码托管

| 技术 | 版本 | 用途 |
|------|------|------|
| Gitea | latest | 本地部署的自托管 Git 服务，代码仓库管理、Git Flow、PR 审核 |
| Git | 2.25+ | 版本控制 |

### 3.5 AI Agent 层

| 技术 | 说明 |
|------|------|
| Hermes Agent | 由 Nous Research 开发的开源 AI 代理，9 个命名 Agent 各部署独立 Profile 实例 |
| Hermes Gateway | 每个 Agent Profile 独立 Gateway 端口 (8765-8773)，暴露 REST API + WebSocket 接口 |
| Profile Scanner | DevFlow 自动扫描用户 profiles 目录，发现和识别可用 Hermes Agent |
| Gateway Client | DevFlow 平台通过 Gateway API 与 Agent 通信，支持流式 (SSE) 和非流式响应 |
| 编程 Agent 蜂群 | Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma / hermes 子 agent / pi-codeing-agent 子 agent |

### 3.6 部署与运维

| 技术 | 版本 | 用途 |
|------|------|------|
| Docker | 24+ | 容器化运行时 |
| Docker Compose | 2.x | 多容器编排 |
| Nginx | 1.24+ | 反向代理，负载均衡 |
| Prometheus | latest | 指标采集和存储 |
| Jaeger | latest | 链路追踪后端 |
| ELK Stack | latest | 日志集中管理 (Elasticsearch + Logstash + Kibana) |

### 3.7 测试与前端验证

| 技术 | 用途 |
|------|------|
| Playwright / Selenium | 前端实操验证，浏览器自动化操作 |

---

## 4. 部署架构

### 4.1 部署拓扑

```
┌───────────────────────────────────────────────────────────────────────┐
│                         宿主机 (Linux, Docker)                          │
│                                                                       │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────────────────┐  │
│  │  Nginx   │───►│  DevFlow     │    │  Celery Workers (N个)      │  │
│  │  (80/443)│    │  (FastAPI    │    │  (异步任务执行)             │  │
│  │          │◄───│   后端)       │    │                           │  │
│  └──────────┘    └──────┬───────┘    └────────────────────────────┘  │
│                         │                                            │
│  ┌──────────────┐  ┌────┴──────────┐  ┌─────────────────────────┐  │
│  │ PostgreSQL   │  │  Redis         │  │  Gitea                  │  │
│  │  (5432)      │  │  (6379)        │  │  (3000/22)              │  │
│  └──────────────┘  └───────────────┘  └─────────────────────────┘  │
│                                                                       │
│  ┌─────────────────── 9个命名Agent (独立进程) ───────────────────┐  │
│  │                                                              │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │  │
│  │  │8765  │ │8766  │ │8767  │ │8768  │ │8769  │ │8770  │    │  │
│  │  │海梅  │ │后兴  │ │后旺  │ │后发  │ │后达  │ │后富  │    │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐                                │  │
│  │  │8771  │ │8772  │ │8773  │                                │  │
│  │  │后贵  │ │后荣  │ │后华  │                                │  │
│  │  └──────┘ └──────┘ └──────┘                                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─────────────────── 可观测性 ─────────────────────────────────┐  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │  │
│  │  │Prometheus│ │  Jaeger  │ │Elastic-  │ │  Kibana  │       │  │
│  │  │(9090)    │ │(16686)   │ │search    │ │(5601)    │       │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  数据卷挂载:                                                            │
│  /data/postgres   - PostgreSQL 数据                                   │
│  /data/redis      - Redis 数据                                        │
│  /data/gitea      - Gitea 数据                                        │
│  /data/git        - Git 仓库数据                                      │
│  /data/backups    - 备份数据                                          │
│  ~/.hermes        - Hermes Profiles 配置                              │
│  /DevFlow/projects - 项目工作目录                                     │
└───────────────────────────────────────────────────────────────────────┘
```

### 4.2 Docker Compose 部署结构

```yaml
version: "3"

services:
  # 反向代理
  nginx:
    image: nginx:1.24
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./configs/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - devflow

  # DevFlow 后端
  devflow:
    build: ./devflow
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://devflow:password@postgres:5432/devflow
      - REDIS_URL=redis://redis:6379/0
      - GITEA_URL=http://gitea:3000
    depends_on:
      - postgres
      - redis
    volumes:
      - /DevFlow/projects:/DevFlow/projects

  # Celery Workers (可水平扩展)
  celery-worker:
    build: ./devflow
    command: celery -A devflow.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://devflow:password@postgres:5432/devflow
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3

  # 数据库
  postgres:
    image: postgres:14
    environment:
      - POSTGRES_USER=devflow
      - POSTGRES_PASSWORD=devflow_password
      - POSTGRES_DB=devflow
    ports:
      - "5432:5432"
    volumes:
      - /data/postgres:/var/lib/postgresql/data

  # 缓存/消息队列
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - /data/redis:/data

  # 代码托管
  gitea:
    image: gitea/gitea:latest
    environment:
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=postgres:5432
      - GITEA__database__NAME=gitea
    ports:
      - "3000:3000"
      - "222:22"
    volumes:
      - /data/gitea:/data
    depends_on:
      - postgres

  # 可观测性
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"

  # 日志管理
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

# 9个命名Agent进程独立于Docker容器外运行
# 各Agent通过 hermes gateway 命令启动，绑定对应端口
# 端口映射: 8765(海梅) 8766(后兴) 8767(后旺) 8768(后发) 8769(后达)
#           8770(后富) 8771(后贵) 8772(后荣) 8773(后华)
```

### 4.3 Agent 部署模型

9 个命名 Agent 角色采用独立 Profile 实例部署模式：

* **独立进程**：每个 Agent 对应独立的 Hermes Agent Profile 实例，拥有独立的配置文件 (config.yaml)、独立的 Gateway 端口、独立的模型配置。
* **Profile 存储路径**：`~/.hermes/profiles/{profile_name}/`（如 `haimei/`、`houxing/`、`houwang/` 等）。
* **Gateway 通信**：各 Agent 通过各自的 Gateway 端口暴露 REST API + WebSocket 接口，DevFlow 平台通过 Gateway API 与各 Agent 通信。
* **端口分配**：

| Agent | 中文名 | 角色 | Gateway 端口 |
|-------|--------|------|-------------|
| HaiMei | 海梅 | 项目经理 | 8765 |
| HouXing | 后兴 | 需求分析师 | 8766 |
| HouWang | 后旺 | 架构设计师 | 8767 |
| HouFa | 后发 | 程序员 (蜂群调度) | 8768 |
| HouDa | 后达 | 测试员 (蜂群调度) | 8769 |
| HouFu | 后富 | CI/CD 工程师 | 8770 |
| HouGui | 后贵 | 文档管理员 | 8771 |
| HouRong | 后荣 | QA (门控) | 8772 |
| HouHua | 后华 | 安全员 | 8773 |

* **进程管理**：各 Agent 进程独立启动、独立运行、独立停止，互不影响。
* **自动发现**：DevFlow Profile Scanner 定期扫描 `~/.hermes/profiles/` 目录，自动发现和识别可用 Agent，检测 Gateway 运行状态（端口监听检查）。

### 4.4 运行环境要求

* **操作系统**：Linux（生产推荐）、macOS、Windows（仅限 WSL2 或 PowerShell Beta）。
* **Python**：3.10+（推荐 3.11）。
* **Node.js**：部分 gateway 功能需要。
* **磁盘空间**：最低 500MB，推荐 2GB+。
* **浏览器**：Chrome 90+ / Firefox 88+ / Safari 14+。
* **Gitea 依赖**：Go 1.21+（源码安装需要）、Git 2.25+。

---

## 5. 组件交互

### 5.1 核心组件交互关系

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│ 人类用户  │────►│ DevFlow后端  │────►│ 命名Agent    │────►│ Gitea    │
│ (前端)    │◄────│ (FastAPI)    │◄────│ (Hermes)     │◄────│ 代码托管  │
└──────────┘     └──────┬───────┘     └──────────────┘     └──────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
     ┌───────────┐ ┌────────┐ ┌──────────┐
     │ PostgreSQL │ │ Redis  │ │ Celery   │
     │ (主存储)   │ │(缓存/  │ │ Workers  │
     │           │ │ MQ)    │ │(异步任务)│
     └───────────┘ └────────┘ └──────────┘
```

### 5.2 16 步流程中的组件交互

16 步标准开发流程中，各组件的交互关系如下：

| 步骤 | 触发者 | 执行者 | 涉及组件 | 产出存储 |
|------|--------|--------|----------|----------|
| 第一步 | 人类用户 | 人类用户 | DevFlow 后端、Gitea | 项目文件夹 + Gitea 仓库 |
| 第二步 | 海梅 | 海梅 (8765) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第三步 | 海梅→后兴 | 后兴 (8766) | DevFlow 后端、Gateway、群聊 | Gitea (develop 分支) |
| 第四步 | 海梅→后旺 | 后旺 (8767) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第五步 | 海梅→后富 | 后富 (8770) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第六步 | 海梅 | 海梅 (8765) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第七步 | 海梅→后发 | 后发+蜂群 (8768) | DevFlow 后端、蜂群 API | Gitea (feature/* 分支) |
| 第八步 | 海梅 | 海梅 (8765) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第九步 | 海梅→后发 | 后发+蜂群 (8768) | DevFlow 后端、蜂群 API | Gitea (feature/* 分支) |
| 第十步 | 海梅→后富 | 后富 (8770) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第十一步 | 海梅→后达 | 后达+蜂群 (8769) | DevFlow 后端、蜂群 API | Gitea (develop/PR) |
| 第十二步 | 海梅→后华 | 后华 (8773) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第十三步 | 海梅→后富 | 后富 (8770) | DevFlow 后端、Gateway | Gitea (release/* 分支) |
| 第十四步 | 海梅→后贵 | 后贵 (8771) | DevFlow 后端、Gateway | Gitea (develop 分支) |
| 第十五步 | 海梅 | 海梅 (8765) | DevFlow 后端、Gateway | Gitea (main/PR) |
| 第十六步 | 海梅↔用户 | 海梅+用户 | DevFlow 后端、群聊 | 版本标签 |

**说明**：
* 每步（第一步除外）产出必须经后荣 (QA, 8772) 检验合格后方可进入下一步。
* 检验合格产出全部提交到 Gitea 代码库，提交遵循 Conventional Commits 规范。
* 前后两个任务必须分配给不同的 Agent 执行。
* 蜂群步骤（第七/九/十一）涉及多个编程 Agent 并行执行。

### 5.3 项目讨论群交互

项目讨论群是所有 9 个命名 Agent 角色实时沟通和协作的核心渠道，支持两种模式：

```
┌──────────────────────────────────────────────────────────────┐
│                    项目讨论群                                  │
│                                                              │
│  ┌────────────────── 讨论模式 ──────────────────────┐        │
│  │                                                  │        │
│  │  人类用户 ──发送──► DevFlow 后端 ──广播──► 所有Agent │        │
│  │  人类用户 ──@后兴──► DevFlow 后端 ──定向──► 后兴    │        │
│  │  后发   ──@后达──► DevFlow 后端 ──定向──► 后达    │        │
│  │                                                  │        │
│  │  消息存储: group_messages 表 (sender_id + sender_type)│        │
│  └──────────────────────────────────────────────────┘        │
│                                                              │
│  ┌────────────────── 会议模式 ──────────────────────┐        │
│  │                                                  │        │
│  │  海梅(主持人) ──► 开场定调 → 制定议程             │        │
│  │            ──► 按议程邀请成员发言                  │        │
│  │            ──► 会议总结 → 结构化纪要               │        │
│  │  产出: 纪要/决议/待办/风险/遗留问题                 │        │
│  │                                                  │        │
│  │  会议类型: 需求评审会/技术方案讨论会/每日站会/故障复盘│        │
│  └──────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

### 5.4 Agent 蜂群交互

后发（程序员）和后达（测试员）可建立编程 Agent 蜂群：

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent 蜂群交互                             │
│                                                             │
│  后发/后达 ──POST /api/swarms──► DevFlow 创建蜂群             │
│       │                                                   │
│       │  ┌── 后发建立代码编写蜂群 (第七步/第九步)          │
│       │  │   后达建立代码测试蜂群 (第十一步)               │
│       │  │                                                   │
│       │  ┌──── 蜂群Agent 启动/初始化/注册 ──────────┐      │
│       │  │ POST /api/agents/register  │               │      │
│       │  │ 加载项目上下文, 建立通信连接   │               │      │
│       │  │ 加入项目讨论群(仅接收)       │               │      │
│       │  └──────────────────────────────┘               │      │
│       │  │                                                   │
│       │  ├── GET /api/swarm/tasks/:agent_id  (获取任务)    │
│       │  ├── POST /api/swarm/tasks/:id/acknowledge (确认)   │
│       │  ├── POST /api/swarm/tasks/:id/progress (进度)      │
│       │  ├── POST /api/swarm/tasks/:id/deliver (交付)       │
│       │  └── POST /api/swarm/tasks/:id/error (错误)         │
│       │                                                   │
│       │  蜂群Agent: Claude Code / Codex / Opencode /      │
│       │  Cursor / CodeArts / Trae / Lingma /              │
│       │  hermes子agent / pi-codeing-agent子agent           │
│       │                                                   │
│       │  生命周期: 启动→初始化→执行→退出→资源清理           │
│       │  超时: 30分钟, 最多重试3次, 指数退避(30s/60s/120s)  │
│       └───────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

### 5.5 QA 门控交互

后荣 (QA) 作为质量门控，贯穿整个流程：

```
┌─────────────────────────────────────────────────────────────┐
│                    QA 门控交互                                │
│                                                             │
│  产出Agent ──提交产物──► POST /api/qa/:task_id/inspect      │
│       │                            │                        │
│       │                    ┌───────▼────────┐              │
│       │                    │  后荣(QA, 8772) │              │
│       │                    │  逐项比对验收标准│              │
│       │                    │  计算综合评分    │              │
│       │                    └───┬──────────┬──┘              │
│       │                        │          │                  │
│       │               合格(≥85分)    不合格                    │
│       │                        │          │                  │
│       │          ┌─────────────▼┐  ┌─────▼────────┐        │
│       │          │ 放行+提交代码库│  │退回重做      │        │
│       │          │ 通知海梅下一步 │  │附带修改建议  │        │
│       │          │              │  │24小时内修改   │        │
│       │          └──────────────┘  └─────┬────────┘        │
│       │                                  │                  │
│       │                    ┌─────────────▼┐                │
│       │                    │ Agent修改后  │                │
│       │                    │ 重新提交检验 │                │
│       │                    └──────────────┘                │
│       │                                                    │
│       │  检验记录保存: qa_records 表                        │
│       │  记录: 检验维度/量化标准/实际得分/合格阈值/是否达标  │
│       │  综合评分 = 各维度得分的算术平均值 (0-100)           │
└─────────────────────────────────────────────────────────────┘
```

### 5.6 代码库提交交互

```
┌─────────────────────────────────────────────────────────────┐
│                  代码库提交交互                               │
│                                                             │
│  DevFlow 后端 ──QA检验合格──► Gitea REST API                │
│       │                           │                        │
│       │  ┌── 创建仓库 (第一步)     │                        │
│       │  │   初始化基础文件        │                        │
│       │  │   设置分支保护          │                        │
│       │  │                         │                        │
│       │  ├── 提交产出 (每步)       │                        │
│       │  │   遵循 Conventional     │                        │
│       │  │   Commits 规范          │                        │
│       │  │   关联任务ID+QA记录ID   │                        │
│       │  │                         │                        │
│       │  ├── 创建 PR (第十一/十五步)│                       │
│       │  │   代码审查              │                        │
│       │  │   自动化测试            │                        │
│       │  │   审批合并              │                        │
│       │  │                         │                        │
│       │  └── 打版本标签 (第十六步) │                        │
│       │                          │                        │
│       │  Git Flow 分支策略:        │                        │
│       │  main / develop / feature/* / release/* / hotfix/* │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 通信机制

### 6.1 DevFlow 与命名 Agent 通信

DevFlow 平台通过 Hermes Gateway API 与 9 个命名 Agent 角色通信：

* **通信协议**：HTTP REST API + WebSocket + Server-Sent Events (SSE)。
* **API 端点**：各 Agent Gateway 暴露 `/v1/chat/completions` 端点（OpenAI 兼容格式）。
* **流式响应**：支持 SSE 流式输出，前端可实时显示 Agent 回复过程。
* **非流式响应**：适用于后台任务、批量操作等场景。
* **并发控制**：信号量限制最大并发请求数（默认 5）。
* **超时控制**：请求超时默认 360 秒。

**通信示例（非流式）**：

```
DevFlow ──POST http://localhost:8765/v1/chat/completions──► 海梅(Gateway)
  Body: {
    "model": "gpt-4o",
    "messages": [
      {"role": "system", "content": "你是海梅，项目经理..."},
      {"role": "user", "content": "请确认项目核心目标..."}
    ],
    "temperature": 0.7
  }
◄── 200 OK ───────────────────────────────────────────────────────
  Body: {
    "choices": [{"message": {"role": "assistant", "content": "项目核心目标为..."}}]
  }
```

**通信示例（流式 SSE）**：

```
DevFlow ──POST http://localhost:8767/v1/chat/completions?stream=true──► 后旺(Gateway)
◄── event: message_chunk
data: {"content": "架构设计..."}
◄── event: message_chunk
data: {"content": "采用微服务..."}
◄── event: message_complete
data: {"content": "...完成"}
```

### 6.2 DevFlow 与前端通信

**REST API**：

* 用于项目 CRUD、进度查询、Agent 管理、QA 操作等请求-响应模式操作。
* 认证：JWT Token，通过 Authorization 请求头传递。
* 路由前缀：`/api/`。

**WebSocket**：

* 端点：`ws://{host}/ws/group-chat`。
* 用于实时通信场景：群聊消息推送、16 步流程进展事件、Agent 状态更新、会议模式互动。
* 支持断线自动重连并恢复群组订阅。

**WebSocket 消息类型**：

| 方向 | 类型 | 描述 |
|------|------|------|
| 客户端→服务端 | subscribe | 订阅指定群组消息 |
| 客户端→服务端 | send_message | 发送群聊消息 (支持 @Agent) |
| 客户端→服务端 | start_meeting | 启动会议 |
| 服务端→客户端 | message_new | 新消息到达 |
| 服务端→客户端 | message_chunk | Agent 流式回复内容块 |
| 服务端→客户端 | message_complete | Agent 回复完成 |
| 服务端→客户端 | project.step.started | 步骤开始执行 |
| 服务端→客户端 | qa.inspection.passed | QA 检验通过 |

### 6.3 DevFlow 与蜂群 Agent 通信

蜂群 Agent 与 DevFlow 平台通过 RESTful API 进行通信：

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/swarms | 创建蜂群 (后发/后达调用) |
| GET | /api/swarms/:id | 获取蜂群详情 |
| POST | /api/swarms/:id/dispatch | 分发任务到蜂群成员 |
| GET | /api/swarms/:id/progress | 获取蜂群整体执行进度 |
| DELETE | /api/swarms/:id | 解散蜂群 |
| GET | /api/swarm/tasks/:agent_id | 蜂群 Agent 获取分配任务 |
| POST | /api/swarm/tasks/:agent_id/acknowledge | 确认接收任务 |
| POST | /api/swarm/tasks/:task_id/progress | 上报任务进度 |
| POST | /api/swarm/tasks/:task_id/deliver | 提交任务成果 |
| POST | /api/swarm/tasks/:task_id/error | 上报执行错误 |

### 6.4 DevFlow 与 Gitea 通信

* **协议**：Gitea REST API (HTTP)。
* **用途**：代码仓库创建、分支管理、PR 操作、代码提交。
* **配置**：通过配置文件指定 Gitea 地址、API Token、默认组织等。

### 6.5 DevFlow 内部异步通信

* **Celery 任务队列**：用于耗时操作的异步处理。
  * Agent 任务执行（调用 Gateway API 等待回复）。
  * QA 检验（调用后荣 Gateway 执行检验）。
  * 蜂群任务分发和监控。
  * 前端实操验证（Playwright/Selenium）。
* **Redis 作为 Broker 和 Result Backend**：Celery 任务的消息中间件和结果存储。
* **Redis 缓存**：高频读取数据的缓存（Agent 状态、项目进度、群聊消息）。

---

## 7. 性能架构

### 7.1 性能指标目标

| 指标 | 目标值 | 测试环境 | 测试方法 |
|------|--------|----------|----------|
| 页面加载时间 | < 2 秒 | Chrome 120+, 2核4GB客户端, 100M局域网 | Lighthouse Performance 评分, 3次取平均 |
| Agent 响应时间 | < 3 秒 | 同上 | curl 记录 API 响应时间, 10次请求取 P95 |
| 蜂群 Agent 任务分配响应时间 | < 500 毫秒 | 同上 | 调用 POST /api/swarms/:id/dispatch, 记录响应时间 |
| QA 检验自动化处理时间 | 单产出 < 1 分钟 | 同上 | 提交 QA 检验请求, 计时到返回结果 |
| 并发项目数 | 支持 20 个项目同时执行 | 8核16GB服务器 | JMeter 模拟 20 个项目并发, 监控 CPU/内存 |
| 数据库查询响应 | < 100 毫秒 | PostgreSQL 14, 4核8GB | pg_stat_statements 监控慢查询 |
| 群聊消息延迟 | < 100ms (局域网内) | 100M局域网, 2台机器 | WebSocket 端到端计时, 100条消息取 P95 |

### 7.2 性能优化策略

#### 7.2.1 异步并发

* **FastAPI 异步路由**：前端请求、WebSocket 处理使用 asyncio 异步处理。
* **Celery 异步任务**：Agent 任务执行、QA 检验、蜂群调度等耗时操作通过 Celery Worker 异步执行，不阻塞 API 响应。
* **信号量并发控制**：Gateway Client 通过信号量限制最大并发请求数（默认 5），避免过载。

#### 7.2.2 缓存策略

* **Redis 缓存**：
  * Agent 在线状态（TTL 30 秒）。
  * 项目进度信息（TTL 60 秒）。
  * 群聊最近消息（TTL 300 秒）。
  * 蜂群 Agent 技能注册信息（不设置 TTL，变更时主动更新）。
* **数据库查询优化**：
  * 常用查询建立索引（project_id、agent_id、group_id）。
  * 慢查询通过 pg_stat_statements 监控和优化。
  * 大结果集分页返回。

#### 7.2.3 数据库性能

* **连接池**：SQLAlchemy 连接池，最大连接数根据服务器资源配置。
* **读写分离**：未来可选配置 PostgreSQL 主从复制，读操作走从库。
* **数据分区**：群聊消息表按项目 ID 分区，提高查询效率。
* **备份不影响性能**：备份在低峰期执行（每日凌晨 2:00-4:00）。

#### 7.2.4 并发与资源隔离

* **项目级隔离**：每个项目的 Agent 执行在独立会话空间运行，数据、文件、临时目录互不干扰。
* **Agent 并发限制**：同一 Agent Profile 同一时间只能执行一个项目的任务（避免上下文冲突）。
* **蜂群 Agent 隔离**：不同项目的蜂群 Agent 使用独立临时工作目录（`/tmp/devflow/{project_id}/`）。
* **并发上限**：系统同时支持最多 20 个项目执行，超出队列等待。
* **调度策略**：按项目创建时间 FIFO 调度，紧急项目可提升优先级。

#### 7.2.5 容错与重试

* **Agent 执行失败重试**：最多 3 次重试，指数退避间隔（30s / 60s / 120s）。
* **超时机制**：Agent 执行超时阈值 30 分钟，超时后自动终止并触发重试或备用 Agent 切换。
* **备用 Agent 选择策略**：
  1. 优先选择同类型且当前负载最低的 Agent。
  2. 若无同类型 Agent，选择技能匹配度 >= 80% 的其他 Agent。
  3. 若无可用的备用 Agent，海梅通知人类用户并暂停该任务。
* **WebSocket 断线重连**：客户端 WebSocket 断线后可自动重连并恢复群组订阅。

### 7.3 可观测性架构

#### 7.3.1 指标采集 (Metrics)

* **存储**：Prometheus 时序数据库，保留 30 天。
* **采集间隔**：系统级 30 秒，应用级 10 秒，Agent 级 30 秒，业务级实时。
* **采集内容**：

| 级别 | 指标 |
|------|------|
| 系统级 | CPU 使用率、内存使用率、磁盘 IO、网络带宽 |
| 应用级 | API 响应时间 P50/P95/P99、QPS、错误率、活跃连接数 |
| Agent 级 | 任务执行时长、任务成功率、Agent 负载、蜂群 Agent 活跃度 |
| 业务级 | 项目数、活跃项目数、QA 检验通过率、各步骤平均耗时 |

#### 7.3.2 链路追踪 (Tracing)

* **标准**：OpenTelemetry。
* **存储**：Jaeger 后端，保留 7 天。
* **追踪范围**：从海梅分派任务开始，经过蜂群 Agent 执行、QA 检验、代码提交的全链路。
* **Trace ID**：每个 Agent 任务分配唯一 Trace ID，贯穿整个执行链。

#### 7.3.3 日志管理 (Logging)

* **格式**：JSON 结构化日志，包含 timestamp、level、service、trace_id、message、context。
* **级别**：DEBUG / INFO / WARN / ERROR / FATAL。
* **存储**：本地文件（按天轮转，保留 30 天）+ ELK Stack 集中管理（保留 90 天）。
* **关键日志**：Agent 任务分派、QA 检验结果、代码提交、错误和异常。

#### 7.3.4 告警规则

| 级别 | 告警条件 | 通知方式 |
|------|----------|----------|
| 系统级 | CPU > 85% 持续 5 分钟、内存 > 90% 持续 3 分钟、磁盘 > 80% | 平台内通知 + 邮件 |
| 应用级 | API 错误率 > 5%、P95 响应时间 > 5 秒、连续 10 个 Agent 任务失败 | 平台内通知 + 邮件 |
| Agent 级 | Agent 进程宕机、连续 3 次重试失败、单个任务执行超过 30 分钟 | 平台内通知 + 邮件 |

* **告警升级**：首次告警通知系统管理员，30 分钟内未处理则通知项目人类用户。

### 7.4 容灾与备份

* **RTO（恢复时间目标）**：系统故障后 2 小时内恢复服务。
* **RPO（恢复点目标）**：数据丢失不超过最后一小时内。
* **备份策略**：

| 数据 | 全量备份 | 增量备份 |
|------|----------|----------|
| PostgreSQL 数据库 | 每日凌晨 2:00 | 每 6 小时 |
| 文件存储 | 每日凌晨 3:00 | - |
| Gitea 仓库 | 每日凌晨 4:00 归档 | Git 历史即版本备份 |

* **备份保留周期**：每日 30 天、每周 90 天、每月 365 天。
* **恢复演练**：每季度一次完整恢复演练。

---

## 8. 数据架构

### 8.1 数据库设计

DevFlow 使用 PostgreSQL 作为主数据库，核心表结构如下：

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| users | 人类用户 | id, username, email, role, created_at |
| projects | 项目 | id, name, description, creator_id, status, current_step(1-16) |
| requirements | 需求 | id, project_id, content, version, is_locked |
| agents | Agent 角色 | id, name, agent_type(named/swarm), role_name, status, api_endpoint |
| tasks | 任务 | id, project_id, assignee_agent_id, status, step_number(1-16), is_atomic |
| task_dependencies | 任务依赖 | id, source_task_id, target_task_id |
| agent_execution_logs | Agent 执行日志 | id, task_id, agent_id, execution_content, result |
| qa_records | QA 检验记录 | id, task_id, reviewer_agent_id, acceptance_result, score(0-100) |
| groups | 群组 (项目讨论群) | id, project_id, name, mode, host_agent_id |
| group_members | 群组-成员关联 | id, group_id, user_id, agent_id, member_type(user/agent) |
| group_messages | 群聊消息 | id, group_id, sender_id, sender_type(user/agent), content |
| meeting_outcomes | 会议结果 | id, group_id, meeting_topic, minutes, decisions, todos, risks |
| swarms | Agent 蜂群 | id, project_id, manager_agent_id, purpose, status |
| swarm_members | 蜂群-成员关联 | id, swarm_id, agent_name, agent_type |
| notifications | 通知 | id, user_id, project_id, content, type, is_read |
| repos | 代码仓库 | id, project_id, gitea_repo_id, name, url, default_branch |
| repo_branches | 分支 | id, repo_id, name, commit_sha, is_protected |
| pull_requests | PR | id, repo_id, number, source_branch, target_branch, status |
| commits | 提交记录 | id, repo_id, sha, message, author |
| task_commits | 任务-提交关联 | id, task_id, commit_id |

### 8.2 数据流

```
人类用户 ──► DevFlow 后端 ──► PostgreSQL (持久化)
              │                    │
              │ 缓存/状态/队列 ──► Redis
              │                    │
              │ Gateway API ──► 命名Agent (产生对话/任务执行内容)
              │                    │
              │ Gitea REST API ──► Gitea (代码/文档持久化)
              │                    │
              │ Celery ──► Celery Workers (异步任务执行)
              │                    │
              │ OpenTelemetry ──► Prometheus/Jaeger (可观测性数据)
```

### 8.3 项目文件夹结构

项目创建后自动生成标准目录结构：

```
/DevFlow/projects/{project_id}/
├── docs/          # 文档 (需求说明书、设计文档、项目文档)
├── src/           # 源代码 (功能代码)
├── tests/         # 测试用例 (TDD 测试用例)
├── configs/       # 配置文件 (环境配置、部署配置)
├── reports/       # 报告 (测试报告、安全审计报告、交付报告)
└── logs/          # 日志
```

---

## 9. 安全架构

### 9.1 认证与授权

* **用户认证**：JWT Token 认证。
* **授权控制**：基于角色的访问控制 (RBAC)，人类用户仅可查看/操作自身发起的项目。
* **Agent 通信**：Gateway API 通过端口隔离实现，DevFlow 内部调用，不对外暴露。

### 9.2 数据安全

* **传输加密**：HTTPS 传输加密。
* **数据存储**：Agent 交互数据脱敏存储。
* **成果安全**：项目代码/成果仅对人类用户和授权 Agent 可见。
* **日志审计**：记录所有 Agent 交互、任务分配、QA 检验操作日志。

### 9.3 安全审计

后华 (安全员) 负责 16 步流程第十二步的安全审计：

* **代码审计**：代码安全漏洞扫描。
* **合规审查**：是否符合行业规范和法规要求。
* **渗透测试**：范围 OWASP Top 10 全部类别，深度中等（自动化扫描 + 关键路径人工验证）。
* **漏洞修复**：高危漏洞 24 小时内修复、中危 72 小时内修复、低危下个迭代修复。

---

## 10. 扩展架构

### 10.1 水平扩展

* **Celery Workers 水平扩展**：通过增加 Celery Worker 容器实例提高异步任务处理能力。
* **Gitea 集群**：未来可迁移 Gitea 到集群部署以支持大规模代码托管。
* **PostgreSQL 读写分离**：主从复制，读操作走从库，写操作走主库。

### 10.2 垂直扩展

* **Agent 类型扩展**：API 设计遵循 RESTful 规范，支持新增编程 Agent 类型的快速接入。
* **任务拆解规则**：支持配置化扩展，适配不同开发流程。
* **验收标准**：支持自定义扩展，适配不同技术栈/行业规范。
* **前端组件化**：支持功能模块快速迭代。
* **群组容量**：单个群组支持至少 10 个 Agent 同时在线。

### 10.3 国际化

* **支持语言**：简体中文（默认）、English（英文）。
* **前端**：Vue I18n 实现多语言切换。
* **后端**：API 响应通过 Accept-Language 请求头自动切换。
* **Agent 交互**：命名 Agent 角色支持中英文双语交互。

### 10.4 无障碍访问

* **标准**：WCAG 2.1 Level AA。
* **键盘导航**：所有交互元素支持 Tab 导航、Enter/Space 激活。
* **屏幕阅读器**：alt 文本、ARIA 标签、label 关联。
* **颜色对比度**：>= 4.5:1（正常文字）、>= 3:1（大文字）。
* **字体缩放**：支持 200% 缩放不破坏布局。

---

## 11. 版本升级与数据迁移

### 11.1 版本管理

* **语义化版本**：MAJOR.MINOR.PATCH（如 1.2.3）。
* **兼容性**：MINOR 版本保证 API 向后兼容，MAJOR 版本可能引入不兼容变更。

### 11.2 升级流程

1. 发布升级公告（含变更说明和兼容性提醒）。
2. 用户备份数据。
3. 执行 Docker 镜像更新（`docker pull` + `docker-compose up -d`）。
4. 自动执行数据库迁移脚本。
5. 运行健康检查验证升级成功。
6. 若健康检查失败，自动回滚到上一版本。

### 11.3 数据迁移

* **工具**：Python + SQLAlchemy Alembic，支持正向迁移和回滚。
* **流程**：备份 → 测试环境验证 → 生产环境执行 → 验证数据完整性 → 保留旧数据 7 天。
* **日志**：每次迁移记录迁移 ID、执行时间、执行结果、影响数据量。

---

## 12. 附录

### 12.1 端口总览

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| Nginx | 80 / 443 | HTTP/HTTPS | 反向代理入口 |
| DevFlow 后端 | 8000 | HTTP | FastAPI 后端 |
| PostgreSQL | 5432 | TCP | 主数据库 |
| Redis | 6379 | TCP | 缓存/消息队列 |
| Gitea | 3000 | HTTP | 代码托管 Web 界面 |
| Gitea SSH | 222 | SSH | 代码托管 SSH |
| 海梅 (HaiMei) | 8765 | HTTP/WS | Gateway |
| 后兴 (HouXing) | 8766 | HTTP/WS | Gateway |
| 后旺 (HouWang) | 8767 | HTTP/WS | Gateway |
| 后发 (HouFa) | 8768 | HTTP/WS | Gateway |
| 后达 (HouDa) | 8769 | HTTP/WS | Gateway |
| 后富 (HouFu) | 8770 | HTTP/WS | Gateway |
| 后贵 (HouGui) | 8771 | HTTP/WS | Gateway |
| 后荣 (HouRong) | 8772 | HTTP/WS | Gateway |
| 后华 (HouHua) | 8773 | HTTP/WS | Gateway |
| Prometheus | 9090 | HTTP | 指标采集 |
| Jaeger | 16686 | HTTP | 链路追踪 UI |
| Kibana | 5601 | HTTP | 日志管理 UI |

### 12.2 16 步标准流程概要

| 步骤 | 执行者 | 核心产出 | QA 门控 |
|------|--------|----------|---------|
| 1 | 人类用户 | 项目创建 + 代码仓库 | 无需 QA |
| 2 | 海梅 | 核心目标 + 组织架构 + 讨论群 | 后荣检验 |
| 3 | 后兴 | 软件需求说明书 | 后荣检验 |
| 4 | 后旺 | 架构/后端/前端/数据库设计文档 | 后荣逐项检验 |
| 5 | 后富 | 开发环境 | 后荣检验 |
| 6 | 海梅 | TDD 测试用例编写计划 | 后荣检验 |
| 7 | 后发 (蜂群) | TDD 测试用例代码 | 后荣逐用例检验 |
| 8 | 海梅 | 代码编写计划 (含依赖图) | 后荣检验 |
| 9 | 后发 (蜂群) | 功能代码 | 后荣逐任务检验 |
| 10 | 后富 | 测试环境部署 | 后荣检验 |
| 11 | 后达 (蜂群) | 全部测试报告 | 后荣检验 |
| 12 | 后华 | 安全审计报告 | 后荣检验 |
| 13 | 后富 | 生产环境部署 | 后荣检验 |
| 14 | 后贵 | 项目文档集 | 后荣检验 |
| 15 | 海梅 | 项目交付报告 | - |
| 16 | 海梅 + 用户 | 满意度确认 / 迭代修改 | - |

### 12.3 参考文献

* SRS 文档：`/home/jim/DevFlow/projects/devflow/docs/devflow_SRS_V6.md`
* Hermes Agent: https://github.com/NousResearch/hermes-agent
* Hermes Agent 文档: https://hermes-agent.nousresearch.com/docs

---

文档结束
