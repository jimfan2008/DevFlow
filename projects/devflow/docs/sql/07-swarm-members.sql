-- ============================================================
-- DevFlow DATABASE V21 - 蜂群-成员关联表
-- File: 07-swarm-members.sql
-- ============================================================

-- ============================================================
-- 蜂群-成员关联表
-- ============================================================
CREATE TABLE swarm_members (
    id SERIAL PRIMARY KEY,
    swarm_id INTEGER NOT NULL REFERENCES swarms(id) ON DELETE CASCADE,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    registered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- V20/V21 修正：改用 swarm_member_status 枚举类型，消除与原 swarm_status 枚举的语义歧义
    status swarm_member_status NOT NULL DEFAULT 'active',
    skills JSONB,
    UNIQUE(swarm_id, agent_id)
);

-- 索引
CREATE INDEX idx_swarm_members_swarm ON swarm_members(swarm_id);
CREATE INDEX idx_swarm_members_agent ON swarm_members(agent_id);
