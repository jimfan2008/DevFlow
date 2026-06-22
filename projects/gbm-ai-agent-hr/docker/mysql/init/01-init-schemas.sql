-- GBM AI Agent HR - MySQL Initialization Scripts
-- Creates 4 schemas: hr_user, hr_recruit, hr_payroll, hr_auto

-- Create schemas
CREATE DATABASE IF NOT EXISTS hr_user
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS hr_recruit
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS hr_payroll
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS hr_auto
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create Keycloak database
CREATE DATABASE IF NOT EXISTS keycloak_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Grant privileges
GRANT ALL PRIVILEGES ON hr_user.* TO 'hr_admin'@'%' IDENTIFIED BY 'hr_admin_password';
GRANT ALL PRIVILEGES ON hr_recruit.* TO 'hr_admin'@'%' IDENTIFIED BY 'hr_admin_password';
GRANT ALL PRIVILEGES ON hr_payroll.* TO 'hr_admin'@'%' IDENTIFIED BY 'hr_admin_password';
GRANT ALL PRIVILEGES ON hr_auto.* TO 'hr_admin'@'%' IDENTIFIED BY 'hr_admin_password';
GRANT ALL PRIVILEGES ON keycloak_db.* TO 'hr_admin'@'%' IDENTIFIED BY 'hr_admin_password';
FLUSH PRIVILEGES;
