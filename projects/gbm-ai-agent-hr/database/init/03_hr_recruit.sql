-- ============================================
-- GBM AI Agent HR - hr_recruit Schema 表结构
-- ============================================
-- 域服务: recruit-domain (端口 8082)
-- 包含: 招聘管理、简历库、考试管理、培训管理、Camunda 8 流程引擎

USE hr_recruit;

-- 1. 招聘流程表
CREATE TABLE IF NOT EXISTS recruitment_process (
    process_id VARCHAR(20) PRIMARY KEY,
    position_id VARCHAR(20) NOT NULL,
    department_id VARCHAR(20) NOT NULL,
    headcount INT NOT NULL DEFAULT 1,
    status ENUM('进行中', '已暂停', '已完成', '已取消') NOT NULL DEFAULT '进行中',
    start_date DATE NOT NULL,
    end_date DATE NULL,
    jd_content TEXT,
   合格线 DECIMAL(5,2) NOT NULL DEFAULT 60,
    created_by VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_position (position_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 简历表
CREATE TABLE IF NOT EXISTS resume (
    resume_id VARCHAR(20) PRIMARY KEY,
    candidate_name VARCHAR(50) NOT NULL,
    id_number VARCHAR(18) NULL,
    phone VARCHAR(20) NULL,
    source_platform VARCHAR(50) NOT NULL,
    education VARCHAR(50) NULL,
    years_of_exp INT NULL,
    skill_tags TEXT NULL,
    age INT NULL,
    certs TEXT NULL,
    applied_position VARCHAR(100) NOT NULL,
    process_id VARCHAR(20) NULL,
    total_score DECIMAL(5,2) NULL,
    classify_result ENUM('高潜', '候审', '淘汰') NULL,
    file_uri VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_process (process_id),
    INDEX idx_score (total_score),
    INDEX idx_classify (classify_result),
    INDEX idx_phone (phone),
    FOREIGN KEY (process_id) REFERENCES recruitment_process(process_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 试卷表
CREATE TABLE IF NOT EXISTS exam_paper (
    paper_id VARCHAR(20) PRIMARY KEY,
    process_id VARCHAR(20) NOT NULL,
    position_type VARCHAR(50) NOT NULL,
    total_questions INT NOT NULL,
    total_score DECIMAL(5,2) NOT NULL DEFAULT 100,
    qr_code_uri VARCHAR(500),
    status ENUM('草稿', '已发布', '已过期') NOT NULL DEFAULT '草稿',
    created_by VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_process (process_id),
    INDEX idx_status (status),
    FOREIGN KEY (process_id) REFERENCES recruitment_process(process_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 试题表
CREATE TABLE IF NOT EXISTS exam_question (
    question_id VARCHAR(20) PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    type ENUM('单选题', '多选题', '判断题', '简答题', '论述题') NOT NULL,
    difficulty ENUM('简单', '中等', '困难') NOT NULL,
    score DECIMAL(5,2) NOT NULL,
    content TEXT NOT NULL,
    options JSON NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT NULL,
    created_by VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_type (type),
    INDEX idx_difficulty (difficulty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 试卷-试题关联表
CREATE TABLE IF NOT EXISTS paper_question (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    paper_id VARCHAR(20) NOT NULL,
    question_id VARCHAR(20) NOT NULL,
    sequence INT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES exam_question(question_id) ON DELETE CASCADE,
    UNIQUE KEY uk_paper_question (paper_id, question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 面试记录表
CREATE TABLE IF NOT EXISTS interview_record (
    record_id VARCHAR(20) PRIMARY KEY,
    resume_id VARCHAR(20) NOT NULL,
    paper_id VARCHAR(20) NULL,
    candidate_name VARCHAR(50) NOT NULL,
    interview_date DATETIME NOT NULL,
    objective_score DECIMAL(5,2) NULL,
    subjective_score DECIMAL(5,2) NULL,
    total_score DECIMAL(5,2) NULL,
    ai_evaluation_summary TEXT NULL,
    interviewer_feedback TEXT NULL,
    result ENUM('通过', '不通过', '待定') NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_resume (resume_id),
    FOREIGN KEY (resume_id) REFERENCES resume(resume_id) ON DELETE CASCADE,
    FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 培训计划表
CREATE TABLE IF NOT EXISTS training_plan (
    plan_id VARCHAR(20) PRIMARY KEY,
    training_name VARCHAR(200) NOT NULL,
    training_type ENUM('入职培训', '在岗培训', '特种作业培训', '其他') NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NULL,
    location VARCHAR(200),
    instructor VARCHAR(100),
    qr_code_uri VARCHAR(500),
    status ENUM('计划中', '进行中', '已完成', '已取消') NOT NULL DEFAULT '计划中',
    created_by VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_type (training_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 培训签到记录表
CREATE TABLE IF NOT EXISTS training_attendance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(20) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    check_in_time DATETIME NULL,
    check_out_time DATETIME NULL,
    status ENUM('已签到', '迟到', '早退', '缺席') NOT NULL DEFAULT '已签到',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_plan (plan_id),
    INDEX idx_employee (employee_id),
    FOREIGN KEY (plan_id) REFERENCES training_plan(plan_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. 考试成绩表
CREATE TABLE IF NOT EXISTS exam_result (
    result_id VARCHAR(20) PRIMARY KEY,
    plan_id VARCHAR(20) NULL,
    paper_id VARCHAR(20) NULL,
    employee_id VARCHAR(20) NULL,
    resume_id VARCHAR(20) NULL,
    candidate_name VARCHAR(50) NOT NULL,
    total_score DECIMAL(5,2) NOT NULL,
    objective_score DECIMAL(5,2) NULL,
    subjective_score DECIMAL(5,2) NULL,
    pass_status ENUM('及格', '不及格') NOT NULL,
    certificate_uri VARCHAR(500) NULL,
    exam_date DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee (employee_id),
    INDEX idx_plan (plan_id),
    INDEX idx_result (pass_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Camunda 8 流程定义表
CREATE TABLE IF NOT EXISTS bpmn_process_definition (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    process_id VARCHAR(100) NOT NULL UNIQUE,
    process_name VARCHAR(200) NOT NULL,
    version INT NOT NULL,
    bpmn_xml LONGTEXT NOT NULL,
    status ENUM('ACTIVE', 'DEPRECATED') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_process (process_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Camunda 8 流程实例表
CREATE TABLE IF NOT EXISTS bpmn_process_instance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    instance_id VARCHAR(64) NOT NULL UNIQUE,
    process_id VARCHAR(100) NOT NULL,
    business_key VARCHAR(200) NOT NULL,
    status ENUM('RUNNING', 'COMPLETED', 'CANCELED', 'TERMINATED') NOT NULL DEFAULT 'RUNNING',
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    variables JSON NULL,
    INDEX idx_process (process_id),
    INDEX idx_business (business_key),
    INDEX idx_status (status),
    FOREIGN KEY (process_id) REFERENCES bpmn_process_definition(process_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Camunda 8 任务表
CREATE TABLE IF NOT EXISTS bpmn_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    instance_id VARCHAR(64) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    assignee VARCHAR(100) NULL,
    status ENUM('CREATED', 'ASSIGNED', 'COMPLETED', 'FAILED') NOT NULL DEFAULT 'CREATED',
    priority INT NOT NULL DEFAULT 50,
    due_date TIMESTAMP NULL,
    variables JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_instance (instance_id),
    INDEX idx_assignee (assignee),
    INDEX idx_status (status),
    FOREIGN KEY (instance_id) REFERENCES bpmn_process_instance(instance_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Camunda 8 变量表
CREATE TABLE IF NOT EXISTS bpmn_variable (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    instance_id VARCHAR(64) NOT NULL,
    variable_name VARCHAR(100) NOT NULL,
    variable_value LONGTEXT NULL,
    variable_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_instance (instance_id),
    FOREIGN KEY (instance_id) REFERENCES bpmn_process_instance(instance_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. Camunda 8 执行日志表
CREATE TABLE IF NOT EXISTS bpmn_execution (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    instance_id VARCHAR(64) NOT NULL,
    activity_id VARCHAR(100) NOT NULL,
    activity_name VARCHAR(200) NOT NULL,
    event_type ENUM('START', 'COMPLETE', 'ERROR') NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    variables JSON NULL,
    INDEX idx_instance (instance_id),
    INDEX idx_activity (activity_id),
    FOREIGN KEY (instance_id) REFERENCES bpmn_process_instance(instance_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. Camunda 8 异常表
CREATE TABLE IF NOT EXISTS bpmn_incident (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    incident_id VARCHAR(64) NOT NULL UNIQUE,
    instance_id VARCHAR(64) NOT NULL,
    task_id VARCHAR(64) NULL,
    incident_type VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('CREATED', 'RESOLVED') NOT NULL DEFAULT 'CREATED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    INDEX idx_instance (instance_id),
    INDEX idx_status (status),
    FOREIGN KEY (instance_id) REFERENCES bpmn_process_instance(instance_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'hr_recruit schema tables created successfully!' AS status;
