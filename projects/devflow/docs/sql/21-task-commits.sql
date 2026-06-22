-- ============================================================
-- DevFlow DATABASE V19 - 任务与提交关联表
-- File: 21-task-commits.sql
-- Source: section 2.21 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 任务与提交关联表
-- ============================================================
CREATE TABLE task_commits (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(task_id, commit_id)
);

-- 索引
CREATE INDEX idx_task_commits_task ON task_commits(task_id);
CREATE INDEX idx_task_commits_commit ON task_commits(commit_id);