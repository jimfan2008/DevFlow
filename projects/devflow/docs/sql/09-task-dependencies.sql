-- ============================================================
-- DevFlow DATABASE V37 - 任务依赖表
-- File: 09-task-dependencies.sql
-- ============================================================

-- ============================================================
-- 任务依赖表
-- ============================================================
CREATE TABLE IF NOT EXISTS task_dependencies (
    id SERIAL PRIMARY KEY,
    source_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    target_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    -- V19 修正：使用 dependency_type_enum 枚举类型替代 VARCHAR(50)+CHECK
    dependency_type dependency_type_enum NOT NULL DEFAULT 'finish_to_start',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(source_task_id, target_task_id),
    CHECK (source_task_id <> target_task_id)
);

-- NOTE: 循环依赖检测采用双重保障：应用层执行完整拓扑排序校验，数据库层通过触发器进行兜底环检测。

-- 索引
CREATE INDEX IF NOT EXISTS idx_task_deps_source ON task_dependencies(source_task_id);
CREATE INDEX IF NOT EXISTS idx_task_deps_target ON task_dependencies(target_task_id);

-- 触发器：确保 source 和 target 任务属于同一 project_id
CREATE OR REPLACE FUNCTION check_same_project_dependency()
RETURNS TRIGGER AS $$
DECLARE
    source_project_id INTEGER;
    target_project_id INTEGER;
BEGIN
    SELECT project_id INTO source_project_id FROM tasks WHERE id = NEW.source_task_id;
    SELECT project_id INTO target_project_id FROM tasks WHERE id = NEW.target_task_id;
    IF source_project_id IS DISTINCT FROM target_project_id THEN
        RAISE EXCEPTION '依赖关系的两个任务必须属于同一项目: source项目=%, target项目=%',
                        source_project_id, target_project_id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS enforce_same_project_dependency
    BEFORE INSERT OR UPDATE OF source_task_id, target_task_id ON task_dependencies
    FOR EACH ROW
    EXECUTE FUNCTION check_same_project_dependency();

-- 数据库级循环依赖检测触发器（兜底保障）
-- V20/V21 修正：递归 CTE 方向修正
-- 正确逻辑：添加边 source->target 后，若从 target 出发可达 source，则形成环，应拒绝
CREATE OR REPLACE FUNCTION check_circular_dependency()
RETURNS TRIGGER AS $$
DECLARE
    v_source INTEGER := NEW.source_task_id;
    v_target INTEGER := NEW.target_task_id;
    v_cycle_found BOOLEAN;
BEGIN
    -- V20 修正：从 v_target 出发正向遍历，检查 v_source 是否可达
    -- 如果从 target 出发能到达 source，说明添加 source->target 后会形成环
    WITH RECURSIVE reachable AS (
        SELECT source_task_id, target_task_id
        FROM task_dependencies
        WHERE source_task_id = v_target          -- V20 修正：从 v_target 出发
        UNION
        SELECT r.source_task_id, td.target_task_id
        FROM reachable r
        JOIN task_dependencies td ON td.source_task_id = r.target_task_id
        WHERE td.target_task_id <> v_target
    )
    -- V20 修正：检查 v_source 是否可达
    SELECT EXISTS(SELECT 1 FROM reachable WHERE target_task_id = v_source)
    INTO v_cycle_found;

    IF v_cycle_found THEN
        RAISE EXCEPTION '检测到循环依赖: 任务 % 已可到达任务 %，插入依赖 % -> % 将形成环',
                        v_target, v_source, v_source, v_target;
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS trg_check_circular_dependency
    BEFORE INSERT OR UPDATE ON task_dependencies
    FOR EACH ROW
    EXECUTE FUNCTION check_circular_dependency();

-- V37 新增：表注释
COMMENT ON TABLE task_dependencies IS '任务依赖表 - 存储任务间的依赖关系，支持循环依赖检测';
-- V37 新增：字段注释
COMMENT ON COLUMN task_dependencies.id IS '依赖记录唯一标识';
COMMENT ON COLUMN task_dependencies.source_task_id IS '源任务 ID';
COMMENT ON COLUMN task_dependencies.target_task_id IS '目标任务 ID';
COMMENT ON COLUMN task_dependencies.dependency_type IS '依赖类型（finish_to_start/start_to_start/finish_to_finish/start_to_finish）';
