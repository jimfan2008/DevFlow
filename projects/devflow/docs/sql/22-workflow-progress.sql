-- ============================================================
-- DevFlow DATABASE V33 - 工作流进度表
-- File: 22-workflow-progress.sql
-- V33 新增：与后端 V37 §5.1 ER 图对齐
-- ============================================================

-- ============================================================
-- 工作流进度表
-- 与 projects 表 1:1 关系，跟踪每个项目的工作流进度
-- ============================================================
CREATE TABLE workflow_progress (
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
CREATE UNIQUE INDEX uq_workflow_progress_project ON workflow_progress(project_id);
CREATE INDEX idx_workflow_progress_project ON workflow_progress(project_id);
CREATE INDEX idx_workflow_progress_current_step ON workflow_progress(current_step);

-- 触发器
CREATE TRIGGER update_workflow_progress_updated_at
    BEFORE UPDATE ON workflow_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
