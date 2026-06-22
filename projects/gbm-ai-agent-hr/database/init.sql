-- GBM AI Agent HR Database Initialization Script V1
-- 基于 SRS V15 第 6 节数据需求 + DATABASE_V19 设计文档
-- 执行: mysql -h localhost -u root -p < database/init.sql

-- 创建数据库
CREATE DATABASE IF NOT EXISTS gbm_hr_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE gbm_hr_db;

-- 创建用户
CREATE USER IF NOT EXISTS 'hr_admin'@'%' IDENTIFIED BY 'hr_password';
GRANT ALL PRIVILEGES ON gbm_hr_db.* TO 'hr_admin'@'%';
FLUSH PRIVILEGES;

-- ============================================
-- 1. 用户与认证
-- ============================================
CREATE TABLE user (
    user_id VARCHAR(20) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'employee',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    last_login_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 2. 组织架构
-- ============================================
CREATE TABLE department (
    dept_id VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    parent_id VARCHAR(20) NULL,
    manager_id VARCHAR(20) NULL,
    sort_order INT DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES department(dept_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE position (
    position_id VARCHAR(20) PRIMARY KEY,
    position_name VARCHAR(100) NOT NULL,
    dept_id VARCHAR(20),
    level VARCHAR(20),
    headcount INT DEFAULT 1,
    description TEXT,
    requirements JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. 员工档案 (SRS 6.2.1)
-- ============================================
CREATE TABLE employee (
    employee_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    id_number VARCHAR(18) NOT NULL UNIQUE,
    gender CHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    birth_date DATE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100) UNIQUE,
    dept_id VARCHAR(20),
    position_id VARCHAR(20),
    hire_date DATE NOT NULL,
    leave_date DATE NULL,
    status VARCHAR(20) NOT NULL DEFAULT '在职',
    user_id VARCHAR(20) UNIQUE,
    face_feature BLOB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE SET NULL,
    FOREIGN KEY (position_id) REFERENCES position(position_id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. 简历数据 (SRS 6.2.2)
-- ============================================
CREATE TABLE resume (
    resume_id VARCHAR(20) PRIMARY KEY,
    candidate_name VARCHAR(50) NOT NULL,
    id_number VARCHAR(18),
    phone VARCHAR(20),
    source_platform VARCHAR(50) NOT NULL,
    education VARCHAR(50),
    years_of_exp INT,
    skill_tags TEXT,
    age INT,
    certs TEXT,
    applied_position VARCHAR(100) NOT NULL,
    total_score DECIMAL(5,2),
    classify_result VARCHAR(20),
    file_uri VARCHAR(500),
    resume_text TEXT,
    vector_embedding BLOB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 5. 考勤记录 (SRS 6.2.3)
-- ============================================
CREATE TABLE attendance_record (
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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE,
    UNIQUE KEY uk_employee_date (employee_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 6. 薪资数据 (SRS 6.2.4)
-- ============================================
CREATE TABLE payroll (
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
    status VARCHAR(20) NOT NULL DEFAULT '已核算',
    reviewed_by VARCHAR(20),
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE,
    UNIQUE KEY uk_employee_month (employee_id, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 7. 绩效评价 (SRS 6.2.5)
-- ============================================
CREATE TABLE performance_review (
    pr_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    cycle VARCHAR(7) NOT NULL,
    self_score DECIMAL(5,2),
    mgr_score DECIMAL(5,2),
    rating VARCHAR(2),
    comments TEXT,
    submit_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approve_at TIMESTAMP NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE,
    UNIQUE KEY uk_employee_cycle (employee_id, cycle)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 8. 培训记录
-- ============================================
CREATE TABLE training_record (
    training_id VARCHAR(20) PRIMARY KEY,
    training_name VARCHAR(200) NOT NULL,
    training_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    trainer VARCHAR(100),
    material_uri VARCHAR(500),
    video_uri VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'planned',
    created_by VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE training_attendance (
    attendance_id VARCHAR(20) PRIMARY KEY,
    training_id VARCHAR(20) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    check_in_at TIMESTAMP NULL,
    check_out_at TIMESTAMP NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'absent',
    qr_code VARCHAR(100),
    FOREIGN KEY (training_id) REFERENCES training_record(training_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE,
    UNIQUE KEY uk_training_employee (training_id, employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 9. 考试试卷与答卷
-- ============================================
CREATE TABLE exam_paper (
    paper_id VARCHAR(20) PRIMARY KEY,
    paper_name VARCHAR(200) NOT NULL,
    position_type VARCHAR(100),
    total_questions INT DEFAULT 40,
    total_score INT DEFAULT 100,
    pass_score INT DEFAULT 60,
    questions JSON NOT NULL,
    qrcode VARCHAR(100) UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_by VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE exam_answer (
    answer_id VARCHAR(20) PRIMARY KEY,
    paper_id VARCHAR(20) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    responses JSON NOT NULL,
    score DECIMAL(5,2),
    ai_score_a DECIMAL(5,2),
    ai_score_b DECIMAL(5,2),
    ai_diff DECIMAL(5,2),
    need_review BOOLEAN DEFAULT FALSE,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    graded_at TIMESTAMP NULL,
    FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 10. 工伤档案 (SRS 6.2.6)
-- ============================================
CREATE TABLE injury_case (
    case_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    accident_date DATE NOT NULL,
    description TEXT NOT NULL,
    docs JSON,
    filing_no VARCHAR(50),
    claim_amount DECIMAL(10,2),
    status VARCHAR(20) NOT NULL DEFAULT '立案中',
    rpa_receipts JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 11. 公积金记录
-- ============================================
CREATE TABLE housing_fund (
    record_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    account_no VARCHAR(50),
    base_amount DECIMAL(10,2),
    personal_ratio DECIMAL(5,2) DEFAULT 0.12,
    company_ratio DECIMAL(5,2) DEFAULT 0.12,
    personal_amount DECIMAL(10,2),
    company_amount DECIMAL(10,2),
    month VARCHAR(7) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT '待缴',
    rpa_receipt JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 12. Agent 执行日志 (SRS 6.2.7)
-- ============================================
CREATE TABLE agent_run_log (
    run_id VARCHAR(32) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    parent_flow_id VARCHAR(32),
    inputs_summary JSON,
    reasoning_trace TEXT,
    outputs_summary JSON,
    status VARCHAR(20) NOT NULL,
    duration_ms BIGINT,
    error_detail TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 13. 审计日志
-- ============================================
CREATE TABLE audit_log (
    log_id VARCHAR(32) PRIMARY KEY,
    operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    operator_id VARCHAR(20) NOT NULL,
    operator_name VARCHAR(50),
    operator_ip VARCHAR(45),
    operation_type VARCHAR(20) NOT NULL,
    module VARCHAR(50) NOT NULL,
    target_id VARCHAR(50),
    target_name VARCHAR(100),
    before_json JSON,
    after_json JSON,
    result VARCHAR(10) NOT NULL,
    duration_ms INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 14. 人脸档案
-- ============================================
CREATE TABLE face_record (
    record_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL UNIQUE,
    face_image_uri VARCHAR(500),
    face_features BLOB,
    compare_score DECIMAL(5,2),
    quality_score DECIMAL(5,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 15. 证书台账
-- ============================================
CREATE TABLE certificate (
    cert_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    cert_type VARCHAR(50) NOT NULL,
    cert_name VARCHAR(200) NOT NULL,
    cert_no VARCHAR(100),
    issue_date DATE,
    expire_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'valid',
    file_uri VARCHAR(500),
    reminder_days INT[] DEFAULT '[60,30,7,1]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 16. 电子签章
-- ============================================
CREATE TABLE document_sign (
    sign_id VARCHAR(20) PRIMARY KEY,
    document_type VARCHAR(50) NOT NULL,
    document_name VARCHAR(200) NOT NULL,
    employee_id VARCHAR(20),
    signer_id VARCHAR(20),
    sign_uri VARCHAR(500),
    sign_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    signature_data TEXT,
    watermark BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) NOT NULL DEFAULT 'signed',
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE SET NULL,
    FOREIGN KEY (signer_id) REFERENCES user(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 17. 通知消息
-- ============================================
CREATE TABLE notice (
    notice_id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    notice_type VARCHAR(50) NOT NULL,
    target_user_id VARCHAR(20),
    target_dept_id VARCHAR(20),
    channel VARCHAR(20) NOT NULL DEFAULT 'app',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,
    created_by VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 18. 系统配置
-- ============================================
CREATE TABLE config (
    config_id VARCHAR(20) PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(20) NOT NULL,
    description VARCHAR(500),
    updated_by VARCHAR(20),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 19. 薪资规则
-- ============================================
CREATE TABLE salary_rule (
    rule_id VARCHAR(20) PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    rule_config JSON NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '1.0',
    effective_date DATE NOT NULL,
    expiry_date DATE NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 20. 招聘渠道
-- ============================================
CREATE TABLE recruitment_channel (
    channel_id VARCHAR(20) PRIMARY KEY,
    channel_name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,
    api_config JSON,
    rpa_config JSON,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    last_sync_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 初始数据
-- ============================================

-- 默认系统配置
INSERT INTO config (config_id, config_key, config_value, config_type, description) VALUES
('cfg001', 'resume.pass_score', '60', 'integer', '简历筛选合格分数线'),
('cfg002', 'exam.default_questions', '40', 'integer', '默认试卷题目数量'),
('cfg003', 'salary.calc_date', '15', 'integer', '每月薪资核算日期'),
('cfg004', 'attendance.late_threshold', '9:05', 'time', '迟到判定时间阈值'),
('cfg005', 'overtime.monthly_limit', '36', 'decimal', '月加班上限(小时)'),
('cfg006', 'cert.reminder_days', '60,30,7,1', 'array', '证书效期提醒天数'),
('cfg007', 'ai.resume_model', 'gpt-4o', 'string', '简历评分使用的 AI 模型'),
('cfg008', 'ai.ocr_engine', 'paddleocr', 'string', 'OCR 引擎选择'),
('cfg009', 'payroll.tax_threshold', '5000', 'decimal', '个税免征额'),
('cfg010', 'backup.retention_days', '3650', 'integer', '备份保留天数(10 年)');

-- 默认薪资规则
INSERT INTO salary_rule (rule_id, rule_name, rule_type, rule_config, effective_date) VALUES
('sr001', '加班费计算', 'overtime', '{"weekday_multiplier": 1.5, "weekend_multiplier": 2.0, "holiday_multiplier": 3.0, "working_days_per_month": 21.75, "working_hours_per_day": 8}', '2026-01-01'),
('sr002', '个人所得税', 'tax', '{"brackets": [{"max": 36000, "rate": 0.03, "deduction": 0}, {"max": 144000, "rate": 0.10, "deduction": 2520}, {"max": 300000, "rate": 0.20, "deduction": 16920}, {"max": 420000, "rate": 0.25, "deduction": 31920}, {"max": 660000, "rate": 0.30, "deduction": 52920}, {"max": 960000, "rate": 0.35, "deduction": 85920}, {"max": null, "rate": 0.45, "deduction": 181920}]}', '2026-01-01');

-- 默认招聘渠道
INSERT INTO recruitment_channel (channel_id, channel_name, channel_type, status) VALUES
('ch001', '前程无忧', 'api', 'active'),
('ch002', '中国人才热线', 'api', 'active');

-- 创建索引
CREATE INDEX idx_employee_dept ON employee(dept_id);
CREATE INDEX idx_employee_status ON employee(status);
CREATE INDEX idx_resume_score ON resume(total_score);
CREATE INDEX idx_resume_position ON resume(applied_position);
CREATE INDEX idx_attendance_employee ON attendance_record(employee_id, date);
CREATE INDEX idx_payroll_month ON payroll(employee_id, month);
CREATE INDEX idx_audit_log_time ON audit_log(operated_at);
CREATE INDEX idx_audit_log_operator ON audit_log(operator_id);
CREATE INDEX idx_agent_log_status ON agent_run_log(status);
CREATE INDEX idx_cert_expire ON certificate(expire_date);