-- ============================================================
-- GBM AI Agent HR 数据库初始化脚本
-- 基于 DATABASE_V19 设计文档
-- 创建 4 个独立 schema 并初始化基础数据
-- ============================================================

-- 创建 4 个独立 schema
CREATE DATABASE IF NOT EXISTS hr_user
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS hr_recruit
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS hr_payroll
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS hr_auto
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- ============================================================
-- hr_user schema - 用户中心表
-- ============================================================

USE hr_user;

-- 部门表
CREATE TABLE IF NOT EXISTS department (
    dept_id VARCHAR(20) NOT NULL COMMENT '部门编号',
    dept_name VARCHAR(100) NOT NULL COMMENT '部门名称',
    parent_id VARCHAR(20) DEFAULT NULL COMMENT '父部门编号',
    sort_order INT DEFAULT 0 COMMENT '排序',
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/INACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (dept_id),
    KEY idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';

-- 岗位表
CREATE TABLE IF NOT EXISTS job_position (
    position_id VARCHAR(20) NOT NULL COMMENT '岗位编号',
    position_name VARCHAR(100) NOT NULL COMMENT '岗位名称',
    dept_id VARCHAR(20) DEFAULT NULL COMMENT '所属部门',
    level VARCHAR(20) DEFAULT NULL COMMENT '职级',
    head_count INT DEFAULT 0 COMMENT '编制人数',
    description TEXT COMMENT '岗位描述',
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (position_id),
    KEY idx_dept_id (dept_id),
    CONSTRAINT fk_position_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位表';

-- 系统用户表
CREATE TABLE IF NOT EXISTS sys_user (
    user_id VARCHAR(20) NOT NULL COMMENT '用户编号',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    password_hash VARCHAR(200) NOT NULL COMMENT '密码哈希',
    real_name VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE/LOCKED/DISABLED',
    last_login_at TIMESTAMP NULL DEFAULT NULL COMMENT '最后登录时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- 角色表
CREATE TABLE IF NOT EXISTS sys_role (
    role_id VARCHAR(20) NOT NULL COMMENT '角色编号',
    role_name VARCHAR(50) NOT NULL COMMENT '角色名称',
    role_type ENUM('系统', '管理', '业务', '普通员工') NOT NULL COMMENT '角色类型',
    description VARCHAR(200) DEFAULT NULL COMMENT '描述',
    status VARCHAR(20) DEFAULT 'ACTIVE' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 权限表
CREATE TABLE IF NOT EXISTS sys_permission (
    permission_id VARCHAR(20) NOT NULL COMMENT '权限编号',
    permission_name VARCHAR(100) NOT NULL COMMENT '权限名称',
    resource_type ENUM('菜单', '按钮', '接口') NOT NULL COMMENT '资源类型',
    resource_path VARCHAR(200) DEFAULT NULL COMMENT '资源路径',
    action VARCHAR(50) DEFAULT NULL COMMENT '操作动作',
    parent_id VARCHAR(20) DEFAULT NULL COMMENT '父权限',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限表';

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS sys_user_role (
    user_id VARCHAR(20) NOT NULL,
    role_id VARCHAR(20) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES sys_user(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS sys_role_permission (
    role_id VARCHAR(20) NOT NULL,
    permission_id VARCHAR(20) NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_rp_perm FOREIGN KEY (permission_id) REFERENCES sys_permission(permission_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_log (
    log_id VARCHAR(32) NOT NULL COMMENT '日志ID',
    operation_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    operator_id VARCHAR(20) NOT NULL COMMENT '操作人',
    operator_name VARCHAR(50) NOT NULL COMMENT '操作人姓名',
    operator_ip VARCHAR(45) NOT NULL COMMENT '操作者IP',
    operation_type ENUM('新增', '修改', '删除', '查看', '导出', '登录', '登出', 'Auto-Agent调用') NOT NULL COMMENT '操作类型',
    operation_module VARCHAR(50) NOT NULL COMMENT '操作模块',
    operation_object VARCHAR(200) DEFAULT NULL COMMENT '操作对象',
    before_snapshot JSON DEFAULT NULL COMMENT '变更前快照',
    after_snapshot JSON DEFAULT NULL COMMENT '变更后快照',
    result VARCHAR(20) NOT NULL COMMENT '结果: 成功/失败',
    duration_ms BIGINT DEFAULT NULL COMMENT '耗时(ms)',
    PRIMARY KEY (log_id),
    KEY idx_operation_time (operation_time),
    KEY idx_operator_id (operator_id),
    KEY idx_operation_module (operation_module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';

-- 初始化基础数据
INSERT INTO department (dept_id, dept_name, parent_id, sort_order) VALUES
('DEPT001', '总经办', NULL, 1),
('DEPT002', '人力资源部', 'DEPT001', 2),
('DEPT003', '财务部', 'DEPT001', 3),
('DEPT004', '信息技术部', 'DEPT001', 4),
('DEPT005', '生产管理部', 'DEPT001', 5);

INSERT INTO sys_role (role_id, role_name, role_type, description) VALUES
('ROLE001', '超级管理员', '系统', '系统最高权限'),
('ROLE002', '系统管理员', '系统', '系统配置和运维管理'),
('ROLE003', '人事主管', '管理', 'HR 流程审核与管理'),
('ROLE004', '人事专员', '业务', 'HR 日常业务操作'),
('ROLE005', '部门主管', '管理', '本部门业务审核'),
('ROLE006', '普通员工', '普通员工', '普通在职员工');

-- 初始化管理员账户 (密码: Admin@123, BCrypt 哈希)
INSERT INTO sys_user (user_id, username, password_hash, real_name, email, status) VALUES
('USER001', 'admin', '$2a$10$N.zmdr9k6uOCQb37SNo.KuM06RRThkZJE00LJ0VvKvBOYBk6V5xBS', '系统管理员', 'admin@gbm.com', 'ACTIVE');

-- 管理员关联超级管理员角色
INSERT INTO sys_user_role (user_id, role_id) VALUES ('USER001', 'ROLE001');

-- ============================================================
-- hr_recruit schema - 招聘入职表
-- ============================================================

USE hr_recruit;

-- 招聘岗位表
CREATE TABLE IF NOT EXISTS recruitment_job (
    job_id VARCHAR(20) NOT NULL COMMENT '招聘岗位编号',
    position_id VARCHAR(20) NOT NULL COMMENT '关联岗位',
    job_name VARCHAR(100) NOT NULL COMMENT '招聘职位名称',
    head_count INT DEFAULT 1 COMMENT '招聘人数',
    requirements TEXT COMMENT '任职要求',
    status ENUM('Draft', 'Published', 'Closed', 'Cancelled') DEFAULT 'Draft' COMMENT '状态',
    publish_at TIMESTAMP NULL DEFAULT NULL COMMENT '发布时间',
    close_at TIMESTAMP NULL DEFAULT NULL COMMENT '截止时间',
    created_by VARCHAR(20) DEFAULT NULL COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='招聘岗位表';

-- 简历表
CREATE TABLE IF NOT EXISTS resume (
    resume_id VARCHAR(20) NOT NULL COMMENT '简历ID',
    candidate_name VARCHAR(50) NOT NULL COMMENT '姓名',
    id_number VARCHAR(18) DEFAULT NULL COMMENT '身份证号(加密)',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    source_platform VARCHAR(50) NOT NULL COMMENT '来源平台',
    education VARCHAR(50) DEFAULT NULL COMMENT '最高学历',
    years_of_exp INT DEFAULT NULL COMMENT '从业年限',
    skill_tags TEXT DEFAULT NULL COMMENT '技能标签',
    age INT DEFAULT NULL COMMENT '年龄',
    certs TEXT DEFAULT NULL COMMENT '持证情况',
    applied_position VARCHAR(100) NOT NULL COMMENT '应聘岗位',
    total_score DECIMAL(5,2) DEFAULT NULL COMMENT '综合匹配分',
    classify_result VARCHAR(20) DEFAULT NULL COMMENT '分拣结果: 高潜/候审/淘汰',
    file_uri VARCHAR(500) DEFAULT NULL COMMENT '简历文件链接',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (resume_id),
    KEY idx_applied_position (applied_position),
    KEY idx_classify_result (classify_result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';

-- 考试试卷表
CREATE TABLE IF NOT EXISTS exam_paper (
    paper_id VARCHAR(20) NOT NULL COMMENT '试卷ID',
    job_id VARCHAR(20) DEFAULT NULL COMMENT '关联招聘',
    paper_name VARCHAR(200) NOT NULL COMMENT '试卷名称',
    total_questions INT DEFAULT 40 COMMENT '总题数',
    total_score DECIMAL(5,2) DEFAULT 100 COMMENT '总分',
    pass_score DECIMAL(5,2) DEFAULT 60 COMMENT '及格分',
    status ENUM('Draft', 'Published', 'Closed') DEFAULT 'Draft' COMMENT '状态',
    valid_from TIMESTAMP NULL DEFAULT NULL COMMENT '有效开始',
    valid_to TIMESTAMP NULL DEFAULT NULL COMMENT '有效截止',
    created_by VARCHAR(20) DEFAULT NULL COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (paper_id),
    KEY idx_job_id (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试试卷表';

-- 入职流程表
CREATE TABLE IF NOT EXISTS onboarding_process (
    process_id VARCHAR(20) NOT NULL COMMENT '入职流程ID',
    employee_id VARCHAR(20) DEFAULT NULL COMMENT '员工编号',
    resume_id VARCHAR(20) DEFAULT NULL COMMENT '关联简历',
    expected_start_date DATE NOT NULL COMMENT '预计入职日期',
    position_id VARCHAR(20) NOT NULL COMMENT '入职岗位',
    status ENUM('Pending', 'In Progress', 'Completed', 'Cancelled') DEFAULT 'Pending' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (process_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='入职流程表';

-- ============================================================
-- hr_payroll schema - 薪资考勤表
-- ============================================================

USE hr_payroll;

-- 考勤记录表
CREATE TABLE IF NOT EXISTS attendance_record (
    record_id VARCHAR(20) NOT NULL COMMENT '记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    date DATE NOT NULL COMMENT '日期',
    clock_in TIME DEFAULT NULL COMMENT '上班打卡',
    clock_out TIME DEFAULT NULL COMMENT '下班打卡',
    late_count INT DEFAULT 0 COMMENT '迟到次数',
    early_leave_count INT DEFAULT 0 COMMENT '早退次数',
    absent_days INT DEFAULT 0 COMMENT '旷工天数',
    holiday_leave_hrs DECIMAL(5,2) DEFAULT 0 COMMENT '事假小时数',
    sick_leave_hrs DECIMAL(5,2) DEFAULT 0 COMMENT '病假小时数',
    overtime_hrs DECIMAL(5,2) DEFAULT 0 COMMENT '加班时长',
    flag VARCHAR(20) DEFAULT NULL COMMENT '异常标志',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    UNIQUE KEY uk_emp_date (employee_id, date),
    KEY idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考勤记录表';

-- 薪资记录表
CREATE TABLE IF NOT EXISTS payroll (
    payroll_id VARCHAR(20) NOT NULL COMMENT '薪资记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    month VARCHAR(7) NOT NULL COMMENT '月份 YYYY-MM',
    base_pay DECIMAL(10,2) NOT NULL COMMENT '基本工资',
    overtime_pay DECIMAL(10,2) DEFAULT 0 COMMENT '加班费',
    attendance_deduct DECIMAL(10,2) DEFAULT 0 COMMENT '考勤扣款',
    allowances_total DECIMAL(10,2) DEFAULT 0 COMMENT '补贴合计',
    deduction_total DECIMAL(10,2) DEFAULT 0 COMMENT '扣款合计',
    ss_personal DECIMAL(10,2) DEFAULT 0 COMMENT '社保个人缴纳',
    gf_personal DECIMAL(10,2) DEFAULT 0 COMMENT '公积金个人缴纳',
    income_tax DECIMAL(10,2) DEFAULT 0 COMMENT '个税',
    net_pay DECIMAL(10,2) NOT NULL COMMENT '实发工资',
    status VARCHAR(20) NOT NULL DEFAULT '已核算' COMMENT '状态',
    reviewed_by VARCHAR(20) DEFAULT NULL COMMENT '审核人',
    reviewed_at TIMESTAMP NULL DEFAULT NULL COMMENT '审核时间',
    version INT DEFAULT 0 COMMENT '乐观锁版本',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (payroll_id),
    UNIQUE KEY uk_emp_month (employee_id, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资记录表';

-- 绩效考核表
CREATE TABLE IF NOT EXISTS performance_review (
    pr_id VARCHAR(20) NOT NULL COMMENT '考核记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    cycle VARCHAR(7) NOT NULL COMMENT '考核周期',
    self_score DECIMAL(5,2) DEFAULT NULL COMMENT '自评分',
    mgr_score DECIMAL(5,2) DEFAULT NULL COMMENT '上级评分',
    rating VARCHAR(2) DEFAULT NULL COMMENT '等级',
    submit_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    approve_at TIMESTAMP NULL DEFAULT NULL COMMENT '审批时间',
    version INT DEFAULT 0 COMMENT '乐观锁版本',
    PRIMARY KEY (pr_id),
    UNIQUE KEY uk_emp_cycle (employee_id, cycle)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='绩效考核表';

-- ============================================================
-- hr_auto schema - 自动化任务表
-- ============================================================

USE hr_auto;

-- Agent 执行日志表
CREATE TABLE IF NOT EXISTS agent_run_log (
    run_id VARCHAR(32) NOT NULL COMMENT '执行流水号',
    agent_name VARCHAR(100) NOT NULL COMMENT 'Agent名称',
    parent_flow_id VARCHAR(32) DEFAULT NULL COMMENT '所属业务流程ID',
    inputs_summary JSON DEFAULT NULL COMMENT '输入概要',
    reasoning_trace TEXT DEFAULT NULL COMMENT '推理过程摘要',
    outputs_summary JSON DEFAULT NULL COMMENT '输出概要',
    status VARCHAR(20) NOT NULL COMMENT '状态: 成功/失败/挂起',
    duration_ms BIGINT DEFAULT NULL COMMENT '耗时(ms)',
    error_detail TEXT DEFAULT NULL COMMENT '错误堆栈',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id),
    KEY idx_agent_name (agent_name),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent执行日志表';

-- RPA 任务表
CREATE TABLE IF NOT EXISTS rpa_task (
    task_id VARCHAR(20) NOT NULL COMMENT '任务ID',
    task_type ENUM('工伤申报', '公积金参保', '公积金补缴', '社保申报', '其他') NOT NULL COMMENT '任务类型',
    employee_id VARCHAR(20) DEFAULT NULL COMMENT '关联员工',
    target_url VARCHAR(500) NOT NULL COMMENT '目标URL',
    form_data JSON DEFAULT NULL COMMENT '表单数据',
    status ENUM('pending', 'running', 'success', 'failed', 'retrying') DEFAULT 'pending' COMMENT '状态',
    process_id VARCHAR(64) DEFAULT NULL COMMENT '异步任务标识',
    kafka_message_id VARCHAR(128) DEFAULT NULL COMMENT 'Kafka消息ID',
    receipt_url VARCHAR(500) DEFAULT NULL COMMENT '操作回执URL',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id),
    KEY idx_status (status),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RPA任务表';

-- 工伤档案表
CREATE TABLE IF NOT EXISTS injury_case (
    case_id VARCHAR(20) NOT NULL COMMENT '案件编号',
    employee_id VARCHAR(20) NOT NULL COMMENT '受伤员工',
    accident_date DATE NOT NULL COMMENT '事故发生日',
    description TEXT NOT NULL COMMENT '事故描述',
    docs JSON DEFAULT NULL COMMENT '上传的材料清单和路径',
    filing_no VARCHAR(50) DEFAULT NULL COMMENT '备案受理号',
    claim_amount DECIMAL(10,2) DEFAULT NULL COMMENT '理赔金额',
    status VARCHAR(20) NOT NULL DEFAULT '立案中' COMMENT '状态',
    rpa_receipts JSON DEFAULT NULL COMMENT 'RPA操作截图凭证',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工伤档案表';

-- 输出完成信息
SELECT 'GBM AI Agent HR 数据库初始化完成!' AS message;
SELECT '已创建 4 个 schema: hr_user, hr_recruit, hr_payroll, hr_auto' AS info;
SELECT '已初始化部门、角色、管理员基础数据' AS info;
