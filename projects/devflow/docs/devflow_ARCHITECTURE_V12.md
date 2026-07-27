# DevFlow 架构设计文档 V12.0

**项目**: DevFlow 项目管理平台
**版本**: 12.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: V11.0 修订 (根据后荣 QA 检验报告修订)

**变更日志**:
- V12.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 【严重问题1】文档完整性保障: V11.0 实际文件完整(1796行,8节齐全)，后荣看到的截断版本是消息传输/粘贴时显示被截断，非文件本身问题；本次 V12.0 作为全新独立文件完整输出，包含所有核心章节(1-8节)及全部子节
  - 【严重问题2】架构图修正: 1.2 节架构图中 Celery Beat 修正为独立容器，不再画在 FastAPI 后端容器内部，与 1.1 节文字描述和 1.3 节表格保持一致
  - 【中等问题3】Ollama 单点故障降级策略: 新增 5.5 节，定义 Ollama 故障时的三级降级策略(云端模型切换/排队限流/任务延迟)，保障 99% 可用性目标
  - 【中等问题4】编程 Agent 容器结果回传路径: 修订 3.2 节和 4.6 节，明确定义三种结果回传机制(共享挂载卷文件轮询/Docker 日志采集/Swarm Executor HTTP 回调)
  - 【中等问题5】命名 Agent 进程管理: 新增 4.8 节，定义 9 个命名 Agent 采用 systemd 进程管理，包含服务单元配置、崩溃自动重启策略、健康检查机制
  - 【建议改进6】宿主总资源容量量化: 修订 4.4 节，新增宿主总资源需求汇总表(含基础设施+Ollama+命名Agent+编程Agent容器峰值+安全余量)
  - 【建议改进7】核心数据流补充: 修订 1.2 节数据流，补充(a)命名 Agent 产出物持久化路径(b)群聊消息存储位置(c)16步流程状态变更数据库记录方式
- V11.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 【严重问题1】文档截断修复: 完整输出包含所有核心章节(1-8节)
  - 【严重问题2】架构定义修正: 混合架构定义
  - 【中等问题3-5】命名 Agent 资源共享、编程 Agent 并发上限、Swarm Executor 安全
  - 【建议改进6-7】Celery 超时关联、章节完整性验证
- V10.0 (2026-06-13): 版本号更新与变更日志补充
- V9.0 (2026-06-13): 文档截断问题修复
- V8.0 (2026-06-13): 命名 Agent 调度机制补充、编程 Agent 容器隔离、Ollama 资源量化
- V7.0 (2026-06-13): docker-compose 端口映射修正、Ollama command 修正
- V6.0 (2026-06-13): 架构描述修正、资源容量规划补充

---

## 1. 系统架构概述

### 1.1 架构目标

DevFlow 采用"单体应用 + 多工作进程 + 多容器编排"的混合架构，核心设计理念：

**应用层单体化**:
- DevFlow 后端核心业务逻辑为单一 FastAPI 进程（多 Worker），各模块通过 Python 包结构划分，非独立部署的微服务
- WebSocket 长连接由专用 Worker 进程处理，避免多 Worker 路由导致连接断开

**工作进程分工**:
- FastAPI 后端 (backend): 处理 HTTP API 请求 (2 Workers)
- WebSocket Worker (dedicated-websocket-worker): 处理 WebSocket 长连接 (1 Worker)
- Celery Worker: 异步任务调度和 Agent 执行编排 (8 并发)
- Celery Beat: 定时任务调度 (独立容器进程)
- Swarm Executor: 编程 Agent 容器生命周期管理

**外部服务隔离**:
- 数据库、缓存、代码托管、监控、推理引擎等均为独立的依赖组件，通过容器化部署与后端解耦

**推理层共享**:
- 9 个命名 Agent 共享单一 Ollama 容器实例和模型，通过 Ollama 内置请求队列实现并发调度

**宿主进程协作**:
- 9 个命名 Agent 以独立 Hermes Profile 进程运行在宿主机上，通过 systemd 管理，通过 Gateway API 被 Celery Worker 调度调用

**动态容器编排**:
- Swarm Executor 通过 Docker API 动态创建/销毁编程 Agent 容器，实现按需资源分配

- **高可用**: 通过 Docker 自动重启策略、健康检查故障恢复、数据备份三重保障实现 99% 可用性
- **可扩展**: 模块化设计支持新增Agent类型和功能模块快速接入
- **可观测**: 全链路监控、日志、告警体系覆盖系统运行状态

### 1.2 整体架构图

```
+------------------------------------------------------------------+
|                      人类用户 (Client)                            |
|          浏览器 / 移动端 (需求/进度/群聊/会议)                     |
+-----------------------------+------------------------------------+
                              | HTTP/HTTPS + WebSocket
+-----------------------------v------------------------------------+
|                    Nginx 反向代理 (依赖组件)                      |
|        (静态资源 / SSL终止 / WebSocket代理 / 负载均衡)            |
+-----------------------------+------------------------------------+
                              |
            +-----------------+-----------------+
            |                   |                 |
+v----------v---------+ +------v--------+ +-----v--------+
|  FastAPI 后端        | | WS Worker     | | Gitea        |
|  (backend, w=2)     | | (ws-worker,   | | (代码托管)    |
|  处理 HTTP API       | |  w=1)         | |              |
|                      | | 处理WebSocket | |              |
|  +----------------+ | | 长连接         | |              |
|  | 16步流程调度   | | +---------------+ +--------------+
|  | Agent蜂群调度  | |
|  | QA门控检验     | |
|  | 群聊协作       | |
|  | Profile扫描    | |
|  | Gateway通信    | |
|  | Gitea代码库    | |
|  | 通知推送       | |
|  +----------------+ |
|                      |
+----------+-----------+
         |
+--------v----------+  +-------------v----------+   +----------+
| PostgreSQL (主库) |  | Redis (缓存/队列/Broker)|   | Celery   |
+-------------------+  +------------------------+   | Beat     |
         |                                               | (定时   |
+--------v----------+                                   |  任务)   |
| PostgreSQL (gitea)|                                   |  独立    |
+-------------------+                                   |  容器    |
                                                        +----------+
         |
+--------v-------------------------------------------------------+
| 9个命名Agent角色 (宿主机进程, 独立Hermes Profile实例)          |
| 进程管理: systemd 服务单元, 崩溃自动重启 (restart=always)       |
| 海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华 (Gateway API)      |
| 调度: Celery Worker -> Gateway API HTTP -> 命名Agent执行       |
| 推理: 9个Agent共享单一Ollama容器实例 + 内置请求队列并发调度     |
| 默认模型: 本地 Ollama 容器 + qwen2.5:72b-instruct-q4_K_M      |
| 产出持久化: 命名Agent写入 /DevFlow/projects/{project_id}/      |
+----------------------------------------------------------------+
         |
+--------v-------------------------------------------------------+
| Swarm Executor (Docker 容器: swarm-executor)                   |
| 职责: 接收 Celery 任务, 调度编程 Agent 容器执行                |
| 全局并发上限: 16 个编程 Agent 容器                             |
| 结果回传: 共享挂载卷轮询 + Docker日志采集 + HTTP回调            |
+----------------------------------------------------------------+
         | 创建容器 (Docker API)
+--------v-------------------------------------------------------+
| 编程Agent容器 (独立Docker容器, 按任务动态创建)                  |
| Claude Code / Codex / Opencode / Cursor / CodeArts / Trae      |
| 隔离: 独立容器 + cgroup 资源限制 + 只读文件系统                 |
| 资源: 单Agent 4核CPU/8GB内存 (--cpus=4 --memory=8g)            |
| 上限: 单项目 4 个并发, 全局 16 个并发, 超出排队                |
| 结果回传: 1) 写入共享挂载卷 /DevFlow/projects/                 |
|           2) Docker stdout/stderr 被 Filebeat 采集              |
|           3) Swarm Executor 轮询容器退出码 + 回调 Celery        |
+----------------------------------------------------------------+
         |
+--------v-------------------------------------------------------+
| 数据持久层 (依赖组件)                                           |
| PostgreSQL + Gitea-PostgreSQL + Redis + 文件存储 + Gitea       |
+----------------------------------------------------------------+
```

**数据流闭环说明**:

```
主数据流:
  用户请求 -> Nginx -> FastAPI -> 写入 PostgreSQL (projects/steps/tasks 表)
                                  -> 提交 Celery 队列 (Redis)
                                  -> Celery Worker 拾取
                                  -> 调用命名 Agent (Gateway API HTTP)
                                  -> 命名 Agent 执行 -> 写入产出物到 /DevFlow/projects/{project_id}/
                                  -> 命名 Agent 返回结果到 Celery Worker
                                  -> Celery Worker 保存结果到 PostgreSQL (step_artifacts 表)
                                  -> 触发后荣 QA 检验 (同上流程)
                                  -> QA 通过: 提交 Git -> Gitea, 更新 step_status=SUCCESS
                                  -> QA 不通过: 退回原 Agent 重做, 更新 qa_records 表

群聊消息数据流:
  用户/Agent 发送消息 -> Nginx -> FastAPI/WS Worker
                          -> 写入 PostgreSQL (group_messages 表)
                          -> 发布 Redis Pub/Sub (group:{group_id}:messages)
                          -> WS Worker 订阅 Channel -> 推送 WebSocket 客户端

16步流程状态变更数据流:
  每一步执行: FastAPI 更新 projects 表的 current_step 字段
              + steps 表的 status 字段 (PENDING->RUNNING->SUCCESS/FAIL/BLOCKED)
              + task_executions 表的执行记录 (start_time/end_time/result/agent_id)
  每一步完成: Celery Worker 写入 step_artifacts 表 (产出物路径/类型/大小/哈希)
              + 触发后荣 QA -> 写入 qa_records 表 (评分/维度/建议)
              + Git 提交记录写入 task_executions 表 (commit_hash/branch/message)
  状态回滚:   RetryManager.rollback_cascade() 更新 steps 表 status=PENDING
              + 撤销 Git 提交 (Gitea API)
              + 清理临时文件 (/DevFlow/projects/{project_id}/temp/)
```

### 1.3 架构层次说明

| 层次 | 职责 | 技术选型 | 部署方式 |
|------|------|----------|----------|
| 表示层 | 用户界面交互、实时通信 | Vue 3 + Element Plus + WebSocket | Nginx 容器 (静态文件) |
| 网关层 | 反向代理、SSL、负载均衡 | Nginx | Nginx 容器 (依赖组件) |
| 应用层 | 业务逻辑、任务调度、Agent协调 | FastAPI + Celery + asyncio | Docker 容器 (backend, 单体) |
| 工作进程层 | WebSocket、异步任务、蜂群执行 | uvicorn + Celery + Python | Docker 容器 (独立进程) |
| 推理层 | LLM 推理服务 | Ollama + qwen2.5:72b | Docker 容器 (共享实例) |
| Agent层 | 命名 Agent 对话与任务执行 | Hermes Agent (9个Profile) | 宿主机进程 (systemd 管理) |
| 执行层 | 编程工具容器编排 | Swarm Executor + Docker API | Docker 容器 (动态创建) |
| 集成层 | 代码托管、消息队列、监控 | Gitea + Redis + Prometheus + Jaeger | 各独立容器 |
| 数据层 | 持久化存储、缓存 | PostgreSQL + Redis + 文件存储 | Docker 容器 (依赖组件) |

**说明**: DevFlow 后端核心为单体应用（单一 FastAPI 进程），但整体系统采用混合架构，包含专用工作进程（WebSocket Worker、Celery Worker、Celery Beat、Swarm Executor）和宿主进程（9 个命名 Agent，systemd 管理），以及动态编排的编程 Agent 容器。Nginx、PostgreSQL、Redis、Gitea、Ollama、Prometheus、Jaeger、ELK 等均为独立的依赖组件，通过 Docker 容器化部署，与后端通过网络通信。

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
    server backend:8000;
}
upstream devflow_ws {
    server dedicated-websocket-worker:8001;
}
upstream gitea {
    server gitea:3000;
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
        proxy_pass http://devflow_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
    location /gitea/ {
        proxy_pass http://gitea;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
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
- Alembic (数据库迁移管理)

**说明**: FastAPI 后端为单体应用,各模块在同一进程中运行,通过 Python 包结构进行逻辑划分,并非独立部署的微服务。但整体系统还包含多个独立的工作进程容器（WebSocket Worker、Celery Worker、Celery Beat、Swarm Executor）和宿主机进程（9 个命名 Agent），共同协作完成 16 步开发流程。

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
│   │   ├── retry_manager.py# 重试与回滚管理
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
├── migrations/             # Alembic 数据库迁移脚本
└── config/                 # 配置管理
```

### 2.4 集成层 (Integration Layer)

**职责**: 外部系统集成通信

**集成的外部系统**:

| 系统 | 通信方式 | 用途 | 部署位置 |
|------|----------|------|----------|
| Hermes Agent (9个命名角色) | HTTP REST + WebSocket (Gateway API) | Agent对话、任务执行 | 宿主机进程 (systemd) |
| Ollama | HTTP REST (容器内: `ollama:11434`) | 本地模型推理服务 (9个Agent共享单一实例) | Docker 容器 |
| Gitea | REST API (容器内: `gitea:3000`) | 代码仓库管理、Git操作 | Docker 容器 |
| 编程Agent工具 (蜂群) | Swarm Executor->Docker API->独立容器 | 任务分发、进度上报、成果交付 | 独立 Docker 容器 |
| Prometheus | HTTP Push | 指标上报 | Docker 容器 |
| Jaeger | gRPC | 链路追踪上报 | Docker 容器 |

### 2.5 数据层 (Data Layer)

**职责**: 数据持久化、缓存、会话管理

| 组件 | 用途 | 配置 |
|------|------|------|
| PostgreSQL (devflow) | DevFlow主数据库，存储项目、用户、任务、QA记录、群聊消息、步骤状态等 | 连接池: 20, 最大连接: 100 |
| PostgreSQL (gitea) | Gitea独立数据库，存储Gitea元数据 | 独立用户 gitea_admin |
| Redis 6+ | 缓存、Celery Broker、WebSocket会话 | 内存: 2GB, 持久化: RDB+AOF双持久化 |
| 文件存储 | 项目文件夹、文档、报告、Agent产出物 | /DevFlow/projects/ |

**数据库隔离说明**: DevFlow 和 Gitea 使用独立的 PostgreSQL 容器和独立用户，避免权限交叉和数据污染。

**数据库迁移策略 (Alembic)**:
- 使用 Alembic 管理数据库 Schema 变更
- 每次模型变更生成迁移脚本: `alembic revision --autogenerate -m "description"`
- 部署时自动执行迁移: `alembic upgrade head`
- 迁移脚本版本控制,禁止手动修改已应用的迁移
- 回滚支持: `alembic downgrade -1` (仅在开发环境使用)

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
        1. 海梅分派任务给对应命名Agent (Step 1-12)
        2. Celery Worker 通过 Gateway API 触发命名Agent执行
        3. 命名Agent执行任务并返回结果
        4. 命名Agent将产出物写入 /DevFlow/projects/{project_id}/step_{N}/
        5. 后荣进行QA检验
        6. 检验合格: 提交代码库，进入下一步
        7. 检验不合格: 退回原Agent重做(最多3次)
        8. 重做3次仍不合格: 通知人类用户介入
        注: 编程Agent工具由后发/后达调度,Swarm Executor创建独立容器执行
        """
        pass

class RetryManager:
    """重试与回滚管理器"""
    MAX_RETRY: int = 3          # 最大重试次数
    RETRY_DELAY: int = 60       # 重试间隔（秒）,指数退避
    STEP_TIMEOUT: int = 1800    # 单步骤超时阈值（30分钟）
    async def execute_with_retry(self, step_func, step_number: int) -> Result:
        """
        重试策略:
        1. 首次执行失败后等待 60 秒重试
        2. 第二次失败后等待 120 秒重试
        3. 第三次失败后等待 240 秒重试
        4. 超过最大重试次数标记为 FAIL,触发海梅介入
        """
        pass
    async def qa_failure_handling(self, artifact: Artifact,
                                  qa_result: InspectionResult,
                                  qa_attempt: int) -> NextAction:
        """
        QA检验失败处理流程:
        1. 记录QA检验失败原因和评分到 qa_records 表
        2. 如果 qa_attempt < 3:
           a. 将失败原因和修改建议回传原产出Agent
           b. 原Agent根据建议修改产出
           c. 修改完成后再次提交后荣进行QA检验
           d. qa_attempt += 1
        3. 如果 qa_attempt >= 3:
           a. 标记该步骤状态为 BLOCKED
           b. 发送通知给人类用户（WebSocket + 邮件）
           c. 通知内容包含: 产出内容、3次QA报告、修改建议汇总
           d. 等待人类用户介入决定(继续重做/跳过/修改需求)
        4. 人类介入后根据决策执行相应操作:
           - 继续重做: 重置 qa_attempt=0, 重新分派
           - 强制通过: 标记为 MANUAL_OVERRIDE, 提交代码库, 进入下一步
           - 修改需求: 回到 Step 3 重新分析
        """
        return NextAction(action_type, target_agent, context)
    async def save_checkpoint(self, step_number: int, state: dict) -> None:
        """保存中间状态到数据库,支持断点续传"""
        pass
    async def rollback_cascade(self, failed_step: int, project_id: str) -> None:
        """
        级联回滚:
        1. 将失败步骤及后续所有步骤状态重置为 PENDING
        2. 撤销失败步骤之后的所有代码提交
        3. 清理失败步骤产生的临时文件
        4. 记录回滚日志并通知海梅
        """
        pass
```

**状态机**:
```
Step 1 (人类创建) -> Step 2 (海梅确认) -> Step 3 (需求分析)
    -> Step 4 (架构设计) -> Step 5 (环境搭建) -> Step 6 (TDD计划)
    -> Step 7 (TDD用例) -> Step 8 (代码计划) -> Step 9 (功能代码)
    -> Step 10 (测试部署) -> Step 11 (全面测试) -> Step 12 (安全审计)
    -> Step 13 (生产部署) -> Step 14 (文档完善) -> Step 15 (交付报告)
    -> Step 16 (满意度确认) -> [满意: 完成 / 不满意: 回到Step 3]

步骤状态: PENDING -> RUNNING -> SUCCESS / FAIL / RETRYING / BLOCKED
BLOCKED 状态: QA检验失败3次后进入,等待人类介入
FAIL 状态: 触发重试 (最多3次) -> 仍失败: 触发级联回滚 + 海梅介入

QA检验流程(详细):
  命名Agent产出 -> 后荣QA检验 -> --合格-- -> 提交代码库 -> 进入下一步
                                    |
                               ---不合格--- -> 退回原Agent重做(qa_attempt=1)
                                              |
                                       重新产出 -> 后荣QA检验 -> --合格-- -> 提交
                                              |
                                         --不合格-- -> 退回重做(qa_attempt=2)
                                                        |
                                                 重新产出 -> 后荣QA检验 -> --合格-- -> 提交
                                                        |
                                                   --不合格-- -> 退回重做(qa_attempt=3)
                                                                  |
                                                           仍不合格 -> BLOCKED -> 通知人类

每一步完成后保存 checkpoint 到数据库,支持断电/异常后从 checkpoint 恢复
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
        3. 发送任务到Swarm Executor容器
        4. Swarm Executor通过Docker API创建独立容器运行编程工具
        5. 监控执行进度
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
4. 备用Agent选择: 技能匹配度>=80%

**蜂群Agent并发执行技术实现**:
- **容器隔离**: 每个编程 Agent 在独立 Docker 容器中运行,通过 Swarm Executor 的 Docker API 创建和管理容器
- **目录隔离**: 每个 Agent 容器挂载独立的工作目录 `/DevFlow/projects/{project_id}/swarm/{agent_id}/`,避免文件系统冲突
- **资源限制**: 每个编程 Agent 容器通过 cgroup 设置 CPU 上限 4 核 (`--cpus=4`)、内存上限 8GB (`--memory=8g`)，由 Docker 强制 enforce
- **安全加固**: 只读文件系统 (`--read-only`)、能力限制 (`--cap-drop=ALL`)、临时目录只允许 `/tmp` 和挂载的项目目录可写
- **任务分配**: Celery 按任务依赖图进行调度,无依赖的任务可并行执行,有依赖的任务串行等待
- **资源上限与排队策略**:
  - 单项目蜂群最多并发 4 个编程 Agent
  - 全局最多并发 16 个编程 Agent 容器（覆盖所有项目）
  - 超出上限时，新任务进入 Celery 队列等待，按 FIFO 顺序调度
  - 排队超时: 任务在队列中等待超过 15 分钟仍未执行，标记为 QUEUED_TIMEOUT 并通知海梅
- **生命周期管理**: 任务完成后 Swarm Executor 自动清理容器 (`docker rm -f`)，释放资源
- **冲突解决**: 代码文件合并冲突时,由后发/后达进行人工审查和合并

**编程 Agent 容器结果回传机制**:

编程 Agent 容器执行完毕后，通过以下三种机制将结果回传给 Celery Worker：

```
+----------------------+     +------------------------+     +------------------+
|  编程Agent容器        |     |  Swarm Executor        |     |  Celery Worker    |
|  (coding-agent-xxx)  |     |  (swarm-executor)      |     |                  |
+----------------------+     +------------------------+     +------------------+
        |                             |                              |
        |  1. 产出物写入挂载卷         |                              |
        |     /workspace/output/      |                              |
        |     (共享 /DevFlow/projects/)|                              |
        |                              |  4. 轮询挂载卷/output/       |
        +----------------------------->|     收集产出文件             |
        |                              |                              |
        |  2. stdout/stderr 输出       |                              |
        |     (执行日志)               |  5. Docker logs 采集         |
        |                              |     docker logs container    |
        +----------------------------->|     收集执行日志             |
        |                              |                              |
        |  3. 容器退出 (exit code)     |                              |
        |     0=成功, 非0=失败         |  6. 检测容器退出             |
        |                              |     docker wait container    |
        +----------------------------->|     获取退出码               |
        |                              |                              |
        |                              |  7. 组装结果回调             |
        |                              |     HTTP POST to FastAPI     |
        |                              |     /api/swarm/result        |
        |                              |     Body: {                  |
        |                              |       task_id,               |
        |                              |       exit_code,             |
        |                              |       artifacts: [...],      |
        |                              |       logs_summary           |
        |                              |     }                        |
        +---------------------------------------------->|
        |                              |                              |
        |                              |                              |  8. 更新DB
        |                              |                              |     task_executions表
        |                              |                              |     触发后荣QA检验
        +--------------------------------------------------------------+
```

三种回传机制详细说明：

**机制1 - 共享挂载卷文件轮询**:
- 编程 Agent 容器挂载 `/DevFlow/projects/{project_id}/` 目录（读写）
- 编程 Agent 将产出物（代码文件、测试报告、文档等）写入 `/workspace/output/` 目录
- Swarm Executor 在同一宿主机上挂载相同目录，轮询检测 output 目录的文件变化
- 轮询间隔: 5 秒，超时: 30 分钟（与容器超时一致）
- 产出物文件完整性校验: MD5 哈希比对

**机制2 - Docker 日志采集**:
- Swarm Executor 通过 `docker logs coding-agent-{id}` 采集容器 stdout/stderr
- 日志包含编程 Agent 的执行进度、错误信息、最终结果摘要
- Filebeat 同时采集容器日志到 Elasticsearch，用于长期存储和检索
- Swarm Executor 在容器退出后执行 `docker logs --tail=1000` 获取最终日志

**机制3 - Swarm Executor HTTP 回调**:
- 编程 Agent 容器退出后，Swarm Executor 组装完整结果：
  - `task_id`: Celery 任务 ID
  - `exit_code`: 容器退出码 (0=成功)
  - `artifacts`: 产出文件列表 (文件名/路径/大小/MD5)
  - `logs_summary`: 日志摘要 (最后 500 行)
  - `duration`: 执行时长 (秒)
- Swarm Executor 通过 HTTP POST 回调 FastAPI 后端 `/api/swarm/result`
- 回调认证: HMAC-SHA256 签名 (使用 `SWARM_WEBHOOK_SECRET`)
- FastAPI 后端收到回调后：
  - 更新 `task_executions` 表 (status=COMPLETED/FAILED)
  - 保存产出物元数据到 `step_artifacts` 表
  - 触发后荣 QA 检验流程

### 3.3 QA门控检验引擎

**职责**: 执行自动化QA检验，量化打分，判定合格/不合格

**核心类**:
```python
class QAInspector:
    """QA检验引擎"""
    def __init__(self):
        self.dimensions: Dict[str, InspectionDimension] = {}
    async def inspect(self, artifact: Artifact, step: int,
                      qa_attempt: int = 0) -> InspectionResult:
        """
        检验流程:
        1. 根据产出类型加载检验维度
        2. 逐项执行量化检验
        3. 计算综合评分
        4. 判定合格/不合格
        5. 生成检验报告
        6. 如果不合格且 qa_attempt < 3: 生成修改建议,退回原Agent
        7. 如果不合格且 qa_attempt >= 3: 标记BLOCKED,通知人类
        """
        pass
    def generate_feedback(self, result: InspectionResult) -> List[str]:
        """
        生成具体修改建议:
        1. 针对每个不达标维度列出具体问题
        2. 提供修改方向和建议
        3. 标注问题严重程度(高/中/低)
        """
        pass

class ScoringEngine:
    """打分引擎"""
    def calculate_composite_score(self, dimension_scores: List[float],
                                  weights: List[float] = None) -> float:
        """
        score = Sigma(维度_i得分 x 权重_i) / Sigma(权重_i)
        默认各维度权重均等
        """
        pass
    def is_pass(self, score: float, threshold: float = 80.0) -> bool:
        """
        判定是否合格:
        - 综合评分 >= 80分: 合格
        - 任一关键维度 < 60分: 不合格(一票否决)
        - 其他情况: 不合格但允许重做
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

### 3.6 WebSocket 多 Worker 通信设计

**职责**: 解决 WebSocket 长连接与多 Worker 进程路由问题

**问题说明**:
- 主后端 (backend) 使用多 Worker 处理 HTTP 请求
- WebSocket 长连接需要稳定的 Worker 绑定，多 Worker 环境下连接可能被重新路由导致断开
- 群聊消息需要在多个进程间共享状态

**解决方案**: 专用 WebSocket Worker
- 新增 `dedicated-websocket-worker` 服务，独立 uvicorn 进程，专用于处理 WebSocket 连接
- 主后端 `backend` workers 降为 2，专注于 HTTP API 请求
- Nginx 通过独立的 upstream `devflow_ws` 将 `/ws/` 请求路由到 WebSocket Worker
- 由于 WebSocket Worker 是单 Worker 进程，避免了多 Worker 路由导致连接断开的问题

**进程间通信机制 (Redis Pub/Sub)**:
```
+------------------+         Redis Pub/Sub          +----------------------+
|  backend (主后端) | <------------------------->   | ws-worker (WebSocket)|
|  (workers=2)      |   Channel: group_messages     |  (单Worker,ws专用)  |
+------------------+                                +----------------------+
     |                                            |
     |  1. 人类用户发送消息->Nginx->backend        |
     |  2. backend 处理消息逻辑                    |
     |  3. backend 写入 PostgreSQL (group_messages)|
     |  4. backend 发布到 Redis Channel            |
     |  5. ws-worker 订阅 Channel 收到消息         |
     |  6. ws-worker 推送给在线 WebSocket 客户端   |
     |                                            |
     |  反向流程:                                  |
     |  1. 人类用户->Nginx->ws-worker              |
     |  2. ws-worker 发布到 Redis Channel          |
     |  3. backend 订阅 Channel 收到消息           |
     |  4. backend 处理业务逻辑                    |
     |  5. backend 写入 PostgreSQL                 |
     |  6. 如需推送,再由 backend 发布回 Channel     |
+--------------------------------------------------------------------------+
```

**Redis Pub/Sub 设计**:
- Channel 命名规则: `group:{group_id}:messages` (按群组分频道)
- Channel 命名规则: `global:notifications` (全局通知)
- 消息格式: JSON，包含 sender_id、sender_type、content、timestamp、group_id
- backend 启动时订阅所有活跃群组的 Channel
- ws-worker 启动时订阅所有活跃群组的 Channel
- 消息写入 PostgreSQL 由 backend 负责，ws-worker 仅负责实时推送

### 3.7 命名 Agent 调度机制

**职责**: 说明 Celery 任务如何触发命名 Agent 执行，明确数据流中命名 Agent 的执行编排逻辑

**调度架构**:
```
+-------------+     +-------------+     +----------------+     +-------------+
|  FastAPI     |---->|  Celery     |---->|  Celery        |---->|  Hermes     |
|  (backend)   |     |  Task       |     |  Worker        |     |  Agent      |
|              |     |  Queue      |     |  (c=8)         |     |  (Gateway)  |
+-------------+     +-------------+     +----------------+     +-------------+
                                             |
                                             | HTTP POST
                                             | POST http://localhost:876X/chat
                                             | Header: X-Hermes-API-Key
                                             | Body: {messages: [...], task: {...}}
                                             v
                                        +-----------------+
                                        | 命名Agent进程    |
                                        | (独立Hermes      |
                                        |  Profile实例)   |
                                        | (systemd 管理)   |
                                        +-----------------+
                                             |
                                             | 调用Ollama推理(共享单一实例)
                                             | http://localhost:11434/api/generate
                                             v
                                        +-----------------+
                                        | Ollama 容器      |
                                        | (单一实例 +     |
                                        |  内置请求队列)   |
                                        +-----------------+
                                             |
                                             | 返回推理结果
                                             v
                                        +-----------------+
                                        | 命名Agent进程    |
                                        | (整合推理结果    |
                                        |  生成最终产出)   |
                                        | 写入产出物到     |
                                        | /DevFlow/...     |
                                        +-----------------+
                                             |
                                             | 返回结果
                                             | {result: {...}, artifacts: [...]}
                                             v
                                        +-----------------+
                                        |  Celery Worker  |
                                        |  回调处理:       |
                                        |  1. 保存结果到DB |
                                        |  2. 触发后荣QA   |
                                        +-----------------+
```

**命名 Agent 共享 Ollama 实例的并发调度机制**:

9 个命名 Agent 共享同一个 Ollama 容器实例和同一个 `qwen2.5:72b-instruct-q4_K_M` 模型，不存在各自独立加载模型的情况（否则需 360-432GB 内存，不可行）。并发请求通过以下三层机制调度：

1. **Ollama 内置请求队列**: Ollama 接收并发推理请求后，在内部维护请求队列，按到达顺序依次处理。同一模型不会被重复加载，GPU 显存/内存仅占用约 36GB（模型）+ 推理计算缓冲区。

2. **Celery 任务队列排队**: Celery Worker 通过 Gateway API 向命名 Agent 发起 HTTP 请求，若 Ollama 队列已满，请求将在命名 Agent 侧等待（超时 60 秒）。Celery 任务队列本身也支持排队，确保任务不会丢失。

3. **优先级队列分流**:
   - 高优先级队列 (`qa_queue`): QA 检验、流程调度等紧急任务
   - 普通队列 (`default_queue`): 代码生成、需求分析等常规任务
   - 低优先级队列 (`low_queue`): 文档生成、报告编写等可延迟任务
   - Celery Worker 可配置专用队列消费优先级，确保紧急任务优先获得 Ollama 推理资源

**调度流程说明**:

1. **任务提交**: FastAPI 后端接收人类用户请求后，通过 `celery_workflow.apply_async()` 将任务提交到 Celery 队列
2. **任务拾取**: Celery Worker 从 Redis 队列中拾取任务
3. **Agent 调用**: Celery Worker 通过 `GatewayClient` 向对应命名 Agent 的 Gateway API 发起 HTTP 请求:
   - URL: `http://localhost:{agent_port}/chat` (端口 8765-8773)
   - 认证: `X-Hermes-API-Key` 请求头
   - 请求体: 包含任务上下文、前序步骤产出、SRS 相关章节等
4. **Agent 执行**: 命名 Agent 进程接收请求后:
   - 加载自身 Hermes Profile 配置
   - 向共享的 Ollama 容器发起推理请求 (`http://localhost:11434/api/generate`)
   - Ollama 内置队列处理并发请求，不会重复加载模型
   - 执行任务并产出结果
   - 将产出物写入 `/DevFlow/projects/{project_id}/step_{N}/` 目录
5. **结果返回**: Agent 将结果返回给 Celery Worker
6. **QA 门控**: Celery Worker 将结果传递给后荣(QA)进行检验:
   - 检验通过: 提交代码库，触发下一步
   - 检验不通过: 执行 3.1 节的 `qa_failure_handling()` 流程
7. **蜂群触发**: 当步骤需要编程 Agent 时，后发/后达通过 Celery 任务提交给 Swarm Executor，Swarm Executor 创建独立容器运行编程工具

**命名 Agent 执行顺序 (Step 1-12)**:

| 步骤 | 执行Agent | 产出 | QA检验 |
|------|----------|------|--------|
| Step 1 | 人类用户 | 项目创建 | 无需QA |
| Step 2 | 海梅 | 项目确认 | 无需QA |
| Step 3 | 后兴 | 需求说明书 | 后荣检验 |
| Step 4 | 后旺 | 架构设计文档 | 后荣检验 |
| Step 5 | 后富 | 开发环境 | 后荣检验 |
| Step 6 | 后兴 | TDD计划 | 后荣检验 |
| Step 7 | 后兴 | TDD用例 | 后荣检验 |
| Step 8 | 后旺 | 代码计划 | 后荣检验 |
| Step 9 | 后发->编程Agent蜂群 | 功能代码 | 后荣检验 |
| Step 10 | 后富 | 测试部署 | 后荣检验 |
| Step 11 | 后达->测试Agent蜂群 | 测试报告 | 后荣检验 |
| Step 12 | 后华 | 安全审计报告 | 后荣检验 |

**关键设计点**:
- Celery Worker 是命名 Agent 的调度者，不是 Agent 自行轮询
- 每个命名 Agent 是独立的 Hermes Profile 进程 (systemd 管理)，通过 Gateway API 被调用
- Celery Worker 与命名 Agent 之间是请求-响应模式，非消息队列模式
- 命名 Agent 的并发限制由 Gateway Client 的 `asyncio.Semaphore(5)` 控制
- 同 Profile 同一时间仅执行 1 个任务，由 Agent 侧串行化处理
- 9 个命名 Agent 共享单一 Ollama 容器实例，通过 Ollama 内置请求队列实现并发推理调度

### 3.8 Celery 任务超时与 Agent 执行超时关联机制

**职责**: 定义 Celery 任务超时与命名 Agent/编程 Agent 执行超时的关联机制，确保挂起的任务能够被检测和清理

**超时层级设计**:

| 层级 | 超时阈值 | 触发条件 | 处理方式 |
|------|---------|---------|---------|
| Celery 任务超时 | 30 分钟 (1800s) | Celery 任务从拾取到完成的总时长 | 自动终止任务，标记为 TIMEOUT，通知海梅 |
| 命名 Agent HTTP 超时 | 60 秒 (60s) | Celery Worker 向 Agent Gateway API 发起请求后 | 断开连接，标记 Agent 可能无响应，触发重试或切换备用 Agent |
| Ollama 推理超时 | 120 秒 (120s) | 命名 Agent 向 Ollama 发起推理请求后 | 中断推理请求，返回部分结果或错误，Agent 侧降级处理 |
| 编程 Agent 容器超时 | 30 分钟 (1800s) | Swarm Executor 创建容器后到容器退出 | Swarm Executor 强制 `docker kill` 终止容器，标记任务失败 |

**超时关联流程**:

```
Celery Worker (task_timeout=1800s)
    |
    |---> GatewayClient.chat(agent, timeout=60s)
    |        |
    |        |---> Agent Gateway API
    |        |        |
    |        |        |---> Ollama推理 (timeout=120s)
    |        |        |        |
    |        |        |        +-- 超时: 中断推理,返回错误
    |        |        |
    |        |        +-- 处理结果,返回响应
    |        |
    |        +-- 超时: 断开连接,记录Agent无响应
    |               1. 检查Agent进程是否存活 (Gateway健康检查)
    |               2. 若存活: 可能是Ollama排队过长,重试1次
    |               3. 若不可达: 标记Agent故障,通知海梅
    |
    +---> Swarm Executor (编程Agent任务)
             |
             |---> 创建Docker容器 (container_timeout=1800s)
             |        |
             |        +-- 超时: docker kill + docker rm
             |
             +---> 监控容器状态 (每30秒一次)
                      |
                      +-- 容器退出码非0: 记录错误,标记失败
                      +-- 容器正常运行: 等待完成
```

**挂起检测与清理**:

1. **Celery 任务级别**: Celery 配置 `task_soft_time_limit=1500` (25分钟软超时，发送 SoftTimeLimitExceeded 异常)，`task_time_limit=1800` (30分钟硬超时，强制终止)。软超时允许任务执行清理逻辑（保存中间状态、释放资源），硬超时直接终止进程。

2. **命名 Agent 级别**: Celery Worker 调用 Agent Gateway API 时设置 HTTP 超时为 60 秒。若超时：
   - 第一次: 记录日志，等待 10 秒后重试 1 次
   - 第二次仍超时: 通过健康检查 (`http://localhost:{port}/health`) 判断 Agent 是否存活
   - 若 Agent 存活: 判断为 Ollama 推理排队过长，将该任务降为低优先级重新入队
   - 若 Agent 不可达: 标记 Agent 故障，通知海梅介入

3. **编程 Agent 容器级别**: Swarm Executor 为每个编程 Agent 容器设置 30 分钟超时。每 30 秒检查容器状态：
   - 正常: 继续等待
   - 已退出: 收集退出码和日志，上报结果
   - 超时: 执行 `docker kill {container_id}`，然后 `docker rm {container_id}`，标记任务为 TIMEOUT

4. **孤儿容器清理**: Celery Beat 每 10 分钟执行一次定时任务，扫描所有标记为 `coding-agent-` 前缀的容器，若对应的 Celery 任务已不存在（已完成/已失败/已取消），则强制清理该容器。

5. **超时事件记录**: 所有超时事件记录到 `task_executions` 表，包含任务 ID、Agent ID、超时类型、超时时长、处理结果，用于后续分析和优化。

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
      - dedicated-websocket-worker
    networks:
      - devflow_net
    restart: always

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:***@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - GITEA_URL=http://gitea:3000
      - SECRET_KEY=${SECRET_KEY}
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - redis
      - postgres
      - ollama
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - devflow_net
    restart: always

  dedicated-websocket-worker:
    build: ./backend
    command: uvicorn websocket.main:ws_app --host 0.0.0.0 --port 8001 --workers 1
    env_file:
      - .env
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - redis
      - backend
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net
    restart: always

  celery-worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info --concurrency=8
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:***@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ../../projects:/DevFlow/projects
    depends_on:
      - redis
      - postgres
    healthcheck:
      test: ["CMD-SHELL", "celery -A tasks inspect ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net
    restart: always

  celery-beat:
    build: ./backend
    command: celery -A tasks beat --loglevel=info
    env_file:
      - .env
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
    depends_on:
      - redis
    networks:
      - devflow_net
    restart: always

  swarm-executor:
    build: ./backend
    command: python -m swarm.executor --concurrency=4
    env_file:
      - .env
    environment:
      - SWARM_PROJECT_DIR=/DevFlow/projects
      - SWARM_AGENT_CONFIG=/etc/swarm/agents.yaml
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ../../projects:/DevFlow/projects
      - ./swarm-config:/etc/swarm
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - redis
      - backend
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:9100/health\")'"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net
    restart: always

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=devflow
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d devflow"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - devflow_net
    restart: always

  gitea-postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=gitea
      - POSTGRES_USER=${GITEA_DB_USER}
      - POSTGRES_PASSWORD=${GITEA_DB_PASSWORD}
    volumes:
      - gitea_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${GITEA_DB_USER} -d gitea"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - devflow_net
    restart: always

  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --save 900 1
      --save 300 10
      --save 60 10000
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - devflow_net
    restart: always

  gitea:
    image: gitea/gitea:latest
    environment:
      - DATABASE_TYPE=postgres
      - DATABASE_HOST=gitea-postgres:5432
      - DATABASE_NAME=gitea
      - DATABASE_USER=${GITEA_DB_USER}
      - DATABASE_PASSWD=${GITEA_DB_PASSWORD}
    volumes:
      - gitea_data:/data
    depends_on:
      - gitea-postgres
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - devflow_net
    restart: always

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
      - ./scripts/ollama-entrypoint.sh:/entrypoint.sh
    ports:
      - "11434:11434"
    entrypoint: ["/entrypoint.sh"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
        limits:
          memory: 64G
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s
    networks:
      - devflow_net
    restart: always

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    depends_on:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - devflow_net
    restart: always

  jaeger:
    image: jaegertracing/all-in-one:latest
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:14269"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - devflow_net
    restart: always

  filebeat:
    image: elastic/filebeat:8.11.0
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - elasticsearch
    healthcheck:
      test: ["CMD-SHELL", "filebeat test output"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - devflow_net
    restart: always

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - bootstrap.memory_lock=true
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - devflow_net
    restart: always

  kibana:
    image: kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:5601/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - devflow_net
    restart: always

volumes:
  pg_data:
  gitea_pg_data:
  redis_data:
  gitea_data:
  ollama_data:
  prometheus_data:
  es_data:

networks:
  devflow_net:
    driver: bridge
```

**Ollama Entrypoint 脚本** (`scripts/ollama-entrypoint.sh`):
```bash
#!/bin/bash
set -e
echo "Pulling model qwen2.5:72b-instruct-q4_K_M..."
ollama pull qwen2.5:72b-instruct-q4_K_M
echo "Starting Ollama server..."
exec ollama serve
```

**Redis 持久化说明**:
- RDB 快照: `--save 900 1` (900秒内至少1次写入则快照)、`--save 300 10` (300秒内至少10次写入则快照)、`--save 60 10000` (60秒内至少10000次写入则快照)
- AOF 追加: `--appendonly yes` (每条写命令追加到 appendonly.aof)
- RDB+AOF 双持久化策略: RDB 用于全量备份和快速恢复，AOF 用于增量恢复和数据完整性
- 配置验证: `redis-cli -a $REDIS_PASSWORD CONFIG GET save` 验证 RDB 规则，`CONFIG GET appendonly` 验证 AOF 开启

**Celery Worker 并发度说明**:
- concurrency=8，管理 9 个命名 Agent + 蜂群编排 + 定时任务 + 健康检查
- 如需进一步分离任务类型，可配置专用 Worker 队列:
  - `celery-worker-named`: 命名 Agent 任务 (concurrency=4)
  - `celery-worker-swarm`: 蜂群编排任务 (concurrency=4)
  - `celery-worker-scheduled`: 定时任务和巡检 (concurrency=2)

**编程 Agent 容器资源限制**:
- Swarm Executor 通过 Docker API 创建编程 Agent 容器时设置资源上限:
  - CPU 限制: 4 核 (`--cpus=4`)
  - 内存限制: 8GB (`--memory=8g`)
  - 只读文件系统: `--read-only`
  - 能力限制: `--cap-drop=ALL`
  - 临时可写目录: `--tmpfs /tmp:rw,noexec,nosuid,size=512m`
- 防止单个编程 Agent 耗尽宿主机资源
- **并发上限与排队策略**:
  - 单项目蜂群最多并发 4 个编程 Agent 容器
  - 全局最多并发 16 个编程 Agent 容器（覆盖所有项目）
  - 超出上限时，新任务进入 Celery 队列按 FIFO 顺序等待
  - 排队超时: 任务在队列中等待超过 15 分钟仍未执行，标记为 QUEUED_TIMEOUT 并通知海梅
  - 全局资源上限: 16 个容器 x 4 核 = 64 核 CPU, 16 个容器 x 8GB = 128GB 内存
- 资源限制由 Docker cgroup 强制 enforce，不依赖编程工具自身

**Ollama 容器资源分配**:
- GPU 显存: `deploy.resources.reservations.devices` 声明 1 个 NVIDIA GPU
- 内存限制: `deploy.resources.limits.memory: 64G`
  - Ollama 服务进程本身约 0.5GB
  - `qwen2.5:72b-instruct-q4_K_M` INT4 量化模型约 36GB 显存/内存
  - 剩余约 27.5GB 用于推理计算和并发请求缓冲
- **9 个命名 Agent 共享单一 Ollama 实例**: 模型仅加载一次，占用约 36GB 显存/内存。并发推理请求由 Ollama 内置队列按顺序处理，不会重复加载模型或超配显存
- 如多项目并发推理导致排队时间过长，可通过 `config.yaml` 将部分 Agent 切换到云端模型分流

### 4.2 .env 文件示例

```env
# DevFlow 数据库
POSTGRES_USER=devflow
POSTGRES_PASSWORD=<生成随机强密码>
# Gitea 数据库 (独立用户,与DevFlow隔离)
GITEA_DB_USER=gitea_admin
GITEA_DB_PASSWORD=<生成随机强密码>
# Redis (Celery Broker 与缓存共用同一密码)
REDIS_PASSWORD=<生成随机强密码>
# JWT 签名密钥
SECRET_KEY=<生成随机密钥,用于JWT签名>
# Hermes Agent API Key (后端与Agent间认证)
HERMES_AGENT_API_KEY=<生成随机API密钥>
# Agent蜂群 Webhook 签名密钥
SWARM_WEBHOOK_SECRET=<生成随机Webhook签名密钥>
```

**注意**: `.env` 文件应添加到 `.gitignore`，不纳入版本控制。

### 4.3 Hermes Agent 部署

9个命名Agent角色采用独立Profile部署:

| Agent | Profile | Gateway端口 | 默认模型 (本地) | 可选模型 (云端) |
|-------|---------|-------------|----------------|----------------|
| 海梅 | haimei | 8765 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后兴 | houxing | 8766 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后旺 | houwang | 8767 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后发 | houfa | 8768 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后达 | houda | 8769 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后富 | houfu | 8770 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后贵 | hougui | 8771 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后荣 | houro | 8772 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |
| 后华 | houhua | 8773 | qwen2.5:72b-instruct-q4_K_M (Ollama) | gpt-4o |

**部署说明**:
- 9个Agent以宿主机进程方式运行，各自独立的 Hermes Profile 实例
- Agent 通过 Gateway API (端口 8765-8773) 与 FastAPI 后端通信
- **Ollama 资源共享**: 9 个 Agent 共享同一个 Ollama 容器实例（单一模型加载），通过 `http://localhost:11434` 访问。模型仅加载一次，占用约 36GB 显存/内存。并发请求由 Ollama 内置队列调度，不会重复加载模型
- FastAPI 后端访问 Ollama: 通过 Docker 内部网络 `http://ollama:11434`
- 默认模型为 `qwen2.5:72b-instruct-q4_K_M` (Qwen2.5-72B-Instruct INT4量化版)，通过 Ollama 容器加载推理
- 调度方式: Celery Worker 主动调用 Agent Gateway API，非 Agent 自行轮询

### 4.4 资源需求

**基础设施组件**:

| 组件 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| FastAPI后端 | 2核 | 4GB | 5GB |
| PostgreSQL (devflow) | 2核 | 4GB | 50GB |
| PostgreSQL (gitea) | 1核 | 2GB | 20GB |
| Redis | 1核 | 2GB | 5GB |
| Gitea | 1核 | 2GB | 50GB |
| Celery Worker | 2核 | 4GB | 5GB |
| Celery Beat | 0.5核 | 0.5GB | 1GB |
| Nginx | 1核 | 512MB | 1GB |
| Prometheus | 1核 | 2GB | 20GB |
| Jaeger | 1核 | 2GB | 10GB |
| Elasticsearch | 2核 | 4GB | 50GB |
| Kibana | 1核 | 2GB | 5GB |
| Ollama (服务进程) | 2核 | 0.5GB | 10GB |
| Swarm Executor | 1核 | 1GB | 2GB |
| WebSocket Worker | 1核 | 1GB | 1GB |
| Filebeat | 0.5核 | 0.5GB | 1GB |
| **基础设施小计** | **21.5核** | **35.5GB** | **238GB** |

**Ollama 模型推理资源**:

| 组件 | CPU | 内存/显存 | 磁盘 |
|------|-----|-----------|------|
| qwen2.5:72b-instruct-q4_K_M (INT4量化) | - | ~36GB 显存/内存 | ~40GB |
| **模型推理小计** | **2核** | **36GB** | **40GB** |

**Hermes Agent 进程资源**:

| 组件 | CPU (单个) | 内存 (单个) | 并发数 | CPU (总计) | 内存 (总计) |
|------|-----------|-------------|--------|-----------|-------------|
| 命名Agent进程 | 0.5核 | 512MB | 最多9个 | 4.5核 | 4.5GB |
| **Agent进程小计** | **4.5核** | **4.5GB** | - |

**Agent蜂群运行时资源**:

| 组件 | CPU (单个) | 内存 (单个) | 最大并发 | CPU (总计) | 内存 (总计) |
|------|-----------|-------------|----------|-----------|-------------|
| 编程Agent容器 (单项目) | 2核 | 4GB | 4个/项目 | 8核 | 16GB |
| 编程Agent容器 (全局上限) | 4核/个 | 8GB/个 | 16个(全局) | 64核(上限) | 128GB(上限) |
| **蜂群小计 (单项目)** | **8核** | **16GB** | - |

**宿主总资源需求汇总**:

| 维度 | 基础运行 (无项目执行) | 单项目峰值 (1个项目+蜂群) | 全局上限 (10项目+16编程容器) | 推荐配置 |
|------|---------------------|------------------------|--------------------------|---------|
| CPU | 26核 (21.5+2+4.5+Ollama2) | 34核 (26+8蜂群) | 90核 (26+64编程容器上限) | 32-64核 |
| 内存 | 76GB (35.5+36+4.5) | 92GB (76+16蜂群) | 184GB (76+128编程容器上限) | 96-128GB |
| 显存 (GPU) | 36GB (Ollama模型) | 36GB (Ollama模型) | 36GB (Ollama模型) | 48GB+ (单卡) |
| 磁盘 | 278GB (238+40模型) | 278GB + 项目文件 | 278GB + 项目文件 | 500GB SSD |

**说明**:
- 基础运行资源: 基础设施(21.5核/35.5GB) + Ollama服务(2核/0.5GB) + Ollama模型(36GB显存) + 命名Agent进程(4.5核/4.5GB)
- 单项目峰值: 基础运行 + 单项目蜂群(8核/16GB)
- 全局上限: 基础运行 + 全局编程容器上限(64核/128GB)
- Ollama 模型推理资源在模型加载后持续占用，`qwen2.5:72b-instruct-q4_K_M` INT4量化版约36GB显存/内存（9个Agent共享单一实例，不重复计算）
- 生产部署建议配备：32核 CPU、96GB 内存 + 48GB GPU显存 (或 128GB 统一内存)、500GB SSD 磁盘
- 实际使用中不会所有Agent同时满载，推荐配置基于 80% 资源利用率上限
- WSL 环境下 GPU 推理需额外配置 NVIDIA 容器工具链

### 4.5 网络拓扑

```
+--------------------------------------------------+
|                  外部网络                         |
|           (人类用户 / 编程Agent)                  |
+------------------------+-------------------------+
                         |
                +--------v--------+
                |    Nginx        |
                |  (443/80)       |
                +--------+--------+
                         |
+------------------------v-------------------------------+
|       Docker 自定义网络 (devflow_net, bridge模式)      |
|                                                       |
|  +----------+  +------------+  +----------+          |
|  | FastAPI  |  | WS Worker  |  | Celery   |          |
|  | :8000    |  | :8001      |  | Worker   |          |
|  |(backend) |  |(ws-worker) |  |(celery-wk)|         |
|  |w=2       |  |w=1,ws专用  |  |c=8       |          |
|  +----+-----+  +----+-------+  +----+-----+          |
|       |              |                |               |
|  +----v-----+  +----v-----+  +-------+------+       |
|  |  Postgres|  |  Redis   |  | Celery Beat|       |
|  | :5432    |  | :6379    |  | (定时任务)  |       |
|  |(devflow) |  |(RDB+AOF) |  | 独立容器    |       |
|  +----------+  +----------+  +------------+       |
|                                                       |
|  +----------+  +----------+  +----------+            |
|  |  Gitea   |  |  Postgres|  |  Ollama  |            |
|  | :3000    |  | :5432    |  | :11434   |            |
|  | (gitea)  |  | (gitea)  |  |(模型推理) |            |
|  | 仅内部   |  +----------+  |mem=64G   |            |
|  +----------+                |gpu=1     |            |
|                              |shared by|            |
|                              |9 agents |            |
|                              +----------+            |
|                                                       |
|  +----------+  +-----------+  +----------+           |
|  |Filebeat  |  |Elastic    |  | Kibana   |           |
|  | :5044    |  | :9200     |  | :5601    |           |
|  +----------+  +-----------+  +----------+           |
|                                                       |
|  +----------+  +----------+  +--------------+        |
|  |Prometheus|  |  Jaeger  |  |Swarm Executor|        |
|  | :9090    |  | :14269   |  | (蜂群执行器)  |        |
|  +----------+  +----------+  +------+-------+        |
|       注: 以上管理端口仅在 devflow_net 内可达,          |
|       不映射到宿主机 (仅 80/443/11434 对外暴露)        |
|       Gitea 通过 Nginx location /gitea/ 代理访问        |
+--------------------------------------------------------+
                         |
+------------------------v-------------------------------+
|              宿主机 (Host)                              |
|                                                        |
|  +--------------------------------------------------+  |
|  |  9个Hermes Agent进程 (Gateway API)               |  |
|  |  端口: 8765-8773 (绑定127.0.0.1)                 |  |
|  |  进程管理: systemd 服务单元                       |  |
|  |  访问Ollama: http://localhost:11434              |  |
|  |  (共享单一Ollama容器实例,内置队列调度)             |  |
|  +--------------------------------------------------+  |
|                                                        |
|  +--------------------------------------------------+  |
|  |  编程Agent容器 (由Swarm Executor动态创建)         |  |
|  |  独立Docker容器, cgroup资源限制                   |  |
|  |  CPU: 4核上限, 内存: 8GB上限                      |  |
|  |  只读文件系统, 能力限制                           |  |
|  |  全局上限: 16个并发容器                           |  |
|  +--------------------------------------------------+  |
+--------------------------------------------------------+
```

**跨网络通信说明**:
- Docker 内部网络 `devflow_net`: 所有容器通过该网络通信，使用容器名作为主机名 (如 `backend:8000`, `ollama:11434`, `gitea:3000`)
- Ollama 容器端口 11434 映射到宿主机，Docker 内部服务通过 `http://ollama:11434` 访问
- 宿主机上的 9 个 Hermes Agent 共享同一个 Ollama 容器实例，通过 `http://localhost:11434` 访问，Ollama 内置队列调度并发请求
- FastAPI 后端与 Hermes Agent 通过宿主机端口 8765-8773 通信 (Gateway API)
- Swarm Executor 容器通过 Docker 网络与 Celery/Redis 通信，通过挂载的宿主机目录访问项目文件，通过 Docker API 创建和管理编程 Agent 容器
- 仅端口 11434 (Ollama) 映射到宿主机，Gitea 不直接映射端口，统一通过 Nginx `location /gitea/` 代理访问
- 其余管理端口仅在 `devflow_net` 内可达

### 4.6 蜂群 Agent 执行环境

**部署架构说明**:

```
+--------------------------------------------------------------+
|              Docker 容器 (devflow_net)                        |
|                                                              |
|  +--------------------------------------------------------+  |
|  |  Swarm Executor (swarm-executor 容器)                  |  |
|  |                                                        |  |
|  |  职责:                                                  |  |
|  |  1. 接收 Celery Worker 分派的蜂群任务                   |  |
|  |  2. 根据任务类型选择合适的编程工具                      |  |
|  |  3. 通过 Docker API 创建独立容器运行编程工具            |  |
|  |  4. 监控容器执行进度,收集输出                           |  |
|  |  5. 任务完成后清理容器资源                               |  |
|  |  6. 结果回传: 轮询挂载卷 + 采集Docker日志 + HTTP回调    |  |
|  |  7. 管理全局并发上限 (16个) 和排队策略                   |  |
|  |                                                        |  |
|  |  Docker API 调用示例:                                   |  |
|  |  docker run --rm                                       |  |
|  |    --name coding-agent-{id}                            |  |
|  |    --cpus=4                                            |  |
|  |    --memory=8g                                         |  |
|  |    --read-only                                         |  |
|  |    --cap-drop=ALL                                      |  |
|  |    --tmpfs /tmp:rw,noexec,nosuid,size=512m             |  |
|  |    -v /DevFlow/projects/{project_id}:/workspace        |  |
|  |    --network devflow_net                               |  |
|  |    coding-tool-image                                   |  |
|  |    claude-code --project /workspace                    |  |
|  |               --task "{task_description}"               |  |
|  |                                                        |  |
|  |  结果回传机制:                                          |  |
|  |  1. 编程Agent写入 /workspace/output/ (共享挂载卷)       |  |
|  |  2. Docker stdout/stderr 被 Swarm Executor 采集         |  |
|  |  3. 容器退出后, Swarm Executor 组装结果                 |  |
|  |  4. HTTP POST /api/swarm/result 回调 FastAPI           |  |
|  |  5. FastAPI 更新 DB 并触发后荣QA检验                    |  |
|  |                                                        |  |
|  |  与宿主机交互方式:                                      |  |
|  |  - 挂载 /DevFlow/projects (读写项目文件)                |  |
|  |  - 挂载 /var/run/docker.sock (ro, 管理容器)            |  |
|  |  - 通过 Docker API 创建子容器运行编程工具                |  |
|  +--------------------------------------------------------+  |
|                                                              |
|  +--------------------------------------------------------+  |
|  |  编程Agent容器 (动态创建, 任务完成后自动清理)            |  |
|  |  +--------------------------------------------------+  |  |
|  |  |  coding-agent-001 (Claude Code)                   |  |  |
|  |  |  CPU: 4核上限 | 内存: 8GB上限                      |  |  |
|  |  |  工作目录: /workspace                             |  |  |
|  |  |  产出写入: /workspace/output/                     |  |  |
|  |  +--------------------------------------------------+  |  |
|  |  +--------------------------------------------------+  |  |
|  |  |  coding-agent-002 (Opencode)                      |  |  |
|  |  |  CPU: 4核上限 | 内存: 8GB上限                      |  |  |
|  |  |  工作目录: /workspace                             |  |  |
|  |  |  产出写入: /workspace/output/                     |  |  |
|  |  +--------------------------------------------------+  |  |
|  |  ... (单项目最多4个, 全局最多16个并发)                   |  |
|  +--------------------------------------------------------+  |
+--------------------------------------------------------------+
```

**关键设计决策**:
- **编程 Agent 以独立容器运行**: 每个编程 Agent 工具在独立 Docker 容器中运行，通过 cgroup 实现 CPU/内存资源限制，通过只读文件系统减少攻击面
- **Swarm Executor 为容器管理器**: Swarm Executor 容器负责通过 Docker API 创建、监控和清理编程 Agent 容器
- **命名 Agent 直接调度**: 后发/后达命名 Agent 通过 Celery 任务将蜂群任务提交给 Swarm Executor，Swarm Executor 负责具体的容器创建和监控
- **结果回传**: 编程 Agent 容器完成后，通过三种机制回传结果(共享挂载卷文件轮询 + Docker日志采集 + Swarm Executor HTTP回调)，由 Swarm Executor 组装后回调 FastAPI 后端
- **资源限制 enforce 机制**: Docker cgroup v2 强制 enforce CPU 和内存上限，不依赖编程工具自身，确保即使工具失控也不会耗尽资源
- **容器自动清理**: 使用 `--rm` 标志，容器退出后自动删除，释放磁盘空间
- **并发上限与排队**: 单项目最多 4 个编程 Agent 容器同时运行，全局最多 16 个。超出上限时新任务进入 Celery 队列 FIFO 等待，等待超时 15 分钟标记为 QUEUED_TIMEOUT

### 4.7 Ollama 并发推理说明

**并发场景**:
- 10 个并发项目 x 9 个命名 Agent = 最多 90 个命名 Agent 进程
- **所有 Agent 共享同一个 Ollama 容器实例和同一个 `qwen2.5:72b-instruct-q4_K_M` 模型**（不各自独立加载，避免 360-432GB 内存的不可行需求）

**Ollama 并发处理能力**:
- Ollama 内置请求队列机制，当并发请求超过处理能力时自动排队
- `qwen2.5:72b-instruct-q4_K_M` (INT4量化) 在 GPU (48GB显存) 下单请求推理延迟约 200-500ms (取决于 prompt 长度和生成 token 数)
- 典型 QPS 估算:
  - GPU 模式 (48GB显存): 约 5-10 QPS (并发请求排队处理)
  - CPU 模式 (36GB内存): 约 1-2 QPS (显著 slower)
- Ollama 默认支持并发加载，但同一模型多副本会重复占用显存，故采用单模型实例 + 队列模式

**资源争抢处理策略**:
- Ollama 容器设置内存上限 64GB，其中模型占用约 36GB，剩余 27.5GB 用于推理计算
- 并发请求超过处理能力时，Ollama 内部队列自动排队，不会创建新模型实例
- 命名 Agent 侧配置请求超时为 60 秒，避免无限等待
- 后端 Gateway Client 使用 `asyncio.Semaphore(5)` 限制对同一 Agent 的并发请求
- 高峰时段策略:
  - 非紧急任务 (文档生成、报告编写) 可延迟执行
  - 紧急任务 (QA检验、流程调度) 优先调度，通过 Celery 专用队列实现
  - Celery 任务队列天然支持排队，不会丢失请求
- 如排队延迟持续超过 60 秒，可自动将部分低优先级 Agent 切换到云端模型 (OpenAI/Anthropic) 分流

**资源瓶颈与优化**:
- 90 个 Agent 并非同时活跃，实际并发推理请求通常 < 10 个
- 如瓶颈明显，可考虑:
  - 为 Agent 分组分配云端模型 (OpenAI/Anthropic) 作为分流
  - 增大 GPU 显存 (如 A100 80GB) 提升单模型并发能力
  - 对轻量任务 (如简短回复) 使用更小的本地模型 (如 qwen2.5:7b-instruct)

### 4.8 命名 Agent 进程管理

**职责**: 定义 9 个命名 Agent 宿主机进程的进程管理、崩溃自动重启、健康检查机制

**进程管理方案**: 采用 systemd 作为进程管理器

每个命名 Agent 对应一个 systemd 服务单元，示例 (`/etc/systemd/system/hermes-haimei.service`):

```ini
[Unit]
Description=Hermes Agent - HaiMei (Project Manager)
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=jim
WorkingDirectory=/home/jim/.hermes/profiles/haimei
ExecStart=/home/jim/.hermes/bin/hermes gateway --profile haimei --port 8765
Restart=always
RestartSec=10
TimeoutStopSec=30
LimitNOFILE=65536

# 环境隔离
Environment=HERMES_PROFILE=haimei
Environment=HERMES_GATEWAY_PORT=8765
EnvironmentFile=/home/jim/.hermes/profiles/haimei/.env

# 资源限制
MemoryMax=2G
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

**9 个 Agent 服务命名规则**:
- `hermes-haimei.service` (海梅, 端口 8765)
- `hermes-houxing.service` (后兴, 端口 8766)
- `hermes-houwang.service` (后旺, 端口 8767)
- `hermes-houfa.service` (后发, 端口 8768)
- `hermes-houda.service` (后达, 端口 8769)
- `hermes-houfu.service` (后富, 端口 8770)
- `hermes-hougui.service` (后贵, 端口 8771)
- `hermes-hourong.service` (后荣, 端口 8772)
- `hermes-houhua.service` (后华, 端口 8773)

**崩溃自动重启策略**:
- `Restart=always`: 任何退出码均自动重启
- `RestartSec=10`: 重启前等待 10 秒，避免快速重启循环
- `TimeoutStopSec=30`: 停止时最多等待 30 秒，超时强制终止
- 重启日志: systemd 自动记录重启次数和时间到 journal

**健康检查机制**:

1. **systemd 级别**: systemd 监控进程存活状态，进程退出自动重启

2. **Gateway API 级别**: 每个 Agent 暴露 `/health` 端点:
   - `http://127.0.0.1:876X/health`
   - 返回 `{"status": "healthy", "profile": "xxx", "uptime_seconds": N}`
   - 超时时间: 5 秒

3. **Celery Worker 级别**: 3.8 节定义的超时关联机制:
   - 调用 Agent Gateway API 时设置 60 秒 HTTP 超时
   - 超时后执行健康检查 (`/health` 端点)
   - 健康检查失败: 标记 Agent 故障，通知海梅

4. **Celery Beat 定时巡检**: 每 5 分钟执行一次命名 Agent 健康检查任务:
   - 遍历 9 个 Agent 的 `/health` 端点
   - 连续 3 次健康检查失败 (15分钟): 自动执行 `systemctl restart hermes-{profile}`
   - 重启后仍失败: 发送告警通知 (WebSocket + 邮件)
   - 健康检查结果记录到 PostgreSQL `agent_health_checks` 表

**进程管理操作**:
```bash
# 启动所有 Agent
systemctl start hermes-{haimei,houxing,houwang,houfa,houda,houfu,hougui,hourong,houhua}

# 启用开机自启
systemctl enable hermes-{haimei,houxing,houwang,houfa,houda,houfu,hougui,hourong,houhua}

# 查看状态
systemctl status hermes-haimei

# 查看日志
journalctl -u hermes-haimei -f

# 重启单个 Agent
systemctl restart hermes-haimei
```

---

## 5. 容灾与高可用

### 5.1 可用性目标

- **当前部署模式**: 单实例部署,可用性目标 99%
- **99% 可用性保障机制**:
  - **Docker 自动重启**: 所有关键服务配置 `restart: always`，容器异常退出时 Docker 自动重启，恢复时间 < 30 秒
  - **健康检查 + 故障恢复**: 每个容器配置 `healthcheck`，Nginx 自动将流量从故障后端剔除，健康检查间隔 30 秒
  - **命名 Agent 进程管理**: systemd 管理 9 个命名 Agent 进程，崩溃自动重启 (Restart=always)，Celery Beat 定时巡检
  - **数据备份**: PostgreSQL 每日全量备份 + 每 6 小时增量备份，Redis RDB+AOF 双持久化，确保数据不丢失
  - **预期年停机时间**: 99% 可用性 = 年停机时间 <= 36.5 小时，主要通过自动重启覆盖意外故障
- **限制说明**: 单实例 PostgreSQL、Redis、Gitea、Ollama 存在单点故障风险，无法支撑 99% 以上 SLA
- **高可用扩展方案** (可选,按需实施):
  - **PostgreSQL**: 流复制 + Patroni 自动故障转移 (主从架构,2-3 节点)
  - **Redis**: Redis Sentinel 集群 (3 节点),自动选举主节点
  - **Gitea**: 多实例 + 共享存储 (NFS/分布式文件系统),前端 Nginx 负载均衡
  - **Ollama**: 多副本 + 云端模型降级 (见 5.5 节)
  - **FastAPI**: 多副本 + Nginx 负载均衡,健康检查自动剔除故障节点
  - **预期可用性**: 扩展后可达 99.5%~99.9%

### 5.2 备份策略

| 数据 | 频率 | 保留 | 存储位置 |
|------|------|------|----------|
| PostgreSQL (devflow) | 每日全量 + 每6h增量 | 30天/90天/365天 | /data/backups/ |
| PostgreSQL (gitea) | 每日全量 | 30天 | /data/backups/ |
| 文件存储 | 每日全量 | 30天 | /data/backups/ |
| Gitea | Git历史 + 每日归档 | 永久 | 内置 + /data/backups/ |
| Ollama模型 | 首次部署拉取 | 永久 | ollama_data 卷 |
| Redis (RDB快照) | 按save规则自动 | 最新3份 | redis_data 卷 |

### 5.3 恢复目标

- **RTO** (恢复时间目标): < 2小时
- **RPO** (恢复点目标): < 1小时

### 5.4 健康检查

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
        "ollama": await check_ollama(),
        "elasticsearch": await check_elasticsearch(),
        "kibana": await check_kibana(),
    }
    return {"status": "healthy" if all(checks.values()) else "degraded",
            "checks": checks}
```

**健康检查覆盖说明**:
- `check_postgres()`: 检查 DevFlow 主数据库连接和查询响应
- `check_redis()`: 检查 Redis PING 响应
- `check_gitea()`: 检查 Gitea API `/api/health` 端点
- `check_hermes_agents()`: 检查9个Agent Gateway API端口可达性
- `check_celery()`: 检查 Celery Worker 活跃状态
- `check_ollama()`: 检查 Ollama `/api/tags` 端点响应和模型加载状态
- `check_elasticsearch()`: 检查 ES `_cluster/health` 端点
- `check_kibana()`: 检查 Kibana `/api/status` 端点

**Docker 容器级健康检查** (已在 docker-compose 中配置):
- `backend`: `curl -sf http://localhost:8000/health` (30s 间隔)
- `dedicated-websocket-worker`: `curl -sf http://localhost:8001/health` (30s 间隔)
- `postgres`: `pg_isready -U ${POSTGRES_USER} -d devflow` (10s 间隔)
- `gitea-postgres`: `pg_isready -U ${GITEA_DB_USER} -d gitea` (10s 间隔)
- `redis`: `redis-cli -a ${REDIS_PASSWORD} ping` (10s 间隔)
- `gitea`: `curl -sf http://localhost:3000/api/health` (30s 间隔)
- `ollama`: `curl -sf http://localhost:11434/api/tags` (30s 间隔, 120s 启动等待)
- `elasticsearch`: `curl -sf http://localhost:9200/_cluster/health` (30s 间隔)
- `kibana`: `curl -sf http://localhost:5601/api/status` (30s 间隔)
- `celery-worker`: `celery -A tasks inspect ping` (30s 间隔)
- `celery-beat`: 由 systemd/Docker 监控进程存活
- `swarm-executor`: `python -c 'import requests; requests.get("http://localhost:9100/health")'` (30s 间隔)
- `prometheus`: `curl -sf http://localhost:9090/-/healthy` (30s 间隔)
- `jaeger`: `curl -sf http://localhost:14269` (30s 间隔)
- `filebeat`: `filebeat test output` (30s 间隔)
- Nginx 健康检查由 Docker 容器自身 `healthcheck` 指令处理 (`curl -sf http://localhost/`)

### 5.5 Ollama 故障降级策略

**背景**: 9 个命名 Agent 共享单一 Ollama 容器实例，Ollama 故障将导致所有命名 Agent 无法执行推理任务，成为系统单点故障。为保障 99% 可用性目标，定义以下三级降级策略：

**降级级别**:

| 级别 | 触发条件 | 降级措施 | 影响范围 | 恢复方式 |
|------|---------|---------|---------|---------|
| L1 - 排队限流 | Ollama 响应延迟 > 30秒 | 低优先级任务延迟执行，高优先级任务继续排队 | 任务执行速度下降，不丢失任务 | Ollama 恢复后自动恢复正常 |
| L2 - 云端分流 | Ollama 连续 3 次健康检查失败 (15分钟) | 自动将非敏感任务 Agent 切换到云端模型 (OpenAI/Anthropic) | 产生云端 API 费用，部分任务切换模型 | Ollama 恢复后自动切回本地 |
| L3 - 任务暂停 | Ollama 完全不可用 + 云端模型不可用 | 暂停所有非紧急 Agent 任务，仅保留 QA 检验和流程调度 | 项目执行暂停，等待推理服务恢复 | 手动恢复 Ollama 或配置云端 API Key |

**L1 排队限流机制**:
- Celery Worker 检测到 Ollama 响应延迟 > 30 秒时，触发限流
- 低优先级队列 (`low_queue`) 中的任务暂停执行，进入等待状态
- 高优先级队列 (`qa_queue`) 和普通队列 (`default_queue`) 继续执行
- 等待超过 15 分钟仍未恢复，自动升级至 L2 级别

**L2 云端分流机制**:
- Ollama 健康检查连续 3 次失败 (间隔 5 分钟，总计 15 分钟)
- 后端自动读取 `.env` 中的云端 API Key (`OPENAI_API_KEY`/`ANTHROPIC_API_KEY`)
- 按优先级切换 Agent 到云端模型:
  1. 后贵 (文档管理员) -> gpt-4o (文档生成适合云端)
  2. 后华 (安全员) -> gpt-4o (安全审计适合云端)
  3. 后兴 (需求分析师) -> gpt-4o (需求分析适合云端)
  4. 其余 Agent 保持排队等待
- 切换方式: 更新 Agent 的 `config.yaml` 中 `model` 和 `provider` 配置
- 切换日志记录到 PostgreSQL `agent_model_switches` 表
- 通知人类用户: WebSocket 推送 + 邮件通知

**L3 任务暂停机制**:
- Ollama 完全不可用 (健康检查连续 10 次失败) 且云端模型 API 也返回错误
- 暂停所有命名 Agent 任务执行
- 已执行的任务保存 checkpoint 到数据库
- 项目状态标记为 `PAUSED_WAITING_INFRA`
- 通知人类用户: WebSocket 推送 + 邮件 + 群聊消息
- 仅保留海梅 (项目经理) 的最低限度功能，用于与人类用户沟通状态

**Ollama 恢复检测**:
- Celery Beat 每 2 分钟执行一次 Ollama 恢复检测
- 检测通过 (健康检查成功 + 模型推理测试成功):
  - 自动取消 L3 暂停状态
  - 逐步取消 L2 云端分流 (Agent 切回本地模型)
  - 恢复 L1 排队任务的正常执行
  - 通知人类用户: Ollama 服务已恢复

**云端模型配置** (`.env` 中预配置):
```env
# 云端模型 API Key (用于 Ollama 故障时降级)
OPENAI_API_KEY=<OpenAI API Key>
ANTHROPIC_API_KEY=<Anthropic API Key>
# 降级策略配置
OLLAMA_FALLBACK_ENABLED=true
OLLAMA_FALLBACK_MODELS=haimei:gpt-4o,houxing:gpt-4o,hougui:gpt-4o,houhua:gpt-4o
```

---

## 6. 安全架构

### 6.1 认证与授权

**人类用户认证**:
- **认证**: JWT Token (Access Token 30分钟 + Refresh Token 7天)
- **授权**: RBAC (基于角色的访问控制)
- **项目隔离**: 用户仅可访问自身创建的项目

**RBAC 角色定义**:

| 角色 | 权限 | 说明 |
|------|------|------|
| admin (管理员) | 全部权限 | 系统管理、用户管理、项目创建、Agent配置、部署管理 |
| developer (项目成员) | 项目读写、群聊、进度查看 | 可参与项目开发、查看进度、群聊讨论 |
| viewer (只读) | 项目只读、群聊只读 | 仅查看项目进度和群聊历史,不可修改 |

**Hermes Agent 认证**:
- 9个命名Agent通过 API Key 向后端认证
- API Key 存储在 `.env` 的 `HERMES_AGENT_API_KEY` 变量中
- 后端通过自定义中间件验证请求头 `X-Hermes-API-Key`
- 每个 Agent Profile 配置中注入对应 API Key，通过 Gateway 请求头传递

**Agent蜂群认证**:
- 蜂群Agent通过 Webhook 签名认证上报结果
- Webhook 签名使用 HMAC-SHA256，密钥为 `.env` 中的 `SWARM_WEBHOOK_SECRET`
- 后端验证请求头 `X-Webhook-Signature` 与请求体的 HMAC 签名是否匹配
- 验证通过后处理蜂群上报的任务结果、进度和产物

**内部Docker网络策略**:
- 使用 Docker 自定义网络 `devflow_net` (bridge 模式)，非公网可达
- **仅以下端口映射到宿主机**: 80 (Nginx HTTP)、443 (Nginx HTTPS)、11434 (Ollama)
- **以下管理端口不映射到宿主机** (仅在 devflow_net 内可达):
  - PostgreSQL (5432)
  - Redis (6379)
  - Gitea (3000) — 通过 Nginx `location /gitea/` 代理访问
  - Elasticsearch (9200)
  - Kibana (5601)
  - Prometheus (9090)
  - Jaeger (16686/14268)
- Hermes Agent Gateway 端口 (8765-8773) 绑定 `127.0.0.1`，仅宿主机本地可达
- 容器间通信通过 Docker 内部网络 `devflow_net`，不受外部网络访问

### 6.2 数据传输

- 全站 HTTPS (TLS 1.3)
- WebSocket wss:// 加密
- Agent通信数据脱敏存储

### 6.3 敏感信息管理

- 所有密码、密钥存储在 `.env` 文件中,不纳入版本控制
- `.env` 文件权限设置为 `600` (仅属主可读)
- 容器内通过 `env_file` 注入环境变量,不暴露为 Docker 明文
- 数据库密码、Redis密码、JWT密钥、API Key、Webhook Secret 均通过 `.env` 管理

### 6.4 审计日志

所有关键操作记录日志:
- Agent任务分派
- QA检验结果
- 代码提交
- 错误和异常
- 用户登录/登出
- Agent认证失败事件
- 蜂群Webhook签名验证失败事件
- Ollama 降级切换事件

### 6.5 Docker Socket 挂载安全策略

**需要挂载 Docker socket 的容器**:

| 容器 | 挂载方式 | 用途 |
|------|----------|------|
| swarm-executor | `/var/run/docker.sock:/var/run/docker.sock:ro` | 创建和管理编程 Agent 容器 |
| filebeat | `/var/run/docker.sock:/var/run/docker.sock:ro` | 采集 Docker 容器日志 |

**最小权限策略**:

1. **只读挂载 (`:ro`)**: 两个容器均以只读方式挂载 Docker socket。swarm-executor 通过 Docker API 的只读挂载仍可创建/管理容器（Docker API 通过 socket 通信，`ro` 限制的是对 socket 文件本身的写入，不影响 API 调用），但无法修改 socket 文件本身。filebeat 仅用于读取容器日志。

2. **Swarm Executor 权限约束**:
   - 仅允许创建编程 Agent 容器，不允许创建其他类型的容器
   - 编程 Agent 容器强制应用安全策略: `--cap-drop=ALL`、`--read-only`、资源上限
   - 编程 Agent 容器加入 `devflow_net` 网络，限制网络访问范围
   - 编程 Agent 容器使用 `--rm` 标志，任务完成后自动清理
   - Swarm Executor 不暴露任何端口到宿主机
   - **Swarm Executor 安全加固**: 容器内运行用户为非 root 用户，仅授予操作 Docker API 所需的最小权限；容器内代码白名单机制限制可创建的镜像和参数

3. **Filebeat 权限约束**:
   - 仅用于读取容器日志，不涉及容器管理操作
   - 只读挂载已足够满足日志采集需求

4. **网络隔离**:
   - swarm-executor 和 filebeat 均在 `devflow_net` 网络内，无法从外部网络直接访问
   - 编程 Agent 容器同样在 `devflow_net` 内，仅能访问 DevFlow 后端和 Ollama 等内部服务

5. **风险说明**:
   - Docker socket 挂载本质上等价于宿主机 root 权限，这是 Swarm Executor 管理编程 Agent 容器的必要代价
   - 通过只读挂载、网络隔离、容器安全加固等多层防护降低风险
   - 生产环境中可考虑使用 Docker API 的 TLS 认证或根less Docker 进一步加固

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

- **并发项目数**: 10个
- **容量规划依据** (修订): 基于完整资源核算计算得出:
  - 服务器总资源: 34核 CPU 基础 + 8核/项目蜂群 (单项目峰值)
  - 基础设施持续占用: 21.5核 CPU、35.5GB 内存
  - Ollama 模型推理占用: 36GB 显存/内存 (`qwen2.5:72b-instruct-q4_K_M` INT4量化，9个Agent共享单一实例)
  - 命名 Agent 进程: 4.5核 CPU、4.5GB 内存
  - 可用资源: 约 10核 CPU、19.5GB 内存 (扣除基础设施+Ollama+Agent进程后)
  - 单个项目平均占用: CPU 0.8核 (含Agent执行峰值)、内存 2GB
  - 按 80% 资源利用率上限: CPU 可支撑约 12 个项目,内存可支撑约 9 个项目
  - 取内存为瓶颈: 保守估计 10 个并发项目
- **Agent并发限制**: 同Profile同一时间仅执行1个任务
- **WebSocket并发**: 单群组支持10+ Agent在线，由专用 WebSocket Worker 处理
- **API并发**: 信号量限制5个/Agent
- **Ollama并发**: 单模型实例 + 内部请求队列,约 5-10 QPS (GPU模式)，9个Agent共享

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
- 追踪全链路: 分派->执行->检验->提交
- 保留7天

### 8.3 日志管理 (ELK Stack)

- **组件部署**: Elasticsearch + Logstash (由Filebeat替代) + Kibana
- **采集方式**: Filebeat 采集各容器日志,推送至 Elasticsearch
- **日志格式**: JSON结构化日志
- **保留策略**: 本地保留30天 + ELK保留90天
- **关键操作**: 所有关键操作必记日志,Kibana 配置实时告警查询

### 8.4 告警规则

| 告警类型 | 条件 | 通知方式 |
|----------|------|----------|
| CPU告警 | >85% 持续5分钟 | WebSocket + 邮件 |
| 内存告警 | >90% 持续3分钟 | WebSocket + 邮件 |
| API错误率 | >5% | WebSocket + 邮件 |
| Agent宕机 | 进程停止 | WebSocket + 邮件 |
| 任务超时 | >30分钟 | WebSocket + 邮件 |
| Ollama服务不可用 | /api/tags 无响应 | WebSocket + 邮件 |
| Ollama降级触发 | 自动切换到云端模型 | WebSocket + 邮件 |
| 命名Agent健康检查失败 | 连续3次失败 | WebSocket + 邮件 |

---
