# GBM AI Agent HR 智能人力管理系统 — 后端设计文档 (V16)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 后端设计文档 |
| 版本号 | V16.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-12 |
| 修订日期 | 2026-06-13 |
| 作者 | 后旺 (HouWang) |
| 角色 | 后端架构师 |

**修订说明**
V10.0→V16.0：根据后荣检验意见逐项修正以下内容：

1. 【严重问题-文档完整性】补充完整所有 10 个章节内容，确保文档不再截断
2. 技术栈补充：说明 OpenTelemetry 追踪粒度、XXL-JOB 与 Spring Scheduled 边界
3. 项目结构补充：Entity-Mapper 完整映射表、模块依赖关系图、实体关系定义、Agent-Service 调用关系与职责边界
4. API 接口设计补充：分页/排序统一方案、RESTful 路径命名规则、版本策略
5. 数据流设计补充：核心业务全流程数据流转图（招聘→入职→考勤→培训→薪资）
6. 安全策略补充：JWT 过期与旋转策略完善、MFA 触发场景完整列表、RBAC 数据行级隔离规则、数据脱敏规则
7. 事件机制补充：Spring Event 与 Redis Stream 使用边界的完整分类标准与投递保障策略
8. 数据库设计新增：核心表索引策略、考勤日志表分表策略
9. 部署架构新增：Docker 容器化方案、Nginx 网关配置、多环境策略

---

## 目录

1. 后端技术栈
2. 项目结构
3. API 接口设计
4. 数据流设计
5. 中间件设计
6. 安全策略
7. Agent 运行时设计
8. RPA 引擎设计
9. 错误处理与异常管理
10. 性能优化策略
11. 数据库设计
12. 部署架构

---

## 1. 后端技术栈

### 1.1 核心技术

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | Java | 17 LTS | 企业级稳定性 |
| 框架 | Spring Boot | 3.2.x | 微服务基础框架 |
| Spring Cloud | - | 已移除（模块化单体不需要服务治理） |
| ORM | MyBatis-Plus | 3.5.x | 灵活 SQL 控制 |
| API 文档 | SpringDoc OpenAPI | 2.x | 自动生成 API 文档 |
| 认证 | Spring Security | 6.x | 安全框架 |
| JWT | jjwt | 0.12.x | Token 生成与验证 |
| 消息队列 | Spring Event (进程内) + Redis Stream (进程间) | - | 模块化单体内优先使用 Spring Event，跨进程可靠事件传递使用 Redis Stream（at-least-once 投递） |
| 流程引擎 | Flowable | 6.8.x | BPMN 2.0 流程编排（对 MySQL 兼容性优于 Camunda） |
| 缓存 | Redis | 7.x | Redisson 客户端 |
| 配置中心 | Nacos | 2.x | 配置热更 + 服务发现 |
| 链路追踪 | OpenTelemetry | 1.x | 分布式追踪（详见 1.1.1） |
| 日志 | SLF4J + Logback | - | 结构化日志 |
| 对象存储 | MinIO SDK | 8.x | 文件上传/下载 |
| RPA | Playwright Python (通过 HTTP API 调用) | - | 浏览器自动化（Python 生态更成熟） |
| OCR | PaddleOCR Python (通过 HTTP API 调用) | - | 证件识别（Python 生态更成熟） |
| 人脸 | Face++ SDK / 自研 | - | 人脸比对 |
| 定时任务 | XXL-JOB | 2.x | 分布式任务调度（详见 1.1.2） |
| WebSocket | Spring WebSocket + STOMP | - | 实时推送（Dashboard 待办提醒、Agent 状态更新） |
| 测试 | JUnit 5 + Mockito | - | 单元测试 |
| 测试容器 | Testcontainers | - | 集成测试 |
| 密钥管理 | HashiCorp Vault | 1.x | 加密密钥、API 凭证安全管理 |
| 监控 | Prometheus + Grafana | - | 指标采集与可视化 |
| 弹性容错 | Resilience4j | 2.x | 熔断器、限流、超时控制（替代 Hystrix，与 Spring Boot 3.x 兼容） |

#### 1.1.1 OpenTelemetry 追踪粒度说明

**设计决策：为什么 HR 系统需要 OpenTelemetry**

本系统为 AI 原生系统，单笔用户操作可能触发多个 Agent 串联执行（如入职流程：OnboardingGuideAgent → OCRAgent → FaceAgent → ExternalAgent → TrainingAgent），每个 Agent 又可能调用外部服务（LLM、OCR、RPA、社保系统）。OpenTelemetry 提供全链路追踪能力，使运维人员能够在复杂的多 Agent 调用链中定位性能瓶颈和故障根因。

**追踪粒度定义：**

| 层级 | Trace 范围 | 示例 | 采样策略 |
|------|-----------|------|---------|
| HTTP 请求 | 从网关到 Controller 结束 | 用户发起薪资核算请求 | 100% 全量采样 |
| Agent 执行 | 从 Agent.execute() 开始到结束 | PayrollAgent 执行全流程 | 100% 全量采样 |
| LLM 调用 | 单次 LLM API 请求 | 简历语义匹配调用 GPT | 100% 全量采样 |
| 数据库查询 | 单次 SQL 执行 | 查询考勤记录 | 1% 采样（日志已覆盖） |
| 外部 HTTP | 单次 HTTP 调用 | 调用 RPA 子服务 | 100% 全量采样 |
| Redis 操作 | 单次 Redis 命令 | 获取薪资规则缓存 | 1% 采样（日志已覆盖） |

**Trace 上下文传递方式：**

- HTTP 请求：通过 `traceparent` 标准 Header 传递 W3C TraceContext
- Spring Event：事件对象携带 `traceId` 字段，监听器从事件中提取并设置当前上下文
- Redis Stream：消息 payload 中包含 `trace_id` 字段，消费者反序列化后恢复上下文
- Agent 编排：`AgentContext` 中包含 `flowId`（等同于 Flowable 的 `processInstanceId`）和 `traceId`

**Trace 数据存储与保留：**

- 存储后端：Jaeger（与 OpenTelemetry Collector 配合）
- 保留周期：30 天（热存储）+ 90 天（冷归档）
- 存储容量估算：日均 500 次 Agent 执行 × 平均 5 次子调用 × 每 span 约 1KB ≈ 2.5MB/天

#### 1.1.2 XXL-JOB 与 Spring Scheduled 边界说明

**设计决策：统一使用 XXL-JOB，不使用 Spring @Scheduled**

| 维度 | XXL-JOB | Spring @Scheduled |
|------|---------|------------------|
| 调度方式 | 中心化调度器分发任务 | 进程内定时器 |
| 可视化 | 有（Web 控制台，查看执行历史、日志、失败重试） | 无（需查看应用日志） |
| 失败重试 | 内置可配置 | 需自行实现 |
| 执行日志 | 自动记录至 XXL-JOB 调度中心 | 需自行记录 |
| 分片广播 | 支持（多节点并行处理） | 不支持 |
| 手动触发 | 控制台一键触发 | 需重启或加 API |
| 运行统计 | 控制台查看成功率、耗时趋势 | 无 |

**哪些任务使用 XXL-JOB：**

| Job Handler | Cron | 类型 | 说明 |
|-------------|------|------|------|
| ResumeCrawlJob | `0 */15 * * * ?` | 数据采集 | 从招聘平台抓取新简历 |
| AttendanceSyncJob | `0 */30 * * * ?` | 数据采集 | 同步打卡设备数据 |
| MonthlyPayrollJob | `0 0 2 27 * ?` | 核心业务 | 月末薪资核算 |
| CertificateExpiryJob | `0 9 * * ?` | 巡检 | 证书效期检查 |
| TalentHealthCheckJob | `0 0 3 ? * 0` | 巡检 | 简历库健康检查 |
| RPAValidationJob | `0 10 ? * 1` | 运维 | 验证 RPA 流程可用性 |
| DataArchiveJob | `0 0 2 ? * 0` | 运维 | 数据归档 |
| BackupJob | `0 0 1 ? * 6` | 运维 | 全量备份 |
| ModelAccuracyJob | `0 0 9 1 * ?` | 模型治理 | 模型精度复查 |
| BiasTestJob | `0 0 10 1 */3 ?` | 模型治理 | 偏见测试 |

**不使用 Spring @Scheduled 的场景（即本系统没有使用 @Scheduled 的任务）：**

本系统所有定时任务统一由 XXL-JOB 管理，不引入 Spring `@Scheduled` 注解，避免维护两套调度体系。原因：
1. XXL-JOB 提供可视化调度中心，运维人员可直接查看任务执行历史、失败重试、手动触发
2. 模块化单体未来可能拆分微服务，XXL-JOB 天然支持分布式调度
3. 任务日志自动持久化至 XXL-JOB 调度中心，无需各模块自行实现日志记录

### 1.2 架构模式

采用**模块化单体 (Modular Monolith)** 架构，各模块通过包边界隔离，后期可按需拆分为微服务。

**模块划分依据**：
- 业务域独立性
- 数据隔离性
- 部署独立性（未来）
- 团队职责划分

**核心模块依赖原则**：
- `gbm-hr-core` 为唯一公共基础模块，不依赖任何业务模块
- 业务模块之间禁止相互依赖，通过 Spring Event / Redis Stream 实现解耦通信
- `gbm-hr-employee` 为 Employee 核心领域对象的归属模块，attendance/payroll/training 等模块通过核心 ID 引用而非直接依赖 Employee 实体

---

## 2. 项目结构

### 2.1 目录结构

```
gbm-ai-agent-hr-backend/
├── gbm-hr-core/                     # 核心公共模块
│   ├── src/main/java/com/gbm/hr/core/
│   │   ├── config/                  # 全局配置
│   │   │   ├── SwaggerConfig.java
│   │   │   ├── RedisConfig.java
│   │   │   ├── SpringEventConfig.java
│   │   │   ├── RedisPubSubConfig.java
│   │   │   ├── MyBatisConfig.java
│   │   │   ├── WebMvcConfig.java
│   │   │   ├── SecurityConfig.java
│   │   │   └── VaultConfig.java
│   │   ├── constant/                # 常量定义
│   │   │   ├── ErrorCode.java
│   │   │   ├── CacheKey.java
│   │   │   └── EventType.java
│   │   ├── dto/                     # 通用 DTO
│   │   │   ├── Result.java          # 统一响应
│   │   │   ├── PageRequest.java
│   │   │   ├── PageResult.java
│   │   │   └── BaseEntity.java
│   │   ├── exception/               # 异常定义
│   │   │   ├── BusinessException.java
│   │   │   ├── GlobalExceptionHandler.java
│   │   │   └── ValidationException.java
│   │   ├── util/                    # 工具类
│   │   │   ├── EncryptUtil.java
│   │   │   ├── DateUtil.java
│   │   │   ├── IdGenerator.java
│   │   │   ├── FileUtil.java
│   │   │   ├── ExcelUtil.java
│   │   │   └── VaultService.java
│   │   └── validator/               # 校验器
│   │       ├── IdCardValidator.java
│   │       ├── PhoneValidator.java
│   │       └── AmountValidator.java
│   └── build.gradle
│
├── gbm-hr-auth/                     # 认证授权模块
│   ├── src/main/java/com/gbm/hr/auth/
│   │   ├── controller/
│   │   │   ├── AuthController.java
│   │   │   ├── MFAController.java
│   │   │   └── PermissionController.java
│   │   ├── service/
│   │   │   ├── AuthService.java
│   │   │   ├── MFAService.java
│   │   │   ├── TokenService.java
│   │   │   └── PermissionService.java
│   │   ├── entity/
│   │   │   ├── User.java
│   │   │   ├── Role.java
│   │   │   └── UserRole.java
│   │   ├── mapper/
│   │   │   ├── UserMapper.java
│   │   │   ├── RoleMapper.java
│   │   │   └── UserRoleMapper.java
│   │   └── filter/
│   │       ├── JwtAuthenticationFilter.java
│   │       └── MFAFilter.java
│   └── build.gradle
│
├── gbm-hr-recruitment/              # 招聘管理模块
│   ├── src/main/java/com/gbm/hr/recruitment/
│   │   ├── controller/
│   │   │   ├── JobPostController.java
│   │   │   ├── ResumeController.java
│   │   │   ├── ExamController.java
│   │   │   ├── QuestionBankController.java
│   │   │   └── TalentPoolController.java
│   │   ├── service/
│   │   │   ├── JobPostService.java
│   │   │   ├── ResumeService.java
│   │   │   ├── ResumeMatchingService.java
│   │   │   ├── ExamService.java
│   │   │   ├── GradingService.java
│   │   │   └── TalentPoolService.java
│   │   ├── agent/
│   │   │   ├── RecruitmentChannelAgent.java
│   │   │   ├── ResumeMatchingAgent.java
│   │   │   ├── ExamPaperAgent.java
│   │   │   └── GradingAgent.java
│   │   ├── entity/
│   │   │   ├── JobPost.java
│   │   │   ├── Resume.java
│   │   │   ├── ResumeScore.java
│   │   │   ├── ExamPaper.java
│   │   │   └── Question.java
│   │   ├── mapper/
│   │   │   ├── JobPostMapper.java
│   │   │   ├── ResumeMapper.java
│   │   │   ├── ResumeScoreMapper.java
│   │   │   ├── ExamPaperMapper.java
│   │   │   └── QuestionMapper.java
│   │   └── job/
│   │       ├── ResumeCrawlJob.java
│   │       └── TalentHealthCheckJob.java
│   └── build.gradle
│
├── gbm-hr-onboarding/               # 入职管理模块
│   ├── src/main/java/com/gbm/hr/onboarding/
│   │   ├── controller/
│   │   │   ├── OnboardingController.java
│   │   │   ├── DocumentController.java
│   │   │   └── FaceController.java
│   │   ├── service/
│   │   │   ├── OnboardingService.java
│   │   │   ├── DocumentRecognitionService.java
│   │   │   └── FaceRecognitionService.java
│   │   ├── agent/
│   │   │   ├── OnboardingGuideAgent.java
│   │   │   ├── OCRAgent.java
│   │   │   └── FaceAgent.java
│   │   ├── entity/
│   │   │   ├── OnboardingRecord.java
│   │   │   └── EmployeeDocument.java
│   │   └── mapper/
│   │       ├── OnboardingRecordMapper.java
│   │       └── EmployeeDocumentMapper.java
│   └── build.gradle
│
├── gbm-hr-training/                 # 培训管理模块
│   ├── src/main/java/com/gbm/hr/training/
│   │   ├── controller/
│   │   │   ├── TrainingPlanController.java
│   │   │   ├── TrainingSessionController.java
│   │   │   ├── CheckInController.java
│   │   │   ├── CertificateController.java
│   │   │   └── AuditMaterialsController.java
│   │   ├── service/
│   │   │   ├── TrainingPlanService.java
│   │   │   ├── CheckInService.java
│   │   │   ├── CertificateService.java
│   │   │   └── AuditMaterialsService.java
│   │   ├── agent/
│   │   │   ├── TrainingAgent.java
│   │   │   ├── VideoAgent.java
│   │   │   └── AuditMaterialsAgent.java
│   │   ├── entity/
│   │   │   ├── TrainingPlan.java
│   │   │   ├── TrainingSession.java
│   │   │   ├── CheckInRecord.java
│   │   │   └── Certificate.java
│   │   └── mapper/
│   │       ├── TrainingPlanMapper.java
│   │       ├── TrainingSessionMapper.java
│   │       ├── CheckInRecordMapper.java
│   │       └── CertificateMapper.java
│   └── build.gradle
│
├── gbm-hr-attendance/               # 考勤管理模块
│   ├── src/main/java/com/gbm/hr/attendance/
│   │   ├── controller/
│   │   │   ├── AttendanceController.java
│   │   │   ├── LeaveController.java
│   │   │   └── ShiftController.java
│   │   ├── service/
│   │   │   ├── AttendanceService.java
│   │   │   ├── AnomalyDetectionService.java
│   │   │   └── ShiftService.java
│   │   ├── agent/
│   │   │   └── AttendanceAgent.java
│   │   ├── entity/
│   │   │   ├── AttendanceRecord.java
│   │   │   ├── LeaveRecord.java
│   │   │   └── ShiftSchedule.java
│   │   └── mapper/
│   │       ├── AttendanceRecordMapper.java
│   │       ├── LeaveRecordMapper.java
│   │       └── ShiftScheduleMapper.java
│   └── build.gradle
│
├── gbm-hr-payroll/                  # 薪资管理模块
│   ├── src/main/java/com/gbm/hr/payroll/
│   │   ├── controller/
│   │   │   ├── PayrollController.java
│   │   │   ├── PayslipController.java
│   │   │   └── PayrollRuleController.java
│   │   ├── service/
│   │   │   ├── PayrollCalculationService.java
│   │   │   ├── PayslipService.java
│   │   │   ├── TaxCalculationService.java
│   │   │   └── PayrollRuleService.java
│   │   ├── agent/
│   │   │   ├── PayrollAgent.java
│   │   │   └── PayslipAgent.java
│   │   ├── entity/
│   │   │   ├── Payroll.java
│   │   │   ├── Payslip.java
│   │   │   └── PayrollRule.java
│   │   └── mapper/
│   │       ├── PayrollMapper.java
│   │       ├── PayslipMapper.java
│   │       └── PayrollRuleMapper.java
│   └── build.gradle
│
├── gbm-hr-performance/              # 绩效管理模块
│   ├── src/main/java/com/gbm/hr/performance/
│   │   ├── controller/
│   │   │   ├── PerformanceController.java
│   │   │   └── ReportController.java
│   │   ├── service/
│   │   │   ├── PerformanceService.java
│   │   │   └── ReportService.java
│   │   ├── agent/
│   │   │   └── PerformanceAgent.java
│   │   ├── entity/
│   │   │   └── PerformanceReview.java
│   │   └── mapper/
│   │       └── PerformanceReviewMapper.java
│   └── build.gradle
│
├── gbm-hr-external/                 # 外务管理模块
│   ├── src/main/java/com/gbm/hr/external/
│   │   ├── controller/
│   │   │   ├── InjuryCaseController.java
│   │   │   └── HousingFundController.java
│   │   ├── service/
│   │   │   ├── InjuryCaseService.java
│   │   │   ├── HousingFundService.java
│   │   │   └── GovernmentDeclarationService.java
│   │   ├── agent/
│   │   │   ├── ExternalAgent.java
│   │   │   └── RPAAgent.java
│   │   ├── entity/
│   │   │   ├── InjuryCase.java
│   │   │   └── HousingFundRecord.java
│   │   ├── mapper/
│   │   │   ├── InjuryCaseMapper.java
│   │   │   └── HousingFundMapper.java
│   │   └── rpa/
│   │       ├── SocialSecurityRPA.java
│   │       ├── HousingFundRPA.java
│   │       └── RPAExecutor.java
│   └── build.gradle
│
├── gbm-hr-employee/                 # 员工服务模块
│   ├── src/main/java/com/gbm/hr/employee/
│   │   ├── controller/
│   │   │   ├── EmployeeController.java
│   │   │   ├── ResignationController.java
│   │   │   ├── CertificateController.java
│   │   │   └── ExpenseController.java
│   │   ├── service/
│   │   │   ├── EmployeeService.java
│   │   │   ├── ResignationService.java
│   │   │   ├── CertificateService.java
│   │   │   └── ExpenseService.java
│   │   ├── agent/
│   │   │   ├── ResignationAgent.java
│   │   │   ├── CertificateAgent.java
│   │   │   └── BudgetAgent.java
│   │   ├── entity/
│   │   │   ├── Employee.java
│   │   │   ├── ResignationRecord.java
│   │   │   └── CertificateRequest.java
│   │   └── mapper/
│   │       ├── EmployeeMapper.java
│   │       ├── ResignationMapper.java
│   │       ├── CertificateRequestMapper.java
│   │       └── ExpenseMapper.java
│   └── build.gradle
│
├── gbm-hr-agent/                    # Agent 运行时模块
│   ├── src/main/java/com/gbm/hr/agent/
│   │   ├── runtime/
│   │   │   ├── AgentRuntime.java
│   │   │   ├── AgentContext.java
│   │   │   └── AgentResult.java
│   │   ├── orchestration/
│   │   │   ├── Orchestrator.java
│   │   │   ├── Pipeline.java
│   │   │   ├── FanOutFanIn.java
│   │   │   ├── DecisionTree.java
│   │   │   └── FeedbackLoop.java
│   │   ├── guardrail/
│   │   │   ├── Guardrail.java
│   │   │   ├── AmountGuardrail.java
│   │   │   ├── CommunicationGuardrail.java
│   │   │   ├── DataDeleteGuardrail.java
│   │   │   └── ReasoningGuardrail.java
│   │   ├── logging/
│   │   │   ├── AgentLogger.java
│   │   │   └── ReasoningTrace.java
│   │   ├── retry/
│   │   │   ├── RetryPolicy.java
│   │   │   └── ExponentialBackoff.java
│   │   ├── event/
│   │   │   ├── AgentEventPublisher.java
│   │   │   └── AgentEventListener.java
│   │   └── redis/
│   │       ├── RedisStreamProducer.java
│   │       └── RedisStreamConsumer.java
│   └── build.gradle
│
├── gbm-hr-notification/             # 通知模块
│   ├── src/main/java/com/gbm/hr/notification/
│   │   ├── controller/
│   │   │   └── NotificationController.java
│   │   ├── service/
│   │   │   ├── EmailService.java
│   │   │   ├── SMSService.java
│   │   │   ├── PushNotificationService.java
│   │   │   └── NotificationService.java
│   │   ├── template/
│   │   │   ├── EmailTemplateEngine.java
│   │   │   └── SMSTemplateEngine.java
│   │   └── redis/
│   │       └── NotificationConsumer.java
│   └── build.gradle
│
├── gbm-hr-audit/                    # 审计模块
│   ├── src/main/java/com/gbm/hr/audit/
│   │   ├── service/
│   │   │   └── AuditLogService.java
│   │   ├── aspect/
│   │   │   └── AuditLogAspect.java
│   │   ├── entity/
│   │   │   └── AuditLog.java
│   │   └── mapper/
│   │       └── AuditLogMapper.java
│   └── build.gradle
│
├── gbm-hr-application/              # 启动模块
│   ├── src/main/java/com/gbm/hr/
│   │   └── GbmHrApplication.java
│   ├── src/main/resources/
│   │   ├── application.yml
│   │   ├── application-dev.yml
│   │   ├── application-test.yml
│   │   ├── application-prod.yml
│   │   └── logback-spring.xml
│   └── build.gradle
│
├── build.gradle                     # 根构建脚本
├── settings.gradle                  # 模块设置
└── gradle/                          # Gradle 包装器
```

### 2.2 模块依赖关系图

```
                    gbm-hr-core (公共基础模块)
                    ↑          ↑          ↑
         ┌─────────┐    ┌─────────┐    ┌─────────┐
         │ gbm-hr-  │    │ gbm-hr- │    │ gbm-hr- │
         │ auth     │    │ agent   │    │ audit   │
         └─────────┘    └─────────┘    └─────────┘
         ↑          ↑          ↑
    ┌────┴───┐  ┌───┴────┐  ┌──┴──────────┐
    │recruit-│  │onboard-│  │employee     │
    │ment    │  │ing     │  │             │
    └────────┘  └────────┘  └─────────────┘
         ↑          ↑          ↑
    ┌────┴──────────┴──────────┴────┐
    │ training  attendance payroll  │
    │ performance  external  notif- │
    │ ication                          │
    └────────────────────────────────┘
                            ↑
                    gbm-hr-application (启动模块)
                    依赖所有业务模块
```

**依赖说明：**

| 模块 | 依赖 | 说明 |
|------|------|------|
| gbm-hr-core | 无 | 唯一公共基础模块，不依赖任何业务模块 |
| gbm-hr-auth | gbm-hr-core | 认证授权，使用 core 的配置、异常、DTO |
| gbm-hr-agent | gbm-hr-core | Agent 运行时，使用 core 的配置、工具类 |
| gbm-hr-audit | gbm-hr-core | 审计模块，使用 core 的配置、异常 |
| gbm-hr-notification | gbm-hr-core, gbm-hr-agent | 通知模块，消费 Redis Stream 事件 |
| gbm-hr-recruitment | gbm-hr-core, gbm-hr-agent | 招聘模块，使用 Agent 运行时 |
| gbm-hr-onboarding | gbm-hr-core, gbm-hr-agent | 入职模块，通过 employeeId 引用 Employee |
| gbm-hr-employee | gbm-hr-core, gbm-hr-agent | 员工模块，Employee 实体归属模块 |
| gbm-hr-training | gbm-hr-core, gbm-hr-agent | 培训模块，通过 employeeId 引用 Employee |
| gbm-hr-attendance | gbm-hr-core, gbm-hr-agent | 考勤模块，通过 employeeId 引用 Employee |
| gbm-hr-payroll | gbm-hr-core, gbm-hr-agent | 薪资模块，通过 employeeId 引用 Employee |
| gbm-hr-performance | gbm-hr-core, gbm-hr-agent | 绩效模块，通过 employeeId 引用 Employee |
| gbm-hr-external | gbm-hr-core, gbm-hr-agent | 外务模块，通过 employeeId 引用 Employee |
| gbm-hr-application | 所有模块 | 启动模块，组装所有业务模块 |

**模块间解耦通信方式：**

- 同进程内事件通知：Spring Event（如简历入库后通知 HR 审核）
- 跨进程可靠事件：Redis Stream（如薪资核算完成通知发放工资条）
- Employee 实体引用：其他模块不依赖 gbm-hr-employee，通过 employeeId (VARCHAR) 作为逻辑外键引用，需要员工信息时通过内部 HTTP 接口或 Spring Event 异步获取

### 2.3 Entity-Mapper 完整映射表

| 模块 | Entity | Mapper | 对应表 |
|------|--------|--------|--------|
| auth | User | UserMapper | sys_user |
| auth | Role | RoleMapper | sys_role |
| auth | UserRole | UserRoleMapper | sys_user_role |
| recruitment | JobPost | JobPostMapper | recruitment_job_post |
| recruitment | Resume | ResumeMapper | recruitment_resume |
| recruitment | ResumeScore | ResumeScoreMapper | recruitment_resume_score |
| recruitment | ExamPaper | ExamPaperMapper | recruitment_exam_paper |
| recruitment | Question | QuestionMapper | recruitment_question |
| onboarding | OnboardingRecord | OnboardingRecordMapper | onboarding_record |
| onboarding | EmployeeDocument | EmployeeDocumentMapper | onboarding_employee_document |
| employee | Employee | EmployeeMapper | employee |
| employee | ResignationRecord | ResignationMapper | employee_resignation |
| employee | CertificateRequest | CertificateRequestMapper | employee_certificate_request |
| training | TrainingPlan | TrainingPlanMapper | training_plan |
| training | TrainingSession | TrainingSessionMapper | training_session |
| training | CheckInRecord | CheckInRecordMapper | training_checkin_record |
| training | Certificate | CertificateMapper | training_certificate |
| attendance | AttendanceRecord | AttendanceRecordMapper | attendance_record |
| attendance | LeaveRecord | LeaveRecordMapper | attendance_leave_record |
| attendance | ShiftSchedule | ShiftScheduleMapper | attendance_shift_schedule |
| payroll | Payroll | PayrollMapper | payroll |
| payroll | Payslip | PayslipMapper | payroll_payslip |
| payroll | PayrollRule | PayrollRuleMapper | payroll_rule |
| performance | PerformanceReview | PerformanceReviewMapper | performance_review |
| external | InjuryCase | InjuryCaseMapper | external_injury_case |
| external | HousingFundRecord | HousingFundMapper | external_housing_fund |
| agent | AgentRunLog | - | agent_run_log (由 AgentLogger 直接操作) |
| audit | AuditLog | AuditLogMapper | audit_log |
| notification | - | - | 通知使用 Redis Stream + MinIO，无独立表 |

### 2.4 实体关系定义

```
Employee (gbm-hr-employee)
├── 1:N → OnboardingRecord (gbm-hr-onboarding)
│       关系: onboarding_record.employee_id = employee.employee_id
├── 1:N → AttendanceRecord (gbm-hr-attendance)
│       关系: attendance_record.employee_id = employee.employee_id
├── 1:N → LeaveRecord (gbm-hr-attendance)
│       关系: leave_record.employee_id = employee.employee_id
├── 1:N → Payroll (gbm-hr-payroll)
│       关系: payroll.employee_id = employee.employee_id
├── 1:N → Payslip (gbm-hr-payroll)
│       关系: payslip.employee_id = employee.employee_id
├── 1:N → PerformanceReview (gbm-hr-performance)
│       关系: performance_review.employee_id = employee.employee_id
├── 1:N → TrainingSession (gbm-hr-training, 参与关系)
│       关系: training_session.participant_id = employee.employee_id
├── 1:N → CheckInRecord (gbm-hr-training)
│       关系: checkin_record.employee_id = employee.employee_id
├── 1:1 → ResignationRecord (gbm-hr-employee)
│       关系: resignation_record.employee_id = employee.employee_id
├── 1:N → CertificateRequest (gbm-hr-employee)
│       关系: certificate_request.employee_id = employee.employee_id
├── 1:N → InjuryCase (gbm-hr-external)
│       关系: injury_case.employee_id = employee.employee_id
└── 1:N → HousingFundRecord (gbm-hr-external)
        关系: housing_fund_record.employee_id = employee.employee_id

JobPost (gbm-hr-recruitment)
└── 1:N → Resume (gbm-hr-recruitment)
        关系: resume.applied_position = job_post.position_name

TrainingPlan (gbm-hr-training)
└── 1:N → TrainingSession (gbm-hr-training)
        关系: training_session.plan_id = training_plan.plan_id

Payroll (gbm-hr-payroll)
└── 1:1 → Payslip (gbm-hr-payroll)
        关系: payslip.payroll_id = payroll.payroll_id

User (gbm-hr-auth)
└── N:M → Role (gbm-hr-auth) [通过 UserRole 关联表]
```

> **注意**：跨模块的实体关系通过 employeeId（VARCHAR 类型）作为逻辑外键实现，数据库层面不建立物理外键约束（避免跨模块表锁和级联删除问题），应用层通过 Service 调用保证引用完整性。

### 2.5 Agent 与 Service 的调用关系和职责边界

**职责划分原则：**

| 层级 | 职责 | 不做的事 |
|------|------|---------|
| Service | CRUD 操作、数据库事务、数据校验、业务规则执行 | 不调用 Agent、不直接调用 LLM |
| Agent | 推理决策、LLM 调用、外部 API 调用、复杂任务编排 | 不直接操作数据库（通过 Service 间接操作） |

**调用方向**：
- Agent → Service（Agent 调用 Service 完成数据读写）
- Service 不调用 Agent（单向依赖）
- Service 通过 Spring Event 发布业务事件 → Agent 监听事件后执行推理任务

**典型调用链路：**

```
Controller → Service → (数据库操作/业务规则)
                    → Spring Event 发布
                          ↓
                    Agent 监听事件
                    → LLM 推理/外部调用
                    → 调用 Service 保存结果

例: 简历入库流程
ResumeController.import()
  → ResumeService.saveBatch() [保存简历到数据库]
  → eventPublisher.publish(ResumeNewEvent)
        ↓
ResumeMatchingAgent.onResumeNew()
  → EmbeddingService.getEmbedding() [调用 LLM]
  → ResumeMatchingService.match() [调用 Service 查询岗位数据]
  → ResumeScoreService.save() [保存评分结果]
  → eventPublisher.publish(ResumeClassifiedEvent)
```

**Agent/包位置说明：**
- Agent 类放在对应业务模块的 `agent/` 包下（与 controller/、service/ 平级）
- `gbm-hr-agent` 模块提供 Agent 运行时的基础设施（BaseAgent、编排器、护栏、日志等）
- 业务 Agent 继承 `BaseAgent`（来自 gbm-hr-agent 模块），注入本模块的 Service

---

## 3. API 接口设计

### 3.1 RESTful 规范与路径命名规则

**URL 命名规则：**
- 资源名词使用复数形式（`/api/v1/resumes` 而非 `/api/v1/resume`）
- 嵌套资源不超过 2 层（`/api/v1/training/sessions/{id}/check-in`）
- 使用短横线连接多词（`job-posts` 而非 `jobposts`）
- 状态使用查询参数（`?status=ACTIVE` 而非 `/active`）

**版本策略：**
- URL 中嵌入 API 版本号：`/api/v1/...`
- 当前版本为 v1，后续不兼容变更时升级为 v2
- 废弃的 API 版本保留至少 6 个月，期间返回 `Deprecation` 响应头

**分页统一方案：**

```
GET /api/v1/recruitment/resumes?page=1&size=20&sort=created_at,desc
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | Integer | 1 | 页码（从 1 开始） |
| size | Integer | 20 | 每页条数（最大 100） |
| sort | String | created_at,desc | 排序字段,方向（asc/desc） |

**分页响应格式：**

```json
{
    "code": 200,
    "data": {
        "total": 1580,
        "page": 1,
        "size": 20,
        "totalPages": 79,
        "items": [...]
    }
}
```

**统一响应格式：**

```java
public class Result<T> {
    private Integer code;       // 状态码: 200 成功, 400 参数错误, 401 未认证, 403 无权限, 500 系统错误
    private String message;     // 消息
    private T data;             // 数据
    private Long timestamp;     // 时间戳
    private String traceId;     // 链路追踪 ID
}
```

### 3.2 认证授权 API

#### 3.2.1 登录

```
POST /api/v1/auth/login
Content-Type: application/json

Request:
{
    "username": "string",
    "password": "string"
}

Response (200 - 无需 MFA):
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "token": "jwt_token_string",
        "refreshToken": "refresh_token_string",
        "expiresIn": 7200,
        "roles": ["HR"],
        "mfaRequired": false
    }
}

Response (200 - 需要 MFA):
{
    "code": 200,
    "message": "需要二因子验证",
    "data": {
        "mfaRequired": true,
        "mfaMethod": "sms",
        "mfaTarget": "138****8888"
    }
}
```

#### 3.2.2 MFA 验证

```
POST /api/v1/auth/mfa/verify
Content-Type: application/json
Authorization: Bearer ***

Request:
{
    "code": "123456"
}

Response (200):
{
    "code": 200,
    "data": {
        "token": "jwt_token_string",
        "refreshToken": "refresh_token_string",
        "expiresIn": 7200
    }
}
```

#### 3.2.3 Token 刷新

```
POST /api/v1/auth/refresh
Content-Type: application/json

Request:
{
    "accessToken": "expiring_access_token",
    "refreshToken": "refresh_token_string"
}

Response (200):
{
    "code": 200,
    "data": {
        "token": "new_jwt_token",
        "refreshToken": "new_refresh_token",
        "expiresIn": 7200
    }
}
```

> **Token 旋转（Rotation）机制**：
> - 请求需同时提交 accessToken 和 refreshToken，服务端验证两者均有效后才发放新 Token
> - 新 refreshToken 生成后，旧 refreshToken 立即加入 Redis 黑名单
> - 黑名单条目 TTL = 原 refreshToken 剩余有效期，到期自动删除
> - 同一 refreshToken 被使用 2 次以上触发告警（可能的 Refresh Token 重用攻击）

### 3.3 招聘管理 API

```
GET    /api/v1/recruitment/jobs                # 岗位列表 (分页)
GET    /api/v1/recruitment/jobs/{id}           # 岗位详情
POST   /api/v1/recruitment/jobs                # 创建岗位
PUT    /api/v1/recruitment/jobs/{id}           # 更新岗位
DELETE /api/v1/recruitment/jobs/{id}           # 删除岗位
POST   /api/v1/recruitment/jobs/{id}/publish   # 发布到招聘平台
GET    /api/v1/recruitment/jobs/{id}/channels  # 查看发布渠道

GET    /api/v1/recruitment/resumes                    # 简历列表 (分页+筛选)
GET    /api/v1/recruitment/resumes/{id}               # 简历详情
GET    /api/v1/recruitment/resumes/{id}/score-detail  # 评分明细
POST   /api/v1/recruitment/resumes/import             # 批量导入
GET    /api/v1/recruitment/resumes/export             # 导出简历
POST   /api/v1/recruitment/resumes/search/nl          # 自然语言搜索

GET    /api/v1/recruitment/exams                    # 考试列表
POST   /api/v1/recruitment/exams                    # 创建考试 (Agent 组卷)
GET    /api/v1/recruitment/exams/{id}/qr-code       # 生成考试二维码
POST   /api/v1/recruitment/exams/{id}/publish        # 发布考试
GET    /api/v1/recruitment/exams/{id}/results        # 查看成绩
GET    /api/v1/recruitment/exams/{token}/paper        # 考生获取试卷
POST   /api/v1/recruitment/exams/{token}/submit       # 考生提交答案

GET    /api/v1/recruitment/questions                # 题目列表
POST   /api/v1/recruitment/questions                # 添加题目
PUT    /api/v1/recruitment/questions/{id}           # 编辑题目
DELETE /api/v1/recruitment/questions/{id}           # 删除题目
POST   /api/v1/recruitment/questions/import         # 批量导入
```

### 3.4 入职管理 API

```
POST   /api/v1/onboarding/start                     # 开始入职流程
GET    /api/v1/onboarding/{employeeId}/progress     # 入职进度
POST   /api/v1/onboarding/{employeeId}/documents    # 上传证件
GET    /api/v1/onboarding/{employeeId}/documents    # 查看已传证件
POST   /api/v1/onboarding/{employeeId}/ocr          # OCR 识别
POST   /api/v1/onboarding/{employeeId}/face-capture # 人脸采集
POST   /api/v1/onboarding/{employeeId}/sign         # 电子签名
GET    /api/v1/onboarding/{employeeId}/agreements   # 待签协议
POST   /api/v1/onboarding/{employeeId}/complete     # 完成入职
GET    /api/v1/onboarding/list                      # 入职名单 (HR)
```

### 3.5 培训管理 API

```
GET    /api/v1/training/plans                       # 培训计划列表
POST   /api/v1/training/plans                       # 创建培训计划
GET    /api/v1/training/sessions                    # 培训场次列表
POST   /api/v1/training/sessions/{id}/check-in      # 签到
GET    /api/v1/training/sessions/{id}/attendance    # 签到统计
POST   /api/v1/training/sessions/{id}/exam          # 结业考试
GET    /api/v1/training/sessions/{id}/results       # 考试成绩
GET    /api/v1/training/certificates                # 证书列表
POST   /api/v1/training/video/generate              # 教材转视频
POST   /api/v1/training/audit/generate              # 生成审核资料包
```

### 3.6 考勤管理 API

```
GET    /api/v1/attendance/records                   # 考勤记录 (分页)
GET    /api/v1/attendance/summary                   # 考勤汇总
GET    /api/v1/attendance/anomalies                 # 异常列表
POST   /api/v1/attendance/leave                     # 请假申请
GET    /api/v1/attendance/shift/schedule            # 排班表
PUT    /api/v1/attendance/shift/schedule            # 调整排班
POST   /api/v1/attendance/sync                      # 手动同步打卡数据
GET    /api/v1/attendance/export                    # 导出考勤数据
```

### 3.7 薪资管理 API

```
POST   /api/v1/payroll/calculate                    # 启动薪资核算
GET    /api/v1/payroll/{month}                      # 查看核算结果
POST   /api/v1/payroll/{month}/review               # 审核确认
GET    /api/v1/payroll/{month}/anomalies            # 异常数据
GET    /api/v1/payroll/{month}/export               # 导出薪资明细
GET    /api/v1/payroll/payslip/current              # 当前月工资条
GET    /api/v1/payroll/payslip/history              # 历史工资条
GET    /api/v1/payroll/rules                        # 薪资规则
PUT    /api/v1/payroll/rules                        # 更新薪资规则
```

### 3.8 绩效管理 API

```
GET    /api/v1/performance/cycles                   # 考核周期列表
POST   /api/v1/performance/evaluate                  # 提交自评
GET    /api/v1/performance/review/pending            # 待审核列表
POST   /api/v1/performance/review/{id}/approve       # 审批确认
GET    /api/v1/performance/report                    # 绩效报告
GET    /api/v1/performance/distribution              # 等级分布
```

### 3.9 外务管理 API

```
POST   /api/v1/external/injury                      # 申报工伤
GET    /api/v1/external/injury/list                 # 工伤列表
GET    /api/v1/external/injury/{id}                 # 工伤详情
GET    /api/v1/external/injury/{id}/progress        # 理赔进度
POST   /api/v1/external/housing-fund/enroll         # 公积金参保
POST   /api/v1/external/housing-fund/seal           # 公积金封存
POST   /api/v1/external/housing-fund/supplement     # 公积金补缴
GET    /api/v1/external/housing-fund/list           # 公积金记录
```

### 3.10 员工服务 API

```
GET    /api/v1/employee/list                        # 员工列表
GET    /api/v1/employee/{id}                        # 员工档案
POST   /api/v1/employee/resignation                 # 离职申请
GET    /api/v1/employee/resignation/progress        # 离职进度
POST   /api/v1/employee/certificate                 # 申请证明
GET    /api/v1/employee/certificate/{id}            # 查看证明
POST   /api/v1/employee/expense                     # 费用报销
GET    /api/v1/employee/expense/list                # 报销记录
```

### 3.11 Agent 管理 API

```
GET    /api/v1/agent/dashboard                      # Agent 监控面板
GET    /api/v1/agent/{name}/status                  # Agent 状态
GET    /api/v1/agent/{name}/logs                    # Agent 执行日志
PUT    /api/v1/agent/{name}/config                  # 更新 Agent 参数
POST   /api/v1/agent/{name}/restart                 # 重启 Agent
POST   /api/v1/agent/{name}/trigger                 # 手动触发 Agent
GET    /api/v1/agent/alerts                         # 告警列表
POST   /api/v1/agent/alerts/{id}/acknowledge        # 确认告警
```

### 3.12 系统管理 API

```
GET    /api/v1/system/users                         # 用户列表
POST   /api/v1/system/users                         # 创建用户
PUT    /api/v1/system/users/{id}                    # 更新用户
DELETE /api/v1/system/users/{id}                    # 删除用户
GET    /api/v1/system/roles                         # 角色列表
PUT    /api/v1/system/roles/{id}/permissions        # 更新角色权限
GET    /api/v1/system/audit-logs                    # 审计日志
GET    /api/v1/system/config                        # 系统配置
PUT    /api/v1/system/config                        # 更新系统配置
POST   /api/v1/system/backup                        # 手动备份
POST   /api/v1/system/restore                       # 恢复备份
```

### 3.13 Flowable 流程管理 API

#### 3.13.1 流程实例管理

```
GET    /api/v1/process/instances                     # 流程实例列表
GET    /api/v1/process/instances/{instanceId}        # 流程实例详情
POST   /api/v1/process/instances/{instanceId}/cancel  # 终止流程实例
```

#### 3.13.2 任务管理

```
GET    /api/v1/process/tasks                         # 我的待办任务
GET    /api/v1/process/tasks/{taskId}                # 任务详情
POST   /api/v1/process/tasks/{taskId}/approve         # 审批通过
POST   /api/v1/process/tasks/{taskId}/reject          # 审批驳回
POST   /api/v1/process/tasks/{taskId}/comment         # 添加审批意见
GET    /api/v1/process/tasks/history                  # 我的已办任务
```

#### 3.13.3 流程定义管理

```
GET    /api/v1/process/definitions                   # 流程定义列表
GET    /api/v1/process/definitions/{key}/model       # 获取 BPMN 模型
POST   /api/v1/process/definitions/{key}/deploy      # 部署新流程定义
POST   /api/v1/process/definitions/{key}/suspended   # 挂起流程定义
POST   /api/v1/process/definitions/{key}/activate    # 激活流程定义
```

---

## 4. 数据流设计

### 4.1 核心业务全链路数据流

```
招聘 → 入职 → 考勤 → 培训 → 薪资

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  招聘管理     │    │  入职管理     │    │  考勤管理     │
│              │    │              │    │              │
│ 简历抓取     │───→│ 扫码登录     │───→│ 打卡数据     │
│ 简历匹配     │    │ OCR 识别     │    │ 异常识别     │
│ 组卷/阅卷    │    │ 人脸采集     │    │ 排班管理     │
│ 人才库       │    │ 签署协议     │    │ 请假管理     │
└──────────────┘    └──────────────┘    └──────────────┘
       │                    │                    │
       │ ResumeClassified   │ OnboardingComplete │ AttendanceSynced
       │ Event (Spring)     │ Event (Spring)     │ Event (Spring)
       ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  培训管理     │    │  员工档案     │    │  薪资管理     │
│              │    │              │    │              │
│ 培训计划     │←───│ Employee     │───→│ 考勤数据     │
│ 签到/考试    │    │ 主数据       │    │ 社保数据     │
│ 证书管理     │    │ (employee    │    │ 薪资规则     │
│ 审核资料     │    │  模块)       │    │ 个税计算     │
└──────────────┘    └──────────────┘    └──────────────┘
                                       │
                                       │ PayrollCalculated
                                       │ Event (Spring)
                                       ▼
                               ┌──────────────┐
                               │  工资条发放   │
                               │  (Payslip    │
                               │   Agent)     │
                               └──────────────┘
```

### 4.2 简历筛选数据流

```
招聘平台 (前程无忧/中国人才热线)
    ↓ (每15分钟定时拉取 - XXL-JOB: ResumeCrawlJob)
简历抓取 Agent (RecruitmentChannelAgent)
    ↓ (Spring Event: ResumeNewEvent)
简历去重与格式校验
    ↓
简历匹配 Agent (ResumeMatchingAgent)
    ├── 学历匹配 (15%)
    ├── 工作经验匹配 (25%)
    ├── 技能匹配 (20%)
    ├── 年龄匹配 (5%)
    ├── 证书匹配 (15%)
    └── 语义综合匹配 (20%) ← LLM API
    ↓
综合评分计算 (0-100分)
    ↓
自动分拣:
    ├── > 合格线+10分 → 高潜简历 → 自动入库
    ├── 合格线-10 ~ 合格线+10 → 候选简历 → 提交HR审核
    └── < 合格线-10分 → 淘汰简历 → 自动标记
    ↓ (Spring Event: ResumeClassifiedEvent)
简历入库 (MySQL: recruitment_resume 表)
    ↓
通知 HR (Redis Stream: notification:email channel)
    ↓
前端 Dashboard 待办提醒 (WebSocket)
```

### 4.3 新员工入职数据流

```
新员工扫码进入入职门户
    ↓
入职引导 Agent (OnboardingGuideAgent)
    ├── Step 1: 基本信息确认
    ├── Step 2: 上传证件材料
    │   ├── 身份证正反面
    │   ├── 学历证书
    │   └── 证件照
    │   ↓
    │   OCR Agent (OCRAgent)
    │   ├── OCR 识别证件
    │   ├── 提取结构化信息
    │   └── 返回识别结果
    │
    ├── Step 3: 实名认证比对
    │   └── 不一致 → 提醒重新上传
    │
    ├── Step 4: 签署电子协议
    │   ├── 推送协议列表
    │   ├── 手写签名
    │   └── 加盖时间戳和水印
    │
    ├── Step 5: 人脸采集
    │   ↓
    │   人脸 Agent (FaceAgent)
    │   ├── 检测照片质量
    │   ├── 与身份证照片比对
    │   ├── 写入人脸门禁系统
    │   └── 返回比对结果
    │
    └── Step 6: 生成人事档案
        ├── 调用 EmployeeService.create() 写入 employee 表
        ├── 建立档案索引
        └── 归档至 MinIO
    ↓ (Spring Event: OnboardingCompleteEvent)
入职完成通知 HR (Redis Stream: notification:email)
    ↓ (Spring Event: OnboardingCompleteEvent → ExternalAgent 监听)
触发公积金参保 (ExternalAgent → RPA Agent)
    ↓ (Spring Event: OnboardingCompleteEvent → TrainingAgent 监听)
触发培训计划 (TrainingAgent 自动生成培训日程)
```

### 4.4 薪资核算数据流

```
月末定时触发 (XXL-JOB: MonthlyPayrollJob)
    ↓
薪资 Agent (PayrollAgent)
    ├── Fan-Out: 并行拉取数据
    │   ├── AttendanceService → 当月考勤数据
    │   ├── HousingFundService → 公积金缴纳数据
    │   └── PayrollRuleService → 现行规则 (Redis 缓存)
    ├── Fan-In: 汇聚数据
    │
    ├── 计算流程
    │   ├── 应发工资 = 基本工资 + 加班费 - 考勤扣款 + 补贴
    │   ├── 加班费 = PayrollRuleService.getOvertimeRates().calculate(加班时长)
    │   ├── 个人社保 = 社保个人缴纳额
    │   ├── 个人公积金 = 公积金个人缴纳额
    │   ├── 应税收入 = 应发 - 社保 - 公积金 - PayrollRuleService.getTaxFreeThreshold() - 专项扣除
    │   ├── 个税 = 七级累进税率计算
    │   └── 实发 = 应发 - 社保 - 公积金 - 个税
    │
    ├── 异常检测
    │   ├── 波动 ±20% 标记
    │   ├── 个税负数标记
    │   ├── 社保/公积金为 0 标记
    │   ├── 低于最低工资标记
    │   └── 加班费异常标记
    │
    └── 输出: 全员薪资明细表
    ↓ (Spring Event: PayrollCalculatedEvent)
推送 HR 审核 (Redis Stream: notification:email)
    ↓
HR 审核确认 / 退回重算
    ↓
工资条 Agent (PayslipAgent)
    ├── 批量生成工资条
    ├── 发送 (短信/邮件/APP 推送)
    └── 追踪阅读状态
    ↓
归档 (MySQL: payroll 表)
```

### 4.5 工伤处理数据流

```
工伤事件触发 (员工报告 / 系统检测)
    ↓
工伤 Agent (ExternalAgent)
    ├── 生成事故说明模板
    ├── 指导员工填写 (≥50字)
    ├── 发出材料清单
    │   ├── 病案
    │   ├── 诊断书
    │   ├── 旁证
    │   ├── 身份证件
    │   └── 出勤记录
    ├── Feedback Loop: 校验材料完整性
    │   ├── 缺失 → 提醒补传
    │   └── 完整 → 进入下一步
    │
    ├── 打包标准化备案文档
    │
    └── 调用 RPA Agent (通过 Redis Stream: rpa:task channel)
        ↓
RPA Agent (RPAAgent)
    ├── 登录社保系统 (Playwright)
    ├── 自动填写表单
    ├── 上传备案材料
    ├── 提交申报
    ├── 截图保存回执
    └── 返回申报回执 (Redis Stream: rpa:result channel)
    ↓
跟踪理赔进度 (XXL-JOB 定时查询)
    ↓
状态更新 → 通知相关人员 (Redis Stream: notification:push)
    ↓
理赔到账 → 记录理赔金额
```

---

## 5. 中间件设计

### 5.1 事件机制

#### 5.1.1 Spring Event 与 Redis Stream 使用边界

| 维度 | Spring Event | Redis Stream |
|------|-------------|-------------|
| 适用范围 | 同 JVM 进程内模块间通信 | 跨进程/跨服务可靠通信 |
| 投递保障 | 同步投递（默认），异步需 @Async | at-least-once（消费组 ACK 机制） |
| 消息持久化 | 无（内存级别，进程重启丢失） | 有（Redis 持久化，支持 AOF/RDB） |
| 消息回溯 | 不支持 | 支持（通过 stream ID 回溯） |
| 消费者组 | 不支持（每个 @EventListener 独立消费） | 支持（消费组内消息只投递一次） |
| 性能 | 高（内存传递，无序列化开销） | 中（网络 + 序列化开销） |
| 适用场景 | 同一请求上下文内的模块联动 | 需要可靠投递、异步处理、跨服务通知 |

**Spring Event 适用场景（进程内解耦）：**
- 简历入库后触发匹配评分（Recruitment 模块内）
- 入职完成后触发档案生成（Onboarding → Employee 模块）
- 薪资核算完成后触发异常检测（Payroll 模块内）
- Agent 执行完成后触发通知（Agent → Notification 模块）

**Redis Stream 适用场景（可靠投递/跨进程）：**
- 邮件/短信/推送通知（Notification 模块消费）
- RPA 任务分发和结果回传（RPA Python 子服务消费/生产）
- Agent 错误告警（告警服务消费）
- 跨服务状态同步（如薪资核算完成通知前端 Dashboard）

**事件类型分类标准：**

| 事件类型 | 投递方式 | 保障级别 | 重试策略 | 示例 |
|---------|---------|---------|---------|------|
| 业务通知类 | Spring Event + @Async | best-effort | 不重试（通知类丢失可接受） | 简历入库通知 |
| 流程推进类 | Spring Event + @Async | at-least-once | 失败记日志，人工触发补偿 | 入职完成触发公积金参保 |
| 通知投递类 | Redis Stream | at-least-once | 消费组 ACK 失败自动重试 | 邮件/短信发送 |
| RPA 任务类 | Redis Stream | at-least-once | 消费组 ACK + 死信队列 | RPA 申报任务 |
| 告警类 | Redis Stream | at-least-once | 消费组 ACK + 升级机制 | Agent 错误告警 |

#### 5.1.2 Spring Event 使用示例

```java
// 事件定义
public class ResumeClassifiedEvent extends ApplicationEvent {
    private final String resumeId;
    private final String classifyResult;
    private final String flowId;
    
    public ResumeClassifiedEvent(Object source, String resumeId, String classifyResult, String flowId) {
        super(source);
        this.resumeId = resumeId;
        this.classifyResult = classifyResult;
        this.flowId = flowId;
    }
}

// 事件发布
@Service
public class ResumeMatchingService {
    @Autowired
    private ApplicationEventPublisher eventPublisher;
    
    public void classifyResume(Resume resume) {
        // ... 分拣逻辑
        eventPublisher.publishEvent(new ResumeClassifiedEvent(
            this, resume.getId(), result, flowId));
    }
}

// 事件监听（@Async 异步执行）
@Component
public class HRNotificationListener {
    @Async
    @EventListener
    public void onResumeClassified(ResumeClassifiedEvent event) {
        notificationService.sendHRNotification(event);
    }
}
```

> **异步事件监听配置**：
> - `@EventListener` 默认同步执行，涉及 LLM 调用等耗时操作的监听器必须添加 `@Async` 注解
> - 配置独立线程池：在 `SpringEventConfig` 中定义 `AsyncEventExecutor` Bean
> - 线程池参数：核心线程数 5，最大线程数 20，队列容量 100

#### 5.1.3 Redis Stream 使用示例

| Channel | 用途 | 消费者 | 可靠性 |
|---------|------|--------|--------|
| `notification:email` | 邮件通知 | 邮件发送服务 | at-least-once |
| `notification:sms` | 短信通知 | 短信发送服务 | at-least-once |
| `notification:push` | APP 推送 | 推送服务 | best-effort |
| `agent:event` | Agent 状态更新 | 前端 Dashboard (WebSocket) | best-effort |
| `agent:error` | Agent 错误告警 | 告警服务 | at-least-once |
| `rpa:task` | RPA 任务分发 | RPA Python 子服务 | at-least-once |
| `rpa:result` | RPA 结果回传 | 主服务 RPA 模块 | at-least-once |

```java
// Redis Stream 发布
@Service
public class RedisStreamService {
    @Autowired
    private StringRedisTemplate redisTemplate;
    
    public void publish(String stream, String message) {
        Map<String, String> entry = new HashMap<>();
        entry.put("payload", message);
        redisTemplate.opsForStream().add(stream, entry);
    }
}

// Redis Stream 订阅（使用 StreamListener）
@Component
public class NotificationConsumer {
    @Autowired
    private StringRedisTemplate redisTemplate;
    
    private final static String GROUP = "notification-group";
    private final static String CONSUMER = "notification-consumer";
    
    @PostConstruct
    public void startListening() {
        StreamListener.<String, MapRecord<String, String, String>>consumer(
            Consumer.from(GROUP, CONSUMER))
            .stream(Streams.stream("notification:email"))
            .read(StreamReadOptions.empty().block(Duration.ofSeconds(5)))
            .listen(record -> {
                try {
                    processNotification(record.getValue());
                    redisTemplate.opsForStream().acknowledge(
                        "notification:email", record.getId());
                } catch (Exception e) {
                    log.error("处理通知消息失败: recordId={}", record.getId(), e);
                }
            });
    }
}
```

#### 5.1.4 消息格式

```json
{
    "message_id": "uuid-v4",
    "trace_id": "uuid-v4",
    "flow_id": "uuid-v4",
    "source": "module_name",
    "target": "module_name|channel_name",
    "event_type": "string",
    "priority": "HIGH|MEDIUM|LOW",
    "ttl_seconds": 3600,
    "payload": {},
    "metadata": {
        "created_at": "2026-06-12T10:00:00Z",
        "retry_count": 0,
        "max_retries": 3
    }
}
```

### 5.2 Redis 缓存

#### 缓存策略

| 缓存 Key 模式 | 过期时间 | 用途 |
|--------------|---------|------|
| `user:session:{userId}` | 2h | 用户会话 |
| `user:token:{tokenId}` | 2h | Token 黑名单 |
| `payroll:rule:current` | 永久 | 现行薪资规则 |
| `attendance:today:{date}` | 24h | 当日考勤 |
| `recruitment:job:{jobId}` | 24h | 岗位信息 |
| `training:qr:{qrCode}` | 2h | 签到二维码 |
| `exam:paper:{examId}` | 考试期间 | 试卷缓存 |
| `rate:limit:{ip}:{action}` | 1min | 速率限制 |
| `agent:lock:{agentName}` | 30s | Agent 分布式锁 |
| `distributed:lock:{resource}` | 10s | 通用分布式锁 |

#### 分布式锁实现

```java
@Service
public class DistributedLockService {
    @Autowired
    private RedissonClient redisson;
    
    public boolean tryLock(String lockKey, long waitTime, long leaseTime, TimeUnit unit) {
        RLock lock = redisson.getLock(lockKey);
        try {
            return lock.tryLock(waitTime, leaseTime, unit);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }
    
    public void unlock(String lockKey) {
        RLock lock = redisson.getLock(lockKey);
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
```

### 5.3 Flowable 流程引擎

**选型理由**：Flowable 对 MySQL 兼容性优于 Camunda 7.x（Camunda 内置引擎要求 PostgreSQL），更适合当前技术栈。

#### 流程定义 (BPMN)

```
入职流程 (onboarding_process.bpmn):
    [开始] → 扫码登录
        → [入职引导 Agent] 引导材料上传
        → [OCR Agent] 识别证件
        → 校验完整性?
            → 否 → [Feedback Loop] 提醒补传 → 回到材料上传
            → 是 → [人脸 Agent] 采集人脸
        → 签署电子协议
        → 生成人事档案
        → [公积金 Agent] 自动参保
        → [培训 Agent] 推送培训计划
        → [结束]

薪资核算流程 (payroll_process.bpmn):
    [定时触发: 月末] → [Fan-Out]
        → [考勤 Agent] 拉取考勤数据
        → [社保系统] 拉取缴费数据
        → [规则库] 读取薪资规则
    → [Fan-In] 汇聚数据
    → [薪资 Agent] 执行计算
    → 异常检测
        → 有异常 → 标记异常
    → [HR 审核] 等待人工确认
        → 确认 → [工资条 Agent] 批量发放
        → 退回 → [薪资 Agent] 重新计算
    → [结束]
```

**Flowable 与 Agent 编排器职责划分：**

| 维度 | Flowable BPMN | Agent 编排器 |
|------|--------------|-------------|
| 生命周期 | 长生命周期（跨天/跨周） | 短生命周期（分钟级） |
| 典型流程 | 入职流程、薪资核算、工伤申报、离职流程 | 简历匹配流水线、薪资 Fan-Out/Fan-In、组卷/阅卷 |
| 人工介入 | 需要（审核节点、等待节点） | 无需（纯自动执行） |
| 状态持久化 | BPMN 引擎自动管理 | 自定义 process_instance 表 |
| 断点恢复 | 引擎内置 | 根据 flow_id 从断点恢复 |
| 重试机制 | BPMN Service Task 重试 | SDK 内置 RetryPolicy |

**AgentCompletionCallback 接口：**

```java
public interface AgentCompletionCallback {
    void complete(String taskId, Map<String, Object> variables);
    void onError(String taskId, String error, Map<String, Object> variables);
}

@Service
public class FlowableAgentCallback implements AgentCompletionCallback {
    @Autowired
    private RuntimeService runtimeService;
    @Autowired
    private TaskService taskService;
    
    @Override
    @Transactional
    public void complete(String taskId, Map<String, Object> variables) {
        Task task = taskService.createTaskQuery().taskId(taskId).singleResult();
        if (task == null) {
            runtimeService.complete(taskId, variables);
        } else {
            taskService.complete(taskId, variables);
        }
    }
    
    @Override
    @Transactional
    public void onError(String taskId, String error, Map<String, Object> variables) {
        variables.put("agent_error", error);
        variables.put("agent_status", "FAILED");
        runtimeService.setVariable(taskId, "bpmnError", error);
        taskService.createTask(taskId + "_compensation");
        taskService.setAssignee(taskId + "_compensation", "hr_admin");
    }
}
```

### 5.4 XXL-JOB 定时任务

| Job Handler | Cron 表达式 | 描述 |
|-------------|------------|------|
| ResumeCrawlJob | `0 */15 * * * ?` | 每 15 分钟抓取简历 |
| AttendanceSyncJob | `0 */30 * * * ?` | 每 30 分钟同步打卡数据 |
| MonthlyPayrollJob | `0 0 2 27 * ?` | 每月 27 日凌晨 2 点核算薪资 |
| CertificateExpiryJob | `0 9 * * ?` | 每天 9 点检查证书效期 |
| TalentHealthCheckJob | `0 0 3 ? * 0` | 每周日凌晨 3 点简历健康检查 |
| RPAValidationJob | `0 10 ? * 1` | 每周一 10 点验证 RPA 流程 |
| DataArchiveJob | `0 0 2 ? * 0` | 每周日凌晨 2 点数据归档 |
| BackupJob | `0 0 1 ? * 6` | 每周日凌晨 1 点全量备份 |
| ModelAccuracyJob | `0 0 9 1 * ?` | 每月 1 日 9 点模型精度复查 |
| BiasTestJob | `0 0 10 1 */3 ?` | 每季度首日 10 点偏见测试 |

**XXL-JOB 配置类：**

```java
@Configuration
public class XxlJobConfig {
    @Value("${xxl.job.admin.addresses}")
    private String adminAddresses;
    @Value("${xxl.job.accessToken}")
    private String accessToken;
    @Value("${xxl.job.executor.appname}")
    private String appname;
    @Value("${xxl.job.executor.port:9999}")
    private int port;
    @Value("${xxl.job.executor.logpath}")
    private String logPath;
    @Value("${xxl.job.executor.logretentiondays:30}")
    private int logRetentionDays;

    @Bean
    public XxlJobSpringExecutor xxlJobExecutor() {
        XxlJobSpringExecutor executor = new XxlJobSpringExecutor();
        executor.setAdminAddresses(adminAddresses);
        executor.setAccessToken(accessToken);
        executor.setAppname(appname);
        executor.setPort(port);
        executor.setLogPath(logPath);
        executor.setLogRetentionDays(logRetentionDays);
        return executor;
    }
}
```

---

## 6. 安全策略

### 6.1 认证流程

```
客户端 → 输入账号密码
    ↓
AuthController → 验证凭证
    ↓
AuthService → 查询用户信息
    ↓
检查是否需要 MFA?
    ├── 是 → 生成临时 Token → 发送验证码
    │       → 客户端输入验证码
    │       → MFAController → 验证验证码
    │       → 生成正式 JWT Token
    │
    └── 否 → 直接生成 JWT Token
    ↓
返回 Token 给客户端
    ↓
后续请求携带 Token (Authorization: Bearer ***)
    ↓
JwtAuthenticationFilter → 验证 Token
    ↓
加载用户权限到 SecurityContext
    ↓
业务逻辑执行
```

### 6.2 JWT Token 设计与过期策略

```java
public class JwtToken {
    private String alg = "RS256";
    private String typ = "JWT";
    private String sub;          // 用户 ID
    private String username;     // 用户名
    private List<String> roles;  // 角色列表
    private List<String> perms;  // 权限列表
    private Long iat;            // 签发时间
    private Long exp;            // 过期时间
    private Long nbf;            // 生效时间
    private String jti;          // Token 唯一 ID
    private String traceId;      // 链路追踪 ID
}
```

| Token 类型 | 有效期 | 说明 |
|-----------|--------|------|
| Access Token | 2 小时 | 用于 API 请求认证，过期后需使用 Refresh Token 刷新 |
| Refresh Token | 7 天 | 用于刷新 Access Token，采用 Rotation 机制（每次刷新后旧 Token 作废） |
| 临时 Token (MFA) | 10 分钟 | 仅用于 MFA 验证阶段，验证完成后销毁 |

**RSA 密钥对**：2048 位，存储在 HashiCorp Vault 中，每 90 天轮换一次。

**Token 旋转机制**：
- 请求需同时提交 accessToken 和 refreshToken
- 新 refreshToken 生成后，旧 refreshToken 立即加入 Redis 黑名单
- 黑名单条目 TTL = 原 refreshToken 剩余有效期
- 同一 refreshToken 被使用 2 次以上触发告警

### 6.3 RBAC 权限模型与数据行级隔离

**角色-权限模型：**

```
用户 (User)
    ↓ (多对多，通过 UserRole 关联表)
角色 (Role)
    ↓ (多对多)
权限 (Permission)

权限命名规则: {模块}:{资源}:{操作}
```

**预设角色：**

| 角色 | 说明 | 典型权限 |
|------|------|---------|
| SYSTEM_ADMIN | 系统管理员 | system:*:* 全部系统管理权限 |
| HR_ADMIN | HR 管理员 | 全部 HR 模块操作权限 + payroll:data:* |
| HR_SPECIALIST | HR 专员 | recruitment:*, onboarding:*, training:*, attendance:read |
| DEPT_MANAGER | 部门主管 | 本部门 performance:*, attendance:read, employee:read |
| EMPLOYEE | 普通员工 | 自助查询: payslip:read, attendance:read, certificate:create |
| EXTERNAL_SPECIALIST | 外务专员 | external:* 全部外务模块权限 |

**数据行级隔离规则：**

| 角色 | 数据可见范围 | 实现方式 |
|------|------------|---------|
| SYSTEM_ADMIN | 全部数据 | 无过滤 |
| HR_ADMIN | 全部数据 | 无过滤 |
| HR_SPECIALIST | 全部数据 | 无过滤 |
| DEPT_MANAGER | 本部门及下属部门 | MyBatis 拦截器自动注入 dept_id IN (...) 条件 |
| EMPLOYEE | 仅本人数据 | MyBatis 拦截器自动注入 employee_id = {当前用户} 条件 |

**数据行级隔离实现（MyBatis 拦截器）：**

```java
@Intercepts({@Signature(
    type = StatementHandler.class,
    method = "prepare",
    args = {Connection.class, Integer.class}
)})
public class DataScopeInterceptor implements Interceptor {
    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        // 获取当前用户角色和数据范围
        UserContext context = SecurityContextHolder.getCurrentUser();
        if (context == null) return invocation.proceed();
        
        // 部门主管：注入本部门及子部门 ID
        if (context.hasRole("DEPT_MANAGER")) {
            BoundSql boundSql = getBoundSql(invocation);
            List<String> deptIds = deptService.getDescendantDeptIds(context.getDeptId());
            rewriteSql(boundSql, deptIds);
        }
        // 普通员工：注入本人 employee_id
        if (context.hasRole("EMPLOYEE")) {
            BoundSql boundSql = getBoundSql(invocation);
            rewriteSql(boundSql, context.getEmployeeId());
        }
        
        return invocation.proceed();
    }
}
```

**MFA 触发场景（强制二因子认证）：**

| 场景 | 触发方式 | MFA 方式 |
|------|---------|---------|
| 管理员首次登录 | 自动触发 | 短信验证码 / TOTP |
| 访问薪资数据 | 操作前触发 | 短信验证码 |
| 公积金/社保操作 | 操作前触发 | 短信验证码 |
| 大批量导出 (>100条) | 操作前触发 | 短信验证码 |
| 密码重置 | 操作前触发 | 短信验证码 |
| 薪资数据修改 | 操作前触发 | TOTP（时间一次性密码） |

### 6.4 数据加密

**加密算法**：AES-256-GCM，密钥由 HashiCorp Vault 管理。

```java
@Component
public class DataEncryptionService {
    @Autowired
    private VaultService vaultService;
    
    private static final String ALGORITHM = "AES/GCM/NoPadding";
    
    public String encrypt(String plaintext) throws GeneralSecurityException {
        SecretKey key = vaultService.getAESKey("hr-data-encryption");
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        GCMParameterSpec spec = new GCMParameterSpec(128, generateIV());
        cipher.init(Cipher.ENCRYPT_MODE, key, spec);
        byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
        // IV + ciphertext → Base64
        return Base64.getEncoder().encodeToString(combineIVAndCipher(spec.getIV(), ciphertext));
    }
    
    public String decrypt(String ciphertextWithIV) throws GeneralSecurityException {
        SecretKey key = vaultService.getAESKey("hr-data-encryption");
        // Base64 解码 → 分离 IV 和 ciphertext → 解密
        // ...
    }
}
```

**加密字段清单：**

| 字段 | 存储位置 | 加密方式 |
|------|---------|---------|
| 身份证号 | employee.id_number | AES-256-GCM（数据库层） |
| 人脸特征 | face.features | AES-256-GCM（数据库层） |
| 薪资数据 | payroll.net_pay | AES-256-GCM（数据库层） |
| 银行账号 | employee_pay_profile.bank_account | AES-256-GCM（数据库层） |
| RPA 登录凭证 | Vault secrets | HashiCorp Vault（不存数据库） |
| LLM API Key | Vault secrets | HashiCorp Vault（不存数据库） |
| RSA 私钥 | Vault secrets | HashiCorp Vault（不存数据库） |

**密钥管理：**
- AES 密钥存储于 HashiCorp Vault
- 密钥定期轮换（90 天）
- 应用启动时从 Vault 加载，内存中缓存
- 不同环境使用不同密钥（dev/test/prod 隔离）

### 6.5 数据脱敏规则

| 字段类型 | 脱敏规则 | 示例（原始 → 脱敏） |
|---------|---------|-------------------|
| 身份证号 | 保留前 3 位和后 4 位 | 110XXXXXXXXX1234 → 110***********1234 |
| 手机号 | 保留前 3 位和后 4 位 | 13812345678 → 138****5678 |
| 邮箱 | 保留首字符和域名 | zhangsan@example.com → z***@example.com |
| 姓名 | 保留姓氏 | 张三 → 张* |
| 银行账号 | 保留后 4 位 | 6222021234567890123 → ************0123 |
| 地址 | 保留到市级 | 北京市海淀区XX路XX号 → 北京市海淀区 |

**脱敏触发场景：**
- API 返回给非授权用户时自动脱敏（通过 Jackson 序列化拦截器）
- 日志中打印敏感字段时自动脱敏（通过 Logback 自定义转换器）
- 导出文件中自动脱敏（ExcelUtil 中处理）
- 系统管理员和 HR 管理员查看薪资数据时不需脱敏

### 6.6 审计日志 (AOP 切面)

```java
@Aspect
@Component
public class AuditLogAspect {
    @Around("@annotation(AuditLog)")
    public Object audit(ProceedingJoinPoint point, AuditLog annotation) throws Throwable {
        AuditLogEntry entry = new AuditLogEntry();
        entry.setOperationTime(LocalDateTime.now());
        entry.setOperator(getCurrentUserId());
        entry.setOperatorIp(getClientIp());
        entry.setOperationType(annotation.type());
        entry.setModule(annotation.module());
        entry.setTarget(annotation.target());
        entry.setBeforeSnapshot(serialize(getTargetObject(point)));
        
        long start = System.currentTimeMillis();
        try {
            Object result = point.proceed();
            entry.setResult("SUCCESS");
            entry.setAfterSnapshot(serialize(result));
            return result;
        } catch (Exception e) {
            entry.setResult("FAILED");
            entry.setErrorDetail(e.getMessage());
            throw e;
        } finally {
            entry.setDuration(System.currentTimeMillis() - start);
            auditLogService.save(entry);
        }
    }
}
```

**Auditor 注册机制：**

```java
public interface ModuleAuditor<T> {
    Class<T> getServiceClass();
    Object getBeforeSnapshot(ProceedingJoinPoint point);
}

@Component
public class AuditorRegistry {
    private final Map<Class<?>, ModuleAuditor<?>> auditorMap = new ConcurrentHashMap<>();
    
    public AuditorRegistry(List<ModuleAuditor<?>> auditors) {
        for (ModuleAuditor<?> auditor : auditors) {
            auditorMap.put(auditor.getServiceClass(), auditor);
        }
    }
    
    public <T> ModuleAuditor<T> getAuditor(Class<T> serviceClass) {
        // ...
    }
}
```

---

## 7. Agent 运行时设计

### 7.0 Service 与 Agent 边界定义

| 场景 | Service 职责 | Agent 职责 |
|------|-------------|-----------|
| 简历匹配 | 读取简历/岗位数据、保存评分结果 | 执行匹配算法、LLM 语义分析、生成分数 |
| 薪资核算 | 读取考勤/社保数据、保存核算结果 | 执行计算逻辑、异常检测、生成审核报告 |
| 工伤申报 | 保存案件信息、上传附件 | 生成事故说明、调用 RPA 子服务、跟踪进度 |
| 入职引导 | 保存员工档案、存储证件文件 | 引导流程、OCR 识别、人脸采集、材料校验 |

**调用方向**：Agent → Service，Service 不调用 Agent。Service 通过 Spring Event 发布业务事件，Agent 监听事件后执行推理任务。

### 7.1 Agent 基类

```java
public abstract class BaseAgent {
    protected String agentName;
    protected AgentLogger logger;
    protected AgentMessageProducer messageProducer;
    protected GuardrailExecutor guardrailExecutor;
    protected RetryPolicy retryPolicy;
    
    public AgentResult execute(AgentContext context) {
        logger.logStart(agentName, context.getFlowId());
        var inputs = perceive(context);
        var decision = reason(inputs, context);
        guardrailExecutor.check(decision);
        
        AgentResult result;
        try {
            result = retryPolicy.execute(() -> act(decision, context));
        } catch (GuardrailException e) {
            result = AgentResult.blocked(e.getMessage());
        } catch (Exception e) {
            result = AgentResult.failed(e.getMessage());
            logger.logError(agentName, context.getFlowId(), e);
        }
        
        logger.logEnd(agentName, context.getFlowId(), result);
        messageProducer.send(context.getFlowId(), agentName, result);
        return result;
    }
    
    protected abstract Map<String, Object> perceive(AgentContext context);
    protected abstract Decision reason(Map<String, Object> inputs, AgentContext context);
    protected abstract AgentResult act(Decision decision, AgentContext context);
}
```

**Agent Bean 注册与生命周期：**

- 所有业务 Agent 通过 `@Service` 注解注册为 Spring Bean
- Spring 启动时自动扫描并实例化
- `@PostConstruct` 从 Vault 加载凭证、订阅消息队列
- Agent 为单例 Bean，通过 `AgentContext` 隔离并发执行

### 7.2 Agent 执行日志

```java
@Entity
@Table(name = "agent_run_log")
public class AgentRunLog {
    @Id
    private String runId;
    private String agentName;
    private String parentFlowId;
    private JsonNode inputsSummary;
    private String reasoningTrace;
    private JsonNode outputsSummary;
    private String status;
    private Long durationMs;
    private String errorDetail;
    private LocalDateTime createdAt;
}
```

### 7.3 安全护栏实现

```java
public class AmountGuardrail implements Guardrail {
    @Override
    public void check(Decision decision) throws GuardrailException {
        if (decision.involvesAmountChange()) {
            if (!decision.hasApproval(HR_APPROVAL)) {
                throw new GuardrailException("金额变动需要人事专员审核批准");
            }
            BigDecimal amount = decision.getAmount();
            if (amount.compareTo(BigDecimal.ZERO) < 0) {
                throw new GuardrailException("金额不能为负数");
            }
        }
    }
}

public class ReasoningGuardrail implements Guardrail {
    @Override
    public void check(Decision decision) throws GuardrailException {
        if (decision.isScoringResult()) {
            int score = decision.getScore();
            if (score < 0 || score > 100) {
                throw new GuardrailException(
                    String.format("评分 %d 超出 [0,100] 范围", score));
            }
        }
        if (decision.isPayrollResult()) {
            BigDecimal salary = decision.getSalary();
            if (salary.compareTo(BigDecimal.ZERO) == 0) {
                throw new GuardrailException("薪资不能为零");
            }
        }
    }
}
```

---

## 8. RPA 引擎设计

**架构决策**：RPA 引擎作为独立的 Python 子服务运行，通过 HTTP API 与 Java 主服务通信。Playwright 在 Python 生态中更成熟。

### 8.1 RPA 子服务通信

```java
@Service
public class RPAService {
    private final WebClient webClient;
    
    @Value("${rpa.service.url:http://localhost:8090}")
    private String rpaServiceUrl;
    
    @CircuitBreaker(name = "rpaService", failureRateThreshold = 50,
        slidingWindowSize = 100, waitDurationInOpenState = 30000)
    @TimeLimiter(name = "rpaService")
    public CompletableFuture<RPAResult> executeAsync(RPATask task) {
        return webClient.post()
            .uri("/api/v1/rpa/execute")
            .bodyValue(buildRequest(task))
            .retrieve()
            .bodyToMono(RPAResult.class)
            .timeout(Duration.ofMillis(120000))
            .toFuture();
    }
    
    public RPAResult execute(RPATask task) {
        try {
            return executeAsync(task).get(120, TimeUnit.SECONDS);
        } catch (Exception e) {
            return RPAResult.degraded("RPA 服务不可用，请人工处理");
        }
    }
}
```

### 8.2 RPA 任务定义

```java
public class RPATask {
    private String taskId;
    private String targetSystem;       // 社保/公积金
    private String targetUrl;
    private Credentials credentials;   // 加密
    private List<RPAAction> actions;
    private int timeoutSeconds;
    private int maxRetries;
}

public class RPAAction {
    private ActionType type;           // CLICK/TYPE/SELECT/UPLOAD/WAIT/SCROLL
    private String selector;           // CSS 选择器
    private String value;
    private String file;
    private int timeout;
    private int scrollAmount;
}
```

### 8.3 RPA 自适应检测

```java
@Component
public class RPAAdaptationService {
    @XxlJob("RPAValidationJob")
    public ReturnT<String> validateRPAFlows(String param) {
        for (RPAFlow flow : rpaFlowRepository.findAll()) {
            ValidationResult result = dryRun(flow);
            if (!result.isAdaptable()) {
                alertService.sendAlert(
                    String.format("RPA 流程 '%s' 检测到页面变化", flow.getName()),
                    AlertLevel.WARNING, result.getChanges());
            }
            if (flow.getFailureRate() > 0.05) {
                alertService.sendAlert(
                    String.format("RPA 流程 '%s' 失败率 %.1f%%", flow.getName(), flow.getFailureRate() * 100),
                    AlertLevel.CRITICAL);
            }
        }
        return ReturnT.SUCCESS;
    }
}
```

---

## 9. 错误处理与异常管理

### 9.1 异常分类

| 异常类 | 父类 | HTTP 状态码 | 说明 |
|--------|------|------------|------|
| BusinessException | RuntimeException | 400 | 业务逻辑异常 |
| ValidationException | BusinessException | 400 | 参数校验失败 |
| AuthenticationException | RuntimeException | 401 | 认证失败 |
| AuthorizationException | RuntimeException | 403 | 权限不足 |
| ResourceNotFoundException | BusinessException | 404 | 资源不存在 |
| RateLimitException | BusinessException | 429 | 请求频率限制 |
| AgentExecutionException | RuntimeException | 500 | Agent 执行失败 |
| RPAException | AgentExecutionException | 500 | RPA 操作失败 |
| ExternalAPIException | AgentExecutionException | 502 | 外部 API 失败 |
| DataConsistencyException | RuntimeException | 500 | 数据一致性异常 |

### 9.2 全局异常处理器

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e) {
        return Result.error(400, e.getMessage());
    }
    
    @ExceptionHandler(AuthenticationException.class)
    public Result<Void> handleAuthException(AuthenticationException e) {
        return Result.error(401, e.getMessage());
    }
    
    @ExceptionHandler(AuthorizationException.class)
    public Result<Void> handleAuthorizationException(AuthorizationException e) {
        return Result.error(403, e.getMessage());
    }
    
    @ExceptionHandler(AgentExecutionException.class)
    public Result<Void> handleAgentException(AgentExecutionException e) {
        alertService.sendAgentAlert(e);
        return Result.error(500, "Agent 执行失败，已自动记录并告警");
    }
    
    @ExceptionHandler(Exception.class)
    public Result<Void> handleUnexpectedException(Exception e) {
        return Result.error(500, "系统内部错误");
    }
}
```

### 9.3 分级异常处理

```
Agent 执行异常
    ↓
异常分级:
    ├── 低级别 (可自动恢复)
    │   └── 自动重试 (指数退避，最多 3 次)
    │       └── 成功 → 继续
    │       └── 失败 → 升级为中级别
    │
    ├── 中级别 (需人工审核)
    │   └── 标记为"待人工处理"
    │   └── 生成故障摘要
    │   └── 通知相关人员 (下一工作日)
    │
    └── 高级别 (需立即处理)
        └── 立即告警 (电话/短信，5 分钟内)
        └── 暂停相关 Agent
        └── 15 分钟无人确认 → 升级通知部门负责人
```

---

## 10. 性能优化策略

### 10.1 数据库优化

| 优化手段 | 实施方式 |
|---------|---------|
| 索引优化 | 高频查询字段建立索引 (employee_id, date, status 等) |
| 分页查询 | MyBatis-Plus 分页插件，避免全表扫描 |
| 读写分离 | MySQL 主从复制，读操作走从库 |
| 连接池 | HikariCP，最大连接数 50 |
| SQL 优化 | 避免 N+1 查询，使用 JOIN 或批量查询 |
| 缓存热点数据 | Redis 缓存薪资规则、岗位信息等 |

### 10.2 API 性能优化

| 优化手段 | 实施方式 |
|---------|---------|
| 响应压缩 | GZIP 压缩响应体 |
| 分页限制 | 默认 20 条/页，最大 100 条/页 |
| 字段过滤 | 支持 SELECT 字段过滤 |
| 批量操作 | 支持批量导入/导出/更新 |
| 异步处理 | 长时间操作采用异步 + 回调 |
| CDN | 静态资源走 CDN |

### 10.3 Agent 性能优化

| 优化手段 | 实施方式 |
|---------|---------|
| LLM 缓存 | 相同输入的 LLM 请求结果缓存 (Redis) |
| 批量请求 | 批量简历评分使用 LLM Batch API |
| 并行处理 | Fan-Out 模式并行拉取数据 |
| 流式响应 | LLM 流式输出，减少等待时间 |
| 模型选择 | 简单任务用小模型，复杂任务用大模型 |
| 预计算 | 常用评分/规则提前计算并缓存 |

### 10.4 性能指标

| 指标 | 目标值 | 监控方式 |
|------|--------|---------|
| API P95 响应时间 | ≤ 3s | Prometheus + Grafana |
| Agent 执行成功率 | ≥ 95% | 自定义指标 |
| 数据库查询 P95 | ≤ 200ms | Slow Query Log |
| 缓存命中率 | ≥ 90% | Redis INFO stats |
| Redis Stream 消费延迟 | ≤ 5s | Redis Stream Pending |
| 系统 CPU 使用率 | ≤ 85% (5min) | Prometheus |
| 系统内存使用率 | ≤ 90% (5min) | Prometheus |

---

## 11. 数据库设计

### 11.1 核心表索引策略

| 表名 | 索引 | 类型 | 说明 |
|------|------|------|------|
| employee | PRIMARY KEY (employee_id) | 主键 | 工号唯一标识 |
| employee | UK_employee_id_number (id_number) | 唯一索引 | 身份证号唯一 |
| employee | IDX_employee_dept (dept_id) | 普通索引 | 按部门查询 |
| employee | IDX_employee_status (status) | 普通索引 | 按状态筛选 |
| employee | IDX_employee_hire_date (hire_date) | 普通索引 | 按入职日期范围查询 |
| recruitment_resume | PRIMARY KEY (resume_id) | 主键 | 简历唯一标识 |
| recruitment_resume | IDX_resume_position (applied_position) | 普通索引 | 按岗位筛选 |
| recruitment_resume | IDX_resume_created (created_at) | 普通索引 | 按时间排序 |
| recruitment_resume | IDX_resume_classify (classify_result) | 普通索引 | 按分类结果筛选 |
| attendance_record | PRIMARY KEY (record_id) | 主键 | 记录唯一标识 |
| attendance_record | IDX_att_emp_date (employee_id, date) | 联合索引 | 按员工+日期查询（最高频） |
| attendance_record | IDX_att_date (date) | 普通索引 | 按日期范围查询 |
| attendance_record | IDX_att_flag (flag) | 普通索引 | 按异常标记筛选 |
| payroll | PRIMARY KEY (payroll_id) | 主键 | 薪资记录唯一标识 |
| payroll | UK_payroll_emp_month (employee_id, month) | 唯一索引 | 同一员工同一月份唯一 |
| payroll | IDX_payroll_month (month) | 普通索引 | 按月查询 |
| payroll | IDX_payroll_status (status) | 普通索引 | 按状态筛选 |
| performance_review | PRIMARY KEY (pr_id) | 主键 | 考核记录唯一标识 |
| performance_review | IDX_perf_emp_cycle (employee_id, cycle) | 联合索引 | 按员工+周期查询 |
| training_session | PRIMARY KEY (session_id) | 主键 | 场次唯一标识 |
| training_session | IDX_train_plan (plan_id) | 普通索引 | 按培训计划查询 |
| training_session | IDX_train_date (session_date) | 普通索引 | 按日期查询 |
| external_injury_case | PRIMARY KEY (case_id) | 主键 | 案件唯一标识 |
| external_injury_case | IDX_injury_emp (employee_id) | 普通索引 | 按员工查询 |
| external_injury_case | IDX_injury_status (status) | 普通索引 | 按状态筛选 |
| audit_log | PRIMARY KEY (log_id) | 主键 | 日志唯一标识 |
| audit_log | IDX_audit_operator_time (operator, operation_time) | 联合索引 | 按操作人+时间查询 |
| audit_log | IDX_audit_module (module) | 普通索引 | 按模块筛选 |
| agent_run_log | PRIMARY KEY (run_id) | 主键 | 执行记录唯一标识 |
| agent_run_log | IDX_agent_flow (parent_flow_id) | 普通索引 | 按流程查询 |
| agent_run_log | IDX_agent_name_time (agent_name, created_at) | 联合索引 | 按 Agent+时间查询 |

### 11.2 考勤日志表分表策略

**背景**：考勤记录 `attendance_record` 为高频写入表（每 30 分钟全量同步），预计日均写入量 = 员工数 × 6 次/天 = 500 × 6 = 3,000 条/天，年增长约 100 万条。

**分表策略**：

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| 按月分表 | `attendance_record_202606` | 当前方案，按 YYYYMM 分表 |
| 查询路由 | 根据 date 字段自动路由到对应月表 | MyBatis 拦截器实现 |
| 历史归档 | 超过 2 年的数据归档至冷存储 | DataArchiveJob 每周执行 |

**分表实现：**

```java
// MyBatis 拦截器自动路由到对应月表
@Intercepts({@Signature(type = StatementHandler.class, method = "prepare", 
    args = {Connection.class, Integer.class})})
public class TableShardingInterceptor implements Interceptor {
    
    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        BoundSql boundSql = getBoundSql(invocation);
        String sql = boundSql.getSql();
        
        // 解析 SQL 中的日期条件
        String dateCondition = extractDateCondition(sql);
        if (dateCondition != null) {
            String yearMonth = extractYearMonth(dateCondition); // 如 "202606"
            String originalTable = "attendance_record";
            String shardedTable = "attendance_record_" + yearMonth;
            String newSql = sql.replace(originalTable, shardedTable);
            rewriteSql(boundSql, newSql);
        }
        
        return invocation.proceed();
    }
}
```

**分表生命周期管理：**

| 阶段 | 操作 | 时机 |
|------|------|------|
| 创建新表 | 每月 25 日自动创建下月表 | DataArchiveJob |
| 数据写入 | 当月数据写入当月表 | 实时 |
| 历史查询 | 跨月查询合并多表结果 | 应用层 UNION ALL |
| 归档 | 超过 2 年的表导出为 Parquet 至 MinIO | 每季度执行 |
| 清理 | 归档后删除原表 | 归档确认后进行 |

### 11.3 数据库连接池配置

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 50
      minimum-idle: 10
      connection-timeout: 30000      # 30 秒
      idle-timeout: 600000           # 10 分钟
      max-lifetime: 1800000          # 30 分钟
      leak-detection-threshold: 60000 # 60 秒（检测连接泄漏）
```

---

## 12. 部署架构

### 12.1 Docker 容器化方案

**容器组成：**

| 容器 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| gbm-hr-app | gbm/hr-app:latest | 8080 | Java 主应用 |
| gbm-hr-rpa | gbm/hr-rpa:latest | 8090 | RPA Python 子服务 |
| mysql | mysql:8.0 | 3306 | 主数据库 |
| mysql-slave | mysql:8.0 | 3307 | 从数据库（读写分离） |
| redis | redis:7-alpine | 6379 | 缓存 + Stream |
| minio | minio/minio:latest | 9000 | 对象存储 |
| nacos | nacos/nacos-server:v2.x | 8848 | 配置中心 |
| xxl-job | xuxueli/xxl-job-admin:2.x | 8081 | 定时任务调度 |
| vault | hashicorp/vault:latest | 8200 | 密钥管理 |
| otel-collector | otel/opentelemetry-collector:latest | 4317 | 链路追踪收集 |
| jaeger | jaegertracing/all-in-one:latest | 16686 | 链路追踪存储 |
| prometheus | prom/prometheus:latest | 9090 | 指标采集 |
| grafana | grafana/grafana:latest | 3000 | 可视化 |
| nginx | nginx:alpine | 80/443 | 反向代理 |

**docker-compose.yml 核心结构：**

```yaml
version: '3.8'
services:
  gbm-hr-app:
    image: gbm/hr-app:${APP_VERSION}
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - VAULT_ADDR=http://vault:8200
      - NACOS_SERVER_ADDR=nacos:8848
      - XXL_JOB_ADMIN_ADDRESSES=http://xxl-job:8081/xxl-job-admin
    depends_on:
      - mysql
      - redis
      - nacos
      - vault
      - xxl-job
    networks:
      - gbm-hr-net

  gbm-hr-rpa:
    image: gbm/hr-rpa:${RPA_VERSION}
    ports:
      - "8090:8090"
    environment:
      - REDIS_URL=redis://redis:6379
    networks:
      - gbm-hr-net

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=gbm_hr
    volumes:
      - mysql-data:/var/lib/mysql
      - ./init:/docker-entrypoint-initdb.d
    networks:
      - gbm-hr-net

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - gbm-hr-net

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
    volumes:
      - minio-data:/data
    networks:
      - gbm-hr-net

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - gbm-hr-app
    networks:
      - gbm-hr-net

volumes:
  mysql-data:
  redis-data:
  minio-data:

networks:
  gbm-hr-net:
    driver: bridge
```

### 12.2 Nginx 网关配置

```nginx
upstream gbm-hr-app {
    server gbm-hr-app:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name hr.gbm.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # API 请求转发
    location /api/ {
        proxy_pass http://gbm-hr-app/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 120s;    # RPA 操作可能耗时较长
        proxy_send_timeout 60s;
        
        # 请求体大小限制
        client_max_body_size 50m;   # 简历导入最大 50MB
    }
    
    # WebSocket 支持 (Dashboard 实时推送)
    location /ws/ {
        proxy_pass http://gbm-hr-app/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;  # WebSocket 长连接
    }
    
    # 静态资源 (前端)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
}

# HTTP 强制跳转 HTTPS
server {
    listen 80;
    server_name hr.gbm.com;
    return 301 https://$server_name$request_uri;
}
```

### 12.3 多环境策略

| 配置项 | dev (开发) | test (测试) | prod (生产) |
|--------|-----------|------------|------------|
| 数据库 | 单机 MySQL | 单机 MySQL | 主从 MySQL |
| Redis | 单机 | 单机 | Redis Sentinel |
| Nacos | 单机 | 单机 | 集群 (3 节点) |
| XXL-JOB | 单机 | 单机 | 单机（调度中心） |
| Vault | Dev 模式 (无需初始化) | 密封模式 | 高可用模式 (Raft) |
| MinIO | 单机 | 单机 | 分布式 (4 节点) |
| 日志级别 | DEBUG | INFO | WARN |
| OpenTelemetry 采样 | 100% | 100% | 按层级采样（见 1.1.1） |
| 前端资源 | 本地构建 | CI 构建 | CI 构建 + CDN |
| 域名 | localhost | test.gbm.com | hr.gbm.com |
| TLS | 自签名证书 | 自签名证书 | Let's Encrypt / 商业证书 |

**环境变量管理：**
- 每个环境独立的 `.env` 文件
- 敏感配置（数据库密码、Redis 密码、Vault Root Token）不入库，由部署时注入
- Nacos 配置中心按环境隔离命名空间（dev/test/prod）

---

*文档结束*
