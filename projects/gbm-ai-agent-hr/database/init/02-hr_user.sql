-- GBM AI Agent HR - hr_user Schema DDL
-- Based on DATABASE_V19 design document
-- Contains: employee, organization, auth tables

USE hr_user;

-- ============================================
-- Department table
-- ============================================
CREATE TABLE dept (
    dept_id VARCHAR(20) NOT NULL COMMENT '部门ID',
    dept_name VARCHAR(100) NOT NULL COMMENT '部门名称',
    parent_id VARCHAR(20) DEFAULT NULL COMMENT '上级部门ID',
    sort_order INT DEFAULT 0 COMMENT '排序号',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/inactive',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (dept_id),
    KEY idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部门表';

-- ============================================
-- Position table
-- ============================================
CREATE TABLE job_position (
    position_id VARCHAR(20) NOT NULL COMMENT '岗位ID',
    position_name VARCHAR(100) NOT NULL COMMENT '岗位名称',
    dept_id VARCHAR(20) DEFAULT NULL COMMENT '所属部门',
    level VARCHAR(20) DEFAULT NULL COMMENT '职级',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (position_id),
    KEY idx_dept_id (dept_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位表';

-- ============================================
-- Employee base info
-- ============================================
CREATE TABLE employee_base (
    employee_id VARCHAR(20) NOT NULL COMMENT '工号',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    id_number VARCHAR(18) NOT NULL COMMENT '身份证号（加密存储）',
    gender CHAR(1) NOT NULL COMMENT '性别: M/F',
    birth_date DATE NOT NULL COMMENT '出生日期',
    phone VARCHAR(20) NOT NULL COMMENT '手机号码',
    email VARCHAR(100) DEFAULT NULL COMMENT '电子邮箱',
    dept_id VARCHAR(20) DEFAULT NULL COMMENT '所属部门',
    position_id VARCHAR(20) DEFAULT NULL COMMENT '现任岗位',
    hire_date DATE NOT NULL COMMENT '入职日期',
    leave_date DATE DEFAULT NULL COMMENT '离职日期',
    status VARCHAR(20) NOT NULL COMMENT '状态: 在职/试用期/停薪留职/离职',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id),
    UNIQUE KEY uk_id_number (id_number),
    KEY idx_dept_id (dept_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工基本信息表';

-- ============================================
-- Employee job info
-- ============================================
CREATE TABLE employee_job (
    employee_id VARCHAR(20) NOT NULL,
    contract_start DATE NOT NULL COMMENT '合同开始日期',
    contract_end DATE DEFAULT NULL COMMENT '合同结束日期',
    probation_end DATE DEFAULT NULL COMMENT '试用期结束日期',
    employment_type VARCHAR(20) DEFAULT NULL COMMENT '用工类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id),
    CONSTRAINT fk_emp_job_base FOREIGN KEY (employee_id) REFERENCES employee_base(employee_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工任职信息表';

-- ============================================
-- Employee pay profile
-- ============================================
CREATE TABLE employee_pay_profile (
    employee_id VARCHAR(20) NOT NULL,
    base_salary DECIMAL(10,2) NOT NULL COMMENT '基本工资',
    position_allowance DECIMAL(10,2) DEFAULT 0 COMMENT '岗位津贴',
    subsidy_amount DECIMAL(10,2) DEFAULT 0 COMMENT '补贴金额',
    social_base DECIMAL(10,2) DEFAULT NULL COMMENT '社保缴费基数',
    fund_base DECIMAL(10,2) DEFAULT NULL COMMENT '公积金缴费基数',
    version INT DEFAULT 0 COMMENT '乐观锁版本号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id),
    CONSTRAINT fk_emp_pay_base FOREIGN KEY (employee_id) REFERENCES employee_base(employee_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工薪资档案';

-- ============================================
-- Employee bank account
-- ============================================
CREATE TABLE employee_bank (
    employee_id VARCHAR(20) NOT NULL,
    bank_name VARCHAR(100) NOT NULL COMMENT '开户银行',
    bank_account VARCHAR(50) NOT NULL COMMENT '银行账号',
    account_name VARCHAR(50) NOT NULL COMMENT '账户姓名',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id),
    CONSTRAINT fk_emp_bank_base FOREIGN KEY (employee_id) REFERENCES employee_base(employee_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工银行信息表';

-- ============================================
-- System user (for RBAC)
-- ============================================
CREATE TABLE sys_user (
    user_id VARCHAR(20) NOT NULL COMMENT '用户ID',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    employee_id VARCHAR(20) DEFAULT NULL COMMENT '关联员工',
    real_name VARCHAR(50) DEFAULT NULL COMMENT '真实姓名',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    status VARCHAR(20) DEFAULT 'enabled' COMMENT '状态: enabled/disabled/locked',
    mfa_enabled BOOLEAN DEFAULT FALSE COMMENT '是否启用MFA',
    last_login_at TIMESTAMP DEFAULT NULL COMMENT '最后登录时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_username (username),
    KEY idx_employee_id (employee_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- ============================================
-- System role
-- ============================================
CREATE TABLE sys_role (
    role_id VARCHAR(20) NOT NULL COMMENT '角色ID',
    role_name VARCHAR(50) NOT NULL COMMENT '角色名称',
    role_code VARCHAR(50) NOT NULL COMMENT '角色编码',
    role_type ENUM('系统','管理','个人','普通员工') DEFAULT '普通员工' COMMENT '角色类型',
    description VARCHAR(255) DEFAULT NULL COMMENT '角色描述',
    status VARCHAR(20) DEFAULT 'enabled' COMMENT '状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id),
    UNIQUE KEY uk_role_code (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统角色表';

-- ============================================
-- System permission
-- ============================================
CREATE TABLE sys_permission (
    perm_id VARCHAR(20) NOT NULL COMMENT '权限ID',
    perm_name VARCHAR(100) NOT NULL COMMENT '权限名称',
    perm_code VARCHAR(100) NOT NULL COMMENT '权限编码',
    resource_type ENUM('menu','button','api') DEFAULT 'menu' COMMENT '资源类型',
    action VARCHAR(50) DEFAULT NULL COMMENT '操作',
    parent_id VARCHAR(20) DEFAULT NULL COMMENT '上级权限',
    sort_order INT DEFAULT 0 COMMENT '排序号',
    path VARCHAR(255) DEFAULT NULL COMMENT '路由路径',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (perm_id),
    UNIQUE KEY uk_perm_code (perm_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统权限表';

-- ============================================
-- User-Role mapping
-- ============================================
CREATE TABLE sys_user_role (
    user_id VARCHAR(20) NOT NULL,
    role_id VARCHAR(20) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES sys_user(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- ============================================
-- Role-Permission mapping
-- ============================================
CREATE TABLE sys_role_permission (
    role_id VARCHAR(20) NOT NULL,
    perm_id VARCHAR(20) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, perm_id),
    CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES sys_role(role_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_rp_perm FOREIGN KEY (perm_id) REFERENCES sys_permission(perm_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';

-- ============================================
-- Audit log (immutable, >= 10 years)
-- ============================================
CREATE TABLE audit_log (
    log_id VARCHAR(32) NOT NULL COMMENT '日志ID (UUID)',
    operation_time DATETIME NOT NULL COMMENT '操作时间',
    operator_user VARCHAR(50) NOT NULL COMMENT '操作人账号',
    operator_name VARCHAR(50) NOT NULL COMMENT '操作人姓名',
    operator_ip VARCHAR(45) NOT NULL COMMENT '操作IP',
    operation_type ENUM('新增','修改','删除','查看','导出','登录','登出','Auto-Agent调用') NOT NULL,
    operation_module VARCHAR(50) NOT NULL COMMENT '操作模块',
    operation_target VARCHAR(200) DEFAULT NULL COMMENT '操作对象',
    before_snapshot JSON DEFAULT NULL COMMENT '变更前快照',
    after_snapshot JSON DEFAULT NULL COMMENT '变更后快照',
    result VARCHAR(20) NOT NULL COMMENT '结果: 成功/失败',
    duration_ms BIGINT DEFAULT NULL COMMENT '耗时(毫秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    KEY idx_operation_time (operation_time),
    KEY idx_operator_user (operator_user),
    KEY idx_operation_module (operation_module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表（不可删除）';

-- ============================================
-- Initial data
-- ============================================
INSERT INTO sys_role (role_id, role_name, role_code, role_type, description) VALUES
('ROLE-001', '系统管理员', 'SYS_ADMIN', '系统', '系统基础设施运维和技术管理'),
('ROLE-002', '人事专员', 'HR_SPECIALIST', '管理', 'HR流程监督者与审核人'),
('ROLE-003', '部门主管', 'DEPT_MANAGER', '管理', '业务决策审批人'),
('ROLE-004', '外务专员', 'EXTERNAL_SPECIALIST', '管理', '政务联络协调人'),
('ROLE-005', '在职员工', 'EMPLOYEE', '个人', '自助信息查询者'),
('ROLE-006', '新员工', 'NEW_EMPLOYEE', '普通员工', '信息提供者');
