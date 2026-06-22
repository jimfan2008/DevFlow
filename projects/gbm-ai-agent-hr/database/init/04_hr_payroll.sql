-- ============================================
-- GBM AI Agent HR - hr_payroll Schema 表结构
-- ============================================
-- 域服务: payroll-domain (端口 8083)
-- 包含: 薪资核算、考勤管理、请假管理、绩效管理

USE hr_payroll;

-- 1. 考勤记录表
CREATE TABLE IF NOT EXISTS attendance_record (
    record_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    clock_in TIME NULL,
    clock_out TIME NULL,
    shift_id VARCHAR(20) NULL,
    late_count INT NOT NULL DEFAULT 0,
    early_leave_count INT NOT NULL DEFAULT 0,
    absent_days INT NOT NULL DEFAULT 0,
    holiday_leave_hrs DECIMAL(5,2) NOT NULL DEFAULT 0,
    sick_leave_hrs DECIMAL(5,2) NOT NULL DEFAULT 0,
    overtime_hrs DECIMAL(5,2) NOT NULL DEFAULT 0,
    flag VARCHAR(20) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_employee_date (employee_id, date),
    INDEX idx_date (date),
    INDEX idx_flag (flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 班次配置表
CREATE TABLE IF NOT EXISTS shift_config (
    shift_id VARCHAR(20) PRIMARY KEY,
    shift_name VARCHAR(50) NOT NULL,
    shift_type ENUM('早班', '中班', '晚班', '常白班') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    break_hours DECIMAL(4,2) NOT NULL DEFAULT 1.0,
    dept_id VARCHAR(20) NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dept (dept_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 请假申请表
CREATE TABLE IF NOT EXISTS leave_application (
    application_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    leave_type ENUM('事假', '病假', '年假', '婚假', '产假', '丧假', '工伤假', '其他') NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    total_hours DECIMAL(5,2) NOT NULL,
    reason TEXT,
    attachment_uri VARCHAR(500) NULL,
    status ENUM('待审批', '已批准', '已拒绝', '已撤销') NOT NULL DEFAULT '待审批',
    approved_by VARCHAR(20) NULL,
    approved_at TIMESTAMP NULL,
    reject_reason TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_status (status),
    INDEX idx_date (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 薪资核算表
CREATE TABLE IF NOT EXISTS payroll (
    payroll_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    month VARCHAR(7) NOT NULL,
    base_pay DECIMAL(10,2) NOT NULL,
    overtime_pay DECIMAL(10,2) NOT NULL DEFAULT 0,
    attendance_deduct DECIMAL(10,2) NOT NULL DEFAULT 0,
    allowances_total DECIMAL(10,2) NOT NULL DEFAULT 0,
    deduction_total DECIMAL(10,2) NOT NULL DEFAULT 0,
    ss_personal DECIMAL(10,2) NOT NULL DEFAULT 0,
    gf_personal DECIMAL(10,2) NOT NULL DEFAULT 0,
    income_tax DECIMAL(10,2) NOT NULL DEFAULT 0,
    net_pay DECIMAL(10,2) NOT NULL,
    status ENUM('已核算', '已审核', '已发放') NOT NULL DEFAULT '已核算',
    reviewed_by VARCHAR(20) NULL,
    reviewed_at TIMESTAMP NULL,
    version INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_employee_month (employee_id, month),
    INDEX idx_month (month),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 薪资规则表
CREATE TABLE IF NOT EXISTS payroll_rule (
    rule_id VARCHAR(20) PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type ENUM('加班系数', '迟到扣款', '补贴定额', '社保比例', '公积金比例', '个税专项扣除') NOT NULL,
    rule_config JSON NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    version INT NOT NULL DEFAULT 1,
    created_by VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (rule_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 薪资变更历史表
CREATE TABLE IF NOT EXISTS salary_change_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    field_type ENUM('薪资', '文本', 'JSON') NOT NULL,
    old_value TEXT NULL,
    new_value TEXT NULL,
    change_reason VARCHAR(200),
    effective_date DATE NOT NULL,
    operated_by VARCHAR(20) NOT NULL,
    operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_date (effective_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 绩效考核表
CREATE TABLE IF NOT EXISTS performance_review (
    pr_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    cycle VARCHAR(7) NOT NULL,
    self_score DECIMAL(5,2) NULL,
    mgr_score DECIMAL(5,2) NULL,
    rating VARCHAR(2) NULL,
    version INT NOT NULL DEFAULT 0,
    submit_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approve_at TIMESTAMP NULL,
    reviewer_id VARCHAR(20) NULL,
    review_comments TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_employee_cycle (employee_id, cycle),
    INDEX idx_cycle (cycle),
    INDEX idx_rating (rating)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 工资条发放记录表
CREATE TABLE IF NOT EXISTS payslip_delivery (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    payroll_id VARCHAR(20) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    delivery_method ENUM('短信', '邮件', 'APP推送') NOT NULL,
    delivery_status ENUM('待发送', '已发送', '已读取', '发送失败') NOT NULL DEFAULT '待发送',
    sent_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,
    retry_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_payroll (payroll_id),
    INDEX idx_status (delivery_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'hr_payroll schema tables created successfully!' AS status;
