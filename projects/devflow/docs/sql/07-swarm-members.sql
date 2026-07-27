-- ============================================================
-- DevFlow DATABASE V37 - 蜂群-成员关联表
-- File: 07-swarm-members.sql
-- ============================================================

-- ============================================================
-- 蜂群-成员关联表
-- ============================================================
CREATE TABLE IF NOT EXISTS swarm_members (
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
CREATE INDEX IF NOT EXISTS idx_swarm_members_swarm ON swarm_members(swarm_id);
CREATE INDEX IF NOT EXISTS idx_swarm_members_agent ON swarm_members(agent_id);

-- V37 新增：表注释
COMMENT ON TABLE swarm_members IS '蜂群成员表 - 蜂群与 Agent 的关联表';
-- V37 新增：字段注释
COMMENT ON COLUMN swarm_members.id IS '成员记录唯一标识';
COMMENT ON COLUMN swarm_members.swarm_id IS '所属蜂群 ID';
COMMENT ON COLUMN swarm_members.agent_id IS 'Agent ID';
COMMENT ON COLUMN swarm_members.status IS '成员状态（active/inactive/removed）';
COMMENT ON COLUMN swarm_members.skills IS '技能描述（JSONB）';
