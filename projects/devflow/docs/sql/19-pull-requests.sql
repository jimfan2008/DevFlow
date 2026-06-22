-- ============================================================
-- DevFlow DATABASE V21 - 拉取请求表
-- File: 19-pull-requests.sql
-- ============================================================

-- ============================================================
-- 拉取请求表
-- ============================================================
CREATE TABLE pull_requests (
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
CREATE INDEX idx_prs_repo ON pull_requests(repo_id);
CREATE INDEX idx_prs_status ON pull_requests(status);
CREATE INDEX idx_prs_source_branch ON pull_requests(source_branch_id);
CREATE INDEX idx_prs_target_branch ON pull_requests(target_branch_id);

-- 触发器
CREATE TRIGGER update_pull_requests_updated_at
    BEFORE UPDATE ON pull_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
