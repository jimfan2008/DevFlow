-- ============================================================
-- DevFlow DATABASE V37 - 工作流步骤表
-- File: 23-workflow-steps.sql
-- V33 新增：与后端 V37 §5.1 ER 图对齐
-- ============================================================

-- ============================================================
-- 工作流步骤表
-- 与 workflow_progress 表 1:N 关系，记录每个步骤的执行状态
-- ============================================================
CREATE TABLE IF NOT EXISTS workflow_steps (
    id SERIAL PRIMARY KEY,
    workflow_id INTEGER NOT NULL REFERENCES workflow_progress(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    CHECK (step_number >= 1 AND step_number <= 16),
    step_name VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    assigned_agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_steps_workflow_step ON workflow_steps(workflow_id, step_number);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow ON workflow_steps(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_status ON workflow_steps(status);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_step_number ON workflow_steps(step_number);

-- 触发器
CREATE TRIGGER IF NOT EXISTS update_workflow_steps_updated_at
    BEFORE UPDATE ON workflow_steps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V37 新增：表注释
COMMENT ON TABLE workflow_steps IS '工作流步骤表 - 工作流各步骤的执行状态';
-- V37 新增：字段注释
COMMENT ON COLUMN workflow_steps.id IS '步骤记录唯一标识';
COMMENT ON COLUMN workflow_steps.workflow_id IS '所属工作流 ID';
COMMENT ON COLUMN workflow_steps.step_number IS '步骤编号';
COMMENT ON COLUMN workflow_steps.status IS '步骤状态';
