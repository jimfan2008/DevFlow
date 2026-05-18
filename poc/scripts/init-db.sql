#!/bin/bash
# PostgreSQL 数据库初始化脚本
# 用途：在容器启动时自动执行初始化配置

set -e

echo "=== PostgreSQL 初始化脚本 ==="
echo "执行时间：$(date)"

# 等待数据库就绪
echo "等待数据库就绪..."
until psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
    echo "数据库未就绪，等待 2 秒..."
    sleep 2
done

echo "数据库已就绪"

# 创建扩展
echo "创建必要的扩展..."
psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<EOF
-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用 JSONB 扩展（已内置，但确保可用）
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建审计表（如果不存在）
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(255) NOT NULL,
    action VARCHAR(20) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(100)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_record_id ON audit_log(record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit_log(changed_at);

-- 创建配置表
CREATE TABLE IF NOT EXISTS app_config (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    description VARCHAR(500),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- 插入默认配置
INSERT INTO app_config (key, value, description) VALUES
    ('app.name', 'DevFlow', '应用程序名称'),
    ('app.version', '1.0.0', '应用程序版本'),
    ('app.debug', 'false', '调试模式'),
    ('cache.enabled', 'true', '缓存启用状态')
ON CONFLICT (key) DO NOTHING;

-- 创建性能监控表
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tags JSONB
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_perf_metrics_name ON performance_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_perf_metrics_timestamp ON performance_metrics(timestamp);

-- 创建 API 密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    permissions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at);

-- 创建模块依赖表（用于依赖检测）
CREATE TABLE IF NOT EXISTS module_dependencies (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR(255) NOT NULL,
    depends_on VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(50) DEFAULT 'hard',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(module_name, depends_on)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_module_deps_module ON module_dependencies(module_name);
CREATE INDEX IF NOT EXISTS idx_module_deps_depends ON module_dependencies(depends_on);

-- 创建循环依赖检测视图
CREATE OR REPLACE VIEW cyclic_dependency_report AS
SELECT 
    md1.module_name AS module_a,
    md1.depends_on AS module_b,
    md2.module_name AS module_c,
    md2.depends_on AS module_d,
    CASE 
        WHEN md1.depends_on = md2.module_name THEN '可能循环：A -> B'
        WHEN md2.depends_on = md1.module_name THEN '可能循环：C -> D'
        ELSE '正常依赖'
    END AS status
FROM module_dependencies md1
LEFT JOIN module_dependencies md2 
    ON md1.depends_on = md2.module_name 
    AND md2.depends_on = md1.module_name
WHERE md1.module_name != md1.depends_on;

-- 统计模块依赖
DO $$
DECLARE
    module_count INTEGER;
    dependency_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO module_count FROM (SELECT DISTINCT module_name FROM module_dependencies) AS modules;
    SELECT COUNT(*) INTO dependency_count FROM module_dependencies;
    
    RAISE NOTICE '初始化完成：发现 % 个模块，% 个依赖关系', module_count, dependency_count;
END $$;

EOF

echo "=== PostgreSQL 初始化完成 ==="
echo "完成时间：$(date)"
