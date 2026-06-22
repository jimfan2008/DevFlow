-- GBM AI Agent HR - 初始化基础数据
-- 默认角色、权限、管理员用户

USE hr_user;

-- ==================== 部门初始化 ====================
INSERT INTO `department` (`dept_id`, `dept_name`, `parent_id`, `sort_order`) VALUES
    ('DEPT-001', '总部', NULL, 0),
    ('DEPT-002', '人力资源部', 'DEPT-001', 1),
    ('DEPT-003', '技术部', 'DEPT-001', 2),
    ('DEPT-004', '财务部', 'DEPT-001', 3),
    ('DEPT-005', '行政部', 'DEPT-001', 4);

-- ==================== 角色初始化 ====================
INSERT INTO `sys_role` (`role_id`, `role_name`, `role_type`, `description`) VALUES
    ('ROLE-001', '系统管理员', '系统管理员', '系统基础设施运维和技术管理'),
    ('ROLE-002', '人事专员', '人事专员', 'HR 流程的监督者与审核人'),
    ('ROLE-003', '部门主管', '部门主管', '业务决策审批人'),
    ('ROLE-004', '外务专员', '外务专员', '政务联络协调人'),
    ('ROLE-005', '新员工', '普通员工', '新员工自助信息提供者'),
    ('ROLE-006', '普通员工', '普通员工', '在职员工自助信息查询者');

-- ==================== 权限初始化 ====================
INSERT INTO `sys_permission` (`permission_id`, `resource_type`, `resource_name`, `action`, `path`) VALUES
    -- 系统管理权限
    ('PERM-001', 'menu', '系统管理', 'view', '/admin'),
    ('PERM-002', 'button', '用户管理', 'manage', '/admin/users'),
    ('PERM-003', 'button', '角色管理', 'manage', '/admin/roles'),
    ('PERM-004', 'button', '权限管理', 'manage', '/admin/permissions'),
    ('PERM-005', 'api', '系统配置', 'update', '/api/v1/system/config'),
    ('PERM-006', 'menu', '审计日志', 'view', '/admin/audit'),

    -- 招聘管理权限
    ('PERM-010', 'menu', '招聘管理', 'view', '/recruitment'),
    ('PERM-011', 'button', '岗位管理', 'manage', '/recruitment/positions'),
    ('PERM-012', 'button', '简历管理', 'manage', '/recruitment/resumes'),
    ('PERM-013', 'button', '面试管理', 'manage', '/recruitment/interviews'),
    ('PERM-014', 'api', '简历筛选', 'execute', '/api/v1/resumes/filter'),

    -- 员工管理权限
    ('PERM-020', 'menu', '员工管理', 'view', '/employees'),
    ('PERM-021', 'button', '入职管理', 'manage', '/employees/onboarding'),
    ('PERM-022', 'button', '离职管理', 'manage', '/employees/exit'),
    ('PERM-023', 'api', '员工档案', 'view', '/api/v1/employees'),

    -- 考勤管理权限
    ('PERM-030', 'menu', '考勤管理', 'view', '/attendance'),
    ('PERM-031', 'button', '考勤统计', 'view', '/attendance/stats'),
    ('PERM-032', 'api', '考勤数据', 'view', '/api/v1/attendance'),

    -- 薪资管理权限
    ('PERM-040', 'menu', '薪资管理', 'view', '/payroll'),
    ('PERM-041', 'button', '薪资核算', 'execute', '/payroll/calculation'),
    ('PERM-042', 'button', '工资条管理', 'manage', '/payroll/payslips'),
    ('PERM-043', 'api', '薪资数据', 'view', '/api/v1/payroll'),

    -- 绩效管理权限
    ('PERM-050', 'menu', '绩效管理', 'view', '/performance'),
    ('PERM-051', 'button', '考核管理', 'manage', '/performance/reviews'),
    ('PERM-052', 'api', '绩效数据', 'view', '/api/v1/performance'),

    -- 培训管理权限
    ('PERM-060', 'menu', '培训管理', 'view', '/training'),
    ('PERM-061', 'button', '培训计划', 'manage', '/training/plans'),
    ('PERM-062', 'api', '培训数据', 'view', '/api/v1/training'),

    -- 外务管理权限
    ('PERM-070', 'menu', '外务管理', 'view', '/external'),
    ('PERM-071', 'button', '工伤管理', 'manage', '/external/injury'),
    ('PERM-072', 'button', '公积金管理', 'manage', '/external/housing-fund'),

    -- 自助服务权限
    ('PERM-080', 'menu', '自助服务', 'view', '/self-service'),
    ('PERM-081', 'button', '工资条查看', 'view', '/self-service/payslip'),
    ('PERM-082', 'button', '证明申请', 'apply', '/self-service/certificate'),
    ('PERM-083', 'api', '个人信息', 'view', '/api/v1/me');

-- ==================== 角色权限分配 ====================

-- 系统管理员 - 全部权限
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`)
SELECT 'ROLE-001', permission_id FROM `sys_permission`;

-- 人事专员 - 招聘、员工、考勤、薪资、绩效、培训、自助审核
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
    ('ROLE-002', 'PERM-010'), ('ROLE-002', 'PERM-011'), ('ROLE-002', 'PERM-012'), ('ROLE-002', 'PERM-013'), ('ROLE-002', 'PERM-014'),
    ('ROLE-002', 'PERM-020'), ('ROLE-002', 'PERM-021'), ('ROLE-002', 'PERM-022'), ('ROLE-002', 'PERM-023'),
    ('ROLE-002', 'PERM-030'), ('ROLE-002', 'PERM-031'), ('ROLE-002', 'PERM-032'),
    ('ROLE-002', 'PERM-040'), ('ROLE-002', 'PERM-041'), ('ROLE-002', 'PERM-042'), ('ROLE-002', 'PERM-043'),
    ('ROLE-002', 'PERM-050'), ('ROLE-002', 'PERM-051'), ('ROLE-002', 'PERM-052'),
    ('ROLE-002', 'PERM-060'), ('ROLE-002', 'PERM-061'), ('ROLE-002', 'PERM-062'),
    ('ROLE-002', 'PERM-080'), ('ROLE-002', 'PERM-081'), ('ROLE-002', 'PERM-082'), ('ROLE-002', 'PERM-083');

-- 部门主管 - 考勤、绩效、部门员工查看
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
    ('ROLE-003', 'PERM-020'), ('ROLE-003', 'PERM-023'),
    ('ROLE-003', 'PERM-030'), ('ROLE-003', 'PERM-031'),
    ('ROLE-003', 'PERM-050'), ('ROLE-003', 'PERM-051'), ('ROLE-003', 'PERM-052'),
    ('ROLE-003', 'PERM-060'), ('ROLE-003', 'PERM-062');

-- 外务专员 - 外务管理
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
    ('ROLE-004', 'PERM-070'), ('ROLE-004', 'PERM-071'), ('ROLE-004', 'PERM-072');

-- 新员工/普通员工 - 自助服务
INSERT INTO `sys_role_permission` (`role_id`, `permission_id`) VALUES
    ('ROLE-005', 'PERM-080'), ('ROLE-005', 'PERM-081'), ('ROLE-005', 'PERM-082'), ('ROLE-005', 'PERM-083'),
    ('ROLE-006', 'PERM-080'), ('ROLE-006', 'PERM-081'), ('ROLE-006', 'PERM-082'), ('ROLE-006', 'PERM-083');

-- ==================== 默认管理员用户 ====================
-- 密码: admin123 (BCrypt hash)
INSERT INTO `sys_user` (`user_id`, `username`, `password_hash`, `name`, `email`, `phone`, `status`) VALUES
    ('USER-001', 'admin', '$2b$12$LQ37gEp4zK5kVQK7YxXfMO1JzXQ7VhYqJ7K3rXvVvQKjYhK3rXvVv', '系统管理员', 'admin@gbm-hr.local', '', 'active');

-- 管理员用户关联系统管理员角色
INSERT INTO `sys_user_role` (`user_id`, `role_id`) VALUES
    ('USER-001', 'ROLE-001');
