# DevFlow 项目管理平台 - 后端设计文档

**版本**: V6
**日期**: 2026-06-15
**作者**: HouWang (后旺)
**状态**: 修订版V6（修复V5审查不合格项）

---

## 1. 后端技术栈

### 1.1 核心技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11 | 编程语言 |
| FastAPI | 0.100+ | Web 框架，REST API + WebSocket |
| asyncio | 3.11 | 异步并发控制 |
| SQLAlchemy | 2.x | ORM 框架 |
| Pydantic | 2.x | 数据验证和序列化 |
| Celery | 5.x | 异步任务队列 |
| Redis | 6.x | 缓存、消息队列、状态存储 |
| PostgreSQL | 14+ | 主数据库 |
| Alembic | 1.x | 数据库迁移工具 |

### 1.2 辅助库

| 库 | 用途 |
|----|------|
| httpx | HTTP 客户端（异步） |
| websockets | WebSocket 支持 |
| pyjwt | JWT Token 处理 |
| passlib | 密码哈希 |
| python-multipart | 文件上传 |
| uvicorn | ASGI 服务器 |
| prometheus-client | Prometheus 指标导出 |
| opentelemetry | 链路追踪 |
| structlog | 结构化日志 |
| gunicorn | 生产环境进程管理 |

---

## 2. 项目目录结构

```
devflow-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── config.py                  # 配置管理
│   ├── database.py                # 数据库连接
│   ├── models/                    # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── step.py               # 步骤模型（含Step、StepStatus）
│   │   ├── group.py
│   │   ├── swarm.py              # 蜂群模型（含SwarmStatus枚举）
│   │   ├── qa.py
│   │   ├── repo.py
│   │   └── notification.py       # 通知模型
│   ├── schemas/                   # Pydantic 模式
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── group.py
│   │   ├── swarm.py
│   │   └── qa.py
│   ├── api/                       # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py               # 认证接口
│   │   ├── projects.py           # 项目管理接口
│   │   ├── agents.py             # Agent管理接口
│   │   ├── swarms.py             # 蜂群管理接口
│   │   ├── groups.py             # 群组管理接口
│   │   ├── qa.py                 # QA门控接口
│   │   ├── repos.py              # 代码库接口
│   │   └── hermes.py             # Hermes通信接口
│   ├── services/                  # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── project_service.py
│   │   ├── agent_service.py
│   │   ├── swarm_service.py
│   │   ├── group_service.py
│   │   ├── qa_service.py
│   │   ├── repo_service.py
│   │   └── hermes_service.py
│   ├── workers/                   # Celery 异步任务
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── task_scheduler.py
│   │   ├── profile_scanner.py
│   │   └── notification_worker.py
│   ├── middleware/                # 中间件
│   │   ├── __init__.py
│   │   ├── auth.py               # 认证中间件
│   │   ├── rate_limiter.py       # 限流中间件
│   │   ├── logging.py            # 日志中间件
│   │   └── cors.py               # CORS中间件
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── jwt.py                # JWT工具
│   │   ├── password.py           # 密码处理
│   │   ├── websocket.py          # WebSocket管理
│   │   └── gitea.py              # Gitea API客户端
│   └── tests/                     # 测试文件
│       ├── __init__.py
│       ├── conftest.py
│       └── test_*.py
├── migrations/                    # Alembic 迁移脚本
├── docker-compose.yml             # Docker编排
├── Dockerfile                     # Docker镜像
├── requirements.txt               # Python依赖
├── .env                           # 环境变量
└── README.md
```

**说明**:
- `models/step.py` 定义 Step 模型及其枚举 StepStatus，用于16步流程中的步骤状态追踪。
- `models/notification.py` 定义 Notification 模型，用于系统通知和消息推送。
- `models/swarm.py` 除了 Swarm 模型外，还定义 SwarmStatus 枚举（ACTIVE, COMPLETED, FAILED, DISSOLVED），供蜂群管理和 AgentService 使用。

---

## 3. API接口列表

### 3.1 用户认证接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/v1/auth/login | 用户登录 | 无 |
| POST | /api/v1/auth/register | 用户注册 | 无 |
| POST | /api/v1/auth/refresh | 刷新Token | Token |
| GET | /api/v1/auth/profile | 获取用户信息 | Token |

### 3.2 项目管理接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/v1/projects | 创建项目（含 Step 1 初始化） | Token |
| GET | /api/v1/projects | 获取项目列表（支持分页: ?limit=20&offset=0） | Token |
| GET | /api/v1/projects/:id | 获取项目详情 | Token |
| GET | /api/v1/projects/:id/progress | 获取项目进度 | Token |
| POST | /api/v1/projects/:id/complete | 确认项目完成 | Token |

### 3.3 16步流程调度接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /api/v1/projects/:id/steps | 获取项目所有步骤列表 | Token |
| GET | /api/v1/projects/:id/steps/:step_number | 获取指定步骤详情 | Token |
| POST | /api/v1/projects/:id/steps/execute | 执行指定步骤（统一入口） | Token |

**说明**:
- Step 1（项目初始化）包含在 `POST /api/v1/projects` 创建项目接口中：创建项目记录、初始化 Gitea 仓库、设置 current_step=1
- Step 2-16 通过统一的 `POST /api/v1/projects/:id/steps/execute` 接口触发，请求体包含 `step_number` 和 `step_data`
- 这种设计避免了为每个步骤硬编码独立 endpoint，支持跳过步骤、批量执行、动态扩展
- 请求体示例: `{"step_number": 3, "step_data": {...}}`

### 3.4 Agent管理接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /api/v1/agents | 获取Agent列表（支持分页: ?limit=20&offset=0） | Token |
| GET | /api/v1/agents/:id | 获取Agent详情 | Token |
| POST | /api/v1/agents/register | Agent注册 | Token |
| DELETE | /api/v1/agents/:id | 移除Agent | Token |
| GET | /api/v1/profiles | 获取Hermes Profiles | Token |
| POST | /api/v1/agents/sync-hermes | 同步Hermes Profiles | Token |

### 3.5 Agent蜂群接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/v1/swarms | 创建蜂群 | Token |
| GET | /api/v1/swarms/:id | 获取蜂群详情 | Token |
| POST | /api/v1/swarms/:id/dispatch | 分发任务到蜂群 | Token |
| GET | /api/v1/swarms/:id/progress | 获取蜂群进度 | Token |
| DELETE | /api/v1/swarms/:id | 解散蜂群 | Token |
| GET | /api/v1/swarms/tasks/:agent_id | 蜂群Agent获取任务 | Token |
| POST | /api/v1/swarms/tasks/:agent_id/acknowledge | 确认接收任务 | Token |
| POST | /api/v1/swarms/tasks/:task_id/progress | 上报任务进度 | Token |
| POST | /api/v1/swarms/tasks/:task_id/deliver | 提交任务成果 | Token |
| POST | /api/v1/swarms/tasks/:task_id/error | 上报执行错误 | Token |

### 3.6 QA门控接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/v1/qa/:task_id/inspect | 执行QA检验 | Token |
| GET | /api/v1/qa/:project_id/records | 获取QA记录（支持分页: ?limit=20&offset=0） | Token |
| POST | /api/v1/qa/:task_id/rollback | 退回重做 | Token |
| GET | /api/v1/qa/:task_id/status | 获取检验状态 | Token |

### 3.7 项目讨论群接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /api/v1/groups | 获取群组列表（支持分页: ?limit=20&offset=0） | Token |
| POST | /api/v1/groups | 创建群组 | Token |
| GET | /api/v1/groups/:id | 获取群组详情 | Token |
| POST | /api/v1/groups/:id/members | 添加成员 | Token |
| DELETE | /api/v1/groups/:id/members/:agent_id | 移除成员 | Token |
| GET | /api/v1/groups/:id/messages | 获取消息列表（支持分页: ?limit=50&offset=0） | Token |
| GET | /api/v1/groups/:id/outcomes | 获取会议结果 | Token |
| POST | /api/v1/groups/:id/host | 设置主持人 | Token |

### 3.8 WebSocket端点

| 端点 | 描述 |
|------|------|
| ws://{host}/ws/group-chat | 群聊WebSocket连接 |
| ws://{host}/ws/notifications | 通知WebSocket连接 |
| ws://{host}/ws/project/:id | 项目进度WebSocket连接 |

### 3.9 健康检查端点

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /health | 基础存活检查 (liveness probe) | 无 |
| GET | /ready | 就绪检查 (readiness probe: 检查DB、Redis连接) | 无 |

**说明**:
- `/health` 直接返回 200，不打开任何数据库或Redis连接，仅表示进程存活，用于 Kubernetes/容器编排的 liveness probe
- `/ready` 复用应用启动时创建的数据库引擎和Redis连接池进行ping检测，不创建新连接，返回 200 表示服务就绪，用于 readiness probe
- 这两个端点不需要认证，供容器编排系统调用

**实现代码**:

```python
from fastapi import APIRouter, HTTPException
from app.database import engine, redis_pool  # 应用启动时创建的引擎和连接池

router = APIRouter()

@router.get("/health")
async def health_check():
    """基础存活检查 - 仅返回进程存活状态，不打开任何连接"""
    return {"status": "alive"}

@router.get("/ready")
async def readiness_check():
    """就绪检查 - 复用已有的数据库引擎和Redis连接池进行ping检测"""
    checks = {}

    # 检查数据库连接（使用应用启动时创建的引擎，异步执行）
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.database import async_session_factory
        async with async_session_factory() as session:
            await session.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # 检查Redis连接（复用应用启动时创建的Redis连接池）
    try:
        await redis_pool.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    all_ok = all(v == "ok" for v in checks.values())

    if all_ok:
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks}
        )
```

**说明**:
- `/health` 不打开任何连接，直接返回进程存活状态。
- `/ready` 使用 `async_session_factory` 创建异步Session进行数据库ping检测，使用 `redis_pool`（应用启动时初始化并缓存在 `app.database` 模块中的Redis连接池）进行Redis ping检测，避免了每次请求创建和销毁连接。
- `engine` 和 `redis_pool` 在 `app/main.py` 的 `@app.on_event("startup")` 中初始化，确保连接复用。

---

## 4. 数据流设计

### 4.1 请求处理流程

```
客户端请求
    │
    ▼
Nginx (反向代理)
    │
    ▼
FastAPI 应用
    │
    ├── 中间件链
    │   ├── CORS 中间件
    │   ├── 认证中间件
    │   ├── 限流中间件
    │   └── 日志中间件
    │
    ├── 路由分发
    │   ├── 验证请求参数 (Pydantic)
    │   ├── 检查权限
    │   └── 调用对应API处理器
    │
    ├── 业务逻辑服务
    │   ├── 验证业务规则
    │   ├── 调用数据库操作
    │   ├── 调用外部服务
    │   └── 返回处理结果
    │
    └── 响应处理
        ├── 序列化响应数据
        ├── 添加响应头
        └── 返回JSON响应
```

### 4.2 异步任务流程

```
API 请求触发异步任务
    │
    ▼
Celery 任务队列 (Redis)
    │
    ├── 任务类型
    │   ├── 16步流程执行任务
    │   ├── Agent蜂群调度任务
    │   ├── QA检验任务
    │   ├── Profile扫描任务
    │   └── 通知发送任务
    │
    ▼
Celery Worker 执行
    │
    ├── 任务执行
    │   ├── 加载任务参数
    │   ├── 执行业务逻辑
    │   ├── 更新数据库状态
    │   └── 记录执行日志
    │
    └── 任务完成
        ├── 更新任务状态
        ├── 触发后续任务
        └── 发送完成通知
```

### 4.3 WebSocket消息流

```
客户端连接 WebSocket
    │
    ▼
Connection Manager (连接管理器)
    │
    ├── 建立连接
    │   ├── 验证用户身份
    │   ├── 注册连接到管理器
    │   └── 订阅相关事件
    │
    ├── 消息处理
    │   ├── 接收客户端消息
    │   ├── 解析消息类型
    │   ├── 调用对应处理器
    │   └── 返回处理结果
    │
    ├── 消息推送
    │   ├── 项目进度更新
    │   ├── 新消息到达
    │   ├── Agent状态变更
    │   └── 通知推送
    │
    └── 连接关闭
        ├── 清理连接资源
        ├── 取消事件订阅
        └── 记录断开日志
```

---

## 5. 中间件设计

### 5.1 认证中间件 (auth.py)

```python
from fastapi import Request, HTTPException
from app.utils.jwt import decode_token

async def auth_middleware(request: Request, call_next):
    # 跳过公开路径
    if request.url.path in ['/api/v1/auth/login', '/api/v1/auth/register', '/health', '/ready']:
        return await call_next(request)

    # 直接从请求头提取Bearer token
    auth_header = request.headers.get('authorization', '')
    if not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing authentication token")

    token = auth_header[7:]
    try:
        payload = decode_token(token)
        request.state.user = payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    response = await call_next(request)
    return response
```

**说明**: HTTPBearer 是 SecurityScheme 而非可调用的 async 函数，因此改为直接从 request.headers 提取 Bearer token。公开路径包含 `/health` 和 `/ready` 以支持容器编排的健康检查。

### 5.2 限流中间件 (rate_limiter.py)

```python
from fastapi import Request, HTTPException
from redis.asyncio import Redis
import time

class RateLimiter:
    def __init__(self, redis: Redis, max_requests: int = 100, window_seconds: int = 60):
        self.redis = redis
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = request.client.host

        # 从JWT token解码提取user_id
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.utils.jwt import decode_token
                token_payload = decode_token(auth_header[7:])
                user_id = token_payload.get('user_id')
            except Exception:
                pass

        # 构建限流键：已认证用户使用 IP+user_id，未认证用户仅使用IP
        if user_id:
            key = f"rate_limit:{client_ip}:user:{user_id}"
        else:
            key = f"rate_limit:{client_ip}"

        # 检查请求次数
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # 清理过期记录
        await self.redis.zremrangebyscore(key, 0, window_start)

        # 获取当前窗口内请求数
        request_count = await self.redis.zcard(key)

        if request_count >= self.max_requests:
            raise HTTPException(status_code=429, detail="Too many requests")

        # 记录当前请求
        await self.redis.zadd(key, {str(current_time): current_time})
        await self.redis.expire(key, self.window_seconds)

        response = await call_next(request)
        return response

**说明**: 已认证用户使用 IP+user_id 组合作为限流键（从JWT token解码提取），避免使用完整token字符串导致key过长，同时防止Token轮换导致同一用户被重新限流。未认证用户仍使用IP限流。
```

### 5.3 日志中间件 (logging.py)

```python
import time
import structlog
from fastapi import Request

logger = structlog.get_logger()

async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    # 记录请求开始
    logger.info("request.start",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host)

    # 执行请求
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time

    # 记录请求完成
    logger.info("request.complete",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=process_time)

    return response
```

---

## 6. 安全策略

### 6.1 认证策略

- JWT Token 认证
- Token 有效期：2小时
- Refresh Token 有效期：7天
- Token 刷新机制
- 密码使用 bcrypt 哈希存储

### 6.2 授权策略 (RBAC)

- RBAC 基于角色的访问控制
- 用户角色：user, admin, system_admin
- 使用 FastAPI Depends() 实现权限校验

```python
from fastapi import Depends, HTTPException, Request
from typing import Literal

class CurrentUser:
    def __init__(self, user_id: int, role: str, username: str):
        self.user_id = user_id
        self.role = role
        self.username = username

async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI 依赖注入方式获取当前用户"""
    user_data = getattr(request.state, 'user', None)
    if not user_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return CurrentUser(
        user_id=user_data['user_id'],
        role=user_data['role'],
        username=user_data['username']
    )

def require_role(*allowed_roles: str):
    """生成角色校验依赖函数"""
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# 使用示例:
# @router.get("/admin/resource")
# async def admin_endpoint(user: CurrentUser = Depends(require_role('admin', 'system_admin'))):
#     return {"message": "Admin resource"}
```

**说明**: 使用 FastAPI 原生的 Depends() 依赖注入机制替代装饰器方案，确保与 FastAPI 的请求处理流程兼容，能够正确获取 request.state.user。

### 6.3 数据加密

- HTTPS 传输加密
- 敏感字段加密存储
- API 密钥加密存储
- 日志脱敏处理

### 6.4 CORS策略

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS.split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 6.5 输入验证

- Pydantic 模式验证所有输入
- SQL 注入防护（使用 ORM）
- XSS 防护（输出转义）
- 文件上传类型和大小限制

---

## 7. 服务层设计

### 7.1 项目服务 (project_service.py)

```python
from sqlalchemy.orm import Session
from typing import List
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.agent import AgentResponse
from app.models.project import Project, ProjectStatus
from app.models.step import Step
from app.models.user import User
from app.models.agent import Agent

# 依赖注入容器
class ServiceContainer:
    """服务层依赖注入容器"""
    def __init__(self, db: Session):
        self.db = db
        self.repo_service = None
        self.agent_service = None

    def inject(self, **services):
        for name, service in services.items():
            setattr(self, name, service)

class ProjectService:
    """项目服务 - 使用依赖注入模式"""

    def __init__(self, db: Session, repo_service=None, agent_service=None, project_folder_service=None):
        self.db = db
        self.repo_service = repo_service or RepoService(db)
        self.agent_service = agent_service or AgentService(db)
        self.project_folder_service = project_folder_service or ProjectFolderService()

    def create_project(self, user_id: int, project_data: ProjectCreate) -> Project:
        # 创建项目记录
        project = Project(
            name=project_data.name,
            description=project_data.description,
            creator_id=user_id,
            status=ProjectStatus.CREATED,
            current_step=1  # Step 1: 项目初始化
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        # 自动创建Gitea仓库 (通过注入的RepoService)
        self.repo_service.create_repo(project.id, project.name)

        # 创建项目文件夹 (通过注入的ProjectFolderService)
        self.project_folder_service.create_project_folder(project.id)

        return project

    def get_project_progress(self, project_id: int) -> dict:
        project = self.get_project(project_id)
        steps = self.db.query(Step).filter(Step.project_id == project_id).all()

        return {
            "project": project,
            "current_step": project.current_step,
            "steps": steps,
            "progress_percent": (project.current_step / 16) * 100
        }

    async def execute_step(self, project_id: int, step_number: int, step_data: dict = None) -> Project:
        """统一步骤执行入口 - 支持跳过步骤、批量执行、动态扩展"""
        project = self.get_project(project_id)

        # 验证步骤号范围（不强制严格顺序，允许跳过）
        if step_number < 1 or step_number > 16:
            raise ValueError(f"Step number must be between 1 and 16, got {step_number}")

        result = await self.agent_service.execute_step(
            project_id=project_id,
            step_number=step_number,
            step_data=step_data or {}
        )

        # 仅在新步骤大于当前步骤时更新
        if step_number > project.current_step:
            project.current_step = step_number
        self.db.commit()
        return project

    def get_project(self, project_id: int) -> Project:
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ProjectNotFoundException(project_id)
        return project
```

**依赖注入说明**: Service 层通过构造函数参数注入依赖服务，避免内部直接实例化。实际使用时由 FastAPI 的 Depends() 或服务容器统一管理生命周期。

### 7.2 Agent服务 (agent_service.py)

```python
from sqlalchemy.orm import Session
from httpx import AsyncClient
from typing import Dict, Any, Optional

class HermesClient:
    """Hermes Gateway API 客户端 - 异步 HTTP 客户端"""

    def __init__(self, base_url: str = "http://localhost", timeout: float = None):
        self.base_url = base_url
        # Agent长任务通过Celery异步执行，HTTP超时从settings读取，默认300秒
        self.client = AsyncClient(timeout=timeout or settings.HERMES_TIMEOUT)

    async def call_agent(self, agent_name: str, prompt: str, project_id: int, model: str = None) -> dict:
        """调用指定Agent的Gateway API"""
        # 从agents表获取agent的api_endpoint
        endpoint = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model or "default",
            "messages": [{"role": "user", "content": prompt}],
            "project_id": project_id
        }
        response = await self.client.post(endpoint, json=payload)
        return response.json()

    async def dispatch_task(self, agent_name: str, task_data: dict) -> dict:
        """向Agent分发任务"""
        endpoint = f"{self.base_url}/v1/tasks/dispatch"
        payload = {"agent": agent_name, **task_data}
        response = await self.client.post(endpoint, json=payload)
        return response.json()

    async def close(self):
        await self.client.aclose()

class QAAgent:
    """QA检验Agent封装 - 调用后荣Agent执行检验"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.hermes_client = HermesClient(agent.api_endpoint)

    async def inspect(self, artifact: dict, criteria: dict) -> 'InspectionResult':
        """执行QA检验"""
        prompt = self._build_inspection_prompt(artifact, criteria)
        result = await self.hermes_client.call_agent(
            agent_name=self.agent.name,
            prompt=prompt,
            project_id=artifact.get('project_id')
        )
        return InspectionResult.from_response(result)

    def _build_inspection_prompt(self, artifact: dict, criteria: dict) -> str:
        return f"""请对以下产出物进行QA检验：
产出物: {artifact}
验收标准: {criteria}
请返回JSON格式的检验结果，包含各维度评分、问题详情、综合评分。"""

class InspectionResult:
    def __init__(self, result: str, problems: list, dimensions: list, score: float):
        self.result = result
        self.problems = problems
        self.dimensions = dimensions
        self.score = score

    @staticmethod
    def from_response(response: dict) -> 'InspectionResult':
        data = response.get('choices', [{}])[0].get('message', {}).get('content', '{}')
        import json
        parsed = json.loads(data) if isinstance(data, str) else data
        return InspectionResult(
            result=parsed.get('acceptance_result', 'fail'),
            problems=parsed.get('problems', []),
            dimensions=parsed.get('dimensions', []),
            score=parsed.get('score', 0.0)
        )

class ProjectFolderService:
    """项目文件系统管理"""

    def __init__(self, base_path: str = None):
        # 从settings读取项目存储根路径，默认 /data/projects
        self.base_path = base_path or settings.PROJECTS_BASE_PATH

    def create_project_folder(self, project_id: int) -> str:
        import os
        path = os.path.join(self.base_path, f"project_{project_id}")
        os.makedirs(path, exist_ok=True)
        # 创建标准目录结构
        for subdir in ['src', 'docs', 'tests', 'configs']:
            os.makedirs(os.path.join(path, subdir), exist_ok=True)
        return path

    def get_project_path(self, project_id: int) -> str:
        return os.path.join(self.base_path, f"project_{project_id}")

class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.hermes_client = HermesClient()

    def get_named_agents(self) -> list:
        """获取所有命名Agent"""
        return self.db.query(Agent).filter(Agent.agent_type == 'named').all()

    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """按名称获取Agent"""
        return self.db.query(Agent).filter(Agent.name == name).first()

    def get_agent_for_step(self, step_number: int) -> Optional[Agent]:
        """从数据库动态读取步骤对应的Agent
        步骤-Agent映射关系存储在数据库agents表的config JSONB字段中，
        支持运行时动态调整，无需修改代码重新部署。
        """
        # 查询agents表中config字段包含该step_number的Agent
        agent = self.db.query(Agent).filter(
            Agent.config['step_number'].as_integer() == step_number,
            Agent.agent_type == 'named'
        ).first()
        return agent

    async def execute_step(self, project_id: int, step_number: int, step_data: dict) -> dict:
        """统一步骤执行 - 根据步骤号路由到对应Agent（从数据库动态读取映射）"""
        # 从数据库动态获取该步骤对应的Agent
        agent = self.get_agent_for_step(step_number)
        if not agent:
            raise ValueError(f"No agent mapped for step {step_number}")

        # 构建任务prompt并调用Agent
        prompt = self._build_step_prompt(project_id, step_number, step_data)
        result = await self.hermes_client.call_agent(
            agent_name=agent.name,
            prompt=prompt,
            project_id=project_id
        )

        # 记录执行日志
        self.record_execution_log(project_id, agent.id, result)

        return result

    async def execute_task(self, task_id: int, agent_id: int) -> dict:
        """执行指定Agent的任务（Celery异步调用入口）"""
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # 使用execute_step执行任务关联的步骤
        result = await self.execute_step(
            project_id=task.project_id,
            step_number=task.step_number,
            step_data=task.data
        )

        # 更新任务状态
        task.status = 'completed'
        task.result = result
        self.db.commit()

        return result

    def _build_step_prompt(self, project_id: int, step_number: int, step_data: dict) -> str:
        # 步骤描述从数据库动态读取，避免硬编码
        # 存储方案：agents表config字段包含 steps_info JSONB，或在独立的step_definitions表中
        # 查询方式：从 agents 表 config['steps_info'] 读取该 step_number 的描述
        agent = self.get_agent_for_step(step_number)
        if agent and agent.config and 'steps_info' in agent.config:
            steps_info = agent.config.get('steps_info', {})
            desc = steps_info.get(str(step_number), f"执行第{step_number}步任务")
        else:
            desc = f"执行第{step_number}步任务"
        return f"项目ID: {project_id}, 步骤: {step_number}, 任务: {desc}, 参数: {step_data}"

    def create_swarm(self, project_id: int, manager_agent_id: int, purpose: str):
        swarm = Swarm(
            project_id=project_id,
            manager_agent_id=manager_agent_id,
            purpose=purpose,
            status=SwarmStatus.ACTIVE
        )
        self.db.add(swarm)
        self.db.commit()
        return swarm

    def dispatch_task_to_swarm(self, swarm_id: int, task: Task):
        swarm = self.get_swarm(swarm_id)
        suitable_agent = self.select_suitable_agent(swarm, task)
        self.hermes_client.dispatch_task(
            agent_name=suitable_agent.name,
            task_data={'task_id': task.id, 'swarm_id': swarm_id}
        )
        return suitable_agent
```

**说明**:
- `_build_step_prompt` 方法中的步骤描述改为从数据库动态读取：存储在 `agents` 表的 `config['steps_info']` JSONB 字段中，或可迁移至独立的 `step_definitions` 表。避免了硬编码在字典中。
- `HermesClient` 的超时配置从 `settings.HERMES_TIMEOUT` 读取，默认值 300 秒（settings 中配置）。
- `ProjectFolderService` 的 `base_path` 默认值从 `settings.PROJECTS_BASE_PATH` 读取，不再硬编码 `/data/projects`。
- `execute_task` 方法为新增方法，供 Celery 异步任务调用，内部委托给 `execute_step` 执行具体步骤。

### 7.3 QA服务 (qa_service.py)

```python
class QAService:
    def __init__(self, db: Session):
        self.db = db

    async def inspect_artifact(self, task_id: int, artifact: dict):
        # 获取任务对应的验收标准
        task = self.get_task(task_id)
        acceptance_criteria = task.acceptance_criteria

        # 调用后荣Agent执行检验
        horong = self.get_agent_by_name('hourong')
        qa_agent = QAAgent(horong)

        # 执行检验（异步调用）
        inspection_result = await qa_agent.inspect(
            artifact=artifact,
            criteria=acceptance_criteria
        )

        # 记录检验结果
        qa_record = QARecord(
            task_id=task_id,
            reviewer_agent_id=horong.id,
            acceptance_result=inspection_result.result,
            problem_details=inspection_result.problems,
            review_dimensions=inspection_result.dimensions,
            score=inspection_result.score
        )
        self.db.add(qa_record)
        self.db.commit()

        return qa_record

    def calculate_score(self, dimensions: list) -> float:
        # 计算综合评分：各维度得分的算术平均值
        if not dimensions:
            return 0.0

        total_score = sum(dim['score'] for dim in dimensions)
        return total_score / len(dimensions)

    def is_artifact_approved(self, qa_record: QARecord) -> bool:
        # 检查所有维度是否达标且综合评分>=85
        all_dimensions_passed = all(
            dim['met_threshold'] for dim in qa_record.review_dimensions
        )
        return all_dimensions_passed and qa_record.score >= 85
```

### 7.4 群组服务 (group_service.py)

```python
class GroupService:
    def __init__(self, db: Session):
        self.db = db
        self.connection_manager = ConnectionManager()

    def create_group(self, project_id: int):
        # 创建项目讨论群
        group = Group(
            project_id=project_id,
            name=f"Project {project_id} Discussion Group",
            mode='discussion'
        )
        self.db.add(group)
        self.db.commit()

        # 添加所有9个命名Agent为成员
        named_agents = self.get_named_agents()
        for agent in named_agents:
            member = GroupMember(
                group_id=group.id,
                agent_id=agent.id,
                member_type='agent'
            )
            self.db.add(member)

        self.db.commit()
        return group

    def send_message(self, group_id: int, sender_id: int, sender_type: str, content: str):
        # 保存消息到数据库
        message = GroupMessage(
            group_id=group_id,
            sender_id=sender_id,
            sender_type=sender_type,
            content=content,
            timestamp=datetime.utcnow()
        )
        self.db.add(message)
        self.db.commit()

        # 通过WebSocket推送消息给所有群组成员
        self.connection_manager.broadcast_to_group(
            group_id=group_id,
            message={
                'type': 'message_new',
                'data': message.to_dict()
            }
        )

        return message

    def start_meeting(self, group_id: int, topic: str, meeting_type: str, host_agent_id: int):
        group = self.get_group(group_id)

        # 切换到会议模式（groups 表仅保留 mode 字段）
        group.mode = 'meeting'
        self.db.commit()

        # 创建 meeting_outcomes 记录存储会议详情
        meeting_outcome = MeetingOutcome(
            group_id=group_id,
            meeting_topic=topic,
            host_agent_id=host_agent_id,
            meeting_type=meeting_type,
            started_at=datetime.utcnow()
        )
        self.db.add(meeting_outcome)
        self.db.commit()

        # 通知所有成员会议开始
        self.connection_manager.broadcast_to_group(
            group_id=group_id,
            message={
                'type': 'meeting_started',
                'data': {
                    'topic': topic,
                    'type': meeting_type
                }
            }
        )

        return group
```

---

## 8. Celery异步任务

### 8.1 Celery配置 (celery_app.py)

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    'devflow',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.workers.task_scheduler', 'app.workers.profile_scanner']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True
)
```

### 8.2 任务调度器 (task_scheduler.py)

```python
from app.workers.celery_app import celery_app
from app.services.agent_service import AgentService

@celery_app.task(bind=True, max_retries=3)
def execute_agent_task(self, task_id: int, agent_id: int):
    """执行Agent任务"""
    db = SessionLocal()
    try:
        agent_service = AgentService(db)
        # 使用execute_task方法执行指定Agent的任务
        # execute_task内部会委托给execute_step执行具体步骤
        result = agent_service.execute_task(task_id, agent_id)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

@celery_app.task
def scan_hermes_profiles():
    """扫描Hermes Profiles"""
    db = SessionLocal()
    try:
        profile_scanner = ProfileScanner(db)
        profiles = profile_scanner.scan()
        profile_scanner.sync_to_database(profiles)
        return len(profiles)
    finally:
        db.close()

@celery_app.task
def send_notification(notification_id: int):
    """发送通知"""
    db = SessionLocal()
    try:
        notification_service = NotificationService(db)
        notification_service.send(notification_id)
    finally:
        db.close()
```

### 8.3 Profile扫描器 (profile_scanner.py)

```python
import os
import yaml
from pathlib import Path

class ProfileScanner:
    def __init__(self, db: Session):
        self.db = db
        self.profiles_path = Path(settings.HERMES_PROFILES_PATH)

    def scan(self) -> list:
        profiles = []

        if not self.profiles_path.exists():
            return profiles

        for profile_dir in self.profiles_path.iterdir():
            if profile_dir.is_dir():
                config_file = profile_dir / 'config.yaml'
                if config_file.exists():
                    profile = self.parse_profile(config_file)
                    if profile:
                        profiles.append(profile)

        return profiles

    def parse_profile(self, config_file: Path) -> dict:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        return {
            'name': config.get('name', config_file.parent.name),
            'model_default': config.get('model_default'),
            'model_provider': config.get('model_provider'),
            'gateway_port': config.get('gateway_port'),
            'personality': config.get('personality', ''),
            'config_path': str(config_file)
        }

    def sync_to_database(self, profiles: list):
        for profile_data in profiles:
            # 检查是否已存在
            profile = self.db.query(Agent).filter(
                Agent.name == profile_data['name']
            ).first()

            # 构建完整的API URL（URL字符串，不是端口号）
            gateway_port = profile_data.get('gateway_port', 8765)
            api_url = f"http://localhost:{gateway_port}/v1/chat/completions"

            if profile:
                # 更新现有记录
                profile.model_default = profile_data['model_default']
                profile.model_provider = profile_data['model_provider']
                profile.api_endpoint = api_url
                profile.config = profile_data
            else:
                # 创建新记录
                profile = Agent(
                    name=profile_data['name'],
                    agent_type='named',
                    model_default=profile_data['model_default'],
                    model_provider=profile_data['model_provider'],
                    api_endpoint=api_url,
                    config=profile_data
                )
                self.db.add(profile)

        self.db.commit()
```

---

## 9. WebSocket连接管理

### 9.1 ConnectionManager 实现

```python
import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # active_connections: {websocket: user_id}
        self.active_connections: Dict[WebSocket, str] = {}
        # group_subscriptions: {group_id: [websocket, ...]}
        self.group_subscriptions: Dict[str, list] = {}
        # user_connections: {user_id: [websocket, ...]}
        self.user_connections: Dict[str, list] = {}
        # 线程安全锁
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            self.active_connections[websocket] = user_id

            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            user_id = self.active_connections.pop(websocket, None)
            if user_id and user_id in self.user_connections:
                if websocket in self.user_connections[user_id]:
                    self.user_connections[user_id].remove(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # 取消所有群组订阅
            for group_id, connections in self.group_subscriptions.items():
                if websocket in connections:
                    connections.remove(websocket)

    async def subscribe_to_group(self, websocket: WebSocket, group_id: str):
        async with self._lock:
            if group_id not in self.group_subscriptions:
                self.group_subscriptions[group_id] = []
            self.group_subscriptions[group_id].append(websocket)

    async def unsubscribe_from_group(self, websocket: WebSocket, group_id: str):
        async with self._lock:
            if group_id in self.group_subscriptions:
                if websocket in self.group_subscriptions[group_id]:
                    self.group_subscriptions[group_id].remove(websocket)

    async def broadcast_to_group(self, group_id: str, message: dict):
        async with self._lock:
            if group_id not in self.group_subscriptions:
                return
            connections = self.group_subscriptions[group_id].copy()

        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            await self.disconnect(connection)

    async def send_to_user(self, user_id: str, message: dict):
        async with self._lock:
            if user_id not in self.user_connections:
                return
            connections = self.user_connections[user_id].copy()

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection)
```

**说明**: 使用 asyncio.Lock 保护所有共享状态的读写操作，确保高并发场景下的线程安全性。

### 9.2 WebSocket端点实现

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.websocket import connection_manager
from app.database import SessionLocal

router = APIRouter()

@router.websocket("/ws/group-chat")
async def group_chat_websocket(websocket: WebSocket, token: str):
    # 验证Token
    user_id = verify_token(token)

    await connection_manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message['type'] == 'subscribe':
                await connection_manager.subscribe_to_group(
                    websocket, message['group_id']
                )
                await websocket.send_json({
                    'type': 'subscribed',
                    'group_id': message['group_id']
                })

            elif message['type'] == 'send_message':
                # 处理发送消息 - 在WebSocket端点内创建独立Session
                db = SessionLocal()
                try:
                    group_service = GroupService(db)
                    saved_message = group_service.send_message(
                        group_id=message['group_id'],
                        sender_id=user_id,
                        sender_type='user',
                        content=message['content']
                    )
                    db.commit()
                finally:
                    db.close()

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
```

**说明**: WebSocket 端点不能使用 FastAPI 的 get_db() 依赖注入（WebSocket 不支持 Depends），因此需要在端点内部手动创建和关闭 SessionLocal。

---

## 10. 错误处理

### 10.1 统一错误响应格式

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.detail.__class__.__name__,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

### 10.2 业务异常类

```python
class DevFlowException(Exception):
    """DevFlow 基础异常"""
    def __init__(self, message: str, code: str = "DEVFLOW_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class ProjectNotFoundException(DevFlowException):
    def __init__(self, project_id: int):
        super().__init__(
            message=f"Project {project_id} not found",
            code="PROJECT_NOT_FOUND",
            status_code=404
        )

class AgentBusyException(DevFlowException):
    def __init__(self, agent_id: int):
        super().__init__(
            message=f"Agent {agent_id} is currently busy",
            code="AGENT_BUSY",
            status_code=409
        )

class QAInspectionFailedException(DevFlowException):
    def __init__(self, task_id: int, problems: list):
        super().__init__(
            message=f"QA inspection failed for task {task_id}",
            code="QA_INSPECTION_FAILED",
            status_code=400
        )
        self.problems = problems
```

---

## 11. 数据库Session管理

### 11.1 FastAPI 请求中的 Session

在 API 路由中统一使用 FastAPI 的 `get_db` 依赖注入，由框架自动管理 Session 的生命周期（打开/关闭/回滚）：

```python
from typing import Generator
from sqlalchemy.orm import Session

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 使用示例
@router.get("/api/v1/projects")
async def list_projects(db: Session = Depends(get_db), limit: int = 20, offset: int = 0):
    project_service = ProjectService(db)
    return project_service.list_projects(limit=limit, offset=offset)
```

### 11.2 Celery 任务中的 Session

在 Celery 异步任务中使用 context manager 模式管理 Session：

```python
@celery_app.task(bind=True, max_retries=3)
def execute_agent_task(self, task_id: int, agent_id: int):
    with SessionLocal() as db:
        try:
            agent_service = AgentService(db)
            # 调用execute_task方法（已定义在AgentService中，内部委托给execute_step）
            result = agent_service.execute_task(task_id, agent_id)
            db.commit()
            return result
        except Exception as exc:
            db.rollback()
            raise self.retry(exc=exc, countdown=60)
```

**说明**: Service 层统一接收 Session 对象，不直接创建 Session。FastAPI 路由通过 Depends(get_db) 注入，Celery 任务使用 context manager 模式，确保 Session 正确关闭。`execute_task` 方法已在 `AgentService` 中定义（见7.2节），内部委托给 `execute_step` 执行具体步骤。

---

**文档结束**
