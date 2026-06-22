-- V4__hr_payroll_tables.sql
USE `hr_payroll`;

CREATE TABLE `attendance_record` (
  `record_id` VARCHAR(20) NOT NULL,
  `employee_id` VARCHAR(20) NOT NULL,
  `date` DATE NOT NULL,
  `clock_in` TIME DEFAULT NULL,
  `clock_out` TIME DEFAULT NULL,
  `shift_id` VARCHAR(20) DEFAULT NULL,
  `late_count` INT NOT NULL DEFAULT 0,
  `early_leave_count` INT NOT NULL DEFAULT 0,
  `absent_days` INT NOT NULL DEFAULT 0,
  `holiday_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `sick_leave_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `overtime_hrs` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `flag` VARCHAR(20) DEFAULT NULL,
  PRIMARY KEY (`record_id`),
  KEY `idx_employee_date` (`employee_id`, `date`),
  KEY `idx_flag` (`flag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `payroll` (
  `payroll_id` VARCHAR(20) NOT NULL,
  `employee_id` VARCHAR(20) NOT NULL,
  `month` VARCHAR(7) NOT NULL COMMENT 'YYYY-MM',
  `base_pay` DECIMAL(10,2) NOT NULL,
  `overtime_pay` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `attendance_deduct` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `allowances_total` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `deduction_total` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `ss_personal` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `gf_personal` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `income_tax` DECIMAL(10,2) NOT NULL DEFAULT 0,
  `net_pay` DECIMAL(10,2) NOT NULL,
  `status` ENUM('已核算','已审核','已发放') NOT NULL DEFAULT '已核算',
  `version` INT NOT NULL DEFAULT 0,
  `reviewed_by` VARCHAR(20) DEFAULT NULL,
  `reviewed_at` TIMESTAMP NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`payroll_id`),
  UNIQUE KEY `uk_employee_month` (`employee_id`, `month`),
  KEY `idx_month` (`month`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `performance_review` (
  `pr_id` VARCHAR(20) NOT NULL,
  `employee_id` VARCHAR(20) NOT NULL,
  `cycle` VARCHAR(7) NOT NULL COMMENT 'YYYY-MM',
  `self_score` DECIMAL(5,2) DEFAULT NULL,
  `mgr_score` DECIMAL(5,2) DEFAULT NULL,
  `rating` VARCHAR(2) DEFAULT NULL,
  `version` INT NOT NULL DEFAULT 0,
  `submit_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `approve_at` TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (`pr_id`),
  KEY `idx_employee_cycle` (`employee_id`, `cycle`),
  KEY `idx_cycle` (`cycle`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `injury_case` (
  `case_id` VARCHAR(20) NOT NULL,
  `employee_id` VARCHAR(20) NOT NULL,
  `accident_date` DATE NOT NULL,
  `description` TEXT NOT NULL,
  `docs` JSON DEFAULT NULL,
  `filing_no` VARCHAR(50) DEFAULT NULL,
  `claim_amount` DECIMAL(10,2) DEFAULT NULL,
  `status` ENUM('立案中','申报中','理赔完成') NOT NULL DEFAULT '立案中',
  `rpa_receipts` JSON DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`case_id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `rpa_task` (
  `task_id` VARCHAR(20) NOT NULL,
  `process_id` VARCHAR(64) DEFAULT NULL,
  `kafka_message_id` VARCHAR(128) DEFAULT NULL,
  `task_type` ENUM('社保申报','公积金参保','公积金减员','工伤申报','其他') NOT NULL,
  `target_url` VARCHAR(500) DEFAULT NULL,
  `status` ENUM('待执行','执行中','成功','失败','挂起') NOT NULL DEFAULT '待执行',
  `result` JSON DEFAULT NULL,
  `error_detail` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (`task_id`),
  KEY `idx_status` (`status`),
  KEY `idx_task_type` (`task_type`),
  KEY `idx_process_id` (`process_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
