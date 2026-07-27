-- ============================================================
-- DevFlow DATABASE V37 - 项目成员表
-- File: 24-project-members.sql
-- V33 新增：与后端 V37 §5.1 ER 图对齐
-- V34 修正：移除 agent_id 字段，仅保留 user_id NOT NULL（与后端 V40 §5.2.20 对齐）
-- V37 修正：恢复 agent_id 字段、member_type 字段及相关约束，与后端 V44 §4.12 对齐
-- ============================================================

-- ============================================================
-- 项目成员表
-- V37 修正：恢复 user_id/agent_id 双成员模式 + member_type 字段
-- 与 projects 表 1:N 关系，记录项目的用户和 Agent 成员
-- ============================================================
CREATE TABLE IF NOT EXISTS project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    -- V37 修正：恢复 member_type 字段，支持 user/agent 双成员模式
    member_type VARCHAR(20) NOT NULL CHECK (member_type IN ('user', 'agent')),
    -- V37 修正：恢复 user_id 和 agent_id 字段，均为 NULLABLE
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    CONSTRAINT check_project_member_type CHECK (
        (member_type = 'user' AND user_id IS NOT NULL AND agent_id IS NULL) OR
        (member_type = 'agent' AND agent_id IS NOT NULL AND user_id IS NULL)
    ),
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_project_members_project ON project_members(project_id);
CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members(user_id);
CREATE INDEX IF NOT EXISTS idx_project_members_agent ON project_members(agent_id);
CREATE INDEX IF NOT EXISTS idx_project_members_type ON project_members(member_type);
-- 部分唯一索引：同项目同成员不重复
CREATE UNIQUE INDEX IF NOT EXISTS uq_project_members_user
    ON project_members(project_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_project_members_agent
    ON project_members(project_id, agent_id) WHERE agent_id IS NOT NULL;

-- V37 新增：表注释
COMMENT ON TABLE project_members IS '项目成员表 - 项目与用户/Agent 的关联关系，支持双成员模式';
-- V37 新增：字段注释
COMMENT ON COLUMN project_members.id IS '成员记录唯一标识';
COMMENT ON COLUMN project_members.project_id IS '所属项目 ID';
COMMENT ON COLUMN project_members.member_type IS '成员类型（user/agent）';
COMMENT ON COLUMN project_members.user_id IS '用户 ID（member_type=user 时必填）';
COMMENT ON COLUMN project_members.agent_id IS 'Agent ID（member_type=agent 时必填）';
COMMENT ON COLUMN project_members.role IS '在项目中的角色';
