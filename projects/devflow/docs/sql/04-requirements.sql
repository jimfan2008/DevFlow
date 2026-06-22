-- ============================================================
-- DevFlow DATABASE V19
-- File: 04-requirements.sql
-- Source: section 2.4 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 需求表（软件需求说明书）
-- ============================================================
CREATE TABLE requirements (
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
CREATE INDEX idx_requirements_project ON requirements(project_id);
-- 联合唯一索引：同一项目的同一版本唯一
CREATE UNIQUE INDEX idx_requirements_project_version ON requirements(project_id, version);

-- 触发器
CREATE TRIGGER update_requirements_updated_at
    BEFORE UPDATE ON requirements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
