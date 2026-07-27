# DevFlow 架构设计文档 V14.0

**项目**: DevFlow 项目管理平台
**版本**: 14.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: V13.0 修订 (根据后荣 QA 检验报告修订)

**变更日志**:
- V14.0 (2026-06-13): 根据后荣 QA 检验报告修订
  - 【严重问题1】文档完整性保障: 本版本采用文件写入方式确保文档完整输出，包含全部9个核心章节及附录，不再出现截断问题
  - 【中等问题2】资源容量规划补充: 新增PostgreSQL数据库容量规划(存储/连接数/IOPS)、Redis内存规划、Nginx并发连接数配置、宿主机总资源需求汇总表
  - 【中等问题3】故障转移与降级策略完善: 补充Ollama故障时自动降级流程、云端模型切换触发条件、降级期间功能限制说明、故障恢复后回切策略
  - 【建议改进4】安全设计补充: 补充用户认证授权方案(JWT+Refresh Token)、API接口鉴权设计、敏感配置管理(.env/密钥管理)、命名Agent与Gateway API之间认证机制
  - 【建议改进5】监控与可观测性细节补充: 明确监控工具选型(Prometheus+Grafana+Loki+Alertmanager)、关键监控指标定义、告警阈值设定、链路追踪方案(OpenTelemetry)
  - 延续 V13.0 已修复项: 架构图 Celery Beat 独立容器、Ollama 降级策略、编程 Agent 结果回传路径、命名 Agent 进程管理、宿主资源容量量化、核心数据流补充
- V13.0 (2026-06-13): 根据后荣 QA 检验报告修订（文档完整性修复）
- V12.0 (2026-06-13): 根据后荣 QA 检验报告修订
- V11.0 ~ V1.0: 历史版本迭代

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
- **可观测**: 全链路监控(Prometheus+Grafana+Loki+OpenTelemetry)、日志、告警体系覆盖系统运行状态

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
                                                        +----+-----+
         |                                                    |
+--------v--------------------------------------------------+ |
| 9个命名Agent角色 (宿主机进程, 独立Hermes Profile实例)       | |
| 进程管理: systemd 服务单元, 崩溃自动重启 (restart=always)   | |
| 海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华 (Gateway API)  | |
| 调度: Celery Worker -> Gateway API HTTP -> 命名Agent执行   | |
| 推理: 9个Agent共享单一Ollama容器实例 + 内置请求队列并发调度  | |
| 默认模型: 本地 Ollama + qwen2.5:72b-instruct-q4_K_M       | |
| 降级策略: Ollama故障 -> 云端模型API(OpenAI/Anthropic)      | |
| 产出持久化: 写入 /DevFlow/projects/{project_id}/            | |
+-------------------------------------------------------------+
         |
+--------v--------------------------------------------------+
| Ollama 容器 (ollama)                                      |
| 模型: qwen2.5:72b-instruct-q4_K_M (72B Q4量化)             |
| GPU: NVIDIA GPU (显存 >= 48GB)                            |
| 内置请求队列: 并发调度9个命名Agent推理请求                 |
| 健康检查: HTTP GET /api/tags, 间隔30秒                     |
+-----------------------------------------------------------+
         |
+--------v--------------------------------------------------+
| Swarm Executor (Docker 容器: swarm-executor)              |
| 职责: 接收 Celery 任务, 调度编程 Agent 容器执行            |
| 全局并发上限: 16 个编程 Agent 容器                        |
| 单项目并发上限: 4 个编程 Agent 容器                       |
| 单个容器资源: 4 核 CPU / 8GB 内存                         |
| 结果回传: 共享挂载卷轮询 + Docker日志采集 + HTTP回调       |
+-----------------------------------------------------------+
         | Docker API 创建/销毁
+--------v--------------------------------------------------+
| 编程 Agent 容器 (动态创建, 按需销毁)                       |
| 镜像: devflow/coding-agent:latest                         |
| 资源限制: 4 核 CPU / 8GB 内存 / 无 GPU                    |
| 生命周期: 任务开始创建 -> 执行完成 -> 自动销毁             |
| 工作空间: 挂载 /DevFlow/projects/{project_id}/            |
+-----------------------------------------------------------+
         |
+--------v--------------------------------------------------+
| 监控与可观测性 (Prometheus + Grafana + Loki + Alertmanager) |
| 指标采集: API延迟/错误率/队列长度/容器资源/Agent执行状态     |
| 日志聚合: Loki 收集所有容器和应用日志                      |
| 链路追踪: OpenTelemetry 追踪 API->Celery->Agent->Ollama     |
| 告警: Alertmanager 邮件/Webhook 通知                      |
+-----------------------------------------------------------+
```

### 1.3 架构层次说明

| 层次 | 组件 | 技术选型 | 职责 |
|------|------|----------|------|
| 客户端层 | Web 前端 | Vue 3 + Vite | 用户界面、实时通信 |
| 客户端层 | 移动端 | Flutter / H5 | 移动访问、通知推送 |
| 接入层 | Nginx | Nginx 1.24 | 反向代理、SSL 终止、WebSocket 代理 |
| 应用层 | DevFlow 后端 | FastAPI + Uvicorn | HTTP API、业务逻辑、流程调度 |
| 应用层 | WebSocket Worker | FastAPI + WebSockets | 长连接管理、实时消息推送 |
| 调度层 | Celery Worker | Celery 5.3 + Redis Broker | 异步任务队列、Agent 执行编排 |
| 调度层 | Celery Beat | Celery Beat (独立容器) | 定时任务调度（项目状态检查、超时清理等） |
| 调度层 | Swarm Executor | Python + Docker SDK | 编程 Agent 容器生命周期管理 |
| Agent 层 | 命名 Agent | Hermes (9 个独立 Profile) | 9 个命名 Agent 角色宿主进程，systemd 管理 |
| Agent 层 | 编程 Agent | Docker 容器 (动态编排) | CodeArts 等编程 Agent 容器，按需创建/销毁 |
| 推理层 | Ollama | Ollama 容器 + qwen2.5:72b | 本地 LLM 推理引擎，9 个命名 Agent 共享 |
| 推理层 | 云端模型 (可选) | OpenAI / Anthropic API | 降级或增强推理能力 |
| 数据层 | PostgreSQL | PostgreSQL 15 | 主数据库（项目、用户、流程状态等） |
| 数据层 | PostgreSQL (Gitea) | PostgreSQL 15 | Gitea 代码托管数据库 |
| 数据层 | Redis | Redis 7 | 缓存、Celery Broker、Session 存储 |
| 集成层 | Gitea | Gitea 1.21 | 代码托管、代码审查、CI 触发 |
| 集成层 | Hermes Gateway | HTTP REST API | 命名 Agent 进程通信网关 |
| 监控层 | Prometheus | Prometheus 2.48+ | 指标采集和查询 |
| 监控层 | Grafana | Grafana 10.0+ | 仪表盘可视化 |
| 监控层 | Loki | Loki 2.9+ | 日志聚合 |
| 监控层 | Alertmanager | Alertmanager 0.26+ | 告警管理 |
| 监控层 | OpenTelemetry | OTel 1.20+ | 分布式链路追踪 |

### 1.4 核心数据流

**主数据流 (16步流程)**:
1. 用户通过前端创建项目 -> Nginx -> FastAPI -> 写入 PostgreSQL
2. 海梅(项目经理)触发 16 步流程 -> 写入流程状态表 (project_steps)
3. FastAPI 调度 Celery Worker -> Celery 调用对应命名 Agent
4. Celery Worker -> HTTP 请求 Hermes Gateway -> 命名 Agent 进程执行
5. 命名 Agent -> 调用 Ollama 容器进行推理 -> 获得响应
6. 命名 Agent 将产出物写入项目目录 (/DevFlow/projects/{project_id}/)
7. 命名 Agent 返回执行结果 -> Gateway -> Celery Worker -> 更新 project_steps 状态
8. 后荣(QA)对产出物进行检验 -> qa_records 表记录检验结果
9. QA 通过后 -> 自动提交到 Gitea 代码库

**群聊消息流**:
1. Agent/用户发送消息 -> WebSocket -> WS Worker 处理
2. WS Worker -> 写入 group_messages 表 (PostgreSQL)
3. WS Worker -> 通过 WebSocket 广播给群内所有在线成员
4. 离线消息 -> 用户下次连接时通过 WebSocket 拉取

**16步流程状态变更**:
1. 每步开始: Celery Worker 写入 project_steps 表 (status=pending -> in_progress)
2. 每步执行中: 命名 Agent 定期更新进度到 project_steps 表 (progress 字段)
3. 每步完成: Celery Worker 更新 project_steps (status=completed, output_path, completed_at)
4. QA 检验: 后荣 写入 qa_records 表 (score, dimensions, feedback)
5. QA 不通过: project_steps 回退 (status=in_progress, qa_status=failed)
6. QA 通过: project_steps 更新 (qa_status=passed)，触发下一步

**命名 Agent 产出物持久化路径**:
- 需求分析: /DevFlow/projects/{project_id}/docs/requirements.md
- 架构设计: /DevFlow/projects/{project_id}/docs/architecture.md
- 后端设计: /DevFlow/projects/{project_id}/docs/backend_design.md
- 前端设计: /DevFlow/projects/{project_id}/docs/frontend_design.md
- 数据库设计: /DevFlow/projects/{project_id}/docs/database_design.md
- TDD 测试用例: /DevFlow/projects/{project_id}/tests/
- 源代码: /DevFlow/projects/{project_id}/src/
- 部署配置: /DevFlow/projects/{project_id}/deploy/
- 文档: /DevFlow/projects/{project_id}/docs/

---

## 2. 技术栈选型

### 2.1 后端技术栈

| 类别 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| Web 框架 | FastAPI | 0.109+ | 高性能异步框架，原生支持 WebSocket，类型安全 |
| 异步运行时 | Uvicorn | 0.27+ | ASGI 服务器，高性能，支持多 Worker |
| 任务队列 | Celery | 5.3+ | 成熟的任务队列框架，支持分布式 |
| 消息代理 | Redis | 7.x | 高性能，同时作为 Celery Broker 和缓存 |
| ORM | SQLAlchemy 2.0 | 2.0+ | 成熟的 Python ORM，支持异步 |
| 数据库迁移 | Alembic | 1.13+ | SQLAlchemy 官方迁移工具 |
| 容器编排 | Docker SDK | 7.0+ | Python Docker API 客户端，用于 Swarm Executor |
| 配置管理 | Pydantic Settings | 2.0+ | 类型安全的配置管理 |
| 日志 | Loguru | 0.7+ | 简洁易用的日志库 |
| 监控 | Prometheus Client | 0.19+ | 指标采集客户端 |

### 2.2 前端技术栈

| 类别 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| 框架 | Vue 3 | 3.4+ | 组合式 API，性能好，生态成熟 |
| 构建工具 | Vite | 5.0+ | 快速构建，HMR 热更新 |
| UI 组件 | Element Plus | 2.5+ | 成熟的 Vue 3 组件库 |
| 状态管理 | Pinia | 2.1+ | Vue 3 官方状态管理 |
| HTTP 客户端 | Axios | 1.6+ | 成熟的前端 HTTP 库 |
| WebSocket | 原生 WebSocket API | - | 实时通信 |
| 路由 | Vue Router | 4.2+ | Vue 3 官方路由 |

### 2.3 基础设施

| 类别 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| 反向代理 | Nginx | 1.24 | 稳定可靠，WebSocket 代理支持 |
| 数据库 | PostgreSQL | 15 | 关系型数据库，JSON 支持，ACID |
| 代码托管 | Gitea | 1.21 | 轻量级 Git 服务，自托管 |
| LLM 推理 | Ollama | 0.1+ | 本地 LLM 推理，支持多种模型 |
| 默认模型 | qwen2.5:72b-instruct-q4_K_M | - | 72B Q4 量化，平衡性能与质量 |
| Agent 框架 | Hermes | latest | 9 个命名 Agent 基于 Hermes Profile 运行 |
| 容器运行时 | Docker | 24.0+ | 容器编排，编程 Agent 隔离 |
| 进程管理 | systemd | - | 命名 Agent 宿主机进程管理 |

### 2.4 监控与可观测性技术栈

| 类别 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| 指标采集 | Prometheus | 2.48+ | 开源指标存储和查询，生态成熟 |
| 可视化 | Grafana | 10.0+ | 仪表盘可视化，支持多种数据源 |
| 日志聚合 | Loki | 2.9+ | 轻量级日志聚合，与 Grafana 集成 |
| 告警 | Alertmanager | 0.26+ | Prometheus 告警管理，支持邮件/Webhook |
| 链路追踪 | OpenTelemetry | 1.20+ | 分布式追踪标准，与 Prometheus/Grafana 集成 |

---

## 3. 模块详细设计

### 3.1 项目与用户管理模块

**职责**: 用户认证、项目管理、权限控制

**核心接口**:
- POST /api/v1/projects — 创建项目
- GET /api/v1/projects/{id} — 获取项目详情
- GET /api/v1/projects — 项目列表
- POST /api/v1/projects/{id}/archive — 归档项目

**数据库表**:
- users (用户表)
- projects (项目表)
- project_members (项目成员关联表)
- roles (角色表)

**设计要点**:
- 项目创建时自动生成 Gitea 代码仓库
- 项目状态: active / archived / paused
- 权限模型: owner / admin / member / viewer

### 3.2 16步流程调度模块

**职责**: 管理 16 步开发流程的状态流转和任务调度

**核心接口**:
- POST /api/v1/projects/{id}/workflow/start — 启动 16 步流程
- GET /api/v1/projects/{id}/workflow/status — 获取流程状态
- GET /api/v1/projects/{id}/workflow/steps — 获取步骤详情
- POST /api/v1/projects/{id}/workflow/steps/{step}/retry — 重试失败步骤

**数据库表**:
- project_steps (项目步骤表):
  - id, project_id, step_number (1-16), step_name
  - status (pending/in_progress/completed/failed/skipped)
  - assigned_agent (执行 Agent 名称)
  - progress (0-100), output_path, qa_status
  - started_at, completed_at, error_message

**流程状态机**:
```
pending -> in_progress -> (completed + qa_passed) -> next_step
                              -> (completed + qa_failed) -> in_progress (retry)
                              -> failed -> (retry) -> in_progress
```

**调度逻辑**:
1. 海梅(项目经理)确认步骤条件满足
2. FastAPI 触发 Celery 任务 `execute_step(project_id, step_number)`
3. Celery Worker 根据步骤分配对应的命名 Agent
4. 调用 Hermes Gateway 执行 Agent 任务
5. Agent 完成后，结果写入项目目录
6. 后荣(QA)自动对产出物进行检验
7. QA 通过后更新状态并触发下一步，QA 不通过则回退并通知重做

### 3.3 Agent 蜂群调度模块

**职责**: 管理编程 Agent 蜂群的创建、调度和销毁

**核心接口**:
- POST /api/v1/projects/{id}/swarm/create — 创建蜂群
- GET /api/v1/projects/{id}/swarm/status — 蜂群状态
- POST /api/v1/projects/{id}/swarm/task — 下发任务到蜂群

**蜂群成员** (由后发或后达建立):
- 编程 Agent: CodeArts (代码编写)
- 由 Swarm Executor 动态编排容器执行

**蜂群生命周期**:
1. 后发/后达根据任务创建蜂群
2. Swarm Executor 接收任务，按并发上限创建编程 Agent 容器
3. 容器挂载项目工作空间，执行编码/测试任务
4. 任务完成后，结果通过三种方式回传:
   - **共享挂载卷文件轮询**: Swarm Executor 轮询挂载卷中的结果文件
   - **Docker 日志采集**: 采集容器 stdout/stderr 日志
   - **Swarm Executor HTTP 回调**: 容器主动调用 Swarm Executor 回调接口
5. 所有容器任务完成，蜂群解散，容器自动销毁

**并发控制**:
- 全局上限: 16 个编程 Agent 容器
- 单项目上限: 4 个编程 Agent 容器
- 资源限制: 每个容器 4 核 CPU / 8GB 内存

### 3.4 QA 门控模块

**职责**: 由后荣对每个 Agent 产出物进行质量检验

**核心接口**:
- POST /api/v1/projects/{id}/qa/inspect — 触发 QA 检验
- GET /api/v1/projects/{id}/qa/records — QA 记录列表
- GET /api/v1/projects/{id}/qa/records/{id} — QA 详情

**数据库表**:
- qa_records (QA 记录表):
  - id, project_id, step_number, output_path
  - score (0-100, 各维度加权平均)
  - completeness_score, consistency_score, verifiability_score
  - clarity_score, format_score
  - status (passed/failed), feedback
  - inspected_by (Agent 名称, 固定为 HouRong)
  - inspected_at, retried_count

**检验维度与权重**:
| 维度 | 权重 | 检验内容 |
|------|------|----------|
| 完整性 | 25% | 是否包含所有必需章节和内容 |
| 一致性 | 25% | 前后表述是否一致，无矛盾 |
| 可验证性 | 20% | 是否有明确的验收标准和量化指标 |
| 无歧义性 | 20% | 表述是否清晰，无模糊语言 |
| 格式规范 | 10% | 是否符合文档格式规范 |

**合格阈值**: 总分 >= 70 分且无单项低于 50 分

### 3.5 群聊协作模块

**职责**: 项目管理群聊，支持人类用户和 Agent 之间的实时沟通

**核心接口**:
- WS /ws/v1/groups/{id} — WebSocket 连接
- GET /api/v1/groups/{id}/messages — 消息历史
- POST /api/v1/groups/{id}/messages — 发送消息

**数据库表**:
- groups (群聊表):
  - id, project_id, name, created_at
- group_members (群成员表):
  - id, group_id, user_id (NULL 表示 Agent)
  - agent_name (NULL 表示人类用户)
  - joined_at
- group_messages (消息表):
  - id, group_id, sender_id (人类用户 ID 或 NULL)
  - sender_type (human/agent), sender_agent_name (NULL 表示人类)
  - content, message_type (text/file/image)
  - attachments (JSON), created_at

**消息推送**:
- 在线用户: WebSocket 实时推送
- 离线用户: 下次连接时拉取未读消息
- Agent 消息: 由 WS Worker 写入数据库并通过 WebSocket 广播

### 3.6 代码库管理模块

**职责**: 与 Gitea 集成，管理代码仓库

**核心接口**:
- POST /api/v1/projects/{id}/repo/init — 初始化代码仓库
- POST /api/v1/projects/{id}/repo/commit — 提交代码
- GET /api/v1/projects/{id}/repo/commits — 提交历史
- POST /api/v1/projects/{id}/repo/review — 创建代码审查

**集成方式**:
- 项目创建时自动在 Gitea 创建仓库
- 通过 Gitea API 进行仓库操作
- QA 通过后自动提交代码到仓库
- 支持 Git Hook 触发 CI/CD 流程

### 3.7 通知推送模块

**职责**: 项目状态变更、任务完成、QA 结果等通知推送

**推送渠道**:
- WebSocket 实时推送 (前端)
- 邮件通知 (可选)
- 移动端推送 (可选)

**通知类型**:
- 项目状态变更 (创建、启动、暂停、归档)
- 步骤状态变更 (开始、完成、失败、重试)
- QA 检验结果 (通过、不通过)
- 群聊新消息
- 安全告警

### 3.8 文档管理模块

**职责**: 由后贵管理项目文档一致性

**核心接口**:
- GET /api/v1/projects/{id}/docs — 文档列表
- GET /api/v1/projects/{id}/docs/{path} — 获取文档
- POST /api/v1/projects/{id}/docs/sync — 触发文档同步检查

**文档目录结构**:
```
/DevFlow/projects/{project_id}/docs/
├── requirements.md          # 需求分析 (后兴)
├── architecture.md          # 架构设计 (后旺)
├── backend_design.md        # 后端设计 (后旺)
├── frontend_design.md       # 前端设计 (后旺)
├── database_design.md       # 数据库设计 (后旺)
├── test_plan.md             # 测试计划 (后达)
├── deploy_config.md         # 部署配置 (后富)
├── security_audit.md        # 安全审计 (后华)
└── qa_reports/              # QA 报告 (后荣)
    └── step_{N}_qa.md
```

**一致性检查**:
- 任一文档修改后，后贵检查其他文档是否需要同步更新
- 检查术语一致性、版本号同步、交叉引用有效性

---

## 4. Agent 调度与资源管理

### 4.1 命名 Agent 架构

**9 个命名 Agent 角色**:

| 序号 | 名称 | 角色 | Hermes Profile | 主要职责 |
|------|------|------|----------------|----------|
| 1 | 海梅 (HaiMei) | 项目经理 | default | 任务分派、协调、进度管理 |
| 2 | 后兴 (HouXing) | 需求分析师 | houxing | 需求分析、SRS 编写 |
| 3 | 后旺 (HouWang) | 架构设计师 | houwang | 架构/前后端/数据库设计 |
| 4 | 后发 (HouFa) | 程序员 | houfa | 编程 Agent 蜂群建立与监督 |
| 5 | 后达 (HouDa) | 测试员 | houda | 测试 Agent 蜂群建立与执行 |
| 6 | 后富 (HouFu) | CI/CD 工程师 | houfu | 环境搭建、部署 |
| 7 | 后贵 (HouGui) | 文档管理员 | hougui | 文档一致性管理 |
| 8 | 后荣 (HouRong) | QA | hourong | 质量检验、门控 |
| 9 | 后华 (HouHua) | 安全员 | houhua | 代码审计、安全测试 |

**部署模型**:
- 每个命名 Agent 运行在宿主机上，作为独立的 Hermes Profile 进程
- 通过 systemd 服务单元管理
- 通过 Hermes Gateway API (HTTP) 被 Celery Worker 调度
- 9 个 Agent 共享单一 Ollama 容器实例进行推理

### 4.2 命名 Agent 调度流程

```
Celery Worker                    Hermes Gateway               命名 Agent 进程
      |                              |                              |
      |--- HTTP POST /execute ------>|                              |
      |   {profile, prompt, task}    |                              |
      |                              |--- HTTP POST /chat ---------->
      |                              |   {profile, message}         |
      |                              |                              |--- Ollama API
      |                              |                              |--- 推理结果
      |                              |<=============================|
      |                              |<--- HTTP 200 + result ------|
      |<-- HTTP 200 + result -------|                              |
```

**超时设置**:
- 默认超时: 30 分钟
- 超时后 Celery Worker 标记任务失败
- 支持 3 次重试机制
- 重试策略: 指数退避 (1min, 5min, 15min)

### 4.3 命名 Agent 资源共享

**Ollama 资源共享**:
- 9 个命名 Agent 共享单一 Ollama 容器
- Ollama 内置请求队列处理并发请求
- 当多个 Agent 同时请求推理时，Ollama 按 FIFO 队列调度
- 模型加载一次，内存共享

**文件系统共享**:
- 所有 Agent 挂载 /DevFlow/projects/ 目录
- 项目目录按 project_id 隔离
- Agent 只能读写所属项目的目录

**进程间通信**:
- Celery Worker 通过 HTTP 调用 Gateway API
- Gateway API 转发到对应的 Hermes Profile 进程
- 响应通过 HTTP 返回给调用方

### 4.4 宿主资源容量规划

**宿主机硬件配置需求**:

| 资源项 | 需求 | 说明 |
|--------|------|------|
| CPU 核心 | 32+ 核 | 基础设施(4核) + Ollama(8核) + 命名Agent(9核) + 编程Agent容器峰值(64核理论/实际并发16个=64核) + 安全余量 |
| 内存 | 128GB+ | 基础设施(8GB) + Ollama 模型(48GB) + 命名Agent(18GB) + 编程Agent容器峰值(128GB理论/实际并发16个=128GB) + 安全余量 |
| GPU 显存 | 48GB+ | Ollama 72B Q4 模型加载 (推荐 NVIDIA A100/RTX 4090) |
| 存储空间 | 1TB+ SSD | 项目文件、代码仓库、模型文件、日志 |

**详细资源分解**:

| 组件 | CPU | 内存 | GPU | 说明 |
|------|-----|------|-----|------|
| FastAPI 后端 | 2 核 | 4GB | - | 2 Workers |
| WS Worker | 1 核 | 2GB | - | 1 Worker |
| Celery Worker | 2 核 | 4GB | - | 8 并发 |
| Celery Beat | 0.5 核 | 0.5GB | - | 定时任务 |
| Swarm Executor | 0.5 核 | 1GB | - | 容器管理 |
| PostgreSQL (主库) | 2 核 | 8GB | - | 主数据库 |
| PostgreSQL (Gitea) | 1 核 | 4GB | - | Gitea 数据库 |
| Redis | 1 核 | 4GB | - | 缓存/队列 |
| Gitea | 1 核 | 2GB | - | 代码托管 |
| Nginx | 0.5 核 | 0.5GB | - | 反向代理 |
| Ollama | 8 核 | 48GB | 48GB GPU | 72B Q4 模型 |
| 命名 Agent (9个) | 9 核 | 18GB (2GB/个) | 共享 Ollama | 宿主进程 |
| 编程 Agent 容器 (峰值16个) | 64 核 (4核/个) | 128GB (8GB/个) | - | 并发上限 |
| 基础设施监控 | 1 核 | 4GB | - | Prometheus/Grafana/Loki |
| **总计** | **~93.5 核** | **~230.5GB** | **48GB GPU** | **峰值需求** |

**实际运行建议**:
- 编程 Agent 容器不会同时达到 16 个峰值，建议按 8 个并发规划
- 实际推荐: 32 核 CPU / 128GB 内存 / 48GB GPU 显存
- 预留 30% 安全余量

### 4.5 数据库容量规划 (V14新增)

**PostgreSQL (主库)**:
- **最大连接数**: 200 (shared_buffers=4GB, effective_cache_size=12GB)
  - FastAPI 后端连接池: 20 (SQLAlchemy pool_size=20, max_overflow=10)
  - Celery Worker 连接池: 10
  - WS Worker 连接池: 5
  - 预留: 165 (用于备份、监控、管理连接)
- **存储规划**:
  - 初始容量: 50GB (含索引)
  - 预估年增长率: 每个项目约 50MB 元数据，100 个项目约 5GB/年
  - 日志表(group_messages、agent_execution_logs)采用分区表按月分区
  - 建议配置 pg_partman 自动管理分区生命周期
- **IOPS 规划**:
  - 随机读写: 5000 IOPS (SSD)
  - 顺序写入: 500MB/s (日志追加写入)
  - WAL 日志独立挂载到高性能磁盘
- **关键参数**:
  - work_mem: 64MB (支持复杂查询排序)
  - maintenance_work_mem: 512MB (VACUUM/索引构建)
  - checkpoint_completion_target: 0.9

**PostgreSQL (Gitea)**:
- **最大连接数**: 100
- **存储规划**: 初始 10GB，按代码仓库数量线性增长
- **IOPS 规划**: 1000 IOPS (SSD)

**Redis**:
- **内存规划**: maxmemory=4GB
  - Celery 任务队列: 512MB
  - Session 存储: 256MB (50 并发用户 x 5KB/session x 冗余)
  - 缓存层: 2GB (项目元数据、Agent 执行结果缓存)
  - 预留: 1GB (峰值缓冲)
- **持久化**: AOF everysec + RDB 每 15 分钟
- **最大客户端连接**: 10000

**Nginx**:
- **并发连接数**: worker_connections=4096, worker_processes=auto (CPU核心数)
- **最大并发请求**: 16384 (4 workers x 4096 connections)
- **WebSocket 连接**: 单实例支持 2000+ 长连接
- **静态文件缓存**: 开启 sendfile + aio
- **关键参数**:
  - keepalive_timeout: 65s
  - keepalive_requests: 1000
  - client_max_body_size: 50MB (支持大文件上传)

### 4.6 编程 Agent 容器管理

**容器规格**:
- 镜像: devflow/coding-agent:latest
- CPU 限制: 4 核
- 内存限制: 8GB
- 磁盘: 挂载项目工作空间 (只读基础代码 + 读写工作目录)
- 网络: 受限网络 (仅访问 Ollama、Gitea、内部服务)

**生命周期**:
1. Swarm Executor 接收 Celery 任务
2. 检查全局/单项目并发上限
3. 创建 Docker 容器，挂载项目工作空间
4. 容器启动，执行编码/测试任务
5. 任务完成，结果回传 (见 4.7 节)
6. 容器自动销毁，释放资源

**并发控制**:
- 全局并发上限: 16 个容器
- 单项目并发上限: 4 个容器
- 超出上限时任务进入队列等待
- 优先级: QA 不通过重试 > 正常步骤 > 并行任务

### 4.7 编程 Agent 结果回传机制

**三种结果回传方式**:

1. **共享挂载卷文件轮询**:
   - 编程 Agent 容器将结果写入共享挂载卷的指定路径
   - Swarm Executor 定期轮询该路径 (5 秒间隔)
   - 检测到结果文件后，读取并上传到 Celery 任务结果
   - 适用场景: 大文件产出 (代码文件、设计文档)

2. **Docker 日志采集**:
   - Swarm Executor 通过 Docker API 实时采集容器 stdout/stderr
   - 解析日志中的结构化输出 (JSON 格式)
   - 适用场景: 进度更新、状态通知、错误信息

3. **Swarm Executor HTTP 回调**:
   - 编程 Agent 容器完成任务后，主动调用 Swarm Executor 的回调接口
   - POST /internal/swarm/callback/{container_id}
   - Body 包含: 任务 ID、状态、结果摘要、产出文件路径
   - 适用场景: 任务完成通知、结构化结果

**结果回传时序**:
```
编程 Agent 容器           Swarm Executor          Celery Worker
       |                       |                       |
       |--- 写入共享挂载卷 ---->|                       |
       |                       |                       |
       |--- Docker 日志 ------->| (实时采集进度)        |
       |                       |                       |
       |--- HTTP 回调 -------->|--- 轮询验证结果 ------|
       |                       |--- 更新任务状态 ------>|
       |                       |                       |--- 更新 project_steps
       |--- 容器销毁 ---------->                       |
```

### 4.8 编程 Agent 安全隔离

**容器安全策略**:
- 非 root 用户运行容器
- 只挂载必要目录 (项目工作空间、只读依赖)
- 网络白名单: 仅允许访问内部服务 (Ollama、Gitea)
- 禁用 Docker 特权模式
- 资源限制: CPU、内存、磁盘 I/O 限制
- 容器自动销毁: 任务完成后立即销毁，不保留状态

**网络隔离**:
- 编程 Agent 容器在独立的 Docker 网络中
- 仅允许访问: Ollama 容器 (11434 端口)、Gitea 容器 (3000 端口)
- 禁止访问宿主机网络、外部网络

**文件系统隔离**:
- 只读挂载: /DevFlow/projects/{project_id}/src/ (基础代码)
- 读写挂载: /DevFlow/projects/{project_id}/work/ (工作目录)
- 禁止挂载宿主机敏感目录

### 4.9 命名 Agent 进程管理

**systemd 服务单元配置**:

每个命名 Agent 对应一个 systemd 服务，以 houwang 为例:

```ini
[Unit]
Description=DevFlow Agent - HouWang (架构设计师)
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=jim
WorkingDirectory=/home/jim/.hermes/profiles/houwang
ExecStart=/home/jim/.herms/bin/hermes agent --profile houwang --gateway-port 8083
Restart=always
RestartSec=10
Environment=HERMES_PROFILE=houwang
EnvironmentFile=/home/jim/.hermes/profiles/houwang/.env

[Install]
WantedBy=multi-user.target
```

**服务单元列表**:

| Agent | 服务名 | Gateway 端口 | Profile |
|-------|--------|-------------|---------|
| 海梅 | devflow-haimei.service | 8080 | default |
| 后兴 | devflow-houxing.service | 8081 | houxing |
| 后旺 | devflow-houwang.service | 8082 | houwang |
| 后发 | devflow-houfa.service | 8083 | houfa |
| 后达 | devflow-houda.service | 8084 | houda |
| 后富 | devflow-houfu.service | 8085 | houfu |
| 后贵 | devflow-hougui.service | 8086 | hougui |
| 后荣 | devflow-hourong.service | 8087 | hourong |
| 后华 | devflow-houhua.service | 8088 | houhua |

**崩溃自动重启策略**:
- Restart=always: 任何退出码都会触发重启
- RestartSec=10: 重启前等待 10 秒
- StartLimitBurst=5: 5 次重启后进入失败状态
- StartLimitIntervalSec=60: 60 秒内的重启计数窗口

**健康检查机制**:
- Celery Worker 调用 Gateway API 前进行健康检查
- HTTP GET /health 端点返回 Agent 状态
- 健康检查超时: 5 秒
- 连续 3 次健康检查失败，标记 Agent 为不可用
- 不可用时，任务进入等待队列或切换备用 Agent

---

## 5. 高可用与容灾方案

### 5.1 可用性目标

- **目标可用性**: 99% (月停机时间 < 7.3 小时)
- **核心服务可用性**: FastAPI、PostgreSQL、Redis、Ollama
- **非核心服务**: Gitea、监控组件

### 5.2 Docker 自动重启策略

所有容器配置 `restart: unless-stopped`:

```yaml
services:
  backend:
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### 5.3 健康检查与故障恢复

**检查项**:
- FastAPI /health: 数据库连接、Redis 连接、Ollama 连接
- Celery Worker: 心跳信号 (每 30 秒)
- Ollama: HTTP GET /api/tags 响应
- PostgreSQL: pg_isready 检查
- Redis: ping 命令响应

**故障恢复流程**:
1. 健康检查失败 -> 触发告警 (Alertmanager)
2. Docker 自动重启容器 (restart 策略)
3. 若重启 3 次仍失败 -> 通知管理员
4. 管理员介入排查或切换备用实例

### 5.4 数据备份与恢复

**备份策略**:
- PostgreSQL 数据库: 每日凌晨 2:00 全量备份 (pg_dump)
- Gitea 数据库: 每日凌晨 2:30 全量备份
- 项目文件: 实时 Git 版本控制 + 每日快照
- Redis: AOF 持久化 + RDB 快照 (每 15 分钟)

**备份存储**:
- 本地: /backups/devflow/ (保留 7 天)
- 远程: S3 兼容存储 (保留 30 天)

**恢复目标**:
- RPO (数据恢复点目标): 1 小时
- RTO (恢复时间目标): 4 小时

### 5.5 Ollama 故障降级策略 (V14 完善)

**三级降级策略**:

**第一级 — 云端模型切换 (自动)**:
- **触发条件**: Ollama 健康检查连续 3 次失败 (间隔 30 秒，即 90 秒后触发)
- **自动切换流程**:
  1. Celery Worker 调用 Ollama 前执行健康检查 (HTTP GET /api/tags)
  2. 健康检查失败计数器 +1，达到阈值 3 时标记 Ollama 为 down
  3. Gateway 层自动将推理请求路由至云端模型 API (OpenAI/Anthropic)
  4. 云端 API Key 从 .env 读取 (FALLBACK_OPENAI_API_KEY / FALLBACK_ANTHROPIC_API_KEY)
  5. 降级模型配置: FALLBACK_MODEL_PROVIDER=openai, FALLBACK_MODEL=gpt-4
  6. Prometheus 指标 `ollama_status` 置为 0，`fallback_active` 置为 1
  7. Alertmanager 触发告警通知管理员
- **降级期间功能限制**:
  - 推理成本增加 (按云端 API 调用计费)
  - 响应延迟可能增加 (网络依赖)
  - 输出格式可能与本地模型略有差异 (需适配不同模型的 prompt 模板)
  - 不受本地模型大小限制，但受云端 API 速率限制 (如 OpenAI RPM/TPM 限制)

**第二级 — 排队限流 (自动)**:
- **触发条件**: Ollama 部分可用 (响应慢但非完全不可用，P99 延迟 > 60 秒)
- **自动限流流程**:
  1. 启用请求排队机制，最大排队数: 50
  2. 排队超时: 5 分钟
  3. 超过排队数则返回 503，建议稍后重试
  4. 排队队列按优先级排序: QA 重试 > 正常步骤 > 并行任务
- **降级期间功能限制**:
  - 新增任务排队等待，用户体验延迟增加
  - 低优先级任务可能被丢弃 (超时 5 分钟)

**第三级 — 任务延迟 (手动)**:
- **触发条件**: Ollama 完全不可用且无云端模型配置 (或云端 API 也不可用)
- **手动操作流程**:
  1. 标记受影响的任务为 pending_retry 状态
  2. 前端显示"推理服务不可用，任务已暂停"
  3. Celery Beat 每 10 分钟检查 Ollama 状态
  4. Ollama 恢复后自动重新执行排队任务
- **降级期间功能限制**:
  - 所有依赖推理的任务暂停，16步流程停滞
  - 群聊消息仍可发送 (不依赖推理)
  - 项目浏览、文档查看等只读功能正常

**故障恢复后回切策略**:
1. **自动回切条件**: Ollama 健康检查连续 5 次成功 (间隔 30 秒)
2. **回切流程**:
   - 逐步将请求从云端模型切换回 Ollama (先 10% 流量，再 50%，最后 100%)
   - 灰度回切期间同时监控 Ollama 延迟和错误率
   - 回切完成后 Prometheus 指标 `ollama_status` 恢复为 1，`fallback_active` 恢复为 0
   - Alertmanager 发送恢复通知
3. **回切失败处理**: 若灰度回切期间 Ollama 再次异常，立即切回云端模型并重新告警
4. **数据一致性**: 降级期间使用云端模型生成的产出物与本地模型保持一致，QA 检验标准不变

---

## 6. 安全设计 (V14 完善)

### 6.1 认证与授权

**认证方式 (JWT + Refresh Token)**:
- **Access Token**: JWT，有效期 2 小时
  - 签发: 用户登录成功后生成
  - 存储: 前端内存存储 (不持久化)
  - 载荷: user_id, role, project_ids, exp, iat, jti
  - 签名: RS256 (非对称签名，私钥服务器保管)
- **Refresh Token**: 随机字符串，有效期 7 天
  - 存储: Redis (key=refresh:{token}, value=user_id, TTL=7天)
  - 用途: Access Token 过期后换取新 token
  - 撤销: 用户登出时从 Redis 删除
- **Token 刷新流程**:
  1. 前端检测到 Access Token 即将过期 (提前 5 分钟)
  2. POST /api/v1/auth/refresh 携带 Refresh Token
  3. 后端验证 Refresh Token (查 Redis)
  4. 验证通过则签发新的 Access Token + Refresh Token (旧 Refresh Token 失效)

**权限模型 (RBAC)**:
- 角色: owner / admin / member / viewer
- 权限粒度: 项目级别 + 操作级别
- 权限矩阵:

| 操作 | owner | admin | member | viewer |
|------|-------|-------|--------|--------|
| 创建项目 | Y | Y | - | - |
| 删除项目 | Y | - | - | - |
| 启动流程 | Y | Y | - | - |
| 查看进度 | Y | Y | Y | Y |
| 发送消息 | Y | Y | Y | Y |
| 修改配置 | Y | Y | - | - |
| 查看代码 | Y | Y | Y | Y |
| 提交代码 | Y | Y | Y | - |

### 6.2 API 接口鉴权

**鉴权中间件**:
- 所有 /api/v1/* 接口强制 JWT 认证
- WebSocket 连接: 连接 URL 携带 token 参数 (ws://host/ws?v=token)
- 健康检查接口 (/health) 和公开接口 (/docs) 无需认证
- 鉴权失败返回 401 Unauthorized
- 权限不足返回 403 Forbidden

**速率限制**:
- 全局: 1000 请求/分钟/IP
- API: 100 请求/分钟/user
- WebSocket 消息: 50 条/分钟/user
- 由 Nginx 层 (limit_req) + 应用层 (slowapi) 双重控制

### 6.3 敏感配置管理

**存储方式**:
- API 密钥: .env 文件 + systemd EnvironmentFile
- 数据库密码: .env 文件，数据库 URL 格式含密码
- Ollama API Key (如需要): .env 文件
- 证书文件: /etc/ssl/ 目录，权限 600
- 云端模型 API Key: .env 文件 (FALLBACK_OPENAI_API_KEY 等)

**访问控制**:
- .env 文件权限: 600 (仅文件所有者可读)
- 容器内通过环境变量传递，不挂载 .env 文件明文
- Docker Secret (可选): 生产环境推荐使用 Docker Secret 管理敏感信息
- 日志脱敏: 日志中出现的 API Key、密码等自动脱敏 (替换为 ****)

**密钥轮换**:
- Access Token 私钥: 每 90 天轮换
- 数据库密码: 每 90 天轮换
- API 密钥: 发现泄露后立即轮换

### 6.4 数据传输加密

- **外部通信**: Nginx 层 SSL/TLS 终止 (TLS 1.2+)
  - 证书: Let's Encrypt 自动续期
  - 强制 HTTPS (HTTP 301 重定向)
  - HSTS 头部: max-age=31536000
- **内部通信**: 容器间使用 Docker 内网 (docker-compose 默认网络隔离)
  - 命名 Agent 与 Gateway API: 宿主机 localhost 通信 (127.0.0.1)
  - 编程 Agent 容器与内部服务: Docker 自定义网络，仅白名单端口
- **数据加密**: 数据库敏感字段 (如用户密码) 使用 bcrypt 哈希存储

### 6.5 容器间通信安全

- Docker 自定义网络: devflow-internal
- 编程 Agent 容器网络白名单:
  - Ollama: 11434 端口
  - Gitea: 3000 端口
  - Swarm Executor: 8090 端口 (回调)
- 禁止编程 Agent 容器访问:
  - 宿主机网络
  - 外部网络 (出站连接)
  - PostgreSQL 数据库 (防止直接数据库操作)
  - Redis (防止缓存注入)

### 6.6 命名 Agent 与 Gateway API 认证机制 (V14 新增)

**内部认证方案**:
- Celery Worker 调用命名 Agent 时，通过 Gateway API 进行认证
- 认证方式: 内部 API Key (非 JWT，简化内部通信)
- 每个命名 Agent 分配独立的内部 API Key:
  - 存储在 .env 文件中 (INTERNAL_GATEWAY_KEY_{PROFILE})
  - Gateway API 验证请求头 X-Gateway-Key
- 认证失败返回 401，记录审计日志
- API Key 轮换: 每 90 天自动轮换

**请求签名 (可选增强)**:
- 对敏感操作 (如删除项目、修改配置) 使用 HMAC-SHA256 签名
- 签名内容: timestamp + method + path + body_hash
- 时间戳有效期: 5 分钟 (防止重放攻击)

### 6.7 审计日志

**记录内容**:
- 用户登录/登出
- 项目创建/删除/归档
- 代码提交/审查
- Agent 任务执行 (开始/完成/失败)
- QA 检验结果
- 安全相关操作 (权限变更、配置修改)
- 内部 API Key 认证失败事件

**日志存储**:
- 应用日志: Loki 聚合
- 审计日志: 独立 PostgreSQL 表 (audit_logs)
- 保留期: 90 天
- 审计日志不可篡改 (append-only)

---

## 7. 监控与可观测性 (V14 完善)

### 7.1 监控工具选型

| 组件 | 工具 | 版本 | 部署方式 |
|------|------|------|----------|
| 指标采集 | Prometheus | 2.48+ | Docker 容器 |
| 可视化 | Grafana | 10.0+ | Docker 容器 |
| 日志聚合 | Loki | 2.9+ | Docker 容器 |
| 告警管理 | Alertmanager | 0.26+ | Docker 容器 |
| 链路追踪 | OpenTelemetry | 1.20+ | SDK 嵌入应用 |

**Prometheus 采集目标**:
- FastAPI 后端 (exporter: prometheus-client, /metrics 端点)
- Celery Worker (exporter: celery-prometheus-exporter)
- Redis (exporter: redis-exporter)
- PostgreSQL (exporter: postgres-exporter)
- Nginx (stub_status 模块)
- Docker 容器资源 (exporter: cadvisor)
- 宿主机资源 (exporter: node-exporter)
- Ollama (自定义 exporter, /api/tags + 响应时间)

### 7.2 关键监控指标定义

**应用层指标**:
| 指标名称 | 类型 | 说明 | 采集方式 |
|----------|------|------|----------|
| http_request_duration_seconds | Histogram | API 请求延迟 (P50/P95/P99) | prometheus-client |
| http_request_total | Counter | API 请求总数 (按 method/path/status) | prometheus-client |
| http_request_errors_total | Counter | API 错误总数 (5xx) | prometheus-client |
| websocket_connections_active | Gauge | 活跃 WebSocket 连接数 | 自定义 |
| websocket_messages_total | Counter | WebSocket 消息收发总数 | 自定义 |

**Agent 执行指标**:
| 指标名称 | 类型 | 说明 | 采集方式 |
|----------|------|------|----------|
| agent_task_duration_seconds | Histogram | Agent 任务执行时间 | Celery exporter |
| agent_task_success_total | Counter | Agent 任务成功数 (按 profile) | Celery exporter |
| agent_task_failure_total | Counter | Agent 任务失败数 (按 profile/原因) | Celery exporter |
| agent_task_retry_total | Counter | Agent 任务重试次数 | Celery exporter |
| agent_queue_length | Gauge | Celery 待处理任务队列长度 | Celery exporter |

**资源指标**:
| 指标名称 | 类型 | 说明 | 采集方式 |
|----------|------|------|----------|
| container_cpu_usage_seconds_total | Counter | 容器 CPU 使用率 | cadvisor |
| container_memory_usage_bytes | Gauge | 容器内存使用量 | cadvisor |
| node_memory_MemAvailable_bytes | Gauge | 宿主机可用内存 | node-exporter |
| node_filesystem_avail_bytes | Gauge | 磁盘可用空间 | node-exporter |
| gpu_memory_used_bytes | Gauge | GPU 显存使用量 | dcgm-exporter |

**推理层指标**:
| 指标名称 | 类型 | 说明 | 采集方式 |
|----------|------|------|----------|
| ollama_request_duration_seconds | Histogram | Ollama 推理响应时间 | 自定义 exporter |
| ollama_request_queue_length | Gauge | Ollama 请求队列长度 | 自定义 exporter |
| ollama_status | Gauge | Ollama 健康状态 (1=正常, 0=故障) | 自定义 exporter |
| fallback_active | Gauge | 降级模式是否激活 (1=激活, 0=正常) | 自定义 exporter |

**数据库指标**:
| 指标名称 | 类型 | 说明 | 采集方式 |
|----------|------|------|----------|
| pg_stat_activity_count | Gauge | PostgreSQL 活跃连接数 | postgres-exporter |
| pg_stat_database_tup_fetched | Counter | 数据查询行数 | postgres-exporter |
| pg_stat_user_tables_n_dead_tup | Gauge | 死元组数量 (VACUUM 指标) | postgres-exporter |
| redis_connected_clients | Gauge | Redis 连接数 | redis-exporter |
| redis_used_memory_bytes | Gauge | Redis 内存使用量 | redis-exporter |

### 7.3 告警阈值设定

**关键告警规则 (Alertmanager)**:

| 告警名称 | 条件 | 严重级别 | 通知方式 |
|----------|------|----------|----------|
| HighAPIErrorRate | 5xx 错误率 > 5% (5min) | P1 (紧急) | 邮件 + Webhook |
| HighAPILatency | P95 延迟 > 1 秒 (5min) | P2 (警告) | 邮件 |
| CeleryQueueBacklog | 队列长度 > 100 (5min) | P2 (警告) | 邮件 |
| AgentTaskTimeout | Agent 任务执行 > 30 分钟 | P1 (紧急) | 邮件 + Webhook |
| AgentTaskFailureRate | 失败率 > 20% (10min) | P1 (紧急) | 邮件 + Webhook |
| OllamaDown | 健康检查连续 3 次失败 | P1 (紧急) | 邮件 + Webhook |
| OllamaHighLatency | P99 延迟 > 60 秒 (5min) | P2 (警告) | 邮件 |
| HighCPULoad | CPU 使用率 > 85% (5min) | P2 (警告) | 邮件 |
| HighMemoryUsage | 内存使用率 > 90% (5min) | P1 (紧急) | 邮件 + Webhook |
| DiskSpaceLow | 磁盘使用率 > 85% | P2 (警告) | 邮件 |
| DiskSpaceCritical | 磁盘使用率 > 95% | P1 (紧急) | 邮件 + Webhook |
| DatabaseConnectionHigh | 连接数 > 180/200 | P2 (警告) | 邮件 |
| RedisMemoryHigh | 内存使用 > 3.5GB/4GB | P2 (警告) | 邮件 |
| ContainerRestartLoop | 容器 10 分钟内重启 > 3 次 | P1 (紧急) | 邮件 + Webhook |
| NginxHighConnections | 活跃连接 > 3000 | P2 (警告) | 邮件 |

### 7.4 Grafana 仪表盘设计

**系统资源仪表盘**:
- CPU/内存/磁盘/GPU 使用率 (实时 + 趋势)
- Docker 容器资源分布
- 宿主机总体负载

**API 性能仪表盘**:
- 请求量 (每分钟/每小时)
- P50/P95/P99 延迟
- 错误率 (4xx/5xx 分布)
- 按接口路径分布的延迟和错误

**Agent 执行仪表盘**:
- 任务执行状态 (成功/失败/重试/排队)
- 各命名 Agent 任务耗时分布
- 蜂群容器并发数 (实时 + 峰值)
- 16步流程进度 (按项目)

**项目进度仪表盘**:
- 活跃项目数
- 各步骤完成率
- QA 通过率 (按步骤/按项目)
- 项目平均完成时间

### 7.5 链路追踪方案 (OpenTelemetry)

**追踪范围**:
- API 请求: Nginx -> FastAPI -> 业务逻辑 -> 响应
- 任务执行: FastAPI -> Celery -> Gateway -> 命名 Agent -> Ollama -> 响应
- 蜂群任务: Celery -> Swarm Executor -> 编程 Agent 容器 -> 结果回传

**实现方式**:
- FastAPI 集成 opentelemetry-instrumentation-fastapi
- Celery 集成 opentelemetry-instrumentation-celery
- HTTP 请求 (Gateway API) 自动注入 trace context
- 追踪数据通过 OTLP 协议发送到后端 (可选: Jaeger/Tempo)

**追踪上下文传播**:
```
用户请求 (trace_id=A)
  -> Nginx (propagate trace_id=A)
    -> FastAPI (span: http_request, trace_id=A)
      -> Celery (span: celery_task, trace_id=A, parent=http_request)
        -> Gateway API (span: gateway_call, trace_id=A, parent=celery_task)
          -> 命名 Agent (span: agent_execute, trace_id=A, parent=gateway_call)
            -> Ollama (span: ollama_inference, trace_id=A, parent=agent_execute)
```

**关键追踪指标**:
- 端到端延迟 (用户请求到响应)
- 各环节耗时分布 (API/Celery/Agent/Ollama)
- 错误链路定位 (哪个环节失败)

### 7.6 日志收集方案 (Loki)

**日志格式**: 所有应用输出 JSON 格式日志
```json
{"level": "INFO", "timestamp": "2026-06-13T10:00:00Z", "service": "backend", "message": "Task executed", "task_id": "abc123", "trace_id": "trace-xyz"}
```

**日志标签 (Labels)**:
- service: backend / ws-worker / celery-worker / swarm-executor / gitea
- level: INFO / WARN / ERROR
- project_id: 项目 ID (可选)

**日志保留**: 30 天 (Loki 本地存储)

**查询示例**:
- `{service="backend"} |~ "ERROR"` — 后端所有错误日志
- `{service="celery-worker"} | json | task_id="abc123"` — 特定任务日志
- `{level="ERROR"} |~ "timeout"` — 所有超时错误

---

## 8. 部署方案

### 8.1 部署架构

**部署模式**: 单机 + Docker Compose

```
宿主机 (Ubuntu 22.04 LTS)
├── systemd 管理的命名 Agent 进程 (9个)
├── Docker 容器:
│   ├── nginx (反向代理)
│   ├── backend (FastAPI, 2 Workers)
│   ├── ws-worker (WebSocket Worker, 1 Worker)
│   ├── celery-worker (异步任务, 8并发)
│   ├── celery-beat (定时任务, 独立容器)
│   ├── swarm-executor (编程Agent容器管理)
│   ├── postgres (主数据库)
│   ├── postgres-gitea (Gitea数据库)
│   ├── redis (缓存/队列)
│   ├── gitea (代码托管)
│   ├── ollama (LLM推理引擎)
│   ├── prometheus (指标采集)
│   ├── grafana (可视化)
│   ├── loki (日志聚合)
│   └── alertmanager (告警管理)
└── 动态创建的编程 Agent 容器 (按需)
```

### 8.2 Docker Compose 配置

```yaml
version: '3.9'

services:
  nginx:
    image: nginx:1.24-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - ws-worker
      - gitea
    restart: unless-stopped

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
    environment:
      - DATABASE_URL=postgresql://devflow:${DB_PASSWORD}@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - GITEA_API_URL=http://gitea:3000
      - OLLAMA_API_URL=http://ollama:11434
      - JWT_SECRET=${JWT_SECRET}
      - FALLBACK_OPENAI_API_KEY=${FALLBACK_OPENAI_API_KEY}
      - FALLBACK_MODEL_PROVIDER=${FALLBACK_MODEL_PROVIDER}
      - FALLBACK_MODEL=${FALLBACK_MODEL}
    volumes:
      - projects_data:/DevFlow/projects
    depends_on:
      - postgres
      - redis
      - ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  ws-worker:
    build: ./backend
    command: uvicorn app.websocket:ws_app --host 0.0.0.0 --port 8001 --workers 1
    environment:
      - DATABASE_URL=postgresql://devflow:${DB_PASSWORD}@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --concurrency=8 --loglevel=info
    environment:
      - DATABASE_URL=postgresql://devflow:${DB_PASSWORD}@postgres:5432/devflow
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - OLLAMA_API_URL=http://ollama:11434
      - GATEWAY_BASE_URL=http://host.docker.internal:8080
      - INTERNAL_GATEWAY_KEY_HAIMEI=${INTERNAL_GATEWAY_KEY_HAIMEI}
      - INTERNAL_GATEWAY_KEY_HOUXING=${INTERNAL_GATEWAY_KEY_HOUXING}
      - INTERNAL_GATEWAY_KEY_HOUWANG=${INTERNAL_GATEWAY_KEY_HOUWANG}
      - INTERNAL_GATEWAY_KEY_HOUFA=${INTERNAL_GATEWAY_KEY_HOUFA}
      - INTERNAL_GATEWAY_KEY_HOUDA=${INTERNAL_GATEWAY_KEY_HOUDA}
      - INTERNAL_GATEWAY_KEY_HOUFU=${INTERNAL_GATEWAY_KEY_HOUFU}
      - INTERNAL_GATEWAY_KEY_HOUGUI=${INTERNAL_GATEWAY_KEY_HOUGUI}
      - INTERNAL_GATEWAY_KEY_HOURONG=${INTERNAL_GATEWAY_KEY_HOURONG}
      - INTERNAL_GATEWAY_KEY_HOUHUA=${INTERNAL_GATEWAY_KEY_HOUHUA}
    volumes:
      - projects_data:/DevFlow/projects
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  celery-beat:
    build: ./backend
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped

  swarm-executor:
    build: ./swarm-executor
    command: python main.py --host 0.0.0.0 --port 8090
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - MAX_GLOBAL_CONCURRENT=16
      - MAX_PROJECT_CONCURRENT=4
      - CONTAINER_CPU=4
      - CONTAINER_MEMORY=8g
    volumes:
      - projects_data:/DevFlow/projects
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=devflow
      - POSTGRES_USER=devflow
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U devflow"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres-gitea:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=gitea
      - POSTGRES_USER=gitea
      - POSTGRES_PASSWORD=${GITEA_DB_PASSWORD}
    volumes:
      - postgres_gitea_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 4gb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  gitea:
    image: gitea/gitea:1.21
    environment:
      - DATABASE_URL=postgres:gitea:${GITEA_DB_PASSWORD}@postgres-gitea:5432/gitea
      - ROOT_URL=http://localhost:3000
    ports:
      - "3000:3000"
    volumes:
      - gitea_data:/data
      - projects_data:/DevFlow/projects
    depends_on:
      - postgres-gitea
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    command: ollama serve
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    restart: unless-stopped

  loki:
    image: grafana/loki:2.9
    volumes:
      - loki_data:/loki
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:0.26
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    restart: unless-stopped

volumes:
  postgres_data:
  postgres_gitea_data:
  redis_data:
  gitea_data:
  ollama_data:
  projects_data:
  prometheus_data:
  grafana_data:
  loki_data:
```

### 8.3 命名 Agent 宿主机部署

**systemd 服务安装**:
```bash
# 为每个命名 Agent 安装 systemd 服务
sudo cp devflow-haimei.service /etc/systemd/system/
sudo cp devflow-houxing.service /etc/systemd/system/
# ... (其他7个)

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用并启动所有 Agent
sudo systemctl enable --now devflow-haimei.service
sudo systemctl enable --now devflow-houxing.service
# ... (其他7个)
```

**Ollama 模型预热**:
```bash
# 启动 Ollama 后预热模型
docker exec ollama ollama pull qwen2.5:72b-instruct-q4_K_M
docker exec ollama ollama run qwen2.5:72b-instruct-q4_K_M "hello"
```

### 8.4 初始化流程

1. 克隆项目代码
2. 配置 .env 文件 (数据库密码、API 密钥、JWT 密钥等)
3. 启动 Docker Compose: `docker compose up -d`
4. 等待所有容器就绪 (健康检查通过)
5. 初始化数据库: `docker exec backend alembic upgrade head`
6. 安装 systemd 服务并启动命名 Agent
7. 预热 Ollama 模型
8. 验证所有组件健康状态
9. 配置 Prometheus 抓取目标和 Grafana 仪表盘
10. 配置 Alertmanager 告警通知渠道

---

## 9. 非功能性需求满足情况

### 9.1 性能指标

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| API 响应时间 (P95) | < 500ms | Prometheus 指标 http_request_duration_seconds |
| WebSocket 消息延迟 | < 100ms | WebSocket 消息时间戳差值 |
| Agent 任务执行超时 | 30 分钟 | Celery 任务超时配置 |
| Ollama 推理响应 (P95) | < 30s (72B Q4) | Ollama 内置指标 |
| 数据库查询 (P95) | < 100ms | PostgreSQL pg_stat_statements |
| 并发用户支持 | 50+ | 负载测试 (k6/Locust) |

**测试环境**:
- CPU: 32 核
- 内存: 128GB
- GPU: NVIDIA 48GB 显存
- 网络: 1Gbps 内网

### 9.2 可扩展性

**水平扩展点**:
- Celery Worker: 增加并发数或添加额外 Worker 容器
- 编程 Agent 容器: 提高全局并发上限 (需相应增加宿主资源)
- WebSocket Worker: 多个 WS Worker + Nginx 粘性会话

**垂直扩展点**:
- PostgreSQL: 增加 CPU/内存
- Ollama: 升级 GPU (更大显存支持更大模型)
- Redis: 增加 maxmemory 配置

**模块化扩展**:
- 新增命名 Agent: 复制 Profile 模板 + systemd 服务
- 新增编程 Agent 类型: 构建新 Docker 镜像 + Swarm Executor 注册
- 新增功能模块: FastAPI 路由模块 + 数据库迁移

### 9.3 可维护性

**代码结构**:
- 后端按模块划分: projects/、workflow/、agent/、qa/、chat/、docs/、security/
- 统一错误处理和日志格式
- API 文档自动生成 (Swagger/OpenAPI)

**部署维护**:
- Docker Compose 一键部署
- Alembic 数据库迁移管理
- systemd 进程自动重启
- 日志集中聚合 (Loki)

**监控告警**:
- Prometheus 指标采集 (API 延迟、错误率、队列长度、容器资源)
- Grafana 仪表盘可视化
- Alertmanager 告警 (邮件/Webhook)

### 9.4 安全性

**已实现安全措施**:
- JWT 认证 + Refresh Token + RBAC 权限控制
- SSL/TLS 传输加密 (TLS 1.2+)
- 容器非 root 运行
- 编程 Agent 容器网络/文件系统隔离
- 敏感信息 .env 文件保护 (权限 600)
- 内部 API Key 认证 (命名 Agent 与 Gateway 之间)
- 审计日志记录 (append-only)
- 速率限制 (Nginx + 应用层)

**安全测试计划**:
- 由后华(安全员)执行渗透测试
- 测试范围: API 端点、文件上传、SQL 注入、XSS、CSRF
- 测试标准: OWASP Top 10
- 漏洞修复时限: 高危 24 小时内，中危 72 小时内

### 9.5 可靠性

**可靠性保障**:
- Docker 自动重启策略 (unless-stopped)
- 健康检查与故障恢复
- 数据备份 (每日全量 + 实时 Git)
- Ollama 三级降级策略 (云端切换/排队限流/任务延迟)
- 任务重试机制 (3 次 + 指数退避)
- Celery 任务持久化 (Redis Broker + AOF)

**RTO/RPO**:
- RTO (恢复时间目标): 4 小时
- RPO (数据恢复点目标): 1 小时

### 9.6 可观测性

**三大支柱**:
1. **指标 (Metrics)**: Prometheus 采集 API 延迟、错误率、队列长度、容器资源使用率
2. **日志 (Logs)**: Loki 聚合所有容器和应用日志，支持结构化查询
3. **追踪 (Traces)**: OpenTelemetry 追踪请求全链路 (API -> Celery -> Agent -> Ollama)

**Grafana 仪表盘**:
- 系统资源仪表盘 (CPU/内存/GPU/磁盘)
- API 性能仪表盘 (延迟/错误率/吞吐量)
- Agent 执行仪表盘 (任务数/成功率/平均耗时)
- 项目进度仪表盘 (活跃项目/步骤完成/QA 通过率)

---

## 附录 A: 数据库 ER 图 (核心表)

```
users (1) ----< (N) project_members (N) >---- (1) projects
                                             |
                                             | (1)
                                             |
                                    (N) tasks (project_steps)
                                             |
                                             | (N)
                                             |
                                    (N) qa_records

projects (1) ----< (1) groups (1) >---- (N) group_members
                                      |
                                      | (1)
                                      |
                                (N) group_messages

projects (1) ----< (N) audit_logs
projects (1) ----< (1) repos ----< (N) repo_branches
                                                |
                                                v
                                         pull_requests ---- commits ---- task_commits
```

## 附录 B: 16 步流程与 Agent 映射

| 步骤 | 步骤名称 | 执行 Agent | QA 检验 | 代码提交 |
|------|----------|-----------|---------|----------|
| 1 | 项目创建 | 人类用户 | 无需 QA | 无需 |
| 2 | 需求分析 | 后兴 | 后荣 | 是 |
| 3 | 架构设计 | 后旺 | 后荣 | 是 |
| 4 | 后端设计 | 后旺 | 后荣 | 是 |
| 5 | 前端设计 | 后旺 | 后荣 | 是 |
| 6 | 数据库设计 | 后旺 | 后荣 | 是 |
| 7 | 开发环境搭建 | 后富 | 后荣 | 是 |
| 8 | TDD 测试编写 | 后发 (蜂群) | 后荣 | 是 |
| 9 | 代码编写 | 后发 (蜂群) | 后荣 | 是 |
| 10 | 单元测试 | 后达 (蜂群) | 后荣 | 是 |
| 11 | 集成测试 | 后达 (蜂群) | 后荣 | 是 |
| 12 | 安全审计 | 后华 | 后荣 | 是 |
| 13 | 部署交付 | 后富 | 后荣 | 是 |
| 14 | 文档整理 | 后贵 | 后荣 | 是 |
| 15 | 前端实操验证 | 后达 | 后荣 | 是 |
| 16 | 项目验收 | 海梅 + 人类 | 后荣 | 是 |

## 附录 C: V14 修正内容对照表

| 后荣检验项 | V13 状态 | V14 修正内容 |
|------------|----------|-------------|
| 【严重问题1】文档完整性 | 声称完整但实际截断 | 采用文件写入确保完整输出，本文件包含全部 9 个核心章节 + 附录 |
| 【中等问题2】资源容量规划 | 缺少 PostgreSQL/Redis/Nginx/总量规划 | 新增 4.5 节：PostgreSQL 连接数/存储/IOPS 规划、Redis 内存规划、Nginx 并发连接数、宿主机总资源汇总表 |
| 【中等问题3】故障转移与降级 | 描述不足 | 完善 5.5 节：补充自动降级流程(触发条件/步骤)、云端模型切换条件、降级期间功能限制、故障恢复后回切策略(灰度回切) |
| 【建议改进4】安全设计 | 缺少认证授权/API鉴权/内部认证 | 完善第 6 节：新增 JWT+Refresh Token 认证方案、API 接口鉴权设计、命名 Agent 与 Gateway API 内部认证机制(API Key)、敏感配置管理(.env/密钥轮换)、容器间通信安全 |
| 【建议改进5】监控与可观测性 | 缺少具体指标/阈值/追踪方案 | 新增第 7 节：监控工具选型表、关键监控指标定义(15+指标)、告警阈值设定(15条规则)、Grafana 仪表盘设计、OpenTelemetry 链路追踪方案、Loki 日志收集方案 |

## 附录 D: 文档分文件存储建议

为避免单文件过大导致传输截断，建议后续版本将架构文档拆分为:

| 文件名 | 内容 |
|--------|------|
| architecture_overview.md | 第 1 节: 系统架构概述 |
| tech_stack.md | 第 2 节: 技术栈选型 |
| module_design.md | 第 3 节: 模块详细设计 |
| agent_scheduling.md | 第 4 节: Agent 调度与资源管理 |
| ha_disaster_recovery.md | 第 5 节: 高可用与容灾方案 |
| security.md | 第 6 节: 安全设计 |
| monitoring.md | 第 7 节: 监控与可观测性 |
| deployment.md | 第 8 节: 部署方案 |
| non_functional.md | 第 9 节: 非功能性需求满足情况 |
