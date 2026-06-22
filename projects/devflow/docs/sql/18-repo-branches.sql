-- ============================================================
-- DevFlow DATABASE V19 - 分支表
-- File: 18-repo-branches.sql
-- Source: section 2.18 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 分支表
-- ============================================================
CREATE TABLE repo_branches (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    commit_sha VARCHAR(40),
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, name)
);

-- 索引
CREATE INDEX idx_repo_branches_repo ON repo_branches(repo_id);

-- 触发器
-- V19 修正：使用标准的 update_updated_at_column() 函数（定义于 02-users.sql）
CREATE TRIGGER update_repo_branches_updated_at
    BEFORE UPDATE ON repo_branches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();