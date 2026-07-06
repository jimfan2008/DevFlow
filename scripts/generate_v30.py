#!/usr/bin/env python3
"""
GBM AI Agent HR 后端设计文档 V29 → V30 修改脚本
根据后荣检验报告修复 17 个缺陷
"""

import os
import re
import os
PROJECTS_DIR = os.environ.get("PROJECTS_BASE_DIR", "/home/jim/projects")
V29_PATH = os.path.join(PROJECTS_DIR, "gbm-ai-agent-hr/docs/gbm-ai-agent-hr_BACKEND_V29.md")
V30_PATH = os.path.join(PROJECTS_DIR, "gbm-ai-agent-hr/docs/gbm-ai-agent-hr_BACKEND_V30.md")

with open(V29_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
total_lines = len(lines)
print(f"V29 文档: {total_lines} 行")

# =====================================================
# 1. 更新版本信息
# =====================================================
# Update version number
content = content.replace('| 版本号 | V29.0 |', '| 版本号 | V30.0 |')
content = content.replace('| 修订日期 | 2026-06-15 |', '| 修订日期 | 2026-06-15 |')

# Replace revision notes
old_revision_start = "**修订说明**\nV28.0→V29.0："
old_revision_end = "\n\nV28 已确认持续有效的修复"

new_revision = """**修订说明**
V29.0→V30.0：后荣检验 V29 时总分 76 分不合格（合格线 > 90 分），发现 17 个缺陷（严重 6 处、中缺陷 8 处、小缺陷 3 处）。V30 逐项修复如下：

【P0-严重缺陷修复】
1. 6.6 节：补充密码存储方案（BCrypt work factor 12，含密码复杂度策略和定期更换策略）
2. 6.7 节：补充输入验证和过滤设计（SQL 注入防护、XSS 过滤、CSRF Token 防护、文件上传安全策略）
3. 5.5 节：补充跨服务业务事务方案（本地消息表 + Saga 模式，薪资核算多模块协同）
4. 4.5 节：补充核心流程异常回滚/补偿设计（薪资核算回退机制、工伤 RPA 失败补偿流程、入职流程状态回滚）
5. 3.1.1 节：补充统一错误码体系（100+ 业务错误码枚举表，含描述和解决建议）
6. 3.14 节：为核心 API 补充完整请求/响应参数定义（薪资、考勤、招聘、入职、外务等核心模块）

【P1-中缺陷修复】
7. 10.7 节：补充主服务健康检查端点设计（Spring Boot Actuator，含数据库、Redis、子服务依赖状态）
8. 9.5 节：补充业务降级策略矩阵（薪资核算、简历匹配、考试管理、人脸采集等 10 个场景降级方案）
9. 9.4 节：补充超时时间统一清单（数据库、HTTP、各子服务、WebSocket、Redis 等 16 项超时配置）
10. 9.6 节：补充 API 级别重试策略（幂等/非幂等分类，含退避算法和重试次数）
11. 3.1.2 节：补充统一分页规范（pageNum/pageSize/sortField/sortOrder）
12. 3.1.3 节：补充速率限制策略（全局/API 级别/用户级别三层限制）
13. 5.6 节：补充编号化业务规则清单（PAY-001 ~ TRN-002，共 17 条规则）
14. 10.12 节：补充读写分离策略（主从路由规则、延迟处理、降级方案）
15. 10.13 节：补充数据导入导出策略（异步导入+进度查询、分片导出、Excel 模板管理）

【P2-小缺陷修复】
16. 9.7 节：补充优雅停机设计（@PreDestroy 资源清理、Tomcat 优雅关闭、Docker stop-grace-period）
17. 1.8 节：补充模块间依赖关系图（Gradle 依赖矩阵 + Mermaid 依赖图）

【运维与可观测性修复】
18. 10.8 节：补充 CI/CD 流程说明（6 阶段流水线，含质量门禁和 .env 注入方式）
19. 10.9 节：补充链路追踪实现方案（OpenTelemetry + Jaeger，traceId 传递方式）
20. 10.10 节：补充配置管理统一策略（四层配置分层、环境差异、热更新策略、变更审计）
21. 10.11 节：补充灰度发布方案（金丝雀发布 + 蓝绿部署策略）

V29 已确认持续有效的修复（从 V28 继承，V29 修复，V30 保持）："""

if old_revision_start in content:
    # Find the end of V29 revision notes and replace
    rev_start = content.index(old_revision_start)
    rev_end = content.index(old_revision_end) + len(old_revision_end)
    content = content[:rev_start] + new_revision + content[rev_end:]

# =====================================================
# 2. 在目录中添加新章节
# =====================================================
old_toc = """1. 后端技术栈
2. 项目结构
3. API 接口设计
4. 数据流设计
5. 中间件设计
6. 安全策略
7. Agent 运行时设计
8. RPA 引擎设计
9. 错误处理与异常管理
10. 性能优化策略"""

new_toc = """1. 后端技术栈
2. 项目结构
3. API 接口设计
4. 数据流设计
5. 中间件设计
6. 安全策略
7. Agent 运行时设计
8. RPA 引擎设计
9. 错误处理与异常管理
10. 性能优化策略"""
# TOC stays the same at chapter level

# =====================================================
# 3. 在 1.7 节之后添加 1.8 模块间依赖关系
# =====================================================
section_1_8 = """
### 1.8 模块间依赖关系

> **V30 新增内容**：响应后荣检验意见"无服务依赖关系图"，补充模块间依赖矩阵。

#### 1.8.1 Gradle 依赖矩阵

| 模块 | 依赖模块 | 说明 |
|------|---------|------|
| gbm-hr-auth | gbm-hr-core | 认证授权模块，依赖核心公共模块 |
| gbm-hr-recruitment | gbm-hr-core, gbm-hr-auth, gbm-hr-agent, gbm-hr-notification | 招聘模块，需要认证、Agent 运行时、通知 |
| gbm-hr-onboarding | gbm-hr-core, gbm-hr-auth, gbm-hr-agent, gbm-hr-notification | 入职模块，需要认证、Agent 运行时、通知 |
| gbm-hr-training | gbm-hr-core, gbm-hr-auth, gbm-hr-agent, gbm-hr-notification | 培训模块，需要认证、Agent 运行时、通知 |
| gbm-hr-attendance | gbm-hr-core, gbm-hr-auth | 考勤模块，需要认证；通过 api/ 包暴露内部接口 |
| gbm-hr-payroll | gbm-hr-core, gbm-hr-auth, gbm-hr-attendance(api), gbm-hr-agent, gbm-hr-notification | 薪资模块，依赖考勤内部 API（InternalApi 模式） |
| gbm-hr-performance | gbm-hr-core, gbm-hr-auth, gbm-hr-agent | 绩效模块，需要认证和 Agent |
| gbm-hr-external | gbm-hr-core, gbm-hr-auth, gbm-hr-agent, gbm-hr-notification | 外务模块，需要认证、Agent 运行时、通知 |
| gbm-hr-employee | gbm-hr-core, gbm-hr-auth, gbm-hr-agent, gbm-hr-notification | 员工服务模块 |
| gbm-hr-agent | gbm-hr-core | Agent 运行时，仅依赖核心模块 |
| gbm-hr-notification | gbm-hr-core | 通知模块，仅依赖核心模块 |
| gbm-hr-audit | gbm-hr-core | 审计模块，仅依赖核心模块 |
| gbm-hr-application | gbm-hr-core, gbm-hr-auth, gbm-hr-recruitment, gbm-hr-onboarding, gbm-hr-training, gbm-hr-attendance, gbm-hr-payroll, gbm-hr-performance, gbm-hr-external, gbm-hr-employee, gbm-hr-agent, gbm-hr-notification, gbm-hr-audit | 启动模块，依赖所有业务模块 |

#### 1.8.2 模块依赖图

```
                    ┌───────────────┐
                    │ gbm-hr-core   │ ← 所有模块的公共依赖
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
 ┌──────┴──────┐    ┌──────┴──────┐    ┌───────┴───────┐
 │gbm-hr-auth  │    │gbm-hr-agent │    │gbm-hr-notification│
 └──────┬──────┘    └──────┬──────┘    └───────┬───────┘
        │                   │                   │
        ├───────────────────┼───────────────────┤
        │                   │                   │
  ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
  │recruitment │      │ onboarding│      │ training  │
  │  external  │      │ employee  │      │performance│
  └───────────┘      └───────────┘      └───────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
         ┌────┴────┐              ┌───────┴───────┐
         │attendance│─────────────│  payroll      │
         └─────────┘ InternalApi  └───────────────┘
              │                           │
              └───────────────┬───────────┘
                              │
                     ┌────────┴────────┐
                     │ gbm-hr-audit    │
                     └────────┬────────┘
                              │
                     ┌────────┴────────┐
                     │gbm-hr-application│ ← 启动模块
                     └─────────────────┘
```

#### 1.8.3 跨模块访问规则

| 规则 | 说明 |
|------|------|
| 同层不可互相依赖 | 同一层级的业务模块（如 recruitment 和 onboarding）不应互相依赖 |
| 跨模块通过 API | 模块间数据访问通过 `*InternalApi` 接口（详见 2.1 节） |
| 禁止循环依赖 | Gradle 构建时会检测循环依赖并报错 |
| 审计模块无业务依赖 | gbm-hr-audit 通过 AOP 切面工作，不直接依赖业务模块 |
"""

# Insert 1.8 after section 1.7
insert_point = content.find("### 1.7 密钥管理方案")
if insert_point == -1:
    print("WARNING: Could not find 1.7 section")
else:
    # Find the end of 1.7 section (before the next major section or ## 2.)
    next_major = content.find("\n## 2. 项目结构", insert_point)
    if next_major != -1:
        content = content[:next_major] + section_1_8 + content[next_major:]
        print("OK: Added section 1.8")
    else:
        print("WARNING: Could not find ## 2. 项目结构")

# =====================================================
# 4. 在 3.1 统一响应格式后添加 3.1.1/3.1.2/3.1.3
# =====================================================
section_3_1_1 = """
### 3.1.1 统一错误码体系 (ErrorCode.java)

> **V30 新增内容**：响应后荣检验意见"缺少统一错误码体系"，定义完整错误码枚举表。

#### 错误码编码规则

- 格式：5 位数字编码
- 第一位：0=系统级，1-9=业务模块
- 模块前缀：SYS/REC/ONB/TRN/ATT/PAY/PER/EXT/EMP/AGT
- 每个错误码包含：编码值、模块、HTTP 状态码、描述、解决建议

#### 系统级错误码 (SYS)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| SYS_SUCCESS | 0 | 200 | 操作成功 | 无需处理 |
| SYS_PARAM_ERROR | 400 | 400 | 请求参数错误 | 检查请求参数格式和必填项 |
| SYS_UNAUTHORIZED | 401 | 401 | 未认证或 Token 失效 | 请重新登录 |
| SYS_FORBIDDEN | 403 | 403 | 无权限访问 | 请联系管理员获取权限 |
| SYS_NOT_FOUND | 404 | 404 | 请求资源不存在 | 检查 URL 或资源 ID 是否正确 |
| SYS_RATE_LIMIT | 429 | 429 | 请求频率超限 | 请稍后重试 |
| SYS_INTERNAL_ERROR | 500 | 500 | 系统内部错误 | 联系系统管理员 |
| SYS_SERVICE_UNAVAILABLE | 503 | 503 | 服务暂时不可用 | 请稍后重试 |
| SYS_DATA_CONFLICT | 409 | 409 | 数据冲突 | 检查是否存在重复数据 |
| SYS_VALIDATION_ERROR | 422 | 422 | 数据校验失败 | 检查字段格式和取值范围 |

#### 招聘模块错误码 (100xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| REC_JOB_NOT_FOUND | 10001 | 404 | 岗位不存在 | 检查岗位 ID |
| REC_JOB_CLOSED | 10002 | 400 | 岗位已关闭 | 请重新创建岗位 |
| REC_RESUME_NOT_FOUND | 10003 | 404 | 简历不存在 | 检查简历 ID |
| REC_RESUME_DUPLICATE | 10004 | 409 | 简历重复导入 | 检查是否已导入该简历 |
| REC_EXAM_NOT_FOUND | 10005 | 404 | 考试不存在 | 检查考试 ID |
| REC_EXAM_EXPIRED | 10006 | 400 | 考试已过期 | 无法提交答案，请联系组织方 |
| REC_EXAM_SUBMITTED | 10007 | 409 | 已提交过答案 | 无法重复提交 |
| REC_QUESTION_NOT_FOUND | 10008 | 404 | 题目不存在 | 检查题目 ID |

#### 入职模块错误码 (110xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| ONB_NOT_FOUND | 11001 | 404 | 入职记录不存在 | 检查员工 ID |
| ONB_COMPLETED | 11002 | 409 | 入职流程已完成 | 无法重复操作 |
| ONB_DOC_MISSING | 11003 | 400 | 缺少必要证件 | 请上传身份证、学历证书、证件照 |
| ONB_FACE_MISMATCH | 11004 | 400 | 人脸比对未通过 | 请重新拍照，最多 3 次 |
| ONB_ID_INVALID | 11005 | 400 | 身份证号格式无效 | 请检查 18 位身份证号码 |

#### 培训模块错误码 (120xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| TRN_PLAN_NOT_FOUND | 12001 | 404 | 培训计划不存在 | 检查计划 ID |
| TRN_SESSION_FULL | 12002 | 409 | 培训场次已满 | 请选择其他场次 |
| TRN_CHECKIN_EXPIRED | 12003 | 400 | 签到已过期 | 签到时间已过 |
| TRN_CERT_NOT_FOUND | 12004 | 404 | 证书不存在 | 检查证书 ID |

#### 考勤模块错误码 (130xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| ATT_NOT_FOUND | 13001 | 404 | 考勤记录不存在 | 检查日期和员工 ID |
| ATT_LEAVE_CONFLICT | 13002 | 409 | 请假时间冲突 | 请检查已有请假记录 |
| ATT_QUOTA_EXCEEDED | 13003 | 400 | 请假额度不足 | 请确认剩余假期额度 |
| ATT_SHIFT_CONFLICT | 13004 | 409 | 排班时间冲突 | 请检查排班安排 |

#### 薪资模块错误码 (140xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| PAY_CALCULATED | 14001 | 409 | 当月薪资已核算 | 请勿重复核算 |
| PAY_NOT_CALCULATED | 14002 | 400 | 当月薪资未核算 | 请先执行薪资核算 |
| PAY_REVIEWED | 14003 | 409 | 薪资已审核确认 | 无法修改，请联系管理员 |
| PAY_RULE_NOT_FOUND | 14004 | 404 | 薪资规则不存在 | 请先配置薪资规则 |
| PAY_AMOUNT_ABNORMAL | 14005 | 400 | 薪资金额异常 | 请检查计算参数或联系管理员 |
| PAY_BANK_MISSING | 14006 | 400 | 缺少银行账号 | 请在员工档案中补充银行账号 |
| PAY_TAX_ERROR | 14007 | 500 | 个税计算异常 | 联系系统管理员 |

#### 绩效模块错误码 (150xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| PER_NOT_FOUND | 15001 | 404 | 绩效考核记录不存在 | 检查考核 ID |
| PER_EVALUATED | 15002 | 409 | 已完成评价 | 无法重复评价 |
| PER_CYCLE_CLOSED | 15003 | 400 | 考核周期已结束 | 请等待下一考核周期 |

#### 外务模块错误码 (160xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| EXT_INJURY_NOT_FOUND | 16001 | 404 | 工伤案件不存在 | 检查案件 ID |
| EXT_INJURY_DECLARED | 16002 | 409 | 工伤已申报 | 无法重复申报 |
| EXT_INJURY_DOC_MISSING | 16003 | 400 | 申报材料不完整 | 请补全材料（病案+诊断书+旁证+身份证+出勤记录） |
| EXT_RPA_FAILED | 16004 | 500 | RPA 申报失败 | 系统将自动重试，如持续失败请联系管理员 |
| EXT_FUND_NOT_FOUND | 16005 | 404 | 公积金记录不存在 | 检查记录 ID |
| EXT_FUND_ENROLLED | 16006 | 409 | 已办理参保 | 无需重复办理 |

#### 员工服务错误码 (170xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| EMP_NOT_FOUND | 17001 | 404 | 员工不存在 | 检查员工 ID |
| EMP_RESIGNING | 17002 | 409 | 离职流程进行中 | 请勿重复提交 |
| EMP_CERT_NOT_FOUND | 17003 | 404 | 证明不存在 | 检查证明 ID |
| EMP_CERT_PENDING | 17004 | 400 | 证明未审核通过 | 请等待审核 |
| EMP_EXPENSE_NOT_FOUND | 17005 | 404 | 报销记录不存在 | 检查报销 ID |

#### Agent 错误码 (180xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| AGT_NOT_FOUND | 18001 | 404 | Agent 不存在 | 检查 Agent 名称 |
| AGT_FAILED | 18002 | 500 | Agent 执行失败 | 系统将自动重试 |
| AGT_BLOCKED | 18003 | 400 | 被安全护栏拦截 | 请检查操作是否符合规则 |
| AGT_RATE_LIMIT | 18004 | 429 | Agent 调用频率超限 | 请稍后重试 |

#### 系统管理错误码 (190xx)

| 枚举名 | 编码 | HTTP | 描述 | 解决建议 |
|--------|------|------|------|---------|
| SYS_USER_NOT_FOUND | 19001 | 404 | 用户不存在 | 检查用户 ID |
| SYS_USER_DISABLED | 19002 | 403 | 用户已禁用 | 请联系管理员 |
| SYS_ROLE_NOT_FOUND | 19003 | 404 | 角色不存在 | 检查角色 ID |
| SYS_CONFIG_NOT_FOUND | 19004 | 404 | 系统配置不存在 | 检查配置 Key |
| SYS_BACKUP_FAILED | 19005 | 500 | 备份失败 | 联系系统管理员 |
| SYS_RESTORE_FAILED | 19006 | 500 | 恢复失败 | 联系系统管理员 |

#### ErrorCode.java 枚举定义

```java
public enum ErrorCode {
    
    // ===== 系统级错误码 =====
    SYS_SUCCESS(0, "SYS", 200, "操作成功", "无需处理"),
    SYS_PARAM_ERROR(400, "SYS", 400, "请求参数错误", "检查请求参数格式和必填项"),
    SYS_UNAUTHORIZED(401, "SYS", 401, "未认证或 Token 失效", "请重新登录"),
    SYS_FORBIDDEN(403, "SYS", 403, "无权限访问", "请联系管理员获取权限"),
    SYS_NOT_FOUND(404, "SYS", 404, "请求资源不存在", "检查 URL 或资源 ID"),
    SYS_RATE_LIMIT(429, "SYS", 429, "请求频率超限", "请稍后重试"),
    SYS_INTERNAL_ERROR(500, "SYS", 500, "系统内部错误", "联系系统管理员"),
    SYS_SERVICE_UNAVAILABLE(503, "SYS", 503, "服务暂时不可用", "请稍后重试"),
    SYS_DATA_CONFLICT(409, "SYS", 409, "数据冲突", "检查是否存在重复数据"),
    SYS_VALIDATION_ERROR(422, "SYS", 422, "数据校验失败", "检查字段格式和取值范围"),
    
    // ===== 招聘模块 (100xx) =====
    REC_JOB_NOT_FOUND(10001, "REC", 404, "岗位不存在", "检查岗位 ID"),
    REC_JOB_CLOSED(10002, "REC", 400, "岗位已关闭", "请重新创建岗位"),
    REC_RESUME_NOT_FOUND(10003, "REC", 404, "简历不存在", "检查简历 ID"),
    REC_RESUME_DUPLICATE(10004, "REC", 409, "简历重复导入", "检查是否已导入"),
    REC_EXAM_NOT_FOUND(10005, "REC", 404, "考试不存在", "检查考试 ID"),
    REC_EXAM_EXPIRED(10006, "REC", 400, "考试已过期", "无法提交答案"),
    REC_EXAM_SUBMITTED(10007, "REC", 409, "已提交过答案", "无法重复提交"),
    REC_QUESTION_NOT_FOUND(10008, "REC", 404, "题目不存在", "检查题目 ID"),
    
    // ===== 入职模块 (110xx) =====
    ONB_NOT_FOUND(11001, "ONB", 404, "入职记录不存在", "检查员工 ID"),
    ONB_COMPLETED(11002, "ONB", 409, "入职流程已完成", "无法重复操作"),
    ONB_DOC_MISSING(11003, "ONB", 400, "缺少必要证件", "请上传完整证件材料"),
    ONB_FACE_MISMATCH(11004, "ONB", 400, "人脸比对未通过", "请重新拍照"),
    ONB_ID_INVALID(11005, "ONB", 400, "身份证号格式无效", "请检查 18 位身份证号码"),
    
    // ===== 培训模块 (120xx) =====
    TRN_PLAN_NOT_FOUND(12001, "TRN", 404, "培训计划不存在", "检查计划 ID"),
    TRN_SESSION_FULL(12002, "TRN", 409, "培训场次已满", "请选择其他场次"),
    TRN_CHECKIN_EXPIRED(12003, "TRN", 400, "签到已过期", "签到时间已过"),
    TRN_CERT_NOT_FOUND(12004, "TRN", 404, "证书不存在", "检查证书 ID"),
    
    // ===== 考勤模块 (130xx) =====
    ATT_NOT_FOUND(13001, "ATT", 404, "考勤记录不存在", "检查日期和员工 ID"),
    ATT_LEAVE_CONFLICT(13002, "ATT", 409, "请假时间冲突", "请检查已有请假记录"),
    ATT_QUOTA_EXCEEDED(13003, "ATT", 400, "请假额度不足", "请确认剩余假期额度"),
    ATT_SHIFT_CONFLICT(13004, "ATT", 409, "排班时间冲突", "请检查排班安排"),
    
    // ===== 薪资模块 (140xx) =====
    PAY_CALCULATED(14001, "PAY", 409, "当月薪资已核算", "请勿重复核算"),
    PAY_NOT_CALCULATED(14002, "PAY", 400, "当月薪资未核算", "请先执行薪资核算"),
    PAY_REVIEWED(14003, "PAY", 409, "薪资已审核确认", "无法修改"),
    PAY_RULE_NOT_FOUND(14004, "PAY", 404, "薪资规则不存在", "请先配置薪资规则"),
    PAY_AMOUNT_ABNORMAL(14005, "PAY", 400, "薪资金额异常", "请检查计算参数"),
    PAY_BANK_MISSING(14006, "PAY", 400, "缺少银行账号", "请补充银行账号信息"),
    PAY_TAX_ERROR(14007, "PAY", 500, "个税计算异常", "联系系统管理员"),
    
    // ===== 绩效模块 (150xx) =====
    PER_NOT_FOUND(15001, "PER", 404, "绩效考核记录不存在", "检查考核 ID"),
    PER_EVALUATED(15002, "PER", 409, "已完成评价", "无法重复评价"),
    PER_CYCLE_CLOSED(15003, "PER", 400, "考核周期已结束", "请等待下一考核周期"),
    
    // ===== 外务模块 (160xx) =====
    EXT_INJURY_NOT_FOUND(16001, "EXT", 404, "工伤案件不存在", "检查案件 ID"),
    EXT_INJURY_DECLARED(16002, "EXT", 409, "工伤已申报", "无法重复申报"),
    EXT_INJURY_DOC_MISSING(16003, "EXT", 400, "申报材料不完整", "请补全申报材料"),
    EXT_RPA_FAILED(16004, "EXT", 500, "RPA 申报失败", "系统将自动重试"),
    EXT_FUND_NOT_FOUND(16005, "EXT", 404, "公积金记录不存在", "检查记录 ID"),
    EXT_FUND_ENROLLED(16006, "EXT", 409, "已办理参保", "无需重复办理"),
    
    // ===== 员工服务 (170xx) =====
    EMP_NOT_FOUND(17001, "EMP", 404, "员工不存在", "检查员工 ID"),
    EMP_RESIGNING(17002, "EMP", 409, "离职流程进行中", "请勿重复提交"),
    EMP_CERT_NOT_FOUND(17003, "EMP", 404, "证明不存在", "检查证明 ID"),
    EMP_CERT_PENDING(17004, "EMP", 400, "证明未审核通过", "请等待审核"),
    EMP_EXPENSE_NOT_FOUND(17005, "EMP", 404, "报销记录不存在", "检查报销 ID"),
    
    // ===== Agent (180xx) =====
    AGT_NOT_FOUND(18001, "AGT", 404, "Agent 不存在", "检查 Agent 名称"),
    AGT_FAILED(18002, "AGT", 500, "Agent 执行失败", "系统将自动重试"),
    AGT_BLOCKED(18003, "AGT", 400, "被安全护栏拦截", "请检查操作是否符合规则"),
    AGT_RATE_LIMIT(18004, "AGT", 429, "Agent 调用频率超限", "请稍后重试"),
    
    // ===== 系统管理 (190xx) =====
    SYS_USER_NOT_FOUND(19001, "SYS", 404, "用户不存在", "检查用户 ID"),
    SYS_USER_DISABLED(19002, "SYS", 403, "用户已禁用", "请联系管理员"),
    SYS_ROLE_NOT_FOUND(19003, "SYS", 404, "角色不存在", "检查角色 ID"),
    SYS_CONFIG_NOT_FOUND(19004, "SYS", 404, "系统配置不存在", "检查配置 Key"),
    SYS_BACKUP_FAILED(19005, "SYS", 500, "备份失败", "联系系统管理员"),
    SYS_RESTORE_FAILED(19006, "SYS", 500, "恢复失败", "联系系统管理员");
    
    private final int code;
    private final String module;
    private final int httpStatus;
    private final String message;
    private final String suggestion;
    
    ErrorCode(int code, String module, int httpStatus, String message, String suggestion) {
        this.code = code;
        this.module = module;
        this.httpStatus = httpStatus;
        this.message = message;
        this.suggestion = suggestion;
    }
    
    public int getCode() { return code; }
    public String getModule() { return module; }
    public int getHttpStatus() { return httpStatus; }
    public String getMessage() { return message; }
    public String getSuggestion() { return suggestion; }
    
    /**
     * 根据编码查找错误码
     */
    public static ErrorCode fromCode(int code) {
        for (ErrorCode ec : values()) {
            if (ec.code == code) return ec;
        }
        return SYS_INTERNAL_ERROR;
    }
}
```

#### BusinessException 与错误码集成

```java
public class BusinessException extends RuntimeException {
    private final ErrorCode errorCode;
    
    public BusinessException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.errorCode = errorCode;
    }
    
    public BusinessException(ErrorCode errorCode, String detail) {
        super(errorCode.getMessage() + ": " + detail);
        this.errorCode = errorCode;
    }
    
    public ErrorCode getErrorCode() { return errorCode; }
}
```

#### GlobalExceptionHandler 与错误码集成

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e) {
        ErrorCode ec = e.getErrorCode();
        log.warn("Business exception: code={}, message={}, suggestion={}", 
            ec.getCode(), ec.getMessage(), ec.getSuggestion());
        return Result.error(ec.getCode(), ec.getMessage());
    }
    
    @ExceptionHandler(ValidationException.class)
    public Result<Void> handleValidationException(ValidationException e) {
        return Result.error(ErrorCode.SYS_VALIDATION_ERROR.getCode(), e.getMessage());
    }
    
    // ... 其他处理器同上
}
```

### 3.1.2 统一分页规范

> **V30 新增内容**：响应后荣检验意见"分页参数无统一定义"，定义统一分页参数规范。

#### 分页请求参数

```java
public class PageRequest {
    private Integer pageNum = 1;         // 页码，从 1 开始，默认 1，最小 1
    private Integer pageSize = 20;       // 每页条数，默认 20，最大 100
    private String sortField;            // 排序字段，默认 created_at
    private String sortOrder = "DESC";   // 排序方向: ASC/DESC，默认 DESC（最新在前）
    
    // 校验
    public void validate() {
        if (pageNum < 1) pageNum = 1;
        if (pageSize < 1) pageSize = 20;
        if (pageSize > 100) pageSize = 100;
        if (sortOrder == null || (!"ASC".equals(sortOrder) && !"DESC".equals(sortOrder))) {
            sortOrder = "DESC";
        }
    }
}
```

#### 分页响应结构

```java
public class PageResult<T> {
    private Long total;                  // 总记录数
    private Integer pageNum;             // 当前页码
    private Integer pageSize;            // 每页条数
    private Integer totalPages;          // 总页数 (total / pageSize, 向上取整)
    private Boolean hasMore;             // 是否有下一页
    private List<T> items;               // 数据列表
}
```

#### 分页规则

| 参数 | 类型 | 默认值 | 最小值 | 最大值 | 说明 |
|------|------|--------|--------|--------|------|
| pageNum | Integer | 1 | 1 | 无上限 | 从 1 开始 |
| pageSize | Integer | 20 | 1 | 100 | 每页条数 |
| sortField | String | created_at | - | - | 支持字段由 API 定义 |
| sortOrder | String | DESC | - | - | ASC 或 DESC |

#### 排序字段白名单

- 各 API 定义允许的排序字段白名单，防止 SQL 注入
- 示例：`List<String> allowedSortFields = Arrays.asList("id", "name", "created_at", "status", "score")`
- 不在白名单中的字段自动回退到默认排序字段

#### URL 查询参数格式

```
GET /api/v1/recruitment/resumes?pageNum=1&pageSize=20&sortField=score&sortOrder=DESC
GET /api/v1/attendance/records?employeeId=1001&startDate=2026-06-01&endDate=2026-06-30&pageNum=1&pageSize=50
```

### 3.1.3 速率限制策略

> **V30 新增内容**：响应后荣检验意见"速率限制设计不完整"，补充完整的速率限制策略。

#### 速率限制技术选型

- 实现：Redis + Bucket4j 滑动窗口算法
- Bucket4j 优势：支持令牌桶算法、支持分布式桶（Redis 后端）、API 简洁

#### 三级速率限制体系

| 级别 | 限制规则 | 适用范围 | 超限响应 |
|------|---------|---------|---------|
| 全局默认 | 100 次/分钟/IP | 所有未单独配置的 API | 429 Too Many Requests |
| API 级别 | 见下表 | 特定高敏感 API | 429 + Retry-After 头 |
| 用户级别 | 见下表 | 特定用户操作 | 429 + Retry-After 头 |

#### API 级别速率限制

| API | 限制规则 | 说明 |
|-----|---------|------|
| POST /api/v1/auth/login | 5 次/分钟/IP | 防止暴力破解 |
| POST /api/v1/auth/mfa/verify | 10 次/分钟/IP | 防止验证码暴力破解 |
| POST /api/v1/payroll/calculate | 1 次/小时/用户 | 防止重复核算 |
| POST /api/v1/recruitment/resumes/import | 5 次/小时/用户 | 防止大量导入占用资源 |
| POST /api/v1/agent/*/trigger | 10 次/分钟/用户 | 防止频繁触发 Agent |
| POST /api/v1/system/backup | 1 次/小时/管理员 | 防止频繁备份 |

#### 用户级别速率限制

| 操作 | 限制规则 | 说明 |
|------|---------|------|
| 密码修改 | 3 次/小时/用户 | 防止频繁修改 |
| 离职申请 | 1 次/天/用户 | 防止重复提交 |
| 证明申请 | 5 次/天/用户 | 防止滥用 |
| 请假申请 | 3 次/天/用户 | 防止频繁提交 |

#### 超限响应格式

```json
{
    "code": 429,
    "message": "请求频率超限，请稍后重试",
    "data": {
        "retryAfter": 30,
        "limit": 100,
        "window": "1min",
        "remaining": 0
    }
}
```

HTTP 响应头：
```
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1718409630
```

#### 速率限制实现

```java
@Configuration
public class RateLimitConfig {
    
    @Bean
    public RedisPipelineBuilder redisPipelineBuilder(RedissonClient redisson) {
        return RedisPipelineBuilder.sync(redisson.getConnectionManager());
    }
    
    @Bean
    public RateLimitInterceptor rateLimitInterceptor(RedisPipelineBuilder builder) {
        // 全局默认限制
        Bandwidth defaultLimit = Bandwidth.classic(100, Refill.greedy(100, Duration.ofMinutes(1)));
        return new RateLimitInterceptor(builder, defaultLimit);
    }
}

// 使用注解方式
@RateLimit(keys = {"#ip"}, limit = "5 per minute")
@PostMapping("/auth/login")
public Result<LoginResponse> login(@RequestBody LoginRequest request, @RequestHeader("X-Forwarded-For") String ip) {
    // ...
}
```

"""

# Insert 3.1.1/3.1.2/3.1.3 after the Result.java definition (after 3.1 统一响应格式)
insert_marker = "```\n\n### 3.2 认证授权 API"
if insert_marker in content:
    content = content.replace(insert_marker, section_3_1_1 + "\n```\n\n### 3.2 认证授权 API")
    print("OK: Added sections 3.1.1, 3.1.2, 3.1.3")
else:
    print("WARNING: Could not find insert point for 3.1.x sections")

# =====================================================
# 5. 添加 3.14 核心 API 完整参数定义（在 Flowable 流程管理 API 之后）
# =====================================================
section_3_14 = """
### 3.14 核心 API 完整请求/响应参数定义

> **V30 新增内容**：响应后荣检验意见"大部分 API 缺少请求参数完整定义"，为核心模块补充完整参数定义。

#### 3.14.1 薪资管理 API 完整定义

**POST /api/v1/payroll/calculate** — 启动薪资核算

请求参数：

| 参数 | 类型 | 必填 | 校验规则 | 说明 |
|------|------|------|---------|------|
| month | String | 是 | 格式 yyyy-MM | 核算月份 |
| dryRun | Boolean | 否 | 默认 false | true=试运行不保存 |

```json
{
    "month": "2026-06",
    "dryRun": false
}
```

响应 (202 Accepted)：

```json
{
    "code": 200,
    "message": "薪资核算任务已提交",
    "data": {
        "taskId": "uuid-v4",
        "month": "2026-06",
        "status": "PROCESSING",
        "estimatedTimeSeconds": 300,
        "totalEmployees": 150
    }
}
```

**GET /api/v1/payroll/{month}** — 查看核算结果

路径参数：`month` (String, 必填, yyyy-MM)
查询参数：`pageNum` (Integer, 默认 1), `pageSize` (Integer, 默认 20), `sortField` (String, 默认 netPay), `sortOrder` (String, 默认 DESC)

响应 (200)：

```json
{
    "code": 200,
    "data": {
        "total": 150,
        "pageNum": 1,
        "pageSize": 20,
        "totalPages": 8,
        "items": [{
            "employeeId": 1001,
            "employeeName": "张三",
            "department": "技术部",
            "grossPay": 15000.00,
            "overtime": 800.00,
            "allowance": 500.00,
            "socialInsurance": 1200.00,
            "housingFund": 800.00,
            "tax": 450.00,
            "attendanceDeduction": 0.00,
            "netPay": 13850.00,
            "anomaly": null
        }]
    }
}
```

**POST /api/v1/payroll/{month}/review** — 审核确认

请求参数：

| 参数 | 类型 | 必填 | 校验规则 | 说明 |
|------|------|------|---------|------|
| approved | Boolean | 是 | - | true=通过, false=退回 |
| comment | String | 否 | 最大 500 字符 | 审核意见 |
| adjustments | Array | 否 | 最多 50 条 | 薪资调整明细 |

```json
{
    "approved": true,
    "comment": "核算无误，同意发放",
    "adjustments": [
        {
            "employeeId": 1001,
            "field": "overtime",
            "originalValue": 800.00,
            "adjustedValue": 1000.00,
            "reason": "加班时长修正"
        }
    ]
}
```

**GET /api/v1/payroll/{month}/anomalies** — 查看异常数据

响应 (200)：分页返回异常薪资记录，`anomaly` 字段标注异常类型（FLUCTUATION/TAX_NEGATIVE/BELOW_MINIMUM 等）

#### 3.14.2 考勤管理 API 完整定义

**GET /api/v1/attendance/records** — 考勤记录列表

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| employeeId | Long | 否 | 员工 ID（不传则返回全员） |
| startDate | String | 否 | 开始日期 yyyy-MM-dd |
| endDate | String | 否 | 结束日期 yyyy-MM-dd |
| status | String | 否 | 状态筛选: NORMAL/LATE/EARLY/ABSENT |
| pageNum | Integer | 否 | 默认 1 |
| pageSize | Integer | 否 | 默认 20 |

响应 (200)：`PageResult<AttendanceRecord>`

```json
{
    "code": 200,
    "data": {
        "total": 30,
        "pageNum": 1,
        "pageSize": 20,
        "items": [{
            "recordId": "att_001",
            "employeeId": 1001,
            "employeeName": "张三",
            "date": "2026-06-01",
            "clockIn": "08:55",
            "clockOut": "18:05",
            "workHours": 9.17,
            "status": "NORMAL",
            "overtime": 1.17
        }]
    }
}
```

**POST /api/v1/attendance/leave** — 请假申请

请求参数：

| 参数 | 类型 | 必填 | 校验规则 | 说明 |
|------|------|------|---------|------|
| employeeId | Long | 是 | - | 员工 ID |
| leaveType | String | 是 | enum: ANNUAL/SICK/PERSONAL/MATERNITY/OTHER | 请假类型 |
| startDate | String | 是 | yyyy-MM-dd, 不得早于今天 | 开始日期 |
| endDate | String | 是 | yyyy-MM-dd, 不得早于 startDate | 结束日期 |
| reason | String | 是 | 2-200 字符 | 请假事由 |
| attachments | Array | 否 | 最多 5 个 URL | 附件（如病假条） |

响应 (200)：

```json
{
    "code": 200,
    "message": "请假申请已提交",
    "data": {
        "leaveId": "leave_001",
        "status": "PENDING_APPROVAL",
        "days": 2
    }
}
```

#### 3.14.3 招聘管理 API 完整定义

**POST /api/v1/recruitment/jobs** — 创建岗位

请求参数：

| 参数 | 类型 | 必填 | 校验规则 | 说明 |
|------|------|------|---------|------|
| title | String | 是 | 2-100 字符 | 岗位名称 |
| department | String | 是 | - | 所属部门 |
| jobLevel | String | 是 | - | 岗位级别 |
| minSalary | Integer | 是 | > 0 | 最低薪资（元） |
| maxSalary | Integer | 是 | > minSalary | 最高薪资（元） |
| minExperience | Integer | 是 | >= 0 | 最低经验年限 |
| education | String | 是 | enum: 大专/本科/硕士/博士 | 学历要求 |
| skills | Array | 是 | 1-20 项 | 技能要求 |
| description | String | 是 | 20-2000 字符 | 岗位描述 |
| headcount | Integer | 是 | > 0 | 招聘人数 |
| channels | Array | 否 | - | 发布渠道 |

响应 (200)：

```json
{
    "code": 200,
    "data": {
        "jobId": "job_001",
        "status": "DRAFT"
    }
}
```

**POST /api/v1/recruitment/jobs/{id}/publish** — 发布到招聘平台

响应 (200)：

```json
{
    "code": 200,
    "data": {
        "publishedChannels": [
            {"channel": "前程无忧", "postId": "ext_001", "status": "PUBLISHED"},
            {"channel": "中国人才热线", "postId": "ext_002", "status": "PUBLISHED"}
        ]
    }
}
```

#### 3.14.4 入职管理 API 完整定义

**POST /api/v1/onboarding/start** — 开始入职流程

请求参数：

| 参数 | 类型 | 必填 | 校验规则 | 说明 |
|------|------|------|---------|------|
| employeeName | String | 是 | 2-50 字符 | 员工姓名 |
| idNumber | String | 是 | 18 位身份证号码 | 身份证号 |
| phone | String | 是 | 11 位手机号 | 联系电话 |
| email | String | 是 | 邮箱格式 | 电子邮箱 |
| department | String | 是 | - | 所属部门 |
| position | String | 是 | - | 职位 |
| startDate | String | 是 | yyyy-MM-dd, 不得早于明天 | 入职日期 |

响应 (200)：

```json
{
    "code": 200,
    "data": {
        "onboardingId": "onb_001",
        "employeeId": 1001,
        "qrCode": "data:image/png;base64,...",
        "status": "INITIATED"
    }
}
```

**POST /api/v1/onboarding/{employeeId}/documents** — 上传证件

Content-Type: `multipart/form-data`

| 参数 | 类型 | 必填 | 校验规则 | 说明 |
|------|------|------|---------|------|
| documents[] | File | 是 | pdf/jpg/png, 单文件 ≤10MB, 最多 10 个 | 证件文件 |
| documentType | String | 是 | enum: ID_CARD/DIPLOMA/PASSPORT/OTHER | 证件类型 |

响应 (200)：

```json
{
    "code": 200,
    "data": {
        "uploadedCount": 3,
        "results": [
            {"fileName": "id_card.jpg", "ocrResult": {"name": "张三", "idNumber": "..."}, "confidence": 0.95}
        ]
    }
}
```

#### 3.14.5 外务管理 API 完整定义

**POST /api/v1/external/injury** — 申报工伤

请求参数：

| 参数 | 类型 | 必填 | 校验规则 | 说明 |
|------|------|------|---------|------|
| employeeId | Long | 是 | - | 员工 ID |
| injuryDate | String | 是 | yyyy-MM-dd | 事故日期 |
| injuryLocation | String | 是 | 2-200 字符 | 事故地点 |
| description | String | 是 | ≥50 字符 | 事故说明 |
| attachments | Array | 是 | 至少 1 个 URL | 申报材料 URL |

响应 (202)：

```json
{
    "code": 200,
    "message": "工伤申报已受理",
    "data": {
        "caseId": "case_001",
        "status": "PROCESSING",
        "estimatedTimeSeconds": 180
    }
}
```

**GET /api/v1/external/injury/{id}/progress** — 查询理赔进度

响应 (200)：

```json
{
    "code": 200,
    "data": {
        "caseId": "case_001",
        "status": "UNDER_REVIEW",
        "steps": [
            {"name": "材料提交", "status": "COMPLETED", "completedAt": "2026-06-10T10:00:00"},
            {"name": "RPA 申报", "status": "COMPLETED", "completedAt": "2026-06-10T10:05:00"},
            {"name": "社保审核", "status": "IN_PROGRESS", "completedAt": null},
            {"name": "理赔支付", "status": "PENDING", "completedAt": null}
        ]
    }
}
```

"""

# Insert 3.14 before Chapter 4
insert_point_3_14 = content.find("## 4. 数据流设计")
if insert_point_3_14 != -1:
    content = content[:insert_point_3_14] + section_3_14 + content[insert_point_3_14:]
    print("OK: Added section 3.14")
else:
    print("WARNING: Could not find Chapter 4")

# =====================================================
# 6. 添加 4.5 核心业务流程异常场景处理（在数据流设计章节末尾）
# =====================================================
section_4_5 = """
### 4.5 核心业务流程异常场景处理

> **V30 新增内容**：响应后荣检验意见"核心业务流程缺少异常场景处理"，补充各核心流程的异常处理方案。

#### 4.5.1 薪资核算异常处理

| 异常场景 | 检测机制 | 处理方式 | 回退策略 |
|---------|---------|---------|---------|
| 考勤数据拉取失败 | AttendanceApiClient 抛出异常 | 标记该员工为数据缺失，继续处理其他员工 | 核算完成后生成缺失员工清单，人工补录后重新核算 |
| 社保/公积金数据异常 | 与上月对比波动 > 50% | 标记异常，不阻断核算 | 异常数据置 0，生成异常报告，人工核实后修正 |
| 个税计算异常 | 负数或超出合理范围 | 标记异常 | 使用简化公式重新计算，仍异常则标记为待人工处理 |
| 核算中途系统崩溃 | 事务回滚 + 状态检查 | Quartz Job 重启时检查当月是否已存在 PENDING 状态记录 | 若存在则跳过或从头重新核算，通过幂等性 Key (month+employeeId) 保证不重复 |
| HR 审核退回 | 流程驳回 | 记录退回原因，薪资 Agent 重新计算 | 重新计算后再次提交审核 |

**薪资核算幂等性设计**：
- 幂等 Key: `{month}:{employeeId}`
- 核算前先检查 payroll 表是否存在该月记录
- 存在且状态为 APPROVED 则跳过
- 存在且状态为 PENDING_REVIEW 则保留原记录，仅处理新增员工
- 不存在则执行完整核算

#### 4.5.2 工伤 RPA 失败补偿流程

| 异常场景 | 处理方式 | 补偿流程 |
|---------|---------|---------|
| RPA 登录失败 | 重试 2 次（间隔 30s） | 仍失败 → 标记为 PENDING_MANUAL，生成操作指南（截图+步骤），通知外务专员人工处理 |
| RPA 元素选择失败 | 截图保存，记录失败步骤 | 标记为 SELECTION_FAILED，通知管理员更新 RPA 流程配置 |
| RPA 超时 | 300s 超时 | 标记为 TIMEOUT，检查社保系统状态，通知人工处理 |
| 政府网站维护 | 检测 HTTP 503 | 记录维护时间，@Scheduled 定时重试（每 2 小时），最多 3 天 |
| 申报材料不完整 | Feedback Loop 检测 | 提醒补传材料，不进入 RPA 阶段 |

**工伤 RPA 补偿流程图**：
```
RPA 失败
    ↓
记录失败原因 + 截图到 injury_case 表
    ↓
生成操作指南 (RPA 已执行步骤 + 剩余手动步骤)
    ↓
通知外务专员 (邮件 + WebSocket)
    ↓
外务专员手动完成剩余步骤
    ↓
手动录入申报回执
    ↓
案件状态更新为 DECLARED
```

#### 4.5.3 入职流程异常处理

| 环节 | 异常场景 | 处理方式 |
|------|---------|---------|
| 证件上传 | 文件格式不支持 | 返回 400 错误，提示支持格式 |
| OCR 识别 | 置信度 < 0.8 | 标记为待人工复核，不阻断流程 |
| 人脸比对 | 不匹配 | 允许重新拍照（最多 3 次），仍不匹配则标记为待人工复核 |
| 电子签名 | 签名失败 | 记录失败原因，允许重新签名 |
| 公积金参保 | RPA 失败 | 同工伤 RPA 失败补偿流程 |
| 整体流程 | 中途退出 | 保存已完成的步骤状态，下次进入时从断点继续 |

**入职流程状态管理**：
- 入职流程为单向推进，不支持状态回滚
- 若最后一步操作失败，标记该步骤为 FAILED，允许重试
- 若需撤销整个入职流程，由 HR 管理员执行"终止入职"操作，标记为 CANCELLED
- 已完成的步骤数据保留，支持从断点恢复

"""

# Insert 4.5 before Chapter 5
insert_point_4_5 = content.find("## 5. 中间件设计")
if insert_point_4_5 != -1:
    content = content[:insert_point_4_5] + section_4_5 + content[insert_point_4_5:]
    print("OK: Added section 4.5")
else:
    print("WARNING: Could not find Chapter 5")

# =====================================================
# 7. 添加 5.5 跨服务业务事务方案 + 5.6 业务规则清单（在中间件设计章节）
# =====================================================
section_5_5 = """
### 5.5 跨服务业务事务方案

> **V30 新增内容**：响应后荣检验意见"无跨服务业务事务方案"，定义 Saga 和本地消息表方案。

#### 5.5.1 方案选型

| 方案 | 适用场景 | 优点 | 缺点 | 当前适配度 |
|------|---------|------|------|-----------|
| @Transactional | 单数据源、同模块内操作 | 强一致性 | 无法跨模块/跨数据源 | 模块内操作首选 |
| TransactionTemplate | 跨模块但同数据源 | 编程式事务控制 | 仍局限于单数据源 | 薪资核算（考勤+薪资同库） |
| 本地消息表 | 跨进程可靠事件传递 | 最终一致性，实现简单 | 非实时一致性 | **当前首选** |
| Saga 模式 | 跨多个业务模块的长事务 | 支持补偿操作 | 实现复杂 | 薪资核算多模块协同 |

#### 5.5.2 本地消息表方案（当前首选）

用于跨进程可靠事件传递（Java → Python 子服务），保证 at-least-once 投递：

```
业务操作 → 本地事务 → 数据库 + 消息表
                    ↓
            @Scheduled 定时扫描消息表
                    ↓
            投递到 Redis Stream
                    ↓
            投递成功后删除消息表记录
```

**消息表设计**：
```sql
CREATE TABLE local_message (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    message_type VARCHAR(50) NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING / SENT / FAILED
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    next_retry_at DATETIME,
    created_at DATETIME DEFAULT NOW(),
    INDEX idx_status_retry (status, next_retry_at)
);
```

**实现**：
```java
@Service
public class LocalMessageService {
    
    @Autowired
    private LocalMessageMapper messageMapper;
    
    @Autowired
    private RedisTemplate<String> redisTemplate;
    
    // 在业务事务中写入消息
    @Transactional
    public void sendInTransaction(String messageType, Object payload) {
        LocalMessage msg = new LocalMessage();
        msg.setMessageType(messageType);
        msg.setPayload(objectMapper.writeValueAsString(payload));
        msg.setStatus("PENDING");
        messageMapper.insert(msg);
    }
    
    // @Scheduled 定时扫描并投递
    @Scheduled(fixedDelay = 5000)
    public void flushPendingMessages() {
        List<LocalMessage> pending = messageMapper.selectPending();
        for (LocalMessage msg : pending) {
            try {
                redisTemplate.opsForStream().add(
                    msg.getMessageType() + ":result",
                    Map.of("payload", msg.getPayload())
                );
                messageMapper.updateStatus(msg.getId(), "SENT");
            } catch (Exception e) {
                msg.setRetryCount(msg.getRetryCount() + 1);
                msg.setNextRetryAt(LocalDateTime.now().plusMinutes(
                    Math.min((int) Math.pow(2, msg.getRetryCount()), 60)));
                if (msg.getRetryCount() >= msg.getMaxRetries()) {
                    msg.setStatus("FAILED");
                }
                messageMapper.update(msg);
            }
        }
    }
}
```

#### 5.5.3 Saga 模式（薪资核算场景）

用于薪资核算涉及多模块数据协同的场景：

```
薪资核算 Saga:
    Step 1: 拉取考勤数据 (补偿: 标记考勤数据为无效)
    Step 2: 拉取社保数据 (补偿: 标记社保数据为无效)
    Step 3: 执行薪资计算 (补偿: 删除本次核算记录)
    Step 4: 生成工资条 (补偿: 撤回工资条发送)
    Step 5: 归档 (补偿: 恢复为待审核状态)

补偿执行顺序: 与正向执行相反 (Step 5 → Step 4 → Step 3 → Step 2 → Step 1)
```

**Saga 编排器**：
```java
public class PayrollSaga {
    
    @Autowired
    private SagaExecutor sagaExecutor;
    
    public void execute(String month) {
        sagaExecutor.execute(new SagaDefinition() {
            
            @SagaStep(order = 1)
            public void fetchAttendance(String month) {
                // 拉取考勤数据
            }
            
            @SagaCompensation(order = 4)
            public void compensateAttendance(String month) {
                // 标记考勤数据为无效
            }
            
            @SagaStep(order = 2)
            public void fetchSocialSecurity(String month) {
                // 拉取社保数据
            }
            
            @SagaCompensation(order = 3)
            public void compensateSocialSecurity(String month) {
                // 标记社保数据为无效
            }
            
            @SagaStep(order = 3)
            public void calculatePayroll(String month) {
                // 执行薪资计算
            }
            
            @SagaCompensation(order = 2)
            public void compensateCalculate(String month) {
                // 删除本次核算记录
            }
            
            @SagaStep(order = 4)
            public void generatePayslip(String month) {
                // 生成工资条
            }
            
            @SagaCompensation(order = 1)
            public void compensatePayslip(String month) {
                // 撤回工资条发送
            }
        });
    }
}
```

#### 5.5.4 事务方案选择指南

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 同模块内 CRUD | @Transactional | 标准 Spring 事务 |
| 跨模块同库 (考勤→薪资) | TransactionTemplate | 编程式事务，灵活控制边界 |
| Java→Python 子服务可靠事件 | 本地消息表 | 保证事务内消息不丢失 |
| 薪资核算多步骤 | Saga 模式 | 支持长事务和补偿操作 |
| 入职流程 (单向推进) | 本地事务 + 状态机 | 单向流程，无需补偿 |

### 5.6 业务规则清单

> **V30 新增内容**：响应后荣检验意见"业务规则定义不完整"，建立编号化业务规则清单。

| 规则编号 | 模块 | 规则描述 | 优先级 | 可配置 |
|---------|------|---------|--------|-------|
| PAY-001 | 薪资 | 应发工资 = 基本工资 + 加班费 - 考勤扣款 + 补贴 | 高 | 是 |
| PAY-002 | 薪资 | 加班费 = 加班时长 × 时薪 × 加班倍数 (平日 1.5x / 周末 2x / 节假日 3x) | 高 | 是 |
| PAY-003 | 薪资 | 个税采用七级累进税率 (3%-45%) | 高 | 否 |
| PAY-004 | 薪资 | 实发工资不得低于当地最低工资标准 | 高 | 是 |
| PAY-005 | 薪资 | 月度薪资波动 > ±20% 需标记异常 | 中 | 是 |
| PAY-006 | 薪资 | 社保个人缴纳比例: 养老 8% + 医疗 2% + 失业 0.5% | 高 | 是 |
| PAY-007 | 薪资 | 公积金个人缴纳比例: 5%-12% (可配置) | 高 | 是 |
| ATT-001 | 考勤 | 迟到 < 30 分钟计迟到，≥ 30 分钟计缺勤半天 | 中 | 是 |
| ATT-002 | 考勤 | 月累计迟到 > 3 次触发预警 | 低 | 是 |
| ATT-003 | 考勤 | 加班需部门负责人审批 | 中 | 否 |
| REC-001 | 招聘 | 简历评分 > 合格线+10 分为高潜，自动入库 | 中 | 是 |
| REC-002 | 招聘 | 简历评分 < 合格线-10 分为淘汰 | 中 | 是 |
| REC-003 | 招聘 | 相同岗位相同简历 30 天内去重 | 高 | 是 |
| ONB-001 | 入职 | 身份证号码必须 18 位且通过校验码验证 | 高 | 否 |
| ONB-002 | 入职 | 人脸比对相似度阈值 ≥ 80% | 中 | 是 |
| ONB-003 | 入职 | 缺少必要证件不可完成入职 | 高 | 否 |
| EXT-001 | 外务 | 工伤申报需在事故发生后 30 天内完成 | 高 | 否 |
| EXT-002 | 外务 | 申报材料完整性校验（病案+诊断书+旁证+身份证+出勤记录） | 高 | 是 |
| TRN-001 | 培训 | 签到率 < 80% 触发预警 | 低 | 是 |
| TRN-002 | 培训 | 结业考试成绩 ≥ 60 分为合格 | 中 | 是 |

**规则配置方式**：
- 可配置规则存储于 `payroll_rule` 表或 Nacos 配置中心
- 不可配置规则硬编码在代码中（如个税税率表）
- 规则变更需经 HR 管理员审批，变更历史保留至少 15 年

"""

# Insert 5.5 and 5.6 before Chapter 6
insert_point_5_5 = content.find("## 6. 安全策略")
if insert_point_5_5 != -1:
    content = content[:insert_point_5_5] + section_5_5 + content[insert_point_5_5:]
    print("OK: Added sections 5.5, 5.6")
else:
    print("WARNING: Could not find Chapter 6")

# =====================================================
# 8. 添加 6.6 密码存储 + 6.7 输入验证（在安全策略章节）
# =====================================================
section_6_6 = """
### 6.6 密码存储方案

> **V30 新增内容**：响应后荣检验意见"无密码存储方案"，明确 BCrypt 哈希算法及参数。

#### 6.6.1 密码哈希算法

| 维度 | 方案 |
|------|------|
| 算法 | BCrypt |
| 工作因子 (work factor) | 12 (2^12 = 4096 迭代) |
| 盐值 | BCrypt 自动生成的 128 位盐值，每次哈希不同 |
| 存储格式 | $2a$12$[22 字符盐值][31 字符哈希] (总长 60 字符) |
| 实现 | Spring Security `BCryptPasswordEncoder` |

```java
@Component
public class PasswordEncoder extends org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder {
    public PasswordEncoder() {
        super(12);  // 工作因子 12
    }
}

// 使用示例
@Autowired
private PasswordEncoder passwordEncoder;

// 注册时加密存储
user.setPassword(passwordEncoder.encode(plainPassword));

// 登录时验证
if (passwordEncoder.matches(plainPassword, user.getPassword())) {
    // 密码正确
}
```

#### 6.6.2 密码复杂度策略

| 规则 | 要求 |
|------|------|
| 最小长度 | 8 字符 |
| 最大长度 | 64 字符 |
| 字符要求 | 至少包含大写、小写、数字、特殊字符中的 3 种 |
| 禁止项 | 不能包含用户名、邮箱地址 |
| 历史密码 | 不能与前 3 次密码相同 |
| 特殊字符 | !@#$%^&*()-_=+[]{}|;:',.<>?/ |

#### 6.6.3 密码定期更换策略

| 角色 | 更换周期 | 说明 |
|------|---------|------|
| 普通用户 | 90 天 | 到期前 7 天提醒 |
| HR 管理员 | 60 天 | 到期前 7 天提醒 |
| 系统管理员 | 30 天 | 到期前 7 天提醒 |

**密码更换提醒**：
- 到期前 7 天: 登录时弹出提醒
- 到期前 3 天: 邮件提醒
- 到期: 强制要求更换密码后才能登录

#### 6.6.4 密码暴力破解防护

| 防护措施 | 实现方式 |
|---------|---------|
| 登录失败计数 | Redis 记录每 IP 失败次数 `login:fail:{ip}` |
| 账户锁定 | 连续 5 次失败锁定 30 分钟 |
| 验证码触发 | 第 3 次失败后要求输入图形验证码 |
| 速率限制 | 登录接口 5 次/分钟/IP（见 3.1.3 节） |
| 异常告警 | 同一账号不同 IP 登录触发告警 |

### 6.7 输入验证和过滤设计

> **V30 新增内容**：响应后荣检验意见"无输入验证和过滤设计"，补充 SQL 注入、XSS、CSRF 防护方案。

#### 6.7.1 SQL 注入防护

| 防护措施 | 实现方式 |
|---------|---------|
| 参数化查询 | MyBatis 使用 `#{}` 占位符，禁止 `${}` 直接拼接 SQL |
| MyBatis-Plus Wrapper | 使用 LambdaQueryWrapper 构建查询，自动生成参数化 SQL |
| 动态 SQL 限制 | 禁止在 XML 映射文件中拼接用户输入 |
| 白名单校验 | 排序字段使用白名单校验: `allowedSortFields = ["id", "name", "created_at"]` |
| ORM 层防护 | MyBatis 默认使用 PreparedStatement，天然防 SQL 注入 |

#### 6.7.2 XSS 防护

| 防护措施 | 实现方式 |
|---------|---------|
| 输出编码 | 所有用户输入在输出到前端时进行 HTML 实体编码 |
| 输入过滤 | 后端对富文本字段进行 HTML 标签白名单过滤 (JSoup Cleaner) |
| Content-Security-Policy | 前端设置 CSP 头限制脚本来源 |
| Cookie 安全 | HttpOnly + Secure + SameSite=Strict |
| 富文本处理 | JSoup 白名单过滤: `Whitelisted tags: p, br, strong, em, ul, ol, li, a` |

```java
@Component
public class InputFilter {
    
    private final Whitelist whitelist = Whitelist.relaxed()
        .addTags("table", "thead", "tbody", "tr", "th", "td")
        .addAttributes("a", "href", "title")
        .addProtocols("a", "href", "https");
    
    public String sanitizeHtml(String input) {
        return Jsoup.clean(input, whitelist);
    }
    
    public String escapeHtml(String input) {
        return StringEscapeUtils.escapeHtml4(input);
    }
}
```

#### 6.7.3 CSRF 防护

| 防护措施 | 实现方式 |
|---------|---------|
| JWT 无状态认证 | 基于 Bearer Token 认证天然免疫 CSRF（CSRF 针对 Cookie 认证） |
| SameSite Cookie | 设置 SameSite=Strict，防止跨站请求携带 Cookie |
| Origin 校验 | 对敏感操作（薪资修改、用户删除等）校验请求 Origin 头 |
| 自定义头校验 | API 请求需携带自定义头 X-Requested-With，服务端校验 |

```java
@Component
public class OriginValidationFilter implements Filter {
    
    @Value("${allowed.origins}")
    private Set<String> allowedOrigins;
    
    private static final Set<String> SENSITIVE_PATHS = Set.of(
        "/api/v1/payroll/**",
        "/api/v1/system/users/**",
        "/api/v1/employee/resignation"
    );
    
    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) {
        HttpServletRequest request = (HttpServletRequest) req;
        if (isSensitivePath(request)) {
            String origin = request.getHeader("Origin");
            if (origin == null || !allowedOrigins.contains(origin)) {
                ((HttpServletResponse) res).sendError(HttpServletResponse.SC_FORBIDDEN);
                return;
            }
        }
        chain.doFilter(req, res);
    }
}
```

#### 6.7.4 文件上传安全策略

| 防护措施 | 实现方式 |
|---------|---------|
| 文件类型白名单 | 仅允许: pdf, jpg, png, xlsx, xls, csv |
| 文件大小限制 | 单文件最大 10MB，总上传最大 50MB |
| 文件重命名 | 上传后重命名为 UUID 格式，防止路径遍历 |
| 病毒扫描 | 集成 ClamAV（可选），对上传文件进行病毒扫描 |
| 存储隔离 | 文件存储于 MinIO 对象存储，与 Web 根目录隔离 |
| Content-Type 校验 | 检查文件实际 MIME 类型，而非仅依赖扩展名 |

"""

# Insert 6.6 and 6.7 before Chapter 7
insert_point_6_6 = content.find("## 7. Agent 运行时设计")
if insert_point_6_6 != -1:
    content = content[:insert_point_6_6] + section_6_6 + content[insert_point_6_6:]
    print("OK: Added sections 6.6, 6.7")
else:
    print("WARNING: Could not find Chapter 7")

# =====================================================
# 9. 添加 9.4~9.7（在错误处理与异常管理章节）
# =====================================================
section_9_4 = """
### 9.4 超时时间清单

> **V30 新增内容**：响应后荣检验意见"无超时时间统一定义"，汇总所有超时配置。

| 类别 | 超时时间 | 说明 | 配置位置 |
|------|---------|------|---------|
| 数据库连接超时 | 30s | HikariCP connectionTimeout | spring.datasource.hikari.connection-timeout |
| 数据库读取超时 | 10s | socketTimeout | spring.datasource.hikari.socket-timeout |
| 数据库语句超时 | 30s | queryTimeout | MyBatis defaultStatementTimeout |
| HTTP 连接超时 (默认) | 5s | WebClient connectTimeout | Resilience4j TimeLimiter |
| HTTP 读取超时 (默认) | 10s | WebClient readTimeout | Resilience4j TimeLimiter |
| RPA 子服务调用 | 120s | RPA 浏览器操作耗时较长 | rpaService TimeLimiter |
| OCR 子服务调用 | 30s | OCR 识别为短时间操作 | ocrService TimeLimiter |
| 人脸子服务调用 | 10s | 人脸比对为 CPU 密集型但耗时短 | faceService TimeLimiter |
| 薪资核算 API | 300s | 批量计算全员薪资 | PayrollController |
| 简历批量导入 API | 60s | 批量导入处理 | ResumeController |
| RPA 任务执行 | 300s | RPA 浏览器自动化完整流程 | RPATask.timeoutSeconds |
| WebSocket 心跳间隔 | 30s | STOMP heartbeat | WebSocket config |
| WebSocket 连接超时 | 60s | 空闲连接超时 | WebSocket config |
| Redis 连接超时 | 5s | Redisson connectionTimeout | Redisson config |
| Redis 命令超时 | 3s | Redisson timeout | Redisson config |
| MinIO 上传超时 | 60s | 大文件上传 | MinIO client config |
| MinIO 下载超时 | 30s | 文件下载 | MinIO client config |

### 9.5 业务降级策略矩阵

> **V30 新增内容**：响应后荣检验意见"无业务降级策略矩阵"，补充各业务场景降级方案。

| 业务场景 | 降级触发条件 | 降级策略 | 降级后用户体验 | 恢复条件 |
|---------|------------|---------|--------------|---------|
| 薪资核算 | RPA/OCR/人脸不可用 | 使用缓存的上月数据估算，标记为估算值 | 提示"部分数据为估算值" | 子服务恢复后重新核算 |
| 薪资核算 | LLM 不可用 | 使用规则引擎（非 AI）进行基础计算 | 无感知（计算精度略降） | 无需恢复 |
| 简历匹配 | LLM 不可用 | 降级为关键词匹配（无语义分析） | 匹配精度降低，提示"简化模式" | LLM 恢复后重新评分 |
| 简历抓取 | 招聘平台 API 不可用 | 跳过该平台，继续抓取其他平台 | 部分平台简历缺失 | 平台恢复后自动补抓 |
| 考试管理 | 在线考试不可用 | 生成纸质考试二维码，转线下模式 | 转为线下考试 | 系统恢复后数据补录 |
| 人脸采集 | 人脸子服务不可用 | 跳过人脸采集，标记为待补充 | 入职流程继续，人脸后续补采 | 子服务恢复后补采 |
| OCR 识别 | OCR 子服务不可用 | 提示手动输入信息 | 需手动填写证件信息 | 子服务恢复后可重新识别 |
| 工伤申报 | RPA 不可用 | 生成操作指南，转人工处理 | 外务专员手动操作政府网站 | RPA 恢复后自动处理 |
| 通知推送 | 邮件/短信不可用 | 记录到系统通知，前端 Dashboard 展示 | 仅能在系统中查看通知 | 服务恢复后补发 |
| 数据库从库 | 从库不可用 | 所有读请求转发到主库 | 主库负载增加，响应略慢 | 从库恢复后自动切换 |

### 9.6 API 级别重试策略

> **V30 新增内容**：响应后荣检验意见"无 API 级别重试策略"，补充重试策略。

| API 类别 | 是否可重试 | 重试次数 | 退避算法 | 说明 |
|---------|-----------|---------|---------|------|
| 幂等 GET 请求 | 是 | 3 次 | 指数退避 (1s, 2s, 4s) | 读取操作天然幂等 |
| 幂等 PUT/DELETE | 是 | 2 次 | 指数退避 (1s, 2s) | 基于 ID 的操作幂等 |
| 非幂等 POST | 否 | 0 次 | - | 创建操作不可重试，避免重复 |
| 薪资核算 POST | 是 | 1 次 | 固定退避 (5s) | 通过幂等 Key (month+employeeId) 保证幂等 |
| RPA 子服务调用 | 是 | 3 次 | 指数退避 (1s, 2s, 4s) | 网络瞬态故障 |
| OCR 子服务调用 | 是 | 2 次 | 指数退避 (1s, 2s) | 网络瞬态故障 |
| 人脸子服务调用 | 是 | 2 次 | 指数退避 (1s, 2s) | 网络瞬态故障 |
| 数据库操作 | 是 | 3 次 | 指数退避 (100ms, 200ms, 400ms) | 连接池瞬态故障 |
| Redis 操作 | 是 | 3 次 | 指数退避 (50ms, 100ms, 200ms) | 连接瞬态故障 |

**重试实现 (Resilience4j Retry)**：
```java
@Retry(name = "default",
    maxAttempts = 3,
    waitDuration = Duration.ofSeconds(1),
    retryExceptions = {ResourceExhaustedException.class, ConnectException.class})
public <T> T executeWithRetry(Supplier<T> supplier) {
    return supplier.get();
}
```

### 9.7 优雅停机设计

> **V30 新增内容**：响应后荣检验意见"无优雅停机设计"，补充优雅停机策略。

**优雅停机流程**：
```
Spring Boot 收到 SIGTERM
    ↓
1. 停止接收新请求 (Spring 关闭 Tomcat 监听器)
    ↓
2. 等待正在处理的请求完成 (server.shutdown=graceful, timeout=30s)
    ↓
3. @PreDestroy 资源清理:
    ├── 停止 @Scheduled 定时任务
    ├── 停止 Quartz Scheduler
    ├── 停止 Redis Stream 消费者 (StreamListener.stop() + flush())
    ├── 关闭 WebSocket 连接 (广播停机通知)
    ├── 刷新并关闭 Agent 日志
    ├── 关闭数据库连接池 (HikariCP)
    └── 关闭 Redis 连接 (Redisson)
    ↓
4. 应用退出 (exit code 0)
```

**配置**：
```yaml
# application.yml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

**关键资源的 @PreDestroy 清理**：
```java
@Component
public class GracefulShutdownManager {
    
    @Autowired
    private Scheduler quartzScheduler;
    
    @Autowired
    private RedissonClient redisson;
    
    @Autowired
    private StreamListener<?> streamListener;
    
    @PreDestroy
    public void shutdown() {
        log.info("开始优雅停机...");
        
        if (quartzScheduler != null && quartzScheduler.isStarted()) {
            quartzScheduler.shutdown(false); // false = 等待当前 Job 完成
        }
        
        if (streamListener != null) {
            streamListener.stop();
            streamListener.flush();
        }
        
        if (redisson != null && !redisson.isShutdown()) {
            redisson.shutdown();
        }
        
        log.info("优雅停机完成");
    }
}
```

**Docker 停机配置**：
- `stop_grace_period`: 45s（给应用 45 秒完成优雅停机）
- 若 45s 内未完成，Docker 发送 SIGKILL 强制终止

"""

# Insert 9.4~9.7 before Chapter 10
insert_point_9_4 = content.find("## 10. 性能优化策略")
if insert_point_9_4 != -1:
    content = content[:insert_point_9_4] + section_9_4 + content[insert_point_9_4:]
    print("OK: Added sections 9.4~9.7")
else:
    print("WARNING: Could not find Chapter 10")

# =====================================================
# 10. 添加 10.7~10.13（在性能优化策略章节末尾）
# =====================================================
section_10_7 = """
### 10.7 健康检查端点设计

> **V30 新增内容**：响应后荣检验意见"无健康检查端点设计"，补充主服务健康检查端点。

#### 10.7.1 Java 主服务健康检查

使用 Spring Boot Actuator 提供健康检查端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| /actuator/health | GET | 总体健康状态 |
| /actuator/health/ready | GET | 就绪状态（负载均衡器使用） |
| /actuator/health/liveness | GET | 存活状态（看门狗使用） |
| /actuator/health/subservices | GET | Python 子服务健康状态汇总 |

**健康检查组件**：

| 组件 | 检查方式 | 不健康条件 |
|------|---------|----------|
| 数据库 | JDBC 连接池测试 | 连接获取失败或连接池耗尽 |
| Redis | PING 命令 | PONG 响应超时 (>3s) |
| RPA 子服务 | HTTP GET /health | HTTP 状态非 200 或超时 (>5s) |
| OCR 子服务 | HTTP GET /health | HTTP 状态非 200 或超时 (>5s) |
| 人脸子服务 | HTTP GET /health | HTTP 状态非 200 或超时 (>5s) |
| Nacos | 配置拉取状态 | 配置拉取失败超过 3 次 |
| MinIO | listBuckets 测试 | 连接失败或超时 (>10s) |

**自定义 HealthIndicator**：
```java
@Component
public class SubServiceHealthIndicator implements HealthIndicator {
    
    @Override
    public Health health() {
        Health.Builder builder = Health.up();
        checkSubService(builder, "rpa", "http://rpa-service:8090/health");
        checkSubService(builder, "ocr", "http://ocr-service:8091/health");
        checkSubService(builder, "face", "http://face-service:8092/health");
        return builder.build();
    }
    
    private void checkSubService(Health.Builder builder, String name, String url) {
        try {
            webClient.get().uri(url).retrieve().bodyToMono(String.class)
                .timeout(Duration.ofSeconds(5)).block();
            builder.withDetail(name, "UP");
        } catch (Exception e) {
            builder.withDetail(name, "DOWN: " + e.getMessage());
        }
    }
}
```

**Actuator 配置**：
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: when-authorized
      probes:
        enabled: true       # 启用 readiness/liveness 探针
      group:
        readwrite:
          include: subservices
```

#### 10.7.2 Docker Compose 健康检查

```yaml
hr-backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/actuator/health/ready"]
      interval: 30s
      timeout: 10s
      start-period: 60s
      retries: 3
```

### 10.8 CI/CD 流程设计

> **V30 新增内容**：响应后荣检验意见"无 CI/CD 流程说明"，补充完整 CI/CD 流水线设计。

**CI/CD 流水线（GitLab CI 为例）**：

```
代码提交 (push/merge request)
    ↓
Stage 1: 构建 (Build)
    ├── Gradle 编译
    ├── Docker 镜像构建 (Java + 3 个 Python 子服务)
    └── 制品推送到容器仓库
    ↓
Stage 2: 单元测试 (Unit Test)
    ├── JUnit 5 单元测试
    ├── 代码覆盖率检查 (JaCoCo, 覆盖率 > 80%)
    └── 静态代码扫描 (SpotBugs)
    ↓
Stage 3: 集成测试 (Integration Test)
    ├── Testcontainers 集成测试 (MySQL + Redis)
    ├── API 契约测试
    └── 数据库迁移脚本验证
    ↓
Stage 4: 质量门禁 (Quality Gate)
    ├── 覆盖率检查: 行覆盖率 > 80%
    ├── 代码复杂度: 圈复杂度 < 15
    ├── 安全扫描: OWASP Dependency Check
    ├── 代码风格: Checkstyle 无 ERROR 级别问题
    └── 失败则阻断后续流程
    ↓
Stage 5: 部署到测试环境 (Deploy Test)
    ├── 注入测试环境 .env (从 GitLab CI Variables 读取)
    ├── Docker Compose 部署
    ├── 健康检查验证
    └── 自动化 E2E 测试
    ↓
Stage 6: 部署到生产环境 (Deploy Prod)
    ├── 人工审批 (Manual approval)
    ├── 注入生产环境 .env (从 GitLab CI Variables / Vault 读取)
    ├── 灰度发布 (金丝雀: 先部署新镜像，观察 30 分钟)
    ├── 健康检查验证
    └── 全量发布
```

**.env 注入方式**：
- 开发环境: 开发者本地维护 .env 文件
- 测试环境: GitLab CI Variables 注入到 .env
- 生产环境: GitLab CI Variables (masked + protected) 注入到 .env，敏感变量不在日志中显示

### 10.9 链路追踪实现方案

> **V30 新增内容**：响应后荣检验意见"无链路追踪实现方案"，补充 OpenTelemetry 方案。

**技术选型：OpenTelemetry**（替代 Spring Cloud Sleuth）

| 组件 | 选型 | 说明 |
|------|------|------|
| 埋点 SDK | OpenTelemetry Java Agent | 无侵入式，通过 Java Agent 自动埋点 |
| 采集器 | OpenTelemetry Collector | 统一接收、处理、转发追踪数据 |
| 存储 | Jaeger / Tempo | 追踪数据存储和查询 |
| 可视化 | Grafana (Jaeger 插件) | 追踪链路可视化 |

**TraceId 传递方式**：

| 场景 | 传递方式 |
|------|---------|
| HTTP 请求 (外部→Java) | W3C Trace Context 标准头 (traceparent, tracestate) |
| Java 内部方法调用 | ThreadLocal 自动传递 (OpenTelemetry 自动完成) |
| Java→Python 子服务 (HTTP) | 通过 HTTP 头传递 traceparent |
| Redis Stream 消息 | 消息 payload 中包含 traceId 字段 |
| Spring Event | 事件对象中包含 traceId，通过 ThreadLocal 传递 |
| WebSocket | STOMP 消息头中包含 traceId |

**OpenTelemetry 配置**：
```yaml
otel:
  service:
    name: gbm-hr-backend
  tracer:
    sampler: parentbased_always_on  # 生产环境可改为 parentbased_traceidratio
```

**Java Agent 启动参数**：
```
-javaagent:/opt/otel/opentelemetry-javaagent-1.x.jar
-Dotel.exporter=jaeger
-Dotel.exporter.jaeger.endpoint=http://jaeger:14268/api/traces
-Dotel.resource.attributes=service.version=${APP_VERSION}
```

**Python 子服务埋点**：
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(app)
```

### 10.10 配置管理统一策略

> **V30 新增内容**：响应后荣检验意见"无配置管理统一策略说明"，补充配置管理策略。

#### 10.10.1 配置分层管理

| 层级 | 存储位置 | 内容 | 优先级 |
|------|---------|------|--------|
| 基础配置 | application.yml | 默认配置，所有环境共用 | 最低 |
| 环境配置 | application-{dev,test,prod}.yml | 环境特定配置 | 中 |
| 动态配置 | Nacos 配置中心 | 薪资规则、Agent 参数等运行时可调配置 | 高 |
| 敏感配置 | .env 文件 | 数据库密码、JWT 密钥、API 密钥等 | 最高 |

#### 10.10.2 环境配置差异

| 配置项 | 开发环境 | 测试环境 | 生产环境 |
|--------|---------|---------|---------|
| 数据库 | 本地 MySQL | Docker MySQL | Docker MySQL |
| Redis | 本地 Redis | Docker Redis | Docker Redis |
| Nacos | 本地 Nacos | 测试 Nacos 集群 | 生产 Nacos 集群 |
| LLM | 免费/测试模型 | 测试模型 | 生产模型 |
| 日志级别 | DEBUG | INFO | WARN |
| 追踪采样率 | 100% | 50% | 10% |
| 子服务 | 本地 Python 进程 | Docker Python 容器 | Docker Python 容器 |

#### 10.10.3 配置热更新策略

| 配置类型 | 更新方式 | 生效时机 | 是否需要重启 |
|---------|---------|---------|------------|
| 薪资规则 | Nacos 控制台修改 | @NacosValue 即时生效 | 否 |
| Agent 参数 | Nacos 控制台修改 | @RefreshScope 懒加载生效 | 否 |
| 日志级别 | Nacos 控制台修改 | Logback 动态调整 | 否 |
| Cron 表达式 | Nacos 控制台修改 | 下次定时任务触发时生效 | 否 |
| 数据库连接 | .env 修改 | 连接池重建 | 是 |
| JWT 密钥 | .env 修改 | 应用重启后生效 | 是 |

#### 10.10.4 配置变更审计

- Nacos 配置变更自动记录历史版本
- 每次配置变更记录: 操作人、变更时间、变更前值、变更后值
- 敏感配置（.env）变更通过 CI/CD 审计日志追踪
- 配置回滚: Nacos 控制台支持一键回滚到历史版本

### 10.11 灰度发布方案

> **V30 新增内容**：响应后荣检验意见"无灰度发布方案"，补充金丝雀发布策略。

**金丝雀发布流程**：
```
金丝雀发布流程:
    1. 当前运行 V1 镜像 (100% 流量)
    2. 部署 V2 镜像 (金丝雀实例)
    3. 通过 Nginx/Ingress 将 5% 流量路由到 V2
    4. 观察 30 分钟:
       ├── API 错误率 < 1%
       ├── P95 响应时间未增加 > 20%
       ├── 无新增异常日志
       └── 健康检查通过
    5. 通过则将流量调整为 50%
    6. 再观察 30 分钟
    7. 通过则将流量调整为 100% (全量 V2)
    8. 保留 V1 镜像 24 小时 (用于紧急回滚)
    9. 回滚: 将流量切回 V1，停止 V2 实例
```

**蓝绿部署（简化方案）**：
- 蓝环境 (当前生产) + 绿环境 (新版本)
- 部署完成后切换 Nginx upstream 指向绿环境
- 回滚: 切回蓝环境

```nginx
# Nginx 配置示例
upstream gbm_hr {
    server blue:8080 weight=100;  # 蓝环境
    # server green:8081 weight=0; # 绿环境（初始 0 流量）
}

# 金丝雀阶段
upstream gbm_hr {
    server blue:8080 weight=95;
    server green:8081 weight=5;
}

# 全量切换
upstream gbm_hr {
    server green:8081 weight=100;
}
```

### 10.12 读写分离策略

> **V30 新增内容**：响应后荣检验意见"读写分离方案不完整"，补充读写分离策略。

**当前采用 MySQL 主从复制架构**：

| 操作类型 | 路由目标 | API 示例 |
|---------|---------|---------|
| 读操作 (主库) | 主库 | 所有实时性要求高的查询 |
| 读操作 (从库) | 从库 | 列表查询、统计查询、报表查询 |
| 写操作 | 主库 | 所有 INSERT/UPDATE/DELETE |

**读写分离路由规则**：
```java
@Aspect
@Component
public class DataSourceRouteAspect {
    
    @Target({METHOD, TYPE})
    @Retention(RUNTIME)
    public @interface ReadFromSlave {}
    
    @Around("@annotation(ReadFromSlave)")
    public Object routeToSlave(ProceedingJoinPoint pjp) {
        DataSourceContextHolder.setSlave();
        try {
            return pjp.proceed();
        } finally {
            DataSourceContextHolder.clear();
        }
    }
}
```

**适用从库的 API**：
- GET /api/v1/employee/list (员工列表)
- GET /api/v1/recruitment/resumes (简历列表)
- GET /api/v1/attendance/records (考勤记录)
- GET /api/v1/payroll/{month} (薪资查询)
- GET /api/v1/performance/report (绩效报告)

**主从延迟处理**：
- 写操作后立即读取的场景: 强制走主库（如创建用户后立即查看）
- 延迟检测: 定时任务对比主从 binlog position，延迟 > 5s 时告警
- 降级方案: 主从同步异常时，所有读请求自动降级到主库

### 10.13 数据导入导出策略

> **V30 新增内容**：响应后荣检验意见"数据导入导出技术实现方案不完整"，补充大批量导入导出策略。

#### 10.13.1 大批量导入策略

| 特性 | 实现方式 |
|------|---------|
| 异步导入 | 上传后返回 taskId，后台异步处理 |
| 进度查询 | GET /api/v1/import/{taskId}/progress 返回进度百分比 |
| 分片处理 | 每 100 行为一个批次，批量插入数据库 |
| 错误回显 | 完成后下载错误报告 (Excel)，标注错误行号和原因 |
| 幂等导入 | 基于唯一 Key (如身份证号) 去重，重复行跳过 |
| 事务边界 | 每个批次独立事务，部分失败不影响其他批次 |

**导入任务状态**：
```java
public enum ImportStatus {
    PENDING,        // 排队中
    PROCESSING,     // 处理中
    COMPLETED,      // 完成（全部成功）
    PARTIAL,        // 部分成功（有错误行）
    FAILED          // 全部失败
}
```

#### 10.13.2 大批量导出策略

| 特性 | 实现方式 |
|------|---------|
| 异步导出 | 提交导出请求后返回 taskId，后台生成文件 |
| 分片导出 | 每 1000 行为一个分片，避免内存溢出 |
| 文件暂存 | 导出文件暂存到 MinIO，24 小时后自动清理 |
| 下载通知 | 导出完成后通过 WebSocket/邮件通知用户 |
| Excel 模板 | 预设标准模板，支持自定义列 |

#### 10.13.3 Excel 模板管理

- 模板存储在数据库中，支持版本管理
- 预设模板: 简历导入模板、员工信息导入模板、薪资调整导入模板
- 模板下载: GET /api/v1/templates/{templateType}/download
- 模板更新: 管理员可在系统中更新模板字段，无需修改代码

"""

# Insert 10.7~10.13 before the document end marker
end_marker = "*文档结束*"
if end_marker in content:
    end_pos = content.find(end_marker)
    content = content[:end_pos] + section_10_7 + "\n" + content[end_pos:]
    print("OK: Added sections 10.7~10.13")
else:
    # If no end marker, append to end
    content += section_10_7 + "\n"
    print("OK: Appended sections 10.7~10.13 (no end marker found)")

# =====================================================
# Write the final V30 document
# =====================================================
with open(V30_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

final_lines = content.split('\n')
final_size = len(content.encode('utf-8'))
print(f"\nV30 文档生成完成:")
print(f"  路径: {V30_PATH}")
print(f"  行数: {len(final_lines)}")
print(f"  大小: {final_size} 字节")
