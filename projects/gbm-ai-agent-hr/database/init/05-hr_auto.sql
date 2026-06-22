-- GBM AI Agent HR - hr_auto Schema DDL
-- Based on DATABASE_V19 design document
-- Contains: injury case, housing fund, RPA task, agent log tables

USE hr_auto;

-- ============================================
-- Injury case (工伤档案)
-- ============================================
CREATE TABLE injury_case (
    case_id VARCHAR(20) NOT NULL COMMENT '案件编号',
    employee_id VARCHAR(20) NOT NULL COMMENT '受伤员工',
    accident_date DATE NOT NULL COMMENT '事故发生日',
    description TEXT NOT NULL COMMENT '事故描述',
    docs JSON DEFAULT NULL COMMENT '上传的材料清单和路径',
    filing_no VARCHAR(50) DEFAULT NULL COMMENT '备案受理号',
    claim_amount DECIMAL(10,2) DEFAULT NULL COMMENT '理赔金额',
    status VARCHAR(20) NOT NULL DEFAULT '立案中' COMMENT '状态: 立案中/申报中/理赔完成',
    rpa_receipts JSON DEFAULT NULL COMMENT 'RPA操作截图凭证',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id),
    KEY idx_employee_id (employee_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工伤档案表';

-- ============================================
-- Housing fund record
-- ============================================
CREATE TABLE housing_fund_record (
    record_id VARCHAR(20) NOT NULL COMMENT '记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    account_no VARCHAR(50) DEFAULT NULL COMMENT '公积金账号',
    operation_type ENUM('开户','封存','补缴','销户') NOT NULL COMMENT '操作类型',
    base_amount DECIMAL(10,2) DEFAULT NULL COMMENT '缴存基数',
    personal_ratio DECIMAL(5,2) DEFAULT NULL COMMENT '个人比例(%)',
    company_ratio DECIMAL(5,2) DEFAULT NULL COMMENT '公司比例(%)',
    effective_month VARCHAR(7) DEFAULT NULL COMMENT '生效月份',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/completed/failed',
    rpa_receipt_uri VARCHAR(500) DEFAULT NULL COMMENT 'RPA操作回执',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    KEY idx_employee_id (employee_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公积金记录表';

-- ============================================
-- RPA task
-- ============================================
CREATE TABLE rpa_task (
    task_id VARCHAR(20) NOT NULL COMMENT '任务ID',
    task_type VARCHAR(50) NOT NULL COMMENT '任务类型: 工伤申报/公积金开户/简历抓取/社保查询',
    target_url VARCHAR(500) DEFAULT NULL COMMENT '目标URL',
    process_id VARCHAR(64) DEFAULT NULL COMMENT '异步任务唯一标识',
    kafka_message_id VARCHAR(128) DEFAULT NULL COMMENT 'Kafka消息消费者偏移追踪',
    status ENUM('pending','running','completed','failed','retry') NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    max_retries INT DEFAULT 3 COMMENT '最大重试次数',
    input_data JSON DEFAULT NULL COMMENT '输入数据',
    output_data JSON DEFAULT NULL COMMENT '输出数据',
    screenshot_uri VARCHAR(500) DEFAULT NULL COMMENT '操作截图链接',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    started_at TIMESTAMP DEFAULT NULL COMMENT '开始时间',
    completed_at TIMESTAMP DEFAULT NULL COMMENT '完成时间',
    duration_ms BIGINT DEFAULT NULL COMMENT '耗时(毫秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id),
    KEY idx_status (status),
    KEY idx_task_type (task_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RPA任务表';

-- ============================================
-- Agent execution log
-- ============================================
CREATE TABLE agent_run_log (
    run_id VARCHAR(32) NOT NULL COMMENT '执行流水号 (UUID)',
    agent_name VARCHAR(100) NOT NULL COMMENT 'Agent名称',
    parent_flow_id VARCHAR(32) DEFAULT NULL COMMENT '所属业务流程ID',
    inputs_summary JSON DEFAULT NULL COMMENT '输入概要',
    reasoning_trace TEXT DEFAULT NULL COMMENT '推理过程摘要',
    outputs_summary JSON DEFAULT NULL COMMENT '输出概要',
    status VARCHAR(20) NOT NULL COMMENT '状态: 成功/失败/挂起',
    duration_ms BIGINT DEFAULT NULL COMMENT '耗时(毫秒)',
    error_detail TEXT DEFAULT NULL COMMENT '错误堆栈',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id),
    KEY idx_agent_name (agent_name),
    KEY idx_parent_flow_id (parent_flow_id),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent执行日志表';

-- ============================================
-- Proof request (人事证明)
-- ============================================
CREATE TABLE proof_request (
    request_id VARCHAR(20) NOT NULL COMMENT '申请ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    proof_type ENUM('在职证明','收入证明','离职证明','薪资证明') NOT NULL COMMENT '证明类型',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/approved/rejected/issued',
    content_preview TEXT DEFAULT NULL COMMENT '内容预览',
    approved_by VARCHAR(20) DEFAULT NULL COMMENT '审批人',
    approved_at TIMESTAMP DEFAULT NULL COMMENT '审批时间',
    file_uri VARCHAR(500) DEFAULT NULL COMMENT '证明文件链接',
    issued_at TIMESTAMP DEFAULT NULL COMMENT '签发时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (request_id),
    KEY idx_employee_id (employee_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人事证明申请表';

-- ============================================
-- Expense receipt (费用票据)
-- ============================================
CREATE TABLE expense_receipt (
    receipt_id VARCHAR(20) NOT NULL COMMENT '票据ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    merchant_name VARCHAR(200) NOT NULL COMMENT '商户名称',
    receipt_date DATE NOT NULL COMMENT '票据日期',
    amount DECIMAL(10,2) NOT NULL COMMENT '金额',
    category VARCHAR(50) NOT NULL COMMENT '品目',
    invoice_no VARCHAR(100) DEFAULT NULL COMMENT '发票号码',
    verification_status VARCHAR(20) DEFAULT 'pending' COMMENT '真伪查验: pending/verified/fake',
    file_uri VARCHAR(500) DEFAULT NULL COMMENT '票据影像链接',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/approved/rejected/reimbursed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (receipt_id),
    KEY idx_employee_id (employee_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='费用票据表';

-- ============================================
-- Social security record
-- ============================================
CREATE TABLE social_security_record (
    record_id VARCHAR(20) NOT NULL COMMENT '记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    operation_type ENUM('参保','停保','补缴','转移') NOT NULL COMMENT '操作类型',
    base_amount DECIMAL(10,2) DEFAULT NULL COMMENT '缴费基数',
    effective_month VARCHAR(7) DEFAULT NULL COMMENT '生效月份',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/completed/failed',
    rpa_receipt_uri VARCHAR(500) DEFAULT NULL COMMENT 'RPA操作回执',
    error_message TEXT DEFAULT NULL COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    KEY idx_employee_id (employee_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社保记录表';

-- ============================================
-- Offboarding checklist (离职交接)
-- ============================================
CREATE TABLE offboarding_checklist (
    checklist_id VARCHAR(20) NOT NULL COMMENT '清单ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    item_name VARCHAR(100) NOT NULL COMMENT '交接项名称',
    responsible_dept VARCHAR(50) NOT NULL COMMENT '负责部门: IT/行政/财务/HR',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/completed',
    notes TEXT DEFAULT NULL COMMENT '备注',
    completed_by VARCHAR(20) DEFAULT NULL COMMENT '完成人',
    completed_at TIMESTAMP DEFAULT NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (checklist_id),
    KEY idx_employee_id (employee_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='离职交接清单';
