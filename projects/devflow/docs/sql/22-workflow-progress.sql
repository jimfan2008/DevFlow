-- ============================================================
-- DevFlow DATABASE V37 - 工作流进度表
-- File: 22-workflow-progress.sql
-- V33 新增：与后端 V37 §5.1 ER 图对齐
-- ============================================================

-- ============================================================
-- 工作流进度表
-- 与 projects 表 1:1 关系，跟踪每个项目的工作流进度
-- ============================================================
CREATE TABLE IF NOT EXISTS workflow_progress (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    current_step INTEGER NOT NULL DEFAULT 1,
    CHECK (current_step >= 1 AND current_step <= 16),
    total_steps INTEGER NOT NULL DEFAULT 16,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_progress_project ON workflow_progress(project_id);
CREATE INDEX IF NOT EXISTS idx_workflow_progress_project ON workflow_progress(project_id);
CREATE INDEX IF NOT EXISTS idx_workflow_progress_current_step ON workflow_progress(current_step);

-- 触发器
CREATE TRIGGER IF NOT EXISTS update_workflow_progress_updated_at
    BEFORE UPDATE ON workflow_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V37 新增：表注释
COMMENT ON TABLE workflow_progress IS '工作流进度表 - 项目工作流进度跟踪，与 project 1:1';
-- V37 新增：字段注释
COMMENT ON COLUMN workflow_progress.id IS '工作流进度唯一标识';
COMMENT ON COLUMN workflow_progress.project_id IS '所属项目 ID（1:1）';
COMMENT ON COLUMN workflow_progress.current_step IS '当前步骤编号';
COMMENT ON COLUMN workflow_progress.total_steps IS '总步骤数';
