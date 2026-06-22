-- ============================================================
-- DevFlow DATABASE V34 - 群聊消息表
-- File: 14-group-messages.sql
-- ============================================================

-- ============================================================
-- 群聊消息表
-- V34 修正：mentions 类型从 TEXT[] 改回 JSONB（与后端 V40 §5.2.10 对齐）
-- V34 修正：sender_type 移除 system，恢复二值 (user, agent)
-- V34 修正：sender_id 校验触发器移除 system 类型处理
-- ============================================================
CREATE TABLE group_messages (
    id BIGSERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    sender_id INTEGER,
    sender_type sender_type,
    role VARCHAR(100),
    content TEXT NOT NULL,
    -- V20/V21 修正 V28 更新：改用 message_type_enum 枚举类型，取代 VARCHAR(20)+CHECK
    -- V28 修正：默认值从 'user' 改为 'text' 以匹配后端 schema
    message_type message_type_enum NOT NULL DEFAULT 'text',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_streaming BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    -- V28 新增 / V30 改为 JSONB / V33 改回 TEXT[] / V34 修正：改回 JSONB，与后端 V40 §5.2.10 对齐
    mentions JSONB,
    CONSTRAINT check_sender_type CHECK (
        (sender_type = 'user' AND sender_id IS NOT NULL) OR
        (sender_type = 'agent' AND sender_id IS NOT NULL) OR
        (sender_type IS NULL AND sender_id IS NULL)
    )
);

-- 索引
CREATE INDEX idx_group_messages_group ON group_messages(group_id);
CREATE INDEX idx_group_messages_sender ON group_messages(sender_id, sender_type);
CREATE INDEX idx_group_messages_timestamp ON group_messages(timestamp);
CREATE INDEX idx_group_messages_metadata_gin ON group_messages USING gin(metadata);
-- V34 修正：GIN 索引操作符类从 text_pattern_gin 改回 jsonb_path_ops（JSONB 类型）
CREATE INDEX idx_group_messages_mentions_gin ON group_messages USING gin(mentions jsonb_path_ops);

COMMENT ON COLUMN group_messages.message_type IS '消息类型：text表示普通文本消息，system表示系统通知，meeting表示会议记录（V20 改用枚举类型，V28 修正枚举值）';
COMMENT ON COLUMN group_messages.sender_id IS '发送者ID：sender_type=user时指向users.id，sender_type=agent时指向agents.id';
COMMENT ON COLUMN group_messages.sender_type IS '发送者类型：user表示人类用户，agent表示AI Agent（V34 修正：移除 system，与后端 V40 对齐）';
COMMENT ON COLUMN group_messages.mentions IS 'V28 新增/V34 修正：被提及的用户/Agent ID 数组（JSONB 类型，与后端 V40 对齐）';

-- V17 说明 / V19 修正：sender_id 外键约束说明
-- PostgreSQL 不支持单字段多目标条件外键（即一个字段根据 sender_type 值指向不同表），
-- 因此 sender_id 未定义 REFERENCES 约束。V19 新增触发器级别校验兜底。
-- 1. 插入消息前，应用层校验 sender_id 是否存在于对应表
--    - sender_type='user' 时校验 sender_id EXISTS IN users(id)
--    - sender_type='agent' 时校验 sender_id EXISTS IN agents(id)
-- 2. 删除用户/Agent 前，应用层检查是否存在未删除的群消息引用该 ID
-- 3. 应用层 INSERT 语句中应包含类似以下校验逻辑：
--    INSERT INTO group_messages (...) VALUES (...)
--    WHERE EXISTS (
--      SELECT 1 FROM (
--        CASE WHEN $sender_type = 'user'
--          THEN (SELECT id FROM users WHERE id = $sender_id)
--          ELSE (SELECT id FROM agents WHERE id = $sender_id)
--        END
--      ) AS valid_sender
--    );

-- V19 新增 / V34 修正：触发器级别 sender_id 校验兜底
-- V34 修正：移除 system 类型处理，仅保留 user 和 agent 二值
CREATE OR REPLACE FUNCTION validate_sender_exists()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.sender_type = 'user' AND NEW.sender_id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM users WHERE id = NEW.sender_id) THEN
            RAISE EXCEPTION '用户ID不存在: sender_id=%', NEW.sender_id;
        END IF;
    ELSIF NEW.sender_type = 'agent' AND NEW.sender_id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM agents WHERE id = NEW.sender_id) THEN
            RAISE EXCEPTION 'Agent ID不存在: sender_id=%', NEW.sender_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_validate_sender
    BEFORE INSERT OR UPDATE OF sender_id, sender_type ON group_messages
    FOR EACH ROW
    EXECUTE FUNCTION validate_sender_exists();

-- NOTE: 分区策略详见第 7 节
