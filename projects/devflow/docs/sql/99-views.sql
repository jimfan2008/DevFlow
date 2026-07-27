-- ============================================================
-- DevFlow DATABASE V37 - 视图定义
-- File: 99-views.sql
-- Source: section 3 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 项目进度视图
-- ============================================================
CREATE OR REPLACE VIEW v_project_progress AS
SELECT
    p.id AS project_id,
    p.name AS project_name,
    p.status AS project_status,
    p.current_step,
    p.creator_id,
    u.username AS creator_username,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) AS completed_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) AS in_progress_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'pending' THEN t.id END) AS pending_tasks,
    ROUND(
        COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END)::DECIMAL /
        NULLIF(COUNT(DISTINCT t.id), 0) * 100,
        2
    ) AS completion_percentage,
    p.created_at,
    p.completed_at
FROM projects p
JOIN users u ON p.creator_id = u.id
LEFT JOIN tasks t ON p.id = t.project_id
GROUP BY p.id, p.name, p.status, p.current_step, p.creator_id,
         u.username, p.created_at, p.completed_at;

-- ============================================================
-- Agent负载视图
-- ============================================================
CREATE OR REPLACE VIEW v_agent_load AS
SELECT
    a.id AS agent_id,
    a.name AS agent_name,
    a.chinese_name,
    a.role_name,
    a.status AS agent_status,
    COUNT(DISTINCT t.id) AS total_assigned_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) AS active_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'pending' THEN t.id END) AS pending_tasks,
    COALESCE(AVG(t.actual_hours), 0) AS avg_task_hours
FROM agents a
LEFT JOIN tasks t ON a.id = t.assignee_agent_id
GROUP BY a.id, a.name, a.chinese_name, a.role_name, a.status;

-- ============================================================
-- QA检验统计视图（V28 更新：qa_records 新增 project_id/step_number/review_round 字段）
-- ============================================================
CREATE OR REPLACE VIEW v_qa_statistics AS
SELECT
    p.id AS project_id,
    p.name AS project_name,
    COUNT(DISTINCT qr.id) AS total_inspections,
    COUNT(DISTINCT CASE WHEN qr.acceptance_result = 'pass' THEN qr.id END) AS passed_inspections,
    COUNT(DISTINCT CASE WHEN qr.acceptance_result = 'fail' THEN qr.id END) AS failed_inspections,
    ROUND(
        COUNT(DISTINCT CASE WHEN qr.acceptance_result = 'pass' THEN qr.id END)::DECIMAL /
        NULLIF(COUNT(DISTINCT qr.id), 0) * 100,
        2
    ) AS pass_rate,
    ROUND(AVG(qr.score), 2) AS average_score
FROM projects p
LEFT JOIN tasks t ON p.id = t.project_id
LEFT JOIN qa_records qr ON t.id = qr.task_id
GROUP BY p.id, p.name;
