-- 01-init-dict-data.sql
USE `hr_user`;

INSERT INTO `sys_role` (`role_code`, `role_name`, `role_type`, `description`) VALUES
('ROLE-001', '系统管理员', '系统管理员', '系统基础设施运维和技术管理'),
('ROLE-002', '人事专员', '人事专员', 'HR 流程监督者与审核人'),
('ROLE-003', '部门主管', '部门主管', '业务决策审批人'),
('ROLE-004', '外务专员', '外务专员', '政务联络协调人'),
('ROLE-005', '普通员工', '普通员工', '自助信息查询');
