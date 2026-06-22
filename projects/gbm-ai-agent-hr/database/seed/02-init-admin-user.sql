-- 02-init-admin-user.sql
USE `hr_user`;

-- 初始管理员 (password: admin123, BCrypt hashed)
INSERT INTO `sys_user` (`username`, `password_hash`, `role_ids`, `status`) VALUES
('admin', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'ROLE-001', '活跃');
