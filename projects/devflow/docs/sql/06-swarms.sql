-- ============================================================
-- DevFlow DATABASE V37 - Agent蜂群表
-- File: 06-swarms.sql
-- ============================================================

-- ============================================================
-- Agent蜂群表
-- V28 修正：添加 step_number 字段以匹配后端 SwarmOut schema
-- V34 修正：manager_agent_id 恢复为 NOT NULL，移除 ON DELETE SET NULL（与后端 V40 §5.2.11 对齐）
-- ============================================================
CREATE TABLE IF NOT EXISTS swarms (
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
CREATE INDEX IF NOT EXISTS idx_swarms_project ON swarms(project_id);
CREATE INDEX IF NOT EXISTS idx_swarms_manager ON swarms(manager_agent_id);
CREATE INDEX IF NOT EXISTS idx_swarms_status ON swarms(status);

-- 触发器
CREATE TRIGGER IF NOT EXISTS update_swarms_updated_at
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

CREATE TRIGGER IF NOT EXISTS auto_add_manager_to_members
    AFTER INSERT ON swarms
    FOR EACH ROW
    EXECUTE FUNCTION ensure_manager_in_swarm_members();

-- V37 新增：表注释
COMMENT ON TABLE swarms IS 'Agent 蜂群表 - 存储 Agent 蜂群信息，manager_agent_id NOT NULL';
-- V37 新增：字段注释
COMMENT ON COLUMN swarms.id IS '蜂群唯一标识';
COMMENT ON COLUMN swarms.project_id IS '所属项目 ID';
COMMENT ON COLUMN swarms.manager_agent_id IS '管理器 Agent ID（NOT NULL）';
COMMENT ON COLUMN swarms.purpose IS '蜂群用途（code_writing/testing/tdd_test）';
COMMENT ON COLUMN swarms.step_number IS '对应 DevFlow 步骤编号（1~16）';
COMMENT ON COLUMN swarms.status IS '蜂群状态（active/completed/dissolved）';
COMMENT ON COLUMN swarms.dissolved_at IS '解散时间';
