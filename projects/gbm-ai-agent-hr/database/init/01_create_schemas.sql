-- ============================================
-- GBM AI Agent HR - 数据库 Schema 初始化
-- ============================================
-- 执行顺序: 01_create_schemas.sql → 02-hr_user.sql → 03-hr_recruit.sql → 04-hr_payroll.sql → 05-hr_auto.sql
-- 数据库: MySQL 8.0+ (InnoDB)
-- 字符集: utf8mb4 / utf8mb4_unicode_ci

-- 创建数据库用户
CREATE USER IF NOT EXISTS 'hr_admin'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'hr_admin'@'%' WITH GRANT OPTION;

-- 创建 4 个独立 schema
CREATE SCHEMA IF NOT EXISTS `hr_user` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE SCHEMA IF NOT EXISTS `hr_recruit` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE SCHEMA IF NOT EXISTS `hr_payroll` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE SCHEMA IF NOT EXISTS `hr_auto` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 授予权限
GRANT ALL PRIVILEGES ON `hr_user`.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON `hr_recruit`.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON `hr_payroll`.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON `hr_auto`.* TO 'hr_admin'@'%';

FLUSH PRIVILEGES;

SELECT 'Database schemas created successfully!' AS status;
