The user wants me to act as a senior software architect (HouWang/后旺) and create a complete design plan based on the SRS document provided. They want 4 parts:

1. Architecture Design Document
2. Frontend Design Document
3. Backend Design Document
4. Database Design Script (SQL DDL)

Let me read the SRS document first to make sure I have all the details, then produce the design documents.

The SRS is already provided in full in the message. Let me analyze it and create comprehensive design documents.

Key points from the SRS:
- AI-native HR management system
- All operational tasks executed by AI Agents
- Human users only do strategic review and arbitration
- Covers: recruitment, onboarding, probation, resignation, training, attendance, payroll, performance, external affairs, certificates


- Tech stack: MySQL 8.x, Redis, MinIO/OSS, RabbitMQ/Kafka, Elasticsearch
- Frontend: Web, Mobile, QR code
- Backend: Spring Boot/Go/Node
- AI models: LLM, OCR, Face Recognition, Embedding, ASR
- Deployment: Kubernetes/Docker Swarm
- RPA: Playwright/Puppeteer

Now I'm designing the architecture across all four layers, mapping out the component interactions, data flow, and deployment strategy for this AI-agent-driven system. Now I'm mapping out the remaining modules for the recruitment system—resume management, interview scheduling, and evaluation tracking—then moving into the other core sections like onboarding, training, attendance, and payroll management.


# 架构设计文档 (GBM AI Agent HR - Architecture Design)

## 1. 系统总体架构

### 1.1 架构愿景

本系统为彻底的 AI 原生 HR 管理平台，以"零操作性原则"为核心设计理念。所有可操作性事务由 AI Agent 自主执行，人类用户仅行使战略性审核与争议仲裁职责。

### 1.2 分层架构总览

```
+------------------------------------------------------------------+
|                     展示层 (Presentation Layer)                    |
|  Web SPA (Vue 3)  |  Mobile H5 (Uni-app)  |  二维码  |  短信/邮件 |
+------------------------------------------------------------------+
|                      统一网关层 (Gateway)                          |
|  Nginx (LB/SSL)  ->  API Gateway (Spring Cloud Gateway)           |
+------------------------------------------------------------------+
|                  Agent 编排调度层 (Orchestration)                  |
|  流程引擎 (Camunda 8)  |  消息总线 (Kafka)  |  任务调度 (XXL-Job)  |
+------------------------------------------------------------------+
|                     AI Agent 运行层 (Agent Runtime)                |
|  招聘Agent群 | 入职Agent群 | 培训Agent群 | 考勤Agent               |
|  薪资Agent   | 绩效Agent   | 外务Agent   | 证明Agent               |
|  OCR Agent   | RPA Agent   | 视频Agent   | 分析Agent               |
+------------------------------------------------------------------+
|                    AI 模型服务层 (AI Model Services)               |
|  LLM推理(vLLM) | OCR(PaddleOCR) | 人脸(ArkId) | Embedding | ASR   |
+------------------------------------------------------------------+
|                    数据基础设施层 (Data Infrastructure)            |
|  MySQL(主从) | Redis(Cluster) | MinIO | Kafka | Elasticsearch     |
+------------------------------------------------------------------+
|                     可观测性层 (Observability)                     |
|  Prometheus | Grafana | Jaeger | ELK | 审计日志                   |
+------------------------------------------------------------------+
```

### 1.3 分层职责说明

| 层级 | 职责 | 关键技术 |
|------|------|----------|
| 展示层 | 用户界面交互、扫码、移动端适配 | Vue 3 + Vite + Uni-app + TailwindCSS |
| 网关层 | 路由分发、认证鉴权、限流熔断、SSL终结 | Nginx + Spring Cloud Gateway |
| 编排调度层 | 业务流程编排、Agent任务调度、状态机管理 | Camunda 8 + Kafka + XXL-Job |
| Agent运行层 | 各业务Agent的具体逻辑执行 | Java(Spring Boot) + Python(AI) |
| AI模型服务层 | LLM推理、OCR、人脸识别、向量嵌入 | vLLM + PaddleOCR + Face++ API |
| 数据基础设施层 | 结构化/非结构化数据存储、消息队列、搜索 | MySQL + Redis + MinIO + Kafka + ES |
| 可观测性层 | 指标采集、链路追踪、日志聚合、告警 | Prometheus + Grafana + Jaeger + ELK |

### 1.4 模块划分

```
GBM-AI-Agent-HR
|-- gbm-gateway           # API网关服务
|-- gbm-auth              # 认证授权服务
|-- gbm-recruit           # 招聘管理微服务
|   |-- recruit-channel   # 招聘渠道Agent
|   |-- recruit-resume    # 简历筛选Agent
|   |-- recruit-exam      # 考试组卷/阅卷Agent
|   |-- recruit-talent    # 人才库管理
|-- gbm-onboard           # 入职管理微服务
|   |-- onboard-guide     # 入职引导Agent
|   |-- onboard-ocr       # OCR识别Agent
|   |-- onboard-face      # 人脸识别Agent
|-- gbm-training          # 培训管理微服务
|   |-- training-plan     # 培训计划Agent
|   |-- training-signin   # 签到管理
|   |-- training-video    # 教材转视频Agent
|   |-- training-audit    # 体系审核资料Agent
|-- gbm-attendance        # 考勤管理微服务
|-- gbm-payroll           # 薪资管理微服务
|   |-- payroll-calc      # 薪资核算Agent
|   |-- payroll-slip      # 工资条Agent
|-- gbm-performance       # 绩效管理微服务
|-- gbm-external          # 外务管理微服务
|   |-- external-injury   # 工伤Agent
|   |-- external-fund     # 公积金Agent
|   |-- external-rpa      # RPA引擎
|-- gbm-procedure         # 证明开具微服务
|-- gbm-budget            # 预算费用微服务
|-- gbm-analysis          # 数据分析微服务
|-- gbm-orchestration     # Agent编排调度服务
|-- gbm-rpa-engine        # RPA自动化引擎服务
|-- gbm-audit             # 审计日志服务
```

### 1.5 技术栈选型

| 技术领域 | 选型 | 选型理由 |
|---------|------|---------|
| 前端框架 | Vue 3 + TypeScript + Vite | 响应式、TypeScript支持、构建速度快 |
| 移动端 | Uni-app | 一套代码多端发布(H5/小程序) |
| UI组件库 | Element Plus + TailwindCSS | 成熟的后台组件 + 原子化CSS |
| 后端语言 | Java 17 + Spring Boot 3.x | 企业级、微服务生态完善 |
| Python服务 | Python 3.11 + FastAPI | AI模型调用、异步高性能 |
| 微服务框架 | Spring Cloud Alibaba 2022.x | Nacos注册中心、Sentinel限流 |
| 流程引擎 | Camunda 8 (Zeebe) | 原生Cloud-native、ZK编排 |
| 消息队列 | Apache Kafka 3.x | 高吞吐、Agent间事件驱动 |
| 任务调度 | XXL-Job 2.4.x | 分布式定时任务、Agent定时触发 |
| 关系数据库 | MySQL 8.0 (主从) | 成熟稳定、JSON字段支持 |
| 缓存 | Redis 7.x Cluster | 高性能、分布式锁、会话管理 |
| 对象存储 | MinIO (本地) / Aliyun OSS (云) | S3兼容、私有部署 |
| 搜索引擎 | Elasticsearch 8.x | 简历全文检索、日志检索 |
| 向量数据库 | Milvus 2.x | 简历向量化检索、Embedding存储 |
| OCR引擎 | PaddleOCR 2.7 (本地部署) | 中文识别精度高、可私有部署 |
| 人脸识别 | 旷视Face++ API / 本地ArcFace | 活体检测、身份证比对 |
| LLM推理 | vLLM + Qwen 72B / Claude API | 高吞吐推理、中英双语 |
| Embedding | bge-m3 (本地) / text-embedding-3 | 多语言、长文本 |
| RPA引擎 | Playwright (Python/Node) | 无头浏览器、反检测能力 |
| 容器编排 | Kubernetes 1.28+ | 弹性伸缩、自愈 |
| CI/CD | GitLab CI / GitHub Actions | 自动化构建部署 |
| 监控 | Prometheus + Grafana | 指标采集与可视化 |
| 链路追踪 | Jaeger | 全链路Agent调用追踪 |
| 日志 | ELK (ES+Logstash+Kibana) | 日志聚合与分析 |

### 1.6 部署架构

#### 1.6.1 Kubernetes 集群部署拓扑

```
+--------------------------------------------------------------+
|                     Ingress (Nginx/Traefik)                   |
+--------------------------------------------------------------+
|                     Kubernetes Cluster                        |
|                                                              |
|  +----------------+  +----------------+  +----------------+  |
|  | Node Pool A    |  | Node Pool A    |  | Node Pool B    |  |
|  | (应用服务)     |  | (应用服务)     |  | (AI推理服务)   |  |
|  +----------------+  +----------------+  +----------------+  |
|  | gbm-gateway x2 |  | gbm-auth x2    |  | vLLM-llm x2    |  |
|  | gbm-recruit x2 |  | gbm-onboard x2 |  | paddle-ocr x2  |  |
|  | gbm-training x2|  | gbm-payroll x2 |  | face-api x2    |  |
|  | gbm-attendance |  | gbm-external x2|  | milvus x3      |  |
|  | gbm-procedure  |  | gbm-rpa x2     |  +----------------+  |
|  | gbm-analysis   |  | gbm-orchestration|                    |
|  | gbm-audit      |  | Camunda-zeebe x2|  +----------------+  |
|  +----------------+  +----------------+  | Data Layer       |
|                                          | MySQL-Primary x1 |  |
|                                          | MySQL-Replica x2 |  |
|                                          | Redis-Cluster x6 |  |
|                                          | Kafka x3         |  |
|                                          | ES x3            |  |
|                                          | MinIO x3         |  |
|                                          +----------------+  |
+--------------------------------------------------------------+
|                     外部服务                                  |
|  LLM API (云端) | 短信服务 | 邮件服务 | 招聘平台 API | 社保 API |
+--------------------------------------------------------------+
```

#### 1.6.2 部署模式对比与推荐

| 维度 | 公有云SaaS | 私有云 | 混合部署(推荐) |
|------|-----------|--------|--------------|
| 数据安全性 | 依赖云服务商 | 完全自主 | 敏感数据本地、AI推理云端 |
| 运维成本 | 低 | 高 | 中等 |
| AI推理成本 | 按量付费 | GPU采购 | 小模型本地、大模型云端 |
| 合规性 | 需确认数据出境 | 完全合规 | 本地存储满足PIPL |
| 推荐场景 | 中小企业 | 大型国企 | 本系统推荐此模式 |

#### 1.6.3 网络架构

```
Internet
  |
  v
[ WAF / 防火墙 ]
  |
  v
[ Nginx Ingress Controller ] ---- SSL/TLS 终结
  |
  +-- /api/* -----> API Gateway (Spring Cloud Gateway)
  +-- /ws/* -----> WebSocket Gateway (实时通知)
  +-- /static/* -----> Nginx 静态资源
  +-- /qr/* -----> 二维码服务
  |
  v
[ 内部服务网格 (Istio) ]
  |
  +-- gbm-gateway <-> gbm-auth (鉴权)
  +-- gbm-gateway <-> gbm-recruit (招聘)
  +-- gbm-gateway <-> gbm-onboard (入职)
  +-- ... (其他微服务)
  |
  v
[ 数据层 ]
  +-- MySQL 主从集群
  +-- Redis Cluster
  +-- Kafka Cluster
  +-- MinIO 集群
  +-- Elasticsearch 集群
  +-- Milvus 向量库
```

### 1.7 Agent 编排架构

#### 1.7.1 编排模式

```
Pipeline 模式 (入职流程):
  扫码 -> 引导Agent -> 上传材料 -> OCR Agent -> 人脸Agent -> 档案生成 -> 完成

Fan-Out/Fan-In 模式 (薪资核算):
                    +-- 考勤Agent --+
                   |               |
  触发核算 --> 编排层                  --> 汇总计算 --> 输出薪资明细
                   |               |
                    +-- 社保Agent --+
                   |               |
                    +-- 公积金Agent--+

Decision Tree 模式 (简历筛选):
  抓取简历 --> 评分Agent --> [>80] --> 高潜(自动入库)
                         --> [60-80] --> 候选(人工审核)
                         --> [<60] --> 淘汰(自动归档)

Feedback Loop 模式 (RPA申报):
  RPA Agent 执行 --> 成功? --> 是 --> 归档
                 --> 否 --> 重试(最多3次) --> 仍失败? --> 挂起告警
```

#### 1.7.2 Agent 通信协议

```json
{
  "message_id": "uuid-v4",
  "trace_id": "distributed-trace-id",
  "source_agent": "recruit-resume-agent",
  "target_agent": "recruit-match-agent",
  "event_type": "resume.captured",
  "priority": "normal",
  "ttl_seconds": 3600,
  "payload": {
    "business_id": "req-2026-0612-001",
    "data": {}
  },
  "timestamp": "2026-06-12T10:30:00Z"
}
```

### 1.8 安全架构

```
+--------------------------------------------------------------+
|  安全边界                                                   |
+--------------------------------------------------------------+
|                                                              |
|  [WAF] --> [Nginx SSL] --> [API Gateway 认证鉴权]            |
|                        |                                    |
|                        +-- RBAC 权限校验                     |
|                        +-- JWT Token 验证                    |
|                        +-- MFA 强制场景                      |
|                        +-- IP 白名单/黑名单                  |
|                        +-- 请求限流 (Sentinel)               |
|                        +-- 防注入过滤                        |
|                                                              |
|  [数据加密层]                                               |
|    AES-256 敏感字段加密存储                                   |
|    TLS 1.3 传输加密                                          |
|    密钥管理 (HashiCorp Vault)                                 |
|                                                              |
|  [审计层]                                                   |
|    全量操作审计日志                                          |
|    不可篡改 (写入ES后只读)                                    |
|    保留 >= 10 年                                             |
|                                                              |
|  [AI安全护栏]                                               |
|    Prompt 注入过滤                                           |
|    输出合理性校验                                            |
|    金额/删除操作二次确认                                      |
|                                                              |
+--------------------------------------------------------------+
```

---

# 前端设计文档 (GBM AI Agent HR - Frontend Design)

## 1. 前端技术栈

| 技术领域 | 选型 | 版本 | 说明 |
|---------|------|------|------|
| 核心框架 | Vue 3 | 3.4+ | Composition API + `<script setup>` |
| 语言 | TypeScript | 5.3+ | 类型安全 |
| 构建工具 | Vite | 5.x | 极速构建 |
| 状态管理 | Pinia | 2.1+ | Vue 3 官方状态管理 |
| 路由 | Vue Router | 4.x | 路由管理与守卫 |
| UI组件库 | Element Plus | 2.5+ | 后台管理系统组件 |
| 原子CSS | TailwindCSS | 3.4+ | 响应式布局 |
| HTTP客户端 | Axios | 1.6+ | 请求拦截、Token注入 |
| 图表 | ECharts | 5.4+ | 数据分析可视化 |
| 移动端 | Uni-app | 3.0+ | H5/小程序多端 |
| 富文本 | WangEditor | 5.x | 报告编辑 |
| 文件预览 | PDF.js + XDocReader | - | 简历/证件预览 |
| 二维码 | qrcode.vue + webrtc-qr | - | 生成与扫码 |
| 测试 | Vitest + Vue Test Utils | - | 单元测试 |
| E2E测试 | Playwright | - | 端到端测试 |
| 国际化 | vue-i18n | 9.x | 中英双语切换 |
| 无障碍 | @vueuse/core + aria-props | - | WCAG 2.1 AA |

## 2. 项目结构

```
gbm-ai-agent-hr-frontend/
|-- public/
|   |-- favicon.ico
|   |-- static/
|       |-- logos/
|       |-- help/
|-- src/
|   |-- assets/
|   |   |-- styles/
|   |   |   |-- global.scss          # 全局样式
|   |   |   |-- variables.scss       # 主题变量
|   |   |   |-- dark-theme.scss      # 暗色主题
|   |   |-- images/
|   |   |-- icons/                   # SVG图标
|   |-- components/
|   |   |-- common/                  # 通用组件
|   |   |   |-- GbmHeader.vue
|   |   |   |-- GbmSidebar.vue
|   |   |   |-- GbmBreadcrumb.vue
|   |   |   |-- GbmTable.vue         # 封装Element表格
|   |   |   |-- GbmPagination.vue
|   |   |   |-- GbmSearchBar.vue
|   |   |   |-- GbmStatusTag.vue
|   |   |   |-- GbmAuditLog.vue      # 审计日志组件
|   |   |-- agent/                   # Agent相关组件
|   |   |   |-- AgentStatusCard.vue  # Agent状态卡片
|   |   |   |-- AgentProgress.vue    # Agent执行进度
|   |   |   |-- AgentChainView.vue   # 思维链查看器
|   |   |   |-- AgentAlertBanner.vue # Agent异常告警
|   |   |-- recruitment/
|   |   |   |-- ResumeCard.vue
|   |   |   |-- ResumeScorePanel.vue
|   |   |   |-- ExamPaperViewer.vue
|   |   |   |-- TalentProfile.vue
|   |   |-- onboarding/
|   |   |   |-- DocumentUploader.vue
|   |   |   |-- OCRPreview.vue
|   |   |   |-- FaceCapture.vue
|   |   |   |-- ESignaturePad.vue    # 电子签名板
|   |   |-- training/
|   |   |   |-- QRCheckIn.vue        # 扫码签到
|   |   |   |-- VideoPlayer.vue
|   |   |   |-- ExamInterface.vue
|   |   |-- payroll/
|   |   |   |-- PayrollSlip.vue      # 工资条
|   |   |   |-- PayrollAudit.vue     # 薪资审核
|   |   |   |-- TaxCalculator.vue
|   |   |-- attendance/
|   |   |   |-- AttendanceCalendar.vue
|   |   |   |-- AttendanceAnomaly.vue
|   |   |-- external/
|   |   |   |-- InjuryReportForm.vue
|   |   |   |-- FundOperation.vue
|   |   |   |-- RPAMonitor.vue       # RPA实时监控
|   |   |-- dashboard/
|   |   |   |-- KPIDashboard.vue
|   |   |   |-- AgentMonitor.vue
|   |   |   |-- SystemHealth.vue
|   |-- views/                       # 页面视图
|   |   |-- login/
|   |   |   |-- Login.vue
|   |   |   |-- MFAVerify.vue
|   |   |-- layout/
|   |   |   |-- AdminLayout.vue      # 管理员布局
|   |   |   |-- HRLayout.vue         # 人事专员布局
|   |   |   |-- ManagerLayout.vue    # 主管布局
|   |   |   |-- EmployeeLayout.vue   # 员工自助布局
|   |   |-- dashboard/
|   |   |   |-- AdminDashboard.vue
|   |   |   |-- HRDashboard.vue
|   |   |   |-- ManagerDashboard.vue
|   |   |   |-- EmployeeDashboard.vue
|   |   |-- recruitment/
|   |   |   |-- JobPostManage.vue
|   |   |   |-- ResumeList.vue
|   |   |   |-- ResumeDetail.vue
|   |   |   |-- ResumeReview.vue     # 候选简历审核
|   |   |   |-- ExamManage.vue
|   |   |   |-- ExamResult.vue
|   |   |   |-- TalentPool.vue
|   |   |-- onboarding/
|   |   |   |-- OnboardGuide.vue     # 新员工引导页
|   |   |   |-- OnboardProgress.vue
|   |   |   |-- DocumentArchive.vue
|   |   |-- training/
|   |   |   |-- TrainingPlan.vue
|   |   |   |-- TrainingSignin.vue
|   |   |   |-- TrainingExam.vue
|   |   |   |-- TrainingVideo.vue
|   |   |   |-- TrainingAudit.vue    # 体系审核
|   |   |-- attendance/
|   |   |   |-- AttendanceOverview.vue
|   |   |   |-- AttendanceDetail.vue
|   |   |   |-- AnomalyReview.vue
|   |   |-- payroll/
|   |   |   |-- PayrollCalc.vue      # 薪资核算结果
|   |   |   |-- PayrollAudit.vue     # 薪资审核页
|   |   |   |-- PayrollSlipView.vue  # 工资条查看
|   |   |   |-- SalaryRule.vue       # 薪资规则管理
|   |   |-- performance/
|   |   |   |-- PerfEvaluation.vue
|   |   |   |-- PerfSummary.vue
|   |   |-- external/
|   |   |   |-- InjuryCase.vue
|   |   |   |-- FundManage.vue
|   |   |   |-- ExternalReview.vue
|   |   |-- procedure/
|   |   |   |-- CertificateApply.vue
|   |   |   |-- CertificateAudit.vue
|   |   |-- employee/                # 员工自助
|   |   |   |-- SelfService.vue
|   |   |   |-- MyPayroll.vue
|   |   |   |-- MyAttendance.vue
|   |   |   |-- MyTraining.vue
|   |   |   |-- MyCertificates.vue
|   |   |-- system/                  # 系统管理
|   |   |   |-- UserManage.vue
|   |   |   |-- RoleManage.vue
|   |   |   |-- AgentConfig.vue
|   |   |   |-- AuditLog.vue
|   |   |   |-- SystemMonitor.vue
|   |   |   |-- NotificationManage.vue
|   |-- stores/                      # Pinia 状态管理
|   |   |-- modules/
|   |   |   |-- user.ts              # 用户状态
|   |   |   |-- auth.ts              # 认证状态
|   |   |   |-- recruit.ts           # 招聘状态
|   |   |   |-- onboarding.ts
|   |   |   |-- training.ts
|   |   |   |-- attendance.ts
|   |   |   |-- payroll.ts
|   |   |   |-- performance.ts
|   |   |   |-- external.ts
|   |   |   |-- agentStatus.ts       # Agent运行状态
|   |   |   |-- notification.ts      # 通知消息
|   |   |   |-- theme.ts             # 主题设置
|   |-- router/
|   |   |-- index.ts                 # 路由配置
|   |   |-- guards.ts                # 路由守卫
|   |   |-- routes/
|   |       |-- admin.ts
|   |       |-- hr.ts
|   |       |-- manager.ts
|   |       |-- employee.ts
|   |       |-- public.ts
|   |-- api/                         # API 接口层
|   |   |-- request.ts               # Axios 实例
|   |   |-- modules/
|   |       |-- auth.ts
|   |       |-- recruit.ts
|   |       |-- onboarding.ts
|   |       |-- training.ts
|   |       |-- attendance.ts
|   |       |-- payroll.ts
|   |       |-- performance.ts
|   |       |-- external.ts
|   |       |-- procedure.ts
|   |       |-- system.ts
|   |       |-- agent.ts
|   |-- utils/                       # 工具函数
|   |   |-- validate.ts              # 表单校验
|   |   |-- date.ts                  # 日期处理
|   |   |-- encrypt.ts               # 加密工具
|   |   |-- download.ts              # 文件下载
|   |   |-- i18n.ts                  # 国际化
|   |   |-- accessibility.ts         # 无障碍工具
|   |-- types/                       # TypeScript 类型
|   |   |-- user.ts
|   |   |-- recruit.ts
|   |   |-- payroll.ts
|   |   |-- common.ts
|   |-- locales/                     # 国际化语言包
|   |   |-- zh-CN/
|   |   |   |-- common.json
|   |   |   |-- recruit.json
|   |   |   |-- payroll.json
|   |   |-- en/
|   |       |-- common.json
|   |       |-- recruit.json
|   |-- App.vue
|   |-- main.ts
|-- tests/
|   |-- unit/
|   |-- e2e/
|   |-- accessibility/               # 无障碍测试
|-- index.html
|-- vite.config.ts
|-- tsconfig.json
|-- tailwind.config.js
|-- package.json
```

## 3. 路由设计

### 3.1 路由结构

```typescript
// 公共路由 (无需登录)
const publicRoutes = [
  { path: '/login', name: 'Login', component: Login },
  { path: '/onboard/:token', name: 'OnboardGuide', component: OnboardGuide },
  { path: '/exam/:examToken', name: 'ExamInterface', component: ExamInterface },
  { path: '/qr/signin/:qrToken', name: 'QRSignin', component: QRCheckIn },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFound },
];

// 管理员路由
const adminRoutes = {
  path: '/admin',
  component: AdminLayout,
  meta: { roles: ['ADMIN'] },
  children: [
    { path: 'dashboard', name: 'AdminDashboard', component: AdminDashboard },
    { path: 'users', name: 'UserManage', component: UserManage },
    { path: 'roles', name: 'RoleManage', component: RoleManage },
    { path: 'agents', name: 'AgentConfig', component: AgentConfig },
    { path: 'audit-log', name: 'AuditLog', component: AuditLog },
    { path: 'monitor', name: 'SystemMonitor', component: SystemMonitor },
    { path: 'notifications', name: 'NotificationManage', component: NotificationManage },
  ],
};

// 人事专员路由
const hrRoutes = {
  path: '/hr',
  component: HRLayout,
  meta: { roles: ['HR_SPECIALIST', 'HR_MANAGER'] },
  children: [
    { path: 'dashboard', name: 'HRDashboard', component: HRDashboard },
    // 招聘管理
    { path: 'recruit/jobs', name: 'JobPostManage', component: JobPostManage },
    { path: 'recruit/resumes', name: 'ResumeList', component: ResumeList },
    { path: 'recruit/resume/:id', name: 'ResumeDetail', component: ResumeDetail },
    { path: 'recruit/review', name: 'ResumeReview', component: ResumeReview },
    { path: 'recruit/exams', name: 'ExamManage', component: ExamManage },
    { path: 'recruit/exam-results', name: 'ExamResult', component: ExamResult },
    { path: 'recruit/talent-pool', name: 'TalentPool', component: TalentPool },
    // 入职管理
    { path: 'onboard/progress', name: 'OnboardProgress', component: OnboardProgress },
    { path: 'onboard/archive', name: 'DocumentArchive', component: DocumentArchive },
    // 培训管理
    { path: 'training/plans', name: 'TrainingPlan', component: TrainingPlan },
    { path: 'training/videos', name: 'TrainingVideo', component: TrainingVideo },
    { path: 'training/audit', name: 'TrainingAudit', component: TrainingAudit },
    // 考勤管理
    { path: 'attendance/overview', name: 'AttendanceOverview', component: AttendanceOverview },
    { path: 'attendance/anomaly', name: 'AnomalyReview', component: AnomalyReview },
    // 薪资管理
    { path: 'payroll/calc', name: 'PayrollCalc', component: PayrollCalc },
    { path: 'payroll/audit', name: 'PayrollAudit', component: PayrollAudit },
    { path: 'payroll/rules', name: 'SalaryRule', component: SalaryRule },
    // 绩效管理
    { path: 'performance/evaluation', name: 'PerfEvaluation', component: PerfEvaluation },
    { path: 'performance/summary', name: 'PerfSummary', component: PerfSummary },
    // 外务管理
    { path: 'external/injury', name: 'InjuryCase', component: InjuryCase },
    { path: 'external/fund', name: 'FundManage', component: FundManage },
    { path: 'external/review', name: 'ExternalReview', component: ExternalReview },
    // 证明管理
    { path: 'procedure/audit', name: 'CertificateAudit', component: CertificateAudit },
  ],
};

// 部门主管路由
const managerRoutes = {
  path: '/manager',
  component: ManagerLayout,
  meta: { roles: ['DEPT_MANAGER'] },
  children: [
    { path: 'dashboard', name: 'ManagerDashboard', component: ManagerDashboard },
    { path: 'recruit/approval', name: 'RecruitApproval', component: RecruitApproval },
    { path: 'performance/evaluation', name: 'PerfEvaluation', component: PerfEvaluation },
    { path: 'performance/summary', name: 'PerfSummary', component: PerfSummary },
    { path: 'team/report', name: 'TeamReport', component: TeamReport },
  ],
};

// 员工自助路由
const employeeRoutes = {
  path: '/employee',
  component: EmployeeLayout,
  meta: { roles: ['EMPLOYEE'] },
  children: [
    { path: 'dashboard', name: 'EmployeeDashboard', component: EmployeeDashboard },
    { path: 'payroll', name: 'MyPayroll', component: MyPayroll },
    { path: 'attendance', name: 'MyAttendance', component: MyAttendance },
    { path: 'training', name: 'MyTraining', component: MyTraining },
    { path: 'certificates', name: 'MyCertificates', component: MyCertificates },
    { path: 'procedure', name: 'SelfService', component: SelfService },
  ],
};
```

### 3.2 路由守卫

```typescript
// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  // 1. 标题设置
  document.title = `${to.meta.title || 'GBM HR'} - GBM AI Agent HR`;

  // 2. 公共路由直接放行
  if (publicRoutes.find(r => r.path === to.path)) {
    return next();
  }

  // 3. Token 检查
  const token = useAuthStore().token;
  if (!token) {
    return next({ path: '/login', query: { redirect: to.fullPath } });
  }

  // 4. Token 刷新 (JWT 即将过期)
  if (isTokenExpiringSoon()) {
    await refreshAccessToken();
  }

  // 5. 角色权限检查
  const userRoles = useUserStore().roles;
  const requiredRoles = to.meta.roles as string[];
  if (requiredRoles && !requiredRoles.some(r => userRoles.includes(r))) {
    return next({ path: '/403' });
  }

  // 6. 行级权限 (部门数据隔离)
  if (to.meta.requireDeptScope) {
    const deptId = useUserStore().deptId;
    // 后端已做行级过滤，前端仅做展示
  }

  // 7. MFA 强制场景
  const mfaRequiredPaths = ['/hr/payroll/audit', '/admin/users'];
  if (mfaRequiredPaths.includes(to.path) && !useAuthStore().mfaVerified) {
    return next({ path: '/mfa-verify', query: { redirect: to.fullPath } });
  }

  next();
});
```

## 4. 状态管理设计 (Pinia)

### 4.1 核心 Store 列表

```typescript
// user.ts - 用户信息状态
export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null as UserInfo | null,
    roles: [] as string[],
    deptId: '' as string,
    permissions: [] as string[],
  }),
  actions: {
    async fetchUserInfo() { /* ... */ },
    async updateProfile(data: Partial<UserInfo>) { /* ... */ },
  },
});

// auth.ts - 认证状态
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '' as string,
    refreshToken: '' as string,
    mfaVerified: false,
    mfaToken: '' as string,
  }),
  actions: {
    async login(credentials: LoginCredentials) { /* ... */ },
    async verifyMFA(code: string) { /* ... */ },
    async refreshAccessToken() { /* ... */ },
    logout() { /* ... */ },
  },
});

// agentStatus.ts - Agent 运行状态 (全局)
export const useAgentStatusStore = defineStore('agentStatus', {
  state: () => ({
    agents: {} as Record<string, AgentStatus>,
    alerts: [] as Alert[],
    wsConnection: null as WebSocket | null,
  }),
  actions: {
    connectWebSocket() {
      // 建立WebSocket连接，实时接收Agent状态更新
      this.wsConnection = new WebSocket(wsUrl);
      this.wsConnection.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.updateAgentStatus(data);
      };
    },
    updateAgentStatus(data: AgentStatusUpdate) { /* ... */ },
    dismissAlert(alertId: string) { /* ... */ },
  },
});

// recruit.ts - 招聘模块状态
export const useRecruitStore = defineStore('recruit', {
  state: () => ({
    jobList: [] as JobPost[],
    resumeList: [] as Resume[],
    currentResume: null as Resume | null,
    examList: [] as Exam[],
    filters: {
      position: '',
      scoreRange: [0, 100],
      classify: '',
      dateRange: [] as Date[],
    },
    pagination: { page: 1, pageSize: 20, total: 0 },
  }),
  getters: {
    highPotentialResumes: (state) =>
      state.resumeList.filter(r => r.classifyResult === '高潜'),
    pendingReviewResumes: (state) =>
      state.resumeList.filter(r => r.classifyResult === '候选'),
  },
  actions: {
    async fetchResumes(params?: QueryParams) { /* ... */ },
    async fetchResumeDetail(id: string) { /* ... */ },
    async reviewResume(id: string, action: 'accept' | 'reject') { /* ... */ },
    async searchTalentPool(query: string) { /* 自然语言搜索 */ },
  },
});

// payroll.ts - 薪资模块状态
export const usePayrollStore = defineStore('payroll', {
  state: () => ({
    currentMonth: '' as string,
    payrollData: [] as PayrollRecord[],
    anomalies: [] as AnomalyRecord[],
    auditStatus: 'pending' as 'pending' | 'reviewing' | 'approved',
    summary: null as PayrollSummary | null,
  }),
  actions: {
    async fetchPayroll(month: string) { /* ... */ },
    async reviewPayroll(recordIds: string[], action: 'approve' | 'reject') { /* ... */ },
    async fetchSummary(month: string) { /* ... */ },
  },
});
```

### 4.2 全局状态数据流

```
用户登录 -> auth.store.setToken()
         -> user.store.fetchUserInfo()
         -> 路由守卫检查角色
         -> 页面渲染
         -> agentStatus.store.connectWebSocket() [实时Agent状态]

页面切换 -> 路由守卫 -> 权限检查 -> 加载对应store数据

Agent 执行 -> WebSocket推送 -> agentStatus.store.update()
          -> 页面自动刷新Agent状态卡片

薪资核算 -> payroll.store.fetchPayroll()
        -> 显示核算结果
        -> HR审核 -> payroll.store.reviewPayroll()
        -> 后端记录审计日志
```

## 5. 页面布局设计

### 5.1 管理员布局 (AdminLayout)

```
+------------------------------------------------------------------+
| [Logo] GBM AI Agent HR                   [通知][语言][管理员头像] |
+------------------------------------------------------------------+
|                                                                  |
|  [侧边栏]                          [主内容区]                    |
|  --------------------------------   --------------------------   |
|  > 系统总览                        |                            |
|    仪表盘                          |   [面包屑: 首页 / 仪表盘]  |
|    Agent监控                       |                            |
|    告警中心                        |   [主内容区域]             |
|                                    |                            |
|  用户管理                          |                            |
|    用户列表                        |                            |
|    角色权限                        |                            |
|                                    |                            |
|  系统配置                          |                            |
|    Agent参数                       |                            |
|    通知管理                        |                            |
|    审计日志                        |                            |
|                                    |                            |
|  运维中心                          |                            |
|    系统监控                        |                            |
|    备份管理                        |                            |
|                                    |                            |
+------------------------------------------------------------------+
| [底部状态栏] Agent运行: 正常 | 系统负载: 32% | 最后刷新: 10:30:05|
+------------------------------------------------------------------+
```

### 5.2 人事专员布局 (HRLayout)

```
+------------------------------------------------------------------+
| [Logo] GBM AI Agent HR                   [待办:3][语言][头像]   |
+------------------------------------------------------------------+
|  [顶部快捷导航]                                                   |
|  [招聘][入职][培训][考勤][薪资][绩效][外务][证明]                  |
+------------------------------------------------------------------+
|  [侧边栏-当前模块子菜单]     [主内容区]                          |
|  --------------------------   --------------------------          |
|  > 招聘岗位                 |                                    |
|    简历管理                 |   [Agent状态横幅 - 可选收起]       |
|    简历审核 (3待审)         |   [当前页面内容]                   |
|    考试管理                 |                                    |
|    人才库                   |                                    |
|                            |                                    |
|  [右侧: 待办事项面板]       |                                    |
|  --------------------------   待办事项 (可折叠)                  |
|                            |  - 简历审核 3 条                    |
|                            |  - 薪资审核 (本月)                  |
|                            |  - 证书到期提醒 2 个                |
+------------------------------------------------------------------+
| [底部] 快速操作: [发起招聘][批量导入][导出报表]                    |
+------------------------------------------------------------------+
```

### 5.3 员工自助布局 (EmployeeLayout)

```
+------------------------------------------------------------------+
| [Logo] GBM 员工自助                                              |
+------------------------------------------------------------------+
|                                                                  |
|  +-------------+  +-------------+  +-------------+              |
|  |  我的工资   |  |  我的考勤   |  |  我的培训   |              |
|  |  本月      |  |  本月      |  |  进行中     |              |
|  |  ¥8,520.00 |  |  出勤22天  |  |  安全培训   |              |
|  +-------------+  +-------------+  +-------------+              |
|                                                                  |
|  +-------------+  +-------------+                               |
|  |  证明申请   |  |  消息通知   |                               |
|  |            |  |  2 条未读   |                               |
|  +-------------+  +-------------+                               |
|                                                                  |
|  [底部导航: 首页 | 工资条 | 考勤 | 培训 | 我的]                   |
+------------------------------------------------------------------+
```

### 5.4 移动端适配策略

- PC端 (>1200px): 侧边栏布局 + 多列内容
- 平板端 (768-1200px): 可折叠侧边栏 + 双列内容
- 移动端 (<768px): 底部Tab导航 + 单列内容 + 卡片式布局
- 扫码页面: 全屏摄像头预览 + 底部操作按钮

---

# 后端设计文档 (GBM AI Agent HR - Backend Design)

## 1. 后端技术栈

| 技术领域 | 选型 | 版本 | 说明 |
|---------|------|------|------|
| 运行时 | Java | 17 LTS | 微服务基础 |
| Web框架 | Spring Boot | 3.2+ | 自动配置、内嵌Tomcat |
| 微服务 | Spring Cloud Alibaba | 2022.x | Nacos/Sentinel/Sentinel |
| AI服务 | Python + FastAPI | 3.11 / 0.109 | Agent AI逻辑 |
| ORM | MyBatis-Plus | 3.5+ | 数据访问层 |
| 流程引擎 | Camunda 8 (Zeebe) | 8.3+ | 业务流程编排 |
| 消息队列 | Apache Kafka | 3.6+ | Agent间事件驱动 |
| 任务调度 | XXL-Job | 2.4.0 | 定时任务 |
| 缓存 | Redis + Spring Cache | 7.x | 缓存/分布式锁 |
| 对象存储 | MinIO SDK | 8.5+ | 文件存储 |
| 搜索 | Elasticsearch + Spring Data ES | 8.x | 简历搜索/日志 |
| 向量库 | Milvus Python SDK | 2.4+ | 简历Embedding |
| OCR | PaddleOCR Python SDK | 2.7 | 证件识别 |
| 人脸识别 | Face++ SDK / ArcFace | - | 人脸比对 |
| LLM | vLLM + OpenAI兼容API | - | 大模型推理 |
| RPA | Playwright Python | 1.40+ | 浏览器自动化 |
| 配置中心 | Nacos | 2.3+ | 动态配置 |
| 服务注册 | Nacos | 2.3+ | 服务发现 |
| 限流熔断 | Sentinel | 1.8+ | 流量保护 |
| API文档 | SpringDoc OpenAPI 3 | 2.3+ | 接口文档 |
| 单元测试 | JUnit 5 + Mockito | 5.10+ | 单元/集成测试 |
| 链路追踪 | Jaeger + Micrometer | - | 分布式追踪 |
| 加密 | Bouncy Castle + Jasypt | - | 数据加密/密钥 |

## 2. 微服务架构

### 2.1 服务清单与端口

| 服务名 | 端口 | 语言 | 职责 |
|--------|------|------|------|
| gbm-gateway | 8080 | Java | API网关 |
| gbm-auth | 8081 | Java | 认证授权 |
| gbm-recruit | 8082 | Java | 招聘管理 |
| gbm-recruit-ai | 9001 | Python | 招聘AI Agent |
| gbm-onboard | 8083 | Java | 入职管理 |
| gbm-onboard-ai | 9002 | Python | 入职AI Agent (OCR/人脸) |
| gbm-training | 8084 | Java | 培训管理 |
| gbm-training-ai | 9003 | Python | 培训AI Agent |
| gbm-attendance | 8085 | Java | 考勤管理 |
| gbm-payroll | 8086 | Java | 薪资管理 |
| gbm-payroll-ai | 9004 | Python | 薪资AI Agent |
| gbm-performance | 8087 | Java | 绩效管理 |
| gbm-external | 8088 | Java | 外务管理 |
| gbm-external-rpa | 9005 | Python | RPA引擎 |
| gbm-procedure | 8089 | Java | 证明开具 |
| gbm-budget | 8090 | Java | 预算费用 |
| gbm-analysis | 8091 | Java | 数据分析 |
| gbm-orchestration | 8092 | Java | Agent编排 |
| gbm-audit | 8093 | Java | 审计日志 |

### 2.2 服务间通信

```
+------------------+       HTTP/gRPC       +------------------+
|  Java 微服务     | <---------------------> |  Python AI服务   |
|  (Spring Boot)   |       内部 REST API    |  (FastAPI)       |
+------------------+                        +------------------+
        |                                          |
        |  Kafka 事件                              |  Kafka 事件
        +------------------------------------------+
                     |
                     v
        +------------------+
        |  Camunda 8 (Zeebe) |
        |  流程编排引擎       |
        +------------------+
                     |
                     v
        +------------------+
        |  XXL-Job 调度中心   |
        |  定时任务触发       |
        +------------------+
```

## 3. API 接口设计

### 3.1 API 设计规范

- 统一前缀: `/api/v1`
- 资源复数命名: `/api/v1/resumes`, `/api/v1/payrolls`
- 动词+资源 (非CRUD操作): `/api/v1/payrolls/{id}/approve`
- 分页参数: `page`, `pageSize`, `sortField`, `sortOrder`
- 统一响应格式:

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "traceId": "abc-123-def"
}
```

### 3.2 认证授权 API (gbm-auth)

```
POST   /api/v1/auth/login              # 用户登录
POST   /api/v1/auth/logout             # 用户登出
POST   /api/v1/auth/mfa/verify         # MFA 验证
POST   /api/v1/auth/token/refresh      # Token 刷新
POST   /api/v1/auth/password/reset     # 密码重置

GET    /api/v1/auth/user/info          # 获取当前用户信息
PUT    /api/v1/auth/user/profile       # 更新用户资料
POST   /api/v1/auth/password/change    # 修改密码
```

### 3.3 招聘管理 API (gbm-recruit)

```
# 岗位管理
POST   /api/v1/jobs                    # 创建岗位需求
GET    /api/v1/jobs                    # 岗位列表
GET    /api/v1/jobs/{id}              # 岗位详情
PUT    /api/v1/jobs/{id}              # 更新岗位
DELETE /api/v1/jobs/{id}              # 下架岗位
POST   /api/v1/jobs/{id}/publish      # 发布到招聘平台 (Agent触发)

# 简历管理
POST   /api/v1/resumes/import/batch    # 批量导入简历
GET    /api/v1/resumes                 # 简历列表 (支持筛选)
GET    /api/v1/resumes/{id}           # 简历详情 (含评分)
POST   /api/v1/resumes/{id}/review    # 审核候选简历
POST   /api/v1/resumes/search/nl      # 自然语言搜索人才库

# Agent 触发接口
POST   /api/v1/agent/resume/capture   # 触发简历抓取Agent
POST   /api/v1/agent/resume/score     # 触发简历评分Agent
GET    /api/v1/resumes/{id}/score/trace # 获取评分思维链

# 考试管理
POST   /api/v1/exams/generate         # Agent生成试卷
GET    /api/v1/exams                  # 考试列表
GET    /api/v1/exams/{id}/paper       # 获取试卷
POST   /api/v1/exams/{id}/submit      # 提交答卷
GET    /api/v1/exams/{id}/results     # 考试成绩
POST   /api/v1/agent/exam/grade       # 触发挥发阅卷Agent
```

### 3.4 入职管理 API (gbm-onboard)

```
# 入职引导
GET    /api/v1/onboard/{token}/guide  # 获取入职引导流程
POST   /api/v1/onboard/{token}/upload # 上传材料
GET    /api/v1/onboard/{token}/status # 入职进度查询
POST   /api/v1/onboard/{token}/sign   # 电子签名

# Agent 操作
POST   /api/v1/agent/ocr/recognize    # OCR识别证件
POST   /api/v1/agent/face/capture     # 人脸采集
POST   /api/v1/agent/face/compare     # 人脸比对
POST   /api/v1/agent/onboard/create   # 创建人事档案

# 人事专员
GET    /api/v1/onboard/progress       # 入职进度总览
GET    /api/v1/onboard/{employeeId}/archive # 查看档案
```

### 3.5 培训管理 API (gbm-training)

```
# 培训计划
POST   /api/v1/training/plans         # 创建培训计划 (Agent自动生成)
GET    /api/v1/training/plans         # 培训计划列表
GET    /api/v1/training/plans/{id}   # 培训计划详情

# 签到管理
POST   /api/v1/training/signin/qr     # 生成签到二维码
POST   /api/v1/training/signin/check  # 扫码签到
GET    /api/v1/training/signin/{planId}/list # 签到记录

# 考试
POST   /api/v1/training/exam/generate # Agent生成考试题
POST   /api/v1/training/exam/submit   # 提交答卷
GET    /api/v1/training/exam/results  # 考试成绩

# 视频课程
POST   /api/v1/training/video/generate # Agent生成培训视频
GET    /api/v1/training/videos        # 视频列表
POST   /api/v1/training/videos/{id}/audit # 审核视频

# 体系审核
POST   /api/v1/training/audit/pack    # Agent生成审核资料包
GET    /api/v1/training/audit/{id}/download # 下载资料包
```

### 3.6 考勤管理 API (gbm-attendance)

```
# 打卡数据
POST   /api/v1/attendance/clock-in    # 打卡上报
POST   /api/v1/attendance/clock-out   # 下班打卡
GET    /api/v1/attendance/records     # 考勤记录

# Agent 操作
POST   /api/v1/agent/attendance/sync  # 触发同步Agent
POST   /api/v1/agent/attendance/analyze # 触发分析Agent

# 审核
GET    /api/v1/attendance/anomalies   # 异常记录
POST   /api/v1/attendance/anomaly/review # 审核异常
GET    /api/v1/attendance/summary     # 考勤汇总
```

### 3.7 薪资管理 API (gbm-payroll)

```
# 薪资规则
GET    /api/v1/payroll/rules          # 薪资规则列表
PUT    /api/v1/payroll/rules/{id}     # 更新规则
GET    /api/v1/payroll/rules/{id}/history # 规则变更历史

# 薪资核算
POST   /api/v1/payroll/calculate      # 触发月度薪资核算 (Agent)
GET    /api/v1/payroll/{month}        # 获取核算结果
GET    /api/v1/payroll/{month}/anomalies # 异常数据
POST   /api/v1/payroll/{month}/audit  # 审核确认

# 工资条
GET    /api/v1/payroll/slip/{employeeId}/{month} # 获取工资条
POST   /api/v1/payroll/slip/send      # 发送工资条 (Agent)
GET    /api/v1/payroll/slip/status    # 发送状态

# 薪资数据
GET    /api/v1/payroll/export         # 导出薪资数据 (审计记录)
```

### 3.8 绩效管理 API (gbm-performance)

```
POST   /api/v1/performance/cycle/start    # 启动考核周期
GET    /api/v1/performance/my/evaluations # 我的考核
POST   /api/v1/performance/submit         # 提交自评
POST   /api/v1/performance/{id}/approve   # 上级审批
GET    /api/v1/performance/summary        # 汇总报表
```

### 3.9 外务管理 API (gbm-external)

```
# 工伤管理
POST   /api/v1/external/injury/report     # 工伤报告
POST   /api/v1/external/injury/{id}/upload # 上传材料
POST   /api/v1/external/injury/{id}/file   # RPA自动申报
GET    /api/v1/external/injury/{id}/status # 理赔进度

# 公积金
POST   /api/v1/external/fund/enroll       # 新参保 (RPA)
POST   /api/v1/external/fund/withdraw     # 封存减员 (RPA)
POST   /api/v1/external/fund/arrears      # 补缴申请 (RPA)
GET    /api/v1/external/fund/records      # 操作记录

# RPA 监控
GET    /api/v1/external/rpa/status        # RPA状态
POST   /api/v1/external/rpa/retry         # 手动重试
```

### 3.10 证明开具 API (gbm-procedure)

```
POST   /api/v1/procedure/apply            # 申请证明
GET    /api/v1/procedure/my               # 我的证明
POST   /api/v1/procedure/{id}/approve     # 审核证明
GET    /api/v1/procedure/{id}/download    # 下载证明
```

### 3.11 系统管理 API (gbm-system / gbm-audit)

```
# 用户管理
POST   /api/v1/system/users               # 创建用户
GET    /api/v1/system/users               # 用户列表
PUT    /api/v1/system/users/{id}          # 更新用户
POST   /api/v1/system/users/{id}/disable  # 禁用用户

# 角色权限
GET    /api/v1/system/roles               # 角色列表
POST   /api/v1/system/roles               # 创建角色
PUT    /api/v1/system/roles/{id}/permissions # 分配权限

# Agent 管理
GET    /api/v1/system/agents              # Agent列表及状态
PUT    /api/v1/system/agents/{id}/config  # Agent参数配置
POST   /api/v1/system/agents/{id}/trigger # 手动触发Agent

# 审计日志
GET    /api/v1/audit/logs                 # 审计日志查询
GET    /api/v1/audit/logs/export          # 审计日志导出

# 系统监控
GET    /api/v1/system/monitor/health      # 健康检查
GET    /api/v1/system/monitor/metrics     # 性能指标
GET    /api/v1/system/monitor/alerts      # 告警列表
```

## 4. 数据流设计

### 4.1 简历筛选数据流

```
[招聘平台] --> (每15分钟) --> [Kafka: resume.captured topic]
                                          |
                                          v
                                    [gbm-recruit-ai]
                                (简历抓取 + 去重)
                                          |
                                          v
                                    [Kafka: resume.ready topic]
                                          |
                                          v
                                    [gbm-recruit-ai]
                                (LLM评分 + 分类)
                                          |
                          +---------------+---------------+
                          |               |               |
                          v               v               v
                     [高潜>80分]    [候选60-80]    [淘汰<60]
                          |               |               |
                          v               v               v
                   [自动入库+通知]  [推送HR审核]  [自动归档]
                          |               |
                          v               v
                   [MySQL: resume]  [Kafka: review.pending]
                                    [ES: 简历索引]
```

### 4.2 薪资核算数据流

```
[XXL-Job: 每月25日触发]
         |
         v
   [gbm-orchestration]
   薪资核算流程启动
         |
   +-----+-----+-----+
   |     |     |     |
   v     v     v     v
[考勤Agent] [社保Agent] [公积金Agent] [绩效Agent]
   |     |     |     |
   +-----+-----+-----+
         |
         v
   [gbm-payroll-ai]
   薪资计算引擎
   (Fan-In 汇总)
         |
         v
   [异常检测] --> 异常标记
         |
         v
   [MySQL: payroll]
   [Kafka: payroll.ready]
         |
         v
   [推送HR审核] --> [人事专员审核确认]
                          |
                          v
                    [工资条Agent发送]
```

### 4.3 入职流程数据流

```
[人事专员创建入职任务] --> [生成邀请二维码/链接]
                                      |
                                      v
                              [新员工扫码进入]
                                      |
                          +------------+------------+
                          |            |            |
                          v            v            v
                   [上传身份证]  [上传学历]  [上传证件照]
                          |            |            |
                          v            v            v
                    [OCR Agent]  [OCR Agent]  [人脸Agent]
                    (Python)    (Python)    (Python)
                          |            |            |
                          v            v            v
                   [结构化数据]  [学历信息]  [人脸特征]
                          |            |            |
                          +------------+------------+
                                       |
                                       v
                              [入职引导Agent]
                              (完整性校验)
                                       |
                              [缺失? --> 提醒补传]
                              [完整? --> v]
                                       |
                                       v
                              [推送电子协议]
                                       |
                                       v
                              [员工手写签名]
                                       |
                                       v
                              [档案Agent]
                              (组装人事档案)
                                       |
                              +--------+--------+
                              |                 |
                              v                 v
                         [MySQL: employee]  [MinIO: 档案文件]
                              |                 |
                              v                 v
                         [通知人事专员]  [审计日志记录]
```

## 5. 中间件设计

### 5.1 Kafka Topic 规划

| Topic | 分区数 | 副本数 | 保留时间 | 说明 |
|-------|--------|--------|---------|------|
| resume.captured | 12 | 3 | 7d | 简历抓取事件 |
| resume.ready | 12 | 3 | 7d | 简历待评分 |
| resume.scored | 12 | 3 | 7d | 简历已评分 |
| review.pending | 6 | 3 | 30d | 待审核事件 |
| payroll.trigger | 3 | 3 | 30d | 薪资核算触发 |
| payroll.data.attendance | 6 | 3 | 30d | 考勤数据 |
| payroll.data.social | 6 | 3 | 30d | 社保数据 |
| payroll.ready | 6 | 3 | 30d | 薪资已核算 |
| onboard.progress | 6 | 3 | 30d | 入职进度 |
| training.signin | 6 | 3 | 30d | 签到事件 |
| agent.alert | 3 | 3 | 7d | Agent告警 |
| audit.event | 12 | 3 | 3650d (10年) | 审计事件 |
| system.notification | 6 | 3 | 7d | 系统通知 |

### 5.2 Redis 使用规划

| 用途 | Key 模式 | 过期时间 | 数据结构 |
|------|---------|---------|----------|
| 用户会话 | `session:{token}` | 24h | Hash |
| 验证码 | `sms:code:{phone}` | 5min | String |
| Agent分布式锁 | `lock:agent:{agent_name}` | 30s | String (SETNX) |
| 简历去重 | `dedup:resume:{hash}` | 7d | String |
| 签到计数 | `signin:count:{plan_id}` | 会话期 | String (INCR) |
| Agent执行状态 | `agent:status:{agent_id}` | 1h | Hash |
| 薪资核算缓存 | `payroll:cache:{month}` | 核算期 | Hash |
| 热数据缓存 | `cache:hot:{type}:{id}` | 10min | String |
| 限流计数 | `ratelimit:{ip}:{api}` | 1min | String (INCR) |
| 排行榜 | `rank:resume:{job_id}` | 30d | ZSet |

### 5.3 缓存策略

```
# 读取策略: Cache-Aside
if (cache.has(key)) {
    return cache.get(key);
}
data = db.query(key);
cache.set(key, data, ttl);
return data;

# 更新策略: Write-Through (核心数据)
db.update(data);
cache.invalidate(key);  // 删除缓存，下次读取重新加载

# 薪资数据: 强一致
// 不使用缓存，直接查库
// 原因: 薪资数据必须保证最终一致性

# 简历评分: 短期缓存
// TTL 30分钟，避免重复LLM调用
```

## 6. 安全策略

### 6.1 认证流程

```
[客户端] --> POST /auth/login {username, password}
         |
         v
   [gbm-auth]
   1. 验证凭据
   2. 检查账户状态
   3. 检查MFA需求
         |
   +-----+
   | MFA? |
   +-----+
   |     |
   No    Yes
   |     |
   v     v
[JWT] [发送MFA码]
   |     |
   |  [客户端输入MFA码]
   |     |
   |     v
   |  [验证MFA码]
   |     |
   +-----+
         |
         v
   {
     "accessToken": "jwt_token_2h",
     "refreshToken": "random_30d",
     "expiresIn": 7200
   }
```

### 6.2 授权策略 (RBAC + 行级隔离)

```
角色层级:
  ADMIN (系统管理员)
    └── 全部权限
  HR_MANAGER (人事主管)
    └── HR全部操作 + 审核权限 + 数据导出
  HR_SPECIALIST (人事专员)
    └── HR操作 + 审核权限
  DEPT_MANAGER (部门主管)
    └── 本部门数据查看 + 审批权限
  EMPLOYEE (普通员工)
    └── 个人数据查看 + 自助操作

行级隔离规则:
  - DEPT_MANAGER 仅可见本部门及下属部门数据
  - EMPLOYEE 仅可见个人数据
  - HR_* 角色可见全量数据
  - 通过 MyBatis 插件实现 SQL 级行过滤
```

### 6.3 数据加密策略

```java
// 敏感字段加密 (AES-256-GCM)
@EncryptField(algorithm = "AES-256-GCM")
private String idNumber;  // 身份证号

@EncryptField(algorithm = "AES-256-GCM")
private String salary;    // 薪资数据

// 密钥管理 (HashiCorp Vault)
// - 密钥每90天轮换
// - 旧密钥保留180天用于解密历史数据
// - 密钥分片存储 (3-of-5 门限)

// 传输加密
// - 全链路 TLS 1.3
// - 内部服务 mTLS (Istio)
```

### 6.4 审计日志策略

```java
// 审计注解
@AuditLog(
    module = Module.PAYROLL,
    operation = Operation.UPDATE,
    target = "#{#employeeId}",
    captureBefore = true,
    captureAfter = true
)
public void approvePayroll(String employeeId, String month) {
    // 业务逻辑
}

// AOP 切面自动记录
// - 操作时间 (精确到秒)
// - 操作人 (账号+姓名)
// - 操作IP
// - 操作类型
// - 操作模块
// - 操作对象
// - 变更前JSON快照
// - 变更后JSON快照
// - 结果 (成功/失败)
// - 耗时 (毫秒)
```

### 6.5 AI 安全护栏

```python
# Prompt 注入防护
class PromptGuard:
    def sanitize(self, user_input: str) -> str:
        # 1. 移除系统指令模式
        patterns = [
            r"ignore\s+previous\s+instructions",
            r"system\s+prompt",
            r"you\s+are\s+now",
            r"作为[系统AI助手]",
        ]
        for pattern in patterns:
            user_input = re.sub(pattern, "[FILTERED]", user_input, flags=re.IGNORECASE)
        # 2. 长度限制
        if len(user_input) > 10000:
            user_input = user_input[:10000]
        # 3. 编码检查
        user_input = sanitize_encoding(user_input)
        return user_input

# 输出校验
class OutputGuard:
    def validate_salary(self, result: dict) -> bool:
        # 薪资不得为负
        if result.get('net_pay', 0) < 0:
            return False
        # 薪资不得低于最低工资
        if result.get('net_pay', 0) < local_min_wage:
            return False
        # 评分在 [0, 100] 范围内
        if not (0 <= result.get('score', 0) <= 100):
            return False
        return True
```

---

# 数据库设计脚本 (GBM AI Agent HR - Database DDL)

## 1. ER 概述

```
+-----------+     +-----------+     +-----------+
| employee  | 1--*| attendance|     | payroll   |
+-----------+     +-----------+     +-----------+
      |                  |                  |
      | 1              *|                  |*
      |                  |                  |
+-----------+     +-----------+     +-----------+
| department|     | training  |     | performance|
+-----------+     +-----------+     +-----------+
      |                  |                  |
      |*                *|                  |*
      |                  |                  |
+-----------+     +-----------+     +-----------+
| resume    |     | injury    |     | certificate|
+-----------+     +-----------+     +-----------+
      |                  |                  |
      |*                *|                  |
      |                  |                  |
+-----------+     +-----------+     +-----------+
| fund_record|    | agent_run |     | audit_log |
+-----------+     +-----------+     +-----------+
```

### 核心实体关系

- **employee** 是核心实体，与 attendance、payroll、performance、training、injury 等多对一
- **department** 与 employee 一对多
- **resume** 独立实体，通过 applied_position 关联 job
- **agent_run_log** 记录所有Agent执行，通过 parent_flow_id 关联业务流程
- **audit_log** 独立审计表，记录所有敏感操作

## 2. 完整 SQL DDL 脚本

```sql
-- ============================================================
-- GBM AI Agent HR 数据库 DDL 脚本
-- 数据库: MySQL 8.0+
-- 字符集: utf8mb4
-- 排序规则: utf8mb4_unicode_ci
-- 作者: 后旺 (HouWang)
-- 日期: 2026-06-12
-- ============================================================

CREATE DATABASE IF NOT EXISTS gbm_hr
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE gbm_hr;

-- ============================================================
-- 1. 组织架构
-- ============================================================

-- 部门表
CREATE TABLE department (
    dept_id         VARCHAR(20)  NOT NULL COMMENT '部门ID',
    dept_name       VARCHAR(100) NOT NULL COMMENT '部门名称',
    parent_id       VARCHAR(20)  DEFAULT NULL COMMENT '上级部门ID',
    dept_level      INT          NOT NULL DEFAULT 1 COMMENT '层级 (1=总部)',
    manager_id      VARCHAR(20)  DEFAULT NULL COMMENT '部门负责人工号',
    sort_order      INT          NOT NULL DEFAULT 0 COMMENT '排序',
    status          TINYINT      NOT NULL DEFAULT 1 COMMENT '状态: 1=启用 0=禁用',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (dept_id),
    INDEX idx_parent_id (parent_id),
    INDEX idx_manager_id (manager_id),
    CONSTRAINT fk_dept_parent FOREIGN KEY (parent_id) REFERENCES department(dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';

-- 岗位表
CREATE TABLE position (
    position_id     VARCHAR(20)  NOT NULL COMMENT '岗位ID',
    position_name   VARCHAR(100) NOT NULL COMMENT '岗位名称',
    dept_id         VARCHAR(20)  NOT NULL COMMENT '所属部门',
    grade           VARCHAR(20)  NOT NULL COMMENT '职级',
    headcount       INT          NOT NULL DEFAULT 1 COMMENT '编制人数',
    description     TEXT         DEFAULT NULL COMMENT '岗位描述',
    qualification   JSON         DEFAULT NULL COMMENT '任职资格模型',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (position_id),
    INDEX idx_dept_id (dept_id),
    CONSTRAINT fk_pos_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位表';

-- ============================================================
-- 2. 员工档案
-- ============================================================

CREATE TABLE employee (
    employee_id     VARCHAR(20)  NOT NULL COMMENT '工号',
    name            VARCHAR(50)  NOT NULL COMMENT '姓名',
    id_number       VARCHAR(32)  NOT NULL COMMENT '身份证号(AES加密后存储)',
    id_number_plain_hash CHAR(64) NOT NULL COMMENT '身份证号SHA256哈希(用于去重查询)',
    gender          CHAR(1)      NOT NULL COMMENT '性别: M/F',
    birth_date      DATE         NOT NULL COMMENT '出生日期',
    phone           VARCHAR(20)  NOT NULL COMMENT '手机号码',
    email           VARCHAR(100) DEFAULT NULL COMMENT '电子邮箱',
    dept_id         VARCHAR(20)  NOT NULL COMMENT '所属部门',
    position_id     VARCHAR(20)  NOT NULL COMMENT '现任岗位',
    hire_date       DATE         NOT NULL COMMENT '入职日期',
    leave_date      DATE         DEFAULT NULL COMMENT '离职日期(NULL=在职)',
    status          VARCHAR(20)  NOT NULL DEFAULT '在职' COMMENT '在职/试用期/停薪留职/离职',
    face_feature_uri VARCHAR(500) DEFAULT NULL COMMENT '人脸特征文件URI',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id),
    UNIQUE KEY uk_id_number_hash (id_number_plain_hash),
    INDEX idx_dept_id (dept_id),
    INDEX idx_status (status),
    INDEX idx_hire_date (hire_date),
    INDEX idx_phone (phone),
    CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id),
    CONSTRAINT fk_emp_pos FOREIGN KEY (position_id) REFERENCES position(position_id),
    CONSTRAINT chk_gender CHECK (gender IN ('M', 'F')),
    CONSTRAINT chk_status CHECK (status IN ('在职', '试用期', '停薪留职', '离职'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工档案表';

-- 员工证件档案
CREATE TABLE employee_document (
    doc_id          VARCHAR(20)  NOT NULL COMMENT '证件ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    doc_type        VARCHAR(50)  NOT NULL COMMENT '证件类型: 身份证/学历证/资格证等',
    doc_number      VARCHAR(100) DEFAULT NULL COMMENT '证件编号',
    issue_date      DATE         DEFAULT NULL COMMENT '发证日期',
    expiry_date     DATE         DEFAULT NULL COMMENT '到期日期',
    file_uri        VARCHAR(500) NOT NULL COMMENT '文件存储路径(MinIO)',
    ocr_data        JSON         DEFAULT NULL COMMENT 'OCR提取的结构化数据',
    status          VARCHAR(20)  NOT NULL DEFAULT '有效' COMMENT '有效/过期/待审核',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (doc_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_doc_type (doc_type),
    INDEX idx_expiry_date (expiry_date),
    CONSTRAINT fk_doc_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工证件档案';

-- 电子签名/协议存证
CREATE TABLE e_signature (
    sig_id          VARCHAR(20)  NOT NULL COMMENT '签名ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    doc_type        VARCHAR(50)  NOT NULL COMMENT '文档类型',
    doc_content_uri VARCHAR(500) NOT NULL COMMENT '文档内容URI',
    signature_uri   VARCHAR(500) NOT NULL COMMENT '手写签名URI',
    signed_at       DATETIME     NOT NULL COMMENT '签署时间',
    watermark_hash  CHAR(64)     NOT NULL COMMENT '安全水印哈希',
    file_uri        VARCHAR(500) NOT NULL COMMENT '最终签署文件URI',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sig_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_signed_at (signed_at),
    CONSTRAINT fk_sig_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='电子签名存证表';

-- ============================================================
-- 3. 招聘管理
-- ============================================================

-- 岗位需求表
CREATE TABLE job_post (
    job_id          VARCHAR(20)  NOT NULL COMMENT '岗位需求ID',
    job_name        VARCHAR(100) NOT NULL COMMENT '岗位名称',
    dept_id         VARCHAR(20)  NOT NULL COMMENT '需求部门',
    grade           VARCHAR(20)  NOT NULL COMMENT '职级',
    headcount       INT          NOT NULL DEFAULT 1 COMMENT '需求人数',
    deadline        DATE         NOT NULL COMMENT '到岗时限',
    requirements    TEXT         NOT NULL COMMENT '核心要求(主管提供)',
    jd_content      TEXT         DEFAULT NULL COMMENT 'Agent生成的职位描述',
    pass_score      DECIMAL(5,2) NOT NULL DEFAULT 60.00 COMMENT '合格分数线',
    status          VARCHAR(20)  NOT NULL DEFAULT '已发布' COMMENT '草稿/已发布/已关闭',
    created_by      VARCHAR(20)  NOT NULL COMMENT '创建人工号',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (job_id),
    INDEX idx_dept_id (dept_id),
    INDEX idx_status (status),
    INDEX idx_deadline (deadline),
    CONSTRAINT fk_job_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位需求表';

-- 简历表
CREATE TABLE resume (
    resume_id       VARCHAR(20)  NOT NULL COMMENT '简历ID',
    candidate_name  VARCHAR(50)  NOT NULL COMMENT '姓名',
    id_number_hash  CHAR(64)     DEFAULT NULL COMMENT '身份证号SHA256哈希(去重用)',
    phone           VARCHAR(20)  DEFAULT NULL COMMENT '手机号(去重用)',
    source_platform VARCHAR(50)  NOT NULL COMMENT '来源平台',
    education       VARCHAR(50)  DEFAULT NULL COMMENT '最高学历',
    years_of_exp    INT          DEFAULT NULL COMMENT '从业年限',
    skill_tags      TEXT         DEFAULT NULL COMMENT '技能标签(逗号分隔)',
    age             INT          DEFAULT NULL COMMENT '年龄',
    certs           TEXT         DEFAULT NULL COMMENT '持证情况',
    applied_job_id  VARCHAR(20)  NOT NULL COMMENT '应聘岗位ID',
    total_score     DECIMAL(5,2) DEFAULT NULL COMMENT '综合匹配分(0-100)',
    score_detail    JSON         DEFAULT NULL COMMENT '分项得分明细',
    reasoning_summary TEXT       DEFAULT NULL COMMENT '评分推理摘要',
    model_version   VARCHAR(50)  DEFAULT NULL COMMENT '评分模型版本',
    classify_result VARCHAR(20)  DEFAULT NULL COMMENT '高潜/候选/淘汰',
    file_uri        VARCHAR(500) DEFAULT NULL COMMENT '简历文件URI',
    duplicate_flag  TINYINT      NOT NULL DEFAULT 0 COMMENT '是否重复: 0=否 1=是',
    format_anomaly  TINYINT      NOT NULL DEFAULT 0 COMMENT '格式异常: 0=正常 1=异常',
    status          VARCHAR(20)  NOT NULL DEFAULT '新投递' COMMENT '新投递/已入库/已面试/已淘汰',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (resume_id),
    INDEX idx_applied_job (applied_job_id),
    INDEX idx_classify (classify_result),
    INDEX idx_total_score (total_score),
    INDEX idx_created_at (created_at),
    INDEX idx_candidate_name (candidate_name),
    CONSTRAINT fk_resume_job FOREIGN KEY (applied_job_id) REFERENCES job_post(job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';

-- 简历评分维度表 (存储每次评分的详细数据)
CREATE TABLE resume_score_detail (
    score_id        VARCHAR(20)  NOT NULL COMMENT '评分ID',
    resume_id       VARCHAR(20)  NOT NULL COMMENT '简历ID',
    education_score DECIMAL(5,2) NOT NULL COMMENT '学历匹配得分',
    exp_score       DECIMAL(5,2) NOT NULL COMMENT '经验匹配得分',
    skill_score     DECIMAL(5,2) NOT NULL COMMENT '技能匹配得分',
    age_score       DECIMAL(5,2) NOT NULL COMMENT '年龄匹配得分',
    cert_score      DECIMAL(5,2) NOT NULL COMMENT '证书匹配得分',
    semantic_score  DECIMAL(5,2) NOT NULL COMMENT '语义综合得分',
    semantic_scores JSON         DEFAULT NULL COMMENT '三次重复评分结果 [s1,s2,s3]',
    total_score     DECIMAL(5,2) NOT NULL COMMENT '加权总分',
    model_version   VARCHAR(50)  NOT NULL COMMENT '模型版本',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (score_id),
    INDEX idx_resume_id (resume_id),
    CONSTRAINT fk_score_resume FOREIGN KEY (resume_id) REFERENCES resume(resume_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历评分明细表';

-- 人才库表 (从简历库精选入库)
CREATE TABLE talent_pool (
    talent_id       VARCHAR(20)  NOT NULL COMMENT '人才ID',
    resume_id       VARCHAR(20)  NOT NULL COMMENT '来源简历ID',
    candidate_name  VARCHAR(50)  NOT NULL COMMENT '姓名',
    industry_tags   JSON         DEFAULT NULL COMMENT '行业背景标签',
    tech_stack      JSON         DEFAULT NULL COMMENT '技术栈标签',
    mgmt_experience JSON         DEFAULT NULL COMMENT '管理经验标签',
    project_experience JSON      DEFAULT NULL COMMENT '项目经验标签',
    last_contact    DATE         DEFAULT NULL COMMENT '最后联系日期',
    health_status   VARCHAR(20)  NOT NULL DEFAULT '活跃' COMMENT '活跃/需刷新/冷备',
    archived_at     DATETIME     DEFAULT NULL COMMENT '转入冷备时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (talent_id),
    INDEX idx_health_status (health_status),
    CONSTRAINT fk_talent_resume FOREIGN KEY (resume_id) REFERENCES resume(resume_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人才库表';

-- 试卷表
CREATE TABLE exam_paper (
    paper_id        VARCHAR(20)  NOT NULL COMMENT '试卷ID',
    job_id          VARCHAR(20)  DEFAULT NULL COMMENT '关联岗位ID(NULL=培训考试)',
    training_plan_id VARCHAR(20) DEFAULT NULL COMMENT '关联培训计划ID',
    paper_type      VARCHAR(20)  NOT NULL COMMENT '面试/培训',
    subject         VARCHAR(100) NOT NULL COMMENT '考试科目',
    total_questions INT          NOT NULL COMMENT '总题数',
    total_score     DECIMAL(5,2) NOT NULL COMMENT '总分',
    paper_content   JSON         NOT NULL COMMENT '试卷内容(JSON存储题目)',
    qr_code         VARCHAR(100) NOT NULL COMMENT '考试二维码',
    status          VARCHAR(20)  NOT NULL DEFAULT '待审核' COMMENT '待审核/已发布/已过期',
    created_by      VARCHAR(20)  DEFAULT NULL COMMENT '创建人(工号或Agent)',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (paper_id),
    INDEX idx_job_id (job_id),
    INDEX idx_qr_code (qr_code),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷表';

-- 考试答卷表
CREATE TABLE exam_submission (
    submission_id   VARCHAR(20)  NOT NULL COMMENT '答卷ID',
    paper_id        VARCHAR(20)  NOT NULL COMMENT '试卷ID',
    candidate_name  VARCHAR(50)  NOT NULL COMMENT '考生姓名',
    resume_id       VARCHAR(20)  DEFAULT NULL COMMENT '关联简历ID',
    employee_id     VARCHAR(20)  DEFAULT NULL COMMENT '关联员工ID',
    answers         JSON         NOT NULL COMMENT '全部作答记录',
    objective_score DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '客观题得分',
    subjective_score DECIMAL(5,2) DEFAULT NULL COMMENT '主观题得分',
    total_score     DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '总分',
    ai_score_detail JSON         DEFAULT NULL COMMENT 'AI交叉评分详情',
    needs_review    TINYINT      NOT NULL DEFAULT 0 COMMENT '是否需要人工复核',
    submitted_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    graded_at       DATETIME     DEFAULT NULL COMMENT '阅卷完成时间',
    PRIMARY KEY (submission_id),
    INDEX idx_paper_id (paper_id),
    INDEX idx_candidate (candidate_name),
    CONSTRAINT fk_sub_paper FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试答卷表';

-- ============================================================
-- 4. 入职管理
-- ============================================================

-- 入职任务表
CREATE TABLE onboarding_task (
    task_id         VARCHAR(20)  NOT NULL COMMENT '入职任务ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    invite_token    VARCHAR(64)  NOT NULL COMMENT '邀请令牌(扫码用)',
    current_step    INT          NOT NULL DEFAULT 0 COMMENT '当前步骤',
    total_steps     INT          NOT NULL DEFAULT 8 COMMENT '总步骤数',
    status          VARCHAR(20)  NOT NULL DEFAULT '进行中' COMMENT '进行中/已完成/已取消',
    completed_at    DATETIME     DEFAULT NULL COMMENT '完成时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id),
    UNIQUE KEY uk_invite_token (invite_token),
    INDEX idx_employee_id (employee_id),
    CONSTRAINT fk_onboard_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='入职任务表';

-- 入职材料清单
CREATE TABLE onboarding_checklist (
    checklist_id    VARCHAR(20)  NOT NULL COMMENT '清单ID',
    task_id         VARCHAR(20)  NOT NULL COMMENT '入职任务ID',
    item_name       VARCHAR(100) NOT NULL COMMENT '材料名称',
    is_required     TINYINT      NOT NULL DEFAULT 1 COMMENT '是否必填',
    status          VARCHAR(20)  NOT NULL DEFAULT '待上传' COMMENT '待上传/已上传/已识别/缺失',
    file_uri        VARCHAR(500) DEFAULT NULL COMMENT '上传文件URI',
    ocr_status      VARCHAR(20)  DEFAULT NULL COMMENT 'OCR状态: 待识别/成功/失败',
    ocr_data        JSON         DEFAULT NULL COMMENT 'OCR识别结果',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (checklist_id),
    INDEX idx_task_id (task_id),
    CONSTRAINT fk_checklist_task FOREIGN KEY (task_id) REFERENCES onboarding_task(task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='入职材料清单';

-- 人脸档案表
CREATE TABLE face_archive (
    face_id         VARCHAR(20)  NOT NULL COMMENT '人脸ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    photo_uri       VARCHAR(500) NOT NULL COMMENT '人脸照片URI',
    feature_vector_uri VARCHAR(500) NOT NULL COMMENT '特征向量文件URI',
    photo_quality   DECIMAL(5,2) NOT NULL COMMENT '照片质量评分(0-100)',
    id_match_score  DECIMAL(5,2) NOT NULL COMMENT '与身份证照片比对得分',
    match_result    VARCHAR(20)  NOT NULL COMMENT '一致/不一致/存疑',
    access_card_id  VARCHAR(50)  DEFAULT NULL COMMENT '关联门禁卡号',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (face_id),
    UNIQUE KEY uk_employee_id (employee_id),
    CONSTRAINT fk_face_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人脸档案表';

-- ============================================================
-- 5. 试用期管理
-- ============================================================

-- 试用期评估表
CREATE TABLE probation_evaluation (
    eval_id         VARCHAR(20)  NOT NULL COMMENT '评估ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    start_date      DATE         NOT NULL COMMENT '试用期开始日期',
    end_date        DATE         NOT NULL COMMENT '试用期结束日期',
    training_score  DECIMAL(5,2) DEFAULT NULL COMMENT '培训成绩',
    performance_score DECIMAL(5,2) DEFAULT NULL COMMENT '绩效评分',
    attendance_summary JSON      DEFAULT NULL COMMENT '考勤汇总',
    reflection_uri  VARCHAR(500) DEFAULT NULL COMMENT '心得体会URI',
    eval_report_uri VARCHAR(500) DEFAULT NULL COMMENT '评估报告PDF URI',
    result          VARCHAR(20)  DEFAULT NULL COMMENT '通过/不通过/延长',
    manager_review  TEXT         DEFAULT NULL COMMENT '主管评语',
    hr_review       TEXT         DEFAULT NULL COMMENT '人事评语',
    status          VARCHAR(20)  NOT NULL DEFAULT '评估中' COMMENT '评估中/待审批/已完成',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (eval_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_end_date (end_date),
    CONSTRAINT fk_probation_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试用期评估表';

-- ============================================================
-- 6. 培训管理
-- ============================================================

-- 培训计划表
CREATE TABLE training_plan (
    plan_id         VARCHAR(20)  NOT NULL COMMENT '培训计划ID',
    plan_name       VARCHAR(200) NOT NULL COMMENT '计划名称',
    plan_type       VARCHAR(20)  NOT NULL COMMENT '入职培训/在岗培训/专项培训',
    start_date      DATETIME     NOT NULL COMMENT '开始时间',
    end_date        DATETIME     NOT NULL COMMENT '结束时间',
    location        VARCHAR(200) DEFAULT NULL COMMENT '培训地点',
    max_attendees   INT          NOT NULL DEFAULT 50 COMMENT '最大人数',
    qr_code         VARCHAR(100) DEFAULT NULL COMMENT '签到二维码',
    trainer         VARCHAR(50)  DEFAULT NULL COMMENT '培训讲师',
    status          VARCHAR(20)  NOT NULL DEFAULT '计划中' COMMENT '计划中/进行中/已完成/已取消',
    created_by      VARCHAR(20)  DEFAULT NULL COMMENT '创建人(工号或Agent)',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (plan_id),
    INDEX idx_plan_type (plan_type),
    INDEX idx_status (status),
    INDEX idx_start_date (start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训计划表';

-- 培训签到记录
CREATE TABLE training_signin (
    signin_id       VARCHAR(20)  NOT NULL COMMENT '签到ID',
    plan_id         VARCHAR(20)  NOT NULL COMMENT '培训计划ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    signin_time     DATETIME     NOT NULL COMMENT '签到时间',
    signin_method   VARCHAR(20)  NOT NULL COMMENT '扫码/人脸识别',
    status          VARCHAR(20)  NOT NULL DEFAULT '正常' COMMENT '正常/迟到/未到',
    late_minutes    INT          DEFAULT 0 COMMENT '迟到分钟数',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (signin_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_employee_id (employee_id),
    CONSTRAINT fk_signin_plan FOREIGN KEY (plan_id) REFERENCES training_plan(plan_id),
    CONSTRAINT fk_signin_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训签到记录';

-- 培训成绩表
CREATE TABLE training_result (
    result_id       VARCHAR(20)  NOT NULL COMMENT '成绩ID',
    plan_id         VARCHAR(20)  NOT NULL COMMENT '培训计划ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    score           DECIMAL(5,2) NOT NULL COMMENT '考试成绩',
    pass_threshold  DECIMAL(5,2) NOT NULL DEFAULT 60.00 COMMENT '及格线',
    passed          TINYINT      NOT NULL COMMENT '是否及格: 1=是 0=否',
    certificate_uri VARCHAR(500) DEFAULT NULL COMMENT '结业证书URI',
    retake_flag     TINYINT      NOT NULL DEFAULT 0 COMMENT '是否补考',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (result_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_employee_id (employee_id),
    CONSTRAINT fk_result_plan FOREIGN KEY (plan_id) REFERENCES training_plan(plan_id),
    CONSTRAINT fk_result_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训成绩表';

-- 培训视频表
CREATE TABLE training_video (
    video_id        VARCHAR(20)  NOT NULL COMMENT '视频ID',
    source_doc_uri  VARCHAR(500) NOT NULL COMMENT '源教材文档URI',
    video_uri       VARCHAR(500) NOT NULL COMMENT '视频文件URI',
    duration_seconds INT         NOT NULL COMMENT '视频时长(秒)',
    knowledge_tags  JSON         DEFAULT NULL COMMENT '知识点标签',
    applicable_positions JSON    DEFAULT NULL COMMENT '适用岗位',
    status          VARCHAR(20)  NOT NULL DEFAULT '待审核' COMMENT '待审核/已发布/已下架',
    created_by      VARCHAR(20)  DEFAULT NULL COMMENT '创建人',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (video_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训视频表';

-- ============================================================
-- 7. 考勤管理
-- ============================================================

-- 班次表
CREATE TABLE shift (
    shift_id        VARCHAR(20)  NOT NULL COMMENT '班次ID',
    shift_name      VARCHAR(50)  NOT NULL COMMENT '班次名称',
    start_time      TIME         NOT NULL COMMENT '上班时间',
    end_time        TIME         NOT NULL COMMENT '下班时间',
    break_minutes   INT          NOT NULL DEFAULT 60 COMMENT '休息分钟数',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (shift_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班次表';

-- 排班表
CREATE TABLE shift_schedule (
    schedule_id     VARCHAR(20)  NOT NULL COMMENT '排班ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    work_date       DATE         NOT NULL COMMENT '工作日期',
    shift_id        VARCHAR(20)  NOT NULL COMMENT '班次ID',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (schedule_id),
    UNIQUE KEY uk_emp_date (employee_id, work_date),
    INDEX idx_work_date (work_date),
    CONSTRAINT fk_schedule_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT fk_schedule_shift FOREIGN KEY (shift_id) REFERENCES shift(shift_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='排班表';

-- 考勤记录表
CREATE TABLE attendance_record (
    record_id       VARCHAR(20)  NOT NULL COMMENT '记录ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    date            DATE         NOT NULL COMMENT '日期',
    clock_in        TIME         DEFAULT NULL COMMENT '上班打卡时间',
    clock_out       TIME         DEFAULT NULL COMMENT '下班打卡时间',
    shift_id        VARCHAR(20)  DEFAULT NULL COMMENT '班次ID',
    late_count      INT          NOT NULL DEFAULT 0 COMMENT '迟到次数',
    early_leave_count INT        NOT NULL DEFAULT 0 COMMENT '早退次数',
    absent_days     INT          NOT NULL DEFAULT 0 COMMENT '旷工天数',
    holiday_leave_hrs DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '事假小时数',
    sick_leave_hrs  DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '病假小时数',
    overtime_hrs    DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '加班时长',
    flag            VARCHAR(20)  DEFAULT NULL COMMENT '异常标志: 迟到/早退/缺卡/旷工/加班超限',
    remark          TEXT         DEFAULT NULL COMMENT '备注说明',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    INDEX idx_employee_date (employee_id, date),
    INDEX idx_date (date),
    INDEX idx_flag (flag),
    CONSTRAINT fk_attend_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT fk_attend_shift FOREIGN KEY (shift_id) REFERENCES shift(shift_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考勤记录表';

-- 请假/加班/出差申请表
CREATE TABLE leave_application (
    apply_id        VARCHAR(20)  NOT NULL COMMENT '申请ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    apply_type      VARCHAR(20)  NOT NULL COMMENT '事假/病假/年假/加班/出差',
    start_time      DATETIME     NOT NULL COMMENT '开始时间',
    end_time        DATETIME     NOT NULL COMMENT '结束时间',
    hours           DECIMAL(5,2) NOT NULL COMMENT '时长(小时)',
    reason          TEXT         DEFAULT NULL COMMENT '申请事由',
    attachment_uri  VARCHAR(500) DEFAULT NULL COMMENT '附件URI(如病假证明)',
    status          VARCHAR(20)  NOT NULL DEFAULT '待审批' COMMENT '待审批/已通过/已拒绝',
    approved_by     VARCHAR(20)  DEFAULT NULL COMMENT '审批人工号',
    approved_at     DATETIME     DEFAULT NULL COMMENT '审批时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (apply_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_apply_type (apply_type),
    INDEX idx_status (status),
    CONSTRAINT fk_leave_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT chk_apply_type CHECK (apply_type IN ('事假', '病假', '年假', '加班', '出差'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='请假/加班/出差申请表';

-- ============================================================
-- 8. 薪资管理
-- ============================================================

-- 员工薪资主数据
CREATE TABLE employee_salary (
    salary_id       VARCHAR(20)  NOT NULL COMMENT '薪资ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    base_pay        DECIMAL(10,2) NOT NULL COMMENT '基本工资',
    position_allowance DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '岗位津贴',
    subsidies       JSON         DEFAULT NULL COMMENT '各类补贴明细',
    bonus_base      DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '绩效奖金基数',
    effective_date  DATE         NOT NULL COMMENT '生效日期',
    version         INT          NOT NULL DEFAULT 1 COMMENT '版本号',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (salary_id),
    UNIQUE KEY uk_employee (employee_id),
    CONSTRAINT fk_salary_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工薪资主数据';

-- 薪资规则表
CREATE TABLE salary_rule (
    rule_id         VARCHAR(20)  NOT NULL COMMENT '规则ID',
    rule_type       VARCHAR(50)  NOT NULL COMMENT '规则类型: 加班系数/迟到扣款/补贴定额/社保比例',
    rule_name       VARCHAR(100) NOT NULL COMMENT '规则名称',
    rule_config     JSON         NOT NULL COMMENT '规则配置(JSON)',
    effective_date  DATE         NOT NULL COMMENT '生效日期',
    expiry_date     DATE         DEFAULT NULL COMMENT '失效日期',
    version         INT          NOT NULL DEFAULT 1 COMMENT '版本号',
    status          VARCHAR(20)  NOT NULL DEFAULT '生效中' COMMENT '生效中/已失效',
    created_by      VARCHAR(20)  NOT NULL COMMENT '创建人',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (rule_id),
    INDEX idx_rule_type (rule_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资规则表';

-- 月度薪资核算表
CREATE TABLE payroll (
    payroll_id      VARCHAR(20)  NOT NULL COMMENT '薪资记录ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    month           VARCHAR(7)   NOT NULL COMMENT '月份 YYYY-MM',
    base_pay        DECIMAL(10,2) NOT NULL COMMENT '基本工资',
    overtime_pay    DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '加班费',
    overtime_detail JSON         DEFAULT NULL COMMENT '加班费计算明细',
    attendance_deduct DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '考勤扣款',
    allowances_total DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '补贴合计',
    deduction_total DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '扣款合计',
    ss_personal     DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '社保个人缴纳',
    gf_personal     DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '公积金个人缴纳',
    taxable_income  DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '应税收入',
    income_tax      DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '个税',
    special_deduction DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '专项附加扣除',
    net_pay         DECIMAL(10,2) NOT NULL COMMENT '实发工资',
    anomaly_flags   JSON         DEFAULT NULL COMMENT '异常标记列表',
    calc_trace      JSON         DEFAULT NULL COMMENT '计算底稿(完整溯源)',
    status          VARCHAR(20)  NOT NULL DEFAULT '已核算' COMMENT '已核算/已审核/已发放',
    reviewed_by     VARCHAR(20)  DEFAULT NULL COMMENT '审核人工号',
    reviewed_at     DATETIME     DEFAULT NULL COMMENT '审核时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (payroll_id),
    UNIQUE KEY uk_emp_month (employee_id, month),
    INDEX idx_month (month),
    INDEX idx_status (status),
    CONSTRAINT fk_payroll_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT chk_payroll_status CHECK (status IN ('已核算', '已审核', '已发放'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='月度薪资核算表';

-- 工资条发送记录
CREATE TABLE payroll_slip (
    slip_id         VARCHAR(20)  NOT NULL COMMENT '工资条ID',
    payroll_id      VARCHAR(20)  NOT NULL COMMENT '薪资记录ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    send_channel    VARCHAR(20)  NOT NULL COMMENT '短信/邮件/APP推送',
    send_status     VARCHAR(20)  NOT NULL DEFAULT '待发送' COMMENT '待发送/已发送/已阅读/发送失败',
    sent_at         DATETIME     DEFAULT NULL COMMENT '发送时间',
    read_at         DATETIME     DEFAULT NULL COMMENT '阅读时间',
    retry_count     INT          NOT NULL DEFAULT 0 COMMENT '重试次数',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (slip_id),
    INDEX idx_payroll_id (payroll_id),
    INDEX idx_send_status (send_status),
    CONSTRAINT fk_slip_payroll FOREIGN KEY (payroll_id) REFERENCES payroll(payroll_id),
    CONSTRAINT fk_slip_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工资条发送记录';

-- ============================================================
-- 9. 绩效管理
-- ============================================================

-- 绩效考核周期表
CREATE TABLE performance_cycle (
    cycle_id        VARCHAR(20)  NOT NULL COMMENT '考核周期ID',
    cycle_name      VARCHAR(100) NOT NULL COMMENT '周期名称',
    start_date      DATE         NOT NULL COMMENT '开始日期',
    end_date        DATE         NOT NULL COMMENT '结束日期',
    scope           VARCHAR(50)  NOT NULL DEFAULT '全员' COMMENT '全员/管理人员',
    status          VARCHAR(20)  NOT NULL DEFAULT '未开始' COMMENT '未开始/进行中/已完成',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cycle_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='绩效考核周期表';

-- 绩效考核记录表
CREATE TABLE performance_review (
    pr_id           VARCHAR(20)  NOT NULL COMMENT '考核记录ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    cycle_id        VARCHAR(20)  NOT NULL COMMENT '考核周期ID',
    self_score      DECIMAL(5,2) DEFAULT NULL COMMENT '自评分',
    self_comment    TEXT         DEFAULT NULL COMMENT '自评说明',
    mgr_score       DECIMAL(5,2) DEFAULT NULL COMMENT '上级评分',
    mgr_comment     TEXT         DEFAULT NULL COMMENT '上级评语',
    peer_scores     JSON         DEFAULT NULL COMMENT '互评分数(管理人员)',
    rating          VARCHAR(2)   DEFAULT NULL COMMENT '等级: A/B/C/D',
    status          VARCHAR(20)  NOT NULL DEFAULT '待自评' COMMENT '待自评/待审批/已完成',
    submit_at       DATETIME     DEFAULT NULL COMMENT '提交时间',
    approve_at      DATETIME     DEFAULT NULL COMMENT '审批时间',
    approved_by     VARCHAR(20)  DEFAULT NULL COMMENT '审批人工号',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (pr_id),
    INDEX idx_employee_cycle (employee_id, cycle_id),
    INDEX idx_cycle_id (cycle_id),
    INDEX idx_rating (rating),
    CONSTRAINT fk_perf_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT fk_perf_cycle FOREIGN KEY (cycle_id) REFERENCES performance_cycle(cycle_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='绩效考核记录表';

-- ============================================================
-- 10. 外务管理
-- ============================================================

-- 工伤档案表
CREATE TABLE injury_case (
    case_id         VARCHAR(20)  NOT NULL COMMENT '案件编号',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '受伤员工',
    accident_date   DATE         NOT NULL COMMENT '事故发生日期',
    description     TEXT         NOT NULL COMMENT '事故描述(>=50字)',
    docs            JSON         DEFAULT NULL COMMENT '上传材料清单和路径',
    filing_no       VARCHAR(50)  DEFAULT NULL COMMENT '备案受理号',
    claim_amount    DECIMAL(10,2) DEFAULT NULL COMMENT '理赔金额',
    status          VARCHAR(20)  NOT NULL DEFAULT '立案中' COMMENT '立案中/申报中/理赔中/理赔完成/被驳回',
    rpa_receipts    JSON         DEFAULT NULL COMMENT 'RPA操作截图凭证',
    progress_log    JSON         DEFAULT NULL COMMENT '理赔进度跟踪记录',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_status (status),
    CONSTRAINT fk_injury_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT chk_injury_desc CHECK (CHAR_LENGTH(description) >= 50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工伤档案表';

-- 公积金记录表
CREATE TABLE fund_record (
    record_id       VARCHAR(20)  NOT NULL COMMENT '记录ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    operation_type  VARCHAR(20)  NOT NULL COMMENT '开户/封存/补缴',
    base_amount     DECIMAL(10,2) DEFAULT NULL COMMENT '缴费基数',
    contribution_rate DECIMAL(5,2) DEFAULT NULL COMMENT '缴存比例(%)',
    amount          DECIMAL(10,2) DEFAULT NULL COMMENT '操作金额',
    rpa_receipt_uri VARCHAR(500) DEFAULT NULL COMMENT 'RPA操作回执截图',
    paper_receipt_uri VARCHAR(500) DEFAULT NULL COMMENT '纸质回执扫描',
    ocr_data        JSON         DEFAULT NULL COMMENT '纸质回执OCR提取',
    status          VARCHAR(20)  NOT NULL DEFAULT '处理中' COMMENT '处理中/已完成/异常',
    anomaly_reason  VARCHAR(200) DEFAULT NULL COMMENT '异常原因',
    retry_count     INT          NOT NULL DEFAULT 0 COMMENT '重试次数',
    operated_at     DATETIME     DEFAULT NULL COMMENT '操作完成时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_operation_type (operation_type),
    INDEX idx_status (status),
    CONSTRAINT fk_fund_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT chk_fund_op CHECK (operation_type IN ('开户', '封存', '补缴'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公积金记录表';

-- ============================================================
-- 11. 离职管理
-- ============================================================

-- 离职申请表
CREATE TABLE resignation (
    resignation_id  VARCHAR(20)  NOT NULL COMMENT '离职ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    reason          TEXT         DEFAULT NULL COMMENT '离职原因',
    reason_analysis JSON         DEFAULT NULL COMMENT 'Agent离职原因分析',
    application_uri VARCHAR(500) DEFAULT NULL COMMENT '手写申请书URI',
    last_work_date  DATE         NOT NULL COMMENT '最后工作日',
    status          VARCHAR(20)  NOT NULL DEFAULT '申请中' COMMENT '申请中/审批中/交接中/已完成',
    handover_list   JSON         DEFAULT NULL COMMENT '交接清单',
    handover_status JSON         DEFAULT NULL COMMENT '各部门交接确认状态',
    certificate_uri VARCHAR(500) DEFAULT NULL COMMENT '离职证明URI',
    archived_at     DATETIME     DEFAULT NULL COMMENT '归档时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (resignation_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_status (status),
    CONSTRAINT fk_resign_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='离职申请表';

-- ============================================================
-- 12. 人事证明
-- ============================================================

-- 证明申请表
CREATE TABLE certificate_application (
    cert_id         VARCHAR(20)  NOT NULL COMMENT '证明ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '申请人工号',
    cert_type       VARCHAR(50)  NOT NULL COMMENT '证明类型: 在职/收入/离职',
    cert_data       JSON         DEFAULT NULL COMMENT '证明所需数据',
    cert_file_uri   VARCHAR(500) DEFAULT NULL COMMENT '生成证明文件URI',
    status          VARCHAR(20)  NOT NULL DEFAULT '待审核' COMMENT '待审核/已审核/已签发/已拒绝',
    reviewed_by     VARCHAR(20)  DEFAULT NULL COMMENT '审核人工号',
    reviewed_at     DATETIME     DEFAULT NULL COMMENT '审核时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (cert_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_cert_type (cert_type),
    INDEX idx_status (status),
    CONSTRAINT fk_cert_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    CONSTRAINT chk_cert_type CHECK (cert_type IN ('在职证明', '收入证明', '离职证明'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证明申请表';

-- ============================================================
-- 13. 预算与费用
-- ============================================================

-- 费用报销表
CREATE TABLE expense_claim (
    claim_id        VARCHAR(20)  NOT NULL COMMENT '报销ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '申请人工号',
    claim_date      DATE         NOT NULL COMMENT '申请日期',
    receipt_count   INT          NOT NULL DEFAULT 0 COMMENT '票据数量',
    receipt_data    JSON         DEFAULT NULL COMMENT '票据OCR识别结果',
    total_amount    DECIMAL(10,2) NOT NULL COMMENT '报销总金额',
    category_breakdown JSON      DEFAULT NULL COMMENT '费用分类汇总',
    verification_result JSON     DEFAULT NULL COMMENT '发票真伪查验结果',
    status          VARCHAR(20)  NOT NULL DEFAULT '待审核' COMMENT '待审核/已通过/已拒绝/已付款',
    approved_by     VARCHAR(20)  DEFAULT NULL COMMENT '审批人工号',
    approved_at     DATETIME     DEFAULT NULL COMMENT '审批时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (claim_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_status (status),
    CONSTRAINT fk_expense_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='费用报销表';

-- ============================================================
-- 14. 系统管理
-- ============================================================

-- 系统用户表
CREATE TABLE system_user (
    user_id         VARCHAR(20)  NOT NULL COMMENT '用户ID',
    username        VARCHAR(50)  NOT NULL COMMENT '登录用户名',
    password_hash   CHAR(64)     NOT NULL COMMENT '密码哈希(BCrypt)',
    name            VARCHAR(50)  NOT NULL COMMENT '真实姓名',
    employee_id     VARCHAR(20)  DEFAULT NULL COMMENT '关联员工工号(NULL=外部用户)',
    email           VARCHAR(100) DEFAULT NULL COMMENT '电子邮箱',
    phone           VARCHAR(20)  DEFAULT NULL COMMENT '手机号码',
    mfa_enabled     TINYINT      NOT NULL DEFAULT 0 COMMENT 'MFA启用: 0=否 1=是',
    mfa_secret      VARCHAR(100) DEFAULT NULL COMMENT 'MFA密钥',
    status          VARCHAR(20)  NOT NULL DEFAULT '活跃' COMMENT '活跃/禁用/锁定',
    last_login_at   DATETIME     DEFAULT NULL COMMENT '最后登录时间',
    last_login_ip   VARCHAR(45)  DEFAULT NULL COMMENT '最后登录IP',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_username (username),
    INDEX idx_employee_id (employee_id),
    CONSTRAINT fk_user_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- 角色表
CREATE TABLE role (
    role_id         VARCHAR(20)  NOT NULL COMMENT '角色ID',
    role_code       VARCHAR(50)  NOT NULL COMMENT '角色代码',
    role_name       VARCHAR(100) NOT NULL COMMENT '角色名称',
    description     TEXT         DEFAULT NULL COMMENT '角色描述',
    is_system       TINYINT      NOT NULL DEFAULT 0 COMMENT '是否系统内置角色',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id),
    UNIQUE KEY uk_role_code (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 权限表
CREATE TABLE permission (
    perm_id         VARCHAR(20)  NOT NULL COMMENT '权限ID',
    perm_code       VARCHAR(100) NOT NULL COMMENT '权限代码',
    perm_name       VARCHAR(100) NOT NULL COMMENT '权限名称',
    module          VARCHAR(50)  NOT NULL COMMENT '所属模块',
    perm_type       VARCHAR(20)  NOT NULL COMMENT '菜单/按钮/API',
    resource_path   VARCHAR(200) DEFAULT NULL COMMENT '资源路径',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (perm_id),
    UNIQUE KEY uk_perm_code (perm_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限表';

-- 用户角色关联表
CREATE TABLE user_role (
    user_id         VARCHAR(20)  NOT NULL,
    role_id         VARCHAR(20)  NOT NULL,
    granted_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by      VARCHAR(20)  NOT NULL COMMENT '授权人工号',
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES system_user(user_id),
    CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES role(role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- 角色权限关联表
CREATE TABLE role_permission (
    role_id         VARCHAR(20)  NOT NULL,
    perm_id         VARCHAR(20)  NOT NULL,
    granted_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by      VARCHAR(20)  NOT NULL COMMENT '授权人工号',
    PRIMARY KEY (role_id, perm_id),
    CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES role(role_id),
    CONSTRAINT fk_rp_perm FOREIGN KEY (perm_id) REFERENCES permission(perm_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';

-- ============================================================
-- 15. Agent 执行日志
-- ============================================================

CREATE TABLE agent_run_log (
    run_id          VARCHAR(32)  NOT NULL COMMENT '执行流水号(UUID)',
    agent_name      VARCHAR(100) NOT NULL COMMENT 'Agent名称',
    parent_flow_id  VARCHAR(32)  DEFAULT NULL COMMENT '所属业务流程ID',
    inputs_summary  JSON         DEFAULT NULL COMMENT '输入概要',
    reasoning_trace TEXT         DEFAULT NULL COMMENT '推理过程摘要(Chain-of-Thought)',
    outputs_summary JSON         DEFAULT NULL COMMENT '输出概要',
    model_version   VARCHAR(50)  DEFAULT NULL COMMENT '使用的模型版本',
    status          VARCHAR(20)  NOT NULL COMMENT '成功/失败/挂起',
    duration_ms     BIGINT       DEFAULT NULL COMMENT '耗时(毫秒)',
    error_detail    TEXT         DEFAULT NULL COMMENT '错误堆栈',
    retry_count     INT          NOT NULL DEFAULT 0 COMMENT '重试次数',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id),
    INDEX idx_agent_name (agent_name),
    INDEX idx_parent_flow (parent_flow_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent执行日志表';

-- ============================================================
-- 16. 审计日志 (不可篡改)
-- ============================================================

CREATE TABLE audit_log (
    audit_id        VARCHAR(32)  NOT NULL COMMENT '审计ID(UUID)',
    operation_time  DATETIME     NOT NULL COMMENT '操作时间(精确到秒)',
    operator_id     VARCHAR(20)  NOT NULL COMMENT '操作人账号',
    operator_name   VARCHAR(50)  NOT NULL COMMENT '操作人姓名',
    operator_ip     VARCHAR(45)  NOT NULL COMMENT '操作IP',
    operation_type  VARCHAR(20)  NOT NULL COMMENT '新增/修改/删除/查看/导出/登录/登出/Auto-Agent',
    module          VARCHAR(50)  NOT NULL COMMENT '招聘/入职/培训/考勤/薪资/绩效/外务/离职',
    target_id       VARCHAR(50)  NOT NULL COMMENT '操作对象ID',
    target_name     VARCHAR(100) DEFAULT NULL COMMENT '操作对象名称',
    before_snapshot JSON         DEFAULT NULL COMMENT '变更前快照',
    after_snapshot  JSON         DEFAULT NULL COMMENT '变更后快照',
    result          VARCHAR(20)  NOT NULL COMMENT '成功/失败',
    duration_ms     INT          DEFAULT NULL COMMENT '耗时(毫秒)',
    trace_id        VARCHAR(64)  DEFAULT NULL COMMENT '链路追踪ID',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    INDEX idx_operation_time (operation_time),
    INDEX idx_operator_id (operator_id),
    INDEX idx_module (module),
    INDEX idx_target_id (target_id),
    INDEX idx_operation_type (operation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表(不可篡改)';

-- ============================================================
-- 17. 通知消息
-- ============================================================

CREATE TABLE notification (
    notification_id VARCHAR(20)  NOT NULL COMMENT '通知ID',
    recipient_id    VARCHAR(20)  NOT NULL COMMENT '接收人工号',
    title           VARCHAR(200) NOT NULL COMMENT '通知标题',
    content         TEXT         NOT NULL COMMENT '通知内容',
    notify_type     VARCHAR(20)  NOT NULL COMMENT '系统/薪资/培训/考勤/外务',
    channel         VARCHAR(20)  NOT NULL DEFAULT '站内信' COMMENT '站内信/短信/邮件',
    status          VARCHAR(20)  NOT NULL DEFAULT '未读' COMMENT '未读/已读/已发送/发送失败',
    related_type    VARCHAR(50)  DEFAULT NULL COMMENT '关联业务类型',
    related_id      VARCHAR(50)  DEFAULT NULL COMMENT '关联业务ID',
    sent_at         DATETIME     DEFAULT NULL COMMENT '发送时间',
    read_at         DATETIME     DEFAULT NULL COMMENT '阅读时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (notification_id),
    INDEX idx_recipient (recipient_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知消息表';

-- ============================================================
-- 18. 证书证照台账
-- ============================================================

CREATE TABLE certificate_registry (
    cert_reg_id     VARCHAR(20)  NOT NULL COMMENT '证书登记ID',
    employee_id     VARCHAR(20)  NOT NULL COMMENT '员工工号',
    cert_name       VARCHAR(200) NOT NULL COMMENT '证书名称',
    cert_no         VARCHAR(100) DEFAULT NULL COMMENT '证书编号',
    issue_org       VARCHAR(200) DEFAULT NULL COMMENT '发证机构',
    issue_date      DATE         DEFAULT NULL COMMENT '发证日期',
    expiry_date     DATE         DEFAULT NULL COMMENT '到期日期',
    cert_type       VARCHAR(50)  NOT NULL COMMENT '特种作业证/上岗证/行业资格证',
    file_uri        VARCHAR(500) DEFAULT NULL COMMENT '证书扫描件URI',
    status          VARCHAR(20)  NOT NULL DEFAULT '有效' COMMENT '有效/即将过期/已过期/待人工确认',
    warning_days    INT          NOT NULL DEFAULT 60 COMMENT '预警天数',
    next_renewal    DATE         DEFAULT NULL COMMENT '下次续期日期',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (cert_reg_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_expiry_date (expiry_date),
    INDEX idx_status (status),
    CONSTRAINT fk_certreg_emp FOREIGN KEY (employee_id) REFERENCES employee(employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证书证照台账';

-- ============================================================
-- 初始化数据
-- ============================================================

-- 初始化系统角色
INSERT INTO role (role_id, role_code, role_name, description, is_system) VALUES
('ROLE_ADMIN', 'ADMIN', '系统管理员', '系统基础设施运维和技术管理', 1),
('ROLE_HR_MGR', 'HR_MANAGER', '人事主管', 'HR流程管理与审核决策', 1),
('ROLE_HR', 'HR_SPECIALIST', '人事专员', 'HR流程监督与审核', 1),
('ROLE_MGR', 'DEPT_MANAGER', '部门主管', '业务决策审批与团队管理', 1),
('ROLE_EMP', 'EMPLOYEE', '普通员工', '自助信息查询与服务', 1),
('ROLE_EXTERNAL', 'EXTERNAL_SPECIALIST', '外务专员', '政务联络与协调', 1);

-- 初始化基础权限 (示例)
INSERT INTO permission (perm_id, perm_code, perm_name, module, perm_type, resource_path) VALUES
('PERM_001', 'recruit:view', '查看招聘信息', '招聘', '菜单', '/hr/recruit'),
('PERM_002', 'recruit:resume:review', '审核简历', '招聘', '按钮', '/api/v1/resumes/*/review'),
('PERM_003', 'payroll:view', '查看薪资信息', '薪资', '菜单', '/hr/payroll'),
('PERM_004', 'payroll:audit', '审核薪资', '薪资', '按钮', '/api/v1/payroll/*/audit'),
('PERM_005', 'payroll:export', '导出薪资数据', '薪资', 'API', '/api/v1/payroll/export'),
('PERM_006', 'attendance:view', '查看考勤信息', '考勤', '菜单', '/hr/attendance'),
('PERM_007', 'training:view', '查看培训信息', '培训', '菜单', '/hr/training'),
('PERM_008', 'external:view', '查看外务信息', '外务', '菜单', '/hr/external'),
('PERM_009', 'system:admin', '系统管理', '系统', '菜单', '/admin'),
('PERM_010', 'audit:view', '查看审计日志', '系统', '菜单', '/admin/audit-log');

-- 初始化默认班次
INSERT INTO shift (shift_id, shift_name, start_time, end_time, break_minutes) VALUES
('SHIFT_001', '早班', '08:00:00', '17:00:00', 60),
('SHIFT_002', '中班', '12:00:00', '21:00:00', 60),
('SHIFT_003', '晚班', '20:00:00', '08:00:00', 60);

-- ============================================================
-- 视图定义 (用于简化复杂查询)
-- ============================================================

-- 员工完整信息视图
CREATE OR REPLACE VIEW v_employee_full AS
SELECT
    e.employee_id,
    e.name,
    e.id_number,
    e.gender,
    e.birth_date,
    e.phone,
    e.email,
    d.dept_id,
    d.dept_name,
    p.position_id,
    p.position_name,
    e.hire_date,
    e.leave_date,
    e.status,
    es.base_pay,
    es.effective_date AS salary_effective_date
FROM employee e
JOIN department d ON e.dept_id = d.dept_id
JOIN position p ON e.position_id = p.position_id
LEFT JOIN employee_salary es ON e.employee_id = es.employee_id;

-- 月度薪资汇总视图
CREATE OR REPLACE VIEW v_payroll_summary AS
SELECT
    p.month,
    COUNT(*) AS employee_count,
    SUM(p.net_pay) AS total_net_pay,
    AVG(p.net_pay) AS avg_net_pay,
    MIN(p.net_pay) AS min_net_pay,
    MAX(p.net_pay) AS max_net_pay,
    SUM(p.income_tax) AS total_tax,
    SUM(p.ss_personal) AS total_ss_personal,
    SUM(p.gf_personal) AS total_gf_personal
FROM payroll p
GROUP BY p.month;

-- 员工考勤月度汇总视图
CREATE OR REPLACE VIEW v_attendance_monthly AS
SELECT
    a.employee_id,
    e.name,
    d.dept_name,
    DATE_FORMAT(a.date, '%Y-%m') AS month,
    COUNT(*) AS work_days,
    SUM(a.late_count) AS total_late,
    SUM(a.early_leave_count) AS total_early_leave,
    SUM(a.absent_days) AS total_absent,
    SUM(a.overtime_hrs) AS total_overtime_hrs,
    SUM(a.holiday_leave_hrs) AS total_holiday_leave_hrs,
    SUM(a.sick_leave_hrs) AS total_sick_leave_hrs
FROM attendance_record a
JOIN employee e ON a.employee_id = e.employee_id
JOIN department d ON e.dept_id = d.dept_id
GROUP BY a.employee_id, e.name, d.dept_name, DATE_FORMAT(a.date, '%Y-%m');

-- ============================================================
-- 存储过程 (用于关键业务操作)
-- ============================================================

-- 薪资核算触发器: 薪资审核时自动记录审计日志
DELIMITER //
CREATE TRIGGER trg_payroll_audit_after
AFTER UPDATE ON payroll
FOR EACH ROW
BEGIN
    IF OLD.status != '已审核' AND NEW.status = '已审核' THEN
        INSERT INTO audit_log (
            audit_id, operation_time, operator_id, operator_name,
            operator_ip, operation_type, module, target_id,
            target_name, before_snapshot, after_snapshot, result
        ) VALUES (
            UUID(), NOW(), NEW.reviewed_by,
            (SELECT name FROM system_user WHERE user_id = NEW.reviewed_by),
            '127.0.0.1', '审核', '薪资',
            NEW.payroll_id,
            (SELECT name FROM employee WHERE employee_id = NEW.employee_id),
            JSON_OBJECT('status', OLD.status, 'net_pay', OLD.net_pay),
            JSON_OBJECT('status', NEW.status, 'net_pay', NEW.net_pay),
            '成功'
        );
    END IF;
END //
DELIMITER ;

-- ============================================================
-- 索引优化建议 (根据查询模式)
-- ============================================================

-- 简历高频查询索引
CREATE INDEX idx_resume_composite ON resume (applied_job_id, classify_result, total_score DESC);

-- 考勤范围查询索引
CREATE INDEX idx_attendance_range ON attendance_record (date, employee_id);

-- 薪资月度查询索引
CREATE INDEX idx_payroll_month_emp ON payroll (month, employee_id);

-- Agent执行日志时间范围索引
CREATE INDEX idx_agent_log_range ON agent_run_log (created_at DESC, agent_name, status);

-- 审计日志复合查询索引
CREATE INDEX idx_audit_composite ON audit_log (operation_time DESC, module, operator_id);

-- ============================================================
-- 分区表建议 (大数据量表)
-- ============================================================

-- 考勤记录按年月分区 (建议在生产环境执行)
-- ALTER TABLE attendance_record PARTITION BY RANGE (YEAR(date)*100 + MONTH(date)) (
--     PARTITION p202601 VALUES LESS THAN (202602),
--     PARTITION p202602 VALUES LESS THAN (202603),
--     ...
--     PARTITION pmax VALUES LESS THAN MAXVALUE
-- );

-- 审计日志按时间分区 (10年保留)
-- ALTER TABLE audit_log PARTITION BY RANGE (YEAR(operation_time)) (
--     PARTITION p2026 VALUES LESS THAN (2027),
--     ...
--     PARTITION p2036 VALUES LESS THAN (2037),
--     PARTITION pmax VALUES LESS THAN MAXVALUE
-- );
```

## 3. 数据库设计说明

### 3.1 表统计

| 类别 | 表数量 | 说明 |
|------|--------|------|
| 组织架构 | 2 | department, position |
| 员工档案 | 3 | employee, employee_document, e_signature |
| 招聘管理 | 5 | job_post, resume, resume_score_detail, talent_pool, exam_paper, exam_submission |
| 入职管理 | 3 | onboarding_task, onboarding_checklist, face_archive |
| 试用期 | 1 | probation_evaluation |
| 培训管理 | 4 | training_plan, training_signin, training_result, training_video |
| 考勤管理 | 4 | shift, shift_schedule, attendance_record, leave_application |
| 薪资管理 | 4 | employee_salary, salary_rule, payroll, payroll_slip |
| 绩效管理 | 2 | performance_cycle, performance_review |
| 外务管理 | 2 | injury_case, fund_record |
| 离职管理 | 1 | resignation |
| 人事证明 | 1 | certificate_application |
| 预算费用 | 1 | expense_claim |
| 系统管理 | 5 | system_user, role, permission, user_role, role_permission |
| Agent日志 | 1 | agent_run_log |
| 审计日志 | 1 | audit_log |
| 通知消息 | 1 | notification |
| 证书台账 | 1 | certificate_registry |
| **合计** | **48** | 含视图3个 |

### 3.2 敏感字段加密策略

- `employee.id_number`: AES-256-GCM 加密存储，同时存储 SHA256 哈希用于去重查询
- `employee_salary.*`: 薪资数据 AES-256-GCM 加密
- `payroll.*`: 薪资核算数据 AES-256-GCM 加密
- 密钥由 HashiCorp Vault 统一管理，每90天轮换

### 3.3 JSON 字段说明

MySQL 8.0 原生 JSON 类型用于以下场景:
- 简历评分明细 (`resume_score_detail`)
- 薪资计算底稿 (`payroll.calc_trace`)
- 工伤材料清单 (`injury_case.docs`)
- RPA操作回执 (`injury_case.rpa_receipts`)
- 加班费明细 (`payroll.overtime_detail`)
- 人才画像标签 (`talent_pool.*`)
- 试卷内容 (`exam_paper.paper_content`)
- 作答记录 (`exam_submission.answers`)