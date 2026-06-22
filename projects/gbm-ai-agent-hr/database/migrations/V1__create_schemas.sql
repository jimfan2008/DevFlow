-- V1__create_schemas.sql
-- 创建 4 个独立 schema + Keycloak schema
CREATE DATABASE IF NOT EXISTS `hr_user` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `hr_recruit` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `hr_payroll` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `hr_auto` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `keycloak` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建应用用户 (请根据实际情况调整密码)
CREATE USER IF NOT EXISTS 'hr_admin'@'%' IDENTIFIED BY 'gbm_hr_admin_2026';
GRANT ALL PRIVILEGES ON `hr_user`.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON `hr_recruit`.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON `hr_payroll`.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON `hr_auto`.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON `keycloak`.* TO 'hr_admin'@'%';
FLUSH PRIVILEGES;
