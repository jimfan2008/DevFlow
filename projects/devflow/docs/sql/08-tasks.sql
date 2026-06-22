-- ============================================================
-- DevFlow DATABASE V21 - 任务表
-- File: 08-tasks.sql
-- ============================================================

-- ============================================================
-- 任务表
-- ============================================================
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    type task_type NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    -- 任务分配三选一: assignee_agent_id (单个Agent)、assignee_swarm_id (蜂群)、assignee_user_id (人类用户)
    assignee_agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    assignee_swarm_id INTEGER REFERENCES swarms(id) ON DELETE SET NULL,
    assignee_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status task_status NOT NULL DEFAULT 'pending',
    acceptance_criteria JSONB,
    step_number INTEGER NOT NULL,
    -- V10 修正 V16 确认：DevFlow 为 16 步标准流程，上限为 16
    CHECK (step_number >= 1 AND step_number <= 16),
    is_atomic BOOLEAN NOT NULL DEFAULT TRUE,
    parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CHECK (completed_at IS NULL OR completed_at >= created_at),
    -- V6 修正 V16 确认：任务分配三选一约束，允许多个全NULL（未分配）或恰好一个非NULL（已分配）
    CHECK (
        (CASE WHEN assignee_agent_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN assignee_swarm_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN assignee_user_id IS NOT NULL THEN 1 ELSE 0 END) <= 1
    )
);

-- 索引
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_agent_id);
CREATE INDEX idx_tasks_swarm ON tasks(assignee_swarm_id);
CREATE INDEX idx_tasks_assignee_user ON tasks(assignee_user_id);
CREATE INDEX idx_tasks_step ON tasks(step_number);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX idx_tasks_deleted ON tasks(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_tasks_acceptance_criteria_gin ON tasks USING gin(acceptance_criteria);

-- 触发器
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 触发器：确保子任务的project_id与父任务的project_id一致
CREATE OR REPLACE FUNCTION check_parent_same_project()
RETURNS TRIGGER AS $$
DECLARE
    parent_project_id INTEGER;
BEGIN
    IF NEW.parent_task_id IS NOT NULL THEN
        SELECT project_id INTO parent_project_id FROM tasks WHERE id = NEW.parent_task_id;
        IF parent_project_id IS DISTINCT FROM NEW.project_id THEN
            RAISE EXCEPTION '子任务的project_id必须与父任务的project_id一致: 子任务项目=%, 父任务项目=%',
                            NEW.project_id, parent_project_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_enforce_parent_same_project
    BEFORE INSERT OR UPDATE OF parent_task_id, project_id ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION check_parent_same_project();

-- ============================================================
-- V20 修正：trg_sync_project_current_step 触发器从 03-projects.sql 移至此处
-- 原因：该触发器作用于 tasks 表，必须在 tasks 表创建之后才能定义
-- ============================================================
CREATE OR REPLACE FUNCTION sync_project_current_step()
RETURNS TRIGGER AS $$
DECLARE
    v_project_id INTEGER;
    v_current_step INTEGER;
BEGIN
    v_project_id := COALESCE(NEW.project_id, OLD.project_id);

    -- INSERT 操作：新任务默认为 pending 状态，不更新项目进度
    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;

    -- UPDATE 操作：任务从已完成变为其他状态，需要重新计算
    IF OLD.status = 'completed' AND NEW.status <> 'completed' THEN
        -- 锁项目行后重新计算最大 step_number
        UPDATE projects SET current_step = (
            SELECT COALESCE(MAX(step_number), 0) + 1
            FROM tasks
            WHERE project_id = v_project_id AND status = 'completed'
        )
        WHERE id = v_project_id
        RETURNING current_step INTO v_current_step;
        RETURN NEW;
    END IF;

    -- UPDATE 操作：任务变为已完成
    IF NEW.status = 'completed' AND (OLD.status IS DISTINCT FROM 'completed') THEN
        -- 锁项目行（不是所有任务），获取当前 current_step
        UPDATE projects SET current_step = current_step
        WHERE id = v_project_id
        RETURNING current_step INTO v_current_step;

        -- 只在新任务 step_number 超过 current_step 时才更新
        IF NEW.step_number >= v_current_step THEN
            UPDATE projects SET current_step = NEW.step_number + 1
            WHERE id = v_project_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_sync_project_current_step
    AFTER INSERT OR UPDATE OF status, step_number ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION sync_project_current_step();
