-- hr_payroll schema - Payroll, Attendance & Performance tables
USE hr_payroll;

-- 考勤记录表
CREATE TABLE IF NOT EXISTS attendance_record (
    record_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    clock_in TIME,
    clock_out TIME,
    shift_id VARCHAR(20),
    late_count INT DEFAULT 0,
    early_leave_count INT DEFAULT 0,
    absent_days INT DEFAULT 0,
    holiday_leave_hrs DECIMAL(5,2) DEFAULT 0,
    sick_leave_hrs DECIMAL(5,2) DEFAULT 0,
    overtime_hrs DECIMAL(5,2) DEFAULT 0,
    flag VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_emp_date (employee_id, date),
    INDEX idx_date (date),
    INDEX idx_flag (flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 班次配置表
CREATE TABLE IF NOT EXISTS shift_config (
    shift_id VARCHAR(20) PRIMARY KEY,
    shift_name VARCHAR(50) NOT NULL,
    shift_type VARCHAR(20) DEFAULT '标准',
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    break_minutes INT DEFAULT 60,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 请假申请表
CREATE TABLE IF NOT EXISTS leave_application (
    application_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    leave_type VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    hours DECIMAL(5,2),
    reason TEXT,
    status VARCHAR(20) DEFAULT '待审批',
    approved_by VARCHAR(20),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 加班申请表
CREATE TABLE IF NOT EXISTS overtime_application (
    application_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    hours DECIMAL(5,2) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT '待审批',
    approved_by VARCHAR(20),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 薪资记录表
CREATE TABLE IF NOT EXISTS payroll (
    payroll_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    month VARCHAR(7) NOT NULL,
    base_pay DECIMAL(10,2) NOT NULL,
    overtime_pay DECIMAL(10,2) DEFAULT 0,
    attendance_deduct DECIMAL(10,2) DEFAULT 0,
    allowances_total DECIMAL(10,2) DEFAULT 0,
    deduction_total DECIMAL(10,2) DEFAULT 0,
    ss_personal DECIMAL(10,2) DEFAULT 0,
    gf_personal DECIMAL(10,2) DEFAULT 0,
    income_tax DECIMAL(10,2) DEFAULT 0,
    net_pay DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT '已核算',
    reviewed_by VARCHAR(20),
    reviewed_at TIMESTAMP,
    version INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_emp_month (employee_id, month),
    INDEX idx_month (month),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 薪资规则表
CREATE TABLE IF NOT EXISTS salary_rule (
    rule_id VARCHAR(20) PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    expression TEXT NOT NULL,
    effective_date DATE NOT NULL,
    expire_date DATE,
    version INT DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (rule_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 薪资变更历史表
CREATE TABLE IF NOT EXISTS salary_change_history (
    history_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    field_type ENUM('薪资', '文本', 'JSON') NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_reason VARCHAR(200),
    changed_by VARCHAR(20),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 绩效考核表
CREATE TABLE IF NOT EXISTS performance_review (
    pr_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    cycle VARCHAR(7) NOT NULL,
    self_score DECIMAL(5,2),
    mgr_score DECIMAL(5,2),
    rating VARCHAR(2),
    comments TEXT,
    submit_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approve_at TIMESTAMP,
    version INT DEFAULT 0,
    UNIQUE KEY uk_emp_cycle (employee_id, cycle)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 工资条发放记录表
CREATE TABLE IF NOT EXISTS payslip (
    payslip_id VARCHAR(20) PRIMARY KEY,
    payroll_id VARCHAR(20) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    status VARCHAR(20) DEFAULT '已发送',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payroll_id) REFERENCES payroll(payroll_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
