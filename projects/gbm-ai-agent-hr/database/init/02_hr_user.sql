-- ============================================
-- GBM AI Agent HR - hr_user Schema 表结构
-- ============================================
-- 域服务: user-domain (端口 8081)
-- 包含: 员工管理、系统用户、角色权限、审计日志、人脸库

USE hr_user;

-- 1. 系统用户表
CREATE TABLE IF NOT EXISTS sys_user (
    user_id VARCHAR(20) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    status ENUM('ACTIVE', 'DISABLED', 'LOCKED') NOT NULL DEFAULT 'ACTIVE',
    last_login_at TIMESTAMP NULL,
    failed_login_count INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 角色表
CREATE TABLE IF NOT EXISTS sys_role (
    role_id VARCHAR(20) PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    role_type ENUM('系统管理员', '人事专员', '部门主管', '外务专员', '普通员工') NOT NULL,
    description TEXT,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_role_type (role_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 权限表
CREATE TABLE IF NOT EXISTS sys_permission (
    permission_id VARCHAR(20) PRIMARY KEY,
    permission_name VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    action ENUM('READ', 'WRITE', 'DELETE', 'APPROVE', 'EXPORT') NOT NULL,
    resource VARCHAR(100) NOT NULL,
    description TEXT,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 用户-角色关联表
CREATE TABLE IF NOT EXISTS sys_user_role (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    role_id VARCHAR(20) NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by VARCHAR(20) NULL,
    UNIQUE KEY uk_user_role (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES sys_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 角色-权限关联表
CREATE TABLE IF NOT EXISTS sys_role_permission (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_id VARCHAR(20) NOT NULL,
    permission_id VARCHAR(20) NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_role_perm (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES sys_permission(permission_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 员工档案表
CREATE TABLE IF NOT EXISTS employee (
    employee_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    id_number VARCHAR(18) NOT NULL UNIQUE,
    gender CHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    birth_date DATE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100) UNIQUE,
    dept_id VARCHAR(20),
    position_id VARCHAR(20),
    hire_date DATE NOT NULL,
    leave_date DATE NULL,
    status ENUM('在职', '试用期', '停薪留职', '离职') NOT NULL DEFAULT '试用期',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dept (dept_id),
    INDEX idx_status (status),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 部门表
CREATE TABLE IF NOT EXISTS department (
    dept_id VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    parent_dept_id VARCHAR(20) NULL,
    manager_id VARCHAR(20) NULL,
    level INT NOT NULL DEFAULT 1,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_dept_id),
    FOREIGN KEY (parent_dept_id) REFERENCES department(dept_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 岗位表
CREATE TABLE IF NOT EXISTS job_position (
    position_id VARCHAR(20) PRIMARY KEY,
    position_name VARCHAR(100) NOT NULL,
    dept_id VARCHAR(20),
    level VARCHAR(20),
    description TEXT,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. 员工薪资档案表
CREATE TABLE IF NOT EXISTS employee_pay_profile (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL UNIQUE,
    base_pay DECIMAL(10,2) NOT NULL,
    position_allowance DECIMAL(10,2) DEFAULT 0,
    seniority_allowance DECIMAL(10,2) DEFAULT 0,
    meal_allowance DECIMAL(10,2) DEFAULT 0,
    transport_allowance DECIMAL(10,2) DEFAULT 0,
    ss_base DECIMAL(10,2) NOT NULL,
    gf_base DECIMAL(10,2) NOT NULL,
    effective_date DATE NOT NULL,
    version INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. 员工银行卡信息表
CREATE TABLE IF NOT EXISTS employee_bank (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL UNIQUE,
    bank_name VARCHAR(100) NOT NULL,
    bank_account VARCHAR(50) NOT NULL,
    bank_branch VARCHAR(200),
    is_default TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. 审计日志表 (不可删除)
CREATE TABLE IF NOT EXISTS audit_log (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    operated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    operator_id VARCHAR(20) NOT NULL,
    operator_name VARCHAR(50) NOT NULL,
    operator_ip VARCHAR(45) NOT NULL,
    operation_type ENUM('新增', '修改', '删除', '查看', '导出', '登录', '登出', 'Auto-Agent 调用') NOT NULL,
    module ENUM('招聘', '入职', '培训', '考勤', '薪资', '绩效', '外务', '离职') NOT NULL,
    target_id VARCHAR(50),
    target_name VARCHAR(100),
    before_snapshot JSON NULL,
    after_snapshot JSON NULL,
    result ENUM('成功', '失败') NOT NULL,
    duration_ms INT NOT NULL,
    INDEX idx_operated_at (operated_at),
    INDEX idx_operator (operator_id),
    INDEX idx_module (module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. 人脸库表
CREATE TABLE IF NOT EXISTS face_library (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL UNIQUE,
    face_feature VARBINARY(1024) NOT NULL,
    photo_uri VARCHAR(500),
    quality_score DECIMAL(3,2),
    match_confidence DECIMAL(3,2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'hr_user schema tables created successfully!' AS status;
