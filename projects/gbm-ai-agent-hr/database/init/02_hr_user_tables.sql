-- GBM AI Agent HR - hr_user schema 核心表
-- 用户管理、员工档案、审计日志

USE hr_user;

-- ==================== 部门表 ====================
CREATE TABLE IF NOT EXISTS `department` (
    `dept_id` VARCHAR(20) NOT NULL,
    `dept_name` VARCHAR(100) NOT NULL,
    `parent_id` VARCHAR(20) DEFAULT NULL,
    `sort_order` INT DEFAULT 0,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`dept_id`),
    KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 用户表 ====================
CREATE TABLE IF NOT EXISTS `sys_user` (
    `user_id` VARCHAR(20) NOT NULL,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `name` VARCHAR(50) NOT NULL,
    `email` VARCHAR(100) DEFAULT NULL UNIQUE,
    `phone` VARCHAR(20) DEFAULT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','locked')),
    `last_login_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`),
    KEY `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 角色表 ====================
CREATE TABLE IF NOT EXISTS `sys_role` (
    `role_id` VARCHAR(20) NOT NULL,
    `role_name` VARCHAR(50) NOT NULL UNIQUE,
    `role_type` ENUM('系统管理员','人事专员','部门主管','外务专员','普通员工') NOT NULL,
    `description` TEXT DEFAULT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 权限表 ====================
CREATE TABLE IF NOT EXISTS `sys_permission` (
    `permission_id` VARCHAR(20) NOT NULL,
    `resource_type` ENUM('menu','button','api','data') NOT NULL,
    `resource_name` VARCHAR(100) NOT NULL,
    `action` VARCHAR(50) NOT NULL,
    `path` VARCHAR(255) DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 用户角色关联 ====================
CREATE TABLE IF NOT EXISTS `sys_user_role` (
    `user_id` VARCHAR(20) NOT NULL,
    `role_id` VARCHAR(20) NOT NULL,
    `assigned_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`, `role_id`),
    CONSTRAINT `fk_ur_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user`(`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_ur_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role`(`role_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 角色权限关联 ====================
CREATE TABLE IF NOT EXISTS `sys_role_permission` (
    `role_id` VARCHAR(20) NOT NULL,
    `permission_id` VARCHAR(20) NOT NULL,
    `assigned_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`role_id`, `permission_id`),
    CONSTRAINT `fk_rp_role` FOREIGN KEY (`role_id`) REFERENCES `sys_role`(`role_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_rp_perm` FOREIGN KEY (`permission_id`) REFERENCES `sys_permission`(`permission_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 员工档案表 ====================
CREATE TABLE IF NOT EXISTS `employee` (
    `employee_id` VARCHAR(20) NOT NULL,
    `name` VARCHAR(50) NOT NULL,
    `id_number` VARBINARY(128) NOT NULL UNIQUE COMMENT 'AES-256 加密存储',
    `gender` CHAR(1) NOT NULL CHECK (gender IN ('M','F')),
    `birth_date` DATE NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `email` VARCHAR(100) DEFAULT NULL UNIQUE,
    `dept_id` VARCHAR(20) DEFAULT NULL,
    `position_id` VARCHAR(20) DEFAULT NULL,
    `hire_date` DATE NOT NULL,
    `leave_date` DATE DEFAULT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT '在职' CHECK (status IN ('在职','试用期','停薪留职','离职')),
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`employee_id`),
    KEY `idx_dept_id` (`dept_id`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_emp_dept` FOREIGN KEY (`dept_id`) REFERENCES `department`(`dept_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 薪资档案表 ====================
CREATE TABLE IF NOT EXISTS `employee_pay_profile` (
    `employee_id` VARCHAR(20) NOT NULL,
    `base_pay` DECIMAL(10,2) NOT NULL,
    `position_allowance` DECIMAL(10,2) DEFAULT 0,
    `other_allowances` DECIMAL(10,2) DEFAULT 0,
    `social_security_base` DECIMAL(10,2) DEFAULT NULL,
    `housing_fund_base` DECIMAL(10,2) DEFAULT NULL,
    `tax_deduction_items` JSON DEFAULT NULL,
    `version` INT NOT NULL DEFAULT 0,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`employee_id`),
    CONSTRAINT `fk_epp_emp` FOREIGN KEY (`employee_id`) REFERENCES `employee`(`employee_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== 审计日志表 (不可删除) ====================
CREATE TABLE IF NOT EXISTS `audit_log` (
    `log_id` BIGINT NOT NULL AUTO_INCREMENT,
    `operated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `operator_id` VARCHAR(20) NOT NULL,
    `operator_name` VARCHAR(50) NOT NULL,
    `operator_ip` VARCHAR(45) NOT NULL,
    `operation_type` ENUM('新增','修改','删除','查看','导出','登录','登出','Auto-Agent调用') NOT NULL,
    `operation_module` VARCHAR(50) NOT NULL,
    `target_id` VARCHAR(50) DEFAULT NULL,
    `target_name` VARCHAR(100) DEFAULT NULL,
    `before_snapshot` JSON DEFAULT NULL,
    `after_snapshot` JSON DEFAULT NULL,
    `result` ENUM('成功','失败') NOT NULL,
    `duration_ms` INT DEFAULT NULL,
    PRIMARY KEY (`log_id`),
    KEY `idx_operated_at` (`operated_at`),
    KEY `idx_operator` (`operator_id`),
    KEY `idx_module` (`operation_module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
