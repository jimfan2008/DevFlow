-- ============================================================
-- DevFlow DATABASE V19 - QA检验记录表
-- File: 11-qa-records.sql
-- Source: section 2.9 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- QA检验记录表
-- ============================================================
-- V28 修正：添加 project_id, step_number, review_round 字段以匹配后端 QARecordOut schema
CREATE TABLE qa_records (
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
CREATE INDEX idx_qa_records_task ON qa_records(task_id);
CREATE INDEX idx_qa_records_project ON qa_records(project_id);
CREATE INDEX idx_qa_records_step ON qa_records(step_number);
CREATE INDEX idx_qa_records_reviewer ON qa_records(reviewer_agent_id);
CREATE INDEX idx_qa_records_result ON qa_records(acceptance_result);
CREATE INDEX idx_qa_records_round ON qa_records(review_round);
CREATE INDEX idx_qa_review_dimensions_gin ON qa_records USING gin(review_dimensions);
