-- ============================================================
-- DevFlow DATABASE V34 - 基础设置 - 扩展与枚举类型定义
-- File: 01-enums.sql
-- ============================================================

-- ============================================================
-- DevFlow 项目管理平台数据库初始化脚本
-- 数据库: PostgreSQL 14+
-- 日期: 2026-06-29
-- V34 修正: 修正 4 个枚举类型以与后端 V40 对齐
-- ============================================================

-- 设置扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- V9 新增：citext 扩展，用于不区分大小写的电子邮件比较
CREATE EXTENSION IF NOT EXISTS "citext";

-- 创建枚举类型
-- V34 修正：恢复 system_admin，与后端 V40 §5.2.1 对齐
CREATE TYPE user_role AS ENUM ('user', 'admin', 'system_admin');
-- V34 修正：从 V33 的 (active, paused, completed, archived) 改为 (created, in_progress, completed, cancelled)，与后端 V40 §5.2.2 对齐
CREATE TYPE project_status AS ENUM ('created', 'in_progress', 'completed', 'cancelled');
CREATE TYPE agent_type AS ENUM ('named', 'swarm');
-- V34 修正：从 V33 的 (idle, busy, error, offline) 改为 (online, offline, busy)，与后端 V40 §5.2.4 对齐
CREATE TYPE agent_status AS ENUM ('online', 'offline', 'busy');
CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'cancelled');
CREATE TYPE task_type AS ENUM ('requirement_analysis', 'architecture_design', 'backend_design',
                               'frontend_design', 'database_design', 'environment_setup',
                               'tdd_test_plan', 'tdd_test_writing', 'code_writing_plan',
                               'code_writing', 'test_deployment', 'testing', 'security_audit',
                               'production_deployment', 'documentation', 'delivery_report');
CREATE TYPE group_mode AS ENUM ('discussion', 'meeting');
CREATE TYPE member_type AS ENUM ('user', 'agent');
-- V34 修正：移除 system，改为二值 (user, agent)，与后端 V40 §5.2.10 对齐
CREATE TYPE sender_type AS ENUM ('user', 'agent');
-- V14 修正 V16 确认：meeting_type 枚举定义完整（闭合引号、括号及分号均已到位）
CREATE TYPE meeting_type AS ENUM ('requirement_review', 'tech_solution', 'daily_standup',
                                  'incident_postmortem');
-- V14 新增 V16 确认：dependency_type 枚举类型定义，与 task_dependencies 表 CHECK 约束保持一致
CREATE TYPE dependency_type_enum AS ENUM ('finish_to_start', 'start_to_start',
                                          'finish_to_finish', 'start_to_finish');
CREATE TYPE swarm_purpose AS ENUM ('code_writing', 'testing', 'tdd_test');
CREATE TYPE swarm_status AS ENUM ('active', 'completed', 'dissolved');
CREATE TYPE qa_result AS ENUM ('pass', 'fail');
CREATE TYPE notification_type AS ENUM ('step_complete', 'qa_pass', 'qa_fail', 'task_assigned',
                                       'task_completed', 'project_complete', 'system_alert');
CREATE TYPE pr_status AS ENUM ('open', 'closed', 'merged');

-- V20/V21 新增：蜂群成员状态枚举（与原 swarm_status 枚举值域不同，语义区分清楚）
-- swarm_status 描述蜂群整体状态（active/completed/dissolved）
-- swarm_member_status 描述蜂群成员个体状态（active/inactive/removed）
CREATE TYPE swarm_member_status AS ENUM ('active', 'inactive', 'removed');

-- V20/V21 新增 V28 修正：消息类型枚举，取代 group_messages 表中 VARCHAR(20)+CHECK 约束
-- V28 修正：枚举值从 (system, agent, user) 改为 (text, system, meeting) 以匹配后端 schema
CREATE TYPE message_type_enum AS ENUM ('text', 'system', 'meeting');

-- V34 修正：agent_status 应用层管理注释
-- agent_status 枚举定义了三种状态 ('online', 'offline', 'busy')
-- 但实际状态切换逻辑由应用层管理，数据库仅做存储：
--   - 'online': Agent 可用，可被分配新任务
--   - 'busy': Agent 正在执行任务中（任务分配时由应用层自动设置）
--   - 'offline': Agent 不可用或空闲（任务完成/失败/取消时由应用层恢复）
-- 数据库不通过触发器自动切换状态，避免数据库层与应用层状态管理冲突
