-- ============================================================
-- DevFlow DATABASE V37 - 软删除物理清理存储过程
-- File: 96-soft-delete-cleanup.sql
-- ============================================================

-- 软删除说明：
-- V34 修正：恢复 projects 表 deleted_at 字段（与后端 V40 §5.2.2 对齐）
-- - 软删除字段: projects、tasks、groups、swarms、notifications 表包含 deleted_at 字段（共 5 张表）
-- - 逻辑删除: 设置为非 NULL 表示逻辑删除，数据仍然保留在数据库中
-- - 物理删除: 仅在数据保留超过 90 天后执行物理删除（通过定时任务清理）
-- - 查询过滤: 应用层查询默认过滤 deleted_at IS NULL 的记录

-- ============================================================
-- 软删除数据物理清理存储过程
-- 建议：通过 pg_cron 或应用层定时任务每天执行一次
-- V6 修正：重写为完整可执行的清理逻辑，按外键依赖顺序逐层清理
-- V20/V21 扩展：孤儿清理覆盖全部 16 张含外键依赖的表（非 deleted_at 清理，详见注释）
-- V33 新增：workflow_progress/workflow_steps/project_members 孤儿清理
-- V34 修正：恢复 projects 软删除清理逻辑（与后端 V40 §5.2.2 对齐）
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_soft_deleted(retention_days INTEGER DEFAULT 90)
RETURNS TABLE(cleared_projects BIGINT, cleared_tasks BIGINT, cleared_groups BIGINT,
              cleared_swarms BIGINT, cleared_notifications BIGINT, cleared_orphans BIGINT) AS $$
DECLARE
    v_cleared_projects BIGINT := 0;
    v_cleared_notifications BIGINT := 0;
    v_cleared_swarms BIGINT := 0;
    v_cleared_groups BIGINT := 0;
    v_cleared_tasks BIGINT := 0;
    v_cleared_orphans BIGINT := 0;
    v_deleted_task_ids BIGINT[];
    v_deleted_project_ids BIGINT[];
    v_deleted_group_ids BIGINT[];
    v_deleted_swarm_ids BIGINT[];
BEGIN
    -- V34 修正：恢复 projects 软删除收集逻辑
    SELECT ARRAY_AGG(id) INTO v_deleted_project_ids
    FROM projects
    WHERE deleted_at IS NOT NULL
      AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL;

    -- 收集待删除的任务 ID
    SELECT ARRAY_AGG(id) INTO v_deleted_task_ids
    FROM tasks
    WHERE deleted_at IS NOT NULL
      AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL;

    -- 收集待删除的群组 ID
    SELECT ARRAY_AGG(id) INTO v_deleted_group_ids
    FROM groups
    WHERE deleted_at IS NOT NULL
      AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL;

    -- 收集待删除的蜂群 ID
    SELECT ARRAY_AGG(id) INTO v_deleted_swarm_ids
    FROM swarms
    WHERE deleted_at IS NOT NULL
      AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL;

    -- ===== 第1层：孤儿数据清理（V20/V21 新增 7 张表，V33 新增 3 张表） =====

    -- 清理 task_commits（依赖 tasks 和 commits）
    DELETE FROM task_commits
    WHERE task_id = ANY(v_deleted_task_ids);

    -- 清理 commits（依赖 repos，父项目已删除）
    DELETE FROM commits
    WHERE repo_id IN (
        SELECT r.id FROM repos r
        WHERE r.project_id = ANY(v_deleted_project_ids)
    );

    -- 清理 pull_requests（依赖 repos 和 repo_branches）
    DELETE FROM pull_requests
    WHERE repo_id IN (
        SELECT r.id FROM repos r
        WHERE r.project_id = ANY(v_deleted_project_ids)
    );

    -- 清理 repo_branches（依赖 repos）
    DELETE FROM repo_branches
    WHERE repo_id IN (
        SELECT r.id FROM repos r
        WHERE r.project_id = ANY(v_deleted_project_ids)
    );

    -- 清理 agent_execution_logs（依赖 tasks 和 agents）
    DELETE FROM agent_execution_logs
    WHERE task_id = ANY(v_deleted_task_ids);

    -- 清理 qa_records（依赖 tasks 和 agents，V28 新增 project_id/step_number/review_round 字段）
    DELETE FROM qa_records
    WHERE task_id = ANY(v_deleted_task_ids);

    -- 清理 requirements（依赖 projects）
    DELETE FROM requirements
    WHERE project_id = ANY(v_deleted_project_ids);

    -- V33 新增：清理 workflow_steps（依赖 workflow_progress -> projects）
    DELETE FROM workflow_steps
    WHERE workflow_id IN (
        SELECT wp.id FROM workflow_progress wp
        WHERE wp.project_id = ANY(v_deleted_project_ids)
    );

    -- V33 新增：清理 workflow_progress（依赖 projects）
    DELETE FROM workflow_progress
    WHERE project_id = ANY(v_deleted_project_ids);

    -- V33 新增 / V34 修正：清理 project_members（依赖 projects）
    DELETE FROM project_members
    WHERE project_id = ANY(v_deleted_project_ids);

    -- 统计孤儿数据清理数量
    SELECT COUNT(*) INTO v_cleared_orphans
    FROM (
        SELECT 1 WHERE EXISTS (SELECT 1 FROM task_commits WHERE task_id = ANY(v_deleted_task_ids))
        UNION ALL
        SELECT 1 WHERE EXISTS (SELECT 1 FROM agent_execution_logs WHERE task_id = ANY(v_deleted_task_ids))
        UNION ALL
        SELECT 1 WHERE EXISTS (SELECT 1 FROM qa_records WHERE task_id = ANY(v_deleted_task_ids))
    ) t;

    -- ===== 第2层：清理关联表 =====

    -- 清理群成员（依赖 groups）
    DELETE FROM group_members
    WHERE group_id = ANY(v_deleted_group_ids);

    -- 清理群消息（依赖 groups）
    DELETE FROM group_messages
    WHERE group_id = ANY(v_deleted_group_ids);

    -- 清理会议结果（依赖 groups）
    DELETE FROM meeting_outcomes
    WHERE group_id = ANY(v_deleted_group_ids);

    -- 清理蜂群成员（依赖 swarms）
    DELETE FROM swarm_members
    WHERE swarm_id = ANY(v_deleted_swarm_ids);

    -- 清理任务依赖（依赖 tasks）
    DELETE FROM task_dependencies
    WHERE source_task_id = ANY(v_deleted_task_ids)
       OR target_task_id = ANY(v_deleted_task_ids);

    -- 清理通知（依赖 projects 和 users）
    WITH deleted AS (
        DELETE FROM notifications
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_notifications FROM deleted;

    -- ===== 第3层：清理父表 =====

    -- 清理蜂群（依赖 projects，swarm_members 已清理）
    WITH deleted AS (
        DELETE FROM swarms
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_swarms FROM deleted;

    -- 清理群组（依赖 projects，group_members/messages/meeting_outcomes 已清理）
    WITH deleted AS (
        DELETE FROM groups
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_groups FROM deleted;

    -- 清理任务（依赖 projects，依赖项已清理）
    WITH deleted AS (
        DELETE FROM tasks
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_tasks FROM deleted;

    -- V34 修正：恢复 projects 软删除清理逻辑（与后端 V40 §5.2.2 对齐）
    WITH deleted AS (
        DELETE FROM projects
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_projects FROM deleted;

    -- 返回清理统计
    cleared_projects := v_cleared_projects;
    cleared_tasks := v_cleared_tasks;
    cleared_groups := v_cleared_groups;
    cleared_swarms := v_cleared_swarms;
    cleared_notifications := v_cleared_notifications;
    cleared_orphans := v_cleared_orphans;
    RETURN NEXT;
END;
$$ language 'plpgsql';

-- 使用方式1：pg_cron 定时任务（需 pg_cron 扩展）
-- SELECT cron.schedule('soft-delete-cleanup', '0 2 * * *',
--     'SELECT * FROM cleanup_soft_deleted(90)');

-- 使用方式2：应用层定时任务（推荐）
-- 由 DevFlow 后端每天凌晨 2 点调用：
--   SELECT * FROM cleanup_soft_deleted(90);

-- V34 清理顺序（按外键依赖从叶子到根）：
--   第1层（孤儿数据）：
--     1. task_commits（依赖 tasks + commits）
--     2. commits（依赖 repos -> projects）
--     3. pull_requests（依赖 repos + repo_branches）
--     4. repo_branches（依赖 repos -> projects）
--     5. agent_execution_logs（依赖 tasks + agents）
--     6. qa_records（依赖 tasks + agents）
--     7. requirements（依赖 projects）
--     8. workflow_steps（依赖 workflow_progress -> projects）[V33 新增]
--     9. workflow_progress（依赖 projects）[V33 新增]
--    10. project_members（依赖 projects）[V33 新增]
--   第2层（关联表）：
--    11. group_members（依赖 groups）
--    12. group_messages（依赖 groups）
--    13. meeting_outcomes（依赖 groups）
--    14. swarm_members（依赖 swarms）
--    15. task_dependencies（依赖 tasks）
--    16. notifications（依赖 projects + users，含 deleted_at）
--   第3层（父表）：
--    17. swarms（依赖 projects，含 deleted_at）
--    18. groups（依赖 projects，含 deleted_at）
--    19. tasks（依赖 projects，含 deleted_at）
--    20. projects（含 deleted_at）[V34 修正：恢复]
--   孤儿清理覆盖 20 张表（5 张含 deleted_at 的软删除表 + 15 张孤儿关联清理表）
