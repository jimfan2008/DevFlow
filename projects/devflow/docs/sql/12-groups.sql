-- ============================================================
-- DevFlow DATABASE V29 - 群组表
-- File: 12-groups.sql
-- Source: section 2.10 of devflow_DATABASE_V16.md
-- V29: 移除 project_id UNIQUE 约束，支持一个项目多个讨论群（1:N）
-- ============================================================

-- ============================================================
-- 群组表（项目讨论群，与 project 1:N，V29 修正）
-- ============================================================
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    mode group_mode NOT NULL DEFAULT 'discussion',
    host_agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_groups_project ON groups(project_id);
CREATE INDEX idx_groups_mode ON groups(mode);

-- 触发器
CREATE TRIGGER update_groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
