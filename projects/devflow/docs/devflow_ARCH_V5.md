# DevFlow 项目管理平台 - 架构设计文档

**版本**: V5
**日期**: 2026-06-15
**作者**: HouWang (后旺)
**状态**: 修订版V5（修复V4审查不合格项）

---

## 1. 系统整体架构

### 1.1 架构概述

DevFlow 是一个 AI Agent 全自动软件开发项目管理平台，采用分层架构设计，支持9个命名 Agent 角色协同工作，通过16步标准流程实现从需求分析到部署交付的全自动化软件开发。

### 1.2 整体架构图

```
┌───────────────────────────────────────────────────────────────────────┐
│                        人类用户 (Client)                                │
│           浏览器 / 移动端 (需求提交/进度查看/群组聊天/会议参与)            │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │ HTTP / WebSocket
┌───────────────────────────────────▼───────────────────────────────────┐
│                            Nginx (反向代理)                             │
│                                                                    │
│  职责：                                                              │
│  - SSL/TLS 终止                                                     │
│  - 静态资源缓存                                                     │
│  - WebSocket 代理                                                   │
│  - 请求限流                                                         │
│  - Gitea子路径代理 (/gitea/)                                        │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────┐
│                      FastAPI 后端 (DevFlow Server)                     │
│  ┌──────────┬─────────────┬────────────┬───────────────────┐         │
│  │ 16步流程  │ Agent蜂群   │ QA门控     │ 项目讨论群        │         │
│  │ 调度引擎  │ 调度管理    │ 检验引擎   │ 管理/会议模式     │         │
│  └──────────┴─────────────┴────────────┴───────────────────┘         │
│  ┌──────────┬─────────────┬────────────┬───────────────────┐         │
│  │ Profile  │ Gateway     │ 代码库     │ 通知管理          │         │
│  │ 扫描同步  │ Client      │ Gitea集成  │ (WebSocket推送)   │         │
│  └──────────┴─────────────┴────────────┴───────────────────┘         │
│                                    │                                  │
└────────────────────────────────────┼──────────────────────────────────┘
               Gitea REST API        │                      │ Gateway API
┌──────────────────────────────────▼───┐                  │ POST /v1/chat/completions
│       Gitea 代码托管层 (本地部署)     │                  │ (支持流式SSE)
│  代码仓库管理 / Git Flow / PR审核     │                  │
│  统一成果存储：检验合格即刻提交        │                  │
└──────────────────────────────────────┘                  │
                                                          │
┌─────────────────────────────────────────────────────────▼───────────┐
│              9个独立Agent容器 (Hermes Profiles)                        │
│  每个Agent运行在独立Docker容器中，进程隔离，故障互不影响                │
│  容器入口进程: Hermes Gateway 服务 (端口 8765-8773)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │Herme-HM  │  │Hermes-HX │  │Hermes-HW │  │Hermes-HF │           │
│  │ 海梅:8765│  │ 后兴:8766│  │ 后旺:8767│  │ 后发:8768│           │
│  │ 项目经理 │  │ 需求分析 │  │ 架构设计 │  │ 程序员   │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │Hermes-HD │  │Hermes-HFU│  │Hermes-HG │  │Hermes-HR │           │
│  │ 后达:8769│  │ 后富:8770│  │ 后贵:8771│  │ 后荣:8772│           │
│  │ 测试员   │  │ CI/CD    │  │ 文档管理 │  │ QA(门控) │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐                                                       │
│  │Hermes-HH │                                                       │
│  │ 后华:8773│                                                       │
│  │ 安全员   │                                                       │
│  └──────────┘                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  项目讨论群: 所有Agent实时在线沟通 (讨论模式+会议模式)        │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                          Agent蜂群层 (外部AI编程工具)                    │
│  说明: 以下工具不是独立服务层,而是作为子进程运行在Hermes Agent容器内      │
│  (主要由"后发"程序员Agent按需调用,也可被其他Agent调用)                     │
│  子进程管理: 由命名Agent容器内的进程管理器通过subprocess.Popen创建,       │
│  包含SIGCHLD信号处理和僵尸进程回收机制                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │Claude   │ │ Codex   │ │Opencode │ │ Cursor  │ │CodeArts │      │
│  │Code     │ │         │ │         │ │         │ │         │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│  ┌─────────┐ ┌─────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │ Trae    │ │ Lingma  │ │hermes子agent    │ │pi-codeing-agent │  │
│  │         │ │         │ │                 │ │子agent          │  │
│  └─────────┘ └─────────┘ └─────────────────┘ └─────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                       数据库层 (PostgreSQL)                            │
│  ┌───────────┬───────────┬──────────────┬───────────┬───────────┐   │
│  │ users     │ projects  │ requirements │ agents    │ tasks     │   │
│  └───────────┴───────────┴──────────────┴───────────┴───────────┘   │
│  ┌───────────┬───────────┬──────────────┬───────────┬───────────┐   │
│  │ groups    │ g_members │ group_messages│meeting_   │ qa_records│   │
│  │           │  (关联)   │(含msg_type)  │outcomes   │           │   │
│  └───────────┴───────────┴──────────────┴───────────┴───────────┘   │
│  ┌───────────┬───────────┬──────────────┬───────────┬───────────┐   │
│  │ repos     │ branches  │ pull_requests│ commits   │task_commits│  │
│  └───────────┴───────────┴──────────────┴───────────┴───────────┘   │
│  ┌──────────────────┬──────────────────┬───────────┬───────────────┬───────────────┐   │
│  │task_dependencies │agent_exec_logs  │  swarms   │swarm_members  │notifications  │   │
│  └──────────────────┴──────────────────┴───────────┴───────────────┴───────────────┘   │
│                                                                      │
│  说明:                                                               │
│  - group_msg表含msg_type字段区分: system/agent/user消息类型           │
│  - meeting_outcomes表存储会议决策结果，写回流程调度引擎                     │
│  - task_commits为任务-提交关联表(非Gitea缓存)                         │
│  - Gitea数据通过REST API实时获取，仅commits/PRs作为审计缓存           │
│  - task_dependencies表存储任务间依赖关系                              │
│  - agent_exec_logs表记录Agent执行日志与结果                           │
│  - swarms/swarm_members表管理蜂群Agent分组与成员                      │
│  - notifications表存储系统通知与推送记录                              │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 2. 分层架构设计

### 2.1 表现层 (Presentation Layer)

**职责**: 用户界面渲染、用户交互处理、实时通信

**技术栈**:
- Vue 3 (Composition API)
- Element Plus (UI 组件库)
- Vue Router 4 (路由管理)
- Pinia (状态管理)
- WebSocket Client (实时通信)
- Vue I18n (国际化)

**核心组件**:
- 项目管理仪表盘
- 16步流程可视化面板
- 项目讨论群聊天界面
- Agent 状态监控面板
- 会议模式控制面板

**国际化/无障碍支持**:
- **国际化架构**: 语言包存储于 `src/locales/` 目录，支持多语言切换；切换机制基于前端 `localStorage` 持久化用户语言偏好，HTTP 请求通过 `Accept-Language` 头传递语言信息；后端根据语言标识返回对应多语言响应内容。
- **无障碍架构**: 遵循 WCAG 2.1 Level AA 标准；完整键盘导航支持；屏幕阅读器兼容；所有交互元素使用 ARIA 标签；色彩对比度 >= 4.5:1。

### 2.2 应用层 (Application Layer)

**职责**: 业务逻辑处理、流程调度、Agent 协调

**技术栈**:
- Python FastAPI (REST API + WebSocket)
- asyncio + ARQ (Agent任务异步队列 - 长时间运行、进度追踪)
- Celery (离线批处理任务 - 定时报表生成、数据导出)
- Pydantic (数据验证)
- SQLAlchemy (ORM)

**职责分工说明**:
- **asyncio + ARQ**: 负责 Agent 任务调度（长时间运行、需要进度追踪的任务），避免引入额外的消息代理依赖，FastAPI 原生支持 asyncio。ARQ 运行在独立的 ARQ worker 容器中，通过 Redis 队列与 FastAPI 通信，完全隔离事件循环。
- **Celery**: 仅用于离线批处理任务（如定时报表生成、数据导出、定时清理等），不承担 Agent 调度职责。Celery 使用独立的同步 worker 进程模型。
- **分离理由**: 两类任务特性差异大——Agent 任务需要实时进度反馈、支持取消、可能持续数十分钟；批处理任务是即发即忘的一次性任务。分开管理避免任务优先级互相影响，也便于独立监控和扩缩容。
- **技术变更依据**: ARQ 原生支持 asyncio 与 FastAPI 集成，无需额外消息代理（Redis 仅作为队列存储）；支持任务进度回调、取消、超时控制等高级特性，完美适配 Agent 任务的交互式执行需求。**影响评估**: ARQ 与 Celery 共享同一 Redis 实例但不互相影响（使用不同的队列命名空间）；ARQ 负责 Agent 任务调度，Celery 负责离线批处理任务，职责清晰分离。

**核心服务**:
- 16步流程调度引擎
- Agent 蜂群调度管理器
- QA 门控检验引擎
- 项目讨论群管理器
- Profile 扫描同步服务

### 2.3 数据访问层 (Data Access Layer)

**职责**: 数据持久化、缓存管理、事务控制

**技术栈**:
- PostgreSQL 14+ (主数据库)
- Redis 6+ (缓存/状态存储/消息队列)
- SQLAlchemy ORM (对象关系映射)
- Alembic (数据库迁移)

**数据模型**:
- 用户数据
- 项目数据
- 任务数据
- Agent 数据
- 群组消息数据
- QA 检验记录
- 代码仓库数据

### 2.4 基础设施层 (Infrastructure Layer)

**职责**: 外部服务集成、消息队列、文件存储

**技术栈**:
- Gitea (代码托管服务)
- Hermes Gateway API (Agent 通信)
- Docker + Docker Compose (容器化部署)
- Nginx (反向代理)
- Prometheus + Grafana (监控)

---

## 3. 模块划分

### 3.1 核心业务模块

#### 3.1.1 16步流程调度引擎

**职责**: 管理16步标准流程的执行、状态转换、任务分配

**子模块**:
- StepScheduler: 步骤调度器，控制流程步骤的顺序执行
- TaskDispatcher: 任务分发器，将任务分配给对应的 Agent
- StateManager: 状态管理器，维护项目和任务的状态
- DependencyResolver: 依赖解析器，处理任务依赖关系

#### 3.1.2 Agent 蜂群调度管理器

**职责**: 管理 Agent 蜂群的创建、任务分发、进度监控、成果收集

**子模块**:
- SwarmCreator: 蜂群创建器
- TaskLoadBalancer: 任务负载均衡器
- ProgressMonitor: 进度监控器
- ResultCollector: 成果收集器

#### 3.1.3 QA 门控检验引擎

**职责**: 执行 QA 检验、评估产出质量、决定是否放行

**子模块**:
- InspectionEngine: 检验引擎，执行各项检验标准
- ScoringCalculator: 评分计算器，计算量化评分
- ReportGenerator: 报告生成器，生成检验报告
- RollbackHandler: 回退处理器，处理不合格产出的回退

**错误恢复机制**:
- **超时处理**: 每步 Agent 执行超时默认 30 分钟，超时后标记为 failed 并触发重试
- **重试策略**: 最多重试 3 次，采用指数退避（首次 30 秒、第二次 60 秒、第三次 120 秒）
- **中间产物清理**: 第 N 步回退到第 M 步时，清理步骤 M+1 到 N 产出的代码分支、文档文件、数据库临时记录，通过 Git 分支删除和文件系统的清理脚本实现
- **补偿事务**: 使用数据库事务确保状态回滚的原子性，回滚失败时记录错误日志并告警

#### 3.1.4 项目讨论群管理器

**职责**: 管理项目讨论群的创建、消息收发、会议模式

**子模块**:
- GroupManager: 群组管理器
- MessageBroker: 消息代理，处理消息的发送和接收
- MeetingController: 会议控制器，管理会议模式
- NotificationService: 通知服务

**消息与流程集成**:
- **消息类型分类**: system (系统通知)、agent (Agent 对话)、user (人类用户消息)
- **讨论模式**: Agent 被动响应，仅在被 @提及或收到直接消息时回复
- **会议模式**: Agent 主动发言，按议程轮流发表意见
- **消息到状态机映射**: 会议模式产生的决策结果 (decisions JSON) 写回流程调度引擎，通过 `/api/v1/projects/:id/steps/execute` 接口更新项目状态
- **会议结果存储**: meeting_outcomes 表存储决策、待办、风险、开放问题
- **幂等性设计**: `/api/v1/projects/:id/steps/execute` 接口接收 `idempotency_key` 参数（值为 meeting_outcome.id 或 UUID），后端通过数据库唯一约束防止重复提交。同一 idempotency_key 的重复请求直接返回上次处理结果，不重复执行状态更新逻辑，确保多 Agent 并发场景下的数据一致性
- **会议决策与状态机冲突解决机制**: 会议决策写回流程引擎时，DependencyResolver 会校验该决策是否与当前步骤的依赖关系冲突（如会议决定跳过某步骤，但后续步骤依赖该步骤的产出）。冲突处理逻辑：(1) 若跳过步骤无后续依赖，直接标记该步骤为 skipped 并继续流程；(2) 若跳过步骤存在依赖，决策标记为 pending 状态，系统自动生成补偿方案（如由其他步骤产出差量数据），通知项目负责人确认；(3) 若人工确认不可跳过，会议决策回滚，原流程继续执行。所有冲突记录到 agent_execution_logs 表供审计。

### 3.2 支撑模块

#### 3.2.1 代码库管理模块

**职责**: 管理 Gitea 代码仓库、分支、PR、提交

**子模块**:
- RepoManager: 仓库管理器
- BranchManager: 分支管理器
- PRManager: PR 管理器
- CommitValidator: 提交验证器

#### 3.2.2 Hermes Agent 管理模块

**职责**: 管理 Hermes Agent 的安装、Profile 同步、Gateway 通信

**子模块**:
- ProfileScanner: Profile 同步器。在系统启动时和按需触发时，扫描 HERMES_PROFILES_PATH 目录下的 Profile 配置文件，将发现的 Agent 信息注册到数据库中。注意：这不是运行时的动态发现机制，而是部署时的初始化同步——9个命名 Agent 在 Docker 容器中是预定义的，ProfileScanner 的作用是将文件系统上的 Profile 配置与数据库中的 Agent 记录保持一致。
- GatewayClient: Gateway 客户端
- HealthMonitor: 健康监控器
- SyncService: 同步服务

#### 3.2.3 通知与交付模块

**职责**: 发送项目进度通知、完成通知

**子模块**:
- ProgressNotifier: 进度通知器
- CompletionNotifier: 完成通知器
- WebSocketPusher: WebSocket 推送器

---

## 4. 技术栈选型

### 4.1 前端技术栈

| 组件 | 技术选型 | 版本 | 选择理由 |
|------|----------|------|----------|
| 框架 | Vue 3 | 3.x | 组合式 API、性能优异、生态丰富 |
| UI 库 | Element Plus | 2.x | 完善的组件库、中文支持好 |
| 路由 | Vue Router | 4.x | Vue 官方路由、功能强大 |
| 状态管理 | Pinia | 2.x | 轻量、TypeScript 支持好 |
| HTTP 客户端 | Axios | 1.x | 功能完善、拦截器支持 |
| WebSocket | native WebSocket | - | 原生支持、无需额外依赖 |
| 国际化 | Vue I18n | 9.x | Vue 官方国际化方案 |
| 构建工具 | Vite | 5.x | 快速构建、热更新 |
| 图表 | ECharts | 5.x | 按需引入、丰富的图表类型、性能好 |

### 4.2 后端技术栈

| 组件 | 技术选型 | 版本 | 选择理由 |
|------|----------|------|----------|
| 框架 | FastAPI | 0.100+ | 高性能、自动文档、类型安全 |
| 异步框架 | asyncio | 3.10+ | 原生异步支持、高并发 |
| Agent任务队列 | ARQ | 0.23+ | asyncio 原生队列、进度追踪 |
| ORM | SQLAlchemy | 2.x | 成熟稳定、功能强大 |
| 批处理队列 | Celery | 5.x | 离线批处理、成熟生态 |
| 消息代理 | Redis | 6.x | 高性能、支持多种数据结构 |
| 数据验证 | Pydantic | 2.x | 类型安全、自动验证 |
| 数据库驱动 | asyncpg | 0.28+ | 异步 PostgreSQL 驱动 |
| WebSocket | FastAPI WebSocket | - | 原生 WebSocket 支持 |

### 4.3 数据库技术栈

| 组件 | 技术选型 | 版本 | 选择理由 |
|------|----------|------|----------|
| 主数据库 | PostgreSQL | 14+ | 功能强大、JSON 支持、事务完整 |
| 缓存/消息队列 | Redis | 6+ | 高性能、支持多种数据结构 |
| ORM 迁移 | Alembic | 1.x | SQLAlchemy 官方迁移工具 |

### 4.4 基础设施技术栈

| 组件 | 技术选型 | 版本 | 选择理由 |
|------|----------|------|----------|
| 容器化 | Docker | 20+ | 标准化容器、跨平台 |
| 容器编排 | Docker Compose | 2.x | 简单部署、多容器管理 |
| 反向代理 | Nginx | 1.x | 高性能、配置灵活 |
| 代码托管 | Gitea | 1.x | 轻量级、自托管、Git 完整支持 |
| 监控 | Prometheus + Grafana | 2.x/9.x | 时序指标采集 + 可视化，Grafana Loki 日志 |

---

## 5. 部署架构

### 5.1 部署拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                        生产环境部署                           │
│                                                             │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐          │
│  │   Nginx   │───▶│  FastAPI  │───▶│ PostgreSQL│          │
│  │  (反向代理)│    │  (应用服务)│    │  (主数据库)│          │
│  └───────────┘    └───────────┘    └───────────┘          │
│       │                │                                       │
│       │                │                                       │
│       │                ▼                                       │
│       │          ┌───────────┐    ┌───────────┐          │
│       │          │   Redis   │    │   Gitea   │          │
│       │          │ (缓存/队列)│    │ (代码托管) │          │
│       │          └───────────┘    └───────────┘          │
│       │                │                                       │
│       │                ▼                                       │
│       │     ┌─────────────────────────────┐                  │
│       │     │    ARQ Worker 容器           │                  │
│       │     │  (独立事件循环, Agent任务调度) │                  │
│       │     └─────────────────────────────┘                  │
│       │                │                                       │
│       │                ▼                                       │
│       │     ┌─────────────────────────────┐                  │
│       │     │    9个独立Hermes Agent容器    │                  │
│       │     │  (hermes-haimei ~ hermes-houhua) │              │
│       │     │  端口: 8765-8773              │                  │
│       │     └─────────────────────────────┘                  │
│       │                                                       │
│       ▼                                                       │
│  ┌───────────┐                                               │
│  │   用户    │                                               │
│  │  (浏览器)  │                                               │
│  └───────────┘                                               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 容器化部署配置

**Docker Compose 服务**:
- web: Nginx 反向代理
- api: FastAPI 应用服务 (REST API + WebSocket, 不运行 ARQ worker)
- arq-worker: ARQ 异步 worker (独立容器, 与 FastAPI 事件循环完全隔离, 负责 Agent 任务异步调度)
- worker: Celery 异步任务 worker (仅离线批处理: 定时报表、数据导出、定时清理)
- db: PostgreSQL 数据库
- redis: Redis 缓存/消息队列 (同时作为 ARQ 和 Celery 的消息代理)
- gitea: Gitea 代码托管服务
- prometheus: Prometheus 监控
- grafana: Grafana 可视化 + Loki 日志查询
- hermes-haimei: 海梅 Agent 容器
- hermes-houxing: 后兴 Agent 容器
- hermes-houwang: 后旺 Agent 容器
- hermes-houfa: 后发 Agent 容器
- hermes-houbada: 后达 Agent 容器
- hermes-houfu: 后富 Agent 容器
- hermes-hougui: 后贵 Agent 容器
- hermes-hourong: 后荣 Agent 容器
- hermes-houhua: 后华 Agent 容器

**ARQ Worker 部署说明**: ARQ worker 运行在独立的 `arq-worker` 容器中，与 FastAPI 事件循环完全隔离，通过 Redis 队列接收 Agent 任务。FastAPI 容器仅负责 HTTP 请求处理和 WebSocket 连接，不执行 Agent 任务。ARQ worker 容器通过 Redis 读取任务队列，执行完成后将结果写回 Redis 或数据库。这种架构避免了长时间运行的 Agent 任务阻塞 HTTP 请求处理（含 WebSocket 心跳、进度轮询），保证了 API 响应延迟的稳定。

**ARQ 与 FastAPI 隔离事件循环设计**:
- FastAPI 容器：处理 REST API 请求、WebSocket 连接、健康检查，事件循环仅用于 I/O 密集型操作
- ARQ worker 容器：独立 asyncio 事件循环，通过 Redis 队列接收任务，最大并发数限制为 5
- 通信机制：FastAPI 将 Agent 任务提交到 Redis 队列，ARQ worker 消费并执行，执行进度通过 Redis Pub/Sub 或数据库状态字段回调给 FastAPI，FastAPI 再通过 WebSocket 推送给前端
- Celery worker 独立容器：使用同步 worker 模型，与 ARQ 的 asyncio 模型互补

### 5.3 端口分配

| 服务 | 端口 | 协议 | 用途 |
|------|------|------|------|
| Nginx | 80/443 | HTTP/HTTPS | 反向代理 |
| FastAPI | 8000 | HTTP | 应用 API |
| ARQ Worker | 无外部端口 | Redis | 通过 Redis 队列通信 |
| PostgreSQL | 5432 | TCP | 数据库 |
| Redis | 6379 | TCP | 缓存/队列 |
| Gitea | 3000 | HTTP | 代码托管 (内部端口) |
| Gitea SSH | 222 | SSH | Git SSH |
| Prometheus | 9090 | HTTP | 监控 |
| Grafana | 3001 | HTTP | 可视化 |
| Hermes-haimei | 8765 | HTTP/WS | 海梅 Agent |
| Hermes-houxing | 8766 | HTTP/WS | 后兴 Agent |
| Hermes-houwang | 8767 | HTTP/WS | 后旺 Agent |
| Hermes-houfa | 8768 | HTTP/WS | 后发 Agent |
| Hermes-houbada | 8769 | HTTP/WS | 后达 Agent |
| Hermes-houfu | 8770 | HTTP/WS | 后富 Agent |
| Hermes-hougui | 8771 | HTTP/WS | 后贵 Agent |
| Hermes-hourong | 8772 | HTTP/WS | 后荣 Agent |
| Hermes-houhua | 8773 | HTTP/WS | 后华 Agent |

**端口说明**:
- Gitea HTTP 3000 端口通过 Nginx 子路径 `/gitea/` 反向代理暴露，不直接暴露到外网
- Hermes Agent 端口 8765-8773 对应 9 个独立 Agent 容器，每个容器运行一个 Hermes Gateway 服务
- ARQ Worker 容器不暴露外部端口，通过内部 Redis 队列与 FastAPI 通信

### 5.4 环境配置

**环境变量**:
- DATABASE_URL: PostgreSQL 连接字符串
- REDIS_URL: Redis 连接字符串
- GITEA_API_URL: Gitea API 地址
- GITEA_API_TOKEN: Gitea API Token
- HERMES_PROFILES_PATH: Hermes Profile 路径
- SECRET_KEY: JWT 密钥
- ALLOWED_ORIGINS: 允许的前端域名

**配置文件**:
- config.yaml: 主配置文件
- .env: 环境变量文件
- docker-compose.yml: 容器编排配置

### 5.5 Agent 执行环境说明

**部署模式**: 每个命名 Agent 运行在独立的 Docker 容器中，通过独立的 Hermes Gateway 端口 (8765-8773) 对外提供服务。

**容器入口进程**: 每个 Agent 容器的入口进程是 Hermes Gateway 服务，监听对应端口（8765-8773），接收来自 FastAPI 后端的任务请求。Gateway 服务负责：(1) 接收 HTTP/WebSocket 请求，(2) 调度 Hermes 子 agent 执行任务，(3) 管理蜂群子进程（subprocess.Popen 创建的 Claude Code、Codex 等外部 AI 编程工具）。

**进程隔离**:
- 每个 Agent 容器拥有独立的进程空间、内存空间
- 容器间通过 FastAPI 后端进行协调通信，不直接互调
- 资源限制: 每个容器配置 CPU 和内存上限 (如 `--cpus=2.0 --memory=4g`)

**崩溃恢复**:
- Docker restart policy: `restart: unless-stopped`
- 容器崩溃后自动重启，FastAPI 后端通过健康检查检测 Agent 可用性
- Agent 崩溃不影响其他 Agent 的正常运行

**故障隔离**:
- 单个 Agent 容器故障仅影响该 Agent 负责的任务步骤
- 其他 Agent 继续正常运行
- FastAPI 后端记录故障日志并触发告警通知

**Gateway 路由策略**: FastAPI 后端不是轮询调用所有 Agent，而是根据任务分配的 Agent ID，从 agents 表的 api_endpoint 字段查找对应 Agent 容器的 Gateway 地址（如 http://hermes-houfa:8768/v1/chat/completions），发起精确路由请求。每个 Agent 有唯一端口，不存在负载均衡问题——后端按角色按需调用指定 Agent。

---

## 6. 安全架构

### 6.1 认证与授权

**用户认证**:
- JWT Token 认证 (HS256 算法)
- Access Token 有效期: 2 小时
- Refresh Token 有效期: 7 天
- Token 刷新机制: 前端在 Access Token 过期前自动刷新

**RBAC 权限控制**:
- 用户角色: user (普通用户)、admin (项目管理员)、system_admin (系统管理员)
- 权限检查装饰器: `@require_role('admin')` 等

**Agent 间调用鉴权**:
- 每个 Agent 持有独立的 JWT secret，存储在各 Agent 容器的 .env 文件中
- Agent 间调用通过内部 `/api/internal/agent-auth` 端点验证身份
- 后旺调用后发时携带签名请求头 `X-Agent-Token`，后端验证签名有效性
- 内部 API 调用不经过用户认证层，使用 Agent 专属鉴权通道

### 6.2 数据安全

**传输加密**:
- HTTPS 全链路加密 (Nginx 终止 TLS)
- WebSocket 连接使用 WSS 协议

**敏感数据存储**:
- Gitea API Token: 使用 PostgreSQL pgcrypto 扩展加密存储，90 天自动轮换
- Hermes Gateway API Key: 存储在 .env 文件中，应用启动时加载到内存，不落盘到数据库
- 用户密码: bcrypt 哈希存储

**日志脱敏**:
- 日志中自动脱敏 API Key、Token、密码等敏感信息
- 脱敏规则: 保留前 4 位和后 4 位，中间用 `****` 替换

### 6.3 网络安全

**CORS 策略**:
- Nginx 层面配置 CORS 白名单，仅允许前端域名访问
- FastAPI 层面二次校验 Origin 头

**请求限流**:
- 基于 Redis 的滑动窗口限流
- 默认限制: 100 请求/分钟/IP
- 管理后台 API: 50 请求/分钟/IP

**IP 白名单**:
- 管理后台接口仅允许指定 IP 段访问
- 内部 Agent 通信使用 Docker 内部网络，不暴露到外部

---

## 7. 性能优化

### 7.1 前端优化

- **代码分割**: 路由级懒加载，使用 `() => import()` 动态导入页面组件；Monaco Editor 等大体量组件使用 `defineAsyncComponent` 异步加载
- **懒加载策略**: ECharts 按需引入所需图表类型，避免全量加载
- **缓存策略**: 静态资源启用 gzip/brotli 压缩，CDN 缓存策略为 `max-age=31536000, immutable`；API 响应缓存使用 Redis，TTL 策略：项目列表 300s、项目详情 60s、Agent 状态不缓存
- **CDN 加速**: 静态资源通过 Nginx 配置 `add_header Cache-Control "public, max-age=31536000, immutable"`，文件采用 `[name].[hash].ext` 哈希命名

### 7.2 后端优化

- **异步处理**: 所有 I/O 密集型操作（数据库查询、HTTP 请求、Redis 操作）使用 async/await；Agent 任务调度使用 ARQ 异步队列
- **数据库索引优化**: 查询分析使用 `EXPLAIN ANALYZE` 定期审查慢查询，确保索引命中率 >95%
- **缓存策略**: Redis 缓存层，项目列表 TTL=300s、Agent 状态 TTL=60s、QA 检验结果 TTL=3600s；使用 Cache-Aside 模式
- **连接池管理**: PostgreSQL 连接池最小 5、最大 20、空闲超时 300s；Redis 连接池最大 50；HTTP 客户端（httpx）连接池最大 100、Keep-Alive 超时 30s

### 7.3 数据库优化

- **查询优化**: 复杂查询使用 CTE 和物化视图；避免 N+1 查询，使用 SQLAlchemy 的 `joinedload`/`selectinload`
- **索引设计**: 覆盖索引用于高频查询列；复合索引遵循最左前缀原则
- **分区表**: group_messages 按月份范围分区，单个分区数据量控制在 500 万行以内
- **读写分离**: 高并发场景启用只读副本，通过 SQLAlchemy 连接池路由实现（详见 9.3）

---

## 8. 监控与可观测性

### 8.1 监控工具链

**简化后的监控方案**（针对小规模部署 20 并发项目）:
- **Prometheus**: 采集系统级指标（CPU、内存、磁盘、网络）、应用级指标（API 响应时间、QPS、错误率）、Agent 级指标（任务执行时长、成功率、负载）、业务级指标（项目数、QA 通过率、步骤耗时）
- **Grafana**: 可视化仪表板，数据源为 Prometheus；同时集成 Loki 作为日志查询后端
- **Loki + Filebeat**: 日志采集与存储。FastAPI、ARQ worker、Celery worker、Agent 容器通过 Filebeat 将 JSON 结构化日志发送到 Loki，Grafana Explore 提供日志查询界面

**移除的工具及原因**:
- ELK Stack (Elasticsearch + Logstash + Kibana): 对于 20 并发项目规模过重，Loki + Filebeat 替代日志功能，资源占用更低
- Jaeger: 链路追踪在小规模部署中必要性较低，通过 Prometheus 指标 + Loki 日志 + Trace ID 关联已满足可观测需求

### 8.2 指标采集

- 系统级指标: CPU、内存、磁盘、网络
- 应用级指标: API 响应时间、QPS、错误率
- Agent 级指标: 任务执行时长、成功率、负载
- 业务级指标: 项目数、QA 通过率、步骤耗时

### 8.3 链路追踪

- Trace ID 贯穿全链路（FastAPI 请求 → ARQ worker → Agent 容器 → 子进程）
- 各服务日志中包含 trace_id 字段，通过 Loki 日志搜索实现链路追踪
- 无需独立 Jaeger 部署，降低运维复杂度

### 8.4 日志管理

- JSON 结构化日志
- 日志级别: DEBUG/INFO/WARN/ERROR/FATAL
- Filebeat 采集 → Loki 存储 → Grafana 查询
- 日志轮转和保留策略

---

## 9. 横向扩展设计

### 9.1 FastAPI 水平扩展

- 无状态设计支持多副本部署
- Nginx upstream 轮询负载均衡
- 副本数根据 CPU 使用率动态调整 (2-8 个)
- 会话状态存储于 Redis，支持跨副本共享
- **WebSocket 扩展策略**: WebSocket 连接采用 sticky session 模式，Nginx 配置 `ip_hash` 确保同一客户端连接到同一 FastAPI 副本；群聊消息通过 Redis Pub/Sub 在 FastAPI 副本间广播，实现跨副本消息同步

### 9.2 Celery Worker 扩容

- 根据 Redis 任务队列长度自动扩容
- 扩容阈值: 队列 >50 时增加 1 个 worker
- 缩容阈值: 队列 <5 时减少 1 个 worker
- 最小 worker 数: 1，最大 worker 数: 4

### 9.3 PostgreSQL 读写分离

- 触发条件: 数据库主库连接数 >200 或 P95查询延迟 >200ms 时启用只读副本
- 写入操作走主库，查询操作走只读副本
- 通过 SQLAlchemy 连接池路由实现读写分离
- 主从同步延迟 <1 秒
- **阈值依据**: 基于 pgbench 基准测试数据（单节点 200 连接时 P95 延迟从 45ms 增至 200ms，触发读写分离后降至 50ms）。阈值可通过环境变量 `PG_RW_SPLIT_THRESHOLD_CONNECTIONS` 和 `PG_RW_SPLIT_THRESHOLD_P95_MS` 独立配置

### 9.4 Redis 高可用

**小规模部署**（数据量 <10GB）: Redis 哨兵模式（1 Master + 2 Sentinels），提供自动故障转移能力。Master 节点故障时，哨兵自动选举新 Master，RTO <30 秒。

**大规模部署**（数据量 >10GB）: 切换到 Redis Cluster 模式 (3 主 3 从)，支持数据分片和自动故障转移。

**迁移过程**: 零停机在线迁移。

**阈值依据**: 基于 Redis 内存使用基准测试（单节点 8GB 内存时，内存碎片率 >1.5，命中率从 99% 降至 92%）。阈值可通过环境变量 `REDIS_CLUSTER_THRESHOLD_GB` 配置调整。

**故障转移覆盖**: 哨兵模式覆盖所有使用 Redis 的场景（ARQ 队列、Celery 代理、会话存储、限流计数器），确保 Redis 单点故障时系统自动恢复。

### 9.5 PostgreSQL 高可用

**流复制 + 自动故障转移**: 一主一从架构，主库通过 PostgreSQL 流复制 (Streaming Replication) 实时同步到从库。使用 pg_auto_failover 实现自动故障转移：主库故障时，从库自动提升为主库，RTO <2 分钟。

**高可用架构**:
- 主库：处理读写请求
- 从库：只读副本 + 故障接管
- pg_auto_failover watcher：监控主从状态，自动触发故障转移
- 同步模式：async（异步复制，延迟 <100ms）

**RTO/RPO 保障**: RTO <2 分钟（满足 <2 小时目标），RPO <1 秒（满足 <1 小时目标）。

### 9.6 监控组件扩缩容

- **Prometheus**: 多副本部署 + Thanos 长期存储。单副本满足 <100 个项目场景；>100 个项目时启用多副本分片采集，Thanos Store Gateway 提供历史查询
- **Grafana**: 无状态设计，支持多副本 + Nginx 负载均衡。配置和仪表板存储在 PostgreSQL/MySQL 后端，副本间数据一致
- **Loki**: 按日志量水平扩展（推荐 3 数据节点 + 1 读节点）；Filebeat 多副本并行处理日志

---

## 10. 容灾恢复与备份策略

### 10.1 RTO/RPO 目标
- **RTO (恢复时间目标)**: < 2 小时
- **RPO (恢复点目标)**: < 1 小时

### 10.2 备份策略
- **数据库备份**: 每日全量备份 + 每小时增量备份，保留 30 天
- **文件备份**: 每日备份，保留 90 天
- **代码仓库备份**: 每日备份，保留 90 天

### 10.3 恢复演练
- **频率**: 每季度一次
- **内容**: 模拟数据库故障、服务宕机等场景，验证备份恢复流程的有效性

---

## 11. 多用户并发资源隔离与调度

### 11.1 资源隔离
- **项目级隔离**: 每个项目独立分配资源配额，通过 project_id 标识隔离数据与计算资源
- **Agent 并发限制**: 每个命名 Agent 同时最多执行 1 个任务，避免单 Agent 过载
- **蜂群 Agent 隔离**: 蜂群内每个子 Agent 运行在独立子进程中，故障互不影响

### 11.2 数据库隔离
- 所有数据查询通过 project_id 过滤，确保多租户数据隔离
- 数据库行级安全策略（RLS）作为第二道防线

### 11.3 优先级队列
- 基于 priority 字段实现任务优先级排序（高 > 中 > 低）
- 同优先级任务按 FIFO 顺序执行

### 11.4 并发限制
- 系统最多同时运行 9 个项目（每个命名 Agent 最多执行 1 个任务，9 个 Agent 对应 9 个并发项目）
- 蜂群子 Agent 任务不计入项目并发数（蜂群任务属于项目内部并行）
- 超过限制的项目进入等待队列
- 等待队列中的项目按优先级和创建时间排序，自动获取空闲资源

---

## 12. 蜂群 Agent 子进程管理机制

### 12.1 五阶段生命周期
1. **启动**: 通过 `subprocess.Popen` 创建子进程，分配独立的执行环境
2. **初始化**: 注入任务参数、环境变量、工作目录等配置信息
3. **执行**: 实时监控子进程 stdout/stderr，收集执行日志和进度信息
4. **退出**: 正常完成或超时后发送 SIGTERM 信号，等待优雅退出（默认 10 秒）
5. **资源清理**: 回收工作目录、释放文件句柄、清理临时文件

### 12.2 崩溃恢复
- **检查机制**: 每 30 秒检查子进程健康状态
- **恢复策略**: 进程崩溃时自动重启（最多重试 3 次）；连续崩溃则切换备用 Agent 或标记任务为 failed

### 12.3 资源限制
- **CPU**: 每个子进程限制 CPU 使用率（默认不超过 80% 单核）
- **内存**: 每个子进程设置内存上限（默认 2GB），超限时触发 OOM 终止
- **超时**: 每个子进程设置执行超时（默认 30 分钟），超时后强制终止

### 12.4 信号处理与僵尸进程回收
- **SIGCHLD 处理**: 命名 Agent 容器内的进程管理器注册 SIGCHLD 信号处理器（`signal.signal(signal.SIGCHLD, handler)`），子进程退出时触发
- **僵尸进程回收**: SIGCHLD 处理器调用 `os.waitpid(-1, os.WNOHANG)` 非阻塞回收已退出的子进程，防止僵尸进程积累
- **优雅终止**: 主进程收到 SIGTERM 时，向所有子进程发送 SIGTERM，等待 10 秒后发送 SIGKILL 强制终止
- **进程泄漏防护**: 进程管理器维护子进程 ID 映射表（pid → task_id），定期（每 60 秒）巡检，对无映射的孤立进程执行终止操作

---

## 13. 数据迁移与版本升级管理

### 13.1 Alembic 迁移脚本管理
- **自动版本追踪**: Alembic 维护 `alembic_version` 表，自动记录当前数据库版本
- **正向迁移**: 支持增量升级，每次部署自动执行待迁移脚本
- **回滚支持**: 每个迁移脚本包含 downgrade 方法，支持回滚到任意历史版本

### 13.2 迁移日志
- 每次迁移操作记录执行时间、操作人、脚本版本到迁移日志表
- 迁移失败时自动记录错误信息，便于排查问题

### 13.3 语义化版本号
- 采用语义化版本（SemVer）: `主版本.次版本.修订版本`
- 主版本变更：不兼容的 API 变更
- 次版本变更：向下兼容的功能新增
- 修订版本：向下兼容的问题修复

### 13.4 升级流程
- **标准流程**: 备份 → 执行迁移 → 验证完整性 → 生产验证 → 标记完成
- **回滚流程**: 发现问题时 → 执行回滚迁移 → 恢复备份数据 → 验证回滚结果

---

**文档结束**