# Agent Harness 管理平台需求规格说明书

## 1. 概述

企业级 Agent 管理平台，基于 ETCLOVG 七层架构，管理多种类型的 Agent（AI Agent、监控 Agent、RPA 等）。核心能力按优先级：**编排 > 安全 > 监控 > 生命周期 > 市场 > 计费**。

部署模式：混合部署。核心私有化指控制面组件（G 层治理与安全、L 层 Temporal Server、L 层 Agent Registry、C 层长期记忆存储、O 层可观测性后端）部署于企业私有数据中心；云端可部署 Agent 运行时沙盒（E 层执行环境）及按需扩展的计算节点，但 Agent 间通信始终经 mTLS 加密回传至私有化控制面。面向企业内部团队，支持大规模（500+ Agent）集群管理。

## 2. ETCLOVG 七层架构

| 层 | 名称 | 职责 |
|----|------|------|
| E | Execution & Sandbox | Agent 运行环境（容器/microVM/浏览器） |
| T | Tool Interface | 工具发现与调用（MCP/A2A/Function Calling） |
| C | Context Management | 短期上下文/中期会话/长期记忆 |
| L | Lifecycle/Orchestration | 执行流调度、重试、多 Agent 编排 |
| O | Observability | 追踪/监控/日志/成本 |
| V | Verification & Evaluation | 评测模型+Harness 组合 |
| G | Governance & Security | 身份/权限/钩子/审计/宪法规则 |

## 3. 术语和定义

| 术语 | 定义 |
|------|------|
| 核心组件 | 控制面组件：G 层（SPIFFE/SPIRE、OPA、审计日志、宪法规则引擎）、L 层（Temporal Server、Agent Registry）、C 层长期记忆存储、O 层可观测性后端。必须部署于企业私有数据中心，不可外迁。 |
| 云端组件 | 可部署于公有云或第三方数据中心的组件：E 层 Agent 运行时沙盒（容器/microVM/浏览器环境）、按需扩展的计算节点。云端运行 Agent 的所有通信经 mTLS 加密回传至私有化控制面。 |
| 宕机零丢失（RPO=0） | 故障场景限定为 Temporal Server 持久化层单集群内故障，包含该集群内所有节点同时故障的场景，依赖 Temporal Durable Execution 的 Event History 持久化语义实现。跨集群故障转移场景不承诺 RPO=0，需额外部署跨区域复制方案方可保障。 |
| Agent 类型 | 指 Agent 在平台中的运行模式分类，由以下维度形式化定义：运行模式（LangGraph ReAct 循环/定时触发/脚本执行）、通信协议（A2A + MCP / A2A 仅）、注册方式（Agent Registry / 配置文件）、沙盒类型（容器/microVM/浏览器）。新增 Agent 类型必须满足以上四维定义，无需修改平台核心代码即可通过配置文件注册。 |
| 沙盒池 | E 层 Agent 运行时沙盒的预分配资源池，包含同类型沙盒实例的集合。沙盒池按沙盒类型（容器/microVM/浏览器）分类管理，支持按租户划分隔离。池内沙盒实例由沙盒池管理器统一分配和回收，单个沙盒实例是沙盒池的基本分配单元。 |
| 基础 O 层 | MVP 范围内的 O 层功能子集，包含：OpenTelemetry Tracing 数据采集、运行时 Metrics 采集（调用量、延迟、错误率）、结构化日志采集。成本追踪功能不在 MVP 范围内。 |

## 4. 用户角色与权限矩阵

平台基于 G 层策略引擎支持的四种标准角色：

| 角色 | 描述 | 权限边界 |
|------|------|---------|
| admin | 平台管理员，拥有全部管理权限 | Agent 注册/注销/配置修改、工作流创建/终止、策略规则增删改、审计日志查询、租户管理、用户管理、系统配置 |
| operator | 运营运维人员，负责日常运行维护 | Agent 查看/启停、工作流查看/重试/终止、审计日志查询、监控面板查看、告警处理、沙盒池扩缩操作 |
| developer | Agent 开发者，负责 Agent 开发与部署 | Agent 注册/更新/版本管理、工作流创建/调试、测试沙盒访问、Agent 日志查询、新 Agent 类型接入 |
| viewer | 只读用户，仅可查看信息 | Agent 列表查看、工作流状态查看、监控面板查看、审计日志只读查询 |

每项权限操作均经过 G 层 OPA 策略引擎校验，跨租户访问由 SPIFFE 命名空间隔离。

## 5. 功能需求

### P0 — 编排（Lifecycle & Orchestration）

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-E-01 | 沙盒执行环境管理 — 支持容器（Docker）、microVM（E2B）、浏览器（Computer Use/GUI操作场景）三种沙盒类型的生命周期管理（创建、启动、停止、销毁）和沙盒池动态管理 | E 层 | 通过集成测试验证：每种沙盒类型连续 100 次创建和启动测试成功率 100%，单次创建到就绪时间 <= 30 秒；沙盒池支持按需分配和回收：分配由 Agent 启动请求触发，单次分配完成延迟上限 <= 10 秒；回收由沙盒实例空闲超时触发，空闲超时阈值可配置（取值范围 [60, 3600] 秒，默认值 300 秒），单次回收完成延迟上限 <= 30 秒 |
| F-T-01 | 工具接口协议支持 — 统一接入 MCP、A2A、Function Calling 三种协议，支持工具发现与调用 | T 层 | 通过集成测试验证：Agent 可通过 MCP 协议发现并调用外部工具，至少成功发现 3 个已注册的 MCP 工具，工具调用成功率 >= 99%（连续 100 次调用），单次工具调用 P95 延迟 <= 500ms；Agent 间通过 A2A 协议通信，支持至少 10 个并发 Agent 间的 A2A 消息交换 |
| F-L-01 | 跨 Agent 工作流编排 — 支持 Temporal Workflow 定义跨 Agent 的执行流程 | L 层核心 | 通过集成测试验证：定义包含 2 个以上 Agent 的工作流，成功执行并在工作流最终 Activity 完成后返回该 Activity 的输出数据，输出数据格式与 Activity 的定义返回值一致 |
| F-L-02 | Saga 补偿事务 — 工作流失败时执行补偿操作回滚部分完成的状态 | L 层核心 | 通过故障注入测试验证：工作流中途失败，补偿操作按注册时定义的逆序执行（后注册的 Activity 先补偿），部分完成状态回滚至初始 |
| F-L-03 | 人工审批（Signal）— 工作流中插入人工审批节点，支持超时后回滚 | L 层核心 | 通过集成测试验证：Signal 等待超时后工作流按回滚策略执行；Signal 发送后工作流继续执行 |
| F-L-04 | 定时/重试调度 — 支持定时触发和工作流重试策略（workflow_retry）。定时触发支持 CRON 表达式和 ISO8601 持续间隔两种调度格式。工作流重试策略（workflow_retry）配置包含以下参数：最大重试次数（max_retries，取值范围 [0, 10]）、退避间隔（backoff_interval，单位秒，取值范围 [1, 3600]，默认值 60）、超时时间（timeout，单位秒，取值范围 [1, 86400]，默认值 600）。工作流重试策略来源包括三个层级，按优先级从高到低排列：(1) 工作流启动时的工作流参数中指定的工作流重试策略配置，优先级最高；(2) Agent Card 的 retry_config 字段（详见第 6.1 节），作用于单个 Agent，可覆盖所属 Agent 类型的默认工作流重试策略配置；(3) Agent 类型配置文件中的工作流重试策略配置定义（重试配置在 Agent 类型注册时指定，详见第 20 节），作为该类型所有 Agent 的默认值。工作流参数中未指定时，优先使用 Agent Card 的 retry_config；Agent Card 未配置时，使用所属 Agent 类型的默认工作流重试策略配置 | L 层核心 | 通过集成测试验证：CRON 表达式指定的定时任务在对应时间触发；ISO8601 持续间隔指定的定时任务按间隔周期触发；失败任务按配置的重试参数自动重试 |
| F-L-05 | Agent Registry — Agent 注册与发现，基于 A2A Agent Card 描述能力集与端点 | L 层核心 | 通过集成测试验证：Agent 注册后可通过 GET /api/v1/agents 接口查询返回的 Agent 列表确认该 Agent 存在，列表项包含 agent、capabilities、status 字段；重复注册返回 HTTP 409 状态码及 CONFLICT 错误码，响应体格式为 { "error": { "code": "CONFLICT", "message": "Agent 已存在" } } |
| F-L-06 | 健康检查 — 定期检测 Agent 运行状态 | L 层核心 | 通过集成测试验证：健康检查间隔可配置，取值范围 [5, 300] 秒，默认值 30 秒；异常状态 Agent 被标记并告警 |
| F-L-07 | LangGraph Agent 内部推理 — 每个 Agent 内部 ReAct 循环（思考→调用工具→观察→思考） | L 层核心 | 通过单元测试验证：ReAct 循环在不超过该 Agent 类型注册时设置的 max_turns 配置值的轮数内完成；工具调用失败时进入工具调用重试策略（tool_retry）（重试参数：最大重试次数取值范围 [0, 5]，退避间隔取值范围 [0.1, 30] 秒，超时时间取值范围 [1, 60] 秒），达到最大重试次数后返回预定义的降级响应（含错误码 ERROR_CODE 和 fallback 占位值），降级响应格式为 { "status": "degraded", "error_code": "TOOL_CALL_FAILED", "fallback": <string>（默认取值为空字符串 ""）, "retry_attempts": <实际重试次数> } |

### P1 — 安全（Governance & Security）

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-G-01 | 工作负载身份 — SPIFFE/SPIRE 为每个 Agent 和工作流分配唯一身份 | G 层 | 通过集成测试验证：每个 Agent 和工作流获得唯一 SPIFFE ID；身份可验证 |
| F-G-02 | 传输加密 — mTLS 双向认证，所有 Agent 间通信加密 | G 层 | 通过安全测试验证：未经 mTLS 认证的连接被拒绝；通信内容经抓包验证为加密 |
| F-G-03 | 策略引擎 — OPA 实现访问控制策略 | G 层 | 通过集成测试验证：OPA 策略生效时越权操作被拒绝；策略更新后 60 秒内生效 |
| F-G-04 | 关系型权限 — OpenFGA 实现细粒度关系权限 | G 层 | 通过集成测试验证：用户对 Agent 的访问受 OpenFGA 模型约束；权限变更后正确生效 |
| F-G-05 | 声明式宪法规则 — 基于 YAML 规则引擎，覆盖宪法规则定义的 3 个拦截点（tool_call.before / llm_input.before / agent_to_agent）。宪法规则先于生命周期钩子（F-G-06）执行：同一事件触发时，先评估宪法规则，若结果为 REJECT 则直接拒绝且不触发钩子；若结果为 REDACT/ALERT/APPROVE，且该拦截点在生命周期钩子中有对应项（tool_call.before 对应 exec_before、llm_input.before 对应 input_before）时，再进入生命周期钩子继续处理。agent_to_agent 拦截点无对应生命周期钩子，宪法规则处理完毕后即结束 | G 层 | 通过集成测试验证：每个拦截点的规则正确触发对应的 REJECT/REDACT/ALERT/APPROVE 动作 |
| F-G-06 | 生命周期钩子 — 四个拦截点：输入前、执行前、返回后、关键动作前。其中"关键动作前"拦截点的触发条件判定标准为满足以下任一项的操作：(1)涉及资源删除（如删除 Agent、工作流、沙盒池）；(2)涉及数据导出或外发（如导出审计日志、导出 Agent 数据到外部系统）；(3)涉及跨租户操作（如跨租户 Agent 间通信、跨租户数据访问）；(4)单次操作涉及的费用超过用户配置的费用阈值； | G 层 | 通过集成测试验证：每个拦截点的钩子函数在正确时机被调用；异常时输出明确错误信息 |
| F-G-07 | 审计日志 — Write-Once 不可篡改，记录每次调用/决策/拒绝 | G 层 | 通过安全测试验证：审计日志写入后不可修改或删除；临时性写入失败（非存储满）触发告警但不阻断业务。审计日志存储空间达到 90% 时触发告警；写满时审计子系统内部返回错误码 AUDIT_LOG_FULL，业务操作以降级模式继续执行（跳过审计写入，不阻塞业务 API 响应） |

### P2 — 监控（Observability）

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-O-01 | 分布式追踪 — OpenTelemetry 采集 Tracing 数据 | O 层 | 通过集成测试验证：工作流执行产生完整的 Trace 链路数据；Trace 数据可在 Langfuse 中查询 |
| F-O-02 | 指标采集 — 运行时 Metrics（调用量、延迟、错误率） | O 层 | 通过集成测试验证：指标数据按时采集并写入可观测后端；指标面板可展示历史趋势 |
| F-O-03 | 日志收集 — 结构化日志采集与存储 | O 层 | 通过集成测试验证：Agent 输出结构化日志；日志可按级别、时间范围、Agent ID 过滤查询。日志保留周期 >= 90 天，过期自动轮转至 O 层可观测性后端冷存储归档目录（自动归档并删除原始日志，归档文件保留期限 >= 365 天以备合规审计） |

> **说明**：F-O-03（O 层结构化日志）与 NFR-C-02（G 层审计日志保留周期）是两套独立的日志系统。F-O-03 记录 Agent 执行过程的结构化运行日志，用于调试与监控，存储于 O 层可观测性后端。NFR-C-02 记录安全审计事件的 Write-Once 链式日志（见 6.2 节审计日志记录实体），存储于 G 层审计存储，具备哈希链完整性保护。两套日志保留周期均 >= 90 天，但存储引擎、完整性保护级别和查询用途不同。

### P3 — 生命周期管理

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-LM-01 | Agent 包管理 — 基于 OCI Distribution（Harbor）管理 Agent 镜像 | 开源工具选型 | 通过集成测试验证：Agent 镜像可推送至 Harbor；支持标签管理 |
| F-LM-02 | 版本管理 — Agent 版本追踪与回滚 | L 层核心 | 通过集成测试验证：Agent 版本历史可查询；回滚至指定版本后功能正常 |
| F-LM-03 | 一键部署 — 从镜像仓库部署 Agent 到运行环境（一键部署指通过 CLI 命令或 Console UI 点击单次触发部署流程，触发后系统自动完成镜像拉取、沙盒分配、Agent 启动、健康检查等后续步骤，无需人工干预） | L 层核心 | 通过集成测试验证：选定版本后 Agent 自动部署至沙盒；部署完成后健康检查通过 |

### P4 — 市场（Agent Marketplace）

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-M-01 | Agent 发现 — 通过 Registry 搜索和浏览可用 Agent | L 层核心 / Agent 市场说明 | 通过集成测试验证：支持按名称、能力、类型搜索；搜索结果正确 |
| F-M-02 | Agent 分发 — 基于 OCI 镜像协议的分发与版本管理 | L 层核心 / Agent 市场说明 | 通过集成测试验证：Agent 镜像可按标准 OCI 协议分发；版本标签正确 |

### P5 — 计费（Billing）

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-O-04 | 成本追踪 — 统计每个 Agent 的资源消耗（Token 使用量、计算资源消耗），为用量统计提供原始数据。输入数据来源：O 层可观测性后端采集的 OpenTelemetry Tracing 和 Metrics 数据，经成本模型计算后输出各 Agent 的资源消耗明细。预期输出接口：按 Agent/时间范围聚合的成本数据查询接口，供 F-B-01（用量统计）消费。输出响应字段规范详见第 6.5 节成本追踪数据实体定义 | O 层 | 通过集成测试验证：成本追踪数据与 O 层采集的原始数据一致；成本查询接口返回正确聚合结果 |
| F-B-01 | 用量统计 — 基于 F-O-04（成本追踪）的输出数据统计每个 Agent 的资源消耗 | O 层 | 通过集成测试验证：用量统计数据与成本追踪原始数据一致；报表可按时间范围导出 |

> **说明**：F-O-04（成本追踪）与 F-B-01（用量统计）均不在 MVP 范围内（详见第 3 节基础 O 层定义和第 23 节 MVP 建议），两者优先级均为 P5，纳入后续迭代规划。

### 上下文管理（Context Management）

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-C-01 | 短期上下文管理 — 基于 System Prompt 渐进式披露、KV 缓存和滑动窗口机制管理当前会话的上下文窗口 | C 层 / 10.1 | 通过集成测试验证：System Prompt 渐进式披露按以下阶段生效——阶段 1（会话前 5 条消息）使用缩减版 System Prompt（仅含角色与基础指令），阶段 2（第 6-20 条消息）补充工具描述与上下文摘要，阶段 3（第 20 条后）注入完整上下文；每个阶段通过断言脚本校验 System Prompt 内容是否符合该阶段的预期规则；KV 缓存键与缓存中间表示正确关联；滑动窗口大小可配置（取值范围 [10, 200] 条消息，默认值 50）且按设置的消息条数截断 |
| F-C-02 | 中期会话状态管理 — 通过结构化笔记、工作文件引用和 Temporal 工作流状态引用实现跨会话的上下文保持 | C 层 / 10.1 | 通过集成测试验证：测试场景——Session A 写入结构化笔记 X（含关键结论"性能优化完成"与未完成任务"修复缓存 bug"），Session B 启动后读取笔记列表，断言 X 在结果中且"关键结论"和"未完成任务"字段完整；工作文件引用列表按 URI 格式可正确解析为实际文件路径；Temporal 工作流状态引用（workflow_id 格式）可从 Temporal Server 恢复对应状态 |
| F-C-03 | 长期持久化记忆 — 基于 Mem0 + Qdrant + Neo4j 实现长期记忆的存储、语义检索和知识图谱关系管理 | C 层 / 10.1 | 通过集成测试验证：长期记忆条目可写入和检索（写入条目后通过 session_id 查询，断言返回该条目且关键字段完整）；语义检索（向量相似度）使用测试数据集——写入 5 条主题不同的记忆条目（如"数据库优化"、"安全策略配置"、"部署流程"等），以与其中一条语义相近的查询词检索，断言返回该条且相似度评分 > 0.7；知识图谱关系查询使用测试三元组——写入三元组 (agent_A, knows, agent_B)，查询 agent_A 的关系，断言返回 agent_B |

### 评测（Verification & Evaluation）

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-V-01 | 评测五阶段闭环 — 支持定义（环境+成功标准）、执行前验证（沙盒/依赖/权限检查）、受控执行与追踪捕获、多级判断与故障归因、回归测试（失败记录→测试用例→自动迭代优化）五个阶段的评测流程 | V 层 / 11 | 通过集成测试验证：五阶段按顺序执行且每个阶段状态可追踪；回归测试用例由失败记录自动生成 |
| F-V-02 | 评测 Harness API — 提供评测任务启动、状态查询、执行轨迹获取和重新执行等接口 | V 层 / 11.2 | 通过集成测试验证：POST /api/v1/eval/run 正确启动评测任务并返回 eval_id；GET /api/v1/eval/{id} 返回正确的评测状态和结果；GET /api/v1/eval/{id}/trace 返回完整的执行轨迹；POST /api/v1/eval/{id}/rerun 支持选择性重新执行 |

### Console UI

| 编号 | 需求描述 | 对应章节 | 验收标准 / 验证方式 |
|------|---------|---------|-------------------|
| F-U-01 | Agent 管理界面 — 提供 Agent 注册（填写 Agent Card 字段提交注册）、列表分页展示（按名称/类型/状态筛选）、详情查看、启动/停止操作和版本管理（版本历史查看、版本回滚） | Console UI / 16 | 通过集成测试验证：Agent 注册表单提交后调用 Agent Registry API 成功注册；列表筛选按各维度正确过滤；版本回滚操作后 Agent 使用指定版本运行 |
| F-U-02 | 工作流监控界面 — 提供工作流列表分页展示（按状态/Agent/时间范围筛选）、工作流详情查看（执行轨迹/当前 Activity/Event History）、人工审批节点操作（批准/拒绝）和运行控制（终止/重试） | Console UI / 16 | 通过集成测试验证：工作流列表按各条件筛选正确；审批节点批准后工作流继续执行；终止/重试操作正确下发至 Temporal |
| F-U-03 | 安全策略配置界面 — 提供宪法规则 YAML 文件在线编辑与生效、OPA 策略上传与启用/禁用、审计日志按时间/Agent/动作类型筛选查询 | Console UI / 16 | 通过集成测试验证：宪法规则编辑保存后 60 秒内生效；OPA 策略禁用后越权操作不再被拦截；审计日志筛选结果与查询条件一致 |
| F-U-04 | 监控面板界面 — 提供 Agent 调用量、延迟 P95、错误率趋势图展示，以及按 Agent/工作流维度的成本看板和告警管理（告警规则配置、告警历史查看） | Console UI / 16 | 通过集成测试验证：指标趋势图数据与 O 层采集数据一致；成本看板数据可正确聚合展示；告警规则配置后触发的告警出现在告警历史中 |
| F-U-05 | CLI 接口 — 提供命令行管理能力，覆盖 Agent 管理（注册/列表/详情/启停）、工作流监控（列表/详情/重试/终止）、安全策略配置（宪法规则应用/审计日志查询）和监控指标查看等主要管理操作。豁免项包括可视化图表交互式查看、拖拽式操作等需图形界面支持的功能。命令格式统一为 `harness <资源类型> <操作> [参数...] [--flags]` | Console UI / 16（CLI 接口） | 通过集成测试验证：CLI 命令可执行覆盖范围内的操作并正确返回结果；命令格式符合统一规范 |

## 6. 数据模型定义

### 6.1 Agent Card 字段规范

基于 A2A Agent Card 格式，每个注册 Agent 的字段定义如下：

| 字段 | 类型 | 必填 | 描述 | 约束 |
|------|------|------|------|------|
| agent | string | 否 | Agent 唯一标识符。用户提供时格式为 {name}@{version}；不含此字段时由平台自动生成，自动生成格式为 {type}-{uuid-short}@{auto}，其中 {type} 取自已注册上下文中的 Agent 类型配置文件的 agent_type.name 字段值（详见第 20 节 Agent 类型扩展机制） | 全局唯一，长度 <= 128 字符 |
| capabilities | string[] | 是 | Agent 能力标签列表 | 每项长度 <= 64 字符，最多 20 项 |
| auth | string | 是 | SPIFFE 身份标识，格式为 spiffe://{namespace}/{path} | 与 SPIFFE/SPIRE 分配的身份一致 |
| rate_limit | integer | 是 | API 调用速率限制（次/秒） | 取值范围 [1, 10000] |
| endpoints.a2a | string | 是 | A2A 协议端点 URL | 有效的 URI 格式 |
| endpoints.mcp | string | 否 | MCP 协议端点 URL，Agent 提供工具能力时必填 | 有效的 URI 格式 |
| health | string | 是 | 健康检查端点路径 | 以 / 开头 |
| runtime | string | 是 | Agent 运行框架标识 | 枚举值：langgraph、custom |
| version | string | 是 | Agent 语义化版本号 | 符合 SemVer 规范（x.y.z） |
| retry_config | object | 否 | 重试配置，含 max_retries（最大重试次数）、backoff_interval（退避间隔，秒）、timeout（超时时间，秒）。未配置时使用当前 Agent 所属 Agent 类型配置文件的默认重试配置（详见第 20 节 agent_type schema） | 参数约束：max_retries 取值范围 [0, 10]；backoff_interval 取值范围 [1, 3600]，默认值 60；timeout 取值范围 [1, 86400]，默认值 600 |

### 6.2 审计日志记录实体

| 字段 | 类型 | 描述 |
|------|------|------|
| log_id | string | 日志记录唯一标识（UUID） |
| timestamp | datetime | 事件发生时间（UTC） |
| agent_id | string | 触发事件的 Agent 标识 |
| workflow_id | string | 关联的工作流标识（可选） |
| action | string | 事件动作类型：invoke、decision、reject、approve |
| hook_point | string | 触发拦截点：input_before、exec_before、return_after、critical_action_before（可选） |
| policy_result | string | 策略评估结果：allowed、denied、redacted（可选） |
| payload_hash | string | 事件内容的 SHA-256 哈希值，用于完整性校验 |
| previous_hash | string | 上一条日志记录的哈希值，形成哈希链防篡改 |
| tenant_id | string | 所属租户标识 |

### 6.3 工作流状态实体

| 字段 | 类型 | 描述 |
|------|------|------|
| workflow_id | string | 工作流唯一标识 |
| status | string | 状态枚举：running、completed、failed、compensating、compensated、timed_out |
| agent_ids | string[] | 参与 Agent 列表 |
| start_time | datetime | 开始时间 |
| last_update | datetime | 最后更新时间 |
| event_history | string[] | Temporal Event History 引用列表 |
| current_activity | string | 当前执行的活动标识 |
| error_info | string | 错误信息（状态为 failed 时） |

### 6.4 策略规则实体

本实体定义 OPA 策略引擎的数据模型，专用于 G 层第二道防线（OPA 策略引擎）的规则持久化。宪法规则（G 层第三道防线）使用独立的 YAML 规则配置表示（详见第 9 节宪法规则配置示例），两者以体系上独立的机制运行：OPA 策略基于 Rego 语法进行访问控制判断，宪法规则基于 YAML 声明式规则进行内容安全拦截。本实体的 hook_point 命名约定与宪法规则拦截点一致，但条件表达式语法不同（Rego vs YAML），互不冲突。

| 字段 | 类型 | 描述 |
|------|------|------|
| rule_id | string | 规则唯一标识 |
| hook_point | string | OPA 策略拦截点枚举：tool_call.before、llm_input.before、agent_to_agent（命名约定与宪法规则拦截点一致） |
| condition | string | 规则条件表达式（OPA Rego 语法） |
| action | string | 触发动作枚举：REJECT、REDACT、ALERT、APPROVE |
| priority | integer | 规则优先级，数值越小优先级越高 |
| enabled | boolean | 是否启用 |
| tenant_id | string | 所属租户标识 |
| created_at | datetime | 创建时间 |

### 6.5 沙盒相关实体定义

#### SandboxPool（沙盒池）

| 字段 | 类型 | 描述 |
|------|------|------|
| pool_id | string | 沙盒池唯一标识 |
| pool_type | string | 沙盒类型枚举：container、microvm、browser |
| target_capacity | integer | 池目标容量，弹性伸缩后自动更新 |
| allocated | integer | 当前已分配实例数 |
| available | integer | 当前可用（空闲）实例数 |
| tenant_id | string | 所属租户标识（可选，为空表示全局池） |
| status | string | 池状态枚举：active、scaling、degraded |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 最后更新时间 |

#### SandboxInstance（沙盒实例）

| 字段 | 类型 | 描述 |
|------|------|------|
| instance_id | string | 沙盒实例唯一标识 |
| pool_id | string | 所属沙盒池标识 |
| agent_id | string | 当前分配的 Agent 标识（可选，空闲时为 null） |
| status | string | 实例状态枚举：creating、ready、allocated、idle、destroying、failed |
| sandbox_type | string | 沙盒类型枚举：container、microvm、browser |
| resource_limits | json | 资源限制，含 cpu 和 memory 字段 |
| started_at | datetime | 实例创建时间 |
| last_activity | datetime | 最后活动时间（用于空闲超时判断） |
| tenant_id | string | 所属租户标识（可选） |

### 6.6 租户实体（Tenant）

| 字段 | 类型 | 描述 |
|------|------|------|
| tenant_id | string | 租户唯一标识 |
| name | string | 租户名称 |
| namespace | string | SPIFFE 命名空间标识，格式为 tenant/{tenant_id} |
| config | json | 租户配置，含配额限制（max_agents、max_workflows）、默认策略配置等 |
| status | string | 租户状态枚举：active、suspended、disabled |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 最后更新时间 |

### 6.7 成本追踪数据实体

本实体定义 F-O-04（成本追踪）按 Agent/时间范围聚合的成本数据查询接口的输出响应模型。

| 字段 | 类型 | 描述 |
|------|------|------|
| agent_id | string | Agent 标识 |
| time_range_start | datetime | 聚合起始时间（UTC） |
| time_range_end | datetime | 聚合结束时间（UTC） |
| token_consumption | json | Token 消耗明细，含 { "input_tokens": integer, "output_tokens": integer, "total_tokens": integer } |
| compute_cost | json | 计算资源消耗，含 { "cpu_time_seconds": float, "memory_mb_seconds": float, "sandbox_runtime_seconds": float } |
| total_cost | float | 总成本（按平台成本模型计算后的归一化值） |
| breakdown | json[] | 成本分解明细列表，每项含 { "category": string（如 "llm_inference"、"sandbox_runtime"、"tool_calls"）, "cost": float, "details": object } |
| currency | string | 成本货币单位（默认 "USD"） |

## 7. 整体架构

架构图按 ETCLOVG 顺序（E→T→C→L→O→V→G）从上至下排列，体现从执行基础到全局治理的层次递进关系。

```
┌──────────────────────────────────────────────────────────────────────┐
│                          API Gateway / Console                        │
│                     (统一的 Web UI + CLI + API)                       │
└──────────────────────────────────────────────────────────────────────┘
                                      │
┌──────────────────────────────────────────────────────────────────────┐
│  E — Execution & Sandbox                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ 容器运行时(Docker) │  │  microVM (E2B)   │  │  Computer Use      │  │
│  │ + 沙盒池管理       │  │ 高隔离场景       │  │  GUI 操作场景      │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  T — Tool Interface                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │   MCP Servers     │  │   A2A Protocol   │  │   Function Calling  │  │
│  │  (工具/数据接入)   │  │ (Agent 间通信)   │  │  (LLM 原生)        │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  C — Context Management                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ 短期上下文窗口     │  │ 中期会话状态      │  │ 长期持久化记忆     │  │
│  │ (System Prompt    │  │ (结构化笔记 +    │  │ (Mem0 + 向量库 +   │  │
│  │  渐进式披露)       │  │  工作文件)       │  │  图数据库)         │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  L — Lifecycle & Orchestration                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │   Temporal        │  │   Agent Registry  │  │   Agent 市场      │  │
│  │   - 跨Agent工作流  │  │   - A2A Agent Card│  │   - OCI 镜像/包   │  │
│  │   - Saga 补偿     │  │   - 服务发现      │  │   - 版本管理       │  │
│  │   - 人工审批(Signal)│  │   - 健康检查      │  │   - 一键部署       │  │
│  │   - 定时/重试      │  │                  │  │                    │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  O — Observability                                                   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  OpenTelemetry → Langfuse/Arize Phoenix                        │  │
│  │  (Tracing + Metrics + Logs + 成本追踪)                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  V — Verification & Evaluation                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 评测沙盒: 执行前验证 → 执行中追踪 → 多级判断 → 回归测试库       │  │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  G — Governance & Security Layer                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │SPIFFE/   │ │   OPA    │ │   mTLS   │ │ 宪法规则  │ │ 审计日志   │  │
│  │SPIRE ID  │ │  策略引擎 │ │  传输加密 │ │声明式配置 │ │ 不可篡改   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  钩子: [输入前 → 执行前 → 返回后 → 关键动作前]                      │
└──────────────────────────────────────────────────────────────────────┘
```

## 8. L 层核心：编排模型

### Temporal + LangGraph 双层架构

```
┌─────────────────────────────────────────────┐
│  Temporal (编排层)                            │
│  跨 Agent 工作流、Saga、重试、人工审批           │
│  工作流状态 100% 持久化，宕机零丢失              │
├─────────────────────────────────────────────┤
│  LangGraph (Agent 内部逻辑)                   │
│  每个 Agent 内部的 ReAct 循环、Tool Calling    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │ AI Agent│ │Monitor  │ │  RPA    │        │
│  │(LangG.) │ │(LangG.) │ │(LangG.) │        │
│  └─────────┘ └─────────┘ └─────────┘        │
├─────────────────────────────────────────────┤
│  MCP Servers / A2A Protocol                   │
└─────────────────────────────────────────────┘
```

- **Temporal** 管 Agent **之间**的编排（跨 Agent 工作流、人工审批、失败补偿）
- **LangGraph** 管单个 Agent **内部**的推理循环（ReAct、Tool Calling、子图路由）

### Agent Registry（A2A Agent Card）

字段规范详见 [6.1 Agent Card 字段规范](#61-agent-card-字段规范)。以下为注册示例：

```
{
  "agent": "hr-candidate-sourcer@v2",
  "capabilities": ["search", "parse", "rank"],
  "auth": "spiffe://prod/hr/sourcer",
  "rate_limit": 100,
  "endpoints": {
    "a2a": "a2a://registry/hr/sourcer",
    "mcp": "mcp://mcp-server/hr"
  },
  "health": "/healthz",
  "runtime": "langgraph",
  "version": "2.1.0"
}
```

### Agent 市场说明

Agent 市场作为 L 层 Agent Registry 的扩展能力，提供 Agent 的分发与发现功能：

- **OCI 镜像/包管理**：基于 Harbor 存储 Agent 运行时包，支持版本标记（tag）和清单（manifest）
- **版本管理**：每 Agent 支持语义化版本号（SemVer），Registry 维护版本历史
- **一键部署**：通过 Registry 将指定版本的 Agent 部署到运行环境

### 编排数据流

```
用户/系统触发任务
  → Temporal Client.StartWorkflow("RecruitmentWF", {jobId})
  → Temporal Server 持久化 Workflow 状态到 DB
  → Workflow 执行 Activity:
    Activity 1: Registry.Lookup("candidate-sourcer")
    Activity 2: AgentA2A.Invoke(sourcer, {criteria})
        └─ Agent 内部: LangGraph ReAct 循环
           思考 → 调用 MCP Tool → 观察 → 思考...
    Activity 3: HumanApproval.Signal{timeout: 24h}
        └─ 等待 Signal / 超时 → 回滚
    Activity 4: Compensation(失败则撤销操作)
```

## 9. G 层：安全治理 — 四道防线

### 第一道：身份与传输层

SPIFFE/SPIRE 为每个 Agent 和工作流分配唯一身份：

- `spiffe://prod/agent/hr-sourcer`
- `spiffe://prod/workflow/recruitment-abc123`
- mTLS 双向认证，所有通信加密

### 第二道：策略与权限

- **OPA** (Open Policy Agent): 策略引擎，如"只有 HR 组的 Agent 可以访问简历数据库"
- **OpenFGA**: 关系型权限，如"用户 A 可以管理 Agent X"

### 第三道：声明式宪法

```yaml
# constitution.yaml
rules:
  - on: "tool_call.before"
    if: "tool.name == 'delete_production_db'"
    then: "REJECT"
  - on: "llm_input.before"
    if: "contains(input, 'password')"
    then: "REDACT"
  - on: "agent_to_agent"
    if: "source.level < target.level"
    then: "REJECT"
```

合规团队直接改配置文件，无需修改代码。

### 第四道：生命周期钩子 + 审计日志

| 拦截点 | 时机 | 作用 |
|--------|------|------|
| 输入前 | LLM 接收消息前 | 防提示词注入 |
| 执行前 | 工具调用前 | 防越权 |
| 返回后 | 工具返回结果后 | 污点追踪 |
| 关键动作前 | 敏感操作 | 人工审批 |

"关键动作前"拦截点的触发条件判定标准：满足以下任一项的操作即视为"关键动作"：(1)涉及资源删除（如删除 Agent、工作流、沙盒池）；(2)涉及数据导出或外发（如导出审计日志、导出 Agent 数据到外部系统）；(3)涉及跨租户操作（如跨租户 Agent 间通信、跨租户数据访问）；(4)单次操作涉及的费用超过用户配置的费用阈值。

审计日志：Write-Once 不可篡改，记录每次调用/决策/拒绝。

宪法规则（第三道）与生命周期钩子（第四道）的执行顺序：两者拦截点集合不同但存在交集——当同一事件同时触发宪法规则和生命周期钩子时，宪法规则先于生命周期钩子执行。宪法规则评估结果为 REJECT 时直接拒绝该操作，不触发后续生命周期钩子；评估结果为 REDACT/ALERT/APPROVE 时，修改后的请求继续进入生命周期钩子处理。REDACT 动作对请求内容中匹配敏感模式的数据进行脱敏处理（将敏感字段值替换为 [REDACTED] 标记），脱敏后的请求保持原始数据结构（JSON/YAML/文本格式不变）传递至钩子。两套机制的结果组合规则为：宪法规则 REJECT 优先级最高，覆盖钩子的任何后续处理结果；宪法规则非 REJECT 时，以生命周期钩子的最终输出为准。

### 安全验证标准

- **四道防线验证**：需通过年度第三方渗透测试验证。通过标准：未发现高危（Critical/High）漏洞；发现的 Medium 级别漏洞数量不超过 3 个且在 30 天内修复；Low 级别漏洞评估后确认不影响生产安全。
- **宪法规则引擎审核**：需通过合规团队审核，覆盖宪法规则定义的 3 个拦截点（tool_call.before、llm_input.before、agent_to_agent）。审核检查清单包括：(1) 每个拦截点至少有一条生效规则；(2) 所有规则的条件表达式可正确解析和执行；(3) 拒绝类规则的动作符合最小权限原则；(4) 规则变更需经审批流程记录。
- **生命周期钩子验证**：需通过集成测试验证全部 4 个拦截点（输入前/input_before、执行前/exec_before、返回后/return_after、关键动作前/critical_action_before）的正确触发，验证每个钩子函数在正确时机被调用、异常时输出明确错误信息。
- **审计日志完整性验证**：Write-Once 机制需通过哈希链完整性测试验证，测试方法：构造连续 N 条日志记录，验证每条记录的 previous_hash 与上一条记录的 payload_hash 一致；尝试修改已写入的记录后校验失败。

## 10. C 层：上下文管理 — 三级记忆架构

| 级别 | 类比 | 技术实现 | 生命周期 |
|------|------|---------|---------|
| 短期 | 内存 | System Prompt 优化 + KV 缓存 + 窗口滑动 | 会话进行中 |
| 中期 | 休眠文件 | 结构化笔记 + 工作文件 + Temporal 状态持久化 | 跨会话 |
| 长期 | 硬盘 | Mem0 + Qdrant + Neo4j | 跨任务 |

### 10.1 上下文数据实体

| 字段 | 类型 | 描述 | 所属层级 |
|------|------|------|---------|
| session_id | string | 会话唯一标识 | 短期/中期 |
| agent_id | string | 关联 Agent 标识 | 短期/中期/长期 |
| context_window | json | 当前会话的 System Prompt 与消息列表，含 Token 计数 | 短期 |
| kv_cache_key | string | KV 缓存键，关联缓存中间表示 | 短期 |
| sliding_window_size | integer | 滑动窗口大小，单位：消息条数 | 短期 |
| structured_notes | json | 跨会话的结构化笔记，含关键结论与未完成任务 | 中期 |
| working_files | string[] | 中期工作文件引用列表 | 中期 |
| temporal_state_ref | string | Temporal 工作流状态引用 | 中期 |
| long_term_memory | json | 长期记忆条目，含观察摘要、反思记录与检索元数据 | 长期 |
| memory_embedding | float[] | 长期记忆的向量嵌入，用于语义检索 | 长期 |
| memory_graph_relations | json | 长期记忆间的知识图谱关系 | 长期 |
| data_classification_labels | string[] | 数据的分类标签列表，支持按标签（如 personal_data、anonymized、aggregated）进行数据隔离 | 长期 |

### 10.2 C 层非功能需求

C 层非功能需求详见第 13 节非功能需求表，其中与 C 层直接相关的 NFR 条目包括 NFR-P-03（P95 端到端响应延迟，含上下文检索时间）、NFR-C-01（工作流状态持久化）、NFR-C-03（长期记忆存储容量，单 Agent 长期记忆条目数 >= 10,000 条，超出后按 LRU 策略淘汰）、NFR-P-06（长期记忆检索延迟 P95，语义检索 P95 <= 200ms）。C 层补充非功能约束如下：

- **长期记忆存储容量**：单 Agent 长期记忆条目数 >= 10,000 条，超出后按最近最少使用（LRU）策略淘汰。验证方式：压力测试写入 10,000+ 记忆条目，验证检索功能正常。
- **长期记忆检索延迟 P95**：语义检索（向量相似度）P95 <= 200ms。验证方式：负载测试持续检索，记录 P95 延迟。

## 11. V 层：评测 — 五阶段闭环

1. **定义** — 环境 + 成功标准
2. **执行前验证** — 沙盒/依赖/权限初始化检查
3. **受控执行 + 追踪捕获** — 完整记录运行轨迹
4. **多级判断 + 故障归因** — 结果 + 工具调用合理性 + 裁判模型偏见评估
5. **回归测试** — 失败记录 → 测试用例 → Harness 自动迭代优化

### 11.1 评测数据实体

| 字段 | 类型 | 描述 |
|------|------|------|
| eval_id | string | 评测任务唯一标识 |
| agent_id | string | 被评测 Agent 标识 |
| eval_stage | string | 所属阶段枚举：define、pre_validate、execute、judge、regression |
| environment_spec | json | 评测环境定义，含沙盒类型、依赖列表、权限声明 |
| success_criteria | json | 成功标准定义，含结果准确率阈值、工具调用合规性要求 |
| execution_trace | json | 受控执行的完整运行轨迹记录，含时间戳与状态快照 |
| judgment_result | json | 多级判断结果，含最终结论、工具合理性评分、裁判模型偏差评估 |
| regression_test_cases | json[] | 回归测试用例列表，由失败记录自动生成 |

### 11.2 评测 Harness 接口

评测 Harness 提供以下接口供外部系统调用：

| 接口 | 说明 | 请求参数 | 响应 |
|------|------|---------|------|
| POST /api/v1/eval/run | 启动评测任务 | { agent_id, environment_spec, success_criteria } | { eval_id, status: "running" } |
| GET /api/v1/eval/{id} | 查询评测状态与结果 | 无 | { eval_id, status, 各阶段状态与结果 } |
| GET /api/v1/eval/{id}/trace | 获取执行轨迹 | 无 | { eval_id, execution_trace } |
| POST /api/v1/eval/{id}/rerun | 重新执行评测 | { regression_only?: boolean } | { eval_id, status } |

## 12. 开源工具选型

| 层 | 组件 | 推荐工具 | 说明 |
|----|------|---------|------|
| E | 沙盒 | E2B, Daytona, Docker, Firecracker | microVM 高隔离（每个实例独占内核，硬件级虚拟化隔离）/ Docker 轻量（共享宿主机内核，进程级隔离，启动快） |
| E | 沙盒抽象 | 自研薄层 | 统一多沙盒接口 |
| T | 工具协议 | MCP SDK (Anthropic) | Agent↔工具 标准 |
| T | Agent 通信 | A2A Protocol (Google) | Agent↔Agent 标准 |
| C | 短期上下文 | LangGraph | 内部 ReAct 循环 |
| C | 长期记忆 | Mem0 + Qdrant + Neo4j | 观察→反思→检索 |
| L | 编排引擎 | **Temporal** | 核心选型 |
| L | Agent 注册 | 自研 Registry | 基于 A2A Agent Card |
| L | 包管理 | OCI Distribution (Harbor) | Agent 镜像仓库 |
| O | 可观测 | OpenTelemetry + Langfuse | Tracing + 成本 |
| V | 评测 | 自研框架 | 五阶段闭环 |
| G | 身份 | SPIRE/SPIFFE (CNCF) | 工作负载身份 |
| G | 策略 | OPA + OpenFGA | 权限 + 关系 |
| G | 审计 | 自研 | Write-Once 审计 |
| G | 宪法规则 | 自研声明式配置 | YAML 规则引擎 |

## 13. 非功能需求

| 维度 | 编号 | 描述 | 目标值 | 验证方式 |
|------|------|------|--------|---------|
| 性能 | NFR-P-01 | 并发 Agent 会话数 | >= 500 个 Agent 同时运行 | 负载压测：模拟 500+ Agent 并发注册和心跳，验证系统稳定运行 |
| 性能 | NFR-P-02 | 并发工作流数 | >= 1000 | Temporal 性能测试：启动 1000+ 并行工作流，验证无超时或丢失 |
| 性能 | NFR-P-03 | P95 平台中间件链路延迟（不含 Agent 内部 LLM 推理时间），链路范围定义：API Gateway 接收请求 → L 层编排 → G 层钩子链 → O 层数据采集 → API Gateway 返回响应，排除 Agent 内部 LLM 推理与工具调用耗时 | <= 500ms | 持续性能监控：在 API Gateway 请求入口埋点记录请求到达时间，在 Agent 调用 LLM 前后埋点记录推理起止时间，在 API Gateway 返回响应时记录响应时间，计算 API Gateway 往返总延迟减去 Agent 端 LLM 推理与工具调用耗时，取 P95 百分位值 |
| 性能 | NFR-P-04 | 单日任务处理量 | >= 10 万次 | 吞吐量压测：持续运行 24 小时模拟生产负载 |
| 性能 | NFR-P-05 | 单节点资源消耗上限 | 8vCPU / 32GB RAM | 资源监控告警：超出阈值触发告警 |
| 性能 | NFR-P-06 | C 层长期记忆检索延迟 P95（语义检索，向量相似度） | <= 200ms | 负载测试：持续进行长期记忆语义检索，记录 P95 延迟 |
| 性能 | NFR-P-07 | C 层长期记忆存储容量 | 单 Agent >= 10,000 条，超出后按 LRU 策略淘汰 | 压力测试：写入 10,000+ 记忆条目，验证检索功能正常 |
| 可用性 | NFR-A-01 | 平台可用性 SLA | >= 99.9%（月度） | 监控：计算月度 uptime 百分比 |
| 可用性 | NFR-A-02 | 恢复时间目标（RTO）— 控制面热备切换（API Gateway、G 层策略引擎） | <= 5 秒 | 故障注入测试：模拟控制面主节点宕机，测量从检测到热备切换完成的时间 |
| 可用性 | NFR-A-03 | 恢复时间目标（RTO）— 灾难恢复（跨区域） | <= 5 分钟 | 故障注入测试：模拟全区域不可用，测量跨区域恢复时间 |
| 可用性 | NFR-A-04 | 恢复点目标（RPO） | 0（基于 Temporal Durable Execution 语义，限定于单集群内持久化层故障场景，包含该集群内所有节点同时故障；跨集群故障转移不在此承诺范围内） | 故障注入测试：启动工作流 → 写入检查点 → 通过 Chaos Engineering 模拟集群所有节点同时故障（强制终止全部 Temporal 节点进程） → 重启集群 → 验证工作流从最后 await 点继续执行 |
| 可用性 | NFR-A-05 | 非 Temporal 持久化组件备份与恢复 — C 层长期记忆存储（Neo4j + Qdrant）、O 层可观测性后端（Langfuse）、L 层 Agent Registry 等关键持久化组件的基础备份策略 | RTO <= 30 分钟，RPO <= 15 分钟（基于持久化组件自身快照或备份工具实现） | 恢复演练测试：模拟持久化组件数据损坏，从备份恢复后验证数据完整性和业务功能正常 |
| 容量 | NFR-C-01 | 工作流状态持久化 | 100% 持久化 | 同 RPO 验证方法 |
| 容量 | NFR-C-02 | 审计日志保留周期 | >= 90 天 | 监控告警：日志存储空间达到 90%（约 81 天写入量）触发告警；超期日志自动轮转 |
| 监控 | NFR-M-01 | 控制面组件健康检查与状态监控 — 对 Temporal Server、OPA 策略引擎、Agent Registry、C 层 Neo4j 数据库、C 层 Qdrant 向量库、G 层审计日志存储等控制面组件提供健康检查端点与状态监控指标（含组件存活状态、响应延迟 P99、资源利用率） | 每个控制面组件暴露 /healthz 健康检查端点；健康检查间隔可配置，取值范围 [10, 300] 秒，默认值 30 秒；状态异常触发告警 | 集成测试验证：每个组件的 /healthz 端点返回正确状态码；模拟组件故障后告警正确触发 |
| 安全 | NFR-S-01 | 安全防线验证频次 | 年度第三方渗透测试 | 安全审计报告：以年度第三方渗透测试报告为判定依据，报告应覆盖四道防线（身份与传输、策略与权限、宪法规则、钩子与审计日志），报告中所有漏洞均已按第 9 节安全验证标准分类和评级。通过标准：未发现高危（Critical/High）漏洞；发现的 Medium 级别漏洞数量不超过 3 个且在 30 天内修复；Low 级别漏洞评估后确认不影响生产安全 |
| 安全 | NFR-S-02 | 宪法规则审核 | 合规团队审核，覆盖全部拦截点 | 合规审核报告：以合规团队签署的审核报告为判定依据，报告应确认第 9 节安全验证标准中宪法规则引擎审核检查清单的 4 项要求（每个拦截点至少一条生效规则、所有规则条件表达式可正确解析和执行、拒绝类规则符合最小权限原则、规则变更经审批流程记录）均已满足 |
| 扩展性 | NFR-E-01 | Temporal 水平扩展维度 | Worker 节点数、数据库连接池、任务队列分区数 | 扩展测试：逐维增加资源配置并验证吞吐量线性增长，线性回归拟合优度 R² >= 0.90 |
| 扩展性 | NFR-E-02 | 沙盒池弹性伸缩 | 按 Agent 负载自动扩缩。触发条件：沙盒池已分配实例数占池总容量的比例 > 80% 持续 60 秒触发扩容，该比例 < 30% 持续 120 秒触发缩容；单次扩缩步长：+/- 20% 当前容量；冷却期：扩容后至少 180 秒不触发新扩容，缩容后至少 300 秒不触发新缩容。其中"池总容量"指沙盒池当前配置的目标容量（target_capacity），每次扩缩后该值随之更新。thrashing 判定标准：在任意 5 分钟内扩缩事件总次数超过 3 次判定为 thrashing，触发 thrashing 后自动暂停弹性伸缩操作 600 秒 | 负载压测：模拟负载波动，验证沙盒池按以上条件自动扩缩，且在任意 5 分钟内扩缩事件总次数不超过 3 次 |

## 14. API 规范

### API Gateway 规格

| 维度 | 规格说明 |
|------|---------|
| 路由规则 | 按路径前缀路由至后端服务：/api/v1/agents/* 路由至 Agent Registry 服务，/api/v1/eval/* 路由至评测 Harness 服务，/api/v1/workflows/* 路由至 Temporal 工作流管理服务，/api/v1/sandbox-pools/* 路由至沙盒池管理服务，/api/v1/policies/* 及 /api/v1/constitution 路由至策略引擎服务，/api/v1/audit-logs/* 路由至审计日志查询服务，/api/v1/agent-types/* 路由至 Agent 类型管理服务，Console UI 静态资源与 WebSocket 连接由 Gateway 直连处理 |
| 认证集成 | 对接 G 层 SPIFFE 身份系统，验证请求携带的 SPIFFE SVID 凭证有效性，验证通过后将身份信息注入请求上下文转发至后端服务。此外，针对 CLI 和 Console UI 的人类用户场景，集成 OIDC/OAuth2 认证方案：CLI 使用 Access Token 进行身份认证（通过 `harness auth login` 命令获取），Console UI 使用 Session Cookie 进行身份认证（通过浏览器 OAuth2 授权码流程获取）。Gateway 根据请求来源路由判断认证方式——内部 Agent 间通信使用 SPIFFE SVID 验证，CLI 请求使用 Access Token 验证，Console UI 请求使用 Session Cookie 验证 |
| 限流配置 | 全局默认限流 1000 请求/秒，超限返回 429 状态码及 RATE_LIMITED 错误码，具体限流策略由 OPA 策略引擎定义 |

### Agent Registry API

基于 A2A Agent Card 格式，注册与发现 Agent：

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/v1/agents | 列出所有已注册 Agent | 无 | { "agents": AgentCard[], "total": integer, "page": integer, "page_size": integer } |
| GET | /api/v1/agents/{id} | 查询单个 Agent 详情 | 无 | AgentCard（详见 6.1 节） |
| POST | /api/v1/agents | 注册新 Agent | AgentCard（不含 agent 字段则为自动生成） | { "agent": string, "status": "registered", "created_at": datetime } |
| PUT | /api/v1/agents/{id} | 更新 Agent 配置 | AgentCard 部分字段 | { "agent": string, "status": "updated", "updated_at": datetime } |
| DELETE | /api/v1/agents/{id} | 注销 Agent | 无 | { "agent": string, "status": "deleted" } |
| GET | /api/v1/agents/{id}/health | 健康检查 | 无 | { "status": "healthy"|"degraded"|"unhealthy", "last_seen": datetime, "metrics": { "uptime": integer, "error_rate": float } } |
| POST | /api/v1/agents/{id}/start | 启动 Agent | 无 | { "agent": string, "status": "starting", "started_at": datetime } |
| POST | /api/v1/agents/{id}/stop | 停止 Agent | 无 | { "agent": string, "status": "stopping", "stopped_at": datetime } |

通用响应格式：

| 场景 | HTTP 状态码 | 响应体 |
|------|-----------|--------|
| 成功 | 200 | 见上表响应体 |
| 创建成功 | 201 | { "agent": string, "status": "registered", "created_at": datetime } |
| 请求参数错误 | 400 | { "error": { "code": "INVALID_REQUEST", "message": "描述信息", "details": {} } } |
| 未授权 | 401 | { "error": { "code": "UNAUTHORIZED", "message": "描述信息" } } |
| 权限不足 | 403 | { "error": { "code": "FORBIDDEN", "message": "描述信息" } } |
| 资源不存在 | 404 | { "error": { "code": "NOT_FOUND", "message": "描述信息" } } |
| 资源冲突 | 409 | { "error": { "code": "CONFLICT", "message": "资源已存在" } } |
| 请求频率超限 | 429 | { "error": { "code": "RATE_LIMITED", "message": "描述信息", "retry_after": integer } } |
| 服务端错误 | 500 | { "error": { "code": "INTERNAL_ERROR", "message": "描述信息" } } |

> **说明**：审计日志写入失败的场景不改变业务 API 的 HTTP 响应码。临时性写入失败（非存储满）触发告警，业务 API 仍正常响应；存储空间写满时，审计子系统内部返回 AUDIT_LOG_FULL 错误码，业务 API 仍正常返回 200/201，业务操作以降级模式继续执行（跳过审计写入），审计失败信息通过告警通道通知运维人员。POST /api/v1/agents 注册接口在重复注册场景下返回 HTTP 409 状态码及 CONFLICT 错误码，响应体格式为 { "error": { "code": "CONFLICT", "message": "Agent 已存在" } }。

### Agent Type Management API

Agent 类型注册与管理，支持第 20 节定义的 YAML 配置文件注册：

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/v1/agent-types | 列出所有已注册的 Agent 类型 | 无 | { "agent_types": AgentTypeRegistration[], "total": integer } |
| GET | /api/v1/agent-types/{name} | 查询指定 Agent 类型详情 | 无 | AgentTypeRegistration（详见第 20 节 agent_type schema） |
| POST | /api/v1/agent-types | 注册新 Agent 类型 | 第 20 节定义的 YAML 配置文件内容（含 agent_type 字段定义） | { "name": string, "status": "registered", "created_at": datetime } |
| DELETE | /api/v1/agent-types/{name} | 删除 Agent 类型 | 无 | { "name": string, "status": "deleted" } |

### 工作流管理 API

工作流管理 API 对接 L 层 Temporal 编排引擎，提供工作流查询与控制能力：

| 方法 | 路径 | 说明 | 请求参数 | 响应体 |
|------|------|------|---------|--------|
| GET | /api/v1/workflows | 列出工作流 | 查询参数：status(状态筛选，可选值 running|completed|failed|timed_out)、agent_id、start_time、end_time、page、page_size | { "workflows": WorkflowState[], "total": integer, "page": integer, "page_size": integer } |
| POST | /api/v1/workflows | 启动新工作流 | { "workflow_type": string, "parameters": object, "retry_config"?: { "max_retries"?: integer, "backoff_interval"?: integer, "timeout"?: integer } } | { "workflow_id": string, "status": "running", "created_at": datetime } |
| GET | /api/v1/workflows/{id} | 查询工作流详情 | 无 | WorkflowState（详见 6.3 节），含当前 Activity 及 Event History 引用列表 |
| POST | /api/v1/workflows/{id}/signal | 发送人工审批 Signal | { "signal_type": "approve"|"reject", "payload": {} } | { "workflow_id": string, "status": "signal_sent", "timestamp": datetime } |
| POST | /api/v1/workflows/{id}/retry | 重试工作流 | 无 | { "workflow_id": string, "status": "running" } |
| POST | /api/v1/workflows/{id}/terminate | 终止工作流 | { "reason": string }（可选） | { "workflow_id": string, "status": "terminated", "reason": string } |

### 沙盒池管理 API

沙盒池管理 API 对接 E 层沙盒抽象层，提供沙盒池的查询与控制能力：

| 方法 | 路径 | 说明 | 请求参数 | 响应体 |
|------|------|------|---------|--------|
| GET | /api/v1/sandbox-pools | 列出所有沙盒池 | 查询参数：type(container|microvm|browser) | { "pools": SandboxPool[], "total": integer } |
| GET | /api/v1/sandbox-pools/{type} | 查询指定类型沙盒池详情 | 无 | { "pool_type": string, "capacity": integer, "allocated": integer, "available": integer, "instances": SandboxInstance[] } |
| POST | /api/v1/sandbox-pools/{type}/scale | 手动扩缩沙盒池 | { "target_capacity": integer } | { "pool_type": string, "capacity": integer, "status": "scaling" } |

### 策略管理 API

OPA 策略管理（基于 Rego 语法，详见 6.4 节策略规则实体）：

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/v1/policies | 列出所有 OPA 策略规则 | 无 | { "policies": PolicyRule[], "total": integer } |
| GET | /api/v1/policies/{id} | 查询单条策略规则详情 | 无 | PolicyRule（详见 6.4 节） |
| POST | /api/v1/policies | 上传新策略规则 | PolicyRule | { "rule_id": string, "status": "created" } |
| PUT | /api/v1/policies/{id} | 更新策略规则 | PolicyRule 部分字段 | { "rule_id": string, "status": "updated" } |
| DELETE | /api/v1/policies/{id} | 删除策略规则 | 无 | { "rule_id": string, "status": "deleted" } |
| POST | /api/v1/policies/{id}/toggle | 启用/禁用策略规则 | { "enabled": boolean } | { "rule_id": string, "enabled": boolean, "status": "updated" } |

宪法规则管理（基于 YAML 声明式配置，详见第 9 节宪法规则配置示例）：

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/v1/constitution | 获取当前生效的宪法规则配置 | 无 | { "rules": object[], "applied_at": datetime } |
| PUT | /api/v1/constitution | 更新宪法规则配置 | { "rules": object[] } 或 YAML 文件内容 | { "status": "applied", "applied_at": datetime } |

### 审计日志查询 API

| 方法 | 路径 | 说明 | 请求参数 | 响应体 |
|------|------|------|---------|--------|
| GET | /api/v1/audit-logs | 查询审计日志 | 查询参数：since(起始时间)、until(结束时间)、agent_id(按 Agent 筛选)、action(invoke|decision|reject|approve)、workflow_id、page、page_size | { "logs": AuditLog[], "total": integer, "page": integer, "page_size": integer } |
| GET | /api/v1/audit-logs/{id} | 查询单条审计日志详情 | 无 | AuditLog（详见 6.2 节） |

## 15. 错误处理规范

### 15.1 标准错误响应格式

所有 API 接口统一采用以下错误响应格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "人类可读的错误描述",
    "details": {}
  }
}
```

### 15.2 错误码定义

| 错误码 | HTTP 状态码 | 场景 | 处理建议 |
|--------|-----------|------|---------|
| INVALID_REQUEST | 400 | 请求参数格式错误或缺少必填字段 | 根据 details 中的字段提示修正请求 |
| UNAUTHORIZED | 401 | 缺少或无效的认证凭据 | 检查 SPIFFE 身份或 API Token |
| FORBIDDEN | 403 | 认证通过但权限不足 | 联系 admin 授权 |
| NOT_FOUND | 404 | 请求的资源不存在 | 检查资源 ID 是否正确 |
| CONFLICT | 409 | 资源冲突（如重复注册） | 检查资源是否已存在 |
| RATE_LIMITED | 429 | API 调用频率超过限流阈值 | 等待 retry_after 秒后重试 |
| AUDIT_LOG_FULL | 审计子系统内部错误码 | 审计日志存储空间已满 | 业务操作以降级模式继续执行，审计写入跳过；需扩容存储或清理历史日志 |
| WORKFLOW_TIMEOUT | 504 | 工作流执行超时 | 检查工作流配置的超时参数 |
| INTERNAL_ERROR | 500 | 服务端未预期的错误 | 联系运维查看服务端日志 |

## 16. Console UI

Console UI 提供以下管理功能（接入 API Gateway）：

### Agent 管理
- Agent 注册：填写 Agent Card 字段信息提交注册
- Agent 列表：分页展示已注册 Agent，支持按名称、类型、状态筛选
- Agent 详情：查看单个 Agent 的完整配置、运行状态、健康检查记录
- Agent 启停：对已注册 Agent 执行启动/停止操作
- Agent 版本管理：查看版本历史，执行版本回滚

### 工作流监控
- 工作流列表：分页展示运行中/已完成/已失败的工作流，支持按状态、Agent、时间范围筛选
- 工作流详情：查看工作流执行轨迹、当前 Activity、Event History
- 人工审批节点：展示待审批 Signal，支持批准/拒绝操作
- 工作流操作：对运行中工作流执行终止、重试

### 安全策略配置
- 宪法规则管理：YAML 规则文件在线编辑与生效
- OPA 策略管理：策略上传、启用/禁用
- 审计日志查询：按时间、Agent、动作类型筛选审计日志记录

### 监控面板
- 实时指标：Agent 调用量、延迟 P95、错误率趋势图
- 成本看板：按 Agent/工作流维度的 Token 消耗和资源使用统计
- 告警管理：告警规则配置、告警历史查看

### CLI 接口

通过 API Gateway 提供命令行管理能力，支持上述所有 Web UI 功能的等效 CLI 命令。命令格式统一为：

```
harness <资源类型> <操作> [参数...] [--flags]
```

常用命令示例：

- `harness agent register --file agent-card.json` — 注册新 Agent（从 JSON 文件读取 Agent Card）
- `harness agent list [--type <type>] [--status <status>]` — 列出 Agent，支持按类型和状态筛选
- `harness agent get <agent-id>` — 查询单个 Agent 详情
- `harness agent start|stop <agent-id>` — 启动/停止 Agent
- `harness workflow list [--status running|completed|failed]` — 列出工作流，支持按状态筛选
- `harness workflow get <workflow-id>` — 查询工作流详情
- `harness workflow retry|terminate <workflow-id>` — 重试/终止工作流
- `harness policy constitution apply --file constitution.yaml` — 应用宪法规则配置文件
- `harness audit query --since <datetime> [--agent <agent-id>] [--action invoke|decision|reject|approve]` — 查询审计日志
- `harness monitor metrics [--since <datetime>] [--interval 1m|5m|1h]` — 查看实时指标
- `harness agent-type register --file agent-type.yaml` — 注册新 Agent 类型（从 YAML 文件读取第 20 节定义的 Agent 类型配置）
- `harness agent-type list` — 列出已注册的 Agent 类型

## 17. A2A Agent 间通信

Agent 通过 A2A 协议进行点对点通信，端点由 Registry 的 endpoints.a2a 字段定义。通信内容格式遵循 A2A 协议规范。

## 18. MCP Tool 发现

Agent 通过 MCP 协议发现和调用外部工具，MCP Server 端点由 Registry 或配置文件提供。

## 19. 多租户模型

平台通过 G 层的 SPIFFE/SPIRE 身份系统和 OPA 策略引擎实现多租户隔离：

- **租户标识**：每个租户分配独立的 SPIFFE 命名空间（如 `spiffe://prod/tenant/{tenant_id}/agent/{agent_id}`）
- **权限隔离**：OPA 策略限制跨租户的 Agent 通信和数据访问
- **资源隔离**：E 层的沙盒池按租户划分，确保运行环境隔离
- **角色分配**：每个租户内可分配 admin、operator、developer、viewer 四种角色，权限定义见第 4 节用户角色与权限矩阵

### 19.1 数据隐私与合规

平台在混合部署模式下涉及的数据处理活动需满足数据隐私与合规要求，具体约束如下：

- **数据驻留位置**：控制面组件（G 层治理与安全、L 层 Temporal Server、L 层 Agent Registry、C 层长期记忆存储、O 层可观测性后端）部署于企业私有数据中心，其存储的所有数据（包括但不限于身份信息、审计日志、长期记忆条目、Agent 配置数据、工作流状态、可观测性数据）必须驻留在私有数据中心内，不得外迁至公有云或第三方数据中心。
- **跨境数据传输约束**：当私有数据中心与云端沙盒位于不同司法管辖区时，Agent 间通信经 mTLS 加密回传仅传输实时执行请求与响应数据，不传输持久化数据。控制面组件（C 层长期记忆存储、O 层可观测性后端、G 层审计存储）中涉及个人数据（包括但不限于 Agent 交互内容、长期记忆条目中的用户信息、日志中的可识别个人数据）的存储与处理必须遵循企业适用的数据保护法规（如 GDPR、PIPL、CCPA 等），具体合规义务由企业法务与合规部门确定，平台提供以下技术支撑：
  - C 层长期记忆存储（Neo4j + Qdrant）支持按数据分类标签（如 personal_data、anonymized、aggregated）进行数据隔离，便于实施数据最小化原则和保留期限策略
  - O 层可观测性后端支持日志脱敏配置（通过配置敏感字段正则表达式自动对写入前的日志内容进行脱敏处理，脱敏后的日志进入存储）
  - G 层审计日志存储支持按租户命名空间隔离，审计日志记录中如包含个人数据应使用脱敏标识符替代
- **合规技术支撑能力**：平台提供数据分类标签、日志脱敏配置、按租户命名空间隔离等机制作为合规支撑手段，但不替代企业内法务与合规团队对具体适用法规（如 GDPR、PIPL、CCPA）的合规判定。

## 20. Agent 类型扩展机制

### 支持的 Agent 类型

Agent 类型的形式化标准：由运行模式、通信协议、注册方式、沙盒类型四个维度定义。新增类型无需修改核心代码即可通过配置文件注册。

| Agent 类型 | 运行模式 | 通信协议 | 注册方式 | 沙盒类型 |
|-----------|---------|---------|---------|---------|
| AI Agent | LangGraph ReAct 循环 | A2A + MCP | Agent Registry | 容器 |
| 监控 Agent | LangGraph + 定时触发 | A2A | Agent Registry | 容器 |
| RPA Agent | LangGraph + 脚本执行 | A2A + MCP | Agent Registry | 容器/microVM |

### 扩展方式

新 Agent 类型接入平台需完成以下步骤及验收标准：

| 步骤 | 描述 | 验收标准 |
|------|------|---------|
| 1. A2A 协议接入 | 实现 A2A 协议端点，遵循 Agent Card 格式注册到 Agent Registry | Agent 注册后可通过 A2A 协议发送和接收消息；Agent Card 必填字段完整 |
| 2. MCP 工具接入 | 按需接入 MCP 服务器提供工具能力 | MCP 端点可达；Agent 可通过 MCP 协议发现工具并调用 |
| 3. 沙盒适配 | 在 E 层选择合适的沙盒类型（容器 / microVM / 浏览器） | Agent 在选定沙盒类型中正常启动并通过健康检查 |
| 4. 安全接入 | 通过 G 层 SPIFFE 分配身份，OPA 配置访问策略 | Agent 获得唯一 SPIFFE 身份；OPA 策略正确限制其权限边界 |

### 配置文件注册 Schema

新增 Agent 类型通过 YAML 配置文件注册至平台，配置文件 Schema 定义如下：

```yaml
# agent-type-registration.yaml
agent_type:
  name: string                          # Agent 类型名称，全局唯一
  runtime_mode: string                  # 运行模式枚举：langgraph_react | scheduled | script_execution
  max_turns: integer                    # Agent 内部 ReAct 循环的最大轮数，取值范围 [1, 100]，默认值 10
  communication:
    a2a: boolean                        # 是否支持 A2A 协议
    mcp: boolean                        # 是否支持 MCP 协议
  registration:
    method: string                      # 注册方式枚举：agent_registry | config_file
    config:                             # config_file 模式下的注册配置（可选）
      card_template: object             # Agent Card 模板，含默认字段值
  sandbox:
    type: string                        # 沙盒类型枚举：container | microvm | browser
    config:                             # 沙盒配置
      image: string                     # 容器镜像或 microVM 镜像标识
      resource_limits:                  # 资源限制（可选）
        cpu: string                     # 如 "2" 表示 2 核
        memory: string                  # 如 "4Gi"
  retry_config:                         # 工作流重试策略（workflow_retry）配置（可选），Agent 类型级别的默认重试策略，可被工作流启动参数或 Agent Card 的 retry_config 字段覆盖
    max_retries: integer                # 最大重试次数，取值范围 [0, 10]
    backoff_interval: integer           # 退避间隔（秒），取值范围 [1, 3600]，默认值 60
    timeout: integer                    # 超时时间（秒），取值范围 [1, 86400]，默认值 600
  default_policies:                     # 默认安全策略（可选）
    - hook_point: string                # 拦截点
      action: string                    # 动作
      condition: string                 # Rego 条件表达式
```

配置示例：

```yaml
agent_type:
  name: "data-pipeline-agent"
  runtime_mode: "scheduled"
  max_turns: 10
  communication:
    a2a: true
    mcp: true
  registration:
    method: "agent_registry"
  sandbox:
    type: "container"
    config:
      image: "base-agent:latest"
      resource_limits:
        cpu: "2"
        memory: "4Gi"
```

## 21. 部署架构约束

- **混合部署**：控制面（G 层、L 层 Temporal Server、L 层 Agent Registry、C 层长期记忆存储、O 层可观测性后端）私有化部署；Agent 运行时沙盒可分布在私有数据中心和云端。私有化组件与云端组件之间的通信经 mTLS 加密回传至私有化控制面
- **大规模支持**：Temporal 水平扩展支持 500+ Agent 同时运行，扩展维度包括 Worker 节点数、数据库连接池、任务队列分区数
- **多 Agent 类型**：AI Agent / 监控 Agent / RPA Agent 统一通过 A2A 协议接入
- **零信任安全**：所有通信 mTLS + SPIFFE 身份验证

## 22. 关键设计决策

### 为什么选 Temporal 而非纯 LangGraph

- Temporal 提供 Durable Execution — Workflow 持久化到 DB，宕机从最后 await 点恢复，RPO = 0
- 原生支持 Saga 补偿事务
- Signal/Query 机制天然适合人工审批场景
- 水平扩展已验证可支撑 >= 1000 并发工作流
- LangGraph 作为 Agent 内部推理层与其互补而非替代

### 为什么选 MCP + A2A

- MCP 统一 Agent 与工具/数据源的连接（向下）
- A2A 统一 Agent 之间的通信与协作（横向）
- 两者由 Anthropic 和 Google 主导，生态成熟度快速提升

## 23. MVP 建议

**首期聚焦**: L 层（Temporal + Agent Registry）+ G 层（SPIFFE + OPA）+ 基础 O 层

基础 O 层定义为 MVP 范围内的 O 层功能子集，包含：OpenTelemetry Tracing 数据采集、运行时 Metrics 采集（调用量、延迟、错误率）、结构化日志采集。成本追踪功能不在 MVP 范围内。

**MVP 可验证目标**：

1. 完成 1-2 种 Agent（AI Agent + 监控 Agent）的完整编排闭环：注册、部署、执行全链路通过验收测试
2. 验证 Temporal 编排 + OPA 安全策略的集成闭环：Agent 执行需经身份验证和策略检查，通过集成测试
3. 基础 O 层采集 Tracing + Metrics + Logs 数据并接入 Langfuse 展示，通过数据可达性验证
4. 验证结果以压测报告和集成测试报告形式输出，作为架构可行性验证依据
