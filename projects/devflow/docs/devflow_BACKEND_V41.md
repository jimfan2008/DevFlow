# DevFlow 项目管理平台 - 后端设计文档

**版本**: V41
**日期**: 2026-06-16
**作者**: HouWang (后旺)
**状态**: 修订版V41（基于V40进行跨文档一致性检验修正，修复前端V20/数据库V33共13项不一致问题）

---

## 1. 后端概述

### 1.1 设计目标

DevFlow 后端是一个高并发的 AI Agent 调度与协作平台，核心职责包括：

1. 提供完整的 RESTful API，支撑前端交互与外部系统集成
2. 调度 9 个命名 Agent 角色，执行 16 步标准开发流程
3. 管理 Agent 蜂群的建立、任务分发、进度监控和成果收集
4. 实现 QA 门控机制，确保每步产出经后荣检验合格后方可进入下一步
5. 提供项目讨论群服务，支持讨论模式和会议模式的实时沟通
6. 集成 Gitea 代码仓库，实现检验合格产出的自动提交
7. 通过 WebSocket 实现实时通信和状态推送

### 1.2 技术选型

| 层     | 技术                         | 说明                          |
| ----- | -------------------------- | --------------------------- |
| 应用框架  | Python 3.11 + FastAPI      | 异步高性能 Web 框架，原生支持 WebSocket |
| ORM   | SQLAlchemy 2.0             | 异步 ORM，支持 PostgreSQL 全特性    |
| 任务队列  | Celery + Redis             | 异步任务调度，支持 Agent 执行、蜂群调度等    |
| 缓存/状态 | Redis 6+                   | Agent 状态缓存、会话管理、分布式锁        |
| 数据库   | PostgreSQL 15              | 主存储引擎、JSONB、全文检索、分区表        |
| 实时通信  | FastAPI WebSocket          | 群聊消息、流程状态推送、流式响应            |
| 认证    | JWT (PyJWT)                | 无状态 Token 认证                |
| 监控    | Prometheus + OpenTelemetry | 指标采集、链路追踪                   |
| 日志    | Python logging + JSON 格式   | 结构化日志，ELK Stack 集中管理        |
| 部署    | Docker + Docker Compose    | 容器化部署                       |

**Celery 选型说明 (V25 补充)**：

为什么选择 Celery 而不是 FastAPI 原生 asyncio 任务队列：

| 维度    | asyncio Task        | Celery                            | 选择理由                      |
| ----- | ------------------- | --------------------------------- | ------------------------- |
| 任务持久化 | 进程内存，重启丢失           | Broker (Redis) 持久化队列              | Agent 任务最长 30 分钟，进程重启不能丢失 |
| 分布式执行 | 单机单进程               | 多 Worker 跨机器部署                    | 支持水平扩展，蜂群任务需要多并发          |
| 定时任务  | 需额外框架 (APScheduler) | Celery Beat 原生支持                  | Profile 扫描、备份等定时任务开箱即用    |
| 重试策略  | 需手动实现               | 原生 retry() + exponential backoff  | Agent 执行失败需要自动重试（3 次）     |
| 任务监控  | 无内置                 | Flower 可视化监控 + 结果后端               | 需要实时监控 Agent 任务执行状态       |
| 超时控制  | asyncio.wait_for()  | task_time_limit + soft_time_limit | 硬超时强制终止 + 软超时允许清理资源       |
| 结果存储  | 内存                  | Redis/DB 后端                       | 需要跨请求查询任务结果               |

结论：DevFlow 的 Agent 执行任务是典型的**长时间运行、需要持久化、支持重试、可分布式**的场景，Celery 是比 asyncio Task 更成熟和可靠的选择。asyncio Task 仅用于请求级别的高速异步操作（如数据库查询、缓存读取）。

### 1.3 后端模块架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI 应用层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ 路由层    │ │ 中间件    │ │ 认证层    │ │ 错误处理  │          │
│  │ (routers) │ │ (middlewares)│ │(auth)  │ │(handlers)│          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │                   │
│  ┌────▼────────────▼────────────▼────────────▼───────────┐     │
│  │                    服务层 (Services)                    │     │
│  │  ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐│     │
│  │  │流程编排       │ │Agent调度 │ │QA门控    │ │蜂群   ││     │
│  │  │服务           │ │服务     │ │服务      │ │管理   ││     │
│  │  └──────────────┘ └──────────┘ └──────────┘ └───────┘│     │
│  │  ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐│     │
│  │  │步骤执行       │ │状态机    │ │讨论群    │ │代码   ││     │
│  │  │服务           │ │服务     │ │服务      │ │仓库   ││     │
│  │  └──────────────┘ └──────────┘ └──────────┘ └───────┘│     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│     │
│  │  │通知       │ │Gateway  │ │WebSocket │ │文件     ││     │
│  │  │服务       │ │通信     │ │管理      │ │服务     ││     │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘│     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │     │
│  │  │Profile   │ │日志监控  │ │会议      │              │     │
│  │  │扫描服务   │ │服务       │ │服务      │              │     │
│  │  └──────────┘ └──────────┘ └──────────┘              │     │
│  └──────────────────────────────────────────────────────┘     │
│                        │                                       │
│  ┌─────────────────────▼───────────────────────────────────┐  │
│  │                  数据访问层 (Repositories)                │  │
│  │  SQLAlchemy 2.0 Async ORM + Alembic 迁移                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                  │                    │
         ▼                  ▼                    ▼
  ┌──────────────┐  ┌───────────┐    ┌──────────────────┐
  │ PostgreSQL   │  │   Redis   │    │ Hermes Gateway   │
  │ (主数据库)   │  │ (缓存/队列)│    │ API (9个Agent)   │
  └──────────────┘  └───────────┘    └──────────────────┘
         │
         ▼
  ┌──────────────┐
  │    Gitea     │
  │ (代码托管)   │
  └──────────────┘
```

服务层拆分说明（V19）：为解决 V18 中 workflow_service.py 职责过重的问题，V19 将其拆分为三个独立服务：
- **流程编排服务 (workflow_orchestrator.py)**: 负责 16 步流程的整体协调、步骤间依赖管理和流程推进决策
- **步骤执行服务 (step_executor.py)**: 负责单个步骤的具体执行、Agent 调度和结果收集
- **状态机服务 (workflow_statemachine.py)**: 负责流程状态转换、前置条件验证和状态一致性保证

### 1.4 目录结构

```
devflow/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 应用入口
│   ├── config.py                   # 配置管理 (pydantic-settings)
│   ├── dependencies.py             # 依赖注入
│   ├── exceptions.py               # 自定义异常
│   ├── middleware.py               # 中间件
│   │
│   ├── core/                       # 核心基础设施
│   │   ├── security.py             # 认证/授权
│   │   ├── redis_client.py         # Redis 客户端
│   │   ├── gateway_client.py       # Hermes Gateway API 客户端
│   │   ├── profile_scanner.py      # Profile 自动扫描
│   │   └── semaphore.py            # 并发控制信号量
│   │
│   │ 职责边界说明 (V25 补充):
│   │ - core/ 层定位: 纯基础设施组件，无业务逻辑，可被 services 层复用
│   │ - profile_scanner.py: 底层文件系统扫描器，负责扫描 ~/.hermes/profiles/ 目录
│   │   发现 Hermes Agent Profile，检查 Gateway 端口连通性。它是纯 I/O 操作，
│   │   不包含注册/注销/状态同步等业务逻辑
│   │ - semaphore.py: 底层并发控制原语封装（asyncio.Semaphore 包装器 + 超时处理
│   │   + profile 级互斥锁工厂）。放在 core 层是因为它和 redis_client.py、
│   │   gateway_client.py 一样，属于基础设施级工具类，不依赖任何业务模型
│   │
│   │ 对比 services/profile_service.py:
│   │ - profile_service.py: 业务服务层，调用 profile_scanner.py 获取扫描结果，
│   │   然后执行注册/注销/状态同步/数据库持久化等业务逻辑。profile_service
│   │   依赖 profile_scanner，但 profile_scanner 不依赖 profile_service
│   ├── models/                     # SQLAlchemy 模型
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── group.py
│   │   ├── swarm.py
│   │   ├── qa.py
│   │   ├── repo.py
│   │   ├── notification.py
│   │   ├── meeting.py
│   │   ├── artifact.py             # V19 新增：文件产出物模型
│   │   ├── audit_log.py            # V30 新增：审计日志模型
│   │   └── step_event.py           # V39 新增：分布式一致性事件记录模型
│   │
│   ├── schemas/                    # Pydantic 数据模型
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── group.py
│   │   ├── swarm.py
│   │   ├── qa.py
│   │   ├── repo.py
│   │   ├── notification.py
│   │   ├── meeting.py
│   │   ├── pagination.py           # V19 新增：分页 schema
│   │   ├── artifact.py             # V19 新增：文件产出物 schema
│   │   ├── error.py                # V30 新增：统一错误响应 schema
│   │   ├── audit_log.py            # V30 新增：审计日志 schema
│   │   ├── settings.py             # V39 新增：用户设置 schema
│   │   └── step_event.py           # V39 新增：步骤事件 schema
│   │
│   ├── routers/                    # API 路由
│   │   ├── auth.py                 # 认证路由
│   │   ├── projects.py             # 项目管理路由
│   │   ├── agents.py               # Agent 管理路由
│   │   ├── workflow.py             # 16步流程路由
│   │   ├── qa.py                   # QA 门控路由
│   │   ├── swarms.py               # 蜂群管理路由
│   │   ├── groups.py               # 讨论群路由
│   │   ├── repos.py                # 代码仓库路由
│   │   ├── notifications.py        # 通知路由
│   │   ├── hermes.py               # Hermes Gateway 路由
│   │   ├── websocket.py            # WebSocket 路由
│   │   ├── artifacts.py            # V19 新增：文件产出物路由
│   │   ├── health.py               # V30 新增：健康检查路由
│   │   └── settings.py             # V39 新增：用户设置路由
│   │
│   ├── services/                   # 业务服务层
│   │   ├── project_service.py      # 项目管理服务
│   │   ├── agent_service.py        # Agent 管理服务
│   │   ├── workflow_orchestrator.py # V19 新增：流程编排服务
│   │   ├── step_executor.py        # V19 新增：步骤执行服务
│   │   ├── workflow_statemachine.py # V19 新增：状态机服务
│   │   ├── task_scheduler.py       # 任务调度引擎
│   │   ├── qa_service.py           # QA 门控服务
│   │   ├── swarm_service.py        # 蜂群管理服务
│   │   ├── group_service.py        # 讨论群服务
│   │   ├── repo_service.py         # 代码仓库集成服务
│   │   ├── notification_service.py # 通知服务
│   │   ├── gateway_service.py      # Gateway 通信服务
│   │   ├── profile_service.py      # Profile 扫描服务
│   │   ├── meeting_service.py      # 会议模式服务
│   │   ├── websocket_service.py    # WebSocket 管理服务
│   │   ├── artifact_service.py     # V19 新增：文件产出物服务
│   │   ├── audit_log_service.py    # V30 新增：审计日志服务
│   │   └── settings_service.py     # V39 新增：用户设置服务
│   │
│   ├── repositories/               # 数据访问层
│   │   ├── base.py                 # 基础 Repository
│   │   ├── user_repo.py
│   │   ├── project_repo.py
│   │   ├── agent_repo.py
│   │   ├── task_repo.py
│   │   ├── group_repo.py
│   │   ├── swarm_repo.py
│   │   ├── qa_repo.py
│   │   ├── repo_repo.py
│   │   ├── notification_repo.py
│   │   ├── meeting_repo.py
│   │   ├── task_dependency_repo.py
│   │   ├── artifact_repo.py        # V19 新增：文件产出物 Repository
│   │   ├── audit_log_repo.py       # V30 新增：审计日志 Repository
│   │   └── step_event_repo.py      # V39 新增：步骤事件 Repository
│   │
│   ├── tasks/                      # Celery 异步任务
│   │   ├── celery_app.py           # Celery 应用配置
│   │   ├── agent_tasks.py          # Agent 执行任务
│   │   ├── swarm_tasks.py          # 蜂群调度任务
│   │   ├── qa_tasks.py             # QA 检验任务
│   │   ├── sync_tasks.py           # 同步任务 (Profile/Gitea)
│   │   └── backup_tasks.py         # 备份任务
│   │
│   └── monitoring/                 # 监控与日志
│       ├── metrics.py              # Prometheus 指标
│       ├── tracing.py              # OpenTelemetry 链路追踪
│       └── logger.py               # 结构化日志
│
├── alembic/                        # 数据库迁移
├── tests/                          # 测试
│   ├── unit/                       # V19 新增：单元测试
│   ├── integration/                # V19 新增：集成测试
│   ├── e2e/                        # V19 新增：端到端测试
│   └── fixtures/                   # V19 新增：测试数据工厂
├── docker/                         # Docker 配置
├── pyproject.toml                  # 项目配置
└── README.md
```

---

## 2. API 设计（RESTful 端点列表）

### 2.1 统一规范

- **基础路径**: `/api/v1`
- **认证方式**: Bearer Token (JWT)
- **响应格式**: JSON
- **分页**:
  - 页码分页: `?page=&limit=`，默认每页 20 条，适用于列表浏览场景
  - 游标分页: `?cursor=&limit=`，cursor 为 Base64 编码的资源 ID，适用于大数据量场景和无限滚动（V19 新增）
- **排序**: `?sort=field,asc/desc`，默认按 created_at desc
- **过滤**: 查询字符串 `?status=active&role=admin`
- **错误码**: HTTP 状态码 + 业务错误码
- **Conventional Commits**: 所有代码提交遵循 Conventional Commits 规范
- **API 文档**: FastAPI 自动生成 OpenAPI/Swagger 文档，访问 `/docs` (Swagger UI) 和 `/redoc` (ReDoc)
- **API 版本化**: URL 路径版本化 (`/api/v1/`)。MAJOR 版本变更可能引入不兼容修改；MINOR 版本保证向后兼容。废弃的端点将在响应头中包含 `Deprecation: true`，并至少保留到下一个 MINOR 版本发布后

### 2.1.1 统一响应格式 (V30 新增)

所有 API 响应遵循统一格式：

**成功响应 (页码分页)**:

```json
{
  "success": true,
  "data": { ... },
  "message": "success",
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 10,
    "has_more": false
  }
}
```

**成功响应 (游标分页)**:

```json
{
  "success": true,
  "data": [...],
  "message": "success",
  "pagination": {
    "has_more": true,
    "next_cursor": "eyJpZC...WiJ9",
    "limit": 20
  }
}
```

**失败响应**:

```json
{
  "success": false,
  "error": "错误描述信息",
  "code": 422,
  "business_code": 30001,
  "detail": "详细错误说明",
  "trace_id": "abc-123-def-456"
}
```

字段说明：
- `success`: 布尔值，标识请求是否成功
- `data`: 成功时的数据载荷，失败时为 null
- `error`: 简短错误描述
- `code`: HTTP 状态码
- `business_code`: 业务错误码（5 位数字），用于前端精确定位错误场景
- `detail`: 详细错误信息，包含调试上下文
- `trace_id`: 链路追踪 ID，用于日志排查
- `pagination`: 分页信息（仅列表接口返回）

### 2.1.2 分页参数标准 (V30 新增)

**页码分页 (Page-based Pagination)**:

| 参数 | 类型 | 默认值 | 范围 | 说明 |
| ---- | ---- | ------ | ---- | ---- |
| page | int | 1 | >= 1 | 页码（从 1 开始） |
| limit | int | 20 | 1-100 | 每页条数 |

请求示例: `GET /api/v1/projects?page=2&limit=50`

**游标分页 (Cursor-based Pagination)**:

| 参数 | 类型 | 默认值 | 说明 |
| ---- | ---- | ------ | ---- |
| cursor | string | null | Base64 编码的 JSON `{"id": last_seen_id}` |
| limit | int | 20 | 每页条数（范围 1-100） |

请求示例: `GET /api/v1/projects/:id/tasks?cursor=***==&limit=20`

首次请求不传 cursor 或传 `cursor=0`，返回最前面的 N 条。

**排序参数**:

| 参数 | 格式 | 示例 | 说明 |
| ---- | ---- | ---- | ---- |
| sort | `field,asc/desc` | `sort=created_at,desc` | 多个排序使用重复参数: `sort=name,asc&sort=created_at,desc` |

默认排序: `created_at,desc`（最新在前）

### 2.1.3 速率限制策略 (V30 新增)

| 维度 | 限制 | 说明 |
| ---- | ---- | ---- |
| 全局 | 100 次/秒/用户 | 基于 Redis 滑动窗口，每用户每端点独立计数 |
| 文件上传 | 10 次/分钟/用户 | 防止大文件暴力上传 |
| WebSocket 消息 | 60 条/分钟/用户 | 防止群聊消息洪水 |
| Agent 对话 | 30 次/分钟/用户 | 控制 Gateway 调用频率 |

超出限制返回 HTTP 429，响应头包含 `Retry-After` 字段（秒数）。

计数键格式: `rate_limit:{user_id}:{endpoint}`
窗口大小: 1 秒（全局）/ 1 分钟（其他）

### 2.2 认证与用户

| 方法   | 路径                    | 描述                  | 认证  |
| ---- | --------------------- | ------------------- | --- |
| POST | /api/v1/auth/login    | 用户登录                | 否   |
| POST | /api/v1/auth/register | 用户注册                | 否   |
| POST | /api/v1/auth/refresh  | 刷新 Token            | 是   |
| POST | /api/v1/auth/logout   | 用户登出 (加入 Token 黑名单) | 是   |
| GET  | /api/v1/auth/me       | 获取当前用户信息            | 是   |

**V41 修正**: 移除 POST /api/v1/auth/ws-token 端点。WebSocket 认证直接使用前端的 access_token，与前端 V20 保持一致。

### 2.2.1 认证流程详细设计

**认证流程**:

```
1. 用户登录 → 服务端验证凭证 → 签发 Access Token + Refresh Token
2. 前端请求携带 Authorization: Bearer ***
3. Token 过期 → 使用 Refresh Token 获取新的一对 Token
4. 用户登出 → Access Token 加入黑名单 → Refresh Token 失效
```

**Token 说明**:
- Access Token: 有效期 2 小时（7200 秒），签名算法 RS256
- Refresh Token: 有效期 7 天，轮换机制（每次使用后旧 Token 立即失效）
- Token 存储在 Redis 黑名单中用于吊销，键格式 `token:blacklist:{jti}`
- WebSocket 认证: 直接使用 access_token 通过 auth 消息进行认证，无需专用 ws_token

### 2.2.2 认证端点请求/响应详细定义 (V30 补全)

**POST /api/v1/auth/login** - 用户登录

请求头: 无需认证
请求体 (Content-Type: application/json):

```json
{
  "username": "devuser",
  "password": "secure_password_123"
}
```

请求参数校验:
| 字段 | 类型 | 必填 | 校验规则 |
| ---- | ---- | ---- | -------- |
| username | string | 是 | 长度 3-64 字符，仅允许字母、数字、下划线、连字符 |
| password | string | 是 | 长度 8-128 字符 |

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...NiIs...",
    "refresh_token": "dGhpcyBpcyBhIHJlZnJl...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user": {
      "id": 1,
      "username": "devuser",
      "email": "devuser@example.com",
      "role": "user",
      "is_active": true,
      "created_at": "2026-06-01T08:00:00Z"
    }
  },
  "message": "登录成功"
}
```

失败响应 (401 Unauthorized):

```json
{
  "success": false,
  "error": "用户名或密码错误",
  "code": 401,
  "business_code": 10002,
  "detail": "凭证验证失败，请检查用户名和密码",
  "trace_id": "trace-abc-123"
}
```

**POST /api/v1/auth/register** - 用户注册

请求体:

```json
{
  "username": "newuser",
  "password": "secure_password_123",
  "email": "newuser@example.com"
}
```

请求参数校验:
| 字段 | 类型 | 必填 | 校验规则 |
| ---- | ---- | ---- | -------- |
| username | string | 是 | 长度 3-64 字符，仅允许字母、数字、下划线、连字符 |
| password | string | 是 | 长度 8-128 字符，至少包含大小写字母和数字 |
| email | string | 是 | 合法邮箱格式 (regex: `^[^\\s]+@[^\\s]+\\.[^\\s]+$`) |

成功响应 (201 Created):

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...NiIs...",
    "refresh_token": "dGhpcyBpcyBhIHJlZnJl...",
    "token_type": "Bearer",
    "expires_in": 7200,
    "user": {
      "id": 2,
      "username": "newuser",
      "email": "newuser@example.com",
      "role": "user",
      "is_active": true,
      "created_at": "2026-06-22T10:00:00Z"
    }
  },
  "message": "注册成功"
}
```

失败响应 (409 Conflict):

```json
{
  "success": false,
  "error": "用户名已存在",
  "code": 409,
  "business_code": 20002,
  "detail": "该用户名已被注册，请使用其他用户名",
  "trace_id": "trace-def-456"
}
```

**POST /api/v1/auth/refresh** - 刷新 Token

请求体:

```json
{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJl..."
}
```

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "access_token": "***...xxx",
    "refresh_token": "bmV3cmVmcmVzaA...yyy",
    "token_type": "Bearer",
    "expires_in": 7200
  },
  "message": "Token 刷新成功"
}
```

失败响应 (401 Unauthorized):

```json
{
  "success": false,
  "error": "Refresh Token 已过期或已吊销",
  "code": 401,
  "business_code": 10003,
  "detail": "Refresh Token 已失效，请重新登录",
  "trace_id": "trace-ghi-789"
}
```

**POST /api/v1/auth/logout** - 用户登出

请求头: `Authorization: Bearer ***`
请求体:

```json
{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJl..."
}
```

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "message": "登出成功",
    "blacklisted_access_tokens": 1,
    "invalidated_refresh_tokens": 1
  },
  "message": "登出成功"
}
```

**GET /api/v1/auth/me** - 获取当前用户信息

请求头: `Authorization: Bearer ***`
查询参数: 无

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "devuser",
    "email": "devuser@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2026-06-01T08:00:00Z",
    "updated_at": "2026-06-20T12:00:00Z",
    "active_projects": 3,
    "total_projects": 12
  }
}
```

失败响应 (401 Unauthorized):

```json
{
  "success": false,
  "error": "Token 已过期",
  "code": 401,
  "business_code": 10001,
  "detail": "Access Token 已超过 2 小时有效期，请使用 Refresh Token 刷新或重新登录",
  "trace_id": "trace-jkl-012"
}
```

**V41 修正**: ws-token 端点已移除，WebSocket 认证直接使用 access_token。
- 服务端通过 Redis 验证 ws_token 有效性，键格式 `ws_token:{token_hash}`

### 2.3 项目管理

| 方法     | 路径                            | 描述                | 认证  |
| ------ | ----------------------------- | ----------------- | --- |
| GET    | /api/v1/projects              | 获取用户项目列表 (分页)     | 是   |
| POST   | /api/v1/projects              | 创建项目 (第一步：人类用户执行) | 是   |
| GET    | /api/v1/projects/:id          | 获取项目详情            | 是   |
| PUT    | /api/v1/projects/:id          | 更新项目信息           | 是   |
| DELETE | /api/v1/projects/:id          | 软删除项目             | 是   |
| GET    | /api/v1/projects/:id/progress | 获取 16 步流程进度       | 是   |
| GET    | /api/v1/projects/:id/steps    | 获取 16 步流程进度 (别名)   | 是   |

**V41 修正**: 项目更新端点 HTTP 方法改为 PUT，与前端 V20 §5.2 端点清单 (PUT /projects/:id) 保持一致。

**GET /api/v1/projects** - 获取用户项目列表

查询参数:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
| ---- | ---- | ---- | ------ | ---- |
| page | int | 否 | 1 | 页码 |
| limit | int | 否 | 20 | 每页条数 (1-100) |
| sort | string | 否 | created_at,desc | 排序字段和方向 |
| status | string | 否 | null | 按状态过滤: active/paused/completed/archived |

**V41 修正**: status 过滤枚举值改为 active/paused/completed/archived，与数据库 V33 §1.3 project_status 枚举保持一致。

成功响应 (200 OK):

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "DevFlow Platform",
      "description": "AI Agent 驱动的全自动开发工具",
      "creator_id": 1,
      "current_step": 5,
      "status": "paused",
      "gitea_repo_id": 10,
      "created_at": "2026-06-01T08:00:00Z",
      "updated_at": "2026-06-15T12:00:00Z",
      "deleted_at": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 42,
    "has_more": true
  }
}
```

**POST /api/v1/projects** - 创建项目

请求体:

```json
{
  "name": "DevFlow Platform",
  "description": "AI Agent 驱动的全自动开发工具"
}
```

请求参数校验:
| 字段 | 类型 | 必填 | 校验规则 |
| ---- | ---- | ---- | -------- |
| name | string | 是 | 长度 1-200 字符，不能全空白 |
| description | string | 否 | 最大 5000 字符 |

成功响应 (201 Created): 返回 ProjectOut 对象
失败响应 (409 Conflict): business_code=20002 (项目名已存在)

**GET /api/v1/projects/:id** - 获取项目详情

路径参数:
| 参数 | 类型 | 必填 | 说明 |
| ---- | ---- | ---- | ---- |
| id | int | 是 | 项目 ID |

成功响应 (200 OK): 返回 ProjectOut 对象
失败响应 (404 Not Found): business_code=20001 (项目不存在)
失败响应 (403 Forbidden): business_code=10004 (无权访问)

**PUT /api/v1/projects/:id** - 更新项目信息 (V41 修正: 改为 PUT，与前端 V20 保持一致)

请求体 (所有字段可选，仅提交需要更新的字段):

```json
{
  "name": "新项目名称",
  "description": "更新后的描述"
}
```

成功响应 (200 OK): 返回更新后的 ProjectOut 对象

说明：V41 修正，将 HTTP 方法改为 PUT，与前端 V20 §5.2 节 updateProject (PUT /projects/:id) 保持一致。

**DELETE /api/v1/projects/:id** - 删除项目

V41 修正：DELETE 操作将项目 status 更新为 archived，与数据库 V33 §3.1 projects 表一致（已移除 deleted_at 字段）。

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "status": "archived"
  },
  "message": "项目已删除"
}
```

**GET /api/v1/projects/:id/progress** - 获取 16 步流程进度

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "current_step": 5,
    "steps": [
      {
        "step_number": 1,
        "step_name": "人类用户创建项目",
        "status": "completed",
        "assigned_agent": null,
        "started_at": "2026-06-01T08:00:00Z",
        "completed_at": "2026-06-01T08:00:00Z"
      },
      {
        "step_number": 5,
        "step_name": "建立开发环境",
        "status": "paused",
        "assigned_agent": "houfu",
        "started_at": "2026-06-15T10:00:00Z",
        "completed_at": null
      }
    ]
  }
}
```

**GET /api/v1/projects/:id/steps** - 获取 16 步流程进度 (V36 新增: 别名端点)

说明：此端点是 `/api/v1/projects/:id/progress` 的别名，返回相同的数据格式。新增此别名以与前端 V16 约定的端点路径保持一致。前端使用 `GET /projects/:id/steps` 获取项目步骤进度，后端通过此别名端点兼容前端调用。

成功响应 (200 OK): 返回与 `/api/v1/projects/:id/progress` 相同的 ProjectProgressOut 数据

### 2.4 16 步流程调度

| 方法   | 路径                                         | 描述                      | 认证  |
| ---- | ------------------------------------------ | ----------------------- | --- |
| POST | /api/v1/projects/:id/workflow/step/:number | 执行指定步骤 (:number 为 2-16) | 是   |
| GET  | /api/v1/projects/:id/workflow/status       | 获取当前流程状态                | 是   |
| POST | /api/v1/projects/:id/workflow/rollback     | 回退到指定步骤 (用于迭代)          | 是   |

**POST /api/v1/projects/:id/workflow/step/:number** - 执行指定步骤

路径参数:
| 参数 | 类型 | 必填 | 说明 |
| ---- | ---- | ---- | ---- |
| id | int | 是 | 项目 ID |
| number | int | 是 | 步骤编号 (2-16) |

请求体 (可选):

```json
{
  "options": {
    "force_rerun": false,
    "custom_agent": null
  }
}
```

请求参数校验:
| 字段 | 类型 | 必填 | 校验规则 |
| ---- | ---- | ---- | -------- |
| options.force_rerun | boolean | 否 | 默认 false |
| options.custom_agent | string | 否 | 必须在 9 个命名 Agent Profile 列表中 |

成功响应 (202 Accepted):

```json
{
  "success": true,
  "data": {
    "task_id": 42,
    "step_number": 3,
    "status": "paused",
    "assigned_agent": "houxing",
    "message": "步骤执行已启动",
    "estimated_duration_seconds": 900
  },
  "message": "步骤执行已启动"
}
```

失败响应 (422 Unprocessable Entity): business_code=30001 (前置步骤未完成)
失败响应 (409 Conflict): business_code=30002 (步骤已在执行中)

**GET /api/v1/projects/:id/workflow/status** - 获取当前流程状态

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "current_step": 5,
    "current_status": "paused",
    "assigned_agent": "houfu",
    "started_at": "2026-06-15T10:00:00Z",
    "total_steps": 16,
    "completed_steps": 4,
    "progress_percent": 25
  }
}
```

**POST /api/v1/projects/:id/workflow/rollback** - 回退到指定步骤

请求体:

```json
{
  "target_step": 3,
  "reason": "需求变更，需要重新进行需求分析"
}
```

成功响应 (200 OK): 返回回退后的流程状态

### 2.5 任务管理

| 方法     | 路径                                     | 描述              | 认证  |
| ------ | -------------------------------------- | --------------- | --- |
| GET    | /api/v1/projects/:id/tasks             | 获取项目任务列表        | 是   |
| GET    | /api/v1/tasks/:id                      | 获取任务详情          | 是   |
| PUT    | /api/v1/tasks/:id                      | 更新任务状态            | 是   |
| POST   | /api/v1/tasks/batch/update             | 批量更新任务状态       | 是   |
| GET    | /api/v1/tasks/:id/dependencies         | 获取任务依赖图         | 是   |
| POST   | /api/v1/tasks/:id/dependencies         | 添加任务依赖          | 是   |
| DELETE | /api/v1/tasks/:id/dependencies/:dep_id | 移除任务依赖          | 是   |

**V41 修正**: 任务更新端点 HTTP 方法改为 PUT，与前端 V20 §4.5 taskStore updateTaskStatus (PUT /tasks/:id) 保持一致。

**PUT /api/v1/tasks/:id** - 更新任务状态 (V41 修正: 改为 PUT)

请求体 (所有字段可选):

```json
{
  "status": "completed"
}
```

成功响应 (200 OK): 返回更新后的 TaskOut 对象

说明：V41 修正，将 HTTP 方法改为 PUT，与前端 V20 §4.5 节 updateTaskStatus (PUT /tasks/:id) 保持一致。

**POST /api/v1/tasks/batch/update** - 批量更新任务状态

请求体:

```json
{
  "task_ids": [1, 2, 3],
  "status": "completed"
}
```

请求参数校验:
| 字段 | 类型 | 必填 | 校验规则 |
| ---- | ---- | ---- | -------- |
| task_ids | array | 是 | 至少 1 个元素，最大 100 个 |
| status | string | 是 | pending/in_progress/completed/failed/cancelled |

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "updated": 3,
    "failed": [],
    "message": "批量更新完成"
  }
}
```

### 2.6 Agent 管理

| 方法     | 路径                               | 描述                     | 认证  |
| ------ | -------------------------------- | ---------------------- | --- |
| GET    | /api/v1/agents                   | 获取所有 Agent 列表          | 是   |
| GET    | /api/v1/agents/:id               | 获取 Agent 详情            | 是   |
| GET    | /api/v1/agents/named             | 获取 9 个命名 Agent 列表      | 是   |
| POST   | /api/v1/agents/register          | 编程 Agent 注册 (蜂群成员)     | 是   |
| DELETE | /api/v1/agents/:id               | 移除蜂群 Agent             | 是   |
| GET    | /api/v1/profiles                 | 获取扫描到的 Hermes Profiles | 是   |
| POST   | /api/v1/profiles/scan            | 手动触发 Profile 扫描        | 是   |
| GET    | /api/v1/agents/:id/load          | 获取 Agent 负载信息          | 是   |
| POST   | /api/v1/agents/:id/status-report | Agent 主动上报状态变更         | 是   |

### 2.7 QA 门控

| 方法   | 路径                             | 描述            | 认证  |
| ---- | ------------------------------ | ------------- | --- |
| POST | /api/v1/qa/:task_id/inspect    | 提交产出供后荣检验     | 是   |
| GET  | /api/v1/qa/:project_id/records | 获取项目 QA 检验记录  | 是   |
| POST | /api/v1/qa/:task_id/rollback   | 退回重做 (附带修改建议) | 是   |
| GET  | /api/v1/qa/:task_id/status     | 获取当前检验状态      | 是   |
| GET  | /api/v1/qa/:task_id/records    | 获取任务的历次检验记录   | 是   |

### 2.8 Agent 蜂群

| 方法     | 路径                                                   | 描述              | 认证  |
| ------ | ---------------------------------------------------- | --------------- | --- |
| POST   | /api/v1/swarms                                       | 建立 Agent 蜂群     | 是   |
| GET    | /api/v1/swarms                                       | 获取蜂群列表          | 是   |
| GET    | /api/v1/swarms/:id                                   | 获取蜂群详情          | 是   |
| POST   | /api/v1/swarms/:id/tasks/dispatch                    | 分发任务到蜂群成员       | 是   |
| GET    | /api/v1/swarms/:id/progress                          | 获取蜂群执行进度        | 是   |
| DELETE | /api/v1/swarms/:id                                   | 解散蜂群            | 是   |
| GET    | /api/v1/swarms/:swarm_id/tasks/:agent_id             | 蜂群 Agent 获取分配任务 | 是   |
| POST   | /api/v1/swarms/:swarm_id/tasks/:agent_id/acknowledge | 蜂群 Agent 确认接收任务 | 是   |
| POST   | /api/v1/swarms/:swarm_id/tasks/:task_id/progress     | 蜂群 Agent 上报任务进度 | 是   |
| POST   | /api/v1/swarms/:swarm_id/tasks/:task_id/deliver      | 蜂群 Agent 提交任务成果 | 是   |
| POST   | /api/v1/swarms/:swarm_id/tasks/:task_id/error        | 蜂群 Agent 上报执行错误 | 是   |

### 2.9 项目讨论群

| 方法     | 路径                                          | 描述             | 认证  |
| ------ | ------------------------------------------- | -------------- | --- |
| GET    | /api/v1/groups                              | 获取群组列表         | 是   |
| POST   | /api/v1/groups                              | 创建群组 (第二步自动调用) | 是   |
| GET    | /api/v1/groups/:group_id                    | 获取群组详情和成员      | 是   |
| PUT    | /api/v1/groups/:group_id                    | 更新群组信息         | 是   |
| POST   | /api/v1/groups/:group_id/members            | 添加成员           | 是   |
| DELETE | /api/v1/groups/:group_id/members/:member_id | 移除成员           | 是   |
| GET    | /api/v1/groups/:group_id/messages           | 获取历史消息 (分页)    | 是   |
| GET    | /api/v1/groups/:group_id/outcomes           | 获取会议结果列表       | 是   |
| POST   | /api/v1/groups/:group_id/host               | 设置主持人          | 是   |
| PUT    | /api/v1/groups/:group_id/mode               | 切换工作模式 (讨论/会议) | 是   |

### 2.10 Hermes Gateway 通信

| 方法   | 路径                                  | 描述                       | 认证  |
| ---- | ----------------------------------- | ------------------------ | --- |
| GET  | /api/v1/hermes/health               | 检查所有 Hermes Gateway 健康状态 | 是   |
| POST | /api/v1/hermes/chat                 | 与指定 Agent 对话 (非流式)       | 是   |
| POST | /api/v1/hermes/chat/stream          | 与指定 Agent 对话 (流式 SSE)    | 是   |
| POST | /api/v1/hermes/tasks/decompose      | 使用 Hermes Agent 拆解任务     | 是   |
| GET  | /api/v1/hermes/:profile_name/status | 检查指定 Profile 运行状态        | 是   |
| POST | /api/v1/hermes/sync-profiles        | 同步发现 profiles 到数据库       | 是   |

### 2.11 代码仓库管理

| 方法   | 路径                                                         | 描述                 | 认证  |
| ---- | ---------------------------------------------------------- | ------------------ | --- |
| POST | /api/v1/projects/:id/repo/init                             | 初始化代码仓库 (项目创建时自动调用) | 是   |
| GET  | /api/v1/projects/:id/repo                                  | 获取仓库详情             | 是   |
| GET  | /api/v1/projects/:id/repo/branches                         | 获取分支列表             | 是   |
| POST | /api/v1/projects/:id/repo/branches                         | 创建分支               | 是   |
| GET  | /api/v1/projects/:id/repo/pulls                            | 获取 PR 列表           | 是   |
| POST | /api/v1/projects/:id/repo/pulls                            | 创建 Pull Request    | 是   |
| POST | /api/v1/projects/:id/repo/pulls/:number/merge              | 合并 PR              | 是   |
| GET  | /api/v1/projects/:id/repo/commits                          | 获取提交记录             | 是   |
| POST | /api/v1/projects/:id/repo/commit                           | 提交代码 (QA 通过后自动)     | 是   |
| POST | /api/v1/projects/:id/repo/validate-commit                  | 验证提交消息规范           | 是   |
| POST | /api/v1/projects/:id/repo/tag                              | 创建版本标签 (项目完成时)     | 是   |

**V39 修正**: 代码仓库端点路径从独立资源 `/api/v1/repos/*` 改为嵌套在项目管理下的 `/api/v1/projects/:id/repo/*` 格式，与架构 V24 §2.2 代码仓库接口 (`/api/v1/projects/{id}/repo/init` 和 `/repo/commit`) 的 REST 风格保持一致。架构采用嵌套资源路径，体现仓库与项目的归属关系。

### 2.12 通知

| 方法     | 路径                             | 描述       | 认证  |
| ------ | ------------------------------ | -------- | --- |
| GET    | /api/v1/notifications          | 获取用户通知列表 | 是   |
| PUT    | /api/v1/notifications/:id/read | 标记通知已读   | 是   |
| PATCH  | /api/v1/notifications/read-all | 全部标记已读   | 是   |
| DELETE | /api/v1/notifications/:id      | 删除通知     | 是   |

**V41 修正**: 标记已读的 HTTP 方法改为 PUT，与前端 V20 §4.6 markAsRead (PUT /notifications/:id/read) 保持一致。

### 2.13 文件产出物管理

| 方法     | 路径                                               | 描述                            | 认证  |
| ------ | ------------------------------------------------ | ----------------------------- | --- |
| POST   | /api/v1/projects/:id/artifacts/upload            | 上传文档产出物 (multipart/form-data) | 是   |
| GET    | /api/v1/projects/:id/artifacts                   | 列出项目产出物文件列表 (分页)              | 是   |
| GET    | /api/v1/projects/:id/artifacts/:file_id          | 获取文件元信息                       | 是   |
| GET    | /api/v1/projects/:id/artifacts/:file_id/download | 下载产出物文件                       | 是   |
| DELETE | /api/v1/projects/:id/artifacts/:file_id          | 删除产出物文件                       | 是   |

### 2.14 用户设置 (V39 新增)

| 方法     | 路径                       | 描述         | 认证  |
| ------ | ------------------------ | ---------- | --- |
| GET    | /api/v1/settings         | 获取用户设置     | 是   |
| PATCH  | /api/v1/settings         | 更新用户设置     | 是   |

**V39 新增**: 与前端 V19 §4.7 settingStore (api.get('/settings') 和 api.patch('/settings')) 保持一致。

**GET /api/v1/settings** - 获取用户设置

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "theme": "dark",
    "language": "zh-CN",
    "notifications_enabled": true,
    "auto_start_workflow": false
  }
}
```

**PATCH /api/v1/settings** - 更新用户设置

请求体 (所有字段可选):

```json
{
  "theme": "light",
  "language": "en-US"
}
```

成功响应 (200 OK): 返回更新后的 SettingsOut 对象

### 2.15 系统管理

| 方法   | 路径                     | 描述              | 认证    |
| ---- | ---------------------- | --------------- | ----- |
| GET  | /api/v1/system/health  | 系统健康检查 (所有 Gateway) | 是     |
| GET  | /api/v1/system/metrics | Prometheus 指标端点 | 否     |
| GET  | /api/v1/system/stats   | 系统统计信息          | Admin |
| POST | /api/v1/system/backup  | 触发手动备份          | Admin |
| POST | /api/v1/system/migrate | 执行数据迁移          | Admin |

### 2.16 健康检查端点 (V30 新增)

| 方法   | 路径                  | 描述                    | 认证  |
| ---- | ------------------- | --------------------- | --- |
| GET  | /health             | 基础健康检查 (仅应用存活)     | 否   |
| GET  | /health/ready       | 就绪检查 (含依赖服务状态)     | 否   |
| GET  | /health/deep        | 深度检查 (含所有依赖组件详细状态) | 否   |

**GET /health** - 基础健康检查

成功响应 (200 OK):

```json
{
  "status": "ok",
  "timestamp": "2026-06-29T10:00:00Z"
}
```

失败响应 (503 Service Unavailable):

```json
{
  "status": "error",
  "timestamp": "2026-06-29T10:00:00Z"
}
```

**GET /health/ready** - 就绪检查

成功响应 (200 OK):

```json
{
  "status": "ready",
  "components": {
    "database": "ok",
    "redis": "ok",
    "migrations": "ok"
  },
  "timestamp": "2026-06-29T10:00:00Z"
}
```

部分就绪 (200 OK, status=not_ready):

```json
{
  "status": "not_ready",
  "components": {
    "database": "ok",
    "redis": "error",
    "migrations": "pending"
  },
  "detail": "Redis: connection refused; Migrations not applied",
  "timestamp": "2026-06-29T10:00:00Z"
}
```

**GET /health/deep** - 深度检查

成功响应 (200 OK):

```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "ok",
      "latency_ms": 2,
      "pool_active": 5,
      "pool_idle": 15
    },
    "redis": {
      "status": "ok",
      "latency_ms": 1,
      "connected_clients": 42
    },
    "celery": {
      "status": "ok",
      "active_workers": 4,
      "queued_tasks": 2
    },
    "gitea": {
      "status": "ok",
      "latency_ms": 15
    },
    "hermes_gateways": {
      "total": 9,
      "online": 9,
      "offline": 0,
      "details": {
        "haimei": "ok",
        "houxing": "ok",
        "houwang": "ok",
        "houfa": "ok",
        "houda": "ok",
        "houfu": "ok",
        "hougui": "ok",
        "hourong": "ok",
        "houhua": "ok"
      }
    }
  },
  "uptime_seconds": 86400,
  "timestamp": "2026-06-29T10:00:00Z"
}
```

### 2.17 WebSocket 端点

| 端点                              | 用途                 | 认证  |
| ------------------------------- | ------------------ | --- |
| ws://host/ws/group-chat             | 群聊消息实时推送         | 是   |
| ws://host/ws/notifications          | 通知实时推送           | 是   |
| ws://host/ws/workflow/:project_id   | 项目流程状态推送      | 是   |

**V41 修正**: WebSocket 端点改为多连接方案，与前端 V20 §6.1 保持一致。前端采用 3 个独立 WebSocket 端点分别处理群聊消息、通知和项目流程状态推送，不再使用单连接加频道订阅的模式。

**WebSocket 认证流程 (V41 修正)**：

客户端建立 WebSocket 连接后，第一条消息必须为 auth 消息。客户端使用 access_token 进行认证：

```json
{
  "type": "auth",
  "token": "access_token_value"
}
```

**V41 修正**: (1) 认证 token 改为 access_token（直接使用 HTTP 认证的 JWT Token），移除 ws_token 专用方案；(2) auth 响应 type 值改为 auth_success/auth_error，与前端 V20 保持一致。

服务端验证 access_token 后返回：

认证成功:

```json
{
  "type": "auth_success"
}
```

认证失败:

```json
{
  "type": "auth_error",
  "message": "Token 无效或已过期"
}
```

认证通过后方可发送/接收业务消息。

**WebSocket 消息格式**:

多连接方案下，每个 WebSocket 连接仅处理对应类型消息，无需频道订阅。消息格式由各端点独立定义：

- **群聊消息**: 收到新的 group_message 时推送
- **通知消息**: 收到新的 notification 时推送
- **流程状态**: 项目 workflow 状态变更时推送

### 2.18 游标分页规范

游标分页使用场景：大数据量列表、无限滚动、实时流数据。

- **请求格式**: `GET /api/v1/projects/:id/tasks?cursor=***==&limit=20`
- **cursor 编码**: Base64(JSON(`{"id": last_seen_id}`))，客户端将上一页最后一条记录的 ID 编码后传入
- **首次请求**: 不传 cursor 或传 `cursor=0`，返回最前面的 N 条
- **响应格式**:

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "has_more": true,
    "next_cursor": "***==",
    "limit": 20
  }
}
```

- **页码分页 vs 游标分页**: 页码分页适用于固定页码浏览（如管理后台列表），游标分页适用于大数据量场景，避免深度分页性能问题

---

## 3. 服务层设计

### 3.1 服务层架构

服务层是后端的核心业务逻辑层，采用分层架构：

```
路由层 (Routers) → 依赖注入 → 服务层 (Services) → 数据访问层 (Repositories) → 数据库
                                         │
                                         ├──→ Gateway Client → Hermes Agent
                                         ├──→ Celery Tasks → 异步任务队列
                                         ├──→ Redis → 缓存/分布式锁/状态
                                         └──→ Gitea API → 代码仓库
```

V19 服务层拆分说明：
- **流程编排服务 (workflow_orchestrator.py)**: 职责为协调 16 步流程的整体执行，包括步骤调度决策、流程推进判断、跨步骤资源协调。不直接执行步骤，而是委派给步骤执行服务
- **步骤执行服务 (step_executor.py)**: 职责为单个步骤的具体执行，包括 Agent 选择、任务构建、Gateway 调用、结果收集。每个步骤的执行是独立的，不感知其他步骤状态
- **状态机服务 (workflow_statemachine.py)**: 职责为维护流程状态一致性，包括前置条件验证、状态转换合法性检查、并发冲突检测。所有流程状态变更必须通过状态机服务

### 3.2 依赖注入

使用 FastAPI 的 Depends 机制进行依赖注入：
- **数据库会话**: 每个请求创建独立的异步数据库会话，请求结束后自动关闭
- **当前用户**: 从 JWT Token 中提取用户信息，注入到需要认证的路由
- **Redis 客户端**: 全局单例，注入到需要缓存或分布式锁的服务
- **Gateway Client**: 全局单例，注入到需要与 Agent 通信的服务
- **日志记录器**: 按模块注入，包含 trace_id 和请求上下文

### 3.3 事务管理与数据一致性

- **事务管理**: 使用 SQLAlchemy 异步事务管理，关键操作使用事务确保数据一致性
- **事务边界定义**:
  - 项目创建: 包含 project 记录、repo 记录、workflow_progress 初始记录、group 创建、group_members 初始化（原子操作）
  - 流程推进: 包含 workflow_progress 状态更新、task 创建、agent 分配（原子操作）
  - QA 检验结果提交: 包含 qa_record 创建、task 状态更新、workflow_progress 更新、repo 提交（原子操作）
- **PostgreSQL + Redis 双写一致性策略**:
  - 数据库为唯一权威数据源 (source of truth)
  - 写操作: 先写入 PostgreSQL，成功后再更新 Redis 缓存 (write-through)
  - 读操作: 优先读取 Redis 缓存，未命中则回源 PostgreSQL 并回填缓存
  - 缓存失效: 写操作成功后主动失效相关缓存键，避免脏数据
  - 缓存过期: 设置合理 TTL（Agent 状态 5 分钟，流程状态 10 分钟，群组信息 30 分钟）
- **跨服务调用的 Saga 模式**:
  - 当操作涉及多个服务且需要回滚时，采用 Saga 补偿模式
  - 每个步骤定义正向操作和补偿操作 (compensating action)
  - 示例: 项目创建失败时，按相反顺序补偿：删除 group_members → 删除 group → 删除 repo → 删除 project
- **分布式锁设计**:
  - 实现: Redis SETNX + TTL 机制
  - 粒度: 每个项目每个步骤一把锁，键格式 `workflow:lock:{project_id}:{step_number}`
  - TTL: 30 分钟，与 Agent 执行超时阈值一致
  - 死锁预防: 采用固定顺序加锁（先项目级锁，再步骤级锁），避免交叉等待
  - 锁续期: Celery Worker 在执行长时间任务时，每 5 分钟检查并续期锁 TTL
  - 锁释放: 任务完成/失败/超时后自动释放锁，通过 Redis WATCH 保证原子性

### 3.4 状态管理与恢复

- **Redis 状态缓存**: Agent 执行状态、蜂群进度、WebSocket 连接状态等写入 Redis
- **状态一致性保证**: PostgreSQL 为权威数据源，Redis 仅作为缓存层。状态不一致时以 PostgreSQL 为准
- **进程重启后状态恢复**:
  - FastAPI 应用启动时: 从 PostgreSQL 重新加载所有活跃项目的流程状态、Agent 状态到 Redis
  - Celery Worker 启动时: 扫描 Redis 中状态为 `in_progress` 的 Celery 任务，检查对应 Agent 是否仍在执行，若不一致则标记为 `error` 并触发重试
  - WebSocket 连接管理器: 内存数据结构，重启后清空。前端重连后自动恢复订阅状态
- **状态恢复流程**:

```
启动 → 加载活跃项目列表 → 加载每个项目的 workflow_progress
     → 加载 Agent 执行日志 → 重建 Redis 缓存
     → 检查中断的 Agent 任务 → 标记异常状态
     → 通知人类用户异常任务 → 服务就绪
```

### 3.5 服务间通信方式定义

各服务间的调用边界和通信机制：

| 调用类型    | 通信方式              | 适用场景            | 示例                                                |
| ------- | ----------------- | --------------- | ------------------------------------------------- |
| 同步调用    | 直接 Python 方法调用    | 同一请求内的服务协作      | orchestrator → statemachine.validate_transition() |
| 异步任务    | Celery Task       | 长时间运行的 Agent 执行 | orchestrator → Celery → agent_execute_task        |
| 事件推送    | WebSocket         | 实时状态推送给前端       | websocket_service.broadcast_group()               |
| 内部 HTTP | 不适用 (单进程)         | -               | 后端为单体架构，无需内部 HTTP                                 |
| 外部 HTTP | httpx.AsyncClient | 调用外部 API        | gateway_client → Hermes Gateway                   |

**同步/异步边界规则**：
1. 路由层 → 服务层：同步调用（FastAPI 依赖注入）
2. 服务层 → 数据访问层：同步调用（await 异步方法）
3. 服务层 → Celery 任务：异步调用（`.delay()` 或 `.apply_async()`）
4. 服务层 → Gateway 调用：异步调用（通过 gateway_client，受信号量控制）
5. 服务层 → WebSocket 推送：异步调用（通过 ConnectionManager）
6. Celery 任务 → 服务层：同步调用（Worker 进程内直接导入服务）

### 3.6 服务依赖关系图

```
                    ┌─────────────────────┐
                    │ workflow_orchestrator│  ← 流程编排服务 (入口)
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────┬────────────┐
              ▼            ▼            ▼            ▼
       ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
       │step_executor│ │statemachine│ │qa_service│ │repo_service│
       └──────┬─────┘ └──────┬───┘ └────┬─────┘ └────┬─────┘
              │               │          │              │
              ▼               │          │              ▼
       ┌────────────┐        │          │     ┌────────────┐
       │gateway_client│◄─────┘          │     │ Gitea API  │
       └────────────┘                   │     └────────────┘
                                        │
                                        ▼
                                 ┌────────────┐
                                 │gateway_client│ ← 调用 HouRong Agent
                                 └────────────┘

    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │swarm_service│────│gateway_client│────│agent_service│
    └──────────┘     └──────────┘     └──────────┘

    ┌──────────┐     ┌──────────┐
    │group_service│────│websocket_service│
    └──────────┘     └──────────┘

    ┌──────────┐     ┌──────────┐
    │profile_service│──│gateway_client│
    └──────────┘     └──────────┘

    ┌──────────┐     ┌──────────┐
    │notification_service│──│websocket_service│ + Celery (email)
    └──────────┘     └──────────┘
```

### 3.7 服务层调用关系矩阵

16 个服务之间的完整调用关系矩阵。箭头表示调用方向：A → B 表示 A 调用 B。

**核心编排链路**:

```
POST /api/v1/projects/:id/workflow/step/:number
  → workflow_router
  → workflow_orchestrator.execute_step()
      → workflow_statemachine.validate_transition()    [读: workflow_progress]
      → workflow_statemachine.acquire_lock()            [写: Redis SETNX]
      → step_executor.execute()
          → gateway_service.build_context()             [读: project, task, agents]
          → gateway_client.send_message()               [HTTP → Hermes Gateway]
          → task_repo.update_status()                   [写: tasks.status='in_progress']
      → qa_service.inspect()
          → gateway_service.build_qa_context()          [读: artifacts, qa criteria]
          → gateway_client.send_message()               [HTTP → HouRong Agent]
          → qa_repo.create()                            [写: qa_records]
      → 分支决策:
          ├── QA Pass → repo_service.submit_to_gitea()  [HTTP → Gitea API]
          │                  → workflow_statemachine.transition_to_completed()
          │                  → workflow_orchestrator.advance_to_next_step()
          │                  → notification_service.send() [写: notifications + WS push]
          └── QA Fail  → step_executor.retry_with_feedback()
                               → notification_service.send()
```

**服务间调用关系矩阵表**:

| 调用方 ↓ → 被调用方              | gateway_service | agent_service | workflow_statemachine | qa_service | repo_service | swarm_service | notification_service |
| ------------------------- | --------------- | ------------- | --------------------- | ---------- | ------------ | ------------- | -------------------- |
| **workflow_orchestrator** | -               | -             | ✅ 状态验证/推进             | ✅ QA 触发    | ✅ 代码提交       | -             | ✅ 通知推送               |
| **step_executor**         | ✅ Gateway 调用    | ✅ Agent 选择    | ✅ 状态更新                | -          | -            | -             | -                    |
| **swarm_service**         | ✅ Gateway 调用    | ✅ Agent 管理    | -                     | -          | -            | -             | -                    |
| **qa_service**            | ✅ Gateway 调用    | -             | ✅ 状态更新                | -          | ✅ 代码提交       | -             | ✅ 通知推送               |
| **repo_service**          | -               | -             | -                     | -          | -            | -             | -                    |
| **group_service**         | -               | -             | -                     | -          | -            | -             | ✅ 通知推送               |
| **meeting_service**       | ✅ Gateway 调用    | -             | -                     | -          | -            | -             | -                    |
| **profile_service**       | -               | ✅ Agent 注册    | -                     | -          | -            | -             | -                    |
| **websocket_service**     | -               | -             | -                     | -          | -            | -             | -                    |
| **artifact_service**      | -               | -             | -                     | -          | -            | -             | -                    |

**Celery 异步任务调用关系**:

| Celery Task        | 触发方                   | 调用链                                                                  |
| ------------------ | --------------------- | -------------------------------------------------------------------- |
| agent_execute_task | workflow_orchestrator | orchestrator → Celery → gateway_service → gateway_client → Hermes GW |
| swarm_dispatch     | swarm_service         | swarm_service → Celery → agent_service → gateway_service             |
| qa_inspect         | workflow_orchestrator | orchestrator → Celery → qa_service → gateway_service                 |
| gitea_sync         | qa_service            | qa_service → Celery → repo_service → Gitea API                       |
| profile_scan       | Celery Beat           | Beat → Celery → profile_service → 文件系统扫描                             |
| backup_db          | Celery Beat           | Beat → Celery → pg_dump → 文件存储                                       |

### 3.8 长时任务事务边界与失败回滚策略

Agent 执行任务可能长达 30 分钟，期间涉及数据库状态更新、文件产出、Gitea 提交等多步骤操作。本节定义事务边界和回滚策略。

**事务边界定义**:

| 操作阶段       | 事务范围                                | 隔离级别           | 失败策略               |
| ---------- | ---------------------------------- | -------------- | ------------------ |
| 步骤启动       | workflow_progress 状态更新 + task 创建    | READ COMMITTED | 事务回滚，状态恢复为 pending |
| Agent 执行中  | 无数据库事务（纯远程调用）                       | -              | 超时则硬终止，状态标记为 error |
| 执行结果保存     | task 结果写入 + workflow_progress 更新    | READ COMMITTED | 事务回滚，状态恢复为 in_progress |
| QA 检验提交    | qa_record 创建 + workflow_progress 更新 | READ COMMITTED | 事务回滚，状态恢复为 in_progress |
| Gitea 代码提交 | 独立 HTTP 调用，非数据库事务                   | -              | 失败则产出暂存本地，定时重试     |
| 流程状态推进     | workflow_progress 状态转换              | READ COMMITTED | 事务回滚，保持原状态         |

**Saga 补偿模式（跨服务操作回滚）**:

```
正向操作: 步骤执行 → QA 检验 → Gitea 提交 → 流程推进
           (A)        (B)        (C)          (D)

补偿操作（从失败点逆向回滚）:

若 A 失败（步骤启动失败）:
  → 无需补偿，事务回滚即可

若 B 失败（QA 检验失败）:
  → 补偿 C1: 回退 workflow_progress 到 'qa_failed'
  → 触发 retry_with_feedback()，附带 problem_details

若 C 失败（Gitea 提交失败）:
  → 补偿 C2: 产出文件暂存到 /data/devflow/pending/{project_id}/{step}/
  → 标记 workflow_progress.result_summary.gitea_status = 'pending_retry'
  → Celery 定时任务每 5 分钟重试，最多 3 次

若 D 失败（流程推进失败）:
  → 补偿 D1: 保持当前步骤 completed 状态
  → 记录错误到 audit_logs，通知人类用户手动介入
```

**分布式锁与数据库事务的配合**:

```python
async def execute_step_safely(self, project_id: int, step_number: int):
    # 1. 先获取分布式锁（Redis SETNX），防止并发冲突
    lock_key = f"workflow:lock:{project_id}:{step_number}"
    acquired = await self.redis.set(lock_key, "1", nx=True, ex=1800)
    if not acquired:
        raise WorkflowError("该步骤已在执行中", code=409)

    try:
        # 2. 在数据库事务内更新状态
        async with self.db.begin():
            await self.statemachine.validate_transition(project_id, step_number)
            await self.statemachine.transition_to(project_id, step_number, "in_progress")

        # 3. 执行 Agent 任务（可能长达 30 分钟，不在事务内）
        result = await self.step_executor.execute(project_id, step_number)

        # 4. 在数据库事务内保存结果
        async with self.db.begin():
            await self.statemachine.transition_to(project_id, step_number, "qa_pending")
            await self.task_repo.save_result(task_id, result)

        # 5. 提交 QA 检验（异步 Celery 任务，不在事务内）
        await self.celery.qa_inspect.delay(project_id, step_number, result)

    except Exception as e:
        # 6. 异常补偿
        await self.handle_failure(project_id, step_number, e)
        raise
    finally:
        # 7. 无论成功失败，释放分布式锁
        await self.redis.delete(lock_key)
```

**死锁预防机制**:

| 策略      | 实现方式                       | 说明              |
| ------- | -------------------------- | --------------- |
| 固定顺序加锁  | 先项目级锁，再步骤级锁，再任务级锁          | 避免交叉等待导致的死锁     |
| 锁超时自动释放 | Redis SETNX + TTL (30 分钟)  | 防止锁持有者崩溃后锁永远不释放 |
| 锁续期机制   | Celery Worker 每 5 分钟续期 TTL | 长时任务不会因锁超期中断    |
| 无锁读策略   | 读操作不使用排他锁                  | 减少锁竞争，避免读写死锁    |
| 死锁检测    | 定期检查 Redis 中超过 25 分钟未释放的锁  | 触发告警并强制释放       |

**蜂群并发隔离策略**:

| 隔离维度         | 实现方式                                                              | 说明                             |
| ------------ | ----------------------------------------------------------------- | ------------------------------ |
| 文件系统隔离       | 每个蜂群 Agent 独立工作目录 `/data/devflow/swarms/{project_id}/{agent_id}/` | Agent 间文件不互相干扰                 |
| 数据库隔离        | 行级锁 + 乐观锁（version 字段）                                             | 更新 tasks/workflow_progress 时使用 |
| Gateway 调用隔离 | 每个蜂群 Agent 复用全局 GatewayClient 连接池                                 | 受总信号量（5）+ profile 互斥锁控制        |
| Redis 状态隔离   | 每个蜂群独立的 Redis 键空间 `swarm:{swarm_id}:*`                            | 进度、状态不互相覆盖                     |
| 资源竞争处理       | Gitea 提交使用分布式锁 `repo:lock:{project_id}:{branch}`                  | 防止多 Agent 同时提交到同一分支            |

### 3.9 业务异常场景处理与 step_events 表 (V39 修正)

V39 修正：架构 V24 §3.9 定义了 step_events 表用于分布式一致性事件记录，V37 缺少对应表定义。V39 新增 step_events 表及相关服务，与架构保持一致。

**step_events 表设计**:

| 字段            | 类型           | 约束                      | 说明                                                    |
| ------------- | ------------ | ----------------------- | ----------------------------------------------------- |
| id            | BIGSERIAL    | PRIMARY KEY             | 事件 ID                                                 |
| project_id    | BIGINT       | NOT NULL, FK→projects.id | 项目 ID                                                 |
| step_number   | SMALLINT     | NOT NULL                 | 步骤编号 (1-16)                                            |
| event_type    | VARCHAR(50)  | NOT NULL                 | 事件类型 (step_started/step_completed/qa_passed/qa_failed/rollback 等) |
| actor_type    | VARCHAR(20)  | NOT NULL                 | user/agent/system                                      |
| actor_id      | BIGINT       |                          | 操作者 ID                                                |
| before_state  | JSONB        |                          | 状态变更前的快照                                           |
| after_state   | JSONB        |                          | 状态变更后的快照                                           |
| details       | JSONB        |                          | 事件详细信息                                               |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()  | 事件时间                                                  |

索引: `idx_se_project_step`, `idx_se_event_type`, `idx_se_time`

说明：step_events 用于记录 16 步流程中的关键状态变更事件，支持分布式环境下的最终一致性校验和审计追踪。与 audit_logs 的区别：audit_logs 记录系统级操作审计（登录、权限变更等），step_events 专注于流程步骤的状态变更事件。

**场景 1: Agent 执行失败**

```
步骤: Agent 执行 → 失败
处理:
1. 记录执行日志到 agent_execution_logs (action='failed')
2. 记录 step_events (event_type='step_failed')
3. 更新 workflow_progress.status = 'failed'
4. 检查重试次数:
   - 重试次数 < 3: 自动重试 (指数退避: 30s/60s/120s)
   - 重试次数 = 3: 触发备用 Agent 切换
5. 备用 Agent 不可用: 通知人类用户，暂停任务
6. WebSocket 推送失败事件到前端
```

**场景 2: 蜂群崩溃**

```
步骤: 蜂群执行中 → 一个或多个成员崩溃
处理:
1. 检测机制: Celery 任务超时 (30 分钟) 或主动心跳超时 (5 分钟)
2. 标记崩溃 Agent 为 'offline' 状态
3. 蜂群管理器 (后发/后达) 评估:
   - 剩余成员能否完成任务: 重新分配崩溃成员的任务
   - 剩余成员不足: 启动新的 Agent 加入蜂群
4. 蜂群全部崩溃: 标记蜂群为 'failed'，通知海梅介入
5. 蜂群解散: 清理临时文件，释放资源
```

**场景 3: QA 检验不通过**

```
步骤: QA 检验 → 不合格
处理:
1. 记录 qa_records (acceptance_result='fail', review_round=N)
2. 记录 step_events (event_type='qa_failed')
3. 更新 workflow_progress.status = 'qa_failed'
4. 检查轮次:
   - review_round < 3: 退回重做 (step_executor.retry_with_feedback)
   - review_round = 3: 海梅介入，在讨论群中协调处理
5. 24 小时时限:
   - 限时内完成: 重新提交 QA 检验
   - 超时: 海梅介入，通知人类用户
6. WebSocket 推送 QA 结果到前端
```

**场景 4: Gateway 不可用**

```
步骤: 调用 Gateway → 连接失败
处理:
1. 记录到 agent_execution_logs (action='escalated')
2. 标记该 Agent 为 'offline' 状态
3. 触发熔断机制 (连续 3 次失败):
   - 熔断窗口: 5 分钟，期间不接受新任务
   - 半开状态: 5 分钟后发送探测请求
4. 所有 Gateway 不可用: 返回 503，通知系统管理员
5. 降级: 新任务排队等待，已执行任务尝试恢复
```

**场景 5: Redis 故障**

```
步骤: 依赖 Redis → 连接失败
处理:
1. 降级: 回退到直接查数据库，禁用缓存
2. 分布式锁: 使用数据库行级锁替代 Redis SETNX
3. 会话管理: 使用数据库 session 表替代 Redis 缓存
4. 告警: WebSocket + 邮件通知系统管理员
5. 恢复: Redis 重连成功后自动重建缓存
```

**场景 6: Gitea 不可用**

```
步骤: 提交代码到 Gitea → 失败
处理:
1. 产出暂存到 /data/devflow/pending/{project_id}/{step}/
2. 标记 gitea_status = 'pending_retry'
3. Celery 定时任务每 5 分钟重试，最多 3 次
4. 3 次均失败: 通知人类用户，保留本地产出
5. 恢复后自动补提交
```

### 3.10 16步标准开发流程流程图 (V33 新增)

以下流程图展示 DevFlow 16 步标准开发流程的完整流转，包括每个步骤的负责 Agent、QA 门控触发点、蜂群建立时机和回退路径。

**16步流程总览**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DevFlow 16步标准开发流程 - 完整流转图                      │
└─────────────────────────────────────────────────────────────────────────────┘

 Step   步骤名称               负责Agent       QA门控       蜂群建立     代码提交
 ----   --------               ---------       ------       --------     --------
  1  →  人类用户创建项目       人类用户         ✗ 无需QA     -            -
         │
  2  →  需求分析               HouXing         ✓ HouRong    -            -
         │
  3  →  软件架构设计           HouWang         ✓ HouRong    -            -
         │
  4  →  数据库设计             HouWang         ✓ HouRong    -            -
         │
  5  →  后端设计               HouWang         ✓ HouRong    -            -
         │
  6  →  前端设计               HouWang         ✓ HouRong    -            -
         │
  7  →  建立开发环境           HouFu           ✓ HouRong    -            -
         │
  8  →  TDD测试用例编写        HouFa           ✓ HouRong    ⚡建立        -
         │                                       编程蜂群
  9  →  代码编写               HouFa           ✓ HouRong    编程蜂群     ✓ Gitea
         │
  10 →  测试验证               HouDa           ✓ HouRong    ⚡建立        ✓ Gitea
         │                                       测试蜂群
  11 →  安全审计               HouHua          ✓ HouRong    -            -
         │
  12 →  代码部署               HouFu           ✓ HouRong    -            -
         │
  13 →  文档管理               HouGui          ✓ HouRong    -            ✓ Gitea
         │
  14 →  集成测试               HouDa           ✓ HouRong    -            ✓ Gitea
         │
  15 →  系统测试               HouDa           ✓ HouRong    -            -
         │
  16 →  项目交付               HaiMei          ✓ HouRong    -            -
         │
  [完成]  项目归档
```

**QA门控流转逻辑**:

```
  Agent执行完成 → 提交 HouRong 检验 → 记录 qa_records
      │
      ├─ 检验合格(score≥80) → 提交 Gitea → 进入下一步
      │
      └─ 检验不合格 → 退回重做
          │
          ├─ review_round < 3 → 附带 problem_details 重新执行
          │
          └─ review_round = 3 → HaiMei 介入协调 → 通知人类用户
```

**蜂群建立与解散时机**:

| 步骤 | 蜂群类型   | 建立者 | 说明                                    | 解散条件              |
| ---- | -------- | ---- | ------------------------------------- | ------------------- |
| 第8步  | 编程蜂群   | HouFa | 拆解TDD测试任务，分发到编程Agent并行执行       | 第8步QA通过后解散         |
| 第9步  | 编程蜂群   | HouFa | 基于测试用例编写实现代码                      | 第9步QA通过后解散         |
| 第10步 | 测试蜂群   | HouDa | 执行单元/模块/集成测试，各Agent提交测试报告      | 第10步QA通过后解散        |

蜂群临时文件目录: `/data/devflow/swarms/{project_id}/{swarm_id}/`

**回退路径**:

```
任意步骤 → POST /api/v1/projects/:id/workflow/rollback
    → 请求体: { "target_step": N, "reason": "..." }
    → 回退到 target_step
    → target_step 之后的所有步骤状态重置为 pending
    → 重新执行从 target_step 开始
    → 回退记录到 audit_logs (event_type='workflow_rollback')
    → 同时记录 step_events (event_type='rollback')
```

**状态转换总览**:

```
pending → in_progress → qa_pending → qa_passed → completed
                                       ↓
                                    qa_failed → pending (重试)
                                                  │
                                              retry_count≥3 → failed
```

---

## 4. Pydantic Schema 定义

本节定义所有 API 请求/响应使用的 Pydantic 数据模型。

### 4.1 统一错误响应 Schema (V30 新增)

```python
class ErrorResponse(BaseModel):
    """统一错误响应格式"""
    success: bool = False
    error: str                          # 简短错误描述
    code: int                           # HTTP 状态码
    business_code: int                  # 业务错误码 (5 位数字)
    detail: Optional[str] = None        # 详细错误信息
    trace_id: str                       # 链路追踪 ID

class ErrorDetail(BaseModel):
    """验证错误详情"""
    field: str
    message: str
    type: str
```

### 4.2 用户 Schema (schemas/user.py)

```python
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str                          # V41 修正: user/admin，与数据库 V33 枚举一致
    is_active: bool
    created_at: datetime
    updated_at: datetime

class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: str = Field(..., pattern=r'^[^\\s]+@[^\\s]+\\.[^\\s]+$')

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int

class UserLoginResponse(TokenResponse):
    user: UserOut

class WsTokenRequest(BaseModel):
    """V39 新增: WebSocket Token 请求"""
    pass  # 从当前用户的 Access Token 中派生 ws_token，无需额外请求体

class WsTokenResponse(BaseModel):
    """V39 新增: WebSocket Token 响应"""
    ws_token: str
    expires_in: int = 900
```

**V41 修正**: UserOut.role 枚举值改为 user/admin，与数据库 V33 §1.3 user_role 枚举保持一致（已移除 system_admin）。

### 4.3 项目 Schema (schemas/project.py)

```python
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)

class ProjectUpdate(BaseModel):
    """V39 修正: 配合 PATCH 方法，所有字段可选（部分更新）"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)

class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    creator_id: int
    current_step: int
    status: str                        # V39 修正: created/in_progress/completed/cancelled
    gitea_repo_id: Optional[int]
    deleted_at: Optional[datetime]     # V39 新增: 对应数据库 projects.deleted_at 软删除字段
    created_at: datetime
    updated_at: datetime

class ProjectProgressOut(BaseModel):
    project_id: int
    current_step: int
    steps: List[StepProgressOut]

class StepProgressOut(BaseModel):
    step_number: int
    step_name: str
    status: str
    assigned_agent: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

**V39 修正**: (1) ProjectOut 新增 deleted_at 字段 (Optional[datetime])，对应数据库 V30 §3.1 projects 表 deleted_at 软删除字段；(2) status 枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致；(3) ProjectUpdate 配合 PATCH 方法使用。

### 4.4 Agent Schema (schemas/agent.py)

```python
class AgentOut(BaseModel):
    id: int
    name: str
    profile_name: str
    role: str
    status: str                        # V39 修正: idle/busy/error/offline
    is_named: bool
    current_load: float
    max_concurrent: int
    last_heartbeat: Optional[datetime]

class AgentStatusReport(BaseModel):
    status: str = Field(..., pattern=r'^(online|offline|busy)$')   # V39 修正: idle/busy/error/offline
    current_task_id: Optional[int] = None
    message: Optional[str] = None

class AgentLoadOut(BaseModel):
    agent_id: int
    profile_name: str
    current_load: float
    active_tasks: int
    max_concurrent: int
    queue_length: int

class AgentRegisterRequest(BaseModel):
    name: str
    skills: List[str]
    capabilities: Dict[str, Any]

class ProfileScanOut(BaseModel):
    profile_name: str
    is_running: bool
    gateway_port: Optional[int]
    config_path: str
    last_scanned: datetime
```

**V39 修正**: (1) AgentOut.status 枚举值改为 idle/busy/error/offline，与数据库 V30 agent_status 枚举保持一致（原 V37 使用 idle/busy/error/offline 四值）；(2) AgentStatusReport.status 正则模式改为 `^(online|offline|busy)$`。

### 4.5 任务 Schema (schemas/task.py)

```python
class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=10000)
    step_number: int = Field(..., ge=1, le=16)
    acceptance_criteria: Optional[str] = None
    priority: int = Field(5, ge=1, le=10)
    estimated_hours: Optional[Decimal] = None

class TaskUpdate(BaseModel):
    """V39 修正: 配合 PATCH 方法"""
    status: Optional[str] = Field(None, pattern=r'^(pending|in_progress|completed|failed|cancelled)$')
    priority: Optional[int] = Field(None, ge=1, le=10)

class TaskOut(BaseModel):
    id: int
    project_id: int
    step_number: int
    name: str
    description: str
    status: str
    assigned_agent_id: Optional[int]
    acceptance_criteria: Optional[str]
    priority: int
    estimated_hours: Optional[Decimal]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class TaskBatchUpdateRequest(BaseModel):
    task_ids: List[int] = Field(..., min_length=1)
    status: str = Field(..., pattern=r'^(pending|in_progress|completed|failed|cancelled)$')

class TaskBatchUpdateResponse(BaseModel):
    updated: int
    failed: List[Dict[str, Any]]
    message: str

class TaskDependencyOut(BaseModel):
    id: int
    source_task_id: int
    target_task_id: int
    is_active: bool

class TaskDependencyCreate(BaseModel):
    source_task_id: int
    target_task_id: int
```

### 4.6 QA 门控 Schema (schemas/qa.py)

```python
class QAInspectRequest(BaseModel):
    artifacts: List[Dict[str, Any]]
    output_content: str
    step_number: int = Field(..., ge=1, le=16)

class QARecordOut(BaseModel):
    id: int
    task_id: int
    project_id: int
    step_number: int
    reviewer_agent_id: int
    review_dimensions: List[Dict[str, Any]]
    score: Decimal
    acceptance_result: str
    problem_details: Optional[str]
    review_round: int
    created_at: datetime

class QARollbackRequest(BaseModel):
    problem_details: str = Field(..., min_length=1, max_length=10000)
    review_dimensions: List[Dict[str, Any]]
    score: Decimal = Field(..., ge=0, le=100)
```

### 4.7 蜂群 Schema (schemas/swarm.py)

```python
class SwarmCreate(BaseModel):
    project_id: int
    step_number: int = Field(..., ge=1, le=16)
    purpose: str  # swarm_purpose 枚举: tdd_test / code_writing / testing

class SwarmOut(BaseModel):
    id: int
    project_id: int
    step_number: int
    manager_agent_id: int              # V39 修正: 对应数据库 swarms.manager_agent_id INTEGER NOT NULL
    status: str
    task_count: int
    completed_count: int
    agents: List[SwarmAgentOut]
    created_at: datetime
    dissolved_at: Optional[datetime]  # V37 新增: 对应数据库 swarms.dissolved_at TIMESTAMPTZ NULLABLE

class SwarmAgentOut(BaseModel):
    agent_id: int
    agent_name: str
    status: str
    assigned_task_id: Optional[int]

class SwarmTaskDispatch(BaseModel):
    tasks: List[Dict[str, Any]]

class SwarmTaskProgress(BaseModel):
    task_id: int
    progress_percent: int = Field(..., ge=0, le=100)
    status: str
    message: str

class SwarmTaskDelivery(BaseModel):
    task_id: int
    status: str = "completed"
    artifacts: Dict[str, Any]
    self_test_result: Optional[Dict[str, int]]

class SwarmTaskError(BaseModel):
    task_id: int
    error_type: str
    error_message: str
```

**V39 修正**: SwarmOut.manager_agent_id 类型从 Optional[int] 改回 int (NOT NULL)，与数据库 V30 第1条变更记录一致：V30 已恢复 NOT NULL 并移除 ON DELETE SET NULL。说明：数据库 V30 明确声明 swarms.manager_agent_id 为 NOT NULL 且无 ON DELETE SET NULL 约束。

### 4.8 讨论群 Schema (schemas/group.py)

```python
class GroupCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    mode: str = Field("discussion", pattern=r"^(discussion|meeting)$")

class GroupOut(BaseModel):
    id: int
    project_id: int
    name: str
    mode: str
    host_agent_id: Optional[int]
    members: List[GroupMemberOut]
    created_at: datetime

class GroupMemberOut(BaseModel):
    id: int
    user_id: Optional[int]            # V39 修正: NULL 表示 Agent 成员
    agent_name: Optional[str]         # V39 修正: NULL 表示人类用户成员
    joined_at: datetime

class GroupMemberAdd(BaseModel):
    is_agent: bool                    # V39 修正: 使用 is_agent 标志区分用户/Agent
    user_id: Optional[int]            # 人类用户时必填
    agent_name: Optional[str]         # Agent 时必填

class GroupMessageOut(BaseModel):
    id: int
    group_id: int
    sender_type: str                  # V39 修正: user/agent（与数据库 V30 一致）
    sender_id: Optional[int]          # V39 修正: 统一为 sender_id（用户或 Agent ID）
    sender_agent_name: Optional[str]  # V39 修正: 新增，当 sender_type='agent' 时记录 Agent 名称
    content: str
    message_type: str  # message_type_enum 枚举: text/system/meeting
    role: Optional[str]
    is_streaming: bool = False
    metadata: Optional[Dict[str, Any]] = None
    mentions: Optional[Dict[str, Any]]     # V39 修正: 对应数据库 JSONB 字段
    created_at: datetime

class GroupModeUpdate(BaseModel):
    mode: str = Field(..., pattern=r"^(discussion|meeting)$")
```

**V39 修正**:
1. **GroupMemberOut/GroupMemberAdd**: 采用架构 V24 §3.5 的双字段设计：user_id(NULL=Agent) + agent_name(NULL=人类用户)，替代 V37 的 member_type + member_id 三选一方案
2. **GroupMessageOut.sender_type**: 枚举值改为 user/agent（二值），与数据库 V30 §1.3 sender_type 枚举保持一致（原 V37 使用 user/agent/system 三值）
3. **GroupMessageOut.sender_id**: 统一为 sender_id，配合 sender_type 区分人类用户和 Agent
4. **GroupMessageOut.sender_agent_name**: 新增字段，当 sender_type='agent' 时记录 Agent 名称，与架构 V24 §3.5 定义一致
5. **GroupMessageOut.mentions**: 类型改为 Optional[Dict[str, Any]]，对应数据库 V30 JSONB 字段（V30 变更日志第1条明确声称已将 mentions 从 TEXT[] 改为 JSONB）

### 4.9 代码仓库 Schema (schemas/repo.py)

```python
class RepoOut(BaseModel):
    id: int
    project_id: int
    gitea_repo_id: int
    gitea_repo_name: str
    default_branch: str
    is_private: bool
    created_at: datetime

class BranchOut(BaseModel):
    name: str
    commit: Dict[str, str]
    protected: bool

class PullRequestOut(BaseModel):
    number: int
    title: str
    head: str
    base: str
    state: str
    created_at: datetime
    merged_at: Optional[datetime]

class CommitOut(BaseModel):
    sha: str
    message: str
    author: str
    timestamp: datetime

class RepoInitRequest(BaseModel):
    """V39 新增: 初始化代码仓库请求"""
    name: str = Field(..., min_length=1, max_length=255)
    is_private: bool = True
    default_branch: str = "main"

class CommitRequest(BaseModel):
    """V39 新增: 代码提交请求"""
    branch: str
    message: str = Field(..., min_length=1, max_length=255)
    files: List[Dict[str, Any]]
```

### 4.10 通知 Schema (schemas/notification.py)

```python
class NotificationOut(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int]
    type: str
    title: str
    content: str
    is_read: bool
    created_at: datetime
```

### 4.11 会议 Schema (schemas/meeting.py)

```python
class MeetingOutcomeOut(BaseModel):
    id: int
    group_id: int
    meeting_type: str
    meeting_topic: str
    host_agent_id: int
    agenda: List[Dict[str, Any]]
    summary: Optional[str]
    decisions: Optional[List[Dict[str, Any]]]
    action_items: Optional[List[Dict[str, Any]]]
    risks: Optional[List[Dict[str, Any]]]
    started_at: datetime
    completed_at: Optional[datetime]
```

### 4.12 分页 Schema (schemas/pagination.py)

```python
class PagePaginationRequest(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)

class CursorPaginationRequest(BaseModel):
    cursor: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)

class PaginationInfo(BaseModel):
    has_more: bool
    next_cursor: Optional[str] = None
    limit: int
    total: Optional[int] = None

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationInfo
```

### 4.13 文件产出物 Schema (schemas/artifact.py)

```python
class ArtifactOut(BaseModel):
    id: int
    project_id: int
    file_name: str
    storage_path: str         # V37 新增: 对应数据库 artifacts.storage_path VARCHAR(1000) NOT NULL
    file_size: int
    mime_type: str
    uploaded_by: str
    uploader_type: str
    checksum: str
    created_at: datetime

class ArtifactUploadResponse(BaseModel):
    id: int
    file_name: str
    stored_name: str
    file_size: int
    mime_type: str
    checksum: str
    download_url: str
```

### 4.14 健康检查 Schema (V30 新增)

```python
class HealthResponse(BaseModel):
    status: str  # "ok" / "error"
    timestamp: datetime

class ReadinessResponse(BaseModel):
    status: str  # "ready" / "not_ready"
    components: Dict[str, str]  # database: "ok"/"error", redis: "ok"/"error", etc.
    detail: Optional[str] = None
    timestamp: datetime

class DeepHealthResponse(BaseModel):
    status: str  # "healthy" / "degraded" / "unhealthy"
    components: Dict[str, Dict[str, Any]]  # 详细组件状态
    uptime_seconds: int
    timestamp: datetime
```

### 4.15 审计日志 Schema (V30 新增)

```python
class AuditLogOut(BaseModel):
    id: int
    event_type: str
    actor_type: str
    actor_id: Optional[int]
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

class AuditLogFilter(BaseModel):
    event_type: Optional[str] = None
    actor_type: Optional[str] = None
    actor_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1, le=200)
```

### 4.16 用户设置 Schema (V39 新增)

```python
class SettingsOut(BaseModel):
    theme: str = "dark"
    language: str = "zh-CN"
    notifications_enabled: bool = True
    auto_start_workflow: bool = False

class SettingsUpdate(BaseModel):
    theme: Optional[str] = Field(None, pattern=r'^(light|dark|auto)$')
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    auto_start_workflow: Optional[bool] = None
```

**V39 新增**: 支持前端 V19 §4.7 settingStore 的 api.get('/settings') 和 api.patch('/settings') 调用。

### 4.17 步骤事件 Schema (V39 新增)

```python
class StepEventOut(BaseModel):
    id: int
    project_id: int
    step_number: int
    event_type: str
    actor_type: str
    actor_id: Optional[int]
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    details: Optional[Dict[str, Any]]
    created_at: datetime
```

**V39 新增**: 对应架构 V24 §3.9 定义的 step_events 表，用于分布式一致性事件记录。

---

## 5. 数据库表结构设计

### 5.1 ER 图 (ASCII)

```
┌──────────┐     ┌───────────────┐     ┌──────────────────┐
│  users   │────<│   projects    │────<│ workflow_progress│
└──────────┘     └───────────────┘     └──────────────────┘
                       │                       │
                       │ 1:N                  │ 1:N
                       ▼                       ▼
                  ┌──────────┐          ┌──────────┐
                  │repositories│         │  tasks   │
                  └──────────┘          └──────────┘
                                            │
                                            │ 1:N
                                            ▼
                                     ┌────────────────┐
                                     │task_dependencies│
                                     └────────────────┘
                       │
                       │ 1:N
                       ▼
                  ┌──────────┐     ┌────────────────┐
                  │  groups  │────<│ group_members  │
                  └──────────┘     └────────────────┘
                       │
                       │ 1:N
                       ▼
                  ┌───────────────┐
                  │group_messages │
                  └───────────────┘

┌──────────┐     ┌──────────┐     ┌────────────┐
│ workflow │────<│  agents  │     │  swarms    │
│  _steps  │     └──────────┘     └────────────┘
│ (config) │                      │  1:N       │
└──────────┘                      ▼
                          ┌──────────────┐
                          │swarm_agents  │
                          └──────────────┘

┌──────────┐     ┌──────────────┐
│  tasks   │────<│  qa_records  │
└──────────┘     └──────────────┘

┌──────────┐     ┌─────────────────────┐
│  users   │────<│  notifications      │
└──────────┘     └─────────────────────┘

┌──────────┐     ┌───────────────────┐
│  groups  │────<│ meeting_outcomes  │
└──────────┘     └───────────────────┘
                       │
                       │ 1:N
                       ▼
                  ┌────────────┐
                  │meeting_agendas│
                  └────────────┘

┌──────────┐     ┌─────────────────────┐
│  tasks   │────<│agent_execution_logs │
└──────────┘     └─────────────────────┘

┌──────────┐     ┌──────────┐
│ projects │────<│artifacts │
└──────────┘     └──────────┘

┌──────────┐     ┌──────────────┐  (V30 新增)
│  system  │────<│ audit_logs   │
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐  (V39 新增)
│ projects │────<│ step_events  │
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐  (V33 新增)
│ projects │────<│project_members│
└──────────┘     └──────────────┘
```

### 5.2 表定义

#### 5.2.1 users

| 字段            | 类型           | 约束                       | 说明             |
| ------------- | ------------ | ------------------------ | -------------- |
| id            | BIGSERIAL    | PRIMARY KEY              | 用户 ID          |
| username      | VARCHAR(64)  | UNIQUE, NOT NULL         | 用户名            |
| email         | VARCHAR(255) | UNIQUE, NOT NULL         | 邮箱             |
| password_hash | VARCHAR(255) | NOT NULL                 | bcrypt 哈希密码    |
| role          | VARCHAR(20)  | NOT NULL, DEFAULT 'user' | 角色: user/admin/system_admin |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()  | 创建时间           |
| updated_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()  | 更新时间           |
| is_active     | BOOLEAN      | NOT NULL, DEFAULT true   | 是否激活           |

**V39 修正**: role 枚举值改为 user/admin/system_admin，与数据库 V30 user_role 枚举保持一致。

索引: `idx_users_username`, `idx_users_email`

#### 5.2.2 projects

| 字段            | 类型           | 约束                         | 说明                                   |
| ------------- | ------------ | -------------------------- | ------------------------------------ |
| id            | BIGSERIAL    | PRIMARY KEY                | 项目 ID                                |
| name          | VARCHAR(200) | NOT NULL                   | 项目名称                                 |
| description   | TEXT         |                            | 项目描述                                 |
| creator_id    | BIGINT       | NOT NULL, FK→users.id      | 项目创建者                                |
| current_step  | SMALLINT     | NOT NULL, DEFAULT 1        | 当前流程步骤 (1-16)                        |
| status        | VARCHAR(20)  | NOT NULL, DEFAULT 'created'| 状态: created/in_progress/completed/cancelled |
| gitea_repo_id | INTEGER      |                            | Gitea 仓库 ID                          |
| deleted_at    | TIMESTAMPTZ  | NULLABLE                   | 软删除时间 (V39 新增)                      |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()    | 创建时间                                 |
| updated_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()    | 更新时间                                 |

**V39 修正**: (1) 新增 deleted_at 字段 (TIMESTAMPTZ NULLABLE)，与数据库 V30 §3.1 projects 表 deleted_at 软删除字段保持一致；(2) status 枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致。

索引: `idx_projects_creator_id`, `idx_projects_status`, `idx_projects_created_at`, `idx_projects_deleted_at`

#### 5.2.3 workflow_progress

| 字段             | 类型          | 约束                       | 说明                                                                 |
| -------------- | ----------- | ------------------------ | ------------------------------------------------------------------ |
| id             | BIGSERIAL   | PRIMARY KEY              | 记录 ID                                                              |
| project_id     | BIGINT      | NOT NULL, FK→projects.id | 项目 ID                                                              |
| step_number    | SMALLINT    | NOT NULL                 | 步骤编号 (1-16)                                                        |
| status         | VARCHAR(20) | NOT NULL                 | pending/in_progress/qa_pending/qa_passed/qa_failed/completed/cancelled |
| assigned_agent | VARCHAR(50) |                          | 负责 Agent Profile 名称                                                |
| started_at     | TIMESTAMPTZ |                          | 开始时间                                                               |
| completed_at   | TIMESTAMPTZ |                          | 完成时间                                                               |
| qa_record_id   | BIGINT      | FK→qa_records.id         | 关联 QA 检验记录                                                         |
| result_summary | JSONB       |                          | 步骤执行结果摘要                                                           |
| created_at     | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | 创建时间                                                               |

索引: `idx_wp_project_step`, `idx_wp_status`, UNIQUE: `(project_id, step_number)`

#### 5.2.4 agents

| 字段             | 类型           | 约束                            | 说明                      |
| -------------- | ------------ | ----------------------------- | ----------------------- |
| id             | BIGSERIAL    | PRIMARY KEY                   | Agent ID                |
| name           | VARCHAR(100) | UNIQUE, NOT NULL              | Agent 名称                |
| profile_name   | VARCHAR(50)  | UNIQUE, NOT NULL              | Hermes Profile 名称       |
| role           | VARCHAR(50)  | NOT NULL                      | 角色描述                    |
| gateway_host   | VARCHAR(255) | NOT NULL, DEFAULT '127.0.0.1' | Gateway 地址              |
| gateway_port   | INTEGER      | NOT NULL                      | Gateway 端口              |
| status         | VARCHAR(20)  | NOT NULL, DEFAULT 'online'    | idle/busy/error/offline     |
| is_named       | BOOLEAN      | NOT NULL, DEFAULT false       | 是否为命名 Agent             |
| skills         | JSONB        |                               | 技能列表                    |
| current_load   | FLOAT        | NOT NULL, DEFAULT 0           | 当前负载 (0-1)              |
| max_concurrent | SMALLINT     | NOT NULL, DEFAULT 1           | 最大并发数                   |
| last_heartbeat | TIMESTAMPTZ  |                               | 最后心跳时间                  |
| created_at     | TIMESTAMPTZ  | NOT NULL, DEFAULT now()       | 创建时间                    |
| updated_at     | TIMESTAMPTZ  | NOT NULL, DEFAULT now()       | 更新时间                    |

**V39 修正**: status 枚举值改为 idle/busy/error/offline，默认值改为 'online'，与数据库 V30 agent_status 枚举保持一致。

索引: `idx_agents_profile_name`, `idx_agents_status`, `idx_agents_is_named`

#### 5.2.5 workflow_steps (配置表)

| 字段               | 类型           | 约束                        | 说明                 |
| ---------------- | ------------ | ------------------------- | ------------------ |
| id               | BIGSERIAL    | PRIMARY KEY               | 配置 ID              |
| step_number      | SMALLINT     | NOT NULL                  | 步骤编号 (2-16)        |
| step_name        | VARCHAR(255) | NOT NULL                  | 步骤名称               |
| assignee_profile | VARCHAR(50)  | NOT NULL                  | 负责 Agent 的 Profile |
| qa_required      | BOOLEAN      | NOT NULL, DEFAULT true    | 是否需要 QA 门控         |
| is_active        | BOOLEAN      | NOT NULL, DEFAULT true    | 是否启用               |
| project_id       | BIGINT       | FK→projects.id, NULL=全局默认 | 项目级覆盖 (NULL 为全局)   |
| created_at       | TIMESTAMPTZ  | NOT NULL, DEFAULT now()   | 创建时间               |

索引: `idx_ws_step_project`, UNIQUE: `(step_number, project_id)`

#### 5.2.6 tasks

| 字段                  | 类型           | 约束                          | 说明                                         |
| ------------------- | ------------ | --------------------------- | ------------------------------------------ |
| id                  | BIGSERIAL    | PRIMARY KEY                 | 任务 ID                                      |
| project_id          | BIGINT       | NOT NULL, FK→projects.id    | 项目 ID                                      |
| step_number         | SMALLINT     | NOT NULL                    | 所属步骤 (1-16)                                |
| name                | VARCHAR(255) | NOT NULL                    | 任务名称                                       |
| description         | TEXT         |                            | 任务描述                                       |
| status              | task_status  | NOT NULL, DEFAULT 'pending' | task_status 枚举: pending/in_progress/completed/failed/cancelled |
| assigned_agent_id   | BIGINT       | FK→agents.id                | 分配的 Agent ID                               |
| acceptance_criteria | TEXT         |                            | 验收标准                                       |
| priority            | SMALLINT     | NOT NULL, DEFAULT 5         | 优先级 (1-10, 10 最高)                          |
| estimated_hours     | DECIMAL(5,2) |                            | 预估耗时 (小时)                                  |
| started_at          | TIMESTAMPTZ  |                            | 开始时间                                       |
| completed_at        | TIMESTAMPTZ  |                            | 完成时间                                       |
| created_at          | TIMESTAMPTZ  | NOT NULL, DEFAULT now()     | 创建时间                                       |
| updated_at          | TIMESTAMPTZ  | NOT NULL, DEFAULT now()     | 更新时间                                       |

索引: `idx_tasks_project`, `idx_tasks_step`, `idx_tasks_status`, `idx_tasks_agent`

#### 5.2.7 task_dependencies

| 字段             | 类型          | 约束                      | 说明      |
| -------------- | ----------- | ----------------------- | ------- |
| id             | BIGSERIAL   | PRIMARY KEY             | 依赖 ID   |
| source_task_id | BIGINT      | NOT NULL, FK→tasks.id   | 前置任务 ID |
| target_task_id | BIGINT      | NOT NULL, FK→tasks.id   | 后继任务 ID |
| is_active      | BOOLEAN     | NOT NULL, DEFAULT true  | 是否有效    |
| created_at     | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间    |

索引: `idx_td_source`, `idx_td_target`, UNIQUE: `(source_task_id, target_task_id)`, 约束: `source_task_id != target_task_id`

#### 5.2.8 groups

| 字段            | 类型           | 约束                             | 说明                 |
| ------------- | ------------ | ------------------------------ | ------------------ |
| id            | BIGSERIAL    | PRIMARY KEY                    | 群组 ID              |
| project_id    | BIGINT       | NOT NULL, FK→projects.id       | 所属项目               |
| name          | VARCHAR(255) | NOT NULL                       | 群组名称               |
| mode          | VARCHAR(20)  | NOT NULL, DEFAULT 'discussion' | discussion/meeting |
| host_agent_id | BIGINT       | FK→agents.id                   | 主持人 Agent ID       |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()        | 创建时间               |
| updated_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()        | 更新时间               |

索引: `idx_groups_project`, `idx_groups_mode`

#### 5.2.9 group_members

| 字段          | 类型          | 约束                       | 说明                  |
| ----------- | ----------- | ------------------------ | ------------------- |
| id          | BIGSERIAL   | PRIMARY KEY              | 成员 ID               |
| group_id    | BIGINT      | NOT NULL, FK→groups.id   | 群组 ID               |
| user_id     | BIGINT      | NULLABLE, FK→users.id    | 用户 ID (NULL=Agent)  |
| agent_name  | VARCHAR(100) | NULLABLE                 | Agent 名称 (NULL=人类)  |
| joined_at   | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | 加入时间                |

**V39 修正**: 采用架构 V24 §3.5 定义的双字段设计：user_id(NULL=Agent) + agent_name(NULL=人类用户)。当成员为人类用户时，user_id 有值、agent_name 为 NULL；当成员为 Agent 时，user_id 为 NULL、agent_name 有值。替代 V37 的 member_type + member_id 三选一方案。

索引: `idx_gm_group`, UNIQUE: `(group_id, user_id, agent_name)`

#### 5.2.10 group_messages

| 字段           | 类型          | 约束                           | 说明                    |
| ------------ | ----------- | ---------------------------- | --------------------- |
| id           | BIGSERIAL   | PRIMARY KEY                  | 消息 ID                 |
| group_id     | BIGINT      | NOT NULL, FK→groups.id       | 群组 ID                 |
| sender_type  | VARCHAR(20) | NOT NULL                     | user/agent            |
| sender_id    | BIGINT      | sender_type='agent' 时为 NULL | 发送者 ID (用户 ID)       |
| sender_agent_name | VARCHAR(100) | sender_type='user' 时为 NULL | 发送者 Agent 名称       |
| content      | TEXT        | NOT NULL                     | 消息内容                  |
| message_type | VARCHAR(20) | NOT NULL, DEFAULT 'text'     | text/system/meeting   |
| mentions     | JSONB       |                              | @mention 信息 (V30 改为 JSONB) |
| is_delivered | BOOLEAN     | NOT NULL, DEFAULT false      | 是否已投递给在线用户            |
| role         | VARCHAR(20) |                              | 发送者角色                  |
| is_streaming | BOOLEAN     | NOT NULL, DEFAULT false      | 是否流式消息                 |
| metadata     | JSONB       |                              | 附加元数据                  |
| created_at   | TIMESTAMPTZ | NOT NULL, DEFAULT now()      | 发送时间                  |

**V39 修正**:
1. **sender_type**: 枚举值改为 user/agent（二值），与数据库 V30 §1.3 sender_type 枚举保持一致
2. **sender_id**: 仅存储用户 ID，当 sender_type='agent' 时为 NULL
3. **sender_agent_name**: 新增字段，存储 Agent 名称，当 sender_type='user' 时为 NULL
4. **mentions**: 字段类型改为 JSONB，与数据库 V30 变更日志第1条一致（V30 已将 mentions 从 TEXT[] 改为 JSONB）

索引: `idx_gm_group_time`, `idx_gm_sender`, `idx_gm_delivered`

#### 5.2.11 swarms

| 字段               | 类型          | 约束                         | 说明                         |
| ---------------- | ----------- | -------------------------- | -------------------------- |
| id               | BIGSERIAL   | PRIMARY KEY                | 蜂群 ID                      |
| project_id       | BIGINT      | NOT NULL, FK→projects.id   | 所属项目                       |
| step_number      | SMALLINT    | NOT NULL                   | 所属步骤                       |
| manager_agent_id | INTEGER     | NOT NULL, FK→agents.id     | 管理者 Agent (后发/后达)         |
| status           | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active/completed/dissolved |
| purpose          | swarm_purpose | NOT NULL                  | swarm_purpose 枚举: tdd_test/code_writing/testing |
| task_count       | INTEGER     | NOT NULL, DEFAULT 0        | 任务总数                       |
| completed_count  | INTEGER     | NOT NULL, DEFAULT 0        | 已完成任务数                     |
| created_at       | TIMESTAMPTZ | NOT NULL, DEFAULT now()    | 创建时间                       |
| dissolved_at     | TIMESTAMPTZ |                            | 解散时间                       |

**V39 修正**: manager_agent_id 恢复为 NOT NULL 且移除 ON DELETE SET NULL，与数据库 V30 第1条变更记录一致（V30 已恢复 NOT NULL 并移除 ON DELETE SET NULL）。

索引: `idx_swarms_project`, `idx_swarms_status`

#### 5.2.12 swarm_agents

| 字段               | 类型          | 约束                       | 说明                      |
| ---------------- | ----------- | ------------------------ | ----------------------- |
| id               | BIGSERIAL   | PRIMARY KEY              | 记录 ID                   |
| swarm_id         | BIGINT      | NOT NULL, FK→swarms.id   | 蜂群 ID                   |
| agent_id         | BIGINT      | NOT NULL, FK→agents.id   | Agent ID                |
| status           | VARCHAR(20) | NOT NULL, DEFAULT 'online' | idle/busy/error/offline   |
| assigned_task_id | BIGINT      | FK→tasks.id              | 当前分配的任务 ID              |
| joined_at        | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | 加入时间                    |
| left_at          | TIMESTAMPTZ |                          | 退出时间                    |

**V39 修正**: status 枚举值改为 idle/busy/error/offline，默认值改为 'online'，与数据库 V30 agent_status 枚举保持一致。

索引: `idx_sa_swarm`, `idx_sa_agent`, UNIQUE: `(swarm_id, agent_id)`

#### 5.2.13 qa_records

| 字段                | 类型          | 约束                       | 说明                 |
| ----------------- | ----------- | ------------------------ | ------------------ |
| id                | BIGSERIAL   | PRIMARY KEY              | 记录 ID              |
| task_id           | BIGINT      | NOT NULL, FK→tasks.id    | 任务 ID              |
| project_id        | BIGINT      | NOT NULL, FK→projects.id | 项目 ID              |
| step_number       | SMALLINT    | NOT NULL                 | 步骤编号               |
| reviewer_agent_id | BIGINT      | NOT NULL, FK→agents.id   | 审查者 (后荣)           |
| review_dimensions | JSONB       | NOT NULL                 | 检验维度及得分 (见 10.4 节) |
| score             | DECIMAL(5,2) | NOT NULL                 | 综合评分 (0-100)       |
| acceptance_result | VARCHAR(10) | NOT NULL                 | pass/fail          |
| problem_details   | TEXT        |                          | 不合格时的修改建议          |
| review_round      | SMALLINT    | NOT NULL, DEFAULT 1      | 检验轮次               |
| created_at        | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | 检验时间               |

索引: `idx_qr_task`, `idx_qr_project`, `idx_qr_result`

#### 5.2.14 repositories

| 字段              | 类型           | 约束                       | 说明          |
| --------------- | ------------ | ------------------------ | ----------- |
| id              | BIGSERIAL    | PRIMARY KEY              | 仓库 ID       |
| project_id      | BIGINT       | NOT NULL, FK→projects.id | 项目 ID       |
| gitea_repo_id   | INTEGER      | NOT NULL                 | Gitea 仓库 ID |
| gitea_repo_name | VARCHAR(255) | NOT NULL                 | 仓库名称        |
| default_branch  | VARCHAR(50)  | NOT NULL, DEFAULT 'main' | 默认分支        |
| is_private      | BOOLEAN      | NOT NULL, DEFAULT true   | 是否私有        |
| created_at      | TIMESTAMPTZ  | NOT NULL, DEFAULT now()  | 创建时间        |

索引: `idx_repos_project`, UNIQUE: `(project_id)`

#### 5.2.15 notifications

| 字段         | 类型          | 约束                       | 说明    |
| ---------- | ----------- | ------------------------ | ----- |
| id         | BIGSERIAL   | PRIMARY KEY              | 通知 ID |
| user_id    | BIGINT      | NOT NULL, FK→users.id    | 接收用户  |
| project_id | BIGINT      | FK→projects.id           | 关联项目  |
| type       | VARCHAR(50) | NOT NULL                 | 通知类型  |
| title      | VARCHAR(200) | NOT NULL                 | 通知标题  |
| content    | TEXT        | NOT NULL                 | 通知内容  |
| is_read    | BOOLEAN     | NOT NULL, DEFAULT false  | 是否已读  |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | 创建时间  |

索引: `idx_notifications_user`, `idx_notifications_read`

#### 5.2.16 meeting_outcomes

| 字段            | 类型           | 约束                     | 说明      |
| ------------- | ------------ | ---------------------- | ------- |
| id            | BIGSERIAL    | PRIMARY KEY            | 会议结果 ID |
| group_id      | BIGINT       | NOT NULL, FK→groups.id | 群组 ID   |
| meeting_type  | VARCHAR(50)  | NOT NULL               | 会议类型    |
| meeting_topic | VARCHAR(255) | NOT NULL               | 会议主题    |
| host_agent_id | BIGINT       | NOT NULL, FK→agents.id | 主持人     |
| agenda        | JSONB        | NOT NULL               | 议程列表    |
| summary       | TEXT         |                        | 会议纪要    |
| decisions     | JSONB        |                        | 决议列表    |
| action_items  | JSONB        |                        | 待办任务    |
| risks         | JSONB        |                        | 风险点     |
| started_at    | TIMESTAMPTZ  | NOT NULL               | 开始时间    |
| completed_at  | TIMESTAMPTZ  |                        | 结束时间    |

索引: `idx_mo_group`, `idx_mo_type`

#### 5.2.17 agent_execution_logs

| 字段               | 类型          | 约束                       | 说明                                                    |
| ---------------- | ----------- | ------------------------ | ----------------------------------------------------- |
| id               | BIGSERIAL   | PRIMARY KEY              | 日志 ID                                                 |
| task_id          | BIGINT      | NOT NULL, FK→tasks.id    | 任务 ID                                                 |
| agent_id         | BIGINT      | NOT NULL, FK→agents.id   | Agent ID                                              |
| action           | VARCHAR(50) | NOT NULL                 | dispatched/retried/succeeded/failed/timeout/escalated |
| details          | JSONB       |                          | 详细信息 (错误消息、重试次数等)                                     |
| duration_seconds | INTEGER     |                          | 执行耗时                                                  |
| created_at       | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | 记录时间                                                  |

索引: `idx_ael_task`, `idx_ael_agent`, `idx_ael_action`

#### 5.2.18 artifacts

| 字段            | 类型            | 约束                       | 说明                            |
| ------------- | ------------- | ------------------------ | ----------------------------- |
| id            | BIGSERIAL     | PRIMARY KEY              | 文件 ID                         |
| project_id    | BIGINT        | NOT NULL, FK→projects.id | 项目 ID                         |
| file_name     | VARCHAR(500)  | NOT NULL                 | 原始文件名                         |
| stored_name   | VARCHAR(500)  | NOT NULL                 | 存储文件名 (带 UUID 前缀)             |
| file_size     | BIGINT        | NOT NULL                 | 文件大小 (字节)                     |
| mime_type     | VARCHAR(100)  | NOT NULL                 | MIME 类型                       |
| uploaded_by   | VARCHAR(50)   | NOT NULL                 | 上传者 (user_id 或 agent profile) |
| uploader_type | VARCHAR(20)   | NOT NULL, DEFAULT 'user' | user/agent/system             |
| storage_path  | VARCHAR(1000) | NOT NULL                 | 服务器存储路径                       |
| checksum      | VARCHAR(64)   | NOT NULL                 | SHA-256 校验和                   |
| created_at    | TIMESTAMPTZ   | NOT NULL, DEFAULT now()  | 上传时间                          |

索引: `idx_artifacts_project`, `idx_artifacts_name`

#### 5.2.19 audit_logs (V30 新增)

| 字段            | 类型           | 约束                      | 说明                            |
| ------------- | ------------ | ----------------------- | ----------------------------- |
| id            | BIGSERIAL    | PRIMARY KEY             | 日志 ID                         |
| event_type    | VARCHAR(50)  | NOT NULL                | 事件类型 (user_login/project_create 等)  |
| actor_type    | VARCHAR(20)  | NOT NULL                | user/admin/system/agent       |
| actor_id      | BIGINT       |                         | 操作者 ID                        |
| resource_type | VARCHAR(50)  |                         | 关联资源类型 (project/task/agent 等)  |
| resource_id   | BIGINT       |                         | 关联资源 ID                       |
| details       | JSONB        | NOT NULL                | 事件详细信息                        |
| ip_address    | VARCHAR(45)  |                         | 客户端 IP                        |
| user_agent    | VARCHAR(500) |                         | 客户端 User-Agent                |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now() | 事件时间                          |

索引: `idx_audit_event_type`, `idx_audit_actor`, `idx_audit_time`, `idx_audit_resource`

#### 5.2.20 project_members (V33 新增)

| 字段         | 类型          | 约束                             | 说明                 |
| ---------- | ----------- | ------------------------------ | ------------------ |
| id         | BIGSERIAL   | PRIMARY KEY                    | 成员记录 ID           |
| project_id | BIGINT      | NOT NULL, FK→projects.id       | 项目 ID              |
| user_id    | BIGINT      | NOT NULL, FK→users.id          | 用户 ID              |
| role       | VARCHAR(20) | NOT NULL, CHECK 约束             | owner/admin/member/viewer |
| invited_by | BIGINT      | FK→users.id                    | 邀请者用户 ID          |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now()        | 加入时间               |

索引: `idx_pm_project`, UNIQUE: `(project_id, user_id)`

说明: 项目创建时，创建者自动以 `owner` 角色加入。`owner` 拥有项目完全控制权，`admin` 可管理项目成员和执行流程操作，`member` 可执行流程操作和编辑项目，`viewer` 仅能查看项目和流程状态。

#### 5.2.21 step_events (V39 新增)

| 字段            | 类型           | 约束                      | 说明                                                    |
| ------------- | ------------ | ----------------------- | ----------------------------------------------------- |
| id            | BIGSERIAL    | PRIMARY KEY             | 事件 ID                                                 |
| project_id    | BIGINT       | NOT NULL, FK→projects.id | 项目 ID                                                 |
| step_number   | SMALLINT     | NOT NULL                 | 步骤编号 (1-16)                                            |
| event_type    | VARCHAR(50)  | NOT NULL                 | 事件类型 (step_started/step_completed/qa_passed/qa_failed/rollback 等) |
| actor_type    | VARCHAR(20)  | NOT NULL                 | user/agent/system                                      |
| actor_id      | BIGINT       |                          | 操作者 ID                                                |
| before_state  | JSONB        |                          | 状态变更前的快照                                           |
| after_state   | JSONB        |                          | 状态变更后的快照                                           |
| details       | JSONB        |                          | 事件详细信息                                               |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()  | 事件时间                                                  |

**V39 新增**: 对应架构 V24 §3.9 定义的 step_events 表，用于分布式一致性事件记录。与 audit_logs 的区别：audit_logs 记录系统级操作审计，step_events 专注于 16 步流程中的关键状态变更事件，支持最终一致性校验和审计追踪。

索引: `idx_se_project_step`, `idx_se_event_type`, `idx_se_time`

### 5.3 表关系总结 (V36 修正)

| 关系                           | 类型  | 说明                     |
| ---------------------------- | --- | ---------------------- |
| users → projects             | 1:N | 一个用户可创建多个项目            |
| projects → workflow_progress | 1:N | 一个项目有 16 条流程进度记录       |
| projects → tasks             | 1:N | 一个项目有多个任务              |
| projects → groups            | 1:N | 一个项目可有多个讨论群 (V36 修正: 从 1:1 改为 1:N) |
| projects → repositories      | 1:1 | 一个项目一个代码仓库             |
| projects → swarms            | 1:N | 一个项目可建立多个蜂群            |
| projects → artifacts         | 1:N | 一个项目有多个产出文件            |
| projects → project_members   | 1:N | 一个项目有多个成员 (V33 新增)       |
| projects → step_events       | 1:N | 一个项目有多个步骤事件 (V39 新增)     |
| groups → group_members       | 1:N | 一个群组有多个成员              |
| groups → group_messages      | 1:N | 一个群组有多条消息              |
| groups → meeting_outcomes    | 1:N | 一个群组有多次会议结果            |
| swarms → swarm_agents        | 1:N | 一个蜂群有多个 Agent          |
| tasks → qa_records           | 1:N | 一个任务可有多次 QA 检验         |
| tasks → agent_execution_logs | 1:N | 一个任务有多条执行日志            |
| tasks → tasks (self)         | M:N | 通过 task_dependencies 表 |

V36 修正说明：projects → groups 关系从 1:1 修正为 1:N。理由：API 设计 2.9 节支持 GET /api/v1/groups（列表）、POST /api/v1/groups（创建）、GET /api/v1/groups/:group_id/outcomes 等多群组操作，前端也按多群组设计。一个项目可拥有多个讨论群（如主讨论群、专项会议群等）。

V39 新增：projects → step_events 关系 (1:N)，对应架构 V24 §3.9 定义的 step_events 表。

### 5.4 索引设计与查询优化 (V30 新增)

**索引设计原则**:
1. 所有外键字段建立索引，加速 JOIN 查询
2. 高频查询字段建立索引（如 status、created_at）
3. 组合索引按查询频率和选择性排序
4. JSONB 字段使用 GIN 索引支持部分查询

**关键索引**:

| 表              | 索引名                      | 字段                        | 类型     | 用途              |
| -------------- | ------------------------ | ------------------------- | ------ | --------------- |
| projects       | idx_projects_creator_id    | creator_id                  | B-tree | 按用户查询项目列表     |
| projects       | idx_projects_status      | status                    | B-tree | 按状态过滤项目       |
| projects       | idx_projects_created_at  | created_at DESC           | B-tree | 项目列表默认排序     |
| projects       | idx_projects_deleted_at  | deleted_at                 | B-tree | 软删除项目过滤        |
| tasks          | idx_tasks_project        | project_id                | B-tree | 按项目查询任务       |
| tasks          | idx_tasks_status         | status                    | B-tree | 按状态过滤任务       |
| tasks          | idx_tasks_project_status | (project_id, status)      | B-tree | 复合查询优化        |
| workflow_progress | idx_wp_project_step    | (project_id, step_number) | B-tree | 流程进度查询        |
| workflow_progress | idx_wp_status         | status                    | B-tree | 按状态查询流程       |
| agents         | idx_agents_status        | status                    | B-tree | Agent 状态查询      |
| agents         | idx_agents_is_named      | is_named                  | B-tree | 命名 Agent 查询     |
| qa_records     | idx_qr_task              | task_id                   | B-tree | 按任务查询检验记录    |
| qa_records     | idx_qr_result            | acceptance_result         | B-tree | 按结果过滤检验记录    |
| group_messages | idx_gm_group_time        | (group_id, created_at)    | B-tree | 按群组和时间查询消息  |
| notifications  | idx_notifications_user   | (user_id, is_read)        | B-tree | 用户未读通知查询      |
| audit_logs     | idx_audit_time           | created_at DESC           | B-tree | 审计日志按时间查询    |
| audit_logs     | idx_audit_resource       | (resource_type, resource_id) | B-tree | 按资源查询审计日志 |
| step_events    | idx_se_project_step      | (project_id, step_number) | B-tree | 按项目和步骤查询事件   |
| step_events    | idx_se_event_type        | event_type                | B-tree | 按事件类型过滤       |

**N+1 查询解决方案**:

使用 SQLAlchemy 2.0 的 `selectin` 和 `joinedload` 策略避免 N+1 查询：

```python
# 场景: 获取项目列表及其任务数
# 错误做法 (N+1):
projects = await db.execute(select(Project))
for p in projects:
    tasks = await db.execute(select(Task).where(Task.project_id == p.id))

# 正确做法 (selectin):
from sqlalchemy.orm import selectinload
stmt = select(Project).options(selectinload(Project.tasks))
projects = await db.execute(stmt)
# 仅 2 次查询: 1 次查 projects, 1 次查所有关联 tasks
```

**分页查询优化**:

对于深度分页场景，使用游标分页替代 OFFSET 分页：

```python
# 错误做法 (深度分页):
stmt = select(Task).where(Task.project_id == project_id).offset(10000).limit(20)
# OFFSET 10000 会导致扫描 10020 行

# 正确做法 (游标分页):
stmt = (
    select(Task)
    .where(Task.project_id == project_id)
    .where(Task.created_at < last_seen_at)
    .order_by(Task.created_at.desc())
    .limit(20)
)
# 仅扫描 20 行
```

**批量操作设计**:

```python
# 批量插入 (execute_many):
async def batch_create_tasks(self, tasks: list[Task]):
    await self.session.execute(insert(Task), [t.__dict__ for t in tasks])
    await self.session.commit()

# 批量更新 (executemany):
async def batch_update_status(self, task_ids: list[int], status: str):
    await self.session.execute(
        update(Task).where(Task.id.in_(task_ids)).values(status=status)
    )
    await self.session.commit()
```

---

## 5.5 大表分区与归档策略 (V33 新增)

以下三张表是明显的写多读少场景，数据量增长迅速，需要提前规划分区和归档策略。

### 5.5.1 group_messages (群消息表)

| 维度     | 策略                                    |
| ------ | ------------------------------------- |
| 分区方式   | RANGE 分区，按 `created_at` 按月分区           |
| 分区命名   | `group_messages_y2026m06` 等              |
| 归档阈值   | 超过 6 个月的消息归档到 `group_messages_archive` |
| 归档频率   | Celery Beat 每月 1 号凌晨执行                   |
| 查询影响   | 前端仅展示最近 3 个月消息，历史消息按需从归档表检索    |
| 分区维护   | 每月自动创建新分区 (`CREATE PARTITION ... FOR`) |

### 5.5.2 audit_logs (审计日志表)

| 维度     | 策略                                    |
| ------ | ------------------------------------- |
| 分区方式   | RANGE 分区，按 `created_at` 按月分区           |
| 分区命名   | `audit_logs_y2026m06` 等                 |
| 归档阈值   | 超过 12 个月的日志归档到 `audit_logs_archive`  |
| 归档频率   | Celery Beat 每季度执行                      |
| 合规要求   | 审计日志保留至少 1 年（满足合规审计需求）            |
| 分区维护   | 每月自动创建新分区                           |

### 5.5.3 agent_execution_logs (Agent执行日志表)

| 维度     | 策略                                    |
| ------ | ------------------------------------- |
| 分区方式   | RANGE 分区，按 `created_at` 按月分区           |
| 分区命名   | `agent_execution_logs_y2026m06` 等       |
| 归档阈值   | 超过 3 个月的日志归档到 `agent_execution_logs_archive` |
| 归档频率   | Celery Beat 每月 1 号凌晨执行                   |
| 查询影响   | 日常排查仅查看最近 1 个月日志                   |
| 分区维护   | 每月自动创建新分区                           |

### 5.5.4 分区维护自动化

```python
# Celery Beat 定时任务: daily_partition_maintenance
@celery_app.task
def daily_partition_maintenance():
    """每日检查并创建下月分区，清理过期归档数据"""
    tables = ["group_messages", "audit_logs", "agent_execution_logs"]
    for table in tables:
        next_month = (datetime.now() + timedelta(days=32)).replace(day=1)
        partition_name = f"{table}_y{next_month.year}m{next_month.month:02d}"
        # 检查分区是否存在，不存在则创建
        if not partition_exists(partition_name):
            create_partition(table, partition_name, next_month)
```

---

## 6. 安全设计 (V33 新增)

### 6.1 认证与授权

**认证机制** (详见 2.2.1 节):
- JWT Access Token: RS256 签名，有效期 2 小时（7200 秒）
- Refresh Token: 轮换机制，有效期 7 天
- WebSocket 认证: 直接使用 access_token 通过 auth 消息进行认证，无需专用 ws_token
- Token 黑名单: Redis 存储，键格式 `token:blacklist:{jti}`
- 密码存储: bcrypt 哈希 (`users.password_hash`)

**V41 修正**: WebSocket 认证直接使用 access_token 通过 auth 消息进行，已移除 ws_token 专用方案，与前端 V20 保持一致。

**授权模型** (V33 新增, V34 修正):

| 角色           | 项目操作                    | 流程操作             | 管理操作    |
| ------------ | ----------------------- | ---------------- | ------- |
| owner        | 创建/编辑/删除/邀请/移除成员       | 启动/回退/暂停/删除流程     | 项目级全权限  |
| admin        | 查看/编辑/邀请/移除成员         | 启动/回退/暂停流程       | 项目级管理权限 |
| member       | 查看/编辑项目信息             | 启动/查看流程           | 无管理权限   |
| viewer       | 仅查看项目和流程状态            | 仅查看流程状态           | 无操作权限   |

权限检查中间件: `project_auth_middleware`，在路由层注入，检查当前用户对目标项目的权限等级。

```python
# 权限检查中间件示例
async def require_project_permission(project_id: int, min_role: str = "viewer"):
    """验证当前用户对指定项目的权限等级"""
    user = get_current_user()
    membership = await project_member_repo.get(project_id, user.id)
    if not membership:
        raise PermissionDenied("无权访问该项目", business_code=10004)
    role_hierarchy = {"viewer": 1, "member": 2, "admin": 3, "owner": 4}
    if role_hierarchy.get(membership.role, 0) < role_hierarchy.get(min_role, 0):
        raise PermissionDenied("权限不足", business_code=10005)
    return membership
```

### 6.2 CSRF 防护

**防护策略**:

| 场景          | 防护方式                               | 说明                    |
| ----------- | ---------------------------------- | --------------------- |
| REST API    | Bearer Token 天然抗 CSRF             | Token 不在 Cookie 中存储    |
| WebSocket   | access_token 认证，通过 auth 消息进行        | 连接建立后通过第一条消息验证身份  |
| Web 页面提交  | SameSite=Lax Cookie + CSRF Token 双重防护 | 用于登录/注册/登出等浏览器端操作   |

**CSRF Token 实现**:

```python
# 生成 CSRF Token (登录后)
csrf_token = str(uuid4())
# 存储在 HttpOnly + SameSite=Lax Cookie 中
response.set_cookie("csrf_token", csrf_token, httponly=True, samesite="lax", max_age=7200)
# 前端在 state-changing 请求 Header 中携带 X-CSRF-Token
```

**SameSite Cookie 策略**:
- `session_id`: SameSite=Lax, HttpOnly, Secure
- `csrf_token`: SameSite=Lax, HttpOnly
- `refresh_token`: SameSite=Strict, HttpOnly, Secure

### 6.3 项目级权限模型

**权限检查流程**:

```
请求到达 → 认证中间件(JWT验证) → 权限中间件(project_auth_middleware)
    → 查询 project_members 表
    → 对比用户角色与端点要求的最低角色
    → 通过 → 执行业务逻辑
    → 拒绝 → 返回 403 (business_code=10004/10005)
```

**端点权限矩阵** (V39 修正: 更新 HTTP 方法):

| 端点 | 最低角色 | 说明 |
| ---- | ------ | ---- |
| GET /projects/:id | viewer | 查看项目详情 |
| PATCH /projects/:id | member | 编辑项目信息 (V39: PATCH) |
| DELETE /projects/:id | owner | 删除项目 (软删除) |
| POST /projects/:id/workflow/step/:number | member | 启动步骤执行 |
| POST /projects/:id/workflow/rollback | admin | 回退流程 |
| GET /projects/:id/artifacts | viewer | 查看产出物 |
| POST /projects/:id/artifacts/upload | member | 上传产出物 |
| POST /groups/:id/members | admin | 邀请成员 |
| DELETE /groups/:id/members/:id | owner | 移除成员 |
| GET /settings | viewer | 获取用户设置 (V39 新增) |
| PATCH /settings | viewer | 更新用户设置 (V39 新增) |

### 6.4 数据传输加密

**TLS/HTTPS 强制**:
- 所有 API 端点强制 HTTPS (TLS 1.2+)
- Nginx 反向代理终止 TLS，后端服务通过 HTTP 与 Nginx 通信 (内网)
- HSTS 头: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- WebSocket 使用 `wss://` 协议
- 禁止 HTTP 明文访问，Nginx 配置 301 重定向 HTTP→HTTPS

**TLS 配置**:
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
```

### 6.5 敏感信息存储

**密钥管理**:

| 敏感信息           | 存储方式                        | 说明                   |
| ------------ | --------------------------- | -------------------- |
| Gitea API Token | `.env` 环境变量 (`GITEA_API_TOKEN`) | 不硬编码到代码中           |
| 数据库连接字符串     | `.env` 环境变量 (`DATABASE_URL`)    | 含用户名、密码、主机         |
| JWT 私钥        | 文件系统文件 (`/etc/devflow/jwt_rs256.pem`) | 文件权限 600，仅 root/app 用户可读 |
| JWT 公钥        | 配置文件或环境变量                    | 用于验证 Token 签名     |
| Redis 密码      | `.env` 环境变量 (`REDIS_PASSWORD`) | 容器内通过环境变量注入        |

**密钥轮换策略**:
- JWT 密钥对: 支持定期轮换，旧公钥在 Access Token 有效期内保留用于验证
- Gitea Token: 通过更新 `.env` + 重启服务完成轮换
- 数据库密码: 通过更新 `.env` + 重启服务完成轮换

---

## 7. 运维与部署 (V33 新增)

### 7.1 优雅停机

**SIGTERM 处理流程**:

```
容器收到 SIGTERM
    │
    ├─ 阶段1: 停止接收新请求 (5秒)
    │   └─ FastAPI 关闭 HTTP listener
    │   └─ 新请求返回 503 Service Unavailable
    │
    ├─ 阶段2: 等待活跃请求完成 (最多30秒)
    │   └─ 等待正在处理的请求完成
    │   └─ 超时未完成的请求强制终止
    │
    ├─ 阶段3: 通知 Celery Worker 停止 (5秒)
    │   └─ Celery Worker 完成当前任务后停止接收新任务
    │   └─ 运行中的任务允许完成或超时终止 (soft_time_limit)
    │
    ├─ 阶段4: 资源清理 (5秒)
    │   └─ 关闭数据库连接池
    │   └─ 关闭 Redis 连接
    │   └─ 关闭 WebSocket 连接 (广播断开通知给客户端)
    │   └─ 刷新日志缓冲区
    │
    └─ 阶段5: 进程退出
        └─ 退出码 0 (正常) / 1 (异常)
```

**FastAPI Shutdown 事件处理**:

```python
import signal
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    await initialize_app()
    yield
    # 关闭时清理
    await cleanup_app()

# SIGTERM handler
async def handle_sigterm(signum, frame):
    """优雅停机信号处理"""
    logger.info("Received SIGTERM, starting graceful shutdown...")
    await shutdown_sequence()
```

**Celery Worker 优雅停机**:
- `worker_shutdown_timeout=60` (秒)
- `worker_cancel_task_on_shutdown=False` (允许运行中的任务完成)
- 健康检查探针: liveness=50s, readiness=10s

### 7.2 CI/CD 流程

**流水线阶段**:

```
Git Push → CI Pipeline → CD Deployment
    │           │              │
    │           ├─ Lint       │
    │           │  (flake8,   │
    │           │   black,    │
    │           │   mypy)     │
    │           │              │
    │           ├─ Unit Test  │
    │           │  (pytest    │
    │           │   --cov)    │
    │           │              │
    │           ├─ Build      │
    │           │  (Docker    │
    │           │   multi-    │
    │           │   stage)    │
    │           │              │
    │           └─ Security   │
    │              (trivy     │
    │               scan)     │
    │                         │
    │                         ├─ Staging
    │                         │  (自动部署)
    │                         │              │
    │                         ├─ Production
    │                         │  (人工审批)
    │                         │              │
    │                         └─ Smoke Test
    │                            (自动验证)
```

**分支策略**:
- `main`: 生产分支，受保护，仅允许 PR 合并
- `develop`: 开发分支，CI 自动运行
- `feature/*`: 功能分支，合并到 develop
- `hotfix/*`: 热修复分支，合并到 main 和 develop
- 所有 PR 要求: CI 通过 + 至少 1 人 Review + Conventional Commits

### 7.3 灰度发布方案

**蓝绿部署**:

```
           负载均衡
          /        \
         /          \
    [蓝环境]      [绿环境]
    (v1.2)       (v1.3)
         \          /
          \        /
      流量切换: 10% → 50% → 100%
```

**灰度步骤**:
1. 部署新版本到绿环境 (不接流量)
2. 运行冒烟测试，验证基本功能
3. 负载均衡切换 10% 流量到绿环境
4. 监控 15 分钟: 错误率 < 1%，P99 延迟 < 2 倍基线
5. 切换到 50% 流量，继续监控 15 分钟
6. 切换到 100% 流量
7. 观察 1 小时，确认无异常后下线蓝环境

**自动回滚条件**:
- 错误率 > 5% (5 分钟滑动窗口)
- P99 延迟 > 3 倍基线
- 健康检查连续 3 次失败
- 触发自动回滚: 负载均衡切回蓝环境，告警通知

**数据库迁移兼容性**:
- 向前兼容: 新代码能读写旧数据库结构
- 迁移分两步: 部署代码 → 执行迁移 → 清理废弃字段
- 回滚时: 反向迁移脚本确保数据完整性

---

## 8. 业务规则注册表 (V33 新增)

本节集中管理 DevFlow 后端所有业务规则，统一编号为 BR-xxx，便于追踪和维护。

### 8.1 流程执行规则

| 编号    | 规则名称             | 规则描述                                      | 关联服务                  |
| ------- | ------------------ | ------------------------------------------- | --------------------- |
| BR-001  | Agent执行超时       | 每个 Agent 执行任务最大超时时间为 30 分钟                   | step_executor         |
| BR-002  | 自动重试次数         | Agent 执行失败后自动重试，最大 3 次                       | agent_tasks (Celery)  |
| BR-003  | 重试退避策略         | 重试间隔采用指数退避: 第1次 30秒，第2次 60秒，第3次 120秒         | agent_tasks (Celery)  |
| BR-004  | QA检验轮次上限       | 每个步骤 QA 检验最多 3 轮，超过 3 轮不通过则海梅介入              | qa_service            |
| BR-005  | QA合格阈值         | QA 检验综合评分 ≥ 80 分视为合格                        | qa_service            |
| BR-006  | 退回重做时限         | QA 不通过的步骤，退回重做时限为 24 小时                     | workflow_orchestrator |
| BR-007  | 备用Agent切换       | Agent 重试 3 次均失败后，自动切换到备用 Agent                | agent_service         |
| BR-008  | 步骤并发限制         | 每个项目每个步骤最多 1 个并发执行实例                       | workflow_statemachine |
| BR-009  | 流程回退规则         | 回退到某步时，该步之后的所有步骤状态重置为 pending             | workflow_orchestrator |

### 8.2 分布式锁规则

| 编号    | 规则名称             | 规则描述                                      | 关联服务                  |
| ------- | ------------------ | ------------------------------------------- | --------------------- |
| BR-010  | 分布式锁TTL         | 工作流分布式锁 TTL 为 30 分钟 (与 Agent 执行超时一致)        | workflow_statemachine |
| BR-011  | 锁续期间隔          | Celery Worker 每 5 分钟检查并续期锁 TTL             | agent_tasks (Celery)  |
| BR-012  | 死锁检测阈值         | Redis 中超 25 分钟未释放的锁触发告警并强制释放               | semaphore             |
| BR-013  | 加锁顺序           | 固定顺序: 项目级锁 → 步骤级锁 → 任务级锁，避免交叉等待死锁           | workflow_statemachine |

### 8.3 熔断与降级规则

| 编号    | 规则名称             | 规则描述                                      | 关联服务              |
| ------- | ------------------ | ------------------------------------------- | ----------------- |
| BR-014  | Gateway熔断阈值     | 同一 Gateway 连续 3 次调用失败，触发 5 分钟熔断           | gateway_service     |
| BR-015  | 熔断半开探测         | 熔断窗口结束后发送 1 次探测请求，成功则恢复，失败则延长熔断       | gateway_service     |
| BR-016  | Redis故障降级       | Redis 不可用时，回退到直接查询数据库，禁用缓存层                | redis_client        |
| BR-017  | Gitea故障降级       | Gitea 不可用时，产出暂存本地，定时重试(每5分钟，最多3次)          | repo_service        |

### 8.4 认证与安全规则 (V39 修正)

| 编号    | 规则名称             | 规则描述                                      | 关联服务              |
| ------- | ------------------ | ------------------------------------------- | ----------------- |
| BR-018  | Access Token有效期  | JWT Access Token 有效期 2 小时（7200 秒）          | security          |
| BR-019  | Refresh Token有效期 | JWT Refresh Token 有效期 7 天                   | security          |
| BR-020  | 密码复杂度要求        | 至少 8 字符，包含大小写字母和数字                       | auth_service       |
| BR-021  | Token轮换           | Refresh Token 每次使用后旧 Token 立即失效               | security          |
| BR-022  | 项目权限校验         | 所有项目相关 API 必须校验当前用户的项目级权限               | project_auth_middleware |
| BR-037  | WebSocket 认证方式 (V41) | WebSocket 使用 access_token 通过 auth 消息认证，响应类型为 auth_success/auth_error | security / websocket_service |

### 8.5 速率限制规则

| 编号    | 规则名称             | 规则描述                                      | 关联服务              |
| ------- | ------------------ | ------------------------------------------- | ----------------- |
| BR-023  | 全局API速率          | 每用户每秒最多 100 次 API 请求                      | rate_limiter      |
| BR-024  | 文件上传速率          | 每用户每分钟最多 10 次文件上传                       | rate_limiter      |
| BR-025  | WebSocket消息速率    | 每用户每分钟最多 60 条 WebSocket 消息                 | rate_limiter      |
| BR-026  | Agent对话速率        | 每用户每分钟最多 30 次 Agent 对话请求                  | rate_limiter      |

### 8.6 缓存规则

| 编号    | 规则名称             | 规则描述                                      | 关联服务              |
| ------- | ------------------ | ------------------------------------------- | ----------------- |
| BR-027  | Agent状态缓存TTL    | Agent 状态缓存 TTL 为 5 分钟                      | redis_client        |
| BR-028  | 流程状态缓存TTL      | 流程状态缓存 TTL 为 10 分钟                       | redis_client        |
| BR-029  | 群组信息缓存TTL      | 群组信息缓存 TTL 为 30 分钟                       | redis_client        |
| BR-030  | 缓存写策略           | 先写数据库，成功后再更新缓存 (write-through)            | 各服务层               |

### 8.7 蜂群规则

| 编号    | 规则名称             | 规则描述                                      | 关联服务              |
| ------- | ------------------ | ------------------------------------------- | ----------------- |
| BR-031  | 蜂群Agent心跳超时    | 蜂群成员超过 5 分钟未上报心跳视为离线                     | swarm_service       |
| BR-032  | 蜂群文件系统隔离      | 每个蜂群 Agent 拥有独立工作目录                         | swarm_service       |
| BR-033  | 蜂群崩溃处理         | 单个成员崩溃 → 任务重新分配；全部崩溃 → 蜂群标记为 failed    | swarm_service       |

### 8.8 代码规范规则

| 编号    | 规则名称             | 规则描述                                      | 关联服务              |
| ------- | ------------------ | ------------------------------------------- | ----------------- |
| BR-034  | 提交消息规范         | 所有代码提交遵循 Conventional Commits 规范             | repo_service        |
| BR-035  | 默认分页大小         | 默认每页 20 条，最大 100 条                        | 全局配置              |
| BR-036  | 任务优先级范围        | 任务优先级范围 1-10，10 为最高优先级                   | task_service        |

---

## 9. V40 修订说明

### 9.1 修订概述

V40 基于跨文档一致性检验报告进行修订，针对 20 项跨文档一致性问题进行逐一修正和验证。本次修订涵盖三个维度：

1. **架构-后端**：5 项不一致问题修正
2. **前端-后端**：7 项不一致问题修正
3. **后端-数据库**：8 项不一致问题修正

V40 在 V39 的基础上进行了全面的交叉验证，确保后端设计与架构 V24、前端 V19 和数据库 V30 完全一致。

### 9.2 架构-后端一致性问题修正 (V40)

| 问题编号 | 不一致描述 | V37 状态 | V40 修正内容 | 验证状态 | 涉及章节 |
| ---- | -------- | ------ | -------- | ------ | ------ |
| 1 | V41 修正：WebSocket 端点改为多连接方案（ws/group-chat, ws/notifications, ws/workflow/:project_id），与前端 V20 §6.1 保持一致 | 已修正 | - | ✅ V41 | §2.17 |
| 2 | 代码仓库 REST 风格不一致：架构 V24 §2.2 使用嵌套路径 `/api/v1/projects/{id}/repo/init` 和 `/repo/commit`，后端 V37 使用独立资源 `/api/v1/repos` | 不一致 | 改为嵌套路径 `/api/v1/projects/:id/repo/*` 格式，与架构嵌套资源路径保持一致 | ✅ 已修正 | §2.11 |
| 3 | group_messages.sender_type 枚举不一致：架构 human/agent，后端 V37 user/agent/system | 不一致 | 改为 user/agent（与数据库 V30 一致），新增 sender_agent_name 字段以支持 Agent 名称记录 | ✅ 已修正 | §4.8, §5.2.10 |
| 4 | group_members 表结构不一致：架构 V24 §3.5 使用 user_id(NULL=Agent) + agent_name(NULL=人类) 双字段，后端 V37 使用 member_type + member_id 三选一方案 | 不一致 | 改为双字段设计 user_id(NULL=Agent) + agent_name(NULL=人类) | ✅ 已修正 | §4.8, §5.2.9 |
| 5 | 架构 V24 §3.9 定义 step_events 表，后端 V37 无对应表定义 | 不一致 | 新增 step_events 表、StepEventOut schema、step_event_repo.py | ✅ 已修正 | §3.9, §4.17, §5.2.21 |

### 9.3 前端-后端一致性问题修正 (V40)

| 问题编号 | 不一致描述 | V37 状态 | V40 修正内容 | 验证状态 | 涉及章节 |
| ---- | -------- | ------ | -------- | ------ | ------ |
| 1 | V41 修正：WebSocket 认证方式统一为 access_token 加 auth_success/auth_error，与前端 V20 保持一致 | 已修正 | - | ✅ V41 | §2.2, §2.17 |
| 2 | 【严重】项目更新 HTTP 方法不一致：前端 V19 §5.1 updateProject 使用 api.patch，§5.2 端点清单为 PATCH /projects/:id；后端 V37 定义为 PUT | 不一致 | 改为 PATCH /api/v1/projects/:id | ✅ 已修正 | §2.3, §4.3 |
| 3 | 【严重】通知已读标记 HTTP 方法不一致：前端 V19 §4.6 markAsRead 使用 api.patch，§5.2 端点清单为 PATCH /notifications/:id/read；后端 V37 定义为 PUT | 不一致 | 改为 PATCH /api/v1/notifications/:id/read 和 PATCH /api/v1/notifications/read-all | ✅ 已修正 | §2.12 |
| 4 | V41 修正：ws-token 端点已移除，WebSocket 认证直接使用 access_token，与前端 V20 保持一致 | 已修正 | - | ✅ V41 | §2.2, §2.17 |
| 5 | V41 修正：WebSocket 端点改为多连接方案（3个独立端点），与前端 V20 §6.1 保持一致 | 已修正 | - | ✅ V41 | §2.17 |
| 6 | 前端 V19 §4.7 settingStore 使用 api.get('/settings') 和 api.patch('/settings')，后端 V37 无对应 /settings 端点 | 不一致 | 新增 GET /api/v1/settings 和 PATCH /api/v1/settings 端点 | ✅ 已修正 | §2.14, §4.16 |
| 7 | 前端 V19 §4.5 taskStore updateTaskStatus 使用 api.patch(/tasks/${taskId}, {status})，后端 V37 使用 PUT /tasks/:id | 不一致 | 改为 PATCH /api/v1/tasks/:id | ✅ 已修正 | §2.5, §4.5 |

### 9.4 后端-数据库一致性问题修正 (V40)

| 问题编号 | 不一致描述 | V37 状态 | V40 修正内容 | 验证状态 | 涉及章节 |
| ---- | -------- | ------ | -------- | ------ | ------ |
| 1 | 【严重】group_messages.mentions 字段类型冲突：后端 V37 §5.2.10 声明 TEXT[]（PostgreSQL 原生数组），数据库 V30 变更日志明确声称 V30 已将 mentions 从 TEXT[] 改为 JSONB | 不一致 | 改为 JSONB (Dict[str, Any])，与数据库 V30 保持一致 | ✅ 已修正 | §4.8, §5.2.10 |
| 2 | swarms.manager_agent_id 约束矛盾：后端 V37 §5.2.11 声明 INTEGER NULLABLE ON DELETE SET NULL，数据库 V30 第1条变更记录声称 V30 已恢复 NOT NULL 并移除 ON DELETE SET NULL | 不一致 | 改为 int (NOT NULL, FK→agents.id)，与数据库 V30 保持一致 | ✅ 已修正 | §4.7, §5.2.11 |
| 3 | 【严重】projects 表：后端 V37 §5.2.2 表定义无 deleted_at 字段，数据库 V30 §3.1 明确 projects 有 deleted_at 软删除字段 | 不一致 | 新增 deleted_at 字段 (TIMESTAMPTZ NULLABLE)，ProjectOut 新增 deleted_at | ✅ 已修正 | §4.3, §5.2.2 |
| 4 | 后端 V37 缺少 workflow_progress、workflow_steps、project_members 三张表的 schema 定义（仅在 ER 图 §5.1 中体现） | 不完整 | 确认三张表在 §5.2 中均有完整表定义 (§5.2.3, §5.2.5, §5.2.20) | ✅ 已确认 | §5.2.3, §5.2.5, §5.2.20 |
| 5 | projects.status 枚举值不一致：后端 V37 使用 active/paused/completed/archived，数据库 V30 §1.3 枚举 project_status 为 created/in_progress/completed/cancelled | 不一致 | 改为 created/in_progress/completed/cancelled | ✅ 已修正 | §2.3, §4.3, §5.2.2 |
| 6 | user_role 枚举不一致：后端 V37 使用 user/admin，数据库 V30 枚举为 user/admin/system_admin | 不一致 | 改为 user/admin/system_admin | ✅ 已修正 | §4.2, §5.2.1 |
| 7 | agent_status 枚举不一致：后端 V37 §4.4 AgentOut.status 使用 idle/busy/error/offline 四值，数据库 V30 枚举 agent_status 为 idle/busy/error/offline 三值 | 不一致 | 改为 idle/busy/error/offline，AgentStatusReport 正则模式同步修正 | ✅ 已修正 | §4.4, §5.2.4, §5.2.12 |
| 8 | group_messages.sender_type 不一致：后端 V37 §4.8 GroupMessageOut.sender_type 为 user/agent/system 三值，数据库 V30 §1.3 sender_type 枚举为 user/agent 二值 | 不一致 | 改为 user/agent 二值，与数据库 V30 保持一致 | ✅ 已修正 | §4.8, §5.2.10 |

### 9.5 目录结构变更 (V40)

V40 相比 V37 新增的文件：

| 文件 | 说明 |
| ---- | ---- |
| `app/models/step_event.py` | step_events 表的 SQLAlchemy 模型 |
| `app/schemas/step_event.py` | StepEventOut schema 定义 |
| `app/schemas/settings.py` | SettingsOut/SettingsUpdate schema 定义 |
| `app/routers/settings.py` | 用户设置路由 |
| `app/services/settings_service.py` | 用户设置服务 |
| `app/repositories/step_event_repo.py` | step_events 数据访问层 |

### 9.6 修正验证清单

V40 通过以下维度的交叉验证：

#### 9.6.1 后端 Schema ↔ 数据库表结构

| 验证项 | 后端定义 | 数据库定义 | 验证结果 |
| ---- | ---- | ---- | ---- |
| users.role | str (user/admin/system_admin) | user_role enum (user/admin/system_admin) | ✅ |
| agents.status | str (idle/busy/error/offline) | agent_status enum (idle/busy/error/offline) | ✅ |
| projects.status | str (created/in_progress/completed/cancelled) | project_status enum (created/in_progress/completed/cancelled) | ✅ |
| projects.deleted_at | Optional[datetime] | TIMESTAMPTZ NULLABLE | ✅ |
| group_messages.sender_type | str (user/agent) | sender_type enum (user/agent) | ✅ |
| group_messages.mentions | Optional[Dict[str, Any]] | JSONB | ✅ |
| swarms.manager_agent_id | int (NOT NULL) | INTEGER NOT NULL FK→agents.id | ✅ |
| group_members | user_id + agent_name 双字段 | user_id NULLABLE + agent_name NULLABLE | ✅ |

#### 9.6.2 后端 API ↔ 前端 API

| 验证项 | 后端定义 | 前端定义 | 验证结果 |
| ---- | ---- | ---- | ---- |
| 项目更新 | PATCH /api/v1/projects/:id | PATCH /projects/:id | ✅ |
| 通知已读 | PATCH /api/v1/notifications/:id/read | PATCH /notifications/:id/read | ✅ |
| 任务状态更新 | PATCH /api/v1/tasks/:id | PATCH /tasks/:id | ✅ |
| ws-token 端点 | V41 已移除 (使用 access_token) | V20 无此端点 | ✅ |
| 用户设置 | GET/PATCH /api/v1/settings | GET/PATCH /settings | ✅ |
| WebSocket 端点 | 多连接方案 (3端点) | 多连接方案 (3端点) | ✅ |
| WS 认证 token | ws_token | ws_token | ✅ |
| WS 响应类型 | auth_ok/auth_fail | auth_ok/auth_fail | ✅ |

#### 9.6.3 后端设计 ↔ 架构设计

| 验证项 | 后端定义 | 架构定义 | 验证结果 |
| ---- | ---- | ---- | ---- |
| 代码仓库路径 | /api/v1/projects/:id/repo/* | /api/v1/projects/{id}/repo/* | ✅ |
| WebSocket 端点 | ws://host/ws (单连接) | ws://host/ws (频道路由) | ✅ |
| step_events 表 | 已定义 | 已定义 | ✅ |
| group_members 表 | user_id + agent_name | user_id + agent_name | ✅ |

### 9.7 V39 已修正问题继承说明

以下修正项在 V39 中已完成，V40 予以继承和确认：
- projects → groups 关系从 1:1 修正为 1:N（V36 修正，V40 继续保持）
- 项目步骤端点路径别名 GET /api/v1/projects/:id/steps（V36 新增，V40 继续保持）
- SwarmOut.dissolved_at 字段（V37 新增，V40 继续保持）
- ArtifactOut.storage_path 字段（V37 新增，V40 继续保持）

---
