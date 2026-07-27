-- ============================================================
-- DevFlow DATABASE V37 - Agent角色表
-- File: 05-agents.sql
-- ============================================================

-- ============================================================
-- Agent角色表（9个命名Agent + 编程Agent蜂群）
-- V33 修正：status 默认值从 'offline' 改为 'idle'，与后端 V37 §4.4 AgentOut.status 对齐
-- ============================================================
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    agent_type agent_type NOT NULL DEFAULT 'named',
    role_name VARCHAR(100) NOT NULL,
    chinese_name VARCHAR(50),
    -- V33 修正：默认值从 'offline' 改为 'idle'
    status agent_status NOT NULL DEFAULT 'idle',
    api_endpoint VARCHAR(255),
    model_default VARCHAR(100),
    model_provider VARCHAR(100),
    config JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_name ON agents(name);
CREATE INDEX IF NOT EXISTS idx_agents_config_gin ON agents USING gin(config);

-- 触发器
CREATE TRIGGER IF NOT EXISTS update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 初始化9个命名Agent
-- V33 修正：status 默认值从 'offline' 改为 'idle'
INSERT INTO agents (name, agent_type, role_name, chinese_name, status) VALUES
('haimei', 'named', 'project_manager', '海梅', 'idle'),
('houxing', 'named', 'requirement_analyst', '后兴', 'idle'),
('houwang', 'named', 'architect', '后旺', 'idle'),
('houfa', 'named', 'programmer', '后发', 'idle'),
('houbada', 'named', 'tester', '后达', 'idle'),
('houfu', 'named', 'cicd_engineer', '后富', 'idle'),
('hougui', 'named', 'document_admin', '后贵', 'idle'),
('hourong', 'named', 'qa', '后荣', 'idle'),
('houhua', 'named', 'security_auditor', '后华', 'idle');

-- V37 新增：表注释
COMMENT ON TABLE agents IS 'Agent 表 - 存储 AI Agent 信息，包含 9 个命名 Agent 初始化数据';
-- V37 新增：字段注释
COMMENT ON COLUMN agents.id IS 'Agent 唯一标识';
COMMENT ON COLUMN agents.name IS 'Agent 名称';
COMMENT ON COLUMN agents.agent_type IS 'Agent 类型（named/swarm）';
COMMENT ON COLUMN agents.role_name IS '角色名称';
COMMENT ON COLUMN agents.chinese_name IS '中文名称';
COMMENT ON COLUMN agents.status IS 'Agent 状态（idle/busy/error/offline）';
COMMENT ON COLUMN agents.config IS '配置信息（JSONB）';
