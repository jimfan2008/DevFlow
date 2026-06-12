# GBM AI Agent HR 智能人力管理系统 — 数据库设计脚本 (V2)

## 版本信息

| 版本号 | 日期 | 作者 | 说明 |
|--------|------|------|------|
| 2.0 | 2026-06-12 | 后旺 | 基于 SRS V15 设计的完整 DDL 脚本 |

---

## 1. ER 概述

本系统共包含 18 张核心数据表，按业务域分组如下：

```
+----------------+     +------------------+
|  employee      |---->|  organization    |
|  (员工档案)     |     |  (组织架构)       |
+----------------+     +------------------+
        |                        |
        |                        |
+----------------+     +------------------+
|  resume        |     |  position        |
|  (简历数据)     |     |  (岗位管理)       |
+----------------+     +------------------+
        |
        v
+----------------+
|  onboarding_doc|
|  (入职资料)     |
+----------------+
        |
        v
+----------------+     +------------------+
|  attendance    |---->|  shift           |
|  (考勤记录)     |     |  (班次排班)       |
+----------------+     +------------------+
        |
        v
+----------------+
|  payroll       |
|  (薪资数据)     |
+----------------+

+----------------+     +------------------+
|  training_plan |---->|  training_record |
|  (培训计划)     |     |  (培训记录)       |
+----------------+     +------------------+
        |
        v
+----------------+
|  certificate   |
|  (证书台账)     |
+----------------+

+----------------+     +------------------+
|  performance   |     |  injury_case     |
|  (绩效评价)     |     |  (工伤档案)       |
+----------------+     +------------------+

+----------------+     +------------------+
|  housing_fund  |     |  resignation     |
|  (公积金记录)   |     |  (离职记录)       |
+----------------+     +------------------+

+----------------+     +------------------+
|  audit_log     |     |  agent_run_log   |
|  (审计日志)     |     |  (Agent执行日志)  |
+----------------+     +------------------+

+----------------+
|  face_library  |
|  (人脸库)       |
+----------------+

+----------------+
|  e_signature   |
|  (电子签章)     |
+----------------+
```

---

## 2. 完整 DDL 脚本

```sql
-- ============================================================
-- GBM AI Agent HR 系统 数据库 DDL 脚本 V2
-- 数据库: MySQL 8.x
-- 字符集: utf8mb4 / utf8mb4_unicode_ci
-- 日期: 2026-06-12
-- ============================================================

CREATE DATABASE IF NOT EXISTS gbm_hr
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE gbm_hr;

-- ============================================================
-- 1. 组织架构模块
-- ============================================================

-- 1.1 部门表
CREATE TABLE `organization` (
    `dept_id`         VARCHAR(20)  NOT NULL COMMENT '部门 ID',
    `dept_name`       VARCHAR(100) NOT NULL COMMENT '部门名称',
    `parent_dept_id`  VARCHAR(20)  DEFAULT NULL COMMENT '上级部门 ID (NULL=根部门)',
    `level`           TINYINT      NOT NULL DEFAULT 1 COMMENT '层级深度',
    `manager_id`      VARCHAR(20)  DEFAULT NULL COMMENT '部门负责人工号',
    `sort_order`      INT          NOT NULL DEFAULT 0 COMMENT '排序序号',
    `status`          TINYINT      NOT NULL DEFAULT 1 COMMENT '状态: 1=启用 0=停用',
    `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`dept_id`),
    KEY `idx_parent_dept` (`parent_dept_id`),
    KEY `idx_manager` (`manager_id`),
    CONSTRAINT `fk_org_parent` FOREIGN KEY (`parent_dept_id`) REFERENCES `organization`(`dept_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组织架构/部门表';

-- 1.2 岗位表
CREATE TABLE `position` (
    `position_id`     VARCHAR(20)   NOT NULL COMMENT '岗位 ID',
    `position_name`   VARCHAR(100)  NOT NULL COMMENT '岗位名称',
    `dept_id`         VARCHAR(20)   NOT NULL COMMENT '所属部门',
    `job_level`       VARCHAR(20)   DEFAULT NULL COMMENT '职级',
    `headcount`       INT           NOT NULL DEFAULT 1 COMMENT '编制人数',
    `education_req`   VARCHAR(50)   DEFAULT NULL COMMENT '学历要求',
    `experience_req`  INT           DEFAULT NULL COMMENT '工作年限要求',
    `skill_keywords`  TEXT          DEFAULT NULL COMMENT '技能关键词 (JSON 数组)',
    `age_range`       VARCHAR(20)   DEFAULT NULL COMMENT '年龄范围 (如 25-35)',
    `cert_required`   TEXT          DEFAULT NULL COMMENT '所需证书 (JSON 数组)',
    `description`     TEXT          DEFAULT NULL COMMENT '岗位描述',
    `status`          TINYINT       NOT NULL DEFAULT 1 COMMENT '状态: 1=启用 0=停用',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`position_id`),
    KEY `idx_dept` (`dept_id`),
    CONSTRAINT `fk_pos_dept` FOREIGN KEY (`dept_id`) REFERENCES `organization`(`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位管理表';

-- ============================================================
-- 2. 员工档案模块
-- ============================================================

-- 2.1 员工表
CREATE TABLE `employee` (
    `employee_id`     VARCHAR(20)  NOT NULL COMMENT '工号',
    `name`            VARCHAR(50)  NOT NULL COMMENT '姓名',
    `id_number`       VARCHAR(18)  NOT NULL COMMENT '身份证号 (AES-256 加密存储)',
    `gender`          CHAR(1)      NOT NULL COMMENT '性别: M/F',
    `birth_date`      DATE         NOT NULL COMMENT '出生日期',
    `phone`           VARCHAR(20)  NOT NULL COMMENT '手机号码',
    `email`           VARCHAR(100) DEFAULT NULL COMMENT '电子邮箱',
    `dept_id`         VARCHAR(20)  DEFAULT NULL COMMENT '所属部门',
    `position_id`     VARCHAR(20)  DEFAULT NULL COMMENT '现任岗位',
    `hire_date`       DATE         NOT NULL COMMENT '入职日期',
    `leave_date`      DATE         DEFAULT NULL COMMENT '离职日期 (NULL=在职)',
    `status`          VARCHAR(20)  NOT NULL DEFAULT '在职' COMMENT '状态: 在职/试用期/停薪留职/离职',
    `contract_start`  DATE         DEFAULT NULL COMMENT '合同起始日',
    `contract_end`    DATE         DEFAULT NULL COMMENT '合同到期日',
    `probation_end`   DATE         DEFAULT NULL COMMENT '试用期届满日',
    `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`employee_id`),
    UNIQUE KEY `uk_id_number` (`id_number`),
    KEY `idx_dept` (`dept_id`),
    KEY `idx_status` (`status`),
    KEY `idx_leave_date` (`leave_date`),
    CONSTRAINT `fk_emp_dept` FOREIGN KEY (`dept_id`) REFERENCES `organization`(`dept_id`),
    CONSTRAINT `fk_emp_pos` FOREIGN KEY (`position_id`) REFERENCES `position`(`position_id`),
    CONSTRAINT `chk_gender` CHECK (`gender` IN ('M', 'F')),
    CONSTRAINT `chk_status` CHECK (`status` IN ('在职', '试用期', '停薪留职', '离职'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工档案表';

-- ============================================================
-- 3. 简历管理模块
-- ============================================================

-- 3.1 简历表
CREATE TABLE `resume` (
    `resume_id`         VARCHAR(20)   NOT NULL COMMENT '简历 ID',
    `candidate_name`    VARCHAR(50)   NOT NULL COMMENT '姓名',
    `id_number`         VARCHAR(18)   DEFAULT NULL COMMENT '身份证号 (加密, 用于去重)',
    `phone`             VARCHAR(20)   DEFAULT NULL COMMENT '手机号 (用于去重)',
    `email`             VARCHAR(100)  DEFAULT NULL COMMENT '邮箱',
    `source_platform`   VARCHAR(50)   NOT NULL COMMENT '来源平台',
    `education`         VARCHAR(50)   DEFAULT NULL COMMENT '最高学历',
    `years_of_exp`      INT           DEFAULT NULL COMMENT '从业年限',
    `skill_tags`        TEXT          DEFAULT NULL COMMENT '技能标签 (逗号分隔)',
    `age`               INT           DEFAULT NULL COMMENT '年龄',
    `certs`             TEXT          DEFAULT NULL COMMENT '持证情况',
    `applied_position`  VARCHAR(100)  NOT NULL COMMENT '应聘岗位',
    `total_score`       DECIMAL(5,2)  DEFAULT NULL COMMENT '综合匹配分 (0-100)',
    `score_education`   DECIMAL(5,2)  DEFAULT NULL COMMENT '学历匹配分',
    `score_experience`  DECIMAL(5,2)  DEFAULT NULL COMMENT '经验匹配分',
    `score_skill`       DECIMAL(5,2)  DEFAULT NULL COMMENT '技能匹配分',
    `score_age`         DECIMAL(5,2)  DEFAULT NULL COMMENT '年龄匹配分',
    `score_cert`        DECIMAL(5,2)  DEFAULT NULL COMMENT '证书匹配分',
    `score_semantic`    DECIMAL(5,2)  DEFAULT NULL COMMENT '语义综合匹配分',
    `reasoning_summary` TEXT          DEFAULT NULL COMMENT '推理摘要',
    `classify_result`   VARCHAR(20)   DEFAULT NULL COMMENT '分拣结果: 高潜/候审/淘汰',
    `format_flag`       VARCHAR(20)   DEFAULT NULL COMMENT '格式异常标记',
    `file_uri`          VARCHAR(500)  DEFAULT NULL COMMENT '简历文件链接',
    `employee_id`       VARCHAR(20)   DEFAULT NULL COMMENT '关联工号 (入职后)',
    `created_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`resume_id`),
    KEY `idx_position` (`applied_position`),
    KEY `idx_classify` (`classify_result`),
    KEY `idx_score` (`total_score`),
    KEY `idx_created` (`created_at`),
    KEY `idx_dedup` (`id_number`, `phone`, `applied_position`),
    CONSTRAINT `chk_classify` CHECK (`classify_result` IN ('高潜', '候审', '淘汰', NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历数据表';

-- 3.2 招聘信息发布表
CREATE TABLE `job_post` (
    `post_id`         VARCHAR(20)   NOT NULL COMMENT '发布 ID',
    `position_id`     VARCHAR(20)   NOT NULL COMMENT '岗位 ID',
    `title`           VARCHAR(200)  NOT NULL COMMENT '招聘标题',
    `description`     TEXT          NOT NULL COMMENT '职位描述 (LLM 生成)',
    `platform`        VARCHAR(50)   NOT NULL COMMENT '发布平台',
    `platform_url`    VARCHAR(500)  DEFAULT NULL COMMENT '平台 URL',
    `apply_count`     INT           NOT NULL DEFAULT 0 COMMENT '投递量',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '已发布' COMMENT '状态: 草稿/已发布/已下架',
    `version`         INT           NOT NULL DEFAULT 1 COMMENT '版本号',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`post_id`),
    KEY `idx_position` (`position_id`),
    KEY `idx_platform` (`platform`),
    CONSTRAINT `fk_post_pos` FOREIGN KEY (`position_id`) REFERENCES `position`(`position_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='招聘信息发布表';

-- 3.3 试卷表
CREATE TABLE `exam_paper` (
    `paper_id`        VARCHAR(20)   NOT NULL COMMENT '试卷 ID',
    `position_id`     VARCHAR(20)   DEFAULT NULL COMMENT '关联岗位',
    `exam_type`       VARCHAR(20)   NOT NULL COMMENT '考试类型: 面试/入职培训/在岗培训',
    `total_questions` INT           NOT NULL DEFAULT 40 COMMENT '题量',
    `single_choice_count` INT NOT NULL DEFAULT 16 COMMENT '单选题数量',
    `multi_choice_count`  INT NOT NULL DEFAULT 12 COMMENT '多选题数量',
    `true_false_count`    INT NOT NULL DEFAULT 12 COMMENT '判断题数量',
    `qr_code`         VARCHAR(100)  NOT NULL COMMENT '考试二维码 (唯一)',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '待发布' COMMENT '状态: 待发布/已发布/已过期',
    `created_by`      VARCHAR(20)   NOT NULL DEFAULT 'Agent' COMMENT '创建人',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`paper_id`),
    UNIQUE KEY `uk_qr` (`qr_code`),
    KEY `idx_type` (`exam_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷表';

-- 3.4 考试成绩表
CREATE TABLE `exam_result` (
    `result_id`       VARCHAR(20)   NOT NULL COMMENT '成绩 ID',
    `paper_id`        VARCHAR(20)   NOT NULL COMMENT '试卷 ID',
    `employee_id`     VARCHAR(20)   DEFAULT NULL COMMENT '员工工号 (入职后)',
    `candidate_name`  VARCHAR(50)   NOT NULL COMMENT '考生姓名',
    `total_score`     DECIMAL(5,2)  NOT NULL COMMENT '总分',
    `pass_score`      DECIMAL(5,2)  NOT NULL DEFAULT 60 COMMENT '及格线',
    `is_pass`         TINYINT       NOT NULL DEFAULT 0 COMMENT '是否及格: 1=是 0=否',
    `objective_score` DECIMAL(5,2)  DEFAULT NULL COMMENT '客观题得分',
    `subjective_score` DECIMAL(5,2) DEFAULT NULL COMMENT '主观题得分',
    `ai_cross_check`  TEXT          DEFAULT NULL COMMENT 'AI 交叉评分报告 (JSON)',
    `submit_time`     DATETIME      NOT NULL COMMENT '提交时间',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`result_id`),
    KEY `idx_paper` (`paper_id`),
    KEY `idx_employee` (`employee_id`),
    CONSTRAINT `fk_result_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper`(`paper_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试成绩表';

-- ============================================================
-- 4. 入职管理模块
-- ============================================================

-- 4.1 入职资料表
CREATE TABLE `onboarding_doc` (
    `doc_id`          VARCHAR(20)   NOT NULL COMMENT '资料 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `doc_type`        VARCHAR(50)   NOT NULL COMMENT '资料类型: 身份证/学历证/资格证/体检报告/协议',
    `file_uri`        VARCHAR(500)  NOT NULL COMMENT '文件存储路径',
    `ocr_result`      JSON          DEFAULT NULL COMMENT 'OCR 识别结果',
    `verification`    VARCHAR(20)   NOT NULL DEFAULT '待核验' COMMENT '核验状态: 待核验/已通过/未通过',
    `watermark`       VARCHAR(100)  DEFAULT NULL COMMENT '安全水印 ID',
    `timestamp_sig`   VARCHAR(100)  DEFAULT NULL COMMENT '时间戳签名',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`doc_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_type` (`doc_type`),
    CONSTRAINT `fk_ondoc_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='入职资料表';

-- 4.2 电子签章表
CREATE TABLE `e_signature` (
    `sig_id`          VARCHAR(20)   NOT NULL COMMENT '签章 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '签署人工号',
    `doc_type`        VARCHAR(50)   NOT NULL COMMENT '协议类型: 劳动合同/保密协议/规章制度确认',
    `doc_uri`         VARCHAR(500)  NOT NULL COMMENT '协议原文路径',
    `signature_uri`   VARCHAR(500)  NOT NULL COMMENT '手写签名路径',
    `signed_at`       DATETIME      NOT NULL COMMENT '签署时间',
    `timestamp_sig`   VARCHAR(100)  NOT NULL COMMENT '时间戳签名',
    `ip_address`      VARCHAR(45)   DEFAULT NULL COMMENT '签署时 IP',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '已签署' COMMENT '状态: 已签署/已撤销',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`sig_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_signed_at` (`signed_at`),
    CONSTRAINT `fk_sig_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='电子签章存证表';

-- 4.3 人脸库表
CREATE TABLE `face_library` (
    `face_id`         VARCHAR(20)   NOT NULL COMMENT '人脸 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `face_features`   LONGTEXT      NOT NULL COMMENT '人脸特征向量 (加密存储)',
    `photo_uri`       VARCHAR(500)  NOT NULL COMMENT '人脸照片路径',
    `id_photo_match`  DECIMAL(5,2)  DEFAULT NULL COMMENT '与身份证照片比对可信度 (0-100)',
    `quality_score`   DECIMAL(5,2)  DEFAULT NULL COMMENT '照片质量评分 (0-100)',
    `access_granted`  TINYINT       NOT NULL DEFAULT 0 COMMENT '门禁权限: 1=已开通',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`face_id`),
    UNIQUE KEY `uk_employee` (`employee_id`),
    CONSTRAINT `fk_face_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人脸特征库表';

-- ============================================================
-- 5. 考勤管理模块
-- ============================================================

-- 5.1 班次表
CREATE TABLE `shift` (
    `shift_id`        VARCHAR(20)   NOT NULL COMMENT '班次 ID',
    `shift_name`      VARCHAR(50)   NOT NULL COMMENT '班次名称',
    `clock_in_time`   TIME          NOT NULL COMMENT '上班时间',
    `clock_out_time`  TIME          NOT NULL COMMENT '下班时间',
    `break_start`     TIME          DEFAULT NULL COMMENT '午休开始',
    `break_end`       TIME          DEFAULT NULL COMMENT '午休结束',
    `effective_from`  DATE          NOT NULL COMMENT '生效起始日',
    `effective_to`    DATE          DEFAULT NULL COMMENT '生效终止日 (NULL=长期)',
    `status`          TINYINT       NOT NULL DEFAULT 1 COMMENT '状态: 1=启用 0=停用',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`shift_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班次定义表';

-- 5.2 排班表
CREATE TABLE `shift_schedule` (
    `schedule_id`     VARCHAR(20)   NOT NULL COMMENT '排班 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `shift_id`        VARCHAR(20)   NOT NULL COMMENT '班次',
    `work_date`       DATE          NOT NULL COMMENT '工作日期',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`schedule_id`),
    UNIQUE KEY `uk_emp_date` (`employee_id`, `work_date`),
    KEY `idx_date` (`work_date`),
    CONSTRAINT `fk_sched_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`),
    CONSTRAINT `fk_sched_shift` FOREIGN KEY (`shift_id`) REFERENCES `shift`(`shift_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='排班表';

-- 5.3 考勤记录表
CREATE TABLE `attendance_record` (
    `record_id`           VARCHAR(20)   NOT NULL COMMENT '记录 ID',
    `employee_id`         VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `date`                DATE          NOT NULL COMMENT '日期',
    `clock_in`            TIME          DEFAULT NULL COMMENT '上班打卡',
    `clock_out`           TIME          DEFAULT NULL COMMENT '下班打卡',
    `shift_id`            VARCHAR(20)   DEFAULT NULL COMMENT '班次',
    `late_count`          INT           NOT NULL DEFAULT 0 COMMENT '迟到次数',
    `early_leave_count`   INT           NOT NULL DEFAULT 0 COMMENT '早退次数',
    `absent_days`         INT           NOT NULL DEFAULT 0 COMMENT '旷工天数',
    `holiday_leave_hrs`   DECIMAL(5,2)  NOT NULL DEFAULT 0 COMMENT '事假小时数',
    `sick_leave_hrs`      DECIMAL(5,2)  NOT NULL DEFAULT 0 COMMENT '病假小时数',
    `overtime_hrs`        DECIMAL(5,2)  NOT NULL DEFAULT 0 COMMENT '加班时长',
    `flag`                VARCHAR(20)   DEFAULT NULL COMMENT '异常标志: 迟到/早退/缺卡/旷工/加班超限',
    `raw_data`            JSON          DEFAULT NULL COMMENT '原始打卡数据',
    `created_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`record_id`),
    UNIQUE KEY `uk_emp_date` (`employee_id`, `date`),
    KEY `idx_date` (`date`),
    KEY `idx_flag` (`flag`),
    CONSTRAINT `fk_att_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`),
    CONSTRAINT `fk_att_shift` FOREIGN KEY (`shift_id`) REFERENCES `shift`(`shift_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考勤记录表';

-- ============================================================
-- 6. 薪资管理模块
-- ============================================================

-- 6.1 薪资主数据表
CREATE TABLE `salary_profile` (
    `profile_id`      VARCHAR(20)   NOT NULL COMMENT '薪资档案 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `base_pay`        DECIMAL(10,2) NOT NULL COMMENT '基本工资',
    `position_allowance` DECIMAL(10,2) DEFAULT 0 COMMENT '岗位津贴',
    `other_allowance` DECIMAL(10,2) DEFAULT 0 COMMENT '其他补贴',
    `bonus_base`      DECIMAL(10,2) DEFAULT 0 COMMENT '绩效奖金基数',
    `effective_date`  DATE          NOT NULL COMMENT '生效日期',
    `version`         INT           NOT NULL DEFAULT 1 COMMENT '版本号',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`profile_id`),
    UNIQUE KEY `uk_employee` (`employee_id`),
    CONSTRAINT `fk_salprof_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工薪资主数据表';

-- 6.2 薪资规则表
CREATE TABLE `salary_rule` (
    `rule_id`         VARCHAR(20)   NOT NULL COMMENT '规则 ID',
    `rule_name`       VARCHAR(100)  NOT NULL COMMENT '规则名称',
    `rule_type`       VARCHAR(50)   NOT NULL COMMENT '类型: 加班系数/迟到扣款/补贴定额/社保比例',
    `rule_config`     JSON          NOT NULL COMMENT '规则配置 (JSON)',
    `effective_from`  DATE          NOT NULL COMMENT '生效起始日',
    `effective_to`    DATE          DEFAULT NULL COMMENT '生效终止日',
    `version`         INT           NOT NULL DEFAULT 1 COMMENT '版本号',
    `created_by`      VARCHAR(20)   DEFAULT NULL COMMENT '创建人',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`rule_id`),
    KEY `idx_type` (`rule_type`),
    KEY `idx_effective` (`effective_from`, `effective_to`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资规则表';

-- 6.3 薪资核算表
CREATE TABLE `payroll` (
    `payroll_id`          VARCHAR(20)   NOT NULL COMMENT '薪资记录 ID',
    `employee_id`         VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `month`               VARCHAR(7)    NOT NULL COMMENT '月份 YYYY-MM',
    `base_pay`            DECIMAL(10,2) NOT NULL COMMENT '基本工资',
    `overtime_pay`        DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '加班费',
    `overtime_regular`    DECIMAL(10,2) DEFAULT 0 COMMENT '平日加班费 (1.5x)',
    `overtime_weekend`    DECIMAL(10,2) DEFAULT 0 COMMENT '周末加班费 (2x)',
    `overtime_holiday`    DECIMAL(10,2) DEFAULT 0 COMMENT '法定节假日加班费 (3x)',
    `overtime_over_flag`  TINYINT       NOT NULL DEFAULT 0 COMMENT '加班超限标记: 1=超36h',
    `attendance_deduct`   DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '考勤扣款',
    `allowances_total`    DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '补贴合计',
    `deduction_total`     DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '扣款合计',
    `earned_pay`          DECIMAL(10,2) NOT NULL COMMENT '应发工资',
    `ss_personal`         DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '社保个人缴纳',
    `gf_personal`         DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '公积金个人缴纳',
    `taxable_income`      DECIMAL(10,2) DEFAULT 0 COMMENT '应税收入',
    `income_tax`          DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '个税',
    `special_deduction`   DECIMAL(10,2) DEFAULT 0 COMMENT '专项附加扣除',
    `net_pay`             DECIMAL(10,2) NOT NULL COMMENT '实发工资',
    `anomaly_flag`        VARCHAR(50)   DEFAULT NULL COMMENT '异常标记',
    `calculation_trace`   JSON          DEFAULT NULL COMMENT '计算溯源底稿',
    `status`              VARCHAR(20)   NOT NULL DEFAULT '已核算' COMMENT '状态: 已核算/已审核/已发放',
    `reviewed_by`         VARCHAR(20)   DEFAULT NULL COMMENT '审核人工号',
    `reviewed_at`         DATETIME      DEFAULT NULL COMMENT '审核时间',
    `created_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`payroll_id`),
    UNIQUE KEY `uk_emp_month` (`employee_id`, `month`),
    KEY `idx_month` (`month`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_payroll_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`),
    CONSTRAINT `chk_payroll_status` CHECK (`status` IN ('已核算', '已审核', '已发放'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='月度薪资核算表';

-- 6.4 工资条发送记录表
CREATE TABLE `payslip_delivery` (
    `delivery_id`     VARCHAR(20)   NOT NULL COMMENT '发送记录 ID',
    `payroll_id`      VARCHAR(20)   NOT NULL COMMENT '薪资记录 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `channel`         VARCHAR(20)   NOT NULL COMMENT '发送渠道: 短信/邮件/APP',
    `sent_at`         DATETIME      DEFAULT NULL COMMENT '发送时间',
    `read_at`         DATETIME      DEFAULT NULL COMMENT '阅读时间',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '待发送' COMMENT '状态: 待发送/已发送/已阅读/发送失败',
    `retry_count`     INT           NOT NULL DEFAULT 0 COMMENT '重试次数',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`delivery_id`),
    KEY `idx_payroll` (`payroll_id`),
    KEY `idx_employee` (`employee_id`),
    CONSTRAINT `fk_payslip_payroll` FOREIGN KEY (`payroll_id`) REFERENCES `payroll`(`payroll_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工资条发送记录表';

-- ============================================================
-- 7. 培训管理模块
-- ============================================================

-- 7.1 培训计划表
CREATE TABLE `training_plan` (
    `plan_id`         VARCHAR(20)   NOT NULL COMMENT '计划 ID',
    `plan_name`       VARCHAR(200)  NOT NULL COMMENT '培训计划名称',
    `training_type`   VARCHAR(50)   NOT NULL COMMENT '类型: 入职培训/在岗培训/专项培训',
    `start_date`      DATE          NOT NULL COMMENT '开始日期',
    `end_date`        DATE          NOT NULL COMMENT '结束日期',
    `qr_code`         VARCHAR(100)  DEFAULT NULL COMMENT '签到二维码',
    `trainer`         VARCHAR(50)   DEFAULT NULL COMMENT '培训讲师',
    `venue`           VARCHAR(200)  DEFAULT NULL COMMENT '培训地点',
    `max_participants` INT          DEFAULT NULL COMMENT '最大参训人数',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '计划中' COMMENT '状态: 计划中/进行中/已完成/已取消',
    `created_by`      VARCHAR(20)   DEFAULT NULL COMMENT '创建人',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`plan_id`),
    KEY `idx_type` (`training_type`),
    KEY `idx_status` (`status`),
    KEY `idx_date` (`start_date`, `end_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训计划表';

-- 7.2 培训记录表
CREATE TABLE `training_record` (
    `record_id`       VARCHAR(20)   NOT NULL COMMENT '记录 ID',
    `plan_id`         VARCHAR(20)   NOT NULL COMMENT '培训计划 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `checkin_time`    DATETIME      DEFAULT NULL COMMENT '签到时间',
    `checkout_time`   DATETIME      DEFAULT NULL COMMENT '签退时间',
    `attendance_status` VARCHAR(20) NOT NULL DEFAULT '未签到' COMMENT '状态: 未签到/已签到/迟到/缺席',
    `exam_score`      DECIMAL(5,2)  DEFAULT NULL COMMENT '考试分数',
    `is_pass`         TINYINT       DEFAULT NULL COMMENT '是否合格: 1=是 0=否 NULL=未考试',
    `certificate_issued` TINYINT    NOT NULL DEFAULT 0 COMMENT '是否已发证',
    `certificate_uri` VARCHAR(500)  DEFAULT NULL COMMENT '结业证书路径',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`record_id`),
    UNIQUE KEY `uk_plan_emp` (`plan_id`, `employee_id`),
    KEY `idx_employee` (`employee_id`),
    CONSTRAINT `fk_trrecord_plan` FOREIGN KEY (`plan_id`) REFERENCES `training_plan`(`plan_id`),
    CONSTRAINT `fk_trrecord_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训记录表';

-- 7.3 培训视频表
CREATE TABLE `training_video` (
    `video_id`        VARCHAR(20)   NOT NULL COMMENT '视频 ID',
    `title`           VARCHAR(200)  NOT NULL COMMENT '视频标题',
    `source_doc_uri`  VARCHAR(500)  DEFAULT NULL COMMENT '源教材路径',
    `video_uri`       VARCHAR(500)  NOT NULL COMMENT '视频文件路径 (MP4)',
    `duration_sec`    INT           NOT NULL COMMENT '视频时长 (秒)',
    `knowledge_tags`  TEXT          DEFAULT NULL COMMENT '知识点索引 (JSON)',
    `applicable_pos`  TEXT          DEFAULT NULL COMMENT '适用岗位 (JSON)',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '已发布' COMMENT '状态: 生成中/已发布/已下架',
    `created_by`      VARCHAR(20)   DEFAULT NULL COMMENT '创建人',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`video_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训视频表';

-- ============================================================
-- 8. 证书管理模块
-- ============================================================

CREATE TABLE `certificate` (
    `cert_id`         VARCHAR(20)   NOT NULL COMMENT '证书 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `cert_type`       VARCHAR(50)   NOT NULL COMMENT '类型: 特种作业证/上岗证/行业资格证/结业证',
    `cert_name`       VARCHAR(200)  NOT NULL COMMENT '证书名称',
    `cert_no`         VARCHAR(100)  DEFAULT NULL COMMENT '证书编号',
    `issue_date`      DATE          DEFAULT NULL COMMENT '发证日期',
    `expiry_date`     DATE          DEFAULT NULL COMMENT '到期日期',
    `issuing_org`     VARCHAR(200)  DEFAULT NULL COMMENT '发证机构',
    `file_uri`        VARCHAR(500)  DEFAULT NULL COMMENT '证书影像路径',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '有效' COMMENT '状态: 有效/即将到期/已过期/待人工确认',
    `alert_days`      INT           NOT NULL DEFAULT 60 COMMENT '预警天数',
    `next_alert_date` DATE          DEFAULT NULL COMMENT '下次预警日期',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`cert_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_expiry` (`expiry_date`),
    KEY `idx_type` (`cert_type`),
    CONSTRAINT `fk_cert_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证书台账表';

-- ============================================================
-- 9. 绩效管理模块
-- ============================================================

CREATE TABLE `performance_review` (
    `pr_id`           VARCHAR(20)   NOT NULL COMMENT '考核记录 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `cycle`           VARCHAR(7)    NOT NULL COMMENT '考核周期 (YYYY-MM 或 YYYY-Q1)',
    `review_type`     VARCHAR(20)   NOT NULL DEFAULT '普通' COMMENT '类型: 普通/管理',
    `self_score`      DECIMAL(5,2)  DEFAULT NULL COMMENT '自评分',
    `peer_score`      DECIMAL(5,2)  DEFAULT NULL COMMENT '互评分',
    `sub_score`       DECIMAL(5,2)  DEFAULT NULL COMMENT '下属评议分',
    `mgr_score`       DECIMAL(5,2)  DEFAULT NULL COMMENT '上级评分',
    `final_score`     DECIMAL(5,2)  DEFAULT NULL COMMENT '最终得分',
    `rating`          VARCHAR(2)    DEFAULT NULL COMMENT '等级: A/B/C/D',
    `comments`        TEXT          DEFAULT NULL COMMENT '评语',
    `submit_at`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    `approve_at`      DATETIME      DEFAULT NULL COMMENT '审批时间',
    `approved_by`     VARCHAR(20)   DEFAULT NULL COMMENT '审批人工号',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`pr_id`),
    UNIQUE KEY `uk_emp_cycle` (`employee_id`, `cycle`),
    KEY `idx_cycle` (`cycle`),
    KEY `idx_rating` (`rating`),
    CONSTRAINT `fk_perf_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`),
    CONSTRAINT `chk_rating` CHECK (`rating` IN ('A', 'B', 'C', 'D', NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='绩效考核表';

-- ============================================================
-- 10. 外务管理模块
-- ============================================================

-- 10.1 工伤档案表
CREATE TABLE `injury_case` (
    `case_id`         VARCHAR(20)   NOT NULL COMMENT '案件编号',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '受伤员工',
    `accident_date`   DATE          NOT NULL COMMENT '事故发生日',
    `description`     TEXT          NOT NULL COMMENT '事故描述',
    `docs`            JSON          DEFAULT NULL COMMENT '材料清单和路径',
    `filing_no`       VARCHAR(50)   DEFAULT NULL COMMENT '备案受理号',
    `claim_amount`    DECIMAL(10,2) DEFAULT NULL COMMENT '理赔金额',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '立案中' COMMENT '状态: 立案中/申报中/理赔中/理赔完成/驳回',
    `rpa_receipts`    JSON          DEFAULT NULL COMMENT 'RPA 操作截图凭证',
    `progress_log`    JSON          DEFAULT NULL COMMENT '理赔进度跟踪记录',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`case_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_injury_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工伤档案表';

-- 10.2 公积金记录表
CREATE TABLE `housing_fund` (
    `record_id`       VARCHAR(20)   NOT NULL COMMENT '记录 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `operation_type`  VARCHAR(20)   NOT NULL COMMENT '操作类型: 开户/缴存/补缴/封存/销户',
    `base_amount`     DECIMAL(10,2) DEFAULT NULL COMMENT '缴费基数',
    `ratio_personal`  DECIMAL(5,2)  DEFAULT NULL COMMENT '个人缴存比例 (%)',
    `ratio_company`   DECIMAL(5,2)  DEFAULT NULL COMMENT '公司缴存比例 (%)',
    `amount_personal` DECIMAL(10,2) DEFAULT NULL COMMENT '个人缴存金额',
    `amount_company`  DECIMAL(10,2) DEFAULT NULL COMMENT '公司缴存金额',
    `month`           VARCHAR(7)    DEFAULT NULL COMMENT '所属月份',
    `rpa_receipt_uri` VARCHAR(500)  DEFAULT NULL COMMENT 'RPA 操作回执截图',
    `paper_receipt_uri` VARCHAR(500) DEFAULT NULL COMMENT '纸质回执扫描件',
    `ocr_result`      JSON          DEFAULT NULL COMMENT '纸质回执 OCR 结果',
    `anomaly_flag`    VARCHAR(50)   DEFAULT NULL COMMENT '异常标记',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '已完成' COMMENT '状态: 处理中/已完成/异常/待人工',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`record_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_month` (`month`),
    KEY `idx_type` (`operation_type`),
    CONSTRAINT `fk_hf_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公积金记录表';

-- ============================================================
-- 11. 离职管理模块
-- ============================================================

CREATE TABLE `resignation` (
    `resign_id`       VARCHAR(20)   NOT NULL COMMENT '离职记录 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '员工工号',
    `reason`          TEXT          DEFAULT NULL COMMENT '离职原因',
    `handwritten_uri` VARCHAR(500)  DEFAULT NULL COMMENT '手写离职申请扫描件',
    `apply_date`      DATE          NOT NULL COMMENT '申请日期',
    `last_work_date`  DATE          DEFAULT NULL COMMENT '最后工作日',
    `handover_list`   JSON          DEFAULT NULL COMMENT '离职交接清单 (JSON)',
    `handover_status` JSON          DEFAULT NULL COMMENT '各部门确认记录 (JSON)',
    `certificate_uri` VARCHAR(500)  DEFAULT NULL COMMENT '离职证明路径',
    `approved_by_hr`  VARCHAR(20)   DEFAULT NULL COMMENT 'HR 审批人',
    `approved_by_mgr` VARCHAR(20)   DEFAULT NULL COMMENT '主管审批人',
    `approved_at`     DATETIME      DEFAULT NULL COMMENT '审批时间',
    `status`          VARCHAR(20)   NOT NULL DEFAULT '申请中' COMMENT '状态: 申请中/审批中/交接中/已完成',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`resign_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_resign_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='离职记录表';

-- ============================================================
-- 12. 人事证明模块
-- ============================================================

CREATE TABLE `proof_request` (
    `request_id`      VARCHAR(20)   NOT NULL COMMENT '申请 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '申请人工号',
    `proof_type`      VARCHAR(50)   NOT NULL COMMENT '类型: 在职证明/收入证明/离职证明',
    `data_snapshot`   JSON          DEFAULT NULL COMMENT '证明数据快照',
    `file_uri`        VARCHAR(500)  DEFAULT NULL COMMENT '生成证明文件路径',
    `review_status`   VARCHAR(20)   NOT NULL DEFAULT '待审核' COMMENT '状态: 待审核/已审核/已签发/已拒绝',
    `reviewed_by`     VARCHAR(20)   DEFAULT NULL COMMENT '审核人工号',
    `reviewed_at`     DATETIME      DEFAULT NULL COMMENT '审核时间',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`request_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_status` (`review_status`),
    CONSTRAINT `fk_proof_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人事证明申请表';

-- ============================================================
-- 13. 费用管理模块
-- ============================================================

CREATE TABLE `expense_record` (
    `expense_id`      VARCHAR(20)   NOT NULL COMMENT '费用记录 ID',
    `employee_id`     VARCHAR(20)   NOT NULL COMMENT '申报人工号',
    `merchant_name`   VARCHAR(200)  DEFAULT NULL COMMENT '商户名称',
    `expense_date`    DATE          DEFAULT NULL COMMENT '消费日期',
    `amount`          DECIMAL(10,2) NOT NULL COMMENT '金额',
    `category`        VARCHAR(50)   DEFAULT NULL COMMENT '费用类别',
    `receipt_uri`     VARCHAR(500)  NOT NULL COMMENT '票据影像路径',
    `ocr_result`      JSON          DEFAULT NULL COMMENT '票据 OCR 结果',
    `auth_check`      VARCHAR(20)   DEFAULT NULL COMMENT '发票真伪查验结果',
    `approval_status` VARCHAR(20)   NOT NULL DEFAULT '待审核' COMMENT '状态: 待审核/已通过/已拒绝',
    `reviewed_by`     VARCHAR(20)   DEFAULT NULL COMMENT '审核人',
    `reviewed_at`     DATETIME      DEFAULT NULL COMMENT '审核时间',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`expense_id`),
    KEY `idx_employee` (`employee_id`),
    KEY `idx_date` (`expense_date`),
    KEY `idx_status` (`approval_status`),
    CONSTRAINT `fk_expense_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='费用报销记录表';

-- ============================================================
-- 14. 系统管理模块
-- ============================================================

-- 14.1 系统用户表
CREATE TABLE `system_user` (
    `user_id`         VARCHAR(20)   NOT NULL COMMENT '用户 ID',
    `username`        VARCHAR(50)   NOT NULL COMMENT '用户名',
    `password_hash`   VARCHAR(200)  NOT NULL COMMENT '密码哈希 (bcrypt)',
    `employee_id`     VARCHAR(20)   DEFAULT NULL COMMENT '关联工号 (NULL=系统账号)',
    `roles`           JSON          NOT NULL COMMENT '角色列表 (JSON 数组)',
    `mfa_enabled`     TINYINT       NOT NULL DEFAULT 0 COMMENT 'MFA 是否启用',
    `mfa_secret`      VARCHAR(200)  DEFAULT NULL COMMENT 'MFA 密钥 (加密)',
    `last_login_at`   DATETIME      DEFAULT NULL COMMENT '最后登录时间',
    `last_login_ip`   VARCHAR(45)   DEFAULT NULL COMMENT '最后登录 IP',
    `status`          TINYINT       NOT NULL DEFAULT 1 COMMENT '状态: 1=启用 0=禁用',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`),
    UNIQUE KEY `uk_username` (`username`),
    KEY `idx_employee` (`employee_id`),
    CONSTRAINT `fk_sysuser_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- 14.2 审计日志表
CREATE TABLE `audit_log` (
    `log_id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '日志 ID',
    `operation_time`  DATETIME      NOT NULL COMMENT '操作时间',
    `operator_id`     VARCHAR(20)   NOT NULL COMMENT '操作人账号',
    `operator_name`   VARCHAR(50)   NOT NULL COMMENT '操作人姓名',
    `operator_ip`     VARCHAR(45)   NOT NULL COMMENT '操作者 IP',
    `operation_type`  VARCHAR(50)   NOT NULL COMMENT '操作类型',
    `operation_module` VARCHAR(50)  NOT NULL COMMENT '操作模块',
    `target_id`       VARCHAR(50)   DEFAULT NULL COMMENT '对象 ID',
    `target_name`     VARCHAR(100)  DEFAULT NULL COMMENT '对象名称',
    `before_snapshot` JSON          DEFAULT NULL COMMENT '变更前快照',
    `after_snapshot`  JSON          DEFAULT NULL COMMENT '变更后快照',
    `result`          VARCHAR(20)   NOT NULL COMMENT '结果: 成功/失败',
    `duration_ms`     INT           NOT NULL COMMENT '耗时 (毫秒)',
    `trace_id`        VARCHAR(64)   DEFAULT NULL COMMENT '链路追踪 ID',
    PRIMARY KEY (`log_id`),
    KEY `idx_time` (`operation_time`),
    KEY `idx_operator` (`operator_id`),
    KEY `idx_module` (`operation_module`),
    KEY `idx_target` (`target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作审计日志表 (不可删除, 保留>=10年)';

-- 14.3 Agent 执行日志表
CREATE TABLE `agent_run_log` (
    `run_id`          VARCHAR(32)   NOT NULL COMMENT '执行流水号 (UUID)',
    `agent_name`      VARCHAR(100)  NOT NULL COMMENT 'Agent 名称',
    `parent_flow_id`  VARCHAR(32)   DEFAULT NULL COMMENT '所属业务流程 ID',
    `inputs_summary`  JSON          DEFAULT NULL COMMENT '输入概要',
    `reasoning_trace` TEXT          DEFAULT NULL COMMENT '推理过程摘要',
    `outputs_summary` JSON          DEFAULT NULL COMMENT '输出概要',
    `model_version`   VARCHAR(50)   DEFAULT NULL COMMENT '使用的模型版本',
    `status`          VARCHAR(20)   NOT NULL COMMENT '状态: 成功/失败/挂起',
    `duration_ms`     BIGINT        DEFAULT NULL COMMENT '耗时 (毫秒)',
    `error_detail`    TEXT          DEFAULT NULL COMMENT '错误堆栈',
    `retry_count`     INT           NOT NULL DEFAULT 0 COMMENT '重试次数',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`run_id`),
    KEY `idx_agent` (`agent_name`),
    KEY `idx_flow` (`parent_flow_id`),
    KEY `idx_status` (`status`),
    KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent 执行日志表';

-- 14.4 薪资规则配置表 (个税税率)
CREATE TABLE `tax_bracket` (
    `level`           TINYINT       NOT NULL COMMENT '级数 (1-7)',
    `min_amount`      DECIMAL(12,2) NOT NULL COMMENT '全年应纳税所得额下限',
    `max_amount`      DECIMAL(12,2) NOT NULL COMMENT '全年应纳税所得额上限 (999999999=无上限)',
    `tax_rate`        DECIMAL(5,2)  NOT NULL COMMENT '税率 (%)',
    `quick_deduction` DECIMAL(10,2) NOT NULL COMMENT '速算扣除数',
    `effective_from`  DATE          NOT NULL COMMENT '生效日期',
    PRIMARY KEY (`level`),
    CONSTRAINT `chk_level` CHECK (`level` BETWEEN 1 AND 7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='个税税率级距表';

-- 初始化个税税率数据
INSERT INTO `tax_bracket` (`level`, `min_amount`, `max_amount`, `tax_rate`, `quick_deduction`, `effective_from`) VALUES
(1, 0, 36000, 3, 0, '2026-01-01'),
(2, 36000, 144000, 10, 2520, '2026-01-01'),
(3, 144000, 300000, 20, 16920, '2026-01-01'),
(4, 300000, 420000, 25, 31920, '2026-01-01'),
(5, 420000, 660000, 30, 52920, '2026-01-01'),
(6, 660000, 960000, 35, 85920, '2026-01-01'),
(7, 960000, 999999999, 45, 181920, '2026-01-01');

-- ============================================================
-- 15. 招聘平台渠道配置表
-- ============================================================

CREATE TABLE `recruitment_channel` (
    `channel_id`      VARCHAR(20)   NOT NULL COMMENT '渠道 ID',
    `channel_name`    VARCHAR(50)   NOT NULL COMMENT '渠道名称',
    `api_type`        VARCHAR(20)   NOT NULL COMMENT '接口类型: API/RPA',
    `api_config`      JSON          DEFAULT NULL COMMENT 'API 配置',
    `rpa_config`      JSON          DEFAULT NULL COMMENT 'RPA 配置',
    `crawl_interval`  INT           NOT NULL DEFAULT 15 COMMENT '抓取间隔 (分钟)',
    `status`          TINYINT       NOT NULL DEFAULT 1 COMMENT '状态: 1=启用 0=停用',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`channel_id`),
    CONSTRAINT `chk_api_type` CHECK (`api_type` IN ('API', 'RPA'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='招聘渠道配置表';

-- ============================================================
-- 16. 人才库标签表
-- ============================================================

CREATE TABLE `talent_tag` (
    `tag_id`          VARCHAR(20)   NOT NULL COMMENT '标签 ID',
    `resume_id`       VARCHAR(20)   NOT NULL COMMENT '简历 ID',
    `tag_category`    VARCHAR(50)   NOT NULL COMMENT '标签类别: 行业/技术栈/管理经验/项目经验',
    `tag_value`       VARCHAR(100)  NOT NULL COMMENT '标签值',
    `confidence`      DECIMAL(3,2)  DEFAULT NULL COMMENT '置信度 (0-1)',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`tag_id`),
    KEY `idx_resume` (`resume_id`),
    KEY `idx_category_value` (`tag_category`, `tag_value`),
    CONSTRAINT `fk_tag_resume` FOREIGN KEY (`resume_id`) REFERENCES `resume`(`resume_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人才标签表';

-- ============================================================
-- 视图定义
-- ============================================================

-- 在职员工视图
CREATE OR REPLACE VIEW `v_active_employees` AS
SELECT * FROM `employee`
WHERE `status` IN ('在职', '试用期')
  AND `leave_date` IS NULL;

-- 考勤月度汇总视图
CREATE OR REPLACE VIEW `v_attendance_monthly` AS
SELECT
    ar.employee_id,
    e.name,
    o.dept_name,
    DATE_FORMAT(ar.date, '%Y-%m') AS month,
    COUNT(*) AS work_days,
    SUM(ar.late_count) AS total_late,
    SUM(ar.early_leave_count) AS total_early_leave,
    SUM(ar.absent_days) AS total_absent,
    SUM(ar.overtime_hrs) AS total_overtime,
    SUM(ar.holiday_leave_hrs) AS total_holiday_leave,
    SUM(ar.sick_leave_hrs) AS total_sick_leave
FROM `attendance_record` ar
JOIN `employee` e ON ar.employee_id = e.employee_id
LEFT JOIN `organization` o ON e.dept_id = o.dept_id
GROUP BY ar.employee_id, e.name, o.dept_name, DATE_FORMAT(ar.date, '%Y-%m');

-- 即将到期证书视图
CREATE OR REPLACE VIEW `v_cert_expiring_soon` AS
SELECT
    c.cert_id,
    c.employee_id,
    e.name AS employee_name,
    c.cert_type,
    c.cert_name,
    c.expiry_date,
    DATEDIFF(c.expiry_date, CURDATE()) AS days_remaining
FROM `certificate` c
JOIN `employee` e ON c.employee_id = e.employee_id
WHERE c.status = '有效'
  AND c.expiry_date IS NOT NULL
  AND DATEDIFF(c.expiry_date, CURDATE()) <= 60
ORDER BY c.expiry_date ASC;

-- ============================================================
-- 存储过程: 薪资核算触发器
-- ============================================================

DELIMITER //

CREATE PROCEDURE `sp_trigger_payroll`(
    IN p_month VARCHAR(7)
)
BEGIN
    -- 此存储过程仅作为薪资核算的数据库层辅助
    -- 实际计算逻辑在 PayrollAgent 中执行
    -- 此处仅记录核算任务已触发
    
    INSERT INTO `agent_run_log` (
        `run_id`, `agent_name`, `parent_flow_id`,
        `inputs_summary`, `status`, `created_at`
    ) VALUES (
        UUID(), 'PayrollAgent', UUID(),
        JSON_OBJECT('month', p_month),
        '成功',
        NOW()
    );
END //

DELIMITER ;

-- ============================================================
-- 索引优化建议
-- ============================================================

-- 以下索引根据实际查询模式可在生产环境按需添加:
-- CREATE INDEX idx_payroll_employee_month ON payroll(employee_id, month);
-- CREATE INDEX idx_audit_log_module_time ON audit_log(operation_module, operation_time);
-- CREATE INDEX idx_agent_log_agent_time ON agent_run_log(agent_name, created_at);
-- CREATE INDEX idx_resume_dedup ON resume(id_number, phone, applied_position);
```

---

## 3. 数据字典汇总

| 表名 | 说明 | 主键 | 预计数据量 | 保留策略 |
|------|------|------|-----------|---------|
| organization | 组织架构/部门 | dept_id | < 1000 | 永久 |
| position | 岗位管理 | position_id | < 500 | 永久 |
| employee | 员工档案 | employee_id | < 10000 | 在职永久; 离职≥5年 |
| resume | 简历数据 | resume_id | ≥ 100000 | 3年在线+2年离线 |
| job_post | 招聘信息发布 | post_id | < 5000 | 永久 |
| exam_paper | 试卷 | paper_id | < 10000 | 永久 |
| exam_result | 考试成绩 | result_id | < 50000 | 永久 |
| onboarding_doc | 入职资料 | doc_id | < 200000 | 永久 |
| e_signature | 电子签章 | sig_id | < 100000 | 永久 |
| face_library | 人脸库 | face_id | < 10000 | 永久 |
| shift | 班次定义 | shift_id | < 50 | 永久 |
| shift_schedule | 排班表 | schedule_id | < 1000000 | 2年在线+2年离线 |
| attendance_record | 考勤记录 | record_id | < 5000000 | 2年在线+2年离线 |
| salary_profile | 薪资主数据 | profile_id | < 10000 | 永久 |
| salary_rule | 薪资规则 | rule_id | < 500 | 永久 |
| payroll | 月度薪资 | payroll_id | < 200000 | ≥15年 |
| payslip_delivery | 工资条发送 | delivery_id | < 200000 | ≥15年 |
| training_plan | 培训计划 | plan_id | < 5000 | 永久 |
| training_record | 培训记录 | record_id | < 500000 | 3年在线+2年离线 |
| training_video | 培训视频 | video_id | < 1000 | 永久 |
| certificate | 证书台账 | cert_id | < 50000 | 永久 |
| performance_review | 绩效考核 | pr_id | < 200000 | 2年在线+2年离线 |
| injury_case | 工伤档案 | case_id | < 1000 | 永久+≥15年离线 |
| housing_fund | 公积金记录 | record_id | < 200000 | 永久 |
| resignation | 离职记录 | resign_id | < 20000 | 永久 |
| proof_request | 人事证明申请 | request_id | < 50000 | 永久 |
| expense_record | 费用报销 | expense_id | < 100000 | 永久 |
| system_user | 系统用户 | user_id | < 5000 | 永久 |
| audit_log | 审计日志 | log_id (自增) | < 10000000 | ≥10年 |
| agent_run_log | Agent 执行日志 | run_id | < 50000000 | 6个月在线+≥1年离线 |
| tax_bracket | 个税税率级距 | level | 7 | 永久 |
| recruitment_channel | 招聘渠道 | channel_id | < 20 | 永久 |
| talent_tag | 人才标签 | tag_id | < 1000000 | 随简历生命周期 |

---

## 4. 分表与归档策略

### 4.1 建议分表

| 表 | 分表策略 | 触发条件 |
|----|---------|---------|
| attendance_record | 按月分表 | 单表超过 500 万行 |
| audit_log | 按月分表 | 单表超过 1000 万行 |
| agent_run_log | 按月分表 | 单表超过 5000 万行 |

### 4.2 归档脚本 (示例)

```sql
-- 考勤数据归档 (每年 1 月 1 日执行)
INSERT INTO `attendance_record_archive`
SELECT * FROM `attendance_record`
WHERE `date` < DATE_SUB(CURDATE(), INTERVAL 2 YEAR);

DELETE FROM `attendance_record`
WHERE `date` < DATE_SUB(CURDATE(), INTERVAL 2 YEAR);
```

---

*文档结束*
