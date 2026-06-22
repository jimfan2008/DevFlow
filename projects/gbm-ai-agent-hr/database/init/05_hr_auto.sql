-- ============================================
-- GBM AI Agent HR - hr_auto Schema 表结构
-- ============================================
-- 域服务: auto-domain (端口 8084)
-- 包含: 工伤管理、公积金管理、RPA 任务、证书管理、文档归档、Agent 执行日志

USE hr_auto;

-- 1. 工伤档案表
CREATE TABLE IF NOT EXISTS injury_case (
    case_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    accident_date DATE NOT NULL,
    description TEXT NOT NULL,
    docs JSON NULL,
    filing_no VARCHAR(50) NULL,
    claim_amount DECIMAL(10,2) NULL,
    status ENUM('立案中', '申报中', '理赔完成', '理赔失败') NOT NULL DEFAULT '立案中',
    rpa_receipts JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_status (status),
    INDEX idx_date (accident_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 公积金记录表
CREATE TABLE IF NOT EXISTS housing_fund_record (
    record_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    operation_type ENUM('开户', '缴存', '补缴', '封存', '销户') NOT NULL,
    base_amount DECIMAL(10,2) NOT NULL,
    personal_rate DECIMAL(5,2) NOT NULL DEFAULT 12.00,
    company_rate DECIMAL(5,2) NOT NULL DEFAULT 12.00,
    personal_amount DECIMAL(10,2) NOT NULL,
    company_amount DECIMAL(10,2) NOT NULL,
    effective_month VARCHAR(7) NOT NULL,
    status ENUM('待提交', '已提交', '已完成', '失败') NOT NULL DEFAULT '待提交',
    receipt_uri VARCHAR(500) NULL,
    rpa_task_id VARCHAR(20) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_month (effective_month),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. RPA 任务表
CREATE TABLE IF NOT EXISTS rpa_task (
    task_id VARCHAR(20) PRIMARY KEY,
    process_id VARCHAR(64) NULL,
    kafka_message_id VARCHAR(128) NULL,
    target_system VARCHAR(50) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    input_data JSON NOT NULL,
    status ENUM('待执行', '执行中', '已完成', '失败', '待人工处理') NOT NULL DEFAULT '待执行',
    result_data JSON NULL,
    screenshot_uri VARCHAR(500) NULL,
    error_detail TEXT NULL,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    duration_ms BIGINT NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_process (process_id),
    INDEX idx_kafka (kafka_message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 证书台账表
CREATE TABLE IF NOT EXISTS certificate_registry (
    cert_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    cert_type ENUM('特种作业证', '上岗证', '职业资格证书', '其他') NOT NULL,
    cert_name VARCHAR(200) NOT NULL,
    cert_number VARCHAR(100) NOT NULL,
    issuing_authority VARCHAR(200),
    issue_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    status ENUM('有效', '即将到期', '已过期', '待续期') NOT NULL DEFAULT '有效',
    attachment_uri VARCHAR(500) NULL,
    reminder_days INT NOT NULL DEFAULT 60,
    next_reminder_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_expiry (expiry_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 文档归档表
CREATE TABLE IF NOT EXISTS document_archive (
    doc_id VARCHAR(20) PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,
    related_employee_id VARCHAR(20) NULL,
    related_process_id VARCHAR(20) NULL,
    file_uri VARCHAR(500) NOT NULL,
    file_name VARCHAR(200) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    hash_value VARCHAR(64),
    retention_years INT NOT NULL,
    archive_date DATE NOT NULL,
    expiry_date DATE NULL,
    status ENUM('在线', '离线归档', '已清理') NOT NULL DEFAULT '在线',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (doc_type),
    INDEX idx_employee (related_employee_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Agent 执行日志表
CREATE TABLE IF NOT EXISTS agent_run_log (
    run_id VARCHAR(32) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    parent_flow_id VARCHAR(32) NULL,
    inputs_summary JSON NULL,
    reasoning_trace TEXT NULL,
    outputs_summary JSON NULL,
    status ENUM('成功', '失败', '挂起') NOT NULL,
    duration_ms BIGINT NULL,
    error_detail TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_agent (agent_name),
    INDEX idx_flow (parent_flow_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 离职交接清单表
CREATE TABLE IF NOT EXISTS exit_checklist (
    checklist_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    responsible_dept VARCHAR(50) NOT NULL,
    status ENUM('待交接', '交接中', '已完成', '已跳过') NOT NULL DEFAULT '待交接',
    remarks TEXT NULL,
    completed_by VARCHAR(20) NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 人事证明申请表
CREATE TABLE IF NOT EXISTS certificate_application (
    application_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    cert_type ENUM('在职证明', '收入证明', '离职证明', '其他') NOT NULL,
    purpose VARCHAR(200) NULL,
    status ENUM('待审核', '已审核', '已签发', '已拒绝') NOT NULL DEFAULT '待审核',
    document_uri VARCHAR(500) NULL,
    reviewed_by VARCHAR(20) NULL,
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'hr_auto schema tables created successfully!' AS status;
