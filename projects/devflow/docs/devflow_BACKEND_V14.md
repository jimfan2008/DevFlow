# DevFlow 项目管理平台 - 后端设计文档

**版本**: V14
**日期**: 2026-06-17
**作者**: HouWang (后旺)
**状态**: 修订版V14（修复后荣检验全部不合格项）

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
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│     │
│  │  │流程调度   │ │Agent调度 │ │QA门控    │ │蜂群管理   ││     │
│  │  │服务       │ │服务     │ │服务      │ │服务       ││     │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘│     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│     │
│  │  │讨论群     │ │代码仓库  │ │通知      │ │Gateway   ││     │
│  │  │服务       │ │集成服务  │ │服务      │ │Client    ││     │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘│     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │     │
│  │  │Profile   │ │WebSocket │ │日志监控   │              │     │
│  │  │扫描服务   │ │管理      │ │服务       │              │     │
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
│   │   └── meeting.py
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
│   │   └── meeting.py
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
│   │   └── websocket.py            # WebSocket 路由
│   │
│   ├── services/                   # 业务服务层
│   │   ├── project_service.py      # 项目管理服务
│   │   ├── agent_service.py        # Agent 管理服务
│   │   ├── workflow_service.py     # 流程调度服务
│   │   ├── task_scheduler.py       # 任务调度引擎
│   │   ├── qa_service.py           # QA 门控服务
│   │   ├── swarm_service.py        # 蜂群管理服务
│   │   ├── group_service.py        # 讨论群服务
│   │   ├── repo_service.py         # 代码仓库集成服务
│   │   ├── notification_service.py # 通知服务
│   │   ├── gateway_service.py      # Gateway 通信服务
│   │   ├── profile_service.py      # Profile 扫描服务
│   │   ├── meeting_service.py      # 会议模式服务
│   │   └── websocket_service.py    # WebSocket 管理服务
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
│   │   └── task_dependency_repo.py
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
- **分页**: 默认每页 20 条，通过 `?page=&limit=` 参数控制
- **错误码**: HTTP 状态码 + 业务错误码
- **Conventional Commits**: 所有代码提交遵循 Conventional Commits 规范

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
| PUT | /api/v1/projects/:id/workflow/step/:number | 执行指定步骤 (:number 为 2-16) | 是 |
| GET | /api/v1/projects/:id/workflow/status | 获取当前流程状态 | 是 |
| POST | /api/v1/projects/:id/workflow/rollback | 回退到指定步骤 (用于迭代) | 是 |

`PUT /api/v1/projects/:id/workflow/step/:number` 统一端点说明：
- `:number` 路径参数为 2-16 之间的整数，对应第二步至第十六步
- 请求体可选，用于传递步骤执行参数（如自定义 Agent 选择、特殊配置等）
- 请求体示例: `{"options": {"force_rerun": false}}`
- 服务端根据 `:number` 自动匹配对应步骤的 Agent 角色并分派任务
- 各步骤对应的 Agent 角色参见 5.2 节 WorkflowStep 与 workflow_steps 配置表

### 2.5 任务管理

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/projects/:id/tasks | 获取项目任务列表 | 是 |
| GET | /api/v1/tasks/:id | 获取任务详情 | 是 |
| PUT | /api/v1/tasks/:id | 更新任务状态 | 是 |
| GET | /api/v1/tasks/:id/dependencies | 获取任务依赖图 | 是 |
| POST | /api/v1/tasks/:id/dependencies | 添加任务依赖 | 是 |
| DELETE | /api/v1/tasks/:id/dependencies/:dep_id | 移除任务依赖 | 是 |

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

路由模块边界说明：Hermes Gateway 通信相关操作（健康检查、对话、任务拆解、Profile 同步等）统一归入 `/api/v1/hermes/` 前缀下，保持路由模块边界清晰。原 `POST /api/v1/agents/sync-hermes` 已移至本表。

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

### 2.13 系统管理

| 方法 | 路径 | 描述 | 认证 |
|---|---|---|---|
| GET | /api/v1/system/health | 系统健康检查 | 否 |
| GET | /api/v1/system/metrics | Prometheus 指标端点 | 否 |
| GET | /api/v1/system/stats | 系统统计信息 | Admin |
| POST | /api/v1/system/backup | 触发手动备份 | Admin |
| POST | /api/v1/system/migrate | 执行数据迁移 | Admin |

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

### 3.2 依赖注入

使用 FastAPI 的 Depends 机制进行依赖注入：

- **数据库会话**: 每个请求创建独立的异步数据库会话，请求结束后自动关闭
- **当前用户**: 从 JWT Token 中提取用户信息，注入到需要认证的路由
- **Redis 客户端**: 全局单例，注入到需要缓存或分布式锁的服务
- **Gateway Client**: 全局单例，注入到需要与 Agent 通信的服务
- **日志记录器**: 按模块注入，包含 trace_id 和请求上下文

### 3.3 事务管理

- 使用 SQLAlchemy 异步事务管理
- 关键操作（如项目创建、流程推进）使用事务确保数据一致性
- 跨服务调用使用 Saga 模式补偿机制
- 分布式锁使用 Redis SETNX 实现，防止并发冲突

---

## 4. Agent 调度服务

### 4.1 职责概述

Agent 调度服务是后端的核心调度中心，负责：

1. 管理 9 个命名 Agent 的生命周期和状态
2. 通过 Hermes Gateway API 与 Agent 通信
3. 执行并发控制（信号量限制，默认最大 5 个并发请求）
4. 实现容错机制（3 次重试、30 分钟超时）
5. 自动发现和同步 Hermes Agent Profile

### 4.2 9 个命名 Agent 配置

| 名称 | Profile | 角色 | 默认端口 |
|---|---|---|---|
| HaiMei | haimei | 项目经理 | 8765 |
| HouXing | houxing | 需求分析师 | 8766 |
| HouWang | houwang | 架构设计师 | 8767 |
| HouFa | houfa | 程序员 | 8768 |
| HouDa | houDa | 测试员 | 8769 |
| HouFu | houfu | CI/CD 工程师 | 8770 |
| HouGui | hougui | 文档管理员 | 8771 |
| HouRong | hourong | QA | 8772 |
| HouHua | houhua | 安全员 | 8773 |

### 4.3 Gateway 通信客户端

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

### 4.4 并发控制

使用 asyncio.Semaphore 限制并发请求数：

- **默认最大并发数**: 5（通过配置文件可调整）
- **并发范围**: 所有通过 Gateway Client 发送的 Agent 请求
- **等待策略**: 超出限制的请求进入等待队列，按 FIFO 顺序执行
- **超时处理**: 请求等待超过 60 秒仍未获取信号量，返回超时错误（通过 `asyncio.wait_for` 实现）
- **Profile 维度互斥**: 除总并发信号量外，每个 Agent Profile 维护独立的 asyncio.Semaphore(1) 互斥锁，确保同一 Agent Profile 同一时间只能执行一个项目的任务。多项目并发时，请求同一 profile 的任务将排队等待，不会被分派多个任务。

### 4.5 容错机制

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

### 4.6 Profile 自动扫描服务

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

ProfileScanner._check_gateway() 修复说明：V13 中该方法每次调用都创建新的 `httpx.AsyncClient`，违背了 4.3 节"复用 httpx.AsyncClient 连接池"的原则。V14 改为调用 `GatewayClient._get_http_client()` 复用连接池。

Profile 状态管理机制（事件驱动 + 定期扫描兜底）：

- **事件驱动**（主机制）: Agent 启动或停止时主动调用 `POST /api/v1/agents/:id/status-report` 上报状态变更，后端立即更新数据库和缓存
- **定期扫描**（兜底机制）: 每 30 分钟全量扫描一次 profiles 目录，检测端口状态并同步到数据库，用于修正因 Agent 异常退出未及时上报导致的状态不一致
- **手动触发**: 通过 `POST /api/v1/profiles/scan` 手动触发全量扫描
- **状态同步**: 扫描结果与 Agent 上报结果自动合并，以最新时间戳为准

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

### 5.3 流程推进机制

```python
class WorkflowService:
    """16 步流程调度服务"""

    async def execute_step(self, project_id: int, step_number: int):
        """执行指定步骤"""
        # 1. 验证前置条件
        await self._validate_prerequisites(project_id, step_number)

        # 2. 更新流程状态
        step = WorkflowStep(step_number)
        await self._update_workflow_status(project_id, step)

        # 3. 从数据库配置表获取对应 Agent（动态而非硬编码）
        assignee = await self._get_step_assignee(step_number, project_id)
        if assignee:
            await self._dispatch_to_agent(project_id, step, assignee)

        # 4. 记录执行日志
        await self._log_execution(project_id, step)

        # 5. WebSocket 推送流程状态变更
        await self._notify_step_started(project_id, step)

    async def _validate_prerequisites(self, project_id: int, step_number: int):
        """验证前置条件：上一步是否已完成"""
        if step_number == 1:
            return  # 第一步由人类用户执行
        current = await self._get_current_step(project_id)
        if current < step_number - 1:
            raise WorkflowError(f"必须先完成第 {step_number - 1} 步")

    async def on_qa_passed(self, task_id: int):
        """QA 检验通过回调：自动推进流程"""
        task = await self._get_task(task_id)
        project_id = task.project_id
        step = task.step_number

        # 检查当前步骤所有子任务是否全部通过
        all_passed = await self._check_step_complete(project_id, step)
        if all_passed:
            # 提交产物到代码库
            await self._submit_to_repo(project_id, step)
            # 自动推进到下一步
            next_step = step + 1
            if next_step <= 16:
                await self._advance_workflow(project_id, next_step)
                await self._notify_step_completed(project_id, step)
```

### 5.4 任务依赖图管理

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

### 5.5 Celery 异步任务

后端使用 Celery 处理以下异步任务：

| 任务 | 说明 | 触发方式 |
|---|---|---|
| agent_execution | Agent 任务执行 | 流程推进时触发 |
| swarm_dispatch | 蜂群任务分发 | 第七步/第九步/第十一步 |
| qa_inspection | QA 检验请求 | Agent 提交产出后 |
| profile_scan | Profile 自动扫描 | 定时 (每 30 分钟) |
| gitea_sync | Gitea 仓库同步 | 检验合格后触发 |
| backup_db | 数据库备份 | 定时 (每日凌晨 2:00) |
| backup_files | 文件备份 | 定时 (每日凌晨 3:00) |
| backup_gitea | 代码仓库归档 | 定时 (每日凌晨 4:00) |

---

## 6. Agent 蜂群服务

### 6.1 职责概述

Agent 蜂群服务负责管理编程 Agent 集群的建立、调度和成果收集。蜂群由后发（HouFa，代码编写）或后达（HouDa，代码测试）建立和管理：

- **后发建立**: 第七步（TDD 测试用例编写）和第九步（功能代码编写）
- **后达建立**: 第十一步（全面测试）

### 6.2 蜂群生命周期

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

### 6.3 技能匹配

| 任务类型 | 技能组合 | 优先 Agent 类型 |
|---|---|---|
| TDD 测试用例编写 | tdd_test + code_review | Claude Code, Codex |
| 功能代码编写 | code_generation + code_review | Opencode, Cursor, Claude Code, CodeArts, Trae, Lingma |
| 测试用例编写 | test_creation + code_review | Claude Code, Codex |
| 环境部署 | deployment + code_generation | Cursor, CodeArts |
| 集成测试 | test_creation + debugging | Claude Code, Trae |

### 6.4 蜂群通信接口

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

### 6.5 负载均衡

- 根据 Agent 当前负载和技能匹配度动态调整任务分配
- 负载计算公式: `负载 = 活跃任务数 × 任务复杂度系数 / 最大并发数`
- 任务分配优先级: 技能匹配度 > 当前负载 > 响应时间

### 6.6 蜂群 Agent 工作目录

- 使用持久化卷存储蜂群 Agent 的临时工作目录，路径为 `/data/devflow/swarms/{project_id}/`
- 容器重启后数据不会丢失，确保跨重启周期的任务状态可恢复
- 在 Docker Compose 中挂载为 named volume: `swarm_data:/data/devflow/swarms`

---

## 7. 项目讨论群服务

### 7.1 职责概述

项目讨论群服务提供 Agent 间实时沟通与协作的核心渠道。第二步执行时自动创建群组，所有 9 个命名 Agent 角色自动加入。支持两种工作模式：

- **讨论模式 (discussion)**: 自由发言，@mention 定向沟通
- **会议模式 (meeting)**: 结构化议程，主持人控场

### 7.2 群组自动创建

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

    def _get_agent_id(self, agent_name: str) -> int:
        """根据 Agent 名称获取 Agent ID（异步版本见下方）"""
        # 同步查找：从已加载的 agents 缓存中获取
        raise NotImplementedError("使用 async 版本的 _get_agent_id_async")

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

### 7.3 讨论模式

- 人类用户或 Agent 可随时在群组中发送消息
- 支持 `@Agent名称` 定向提及特定 Agent
- **自动回复机制**:
  1. 检测消息中的 @mention
  2. 确定目标回复 Agent
  3. 获取最近消息作为上下文
  4. 调用 Gateway API 获取各 Agent 的响应
  5. 流式输出响应内容到前端（通过 WebSocket）
- 消息持久化到 `group_messages` 表，支持历史查询

### 7.4 会议模式

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

## 8. QA 门控服务

### 8.1 职责概述

QA 门控服务由后荣（HouRong）负责，是流程中每步的质量控制节点。核心原则：

- 每步产出必须经后荣检验合格方可进入下一步（第一步除外）
- 检验合格：放行 → 产出提交到代码库 → 通知海梅进入下一步
- 检验不合格：退回重做 → 附带修改建议 → Agent 必须在 24 小时内修改重新提交

### 8.2 检验流程

```
Agent 提交产出 → QA 门控服务接收 → 调用后荣 Agent 执行检验
    → 后荣按验收标准逐项比对
    → 检验结果: 合格 or 不合格
    → 合格: 提交代码库, 通知海梅推进流程
    → 不合格: 退回重做, 发送修改建议, 设置 24 小时期限
```

### 8.3 检验维度与量化打分

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

### 8.4 QA 检验记录

每次检验记录保存到 `qa_records` 表，包含：

- `review_dimensions`: JSON 数组，存储各维度的名称、量化标准、实际得分、合格阈值、是否达标
- `score`: 综合评分（0-100）
- `acceptance_result`: pass / fail
- `problem_details`: 不合格时的详细修改建议

### 8.5 退回重做机制

- 检验不合格时，QA 服务将检验报告发送给对应 Agent
- 设定 24 小时规定时限
- 超时未完成修改，触发海梅介入处理
- 每次检验记录完整保存，支持追溯

---

## 9. 代码仓库集成服务

### 9.1 职责概述

代码仓库集成服务负责与 Gitea 的对接，实现检验合格产出的自动提交。Gitea 作为所有 Agent 共享的成果存储中心。

### 9.2 仓库自动创建

项目创建时（第一步），服务自动在 Gitea 中创建项目代码仓库：

1. 根据项目名称生成仓库名称
2. 在配置的默认组织下创建仓库
3. 设置仓库为私有
4. 初始化仓库（README.md、.gitignore、LICENSE 等）
5. 设置默认分支为 `main`
6. 配置分支保护规则

### 9.3 分支管理（Git Flow）

| 分支 | 说明 | 保护规则 |
|---|---|---|
| main | 生产分支 | 仅通过 PR 合并，严格保护 |
| develop | 开发分支 | 仅通过 PR 合并 |
| feature/* | 功能开发分支 | 无保护 |
| release/* | 发布准备分支 | 仅通过 PR 合并 |
| hotfix/* | 紧急修复分支 | 仅通过 PR 合并 |

### 9.4 提交规范

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

### 9.5 提交时机与规则

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

### 9.6 Pull Request 流程

所有代码合并必须通过 Pull Request 流程：

1. 创建分支 → 2. 开发编码 → 3. 推送远程 → 4. 创建 PR → 5. 代码审查 → 6. 自动化测试 → 7. 审批通过 → 8. 合并 → 9. 删除源分支

### 9.7 Gitea API 客户端

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
        """创建 Pull Request

        通过 Gitea Pull Requests API 创建 PR，
        设置标题、描述、源分支和目标分支。

        返回: PR 信息字典 (包含 number、url、html_url 等)
        """
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

## 10. 通知服务

### 10.1 职责概述

通知服务负责在关键节点向人类用户推送通知。通知方式：平台内消息（WebSocket 推送）+ 邮件（可选配置）。

### 10.2 通知类型

| 类型 | 触发时机 |
|---|---|
| step_complete | 流程步骤完成 |
| qa_pass | QA 检验通过 |
| qa_fail | QA 检验未通过 |
| task_assigned | 任务分配 |
| task_completed | 任务完成 |
| project_complete | 项目完成 |
| system_alert | 系统告警 |

### 10.3 通知节点

- 需求确认完成
- 设计完成
- 测试用例完成
- 代码编写完成
- 测试完成
- 安全审计完成
- 部署完成

### 10.4 通知机制

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

## 11. WebSocket 实时通信

### 11.1 职责概述

WebSocket 服务提供实时双向通信能力，支撑以下场景：

- 群聊消息实时推送（讨论模式 + 会议模式）
- 16 步流程进展事件推送
- Agent 流式响应输出
- 通知实时推送
- 蜂群执行进度实时更新

### 11.2 WebSocket 端点

| 端点 | 用途 |
|---|---|
| ws://host/ws/group-chat | 群聊实时通信 |
| ws://host/ws/notifications | 通知推送 |
| ws://host/ws/workflow/:project_id | 流程状态推送 |

### 11.3 群聊 WebSocket 协议

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

### 11.4 连接管理

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

### 11.5 断线重连

- WebSocket 断线后前端自动重连
- 重连后自动恢复群组订阅
- 支持断线期间的消息补发（基于消息 ID 去重）

---

## 12. 错误处理

### 12.1 统一异常处理

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

错误码冲突修复说明：V13 中 `QAFailError` 和 `WorkflowError` 均使用 HTTP 422 状态码，前端无法通过 HTTP 状态码区分"前置条件未满足"和"QA 检验不合格"两种场景。V14 将 `QAFailError` 的 HTTP 状态码改为 406 (Not Acceptable)，语义上表示"产出不符合验收标准"，与 `WorkflowError` 的 422 (Unprocessable Entity，表示前置条件未满足) 明确区分。两者在响应体的 `code` 字段中也使用不同的业务错误码。

命名说明：原 `TimeoutError` 与 Python 内置异常 `builtins.TimeoutError` 同名，已更名为 `AgentTimeoutError`，避免命名空间冲突和混淆。

### 12.2 错误码表

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

错误码使用说明：HTTP 406 (Not Acceptable) 专用于 QA 检验不合格场景，HTTP 422 (Unprocessable Entity) 专用于流程前置条件未满足场景。前端可通过 HTTP 状态码明确区分两种业务场景，响应体的 `code` 字段进一步标识具体业务错误类型。

### 12.3 关键流程容错

- 关键流程失败时提供明确错误提示和人工介入入口
- Agent 执行失败时，海梅自动重试（最多 3 次，指数退避：30s/60s/120s）
- 3 次重试均失败后，切换备用 Agent 执行
- 备用 Agent 不可用时，通知人类用户并暂停任务
- 所有容错操作记录到 `agent_execution_logs` 表

---

## 13. 安全设计

### 13.1 认证与授权

- **认证方式**: JWT Token 认证
  - Access Token: 有效期 15 分钟
  - Refresh Token: 有效期 7 天
  - Token 签发算法: RS256（非对称算法）
  - 私钥用于签发 Token，公钥用于验证 Token，多服务部署时无需共享密钥
  - 私钥存储在 `.env` 文件的 `JWT_PRIVATE_KEY` 配置项中，公钥存储在 `JWT_PUBLIC_KEY` 配置项中
- **Token 吊销机制**:
  - 用户登出或密码变更后，将 Access Token 的 JTI (JWT ID) 加入 Redis 黑名单
  - 黑名单键格式: `token:blacklist:{jti}`，过期时间与 Token 剩余有效期一致
  - 每次验证 Token 时检查 Redis 黑名单，若存在则拒绝访问
  - Refresh Token 采用轮换机制：每次使用 Refresh Token 获取新的 Access Token 时，旧的 Refresh Token 立即失效，新签发一对 Token
- **授权控制**: 基于角色的访问控制 (RBAC)
  - 人类用户: 仅可查看/操作自身发起的项目
  - 系统管理员: 可管理所有项目、Agent 配置、系统设置

### 13.2 数据安全

- **传输加密**: HTTPS 传输加密
- **密码存储**: bcrypt 哈希存储
- **Agent 交互数据**: 脱敏存储，敏感信息不记录到日志
- **项目成果安全**: 代码/成果仅对人类用户和授权 Agent 可见

### 13.3 API 安全

- **速率限制**: 每个用户每秒最多 100 次 API 请求
- **CORS**: 仅允许配置的前端域名
- **请求体大小限制**: 默认 10MB
- **输入验证**: 所有输入通过 Pydantic 模型验证
- **SQL 注入防护**: SQLAlchemy ORM 参数化查询

### 13.4 审计日志

记录所有关键操作：

- Agent 任务分派
- QA 检验结果
- 代码提交
- 错误和异常
- 用户登录/登出
- 配置变更

### 13.5 多用户资源隔离

- **项目级别隔离**: 每个项目的 Agent 执行在独立的会话空间中运行
- **Agent 并发限制**: 同一 Agent Profile 同一时间只能执行一个项目的任务。GatewayClient 通过 `_profile_locks` 字典为每个 profile 维护独立的 `asyncio.Semaphore(1)` 互斥锁，在 `send_message` 方法中先获取总信号量再获取 profile 级互斥锁，确保多项目并发时同一 agent 不会被分派多个任务
- **蜂群 Agent 隔离**: 不同项目的蜂群 Agent 使用独立的持久化工作目录 (`/data/devflow/swarms/{project_id}/`)，挂载为 Docker named volume 确保容器重启后数据不丢失
- **数据库隔离**: 通过 project_id 字段实现逻辑隔离，用户只能访问自己发起的项目数据

---

## 14. 日志与监控

### 14.1 日志管理

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

### 14.2 指标采集 (Metrics)

使用 Prometheus 时序数据库，指标保留 30 天：

| 指标类别 | 指标 | 采集间隔 |
|---|---|---|
| 系统级 | CPU 使用率、内存使用率、磁盘 IO、网络带宽 | 30 秒 |
| 应用级 | API 响应时间 P50/P95/P99、QPS、错误率、活跃连接数 | 10 秒 |
| Agent 级 | 任务执行时长、任务成功率、Agent 负载、蜂群 Agent 活跃度 | 30 秒 |
| 业务级 | 项目数、活跃项目数、QA 检验通过率、各步骤平均耗时 | 实时统计 |

### 14.3 链路追踪 (Tracing)

- 采用 OpenTelemetry 标准
- 为每个 Agent 任务分配唯一 Trace ID
- 追踪范围：从海梅分派任务开始，经过蜂群 Agent 执行、QA 检验、代码提交的全链路
- 存储：Jaeger 后端，保留 7 天

### 14.4 告警规则

| 告警级别 | 条件 | 通知方式 |
|---|---|---|
| 系统级 | CPU >85% 持续 5 分钟、内存 >90% 持续 3 分钟、磁盘 >80% | WebSocket + 邮件 |
| 应用级 | API 错误率 >5%、P95 响应时间 >5 秒、连续 10 个 Agent 任务失败 | WebSocket + 邮件 |
| Agent 级 | Agent 进程宕机、连续 3 次重试失败、单个任务执行超过 30 分钟 | WebSocket + 邮件 |

**告警升级**: 首次告警通知系统管理员，30 分钟内未处理则通知项目人类用户。

---

## 15. 配置管理

### 15.1 配置项

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

    class Config:
        env_file = ".env"
```

---

## 16. 部署架构

### 16.1 Docker 部署

```yaml
# docker-compose.yml
version: "3.8"

services:
  # DevFlow 后端 (FastAPI 主服务)
  devflow:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://devflow:***@postgres:5432/devflow_db
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - postgres
      - redis
    volumes:
      ### 16.1 Docker 部署

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
            - DATABASE_URL=postgresql://devflow:devflow_password@postgres:5432/devflow_db
            - REDIS_URL=redis://redis:6379
            - CELERY_BROKER_URL=redis://redis:6379/1
            - CELERY_RESULT_BACKEND=redis://redis:6379/2
          depends_on:
            - postgres
            - redis
          volumes:
            - swarm_data:/data/devflow/swarms

        # Celery Worker (处理所有异步任务)
        celery-worker:
          build: .
          command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
          environment:
            - DATABASE_URL=postgresql://devflow:devflow_password@postgres:5432/devflow_db
            - REDIS_URL=redis://redis:6379
            - CELERY_BROKER_URL=redis://redis:6379/1
            - CELERY_RESULT_BACKEND=redis://redis:6379/2
          depends_on:
            - postgres
            - redis
          volumes:
            - swarm_data:/data/devflow/swarms

        # Celery Beat (定时调度器)
        celery-beat:
          build: .
          command: celery -A app.tasks.celery_app beat --loglevel=info
          environment:
            - DATABASE_URL=postgresql://devflow:devflow_password@postgres:5432/devflow_db
            - REDIS_URL=redis://redis:6379
            - CELERY_BROKER_URL=redis://redis:6379/1
            - CELERY_RESULT_BACKEND=redis://redis:6379/2
          depends_on:
            - postgres
            - redis
            - celery-worker

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
        wal_archive:
      ```

      Docker 部署修复说明
1. **celery-worker** 服务：独立容器运行 Celery Worker，处理所有异步任务（Agent 执行、蜂群调度、QA 检验、Gitea 同步等），配置 4 个并发 worker 进程
2. **celery-beat** 服务：独立容器运行 Celery Beat 定时调度器，负责定时任务（Profile 扫描每 30 分钟、数据库备份每日凌晨 2:00、文件备份每日凌晨 3:00、代码仓库归档每日凌晨 4:00）
3. 三个服务共享相同的 Redis broker/backend 配置和数据库连接，celery-worker 和 celery-beat 依赖 devflow 服务以确保应用代码已就绪
4. swarm_data 卷同时挂载到 devflow 和 celery-worker，确保蜂群 Agent 工作目录在异步任务执行中可访问

### 16.2 9 个命名 Agent 部署

每个命名 Agent 独立部署为 Hermes Agent Profile 实例：

- 独立进程、独立配置文件、独立 Gateway 端口
- 端口范围: 8765-8773
- Profile 存储路径: `~/.hermes/profiles/{profile_name}/`
- 各 Agent 进程独立启动、独立运行、独立停止，互不影响

---

## 17. 数据迁移与版本升级

### 17.1 数据迁移

- 使用 Alembic 管理数据库迁移
- 支持正向迁移和回滚
- 流程: 备份当前数据 → 在测试环境执行迁移脚本验证 → 迁移通过后在生产环境执行 → 验证数据完整性 → 保留旧版本数据 7 天以备回滚
- 每次迁移记录迁移 ID、执行时间、执行结果、影响数据量

### 17.2 版本升级

- 语义化版本控制 (MAJOR.MINOR.PATCH)
- MINOR 版本升级保证 API 向后兼容
- 升级流程: 发布升级公告 → 用户备份数据 → Docker 镜像更新 → 自动执行数据库迁移 → 健康检查验证 → 失败自动回滚
- 保留最近 3 个版本的 Docker 镜像标签，支持一键回滚

---

## 18. 容灾恢复与备份

### 18.1 恢复目标

- **RTO**: 系统故障后 2 小时内恢复服务
- **RPO**: 数据丢失不超过最后一小时内

### 18.2 备份策略

采用全量备份 + PostgreSQL WAL 归档策略以满足 RPO ≤ 1 小时的要求：

| 备份对象 | 频率 | 保留周期 |
|---|---|---|
| 数据库全量 (pg_basebackup) | 每日凌晨 2:00 | 30 天 |
| PostgreSQL WAL 归档 | 持续归档 (每 5 分钟切换) | 30 天 |
| 文件存储全量 | 每日凌晨 3:00 | 30 天 |
| 代码仓库归档 | 每日凌晨 4:00 | 30 天 |
| 每周备份 (周日凌晨) | 每周 | 90 天 |
| 每月备份 (每月 1 日) | 每月 | 365 天 |

备份策略说明：
- 全量备份使用 `pg_basebackup` 在每日凌晨 2:00 执行
- 启用 PostgreSQL WAL 归档 (`wal_level=replica`, `archive_mode=on`)，WAL 段文件持续归档到 `wal_archive` 持久化卷
- 恢复时可基于全量备份 + WAL 归档恢复到任意时间点 (PITR)，确保 RPO ≤ 1 小时
- 文件存储通过归档压缩，Gitea 仓库通过 `git bundle` 归档
- 每周和每月备份为全量备份的长期保留副本，用于满足不同周期的恢复需求

### 18.3 恢复演练

- 每季度进行一次完整恢复演练
- 步骤: 恢复数据库 → 恢复文件存储 → 恢复 Gitea 仓库 → 验证应用功能 → 记录恢复时间和数据完整性

---

## 19. V14 修订记录

本节记录 V13 到 V14 的修订内容，对应后荣检验报告中的 7 项不合格项：

| 序号 | 严重级别 | 问题描述 | 修复方案 |
|---|---|---|---|
| 1 | 严重 | docker-compose.yml 缺少 Celery Worker 服务 | 16.1 节补充 celery-worker 和 celery-beat 服务容器配置，共享 Redis broker/backend 和数据库连接 |
| 2 | 中等 | ProfileScanner._check_gateway() 每次创建新的 httpx.AsyncClient | 4.6 节改为调用 GatewayClient._get_http_client() 复用连接池 |
| 3 | 中等 | WorkflowStep.assignee_agent 使用硬编码字典映射 | 5.2 节改为从 workflow_steps 数据库配置表动态读取，支持运行时调整 |
| 4 | 中等 | QAFailError 和 WorkflowError 均使用 HTTP 422 | 12.1 节将 QAFailError 改为 HTTP 406 (Not Acceptable)，12.2 节更新错误码表 |
| 5 | 轻微 | POST /api/v1/repos/validate-commit 缺少 :repo_id 参数 | 2.11 节改为 POST /api/v1/repos/:repo_id/validate-commit |
| 6 | 轻微 | get_ready_tasks() 使用 Redis KEYS 命令 O(N) 复杂度 | 5.4 节改用 SCAN + 维护独立的 ready_set 集合，get_ready_tasks() 降至 O(1) |
| 7 | 轻微 | POST /api/v1/agents/sync-hermes 路由模块边界不清 | 2.6 节移除该端点，2.10 节新增 POST /api/v1/hermes/sync-profiles |

**文档结束**
