-- ============================================================
-- DevFlow DATABASE V37 - 任务与提交关联表
-- File: 21-task-commits.sql
-- Source: section 2.21 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 任务与提交关联表
-- ============================================================
CREATE TABLE IF NOT EXISTS task_commits (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(task_id, commit_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_task_commits_task ON task_commits(task_id);
CREATE INDEX IF NOT EXISTS idx_task_commits_commit ON task_commits(commit_id);
-- V37 新增：表注释
COMMENT ON TABLE task_commits IS '任务-提交关联表 - 任务与提交的关联关系';
-- V37 新增：字段注释
COMMENT ON COLUMN task_commits.id IS '关联记录唯一标识';
COMMENT ON COLUMN task_commits.task_id IS '任务 ID';
COMMENT ON COLUMN task_commits.commit_id IS '提交 ID';
