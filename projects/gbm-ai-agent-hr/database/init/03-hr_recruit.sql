-- GBM AI Agent HR - hr_recruit Schema DDL
-- Based on DATABASE_V19 design document
-- Contains: recruitment, interview, training tables

USE hr_recruit;

-- ============================================
-- Resume table
-- ============================================
CREATE TABLE resume (
    resume_id VARCHAR(20) NOT NULL COMMENT '简历ID',
    candidate_name VARCHAR(50) NOT NULL COMMENT '姓名',
    id_number VARCHAR(18) DEFAULT NULL COMMENT '身份证号（加密，用于去重）',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号（用于去重）',
    source_platform VARCHAR(50) NOT NULL COMMENT '来源平台',
    education VARCHAR(50) DEFAULT NULL COMMENT '最高学历',
    years_of_exp INT DEFAULT NULL COMMENT '从业年限',
    skill_tags TEXT DEFAULT NULL COMMENT '技能标签（逗号分隔）',
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
    KEY idx_classify_result (classify_result),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';

-- ============================================
-- Recruitment process
-- ============================================
CREATE TABLE recruitment_process (
    process_id VARCHAR(20) NOT NULL COMMENT '流程ID',
    position_id VARCHAR(20) DEFAULT NULL COMMENT '岗位ID',
    job_description TEXT DEFAULT NULL COMMENT '职位描述',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/closed/frozen',
    required_count INT DEFAULT 1 COMMENT '需求人数',
    hired_count INT DEFAULT 0 COMMENT '已录用人数',
    qualified_threshold DECIMAL(5,2) DEFAULT 60.00 COMMENT '合格线（默认60分）',
    start_date DATE DEFAULT NULL COMMENT '开始日期',
    end_date DATE DEFAULT NULL COMMENT '截止日期',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (process_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='招聘流程表';

-- ============================================
-- Exam paper
-- ============================================
CREATE TABLE exam_paper (
    paper_id VARCHAR(20) NOT NULL COMMENT '试卷ID',
    process_id VARCHAR(20) DEFAULT NULL COMMENT '所属招聘流程',
    paper_name VARCHAR(200) NOT NULL COMMENT '试卷名称',
    total_questions INT DEFAULT 40 COMMENT '题目总数',
    total_score DECIMAL(5,2) DEFAULT 100.00 COMMENT '总分',
    pass_score DECIMAL(5,2) DEFAULT 60.00 COMMENT '及格分数',
    qr_code_uri VARCHAR(500) DEFAULT NULL COMMENT '考试二维码',
    status VARCHAR(20) DEFAULT 'draft' COMMENT '状态: draft/published/archived',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (paper_id),
    KEY idx_process_id (process_id),
    CONSTRAINT fk_exam_paper_process FOREIGN KEY (paper_id) REFERENCES recruitment_process(process_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷表';

-- ============================================
-- Exam question
-- ============================================
CREATE TABLE exam_question (
    question_id VARCHAR(20) NOT NULL COMMENT '题目ID',
    type ENUM('单选','多选','判断','简答','论述','案例分析') NOT NULL COMMENT '题型',
    difficulty ENUM('简单','中等','困难') NOT NULL COMMENT '难度',
    score DECIMAL(5,2) NOT NULL COMMENT '分值',
    content TEXT NOT NULL COMMENT '题目内容',
    options JSON DEFAULT NULL COMMENT '选项（A/B/C/D）',
    answer TEXT DEFAULT NULL COMMENT '标准答案',
    explanation TEXT DEFAULT NULL COMMENT '解析',
    tags VARCHAR(255) DEFAULT NULL COMMENT '知识点标签',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (question_id),
    KEY idx_type (type),
    KEY idx_difficulty (difficulty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题库表';

-- ============================================
-- Paper-question mapping
-- ============================================
CREATE TABLE paper_question (
    paper_id VARCHAR(20) NOT NULL,
    question_id VARCHAR(20) NOT NULL,
    question_order INT DEFAULT 0 COMMENT '题目序号',
    PRIMARY KEY (paper_id, question_id),
    CONSTRAINT fk_pq_paper FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_pq_question FOREIGN KEY (question_id) REFERENCES exam_question(question_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷题目关联表';

-- ============================================
-- Interview record
-- ============================================
CREATE TABLE interview_record (
    record_id VARCHAR(20) NOT NULL COMMENT '记录ID',
    resume_id VARCHAR(20) NOT NULL COMMENT '简历ID',
    paper_id VARCHAR(20) DEFAULT NULL COMMENT '试卷ID',
    candidate_name VARCHAR(50) NOT NULL COMMENT '考生姓名',
    total_score DECIMAL(5,2) DEFAULT NULL COMMENT '总分',
    objective_score DECIMAL(5,2) DEFAULT NULL COMMENT '客观题得分',
    subjective_score DECIMAL(5,2) DEFAULT NULL COMMENT '主观题得分',
    ai_cross_score_detail JSON DEFAULT NULL COMMENT 'AI交叉评分详情',
    result VARCHAR(20) DEFAULT NULL COMMENT '结果: 合格/不合格/待复核',
    completed_at TIMESTAMP DEFAULT NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    KEY idx_resume_id (resume_id),
    KEY idx_result (result),
    CONSTRAINT fk_interview_resume FOREIGN KEY (record_id) REFERENCES resume(resume_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_interview_paper FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试记录表';

-- ============================================
-- Training plan
-- ============================================
CREATE TABLE training_plan (
    plan_id VARCHAR(20) NOT NULL COMMENT '培训计划ID',
    plan_name VARCHAR(200) NOT NULL COMMENT '培训计划名称',
    dept_id VARCHAR(20) DEFAULT NULL COMMENT '所属部门',
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NOT NULL COMMENT '结束日期',
    status VARCHAR(20) DEFAULT 'draft' COMMENT '状态: draft/scheduled/in_progress/completed',
    qr_code_uri VARCHAR(500) DEFAULT NULL COMMENT '签到二维码',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (plan_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训计划表';

-- ============================================
-- Training record
-- ============================================
CREATE TABLE training_record (
    record_id VARCHAR(20) NOT NULL COMMENT '记录ID',
    plan_id VARCHAR(20) NOT NULL COMMENT '培训计划ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工ID',
    sign_in_time TIMESTAMP DEFAULT NULL COMMENT '签到时间',
    sign_in_status VARCHAR(20) DEFAULT 'pending' COMMENT '签到状态: pending/on_time/late/absent',
    exam_score DECIMAL(5,2) DEFAULT NULL COMMENT '考试成绩',
    exam_result VARCHAR(20) DEFAULT NULL COMMENT '考试结果: 及格/不及格/补考',
    certificate_uri VARCHAR(500) DEFAULT NULL COMMENT '结业证书链接',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    KEY idx_plan_id (plan_id),
    KEY idx_employee_id (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='培训记录表';

-- ============================================
-- Certificate ledger
-- ============================================
CREATE TABLE certificate_ledger (
    cert_id VARCHAR(20) NOT NULL COMMENT '证书ID',
    employee_id VARCHAR(20) NOT NULL COMMENT '员工ID',
    cert_type VARCHAR(50) NOT NULL COMMENT '证书类型',
    cert_no VARCHAR(100) NOT NULL COMMENT '证书编号',
    issue_date DATE DEFAULT NULL COMMENT '颁发日期',
    expire_date DATE DEFAULT NULL COMMENT '到期日期',
    status VARCHAR(20) DEFAULT 'valid' COMMENT '状态: valid/expiring/expired/revoked',
    reminder_days INT[] DEFAULT '[60,30,7,1]' COMMENT '提醒天数',
    file_uri VARCHAR(500) DEFAULT NULL COMMENT '证书影像链接',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (cert_id),
    KEY idx_employee_id (employee_id),
    KEY idx_expire_date (expire_date),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='证书台账表';

-- ============================================
-- Camunda 8 process tables
-- ============================================
CREATE TABLE bpmn_process_definition (
    definition_id VARCHAR(32) NOT NULL,
    bpmn_xml TEXT NOT NULL,
    version INT DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (definition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='BPMN流程定义';

CREATE TABLE bpmn_process_instance (
    instance_id VARCHAR(32) NOT NULL,
    definition_id VARCHAR(32) NOT NULL,
    business_key VARCHAR(100) DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'running',
    variables JSON DEFAULT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP DEFAULT NULL,
    PRIMARY KEY (instance_id),
    KEY idx_definition_id (definition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='BPMN流程实例';

CREATE TABLE bpmn_task (
    task_id VARCHAR(32) NOT NULL,
    instance_id VARCHAR(32) NOT NULL,
    task_type ENUM('service','user','subprocess') NOT NULL,
    assignee VARCHAR(50) DEFAULT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    due_date DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP DEFAULT NULL,
    PRIMARY KEY (task_id),
    KEY idx_instance_id (instance_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='BPMN任务表';
