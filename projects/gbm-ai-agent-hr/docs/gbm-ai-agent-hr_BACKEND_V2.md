# GBM AI Agent HR 智能人力管理系统 —— 后端设计文档 (V2)

## 版本信息

| 版本号 | 日期 | 作者 | 说明 |
|--------|------|------|------|
| 2.0 | 2026-06-12 | 后旺 | 基于 SRS V15 纯净版重新设计：修复后端架构完整性、API 接口完整性、安全策略细节、Agent 编排与通信机制、降级模式后端实现 |

---

## 1. 后端技术栈

### 1.1 核心技术选型

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| 主框架 | Spring Boot | 3.2+ | 成熟稳定、自动配置、生态完善 |
| 语言 | Java | 17+ | LTS 版本、性能稳定、类型安全 |
| 构建工具 | Maven | 3.9+ | 依赖管理、多模块项目支持 |
| ORM | MyBatis-Plus | 3.5+ | 灵活 SQL 控制、代码生成器、分页插件 |
| 认证授权 | Spring Security + JWT | 6.x | 标准认证框架、JWT 无状态认证 |
| API 文档 | SpringDoc OpenAPI 3 | 2.x | 自动生成 OpenAPI 3 规范文档 |
| 消息队列 | Spring AMQP (RabbitMQ) | 最新版 | Agent 间事件驱动通信 |
| 工作流引擎 | Camunda 7 | 7.20+ | BPMN 2.0 流程编排、可视化设计器 |
| 配置中心 | Nacos | 2.x | 配置热更新、服务发现、命名空间隔离 |
| 缓存 | Spring Data Redis | 最新版 | Redis 模板、序列化、分布式锁 |
| 对象存储 | MinIO Java SDK | 最新版 | S3 兼容接口、文件管理 |
| RPA 引擎 | Playwright (Java 绑定) | 最新版 | 浏览器自动化、多浏览器支持 |
| OCR | PaddleOCR (Python 服务) | 最新版 | 通过 HTTP 接口调用 |
| 人脸 | ArcFace (Python 服务) | 最新版 | 通过 HTTP 接口调用 |
| PDF 生成 | Apache PDFBox | 2.x | 证明文件 PDF 生成 |
| Excel 处理 | Apache POI | 5.x | 薪资/考勤数据导出 |
| 测试 | JUnit 5 + Mockito | 5.x | 单元测试、Mock |
| 链路追踪 | Spring Cloud Sleuth + Zipkin | — | 全链路追踪 |

### 1.2 多模块项目结构

```
gbm-hr-backend/
├── pom.xml                          # 父 POM (统一版本管理)
├── gbm-hr-common/                   # 公共模块
│   ├── src/main/java/
│   │   ├── model/                    # 通用实体/DTO
│   │   │   ├── BaseEntity.java       # 基础实体 (id/createdAt/updatedAt)
│   │   │   ├── ApiResponse.java      # 统一 API 响应
│   │   │   ├── PageRequest.java      # 分页请求
│   │   │   └── PageResponse.java     # 分页响应
│   │   ├── enums/                    # 通用枚举
│   │   │   ├── EmployeeStatus.java
│   │   │   ├── AgentStatus.java
│   │   │   └── AuditOperationType.java
│   │   ├── exception/                # 异常定义
│   │   │   ├── BusinessException.java
│   │   │   ├── GlobalExceptionHandler.java
│   │   │   └── ErrorCode.java
│   │   ├── util/                     # 工具类
│   │   │   ├── DateUtil.java
│   │   │   ├── EncryptUtil.java      # AES-256 加密
│   │   │   ├── IdGenerator.java      # 工号/ID 生成
│   │   │   └── ValidationUtil.java
│   │   ├── config/                   # 通用配置
│   │   │   ├── JacksonConfig.java
│   │   │   └── RedisConfig.java
│   │   └── constant/                 # 常量
│   │       ├── CacheConstant.java
│   │       └── MessageConstant.java
│   └── pom.xml
├── gbm-hr-gateway/                  # API 网关模块
│   ├── src/main/java/
│   │   ├── config/
│   │   │   ├── GatewayConfig.java
│   │   │   ├── CorsConfig.java
│   │   │   └── RateLimitConfig.java
│   │   ├── filter/
│   │   │   ├── AuthFilter.java       # 认证过滤器
│   │   │   ├── RateLimitFilter.java  # 限流过滤器
│   │   │   └── LoggingFilter.java    # 请求日志过滤器
│   │   └── route/
│   │       └── RouteConfig.java      # 路由配置
│   └── pom.xml
├── gbm-hr-auth/                     # 认证服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   └── AuthController.java
│   │   ├── service/
│   │   │   ├── AuthService.java
│   │   │   ├── MfaService.java
│   │   │   └── PermissionService.java
│   │   ├── repository/
│   │   │   ├── UserRepository.java
│   │   │   └── RoleRepository.java
│   │   ├── model/
│   │   │   ├── User.java
│   │   │   ├── Role.java
│   │   │   └── Permission.java
│   │   └── config/
│   │       ├── SecurityConfig.java
│   │       └── JwtConfig.java
│   └── pom.xml
├── gbm-hr-recruitment/              # 招聘服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   ├── JobPostController.java
│   │   │   ├── ResumeController.java
│   │   │   ├── ExamController.java
│   │   │   └── TalentPoolController.java
│   │   ├── service/
│   │   │   ├── JobPostService.java
│   │   │   ├── ResumeService.java
│   │   │   ├── ResumeScoringService.java
│   │   │   ├── ExamService.java
│   │   │   └── TalentPoolService.java
│   │   ├── agent/
│   │   │   ├── RecruitmentChannelAgent.java
│   │   │   ├── ResumeMatchAgent.java
│   │   │   ├── ExamPaperAgent.java
│   │   │   └── GradingAgent.java
│   │   ├── repository/
│   │   │   ├── JobPostRepository.java
│   │   │   ├── ResumeRepository.java
│   │   │   └── ExamPaperRepository.java
│   │   └── model/
│   │       ├── JobPost.java
│   │       ├── Resume.java
│   │       ├── ExamPaper.java
│   │       └── ScoreRecord.java
│   └── pom.xml
├── gbm-hr-onboarding/               # 入职服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   └── OnboardingController.java
│   │   ├── service/
│   │   │   ├── OnboardingService.java
│   │   │   ├── OcrService.java
│   │   │   └── FaceService.java
│   │   ├── agent/
│   │   │   ├── OnboardingGuideAgent.java
│   │   │   ├── OcrAgent.java
│   │   │   └── FaceAgent.java
│   │   └── repository/
│   │       └── OnboardingRepository.java
│   └── pom.xml
├── gbm-hr-training/                 # 培训服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   ├── TrainingPlanController.java
│   │   │   ├── CheckInController.java
│   │   │   ├── TrainingExamController.java
│   │   │   └── AuditPackageController.java
│   │   ├── service/
│   │   │   ├── TrainingPlanService.java
│   │   │   ├── CheckInService.java
│   │   │   └── AuditPackageService.java
│   │   ├── agent/
│   │   │   ├── TrainingAgent.java
│   │   │   ├── VideoConversionAgent.java
│   │   │   └── AuditMaterialAgent.java
│   │   └── repository/
│   │       └── TrainingRepository.java
│   └── pom.xml
├── gbm-hr-attendance/               # 考勤服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   ├── AttendanceController.java
│   │   │   └── AnomalyController.java
│   │   ├── service/
│   │   │   ├── AttendanceService.java
│   │   │   └── AnomalyDetectionService.java
│   │   ├── agent/
│   │   │   └── AttendanceAgent.java
│   │   └── repository/
│   │       └── AttendanceRepository.java
│   └── pom.xml
├── gbm-hr-payroll/                  # 薪资服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   ├── PayrollController.java
│   │   │   ├── PayslipController.java
│   │   │   └── PayrollConfigController.java
│   │   ├── service/
│   │   │   ├── PayrollCalculationService.java
│   │   │   ├── TaxCalculationService.java
│   │   │   ├── SocialSecurityService.java
│   │   │   └── PayslipDeliveryService.java
│   │   ├── agent/
│   │   │   ├── PayrollAgent.java
│   │   │   └── PayslipAgent.java
│   │   └── repository/
│   │       └── PayrollRepository.java
│   └── pom.xml
├── gbm-hr-performance/              # 绩效服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   └── PerformanceController.java
│   │   ├── service/
│   │   │   └── PerformanceService.java
│   │   ├── agent/
│   │   │   └── PerformanceAgent.java
│   │   └── repository/
│   │       └── PerformanceRepository.java
│   └── pom.xml
├── gbm-hr-external/                 # 外务服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   ├── InjuryCaseController.java
│   │   │   └── HousingFundController.java
│   │   ├── service/
│   │   │   ├── InjuryCaseService.java
│   │   │   └── HousingFundService.java
│   │   ├── agent/
│   │   │   ├── ExternalAgent.java
│   │   │   └── RpaAgent.java
│   │   ├── rpa/
│   │   │   ├── SocialSecurityRpa.java
│   │   │   └── HousingFundRpa.java
│   │   └── repository/
│   │       └── ExternalRepository.java
│   └── pom.xml
├── gbm-hr-resignation/              # 离职服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   └── ResignationController.java
│   │   ├── service/
│   │   │   └── ResignationService.java
│   │   ├── agent/
│   │   │   └── ResignationAgent.java
│   │   └── repository/
│   │       └── ResignationRepository.java
│   └── pom.xml
├── gbm-hr-certificate/              # 证明服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   └── CertificateController.java
│   │   ├── service/
│   │   │   └── CertificateService.java
│   │   ├── agent/
│   │   │   └── CertificateAgent.java
│   │   └── repository/
│   │       └── CertificateRepository.java
│   └── pom.xml
├── gbm-hr-admin/                    # 管理服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   ├── UserController.java
│   │   │   ├── RoleController.java
│   │   │   ├── AgentMonitorController.java
│   │   │   ├── AuditLogController.java
│   │   │   ├── SystemConfigController.java
│   │   │   └── AiCostController.java
│   │   ├── service/
│   │   │   ├── UserService.java
│   │   │   ├── AuditLogService.java
│   │   │   ├── AgentMonitorService.java
│   │   │   └── AiCostService.java
│   │   └── repository/
│   │       └── AdminRepository.java
│   └── pom.xml
├── gbm-hr-orchestration/            # Agent 编排服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   └── OrchestrationController.java
│   │   ├── service/
│   │   │   ├── FlowDefinitionService.java
│   │   │   ├── TaskSplitService.java
│   │   │   ├── RouterService.java
│   │   │   └── StateManagementService.java
│   │   ├── event/
│   │   │   ├── EventBus.java
│   │   │   ├── AgentEventListener.java
│   │   │   └── AgentEventPublisher.java
│   │   ├── model/
│   │   │   ├── FlowDefinition.java
│   │   │   ├── TaskNode.java
│   │   │   └── FlowState.java
│   │   └── repository/
│   │       └── OrchestrationRepository.java
│   └── pom.xml
├── gbm-hr-notification/             # 通知服务模块
│   ├── src/main/java/
│   │   ├── controller/
│   │   │   └── NotificationController.java
│   │   ├── service/
│   │   │   ├── EmailService.java
│   │   │   ├── SmsService.java
│   │   │   └── PushNotificationService.java
│   │   └── config/
│   │       └── MailConfig.java
│   └── pom.xml
└── gbm-hr-audit/                    # 审计服务模块
    ├── src/main/java/
    │   ├── aspect/
    │   │   └── AuditLogAspect.java   # AOP 审计日志切面
    │   ├── service/
    │   │   └── AuditService.java
    │   ├── model/
    │   │   └── AuditLog.java
    │   └── repository/
    │       └── AuditLogRepository.java
    └── pom.xml
```

---

## 2. API 接口列表

### 2.1 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2026-06-12T10:30:00Z",
  "traceId": "abc-123-def-456"
}
```

### 2.2 认证服务 API (gbm-hr-auth)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 | 公开 |
| POST | `/api/v1/auth/logout` | 用户登出 | 已认证 |
| POST | `/api/v1/auth/mfa/verify` | MFA 验证 | 已认证 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | 已认证 |
| POST | `/api/v1/auth/forgot-password` | 密码重置请求 | 公开 |
| POST | `/api/v1/auth/reset-password` | 密码重置执行 | 公开 (验证码) |
| GET | `/api/v1/auth/me` | 获取当前用户信息 | 已认证 |
| GET | `/api/v1/auth/roles` | 获取角色列表 | 管理员 |
| POST | `/api/v1/auth/roles` | 创建角色 | 管理员 |
| PUT | `/api/v1/auth/roles/{id}` | 更新角色 | 管理员 |
| DELETE | `/api/v1/auth/roles/{id}` | 删除角色 | 管理员 |
| GET | `/api/v1/auth/permissions` | 获取权限列表 | 管理员 |
| POST | `/api/v1/auth/qr-temp-auth` | 生成临时二维码授权 | 管理员 |

### 2.3 招聘服务 API (gbm-hr-recruitment)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/recruitment/job-posts` | 发布招聘信息 | 人事专员 |
| GET | `/api/v1/recruitment/job-posts` | 查询招聘信息列表 | 人事专员 |
| GET | `/api/v1/recruitment/job-posts/{id}` | 查询招聘信息详情 | 人事专员 |
| PUT | `/api/v1/recruitment/job-posts/{id}` | 更新招聘信息 | 人事专员 |
| DELETE | `/api/v1/recruitment/job-posts/{id}` | 下架招聘信息 | 人事专员 |
| POST | `/api/v1/recruitment/resumes/import` | 批量导入简历 | 人事专员 |
| GET | `/api/v1/recruitment/resumes` | 查询简历列表 (分页/筛选) | 人事专员 |
| GET | `/api/v1/recruitment/resumes/{id}` | 查询简历详情+评分 | 人事专员 |
| POST | `/api/v1/recruitment/resumes/{id}/rescore` | 重新评分 | 人事专员 |
| POST | `/api/v1/recruitment/resumes/nlp-search` | 自然语言搜索简历 | 人事专员 |
| GET | `/api/v1/recruitment/resumes/stats` | 简历统计 (高潜/候审/淘汰) | 人事专员 |
| POST | `/api/v1/recruitment/exams/generate` | Agent 生成试卷 | 人事专员 |
| GET | `/api/v1/recruitment/exams/{id}` | 查询试卷详情 | 人事专员 |
| POST | `/api/v1/recruitment/exams/{id}/publish` | 发布考试 | 人事专员 |
| GET | `/api/v1/recruitment/exams/{id}/take` | 获取考试答题界面数据 | 候选人 (QR 临时授权) |
| POST | `/api/v1/recruitment/exams/{id}/submit` | 提交答卷 | 候选人 (QR 临时授权) |
| GET | `/api/v1/recruitment/exams/{id}/scores` | 查询考试成绩 | 人事专员 |
| GET | `/api/v1/recruitment/exams/{id}/score/{candidateId}` | 查询个人成绩 | 候选人 |
| GET | `/api/v1/recruitment/talent-pool` | 查询人才库 | 人事专员 |
| POST | `/api/v1/recruitment/talent-pool/search` | 人才库搜索 | 人事专员 |
| GET | `/api/v1/recruitment/talent-pool/{id}` | 人才库详情 | 人事专员 |

### 2.4 入职服务 API (gbm-hr-onboarding)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/onboarding/{token}` | 获取入职引导信息 | 新员工 (Token) |
| POST | `/api/v1/onboarding/{token}/upload` | 上传证件材料 | 新员工 (Token) |
| GET | `/api/v1/onboarding/{token}/ocr-result` | 获取 OCR 识别结果 | 新员工 (Token) |
| POST | `/api/v1/onboarding/{token}/face-capture` | 人脸采集 | 新员工 (Token) |
| GET | `/api/v1/onboarding/{token}/agreements` | 获取待签署协议列表 | 新员工 (Token) |
| POST | `/api/v1/onboarding/{token}/sign` | 签署电子协议 | 新员工 (Token) |
| GET | `/api/v1/onboarding/{token}/progress` | 入职进度查询 | 新员工 (Token) |
| GET | `/api/v1/onboarding/list` | 入职办理列表 | 人事专员 |
| GET | `/api/v1/onboarding/{id}/archive` | 查看入职档案 | 人事专员 |

### 2.5 培训服务 API (gbm-hr-training)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/training/plans` | 创建培训计划 | 人事专员 |
| GET | `/api/v1/training/plans` | 查询培训计划列表 | 人事专员 |
| GET | `/api/v1/training/plans/{id}` | 查询培训计划详情 | 人事专员 |
| PUT | `/api/v1/training/plans/{id}` | 更新培训计划 | 人事专员 |
| POST | `/api/v1/training/checkin/{code}` | 扫码签到 | 受训员工 |
| GET | `/api/v1/training/checkin/{planId}` | 查询签到统计 | 人事专员 |
| GET | `/api/v1/training/exams/{id}` | 获取培训考试 | 受训员工 |
| POST | `/api/v1/training/exams/{id}/submit` | 提交培训答卷 | 受训员工 |
| GET | `/api/v1/training/exams/{id}/scores` | 查询培训成绩 | 人事专员 |
| GET | `/api/v1/training/videos/{id}` | 获取培训视频 | 在职员工 |
| POST | `/api/v1/training/videos/generate` | 教材转视频 | 人事专员 |
| GET | `/api/v1/training/certificates` | 查询个人证书 | 在职员工 |
| GET | `/api/v1/training/certificates/list` | 查询证书列表 | 人事专员 |
| POST | `/api/v1/training/audit-package/generate` | 生成体系审核资料包 | 人事专员 |
| GET | `/api/v1/training/audit-package/{id}` | 下载审核资料包 | 人事专员 |

### 2.6 考勤服务 API (gbm-hr-attendance)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/attendance/calendar` | 考勤日历视图 | 人事专员/主管 |
| GET | `/api/v1/attendance/summary` | 考勤汇总 (按部门/月份) | 人事专员 |
| GET | `/api/v1/attendance/employee/{id}` | 个人考勤记录 | 在职员工 (本人) |
| GET | `/api/v1/attendance/anomalies` | 考勤异常列表 | 人事专员 |
| GET | `/api/v1/attendance/anomaly-report` | 异常趋势分析报告 | 人事专员 |
| POST | `/api/v1/attendance/data/sync` | 同步打卡设备数据 | 系统 (定时触发) |
| POST | `/api/v1/attendance/export` | 导出考勤数据 | 人事专员 |

### 2.7 薪资服务 API (gbm-hr-payroll)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/payroll/config` | 查询薪资配置 | 人事专员 |
| PUT | `/api/v1/payroll/config` | 更新薪资配置 | 人事专员 |
| GET | `/api/v1/payroll/rules` | 查询薪资规则 | 人事专员 |
| PUT | `/api/v1/payroll/rules` | 更新薪资规则 | 人事专员 |
| POST | `/api/v1/payroll/calculate/{month}` | 触发月度薪资核算 | 人事专员/系统 |
| GET | `/api/v1/payroll/calculation/{month}` | 查询核算结果 | 人事专员 |
| POST | `/api/v1/payroll/review/{month}` | 审核确认薪资 | 人事专员 (MFA) |
| GET | `/api/v1/payroll/payslip` | 查看个人工资条 | 在职员工 (本人) |
| GET | `/api/v1/payroll/payslip/{month}/read-status` | 工资条阅读状态 | 人事专员 |
| POST | `/api/v1/payroll/export/{month}` | 导出薪资数据 | 人事主管/管理员 (MFA) |
| GET | `/api/v1/payroll/employee/{id}` | 查询个人薪资历史 | 在职员工 (本人) |

### 2.8 绩效服务 API (gbm-hr-performance)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/performance/cycles` | 查询考核周期列表 | 人事专员 |
| POST | `/api/v1/performance/self` | 提交绩效自评 | 在职员工 |
| GET | `/api/v1/performance/self` | 查询个人自评 | 在职员工 |
| POST | `/api/v1/performance/review` | 提交上级评审 | 部门主管 |
| GET | `/api/v1/performance/review/pending` | 待评审列表 | 部门主管 |
| GET | `/api/v1/performance/summary` | 绩效汇总报表 | 人事专员/主管 |
| GET | `/api/v1/performance/trend` | 绩效趋势分析 | 人事专员/主管 |
| POST | `/api/v1/performance/export` | 导出绩效数据 | 人事专员 |

### 2.9 外务服务 API (gbm-hr-external)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/external/injury/cases` | 创建工伤案件 | 外务专员 |
| GET | `/api/v1/external/injury/cases` | 查询工伤案件列表 | 外务专员 |
| GET | `/api/v1/external/injury/cases/{id}` | 查询工伤案件详情 | 外务专员 |
| POST | `/api/v1/external/injury/cases/{id}/file` | RPA 申报工伤 | 外务专员 (MFA) |
| GET | `/api/v1/external/injury/cases/{id}/progress` | 查询理赔进度 | 外务专员 |
| POST | `/api/v1/external/housing-fund/enroll` | RPA 公积金参保 | 外务专员 (MFA) |
| POST | `/api/v1/external/housing-fund/withdraw` | RPA 公积金封存 | 外务专员 (MFA) |
| POST | `/api/v1/external/housing-fund/repayment` | RPA 公积金补缴 | 外务专员 (MFA) |
| GET | `/api/v1/external/housing-fund/records` | 查询公积金记录 | 外务专员 |

### 2.10 离职服务 API (gbm-hr-resignation)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/resignation/apply` | 提交离职申请 | 在职员工 |
| GET | `/api/v1/resignation/apply` | 查询离职申请状态 | 在职员工 |
| GET | `/api/v1/resignation/pending` | 待审批离职列表 | 部门主管/人事 |
| POST | `/api/v1/resignation/{id}/approve` | 审批离职申请 | 部门主管/人事 |
| GET | `/api/v1/resignation/{id}/handover` | 查询交接清单 | 相关部门 |
| POST | `/api/v1/resignation/{id}/handover/confirm` | 确认交接完成 | 相关部门 |
| GET | `/api/v1/resignation/{id}/certificate` | 查看离职证明 | 离职员工 |

### 2.11 证明服务 API (gbm-hr-certificate)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/certificate/apply` | 申请人事证明 | 在职员工 |
| GET | `/api/v1/certificate/apply/{id}` | 查询证明申请状态 | 在职员工 |
| GET | `/api/v1/certificate/pending` | 待审核证明列表 | 人事专员 |
| POST | `/api/v1/certificate/{id}/approve` | 审核通过证明 | 人事专员 |
| GET | `/api/v1/certificate/{id}/download` | 下载证明文件 | 在职员工 |
| GET | `/api/v1/certificate/history` | 证明申请历史 | 在职员工 |

### 2.12 管理服务 API (gbm-hr-admin)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/admin/users` | 查询用户列表 | 管理员 |
| POST | `/api/v1/admin/users` | 创建用户 | 管理员 |
| PUT | `/api/v1/admin/users/{id}` | 更新用户 | 管理员 |
| DELETE | `/api/v1/admin/users/{id}` | 禁用用户 | 管理员 |
| GET | `/api/v1/admin/agents/status` | 查询 Agent 运行状态 | 管理员 |
| POST | `/api/v1/admin/agents/{name}/trigger` | 手动触发 Agent | 管理员 |
| GET | `/api/v1/admin/agents/{name}/config` | 查询 Agent 配置 | 管理员 |
| PUT | `/api/v1/admin/agents/{name}/config` | 更新 Agent 配置 | 管理员 |
| GET | `/api/v1/admin/agents/{name}/logs` | 查询 Agent 执行日志 | 管理员 |
| GET | `/api/v1/admin/audit-logs` | 查询审计日志 | 管理员 |
| GET | `/api/v1/admin/config` | 查询系统配置 | 管理员 |
| PUT | `/api/v1/admin/config` | 更新系统配置 | 管理员 |
| GET | `/api/v1/admin/ai-cost/report` | AI 费用报表 | 管理员 |

### 2.13 通知服务 API (gbm-hr-notification)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/notifications` | 查询通知列表 | 已认证 |
| PUT | `/api/v1/notifications/{id}/read` | 标记通知已读 | 已认证 |
| DELETE | `/api/v1/notifications/{id}` | 删除通知 | 已认证 |
| POST | `/api/v1/notifications/send` | 发送通知 (内部调用) | 系统 |

---

## 3. 数据流设计

### 3.1 简历筛选数据流

```
[招聘平台 API] ──→ [定时任务 (每15分钟)] ──→ [招聘渠道 Agent]
                                                      │
                                                      ▼
                                              [简历去重服务]
                                                      │
                                                      ▼
                                              [简历匹配 Agent]
                                             ┌────────┴────────┐
                                             │                 │
                                    多维度评分计算        LLM 语义匹配
                                             │                 │
                                             └────────┬────────┘
                                                      │
                                                      ▼
                                              [分拣规则引擎]
                                           ┌─────────┼──────────┐
                                           │         │          │
                                      [高潜简历]  [候审简历]  [淘汰简历]
                                           │         │          │
                                           ▼         ▼          ▼
                                     自动入库  推送审核  自动打标签
                                           │         │
                                           ▼         ▼
                                      [简历库 ES 索引]  [通知中心]
```

### 3.2 薪资核算数据流

```
[月末触发] ──→ [薪资 Agent]
                   │
          ┌────────┼────────┬────────┐
          ▼        ▼        ▼        ▼
    [考勤服务] [薪资主数据] [社保数据库] [个税规则库]
          │        │        │        │
          └────────┼────────┼────────┘
                   ▼
          [薪资核算引擎]
         ┌─────────┴──────────┐
         │ 应发工资计算        │
         │ 加班费计算 (1.5x/2x/3x)│
         │ 考勤扣款计算        │
         │ 社保扣除计算        │
         │ 公积金扣除计算      │
         │ 个税计算 (七级累进) │
         │ 实发工资计算        │
         └──────────┬─────────┘
                    ▼
          [异常检测引擎]
         ┌─────────┴──────────┐
         │ 波动>±20% 标记     │
         │ 个税负数 标记      │
         │ 社保=0 但在职 标记 │
         │ 低于最低薪资 标记  │
         │ 加班费突增 标记    │
         └──────────┬─────────┘
                    ▼
          [生成核算报告] ──→ [推送人事专员审核]
                                    │
                           [人事专员确认]
                                    │
                                    ▼
                           [工资条 Agent] ──→ [批量推送工资条]
```

### 3.3 工伤 RPA 数据流

```
[工伤事件触发] ──→ [工伤 Agent]
                       │
                       ▼
              [生成情况说明模板] ──→ [推送员工填写]
                       │
                       ▼
              [材料清单检查] ──→ [逐项校验完整性]
                       │
                       ▼
              [打包备案文档] ──→ [RPA Agent]
                                     │
                            ┌────────┴────────┐
                            │ 有官方 API      │ 无官方 API
                            ▼                 ▼
                      [API 提交申报]    [Playwright RPA]
                            │            登录→填表→提交→截图
                            │                 │
                            └────────┬────────┘
                                     ▼
                          [捕获申报回执]
                                     │
                                     ▼
                          [跟踪理赔进度] ──→ [定期查询]
                                     │
                                     ▼
                          [理赔到账记录] ──→ [关联保单]
```

---

## 4. 中间件设计

### 4.1 消息队列 (RabbitMQ)

#### 4.1.1 队列定义

| 队列名称 | 用途 | 消费者 |
|---------|------|--------|
| `agent.recruitment.resume` | 新简历进入评分队列 | 简历匹配 Agent |
| `agent.recruitment.exam-submit` | 答卷提交阅卷队列 | 阅卷 Agent |
| `agent.onboarding.document` | 证件上传 OCR 队列 | OCR Agent |
| `agent.onboarding.face` | 人脸采集处理队列 | 人脸 Agent |
| `agent.attendance.sync` | 打卡数据同步队列 | 考勤 Agent |
| `agent.payroll.calculate` | 薪资核算触发队列 | 薪资 Agent |
| `agent.payroll.payslip` | 工资条发放队列 | 工资条 Agent |
| `agent.training.checkin` | 签到记录队列 | 培训 Agent |
| `agent.external.rpa` | RPA 任务队列 | RPA Agent |
| `agent.notification` | 通知推送队列 | 通知服务 |
| `agent.audit-log` | 审计日志异步写入队列 | 审计服务 |

#### 4.1.2 消息格式

```json
{
  "messageId": "uuid-v4",
  "traceId": "trace-uuid",
  "eventType": "agent.recruitment.resume",
  "priority": "HIGH",        // HIGH / NORMAL / LOW
  "ttl": 3600000,            // 1 小时过期
  "retryCount": 0,
  "maxRetries": 3,
  "timestamp": "2026-06-12T10:30:00Z",
  "payload": {
    "resumeId": "R-20260612-001",
    "jobPostId": "JP-001",
    "sourcePlatform": "前程无忧"
  }
}
```

#### 4.1.3 消息确认策略

- 手动确认 (Manual Ack)：消费者处理成功后显式确认
- 死信队列 (DLQ)：超过最大重试次数的消息进入死信队列
- 告警机制：死信队列消息触发告警通知

### 4.2 缓存 (Redis)

#### 4.2.1 缓存策略

| 缓存键模式 | 用途 | TTL | 淘汰策略 |
|-----------|------|-----|---------|
| `auth:token:{userId}` | JWT Token 缓存 | 24h | volatile-lru |
| `auth:refresh:{userId}` | 刷新 Token | 7d | volatile-lru |
| `user:profile:{userId}` | 用户信息缓存 | 30min | volatile-lru |
| `recruitment:resume:score:{resumeId}` | 简历评分结果 | 24h | volatile-lru |
| `recruitment:exam:paper:{examId}` | 试卷缓存 | 考试期间 | no-eviction |
| `attendance:clock:{employeeId}:{date}` | 当日打卡记录 | 24h | volatile-lru |
| `payroll:calc:{month}` | 当月薪资核算结果 | 核算期间 | no-eviction |
| `agent:lock:{agentName}` | Agent 分布式锁 | 5min | volatile-lru |
| `agent:status:{agentName}` | Agent 运行状态 | 1min | volatile-lru |
| `config:payroll:rules` | 薪资规则缓存 | 热更新 | no-eviction |
| `config:attendance:rules` | 考勤规则缓存 | 热更新 | no-eviction |
| `config:scoring:weights` | 筛选权重缓存 | 热更新 | no-eviction |
| `rate:limit:{ip}:{endpoint}` | 接口限流计数器 | 1min | volatile-lru |
| `session:mfa:{userId}` | MFA 验证状态 | 10min | volatile-lru |

### 4.3 工作流引擎 (Camunda 7)

#### 4.3.1 定义的工作流

| 流程 ID | 流程名称 | 触发条件 | 步骤数 |
|--------|---------|---------|--------|
| `onboarding-flow` | 入职办理流程 | 新员工扫码进入 | 8 步 |
| `resignation-flow` | 离职办理流程 | 员工提交离职申请 | 12 步 |
| `payroll-flow` | 薪资核算流程 | 每月指定日期 | 10 步 |
| `injury-flow` | 工伤处理流程 | 工伤事件触发 | 10 步 |
| `housing-fund-flow` | 公积金操作流程 | 员工入职/离职 | 6 步 |
| `training-flow` | 培训全流程 | 培训计划启动 | 9 步 |
| `certificate-flow` | 证明签发流程 | 员工提交申请 | 5 步 |
| `performance-flow` | 绩效考核流程 | 考核周期开始 | 8 步 |

#### 4.3.2 工作流状态机

```
PENDING → RUNNING → COMPLETED
                ↘ ERROR → RETRY → RUNNING
                ↘ SUSPENDED → RESUMED → RUNNING
                ↘ CANCELLED
```

### 4.4 配置中心 (Nacos)

#### 4.4.1 配置分组

| 分组 | 配置项 | 更新频率 |
|------|--------|---------|
| `recruitment` | 筛选权重阈值、合格线、评分模型版本 | 按需 |
| `payroll` | 加班系数、迟到扣款标准、社保比例、个税免征额 | 按月/政策变更 |
| `attendance` | 班次定义、迟到/早退时间阈值、加班上限 | 按需 |
| `scoring` | 简历评分各维度权重、语义匹配模型版本 | 按季度 |
| `rpa` | 政府网站 URL、RPA 凭证 (加密)、超时设置 | 按需 |
| `notification` | 邮件模板、短信模板、推送频率 | 按需 |
| `guardrails` | 安全护栏阈值 (金额上限、操作频率) | 按需 |

---

## 5. 安全策略

### 5.1 认证与授权

#### 5.1.1 JWT Token 设计

```
Header:
{
  "alg": "RS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "user-001",
  "name": "张三",
  "roles": ["HR_SPECIALIST"],
  "deptId": "DEPT-001",
  "permissions": ["recruitment:read", "recruitment:write"],
  "iat": 1718188200,
  "exp": 1718274600,       // 24 小时有效期
  "jti": "uuid-token-id"
}
```

#### 5.1.2 MFA 触发场景

| 场景 | MFA 方式 | 实现 |
|------|---------|------|
| 管理员首次登录 | 短信验证码 / Authenticator APP | 登录后跳转 MFA 验证页 |
| 访问薪资数据 | 短信验证码 | API 请求检查 MFA 状态 |
| 公积金/社保操作 | 短信验证码 | RPA 操作前验证 |
| 大批量数据导出 | 短信验证码 | 导出请求检查 MFA |
| 密码重置 | 邮箱验证码 | 重置流程中验证 |

#### 5.1.3 RBAC 权限矩阵

| 角色 | 招聘 | 入职 | 培训 | 考勤 | 薪资 | 绩效 | 外务 | 离职 | 证明 | 管理 |
|------|------|------|------|------|------|------|------|------|------|------|
| 系统管理员 | R | R | R | R | R | R | R | R | R | RW |
| 人事专员 | RW | RW | RW | RW | RW | RW | R | RW | RW | — |
| 部门主管 | R | — | R | R | — | RW | — | R | — | — |
| 外务专员 | — | — | — | — | — | — | RW | — | — | — |
| 在职员工 | — | R | RW | R | R | RW | — | RW | RW | — |
| 新员工 | — | RW | — | — | — | — | — | — | — | — |

### 5.2 数据加密

| 数据类型 | 加密算法 | 存储位置 |
|---------|---------|---------|
| 身份证号 | AES-256-GCM | MySQL (加密字段) |
| 人脸特征 | AES-256-GCM | 人脸库 |
| 薪资数据 | AES-256-GCM | MySQL (加密字段) |
| 公积金账号 | AES-256-GCM | MySQL (加密字段) |
| API 密钥 | AES-256-GCM | Nacos (加密配置) |
| 传输数据 | TLS 1.2+ | 网络层 |

#### 5.2.1 密钥管理

```
密钥保管方案:
1. 主密钥 (Master Key) 存储在硬件安全模块 (HSM) 或云 KMS
2. 数据密钥 (Data Key) 由主密钥加密后存储在配置中心
3. 密钥轮换周期: 主密钥每年轮换，数据密钥每季度轮换
4. 密钥访问: 仅授权服务可通过 KMS API 获取解密后的密钥
```

### 5.3 审计日志

#### 5.3.1 AOP 切面实现

```java
@Aspect
@Component
public class AuditLogAspect {

    @Around("@annotation(AuditLog)")
    public Object auditLog(ProceedingJoinPoint pjp, AuditLog annotation) throws Throwable {
        // 1. 记录操作前快照
        // 2. 执行目标方法
        // 3. 记录操作后快照
        // 4. 异步发送审计日志到消息队列
        // 5. 审计日志写入专用表 (不可修改/删除)
    }
}
```

#### 5.3.2 审计日志字段

| 字段 | 类型 | 说明 |
|------|------|------|
| 操作时间 | TIMESTAMP | 精确到秒 |
| 操作人 | VARCHAR(50) | 账号 + 真实姓名 |
| 操作者 IP | VARCHAR(45) | IPv4/IPv6 |
| 操作类型 | VARCHAR(20) | 新增/修改/删除/查看/导出/登录/Auto-Agent |
| 操作模块 | VARCHAR(20) | 招聘/入职/培训/考勤/薪资/绩效/外务/离职 |
| 操作对象 | VARCHAR(100) | 对象 ID 及名称 |
| 变更前快照 | JSON | JSON 格式 |
| 变更后快照 | JSON | JSON 格式 |
| 结果 | VARCHAR(10) | 成功/失败 |
| 耗时 (ms) | BIGINT | 精确到毫秒 |

### 5.4 Agent 安全护栏实现

#### 5.4.1 护栏拦截器

```java
@Component
public class AgentGuardrailsInterceptor implements ApplicationListener<AgentExecuteEvent> {

    @Override
    public void onApplicationEvent(AgentExecuteEvent event) {
        // 金额操作护栏: 检查是否涉及金额变动，需人事专员审批
        if (event.isAmountChange() && !event.isApproved()) {
            throw new GuardrailsViolationException("金额操作需人事专员审核批准");
        }
        // 对外通讯护栏: 检查是否对外发送内容，需预审
        if (event.isExternalCommunication() && !event.isPreReviewed()) {
            throw new GuardrailsViolationException("对外通讯需预审确认");
        }
        // 数据删除护栏: 检查是否删除已归档数据
        if (event.isArchiveDelete()) {
            throw new GuardrailsViolationException("已归档数据只能移动归档位，删除需二次审批");
        }
        // 模型推理护栏: 检查输出合理性
        if (event.getOutput() != null) {
            validateOutputReasonableness(event.getOutput());
        }
    }
}
```

### 5.5 接口限流与熔断

#### 5.5.1 限流策略

| 接口类别 | 限流规则 | 实现 |
|---------|---------|------|
| 认证接口 | 10 次/分钟/IP | Redis 计数器 |
| 简历导入 | 5 并发/用户 | 信号量 |
| OCR 识别 | 30 次/分钟 | Token Bucket |
| RPA 操作 | 10 次/小时 | 滑动窗口 |
| 薪资导出 | 5 次/天/用户 | Redis 计数器 |
| 普通 API | 100 次/分钟/IP | Nginx 限流 |

#### 5.5.2 熔断策略 (Resilience4j)

| 服务 | 熔断条件 | 恢复策略 |
|------|---------|---------|
| 招聘平台 API | 连续 3 次失败 | 暂停 1 小时后自动恢复 |
| 社保系统 API | 连续 2 次失败 | 暂停 30 分钟后恢复 |
| OCR 服务 | 连续 5 次失败 | 降级为人工录入模式 |
| LLM API | 连续 3 次超时 (>30s) | 降级为规则引擎模式 |
| RPA 目标网站 | 失败率 > 5% | 暂停 RPA 并告警 |

---

## 6. Agent 编排与通信

### 6.1 Agent 执行模型

```
Agent 执行生命周期:

1. 事件触发 → 2. 编排层接收 → 3. 任务分解 → 4. Agent 调度
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              [Pipeline 模式]      [Fan-Out 模式]      [Decision 模式]
              顺序执行             并行获取数据         条件分支
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                         ▼
                                  5. Agent 执行
                                         │
                                  ┌──────┴──────┐
                                  ▼             ▼
                             [成功]         [失败]
                                  │             │
                                  ▼             ▼
                             6. 结果汇聚   重试/挂起/告警
                                  │
                                  ▼
                             7. 状态持久化
                                  │
                                  ▼
                             8. 触发下一步或完成
```

### 6.2 Agent 执行日志

每个 Agent 执行记录写入 `agent_run_log` 表:

| 字段 | 说明 |
|------|------|
| run_id | UUID 执行流水号 |
| agent_name | Agent 名称 |
| parent_flow_id | 所属业务流程 ID |
| inputs_summary | 输入概要 (JSON) |
| reasoning_trace | 推理过程摘要 |
| outputs_summary | 输出概要 (JSON) |
| status | 成功/失败/挂起 |
| duration_ms | 耗时 (毫秒) |
| error_detail | 错误堆栈 (如有) |
| created_at | 执行时间 |

### 6.3 断点恢复机制

```java
public class StateManagementService {

    // Agent 崩溃后断点恢复
    public FlowState resumeFromCheckpoint(String flowId) {
        // 1. 从流程状态仓库加载最后持久化的状态
        FlowState state = flowStateRepository.findByFlowId(flowId);
        // 2. 确定当前失败的节点
        TaskNode failedNode = state.getFailedNode();
        // 3. 从失败节点重新开始执行
        return executeFromNode(flowId, failedNode);
    }

    // 操作前自动生成状态快照 (支持 30 秒内回退)
    public StateSnapshot createSnapshot(String flowId) {
        StateSnapshot snapshot = new StateSnapshot();
        snapshot.setFlowId(flowId);
        snapshot.setStateJson(stateSerializer.serialize(currentState));
        snapshot.setCreatedAt(Instant.now());
        snapshotRepository.save(snapshot);
        return snapshot;
    }
}
```

---

## 7. 降级模式后端实现

### 7.1 降级检测与切换

```java
@Component
public class DegradationManager {

    @Autowired
    private HealthCheckService healthCheck;

    public void checkAndDegrade() {
        // LLM 不可用 → 切换为关键词匹配模式
        if (!healthCheck.isLlmAvailable()) {
            scoringStrategy.setMode(ScoringMode.KEYWORD_MATCH);
            alertService.sendDegradationAlert("LLM 不可用，简历筛选切换为关键词匹配模式");
        }
        // OCR 不可用 → 切换为人工录入模式
        if (!healthCheck.isOcrAvailable()) {
            onboardingService.enableManualEntry();
            alertService.sendDegradationAlert("OCR 不可用，证件信息切换为人工录入模式");
        }
        // 人脸不可用 → 切换为身份证+手机验证码
        if (!healthCheck.isFaceServiceAvailable()) {
            authService.enableFallbackVerification();
            alertService.sendDegradationAlert("人脸不可用，身份校验切换为身份证+手机验证码模式");
        }
    }
}
```

### 7.2 降级模式对应关系

| 降级场景 | 后端变更 | 影响范围 |
|---------|---------|---------|
| LLM 不可用 | 评分策略切换为关键词正则匹配；文书生成切换为预置模板 | 简历筛选、文书生成 |
| OCR 不可用 | 入职服务开放人工录入接口；跳过 OCR 校验步骤 | 入职办理 |
| 人脸不可用 | 认证服务启用"身份证+手机验证码"降级验证 | 入职、考勤签到 |
| 编排层异常 | 开放手动调度接口；Agent 独立执行 | 所有 Agent 流程 |
| RPA 被拦截 | 暂停 RPA 队列；生成预填数据下载 | 外务申报 |
| DB 故障 | 自动切换从库；双主宕机进入只读模式 | 全部服务 |

---

## 8. 定时任务

| 任务名称 | Cron 表达式 | 说明 |
|---------|------------|------|
| 简历定时抓取 | `0 */15 * * * *` | 每 15 分钟从各招聘平台拉取简历 |
| 打卡数据同步 | `0 */30 * * * *` | 每 30 分钟同步打卡设备数据 |
| 月度薪资核算 | `0 0 22 28-31 * ?` | 每月末 22:00 触发 |
| 证书效期扫描 | `0 9 * * *` | 每日 9:00 扫描证书效期 |
| 简历健康检查 | `0 0 3 * * 0` | 每周日凌晨 3:00 |
| RPA 流程验证 | `0 10 * * 1` | 每周一 10:00 验证 RPA 可用性 |
| 偏见测试 | `0 0 0 1 */3 ?` | 每季度首月 1 日 0:00 |
| 全量备份 | `0 0 2 * * 0` | 每周日凌晨 2:00 |
| 增量备份 | `0 0 2 * * *` | 每日凌晨 2:00 |
| 审计日志归档 | `0 0 4 1 * ?` | 每月 1 日 4:00 归档上月日志 |
| Agent 模型精度复查 | `0 0 0 1 */3 ?` | 每季度首月 |
| Token 用量统计 | `0 0 8 * * *` | 每日 8:00 统计前日用量 |

---

## 9. 全链路追踪

### 9.1 追踪架构

```
[前端请求] → [API Gateway] → [微服务 A] → [RabbitMQ] → [Agent B]
    │              │              │             │             │
    └──────────────┴──────────────┴─────────────┴─────────────┘
                         trace-id
                         │
                    [Zipkin / Jaeger]
                         │
                    [可视化追踪]
```

### 9.2 追踪字段

| 字段 | 说明 |
|------|------|
| trace-id | 全局唯一追踪 ID (UUID) |
| span-id | 当前操作段 ID |
| parent-span-id | 父操作段 ID |
| service-name | 服务名称 |
| operation-name | 操作名称 |
| timestamp | 开始时间 |
| duration | 耗时 (ms) |
| status | 成功/失败 |
| tags | 附加标签 (userId, agentName 等) |

---

*文档结束*
