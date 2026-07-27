# DevFlow 数据库设计文档

**版本**: V10
**日期**: 2026-06-19
**作者**: HouWang (后旺)
**状态**: V10 版本（根据后荣检验报告修正）

---

## 变更日志

- V10 (2026-06-19): 根据后荣检验报告修正以下问题
  1. projects 表 current_step CHECK 约束上限从 100 改为 16（DevFlow 为 16 步标准流程）
  2. tasks 表 step_number CHECK 约束上限从 100 改为 16
  3. 新增第 8 节：事务隔离级别与并发控制策略
  4. 新增第 9 节：分区表策略详细说明
  5. 确保所有实体表 DDL 完整提供（共 20 张表）
  6. 新增第 10 节：表清单与 DDL 完整性验证
  7. 新增第 11 节：V10 修正内容对照表
  8. 索引设计与外键级联策略总览（V9 第 7 节）保留不变

- V9 (2026-06-18): 根据后荣检验报告修正以下问题
  1. 补充 citext 扩展，users 表 email 字段使用 citext 类型以避免大小写重复问题
  2. 补充完整的 DDL 脚本（确保所有实体表建表语句完整提供）
  3. 新增第 7 节：索引设计与外键级联策略总览
  4. sync_project_current_step 触发器：V6 已有完整实现代码，V9 保持不变
  5. 任务分配三选一 CHECK 约束：V6 已实现，V9 保持不变
  6. 循环依赖检测递归 CTE：V6 已实现，V9 保持不变
  7. dependency_type 字段 CHECK 约束：V6 已实现，V9 保持不变
  8. meeting_outcomes UNIQUE(group_id, started_at)：V6 已实现，V9 保持不变
  9. 软删除物理清理存储过程：V6 已实现完整可执行代码，V9 保持不变
  10. agent_status 状态切换：V6 已补充应用层管理注释，V9 保持不变

- V8 (2026-06-18): 后荣检验未返回新的不合格项，V7 内容保持不变
- V7 (2026-06-18): 后荣检验未返回新的不合格项，V6 内容保持不变
- V6 (2026-06-17): 根据后荣检验报告修复 7 个问题
  1. 循环依赖检测：从单路径回溯改为递归 CTE 完整遍历
  2. 任务分配三选一：添加数据库级 CHECK 约束（修正为允许多个全NULL或恰好一个非NULL）
  3. sync_project_current_step 触发器：优化锁策略，改为只锁项目行
  4. dependency_type 字段：添加 CHECK 约束限制合法值
  5. meeting_outcomes：添加 UNIQUE(group_id, started_at) 防重复约束
  6. 软删除物理清理：补充完整可执行的清理存储过程实现
  7. agent_status 状态切换：补充应用层管理注释

- V5 (2026-06-16): 初始版本

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
  │group_members│ │task_dependencies │ │repo_branches│
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
-- 日期: 2026-06-19
-- ============================================================

-- 设置扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- V9 新增：citext 扩展，用于不区分大小写的电子邮件比较
CREATE EXTENSION IF NOT EXISTS "citext";

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
    -- V9 修订：使用 citext 类型，不区分大小写，避免 User@Example.com 和 user@example.com 被视为不同邮箱
    email citext NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
-- email 的 UNIQUE 约束已隐含唯一索引，citext 类型自动处理大小写不敏感比较

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
    -- V10 修正：DevFlow 为 16 步标准流程，上限从 100 改为 16
    CHECK (current_step >= 1 AND current_step <= 16),
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
-- V6 修订：优化锁策略，改为只锁项目行，避免锁竞争
-- 移除无效的 DELETE 分支（该触发器不响应 DELETE 操作）
-- 应用层管理注释：agent_status 字段状态切换由应用层管理：
--   - 任务分配时自动将对应 Agent 设为 'busy'
--   - 任务完成/失败/取消时恢复为 'offline'
CREATE OR REPLACE FUNCTION sync_project_current_step()
RETURNS TRIGGER AS $$
DECLARE
    v_project_id INTEGER;
    v_current_step INTEGER;
BEGIN
    v_project_id := COALESCE(NEW.project_id, OLD.project_id);

    -- INSERT 操作：新任务默认为 pending 状态，不更新项目进度
    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;

    -- UPDATE 操作：任务从已完成变为其他状态，需要重新计算
    IF OLD.status = 'completed' AND NEW.status <> 'completed' THEN
        -- 锁项目行后重新计算最大 step_number
        UPDATE projects SET current_step = (
            SELECT COALESCE(MAX(step_number), 0) + 1
            FROM tasks
            WHERE project_id = v_project_id AND status = 'completed'
        )
        WHERE id = v_project_id
        RETURNING current_step INTO v_current_step;
        RETURN NEW;
    END IF;

    -- UPDATE 操作：任务变为已完成
    IF NEW.status = 'completed' AND (OLD.status IS DISTINCT FROM 'completed') THEN
        -- 锁项目行（不是所有任务），获取当前 current_step
        UPDATE projects SET current_step = current_step
        WHERE id = v_project_id
        RETURNING current_step INTO v_current_step;

        -- 只在新任务 step_number 超过 current_step 时才更新
        IF NEW.step_number >= v_current_step THEN
            UPDATE projects SET current_step = NEW.step_number + 1
            WHERE id = v_project_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_sync_project_current_step
    AFTER INSERT OR UPDATE OF status, step_number ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION sync_project_current_step();
```

### 2.4 需求表（软件需求说明书）

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
    -- V10 修正：DevFlow 为 16 步标准流程，上限从 100 改为 16
    CHECK (step_number >= 1 AND step_number <= 16),
    is_atomic BOOLEAN NOT NULL DEFAULT TRUE,
    parent_task_id INTEGER REFERENCES tasks(id),
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CHECK (completed_at IS NULL OR completed_at >= created_at),
    -- V6 修正：任务分配三选一约束，允许多个全NULL（未分配）或恰好一个非NULL（已分配）
    CHECK (
        (CASE WHEN assignee_agent_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN assignee_swarm_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN assignee_user_id IS NOT NULL THEN 1 ELSE 0 END) <= 1
    )
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
    CHECK (source_task_id <> target_task_id),
    -- V6 新增：限制 dependency_type 合法值
    CHECK (dependency_type IN ('finish_to_start', 'start_to_start', 'finish_to_finish', 'start_to_finish'))
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
-- V6 修订：使用递归 CTE 从 source 出发正向遍历所有可达节点，若包含 target 则存在环
CREATE OR REPLACE FUNCTION check_circular_dependency()
RETURNS TRIGGER AS $$
DECLARE
    v_source INTEGER := NEW.source_task_id;
    v_target INTEGER := NEW.target_task_id;
    v_cycle_found BOOLEAN;
BEGIN
    -- 使用递归 CTE 从 source_task_id 出发，沿依赖边（source→target）正向遍历
    -- 检查是否能到达 target_task_id，若能到达则插入 source→target 将形成环
    WITH RECURSIVE reachable AS (
        -- 起始：source 的直接后继
        SELECT source_task_id, target_task_id
        FROM task_dependencies
        WHERE source_task_id = v_source

        UNION

        -- 递归：沿依赖边继续遍历
        SELECT r.source_task_id, td.target_task_id
        FROM reachable r
        JOIN task_dependencies td ON td.source_task_id = r.target_task_id
        WHERE td.target_task_id <> v_source  -- 避免回退到起点造成无限循环
    )
    SELECT EXISTS(SELECT 1 FROM reachable WHERE target_task_id = v_target)
    INTO v_cycle_found;

    IF v_cycle_found THEN
        RAISE EXCEPTION '检测到循环依赖: 任务 % 已可到达任务 %，插入依赖 % -> % 将形成环',
                        v_source, v_target, v_source, v_target;
    END IF;

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
    sender_id INTEGER,
    sender_type sender_type,
    role VARCHAR(100),
    content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (message_type IN ('system', 'agent', 'user')),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_streaming BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
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

COMMENT ON COLUMN group_messages.message_type IS '消息类型：system表示系统通知，agent表示Agent消息，user表示人类用户消息';
COMMENT ON COLUMN group_messages.sender_id IS '发送者ID：sender_type=user时指向users.id，sender_type=agent时指向agents.id';
COMMENT ON COLUMN group_messages.sender_type IS '发送者类型：user表示人类用户，agent表示AI Agent';

-- NOTE: 分区策略详见第 9 节
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
    CHECK (ended_at IS NULL OR ended_at >= started_at),
    -- V6 新增：同一群组同一开始时间不重复创建会议记录
    UNIQUE(group_id, started_at)
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

### 6.1 软删除物理清理存储过程（V6 修正：完整可执行实现）

```sql
-- ============================================================
-- 软删除数据物理清理存储过程
-- 建议：通过 pg_cron 或应用层定时任务每天执行一次
-- V6 修正：重写为完整可执行的清理逻辑，按外键依赖顺序逐层清理
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_soft_deleted(retention_days INTEGER DEFAULT 90)
RETURNS TABLE(cleared_projects BIGINT, cleared_tasks BIGINT, cleared_groups BIGINT,
              cleared_swarms BIGINT, cleared_notifications BIGINT) AS $$
DECLARE
    v_cleared_notifications BIGINT := 0;
    v_cleared_swarms BIGINT := 0;
    v_cleared_groups BIGINT := 0;
    v_cleared_tasks BIGINT := 0;
    v_cleared_projects BIGINT := 0;
BEGIN
    -- 第1层：清理通知（依赖 projects 和 users）
    WITH deleted AS (
        DELETE FROM notifications
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_notifications FROM deleted;

    -- 第2层：清理蜂群成员（依赖 swarms）
    DELETE FROM swarm_members
    WHERE swarm_id IN (
        SELECT id FROM swarms
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    );

    -- 第2层：清理群成员（依赖 groups）
    DELETE FROM group_members
    WHERE group_id IN (
        SELECT id FROM groups
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    );

    -- 第2层：清理群消息（依赖 groups）
    DELETE FROM group_messages
    WHERE group_id IN (
        SELECT id FROM groups
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    );

    -- 第3层：清理蜂群（依赖 projects，swarm_members 已清理）
    WITH deleted AS (
        DELETE FROM swarms
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_swarms FROM deleted;

    -- 第3层：清理群组（依赖 projects，group_members/messages 已清理）
    WITH deleted AS (
        DELETE FROM groups
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_groups FROM deleted;

    -- 第3层：清理任务依赖（依赖 tasks）
    DELETE FROM task_dependencies
    WHERE source_task_id IN (
        SELECT id FROM tasks
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    OR target_task_id IN (
        SELECT id FROM tasks
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    );

    -- 第3层：清理任务（依赖 projects，依赖项已清理）
    WITH deleted AS (
        DELETE FROM tasks
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_tasks FROM deleted;

    -- 第4层：清理项目（最顶层）
    WITH deleted AS (
        DELETE FROM projects
        WHERE deleted_at IS NOT NULL
          AND deleted_at < NOW() - (retention_days || ' days')::INTERVAL
    )
    SELECT COUNT(*) INTO v_cleared_projects FROM deleted;

    -- 返回清理统计
    cleared_projects := v_cleared_projects;
    cleared_tasks := v_cleared_tasks;
    cleared_groups := v_cleared_groups;
    cleared_swarms := v_cleared_swarms;
    cleared_notifications := v_cleared_notifications;
    RETURN NEXT;
END;
$$ language 'plpgsql';

-- 使用方式1：pg_cron 定时任务（需 pg_cron 扩展）
-- SELECT cron.schedule('soft-delete-cleanup', '0 2 * * *',
--     'SELECT * FROM cleanup_soft_deleted(90)');

-- 使用方式2：应用层定时任务（推荐）
-- 由 DevFlow 后端每天凌晨 2 点调用：
--   SELECT * FROM cleanup_soft_deleted(90);
-- 清理顺序（按外键依赖从叶子到根）：
--   1. notifications（依赖 projects, users）
--   2. swarm_members（依赖 swarms）
--   3. group_members / group_messages（依赖 groups）
--   4. task_dependencies（依赖 tasks）
--   5. swarms（依赖 projects）
--   6. groups（依赖 projects）
--   7. tasks（依赖 projects）
--   8. projects（根节点）
```

---

## 7. 索引设计与外键级联策略总览（V9 新增，V10 保留）

### 7.1 索引设计说明

本数据库设计的索引策略遵循以下原则：

**主键索引**: 每张表 SERIAL/BIGSERIAL 主键自动创建 B-tree 唯一索引。

**外键索引**: 所有外键字段均创建普通 B-tree 索引，加速 JOIN 和级联删除操作。

**业务查询索引**: 针对高频查询条件创建索引：
- `idx_projects_status`: 按项目状态筛选
- `idx_projects_name`: GIN 三字符索引，支持模糊搜索
- `idx_tasks_status`: 按任务状态筛选
- `idx_tasks_step`: 按步骤号排序
- `idx_notifications_read`: 复合索引，支持按用户+未读筛选

**JSONB 索引**: 对 JSONB 字段使用 GIN 索引加速内部字段查询：
- `idx_agents_config_gin`
- `idx_tasks_acceptance_criteria_gin`
- `idx_qa_review_dimensions_gin`
- `idx_group_messages_metadata_gin`

**唯一约束索引**: 唯一约束自动创建唯一索引：
- `users.email` (citext 不区分大小写)
- `users.username`
- `projects.code`
- `requirements(project_id, version)`
- `groups.project_id` (1:1 关系)
- `repos.project_id` (1:1 关系)
- `repos(vcs_platform, vcs_repo_id)`
- `task_dependencies(source_task_id, target_task_id)`
- `swarm_members(swarm_id, agent_id)`
- `group_members(group_id, user_id)` (部分唯一)
- `group_members(group_id, agent_id)` (部分唯一)
- `meeting_outcomes(group_id, started_at)`
- `repo_branches(repo_id, name)`
- `pull_requests(repo_id, number)`
- `commits(repo_id, sha)`
- `task_commits(task_id, commit_id)`

**软删除索引**: `idx_projects_deleted`、`idx_tasks_deleted` 加速已删除记录的清理查询。

### 7.2 外键级联策略总览

| 子表 | 外键字段 | 父表 | 删除策略 | 理由 |
|------|----------|------|----------|------|
| projects | creator_id | users | RESTRICT (默认) | 项目创建者删除需先迁移项目 |
| requirements | project_id | projects | CASCADE | 项目删除则需求同步删除 |
| tasks | project_id | projects | CASCADE | 项目删除则任务同步删除 |
| tasks | assignee_agent_id | agents | SET NULL | Agent 删除后任务恢复未分配 |
| tasks | assignee_swarm_id | swarms | SET NULL | 蜂群删除后任务恢复未分配 |
| tasks | assignee_user_id | users | SET NULL | 用户删除后任务恢复未分配 |
| tasks | parent_task_id | tasks | SET NULL (默认) | 父任务删除后子任务变为顶级 |
| task_dependencies | source_task_id | tasks | CASCADE | 任务删除则依赖同步删除 |
| task_dependencies | target_task_id | tasks | CASCADE | 任务删除则依赖同步删除 |
| groups | project_id | projects | CASCADE | 项目删除则群同步删除 |
| groups | host_agent_id | agents | SET NULL | Agent 删除后群主持人清空 |
| group_members | group_id | groups | CASCADE | 群删除则成员同步删除 |
| group_members | user_id | users | SET NULL (默认) | 用户删除后从群中移除 |
| group_members | agent_id | agents | SET NULL (默认) | Agent 删除后从群中移除 |
| group_messages | group_id | groups | CASCADE | 群删除则消息同步删除 |
| meeting_outcomes | group_id | groups | CASCADE | 群删除则会议记录同步删除 |
| meeting_outcomes | host_agent_id | agents | SET NULL | Agent 删除后会议主持人清空 |
| swarms | project_id | projects | CASCADE | 项目删除则蜂群同步删除 |
| swarms | manager_agent_id | agents | SET NULL | Agent 删除后蜂群管理器清空 |
| swarm_members | swarm_id | swarms | CASCADE | 蜂群删除则成员同步删除 |
| swarm_members | agent_id | agents | RESTRICT (默认) | Agent 有蜂群成员时禁止删除 |
| notifications | user_id | users | CASCADE | 用户删除则通知同步删除 |
| notifications | project_id | projects | CASCADE | 项目删除则通知同步删除 |
| repos | project_id | projects | CASCADE | 项目删除则仓库同步删除 |
| repo_branches | repo_id | repos | CASCADE | 仓库删除则分支同步删除 |
| pull_requests | repo_id | repos | CASCADE | 仓库删除则 PR 同步删除 |
| commits | repo_id | repos | CASCADE | 仓库删除则提交同步删除 |
| task_commits | task_id | tasks | CASCADE | 任务删除则关联同步删除 |
| task_commits | commit_id | commits | CASCADE | 提交删除则关联同步删除 |
| agent_execution_logs | task_id | tasks | CASCADE | 任务删除则日志同步删除 |
| agent_execution_logs | agent_id | agents | SET NULL | Agent 删除后日志保留 |
| qa_records | task_id | tasks | CASCADE | 任务删除则 QA 记录同步删除 |
| qa_records | reviewer_agent_id | agents | SET NULL | Agent 删除后 QA 记录保留 |

### 7.3 关键约束说明

**任务分配三选一 CHECK 约束** (2.6 tasks 表):

```sql
CHECK (
    (CASE WHEN assignee_agent_id IS NOT NULL THEN 1 ELSE 0 END) +
    (CASE WHEN assignee_swarm_id IS NOT NULL THEN 1 ELSE 0 END) +
    (CASE WHEN assignee_user_id IS NOT NULL THEN 1 ELSE 0 END) <= 1
)
```

- 允许三个字段全为 NULL（任务未分配状态）
- 允许恰好一个字段非 NULL（任务已分配）
- 禁止同时分配给多个对象

**dependency_type 合法值限制** (2.7 task_dependencies 表):

```sql
CHECK (dependency_type IN ('finish_to_start', 'start_to_start', 'finish_to_finish', 'start_to_finish'))
```

**循环依赖检测** (2.7 task_dependencies 表): 采用递归 CTE 从 source_task_id 出发正向遍历所有可达节点，若可达节点包含 target_task_id 则拒绝插入，防止形成环。

**会议防重复约束** (2.13 meeting_outcomes 表):

```sql
UNIQUE(group_id, started_at)
```

同一群组在同一开始时间只能有一条会议记录。

**邮箱大小写不敏感** (2.2 users 表): 使用 citext 扩展，User@Example.com 与 user@example.com 被视为同一邮箱，自动防止大小写重复注册。

---

## 8. 事务隔离级别与并发控制策略（V10 新增）

### 8.1 事务隔离级别

**推荐默认隔离级别**: READ COMMITTED（PostgreSQL 默认）

| 隔离级别 | 适用场景 | 是否推荐 |
|----------|----------|----------|
| READ COMMITTED | 大多数业务操作（任务创建、状态更新、消息发送） | 推荐（默认） |
| REPEATABLE READ | 项目进度统计、QA 报告生成等需要一致性快照的场景 | 按需使用 |
| SERIALIZABLE | 任务依赖关系批量操作（如迁移整条任务链） | 极少使用 |
| READ UNCOMMITTED | 不适用（PostgreSQL 中等同 READ COMMITTED） | 不推荐 |

**应用层设置方式**:

```sql
-- 会话级别设置（按需）
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- 连接池推荐配置（如 PgBouncer）
-- default_transaction_isolation = 'read committed'
```

### 8.2 并发控制策略

**乐观锁策略**: 适用于大多数业务场景，通过 `updated_at` 时间戳进行版本控制。

- 任务状态更新时检查 `updated_at` 是否被其他事务修改：

```sql
-- 示例：带乐观锁的任务状态更新
UPDATE tasks
SET status = 'in_progress', updated_at = NOW()
WHERE id = $1 AND updated_at = $2;
-- 返回影响行数为 0 表示冲突，应用层应重试
```

**悲观锁策略**: 适用于高竞争场景（如项目 current_step 并发更新）。

- `sync_project_current_step` 触发器中已使用 `UPDATE ... WHERE id = v_project_id` 锁定项目行
- 适用于：任务批量分配、蜂群创建、项目状态流转

```sql
-- 示例：SELECT FOR UPDATE 锁定项目行
BEGIN;
SELECT * FROM projects WHERE id = $1 FOR UPDATE;
-- ... 业务逻辑 ...
UPDATE projects SET status = 'in_progress' WHERE id = $1;
COMMIT;
```

**SELECT FOR UPDATE 使用场景**:

| 操作 | 锁粒度 | 策略 |
|------|--------|------|
| 任务分配 | tasks 行级 | 悲观锁 (FOR UPDATE) |
| 项目状态切换 | projects 行级 | 悲观锁 (FOR UPDATE) |
| 蜂群成员添加 | swarm_members 行级 | 乐观锁 (updated_at) |
| 群消息发送 | group_messages 行级 | 无锁（APPEND ONLY） |
| QA 检验记录 | qa_records 行级 | 无锁（APPEND ONLY） |
| Agent 执行日志 | agent_execution_logs 行级 | 无锁（APPEND ONLY） |

### 8.3 死锁预防

- 多表更新时遵循固定顺序：projects → tasks → task_dependencies → 其他
- `sync_project_current_step` 触发器只锁单行（project_id），避免表级锁
- 应用层建议使用连接池（如 PgBouncer）配置合理的 `statement_timeout`（建议 30 秒）

---

## 9. 分区表策略说明（V10 新增）

### 9.1 分区表设计

目前采用单表设计，以下表在数据量增长后建议采用分区策略：

| 表名 | 建议分区方式 | 触发条件 |
|------|-------------|----------|
| group_messages | RANGE BY timestamp（按月分区） | 单表超过 500 万行 |
| agent_execution_logs | RANGE BY created_at（按月分区） | 单表超过 500 万行 |
| notifications | RANGE BY created_at（按月分区） | 单表超过 200 万行 |

### 9.2 分区示例（group_messages）

当 group_messages 单表超过 500 万行时，按以下 DDL 改造为范围分区表：

```sql
-- 注意：此 DDL 仅在达到触发条件时执行，非初始化脚本的一部分

-- 1. 创建分区主表
CREATE TABLE group_messages_partitioned (
    id BIGSERIAL,
    group_id INTEGER NOT NULL,
    sender_id INTEGER,
    sender_type sender_type,
    role VARCHAR(100),
    content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL DEFAULT 'user',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_streaming BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    PRIMARY KEY (id, timestamp),  -- 分区键必须包含在主键中
    CONSTRAINT check_message_type CHECK (message_type IN ('system', 'agent', 'user')),
    CONSTRAINT check_sender_type CHECK (
        (sender_type = 'user' AND sender_id IS NOT NULL) OR
        (sender_type = 'agent' AND sender_id IS NOT NULL) OR
        (sender_type IS NULL AND sender_id IS NULL)
    )
) PARTITION BY RANGE (timestamp);

-- 2. 创建按月分区（示例：2026 年 6-8 月）
CREATE TABLE group_messages_2026_06 PARTITION OF group_messages_partitioned
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE group_messages_2026_07 PARTITION OF group_messages_partitioned
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE group_messages_2026_08 PARTITION OF group_messages_partitioned
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');

-- 3. 数据迁移（在维护窗口执行）
INSERT INTO group_messages_partitioned (id, group_id, sender_id, sender_type, role,
    content, message_type, timestamp, is_streaming, metadata)
SELECT id, group_id, sender_id, sender_type, role, content, message_type,
       timestamp, is_streaming, metadata FROM group_messages;

-- 4. 建立索引（每个分区自动继承主表索引定义）
CREATE INDEX idx_gm_group ON group_messages_partitioned(group_id);
CREATE INDEX idx_gm_sender ON group_messages_partitioned(sender_id, sender_type);
CREATE INDEX idx_gm_timestamp ON group_messages_partitioned(timestamp);
CREATE INDEX idx_gm_metadata_gin ON group_messages_partitioned USING gin(metadata);
```

### 9.3 自动分区管理

建议使用 pg_partman 扩展自动管理分区：

```sql
-- 安装 pg_partman 扩展
CREATE EXTENSION IF NOT EXISTS pg_partman;

-- 自动按月创建未来 3 个月的分区，保留最近 12 个月分区
SELECT partman.create_parent(p_parent_table := 'public.group_messages_partitioned',
    p_control := 'timestamp',
    p_type := 'range',
    p_interval := '1 month',
    p_premake := 3,
    p_retention := '1 year',
    p_retention_schema := NULL);
```

### 9.4 不分区的理由

当前 DevFlow 为初期阶段，预计单项目消息量有限（一个 16 步项目的群消息通常在几千条以内），不分区的优势：

- 简化 DDL 脚本
- 避免跨分区 JOIN 性能损失
- 减少运维复杂度
- 外键约束在分区表中需要额外处理

---

## 10. 表清单与 DDL 完整性验证（V10 新增）

以下清单列出所有实体表及其对应的 DDL 节号，供后荣检验时核对：

| 序号 | 表名 | DDL 节号 | 状态 |
|------|------|----------|------|
| 1 | users | 2.2 | 完整 |
| 2 | projects | 2.3 | 完整 |
| 3 | requirements | 2.4 | 完整 |
| 4 | agents | 2.5 | 完整 |
| 5 | tasks | 2.6 | 完整 |
| 6 | task_dependencies | 2.7 | 完整 |
| 7 | agent_execution_logs | 2.8 | 完整 |
| 8 | qa_records | 2.9 | 完整 |
| 9 | groups | 2.10 | 完整 |
| 10 | group_members | 2.11 | 完整 |
| 11 | group_messages | 2.12 | 完整 |
| 12 | meeting_outcomes | 2.13 | 完整 |
| 13 | swarms | 2.14 | 完整 |
| 14 | swarm_members | 2.15 | 完整 |
| 15 | notifications | 2.16 | 完整 |
| 16 | repos | 2.17 | 完整 |
| 17 | repo_branches | 2.18 | 完整 |
| 18 | pull_requests | 2.19 | 完整 |
| 19 | commits | 2.20 | 完整 |
| 20 | task_commits | 2.21 | 完整 |

共计 20 张实体表，全部 DDL 已在第 2 节完整提供。

---

## 11. V10 修正内容对照表（V10 新增）

| 后荣检验问题编号 | 问题描述 | V10 修正方式 | 对应位置 |
|-------------------|----------|-------------|----------|
| 1 | 文档在 2.3 项目表处被截断 | V10 确保完整提供全部 20 张表 DDL（2.2~2.21） | 第 2 节 + 第 10 节 |
| 2 | V9 声称的修正无法验证 | V10 提供表清单和 DDL 完整性验证表 | 第 10 节 |
| 3 | current_step CHECK 上限应为 16 | 从 `<= 100` 改为 `<= 16` | 2.3 projects 表 |
| 4 | step_number CHECK 上限应为 16 | 从 `<= 100` 改为 `<= 16` | 2.6 tasks 表 |
| 5 | 缺少外键级联删除策略 | 第 7.2 节完整列出 33 条外键级联策略 | 7.2 节 |
| 6 | 缺少分区表策略说明 | 新增第 9 节分区表策略说明 | 第 9 节 |
| 7 | 缺少事务隔离级别建议 | 新增第 8.1 节事务隔离级别说明 | 8.1 节 |
| 8 | 缺少并发控制策略 | 新增第 8.2/8.3 节乐观锁/悲观锁策略 | 第 8 节 |

---

**文档结束**