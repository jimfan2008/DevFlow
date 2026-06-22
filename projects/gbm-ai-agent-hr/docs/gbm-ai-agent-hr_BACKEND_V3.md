# GBM AI Agent HR 智能人力管理系统 — 后端设计文档 (V2)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 后端设计文档 |
| 版本号 | V2.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-12 |
| 作者 | 后旺 (HouWang) |
| 角色 | 后端架构师 |

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

---

## 1. 后端技术栈

### 1.1 核心技术

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | Java | 17 LTS | 企业级稳定性 |
| 框架 | Spring Boot | 3.2.x | 微服务基础框架 |
| Spring Cloud | 2023.x | 服务治理 |
| ORM | MyBatis-Plus | 3.5.x | 灵活 SQL 控制 |
| API 文档 | SpringDoc OpenAPI | 2.x | 自动生成 API 文档 |
| 认证 | Spring Security | 6.x | 安全框架 |
| JWT | jjwt | 0.12.x | Token 生成与验证 |
| 消息队列 | Apache Kafka | 3.x | 事件总线 |
| 流程引擎 | Camunda | 7.21.x | BPMN 2.0 流程编排 |
| 缓存 | Redis | 7.x | Redisson 客户端 |
| 配置中心 | Nacos | 2.x | 配置热更 + 服务发现 |
| 链路追踪 | OpenTelemetry | 1.x | 分布式追踪 |
| 日志 | SLF4J + Logback | - | 结构化日志 |
| 对象存储 | MinIO SDK | 8.x | 文件上传/下载 |
| RPA | Playwright | - | 浏览器自动化 |
| OCR | PaddleOCR Java API | - | 证件识别 |
| 人脸 | Face++ SDK / 自研 | - | 人脸比对 |
| 定时任务 | XXL-JOB | 2.x | 分布式任务调度 |
| 测试 | JUnit 5 + Mockito | - | 单元测试 |
| 测试容器 | Testcontainers | - | 集成测试 |

### 1.2 架构模式

采用**模块化单体 (Modular Monolith)** 架构，各模块通过包边界隔离，后期可按需拆分为微服务。

**模块划分依据**：
- 业务域独立性
- 数据隔离性
- 部署独立性（未来）
- 团队职责划分

---

## 2. 项目结构

```
gbm-ai-agent-hr-backend/
├── gbm-hr-core/                     # 核心公共模块
│   ├── src/main/java/com/gbm/hr/core/
│   │   ├── config/                  # 全局配置
│   │   │   ├── SwaggerConfig.java
│   │   │   ├── RedisConfig.java
│   │   │   ├── KafkaConfig.java
│   │   │   ├── MyBatisConfig.java
│   │   │   ├── WebMvcConfig.java
│   │   │   └── SecurityConfig.java
│   │   ├── constant/                # 常量定义
│   │   │   ├── ErrorCode.java
│   │   │   ├── CacheKey.java
│   │   │   └── KafkaTopic.java
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
│   │   │   └── ExcelUtil.java
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
│   │   │   └── RoleMapper.java
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
│   │   │   └── ExamPaperMapper.java
│   │   └── job/
│   │       ├── ResumeCrawlJob.java     # 定时抓取简历
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
│   │   │   ├── Employee.java
│   │   │   ├── OnboardingRecord.java
│   │   │   └── EmployeeDocument.java
│   │   └── mapper/
│   │       ├── EmployeeMapper.java
│   │       └── OnboardingRecordMapper.java
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
│   │       └── CheckInRecordMapper.java
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
│   │   ├── mapper/
│   │   │   ├── AttendanceRecordMapper.java
│   │   │   └── LeaveRecordMapper.java
│   │   └── job/
│   │       └── AttendanceSyncJob.java  # 定时同步打卡数据
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
│   │   ├── mapper/
│   │   │   ├── PayrollMapper.java
│   │   │   └── PayslipMapper.java
│   │   └── job/
│   │       └── MonthlyPayrollJob.java  # 月末薪资核算
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
│   │       ├── SocialSecurityRPA.java  # 社保系统 RPA
│   │       ├── HousingFundRPA.java     # 公积金系统 RPA
│   │       └── RPAExecutor.java        # RPA 执行器
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
│   │   │   ├── ResignationRecord.java
│   │   │   └── CertificateRequest.java
│   │   └── mapper/
│   │       ├── ResignationMapper.java
│   │       └── CertificateMapper.java
│   └── build.gradle
│
├── gbm-hr-agent/                    # Agent 运行时模块
│   ├── src/main/java/com/gbm/hr/agent/
│   │   ├── runtime/
│   │   │   ├── AgentRuntime.java       # Agent 运行时
│   │   │   ├── AgentContext.java       # Agent 上下文
│   │   │   └── AgentResult.java        # Agent 执行结果
│   │   ├── orchestration/
│   │   │   ├── Orchestrator.java       # 编排器
│   │   │   ├── Pipeline.java           # 流水线编排
│   │   │   ├── FanOutFanIn.java        # 扇出扇入编排
│   │   │   ├── DecisionTree.java       # 决策树编排
│   │   │   └── FeedbackLoop.java       # 反馈环编排
│   │   ├── guardrail/
│   │   │   ├── Guardrail.java          # 护栏接口
│   │   │   ├── AmountGuardrail.java    # 金额护栏
│   │   │   ├── CommunicationGuardrail.java
│   │   │   ├── DataDeleteGuardrail.java
│   │   │   └── ReasoningGuardrail.java
│   │   ├── logging/
│   │   │   ├── AgentLogger.java        # Agent 日志
│   │   │   └── ReasoningTrace.java     # 推理链
│   │   ├── retry/
│   │   │   ├── RetryPolicy.java        # 重试策略
│   │   │   └── ExponentialBackoff.java # 指数退避
│   │   └── kafka/
│   │       ├── AgentMessageProducer.java
│   │       └── AgentMessageConsumer.java
│   └── build.gradle
│
├── gbm-hr-notification/             # 通知模块
│   ├── src/main/java/com/gbm/hr/notification/
│   │   ├── controller/
│   │   │   └── NotificationController.java
│   │   ├── service/
│   │   │   ├── EmailService.java
│   │   │   ├── SMS Service.java
│   │   │   ├── PushNotificationService.java
│   │   │   └── NotificationService.java
│   │   ├── template/
│   │   │   ├── EmailTemplateEngine.java
│   │   │   └── SMSTemplateEngine.java
│   │   └── kafka/
│   │       └── NotificationConsumer.java
│   └── build.gradle
│
├── gbm-hr-audit/                    # 审计模块
│   ├── src/main/java/com/gbm/hr/audit/
│   │   ├── service/
│   │   │   └── AuditLogService.java
│   │   ├── aspect/
│   │   │   └── AuditLogAspect.java     # AOP 审计切面
│   │   ├── entity/
│   │   │   └── AuditLog.java
│   │   └── mapper/
│   │       └── AuditLogMapper.java
│   └── build.gradle
│
├── gbm-hr-application/              # 启动模块
│   ├── src/main/java/com/gbm/hr/
│   │   └── GbmHrApplication.java     # Spring Boot 启动类
│   ├── src/main/resources/
│   │   ├── application.yml           # 主配置
│   │   ├── application-dev.yml       # 开发环境
│   │   ├── application-test.yml      # 测试环境
│   │   ├── application-prod.yml      # 生产环境
│   │   └── logback-spring.xml        # 日志配置
│   └── build.gradle
│
├── build.gradle                     # 根构建脚本
├── settings.gradle                  # 模块设置
└── gradle/                          # Gradle 包装器
```

---

## 3. API 接口设计

### 3.1 统一响应格式

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
    "username": "string",       // 账号/邮箱/手机号
    "password": "string"        // 密码 (前端已加密)
}

Response (200):
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

Response (200 - MFA needed):
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
Authorization: Bearer temp_token

Request:
{
    "code": "123456"            // 验证码
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

### 3.3 招聘管理 API

#### 3.3.1 岗位管理

```
GET    /api/v1/recruitment/jobs                # 岗位列表 (分页)
GET    /api/v1/recruitment/jobs/{id}           # 岗位详情
POST   /api/v1/recruitment/jobs                # 创建岗位
PUT    /api/v1/recruitment/jobs/{id}           # 更新岗位
DELETE /api/v1/recruitment/jobs/{id}           # 删除岗位
POST   /api/v1/recruitment/jobs/{id}/publish   # 发布到招聘平台
GET    /api/v1/recruitment/jobs/{id}/channels  # 查看发布渠道
```

#### 3.3.2 简历管理

```
GET    /api/v1/recruitment/resumes                    # 简历列表 (分页+筛选)
GET    /api/v1/recruitment/resumes/{id}               # 简历详情
GET    /api/v1/recruitment/resumes/{id}/score-detail  # 评分明细
POST   /api/v1/recruitment/resumes/import             # 批量导入 (Excel/CSV)
POST   /api/v1/recruitment/resumes/{id}/classify      # 手动分类
GET    /api/v1/recruitment/resumes/export             # 导出简历
POST   /api/v1/recruitment/resumes/search/nl          # 自然语言搜索

# 导入请求示例
POST /api/v1/recruitment/resumes/import
Content-Type: multipart/form-data

File: file (xlsx/xls/csv, max 50MB)

Response:
{
    "code": 200,
    "data": {
        "total": 150,
        "success": 142,
        "failed": 8,
        "failures": [
            {"row": 5, "reason": "身份证号格式无效"},
            {"row": 12, "reason": "手机号格式无效"}
        ]
    }
}

# 自然语言搜索示例
POST /api/v1/recruitment/resumes/search/nl
{
    "query": "找出所有有5年以上Java经验且做过微服务架构设计的候选人"
}
```

#### 3.3.3 考试管理

```
GET    /api/v1/recruitment/exams                    # 考试列表
POST   /api/v1/recruitment/exams                    # 创建考试 (Agent 组卷)
GET    /api/v1/recruitment/exams/{id}               # 考试详情
GET    /api/v1/recruitment/exams/{id}/qr-code       # 生成考试二维码
POST   /api/v1/recruitment/exams/{id}/publish        # 发布考试
GET    /api/v1/recruitment/exams/{id}/results        # 查看成绩
GET    /ai/v1/recruitment/exams/{token}/paper        # 考生获取试卷 (Token 访问)
POST   /ai/v1/recruitment/exams/{token}/submit       # 考生提交答案
```

#### 3.3.4 题库管理

```
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

---

## 4. 数据流设计

### 4.1 简历筛选数据流

```
招聘平台 (前程无忧/中国人才热线)
    ↓ (每15分钟定时拉取)
简历抓取 Agent (RecruitmentChannelAgent)
    ↓ (Kafka: resume.new topic)
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
    ↓ (Kafka: resume.classified topic)
简历入库 (MySQL: resume 表)
    ↓
通知 HR (Kafka: notification.topic)
    ↓
前端 Dashboard 待办提醒
```

### 4.2 薪资核算数据流

```
月末定时触发 (XXL-JOB: MonthlyPayrollJob)
    ↓
薪资 Agent (PayrollAgent)
    ├── Fan-Out: 并行拉取数据
    │   ├── 考勤 Agent → 当月考勤数据 (Kafka)
    │   ├── 社保/公积金系统 → 缴纳数据 (API)
    │   └── 薪资规则库 → 现行规则 (Redis 缓存)
    ├── Fan-In: 汇聚数据
    │
    ├── 计算流程
    │   ├── 应发工资 = 基本工资 + 加班费 - 考勤扣款 + 补贴
    │   ├── 加班费 = 平日1.5倍 + 周末2倍 + 法定3倍
    │   ├── 个人社保 = 社保个人缴纳额
    │   ├── 个人公积金 = 公积金个人缴纳额
    │   ├── 应税收入 = 应发 - 社保 - 公积金 - 5000 - 专项扣除
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
    ↓ (Kafka: payroll.calculated topic)
推送 HR 审核 (notification.topic)
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

### 4.3 工伤处理数据流

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
    └── 调用 RPA Agent
        ↓
RPA Agent (RPAAgent)
    ├── 登录社保系统 (Playwright)
    ├── 自动填写表单
    ├── 上传备案材料
    ├── 提交申报
    ├── 截图保存回执
    └── 返回申报回执
    ↓
跟踪理赔进度 (定时查询)
    ↓
状态更新 → 通知相关人员 (Kafka: notification.topic)
    ↓
理赔到账 → 记录理赔金额
```

### 4.4 新员工入职数据流

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
    │   ├── OCR 信息 vs 身份证原件
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
        ├── 组装结构化信息
        ├── 建立档案索引
        └── 归档至 MinIO
    ↓
入职完成通知 HR (Kafka: notification.topic)
    ↓
触发公积金参保 (ExternalAgent)
    ↓
触发培训计划 (TrainingAgent)
```

---

## 5. 中间件设计

### 5.1 Kafka 消息队列

#### Topic 设计

| Topic | 分区数 | 副本因子 | 保留时间 | 用途 |
|-------|--------|---------|---------|------|
| resume.new | 8 | 3 | 7d | 新简历流入 |
| resume.classified | 8 | 3 | 7d | 简历分拣结果 |
| resume.score | 4 | 3 | 30d | 评分结果 |
| payroll.calculated | 4 | 3 | 90d | 薪资核算结果 |
| payroll.review | 2 | 3 | 90d | 薪资审核 |
| attendance.sync | 8 | 3 | 30d | 考勤数据同步 |
| attendance.anomaly | 4 | 3 | 90d | 考勤异常 |
| training.checkin | 4 | 3 | 30d | 培训签到 |
| training.exam | 4 | 3 | 30d | 考试成绩 |
| notification.email | 4 | 3 | 7d | 邮件通知 |
| notification.sms | 4 | 3 | 7d | 短信通知 |
| notification.push | 4 | 3 | 7d | APP 推送 |
| agent.event | 8 | 3 | 30d | Agent 事件 |
| agent.error | 4 | 3 | 90d | Agent 错误 |
| rpa.task | 2 | 3 | 7d | RPA 任务 |
| rpa.result | 2 | 3 | 30d | RPA 结果 |
| audit.log | 8 | 3 | 365d | 审计日志 |

#### 消息格式

```json
{
    "message_id": "uuid-v4",
    "trace_id": "uuid-v4",
    "flow_id": "uuid-v4",
    "source": "agent_name",
    "target": "agent_name|*|topic_name",
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

### 5.3 Camunda 流程引擎

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

### 5.4 XXL-JOB 定时任务

| Job Handler | Cron 表达式 | 描述 |
|-------------|------------|------|
| ResumeCrawlJob | `0 */15 * * * ?` | 每 15 分钟抓取简历 |
| AttendanceSyncJob | `0 */30 * * * ?` | 每 30 分钟同步打卡数据 |
| MonthlyPayrollJob | `0 0 2 28 * ?` | 每月 28 日凌晨 2 点核算薪资 |
| CertificateExpiryJob | `0 9 * * ?` | 每天 9 点检查证书效期 |
| TalentHealthCheckJob | `0 0 3 ? * 0` | 每周日凌晨 3 点简历健康检查 |
| RPAValidationJob | `0 10 ? * 1` | 每周一 10 点验证 RPA 流程 |
| DataArchiveJob | `0 0 2 ? * 0` | 每周日凌晨 2 点数据归档 |
| BackupJob | `0 0 1 ? * 6` | 每周日凌晨 1 点全量备份 |
| ModelAccuracyJob | `0 0 9 1 * ?` | 每月 1 日 9 点模型精度复查 |
| BiasTestJob | `0 0 10 1 */3 ?` | 每季度首日 10 点偏见测试 |

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
后续请求携带 Token (Authorization: Bearer xxx)
    ↓
JwtAuthenticationFilter → 验证 Token
    ↓
加载用户权限到 SecurityContext
    ↓
业务逻辑执行
```

### 6.2 JWT Token 设计

```java
public class JwtToken {
    // Header
    private String alg = "RS256";
    private String typ = "JWT";
    
    // Payload
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

// Token 配置
// Access Token: 有效期 2 小时
// Refresh Token: 有效期 7 天
// RSA 密钥对: 2048 位，定期轮换
```

### 6.3 RBAC 权限模型

```
用户 (User)
    ↓ (多对多)
角色 (Role)
    ↓ (多对多)
权限 (Permission)

权限命名规则: {模块}:{资源}:{操作}

示例:
recruitment:job:create        创建岗位
recruitment:job:read          查看岗位
recruitment:job:update        编辑岗位
recruitment:job:delete        删除岗位
recruitment:resume:read       查看简历
recruitment:resume:export     导出简历
payroll:data:read             查看薪资数据 (需 MFA)
payroll:data:update           修改薪资数据 (需 MFA)
system:user:create            创建用户 (管理员)
system:audit:read             查看审计日志 (管理员)
```

### 6.4 数据加密

```java
@Component
public class DataEncryptionService {
    
    // AES-256-GCM 加密
    public String encrypt(plaintext: String): String {
        // 生成随机 IV
        // AES-256-GCM 加密
        // 返回: IV + ciphertext (Base64)
    }
    
    public String decrypt(ciphertext: String): String {
        // 提取 IV
        // AES-256-GCM 解密
        // 返回明文
    }
    
    // 加密字段:
    // - 身份证号 (employee.id_number)
    // - 人脸特征 (face.features)
    // - 薪资数据 (payroll.net_pay) - 数据库级加密
}
```

### 6.5 审计日志 (AOP 切面)

```java
@Aspect
@Component
public class AuditLogAspect {
    
    @Around("@annotation(AuditLog)")
    public Object audit(ProceedingJoinPoint point, AuditLog annotation) 
            throws Throwable {
        // 记录操作前快照
        AuditLogEntry entry = new AuditLogEntry();
        entry.setOperationTime(LocalDateTime.now());
        entry.setOperator(getCurrentUserId());
        entry.setOperatorIp(getClientIp());
        entry.setOperationType(annotation.type());
        entry.setModule(annotation.module());
        entry.setTarget(annotation.target());
        
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

// 使用示例
@AuditLog(type = "UPDATE", module = "PAYROLL", target = "payroll:{month}")
public PayrollResult calculatePayroll(String month) {
    // 薪资核算逻辑
}
```

---

## 7. Agent 运行时设计

### 7.1 Agent 基类

```java
public abstract class BaseAgent {
    
    protected String agentName;
    protected AgentLogger logger;
    protected AgentMessageProducer messageProducer;
    protected GuardrailExecutor guardrailExecutor;
    protected RetryPolicy retryPolicy;
    
    /**
     * Agent 执行入口
     */
    public AgentResult execute(AgentContext context) {
        // 1. 记录开始
        logger.logStart(agentName, context.getFlowId());
        
        // 2. 感知阶段: 获取所需数据
        var inputs = perceive(context);
        
        // 3. 推理阶段: 分析并决策
        var decision = reason(inputs, context);
        
        // 4. 护栏检查
        guardrailExecutor.check(decision);
        
        // 5. 行动阶段: 执行操作
        AgentResult result;
        try {
            result = retryPolicy.execute(() -> act(decision, context));
        } catch (GuardrailException e) {
            result = AgentResult.blocked(e.getMessage());
        } catch (Exception e) {
            result = AgentResult.failed(e.getMessage());
            logger.logError(agentName, context.getFlowId(), e);
        }
        
        // 6. 记录结果
        logger.logEnd(agentName, context.getFlowId(), result);
        
        // 7. 发布事件
        messageProducer.send(context.getFlowId(), agentName, result);
        
        return result;
    }
    
    // 子类实现
    protected abstract Map<String, Object> perceive(AgentContext context);
    protected abstract Decision reason(Map<String, Object> inputs, AgentContext context);
    protected abstract AgentResult act(Decision decision, AgentContext context);
}
```

### 7.2 Agent 执行日志

```java
@Entity
@Table(name = "agent_run_log")
public class AgentRunLog {
    @Id
    private String runId;              // UUID
    private String agentName;          // Agent 名称
    private String parentFlowId;       // 所属流程 ID
    private JsonNode inputsSummary;    // 输入概要
    private String reasoningTrace;     // 推理过程
    private JsonNode outputsSummary;   // 输出概要
    private String status;             // SUCCESS/FAILED/SUSPENDED
    private Long durationMs;           // 耗时
    private String errorDetail;        // 错误详情
    private LocalDateTime createdAt;   // 执行时间
}
```

### 7.3 安全护栏实现

```java
public class AmountGuardrail implements Guardrail {
    
    @Override
    public void check(Decision decision) throws GuardrailException {
        // 检查是否涉及金额变动
        if (decision.involvesAmountChange()) {
            // 检查是否有 HR 审核批准
            if (!decision.hasApproval(HR_APPROVAL)) {
                throw new GuardrailException(
                    "金额变动需要人事专员审核批准"
                );
            }
            // 检查金额合理性
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
        // 评分范围检查
        if (decision.isScoringResult()) {
            int score = decision.getScore();
            if (score < 0 || score > 100) {
                throw new GuardrailException(
                    String.format("评分 %d 超出 [0,100] 范围", score)
                );
            }
        }
        // 薪资非零检查
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

### 8.1 RPA 执行器

```java
@Service
public class RPAExecutor {
    
    @Autowired
    private Playwright playwright;
    
    /**
     * 执行 RPA 任务
     */
    public RPAResult execute(RPATask task) {
        Browser browser = null;
        try {
            // 1. 启动浏览器
            browser = playwright.chromium()
                .launch(new BrowserType.LaunchOptions()
                    .setHeadless(true)
                    .setTimeout(60000));
            
            Page page = browser.newPage();
            
            // 2. 登录目标网站
            login(page, task.getCredentials());
            
            // 3. 导航到目标页面
            page.navigate(task.getTargetUrl());
            
            // 4. 执行操作序列
            for (RPAAction action : task.getActions()) {
                executeAction(page, action);
            }
            
            // 5. 截图保存
            String screenshot = page.screenshot();
            
            // 6. 捕获回执
            String receipt = captureReceipt(page);
            
            return RPAResult.success(screenshot, receipt);
            
        } catch (Exception e) {
            return RPAResult.failed(e.getMessage());
        } finally {
            if (browser != null) {
                browser.close();
            }
        }
    }
    
    /**
     * 执行单个 RPA 操作
     */
    private void executeAction(Page page, RPAAction action) {
        switch (action.getType()) {
            case CLICK:
                page.locator(action.getSelector()).click();
                break;
            case TYPE:
                page.locator(action.getSelector()).fill(action.getValue());
                break;
            case SELECT:
                page.locator(action.getSelector())
                    .selectOption(action.getValue());
                break;
            case UPLOAD:
                page.locator(action.getSelector())
                    .setInputFiles(action.getFile());
                break;
            case WAIT:
                page.waitForTimeout(action.getTimeout());
                break;
            case SCROLL:
                page.evaluate(String.format(
                    "window.scrollBy(0, %d)", action.getScrollAmount()));
                break;
        }
    }
}
```

### 8.2 RPA 任务定义

```java
public class RPATask {
    private String taskId;             // 任务 ID
    private String targetSystem;       // 目标系统 (社保/公积金)
    private String targetUrl;          // 目标 URL
    private Credentials credentials;   // 登录凭证 (加密)
    private List<RPAAction> actions;   // 操作序列
    private int timeoutSeconds;        // 超时时间
    private int maxRetries;            // 最大重试次数
}

public class RPAAction {
    private ActionType type;           // CLICK/TYPE/SELECT/UPLOAD/WAIT/SCROLL
    private String selector;           // CSS 选择器
    private String value;              // 输入值
    private String file;               // 上传文件路径
    private int timeout;               // 等待时间
    private int scrollAmount;          // 滚动距离
}
```

### 8.3 RPA 自适应检测

```java
@Component
public class RPAAdaptationService {
    
    /**
     * 每周验证 RPA 流程可用性
     */
    @Scheduled(cron = "0 10 ? * 1")  // 每周一 10 点
    public void validateRPAFlows() {
        for (RPAFlow flow : rpaFlowRepository.findAll()) {
            // 执行干运行 (Dry Run)
            ValidationResult result = dryRun(flow);
            
            if (!result.isAdaptable()) {
                // 页面元素变化告警
                alertService.sendAlert(
                    String.format("RPA 流程 '%s' 检测到页面变化", flow.getName()),
                    AlertLevel.WARNING,
                    result.getChanges()
                );
            }
            
            // 失败率 > 5% 时触发重新配置
            if (flow.getFailureRate() > 0.05) {
                alertService.sendAlert(
                    String.format("RPA 流程 '%s' 失败率 %.1f%%，需要重新配置",
                        flow.getName(), flow.getFailureRate() * 100),
                    AlertLevel.CRITICAL
                );
            }
        }
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
        log.warn("Business exception: {}", e.getMessage());
        return Result.error(400, e.getMessage());
    }
    
    @ExceptionHandler(AuthenticationException.class)
    public Result<Void> handleAuthException(AuthenticationException e) {
        log.warn("Authentication failed: {}", e.getMessage());
        return Result.error(401, e.getMessage());
    }
    
    @ExceptionHandler(AuthorizationException.class)
    public Result<Void> handleAuthorizationException(AuthorizationException e) {
        log.warn("Authorization denied: {}", e.getMessage());
        return Result.error(403, e.getMessage());
    }
    
    @ExceptionHandler(AgentExecutionException.class)
    public Result<Void> handleAgentException(AgentExecutionException e) {
        log.error("Agent execution failed", e);
        // 触发告警
        alertService.sendAgentAlert(e);
        return Result.error(500, "Agent 执行失败，已自动记录并告警");
    }
    
    @ExceptionHandler(Exception.class)
    public Result<Void> handleUnexpectedException(Exception e) {
        log.error("Unexpected error", e);
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
    │   └── 生成故障摘要 (Error Report)
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
| 索引优化 | 为高频查询字段建立索引 (employee_id, date, status 等) |
| 分页查询 | 使用 MyBatis-Plus 分页插件，避免全表扫描 |
| 读写分离 | MySQL 主从复制，读操作走从库 |
| 连接池 | HikariCP 连接池，最大连接数 50 |
| SQL 优化 | 避免 N+1 查询，使用 JOIN 或批量查询 |
| 缓存热点数据 | Redis 缓存薪资规则、岗位信息等热点数据 |

### 10.2 API 性能优化

| 优化手段 | 实施方式 |
|---------|---------|
| 响应压缩 | GZIP 压缩响应体 |
| 分页限制 | 默认 20 条/页，最大 100 条/页 |
| 字段过滤 | 支持 SELECT 字段过滤，减少数据传输 |
| 批量操作 | 支持批量导入/导出/更新 |
| 异步处理 | 长时间操作 (薪资核算、RPA) 采用异步 + 回调 |
|  CDN  | 静态资源走 CDN |

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
| Kafka 消费延迟 | ≤ 1s | Kafka Consumer Lag |
| 系统 CPU 使用率 | ≤ 85% (5min) | Prometheus |
| 系统内存使用率 | ≤ 90% (5min) | Prometheus |

---

*文档结束*
