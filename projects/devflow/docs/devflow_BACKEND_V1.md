# DevFlow 后端设计文档 V1.0

**项目**: DevFlow 项目管理平台
**版本**: 1.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: 初稿

---

## 1. 后端技术栈

### 1.1 核心框架与库

| 类别 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| Web框架 | FastAPI | 0.109+ | 异步Web框架，自动API文档 |
| 异步运行时 | uvicorn | 0.27+ | ASGI服务器 |
| ORM | SQLAlchemy 2.0 | 2.0+ | 异步ORM |
| 数据验证 | Pydantic 2.0 | 2.5+ | 请求/响应模型验证 |
| 任务队列 | Celery | 5.3+ | 分布式任务调度 |
| 消息代理 | Redis | 6+ | Celery Broker + 结果后端 |
| 数据库驱动 | asyncpg | 0.29+ | PostgreSQL异步驱动 |
| JWT认证 | python-jose | 3.3+ | JWT Token生成和验证 |
| 密码哈希 | passlib[bcrypt] | 1.7+ | 用户密码加密 |
| HTTP客户端 | httpx | 0.27+ | 异步HTTP请求 (Gitea/Gateway) |
| WebSocket | websockets | 12.0+ | WebSocket支持 |
| 邮件发送 | python-dotenv | 1.0+ | 环境变量管理 |
| 日志 | loguru | 0.7+ | 结构化日志 |
| 监控 | prometheus-client | 0.19+ | 指标采集 |
| 链路追踪 | opentelemetry-api | 1.22+ | 分布式追踪 |
| 数据库迁移 | Alembic | 1.13+ | 数据库版本管理 |
| 测试 | pytest + httpx | 7.4+ | 单元测试和集成测试 |

### 1.2 项目目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI应用入口
│   ├── config/                 # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py         # 应用配置 (环境变量)
│   │   └── database.py         # 数据库连接配置
│   ├── api/                    # API路由层
│   │   ├── __init__.py
│   │   ├── deps.py             # 依赖注入
│   │   └── v1/                 # API v1版本
│   │       ├── __init__.py
│   │       ├── router.py       # 路由聚合
│   │       ├── auth.py         # 认证接口
│   │       ├── projects.py     # 项目管理接口
│   │       ├── agents.py       # Agent管理接口
│   │       ├── swarms.py       # 蜂群管理接口
│   │       ├── qa.py           # QA门控接口
│   │       ├── groups.py       # 群聊管理接口
│   │       ├── repos.py        # 代码库管理接口
│   │       ├── hermes.py       # Gateway通信接口
│   │       └── websocket/      # WebSocket端点
│   │           ├── __init__.py
│   │           ├── connection.py   # WebSocket连接管理
│   │           └── group_chat.py  # 群聊WebSocket
│   ├── core/                   # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── workflow/           # 16步流程引擎
│   │   │   ├── __init__.py
│   │   │   ├── engine.py       # 流程调度引擎
│   │   │   ├── step_executor.py# 步骤执行器
│   │   │   ├── dependency_graph.py # 任务依赖图
│   │   │   └── state_machine.py # 步骤状态机
│   │   ├── agent/              # Agent管理
│   │   │   ├── __init__.py
│   │   │   ├── coordinator.py  # Agent协调器
│   │   │   ├── profile_scanner.py # Profile扫描
│   │   │   ├── gateway_client.py  # Gateway HTTP客户端
│   │   │   └── swarm_manager.py   # 蜂群管理器
│   │   ├── qa/                 # QA门控
│   │   │   ├── __init__.py
│   │   │   ├── inspector.py    # QA检验引擎
│   │   │   ├── dimensions.py   # 检验维度定义
│   │   │   ├── scorer.py       # 量化打分引擎
│   │   │   └── rules.py        # 合格判定规则
│   │   ├── collaboration/      # 协作模块
│   │   │   ├── __init__.py
│   │   │   ├── group_manager.py# 群组管理
│   │   │   ├── discussion.py   # 讨论模式
│   │   │   ├── meeting.py      # 会议模式
│   │   │   └── message_bus.py  # 消息总线
│   │   ├── gitea/              # Gitea集成
│   │   │   ├── __init__.py
│   │   │   ├── client.py       # Gitea REST客户端
│   │   │   ├── repo_manager.py # 仓库管理
│   │   │   ├── branch_manager.py# 分支管理
│   │   │   └── pr_manager.py   # PR管理
│   │   └── notification/       # 通知模块
│   │       ├── __init__.py
│   │       ├── push.py         # WebSocket推送
│   │       └── email.py        # 邮件通知
│   ├── models/                 # SQLAlchemy数据模型
│   │   ├── __init__.py
│   │   ├── user.py             # 用户模型
│   │   ├── project.py          # 项目模型
│   │   ├── requirement.py      # 需求模型
│   │   ├── agent.py            # Agent模型
│   │   ├── task.py             # 任务模型
│   │   ├── qa.py               # QA记录模型
│   │   ├── group.py            # 群组模型
│   │   ├── meeting.py          # 会议模型
│   │   ├── swarm.py            # 蜂群模型
│   │   ├── notification.py     # 通知模型
│   │   └── repo.py             # 代码库模型
│   ├── schemas/                # Pydantic请求/响应模型
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── project.py
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── qa.py
│   │   ├── group.py
│   │   ├── meeting.py
│   │   ├── swarm.py
│   │   ├── notification.py
│   │   └── repo.py
│   ├── services/               # 业务服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── agent_service.py
│   │   ├── workflow_service.py
│   │   ├── qa_service.py
│   │   ├── group_service.py
│   │   ├── swarm_service.py
│   │   ├── repo_service.py
│   │   └── notification_service.py
│   ├── tasks/                  # Celery异步任务
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery应用配置
│   │   ├── workflow_tasks.py   # 流程执行任务
│   │   ├── agent_tasks.py      # Agent执行任务
│   │   ├── qa_tasks.py         # QA检验任务
│   │   ├── gitea_tasks.py      # Gitea操作任务
│   │   └── notification_tasks.py# 通知推送任务
│   ├── middleware/             # 中间件
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证中间件
│   │   ├── cors.py             # CORS中间件
│   │   ├── logging.py          # 日志中间件
│   │   ├── rate_limit.py       # 限流中间件
│   │   └── tracing.py          # 链路追踪中间件
│   ├── utils/                  # 工具函数
│   │   ├── __init__.py
│   │   ├── jwt.py              # JWT工具
│   │   ├── password.py         # 密码哈希
│   │   ├── datetime.py         # 日期时间处理
│   │   ├── file.py             # 文件操作
│   │   └── validator.py        # 数据验证
│   └── monitoring/             # 监控
│       ├── __init__.py
│       ├── metrics.py          # Prometheus指标
│       ├── tracing.py          # OpenTelemetry追踪
│       └── health.py           # 健康检查
├── tests/                      # 测试
│   ├── __init__.py
│   ├── conftest.py             # pytest配置
│   ├── test_auth.py
│   ├── test_projects.py
│   ├── test_agents.py
│   ├── test_workflow.py
│   ├── test_qa.py
│   ├── test_groups.py
│   └── test_swarms.py
├── migrations/                 # Alembic数据库迁移
│   ├── versions/               # 迁移脚本
│   ├── env.py
│   └── script.py.mako
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 2. API接口设计

### 2.1 接口规范

**统一响应格式**:
```python
class ResponseSchema(BaseModel):
    """统一API响应格式"""
    code: int = Field(default=200, description="状态码: 200成功, 4xx客户端错误, 5xx服务器错误")
    message: str = Field(default="success", description="响应消息")
    data: Optional[dict] = Field(default=None, description="响应数据")

class PaginatedResponse(BaseModel):
    """分页响应格式"""
    code: int = 200
    message: str = "success"
    data: List[T]
    pagination: PaginationInfo

class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
```

**错误响应格式**:
```python
class ErrorResponse(BaseModel):
    code: int
    message: str
    details: Optional[dict] = None
    trace_id: str  # 用于追踪问题
```

**HTTP状态码约定**:
| 状态码 | 含义 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 数据验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

### 2.2 认证与授权接口

```python
# auth.py

@router.post("/api/auth/login", response_model=AuthResponse)
async def login(credentials: LoginCredentials):
    """
    人类用户登录
    - 验证用户名和密码
    - 返回JWT Access Token + Refresh Token
    """
    pass

@router.post("/api/auth/refresh", response_model=AuthResponse)
async def refresh_token(refresh: RefreshTokenRequest):
    """刷新Access Token"""
    pass

@router.post("/api/auth/logout")
async def logout(token: str = Header(...)):
    """用户登出 (将Token加入黑名单)"""
    pass

@router.get("/api/auth/me", response_model=UserInfo)
async def get_current_user(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    pass
```

### 2.3 项目管理接口

```python
# projects.py

@router.post("/api/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: CreateProjectRequest,
    current_user: User = Depends(get_current_user)
):
    """
    第一步: 人类用户创建项目
    - 生成唯一项目ID (proj-YYYYMMDD-SEQ)
    - 自动创建Gitea代码仓库
    - 自动创建项目文件夹
    - 无需QA门控
    """
    pass

@router.get("/api/projects", response_model=PaginatedResponse[ProjectSummary])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """获取用户项目列表 (仅返回当前用户的项目)"""
    pass

@router.get("/api/projects/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取项目详情 (含16步流程进度)"""
    pass

@router.get("/api/projects/{project_id}/progress", response_model=WorkflowProgress)
async def get_project_progress(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取项目16步流程详细进度"""
    pass

@router.post("/api/projects/{project_id}/complete")
async def complete_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """确认项目完成 (第十六步)"""
    pass
```

### 2.4 16步流程调度接口

```python
# workflow.py

@router.post("/api/projects/{project_id}/step2", response_model=StepExecutionResponse)
async def execute_step2(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第二步: 海梅确认核心目标 + 搭建组织架构 + 建立讨论群
    - 海梅主动与用户对话
    - 激活9个命名Agent角色
    - 创建项目讨论群
    - 后荣进行QA检验
    """
    pass

@router.post("/api/projects/{project_id}/step3", response_model=StepExecutionResponse)
async def execute_step3(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第三步: 海梅→后兴需求分析
    - 后兴与用户对话沟通需求
    - 复杂项目召开需求评审会议
    - 生成软件需求说明书
    - 后荣按四维度检验 (完整性/一致性/可验证性/无歧义性)
    """
    pass

@router.post("/api/projects/{project_id}/step4", response_model=StepExecutionResponse)
async def execute_step4(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第四步: 海梅→后旺架构设计
    - 生成4份设计文档 (架构/后端/前端/数据库)
    - 每份文档经后荣逐项检验
    - 全部合格方可放行
    """
    pass

@router.post("/api/projects/{project_id}/step5", response_model=StepExecutionResponse)
async def execute_step5(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第五步: 海梅→后富建立开发环境
    - 代码仓库初始化
    - 开发框架搭建
    - 依赖配置
    - 数据库初始化
    - CI/CD流水线配置
    """
    pass

@router.post("/api/projects/{project_id}/step6", response_model=StepExecutionResponse)
async def execute_step6(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第六步: 海梅制订TDD测试用例编写计划
    - 每个用例原子化 (单一功能/<200行/<2小时)
    - 每个用例有可量化验收标准
    """
    pass

@router.post("/api/projects/{project_id}/step7", response_model=StepExecutionResponse)
async def execute_step7(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第七步: 海梅→后发(蜂群)编写TDD测试用例
    - 后发建立Agent蜂群
    - 蜂群Agent并行编写测试用例
    - 后荣逐用例检验
    """
    pass

@router.post("/api/projects/{project_id}/step8", response_model=StepExecutionResponse)
async def execute_step8(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第八步: 海梅制订代码编写计划
    - 每个任务原子化
    - 每个任务有测试用例一一对应
    - 绘制任务依赖图 (有向无环图)
    """
    pass

@router.post("/api/projects/{project_id}/step9", response_model=StepExecutionResponse)
async def execute_step9(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第九步: 海梅→后发(蜂群)编写功能代码
    - 按依赖图顺序执行
    - 前置任务QA通过后才执行后继任务
    - 前后任务由不同蜂群Agent执行
    - 后荣逐任务检验
    """
    pass

@router.post("/api/projects/{project_id}/step10", response_model=StepExecutionResponse)
async def execute_step10(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """第十步: 海梅→后富部署到测试环境"""
    pass

@router.post("/api/projects/{project_id}/step11", response_model=StepExecutionResponse)
async def execute_step11(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第十一步: 海梅→后达(蜂群)全面测试
    - 单元测试 / 模块测试 / 集成测试 / 前端实操验证
    - 前端实操使用Playwright/Selenium
    """
    pass

@router.post("/api/projects/{project_id}/step12", response_model=StepExecutionResponse)
async def execute_step12(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第十二步: 海梅→后华安全审计
    - 代码审计 / 合规审查 / 渗透测试 / 漏洞修复
    - 渗透测试范围: OWASP Top 10
    """
    pass

@router.post("/api/projects/{project_id}/step13", response_model=StepExecutionResponse)
async def execute_step13(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """第十三步: 海梅→后富部署到生产环境"""
    pass

@router.post("/api/projects/{project_id}/step14", response_model=StepExecutionResponse)
async def execute_step14(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    第十四步: 海梅→后贵完善项目文档
    - 部署手册 / 操作手册 / API文档 / 用户手册
    - 保证所有文档一致性
    """
    pass

@router.post("/api/projects/{project_id}/step15", response_model=StepExecutionResponse)
async def execute_step15(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """第十五步: 海梅向用户报告交付成果"""
    pass

@router.post("/api/projects/{project_id}/step16", response_model=StepExecutionResponse)
async def execute_step16(
    project_id: str,
    feedback: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    第十六步: 用户满意度确认与迭代修改
    - 满意: 项目结束, 打版本标签
    - 不满意: 收集意见, 回到第三步
    """
    pass
```

### 2.5 Agent管理接口

```python
# agents.py

@router.get("/api/agents", response_model=AgentListResponse)
async def list_agents():
    """获取所有Agent列表 (含9个命名Agent + 蜂群Agent)"""
    pass

@router.get("/api/agents/{agent_id}", response_model=AgentDetail)
async def get_agent(agent_id: str):
    """获取指定Agent详情"""
    pass

@router.post("/api/agents/register", response_model=AgentResponse, status_code=201)
async def register_agent(data: RegisterAgentRequest):
    """编程Agent注册 (蜂群成员)"""
    pass

@router.delete("/api/agents/{agent_id}")
async def remove_agent(agent_id: str):
    """移除Agent"""
    pass

@router.get("/api/profiles", response_model=ProfileListResponse)
async def list_profiles():
    """获取所有扫描到的Hermes Agent Profiles"""
    pass

@router.post("/api/agents/sync-hermes")
async def sync_hermes_profiles():
    """同步发现的profiles到数据库"""
    pass
```

### 2.6 QA门控接口

```python
# qa.py

@router.post("/api/qa/{task_id}/inspect", response_model=QAInspectionResponse)
async def inspect_artifact(
    task_id: str,
    data: InspectionRequest
):
    """
    后荣检验Agent产出
    - 按产出类型加载检验维度
    - 逐项执行量化检验
    - 计算综合评分
    - 判定合格/不合格
    """
    pass

@router.get("/api/qa/{project_id}/records", response_model=QARecordListResponse)
async def list_qa_records(project_id: str):
    """获取项目QA检验记录列表"""
    pass

@router.post("/api/qa/{task_id}/rollback")
async def rollback_task(
    task_id: str,
    suggestions: str
):
    """退回重做 (附带修改建议)"""
    pass

@router.get("/api/qa/{task_id}/status", response_model=QAStatusResponse)
async def get_qa_status(task_id: str):
    """获取当前检验状态"""
    pass
```

### 2.7 蜂群管理接口

```python
# swarms.py

@router.post("/api/swarms", response_model=SwarmResponse, status_code=201)
async def create_swarm(data: CreateSwarmRequest):
    """
    建立Agent蜂群 (后发/后达)
    - 根据任务类型和数量选择Agent
    - 自动启动并初始化Agent
    """
    pass

@router.get("/api/swarms/{swarm_id}", response_model=SwarmDetail)
async def get_swarm(swarm_id: str):
    """获取蜂群详情"""
    pass

@router.post("/api/swarms/{swarm_id}/dispatch")
async def dispatch_task(
    swarm_id: str,
    data: DispatchTaskRequest
):
    """
    蜂群调度: 分发任务到蜂群成员
    - 技能匹配
    - 负载均衡
    - 任务分配
    """
    pass

@router.get("/api/swarms/{swarm_id}/progress", response_model=SwarmProgressResponse)
async def get_swarm_progress(swarm_id: str):
    """获取蜂群整体执行进度"""
    pass

@router.delete("/api/swarms/{swarm_id}")
async def dissolve_swarm(swarm_id: str):
    """解散蜂群"""
    pass

@router.get("/api/swarm/tasks/{agent_id}", response_model=SwarmTaskResponse)
async def get_swarm_task(agent_id: str):
    """蜂群Agent获取分配任务"""
    pass

@router.post("/api/swarm/tasks/{agent_id}/acknowledge")
async def acknowledge_task(agent_id: str):
    """蜂群Agent确认接收任务"""
    pass

@router.post("/api/swarm/tasks/{task_id}/progress")
async def report_task_progress(data: TaskProgressRequest):
    """蜂群Agent上报任务进度"""
    pass

@router.post("/api/swarm/tasks/{task_id}/deliver")
async def deliver_task_result(data: TaskDeliveryRequest):
    """蜂群Agent提交任务成果"""
    pass

@router.post("/api/swarm/tasks/{task_id}/error")
async def report_task_error(data: TaskErrorRequest):
    """蜂群Agent上报执行错误"""
    pass
```

### 2.8 项目讨论群接口

```python
# groups.py

@router.get("/api/groups", response_model=GroupListResponse)
async def list_groups():
    """获取所有群组列表"""
    pass

@router.post("/api/groups", response_model=GroupResponse, status_code=201)
async def create_group(data: CreateGroupRequest):
    """创建群组 (第二步自动调用)"""
    pass

@router.get("/api/groups/{group_id}", response_model=GroupDetail)
async def get_group(group_id: str):
    """获取群组详情和成员列表"""
    pass

@router.post("/api/groups/{group_id}/members")
async def add_group_member(
    group_id: str,
    data: AddMemberRequest
):
    """添加成员到群组"""
    pass

@router.delete("/api/groups/{group_id}/members/{agent_id}")
async def remove_group_member(group_id: str, agent_id: str):
    """从群组移除成员"""
    pass

@router.get("/api/groups/{group_id}/messages", response_model=MessageListResponse)
async def get_group_messages(
    group_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """获取群组历史消息 (支持分页)"""
    pass

@router.get("/api/groups/{group_id}/outcomes", response_model=MeetingOutcomeListResponse)
async def get_group_outcomes(group_id: str):
    """获取群组会议结果列表"""
    pass

@router.post("/api/groups/{group_id}/host")
async def set_group_host(
    group_id: str,
    data: SetHostRequest
):
    """设置群组主持人"""
    pass
```

### 2.9 Gateway通信接口

```python
# hermes.py

@router.get("/api/hermes/health", response_model=HealthCheckResponse)
async def check_hermes_health():
    """检查Hermes Gateway健康状态"""
    pass

@router.post("/api/hermes/chat", response_model=ChatResponse)
async def hermes_chat(data: ChatRequest):
    """与指定Agent对话 (非流式响应)"""
    pass

@router.post("/api/hermes/chat/stream")
async def hermes_chat_stream(data: ChatRequest, request: Request):
    """与Agent对话 (流式SSE响应)"""
    pass

@router.post("/api/hermes/decompose", response_model=DecomposeResponse)
async def decompose_task(data: DecomposeRequest):
    """使用Hermes Agent拆解任务"""
    pass
```

### 2.10 代码库管理接口

```python
# repos.py

@router.post("/api/repos", response_model=RepoResponse, status_code=201)
async def create_repo(data: CreateRepoRequest):
    """创建代码仓库 (第一步自动调用)"""
    pass

@router.get("/api/repos/{repo_id}", response_model=RepoDetail)
async def get_repo(repo_id: str):
    """获取仓库详情"""
    pass

@router.get("/api/repos/{repo_id}/branches", response_model=BranchListResponse)
async def list_branches(repo_id: str):
    """获取仓库分支列表"""
    pass

@router.post("/api/repos/{repo_id}/branches", response_model=BranchResponse, status_code=201)
async def create_branch(
    repo_id: str,
    data: CreateBranchRequest
):
    """创建新分支"""
    pass

@router.get("/api/repos/{repo_id}/pulls", response_model=PRListResponse)
async def list_pull_requests(repo_id: str):
    """获取PR列表"""
    pass

@router.post("/api/repos/{repo_id}/pulls", response_model=PRResponse, status_code=201)
async def create_pull_request(
    repo_id: str,
    data: CreatePRRequest
):
    """创建Pull Request"""
    pass

@router.post("/api/repos/{repo_id}/pulls/{number}/merge")
async def merge_pull_request(repo_id: str, number: int):
    """合并PR"""
    pass

@router.get("/api/repos/{repo_id}/commits", response_model=CommitListResponse)
async def list_commits(repo_id: str):
    """获取提交记录"""
    pass

@router.post("/api/repos/validate-commit")
async def validate_commit_message(data: ValidateCommitRequest):
    """验证提交消息规范 (Conventional Commits)"""
    pass
```

---

## 3. 数据流设计

### 3.1 16步流程数据流

```
用户创建项目 (Step 1)
    │
    ├─→ POST /api/projects
    │   ├─→ 生成项目ID
    │   ├─→ 创建Gitea仓库
    │   └─→ 创建项目文件夹
    │
    ▼
海梅确认目标 (Step 2)
    │
    ├─→ POST /api/projects/{id}/step2
    │   ├─→ 海梅Agent对话 (Gateway API)
    │   ├─→ 创建项目讨论群
    │   ├─→ 激活9个Agent
    │   └─→ 后荣QA检验
    │       ├─→ 检验合格 → 提交代码库 → 进入Step 3
    │       └─→ 检验不合格 → 退回重做
    │
    ▼
需求分析 (Step 3)
    │
    ├─→ POST /api/projects/{id}/step3
    │   ├─→ 海梅→后兴分派任务
    │   ├─→ 后兴与用户对话
    │   ├─→ 复杂项目召开需求评审会议
    │   ├─→ 生成SRS文档
    │   └─→ 后荣四维度检验
    │       ├─→ 完整性 (12项必查)
    │       ├─→ 一致性 (6类矛盾)
    │       ├─→ 可验证性 (7条规则)
    │       └─→ 无歧义性 (5类模糊)
    │
    ▼
架构设计 (Step 4) → 环境搭建 (Step 5) → TDD计划 (Step 6)
    │
    ▼
TDD测试用例 (Step 7)
    │
    ├─→ 后发建立蜂群
    │   ├─→ POST /api/swarms
    │   ├─→ POST /api/swarms/{id}/dispatch (分发任务)
    │   ├─→ 蜂群Agent执行 (GET /api/swarm/tasks/{agent_id})
    │   ├─→ 进度上报 (POST /api/swarm/tasks/{id}/progress)
    │   └─→ 成果交付 (POST /api/swarm/tasks/{id}/deliver)
    │
    ▼
代码编写 (Step 9)
    │
    ├─→ 按依赖图顺序
    │   ├─→ 前置任务QA通过
    │   ├─→ 后发分发任务
    │   ├─→ 蜂群Agent执行
    │   ├─→ 后荣逐任务检验
    │   └─→ 前后任务不同Agent
    │
    ▼
测试部署 (Step 10) → 全面测试 (Step 11) → 安全审计 (Step 12)
    │
    ▼
生产部署 (Step 13) → 文档完善 (Step 14) → 交付报告 (Step 15)
    │
    ▼
满意度确认 (Step 16)
    │
    ├─→ 满意 → 打版本标签 → 项目结束
    └─→ 不满意 → 收集意见 → 回到Step 3
```

### 3.2 Agent蜂群数据流

```
后发/后达发起蜂群创建
    │
    ├─→ POST /api/swarms {
    │     project_id: "proj-001",
    │     manager_agent_id: "houfa",
    │     purpose: "code_writing",
    │     task_count: 10
    │   }
    │
    ├─→ SwarmManager.create_swarm()
    │   ├─→ 根据任务类型选择Agent
    │   ├─→ 启动Agent进程
    │   ├─→ Agent初始化
    │   │   ├─→ 加载项目上下文
    │   │   ├─→ POST /api/agents/register (注册技能)
    │   │   └─→ 建立通信连接
    │   └─→ 加入项目讨论群 (仅接收消息)
    │
    ├─→ 任务分发
    │   └─→ POST /api/swarms/{id}/dispatch
    │       ├─→ 技能匹配
    │       ├─→ 负载均衡
    │       └─→ 分配任务到Agent
    │
    ├─→ Agent执行
    │   ├─→ GET /api/swarm/tasks/{agent_id} (轮询获取任务)
    │   ├─→ POST /api/swarm/tasks/{id}/acknowledge (确认接收)
    │   ├─→ POST /api/swarm/tasks/{id}/progress (上报进度)
    │   └─→ POST /api/swarm/tasks/{id}/deliver (提交成果)
    │
    └─→ 退出
        ├─→ 正常退出: 任务完成且QA通过
        ├─→ 手动退出: DELETE /api/swarms/{id}
        ├─→ 超时退出: 30分钟超时 + 3次重试失败
        └─→ 异常退出: 进程崩溃 → 更换备用Agent
```

### 3.3 WebSocket群聊数据流

```
客户端连接
    │
    ├─→ ws://{host}/ws/group-chat?group_id={id}
    │   ├─→ ConnectionManager.connect()
    │   ├─→ 加入群组订阅
    │   └─→ 推送历史消息 (最近50条)
    │
    ├─→ 客户端发送消息
    │   └─→ { type: "send_message", data: { content, mentions } }
    │       ├─→ 保存到数据库
    │       ├─→ 广播给所有订阅者
    │       └─→ 检测@mention → 触发Agent回复
    │
    ├─→ Agent回复
    │   ├─→ Gateway API调用Agent
    │   ├─→ 流式推送: message_start → message_chunk → message_complete
    │   └─→ 保存到数据库
    │
    ├─→ 会议模式
    │   ├─→ { type: "start_meeting", data: { topic, type, agenda } }
    │   ├─→ 海梅主持
    │   ├─→ 按议程讨论
    │   └─→ 产出会议纪要
    │
    └─→ 断线重连
        ├─→ 自动重连 (最多5次)
        ├─→ 指数退避 (1s → 2s → 4s → 8s → 16s)
        └─→ 恢复群组订阅
```

---

## 4. 中间件设计

### 4.1 认证中间件

```python
# middleware/auth.py

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """JWT认证依赖"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            Settings.SECRET_KEY,
            algorithms=[Settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return await User.get(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(user: User = Depends(get_current_user)):
    """管理员权限检查"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

### 4.2 CORS中间件

```python
# middleware/cors.py

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.3 日志中间件

```python
# middleware/logging.py

import time
from fastapi import Request
from loguru import logger

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    response.headers["X-Process-Time"] = str(duration)
    return response
```

### 4.4 限流中间件

```python
# middleware/rate_limit.py

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379/1"
)

app.state.limiter = limiter

@router.get("/api/projects")
@limiter.limit("100/minute")
async def list_projects(request: Request):
    # 限流: 每分钟100次
    pass
```

### 4.5 链路追踪中间件

```python
# middleware/tracing.py

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

@app.middleware("http")
async def trace_requests(request: Request, call_next):
    with tracer.start_as_current_span(
        name=f"{request.method} {request.url.path}"
    ) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        
        response = await call_next(request)
        
        span.set_attribute("http.status_code", response.status_code)
        return response
```

---

## 5. 安全策略

### 5.1 认证策略

**JWT Token设计**:
```python
# Access Token (30分钟有效期)
{
    "sub": "user_id",
    "role": "user",
    "exp": 1686700000,
    "iat": 1686698200,
    "type": "access"
}

# Refresh Token (7天有效期)
{
    "sub": "user_id",
    "exp": 1687304800,
    "iat": 1686700000,
    "type": "refresh"
}
```

**密码策略**:
- 最小长度: 8位
- 必须包含: 大写字母、小写字母、数字、特殊字符
- 哈希算法: bcrypt (cost factor: 12)

### 5.2 授权策略 (RBAC)

| 角色 | 权限 |
|------|------|
| user | 创建/查看/操作自身项目 |
| admin | 管理所有项目、Agent、用户 |
| agent | Agent专用权限 (通过API Token认证) |

**项目隔离**:
```python
async def get_project_or_404(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    return project
```

### 5.3 数据传输安全

- 全站 HTTPS (TLS 1.3)
- WebSocket wss:// 加密
- API请求签名 (HMAC-SHA256)
- 敏感数据脱敏存储 (密码哈希、Token加密)

### 5.4 输入验证

```python
# schemas/project.py

from pydantic import BaseModel, Field, field_validator

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=5000)
    initial_requirements: Optional[str] = Field(default=None, max_length=10000)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Project name cannot be empty")
        # 防止XSS
        if "<" in v or ">" in v:
            raise ValueError("Project name contains invalid characters")
        return v.strip()
```

### 5.5 审计日志

```python
# 关键操作审计
AUDIT_EVENTS = [
    "user.login",
    "user.logout",
    "project.create",
    "project.update",
    "agent.task_assign",
    "qa.inspection_pass",
    "qa.inspection_fail",
    "code.commit",
    "swarm.create",
    "swarm.dissolve",
    "error.occurred"
]

async def audit_log(event: str, user_id: str, project_id: str, 
                    action: str, details: dict):
    """记录审计日志"""
    await AuditLog.create(
        event=event,
        user_id=user_id,
        project_id=project_id,
        action=action,
        details=details,
        timestamp=datetime.utcnow(),
        ip_address=request.client.host
    )
```

---

## 6. Celery 异步任务

### 6.1 Celery 配置

```python
# tasks/celery_app.py

from celery import Celery

celery_app = Celery(
    "devflow",
    broker=Settings.REDIS_URL,
    backend=Settings.REDIS_URL,
    include=[
        "app.tasks.workflow_tasks",
        "app.tasks.agent_tasks",
        "app.tasks.qa_tasks",
        "app.tasks.gitea_tasks",
        "app.tasks.notification_tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30分钟超时
    task_soft_time_limit=1700,  # 28分20秒软超时
    worker_prefetch_multiplier=1,  # 一次只处理一个任务
    task_acks_late=True  # 任务完成后确认
)
```

### 6.2 任务定义

```python
# tasks/workflow_tasks.py

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def execute_workflow_step(self, project_id: str, step_number: int):
    """
    执行16步流程中的指定步骤
    - 异步执行，不阻塞API响应
    - 支持重试 (最多3次)
    - 超时30分钟自动终止
    """
    try:
        workflow_engine = WorkflowEngine(project_id)
        result = workflow_engine.execute_step(step_number)
        
        # 推送WebSocket通知
        push_workflow_update(project_id, step_number, result)
        
        return result
    except Exception as exc:
        # 记录错误并重试
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

# tasks/agent_tasks.py

@celery_app.task(bind=True, max_retries=3)
def execute_agent_task(self, task_id: str, agent_id: str, 
                       task_data: dict):
    """
    执行Agent任务
    - 调用Gateway API
    - 收集执行结果
    - 提交QA检验
    """
    pass

# tasks/qa_tasks.py

@celery_app.task
def perform_qa_inspection(task_id: str, artifact_data: dict):
    """
    执行QA检验
    - 加载检验维度
    - 逐项检验
    - 计算综合评分
    - 判定合格/不合格
    """
    pass

# tasks/gitea_tasks.py

@celery_app.task
def commit_artifact_to_repo(task_id: str, qa_record_id: str, 
                           files: list):
    """
    提交产出到Gitea代码库
    - 创建分支
    - 添加文件
    - 提交 (Conventional Commits)
    - 创建PR
    """
    pass
```

---

## 7. 错误处理

### 7.1 统一异常处理

```python
# exceptions.py

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证错误"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "Request validation failed",
            "details": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "Internal server error",
            "trace_id": get_trace_id()
        }
    )
```

### 7.2 业务异常

```python
class DevFlowError(Exception):
    """DevFlow业务异常基类"""
    def __init__(self, code: int, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details

class ProjectNotFoundError(DevFlowError):
    def __init__(self, project_id: str):
        super().__init__(404, f"Project not found: {project_id}")

class AgentBusyError(DevFlowError):
    def __init__(self, agent_id: str):
        super().__init__(409, f"Agent is busy: {agent_id}")

class QAFailedError(DevFlowError):
    def __init__(self, task_id: str, score: float, dimensions: dict):
        super().__init__(
            400,
            f"QA inspection failed for task {task_id}",
            {"score": score, "dimensions": dimensions}
        )

class TaskTimeoutError(DevFlowError):
    def __init__(self, task_id: str):
        super().__init__(504, f"Task execution timeout: {task_id}")
```

---

## 8. 性能优化

### 8.1 数据库查询优化

```python
# 使用异步查询
async def get_project_with_related(project_id: str):
    """预加载相关数据，避免N+1查询"""
    return await Project.get(project_id).options(
        selectinload(Project.tasks),
        selectinload(Project.qa_records),
        selectinload(Project.group)
    )

# 数据库索引
CREATE INDEX idx_projects_creator_id ON projects(creator_id);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_qa_records_task_id ON qa_records(task_id);
CREATE INDEX idx_group_messages_group_id ON group_messages(group_id);
CREATE INDEX idx_group_messages_timestamp ON group_messages(timestamp);
```

### 8.2 Redis 缓存

```python
# 缓存项目进度
async def get_project_progress_cached(project_id: str):
    cache_key = f"project:progress:{project_id}"
    
    # 尝试从缓存获取
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 缓存未命中，查询数据库
    progress = await get_project_progress(project_id)
    
    # 写入缓存 (5分钟TTL)
    await redis.setex(cache_key, 300, json.dumps(progress))
    
    return progress

# 缓存失效
async def invalidate_project_cache(project_id: str):
    pattern = f"project:*:{project_id}"
    async for key in redis.scan_iter(pattern):
        await redis.delete(key)
```

### 8.3 连接池

```python
# PostgreSQL连接池
engine = create_async_engine(
    Settings.DATABASE_URL,
    pool_size=20,           # 连接池大小
    max_overflow=80,        # 最大溢出连接数
    pool_timeout=30,        # 获取连接超时
    pool_recycle=1800,      # 连接回收时间 (30分钟)
    pool_pre_ping=True      # 连接前检查
)

# Redis连接池
redis_pool = ConnectionPool.from_url(
    Settings.REDIS_URL,
    max_connections=50
)
```

---

## 9. 部署配置

### 9.1 Docker 配置

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m devflow
USER devflow

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", 
     "--workers", "4", "--loop", "uvloop"]
```

### 9.2 环境变量配置

```bash
# .env
# 应用配置
APP_NAME=DevFlow
APP_ENV=production
DEBUG=false
SECRET_KEY=your-secret-key-here
API_VERSION=v1

# 数据库配置
DATABASE_URL=postgresql+asyncpg://devflow:password@postgres:5432/devflow

# Redis配置
REDIS_URL=redis://:password@redis:6379/0

# Gitea配置
GITEA_HOST=http://localhost:3000
GITEA_API_TOKEN=your-gitea-token
GITEA_USERNAME=devflow_bot
GITEA_DEFAULT_ORG=devflow

# Hermes Agent配置
HERMES_PROFILES_DIR=/home/user/.hermes/profiles
HERMES_GATEWAY_TIMEOUT=360

# JWT配置
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS配置
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# 监控配置
PROMETHEUS_ENABLED=true
OPENTELEMETRY_ENABLED=true
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
```

---

文档结束
