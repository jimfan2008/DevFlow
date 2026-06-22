-- hr_recruit schema - Recruitment & Training tables
USE hr_recruit;

-- 简历表
CREATE TABLE IF NOT EXISTS resume (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_position (applied_position),
    INDEX idx_score (total_score),
    INDEX idx_classify (classify_result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 招聘流程表
CREATE TABLE IF NOT EXISTS recruitment_process (
    process_id VARCHAR(20) PRIMARY KEY,
    position_id VARCHAR(20) NOT NULL,
    dept_id VARCHAR(20),
    head_count INT DEFAULT 1,
    status VARCHAR(20) DEFAULT '招聘中',
    jd_content TEXT,
    publish_date DATE,
    close_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (position_id) REFERENCES job_position(position_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 试卷表
CREATE TABLE IF NOT EXISTS exam_paper (
    paper_id VARCHAR(20) PRIMARY KEY,
    process_id VARCHAR(20),
    position_id VARCHAR(20),
    paper_name VARCHAR(200) NOT NULL,
    total_questions INT DEFAULT 40,
    total_score INT DEFAULT 100,
    pass_score INT DEFAULT 60,
    qr_code VARCHAR(500),
    status VARCHAR(20) DEFAULT '待发布',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (process_id) REFERENCES recruitment_process(process_id),
    INDEX idx_position (position_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 试题表
CREATE TABLE IF NOT EXISTS exam_question (
    question_id VARCHAR(20) PRIMARY KEY,
    paper_id VARCHAR(20),
    question_type ENUM('single', 'multiple', 'true_false', 'short_answer', 'essay') NOT NULL,
    difficulty ENUM('easy', 'medium', 'hard') NOT NULL,
    score INT NOT NULL,
    content TEXT NOT NULL,
    options JSON,
    correct_answer TEXT,
    explanation TEXT,
    tags VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 面试记录表
CREATE TABLE IF NOT EXISTS interview_record (
    record_id VARCHAR(20) PRIMARY KEY,
    resume_id VARCHAR(20) NOT NULL,
    paper_id VARCHAR(20),
    process_id VARCHAR(20),
    interview_date DATETIME,
    total_score DECIMAL(5,2),
    ai_score DECIMAL(5,2),
    human_score DECIMAL(5,2),
    score_diff DECIMAL(5,2),
    need_review BOOLEAN DEFAULT FALSE,
    result VARCHAR(20),
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES resume(resume_id),
    FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id) ON DELETE SET NULL,
    INDEX idx_date (interview_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 培训记录表
CREATE TABLE IF NOT EXISTS training_record (
    training_id VARCHAR(20) PRIMARY KEY,
    training_name VARCHAR(200) NOT NULL,
    training_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    instructor VARCHAR(100),
    max_attendees INT,
    qr_code VARCHAR(500),
    status VARCHAR(20) DEFAULT '待开始',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 培训签到表
CREATE TABLE IF NOT EXISTS training_attendance (
    attendance_id VARCHAR(20) PRIMARY KEY,
    training_id VARCHAR(20) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    check_in_time DATETIME,
    check_out_time DATETIME,
    status VARCHAR(20) DEFAULT '已签到',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (training_id) REFERENCES training_record(training_id),
    INDEX idx_training (training_id),
    INDEX idx_employee (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 培训成绩表
CREATE TABLE IF NOT EXISTS training_score (
    score_id VARCHAR(20) PRIMARY KEY,
    training_id VARCHAR(20) NOT NULL,
    employee_id VARCHAR(20) NOT NULL,
    paper_id VARCHAR(20),
    total_score DECIMAL(5,2),
    pass BOOLEAN,
    certificate_uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (training_id) REFERENCES training_record(training_id),
    FOREIGN KEY (employee_id) REFERENCES employee_base(employee_id),
    FOREIGN KEY (paper_id) REFERENCES exam_paper(paper_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Camunda 8 流程定义表
CREATE TABLE IF NOT EXISTS bpmn_process_definition (
    def_id VARCHAR(32) PRIMARY KEY,
    process_key VARCHAR(100) NOT NULL,
    version INT NOT NULL,
    bpmn_xml LONGTEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Camunda 8 流程实例表
CREATE TABLE IF NOT EXISTS bpmn_process_instance (
    instance_id VARCHAR(32) PRIMARY KEY,
    def_id VARCHAR(32) NOT NULL,
    business_key VARCHAR(100),
    status VARCHAR(20) DEFAULT 'running',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    variables JSON,
    FOREIGN KEY (def_id) REFERENCES bpmn_process_definition(def_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Camunda 8 任务表
CREATE TABLE IF NOT EXISTS bpmn_task (
    task_id VARCHAR(32) PRIMARY KEY,
    instance_id VARCHAR(32) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    assignee VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    variables JSON,
    FOREIGN KEY (instance_id) REFERENCES bpmn_process_instance(instance_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Camunda 8 变量表
CREATE TABLE IF NOT EXISTS bpmn_variable (
    var_id VARCHAR(32) PRIMARY KEY,
    instance_id VARCHAR(32) NOT NULL,
    variable_name VARCHAR(100) NOT NULL,
    variable_value JSON,
    type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES bpmn_process_instance(instance_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Camunda 8 执行记录表
CREATE TABLE IF NOT EXISTS bpmn_execution (
    exec_id VARCHAR(32) PRIMARY KEY,
    task_id VARCHAR(32) NOT NULL,
    step_name VARCHAR(100),
    status VARCHAR(20),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    result JSON,
    FOREIGN KEY (task_id) REFERENCES bpmn_task(task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Camunda 8 事件记录表
CREATE TABLE IF NOT EXISTS bpmn_incident (
    incident_id VARCHAR(32) PRIMARY KEY,
    instance_id VARCHAR(32) NOT NULL,
    task_id VARCHAR(32),
    incident_type VARCHAR(50),
    message TEXT,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES bpmn_process_instance(instance_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
