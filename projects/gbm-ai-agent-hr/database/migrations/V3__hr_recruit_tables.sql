-- V3__hr_recruit_tables.sql
USE `hr_recruit`;

CREATE TABLE `resume` (
  `resume_id` VARCHAR(20) NOT NULL,
  `candidate_name` VARCHAR(50) NOT NULL,
  `id_number` VARBINARY(128) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `source_platform` VARCHAR(50) NOT NULL,
  `education` VARCHAR(50) DEFAULT NULL,
  `years_of_exp` INT DEFAULT NULL,
  `skill_tags` TEXT DEFAULT NULL,
  `age` INT DEFAULT NULL,
  `certs` TEXT DEFAULT NULL,
  `applied_position` VARCHAR(100) NOT NULL,
  `total_score` DECIMAL(5,2) DEFAULT NULL,
  `classify_result` ENUM('高潜','候审','淘汰') DEFAULT NULL,
  `file_uri` VARCHAR(500) DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`resume_id`),
  KEY `idx_applied_position` (`applied_position`),
  KEY `idx_total_score` (`total_score`),
  KEY `idx_classify_result` (`classify_result`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `recruitment_process` (
  `process_id` VARCHAR(20) NOT NULL,
  `position_id` VARCHAR(20) NOT NULL,
  `status` ENUM('进行中','已完成','已取消') NOT NULL DEFAULT '进行中',
  `jd_content` TEXT DEFAULT NULL,
  `pass_score` DECIMAL(5,2) NOT NULL DEFAULT 60,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`process_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `exam_paper` (
  `paper_id` VARCHAR(20) NOT NULL,
  `process_id` VARCHAR(20) NOT NULL,
  `candidate_name` VARCHAR(50) NOT NULL,
  `total_questions` INT NOT NULL,
  `qr_code` VARCHAR(100) NOT NULL,
  `status` ENUM('待考试','已完成','已阅卷') NOT NULL DEFAULT '待考试',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`paper_id`),
  KEY `idx_process_id` (`process_id`),
  KEY `idx_qr_code` (`qr_code`),
  CONSTRAINT `fk_paper_process` FOREIGN KEY (`process_id`) REFERENCES `recruitment_process`(`process_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `training_record` (
  `record_id` VARCHAR(20) NOT NULL,
  `employee_id` VARCHAR(20) NOT NULL,
  `course_name` VARCHAR(200) NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE DEFAULT NULL,
  `status` ENUM('进行中','已完成','已取消') NOT NULL DEFAULT '进行中',
  `score` DECIMAL(5,2) DEFAULT NULL,
  `certificate_uri` VARCHAR(500) DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`record_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `interview_record` (
  `record_id` VARCHAR(20) NOT NULL,
  `resume_id` VARCHAR(20) NOT NULL,
  `paper_id` VARCHAR(20) DEFAULT NULL,
  `interview_date` DATETIME NOT NULL,
  `interviewer` VARCHAR(50) NOT NULL,
  `score` DECIMAL(5,2) DEFAULT NULL,
  `evaluation` TEXT DEFAULT NULL,
  `result` ENUM('通过','不通过','待定') DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`record_id`),
  KEY `idx_resume_id` (`resume_id`),
  CONSTRAINT `fk_interview_resume` FOREIGN KEY (`resume_id`) REFERENCES `resume`(`resume_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_interview_paper` FOREIGN KEY (`paper_id`) REFERENCES `exam_paper`(`paper_id`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
