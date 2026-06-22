# DevFlow 项目管理平台 - 后端设计文档

**版本**: V20
**日期**: 2026-06-22
**作者**: HouWang (后旺)
**状态**: 修订版V20（根据后荣检验报告V19全面修订）

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

| 层 | 技术 | 说明 |
|---|---|---|
| 应用框架 | Python 3.11 + FastAPI | 异步高性能 Web 框架，原生支持 WebSocket |
| ORM | SQLAlchemy 2.0 | 异步 ORM，支持 PostgreSQL 全特性 |
| 任务队列 | Celery + Redis | 异步任务调度，支持 Agent 执行、蜂群调度等 |
| 缓存/状态 | Redis 6+ | Agent 状态缓存、会话管理、分布式锁 |
| 数据库 | PostgreSQL 14+ | 主存储引擎，JSONB、全文检索、分区表 |
| 实时通信 | FastAPI WebSocket | 群聊消息、流程状态推送、流式响应 |
| 认证 | JWT (PyJWT) | 无状态 Token 认证 |
| 监控 | Prometheus + OpenTelemetry | 指标采集、链路追踪 |
| 日志 | Python logging + JSON 格式 | 结构化日志，ELK Stack 集中管理 |
| 部署 | Docker + Docker Compose | 容器化部署 |

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
│   │   └── artifact.py             # V19 新增：文件产出物模型
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
│   │   └── artifact.py             # V19 新增：文件产出物 schema
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
│   │   └── artifacts.py            # V19 新增：文件产出物路由
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
│   │   └── artifact_service.py     # V19 新增：文件产出物服务
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
│   │   └── artifact_repo.py        # V19 新增：文件产出物 Repository
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
- **错误码**: HTTP 状态码 + 业务错误码
- **Conventional Commits**: 所有代码提交遵循 Conventional Commits 规范
- **API 文档**: FastAPI 自动生成 OpenAPI/Swagger 文档，访问 `/docs` (Swagger UI) 和 `/redoc` (ReDoc)
- **API 版本化**: URL 路径版本化 (`/api/v1/`)。MAJOR 版本变更可能引入不兼容修改；MINOR 版本保证向后兼容。废弃的端点将在响应头中包含 `Deprecation: true`，并至少保留到下一个 MINOR 版本发布后

### 2.2 认证与用户

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| POST | /api/v1/auth/login | 用户登录 | 否 |
| POST | /api/v1/auth/register | 用户注册 | 否 |
| POST | /api/v1/auth/refresh | 刷新 Token | 是 |
| POST | /api/v1/auth/logout | 用户登出 (加入 Token 黑名单) | 是 |
| GET | /api/v1/auth/me | 获取当前用户信息 | 是 |

### 2.3 项目管理

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/projects | 获取用户项目列表 (分页) | 是 |
| POST | /api/v1/projects | 创建项目 (第一步：人类用户执行) | 是 |
| GET | /api/v1/projects/:id | 获取项目详情 | 是 |
| PUT | /api/v1/projects/:id | 更新项目信息 | 是 |
| DELETE | /api/v1/projects/:id | 软删除项目 | 是 |
| GET | /api/v1/projects/:id/progress | 获取 16 步流程进度 | 是 |

### 2.4 16 步流程调度

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| POST | /api/v1/projects/:id/workflow/step/:number | 执行指定步骤 (:number 为 2-16) | 是 |
| GET | /api/v1/projects/:id/workflow/status | 获取当前流程状态 | 是 |
| POST | /api/v1/projects/:id/workflow/rollback | 回退到指定步骤 (用于迭代) | 是 |

V19 修订说明：将 V18 中的 `PUT` 改为 `POST`。执行步骤是一个动作操作，不是替换资源，POST 语义更正确。

`POST /api/v1/projects/:id/workflow/step/:number` 端点说明：
- `:number` 路径参数为 2-16 之间的整数，对应第二步至第十六步
- 请求体可选，用于传递步骤执行参数
- **请求体示例**:
  ```json
  {
    "options": {
      "force_rerun": false,
      "custom_agent": null
    }
  }
  ```
- **成功响应示例 (202 Accepted)**:
  ```json
  {
    "task_id": 42,
    "step_number": 3,
    "status": "running",
    "assigned_agent": "houxing",
    "message": "步骤执行已启动",
    "estimated_duration_seconds": 900
  }
  ```
- **失败响应示例 (422 Unprocessable Entity)**:
  ```json
  {
    "error": "前置条件未满足",
    "code": 422,
    "detail": "请先完成第二步",
    "trace_id": "abc-123-def"
  }
  ```
- 服务端根据 `:number` 自动匹配对应步骤的 Agent 角色并分派任务
- 各步骤对应的 Agent 角色参见 5.2 节 WorkflowStep 与 workflow_steps 配置表

### 2.5 任务管理

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/projects/:id/tasks | 获取项目任务列表 | 是 |
| GET | /api/v1/tasks/:id | 获取任务详情 | 是 |
| PUT | /api/v1/tasks/:id | 更新任务状态 | 是 |
| POST | /api/v1/tasks/batch/update | V19 新增：批量更新任务状态 | 是 |
| GET | /api/v1/tasks/:id/dependencies | 获取任务依赖图 | 是 |
| POST | /api/v1/tasks/:id/dependencies | 添加任务依赖 | 是 |
| DELETE | /api/v1/tasks/:id/dependencies/:dep_id | 移除任务依赖 | 是 |

`POST /api/v1/tasks/batch/update` (V19 新增) 批量操作端点：
- **请求体示例**:
  ```json
  {
    "task_ids": [1, 2, 3],
    "status": "completed"
  }
  ```
- **响应示例 (200 OK)**:
  ```json
  {
    "updated": 3,
    "failed": [],
    "message": "批量更新完成"
  }
  ```

### 2.6 Agent 管理

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/agents | 获取所有 Agent 列表 | 是 |
| GET | /api/v1/agents/:id | 获取 Agent 详情 | 是 |
| GET | /api/v1/agents/named | 获取 9 个命名 Agent 列表 | 是 |
| POST | /api/v1/agents/register | 编程 Agent 注册 (蜂群成员) | 是 |
| DELETE | /api/v1/agents/:id | 移除蜂群 Agent | 是 |
| GET | /api/v1/profiles | 获取扫描到的 Hermes Profiles | 是 |
| POST | /api/v1/profiles/scan | 手动触发 Profile 扫描 | 是 |
| GET | /api/v1/agents/:id/load | 获取 Agent 负载信息 | 是 |
| POST | /api/v1/agents/:id/status-report | Agent 主动上报状态变更 | 是 |

### 2.7 QA 门控

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| POST | /api/v1/qa/:task_id/inspect | 提交产出供后荣检验 | 是 |
| GET | /api/v1/qa/:project_id/records | 获取项目 QA 检验记录 | 是 |
| POST | /api/v1/qa/:task_id/rollback | 退回重做 (附带修改建议) | 是 |
| GET | /api/v1/qa/:task_id/status | 获取当前检验状态 | 是 |
| GET | /api/v1/qa/:task_id/records | 获取任务的历次检验记录 | 是 |

### 2.8 Agent 蜂群

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| POST | /api/v1/swarms | 建立 Agent 蜂群 | 是 |
| GET | /api/v1/swarms | 获取蜂群列表 | 是 |
| GET | /api/v1/swarms/:id | 获取蜂群详情 | 是 |
| POST | /api/v1/swarms/:id/tasks/dispatch | 分发任务到蜂群成员 | 是 |
| GET | /api/v1/swarms/:id/progress | 获取蜂群执行进度 | 是 |
| DELETE | /api/v1/swarms/:id | 解散蜂群 | 是 |
| GET | /api/v1/swarms/:swarm_id/tasks/:agent_id | 蜂群 Agent 获取分配任务 | 是 |
| POST | /api/v1/swarms/:swarm_id/tasks/:agent_id/acknowledge | 蜂群 Agent 确认接收任务 | 是 |
| POST | /api/v1/swarms/:swarm_id/tasks/:task_id/progress | 蜂群 Agent 上报任务进度 | 是 |
| POST | /api/v1/swarms/:swarm_id/tasks/:task_id/deliver | 蜂群 Agent 提交任务成果 | 是 |
| POST | /api/v1/swarms/:swarm_id/tasks/:task_id/error | 蜂群 Agent 上报执行错误 | 是 |

路径命名规范说明：所有蜂群相关端点均以 `/api/v1/swarms/` 为前缀（复数），蜂群内部子资源（tasks、progress 等）作为其从属路径，保证路径命名一致性。

### 2.9 项目讨论群

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/groups | 获取群组列表 | 是 |
| POST | /api/v1/groups | 创建群组 (第二步自动调用) | 是 |
| GET | /api/v1/groups/:group_id | 获取群组详情和成员 | 是 |
| PUT | /api/v1/groups/:group_id | 更新群组信息 | 是 |
| POST | /api/v1/groups/:group_id/members | 添加成员 | 是 |
| DELETE | /api/v1/groups/:group_id/members/:member_id | 移除成员 | 是 |
| GET | /api/v1/groups/:group_id/messages | 获取历史消息 (分页) | 是 |
| GET | /api/v1/groups/:group_id/outcomes | 获取会议结果列表 | 是 |
| POST | /api/v1/groups/:group_id/host | 设置主持人 | 是 |
| PUT | /api/v1/groups/:group_id/mode | 切换工作模式 (讨论/会议) | 是 |

### 2.10 Hermes Gateway 通信

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/hermes/health | 检查所有 Hermes Gateway 健康状态 | 是 |
| POST | /api/v1/hermes/chat | 与指定 Agent 对话 (非流式) | 是 |
| POST | /api/v1/hermes/chat/stream | 与指定 Agent 对话 (流式 SSE) | 是 |
| POST | /api/v1/hermes/tasks/decompose | 使用 Hermes Agent 拆解任务 | 是 |
| GET | /api/v1/hermes/:profile_name/status | 检查指定 Profile 运行状态 | 是 |
| POST | /api/v1/hermes/sync-profiles | 同步发现 profiles 到数据库 | 是 |

路由模块边界说明：Hermes Gateway 通信相关操作（健康检查、对话、任务拆解、Profile 同步等）统一归入 `/api/v1/hermes/` 前缀下，保持路由模块边界清晰。

### 2.11 代码仓库管理

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| POST | /api/v1/repos | 创建代码仓库 (项目创建时自动调用) | 是 |
| GET | /api/v1/repos/:repo_id | 获取仓库详情 | 是 |
| GET | /api/v1/repos/:repo_id/branches | 获取分支列表 | 是 |
| POST | /api/v1/repos/:repo_id/branches | 创建分支 | 是 |
| GET | /api/v1/repos/:repo_id/pulls | 获取 PR 列表 | 是 |
| POST | /api/v1/repos/:repo_id/pulls | 创建 Pull Request | 是 |
| POST | /api/v1/repos/:repo_id/pulls/:number/merge | 合并 PR | 是 |
| GET | /api/v1/repos/:repo_id/commits | 获取提交记录 | 是 |
| POST | /api/v1/repos/:repo_id/validate-commit | 验证提交消息规范 | 是 |
| POST | /api/v1/repos/:repo_id/tag | 创建版本标签 (项目完成时) | 是 |

路径命名一致性说明：所有同资源操作端点均包含 `:repo_id` 路径参数，`validate-commit` 端点与其他仓库操作端点保持一致的命名规范。

### 2.12 通知

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/notifications | 获取用户通知列表 | 是 |
| PUT | /api/v1/notifications/:id/read | 标记通知已读 | 是 |
| PUT | /api/v1/notifications/read-all | 全部标记已读 | 是 |
| DELETE | /api/v1/notifications/:id | 删除通知 | 是 |

### 2.13 文件产出物管理 (V19 新增)

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| POST | /api/v1/projects/:id/artifacts/upload | 上传文档产出物 (multipart/form-data) | 是 |
| GET | /api/v1/projects/:id/artifacts | 列出项目产出物文件列表 (分页) | 是 |
| GET | /api/v1/projects/:id/artifacts/:file_id | 获取文件元信息 | 是 |
| GET | /api/v1/projects/:id/artifacts/:file_id/download | 下载产出物文件 | 是 |
| DELETE | /api/v1/projects/:id/artifacts/:file_id | 删除产出物文件 | 是 |

文件产出物 API 说明：
- 上传支持最大 50MB 单文件，支持 .md/.txt/.json/.yaml/.py/.sh 等常见文档和代码格式
- 文件存储在服务器 `/data/devflow/artifacts/{project_id}/` 目录下
- 文件名自动附加 UUID 前缀防止冲突: `{uuid}_{original_filename}`
- 下载返回 `Content-Disposition: attachment` 头，触发浏览器下载
- 文件元数据（文件名、大小、类型、上传时间、上传者）持久化到 `artifacts` 表

### 2.14 系统管理

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/system/health | 系统健康检查 | 否 |
| GET | /api/v1/system/metrics | Prometheus 指标端点 | 否 |
| GET | /api/v1/system/stats | 系统统计信息 | Admin |
| POST | /api/v1/system/backup | 触发手动备份 | Admin |
| POST | /api/v1/system/migrate | 执行数据迁移 | Admin |

### 2.15 WebSocket 端点 (V19 补充)

| 端点 | 用途 | 认证 |
|---|---|---|
| ws://host/ws/group-chat | 群聊实时通信 (JWT Query 参数认证) | 是 |
| ws://host/ws/notifications | 通知推送 (JWT Query 参数认证) | 是 |
| ws://host/ws/workflow/:project_id | 流程状态推送 (JWT Query 参数认证) | 是 |

### 2.16 游标分页规范 (V19 新增)

游标分页使用场景：大数据量列表、无限滚动、实时流数据。

- **请求格式**: `GET /api/v1/projects/:id/tasks?cursor=***==&limit=20`
- **cursor 编码**: Base64(JSON({"id": last_seen_id}))，客户端将上一页最后一条记录的 ID 编码后传入
- **首次请求**: 不传 cursor 或传 `cursor=0`，返回最前面的 N 条
- **响应格式**:
  ```json
  {
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

---

## 4. 数据库表结构设计 (V19 新增)

### 4.1 ER 图 (ASCII)

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
│ (config) │                      │ 1:N        │
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
```

### 4.2 表定义

#### 4.2.1 users

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 用户 ID |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 用户名 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 哈希密码 |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'user' | 角色: user/admin |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 更新时间 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否激活 |

索引: `idx_users_username`, `idx_users_email`

#### 4.2.2 projects

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 项目 ID |
| name | VARCHAR(255) | NOT NULL | 项目名称 |
| description | TEXT | | 项目描述 |
| owner_id | BIGINT | NOT NULL, FK→users.id | 项目所有者 |
| current_step | SMALLINT | NOT NULL, DEFAULT 1 | 当前流程步骤 (1-16) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | 状态: active/paused/completed/archived |
| gitea_repo_id | INTEGER | | Gitea 仓库 ID |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 更新时间 |

索引: `idx_projects_owner_id`, `idx_projects_status`, `idx_projects_created_at`

#### 4.2.3 workflow_progress

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 记录 ID |
| project_id | BIGINT | NOT NULL, FK→projects.id | 项目 ID |
| step_number | SMALLINT | NOT NULL | 步骤编号 (1-16) |
| status | VARCHAR(20) | NOT NULL | pending/running/qa_pending/qa_passed/qa_failed/completed/cancelled |
| assigned_agent | VARCHAR(50) | | 负责 Agent Profile 名称 |
| started_at | TIMESTAMPTZ | | 开始时间 |
| completed_at | TIMESTAMPTZ | | 完成时间 |
| qa_record_id | BIGINT | FK→qa_records.id | 关联 QA 检验记录 |
| result_summary | JSONB | | 步骤执行结果摘要 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

索引: `idx_wp_project_step`, `idx_wp_status`, UNIQUE: `(project_id, step_number)`

#### 4.2.4 agents

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | Agent ID |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Agent 名称 |
| profile_name | VARCHAR(50) | UNIQUE, NOT NULL | Hermes Profile 名称 |
| role | VARCHAR(50) | NOT NULL | 角色描述 |
| gateway_host | VARCHAR(255) | NOT NULL, DEFAULT '127.0.0.1' | Gateway 地址 |
| gateway_port | INTEGER | NOT NULL | Gateway 端口 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'idle' | idle/busy/offline/error |
| is_named | BOOLEAN | NOT NULL, DEFAULT false | 是否为命名 Agent |
| skills | JSONB | | 技能列表 |
| current_load | FLOAT | NOT NULL, DEFAULT 0 | 当前负载 (0-1) |
| max_concurrent | SMALLINT | NOT NULL, DEFAULT 1 | 最大并发数 |
| last_heartbeat | TIMESTAMPTZ | | 最后心跳时间 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 更新时间 |

索引: `idx_agents_profile_name`, `idx_agents_status`, `idx_agents_is_named`

Agent 状态机: `idle → busy` (接收任务) → `idle` (完成任务) / `error` (执行失败) → `idle` (恢复)。`offline` 表示 Gateway 不可达，由健康检查自动更新。

#### 4.2.5 workflow_steps (配置表)

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 配置 ID |
| step_number | SMALLINT | NOT NULL | 步骤编号 (2-16) |
| step_name | VARCHAR(255) | NOT NULL | 步骤名称 |
| assignee_profile | VARCHAR(50) | NOT NULL | 负责 Agent 的 Profile |
| qa_required | BOOLEAN | NOT NULL, DEFAULT true | 是否需要 QA 门控 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否启用 |
| project_id | BIGINT | FK→projects.id, NULL=全局默认 | 项目级覆盖 (NULL 为全局) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

索引: `idx_ws_step_project`, UNIQUE: `(step_number, project_id)`

#### 4.2.6 tasks

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 任务 ID |
| project_id | BIGINT | NOT NULL, FK→projects.id | 项目 ID |
| step_number | SMALLINT | NOT NULL | 所属步骤 (1-16) |
| name | VARCHAR(255) | NOT NULL | 任务名称 |
| description | TEXT | | 任务描述 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | pending/running/completed/failed/cancelled |
| assigned_agent_id | BIGINT | FK→agents.id | 分配的 Agent ID |
| acceptance_criteria | TEXT | | 验收标准 |
| priority | SMALLINT | NOT NULL, DEFAULT 5 | 优先级 (1-10, 10 最高) |
| estimated_minutes | INTEGER | | 预估耗时 (分钟) |
| started_at | TIMESTAMPTZ | | 开始时间 |
| completed_at | TIMESTAMPTZ | | 完成时间 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 更新时间 |

索引: `idx_tasks_project`, `idx_tasks_step`, `idx_tasks_status`, `idx_tasks_agent`

#### 4.2.7 task_dependencies

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 依赖 ID |
| source_task_id | BIGINT | NOT NULL, FK→tasks.id | 前置任务 ID |
| target_task_id | BIGINT | NOT NULL, FK→tasks.id | 后继任务 ID |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否有效 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

索引: `idx_td_source`, `idx_td_target`, UNIQUE: `(source_task_id, target_task_id)`, 约束: `source_task_id != target_task_id`

#### 4.2.8 groups

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 群组 ID |
| project_id | BIGINT | NOT NULL, FK→projects.id | 所属项目 |
| name | VARCHAR(255) | NOT NULL | 群组名称 |
| mode | VARCHAR(20) | NOT NULL, DEFAULT 'discussion' | discussion/meeting |
| host_agent_id | BIGINT | FK→agents.id | 主持人 Agent ID |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 更新时间 |

索引: `idx_groups_project`, `idx_groups_mode`

#### 4.2.9 group_members

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 成员 ID |
| group_id | BIGINT | NOT NULL, FK→groups.id | 群组 ID |
| member_type | VARCHAR(20) | NOT NULL | user/agent |
| member_id | BIGINT | NOT NULL | 用户 ID 或 Agent ID |
| joined_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 加入时间 |

索引: `idx_gm_group`, UNIQUE: `(group_id, member_type, member_id)`

#### 4.2.10 group_messages

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 消息 ID |
| group_id | BIGINT | NOT NULL, FK→groups.id | 群组 ID |
| sender_type | VARCHAR(20) | NOT NULL | user/agent/system |
| sender_id | BIGINT |  sender_type='system' 时为 NULL | 发送者 ID |
| content | TEXT | NOT NULL | 消息内容 |
| message_type | VARCHAR(20) | NOT NULL, DEFAULT 'text' | text/system/meeting |
| mentions | JSONB | | @mention 的 Agent/用户列表 |
| is_delivered | BOOLEAN | NOT NULL, DEFAULT false | 是否已投递给在线用户 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 发送时间 |

索引: `idx_gm_group_time`, `idx_gm_sender`, `idx_gm_delivered`

#### 4.2.11 swarms

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 蜂群 ID |
| project_id | BIGINT | NOT NULL, FK→projects.id | 所属项目 |
| step_number | SMALLINT | NOT NULL | 所属步骤 |
| manager_agent_id | BIGINT | NOT NULL, FK→agents.id | 管理者 Agent (后发/后达) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active/completed/dissolved |
| task_count | INTEGER | NOT NULL, DEFAULT 0 | 任务总数 |
| completed_count | INTEGER | NOT NULL, DEFAULT 0 | 已完成任务数 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |
| dissolved_at | TIMESTAMPTZ | | 解散时间 |

索引: `idx_swarms_project`, `idx_swarms_status`

#### 4.2.12 swarm_agents

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 记录 ID |
| swarm_id | BIGINT | NOT NULL, FK→swarms.id | 蜂群 ID |
| agent_id | BIGINT | NOT NULL, FK→agents.id | Agent ID |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'idle' | idle/busy/offline/error |
| assigned_task_id | BIGINT | FK→tasks.id | 当前分配的任务 ID |
| joined_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 加入时间 |
| left_at | TIMESTAMPTZ | | 退出时间 |

索引: `idx_sa_swarm`, `idx_sa_agent`, UNIQUE: `(swarm_id, agent_id)`

#### 4.2.13 qa_records

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 记录 ID |
| task_id | BIGINT | NOT NULL, FK→tasks.id | 任务 ID |
| project_id | BIGINT | NOT NULL, FK→projects.id | 项目 ID |
| step_number | SMALLINT | NOT NULL | 步骤编号 |
| reviewer_agent_id | BIGINT | NOT NULL, FK→agents.id | 审查者 (后荣) |
| review_dimensions | JSONB | NOT NULL | 检验维度及得分 (见 8.3 节) |
| score | SMALLINT | NOT NULL | 综合评分 (0-100) |
| acceptance_result | VARCHAR(10) | NOT NULL | pass/fail |
| problem_details | TEXT | | 不合格时的修改建议 |
| review_round | SMALLINT | NOT NULL, DEFAULT 1 | 检验轮次 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 检验时间 |

索引: `idx_qr_task`, `idx_qr_project`, `idx_qr_result`

#### 4.2.14 repositories

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 仓库 ID |
| project_id | BIGINT | NOT NULL, FK→projects.id | 项目 ID |
| gitea_repo_id | INTEGER | NOT NULL | Gitea 仓库 ID |
| gitea_repo_name | VARCHAR(255) | NOT NULL | 仓库名称 |
| default_branch | VARCHAR(50) | NOT NULL, DEFAULT 'main' | 默认分支 |
| is_private | BOOLEAN | NOT NULL, DEFAULT true | 是否私有 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

索引: `idx_repos_project`, UNIQUE: `(project_id)`

#### 4.2.15 notifications

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 通知 ID |
| user_id | BIGINT | NOT NULL, FK→users.id | 接收用户 |
| project_id | BIGINT | FK→projects.id | 关联项目 |
| type | VARCHAR(50) | NOT NULL | 通知类型 |
| content | TEXT | NOT NULL | 通知内容 |
| is_read | BOOLEAN | NOT NULL, DEFAULT false | 是否已读 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 创建时间 |

索引: `idx_notifications_user`, `idx_notifications_read`

#### 4.2.16 meeting_outcomes

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 会议结果 ID |
| group_id | BIGINT | NOT NULL, FK→groups.id | 群组 ID |
| meeting_type | VARCHAR(50) | NOT NULL | 会议类型 |
| meeting_topic | VARCHAR(255) | NOT NULL | 会议主题 |
| host_agent_id | BIGINT | NOT NULL, FK→agents.id | 主持人 |
| agenda | JSONB | NOT NULL | 议程列表 |
| summary | TEXT | | 会议纪要 |
| decisions | JSONB | | 决议列表 |
| action_items | JSONB | | 待办任务 |
| risks | JSONB | | 风险点 |
| started_at | TIMESTAMPTZ | NOT NULL | 开始时间 |
| completed_at | TIMESTAMPTZ | | 结束时间 |

索引: `idx_mo_group`, `idx_mo_type`

#### 4.2.17 agent_execution_logs

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 日志 ID |
| task_id | BIGINT | NOT NULL, FK→tasks.id | 任务 ID |
| agent_id | BIGINT | NOT NULL, FK→agents.id | Agent ID |
| action | VARCHAR(50) | NOT NULL | dispatched/retried/succeeded/failed/timeout/escalated |
| details | JSONB | | 详细信息 (错误消息、重试次数等) |
| duration_seconds | INTEGER | | 执行耗时 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 记录时间 |

索引: `idx_ael_task`, `idx_ael_agent`, `idx_ael_action`

#### 4.2.18 artifacts (V19 新增)

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGSERIAL | PRIMARY KEY | 文件 ID |
| project_id | BIGINT | NOT NULL, FK→projects.id | 项目 ID |
| file_name | VARCHAR(500) | NOT NULL | 原始文件名 |
| stored_name | VARCHAR(500) | NOT NULL | 存储文件名 (带 UUID 前缀) |
| file_size | BIGINT | NOT NULL | 文件大小 (字节) |
| mime_type | VARCHAR(100) | NOT NULL | MIME 类型 |
| uploaded_by | VARCHAR(50) | NOT NULL | 上传者 (user_id 或 agent profile) |
| uploader_type | VARCHAR(20) | NOT NULL, DEFAULT 'user' | user/agent/system |
| storage_path | VARCHAR(1000) | NOT NULL | 服务器存储路径 |
| checksum | VARCHAR(64) | NOT NULL | SHA-256 校验和 |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | 上传时间 |

索引: `idx_artifacts_project`, `idx_artifacts_name`

### 4.3 表关系总结

| 关系 | 类型 | 说明 |
|---|---|---|
| users → projects | 1:N | 一个用户可创建多个项目 |
| projects → workflow_progress | 1:N | 一个项目有 16 条流程进度记录 |
| projects → tasks | 1:N | 一个项目有多个任务 |
| projects → groups | 1:1 | 一个项目一个讨论群 |
| projects → repositories | 1:1 | 一个项目一个代码仓库 |
| projects → swarms | 1:N | 一个项目可建立多个蜂群 |
| projects → artifacts | 1:N | 一个项目有多个产出文件 |
| groups → group_members | 1:N | 一个群组有多个成员 |
| groups → group_messages | 1:N | 一个群组有多条消息 |
| groups → meeting_outcomes | 1:N | 一个群组有多次会议结果 |
| swarms → swarm_agents | 1:N | 一个蜂群有多个 Agent |
| tasks → qa_records | 1:N | 一个任务可有多次 QA 检验 |
| tasks → agent_execution_logs | 1:N | 一个任务有多条执行日志 |
| tasks → tasks (self) | M:N | 通过 task_dependencies 表 |

---

## 5. 任务调度引擎

### 5.1 职责概述

任务调度引擎负责管理 16 步标准开发流程的执行，由海梅（HaiMei）作为总调度者：

1. 维护 16 步流程状态机
2. 自动推进流程步骤（当前一步完成后自动推进到下一步）
3. 管理任务依赖图（有向无环图）
4. 协调 Agent 间任务交接
5. 确保每步产出经 QA 门控检验合格后方可进入下一步

### 5.2 16 步流程状态机

```python
class WorkflowStep(Enum):
    STEP_1_USER_CREATE = 1       # 人类用户创建项目
    STEP_2_CORE_GOAL = 2         # 海梅确认核心目标+搭建组织架构
    STEP_3_REQUIREMENT = 3       # 后兴需求分析
    STEP_4_DESIGN = 4            # 后旺架构设计
    STEP_5_ENV_SETUP = 5         # 后富建立开发环境
    STEP_6_TDD_PLAN = 6          # 海梅制订 TDD 测试用例计划
    STEP_7_TDD_WRITING = 7       # 后发(蜂群)编写 TDD 测试用例
    STEP_8_CODE_PLAN = 8         # 海梅制订代码编写计划
    STEP_9_CODE_WRITING = 9      # 后发(蜂群)编写功能代码
    STEP_10_TEST_DEPLOY = 10     # 后富部署到测试环境
    STEP_11_TESTING = 11         # 后达(蜂群)全面测试
    STEP_12_SECURITY = 12        # 后华安全审计
    STEP_13_PROD_DEPLOY = 13     # 后富部署到生产环境
    STEP_14_DOCUMENTATION = 14   # 后贵完善文档
    STEP_15_DELIVERY = 15        # 海梅报告交付成果
    STEP_16_SATISFACTION = 16    # 用户满意度确认/迭代

    @property
    def qa_required(self) -> bool:
        """第一步无需 QA 门控，其余均需"""
        return self.value != 1

    @property
    def assignee_agent(self) -> Optional[str]:
        """返回负责该步骤的 Agent（从数据库配置表动态读取，非硬编码）"""
        # 实际实现通过 WorkflowService 查询 workflow_steps 配置表
        # 此处仅保留枚举定义，Agent 分配关系由数据库驱动
        return None  # 占位，实际由 WorkflowService._get_step_assignee() 提供
```

WorkflowStep.assignee_agent 修复说明：V13 中使用了硬编码字典映射步骤到 Agent 名称，不符合"不能接受硬编码，必须完全动态泛化"的要求。V14 改为从数据库 `workflow_steps` 配置表动态读取 Agent 分配关系，支持运行时动态调整。

Agent 分配关系存储在 `workflow_steps` 配置表中：

```python
# workflow_steps 表结构
class WorkflowStepConfig(Base):
    __tablename__ = "workflow_steps"

    id: int                      # 主键
    step_number: int             # 步骤编号 (2-16)
    step_name: str               # 步骤名称
    assignee_profile: str        # 负责 Agent 的 Profile 名称
    qa_required: bool            # 是否需要 QA 门控
    is_active: bool              # 是否启用

    # 支持按项目覆盖默认 Agent 分配
    project_id: Optional[int]    # NULL 表示全局默认配置

# 初始化数据示例（系统启动时写入）
# step_number | assignee_profile | step_name
#     2       | haimei           | 确认核心目标+搭建组织架构
#     3       | houxing          | 需求分析
#     4       | houwang          | 架构设计
#     5       | houfu            | 建立开发环境
#     6       | haimei           | 制订TDD测试用例计划
#     7       | houfa            | 编写TDD测试用例
#     8       | haimei           | 制订代码编写计划
#     9       | houfa            | 编写功能代码
#     10      | houfu            | 部署到测试环境
#     11      | houda            | 全面测试
#     12      | houhua           | 安全审计
#     13      | houfu            | 部署到生产环境
#     14      | hougui           | 完善文档
#     15      | haimei           | 报告交付成果
#     16      | haimei           | 用户满意度确认/迭代
```

`WorkflowService._get_step_assignee()` 实现：

```python
async def _get_step_assignee(self, step_number: int, project_id: Optional[int] = None) -> str:
    """从数据库查询指定步骤的 Agent 分配（优先项目级覆盖，其次全局默认）"""
    # 优先查询项目级覆盖配置
    if project_id:
        config = await self.workflow_step_repo.get_by_step_and_project(
            step_number, project_id
        )
        if config and config.is_active:
            return config.assignee_profile

    # 回退到全局默认配置
    config = await self.workflow_step_repo.get_default(step_number)
    if config and config.is_active:
        return config.assignee_profile

    raise WorkflowError(f"未配置步骤 {step_number} 的 Agent 分配")
```

### 5.3 16 步流程状态转移图 (V20 新增)

以下状态转移图描述了 16 步流程中每个步骤的完整生命周期状态转换：

```
                    ┌───────────┐
                    │  pending  │ ← 初始状态，等待执行
                    └─────┬─────┘
                          │ execute_step()
                          ▼
                    ┌───────────┐
                    │  running  │ ← Agent 正在执行中
                    └─────┬─────┘
                          │
           ┌──────────────┼──────────────┐
           │              │              │
    success│              │              │error/timeout
           │              │              │
           ▼              ▼              ▼
   ┌───────────┐   ┌───────────┐   ┌───────────┐
   │qa_pending │   │ completed │   │   error   │
   │(需QA门控) │   │(无需QA)   │   └─────┬─────┘
   └─────┬─────┘   └─────┬─────┘         │
         │                │         retry()
    ┌────┴────┐          │               │
    │         │          │               ▼
    ▼         ▼    ┌───────────┐    ┌───────────┐
┌───────┐ ┌───────┐│ cancelled │    │  running  │ ← 重试后重新执行
│qa_    │ │qa_    │└───────────┘    └───────────┘
│passed │ │failed │                          │
└───┬───┘ └───┬───┘                          │
    │         │                              │
    │         │ retry_with_feedback()        │
    │         │                              │
    ▼         └──────────────────────────────┘
┌───────────┐
│ completed │ ← QA 通过，可进入下一步
└───────────┘
```

**状态说明**：
- `pending`: 步骤等待执行，前置条件已满足
- `running`: Agent 正在执行该步骤
- `qa_pending`: Agent 执行完成，等待后荣 QA 检验（适用于需要 QA 门控的步骤）
- `qa_passed`: QA 检验通过
- `qa_failed`: QA 检验未通过，需要退回重做
- `completed`: 步骤完成（包括无需 QA 的步骤直接完成和 QA 通过后完成）
- `error`: 执行出错，可重试
- `cancelled`: 被取消（由海梅或人类用户主动取消）

**各步骤前置条件表**（V20 新增）：

| 步骤编号 | 前置条件 | 验证方式 |
|---|---|---|
| 第一步 | 无（人类用户创建项目） | 无需验证 |
| 第二步 | 第一步已完成 | `workflow_progress[1].status == 'completed'` |
| 第三步 | 第二步已完成 | `workflow_progress[2].status == 'completed'` |
| 第四步 | 第三步已完成 | `workflow_progress[3].status == 'completed'` |
| 第五步 | 第四步已完成 | `workflow_progress[4].status == 'completed'` |
| 第六步 | 第五步已完成 | `workflow_progress[5].status == 'completed'` |
| 第七步 | 第六步已完成 | `workflow_progress[6].status == 'completed'` |
| 第八步 | 第七步已完成 | `workflow_progress[7].status == 'completed'` |
| 第九步 | 第八步已完成 | `workflow_progress[8].status == 'completed'` |
| 第十步 | 第九步已完成 | `workflow_progress[9].status == 'completed'` |
| 第十一步 | 第十步已完成 | `workflow_progress[10].status == 'completed'` |
| 第十二步 | 第十一步已完成 | `workflow_progress[11].status == 'completed'` |
| 第十三步 | 第十二步已完成 | `workflow_progress[12].status == 'completed'` |
| 第十四步 | 第十三步已完成 | `workflow_progress[13].status == 'completed'` |
| 第十五步 | 第十四步已完成 | `workflow_progress[14].status == 'completed'` |
| 第十六步 | 第十五步已完成 | `workflow_progress[15].status == 'completed'` |

**失败回滚策略**（V20 新增）：

当某一步骤执行失败且重试耗尽后，系统采用以下回滚策略：

1. **步骤级回滚**（默认策略）:
   - 仅回退当前步骤到 `pending` 状态
   - 保留该步骤已创建的部分产出（如部分代码文件）
   - 通知对应 Agent 重新执行，附带失败原因和修改建议
   - 适用场景：单步执行失败，不影响前置步骤

2. **跨步骤回滚**（严重失败）:
   - 当某步骤的失败导致前置步骤的产出不可用时，回退到上一个 `completed` 步骤
   - 回滚路径: 从失败步骤开始，逐向前查找最近一个 `completed` 步骤
   - 回滚后中间步骤的状态重置为 `pending`
   - 适用场景：依赖链断裂、环境配置错误等影响后续多步骤的情况

3. **项目级暂停**（致命失败）:
   - 当 3 次重试均失败且无备用 Agent 可用时
   - 项目状态设为 `paused`
   - 所有未执行步骤设为 `cancelled`
   - 通知人类用户介入处理
   - 适用场景：Agent 持续不可用、基础设施故障

```python
class WorkflowStateMachine:
    VALID_TRANSITIONS = {
        "pending": {"running"},
        "running": {"qa_pending", "completed", "error", "cancelled"},
        "qa_pending": {"qa_passed", "qa_failed"},
        "qa_failed": {"running"},  # 退回重做
        "qa_passed": {"completed"},
        "error": {"running"},  # 重试
        "cancelled": set(),  # 终态，不可恢复
    }

    async def validate_transition(self, project_id: int, step_number: int):
        """验证状态转换是否合法"""
        current = await self._get_current_status(project_id, step_number)
        if current != "pending" and current != "qa_failed" and current != "error":
            raise WorkflowError(f"步骤 {step_number} 当前状态为 {current}，无法执行")
        # 验证上一步已完成
        if step_number > 1:
            prev_status = await self._get_current_status(project_id, step_number - 1)
            if prev_status != "completed":
                raise WorkflowError(f"必须先完成第 {step_number - 1} 步")

    async def transition_to(self, project_id: int, step_number: int, new_status: str):
        """执行状态转换（事务内完成）"""
        current = await self._get_current_status(project_id, step_number)
        allowed = self.VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise WorkflowError(f"不允许从 {current} 转换到 {new_status}")
        # 在事务中更新数据库
        await self._update_status_in_txn(project_id, step_number, new_status)

    async def rollback_step(self, project_id: int, failed_step: int) -> int:
        """回滚到上一个完成的步骤，返回回滚目标步骤号"""
        for step in range(failed_step - 1, 0, -1):
            status = await self._get_current_status(project_id, step)
            if status == "completed":
                # 将中间步骤重置为 pending
                for s in range(step + 1, failed_step + 1):
                    await self.transition_to(project_id, s, "pending")
                return step
        return 1  # 如果没有已完成的步骤，回退到第一步

    async def is_qa_required(self, step_number: int) -> bool:
        """查询步骤是否需要 QA 门控"""
        config = await self.workflow_step_repo.get_default(step_number)
        return config.qa_required if config else step_number != 1
```

### 5.4 流程推进机制 (V19 拆分)

V19 将流程推进拆分为三个服务的协作：

```python
# workflow_orchestrator.py - 流程编排服务
class WorkflowOrchestrator:
    """16 步流程编排服务"""

    def __init__(self, statemachine: WorkflowStateMachine,
                 executor: StepExecutor, qa_service: QAService,
                 notification_service: NotificationService):
        self.statemachine = statemachine
        self.executor = executor
        self.qa_service = qa_service
        self.notification_service = notification_service

    async def execute_step(self, project_id: int, step_number: int):
        """编排步骤执行流程"""
        # 1. 状态机验证前置条件
        await self.statemachine.validate_transition(project_id, step_number)

        # 2. 状态机更新状态为 running
        await self.statemachine.transition_to(project_id, step_number, "running")

        # 3. 委派给步骤执行服务
        task_result = await self.executor.execute(project_id, step_number)

        # 4. 检查是否需要 QA 门控
        qa_required = await self.statemachine.is_qa_required(step_number)
        if qa_required:
            # 提交 QA 检验
            qa_result = await self.qa_service.inspect(task_result)
            if qa_result.acceptance_result == "pass":
                await self._on_qa_passed(project_id, step_number, task_result)
            else:
                await self._on_qa_failed(project_id, step_number, qa_result)
        else:
            # 无需 QA，直接完成
            await self.statemachine.transition_to(project_id, step_number, "completed")
            await self._auto_advance(project_id, step_number)

    async def _on_qa_passed(self, project_id: int, step_number: int, result):
        """QA 通过: 提交代码库，自动推进"""
        await self._submit_to_repo(project_id, step_number, result)
        await self.statemachine.transition_to(project_id, step_number, "completed")
        await self._auto_advance(project_id, step_number)

    async def _on_qa_failed(self, project_id: int, step_number: int, qa_result):
        """QA 未通过: 退回重做"""
        await self.statemachine.transition_to(project_id, step_number, "qa_failed")
        await self.notification_service.send_notification(
            user_id=project_owner,
            content=f"第 {step_number} 步 QA 检验未通过，正在退回重做"
        )
        # 触发重做流程（24 小时时限）
        await self.executor.retry_with_feedback(project_id, step_number, qa_result.problem_details)

    async def _auto_advance(self, project_id: int, completed_step: int):
        """自动推进到下一步"""
        next_step = completed_step + 1
        if next_step <= 16:
            await self.execute_step(project_id, next_step)


# workflow_statemachine.py - 状态机服务
class WorkflowStateMachine:
    """流程状态机服务"""

    VALID_TRANSITIONS = {
        "pending": {"running"},
        "running": {"qa_pending", "completed", "error", "cancelled"},
        "qa_pending": {"qa_passed", "qa_failed"},
        "qa_failed": {"running"},  # 退回重做
        "qa_passed": {"completed"},
        "error": {"running"},  # 重试
        "cancelled": set(),  # 终态
    }

    async def validate_transition(self, project_id: int, step_number: int):
        """验证状态转换是否合法"""
        current = await self._get_current_status(project_id, step_number)
        if current != "pending" and current != "qa_failed" and current != "error":
            raise WorkflowError(f"步骤 {step_number} 当前状态为 {current}，无法执行")
        # 验证上一步已完成
        if step_number > 1:
            prev_status = await self._get_current_status(project_id, step_number - 1)
            if prev_status != "completed":
                raise WorkflowError(f"必须先完成第 {step_number - 1} 步")

    async def transition_to(self, project_id: int, step_number: int, new_status: str):
        """执行状态转换（事务内完成）"""
        current = await self._get_current_status(project_id, step_number)
        allowed = self.VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise WorkflowError(f"不允许从 {current} 转换到 {new_status}")
        # 在事务中更新数据库
        await self._update_status_in_txn(project_id, step_number, new_status)

    async def is_qa_required(self, step_number: int) -> bool:
        """查询步骤是否需要 QA 门控"""
        config = await self.workflow_step_repo.get_default(step_number)
        return config.qa_required if config else step_number != 1


# step_executor.py - 步骤执行服务
class StepExecutor:
    """单步执行服务"""

    def __init__(self, gateway_client: GatewayClient, agent_service: AgentService,
                 task_repo: TaskRepository):
        self.gateway_client = gateway_client
        self.agent_service = agent_service
        self.task_repo = task_repo

    async def execute(self, project_id: int, step_number: int) -> dict:
        """执行单个步骤"""
        # 1. 获取负责的 Agent
        assignee = await self._get_step_assignee(step_number, project_id)

        # 2. 构建任务上下文
        context = await self._build_context(project_id, step_number, assignee)

        # 3. 通过 Gateway Client 发送任务到 Agent
        result = await self.gateway_client.send_message(
            profile_name=assignee,
            messages=context
        )

        # 4. 解析并保存结果
        await self._save_result(project_id, step_number, result)
        return result

    async def retry_with_feedback(self, project_id: int, step_number: int,
                                   feedback: str):
        """带反馈的重做"""
        context = await self._build_retry_context(project_id, step_number, feedback)
        assignee = await self._get_step_assignee(step_number, project_id)
        result = await self.gateway_client.send_message(
            profile_name=assignee,
            messages=context
        )
        await self._save_result(project_id, step_number, result)
```

### 5.5 任务依赖图管理

- 使用有向无环图 (DAG) 管理任务依赖关系
- 依赖关系持久化存储在 `task_dependencies` 表中
- 分布式环境下使用 Redis 存储依赖图状态，确保多 Celery worker 状态一致
- 拓扑排序确定执行顺序
- 前置任务未通过 QA 检验的，后继任务不得开始
- 前后两个任务必须分配给不同的蜂群 Agent（第九步要求）

```python
class TaskDependencyGraph:
    """任务依赖图管理器（Redis 后端，支持分布式部署）"""

    REDIS_PREFIX = "task_dep_graph:"
    READY_TASKS_KEY = "task_dep_graph:ready_set"  # 独立维护可执行任务集合

    def __init__(self, redis_client: Redis, task_dependency_repo: TaskDependencyRepository):
        self._redis = redis_client
        self._repo = task_dependency_repo

    async def initialize(self):
        """服务启动时从数据库重建依赖图（写入 Redis）"""
        dependencies = await self._repo.get_all_active()
        pipeline = self._redis.pipeline()
        for dep in dependencies:
            # 使用 Redis Set 存储: source -> targets
            pipeline.sadd(f"{self.REDIS_PREFIX}{dep.source_task_id}", dep.target_task_id)
        await pipeline.execute()
        # 初始化可执行任务集合
        await self._refresh_ready_set()

    async def add_dependency(self, source_task_id: int, target_task_id: int):
        """添加依赖关系（同时更新 Redis 和数据库）"""
        if source_task_id == target_task_id:
            raise DependencyError("任务不能依赖自身")

        # 循环依赖检测
        if await self._has_cycle(source_task_id, target_task_id):
            raise DependencyError(f"添加依赖将形成循环: {source_task_id} -> {target_task_id}")

        # 更新 Redis 缓存
        await self._redis.sadd(f"{self.REDIS_PREFIX}{source_task_id}", target_task_id)

        # 持久化到数据库
        await self._repo.create(source_task_id=source_task_id,
                                target_task_id=target_task_id)

        # 可执行任务集合变更：移除目标（因新增依赖变为不可执行）
        await self._redis.srem(self.READY_TASKS_KEY, target_task_id)

    async def remove_dependency(self, dep_id: int):
        """移除依赖关系"""
        dep = await self._repo.get_by_id(dep_id)
        if dep:
            # 移除 Redis 缓存
            await self._redis.srem(f"{self.REDIS_PREFIX}{dep.source_task_id}",
                                    dep.target_task_id)
            # 标记数据库记录为非活跃
            await self._repo.deactivate(dep_id)

    async def _has_cycle(self, source: int, target: int) -> bool:
        """检测是否形成循环依赖（BFS 遍历 Redis 中的图）"""
        visited = set()
        queue = [target]
        while queue:
            current = queue.pop(0)
            if current == source:
                return True
            if current in visited:
                continue
            visited.add(current)
            targets = await self._redis.smembers(f"{self.REDIS_PREFIX}{current}")
            queue.extend(int(t) for t in targets)
        return False

    async def _refresh_ready_set(self):
        """使用 SCAN 遍历所有依赖键，计算可执行任务并写入独立集合"""
        # 清除旧的可执行任务集合
        await self._redis.delete(self.READY_TASKS_KEY)

        # 使用 SCAN 替代 KEYS，避免全键遍历阻塞
        all_nodes = set()
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{self.REDIS_PREFIX}*", count=100)
            for key in keys:
                source = int(key.decode().replace(self.REDIS_PREFIX, ""))
                all_nodes.add(source)
                targets = await self._redis.smembers(key)
                all_nodes.update(int(t) for t in targets)
            if cursor == 0:
                break

        # 将无入边的节点加入可执行集合（这些任务没有前置依赖）
        sources_with_deps = set()
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match=f"{self.REDIS_PREFIX}*", count=100)
            for key in keys:
                targets = await self._redis.smembers(key)
                sources_with_deps.update(int(t) for t in targets)
            if cursor == 0:
                break

        ready_nodes = all_nodes - sources_with_deps
        for task_id in ready_nodes:
            await self._redis.sadd(self.READY_TASKS_KEY, task_id)

    async def get_ready_tasks(self, completed: set) -> List[int]:
        """获取当前可执行的任务（前置依赖已完成）"""
        # 直接从独立的可执行任务集合读取，O(1) 复杂度
        ready_task_ids = await self._redis.smembers(self.READY_TASKS_KEY)
        ready = [int(tid) for tid in ready_task_ids if int(tid) not in completed]
        return ready

    async def mark_task_completed(self, task_id: int):
        """标记任务完成，更新可执行任务集合"""
        # 从可执行集合中移除已完成的
        await self._redis.srem(self.READY_TASKS_KEY, task_id)

        # 检查该任务的后续任务是否变为可执行
        targets = await self._redis.smembers(f"{self.REDIS_PREFIX}{task_id}")
        for target_id in targets:
            target_id = int(target_id)
            # 获取该目标任务的所有前置依赖
            all_sources = set()
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=f"{self.REDIS_PREFIX}*", count=100)
                for key in keys:
                    members = await self._redis.smembers(key)
                    if str(target_id).encode() in members:
                        source = int(key.decode().replace(self.REDIS_PREFIX, ""))
                        all_sources.add(source)
                if cursor == 0:
                    break

            # 所有前置依赖均已完成，则该任务变为可执行
            if all(s in completed or s == task_id for s in all_sources):
                await self._redis.sadd(self.READY_TASKS_KEY, target_id)
```

TaskDependencyGraph 修复说明：V13 中 `get_ready_tasks()` 使用 `Redis KEYS` 命令遍历所有依赖键，O(N) 复杂度在任务量增长时性能显著下降。V14 改为：
1. 使用 `SCAN` 替代 `KEYS` 遍历依赖键，避免全键阻塞
2. 维护独立的 Redis Set (`task_dep_graph:ready_set`) 存储当前可执行的任务集合，`get_ready_tasks()` 直接从该集合读取，复杂度降至 O(1)
3. 新增 `mark_task_completed()` 方法，在任务完成时增量更新可执行集合

TaskDependencyRepository（task_dependency_repo.py）：

```python
class TaskDependencyRepository(BaseRepository):
    """任务依赖关系数据访问层"""

    async def create(self, source_task_id: int, target_task_id: int) -> TaskDependency:
        """创建依赖关系记录"""
        dep = TaskDependency(source_task_id=source_task_id,
                             target_task_id=target_task_id)
        self.session.add(dep)
        return dep

    async def get_by_id(self, dep_id: int) -> Optional[TaskDependency]:
        """根据 ID 获取依赖关系记录"""
        return await self.session.get(TaskDependency, dep_id)

    async def deactivate(self, dep_id: int):
        """标记依赖关系为非活跃（软删除）"""
        dep = await self.get_by_id(dep_id)
        if dep:
            dep.is_active = False

    async def get_all_active(self) -> List[TaskDependency]:
        """获取所有未删除的依赖关系记录（用于服务启动时重建图）"""
        return await self.session.execute(
            select(TaskDependency).where(TaskDependency.is_active == True)
        )

    async def get_dependencies_for_task(self, task_id: int) -> List[TaskDependency]:
        """获取某任务作为目标的所有依赖"""
        return await self.session.execute(
            select(TaskDependency).where(
                TaskDependency.target_task_id == task_id,
                TaskDependency.is_active == True
            )
        )
```

### 5.6 Celery 异步任务 (V20 修订)

后端使用 Celery 处理以下异步任务：

| 任务 | 说明 | 触发方式 | 优先级队列 |
|---|---|---|---|
| agent_execution | Agent 任务执行 | 流程推进时触发 | high |
| swarm_dispatch | 蜂群任务分发 | 第七步/第九步/第十一步 | high |
| qa_inspection | QA 检验请求 | Agent 提交产出后 | high |
| profile_scan | Profile 自动扫描 | 定时 (每 30 分钟) | low |
| gitea_sync | Gitea 仓库同步 | 检验合格后触发 | medium |
| backup_db | 数据库备份 | 定时 (每日凌晨 2:00) | low |
| backup_files | 文件备份 | 定时 (每日凌晨 3:00) | low |
| backup_gitea | 代码仓库归档 | 定时 (每日凌晨 4:00) | low |

### 5.7 Celery 任务签名定义 (V20 新增)

以下为各 Celery 任务的具体签名定义：

**agent_execution 任务** (`tasks/agent_tasks.py`):

```python
@celery_app.task(
    name='agent_execution',
    queue='high',
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    time_limit=1800,
    soft_time_limit=1740,
    acks_late=True,
    reject_on_worker_lost=True,
    rate_limit='10/m'  # 每分钟最多 10 个 Agent 执行任务
)
def agent_execution(project_id: int, step_number: int,
                    profile_name: str, task_context: dict) -> dict:
    """
    执行单个 Agent 任务
    
    入参:
        project_id (int): 项目 ID
        step_number (int): 步骤编号 (2-16)
        profile_name (str): Agent Profile 名称
        task_context (dict): 任务上下文（消息历史、项目描述、前置产出等）
    
    返回值:
        dict: {
            "task_id": int,
            "step_number": int,
            "status": "success" | "failed",
            "result": str,           # Agent 执行结果
            "duration_seconds": int,  # 执行耗时
            "error": str | None       # 错误信息
        }
    
    重试策略:
        - 第 1 次重试: 30 秒后
        - 第 2 次重试: 60 秒后
        - 第 3 次重试: 120 秒后
        - 超过 3 次重试失败: 切换备用 Agent 或通知人类用户
    """
    ...
```

**swarm_dispatch 任务** (`tasks/swarm_tasks.py`):

```python
@celery_app.task(
    name='swarm_dispatch',
    queue='high',
    max_retries=2,
    default_retry_delay=30,
    retry_backoff=True,
    time_limit=600,
    acks_late=True
)
def swarm_dispatch(swarm_id: int, tasks_payload: list) -> dict:
    """
    分发任务到蜂群成员
    
    入参:
        swarm_id (int): 蜂群 ID
        tasks_payload (list): 任务载荷列表，每项为 {
            "task_id": int,
            "agent_id": int,
            "description": str,
            "acceptance_criteria": str
        }
    
    返回值:
        dict: {
            "swarm_id": int,
            "dispatched_count": int,
            "failed_count": int,
            "failed_tasks": list  # 分发失败的任务 ID 列表
        }
    """
    ...
```

**qa_inspection 任务** (`tasks/qa_tasks.py`):

```python
@celery_app.task(
    name='qa_inspection',
    queue='high',
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=120,
    time_limit=1800,
    soft_time_limit=1740,
    acks_late=True
)
def qa_inspection(task_id: int, project_id: int,
                  step_number: int, artifacts: dict) -> dict:
    """
    提交产出供后荣检验
    
    入参:
        task_id (int): 任务 ID
        project_id (int): 项目 ID
        step_number (int): 步骤编号
        artifacts (dict): 产出物（文件路径、文档内容等）
    
    返回值:
        dict: {
            "qa_record_id": int,
            "score": int,             # 0-100 综合评分
            "acceptance_result": str,  # "pass" | "fail"
            "review_round": int,       # 检验轮次
            "problem_details": str,    # 不合格时的修改建议
            "dimensions": list          # 各维度得分
        }
    """
    ...
```

**profile_scan 任务** (`tasks/sync_tasks.py`):

```python
@celery_app.task(
    name='profile_scan',
    queue='low',
    max_retries=1,
    default_retry_delay=60,
    time_limit=300
)
def profile_scan() -> dict:
    """
    扫描 Hermes Agent Profile 目录
    
    返回值:
        dict: {
            "scanned_count": int,
            "online_count": int,
            "offline_count": int,
            "agents": list  # Agent 配置摘要列表
        }
    """
    ...
```

**gitea_sync 任务** (`tasks/sync_tasks.py`):

```python
@celery_app.task(
    name='gitea_sync',
    queue='medium',
    max_retries=2,
    default_retry_delay=30,
    retry_backoff=True,
    time_limit=300
)
def gitea_sync(project_id: int, step_number: int,
               files: list, commit_message: str) -> dict:
    """
    将产出提交到 Gitea 代码仓库
    
    入参:
        project_id (int): 项目 ID
        step_number (int): 步骤编号
        files (list): 文件变更列表 [{path, content, operation}]
        commit_message (str): 提交消息
    
    返回值:
        dict: {
            "commit_sha": str,
            "branch": str,
            "file_count": int
        }
    """
    ...
```

**backup_db 任务** (`tasks/backup_tasks.py`):

```python
@celery_app.task(
    name='backup_db',
    queue='low',
    max_retries=1,
    default_retry_delay=300,
    time_limit=3600  # 1 小时超时
)
def backup_db(backup_type: str = "daily") -> dict:
    """
    数据库备份任务
    
    入参:
        backup_type (str): "daily" | "weekly" | "monthly"
    
    返回值:
        dict: {
            "backup_path": str,
            "size_bytes": int,
            "duration_seconds": int,
            "backup_type": str
        }
    """
    ...
```

### 5.8 Celery 长时间任务支持 (V19 新增)

Agent 任务是长时间运行的 LLM 调用，可能持续数分钟至 30 分钟。Celery 配置如下：

- **task_time_limit**: 1800 秒 (30 分钟)，硬超时，超过后强制终止
- **task_soft_time_limit**: 1740 秒 (29 分钟)，软超时，抛出 SoftTimeLimitExceeded 允许清理
- **task_acks_late**: True，任务完成后才确认，确保失败时自动重试
- **task_reject_on_worker_lost**: True，Worker 丢失时拒绝任务并重新入队
- **worker_heartbeat**: 30 秒，Worker 每 30 秒向 Broker 发送心跳
- **broker_transport_options**: `{'visibility_timeout': 1800}`，Redis 消息可见超时 30 分钟
- **并发控制**: `worker_concurrency=4`，每个 Worker 进程 4 个并发，防止资源耗尽

Celery Worker 配置示例:
```python
# celery_app.py
app.conf.update(
    task_time_limit=1800,
    task_soft_time_limit=1740,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_heartbeat=30,
    broker_transport_options={
        'visibility_timeout': 1800,
        'confirm_publish': True
    },
    worker_prefetch_multiplier=1,  # 一次只取一个任务，避免堆积
    task_tracker_dns_enabled=True,  # 启用任务跟踪
)

# 优先级队列配置
app.conf.update(
    task_queues={
        'high': {'queue_ordering': 'priority'},
        'medium': {'queue_ordering': 'priority'},
        'low': {'queue_ordering': 'priority'}
    },
    task_default_queue='medium',
    task_default_priority=5
)
```

Agent 执行失败后的重试策略：
1. 首次失败: 30 秒后重试
2. 第二次失败: 60 秒后重试
3. 第三次失败: 120 秒后重试
4. 三次均失败: 切换备用 Agent 执行
5. 备用 Agent 不可用: 通知人类用户并暂停任务
6. 所有重试记录到 `agent_execution_logs` 表

---

## 6. Agent 调度服务

### 6.1 职责概述

Agent 调度服务是后端的核心调度中心，负责：

1. 管理 9 个命名 Agent 的生命周期和状态
2. 通过 Hermes Gateway API 与 Agent 通信
3. 执行并发控制（信号量限制，默认最大 5 个并发请求）
4. 实现容错机制（3 次重试、30 分钟超时）
5. 自动发现和同步 Hermes Agent Profile

### 6.2 9 个命名 Agent 配置

| 名称 | Profile | 角色 | 默认端口 |
|---|---|---|---|
| HaiMei | haimei | 项目经理 | 8765 |
| HouXing | houxing | 需求分析师 | 8766 |
| HouWang | houwang | 架构设计师 | 8767 |
| HouFa | houfa | 程序员 | 8768 |
| HouDa | houda | 测试员 | 8769 |
| HouFu | houfu | CI/CD 工程师 | 8770 |
| HouGui | hougui | 文档管理员 | 8771 |
| HouRong | hourong | QA | 8772 |
| HouHua | houhua | 安全员 | 8773 |

### 6.3 Agent 生命周期管理 (V19 新增)

Agent 状态机:

```
                    ┌─────────┐
                    │  idle   │ ← 初始状态，等待任务
                    └────┬────┘
                         │ receive_task
                         ▼
                    ┌─────────┐
                    │  busy   │ ← 执行任务中
                    └────┬────┘
                   ┌──────┼──────┐
                   │      │      │
            success│      │      │error/timeout
                   │      │      │
                   ▼      ▼      ▼
              ┌──────┐ ┌──────┐ ┌─────────┐
              │ idle │ │idle  │ │  error  │
              └──────┘ └──────┘ └────┬────┘
                                      │ recover
                                      ▼
                                 ┌─────────┐
                                 │  idle   │
                                 └─────────┘

            健康检查失败 → offline
                   offline → 健康检查恢复 → idle
```

- **idle**: Agent 空闲，可接收新任务
- **busy**: Agent 正在执行任务，不可分配新任务（同一 profile 的互斥锁已获取）
- **error**: Agent 执行失败，记录错误详情，等待恢复或人工干预
- **offline**: Gateway 健康检查失败，标记为离线

状态更新机制:
1. **主动上报**: Agent 通过 `POST /api/v1/agents/:id/status-report` 上报状态变更
2. **被动检测**: 定时健康检查（每 5 分钟），失败超过 2 次标记为 offline
3. **任务完成后自动恢复**: 任务完成/失败后自动将状态恢复为 idle
4. **错误恢复**: error 状态在下次任务分配前自动重置为 idle（非致命错误）

### 6.4 Hermes Gateway API 契约 (V20 新增)

本节定义 DevFlow 后端与 Hermes Gateway API 之间的通信契约。

**Gateway 端点**:

| 端点 | 方法 | 用途 |
|---|---|---|
| /v1/chat/completions | POST | 与指定 Agent 对话（非流式/流式） |
| /v1/chat/completions (stream=true) | POST | 流式 SSE 对话 |
| /v1/health | GET | 健康检查 |

**请求格式** (`POST /v1/chat/completions`):

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是后旺，架构设计师角色..."
    },
    {
      "role": "user",
      "content": "请完成第四步：架构设计..."
    }
  ],
  "stream": false,
  "profile_name": "houwang"
}
```

**响应格式** (非流式):

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1718999999,
  "model": "qwen3.6-27b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "...Agent 的完整回复..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1000,
    "completion_tokens": 500,
    "total_tokens": 1500
  }
}
```

**响应格式** (流式 SSE):

```
data: {"id": "chatcmpl-xxx", "choices": [{"delta": {"content": "首"}}]}

data: {"id": "chatcmpl-xxx", "choices": [{"delta": {"content": "个"}}]}

...

data: {"id": "chatcmpl-xxx", "choices": [{"finish_reason": "stop"}]}

data: [DONE]
```

**超时策略**:
- 非流式请求: 30 分钟 (1800 秒) 超时
- 流式请求: 首字节超时 30 秒，整体超时 30 分钟
- 健康检查: 5 秒超时

**重试机制**:
- 连接超时/网络错误: 自动重试 3 次，指数退避 (30s/60s/120s)
- Gateway 返回 5xx: 重试 1 次，等待 10 秒
- Gateway 返回 429 (限流): 等待 `Retry-After` 头指定的时间后重试
- 3 次重试均失败: 标记 Agent 为 error 状态，触发备用 Agent 切换

**Agent 失败恢复**:
1. 单次 Gateway 调用失败 → 重试（最多 3 次）
2. 连续 3 次失败 → 标记该 Agent 为 `error` 状态
3. 检查同类型备用 Agent → 切换执行
4. 无可用的备用 Agent → 通知海梅和人类用户，暂停任务
5. 所有恢复操作记录到 `agent_execution_logs` 表

### 6.5 Gateway 通信客户端

```python
class GatewayClient:
    """Hermes Gateway API 客户端"""

    def __init__(self):
        self._semaphore = asyncio.Semaphore(5)  # 总并发信号量
        self._semaphore_timeout = 60  # 信号量等待超时 (秒)
        self._profile_locks: Dict[str, asyncio.Semaphore] = {}  # 按 profile 维度的互斥锁
        self._agents: Dict[str, AgentConfig] = {}
        self._timeout = 1800  # 30 分钟超时
        # 复用 httpx.AsyncClient 连接池，避免每次请求创建新客户端
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取或创建复用的 HTTP 客户端（连接池）"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
        return self._http_client

    async def _get_profile_lock(self, profile_name: str) -> asyncio.Semaphore:
        """获取指定 profile 的互斥锁，确保同一 profile 同一时间只执行一个任务"""
        if profile_name not in self._profile_locks:
            self._profile_locks[profile_name] = asyncio.Semaphore(1)
        return self._profile_locks[profile_name]

    async def send_message(self, profile_name: str, messages: list,
                           stream: bool = False) -> AsyncGenerator | dict:
        """发送消息到指定 Agent"""
        # 总并发控制（带超时处理）
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._semaphore_timeout)
        except asyncio.TimeoutError:
            raise AgentTimeoutError("获取并发信号量超时，请稍后重试",
                                    detail=f"等待超过 {self._semaphore_timeout} 秒仍未获取信号量")

        try:
            # 按 profile 维度的互斥锁：同一 Agent Profile 同一时间只能执行一个项目的任务
            profile_lock = await self._get_profile_lock(profile_name)
            async with profile_lock:
                agent = self._agents[profile_name]
                url = f"http://{agent.host}:{agent.port}/v1/chat/completions"

                if stream:
                    return await self._stream_request(url, messages)
                else:
                    return await self._request(url, messages)
        finally:
            self._semaphore.release()

    async def _request(self, url: str, messages: list) -> dict:
        """非流式请求"""
        client = await self._get_http_client()
        response = await client.post(url, json={"messages": messages})
        response.raise_for_status()
        return response.json()

    async def _stream_request(self, url: str, messages: list):
        """流式 SSE 请求"""
        client = await self._get_http_client()
        async with client.stream("POST", url,
                                  json={"messages": messages, "stream": True}) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield json.loads(line[6:])

    async def health_check(self, profile_name: str) -> bool:
        """检查 Agent 健康状态"""
        agent = self._agents[profile_name]
        url = f"http://{agent.host}:{agent.port}/v1/health"
        try:
            client = await self._get_http_client()
            resp = await client.get(url, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        """关闭 HTTP 客户端连接池"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
```

### 6.6 Gateway 职责边界与降级策略 (V19 新增)

**gateway_client.py vs gateway_service.py 职责划分**:
- `gateway_client.py` (core 层): 纯 HTTP 客户端，负责与 Hermes Gateway API 的底层通信，包括连接池管理、请求发送、响应解析。不包含业务逻辑
- `gateway_service.py` (services 层): 业务服务，负责构建 Agent 通信的上下文（消息历史、项目上下文、任务描述等），调用 gateway_client 发送请求，解析响应并转换为业务对象

**Gateway API 调用方式**: 全部为异步调用 (`async/await`)，使用 `httpx.AsyncClient`，不阻塞事件循环

**Gateway 不可用时的降级策略**:
1. 单次调用失败: 自动重试 3 次（指数退避: 30s/60s/120s）
2. 连续 3 次失败: 标记该 Agent 为 `error` 状态
3. 触发备用 Agent 切换机制（见 6.8 节）
4. 所有 Gateway 不可用: 返回 503 Service Unavailable，通知系统管理员
5. 降级期间新任务排队等待，已执行任务尝试恢复

### 6.7 并发控制 (V20 修订)

使用 asyncio.Semaphore 限制并发请求数，具体量化定义如下：

| 并发控制维度 | 上限值 | 配置项 | 说明 |
|---|---|---|---|
| 全局 Gateway 并发请求数 | 5 | GATEWAY_MAX_CONCURRENT | 所有通过 GatewayClient 的请求共享此信号量 |
| 单 Profile 并发任务数 | 1 | 硬编码 Semaphore(1) | 同一 Agent Profile 同一时间只能执行一个任务 |
| 单项目并发流程数 | 1 | 分布式锁 workflow:lock:{project_id} | 一个项目同时只能有一个流程在运行 |
| 单项目并发蜂群数 | 3 | SWARM_MAX_PER_PROJECT | 单项目最多 3 个并发蜂群 |
| 全局蜂群 Agent 总数 | 20 | SWARM_MAX_TOTAL_AGENTS | 所有蜂群 Agent 的总数上限 |
| Celery Worker 并发数 | 4 | worker_concurrency | 每个 Worker 进程 4 个并发任务 |

**并发控制场景量化说明**:
- 场景 1: 多项目同时执行 16 步流程 → 受全局信号量 (5) 限制，最多 5 个 Agent 请求并发
- 场景 2: 同一项目多个用户操作 → 受项目级分布式锁限制，流程推进串行化
- 场景 3: 蜂群任务分发 → 受单项目蜂群上限 (3) 和全局 Agent 总数 (20) 限制
- 场景 4: 同一 Profile 被多个项目请求 → 受 Profile 级互斥锁限制，排队等待

**等待策略**: 超出限制的请求进入等待队列，按 FIFO 顺序执行。等待超过 60 秒未获取信号量则返回超时错误。

### 6.8 容错机制

#### 重试策略

| 重试次数 | 等待间隔 | 说明 |
|---|---|---|
| 第 1 次 | 30 秒 | 首次重试 |
| 第 2 次 | 60 秒 | 第二次重试 |
| 第 3 次 | 120 秒 | 最后一次重试 |

#### 超时与退出

- **Agent 执行超时阈值**: 30 分钟
- 超时后自动终止当前 Agent 执行
- 3 次重试均失败后，触发备用 Agent 切换机制

#### 备用 Agent 选择策略

1. 优先选择同类型且当前负载最低的 Agent
2. 若无同类型 Agent，选择技能匹配度 ≥80% 的其他 Agent
3. 若无可用的备用 Agent，海梅通知人类用户并暂停该任务

### 6.9 Profile 自动扫描服务

```python
class ProfileScanner:
    """Hermes Agent Profile 自动扫描器"""

    PROFILES_DIR = Path.home() / ".hermes" / "profiles"

    def __init__(self, gateway_client: GatewayClient):
        self._gateway_client = gateway_client

    async def scan(self) -> List[AgentConfig]:
        """扫描 profiles 目录，发现所有可用 Hermes Agent"""
        agents = []
        if not self.PROFILES_DIR.exists():
            return agents

        for profile_dir in self.PROFILES_DIR.iterdir():
            if not profile_dir.is_dir():
                continue
            config_path = profile_dir / "config.yaml"
            if config_path.exists():
                config = await self._parse_config(config_path)
                is_running = await self._check_gateway(config.get("gateway_port"))
                config["is_running"] = is_running
                config["profile_name"] = profile_dir.name
                config["config_path"] = str(config_path)
                agents.append(AgentConfig(**config))

        return agents

    async def _check_gateway(self, port: int) -> bool:
        """检查 Gateway 健康状态（复用 GatewayClient 连接池，避免每次创建新客户端）"""
        if port is None:
            return False
        try:
            client = await self._gateway_client._get_http_client()
            resp = await client.get(f"http://127.0.0.1:{port}/v1/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
```

ProfileScanner._check_gateway() 修复说明：V13 中该方法每次调用都创建新的 `httpx.AsyncClient`，违背了"复用 httpx.AsyncClient 连接池"的原则。V14 改为调用 `GatewayClient._get_http_client()` 复用连接池。

Profile 状态管理机制（事件驱动 + 定期扫描兜底）：

- **事件驱动**（主机制）: Agent 启动或停止时主动调用 `POST /api/v1/agents/:id/status-report` 上报状态变更，后端立即更新数据库和缓存
- **定期扫描**（兜底机制）: 每 30 分钟全量扫描一次 profiles 目录，检测端口状态并同步到数据库，用于修正因 Agent 异常退出未及时上报导致的状态不一致
- **手动触发**: 通过 `POST /api/v1/profiles/scan` 手动触发全量扫描
- **状态同步**: 扫描结果与 Agent 上报结果自动合并，以最新时间戳为准

---

## 7. Agent 蜂群服务

### 7.1 职责概述

Agent 蜂群服务负责管理编程 Agent 集群的建立、调度和成果收集。蜂群由后发（HouFa，代码编写）或后达（HouDa，代码测试）建立和管理：

- **后发建立**: 第七步（TDD 测试用例编写）和第九步（功能代码编写）
- **后达建立**: 第十一步（全面测试）

### 7.2 蜂群生命周期

```
创建 → 启动成员 → 注册 → 初始化 → 执行任务 → 成果收集 → 解散/退出
```

1. **创建阶段**: 后发/后达通过 `POST /api/v1/swarms` 创建蜂群，DevFlow 根据任务类型和数量自动选择并启动合适的编程 Agent
2. **启动阶段**:
   - 对于 Hermes 子 agent：通过 Gateway API 创建子会话
   - 对于外部编程 Agent（Claude Code 等）：通过其 CLI 或 API 启动独立进程
3. **初始化阶段**: Agent 加载项目上下文，通过 `POST /api/v1/agents/register` 注册自身信息和可用技能，建立通信连接
4. **执行阶段**: Agent 接收任务，执行代码编写或测试任务，定期上报进度，完成后交付成果
5. **退出阶段**: 满足以下任一条件时退出：
   - 任务完成且成果通过 QA 检验（正常退出）
   - 蜂群调度者手动解散
   - Agent 执行超时超过 30 分钟，自动终止（最多重试 3 次）
   - Agent 进程异常崩溃（异常退出，调度者自动记录并更换备用 Agent）
6. **资源清理**: 自动清理临时文件，断开通信连接，释放计算资源

### 7.3 蜂群详细实现方案 (V19 新增)

#### 蜂群创建流程

```python
class SwarmService:
    async def create_swarm(self, project_id: int, step_number: int,
                           manager_agent_id: int) -> Swarm:
        """创建蜂群（事务内完成）"""
        # 1. 检查资源: 当前活跃蜂群数是否超过上限
        active_count = await self.swarm_repo.count_active(project_id)
        if active_count >= 3:  # 单项目最多 3 个并发蜂群
            raise SwarmError("活跃蜂群数已达上限，请先等待现有蜂群完成")

        # 2. 创建蜂群记录
        swarm = await self.swarm_repo.create(
            project_id=project_id,
            step_number=step_number,
            manager_agent_id=manager_agent_id
        )

        # 3. 根据任务类型选择合适的 Agent 类型和数量
        agents_needed = await self._select_agents(step_number)

        # 4. 启动并注册 Agent
        for agent_config in agents_needed:
            agent = await self.agent_service.start_agent(agent_config)
            await self.swarm_repo.add_agent(swarm.id, agent.id)

        return swarm
```

#### 蜂群任务分解（由海梅执行）

海梅作为项目经理，使用 Hermes Agent 的 `POST /api/v1/hermes/tasks/decompose` 接口将复杂任务分解为原子化子任务：
1. 海梅接收蜂群创建请求和任务描述
2. 调用任务拆解接口，生成 DAG 任务依赖图
3. 为每个子任务分配验收标准
4. 按拓扑排序分发任务到蜂群成员

#### 蜂群并发资源保护

- 单项目最多 3 个并发蜂群，防止资源耗尽
- 全局蜂群 Agent 总数上限: 20（通过配置 `SWARM_MAX_TOTAL_AGENTS` 调整）
- 蜂群 Agent 共享 Gateway 总信号量，不额外占用命名 Agent 的 profile 锁
- 蜂群 Agent 使用独立的工作目录 (`/data/devflow/swarms/{project_id}/`)，实现文件系统隔离

### 7.4 技能匹配

| 任务类型 | 技能组合 | 优先 Agent 类型 |
|---|---|---|
| TDD 测试用例编写 | tdd_test + code_review | Claude Code, Codex |
| 功能代码编写 | code_generation + code_review | Opencode, Cursor, Claude Code, CodeArts, Trae, Lingma |
| 测试用例编写 | test_creation + code_review | Claude Code, Codex |
| 环境部署 | deployment + code_generation | Cursor, CodeArts |
| 集成测试 | test_creation + debugging | Claude Code, Trae |

### 7.5 蜂群通信接口

蜂群 Agent 与 DevFlow 通过 RESTful API 通信：

```python
# 任务接收
class SwarmTaskResponse(BaseModel):
    task_id: int
    task_name: str
    description: str
    acceptance_criteria: str
    test_case_id: Optional[int]
    dependency_tasks: List[int]
    deadline: datetime

# 进度上报
class TaskProgressRequest(BaseModel):
    task_id: int
    progress_percent: int
    status: str  # in_progress / completed / failed
    message: str
    timestamp: datetime

# 成果交付
class TaskDeliveryRequest(BaseModel):
    task_id: int
    status: str  # completed
    artifacts: Dict[str, Any]  # 文件列表、代码行数等
    self_test_result: Optional[Dict[str, int]]  # 自测结果
    timestamp: datetime

# 错误上报
class TaskErrorRequest(BaseModel):
    task_id: int
    error_type: str
    error_message: str
    timestamp: datetime
```

### 7.6 负载均衡

- 根据 Agent 当前负载和技能匹配度动态调整任务分配
- 负载计算公式: `负载 = 活跃任务数 × 任务复杂度系数 / 最大并发数`
- 任务分配优先级: 技能匹配度 > 当前负载 > 响应时间

### 7.7 蜂群 Agent 工作目录

- 使用持久化卷存储蜂群 Agent 的临时工作目录，路径为 `/data/devflow/swarms/{project_id}/`
- 容器重启后数据不会丢失，确保跨重启周期的任务状态可恢复
- 在 Docker Compose 中挂载为 named volume: `swarm_data:/data/devflow/swarms`

---

## 8. 项目讨论群服务

### 8.1 职责概述

项目讨论群服务提供 Agent 间实时沟通与协作的核心渠道。第二步执行时自动创建群组，所有 9 个命名 Agent 角色自动加入。支持两种工作模式：

- **讨论模式 (discussion)**: 自由发言，@mention 定向沟通
- **会议模式 (meeting)**: 结构化议程，主持人控场

### 8.2 群组自动创建

```python
class GroupService:
    """项目讨论群服务"""

    NAMED_AGENTS = ["haimei", "houxing", "houwang", "houfa", "houda",
                     "houfu", "hougui", "hourong", "houhua"]

    def __init__(self, group_repo, agent_repo, project_repo,
                 group_member_repo, message_repo, websocket_manager):
        self.group_repo = group_repo
        self.agent_repo = agent_repo
        self.project_repo = project_repo
        self.group_member_repo = group_member_repo
        self.message_repo = message_repo
        self.websocket_manager = websocket_manager

    async def _get_agent_id_async(self, agent_name: str) -> int:
        """根据 Agent 名称获取 Agent ID"""
        agent = await self.agent_repo.find_by_name(agent_name)
        return agent.id

    async def _send_system_message(self, group_id: int, content: str):
        """发送系统通知消息到群组"""
        message = await self.message_repo.create(
            group_id=group_id,
            sender_type="system",
            sender_id=None,
            content=content,
            message_type="system"
        )
        # 通过 WebSocket 推送系统消息
        await self.websocket_manager.broadcast_group(group_id, {
            "type": "message_new",
            "message": message.to_dict()
        })

    async def create_project_group(self, project_id: int):
        """第二步：自动创建项目讨论群"""
        # 1. 创建群组
        group = await self.group_repo.create(
            project_id=project_id,
            name=f"项目 {project_id} 讨论群",
            mode="discussion",
            host_agent_id=await self._get_agent_id_async("haimei")
        )

        # 2. 自动添加所有 9 个命名 Agent
        for agent_name in self.NAMED_AGENTS:
            agent = await self.agent_repo.find_by_name(agent_name)
            await self.group_member_repo.add_agent(group.id, agent.id)

        # 3. 添加人类用户
        user = await self.project_repo.get_creator(project_id)
        await self.group_member_repo.add_user(group.id, user.id)

        # 4. 发送系统通知消息
        await self._send_system_message(group.id,
            f"项目讨论群已创建，所有 {len(self.NAMED_AGENTS)} 个命名 Agent 角色已加入")

        return group
```

### 8.3 讨论模式

- 人类用户或 Agent 可随时在群组中发送消息
- 支持 `@Agent名称` 定向提及特定 Agent
- **自动回复机制**:
  1. 检测消息中的 @mention
  2. 确定目标回复 Agent
  3. 获取最近消息作为上下文
  4. 调用 Gateway API 获取各 Agent 的响应
  5. 流式输出响应内容到前端（通过 WebSocket）
- 消息持久化到 `group_messages` 表，支持历史查询

### 8.4 会议模式

- **会议类型**:
  - 需求评审会 (requirement_review)
  - 技术方案讨论会 (tech_solution)
  - 每日站会 (daily_standup)
  - 故障复盘会 (incident_postmortem)

- **会议流程**:
  1. 开场定调：主持人介绍会议目标、产出要求
  2. 制订议程：根据会议类型生成可执行议程
  3. 按议程讨论：按顺序邀请各成员发言
  4. 会议总结：输出结构化会议纪要

- **输出**: 会议纪要、决议、待办任务、风险点、遗留问题
- **用户干预**: 会议进行中人类用户可发送消息干预，主持人可调整议程

```python
class MeetingService:
    """会议模式服务"""

    def __init__(self, meeting_repo, group_repo, agent_repo, websocket_manager):
        self.meeting_repo = meeting_repo
        self.group_repo = group_repo
        self.agent_repo = agent_repo
        self.websocket_manager = websocket_manager

    MEETING_TEMPLATES = {
        "requirement_review": [
            "PRD 整体介绍", "业务流程梳理", "边界规则讨论",
            "特殊场景分析", "开发提问环节", "当场确认"
        ],
        "tech_solution": [
            "背景与目标", "现有问题分析", "备选方案对比",
            "架构与接口设计", "敲定方案", "拆分任务"
        ],
        "daily_standup": [
            "每人汇报：昨天完成/今天计划/阻塞问题"
        ],
        "incident_postmortem": [
            "事件时间线", "影响面评估", "根因分析",
            "修复措施", "预防改进"
        ]
    }

    async def _get_host_agent_id(self, group_id: int) -> int:
        """获取群组主持人 Agent ID"""
        group = await self.group_repo.get_by_id(group_id)
        return group.host_agent_id

    async def _push_event(self, group_id: int, event_type: str, data: dict):
        """通过 WebSocket 推送事件到群组"""
        await self.websocket_manager.broadcast_group(group_id, {
            "type": event_type,
            **data
        })

    async def start_meeting(self, group_id: int, meeting_type: str,
                            topic: str) -> MeetingOutcome:
        """启动会议"""
        # 1. 生成议程
        agenda = self.MEETING_TEMPLATES[meeting_type]

        # 2. 创建会议记录
        meeting = await self.meeting_repo.create(
            group_id=group_id,
            meeting_type=meeting_type,
            meeting_topic=topic,
            host_agent_id=await self._get_host_agent_id(group_id)
        )

        # 3. 切换群组模式
        await self.group_repo.update_mode(group_id, "meeting")

        # 4. WebSocket 推送会议开始事件
        await self._push_event(group_id, "meeting_started", {
            "meeting_id": meeting.id,
            "agenda": agenda
        })

        return meeting
```

---

## 9. QA 门控服务

### 9.1 职责概述

QA 门控服务由后荣（HouRong）负责，是流程中每步的质量控制节点。核心原则：

- 每步产出必须经后荣检验合格方可进入下一步（第一步除外）
- 检验合格：放行 → 产出提交到代码库 → 通知海梅进入下一步
- 检验不合格：退回重做 → 附带修改建议 → Agent 必须在 24 小时内修改重新提交

### 9.2 QA 检验详细流程 (V19 新增)

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Agent 完成   │───▶│ 提交产出到   │───▶│ QA 门控服务  │
│ 步骤执行     │     │ QA 门控服务  │     │ 接收产出     │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │ 调用后荣 Agent       │
                                    │ 执行多维度检验       │
                                    └──────────┬──────────┘
                                               │
                              ┌────────────────┼────────────────┐
                              │                │                 │
                     ┌────────▼───────┐  ┌────▼────────┐  ┌────▼────────┐
                     │ 全部达标       │  │ 部分未达标   │  │ 严重不达标  │
                     │ score >= 85    │  │ score < 85   │  │ score < 60  │
                     └────────┬───────┘  └────┬────────┘  └────┬────────┘
                              │                │                 │
                     ┌────────▼───────┐  ┌────▼────────┐  ┌────▼────────┐
                     │ 提交代码库     │  │ 退回重做     │  │ 退回重做    │
                     │ 更新流程状态   │  │ (24h 时限)   │  │ + 海梅介入  │
                     │ 推进下一步     │  │ 附带修改建议 │  │             │
                     └────────────────┘  └─────────────┘  └─────────────┘
```

QA 门控与流程的集成:
- 步骤执行完成后，状态变为 `qa_pending`
- QA 检验通过: 状态变为 `qa_passed` → `completed`，流程自动推进
- QA 检验未通过: 状态变为 `qa_failed`，触发重做流程
- 重做完成后重新提交 QA，review_round + 1
- 同一任务最多 3 轮 QA 检验，超过 3 轮仍未通过则海梅介入处理

### 9.3 检验维度与量化打分

QA 门控服务按产出类型调用后荣执行相应维度的检验，合格判定规则：所有检验维度的量化指标均达到合格阈值，综合评分 ≥85 分。

**综合评分计算公式**: `score = Σ(维度_i 得分 × 权重_i) / Σ(权重_i)`，默认各维度权重均等（权重_i = 1），即 score = 各维度得分的算术平均值。当某维度为布尔型指标时，达标记为 100 分，不达标记为 0 分。

检验维度按产出类型匹配（详见 SRS 4.3.1 节）：

| 产出类型 | 检验维度 | 合格阈值 | 步骤 |
|---|---|---|---|
| 核心目标与组织架构 | 目标明确性 ≥80 分 + 组织完整性 100% | 目标 ≥80, 组织 =100 | 第二步 |
| 软件需求说明书 | 完整性 ≥90, 一致性=0, 可验证性 ≥90, 无歧义性=0 | 综合 ≥85 | 第三步 |
| 设计文档 | 完整性 4/4, 需求覆盖 ≥95%, 技术可行性=是, 无循环依赖 | 全部达标 | 第四步 |
| 开发环境 | 可用性 100%, 配置正确性 100%, 依赖完整性 100% | 全部达标 | 第五步 |
| TDD 测试用例计划 | 覆盖率 ≥95%, 原子化 ≥90%, 可量化 ≥90% | 全部达标 | 第六步 |
| TDD 测试用例代码 | 编译通过率 100%, 覆盖率 ≥95%, 原子化 ≥90%, 匹配率 ≥95% | 全部达标 | 第七步 |
| 代码编写计划 | 原子化 ≥90%, 测试对应率=100%, 循环依赖=0 | 全部达标 | 第八步 |
| 功能代码 | 编译通过率=100%, 测试通过率 ≥95%, 需求覆盖 ≥90%, 规范违规 ≤5 | 全部达标 | 第九步 |
| 测试报告 | 覆盖率 ≥90%, 通过率 ≥95%, Critical=0, 实操=100% | 全部达标 | 第十一步 |
| 安全审计报告 | 高危修复=100%, 中危 ≥90%, 合规=100%, OWASP Critical/High=0 | 全部达标 | 第十二步 |
| 测试环境部署 | 可用性=100%, 可访问率=100%, 功能 ≥95% | 全部达标 | 第十步 |
| 生产环境部署 | 可用性=100%, 可访问率=100%, 功能=100%, 性能达标 | 全部达标 | 第十三步 |
| 项目文档 | 完整性 4/4, 矛盾项=0, 一致率 ≥95% | 全部达标 | 第十四步 |

### 9.4 QA 检验记录

每次检验记录保存到 `qa_records` 表，包含：

- `review_dimensions`: JSON 数组，存储各维度的名称、量化标准、实际得分、合格阈值、是否达标
- `score`: 综合评分（0-100）
- `acceptance_result`: pass / fail
- `problem_details`: 不合格时的详细修改建议

### 9.5 退回重做机制

- 检验不合格时，QA 服务将检验报告发送给对应 Agent
- 设定 24 小时规定时限
- 超时未完成修改，触发海梅介入处理
- 每次检验记录完整保存，支持追溯

---

## 10. 代码仓库集成服务

### 10.1 职责概述

代码仓库集成服务负责与 Gitea 的对接，实现检验合格产出的自动提交。Gitea 作为所有 Agent 共享的成果存储中心。

### 10.2 仓库自动创建

项目创建时（第一步），服务自动在 Gitea 中创建项目代码仓库：

1. 根据项目名称生成仓库名称
2. 在配置的默认组织下创建仓库
3. 设置仓库为私有
4. 初始化仓库（README.md、.gitignore、LICENSE 等）
5. 设置默认分支为 `main`
6. 配置分支保护规则

### 10.3 分支管理（Git Flow）

| 分支 | 说明 | 保护规则 |
|---|---|---|
| main | 生产分支 | 仅通过 PR 合并，严格保护 |
| develop | 开发分支 | 仅通过 PR 合并 |
| feature/* | 功能开发分支 | 无保护 |
| release/* | 发布准备分支 | 仅通过 PR 合并 |
| hotfix/* | 紧急修复分支 | 仅通过 PR 合并 |

### 10.4 提交规范

所有代码提交必须遵循 Conventional Commits 规范：`<type>(<scope>): <subject>`

| 类型 | 描述 |
|---|---|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式调整 |
| refactor | 代码重构 |
| test | 添加或修改测试 |
| build | 构建系统或依赖更新 |
| ci | CI 配置更新 |
| chore | 其他杂项任务 |

### 10.5 提交时机与规则

| 阶段 | 提交内容 | 目标分支 |
|---|---|---|
| 第二步 | 核心目标文档 | develop |
| 第三步 | 软件需求说明书 | develop |
| 第四步 | 设计文档（架构/后端/前端/数据库） | develop |
| 第五步 | 环境配置文件 | develop |
| 第六步 | TDD 测试用例编写计划 | develop |
| 第七步 | TDD 测试用例代码 | feature/* |
| 第八步 | 代码编写计划 + 任务依赖图 | develop |
| 第九步 | 功能代码（逐任务提交） | feature/* |
| 第十步 | 测试环境部署配置 | develop |
| 第十一步 | 测试报告 | develop (通过 PR) |
| 第十二步 | 安全审计报告 | develop |
| 第十三步 | 生产环境部署配置 | release/* |
| 第十四步 | 项目文档集 | develop |
| 第十五步 | 项目交付报告 | main (通过 PR) |

提交规则：
- 提交必须关联任务 ID 和 QA 检验记录 ID
- 未检验或检验不合格的产出禁止提交
- 提交消息自动附带 Conventional Commits 前缀

### 10.6 Pull Request 流程

所有代码合并必须通过 Pull Request 流程：

1. 创建分支 → 2. 开发编码 → 3. 推送远程 → 4. 创建 PR → 5. 代码审查 → 6. 自动化测试 → 7. 审批通过 → 8. 合并 → 9. 删除源分支

### 10.7 Gitea API 客户端

```python
class GiteaClient:
    """Gitea REST API 客户端"""

    def __init__(self, host: str, port: int, api_token: str, default_org: str):
        self.base_url = f"http://{host}:{port}/api/v1"
        self._headers = {
            "Authorization": f"token {api_token}",
            "Content-Type": "application/json"
        }
        self.default_org = default_org
        # 复用 httpx.AsyncClient 连接池
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取或创建复用的 HTTP 客户端（连接池）"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
        return self._http_client

    async def create_repo(self, name: str, description: str = "") -> dict:
        """创建代码仓库"""
        payload = {
            "name": name,
            "description": description,
            "private": True,
            "auto_init": True,
            "default_branch": "main"
        }
        url = f"{self.base_url}/orgs/{self.default_org}/repos"
        client = await self._get_http_client()
        resp = await client.post(url, json=payload, headers=self._headers)
        resp.raise_for_status()
        return resp.json()

    async def create_commit(self, repo_id: int, branch: str,
                            files: list, message: str) -> str:
        """创建提交

        将多个文件变更打包为单次提交：
        1. 获取目标分支当前 commit SHA 和 tree SHA
        2. 为每个文件创建 blob
        3. 构建包含所有文件变更的 tree
        4. 基于 tree 创建单次 commit
        5. 更新分支引用指向新 commit

        files 格式: [{"path": "relative/path", "content": "file_content",
                      "operation": "create|update|delete"}]

        返回: commit SHA
        """
        import base64

        client = await self._get_http_client()
        repo_info = await self._get_repo_info(repo_id)
        repo_name = repo_info["name"]

        # 1. 获取目标分支当前 commit SHA 和 tree
        ref_url = f"{self.base_url}/repos/{self.default_org}/{repo_name}/git/refs/heads/{branch}"
        ref_resp = await client.get(ref_url, headers=self._headers)
        ref_resp.raise_for_status()
        current_sha = ref_resp.json()["sha"]

        commit_url = f"{self.base_url}/repos/{self.default_org}/{repo_name}/git/commits/{current_sha}"
        commit_resp = await client.get(commit_url, headers=self._headers)
        commit_resp.raise_for_status()
        parent_tree_sha = commit_resp.json()["tree"]["sha"]

        # 2. 为每个文件创建 blob 并收集 tree entries
        tree_entries = []

        # 先加载当前 tree 的所有条目（用于保留未变更的文件）
        tree_url = f"{self.base_url}/repos/{self.default_org}/{repo_name}/git/trees/{parent_tree_sha}"
        tree_resp = await client.get(tree_url, headers=self._headers)
        tree_resp.raise_for_status()
        existing_files = {entry["path"]: entry for entry in tree_resp.json().get("tree", [])}

        # 记录被操作的文件路径
        operated_paths = set()
        for file in files:
            operated_paths.add(file["path"])
            if file["operation"] == "delete":
                # 删除操作：不添加到 tree entries 中（即从 tree 中移除）
                continue
            elif file["operation"] in ("create", "update"):
                # 创建 blob
                blob_payload = {
                    "content": base64.b64encode(file["content"].encode()).decode()
                }
                blob_url = f"{self.base_url}/repos/{self.default_org}/{repo_name}/git/blobs"
                blob_resp = await client.post(blob_url, json=blob_payload, headers=self._headers)
                blob_resp.raise_for_status()
                blob_sha = blob_resp.json()["sha"]

                tree_entries.append({
                    "path": file["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha
                })

        # 3. 合并未变更的文件到 tree entries
        for path, entry in existing_files.items():
            if path not in operated_paths:
                tree_entries.append({
                    "path": entry["path"],
                    "mode": entry["mode"],
                    "type": entry["type"],
                    "sha": entry["sha"]
                })

        # 4. 创建新 tree
        create_tree_url = f"{self.base_url}/repos/{self.default_org}/{repo_name}/git/trees"
        tree_payload = {
            "base_tree": parent_tree_sha,
            "tree": tree_entries
        }
        new_tree_resp = await client.post(create_tree_url, json=tree_payload, headers=self._headers)
        new_tree_resp.raise_for_status()
        new_tree_sha = new_tree_resp.json()["sha"]

        # 5. 创建 commit
        create_commit_url = f"{self.base_url}/repos/{self.default_org}/{repo_name}/git/commits"
        commit_payload = {
            "message": message,
            "tree": new_tree_sha,
            "parents": [current_sha]
        }
        new_commit_resp = await client.post(create_commit_url, json=commit_payload, headers=self._headers)
        new_commit_resp.raise_for_status()
        new_commit_sha = new_commit_resp.json()["sha"]

        # 6. 更新分支引用
        update_ref_url = f"{self.base_url}/repos/{self.default_org}/{repo_name}/git/refs/heads/{branch}"
        update_ref_payload = {
            "sha": new_commit_sha,
            "force": True
        }
        update_ref_resp = await client.patch(update_ref_url, json=update_ref_payload, headers=self._headers)
        update_ref_resp.raise_for_status()

        return new_commit_sha

    async def create_pr(self, repo_id: int, source_branch: str,
                        target_branch: str, title: str) -> dict:
        """创建 Pull Request"""
        client = await self._get_http_client()
        repo_info = await self._get_repo_info(repo_id)
        pr_url = f"{self.base_url}/repos/{self.default_org}/{repo_info['name']}/pulls"

        payload = {
            "title": title,
            "head": source_branch,
            "base": target_branch,
            "body": self._generate_pr_body(source_branch, target_branch)
        }

        resp = await client.post(pr_url, json=payload, headers=self._headers)
        resp.raise_for_status()
        return resp.json()

    async def _get_repo_info(self, repo_id: int) -> dict:
        """获取仓库信息"""
        client = await self._get_http_client()
        url = f"{self.base_url}/repos/{self.default_org}/{repo_id}"
        resp = await client.get(url, headers=self._headers)
        resp.raise_for_status()
        return resp.json()

    async def _get_file_sha(self, repo_id: int, file_path: str, branch: str) -> str:
        """获取文件 SHA（用于更新时指定版本）"""
        client = await self._get_http_client()
        repo_info = await self._get_repo_info(repo_id)
        url = f"{self.base_url}/repos/{self.default_org}/{repo_info['name']}/contents/{file_path}?ref={branch}"
        resp = await client.get(url, headers=self._headers)
        if resp.status_code == 404:
            return ""  # 文件不存在
        resp.raise_for_status()
        return resp.json()["sha"]

    def _generate_pr_body(self, source_branch: str, target_branch: str) -> str:
        """生成 PR 描述"""
        return f"Auto-generated PR: merge {source_branch} into {target_branch}\n\n" \
               f"Source: {source_branch}\n" \
               f"Target: {target_branch}\n" \
               f"Created by: DevFlow Bot"

    async def close(self):
        """关闭 HTTP 客户端连接池"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
```

---

## 11. 通知服务

### 11.1 职责概述

通知服务负责在关键节点向人类用户推送通知。通知方式：平台内消息（WebSocket 推送）+ 邮件（可选配置）。

### 11.2 通知类型

| 类型 | 触发时机 |
|---|---|
| step_complete | 流程步骤完成 |
| qa_pass | QA 检验通过 |
| qa_fail | QA 检验未通过 |
| task_assigned | 任务分配 |
| task_completed | 任务完成 |
| project_complete | 项目完成 |
| system_alert | 系统告警 |

### 11.3 通知节点

- 需求确认完成
- 设计完成
- 测试用例完成
- 代码编写完成
- 测试完成
- 安全审计完成
- 部署完成

### 11.4 通知机制

```python
class NotificationService:
    """通知服务"""

    async def send_notification(self, user_id: int, project_id: int,
                                content: str, notification_type: str):
        """发送通知"""
        # 1. 持久化到数据库
        notification = await self.notification_repo.create(
            user_id=user_id, project_id=project_id,
            content=content, type=notification_type
        )

        # 2. WebSocket 实时推送
        await self._push_via_websocket(user_id, {
            "type": "notification",
            "notification": notification.to_dict()
        })

        # 3. 邮件推送（可选，异步 Celery 任务）
        if config.EMAIL_ENABLED:
            await send_email.delay(user_id, content)
```

---

## 12. WebSocket 实时通信

### 12.1 职责概述

WebSocket 服务提供实时双向通信能力，支撑以下场景：

- 群聊消息实时推送（讨论模式 + 会议模式）
- 16 步流程进展事件推送
- Agent 流式响应输出
- 通知实时推送
- 蜂群执行进度实时更新

### 12.2 通道设计 (V20 新增)

WebSocket 采用通道 (channel) 隔离不同用途的消息流：

| 通道 | WebSocket 端点 | 消息方向 | 说明 |
|---|---|---|---|
| 群聊通道 | ws://host/ws/group-chat | 双向 | 订阅/取消订阅群组，发送/接收消息 |
| 通知通道 | ws://host/ws/notifications | 服务端→客户端 | 单向推送，客户端订阅后接收通知 |
| 流程通道 | ws://host/ws/workflow/:project_id | 服务端→客户端 | 单向推送，项目流程状态变更事件 |

**通道订阅机制**:
- 客户端连接后发送 `subscribe` 消息指定目标群组/项目
- 服务端维护 `channel -> connections` 映射表（Redis 存储，支持多实例）
- 消息推送时按通道路由到对应的连接集合

### 12.3 WebSocket 端点

| 端点 | 用途 |
|---|---|
| ws://host/ws/group-chat | 群聊实时通信 |
| ws://host/ws/notifications | 通知推送 |
| ws://host/ws/workflow/:project_id | 流程状态推送 |

### 12.4 消息协议 (V19 新增)

所有 WebSocket 消息采用统一 JSON 格式：

```json
{
  "message_id": "uuid-v4",
  "type": "message_new",
  "timestamp": "2026-06-22T10:30:00Z",
  "data": { ... }
}
```

- `message_id`: 唯一消息标识符 (UUID v4)
- `type`: 消息类型 (见下方类型表)
- `timestamp`: ISO 8601 时间戳
- `data`: 消息载荷，结构依 type 而定

### 12.5 群聊 WebSocket 协议

**客户端发送的消息类型**:

| 类型 | 描述 |
|---|---|
| subscribe | 订阅指定群组的消息 |
| unsubscribe | 取消订阅群组的消息 |
| send_message | 发送消息到群组 (支持 @Agent 定向沟通) |
| start_meeting | 启动会议 (指定主题、主持人、类型、时长) |
| stop_meeting | 停止当前会议 |
| meeting_intervention | 会议进行中人类用户干预 |

**服务端推送的事件类型**:

| 事件类型 | 描述 |
|---|---|
| subscribed | 成功订阅群组 |
| message_new | 新消息到达 |
| message_start | Agent 开始回复 (流式输出开始) |
| message_chunk | Agent 回复的流式内容块 |
| message_complete | Agent 回复完成 |
| agent_status | Agent 状态更新 (typing/speaking/idle) |
| meeting_started | 会议开始 |
| meeting_stopped | 会议结束 |
| meeting_phase | 会议阶段变更 |
| meeting_agenda | 会议议程就绪 |
| meeting_minutes | 会议纪要推送 |
| meeting_outcome_saved | 会议结果已保存 |
| task_created | 新任务创建 (来自会议待办) |

### 12.6 心跳与断线重连 (V19 新增 / V20 修订)

**心跳机制**:
- 服务端每 30 秒发送 ping 帧
- 客户端应在 10 秒内回复 pong 帧
- 超过 30 秒未收到 pong，服务端关闭连接并清理资源
- 心跳不通过 JSON 消息实现，使用 WebSocket 原生 ping/pong 帧

**断线处理**:
- 连接断开时，ConnectionManager 自动清理该连接的所有订阅
- 群组订阅状态仅在当前连接存活时有效
- 断线期间的消息保存到 `group_messages` 表，标记 `is_delivered=false`

**重连机制**:
- 前端检测到断线后自动重连（指数退避: 1s/2s/4s/8s/16s，最大 30s）
- 重连成功后自动恢复群组订阅
- 服务端补发断线期间未投递的消息（基于 `is_delivered` 标记）
- 客户端使用 `message_id` 去重，避免重复显示

### 12.7 消息持久化方案 (V20 新增)

WebSocket 消息的持久化策略：

1. **群聊消息**: 所有通过 WebSocket 发送的群聊消息同时写入 `group_messages` 表，`is_delivered` 字段标记是否已推送到在线用户。断线用户重连后查询未投递消息并补发
2. **流程状态事件**: 不持久化到 `group_messages`，仅通过 WebSocket 实时推送。前端需自行缓存最近的状态快照
3. **通知消息**: 持久化到 `notifications` 表，WebSocket 仅作为推送通道。用户可通过 REST API 拉取历史通知
4. **会议事件**: 会议纪要和决议持久化到 `meeting_outcomes` 表。WebSocket 仅推送实时事件

**消息补发流程**:
```
用户重连 → 建立 WebSocket → 发送 subscribe 消息
→ 服务端查询该用户所属群组中 is_delivered=false 的消息
→ 按时间顺序补发最近 100 条未投递消息
→ 批量更新 is_delivered=true
→ 正常接收新消息
```

### 12.8 连接生命周期管理 (V19 新增)

```python
import uuid

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # user_id -> [connection_uuids]
        self.user_connections: Dict[int, List[str]] = defaultdict(list)
        # connection_uuid -> WebSocket 映射
        self._uuid_to_ws: Dict[str, WebSocket] = {}
        # connection_uuid -> user_id 映射
        self._uuid_to_user: Dict[str, int] = {}
        # group_id -> [user_ids]  (订阅该群组的用户)
        self.group_subscriptions: Dict[int, Set[int]] = defaultdict(set)

    async def connect(self, ws: WebSocket, user_id: int):
        """用户连接"""
        await ws.accept()
        conn_uuid = str(uuid.uuid4())
        self.user_connections[user_id].append(conn_uuid)
        self._uuid_to_ws[conn_uuid] = ws
        self._uuid_to_user[conn_uuid] = user_id
        return conn_uuid

    async def subscribe_group(self, conn_uuid: str, user_id: int, group_id: int):
        """订阅群组"""
        self.group_subscriptions[group_id].add(user_id)
        ws = self._uuid_to_ws.get(conn_uuid)
        if ws:
            await self._send(ws, {"type": "subscribed", "group_id": group_id})

    async def _send(self, ws: WebSocket, message: dict):
        """安全发送消息"""
        try:
            await ws.send_json(message)
        except Exception:
            pass  # 连接已断开，在 disconnect 中清理

    async def broadcast_group(self, group_id: int, message: dict):
        """向群组订阅者广播消息"""
        user_ids = self.group_subscriptions.get(group_id, set())
        for user_id in user_ids:
            for conn_uuid in self.user_connections.get(user_id, []):
                ws = self._uuid_to_ws.get(conn_uuid)
                if ws:
                    await self._send(ws, message)

    async def disconnect(self, conn_uuid: str, user_id: int):
        """断开连接，完整清理"""
        # 1. 移除 ws 连接
        if user_id in self.user_connections:
            if conn_uuid in self.user_connections[user_id]:
                self.user_connections[user_id].remove(conn_uuid)
            # 如果该用户没有其他连接了，清理相关数据
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        # 2. 清理 uuid 映射
        if conn_uuid in self._uuid_to_ws:
            del self._uuid_to_ws[conn_uuid]
        if conn_uuid in self._uuid_to_user:
            del self._uuid_to_user[conn_uuid]

        # 3. 清理 group_subscriptions 中对应的 user_id
        # 仅当该用户没有任何活跃连接时才从群组订阅中移除
        if user_id not in self.user_connections or not self.user_connections[user_id]:
            for group_id in list(self.group_subscriptions.keys()):
                self.group_subscriptions[group_id].discard(user_id)
                # 清理空的群组订阅
                if not self.group_subscriptions[group_id]:
                    del self.group_subscriptions[group_id]
```

断开连接清理逻辑说明：
- `user_connections` 使用 `connection_uuid` 作为标识符（而非 WebSocket 对象），避免 WebSocket 对象不可哈希 (unhashable) 的问题
- 若该 user_id 再无其他活跃连接，则从所有 `group_subscriptions` 中移除该 user_id，避免向已断开的用户发送消息
- 清理空的 group_subscriptions 条目，防止长期运行后内存泄漏
- `_uuid_to_ws` 和 `_uuid_to_user` 映射同步清理，确保断开时能快速定位 user_id 和 WebSocket 对象

---

## 13. 错误处理

### 13.1 统一异常处理

所有异常通过 FastAPI 的 ExceptionHandler 统一处理，返回标准化的 JSON 错误响应：

```python
class ErrorResponse(BaseModel):
    error: str           # 错误消息
    code: int            # 业务错误码
    detail: Optional[str]  # 详细错误信息
    trace_id: str        # 追踪 ID

class AppError(Exception):
    """应用基础异常"""
    def __init__(self, message: str, code: int = 400, detail: str = None):
        self.message = message
        self.code = code
        self.detail = detail

class WorkflowError(AppError):
    """流程异常（前置条件未满足）"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, code=422, detail=detail)

class AgentError(AppError):
    """Agent 执行异常"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, code=502, detail=detail)

class DependencyError(AppError):
    """依赖异常"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, code=409, detail=detail)

class QAFailError(AppError):
    """QA 检验不合格（使用 HTTP 406 Not Acceptable，与 WorkflowError 的 422 区分）"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, code=406, detail=detail)

class AgentTimeoutError(AppError):
    """Agent 执行超时异常"""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message, code=408, detail=detail)
```

错误码冲突修复说明：V13 中 `QAFailError` 和 `WorkflowError` 均使用 HTTP 422 状态码，前端无法通过 HTTP 状态码区分"前置条件未满足"和"QA 检验不合格"两种场景。V14 将 `QAFailError` 的 HTTP 状态码改为 406 (Not Acceptable)，语义上表示"产出不符合验收标准"，与 `WorkflowError` 的 422 (Unprocessable Entity，表示前置条件未满足) 明确区分。

命名说明：原 `TimeoutError` 与 Python 内置异常 `builtins.TimeoutError` 同名，已更名为 `AgentTimeoutError`，避免命名空间冲突和混淆。

### 13.2 错误分类体系 (V20 新增)

自定义异常按类别划分如下：

**业务异常** (4xx):
| 异常类 | HTTP 状态码 | 场景 |
|---|---|---|
| WorkflowError | 422 | 流程前置条件未满足 |
| QAFailError | 406 | QA 检验不合格 |
| DependencyError | 409 | 循环依赖/资源冲突 |
| SwarmError | 409 | 蜂群资源不足 |
| ValidationError | 422 | Pydantic 数据验证失败 |

**认证/授权异常** (401/403):
| 异常类 | HTTP 状态码 | 场景 |
|---|---|---|
| AuthenticationError | 401 | Token 缺失/过期/无效 |
| AuthorizationError | 403 | RBAC 权限拒绝 |

**外部服务异常** (5xx):
| 异常类 | HTTP 状态码 | 场景 |
|---|---|---|
| AgentError | 502 | Hermes Gateway 不可用 |
| AgentTimeoutError | 408 | Agent 执行超时 |
| GiteaError | 502 | Gitea API 调用失败 |
| RedisError | 503 | Redis 连接失败 |
| DatabaseError | 503 | PostgreSQL 连接/操作失败 |

**系统异常** (500):
| 异常类 | HTTP 状态码 | 场景 |
|---|---|---|
| AppError | 500 | 未预期的内部错误 |
| CeleryError | 500 | Celery 任务队列异常 |

### 13.3 错误码表

| 错误码 | 含义 | 场景 |
|---|---|---|
| 400 | 请求参数错误 | 参数验证失败 |
| 401 | 未认证 | Token 缺失或过期 |
| 403 | 权限不足 | RBAC 拒绝 |
| 404 | 资源不存在 | 项目/任务/Agent 不存在 |
| 406 | QA 检验不合格 | 产出不符合验收标准，退回重做 |
| 408 | 请求超时 | Agent 执行超时 (30 分钟) 或信号量等待超时 |
| 409 | 资源冲突 | 循环依赖 / 重复操作 |
| 422 | 前置条件未满足 | 流程步骤前置条件不满足，无法执行 |
| 429 | 请求过多 | 并发数超过信号量限制 |
| 500 | 服务器内部错误 | 未预期的异常 |
| 502 | Agent 网关错误 | Hermes Gateway 不可用 |
| 503 | 服务不可用 | 依赖服务 (Redis/Gitea/DB) 不可用 |

### 13.4 异常传播机制 (V19 新增)

异常从内向外传播路径:

```
Repository 层 (数据库操作异常)
    → Service 层 (转换为业务异常)
    → Router 层 (FastAPI ExceptionHandler 捕获)
    → 返回标准化 JSON 错误响应
    → 记录到结构化日志 (含 trace_id)
```

- 数据库异常 (IntegrityError, OperationalError): 转换为 AppError(code=500)
- Gateway 调用异常 (ConnectionError, Timeout): 转换为 AgentError(code=502)
- Redis 异常 (ConnectionError): 转换为 AppError(code=503)
- 业务验证异常: 直接抛出对应的业务异常 (WorkflowError, QAFailError 等)
- 所有异常均记录 trace_id，可通过日志追踪完整调用链

### 13.5 关键流程容错

- 关键流程失败时提供明确错误提示和人工介入入口
- Agent 执行失败时，海梅自动重试（最多 3 次，指数退避：30s/60s/120s）
- 3 次重试均失败后，切换备用 Agent 执行
- 备用 Agent 不可用时，通知人类用户并暂停任务
- 所有容错操作记录到 `agent_execution_logs` 表

---

## 14. 安全设计

### 14.1 认证与授权 (V20 修订)

**JWT Token 认证流程**:

```
1. 用户登录 → 验证用户名/密码 → 签发 Access Token + Refresh Token
2. 客户端存储 Token → 后续请求携带 Authorization: Bearer <access_token>
3. 服务端中间件验证 Token → 提取用户信息 → 注入请求上下文
4. Token 过期 → 客户端使用 Refresh Token 换取新的一对 Token
5. 用户登出 → 将 Access Token JTI 加入 Redis 黑名单
```

- **Token 参数**:
  - Access Token: 有效期 15 分钟
  - Refresh Token: 有效期 7 天
  - 签发算法: RS256（非对称算法）
  - 私钥用于签发 Token，公钥用于验证 Token，多服务部署时无需共享密钥
  - 私钥存储在 `.env` 文件的 `JWT_PRIVATE_KEY` 配置项中，公钥存储在 `JWT_PUBLIC_KEY` 配置项中

- **Token 吊销机制**:
  - 用户登出或密码变更后，将 Access Token 的 JTI (JWT ID) 加入 Redis 黑名单
  - 黑名单键格式: `token:blacklist:{jti}`，过期时间与 Token 剩余有效期一致
  - 每次验证 Token 时检查 Redis 黑名单，若存在则拒绝访问
  - Refresh Token 采用轮换机制：每次使用 Refresh Token 获取新的 Access Token 时，旧的 Refresh Token 立即失效，新签发一对 Token

**RBAC 权限模型** (V20 修订):

| 角色 | 权限范围 | 可操作资源 |
|---|---|---|
| user (普通用户) | 自身项目 | 创建/查看/操作自己的项目、任务、群组 |
| admin (系统管理员) | 全局 | 所有项目、Agent 配置、系统设置、备份管理 |

**API 端点权限标注** (V20 新增):

| 端点前缀 | 最低权限 | 说明 |
|---|---|---|
| /api/v1/auth/* | 无需认证 (login/register) / 已认证 (refresh/logout/me) | 认证相关 |
| /api/v1/projects/* | user | 仅可操作自身项目 |
| /api/v1/workflow/* | user | 仅可操作自身项目的流程 |
| /api/v1/tasks/* | user | 仅可操作自身项目的任务 |
| /api/v1/agents/* | user (查看) / admin (管理) | 查看对所有用户开放 |
| /api/v1/swarms/* | user | 仅可操作自身项目的蜂群 |
| /api/v1/groups/* | user | 仅可操作自身项目的群组 |
| /api/v1/qa/* | user | 仅可查看自身项目的 QA 记录 |
| /api/v1/hermes/* | admin | 仅限管理员操作 Hermes Gateway |
| /api/v1/repos/* | user | 仅可操作自身项目的仓库 |
| /api/v1/notifications/* | user | 仅可查看自身通知 |
| /api/v1/system/* | admin | 系统管理端点 |
| /ws/* | user | WebSocket 连接需要有效 Token |

**认证中间件实现** (V20 新增):

```python
# middleware.py
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """从 JWT Token 中提取当前用户"""
    token = credentials.credentials
    # 1. 检查 Redis 黑名单
    if await redis_client.exists(f"token:blacklist:{token_jti}"):
        raise HTTPException(status_code=401, detail="Token 已失效")
    # 2. 验证并解码 Token
    try:
        payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    # 3. 查询用户
    user = await user_repo.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user

# 路由级别权限装饰器
def require_admin(user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

def require_project_owner(project_id: int, user: User = Depends(get_current_user)):
    """要求项目所有者权限"""
    project = await project_repo.get_by_id(project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return project
```

### 14.2 数据安全

- **传输加密**: HTTPS 传输加密
- **密码存储**: bcrypt 哈希存储，cost factor = 12
- **Agent 交互数据**: 脱敏存储，敏感信息不记录到日志
- **项目成果安全**: 代码/成果仅对人类用户和授权 Agent 可见

### 14.3 API 安全 (V19 补充)

- **速率限制**: 基于 Redis 滑动窗口算法，每个用户每秒最多 100 次 API 请求。键格式 `rate_limit:{user_id}:{endpoint}`，窗口大小 1 秒，计数阈值 100。超过限制返回 HTTP 429
- **CORS**: 使用 `fastapi.middleware.cors.CORSMiddleware`，仅允许配置的前端域名 (`ALLOWED_ORIGINS` 环境变量)，支持凭证 (credentials)。预检请求 (OPTIONS) 缓存 600 秒
- **CSRF 防护**: JWT 通过 HTTP Header (`Authorization: Bearer ***`) 传递，不使用 Cookie，因此不受 CSRF 攻击影响。CORS 限制了跨域请求，进一步降低了风险
- **请求体大小限制**: 默认 10MB（文件上传 API 为 50MB），通过 Uvicorn `--limit-max-request-size` 配置
- **输入验证**: 所有输入通过 Pydantic 模型验证，无效输入直接返回 422 错误
- **SQL 注入防护**: SQLAlchemy ORM 使用参数化查询，禁止字符串拼接 SQL。Raw SQL 查询使用 SQLAlchemy text() 和绑定参数

### 14.4 审计日志

记录所有关键操作：

- Agent 任务分派
- QA 检验结果
- 代码提交
- 错误和异常
- 用户登录/登出
- 配置变更

### 14.5 多用户资源隔离

- **项目级别隔离**: 每个项目的 Agent 执行在独立的会话空间中运行
- **Agent 并发限制**: 同一 Agent Profile 同一时间只能执行一个项目的任务。GatewayClient 通过 `_profile_locks` 字典为每个 profile 维护独立的 `asyncio.Semaphore(1)` 互斥锁，在 `send_message` 方法中先获取总信号量再获取 profile 级互斥锁，确保多项目并发时同一 agent 不会被分派多个任务
- **蜂群 Agent 隔离**: 不同项目的蜂群 Agent 使用独立的持久化工作目录 (`/data/devflow/swarms/{project_id}/`)，挂载为 Docker named volume 确保容器重启后数据不丢失
- **数据库隔离**: 通过 project_id 字段实现逻辑隔离，用户只能访问自己发起的项目数据

---

## 15. 数据验证规则 (V19 新增)

### 15.1 验证框架

使用 Pydantic v2 进行数据验证，所有 API 请求体/响应体均定义对应的 Pydantic schema。

### 15.2 关键验证规则

**项目创建 (ProjectCreate)**:
```python
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="项目名称")
    description: str = Field("", max_length=5000, description="项目描述")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("项目名称不能为空")
        return v
```

**步骤执行 (StepExecute)**:
```python
class StepExecute(BaseModel):
    options: Optional[StepOptions] = None

class StepOptions(BaseModel):
    force_rerun: bool = Field(False, description="强制重新执行")
    custom_agent: Optional[str] = Field(None, description="自定义 Agent Profile")

    @field_validator("custom_agent")
    @classmethod
    def validate_agent(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in NAMED_AGENT_PROFILES:
            raise ValueError(f"无效的 Agent Profile: {v}")
        return v
```

**步骤编号验证**:
```python
@field_validator("step_number")
@classmethod
def validate_step_number(cls, v: int) -> int:
    if v < 2 or v > 16:
        raise ValueError("步骤编号必须在 2-16 之间")
    return v
```

**群消息验证 (GroupMessage)**:
```python
class GroupMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    mentions: List[str] = Field([], max_length=10, description="提及的 Agent/用户")

    @field_validator("mentions")
    @classmethod
    def validate_mentions(cls, v: List[str]) -> List[str]:
        # 过滤无效的 mention
        valid = [m for m in v if m in NAMED_AGENT_NAMES]
        return valid
```

### 15.3 响应体 schema

所有 API 响应使用统一的响应包装:
```python
class ApiResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: str = "success"
    pagination: Optional[PaginationInfo] = None

class PaginationInfo(BaseModel):
    has_more: bool
    next_cursor: Optional[str] = None
    limit: int
    total: Optional[int] = None
```

---

## 16. 日志与监控

### 16.1 日志管理

- **日志级别**: DEBUG / INFO / WARN / ERROR / FATAL
- **日志格式**: JSON 结构化日志
  ```json
  {
    "timestamp": "2026-06-16T10:30:00Z",
    "level": "INFO",
    "service": "devflow-backend",
    "trace_id": "abc-123-def",
    "message": "Agent 任务分派成功",
    "context": {
      "project_id": 1,
      "agent_name": "houfa",
      "task_id": 42
    }
  }
  ```
- **日志存储**: 本地文件（按天轮转，保留 30 天）+ ELK Stack 集中管理（保留 90 天）
- **关键操作日志**: Agent 任务分派、QA 检验结果、代码提交、错误和异常

### 16.2 指标采集 (Metrics)

使用 Prometheus 时序数据库，指标保留 30 天：

| 指标类别 | 指标 | 采集间隔 |
|---|---|---|
| 系统级 | CPU 使用率、内存使用率、磁盘 IO、网络带宽 | 30 秒 |
| 应用级 | API 响应时间 P50/P95/P99、QPS、错误率、活跃连接数 | 10 秒 |
| Agent 级 | 任务执行时长、任务成功率、Agent 负载、蜂群 Agent 活跃度 | 30 秒 |
| 业务级 | 项目数、活跃项目数、QA 检验通过率、各步骤平均耗时 | 实时统计 |

### 16.3 链路追踪 (Tracing)

- 采用 OpenTelemetry 标准
- 为每个 Agent 任务分配唯一 Trace ID
- 追踪范围：从海梅分派任务开始，经过蜂群 Agent 执行、QA 检验、代码提交的全链路
- 存储：Jaeger 后端，保留 7 天

### 16.4 告警规则

| 告警级别 | 条件 | 通知方式 |
|---|---|---|
| 系统级 | CPU >85% 持续 5 分钟、内存 >90% 持续 3 分钟、磁盘 >80% | WebSocket + 邮件 |
| 应用级 | API 错误率 >5%、P95 响应时间 >5 秒、连续 10 个 Agent 任务失败 | WebSocket + 邮件 |
| Agent 级 | Agent 进程宕机、连续 3 次重试失败、单个任务执行超过 30 分钟 | WebSocket + 邮件 |

**告警升级**: 首次告警通知系统管理员，30 分钟内未处理则通知项目人类用户。

---

## 17. 配置管理

### 17.1 配置项

使用 pydantic-settings 管理配置，支持环境变量和配置文件（.env / config.yaml）：

```python
class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "DevFlow"
    DEBUG: bool = False
    JWT_PRIVATE_KEY: str  # RS256 私钥 (PEM 格式)
    JWT_PUBLIC_KEY: str   # RS256 公钥 (PEM 格式)
    API_VERSION: str = "v1"

    # 数据库
    DATABASE_URL: str  # PostgreSQL 连接字符串

    # Redis
    REDIS_URL: str  # Redis 连接字符串

    # Gitea
    GITEA_HOST: str = "localhost"
    GITEA_PORT: int = 3000
    GITEA_PROTOCOL: str = "http"
    GITEA_API_TOKEN: str
    GITEA_USERNAME: str = "devflow_bot"
    GITEA_DEFAULT_ORG: str = "devflow"

    # Hermes Agent
    HERMES_PROFILES_DIR: Path = Path.home() / ".hermes" / "profiles"
    GATEWAY_DEFAULT_PORT_START: int = 8765
    GATEWAY_MAX_CONCURRENT: int = 5  # 信号量并发限制
    GATEWAY_TIMEOUT: int = 1800  # 30 分钟超时 (秒)
    GATEWAY_SEMAPHORE_TIMEOUT: int = 60  # 信号量等待超时 (秒)
    RETRY_MAX_ATTEMPTS: int = 3  # 最大重试次数
    RETRY_BACKOFF_BASE: int = 30  # 首次重试间隔 (秒)

    # Celery
    CELERY_BROKER_URL: str  # Redis 作为消息代理
    CELERY_RESULT_BACKEND: str

    # 监控
    PROMETHEUS_ENABLED: bool = True
    OPENTELEMETRY_ENABLED: bool = True

    # 邮件
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587

    # V19 新增: 文件存储
    ARTIFACTS_STORAGE_PATH: str = "/data/devflow/artifacts"
    ARTIFACTS_MAX_SIZE_MB: int = 50

    # V19 新增: 蜂群配置
    SWARM_MAX_PER_PROJECT: int = 3
    SWARM_MAX_TOTAL_AGENTS: int = 20

    class Config:
        env_file = ".env"
```

### 17.2 .env 配置示例 (V20 新增)

```bash
# .env 示例文件

# === 应用配置 ===
APP_NAME=DevFlow
DEBUG=false
API_VERSION=v1

# === JWT 认证 (RS256 非对称密钥) ===
# 生成密钥: openssl genrsa -out private.pem 2048 && openssl rsa -in private.pem -pubout -out public.pem
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A...\n-----END PUBLIC KEY-----"

# === 数据库 (PostgreSQL 14+) ===
DATABASE_URL=postgresql+asyncpg://devflow:devflow_password@postgres:5432/devflow_db

# === Redis 6+ ===
REDIS_URL=redis://:redis_password@redis:6379/0

# === Gitea 代码仓库 ===
GITEA_HOST=gitea
GITEA_PORT=3000
GATEWAY_PROTOCOL=http
GITEA_API_TOKEN=your-gitea-api-token-here
GITEA_USERNAME=devflow_bot
GITEA_DEFAULT_ORG=devflow

# === Hermes Agent ===
HERMES_PROFILES_DIR=/home/jim/.hermes/profiles
GATEWAY_DEFAULT_PORT_START=8765
GATEWAY_MAX_CONCURRENT=5
GATEWAY_TIMEOUT=1800
GATEWAY_SEMAPHORE_TIMEOUT=60
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_BASE=30

# === Celery ===
CELERY_BROKER_URL=redis://:redis_password@redis:6379/1
CELERY_RESULT_BACKEND=redis://:redis_password@redis:6379/2

# === 监控 ===
PROMETHEUS_ENABLED=true
OPENTELEMETRY_ENABLED=true

# === 邮件通知 (可选) ===
EMAIL_ENABLED=false
SMTP_HOST=smtp.example.com
SMTP_PORT=587

# === 文件存储 ===
ARTIFACTS_STORAGE_PATH=/data/devflow/artifacts
ARTIFACTS_MAX_SIZE_MB=50

# === 蜂群配置 ===
SWARM_MAX_PER_PROJECT=3
SWARM_MAX_TOTAL_AGENTS=20

# === CORS ===
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

---

## 18. 部署架构

### 18.1 Docker 部署

```yaml
# docker-compose.yml
version: "3.8"

services:
  # DevFlow 后端 (FastAPI 主服务 - 仅处理 HTTP/WebSocket 请求)
  devflow:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://devflow:devflow_password@postgres:5432/devflow_db
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    volumes:
      - artifacts_data:/data/devflow/artifacts
      - swarm_data:/data/devflow/swarms
    depends_on:
      - postgres
      - redis

  # Celery Worker (异步任务处理)
  celery-worker:
    build: .
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://devflow:devflow_password@postgres:5432/devflow_db
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    volumes:
      - swarm_data:/data/devflow/swarms
      - artifacts_data:/data/devflow/artifacts
    depends_on:
      - devflow
      - redis

  # Celery Beat (定时任务调度器)
  celery-beat:
    build: .
    command: celery -A app.tasks.celery_app beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - devflow
      - redis

  # 数据库
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: devflow_db
      POSTGRES_USER: devflow
      POSTGRES_PASSWORD: devflow_password
    volumes:
      - pg_data:/var/lib/postgresql/data
      - wal_archive:/var/lib/postgresql/wal_archive

  # Redis
  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

  # Gitea (代码仓库)
  gitea:
    image: gitea/gitea:latest
    ports:
      - "3000:3000"
      - "222:22"
    environment:
      GITEA__database__DB_TYPE: postgres
      GITEA__database__HOST: postgres:5432
      GITEA__database__NAME: gitea
      GITEA__database__USER: gitea
      GITEA__database__PASSWD: gitea_db_password
    volumes:
      - gitea_data:/data

volumes:
  pg_data:
  redis_data:
  gitea_data:
  swarm_data:
  artifacts_data:
  wal_archive:
```

Docker 部署修复说明
1. **celery-worker** 服务：独立容器运行 Celery Worker，处理所有异步任务（Agent 执行、蜂群调度、QA 检验、Gitea 同步等），配置 4 个并发 worker 进程
2. **celery-beat** 服务：独立容器运行 Celery Beat 定时调度器，负责定时任务（Profile 扫描每 30 分钟、数据库备份每日凌晨 2:00、文件备份每日凌晨 3:00、代码仓库归档每日凌晨 4:00）
3. 三个服务共享相同的 Redis broker/backend 配置和数据库连接，celery-worker 和 celery-beat 依赖 devflow 服务以确保应用代码已就绪
4. swarm_data 卷同时挂载到 devflow 和 celery-worker，确保蜂群 Agent 工作目录在异步任务执行中可访问
5. artifacts_data 卷挂载到 devflow，用于存储文件产出物

### 18.2 多实例与负载均衡 (V19 新增)

**部署模式**:
- **开发/测试环境**: 单实例部署，直接访问 FastAPI 服务
- **生产环境**: 多实例部署，通过 Nginx 反向代理负载均衡

**负载均衡策略**:
```nginx
# Nginx 配置示例
upstream devflow_backend {
    least_conn;  # 最少连接数算法
    server devflow-1:8000;
    server devflow-2:8000;
    server devflow-3:8000;
}

# HTTP 请求
location /api/ {
    proxy_pass http://devflow_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

# WebSocket 连接 (sticky session)
location /ws/ {
    proxy_pass http://devflow_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header X-Real-IP $remote_addr;
    # WebSocket 需要 sticky session，使用 ip_hash 保证同一用户连接到同一实例
}
```

**WebSocket Sticky Session**: WebSocket 连接需要 sticky session，推荐使用 Nginx `ip_hash` 或 `hash $http_cookie` 确保同一用户的 WebSocket 连接到同一后端实例，避免 ConnectionManager 状态不一致。

**水平扩展方案**:
- FastAPI 实例: 无状态，可水平扩展，增加实例即可提升 HTTP 处理能力
- Celery Worker: 增加 worker 实例提升异步任务并发能力
- Redis: 使用 Redis Sentinel 或 Redis Cluster 实现高可用
- PostgreSQL: 主从复制，读写分离（写操作走主库，只读查询可走从库）

### 18.3 9 个命名 Agent 部署

每个命名 Agent 独立部署为 Hermes Agent Profile 实例：

- 独立进程、独立配置文件、独立 Gateway 端口
- 端口范围: 8765-8773
- Profile 存储路径: `~/.hermes/profiles/{profile_name}/`
- 各 Agent 进程独立启动、独立运行、独立停止，互不影响

---

## 19. 数据迁移与版本升级

### 19.1 数据迁移

- 使用 Alembic 管理数据库迁移
- 支持正向迁移和回滚
- 流程: 备份当前数据 → 在测试环境执行迁移脚本验证 → 迁移通过后在生产环境执行 → 验证数据完整性 → 保留旧版本数据 7 天以备回滚
- 每次迁移记录迁移 ID、执行时间、执行结果、影响数据量

### 19.2 版本升级

- 语义化版本控制 (MAJOR.MINOR.PATCH)
- MINOR 版本升级保证 API 向后兼容
- 升级流程: 发布升级公告 → 用户备份数据 → Docker 镜像更新 → 自动执行数据库迁移 → 健康检查验证 → 失败自动回滚
- 保留最近 3 个版本的 Docker 镜像标签，支持一键回滚

---

## 20. 容灾恢复与备份

### 20.1 恢复目标

- **RTO**: 系统故障后 2 小时内恢复服务
- **RPO**: 数据丢失不超过最后一小时内

### 20.2 备份策略 (V20 修订)

采用全量备份 + PostgreSQL WAL 归档策略以满足 RPO ≤ 1 小时的要求：

| 备份对象 | 频率 | 保留周期 | 备份方式 |
|---|---|---|---|
| 数据库全量 (pg_basebackup) | 每日凌晨 2:00 | 30 天 | Celery Beat 触发 backup_db 任务 |
| PostgreSQL WAL 归档 | 持续归档 (每 5 分钟切换) | 30 天 | PostgreSQL archive_mode=on |
| 文件存储全量 | 每日凌晨 3:00 | 30 天 | Celery Beat 触发 backup_files 任务 |
| 代码仓库归档 | 每日凌晨 4:00 | 30 天 | Celery Beat 触发 backup_gitea 任务 (git bundle) |
| 每周备份 (周日凌晨) | 每周 | 90 天 | 全量备份的长期保留副本 |
| 每月备份 (每月 1 日) | 每月 | 365 天 | 全量备份的长期保留副本 |

**备份内容说明**:
- 数据库: PostgreSQL 全量快照 + WAL 日志归档，支持任意时间点恢复 (PITR)
- 文件产出物: /data/devflow/artifacts 目录的完整归档 (tar.gz + 校验和)
- 代码仓库: Gitea 数据目录 + git bundle 导出
- 蜂群工作目录: /data/devflow/swarms 目录（仅保留活跃项目）

### 20.3 恢复流程 (V20 修订)

**数据库恢复**:
1. 从最新备份恢复: `pg_restore -d devflow_db /backups/daily/latest.dump`
2. 如需 PITR 恢复: 基于全量备份 + WAL 归档恢复到指定时间点
3. 验证数据完整性: 检查关键表记录数、外键约束
4. 恢复文件存储和 Gitea 仓库
5. 启动应用并运行健康检查

**文件恢复**:
1. 定位备份文件: `ls -lt /backups/files/` 选择目标日期
2. 解压备份: `tar -xzf /backups/files/YYYY-MM-DD.tar.gz -C /data/devflow/artifacts/`
3. 校验完整性: 对比 SHA-256 校验和

**Gitea 仓库恢复**:
1. 从 git bundle 恢复: `git clone /backups/gitea/YYYY-MM-DD.bundle /tmp/repo`
2. 推送到 Gitea: `cd /tmp/repo && git remote add gitea <url> && git push gitea --all`

### 20.4 恢复演练

- 每季度进行一次完整恢复演练
- 步骤: 恢复数据库 → 恢复文件存储 → 恢复 Gitea 仓库 → 验证应用功能 → 记录恢复时间和数据完整性

### 20.5 数据库备份与恢复流程 (V19 新增)

**备份流程**:
1. Celery Beat 触发 `backup_db` 任务（每日凌晨 2:00）
2. 执行 `pg_basebackup -D /backups/daily/ -Ft -z -P`
3. 备份文件存储到 `/backups/daily/`，保留 30 天
4. 清理过期备份
5. 记录备份结果到日志

**恢复流程**:
1. 从最新备份恢复: `pg_restore -d devflow_db /backups/daily/latest.dump`
2. 如需 PITR 恢复: 基于全量备份 + WAL 归档恢复到指定时间点
3. 验证数据完整性: 检查关键表记录数、外键约束
4. 恢复文件存储和 Gitea 仓库
5. 启动应用并运行健康检查

---

## 21. 测试策略 (V20 修订)

### 21.1 测试框架

- **单元测试**: pytest + pytest-asyncio
- **集成测试**: pytest + TestClient (httpx)，测试数据库、Redis、Gateway 交互
- **E2E 测试**: pytest + Playwright，测试关键用户路径

### 21.2 测试覆盖率目标 (V20 新增)

| 测试类型 | 覆盖率目标 | 说明 |
|---|---|---|
| 单元测试 | ≥80% | 所有服务层、Schema 验证、异常类 |
| 集成测试 | ≥60% | 数据库操作、Redis 交互、外部 API |
| E2E 测试 | 覆盖 100% 关键路径 | 项目创建、16 步流程、QA 门控、WebSocket |

CI/CD 集成: 每次 PR 提交自动运行单元测试和集成测试，覆盖率低于目标值阻止合并。

### 21.3 测试分层

```
tests/
├── unit/                    # 单元测试 (不依赖外部服务)
│   ├── test_schemas.py      # Pydantic schema 验证测试
│   ├── test_exceptions.py   # 异常类测试
│   ├── test_statemachine.py # 状态机转换测试
│   └── test_dependency_graph.py # 依赖图算法测试
│
├── integration/             # 集成测试 (依赖测试数据库/Redis)
│   ├── test_project_service.py
│   ├── test_workflow_service.py
│   ├── test_qa_service.py
│   ├── test_swarm_service.py
│   └── test_gitea_client.py (Mock Gateway)
│
├── e2e/                     # 端到端测试 (完整请求链路)
│   ├── test_project_lifecycle.py  # 项目创建→执行→完成
│   ├── test_qa_flow.py        # QA 检验→通过/退回→重做
│   └── test_websocket.py      # WebSocket 连接→消息→断开→重连
│
└── fixtures/                # 测试数据工厂
    ├── factory.py           # pytest-factory_boy 工厂类
    ├── conftest.py          # 共享 fixtures (db_session, redis_client)
    └── mock_gateway.py      # Hermes Gateway Mock 服务器
```

### 21.4 Mock 策略 (V20 新增)

**Hermes Gateway Mock**:
- 使用 `respx` 或 `pytest-httpx` 拦截 httpx 请求
- 预定义的响应模板覆盖常见场景: 正常响应、超时、连接失败、5xx 错误
- 支持流式响应的 Mock（SSE 事件模拟）

```python
# fixtures/mock_gateway.py
import respx
import httpx

@respx.mock
async def test_agent_execution(mock_gateway):
    # Mock 正常响应
    respx.post("http://127.0.0.1:8767/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "测试架构设计文档"}}]
        })
    )
    # 执行测试...
```

**Gitea API Mock**:
- 使用 `respx` 拦截 GiteaClient 的 httpx 请求
- Mock 端点: create_repo、create_commit、create_pr
- 覆盖场景: 仓库创建成功、提交失败、PR 冲突

**Redis Mock**:
- 使用 `fakeredis` 提供内存中的 Redis 模拟
- 覆盖场景: 分布式锁获取/释放、缓存读写、依赖图操作

**数据库 Mock**:
- 使用独立的测试数据库容器（Docker）
- 每个测试使用独立事务，测试结束后自动回滚
- 使用 `pytest-factory_boy` 生成测试数据

### 21.5 关键测试场景

| 测试类别 | 场景 | 验证点 |
|---|---|---|
| 单元测试 | Pydantic 验证 | 无效输入返回 422 |
| 单元测试 | 状态机转换 | 非法转换抛出 WorkflowError |
| 单元测试 | 依赖图算法 | 循环依赖检测正确 |
| 集成测试 | 项目创建 | 数据库记录、Gitea 仓库、群组均创建成功 |
| 集成测试 | QA 检验通过 | 自动推进到下一步 |
| 集成测试 | QA 检验未通过 | 退回重做，24h 时限 |
| E2E 测试 | 完整流程 | 项目创建→16步执行→交付 |
| E2E 测试 | 蜂群执行 | 任务分解→分发→完成→收集 |
| E2E 测试 | WebSocket | 连接→发消息→接收→断线→重连→补发 |

### 21.6 测试数据管理

- 使用 `pytest-factory_boy` 生成测试数据
- 每个测试使用独立的事务，测试结束后自动回滚
- 测试数据库与生产数据库隔离，使用独立的 Docker 容器
- Gateway Mock 服务器模拟 Agent 响应，不依赖真实 Hermes 实例

### 21.7 CI/CD 集成

- 每次 PR 提交自动运行单元测试和集成测试
- 覆盖率低于目标值阻止合并
- E2E 测试在预发布环境运行

---

## 22. 性能指标与容量规划 (V19 新增)

### 22.1 目标性能指标

| 指标 | 目标值 | 测试方法 |
|---|---|---|
| API 响应时间 P50 | <100ms | 压力测试 (Locust) |
| API 响应时间 P95 | <200ms | 压力测试 (Locust) |
| API 响应时间 P99 | <500ms | 压力测试 (Locust) |
| WebSocket 消息延迟 | <50ms | 实时消息测试 |
| 数据库查询 P95 | <50ms | 慢查询日志分析 |
| Agent 任务调度延迟 | <1s | 端到端测量 |

### 22.2 容量规划

| 资源 | 容量 | 扩容触发条件 |
|---|---|---|
| 单 Agent 并发项目数 | 10 | 信号量等待超时率 >10% |
| 单项目蜂群数 | 3 | 达到上限时排队等待 |
| 全局蜂群 Agent 总数 | 20 | 配置项 SWARM_MAX_TOTAL_AGENTS |
| WebSocket 连接数 | 1000/实例 | 连接数 >800 时增加实例 |
| 数据库连接池 | 20 | 连接等待时间 >1s |
| Redis 内存使用 | 512MB | 使用率 >80% 时扩容 |

### 22.3 压力测试方案

- 使用 Locust 进行压力测试
- 测试场景: 10 个并发用户，每个用户创建一个项目并执行 16 步流程
- 监控指标: CPU、内存、响应时间、错误率
- 测试环境: 与生产环境配置一致

---

## 23. V20 修订记录

本节记录 V19 到 V20 的修订内容，对应后荣检验报告中的所有不合格项：

| 序号 | 严重级别 | 问题描述 | V20 修复方案 |
|---|---|---|---|
| 1 | BLOCKER | API 端点定义缺失 | V19 已包含完整 API 端点列表 (2.2-2.16)，V20 保持完整 |
| 2 | BLOCKER | 9 个命名 Agent 调度机制未定义 | 新增 6.4 节"Hermes Gateway API 契约"，明确请求/响应格式、超时策略、重试机制、Agent 失败恢复流程 |
| 3 | BLOCKER | 16 步状态机定义缺失 | 新增 5.3 节完整状态转移图（ASCII 图）、前置条件表、失败回滚策略（步骤级/跨步骤/项目级三种策略） |
| 4 | MAJOR | Celery 任务定义不完整 | 新增 5.7 节"Celery 任务签名定义"，为每个任务定义入参、返回值、重试策略、优先级队列 |
| 5 | MAJOR | 数据模型 Schema 缺失 | V19 已包含完整 ER 图和 18 张表定义 (4.1-4.2)，V20 保持完整 |
| 6 | MAJOR | WebSocket 设计过于简略 | 新增 12.2 节"通道设计"（channel 隔离）、12.7 节"消息持久化方案"（补发流程）、修订心跳/重连机制 |
| 7 | MAJOR | 认证授权设计缺失 | 新增 14.1 节完整 JWT 签发/验证流程图、RBAC 权限模型表、API 端点权限标注表、认证中间件代码示例 |
| 8 | MAJOR | 并发控制方案不明确 | 修订 6.7 节为"并发控制"，新增量化定义表（6 个维度的上限值、配置项、说明），4 个典型并发场景说明 |
| 9 | MINOR | 错误处理规范缺失 | 新增 13.2 节"错误分类体系"，按业务异常/认证异常/外部服务异常/系统异常分类 |
| 10 | MINOR | 配置管理细节缺失 | 新增 17.2 节".env 配置示例"，包含所有配置项的完整示例 |
| 11 | MINOR | 备份策略未说明 | 修订 20.2 节"备份策略"，新增备份方式列；修订 20.3 节"恢复流程"，分数据库/文件/Gitea 三种恢复方式 |
| 12 | MINOR | 测试策略未展开 | 新增 21.2 节"测试覆盖率目标"、21.4 节"Mock 策略"（Gateway/Gitea/Redis/数据库的 Mock 方案） |

---

## 24. V19 保留的改进内容

以下改进在 V19 中已实现，V20 继续保持：

| 序号 | 改进内容 | 状态 |
|---|---|---|
| 1 | workflow_service.py 拆分为 orchestrator/executor/statemachine 三个服务 | 保留 |
| 2 | 新增 artifact 产出物管理模块 | 保留 |
| 3 | 新增 pagination schema | 保留 |
| 4 | 测试目录结构完善（unit/integration/e2e/fixtures） | 保留 |
| 5 | 新增数据库表结构设计（18 张表 + ER 图） | 保留 |
| 6 | RESTful 语义修正（PUT → POST） | 保留 |
| 7 | 新增 Agent 生命周期管理 | 保留 |
| 8 | 新增蜂群详细实现方案 | 保留 |
| 9 | 新增 QA 检验详细流程 | 保留 |
| 10 | 新增 WebSocket 消息格式/心跳/断线处理 | 保留 |
| 11 | 新增异常传播机制 | 保留 |
| 12 | 补充安全设计细节 | 保留 |
| 13 | 新增数据验证规则 | 保留 |
| 14 | 补充 API 版本化方案 | 保留 |
| 15 | 新增文件产出物 API | 保留 |
| 16 | 新增多实例与负载均衡 | 保留 |
| 17 | 新增数据库备份与恢复流程 | 保留 |
| 18 | 新增测试策略 | 保留 |
| 19 | 新增性能指标与容量规划 | 保留 |
| 20 | Celery 长时间任务支持 | 保留 |
| 21 | Gateway 职责边界与降级策略 | 保留 |
| 22 | 状态管理与恢复方案 | 保留 |
| 23 | 数据一致性策略（双写/Saga/分布式锁） | 保留 |
| 24 | 批量操作端点 | 保留 |
| 25 | 游标分页方案 | 保留 |
| 26 | API 文档自动生成 | 保留 |
| 27 | 配置项补充 | 保留 |

---

**文档结束**
