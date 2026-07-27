-- ============================================================
-- DevFlow DATABASE V37 - 提交记录表
-- File: 20-commits.sql
-- Source: section 2.20 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 提交记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS commits (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    sha VARCHAR(40) NOT NULL,
    message TEXT,
    author VARCHAR(200),
    parent_sha VARCHAR(40),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, sha)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repo_id);
-- V37 新增：表注释
COMMENT ON TABLE commits IS '提交记录表 - 代码提交记录';
-- V37 新增：字段注释
COMMENT ON COLUMN commits.id IS '提交唯一标识';
COMMENT ON COLUMN commits.repo_id IS '所属仓库 ID';
COMMENT ON COLUMN commits.sha IS '提交 SHA';
