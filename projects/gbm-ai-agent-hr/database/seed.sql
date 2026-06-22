-- ============================================
-- GBM AI Agent HR - 数据库种子数据
-- 基于 SRS V15 和 DATABASE_V19 设计
-- 4 个独立 schema: hr_user/hr_recruit/hr_payroll/hr_auto
-- ============================================

USE hr_user;

-- 插入默认系统管理员
INSERT INTO sys_user (user_id, username, password_hash, real_name, email, phone, status) VALUES
('USR001', 'admin', '$2b$12$LQv3c1yamlOGl.2Hx1j5e.K8B2sN4Q5m6P7wX8yZ0aB1cD2eF3gHi', '系统管理员', 'admin@gbm-hr.local', '13800000001', 'active');

-- 插入默认角色
INSERT INTO sys_role (role_id, role_name, role_type, description) VALUES
('ROLE001', '系统管理员', '系统管理员', '系统基础设施运维和技术管理'),
('ROLE002', '人事专员', '人事专员', 'HR 流程监督者与审核人'),
('ROLE003', '部门主管', '部门主管', '业务决策审批人'),
('ROLE004', '外务专员', '外务专员', '政务联络协调人'),
('ROLE005', '普通员工', '普通员工', '在职员工，自助信息查询');

-- 管理员角色分配
INSERT INTO sys_user_role (user_id, role_id) VALUES
('USR001', 'ROLE001');

-- 插入默认部门
INSERT INTO department (dept_id, dept_name, parent_id, level, sort_order) VALUES
('DEPT001', 'GBM 集团总部', NULL, 1, 1),
('DEPT002', '人力资源部', 'DEPT001', 2, 10),
('DEPT003', '技术研发部', 'DEPT001', 2, 20),
('DEPT004', '生产制造部', 'DEPT001', 2, 30),
('DEPT005', '品质管理部', 'DEPT001', 2, 40),
('DEPT006', '行政管理部', 'DEPT001', 2, 50);

-- 插入默认岗位
INSERT INTO job_position (position_id, position_name, dept_id, level, base_salary_min, base_salary_max, status) VALUES
('POS001', '人力资源总监', 'DEPT002', '总监', 25000, 40000, 'active'),
('POS002', '人事专员', 'DEPT002', '专员', 8000, 15000, 'active'),
('POS003', '技术研发经理', 'DEPT003', '经理', 20000, 35000, 'active'),
('POS004', '品质经理', 'DEPT004', '经理', 18000, 30000, 'active');

-- ============================================
-- hr_recruit schema
-- ============================================

USE hr_recruit;

-- 插入默认岗位类型
INSERT INTO position_category (category_id, category_name, description) VALUES
('CAT001', '技术类', '研发、IT、工程技术'),
('CAT002', '管理类', '管理、行政、运营'),
('CAT003', '生产类', '生产制造、品质管理'),
('CAT004', '销售类', '销售、市场、客服');

-- 插入默认考试科目
INSERT INTO exam_subject (subject_id, subject_name, category) VALUES
('SUB001', '通用知识', '通用'),
('SUB002', '专业技能', '专业'),
('SUB003', '管理能力', '管理'),
('SUB004', '安全规范', '安全');

-- 插入默认培训计划模板
INSERT INTO training_template (template_id, template_name, category, duration_minutes) VALUES
('TPL001', '新员工入职培训', '入职培训', 240),
('TPL002', '安全生产培训', '安全培训', 120),
('TPL003', '岗位技能培训', '岗位培训', 180);

-- ============================================
-- hr_payroll schema
-- ============================================

USE hr_payroll;

-- 插入默认薪资规则
INSERT INTO salary_rule (rule_id, rule_name, rule_type, formula, effective_date, status) VALUES
('RULE001', '平日加班系数', 'overtime', '1.5', '2026-01-01', 'active'),
('RULE002', '周末加班系数', 'overtime', '2.0', '2026-01-01', 'active'),
('RULE003', '法定节假日加班系数', 'overtime', '3.0', '2026-01-01', 'active'),
('RULE004', '迟到扣款标准', 'attendance', '50 per occurrence', '2026-01-01', 'active');

-- 插入默认社保规则
INSERT INTO social_security_rule (rule_id, insurance_type, employee_ratio, company_ratio, effective_date, status) VALUES
('SS001', '养老保险', 0.08, 0.16, '2026-01-01', 'active'),
('SS002', '医疗保险', 0.02, 0.10, '2026-01-01', 'active'),
('SS003', '失业保险', 0.005, 0.005, '2026-01-01', 'active'),
('SS004', '工伤保险', 0.00, 0.004, '2026-01-01', 'active'),
('SS005', '生育保险', 0.00, 0.008, '2026-01-01', 'active');

-- 插入默认公积金规则
INSERT INTO housing_fund_rule (rule_id, fund_type, employee_ratio, company_ratio, effective_date, status) VALUES
('HF001', '住房公积金', 0.08, 0.08, '2026-01-01', 'active');

-- 插入默认班次
INSERT INTO shift_config (shift_id, shift_name, start_time, end_time, break_hours, shift_type) VALUES
('SHIFT001', '早班', '08:00:00', '17:00:00', 1, '标准班'),
('SHIFT002', '中班', '16:00:00', '01:00:00', 1, '中班'),
('SHIFT003', '夜班', '01:00:00', '09:00:00', 1, '夜班');

-- ============================================
-- hr_auto schema
-- ============================================

USE hr_auto;

-- 插入默认报告模板
INSERT INTO report_template (template_id, template_name, report_type, content_format) VALUES
('RPT001', '月度人力分析报告', 'monthly', 'JSON'),
('RPT002', '季度培训总结', 'quarterly', 'PDF'),
('RPT003', '年度绩效汇总', 'yearly', 'Excel');

-- 插入默认证书类型
INSERT INTO certificate_type (type_id, type_name, category, validity_months, renewal_advance_days) VALUES
('CERT001', '特种作业操作证', '特种作业', 60, 90),
('CERT002', '上岗证', '内部', 12, 30),
('CERT003', '安全生产培训合格证', '安全培训', 36, 60);

-- 插入默认外务申报类型
INSERT INTO external_affairs_type (type_id, type_name, category, target_system, rpa_enabled) VALUES
('EA001', '工伤申报', '工伤', '社保系统', true),
('EA002', '公积金开户', '公积金', '住房公积金网站', true),
('EA003', '公积金减员封存', '公积金', '住房公积金网站', true),
('EA004', '社保参保登记', '社保', '社保系统', true);

-- 插入系统配置
INSERT INTO sys_config (config_key, config_value, config_group, description) VALUES
('hr.recruit.resume_expire_days', '1095', 'recruit', '简历保存期限 3 年'),
('hr.payroll.auto_calculate_day', '25', 'payroll', '每月薪资核算触发日'),
('hr.attendance.overtime_max_hours', '36', 'attendance', '每月加班上限 (劳动法规定)'),
('hr.cert.renewal_advance_days', '60', 'certificate', '证书到期提前提醒天数'),
('hr.ai.resume_pass_score', '60', 'recruit', '简历合格线默认值'),
('hr.ai.interview_pass_base', '30', 'recruit', '面试转化率初始基线 (%)');
