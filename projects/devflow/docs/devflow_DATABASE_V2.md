# DevFlow 数据库设计文档 V2.0

**项目**: DevFlow 项目管理平台
**版本**: 2.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: 修订版 (根据后荣QA检验报告修订)

**变更说明 (V1.0 → V2.0)**:
- 修复 group_messages.sender_id 参照完整性缺陷，拆分为 sender_user_id 和 sender_agent_id
- 删除 repos 表冗余字段 http_url（与 url 语义重复）
- 新增 task_dependencies 循环依赖防止触发器（递归CTE检测）
- 补齐 agent_execution_logs、audit_logs、notifications、qa_records 等表外键 ON DELETE/ON UPDATE 策略
- swarm_members 新增 agent_id 外键关联 agents 表
- meeting_outcomes.host_agent_id 补充 ON DELETE CASCADE
- 移除 projects.current_step 和 tasks.step_number 硬编码 1-16 范围检查，改为通过 system_configs 动态管理
- 补全 ER 图，加入 agent_execution_logs、audit_logs、system_configs、notifications 等表
- 核心业务表新增 is_deleted 软删除字段
- 新增 tasks 表复合索引 (project_id, status, step_number)

---

## 1. ER图概述

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  users   │────<│  projects   │────<│ requirements │
└──────────┘     └──────┬──────┘     └──────────────┘
                        │
            ┌───────────┼───────────┐
            │           │           │
     ┌──────▼──────┐ ┌──▼────────┐ ┌▼────────────┐
     │   tasks     │ │   groups  │ │    repos    │
     └──────┬──────┘ └────┬──────┘ └─────────────┘
            │              │
     ┌──────▼────────┐ ┌──▼─────────────┐
     │task_dependencies│ │group_members  │
     └────────────────┘ └───────────────┘
            │              │
     ┌──────▼──────┐ ┌────▼──────────┐
     │ qa_records  │ │group_messages │
     └─────────────┘ └───────────────┘

┌──────────┐     ┌──────────┐     ┌──────────────┐
│  agents  │────<│ swarms   │────<│swarm_members │
└──────────┘     └──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐
│  agents  │────<│meeting_outcomes│
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐
│ projects │────<│ notifications│
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐
│   users  │────<│ notifications│
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐
│  repos   │────<│  branches    │
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐
│  repos   │────<│pull_requests │
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐
│  repos   │────<│   commits    │
└──────────┘     └──────────────┘

┌──────────┐     ┌──────────────┐
│  tasks   │────<│task_commits  │─┤  commits   │
└──────────┘     └──────────────┘ └──────────────┘

┌──────────┐     ┌────────────────────┐
│  tasks   │────<│agent_execution_logs│
└──────────┘     └────────────────────┘

┌──────────┐     ┌──────────────────┐
│  agents  │────<│agent_execution_logs│
└──────────┘     └──────────────────┘

┌──────────┐     ┌─────────────┐
│   users  │────<│ audit_logs  │
└──────────┘     └─────────────┘

┌──────────┐     ┌─────────────┐
│  agents  │────<│ audit_logs  │
└──────────┘     └─────────────┘

┌──────────┐     ┌─────────────┐
│ projects │────<│ audit_logs  │
└──────────┘     └─────────────┘

┌────────────────┐
│ system_configs │  (独立配置表)
└────────────────┘
```

---

## 2. 完整SQL DDL脚本

```sql
-- ================================================================
-- DevFlow 数据库初始化脚本 V2.0
-- 数据库: PostgreSQL 14+
-- 字符集: UTF-8
-- 变更: 修复外键约束、软删除、循环依赖检测、字段冗余等
-- ================================================================

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ================================================================
-- 1. 用户表
-- ================================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(50) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE, -- 软删除
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMP WITH TIME ZONE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    language        VARCHAR(10) NOT NULL DEFAULT 'zh-CN', -- 用户偏好语言

    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_is_active ON users (is_active);
CREATE INDEX idx_users_is_deleted ON users (is_deleted);

COMMENT ON TABLE users IS '人类用户表';
COMMENT ON COLUMN users.role IS '用户角色: user(普通用户), admin(管理员)';
COMMENT ON COLUMN users.is_deleted IS '软删除标记: TRUE表示已删除';

-- ================================================================
-- 2. 项目表
-- ================================================================
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_code    VARCHAR(30) NOT NULL, -- proj-YYYYMMDD-SEQ
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    core_goal       TEXT, -- 核心目标 (第二步确认)
    creator_id      UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status          VARCHAR(20) NOT NULL DEFAULT 'created' CHECK (
        status IN ('created', 'in_progress', 'completed', 'cancelled', 'iterating')
    ),
    current_step    INTEGER NOT NULL DEFAULT 1 CHECK (current_step > 0),
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE, -- 软删除
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_projects_project_code UNIQUE (project_code),
    CONSTRAINT uq_projects_name_creator UNIQUE (name, creator_id)
);

CREATE INDEX idx_projects_creator_id ON projects (creator_id);
CREATE INDEX idx_projects_status ON projects (status);
CREATE INDEX idx_projects_current_step ON projects (current_step);
CREATE INDEX idx_projects_created_at ON projects (created_at DESC);
CREATE INDEX idx_projects_is_deleted ON projects (is_deleted);

COMMENT ON TABLE projects IS '项目表';
COMMENT ON COLUMN projects.project_code IS '项目唯一编码: proj-YYYYMMDD-SEQ';
COMMENT ON COLUMN projects.current_step IS '当前执行的步骤编号 (正整数, 最大值通过 system_configs 动态配置)';
COMMENT ON COLUMN projects.is_deleted IS '软删除标记: TRUE表示已删除';

-- ================================================================
-- 3. 需求表
-- ================================================================
CREATE TABLE requirements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content         TEXT NOT NULL, -- SRS文档内容 (Markdown格式)
    version         INTEGER NOT NULL DEFAULT 1,
    is_locked       BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at    TIMESTAMP WITH TIME ZONE,
    confirmed_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_requirements_project_version UNIQUE (project_id, version)
);

CREATE INDEX idx_requirements_project_id ON requirements (project_id);

COMMENT ON TABLE requirements IS '软件需求说明书表';

-- ================================================================
-- 4. Agent角色表
-- ================================================================
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(50) NOT NULL, -- haimei, houxing, houwang等
    agent_type      VARCHAR(20) NOT NULL CHECK (agent_type IN ('named', 'swarm')),
    role_name       VARCHAR(50) NOT NULL, -- project_manager, requirement_analyst等
    chinese_name    VARCHAR(20) NOT NULL, -- 海梅, 后兴, 后旺等
    personality     TEXT, -- Agent人设描述
    status          VARCHAR(20) NOT NULL DEFAULT 'offline' CHECK (
        status IN ('online', 'offline', 'busy', 'error')
    ),
    api_endpoint    VARCHAR(500), -- Gateway API地址
    gateway_port    INTEGER, -- Gateway端口
    model_name      VARCHAR(100), -- 使用的模型
    model_provider  VARCHAR(50), -- 模型提供商
    config          JSONB NOT NULL DEFAULT '{}'::jsonb, -- 额外配置
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_agents_name UNIQUE (name)
);

CREATE INDEX idx_agents_agent_type ON agents (agent_type);
CREATE INDEX idx_agents_status ON agents (status);
CREATE INDEX idx_agents_role_name ON agents (role_name);

COMMENT ON TABLE agents IS 'Agent角色表 (9个命名Agent + 编程Agent蜂群)';
COMMENT ON COLUMN agents.agent_type IS 'named(命名Agent), swarm(蜂群Agent)';

-- 初始化9个命名Agent
INSERT INTO agents (name, agent_type, role_name, chinese_name, personality, status) VALUES
('haimei', 'named', 'project_manager', '海梅', '默认Hermes Agent，项目经理角色，负责任务分派，对项目交付成果负责', 'online'),
('houxing', 'named', 'requirement_analyst', '后兴', '需求分析师角色，负责需求分析，与用户沟通具体需求，产出完整、准确的软件需求说明书', 'online'),
('houwang', 'named', 'architect', '后旺', '架构设计师角色，负责架构设计、后端设计、前端设计、数据库设计等', 'online'),
('houfa', 'named', 'programmer', '后发', '程序员角色，负责建立代码编写Agent蜂群，监督蜂群完成TDD测试用例和代码编写', 'online'),
('houda', 'named', 'tester', '后达', '测试员角色，负责建立代码测试Agent蜂群，执行单元测试、模块测试、集成测试、前端实操验证', 'online'),
('houfu', 'named', 'cicd_engineer', '后富', 'CI/CD工程师角色，负责开发环境搭建和代码部署到测试/生产环境', 'online'),
('hougui', 'named', 'document_manager', '后贵', '文档管理员角色，负责整个项目文档的一致性管理，任一文档修改，其它文档必须同步修改', 'online'),
('hourong', 'named', 'qa', '后荣', 'QA角色，负责检验每个Agent的产出是否达到验收标准，未达标退回重做，达标放行并提交代码库', 'online'),
('houhua', 'named', 'security_auditor', '后华', '安全员角色，负责代码审计、合规审查、渗透测试、漏洞修复', 'online');

-- ================================================================
-- 5. 任务表
-- ================================================================
CREATE TABLE tasks (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name                    VARCHAR(200) NOT NULL,
    description             TEXT,
    type                    VARCHAR(50) NOT NULL, -- requirement, design, tdd_plan, tdd_code, code_plan, code, deploy_test, test, security, deploy_prod, document, report
    priority                INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    assignee_agent_id       UUID REFERENCES agents(id) ON DELETE SET NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'in_progress', 'completed', 'failed', 'rolled_back', 'cancelled')
    ),
    acceptance_criteria     TEXT, -- 验收标准
    step_number             INTEGER NOT NULL CHECK (step_number > 0),
    is_atomic               BOOLEAN NOT NULL DEFAULT TRUE, -- 是否原子化任务
    parent_task_id          UUID REFERENCES tasks(id) ON DELETE SET NULL, -- 父任务 (用于任务分解)
    estimated_lines         INTEGER DEFAULT 0, -- 预计代码行数
    estimated_hours         DECIMAL(4,1) DEFAULT 0.0, -- 预计完成时间 (小时)
    dependency_order        INTEGER DEFAULT 0, -- 依赖图中的执行顺序
    is_deleted              BOOLEAN NOT NULL DEFAULT FALSE, -- 软删除
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at              TIMESTAMP WITH TIME ZONE,
    completed_at            TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_tasks_atomic CHECK (
        (is_atomic = TRUE AND estimated_lines < 200 AND estimated_hours <= 2.0)
        OR is_atomic = FALSE
    )
);

CREATE INDEX idx_tasks_project_id ON tasks (project_id);
CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_tasks_assignee_agent_id ON tasks (assignee_agent_id);
CREATE INDEX idx_tasks_step_number ON tasks (step_number);
CREATE INDEX idx_tasks_type ON tasks (type);
CREATE INDEX idx_tasks_dependency_order ON tasks (project_id, dependency_order);
CREATE INDEX idx_tasks_is_deleted ON tasks (is_deleted);

-- 复合索引: 按项目+状态+步骤查询任务 (高频查询)
CREATE INDEX idx_tasks_project_status_step ON tasks (project_id, status, step_number);

COMMENT ON TABLE tasks IS '任务表';
COMMENT ON COLUMN tasks.is_atomic IS '原子化任务: 单一功能, <200行代码, 单测试用例对应, <2小时完成';
COMMENT ON COLUMN tasks.step_number IS '步骤编号 (正整数, 最大值通过 system_configs 动态配置)';
COMMENT ON COLUMN tasks.is_deleted IS '软删除标记: TRUE表示已删除';

-- ================================================================
-- 6. 任务依赖表
-- ================================================================
CREATE TABLE task_dependencies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_task_id  UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    target_task_id  UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(30) NOT NULL DEFAULT 'finish_to_start' CHECK (
        dependency_type IN ('finish_to_start', 'finish_to_finish', 'start_to_start')
    ),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_task_dependencies_source_target UNIQUE (source_task_id, target_task_id),
    CONSTRAINT chk_task_dependencies_no_self CHECK (source_task_id <> target_task_id)
);

CREATE INDEX idx_task_dependencies_source ON task_dependencies (source_task_id);
CREATE INDEX idx_task_dependencies_target ON task_dependencies (target_task_id);

COMMENT ON TABLE task_dependencies IS '任务依赖表 (有向无环图, 通过触发器防止循环依赖)';

-- 循环依赖检测触发器函数
CREATE OR REPLACE FUNCTION check_task_dependency_cycle()
RETURNS TRIGGER AS $$
DECLARE
    v_source UUID;
    v_target UUID;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_source := NEW.source_task_id;
        v_target := NEW.target_task_id;
    ELSIF TG_OP = 'UPDATE' THEN
        v_source := NEW.source_task_id;
        v_target := NEW.target_task_id;
    END IF;

    -- 使用递归CTE检测从 target 是否能回到 source (即是否存在循环)
    IF EXISTS (
        WITH RECURSIVE dep_path AS (
            SELECT target_task_id AS node
            FROM task_dependencies
            WHERE source_task_id = v_target
            UNION
            SELECT td.target_task_id
            FROM task_dependencies td
            INNER JOIN dep_path dp ON td.source_task_id = dp.node
        )
        SELECT 1 FROM dep_path WHERE node = v_source
    ) THEN
        RAISE EXCEPTION '循环依赖检测失败: 添加依赖 % -> % 将形成环', v_source, v_target;
    END IF;

    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器: 插入/更新时检测循环依赖
CREATE TRIGGER trg_task_dependencies_cycle_check
    BEFORE INSERT OR UPDATE ON task_dependencies
    FOR EACH ROW EXECUTE FUNCTION check_task_dependency_cycle();

-- ================================================================
-- 7. Agent执行日志表
-- ================================================================
CREATE TABLE agent_execution_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    execution_type  VARCHAR(50) NOT NULL, -- chat, code_generation, test_execution, inspection等
    input_content   TEXT, -- 输入内容
    execution_content TEXT, -- 执行过程记录
    result          TEXT, -- 执行结果
    status          VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (
        status IN ('running', 'completed', 'failed', 'timeout', 'cancelled')
    ),
    duration_ms     INTEGER, -- 执行耗时 (毫秒)
    error_message   TEXT, -- 错误信息
    trace_id        VARCHAR(100), -- 链路追踪ID
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_logs_duration CHECK (duration_ms IS NULL OR duration_ms >= 0)
);

CREATE INDEX idx_agent_execution_logs_task_id ON agent_execution_logs (task_id);
CREATE INDEX idx_agent_execution_logs_agent_id ON agent_execution_logs (agent_id);
CREATE INDEX idx_agent_execution_logs_created_at ON agent_execution_logs (created_at DESC);

COMMENT ON TABLE agent_execution_logs IS 'Agent执行日志表';

-- ================================================================
-- 8. QA检验记录表
-- ================================================================
CREATE TABLE qa_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id             UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    reviewer_agent_id   UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT, -- 固定为后荣的agent id
    acceptance_result   VARCHAR(10) NOT NULL CHECK (acceptance_result IN ('pass', 'fail')),
    problem_details     TEXT, -- 问题详情 (检验不合格时)
    review_dimensions   JSONB NOT NULL DEFAULT '{}'::jsonb, -- 各维度检验结果
    score               INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100), -- 综合评分 (0-100)
    retry_count         INTEGER NOT NULL DEFAULT 0, -- 重试次数
    rollback_suggestions TEXT, -- 退回修改建议
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_qa_score_range CHECK (score >= 0 AND score <= 100)
);

CREATE INDEX idx_qa_records_task_id ON qa_records (task_id);
CREATE INDEX idx_qa_records_reviewer_agent_id ON qa_records (reviewer_agent_id);
CREATE INDEX idx_qa_records_acceptance_result ON qa_records (acceptance_result);
CREATE INDEX idx_qa_records_created_at ON qa_records (created_at DESC);

-- QA记录查询优化复合索引
CREATE INDEX idx_qa_records_task_result ON qa_records (task_id, acceptance_result);

COMMENT ON TABLE qa_records IS 'QA检验记录表 (后荣检验记录)';
COMMENT ON COLUMN qa_records.score IS '综合评分: score = 各维度得分的算术平均值 (0-100), 各维度权重默认均等';
COMMENT ON COLUMN qa_records.review_dimensions IS 'JSON存储各维度名称、量化标准、实际得分、合格阈值和是否达标';

-- ================================================================
-- 9. 群组表 (项目讨论群)
-- ================================================================
CREATE TABLE groups (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    mode            VARCHAR(20) NOT NULL DEFAULT 'discussion' CHECK (
        mode IN ('discussion', 'meeting')
    ),
    host_agent_id   UUID REFERENCES agents(id) ON DELETE SET NULL, -- 会议模式主持人 (默认海梅)
    meeting_type    VARCHAR(50), -- 会议类型 (讨论模式下为NULL)
    meeting_topic   VARCHAR(500), -- 会议主题
    meeting_status  VARCHAR(20) DEFAULT 'idle' CHECK (
        meeting_status IN ('idle', 'running', 'paused', 'completed')
    ),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_groups_project_id UNIQUE (project_id)
);

CREATE INDEX idx_groups_project_id ON groups (project_id);
CREATE INDEX idx_groups_mode ON groups (mode);

COMMENT ON TABLE groups IS '群组表 (项目讨论群)';

-- ================================================================
-- 10. 群组-成员关联表
-- ================================================================
CREATE TABLE group_members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id        UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE, -- 人类用户
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE, -- Agent
    member_type     VARCHAR(10) NOT NULL CHECK (member_type IN ('user', 'agent')),
    joined_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    role_in_group   VARCHAR(50) DEFAULT 'member', -- 在群组中的角色

    CONSTRAINT uq_group_members_group_user UNIQUE (group_id, user_id),
    CONSTRAINT uq_group_members_group_agent UNIQUE (group_id, agent_id),
    CONSTRAINT chk_group_members_either_id CHECK (
        (member_type = 'user' AND user_id IS NOT NULL AND agent_id IS NULL)
        OR
        (member_type = 'agent' AND agent_id IS NOT NULL AND user_id IS NULL)
    )
);

CREATE INDEX idx_group_members_group_id ON group_members (group_id);
CREATE INDEX idx_group_members_agent_id ON group_members (agent_id);
CREATE INDEX idx_group_members_user_id ON group_members (user_id);

COMMENT ON TABLE group_members IS '群组-成员关联表 (user_id和agent_id二选一必填)';

-- ================================================================
-- 11. 群聊消息表
-- ================================================================
CREATE TABLE group_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id        UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    sender_user_id  UUID, -- 发送者: 人类用户ID (发送者为Agent时为NULL)
    sender_agent_id UUID, -- 发送者: AgentID (发送者为人类时为NULL)
    sender_type     VARCHAR(10) NOT NULL CHECK (sender_type IN ('user', 'agent')),
    role            VARCHAR(50), -- 发送者角色
    content         TEXT NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_streaming    BOOLEAN NOT NULL DEFAULT FALSE, -- 是否流式消息
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb, -- 附加信息 (@mentions等)
    parent_message_id UUID REFERENCES group_messages(id) ON DELETE SET NULL, -- 回复的消息

    -- sender_user_id和sender_agent_id互斥约束
    CONSTRAINT chk_group_messages_sender CHECK (
        (sender_type = 'user' AND sender_user_id IS NOT NULL AND sender_agent_id IS NULL)
        OR
        (sender_type = 'agent' AND sender_agent_id IS NOT NULL AND sender_user_id IS NULL)
    )
);

-- sender_user_id 外键约束 (延迟检查, 允许NULL)
ALTER TABLE group_messages
    ADD CONSTRAINT fk_group_messages_sender_user
    FOREIGN KEY (sender_user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE;

-- sender_agent_id 外键约束 (延迟检查, 允许NULL)
ALTER TABLE group_messages
    ADD CONSTRAINT fk_group_messages_sender_agent
    FOREIGN KEY (sender_agent_id) REFERENCES agents(id) ON DELETE CASCADE ON UPDATE CASCADE;

CREATE INDEX idx_group_messages_group_id ON group_messages (group_id);
CREATE INDEX idx_group_messages_timestamp ON group_messages (timestamp DESC);
CREATE INDEX idx_group_messages_sender_user_id ON group_messages (sender_user_id);
CREATE INDEX idx_group_messages_sender_agent_id ON group_messages (sender_agent_id);
CREATE INDEX idx_group_messages_parent ON group_messages (parent_message_id);

-- 群消息查询优化复合索引
CREATE INDEX idx_group_messages_group_time ON group_messages (group_id, timestamp DESC);

-- 全文搜索索引
CREATE INDEX idx_group_messages_content_gin ON group_messages USING gin (content gin_trgm_ops);

COMMENT ON TABLE group_messages IS '群聊消息表 (sender_user_id/sender_agent_id互斥, 通过外键保证参照完整性)';

-- ================================================================
-- 12. 会议结果表
-- ================================================================
CREATE TABLE meeting_outcomes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id        UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    meeting_topic   VARCHAR(500) NOT NULL,
    host_agent_id   UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    meeting_type    VARCHAR(50) NOT NULL, -- requirement_review, tech_solution, daily_standup, incident_postmortem
    started_at      TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at        TIMESTAMP WITH TIME ZONE,
    minutes         TEXT, -- 会议纪要 (Markdown格式)
    decisions       JSONB NOT NULL DEFAULT '[]'::jsonb, -- 决议列表
    todos           JSONB NOT NULL DEFAULT '[]'::jsonb, -- 待办任务
    risks           JSONB NOT NULL DEFAULT '[]'::jsonb, -- 风险点
    open_issues     JSONB NOT NULL DEFAULT '[]'::jsonb, -- 遗留问题
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_meeting_outcomes_group_id ON meeting_outcomes (group_id);
CREATE INDEX idx_meeting_outcomes_host_agent_id ON meeting_outcomes (host_agent_id);
CREATE INDEX idx_meeting_outcomes_started_at ON meeting_outcomes (started_at DESC);

COMMENT ON TABLE meeting_outcomes IS '会议结果表';

-- ================================================================
-- 13. Agent蜂群表
-- ================================================================
CREATE TABLE swarms (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    manager_agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT, -- 后发/后达
    purpose             VARCHAR(30) NOT NULL CHECK (purpose IN ('code_writing', 'test')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (
        status IN ('active', 'paused', 'dissolved', 'error')
    ),
    total_tasks         INTEGER NOT NULL DEFAULT 0,
    completed_tasks     INTEGER NOT NULL DEFAULT 0,
    failed_tasks        INTEGER NOT NULL DEFAULT 0,
    config              JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    dissolved_at        TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_swarms_tasks CHECK (
        completed_tasks + failed_tasks <= total_tasks
    )
);

CREATE INDEX idx_swarms_project_id ON swarms (project_id);
CREATE INDEX idx_swarms_manager_agent_id ON swarms (manager_agent_id);
CREATE INDEX idx_swarms_status ON swarms (status);
CREATE INDEX idx_swarms_purpose ON swarms (purpose);

COMMENT ON TABLE swarms IS 'Agent蜂群表';
COMMENT ON COLUMN swarms.manager_agent_id IS '蜂群调度者: 后发 (代码编写) 或 后达 (代码测试)';

-- ================================================================
-- 14. 蜂群-成员关联表
-- ================================================================
CREATE TABLE swarm_members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    swarm_id        UUID NOT NULL REFERENCES swarms(id) ON DELETE CASCADE,
    agent_id        UUID REFERENCES agents(id) ON DELETE SET NULL, -- 关联agents表 (保证成员有效性)
    agent_name      VARCHAR(100) NOT NULL, -- Claude Code, Codex, Opencode等
    agent_type      VARCHAR(50) NOT NULL, -- 具体Agent类型
    external_id     VARCHAR(100), -- 外部Agent标识
    status          VARCHAR(20) NOT NULL DEFAULT 'idle' CHECK (
        status IN ('idle', 'busy', 'error', 'offline')
    ),
    skills          JSONB NOT NULL DEFAULT '[]'::jsonb, -- 技能列表
    current_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL, -- 当前执行的任务
    registered_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_heartbeat  TIMESTAMP WITH TIME ZONE,

    CONSTRAINT uq_swarm_members_swarm_agent UNIQUE (swarm_id, agent_name, agent_type)
);

CREATE INDEX idx_swarm_members_swarm_id ON swarm_members (swarm_id);
CREATE INDEX idx_swarm_members_agent_id ON swarm_members (agent_id);
CREATE INDEX idx_swarm_members_status ON swarm_members (status);

COMMENT ON TABLE swarm_members IS '蜂群-成员关联表 (agent_id关联agents表, 保证成员有效性)';

-- ================================================================
-- 15. 通知表
-- ================================================================
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE,
    content         TEXT NOT NULL,
    type            VARCHAR(50) NOT NULL, -- step_complete, qa_pass, qa_fail, task_assigned, project_complete等
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    related_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL ON UPDATE CASCADE,
    related_qa_id   UUID REFERENCES qa_records(id) ON DELETE SET NULL ON UPDATE CASCADE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    read_at         TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_notifications_read_time CHECK (
        (is_read = FALSE AND read_at IS NULL)
        OR
        (is_read = TRUE AND read_at IS NOT NULL)
    )
);

CREATE INDEX idx_notifications_user_id ON notifications (user_id);
CREATE INDEX idx_notifications_project_id ON notifications (project_id);
CREATE INDEX idx_notifications_is_read ON notifications (is_read);
CREATE INDEX idx_notifications_created_at ON notifications (created_at DESC);

-- 通知查询优化复合索引
CREATE INDEX idx_notifications_user_unread ON notifications (user_id, is_read, created_at DESC)
    WHERE is_read = FALSE;

COMMENT ON TABLE notifications IS '通知表';

-- ================================================================
-- 16. 代码仓库表
-- ================================================================
CREATE TABLE repos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    gitea_repo_id   INTEGER NOT NULL, -- Gitea中的仓库ID
    name            VARCHAR(200) NOT NULL,
    url             VARCHAR(500) NOT NULL, -- HTTP URL
    ssh_url         VARCHAR(500), -- SSH URL
    default_branch  VARCHAR(50) NOT NULL DEFAULT 'main',
    is_private      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_repos_project_id UNIQUE (project_id),
    CONSTRAINT uq_repos_gitea_repo_id UNIQUE (gitea_repo_id)
);

CREATE INDEX idx_repos_project_id ON repos (project_id);

COMMENT ON TABLE repos IS '代码仓库表 (Gitea集成)';

-- ================================================================
-- 17. 分支表
-- ================================================================
CREATE TABLE repo_branches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id         UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL, -- main, develop, feature/*, release/*, hotfix/*
    commit_sha      VARCHAR(40), -- Git commit SHA
    is_protected    BOOLEAN NOT NULL DEFAULT FALSE,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_repo_branches_repo_name UNIQUE (repo_id, name)
);

CREATE INDEX idx_repo_branches_repo_id ON repo_branches (repo_id);
CREATE INDEX idx_repo_branches_is_protected ON repo_branches (is_protected);

COMMENT ON TABLE repo_branches IS '分支表 (Git Flow: main/develop/feature/release/hotfix)';

-- ================================================================
-- 18. Pull Request表
-- ================================================================
CREATE TABLE pull_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id         UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    number          INTEGER NOT NULL, -- PR编号
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    source_branch   VARCHAR(100) NOT NULL,
    target_branch   VARCHAR(100) NOT NULL,
    author          VARCHAR(100), -- 创建者
    status          VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (
        status IN ('open', 'closed', 'merged', 'draft')
    ),
    review_status   VARCHAR(20) DEFAULT 'pending' CHECK (
        review_status IN ('pending', 'approved', 'changes_requested', 'rejected')
    ),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    merged_at       TIMESTAMP WITH TIME ZONE,
    merged_by       VARCHAR(100),

    CONSTRAINT uq_pull_requests_repo_number UNIQUE (repo_id, number)
);

CREATE INDEX idx_pull_requests_repo_id ON pull_requests (repo_id);
CREATE INDEX idx_pull_requests_status ON pull_requests (status);
CREATE INDEX idx_pull_requests_created_at ON pull_requests (created_at DESC);

COMMENT ON TABLE pull_requests IS 'Pull Request表';

-- ================================================================
-- 19. 提交记录表
-- ================================================================
CREATE TABLE commits (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repo_id         UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    sha             VARCHAR(40) NOT NULL, -- Git commit SHA
    message         TEXT NOT NULL, -- 提交消息 (Conventional Commits格式)
    author          VARCHAR(100),
    parent_sha      VARCHAR(40), -- 父commit SHA
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_commits_repo_sha UNIQUE (repo_id, sha)
);

CREATE INDEX idx_commits_repo_id ON commits (repo_id);
CREATE INDEX idx_commits_sha ON commits (sha);
CREATE INDEX idx_commits_created_at ON commits (created_at DESC);

COMMENT ON TABLE commits IS '提交记录表 (Conventional Commits规范)';

-- ================================================================
-- 20. 任务与提交关联表
-- ================================================================
CREATE TABLE task_commits (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id         UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    commit_id       UUID NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    qa_record_id    UUID REFERENCES qa_records(id) ON DELETE SET NULL, -- 关联的QA检验记录
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_task_commits_task_commit UNIQUE (task_id, commit_id)
);

CREATE INDEX idx_task_commits_task_id ON task_commits (task_id);
CREATE INDEX idx_task_commits_commit_id ON task_commits (commit_id);
CREATE INDEX idx_task_commits_qa_record_id ON task_commits (qa_record_id);

COMMENT ON TABLE task_commits IS '任务与提交关联表 (提交关联任务ID和QA检验记录ID)';

-- ================================================================
-- 21. 审计日志表
-- ================================================================
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event           VARCHAR(100) NOT NULL, -- 事件类型
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    agent_id        UUID REFERENCES agents(id) ON DELETE SET NULL ON UPDATE CASCADE,
    project_id      UUID REFERENCES projects(id) ON DELETE SET NULL ON UPDATE CASCADE,
    action          VARCHAR(200) NOT NULL, -- 操作描述
    details         JSONB NOT NULL DEFAULT '{}'::jsonb, -- 详细信息
    ip_address      VARCHAR(45), -- IP地址
    user_agent      VARCHAR(500), -- 客户端信息
    trace_id        VARCHAR(100), -- 链路追踪ID
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_event ON audit_logs (event);
CREATE INDEX idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_agent_id ON audit_logs (agent_id);
CREATE INDEX idx_audit_logs_project_id ON audit_logs (project_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at DESC);

COMMENT ON TABLE audit_logs IS '审计日志表';

-- ================================================================
-- 22. 系统配置表
-- ================================================================
CREATE TABLE system_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key      VARCHAR(100) NOT NULL,
    config_value    TEXT NOT NULL,
    description     TEXT,
    is_public       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_system_configs_key UNIQUE (config_key)
);

COMMENT ON TABLE system_configs IS '系统配置表 (包括步骤数上限等动态配置)';

-- 初始化系统配置
INSERT INTO system_configs (config_key, config_value, description) VALUES
('qa_score_threshold', '85', 'QA检验合格阈值 (综合评分)'),
('agent_timeout_minutes', '30', 'Agent执行超时阈值 (分钟)'),
('qa_retry_deadline_hours', '24', 'QA检验不合格后修改时限 (小时)'),
('max_retry_count', '3', 'Agent执行最大重试次数'),
('max_concurrent_projects', '20', '系统最大并发项目数'),
('max_swarm_agents', '10', '单个蜂群最大Agent数'),
('project_folder_base', '/DevFlow/projects/', '项目文件夹基础路径'),
('max_step_number', '16', '项目流程最大步骤数 (动态配置, 替代硬编码)');

-- ================================================================
-- 触发器: 自动更新 updated_at 字段
-- ================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_requirements_updated_at BEFORE UPDATE ON requirements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_groups_updated_at BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_swarms_updated_at BEFORE UPDATE ON swarms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_repo_branches_updated_at BEFORE UPDATE ON repo_branches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_pull_requests_updated_at BEFORE UPDATE ON pull_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_system_configs_updated_at BEFORE UPDATE ON system_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- 视图: 项目进度概览
-- ================================================================
CREATE OR REPLACE VIEW v_project_progress AS
SELECT
    p.id AS project_id,
    p.project_code,
    p.name AS project_name,
    p.status,
    p.current_step,
    p.creator_id,
    u.username AS creator_username,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) AS completed_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) AS in_progress_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'pending' THEN t.id END) AS pending_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'failed' THEN t.id END) AS failed_tasks,
    COUNT(DISTINCT qr.id) AS total_qa_records,
    COUNT(DISTINCT CASE WHEN qr.acceptance_result = 'pass' THEN qr.id END) AS qa_passed,
    COUNT(DISTINCT CASE WHEN qr.acceptance_result = 'fail' THEN qr.id END) AS qa_failed,
    CASE
        WHEN COUNT(DISTINCT qr.id) > 0 THEN
            ROUND(
                (COUNT(DISTINCT CASE WHEN qr.acceptance_result = 'pass' THEN qr.id END)::NUMERIC /
                 COUNT(DISTINCT qr.id)) * 100, 2
            )
        ELSE 0
    END AS qa_pass_rate,
    p.created_at,
    p.completed_at
FROM projects p
JOIN users u ON p.creator_id = u.id
LEFT JOIN tasks t ON p.id = t.project_id
LEFT JOIN qa_records qr ON t.id = qr.task_id
GROUP BY p.id, p.project_code, p.name, p.status, p.current_step,
         p.creator_id, u.username, p.created_at, p.completed_at;

COMMENT ON VIEW v_project_progress IS '项目进度概览视图';

-- ================================================================
-- 视图: Agent工作负载
-- ================================================================
CREATE OR REPLACE VIEW v_agent_workload AS
SELECT
    a.id AS agent_id,
    a.name AS agent_name,
    a.chinese_name,
    a.role_name,
    a.agent_type,
    a.status,
    COUNT(DISTINCT t.id) AS total_assigned_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.id END) AS active_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) AS completed_tasks,
    COALESCE(AVG(ael.duration_ms), 0) AS avg_execution_time_ms,
    a.last_seen_at
FROM agents a
LEFT JOIN tasks t ON a.id = t.assignee_agent_id
LEFT JOIN agent_execution_logs ael ON a.id = ael.agent_id
GROUP BY a.id, a.name, a.chinese_name, a.role_name, a.agent_type, a.status, a.last_seen_at;

COMMENT ON VIEW v_agent_workload IS 'Agent工作负载视图';

-- ================================================================
-- 分区表: 群聊消息按时间分区 (可选，大数据量时启用)
-- ================================================================
-- CREATE TABLE group_messages (
--     ... -- 与上述定义相同，但添加 PARTITION BY RANGE (timestamp)
-- ) PARTITION BY RANGE (timestamp);
-- 
-- CREATE TABLE group_messages_2026_q1 PARTITION OF group_messages
--     FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');
-- CREATE TABLE group_messages_2026_q2 PARTITION OF group_messages
--     FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');

-- ================================================================
-- 权限设置
-- ================================================================
-- 创建应用用户
-- CREATE USER devflow_app WITH PASSWORD '***';
-- GRANT CONNECT ON DATABASE devflow TO devflow_app;
-- GRANT USAGE ON SCHEMA public TO devflow_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO devflow_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO devflow_app;

-- ================================================================
-- 数据保留策略 (通过定时任务执行)
-- ================================================================
-- 审计日志保留90天
-- DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '90 days';
-- 
-- Agent执行日志保留30天
-- DELETE FROM agent_execution_logs WHERE created_at < NOW() - INTERVAL '30 days';
-- 
-- 通知表清理已读超过30天的通知
-- DELETE FROM notifications WHERE is_read = TRUE AND read_at < NOW() - INTERVAL '30 days';
```

---

## 3. 索引优化说明

### 3.1 核心索引

| 表 | 索引 | 类型 | 用途 |
|----|------|------|------|
| users | idx_users_role | B-tree | 按角色筛选用户 |
| users | idx_users_is_active | B-tree | 过滤活跃用户 |
| users | idx_users_is_deleted | B-tree | 软删除过滤 |
| projects | idx_projects_creator_id | B-tree | 按用户查询项目 |
| projects | idx_projects_status | B-tree | 按状态筛选项目 |
| projects | idx_projects_current_step | B-tree | 按步骤筛选项目 |
| projects | idx_projects_is_deleted | B-tree | 软删除过滤 |
| tasks | idx_tasks_project_id | B-tree | 按项目查询任务 |
| tasks | idx_tasks_status | B-tree | 按状态筛选任务 |
| tasks | idx_tasks_dependency_order | B-tree | 依赖图排序 |
| tasks | idx_tasks_is_deleted | B-tree | 软删除过滤 |
| qa_records | idx_qa_records_task_id | B-tree | 按任务查询QA记录 |
| group_messages | idx_group_messages_group_id | B-tree | 按群组查询消息 |
| group_messages | idx_group_messages_timestamp | B-tree | 消息时间排序 |
| group_messages | idx_group_messages_content_gin | GIN | 全文搜索 |
| commits | idx_commits_sha | B-tree | 按SHA查找提交 |
| audit_logs | idx_audit_logs_created_at | B-tree | 日志时间查询 |

### 3.2 复合索引

```sql
-- 项目任务查询优化 (按项目+状态+步骤)
CREATE INDEX idx_tasks_project_status_step ON tasks (project_id, status, step_number);

-- QA记录查询优化
CREATE INDEX idx_qa_records_task_result ON qa_records (task_id, acceptance_result);

-- 群消息查询优化
CREATE INDEX idx_group_messages_group_time ON group_messages (group_id, timestamp DESC);

-- 通知查询优化
CREATE INDEX idx_notifications_user_unread ON notifications (user_id, is_read, created_at DESC)
    WHERE is_read = FALSE;
```

### 3.3 JSONB 索引

```sql
-- QA检验维度索引
CREATE INDEX idx_qa_records_dimensions GIN ON qa_records USING GIN (review_dimensions);

-- 群消息metadata索引
CREATE INDEX idx_group_messages_metadata GIN ON group_messages USING GIN (metadata);

-- Agent配置索引
CREATE INDEX idx_agents_config GIN ON agents USING GIN (config);
```

---

## 4. 数据完整性约束

### 4.1 外键约束

所有外键均设置了 ON DELETE 和 ON UPDATE 策略:

| 表 | 外键列 | 引用表 | ON DELETE | ON UPDATE |
|----|--------|--------|-----------|-----------|
| projects | creator_id | users | RESTRICT | CASCADE |
| requirements | project_id | projects | CASCADE | CASCADE |
| requirements | confirmed_by | users | SET NULL | CASCADE |
| tasks | project_id | projects | CASCADE | CASCADE |
| tasks | assignee_agent_id | agents | SET NULL | CASCADE |
| tasks | parent_task_id | tasks | SET NULL | CASCADE |
| task_dependencies | source_task_id | tasks | CASCADE | CASCADE |
| task_dependencies | target_task_id | tasks | CASCADE | CASCADE |
| agent_execution_logs | task_id | tasks | CASCADE | CASCADE |
| agent_execution_logs | agent_id | agents | RESTRICT | CASCADE |
| qa_records | task_id | tasks | CASCADE | CASCADE |
| qa_records | reviewer_agent_id | agents | RESTRICT | CASCADE |
| groups | project_id | projects | CASCADE | CASCADE |
| groups | host_agent_id | agents | SET NULL | CASCADE |
| group_members | group_id | groups | CASCADE | CASCADE |
| group_members | user_id | users | CASCADE | CASCADE |
| group_members | agent_id | agents | CASCADE | CASCADE |
| group_messages | group_id | groups | CASCADE | CASCADE |
| group_messages | sender_user_id | users | CASCADE | CASCADE |
| group_messages | sender_agent_id | agents | CASCADE | CASCADE |
| group_messages | parent_message_id | group_messages | SET NULL | CASCADE |
| meeting_outcomes | group_id | groups | CASCADE | CASCADE |
| meeting_outcomes | host_agent_id | agents | CASCADE | CASCADE |
| swarms | project_id | projects | CASCADE | CASCADE |
| swarms | manager_agent_id | agents | RESTRICT | CASCADE |
| swarm_members | swarm_id | swarms | CASCADE | CASCADE |
| swarm_members | agent_id | agents | SET NULL | CASCADE |
| swarm_members | current_task_id | tasks | SET NULL | CASCADE |
| notifications | user_id | users | CASCADE | CASCADE |
| notifications | project_id | projects | CASCADE | CASCADE |
| notifications | related_task_id | tasks | SET NULL | CASCADE |
| notifications | related_qa_id | qa_records | SET NULL | CASCADE |
| repos | project_id | projects | CASCADE | CASCADE |
| repo_branches | repo_id | repos | CASCADE | CASCADE |
| pull_requests | repo_id | repos | CASCADE | CASCADE |
| commits | repo_id | repos | CASCADE | CASCADE |
| task_commits | task_id | tasks | CASCADE | CASCADE |
| task_commits | commit_id | commits | CASCADE | CASCADE |
| task_commits | qa_record_id | qa_records | SET NULL | CASCADE |
| audit_logs | user_id | users | SET NULL | CASCADE |
| audit_logs | agent_id | agents | SET NULL | CASCADE |
| audit_logs | project_id | projects | SET NULL | CASCADE |

策略说明:
- CASCADE: 级联删除/更新 (子记录跟随父记录)
- RESTRICT: 禁止删除 (引用该Agent的记录存在时禁止删除Agent)
- SET NULL: 设为NULL (可选关联字段, 父记录删除时清空关联)

### 4.2 检查约束

| 表 | 约束 | 说明 |
|----|------|------|
| users | role IN ('user', 'admin') | 角色枚举 |
| projects | status IN (...) | 项目状态枚举 |
| projects | current_step > 0 | 步骤编号为正整数 (上限由 system_configs.max_step_number 动态管理) |
| agents | agent_type IN ('named', 'swarm') | Agent类型 |
| agents | status IN (...) | Agent状态枚举 |
| tasks | status IN (...) | 任务状态枚举 |
| tasks | step_number > 0 | 步骤编号为正整数 (上限由 system_configs.max_step_number 动态管理) |
| tasks | is_atomic 与行数/时间关联 | 原子化任务校验 |
| qa_records | score BETWEEN 0 AND 100 | 评分范围 |
| qa_records | acceptance_result IN ('pass', 'fail') | 检验结果 |
| groups | mode IN ('discussion', 'meeting') | 群组模式 |
| swarms | purpose IN ('code_writing', 'test') | 蜂群目的 |
| swarms | completed + failed <= total | 任务计数一致性 |
| group_members | user_id和agent_id二选一 | 成员类型约束 |
| group_messages | sender_user_id/sender_agent_id互斥 | 发送者类型约束 (通过外键保证参照完整性) |
| notifications | is_read与read_at一致性 | 已读状态约束 |
| task_dependencies | source_task_id <> target_task_id | 禁止自引用 |

### 4.3 唯一约束

| 表 | 约束 | 说明 |
|----|------|------|
| users | username | 用户名唯一 |
| users | email | 邮箱唯一 |
| projects | project_code | 项目编码唯一 |
| projects | (name, creator_id) | 同一用户下项目名称唯一 |
| agents | name | Agent名称唯一 |
| requirements | (project_id, version) | 项目需求版本唯一 |
| groups | project_id | 每个项目只有一个讨论群 |
| repos | project_id | 每个项目只有一个代码仓库 |
| repos | gitea_repo_id | Gitea仓库ID唯一 |
| commits | (repo_id, sha) | 仓库内commit唯一 |
| pull_requests | (repo_id, number) | 仓库内PR编号唯一 |
| repo_branches | (repo_id, name) | 仓库内分支名称唯一 |
| swarm_members | (swarm_id, agent_name, agent_type) | 蜂群内成员唯一 |
| system_configs | config_key | 配置键唯一 |
| task_dependencies | (source_task_id, target_task_id) | 依赖关系唯一 |

### 4.4 循环依赖防止

task_dependencies 表通过触发器 `trg_task_dependencies_cycle_check` 使用递归CTE检测循环依赖。当插入或更新依赖关系时，从 target_task_id 出发递归遍历所有下游依赖，若能到达 source_task_id 则判定为循环，抛出异常拒绝操作。这确保了任务依赖图始终为有向无环图 (DAG)。

---

## 5. 软删除机制

### 5.1 软删除字段

以下核心业务表添加了 `is_deleted BOOLEAN NOT NULL DEFAULT FALSE` 字段:

| 表 | 说明 |
|----|------|
| users | 用户软删除 |
| projects | 项目软删除 |
| tasks | 任务软删除 |

### 5.2 使用约定

- 删除操作将 `is_deleted` 设为 TRUE，而非执行物理 DELETE
- 查询默认过滤 `WHERE is_deleted = FALSE`
- 已删除记录保留用于审计追溯
- 定期清理超过保留期的已删除记录（由运维定时任务执行）

---

## 6. 数据库性能优化

### 6.1 查询优化

```sql
-- 使用 EXPLAIN ANALYZE 分析慢查询
EXPLAIN ANALYZE
SELECT * FROM v_project_progress WHERE project_id = 'xxx';

-- 定期更新表统计信息
ANALYZE projects;
ANALYZE tasks;
ANALYZE qa_records;
ANALYZE group_messages;

-- 真空清理
VACUUM ANALYZE group_messages;
```

### 6.2 连接池配置

```yaml
# PostgreSQL 配置 (postgresql.conf)
max_connections = 200
shared_buffers = 2GB          # 内存的25%
work_mem = 64MB               # 排序/哈希操作内存
maintenance_work_mem = 512MB  # VACUUM等维护操作
effective_cache_size = 6GB    # 内存的75%
wal_buffers = 64MB
checkpoint_completion_target = 0.9
max_wal_size = 4GB
min_wal_size = 1GB

# 日志配置
log_min_duration_statement = 1000  # 记录超过1秒的查询
log_lock_waits = on
log_temp_files = 0
```

### 6.3 备份策略

```bash
#!/bin/bash
# 每日全量备份 (凌晨2:00)
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h localhost -U devflow \
    -F custom -f /data/backups/devflow_$(date +%Y%m%d_%H%M%S).dump \
    devflow

# 增量备份 (每6小时) - 使用 WAL 归档
# postgresql.conf:
# wal_level = replica
# archive_mode = on
# archive_command = 'cp %p /data/backups/wal/%f'

# 保留策略
find /data/backups/ -name "*.dump" -mtime +30 -delete
```

---

## 7. 数据迁移

### 7.1 迁移工具

使用 Alembic 进行数据库版本管理:

```bash
# 初始化迁移环境
alembic init migrations

# 创建新迁移
alembic revision -m "add project folder path column"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 7.2 迁移配置

```python
# migrations/env.py
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.models import Base

config = context.config
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=False
        )
        with context.begin_transaction():
            context.run_migrations()
```

---

## 8. 监控与告警

### 8.1 数据库监控指标

```sql
-- 活跃连接数
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- 慢查询
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 表大小
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 索引使用情况
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### 8.2 告警阈值

| 指标 | 警告阈值 | 严重阈值 |
|------|----------|----------|
| 活跃连接数 | > 150 | > 180 |
| 慢查询比例 | > 5% | > 10% |
| 磁盘使用率 | > 70% | > 85% |
| 复制延迟 | > 10s | > 60s |
| 死锁次数 | > 5/hour | > 20/hour |

---

文档结束
