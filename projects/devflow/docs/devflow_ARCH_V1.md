# DevFlow 项目管理平台 - 架构设计文档

**版本**: V2  
**日期**: 2026-06-12  
**作者**: HouWang (后旺)  
**状态**: 修订版

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
               Gitea REST API         │                      │ Gateway API
┌──────────────────────────────────▼───┐                  │ POST /v1/chat/completions
│       Gitea 代码托管层 (本地部署)     │                  │ (支持流式SSE)
│  代码仓库管理 / Git Flow / PR审核     │                  │
│  统一成果存储：检验合格即刻提交        │                  │
└──────────────────────────────────────┘                  │
                                                          │
┌─────────────────────────────────────────────────────────▼───────────┐
│              9个独立Agent容器 (Hermes Profiles)                        │
│  每个Agent运行在独立Docker容器中，进程隔离，故障互不影响                │
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
│                          Agent蜂群层                                  │
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
│  │ groups    │ g_members │ group_msg    │meeting_   │ qa_records│   │
│  │           │  (关联)   │(含msg_type)  │outcomes   │           │   │
│  └───────────┴───────────┴──────────────┴───────────┴───────────┘   │
│  ┌───────────┬───────────┬──────────────┬───────────┬───────────┐   │
│  │ repos     │ branches  │ pull_requests│ commits   │task_commits│  │
│  └───────────┴───────────┴──────────────┴───────────┴───────────┘   │
│                                                                      │
│  说明:                                                               │
│  - group_msg表含msg_type字段区分: system/agent/user消息类型           │
│  - meeting_out表存储会议决策结果，写回流程调度引擎                     │
│  - task_commits为任务-提交关联表(非Gitea缓存)                         │
│  - Gitea数据通过REST API实时获取，仅commits/PRs作为审计缓存           │
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

### 2.2 应用层 (Application Layer)

**职责**: 业务逻辑处理、流程调度、Agent 协调

**技术栈**:
- Python FastAPI (REST API + WebSocket)
- asyncio + ARQ (Agent任务异步队列 - 长时间运行、进度追踪)
- Celery (离线批处理任务 - 定时报表生成、数据导出)
- Pydantic (数据验证)
- SQLAlchemy (ORM)

**职责分工说明**:
- **asyncio + ARQ**: 负责 Agent 任务调度（长时间运行、需要进度追踪的任务），避免引入额外的消息代理依赖，FastAPI 原生支持 asyncio
- **Celery**: 仅用于离线批处理任务（如定时报表生成、数据导出、定时清理等），不承担 Agent 调度职责

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
- **重试策略**: 最大重试 2 次，采用指数退避 (1min, 5min, 15min)
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
- **消息到状态机映射**: 会议模式产生的决策结果 (decisions JSON) 写回流程调度引擎，通过 `/api/projects/:id/step-update` 接口更新项目状态
- **会议结果存储**: meeting_outcomes 表存储决策、待办、风险、开放问题

### 3.2 支撑模块

#### 3.2.1 代码库管理模块

**职责**: 管理 Gitea 代码仓库、分支、PR、提交

**子模块**:
- RepoManager: 仓库管理器
- BranchManager: 分支管理器
- PRManager: PR 管理器
- CommitValidator: 提交验证器

#### 3.2.2 Hermes Agent 管理模块

**职责**: 管理 Hermes Agent 的安装、Profile 发现、Gateway 通信

**子模块**:
- ProfileScanner: Profile 扫描器
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
| 监控 | Prometheus | 2.x | 时序数据库、强大查询 |
| 可视化 | Grafana | 9.x | 丰富的图表、多数据源 |

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
- api: FastAPI 应用服务
- worker: Celery 异步任务 worker (仅离线批处理)
- db: PostgreSQL 数据库
- redis: Redis 缓存/消息队列
- gitea: Gitea 代码托管服务
- prometheus: Prometheus 监控
- grafana: Grafana 可视化
- elk-logstash: ELK Stack 日志收集
- elk-elasticsearch: ELK Stack 日志存储
- elk-kibana: ELK Stack 日志可视化
- jaeger: Jaeger 链路追踪
- hermes-haimei: 海梅 Agent 容器
- hermes-houxing: 后兴 Agent 容器
- hermes-houwang: 后旺 Agent 容器
- hermes-houfa: 后发 Agent 容器
- hermes-houbada: 后达 Agent 容器
- hermes-houfu: 后富 Agent 容器
- hermes-hougui: 后贵 Agent 容器
- hermes-hourong: 后荣 Agent 容器
- hermes-houhua: 后华 Agent 容器

### 5.3 端口分配

| 服务 | 端口 | 协议 | 用途 |
|------|------|------|------|
| Nginx | 80/443 | HTTP/HTTPS | 反向代理 |
| FastAPI | 8000 | HTTP | 应用 API |
| PostgreSQL | 5432 | TCP | 数据库 |
| Redis | 6379 | TCP | 缓存/队列 |
| Gitea | 3000 | HTTP | 代码托管 (内部端口) |
| Gitea SSH | 222 | SSH | Git SSH |
| Prometheus | 9090 | HTTP | 监控 |
| Grafana | 3001 | HTTP | 可视化 |
| Elasticsearch | 9200 | HTTP | 日志存储 |
| Kibana | 5601 | HTTP | 日志可视化 |
| Jaeger | 16686 | HTTP | 链路追踪 |
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
- Gitea HTTP 3000 端口通过 Nginx 子路径 `/gitea/` 反向代理暴露，避免与 Grafana 3001 冲突
- Hermes Agent 端口 8765-8773 对应 9 个独立 Agent 容器，每个容器运行一个 Hermes Gateway 服务

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

### 8.1 指标采集

- 系统级指标: CPU、内存、磁盘、网络
- 应用级指标: API 响应时间、QPS、错误率
- Agent 级指标: 任务执行时长、成功率、负载
- 业务级指标: 项目数、QA 通过率、步骤耗时

### 8.2 链路追踪

- OpenTelemetry 标准
- Trace ID 全链路追踪
- Jaeger 后端存储

### 8.3 日志管理

- JSON 结构化日志
- 日志级别: DEBUG/INFO/WARN/ERROR/FATAL
- ELK Stack 集中管理
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

- 触发条件: 并发项目数 >10 时启用只读副本
- 写入操作走主库，查询操作走只读副本
- 通过 SQLAlchemy 连接池路由实现读写分离
- 主从同步延迟 <1 秒
- **阈值依据**: 基于基准测试数据（使用 pgbench 模拟 10 并发项目场景，P95 查询延迟从 45ms 增至 200ms，触发读写分离后降至 50ms）。阈值可通过环境变量 `PG_RW_SPLIT_THRESHOLD` 配置调整

### 9.4 Redis 集群

- 数据量 <10GB: 单节点 Redis + AOF 持久化
- 数据量 >10GB: 切换到 Redis Cluster 模式 (3 主 3 从)
- 迁移过程: 零停机在线迁移
- **阈值依据**: 基于 Redis 内存使用基准测试（单节点 8GB 内存时，内存碎片率 >1.5，命中率从 99% 降至 92%）。阈值可通过环境变量 `REDIS_CLUSTER_THRESHOLD_GB` 配置调整

---

**文档结束**
