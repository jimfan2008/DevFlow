-- ============================================================
-- DevFlow DATABASE V37
-- File: 04-requirements.sql
-- Source: section 2.4 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 需求表（软件需求说明书）
-- ============================================================
CREATE TABLE IF NOT EXISTS requirements (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_requirements_project ON requirements(project_id);
-- 联合唯一索引：同一项目的同一版本唯一
CREATE UNIQUE INDEX IF NOT EXISTS idx_requirements_project_version ON requirements(project_id, version);

-- 触发器
CREATE TRIGGER IF NOT EXISTS update_requirements_updated_at
    BEFORE UPDATE ON requirements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V37 新增：表注释
COMMENT ON TABLE requirements IS '需求表 - 存储软件需求说明书，(project_id, version) 唯一约束';
-- V37 新增：字段注释
COMMENT ON COLUMN requirements.id IS '需求唯一标识';
COMMENT ON COLUMN requirements.project_id IS '所属项目 ID';
COMMENT ON COLUMN requirements.content IS '需求说明书内容';
COMMENT ON COLUMN requirements.version IS '版本号';
COMMENT ON COLUMN requirements.is_locked IS '是否锁定';
