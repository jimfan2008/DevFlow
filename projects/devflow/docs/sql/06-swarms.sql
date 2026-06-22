-- ============================================================
-- DevFlow DATABASE V34 - Agent蜂群表
-- File: 06-swarms.sql
-- ============================================================

-- ============================================================
-- Agent蜂群表
-- V28 修正：添加 step_number 字段以匹配后端 SwarmOut schema
-- V34 修正：manager_agent_id 恢复为 NOT NULL，移除 ON DELETE SET NULL（与后端 V40 §5.2.11 对齐）
-- ============================================================
CREATE TABLE swarms (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    -- V34 修正：从 V33 的 NULLABLE ON DELETE SET NULL 恢复为 NOT NULL（默认 NO ACTION）
    manager_agent_id INTEGER NOT NULL REFERENCES agents(id),
    purpose swarm_purpose NOT NULL,
    step_number INTEGER NOT NULL DEFAULT 1,
    CHECK (step_number >= 1 AND step_number <= 16),
    status swarm_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dissolved_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_swarms_project ON swarms(project_id);
CREATE INDEX idx_swarms_manager ON swarms(manager_agent_id);
CREATE INDEX idx_swarms_status ON swarms(status);

-- 触发器
CREATE TRIGGER update_swarms_updated_at
    BEFORE UPDATE ON swarms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 管理器自动注册为 swarm_members 的约束
CREATE OR REPLACE FUNCTION ensure_manager_in_swarm_members()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO swarm_members (swarm_id, agent_id, status)
    VALUES (NEW.id, NEW.manager_agent_id, 'active')
    ON CONFLICT (swarm_id, agent_id) DO NOTHING;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER auto_add_manager_to_members
    AFTER INSERT ON swarms
    FOR EACH ROW
    EXECUTE FUNCTION ensure_manager_in_swarm_members();
