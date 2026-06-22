-- hr_user schema - Employee & User management tables
USE hr_user;

-- 员工基础信息表
CREATE TABLE IF NOT EXISTS employee_base (
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
    leave_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT '在职',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dept (dept_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 员工薪资档案表
CREATE TABLE IF NOT EXISTS employee_pay_profile (
    profile_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    base_pay DECIMAL(10,2) NOT NULL,
    position_allowance DECIMAL(10,2) DEFAULT 0,
    subsidy_total DECIMAL(10,2) DEFAULT 0,
    performance_base DECIMAL(10,2) DEFAULT 0,
    version INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee_base(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 部门表
CREATE TABLE IF NOT EXISTS department (
    dept_id VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    parent_id VARCHAR(20),
    level INT DEFAULT 1,
    manager_id VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 岗位表
CREATE TABLE IF NOT EXISTS job_position (
    position_id VARCHAR(20) PRIMARY KEY,
    position_name VARCHAR(100) NOT NULL,
    dept_id VARCHAR(20),
    level VARCHAR(20),
    description TEXT,
    requirements TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 系统用户表
CREATE TABLE IF NOT EXISTS sys_user (
    user_id VARCHAR(20) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    employee_id VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 角色表
CREATE TABLE IF NOT EXISTS sys_role (
    role_id VARCHAR(20) PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL,
    role_type VARCHAR(20) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS sys_user_role (
    user_id VARCHAR(20) NOT NULL,
    role_id VARCHAR(20) NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES sys_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 权限表
CREATE TABLE IF NOT EXISTS sys_permission (
    permission_id VARCHAR(20) PRIMARY KEY,
    permission_name VARCHAR(100) NOT NULL,
    resource_type VARCHAR(20) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 角色权限关联表
CREATE TABLE IF NOT EXISTS sys_role_permission (
    role_id VARCHAR(20) NOT NULL,
    permission_id VARCHAR(20) NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES sys_permission(permission_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 证书台账表
CREATE TABLE IF NOT EXISTS certificate_registry (
    cert_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    cert_type VARCHAR(50) NOT NULL,
    cert_number VARCHAR(100),
    issue_date DATE,
    expiry_date DATE,
    issuing_authority VARCHAR(200),
    status VARCHAR(20) DEFAULT 'valid',
    file_uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee_base(employee_id) ON DELETE CASCADE,
    INDEX idx_expiry (expiry_date),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 人脸特征表
CREATE TABLE IF NOT EXISTS face_feature (
    face_id VARCHAR(20) PRIMARY KEY,
    employee_id VARCHAR(20) NOT NULL,
    face_data VARBINARY(1024) NOT NULL,
    quality_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employee_base(employee_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_log (
    log_id VARCHAR(32) PRIMARY KEY,
    operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operator_id VARCHAR(20),
    operator_name VARCHAR(50),
    operator_ip VARCHAR(45),
    operation_type VARCHAR(20) NOT NULL,
    module VARCHAR(50) NOT NULL,
    target_id VARCHAR(50),
    target_name VARCHAR(100),
    before_snapshot JSON,
    after_snapshot JSON,
    result VARCHAR(20),
    duration_ms BIGINT,
    INDEX idx_time (operation_time),
    INDEX idx_operator (operator_id),
    INDEX idx_module (module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
