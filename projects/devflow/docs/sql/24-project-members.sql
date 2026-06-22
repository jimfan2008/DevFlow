-- ============================================================
-- DevFlow DATABASE V34 - 项目成员表
-- File: 24-project-members.sql
-- V33 新增：与后端 V37 §5.1 ER 图对齐
-- V34 修正：移除 agent_id 字段，仅保留 user_id NOT NULL（与后端 V40 §5.2.20 对齐）
-- ============================================================

-- ============================================================
-- 项目成员表
-- V34 修正：从 user_id/agent_id 双成员模式改为仅 user_id NOT NULL
-- 与 projects 表 1:N 关系，记录项目的用户成员
-- ============================================================
CREATE TABLE project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    -- V34 修正：从 NULLABLE 改为 NOT NULL，移除 agent_id 字段
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);
-- 部分唯一索引：同项目同用户不重复
CREATE UNIQUE INDEX uq_project_members_project_user ON project_members(project_id, user_id);
