-- ============================================================
-- DevFlow DATABASE V19 - 提交记录表
-- File: 20-commits.sql
-- Source: section 2.20 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 提交记录表
-- ============================================================
CREATE TABLE commits (
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
CREATE INDEX idx_commits_repo ON commits(repo_id);