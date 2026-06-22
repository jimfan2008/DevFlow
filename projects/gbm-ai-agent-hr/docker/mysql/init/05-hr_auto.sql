-- hr_auto schema - External Affairs, RPA, Injury, Housing Fund tables
USE hr_auto;

-- 工伤案件表
CREATE TABLE IF NOT EXISTS injury_case (
    case_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    accident_date DATE NOT NULL,
    description TEXT NOT NULL,
    docs JSON,
    filing_no VARCHAR(50),
    claim_amount DECIMAL(10,2),
    status VARCHAR(20) DEFAULT '立案中',
    rpa_receipts JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_date (accident_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 公积金记录表
CREATE TABLE IF NOT EXISTS housing_fund_record (
    record_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    operation_type ENUM('开户', '缴存', '补缴', '封存', '销户') NOT NULL,
    base_amount DECIMAL(10,2),
    company_amount DECIMAL(10,2),
    personal_amount DECIMAL(10,2),
    effective_month VARCHAR(7),
    status VARCHAR(20) DEFAULT '待办理',
    rpa_receipt_uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_month (effective_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 社保记录表
CREATE TABLE IF NOT EXISTS social_security_record (
    record_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    operation_type ENUM('参保', '补缴', '停保', '转移') NOT NULL,
    insurance_type VARCHAR(50) NOT NULL,
    base_amount DECIMAL(10,2),
    company_amount DECIMAL(10,2),
    personal_amount DECIMAL(10,2),
    effective_month VARCHAR(7),
    status VARCHAR(20) DEFAULT '待办理',
    receipt_uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_month (effective_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- RPA 任务表
CREATE TABLE IF NOT EXISTS rpa_task (
    task_id VARCHAR(20) PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    target_system VARCHAR(50) NOT NULL,
    process_id VARCHAR(64),
    kafka_message_id VARCHAR(128),
    employee_id VARCHAR(20),
    related_case_id VARCHAR(20),
    status ENUM('pending', 'running', 'success', 'failed', 'retrying', 'manual_intervention') DEFAULT 'pending',
    inputs JSON,
    outputs JSON,
    screenshot_uri VARCHAR(500),
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_type (task_type),
    INDEX idx_employee (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 离职申请表
CREATE TABLE IF NOT EXISTS leave_application (
    application_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    last_work_date DATE NOT NULL,
    reason TEXT,
    handover_list JSON,
    status VARCHAR(20) DEFAULT '待审批',
    approved_by VARCHAR(20),
    approved_at TIMESTAMP,
    certificate_uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 证明申请表
CREATE TABLE IF NOT EXISTS proof_application (
    application_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    proof_type VARCHAR(50) NOT NULL,
    purpose VARCHAR(200),
    status VARCHAR(20) DEFAULT '待审核',
    reviewed_by VARCHAR(20),
    reviewed_at TIMESTAMP,
    file_uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_type (proof_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 费用报销表
CREATE TABLE IF NOT EXISTS expense_claim (
    claim_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    claim_type VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    invoice_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT '待审核',
    reviewed_by VARCHAR(20),
    reviewed_at TIMESTAMP,
    receipts JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Agent 执行日志表
CREATE TABLE IF NOT EXISTS agent_run_log (
    run_id VARCHAR(32) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    parent_flow_id VARCHAR(32),
    inputs_summary JSON,
    reasoning_trace TEXT,
    outputs_summary JSON,
    status VARCHAR(20) NOT NULL,
    duration_ms BIGINT,
    error_detail TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_agent (agent_name),
    INDEX idx_status (status),
    INDEX idx_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    config_id VARCHAR(20) PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(20) DEFAULT 'string',
    description VARCHAR(500),
    updated_by VARCHAR(20),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
