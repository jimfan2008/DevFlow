-- ============================================================
-- DevFlow DATABASE V19 - 会议结果表
-- File: 15-meeting-outcomes.sql
-- Source: section 2.13 of devflow_DATABASE_V16.md
-- ============================================================

-- ============================================================
-- 会议结果表
-- ============================================================
CREATE TABLE meeting_outcomes (
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
CREATE INDEX idx_meeting_outcomes_group ON meeting_outcomes(group_id);
CREATE INDEX idx_meeting_outcomes_host ON meeting_outcomes(host_agent_id);
CREATE INDEX idx_meeting_outcomes_composite ON meeting_outcomes(group_id, host_agent_id);