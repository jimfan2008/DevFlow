-- ============================================================
-- DevFlow DATABASE V37 - 通知表
-- File: 16-notifications.sql
-- ============================================================

-- ============================================================
-- 通知表
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    type notification_type NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_project ON notifications(project_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_user_project ON notifications(user_id, project_id);

-- V20/V21 新增：updated_at 触发器，与其他含 updated_at 的表保持一致
CREATE TRIGGER IF NOT EXISTS update_notifications_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- V37 新增：表注释
COMMENT ON TABLE notifications IS '通知表 - 系统通知消息，project_id 可空';
-- V37 新增：字段注释
COMMENT ON COLUMN notifications.id IS '通知唯一标识';
COMMENT ON COLUMN notifications.user_id IS '接收用户 ID';
COMMENT ON COLUMN notifications.project_id IS '关联项目 ID（可空）';
COMMENT ON COLUMN notifications.type IS '通知类型';
COMMENT ON COLUMN notifications.is_read IS '是否已读';
COMMENT ON COLUMN notifications.deleted_at IS '软删除时间戳';
