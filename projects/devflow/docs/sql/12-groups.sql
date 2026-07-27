-- ============================================================
-- DevFlow DATABASE V37 - 群组表
-- File: 12-groups.sql
-- Source: section 2.10 of devflow_DATABASE_V16.md
-- V29: 移除 project_id UNIQUE 约束，支持一个项目多个讨论群（1:N）
-- ============================================================

-- ============================================================
-- 群组表（项目讨论群，与 project 1:N，V29 修正）
-- ============================================================
CREATE TABLE IF NOT EXISTS groups (
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
CREATE INDEX IF NOT EXISTS idx_groups_project ON groups(project_id);
CREATE INDEX IF NOT EXISTS idx_groups_mode ON groups(mode);

-- 触发器
CREATE TRIGGER IF NOT EXISTS update_groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V37 新增：表注释
COMMENT ON TABLE groups IS '群组表 - 项目讨论群，与 project 1:N 关系';
-- V37 新增：字段注释
COMMENT ON COLUMN groups.id IS '群组唯一标识';
COMMENT ON COLUMN groups.project_id IS '所属项目 ID';
COMMENT ON COLUMN groups.name IS '群组名称';
COMMENT ON COLUMN groups.mode IS '群组模式（discussion/meeting）';
COMMENT ON COLUMN groups.host_agent_id IS '主持人 Agent ID';
COMMENT ON COLUMN groups.deleted_at IS '软删除时间戳';
