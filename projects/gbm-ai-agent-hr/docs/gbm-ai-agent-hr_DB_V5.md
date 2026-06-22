# GBM AI Agent HR 智能人力管理系统 — 数据库设计脚本 (V3)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 数据库设计脚本 |
| 版本号 | V5.0 |
| 基于 SRS | V15.0 |
| 数据库 | MySQL 8.x (InnoDB) |
| 字符集 | utf8mb4 / utf8mb4_unicode_ci |
| 日期 | 2026-06-12 |
| 作者 | 后旺 (HouWang) |
| 角色 | 数据库架构师 |

## 修订说明

V4.0→V5.0：根据后荣检验报告修复以下问题：
1. 修复 v_monthly_attendance 视图字段错误（late_count/early_leave_count/absent_days → late_minutes/early_leave_minutes）
2. 考勤表 attendance_record 放弃分区方案，改为归档表策略（MySQL 分区键必须是主键一部分的约束）
3. 薪资表 payroll 放弃分区方案，改为归档表策略
4. 修正审计日志分区边界计算逻辑
5. 新增 shift 班次表定义
6. 移除简历 JSON 字段全文索引（MySQL 不支持 JSON 列 FULLTEXT INDEX）
7. 移除 department.manager_id 外键约束（解决 department ↔ employee 循环依赖）
8. employee 表增加 id_number、phone 唯一约束
9. 修正 exam_question 题型枚举大小写（Essay → ESSAY）
10. employee 表增加 hire_source_resume_id 字段（简历-员工关联）
11. payroll_rule 表增加 dept_id、position_id 关联字段

---

## 目录

1. ER 概述
2. 基础表结构
3. 业务表结构
4. Agent 与审计表
5. 索引设计
6. 视图设计
7. 初始化数据
8. 分区与归档策略

---

## 1. ER 概述

### 1.1 实体关系图 (文本描述)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   department  │────│   employee    │────│  attendance  │
│   部门表      │ 1:N│   员工表      │ N:1│  考勤记录表   │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐    ┌──────▼───────┐   ┌──────▼──────┐
│   resume     │    │   payroll    │   │ performance_review │
│   简历表      │    │   薪资表      │   │  绩效考核表        │
└──────────────┘    └──────────────┘   └─────────────┘
        │                   │                   │
        │         ┌─────────▼─────────┐         │
        │         │  employee_pay_profile │         │
        │         │   员工薪资档案表    │         │
        │         └───────────────────┘         │
        │                                       │
┌──────────────┐    ┌──────────────────┐   ┌──────────────┐
│ job_position │    │  training_plan   │   │  injury     │
│  岗位表       │    │  培训计划表       │   │  工伤表      │
└──────────────┘    └────────┬─────────┘   └─────────────┘
                             │
                    ┌────────▼──────────┐
                    │ training_session  │
                    │   培训场次表       │
                    └────────┬─────────┘
                    ┌────────▼──────────┐
                    │ training_checkin  │
                    │   培训签到记录表   │
                    └────────┬─────────┘
                    ┌────────▼──────────┐
                    │ training_record   │
                    │   培训记录表       │
                    └───────────────────┘

┌──────────────┐    ┌──────────────┐   ┌──────────────┐
│  sys_user     │    │  sys_role    │   │  audit_log   │
│   系统用户表   │    │   系统角色表  │   │  审计日志表   │
└──────────────┘    └──────────────┘   └─────────────┘
        │                   │
        └────────┬──────────┘
                 │
        ┌────────▼────────┐
        │  user_role      │
        │  用户角色关联表   │
        └─────────────────┘

┌──────────────┐    ┌──────────────┐   ┌──────────────┐
│ agent_run_log  │    │   rpa_task   │   │  certificate  |
│ Agent执行日志   │    │  RPA任务表   │   │  证书台账表   |
└──────────────┘    └──────────────┘   └─────────────┘
```

### 1.2 核心实体关系

| 关系 | 类型 | 说明 |
|------|------|------|
| department → employee | 1:N | 一个部门包含多个员工 |
| employee → attendance | 1:N | 一个员工有多条考勤记录 |
| employee → payroll | 1:N | 一个员工有多条薪资记录 |
| employee → performance | 1:N | 一个员工有多次绩效记录 |
| employee → training_record | 1:N | 一个员工有多个培训记录 |
| employee → injury | 1:N | 一个员工可能有多个工伤记录 |
| user → role | M:N | 多对多（通过 user_role 表关联） |
| role → permission | M:N | 多对多（通过 role_permission 表关联） |
| training_plan → session | 1:N | 一个培训计划有多个场次 |
| session → checkin | 1:N | 一场培训有多条签到记录 |
| exam_paper → question | M:N | 多对多（通过 paper_question 表关联） |

---

## 2. 基础表结构

### 2.1 部门表 (department)

```sql
CREATE TABLE `department` (
  `dept_id` VARCHAR(20) NOT NULL COMMENT '部门ID',
  `dept_name` VARCHAR(100) NOT NULL COMMENT '部门名称',
  `parent_id` VARCHAR(20) DEFAULT '0' COMMENT '父部门ID (0=根部门)',
  `dept_code` VARCHAR(50) DEFAULT NULL COMMENT '部门编码',
  `manager_id` VARCHAR(20) DEFAULT NULL COMMENT '部门负责人ID (引用 employee.employee_id，不设外键约束，避免 department ↔ employee 循环依赖，由应用层校验)',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '部门电话',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '部门邮箱',
  `address` VARCHAR(200) DEFAULT NULL COMMENT '办公地址',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` TIMESTAMP NULL DEFAULT NULL COMMENT '逻辑删除时间',
  PRIMARY KEY (`dept_id`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_dept_code` (`dept_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';
```

### 2.2 系统用户表 (sys_user)

```sql
CREATE TABLE `sys_user` (
  `user_id` VARCHAR(20) NOT NULL COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '登录名',
  `password_hash` VARCHAR(200) NOT NULL COMMENT '密码哈希 (BCrypt)',
  `name` VARCHAR(50) NOT NULL COMMENT '显示名称',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `avatar_uri` VARCHAR(500) DEFAULT NULL COMMENT '头像链接',
  `mfa_enabled` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否启用MFA',
  `mfa_method` VARCHAR(20) DEFAULT 'sms' COMMENT 'MFA方式: sms/email/totp',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/LOCKED/DELETED',
  `last_login_at` TIMESTAMP NULL DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` VARCHAR(45) DEFAULT NULL COMMENT '最后登录IP',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_phone` (`phone`),
  KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';
```

### 2.3 系统角色表 (sys_role)

```sql
CREATE TABLE `sys_role` (
  `role_id` VARCHAR(50) NOT NULL COMMENT '角色ID',
  `role_name` VARCHAR(50) NOT NULL COMMENT '角色名称',
  `role_code` VARCHAR(50) NOT NULL COMMENT '角色编码',
  `description` VARCHAR(200) DEFAULT NULL COMMENT '角色描述',
  `is_system` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否系统内置角色',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统角色表';
```

### 2.4 系统权限表 (sys_permission)

```sql
CREATE TABLE `sys_permission` (
  `permission_id` VARCHAR(50) NOT NULL COMMENT '权限ID',
  `permission_name` VARCHAR(50) NOT NULL COMMENT '权限名称',
  `permission_code` VARCHAR(100) NOT NULL COMMENT '权限编码',
  `resource_type` VARCHAR(20) NOT NULL COMMENT '资源类型: MENU/API/BUTTON',
  `parent_id` VARCHAR(50) DEFAULT NULL COMMENT '父权限ID',
  `path` VARCHAR(200) DEFAULT NULL COMMENT '前端路由路径',
  `icon` VARCHAR(50) DEFAULT NULL COMMENT '图标',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '排序序号',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`permission_id`),
  UNIQUE KEY `uk_permission_code` (`permission_code`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统权限表';
```

### 2.5 用户角色关联表 (sys_user_role)

```sql
CREATE TABLE `sys_user_role` (
  `user_id` VARCHAR(20) NOT NULL COMMENT '用户ID',
  `role_id` VARCHAR(50) NOT NULL COMMENT '角色ID',
  `assigned_by` VARCHAR(20) DEFAULT NULL COMMENT '分配人ID',
  `assigned_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分配时间',
  PRIMARY KEY (`user_id`, `role_id`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `fk_ur_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_ur_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`role_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';
```

### 2.6 角色权限关联表 (sys_role_permission)

```sql
CREATE TABLE `sys_role_permission` (
  `role_id` VARCHAR(50) NOT NULL COMMENT '角色ID',
  `permission_id` VARCHAR(50) NOT NULL COMMENT '权限ID',
  `assigned_by` VARCHAR(20) DEFAULT NULL COMMENT '分配人ID',
  `assigned_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分配时间',
  PRIMARY KEY (`role_id`, `permission_id`),
  KEY `idx_permission_id` (`permission_id`),
  CONSTRAINT `fk_rp_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`role_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_rp_permission` FOREIGN KEY (`permission_id`) REFERENCES `sys_permission` (`permission_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';
```

### 2.7 岗位表 (job_position)

```sql
CREATE TABLE `job_position` (
  `position_id` VARCHAR(20) NOT NULL COMMENT '岗位ID',
  `position_name` VARCHAR(100) NOT NULL COMMENT '岗位名称',
  `dept_id` VARCHAR(20) NOT NULL COMMENT '所属部门ID',
  `job_level` VARCHAR(20) DEFAULT NULL COMMENT '职级',
  `head_count` INT NOT NULL DEFAULT 1 COMMENT '编制人数',
  `filled_count` INT NOT NULL DEFAULT 0 COMMENT '已 filling 人数',
  `salary_min` DECIMAL(10,2) DEFAULT NULL COMMENT '薪资下限',
  `salary_max` DECIMAL(10,2) DEFAULT NULL COMMENT '薪资上限',
  `requirements` JSON DEFAULT NULL COMMENT '岗位要求 (JSON)',
  `status` VARCHAR(20) NOT NULL DEFAULT 'OPEN' COMMENT '状态: OPEN/CLOSED/PAUSED',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` TIMESTAMP NULL DEFAULT NULL COMMENT '逻辑删除时间',
  PRIMARY KEY (`position_id`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_pos_dept` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位表';
```

---

## 3. 业务表结构

### 3.1 员工表 (employee)

```sql
CREATE TABLE `employee` (
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `gender` VARCHAR(10) NOT NULL COMMENT '性别: MALE/FEMALE',
  `birth_date` DATE DEFAULT NULL COMMENT '出生日期',
  `id_number` VARCHAR(18) DEFAULT NULL COMMENT '身份证号 (加密存储)',
  `id_card_front_uri` VARCHAR(500) DEFAULT NULL COMMENT '身份证正面图片',
  `id_card_back_uri` VARCHAR(500) DEFAULT NULL COMMENT '身份证反面图片',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `dept_id` VARCHAR(20) NOT NULL COMMENT '所属部门ID',
  `position_id` VARCHAR(20) NOT NULL COMMENT '岗位ID',
  `hire_date` DATE NOT NULL COMMENT '入职日期',
  `probation_end_date` DATE DEFAULT NULL COMMENT '试用期结束日期',
  `employee_type` VARCHAR(20) NOT NULL DEFAULT 'FULL_TIME' COMMENT '用工类型: FULL_TIME/PART_TIME/CONTRACT/INTERN',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/PROBATION/RESIGNED/FIRED/QUIT',
  `face_features` TEXT DEFAULT NULL COMMENT '人脸特征 (加密存储)',
  `education` VARCHAR(20) DEFAULT NULL COMMENT '学历: HIGH_SCHOOL/BACHELOR/MASTER/DOCTOR',
  `graduate_school` VARCHAR(100) DEFAULT NULL COMMENT '毕业院校',
  `major` VARCHAR(100) DEFAULT NULL COMMENT '专业',
  `emergency_contact` VARCHAR(50) DEFAULT NULL COMMENT '紧急联系人',
  `emergency_phone` VARCHAR(20) DEFAULT NULL COMMENT '紧急联系电话',
  `address` VARCHAR(200) DEFAULT NULL COMMENT '通讯地址',
  `social_security_no` VARCHAR(50) DEFAULT NULL COMMENT '社保号',
  `housing_fund_no` VARCHAR(50) DEFAULT NULL COMMENT '公积金号',
  `user_id` VARCHAR(20) DEFAULT NULL COMMENT '关联系统用户ID',
  `hire_source_resume_id` VARCHAR(20) DEFAULT NULL COMMENT '来源简历ID (关联 resume.resume_id，候选人 hired 后映射为正式员工)',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` TIMESTAMP NULL DEFAULT NULL COMMENT '逻辑删除时间',
  PRIMARY KEY (`employee_id`),
  UNIQUE KEY `uk_id_number` (`id_number`),
  UNIQUE KEY `uk_phone` (`phone`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_position_id` (`position_id`),
  KEY `idx_status` (`status`),
  KEY `idx_user_id` (`user_id`),
  CONSTRAINT `fk_emp_dept` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_emp_pos` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工表';
```

### 3.1.1 班次表 (shift)

> V5.0 新增：attendance_record 表引用 shift_id，需定义班次表以支持倒班/轮班场景。

```sql
CREATE TABLE `shift` (
  `shift_id` VARCHAR(20) NOT NULL COMMENT '班次ID',
  `shift_name` VARCHAR(50) NOT NULL COMMENT '班次名称: 早班/中班/晚班/白班/夜班',
  `start_time` TIME NOT NULL COMMENT '班次开始时间',
  `end_time` TIME NOT NULL COMMENT '班次结束时间',
  `is_overtime` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否计为加班',
  `overtime_rate` DECIMAL(3,2) NOT NULL DEFAULT 1.5 COMMENT '加班费率',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`shift_id`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班次表';
```

### 3.2 简历表 (resume)

```sql
CREATE TABLE `resume` (
  `resume_id` VARCHAR(20) NOT NULL COMMENT '简历ID',
  `candidate_name` VARCHAR(50) NOT NULL COMMENT '候选人姓名',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `email` VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `gender` VARCHAR(10) DEFAULT NULL COMMENT '性别',
  `birth_year` INT DEFAULT NULL COMMENT '出生年份',
  `age` INT DEFAULT NULL COMMENT '年龄',
  `education` VARCHAR(20) DEFAULT NULL COMMENT '学历',
  `graduate_school` VARCHAR(100) DEFAULT NULL COMMENT '毕业院校',
  `major` VARCHAR(100) DEFAULT NULL COMMENT '专业',
  `work_years` INT DEFAULT NULL COMMENT '工作年限',
  `current_company` VARCHAR(100) DEFAULT NULL COMMENT '现公司',
  `current_position` VARCHAR(100) DEFAULT NULL COMMENT '现岗位',
  `current_salary` DECIMAL(10,2) DEFAULT NULL COMMENT '现薪资',
  `expected_salary` DECIMAL(10,2) DEFAULT NULL COMMENT '期望薪资',
  `applied_position_name` VARCHAR(100) DEFAULT NULL COMMENT '应聘岗位名称',
  `position_id` VARCHAR(20) DEFAULT NULL COMMENT '应聘岗位ID',
  `skill_tags` JSON DEFAULT NULL COMMENT '技能标签 (JSON数组)',
  `certs` JSON DEFAULT NULL COMMENT '证书 (JSON数组)',
  `resume_text` TEXT DEFAULT NULL COMMENT '简历全文 (用于ES搜索)',
  `resume_uri` VARCHAR(500) DEFAULT NULL COMMENT '简历文件链接 (MinIO)',
  `source` VARCHAR(50) DEFAULT NULL COMMENT '来源: BOSS/51JOB/ZHAOPIN/REFERAL/MANUAL',
  `source_url` VARCHAR(500) DEFAULT NULL COMMENT '来源链接',
  `total_score` DECIMAL(5,2) DEFAULT NULL COMMENT '综合评分',
  `classify_result` VARCHAR(20) DEFAULT NULL COMMENT '分类结果: HIGH/MEDIUM/LOW',
  `status` VARCHAR(20) NOT NULL DEFAULT 'NEW' COMMENT '状态: NEW/SCREENING/INTERVIEW/OFFER/REJECTED/HIRED',
  `interview_feedback` TEXT DEFAULT NULL COMMENT '面试反馈',
  `reject_reason` VARCHAR(200) DEFAULT NULL COMMENT '淘汰原因',
  `parser_version` VARCHAR(20) DEFAULT NULL COMMENT '解析器版本',
  `parsed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '解析时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` TIMESTAMP NULL DEFAULT NULL COMMENT '逻辑删除时间',
  PRIMARY KEY (`resume_id`),
  KEY `idx_candidate_name` (`candidate_name`),
  KEY `idx_phone` (`phone`),
  KEY `idx_position_id` (`position_id`),
  KEY `idx_status` (`status`),
  KEY `idx_classify_result` (`classify_result`),
  CONSTRAINT `fk_resume_pos` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';
```

### 3.3 员工薪资档案表 (employee_pay_profile)

```sql
CREATE TABLE `employee_pay_profile` (
  `profile_id` VARCHAR(20) NOT NULL COMMENT '档案ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `base_salary` DECIMAL(10,2) NOT NULL COMMENT '基本工资',
  `allowance` DECIMAL(10,2) DEFAULT 0 COMMENT '固定补贴',
  `pay_date` INT NOT NULL DEFAULT 15 COMMENT '发薪日 (1-31)',
  `bank_name` VARCHAR(100) DEFAULT NULL COMMENT '开户银行',
  `bank_account` VARCHAR(50) DEFAULT NULL COMMENT '银行账号 (加密存储)',
  `ss_ratio_personal` DECIMAL(5,4) NOT NULL DEFAULT 0.105 COMMENT '社保个人缴纳比例',
  `ss_ratio_company` DECIMAL(5,4) NOT NULL DEFAULT 0.24 COMMENT '社保公司缴纳比例',
  `gf_ratio_personal` DECIMAL(5,4) NOT NULL DEFAULT 0.07 COMMENT '公积金个人缴纳比例',
  `gf_ratio_company` DECIMAL(5,4) NOT NULL DEFAULT 0.07 COMMENT '公积金公司缴纳比例',
  `ss_base` DECIMAL(10,2) DEFAULT NULL COMMENT '社保缴纳基数',
  `gf_base` DECIMAL(10,2) DEFAULT NULL COMMENT '公积金缴纳基数',
  `special_deduction` JSON DEFAULT NULL COMMENT '专项附加扣除 (JSON)',
  `effective_date` DATE NOT NULL COMMENT '生效日期',
  `version` INT NOT NULL DEFAULT 1 COMMENT '版本号',
  `updated_by` VARCHAR(20) DEFAULT NULL COMMENT '修改人ID',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`profile_id`),
  UNIQUE KEY `uk_employee` (`employee_id`),
  CONSTRAINT `fk_payprof_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工薪资档案表';
```

### 3.4 考勤记录表 (attendance_record)

```sql
CREATE TABLE `attendance_record` (
  `record_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `date` DATE NOT NULL COMMENT '考勤日期',
  `clock_in_time` TIME DEFAULT NULL COMMENT '上班打卡时间',
  `clock_out_time` TIME DEFAULT NULL COMMENT '下班打卡时间',
  `flag` VARCHAR(20) NOT NULL DEFAULT 'NORMAL' COMMENT '状态: NORMAL/LATE/EARLY_LEAVE/ABSENT/OVERTIME/LEAVE/TRAVEL',
  `late_minutes` INT NOT NULL DEFAULT 0 COMMENT '迟到分钟数',
  `early_leave_minutes` INT NOT NULL DEFAULT 0 COMMENT '早退分钟数',
  `overtime_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '加班时长 (小时)',
  `holiday_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '事假时长',
  `sick_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '病假时长',
  `annual_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '年假时长',
  `marriage_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '婚假时长',
  `maternity_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '产假时长',
  `business_trip_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '出差时长',
  `absence_reason` VARCHAR(200) DEFAULT NULL COMMENT '缺勤原因',
  `shift_id` VARCHAR(20) DEFAULT NULL COMMENT '班次ID',
  `device_id` VARCHAR(50) DEFAULT NULL COMMENT '打卡设备ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`record_id`),
  UNIQUE KEY `uk_emp_date` (`employee_id`, `date`),
  KEY `idx_date` (`date`),
  KEY `idx_flag` (`flag`),
  CONSTRAINT `fk_att_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考勤记录表';
```

### 3.5 薪资表 (payroll)

```sql
CREATE TABLE `payroll` (
  `payroll_id` VARCHAR(20) NOT NULL COMMENT '薪资ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `month` VARCHAR(7) NOT NULL COMMENT '薪资月份 (YYYY-MM)',
  `month_date` DATE GENERATED ALWAYS AS (CONCAT(month, '-01')) STORED COMMENT '月份日期 (用于分区)',
  `snapshot_id` VARCHAR(32) DEFAULT NULL COMMENT '数据快照ID',
  `base_salary` DECIMAL(10,2) NOT NULL COMMENT '基本工资',
  `allowance` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '补贴',
  `overtime_pay` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '加班费',
  `bonus` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '奖金',
  `deduction` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '扣款',
  `gross_pay` DECIMAL(10,2) NOT NULL COMMENT '应发工资',
  `ss_personal` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '社保个人',
  `ss_company` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '社保公司',
  `gf_personal` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '公积金个人',
  `gf_company` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '公积金公司',
  `taxable_income` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '应税收入',
  `income_tax` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '个人所得税',
  `net_pay` DECIMAL(10,2) NOT NULL COMMENT '实发工资',
  `cumulative_taxable` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '累计应税收入',
  `cumulative_tax` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '累计个税',
  `anomaly_flags` JSON DEFAULT NULL COMMENT '异常标记 (JSON数组)',
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
  CONSTRAINT `fk_payroll_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资表';
```

### 3.6 绩效考核表 (performance_review)

```sql
CREATE TABLE `performance_review` (
  `review_id` VARCHAR(20) NOT NULL COMMENT '考核ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `cycle` VARCHAR(20) NOT NULL COMMENT '考核周期 (YYYY-Q1/半年/年)',
  `self_score` DECIMAL(5,2) DEFAULT NULL COMMENT '自评分数',
  `self_comment` TEXT DEFAULT NULL COMMENT '自评说明',
  `manager_score` DECIMAL(5,2) DEFAULT NULL COMMENT '主管评分',
  `manager_comment` TEXT DEFAULT NULL COMMENT '主管评语',
  `final_score` DECIMAL(5,2) DEFAULT NULL COMMENT '最终分数',
  `rating` VARCHAR(10) DEFAULT NULL COMMENT '等级: S/A/B/C/D',
  `weight_self` DECIMAL(3,2) NOT NULL DEFAULT 0.3 COMMENT '自评权重',
  `weight_manager` DECIMAL(3,2) NOT NULL DEFAULT 0.7 COMMENT '主管权重',
  `kpi_items` JSON DEFAULT NULL COMMENT 'KPI 指标 (JSON)',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING_SELF' COMMENT '状态: PENDING_SELF/PENDING_MANAGER/COMPLETED/ARCHIVED',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` TIMESTAMP NULL DEFAULT NULL COMMENT '逻辑删除时间',
  PRIMARY KEY (`review_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_cycle` (`cycle`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_perf_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='绩效考核表';
```

### 3.7 培训计划表 (training_plan)

```sql
CREATE TABLE `training_plan` (
  `plan_id` VARCHAR(20) NOT NULL COMMENT '计划ID',
  `plan_name` VARCHAR(200) NOT NULL COMMENT '计划名称',
  `training_type` VARCHAR(50) NOT NULL COMMENT '培训类型: ONBOARDING/SAFETY/SKILL/COMPLIANCE/OTHER',
  `quarter` VARCHAR(20) NOT NULL COMMENT '所属季度 (YYYY-Q1)',
  `description` TEXT DEFAULT NULL COMMENT '培训说明',
  `target_positions` JSON DEFAULT NULL COMMENT '目标岗位 (JSON数组)',
  `target_count` INT NOT NULL DEFAULT 0 COMMENT '目标人数',
  `budget` DECIMAL(10,2) DEFAULT NULL COMMENT '预算金额',
  `start_date` DATE NOT NULL COMMENT '开始日期',
  `end_date` DATE NOT NULL COMMENT '结束日期',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/APPROVED/IN_PROGRESS/COMPLETED/CANCELLED',
  `approved_by` VARCHAR(20) DEFAULT NULL COMMENT '审批人ID',
  `approved_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审批时间',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` TIMESTAMP NULL DEFAULT NULL COMMENT '逻辑删除时间',
  PRIMARY KEY (`plan_id`),
  KEY `idx_training_type` (`training_type`),
  KEY `idx_quarter` (`quarter`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训计划表';
```

### 3.8 培训场次表 (training_session)

```sql
CREATE TABLE `training_session` (
  `session_id` VARCHAR(20) NOT NULL COMMENT '场次ID',
  `plan_id` VARCHAR(20) NOT NULL COMMENT '计划ID',
  `session_name` VARCHAR(200) NOT NULL COMMENT '场次名称',
  `trainer_name` VARCHAR(100) DEFAULT NULL COMMENT '讲师姓名',
  `location` VARCHAR(200) DEFAULT NULL COMMENT '培训地点',
  `start_time` DATETIME NOT NULL COMMENT '开始时间',
  `end_time` DATETIME NOT NULL COMMENT '结束时间',
  `max_attendees` INT NOT NULL DEFAULT 0 COMMENT '最大人数',
  `qr_code` VARCHAR(100) DEFAULT NULL COMMENT '签到二维码 (Redis缓存)',
  `exam_paper_id` VARCHAR(20) DEFAULT NULL COMMENT '结业考试试卷ID',
  `pass_score` DECIMAL(5,2) DEFAULT NULL COMMENT '及格分数',
  `status` VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED' COMMENT '状态: SCHEDULED/IN_PROGRESS/COMPLETED/CANCELLED',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人/Agent',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`session_id`),
  KEY `idx_plan_id` (`plan_id`),
  KEY `idx_start_time` (`start_time`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_session_plan` FOREIGN KEY (`plan_id`) REFERENCES `training_plan` (`plan_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_session_paper` FOREIGN KEY (`exam_paper_id`) REFERENCES `exam_paper` (`paper_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训场次表';
```

### 3.9 培训签到记录表 (training_checkin)

```sql
CREATE TABLE `training_checkin` (
  `checkin_id` VARCHAR(20) NOT NULL COMMENT '签到ID',
  `session_id` VARCHAR(20) NOT NULL COMMENT '场次ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `checkin_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '签到时间',
  `checkin_method` VARCHAR(20) NOT NULL DEFAULT 'QR' COMMENT '签到方式: QR/FACE/MANUAL',
  `device_id` VARCHAR(50) DEFAULT NULL COMMENT '设备ID',
  `location` JSON DEFAULT NULL COMMENT '签到位置 (JSON: lat/lon)',
  `face_match_score` DECIMAL(4,3) DEFAULT NULL COMMENT '人脸匹配分数',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PRESENT' COMMENT '状态: PRESENT/ABSENT/LATE',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`checkin_id`),
  UNIQUE KEY `uk_session_emp` (`session_id`, `employee_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_employee_id` (`employee_id`),
  CONSTRAINT `fk_checkin_session` FOREIGN KEY (`session_id`) REFERENCES `training_session` (`session_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_checkin_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训签到记录表';
```

### 3.10 培训记录表 (training_record)

```sql
CREATE TABLE `training_record` (
  `record_id` VARCHAR(20) NOT NULL COMMENT '记录ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `session_id` VARCHAR(20) NOT NULL COMMENT '场次ID',
  `plan_id` VARCHAR(20) NOT NULL COMMENT '计划ID',
  `exam_score` DECIMAL(5,2) DEFAULT NULL COMMENT '考试成绩',
  `exam_pass` TINYINT(1) DEFAULT NULL COMMENT '考试是否通过',
  `certificate_issued` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已发证',
  `certificate_uri` VARCHAR(500) DEFAULT NULL COMMENT '证书文件链接',
  `certificate_no` VARCHAR(50) DEFAULT NULL COMMENT '证书编号',
  `satisfaction_score` DECIMAL(3,1) DEFAULT NULL COMMENT '满意度评分 (1-5)',
  `feedback` TEXT DEFAULT NULL COMMENT '培训反馈',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`record_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_plan_id` (`plan_id`),
  CONSTRAINT `fk_record_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_record_session` FOREIGN KEY (`session_id`) REFERENCES `training_session` (`session_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训记录表';
```

### 3.11 证书台账表 (certificate)

```sql
CREATE TABLE `certificate` (
  `cert_id` VARCHAR(20) NOT NULL COMMENT '证书ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `cert_name` VARCHAR(200) NOT NULL COMMENT '证书名称',
  `cert_no` VARCHAR(100) DEFAULT NULL COMMENT '证书编号',
  `issuing_authority` VARCHAR(100) DEFAULT NULL COMMENT '发证机关',
  `issue_date` DATE NOT NULL COMMENT '发证日期',
  `expire_date` DATE DEFAULT NULL COMMENT '到期日期',
  `file_uri` VARCHAR(500) DEFAULT NULL COMMENT '证书文件链接',
  `renewal_status` VARCHAR(20) NOT NULL DEFAULT 'VALID' COMMENT '续期状态: VALID/EXPIRING/EXPIRED/RENEWING',
  `renewal_reminder_days` INT NOT NULL DEFAULT 30 COMMENT '到期提醒天数',
  `reminder_sent` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已发送提醒',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`cert_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_expire_date` (`expire_date`),
  KEY `idx_renewal_status` (`renewal_status`),
  CONSTRAINT `fk_cert_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证书台账表';
```

### 3.12 薪资快照表 (payroll_snapshot)

```sql
CREATE TABLE `payroll_snapshot` (
  `snapshot_id` VARCHAR(32) NOT NULL COMMENT '快照ID (UUID)',
  `year_month` VARCHAR(7) NOT NULL COMMENT '薪资月份 (YYYY-MM)',
  `attendance_snapshot_ts` TIMESTAMP DEFAULT NULL COMMENT '考勤数据快照时间',
  `social_security_ts` TIMESTAMP DEFAULT NULL COMMENT '社保数据快照时间',
  `housing_fund_ts` TIMESTAMP DEFAULT NULL COMMENT '公积金数据快照时间',
  `payroll_rule_ts` TIMESTAMP DEFAULT NULL COMMENT '薪资规则快照时间',
  `allowance_ts` TIMESTAMP DEFAULT NULL COMMENT '补贴数据快照时间',
  `data_checksum` VARCHAR(64) DEFAULT NULL COMMENT '数据校验和 (SHA-256)',
  `status` VARCHAR(20) NOT NULL DEFAULT 'CREATED' COMMENT '状态: CREATED/LOCKED/ARCHIVED',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人/Agent',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`snapshot_id`),
  UNIQUE KEY `uk_year_month` (`year_month`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资快照表';
```

### 3.13 工资条表 (payslip)

```sql
CREATE TABLE `payslip` (
  `payslip_id` VARCHAR(20) NOT NULL COMMENT '工资条ID',
  `payroll_id` VARCHAR(20) NOT NULL COMMENT '薪资ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `month` VARCHAR(7) NOT NULL COMMENT '薪资月份',
  `payslip_uri` VARCHAR(500) DEFAULT NULL COMMENT '工资条文件链接',
  `send_method` VARCHAR(20) DEFAULT NULL COMMENT '发送方式: SMS/EMAIL/APP',
  `sent_at` TIMESTAMP NULL DEFAULT NULL COMMENT '发送时间',
  `read_at` TIMESTAMP NULL DEFAULT NULL COMMENT '阅读时间',
  `is_read` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已阅读',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`payslip_id`),
  UNIQUE KEY `uk_payroll` (`payroll_id`),
  KEY `idx_employee_month` (`employee_id`, `month`),
  CONSTRAINT `fk_payslip_payroll` FOREIGN KEY (`payroll_id`) REFERENCES `payroll` (`payroll_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_payslip_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工资条表';
```

### 3.14 工伤档案表 (injury_case)

```sql
CREATE TABLE `injury_case` (
  `case_id` VARCHAR(20) NOT NULL COMMENT '案件编号',
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
  `status` VARCHAR(20) NOT NULL DEFAULT 'OPENING' COMMENT '状态: OPENING/FILED/CLAIMING/COMPLETED/REJECTED',
  `handler_id` VARCHAR(20) DEFAULT NULL COMMENT '处理人ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`case_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_accident_date` (`accident_date`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_injury_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工伤档案表';
```

### 3.15 公积金记录表 (housing_fund_record)

```sql
CREATE TABLE `housing_fund_record` (
  `record_id` VARCHAR(20) NOT NULL COMMENT '记录ID',
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
  CONSTRAINT `fk_hf_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公积金记录表';
```

### 3.16 离职记录表 (resignation_record)

```sql
CREATE TABLE `resignation_record` (
  `resign_id` VARCHAR(20) NOT NULL COMMENT '离职记录ID',
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
  `approved_by` VARCHAR(20) DEFAULT NULL COMMENT '审批人ID',
  `approved_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审批时间',
  `status` VARCHAR(20) NOT NULL DEFAULT 'APPLIED' COMMENT '状态: APPLIED/APPROVED/HANDOVERING/COMPLETED/CANCELLED',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`resign_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_resign_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='离职记录表';
```

### 3.17 证明申请表 (proof_request)

```sql
CREATE TABLE `proof_request` (
  `request_id` VARCHAR(20) NOT NULL COMMENT '申请ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `cert_type` VARCHAR(50) NOT NULL COMMENT '证明类型: EMPLOYMENT_INCOME/RESIGNATION/OTHER',
  `purpose` VARCHAR(200) DEFAULT NULL COMMENT '用途说明',
  `custom_content` TEXT DEFAULT NULL COMMENT '自定义内容',
  `generated_file_uri` VARCHAR(500) DEFAULT NULL COMMENT '生成证明文件链接',
  `review_status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '审核状态: PENDING/APPROVED/REJECTED',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `reject_reason` TEXT DEFAULT NULL COMMENT '驳回原因',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`request_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_cert_type` (`cert_type`),
  KEY `idx_review_status` (`review_status`),
  CONSTRAINT `fk_cert_req_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证明申请表';

-- 说明: 表名 proof_request 替代原 certificate_request，避免与 certificate 证书台账表混淆。
```

### 3.18 费用报销表 (expense_claim)

```sql
CREATE TABLE `expense_claim` (
  `claim_id` VARCHAR(20) NOT NULL COMMENT '报销ID',
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
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`claim_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_claim_date` (`claim_date`),
  KEY `idx_category` (`category`),
  KEY `idx_review_status` (`review_status`),
  CONSTRAINT `fk_claim_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='费用报销表';
```

### 3.19 试卷表 (exam_paper)

```sql
CREATE TABLE `exam_paper` (
  `paper_id` VARCHAR(20) NOT NULL COMMENT '试卷ID',
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
  CONSTRAINT `fk_paper_position` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_paper_session` FOREIGN KEY (`training_session_id`) REFERENCES `training_session` (`session_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷表';
```

### 3.20 题目表 (exam_question)

```sql
CREATE TABLE `exam_question` (
  `question_id` VARCHAR(20) NOT NULL COMMENT '题目ID',
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
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/INACTIVE',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`question_id`),
  KEY `idx_category` (`category`),
  KEY `idx_question_type` (`question_type`),
  KEY `idx_difficulty` (`difficulty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目表';
```

### 3.21 试卷题目关联表 (paper_question)

```sql
CREATE TABLE `paper_question` (
  `pq_id` VARCHAR(20) NOT NULL COMMENT '关联ID',
  `paper_id` VARCHAR(20) NOT NULL COMMENT '试卷ID',
  `question_id` VARCHAR(20) NOT NULL COMMENT '题目ID',
  `display_order` INT NOT NULL DEFAULT 0 COMMENT '显示顺序',
  `score_override` DECIMAL(5,2) DEFAULT NULL COMMENT '分值覆盖 (NULL则使用题目默认分值)',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`pq_id`),
  UNIQUE KEY `uk_paper_question` (`paper_id`, `question_id`),
  KEY `idx_question_id` (`question_id`),
  CONSTRAINT `fk_pq_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper` (`paper_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_pq_question` FOREIGN KEY (`question_id`) REFERENCES `exam_question` (`question_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷题目关联表';
```

### 3.22 考试答题记录表 (exam_response)

```sql
CREATE TABLE `exam_response` (
  `response_id` VARCHAR(20) NOT NULL COMMENT '答题记录ID',
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
  `status` VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS' COMMENT '状态: IN_PROGRESS/SUBMITTED/GRADED/REVIEW_NEEDED',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`response_id`),
  KEY `idx_paper_id` (`paper_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_resume_id` (`resume_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_response_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper` (`paper_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_response_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee` (`employee_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_response_resume` FOREIGN KEY (`resume_id`) REFERENCES `resume` (`resume_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试答题记录表';
```

---

## 4. Agent 与审计表

### 4.1 Agent 执行日志表 (agent_run_log)

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
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
  PRIMARY KEY (`run_id`),
  KEY `idx_agent_name` (`agent_name`),
  KEY `idx_parent_flow_id` (`parent_flow_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent执行日志表';
```

### 4.2 审计日志表 (audit_log)

```sql
CREATE TABLE `audit_log` (
  `log_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `operation_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  `operator_id` VARCHAR(20) DEFAULT NULL COMMENT '操作人ID (NULL=系统/Agent/定时任务)',
  `operator_name` VARCHAR(50) DEFAULT NULL COMMENT '操作人姓名 (NULL=系统/Agent/定时任务)',
  `operator_type` VARCHAR(20) NOT NULL DEFAULT 'USER' COMMENT '操作人类型: USER/SYSTEM/AGENT/SCHEDULED',
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
  PRIMARY KEY (`log_id`),
  KEY `idx_operation_time` (`operation_time`),
  KEY `idx_operator_id` (`operator_id`),
  KEY `idx_module` (`module`),
  KEY `idx_operation_type` (`operation_type`),
  KEY `idx_target_id` (`target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';
```

### 4.3 RPA 任务表 (rpa_task)

```sql
CREATE TABLE `rpa_task` (
  `task_id` VARCHAR(20) NOT NULL COMMENT '任务ID',
  `target_system` VARCHAR(50) NOT NULL COMMENT '目标系统: SOCIAL_SECURITY/HOUSING_FUND/GOVERNMENT_OTHER',
  `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型: INJURY_FILING/HF_ENROLL/HF_SEAL/HF_SUPPLEMENT',
  `flow_id` VARCHAR(32) DEFAULT NULL COMMENT '所属业务流程ID',
  `employee_id` VARCHAR(20) DEFAULT NULL COMMENT '关联员工ID',
  `target_url` VARCHAR(500) NOT NULL COMMENT '目标URL',
  `form_data` JSON DEFAULT NULL COMMENT '表单数据',
  `upload_files` JSON DEFAULT NULL COMMENT '上传文件列表 (JSON)',
  `browser_screenshot` VARCHAR(500) DEFAULT NULL COMMENT '浏览器截图',
  `receipt_uri` VARCHAR(500) DEFAULT NULL COMMENT '操作回执文件',
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
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RPA任务表';
```

### 4.4 流程实例表 (process_instance)

```sql
CREATE TABLE `process_instance` (
  `flow_id` VARCHAR(32) NOT NULL COMMENT '流程ID (UUID)',
  `process_key` VARCHAR(100) NOT NULL COMMENT '流程类型: ONBOARDING/PAYROLL/INJURY/RESIGNATION/TRAINING',
  `trigger_type` VARCHAR(20) NOT NULL COMMENT '触发类型: MANUAL/AGENT/SCHEDULED/EVENT',
  `triggered_by` VARCHAR(20) DEFAULT NULL COMMENT '触发人/Agent',
  `context_data` JSON DEFAULT NULL COMMENT '流程上下文数据',
  `current_step` VARCHAR(100) DEFAULT NULL COMMENT '当前步骤',
  `status` VARCHAR(20) NOT NULL DEFAULT 'RUNNING' COMMENT '状态: RUNNING/COMPLETED/FAILED/SUSPENDED/CANCELLED',
  `result_summary` JSON DEFAULT NULL COMMENT '结果摘要',
  `error_detail` TEXT DEFAULT NULL COMMENT '错误详情',
  `started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
  `completed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
  `duration_ms` BIGINT DEFAULT NULL COMMENT '总耗时 (毫秒)',
  PRIMARY KEY (`flow_id`),
  KEY `idx_process_key` (`process_key`),
  KEY `idx_status` (`status`),
  KEY `idx_started_at` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='流程实例表';
```

### 4.5 通知消息表 (notification_message)

```sql
CREATE TABLE `notification_message` (
  `message_id` VARCHAR(20) NOT NULL COMMENT '消息ID',
  `recipient_id` VARCHAR(20) NOT NULL COMMENT '接收人ID',
  `message_type` VARCHAR(20) NOT NULL COMMENT '消息类型: EMAIL/SMS/PUSH/IN_APP',
  `template_code` VARCHAR(50) NOT NULL COMMENT '模板编码',
  `subject` VARCHAR(200) DEFAULT NULL COMMENT '主题',
  `content` TEXT NOT NULL COMMENT '消息内容',
  `payload` JSON DEFAULT NULL COMMENT '附加数据',
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
  CONSTRAINT `fk_notify_user` FOREIGN KEY (`recipient_id`) REFERENCES `sys_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知消息表';
```

### 4.6 薪资规则表 (payroll_rule)

```sql
CREATE TABLE `payroll_rule` (
  `rule_id` VARCHAR(20) NOT NULL COMMENT '规则ID',
  `rule_name` VARCHAR(100) NOT NULL COMMENT '规则名称',
  `rule_type` VARCHAR(50) NOT NULL COMMENT '规则类型: OVERTIME_RATE/DEDUCTION_STANDARD/ALLOWANCE/SS_RATIO/TAX_TABLE',
  `dept_id` VARCHAR(20) DEFAULT NULL COMMENT '适用部门ID (NULL=全公司通用)',
  `position_id` VARCHAR(20) DEFAULT NULL COMMENT '适用岗位ID (NULL=全岗位通用)',
  `rule_config` JSON NOT NULL COMMENT '规则配置 (JSON)',
  `effective_date` DATE NOT NULL COMMENT '生效日期',
  `expiry_date` DATE DEFAULT NULL COMMENT '失效日期',
  `version` INT NOT NULL DEFAULT 1 COMMENT '版本号',
  `description` TEXT DEFAULT NULL COMMENT '规则说明',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人ID',
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/INACTIVE',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`rule_id`),
  KEY `idx_rule_type` (`rule_type`),
  KEY `idx_dept_id` (`dept_id`),
  KEY `idx_position_id` (`position_id`),
  KEY `idx_effective_date` (`effective_date`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_rule_dept` FOREIGN KEY (`dept_id`) REFERENCES `department` (`dept_id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_rule_pos` FOREIGN KEY (`position_id`) REFERENCES `job_position` (`position_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资规则表';

> **V5.0 变更说明**：增加 dept_id 和 position_id 字段，支持按部门/岗位差异化配置薪资规则。当两者均为 NULL 时，规则适用于全公司全岗位。
```

### 4.7 视频课程表 (video_course)

```sql
CREATE TABLE `video_course` (
  `course_id` VARCHAR(20) NOT NULL COMMENT '课程ID',
  `title` VARCHAR(200) NOT NULL COMMENT '课程标题',
  `source_doc_uri` VARCHAR(500) DEFAULT NULL COMMENT '源教材文件链接',
  `video_uri` VARCHAR(500) NOT NULL COMMENT '视频文件链接 (MinIO)',
  `duration_seconds` INT NOT NULL COMMENT '视频时长 (秒)',
  `knowledge_points` JSON DEFAULT NULL COMMENT '知识点索引 (JSON)',
  `applicable_positions` TEXT DEFAULT NULL COMMENT '适用岗位 (逗号分隔)',
  `thumbnail_uri` VARCHAR(500) DEFAULT NULL COMMENT '缩略图链接',
  `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT '状态: DRAFT/REVIEWED/PUBLISHED/DELETED',
  `reviewed_by` VARCHAR(20) DEFAULT NULL COMMENT '审核人ID',
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
  `view_count` INT NOT NULL DEFAULT 0 COMMENT '播放次数',
  `created_by` VARCHAR(20) NOT NULL COMMENT '创建人/Agent',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`course_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频课程表';
```

---

## 5. 索引设计


### 统一逻辑删除

以下表已添加 `deleted_at` 字段，实现统一的逻辑删除机制：
`employee`, `resume`, `department`, `job_position`, `training_plan`, `performance_review`

- `deleted_at IS NULL`: 未删除，正常查询可见
- `deleted_at IS NOT NULL`: 已删除，查询时通过 `WHERE deleted_at IS NULL` 过滤
- MyBatis-Plus 自动注入 `WHERE deleted_at IS NULL` 条件（配置 `LogicDelete` 插件）

### 5.1 复合索引

```sql
-- 考勤查询优化
ALTER TABLE `attendance_record` 
  ADD INDEX `idx_emp_date_flag` (`employee_id`, `date`, `flag`);

-- 薪资月度查询优化
ALTER TABLE `payroll`
  ADD INDEX `idx_month_status` (`month`, `status`);

-- 简历多维查询优化
ALTER TABLE `resume`
  ADD INDEX `idx_position_score_classify` (`applied_position_name`, `total_score`, `classify_result`);

-- 绩效周期查询优化
ALTER TABLE `performance_review`
  ADD INDEX `idx_cycle_status` (`cycle`, `status`);

-- 培训记录查询优化
ALTER TABLE `training_record`
  ADD INDEX `idx_emp_exam_pass` (`employee_id`, `exam_pass`);

-- 证书到期预警查询优化
ALTER TABLE `certificate`
  ADD INDEX `idx_expire_renewal` (`expire_date`, `renewal_status`);

-- 审计日志查询优化
ALTER TABLE `audit_log`
  ADD INDEX `idx_time_operator_module` (`operation_time`, `operator_id`, `module`);

-- Agent日志查询优化
ALTER TABLE `agent_run_log`
  ADD INDEX `idx_agent_flow_status` (`agent_name`, `parent_flow_id`, `status`);

-- 通知消息查询优化
ALTER TABLE `notification_message`
  ADD INDEX `idx_recipient_status` (`recipient_id`, `send_status`);
```

### 5.2 全文索引

```sql
-- 简历全文搜索
ALTER TABLE `resume`
  ADD FULLTEXT INDEX `ft_resume_search` (`candidate_name`, `work_experience`, `education_summary`);

-- V5.0 变更说明：移除 skill_tags 和 certs JSON 字段（MySQL 8.0 不支持对 JSON 列建立 FULLTEXT INDEX）
-- 如需对 JSON 字段全文搜索，建议方案：
-- 1. 使用 Elasticsearch 对 JSON 字段建立索引（推荐）
-- 2. 使用 GENERATED ALWAYS AS 虚拟列提取 JSON 字段为 TEXT，再建立 FULLTEXT INDEX

-- 题目全文搜索
ALTER TABLE `exam_question`
  ADD FULLTEXT INDEX `ft_question_search` (`content`, `tags`);
```

---

## 6. 视图设计

### 6.1 员工综合信息视图

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
LEFT JOIN department d ON e.dept_id = d.dept_id
LEFT JOIN job_position p ON e.position_id = p.position_id
LEFT JOIN training_record tr ON e.employee_id = tr.employee_id
LEFT JOIN certificate c ON e.employee_id = c.employee_id
LEFT JOIN injury_case ic ON e.employee_id = ic.employee_id
GROUP BY e.employee_id;
```

### 6.2 月度考勤汇总视图

```sql
CREATE OR REPLACE VIEW `v_monthly_attendance` AS
SELECT 
  ar.employee_id,
  e.name,
  d.dept_name,
  DATE_FORMAT(ar.date, '%Y-%m') AS month,
  COUNT(*) AS total_days,
  SUM(CASE WHEN ar.flag = 'NORMAL' THEN 1 ELSE 0 END) AS normal_days,
  SUM(ar.late_minutes) AS total_late_minutes,
  SUM(ar.early_leave_minutes) AS total_early_leave_minutes,
  SUM(CASE WHEN ar.flag = 'ABSENT' THEN 1 ELSE 0 END) AS total_absent_days,
  SUM(ar.overtime_hrs) AS total_overtime_hrs,
  SUM(ar.holiday_leave_hrs) AS total_holiday_leave,
  SUM(ar.sick_leave_hrs) AS total_sick_leave
FROM attendance_record ar
JOIN employee e ON ar.employee_id = e.employee_id
LEFT JOIN department d ON e.dept_id = d.dept_id
GROUP BY ar.employee_id, e.name, d.dept_name, DATE_FORMAT(ar.date, '%Y-%m');
```

### 6.3 薪资汇总视图

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
WHERE p.status IN ('REVIEWED', 'PAID')
GROUP BY p.month;
```

### 6.4 培训效果统计视图

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
LEFT JOIN training_session ts ON tp.plan_id = ts.plan_id
LEFT JOIN training_checkin tc ON ts.session_id = tc.session_id
LEFT JOIN training_record tr ON tc.session_id = tr.session_id AND tc.employee_id = tr.employee_id
GROUP BY tp.plan_id, tp.plan_name, tp.training_type, tp.quarter;
```

---

## 7. 初始化数据

### 7.1 系统角色初始化

```sql
INSERT INTO `sys_role` (`role_id`, `role_name`, `role_code`, `description`, `is_system`) VALUES
('ROLE_ADMIN', '系统管理员', 'ADMIN', '系统基础设施运维和技术管理', 1),
('ROLE_HR', '人事专员', 'HR', 'HR流程监督者与审核人', 1),
('ROLE_MANAGER', '部门主管', 'MANAGER', '业务决策审批人', 1),
('ROLE_EMPLOYEE', '在职员工', 'EMPLOYEE', '自助信息查询者', 1),
('ROLE_EXTERNAL', '外务专员', 'EXTERNAL', '政务联络协调人', 1),
('ROLE_NEW_HIRE', '新员工', 'NEW_HIRE', '信息提供者', 1);
```

### 7.2 基础权限初始化

```sql
INSERT INTO `sys_permission` (`permission_id`, `permission_name`, `permission_code`, `resource_type`, `parent_id`) VALUES
-- 招聘管理
('PERM_REC_JOB', '岗位管理', 'recruitment:job:*', 'MENU', NULL),
('PERM_REC_RESUME', '简历管理', 'recruitment:resume:*', 'MENU', NULL),
('PERM_REC_EXAM', '考试管理', 'recruitment:exam:*', 'MENU', NULL),
('PERM_REC_TALENT', '人才库', 'recruitment:talent:*', 'MENU', NULL),
-- 入职管理
('PERM_ONB_ALL', '入职管理', 'onboarding:*:*', 'MENU', NULL),
-- 培训管理
('PERM_TRAIN_ALL', '培训管理', 'training:*:*', 'MENU', NULL),
-- 考勤管理
('PERM_ATT_ALL', '考勤管理', 'attendance:*:*', 'MENU', NULL),
-- 薪资管理
('PERM_PAY_ALL', '薪资管理', 'payroll:*:*', 'MENU', NULL),
('PERM_PAY_REVIEW', '薪资审核', 'payroll:review:approve', 'API', 'PERM_PAY_ALL'),
-- 绩效管理
('PERM_PERF_ALL', '绩效管理', 'performance:*:*', 'MENU', NULL),
-- 外务管理
('PERM_EXT_ALL', '外务管理', 'external:*:*', 'MENU', NULL),
-- 员工服务
('PERM_EMP_ALL', '员工服务', 'employee:*:*', 'MENU', NULL),
-- Agent 管理
('PERM_AGENT_ALL', 'Agent管理', 'agent:*:*', 'MENU', NULL),
-- 系统管理
('PERM_SYS_ALL', '系统管理', 'system:*:*', 'MENU', NULL);
```

### 7.3 角色权限分配

```sql
-- 系统管理员: 所有权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`)
SELECT 'ROLE_ADMIN', permission_id FROM sys_permission;

-- 人事专员: HR 相关权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
('ROLE_HR', 'PERM_REC_JOB'),
('ROLE_HR', 'PERM_REC_RESUME'),
('ROLE_HR', 'PERM_REC_EXAM'),
('ROLE_HR', 'PERM_REC_TALENT'),
('ROLE_HR', 'PERM_ONB_ALL'),
('ROLE_HR', 'PERM_TRAIN_ALL'),
('ROLE_HR', 'PERM_ATT_ALL'),
('ROLE_HR', 'PERM_PAY_ALL'),
('ROLE_HR', 'PERM_PERF_ALL'),
('ROLE_HR', 'PERM_EXT_ALL'),
('ROLE_HR', 'PERM_EMP_ALL');

-- 部门主管: 团队管理和审批权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
('ROLE_MANAGER', 'PERM_PERF_ALL'),
('ROLE_MANAGER', 'PERM_ATT_ALL'),
('ROLE_MANAGER', 'PERM_TRAIN_ALL');

-- 外务专员: 外务权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
('ROLE_EXTERNAL', 'PERM_EXT_ALL');

-- 在职员工: 自助服务权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
('ROLE_EMPLOYEE', 'PERM_EMP_ALL');
```

---

## 8. 分区与归档策略

> **V5.0 变更说明**：考勤表和薪资表原采用 MySQL RANGE 分区方案，但违反 MySQL 约束（分区键必须是主键的一部分）。V5.0 放弃分区方案，改为归档表策略。审计日志分区保留，但修正了边界计算逻辑。

### 8.1 考勤表归档（放弃分区方案）

> MySQL 要求分区键必须是主键/唯一键的一部分。`attendance_record` 主键为 `record_id` (BIGINT AUTO_INCREMENT)，而分区键 `YEAR(date)*100+MONTH(date)` 未包含在主键中，导致 `ALTER TABLE PARTITION` 报错。V5.0 改为归档表策略。

```sql
-- 考勤归档表（保留超过 24 个月的历史数据）
CREATE TABLE `attendance_record_archive` (
  `record_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `date` DATE NOT NULL COMMENT '考勤日期',
  `clock_in_time` TIME DEFAULT NULL COMMENT '上班打卡时间',
  `clock_out_time` TIME DEFAULT NULL COMMENT '下班打卡时间',
  `late_minutes` INT NOT NULL DEFAULT 0 COMMENT '迟到分钟数',
  `early_leave_minutes` INT NOT NULL DEFAULT 0 COMMENT '早退分钟数',
  `overtime_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '加班时长',
  `flag` VARCHAR(20) NOT NULL DEFAULT 'NORMAL' COMMENT '状态: NORMAL/LATE/EARLY_LEAVE/ABSENT/OVERTIME',
  `holiday_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '请假时长',
  `sick_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '病假时长',
  `maternity_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '产假时长',
  `business_trip_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '出差时长',
  `absence_reason` VARCHAR(200) DEFAULT NULL COMMENT '缺勤原因',
  `shift_id` VARCHAR(20) DEFAULT NULL COMMENT '班次ID',
  `device_id` VARCHAR(50) DEFAULT NULL COMMENT '打卡设备ID',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `archived_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '归档时间',
  PRIMARY KEY (`record_id`),
  KEY `idx_employee_date` (`employee_id`, `date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考勤记录归档表';
```

> **归档策略**：每月末将超过 24 个月的考勤数据迁移至 `attendance_record_archive` 表，原表仅保留最近 24 个月数据。

### 8.2 薪资表归档（放弃分区方案）

> `payroll` 表主键为 `payroll_id` (VARCHAR)，分区键 `TO_DAYS(month_date)` 未包含在主键中，违反 MySQL 分区规则。V5.0 改为归档表策略。

```sql
-- 薪资归档表（保留超过 15 年的历史薪资数据）
CREATE TABLE `payroll_archive` (
  `payroll_id` VARCHAR(20) NOT NULL COMMENT '薪资ID',
  `employee_id` VARCHAR(20) NOT NULL COMMENT '员工ID',
  `month` VARCHAR(7) NOT NULL COMMENT '薪资月份 (YYYY-MM)',
  `month_date` DATE GENERATED ALWAYS AS (CONCAT(month, '-01')) STORED COMMENT '月份日期',
  `snapshot_id` VARCHAR(32) DEFAULT NULL COMMENT '数据快照ID',
  `base_salary` DECIMAL(10,2) NOT NULL COMMENT '基本工资',
  `allowance` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '补贴',
  `overtime_pay` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '加班费',
  `bonus` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '奖金',
  `deduction` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '扣款',
  `social_security` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '社保个人部分',
  `housing_fund` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '公积金个人部分',
  `tax` DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '个人所得税',
  `net_salary` DECIMAL(10,2) NOT NULL COMMENT '实发工资',
  `attendance_snapshot_ts` TIMESTAMP DEFAULT NULL COMMENT '考勤数据快照时间',
  `social_security_ts` TIMESTAMP DEFAULT NULL COMMENT '社保数据快照时间',
  `housing_fund_ts` TIMESTAMP DEFAULT NULL COMMENT '公积金数据快照时间',
  `payroll_rule_ts` TIMESTAMP DEFAULT NULL COMMENT '薪资规则快照时间',
  `allowance_ts` TIMESTAMP DEFAULT NULL COMMENT '补贴数据快照时间',
  `data_checksum` VARCHAR(64) DEFAULT NULL COMMENT '数据校验和 (SHA-256)',
  `status` VARCHAR(20) NOT NULL DEFAULT 'CREATED' COMMENT '状态: CREATED/LOCKED/ARCHIVED',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `archived_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '归档时间',
  PRIMARY KEY (`payroll_id`),
  KEY `idx_employee_month` (`employee_id`, `month`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资归档表';
```

> **归档策略**：每年末将超过 15 年的薪资数据迁移至 `payroll_archive` 表，原表仅保留最近 15 年数据。

### 8.3 审计日志分区（按季度，已修正边界计算）

```sql
-- 审计日志按季度分区 (保留 10 年)
-- 修正：QUARTER() 返回 1-4，表达式 YEAR*100+QUARTER 得到 202601/202602/202603/202604
-- 边界值 LESS THAN 为开区间，如 p2026Q1 为 [202601, 202602)，包含 Q1 全部数据 (202601)
-- p2026Q2 为 [202602, 202603)，包含 Q2 全部数据 (202602)
-- p2026Q3 为 [202603, 202604)，包含 Q3 全部数据 (202603)
-- p2026Q4 为 [202604, 202701)，包含 Q4 全部数据 (202604)
ALTER TABLE `audit_log`
  PARTITION BY RANGE (YEAR(operation_time) * 100 + QUARTER(operation_time)) (
  PARTITION p2026Q1 VALUES LESS THAN (202602),
  PARTITION p2026Q2 VALUES LESS THAN (202603),
  PARTITION p2026Q3 VALUES LESS THAN (202604),
  PARTITION p2026Q4 VALUES LESS THAN (202701),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);
```

> **分区边界说明**：
> - `QUARTER()` 返回值：Q1→1, Q2→2, Q3→3, Q4→4
> - 表达式 `YEAR(t)*100 + QUARTER(t)` 结果：2026Q1→202601, 2026Q2→202602, 2026Q3→202603, 2026Q4→202604
> - `LESS THAN` 为开区间边界，数据落在 `[lower, upper)` 范围内
> - Q4 边界值修正为 `202701`（而非 `202605`），确保 Q4 数据 (202604) 正确落入 p2026Q4 分区

### 8.4 Agent 日志分区 (按月)

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

### 8.5 数据归档存储策略

| 数据类型 | 在线保留 | 离线归档 | 归档方式 |
|---------|---------|---------|---------|
| 考勤数据 | 24 个月 | ≥ 2 年 | 冷备表 + 压缩 |
| 薪资数据 | 15 年 | ≥ 15 年 | 独立归档库 |
| 简历数据 | 3 年 | ≥ 2 年 | MinIO 冷存储 |
| Agent 日志 | 6 个月 | ≥ 1 年 | Elasticsearch 归档 |
| 审计日志 | 10 年 | ≥ 10 年 | 独立归档库 |
| 培训记录 | 3 年 | ≥ 2 年 | 冷备表 |

---

## 附录: 数据库配置建议

### MySQL 8.x 推荐配置

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
transaction-isolation = READ COMMITTED

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

### 备份策略

```bash
# 全量备份 (每周日凌晨 1 点)
0 1 * * 0 mysqldump --all-databases --single-transaction --routines --triggers --master-data=2 | gzip > /backup/full_$(date +\%Y\%m\%d).sql.gz

# 增量备份 (每天凌晨 2 点, 基于 binlog)
0 2 * * * cp /var/lib/mysql/mysql-bin.* /backup/incremental/ 2>/dev/null
```

---

*文档结束*