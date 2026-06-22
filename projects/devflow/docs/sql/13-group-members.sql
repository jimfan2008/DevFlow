-- ============================================================
-- DevFlow DATABASE V19 - 群成员表
-- File: 13-group-members.sql
-- Source: section 2.11 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 群成员表（V17 修正：ON DELETE SET NULL）
-- ============================================================
CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    member_type member_type NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- user 类型时 user_id 非空，agent 类型时 agent_id 非空
    CHECK (
        (member_type = 'user' AND user_id IS NOT NULL AND agent_id IS NULL) OR
        (member_type = 'agent' AND agent_id IS NOT NULL AND user_id IS NULL)
    ),
    UNIQUE(group_id, user_id) WHERE user_id IS NOT NULL,
    UNIQUE(group_id, agent_id) WHERE agent_id IS NOT NULL
);

-- 索引
CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user_only ON group_members(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_group_members_agent_only ON group_members(agent_id) WHERE agent_id IS NOT NULL;
