-- ============================================================
-- DevFlow DATABASE V37 - 权限设置
-- File: 97-permissions.sql
-- Source: section 2.23 of devflow_DATABASE_V16.md
-- ============================================================

-- 创建应用用户
-- CREATE USER devflow_app WITH PASSWORD 'secure_password';
-- GRANT CONNECT ON DATABASE devflow_db TO devflow_app;
-- GRANT USAGE ON SCHEMA public TO devflow_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO devflow_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO devflow_app;

-- 创建只读用户（用于报表和监控）
-- CREATE USER devflow_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE devflow_db TO devflow_readonly;
-- GRANT USAGE ON SCHEMA public TO devflow_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO devflow_readonly;
