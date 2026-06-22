-- ============================================================
-- DevFlow DATABASE V34 - 项目表
-- File: 03-projects.sql
-- ============================================================

-- ============================================================
-- 项目表
-- V34 修正：恢复 deleted_at 字段（与后端 V40 §5.2.2 对齐）
-- V34 修正：status 默认值从 'active' 改回 'created'
-- ============================================================
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,  -- 业务编号: proj-YYYYMMDD-NNN
    name VARCHAR(200) NOT NULL,
    description TEXT,
    creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    core_goal TEXT,
    status project_status NOT NULL DEFAULT 'created',
    current_step INTEGER NOT NULL DEFAULT 1,
    -- V10 修正 V16 确认：DevFlow 为 16 步标准流程，上限为 16
    CHECK (current_step >= 1 AND current_step <= 16),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    -- V34 修正：恢复 deleted_at 字段（与后端 V40 §5.2.2 对齐）
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_projects_creator ON projects(creator_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_name ON projects(name) USING gin(name gin_trgm_ops);
-- V34 修正：恢复 deleted_at 部分索引
CREATE INDEX idx_projects_deleted ON projects(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_projects_code ON projects(code);

-- 触发器
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V20 修正：trg_sync_project_current_step 触发器已移至 08-tasks.sql
-- 原因：该触发器作用于 tasks 表，在 tasks 表未创建之前定义会报错
