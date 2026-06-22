# Agent Harness 管理平台设计文档

## 概述

企业级 Agent 管理平台，基于 ETCLOVG 七层架构，管理多种类型的 Agent（AI Agent、监控 Agent、RPA 等）。核心能力按优先级：**编排 > 安全 > 监控 > 生命周期 > 市场 > 计费**。

部署模式：混合部署（核心私有化 + 部分云端），面向企业内部团队，支持大规模（500+ Agent）集群管理。

## ETCLOVG 七层架构

| 层 | 名称 | 职责 |
|----|------|------|
| E | Execution & Sandbox | Agent 运行环境（容器/microVM/浏览器） |
| T | Tool Interface | 工具发现与调用（MCP/A2A/Function Calling） |
| C | Context Management | 短期上下文/中期会话/长期记忆 |
| L | Lifecycle/Orchestration | 执行流调度、重试、多 Agent 编排 |
| O | Observability | 追踪/监控/日志/成本 |
| V | Verification & Evaluation | 评测模型+Harness 组合 |
| G | Governance & Security | 身份/权限/钩子/审计/宪法规则 |

## 整体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                          API Gateway / Console                        │
│                     (统一的 Web UI + CLI + API)                       │
└──────────────────────────────────────────────────────────────────────┘
                                      │
┌──────────────────────────────────────────────────────────────────────┐
│  G — Governance & Security Layer                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │SPIFFE/   │ │   OPA    │ │   mTLS   │ │ 宪法规则  │ │ 审计日志   │  │
│  │SPIRE ID  │ │  策略引擎 │ │  传输加密 │ │声明式配置 │ │ 不可篡改   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  钩子: [输入前 → 执行前 → 返回后 → 关键动作审批]                      │
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
│  V — Verification & Evaluation                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ 评测沙盒: 执行前验证 → 执行中追踪 → 多级判断 → 回归测试库       │  │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                    ↓ Agents 运行时三层支撑 ↓                          │
├──────────────────────────────────────────────────────────────────────┤
│  C — Context Management                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ 短期上下文窗口     │  │ 中期会话状态      │  │ 长期持久化记忆     │  │
│  │ (System Prompt    │  │ (结构化笔记 +    │  │ (Mem0 + 向量库 +   │  │
│  │  渐进式披露)       │  │  工作文件)       │  │  图数据库)         │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  T — Tool Interface                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │   MCP Servers     │  │   A2A Protocol   │  │   Function Calling  │  │
│  │  (工具/数据接入)   │  │ (Agent 间通信)   │  │  (LLM 原生)        │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  E — Execution & Sandbox                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │ 容器运行时(Docker) │  │  microVM (E2B)   │  │  Computer Use      │  │
│  │ + 沙盒池管理       │  │ 高隔离场景       │  │  GUI 操作场景      │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  O — Observability                                                   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  OpenTelemetry → Langfuse/Arize Phoenix                        │  │
│  │  (Tracing + Metrics + Logs + 成本追踪)                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## L 层核心：编排模型

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

## G 层：安全治理 — 四道防线

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
    then: "REJECT + notify(ops)"
  - on: "llm_input.before"
    if: "contains(input, 'password')"
    then: "REDACT + alert"
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

审计日志：Write-Once 不可篡改，记录每次调用/决策/拒绝。

## C 层：上下文管理 — 三级记忆架构

| 级别 | 类比 | 技术实现 | 生命周期 |
|------|------|---------|---------|
| 短期 | 内存 | System Prompt 优化 + KV 缓存 + 窗口滑动 | 会话进行中 |
| 中期 | 休眠文件 | 结构化笔记 + 工作文件 + Temporal 状态持久化 | 跨会话 |
| 长期 | 硬盘 | Mem0 + Qdrant + Neo4j | 跨任务 |

## V 层：评测 — 五阶段闭环

1. **定义** — 环境 + 成功标准
2. **执行前验证** — 沙盒/依赖/权限初始化检查
3. **受控执行 + 追踪捕获** — 完整记录运行轨迹
4. **多级判断 + 故障归因** — 结果 + 工具调用合理性 + 裁判模型偏见评估
5. **回归测试** — 失败记录 → 测试用例 → Harness 自动迭代优化

## 开源工具选型

| 层 | 组件 | 推荐工具 | 说明 |
|----|------|---------|------|
| E | 沙盒 | E2B, Daytona, Docker, Firecracker | microVM 高隔离 / Docker 轻量 |
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

## 关键设计决策

### 为什么选 Temporal 而非纯 LangGraph

- Temporal 提供 Durable Execution — Workflow 持久化到 DB，宕机从最后 await 点恢复
- 原生支持 Saga 补偿事务
- Signal/Query 机制天然适合人工审批场景
- 生产验证于 Uber/Netflix/Stripe 的大规模场景
- LangGraph 作为 Agent 内部推理层与其互补而非替代

### 为什么选 MCP + A2A

- MCP 统一 Agent 与工具/数据源的连接（向下）
- A2A 统一 Agent 之间的通信与协作（横向）
- 两者由 Anthropic 和 Google 主导，生态成熟度快速提升

## MVP 建议

**首期聚焦**: L 层（Temporal + Agent Registry）+ G 层（SPIFFE + OPA）+ 基础 O 层（OTel）

目标：让 1-2 种 Agent 跑通完整编排→安全→监控闭环，验证架构可行性。

## 架构约束

- **混合部署**: 控制面私有化部署，Agent 运行时可分布在私有数据中心和云端
- **大规模**: 支持 500+ Agent 同时运行，Temporal 水平扩展
- **多 Agent 类型**: AI Agent / 监控 Agent / RPA Agent 统一通过 A2A 协议接入
- **零信任安全**: 所有通信 mTLS + SPIFFE 身份验证
