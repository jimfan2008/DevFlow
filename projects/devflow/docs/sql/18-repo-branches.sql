-- ============================================================
-- DevFlow DATABASE V37 - 分支表
-- File: 18-repo-branches.sql
-- Source: section 2.18 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 分支表
-- ============================================================
CREATE TABLE IF NOT EXISTS repo_branches (
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
CREATE INDEX IF NOT EXISTS idx_repo_branches_repo ON repo_branches(repo_id);

-- 触发器
-- V19 修正：使用标准的 update_updated_at_column() 函数（定义于 02-users.sql）
CREATE TRIGGER IF NOT EXISTS update_repo_branches_updated_at
    BEFORE UPDATE ON repo_branches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
-- V37 新增：表注释
COMMENT ON TABLE repo_branches IS '代码分支表 - 仓库分支信息';
-- V37 新增：字段注释
COMMENT ON COLUMN repo_branches.id IS '分支唯一标识';
COMMENT ON COLUMN repo_branches.repo_id IS '所属仓库 ID';
COMMENT ON COLUMN repo_branches.name IS '分支名称';
COMMENT ON COLUMN repo_branches.is_protected IS '是否受保护';
