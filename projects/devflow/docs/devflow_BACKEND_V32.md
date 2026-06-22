# DevFlow 项目管理平台 - 后端设计文档

**版本**: V32
**日期**: 2026-06-15
**作者**: HouWang (后旺)
**状态**: 修订版V32（V30 文档内容无不合格项，本次为版本延续）

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
| 数据库   | PostgreSQL 14+             | 主存储引擎，JSONB、全文检索、分区表        |
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
│   │   └── audit_log.py            # V30 新增：审计日志模型
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
│   │   └── audit_log.py            # V30 新增：审计日志 schema
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
│   │   └── health.py               # V30 新增：健康检查路由
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
│   │   └── audit_log_service.py    # V30 新增：审计日志服务
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
│   │   └── audit_log_repo.py       # V30 新增：审计日志 Repository
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

**成功响应**:

```json
{
  "success": true,
  "data": { ... },
  "message": "success",
  "pagination": {
    "has_more": false,
    "next_cursor": null,
    "limit": 20,
    "total": 10
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

请求示例: `GET /api/v1/projects/:id/tasks?cursor=eyJpZCI6MTAwfQ==&limit=20`

首次请求不传 cursor 或传 `cursor=0`，返回最前面的 N 条。

**排序参数**:

| 参数 | 格式 | 示例 | 说明 |
| ---- | ---- | ---- | ---- |
| sort | `field,asc/desc` | `sort=created_at,desc` | 多个排序用逗号分隔: `sort=name,asc&sort=created_at,desc` |

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

### 2.2.1 认证流程详细设计

**认证流程**:

```
1. 用户登录 → 服务端验证凭证 → 签发 Access Token + Refresh Token
2. 前端请求携带 Authorization: Bearer ***
3. Token 过期 → 使用 Refresh Token 获取新的一对 Token
4. 用户登出 → Access Token 加入黑名单 → Refresh Token 失效
```

**Token 说明**:
- Access Token: 有效期 15 分钟，签名算法 RS256
- Refresh Token: 有效期 7 天，轮换机制（每次使用后旧 Token 立即失效）
- Token 存储在 Redis 黑名单中用于吊销，键格式 `token:blacklist:{jti}`

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
    "expires_in": 900,
    "user": {
      "id": 1,
      "username": "devuser",
      "email": "devuser@example.com",
      "role": "user",
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
    "expires_in": 900,
    "user": {
      "id": 2,
      "username": "newuser",
      "email": "newuser@example.com",
      "role": "user",
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
    "expires_in": 900
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
  "detail": "Access Token 已超过 15 分钟有效期，请使用 Refresh Token 刷新或重新登录",
  "trace_id": "trace-jkl-012"
}
```

### 2.3 项目管理

| 方法     | 路径                            | 描述                | 认证  |
| ------ | ----------------------------- | ----------------- | --- |
| GET    | /api/v1/projects              | 获取用户项目列表 (分页)     | 是   |
| POST   | /api/v1/projects              | 创建项目 (第一步：人类用户执行) | 是   |
| GET    | /api/v1/projects/:id          | 获取项目详情            | 是   |
| PUT    | /api/v1/projects/:id          | 更新项目信息            | 是   |
| DELETE | /api/v1/projects/:id          | 软删除项目             | 是   |
| GET    | /api/v1/projects/:id/progress | 获取 16 步流程进度       | 是   |

**GET /api/v1/projects** - 获取用户项目列表

查询参数:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
| ---- | ---- | ---- | ------ | ---- |
| page | int | 否 | 1 | 页码 |
| limit | int | 否 | 20 | 每页条数 (1-100) |
| sort | string | 否 | created_at,desc | 排序字段和方向 |
| status | string | 否 | null | 按状态过滤: active/paused/completed/archived |

成功响应 (200 OK):

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "DevFlow Platform",
      "description": "AI Agent 驱动的全自动开发工具",
      "owner_id": 1,
      "current_step": 5,
      "status": "active",
      "gitea_repo_id": 10,
      "created_at": "2026-06-01T08:00:00Z",
      "updated_at": "2026-06-15T12:00:00Z"
    }
  ],
  "pagination": {
    "has_more": true,
    "next_cursor": null,
    "limit": 20,
    "total": 42
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
| name | string | 是 | 长度 1-255 字符，不能全空白 |
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

**PUT /api/v1/projects/:id** - 更新项目信息

请求体 (所有字段可选):

```json
{
  "name": "新项目名称",
  "description": "更新后的描述"
}
```

成功响应 (200 OK): 返回更新后的 ProjectOut 对象

**DELETE /api/v1/projects/:id** - 软删除项目

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "status": "archived",
    "archived_at": "2026-06-29T10:00:00Z"
  },
  "message": "项目已归档"
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
        "status": "running",
        "assigned_agent": "houfu",
        "started_at": "2026-06-15T10:00:00Z",
        "completed_at": null
      }
    ]
  }
}
```

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
    "status": "running",
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
    "current_status": "running",
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
| PUT    | /api/v1/tasks/:id                      | 更新任务状态          | 是   |
| POST   | /api/v1/tasks/batch/update             | 批量更新任务状态       | 是   |
| GET    | /api/v1/tasks/:id/dependencies         | 获取任务依赖图         | 是   |
| POST   | /api/v1/tasks/:id/dependencies         | 添加任务依赖          | 是   |
| DELETE | /api/v1/tasks/:id/dependencies/:dep_id | 移除任务依赖          | 是   |

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
| status | string | 是 | pending/running/completed/failed/cancelled |

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

| 方法   | 路径                                         | 描述                 | 认证  |
| ---- | ------------------------------------------ | ------------------ | --- |
| POST | /api/v1/repos                              | 创建代码仓库 (项目创建时自动调用) | 是   |
| GET  | /api/v1/repos/:repo_id                     | 获取仓库详情             | 是   |
| GET  | /api/v1/repos/:repo_id/branches            | 获取分支列表             | 是   |
| POST | /api/v1/repos/:repo_id/branches            | 创建分支               | 是   |
| GET  | /api/v1/repos/:repo_id/pulls               | 获取 PR 列表           | 是   |
| POST | /api/v1/repos/:repo_id/pulls               | 创建 Pull Request    | 是   |
| POST | /api/v1/repos/:repo_id/pulls/:number/merge | 合并 PR              | 是   |
| GET  | /api/v1/repos/:repo_id/commits             | 获取提交记录             | 是   |
| POST | /api/v1/repos/:repo_id/validate-commit     | 验证提交消息规范           | 是   |
| POST | /api/v1/repos/:repo_id/tag                 | 创建版本标签 (项目完成时)     | 是   |

### 2.12 通知

| 方法     | 路径                             | 描述       | 认证  |
| ------ | ------------------------------ | -------- | --- |
| GET    | /api/v1/notifications          | 获取用户通知列表 | 是   |
| PUT    | /api/v1/notifications/:id/read | 标记通知已读   | 是   |
| PUT    | /api/v1/notifications/read-all | 全部标记已读   | 是   |
| DELETE | /api/v1/notifications/:id      | 删除通知     | 是   |

### 2.13 文件产出物管理

| 方法     | 路径                                               | 描述                            | 认证  |
| ------ | ------------------------------------------------ | ----------------------------- | --- |
| POST   | /api/v1/projects/:id/artifacts/upload            | 上传文档产出物 (multipart/form-data) | 是   |
| GET    | /api/v1/projects/:id/artifacts                   | 列出项目产出物文件列表 (分页)              | 是   |
| GET    | /api/v1/projects/:id/artifacts/:file_id          | 获取文件元信息                       | 是   |
| GET    | /api/v1/projects/:id/artifacts/:file_id/download | 下载产出物文件                       | 是   |
| DELETE | /api/v1/projects/:id/artifacts/:file_id          | 删除产出物文件                       | 是   |

### 2.14 系统管理

| 方法   | 路径                     | 描述              | 认证    |
| ---- | ---------------------- | --------------- | ----- |
| GET  | /api/v1/system/health  | 系统健康检查 (所有 Gateway) | 是     |
| GET  | /api/v1/system/metrics | Prometheus 指标端点 | 否     |
| GET  | /api/v1/system/stats   | 系统统计信息          | Admin |
| POST | /api/v1/system/backup  | 触发手动备份          | Admin |
| POST | /api/v1/system/migrate | 执行数据迁移          | Admin |

### 2.15 健康检查端点 (V30 新增)

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

### 2.16 WebSocket 端点

| 端点                                | 用途                      | 认证  |
| --------------------------------- | ----------------------- | --- |
| ws://host/ws/group-chat           | 群聊实时通信 (JWT Query 参数认证) | 是   |
| ws://host/ws/notifications        | 通知推送 (JWT Query 参数认证)   | 是   |
| ws://host/ws/workflow/:project_id | 流程状态推送 (JWT Query 参数认证) | 是   |

### 2.17 游标分页规范

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
  - Celery Worker 启动时: 扫描 Redis 中状态为 `running` 的 Celery 任务，检查对应 Agent 是否仍在执行，若不一致则标记为 `error` 并触发重试
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
          → task_repo.update_status()                   [写: tasks.status='running']
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
| 执行结果保存     | task 结果写入 + workflow_progress 更新    | READ COMMITTED | 事务回滚，状态恢复为 running |
| QA 检验提交    | qa_record 创建 + workflow_progress 更新 | READ COMMITTED | 事务回滚，状态恢复为 running |
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
            await self.statemachine.transition_to(project_id, step_number, "running")

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

### 3.9 业务异常场景处理 (V30 新增)

**场景 1: Agent 执行失败**

```
步骤: Agent 执行 → 失败
处理:
1. 记录执行日志到 agent_execution_logs (action='failed')
2. 更新 workflow_progress.status = 'failed'
3. 检查重试次数:
   - 重试次数 < 3: 自动重试 (指数退避: 30s/60s/120s)
   - 重试次数 = 3: 触发备用 Agent 切换
4. 备用 Agent 不可用: 通知人类用户，暂停任务
5. WebSocket 推送失败事件到前端
```

**场景 2: 蜂群崩溃**

```
步骤: 蜂群执行中 → 一个或多个成员崩溃
处理:
1. 检测机制: Celery 任务超时 (30 分钟) 或主动心跳超时 (5 分钟)
2. 标记崩溃 Agent 为 'error' 状态
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
2. 更新 workflow_progress.status = 'qa_failed'
3. 检查轮次:
   - review_round < 3: 退回重做 (step_executor.retry_with_feedback)
   - review_round = 3: 海梅介入，在讨论群中协调处理
4. 24 小时时限:
   - 限时内完成: 重新提交 QA 检验
   - 超时: 海梅介入，通知人类用户
5. WebSocket 推送 QA 结果到前端
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
    role: str
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
```

### 4.3 项目 Schema (schemas/project.py)

```python
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=5000)

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)

class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    current_step: int
    status: str
    gitea_repo_id: Optional[int]
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

### 4.4 Agent Schema (schemas/agent.py)

```python
class AgentOut(BaseModel):
    id: int
    name: str
    profile_name: str
    role: str
    status: str
    is_named: bool
    current_load: float
    max_concurrent: int
    last_heartbeat: Optional[datetime]

class AgentStatusReport(BaseModel):
    status: str = Field(..., pattern=r'^(idle|busy|error|offline)$')
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

### 4.5 任务 Schema (schemas/task.py)

```python
class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=10000)
    step_number: int = Field(..., ge=1, le=16)
    acceptance_criteria: Optional[str] = None
    priority: int = Field(5, ge=1, le=10)
    estimated_minutes: Optional[int] = None

class TaskUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r'^(pending|running|completed|failed|cancelled)$')
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
    estimated_minutes: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class TaskBatchUpdateRequest(BaseModel):
    task_ids: List[int] = Field(..., min_length=1)
    status: str = Field(..., pattern=r'^(pending|running|completed|failed|cancelled)$')

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
    score: int
    acceptance_result: str
    problem_details: Optional[str]
    review_round: int
    created_at: datetime

class QARollbackRequest(BaseModel):
    problem_details: str = Field(..., min_length=1, max_length=10000)
    review_dimensions: List[Dict[str, Any]]
    score: int = Field(..., ge=0, le=100)
```

### 4.7 蜂群 Schema (schemas/swarm.py)

```python
class SwarmCreate(BaseModel):
    project_id: int
    step_number: int = Field(..., ge=1, le=16)
    task_type: str  # tdd_test / code_writing / testing

class SwarmOut(BaseModel):
    id: int
    project_id: int
    step_number: int
    manager_agent_id: int
    status: str
    task_count: int
    completed_count: int
    agents: List[SwarmAgentOut]
    created_at: datetime

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
    member_type: str
    member_id: int
    joined_at: datetime

class GroupMemberAdd(BaseModel):
    member_type: str = Field(..., pattern=r"^(user|agent)$")
    member_id: int

class GroupMessageOut(BaseModel):
    id: int
    group_id: int
    sender_type: str
    sender_id: Optional[int]
    content: str
    message_type: str
    mentions: Optional[List[str]]
    created_at: datetime

class GroupModeUpdate(BaseModel):
    mode: str = Field(..., pattern=r"^(discussion|meeting)$")
```

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
```

### 4.10 通知 Schema (schemas/notification.py)

```python
class NotificationOut(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int]
    type: str
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
                  ┌──────────────┐
                  │meeting_agendas│
                  └──────────────┘

┌──────────┐     ┌─────────────────────┐
│  tasks   │────<│agent_execution_logs │
└──────────┘     └─────────────────────┘

┌──────────┐     ┌──────────┐
│ projects │────<│artifacts │
└──────────┘     └──────────┘

┌──────────┐     ┌──────────────┐  (V30 新增)
│  system  │────<│ audit_logs   │
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
| role          | VARCHAR(20)  | NOT NULL, DEFAULT 'user' | 角色: user/admin |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()  | 创建时间           |
| updated_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()  | 更新时间           |
| is_active     | BOOLEAN      | NOT NULL, DEFAULT true   | 是否激活           |

索引: `idx_users_username`, `idx_users_email`

#### 5.2.2 projects

| 字段            | 类型           | 约束                         | 说明                                   |
| ------------- | ------------ | -------------------------- | ------------------------------------ |
| id            | BIGSERIAL    | PRIMARY KEY                | 项目 ID                                |
| name          | VARCHAR(255) | NOT NULL                   | 项目名称                                 |
| description   | TEXT         |                            | 项目描述                                 |
| owner_id      | BIGINT       | NOT NULL, FK→users.id      | 项目所有者                                |
| current_step  | SMALLINT     | NOT NULL, DEFAULT 1        | 当前流程步骤 (1-16)                        |
| status        | VARCHAR(20)  | NOT NULL, DEFAULT 'active' | 状态: active/paused/completed/archived |
| gitea_repo_id | INTEGER      |                            | Gitea 仓库 ID                          |
| created_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()    | 创建时间                                 |
| updated_at    | TIMESTAMPTZ  | NOT NULL, DEFAULT now()    | 更新时间                                 |

索引: `idx_projects_owner_id`, `idx_projects_status`, `idx_projects_created_at`

#### 5.2.3 workflow_progress

| 字段             | 类型          | 约束                       | 说明                                                                 |
| -------------- | ----------- | ------------------------ | ------------------------------------------------------------------ |
| id             | BIGSERIAL   | PRIMARY KEY              | 记录 ID                                                              |
| project_id     | BIGINT      | NOT NULL, FK→projects.id | 项目 ID                                                              |
| step_number    | SMALLINT    | NOT NULL                 | 步骤编号 (1-16)                                                        |
| status         | VARCHAR(20) | NOT NULL                 | pending/running/qa_pending/qa_passed/qa_failed/completed/cancelled |
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
| status         | VARCHAR(20)  | NOT NULL, DEFAULT 'idle'      | idle/busy/offline/error |
| is_named       | BOOLEAN      | NOT NULL, DEFAULT false       | 是否为命名 Agent             |
| skills         | JSONB        |                               | 技能列表                    |
| current_load   | FLOAT        | NOT NULL, DEFAULT 0           | 当前负载 (0-1)              |
| max_concurrent | SMALLINT     | NOT NULL, DEFAULT 1           | 最大并发数                   |
| last_heartbeat | TIMESTAMPTZ  |                               | 最后心跳时间                  |
| created_at     | TIMESTAMPTZ  | NOT NULL, DEFAULT now()       | 创建时间                    |
| updated_at     | TIMESTAMPTZ  | NOT NULL, DEFAULT now()       | 更新时间                    |

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
| status              | VARCHAR(20)  | NOT NULL, DEFAULT 'pending' | pending/running/completed/failed/cancelled |
| assigned_agent_id   | BIGINT       | FK→agents.id                | 分配的 Agent ID                               |
| acceptance_criteria | TEXT         |                            | 验收标准                                       |
| priority            | SMALLINT     | NOT NULL, DEFAULT 5         | 优先级 (1-10, 10 最高)                          |
| estimated_minutes   | INTEGER      |                            | 预估耗时 (分钟)                                  |
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

| 字段          | 类型          | 约束                      | 说明               |
| ----------- | ----------- | ----------------------- | ---------------- |
| id          | BIGSERIAL   | PRIMARY KEY             | 成员 ID            |
| group_id    | BIGINT      | NOT NULL, FK→groups.id  | 群组 ID            |
| member_type | VARCHAR(20) | NOT NULL                | user/agent       |
| member_id   | BIGINT      | NOT NULL                | 用户 ID 或 Agent ID |
| joined_at   | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 加入时间             |

索引: `idx_gm_group`, UNIQUE: `(group_id, member_type, member_id)`

#### 5.2.10 group_messages

| 字段           | 类型          | 约束                           | 说明                    |
| ------------ | ----------- | ---------------------------- | --------------------- |
| id           | BIGSERIAL   | PRIMARY KEY                  | 消息 ID                 |
| group_id     | BIGINT      | NOT NULL, FK→groups.id       | 群组 ID                 |
| sender_type  | VARCHAR(20) | NOT NULL                     | user/agent/system     |
| sender_id    | BIGINT      | sender_type='system' 时为 NULL | 发送者 ID                |
| content      | TEXT        | NOT NULL                     | 消息内容                  |
| message_type | VARCHAR(20) | NOT NULL, DEFAULT 'text'     | text/system/meeting   |
| mentions     | JSONB       |                              | @mention 的 Agent/用户列表 |
| is_delivered | BOOLEAN     | NOT NULL, DEFAULT false      | 是否已投递给在线用户            |
| created_at   | TIMESTAMPTZ | NOT NULL, DEFAULT now()      | 发送时间                  |

索引: `idx_gm_group_time`, `idx_gm_sender`, `idx_gm_delivered`

#### 5.2.11 swarms

| 字段               | 类型          | 约束                         | 说明                         |
| ---------------- | ----------- | -------------------------- | -------------------------- |
| id               | BIGSERIAL   | PRIMARY KEY                | 蜂群 ID                      |
| project_id       | BIGINT      | NOT NULL, FK→projects.id   | 所属项目                       |
| step_number      | SMALLINT    | NOT NULL                   | 所属步骤                       |
| manager_agent_id | BIGINT      | NOT NULL, FK→agents.id     | 管理者 Agent (后发/后达)          |
| status           | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active/completed/dissolved |
| task_count       | INTEGER     | NOT NULL, DEFAULT 0        | 任务总数                       |
| completed_count  | INTEGER     | NOT NULL, DEFAULT 0        | 已完成任务数                     |
| created_at       | TIMESTAMPTZ | NOT NULL, DEFAULT now()    | 创建时间                       |
| dissolved_at     | TIMESTAMPTZ |                            | 解散时间                       |

索引: `idx_swarms_project`, `idx_swarms_status`

#### 5.2.12 swarm_agents

| 字段               | 类型          | 约束                       | 说明                      |
| ---------------- | ----------- | ------------------------ | ----------------------- |
| id               | BIGSERIAL   | PRIMARY KEY              | 记录 ID                   |
| swarm_id         | BIGINT      | NOT NULL, FK→swarms.id   | 蜂群 ID                   |
| agent_id         | BIGINT      | NOT NULL, FK→agents.id   | Agent ID                |
| status           | VARCHAR(20) | NOT NULL, DEFAULT 'idle' | idle/busy/offline/error |
| assigned_task_id | BIGINT      | FK→tasks.id              | 当前分配的任务 ID              |
| joined_at        | TIMESTAMPTZ | NOT NULL, DEFAULT now()  | 加入时间                    |
| left_at          | TIMESTAMPTZ |                          | 退出时间                    |

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
| score             | SMALLINT    | NOT NULL                 | 综合评分 (0-100)       |
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

| 字段         | 类型          | 约束                      | 说明    |
| ---------- | ----------- | ----------------------- | ----- |
| id         | BIGSERIAL   | PRIMARY KEY             | 通知 ID |
| user_id    | BIGINT      | NOT NULL, FK→users.id   | 接收用户  |
| project_id | BIGINT      | FK→projects.id          | 关联项目  |
| type       | VARCHAR(50) | NOT NULL                | 通知类型  |
| content    | TEXT        | NOT NULL                | 通知内容  |
| is_read    | BOOLEAN     | NOT NULL, DEFAULT false | 是否已读  |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间  |

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

| 字段               | 类型          | 约束                      | 说明                                                    |
| ---------------- | ----------- | ----------------------- | ----------------------------------------------------- |
| id               | BIGSERIAL   | PRIMARY KEY             | 日志 ID                                                 |
| task_id          | BIGINT      | NOT NULL, FK→tasks.id   | 任务 ID                                                 |
| agent_id         | BIGINT      | NOT NULL, FK→agents.id  | Agent ID                                              |
| action           | VARCHAR(50) | NOT NULL                | dispatched/retried/succeeded/failed/timeout/escalated |
| details          | JSONB       |                         | 详细信息 (错误消息、重试次数等)                                     |
| duration_seconds | INTEGER     |                         | 执行耗时                                                  |
| created_at       | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 记录时间                                                  |

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

### 5.3 表关系总结

| 关系                           | 类型  | 说明                     |
| ---------------------------- | --- | ---------------------- |
| users → projects             | 1:N | 一个用户可创建多个项目            |
| projects → workflow_progress | 1:N | 一个项目有 16 条流程进度记录       |
| projects → tasks             | 1:N | 一个项目有多个任务              |
| projects → groups            | 1:1 | 一个项目一个讨论群              |
| projects → repositories      | 1:1 | 一个项目一个代码仓库             |
| projects → swarms            | 1:N | 一个项目可建立多个蜂群            |
| projects → artifacts         | 1:N | 一个项目有多个产出文件            |
| groups → group_members       | 1:N | 一个群组有多个成员              |
| groups → group_messages      | 1:N | 一个群组有多条消息              |
| groups → meeting_outcomes    | 1:N | 一个群组有多次会议结果            |
| swarms → swarm_agents        | 1:N | 一个蜂群有多个 Agent          |
| tasks → qa_records           | 1:N | 一个任务可有多次 QA 检验         |
| tasks → agent_execution_logs | 1:N | 一个任务有多条执行日志            |
| tasks → tasks (self)         | M:N | 通过 task_dependencies 表 |

### 5.4 索引设计与查询优化 (V30 新增)

**索引设计原则**:
1. 所有外键字段建立索引，加速 JOIN 查询
2. 高频查询字段建立索引（如 status、created_at）
3. 组合索引按查询频率和选择性排序
4. JSONB 字段使用 GIN 索引支持部分查询

**关键索引**:

| 表              | 索引名                      | 字段                        | 类型     | 用途              |
| -------------- | ------------------------ | ------------------------- | ------ | --------------- |
| projects       | idx_projects_owner_id    | owner_id                  | B-tree | 按用户查询项目列表     |
| projects       | idx_projects_status      | status                    | B-tree | 按状态过滤项目       |
| projects       | idx_projects_created_at  | created_at DESC           | B-tree | 项目列表默认排序     |
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
