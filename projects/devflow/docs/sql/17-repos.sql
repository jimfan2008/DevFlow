-- ============================================================
-- DevFlow DATABASE V19 - 代码仓库表
-- File: 17-repos.sql
-- Source: section 2.17 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 代码仓库表（与 project 1:1）
-- ============================================================
CREATE TABLE repos (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    vcs_platform VARCHAR(50) NOT NULL CHECK (vcs_platform IN ('gitea', 'github', 'gitlab')),
    vcs_repo_id VARCHAR(100),
    url TEXT,
    default_branch VARCHAR(100) DEFAULT 'main',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(vcs_platform, vcs_repo_id)
);

-- 索引
CREATE INDEX idx_repos_vcs_id ON repos(vcs_platform, vcs_repo_id);