# DevFlow 项目管理平台 - 后端设计文档

**版本**: V3  
**日期**: 2026-06-12  
**作者**: HouWang (后旺)  
**状态**: 修订版

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
│   │   ├── group.py
│   │   ├── swarm.py
│   │   ├── qa.py
│   │   └── repo.py
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

---

## 3. API接口列表

### 3.1 用户认证接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/auth/login | 用户登录 | 无 |
| POST | /api/auth/register | 用户注册 | 无 |
| POST | /api/auth/refresh | 刷新Token | Token |
| GET | /api/auth/profile | 获取用户信息 | Token |

### 3.2 项目管理接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/projects | 创建项目 | Token |
| GET | /api/projects | 获取项目列表 | Token |
| GET | /api/projects/:id | 获取项目详情 | Token |
| GET | /api/projects/:id/progress | 获取项目进度 | Token |
| POST | /api/projects/:id/complete | 确认项目完成 | Token |

### 3.3 16步流程调度接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/projects/:id/step2 | 执行第二步：确认核心目标 | Token |
| POST | /api/projects/:id/step3 | 执行第三步：需求分析 | Token |
| POST | /api/projects/:id/step4 | 执行第四步：架构设计 | Token |
| POST | /api/projects/:id/step5 | 执行第五步：建立开发环境 | Token |
| POST | /api/projects/:id/step6 | 执行第六步：TDD测试计划 | Token |
| POST | /api/projects/:id/step7 | 执行第七步：TDD测试用例编写 | Token |
| POST | /api/projects/:id/step8 | 执行第八步：代码编写计划 | Token |
| POST | /api/projects/:id/step9 | 执行第九步：功能代码编写 | Token |
| POST | /api/projects/:id/step10 | 执行第十步：测试环境部署 | Token |
| POST | /api/projects/:id/step11 | 执行第十一步：全面测试 | Token |
| POST | /api/projects/:id/step12 | 执行第十二步：安全审计 | Token |
| POST | /api/projects/:id/step13 | 执行第十三步：生产环境部署 | Token |
| POST | /api/projects/:id/step14 | 执行第十四步：文档完善 | Token |
| POST | /api/projects/:id/step15 | 执行第十五步：交付报告 | Token |
| POST | /api/projects/:id/step16 | 执行第十六步：满意度确认 | Token |

### 3.4 Agent管理接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /api/agents | 获取Agent列表 | Token |
| GET | /api/agents/:id | 获取Agent详情 | Token |
| POST | /api/agents/register | Agent注册 | Token |
| DELETE | /api/agents/:id | 移除Agent | Token |
| GET | /api/profiles | 获取Hermes Profiles | Token |
| POST | /api/agents/sync-hermes | 同步Hermes Profiles | Token |

### 3.5 Agent蜂群接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/swarms | 创建蜂群 | Token |
| GET | /api/swarms/:id | 获取蜂群详情 | Token |
| POST | /api/swarms/:id/dispatch | 分发任务到蜂群 | Token |
| GET | /api/swarms/:id/progress | 获取蜂群进度 | Token |
| DELETE | /api/swarms/:id | 解散蜂群 | Token |
| GET | /api/swarm/tasks/:agent_id | 蜂群Agent获取任务 | Token |
| POST | /api/swarm/tasks/:agent_id/acknowledge | 确认接收任务 | Token |
| POST | /api/swarm/tasks/:task_id/progress | 上报任务进度 | Token |
| POST | /api/swarm/tasks/:task_id/deliver | 提交任务成果 | Token |
| POST | /api/swarm/tasks/:task_id/error | 上报执行错误 | Token |

### 3.6 QA门控接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /api/qa/:task_id/inspect | 执行QA检验 | Token |
| GET | /api/qa/:project_id/records | 获取QA记录 | Token |
| POST | /api/qa/:task_id/rollback | 退回重做 | Token |
| GET | /api/qa/:task_id/status | 获取检验状态 | Token |

### 3.7 项目讨论群接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | /api/groups | 获取群组列表 | Token |
| POST | /api/groups | 创建群组 | Token |
| GET | /api/groups/:id | 获取群组详情 | Token |
| POST | /api/groups/:id/members | 添加成员 | Token |
| DELETE | /api/groups/:id/members/:agent_id | 移除成员 | Token |
| GET | /api/groups/:id/messages | 获取消息列表 | Token |
| GET | /api/groups/:id/outcomes | 获取会议结果 | Token |
| POST | /api/groups/:id/host | 设置主持人 | Token |

### 3.8 WebSocket端点

| 端点 | 描述 |
|------|------|
| ws://{host}/ws/group-chat | 群聊WebSocket连接 |
| ws://{host}/ws/notifications | 通知WebSocket连接 |
| ws://{host}/ws/project/:id | 项目进度WebSocket连接 |

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
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.jwt import decode_token

security = HTTPBearer()

async def auth_middleware(request: Request, call_next):
    # 跳过公开路径
    if request.url.path in ['/api/auth/login', '/api/auth/register']:
        return await call_next(request)
    
    # 提取并验证Token
    credentials = await security(request)
    try:
        payload = decode_token(credentials.credentials)
        request.state.user = payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    response = await call_next(request)
    return response
```

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
        
        # 构建限流键
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

### 6.2 授权策略

- RBAC 基于角色的访问控制
- 用户角色：user, admin, system_admin
- 权限检查装饰器

```python
from functools import wraps
from fastapi import HTTPException

def require_role(*roles):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            if user.role not in roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

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
class ProjectService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_project(self, user_id: int, project_data: ProjectCreate):
        # 创建项目记录
        project = Project(
            name=project_data.name,
            description=project_data.description,
            creator_id=user_id,
            status=ProjectStatus.CREATED
        )
        self.db.add(project)
        self.db.commit()
        
        # 自动创建Gitea仓库
        repo_service = RepoService(self.db)
        repo_service.create_repo(project.id, project.name)
        
        # 创建项目文件夹
        project_folder_service.create_project_folder(project.id)
        
        return project
    
    def get_project_progress(self, project_id: int):
        project = self.get_project(project_id)
        steps = self.db.query(Step).filter(Step.project_id == project_id).all()
        
        return {
            "project": project,
            "current_step": project.current_step,
            "steps": steps,
            "progress_percent": (project.current_step / 16) * 100
        }
    
    def execute_step(self, project_id: int, step_number: int, user: User):
        project = self.get_project(project_id)
        
        # 验证步骤执行条件
        if step_number != project.current_step + 1:
            raise ValueError("Invalid step sequence")
        
        # 根据步骤号调用对应的Agent服务
        agent_service = AgentService(self.db)
        
        if step_number == 2:
            # 第二步：海梅确认核心目标
            agent_service.execute_step_2(project_id)
        elif step_number == 3:
            # 第三步：后兴需求分析
            agent_service.execute_step_3(project_id)
        # ... 其他步骤
        
        # 更新项目当前步骤
        project.current_step = step_number
        self.db.commit()
        
        return project
```

### 7.2 Agent服务 (agent_service.py)

```python
class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.hermes_client = HermesClient()
    
    def get_named_agents(self):
        return self.db.query(Agent).filter(Agent.agent_type == 'named').all()
    
    def execute_step_2(self, project_id: int):
        # 第二步：海梅确认核心目标+搭建组织架构+建立讨论群
        haimei = self.get_agent_by_name('haimei')
        
        # 调用海梅的Gateway API
        result = self.hermes_client.call_agent(
            agent_id=haimei.id,
            task_type='step2',
            project_id=project_id
        )
        
        # 记录执行日志
        self.record_execution_log(project_id, haimei.id, result)
        
        return result
    
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
        
        # 选择适合的蜂群Agent
        suitable_agent = self.select_suitable_agent(swarm, task)
        
        # 分发任务
        self.hermes_client.dispatch_task(
            agent_id=suitable_agent.id,
            task=task
        )
        
        return suitable_agent
```

### 7.3 QA服务 (qa_service.py)

```python
class QAService:
    def __init__(self, db: Session):
        self.db = db
    
    def inspect_artifact(self, task_id: int, artifact: dict):
        # 获取任务对应的验收标准
        task = self.get_task(task_id)
        acceptance_criteria = task.acceptance_criteria
        
        # 调用后荣Agent执行检验
        horong = self.get_agent_by_name('hourong')
        qa_agent = QAAgent(horong)
        
        # 执行检验
        inspection_result = qa_agent.inspect(
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
            
            if profile:
                # 更新现有记录
                profile.model_default = profile_data['model_default']
                profile.model_provider = profile_data['model_provider']
                profile.api_endpoint = profile_data['gateway_port']
                profile.config = profile_data
            else:
                # 创建新记录
                profile = Agent(
                    name=profile_data['name'],
                    agent_type='named',
                    model_default=profile_data['model_default'],
                    model_provider=profile_data['model_provider'],
                    api_endpoint=profile_data['gateway_port'],
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
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[websocket] = user_id
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket):
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
        if group_id not in self.group_subscriptions:
            self.group_subscriptions[group_id] = []
        self.group_subscriptions[group_id].append(websocket)
    
    async def unsubscribe_from_group(self, websocket: WebSocket, group_id: str):
        if group_id in self.group_subscriptions:
            if websocket in self.group_subscriptions[group_id]:
                self.group_subscriptions[group_id].remove(websocket)
    
    async def broadcast_to_group(self, group_id: str, message: dict):
        if group_id in self.group_subscriptions:
            connections = self.group_subscriptions[group_id].copy()
            disconnected = []
            
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            
            # 清理断开的连接
            for connection in disconnected:
                self.disconnect(connection)
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.user_connections:
            connections = self.user_connections[user_id].copy()
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(connection)
```

### 9.2 WebSocket端点实现

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.websocket import connection_manager

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
                # 处理发送消息
                group_service = GroupService(get_db())
                saved_message = group_service.send_message(
                    group_id=message['group_id'],
                    sender_id=user_id,
                    sender_type='user',
                    content=message['content']
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
```

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

async http_exception_handler(request: Request, exc: HTTPException):
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

**文档结束**
