-- V2__hr_user_tables.sql
USE `hr_user`;

CREATE TABLE `employee_base` (
  `employee_id` VARCHAR(20) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `id_number` VARBINARY(128) NOT NULL COMMENT 'AES-256-GCM encrypted',
  `gender` CHAR(1) NOT NULL CHECK (`gender` IN ('M','F')),
  `birth_date` DATE NOT NULL,
  `phone` VARCHAR(20) NOT NULL,
  `email` VARCHAR(100) DEFAULT NULL,
  `hire_date` DATE NOT NULL,
  `leave_date` DATE DEFAULT NULL,
  `status` ENUM('在职','试用期','停薪留职','离职') NOT NULL DEFAULT '在职',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`employee_id`),
  KEY `idx_status` (`status`),
  KEY `idx_hire_date` (`hire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `employee_job` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `employee_id` VARCHAR(20) NOT NULL,
  `dept_id` VARCHAR(20) NOT NULL,
  `position_id` VARCHAR(20) NOT NULL,
  `entry_date` DATE NOT NULL,
  `is_primary` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_employee_id` (`employee_id`),
  CONSTRAINT `fk_ej_employee` FOREIGN KEY (`employee_id`) REFERENCES `employee_base`(`employee_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `employee_pay_profile` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `employee_id` VARCHAR(20) NOT NULL,
  `base_salary` DECIMAL(10,2) NOT NULL,
  `position_allowance` DECIMAL(10,2) DEFAULT 0,
  `subsidy_total` DECIMAL(10,2) DEFAULT 0,
  `version` INT NOT NULL DEFAULT 0 COMMENT 'Optimistic lock',
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_employee_id` (`employee_id`),
  CONSTRAINT `fk_epp_employee` FOREIGN KEY (`employee_id`) REFERENCES `employee_base`(`employee_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `face_feature` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `employee_id` VARCHAR(20) NOT NULL,
  `face_data` VARBINARY(1024) NOT NULL COMMENT '128-dim float vector AES-256-GCM encrypted',
  `photo_uri` VARCHAR(500) DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_employee_id` (`employee_id`),
  CONSTRAINT `fk_face_employee` FOREIGN KEY (`employee_id`) REFERENCES `employee_base`(`employee_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `certificate` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `employee_id` VARCHAR(20) NOT NULL,
  `cert_type` VARCHAR(50) NOT NULL,
  `cert_no` VARCHAR(100) NOT NULL,
  `issue_date` DATE DEFAULT NULL,
  `expiry_date` DATE DEFAULT NULL,
  `status` ENUM('有效','即将过期','已过期','待续期') NOT NULL DEFAULT '有效',
  `file_uri` VARCHAR(500) DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_employee_id` (`employee_id`),
  KEY `idx_expiry_date` (`expiry_date`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_cert_employee` FOREIGN KEY (`employee_id`) REFERENCES `employee_base`(`employee_id`)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `sys_user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL COMMENT 'BCrypt hash',
  `employee_id` VARCHAR(20) DEFAULT NULL,
  `role_ids` TEXT DEFAULT NULL,
  `status` ENUM('活跃','禁用','待审核') NOT NULL DEFAULT '活跃',
  `last_login_at` TIMESTAMP NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_employee_id` (`employee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `sys_role` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `role_code` VARCHAR(50) NOT NULL,
  `role_name` VARCHAR(100) NOT NULL,
  `role_type` ENUM('系统管理员','人事专员','部门主管','外务专员','普通员工') NOT NULL,
  `description` VARCHAR(500) DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `audit_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `operation_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `operator_id` VARCHAR(20) DEFAULT NULL,
  `operator_name` VARCHAR(50) DEFAULT NULL,
  `operator_ip` VARCHAR(45) DEFAULT NULL,
  `operation_type` VARCHAR(20) NOT NULL,
  `module` VARCHAR(50) NOT NULL,
  `target_id` VARCHAR(50) DEFAULT NULL,
  `target_name` VARCHAR(100) DEFAULT NULL,
  `before_snapshot` JSON DEFAULT NULL,
  `after_snapshot` JSON DEFAULT NULL,
  `result` ENUM('成功','失败') NOT NULL,
  `duration_ms` INT DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_operation_time` (`operation_time`),
  KEY `idx_operator_id` (`operator_id`),
  KEY `idx_module` (`module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `agent_run_log` (
  `run_id` VARCHAR(32) NOT NULL,
  `agent_name` VARCHAR(100) NOT NULL,
  `parent_flow_id` VARCHAR(32) DEFAULT NULL,
  `inputs_summary` JSON DEFAULT NULL,
  `reasoning_trace` TEXT DEFAULT NULL,
  `outputs_summary` JSON DEFAULT NULL,
  `status` ENUM('成功','失败','挂起') NOT NULL,
  `duration_ms` BIGINT DEFAULT NULL,
  `error_detail` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`run_id`),
  KEY `idx_agent_name` (`agent_name`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
