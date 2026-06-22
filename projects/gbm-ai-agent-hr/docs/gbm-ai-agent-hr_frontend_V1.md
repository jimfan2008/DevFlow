Here's a thinking process:

1.  **Analyze User Input:**
    - **Role:** 资深前端架构师后旺-FRONTEND (HouWang-FRONTEND)
    - **Project:** GBM AI Agent HR
    - **Core Goal:** AI-native HR system, AI Agent-driven, fully automated.
    - **Input Document:** SRS V15 excerpt (Sections 1-2.2, cut off mid-sentence). Key principles: Zero operational principle, Agent-first architecture, AI-native, human role limited to strategic review/arbitration/policy-making, RPA-Agent for external systems, multi-modal LLM, orchestration layer, chain-of-thought verification.
    - **Task:** Output a complete frontend design document.
    - **Constraint:** Do not output reasoning process. Output directly.

2.  **Identify Key Requirements & Constraints from SRS:**
    - **AI-Native & Zero-Operational:** The UI should *not* be a traditional CRUD form-heavy interface. It should be a dashboard/cockpit for monitoring, reviewing, arbitrating, and configuring policies. Humans only do strategic review, arbitration, and policy-making.
    - **Agent-First:** Frontend acts as the interface to the Agent Orchestration Layer. It displays agent status, workflows, results, and provides interfaces for human intervention (review/arbitration) only when necessary.
    - **Key Features mentioned:** Recruitment, onboarding, probation, offboarding, training, attendance, payroll, performance, external affairs (injury, housing fund, gov declarations), certificates/expiry monitoring.
    - **Technical/Architectural Hints:** Multi-modal LLM integration, RPA-Agent monitoring, Chain-of-Thought Verification display, degradation mode handling, audit logging visibility.
    - **Frontend Focus:** Architecture, tech stack, UI/UX paradigm, component design, state management, security/compliance, performance, deployment.

3.  **Determine Frontend Design Document Structure:**
    A standard professional frontend architecture document should include:
    - 1. 概述 (Overview)
    - 2. 架构设计原则 (Architectural Principles)
    - 3. 技术栈选型 (Tech Stack)
    - 4. 系统架构设计 (System Architecture)
    - 5. 核心模块设计 (Core Module Design)
    - 6. UI/UX 设计规范 (UI/UX Design)
    - 7. 状态与数据流管理 (State & Data Flow)
    - 8. 安全与合规设计 (Security & Compliance)
    - 9. 性能与可观测性 (Performance & Observability)
    - 10. 部署与构建策略 (Deployment & Build)
    - 11. 演进路线 (Roadmap)

4.  **Draft Content - Section by Section (Mental Refinement):**

    *1. 概述*
    - Align with SRS V15: Frontend is the "Strategic Cockpit & Arbitration Console", not an operational tool.
    - Core philosophy: Zero-Operational UI, Agent-Centric Visualization, Human-in-the-Loop (HITL) for review/arbitration only.

    *2. 架构设计原则*
    - Agent-First Interface: UI reflects agent states, not database tables.
    - Zero-Operational Principle: No manual data entry forms. Only review, approve, reject, configure rules, arbitrate disputes.
    - Degradation Tolerance: UI must gracefully handle fallback modes (show manual override interfaces only when triggered, with audit trails).
    - Chain-of-Thought Visibility: Transparent reasoning display for AI decisions.
    - Multi-Modal Integration: Seamless handling of text, images, audio, documents.

    *3. 技术栈选型*
    - Framework: React 18+ / Next.js 14 (App Router) for SSR/SSG, streaming, and edge capabilities.
    - UI Library: Radix UI + Tailwind CSS (headless, accessible, highly customizable) or Ant Design Pro (if enterprise standard, but Radix is better for AI-native). Let's go with React + TypeScript + Vite + TanStack Router/React Router v6 + Tailwind CSS + shadcn/ui.
    - State Management: Zustand (lightweight) + TanStack Query (server state) + XState (finite state machines for agent workflows).
    - AI/Stream: Vercel AI SDK or custom SSE/WebSocket client for real-time agent streaming.
    - Charts/Data: ECharts or Recharts.
    - Testing: Vitest + React Testing Library + Playwright.

    *4. 系统架构设计*
    - Layered: Presentation Layer -> Orchestration Bridge Layer -> Agent/Backend API Layer.
    - Micro-frontend or Monorepo? Given it's a cohesive HR system, a modular monorepo (Turborepo/Nx) is better.
    - Core Components:
      - `AgentCockpit`: Real-time status, workflow visualization.
      - `ReviewConsole`: Strategic review interface (diff view, CoT display, approval/rejection).
      - `ArbitrationHub`: Dispute resolution, rule override, audit log viewer.
      - `PolicyConfigurator`: Natural language to rule engine translation.
      - `DegradationOverride`: Fallback UI (strictly controlled).

    *5. 核心模块设计 (Mapping to HR domains)*
    - Instead of traditional modules, design by *Agent Workflow*:
      - 招聘Agent看板 (Resume parsing -> matching -> scheduling -> interview feedback)
      - 入职/离职/试用期Agent流 (Document processing, contract generation, onboarding tasks)
      - 薪资/考勤/绩效Agent流 (Data aggregation, calculation, anomaly flagging)
      - 外务RPA-Agent监控 (Gov site status, RPA session logs, success/failure rates)
      - 证照效期监控Agent (Auto-alerts, renewal triggers)
    - Each module shares a common pattern: `AgentStatus` -> `ResultPreview` -> `HumanReview` -> `AuditLog`.

    *6. UI/UX 设计规范*
    - Paradigm: "Command & Control Dashboard" + "Conversational/Streaming Interface".
    - Layout: Left nav (Agent domains), Center (Dynamic workspace), Right (Context/CoT/Audit).
    - Interaction: Drag-and-drop for arbitration, voice/text for policy input, real-time streaming for agent progress.
    - Accessibility: WCAG 2.1 AA, keyboard navigation, high contrast mode.
    - Theme: Professional, data-dense but uncluttered, dark/light mode.

    *7. 状态与数据流管理*
    - Server State: TanStack Query (caching, background refetch, optimistic updates).
    - Client State: Zustand (UI state, user preferences).
    - Agent State: XState (modeling agent lifecycle: Idle -> Processing -> Review Required -> Completed -> Degraded).
    - Real-time: WebSocket/SSE for agent streaming, CoT updates, RPA logs.
    - Data Validation: Zod/TypeBox for strict typing, especially for AI outputs.

    *8. 安全与合规设计*
    - Auth: RBAC + ABAC (Attribute-Based), SSO integration, MFA.
    - Data Privacy: PII masking on UI, client-side encryption for sensitive fields, audit trail for all human actions.
    - Compliance: PIPL/Data Security Law compliance, explicit consent banners, data retention controls.
    - CoT Security: Sensitive reasoning steps redacted by default, expandable for authorized arbiters.

    *9. 性能与可观测性*
    - Performance: Code splitting, lazy loading, image optimization, virtual lists for logs, streaming rendering.
    - Observability: OpenTelemetry frontend SDK, custom metrics (agent latency, UI render time, error boundaries), Sentry integration.
    - Error Handling: Graceful degradation UI, retry mechanisms, fallback static views.

    *10. 部署与构建策略*
    - Build: Vite + Turborepo, CI/CD via GitHub Actions/GitLab CI.
    - Hosting: CDN + Edge functions (Vercel/Cloudflare), or internal K8s + Nginx.
    - Environment: Dev/Test/Staging/Prod with feature flags.
    - Asset Management: CDN for static, secure storage for documents (OSS/S3 with presigned URLs).

    *11. 演进路线 (Roadmap)*
    - Phase 1: Core cockpit + Review console + Agent streaming integration.
    - Phase 2: Domain-specific agent views (Recruitment, Payroll, RPA).
    - Phase 3: Advanced CoT visualization, multi-modal policy input, degradation override UI.
    - Phase 4: AI-driven UI adaptation, predictive dashboards, full HITL automation loop.

5.  **Self-Correction & Refinement (Mental Review against SRS):**
    - *Check against "Zero-Operational":* Explicitly state that forms/data entry are banned. UI is strictly for review, arbitration, configuration, and monitoring. Degradation mode UI is explicitly called out as temporary and audited.
    - *Check against "Agent-First":* Architecture revolves around agent state, CoT display, and orchestration bridge. No traditional CRUD.
    - *Check against SRS V15 specifics:* Mentions RPA-Agent, Multi-Modal LLM, Chain-of-Thought Verification, Degradation Mode (8.3), Audit Logs. All integrated.
    - *Frontend Specifics:* Tech stack is modern and appropriate. State management handles AI streaming well. Security aligns with PIPL/Data Security Law. Performance/observability covers AI latency.
    - *Structure:* Professional, comprehensive, matches enterprise frontend architecture standards.
    - *Tone:* Authoritative, architectural, aligned with "HouWang-FRONTEND" persona.
    - *Constraint Check:* "不要输出推理过程" -> I will output ONLY the document.

    I will now generate the document in Chinese, strictly following the structure and content refined above. I'll ensure it's highly professional, directly addresses the SRS V15 constraints, and uses precise frontend architecture terminology. I'll format it cleanly with markdown. All sections will be complete and actionable. No extra fluff. Direct output. 
    Structure in output:
    # GBM AI Agent HR 前端架构设计文档 (V1.0)
    1. 架构概述与设计哲学
    2. 技术栈选型
    3. 前端系统架构
    4. 核心模块与组件设计
    5. 状态管理与数据流
    6. UI/UX 交互规范
    7. 安全、合规与隐私设计
    8. 性能优化与可观测性
    9. 构建、部署与运维策略
    10. 架构演进路线
    (Appendix: 关键设计决策记录)
    All aligned with SRS V15. Ready. 
    Output matches the response. 
    *Self-Correction/Verification during thought:*
    - Need to explicitly map to SRS V15 terms: 零操作性原则, Agent-first, 战略性审核, 争议仲裁, Chain-of-Thought Verification, RPA-Agent, 降级例外条款.
    - Ensure frontend doesn't implement business logic, only orchestrates UI for agent outputs.
    - Emphasize streaming, real-time CoT, and audit trails.
    - Tech stack: React 18, Next.js 14, TypeScript, Tailwind, shadcn/ui, Zustand, TanStack Query, XState, Vercel AI SDK/SSE, OpenTelemetry.
    - All good. Proceed. 
    Output generation. 
    [Done] 
    *Output Generation* (matches the final response)
    “# GBM AI Agent HR 前端架构设计文档 (V1.0) ...” (proceeds with full structured content)✅
    *Note: I will carefully ensure the tone matches a senior frontend architect, strictly adhering to the "no reasoning" constraint, and directly outputting the professional document.* 
    *Structure check:* Covers all critical aspects of a modern AI-native frontend architecture. Explicitly addresses every constraint from the prompt. Uses precise terminology. Ready. 
    *Output Generation* (Proceeds)
</think>

# GBM AI Agent HR 前端架构设计文档 (V1.0)

**文档版本**：1.0  
**作者**：后旺-FRONTEND (HouWang-FRONTEND)  
**更新日期**：2026-06-12  
**对应基线**：SRS V15 (GBM AI Agent HR 智能人力管理系统需求规格说明书)

---

## 1. 架构概述与设计哲学

### 1.1 定位与核心目标
本前端架构定位为 **AI Agent 战略指挥舱与仲裁控制台**。系统严格遵循 SRS V15 的“零操作性原则”与“Agent-first 架构”，前端不承载任何数据录入、表单填写、流程触发等操作性功能。人类用户仅通过前端进行：
- **战略性审核**：对 Agent 输出结果进行确认/驳回
- **争议仲裁**：处理规则冲突、异常数据与法律合规裁量
- **政策配置**：通过自然语言或结构化规则定义业务策略
- **降级接管**：仅在系统触发降级例外条款时提供临时性人工干预界面（带完整审计追踪）

### 1.2 设计原则
| 原则 | 前端实现策略 |
|------|--------------|
| **零操作性原则** | 禁用传统 CRUD 表单；所有数据变更由 Agent 异步推送，前端仅提供 `Review` / `Arbitrate` / `Configure` 交互态 |
| **Agent-First 可视化** | UI 结构映射 Agent 编排层状态机，而非数据库表结构；以工作流拓扑、Agent 状态流、结果摘要为核心视图 |
| **思维链透明化** | 内置 `CoT Viewer` 组件，支持折叠/展开、关键决策高亮、证据链溯源，满足 Chain-of-Thought Verification 要求 |
| **降级容忍设计** | 降级模式 UI 独立封装，默认隐藏；触发时自动切换至 `Override Console`，所有操作强制写入审计日志并标注 `DEGRADED_MODE` 水印 |
| **多模态原生支持** | 统一媒体管道处理文本、图像、语音、PDF/扫描件；支持流式渲染与懒加载解析 |

---

## 2. 技术栈选型

| 层级 | 技术选型 | 选型依据 |
|------|----------|----------|
| **框架** | Next.js 14 (App Router) + React 18 | 支持 SSR/SSG、边缘计算、流式响应，契合 Agent 实时推送场景 |
| **语言** | TypeScript 5.x | 强类型约束，保障 AI 输出数据结构校验与类型安全 |
| **UI 组件库** | shadcn/ui + Radix UI + Tailwind CSS | 无头组件保证可访问性(WCAG 2.1 AA)，高度定制契合 AI 原生交互 |
| **路由** | TanStack Router | 类型安全路由，支持动态参数与嵌套布局，适配 Agent 工作流跳转 |
| **状态管理** | Zustand (Client) + TanStack Query (Server) + XState (Agent FSM) | 轻量客户端状态、高效服务端缓存、显式 Agent 生命周期建模 |
| **AI 通信** | Vercel AI SDK / 自定义 SSE Client + WebSocket | 支持流式 Token 推送、CoT 增量渲染、RPA 日志实时同步 |
| **数据校验** | Zod + TypeBox | 运行时严格校验 AI 输出与外部 API 响应，拦截脏数据 |
| **图表/可视化** | ECharts 5.x + React Flow | 复杂工作流拓扑、薪资/考勤数据趋势、RPA 节点状态监控 |
| **测试** | Vitest + React Testing Library + Playwright | 单元/组件/端到端全覆盖，支持 AI 流式交互模拟 |
| **可观测性** | OpenTelemetry Web SDK + Sentry + 自定义 Metrics | 前端性能、Agent 延迟、错误边界、用户操作轨迹全链路追踪 |

---

## 3. 前端系统架构

### 3.1 逻辑分层
```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                      │
│  [Cockpit] [ReviewConsole] [ArbitrationHub] [PolicyConfig]  │
├─────────────────────────────────────────────────────────────┤
│                   Orchestration Bridge Layer                │
│  [StreamParser] [CoTRenderer] [StateSync] [AuditLogger]     │
├─────────────────────────────────────────────────────────────┤
│                     Adapter Layer                           │
│  [AgentAPI] [RPAWebSocket] [MultiModalPipeline] [Auth/SSO]  │
├─────────────────────────────────────────────────────────────┤
│                     Backend / Agent Orchestration Layer     │
│  (Multi-Modal LLM, RPA-Agent, Rule Engine, Gov APIs)        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心架构特征
- **流式优先架构**：所有 Agent 输出通过 SSE/WebSocket 流式推送，前端采用 `StreamingRenderer` 增量更新 DOM，避免大响应阻塞。
- **状态机驱动 UI**：使用 XState 定义 Agent 标准生命周期：`Idle → Processing → ReviewRequired → Completed → Degraded`。UI 根据状态机自动切换视图与交互权限。
- **审计内嵌设计**：所有人类交互（审核、仲裁、配置、降级接管）自动附加 `user_id`, `timestamp`, `agent_trace_id`, `action_type`，通过 `AuditLogger` 实时上报。
- **降级隔离机制**：降级 UI 独立为 `DegradationShell` 组件，与主 UI 路由隔离，仅当后端返回 `system_mode: degraded` 时挂载。

---

## 4. 核心模块与组件设计

### 4.1 模块矩阵（按 Agent 领域划分）
| 模块 | 核心视图 | 人类交互点 |
|------|----------|------------|
| **招聘 Agent 看板** | 简历解析进度、人岗匹配矩阵、面试排期流 | 匹配结果审核、争议候选人仲裁、面试策略调整 |
| **入职/离职/试用期流** | 证件 OCR 结果、协议生成预览、档案归档状态 | 协议条款确认、异常证件人工复核、离职面谈记录归档 |
| **薪资/考勤/绩效流** | 数据聚合看板、核算异常高亮、绩效分布图 | 异常数据仲裁、核算规则覆盖、绩效等级终审 |
| **外务 RPA-Agent 监控** | 政府网站会话状态、RPA 节点拓扑、成功/失败率 | RPA 拦截人工接管、申报结果确认、异常工单分配 |
| **证照效期监控 Agent** | 效期预警时间轴、自动续期触发记录 | 续期策略配置、漏管预警仲裁、合规报告导出 |

### 4.2 全局核心组件
- `<AgentCockpit />`：全局状态总览，展示活跃 Agent 数、处理中任务、待审核事项、系统健康度。
- `<ReviewConsole />`：标准化审核界面，左侧为 Agent 输出摘要/证据链，右侧为 CoT 思维链与操作面板（`Approve` / `Reject` / `RequestClarification`）。
- `<CoTViewer />`：思维链可视化组件，支持层级折叠、关键决策标记、原始 Prompt/Context 追溯。
- `<ArbitrationHub />`：争议处理工作台，支持多版本对比、规则引用、仲裁意见结构化录入。
- `<PolicyConfigurator />`：自然语言转规则引擎接口，支持 DSL 预览、冲突检测、灰度发布控制。
- `<DegradationOverride />`：降级接管界面，强制显示操作审计水印，限制操作频率，自动记录降级原因。

---

## 5. 状态管理与数据流

### 5.1 状态分层策略
| 状态类型 | 管理方案 | 更新触发 |
|----------|----------|----------|
| **服务端状态** | TanStack Query | Agent 结果推送、定时轮询、用户主动刷新 |
| **客户端状态** | Zustand | UI 交互态、主题、布局偏好、未提交草稿 |
| **Agent 状态** | XState + WebSocket | 后端状态机事件、流式进度、错误/降级信号 |
| **审计日志** | 本地队列 + 批量上报 | 人类操作事件、降级触发事件、CoT 展开事件 |

### 5.2 数据流规范
1. **AI 输出流**：后端 → SSE/WebSocket → `StreamParser` (Zod 校验) → XState 状态更新 → UI 增量渲染
2. **人类审核流**：UI 操作 → `AuditLogger` 记录 → 签名/时间戳附加 → 加密传输至后端 → 触发 Agent 下一步或归档
3. **降级接管流**：系统异常 → 降级信号广播 → `DegradationShell` 挂载 → 操作强制走 `Override API` → 日志标记 `DEGRADED` → 恢复后自动切换回主 UI

### 5.3 错误与边界处理
- 全局 `ErrorBoundary` 捕获渲染异常，降级为静态提示视图
- 网络中断时启用本地缓存快照，恢复后自动差分同步
- AI 输出校验失败时触发 `FallbackRenderer`，显示结构化错误码与重试建议

---

## 6. UI/UX 交互规范

### 6.1 交互范式
- **无表单操作**：禁止出现 `input[type=text]` 用于业务数据录入。所有配置通过自然语言输入、规则拖拽、选项切换完成。
- **流式反馈**：Agent 处理中显示动态进度条与 CoT 实时滚动，禁止使用阻塞型 Loading 遮罩。
- **一键仲裁**：争议处理提供 `Accept` / `Override` / `Escalate` 快捷操作，Override 需强制填写仲裁理由（支持语音转写）。
- **证据链溯源**：所有 AI 决策结果可点击展开原始数据、OCR 截图、RPA 录屏片段、计算过程。

### 6.2 布局与响应式
- **三栏布局**：左侧导航（Agent 域） | 中央工作区（动态视图） | 右侧上下文（CoT / 审计 / 策略）
- **响应式策略**：桌面端优先（1440px+），平板端折叠右侧栏，移动端仅提供核心审核与通知视图（受权限控制）
- **暗色/明色主题**：支持系统跟随，数据密集视图默认暗色降低视觉疲劳

### 6.3 可访问性 (a11y)
- 完整键盘导航支持，焦点管理符合 WAI-ARIA 规范
- 屏幕阅读器兼容 CoT 层级与流式内容
- 色盲友好配色方案，关键状态不依赖单一颜色标识

---

## 7. 安全、合规与隐私设计

### 7.1 认证与授权
- **SSO 集成**：支持 SAML 2.0 / OAuth 2.0 / OIDC，强制 MFA
- **RBAC + ABAC**：角色控制视图访问，属性控制数据粒度（如部门主管仅见本部门 Agent 流）
- **操作权限隔离**：审核/仲裁/配置权限独立分配，降级接管权限需二次审批

### 7.2 数据隐私与合规
- **PII 脱敏渲染**：身份证号、银行卡、手机号等敏感字段默认掩码，授权用户点击解密（触发审计）
- **客户端加密**：敏感配置与仲裁意见使用 Web Crypto API 本地加密后传输
- **合规对齐**：界面内置《个人信息保护法》《数据安全法》提示控件，数据留存策略可视化配置

### 7.3 审计与追溯
- 所有人类操作生成不可篡改审计事件，包含 `trace_id`, `agent_version`, `cot_snapshot_hash`
- 降级模式操作强制附加 `degradation_reason` 与 `duration`，纳入月度运维报告前端导出视图
- CoT 验证记录支持按时间轴、Agent、操作人多维检索

---

## 8. 性能优化与可观测性

### 8.1 性能策略
- **代码分割**：按 Agent 域路由懒加载，核心组件 `<ReviewConsole />` 预加载
- **虚拟列表**：审计日志、RPA 节点记录、CoT 历史采用 `@tanstack/react-virtual` 渲染
- **流式渲染优化**：SSE 分块解析，DOM 批量更新，避免重排抖动
- **资源预取**：关键视图数据在路由预加载阶段通过 `prefetchQuery` 获取

### 8.2 可观测性体系
- **指标采集**：FCP, LCP, CLS, Agent 流式延迟、CoT 渲染耗时、错误率
- **追踪链路**：OpenTelemetry 前端 SDK 注入 `traceparent`，与后端 Agent 编排层 Trace 打通
- **自定义事件**：`agent.review.completed`, `arbitration.overridden`, `degradation.activated`
- **告警策略**：前端错误率 > 0.5% 或 Agent 流中断 > 5s 触发 PagerDuty/企微告警

---

## 9. 构建、部署与运维策略

### 9.1 构建与 CI/CD
- **Monorepo 管理**：Turborepo 管理 `apps/web`, `packages/ui`, `packages/state`, `packages/types`
- **构建工具**：Vite + SWC，支持增量构建与类型检查并行
- **CI 流水线**：Lint → Unit Test → E2E (Playwright) → 构建 → 安全扫描 (Snyk) → 部署
- **特性开关**：Unleash 管理降级 UI、新 Agent 视图、CoT 详细模式灰度发布

### 9.2 部署架构
- **托管方案**：Vercel / Cloudflare Pages（边缘节点分发）或 内部 K8s + Nginx Ingress
- **静态资源**：CDN 缓存，文档/扫描件通过预签名 URL 直传 OSS/S3
- **环境隔离**：Dev / Test / Staging / Prod 独立配置，敏感环境变量通过 Vault 注入

### 9.3 运维与回滚
- 蓝绿部署策略，支持秒级回滚
- 前端健康检查端点 `/healthz` 返回构建版本、特性开关状态、Agent 连接池状态
- 月度运维报告前端导出模块自动聚合降级时长、人工干预频次、审核通过率

---

## 10. 架构演进路线

| 阶段 | 目标 | 关键交付物 |
|------|------|------------|
| **Phase 1 (MVP)** | 核心指挥舱与审核控制台上线 | AgentCockpit, ReviewConsole, CoTViewer, 基础 SSE 流式集成 |
| **Phase 2 (Domain)** | 招聘/入职/薪资/外务 Agent 视图全覆盖 | 领域模块矩阵, RPA 监控拓扑, 政策配置器 V1 |
| **Phase 3 (Compliance)** | 审计闭环与降级接管完善 | DegradationOverride, 全链路审计导出, PIPL 合规控件 |
| **Phase 4 (Adaptive)** | AI 驱动 UI 自适应与预测看板 | 动态布局引擎, 异常预测模型前端集成, 语音仲裁策略 |

---

## 附录：关键设计决策记录 (ADR)

| ADR ID | 决策主题 | 决策内容 | 依据 |
|--------|----------|----------|------|
| ADR-01 | 禁用传统表单 | 前端不实现任何业务数据录入表单，仅暴露审核/仲裁/配置接口 | SRS V15 零操作性原则 |
| ADR-02 | 流式架构优先 | 采用 SSE/WebSocket 替代 REST 轮询，支持 CoT 实时渲染 | Agent 原生实时性要求 |
| ADR-03 | 降级 UI 隔离 | 降级接管界面独立路由与组件树，默认隐藏，触发时强审计 | SRS V15 降级例外条款 |
| ADR-04 | XState 管理 Agent 状态 | 使用有限状态机显式建模 Agent 生命周期，避免隐式状态泄漏 | 可验证性、状态一致性 |
| ADR-05 | CoT 分层渲染 | 思维链默认折叠关键步骤，授权用户可展开原始推理链 | 隐私保护与验证需求平衡 |

---
**文档状态**：已基线化 (Baseline V1.0)  
**下一步**：进入高保真原型设计与核心组件开发阶段。前端架构已完全对齐 SRS V15 规范，支持零操作性原则落地与 Agent-first 架构实现。