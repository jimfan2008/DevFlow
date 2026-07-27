# DevFlow 项目管理平台 - 数据库设计文档

**版本**: V6  
**日期**: 2026-06-15  
**作者**: HouWang (后旺)  
**状态**: 修订版V6（修复V5审查不合格项）

---

## 1. ER 概述

### 1.1 实体关系图

```
┌──────────┐     ┌───────────┐     ┌──────────────┐
│  users   ├─────▶│ projects  ├─────▶│ requirements │
└──────────┘     └───────────┘     └──────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
     ┌──────────┐ ┌────────┐ ┌──────────┐
     │  groups  │ │ tasks  │ │  repos   │
     │  (1:1)   │ │        │ │          │
     └──────────┘ └────────┘ └──────────┘
          │           │           │
          ▼           ▼           ▼
   ┌─────────────┐ ┌──────────────────┐ ┌─────────────┐
   │group_members│ │task_dependencies  │ │repo_branches│
   └─────────────┘ └──────────────────┘ └─────────────┘
          │                      │
          ▼                      ▼
   ┌──────────────┐      ┌─────────────┐
   │group_messages│      │pull_requests│
   └──────────────┘      └─────────────┘
                                   │
                                   ▼
                            ┌──────────┐
                            │ commits  │
                            └──────────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │ task_commits │  (N:M 关联表)
                            └──────────────┘

┌──────────┐  1:N  ┌────────┐
│  agents  ├───────▶│  tasks │
└──────────┘       └────────┘
       │
       ▼
  ┌──────────┐
  │  swarms  │
  └──────────┘
       │         │
       │    1:N  │
       │      ┌──┤
       ▼      ▼
  ┌──────────────┐
  │swarm_members │
  └──────────────┘

┌──────────┐     ┌───────────┐     ┌──────────┐
│  tasks   ├─────▶│qa_records │◀────┤  agents  │
└──────────┘     └───────────┘     └──────────┘
                    (N:1 tasks, N:1 agents reviewer)

┌──────────┐     ┌──────────────────┐     ┌──────────┐
│ projects ├─────▶│  notifications   │◀────┤  users   │
└──────────┘     └──────────────────┘     └──────────┘

┌──────────┐     ┌───────────────────┐
│  tasks   ├─────▶│agent_execution_logs│
└──────────┘     └───────────────────┘

┌──────────┐     ┌──────────────────┐
│  groups  ├─────▶│meeting_outcomes  │
└──────────┘     └──────────────────┘
```

### 1.2 核心实体说明

| 实体 | 描述 | 关联 |
|------|------|------|
| users | 人类用户 | 1:N projects, 1:N notifications, 1:N tasks(assignee) |
| projects | 软件项目 | N:1 users, 1:N tasks, 1:1 groups, 1:1 repos |
| requirements | 软件需求说明书 | N:1 projects |
| agents | Agent角色 | 1:N tasks, 1:N swarms, 1:N group_members |
| tasks | 开发任务 | N:1 projects, N:1 agents/N:1 swarms/N:1 users (三选一分配), N:M task_dependencies |
| groups | 项目讨论群 | 1:1 projects, 1:N group_members, 1:N group_messages |
| swarms | Agent蜂群 | N:1 projects, N:1 agents(manager), 1:N swarm_members, 1:N tasks(assignee) |
| qa_records | QA检验记录 | N:1 tasks, N:1 agents(reviewer) |
| repos | 代码仓库 | 1:1 projects, 1:N pull_requests |
| notifications | 通知消息 | N:1 users, N:1 projects |
| agent_execution_logs | Agent执行日志 | N:1 tasks, N:1 agents |
| meeting_outcomes | 会议结果 | N:1 groups, N:1 agents(host) |
| repo_branches | 代码分支 | N:1 repos |
| commits | 提交记录 | N:1 repos |
| task_commits | 任务与提交关联 | N:1 tasks, N:1 commits |

---

## 2. 完整SQL DDL脚本

### 2.1 基础设置

```sql
-- ============================================================
-- DevFlow 项目管理平台数据库初始化脚本
-- 数据库: PostgreSQL 14+
-- 日期: 2026-06-12
-- ============================================================

-- 创建数据库（如果在外部执行）
-- CREATE DATABASE devflow_db;

-- 设置扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建枚举类型
CREATE TYPE user_role AS ENUM ('user', 'admin', 'system_admin');
CREATE TYPE project_status AS ENUM ('created', 'in_progress', 'completed', 'cancelled');
CREATE TYPE agent_type AS ENUM ('named', 'swarm');
CREATE TYPE agent_status AS ENUM ('online', 'offline', 'busy');
CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'cancelled');
CREATE TYPE task_type AS ENUM ('requirement_analysis', 'architecture_design', 'backend_design', 
                                'frontend_design', 'database_design', 'environment_setup',
                                'tdd_test_plan', 'tdd_test_writing', 'code_writing_plan',
                                'code_writing', 'test_deployment', 'testing', 'security_audit',
                                'production_deployment', 'documentation', 'delivery_report');
CREATE TYPE group_mode AS ENUM ('discussion', 'meeting');
CREATE TYPE member_type AS ENUM ('user', 'agent');
CREATE TYPE sender_type AS ENUM ('user', 'agent');
CREATE TYPE meeting_type AS ENUM ('requirement_review', 'tech_solution', 'daily_standup', 
                                  'incident_postmortem');
CREATE TYPE swarm_purpose AS ENUM ('code_writing', 'testing');
CREATE TYPE swarm_status AS ENUM ('active', 'completed', 'dissolved');
CREATE TYPE qa_result AS ENUM ('pass', 'fail');
CREATE TYPE notification_type AS ENUM ('step_complete', 'qa_pass', 'qa_fail', 'task_assigned',
                                       'task_completed', 'project_complete', 'system_alert');
CREATE TYPE pr_status AS ENUM ('open', 'closed', 'merged');
```

### 2.2 用户表

```sql
-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- 更新时间戳触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.3 项目表

```sql
-- ============================================================
-- 项目表
-- ============================================================
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,  -- 业务编号: proj-YYYYMMDD-NNN
    name VARCHAR(200) NOT NULL,
    description TEXT,
    creator_id INTEGER NOT NULL REFERENCES users(id),
    core_goal TEXT,
    status project_status NOT NULL DEFAULT 'created',
    current_step INTEGER NOT NULL DEFAULT 1,
    CHECK (current_step >= 1 AND current_step <= 100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_projects_creator ON projects(creator_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_name ON projects(name) USING gin(name gin_trgm_ops);
CREATE INDEX idx_projects_deleted ON projects(deleted_at);
CREATE INDEX idx_projects_code ON projects(code);

-- 触发器
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 触发器：当任务状态变更时自动更新项目的current_step
CREATE OR REPLACE FUNCTION sync_project_current_step()
RETURNS TRIGGER AS $$
DECLARE
    v_project_id INTEGER;
    v_max_step INTEGER;
BEGIN
    v_project_id := COALESCE(NEW.project_id, OLD.project_id);

    -- 使用 FOR UPDATE 锁避免多任务并发完成时的竞态条件
    SELECT COALESCE(MAX(step_number), 0) INTO v_max_step
    FROM tasks
    WHERE project_id = v_project_id AND status = 'completed'
    FOR UPDATE;

    IF v_max_step > 0 THEN
        UPDATE projects SET current_step = v_max_step + 1
        WHERE id = v_project_id;
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_sync_project_current_step
    AFTER INSERT OR UPDATE OF status, step_number ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION sync_project_current_step();
```

### 2.4 需求表

```sql
-- ============================================================
-- 需求表（软件需求说明书）
-- ============================================================
CREATE TABLE requirements (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_requirements_project ON requirements(project_id);
-- 联合唯一索引：同一项目的同一版本唯一
CREATE UNIQUE INDEX idx_requirements_project_version ON requirements(project_id, version);

-- 触发器
CREATE TRIGGER update_requirements_updated_at
    BEFORE UPDATE ON requirements
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.5 Agent角色表

```sql
-- ============================================================
-- Agent角色表（9个命名Agent + 编程Agent蜂群）
-- ============================================================
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    agent_type agent_type NOT NULL DEFAULT 'named',
    role_name VARCHAR(100) NOT NULL,
    chinese_name VARCHAR(50),
    status agent_status NOT NULL DEFAULT 'offline',
    api_endpoint VARCHAR(255),
    model_default VARCHAR(100),
    model_provider VARCHAR(100),
    config JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_name ON agents(name);
CREATE INDEX idx_agents_config_gin ON agents USING gin(config);

-- 触发器
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 初始化9个命名Agent
INSERT INTO agents (name, agent_type, role_name, chinese_name, status) VALUES
('haimei', 'named', 'project_manager', '海梅', 'offline'),
('houxing', 'named', 'requirement_analyst', '后兴', 'offline'),
('houwang', 'named', 'architect', '后旺', 'offline'),
('houfa', 'named', 'programmer', '后发', 'offline'),
('houbada', 'named', 'tester', '后达', 'offline'),
('houfu', 'named', 'cicd_engineer', '后富', 'offline'),
('hougui', 'named', 'document_admin', '后贵', 'offline'),
('hourong', 'named', 'qa', '后荣', 'offline'),
('houhua', 'named', 'security_auditor', '后华', 'offline');
```

### 2.6 任务表

```sql
-- ============================================================
-- 任务表
-- ============================================================
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    type task_type NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    -- 任务分配三选一: assignee_agent_id (单个Agent)、assignee_swarm_id (蜂群)、assignee_user_id (人类用户)
    assignee_agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    assignee_swarm_id INTEGER REFERENCES swarms(id) ON DELETE SET NULL,
    assignee_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status task_status NOT NULL DEFAULT 'pending',
    acceptance_criteria JSONB,
    step_number INTEGER NOT NULL,
    CHECK (step_number >= 1 AND step_number <= 100),
    is_atomic BOOLEAN NOT NULL DEFAULT TRUE,
    parent_task_id INTEGER REFERENCES tasks(id),
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CHECK (completed_at IS NULL OR completed_at >= created_at)
);

-- 索引
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_agent_id);
CREATE INDEX idx_tasks_swarm ON tasks(assignee_swarm_id);
CREATE INDEX idx_tasks_assignee_user ON tasks(assignee_user_id);
CREATE INDEX idx_tasks_step ON tasks(step_number);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX idx_tasks_deleted ON tasks(deleted_at);
CREATE INDEX idx_tasks_acceptance_criteria_gin ON tasks USING gin(acceptance_criteria);

-- 触发器
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 触发器：确保子任务的project_id与父任务的project_id一致
CREATE OR REPLACE FUNCTION check_parent_same_project()
RETURNS TRIGGER AS $$
DECLARE
    parent_project_id INTEGER;
BEGIN
    IF NEW.parent_task_id IS NOT NULL THEN
        SELECT project_id INTO parent_project_id FROM tasks WHERE id = NEW.parent_task_id;
        IF parent_project_id IS DISTINCT FROM NEW.project_id THEN
            RAISE EXCEPTION '子任务的project_id必须与父任务的project_id一致: 子任务项目=%, 父任务项目=%',
                            NEW.project_id, parent_project_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_enforce_parent_same_project
    BEFORE INSERT OR UPDATE OF parent_task_id, project_id ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION check_parent_same_project();
```

### 2.7 任务依赖表

```sql
-- ============================================================
-- 任务依赖表
-- ============================================================
CREATE TABLE task_dependencies (
    id SERIAL PRIMARY KEY,
    source_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    target_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'finish_to_start',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(source_task_id, target_task_id),
    CHECK (source_task_id <> target_task_id)
);

-- NOTE: 循环依赖检测采用双重保障：应用层执行完整拓扑排序校验，数据库层通过触发器进行兜底环检测。

-- 索引
CREATE INDEX idx_task_deps_source ON task_dependencies(source_task_id);
CREATE INDEX idx_task_deps_target ON task_dependencies(target_task_id);

-- 触发器：确保 source 和 target 任务属于同一 project_id
CREATE OR REPLACE FUNCTION check_same_project_dependency()
RETURNS TRIGGER AS $$
DECLARE
    source_project_id INTEGER;
    target_project_id INTEGER;
BEGIN
    SELECT project_id INTO source_project_id FROM tasks WHERE id = NEW.source_task_id;
    SELECT project_id INTO target_project_id FROM tasks WHERE id = NEW.target_task_id;
    IF source_project_id IS DISTINCT FROM target_project_id THEN
        RAISE EXCEPTION '依赖关系的两个任务必须属于同一项目: source项目=%, target项目=%',
                        source_project_id, target_project_id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER enforce_same_project_dependency
    BEFORE INSERT OR UPDATE OF source_task_id, target_task_id ON task_dependencies
    FOR EACH ROW
    EXECUTE FUNCTION check_same_project_dependency();

-- 数据库级循环依赖检测触发器（兜底保障）
CREATE OR REPLACE FUNCTION check_circular_dependency()
RETURNS TRIGGER AS $$
DECLARE
    v_source INTEGER := NEW.source_task_id;
    v_target INTEGER := NEW.target_task_id;
    v_current INTEGER;
    v_visited_count INTEGER := 0;
    v_max_depth INTEGER := 100;
BEGIN
    v_current := v_target;
    WHILE v_current IS NOT NULL AND v_visited_count < v_max_depth LOOP
        SELECT source_task_id INTO v_current
        FROM task_dependencies
        WHERE target_task_id = v_current
        AND source_task_id <> v_target
        LIMIT 1;
        
        IF v_current = v_source THEN
            RAISE EXCEPTION '检测到循环依赖: 任务 % -> 任务 % 将形成环', v_source, v_target;
        END IF;
        
        v_visited_count := v_visited_count + 1;
    END LOOP;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_check_circular_dependency
    BEFORE INSERT OR UPDATE ON task_dependencies
    FOR EACH ROW
    EXECUTE FUNCTION check_circular_dependency();
```

### 2.8 Agent执行日志表

```sql
-- ============================================================
-- Agent执行日志表
-- ============================================================
CREATE TABLE agent_execution_logs (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE SET NULL,
    execution_content TEXT,
    result JSONB,
    execution_time_seconds DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_exec_logs_task ON agent_execution_logs(task_id);
CREATE INDEX idx_exec_logs_agent ON agent_execution_logs(agent_id);
CREATE INDEX idx_exec_logs_created ON agent_execution_logs(created_at);
```

### 2.9 QA检验记录表

```sql
-- ============================================================
-- QA检验记录表（后荣检验记录）
-- ============================================================
CREATE TABLE qa_records (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    reviewer_agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE SET NULL,
    acceptance_result qa_result NOT NULL,
    problem_details TEXT,
    review_dimensions JSONB NOT NULL,
    score DECIMAL(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_qa_records_task ON qa_records(task_id);
CREATE INDEX idx_qa_records_reviewer ON qa_records(reviewer_agent_id);
CREATE INDEX idx_qa_records_result ON qa_records(acceptance_result);
CREATE INDEX idx_qa_review_dimensions_gin ON qa_records USING gin(review_dimensions);

COMMENT ON COLUMN qa_records.score IS '综合评分(0-100) = 各维度得分的算术平均值';
COMMENT ON COLUMN qa_records.review_dimensions IS 'JSON数组，包含各维度的名称、量化标准、实际得分、合格阈值、是否达标';
```

### 2.10 群组表

```sql
-- ============================================================
-- 群组表（项目讨论群，与项目 1:1 关系）
-- ============================================================
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    mode group_mode NOT NULL DEFAULT 'discussion',
    host_agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_groups_project ON groups(project_id);
CREATE INDEX idx_groups_mode ON groups(mode);

-- 触发器
CREATE TRIGGER update_groups_updated_at
    BEFORE UPDATE ON groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.11 群组-成员关联表

```sql
-- ============================================================
-- 群组-成员关联表
-- ============================================================
CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    agent_id INTEGER REFERENCES agents(id),
    member_type member_type NOT NULL,
    role_in_group VARCHAR(50),
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT check_member_type CHECK (
        (member_type = 'user' AND user_id IS NOT NULL AND agent_id IS NULL) OR
        (member_type = 'agent' AND agent_id IS NOT NULL AND user_id IS NULL)
    )
);

CREATE UNIQUE INDEX idx_group_members_user ON group_members(group_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX idx_group_members_agent ON group_members(group_id, agent_id) WHERE agent_id IS NOT NULL;

-- 索引
CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user_only ON group_members(user_id);
CREATE INDEX idx_group_members_agent_only ON group_members(agent_id);
```

### 2.12 群聊消息表

```sql
-- ============================================================
-- 群聊消息表
-- ============================================================
CREATE TABLE group_messages (
    id BIGSERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    sender_user_id INTEGER REFERENCES users(id),
    sender_agent_id INTEGER REFERENCES agents(id),
    role VARCHAR(100),
    content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (message_type IN ('system', 'agent', 'user')),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_streaming BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    CONSTRAINT check_sender CHECK (
        (message_type = 'user' AND sender_user_id IS NOT NULL AND sender_agent_id IS NULL) OR
        (message_type = 'agent' AND sender_agent_id IS NOT NULL AND sender_user_id IS NULL) OR
        (message_type = 'system' AND sender_user_id IS NULL AND sender_agent_id IS NULL)
    )
);

-- 索引
CREATE INDEX idx_group_messages_group ON group_messages(group_id);
CREATE INDEX idx_group_messages_sender ON group_messages(sender_user_id, sender_agent_id);
CREATE INDEX idx_group_messages_timestamp ON group_messages(timestamp);
CREATE INDEX idx_group_messages_metadata_gin ON group_messages USING gin(metadata);

COMMENT ON COLUMN group_messages.message_type IS '消息类型：system表示系统通知，agent表示Agent消息，user表示人类用户消息';
COMMENT ON COLUMN group_messages.sender_user_id IS '发送者ID（人类用户时指向users.id）';
COMMENT ON COLUMN group_messages.sender_agent_id IS '发送者ID（Agent时指向agents.id）';

-- NOTE: 分区策略规划
-- group_messages 按 timestamp 字段进行 RANGE 范围分区（按月）
-- 单个分区数据量控制在 500 万行以内
-- 实际分区 DDL 在数据库初始化时通过 CREATE TABLE ... PARTITION BY RANGE (timestamp) 实现
-- 当前 BIGSERIAL 主键设计已为高并发分区场景预留
```

### 2.13 会议结果表

```sql
-- ============================================================
-- 会议结果表
-- ============================================================
CREATE TABLE meeting_outcomes (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    meeting_topic VARCHAR(200) NOT NULL,
    meeting_type meeting_type NOT NULL DEFAULT 'requirement_review',
    host_agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE SET NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    minutes TEXT,
    decisions JSONB,
    todos JSONB,
    risks JSONB,
    open_issues JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CHECK (ended_at IS NULL OR ended_at >= started_at)
);

-- 索引
CREATE INDEX idx_meeting_outcomes_group ON meeting_outcomes(group_id);
CREATE INDEX idx_meeting_outcomes_host ON meeting_outcomes(host_agent_id);
CREATE INDEX idx_meeting_outcomes_composite ON meeting_outcomes(group_id, host_agent_id);
```

### 2.14 Agent蜂群表

```sql
-- ============================================================
-- Agent蜂群表
-- ============================================================
CREATE TABLE swarms (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    manager_agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE SET NULL,
    purpose swarm_purpose NOT NULL,
    status swarm_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dissolved_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_swarms_project ON swarms(project_id);
CREATE INDEX idx_swarms_manager ON swarms(manager_agent_id);
CREATE INDEX idx_swarms_status ON swarms(status);

-- 触发器
CREATE TRIGGER update_swarms_updated_at
    BEFORE UPDATE ON swarms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 管理器自动注册为 swarm_members 的约束
CREATE OR REPLACE FUNCTION ensure_manager_in_swarm_members()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO swarm_members (swarm_id, agent_id, status)
    VALUES (NEW.id, NEW.manager_agent_id, 'active')
    ON CONFLICT (swarm_id, agent_id) DO NOTHING;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER auto_add_manager_to_members
    AFTER INSERT ON swarms
    FOR EACH ROW
    EXECUTE FUNCTION ensure_manager_in_swarm_members();
```

### 2.15 蜂群-成员关联表

```sql
-- ============================================================
-- 蜂群-成员关联表
-- ============================================================
CREATE TABLE swarm_members (
    id SERIAL PRIMARY KEY,
    swarm_id INTEGER NOT NULL REFERENCES swarms(id) ON DELETE CASCADE,
    agent_id INTEGER NOT NULL REFERENCES agents(id),
    registered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    skills JSONB,
    UNIQUE(swarm_id, agent_id)
);

-- 索引
CREATE INDEX idx_swarm_members_swarm ON swarm_members(swarm_id);
CREATE INDEX idx_swarm_members_agent ON swarm_members(agent_id);
```

### 2.16 通知表

```sql
-- ============================================================
-- 通知表
-- ============================================================
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    -- user_id为必填字段，用户删除时级联删除关联通知，避免孤儿通知记录
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    type notification_type NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_project ON notifications(project_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_user_project ON notifications(user_id, project_id);
```

### 2.17 代码仓库表

```sql
-- ============================================================
-- 代码仓库表
-- ============================================================
CREATE TABLE repos (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,
    vcs_platform VARCHAR(20) NOT NULL DEFAULT 'gitea' CHECK (vcs_platform IN ('gitea', 'github', 'gitlab')),
    vcs_repo_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    url VARCHAR(500) NOT NULL,
    ssh_url VARCHAR(500),
    http_url VARCHAR(500),
    default_branch VARCHAR(50) NOT NULL DEFAULT 'main',
    is_private BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(vcs_platform, vcs_repo_id)
);

-- 索引
CREATE INDEX idx_repos_vcs_id ON repos(vcs_platform, vcs_repo_id);
```

### 2.18 分支表

```sql
-- ============================================================
-- 分支表
-- ============================================================
CREATE TABLE repo_branches (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    commit_sha VARCHAR(40),
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, name)
);

-- 索引
CREATE INDEX idx_repo_branches_repo ON repo_branches(repo_id);

-- 触发器
CREATE TRIGGER update_repo_branches_updated_at
    BEFORE UPDATE ON repo_branches
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.19 Pull Request表

```sql
-- ============================================================
-- Pull Request表
-- ============================================================
CREATE TABLE pull_requests (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    source_branch VARCHAR(100) NOT NULL,
    target_branch VARCHAR(100) NOT NULL,
    author VARCHAR(100),
    status pr_status NOT NULL DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    merged_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(repo_id, number)
);

-- 索引
CREATE INDEX idx_prs_repo ON pull_requests(repo_id);
CREATE INDEX idx_prs_status ON pull_requests(status);

-- 触发器
CREATE TRIGGER update_pull_requests_updated_at
    BEFORE UPDATE ON pull_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2.20 提交记录表

```sql
-- ============================================================
-- 提交记录表
-- ============================================================
CREATE TABLE commits (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    sha VARCHAR(40) NOT NULL,
    message TEXT NOT NULL,
    author_name VARCHAR(100),
    author_email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, sha)
);

-- 索引
CREATE INDEX idx_commits_repo ON commits(repo_id);
```

### 2.21 任务与提交关联表

```sql
-- ============================================================
-- 任务与提交关联表
-- ============================================================
CREATE TABLE task_commits (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(task_id, commit_id)
);

-- 索引
CREATE INDEX idx_task_commits_task ON task_commits(task_id);
CREATE INDEX idx_task_commits_commit ON task_commits(commit_id);
```

---

## 3. 视图和存储过程

### 3.1 项目进度视图

```sql
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
```

### 3.2 Agent负载视图

```sql
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
```

### 3.3 QA检验统计视图

```sql
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
```

---

## 4. 数据初始化

### 4.1 初始化命名Agent数据

```sql
-- 9个命名Agent已在上文agents表创建时初始化
-- api_endpoint由应用层在首次启动时从环境变量或配置文件写入，不硬编码在DDL脚本中
```

### 4.2 创建默认管理员用户

```sql
-- 注意：实际密码应使用bcrypt哈希
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@devflow.local', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36PQm3iVJQZr3uVILE6WQeO', 'system_admin');
```

---

## 5. 权限设置

```sql
-- ============================================================
-- 数据库用户和权限设置
-- ============================================================

-- 创建应用用户
-- CREATE USER devflow_app WITH PASSWORD 'secure_password';
-- GRANT CONNECT ON DATABASE devflow_db TO devflow_app;
-- GRANT USAGE ON SCHEMA public TO devflow_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO devflow_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO devflow_app;

-- 创建只读用户（用于报表和监控）
-- CREATE USER devflow_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE devflow_db TO devflow_readonly;
-- GRANT USAGE ON SCHEMA public TO devflow_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO devflow_readonly;
```

---

## 6. 软删除说明

- **软删除字段**: projects、tasks、groups、swarms、notifications 表包含 deleted_at 字段
- **逻辑删除**: 设置为非 NULL 表示逻辑删除，数据仍然保留在数据库中
- **物理删除**: 仅在数据保留超过 90 天后执行物理删除（通过定时任务清理）
- **查询过滤**: 应用层查询默认过滤 deleted_at IS NULL 的记录

---

**文档结束**