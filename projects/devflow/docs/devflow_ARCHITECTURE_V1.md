# DevFlow 架构设计文档 V1.0

**项目**: DevFlow 项目管理平台
**版本**: 1.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: 初稿

---

## 1. 系统架构概述

### 1.1 架构目标

DevFlow 采用分层微服务架构，核心设计理念：
- **职责单一**: 各层职责清晰分离，前端负责交互、后端负责业务逻辑、数据库负责持久化
- **高可用**: 通过容器化部署和负载均衡实现99.5%可用性
- **可扩展**: 模块化设计支持新增Agent类型和功能模块快速接入
- **可观测**: 全链路监控、日志、告警体系覆盖系统运行状态

### 1.2 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        人类用户 (Client)                                 │
│              浏览器 / 移动端 (需求/进度/群聊/会议)                        │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │ HTTP/HTTPS + WebSocket
┌───────────────────────────────────────▼─────────────────────────────────┐
│                          Nginx 反向代理                                  │
│              (静态资源 / SSL终止 / WebSocket代理 / 负载均衡)               │
└───────────────────────────────────────┬─────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────┐
│                      FastAPI 后端应用层 (DevFlow Server)                 │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 16步流程调度  │  │ Agent蜂群调度 │  │ QA门控检验   │  │ 群聊协作   │ │
│  │ 引擎模块     │  │ 管理模块     │  │ 引擎模块     │  │ 模块       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Profile扫描  │  │ Gateway通信  │  │ Gitea代码库  │  │ 通知推送   │ │
│  │ 同步模块     │  │ 客户端模块   │  │ 集成模块     │  │ 模块       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Celery 任务队列 (异步任务调度 / Agent执行编排)                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────────────┘
              │                    │                    │
   ┌──────────▼──────────┐ ┌──────▼───────┐ ┌─────────▼──────────┐
   │ Gitea REST API      │ │ Redis        │ │ Prometheus         │
   │ (代码托管服务)       │ │ (缓存/队列)  │ │ (指标采集)         │
   └─────────────────────┘ └──────────────┘ └────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              9个命名Agent角色 (独立Hermes Profile实例)                  │
│  海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华 (Gateway API通信)         │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              Agent蜂群层 (编程Agent集群)                               │
│  Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma  │
│  hermes子agent / pi-codeing-agent子agent                               │
└────────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼─────────────────────────────────────────────────────────┐
│              数据持久层                                                 │
│  PostgreSQL (主数据库) + 文件存储 (项目文件夹)                          │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.3 架构层次说明

| 层次 | 职责 | 技术选型 |
|------|------|----------|
| 表示层 | 用户界面交互、实时通信 | Vue 3 + Element Plus + WebSocket |
| 网关层 | 反向代理、SSL、负载均衡 | Nginx |
| 应用层 | 业务逻辑、任务调度、Agent协调 | FastAPI + Celery + asyncio |
| 集成层 | 代码托管、Agent通信、消息队列 | Gitea API + Hermes Gateway + Redis |
| 数据层 | 持久化存储、缓存 | PostgreSQL + Redis + 文件存储 |

---

## 2. 分层架构设计

### 2.1 表示层 (Presentation Layer)

**职责**: 用户界面渲染、事件处理、实时数据展示

**技术栈**:
- Vue 3 (Composition API + `<script setup>`)
- Element Plus (UI组件库)
- Pinia (状态管理)
- Vue Router 4 (路由管理)
- Vue I18n (国际化)
- WebSocket 客户端 (实时通信)

**核心模块**:
- 项目列表页
- 项目详情/进度页
- 16步流程可视化管理
- 项目讨论群聊天界面
- 会议模式界面
- Agent蜂群监控面板
- QA检验结果展示
- 系统管理后台

### 2.2 网关层 (Gateway Layer)

**职责**: 请求路由、SSL终止、静态资源服务、WebSocket代理

**配置**:
```nginx
upstream devflow_backend {
    server 127.0.0.1:8000;
}

upstream gitea {
    server 127.0.0.1:3000;
}

server {
    listen 443 ssl;
    server_name devflow.example.com;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://devflow_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://devflow_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /gitea/ {
        proxy_pass http://gitea;
    }
}
```

### 2.3 应用层 (Application Layer)

**职责**: 核心业务逻辑实现、任务编排、Agent协调

**技术栈**:
- FastAPI (Web框架，异步支持)
- Celery (分布式任务队列)
- SQLAlchemy 2.0 (ORM)
- Pydantic 2.0 (数据验证)

**核心模块划分**:

```
devflow/
├── api/                    # API路由层
│   ├── v1/
│   │   ├── auth.py         # 认证接口
│   │   ├── projects.py     # 项目管理接口
│   │   ├── agents.py       # Agent管理接口
│   │   ├── swarms.py       # 蜂群管理接口
│   │   ├── qa.py           # QA门控接口
│   │   ├── groups.py       # 群聊管理接口
│   │   ├── repos.py        # 代码库管理接口
│   │   └── hermes.py       # Gateway通信接口
│   └── websocket/
│       └── group_chat.py   # WebSocket群聊端点
├── core/                   # 核心业务层
│   ├── workflow/
│   │   ├── engine.py       # 16步流程调度引擎
│   │   ├── step_executor.py# 步骤执行器
│   │   └── dependency_graph.py # 任务依赖图管理
│   ├── agent/
│   │   ├── coordinator.py  # Agent协调器
│   │   ├── profile_scanner.py # Profile扫描同步
│   │   ├── gateway_client.py  # Hermes Gateway客户端
│   │   └── swarm_manager.py   # 蜂群管理器
│   ├── qa/
│   │   ├── inspector.py    # QA检验引擎
│   │   ├── dimensions.py   # 检验维度定义
│   │   └── scorer.py       # 量化打分引擎
│   ├── collaboration/
│   │   ├── group_manager.py# 群组管理
│   │   ├── discussion.py   # 讨论模式
│   │   └── meeting.py      # 会议模式
│   ├── gitea/
│   │   ├── client.py       # Gitea API客户端
│   │   ├── repo_manager.py # 仓库管理
│   │   └── branch_manager.py# 分支管理
│   └── notification/
│       └── push.py         # 通知推送
├── models/                 # 数据模型
├── schemas/                # Pydantic Schema
├── services/               # 业务服务层
├── tasks/                  # Celery异步任务
├── utils/                  # 工具函数
└── config/                 # 配置管理
```

### 2.4 集成层 (Integration Layer)

**职责**: 外部系统集成通信

**集成的外部系统**:

| 系统 | 通信方式 | 用途 |
|------|----------|------|
| Hermes Agent (9个命名角色) | HTTP REST + WebSocket (Gateway API) | Agent对话、任务执行 |
| Gitea | REST API | 代码仓库管理、Git操作 |
| 编程Agent蜂群 | REST API | 任务分发、进度上报、成果交付 |
| Prometheus | HTTP Push | 指标上报 |
| Jaeger | gRPC | 链路追踪上报 |

### 2.5 数据层 (Data Layer)

**职责**: 数据持久化、缓存、会话管理

| 组件 | 用途 | 配置 |
|------|------|------|
| PostgreSQL 14+ | 主数据库，存储项目、用户、任务、QA记录等 | 连接池: 20, 最大连接: 100 |
| Redis 6+ | 缓存、Celery Broker、WebSocket会话 | 内存: 2GB, 持久化: AOF |
| 文件存储 | 项目文件夹、文档、报告 | /DevFlow/projects/ |

---

## 3. 模块设计

### 3.1 16步流程调度引擎

**职责**: 编排16步标准流程的执行顺序和状态管理

**核心类**:
```python
class WorkflowEngine:
    """16步流程调度引擎"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.current_step: int = 1
        self.step_status: Dict[int, StepStatus] = {}
    
    async def execute_step(self, step_number: int, agent_id: str, 
                          input_data: dict) -> StepResult:
        """执行指定步骤"""
        pass
    
    def get_dependency_graph(self) -> DirectedAcyclicGraph:
        """获取任务依赖图"""
        pass
    
    def check_step_prerequisites(self, step_number: int) -> bool:
        """检查步骤前置条件是否满足"""
        pass

class StepExecutor:
    """步骤执行器"""
    
    async def execute(self, step: int, context: ExecutionContext) -> Result:
        """
        执行流程:
        1. 海梅分派任务给对应Agent
        2. Agent执行任务
        3. 后荣进行QA检验
        4. 检验合格提交代码库
        5. 检验不合格退回重做
        """
        pass
```

**状态机**:
```
Step 1 (人类创建) → Step 2 (海梅确认) → Step 3 (需求分析)
    → Step 4 (架构设计) → Step 5 (环境搭建) → Step 6 (TDD计划)
    → Step 7 (TDD用例) → Step 8 (代码计划) → Step 9 (功能代码)
    → Step 10 (测试部署) → Step 11 (全面测试) → Step 12 (安全审计)
    → Step 13 (生产部署) → Step 14 (文档完善) → Step 15 (交付报告)
    → Step 16 (满意度确认) → [满意: 完成 / 不满意: 回到Step 3]
```

### 3.2 Agent蜂群调度模块

**职责**: 管理蜂群Agent的生命周期、任务分发、负载均衡

**核心类**:
```python
class SwarmManager:
    """蜂群管理器"""
    
    def __init__(self, project_id: str, manager_agent: str, 
                 purpose: SwarmPurpose):
        self.project_id = project_id
        self.manager_agent = manager_agent  # 后发或后达
        self.purpose = purpose  # code_writing / test
        self.members: List[SwarmAgent] = []
    
    async def create_swarm(self, task_count: int) -> Swarm:
        """创建蜂群并选择合适的Agent"""
        pass
    
    async def dispatch_task(self, task: Task) -> Assignment:
        """
        任务分发策略:
        1. 根据任务类型匹配技能
        2. 选择负载最低的匹配Agent
        3. 发送任务到Agent
        4. 监控执行进度
        """
        pass
    
    def get_load_balanced_agent(self, required_skills: List[str]) -> SwarmAgent:
        """负载均衡选择Agent"""
        pass
```

**Agent选择策略**:
1. 技能匹配度优先
2. 当前负载最低优先
3. 同类型Agent优先
4. 备用Agent选择: 技能匹配度≥80%

### 3.3 QA门控检验引擎

**职责**: 执行自动化QA检验，量化打分，判定合格/不合格

**核心类**:
```python
class QAInspector:
    """QA检验引擎"""
    
    def __init__(self):
        self.dimensions: Dict[str, InspectionDimension] = {}
    
    async def inspect(self, artifact: Artifact, step: int) -> InspectionResult:
        """
        检验流程:
        1. 根据产出类型加载检验维度
        2. 逐项执行量化检验
        3. 计算综合评分
        4. 判定合格/不合格
        5. 生成检验报告
        """
        pass

class ScoringEngine:
    """打分引擎"""
    
    def calculate_composite_score(self, dimension_scores: List[float], 
                                  weights: List[float] = None) -> float:
        """
        score = Σ(维度_i得分 × 权重_i) / Σ(权重_i)
        默认各维度权重均等
        """
        pass
```

### 3.4 项目讨论群协作模块

**职责**: 管理群组、讨论模式、会议模式

**核心类**:
```python
class GroupManager:
    """群组管理器"""
    
    async def create_group(self, project_id: str) -> Group:
        """第二步自动创建项目讨论群"""
        pass
    
    async def add_members(self, group_id: str, 
                         agents: List[str], users: List[str]) -> None:
        """添加群组成员"""
        pass

class DiscussionMode:
    """讨论模式"""
    
    async def send_message(self, group_id: str, sender_id: str, 
                          sender_type: str, content: str, 
                          mentions: List[str]) -> Message:
        """发送消息并触发@mention回复"""
        pass

class MeetingMode:
    """会议模式"""
    
    async def start_meeting(self, group_id: str, host_agent: str,
                           meeting_type: str, agenda: List[str]) -> Meeting:
        """启动结构化会议"""
        pass
```

### 3.5 Hermes Gateway通信模块

**职责**: 与9个命名Agent角色的Gateway API通信

**核心类**:
```python
class GatewayClient:
    """Hermes Gateway客户端"""
    
    def __init__(self, agent_profile: str, port: int):
        self.base_url = f"http://localhost:{port}"
        self.semaphore = asyncio.Semaphore(5)  # 并发控制
    
    async def chat(self, messages: List[Message], 
                   stream: bool = False) -> Response:
        """与Agent对话"""
        pass
    
    async def chat_stream(self, messages: List[Message]) -> AsyncGenerator:
        """流式对话 (SSE)"""
        pass

class ProfileScanner:
    """Profile扫描器"""
    
    def scan_profiles(self, profiles_dir: str) -> List[ProfileInfo]:
        """
        扫描 ~/.hermes/profiles/ 目录
        返回所有可用的Agent Profile信息
        """
        pass
```

---

## 4. 部署架构

### 4.1 容器化部署

**Docker Compose 编排**:

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./frontend/dist:/usr/share/nginx/html
    depends_on:
      - backend

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - DATABASE_URL=postgresql://devflow:password@postgres:5432/devflow
      - REDIS_URL=redis://redis:6379/0
      - GITEA_URL=http://gitea:3000
    depends_on:
      - postgres
      - redis
    volumes:
      - /DevFlow/projects:/DevFlow/projects

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://devflow:password@postgres:5432/devflow
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - postgres

  celery-beat:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    depends_on:
      - redis

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=devflow
      - POSTGRES_USER=devflow
      - POSTGRES_PASSWORD=devflow_password
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  gitea:
    image: gitea/gitea:latest
    environment:
      - DATABASE_TYPE=postgres
      - DATABASE_HOST=postgres:5432
      - DATABASE_NAME=gitea
      - DATABASE_USER=gitea
      - DATABASE_PASSWD=gitea_password
    volumes:
      - gitea_data:/data
    ports:
      - "3000:3000"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"

volumes:
  pg_data:
  redis_data:
  gitea_data:
  prometheus_data:
```

### 4.2 Hermes Agent 部署

9个命名Agent角色采用独立Profile部署:

| Agent | Profile | Gateway端口 | 模型 |
|-------|---------|-------------|------|
| 海梅 | haimei | 8765 | gpt-4o |
| 后兴 | houxing | 8766 | gpt-4o |
| 后旺 | houwang | 8767 | gpt-4o |
| 后发 | houfa | 8768 | gpt-4o |
| 后达 | houda | 8769 | gpt-4o |
| 后富 | houfl | 8770 | gpt-4o |
| 后贵 | hougui | 8771 | gpt-4o |
| 后荣 | houro | 8772 | gpt-4o |
| 后华 | houhua | 8773 | gpt-4o |

### 4.3 资源需求

| 组件 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| FastAPI后端 | 2核 | 4GB | 5GB |
| PostgreSQL | 2核 | 4GB | 50GB |
| Redis | 1核 | 2GB | 5GB |
| Gitea | 1核 | 2GB | 50GB |
| Celery Worker | 2核 | 4GB | 5GB |
| Nginx | 1核 | 512MB | 1GB |
| Prometheus | 1核 | 2GB | 20GB |
| Jaeger | 1核 | 2GB | 10GB |
| **总计** | **11核** | **25.5GB** | **146GB** |

### 4.4 网络拓扑

```
┌─────────────────────────────────────────────────────┐
│                    外部网络                           │
│              (人类用户 / 编程Agent)                   │
└───────────────────────────┬─────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │    Nginx      │
                    │  (443/80)     │
                    └───────┬───────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│                  内部网络 (Docker Network)            │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ FastAPI  │  │ Celery   │  │  Redis   │         │
│  │ :8000    │  │ Worker   │  │ :6379    │         │
│  └────┬─────┘  └────┬─────┘  └──────────┘         │
│       │              │                              │
│  ┌────▼──────────────▼──────────┐                  │
│  │        PostgreSQL :5432      │                  │
│  └──────────────────────────────┘                  │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Gitea   │  │Prometheus│  │  Jaeger  │         │
│  │ :3000    │  │ :9090    │  │ :16686   │         │
│  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│              Hermes Agent (宿主机)                   │
│  8个Agent通过Gateway API与后端通信                   │
│  端口范围: 8765-8773                                 │
└─────────────────────────────────────────────────────┘
```

---

## 5. 容灾与高可用

### 5.1 备份策略

| 数据 | 频率 | 保留 | 存储位置 |
|------|------|------|----------|
| PostgreSQL | 每日全量 + 每6h增量 | 30天/90天/365天 | /data/backups/ |
| 文件存储 | 每日全量 | 30天 | /data/backups/ |
| Gitea | Git历史 + 每日归档 | 永久 | 内置 + /data/backups/ |

### 5.2 恢复目标

- **RTO** (恢复时间目标): < 2小时
- **RPO** (恢复点目标): < 1小时

### 5.3 健康检查

```python
@app.get("/health")
async def health_check():
    """系统健康检查"""
    checks = {
        "postgres": await check_postgres(),
        "redis": await check_redis(),
        "gitea": await check_gitea(),
        "hermes_agents": await check_hermes_agents(),
        "celery": await check_celery(),
    }
    return {"status": "healthy" if all(checks.values()) else "degraded",
            "checks": checks}
```

---

## 6. 安全架构

### 6.1 认证与授权

- **认证**: JWT Token (Access Token 30分钟 + Refresh Token 7天)
- **授权**: RBAC (基于角色的访问控制)
- **项目隔离**: 用户仅可访问自身创建的项目

### 6.2 数据传输

- 全站 HTTPS (TLS 1.3)
- WebSocket wss:// 加密
- Agent通信数据脱敏存储

### 6.3 审计日志

所有关键操作记录日志:
- Agent任务分派
- QA检验结果
- 代码提交
- 错误和异常
- 用户登录/登出

---

## 7. 性能设计

### 7.1 性能指标目标

| 指标 | 目标值 | 测试方法 |
|------|--------|----------|
| 页面加载 | < 2秒 | Lighthouse 3次平均 |
| API响应 | < 3秒 (P95) | curl 10次请求 |
| 蜂群任务分发 | < 500ms | 接口计时 |
| QA检验处理 | < 1分钟/产出 | 计时统计 |
| 数据库查询 | < 100ms | pg_stat_statements |
| 群聊消息延迟 | < 100ms | WebSocket端到端 |

### 7.2 并发处理

- **并发项目数**: 20个
- **Agent并发限制**: 同Profile同一时间仅执行1个任务
- **WebSocket并发**: 单群组支持10+ Agent在线
- **API并发**: 信号量限制5个/Agent

### 7.3 缓存策略

| 缓存内容 | TTL | 存储 |
|----------|-----|------|
| 用户Session | 30分钟 | Redis |
| 项目进度 | 5分钟 | Redis |
| Agent状态 | 1分钟 | Redis |
| 群聊消息 | 24小时 | Redis + PostgreSQL |
| 静态资源 | 1年 | Nginx + 浏览器 |

---

## 8. 监控与可观测性

### 8.1 指标采集 (Prometheus)

- **系统级**: CPU/内存/磁盘/网络 (30秒间隔)
- **应用级**: API响应时间/QPS/错误率 (10秒间隔)
- **Agent级**: 任务时长/成功率/负载 (30秒间隔)
- **业务级**: 项目数/QA通过率/步骤耗时 (实时)

### 8.2 链路追踪 (Jaeger)

- 每个Agent任务分配唯一Trace ID
- 追踪全链路: 分派→执行→检验→提交
- 保留7天

### 8.3 日志管理 (ELK Stack)

- JSON结构化日志
- 本地保留30天 + ELK保留90天
- 关键操作必记日志

### 8.4 告警规则

| 告警类型 | 条件 | 通知方式 |
|----------|------|----------|
| CPU告警 | >85% 持续5分钟 | WebSocket + 邮件 |
| 内存告警 | >90% 持续3分钟 | WebSocket + 邮件 |
| API错误率 | >5% | WebSocket + 邮件 |
| Agent宕机 | 进程停止 | WebSocket + 邮件 |
| 任务超时 | >30分钟 | WebSocket + 邮件 |

---

文档结束
