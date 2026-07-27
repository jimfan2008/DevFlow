-- ============================================================
-- DevFlow DATABASE V37 - 拉取请求表
-- File: 19-pull-requests.sql
-- ============================================================

-- ============================================================
-- 拉取请求表
-- ============================================================
CREATE TABLE IF NOT EXISTS pull_requests (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT,
    status pr_status NOT NULL DEFAULT 'open',
    -- V20/V21 修正：source_branch_id/target_branch_id 改为 BIGINT 类型，新增外键引用 repo_branches(id)
    source_branch_id INTEGER REFERENCES repo_branches(id) ON DELETE SET NULL,
    target_branch_id INTEGER REFERENCES repo_branches(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, number)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_prs_repo ON pull_requests(repo_id);
CREATE INDEX IF NOT EXISTS idx_prs_status ON pull_requests(status);
CREATE INDEX IF NOT EXISTS idx_prs_source_branch ON pull_requests(source_branch_id);
CREATE INDEX IF NOT EXISTS idx_prs_target_branch ON pull_requests(target_branch_id);

-- 触发器
CREATE TRIGGER IF NOT EXISTS update_pull_requests_updated_at
    BEFORE UPDATE ON pull_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V37 新增：表注释
COMMENT ON TABLE pull_requests IS '拉取请求表 - 代码拉取请求信息';
-- V37 新增：字段注释
COMMENT ON COLUMN pull_requests.id IS 'PR 唯一标识';
COMMENT ON COLUMN pull_requests.repo_id IS '所属仓库 ID';
COMMENT ON COLUMN pull_requests.number IS 'PR 编号';
COMMENT ON COLUMN pull_requests.status IS 'PR 状态（open/closed/merged）';
COMMENT ON COLUMN pull_requests.source_branch_id IS '源分支 ID';
COMMENT ON COLUMN pull_requests.target_branch_id IS '目标分支 ID';
