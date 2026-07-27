-- ============================================================
-- DevFlow DATABASE V37 - 代码仓库表
-- File: 17-repos.sql
-- Source: section 2.17 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 代码仓库表（与 project 1:1）
-- ============================================================
CREATE TABLE IF NOT EXISTS repos (
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
CREATE INDEX IF NOT EXISTS idx_repos_vcs_id ON repos(vcs_platform, vcs_repo_id);
-- V37 新增：表注释
COMMENT ON TABLE repos IS '代码仓库表 - 代码版本控制仓库，与 project 1:1 关系';
-- V37 新增：字段注释
COMMENT ON COLUMN repos.id IS '仓库唯一标识';
COMMENT ON COLUMN repos.project_id IS '所属项目 ID（1:1）';
COMMENT ON COLUMN repos.vcs_platform IS 'VCS 平台（gitea/github/gitlab）';
COMMENT ON COLUMN repos.vcs_repo_id IS 'VCS 仓库 ID';
