-- GBM AI Agent HR - Database Initialization Script
-- Schema: 01-create-schemas.sql
-- Based on DATABASE_V19 design document

-- Create 4 independent schemas
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

-- Create database users and grant privileges
-- Note: In production, use proper password management
CREATE USER IF NOT EXISTS 'hr_admin'@'%' IDENTIFIED BY 'hr_password';
GRANT ALL PRIVILEGES ON hr_user.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON hr_recruit.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON hr_payroll.* TO 'hr_admin'@'%';
GRANT ALL PRIVILEGES ON hr_auto.* TO 'hr_admin'@'%';

-- Create read-only user for reporting
CREATE USER IF NOT EXISTS 'hr_reader'@'%' IDENTIFIED BY 'hr_reader_password';
GRANT SELECT ON hr_user.* TO 'hr_reader'@'%';
GRANT SELECT ON hr_recruit.* TO 'hr_reader'@'%';
GRANT SELECT ON hr_payroll.* TO 'hr_reader'@'%';
GRANT SELECT ON hr_auto.* TO 'hr_reader'@'%';

FLUSH PRIVILEGES;
