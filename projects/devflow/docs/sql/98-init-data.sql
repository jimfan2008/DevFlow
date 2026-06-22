-- ============================================================
-- DevFlow DATABASE V19 - 初始化数据
-- File: 98-init-data.sql
-- Source: section 2.24 of devflow_DATABASE_V16.md
-- ============================================================

-- 9个命名Agent已在 05-agents.sql 中初始化
-- api_endpoint由应用层在首次启动时从环境变量或配置文件写入，不硬编码在DDL脚本中

-- 注意：实际密码应使用bcrypt哈希
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@devflow.local', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iVJQZr3uVILE6WQeO', 'system_admin');
