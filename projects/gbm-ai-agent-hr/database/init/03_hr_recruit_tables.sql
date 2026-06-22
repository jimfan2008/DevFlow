-- GBM AI Agent HR - hr_recruit schema 表
-- 招聘管理、简历筛选、面试管理

USE hr_recruit;

-- ==================== 岗位表 ====================
CREATE TABLE IF NOT EXISTS `job_position` (
    `position_id` VARCHAR(20) NOT NULL,
    `position_name` VARCHAR(100) NOT NULL,
    `dept_id` VARCHAR(20) DEFAULT NULL,
    `level` VARCHAR(20) DEFAULT NULL,
    `headcount` INT DEFAULT 1,
    `min_education` VARCHAR(50) DEFAULT NULL,
    `min_years_exp` INT DEFAULT 0,
    `skill_requirements` JSON DEFAULT NULL,
    `cert_requirements` JSON DEFAULT NULL,
    `age_min` INT DEFAULT NULL,
    `age_max` INT DEFAULT NULL,
    `pass_score` DECIMAL(5,2) DEFAULT 60.00,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed','archived')),
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`position_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 招聘流程表 ====================
CREATE TABLE IF NOT EXISTS `recruitment_process` (
    `process_id` VARCHAR(20) NOT NULL,
    `position_id` VARCHAR(20) NOT NULL,
    `status` ENUM('发布中','筛选中','面试中','录用中','已完成','已取消') NOT NULL DEFAULT '发布中',
    `jd_content` TEXT DEFAULT NULL,
    `channel_list` JSON DEFAULT NULL,
    `started_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `completed_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`process_id`),
    KEY `idx_position_id` (`position_id`),
    CONSTRAINT `fk_rp_position` FOREIGN KEY (`position_id`) REFERENCES `job_position`(`position_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 简历表 ====================
CREATE TABLE IF NOT EXISTS `resume` (
    `resume_id` VARCHAR(20) NOT NULL,
    `candidate_name` VARCHAR(50) NOT NULL,
    `id_number` VARBINARY(128) DEFAULT NULL COMMENT 'AES-256 加密',
    `phone` VARCHAR(20) DEFAULT NULL,
    `source_platform` VARCHAR(50) NOT NULL,
    `education` VARCHAR(50) DEFAULT NULL,
    `years_of_exp` INT DEFAULT NULL,
    `skill_tags` TEXT DEFAULT NULL,
    `age` INT DEFAULT NULL,
    `certs` TEXT DEFAULT NULL,
    `applied_position` VARCHAR(100) NOT NULL,
    `total_score` DECIMAL(5,2) DEFAULT NULL,
    `score_detail` JSON DEFAULT NULL,
    `classify_result` VARCHAR(20) DEFAULT NULL CHECK (classify_result IN ('高潜','候审','淘汰')),
    `file_uri` VARCHAR(500) DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`resume_id`),
    KEY `idx_classify` (`classify_result`),
    KEY `idx_position` (`applied_position`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 试卷表 ====================
CREATE TABLE IF NOT EXISTS `exam_paper` (
    `paper_id` VARCHAR(20) NOT NULL,
    `process_id` VARCHAR(20) DEFAULT NULL,
    `position_id` VARCHAR(20) DEFAULT NULL,
    `candidate_id` VARCHAR(20) DEFAULT NULL,
    `total_questions` INT NOT NULL DEFAULT 40,
    `total_score` DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    `pass_score` DECIMAL(5,2) DEFAULT 60.00,
    `qr_code_uri` VARCHAR(500) DEFAULT NULL,
    `status` ENUM('草稿','已发布','已完成','已归档') NOT NULL DEFAULT '草稿',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`paper_id`),
    KEY `idx_process_id` (`process_id`),
    CONSTRAINT `fk_ep_process` FOREIGN KEY (`process_id`) REFERENCES `recruitment_process`(`process_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 题目表 ====================
CREATE TABLE IF NOT EXISTS `exam_question` (
    `question_id` VARCHAR(20) NOT NULL,
    `type` ENUM('单选','多选','判断','简答','论述','案例分析') NOT NULL,
    `difficulty` ENUM('简单','中等','困难') NOT NULL,
    `category` VARCHAR(50) DEFAULT NULL,
    `content` TEXT NOT NULL,
    `options` JSON DEFAULT NULL,
    `answer` TEXT DEFAULT NULL,
    `score` DECIMAL(5,2) NOT NULL DEFAULT 1.00,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`question_id`),
    KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 面试记录表 ====================
CREATE TABLE IF NOT EXISTS `interview_record` (
    `record_id` VARCHAR(20) NOT NULL,
    `resume_id` VARCHAR(20) NOT NULL,
    `paper_id` VARCHAR(20) DEFAULT NULL,
    `interview_date` DATE NOT NULL,
    `total_score` DECIMAL(5,2) DEFAULT NULL,
    `result` ENUM('通过','待定','不通过') DEFAULT NULL,
    `interviewer_id` VARCHAR(20) DEFAULT NULL,
    `comments` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`record_id`),
    KEY `idx_resume_id` (`resume_id`),
    CONSTRAINT `fk_ir_resume` FOREIGN KEY (`resume_id`) REFERENCES `resume`(`resume_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_ir_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper`(`paper_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
