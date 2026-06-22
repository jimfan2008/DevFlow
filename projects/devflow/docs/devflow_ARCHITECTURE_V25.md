# DevFlow 架构设计文档 V25.0

**项目**: DevFlow 项目管理平台
**版本**: 25.0
**日期**: 2026-06-16
**作者**: HouWang (后旺) — 架构设计师
**状态**: V24.0 修订 (根据跨文档一致性检验报告修订)

**变更日志**:
- V25.0 (2026-06-16): 根据跨文档一致性检验报告修订
  - 【一致性问题 - WebSocket 端点不一致】修复: §3.5 WebSocket 端点从 `/ws/v1/groups/{id}` 修正为三个独立端点 `/ws/group-chat`、`/ws/notifications`、`/ws/workflow/:project_id`，与后端文档 V37 §2.16 保持完全一致
  - 【一致性问题 - 代码仓库接口 REST 风格不一致】修复: §3.6 代码仓库接口从嵌套路径 `/api/v1/projects/{id}/repo/init` 和 `/repo/commit` 修正为独立资源路径 `/api/v1/repos` 系列，与后端文档 V37 §2.11 保持完全一致
  - 【一致性问题 - 群聊消息表 sender_type 枚举值不一致】修复: §3.5 group_messages 表 sender_type 从 (human/agent) 修正为 (user/agent/system)，与后端文档 V37 §5.2.10 保持完全一致
  - 【一致性问题 - 群聊成员表结构不一致】修复: §3.5 group_members 表从 `user_id(NULL=Agent)` + `agent_name(NULL=人类)` 双字段方案修正为 `member_type` + `member_id` 三选一方案，与后端文档 V37 §5.2.9 保持完全一致
  - 【一致性问题 - step_events 表后端未定义】修复: 后端文档 V37 补充 step_events 表定义，架构 §3.9 与后端数据库设计保持一致
  - 延续 V24.0 已修复项: Access Token 有效期、角色模型、WebSocket 认证响应类型、UI 组件库一致
- V22.0 (2026-06-15): 根据跨文档一致性检验报告修订
  - 【一致性问题 - UI组件库不一致】修复: 1.3 节"架构层次说明"客户端层技术选型从"Vue 3 + Vite"更新为"Vue 3 + Vite + Element Plus"，与 2.2 节"前端技术栈"和前端设计文档保持完全一致
  - 延续 V21.0 已修复项: 推理层并发瓶颈、文档完整性、降级策略、命名 Agent 部署模型、Patroni 单机部署、云端 API 成本控制、Ollama 显存计算、文档截断、单机可用性、SPOF 分析、资源分解、资源配置、单机与多节点区分、Docker Socket 权限、后端通信路径、网络安全域、Patroni 统一、16步流程映射、Gitea DB 隔离、Celery 并发映射、Redis 数据隔离、核心数据流、PostgreSQL HA、Redis Sentinel、Ollama 多实例、分布式数据一致性、推理层扩展、容器池预热、结果回传、安全设计、监控可观测性、Swarm Executor 主备
- V21.0 (2026-06-15): 根据后荣 QA 检验报告修订
  - 【严重缺陷 - 推理层并发瓶颈未解决】修复: 新增 4.12 节"推理层并发排队 SLA 分析"，包含: (1) 13+ Agent 共享 2 并发 Ollama 的排队延迟分析 (2) 请求优先级机制 (3 级: 紧急/正常/低优先级) (3) 超时策略 (排队超时 3 分钟, 推理超时 60 秒) (4) 排队等待期间 Agent 侧的并行工作优化 (5) 前端 UI 排队状态可见性 (6) 并发升级路径 (80GB GPU 支持 4 并发, 多 GPU 支持 8+ 并发)
  - 【严重缺陷 - 文档仍然截断】修复: 确认 V21 源文件完整, 更新完整性自检命令引用 V21 文件名, 新增分文件存储建议 (D.2 节) 以防传输截断
  - 【中缺陷 - 降级策略 5 分钟切换延迟过长】修复: 5.5 节 L3 级别降级策略重构: (1) 排队超时从 5 分钟降至 60 秒 (2) 新增前端 UI 缓解方案: 排队期间显示"推理服务繁忙, 预计等待 X 秒"状态条 (3) 超过 60 秒未响应时自动切换至云端 API (L2) 或返回 503 建议稍后重试 (4) 前端显示预估恢复时间 (基于当前队列长度 × 平均推理时间)
  - 【中缺陷 - 命名 Agent 宿主进程与容器化不一致】修复: 新增 4.9.1 节"命名 Agent 部署模型合理性说明", 解释为何采用 systemd 宿主进程而非容器化: (1) 命名 Agent 需要访问宿主机文件系统 (项目目录) (2) 需要调用本地工具链 (git/pytest 等) (3) systemd 提供更可靠的崩溃恢复 (4) 给出统一监控方案: node-exporter + Prometheus 采集宿主机进程指标, Loki 收集 systemd 日志 (5) 崩溃恢复策略与容器 restart policy 对齐 (Restart=always, RestartSec=10s) (6) 提供容器化升级路径 (Docker 绑定挂载项目目录 + 工具链镜像)
  - 【中缺陷 - PostgreSQL Patroni 单机部署合理性存疑】修复: 5.6 节新增"单机 Patroni 局限性说明"块: (1) 明确单机 Patroni 只能应对容器/进程级别故障, 无法应对宿主机级别故障 (2) 给出同主机流复制从库的实际价值: 读取负载均衡、数据冗余备份、故障快速恢复 (3) 说明 etcd 3 节点同机部署的 quorum 局限性 (4) 给出多节点升级路径 (跨主机 etcd + 跨主机 PostgreSQL)
  - 【轻微缺陷 - 云端 API 成本控制机制未与预算关联】修复: 5.5 节补充具体参数: (1) 每日预算上限: $50/天 (可通过 FALLBACK_DAILY_BUDGET 环境变量调整) (2) 单次请求最大花费: $0.50 (超过则自动截断) (3) 成本监控频率: Prometheus 每 5 分钟采集一次 (4) 告警级别: 达到 80% 预算时 P2 警告 (邮件), 达到 100% 时 P1 紧急 (邮件 + Webhook, 自动熔断) (5) 熔断恢复: 次日零点自动重置预算计数器
  - 延续 V20.0 已修复项: Ollama 显存计算修正、文档完整性、单机可用性约束、SPOF 分析、资源分解细化、命名 Agent 资源明细、降级策略细节、资源配置一致、单机与多节点区分、Docker Socket 权限、后端通信路径、网络安全域、Patroni 统一
  - 延续 V19.0 已修复项: 资源配置自相矛盾、单机与多节点冲突、Ollama 显存计算不一致、Docker Socket 挂载权限、后端与 Swarm 通信路径、Docker 网络安全域、pg_auto_failover 统一
  - 延续 V18.0 已修复项: 文档完整性、推理层单点故障、16步流程映射、Gitea DB 隔离、Celery 并发映射、Redis 数据隔离、核心数据流、PostgreSQL HA、Redis Sentinel、Ollama 多实例、分布式数据一致性、推理层扩展、容器池预热、结果回传、安全设计、监控可观测性、Swarm Executor 主备

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
- Swarm Executor: 编程 Agent 容器生命周期管理 (主备双实例部署)

**外部服务隔离**:
- 数据库、缓存、代码托管、监控、推理引擎等均为独立的依赖组件，通过容器化部署与后端解耦

**推理层共享**:
- 9 个命名 Agent 共享单一 Ollama 容器实例和模型，通过 Ollama 内置请求队列实现并发调度
- 并发限制: 最大 2 个并行推理请求 (48GB GPU 显存约束, V20 修正)
- 请求优先级: 3 级 (紧急/正常/低), 确保关键任务优先获得推理资源 (V21 新增)
- 排队 SLA: 平均排队等待时间 < 60 秒 (P95), 超时自动降级 (V21 新增)

**宿主进程协作**:
- 9 个命名 Agent 以独立 Hermes Profile 进程运行在宿主机上，通过 systemd 管理，通过 Gateway API 被 Celery Worker 调度调用
- **9 个命名 Agent 角色列表**:
  1. 海梅 (HaiMei) — 项目经理: 任务分派、协调所有 Agent 工作、对项目交付成果负责
  2. 后兴 (HouXing) — 需求分析师: 需求分析、与用户沟通、产出 SRS
  3. 后旺 (HouWang) — 架构设计师: 架构/前后端/数据库设计
  4. 后发 (HouFa) — 程序员: 建立编程 Agent 蜂群、监督 TDD 和代码编写
  5. 后达 (HouDa) — 测试员: 建立测试 Agent 蜂群、执行各类测试
  6. 后富 (HouFu) — CI/CD 工程师: 开发环境搭建、代码部署
  7. 后贵 (HouGui) — 文档管理员: 项目文档一致性管理
  8. 后荣 (HouRong) — QA: 检验每个 Agent 产出物、门控放行
  9. 后华 (HouHua) — 安全员: 代码审计、合规审查、渗透测试、漏洞修复

**动态容器编排**:
- Swarm Executor 通过 Docker API 动态创建/销毁编程 Agent 容器，实现按需资源分配

- **高可用 (V20 修正)**: 当前架构为单机部署模式，软件层面通过 Docker 自动重启策略、健康检查故障恢复、数据备份三重保障实现 99% 可用性 (约每月 < 7.3 小时停机)。但单机存在硬件级单点故障 (主机宕机/磁盘故障/网络中断)，无法通过软件方案解决。真正 99.9%+ 可用性需要多节点部署 (见 5.10 节升级路径)。
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
+v----------+---------+ +------+---------+ +-----+--------+
|  FastAPI 后端       | | WS   | Worker   | | Gitea        |
|  (backend, w=2)     | | (ws-  |, w=1)   | | (代码托管)    |
|  处理 HTTP API       | | worker|         | |              |
|                      | | 处理  |WebSocket| |              |
|  +----------------+ | | 长连接 |         | |              |
|  | 16步流程调度   | | +--------+---------+ +--------------+
|  | Agent蜂群调度  | |                    | Gitea DB:    |
|  | QA门控检验     | |                    | 独立PostgreSQL|
|  | 群聊协作       | |                    | 实例(不共享)  |
|  | Profile扫描    | |                    +--------------+
|  | Gateway通信    | |
|  | Gitea代码库    | |
|  | 通知推送       | |
|  +----------------+ |
|                      |
+----------+-----------+
         |
+--------v----------+  +-------------v----------+   +----------+
|| PostgreSQL (主库) |  | Redis (缓存/队列/Broker)|   | Celery   |
|| 主从流复制(Patroni)|  | Sentinel哨兵模式       |   | Beat     |
|| 与Gitea DB完全独立|  | 数据隔离: 分DB编号     |   | (定时   |
+-------------------+  | DB0=缓存 DB1=Broker    |   | 任务)   |
         |              | DB2=Session           |   | 独立    |
+--------v----------+  +------------------------+   | 容器    |
|| PostgreSQL (gitea)|                                   +----+-----+
|| 完全独立实例,      |                                                    |
|| 不共享主库集群     |                                            +-------+-------+
+-------------------+                                            | Celery Worker  |
         |                                                       | (8 并发)       |
+--------v--------------------------------------------------+   +-------+-------+
|| 9个命名Agent角色 (宿主机进程, 独立Hermes Profile实例)       |           |
|| 进程管理: systemd 服务单元, 崩溃自动重启 (restart=always)   |    +------v------+
|| 海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华 (Gateway API)  |    | Swarm Exec   |
|| 调度: Celery Worker -> Gateway API HTTP -> 命名Agent执行   |    | (主:8090)    |
|| 推理: 9个Agent共享Ollama实例 + 内置请求队列并发调度        |    | Swarm Exec   |
|| 默认模型: 本地 Ollama + qwen2.5:72b-instruct-q4_K_M       |    | (备:8091)    |
|| 降级策略: Ollama故障 -> 多实例切换 -> 云端模型API           |    |              |
|| 产出持久化: 写入 /DevFlow/projects/{project_id}/            |    +------+---+   |
+------------------------------------------------------------+           |       |
         |                                                        +------+---+  |
+--------v--------------------------------------------------+           |       |
|| Ollama 容器 (ollama:11434, 主)                            |    +------+---+  |
|| Ollama 容器 (ollama-backup:11435, 备, 可选)               |    | Docker API | |
|| 模型: qwen2.5:72b-instruct-q4_K_M (72B Q4量化)             |    | 创建/销毁  | |
|| GPU: NVIDIA GPU (显存 >= 48GB)                            |    +------+---+  |
|| 内置请求队列: 并发调度9个命名Agent推理请求                 |           |       |
|| 并发限制: 最大2个并行推理请求 (KV cache + 显存安全余量)     |    +------+---+  |
|| 优先级队列: 3级 (紧急/正常/低) + 超时自动降级 (V21 新增)   |    | 编程Agent  | |
|| 健康检查: HTTP GET /api/tags, 间隔30秒                     |    | 容器池     | |
|| 故障转移: 主实例故障 -> 自动切换至备实例 -> 云端API        |    | (上限4个)  | |
+-----------------------------------------------------------+    +-------------+
         |                                                     
+--------v--------------------------------------------------+
|| 监控与可观测性 (Prometheus + Grafana + Loki + Alertmanager) |
|| 指标采集: API延迟/错误率/队列长度/容器资源/Agent执行状态     |
|| 日志聚合: Loki 收集所有容器和应用日志                      |
|| 链路追踪: OpenTelemetry 追踪 API->Celery->Agent->Ollama     |
|| 告警: Alertmanager 邮件/Webhook 通知                      |
+-----------------------------------------------------------+
```

### 1.3 架构层次说明

| 层次 | 组件 | 技术选型 | 职责 |
|------|------|----------|------|
| 客户端层 | Web 前端 | Vue 3 + Vite + Element Plus | 用户界面、实时通信 |
| 客户端层 | 移动端 | Flutter / H5 | 移动访问、通知推送 |
| 接入层 | Nginx | Nginx 1.24 | 反向代理、SSL 终止、WebSocket 代理 |
| 应用层 | DevFlow 后端 | FastAPI + Uvicorn | HTTP API、业务逻辑、流程调度 |
| 应用层 | WebSocket Worker | FastAPI + WebSockets | 长连接管理、实时消息推送 |
| 调度层 | Celery Worker | Celery 5.3 + Redis Broker | 异步任务队列、Agent 执行编排 (8 并发) |
| 调度层 | Celery Beat | Celery Beat (独立容器) | 定时任务调度（项目状态检查、超时清理等） |
| 调度层 | Swarm Executor | Python + Docker SDK | 编程 Agent 容器生命周期管理; Celery Worker 调度的独立服务容器 (非 Celery 组成部分)，通过 HTTP 接收 Celery 任务指令，再通过 Docker API 创建/销毁编程 Agent 容器; 采用主备双实例部署 (主:8090, 备:8091) |
| Agent 层 | 命名 Agent | Hermes (9 个独立 Profile) | 9 个命名 Agent 角色宿主进程，systemd 管理 |
| Agent 层 | 编程 Agent | Docker 容器 (动态编排) | CodeArts 等编程 Agent 容器，按需创建/销毁 |
| 推理层 | Ollama | Ollama 容器 + qwen2.5:72b | 本地 LLM 推理引擎，9 个命名 Agent 共享 |
| 推理层 | 云端模型 (可选) | OpenAI / Anthropic API | 降级或增强推理能力 |
| 数据层 | PostgreSQL (主库) | PostgreSQL 14+ | DevFlow 主数据库（项目、用户、流程状态等），主从流复制(Patroni+etcd) |
| 数据层 | PostgreSQL (Gitea) | PostgreSQL 14+ | Gitea 代码托管数据库，完全独立的 PostgreSQL 实例，不共享主库集群和数据目录 |
| 数据层 | Redis | Redis 7 | 缓存、Celery Broker、Session 存储，Sentinel哨兵模式；数据隔离方案：分 DB 编号 (DB0=缓存层, DB1=Celery Broker 任务队列, DB2=Session 存储) |
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

**群聊消息流 (V25 修正)**:
1. Agent/用户发送消息 -> WS /ws/group-chat -> WS Worker 处理
2. WS Worker -> 写入 group_messages 表 (PostgreSQL, sender_type=user/agent/system)
3. WS Worker -> 通过 /ws/group-chat 广播给群内所有在线成员
4. 系统通知 -> 通过 /ws/notifications 推送给相关用户
5. 流程状态变更 -> 通过 /ws/workflow/{project_id} 推送给项目相关人员
6. 离线消息 -> 用户下次连接时通过 WebSocket 拉取

> **V25 修正说明**: 群聊消息流中的 WebSocket 端点从 V24 的单一 `/ws/v1/groups/{id}` 修正为三个独立端点 (`/ws/group-chat`、`/ws/notifications`、`/ws/workflow/{project_id}`)，与 §3.5 和后端文档 V37 §2.16 保持一致。

**16步流程状态变更机制 (V15 完善)**:

每步状态流转遵循严格的状态机规则:

```
状态: pending -> in_progress -> completed -> (qa_passed | qa_failed)
                                                   |              |
                                                   v              v
                                              (触发下一步)    (退回in_progress, 标记qa_failed)

异常路径:
pending -> in_progress -> failed (执行异常)
                                 |
                                 v
                           (自动重试, max=3次)
                                 |
                            重试仍失败 -> blocked (阻塞, 需人工介入)
```

状态变更详细流程:

1. **每步开始**: Celery Worker 写入 project_steps 表 (status=pending -> in_progress), 记录 started_at
2. **每步执行中**: 命名 Agent 定期(每5分钟)通过 Gateway 回调更新进度到 project_steps 表 (progress 字段, 0-100)
3. **每步完成**: Celery Worker 更新 project_steps (status=completed, output_path, completed_at), 触发 QA 检验任务
4. **QA 检验通过**: 后荣 写入 qa_records 表 (score, dimensions, feedback), project_steps 更新 (qa_status=passed), 自动触发下一步
5. **QA 检验不通过**: project_steps 回退 (status=in_progress, qa_status=failed, qa_feedback), 通知原执行 Agent 重做
6. **执行失败**: Celery Worker 捕获异常, project_steps 更新 (status=failed, error_message), 触发自动重试
7. **重试耗尽**: 重试3次后仍失败, status 置为 blocked, 触发告警通知管理员介入
8. **人工介入恢复**: 管理员手动重置 status 为 pending 或 in_progress, 继续执行

**故障处理流程 (V15 新增)**:

1. **命名 Agent 进程崩溃**:
   - systemd 自动重启 (Restart=always)
   - Celery Worker 检测到 Gateway 调用超时 (5秒健康检查)
   - 连续3次健康检查失败, 标记 Agent 为不可用
   - 任务进入等待队列, Celery Beat 每1分钟重新尝试
   - 重启后自动恢复, 任务继续执行

2. **Ollama 推理引擎故障**:
   - 见 5.5 节三级降级策略
   - 第一级: 自动切换至 Ollama 备实例
   - 第二级: 自动切换至云端模型 API
   - 第三级: 任务排队等待, 定期重试

3. **数据库故障**:
   - PostgreSQL 主从切换 (Patroni + etcd, 见 5.6 节)
   - 故障期间读写切换至从库提升为主库
   - 原主库恢复后重新加入集群作为从库

4. **Redis 故障**:
   - Redis Sentinel 自动故障转移 (见 5.7 节)
   - 未完成的任务由 Celery 从 AOF 日志恢复
   - 缓存数据丢失不影响核心业务 (缓存可重建)

5. **Swarm Executor 故障**:
   - Swarm Executor 主实例故障 -> Nginx 自动切换至备实例 (见 5.9 节)
   - 备实例不可用 -> Docker 自动重启容器
   - 运行中的编程 Agent 容器不受影响 (独立运行)
   - 重启后 Swarm Executor 扫描现有容器重新建立管理
   - 降级策略: 管理员可通过 `docker exec` 和 `docker run` 手动操作容器

**异常回滚策略 (V15 新增)**:

1. **产出物回滚**:
   - 每个步骤的产出物在 QA 检验通过后提交到 Gitea
   - Gitea Git 版本控制天然支持回滚
   - 若后续步骤发现前序步骤产出物有问题, 可通过 Git 回滚到之前版本
   - project_steps 表保留每个步骤的所有历史执行记录

2. **状态回滚**:
   - QA 不通过时, 当前步骤状态回退为 in_progress
   - 后续未执行步骤保持 pending 状态不变
   - 不支持跨步骤回滚 (即第 N 步问题不会回退第 N-1 步)

3. **数据一致性回滚**:
   - 采用本地消息表模式 (见 3.9 节)
   - 步骤执行相关的事件记录在 step_events 表中
   - 若最终状态不一致, 通过事件回放修复

**命名 Agent 产出物写入确认机制 (V15 新增)**:

1. **写入确认**:
   - 命名 Agent 将产出物写入文件后, 返回文件路径和文件大小
   - Celery Worker 收到返回后执行验证:
     a. 检查文件是否存在 (os.path.exists)
     b. 检查文件大小是否大于 0
     c. 计算文件 MD5 校验和, 与 Agent 返回的校验和比对
   - 验证通过 -> 标记产出物写入成功
   - 验证失败 -> 触发重试 (最多3次)

2. **写入失败处理**:
   - 重试3次后仍失败 -> 标记步骤为 failed
   - 记录 error_message = "Output write verification failed after 3 retries"
   - 触发告警通知管理员
   - 可能的原因: 磁盘空间不足、权限问题、文件系统损坏
   - 管理员介入修复后手动重试该步骤

### 1.5 16步标准流程与架构组件映射 (V18 新增)

**映射总览**:

| 步骤 | 步骤名称 | 执行 Agent | 执行组件 | 推理组件 | 产出物 | 产出物路径 | QA 门控 | 代码提交 |
|------|----------|-----------|---------|---------|--------|-----------|---------|---------|
| 1 | 项目创建 | 人类用户 | FastAPI + PostgreSQL | 无 | 项目元数据 | projects 表 | 无需 QA | 自动创建 Gitea 仓库 |
| 2 | 需求分析 | 后兴 | Celery->Gateway->后兴进程 | Ollama | SRS 文档 | /docs/requirements.md | 后荣检验 | 是 |
| 3 | 架构设计 | 后旺 | Celery->Gateway->后旺进程 | Ollama | 架构设计文档 | /docs/architecture.md | 后荣检验 | 是 |
| 4 | 后端设计 | 后旺 | Celery->Gateway->后旺进程 | Ollama | 后端设计文档 | /docs/backend_design.md | 后荣检验 | 是 |
| 5 | 前端设计 | 后旺 | Celery->Gateway->后旺进程 | Ollama | 前端设计文档 | /docs/frontend_design.md | 后荣检验 | 是 |
| 6 | 数据库设计 | 后旺 | Celery->Gateway->后旺进程 | Ollama | 数据库设计文档 | /docs/database_design.md | 后荣检验 | 是 |
| 7 | 开发环境搭建 | 后富 | Celery->Gateway->后富进程 | Ollama | 环境配置 | /config/docker-compose.yml | 后荣检验 | 是 |
| 8 | TDD 测试编写 | 后发(蜂群) | Celery->Swarm Exec->编程Agent容器 | Ollama | 测试用例 | /tests/test_*.py | 后荣检验 | 是 |
| 9 | 代码编写 | 后发(蜂群) | Celery->Swarm Exec->编程Agent容器 | Ollama | 源代码 | /src/*.py | 后荣检验 | 是 |
| 10 | 单元测试 | 后达(蜂群) | Celery->Swarm Exec->编程Agent容器 | Ollama | 测试报告 | /reports/unit_test.md | 后荣检验 | 是 |
| 11 | 集成测试 | 后达(蜂群) | Celery->Swarm Exec->编程Agent容器 | Ollama | 测试报告 | /reports/integration_test.md | 后荣检验 | 是 |
| 12 | 安全审计 | 后华 | Celery->Gateway->后华进程 | Ollama | 安全审计报告 | /docs/security_audit.md | 后荣检验 | 是 |
| 13 | 部署交付 | 后富 | Celery->Gateway->后富进程 | Ollama | 部署配置 | /config/deploy_config.md | 后荣检验 | 是 |
| 14 | 文档整理 | 后贵 | Celery->Gateway->后贵进程 | Ollama | 完整项目文档 | /docs/ (全量) | 后荣检验 | 是 |
| 15 | 前端实操验证 | 后达 | Celery->Gateway->后达进程 | Ollama | 实操验证报告 | /reports/e2e_test.md | 后荣检验 | 是 |
| 16 | 项目验收 | 海梅+人类 | FastAPI + 前端 | 无 | 验收报告 | /docs/acceptance.md | 后荣检验 | 是 |

**流程执行路径分类**:

1. **命名 Agent 路径** (步骤 1-7, 12-16):
   - Celery Worker 调度 -> Gateway API HTTP 调用 -> 命名 Agent 宿主进程 -> Ollama 推理 -> 产出物写入项目目录 -> 返回结果

2. **编程 Agent 蜂群路径** (步骤 8-11):
   - Celery Worker 调度 -> Swarm Executor HTTP 调用 -> Docker API 创建编程 Agent 容器 -> 容器内执行编码/测试任务 (调用 Ollama) -> 结果通过 HTTP 回调回传 -> 容器销毁

3. **人类执行路径** (步骤 1):
   - 用户通过前端操作 -> FastAPI 处理 -> PostgreSQL 写入 -> Gitea 仓库创建

**门控点说明**:
- 每步完成 (步骤 2-16) 均需经过后荣 QA 检验
- QA 检验维度: 完整性(25%) + 一致性(25%) + 可验证性(20%) + 无歧义性(20%) + 格式规范(10%)
- 合格阈值: 总分 >= 70 分且无单项低于 50 分
- QA 不通过时, 当前步骤退回 in_progress 状态, 通知原执行 Agent 重做
- QA 通过后, 产出物自动提交至 Gitea 代码库, 触发下一步执行

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
| 数据库 | PostgreSQL | 14+ | 关系型数据库，JSON 支持，ACID |
| 数据库 HA | Patroni + etcd | latest | PostgreSQL 高可用自动故障转移 |
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
  - status (pending/in_progress/completed/failed/skipped/blocked)
  - assigned_agent (执行 Agent 名称)
  - progress (0-100), output_path, output_md5, qa_status
  - started_at, completed_at, error_message, retry_count

**流程状态机**:
```
pending -> in_progress -> completed -> (qa_passed) -> next_step
                             -> completed -> (qa_failed) -> in_progress (retry)
                             -> failed -> (retry, max=3) -> in_progress
                                                         -> blocked (exhausted)
```

**调度逻辑**:
1. 海梅(项目经理)确认步骤条件满足
2. FastAPI 触发 Celery 任务 `execute_step(project_id, step_number)`
3. Celery Worker 根据步骤分配对应的命名 Agent
4. 调用 Hermes Gateway 执行 Agent 任务
5. Agent 完成后，结果写入项目目录
6. Celery Worker 验证产出物写入 (文件存在、大小>0、MD5校验)
7. 后荣(QA)自动对产出物进行检验
8. QA 通过后更新状态并触发下一步，QA 不通过则回退并通知重做
9. 执行失败时触发重试 (最多3次, 指数退避: 1min/5min/15min)
10. 重试耗尽后状态置为 blocked, 触发告警

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
4. 任务完成后，结果通过 HTTP 回调(主)回传 (见 4.7 节)
5. 所有容器任务完成，蜂群解散，容器自动销毁

**并发控制**:
- 全局上限: 4 个编程 Agent 容器 (V19: 原 16 个下调)
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
- WS /ws/group-chat — 群聊消息 WebSocket 连接
- WS /ws/notifications — 通知推送 WebSocket 连接
- WS /ws/workflow/{project_id} — 流程状态变更 WebSocket 连接
- GET /api/v1/groups/{id}/messages — 消息历史
- POST /api/v1/groups/{id}/messages — 发送消息

> **V25 修正说明**: WebSocket 端点从 V24 的 `/ws/v1/groups/{id}` 单一端点调整为三个独立端点 `/ws/group-chat`、`/ws/notifications`、`/ws/workflow/{project_id}`，与后端文档 V37 §2.16 保持一致。三个端点职责分离：群聊消息、通知推送、流程状态变更各自独立连接，避免消息混淆和连接管理复杂度。

**数据库表**:
- groups (群聊表):
  - id, project_id, name, created_at
- group_members (群成员表):
  - id, group_id
  - member_type (user/agent/system) — 成员类型
  - member_id — 成员 ID (用户 ID / Agent ID / 系统标识)
  - joined_at

> **V25 修正说明**: group_members 表从 V24 的 `user_id(NULL=Agent)` + `agent_name(NULL=人类)` 双字段方案，修正为 `member_type + member_id` 统一方案，与后端文档 V37 §5.2.9 保持一致。`member_type` 枚举值为 `user`(人类用户) / `agent`(Agent 成员) / `system`(系统通知)，`member_id` 存储对应类型的唯一标识符。

- group_messages (消息表):
  - id, group_id
  - sender_id — 发送者 ID (用户 ID / Agent ID / 系统标识)
  - sender_type (user/agent/system) — 发送者类型
  - content, message_type (text/file/image)
  - attachments (JSON), created_at

> **V25 修正说明**: group_messages 表 `sender_type` 枚举值从 V24 的 `(human/agent)` 修正为 `(user/agent/system)`，与后端文档 V37 §5.2.10 保持一致。新增 `system` 类型用于系统自动发送的通知消息（如步骤完成通知、QA 结果通知等）。同时移除了 V24 的 `sender_agent_name` 冗余字段，Agent 名称通过 `sender_id` 关联 Agent 配置表获取。

**消息推送**:
- 在线用户: WebSocket 实时推送 (通过 /ws/group-chat 连接)
- 离线用户: 下次连接时拉取未读消息
- Agent 消息: 由 WS Worker 写入数据库并通过 WebSocket 广播
- 系统通知: 通过 /ws/notifications 连接推送
- 流程状态变更: 通过 /ws/workflow/{project_id} 连接推送

### 3.6 代码库管理模块

**职责**: 与 Gitea 集成，管理代码仓库

**核心接口 (V25 修正)**:
- POST /api/v1/repos — 创建代码仓库 (关联 project_id)
- GET /api/v1/repos/{id} — 获取仓库信息
- GET /api/v1/repos/{id}/commits — 提交历史
- POST /api/v1/repos/{id}/commits — 提交代码
- GET /api/v1/repos/{id}/branches — 分支列表
- POST /api/v1/repos/{id}/reviews — 创建代码审查

> **V25 修正说明**: 代码仓库接口从 V24 的嵌套路径 `/api/v1/projects/{id}/repo/init` 和 `/api/v1/projects/{id}/repo/commit` 修正为独立资源路径 `/api/v1/repos` 系列，与后端文档 V37 §2.11 保持一致。仓库作为独立资源管理，通过 project_id 字段与项目关联，符合 RESTful 独立资源风格。

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

### 3.9 分布式数据一致性方案 (V15 新增, V25 修正)

**问题场景**: DevFlow 架构涉及 FastAPI、Celery Worker、命名 Agent、编程 Agent 等多个独立进程/容器，需要保证分布式操作的数据一致性。

**采用方案**: 本地消息表 (Local Message Table) + Saga 补偿模式

**本地消息表设计**:

在 PostgreSQL 中新增 `step_events` 表 (V25 修正: 补充后端 V37 缺失的表定义):

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 事件 ID |
| project_id | UUID | 项目 ID |
| step_number | INT | 步骤号 (1-16) |
| event_type | VARCHAR | 事件类型 (step_started/step_completed/qa_passed/qa_failed/output_written/retry_triggered) |
| event_data | JSONB | 事件数据 (产出物路径、分数、错误信息等) |
| status | VARCHAR | pending/processed/failed |
| created_at | TIMESTAMP | 事件创建时间 |
| processed_at | TIMESTAMP | 事件处理时间 |

> **V25 修正说明**: step_events 表是架构 §3.9 定义的本地消息表，用于分布式一致性事件记录。后端 V37 目前无对应表定义（仅有 audit_logs 表，但结构与用途不同）。step_events 与 audit_logs 的区别:
> - `step_events`: 业务事件驱动表，用于触发下游操作 (如 step_completed 触发 QA 检验)，status 字段用于事件消费状态追踪
> - `audit_logs`: 安全审计日志表，用于记录用户操作历史，不可篡改
> - 两者互补，不应互相替代

**工作流程**:

1. **事件记录**: 每步执行的关键状态变更，Celery Worker 在同一数据库事务中同时更新 project_steps 表和写入 step_events 表 (保证原子性)

2. **事件消费**: Celery Beat 定时任务 (每 30 秒) 扫描 step_events 表中 status=pending 的事件, 触发下游操作:
   - step_completed 事件 -> 触发 QA 检验
   - qa_passed 事件 -> 触发下一步执行
   - qa_failed 事件 -> 触发重试
   - output_written 事件 -> 触发代码库提交

3. **幂等性保证**: 事件消费者处理事件前检查是否已处理 (通过 event_id 去重), 避免重复执行

**Saga 补偿模式**:

用于处理跨步骤的长事务场景:

1. **正向操作**: 每步执行是一个 Saga 步骤
2. **补偿操作**: 若后续步骤发现前序步骤存在问题, 执行补偿:
   - 撤销代码库提交 (Git revert)
   - 重置 project_steps 状态
   - 通知相关 Agent 重新执行
3. **补偿触发**: 由后贵(文档管理员)或后华(安全员)在发现问题时触发
4. **补偿日志**: 所有补偿操作记录在 step_events 表中 (event_type=compensation_executed)

**最终一致性保证**:

- 强一致性: 同一事务内的 project_steps 更新和 step_events 写入
- 最终一致性: step_events 事件消费 (异步, 但有重试机制)
- 数据核对: Celery Beat 每日执行一次数据一致性核对任务, 比对 project_steps 状态与 step_events 事件链是否一致, 不一致时触发修复

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
- 9 个 Agent 共享 Ollama 容器实例进行推理

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
- 9 个命名 Agent 共享 Ollama 实例
- Ollama 内置请求队列处理并发请求
- 当多个 Agent 同时请求推理时，Ollama 按优先级队列调度 (V21 修正: FIFO -> 优先级队列)
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
| CPU 核心 | 64+ 核 | 基础设施(11.5核) + Ollama(8核) + 命名Agent(9核) + 编程Agent容器峰值(16核, 4个并发) + 监控(1核) + 安全余量(~30%) |
| 内存 | 192GB+ | 基础设施(19GB) + Ollama 模型(48GB) + 命名Agent(18GB) + 编程Agent容器峰值(32GB, 4个并发) + 监控(4GB) + 安全余量(~30%) |
| GPU 显存 | 48GB+ | Ollama 72B Q4 模型加载 (推荐 NVIDIA A100/RTX 4090) |
| 存储空间 | 1TB+ SSD | 项目文件、代码仓库、模型文件、日志 |

**GPU 显存容量详细规划 (V18 新增, V20 修正)**:

72B Q4 量化模型显存需求分析:

| 显存占用项 | 占用量 | 说明 |
|-----------|--------|------|
| 模型权重 (Q4_K_M) | ~38GB | 72B 参数 x 4-bit 量化，**所有并发请求共享加载** |
| 单次推理 KV Cache | ~2GB/请求 | 取决于上下文长度 (4K tokens) |
| 系统开销 | ~2GB | Ollama 运行时、Docker 开销 |
| **总计 (单请求)** | **~42GB** | 需 >= 48GB GPU |
| **总计 (2并发请求, V20)** | **~44GB 峰值** | 38GB + 2x2GB KV Cache + 2GB 系统开销 |
| **总计 (4并发请求)** | **~48GB 峰值** | 38GB + 4x2GB KV Cache + 2GB 系统开销 (恰好满载，无安全余量) |

> **V20 修正说明**: V19 错误地计算"单次推理42GB x 4并发 = 168GB"，将模型权重(38GB)重复计算了4次。正确的计算方式是: 模型权重仅加载一次，并发请求仅增加 KV Cache 显存 (2GB/请求)。因此 N 并发峰值 = 38GB + N x 2GB + 2GB。

**并发请求限制策略**:

| 参数 | 限制值 (V20) | 依据 |
|------|--------|------|
| 最大并行推理请求数 | **2** (V20: 从4下调) | 2并发峰值44GB，占48GB显存的91.7%，保留~8.3%安全余量防 OOM |
| Ollama 请求队列长度 | 50 | 超出并发限制时排队等待 |
| 单个推理超时 | 60 秒 | P99 延迟告警阈值 |
| KV Cache 清理策略 | 推理完成后立即释放 | 避免显存碎片化 |
| 显存 OOM 保护 | 请求数达到 2 时拒绝新请求, 入队等待 | 防止 GPU 崩溃 |
| 4并发需求 (可选) | 需升级至 80GB GPU (如 A100/H100) | 4并发峰值48GB，需80GB GPU才有余量 |

**显存压力测试建议**:
- 测试场景: 模拟 9 个命名 Agent 同时发起推理请求
- 预期行为: 前 2 个请求立即执行, 后 7 个进入 Ollama 内置队列
- 预期延迟: 前 2 个 ~30s (P95), 队列中 ~60-120s (取决于前面请求完成时间)
- 监控指标: `gpu_memory_used_bytes` 不超过 44GB (留 4GB 安全余量)

**详细资源分解 (V20 修正)**:

> **峰值计算依据**: 以下分解逐项列出各组件在峰值负载下的资源消耗，便于验证推荐配置的合理性。

| 组件 | CPU | 内存 | GPU | 说明 |
|------|-----|------|-----|------|
| FastAPI 后端 | 2 核 | 4GB | - | 2 Workers |
| WS Worker | 1 核 | 2GB | - | 1 Worker |
| Celery Worker | 2 核 | 4GB | - | 8 并发 |
| Celery Beat | 0.5 核 | 0.5GB | - | 定时任务 |
| Swarm Executor | 1 核 | 2GB | - | 主备双实例 (各0.5核/1GB) |
| PostgreSQL (主库) | 2 核 | 8GB | - | 主数据库 |
| PostgreSQL (Gitea) | 1 核 | 4GB | - | Gitea 数据库 (完全独立实例) |
| Redis | 1 核 | 4GB | - | 缓存/队列 (含 Replica 和 Sentinel 增量) |
| Gitea | 1 核 | 2GB | - | 代码托管 |
| Nginx | 0.5 核 | 0.5GB | - | 反向代理 |
| Ollama | 8 核 | 48GB | 42GB GPU | 72B Q4 模型 + 单请求推理 (V20) |
| 命名 Agent (9个, V20 新增明细) | 9 核 | 18GB (2GB/个) | 共享 Ollama | 宿主进程 (详见下方子表) |
| 编程 Agent 容器 (峰值4个) | 16 核 (4核/个) | 32GB (8GB/个) | - | 并发上限 (V19: 16->4) |
| 基础设施监控 | 1 核 | 4GB | - | Prometheus/Grafana/Loki |
| **总计** | **~45.5 核** | **~121GB** | **42GB GPU** | **峰值需求 (V20 修订)** |

**命名 Agent 资源明细表 (V20 新增)**:

| Agent | 角色 | CPU | 内存 | GPU | 说明 |
|-------|------|-----|------|-----|------|
| 海梅 (HaiMei) | 项目经理 | 1 核 | 2GB | 共享 Ollama | 协调调度，推理请求量中等 |
| 后兴 (HouXing) | 需求分析师 | 1 核 | 2GB | 共享 Ollama | 大量文本生成任务 |
| 后旺 (HouWang) | 架构设计师 | 1 核 | 2GB | 共享 Ollama | 文档生成，推理请求量大 |
| 后发 (HouFa) | 程序员 | 1 核 | 2GB | 共享 Ollama | 蜂群管理，自身推理量较小 |
| 后达 (HouDa) | 测试员 | 1 核 | 2GB | 共享 Ollama | 蜂群管理，自身推理量较小 |
| 后富 (HouFu) | CI/CD 工程师 | 1 核 | 2GB | 共享 Ollama | 环境配置生成 |
| 后贵 (HouGui) | 文档管理员 | 1 核 | 2GB | 共享 Ollama | 文档一致性检查 |
| 后荣 (HouRong) | QA | 1 核 | 2GB | 共享 Ollama | 产出物检验推理 |
| 后华 (HouHua) | 安全员 | 1 核 | 2GB | 共享 Ollama | 代码审计推理 |
| **9 个合计** | - | **9 核** | **18GB** | **共享 Ollama** | - |

> **命名 Agent 并发执行说明**: 9 个 Agent 通常不会同时执行推理任务。实际场景中最多 2-3 个 Agent 并发推理 (如后旺架构设计 + 后兴需求分析并行)。所有 Agent 共享 Ollama 内置请求队列，由 Ollama 并发限制 (最大 2 个并行推理) 控制总并发量。因此 Agent 进程的 CPU/内存资源是叠加的 (9核/18GB)，但 GPU 显存不叠加。

**实际运行建议 (V19 修订)**:
- 编程 Agent 容器全局并发上限下调至 4 个 (原 16 个)，原因是:
  (1) 峰值 16 个容器 x 4 核 x 8GB = 64 核 / 128GB 就占满了推荐的 CPU 和内存, 基础设施/Ollama/命名 Agent 无资源可用
  (2) 实际场景中 9 个步骤并行执行蜂群任务的情况极少 (通常仅步骤 8/9/10/11 使用蜂群, 且它们串行执行)
  (3) 单项目上限维持 4 个, 全局上限与单项目上限一致
- 按 4 个并发编程 Agent 容器重新计算资源需求:
  - 峰值 CPU: 基础设施(11.5核) + Ollama(8核) + 命名Agent(9核) + 编程Agent(16核) + 监控(1核) = ~45.5 核
  - 峰值内存: 基础设施(19GB) + Ollama(48GB) + 命名Agent(18GB) + 编程Agent(32GB) + 监控(4GB) = ~121GB
  - 实际推荐: 64 核 CPU / 192GB 内存 / 48GB GPU 显存 (峰值基础上预留 ~30% 安全余量)

### 4.5 数据库容量规划

**PostgreSQL (主库)**:
- **最大连接数**: 200 (shared_buffers=4GB, effective_cache_size=12GB)
  - FastAPI 后端连接池: 20 (SQLAlchemy pool_size=20, max_overflow=10)
  - Celery Worker 连接池: 10
  - WS Worker 连接池: 5
  - Patroni 监控连接: 5
  - 预留: 160 (用于备份、监控、管理连接)
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
  - max_wal_senders: 3 (流复制预留)
  - wal_level: replica (启用流复制)

**PostgreSQL (Gitea)**:
- **与主库隔离关系 (V18 明确)**: Gitea 数据库使用完全独立的 PostgreSQL 实例，不共享主库的 Patroni 集群、数据目录、或连接池。独立部署的原因是: (1) Gitea 数据库访问模式与 DevFlow 主库差异较大 (大量小表随机读写 vs 主库的事务型操作) (2) 故障隔离，Gitea 数据库问题不会影响主库 (3) 备份策略不同 (Gitea 数据量增长更快)
- **最大连接数**: 100
- **存储规划**: 初始 10GB，按代码仓库数量线性增长
- **IOPS 规划**: 1000 IOPS (SSD)

**Redis**:
- **内存规划**: maxmemory=4GB
  - Celery 任务队列: 512MB
  - Session 存储: 256MB (50 并发用户 x 5KB/session x 冗余)
  - 缓存层: 2GB (项目元数据、Agent 执行结果缓存)
  - 预留: 1GB (峰值缓冲)
- **数据隔离方案 (V18 新增)**:
  - 采用 Redis 分 DB 编号方案隔离不同用途的数据:
    - DB0 (database=0): 缓存层 (项目元数据、Agent 执行结果缓存、前端页面缓存)
    - DB1 (database=1): Celery Broker 任务队列 (任务消息、结果后端)
    - DB2 (database=2): Session 存储 (用户会话、Refresh Token)
  - 各 DB 之间完全隔离, `FLUSHDB` 操作只影响单个 DB, 不会误删其他数据
  - 连接配置示例:
    - 缓存: `redis://:password@redis-sentinel:26379/0`
    - Celery Broker: `sentinel://devflow-redis@redis-sentinel1:26379;sentinel://devflow-redis@redis-sentinel2:26379;sentinel://devflow-redis@redis-sentinel3:26379/1`
    - Session: `redis://:password@redis-sentinel:26379/2`
  - key 前缀规范 (DB 内进一步隔离):
    - DB0: `cache:project:*`, `cache:agent_result:*`, `cache:page:*`
    - DB1: Celery 自动管理 key 命名 (chord:*、celery:*、task_result:*)
    - DB2: `session:*`, `refresh:*`
- **持久化**: AOF everysec + RDB 每 15 分钟
- **最大客户端连接**: 10000
- **Sentinel 模式**: 3 个 Sentinel 节点, 部署在独立容器中

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
3. 从预热容器池分配或创建新 Docker 容器，挂载项目工作空间
4. 容器启动，执行编码/测试任务
5. 任务完成，结果回传 (见 4.7 节)
6. 容器返回预热池或自动销毁，释放资源

**并发控制**:
- 全局并发上限: 4 个容器 (V19: 原 16 个下调)
- 单项目并发上限: 4 个容器
- 超出上限时任务进入队列等待
- 优先级: QA 不通过重试 > 正常步骤 > 并行任务

**Celery 并发与编程 Agent 容器调度映射 (V18 新增)**:

| 概念 | 数量 | 说明 |
|------|------|------|
| Celery Worker 并发数 | 8 | 同时可执行 8 个 Celery 任务 |
| 编程 Agent 容器全局上限 | 4 | Swarm Executor 同时运行的容器总数上限 (V19: 16->4) |
| 1 个 Celery 任务 = ? | 1 次蜂群编排 | 1 个 Celery 任务对应 1 次蜂群任务编排, 可启动 1-4 个编程 Agent 容器 (取决于任务复杂度) |
| 最大并行容器数 | 4 | 全局上限下调至 4 个 (V19 修订) |
| 实际场景 | 通常 1-4 个容器 | 大多数步骤只需 1-2 个容器，复杂步骤 (如代码编写) 可能用到 3-4 个 |

**调度映射示例**:
- 步骤 8 (TDD 测试编写): 1 个 Celery 任务 -> 后发建立蜂群 -> Swarm Executor 创建 2-4 个编程 Agent 容器并行编写测试用例
- 步骤 9 (代码编写): 1 个 Celery 任务 -> 后发建立蜂群 -> Swarm Executor 创建 2-4 个编程 Agent 容器并行编写代码
- 步骤 10 (单元测试): 1 个 Celery 任务 -> 后达建立蜂群 -> Swarm Executor 创建 2-3 个编程 Agent 容器并行执行测试
- 步骤 3 (架构设计): 1 个 Celery 任务 -> 后旺命名 Agent 直接执行 (无需编程 Agent 容器)

### 4.7 编程 Agent 结果回传机制

**三种结果回传方式 (明确主备关系)**:

**主方式 — HTTP 回调 (首选)**:
- 编程 Agent 容器完成任务后，主动调用 Swarm Executor 的回调接口
- POST /internal/swarm/callback/{container_id}
- Body 包含: 任务 ID、状态、结果摘要、产出文件路径、MD5 校验和
- Swarm Executor 收到回调后, 验证文件写入 (存在性+MD5), 确认成功后更新任务状态
- 适用场景: 所有任务完成通知和结构化结果回传
- 优势: 实时通知, 无轮询延迟, 带校验

**备方式 — 共享挂载卷文件轮询 (故障转移)**:
- **触发条件**: HTTP 回调失败 (容器网络不通或 Swarm Executor 不可达)
- 编程 Agent 容器将结果写入共享挂载卷的指定路径, 并写入一个 .done 标记文件
- Swarm Executor 定期轮询该路径 (5 秒间隔)
- 检测到 .done 标记文件后, 读取结果文件, 验证后上传到 Celery 任务结果
- 适用场景: HTTP 回调不可用时的降级方案
- 劣势: 有 5 秒轮询延迟

**辅助方式 — Docker 日志采集 (进度跟踪)**:
- Swarm Executor 通过 Docker API 实时采集容器 stdout/stderr
- 解析日志中的结构化输出 (JSON 格式)
- 适用场景: 仅用于进度更新、状态通知、错误信息, 不作为结果回传的主要方式
- 不与主备方式竞争, 并行运行提供实时可见性

**故障转移逻辑**:

```
编程 Agent 完成任务
        |
        v
  尝试 HTTP 回调 (主方式)
        |
   +----+----+
   |         |
  成功      失败
   |         |
   v         v
更新状态   写入共享挂载卷 + .done 标记 (备方式)
            |
            v
      Swarm Executor 轮询检测到 .done
            |
            v
          验证并更新状态
```

**结果回传时序**:
```
编程 Agent 容器           Swarm Executor          Celery Worker
       |                       |                       |
       |--- Docker 日志 ------->| (实时采集进度, 辅助方式)
       |                       |                       |
       |--- HTTP 回调 -------->|--- 验证文件写入 ------|
       |                       |--- 更新任务状态 ------>|
       |                       |                       |--- 更新 project_steps
       |                       |                       |
   (回调失败时)                |                       |
       |--- 写入共享挂载卷 ---->|                       |
       |                       |--- 轮询检测到 --------|
       |                       |--- 更新任务状态 ------>|
       |--- 容器返回预热池 ---->|                       |
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
- 编程 Agent 容器在独立的 Docker 网络中 (devflow-swarm)
- 仅允许访问: Ollama 容器 (11434 端口)、Gitea 容器 (3000 端口)、Swarm Executor (8090 端口)
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

### 4.9.1 命名 Agent 部署模型合理性说明 (V21 新增)

> **后荣指出**: 9 个命名 Agent 以 systemd 宿主进程运行，与 Docker Compose 容器化部署模式不一致，增加了运维复杂度。

**采用 systemd 宿主进程的原因**:

1. **文件系统访问需求**: 命名 Agent 需要直接读写项目目录 (/DevFlow/projects/{project_id}/)，包含源代码、文档、测试文件等。容器化虽然可以通过绑定挂载实现，但涉及跨容器/跨网络的文件路径映射，增加了复杂性。

2. **本地工具链依赖**: 命名 Agent 在执行任务时需要调用宿主机上的工具链 (git、pytest、node、npm、docker 等)。容器化需要将这些工具链全部打包进镜像，导致镜像体积庞大且更新频繁。

3. **Hermes Profile 配置**: 每个命名 Agent 对应一个 Hermes Profile，包含独立的技能库、配置文件、.env 文件等。systemd 可以直接读取宿主机的配置，容器化则需要额外的卷挂载配置。

4. **崩溃恢复可靠性**: systemd 的 Restart=always + RestartSec=10 策略提供了可靠的进程级崩溃恢复，与 Docker 的 restart:unless-stopped 策略效果一致。

**统一监控方案 (V21 新增)**:

| 监控维度 | 容器组件方案 | 命名 Agent 方案 | 统一方式 |
|---------|------------|--------------|---------|
| 资源指标 | cadvisor (Docker) | node-exporter (PID) | Prometheus 统一采集 |
| 日志收集 | Loki + Docker driver | Loki + systemd journal | Loki 统一聚合 |
| 健康检查 | Docker healthcheck | HTTP /health 端点 | 统一的 /health API |
| 崩溃恢复 | restart:unless-stopped | Restart=always | 等效策略 |
| 启动顺序 | depends_on | After= + Requires= | 等效依赖管理 |

**具体实现**:

- **Prometheus 采集**: 使用 `process-exporter` 或自定义 exporter 采集命名 Agent 进程的 CPU/内存指标, 与 cadvisor 采集的容器指标统一进入 Prometheus。
- **Loki 日志收集**: 配置 `promtail` 读取 `/var/log/journal` 中命名 Agent 的 systemd 日志, 与 Docker 容器日志统一进入 Loki。
- **健康检查**: 命名 Agent Gateway API 暴露 HTTP /health 端点, Celery Worker 每 30 秒探测, 与容器的 Docker healthcheck 等效。

**容器化升级路径 (可选)**:

若未来需要统一为全容器化部署，可采用以下方案:

1. 构建命名 Agent 专用 Docker 镜像 (包含 Hermes + 所有工具链)
2. 绑定挂载项目目录: `-v /DevFlow/projects:/DevFlow/projects`
3. 绑定挂载 Profile 配置: `-v ~/.hermes/profiles/{profile}:/root/.hermes/profile`
4. 使用 Docker Compose 统一管理所有服务
5. 网络: 命名 Agent 容器加入 devflow-app 网络, 可访问 Ollama、后端等服务

**结论**: 当前 systemd 宿主进程方案是合理的权衡选择，在运维复杂度和功能需求之间取得了平衡。统一监控方案已覆盖容器和宿主进程的差异。全容器化作为升级路径保留。

### 4.10 Ollama 横向扩展方案 (V15 新增)

**扩展瓶颈分析**: Ollama 单实例+内置请求队列的设计, 当项目并发量增加时, 推理层将成为性能瓶颈。72B Q4 模型权重占用约 38GB 显存 (所有并发请求共享), 单次推理总计约 42GB (含 KV Cache 2GB 和系统开销 2GB), 48GB GPU 显存下最大支持 2 个并行推理请求 (V20 修正: 峰值 44GB/48GB)。

**横向扩展方案**:

1. **多实例部署 (同机多 GPU)**:
   - 条件: 宿主机拥有多块 GPU
   - 方案: 部署多个 Ollama 容器, 每块 GPU 运行一个实例
   - 负载均衡: Nginx 层对 Ollama API 请求进行轮询分发
   - 模型预热: 每个实例独立加载模型, 总显存需求 = 实例数 x 单模型显存

2. **多实例部署 (多机分布式)**:
   - 条件: 多台带 GPU 的宿主机
   - 方案: 每台主机部署 Ollama 容器, Nginx 层跨机器负载均衡
   - 模型同步: 模型文件通过共享存储 (NFS) 或预先拉取到各节点
   - 故障转移: 某节点故障时, Nginx 自动将请求路由至其他可用节点

3. **请求批处理优化**:
   - Ollama 支持批量推理请求, 将多个命名 Agent 的短请求合并为一次批量推理
   - 适用场景: 文档分析、代码审查等批量任务
   - 实现: Celery Worker 收集待推理请求, 每隔 2 秒或积攒 5 个请求后批量发送

4. **模型缓存与预热**:
   - 系统启动时预热模型, 避免首次推理的加载延迟
   - Ollama 的 keep_alive 参数设置为 -1 (永久驻留), 避免模型卸载

### 4.11 编程 Agent 容器池预热策略 (V15 新增)

**冷启动问题分析**: Swarm Executor 动态创建/销毁容器, 容器冷启动时间包括: 镜像拉取 (~30秒, 首次)、容器初始化 (~5秒)、环境准备 (~10秒), 总计约 45 秒 (首次) 或 15 秒 (镜像已缓存)。这将显著影响任务响应时间。

**预热策略**:

1. **空闲预热容器池**:
   - Swarm Executor 在空闲时保持 2 个预热容器运行
   - 预热容器已加载镜像、完成环境初始化, 可随时接收任务
   - 任务到达时直接分配预热容器, 响应时间从 15-45 秒降至 1-2 秒
   - 预热容器空闲超时: 10 分钟后自动销毁, 再重新创建预热容器

2. **镜像本地缓存**:
   - 宿主机预先拉取 devflow/coding-agent:latest 镜像
   - 镜像更新时, Swarm Executor 后台拉取新镜像, 不影响现有任务
   - 容器创建时直接使用本地缓存镜像, 跳过网络拉取环节

3. **层叠预热 (可选)**:
   - 预测即将到来的任务 (如第 9 步代码编写通常在第 8 步 TDD 完成后触发)
   - 在第 8 步执行期间, 提前启动 1-2 个预热容器
   - 第 8 步完成后, 预热容器已就绪, 立即分配

4. **预热容器资源管理**:
   - 预热容器使用最低资源配置 (1 核 CPU / 2GB 内存)
   - 分配任务时, Swarm Executor 动态调整资源限制至正式配置 (4 核 / 8GB)
   - 预热容器总数不超过 4 个, 避免资源浪费

5. **预热健康检查**:
   - Swarm Executor 每 30 秒检查预热容器状态
   - 异常预热容器自动销毁并重新创建
   - 预热容器数量不足时自动补充

### 4.12 推理层并发排队 SLA 分析 (V21 新增)

> **后荣指出**: V20 将 Ollama 并发上限从 4 下调至 2（受 48GB 显存限制），但系统有 9 个命名 Agent + 最多 4 个编程 Agent = 13+ 个 Agent 共享单一 Ollama 实例。缺少正式的并发排队 SLA 分析、超时策略或请求优先级机制。

**并发排队场景分析**:

| 场景 | 并发请求数 | 立即执行 | 排队等待 | 最大排队延迟 | 说明 |
|------|-----------|---------|---------|-------------|------|
| 正常串行 | 1 | 1 | 0 | 0s | 大多数场景, Agent 串行执行 |
| 轻度并发 | 2-3 | 2 | 0-1 | 0-30s | 2个Agent并行, 如架构+需求 |
| 中度并发 | 4-6 | 2 | 2-4 | 30-90s | 多个Agent同时提交推理请求 |
| 重度并发 | 7-13 | 2 | 5-11 | 90-210s | 极端场景, 所有Agent同时推理 |

> **注意**: 72B 模型单次推理约 30-120 秒 (取决于 prompt 长度和输出长度)。上述延迟按平均 30 秒/请求估算。

**SLA 目标**:

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| P50 排队延迟 | < 30 秒 | Prometheus: `ollama_request_queue_wait_seconds` |
| P95 排队延迟 | < 60 秒 | 同上 |
| P99 排队延迟 | < 120 秒 | 同上 |
| 排队超时阈值 | 60 秒 | 超过则自动降级或拒绝 |
| 推理总延迟 (P95) | < 90 秒 (排队+推理) | 端到端追踪 |

**请求优先级机制 (V21 新增)**:

Ollama 内置队列按优先级调度，分为 3 级:

| 优先级 | 级别值 | 适用场景 | 示例 |
|--------|--------|---------|------|
| 紧急 (High) | 1 | QA 检验、安全审计、项目验收 | 后荣 QA 检验、后华安全审计、海梅项目验收 |
| 正常 (Normal) | 2 | 常规步骤执行 | 后兴需求分析、后旺架构设计、后富环境搭建 |
| 低 (Low) | 3 | 文档整理、非关键任务 | 后贵文档一致性检查 |

**优先级调度规则**:
1. 高优先级请求到达时，若队列中有低优先级请求正在等待，高优先级请求可插队 (preempt)
2. 正在执行的推理请求不会被抢占 (推理一旦开始必须完成)
3. 同优先级请求按 FIFO 顺序执行
4. Celery Worker 调用 Gateway API 时传递优先级参数: `X-Priority: high|normal|low`

**超时策略 (V21 新增)**:

| 超时类型 | 阈值 | 处理策略 |
|---------|------|---------|
| 排队超时 | 60 秒 | 自动降级至云端 API (L2) 或返回 503 |
| 推理超时 | 120 秒 | 终止当前推理, 返回超时错误, 触发重试 |
| 总超时 (排队+推理) | 180 秒 | 任务标记为 failed, 进入重试队列 |

**排队等待期间的 Agent 优化 (V21 新增)**:

命名 Agent 在推理请求排队等待期间不应空闲等待，可执行以下并行工作:
1. **本地预处理**: 读取/解析项目文件、构建上下文、准备 prompt 模板
2. **文件操作**: 读取历史文档、计算文件哈希、检查目录结构
3. **状态更新**: 向 Celery Worker 报告当前进度 (progress 字段)
4. **群聊通信**: 在群聊中发送进度更新消息

**前端 UI 排队状态可见性 (V21 新增)**:

- 前端通过 WebSocket 实时获取 Ollama 队列状态
- 显示内容:
  - 当前排队中的请求数
  - 预估等待时间 (队列长度 x 平均推理时间)
  - 当前正在执行的推理任务 (Agent 名称 + 步骤名称)
- 当排队超过 30 秒时，前端显示黄色警告条: "推理服务繁忙，预计等待 X 秒"
- 当排队超过 60 秒时，前端显示橙色警告条 + 自动降级提示: "推理排队超时，已切换至云端模型"

**并发升级路径**:

| GPU 配置 | 最大并发 | 排队改善 | 成本 |
|---------|---------|---------|------|
| 48GB (当前) | 2 | 中度并发排队 30-90s | 基准 |
| 80GB (A100/H100) | 4 | 重度并发排队降至 30-60s | ~2x |
| 2x48GB (双GPU) | 4 (每卡2) | 基本消除排队 | ~2x |
| 2x80GB (双GPU) | 8 (每卡4) | 完全消除排队 | ~4x |

---

## 5. 高可用与容灾方案

### 5.1 可用性目标 (V20 修正)

- **目标可用性**: 99% (软件层面，月停机时间 < 7.3 小时)
- **核心服务可用性**: FastAPI、PostgreSQL、Redis、Ollama
- **非核心服务**: Gitea、监控组件

> **单机架构可用性约束 (V20 新增)**: 当前架构为"单机 + Docker Compose"部署模式。软件层面的高可用方案 (Patroni 主从切换、Redis Sentinel 故障转移、Docker 自动重启等) 只能应对**容器/进程级别的故障**，无法应对**宿主机级别的故障** (主机宕机、磁盘故障、网络中断、电源故障)。因此：
> - 软件层面可用性目标: 99% (约每月 < 7.3 小时停机)
> - 包含硬件故障的真实可用性: 取决于宿主机可靠性，通常低于 99%
> - 达到 99.9% 可用性需多节点部署 (见 5.10 节升级路径)
> - 见 5.11 节了解所有单点故障组件的详细分析

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

### 5.5 Ollama 故障降级策略

**四级降级策略**:

**第一级 — Ollama 备实例切换 (自动)**:
- **触发条件**: Ollama 主实例健康检查连续 2 次失败 (间隔 30 秒)
- **自动切换流程**:
  1. Celery Worker 调用 Ollama 前执行健康检查 (HTTP GET /api/tags)
  2. 健康检查失败计数器 +1, 达到阈值 2 时标记主实例为 down
  3. Gateway 层自动将推理请求路由至 Ollama 备实例 (端口 11435)
  4. Prometheus 指标 `ollama_primary_status` 置为 0, `ollama_standby_active` 置为 1
  5. Alertmanager 触发 P2 级别告警通知管理员
- **切换延迟**: 约 30 秒 (2次健康检查 x 间隔30秒)
- **降级期间功能限制**: 无明显功能限制, 备实例使用相同模型
- **备实例部署要求**: 备实例需预加载相同模型, 占用额外 48GB 显存 (需双 GPU 或大显存)

**第二级 — 云端模型切换 (自动)**:
- **触发条件**: Ollama 主备实例均不可用 (或仅部署单实例时主实例故障)
- **故障检测责任方 (V20 新增)**:
  - 第一检测层: Celery Worker 调用 Ollama 前执行健康检查 (HTTP GET /api/tags, 超时 5 秒)
  - 第二检测层: Prometheus 每 30 秒采集 Ollama 健康指标, 连续 3 次失败触发 P1 告警
  - 第三检测层: Alertmanager 通知管理员介入
- **自动切换流程**:
  1. Celery Worker 调用 Ollama 前执行健康检查
  2. 主备实例均健康检查失败计数器 +1, 达到阈值 3 时标记 Ollama 为 down
  3. Gateway 层自动将推理请求路由至云端模型 API (OpenAI/Anthropic)
  4. 云端 API Key 从 .env 读取 (FALLBACK_OPENAI_API_KEY / FALLBACK_ANTHROPIC_API_KEY)
  5. 降级模型配置: FALLBACK_MODEL_PROVIDER=openai, FALLBACK_MODEL=gpt-4
  6. Prometheus 指标 `ollama_status` 置为 0, `fallback_active` 置为 1
  7. Alertmanager 触发 P1 级别告警通知管理员
- **切换延迟 (V20 新增, V21 修正)**:
  - 健康检查检测延迟: 5 秒 (超时阈值) x 3 (失败计数) = 15 秒
  - Gateway 路由切换: < 1 秒 (配置切换, 无状态)
  - 首次云端 API 调用: 1-3 秒 (网络延迟 + API 初始化)
  - 总计切换延迟: 约 15-20 秒 (V21 确认: 远优于 60 秒目标)
- **云端 API Key 管理 (V20 新增)**:
  - 存储方式: .env 文件 (FALLBACK_OPENAI_API_KEY / FALLBACK_ANTHROPIC_API_KEY)
  - 密钥轮换: 每 90 天自动轮换, 轮换期间新旧 Key 并行有效 24 小时
  - 访问控制: .env 文件权限 600, 容器内通过环境变量注入, 不挂载明文文件
  - 密钥注入: Docker Compose 通过 env_file 或 environment 变量传递, 不硬编码
- **云端 API 成本控制 (V20 新增, V21 细化)**:
  - **每日预算上限**: $50/天 (默认, 可通过 FALLBACK_DAILY_BUDGET 环境变量调整)
  - **单次请求最大花费**: $0.50 (超过则自动截断输出, 防止单次请求费用过高)
  - **自动熔断机制**:
    - 当日 API 费用达到预算 80% ($40) 时: 发出 P2 告警 (邮件通知)
    - 当日 API 费用达到预算 100% ($50) 时: 发出 P1 告警 (邮件 + Webhook), **自动熔断** — 停止所有云端 API 调用, 降级至第三级 (排队限流)
  - **熔断恢复**: 次日零点 (UTC+8) 自动重置预算计数器, 恢复云端 API 调用
  - **成本监控频率**: Prometheus 每 5 分钟采集一次 `cloud_api_daily_cost` 指标
  - **成本监控告警级别**:
    | 费用占比 | 告警级别 | 通知方式 | 自动动作 |
    |---------|---------|---------|---------|
    | 50% ($25) | P3 (信息) | 无 | 记录日志 |
    | 80% ($40) | P2 (警告) | 邮件 | 无 |
    | 100% ($50) | P1 (紧急) | 邮件 + Webhook | 自动熔断 |
  - **请求量控制**: 云端 API 最大 QPS=10, 避免突发流量导致费用激增
- **降级期间功能限制**:
  - 推理成本增加 (按云端 API 调用计费)
  - 响应延迟可能增加 (网络依赖)
  - 输出格式可能与本地模型略有差异 (需适配不同模型的 prompt 模板)
  - 不受本地模型大小限制，但受云端 API 速率限制

**第三级 — 排队限流 (自动, V21 修正)**:
- **触发条件**: Ollama 部分可用 (响应慢但非完全不可用，P99 延迟 > 60 秒) 或云端 API 预算耗尽
- **V21 修正**: 排队超时从 5 分钟降至 60 秒
- **自动限流流程**:
  1. 启用请求排队机制, 最大排队数: 50
  2. **排队超时: 60 秒** (V21 修正: 原 5 分钟)
  3. 超过排队数或排队超时则返回 503, 建议稍后重试
  4. 排队队列按优先级排序: QA 重试 > 正常步骤 > 并行任务
- **前端 UI 缓解方案 (V21 新增)**:
  - **排队等待 < 30 秒**: 前端显示蓝色状态条 "推理服务处理中, 请稍等..."
  - **排队等待 30-60 秒**: 前端显示黄色警告条 "推理服务繁忙, 预计等待 X 秒" (X 为预估剩余时间)
  - **排队等待 > 60 秒**: 前端显示橙色警告条 "推理排队超时, 已自动切换至云端模型或建议稍后重试"
  - **预估恢复时间计算**: 当前队列长度 x 平均推理时间 (30 秒/请求), 通过 WebSocket 实时推送给前端
  - **用户操作建议**: 排队期间用户可继续浏览其他页面, 不影响非推理相关操作

**第四级 — 任务延迟 (手动)**:
- **触发条件**: 所有推理服务不可用 (Ollama + 云端 API 均故障)
- **手动操作流程**:
  1. 标记受影响的任务为 pending_retry 状态
  2. 前端显示"推理服务不可用，任务已暂停"
  3. Celery Beat 每 10 分钟检查推理服务状态
  4. 服务恢复后自动重新执行排队任务

**故障恢复后回切策略**:
1. **自动回切条件**: Ollama 主实例健康检查连续 5 次成功 (间隔 30 秒)
2. **回切流程**:
   - 逐步将请求从云端模型切换回 Ollama (先 10% 流量, 再 50%, 最后 100%)
   - 灰度回切期间同时监控 Ollama 延迟和错误率
   - 回切完成后 Prometheus 指标恢复
   - Alertmanager 发送恢复通知
3. **回切失败处理**: 若灰度回切期间 Ollama 再次异常, 立即切回云端模型并重新告警
4. **数据一致性**: 降级期间使用云端模型生成的产出物与本地模型保持一致, QA 检验标准不变

### 5.6 PostgreSQL 高可用方案 (V15 新增)

**问题分析**: PostgreSQL 主库采用单实例部署, 无主从复制/流复制设计, 数据库故障将导致系统完全不可用。

**采用方案**: Patroni + etcd 自动故障转移

**架构设计**:

```
PostgreSQL 主节点 (postgres-primary:5432)
    |--- 流复制 (WAL streaming) ---|
PostgreSQL 从节点 (postgres-standby:5432)

Patroni 节点 1 (集成在主节点容器中)
Patroni 节点 2 (集成在从节点容器中)
Patroni 节点 3 (独立容器, 仲裁节点)

etcd 集群 (3 节点, 用于 Patroni 分布式锁)
    |--- 存储集群状态 ---|
    |--- 领导者选举 ---|

PgBouncer (连接池, 统一入口: 5432)
    |--- 读写分离 ---|
    |--- 连接复用 ---|
```

> **单机 Patroni 局限性说明 (V21 新增)**:
> 当前 Patroni + etcd 部署在单一宿主机上，存在以下局限性：
>
> 1. **宿主机级别故障无法应对**: 当宿主机宕机、断电、或网络中断时，PostgreSQL 主从节点、Patroni 节点、etcd 节点同时失效，Patroni 无法执行故障转移 (因为 etcd quorum 也丢失了)。这是单机架构的根本限制。
>
> 2. **etcd quorum 局限性**: etcd 需要多数派 (quorum) 才能正常工作。3 节点同机部署时，宿主机故障会导致 3 节点全部丢失，quorum 机制完全失效。跨主机部署 etcd 才能真正发挥 quorum 价值。
>
> 3. **同主机从库的实际价值**: 尽管无法应对宿主机故障，同主机流复制从库仍有以下价值:
>    - **读取负载均衡**: 可通过 PgBouncer 将只读查询路由至从库, 减轻主库压力
>    - **数据冗余备份**: 从库数据目录可作为额外的数据副本, 降低数据丢失风险
>    - **容器/进程级故障恢复**: PostgreSQL 容器崩溃或 Patroni 进程异常时, 主从切换仍然有效 (故障窗口 10-30 秒)
>    - **零数据丢失**: 同步复制模式 (synchronous_commit=on) 保证主库写入确认前从库已接收, RPO=0
>
> 4. **多节点升级路径**: 真正的高可用需要跨宿主机部署:
>    - etcd 集群: 至少 2 台物理机, 每台部署 2 节点 (共 4 节点, quorum=3)
>    - PostgreSQL: 主库在 A 机, 从库在 B 机, 跨机流复制
>    - Patroni: 跟随 PostgreSQL 节点部署, 跨机故障转移
>    - 见 5.10 节了解完整的多节点部署方案

**Gitea 数据库隔离说明 (V18 补充)**:
- Gitea 数据库 (`postgres-gitea`) 是独立的 PostgreSQL 实例，不加入 Patroni 高可用集群
- 原因: Gitea 数据库访问量相对较小，独立部署简化运维，且故障隔离 (Gitea DB 故障不影响 DevFlow 主库)
- Gitea DB 采用 Docker 自动重启策略 (`restart: unless-stopped`) + 每日备份保障可用性
- 若需 Gitea DB 高可用，可后续独立部署 Patroni 集群

**部署方式 (Docker Compose)**:

```yaml
services:
  postgres-primary:
    image: ghcr.io/cybertec-postgresql/patroni:15
    environment:
      - PATRONI_SCOPE=devflow
      - ETCD_HOSTS=etcd1:2379,etcd2:2379,etcd3:2379
    volumes:
      - postgres_data:/home/postgres/pgdata
      - ./patroni.yml:/patroni.yml:ro
    restart: unless-stopped

  postgres-standby:
    image: ghcr.io/cybertec-postgresql/patroni:15
    environment:
      - PATRONI_SCOPE=devflow
      - ETCD_HOSTS=etcd1:2379,etcd2:2379,etcd3:2379
    volumes:
      - postgres_standby_data:/home/postgres/pgdata
      - ./patroni.yml:/patroni.yml:ro
    restart: unless-stopped

  etcd1:
    image: quay.io/coreos/etcd:v3.5
    environment:
      - ETCD_NAME=etcd1
      - ETCD_INITIAL_CLUSTER=etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
    restart: unless-stopped

  etcd2:
    image: quay.io/coreos/etcd:v3.5
    # ... 类似配置
    restart: unless-stopped

  etcd3:
    image: quay.io/coreos/etcd:v3.5
    # ... 类似配置
    restart: unless-stopped

  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      - DATABASE_URL=postgresql://devflow:***@postgres-primary:5432/devflow
    ports:
      - "5432:6432"
    restart: unless-stopped
```

**故障转移流程**:

1. **主节点故障检测**: Patroni 每 10 秒通过 etcd 分布式锁进行领导者选举, 若主节点失去锁, 判定为故障
2. **自动故障转移**: Patroni 选举从节点为新主节点, 提升为 writable 状态
3. **应用层切换**: 应用通过 PgBouncer 统一入口访问, 无需修改连接地址; PgBouncer 自动重连到新主节点
4. **恢复后重新加入**: 原主节点恢复后, Patroni 自动将其作为从节点加入集群, 通过流复制同步数据
5. **故障窗口**: 预计 10-30 秒 (故障检测 10 秒 + 提升 10-20 秒)

**数据一致性保障**:
- 流复制模式: synchronous_commit=on (同步复制, 强一致性)
- 性能权衡: 同步复制会降低写入性能约 10-20%, 但保证数据不丢失
- 若性能要求更高, 可切换为异步复制 (synchronous_commit=off), RPO 增大至毫秒级

**资源需求增量**:
- 从节点: 额外 2 核 CPU / 8GB 内存 / 50GB 存储
- etcd 集群: 3 个节点, 各 0.5 核 CPU / 0.5GB 内存
- PgBouncer: 0.5 核 CPU / 0.5GB 内存

### 5.7 Redis 高可用方案 (V15 新增)

**问题分析**: Redis 作为 Celery Broker 和缓存层, 单点部署存在单点故障风险, Redis 故障将导致所有异步任务停滞。

**采用方案**: Redis Sentinel 哨兵模式 (3 Sentinel + 1 Master + 2 Replica)

**架构设计**:

```
Redis Master (redis-master:6379)
    |--- 主从复制 ---|
Redis Replica 1 (redis-replica1:6379)
    |--- 主从复制 ---|
Redis Replica 2 (redis-replica2:6379)

Sentinel 1 (redis-sentinel1:26379)
Sentinel 2 (redis-sentinel2:26379)
Sentinel 3 (redis-sentinel3:26379)

应用层通过 Sentinel 发现 Master 地址
```

**部署方式 (Docker Compose)**:

```yaml
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 4gb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_master_data:/data
    restart: unless-stopped

  redis-replica1:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --replicaof redis-master 6379 --masterauth ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_replica1_data:/data
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-replica2:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --replicaof redis-master 6379 --masterauth ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_replica2_data:/data
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-sentinel1:
    image: redis:7-alpine
    command: redis-sentinel /sentinel.conf
    volumes:
      - ./sentinel1.conf:/sentinel.conf:ro
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-sentinel2:
    image: redis:7-alpine
    # ... 类似配置
    restart: unless-stopped

  redis-sentinel3:
    image: redis:7-alpine
    # ... 类似配置
    restart: unless-stopped
```

**Sentinel 配置 (sentinel.conf)**:

```
port 26379
sentinel monitor devflow-redis redis-master 6379 2
sentinel auth-pass devflow-redis ${REDIS_PASSWORD}
sentinel down-after-milliseconds devflow-redis 5000
sentinel failover-timeout devflow-redis 30000
sentinel parallel-syncs devflow-redis 1
```

**故障转移流程**:

1. **故障检测**: 3 个 Sentinel 每 1 秒 ping Redis Master, 连续 5 秒无响应判定为故障
2. **领导者选举**: Sentinel 之间进行 Raft 选举, 选出的领导者执行故障转移
3. **自动故障转移**: 领导者选择一个从节点提升为新的 Master
4. **应用层切换**: Celery Worker 通过 Sentinel 地址发现新的 Master; SQLAlchemy 连接池自动重连
5. **恢复后重新加入**: 原 Master 恢复后, Sentinel 自动将其作为从节点加入集群
6. **故障窗口**: 预计 5-15 秒

**应用层适配**:
- Celery Broker URL: 配置为 Sentinel 模式 `sentinel://devflow-redis@redis-sentinel1:26379;sentinel://devflow-redis@redis-sentinel2:26379;sentinel://devflow-redis@redis-sentinel3:26379/1`
- 缓存层: 使用 redis-py 的 Sentinel 客户端自动发现 Master (DB0)
- Session 存储: Sentinel 客户端 (DB2)
- 未完成的任务: Celery 从 AOF 日志恢复未确认的任务

**资源需求增量**:
- 2 个 Replica: 各 1 核 CPU / 4GB 内存
- 3 个 Sentinel: 各 0.25 核 CPU / 128MB 内存 (Sentinel 资源消耗极低)

### 5.8 Ollama 推理引擎高可用方案 (V15 新增)

**问题分析**: 9 个命名 Agent 共享单一 Ollama 容器, 未提及多 GPU 实例或故障转移方案, 推理引擎故障将阻塞所有 Agent 任务。

**高可用方案**:

1. **双实例主备模式 (推荐, 需双 GPU)**:
   - 主实例 (ollama:11434) + 备实例 (ollama-backup:11435)
   - 备实例预加载相同模型 (qwen2.5:72b-instruct-q4_K_M)
   - 正常情况所有请求走主实例
   - 主实例故障时自动切换至备实例 (见 5.5 节第一级降级策略)
   - 资源需求: 额外 1 块 GPU (48GB 显存)

2. **单实例 + 自动重启 (基本方案, 单 GPU)**:
   - Docker restart:unless-stopped 策略
   - Ollama 崩溃后自动重启, 模型重新加载 (约 60 秒)
   - 重启期间触发第二级降级 (云端模型切换)
   - 优势: 无需额外硬件投入
   - 劣势: 故障窗口较长 (60 秒 + 模型加载时间)

3. **多实例负载均衡 (高级方案, 多 GPU)**:
   - 部署 2-3 个 Ollama 实例, 每实例独立 GPU
   - Nginx 层对 Ollama API 请求进行轮询负载均衡
   - 某实例故障时自动从负载均衡池中剔除
   - 资源需求: N 块 GPU (N = 实例数)

**推荐方案**: 根据硬件条件选择:
- 双 GPU 环境: 采用方案 1 (双实例主备)
- 单 GPU 环境: 采用方案 2 (自动重启 + 云端降级)
- 多 GPU 环境: 采用方案 3 (多实例负载均衡)

### 5.9 Swarm Executor 高可用方案 (V18 新增)

**问题分析**: Swarm Executor 是编程 Agent 容器生命周期管理的唯一入口，单实例部署存在单点故障风险。Swarm Executor 故障将导致无法创建新的编程 Agent 容器（运行中的容器不受影响）。

**高可用方案 — 主备双实例部署**:

1. **主实例** (swarm-executor-primary, 端口 8090):
   - 正常情况所有蜂群编排请求由主实例处理
   - Celery Worker 默认调用主实例 HTTP API

2. **备实例** (swarm-executor-standby, 端口 8091):
   - 备实例持续运行，与主实例共享 Docker 守护进程
   - 备实例定期 (每 10 秒) 通过 HTTP GET /health 检查主实例状态

3. **故障转移流程**:
   - **自动切换**: Nginx 层配置 upstream 负载均衡, 主实例健康检查失败时自动将请求路由至备实例
   - **备实例接管**: 备实例检测到主实例故障后, 扫描现有 Docker 容器状态, 建立管理关系
   - **运行中的容器**: 不受影响, 继续执行任务, 结果通过 HTTP 回调 (主方式) 或共享挂载卷 (备方式) 回传
   - **新任务调度**: 备实例接管后, 继续接收 Celery 任务, 创建新的编程 Agent 容器

4. **Nginx 负载均衡配置**:
   ```nginx
   upstream swarm_executor {
       server swarm-executor-primary:8090 max_fails=2 fail_timeout=30s;
       server swarm-executor-standby:8091 backup;
   }
   ```

5. **降级策略 (主备均不可用时)**:
   - 管理员可通过 Docker CLI 手动操作:
     - `docker run` 手动创建编程 Agent 容器
     - `docker exec` 在容器内执行任务
     - `docker logs` 查看容器输出
   - 运行中的容器不受影响, 可正常完成任务
   - 新任务暂挂, 等待 Swarm Executor 恢复后继续调度

6. **数据一致性保障**:
   - Swarm Executor 不维护持久化状态 (无状态设计)
   - 容器状态通过 Docker API 实时查询, 备实例接管时可立即获取完整容器列表
   - 任务状态存储在 PostgreSQL 的 project_steps 表中, 不依赖 Swarm Executor

7. **资源需求增量**:
   - 备实例: 0.5 核 CPU / 1GB 内存 (与主实例相同规格)

### 5.10 命名 Agent 宿主机高可用方案 (V18 新增)

**问题分析**: 9 个命名 Agent 以 systemd 服务运行在单一宿主机上, 宿主机宕机将导致所有命名 Agent 不可用。systemd restart=always 只能处理进程级别崩溃, 无法处理宿主机级别故障。

**高可用方案 (按实施成本分级, V19 明确定位)**:

> **架构定位说明**: 当前 DevFlow 架构定位为"单机 + Docker Compose"部署模式 (见 8.1 节)。本节方案为**架构升级路径**, 供用户在业务规模增长后参考实施, 非当前必须部署的方案。

1. **基础方案 (当前, 低成本)**:
   - systemd Restart=always: 进程崩溃自动重启
   - systemd StartLimitBurst=5: 频繁崩溃时告警
   - 宿主机看门狗 (watchdog): Linux watchdog 内核模块, 系统死机时硬件级重启
   - 监控告警: Prometheus node-exporter 监控宿主机资源, 异常时 Alertmanager 通知

2. **推荐方案 (中成本, 架构升级路径 - 多节点部署)**:
   - 部署 2 台宿主机 (主 + 备)
   - 命名 Agent systemd 服务在两台上同时部署
   - 使用 keepalived + VIP (虚拟 IP) 实现故障转移:
     - 主节点 VIP: 192.168.1.100
     - 备节点: 192.168.1.101
     - keepalived 每 2 秒心跳检测, 主节点故障时 VIP 自动漂移至备节点
   - Celery Worker 通过 VIP 访问命名 Agent Gateway API
   - 故障窗口: 预计 2-5 秒 (keepalived 故障检测 + VIP 漂移)

3. **高级方案 (高成本, 云环境升级路径)**:
   - 使用云厂商负载均衡器 (如 AWS ALB / 阿里云 SLB) 替代 keepalived
   - 命名 Agent 部署在多个可用区的 ECS/EC2 实例上
   - 负载均衡器健康检查自动剔除故障节点
   - 配合自动伸缩组实现容量弹性

**推荐实施路径**:
- 第一阶段 (当前): 部署基础方案 (watchdog + 监控告警) — 单机部署
- 第二阶段 (升级): 评估多节点部署需求, 实施 keepalived + VIP 方案
- 第三阶段 (升级): 如迁移至云环境, 采用云厂商负载均衡器方案

**宿主机故障时的临时措施**:
- 宿主机宕机后, Celery Worker 检测到 Gateway API 不可达
- 任务进入等待队列, Celery Beat 每 1 分钟重试
- 宿主机恢复后, systemd 自动重启所有命名 Agent 服务
- 等待队列中的任务自动恢复执行

### 5.11 Gitea/Celery Beat/etcd/Nginx 单点故障分析与应对策略 (V20 新增)

**问题分析**: 后荣指出 Gitea、Celery Beat、etcd、Nginx 均为单实例部署，存在单点故障 (SPOF) 风险。本节逐一分析各组件 SPOF 风险、当前缓解措施和多节点升级方案。

| 组件 | SPOF 风险 | 故障影响 | 当前缓解措施 | 多节点升级方案 |
|------|-----------|----------|-------------|---------------|
| Gitea | 单实例，无主备 | 代码托管不可用，QA 通过后无法提交代码 | (1) Docker 自动重启 (2) 每日备份 (3) Git 数据独立持久化卷 | 双实例 + Nginx 负载均衡 + 共享 Git 数据卷 (NFS) |
| Celery Beat | 单实例，无故障转移 | 定时任务停止 (项目状态检查、超时清理等)，不影响正在执行的任务 | (1) Docker 自动重启 (2) 关键定时任务可由 Celery Worker 周期性触发代替 | 双实例 + 分布式锁 (Redis) 防止任务重复执行 |
| etcd | 单机部署 3 节点，但宿主机故障时 3 节点同时丢失 | Patroni 失去 quorum，无法进行主从切换 | (1) etcd 数据持久化 (2) 宿主机 watchdog 硬件级重启 (3) Prometheus 监控 etcd 健康状态 | 跨宿主机部署 etcd 集群 (至少 2 台物理机) |
| Nginx | 单实例，无 keepalived | 外部流量入口不可用，所有 HTTP/HTTPS 请求失败 | (1) Docker 自动重启 (2) 宿主机防火墙转发 80/443 到备用端口 | keepalived + VIP 漂移，或云厂商负载均衡器 |

**各组件 SPOF 详细分析**:

**1. Gitea 单点故障**:
- **故障场景**: Gitea 容器崩溃或数据卷损坏
- **影响范围**: 代码托管不可用，但已提交的代码保存在 Git 数据卷中
- **恢复步骤**:
  1. Docker 自动重启 Gitea 容器 (restart: unless-stopped)
  2. 若数据损坏，从每日备份恢复 (RPO=24h)
  3. Gitea 恢复后，DevFlow 后端自动重新连接
- **升级路径**: 双实例 + Nginx 反向代理 + NFS 共享 Git 数据目录

**2. Celery Beat 单点故障**:
- **故障场景**: Celery Beat 容器崩溃
- **影响范围**: 定时任务停止，但正在执行的 Celery Worker 任务不受影响
- **关键定时任务**:
  - 项目状态检查 (每 5 分钟)
  - 超时任务清理 (每 30 分钟)
  - 数据一致性核对 (每日)
- **缓解措施**: 将关键定时任务改为 Celery Worker 周期性触发 (crontab 模式)，减少依赖 Beat 单实例
- **升级路径**: 双实例 + Redis 分布式锁防止任务重复执行

**3. etcd 单点故障**:
- **故障场景**: 宿主机宕机导致 3 个 etcd 节点同时丢失
- **影响范围**: Patroni 失去分布式锁存储，无法进行 PostgreSQL 主从切换
- **关键矛盾**: etcd 需要 quorum (多数派) 才能正常工作，单机 3 节点在宿主机故障时全部丢失，quorum 机制失效
- **缓解措施**:
  1. 宿主机 watchdog 内核模块，系统死机时硬件级重启
  2. etcd 数据持久化到独立磁盘，降低数据丢失风险
  3. Prometheus 监控 etcd 健康状态，故障时告警
- **升级路径**: 跨宿主机部署 etcd 集群 (至少 2 台物理机，每台部署 2 节点，共 4 节点)

**4. Nginx 单点故障**:
- **故障场景**: Nginx 容器崩溃或配置错误
- **影响范围**: 所有外部 HTTP/HTTPS 请求失败，内部服务间通信不受影响
- **缓解措施**:
  1. Docker 自动重启
  2. 健康检查失败时 Alertmanager 告警
  3. 宿主机 iptables 可配置备用端口转发
- **升级路径**:
  - 方案 A: keepalived + VIP 漂移 (两台宿主机各部署 Nginx)
  - 方案 B: 云厂商负载均衡器 (AWS ALB / 阿里云 SLB)

**SPOF 风险等级评估**:

| 组件 | 故障概率 | 故障影响 | 恢复时间 | 综合风险 |
|------|---------|----------|----------|---------|
| Nginx | 低 (Docker 自动重启) | 高 (完全不可用) | < 30 秒 | 中 |
| Gitea | 低 (Docker 自动重启) | 中 (代码托管不可用) | < 1 分钟 | 低 |
| Celery Beat | 低 (Docker 自动重启) | 低 (仅定时任务) | < 1 分钟 | 低 |
| etcd | 极低 (3 节点同时故障) | 高 (无法主从切换) | 取决于宿主机恢复 | 中 (受限于单机架构) |

> **结论**: 在单机架构下，Nginx 和 etcd 是中风险 SPOF，Gitea 和 Celery Beat 是低风险 SPOF。真正消除这些 SPOF 需要多节点部署 (见 5.10 节升级路径)。当前通过 Docker 自动重启 + 监控告警 + 数据备份的组合策略将风险控制在可接受范围。

---

## 6. 安全设计

### 6.1 认证与授权

**认证方式 (JWT + Refresh Token)**:
- **Access Token**: JWT, 有效期 2 小时 (7200 秒)
  - 签发: 用户登录成功后生成
  - 存储: 前端内存存储 (不持久化)
  - 载荷: user_id, role, project_ids, exp, iat, jti
  - 签名: RS256 (非对称签名, 私钥服务器保管)
- **Refresh Token**: 随机字符串, 有效期 7 天
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
| 创建项目 | Y | - | - | - |
| 删除项目 | Y | - | - | - |
| 管理成员 | Y | Y | - | - |
| 启动流程 | Y | Y | Y | - |
| 编辑项目 | Y | Y | Y | - |
| 查看进度 | Y | Y | Y | Y |
| 发送消息 | Y | Y | Y | Y |
| 修改配置 | Y | Y | - | - |
| 查看代码 | Y | Y | Y | Y |
| 提交代码 | Y | Y | Y | - |

### 6.2 API 接口鉴权

**鉴权中间件**:
- 所有 /api/v1/* 接口强制 JWT 认证
- WebSocket 连接: 三个独立端点各自独立认证
  - `/ws/group-chat`: 连接建立后发送 `{ "type": "auth", "token": "<jwt_token>", "target": "group-chat" }` 进行群聊认证
  - `/ws/notifications`: 连接建立后发送 `{ "type": "auth", "token": "<jwt_token>", "target": "notifications" }` 进行通知认证
  - `/ws/workflow/{project_id}`: 连接建立后发送 `{ "type": "auth", "token": "<jwt_token>", "project_id": "<id>" }` 进行流程认证
  - 服务端成功响应: `{ "type": "authenticated", "user_id": <id> }`
  - 服务端失败响应: `{ "type": "auth_failed", "reason": "<error_message>" }`
  - 认证成功前，服务端仅接受 auth 消息，拒绝其他操作

> **V25 修正说明**: WebSocket 鉴权从 V24 的单一端点认证方式修正为三个独立端点各自认证，与 §3.5 和后端文档 V37 §2.16 保持一致。
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
- 数据库密码: .env 文件, 数据库 URL 格式含密码
- Ollama API Key (如需要): .env 文件
- 证书文件: /etc/ssl/ 目录, 权限 600
- 云端模型 API Key: .env 文件 (FALLBACK_OPENAI_API_KEY 等)

**访问控制**:
- .env 文件权限: 600 (仅文件所有者可读)
- 容器内通过环境变量传递, 不挂载 .env 文件明文
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
  - 编程 Agent 容器与内部服务: Docker 自定义网络, 仅白名单端口
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

### 6.6 命名 Agent 与 Gateway API 认证机制

**内部认证方案**:
- Celery Worker 调用命名 Agent 时, 通过 Gateway API 进行认证
- 认证方式: 内部 API Key (非 JWT, 简化内部通信)
- 每个命名 Agent 分配独立的内部 API Key:
  - 存储在 .env 文件中 (INTERNAL_GATEWAY_KEY_{PROFILE})
  - Gateway API 验证请求头 X-Gateway-Key
- 认证失败返回 401, 记录审计日志
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

### 6.8 网络隔离与安全域划分 (V15 新增)

**安全域划分**:

| 安全域 | 包含组件 | 访问策略 |
|--------|----------|----------|
| 公网域 | Nginx (80/443) | 接受外部 HTTP/HTTPS 请求 |
| 应用域 | FastAPI 后端、WS Worker | 仅接受 Nginx 转发请求; 访问数据域、推理域 |
| 调度域 | Celery Worker、Celery Beat、Swarm Executor | 内部通信; 访问数据域、推理域、Agent域 |
| 数据域 | PostgreSQL、Redis、Gitea 数据库 | 仅接受应用域、调度域访问; 禁止外部访问 |
| 推理域 | Ollama | 仅接受调度域、Agent域访问 |
| Agent 域 | 9 个命名 Agent 宿主进程 | 通过 localhost 访问 Gateway API; 访问推理域 |
| 蜂群域 | 编程 Agent 容器 (动态) | 独立 Docker 网络 (devflow-swarm); 仅访问 Ollama、Gitea、Swarm Executor |
| 监控域 | Prometheus、Grafana、Loki、Alertmanager | 内部采集; Grafana 可通过 Nginx 反向代理暴露 |
| 管理域 | 宿主机 (SSH)、Docker Daemon | 仅限管理员通过 SSH 访问 |

**Docker 网络设计 (V19 修订 - 多网络隔离)**:

> **安全域与网络隔离说明**: 上述 9 个安全域为逻辑划分。Docker 层面通过自定义网络实现部分物理隔离，其余隔离通过 iptables 规则在宿主机层面补充实现。

```
应用网络 (devflow-app):
  - nginx, backend, ws-worker
  - 仅允许这些服务之间通信
  - 出站: 允许访问 devflow-data, devflow-schedule, devflow-inference

调度网络 (devflow-schedule):
  - celery-worker, celery-beat, swarm-executor, swarm-executor-standby
  - 仅允许调度组件之间通信
  - 出站: 允许访问 devflow-data, devflow-inference, devflow-swarm

数据网络 (devflow-data):
  - postgres-primary, postgres-standby, postgres-gitea, pgbouncer
  - redis-master, redis-replica1, redis-replica2
  - redis-sentinel1, redis-sentinel2, redis-sentinel3
  - etcd1, etcd2, etcd3
  - 仅接受来自 devflow-app 和 devflow-schedule 的入站连接

推理网络 (devflow-inference):
  - ollama, ollama-backup
  - 仅接受来自 devflow-schedule 和命名 Agent (宿主机) 的入站连接

蜂群网络 (devflow-swarm):
  - 编程 Agent 容器 (动态创建)
  - 仅允许访问 devflow-inference 中的 Ollama
  - 出站连接被 iptables 规则限制

监控网络 (devflow-monitor):
  - prometheus, grafana, loki, alertmanager
  - 通过 Docker 网络互联策略 (--link) 采集其他网络中的服务指标

公网域:
  - nginx 端口 80/443 映射到宿主机
  - 其他服务不暴露端口到宿主机

管理域:
  - 宿主机 SSH (端口 22)
  - Docker Daemon (仅 localhost 访问)
```

**iptables 防火墙规则 (宿主机层面)**:

```bash
# 允许 SSH (管理域)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP/HTTPS (公网域 -> Nginx)
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许命名 Agent Gateway API (localhost 通信)
iptables -A INPUT -s 127.0.0.1 -p tcp --dport 8080:8088 -j ACCEPT

# 阻止外部直接访问数据库
iptables -A INPUT -p tcp --dport 5432 -s 0.0.0.0/0 -j DROP
iptables -A INPUT -p tcp --dport 6379 -s 0.0.0.0/0 -j DROP

# 阻止外部直接访问 Ollama
iptables -A INPUT -p tcp --dport 11434 -s 0.0.0.0/0 -j DROP

# 允许 Docker 容器间通信 (Docker 内部网络)
iptables -A INPUT -s 172.18.0.0/16 -j ACCEPT  # Docker 默认网段

# 默认拒绝
iptables -A INPUT -j DROP
```

**编程 Agent 容器出站过滤**:

```bash
# 创建专用 iptables 规则链
iptables -N SWARM_OUTBOUND

# 允许访问 Ollama (Docker 内网)
iptables -A SWARM_OUTBOUND -d 172.18.0.0/16 -p tcp --dport 11434 -j ACCEPT

# 允许访问 Gitea (Docker 内网)
iptables -A SWARM_OUTBOUND -d 172.18.0.0/16 -p tcp --dport 3000 -j ACCEPT

# 允许访问 Swarm Executor 回调 (Docker 内网)
iptables -A SWARM_OUTBOUND -d 172.18.0.0/16 -p tcp --dport 8090 -j ACCEPT

# 拒绝所有其他出站连接
iptables -A SWARM_OUTBOUND -j DROP

# 将规则应用到 swarm 网络
iptables -A FORWARD -o br-swarm -j SWARM_OUTBOUND
```

---

## 7. 监控与可观测性

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
- Patroni (exporter: patroni-exporter)
- Redis Sentinel (自定义 exporter)
- Swarm Executor (自定义 exporter, 主备状态)
- 命名 Agent 进程 (exporter: process-exporter, V21 新增)

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
| ollama_request_queue_wait_seconds | Histogram | Ollama 排队等待时间 (V21 新增) | 自定义 exporter |
| ollama_status | Gauge | Ollama 健康状态 (1=正常, 0=故障) | 自定义 exporter |
| ollama_primary_status | Gauge | Ollama 主实例状态 | 自定义 exporter |
| ollama_standby_active | Gauge | Ollama 备实例是否激活 | 自定义 exporter |
| fallback_active | Gauge | 降级模式是否激活 (1=激活, 0=正常) | 自定义 exporter |
| fallback_daily_cost | Gauge | 云端 API 当日累计费用 (V21 新增) | 自定义 exporter |
| swarm_executor_primary_status | Gauge | Swarm Executor 主实例状态 (V18 新增) | 自定义 exporter |
| swarm_executor_standby_status | Gauge | Swarm Executor 备实例状态 (V18 新增) | 自定义 exporter |

**数据库指标**:
| 指标名称 | 类型 | 说明 | 采集方式 |
|----------|------|------|----------|
| pg_stat_activity_count | Gauge | PostgreSQL 活跃连接数 | postgres-exporter |
| pg_replication_lag_bytes | Gauge | PostgreSQL 主从复制延迟 | postgres-exporter |
| patroni_master | Gauge | Patroni 主节点状态 | patroni-exporter |
| redis_connected_clients | Gauge | Redis 连接数 | redis-exporter |
| redis_used_memory_bytes | Gauge | Redis 内存使用量 | redis-exporter |
| redis_sentinel_master_status | Gauge | Redis Sentinel Master 状态 | 自定义 exporter |

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
| OllamaQueueBacklog (V21 新增) | 排队长度 > 10 (5min) | P2 (警告) | 邮件 |
| OllamaQueueTimeout (V21 新增) | 排队等待 > 60 秒 | P1 (紧急) | 邮件 + Webhook |
| FallbackBudgetWarning (V21 新增) | 云端 API 费用 > $40/天 (80%) | P2 (警告) | 邮件 |
| FallbackBudgetExceeded (V21 新增) | 云端 API 费用 > $50/天 (100%) | P1 (紧急) | 邮件 + Webhook |
| HighCPULoad | CPU 使用率 > 85% (5min) | P2 (警告) | 邮件 |
| HighMemoryUsage | 内存使用率 > 90% (5min) | P1 (紧急) | 邮件 + Webhook |
| DiskSpaceLow | 磁盘使用率 > 85% | P2 (警告) | 邮件 |
| DiskSpaceCritical | 磁盘使用率 > 95% | P1 (紧急) | 邮件 + Webhook |
| DatabaseConnectionHigh | 连接数 > 180/200 | P2 (警告) | 邮件 |
| RedisMemoryHigh | 内存使用 > 3.5GB/4GB | P2 (警告) | 邮件 |
| ContainerRestartLoop | 容器 10 分钟内重启 > 3 次 | P1 (紧急) | 邮件 + Webhook |
| NginxHighConnections | 活跃连接 > 3000 | P2 (警告) | 邮件 |
| PgReplicationLag | 主从复制延迟 > 100MB | P1 (紧急) | 邮件 + Webhook |
| RedisSentinelFailover | Sentinel 触发故障转移 | P1 (紧急) | 邮件 + Webhook |
| SwarmExecutorDown (V18 新增) | Swarm Executor 主实例健康检查失败 | P1 (紧急) | 邮件 + Webhook |
| SwarmExecutorFailover (V18 新增) | Swarm Executor 发生主备切换 | P2 (警告) | 邮件 |
| GPUMemoryHigh (V18 新增) | GPU 显存使用率 > 90% (43GB/48GB) | P2 (警告) | 邮件 |
| GPUOOM (V18 新增) | GPU 显存 OOM 事件 | P1 (紧急) | 邮件 + Webhook |

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

**推理层仪表盘 (V21 新增)**:
- Ollama 队列长度 (实时)
- 排队等待时间分布 (P50/P95/P99)
- 并发推理请求数 (当前/峰值)
- 降级模式状态 (本地/云端)
- 云端 API 当日费用 (实时 + 预算占比)

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
- service: backend / ws-worker / celery-worker / swarm-executor / gitea / named-agent-{profile}
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
│   ├── swarm-executor-primary (编程Agent容器管理, 主, 端口8090)
│   ├── swarm-executor-standby (编程Agent容器管理, 备, 端口8091)
│   ├── postgres-primary + patroni (主数据库)
│   ├── postgres-standby + patroni (从数据库)
│   ├── pgbouncer (连接池)
│   ├── etcd1, etcd2, etcd3 (分布式锁)
│   ├── postgres-gitea (Gitea数据库, 完全独立实例)
│   ├── redis-master, redis-replica1, redis-replica2
│   ├── redis-sentinel1, redis-sentinel2, redis-sentinel3
│   ├── gitea (代码托管)
│   ├── ollama (LLM推理引擎, 主)
│   ├── ollama-backup (LLM推理引擎, 备, 可选)
│   ├── prometheus (指标采集)
│   ├── grafana (可视化)
│   ├── loki (日志聚合)
│   └── alertmanager (告警管理)
└── 动态创建的编程 Agent 容器 (按需)
```

### 8.2 Docker Compose 配置 (核心部分)

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
      - DATABASE_URL=postgresql://devflow:***@pgbouncer:6432/devflow
      - REDIS_URL=sentinel://devflow-redis@redis-sentinel1:26379;sentinel://devflow-redis@redis-sentinel2:26379;sentinel://devflow-redis@redis-sentinel3:26379
      - GITEA_API_URL=http://gitea:3000
      - OLLAMA_API_URL=http://ollama:11434
      - OLLAMA_BACKUP_URL=http://ollama-backup:11435
      - SWARM_EXECUTOR_URL=http://nginx:80/internal/swarm-executor
      - SWARM_EXECUTOR_PRIMARY_URL=http://swarm-executor-primary:8090
      - SWARM_EXECUTOR_STANDBY_URL=http://swarm-executor-standby:8091
      - JWT_SECRET=${JWT_SECRET}
      - FALLBACK_OPENAI_API_KEY=${FALLBACK_OPENAI_API_KEY}
      - FALLBACK_DAILY_BUDGET=${FALLBACK_DAILY_BUDGET:-50}
    volumes:
      - projects_data:/DevFlow/projects
    depends_on:
      - pgbouncer
      - redis-master
      - ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  swarm-executor-primary:
    build: ./swarm-executor
    command: python main.py --port 8090 --role primary
    environment:
      - DOCKER_API_VERSION=1.43
      - MAX_CONTAINERS=4
      - MAX_PER_PROJECT=4
      - PREHEAT_COUNT=2
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - projects_data:/DevFlow/projects
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  swarm-executor-standby:
    build: ./swarm-executor
    command: python main.py --port 8091 --role standby
    environment:
      - DOCKER_API_VERSION=1.43
      - MAX_CONTAINERS=4
      - MAX_PER_PROJECT=4
      - PRIMARY_URL=http://swarm-executor-primary:8090
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - projects_data:/DevFlow/projects
    depends_on:
      - swarm-executor-primary
    restart: unless-stopped

  postgres-primary:
    image: ghcr.io/cybertec-postgresql/patroni:15
    environment:
      - PATRONI_SCOPE=devflow
      - ETCD_HOSTS=etcd1:2379,etcd2:2379,etcd3:2379
    volumes:
      - postgres_data:/home/postgres/pgdata
      - ./patroni.yml:/patroni.yml:ro
    restart: unless-stopped

  postgres-standby:
    image: ghcr.io/cybertec-postgresql/patroni:15
    environment:
      - PATRONI_SCOPE=devflow
      - ETCD_HOSTS=etcd1:2379,etcd2:2379,etcd3:2379
    volumes:
      - postgres_standby_data:/home/postgres/pgdata
      - ./patroni.yml:/patroni.yml:ro
    restart: unless-stopped

  postgres-gitea:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=gitea
      - POSTGRES_PASSWORD=${GITEA_DB_PASSWORD}
      - POSTGRES_DB=gitea
    volumes:
      - postgres_gitea_data:/var/lib/postgresql/data
    restart: unless-stopped

  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      - DATABASE_URL=postgresql://devflow:***@postgres-primary:5432/devflow
    ports:
      - "6432:6432"
    restart: unless-stopped

  redis-master:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 4gb --maxmemory-policy allkeys-lru --appendonly yes
    volumes:
      - redis_master_data:/data
    restart: unless-stopped

  redis-replica1:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --replicaof redis-master 6379 --masterauth ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_replica1_data:/data
    depends_on:
      - redis-master
    restart: unless-stopped

  redis-sentinel1:
    image: redis:7-alpine
    command: redis-sentinel /sentinel.conf
    volumes:
      - ./sentinel1.conf:/sentinel.conf:ro
    depends_on:
      - redis-master
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    command: ollama serve
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_MAX_LOADED_MODELS=1
      - OLLAMA_MAX_QUEUE=50
      - OLLAMA_NUM_PARALLEL=2
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

volumes:
  postgres_data:
  postgres_standby_data:
  postgres_gitea_data:
  redis_master_data:
  redis_replica1_data:
  redis_replica2_data:
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
# 如有备实例, 同样预热
docker exec ollama-backup ollama pull qwen2.5:72b-instruct-q4_K_M
```

### 8.4 初始化流程

1. 克隆项目代码
2. 配置 .env 文件 (数据库密码、API 密钥、JWT 密钥等)
3. 启动 Docker Compose: `docker compose up -d`
4. 等待所有容器就绪 (健康检查通过)
5. 等待 Patroni 集群选举完成 (主从关系建立)
6. 等待 Redis Sentinel 集群就绪
7. 等待 Swarm Executor 主备实例就绪
8. 初始化数据库: `docker exec backend alembic upgrade head`
9. 安装 systemd 服务并启动命名 Agent
10. 预热 Ollama 模型 (主备实例)
11. 验证所有组件健康状态
12. 配置 Prometheus 抓取目标和 Grafana 仪表盘
13. 配置 Alertmanager 告警通知渠道
14. 验证 PostgreSQL 主从复制状态
15. 验证 Redis Sentinel 故障转移能力
16. 验证 Swarm Executor 主备切换能力

---

## 9. 非功能性需求满足情况

### 9.1 性能指标

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| API 响应时间 (P95) | < 500ms | Prometheus 指标 http_request_duration_seconds |
| WebSocket 消息延迟 | < 100ms | WebSocket 消息时间戳差值 |
| Agent 任务执行超时 | 30 分钟 | Celery 任务超时配置 |
| Ollama 推理响应 (P95) | < 30s (72B Q4) | Ollama 内置指标 |
| Ollama 排队等待 (P95) | < 60s (V21 新增) | Prometheus 指标 ollama_request_queue_wait_seconds |
| 数据库查询 (P95) | < 100ms | PostgreSQL pg_stat_statements |
| 并发用户支持 | 50+ | 负载测试 (k6/Locust) |

**测试环境 (V19 修订)**:
- CPU: 64 核
- 内存: 192GB
- GPU: NVIDIA 48GB 显存
- 网络: 1Gbps 内网

### 9.2 可扩展性

**水平扩展点**:
- Celery Worker: 增加并发数或添加额外 Worker 容器
- 编程 Agent 容器: 提高全局并发上限 (需相应增加宿主资源)
- WebSocket Worker: 多个 WS Worker + Nginx 粘性会话
- Ollama: 多实例横向扩展 (见 4.10 节)

**垂直扩展点**:
- PostgreSQL: 增加 CPU/内存 ( Patroni 集群支持滚动升级)
- Ollama: 升级 GPU (更大显存支持更大模型)
- Redis: 增加 maxmemory 配置 (Sentinel 支持滚动升级)

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
- 网络隔离与安全域划分 (Docker 网络 + iptables)

**安全测试计划**:
- 由后华(安全员)执行渗透测试
- 测试范围: API 端点、文件上传、SQL 注入、XSS、CSRF
- 测试标准: OWASP Top 10
- 漏洞修复时限: 高危 24 小时内, 中危 72 小时内

### 9.5 可靠性

**可靠性保障**:
- Docker 自动重启策略 (unless-stopped)
- 健康检查与故障恢复
- 数据备份 (每日全量 + 实时 Git)
- Ollama 四级降级策略 (备实例切换/云端切换/排队限流/任务延迟)
- PostgreSQL 主从高可用 (Patroni + etcd)
- Redis 高可用 (Sentinel 哨兵模式)
- Swarm Executor 主备双实例 (V18 新增)
- 命名 Agent 宿主机高可用方案 (V18 新增)
- 任务重试机制 (3 次 + 指数退避)
- 分布式数据一致性 (本地消息表 + Saga 补偿)
- 推理层请求优先级队列 (V21 新增)

**RTO/RPO**:
- RTO (恢复时间目标): 4 小时 (数据库故障 < 30 秒自动切换)
- RPO (数据恢复点目标): 1 小时 (同步复制 RPO=0)

### 9.6 可观测性

**三大支柱**:
1. **指标 (Metrics)**: Prometheus 采集 API 延迟、错误率、队列长度、容器资源使用率、Ollama 排队延迟、云端 API 费用
2. **日志 (Logs)**: Loki 聚合所有容器和应用日志, 支持结构化查询
3. **追踪 (Traces)**: OpenTelemetry 追踪请求全链路 (API -> Celery -> Agent -> Ollama)

**Grafana 仪表盘**:
- 系统资源仪表盘 (CPU/内存/GPU/磁盘)
- API 性能仪表盘 (延迟/错误率/吞吐量)
- Agent 执行仪表盘 (任务数/成功率/平均耗时)
- 项目进度仪表盘 (活跃项目/步骤完成/QA 通过率)
- 推理层仪表盘 (队列长度/排队延迟/降级状态/云端费用, V21 新增)

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

projects (1) ----< (N) group_members (V25: member_type + member_id)
projects (1) ----< (N) group_messages (V25: sender_type=user/agent/system)

projects (1) ----< (N) audit_logs
projects (1) ----< (1) repos ----< (N) repo_branches
                                                |
                                                v
                                         pull_requests ---- commits ---- task_commits

projects (1) ----< (N) step_events (本地消息表)
```

## 附录 B: 16 步流程与 Agent 映射

| 步骤 | 步骤名称 | 执行 Agent | 执行路径 | 产出物 | QA 检验 | 代码提交 |
|------|----------|-----------|---------|--------|---------|---------|
| 1 | 项目创建 | 人类用户 | 前端 -> FastAPI -> PostgreSQL | 项目元数据 | 无需 QA | 自动创建 Gitea 仓库 |
| 2 | 需求分析 | 后兴 | Celery -> Gateway -> 后兴 -> Ollama | SRS 文档 | 后荣 | 是 |
| 3 | 架构设计 | 后旺 | Celery -> Gateway -> 后旺 -> Ollama | 架构设计文档 | 后荣 | 是 |
| 4 | 后端设计 | 后旺 | Celery -> Gateway -> 后旺 -> Ollama | 后端设计文档 | 后荣 | 是 |
| 5 | 前端设计 | 后旺 | Celery -> Gateway -> 后旺 -> Ollama | 前端设计文档 | 后荣 | 是 |
| 6 | 数据库设计 | 后旺 | Celery -> Gateway -> 后旺 -> Ollama | 数据库设计文档 | 后荣 | 是 |
| 7 | 开发环境搭建 | 后富 | Celery -> Gateway -> 后富 -> Ollama | 环境配置文件 | 后荣 | 是 |
| 8 | TDD 测试编写 | 后发(蜂群) | Celery -> Swarm Exec -> 编程Agent容器 -> Ollama | 测试用例代码 | 后荣 | 是 |
| 9 | 代码编写 | 后发(蜂群) | Celery -> Swarm Exec -> 编程Agent容器 -> Ollama | 源代码 | 后荣 | 是 |
| 10 | 单元测试 | 后达(蜂群) | Celery -> Swarm Exec -> 编程Agent容器 -> Ollama | 单元测试报告 | 后荣 | 是 |
| 11 | 集成测试 | 后达(蜂群) | Celery -> Swarm Exec -> 编程Agent容器 -> Ollama | 集成测试报告 | 后荣 | 是 |
| 12 | 安全审计 | 后华 | Celery -> Gateway -> 后华 -> Ollama | 安全审计报告 | 后荣 | 是 |
| 13 | 部署交付 | 后富 | Celery -> Gateway -> 后富 -> Ollama | 部署配置文档 | 后荣 | 是 |
| 14 | 文档整理 | 后贵 | Celery -> Gateway -> 后贵 -> Ollama | 完整项目文档 | 后荣 | 是 |
| 15 | 前端实操验证 | 后达 | Celery -> Gateway -> 后达 -> Ollama | E2E 验证报告 | 后荣 | 是 |
| 16 | 项目验收 | 海梅 + 人类 | 前端 + FastAPI | 项目验收报告 | 后荣 | 是 |

## 附录 C: V22 修正内容对照表

| 后荣检验项 | V21 状态 | V22 修正内容 |
|------------|----------|-------------|
| 【一致性问题 - UI组件库不一致】 | 1.3 节"架构层次说明"客户端层写 "Vue 3 + Vite"，未包含 Element Plus | 更新为 "Vue 3 + Vite + Element Plus"，与 2.2 节"前端技术栈"和前端设计文档完全一致 |
| 延续 V21.0 已修复项 | 推理层并发瓶颈、文档完整性、降级策略、命名 Agent 部署模型、Patroni 单机部署、云端 API 成本控制、Ollama 显存计算、文档截断、单机可用性、SPOF 分析、资源分解、资源配置、单机与多节点区分、Docker Socket 权限、后端通信路径、网络安全域、Patroni 统一、16步流程映射、Gitea DB 隔离、Celery 并发映射、Redis 数据隔离、核心数据流、PostgreSQL HA、Redis Sentinel、Ollama 多实例、分布式数据一致性、推理层扩展、容器池预热、结果回传、安全设计、监控可观测性、Swarm Executor 主备 | 保持不变 |

## 附录 D: 文档完整性自检与分文件存储建议

### D.1 完整性自检声明

本文档为独立完整的 Markdown 文件，包含 9 个核心章节 + 4 个附录。请使用以下命令验证完整性:

```bash
# 验证行数 (应 >= 2800 行)
wc -l /home/jim/DevFlow/projects/devflow/docs/devflow_ARCHITECTURE_V25.md

# 验证章节数量 (应返回 13 行: 9 个核心章节 + 4 个附录)
grep "^## " /home/jim/DevFlow/projects/devflow/docs/devflow_ARCHITECTURE_V25.md

# 验证文件完整性 (应无截断)
tail -5 /home/jim/DevFlow/projects/devflow/docs/devflow_ARCHITECTURE_V25.md
```

**期望输出**:
- `wc -l`: 2800+ 行
- `grep "^## "`: 返回 9 个核心章节 + 4 个附录共 13 个标题:
  - ## 1. 系统架构概述
  - ## 2. 技术栈选型
  - ## 3. 模块详细设计
  - ## 4. Agent 调度与资源管理
  - ## 5. 高可用与容灾方案
  - ## 6. 安全设计
  - ## 7. 监控与可观测性
  - ## 8. 部署方案
  - ## 9. 非功能性需求满足情况
  - ## 附录 A: 数据库 ER 图 (核心表)
  - ## 附录 B: 16 步流程与 Agent 映射
  - ## 附录 C: V22 修正内容对照表
  - ## 附录 D: 文档完整性自检与分文件存储建议

### D.2 分文件存储建议

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

### D.3 文档结构图

```
devflow_ARCHITECTURE_V22.md
├── 1. 系统架构概述
│   ├── 1.1 架构目标
│   ├── 1.2 整体架构图
│   ├── 1.3 架构层次说明
│   ├── 1.4 核心数据流
│   └── 1.5 16步标准流程与架构组件映射
├── 2. 技术栈选型
│   ├── 2.1 后端技术栈
│   ├── 2.2 前端技术栈
│   ├── 2.3 基础设施
│   └── 2.4 监控与可观测性技术栈
├── 3. 模块详细设计
│   ├── 3.1 项目与用户管理模块
│   ├── 3.2 16步流程调度模块
│   ├── 3.3 Agent 蜂群调度模块
│   ├── 3.4 QA 门控模块
│   ├── 3.5 群聊协作模块
│   ├── 3.6 代码库管理模块
│   ├── 3.7 通知推送模块
│   ├── 3.8 文档管理模块
│   └── 3.9 分布式数据一致性方案
├── 4. Agent 调度与资源管理
│   ├── 4.1 命名 Agent 架构
│   ├── 4.2 命名 Agent 调度流程
│   ├── 4.3 命名 Agent 资源共享
│   ├── 4.4 宿主资源容量规划 (含 GPU 显存详细规划 + 命名 Agent 资源明细, V20 修正)
│   ├── 4.5 数据库容量规划
│   ├── 4.6 编程 Agent 容器管理
│   ├── 4.7 编程 Agent 结果回传机制
│   ├── 4.8 编程 Agent 安全隔离
│   ├── 4.9 命名 Agent 进程管理
│   │   └── 4.9.1 命名 Agent 部署模型合理性说明 (V21 新增)
│   ├── 4.10 Ollama 横向扩展方案
│   ├── 4.11 编程 Agent 容器池预热策略
│   └── 4.12 推理层并发排队 SLA 分析 (V21 新增)
├── 5. 高可用与容灾方案
│   ├── 5.1 可用性目标 (V20 修正: 单机架构约束说明)
│   ├── 5.2 Docker 自动重启策略
│   ├── 5.3 健康检查与故障恢复
│   ├── 5.4 数据备份与恢复
│   ├── 5.5 Ollama 故障降级策略 (V21 修正: 排队超时60s + UI缓解 + 成本控制细化)
│   ├── 5.6 PostgreSQL 高可用方案 (V21 修正: 单机局限性说明)
│   ├── 5.7 Redis 高可用方案
│   ├── 5.8 Ollama 推理引擎高可用方案
│   ├── 5.9 Swarm Executor 高可用方案
│   ├── 5.10 命名 Agent 宿主机高可用方案
│   └── 5.11 Gitea/Celery Beat/etcd/Nginx 单点故障分析与应对策略 (V20 新增)
├── 6. 安全设计
│   ├── 6.1 认证与授权
│   ├── 6.2 API 接口鉴权
│   ├── 6.3 敏感配置管理
│   ├── 6.4 数据传输加密
│   ├── 6.5 容器间通信安全
│   ├── 6.6 命名 Agent 与 Gateway API 认证机制
│   ├── 6.7 审计日志
│   └── 6.8 网络隔离与安全域划分
├── 7. 监控与可观测性
│   ├── 7.1 监控工具选型
│   ├── 7.2 关键监控指标定义 (V21 新增: 推理层排队/云端费用指标)
│   ├── 7.3 告警阈值设定 (V21 新增: 排队/预算告警)
│   ├── 7.4 Grafana 仪表盘设计 (V21 新增: 推理层仪表盘)
│   ├── 7.5 链路追踪方案
│   └── 7.6 日志收集方案
├── 8. 部署方案
│   ├── 8.1 部署架构
│   ├── 8.2 Docker Compose 配置
│   ├── 8.3 命名 Agent 宿主机部署
│   └── 8.4 初始化流程
├── 9. 非功能性需求满足情况
│   ├── 9.1 性能指标 (V21 新增: Ollama 排队等待 P95<60s)
│   ├── 9.2 可扩展性
│   ├── 9.3 可维护性
│   ├── 9.4 安全性
│   ├── 9.5 可靠性 (V21 新增: 推理层请求优先级队列)
│   └── 9.6 可观测性 (V21 新增: 推理层仪表盘)
├── 附录 A: 数据库 ER 图
├── 附录 B: 16 步流程与 Agent 映射
├── 附录 C: V22 修正内容对照表
└── 附录 D: 文档完整性自检与分文件存储建议
    ├── D.1 完整性自检声明
    ├── D.2 分文件存储建议
    └── D.3 文档结构图
```

---

*文档结束*
