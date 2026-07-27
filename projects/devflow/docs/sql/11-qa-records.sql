-- ============================================================
-- DevFlow DATABASE V37 - QA检验记录表
-- File: 11-qa-records.sql
-- Source: section 2.9 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- QA检验记录表
-- ============================================================
-- V28 修正：添加 project_id, step_number, review_round 字段以匹配后端 QARecordOut schema
CREATE TABLE IF NOT EXISTS qa_records (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    CHECK (step_number >= 1 AND step_number <= 16),
    reviewer_agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    score DECIMAL(5,2) CHECK (score >= 0 AND score <= 100),
    acceptance_result qa_result NOT NULL,
    review_dimensions JSONB,
    comments TEXT,
    review_round INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_qa_records_task ON qa_records(task_id);
CREATE INDEX IF NOT EXISTS idx_qa_records_project ON qa_records(project_id);
CREATE INDEX IF NOT EXISTS idx_qa_records_step ON qa_records(step_number);
CREATE INDEX IF NOT EXISTS idx_qa_records_reviewer ON qa_records(reviewer_agent_id);
CREATE INDEX IF NOT EXISTS idx_qa_records_result ON qa_records(acceptance_result);
CREATE INDEX IF NOT EXISTS idx_qa_records_round ON qa_records(review_round);
CREATE INDEX IF NOT EXISTS idx_qa_review_dimensions_gin ON qa_records USING gin(review_dimensions);

-- V37 新增：表注释
COMMENT ON TABLE qa_records IS 'QA 检验记录表 - 记录 QA 检验结果和评分';
-- V37 新增：字段注释
COMMENT ON COLUMN qa_records.id IS '检验记录唯一标识';
COMMENT ON COLUMN qa_records.task_id IS '所属任务 ID';
COMMENT ON COLUMN qa_records.project_id IS '所属项目 ID';
COMMENT ON COLUMN qa_records.step_number IS 'DevFlow 步骤编号';
COMMENT ON COLUMN qa_records.reviewer_agent_id IS '审查 Agent ID';
COMMENT ON COLUMN qa_records.score IS '评分（0~100）';
COMMENT ON COLUMN qa_records.acceptance_result IS '验收结果（pass/fail）';
COMMENT ON COLUMN qa_records.review_dimensions IS '审查维度（JSONB）';
COMMENT ON COLUMN qa_records.review_round IS '审查轮次';
