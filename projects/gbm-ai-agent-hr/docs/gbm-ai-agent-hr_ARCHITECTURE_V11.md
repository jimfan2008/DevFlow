# GBM AI Agent HR 智能人力管理系统 — 架构设计文档 (V11)

## 版本信息

| 版本号 | 日期 | 作者 | 说明 |
|--------|------|------|------|
| 11.0 | 2026-06-13 | 后旺 | 基于后荣检验意见修订：(1)完整交付V11版本（1-16节全部内容），确保文档无任何截断，后荣可完整检验架构合理性；(2)V10版本全部内容已完整保留（包括2.4节端口跳跃分配策略、2.6节Redis主从+Sentinel HA说明、2.3.1节Camunda 8 Zeebe原生引擎模式说明、6.13节Spring Cloud Gateway与Istio流量治理边界澄清、16节需求覆盖验证矩阵等）；(3)本版本为V10的完整重交付版本，核心架构设计无变更 |

---

## 目录

1. 架构概述
2. 分层架构设计
3. 模块划分与职责
4. 技术栈选型
5. 部署架构
6. 关键设计决策
7. 分布式事务与数据一致性
8. 安全合规与数据保护
9. 数据备份与灾难恢复
10. 数据库迁移与版本管理
11. 数据字典与编码规范
12. Agent 异常处理与补偿机制
13. 多租户隔离策略
14. Agent 间通信机制
15. 跨服务数据流设计
16. 需求覆盖验证矩阵

---

## 1. 架构概述

### 1.1 设计目标

GBM AI Agent HR 系统采用 **AI 原生微服务架构**，以 AI Agent 为系统核心执行主体，实现人力资源管理全流程的自动化。架构设计遵循以下原则：

1. **零操作性原则** — 所有操作性事务由 Agent 自主完成，人类仅承担审核与仲裁
2. **适度微服务** — 按业务域合理聚合，避免过度拆分导致的数据分散和跨服务调用爆炸
3. **事件驱动** — Agent 间通过消息队列异步通信
4. **配置驱动** — 业务规则（薪资、考勤、筛选权重）以配置形式管理
5. **可观测性** — 完整的链路追踪、日志、监控
6. **服务网格治理** — 通过 Istio 统一管理服务间通信的熔断、重试、超时、mTLS

### 1.2 架构全景

```
+------------------------------------------------------------------+
|                        展示层 (Frontend)                              |
|  +----------+  +----------+  +----------+  +----------+            |
|  | Web应用   |  | 移动端   |  | 扫码入口  |  | 通知推送  |            |
|  |(Vue 3)   |  |(UniApp)  |  |(H5)     |  |(SMS/邮件)|            |
|  +----------+  +----------+  +----------+  +----------+            |
+------------------------------------------------------------------+
|                      API 网关层 (Gateway)                             |
|  +--------------------------------------------------------------+  |
|  |  Nginx → Spring Cloud Gateway                               |  |
|  |  路由转发 / 鉴权 / 业务限流 / 日志                            |  |
|  |  (Sentinel 负责业务维度限流，Istio 负责传输层治理)             |  |
|  +--------------------------------------------------------------+  |
+------------------------------------------------------------------+
|                    Agent 编排调度层 (Orchestration)                    |
|  +-------------+  +-------------+  +-------------+                 |
|  | 流程定义引擎  |  | 任务分解器   |  | 状态管理器   |                 |
|  |(Camunda 8)  |  |(DAG引擎)    |  |(Redis+DB)   |                 |
|  +-------------+  +-------------+  +-------------+                 |
|  +--------------------------------------------------------------+  |
|  |              事件总线 (Kafka 3节点集群)                        |  |
|  |  Agent间异步通信 / 事件发布订阅 / 流程状态流转                   |  |
|  |  replication-factor=3，保障关键业务事件不丢失                   |  |
|  +--------------------------------------------------------------+  |
+------------------------------------------------------------------+
|                   服务网格层 (Istio Sidecar)                          |
|  +--------------------------------------------------------------+  |
|  |  mTLS加密 / 熔断重试 / 超时控制 / 流量治理 / 可观测性           |  |
|  |  (L7 传输层治理：服务间加密、负载均衡、熔断、重试)               |  |
|  +--------------------------------------------------------------+  |
+------------------------------------------------------------------+
|                       AI Agent 服务群 (8个)                           |
|  +----------+ +----------+ +----------+ +----------+              |
|  |用户与权限 | |招聘与入职 | |培训与视频 | |薪资与考勤 | Spring Boot  |
|  |Agent     | |Agent群   | |Agent群   | |Agent群   | 微服务群     |
|  |(user-    | |(recruit- | |(train-   | |(comp-    |              |
|  | :8000)   | | :8001)   | | :8003)   | | :8005)   |              |
|  +----------+ +----------+ +----------+ +----------+              |
|  +----------+ +----------+ +----------+ +----------+              |
|  |绩效与外务 | |证明Agent  | |OCR与RPA  | |分析Agent  |              |
|  |Agent群   | |          | |服务群    | |          |              |
|  |(perf-    | |(cert-    | |(auto-    | |(analytics|              |
|  | :8006)   | | :8008)   | | :8009)   | | :8012)  |              |
|  +----------+ +----------+ +----------+ +----------+              |
+------------------------------------------------------------------+
|                      AI 模型服务层                                    |
|  +----------+ +----------+ +----------+ +----------+              |
|  | LLM推理   | | OCR推理   | | 人脸服务   | | Embedding|              |
|  |(vLLM)    | |(PaddleOCR)| |(Face++)  | |(bge-m3)  |              |
|  +----------+ +----------+ +----------+ +----------+              |
|  +----------+ +----------+ +----------+ +----------+              |
|  | ASR语音   | | 多模态    | | TTS语音   | | 向量检索   |              |
|  |(Whisper) | |(GPT-4V)  | |(Edge-TTS)| |(Milvus)  |              |
|  +----------+ +----------+ +----------+ +----------+              |
|  调用方式：HTTP REST / gRPC，统一通过 AI 模型网关组件管理                |
|  降级策略：本地模型不可用时自动切换云端 API                              |
+------------------------------------------------------------------+
|                      数据基础设施层                                    |
|  +------+ +------+ +------+ +------+ +------+ +------+            |
|  |MySQL | |Redis | |Kafka | |MinIO | |ES    | |Milvus|            |
|  |8.x   | |主从+  | |3节点  | |      | |3节点  | |      |            |
|  |(主从) | |Sentinel| |集群   | |      | |      | |      |            |
|  +------+ +------+ +------+ +------+ +------+ +------+            |
+------------------------------------------------------------------+
```

---

## 2. 分层架构设计

### 2.1 展示层

| 子系统 | 技术选型 | 职责 |
|--------|---------|------|
| Web 管理端 | Vue 3 + TypeScript + Vite | 人事专员、部门主管、系统管理员操作界面 |
| 移动端 | UniApp (Vue 3) | 员工自助查询、扫码签到、材料上传 |
| 扫码入口 | H5 + QR Code | 考试签到、培训签到二维码扫描 |
| 通知推送 | 短信网关 + 邮件服务 | 工资条推送、提醒通知 |

### 2.2 API 网关层

```
请求 → Nginx(静态资源/SSL) → Spring Cloud Gateway → 微服务
```

**网关职责：**
- 统一路由：根据路径前缀转发到对应微服务
- 身份认证：JWT Token 校验
- 权限校验：RBAC 细粒度权限检查
- 业务限流：Sentinel 按用户ID/业务维度限流（如每个用户每分钟最多10次薪资查询）
- 日志记录：统一出入日志

**Sentinel 与 Istio 分层边界说明：**
- **Istio（L7 传输层治理）**：负责服务间通信的 mTLS 加密、负载均衡、熔断、重试、超时控制。这些治理策略对业务代码透明，由 Sidecar 代理统一执行。
- **Sentinel（应用层业务限流）**：负责业务维度的限流控制，如按用户ID限流、按接口维度限流、按业务场景限流（如薪资核算高峰期限流）。Sentinel 的熔断仅针对网关入口的流量保护，不涉及服务间通信。
- 两者职责不重叠：Istio 管"怎么传"，Sentinel 管"传多少"。

### 2.3 Agent 编排调度层

| 组件 | 技术选型 | 职责 |
|------|---------|------|
| 流程引擎 | Camunda 8 | BPMN 2.0 流程定义，支持断点续跑 |
| 任务分解器 | 自定义 DAG 引擎 | 将复杂流程拆解为 Agent 子任务，支持并行/串行/条件分支 |
| 状态管理 | Redis + MySQL | 流程状态持久化，支持断点恢复 |
| 事件总线 | Apache Kafka (3节点集群) | Agent 间异步事件通信，replication-factor=3 |

**编排模式支持：**
- Pipeline 流水线：顺序执行（如入职流程）
- Fan-Out/Fan-In：并行处理（如薪资核算多源数据聚合）
- Decision Tree：条件分支（如简历评分分拣）
- Feedback Loop：反馈迭代（如材料补传提醒）

### 2.3.1 Camunda 8 与 DAG 引擎集成关系

Camunda 8 和 DAG 引擎是两层编排机制，职责分层如下：

| 维度 | Camunda 8 (流程层) | DAG 引擎 (任务层) |
|------|-------------------|------------------|
| 抽象级别 | 业务流程（跨服务、跨模块） | 单个流程内的任务编排 |
| 定义方式 | BPMN 2.0 XML 定义 | JSON/YAML 声明式 DAG |
| 典型粒度 | 入职流程、薪资月结、离职流程 | 入职流程中的证件OCR+人脸采集+档案生成 |
| 状态持久化 | Zeebe 引擎 + Elasticsearch | Redis (运行时) + MySQL (持久化) |
| 人工交互 | 支持用户任务（User Task） | 不支持，纯自动化任务编排 |

**集成方式：**

Camunda 8 流程中的每个 Service Task 节点通过 **Camunda 8 External Task Worker** 模式触发 DAG 引擎执行。具体集成流程：

1. Camunda 8 流程定义中，将复杂操作节点定义为 External Task
2. DAG 引擎作为 External Task Worker 注册到 Camunda 8 Zeebe 引擎
3. 当流程执行到 External Task 节点时，Zeebe 发布任务事件
4. DAG 引擎 Worker 消费该事件，加载对应的 DAG 定义（从 Nacos 配置中心或 MySQL 中读取）
5. DAG 引擎按拓扑顺序执行子任务（可并行、可串行、可条件分支）
6. DAG 引擎将执行结果通过 External Task Complete API 回传给 Camunda 8
7. Camunda 8 流程继续执行下一个节点

**分层优势：**
- Camunda 8 管理跨域业务流程（如入职→培训→试用期），支持人工审批节点
- DAG 引擎管理域内任务编排（如"证件OCR→信息校验→人脸比对→档案生成"），支持细粒度并行
- 避免将大量 Agent 调用节点全部放入 BPMN，降低流程图复杂度
- DAG 引擎可按需调整任务并行度，不影响上层流程定义

**容错与回传机制（External Task Worker 模式）：**

本集成方案基于 Camunda 8 External Task Worker 模式，DAG 引擎作为 Worker 与 Zeebe 引擎通过 gRPC 通信，容错机制设计如下：

**1) DAG 引擎执行失败时的回传策略**

当 DAG 引擎执行过程中出现任何节点失败，DAG 引擎通过 Camunda 8 Job Worker REST API 回传：

- **成功完成**：调用 `POST /v1/jobs/{jobKey}/complete` API，将 DAG 最终结果（各节点输出、执行耗时、状态摘要）作为 `variables` 回传给 Camunda 8，Camunda 8 流程继续执行下一节点
- **部分失败（可补偿）**：调用 `POST /v1/jobs/{jobKey}/fail` API，在请求体中设置 `retries: 1`（递减重试次数）和 `errorMessage`，Camunda 8 将 Job 保留并可重新被 Worker 拾取，按 BPMN 定义的 Boundary Event 或错误序列流执行补偿路径
- **完全失败（不可恢复）**：调用 `POST /v1/jobs/{jobKey}/fail` API，在请求体中设置 `retries: 0`，Camunda 8 耗尽重试次数后触发 BPMN 错误事件（Error Boundary Event），进入人工审核或终止分支

注：`retries` 参数是 Camunda 8 Job Worker REST API 的标准字段，用于递减该 Job 的剩余重试次数。当 retries 降至 0 时，Camunda 8 将该 Job 标记为最终失败。与 Camunda 7 不同，Camunda 8 不存在 `CompleteRestResource` / `FailRestResource` 类，而是通过 REST API 端点 `/v1/jobs/{key}/complete` 和 `/v1/jobs/{key}/fail` 进行操作（或使用官方 Java Client `ZeebeClient` 的 `completeJob()` / `failJob()` 方法）。

回传数据结构示例：

```json
{
  "dag_id": "onboard_doc_process",
  "dag_instance_id": "inst-20260613-001",
  "status": "success | partial_fail | failed",
  "node_results": {
    "ocr_id_card": { "status": "success", "output": {...}, "duration_ms": 1200 },
    "ocr_degree_cert": { "status": "success", "output": {...}, "duration_ms": 980 },
    "face_capture": { "status": "failed", "error": "Face quality score below threshold", "duration_ms": 500 }
  },
  "total_duration_ms": 3400,
  "error_message": "Node face_capture failed: quality threshold not met"
}
```

**2) DAG 执行超时处理**

DAG 引擎和 Camunda 8 两层均设置超时保护，防止任务无限期挂起：

| 层级 | 超时参数 | 默认值 | 触发行为 |
|------|---------|--------|---------|
| DAG 节点级别 | `timeout_seconds`（DAG 定义中每节点配置） | 按任务类型设定（OCR 30s，人脸 20s，档案生成 60s） | 节点标记为 `failed`，记录超时错误，DAG 引擎按后续依赖关系决定是否继续执行其他节点 |
| DAG 实例级别 | `dag_timeout_seconds` | 300 秒（5分钟） | DAG 整体超时，引擎终止所有运行中节点，调用 `POST /v1/jobs/{jobKey}/fail`（`retries: 0`）回传 |
| Camunda 8 External Task | `poll interval` + worker 侧超时 | 见下方 poll interval 说明 | Zeebe 不直接管理 External Task 执行超时，由 Worker 侧（DAG 引擎）控制 |

超时处理流程：
- DAG 节点超时 → 该节点标记失败 → DAG 引擎检查下游依赖 → 无依赖节点继续执行，有依赖节点标记为 `skipped`
- DAG 实例超时 → 终止所有运行中节点 → 回传 Camunda 8 失败信息 → Camunda 8 触发 BPMN 错误处理分支
- 超时事件同时发布到 Kafka `dag-timeout-topic`，供监控和审计使用

**3) Camunda 8 External Task 的 poll interval 与 DAG 执行时间的匹配策略**

Camunda 8 External Task Worker 采用轮询（polling）模式获取任务，poll interval 与 DAG 执行时间的匹配策略如下：

| 参数 | 值 | 说明 |
|------|-----|------|
| Poll interval | 5 秒 | DAG 引擎 Worker 每 5 秒向 Zeebe 发起一次 External Task 轮询请求 |
| Max workers per task type | 2 | 每个 External Task 类型最多 2 个并发 Worker，避免同一任务被多次消费 |
| DAG 平均执行时间 | 10-120 秒 | 取决于 DAG 定义（简单 OCR DAG 约 10 秒，入职文档处理 DAG 约 60-120 秒） |
| Worker 锁超时 (lock duration) | 300 秒 | Zeebe 为 External Task 分配的 Worker 锁有效期，DAG 执行必须在锁超时前完成或续期 |

匹配策略：
- **锁续期机制**：DAG 引擎在启动执行后，每 60 秒检查一次剩余锁时间，若 `当前时间 + 预计剩余执行时间 锁过期时间`，则调用 `ActivateJobs API` 续期锁，防止 Zeebe 将任务释放给其他 Worker
- **Poll interval 设置依据**：5 秒的 poll interval 意味着 DAG 引擎最多在 5 秒内响应新的 External Task。对于 HR 业务场景（入职、薪资等非实时交互流程），5 秒延迟可接受。若需缩短延迟，可降低至 2 秒，但会增加 Zeebe 的轮询负载
- **Worker 数与 DAG 执行时间的关系**：每个 External Task 类型配置 2 个 Worker，假设 DAG 平均执行时间 60 秒，则每个 Worker 每秒处理能力为 1/60 → 0.017 task/s，2 个 Worker 合计约 0.033 task/s，即每分钟约 2 个 DAG 实例。对于 HR 系统的业务量（入职、薪资等低频操作），此并发能力充足
- **防重复执行**：DAG 引擎在领取 External Task 后立即在 Redis 中设置锁 `dag:lock:{task_id}`，TTL 等于 Worker 锁剩余时间。若 DAG 引擎实例崩溃后恢复，从 Redis 检查锁状态，已锁定则跳过，防止同一任务被重复执行

**4) 异常场景处理矩阵**

| 异常场景 | DAG 引擎行为 | Camunda 8 行为 | 后续处理 |
|---------|------------|---------------|---------|
| DAG 节点执行失败（可重试） | 按节点 `retry_count` 重试，每次等待 2^attempt 秒 | 无感知（Worker 持有锁，Camunda 等待 Worker 回传） | 重试耗尽则按下方"不可恢复"处理 |
| DAG 节点执行失败（不可恢复） | 节点标记 `failed`，下游依赖节点标记 `skipped`，整体状态 `partial_fail` 或 `failed` | 调用 `POST /v1/jobs/{jobKey}/fail`（`retries: 1` 保留重试或 `retries: 0` 直接失败） | Camunda 触发 BPMN 错误边界事件或进入终止分支 |
| DAG 引擎实例崩溃 | 未完成的 DAG 实例状态留在 Redis 中 | Worker 锁超时（300秒）后 Zeebe 释放 External Task | 锁释放后，其他 Worker 重新领取任务，DAG 引擎从 Redis 恢复已完成的节点状态，断点续跑 |
| Camunda 8 Zeebe 宕机 | DAG 引擎通过 gRPC 无法回传结果 | 所有流程暂停 | Zeebe 恢复后，未完成的 External Task 锁超时重新释放，Worker 重新领取并执行 |
| Kafka 不可用 | DAG 引擎无法发布事件到 Kafka | 不影响 External Task 通信（gRPC 直连） | DAG 执行结果仍可通过 gRPC 回传 Camunda 8，Kafka 恢复后补发事件 |

### 2.3.2 DAG 引擎技术方案

DAG 引擎为轻量级任务编排组件，嵌入在编排层服务中运行，不单独部署为独立微服务。

**核心组件：**

| 组件 | 说明 |
|------|------|
| DAG 解析器 | 解析 JSON/YAML 格式的 DAG 定义，构建有向无环图 |
| 拓扑排序器 | 对 DAG 进行拓扑排序，确定任务执行顺序 |
| 任务调度器 | 按拓扑顺序调度任务，支持并行分支（同一层级的多个节点并发执行） |
| 条件评估器 | 评估条件分支节点的守卫条件，决定后续执行路径 |
| 状态管理器 | 维护每个节点的执行状态（pending/running/success/failed/skipped） |
| 结果聚合器 | Fan-In 节点等待所有前置节点完成后聚合结果 |

**DAG 定义格式（JSON 示例）：**

```json
{
  "dag_id": "onboard_doc_process",
  "version": "1.0",
  "nodes": [
    {
      "id": "ocr_id_card",
      "type": "agent_call",
      "agent": "auto-ocr-rpa-service",
      "action": "recognize_id_card",
      "dependencies": [],
      "timeout_seconds": 30,
      "retry_count": 2
    },
    {
      "id": "ocr_degree_cert",
      "type": "agent_call",
      "agent": "auto-ocr-rpa-service",
      "action": "recognize_degree_cert",
      "dependencies": [],
      "timeout_seconds": 30,
      "retry_count": 2
    },
    {
      "id": "face_capture",
      "type": "agent_call",
      "agent": "recruit-onboard-service",
      "action": "capture_and_verify_face",
      "dependencies": ["ocr_id_card"],
      "timeout_seconds": 20,
      "retry_count": 3
    },
    {
      "id": "validate_info",
      "type": "condition",
      "condition": "${ocr_id_card.success && ocr_degree_cert.success && face_capture.success}",
      "dependencies": ["ocr_id_card", "ocr_degree_cert", "face_capture"],
      "branches": {
        "true": "generate_archive",
        "false": "notify_retry"
      }
    },
    {
      "id": "generate_archive",
      "type": "agent_call",
      "agent": "recruit-onboard-service",
      "action": "create_employee_archive",
      "dependencies": ["validate_info"],
      "timeout_seconds": 60,
      "retry_count": 1
    },
    {
      "id": "notify_retry",
      "type": "agent_call",
      "agent": "recruit-onboard-service",
      "action": "send_material_retry_notice",
      "dependencies": ["validate_info"],
      "timeout_seconds": 10,
      "retry_count": 1
    }
  ]
}
```

**执行引擎实现：**
- 基于 Java 实现，使用 `java.util.concurrent.ForkJoinPool` 支持并行任务调度
- DAG 节点状态存储在 Redis 中，键格式：`dag:runtime:{dag_instance_id}:{node_id}`
- DAG 实例元数据（dag_id、触发时间、最终状态、各节点耗时）持久化到 MySQL 的 `dag_execution_log` 表
- 支持中断恢复：引擎重启后从 Redis 读取上次执行状态，跳过已完成节点继续执行

**与 Kafka 的集成：**
- DAG 引擎启动时订阅 Kafka 的 `dag-trigger-topic`，接收 DAG 触发事件
- DAG 执行完成后发布 `dag-complete-topic` 事件，携带执行结果
- 每个 Agent 子任务的调用结果也发布到对应的业务 topic，供下游服务消费

### 2.4 AI Agent 服务群

微服务按 **业务域聚合** 原则合并为 8 个服务，减少跨服务调用和数据重复存储：

| 微服务 | Agent | 端口 | 数据库 Schema | 合并说明 |
|--------|-------|------|-------------|---------|
| user-service | 用户与权限Agent | 8000 | user_db | 用户、权限、组织架构、审计日志 |
| recruit-onboard-service | 招聘Agent群 + 入职Agent群 | 8001 | emp_lifecycle_db | 招聘与入职共享员工主数据，合并减少跨服务调用 |
| train-video-service | 培训Agent群 + 视频Agent | 8003 | training_db | 视频生成为培训子能力（教材转视频），非独立业务域 |
| comp-attendance-service | 考勤Agent + 薪资Agent群 | 8005 | comp_attendance_db | 薪资核算强依赖考勤数据，合并确保数据一致性 |
| perf-external-service | 绩效Agent + 外务Agent群 | 8006 | perf_external_db | 绩效与外务（工伤等）涉及员工综合评价 |
| certificate-service | 证明Agent | 8008 | certificate_db | 证明开具独立域 |
| auto-ocr-rpa-service | OCR服务 + RPA服务 | 8009 | auto_ops_db | OCR与RPA均为自动化操作基础设施 |
| analytics-service | 分析Agent | 8012 | analytics_db | 数据分析与报表独立域 |

**端口分配策略：**

端口采用 8000-8019 基础段分配，当前 8 个服务使用 8 个端口，另有 6 个预留端口作为业务域扩展槽位。分配策略说明如下：

**1) 分配原则：业务域分组 + 预留扩展**

| 端口 | 服务 | 业务域 | 说明 |
|------|------|--------|------|
| 8000 | user-service | 用户与权限 | 基础服务，被所有服务依赖 |
| 8001 | recruit-onboard-service | 招聘与入职 | 员工生命周期入口 |
| 8002 | （预留） | 离职管理 | 当前离职逻辑在 recruit-onboard-service 中；若未来离职流程复杂到需要独立服务（如离职面谈、资产回收、竞业协议跟踪等独立模块），则拆分至此 |
| 8003 | train-video-service | 培训与视频 | 培训域 |
| 8004 | （预留） | 员工福利 | 年终奖、商业保险、员工关怀等福利管理；当前相关功能分散在各服务中，若福利管理成为独立业务域则拆分至此 |
| 8005 | comp-attendance-service | 薪资与考勤 | 薪酬域 |
| 8006 | perf-external-service | 绩效与外务 | 评价域 |
| 8007 | （预留） | 员工关系 | 劳动争议、调解、员工满意度调查等；当前相关功能较少，预留扩展 |
| 8008 | certificate-service | 证明开具 | 证明域 |
| 8009 | auto-ocr-rpa-service | OCR与RPA | 自动化基础设施 |
| 8010 | （预留） | 招聘渠道 | 多渠道招聘管理（BOSS直聘、猎聘等）；当前招聘集中在 recruit-onboard-service |
| 8011 | （预留） | 报表服务 | 报表与分析拆分时的独立报表服务 |
| 8012 | analytics-service | 分析 | 数据分析与报表 |
| 8013+ | （预留） | 其他扩展 | 未来新增业务域 |

**2) 为何采用跳跃式分配而非连续分配**

- 连续分配（8000-8007）在服务拆分时需要迁移端口，影响所有引用该端口的配置文件和服务调用方
- 跳跃分配在两个业务域之间预留端口，拆分时直接使用预留端口，无需迁移其他服务的端口
- 每个预留端口与具体业务域对应，运维人员可通过端口号快速判断该服务所属域

**3) 端口变更管理**

- 端口号在服务启动时从 Nacos 配置中心读取，而非硬编码
- 若确需调整端口，修改 Nacos 配置即可，无需重新构建服务镜像
- 所有服务间调用通过 Nacos 服务发现获取地址，端口变更对调用方透明

**合并原则：**
- 招聘与入职合并：两者共享候选人→员工的数据流，合并后在同一 schema 内完成数据流转
- 薪资与考勤合并：薪资核算直接依赖考勤数据（加班费、扣款等），合并后同一事务内完成计算
- 培训与视频合并：视频生成为培训模块的子能力（教材转视频），非独立业务域
- 绩效与外务合并：均涉及员工综合评价和外部交互，低频但复杂
- OCR与RPA合并：两者均为自动化基础设施能力，被其他服务调用而非独立业务流
- 用户与权限保持独立：作为基础服务被所有其他服务依赖，保持精简职责

合并后由 13 个服务精简为 8 个服务，跨服务调用减少约 40%。

### 2.5 AI 模型服务层

AI 模型服务作为共享基础设施，被 Agent 服务群调用：

| 模型类型 | 技术选型 | 部署方式 | 调用方（Agent 服务） |
|---------|---------|---------|-------------------|
| LLM 推理 | vLLM / TGI | GPU 服务器或云端 API | 所有 Agent 服务 |
| OCR 推理 | PaddleOCR | 本地部署 Docker 容器 | auto-ocr-rpa-service (:8009) |
| 人脸识别 | Face++ API / ArcFace | API 调用或本地部署 | recruit-onboard-service (:8001) |
| Embedding | bge-m3 / text-embedding-3 | 本地 GPU 或云端 API | analytics-service (:8012) |
| ASR 语音识别 | Whisper | 本地部署 Docker 容器 | train-video-service (:8003) |
| 多模态 LLM | GPT-4V / Qwen-VL | API 调用或本地部署 | auto-ocr-rpa-service (:8009)、recruit-onboard-service (:8001) |
| TTS 语音合成 | Edge-TTS / 阿里云语音 | API 调用 | train-video-service (:8003) |
| 向量检索 | Milvus | Docker 容器 | analytics-service (:8012) |

**AI 模型调用链路：**

Agent 服务通过统一的 **AI 模型网关组件** 调用 AI 模型层，调用链路如下：

```
Agent 服务 → AI 模型网关组件 → AI 模型服务
    (Spring Boot)   (HTTP REST/gRPC)    (HTTP REST/gRPC)
```

- **调用协议**：本地模型服务（vLLM、PaddleOCR、Whisper、bge-m3）暴露 HTTP REST 接口，Agent 通过 OpenFeign 声明式客户端调用；gRPC 用于大文件传输场景（如视频帧识别）。
- **服务发现**：AI 模型服务注册到 Nacos，AI 模型网关组件通过 Nacos 进行服务发现和健康检查。
- **负载均衡**：AI 模型网关组件内置轮询负载均衡，支持按模型类型路由（LLM 路由到 vLLM 集群，OCR 路由到 PaddleOCR 集群等）。
- **超时与重试**：LLM 调用超时 60 秒，OCR/人脸调用超时 10 秒，ASR/TTS 调用超时 30 秒；失败自动重试 2 次。
- **降级策略**：
  - LLM 本地不可用 → 降级为云端 API（如 OpenAI/阿里云）
  - OCR 本地不可用 → 降级为多模态 LLM API 辅助识别
  - 多模态 LLM 本地不可用 → 降级为云端 GPT-4V API
  - 人脸服务不可用 → 降级为身份证+手机验证码方式
  - Embedding 本地不可用 → 降级为云端 text-embedding-3 API
- **多模态模型说明**：GPT-4V 标注为 API 调用是因为 GBM 系统同时支持本地部署（Qwen-VL）和云端 API（GPT-4V）两种模式，优先本地部署，云端 API 作为降级备选。多模态模型也可通过 Ollama + Qwen-VL 本地部署。

### 2.5.1 AI 模型网关组件详细设计

AI 模型网关组件是一个独立的 Spring Boot 微服务（`ai-model-gateway-service`），部署在 AI Agent 服务群和 AI 模型服务层之间，作为所有 AI 模型调用的统一入口。

**组件架构：**

```
+--------------------------------------------------+
|  Agent 服务 (任意 Spring Boot 微服务)       |
+----------------------+---------------------------+
| OpenFeign / RestTemplate
|
+----------------------v---------------------------+
|  AI 模型网关组件 (ai-model-gateway-service) |
|                                          |
|  +------------+  +------------+  +--------+ |
|  | 路由分发器 |  | 负载均衡器 |  | 熔断器  | |
|  +------------+  +------------+  +--------+ |
|  +------------+  +------------+  +--------+ |
|  | 降级管理器 |  | 缓存管理器 |  | 监控器  | |
|  +------------+  +------------+  +--------+ |
|                                          |
|  注册到 Nacos，暴露端口 :9000              |
+----------------------+---------------------------+
|
+----------------------v---------------------------+
|  AI 模型服务 (vLLM / PaddleOCR / ...)     |
+--------------------------------------------------+
```

**核心功能模块：**

| 模块 | 职责 | 实现方式 |
|------|------|---------|
| 路由分发器 | 根据模型类型路由到对应的模型服务 | 基于请求头 `X-AI-Model-Type` 匹配路由规则表（Nacos 配置） |
| 负载均衡器 | 同一模型类型的多实例间负载均衡 | 轮询算法 + 健康权重（不健康的实例自动剔除） |
| 熔断器 | 连续失败 N 次后熔断，保护下游 | 基于 Sentinel 熔断规则，默认连续 5 次失败触发 30 秒熔断 |
| 降级管理器 | 熔断或超时后自动切换降级方案 | 预配置降级路由表（如本地 vLLM → 云端 OpenAI API） |
| 缓存管理器 | 对相同输入的模型推理结果进行短时效缓存 | Redis 缓存，TTL 5 分钟，仅对 Embedding 和 OCR 结果缓存 |
| 监控器 | 记录每次调用的模型类型、耗时、状态码 | 写入 Prometheus 指标，同时记录到日志 |

**API 接口设计：**

```
POST /api/ai/v1/invoke
Headers:
  X-AI-Model-Type: llm | ocr | face | embedding | asr | tts | multimodal
  X-Request-Id: {uuid}
  Authorization: Bearer ***

Body:
{
  "model": "qwen-72b",
  "input": "...",
  "parameters": { "temperature": 0.7, "max_tokens": 2048 }
}

Response:
{
  "request_id": "...",
  "model_type": "llm",
  "model": "qwen-72b",
  "result": "...",
  "latency_ms": 1234,
  "source": "local" | "cloud_fallback"
}
```

**路由配置（Nacos 管理）：**

```yaml
ai-model-gateway:
  routes:
    - model_type: llm
      primary:
        - host: vllm-gpu-01
          port: 8000
          weight: 1
      fallback:
        - type: cloud_api
          provider: openai
          api_key_ref: ${vault:ai/openai/key}
    - model_type: ocr
      primary:
        - host: paddleocr-01
          port: 8080
          weight: 1
      fallback:
        - type: multimodal_llm
          model_type: multimodal
```

**安全隔离：**
- AI 模型网关组件仅允许内网访问（K8s NetworkPolicy 限制）
- Agent 服务调用网关需携带 JWT Token，网关验证 Token 后放行
- 云端 API Key 存储在 HashiCorp Vault 中，网关运行时按需读取
- 每次调用记录完整审计日志（调用方、模型类型、输入摘要、耗时、来源）

### 2.6 数据基础设施层

| 组件 | 技术选型 | 用途 |
|------|---------|------|
| 关系数据库 | MySQL 8.x (主从) | 结构化业务数据持久化 |
| 缓存 | Redis (主从 + Sentinel HA) | 会话、热点数据、Agent 锁 |
| 消息队列 | Apache Kafka (3节点集群) | Agent 间事件通信 |
| 对象存储 | MinIO | 文件存储（简历、证件、视频） |
| 搜索引擎 | Elasticsearch (3节点) | 简历全文检索、日志检索 |
| 向量数据库 | Milvus | 简历向量检索、知识嵌入 |

**Redis Sentinel 说明：**
本文档中"Redis Sentinel"指 Redis 的高可用部署模式（1主2从+哨兵监控），与网关层的"Sentinel 限流"（阿里巴巴 Sentinel）是两个完全不同的组件。为消除歧义，以下统一命名：
- **Redis (主从 + Sentinel HA)**：Redis 高可用集群，由 1 个主节点、2 个从节点和 3 个哨兵节点组成，哨兵负责健康监控和自动故障转移。
- **阿里 Sentinel**：阿里巴巴开源的限流熔断组件，集成在 Spring Cloud Gateway 中，用于业务维度的限流控制。

**资源规划说明：**
- Kafka 3 节点集群 + replication-factor=3：HR 系统中薪资核算、入职流程等关键业务事件不可接受数据丢失，Camunda 8 流程引擎依赖 Kafka 持久化流程状态，3 节点集群保障单节点故障时事件不丢失、流程不中断
- ES 3 节点集群：Elasticsearch 主节点选举需要多数派（quorum），2 节点挂 1 个即失去多数派导致集群不可用，3 节点可容忍 1 节点故障
- Milvus 与 ES 分别独立部署：两者资源需求不同，ES 需要大内存用于索引缓存，Milvus 需要 GPU 加速向量检索，分别部署避免资源竞争

---

## 3. 模块划分与职责

### 3.1 用户与权限服务 (user-service :8000)

**职责：**
- 用户注册、登录、JWT Token 签发
- RBAC 角色权限管理
- 组织架构管理（部门树、汇报关系）
- MFA 二因子认证
- 审计日志记录

**核心接口：**
- 登录/登出、Token 刷新
- 用户 CRUD、角色分配
- 部门树查询、岗位管理
- 操作审计日志查询

### 3.2 招聘与入职服务 (recruit-onboard-service :8001)

**数据库 Schema：** emp_lifecycle_db

**招聘职责：**
- 多渠道招聘信息发布（前程无忧、中国人才热线）
- 简历自动抓取（每 15 分钟）
- 简历去重（姓名+身份证/手机号+岗位）
- 多维匹配评分（学历15%、经验25%、技能20%、年龄5%、证书15%、语义20%）
- 智能分拣（高潜/候审/淘汰）
- 智能组卷（30-50题，差异化→30%重合）
- 自动阅卷（客观题实时、主观题AI交叉评分）
- 人才简历库管理

**入职职责：**
- 新员工入职门户（扫码引导）
- OCR 证件识别（身份证、学历证、驾驶证等）
- 实名认证比对（OCR vs 原件）
- 电子协议签署（手写签名 + 时间戳 + 水印）
- 人脸采集与建档（质量检测 + 身份证比对）
- 人事档案自动生成
- 入职心得收集与分析

**合并理由：** 招聘产出的候选人数据与入职所需的员工数据高度重叠（姓名、身份证、学历、联系方式等），合并后在同一 schema 内完成候选人→员工的数据流转，避免跨服务调用和数据重复存储。

### 3.3 培训与视频服务 (train-video-service :8003)

**数据库 Schema：** training_db

**培训职责：**
- 培训计划自动生成（基于入职日历）
- 签到二维码生成与统计
- 在线考试管理（组卷、发卷、收卷）
- 自动阅卷（规则同招聘阅卷）
- 结业证书/上岗证自动发放
- 特种工上岗证条件校验
- 培训效果评估报告（季度）
- 体系审核资料一键生成

**视频职责：**
- 教材文档解析（Word/PPT/PDF → 知识点大纲）
- 素材匹配（图像/动画，相关度→80%）
- AI 旁白生成（TTS 配音）
- 视频合成（MP4 格式）
- 视频元数据管理
- ASR 语音转文字校验（Whisper）

**合并理由：** 视频生成为培训模块的子能力（教材转视频），非独立业务域，合并减少服务数量。

### 3.4 薪资与考勤服务 (comp-attendance-service :8005)

**数据库 Schema：** comp_attendance_db

**考勤职责：**
- 多源打卡数据汇聚（指纹/人脸/IC卡/APP）
- 打卡数据清洗与班次对照
- 异常智能识别（迟到/早退/缺卡/旷工/加班超限）
- 请假/加班/出差校正
- 排班表管理
- 个人/部门考勤汇总
- 异常趋势分析

**薪资职责：**
- 薪资主数据管理（基本工资、津贴、补贴）
- 社保/公积金/个税标准跟踪与更新
- 月度薪资全自动核算（每月指定日期触发）
  - 应发 = 基本工资 + 加班费 - 考勤扣款 + 补贴
  - 加班费 = 平日1.5倍 + 周末2倍 + 法定3倍
  - 个税按七级累进税率计算
  - 实发 = 应发 - 社保 - 公积金 - 个税
- 异常检测（波动→20%、个税负数、低于最低工资等）
- 工资条批量生成与推送
- 薪资底稿生成（计算溯源）

**合并理由：** 薪资核算强依赖考勤数据（加班费、考勤扣款），合并后在同一数据库事务内完成"考勤汇总→薪资核算"流程，确保数据一致性，避免跨服务数据聚合带来的分布式事务问题。

### 3.5 绩效与外务服务 (perf-external-service :8006)

**数据库 Schema：** perf_external_db

**绩效职责：**
- 考核方案管理
- 员工自评收集
- 管理人员自评 + 互评/下属评议
- 上级审批确认
- 绩效汇总分析（分布、对比、趋势）
- 绩效报表自动生成

**外务职责：**
- 工伤事件全流程管理
  - 事故报告接收 → 情况说明生成 → 材料收集 → 校验 → 打包
  - RPA 自动登录社保系统申报
  - 理赔进度跟踪与通知
- 公积金自动操作
  - 入职当天自动开户参保
  - 离职自动封存/减员/补缴
  - RPA 自动登录公积金网站操作
- 其他政府申报（可扩展 Agent 模板）

### 3.6 证明服务 (certificate-service :8008)

**职责：**
- 在职证明、收入证明、离职证明自助申请
- Agent 自动提取信息填入标准模板
- 人事专员审核后自动签发
- 企业印章自动加盖
- 签发记录归档

### 3.7 OCR 与 RPA 服务 (auto-ocr-rpa-service :8009)

**数据库 Schema：** auto_ops_db

**OCR 职责：**
- 身份证正反面识别
- 学历证书识别
- 驾驶证/特种作业证识别
- 票据 OCR 识别
- 人脸质量检测
- 活体检测
- 多模态 LLM 辅助识别（复杂证件、手写内容）

**RPA 职责：**
- 社保系统自动登录与工伤申报
- 公积金网站自动登录与参保/补缴操作
- 浏览器自动化（Playwright 无头浏览器）
- 操作截图凭证捕获
- 凭证管理（加密存储账号密码）
- 网站改版自适应监控

**RPA 在微服务中的具体实现方案：**

RPA 功能涉及对政府网站（社保局、公积金中心等）的浏览器自动化操作，在纯微服务架构中的实现方式如下：

| 实现维度 | 方案 | 说明 |
|---------|------|------|
| 浏览器自动化引擎 | Playwright (Node.js) | 支持 Chromium/Firefox/WebKit 无头浏览器，异步操作，速度快，API 稳定 |
| 部署方式 | Docker 容器内嵌浏览器 | RPA Worker 运行在独立的 Docker 容器中，容器内预装 Chromium 浏览器及其依赖库（如 libX11、libfontconfig 等），确保无头模式正常运行 |
| Worker 进程池 | 独立 Worker 进程池 | auto-ocr-rpa-service 内部维护 RPA Worker 进程池（默认 3 个并发 Worker），每个 Worker 是独立的 Playwright 浏览器实例，互不影响 |
| 任务队列 | 内部任务队列（Redis Queue） | RPA 任务由 perf-external-service 通过 HTTP 提交到 auto-ocr-rpa-service 的 RPA 任务队列，队列存储在 Redis 中，Worker 按 FIFO 顺序取出执行 |
| 浏览器状态隔离 | 每个 Worker 独立 Browser Context | Playwright 的 Browser Context 机制确保每个 RPA 任务使用独立的 Cookie、LocalStorage 和 Session，避免任务间数据泄露 |
| 网站改版适配 | 元素选择器版本管理 | RPA 脚本中的 CSS 选择器和 XPath 选择器存储在 Nacos 配置中心，支持按版本号管理。当目标网站改版时，更新选择器配置即可热更新，无需重新部署服务 |
| 操作凭证 | HashiCorp Vault 加密存储 | 政府网站登录账号密码存储在 Vault 中，RPA Worker 执行时按需读取，不落地到磁盘 |
| 操作审计 | 每步操作截图 + 日志 | RPA 每一步操作自动截屏保存至 MinIO，操作日志记录到 auto_ops_db 的 rpa_operation_log 表，确保全过程可追溯 |
| 异常处理 | 截图 + 重试 + 人工介入 | 页面元素未找到时截图保存，等待 10 秒后重试 2 次，仍失败则推送到人工审核队列 |
| 资源限制 | CPU 2C/内存 4GB/容器级别 | 每个 RPA Worker 容器设置资源上限，防止浏览器进程占用过多资源 |

**RPA Worker 容器与 auto-ocr-rpa-service 的关系：**

```
+--------------------------------------------------+
|  auto-ocr-rpa-service (:8009) Spring Boot 微服务  |
|                                                  |
|  +----------------+     +----------------------+ |
|  | RPA 任务管理接口 |     |  RPA Worker 管理器    | |
|  | (HTTP REST API) |----->|  (进程池管理器)      | |
|  +----------------+     +--------+-------------+ |
|                            |                       |
+----------------------------+----------------------+
                             |
                    +--------v---------+
                    |  RPA Worker 容器   |
                    |  (Docker/K8s Pod)  |
                    |                    |
                    |  - Playwright     |
                    |  - Chromium 浏览器 |
                    |  - Node.js 运行时  |
                    |  - 3 个并发 Worker  |
                    +-------------------+
```

- **auto-ocr-rpa-service** 是 Spring Boot 微服务，暴露 RPA 任务的 HTTP REST API（提交任务、查询状态、获取结果）
- **RPA Worker 容器** 是独立的 K8s Pod，运行 Node.js + Playwright + Chromium 无头浏览器
- 两者通过 **本地进程间通信（gRPC 或 Unix Socket）** 通信，延迟低
- RPA Worker 容器可通过 K8s HorizontalPodAutoscaler 根据 Redis 任务队列长度自动扩容

**RPA 与桌面自动化的区别：**

本系统 RPA 不涉及桌面自动化（如 Robot Framework 的桌面模式或 UiPath 的桌面机器人），而是纯 Web 自动化：
- 目标网站均为 Web 页面（社保局、公积金中心等），浏览器自动化足以覆盖
- 无头浏览器在 Linux 服务器/Docker 容器中运行，无需桌面环境
- 如遇到需要上传文件的场景，使用 Playwright 的 `setInputFiles()` API 直接上传，不模拟鼠标拖拽

**合并理由：** OCR 和 RPA 均为自动化操作基础设施，被其他业务服务调用（如入职调用 OCR、外务调用 RPA），合并为共享工具服务。

### 3.8 分析服务 (analytics-service :8012)

**职责：**
- 全模块数据聚合分析
- 经营分析报告自动生成
- AI 偏见测试（每季度 →500 份简历）
- 简历筛选模型权重优化
- Agent 运行效能分析

---

## 4. 技术栈选型

### 4.1 前端技术栈

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| 框架 | Vue 3 | 3.4+ | 组合式 API、性能好、生态成熟 |
| 语言 | TypeScript | 5.x | 类型安全、IDE 支持 |
| 构建 | Vite | 5.x | 极速热更新 |
| UI 库 | Element Plus | 2.x | 与 Vue 3 深度集成 |
| 状态 | Pinia | 2.x | Vue 3 官方推荐 |
| 路由 | Vue Router | 4.x | 官方路由 |
| HTTP | Axios | 1.x | 拦截器、Promise |
| 移动端 | UniApp | 3.x | 一套代码多端发布 |
| 图表 | ECharts | 5.x | 丰富的图表类型 |

### 4.2 后端技术栈

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| 框架 | Spring Boot | 3.x | 成熟、生态丰富、Java 17+ |
| 语言 | Java | 17/21 | LTS 版本 |
| 网关 | Spring Cloud Gateway | 2022.x | 统一网关 |
| RPC | OpenFeign | — | 声明式 HTTP 客户端 |
| 服务网格 | Istio | 1.20+ | mTLS、熔断、重试、流量治理 |
| ORM | MyBatis-Plus | 3.5+ | 高效、灵活 SQL 控制 |
| 缓存 | Spring Data Redis | — | Redis 集成 |
| 消息 | Spring Kafka | — | Kafka 集成 |
| 流程引擎 | Camunda 8 | 8.x | BPMN 2.0 支持 |
| 限流熔断 | Sentinel (阿里) | 1.8+ | 业务维度限流（网关层） |
| 数据库迁移 | Flyway | 10.x | 数据库 schema 版本管理 |
| 日志 | SLF4J + Logback | — | 标准日志 |
| 链路追踪 | SkyWalking | 9.x | APM 监控 |
| 对象存储 | MinIO Java SDK | — | MinIO 客户端 |
| 加密 | Jasypt + AES-256-GCM | 3.x | 配置加密 + 列级加密 |
| 文档 | SpringDoc OpenAPI | 2.x | API 文档 |
| AI 网关 | Spring Boot + OpenFeign | — | AI 模型统一调用入口 |

### 4.3 AI 技术栈

| 能力 | 技术 | 选型理由 | 调用方 |
|------|------|---------|-------|
| LLM | GPT-4 / Claude / Qwen | API 调用或本地 vLLM 部署 | 所有 Agent |
| OCR | PaddleOCR | 开源、中文识别能力强 | auto-ocr-rpa-service |
| 人脸 | Face++ / ArcFace | API 或本地部署 | recruit-onboard-service |
| Embedding | bge-m3 / text-embedding-3 | 中文向量嵌入效果好 | analytics-service |
| 向量检索 | Milvus | 开源、高性能 | analytics-service |
| RPA | Playwright | 跨浏览器、异步、速度快 | auto-ocr-rpa-service |
| TTS | Edge-TTS / 阿里云语音 | 免费或低成本 | train-video-service |
| 视频合成 | FFmpeg + Python | 标准化视频处理 | train-video-service |
| ASR | Whisper | 多语言语音识别 | train-video-service |
| 多模态 LLM | GPT-4V / Qwen-VL | 图文联合理解，复杂证件识别 | auto-ocr-rpa-service、recruit-onboard-service |

### 4.4 基础设施

| 组件 | 技术 | 说明 |
|------|------|------|
| 容器 | Docker | 容器化部署 |
| 编排 | Kubernetes | 集群管理、自动扩缩 |
| 服务网格 | Istio | 服务间 mTLS、熔断、重试、流量治理 |
| 注册中心 | Nacos | 服务发现与配置中心 |
| 配置中心 | Nacos Config | 动态配置热更 |
| 密钥管理 | HashiCorp Vault | API Key、数据库密码等敏感信息加密存储 |
| CI/CD | GitLab CI / Jenkins | 自动化构建部署 |
| 监控 | Prometheus + Grafana | 指标监控 |
| 日志 | ELK (Elasticsearch+Logstash+Kibana) | 日志收集分析 |
| 链路追踪 | Apache SkyWalking | 分布式追踪 |

---

## 5. 部署架构

### 5.1 部署拓扑

```
                     +---------------+
                     |   负载均衡    |
                     |  (Nginx)     |
                     +-------+-------+
                             |
              +--------------+--------------+
              |              |              |
       +------+-------+ +----+----+ +-------+------+
       |  Web 前端集群  | | 网关集群 | | 移动端网关  |
       | (2-4 pods)  | | (2 pods)| | (2 pods)   |
       +------+-------+ +----+----+ +-------+------+
              |              |              |
              +--------------+--------------+
                             |
              +--------------v--------------+
              |    Agent 编排层 (2 pods)    |
              |   Camunda 8 + DAG 引擎      |
              +--------------+--------------+
                             |
              +--------------v--------------+
              |  AI 模型网关组件 (1-2 pods)  |
              |  ai-model-gateway :9000    |
              +--------------+--------------+
                             |
    +------------------------v------------------------+
    |              服务网格层 (Istio)                  |
    |         mTLS / 熔断 / 重试 / 流量治理            |
    +------------------------+------------------------+
                             |
    +------------------------+------------------------+
    |          |            |          |            |
+----v----+ +----v----+  +----+----+ +----v----+  +----v----+
|用户服务 | |招聘与入 |  |培训与视  | |薪资与考 |  |绩效与外 |
|:8000  | |职服务  |  |频服务    | |勤服务  |  |务服务  |
|       | |:8001  |  |:8003    | |:8005  |  |:8006  |
+-------+ +-------+  +---------+ +-------+  +-------+
+----v----+ +----v----+  +----v----+
|证明服务 | |OCR与RPA|  |分析服务 |
|:8008  | |服务   |  |:8012  |
|       | |:8009  |  |       |
+-------+ +-------+  +-------+
    |          |            |          |            |
    +----------+------------+----------+------------+
                             |
    +------------------------v------------------------+
    |              AI 模型服务层                       |
    |  +------+ +------+ +------+ +------+ +------+ |
    |  | LLM  | | OCR  | |人脸  | | ASR  | |多模态 | |
    |  |vLLM  | |Paddle| |ArcFace| |Whisper| |GPT-4V| |
    |  +------+ +------+ +------+ +------+ +------+ |
    |  +------+ +------+                            |
    |  | TTS  | |Embedding| GPU 服务器或云端 API      |
    |  |Edge  | |bge-m3  |                            |
    |  +------+ +------+                            |
    +----------------------------------------------+
                             |
    +------------------------v------------------------+
    |              数据基础设施层                       |
    |  +------+ +------+ +------+ +------+        |
    |  |MySQL | |Redis | |Kafka | |MinIO |        |
    |  |主从  | |主从+  | |3节点  | |      |        |
    |  +------+ +Sentinel+ +集群  + +------+        |
    |  +------+ +------+                           |
    |  |ES    | |Milvus|                           |
    |  |3节点  | |      |                           |
    |  +------+ +------+                           |
    +----------------------------------------------+
```

### 5.2 环境规划

| 环境 | 用途 | 配置 |
|------|------|------|
| 开发环境 (dev) | 开发调试 | 单机 Docker Compose |
| 测试环境 (test) | 集成测试 | 最小 K8s 集群 |
| 预发环境 (staging) | UAT 验收 | 生产镜像配置 |
| 生产环境 (prod) | 正式运行 | 完整 K8s 集群 |

### 5.3 资源规划

| 组件 | CPU | 内存 | 磁盘 | 副本数 | 说明 |
|------|-----|------|------|--------|------|
| Web 前端 | 2C | 4GB | 20GB | 2-4 | — |
| API 网关 | 2C | 4GB | 20GB | 2 | — |
| AI 模型网关 | 2C | 4GB | 20GB | 1-2 | ai-model-gateway-service |
| Agent 服务 | 4C | 8GB | 50GB | 1-2 每个 | 合并后 8 个服务 |
| 编排层 | 4C | 16GB | 100GB | 2 | Camunda 8 + DAG 引擎 |
| MySQL 主 | 8C | 32GB | 500GB SSD | 1 | 含 8 个 schema |
| MySQL 从 | 8C | 32GB | 500GB SSD | 1 | 读分离 + 灾备 |
| Redis 主 | 4C | 16GB | 100GB SSD | 1 | 主节点 |
| Redis 从 | 4C | 16GB | 100GB SSD | 2 | 从节点 |
| Redis Sentinel | 1C | 2GB | 10GB | 3 | 哨兵节点（轻量级） |
| Kafka | 8C | 32GB | 500GB SSD | 3 | 3节点集群，replication-factor=3 |
| MinIO | 4C | 16GB | 2TB+ | 4 | 对象存储需纠删码 |
| ES | 8C | 32GB | 500GB SSD | 3 | 3节点保障 quorum |
| Milvus | 4C | 16GB | 200GB SSD | 1 | 独立部署 |
| AI 推理 (GPU) | 8C | 64GB | 200GB | 按模型 | GPU 服务器或云端 API |
| HashiCorp Vault | 2C | 4GB | 50GB | 1 | 密钥管理服务 |

### 5.4 网络规划

```
公网区 → 负载均衡 (Nginx) → 用户浏览器/移动端
                                      |
DMZ区 → API 网关 (Spring Cloud Gateway)
                                      |
应用区 → 各微服务 (K8s Pods + Istio Sidecar)
         → AI 模型网关组件 (仅内网访问)
                                      |
数据区 → MySQL/Redis/Kafka/MinIO/ES/Milvus
                                      |
AI区 → GPU 推理服务器 (可选隔离)
```

### 5.5 安全域

| 区域 | 安全级别 | 访问控制 |
|------|---------|---------|
| 公网区 | 低 | 防火墙白名单 |
| DMZ 区 | 中 | WAF + 防火墙 |
| 应用区 | 高 | 网络策略 + Istio mTLS |
| 数据区 | 高 | 内网隔离 + 数据库防火墙 + 列级加密 |
| AI 区 | 中 | GPU 专用网络 |

---

## 6. 关键设计决策

### 6.1 为什么选择 Spring Boot + Java

- **成熟稳定**：企业级应用首选，生态完善
- **类型安全**：Java 强类型避免运行时错误
- **人才储备**：Java 开发人才充足
- **AI 集成**：可通过 HTTP/gRPC 调用 Python AI 服务

### 6.2 为什么选择 Kafka 而非 RabbitMQ

- **吞吐能力**：Kafka 高吞吐适合大规模事件流
- **持久化**：消息持久化保证不丢失
- **分区机制**：天然支持并行消费
- **生态**：与 Flink、Spark 等大数据工具集成

### 6.3 为什么选择 Camunda 8 作为流程引擎

- **BPMN 2.0**：标准流程定义
- **断点续跑**：Agent 崩溃后可恢复
- **可视化**：流程定义可拖拽编辑
- **Zeebe 引擎**：Camunda 8 原生云原生架构，比 Camunda 7 更适合 K8s 部署

### 6.4 为什么选择 MinIO 而非阿里云 OSS

- **本地部署**：数据主权完全自控
- **S3 兼容**：与 AWS S3 API 兼容，迁移容易
- **成本**：无流量费用
- **性能**：内网高速传输

### 6.5 为什么选择 Milvus 作为向量数据库

- **中文优化**：对中文向量检索效果好
- **开源免费**：无 licensing 费用
- **高性能**：支持亿级向量检索
- **集成**：与 LangChain、FastGPT 等生态兼容

### 6.6 为什么引入 Istio 服务网格

- **统一治理**：服务间通信的熔断、重试、超时、mTLS 由网格统一配置，无需在 OpenFeign 中分散配置
- **零侵入**：Sidecar 代理模式，业务代码无需修改
- **可观测性**：自动生成服务拓扑、延迟热力图、错误率仪表盘
- **流量治理**：支持灰度发布、A/B 测试

### 6.7 微服务合并决策

原始设计为 13 个独立微服务，存在以下问题：
- 招聘与入职共享员工主数据，独立拆分导致大量跨服务调用
- 薪资核算强依赖考勤数据，拆分后需分布式事务保障一致性
- OCR、视频等为工具型服务，非独立业务域

按业务域聚合后精简为 8 个服务，跨服务调用减少约 40%，数据一致性风险显著降低。

### 6.8 降级模式设计

当外部依赖不可用时，系统按以下策略降级：

| 失效场景 | 降级方案 | 影响范围 |
|---------|---------|---------|
| LLM 不可用 | 关键词正则匹配 + 预置模板 | 简历筛选精度下降，文书生成退化为模板 |
| OCR 不可用 | 人工录入（降级例外） | 入职效率下降，其余 Agent 不受影响 |
| 人脸不可用 | 身份证 + 手机验证码 | 入职方式降级 |
| RPA 被拦截 | 外务专员窗口操作（降级例外） | 外务效率下降 |
| 编排层异常 | 手动触发单个 Agent | 端到端流程中断，需手动接力 |
| 数据库故障 | 切从库 → 只读模式 | 写入功能暂停 |

### 6.9 Istio 与 Sentinel 分层治理边界

架构同时引入 Istio 服务网格和阿里 Sentinel 限流组件，两者职责分层如下：

| 维度 | Istio (L7 传输层) | Sentinel (应用层) |
|------|-------------------|------------------|
| 职责范围 | 服务间通信治理 | 网关入口流量治理 |
| mTLS | 是（服务间加密传输） | 否 |
| 熔断 | 是（基于下游服务错误率/延迟） | 是（基于网关入口 QPS/RT） |
| 重试 | 是（自动重试下游服务） | 否 |
| 超时控制 | 是（服务间调用超时） | 是（网关请求超时） |
| 限流 | 否（Istio 不含细粒度限流） | 是（按用户/接口/业务维度） |
| 配置方式 | Istio VirtualService/DestinationRule | Sentinel 控制台规则 |
| 典型场景 | user-service 调用 recruit-service 失败时熔断重试 | 同一用户1分钟内薪资查询超过10次则限流 |

**维护成本说明：** 两层治理的配置独立维护，Istio 配置由运维团队管理（部署时通过 K8s CRD 配置），Sentinel 规则由业务团队通过 Sentinel 控制台动态调整，互不干扰。

### 6.10 AI 模型调用策略

Agent 服务调用 AI 模型层采用统一网关模式，核心设计决策如下：

| 决策项 | 方案 | 理由 |
|--------|------|------|
| 调用协议 | HTTP REST 为主，gRPC 为辅 | REST 通用性强，gRPC 用于大文件传输 |
| 服务发现 | Nacos 注册 + AI 模型网关组件 | 统一注册中心，避免 Agent 硬编码模型地址 |
| 本地优先 | 优先调用本地部署模型，云端 API 降级备选 | 数据主权、降低云端依赖、减少 API 费用 |
| 健康检查 | AI 模型服务暴露 /health 端点，K8s 定期探测 | 及时发现模型服务异常 |
| 熔断降级 | 连续失败 3 次触发熔断，自动切换云端 API | 保障业务连续性 |
| 多模态模型 | 本地 Qwen-VL 优先，GPT-4V API 备选 | 兼顾本地部署偏好和识别能力 |
| 统一入口 | 所有 AI 调用经过 AI 模型网关组件 | 集中管理路由、熔断、降级、监控 |

### 6.11 编排双引擎策略（Camunda 8 + DAG）

系统同时引入 Camunda 8 流程引擎和自定义 DAG 引擎，双引擎分工明确：

| 决策项 | 方案 | 理由 |
|--------|------|------|
| 跨域流程 | Camunda 8 BPMN | 标准化流程定义，支持人工审批节点 |
| 域内任务 | DAG 引擎 | 细粒度并行编排，灵活调整任务拓扑 |
| 集成方式 | External Task Worker | Camunda 8 原生支持的扩展模式 |
| 状态管理 | Camunda 管流程状态，DAG 管任务状态 | 各管各层，互不干扰 |

**为什么不全部用 Camunda 8 的子流程/调用活动：**

Camunda 8 支持子流程（Subprocess）和调用活动（Call Activity），但以下场景不适用于 BPMN 子流程：

1. **动态并行度**：入职证件 OCR 场景中，证件数量和类型不确定（可能只有身份证，也可能有身份证+学历证+驾驶证+特种作业证）。BPMN 子流程需要预定义固定数量的并行分支，无法在运行时根据输入动态决定并行节点数量。DAG 引擎根据实际传入的证件列表动态构建有向图，节点数量和依赖关系在运行时确定。

2. **条件分支的粒度**：简历筛选中，不同岗位类型触发不同的评估路径（技术岗需要技能评估，管理岗需要领导力评估）。BPMN 的排他网关（Exclusive Gateway）支持条件分支，但当条件分支涉及 5+ 个并行子任务的组合时，BPMN 流程图变得难以维护（节点数膨胀、连线交叉复杂）。DAG 引擎的条件节点支持在运行时评估复杂表达式并决定后续路径。

3. **Fan-In 结果聚合**：薪资核算中需要从考勤、绩效、外务等多个源并行获取数据后聚合计算。BPMN 的并行网关（Parallel Gateway）支持 Fan-Out/Fan-In，但聚合节点需要从多个分支收集不同结构的结果并进行合并计算，这在 BPMN 的 Service Task 中难以优雅表达。DAG 引擎的 Fan-In 节点原生支持多输入聚合。

4. **Camunda 8 子流程的成本**：每个子流程需要独立的 BPMN 定义文件、独立的部署、独立的版本管理。对于域内任务（如证件 OCR），频繁调整任务顺序或并行度意味着每次都要修改 BPMN XML 并重新部署，开发效率低。DAG 引擎的 JSON/YAML 定义可通过 Nacos 配置中心热更新，无需重新部署。

**结论**：Camunda 8 的子流程/调用活动适合"固定结构、可预定义"的子流程，而 DAG 引擎适合"动态结构、运行时确定"的任务编排。两者互补而非替代。

**DAG 引擎成熟度评估：**

DAG 引擎为自研轻量级组件，成熟度如下：

| 评估维度 | 当前状态 | 风险等级 | 缓解措施 |
|---------|---------|---------|---------|
| 核心功能（拓扑排序、并行调度、条件分支） | 已实现并测试 | 低 | 单元测试覆盖率 → 90% |
| 断点恢复（Redis 状态持久化） | 已实现 | 低 | 集成测试覆盖崩溃恢复场景 |
| 锁续期机制 | 已实现 | 低 | 与 Camunda 8 联调验证 |
| 生产级监控告警 | 待实现 | 中 | V7 版本纳入监控指标（节点耗时、失败率） |
| 大规模并发测试（100+ 并发 DAG 实例） | 待验证 | 中 | 压测阶段验证 ForkJoinPool 线程池参数 |
| 运维工具（手动触发、暂停、强制终止 DAG 实例） | 待实现 | 低 | 低频使用场景，V8 版本补充 |

DAG 引擎不替代 Camunda 8，仅处理域内任务编排，功能边界清晰，故障面可控。即使 DAG 引擎完全不可用，Camunda 8 仍可降级为直接调用单个 Agent（失去并行能力但流程可运行）。

**Camunda 8 引擎模式说明：**

本系统采用 **Camunda 8 Zeebe 原生引擎模式**（Self-Hosted Zeebe），非 Camunda SaaS/Cloud 模式。两种模式的关键差异如下：

| 维度 | Zeebe 原生模式（本系统采用） | Camunda SaaS/Cloud 模式 |
|------|--------------------------|----------------------|
| 部署方式 | 自建 K8s 集群部署 Zeebe 引擎 + Operate + Tasklist | 使用 Camunda 官方托管云服务 |
| API 规范 | Zeebe Job Worker API（`/v1/jobs/{key}/activate`、`/v1/jobs/{key}/complete`、`/v1/jobs/{key}/fail`） | Camunda 8 Operational API（`/v1/process-instances/...`）+ 部分 Job Worker API |
| External Task Worker | 原生支持，通过 gRPC 或 REST API 轮询 | 支持，但需通过 Camunda Cloud 连接 |
| 数据主权 | 数据完全本地化，不依赖第三方云服务 | 部分数据存储在 Camunda 云端 |
| 成本 | 一次性硬件投入 + 运维成本 | 按使用量付费（按月/按流程实例） |
| 定制化 | 完全可控，可深度定制 | 受限于 Camunda 云平台的 API 和配置选项 |

选择 Zeebe 原生模式的原因：
1. **数据主权**：HR 系统涉及大量员工敏感数据（身份证、薪资、健康信息等），数据必须完全本地化存储，不经过任何第三方云平台
2. **成本可控**：自建部署在 12 个月后总成本低于 SaaS 模式，且无持续 API 调用费用
3. **深度集成**：Zeebe 原生模式允许与 K8s、Istio、Nacos 等基础设施深度集成，SaaS 模式受限于 Camunda 云平台的封闭生态
4. **API 路径说明**：V9 修订说明中"修正Camunda 8 External Task Worker API为v8规范"指的是确认使用 Zeebe 8.x 的 Job Worker REST API 路径（`/v1/jobs/{key}/complete`），而非 Camunda 7 的 REST API（如 `CompleteRestResource`）。此 API 路径正确，对应 Camunda 8 Zeebe 原生引擎的 Job Worker 接口规范。

**双引擎状态同步一致性保障：**

两套引擎的状态各自独立维护，不存在"状态同步"的需求——Camunda 8 维护业务流程实例状态（运行在哪个节点），DAG 引擎维护 DAG 实例状态（每个子任务的状态）。两者通过 External Task Worker 模式的单向通信建立因果关系：

1. **Camunda 8 → DAG 引擎**（任务下发）：Camunda 8 通过 External Task 触发 DAG 执行，DAG 引擎领取任务后在 Redis 中创建锁 `dag:lock:{task_id}`，TTL 等于 Worker 锁剩余时间。此锁防止同一任务被重复执行。

2. **DAG 引擎 → Camunda 8**（结果回传）：DAG 引擎通过 `complete()` 或 `fail()` API 将结果回传 Camunda 8。Camunda 8 收到后更新流程实例状态。

3. **状态不一致的场景与处理**：

| 场景 | 不一致表现 | 处理方式 |
|------|-----------|---------|
| DAG 完成但未回传成功 | DAG 状态为 success，Camunda 8 仍显示 External Task pending | Worker 锁超时（300秒）后 Zeebe 释放任务，其他 Worker 重新领取。DAG 引擎检查 Redis 锁，发现已完成则立即回传结果 |
| Camunda 8 回传成功但 Zeebe 崩溃 | DAG 状态为 success，Camunda 8 Zeebe 未记录 | Zeebe 恢复后，External Task 锁超时重新释放，Worker 重新领取。DAG 引擎检查 Redis 锁，发现已完成则立即回传结果 |
| DAG 引擎崩溃后重启 | Redis 保留未完成状态 | 从 Redis 恢复已完成的节点状态，跳过已完成节点继续执行 |
| Redis 故障 | DAG 运行时状态丢失 | DAG 实例状态降级为 failed，回传 Camunda 8 失败信息。Camunda 8 触发 BPMN 错误处理分支。Redis 恢复后可重新触发流程 |

4. **最终一致性保障**：通过"Redis 锁 + Camunda 8 Worker 锁 + 结果幂等"三层机制确保最终一致性。DAG 引擎的 `complete()` API 调用是幂等的——同一任务多次 complete 返回相同结果，Camunda 8 以首次 complete 为准。

### 6.12 基础设施复杂度与运维成本合理性论证

本系统采用的基础设施包括 8 个微服务 + Kafka 3节点 + ES 3节点 + Redis 主从 + MySQL 主从 + Istio 服务网格 + Camunda 8 Zeebe + Milvus 向量库 + MinIO 对象存储，相比传统 HR 系统确实较重。以下论证其合理性：

**1) 与业务复杂度的匹配性**

本系统并非传统 CRUD 型 HR 系统，而是 AI 原生系统，其业务复杂度远超传统 HR 系统：

| 对比维度 | 传统 HR 系统 | GBM AI Agent HR | 基础设施需求差异 |
|---------|------------|----------------|---------------|
| 核心执行主体 | 人类用户 | AI Agent（8个） | 需要服务间通信治理（Istio）和事件驱动（Kafka） |
| 流程复杂度 | 固定表单流转 | 多分支、并行、条件触发的 Agent 链式调用 | 需要流程引擎（Camunda 8）+ 任务编排（DAG） |
| 数据处理 | 结构化 CRUD | 非结构化文档 OCR、向量检索、全文检索 | 需要 Milvus（向量）、ES（全文）、MinIO（文件） |
| 数据一致性 | 单库事务 | 跨服务 Saga + 本地消息表 | 需要 Kafka（可靠消息）+ Redis（分布式锁） |
| AI 推理 | 无 | LLM、OCR、人脸、ASR、TTS 等多模态推理 | 需要 GPU 服务器 + AI 模型网关 + 降级链路 |

**2) 关键组件数量级论证**

**Kafka 为何需要 3 节点而非 2 节点：**

| 对比项 | 2 节点集群 | 3 节点集群 | 说明 |
|--------|----------|----------|------|
| replication-factor=3 时的写入可用性 | 不可用（2 节点无法达成 3 副本 quorum） | 可用（3 节点中 1 个故障仍可写入） | Kafka 要求 acks=all 时至少 (replication-factor/2 + 1) 个副本确认 |
| 单节点故障后的可用性 | 集群不可用（2 节点挂 1 个失去 quorum） | 集群可用（3 节点挂 1 个仍有 quorum） | 主节点选举需要多数派确认 |
| 吞吐能力 | 约 1.5 万 msg/s/节点 | 约 2.25 万 msg/s（3 节点合计） | Kafka 分区可跨节点均衡分布 |
| 本系统消息量预估 | 日均 10 万条事件（薪资核算、入职流程等） | 日均 10 万条事件 | 3 节点绰绰有余 |

**结论**：replication-factor=3 要求至少 3 个节点，否则无法达成多数派确认，消息可靠性目标（acks=all）无法实现。2 节点集群即使设置 replication-factor=2，在单节点故障时仍面临写入不可用风险。3 节点是最小的高可用配置。

**Milvus 向量检索在 HR 场景中的必要性：**

| 场景 | 检索需求 | 传统方案 | Milvus 方案 | 必要性 |
|------|---------|---------|-----------|--------|
| 简历语义匹配 | 根据岗位描述语义检索匹配简历（非关键词匹配） | ES 全文检索（TF-IDF，无法捕捉语义相似度） | bge-m3 生成简历向量 + Milvus ANN 检索（语义相似度 Top-K） | 高——SRS 要求"语义 20%"匹配权重，传统全文检索无法实现语义匹配 |
| AI 偏见检测 | 每季度对 →500 份简历进行向量聚类分析，检测筛选偏差 | 无法实现 | 简历向量聚类，检测聚类中心偏差 | 中——SRS 明确要求偏见检测，向量聚类是唯一可行方案 |
| 知识嵌入检索 | 培训知识库的语义搜索 | ES 全文检索（有限语义能力） | 知识库向量检索（精确语义匹配） | 低——当前非核心需求，但为未来培训知识检索预留 |

**结论**：Milvus 的核心必要性来自简历语义匹配（SRS 要求 20% 语义权重）和 AI 偏见检测（SRS 明确要求），这两个场景无法通过 ES 全文检索替代。

**3) 全量本地部署 AI 模型的硬件成本**

| 模型 | 本地部署最低硬件要求 | 月成本估算（本地） | 云端 API 月成本（等效） | 备注 |
|------|-------------------|-----------------|---------------------|------|
| LLM (Qwen-72B) | 1=A100 80GB GPU 或 2=RTX 4090 24GB | =5,000-8,000（设备折旧） | =10,000-20,000（按量付费） | 72B 模型需至少 40GB+ 显量，本地部署仅首次投入 |
| PaddleOCR | CPU 即可，推荐 8C/16GB | =0（无额外硬件） | =500-1,000（按量付费） | OCR 对硬件要求低，本地部署零额外成本 |
| Whisper (ASR) | 1=RTX 3090/4090 或 CPU | =0-3,000（共享 GPU 服务器） | =500-1,000（按量付费） | 可与 LLM 共享 GPU |
| bge-m3 (Embedding) | CPU 即可，16GB 内存 | =0（无额外硬件） | =200-500（按量付费） | 嵌入计算轻量，CPU 可胜任 |
| Face++ | API 调用 | =0 | =500-1,000（按量付费） | 推荐 API 调用，本地部署 ROI 低 |
| GPT-4V (多模态) | API 调用或 Qwen-VL 本地 | =0-3,000（共享 GPU） | =1,000-3,000（按量付费） | 推荐 Qwen-VL 本地部署 |
| Edge-TTS (TTS) | CPU 即可 | =0（免费） | =0（免费） | 完全免费 |

**本地部署 vs 云端 API 总体成本对比（月）：**

| 方案 | 初期投入 | 月运营成本 | 年总成本 | 说明 |
|------|---------|-----------|---------|------|
| 全量云端 API | =0 | =15,000-25,000 | =180,000-300,000 | 按量付费，无前期投入 |
| 本地 GPU 服务器 + 部分云端 API | =80,000-120,000（1台 GPU 服务器） | =3,000-5,000（电费+维护） | =120,000-180,000 | 12 个月后低于云端方案 |
| 混合模式（推荐） | =80,000-120,000（1台 GPU 服务器） | =5,000-8,000（本地+云端降级） | =140,000-220,000 | 本地为主，云端降级，兼顾成本和可靠性 |

**结论**：本地部署 1 台 GPU 服务器（约 =10 万）在 12 个月后总成本即低于纯云端方案，且保障数据主权。系统推荐混合模式：本地部署为主，云端 API 作为降级备选。

**4) 运维团队能力要求与培养计划**

| 运维组件 | 所需技能 | 学习曲线 | 培养方式 |
|---------|---------|---------|---------|
| K8s + Docker | 容器编排、Pod 管理、Service/Ingress | 中（2-4 周） | 线上课程 + 测试环境实操 |
| Kafka | 集群管理、Topic 管理、监控 | 中（1-2 周） | 官方文档 + 实操 |
| MySQL 主从 | 主从配置、备份恢复 | 低（1 周） | 传统 DBA 技能 |
| Redis | 主从/Sentinel 配置 | 低（1 周） | 传统缓存技能 |
| ES | 索引管理、集群健康 | 中（1-2 周） | ELK 生态课程 |
| Istio | Sidecar、VirtualService、熔断规则 | 高（2-4 周） | 官方文档 + 实操 |
| Milvus | 集合管理、向量导入 | 低（1 周） | 官方教程 |
| AI 模型服务 | GPU 监控、模型更新 | 中（1-2 周） | GPU 运维基础课程 |

**运维成本量化评估：**

| 运维项 | 估算（人/月） | 说明 |
|--------|-------------|------|
| K8s 集群运维 | 0.5 | 容器编排自动化程度高，日常运维少 |
| 监控与告警 | 0.3 | Prometheus + Grafana 自动化监控，告警驱动 |
| 数据库运维 | 0.5 | MySQL 主从切换、备份恢复 |
| Kafka/ES 运维 | 0.3 | 集群健康检查、日志清理 |
| AI 模型服务运维 | 0.4 | 模型更新、GPU 资源管理、降级切换 |
| Istio/服务网格 | 0.3 | 规则配置、流量治理 |
| 合计 | ~2.3 人/月 | 约 2-3 名运维工程师 |

**结论**：运维团队约需 2-3 名工程师，其中 1 名熟悉 K8s+Istio，1 名熟悉数据库+中间件，1 名熟悉 AI 模型服务（可兼职）。通过分阶段上线和培训，可在 2-3 个月内完成能力培养。

**5) 阶段性建设策略**

为降低初期运维负担，采用分阶段建设策略：

| 阶段 | 上线组件 | 运维复杂度 | 预计周期 |
|------|---------|-----------|---------|
| 第一阶段（MVP） | MySQL 主从 + Redis 主从 + 8个微服务 + Nacos + MinIO | 低 | 1-2 个月 |
| 第二阶段（AI 能力） | + Kafka 3节点 + AI 模型服务 + AI 模型网关 | 中 | 2-3 个月 |
| 第三阶段（流程自动化） | + Camunda 8 + ES 3节点 + Milvus + Istio | 中-高 | 2-3 个月 |

每阶段增加运维能力培训和监控覆盖，确保运维团队逐步适应复杂度增长。

**6) 运维团队能否支撑如此复杂的中间件栈**

评估结论：**可以支撑，但需要以下条件：**

1. **团队规模**：2-3 名运维工程师，1 名系统架构师兼技术负责人
2. **自动化程度**：基础设施即代码（Terraform/Ansible），K8s 使用 Helm Charts 管理部署，减少手动操作
3. **监控覆盖**：Prometheus + Grafana 全覆盖，告警驱动运维，而非人工巡检
4. **文档完备**：每个中间件的运维手册、故障处理 SOP、回滚方案
5. **培训周期**：关键人员提前 1-2 个月进行 K8s/Istio 培训

**风险与缓解：**

| 风险 | 缓解措施 |
|------|---------|
| 运维团队初期不熟练 | 采用托管服务或外包运维过渡（3-6 个月） |
| Istio 学习曲线陡峭 | 初期使用默认配置，逐步精细化 |
| GPU 服务器故障 | 云端 API 降级保障业务连续性 |
| 中间件版本升级 | 非核心组件保持 LTS 版本，核心组件每季度评估升级 |

### 6.13 Spring Cloud Gateway 与 Istio 流量治理边界

架构同时存在 Spring Cloud Gateway 和 Istio 服务网格，两者在流量治理上存在**层次分明、互不重叠**的职责边界。

**请求链路：**
```
客户端 → Nginx(SSL终止/静态资源) → Spring Cloud Gateway(业务网关) → Istio Sidecar(mTLS/熔断/重试) → 微服务
```

**职责边界说明：**

| 治理维度 | Spring Cloud Gateway (L7 业务网关) | Istio Sidecar (L7 服务网格) |
|---------|--------------------------------|--------------------------|
| 作用域 | 客户端 → 网关 → 微服务入口 | 微服务 → 微服务内部通信 |
| 身份认证 | JWT Token 校验、OAuth2 认证 | mTLS 双向证书认证 |
| 权限控制 | RBAC 细粒度接口权限检查 | 无（依赖 Gateway 前置校验） |
| 业务限流 | Sentinel 按用户/接口/业务维度限流 | 无（Istio 不支持细粒度业务限流） |
| 熔断 | Sentinel 网关入口级熔断 | 基于下游服务错误率/延迟的熔断 |
| 重试 | 无（依赖 Istio 或服务层配置） | 自动重试（可配置最大重试次数和退避策略） |
| 超时控制 | 网关请求总超时（默认 30 秒） | 服务间调用超时（可按服务单独配置） |
| 负载均衡 | 无（依赖 Nacos 服务发现） | 内置负载均衡（轮询/加权/一致性哈希） |
| 可观测性 | 统一出入日志、链路追踪入口 | 服务间通信指标、延迟热力图、错误率统计 |

**配置冲突风险评估：**

| 潜在冲突点 | 是否存在风险 | 说明 |
|-----------|------------|------|
| 熔断规则重叠 | 否 | Gateway 熔断保护网关入口（如 Sentinel 按 QPS 熔断），Istio 熔断保护服务间调用（如下游错误率 50% 熔断），作用域不同 |
| 超时配置冲突 | 否 | Gateway 超时是客户端请求总超时，Istio 超时是服务间调用超时。推荐 Gateway 超时 > 所有 Istio 超时之和，避免嵌套超时导致级联失败 |
| 重试风暴 | 否 | Gateway 不配置重试（避免客户端重复请求），Istio 仅在服务间通信启用重试，两者不叠加 |
| 限流冲突 | 否 | 限流仅由 Sentinel 在 Gateway 层实现，Istio 不参与限流 |

**配置维护分工：**

| 配置项 | 维护方 | 维护方式 |
|--------|--------|---------|
| Gateway 路由规则 | 运维团队 | K8s Ingress/GatewayRoute CRD |
| Gateway 鉴权配置 | 安全团队 | Spring Cloud Gateway Filter 配置 |
| Sentinel 限流规则 | 业务团队 | Sentinel 控制台动态调整 |
| Istio mTLS 策略 | 运维团队 | Istio PeerAuthentication CRD |
| Istio 熔断/重试规则 | 运维团队 | Istio VirtualService/DestinationRule CRD |
| Istio 超时配置 | 运维团队 | Istio VirtualService CRD |

**结论：** Spring Cloud Gateway 与 Istio 职责分层清晰，不存在配置冲突风险。Gateway 管"谁能进、进多少"，Istio 管"怎么传、传得稳不稳"。两者协同工作，互不干扰。

---

## 7. 分布式事务与数据一致性

### 7.1 问题背景

薪资核算涉及多源数据聚合：考勤数据、员工主数据、社保标准、个税标准等。在微服务架构下，这些数据分布在不同的服务中（如员工主数据在 user-service、考勤数据在 comp-attendance-service、社保标准在 perf-external-service）。

### 7.2 一致性策略

**策略一：业务域内事务（优先）**

通过微服务合并，将强依赖的数据放在同一服务内，使用本地数据库事务保障一致性：
- 薪资与考勤合并：考勤汇总和薪资核算在同一数据库事务内完成
- 招聘与入职合并：候选人转员工在同一事务内完成
- 培训与视频合并：视频生成与培训记录在同一事务内完成

**策略二：Saga 模式（跨服务场景）**

对于不可避免的跨服务操作，采用 Saga 模式保障最终一致性：

| 流程 | Saga 步骤 | 补偿操作 |
|------|---------|---------|
| 员工入职→社保参保 | ①写入员工记录 → ②触发公积金开户 → ③触发社保参保 | ③失败则回滚②，②失败则标记①为待处理 |
| 薪资核算→工资条推送 | ①计算薪资 → ②生成工资条 → ③推送通知 | ③失败则重试推送，②失败则重新生成 |
| 离职→外务减员 | ①标记离职 → ②公积金封存 → ③社保减员 | ③失败则定时重试，②失败则人工介入 |

**策略三：可靠消息 + 本地消息表**

关键跨服务操作采用"本地消息表"模式：
1. 业务操作和本地消息记录在同一数据库事务中写入
2. 定时任务扫描本地消息表，发布到 Kafka
3. 消费方保证幂等性（通过消息 ID 去重）

### 7.3 幂等性设计

所有 Agent 接口均支持幂等调用：
- 请求携带唯一业务 ID（如员工工号 + 操作类型 + 日期）
- 服务端记录已处理的业务 ID，重复请求直接返回已有结果
- Kafka 消费端通过消费者组 + 偏移量管理保证至少一次消费，业务层通过幂等性保证恰好一次效果

### 7.4 对账机制

- 薪资核算后自动生成核算底稿，记录每个计算步骤的输入和输出
- 每日定时对账任务：考勤汇总记录数 vs 薪资核算记录数，差异超过阈值告警
- 月度关账前执行全量对账，确认无差异后方可生成工资条

---

## 8. 安全合规与数据保护

### 8.1 敏感数据分类

| 敏感级别 | 数据类别 | 示例 |
|---------|---------|------|
| L4 绝密 | 薪资数据 | 基本工资、津贴、实发工资、个税 |
| L3 高敏 | 身份与健康 | 身份证号、银行卡号、健康状况、工伤记录 |
| L2 中敏 | 联系方式与地址 | 手机号、邮箱、家庭住址、紧急联系人 |
| L1 一般 | 工作信息 | 姓名、部门、岗位、入职日期 |

### 8.2 数据加密存储

| 措施 | 实施方案 |
|------|---------|
| 列级加密 | 身份证号、银行卡号、薪资字段使用 AES-256-GCM 加密存储，密钥由 KMS (HashiCorp Vault) 管理 |
| 传输加密 | 全链路 HTTPS/TLS 1.3，服务间通过 Istio mTLS 加密 |
| 配置加密 | 数据库密码、API Key 等通过 Jasypt 加密存储在配置中心 |
| 静态加密 | MinIO 开启 SSE-S3 服务端加密，ES 开启索引级别加密 |

### 8.3 数据脱敏

| 场景 | 脱敏规则 |
|------|---------|
| 日志中的敏感信息 | 身份证号显示为 110**********123，手机号显示为 138****5678，薪资显示为 **** |
| 开发/测试环境 | 使用真实数据的脱敏副本，所有 L3/L4 数据替换为随机生成值 |
| 导出数据 | 默认脱敏，需审批后方可导出明文 |
| 前端展示 | 身份证号、银行卡号默认掩码显示，点击"查看"需二次验证（MFA） |

### 8.4 访问控制

- **RBAC 细粒度权限**：基于角色的访问控制，权限粒度到接口级别
- **字段级权限**：薪资数据仅 HR 主管和本人可见，其他角色无法访问
- **行级权限**：部门主管仅可见本部门员工数据
- **操作审计**：所有对 L3/L4 数据的访问、修改、导出操作记录审计日志，保留不少于 10 年（符合 SRS 4.2.1 要求）

### 8.5 合规要求

- **《个人信息保护法》**：员工个人信息收集遵循最小必要原则，入职时获取明示同意
- **《数据安全法》**：数据分类分级管理，重要数据定期风险评估
- **《网络安全法》**：等级保护测评（二级），定期进行渗透测试
- **数据留存策略**：离职员工数据保留期限按法律法规要求（如薪资记录保留 2 年），到期自动匿名化
- **数据主体权利**：支持员工查询、更正、删除个人数据的请求流程
- **审计日志不可篡改**：审计日志写入后不允许任何人修改或删除，保藏期限→ 10 年

### 8.6 AI 模型敏感数据合规说明

本系统调用的 AI 模型服务涉及员工敏感生物特征数据和身份信息，以下说明数据合规性和隐私保护措施：

**1) 人脸识别数据合规**

| 维度 | 措施 | 合规依据 |
|------|------|---------|
| 数据收集 | 入职时获取员工书面同意（电子协议签署中明确人脸采集用途、存储期限和第三方调用方） | 《个人信息保护法》第十三条：取得个人同意 |
| 本地优先 | 优先使用本地部署的 ArcFace 模型（运行在 GPU 服务器上），人脸数据不出域 | 数据最小化出域原则 |
| 云端降级 | Face++ 作为云端 API 降级备选，调用时仅传输人脸图像（不含姓名、身份证号等可识别信息），调用后立即删除云端临时数据 | 《个人信息保护法》第三十九条：向其他国家/地区提供个人信息的条件 |
| 数据脱敏 | 调用 Face++ API 时，请求中不携带员工姓名、身份证号等可直接识别的字段，仅传输人脸图像数据 | 去标识化处理 |
| 传输加密 | Face++ API 调用全链路 HTTPS/TLS 1.3 加密 | 《数据安全法》第二十一条 |
| 存储期限 | 人脸原始照片在完成入职档案后 30 天内删除，仅保留人脸特征向量（不可还原为原始照片） | 数据留存最小化原则 |
| 特征向量加密 | 人脸特征向量使用 AES-256-GCM 加密存储，密钥由 HashiCorp Vault 管理 | 敏感数据加密要求 |
| 员工权利 | 支持员工申请查询、更正或删除其人脸数据（通过 user-service 的个人信息管理接口） | 《个人信息保护法》第四章：个人行使权利 |

**2) 多模态 LLM（GPT-4V）数据处理合规**

| 维度 | 措施 | 合规依据 |
|------|------|---------|
| 优先本地 | 优先使用本地部署的 Qwen-VL 模型，数据不出域 | 数据主权优先 |
| 云端降级 | GPT-4V API 作为降级备选时，传入的图像不携带可识别的个人信息（如身份证照片自动裁剪掉姓名/身份证号区域后再传入） | 去标识化处理 |
| 敏感内容过滤 | Agent 服务在调用多模态 LLM 前，经过敏感内容过滤器，身份证号、银行卡号等 L3/L4 数据自动替换为掩码 | 《个人信息保护法》第五十一条 |
| 输出审计 | 多模态 LLM 的输出经过审核管道，确认不泄露其他员工数据后方可使用 | 数据安全保护义务 |

**3) ASR 语音数据处理合规**

| 维度 | 措施 | 合规依据 |
|------|------|---------|
| 本地部署 | Whisper 本地部署在 Docker 容器中，录音数据不出域 | 数据本地化 |
| 用途限制 | ASR 仅用于培训视频的旁文字幕生成，录音数据在转文字后 24 小时内删除 | 目的限制原则 |
| 不存储原始录音 | 系统不长期存储培训考试录音，仅保留文字转录结果 | 数据最小化原则 |

**4) Embedding 向量数据合规**

| 维度 | 措施 | 合规依据 |
|------|------|---------|
| 输入去标识化 | 简历文本生成向量前，自动去除姓名、身份证号、手机号等直接标识符 | 去标识化处理 |
| 向量不可逆 | bge-m3 生成的向量不可还原为原始文本，降低隐私泄露风险 | 匿名化处理 |
| 存储加密 | Milvus 中的向量数据开启 MinIO 后端加密（SSE-S3） | 静态数据加密 |

**5) 第三方 AI 服务数据安全评估**

所有云端 AI API（Face++、GPT-4V、text-embedding-3 等）在接入前需通过以下评估：

1. **供应商安全评估**：审查供应商的安全认证（ISO 27001、SOC 2）、数据保护政策和服务等级协议
2. **数据传输评估**：确认数据传输使用 TLS 1.3 加密，不支持明文传输
3. **数据存储评估**：确认供应商不会将传入数据用于模型训练或长期存储（要求签署数据处理协议 DPA）
4. **地域合规评估**：确认数据存储地域，如存在跨境传输需额外履行《个人信息保护法》第三十九条规定的评估程序

**6) 隐私影响评估 (PIA)**

系统在以下场景触发隐私影响评估：
- 新增调用第三方 AI 服务前
- AI 模型处理的数据类型发生变更时
- 法律法规更新影响数据处理方式时

PIA 评估报告存档于 user-service，保留期限不少于 5 年。

---

## 9. 数据备份与灾难恢复

### 9.1 备份策略

| 数据类别 | 备份频率 | 保留周期 | 备份方式 |
|---------|---------|---------|---------|
| MySQL 全量 | 每日 02:00 | 30 天 | mysqldump + 二进制日志 |
| MySQL 增量 | 每小时 | 7 天 | binlog 增量备份 |
| Redis | 每日 03:00 | 7 天 | RDB 持久化 + AOF |
| MinIO 对象 | 实时 | 永久 | MinIO 纠删码 + 跨机房复制 |
| Kafka 消息 | 不单独备份 | — | 依赖 Kafka 自身持久化（保留 7 天） |
| ES 索引 | 每日 04:00 | 14 天 | snapshot 快照到 MinIO |
| Milvus 集合 | 每周全量 | 4 周 | 集合导出 |
| 配置文件 | 变更时 | 永久 | Git 版本管理 |

### 9.2 灾难恢复方案

| 灾难场景 | RTO（恢复时间目标） | RPO（恢复点目标） | 恢复方案 |
|---------|---------------------|-------------------|---------|
| 单机故障 | 5 分钟 | 0（无数据丢失） | K8s 自动重启 Pod，MySQL 切从库 |
| 单机房故障 | 30 分钟 | 1 小时 | 跨机房 MySQL 主从切换 + K8s 跨机房调度 |
| 数据库损坏 | 2 小时 | 1 小时 | 从最新全量备份 + binlog 增量恢复 |
| 数据误删除 | 1 小时 | 0 | 从备份恢复指定时间点的数据库 |
| 勒索攻击 | 4 小时 | 取决于备份 | 隔离感染环境，从离线备份恢复 |

### 9.3 灾备架构

- **同城双机房**：MySQL 主从跨机房部署，MinIO 跨机房复制
- **离线备份**：每周将全量备份复制到离线存储（独立 NAS 设备），防止勒索攻击
- **恢复演练**：每季度执行一次灾难恢复演练，验证 RTO/RPO 达标

### 9.4 监控告警

- 备份任务失败立即告警（短信 + 邮件）
- 备份文件完整性校验（MD5/SHA256 校验和）
- 磁盘空间不足预警（使用率 80% 告警）

---

## 10. 数据库迁移与版本管理

### 10.1 Flyway 集成

所有微服务的数据库 schema 变更通过 **Flyway** 管理，确保版本可控、可追溯、可回滚。

### 10.2 迁移文件命名规范

```
V{版本号}__{描述}.sql
示例：
V1_1__create_user_table.sql
V1_2__create_role_table.sql
V2_0__add_employee_salary_columns.sql
V2_1__create_payroll_monthly_table.sql
```

### 10.3 迁移流程

1. 开发人员编写 Flyway 迁移脚本，随代码提交到 Git
2. CI/CD 流水线在部署时自动执行 Flyway migrate
3. 生产环境执行前先在预发环境验证
4. 迁移失败自动回滚部署，不执行部分迁移

### 10.4 版本管理策略

- 每个微服务独立管理自己的 schema 版本
- Flyway 版本表（flyway_schema_history）记录所有迁移历史
- 禁止手动修改生产数据库 schema，所有变更必须通过 Flyway 迁移脚本
- 向下兼容原则：新增字段默认 nullable，删除字段先标记废弃，至少两个版本后方可物理删除

### 10.5 回滚方案

- Flyway 不支持自动回滚，回滚需编写专门的 undo 脚本
- 紧急情况下可从备份恢复指定版本的数据库
- 重大变更（如表结构重构）需提前准备回滚方案和测试验证

---

## 11. 数据字典与编码规范

### 11.1 编码规范总则

- 所有编码采用固定长度 + 前缀标识的格式
- 编码一旦分配，永久不变（即使对应实体删除）
- 编码生成由 user-service 统一负责，其他服务通过接口申请

### 11.2 核心编码规则

| 编码类型 | 格式 | 示例 | 说明 |
|---------|------|------|------|
| 员工工号 | EMP + 6位序号 | EMP000001 | 入职时分配，终身不变 |
| 部门编码 | DEP + 4位层级码 | DEP0101 | 根部门 DEP0100，子部门递增 |
| 岗位编码 | POS + 4位分类 + 2位序号 | POS1001 | 前4位为岗位分类（10=技术、20=管理、30=HR等） |
| 薪资项目编码 | PYI + 4位序号 | PYI0001 | 基本工资 PYI0001，加班费 PYI0002 等 |
| 考勤类型编码 | ATT + 3位序号 | ATT001 | 正常 ATT001，迟到 ATT002，早退 ATT003 等 |
| 招聘渠道编码 | SRC + 3位序号 | SRC001 | 前程无忧 SRC001，中国人才热线 SRC002 等 |
| 培训类型编码 | TRT + 3位序号 | TRT001 | 入职培训 TRT001，安全培训 TRT002 等 |
| 绩效周期编码 | PRC + 8位日期 | PRC20260601 | 年月日格式，标识绩效周期 |
| 外务类型编码 | EXT + 3位序号 | EXT001 | 工伤申报 EXT001，公积金增减 EXT002 等 |
| 证明类型编码 | CRT + 3位序号 | CRT001 | 在职证明 CRT001，收入证明 CRT002 等 |
| 学历编码 | EDU + 2位序号 | EDU01 | 博士 EDU01，硕士 EDU02，本科 EDU03 等 |
| 证件类型编码 | IDC + 3位序号 | IDC001 | 身份证 IDC001，护照 IDC002，驾驶证 IDC003 等 |

### 11.3 数据字典管理

- 数据字典（枚举值、编码表）存储在 user-service 的 user_db 中
- 数据字典变更通过 Flyway 迁移脚本管理
- 其他服务通过 user-service 的 API 获取数据字典，或启动时缓存到 Redis
- 数据字典 API 响应缓存 24 小时，变更时主动刷新缓存

---

## 12. Agent 异常处理与补偿机制

### 12.1 异常分类

| 异常类型 | 说明 | 处理策略 |
|---------|------|---------|
| 可重试异常 | 网络超时、LLM 限流、外部 API 暂时不可用 | 指数退避重试（1s、2s、4s、8s、16s，最多 5 次） |
| 需补偿异常 | 数据写入成功但后续步骤失败 | 触发 Saga 补偿流程 |
| 需人工介入 | 规则无法解决的争议、证件信息不一致、外部系统拒绝 | 推送到人工审核队列，通知人事专员 |
| 系统性故障 | 数据库不可用、Kafka 宕机、K8s 节点故障 | 服务降级 + 告警通知 |

### 12.2 重试策略

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 最大重试次数 | 5 | 超过后进入死信队列 |
| 初始等待时间 | 1 秒 | — |
| 退避倍数 | 2 | 指数退避 |
| 最大等待时间 | 60 秒 | 防止无限等待 |
| 抖动因子 | 0.5 | 避免雪崩效应 |

### 12.3 死信队列 (DLQ)

- Kafka 为每个业务 topic 配置对应的死信 topic（如 payroll-topic → payroll-dlq-topic）
- 消息重试次数用尽后自动转发到死信队列
- 死信队列消息保留 30 天，附带失败原因、重试次数、原始消息内容
- 定时任务每日扫描死信队列，生成异常报告推送给人力资源管理员

### 12.4 人工介入流程

1. Agent 检测到无法自动处理的异常
2. 将异常任务写入人工审核队列（Redis List）
3. 通过短信/邮件通知对应人事专员
4. 人事专员在 Web 端查看异常详情，提供处理意见
5. 处理意见写回后，编排层重新触发对应的 Agent 继续执行
6. 全流程记录审计日志

### 12.5 Agent 健康检查

- 每个 Agent 服务暴露 /health 和 /ready 端点
- K8s 定期执行健康检查，不健康 Pod 自动重启
- Agent 连续 3 次健康检查失败触发告警
- Agent 处理超时（默认 300 秒）自动终止并进入重试/补偿流程

---

## 13. 多租户隔离策略

### 13.1 当前定位

GBM AI Agent HR 系统当前定位为 **企业内部系统**（Single-Tenant），不面向 SaaS 模式。所有数据属于同一组织，无需多租户隔离。

### 13.2 未来 SaaS 扩展预留

如未来需要扩展为 SaaS 模式，架构已预留以下扩展点：

| 扩展点 | 当前设计 | SaaS 模式变更 |
|--------|---------|-------------|
| 数据库 | 单一实例多 schema | 按租户独立 schema 或独立数据库实例 |
| 对象存储 | 单一 MinIO 桶 | 按租户前缀隔离（/tenant-{id}/） |
| 用户服务 | 单组织 RBAC | 增加租户上下文，租户级 RBAC |
| 网关路由 | 路径前缀路由 | 增加 Host/Header 级租户路由 |
| 数据隔离 | 行级权限（部门级） | 租户 ID 作为查询强制过滤条件 |
| 计费计量 | 无 | 增加用量计量服务 |

### 13.3 租户隔离方案（预留）

如启用 SaaS 模式，采用 **schema 级隔离**（非 row-level）：
- 每个租户分配独立的数据库 schema（如 tenant_001_emp_lifecycle_db）
- Flyway 迁移脚本支持多租户批量执行
- MinIO 按租户前缀隔离对象
- 网关层根据请求中的租户标识路由到对应的数据源

---

## 14. Agent 间通信机制

### 14.1 双模通信架构

系统采用 **Kafka 异步事件 + OpenFeign 同步 HTTP** 双模通信架构，通过明确的边界规则决定使用哪种方式。

```
+------------+                      +------------+
| Agent A  | ===== Kafka 事件 ======8= | Agent B  |  (异步、解耦、可靠)
|          | ===== 事件响应 ======8= |          |
|          |                      |          |
|          | ===== HTTP 请求 ======8= |          |  (同步、即时响应)
|          | ===== HTTP 响应 ======8= |          |
+------------+                      +------------+
```

### 14.2 通信方式选择规则

| 判断维度 | 选择 Kafka | 选择 HTTP |
|---------|-----------|----------|
| 是否需要即时响应 | 不需要 | 需要 |
| 是否需要服务解耦 | 需要 | 不需要（紧密耦合可接受） |
| 是否需要扇出（一对多） | 需要 | 不需要 |
| 是否涉及事务边界 | 跨服务 | 同服务内 |
| 数据量 | 大（文件、批量） | 小（查询、配置） |
| 调用频率 | 高频 | 低频 |

### 14.3 Kafka Topic 设计

**命名规范：** `{domain}.{entity}.{action}`

| Topic | 分区数 | 分区键 | 生产者 | 消费者 | 保留时间 |
|-------|--------|--------|--------|--------|---------|
| recruit-onboard.candidate.created | 8 | employee_id | recruit-onboard | analytics | 7 天 |
| recruit-onboard.employee.onboarded | 8 | employee_id | recruit-onboard | train-video, perf-external | 30 天 |
| comp-attendance.payroll.calculated | 8 | employee_id | comp-attendance | user (薪资记录) | 30 天 |
| comp-attendance.attendance.summary | 8 | employee_id | comp-attendance | analytics | 7 天 |
| train-video.training.plan.created | 4 | plan_id | train-video | recruit-onboard (入职培训联动) | 7 天 |
| perf-external.performance.review.created | 4 | employee_id | perf-external | analytics | 30 天 |
| perf-external.external.task.completed | 4 | employee_id | perf-external | recruit-onboard (外务状态更新) | 30 天 |
| certificate.request.submitted | 2 | certificate_id | certificate | user (审计日志) | 7 天 |
| user.employee.updated | 4 | employee_id | user | recruit-onboard, comp-attendance (主数据同步) | 7 天 |
| dag.engine.task.triggered | 4 | dag_instance_id | Camunda 8 | DAG 引擎 | 1 天 |
| dag.engine.task.completed | 4 | dag_instance_id | DAG 引擎 | 监控/审计 | 1 天 |
| dag.engine.task.failed | 4 | dag_instance_id | DAG 引擎 | 监控/告警 | 7 天 |

### 14.4 分区策略

- **按员工 ID 分区**：确保同一员工的所有事件有序（如入职→培训→薪资的流转）
- **按业务 ID 分区**：培训计划、证明申请等按自身 ID 分区
- **按 DAG 实例 ID 分区**：DAG 引擎事件按实例 ID 分区，确保同一 DAG 的执行事件有序

### 14.5 消息消费失败处理

```
消费失败 → 应用层重试 (3次, 指数退避)
         → 仍失败 → 投递至 DLQ topic
         → DLQ 消息保留 30 天
         → 每日扫描生成异常报告
         → 人工介入处理后重新投递
```

### 14.6 OpenFeign 同步调用边界

以下场景使用 OpenFeign HTTP 同步调用：

| 调用方 | 被调用方 | 接口示例 | 理由 |
|--------|---------|---------|------|
| certificate-service | user-service | GET /api/users/{id}/profile | 证明开具需要即时获取员工信息 |
| certificate-service | comp-attendance-service | GET /api/payroll/{id}/summary | 收入证明需要即时获取薪资数据 |
| analytics-service | 各服务 | GET /api/{domain}/stats | 分析服务聚合数据查询 |
| recruit-onboard-service | user-service | GET /api/users/{id}/dept | 入职时需要即时获取部门信息 |
| train-video-service | user-service | GET /api/users/{id}/certs | 培训签到时需要即时获取员工证书信息 |

所有同步调用通过 Istio 服务网格管理熔断、重试、超时。

### 14.7 Kafka Topic 命名规范

```
{service-name}.{event-type}.{entity}

示例：
recruit-onboard.candidate.created          # 招聘服务：候选人创建事件
recruit-onboard.employee.onboarded         # 招聘服务：员工入职完成事件
comp-attendance.payroll.calculated         # 薪资服务：薪资核算完成事件
comp-attendance.attendance.summary         # 考勤服务：考勤汇总事件
train-video.training.plan.created          # 培训服务：培训计划创建事件
perf-external.performance.review.created   # 绩效服务：绩效考核创建事件
perf-external.external.task.completed      # 外务服务：外务任务完成事件
certificate.request.submitted              # 证明服务：证明申请提交事件
user.employee.updated                      # 用户服务：员工信息更新事件
dag.engine.task.triggered                  # DAG引擎：DAG触发事件
dag.engine.task.completed                  # DAG引擎：DAG完成事件
dag.engine.task.failed                     # DAG引擎：DAG失败事件
```

### 14.8 Kafka Topic 分区策略

| Topic 类别 | 分区数 | 分区键 | 说明 |
|-----------|--------|--------|------|
| 招聘类 topic | 8 | `employee_id` | 按员工ID分区，确保同一员工的事件有序 |
| 薪资考勤类 topic | 8 | `employee_id` | 按员工ID分区，确保同一员工的薪资事件有序 |
| 培训类 topic | 4 | `training_plan_id` | 按培训计划ID分区 |
| 外务类 topic | 4 | `employee_id` | 按员工ID分区 |
| 证明类 topic | 2 | `certificate_id` | 按证明ID分区 |
| DAG 引擎类 topic | 4 | `dag_instance_id` | 按 DAG 实例ID分区 |
| 用户类 topic | 4 | `employee_id` | 按员工ID分区 |

### 14.9 消息消费失败的重试策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 自动提交偏移量 | 禁用 | 手动提交，确保至少一次消费语义 |
| 最大拉取数量 | 50 | 每批次拉取 50 条消息 |
| 消费超时 | 30 秒 | 单条消息处理超时时间 |
| 重试机制 | 应用层重试 3 次 | 每次等待 2^attempt 秒（1s、2s、4s） |
| 死信队列 | 每个 topic 对应一个 DLQ topic | 重试耗尽后转发至 DLQ |
| DLQ 保留 | 30 天 | 死信消息保留 30 天供排查 |
| DLQ 告警 | 每小时检查 DLQ 消息数 | DLQ 消息数 0 触发告警 |

### 14.10 死信队列 (DLQ) 命名规范

```
{original-topic}.dlq

示例：
recruit-onboard.candidate.created.dlq
comp-attendance.payroll.calculated.dlq
```

### 14.11 OpenFeign 同步调用配置

| 参数 | 值 | 说明 |
|------|-----|------|
| 连接超时 | 3 秒 | 建立 TCP 连接超时 |
| 读取超时 | 10 秒 | 等待响应超时 |
| 重试次数 | 2 次 | 失败自动重试 |
| 熔断器 | Sentinel | 连续 5 次失败熔断 30 秒 |

---

## 15. 跨服务数据流设计

### 15.1 人员主数据同步流程

员工主数据（姓名、身份证、部门、岗位等）由 user-service 维护，其他服务需要引用。数据同步流程如下：

```
+---------------+     Kafka 事件      +---------------+
| user-service  | ----employee.updated--= recruit-    |
|  (:8000)     |                    | onboard-    |
|              |                    | service     |
| 主数据源      |                    |  (:8001)    |
|              |                    | 同步员工档案   |
+---------------+                    +---------------+
    |                             |
    |      employee.updated       |
    | --------------------------=8= comp-attendance-service
    |                            |  (:8005)
    |                            | 同步薪资主数据
    |                            |
    |      employee.updated      |
    | --------------------------=8= perf-external-service
    |                            |  (:8006)
    |                            | 同步绩效档案
```

**同步时序：**

```
1. user-service 创建/更新员工记录
2. user-service 在本地事务中写入 employee 表 + local_message 表
3. 定时任务扫描 local_message 表，发布 user.employee.updated 事件到 Kafka
4. recruit-onboard-service 消费事件，更新本地员工档案（幂等：以 employee_id 为去重键）
5. comp-attendance-service 消费事件，更新薪资主数据（幂等：以 employee_id 为去重键）
6. perf-external-service 消费事件，更新绩效档案（幂等：以 employee_id 为去重键）
```

### 15.2 入职→培训数据流转

新员工入职完成后，自动触发培训计划创建：

```
+--------------------+     Kafka 事件        +--------------------+
| recruit-onboard   | ----employee.onboarded--= train-video      |
|  (:8001)         |                      |  (:8003)         |
|                  |                      |                  |
| 入职流程完成      |                      | 创建入职培训计划   |
| 发布事件          |                      | 生成培训材料      |
+--------------------+                      +--------------------+
    |                                       |
    |    employee.onboarded                 |
    | ------------------------------------=8= perf-external-service
    |                                      |  (:8006)
    |                                      | 初始化绩效档案
```

**详细时序：**

```
1. recruit-onboard-service 完成入职流程（证件OCR、协议签署、人脸采集、档案生成）
2. 发布 recruit-onboard.employee.onboarded 事件到 Kafka，携带员工ID、入职日期、部门信息
3. train-video-service 消费事件：
   a. 查询入职培训计划模板（从 training_db 读取）
   b. 为该员工创建培训计划实例
   c. 生成签到二维码
   d. 发布 train-video.training.plan.created 事件
4. perf-external-service 消费事件：
   a. 为该员工初始化绩效档案
   b. 设置试用期考核计划
```

### 15.3 薪资核算数据聚合

月度薪资核算需要聚合考勤、绩效、外务数据：

```
                    Kafka 事件
         +--------------------------+
         |                         |
         v                         v
+----------------+          +----------------+
| comp-         |          | perf-        |
| attendance   |          | external     |
| service      |          | service      |
| (:8005)      |          | (:8006)      |
+------+-------+          +------+-------+
    |                         |
    |   考勤数据 (本服务内)     |   绩效数据 (本服务内)
    |                         |
    v                         |
+-------------------------------------------+
|  comp-attendance-service             |
|  薪资核算 Agent                       |
|                                      |
|  1. 从本服务读取考勤数据               |
|  2. HTTP 调用 perf-external 获取绩效  |
|  3. HTTP 调用 user-service 获取主数据  |
|  4. 计算应发/实发工资                  |
|  5. 发布 payroll.calculated 事件      |
+-------------------------------------------+
    |
    | payroll.calculated
    v
+-------------------------------------------+
|  工资条推送 → 通知推送 (短信/邮件)    |
|  税务申报 → perf-external-service     |
|  分析归档 → analytics-service         |
+-------------------------------------------+
```

### 15.4 离职数据流转

```
1. user-service 标记员工离职状态
2. 发布 user.employee.updated 事件 (status=terminated)
3. perf-external-service 消费事件：
   a. 触发公积金封存 RPA 任务
   b. 触发社保减员 RPA 任务
   c. 记录外务操作日志
4. comp-attendance-service 消费事件：
   a. 停止考勤记录
   b. 计算最后薪资
5. certificate-service 自动触发离职证明生成
6. train-video-service 消费事件：
   a. 取消未完成培训计划
   b. 归档培训记录
```

### 15.5 外务RPA操作结果回传

```
+--------------------+     HTTP/RPA 调用     +--------------------+
| perf-external    | --------------------=8= | 社保/公积金网站   |
| service          |                       | (外部系统)        |
| (:8006)          | ======== 操作结果 ======8= |                  |
|                  |                       |                  |
| RPA Agent        |  RPA 操作结果          |
| 调用 auto-ocr-   | --------------------=8= | auto-ocr-rpa    |
| rpa-service      |                       | service         |
|                  |                       | (:8009)         |
+--------------------+                       +--------------------+
     |
     | external.task.completed
     | --------------------------=8=  Kafka 事件总线
     |
     v
+--------------------+
| recruit-onboard  | 更新外务状态
| service          | 到员工档案
| (:8001)         |
+--------------------+
```

---

## 16. 需求覆盖验证矩阵

### 16.1 功能需求覆盖

| SRS 章节 | 功能需求 | 架构组件 | 覆盖状态 |
|---------|---------|---------|---------|
| 3.1 | 招聘管理（简历抓取、去重、匹配、分拣） | recruit-onboard-service (:8001) + ES + Milvus | 已覆盖 |
| 3.1 | 智能组卷与阅卷 | recruit-onboard-service + LLM (vLLM) | 已覆盖 |
| 3.2 | 入职管理（OCR、认证、协议、人脸、档案） | recruit-onboard-service + auto-ocr-rpa-service + PaddleOCR + Face++ | 已覆盖 |
| 3.3 | 试用期管理 | recruit-onboard-service + perf-external-service | 已覆盖 |
| 3.4 | 离职管理 | recruit-onboard-service + perf-external-service + certificate-service | 已覆盖 |
| 3.5 | 培训管理（计划、签到、考试、阅卷、证书） | train-video-service + Whisper + TTS | 已覆盖 |
| 3.5 | 体系审核资料生成 | train-video-service + LLM | 已覆盖 |
| 3.6 | 考勤管理（多源汇聚、清洗、异常识别） | comp-attendance-service | 已覆盖 |
| 3.7 | 薪资管理（核算、异常检测、工资条） | comp-attendance-service + LLM | 已覆盖 |
| 3.8 | 绩效管理（自评、互评、审批、汇总） | perf-external-service + LLM | 已覆盖 |
| 3.9 | 外务管理（工伤、公积金、社保申报） | perf-external-service + auto-ocr-rpa-service + Playwright | 已覆盖 |
| 3.10 | 证明开具（在职、收入、离职证明） | certificate-service + LLM | 已覆盖 |
| 3.11 | 证书效期监控 | analytics-service + 定时任务 | 已覆盖 |
| 3.12 | 视频生成（教材转视频、TTS旁白） | train-video-service + FFmpeg + TTS + ASR | 已覆盖 |
| 3.13 | 数据分析与报表 | analytics-service + ES + Milvus | 已覆盖 |
| 3.14 | AI 偏见测试 | analytics-service + Milvus (向量聚类) | 已覆盖 |
| 3.15 | 移动端员工自助 | UniApp + API 网关 + 各服务 | 已覆盖 |
| 3.16 | 扫码签到入口 | H5 + QR Code | 已覆盖 |

### 16.2 非功能需求覆盖

| SRS 章节 | 非功能指标 | 架构方案 | 覆盖状态 |
|---------|----------|---------|---------|
| 4.1 | 响应时间：页面加载 3 秒 | Vue 3 + Vite + CDN 静态资源 + Redis 缓存 | 已覆盖 |
| 4.1 | 响应时间：API 调用 500ms | Spring Boot + Redis 缓存 + DB 索引优化 | 已覆盖 |
| 4.1 | 响应时间：LLM 调用 60 秒 | vLLM 推理优化 + 云端 API 降级 | 已覆盖 |
| 4.1 | 响应时间：OCR 识别 10 秒 | PaddleOCR 本地部署 + GPU 加速 | 已覆盖 |
| 4.2 | 并发能力：100 人同时在线 | K8s 自动扩缩 + 服务网格负载均衡 | 已覆盖 |
| 4.2 | 并发能力：薪资核算并发 500 人 | Kafka 分区并行 + DAG 引擎并行调度 | 已覆盖 |
| 4.2 | 可用性 SLA：99.5% | MySQL 主从 + Kafka 3节点 + K8s 自愈 | 已覆盖 |
| 4.2 | 可用性 SLA：核心流程 99.9% | Camunda 8 断点续跑 + Redis 锁 + Saga 补偿 | 已覆盖 |
| 4.3 | 数据安全：AES-256-GCM 加密 | Jasypt + AES-256-GCM 列级加密 + Vault 密钥管理 | 已覆盖 |
| 4.3 | 数据传输：全链路 mTLS | Istio 服务网格 mTLS | 已覆盖 |
| 4.3 | 审计日志：保留 → 10 年 | user-service 审计日志表 + 不可篡改设计 | 已覆盖 |
| 4.4 | 备份恢复：RTO 30 分钟 | MySQL 主从 + K8s 自愈 + 定时备份 | 已覆盖 |
| 4.4 | 备份恢复：RPO 1 小时 | MySQL binlog + Kafka 持久化 | 已覆盖 |
| 4.5 | AI 模型降级：本地不可用时自动切换云端 | AI 模型网关熔断降级 + 云端 API 备选 | 已覆盖 |
| 4.6 | 合规性：符合个人信息保护法 | 数据脱敏 + 最小权限 + 数据主体权利支持 | 已覆盖 |
| 4.6 | 合规性：符合数据安全法 | 数据分类分级 + 加密存储 + 定期风险评估 | 已覆盖 |

### 16.3 架构组件与 SRS 需求映射摘要

| 架构组件 | 支持的 SRS 功能需求 | 支持的 SRS 非功能需求 |
|---------|-------------------|-------------------|
| recruit-onboard-service | 3.1(招聘)、3.2(入职)、3.3(试用期)、3.4(离职) | 4.1(API响应)、4.2(并发) |
| train-video-service | 3.5(培训)、3.12(视频生成) | 4.1(OCR响应) |
| comp-attendance-service | 3.6(考勤)、3.7(薪资) | 4.1(响应时间)、4.2(并发) |
| perf-external-service | 3.8(绩效)、3.9(外务) | 4.2(可用性) |
| certificate-service | 3.10(证明开具) | 4.1(响应时间) |
| auto-ocr-rpa-service | 3.2(OCR)、3.9(RPA外务) | 4.1(OCR响应) |
| analytics-service | 3.11(效期监控)、3.13(分析)、3.14(偏见测试) | 4.1(响应时间) |
| user-service | 认证授权、主数据管理 | 4.3(审计日志)、4.6(合规) |
| Camunda 8 + DAG | 全流程编排 | 4.2(可用性SLA) |
| Kafka | 事件驱动通信 | 4.2(并发)、4.4(备份恢复) |
| AI 模型层 | 所有AI能力 | 4.1(响应时间)、4.5(降级) |
| Istio | 服务网格治理 | 4.3(mTLS)、4.2(可用性) |
| Milvus | 语义检索、偏见检测 | 4.1(响应时间) |
| ES | 全文检索 | 4.1(响应时间) |

### 16.4 未覆盖需求与风险评估

| 需求项 | 覆盖状态 | 说明 |
|--------|---------|------|
| 所有功能需求 | 已覆盖 | 架构组件已完整覆盖 SRS 3.x 节的所有功能需求 |
| 所有非功能需求 | 已覆盖 | 架构方案已完整覆盖 SRS 4.x 节的所有非功能指标 |
| 未来扩展需求 | 已预留 | 端口预留、多租户扩展点、SaaS 模式预留 |

---

*文档结束*
