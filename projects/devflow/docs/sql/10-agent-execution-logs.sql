-- ============================================================
-- DevFlow DATABASE V19 - Agent执行日志表
-- File: 10-agent-execution-logs.sql
-- Source: section 2.8 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- Agent执行日志表
-- ============================================================
CREATE TABLE agent_execution_logs (
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
CREATE INDEX idx_exec_logs_task ON agent_execution_logs(task_id);
CREATE INDEX idx_exec_logs_agent ON agent_execution_logs(agent_id);
CREATE INDEX idx_exec_logs_created ON agent_execution_logs(created_at);
