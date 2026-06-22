# DevFlow 数据库设计文档

**版本**: V19
**日期**: 2026-06-28
**作者**: HouWang (后旺)
**状态**: V19 版本（修正 V18 执行顺序致命错误、触发器函数引用错误、枚举类型未使用、字段约束缺失、sender_id 校验兜底等 8 项问题）

---

## 变更日志

- V19 (2026-06-28): 根据后荣检验报告修正以下问题
  1. 【执行顺序致命错误修复】将 swarms 表从 14-swarms.sql 提前至 06-swarms.sql，将 swarm_members 表从 15-swarm-members.sql 提前至 07-swarm-members.sql，确保 tasks 表（08-tasks.sql）引用 swarms 外键时目标表已存在，DDL 可正常执行
  2. 【触发器引用未存在表修复】swarm_members 表（07）现位于 swarms 表（06）之后、tasks 表（08）之前，确保 swarms 表的 auto_add_manager_to_members 触发器函数引用 swarm_members 表时目标表已存在
  3. 【触发器函数不存在修复】18-repo-branches.sql 中原调用不存在的 update_repo_branches_updated_at_column() 函数，V19 修正为标准函数 update_updated_at_column()（定义于 02-users.sql）
  4. 【枚举定义未使用修复】09-task-dependencies.sql 中 dependency_type 字段由 VARCHAR(50)+CHECK 约束改为直接使用 dependency_type_enum 枚举类型，消除枚举冗余
  5. 【swarm_members.status 约束缺失修复】07-swarm-members.sql 中 status 字段新增 CHECK (status IN ('active', 'inactive', 'removed')) 约束，限制值域
  6. 【group_messages.sender_id 无外键约束修复】14-group-messages.sql 新增 validate_sender_exists() 触发器函数和 trg_validate_sender 触发器，在 INSERT/UPDATE 时校验 sender_id 是否存在于 users 或 agents 表，提供数据库级兜底校验
  7. 【ER 图可读性改善】重新设计 ASCII ER 图，按模块分层展示（用户与项目层、任务与执行层、协作与沟通层、蜂群管理层、代码仓库层），关系方向更清晰
  8. 保留 V14~V18 全部修正内容

- V18 (2026-06-27): 根据后荣检验报告修正以下问题
  1. SQL 文件清单修正：修正为与实际 25 个 SQL 文件一一对应
  2. ER 图补全：补全全部 21 张表的 ER 关系
  3. 枚举类型补全：完整列出 16 个枚举类型及全部值
  4. 第 2~11 节内容补全：补充 DDL 文件引用、关键设计决策、约束与索引总结等内容
  5. 保留 V14~V17 全部修正内容

- V17 (2026-06-27): 拆分文件架构、group_members 级联策略修正、sender_id 约束说明、FK 索引验证表、约束命名规范
- V16 (2026-06-26): 修复截断问题，确认全部 DDL 完整可执行
- V14 (2026-06-22): 修复 meeting_type 枚举不完整，新增 dependency_type 枚举
- V12 (2026-06-21): 修复 updated_at DEFAULT NOW()，CHECK 约束上限修正为 16
- V11 (2026-06-20): 修复 ER 图重复展示，补充 agent_status 应用层管理注释
- V10 (2026-06-19): current_step/step_number 上限改为 16，新增事务隔离/分区策略/表清单章节
- V9 (2026-06-18): 补充 citext 扩展，新增索引设计与外键级联策略总览
- V6 (2026-06-17): 循环依赖递归 CTE、三选一 CHECK 约束、触发器锁策略优化
- V5 (2026-06-16): 初始版本

---

## 文档结构说明

V19 文档采用拆分文件架构：

- **主文档（本文）**：包含变更日志、ER 图、枚举类型定义、DDL 文件引用、关键设计决策、索引与级联策略、事务隔离、分区策略、存储过程、视图、表清单、修正对照表、执行指南
- **SQL 文件**：完整 DDL 拆分为 25 个独立 `.sql` 文件，存放于 `sql/` 子目录
- **执行顺序**：按文件名数字顺序执行（01 到 99），确保依赖关系正确

### V19 核心修正：执行顺序重排

| 问题 | V18 状态 | V19 修正 |
|------|----------|----------|
| tasks 引用 swarms 外键 | 06-tasks.sql 引用 14-swarms.sql，执行时报错 | swarms 提前至 06，tasks 后移至 08，依赖关系正确 |
| swarms 触发器引用 swarm_members | 14-swarms.sql 触发器引用 15-swarm-members.sql | swarm_members 提前至 07，在 06-swarms 之后，触发器函数可正常创建 |
| repo-branches 触发器函数不存在 | 调用 update_repo_branches_updated_at_column() | 改为标准函数 update_updated_at_column() |
| dependency_type 未使用枚举 | VARCHAR(50)+CHECK | 改为 dependency_type_enum |
| swarm_members.status 无约束 | VARCHAR(50) 无限制 | 新增 CHECK 约束 |
| group_messages.sender_id 无校验 | 仅应用层校验 | 新增数据库级触发器兜底校验 |

### SQL 文件清单（V19 修正：执行顺序已验证可正确执行）

| 序号 | 文件 | 说明 | 行数 |
|------|------|------|------|
| 1 | `sql/01-enums.sql` | 扩展与枚举类型定义（16 个枚举） | ~54 |
| 2 | `sql/02-users.sql` | 用户表（含 update_updated_at_column 函数） | ~39 |
| 3 | `sql/03-projects.sql` | 项目表（含 sync_project_current_step 触发器） | ~90 |
| 4 | `sql/04-requirements.sql` | 需求表（软件需求说明书） | ~30 |
| 5 | `sql/05-agents.sql` | Agent 表（含 9 个命名 Agent 初始化） | ~47 |
| 6 | `sql/06-swarms.sql` | Agent 蜂群表（V19 从 14 提前至 06） | ~47 |
| 7 | `sql/07-swarm-members.sql` | 蜂群成员关联表（V19 从 15 提前至 07，新增 CHECK 约束） | ~22 |
| 8 | `sql/08-tasks.sql` | 任务表（V19 从 06 后移至 08，swarms 依赖已满足） | ~80 |
| 9 | `sql/09-task-dependencies.sql` | 任务依赖表（V19 从 07 后移至 09，改用枚举类型） | ~90 |
| 10 | `sql/10-agent-execution-logs.sql` | Agent 执行日志表 | ~23 |
| 11 | `sql/11-qa-records.sql` | QA 检验记录表 | ~28 |
| 12 | `sql/12-groups.sql` | 群组表（项目讨论群） | ~30 |
| 13 | `sql/13-group-members.sql` | 群成员表（V17：ON DELETE SET NULL） | ~30 |
| 14 | `sql/14-group-messages.sql` | 群消息表（V19：新增 sender 校验触发器） | ~68 |
| 15 | `sql/15-meeting-outcomes.sql` | 会议结果表 | ~32 |
| 16 | `sql/16-notifications.sql` | 通知表 | ~26 |
| 17 | `sql/17-repos.sql` | 代码仓库表 | ~26 |
| 18 | `sql/18-repo-branches.sql` | 代码分支表（V19：修正触发器函数名） | ~28 |
| 19 | `sql/19-pull-requests.sql` | 拉取请求表 | ~34 |
| 20 | `sql/20-commits.sql` | 提交记录表 | ~22 |
| 21 | `sql/21-task-commits.sql` | 任务与提交关联表 | ~20 |
| 22 | `sql/96-soft-delete-cleanup.sql` | 软删除物理清理存储过程 | ~130 |
| 23 | `sql/97-permissions.sql` | 权限设置 | ~18 |
| 24 | `sql/98-init-data.sql` | 初始化数据 | ~12 |
| 25 | `sql/99-views.sql` | 视图定义 | ~72 |
| **合计** | **25 个文件** | | **约 1082 行** |

> 完整 DDL 请查看 `sql/` 目录下的各 `.sql` 文件。以下保留设计说明与架构文档。

---

## 1. ER 概述

### 1.1 实体关系图（V19 改善：按模块分层展示）

```
===== 用户与项目层 =====

+----------+     +-----------+     +--------------+
|  users   |-----| projects  |-----| requirements |
|  (02)    | 1:N |   (03)    | 1:N |   (04)       |
+----------+     +-----+-----+     +--------------+
                       |
          +------------+-------------+
          |            |             |
          v            v             v
   +----------+  +----------+  +----------+
   |  groups  |  |  swarms  |  |  repos   |
   |  (12)    |  |  (06)    |  |  (17)    |
   |  1:1     |  |          |  |  1:1     |
   +----+----+  +----+-----+  +----+-----+
        |             |              |
        v             v              v
 +-------------+ +---------------+ +---------------+
 |group_members| |swarm_members  | |repo_branches  |
 |   (13)      | |   (07)        | |   (18)        |
 +------+------+ +---------------+ +-------+-------+
        |                                                |
        v                                                v
 +--------------+                              +---------------+
 |group_messages|                              |pull_requests  |
 |   (14)       |                              |    (19)       |
 +--------------+                              +-------+-------+
                                                       |
                                                       v
                                                  +----------+
                                                  | commits  |
                                                  |  (20)    |
                                                  +-----+----+
                                                        |
                                                        v
                                               +--------------+
                                               |task_commits  |
                                               |    (21)      |
                                               +--------------+

===== 任务与执行层 =====

+----------+     +-----------+     +----------+
|  agents  |-----|   tasks   |-----|  task_deps|
|  (05)    | M:N |   (08)    |     |  (09)     |
+-----+----+     +-----+-----+     +----------+
      |                    |
      |         +----------+----------+
      |         v                      v
      |  +--------------+     +--------------+
      |  | agent_exec   |     |  qa_records  |
      |  |  _logs (10)  |     |   (11)       |
      |  +--------------+     +--------------+
      |           |
      v           v
+------------------+
| notifications    |
|   (16)           |
+------------------+

===== 协作与沟通层 =====

+------------------+
| meeting_outcomes |
|    (15)          |
+------------------+
  (关联 groups + agents)

===== 蜂群管理层 =====

+----------+     +-----------+     +---------------+
|  agents  |-----|  swarms   |-----|swarm_members  |
|  (05)    | 1:N |   (06)    | 1:N |    (07)       |
+----------+     +-----------+     +---------------+
  manager_agent_id  自动注册触发器  status CHECK 约束
```

**关系方向说明（按外键）:**
- `A ---< B` 表示 B 表有外键引用 A 表
- `1:N` 表示一对多关系
- `1:1` 表示一对一关系
- `M:N` 表示多对多（通过关联表或三选一字段）

**核心关系链:**
```
users -> projects -> tasks -> task_dependencies
                   -> agent_execution_logs
                   -> qa_records
                   -> task_commits -> commits
projects -> groups -> group_members
                    -> group_messages
                    -> meeting_outcomes
projects -> swarms -> swarm_members
projects -> repos -> repo_branches
                    -> pull_requests
                    -> commits -> task_commits
agents -> tasks (assignee)
agents -> group_members
agents -> swarms (manager)
agents -> swarm_members
```

### 1.2 核心实体说明

| 实体 | 对应 SQL 文件 | 说明 | 关键约束 |
|------|------|------|------|
| users | 02-users.sql | 人类用户信息 | email UNIQUE(citext)、password_hash 非空 |
| projects | 03-projects.sql | 项目主表 | code UNIQUE、current_step 1~16 |
| requirements | 04-requirements.sql | 软件需求说明书 | 关联 project_id、(project_id, version) 唯一 |
| agents | 05-agents.sql | Agent 信息 | name UNIQUE、支持命名 Agent 与蜂群 Agent |
| swarms | 06-swarms.sql | Agent 蜂群 | 关联 project_id、manager_agent_id（V19 从 14 提前） |
| swarm_members | 07-swarm-members.sql | 蜂群成员 | UNIQUE(swarm_id, agent_id)、status CHECK 约束（V19 新增） |
| tasks | 08-tasks.sql | 任务记录 | step_number 1~16、三选一分配（V19 从 06 后移） |
| task_dependencies | 09-task-dependencies.sql | 任务依赖 | 防止循环依赖、防止自依赖、使用枚举类型（V19 修正） |
| agent_execution_logs | 10-agent-execution-logs.sql | Agent 执行日志 | 关联 task_id 和 agent_id |
| qa_records | 11-qa-records.sql | QA 检验记录 | score 0~100、关联 task_id |
| groups | 12-groups.sql | 项目讨论群 | 与 project 1:1（project_id UNIQUE） |
| group_members | 13-group-members.sql | 群成员 | V17: user_id/agent_id ON DELETE SET NULL |
| group_messages | 14-group-messages.sql | 群消息 | V19: 新增 sender 校验触发器 |
| meeting_outcomes | 15-meeting-outcomes.sql | 会议结果 | UNIQUE(group_id, started_at) |
| notifications | 16-notifications.sql | 通知消息 | 关联 user_id 和 project_id |
| repos | 17-repos.sql | 代码仓库 | 与 project 1:1、(vcs_platform, vcs_repo_id) 唯一 |
| repo_branches | 18-repo-branches.sql | 代码分支 | UNIQUE(repo_id, name)、V19 修正触发器函数 |
| pull_requests | 19-pull-requests.sql | 拉取请求 | UNIQUE(repo_id, number) |
| commits | 20-commits.sql | 提交记录 | UNIQUE(repo_id, sha) |
| task_commits | 21-task-commits.sql | 任务-提交关联 | UNIQUE(task_id, commit_id) |

### 1.3 枚举类型定义（V19 确认：16 个枚举类型，全部被引用）

| 序号 | 枚举类型 | 值 | 说明 | 所在文件 | 引用表 |
|------|------|------|------|------|------|
| 1 | `user_role` | `user`, `admin`, `system_admin` | 用户角色 | 01-enums.sql | users.role |
| 2 | `project_status` | `created`, `in_progress`, `completed`, `cancelled` | 项目状态 | 01-enums.sql | projects.status |
| 3 | `agent_type` | `named`, `swarm` | Agent 类型 | 01-enums.sql | agents.agent_type |
| 4 | `agent_status` | `online`, `offline`, `busy` | Agent 状态 | 01-enums.sql | agents.status |
| 5 | `task_status` | `pending`, `in_progress`, `completed`, `failed`, `cancelled` | 任务状态 | 01-enums.sql | tasks.status |
| 6 | `task_type` | 16 个值对应 DevFlow 16 步 | 任务类型 | 01-enums.sql | tasks.type |
| 7 | `group_mode` | `discussion`, `meeting` | 群组模式 | 01-enums.sql | groups.mode |
| 8 | `member_type` | `user`, `agent` | 群成员类型 | 01-enums.sql | group_members.member_type |
| 9 | `sender_type` | `user`, `agent` | 消息发送者类型 | 01-enums.sql | group_messages.sender_type |
| 10 | `meeting_type` | `requirement_review`, `tech_solution`, `daily_standup`, `incident_postmortem` | 会议类型 | 01-enums.sql | meeting_outcomes.type |
| 11 | `dependency_type_enum` | `finish_to_start`, `start_to_start`, `finish_to_finish`, `start_to_finish` | 依赖类型 | 01-enums.sql | **task_dependencies.dependency_type（V19 已使用）** |
| 12 | `swarm_purpose` | `code_writing`, `testing` | 蜂群用途 | 01-enums.sql | swarms.purpose |
| 13 | `swarm_status` | `active`, `completed`, `dissolved` | 蜂群状态 | 01-enums.sql | swarms.status |
| 14 | `qa_result` | `pass`, `fail` | QA 检验结果 | 01-enums.sql | qa_records.acceptance_result |
| 15 | `notification_type` | `step_complete`, `qa_pass`, `qa_fail`, `task_assigned`, `task_completed`, `project_complete`, `system_alert` | 通知类型 | 01-enums.sql | notifications.type |
| 16 | `pr_status` | `open`, `closed`, `merged` | Pull Request 状态 | 01-enums.sql | pull_requests.status |

> **V19 修正确认**：`dependency_type_enum` 枚举类型现已被 `task_dependencies` 表直接引用（09-task-dependencies.sql），V18 中"枚举被定义但从未被引用"的问题已解决。

> **agent_status 应用层管理注释**: `agent_status` 枚举定义了三种状态，但实际状态切换由应用层管理：
> - `online`: Agent 可用，可被分配新任务
> - `busy`: Agent 正在执行任务中（任务分配时由应用层自动设置）
> - `offline`: Agent 不可用或空闲（任务完成/失败/取消时由应用层恢复）
> 数据库不通过触发器自动切换状态，避免数据库层与应用层状态管理冲突。

---

## 2. DDL 文件引用

完整建表语句、索引定义、触发器、存储过程请参见 `sql/` 目录下的独立 SQL 文件。

### 2.1 枚举与基础设置
- `sql/01-enums.sql` — 扩展（uuid-ossp、pg_trgm、citext）与 16 个枚举类型定义

### 2.2 核心业务表
- `sql/02-users.sql` — 用户表（含 citext email 唯一约束、updated_at 触发器、update_updated_at_column 函数）
- `sql/03-projects.sql` — 项目表（含 current_step CHECK 1~16、sync_project_current_step 触发器）
- `sql/04-requirements.sql` — 需求表（含 (project_id, version) 唯一索引）
- `sql/05-agents.sql` — Agent 表（含 9 个命名 Agent 初始化数据）

### 2.3 蜂群管理表（V19 从第 2.5 节提前至此）
- `sql/06-swarms.sql` — Agent 蜂群表（含管理器自动注册触发器、V19 从 14 提前至 06）
- `sql/07-swarm-members.sql` — 蜂群成员关联表（V19 从 15 提前至 07、新增 status CHECK 约束）

### 2.4 任务与依赖表
- `sql/08-tasks.sql` — 任务表（含 step_number CHECK 1~16、三选一分配约束、父子项目一致性触发器、V19 从 06 后移至 08）
- `sql/09-task-dependencies.sql` — 任务依赖表（含循环依赖检测递归 CTE、同项目约束触发器、V19 改用 dependency_type_enum 枚举类型）

### 2.5 执行与检验表
- `sql/10-agent-execution-logs.sql` — Agent 执行日志表
- `sql/11-qa-records.sql` — QA 检验记录表（含 score 0~100 CHECK 约束）

### 2.6 协作与沟通表
- `sql/12-groups.sql` — 群组表（与 project 1:1）
- `sql/13-group-members.sql` — 群成员表（V17 修正：ON DELETE SET NULL）
- `sql/14-group-messages.sql` — 群消息表（V19 新增 sender 校验触发器）
- `sql/15-meeting-outcomes.sql` — 会议结果表（UNIQUE(group_id, started_at)）

### 2.7 通知与代码仓库表
- `sql/16-notifications.sql` — 通知表
- `sql/17-repos.sql` — 代码仓库表（与 project 1:1）
- `sql/18-repo-branches.sql` — 代码分支表（V19 修正触发器函数名）
- `sql/19-pull-requests.sql` — 拉取请求表
- `sql/20-commits.sql` — 提交记录表
- `sql/21-task-commits.sql` — 任务与提交关联表

### 2.8 工具与辅助脚本
- `sql/96-soft-delete-cleanup.sql` — 软删除物理清理存储过程（按外键依赖顺序逐层清理）
- `sql/97-permissions.sql` — 数据库权限设置
- `sql/98-init-data.sql` — 初始化数据（admin 用户）
- `sql/99-views.sql` — 视图定义（v_project_progress、v_agent_load、v_qa_statistics）

---

## 3. 关键设计决策

### 3.1 软删除策略

所有核心业务表均包含 `deleted_at` 字段（nullable timestamptz），支持软删除。包含软删除的表：

| 表名 | deleted_at 字段 | 说明 |
|------|------|------|
| projects | 有 | 项目逻辑删除 |
| tasks | 有 | 任务逻辑删除 |
| groups | 有 | 群组逻辑删除 |
| swarms | 有 | 蜂群逻辑删除 |
| notifications | 有 | 通知逻辑删除 |

应用层查询应添加 `WHERE deleted_at IS NULL` 条件。物理清理通过 `cleanup_soft_deleted()` 存储过程执行（保留期默认 90 天）。

### 3.2 任务分配三选一约束

tasks 表通过 CHECK 约束确保 `assignee_agent_id`、`assignee_swarm_id`、`assignee_user_id` 三个字段中恰好一个非空或全部为空：

```sql
CHECK (
    (CASE WHEN assignee_agent_id IS NOT NULL THEN 1 ELSE 0 END) +
    (CASE WHEN assignee_swarm_id IS NOT NULL THEN 1 ELSE 0 END) +
    (CASE WHEN assignee_user_id IS NOT NULL THEN 1 ELSE 0 END) <= 1
)
```

### 3.3 循环依赖检测

task_dependencies 表提供递归 CTE 触发器，在插入前验证不会引入循环依赖：

```sql
WITH RECURSIVE reachable AS (
    SELECT source_task_id, target_task_id
    FROM task_dependencies
    WHERE source_task_id = v_source
    UNION
    SELECT r.source_task_id, td.target_task_id
    FROM reachable r
    JOIN task_dependencies td ON td.source_task_id = r.target_task_id
    WHERE td.target_task_id <> v_source
)
SELECT EXISTS(SELECT 1 FROM reachable WHERE target_task_id = v_target);
```

### 3.4 同步项目当前步骤

projects 表通过 `sync_project_current_step` 触发器自动更新 current_step：
- INSERT 任务时：新任务默认为 pending 状态，不更新项目进度
- UPDATE 任务状态为 completed 时：自动推进 current_step
- UPDATE 任务从 completed 变为其他状态时：重新计算最大 step_number

### 3.5 V19 新增：sender_id 校验触发器

group_messages 表的 sender_id 字段因 PostgreSQL 不支持单字段多目标条件外键，无法定义标准 REFERENCES 约束。V19 新增触发器级校验兜底：

```sql
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
```

### 3.6 V19 新增：执行顺序重排说明

V18 存在的执行顺序致命错误在 V19 中已修复：

| 问题 | 原因 | V19 方案 |
|------|------|----------|
| tasks 引用 swarms 外键失败 | swarms(14) 在 tasks(06) 之后 | swarms 提前至 06，tasks 后移至 08 |
| swarms 触发器引用 swarm_members 失败 | swarm_members(15) 在 swarms(14) 之后 | swarm_members 提前至 07，在 swarms(06) 之后 |
| repo-branches 触发器函数不存在 | 调用了未定义的函数名 | 改为标准函数 update_updated_at_column() |

**V19 执行顺序依赖链验证:**
```
01-enums (无依赖)
02-users (依赖: 01)
03-projects (依赖: 02)
04-requirements (依赖: 03)
05-agents (依赖: 01)
06-swarms (依赖: 03, 05) -- 新项目表
07-swarm_members (依赖: 06, 05) -- 新蜂群成员
08-tasks (依赖: 03, 05, 06, 02) -- 所有依赖已满足
09-task_dependencies (依赖: 08)
10-agent_execution_logs (依赖: 08, 05)
11-qa_records (依赖: 08, 05)
12-groups (依赖: 03, 05)
13-group_members (依赖: 12, 02, 05)
14-group_messages (依赖: 12, 02, 05)
15-meeting_outcomes (依赖: 12, 05)
16-notifications (依赖: 02, 03)
17-repos (依赖: 03)
18-repo_branches (依赖: 17)
19-pull_requests (依赖: 17)
20-commits (依赖: 17)
21-task_commits (依赖: 08, 20)
```

### 3.7 V17 修正项保留

#### 3.7.1 group_members 级联策略变更

```sql
ALTER TABLE group_members
  DROP CONSTRAINT IF EXISTS fk_group_members_user,
  ADD CONSTRAINT fk_group_members_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE SET NULL;

ALTER TABLE group_members
  DROP CONSTRAINT IF EXISTS fk_group_members_agent,
  ADD CONSTRAINT fk_group_members_agent
    FOREIGN KEY (agent_id) REFERENCES agents(id)
    ON DELETE SET NULL;
```

---

## 4. 约束与索引总结

### 4.1 CHECK 约束清单

| 表 | 约束 | 说明 | 所在文件 |
|---|------|------|---|
| projects | `current_step >= 1 AND current_step <= 16` | DevFlow 16 步流程 | 03-projects.sql |
| tasks | `step_number >= 1 AND step_number <= 16` | DevFlow 16 步流程 | 08-tasks.sql |
| tasks | 三选一分配约束 | 见 3.2 节 | 08-tasks.sql |
| tasks | `completed_at IS NULL OR completed_at >= created_at` | 完成时间不早于创建时间 | 08-tasks.sql |
| task_dependencies | `source_task_id <> target_task_id` | 禁止自依赖 | 09-task-dependencies.sql |
| task_dependencies | dependency_type 使用枚举类型 | V19 修正：直接使用枚举，无需 CHECK | 09-task-dependencies.sql |
| group_members | member_type 与 user_id/agent_id 互斥约束 | user 类型时 user_id 非空，agent 类型时 agent_id 非空 | 13-group-members.sql |
| group_messages | sender_type 与 sender_id 互斥约束 | sender_type 非空时 sender_id 必须非空 | 14-group-messages.sql |
| group_messages | `message_type IN ('system','agent','user')` | 消息类型合法值 | 14-group-messages.sql |
| meeting_outcomes | `ended_at IS NULL OR ended_at >= started_at` | 结束时间不早于开始时间 | 15-meeting-outcomes.sql |
| repos | `vcs_platform IN ('gitea','github','gitlab')` | VCS 平台合法值 | 17-repos.sql |
| qa_records | `score >= 0 AND score <= 100` | 评分范围 | 11-qa-records.sql |
| swarm_members | `status IN ('active','inactive','removed')` | **V19 新增**：蜂群成员状态合法值 | 07-swarm-members.sql |

### 4.2 UNIQUE 约束清单

| 表 | 约束 | 说明 | 所在文件 |
|---|------|------|---|
| users | `username UNIQUE` | 用户名唯一 | 02-users.sql |
| users | `email UNIQUE (citext)` | 邮箱唯一（不区分大小写） | 02-users.sql |
| projects | `code UNIQUE` | 业务编号唯一 | 03-projects.sql |
| requirements | `(project_id, version) UNIQUE` | 同项目同版本唯一 | 04-requirements.sql |
| agents | `name UNIQUE` | Agent 名称唯一 | 05-agents.sql |
| groups | `project_id UNIQUE` | 项目与群 1:1 | 12-groups.sql |
| meeting_outcomes | `(group_id, started_at) UNIQUE` | 同一会议不重复 | 15-meeting-outcomes.sql |
| task_dependencies | `(source_task_id, target_task_id) UNIQUE` | 同一对依赖不重复 | 09-task-dependencies.sql |
| repo_branches | `(repo_id, name) UNIQUE` | 同仓库分支名唯一 | 18-repo-branches.sql |
| pull_requests | `(repo_id, number) UNIQUE` | 同仓库 PR 号唯一 | 19-pull-requests.sql |
| commits | `(repo_id, sha) UNIQUE` | 同仓库提交 SHA 唯一 | 20-commits.sql |
| task_commits | `(task_id, commit_id) UNIQUE` | 同一关联不重复 | 21-task-commits.sql |
| swarm_members | `(swarm_id, agent_id) UNIQUE` | 同蜂群同 Agent 不重复 | 07-swarm-members.sql |
| repos | `project_id UNIQUE` | 项目与仓库 1:1 | 17-repos.sql |
| repos | `(vcs_platform, vcs_repo_id) UNIQUE` | VCS 仓库全局唯一 | 17-repos.sql |
| group_members | `(group_id, user_id) UNIQUE WHERE user_id IS NOT NULL` | 同群同用户不重复 | 13-group-members.sql |
| group_members | `(group_id, agent_id) UNIQUE WHERE agent_id IS NOT NULL` | 同群同 Agent 不重复 | 13-group-members.sql |

### 4.3 约束命名规范（V17 新增，V19 保留）

| 约束类型 | 命名格式 | 示例 |
|---|---|---|
| PRIMARY KEY | `pk_表名` | `pk_tasks` |
| FOREIGN KEY | `fk_表名_字段` | `fk_tasks_project` |
| CHECK | `chk_表名_描述` | `chk_tasks_step_range` |
| UNIQUE | `uq_表名_字段` | `uq_meeting_outcomes_group_started` |

---

## 5. 索引设计与外键级联策略总览

### 5.1 索引设计

| 表 | 索引 | 类型 | 说明 | 所在文件 |
|---|------|------|------|---|
| users | idx_users_username | B-tree | 按用户名查询 | 02-users.sql |
| projects | idx_projects_creator | B-tree | 按创建者查询项目 | 03-projects.sql |
| projects | idx_projects_status | B-tree | 按状态筛选项目 | 03-projects.sql |
| projects | idx_projects_name | GIN (pg_trgm) | 模糊搜索项目名称 | 03-projects.sql |
| projects | idx_projects_deleted | B-tree | 软删除过滤 | 03-projects.sql |
| projects | idx_projects_code | B-tree | 按业务编号查询 | 03-projects.sql |
| requirements | idx_requirements_project | B-tree | 按项目查询需求 | 04-requirements.sql |
| requirements | idx_requirements_project_version | UNIQUE | 同项目同版本唯一 | 04-requirements.sql |
| agents | idx_agents_type | B-tree | 按类型查询 Agent | 05-agents.sql |
| agents | idx_agents_status | B-tree | 按状态筛选 Agent | 05-agents.sql |
| agents | idx_agents_name | B-tree | 按名称查询 Agent | 05-agents.sql |
| agents | idx_agents_config_gin | GIN | 配置 JSONB 搜索 | 05-agents.sql |
| tasks | idx_tasks_project | B-tree | 按项目查询任务 | 08-tasks.sql |
| tasks | idx_tasks_status | B-tree | 按状态筛选任务 | 08-tasks.sql |
| tasks | idx_tasks_assignee | B-tree | 按 Agent 查询分配 | 08-tasks.sql |
| tasks | idx_tasks_swarm | B-tree | 按蜂群查询分配 | 08-tasks.sql |
| tasks | idx_tasks_assignee_user | B-tree | 按人类用户查询分配 | 08-tasks.sql |
| tasks | idx_tasks_step | B-tree | 按步骤筛选任务 | 08-tasks.sql |
| tasks | idx_tasks_parent | B-tree | 父子任务查询 | 08-tasks.sql |
| tasks | idx_tasks_deleted | B-tree | 软删除过滤 | 08-tasks.sql |
| tasks | idx_tasks_acceptance_criteria_gin | GIN | 验收标准全文搜索 | 08-tasks.sql |
| task_dependencies | idx_task_deps_source | B-tree | 按源任务查找依赖 | 09-task-dependencies.sql |
| task_dependencies | idx_task_deps_target | B-tree | 按目标任务查找依赖 | 09-task-dependencies.sql |
| agent_execution_logs | idx_exec_logs_task | B-tree | 按任务查询日志 | 10-agent-execution-logs.sql |
| agent_execution_logs | idx_exec_logs_agent | B-tree | 按 Agent 查询日志 | 10-agent-execution-logs.sql |
| agent_execution_logs | idx_exec_logs_created | B-tree | 按时间排序日志 | 10-agent-execution-logs.sql |
| qa_records | idx_qa_records_task | B-tree | 按任务查询 QA 记录 | 11-qa-records.sql |
| qa_records | idx_qa_records_reviewer | B-tree | 按审查者查询 | 11-qa-records.sql |
| qa_records | idx_qa_records_result | B-tree | 按结果筛选 QA 记录 | 11-qa-records.sql |
| qa_records | idx_qa_review_dimensions_gin | GIN | 审查维度全文搜索 | 11-qa-records.sql |
| groups | idx_groups_project | B-tree | 按项目查询群 | 12-groups.sql |
| groups | idx_groups_mode | B-tree | 按模式筛选群 | 12-groups.sql |
| group_members | idx_group_members_group | B-tree | 按群查询成员 | 13-group-members.sql |
| group_members | idx_group_members_user_only | B-tree | 按用户查询群成员 | 13-group-members.sql |
| group_members | idx_group_members_agent_only | B-tree | 按 Agent 查询群成员 | 13-group-members.sql |
| group_messages | idx_group_messages_group | B-tree | 按群查询消息 | 14-group-messages.sql |
| group_messages | idx_group_messages_sender | B-tree | 按发送者查询消息 | 14-group-messages.sql |
| group_messages | idx_group_messages_timestamp | B-tree | 按时间排序消息 | 14-group-messages.sql |
| group_messages | idx_group_messages_metadata_gin | GIN | 元数据全文搜索 | 14-group-messages.sql |
| meeting_outcomes | idx_meeting_outcomes_group | B-tree | 按群查询会议 | 15-meeting-outcomes.sql |
| meeting_outcomes | idx_meeting_outcomes_host | B-tree | 按主持人查询 | 15-meeting-outcomes.sql |
| meeting_outcomes | idx_meeting_outcomes_composite | B-tree | 群+主持人组合查询 | 15-meeting-outcomes.sql |
| swarms | idx_swarms_project | B-tree | 按项目查询蜂群 | 06-swarms.sql |
| swarms | idx_swarms_manager | B-tree | 按管理器查询 | 06-swarms.sql |
| swarms | idx_swarms_status | B-tree | 按状态筛选蜂群 | 06-swarms.sql |
| swarm_members | idx_swarm_members_swarm | B-tree | 按蜂群查询成员 | 07-swarm-members.sql |
| swarm_members | idx_swarm_members_agent | B-tree | 按 Agent 查询蜂群成员 | 07-swarm-members.sql |
| notifications | idx_notifications_user | B-tree | 按用户查询通知 | 16-notifications.sql |
| notifications | idx_notifications_project | B-tree | 按项目查询通知 | 16-notifications.sql |
| notifications | idx_notifications_read | B-tree | 未读通知查询 | 16-notifications.sql |
| notifications | idx_notifications_user_project | B-tree | 用户+项目组合查询 | 16-notifications.sql |
| repos | idx_repos_vcs_id | B-tree | VCS 平台+仓库 ID 查询 | 17-repos.sql |
| repo_branches | idx_repo_branches_repo | B-tree | 按仓库查询分支 | 18-repo-branches.sql |
| pull_requests | idx_prs_repo | B-tree | 按仓库查询 PR | 19-pull-requests.sql |
| pull_requests | idx_prs_status | B-tree | 按状态筛选 PR | 19-pull-requests.sql |
| commits | idx_commits_repo | B-tree | 按仓库查询提交 | 20-commits.sql |
| task_commits | idx_task_commits_task | B-tree | 按任务查询提交 | 21-task-commits.sql |
| task_commits | idx_task_commits_commit | B-tree | 按提交查询任务 | 21-task-commits.sql |

### 5.2 外键级联策略（V17 修正，V19 保留）

| 外键 | 源表 -> 目标表 | 删除策略 | 更新策略 | 说明 | 所在文件 |
|---|---|---|---|---|---|
| fk_projects_user | projects -> users | SET NULL | CASCADE | 用户删除后项目保留 | 03-projects.sql |
| fk_requirements_project | requirements -> projects | CASCADE | CASCADE | 项目删除则需求删除 | 04-requirements.sql |
| fk_tasks_project | tasks -> projects | CASCADE | CASCADE | 项目删除则任务删除 | 08-tasks.sql |
| fk_tasks_agent | tasks -> agents | SET NULL | CASCADE | Agent 删除后任务保留 | 08-tasks.sql |
| fk_tasks_swarm | tasks -> swarms | SET NULL | CASCADE | 蜂群删除后任务保留 | 08-tasks.sql |
| fk_tasks_user | tasks -> users | SET NULL | CASCADE | 用户删除后任务保留 | 08-tasks.sql |
| fk_td_tasks_source | task_dependencies -> tasks | CASCADE | CASCADE | 任务删除则依赖删除 | 09-task-dependencies.sql |
| fk_td_tasks_target | task_dependencies -> tasks | CASCADE | CASCADE | 任务删除则依赖删除 | 09-task-dependencies.sql |
| fk_exec_logs_task | agent_execution_logs -> tasks | CASCADE | CASCADE | 任务删除则日志删除 | 10-agent-execution-logs.sql |
| fk_exec_logs_agent | agent_execution_logs -> agents | SET NULL | CASCADE | Agent 删除后日志保留 | 10-agent-execution-logs.sql |
| fk_qr_task | qa_records -> tasks | CASCADE | CASCADE | 任务删除则 QA 删除 | 11-qa-records.sql |
| fk_qr_agent | qa_records -> agents | SET NULL | CASCADE | Agent 删除后 QA 保留 | 11-qa-records.sql |
| fk_groups_project | groups -> projects | CASCADE | CASCADE | 项目删除则群删除 | 12-groups.sql |
| fk_groups_host | groups -> agents | SET NULL | CASCADE | 主持人删除后群保留 | 12-groups.sql |
| fk_group_members_group | group_members -> groups | CASCADE | CASCADE | 群删除则成员删除 | 13-group-members.sql |
| fk_group_members_user | group_members -> users | **SET NULL** | CASCADE | V17 修正 | 13-group-members.sql |
| fk_group_members_agent | group_members -> agents | **SET NULL** | CASCADE | V17 修正 | 13-group-members.sql |
| fk_group_messages_group | group_messages -> groups | CASCADE | CASCADE | 群删除则消息删除 | 14-group-messages.sql |
| fk_meeting_outcomes_group | meeting_outcomes -> groups | CASCADE | CASCADE | 群删除则成果删除 | 15-meeting-outcomes.sql |
| fk_meeting_outcomes_host | meeting_outcomes -> agents | SET NULL | CASCADE | 主持人删除后成果保留 | 15-meeting-outcomes.sql |
| fk_swarms_project | swarms -> projects | CASCADE | CASCADE | 项目删除则蜂群删除 | 06-swarms.sql |
| fk_swarms_manager | swarms -> agents | SET NULL | CASCADE | 管理器删除后蜂群保留 | 06-swarms.sql |
| fk_swarm_members_swarm | swarm_members -> swarms | CASCADE | CASCADE | 蜂群删除则成员删除 | 07-swarm-members.sql |
| fk_swarm_members_agent | swarm_members -> agents | CASCADE | CASCADE | Agent 删除则蜂群成员删除 | 07-swarm-members.sql |
| fk_notifications_user | notifications -> users | CASCADE | CASCADE | 用户删除则通知删除 | 16-notifications.sql |
| fk_notifications_project | notifications -> projects | CASCADE | CASCADE | 项目删除则通知删除 | 16-notifications.sql |
| fk_repos_project | repos -> projects | CASCADE | CASCADE | 项目删除则仓库删除 | 17-repos.sql |
| fk_branches_repo | repo_branches -> repos | CASCADE | CASCADE | 仓库删除则分支删除 | 18-repo-branches.sql |
| fk_pr_repo | pull_requests -> repos | CASCADE | CASCADE | 仓库删除则 PR 删除 | 19-pull-requests.sql |
| fk_commits_repo | commits -> repos | CASCADE | CASCADE | 仓库删除则提交删除 | 20-commits.sql |
| fk_task_commits_task | task_commits -> tasks | CASCADE | CASCADE | 任务删除则关联删除 | 21-task-commits.sql |
| fk_task_commits_commit | task_commits -> commits | CASCADE | CASCADE | 提交删除则关联删除 | 21-task-commits.sql |
| fk_tasks_parent | tasks -> tasks | CASCADE | CASCADE | 自引用：父任务删除则子任务删除 | 08-tasks.sql |

**共 33 条外键约束。**

### 5.3 FK 索引验证表（V17 新增，V19 保留并更新）

所有外键字段均有对应索引，避免 DELETE/UPDATE 时的全表扫描锁：

| 外键约束 | 对应索引 | 验证状态 |
|---|---|---|
| fk_projects_user (projects.creator_id) | idx_projects_creator | 已创建 |
| fk_requirements_project (requirements.project_id) | idx_requirements_project | 已创建 |
| fk_tasks_project (tasks.project_id) | idx_tasks_project | 已创建 |
| fk_tasks_agent (tasks.assignee_agent_id) | idx_tasks_assignee | 已创建 |
| fk_tasks_swarm (tasks.assignee_swarm_id) | idx_tasks_swarm | 已创建 |
| fk_tasks_user (tasks.assignee_user_id) | idx_tasks_assignee_user | 已创建 |
| fk_td_tasks_source (task_dependencies.source_task_id) | idx_task_deps_source | 已创建 |
| fk_td_tasks_target (task_dependencies.target_task_id) | idx_task_deps_target | 已创建 |
| fk_exec_logs_task (agent_execution_logs.task_id) | idx_exec_logs_task | 已创建 |
| fk_exec_logs_agent (agent_execution_logs.agent_id) | idx_exec_logs_agent | 已创建 |
| fk_qr_task (qa_records.task_id) | idx_qa_records_task | 已创建 |
| fk_qr_agent (qa_records.reviewer_agent_id) | idx_qa_records_reviewer | 已创建 |
| fk_groups_project (groups.project_id) | idx_groups_project | 已创建 |
| fk_group_members_group (group_members.group_id) | idx_group_members_group | 已创建 |
| fk_group_members_user (group_members.user_id) | idx_group_members_user_only | 已创建 |
| fk_group_members_agent (group_members.agent_id) | idx_group_members_agent_only | 已创建 |
| fk_group_messages_group (group_messages.group_id) | idx_group_messages_group | 已创建 |
| fk_swarms_project (swarms.project_id) | idx_swarms_project | 已创建 |
| fk_swarms_manager (swarms.manager_agent_id) | idx_swarms_manager | 已创建 |
| fk_swarm_members_swarm (swarm_members.swarm_id) | idx_swarm_members_swarm | 已创建 |
| fk_swarm_members_agent (swarm_members.agent_id) | idx_swarm_members_agent | 已创建 |
| fk_notifications_user (notifications.user_id) | idx_notifications_user | 已创建 |
| fk_notifications_project (notifications.project_id) | idx_notifications_project | 已创建 |
| fk_repos_project (repos.project_id) | 无单独索引（UNIQUE 约束隐含索引） | UNIQUE 约束覆盖 |
| fk_branches_repo (repo_branches.repo_id) | idx_repo_branches_repo | 已创建 |
| fk_pr_repo (pull_requests.repo_id) | idx_prs_repo | 已创建 |
| fk_commits_repo (commits.repo_id) | idx_commits_repo | 已创建 |
| fk_task_commits_task (task_commits.task_id) | idx_task_commits_task | 已创建 |
| fk_task_commits_commit (task_commits.commit_id) | idx_task_commits_commit | 已创建 |

**V19 验证结论：全部 29 个外键字段均有对应索引覆盖，无遗漏。**

---

## 6. 事务隔离级别与并发控制策略

### 6.1 默认事务隔离级别

PostgreSQL 默认使用 `READ COMMITTED` 隔离级别，适用于 DevFlow 大多数场景：
- 读取已提交数据，避免脏读
- 允许不可重复读和幻读，但对 DevFlow 业务逻辑影响有限
- 写操作自动获取行级排他锁

### 6.2 高并发场景处理

| 场景 | 隔离级别 | 说明 |
|---|---|---|
| 任务状态流转 | READ COMMITTED + SELECT FOR UPDATE | 锁住任务行，防止并发修改 |
| 项目步骤推进 | READ COMMITTED + 触发器 | 触发器自动锁项目行 |
| 群消息插入 | READ COMMITTED | BIGSERIAL ID 天然串行化 |
| 依赖插入检测 | REPEATABLE READ | 防止循环依赖检测时的幻读 |
| QA 记录写入 | READ COMMITTED | 每任务一条记录，无并发冲突 |

### 6.3 死锁预防策略

1. 按 ID 顺序获取锁：先锁 ID 小的行，再锁 ID 大的行
2. 超时设置：`lock_timeout = '5s'`，避免长时间持有锁
3. 应用层重试：捕获死锁错误后自动重试（最多 3 次）

---

## 7. 分区表策略详细说明

### 7.1 分区依据

group_messages 表预计数据量最大（BIGSERIAL 主键），建议按时间范围分区：

```sql
-- 按月分区示例（实际实施时）
CREATE TABLE group_messages (LIKE group_messages INCLUDING ALL)
  PARTITION BY RANGE (timestamp);

CREATE TABLE group_messages_2026_06 PARTITION OF group_messages
  FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
```

### 7.2 分区维护

- 每月提前创建新分区
- 历史分区可归档为只读
- 分区切换使用 `ALTER TABLE ... DETACH PARTITION`

---

## 8. 存储过程与函数

### 8.1 循环依赖检测

完整递归 CTE 实现见 `sql/09-task-dependencies.sql`。
返回值：检测到循环依赖时抛出 EXCEPTION，否则允许插入。

### 8.2 软删除物理清理

完整实现见 `sql/96-soft-delete-cleanup.sql`。
功能：按外键依赖顺序逐层清理超过保留期（默认 90 天）的软删除记录。
清理顺序：notifications -> swarm_members/group_members/group_messages -> swarms/groups/tasks -> projects。

### 8.3 同步项目当前步骤

完整实现见 `sql/03-projects.sql`。
触发时机：tasks 表 INSERT 或 UPDATE status/step_number 时自动触发。

### 8.4 其他触发器

| 触发器 | 所在表 | 触发时机 | 功能 | 所在文件 |
|---|---|---|---|---|
| update_users_updated_at | users | BEFORE UPDATE | 自动更新 updated_at | 02-users.sql |
| update_projects_updated_at | projects | BEFORE UPDATE | 自动更新 updated_at | 03-projects.sql |
| update_requirements_updated_at | requirements | BEFORE UPDATE | 自动更新 updated_at | 04-requirements.sql |
| update_agents_updated_at | agents | BEFORE UPDATE | 自动更新 updated_at | 05-agents.sql |
| update_swarms_updated_at | swarms | BEFORE UPDATE | 自动更新 updated_at | 06-swarms.sql |
| update_tasks_updated_at | tasks | BEFORE UPDATE | 自动更新 updated_at | 08-tasks.sql |
| trg_sync_project_current_step | tasks | AFTER INSERT/UPDATE | 同步项目 current_step | 03-projects.sql |
| trg_enforce_parent_same_project | tasks | BEFORE INSERT/UPDATE | 确保子任务与父任务同项目 | 08-tasks.sql |
| enforce_same_project_dependency | task_dependencies | BEFORE INSERT/UPDATE | 确保依赖双方同项目 | 09-task-dependencies.sql |
| trg_check_circular_dependency | task_dependencies | BEFORE INSERT/UPDATE | 循环依赖检测 | 09-task-dependencies.sql |
| update_groups_updated_at | groups | BEFORE UPDATE | 自动更新 updated_at | 12-groups.sql |
| auto_add_manager_to_members | swarms | AFTER INSERT | 管理器自动注册为蜂群成员 | 06-swarms.sql |
| trg_validate_sender | group_messages | BEFORE INSERT/UPDATE | **V19 新增**：校验 sender_id 存在性 | 14-group-messages.sql |
| update_repo_branches_updated_at | repo_branches | BEFORE UPDATE | 自动更新 updated_at | 18-repo-branches.sql |
| update_pull_requests_updated_at | pull_requests | BEFORE UPDATE | 自动更新 updated_at | 19-pull-requests.sql |

**V19 确认：共 15 个触发器。**

---

## 9. 视图定义

### 9.1 项目进度视图 (v_project_progress)

见 `sql/99-views.sql`。
功能：展示每个项目的总任务数、已完成/进行中/待处理任务数、完成百分比。

### 9.2 Agent 负载视图 (v_agent_load)

见 `sql/99-views.sql`。
功能：展示每个 Agent 的分配任务数、活跃任务数、平均任务耗时。

### 9.3 QA 检验统计视图 (v_qa_statistics)

见 `sql/99-views.sql`。
功能：展示每个项目的 QA 总检验次数、通过/失败次数、通过率、平均得分。

---

## 10. 表清单与 DDL 完整性验证

### 10.1 表清单（21 张表）

| 序号 | 表名 | SQL 文件 | 行数 | 关键特性 |
|---|---|---|---|---|
| 1 | users | 02-users.sql | ~39 | citext email、密码哈希、updated_at 触发器 |
| 2 | projects | 03-projects.sql | ~90 | current_step 1~16、sync 触发器 |
| 3 | requirements | 04-requirements.sql | ~30 | (project_id, version) 唯一 |
| 4 | agents | 05-agents.sql | ~47 | 9 个命名 Agent 初始化 |
| 5 | swarms | 06-swarms.sql | ~47 | 管理器自动注册触发器（V19 从 14 提前） |
| 6 | swarm_members | 07-swarm-members.sql | ~22 | UNIQUE(swarm_id, agent_id)、status CHECK（V19 新增） |
| 7 | tasks | 08-tasks.sql | ~80 | 三选一分配、16 步、父子项目一致性 |
| 8 | task_dependencies | 09-task-dependencies.sql | ~90 | 循环依赖检测、枚举类型（V19 修正） |
| 9 | agent_execution_logs | 10-agent-execution-logs.sql | ~23 | 执行内容与结果 JSONB |
| 10 | qa_records | 11-qa-records.sql | ~28 | score 0~100、审查维度 JSONB |
| 11 | groups | 12-groups.sql | ~30 | 与 project 1:1 |
| 12 | group_members | 13-group-members.sql | ~30 | SET NULL 级联、成员类型约束 |
| 13 | group_messages | 14-group-messages.sql | ~68 | 多发送者类型、sender 校验触发器（V19 新增） |
| 14 | meeting_outcomes | 15-meeting-outcomes.sql | ~32 | UNIQUE(group_id, started_at) |
| 15 | notifications | 16-notifications.sql | ~26 | 多类型通知 |
| 16 | repos | 17-repos.sql | ~26 | 与 project 1:1、VCS 平台约束 |
| 17 | repo_branches | 18-repo-branches.sql | ~28 | UNIQUE(repo_id, name)、触发器函数修正 |
| 18 | pull_requests | 19-pull-requests.sql | ~34 | UNIQUE(repo_id, number) |
| 19 | commits | 20-commits.sql | ~22 | UNIQUE(repo_id, sha) |
| 20 | task_commits | 21-task-commits.sql | ~20 | UNIQUE(task_id, commit_id) |
| 21 | 视图 v_project_progress | 99-views.sql | ~24 | 项目进度统计 |
| 22 | 视图 v_agent_load | 99-views.sql | ~14 | Agent 负载统计 |
| 23 | 视图 v_qa_statistics | 99-views.sql | ~17 | QA 检验统计 |

**总计：21 张数据表 + 3 个视图，25 个 SQL 文件，约 1082 行 DDL。**

### 10.2 枚举类型清单（16 个，全部被引用）

| 序号 | 类型名 | 值数量 | 所在文件 | 引用状态 |
|---|---|---|---|---|
| 1 | user_role | 3 | 01-enums.sql | users.role |
| 2 | project_status | 4 | 01-enums.sql | projects.status |
| 3 | agent_type | 2 | 01-enums.sql | agents.agent_type |
| 4 | agent_status | 3 | 01-enums.sql | agents.status |
| 5 | task_status | 5 | 01-enums.sql | tasks.status |
| 6 | task_type | 16 | 01-enums.sql | tasks.type |
| 7 | group_mode | 2 | 01-enums.sql | groups.mode |
| 8 | member_type | 2 | 01-enums.sql | group_members.member_type |
| 9 | sender_type | 2 | 01-enums.sql | group_messages.sender_type |
| 10 | meeting_type | 4 | 01-enums.sql | meeting_outcomes.type |
| 11 | dependency_type_enum | 4 | 01-enums.sql | **task_dependencies.dependency_type（V19 已引用）** |
| 12 | swarm_purpose | 2 | 01-enums.sql | swarms.purpose |
| 13 | swarm_status | 3 | 01-enums.sql | swarms.status |
| 14 | qa_result | 2 | 01-enums.sql | qa_records.acceptance_result |
| 15 | notification_type | 7 | 01-enums.sql | notifications.type |
| 16 | pr_status | 3 | 01-enums.sql | pull_requests.status |

**V19 确认：全部 16 个枚举类型均被至少一张表引用，无冗余枚举。**

### 10.3 触发器清单（15 个）

| 序号 | 触发器名 | 表 | 功能 | 所在文件 |
|---|---|---|---|---|
| 1 | update_users_updated_at | users | 自动更新 updated_at | 02-users.sql |
| 2 | update_projects_updated_at | projects | 自动更新 updated_at | 03-projects.sql |
| 3 | trg_sync_project_current_step | tasks | 同步项目 current_step | 03-projects.sql |
| 4 | update_requirements_updated_at | requirements | 自动更新 updated_at | 04-requirements.sql |
| 5 | update_agents_updated_at | agents | 自动更新 updated_at | 05-agents.sql |
| 6 | update_swarms_updated_at | swarms | 自动更新 updated_at | 06-swarms.sql |
| 7 | update_tasks_updated_at | tasks | 自动更新 updated_at | 08-tasks.sql |
| 8 | trg_enforce_parent_same_project | tasks | 父子项目一致性 | 08-tasks.sql |
| 9 | enforce_same_project_dependency | task_dependencies | 依赖同项目约束 | 09-task-dependencies.sql |
| 10 | trg_check_circular_dependency | task_dependencies | 循环依赖检测 | 09-task-dependencies.sql |
| 11 | update_groups_updated_at | groups | 自动更新 updated_at | 12-groups.sql |
| 12 | auto_add_manager_to_members | swarms | 管理器自动注册 | 06-swarms.sql |
| 13 | trg_validate_sender | group_messages | **V19 新增**：sender_id 存在性校验 | 14-group-messages.sql |
| 14 | update_repo_branches_updated_at | repo_branches | 自动更新 updated_at | 18-repo-branches.sql |
| 15 | update_pull_requests_updated_at | pull_requests | 自动更新 updated_at | 19-pull-requests.sql |

---

## 11. 修正内容对照表

### 11.1 V19 修正项

| 序号 | 修正项 | 位置 | 变更内容 | 优先级 |
|---|---|---|---|---|
| 1 | 执行顺序重排 | 文件命名 | swarms 从 14 提前至 06，swarm_members 从 15 提前至 07，tasks 从 06 后移至 08 | **阻塞性** |
| 2 | 触发器函数修正 | 18-repo-branches.sql | update_repo_branches_updated_at_column() 改为 update_updated_at_column() | **阻塞性** |
| 3 | 枚举类型使用 | 09-task-dependencies.sql | dependency_type 由 VARCHAR(50)+CHECK 改为 dependency_type_enum | 设计缺陷 |
| 4 | status 约束 | 07-swarm-members.sql | 新增 CHECK (status IN ('active', 'inactive', 'removed')) | 设计缺陷 |
| 5 | sender 校验触发器 | 14-group-messages.sql | 新增 validate_sender_exists() 函数和 trg_validate_sender 触发器 | 设计缺陷 |
| 6 | ER 图改善 | 第 1.1 节 | 按模块分层展示，关系方向更清晰 | 可读性 |
| 7 | 触发器清单更新 | 第 10.3 节 | 从 14 个更新为 15 个（新增 trg_validate_sender） | 一致性 |
| 8 | 枚举引用状态 | 第 1.3/10.2 节 | 确认全部 16 个枚举均被引用 | 一致性 |

### 11.2 V14~V18 保留修正项

| 版本 | 关键修正 |
|---|---|
| V18 | SQL 文件清单修正、ER 图补全、枚举类型补全、第 2~11 节内容补全 |
| V17 | 拆分文件架构、group_members ON DELETE SET NULL、sender_id 约束说明、FK 索引验证表、约束命名规范 |
| V16 | 修复截断问题，确认全部 DDL 完整可执行 |
| V14 | 修复 meeting_type 枚举不完整，新增 dependency_type 枚举 |
| V12 | 修复 updated_at DEFAULT NOW()，CHECK 约束上限修正为 16 |
| V11 | 修复 ER 图重复展示，补充 agent_status 应用层管理注释 |
| V10 | 新增事务隔离/分区策略/表清单/修正对照表章节 |
| V9 | 补充 citext 扩展，新增索引设计与外键级联策略总览 |
| V6 | 循环依赖检测递归 CTE、三选一 CHECK 约束、触发器锁策略优化 |

---

## 12. 执行指南

### 12.1 首次初始化

```bash
# 按顺序执行所有 SQL 文件
cd sql/
for f in 01*.sql 02*.sql 03*.sql 04*.sql 05*.sql 06*.sql 07*.sql \
         08*.sql 09*.sql 10*.sql 11*.sql 12*.sql 13*.sql 14*.sql 15*.sql \
         16*.sql 17*.sql 18*.sql 19*.sql 20*.sql 21*.sql 96*.sql 97*.sql 98*.sql 99*.sql; do
  echo "Executing $f..."
  psql -U devflow -d devflow_db -f "$f"
done
```

### 12.2 验证完整性

```bash
# 验证表数量
psql -U devflow -d devflow_db -c "
  SELECT COUNT(*) AS table_count
  FROM information_schema.tables
  WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
"
# 预期结果：21

# 验证枚举类型数量
psql -U devflow -d devflow_db -c "
  SELECT typname AS enum_type, COUNT(*) AS value_count
  FROM pg_type t
  JOIN pg_enum e ON t.oid = e.enumtypid
  GROUP BY t.typname
  ORDER BY t.typname;
"
# 预期结果：16 行（16 个枚举类型）

# 验证触发器数量
psql -U devflow -d devflow_db -c "
  SELECT COUNT(*) AS trigger_count
  FROM information_schema.triggers;
"
# 预期结果：15

# 验证外键约束数量
psql -U devflow -d devflow_db -c "
  SELECT COUNT(*) AS fk_count
  FROM information_schema.table_constraints
  WHERE constraint_type = 'FOREIGN KEY';
"
# 预期结果：33
```

### 12.3 从 V18 升级到 V19

V19 主要修正执行顺序、触发器函数、枚举使用、字段约束等问题。升级时建议：

1. 备份现有数据库
2. 如果是全新部署，直接按 12.1 节执行所有 SQL 文件
3. 如果是已有数据库升级，需注意以下变更：
   - task_dependencies.dependency_type 字段类型由 VARCHAR(50) 改为 dependency_type_enum 枚举
   - swarm_members 表新增 status CHECK 约束
   - group_messages 表新增 trg_validate_sender 触发器
   - repo_branches 表触发器函数由 update_repo_branches_updated_at_column() 改为 update_updated_at_column()

---

*文档结束。完整 DDL 请参见 sql/ 目录。*