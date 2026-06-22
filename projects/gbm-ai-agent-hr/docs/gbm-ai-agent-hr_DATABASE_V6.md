# GBM AI Agent HR 智能人力管理系统 — 数据库设计脚本 (V6)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 数据库设计脚本 |
| 版本号 | V6.0 |
| 基于 SRS | V15.0 |
| 数据库 | MySQL 8.x (InnoDB) |
| 字符集 | utf8mb4 / utf8mb4_unicode_ci |
| 日期 | 2026-06-13 |
| 作者 | 后旺 (HouWang) |
| 角色 | 数据库架构师 |

---

## 目录

1. ER 概述与设计规范
2. 建表顺序与依赖说明
3. 基础表结构
4. 业务表结构
5. Agent 与审计表
6. 索引设计
7. 视图设计
8. 初始化数据
9. 分区与归档策略
10. 附录

---

## 1. ER 概述与设计规范

### 1.1 实体关系图 (文本描述)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  department   │────│   employee    │────│ attendance_   │
│   部门表      │ 1:N│   员工表      │ 1:N│  record       │
│              │     │              │    │  考勤记录表    │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐    ┌──────▼───────┐   ┌──────▼──────┐
│    resume    │    │   payroll    │   │ performance  │
│    简历表    │    │   薪资记录表  │   │  _review     │
└──────────────┘    └──────────────┘   │  绩效表      │
                                       └─────────────┘
                            │
                   ┌────────▼──────────┐
                   │ employee_pay_     │
                   │  profile          │
                   │  员工薪资档案表   │
                   └───────────────────┘

┌──────────────┐    ┌──────────────┐   ┌──────────────┐
│ job_position │    │training_plan │   │  injury_case │
│    岗位表    │    │  培训计划表   │   │   工伤档案表  │
└──────────────┘    └──────┬───────┘   └─────────────┘
                           │
                  ┌────────▼────────┐
                  │training_session │
                  │   培训场次表    │
                  └────────┬────────┘
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼───┐ ┌─────▼────┐ ┌────▼────────┐
    │ training_   │ │ exam_    │ │ training_   │
    │ checkin     │ │ paper    │ │ record      │
    │ 培训签到表   │ │  试卷表   │ │  培训记录表  │
    └─────────────┘ └─────┬────┘ └─────────────┘
                          │
                 ┌────────▼────────┐
                 │ paper_question  │
                 │ 试卷题目关联表   │
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │ exam_question   │
                 │    题目表       │
                 └─────────────────┘

┌──────────────┐    ┌──────────────┐   ┌──────────────┐
│   sys_user   │    │  sys_role    │   │  audit_log   │
│   系统用户    │    │   角色表      │   │  审计日志表   │
└──────────────┘    └──────┬───────┘   └─────────────┘
        │                   │
        └────────┬──────────┘
                 │
        ┌────────▼────────┐
        │ sys_user_role   │
        │ 用户角色关联表   │
        └─────────────────┘
                 │
        ┌────────▼────────┐
        │ sys_role_       │
        │ permission      │
        │ 角色权限关联表   │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ sys_permission  │
        │    权限表        │
        └─────────────────┘

┌──────────────┐    ┌──────────────┐   ┌──────────────┐
│ agent_run_log│    │   rpa_task   │   │ certificate  │
│ Agent执行日志 │    │  RPA任务表   │   │  证书台账表   │
└──────────────┘    └──────────────┘   └─────────────┘
```

### 1.2 核心实体关系

| 关系 | 类型 | 说明 |
|------|------|------|
| department → employee | 1:N | 一个部门包含多个员工 |
| employee → attendance_record | 1:N | 一个员工有多条考勤记录 |
| employee → payroll | 1:N | 一个员工有多条薪资记录 |
| employee → employee_pay_profile | 1:N | 一个员工有多个薪资档案版本（历史变更记录），通过 is_active 字段区分当前有效版本与历史版本 |
| employee → performance_review | 1:N | 一个员工有多次绩效记录 |
| employee → training_record | 1:N | 一个员工有多个培训记录 |
| employee → injury_case | 1:N | 一个员工可能有多个工伤记录 |
| employee → certificate | 1:N | 一个员工有多个证书 |
| sys_user → sys_role | M:N | 用户与角色多对多（通过 sys_user_role 中间表） |
| sys_role → sys_permission | M:N | 角色与权限多对多（通过 sys_role_permission 中间表），一个权限可赋给多个角色 |
| job_position → resume | 1:N | 一个岗位有多份投递简历 |
| training_plan → training_session | 1:N | 一个培训计划有多个培训场次 |
| training_session → training_checkin | 1:N | 一个场次有多个签到记录 |
| training_session → training_record | 1:N | 一个场次有多个培训记录 |
| exam_paper → exam_question | M:N | 试卷与题目多对多（通过 paper_question 关联表） |

### 1.3 全局字段约定

以下字段在所有业务表中统一使用：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `tenant_id` | VARCHAR(20) | 租户ID，多租户隔离。默认值由应用层配置注入，DDL 中不硬编码默认值 |
| `is_deleted` | TINYINT(1) | 软删除标记：0=正常，1=已删除。HR 数据涉及劳动法合规要求，禁止物理删除 |
| `version` | INT | 乐观锁版本号，每次 UPDATE 自动 +1，防止并发编辑冲突 |
| `created_at` | TIMESTAMP | 记录创建时间，默认 CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | 记录最后更新时间，默认 CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

### 1.4 ID 生成策略

本系统统一采用雪花算法（Snowflake）生成分布式唯一 ID，存储为 VARCHAR(20) 类型（避免 BIGINT 在前端 JavaScript 中精度丢失）。所有表的 ID 字段均遵循此策略，由应用层在插入前生成。

**雪花算法位数分配方案：**

| 位数范围 | 位数 | 说明 |
|---------|------|------|
| 符号位 | 1 bit | 固定为 0（正数） |
| 时间戳 | 41 bits | 毫秒级时间戳，支持约 69 年（至 2082 年） |
| 机器 ID | 10 bits | 支持最大 1024 个节点（worker/node ID） |
| 序列号 | 12 bits | 每毫秒内支持 4096 个序列号 |

**总计：** 1 + 41 + 10 + 12 = 64 bits（一个有符号 64 位长整型）。转换为十进制字符串后为 18-19 位，VARCHAR(20) 提供 1 位冗余以应对未来可能的扩展（如引入数据中心 ID 等）。

**生成示例：**
- 时间戳偏移量：当前时间减去固定起始时间（如 2024-01-01 00:00:00），避免时间戳过大
- 机器 ID：由部署配置文件指定或通过服务注册中心分配
- 序列号：每毫秒自增，跨毫秒归零
- 前端传输：以字符串形式传递，避免 JavaScript Number 类型精度丢失（Number.MAX_SAFE_INTEGER = 2^53 - 1）

### 1.5 字段命名规范

本系统所有字段命名统一采用蛇形命名法（snake_case）：

| 规则 | 示例 |
|------|------|
| 表名：全小写，单词间用下划线分隔 | `attendance_record`, `employee_pay_profile` |
| 字段名：全小写，单词间用下划线分隔 | `first_name`, `hire_date`, `is_deleted` |
| 主键命名：`{表简称}_id` | `employee_id`, `dept_id`, `position_id` |
| 外键命名：引用目标表的主键名 | `employee.dept_id` 引用 `department.dept_id` |
| 外键约束名：`fk_{来源表简称}_{目标字段}` | `fk_emp_dept`, `fk_dept_manager` |
| 索引命名：`idx_{字段名}` | `idx_dept_id`, `idx_hire_date` |
| 联合索引命名：`idx_{字段1}_{字段2}` | `idx_emp_date_flag`, `idx_month_status` |
| 唯一索引命名：`uk_{字段名}` 或 `uk_{字段1}_{字段2}` | `uk_username`, `uk_emp_date` |

**布尔/标志字段：** 使用 TINYINT(1) 类型，命名以 `is_` 或 `has_` 前缀开头（如 `is_deleted`, `is_active`），或使用 `enabled`、`status` 等描述性名称。

### 1.6 外键约束策略

本系统采用 **数据库层面强制外键约束** 方案，理由如下：

| 方案 | 优点 | 缺点 | 本系统选择 |
|------|------|------|-----------|
| 数据库外键约束 | 数据完整性由数据库保证，不受应用层逻辑影响；跨连接操作也能维护引用完整性 | 对分库分表扩展有一定限制 | **✅ 采用** |
| 应用层维护引用完整性 | 灵活性高，易于分库分表；可在应用层实现更复杂的业务逻辑 | 应用 bug 可能导致脏数据；难以保证跨会话的数据一致性 | 仅作为辅助手段 |

**具体策略：**
1. 所有关联字段在数据库层面定义外键约束（FOREIGN KEY）
2. 级联策略：父表更新时子表同步更新（ON UPDATE CASCADE），父表删除时根据业务需求选择 CASCADE/SET NULL/RESTRICT
3. 循环依赖通过 ALTER TABLE 延迟添加外键解决（见第 2.2 节）
4. 应用层 ORM/DAO 在插入/删除时仍需遵守外键约束顺序，避免违反引用完整性

### 1.7 字符集与排序规则

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 数据库字符集 | utf8mb4 | 支持完整的 Unicode（含 Emoji），MySQL 官方推荐 |
| 排序规则 | utf8mb4_unicode_ci | 不区分大小写，支持多语言（中文/英文/日文等） |
| 表级别覆盖 | 所有表统一使用 utf8mb4/utf8mb4_unicode_ci | 无例外 |

**选择理由：**
- utf8mb4 是 MySQL 8.x 的标准字符集，完全替代旧的 utf8（实际为 utf8mb3）
- utf8mb4_unicode_ci 比 utf8mb4_general_ci 排序更准确（正确识别特殊字符和变音符号）
- 对性能影响极小（现代 CPU 上差异可忽略）

### 1.8 事务隔离级别

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 事务隔离级别 | READ COMMITTED | 防止脏读，允许不可重复读和幻读 |
| 行锁模式 | InnoDB 默认（Next-Key Lock） | 间隙锁 + 记录锁，防止幻读在 SELECT...FOR UPDATE 场景 |

**选择理由：**
- REPEATABLE READ（MySQL 默认）在 HR 系统中过于严格，容易导致锁等待和死锁
- READ COMMITTED 已足够满足本系统并发需求（HR 操作频率低，主要为 Agent 批量处理）
- 关键操作（薪资核算、证书颁发）通过乐观锁（version 字段）保证最终一致性

### 1.9 数据量预估与容量规划

| 表名 | 预估日均增量 | 年增量 | 10 年预估 | 归档策略 |
|------|------------|--------|-----------|---------|
| employee | 5 条 | 1,825 条 | < 20,000 条 | 不归档 |
| attendance_record | 1,000 条 | 365,000 条 | ~3.7M 条 | 24 个月后离线归档 |
| payroll | 500 条 | 6,000 条 | < 70,000 条 | 15 年以上保留 |
| audit_log | 10,000 条 | 3.65M 条 | ~36M 条 | 10 年后离线归档 |
| agent_run_log | 5,000 条 | 1.83M 条 | ~18M 条 | 6 个月后离线归档 |
| resume | 50 条 | 18,250 条 | ~180,000 条 | 3 年后冷存储 |
| training_record | 10 条 | 3,650 条 | < 40,000 条 | 3 年后冷备 |
| exam_response | 20 条 | 7,300 条 | < 80,000 条 | 不归档 |

**容量规划建议：**
- 初始存储：50GB SSD（包含 10 年数据增长余量）
- InnoDB buffer pool：建议设置为物理内存的 70-80%
- 索引占比：预估为表数据的 30-40%
- 日志保留：binlog 保留 15 天，慢查询日志保留 30 天

---

## 2. 建表顺序与依赖说明

### 2.1 表创建顺序

本系统表创建需严格遵循外键依赖关系，按以下顺序执行：

```
1.  department (自引用外键: parent_id → dept_id)
2.  job_position (依赖 department)
3.  employee (依赖 department, job_position)
4.  [ALTER] department 添加 fk_dept_manager (依赖 employee)
5.  sys_user (依赖 employee)
6.  sys_role
7.  sys_permission (自引用外键: parent_id → permission_id)
8.  sys_user_role (依赖 sys_user, sys_role)
9.  sys_role_permission (依赖 sys_role, sys_permission)
10. resume (依赖 job_position)
11. job_post (依赖 job_position)
12. job_post_channel (依赖 job_post)
13. attendance_record (依赖 employee)
14. employee_pay_profile (依赖 employee)
15. payroll (依赖 employee)
16. performance_review (依赖 employee)
17. training_plan (依赖 department)
18. exam_question (无外键依赖)
19. exam_paper (依赖 job_position)
20. training_session (依赖 training_plan, exam_paper)
21. training_checkin (依赖 training_session, employee)
22. certificate (依赖 employee)
23. training_record (依赖 training_session, employee)
24. [ALTER] training_record 添加 fk_record_cert (依赖 certificate)
25. injury_case (依赖 employee)
26. housing_fund_record (依赖 employee)
27. resignation_record (依赖 employee)
28. certificate_request (依赖 employee)
29. expense_claim (依赖 employee)
30. paper_question (依赖 exam_paper, exam_question)
31. exam_response (依赖 exam_paper, employee, resume)
32. agent_run_log (无外键依赖)
33. audit_log (无外键依赖)
34. rpa_task (依赖 employee - 可选)
35. process_instance (无外键依赖)
36. notification_message (无外键依赖)
37. payroll_rule (无外键依赖)
38. video_course (无外键依赖)
```

### 2.2 循环依赖解决方案

**department ↔ employee 循环依赖：**

- `department.manager_id` 引用 `employee.employee_id`
- `employee.dept_id` 引用 `department.dept_id`

**解决方案：**

1. 先创建 `department` 表，`manager_id` 字段不建外键约束
2. 创建 `employee` 表，正常添加 `fk_emp_dept` 外键
3. 通过 `ALTER TABLE` 补充 `department` 的 `fk_dept_manager` 外键

具体 ALTER 语句见第 3.1 节末尾。

### 2.3 training_record ↔ certificate 依赖

`training_record.certificate_id` 引用 `certificate.cert_id`，但 training_record 在 certificate 之前定义。

**解决方案：**

1. 先创建 `training_record` 表，`certificate_id` 字段不加外键约束
2. 创建 `certificate` 表
3. 通过 `ALTER TABLE` 补充 `training_record` 的 `fk_record_cert` 外键

具体 ALTER 语句见第 4.12 节末尾。

---

## 3. 基础表结构

### 3.1 部门表 (department)

```sql
CREATE TABLE `department` (
  `dept_id` VARCHAR(20) NOT NULL COMMENT '部门ID (雪花算法生成)',
  `parent_id` VARCHAR(20) DEFAULT NULL COMMENT '父部门ID',
  `dept_name` VARCHAR(100) NOT NULL COMMENT '部门名称',
  `dept_code` VARCHAR(50) NOT NULL COMMENT '部门编码',
  `manager_id` VARCHAR(20) DEFAULT NULL COMMENT '部门负责人工号 (外键见本节末尾ALTER)',
  `level` INT NOT NULL DEFAULT 1 COMMENT '部门层级',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序号',
  `description` TEXT DEFAULT NULL COMMENT '部门描述',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/INACTIVE',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`dept_id`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_dept_code` (`dept_code`),
  KEY `idx_manager_id` (`manager_id`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_dept_parent` FOREIGN KEY (`parent_id`) REFERENCES `department` (`dept_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';
```

**循环依赖处理 — department.manager_id 外键补充：**

```sql
-- 在 employee 表创建后执行：
ALTER TABLE `department`
  ADD CONSTRAINT `fk_dept_manager` FOREIGN KEY (`manager_id`) REFERENCES `employee` (`employee_id`) ON DELETE SET NULL ON UPDATE CASCADE;
```

### 3.2 岗位表 (job_position)

```sql
CREATE TABLE `job_position` (
  `position_id` VARCHAR(20) NOT NULL COMMENT '岗位ID (雪花算法生成)',
  `dept_id` VARCHAR(20) NOT NULL COMMENT '所属部门ID',
  `position_name` VARCHAR(100) NOT NULL COMMENT '岗位名称',
  `position_code` VARCHAR(50) NOT NULL COMMENT '岗位编码',
  `job_level` VARCHAR(20) DEFAULT NULL COMMENT '职级',
  `head_count` INT NOT NULL DEFAULT 1 COMMENT '编制人数',
  `current_count` INT NOT NULL DEFAULT 0 COMMENT '在岗人数',
  `min_salary` DECIMAL(10,2) DEFAULT NULL COMMENT '最低薪资',
  `max_salary` DECIMAL(10,2) DEFAULT NULL COMMENT '最高薪资',
  `requirements` JSON DEFAULT NULL COMMENT '任职要求 (JSON schema: {education: string, years_of_exp: int, skills: string[], certs: string[]})',
  `description` TEXT DEFAULT NULL COMMENT '岗位描述',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/INACTIVE',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`position_id`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_position_code` (`position_code`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_pos_dept` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位表';
```

**job_position.requirements JSON Schema 规范：**

```json
{
  "education": "大专及以上",
  "years_of_exp": 3,
  "skills": ["技能1", "技能2"],
  "certs": ["证书1", "证书2"]
}
```

### 3.3 员工表 (employee)

```sql
CREATE TABLE `employee` (
  `employee_id` VARCHAR(20) NOT NULL COMMENT '工号 (雪花算法生成)',
  `name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `id_number_encrypted` VARBINARY(64) NOT NULL COMMENT '身份证号 (AES-256加密)',
  `id_number_hash` VARCHAR(64) NOT NULL COMMENT '身份证号SHA-256摘要 (用于去重)',
  `gender` CHAR(1) NOT NULL COMMENT '性别: M/F',
  `birth_date` DATE NOT NULL COMMENT '出生日期',
  `phone` VARCHAR(20) NOT NULL COMMENT '手机号码',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '电子邮箱',
  `dept_id` VARCHAR(20) DEFAULT NULL COMMENT '所属部门ID',
  `position_id` VARCHAR(20) DEFAULT NULL COMMENT '现任岗位ID',
  `education` VARCHAR(50) DEFAULT NULL COMMENT '最高学历',
  `graduation_school` VARCHAR(100) DEFAULT NULL COMMENT '毕业院校',
  `major` VARCHAR(100) DEFAULT NULL COMMENT '专业',
  `hire_date` DATE NOT NULL COMMENT '入职日期',
  `probation_end_date` DATE DEFAULT NULL COMMENT '试用期结束日期',
  `leave_date` DATE DEFAULT NULL COMMENT '离职日期 (NULL=在职)',
  `leave_reason` VARCHAR(20) DEFAULT NULL COMMENT '离职原因: QUIT/TERMINATE/RETIRE/EXPIRE',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PROBATION' COMMENT '状态: PROBATION/ACTIVE/LEAVE_OF_ABSENCE/RESIGNED',
  `emergency_contact` VARCHAR(50) DEFAULT NULL COMMENT '紧急联系人',
  `emergency_phone` VARCHAR(20) DEFAULT NULL COMMENT '紧急联系电话',
  `bank_name` VARCHAR(100) DEFAULT NULL COMMENT '开户银行',
  `bank_account` VARBINARY(64) DEFAULT NULL COMMENT '银行账号 (加密)',
  `face_feature_id` VARCHAR(50) DEFAULT NULL COMMENT '人脸特征ID',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`employee_id`),
  UNIQUE KEY `uk_id_number_hash` (`id_number_hash`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_position_id` (`position_id`),
  KEY `idx_status` (`status`),
  KEY `idx_hire_date` (`hire_date`),
  KEY `idx_leave_date` (`leave_date`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_emp_dept` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_emp_position` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工表';
```

### 3.4 系统用户表 (sys_user)

```sql
CREATE TABLE `sys_user` (
  `user_id` VARCHAR(20) NOT NULL COMMENT '用户ID (雪花算法生成)',
  `username` VARCHAR(50) NOT NULL COMMENT '登录账号',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希 (BCrypt)',
  `real_name` VARCHAR(50) NOT NULL COMMENT '真实姓名',
  `email` VARCHAR(100) NOT NULL COMMENT '电子邮箱',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号码',
  `employee_id` VARCHAR(20) DEFAULT NULL COMMENT '关联工号 (NULL=外部用户)',
  `mfa_enabled` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否启用MFA',
  `mfa_method` VARCHAR(20) DEFAULT 'SMS' COMMENT 'MFA方式: SMS/EMAIL/TOTP',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/LOCKED/DISABLED',
  `last_login_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` VARCHAR(45) DEFAULT NULL COMMENT '最后登录IP',
  `failed_login_count` INT NOT NULL DEFAULT 0 COMMENT '连续失败登录次数',
  `locked_until` TIMESTAMP NULL DEFAULT NULL COMMENT '锁定截止时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`),
  UNIQUE KEY `uk_phone` (`phone`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_user_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';
```

**设计说明：**
- `email` 为 NOT NULL，UNIQUE 约束对非空字段才能真正保证唯一性
- `phone` 增加 UNIQUE KEY `uk_phone`，手机号作为登录方式之一需保证唯一性（MySQL 下 UNIQUE 允许一个 NULL 值）

### 3.5 角色表 (sys_role)

```sql
CREATE TABLE `sys_role` (
  `role_id` VARCHAR(20) NOT NULL COMMENT '角色ID (雪花算法生成)',
  `role_name` VARCHAR(50) NOT NULL COMMENT '角色名称',
  `role_code` VARCHAR(50) NOT NULL COMMENT '角色编码',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '角色描述',
  `is_system` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否系统内置角色',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `uk_role_code` (`role_code`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';
```

### 3.6 权限表 (sys_permission)

```sql
CREATE TABLE `sys_permission` (
  `permission_id` VARCHAR(20) NOT NULL COMMENT '权限ID (雪花算法生成)',
  `permission_name` VARCHAR(100) NOT NULL COMMENT '权限名称',
  `permission_code` VARCHAR(100) NOT NULL COMMENT '权限编码 (module:resource:action)',
  `resource_type` VARCHAR(20) NOT NULL COMMENT '资源类型: MENU/API/BUTTON',
  `parent_id` VARCHAR(20) DEFAULT NULL COMMENT '父权限ID',
  `path` VARCHAR(200) DEFAULT NULL COMMENT '路由路径 (API路径)',
  `method` VARCHAR(10) DEFAULT NULL COMMENT 'HTTP方法 (GET/POST/PUT/DELETE)',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序号',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`permission_id`),
  UNIQUE KEY `uk_permission_code` (`permission_code`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_perm_parent` FOREIGN KEY (`parent_id`) REFERENCES `sys_permission` (`permission_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限表';
```

### 3.7 用户角色关联表 (sys_user_role)

```sql
CREATE TABLE `sys_user_role` (
  `user_id` VARCHAR(20) NOT NULL COMMENT '用户ID',
  `role_id` VARCHAR(20) NOT NULL COMMENT '角色ID',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `assigned_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分配时间',
  `assigned_by` VARCHAR(20) DEFAULT NULL COMMENT '分配人ID',
  PRIMARY KEY (`user_id`, `role_id`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `fk_ur_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_ur_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`role_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';
```

### 3.8 角色权限关联表 (sys_role_permission)

```sql
CREATE TABLE `sys_role_permission` (
  `role_id` VARCHAR(20) NOT NULL COMMENT '角色ID',
  `permission_id` VARCHAR(20) NOT NULL COMMENT '权限ID',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `granted_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '授予时间',
  `granted_by` VARCHAR(20) DEFAULT NULL COMMENT '授予人ID',
  PRIMARY KEY (`role_id`, `permission_id`),
  KEY `idx_permission_id` (`permission_id`),
  CONSTRAINT `fk_rp_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`role_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_rp_permission` FOREIGN KEY (`permission_id`) REFERENCES `sys_permission` (`permission_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';
```

**RBAC 模型说明：** 角色与权限为 M:N 关系，通过 sys_role_permission 中间表实现。一个权限可授予多个角色，一个角色可拥有多个权限，符合权限管理最佳实践。

---

## 4. 业务表结构

### 4.1 简历表 (resume)

```sql
CREATE TABLE `resume` (
  `resume_id` VARCHAR(20) NOT NULL COMMENT '简历ID (雪花算法生成)',
  `candidate_name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `id_number` VARBINARY(64) DEFAULT NULL COMMENT '身份证号 (加密, 用于去重)',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号 (用于去重)',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '电子邮箱',
  `source_platform` VARCHAR(50) NOT NULL COMMENT '来源平台: 前程无忧/中国人才热线/手动导入/其他',
  `education` VARCHAR(50) DEFAULT NULL COMMENT '最高学历',
  `years_of_exp` INT DEFAULT NULL COMMENT '从业年限',
  `skill_tags` TEXT DEFAULT NULL COMMENT '技能标签 (逗号分隔)',
  `age` INT DEFAULT NULL COMMENT '年龄',
  `certs` TEXT DEFAULT NULL COMMENT '持证情况',
  `position_id` VARCHAR(20) NOT NULL COMMENT '应聘岗位ID',
  `total_score` DECIMAL(5,2) DEFAULT NULL COMMENT '综合匹配分 (0-100)',
  `education_score` DECIMAL(5,2) DEFAULT NULL COMMENT '学历匹配分',
  `experience_score` DECIMAL(5,2) DEFAULT NULL COMMENT '经验匹配分',
  `skill_score` DECIMAL(5,2) DEFAULT NULL COMMENT '技能匹配分',
  `age_score` DECIMAL(5,2) DEFAULT NULL COMMENT '年龄匹配分',
  `cert_score` DECIMAL(5,2) DEFAULT NULL COMMENT '证书匹配分',
  `semantic_score` DECIMAL(5,2) DEFAULT NULL COMMENT '语义综合匹配分',
  `classify_result` VARCHAR(20) DEFAULT NULL COMMENT '分拣结果: HIGH_POTENTIAL/CANDIDATE/ELIMINATED',
  `score_reasoning` TEXT DEFAULT NULL COMMENT '评分推理摘要',
  `score_model_version` VARCHAR(20) DEFAULT NULL COMMENT '评分模型版本',
  `scored_at` TIMESTAMP NULL DEFAULT NULL COMMENT '评分时间',
  `file_uri` VARCHAR(500) DEFAULT NULL COMMENT '简历文件链接 (MinIO URI)',
  `file_format` VARCHAR(10) DEFAULT NULL COMMENT '文件类型: PDF/DOC/DOCX/JPG',
  `interview_status` VARCHAR(20) DEFAULT NULL COMMENT '面试状态: PENDING/INVITED/ATTENDED/PASSED/FAILED',
  `interview_date` DATE DEFAULT NULL COMMENT '面试日期',
  `interview_score` DECIMAL(5,2) DEFAULT NULL COMMENT '面试成绩',
  `hire_status` VARCHAR(20) DEFAULT NULL COMMENT '录用状态: OFFERED/ACCEPTED/DECLINED/NOT_HIRED',
  `employee_id` VARCHAR(20) DEFAULT NULL COMMENT '转正后关联工号',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `data_status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '数据状态: ACTIVE/COLD/ARCHIVED',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`resume_id`),
  KEY `idx_candidate_name` (`candidate_name`),
  KEY `idx_phone` (`phone`),
  KEY `idx_position_id` (`position_id`),
  KEY `idx_classify_result` (`classify_result`),
  KEY `idx_interview_status` (`interview_status`),
  KEY `idx_hire_status` (`hire_status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_total_score` (`total_score`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_resume_position` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';
```

### 4.2 岗位发布表 (job_post)

```sql
CREATE TABLE `job_post` (
  `post_id` VARCHAR(20) NOT NULL COMMENT '发布ID (雪花算法生成)',
  `position_id` VARCHAR(20) NOT NULL COMMENT '岗位ID',
  `title` VARCHAR(200) NOT NULL COMMENT '发布标题',
  `description` TEXT NOT NULL COMMENT '职位描述',
  `salary_min` DECIMAL(10,2) DEFAULT NULL COMMENT '薪资下限',
  `salary_max` DECIMAL(10,2) DEFAULT NULL COMMENT '薪资上限',
  `head_count` INT NOT NULL DEFAULT 1 COMMENT '招聘人数',
  `deadline` DATE DEFAULT NULL COMMENT '截止日期',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/PUBLISHED/CLOSED/EXPIRED',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人ID',
  `published_at` TIMESTAMP NULL DEFAULT NULL COMMENT '发布时间',
  `closed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '关闭时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`post_id`),
  KEY `idx_position_id` (`position_id`),
  KEY `idx_status` (`status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_post_position` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位发布表';
```

### 4.3 岗位发布渠道表 (job_post_channel)

```sql
CREATE TABLE `job_post_channel` (
  `channel_id` VARCHAR(20) NOT NULL COMMENT '渠道记录ID (雪花算法生成)',
  `post_id` VARCHAR(20) NOT NULL COMMENT '发布ID',
  `platform` VARCHAR(50) NOT NULL COMMENT '平台: 前程无忧/中国人才热线/BOSS直聘',
  `platform_post_id` VARCHAR(100) DEFAULT NULL COMMENT '平台侧帖子ID',
  `platform_url` VARCHAR(500) DEFAULT NULL COMMENT '平台帖子URL',
  `publish_status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/PUBLISHED/FAILED/REMOVED',
  `applicant_count` INT NOT NULL DEFAULT 0 COMMENT '投递量',
  `last_synced_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最后同步时间',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `published_at` TIMESTAMP NULL DEFAULT NULL COMMENT '发布时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`channel_id`),
  KEY `idx_post_id` (`post_id`),
  KEY `idx_platform` (`platform`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_channel_post` FOREIGN KEY (`post_id`) REFERENCES `job_post` (`post_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位发布渠道表';
```

### 4.4 考勤记录表 (attendance_record)

```sql
CREATE TABLE `attendance_record` (
  `record_id` VARCHAR(20) NOT NULL COMMENT '记录ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `date` DATE NOT NULL COMMENT '日期',
  `clock_in` TIME DEFAULT NULL COMMENT '上班打卡时间',
  `clock_out` TIME DEFAULT NULL COMMENT '下班打卡时间',
  `shift_id` VARCHAR(20) DEFAULT NULL COMMENT '班次ID',
  `expected_clock_in` TIME DEFAULT NULL COMMENT '应到时间',
  `expected_clock_out` TIME DEFAULT NULL COMMENT '应离时间',
  `late_minutes` INT NOT NULL DEFAULT 0 COMMENT '迟到分钟数',
  `early_leave_minutes` INT NOT NULL DEFAULT 0 COMMENT '早退分钟数',
  `absent_days` DECIMAL(3,2) NOT NULL DEFAULT 0 COMMENT '旷工天数',
  `holiday_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '事假小时数',
  `sick_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '病假小时数',
  `overtime_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '加班小时数',
  `business_trip` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否出差',
  `remark` VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `flag` VARCHAR(20) DEFAULT NULL COMMENT '异常标志: LATE/EARLY_LEAVE/ABSENT/OVERTIME_EXCEEDED/NORMAL',
  `data_source` VARCHAR(20) DEFAULT NULL COMMENT '数据来源: 打卡设备/手动/系统计算',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`record_id`),
  UNIQUE KEY `uk_emp_date` (`employee_id`, `date`),
  KEY `idx_date` (`date`),
  KEY `idx_flag` (`flag`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_attendance_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考勤记录表';
```

### 4.5 员工薪资档案表 (employee_pay_profile)

```sql
CREATE TABLE `employee_pay_profile` (
  `profile_id` VARCHAR(20) NOT NULL COMMENT '档案ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `base_salary` DECIMAL(10,2) NOT NULL COMMENT '基本工资',
  `position_allowance` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '岗位津贴',
  `meal_allowance` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '餐补',
  `transport_allowance` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '交通补',
  `housing_allowance` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '住房补贴',
  `performance_base` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '绩效奖金基数',
  `ss_base` DECIMAL(10,2) NOT NULL COMMENT '社保缴费基数',
  `gf_base` DECIMAL(10,2) NOT NULL COMMENT '公积金缴费基数',
  `gf_ratio` DECIMAL(5,2) NOT NULL DEFAULT 12.00 COMMENT '公积金缴存比例 (%)',
  `effective_date` DATE NOT NULL COMMENT '生效日期',
  `is_active` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否当前有效: 1=当前生效, 0=历史版本',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 1 COMMENT '乐观锁版本号',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`profile_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_effective_date` (`effective_date`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_pay_profile_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工薪资档案表';
```

**ER 关系说明：** employee_pay_profile 为员工薪资主档案表，记录薪资结构的历史变更版本（通过 is_active + effective_date 管理）。payroll 为每期（月度）薪资计算记录表，引用 employee_pay_profile 的当前有效版本进行核算。关系方向为：employee → employee_pay_profile (1:N，一个员工有多个薪资档案版本)，employee → payroll (1:N，一个员工有多条月度薪资记录)。表名 employee_pay_profile 在 ER 图、实体关系表和 DDL 中保持一致。

### 4.6 薪资表 (payroll)

```sql
CREATE TABLE `payroll` (
  `payroll_id` VARCHAR(20) NOT NULL COMMENT '薪资记录ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `month` VARCHAR(7) NOT NULL COMMENT '月份 (YYYY-MM)',
  `base_pay` DECIMAL(10,2) NOT NULL COMMENT '基本工资',
  `overtime_pay` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '加班费',
  `attendance_deduct` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '考勤扣款',
  `allowances_total` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '补贴合计',
  `deduction_total` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '扣款合计',
  `ss_personal` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '社保个人缴纳',
  `gf_personal` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '公积金个人缴纳',
  `income_tax` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '个税',
  `net_pay` DECIMAL(10,2) NOT NULL COMMENT '实发工资',
  `gross_pay` DECIMAL(10,2) NOT NULL COMMENT '应发工资',
  `taxable_income` DECIMAL(10,2) NOT NULL COMMENT '应税收入',
  `special_deduction` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '专项附加扣除',
  `anomaly_flags` JSON DEFAULT NULL COMMENT '异常标记 (JSON数组)',
  `calculation_trace` JSON DEFAULT NULL COMMENT '计算溯源 (JSON)',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'CALCULATED' COMMENT '状态: CALCULATED/REVIEWED/PAID',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `paid_at` TIMESTAMP NULL DEFAULT NULL COMMENT '发放时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`payroll_id`),
  UNIQUE KEY `uk_emp_month` (`employee_id`, `month`),
  KEY `idx_month` (`month`),
  KEY `idx_status` (`status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_payroll_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资表';
```

### 4.7 绩效表 (performance_review)

```sql
CREATE TABLE `performance_review` (
  `pr_id` VARCHAR(20) NOT NULL COMMENT '考核记录ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `cycle` VARCHAR(7) NOT NULL COMMENT '考核周期 (YYYY-MM 或 YYYY-Q1)',
  `cycle_type` VARCHAR(20) NOT NULL COMMENT '周期类型: MONTHLY/QUARTERLY/ANNUALLY',
  `self_score` DECIMAL(5,2) DEFAULT NULL COMMENT '自评分',
  `self_comment` TEXT DEFAULT NULL COMMENT '自评说明',
  `mgr_score` DECIMAL(5,2) DEFAULT NULL COMMENT '上级评分',
  `mgr_comment` TEXT DEFAULT NULL COMMENT '上级评语',
  `peer_score` DECIMAL(5,2) DEFAULT NULL COMMENT '同事互评分',
  `subordinate_score` DECIMAL(5,2) DEFAULT NULL COMMENT '下属评议分',
  `final_score` DECIMAL(5,2) DEFAULT NULL COMMENT '综合得分',
  `rating` VARCHAR(2) DEFAULT NULL COMMENT '等级: S/A/B/C/D',
  `weight_self` DECIMAL(5,2) NOT NULL DEFAULT 30.00 COMMENT '自评权重 (%)',
  `weight_mgr` DECIMAL(5,2) NOT NULL DEFAULT 50.00 COMMENT '上级权重 (%)',
  `weight_peer` DECIMAL(5,2) NOT NULL DEFAULT 10.00 COMMENT '互评权重 (%)',
  `weight_sub` DECIMAL(5,2) NOT NULL DEFAULT 10.00 COMMENT '下属权重 (%)',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/SUBMITTED/APPROVED/REJECTED',
  `submit_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `approve_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审批时间',
  `approved_by` VARCHAR(20) DEFAULT NULL COMMENT '审批人ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`pr_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_cycle` (`cycle`),
  KEY `idx_status` (`status`),
  KEY `idx_rating` (`rating`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_performance_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='绩效表';
```

### 4.8 培训计划表 (training_plan)

```sql
CREATE TABLE `training_plan` (
  `plan_id` VARCHAR(20) NOT NULL COMMENT '计划ID (雪花算法生成)',
  `plan_name` VARCHAR(200) NOT NULL COMMENT '计划名称',
  `training_type` VARCHAR(20) NOT NULL COMMENT '培训类型: ONBOARDING/REGULAR/SPECIAL_EQUIPMENT/SAFETY',
  `quarter` VARCHAR(7) NOT NULL COMMENT '季度 (YYYY-Q1)',
  `dept_id` VARCHAR(20) DEFAULT NULL COMMENT '申请部门ID (NULL=公司级)',
  `description` TEXT DEFAULT NULL COMMENT '计划描述',
  `total_sessions` INT NOT NULL DEFAULT 0 COMMENT '计划场次',
  `completed_sessions` INT NOT NULL DEFAULT 0 COMMENT '已完成场次',
  `total_participants` INT NOT NULL DEFAULT 0 COMMENT '参训人数',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/APPROVED/IN_PROGRESS/COMPLETED/CANCELLED',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人ID',
  `approved_by` VARCHAR(20) DEFAULT NULL COMMENT '审批人ID',
  `approved_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审批时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`plan_id`),
  KEY `idx_training_type` (`training_type`),
  KEY `idx_quarter` (`quarter`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_plan_dept` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训计划表';
```

### 4.9 题目表 (exam_question)

```sql
CREATE TABLE `exam_question` (
  `question_id` VARCHAR(20) NOT NULL COMMENT '题目ID (雪花算法生成)',
  `category` VARCHAR(50) NOT NULL COMMENT '科目: GENERAL/PROFESSIONAL/MANAGEMENT/SAFETY',
  `question_type` VARCHAR(20) NOT NULL COMMENT '题型: SINGLE_CHOICE/MULTI_CHOICE/TRUE_FALSE/ESSAY',
  `difficulty` INT NOT NULL COMMENT '难度: 1-10',
  `score` DECIMAL(5,2) NOT NULL COMMENT '分值',
  `content` TEXT NOT NULL COMMENT '题目内容',
  `options` JSON DEFAULT NULL COMMENT '选项 (JSON数组)',
  `correct_answer` TEXT NOT NULL COMMENT '正确答案',
  `explanation` TEXT DEFAULT NULL COMMENT '解析',
  `tags` TEXT DEFAULT NULL COMMENT '标签 (逗号分隔)',
  `usage_count` INT NOT NULL DEFAULT 0 COMMENT '使用次数',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/INACTIVE',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`question_id`),
  KEY `idx_category` (`category`),
  KEY `idx_question_type` (`question_type`),
  KEY `idx_difficulty` (`difficulty`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目表';
```

### 4.10 试卷表 (exam_paper)

```sql
CREATE TABLE `exam_paper` (
  `paper_id` VARCHAR(20) NOT NULL COMMENT '试卷ID (雪花算法生成)',
  `position_id` VARCHAR(20) DEFAULT NULL COMMENT '关联岗位ID (NULL=培训考试)',
  `training_session_id` VARCHAR(20) DEFAULT NULL COMMENT '关联培训场次ID',
  `paper_name` VARCHAR(200) NOT NULL COMMENT '试卷名称',
  `question_count` INT NOT NULL DEFAULT 40 COMMENT '题目数量',
  `single_choice_count` INT NOT NULL DEFAULT 16 COMMENT '单选题数',
  `multi_choice_count` INT NOT NULL DEFAULT 12 COMMENT '多选题数',
  `true_false_count` INT NOT NULL DEFAULT 12 COMMENT '判断题数',
  `total_score` DECIMAL(5,2) NOT NULL DEFAULT 100 COMMENT '总分',
  `pass_score` DECIMAL(5,2) NOT NULL DEFAULT 60 COMMENT '及格分',
  `duration_minutes` INT NOT NULL DEFAULT 60 COMMENT '考试时长 (分钟)',
  `qr_code` VARCHAR(100) DEFAULT NULL COMMENT '考试二维码',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/REVIEWED/PUBLISHED/CLOSED',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `published_at` TIMESTAMP NULL DEFAULT NULL COMMENT '发布时间',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人/Agent',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`paper_id`),
  KEY `idx_position_id` (`position_id`),
  KEY `idx_training_session_id` (`training_session_id`),
  KEY `idx_status` (`status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_paper_position` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷表';
```

### 4.11 培训场次表 (training_session)

```sql
CREATE TABLE `training_session` (
  `session_id` VARCHAR(20) NOT NULL COMMENT '场次ID (雪花算法生成)',
  `plan_id` VARCHAR(20) NOT NULL COMMENT '计划ID',
  `session_name` VARCHAR(200) NOT NULL COMMENT '场次名称',
  `trainer` VARCHAR(100) DEFAULT NULL COMMENT '讲师',
  `location` VARCHAR(200) DEFAULT NULL COMMENT '培训地点',
  `start_time` DATETIME NOT NULL COMMENT '开始时间',
  `end_time` DATETIME NOT NULL COMMENT '结束时间',
  `qr_code` VARCHAR(100) DEFAULT NULL COMMENT '签到二维码',
  `expected_count` INT NOT NULL DEFAULT 0 COMMENT '预期人数',
  `actual_count` INT NOT NULL DEFAULT 0 COMMENT '实际签到人数',
  `exam_required` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否需要考试',
  `exam_paper_id` VARCHAR(20) DEFAULT NULL COMMENT '关联试卷ID',
  `certificate_template` VARCHAR(50) DEFAULT NULL COMMENT '证书模板',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED' COMMENT '状态: SCHEDULED/IN_PROGRESS/COMPLETED/CANCELLED',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`session_id`),
  KEY `idx_plan_id` (`plan_id`),
  KEY `idx_start_time` (`start_time`),
  KEY `idx_qr_code` (`qr_code`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_session_plan` FOREIGN KEY (`plan_id`) REFERENCES `training_plan` (`plan_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_session_paper` FOREIGN KEY (`exam_paper_id`) REFERENCES `exam_paper` (`paper_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训场次表';
```

### 4.12 培训签到记录表 (training_checkin)

```sql
CREATE TABLE `training_checkin` (
  `checkin_id` VARCHAR(20) NOT NULL COMMENT '签到ID (雪花算法生成)',
  `session_id` VARCHAR(20) NOT NULL COMMENT '场次ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `checkin_time` DATETIME NOT NULL COMMENT '签到时间',
  `checkin_method` VARCHAR(20) NOT NULL COMMENT '签到方式: QR_CODE/MANUAL/AGENT',
  `location_lat` DECIMAL(10,7) DEFAULT NULL COMMENT '签到纬度',
  `location_lng` DECIMAL(10,7) DEFAULT NULL COMMENT '签到经度',
  `is_late` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否迟到',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PRESENT' COMMENT '状态: PRESENT/ABSENT/LATE',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`checkin_id`),
  UNIQUE KEY `uk_session_emp` (`session_id`, `employee_id`),
  KEY `idx_checkin_time` (`checkin_time`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_checkin_session` FOREIGN KEY (`session_id`) REFERENCES `training_session` (`session_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_checkin_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训签到记录表';
```

### 4.13 培训记录表 (training_record)

```sql
CREATE TABLE `training_record` (
  `record_id` VARCHAR(20) NOT NULL COMMENT '记录ID (雪花算法生成)',
  `session_id` VARCHAR(20) NOT NULL COMMENT '场次ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `exam_score` DECIMAL(5,2) DEFAULT NULL COMMENT '考试成绩',
  `exam_pass` TINYINT(1) DEFAULT NULL COMMENT '考试是否合格',
  `certificate_id` VARCHAR(20) DEFAULT NULL COMMENT '关联证书ID (外键见本节末尾ALTER)',
  `certificate_issue_date` DATE DEFAULT NULL COMMENT '证书颁发日期',
  `certificate_expire_date` DATE DEFAULT NULL COMMENT '证书到期日期',
  `satisfaction_score` DECIMAL(3,1) DEFAULT NULL COMMENT '满意度评分 (1-5)',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`record_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_certificate_expire` (`certificate_expire_date`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_record_session` FOREIGN KEY (`session_id`) REFERENCES `training_session` (`session_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_record_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训记录表';
```

**certificate 外键补充（循环依赖处理）：**

```sql
-- 在 certificate 表创建后执行：
ALTER TABLE `training_record`
  ADD CONSTRAINT `fk_record_cert` FOREIGN KEY (`certificate_id`) REFERENCES `certificate` (`cert_id`) ON DELETE SET NULL ON UPDATE CASCADE;
```

### 4.14 证书台账表 (certificate)

```sql
CREATE TABLE `certificate` (
  `cert_id` VARCHAR(20) NOT NULL COMMENT '证书ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `cert_type` VARCHAR(50) NOT NULL COMMENT '证书类型: SPECIAL_EQUIPMENT/SAFETY/QUALIFICATION/UPSKILLING',
  `cert_name` VARCHAR(200) NOT NULL COMMENT '证书名称',
  `cert_number` VARCHAR(100) DEFAULT NULL COMMENT '证书编号',
  `issuing_authority` VARCHAR(200) DEFAULT NULL COMMENT '颁发机构',
  `issue_date` DATE NOT NULL COMMENT '颁发日期',
  `expire_date` DATE DEFAULT NULL COMMENT '到期日期',
  `file_uri` VARCHAR(500) DEFAULT NULL COMMENT '证书文件链接',
  `renewal_status` VARCHAR(20) NOT NULL DEFAULT 'VALID' COMMENT '续期状态: VALID/EXPIRING/EXPIRED/RENEWING/RENEWED',
  `alert_60_days` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '60天预警已触发',
  `alert_30_days` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '30天预警已触发',
  `alert_7_days` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '7天预警已触发',
  `alert_1_day` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1天预警已触发',
  `remark` TEXT DEFAULT NULL COMMENT '备注',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`cert_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_cert_type` (`cert_type`),
  KEY `idx_expire_date` (`expire_date`),
  KEY `idx_renewal_status` (`renewal_status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_cert_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证书台账表';
```

### 4.15 工伤档案表 (injury_case)

```sql
CREATE TABLE `injury_case` (
  `case_id` VARCHAR(20) NOT NULL COMMENT '案件编号 (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '受伤员工ID',
  `accident_date` DATE NOT NULL COMMENT '事故发生日期',
  `accident_location` VARCHAR(200) DEFAULT NULL COMMENT '事故地点',
  `description` TEXT NOT NULL COMMENT '事故描述',
  `injury_level` VARCHAR(20) DEFAULT NULL COMMENT '伤害等级',
  `docs` JSON DEFAULT NULL COMMENT '上传材料清单和路径 (JSON)',
  `diagnosis_doc_uri` VARCHAR(500) DEFAULT NULL COMMENT '诊断书文件链接',
  `witness_statements` JSON DEFAULT NULL COMMENT '旁证陈述 (JSON)',
  `filing_no` VARCHAR(50) DEFAULT NULL COMMENT '备案受理号',
  `filing_date` DATE DEFAULT NULL COMMENT '备案日期',
  `claim_amount` DECIMAL(10,2) DEFAULT NULL COMMENT '理赔金额',
  `received_amount` DECIMAL(10,2) DEFAULT NULL COMMENT '实际到账金额',
  `received_date` DATE DEFAULT NULL COMMENT '到账日期',
  `rpa_receipts` JSON DEFAULT NULL COMMENT 'RPA操作截图凭证 (JSON)',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'OPENING' COMMENT '状态: OPENING/FILED/CLAIMING/COMPLETED/REJECTED',
  `handler_id` VARCHAR(20) DEFAULT NULL COMMENT '处理人ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`case_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_accident_date` (`accident_date`),
  KEY `idx_status` (`status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_injury_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工伤档案表';
```

### 4.16 公积金记录表 (housing_fund_record)

```sql
CREATE TABLE `housing_fund_record` (
  `record_id` VARCHAR(20) NOT NULL COMMENT '记录ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `operation_type` VARCHAR(20) NOT NULL COMMENT '操作类型: ENROLL/SEAL/SUPPLEMENT/CANCEL',
  `account_number` VARCHAR(50) DEFAULT NULL COMMENT '公积金账号',
  `contribution_base` DECIMAL(10,2) DEFAULT NULL COMMENT '缴存基数',
  `contribution_ratio` DECIMAL(5,2) DEFAULT NULL COMMENT '缴存比例 (%)',
  `personal_amount` DECIMAL(10,2) DEFAULT NULL COMMENT '个人缴存额',
  `company_amount` DECIMAL(10,2) DEFAULT NULL COMMENT '公司缴存额',
  `effective_month` VARCHAR(7) DEFAULT NULL COMMENT '生效月份 (YYYY-MM)',
  `rpa_screenshot_uri` VARCHAR(500) DEFAULT NULL COMMENT 'RPA操作截图',
  `receipt_uri` VARCHAR(500) DEFAULT NULL COMMENT '操作回执文件',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/SUCCESS/FAILED',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `completed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
  `triggered_by` VARCHAR(20) DEFAULT NULL COMMENT '触发人/Agent',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`record_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_operation_type` (`operation_type`),
  KEY `idx_effective_month` (`effective_month`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_hf_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公积金记录表';
```

### 4.17 离职记录表 (resignation_record)

```sql
CREATE TABLE `resignation_record` (
  `resign_id` VARCHAR(20) NOT NULL COMMENT '离职记录ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `resign_date` DATE NOT NULL COMMENT '申请离职日期',
  `last_work_date` DATE NOT NULL COMMENT '最后工作日',
  `resign_reason` TEXT DEFAULT NULL COMMENT '离职原因',
  `resign_letter_uri` VARCHAR(500) DEFAULT NULL COMMENT '离职申请书文件',
  `handover_checklist` JSON DEFAULT NULL COMMENT '交接清单 (JSON)',
  `handover_status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '交接状态: PENDING/IN_PROGRESS/COMPLETED',
  `it_handover` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'IT交接完成',
  `admin_handover` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '行政交接完成',
  `finance_handover` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '财务交接完成',
  `hr_handover` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'HR交接完成',
  `certificate_issued` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '离职证明已开具',
  `certificate_uri` VARCHAR(500) DEFAULT NULL COMMENT '离职证明文件',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'APPLIED' COMMENT '状态: APPLIED/APPROVED/HANDOVERING/COMPLETED/CANCELLED',
  `approved_by` VARCHAR(20) DEFAULT NULL COMMENT '审批人ID',
  `approved_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审批时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`resign_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_status` (`status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_resign_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='离职记录表';
```

### 4.18 证明申请表 (certificate_request)

```sql
CREATE TABLE `certificate_request` (
  `request_id` VARCHAR(20) NOT NULL COMMENT '申请ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `cert_type` VARCHAR(50) NOT NULL COMMENT '证明类型: EMPLOYMENT_INCOME/RESIGNATION/OTHER',
  `purpose` VARCHAR(200) DEFAULT NULL COMMENT '用途说明',
  `custom_content` TEXT DEFAULT NULL COMMENT '自定义内容',
  `generated_file_uri` VARCHAR(500) DEFAULT NULL COMMENT '生成证明文件链接',
  `review_status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '审核状态: PENDING/APPROVED/REJECTED',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `reject_reason` TEXT DEFAULT NULL COMMENT '驳回原因',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`request_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_cert_type` (`cert_type`),
  KEY `idx_review_status` (`review_status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_cert_req_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证明申请表';
```

### 4.19 费用报销表 (expense_claim)

```sql
CREATE TABLE `expense_claim` (
  `claim_id` VARCHAR(20) NOT NULL COMMENT '报销ID (雪花算法生成)',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `claim_date` DATE NOT NULL COMMENT '报销日期',
  `category` VARCHAR(50) NOT NULL COMMENT '费用类别: TRAVEL/MEAL/TRANSPORT/OFFICE/TRAINING/OTHER',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '报销金额',
  `receipt_count` INT NOT NULL DEFAULT 0 COMMENT '票据张数',
  `receipts` JSON DEFAULT NULL COMMENT '票据信息 (JSON: 商户/日期/金额/品目)',
  `receipt_files` JSON DEFAULT NULL COMMENT '票据文件链接 (JSON数组)',
  `ocr_result` JSON DEFAULT NULL COMMENT 'OCR识别结果 (JSON)',
  `receipt_verification` JSON DEFAULT NULL COMMENT '发票真伪查验结果 (JSON)',
  `description` TEXT DEFAULT NULL COMMENT '费用说明',
  `review_status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '审核状态: PENDING/APPROVED/REJECTED/PAID',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `paid_amount` DECIMAL(10,2) DEFAULT NULL COMMENT '实付金额',
  `paid_at` TIMESTAMP NULL DEFAULT NULL COMMENT '支付时间',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`claim_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_claim_date` (`claim_date`),
  KEY `idx_category` (`category`),
  KEY `idx_review_status` (`review_status`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_claim_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='费用报销表';
```

### 4.20 试卷-题目关联表 (paper_question)

```sql
CREATE TABLE `paper_question` (
  `paper_question_id` VARCHAR(20) NOT NULL COMMENT '关联ID (雪花算法生成)',
  `paper_id` VARCHAR(20) NOT NULL COMMENT '试卷ID',
  `question_id` VARCHAR(20) NOT NULL COMMENT '题目ID',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '题目排序号',
  `score_override` DECIMAL(5,2) DEFAULT NULL COMMENT '分数覆盖 (NULL=使用题目默认分值)',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`paper_question_id`),
  UNIQUE KEY `uk_paper_question` (`paper_id`, `question_id`),
  KEY `idx_question_id` (`question_id`),
  KEY `idx_tenant` (`tenant_id`),
  CONSTRAINT `fk_pq_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper` (`paper_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_pq_question` FOREIGN KEY (`question_id`) REFERENCES `exam_question` (`question_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷-题目关联表';
```

### 4.21 考试答题记录表 (exam_response)

```sql
CREATE TABLE `exam_response` (
  `response_id` VARCHAR(20) NOT NULL COMMENT '答题记录ID (雪花算法生成)',
  `paper_id` VARCHAR(20) NOT NULL COMMENT '试卷ID',
  `employee_id` VARCHAR(20) DEFAULT NULL COMMENT '员工ID (正式考试)',
  `candidate_name` VARCHAR(50) DEFAULT NULL COMMENT '考生姓名 (面试考试)',
  `resume_id` VARCHAR(20) DEFAULT NULL COMMENT '简历ID (面试考试)',
  `start_time` DATETIME NOT NULL COMMENT '开始时间',
  `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
  `answers` JSON NOT NULL COMMENT '答题记录 (JSON)',
  `total_score` DECIMAL(5,2) DEFAULT NULL COMMENT '总分',
  `objectives_score` DECIMAL(5,2) DEFAULT NULL COMMENT '客观题得分',
  `subjective_score` DECIMAL(5,2) DEFAULT NULL COMMENT '主观题得分',
  `ai_cross_score` JSON DEFAULT NULL COMMENT 'AI交叉评分结果 (JSON: 模型A分/模型B分/差异/结论)',
  `pass_result` TINYINT(1) DEFAULT NULL COMMENT '是否通过',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS' COMMENT '状态: IN_PROGRESS/SUBMITTED/GRADED/REVIEW_NEEDED',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`response_id`),
  KEY `idx_paper_id` (`paper_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_resume_id` (`resume_id`),
  KEY `idx_status` (`status`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试答题记录表';
```

---

## 5. Agent 与审计表

### 5.1 Agent 执行日志表 (agent_run_log)

```sql
CREATE TABLE `agent_run_log` (
  `run_id` VARCHAR(32) NOT NULL COMMENT '执行流水号 (UUID)',
  `agent_name` VARCHAR(100) NOT NULL COMMENT 'Agent名称',
  `parent_flow_id` VARCHAR(32) DEFAULT NULL COMMENT '所属业务流程ID',
  `inputs_summary` JSON DEFAULT NULL COMMENT '输入概要',
  `reasoning_trace` TEXT DEFAULT NULL COMMENT '推理过程摘要',
  `outputs_summary` JSON DEFAULT NULL COMMENT '输出概要',
  `model_version` VARCHAR(20) DEFAULT NULL COMMENT '使用的模型版本',
  `status` VARCHAR(20) NOT NULL COMMENT '状态: SUCCESS/FAILED/SUSPENDED/BLOCKED',
  `duration_ms` BIGINT DEFAULT NULL COMMENT '耗时 (毫秒)',
  `error_detail` TEXT DEFAULT NULL COMMENT '错误堆栈',
  `retry_count` INT NOT NULL DEFAULT 0 COMMENT '重试次数',
  `guardrail_triggered` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否触发护栏',
  `guardrail_reason` VARCHAR(500) DEFAULT NULL COMMENT '护栏触发原因',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
  PRIMARY KEY (`run_id`),
  KEY `idx_agent_name` (`agent_name`),
  KEY `idx_parent_flow_id` (`parent_flow_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent执行日志表';
```

### 5.2 审计日志表 (audit_log)

```sql
CREATE TABLE `audit_log` (
  `log_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `operation_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  `operator_id` VARCHAR(20) NOT NULL COMMENT '操作人ID',
  `operator_name` VARCHAR(50) NOT NULL COMMENT '操作人姓名',
  `operator_ip` VARCHAR(45) NOT NULL COMMENT '操作者IP',
  `operation_type` VARCHAR(20) NOT NULL COMMENT '操作类型: CREATE/UPDATE/DELETE/VIEW/EXPORT/LOGIN/LOGOUT/AGENT_CALL',
  `module` VARCHAR(50) NOT NULL COMMENT '操作模块: RECRUITMENT/ONBOARDING/TRAINING/ATTENDANCE/PAYROLL/PERFORMANCE/EXTERNAL/RESIGNATION',
  `target_id` VARCHAR(50) DEFAULT NULL COMMENT '操作对象ID',
  `target_name` VARCHAR(100) DEFAULT NULL COMMENT '操作对象名称',
  `before_snapshot` JSON DEFAULT NULL COMMENT '变更前快照',
  `after_snapshot` JSON DEFAULT NULL COMMENT '变更后快照',
  `result` VARCHAR(20) NOT NULL COMMENT '结果: SUCCESS/FAILED',
  `duration_ms` INT NOT NULL COMMENT '耗时 (毫秒)',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '客户端User-Agent',
  `trace_id` VARCHAR(64) DEFAULT NULL COMMENT '链路追踪ID',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  PRIMARY KEY (`log_id`),
  KEY `idx_operation_time` (`operation_time`),
  KEY `idx_operator_id` (`operator_id`),
  KEY `idx_module` (`module`),
  KEY `idx_operation_type` (`operation_type`),
  KEY `idx_target_id` (`target_id`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';
```

### 5.3 RPA 任务表 (rpa_task)

```sql
CREATE TABLE `rpa_task` (
  `task_id` VARCHAR(20) NOT NULL COMMENT '任务ID (雪花算法生成)',
  `target_system` VARCHAR(50) NOT NULL COMMENT '目标系统: SOCIAL_SECURITY/HOUSING_FUND/GOVERNMENT_OTHER',
  `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型: INJURY_FILING/HF_ENROLL/HF_SEAL/HF_SUPPLEMENT',
  `flow_id` VARCHAR(32) DEFAULT NULL COMMENT '所属业务流程ID',
  `employee_id` VARCHAR(20) DEFAULT NULL COMMENT '关联员工ID',
  `target_url` VARCHAR(500) NOT NULL COMMENT '目标URL',
  `form_data` JSON DEFAULT NULL COMMENT '表单数据',
  `upload_files` JSON DEFAULT NULL COMMENT '上传文件列表 (JSON)',
  `browser_screenshot` VARCHAR(500) DEFAULT NULL COMMENT '浏览器截图',
  `receipt_uri` VARCHAR(500) DEFAULT NULL COMMENT '操作回执文件',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/RUNNING/SUCCESS/FAILED/INTERCEPTED',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `retry_count` INT NOT NULL DEFAULT 0 COMMENT '重试次数',
  `max_retries` INT NOT NULL DEFAULT 3 COMMENT '最大重试次数',
  `duration_ms` BIGINT DEFAULT NULL COMMENT '执行耗时 (毫秒)',
  `started_at` TIMESTAMP NULL DEFAULT NULL COMMENT '开始时间',
  `completed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`task_id`),
  KEY `idx_target_system` (`target_system`),
  KEY `idx_status` (`status`),
  KEY `idx_flow_id` (`flow_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RPA任务表';
```

### 5.4 流程实例表 (process_instance)

```sql
CREATE TABLE `process_instance` (
  `flow_id` VARCHAR(32) NOT NULL COMMENT '流程ID (UUID)',
  `process_key` VARCHAR(100) NOT NULL COMMENT '流程类型: ONBOARDING/PAYROLL/INJURY/RESIGNATION/TRAINING',
  `trigger_type` VARCHAR(20) NOT NULL COMMENT '触发类型: MANUAL/AGENT/SCHEDULED/EVENT',
  `triggered_by` VARCHAR(20) DEFAULT NULL COMMENT '触发人/Agent',
  `context_data` JSON DEFAULT NULL COMMENT '流程上下文数据',
  `current_step` VARCHAR(100) DEFAULT NULL COMMENT '当前步骤',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'RUNNING' COMMENT '状态: RUNNING/COMPLETED/FAILED/SUSPENDED/CANCELLED',
  `result_summary` JSON DEFAULT NULL COMMENT '结果摘要',
  `error_detail` TEXT DEFAULT NULL COMMENT '错误详情',
  `started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
  `completed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
  `duration_ms` BIGINT DEFAULT NULL COMMENT '总耗时 (毫秒)',
  PRIMARY KEY (`flow_id`),
  KEY `idx_process_key` (`process_key`),
  KEY `idx_status` (`status`),
  KEY `idx_started_at` (`started_at`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流程实例表';
```

### 5.5 通知消息表 (notification_message)

```sql
CREATE TABLE `notification_message` (
  `message_id` VARCHAR(20) NOT NULL COMMENT '消息ID (雪花算法生成)',
  `recipient_id` VARCHAR(20) NOT NULL COMMENT '接收人ID',
  `message_type` VARCHAR(20) NOT NULL COMMENT '消息类型: EMAIL/SMS/PUSH/IN_APP',
  `template_code` VARCHAR(50) NOT NULL COMMENT '模板编码',
  `subject` VARCHAR(200) DEFAULT NULL COMMENT '主题',
  `content` TEXT NOT NULL COMMENT '消息内容',
  `payload` JSON DEFAULT NULL COMMENT '附加数据',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `send_status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/SENT/FAILED/READ',
  `sent_at` TIMESTAMP NULL DEFAULT NULL COMMENT '发送时间',
  `read_at` TIMESTAMP NULL DEFAULT NULL COMMENT '阅读时间',
  `retry_count` INT NOT NULL DEFAULT 0 COMMENT '重试次数',
  `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`message_id`),
  KEY `idx_recipient_id` (`recipient_id`),
  KEY `idx_send_status` (`send_status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知消息表';
```

### 5.6 薪资规则表 (payroll_rule)

```sql
CREATE TABLE `payroll_rule` (
  `rule_id` VARCHAR(20) NOT NULL COMMENT '规则ID (雪花算法生成)',
  `rule_name` VARCHAR(100) NOT NULL COMMENT '规则名称',
  `rule_type` VARCHAR(50) NOT NULL COMMENT '规则类型: OVERTIME_RATE/DEDUCTION_STANDARD/ALLOWANCE/SS_RATIO/TAX_TABLE',
  `rule_config` JSON NOT NULL COMMENT '规则配置 (JSON)',
  `effective_date` DATE NOT NULL COMMENT '生效日期',
  `expiry_date` DATE DEFAULT NULL COMMENT '失效日期',
  `business_version` INT NOT NULL DEFAULT 1 COMMENT '业务版本号 (薪资规则版本)',
  `description` TEXT DEFAULT NULL COMMENT '规则说明',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人ID',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/INACTIVE',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`rule_id`),
  KEY `idx_rule_type` (`rule_type`),
  KEY `idx_effective_date` (`effective_date`),
  KEY `idx_status` (`status`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资规则表';
```

**注意：** payroll_rule 的 `business_version` 字段用于业务版本号（薪资规则版本），乐观锁版本字段统一使用全局约定 `version` 以避免命名冲突。

### 5.7 视频课程表 (video_course)

```sql
CREATE TABLE `video_course` (
  `course_id` VARCHAR(20) NOT NULL COMMENT '课程ID (雪花算法生成)',
  `title` VARCHAR(200) NOT NULL COMMENT '课程标题',
  `source_doc_uri` VARCHAR(500) DEFAULT NULL COMMENT '源教材文件链接',
  `video_uri` VARCHAR(500) NOT NULL COMMENT '视频文件链接 (MinIO)',
  `duration_seconds` INT NOT NULL COMMENT '视频时长 (秒)',
  `knowledge_points` JSON DEFAULT NULL COMMENT '知识点索引 (JSON)',
  `applicable_positions` TEXT DEFAULT NULL COMMENT '适用岗位 (逗号分隔)',
  `thumbnail_uri` VARCHAR(500) DEFAULT NULL COMMENT '缩略图链接',
  `tenant_id` VARCHAR(20) NOT NULL COMMENT '租户ID (由应用层配置注入)',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  `version` INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/REVIEWED/PUBLISHED/DELETED',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `view_count` INT NOT NULL DEFAULT 0 COMMENT '播放次数',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人/Agent',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`course_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_tenant` (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频课程表';
```

---

## 6. 索引设计

### 6.1 表内索引说明

所有表的 DDL 中已包含基础索引（单列索引），覆盖主键、外键和常用查询字段。以下列出各表已定义的单列索引及其查询场景：

| 表名 | 索引 | 查询场景 |
|------|------|---------|
| department | idx_parent_id | 递归查询子部门 |
| department | idx_dept_code | 按部门编码精确查找 |
| department | idx_manager_id | 查找某负责人管理的所有部门 |
| employee | idx_dept_id | 按部门查询员工列表 |
| employee | idx_status | 筛选在职/试用期/离职员工 |
| employee | idx_hire_date | 入职日期范围查询 |
| attendance_record | idx_date | 按日期查询考勤 |
| attendance_record | idx_flag | 筛选异常考勤记录 |
| payroll | idx_month | 按月查询薪资 |
| payroll | idx_status | 筛选已审核/已发放薪资 |
| resume | idx_position_id | 按岗位查询简历 |
| resume | idx_classify_result | 按分拣结果筛选简历 |
| resume | idx_total_score | 按匹配分排序 |
| certificate | idx_expire_date | 证书到期预警查询 |
| certificate | idx_renewal_status | 筛选需续期证书 |

### 6.2 复合索引

以下复合索引针对高频查询场景设计，覆盖多字段组合查询需求：

```sql
-- 考勤查询优化
-- 场景：按部门统计某段时间内某类型异常考勤（如查询某部门本月迟到记录）
ALTER TABLE `attendance_record`
  ADD INDEX `idx_emp_date_flag` (`employee_id`, `date`, `flag`);

-- 薪资月度查询优化
-- 场景：按月筛选特定状态的薪资记录（如查询已审核的某月薪资）
ALTER TABLE `payroll`
  ADD INDEX `idx_month_status` (`month`, `status`);

-- 简历多维查询优化
-- 场景：按岗位查询简历并按综合匹配分和分拣结果排序/筛选
ALTER TABLE `resume`
  ADD INDEX `idx_position_score_classify` (`position_id`, `total_score`, `classify_result`);

-- 绩效周期查询优化
-- 场景：按考核周期筛选特定状态的绩效记录（如查询本月已审批的绩效）
ALTER TABLE `performance_review`
  ADD INDEX `idx_cycle_status` (`cycle`, `status`);

-- 培训记录查询优化
-- 场景：查询某员工某考试是否合格（如统计员工培训通过率）
ALTER TABLE `training_record`
  ADD INDEX `idx_emp_exam_pass` (`employee_id`, `exam_pass`);

-- 证书到期预警查询优化
-- 场景：按到期日期筛选特定续期状态的证书（如查询即将到期但未续期的证书）
ALTER TABLE `certificate`
  ADD INDEX `idx_expire_renewal` (`expire_date`, `renewal_status`);

-- 审计日志查询优化
-- 场景：按时间范围和操作人员查询特定模块的审计记录
ALTER TABLE `audit_log`
  ADD INDEX `idx_time_operator_module` (`operation_time`, `operator_id`, `module`);

-- Agent日志查询优化
-- 场景：按Agent名称和流程ID查询特定状态的执行日志
ALTER TABLE `agent_run_log`
  ADD INDEX `idx_agent_flow_status` (`agent_name`, `parent_flow_id`, `status`);

-- 通知消息查询优化
-- 场景：查询某用户的未读消息（按接收人和发送状态筛选）
ALTER TABLE `notification_message`
  ADD INDEX `idx_recipient_status` (`recipient_id`, `send_status`);

-- 试卷-题目关联查询优化
-- 场景：按试卷ID获取题目并按排序号排序（如加载某试卷的全部题目）
ALTER TABLE `paper_question`
  ADD INDEX `idx_paper_sort` (`paper_id`, `sort_order`);

-- 员工薪资档案查询优化
-- 场景：查询某员工的当前有效薪资档案（按员工ID和激活状态筛选）
ALTER TABLE `employee_pay_profile`
  ADD INDEX `idx_emp_active` (`employee_id`, `is_active`);
```

### 6.3 全文索引

```sql
-- 简历全文搜索
-- 场景：自然语言搜索简历关键词（如"Java 5年经验"）
ALTER TABLE `resume`
  ADD FULLTEXT INDEX `ft_resume_search` (`candidate_name`, `skill_tags`, `certs`);

-- 题目全文搜索
-- 场景：按关键词搜索题库题目（如搜索"安全生产"相关题目）
ALTER TABLE `exam_question`
  ADD FULLTEXT INDEX `ft_question_search` (`content`, `tags`);
```

### 6.4 索引设计原则

| 原则 | 说明 |
|------|------|
| 最左前缀原则 | 复合索引查询必须从最左列开始匹配，如 idx_emp_date_flag 可支持 (employee_id)、(employee_id, date)、(employee_id, date, flag) 三种查询 |
| 区分度优先 | 将区分度高的字段放在索引前列，如 employee_id 的区分度远高于 flag |
| 覆盖索引 | 尽量使索引包含查询所需的所有字段，避免回表 |
| 避免过度索引 | 每张表索引数量控制在 5-8 个以内，过多索引会降低写入性能 |
| 定期分析 | 使用 EXPLAIN 分析慢查询，确认索引是否被正确使用 |

---

## 7. 视图设计

### 7.1 员工综合信息视图

```sql
CREATE OR REPLACE VIEW `v_employee_summary` AS
SELECT
  e.employee_id,
  e.name,
  e.gender,
  e.birth_date,
  e.phone,
  e.email,
  d.dept_name,
  p.position_name,
  e.hire_date,
  e.probation_end_date,
  e.status,
  TIMESTAMPDIFF(YEAR, e.hire_date, CURDATE()) AS work_years,
  COUNT(DISTINCT tr.record_id) AS training_count,
  COUNT(DISTINCT c.cert_id) AS certificate_count,
  COUNT(DISTINCT ic.case_id) AS injury_count
FROM employee e
LEFT JOIN department d ON e.dept_id = d.dept_id AND d.is_deleted = 0
LEFT JOIN job_position p ON e.position_id = p.position_id AND p.is_deleted = 0
LEFT JOIN training_record tr ON e.employee_id = tr.employee_id AND tr.is_deleted = 0
LEFT JOIN certificate c ON e.employee_id = c.employee_id AND c.is_deleted = 0
LEFT JOIN injury_case ic ON e.employee_id = ic.employee_id AND ic.is_deleted = 0
WHERE e.is_deleted = 0
GROUP BY e.employee_id;
```

### 7.2 月度考勤汇总视图

```sql
CREATE OR REPLACE VIEW `v_monthly_attendance` AS
SELECT
  ar.employee_id,
  e.name,
  d.dept_name,
  DATE_FORMAT(ar.date, '%Y-%m') AS month,
  COUNT(*) AS total_days,
  SUM(CASE WHEN ar.flag = 'NORMAL' THEN 1 ELSE 0 END) AS normal_days,
  SUM(CASE WHEN ar.flag = 'LATE' THEN 1 ELSE 0 END) AS total_late_count,
  SUM(CASE WHEN ar.flag = 'EARLY_LEAVE' THEN 1 ELSE 0 END) AS total_early_count,
  SUM(ar.absent_days) AS total_absent_days,
  SUM(ar.overtime_hrs) AS total_overtime_hrs,
  SUM(ar.holiday_leave_hrs) AS total_holiday_leave,
  SUM(ar.sick_leave_hrs) AS total_sick_leave
FROM attendance_record ar
JOIN employee e ON ar.employee_id = e.employee_id AND e.is_deleted = 0
LEFT JOIN department d ON e.dept_id = d.dept_id AND d.is_deleted = 0
WHERE ar.is_deleted = 0
GROUP BY ar.employee_id, e.name, d.dept_name, DATE_FORMAT(ar.date, '%Y-%m');
```

### 7.3 薪资汇总视图

```sql
CREATE OR REPLACE VIEW `v_payroll_summary` AS
SELECT
  p.month,
  COUNT(*) AS employee_count,
  SUM(p.gross_pay) AS total_gross,
  SUM(p.net_pay) AS total_net,
  SUM(p.ss_personal) AS total_ss_personal,
  SUM(p.gf_personal) AS total_gf_personal,
  SUM(p.income_tax) AS total_tax,
  AVG(p.net_pay) AS avg_net_pay,
  MIN(p.net_pay) AS min_net_pay,
  MAX(p.net_pay) AS max_net_pay
FROM payroll p
WHERE p.status IN ('REVIEWED', 'PAID') AND p.is_deleted = 0
GROUP BY p.month;
```

### 7.4 培训效果统计视图

```sql
CREATE OR REPLACE VIEW `v_training_effectiveness` AS
SELECT
  tp.plan_id,
  tp.plan_name,
  tp.training_type,
  tp.quarter,
  COUNT(DISTINCT ts.session_id) AS session_count,
  COUNT(DISTINCT tc.employee_id) AS participant_count,
  AVG(tr.exam_score) AS avg_score,
  SUM(CASE WHEN tr.exam_pass = 1 THEN 1 ELSE 0 END) AS pass_count,
  ROUND(SUM(CASE WHEN tr.exam_pass = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(tr.record_id), 0), 2) AS pass_rate,
  AVG(tr.satisfaction_score) AS avg_satisfaction
FROM training_plan tp
LEFT JOIN training_session ts ON tp.plan_id = ts.plan_id AND ts.is_deleted = 0
LEFT JOIN training_checkin tc ON ts.session_id = tc.session_id AND tc.is_deleted = 0
LEFT JOIN training_record tr ON tc.session_id = tr.session_id AND tc.employee_id = tr.employee_id AND tr.is_deleted = 0
WHERE tp.is_deleted = 0
GROUP BY tp.plan_id, tp.plan_name, tp.training_type, tp.quarter;
```

---

## 8. 初始化数据

### 8.1 系统角色初始化

```sql
INSERT INTO `sys_role` (`role_id`, `role_name`, `role_code`, `description`, `is_system`, `tenant_id`) VALUES
('ROLE_ADMIN', '系统管理员', 'ADMIN', '系统基础设施运维和技术管理', 1, '${TENANT_ID}'),
('ROLE_HR', '人事专员', 'HR', 'HR流程监督者与审核人', 1, '${TENANT_ID}'),
('ROLE_MANAGER', '部门主管', 'MANAGER', '业务决策审批人', 1, '${TENANT_ID}'),
('ROLE_EMPLOYEE', '在职员工', 'EMPLOYEE', '自助信息查询者', 1, '${TENANT_ID}'),
('ROLE_EXTERNAL', '外务专员', 'EXTERNAL', '政务联络协调人', 1, '${TENANT_ID}'),
('ROLE_NEW_HIRE', '新员工', 'NEW_HIRE', '信息提供者', 1, '${TENANT_ID}');
```

**注意：** `${TENANT_ID}` 为占位符，由应用层在初始化时替换为实际租户编码（如 GBM001）。

### 8.2 基础权限初始化

```sql
INSERT INTO `sys_permission` (`permission_id`, `permission_name`, `permission_code`, `resource_type`, `parent_id`, `tenant_id`) VALUES
-- 招聘管理
('PERM_REC_JOB', '岗位管理', 'recruitment:job:*', 'MENU', NULL, '${TENANT_ID}'),
('PERM_REC_RESUME', '简历管理', 'recruitment:resume:*', 'MENU', NULL, '${TENANT_ID}'),
('PERM_REC_EXAM', '考试管理', 'recruitment:exam:*', 'MENU', NULL, '${TENANT_ID}'),
('PERM_REC_TALENT', '人才库', 'recruitment:talent:*', 'MENU', NULL, '${TENANT_ID}'),
-- 入职管理
('PERM_ONB_ALL', '入职管理', 'onboarding:*:*', 'MENU', NULL, '${TENANT_ID}'),
-- 培训管理
('PERM_TRAIN_ALL', '培训管理', 'training:*:*', 'MENU', NULL, '${TENANT_ID}'),
-- 考勤管理
('PERM_ATT_ALL', '考勤管理', 'attendance:*:*', 'MENU', NULL, '${TENANT_ID}'),
-- 薪资管理
('PERM_PAY_ALL', '薪资管理', 'payroll:*:*', 'MENU', NULL, '${TENANT_ID}'),
('PERM_PAY_REVIEW', '薪资审核', 'payroll:review:approve', 'API', 'PERM_PAY_ALL'),
-- 绩效管理
('PERM_PERF_ALL', '绩效管理', 'performance:*:*', 'MENU', NULL, '${TENANT_ID}'),
-- 外务管理
('PERM_EXT_ALL', '外务管理', 'external:*:*', 'MENU', NULL, '${TENANT_ID}'),
-- 员工服务
('PERM_EMP_ALL', '员工服务', 'employee:*:*', 'MENU', NULL, '${TENANT_ID}'),
-- Agent 管理
('PERM_AGENT_ALL', 'Agent管理', 'agent:*:*', 'MENU', NULL, '${TENANT_ID}'),
-- 系统管理
('PERM_SYS_ALL', '系统管理', 'system:*:*', 'MENU', NULL, '${TENANT_ID}');
```

### 8.3 角色权限分配

```sql
-- 系统管理员: 所有权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `tenant_id`)
SELECT 'ROLE_ADMIN', permission_id, '${TENANT_ID}' FROM sys_permission;

-- 人事专员: HR 相关权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `tenant_id`) VALUES
('ROLE_HR', 'PERM_REC_JOB', '${TENANT_ID}'),
('ROLE_HR', 'PERM_REC_RESUME', '${TENANT_ID}'),
('ROLE_HR', 'PERM_REC_EXAM', '${TENANT_ID}'),
('ROLE_HR', 'PERM_REC_TALENT', '${TENANT_ID}'),
('ROLE_HR', 'PERM_ONB_ALL', '${TENANT_ID}'),
('ROLE_HR', 'PERM_TRAIN_ALL', '${TENANT_ID}'),
('ROLE_HR', 'PERM_ATT_ALL', '${TENANT_ID}'),
('ROLE_HR', 'PERM_PAY_ALL', '${TENANT_ID}'),
('ROLE_HR', 'PERM_PERF_ALL', '${TENANT_ID}'),
('ROLE_HR', 'PERM_EXT_ALL', '${TENANT_ID}'),
('ROLE_HR', 'PERM_EMP_ALL', '${TENANT_ID}');

-- 部门主管: 团队管理和审批权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `tenant_id`) VALUES
('ROLE_MANAGER', 'PERM_PERF_ALL', '${TENANT_ID}'),
('ROLE_MANAGER', 'PERM_ATT_ALL', '${TENANT_ID}'),
('ROLE_MANAGER', 'PERM_TRAIN_ALL', '${TENANT_ID}');

-- 外务专员: 外务权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `tenant_id`) VALUES
('ROLE_EXTERNAL', 'PERM_EXT_ALL', '${TENANT_ID}');

-- 在职员工: 自助服务权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`, `tenant_id`) VALUES
('ROLE_EMPLOYEE', 'PERM_EMP_ALL', '${TENANT_ID}');
```

---

## 9. 分区与归档策略

### 9.1 考勤表分区 (按月份)

```sql
-- 考勤记录按月分区 (保留最近 24 个月在线)
ALTER TABLE `attendance_record`
  PARTITION BY RANGE (YEAR(date) * 100 + MONTH(date)) (
  PARTITION p202601 VALUES LESS THAN (202602),
  PARTITION p202602 VALUES LESS THAN (202603),
  PARTITION p202603 VALUES LESS THAN (202604),
  PARTITION p202604 VALUES LESS THAN (202605),
  PARTITION p202605 VALUES LESS THAN (202606),
  PARTITION p202606 VALUES LESS THAN (202607),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

### 9.2 薪资表分区 (按月份)

```sql
-- 薪资记录按月分区 (保留 15 年以上)
ALTER TABLE `payroll`
  PARTITION BY RANGE (YEAR(SUBSTRING(month, 1, 4)) * 100 + MONTH(SUBSTRING(month, 6, 2))) (
  PARTITION p202601 VALUES LESS THAN (202602),
  PARTITION p202602 VALUES LESS THAN (202603),
  PARTITION p202603 VALUES LESS THAN (202604),
  PARTITION p202604 VALUES LESS THAN (202605),
  PARTITION p202605 VALUES LESS THAN (202606),
  PARTITION p202606 VALUES LESS THAN (202607),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

### 9.3 审计日志分区 (按季度)

```sql
-- 审计日志按季度分区 (保留 10 年)
ALTER TABLE `audit_log`
  PARTITION BY RANGE (YEAR(operation_time) * 100 + QUARTER(operation_time)) (
  PARTITION p2026Q1 VALUES LESS THAN (202602),
  PARTITION p2026Q2 VALUES LESS THAN (202603),
  PARTITION p2026Q3 VALUES LESS THAN (202604),
  PARTITION p2026Q4 VALUES LESS THAN (202605),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

### 9.4 Agent 日志分区 (按月)

```sql
-- Agent 执行日志按月分区 (保留 6 个月在线)
ALTER TABLE `agent_run_log`
  PARTITION BY RANGE (YEAR(created_at) * 100 + MONTH(created_at)) (
  PARTITION p202601 VALUES LESS THAN (202602),
  PARTITION p202602 VALUES LESS THAN (202603),
  PARTITION p202603 VALUES LESS THAN (202604),
  PARTITION p202604 VALUES LESS THAN (202605),
  PARTITION p202605 VALUES LESS THAN (202606),
  PARTITION p202606 VALUES LESS THAN (202607),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

### 9.5 数据归档存储策略

| 数据类型 | 在线保留 | 离线归档 | 归档方式 |
|---------|---------|---------|---------|
| 考勤数据 | 24 个月 | >= 2 年 | 冷备表 + 压缩 |
| 薪资数据 | 15 年 | >= 15 年 | 独立归档库 |
| 简历数据 | 3 年 | >= 2 年 | MinIO 冷存储 |
| Agent 日志 | 6 个月 | >= 1 年 | Elasticsearch 归档 |
| 审计日志 | 10 年 | >= 10 年 | 独立归档库 |
| 培训记录 | 3 年 | >= 2 年 | 冷备表 |

---

## 10. 附录

### 10.1 MySQL 8.x 推荐配置

```ini
[mysqld]
# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# 连接
max_connections = 200
max_connect_errors = 1000

# InnoDB
innodb_buffer_pool_size = 4G
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT

# 事务
default-storage-engine = InnoDB
transaction-isolation = READ-COMMITTED

# 慢查询
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1

# 二进制日志 (主从复制)
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
expire-logs-days = 15
```

### 10.2 连接池建议

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 最大连接数 | 50 | 覆盖 Agent 并发请求峰值（Agent 链式调用通常串行） |
| 最小空闲连接 | 10 | 保证冷启动时的连接可用性 |
| 连接超时 | 30s | 超过 30s 未响应视为连接失效 |
| 空闲超时 | 600s | 空闲 10 分钟回收连接 |
| 测试查询 | SELECT 1 | 借出前测试连接有效性 |

**连接池选型建议：** 推荐使用 HikariCP（Java）或 SQLAlchemy Pool（Python），均为业界成熟的连接池实现。

### 10.3 备份策略

```bash
# 全量备份 (每周日凌晨 1 点)
0 1 * * 0 mysqldump --all-databases --single-transaction --routines --triggers --master-data=2 | gzip > /backup/full_$(date +\%Y\%m\%d).sql.gz

# 增量备份 (每天凌晨 2 点, 基于 binlog)
0 2 * * * cp /var/lib/mysql/mysql-bin.* /backup/incremental/ 2>/dev/null
```

### 10.4 安全建议

| 措施 | 说明 |
|------|------|
| 敏感字段加密 | 身份证号使用 AES-256 加密存储，SHA-256 哈希用于去重 |
| 银行账号加密 | VARBINARY(64) 类型存储 AES 加密后的银行账号 |
| 密码存储 | 使用 BCrypt 哈希（salt 自动内联），不存储明文密码 |
| 访问控制 | 数据库用户最小权限原则，应用层使用独立数据库账号 |
| 审计日志 | 所有敏感操作记录完整审计日志，保留 10 年 |
| 传输加密 | 强制使用 TLS 1.2+ 加密数据库连接 |

---

## 附录: V5 到 V6 修订说明

### 后荣检验意见修复清单

**一、ID 生成策略补充**

1. **新增雪花算法位数分配方案说明（第 1.4 节）：**
   - 明确标准雪花算法 64 位分配：1 位符号位 + 41 位时间戳 + 10 位机器 ID + 12 位序列号
   - 说明时间戳支持约 69 年（至 2082 年），足够覆盖系统生命周期
   - 说明 10 位机器 ID 支持最大 1024 个节点，满足未来扩展需求
   - 说明 12 位序列号每毫秒支持 4096 个序列号，足以应对高并发场景
   - 说明 VARCHAR(20) 存储 18-19 位十进制字符串，提供 1 位冗余扩展空间

**二、tenant_id 硬编码修复**

2. **移除所有 DDL 中的 `DEFAULT 'GBM001'`：**
   - 所有 38 张表的 `tenant_id` 字段从 `DEFAULT 'GBM001'` 改为 `NOT NULL COMMENT '租户ID (由应用层配置注入)'`
   - 全局字段约定（第 1.3 节）更新说明：默认值由应用层配置注入，DDL 中不硬编码
   - 初始化数据中的 `${TENANT_ID}` 占位符由应用层在初始化脚本中替换

**三、ER 图命名一致性确认**

3. **统一命名确认：**
   - 确认 ER 图、实体关系表、DDL 中 `employee_pay_profile` 命名完全一致
   - 第 1.2 节关系说明中补充 `is_active` 字段的版本管理说明

**四、外键约束策略补充**

4. **新增第 1.6 节"外键约束策略"：**
   - 明确采用数据库层面强制外键约束方案
   - 说明选择理由（数据完整性、跨连接一致性）
   - 说明级联策略（ON UPDATE CASCADE，根据业务选择 CASCADE/SET NULL/RESTRICT）
   - 说明循环依赖通过 ALTER TABLE 延迟添加解决
   - 说明应用层 ORM/DAO 作为辅助手段

**五、核心设计要素补充**

5. **新增第 1.5 节"字段命名规范"：**
   - 蛇形命名法（snake_case）统一规范
   - 表名、字段名、主键、外键、索引、约束命名规则
   - 布尔/标志字段命名约定

6. **新增第 1.7 节"字符集与排序规则"：**
   - utf8mb4 / utf8mb4_unicode_ci 全局定义
   - 选择理由（完整 Unicode 支持、多语言排序准确性）

7. **新增第 1.8 节"事务隔离级别"：**
   - 推荐 READ COMMITTED
   - 选择理由（HR 操作频率低，RR 过于严格）
   - 关键操作通过乐观锁保证最终一致性

8. **新增第 1.9 节"数据量预估与容量规划"：**
   - 8 张核心表的日均/年/10 年数据量预估
   - 归档策略对应表
   - 初始存储容量建议（50GB SSD）
   - InnoDB buffer pool、索引占比、日志保留建议

9. **新增第 10.2 节"连接池建议"：**
   - 连接池参数推荐值（最大 50，最小空闲 10 等）
   - 选型建议（HikariCP / SQLAlchemy Pool）

10. **新增第 10.4 节"安全建议"：**
    - 敏感字段加密、密码存储、访问控制、传输加密等

**六、索引设计补充**

11. **完善第 6 节"索引设计"：**
    - 新增 6.1 节"表内索引说明"，列出各表已定义的单列索引及查询场景
    - 6.2 节"复合索引"中每条索引补充具体查询场景说明（如考勤查询常用 employee_id + date + flag 组合）
    - 新增 6.4 节"索引设计原则"（最左前缀、区分度优先、覆盖索引、避免过度索引、定期分析）

---

*文档结束*
