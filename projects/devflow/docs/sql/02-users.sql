-- ============================================================
-- DevFlow DATABASE V37
-- File: 02-users.sql
-- Source: section 2.2 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    -- V9 修订：使用 citext 类型，不区分大小写，避免 User@Example.com 和 user@example.com 被视为不同邮箱
    email citext NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
-- email 的 UNIQUE 约束已隐含唯一索引，citext 类型自动处理大小写不敏感比较

-- 更新时间戳触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V37 新增：表注释
COMMENT ON TABLE users IS '用户表 - 存储系统用户信息，支持 citext 不区分大小写的邮箱唯一约束';
-- V37 新增：字段注释
COMMENT ON COLUMN users.id IS '用户唯一标识';
COMMENT ON COLUMN users.username IS '用户名';
COMMENT ON COLUMN users.email IS '邮箱地址（citext 不区分大小写）';
COMMENT ON COLUMN users.password_hash IS '密码哈希值（bcrypt）';
COMMENT ON COLUMN users.role IS '用户角色（user/admin/system_admin）';
COMMENT ON COLUMN users.is_active IS '是否激活';
