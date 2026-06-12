# GBM AI Agent HR 智能人力管理系统 — 后端设计文档 (V2)

## 版本信息

| 版本号 | 日期 | 作者 | 说明 |
|--------|------|------|------|
| 2.0 | 2026-06-12 | 后旺 | 基于 SRS V15 重新设计的后端架构文档 |

---

## 1. 后端技术栈

### 1.1 核心技术

| 类别 | 技术选型 | 版本 | 选型理由 |
|------|---------|------|---------|
| 语言 | Java | 21 | LTS、Record/Virtual Threads、GC 优化 |
| 框架 | Spring Boot | 3.3.x | 成熟生态、自动配置、生产级稳定性 |
| ORM | MyBatis-Plus | 3.5.x | 灵活 SQL、代码生成、分页插件 |
| API | RESTful + WebSocket | — | 标准接口 + 实时推送 |
| 认证 | Spring Security + JWT | 6.x | RBAC 权限模型、OAuth2 扩展 |
| 流程编排 | Temporal.io SDK | 1.x | DAG 编排、断点恢复、重试策略 |
| 消息队列 | Kafka + RabbitMQ | 3.x/3.13 | 事件流(高吞吐) + Agent 通信(低延迟) |
| RPC | gRPC | 1.x | 高性能内部通信、ProtoBuf 定义 |
| 缓存 | Redis (Spring Data Redis) | 7.x | 会话、分布式锁、热点数据 |
| 对象存储 | MinIO SDK | 8.x | S3 兼容、私有化部署 |
| 搜索引擎 | Elasticsearch | 8.x | 简历全文检索、日志检索 |
| 文档 | SpringDoc OpenAPI 3 | 2.x | 自动生成 OpenAPI 文档 |
| 配置中心 | Nacos | 2.x | 动态配置热更新、服务发现 |
| 监控 | Micrometer + Prometheus | — | 指标采集 |
| 链路追踪 | Micrometer Tracing + Zipkin | — | 全链路追踪 |
| 日志 | SLF4J + Logback | — | 结构化日志输出 |
| 构建 | Maven | 3.9.x | 依赖管理、多模块构建 |
| 测试 | JUnit 5 + Mockito + Testcontainers | — | 单元测试、集成测试 |

### 1.2 项目结构 (多模块 Maven)

```
gbm-ai-agent-hr-server/
├── pom.xml                              # 父 POM (BOM 管理)
├── gbm-common/                          # 公共模块
│   ├── gbm-common-core/                 # 核心工具类
│   │   ├── constants/                   # 常量定义
│   │   ├── exception/                   # 全局异常体系
│   │   ├── response/                    # 统一响应结构
│   │   ├── util/                        # 工具类
│   │   └── validator/                   # 校验器
│   ├── gbm-common-security/             # 安全公共模块
│   │   ├── jwt/                         # JWT 工具
│   │   ├── rbac/                        # RBAC 注解与切面
│   │   └── audit/                       # 审计日志切面
│   └── gbm-common-mq/                   # 消息队列公共模块
│       ├── kafka/                       # Kafka 配置
│       └── rabbitmq/                    # RabbitMQ 配置
│
├── gbm-gateway/                         # API 网关模块
│   └── src/main/java/.../gateway/
│       ├── GatewayApplication.java
│       ├── filter/                      # 网关过滤器
│       │   ├── AuthGlobalFilter.java
│       │   ├── RateLimitFilter.java
│       │   └── AuditLogFilter.java
│       └── route/                       # 路由配置
│
├── gbm-orchestration/                   # Agent 编排调度模块
│   └── src/main/java/.../orchestration/
│       ├── OrchestrationApplication.java
│       ├── workflow/                    # 工作流定义
│       │   ├── OnboardingWorkflow.java
│       │   ├── PayrollWorkflow.java
│       │   ├── RecruitmentWorkflow.java
│       │   └── ResignationWorkflow.java
│       ├── scheduler/                   # 定时任务调度
│       │   ├── ResumeCrawlScheduler.java
│       │   ├── CertificateExpiryScheduler.java
│       │   ├── PayrollTriggerScheduler.java
│       │   └── AttendanceSyncScheduler.java
│       └── state/                       # 流程状态管理
│
├── gbm-agent-runtime/                   # Agent 运行时框架
│   └── src/main/java/.../agent/
│       ├── Agent.java                   # Agent 接口
│       ├── AgentContext.java            # Agent 执行上下文
│       ├── AgentRegistry.java           # Agent 注册表
│       ├── guardrail/                   # 安全护栏
│       │   ├── AmountGuardrail.java
│       │   ├── CommunicationGuardrail.java
│       │   └── DeletionGuardrail.java
│       └── trace/                       # 推理链追踪
│           ├── ReasoningTrace.java
│           └── TraceRepository.java
│
├── gbm-service-recruitment/             # 招聘服务
│   └── src/main/java/.../recruitment/
│       ├── controller/
│       │   ├── JobPostController.java
│       │   ├── ResumeController.java
│       │   ├── ExamController.java
│       │   └── TalentPoolController.java
│       ├── service/
│       │   ├── JobPostService.java
│       │   ├── ResumeMatchService.java
│       │   └── ExamService.java
│       ├── agent/
│       │   ├── RecruitmentChannelAgent.java
│       │   ├── ResumeMatchAgent.java
│       │   ├── ExamPaperAgent.java
│       │   └── GradingAgent.java
│       ├── mapper/                      # MyBatis Mapper
│       └── dto/
│
├── gbm-service-onboarding/              # 入职服务
│   └── src/main/java/.../onboarding/
│       ├── agent/
│       │   ├── OnboardingAgent.java
│       │   ├── OCRAgent.java
│       │   └── FaceAgent.java
│       ├── controller/
│       ├── service/
│       ├── mapper/
│       └── dto/
│
├── gbm-service-training/                # 培训服务
│   └── src/main/java/.../training/
│       ├── agent/
│       │   ├── TrainingAgent.java
│       │   ├── MaterialToVideoAgent.java
│       │   └── AuditDocAgent.java
│       ├── controller/
│       ├── service/
│       ├── mapper/
│       └── dto/
│
├── gbm-service-attendance/              # 考勤服务
│   └── src/main/java/.../attendance/
│       ├── agent/
│       │   └── AttendanceAgent.java
│       ├── controller/
│       ├── service/
│       ├── mapper/
│       └── dto/
│
├── gbm-service-payroll/                 # 薪资服务
│   └── src/main/java/.../payroll/
│       ├── agent/
│       │   ├── PayrollAgent.java
│       │   └── PayslipAgent.java
│       ├── controller/
│       ├── service/
│       ├── calculator/                  # 薪资计算引擎
│       │   ├── PayrollCalculator.java
│       │   ├── OvertimeCalculator.java
│       │   ├── TaxCalculator.java
│       │   └── SocialSecurityCalculator.java
│       ├── mapper/
│       └── dto/
│
├── gbm-service-performance/             # 绩效服务
│   └── src/main/java/.../performance/
│       ├── agent/
│       │   └── PerformanceAgent.java
│       ├── controller/
│       ├── service/
│       ├── mapper/
│       └── dto/
│
├── gbm-service-external/                # 外务服务
│   └── src/main/java/.../external/
│       ├── agent/
│       │   ├── ExternalAgent.java
│       │   └── RPAAgent.java
│       ├── controller/
│       ├── service/
│       ├── rpa/                         # RPA 自动化引擎
│       │   ├── SocialSecurityRPA.java
│       │   ├── HousingFundRPA.java
│       │   └── RPABase.java
│       ├── mapper/
│       └── dto/
│
├── gbm-service-certificate/             # 证明服务
│   └── src/main/java/.../certificate/
│       ├── agent/
│       │   └── CertificateAgent.java
│       ├── controller/
│       ├── service/
│       ├── mapper/
│       └── dto/
│
├── gbm-service-budget/                  # 预算服务
│   └── src/main/java/.../budget/
│       ├── agent/
│       │   └── BudgetAgent.java
│       ├── controller/
│       ├── service/
│       ├── mapper/
│       └── dto/
│
├── gbm-service-analysis/                # 分析服务
│   └── src/main/java/.../analysis/
│       ├── agent/
│       │   └── AnalysisAgent.java
│       ├── controller/
│       ├── service/
│       └── dto/
│
├── gbm-model-service/                   # AI 模型服务
│   └── src/main/java/.../model/
│       ├── LLMService.java              # LLM 推理服务
│       ├── OCRService.java              # OCR 识别服务
│       ├── FaceService.java             # 人脸识别服务
│       ├── EmbeddingService.java        # 向量化服务
│       └── ASRService.java              # 语音转写服务
│
└── gbm-service-resignation/             # 离职服务
    └── src/main/java/.../resignation/
        ├── agent/
        │   └── ResignationAgent.java
        ├── controller/
        ├── service/
        ├── mapper/
        └── dto/
```

---

## 2. API 接口列表

### 2.1 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "traceId": "abc123..."
}
```

错误码规范：
- 2xx: 成功
- 4xx: 客户端错误
- 5xx: 服务端错误
- 业务错误码: 10000+ (如 10001 = 参数校验失败)

### 2.2 认证模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/auth/login | 用户登录 | 公开 |
| POST | /api/v1/auth/mfa/verify | MFA 验证 | 公开 |
| POST | /api/v1/auth/logout | 用户登出 | 已认证 |
| POST | /api/v1/auth/refresh | 刷新 Token | 已认证 |
| POST | /api/v1/auth/password/reset | 密码重置 | 已认证 + MFA |

### 2.3 招聘模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/recruitment/jobs | 招聘信息列表 | HR/Admin |
| POST | /api/v1/recruitment/jobs | 创建招聘信息 | HR/Admin |
| GET | /api/v1/recruitment/jobs/{id} | 招聘信息详情 | HR/Admin |
| PUT | /api/v1/recruitment/jobs/{id} | 更新招聘信息 | HR/Admin |
| POST | /api/v1/recruitment/jobs/{id}/publish | 发布到渠道 | HR/Admin |
| GET | /api/v1/recruitment/resumes | 简历列表 | HR/Admin |
| POST | /api/v1/recruitment/resumes/import | 批量导入简历 | HR/Admin |
| GET | /api/v1/recruitment/resumes/{id} | 简历详情+评分 | HR/Admin |
| POST | /api/v1/recruitment/resumes/{id}/review | 简历审核确认 | HR |
| GET | /api/v1/recruitment/resumes/stats | 简历筛选统计 | HR/Admin |
| POST | /api/v1/recruitment/exams/generate | Agent 生成试卷 | HR/Admin |
| GET | /api/v1/recruitment/exams/{id} | 试卷详情 | HR/Admin |
| POST | /api/v1/recruitment/exams/{id}/publish | 发布考试 | HR/Admin |
| GET | /api/v1/recruitment/exams/results | 考试成绩列表 | HR/Admin |
| GET | /api/v1/recruitment/exams/results/{id} | 个人成绩单 | HR/Admin |
| POST | /api/v1/recruitment/exams/submit | 提交答卷 | 考生 (Token) |
| GET | /api/v1/recruitment/talent-pool | 人才库查询 | HR/Admin |
| POST | /api/v1/recruitment/talent-pool/search | 自然语言搜索 | HR/Admin |

### 2.4 入职模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/onboarding/portal/{token} | 新员工门户 | 新员工 (Token) |
| POST | /api/v1/onboarding/portal/upload | 上传入职材料 | 新员工 (Token) |
| POST | /api/v1/onboarding/portal/sign | 签署电子协议 | 新员工 (Token) |
| POST | /api/v1/onboarding/portal/face | 人脸采集 | 新员工 (Token) |
| GET | /api/v1/onboarding/archives | 入职档案列表 | HR/Admin |
| GET | /api/v1/onboarding/archives/{id} | 档案详情 | HR/Admin |
| POST | /api/v1/onboarding/archives/{id}/approve | 档案审核 | HR |

### 2.5 试用期模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/probation/list | 试用期员工列表 | HR/Manager |
| GET | /api/v1/probation/{id}/evaluation | 转正评估报告 | HR/Manager |
| POST | /api/v1/probation/{id}/approve | 转正审批 | HR/Manager |

### 2.6 离职模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/resignation/apply | 提交离职申请 | 员工 |
| GET | /api/v1/resignation/list | 离职申请列表 | HR/Manager |
| GET | /api/v1/resignation/{id}/handover | 交接清单 | HR |
| POST | /api/v1/resignation/{id}/approve | 离职审批 | HR/Manager |
| POST | /api/v1/resignation/{id}/handover/confirm | 交接确认 | 相关部门 |
| GET | /api/v1/resignation/{id}/certificate | 离职证明 | HR |

### 2.7 培训模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/training/plans | 培训计划列表 | HR |
| POST | /api/v1/training/plans | 创建培训计划 | HR |
| POST | /api/v1/training/attendance/checkin | 扫码签到 | 受训人员 (Token) |
| GET | /api/v1/training/attendance/{planId} | 签到台账 | HR |
| POST | /api/v1/training/exam/{token}/start | 开始考试 | 考生 (Token) |
| POST | /api/v1/training/exam/submit | 提交答卷 | 考生 (Token) |
| GET | /api/v1/training/certificates | 证书列表 | HR/Employee |
| GET | /api/v1/training/videos | 视频库列表 | 全员 |
| POST | /api/v1/training/videos/generate | Agent 生成视频 | HR |
| POST | /api/v1/training/audit/generate | 生成审核资料包 | HR |

### 2.8 考勤模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/attendance/calendar | 考勤日历 | 全员 |
| GET | /api/v1/attendance/anomalies | 考勤异常列表 | HR/Manager |
| GET | /api/v1/attendance/report | 考勤报表 | HR/Manager |
| POST | /api/v1/attendance/shift | 调整排班 | HR |
| GET | /api/v1/attendance/export | 导出考勤数据 | HR |
| POST | /api/v1/attendance/sync | 手动同步打卡数据 | HR |

### 2.9 薪资模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/payroll/structure | 薪资结构 | HR/Admin |
| PUT | /api/v1/payroll/structure | 更新薪资规则 | HR/Admin + MFA |
| POST | /api/v1/payroll/calculate | 触发薪资核算 | HR + MFA |
| GET | /api/v1/payroll/review/{month} | 薪资审核页面 | HR |
| POST | /api/v1/payroll/review/{month}/approve | 薪资审核确认 | HR + MFA |
| GET | /api/v1/payroll/payslip | 查看工资条 | 员工本人 |
| GET | /api/v1/payroll/export | 导出薪资数据 | HR/Admin + MFA |
| GET | /api/v1/payroll/analytics | 薪资分析 | HR/Admin + MFA |

### 2.10 绩效模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/performance/list | 考核列表 | HR/Manager |
| POST | /api/v1/performance/self/submit | 提交自评 | 员工 |
| POST | /api/v1/performance/review | 上级评分 | Manager |
| GET | /api/v1/performance/report | 绩效报告 | HR/Manager |
| GET | /api/v1/performance/export | 导出绩效数据 | HR |

### 2.11 外务模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/external/injury/report | 工伤报告 | 全员 |
| GET | /api/v1/external/injury/list | 工伤案件列表 | HR/外务专员 |
| GET | /api/v1/external/injury/{id} | 工伤案件详情 | HR/外务专员 |
| POST | /api/v1/external/injury/{id}/file | RPA 工伤申报 | 外务专员 |
| GET | /api/v1/external/housing-fund/list | 公积金记录 | HR/外务专员 |
| POST | /api/v1/external/housing-fund/enroll | RPA 参保开户 | 外务专员 |
| POST | /api/v1/external/housing-fund/transfer | RPA 减员封存 | 外务专员 |
| GET | /api/v1/external/declaration/list | 政府申报列表 | HR/外务专员 |

### 2.12 证明模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/certificate/request | 申请证明 | 员工 |
| GET | /api/v1/certificate/request/list | 申请列表 | 员工 |
| GET | /api/v1/certificate/review | 待审核列表 | HR |
| POST | /api/v1/certificate/review/{id}/approve | 证明确认 | HR |
| GET | /api/v1/certificate/{id}/download | 下载证明文件 | 员工 |

### 2.13 预算模块 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /api/v1/budget/expense/upload | 上传费用票据 | 员工 |
| GET | /api/v1/budget/expense/list | 费用列表 | HR/Manager |
| GET | /api/v1/budget/expense/summary | 费用汇总 | HR |
| GET | /api/v1/budget/forecast | 预算预测 | HR/Admin |

### 2.14 系统管理 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /api/v1/system/users | 用户列表 | Admin |
| POST | /api/v1/system/users | 创建用户 | Admin |
| PUT | /api/v1/system/users/{id} | 更新用户 | Admin |
| DELETE | /api/v1/system/users/{id} | 删除用户 | Admin |
| GET | /api/v1/system/roles | 角色列表 | Admin |
| PUT | /api/v1/system/roles/{id} | 更新角色权限 | Admin |
| GET | /api/v1/system/agents/status | Agent 状态总览 | Admin |
| GET | /api/v1/system/agents/{name}/logs | Agent 执行日志 | Admin |
| GET | /api/v1/system/audit-log | 审计日志 | Admin |
| GET | /api/v1/system/config | 系统配置 | Admin |
| PUT | /api/v1/system/config | 更新系统配置 | Admin |
| GET | /api/v1/system/api-keys | API 密钥列表 | Admin |
| POST | /api/v1/system/api-keys | 创建 API 密钥 | Admin |
| DELETE | /api/v1/system/api-keys/{id} | 删除 API 密钥 | Admin |
| GET | /api/v1/system/monitor/metrics | 系统监控指标 | Admin |

### 2.15 WebSocket 接口

| 端点 | 说明 | 订阅角色 |
|------|------|---------|
| /ws/notifications | 全局通知推送 | 全员 |
| /ws/agent-progress | Agent 任务进度推送 | HR/Admin |
| /ws/alarm | 告警推送 | Admin |
| /ws/resume-update | 新简历到达通知 | HR |

---

## 3. 数据流

### 3.1 招聘数据流

```
[招聘平台] --> [RecruitmentChannelAgent (定时抓取/RPA)]
    --> [Kafka: resume-ingest topic]
        --> [ResumeMatchAgent (去重 + 评分)]
            --> [MySQL: resume 表]
                --> [消息队列: 高分简历通知]
                    --> [前端: HR 审核页面]
```

### 3.2 入职数据流

```
[新员工扫码] --> [OnboardingAgent 引导]
    --> [上传证件] --> [OCRAgent (识别)]
    --> [人脸采集] --> [FaceAgent (比对)]
    --> [签署协议] --> [电子签章存证]
    --> [MinIO: 存档文件]
    --> [MySQL: employee 表]
    --> [Redis: 人脸特征缓存]
```

### 3.3 薪资核算数据流

```
[月末触发] --> [PayrollAgent 启动]
    --> [Fan-Out 并行获取]
        --> [AttendanceService (考勤数据)]
        --> [MySQL (薪资主数据)]
        --> [社保/公积金 API]
    --> [Fan-In 汇聚数据]
        --> [PayrollCalculator (逐项计算)]
            --> [OvertimeCalculator]
            --> [TaxCalculator]
            --> [SocialSecurityCalculator]
        --> [异常检测]
        --> [生成核算底稿]
    --> [消息队列: 推送审核通知]
        --> [前端: HR 审核页面]
```

### 3.4 外务 RPA 数据流

```
[员工变动事件] --> [ExternalAgent 触发]
    --> [收集参保要素]
    --> [RPAAgent 启动]
        --> [Playwright 打开公积金网站]
        --> [自动登录 (凭证库读取)]
        --> [填写表单]
        --> [提交申报]
        --> [截屏保存回执]
        --> [MinIO: 回执存档]
    --> [MySQL: 记录操作结果]
    --> [消息队列: 通知外务专员]
```

---

## 4. 中间件

### 4.1 认证中间件 (AuthGlobalFilter)

- 解析请求 Header 中的 Authorization: Bearer {token}
- 验证 JWT 签名和过期时间
- 从 Token 中提取 userId、roles、permissions
- 将用户上下文注入请求属性 (RequestAttributes)
- 未认证请求返回 401

### 4.2 权限中间件 (RbacAspect)

- 基于 @PreAuthorize 注解进行方法级权限校验
- 支持行级数据权限过滤 (部门隔离)
- 示例: @PreAuthorize("hasRole('HR') && @dataPermission.checkDept(#request)")

### 4.3 审计日志中间件 (AuditLogAspect)

- 使用 AOP 切面拦截标注 @AuditLog 的方法
- 记录字段: 操作时间、操作人、IP、操作类型、模块、对象 ID、变更前后快照
- 异步写入审计日志表 (不阻塞主流程)
- 审计日志不可删除，保留 ≥ 10 年

### 4.4 限流中间件 (RateLimitFilter)

- 基于 Redis + Token Bucket 算法
- 默认限流: 100 req/min/IP
- 薪资查询限流: 30 req/min/user
- 简历导入限流: 5 req/min/user

### 4.5 全局异常处理 (GlobalExceptionHandler)

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(BusinessException.class)
    public ApiResponse handleBusiness(BusinessException e) {
        return ApiResponse.error(e.getCode(), e.getMessage());
    }
    
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResponse handleValidation(MethodArgumentNotValidException e) {
        // 提取字段级错误信息
    }
    
    @ExceptionHandler(Exception.class)
    public ApiResponse handleUnknown(Exception e) {
        log.error("Unhandled exception", e);
        return ApiResponse.error(50000, "系统内部错误");
    }
}
```

### 4.6 数据脱敏中间件 (DataMaskingSerializer)

- 对敏感字段自动脱敏 (身份证、手机号、薪资)
- 身份证: 310101********1234
- 手机号: 138****5678
- 薪资: 仅在授权用户可见完整值

---

## 5. 安全策略

### 5.1 认证与授权

**JWT 配置:**
- 签发者 (issuer): gbm-hr-auth-service
- 过期时间: 2 小时
- 刷新 Token 过期: 7 天
- 签名算法: RS256 (非对称)
- 载荷: userId, username, roles, permissions, deptId

**MFA 强制场景:**
- 管理员首次登录
- 访问薪资数据
- 公积金/社保操作
- 大批量导出
- 密码重置

**RBAC 权限模型:**

| 角色 | 权限范围 |
|------|---------|
| ADMIN | 全部模块全部操作 |
| HR | 招聘/入职/培训/考勤/薪资/绩效/证明 的 CRUD + 审核 |
| MANAGER | 本部门下属数据查看 + 审批 |
| EXTERNAL_SPECIALIST | 外务模块操作 + 审核 |
| EMPLOYEE | 自助查询 + 证明申请 + 绩效自评 |

**行级数据隔离:**
- 部门主管只能查看本部门下属
- 员工只能查看自己的数据
- HR 可查看全公司数据

### 5.2 数据安全

**加密存储:**
- 身份证号: AES-256-GCM 加密 (字段级)
- 人脸特征: AES-256-GCM 加密
- 薪资数据: AES-256-GCM 加密
- 加密密钥: 独立密钥管理服务保管，定期轮换 (90 天)

**传输安全:**
- 全链路 TLS 1.2+
- 内部服务间 mTLS (Istio Service Mesh)

**数据出境禁止:**
- 员工个人信息不出境
- 除非满足 PIPL 三项条件 (明示同意 + 安全评估 + 标准合同)

### 5.3 Agent 安全护栏

**金额操作护栏:**
```java
public class AmountGuardrail implements Guardrail {
    @Override
    public boolean check(AgentContext ctx, Operation op) {
        if (op.isAmountChange() && !ctx.hasApproval("HR")) {
            ctx.suspend("金额变动需人事专员审核");
            return false;
        }
        return true;
    }
}
```

**对外通讯护栏:**
- Agent 发送邮件给外部联系人前需预审确认
- 邮件内容经模板校验，防止注入

**数据删除护栏:**
- Agent 不得无条件删除已归档数据
- 只能移动至归档位
- 物理删除需二次审批

**模型推理护栏:**
- 输出结果经过合理性阈值检查
- 薪资不得为零、评分不得超出 [0, 100]

**Prompt 注入防护:**
- 对用户输入统一注入安全过滤
- 使用结构化 Prompt 模板
- 限制 Agent 系统指令修改权限

### 5.4 二次校验机制

薪资等涉及资金变动的核心操作实行二次校验:
1. Agent 完成初算 → 生成核算底稿
2. 推送人事专员审核 → 人事确认无误
3. 二次校验: 系统自动复算关键数值
4. 复算一致 → 放行; 不一致 → 告警

### 5.5 操作审计

所有操作计入不可篡改的审计日志:

| 字段 | 说明 |
|------|------|
| 操作时间 | 精确到秒 |
| 操作人 | 账号 + 真实姓名 |
| 操作者 IP | IPv4/IPv6 |
| 操作类型 | 新增/修改/删除/查看/导出/登录/登出/Auto-Agent |
| 操作模块 | 招聘/入职/培训/考勤/薪资/绩效/外务/离职 |
| 操作对象 | 对象 ID + 名称 |
| 变更前快照 | JSON |
| 变更后快照 | JSON |
| 结果 | 成功/失败 |
| 耗时 | 精确到毫秒 |

---

## 6. Agent 执行框架

### 6.1 Agent 基类

```java
public abstract class BaseAgent implements Agent {
    
    protected final AgentRegistry registry;
    protected final ReasoningTraceService traceService;
    protected final GuardrailChain guardrails;
    
    @Override
    public final AgentResult execute(AgentContext ctx) {
        // 1. 记录开始
        traceService.start(ctx.getAgentName(), ctx.getTraceId());
        
        // 2. 执行前护栏检查
        guardrails.checkBefore(ctx);
        
        try {
            // 3. 执行具体业务逻辑 (由子类实现)
            AgentResult result = doExecute(ctx);
            
            // 4. 执行后护栏检查
            guardrails.checkAfter(ctx, result);
            
            // 5. 记录成功
            traceService.success(ctx.getTraceId(), result);
            return result;
        } catch (Exception e) {
            // 6. 记录失败
            traceService.fail(ctx.getTraceId(), e);
            throw new AgentExecutionException(this.getClass().getSimpleName(), e);
        }
    }
    
    protected abstract AgentResult doExecute(AgentContext ctx);
}
```

### 6.2 重试策略

```java
public class AgentRetryPolicy {
    // 指数退避: 5s, 15s, 60s
    private static final List<Duration> BACKOFF = List.of(
        Duration.ofSeconds(5),
        Duration.ofSeconds(15),
        Duration.ofSeconds(60)
    );
    
    public static final int MAX_RETRIES = 3;
    
    public AgentResult executeWithRetry(Agent agent, AgentContext ctx) {
        for (int i = 0; i <= MAX_RETRIES; i++) {
            try {
                return agent.execute(ctx);
            } catch (TransientException e) {
                if (i == MAX_RETRIES) {
                    ctx.suspend("重试耗尽，需人工处理");
                    alarmService.notify(ctx);
                    throw new AgentExhaustedException(agent, e);
                }
                Thread.sleep(BACKOFF.get(i).toMillis());
            }
        }
    }
}
```

### 6.3 断点恢复

流程状态持久化:

```java
public interface FlowStateRepository {
    void save(FlowState state);           // 保存流程状态
    FlowState get(String flowId);         // 获取流程状态
    FlowState resumeFrom(String flowId);  // 从断点恢复
    void complete(String flowId);         // 标记流程完成
}
```

每个业务流程拥有唯一 UUID，每一步执行后状态持久化，Agent 崩溃后可在断点恢复。

---

## 7. 定时任务

| 任务 | 频率 | 执行 Agent |
|------|------|-----------|
| 简历抓取 | 每 15 分钟 | RecruitmentChannelAgent |
| 考勤数据同步 | 每 1 小时 | AttendanceAgent |
| 证书到期扫描 | 每日 08:00 | TrainingAgent |
| 月度薪资核算 | 每月 25 日 00:00 | PayrollAgent |
| RPA 可用性验证 | 每周一次 | RPAAgent |
| 简历偏见测试 | 每季度一次 | ResumeMatchAgent |
| 备份任务 | 每日/每周 | 系统调度 |
| 审计日志归档 | 每月 | 系统调度 |

---

## 8. 降级策略

| 失效场景 | 降级方案 | 实现方式 |
|---------|---------|---------|
| LLM 不可用 | 关键词正则匹配 | ResumeMatchAgent 切换到 KeywordMatcher |
| OCR 不可用 | 人工录入 | 前端切换为表单输入模式 |
| 人脸比对宕机 | 身份证 + 短信验证码 | FaceAgent 跳过，改用 SMS 验证 |
| 编排层异常 | 手动调度 | 控制台手动触发单个 Agent |
| RPA 被拦截 | 外务专员手工操作 | RPAAgent 生成预填数据导出 |
| DB 主库宕机 | 切换从库 | 自动 Failover (15 分钟内) |

降级期间所有人工操作完整记录至审计日志，降级原因和持续时间纳入月度运维报告。

---

*文档结束*
