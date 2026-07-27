-- ============================================================
-- DevFlow DATABASE V37 - Agent执行日志表
-- File: 10-agent-execution-logs.sql
-- Source: section 2.8 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- Agent执行日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_execution_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    step_number INTEGER NOT NULL,
    content TEXT,
    result JSONB,
    error_message TEXT,
    duration_seconds DECIMAL(8,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_exec_logs_task ON agent_execution_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_exec_logs_agent ON agent_execution_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_exec_logs_created ON agent_execution_logs(created_at);

-- V37 新增：表注释
COMMENT ON TABLE agent_execution_logs IS 'Agent 执行日志表 - 记录 Agent 执行任务的详细日志';
-- V37 新增：字段注释
COMMENT ON COLUMN agent_execution_logs.id IS '日志唯一标识';
COMMENT ON COLUMN agent_execution_logs.task_id IS '所属任务 ID';
COMMENT ON COLUMN agent_execution_logs.agent_id IS '执行 Agent ID';
COMMENT ON COLUMN agent_execution_logs.content IS '执行内容';
COMMENT ON COLUMN agent_execution_logs.result IS '执行结果（JSONB）';
COMMENT ON COLUMN agent_execution_logs.error_message IS '错误信息';
COMMENT ON COLUMN agent_execution_logs.duration_seconds IS '耗时（秒）';
