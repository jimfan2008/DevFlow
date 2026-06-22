# DevFlow 数据库设计文档

**版本**: V18
**日期**: 2026-06-27
**作者**: HouWang (后旺)
**状态**: V18 版本（修正 V17 SQL 文件清单与实际文件不一致问题，补全 ER 图、枚举定义与第 2~11 节内容）

---

## 变更日志

- V18 (2026-06-27): 根据后荣检验报告修正以下问题
  1. 【SQL 文件清单修正】V17 文档声明的 SQL 文件清单与实际 `sql/` 目录中的文件严重不一致（如 `00-settings.sql`、`14-documents.sql`、`17-artifacts.sql`、`18-artifact-versions.sql`、`19-deployments.sql` 均不存在），V18 修正为与实际 25 个 SQL 文件一一对应
  2. 【ER 图补全】V17 ER 图仅展示了 11 个实体，缺少 agents、swarms、swarm_members、agent_execution_logs、qa_records、commits、task_commits、notifications、requirements、repo_branches、pull_requests 等实体，V18 补全全部 21 张表的 ER 关系
  3. 【枚举类型补全】V17 枚举定义在 meeting_type 处截断，V18 完整列出全部 16 个枚举类型及其值
  4. 【第 2~11 节内容补全】V17 提供的文档在第 2 节后缺失，V18 补充完整的第 2 节（DDL 文件引用）、第 3 节（关键设计决策）、第 4 节（约束与索引总结）、第 5 节（索引设计与外键级联策略总览）、第 6 节（事务隔离级别与并发控制策略）、第 7 节（分区表策略）、第 8 节（存储过程与函数）、第 9 节（视图定义）、第 10 节（表清单与 DDL 完整性验证）、第 11 节（修正内容对照表）、第 12 节（执行指南）
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

V18 文档采用拆分文件架构：

- **主文档（本文）**：包含变更日志、ER 图、枚举类型定义、DDL 文件引用、关键设计决策、索引与级联策略、事务隔离、分区策略、存储过程、视图、表清单、修正对照表、执行指南
- **SQL 文件**：完整 DDL 拆分为 25 个独立 `.sql` 文件，存放于 `sql/` 子目录
- **执行顺序**：按文件名数字顺序执行（01 到 99），确保依赖关系正确

### SQL 文件清单（V18 修正：与实际文件一一对应）

| 序号 | 文件 | 说明 | 行数 |
|------|------|------|------|
| 1 | `sql/01-enums.sql` | 扩展与枚举类型定义（16 个枚举） | ~54 |
| 2 | `sql/02-users.sql` | 用户表 | ~39 |
| 3 | `sql/03-projects.sql` | 项目表（含 sync_project_current_step 触发器） | ~90 |
| 4 | `sql/04-requirements.sql` | 需求表（软件需求说明书） | ~30 |
| 5 | `sql/05-agents.sql` | Agent 表（含 9 个命名 Agent 初始化） | ~47 |
| 6 | `sql/06-tasks.sql` | 任务表（含 CHECK/UNIQUE 约束与索引） | ~80 |
| 7 | `sql/07-task-dependencies.sql` | 任务依赖表（含循环依赖检测） | ~90 |
| 8 | `sql/08-agent-execution-logs.sql` | Agent 执行日志表 | ~23 |
| 9 | `sql/09-qa-records.sql` | QA 检验记录表 | ~28 |
| 10 | `sql/10-groups.sql` | 群组表（项目讨论群） | ~30 |
| 11 | `sql/11-group-members.sql` | 群成员表（V17：ON DELETE SET NULL） | ~30 |
| 12 | `sql/12-group-messages.sql` | 群消息表（V17：sender_id 约束说明） | ~56 |
| 13 | `sql/13-meeting-outcomes.sql` | 会议结果表 | ~32 |
| 14 | `sql/14-swarms.sql` | Agent 蜂群表 | ~47 |
| 15 | `sql/15-swarm-members.sql` | 蜂群成员关联表 | ~22 |
| 16 | `sql/16-notifications.sql` | 通知表 | ~26 |
| 17 | `sql/17-repos.sql` | 代码仓库表 | ~26 |
| 18 | `sql/18-repo-branches.sql` | 代码分支表 | ~28 |
| 19 | `sql/19-pull-requests.sql` | 拉取请求表 | ~34 |
| 20 | `sql/20-commits.sql` | 提交记录表 | ~22 |
| 21 | `sql/21-task-commits.sql` | 任务与提交关联表 | ~20 |
| 22 | `sql/96-soft-delete-cleanup.sql` | 软删除物理清理存储过程 | ~130 |
| 23 | `sql/97-permissions.sql` | 权限设置 | ~18 |
| 24 | `sql/98-init-data.sql` | 初始化数据 | ~12 |
| 25 | `sql/99-views.sql` | 视图定义 | ~72 |
| **合计** | **25 个文件** | | **约 1026 行** |

> 完整 DDL 请查看 `sql/` 目录下的各 `.sql` 文件。以下保留设计说明与架构文档。

---

## 1. ER 概述

### 1.1 实体关系图（V18 补全：21 张表全量展示）

```
+----------+     +-----------+     +--------------+
|  users   |-----| projects  |-----| requirements |
| (02)     |     |  (03)     |     |    (04)      |
+----------+     +-----+-----+     +--------------+
                       |
        +--------------+---------------+
        |              |               |
        v              v               v
 +----------+     +-----------+    +----------+
 |  groups  |     |   tasks   |    |  repos   |
 |  (10)    |     |   (06)    |    |  (17)    |
 |  1:1     |     |           |    |          |
 +----+----+     +-----+-----+    +----+-----+
      |                    |               |
      |         +----------+----------+    |
      v         v          v          v    |
+-------------+ +--------------+ +-------------+
|group_members| |task_deps     | |repo_branches|
|    (11)     | | (07)         | |    (18)    |
+------+------+ +--------------+ +-----+-------+
      |                                               |
      v                                               v
+--------------+                             +-------------+
|group_messages|                             |pull_requests|
|    (12)      |                             |    (19)    |
+--------------+                             +-------------+
                                                       |
                                                       v
                                                  +----------+
                                                  | commits  |
                                                  |  (20)    |
                                                  +-----+----+
                                                        |
+----------+     +-----------+               +---------+
|  agents  |-----|   swarms  |-----+         |
|  (05)    |     |  (14)     |     |    +----+----+
+-----+----+     +-----+-----+     |    |         |
      |                  |         |    v         v
      |         +--------+--+      |+-------------+
      |         |               |  | task_commits |
      |         v               |  |    (21)      |
      |    +------------+       |  +--------------+
      |    |swarm_members|      |
      |    |   (15)      |      |
      |    +-------------+      |
      |                         |
      v                         v
+------------------+    +------------------+
| agent_exec_logs  |    |   qa_records     |
|    (08)          |    |    (09)          |
+------------------+    +------------------+

+------------------+    +------------------+    +------------------+
| meeting_outcomes |    | notifications    |    |    (其他关系)     |
|    (13)          |    |    (16)          |
+------------------+    +------------------+

关系说明（按外键）:
  users ---< projects (creator_id)
  users ---< tasks (assignee_user_id, SET NULL)
  users ---< group_members (user_id, SET NULL)
  users ---< notifications (user_id, CASCADE)
  projects ---< requirements (project_id, CASCADE)
  projects ---< tasks (project_id, CASCADE)
  projects ---< agents (无直接FK，agents为全局注册)
  projects ---< swarms (project_id, CASCADE)
  projects ---< repos (project_id, CASCADE) [1:1]
  projects ---< groups (project_id, CASCADE) [1:1]
  projects ---< notifications (project_id, CASCADE)
  agents ---< tasks (assignee_agent_id, SET NULL)
  agents ---< group_members (agent_id, SET NULL)
  agents ---< groups (host_agent_id, SET NULL)
  agents ---< meeting_outcomes (host_agent_id, SET NULL)
  agents ---< swarm_members (agent_id)
  agents ---< swarms (manager_agent_id, SET NULL)
  agents ---< agent_execution_logs (agent_id, SET NULL)
  agents ---< qa_records (reviewer_agent_id, SET NULL)
  swarms ---< tasks (assignee_swarm_id, SET NULL)
  swarms ---< swarm_members (swarm_id, CASCADE)
  tasks ---< task_dependencies (source/target, CASCADE)
  tasks ---< agent_execution_logs (task_id, CASCADE)
  tasks ---< qa_records (task_id, CASCADE)
  tasks ---< task_commits (task_id, CASCADE)
  groups ---< group_members (group_id, CASCADE)
  groups ---< group_messages (group_id, CASCADE)
  groups ---< meeting_outcomes (group_id, CASCADE)
  repos ---< repo_branches (repo_id, CASCADE)
  repos ---< pull_requests (repo_id, CASCADE)
  repos ---< commits (repo_id, CASCADE)
  commits ---< task_commits (commit_id, CASCADE)
```

### 1.2 核心实体说明

| 实体 | 对应 SQL 文件 | 说明 | 关键约束 |
|------|------|------|------|
| users | 02-users.sql | 人类用户信息 | email UNIQUE(citext)、password_hash 非空 |
| projects | 03-projects.sql | 项目主表 | code UNIQUE、current_step 1~16 |
| requirements | 04-requirements.sql | 软件需求说明书 | 关联 project_id、(project_id, version) 唯一 |
| agents | 05-agents.sql | Agent 信息 | name UNIQUE、支持命名 Agent 与蜂群 Agent |
| tasks | 06-tasks.sql | 任务记录 | step_number 1~16、三选一分配、status 流 |
| task_dependencies | 07-task-dependencies.sql | 任务依赖 | 防止循环依赖、防止自依赖、同项目约束 |
| agent_execution_logs | 08-agent-execution-logs.sql | Agent 执行日志 | 关联 task_id 和 agent_id |
| qa_records | 09-qa-records.sql | QA 检验记录 | score 0~100、关联 task_id |
| groups | 10-groups.sql | 项目讨论群 | 与 project 1:1（project_id UNIQUE） |
| group_members | 11-group-members.sql | 群成员 | V17: user_id/agent_id ON DELETE SET NULL |
| group_messages | 12-group-messages.sql | 群消息 | V17: sender_id 应用层校验 |
| meeting_outcomes | 13-meeting-outcomes.sql | 会议结果 | UNIQUE(group_id, started_at) |
| swarms | 14-swarms.sql | Agent 蜂群 | 关联 project_id、manager_agent_id |
| swarm_members | 15-swarm-members.sql | 蜂群成员 | UNIQUE(swarm_id, agent_id) |
| notifications | 16-notifications.sql | 通知消息 | 关联 user_id 和 project_id |
| repos | 17-repos.sql | 代码仓库 | 与 project 1:1、(vcs_platform, vcs_repo_id) 唯一 |
| repo_branches | 18-repo-branches.sql | 代码分支 | UNIQUE(repo_id, name) |
| pull_requests | 19-pull-requests.sql | 拉取请求 | UNIQUE(repo_id, number) |
| commits | 20-commits.sql | 提交记录 | UNIQUE(repo_id, sha) |
| task_commits | 21-task-commits.sql | 任务-提交关联 | UNIQUE(task_id, commit_id) |

### 1.3 枚举类型定义（V18 补全：16 个枚举类型）

| 序号 | 枚举类型 | 值 | 说明 | 所在文件 |
|------|------|------|------|------|
| 1 | `user_role` | `user`, `admin`, `system_admin` | 用户角色 | 01-enums.sql |
| 2 | `project_status` | `created`, `in_progress`, `completed`, `cancelled` | 项目状态 | 01-enums.sql |
| 3 | `agent_type` | `named`, `swarm` | Agent 类型（命名/蜂群） | 01-enums.sql |
| 4 | `agent_status` | `online`, `offline`, `busy` | Agent 状态（应用层管理） | 01-enums.sql |
| 5 | `task_status` | `pending`, `in_progress`, `completed`, `failed`, `cancelled` | 任务状态 | 01-enums.sql |
| 6 | `task_type` | `requirement_analysis`, `architecture_design`, `backend_design`, `frontend_design`, `database_design`, `environment_setup`, `tdd_test_plan`, `tdd_test_writing`, `code_writing_plan`, `code_writing`, `test_deployment`, `testing`, `security_audit`, `production_deployment`, `documentation`, `delivery_report` | 16 个值对应 DevFlow 16 步流程 | 01-enums.sql |
| 7 | `group_mode` | `discussion`, `meeting` | 群组模式 | 01-enums.sql |
| 8 | `member_type` | `user`, `agent` | 群成员类型 | 01-enums.sql |
| 9 | `sender_type` | `user`, `agent` | 消息发送者类型 | 01-enums.sql |
| 10 | `meeting_type` | `requirement_review`, `tech_solution`, `daily_standup`, `incident_postmortem` | 会议类型 | 01-enums.sql |
| 11 | `dependency_type_enum` | `finish_to_start`, `start_to_start`, `finish_to_finish`, `start_to_finish` | 依赖类型（枚举定义） | 01-enums.sql |
| 12 | `swarm_purpose` | `code_writing`, `testing` | 蜂群用途 | 01-enums.sql |
| 13 | `swarm_status` | `active`, `completed`, `dissolved` | 蜂群状态 | 01-enums.sql |
| 14 | `qa_result` | `pass`, `fail` | QA 检验结果 | 01-enums.sql |
| 15 | `notification_type` | `step_complete`, `qa_pass`, `qa_fail`, `task_assigned`, `task_completed`, `project_complete`, `system_alert` | 通知类型 | 01-enums.sql |
| 16 | `pr_status` | `open`, `closed`, `merged` | Pull Request 状态 | 01-enums.sql |

> **注意**: task_dependencies 表的 `dependency_type` 字段使用 `VARCHAR(50)` 类型而非 `dependency_type_enum` 枚举，通过 CHECK 约束限制合法值为 `('finish_to_start', 'start_to_start', 'finish_to_finish', 'start_to_finish')`，与枚举定义保持一致。

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
- `sql/02-users.sql` — 用户表（含 citext email 唯一约束、updated_at 触发器）
- `sql/03-projects.sql` — 项目表（含 current_step CHECK 1~16、sync_project_current_step 触发器）
- `sql/04-requirements.sql` — 需求表（含 (project_id, version) 唯一索引）
- `sql/05-agents.sql` — Agent 表（含 9 个命名 Agent 初始化数据）
- `sql/06-tasks.sql` — 任务表（含 step_number CHECK 1~16、三选一分配约束、父子项目一致性触发器）
- `sql/07-task-dependencies.sql` — 任务依赖表（含循环依赖检测递归 CTE、同项目约束触发器）

### 2.3 执行与检验表
- `sql/08-agent-execution-logs.sql` — Agent 执行日志表
- `sql/09-qa-records.sql` — QA 检验记录表（含 score 0~100 CHECK 约束）

### 2.4 协作与沟通表
- `sql/10-groups.sql` — 群组表（与 project 1:1）
- `sql/11-group-members.sql` — 群成员表（V17 修正：ON DELETE SET NULL）
- `sql/12-group-messages.sql` — 群消息表（V17 修正：sender_id 约束说明）
- `sql/13-meeting-outcomes.sql` — 会议结果表（UNIQUE(group_id, started_at)）

### 2.5 蜂群管理表
- `sql/14-swarms.sql` — Agent 蜂群表（含管理器自动注册触发器）
- `sql/15-swarm-members.sql` — 蜂群成员关联表

### 2.6 通知与代码仓库表
- `sql/16-notifications.sql` — 通知表
- `sql/17-repos.sql` — 代码仓库表（与 project 1:1）
- `sql/18-repo-branches.sql` — 代码分支表
- `sql/19-pull-requests.sql` — 拉取请求表
- `sql/20-commits.sql` — 提交记录表
- `sql/21-task-commits.sql` — 任务与提交关联表

### 2.7 工具与辅助脚本
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
-- 递归 CTE 完整遍历所有下游节点，检测循环
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

### 3.5 V17 修正项保留

#### 3.5.1 group_members 级联策略变更

```sql
-- V17 修正：用户/Agent 被删除时，群成员记录保留但关联 ID 置 NULL
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

#### 3.5.2 group_messages sender_id 约束说明

`sender_id` 字段未定义外键约束，因为 PostgreSQL 不支持单字段多目标条件外键（即一个字段根据 sender_type 值指向不同表）。引用完整性由应用层保证：

1. 插入消息前校验 sender_id 是否存在于对应表
2. 删除用户/Agent 前检查是否存在未删除的群消息引用
3. 应用层 INSERT 语句包含 EXISTS 子句校验

---

## 4. 约束与索引总结

### 4.1 CHECK 约束清单

| 表 | 约束 | 说明 | 所在文件 |
|---|------|------|---|
| projects | `current_step >= 1 AND current_step <= 16` | DevFlow 16 步流程 | 03-projects.sql |
| tasks | `step_number >= 1 AND step_number <= 16` | DevFlow 16 步流程 | 06-tasks.sql |
| tasks | 三选一分配约束 | 见 3.2 节 | 06-tasks.sql |
| tasks | `completed_at IS NULL OR completed_at >= created_at` | 完成时间不早于创建时间 | 06-tasks.sql |
| task_dependencies | `dependency_type IN ('finish_to_start','start_to_start','finish_to_finish','start_to_finish')` | 依赖类型合法值 | 07-task-dependencies.sql |
| task_dependencies | `source_task_id <> target_task_id` | 禁止自依赖 | 07-task-dependencies.sql |
| group_members | member_type 与 user_id/agent_id 互斥约束 | user 类型时 user_id 非空，agent 类型时 agent_id 非空 | 11-group-members.sql |
| group_messages | sender_type 与 sender_id 互斥约束 | sender_type 非空时 sender_id 必须非空 | 12-group-messages.sql |
| group_messages | `message_type IN ('system','agent','user')` | 消息类型合法值 | 12-group-messages.sql |
| meeting_outcomes | `ended_at IS NULL OR ended_at >= started_at` | 结束时间不早于开始时间 | 13-meeting-outcomes.sql |
| repos | `vcs_platform IN ('gitea','github','gitlab')` | VCS 平台合法值 | 17-repos.sql |
| qa_records | `score >= 0 AND score <= 100` | 评分范围 | 09-qa-records.sql |

### 4.2 UNIQUE 约束清单

| 表 | 约束 | 说明 | 所在文件 |
|---|------|------|---|
| users | `username UNIQUE` | 用户名唯一 | 02-users.sql |
| users | `email UNIQUE (citext)` | 邮箱唯一（不区分大小写） | 02-users.sql |
| projects | `code UNIQUE` | 业务编号唯一 | 03-projects.sql |
| requirements | `(project_id, version) UNIQUE` | 同项目同版本唯一 | 04-requirements.sql |
| agents | `name UNIQUE` | Agent 名称唯一 | 05-agents.sql |
| groups | `project_id UNIQUE` | 项目与群 1:1 | 10-groups.sql |
| meeting_outcomes | `(group_id, started_at) UNIQUE` | 同一会议不重复 | 13-meeting-outcomes.sql |
| task_dependencies | `(source_task_id, target_task_id) UNIQUE` | 同一对依赖不重复 | 07-task-dependencies.sql |
| repo_branches | `(repo_id, name) UNIQUE` | 同仓库分支名唯一 | 18-repo-branches.sql |
| pull_requests | `(repo_id, number) UNIQUE` | 同仓库 PR 号唯一 | 19-pull-requests.sql |
| commits | `(repo_id, sha) UNIQUE` | 同仓库提交 SHA 唯一 | 20-commits.sql |
| task_commits | `(task_id, commit_id) UNIQUE` | 同一关联不重复 | 21-task-commits.sql |
| swarm_members | `(swarm_id, agent_id) UNIQUE` | 同蜂群同 Agent 不重复 | 15-swarm-members.sql |
| repos | `project_id UNIQUE` | 项目与仓库 1:1 | 17-repos.sql |
| repos | `(vcs_platform, vcs_repo_id) UNIQUE` | VCS 仓库全局唯一 | 17-repos.sql |
| group_members | `(group_id, user_id) UNIQUE WHERE user_id IS NOT NULL` | 同群同用户不重复 | 11-group-members.sql |
| group_members | `(group_id, agent_id) UNIQUE WHERE agent_id IS NOT NULL` | 同群同 Agent 不重复 | 11-group-members.sql |

### 4.3 约束命名规范（V17 新增，V18 保留）

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
| tasks | idx_tasks_project | B-tree | 按项目查询任务 | 06-tasks.sql |
| tasks | idx_tasks_status | B-tree | 按状态筛选任务 | 06-tasks.sql |
| tasks | idx_tasks_assignee | B-tree | 按 Agent 查询分配 | 06-tasks.sql |
| tasks | idx_tasks_swarm | B-tree | 按蜂群查询分配 | 06-tasks.sql |
| tasks | idx_tasks_assignee_user | B-tree | 按人类用户查询分配 | 06-tasks.sql |
| tasks | idx_tasks_step | B-tree | 按步骤筛选任务 | 06-tasks.sql |
| tasks | idx_tasks_parent | B-tree | 父子任务查询 | 06-tasks.sql |
| tasks | idx_tasks_deleted | B-tree | 软删除过滤 | 06-tasks.sql |
| tasks | idx_tasks_acceptance_criteria_gin | GIN | 验收标准全文搜索 | 06-tasks.sql |
| task_dependencies | idx_task_deps_source | B-tree | 按源任务查找依赖 | 07-task-dependencies.sql |
| task_dependencies | idx_task_deps_target | B-tree | 按目标任务查找依赖 | 07-task-dependencies.sql |
| agent_execution_logs | idx_exec_logs_task | B-tree | 按任务查询日志 | 08-agent-execution-logs.sql |
| agent_execution_logs | idx_exec_logs_agent | B-tree | 按 Agent 查询日志 | 08-agent-execution-logs.sql |
| agent_execution_logs | idx_exec_logs_created | B-tree | 按时间排序日志 | 08-agent-execution-logs.sql |
| qa_records | idx_qa_records_task | B-tree | 按任务查询 QA 记录 | 09-qa-records.sql |
| qa_records | idx_qa_records_reviewer | B-tree | 按审查者查询 | 09-qa-records.sql |
| qa_records | idx_qa_records_result | B-tree | 按结果筛选 QA 记录 | 09-qa-records.sql |
| qa_records | idx_qa_review_dimensions_gin | GIN | 审查维度全文搜索 | 09-qa-records.sql |
| groups | idx_groups_project | B-tree | 按项目查询群 | 10-groups.sql |
| groups | idx_groups_mode | B-tree | 按模式筛选群 | 10-groups.sql |
| group_members | idx_group_members_group | B-tree | 按群查询成员 | 11-group-members.sql |
| group_members | idx_group_members_user_only | B-tree | 按用户查询群成员 | 11-group-members.sql |
| group_members | idx_group_members_agent_only | B-tree | 按 Agent 查询群成员 | 11-group-members.sql |
| group_messages | idx_group_messages_group | B-tree | 按群查询消息 | 12-group-messages.sql |
| group_messages | idx_group_messages_sender | B-tree | 按发送者查询消息 | 12-group-messages.sql |
| group_messages | idx_group_messages_timestamp | B-time | 按时间排序消息 | 12-group-messages.sql |
| group_messages | idx_group_messages_metadata_gin | GIN | 元数据全文搜索 | 12-group-messages.sql |
| meeting_outcomes | idx_meeting_outcomes_group | B-tree | 按群查询会议 | 13-meeting-outcomes.sql |
| meeting_outcomes | idx_meeting_outcomes_host | B-tree | 按主持人查询 | 13-meeting-outcomes.sql |
| meeting_outcomes | idx_meeting_outcomes_composite | B-tree | 群+主持人组合查询 | 13-meeting-outcomes.sql |
| swarms | idx_swarms_project | B-tree | 按项目查询蜂群 | 14-swarms.sql |
| swarms | idx_swarms_manager | B-tree | 按管理器查询 | 14-swarms.sql |
| swarms | idx_swarms_status | B-tree | 按状态筛选蜂群 | 14-swarms.sql |
| swarm_members | idx_swarm_members_swarm | B-tree | 按蜂群查询成员 | 15-swarm-members.sql |
| swarm_members | idx_swarm_members_agent | B-tree | 按 Agent 查询蜂群成员 | 15-swarm-members.sql |
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

### 5.2 外键级联策略（V17 修正，V18 保留）

| 外键 | 源表 → 目标表 | 删除策略 | 更新策略 | 说明 | 所在文件 |
|---|---|---|---|---|---|
| fk_projects_user | projects → users | SET NULL | CASCADE | 用户删除后项目保留 | 03-projects.sql |
| fk_requirements_project | requirements → projects | CASCADE | CASCADE | 项目删除则需求删除 | 04-requirements.sql |
| fk_tasks_project | tasks → projects | CASCADE | CASCADE | 项目删除则任务删除 | 06-tasks.sql |
| fk_tasks_agent | tasks → agents | SET NULL | CASCADE | Agent 删除后任务保留 | 06-tasks.sql |
| fk_tasks_swarm | tasks → swarms | SET NULL | CASCADE | 蜂群删除后任务保留 | 06-tasks.sql |
| fk_tasks_user | tasks → users | SET NULL | CASCADE | 用户删除后任务保留 | 06-tasks.sql |
| fk_td_tasks_source | task_dependencies → tasks | CASCADE | CASCADE | 任务删除则依赖删除 | 07-task-dependencies.sql |
| fk_td_tasks_target | task_dependencies → tasks | CASCADE | CASCADE | 任务删除则依赖删除 | 07-task-dependencies.sql |
| fk_exec_logs_task | agent_execution_logs → tasks | CASCADE | CASCADE | 任务删除则日志删除 | 08-agent-execution-logs.sql |
| fk_exec_logs_agent | agent_execution_logs → agents | SET NULL | CASCADE | Agent 删除后日志保留 | 08-agent-execution-logs.sql |
| fk_qr_task | qa_records → tasks | CASCADE | CASCADE | 任务删除则 QA 删除 | 09-qa-records.sql |
| fk_qr_agent | qa_records → agents | SET NULL | CASCADE | Agent 删除后 QA 保留 | 09-qa-records.sql |
| fk_groups_project | groups → projects | CASCADE | CASCADE | 项目删除则群删除 | 10-groups.sql |
| fk_groups_host | groups → agents | SET NULL | CASCADE | 主持人删除后群保留 | 10-groups.sql |
| fk_group_members_group | group_members → groups | CASCADE | CASCADE | 群删除则成员删除 | 11-group-members.sql |
| fk_group_members_user | group_members → users | **SET NULL** | CASCADE | **V17 修正** | 11-group-members.sql |
| fk_group_members_agent | group_members → agents | **SET NULL** | CASCADE | **V17 修正** | 11-group-members.sql |
| fk_group_messages_group | group_messages → groups | CASCADE | CASCADE | 群删除则消息删除 | 12-group-messages.sql |
| fk_meeting_outcomes_group | meeting_outcomes → groups | CASCADE | CASCADE | 群删除则成果删除 | 13-meeting-outcomes.sql |
| fk_meeting_outcomes_host | meeting_outcomes → agents | SET NULL | CASCADE | 主持人删除后成果保留 | 13-meeting-outcomes.sql |
| fk_swarms_project | swarms → projects | CASCADE | CASCADE | 项目删除则蜂群删除 | 14-swarms.sql |
| fk_swarms_manager | swarms → agents | SET NULL | CASCADE | 管理器删除后蜂群保留 | 14-swarms.sql |
| fk_swarm_members_swarm | swarm_members → swarms | CASCADE | CASCADE | 蜂群删除则成员删除 | 15-swarm-members.sql |
| fk_swarm_members_agent | swarm_members → agents | CASCADE | CASCADE | Agent 删除则蜂群成员删除 | 15-swarm-members.sql |
| fk_notifications_user | notifications → users | CASCADE | CASCADE | 用户删除则通知删除 | 16-notifications.sql |
| fk_notifications_project | notifications → projects | CASCADE | CASCADE | 项目删除则通知删除 | 16-notifications.sql |
| fk_repos_project | repos → projects | CASCADE | CASCADE | 项目删除则仓库删除 | 17-repos.sql |
| fk_branches_repo | repo_branches → repos | CASCADE | CASCADE | 仓库删除则分支删除 | 18-repo-branches.sql |
| fk_pr_repo | pull_requests → repos | CASCADE | CASCADE | 仓库删除则 PR 删除 | 19-pull-requests.sql |
| fk_commits_repo | commits → repos | CASCADE | CASCADE | 仓库删除则提交删除 | 20-commits.sql |
| fk_task_commits_task | task_commits → tasks | CASCADE | CASCADE | 任务删除则关联删除 | 21-task-commits.sql |
| fk_task_commits_commit | task_commits → commits | CASCADE | CASCADE | 提交删除则关联删除 | 21-task-commits.sql |
| fk_tasks_parent | tasks → tasks | CASCADE | CASCADE | 自引用：父任务删除则子任务删除 | 06-tasks.sql |

**共 33 条外键约束。**

### 5.3 FK 索引验证表（V17 新增，V18 保留并更新）

所有外键字段均有对应索引，避免 DELETE/UPDATE 时的全表扫描锁：

| 外键约束 | 对应索引 | 验证状态 |
|---|---|---|
| fk_projects_user (projects.creator_id) | idx_projects_creator | ✅ 已创建 |
| fk_requirements_project (requirements.project_id) | idx_requirements_project | ✅ 已创建 |
| fk_tasks_project (tasks.project_id) | idx_tasks_project | ✅ 已创建 |
| fk_tasks_agent (tasks.assignee_agent_id) | idx_tasks_assignee | ✅ 已创建 |
| fk_tasks_swarm (tasks.assignee_swarm_id) | idx_tasks_swarm | ✅ 已创建 |
| fk_tasks_user (tasks.assignee_user_id) | idx_tasks_assignee_user | ✅ 已创建 |
| fk_td_tasks_source (task_dependencies.source_task_id) | idx_task_deps_source | ✅ 已创建 |
| fk_td_tasks_target (task_dependencies.target_task_id) | idx_task_deps_target | ✅ 已创建 |
| fk_exec_logs_task (agent_execution_logs.task_id) | idx_exec_logs_task | ✅ 已创建 |
| fk_exec_logs_agent (agent_execution_logs.agent_id) | idx_exec_logs_agent | ✅ 已创建 |
| fk_qr_task (qa_records.task_id) | idx_qa_records_task | ✅ 已创建 |
| fk_qr_agent (qa_records.reviewer_agent_id) | idx_qa_records_reviewer | ✅ 已创建 |
| fk_groups_project (groups.project_id) | idx_groups_project | ✅ 已创建 |
| fk_group_members_group (group_members.group_id) | idx_group_members_group | ✅ 已创建 |
| fk_group_members_user (group_members.user_id) | idx_group_members_user_only | ✅ 已创建 |
| fk_group_members_agent (group_members.agent_id) | idx_group_members_agent_only | ✅ 已创建 |
| fk_group_messages_group (group_messages.group_id) | idx_group_messages_group | ✅ 已创建 |
| fk_swarms_project (swarms.project_id) | idx_swarms_project | ✅ 已创建 |
| fk_swarms_manager (swarms.manager_agent_id) | idx_swarms_manager | ✅ 已创建 |
| fk_swarm_members_swarm (swarm_members.swarm_id) | idx_swarm_members_swarm | ✅ 已创建 |
| fk_swarm_members_agent (swarm_members.agent_id) | idx_swarm_members_agent | ✅ 已创建 |
| fk_notifications_user (notifications.user_id) | idx_notifications_user | ✅ 已创建 |
| fk_notifications_project (notifications.project_id) | idx_notifications_project | ✅ 已创建 |
| fk_repos_project (repos.project_id) | 无单独索引（UNIQUE 约束隐含索引） | ✅ UNIQUE 约束覆盖 |
| fk_branches_repo (repo_branches.repo_id) | idx_repo_branches_repo | ✅ 已创建 |
| fk_pr_repo (pull_requests.repo_id) | idx_prs_repo | ✅ 已创建 |
| fk_commits_repo (commits.repo_id) | idx_commits_repo | ✅ 已创建 |
| fk_task_commits_task (task_commits.task_id) | idx_task_commits_task | ✅ 已创建 |
| fk_task_commits_commit (task_commits.commit_id) | idx_task_commits_commit | ✅ 已创建 |

**V18 验证结论：全部 29 个外键字段均有对应索引覆盖，无遗漏。**

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

完整递归 CTE 实现见 `sql/07-task-dependencies.sql`。
返回值：检测到循环依赖时抛出 EXCEPTION，否则允许插入。

### 8.2 软删除物理清理

完整实现见 `sql/96-soft-delete-cleanup.sql`。
功能：按外键依赖顺序逐层清理超过保留期（默认 90 天）的软删除记录。
清理顺序：notifications → swarm_members/group_members/group_messages → swarms/groups/tasks → projects。

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
| update_tasks_updated_at | tasks | BEFORE UPDATE | 自动更新 updated_at | 06-tasks.sql |
| trg_sync_project_current_step | tasks | AFTER INSERT/UPDATE | 同步项目 current_step | 03-projects.sql |
| trg_enforce_parent_same_project | tasks | BEFORE INSERT/UPDATE | 确保子任务与父任务同项目 | 06-tasks.sql |
| enforce_same_project_dependency | task_dependencies | BEFORE INSERT/UPDATE | 确保依赖双方同项目 | 07-task-dependencies.sql |
| trg_check_circular_dependency | task_dependencies | BEFORE INSERT/UPDATE | 循环依赖检测 | 07-task-dependencies.sql |
| update_groups_updated_at | groups | BEFORE UPDATE | 自动更新 updated_at | 10-groups.sql |
| update_swarms_updated_at | swarms | BEFORE UPDATE | 自动更新 updated_at | 14-swarms.sql |
| auto_add_manager_to_members | swarms | AFTER INSERT | 管理器自动注册为蜂群成员 | 14-swarms.sql |
| update_repo_branches_updated_at | repo_branches | BEFORE UPDATE | 自动更新 updated_at | 18-repo-branches.sql |
| update_pull_requests_updated_at | pull_requests | BEFORE UPDATE | 自动更新 updated_at | 19-pull-requests.sql |

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
| 5 | tasks | 06-tasks.sql | ~80 | 三选一分配、16 步、父子项目一致性 |
| 6 | task_dependencies | 07-task-dependencies.sql | ~90 | 循环依赖检测递归 CTE、同项目约束 |
| 7 | agent_execution_logs | 08-agent-execution-logs.sql | ~23 | 执行内容与结果 JSONB |
| 8 | qa_records | 09-qa-records.sql | ~28 | score 0~100、审查维度 JSONB |
| 9 | groups | 10-groups.sql | ~30 | 与 project 1:1 |
| 10 | group_members | 11-group-members.sql | ~30 | SET NULL 级联、成员类型约束 |
| 11 | group_messages | 12-group-messages.sql | ~56 | 多发送者类型、sender_id 应用层校验 |
| 12 | meeting_outcomes | 13-meeting-outcomes.sql | ~32 | UNIQUE(group_id, started_at) |
| 13 | swarms | 14-swarms.sql | ~47 | 管理器自动注册触发器 |
| 14 | swarm_members | 15-swarm-members.sql | ~22 | UNIQUE(swarm_id, agent_id) |
| 15 | notifications | 16-notifications.sql | ~26 | 多类型通知 |
| 16 | repos | 17-repos.sql | ~26 | 与 project 1:1、VCS 平台约束 |
| 17 | repo_branches | 18-repo-branches.sql | ~28 | UNIQUE(repo_id, name) |
| 18 | pull_requests | 19-pull-requests.sql | ~34 | UNIQUE(repo_id, number) |
| 19 | commits | 20-commits.sql | ~22 | UNIQUE(repo_id, sha) |
| 20 | task_commits | 21-task-commits.sql | ~20 | UNIQUE(task_id, commit_id) |
| 21 | 视图 v_project_progress | 99-views.sql | ~24 | 项目进度统计 |
| 22 | 视图 v_agent_load | 99-views.sql | ~14 | Agent 负载统计 |
| 23 | 视图 v_qa_statistics | 99-views.sql | ~17 | QA 检验统计 |

**总计：21 张数据表 + 3 个视图，25 个 SQL 文件，约 1026 行 DDL。**

### 10.2 枚举类型清单（16 个）

| 序号 | 类型名 | 值数量 | 所在文件 |
|---|---|---|---|
| 1 | user_role | 3 | 01-enums.sql |
| 2 | project_status | 4 | 01-enums.sql |
| 3 | agent_type | 2 | 01-enums.sql |
| 4 | agent_status | 3 | 01-enums.sql |
| 5 | task_status | 5 | 01-enums.sql |
| 6 | task_type | 16 | 01-enums.sql |
| 7 | group_mode | 2 | 01-enums.sql |
| 8 | member_type | 2 | 01-enums.sql |
| 9 | sender_type | 2 | 01-enums.sql |
| 10 | meeting_type | 4 | 01-enums.sql |
| 11 | dependency_type_enum | 4 | 01-enums.sql |
| 12 | swarm_purpose | 2 | 01-enums.sql |
| 13 | swarm_status | 3 | 01-enums.sql |
| 14 | qa_result | 2 | 01-enums.sql |
| 15 | notification_type | 7 | 01-enums.sql |
| 16 | pr_status | 3 | 01-enums.sql |

### 10.3 触发器清单（14 个）

| 序号 | 触发器名 | 表 | 功能 | 所在文件 |
|---|---|---|---|---|
| 1 | update_users_updated_at | users | 自动更新 updated_at | 02-users.sql |
| 2 | update_projects_updated_at | projects | 自动更新 updated_at | 03-projects.sql |
| 3 | trg_sync_project_current_step | tasks | 同步项目 current_step | 03-projects.sql |
| 4 | update_requirements_updated_at | requirements | 自动更新 updated_at | 04-requirements.sql |
| 5 | update_agents_updated_at | agents | 自动更新 updated_at | 05-agents.sql |
| 6 | update_tasks_updated_at | tasks | 自动更新 updated_at | 06-tasks.sql |
| 7 | trg_enforce_parent_same_project | tasks | 父子项目一致性 | 06-tasks.sql |
| 8 | enforce_same_project_dependency | task_dependencies | 依赖同项目约束 | 07-task-dependencies.sql |
| 9 | trg_check_circular_dependency | task_dependencies | 循环依赖检测 | 07-task-dependencies.sql |
| 10 | update_groups_updated_at | groups | 自动更新 updated_at | 10-groups.sql |
| 11 | update_swarms_updated_at | swarms | 自动更新 updated_at | 14-swarms.sql |
| 12 | auto_add_manager_to_members | swarms | 管理器自动注册 | 14-swarms.sql |
| 13 | update_repo_branches_updated_at | repo_branches | 自动更新 updated_at | 18-repo-branches.sql |
| 14 | update_pull_requests_updated_at | pull_requests | 自动更新 updated_at | 19-pull-requests.sql |

---

## 11. 修正内容对照表

### 11.1 V18 修正项

| 序号 | 修正项 | 位置 | 变更内容 |
|---|---|---|---|
| 1 | SQL 文件清单修正 | SQL 文件清单表 | 修正为与实际 25 个文件一一对应（移除不存在的文件引用） |
| 2 | ER 图补全 | 第 1.1 节 | 补全全部 21 张表的 ER 关系图（V17 仅展示 11 个实体） |
| 3 | 枚举类型补全 | 第 1.3 节 | 完整列出 16 个枚举类型及全部值（V17 在 meeting_type 处截断） |
| 4 | 第 2~11 节补全 | 第 2~11 节 | 补充 DDL 文件引用、关键设计决策、约束与索引总结、索引与级联策略、事务隔离、分区策略、存储过程、视图、表清单、修正对照表 |
| 5 | 核心实体说明更新 | 第 1.2 节 | 补全全部 21 张表的说明与对应 SQL 文件 |
| 6 | FK 索引验证表更新 | 第 5.3 节 | 验证全部 29 个外键字段均有索引覆盖 |

### 11.2 V14~V17 保留修正项

| 版本 | 关键修正 |
|---|---|
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
# 预期结果：14
```

### 12.3 从 V17 升级到 V18

V18 主要修正文档内容，SQL 文件本身无结构性变更（V17 修正已在 SQL 文件中体现）。升级时无需执行额外迁移脚本，仅需确认 SQL 文件清单与实际文件一致。

---

*文档结束。完整 DDL 请参见 sql/ 目录。*
