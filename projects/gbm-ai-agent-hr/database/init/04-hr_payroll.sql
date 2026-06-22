-- GBM AI Agent HR - hr_payroll Schema DDL
-- Based on DATABASE_V19 design document
-- Contains: attendance, payroll, performance tables

USE hr_payroll;

-- ============================================
-- Shift configuration
-- ============================================
CREATE TABLE shift_config (
    shift_id VARCHAR(20) NOT NULL COMMENT '班次ID',
    shift_name VARCHAR(50) NOT NULL COMMENT '班次名称',
    shift_type ENUM('早班','中班','晚班','白班','夜班','弹性') NOT NULL COMMENT '班次类型',
    start_time TIME NOT NULL COMMENT '上班时间',
    end_time TIME NOT NULL COMMENT '下班时间',
    work_hours DECIMAL(4,2) NOT NULL COMMENT '工作时长',
    break_minutes INT DEFAULT 0 COMMENT '休息分钟',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (shift_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班次配置表';

-- ============================================
-- Attendance record
-- ============================================
CREATE TABLE attendance_record (
    record_id VARCHAR(20) NOT NULL COMMENT '记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    date DATE NOT NULL COMMENT '日期',
    clock_in TIME DEFAULT NULL COMMENT '上班打卡',
    clock_out TIME DEFAULT NULL COMMENT '下班打卡',
    shift_id VARCHAR(20) DEFAULT NULL COMMENT '班次',
    late_count INT DEFAULT 0 COMMENT '迟到次数',
    early_leave_count INT DEFAULT 0 COMMENT '早退次数',
    absent_days INT DEFAULT 0 COMMENT '旷工天数',
    holiday_leave_hrs DECIMAL(5,2) DEFAULT 0 COMMENT '事假小时数',
    sick_leave_hrs DECIMAL(5,2) DEFAULT 0 COMMENT '病假小时数',
    overtime_hrs DECIMAL(5,2) DEFAULT 0 COMMENT '加班时长',
    flag VARCHAR(20) DEFAULT NULL COMMENT '异常标志',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    KEY idx_employee_id_date (employee_id, date),
    KEY idx_flag (flag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考勤记录表';

-- ============================================
-- Leave application
-- ============================================
CREATE TABLE leave_application (
    apply_id VARCHAR(20) NOT NULL COMMENT '申请ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    leave_type ENUM('事假','病假','年假','婚假','产假','陪产假','丧假','工伤假') NOT NULL COMMENT '请假类型',
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NOT NULL COMMENT '结束日期',
    total_hours DECIMAL(5,2) NOT NULL COMMENT '总小时数',
    reason TEXT DEFAULT NULL COMMENT '请假事由',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/approved/rejected/cancelled',
    approver_id VARCHAR(20) DEFAULT NULL COMMENT '审批人',
    approved_at TIMESTAMP DEFAULT NULL COMMENT '审批时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (apply_id),
    KEY idx_employee_id (employee_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='请假申请表';

-- ============================================
-- Payroll
-- ============================================
CREATE TABLE payroll (
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
    status VARCHAR(20) NOT NULL DEFAULT '已核算' COMMENT '状态: 已核算/已审核/已发放',
    reviewed_by VARCHAR(20) DEFAULT NULL COMMENT '审核人',
    reviewed_at TIMESTAMP DEFAULT NULL COMMENT '审核时间',
    version INT DEFAULT 0 COMMENT '乐观锁版本号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (payroll_id),
    KEY idx_employee_id_month (employee_id, month),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资表';

-- ============================================
-- Salary change history
-- ============================================
CREATE TABLE salary_change_history (
    history_id VARCHAR(20) NOT NULL COMMENT '历史记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    field_type ENUM('薪资','文本','JSON') NOT NULL COMMENT '字段类型',
    field_name VARCHAR(50) NOT NULL COMMENT '字段名称',
    old_value TEXT DEFAULT NULL COMMENT '旧值',
    new_value TEXT DEFAULT NULL COMMENT '新值',
    change_reason VARCHAR(255) DEFAULT NULL COMMENT '变更原因',
    changed_by VARCHAR(20) DEFAULT NULL COMMENT '变更人',
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (history_id),
    KEY idx_employee_id (employee_id),
    KEY idx_changed_at (changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资变更历史';

-- ============================================
-- Salary rule
-- ============================================
CREATE TABLE salary_rule (
    rule_id VARCHAR(20) NOT NULL COMMENT '规则ID',
    rule_code VARCHAR(50) NOT NULL COMMENT '规则编号',
    rule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
    rule_type VARCHAR(50) NOT NULL COMMENT '规则类型: 加班系数/迟到扣款/补贴定额/社保比例/税率',
    rule_expression TEXT NOT NULL COMMENT '规则表达式',
    effective_date DATE NOT NULL COMMENT '生效日期',
    expire_date DATE DEFAULT NULL COMMENT '失效日期',
    version VARCHAR(20) DEFAULT '1.0' COMMENT '版本号',
    description VARCHAR(500) DEFAULT NULL COMMENT '规则说明',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/inactive',
    created_by VARCHAR(20) DEFAULT NULL COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (rule_id),
    UNIQUE KEY uk_rule_code_version (rule_code, version),
    KEY idx_rule_type (rule_type),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='薪资规则表';

-- ============================================
-- Performance review
-- ============================================
CREATE TABLE performance_review (
    pr_id VARCHAR(20) NOT NULL COMMENT '考核记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    cycle VARCHAR(7) NOT NULL COMMENT '考核周期 YYYY-MM',
    self_score DECIMAL(5,2) DEFAULT NULL COMMENT '自评分',
    mgr_score DECIMAL(5,2) DEFAULT NULL COMMENT '上级评分',
    rating VARCHAR(2) DEFAULT NULL COMMENT '等级: A/B/C/D',
    comments TEXT DEFAULT NULL COMMENT '评语',
    submit_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    approve_at TIMESTAMP DEFAULT NULL COMMENT '审批时间',
    approved_by VARCHAR(20) DEFAULT NULL COMMENT '审批人',
    version INT DEFAULT 0 COMMENT '乐观锁版本号',
    PRIMARY KEY (pr_id),
    KEY idx_employee_id_cycle (employee_id, cycle),
    KEY idx_rating (rating)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='绩效考核表';

-- ============================================
-- Payslip delivery record
-- ============================================
CREATE TABLE payslip_delivery (
    delivery_id VARCHAR(20) NOT NULL COMMENT '发放记录ID',
    payroll_id VARCHAR(20) NOT NULL COMMENT '薪资记录ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工',
    delivery_channel ENUM('email','sms','app_push') NOT NULL COMMENT '发放渠道',
    delivery_status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/sent/read/failed',
    delivered_at TIMESTAMP DEFAULT NULL COMMENT '发放时间',
    read_at TIMESTAMP DEFAULT NULL COMMENT '阅读时间',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (delivery_id),
    KEY idx_payroll_id (payroll_id),
    KEY idx_delivery_status (delivery_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工资条发放记录';
