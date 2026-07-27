-- ============================================================
-- DevFlow DATABASE V37 - 会议结果表
-- File: 15-meeting-outcomes.sql
-- Source: section 2.13 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 会议结果表
-- ============================================================
CREATE TABLE IF NOT EXISTS meeting_outcomes (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    host_agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    type meeting_type NOT NULL,
    outcome TEXT,
    UNIQUE(group_id, started_at),
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_meeting_outcomes_group ON meeting_outcomes(group_id);
CREATE INDEX IF NOT EXISTS idx_meeting_outcomes_host ON meeting_outcomes(host_agent_id);
CREATE INDEX IF NOT EXISTS idx_meeting_outcomes_composite ON meeting_outcomes(group_id, host_agent_id);
-- V37 新增：表注释
COMMENT ON TABLE meeting_outcomes IS '会议结果表 - 记录会议结果和决议';
-- V37 新增：字段注释
COMMENT ON COLUMN meeting_outcomes.id IS '会议记录唯一标识';
COMMENT ON COLUMN meeting_outcomes.group_id IS '所属群组 ID';
COMMENT ON COLUMN meeting_outcomes.host_agent_id IS '主持人 Agent ID';
COMMENT ON COLUMN meeting_outcomes.type IS '会议类型';
COMMENT ON COLUMN meeting_outcomes.outcome IS '会议结果';
