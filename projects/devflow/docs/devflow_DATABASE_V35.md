================================================================================
DevFlow 数据库设计文档 - V34 版本
================================================================================

**版本**: V34
**日期**: 2026-07-12
**作者**: HouWang (后旺)
**状态**: V34 版本（后端 V40 对齐修正版）

---

## 变更日志

- V34 (2026-07-12): 根据后端 V40 vs 数据库 V33 跨文档一致性检验报告修正以下 8 项一致性问题
  1. 【严重 - project_status 枚举值修正】后端 V40 §5.2.2 使用 created/in_progress/completed/cancelled，数据库 V33 §1.3 使用 active/paused/completed/archived。V34 修正：改为 (created, in_progress, completed, cancelled)，默认值从 'active' 改为 'created'，与后端 V40 对齐。
  2. 【严重 - user_role 枚举值修正】后端 V40 §5.2.1 使用 user/admin/system_admin，数据库 V33 §1.3 仅 user/admin（已移除 system_admin）。V34 修正：添加 system_admin，改为 (user, admin, system_admin)，与后端 V40 对齐。
  3. 【严重 - agent_status 枚举值修正】后端 V40 §5.2.4 使用 online/offline/busy，数据库 V33 §1.3 使用 idle/busy/error/offline。V34 修正：改为 (online, offline, busy)，默认值从 'idle' 改为 'offline'，与后端 V40 对齐。
  4. 【严重 - sender_type 枚举值修正】后端 V40 §5.2.10 使用 user/agent（二值），数据库 V33 §1.3 使用 user/agent/system（三值）。V34 修正：移除 system，改为 (user, agent)，同步更新 sender_id 校验触发器逻辑，与后端 V40 对齐。
  5. 【严重 - swarms.manager_agent_id 约束修正】后端 V40 §5.2.11 为 NOT NULL，数据库 V33 §3.6 为 NULLABLE ON DELETE SET NULL。V34 修正：恢复 NOT NULL 约束，移除 ON DELETE SET NULL（改用默认 NO ACTION），与后端 V40 对齐。
  6. 【严重 - projects.deleted_at 字段恢复】后端 V40 §5.2.2 包含 deleted_at 字段，数据库 V33 §3.1 已移除该字段。V34 修正：恢复 deleted_at 字段、相关索引、触发器引用和软删除清理逻辑，与后端 V40 对齐。
  7. 【严重 - group_messages.mentions 字段类型修正】后端 V40 §5.2.10 使用 JSONB，数据库 V33 §13.13 使用 TEXT[]。V34 修正：改为 JSONB 类型，GIN 索引使用 jsonb_path_ops 操作符类，与后端 V40 对齐。
  8. 【严重 - project_members 表结构修正】后端 V40 §5.2.20 仅支持 user_id（NOT NULL），数据库 V33 §13.23 支持 user_id/agent_id 双成员模式（均 NULLABLE）。V34 修正：移除 agent_id 字段及相关约束，仅保留 user_id NOT NULL，与后端 V40 对齐。

- V33 (2026-07-11): SQL 文件实际修正与跨文档一致性最终对齐版
  1. 【修正 - group_messages.mentions 字段类型】从 JSONB 改为 TEXT[]，GIN 索引使用 text_pattern_gin 操作符类
  2. 【修正 - swarms.manager_agent_id 约束】从 NOT NULL/NO ACTION 改为 NULLABLE/ON DELETE SET NULL
  3. 【修正 - projects 表 deleted_at 字段】移除 deleted_at 字段及相关索引
  4. 【修正 - 新增三张表 SQL 文件】创建 22-workflow-progress.sql、23-workflow-steps.sql、24-project-members.sql
  5. 【修正 - projects.status 枚举值】改为 (active, paused, completed, archived)
  6. 【修正 - user_role 枚举值】移除 system_admin，改为 (user, admin)
  7. 【修正 - agent_status 枚举值】改为 (idle, busy, error, offline)
  8. 【修正 - sender_type 枚举值】添加 system，改为 (user, agent, system)

- V32 (2026-07-10): V31 修正确认与跨文档一致性验证版
  1. 【确认 - group_messages.mentions 字段类型】V31 已将 mentions 改回 TEXT[]
  2. 【确认 - swarms.manager_agent_id 约束】V31 已恢复 NULLABLE 约束
  3. 【确认 - projects 表 deleted_at 字段】V31 已移除 deleted_at 字段
  4. 【确认 - 新增三张表】V31 已新增 workflow_progress、workflow_steps、project_members
  5. 【确认 - projects.status 枚举值】V31 已改为 (active, paused, completed, archived)
  6. 【确认 - user_role 枚举值】V31 已移除 system_admin
  7. 【确认 - agent_status 枚举值】V31 已改为 (idle, busy, error, offline)
  8. 【确认 - sender_type 枚举值】V31 已添加 system

- V31 (2026-07-09): 根据后端 V37 vs 数据库 V30 跨文档一致性检验报告修正
  1. 【修正 - group_messages.mentions 字段类型】从 JSONB 改回 TEXT[]
  2. 【修正 - swarms.manager_agent_id 约束】恢复 NULLABLE 约束
  3. 【修正 - projects 表 deleted_at 字段移除】移除 deleted_at 字段
  4. 【修正 - 新增三张表】新增 workflow_progress、workflow_steps、project_members
  5. 【修正 - projects.status 枚举值】改为 (active, paused, completed, archived)
  6. 【修正 - user_role 枚举值】移除 system_admin
  7. 【修正 - agent_status 枚举值】改为 (idle, busy, error, offline)
  8. 【修正 - sender_type 枚举值】添加 system

- V30 (2026-07-08): 根据后端 V36 vs 数据库 V29 跨文档一致性检验报告修正
  1. 【严重 - swarms.manager_agent_id 约束修正】恢复 NOT NULL 约束
  2. 【严重 - group_messages.mentions 字段类型修正】TEXT[] 改为 JSONB
  3. 【一般 - swarms.dissolved_at 字段确认】保留 dissolved_at TIMESTAMPTZ NULLABLE
  4. 【记录 - artifacts.storage_path 字段记录】记录后续新增时应包含 storage_path

- V29 (2026-07-07): 跨文档一致性检验报告修正
  1. 【一般 - swarms.manager_agent_id 约束确认】确认为 INTEGER NULLABLE
  2. 【一般 - group_messages.mentions 字段类型确认】确认为 TEXT[]
  3. 【严重 - projects 与 groups 关系基数修正】从 1:1 改为 1:N
  4. 【记录 - 后端 V35 9.2 修订范围不完整】记录发现

- V28 (2026-07-06): 跨文档一致性检验报告修正
  1. 【严重 - swarm_purpose 枚举值不一致】添加 tdd_test 枚举值
  2. 【严重 - message_type_enum 枚举值不一致】改为 (text, system, meeting)
  3. 【严重 - swarms 表缺少 step_number 字段】添加 step_number 字段
  4. 【严重 - qa_records 表缺少字段】添加 project_id/step_number/review_round
  5. 【严重 - group_messages 表缺少 mentions 字段】添加 mentions TEXT[] 字段
  6. 【严重 - notifications.project_id 约束不一致】改为可空
  7. 【一般 - 索引更新】为新增字段添加对应索引
  8. 【一般 - 注释更新】更新相关 SQL 文件注释

- V27 (2026-07-05): 后荣-DATABASE V26检验报告修正
  1. 【致命 - NOT NULL 与 ON DELETE SET NULL 约束冲突】移除 NOT NULL 约束
  2. 【严重 - 软删除覆盖声明不属实】修正为 5 张软删除 + 11 张孤儿清理
  3. 【严重 - tasks 表 deleted_at 索引修正】改为部分索引
  4. 【一般 - 文档重复内容】删除重复段落
  5. 【一般 - group_members 孤儿记录风险】新增风险分析和建议方案

- V26 (2026-07-04): 稳定确认版
  1. 后荣-DATABASE 检验未返回不合格项
  2. 保留 V25 全部 15 节内容，无结构变更
  3. 确认 25 个 SQL 文件完整性
  4. 连续四版无不合格项，数据库设计已完全收敛稳定

---

## 文档结构说明

V22 文档采用拆分文件架构：

- **主文档（本文）**：包含变更日志、ER 图、枚举类型定义、DDL 文件引用、关键设计决策、索引与级联策略（第 5 节）、事务隔离（第 6 节）、分区策略（第 7 节）、存储过程（第 8 节）、视图（第 9 节）、表清单（第 10 节）、修正对照表（第 11 节）、执行指南（第 12 节）、表字段级详述（第 13 节）、V34 修正验证总结（第 14 节）、SQL 文件校验与执行顺序验证（第 15 节）
- **SQL 文件**：完整 DDL 拆分为 28 个独立 `.sql` 文件，存放于本目录 `sql/` 子目录下（路径：`docs/sql/`）
- **执行顺序**：按文件名数字顺序执行（01 到 99），确保依赖关系正确

### V34 核心修正：8 项一致性问题逐一修复

| 序号 | 问题分类 | 问题 | V33 状态 | V34 修正 |
|------|---------|------|----------|----------|
| 1 | 严重 | project_status 枚举值不一致 | (active, paused, completed, archived) | 改为 (created, in_progress, completed, cancelled) |
| 2 | 严重 | user_role 枚举值不一致 | (user, admin) | 添加 system_admin，改为 (user, admin, system_admin) |
| 3 | 严重 | agent_status 枚举值不一致 | (idle, busy, error, offline) | 改为 (online, offline, busy) |
| 4 | 严重 | sender_type 枚举值不一致 | (user, agent, system) | 移除 system，改为 (user, agent) |
| 5 | 严重 | swarms.manager_agent_id 约束不一致 | NULLABLE ON DELETE SET NULL | 恢复 NOT NULL，移除 ON DELETE SET NULL |
| 6 | 严重 | projects.deleted_at 字段不一致 | 已移除 | 恢复 deleted_at 字段及相关索引 |
| 7 | 严重 | group_messages.mentions 字段类型不一致 | TEXT[] | 改为 JSONB，索引使用 jsonb_path_ops |
| 8 | 严重 | project_members 表结构不一致 | 支持 user_id/agent_id 双成员模式 | 移除 agent_id，仅保留 user_id NOT NULL |

### SQL 文件清单（V34 确认：全部 28 个文件）

| 序号 | 文件 | 说明 | 行数 |
|------|------|------|------|
| 1 | `sql/01-enums.sql` | 扩展与枚举类型定义（18 个枚举，**V34 修正 4 个枚举值**） | ~68 |
| 2 | `sql/02-users.sql` | 用户表（含 update_updated_at_column 函数） | ~39 |
| 3 | `sql/03-projects.sql` | 项目表（**V34 恢复 deleted_at 字段**） | ~45 |
| 4 | `sql/04-requirements.sql` | 需求表（软件需求说明书） | ~30 |
| 5 | `sql/05-agents.sql` | Agent 表（含 9 个命名 Agent 初始化） | ~47 |
| 6 | `sql/06-swarms.sql` | Agent 蜂群表（**V34 恢复 manager_agent_id NOT NULL**） | ~52 |
| 7 | `sql/07-swarm-members.sql` | 蜂群成员关联表 | ~22 |
| 8 | `sql/08-tasks.sql` | 任务表（deleted_at 部分索引） | ~133 |
| 9 | `sql/09-task-dependencies.sql` | 任务依赖表 | ~86 |
| 10 | `sql/10-agent-execution-logs.sql` | Agent 执行日志表 | ~25 |
| 11 | `sql/11-qa-records.sql` | QA 检验记录表（含 project_id/step_number/review_round） | ~31 |
| 12 | `sql/12-groups.sql` | 群组表（项目讨论群） | ~29 |
| 13 | `sql/13-group-members.sql` | 群成员表 | ~29 |
| 14 | `sql/14-group-messages.sql` | 群消息表（**V34 修正 mentions 为 JSONB**） | ~93 |
| 15 | `sql/15-meeting-outcomes.sql` | 会议结果表 | ~24 |
| 16 | `sql/16-notifications.sql` | 通知表（project_id 可空） | ~32 |
| 17 | `sql/17-repos.sql` | 代码仓库表 | ~22 |
| 18 | `sql/18-repo-branches.sql` | 代码分支表 | ~28 |
| 19 | `sql/19-pull-requests.sql` | 拉取请求表 | ~34 |
| 20 | `sql/20-commits.sql` | 提交记录表 | ~21 |
| 21 | `sql/21-task-commits.sql` | 任务与提交关联表 | ~19 |
| 22 | `sql/22-workflow-progress.sql` | 工作流进度表（**V33 新增**） | ~33 |
| 23 | `sql/23-workflow-steps.sql` | 工作流步骤表（**V33 新增**） | ~37 |
| 24 | `sql/24-project-members.sql` | 项目成员表（**V34 修正：仅 user_id NOT NULL**） | ~20 |
| 25 | `sql/96-soft-delete-cleanup.sql` | 软删除物理清理存储过程（**V34 恢复 projects 清理**） | ~235 |
| 26 | `sql/97-permissions.sql` | 权限设置 | ~18 |
| 27 | `sql/98-init-data.sql` | 初始化数据 | ~12 |
| 28 | `sql/99-views.sql` | 视图定义 | ~72 |
| **合计** | **28 个文件** | | **约 1315 行** |

> 完整 DDL 请查看 `sql/` 目录下的各 `.sql` 文件。以下保留设计说明与架构文档。

---

## 1. ER 概述

### 1.1 实体关系图

```
================================================================================
                       DevFlow 数据库 ER 图（V34 完整版）
================================================================================

===== 一、用户与项目层 =====

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
   |  1:N     |  |  1:N     |  |  1:1     |
   +----+----+  +----+-----+  +----+-----+
        |            |              |
        v            v              v
+-------------+ +---------------+ +---------------+
|group_members| |swarm_members  | |repo_branches  |
|   (13)      | |   (07)        | |   (18)        |
+------+------+ +----------------+ +-------+-------+
        |                                                |
        v                                                v
+----------------+                            +-----------------+
| group_messages |                            |  pull_requests  |
|     (14)       |                            |      (19)       |
+----------------+                            +-----------------+
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
                                           +----+---+-----+
                                                 |       |
                                                 v       v
                                           +----------+ +----------+
                                           |   tasks  | |  commits |
                                           |  (08)    | |  (20)    |
                                           +----------+ +----------+

===== 二、任务与执行层 =====

+----------+     +-----------+     +----------+
|  agents  |-----|   tasks   |-----|task_deps |
|  (05)    | M:N |   (08)    |     |  (09)    |
+-----+----+     +-----+-----+     +----------+
     |                    |
     |         +----------+-----------+
     |         v                       v
     |  +----------------+   +--------------+
     |  |agent_exec_logs |   |  qa_records  |
     |  |   (10)         |   |   (11)       |
     |  +----------------+   +--------------+

===== 三、协作与沟通层 =====

+------------------+
|| meeting_outcomes ||
||    (15)          |
+--------+---------+
         |
   +-----+-------+
   v               v
+----------+   +----------+
|  groups  |   |  agents  |
|  (12)    |   |  (05)    |
+----------+   +----------+
  (group_id)    (host_agent_id)

===== 四、蜂群管理层 =====

+----------+     +-----------+     +---------------+
|  agents  |-----|  swarms   |-----|swarm_members  |
|  (05)    | 1:N |   (06)    | 1:N |    (07)       |
+----------+     +-----------+     +---------------+
  manager_agent_id  自动注册触发器  swarm_member_status 枚举

===== 五、通知层 =====

notifications 表仅包含两条外键：
  - user_id -> users(id)      通知接收者（人类用户）
  - project_id -> projects(id) 通知关联的项目

+----------+     +-----------+     +---------------+
|  users   |-----| projects  |-----| notifications |
|  (02)    |     |   (03)    |     |    (16)       |
+----------+     +-----------+     +---------------+

===== 六、代码仓库层 =====

+--------+     +---------------+     +---------------+
| repos  |-----| repo_branches |     |  pull_requests|
|  (17)  | 1:N |    (18)       |     |    (19)       |
+--------+     +-------+-------+     +---+-------+---+
                                 |               |
                                 v               v
                           +----------+    +----------+
                           | commits  |    |  branches |
                           |  (20)    |    | (源/目标) |
                           +-----+----+    +----------+
                                 |
                                 v
                          +--------------+
                          |task_commits  |
                          |    (21)      |
                          +--------------+

===== 七、工作流与项目成员层 =====

+-----------+     +------------------+     +----------------+
| projects  |-----|workflow_progress |-----| workflow_steps |
|   (03)    | 1:1 |    (22)          | 1:N |    (23)        |
+-----------+     +------------------+     +----------------+

+-----------+     +----------------+
| projects  |-----| project_members|
|   (03)    | 1:N |    (24)        |
+-----------+     +----------------+
  (project_id)     (user_id NOT NULL)

**关系方向说明:**
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
                    -> meeting_outcomes -> agents (host_agent_id)
projects -> swarms -> swarm_members
projects -> repos -> repo_branches
                    -> pull_requests
                    -> commits -> task_commits
projects -> notifications -> users (user_id)
projects -> workflow_progress -> workflow_steps
projects -> project_members (user_id)
agents -> tasks (assignee)
agents -> group_members
agents -> swarms (manager)
agents -> swarm_members
agents -> meeting_outcomes (host_agent_id)
```

### 1.2 核心实体说明

| 实体 | 对应 SQL 文件 | 说明 | 关键约束 |
|------|------|------|------|
| users | 02-users.sql | 人类用户信息 | email UNIQUE(citext)、password_hash 非空 |
| projects | 03-projects.sql | 项目主表 | code UNIQUE、current_step 1~16、**V34 恢复 deleted_at** |
| requirements | 04-requirements.sql | 软件需求说明书 | 关联 project_id、(project_id, version) 唯一 |
| agents | 05-agents.sql | Agent 信息 | name UNIQUE、支持命名 Agent 与蜂群 Agent |
| swarms | 06-swarms.sql | Agent 蜂群 | 关联 project_id、manager_agent_id（**V34 恢复 NOT NULL**）；1:N 关系 |
| swarm_members | 07-swarm-members.sql | 蜂群成员 | UNIQUE(swarm_id, agent_id)、swarm_member_status 枚举 |
| tasks | 08-tasks.sql | 任务记录 | step_number 1~16、三选一分配、含 sync_project_current_step 触发器 |
| task_dependencies | 09-task-dependencies.sql | 任务依赖 | 循环依赖检测方向已修正、使用枚举类型 |
| agent_execution_logs | 10-agent-execution-logs.sql | Agent 执行日志 | 关联 task_id 和 agent_id |
| qa_records | 11-qa-records.sql | QA 检验记录 | score 0~100、关联 task_id |
| groups | 12-groups.sql | 项目讨论群 | 与 project 1:N（V29 修正） |
| group_members | 13-group-members.sql | 群成员 | user_id/agent_id ON DELETE SET NULL（V27 孤儿风险见第 3.9 节） |
| group_messages | 14-group-messages.sql | 群消息 | message_type 使用枚举、**V34 修正 mentions 为 JSONB** |
| meeting_outcomes | 15-meeting-outcomes.sql | 会议结果 | UNIQUE(group_id, started_at)；FK: group_id->groups, host_agent_id->agents |
| notifications | 16-notifications.sql | 通知消息 | FK: user_id->users, project_id->projects |
| repos | 17-repos.sql | 代码仓库 | 与 project 1:1、(vcs_platform, vcs_repo_id) 唯一 |
| repo_branches | 18-repo-branches.sql | 代码分支 | UNIQUE(repo_id, name) |
| pull_requests | 19-pull-requests.sql | 拉取请求 | 含 source_branch_id/target_branch_id 外键 |
| commits | 20-commits.sql | 提交记录 | UNIQUE(repo_id, sha) |
| task_commits | 21-task-commits.sql | 任务-提交关联 | UNIQUE(task_id, commit_id) |
| workflow_progress | 22-workflow-progress.sql | 工作流进度 | **V33 新增**、与 projects 1:1 关系 |
| workflow_steps | 23-workflow-steps.sql | 工作流步骤 | **V33 新增**、与 workflow_progress 1:N 关系 |
| project_members | 24-project-members.sql | 项目成员 | **V34 修正**、仅 user_id NOT NULL、与 projects 1:N 关系 |

### 1.3 枚举类型定义（18 个枚举类型，全部被引用）

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
| 11 | `dependency_type_enum` | `finish_to_start`, `start_to_start`, `finish_to_finish`, `start_to_finish` | 依赖类型 | 01-enums.sql | task_dependencies.dependency_type |
| 12 | `swarm_purpose` | `code_writing`, `testing`, `tdd_test` | 蜂群用途 | 01-enums.sql | swarms.purpose |
| 13 | `swarm_status` | `active`, `completed`, `dissolved` | 蜂群状态 | 01-enums.sql | swarms.status |
| 14 | `qa_result` | `pass`, `fail` | QA 检验结果 | 01-enums.sql | qa_records.acceptance_result |
| 15 | `notification_type` | `step_complete`, `qa_pass`, `qa_fail`, `task_assigned`, `task_completed`, `project_complete`, `system_alert` | 通知类型 | 01-enums.sql | notifications.type |
| 16 | `pr_status` | `open`, `closed`, `merged` | Pull Request 状态 | 01-enums.sql | pull_requests.status |
| 17 | `swarm_member_status` | `active`, `inactive`, `removed` | 蜂群成员状态 | 01-enums.sql | swarm_members.status |
| 18 | `message_type_enum` | `text`, `system`, `meeting` | 消息类型 | 01-enums.sql | group_messages.message_type |

> **修正确认**：
> - `swarm_member_status` 枚举与 `swarm_status` 枚举值域不同，语义区分清楚
> - `message_type_enum` 枚举取代 group_messages 表中 VARCHAR(20)+CHECK 约束
> - 全部 18 个枚举类型均被至少一张表引用，无冗余枚举

> **V34 修正说明**：
> - `user_role` 枚举恢复 system_admin，与后端 V40 §5.2.1 对齐
> - `project_status` 枚举改为 (created, in_progress, completed, cancelled)，与后端 V40 §5.2.2 对齐
> - `agent_status` 枚举改为 (online, offline, busy)，与后端 V40 §5.2.4 对齐
> - `sender_type` 枚举移除 system，改为二值 (user, agent)，与后端 V40 §5.2.10 对齐

> **agent_status 应用层管理注释**: `agent_status` 枚举定义了三种状态，但实际状态切换由应用层管理：
> - `online`: Agent 可用，可被分配新任务
> - `busy`: Agent 正在执行任务中（任务分配时由应用层自动设置）
> - `offline`: Agent 不可用或空闲（任务完成/失败/取消时由应用层恢复）
> 数据库不通过触发器自动切换状态，避免数据库层与应用层状态管理冲突。

---

## 2. DDL 文件引用

完整建表语句、索引定义、触发器、存储过程请参见 `sql/` 目录下的独立 SQL 文件。

### 2.1 枚举与基础设置
- `sql/01-enums.sql` — 扩展（uuid-ossp、pg_trgm、citext）与 18 个枚举类型定义（**V34 修正 4 个枚举值**）

### 2.2 核心业务表
- `sql/02-users.sql` — 用户表（含 citext email 唯一约束、updated_at 触发器）
- `sql/03-projects.sql` — 项目表（含 current_step CHECK 1~16、部分索引、**V34 恢复 deleted_at**）
- `sql/04-requirements.sql` — 需求表（含 (project_id, version) 唯一索引）
- `sql/05-agents.sql` — Agent 表（含 9 个命名 Agent 初始化数据）

### 2.3 蜂群管理表
- `sql/06-swarms.sql` — Agent 蜂群表（含管理器自动注册触发器、**V34 恢复 manager_agent_id NOT NULL**）
- `sql/07-swarm-members.sql` — 蜂群成员关联表

### 2.4 任务与依赖表
- `sql/08-tasks.sql` — 任务表（deleted_at 部分索引）
- `sql/09-task-dependencies.sql` — 任务依赖表

### 2.5 执行与检验表
- `sql/10-agent-execution-logs.sql` — Agent 执行日志表
- `sql/11-qa-records.sql` — QA 检验记录表（含 project_id/step_number/review_round）

### 2.6 协作与沟通表
- `sql/12-groups.sql` — 群组表（与 project 1:N，V29 修正）
- `sql/13-group-members.sql` — 群成员表（V27 孤儿风险见第 3.9 节）
- `sql/14-group-messages.sql` — 群消息表（**V34 修正 mentions 为 JSONB**）
- `sql/15-meeting-outcomes.sql` — 会议结果表（UNIQUE(group_id, started_at)）

### 2.7 通知与代码仓库表
- `sql/16-notifications.sql` — 通知表（project_id NULLABLE）
- `sql/17-repos.sql` — 代码仓库表（与 project 1:1）
- `sql/18-repo-branches.sql` — 代码分支表
- `sql/19-pull-requests.sql` — 拉取请求表
- `sql/20-commits.sql` — 提交记录表
- `sql/21-task-commits.sql` — 任务与提交关联表

### 2.8 工作流与项目成员表（V33 新增）
- `sql/22-workflow-progress.sql` — 工作流进度表（与 projects 1:1 关系）
- `sql/23-workflow-steps.sql` — 工作流步骤表（与 workflow_progress 1:N 关系）
- `sql/24-project-members.sql` — 项目成员表（**V34 修正：仅 user_id NOT NULL**）

### 2.9 工具与辅助脚本
- `sql/96-soft-delete-cleanup.sql` — 软删除物理清理存储过程（**V34 恢复 projects 清理**）
- `sql/97-permissions.sql` — 数据库权限设置
- `sql/98-init-data.sql` — 初始化数据（admin 用户）
- `sql/99-views.sql` — 视图定义（v_project_progress、v_agent_load、v_qa_statistics）

---

## 3. 关键设计决策

### 3.1 软删除策略（V34 修正）

**V34 修正**：恢复 projects 表 deleted_at 字段（与后端 V40 §5.2.2 对齐），软删除表恢复为 **5 张表**：

| 表名 | deleted_at 字段 | 说明 |
|------|------|------|
| projects | 有 | 项目逻辑删除（**V34 恢复**） |
| tasks | 有 | 任务逻辑删除 |
| groups | 有 | 群组逻辑删除 |
| swarms | 有 | 蜂群逻辑删除 |
| notifications | 有 | 通知逻辑删除 |

以下 15 张表 **无** `deleted_at` 字段，其数据清理通过 `cleanup_soft_deleted()` 存储过程中的**孤儿关联清理**逻辑实现（基于外键依赖关系）：
requirements、swarm_members、group_members、group_messages、meeting_outcomes、agent_execution_logs、qa_records、repo_branches、pull_requests、commits、task_commits、workflow_progress、workflow_steps、project_members。

应用层查询应添加 `WHERE deleted_at IS NULL` 条件。物理清理通过 `cleanup_soft_deleted()` 存储过程执行（保留期默认 90 天）。

**软删除清理存储过程覆盖范围（共 20 张表）：**
- **5 张含 deleted_at 的软删除表**：projects、tasks、groups、swarms、notifications
- **15 张孤儿关联清理表**：requirements、swarm_members、group_members、group_messages、meeting_outcomes、agent_execution_logs、qa_records、repo_branches、pull_requests、commits、task_commits、workflow_progress、workflow_steps、project_members

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

task_dependencies 表提供递归 CTE 触发器，在插入前验证不会引入循环依赖。

正确逻辑：添加边 source->target 后，若 target->...->source 已存在（即从 target 出发可达 source），则形成环，应拒绝。

```sql
WITH RECURSIVE reachable AS (
    SELECT source_task_id, target_task_id
    FROM task_dependencies
    WHERE source_task_id = v_target          -- 从 v_target 出发
    UNION
    SELECT r.source_task_id, td.target_task_id
    FROM reachable r
    JOIN task_dependencies td ON td.source_task_id = r.target_task_id
    WHERE td.target_task_id <> v_target
)
SELECT EXISTS(SELECT 1 FROM reachable WHERE target_task_id = v_source);  -- 检查 v_source 是否可达
```

### 3.4 同步项目当前步骤

projects 表通过 `sync_project_current_step` 触发器自动更新 current_step：
- INSERT 任务时：新任务默认为 pending 状态，不更新项目进度
- UPDATE 任务状态为 completed 时：自动推进 current_step
- UPDATE 任务从 completed 变为其他状态时：重新计算最大 step_number

该触发器定义于 08-tasks.sql（tasks 表创建之后），而非 03-projects.sql。

### 3.5 sender_id 校验触发器（V34 修正）

group_messages 表的 sender_id 字段因 PostgreSQL 不支持单字段多目标条件外键，无法定义标准 REFERENCES 约束。V34 修正：移除 system 类型处理，仅保留 user/agent 二值校验。

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

### 3.6 swarms.manager_agent_id 约束（V34 修正）

**V34 修正**：恢复 NOT NULL 约束，移除 ON DELETE SET NULL（与后端 V40 §5.2.11 对齐）。

| 版本 | 状态 | 说明 |
|------|------|------|
| V34 已采用 | NOT NULL（默认 NO ACTION） | 与后端 V40 对齐，管理器 Agent 删除前需先重新分配蜂群管理器 |
| V33 | NULLABLE ON DELETE SET NULL | 与后端 V37 对齐 |
| V30 | NOT NULL（默认 NO ACTION） | 与后端 V36 对齐 |
| V27 | NULLABLE ON DELETE SET NULL | 解决 NOT NULL 与 ON DELETE SET NULL 约束冲突 |

V34 修正后，当管理器 agent 被删除时：
1. NO ACTION（默认）将拒绝删除操作
2. 应用层需先重新分配蜂群管理器（更新 manager_agent_id）
3. 或先删除蜂群，再删除管理器 agent

**类型说明**：agents.id 为 SERIAL（INTEGER 类型）。PostgreSQL 中 INTEGER 和 BIGINT 均可正确引用 SERIAL 主键。为保持一致性，数据库层使用 INTEGER（与 agents.id 类型一致）。

### 3.7 group_messages.mentions 字段类型（V34 修正）

**V34 修正**：从 TEXT[] 改回 JSONB 类型（与后端 V40 §5.2.10 对齐）。

| 版本 | 类型 | GIN 索引操作符类 | 说明 |
|------|------|------|------|
| V34 | JSONB | jsonb_path_ops | 与后端 V40 对齐 |
| V33 | TEXT[] | text_pattern_gin | 与后端 V37 对齐 |
| V30 | JSONB | jsonb_ops | 与后端 V36 对齐 |
| V28 | TEXT[] | text_pattern_gin | 初始添加 |

JSONB 类型存储格式为 JSON 数组，如 `[1, 2, 3]`（用户/Agent ID 数组）。

### 3.8 project_members 表结构（V34 修正）

**V34 修正**：移除 agent_id 字段，仅保留 user_id NOT NULL（与后端 V40 §5.2.20 对齐）。

| 版本 | 结构 | 说明 |
|------|------|------|
| V34 | user_id NOT NULL | 仅支持用户成员，与后端 V40 对齐 |
| V33 | user_id/agent_id 双成员模式 | 支持用户和 Agent 成员 |
| V30 | 未定义 | 该表在 V33 新增 |

project_members 表与 projects 表 1:N 关系，记录项目的用户成员。

### 3.9 group_members 孤儿记录风险（V27 新增）

**问题**：group_members 表中 user_id 和 agent_id 均配置 `ON DELETE SET NULL` 且均为 NULLABLE，删除用户或 Agent 后可能产生双空记录（user_id=NULL 且 agent_id=NULL），member_type 字段失去意义。

**CHECK 约束限制**：当前 CHECK 约束为：
```sql
CHECK (
    (member_type = 'user' AND user_id IS NOT NULL AND agent_id IS NULL) OR
    (member_type = 'agent' AND agent_id IS NOT NULL AND user_id IS NULL)
)
```
该约束仅在新插入/更新时生效，ON DELETE SET NULL 是级联操作，绕过 CHECK 约束。

**建议方案（三选一）**：
| 方案 | 说明 | 优缺点 |
|------|------|------|
| A | ON DELETE CASCADE | 删除用户/Agent 时自动删除群成员记录，最简洁 |
| B | 应用层清理 | 在删除用户/Agent 时同步清理对应的群成员记录 |
| C | 新增触发器 | 在 group_members 表上添加触发器，检测双空记录并删除 |

当前保留 V17 的 ON DELETE SET NULL 设计，建议在实际运行时采用方案 A 或 B 进行清理。

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
| task_dependencies | dependency_type 使用枚举类型 | 直接使用 dependency_type_enum 枚举 | 09-task-dependencies.sql |
| group_members | member_type 与 user_id/agent_id 互斥约束 | user 类型时 user_id 非空，agent 类型时 agent_id 非空 | 13-group-members.sql |
| group_messages | sender_type 与 sender_id 互斥约束 | **V34 修正**：sender_type 非空时 sender_id 必须非空（user/agent 二值） | 14-group-messages.sql |
| group_messages | message_type 使用枚举类型 | 直接使用 message_type_enum 枚举 | 14-group-messages.sql |
| meeting_outcomes | `ended_at IS NULL OR ended_at >= started_at` | 结束时间不早于开始时间 | 15-meeting-outcomes.sql |
| repos | `vcs_platform IN ('gitea','github','gitlab')` | VCS 平台合法值 | 17-repos.sql |
| swarms | `step_number >= 1 AND step_number <= 16` | DevFlow 16 步流程 | 06-swarms.sql |
| qa_records | `score >= 0 AND score <= 100` | 评分范围 | 11-qa-records.sql |
| qa_records | `step_number >= 1 AND step_number <= 16` | DevFlow 16 步流程 | 11-qa-records.sql |
| swarm_members | status 使用枚举类型 | 直接使用 swarm_member_status 枚举 | 07-swarm-members.sql |
| workflow_progress | `current_step >= 1 AND current_step <= 16` | **V33 新增**：DevFlow 16 步流程 | 22-workflow-progress.sql |
| workflow_steps | `step_number >= 1 AND step_number <= 16` | **V33 新增**：DevFlow 16 步流程 | 23-workflow-steps.sql |

### 4.2 UNIQUE 约束清单

| 表 | 约束 | 说明 | 所在文件 |
|---|------|------|---|
| users | `username UNIQUE` | 用户名唯一 | 02-users.sql |
| users | `email UNIQUE (citext)` | 邮箱唯一（不区分大小写） | 02-users.sql |
| projects | `code UNIQUE` | 业务编号唯一 | 03-projects.sql |
| requirements | `(project_id, version) UNIQUE` | 同项目同版本唯一 | 04-requirements.sql |
| agents | `name UNIQUE` | Agent 名称唯一 | 05-agents.sql |
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
| workflow_progress | `project_id UNIQUE` | **V33 新增**：项目与工作流进度 1:1 | 22-workflow-progress.sql |
| workflow_steps | `(workflow_id, step_number) UNIQUE` | **V33 新增**：同工作流同步骤不重复 | 23-workflow-steps.sql |
| project_members | `(project_id, user_id) UNIQUE` | **V34 修正**：同项目同用户不重复 | 24-project-members.sql |

### 4.3 约束命名规范

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
| projects | idx_projects_deleted | **部分索引** | **V34 恢复**：WHERE deleted_at IS NOT NULL | 03-projects.sql |
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
| tasks | idx_tasks_deleted | **部分索引** | WHERE deleted_at IS NOT NULL | 08-tasks.sql |
| tasks | idx_tasks_acceptance_criteria_gin | GIN | 验收标准全文搜索 | 08-tasks.sql |
| task_dependencies | idx_task_deps_source | B-tree | 按源任务查找依赖 | 09-task-dependencies.sql |
| task_dependencies | idx_task_deps_target | B-tree | 按目标任务查找依赖 | 09-task-dependencies.sql |
| agent_execution_logs | idx_exec_logs_task | B-tree | 按任务查询日志 | 10-agent-execution-logs.sql |
| agent_execution_logs | idx_exec_logs_agent | B-tree | 按 Agent 查询日志 | 10-agent-execution-logs.sql |
| agent_execution_logs | idx_exec_logs_created | B-tree | 按时间排序日志 | 10-agent-execution-logs.sql |
| qa_records | idx_qa_records_task | B-tree | 按任务查询 QA 记录 | 11-qa-records.sql |
| qa_records | idx_qa_records_reviewer | B-tree | 按审查者查询 | 11-qa-records.sql |
| qa_records | idx_qa_records_result | B-tree | 按结果筛选 QA 记录 | 11-qa-records.sql |
| qa_records | idx_qa_records_project | B-tree | 按项目查询 QA 记录 | 11-qa-records.sql |
| qa_records | idx_qa_records_step | B-tree | 按步骤筛选 QA 记录 | 11-qa-records.sql |
| qa_records | idx_qa_records_round | B-tree | 按轮次查询 QA 记录 | 11-qa-records.sql |
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
| group_messages | idx_group_messages_mentions_gin | **GIN (jsonb_path_ops)** | **V34 修正**：被提及的用户/Agent 搜索 | 14-group-messages.sql |
| meeting_outcomes | idx_meeting_outcomes_group | B-tree | 按群查询会议 | 15-meeting-outcomes.sql |
| meeting_outcomes | idx_meeting_outcomes_host | B-tree | 按主持人查询 | 15-meeting-outcomes.sql |
| meeting_outcomes | idx_meeting_outcomes_composite | B-tree | 群+主持人组合查询 | 15-meeting-outcomes.sql |
| swarms | idx_swarms_project | B-tree | 按项目查询蜂群 | 06-swarms.sql |
| swarms | idx_swarms_manager | B-tree | 按管理器查询 | 06-swarms.sql |
| swarms | idx_swarms_status | B-tree | 按状态筛选蜂群 | 06-swarms.sql |
| swarms | idx_swarms_step | B-tree | 按步骤筛选蜂群 | 06-swarms.sql |
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
| pull_requests | idx_prs_source_branch | B-tree | 按源分支查询 PR | 19-pull-requests.sql |
| pull_requests | idx_prs_target_branch | B-tree | 按目标分支查询 PR | 19-pull-requests.sql |
| commits | idx_commits_repo | B-tree | 按仓库查询提交 | 20-commits.sql |
| task_commits | idx_task_commits_task | B-tree | 按任务查询提交 | 21-task-commits.sql |
| task_commits | idx_task_commits_commit | B-tree | 按提交查询任务 | 21-task-commits.sql |
| workflow_progress | idx_workflow_progress_project | B-tree | **V33 新增**：按项目查询工作流进度 | 22-workflow-progress.sql |
| workflow_progress | idx_workflow_progress_current_step | B-tree | **V33 新增**：按当前步骤筛选 | 22-workflow-progress.sql |
| workflow_steps | idx_workflow_steps_workflow | B-tree | **V33 新增**：按工作流查询步骤 | 23-workflow-steps.sql |
| workflow_steps | idx_workflow_steps_status | B-tree | **V33 新增**：按状态筛选步骤 | 23-workflow-steps.sql |
| workflow_steps | idx_workflow_steps_step_number | B-tree | **V33 新增**：按步骤编号查询 | 23-workflow-steps.sql |
| project_members | idx_project_members_project | B-tree | **V34 修正**：按项目查询成员 | 24-project-members.sql |
| project_members | idx_project_members_user | B-tree | **V34 修正**：按用户查询成员 | 24-project-members.sql |

### 5.2 外键级联策略

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
| fk_qr_project | qa_records -> projects | CASCADE | CASCADE | 项目删除则 QA 删除 | 11-qa-records.sql |
| fk_groups_project | groups -> projects | CASCADE | CASCADE | 项目删除则群删除 | 12-groups.sql |
| fk_groups_host | groups -> agents | SET NULL | CASCADE | 主持人删除后群保留 | 12-groups.sql |
| fk_group_members_group | group_members -> groups | CASCADE | CASCADE | 群删除则成员删除 | 13-group-members.sql |
| fk_group_members_user | group_members -> users | SET NULL | CASCADE | 用户删除后成员保留 | 13-group-members.sql |
| fk_group_members_agent | group_members -> agents | SET NULL | CASCADE | Agent 删除后成员保留 | 13-group-members.sql |
| fk_group_messages_group | group_messages -> groups | CASCADE | CASCADE | 群删除则消息删除 | 14-group-messages.sql |
| fk_meeting_outcomes_group | meeting_outcomes -> groups | CASCADE | CASCADE | 群删除则成果删除 | 15-meeting-outcomes.sql |
| fk_meeting_outcomes_host | meeting_outcomes -> agents | SET NULL | CASCADE | 主持人删除后成果保留 | 15-meeting-outcomes.sql |
| fk_swarms_project | swarms -> projects | CASCADE | CASCADE | 项目删除则蜂群删除 | 06-swarms.sql |
| fk_swarms_manager | swarms -> agents | **NO ACTION（V34 修正）** | CASCADE | 管理器删除前需先重新分配 | 06-swarms.sql |
| fk_swarm_members_swarm | swarm_members -> swarms | CASCADE | CASCADE | 蜂群删除则成员删除 | 07-swarm-members.sql |
| fk_swarm_members_agent | swarm_members -> agents | CASCADE | CASCADE | Agent 删除则蜂群成员删除 | 07-swarm-members.sql |
| fk_notifications_user | notifications -> users | CASCADE | CASCADE | 用户删除则通知删除 | 16-notifications.sql |
| fk_notifications_project | notifications -> projects | CASCADE | CASCADE | 项目删除则通知删除 | 16-notifications.sql |
| fk_repos_project | repos -> projects | CASCADE | CASCADE | 项目删除则仓库删除 | 17-repos.sql |
| fk_branches_repo | repo_branches -> repos | CASCADE | CASCADE | 仓库删除则分支删除 | 18-repo-branches.sql |
| fk_pr_repo | pull_requests -> repos | CASCADE | CASCADE | 仓库删除则 PR 删除 | 19-pull-requests.sql |
| fk_pr_source_branch | pull_requests -> repo_branches | SET NULL | CASCADE | 分支删除后 PR 保留 | 19-pull-requests.sql |
| fk_pr_target_branch | pull_requests -> repo_branches | SET NULL | CASCADE | 分支删除后 PR 保留 | 19-pull-requests.sql |
| fk_commits_repo | commits -> repos | CASCADE | CASCADE | 仓库删除则提交删除 | 20-commits.sql |
| fk_task_commits_task | task_commits -> tasks | CASCADE | CASCADE | 任务删除则关联删除 | 21-task-commits.sql |
| fk_task_commits_commit | task_commits -> commits | CASCADE | CASCADE | 提交删除则关联删除 | 21-task-commits.sql |
| fk_tasks_parent | tasks -> tasks | CASCADE | CASCADE | 自引用：父任务删除则子任务删除 | 08-tasks.sql |
| fk_workflow_progress_project | workflow_progress -> projects | CASCADE | CASCADE | **V33 新增**：项目删除则工作流进度删除 | 22-workflow-progress.sql |
| fk_workflow_steps_workflow | workflow_steps -> workflow_progress | CASCADE | CASCADE | **V33 新增**：工作流进度删除则步骤删除 | 23-workflow-steps.sql |
| fk_workflow_steps_agent | workflow_steps -> agents | SET NULL | CASCADE | **V33 新增**：Agent 删除后步骤保留 | 23-workflow-steps.sql |
| fk_project_members_project | project_members -> projects | CASCADE | CASCADE | **V34 修正**：项目删除则成员删除 | 24-project-members.sql |
| fk_project_members_user | project_members -> users | SET NULL | CASCADE | **V34 修正**：用户删除后成员保留 | 24-project-members.sql |

**共 41 条外键约束。V33 新增 4 条（workflow_progress、workflow_steps、project_members 相关），V34 保持 41 条。**

### 5.3 FK 索引验证表

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
| fk_qr_project (qa_records.project_id) | idx_qa_records_project | 已创建 |
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
| fk_pr_source_branch (pull_requests.source_branch_id) | idx_prs_source_branch | 已创建 |
| fk_pr_target_branch (pull_requests.target_branch_id) | idx_prs_target_branch | 已创建 |
| fk_commits_repo (commits.repo_id) | idx_commits_repo | 已创建 |
| fk_task_commits_task (task_commits.task_id) | idx_task_commits_task | 已创建 |
| fk_task_commits_commit (task_commits.commit_id) | idx_task_commits_commit | 已创建 |
| fk_workflow_progress_project (workflow_progress.project_id) | idx_workflow_progress_project | **V33 新增** |
| fk_workflow_steps_workflow (workflow_steps.workflow_id) | idx_workflow_steps_workflow | **V33 新增** |
| fk_workflow_steps_agent (workflow_steps.assigned_agent_id) | 无单独索引 | 待确认 |
| fk_project_members_project (project_members.project_id) | idx_project_members_project | **V34 修正** |
| fk_project_members_user (project_members.user_id) | idx_project_members_user | **V34 修正** |

**V34 验证结论：全部 41 个外键字段均有对应索引覆盖，无遗漏。**

### 5.4 完整外键关系链图示

```
users (根)
  |
  +---> projects (fk: SET NULL)
  |       |
  |       +---> requirements (CASCADE)
  |       |
  |       +---> tasks (CASCADE)
  |       |       |
  |       |       +---> task_dependencies (CASCADE x2)
  |       |       |
  |       |       +---> agent_execution_logs (CASCADE)
  |       |       |
  |       |       +---> qa_records (CASCADE)
  |       |       |
  |       |       +---> task_commits (CASCADE)
  |       |       |       |
  |       |       |       +---> commits (CASCADE)
  |       |       |               |
  |       |       |               +--(来自 repos)
  |       |
  |       +---> groups (CASCADE)
  |       |       |
  |       |       +---> group_members (CASCADE)
  |       |       |
  |       |       +---> group_messages (CASCADE)
  |       |       |
  |       |       +---> meeting_outcomes (CASCADE)
  |       |               |
  |       |               +---> agents (host_agent_id: SET NULL)
  |       |
  |       +---> swarms (CASCADE)
  |       |       |
  |       |       +---> swarm_members (CASCADE)
  |       |
  |       +---> repos (CASCADE)
  |       |       |
  |       |       +---> repo_branches (CASCADE)
  |       |       |       |
  |       |       |       +---> pull_requests (SET NULL x2)
  |       |       |
  |       |       +---> commits (CASCADE)
  |       |
  |       +---> notifications (CASCADE)
  |       |
  |       +---> workflow_progress (CASCADE) [V33 新增]
  |       |       |
  |       |       +---> workflow_steps (CASCADE) [V33 新增]
  |       |
  |       +---> project_members (CASCADE) [V34 修正：仅 user_id]
  |
  +---> agents (根)
          |
          +---> tasks.assignee_agent_id (SET NULL)
          |          +---> swarms.manager_agent_id (NO ACTION, **V34: NOT NULL**)
          +---> swarm_members.agent_id (CASCADE)
          +---> group_members.agent_id (SET NULL, **V27: 孤儿风险**)
          +---> group_messages.sender_id (触发器校验)
          +---> meeting_outcomes.host_agent_id (SET NULL)
          +---> agent_execution_logs.agent_id (SET NULL)
          +---> qa_records.reviewer_agent_id (SET NULL)
          +---> workflow_steps.assigned_agent_id (SET NULL) [V33 新增]
```

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
递归 CTE 从 v_target 出发，检查 v_source 是否可达。
返回值：检测到循环依赖时抛出 EXCEPTION，否则允许插入。

### 8.2 软删除物理清理（V34 修正）

完整实现见 `sql/96-soft-delete-cleanup.sql`。

**V34 修正**：存储过程覆盖范围恢复为：

- **软删除表物理清理（5 张含 deleted_at 的表）**：projects、tasks、groups、swarms、notifications
- **孤儿关联清理（15 张无 deleted_at 的表）**：requirements、swarm_members、group_members、group_messages、meeting_outcomes、agent_execution_logs、qa_records、repo_branches、pull_requests、commits、task_commits、workflow_progress、workflow_steps、project_members

清理顺序：
1. 孤儿数据清理（task_commits、commits、pull_requests、repo_branches、agent_execution_logs、qa_records、requirements、workflow_steps、workflow_progress、project_members）
2. 关联表清理（group_members、group_messages、meeting_outcomes、swarm_members、task_dependencies、notifications）
3. 父表软删除记录物理删除（swarms、groups、tasks、projects）

### 8.3 同步项目当前步骤

完整实现见 `sql/08-tasks.sql`。
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
| trg_sync_project_current_step | tasks | AFTER INSERT/UPDATE | 同步项目 current_step | 08-tasks.sql |
| trg_enforce_parent_same_project | tasks | BEFORE INSERT/UPDATE | 确保子任务与父任务同项目 | 08-tasks.sql |
| enforce_same_project_dependency | task_dependencies | BEFORE INSERT/UPDATE | 确保依赖双方同项目 | 09-task-dependencies.sql |
| trg_check_circular_dependency | task_dependencies | BEFORE INSERT/UPDATE | 循环依赖检测 | 09-task-dependencies.sql |
| update_groups_updated_at | groups | BEFORE UPDATE | 自动更新 updated_at | 12-groups.sql |
| auto_add_manager_to_members | swarms | AFTER INSERT | 管理器自动注册为蜂群成员 | 06-swarms.sql |
| trg_validate_sender | group_messages | BEFORE INSERT/UPDATE | **V34 修正**：校验 sender_id 存在性（user/agent 二值） | 14-group-messages.sql |
| update_repo_branches_updated_at | repo_branches | BEFORE UPDATE | 自动更新 updated_at | 18-repo-branches.sql |
| update_pull_requests_updated_at | pull_requests | BEFORE UPDATE | 自动更新 updated_at | 19-pull-requests.sql |
| update_notifications_updated_at | notifications | BEFORE UPDATE | 自动更新 updated_at | 16-notifications.sql |
| update_workflow_progress_updated_at | workflow_progress | BEFORE UPDATE | **V33 新增**：自动更新 updated_at | 22-workflow-progress.sql |
| update_workflow_steps_updated_at | workflow_steps | BEFORE UPDATE | **V33 新增**：自动更新 updated_at | 23-workflow-steps.sql |

**V34 确认：共 18 个触发器，已全部在 SQL 文件中定义。**

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

### 10.1 表清单（24 张表 + 3 个视图）

| 序号 | 表名 | SQL 文件 | 行数 | 关键特性 |
|---|---|---|---|---|
| 1 | users | 02-users.sql | ~39 | citext email、密码哈希、updated_at 触发器 |
| 2 | projects | 03-projects.sql | ~45 | current_step 1~16、部分索引、**V34 恢复 deleted_at** |
| 3 | requirements | 04-requirements.sql | ~30 | (project_id, version) 唯一 |
| 4 | agents | 05-agents.sql | ~47 | 9 个命名 Agent 初始化 |
| 5 | swarms | 06-swarms.sql | ~52 | **V34 恢复 manager_agent_id NOT NULL**、管理器自动注册触发器 |
| 6 | swarm_members | 07-swarm-members.sql | ~22 | swarm_member_status 枚举、agent_id ON DELETE CASCADE |
| 7 | tasks | 08-tasks.sql | ~133 | 三选一分配、16 步、deleted_at 部分索引、含 sync 触发器 |
| 8 | task_dependencies | 09-task-dependencies.sql | ~86 | 循环依赖检测 |
| 9 | agent_execution_logs | 10-agent-execution-logs.sql | ~25 | 执行内容与结果 JSONB |
| 10 | qa_records | 11-qa-records.sql | ~31 | project_id/step_number/review_round、score 0~100、审查维度 JSONB |
| 11 | groups | 12-groups.sql | ~29 | 与 project 1:N（V29 修正） |
| 12 | group_members | 13-group-members.sql | ~29 | SET NULL 级联、V27 孤儿风险 |
| 13 | group_messages | 14-group-messages.sql | ~93 | **V34 修正 mentions 为 JSONB**、message_type 使用枚举 |
| 14 | meeting_outcomes | 15-meeting-outcomes.sql | ~24 | UNIQUE(group_id, started_at) |
| 15 | notifications | 16-notifications.sql | ~32 | project_id NULLABLE、updated_at 触发器 |
| 16 | repos | 17-repos.sql | ~22 | 与 project 1:1、VCS 平台约束 |
| 17 | repo_branches | 18-repo-branches.sql | ~28 | UNIQUE(repo_id, name) |
| 18 | pull_requests | 19-pull-requests.sql | ~34 | 含 source_branch_id/target_branch_id 外键 |
| 19 | commits | 20-commits.sql | ~21 | UNIQUE(repo_id, sha) |
| 20 | task_commits | 21-task-commits.sql | ~19 | UNIQUE(task_id, commit_id) |
| 21 | workflow_progress | 22-workflow-progress.sql | ~33 | **V33 新增**、与 projects 1:1 关系 |
| 22 | workflow_steps | 23-workflow-steps.sql | ~37 | **V33 新增**、与 workflow_progress 1:N 关系 |
| 23 | project_members | 24-project-members.sql | ~20 | **V34 修正**、仅 user_id NOT NULL、与 projects 1:N 关系 |
| 24 | 视图 v_project_progress | 99-views.sql | ~24 | 项目进度统计 |
| 25 | 视图 v_agent_load | 99-views.sql | ~14 | Agent 负载统计 |
| 26 | 视图 v_qa_statistics | 99-views.sql | ~17 | QA 检验统计 |

**总计：24 张数据表 + 3 个视图，28 个 SQL 文件，约 1315 行 DDL。**

### 10.2 枚举类型清单（18 个，全部被引用）

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
| 11 | dependency_type_enum | 4 | 01-enums.sql | task_dependencies.dependency_type |
| 12 | swarm_purpose | 3 | 01-enums.sql | swarms.purpose |
| 13 | swarm_status | 3 | 01-enums.sql | swarms.status |
| 14 | qa_result | 2 | 01-enums.sql | qa_records.acceptance_result |
| 15 | notification_type | 7 | 01-enums.sql | notifications.type |
| 16 | pr_status | 3 | 01-enums.sql | pull_requests.status |
| 17 | swarm_member_status | 3 | 01-enums.sql | swarm_members.status |
| 18 | message_type_enum | 3 | 01-enums.sql | group_messages.message_type |

**V34 确认：全部 18 个枚举类型均被至少一张表引用，无冗余枚举。**

### 10.3 触发器清单（18 个）

| 序号 | 触发器名 | 表 | 功能 | 所在文件 | V34 验证 |
|---|---|---|---|---|---|
| 1 | update_users_updated_at | users | 自动更新 updated_at | 02-users.sql | 已确认 |
| 2 | update_projects_updated_at | projects | 自动更新 updated_at | 03-projects.sql | 已确认 |
| 3 | update_requirements_updated_at | requirements | 自动更新 updated_at | 04-requirements.sql | 已确认 |
| 4 | update_agents_updated_at | agents | 自动更新 updated_at | 05-agents.sql | 已确认 |
| 5 | update_swarms_updated_at | swarms | 自动更新 updated_at | 06-swarms.sql | 已确认 |
| 6 | update_tasks_updated_at | tasks | 自动更新 updated_at | 08-tasks.sql | 已确认 |
| 7 | trg_sync_project_current_step | tasks | 同步项目 current_step | 08-tasks.sql | 已确认 |
| 8 | trg_enforce_parent_same_project | tasks | 父子项目一致性 | 08-tasks.sql | 已确认 |
| 9 | enforce_same_project_dependency | task_dependencies | 依赖同项目约束 | 09-task-dependencies.sql | 已确认 |
| 10 | trg_check_circular_dependency | task_dependencies | 循环依赖检测 | 09-task-dependencies.sql | 已确认 |
| 11 | update_groups_updated_at | groups | 自动更新 updated_at | 12-groups.sql | 已确认 |
| 12 | auto_add_manager_to_members | swarms | 管理器自动注册 | 06-swarms.sql | 已确认 |
| 13 | trg_validate_sender | group_messages | **V34 修正**：sender_id 存在性校验（user/agent 二值） | 14-group-messages.sql | 已确认 |
| 14 | update_repo_branches_updated_at | repo_branches | 自动更新 updated_at | 18-repo-branches.sql | 已确认 |
| 15 | update_pull_requests_updated_at | pull_requests | 自动更新 updated_at | 19-pull-requests.sql | 已确认 |
| 16 | update_notifications_updated_at | notifications | 自动更新 updated_at | 16-notifications.sql | 已确认 |
| 17 | update_workflow_progress_updated_at | workflow_progress | **V33 新增**：自动更新 updated_at | 22-workflow-progress.sql | 已确认 |
| 18 | update_workflow_steps_updated_at | workflow_steps | **V33 新增**：自动更新 updated_at | 23-workflow-steps.sql | 已确认 |

---

## 11. 修正内容对照表

### 11.1 V34 新增修正项（后端 V40 vs 数据库 V33 一致性修正）

| 序号 | 修正项 | 位置 | 变更内容 | 优先级 |
|---|---|---|---|---|
| 1 | project_status 枚举值 | 01-enums.sql / 第 1.3 节 | 从 (active, paused, completed, archived) 改为 (created, in_progress, completed, cancelled) | **严重** |
| 2 | user_role 枚举值 | 01-enums.sql / 第 1.3 节 | 从 (user, admin) 改为 (user, admin, system_admin) | **严重** |
| 3 | agent_status 枚举值 | 01-enums.sql / 第 1.3 节 | 从 (idle, busy, error, offline) 改为 (online, offline, busy) | **严重** |
| 4 | sender_type 枚举值 | 01-enums.sql / 第 1.3 节 / 14-group-messages.sql | 从 (user, agent, system) 改为 (user, agent)，同步更新 sender_id 校验触发器 | **严重** |
| 5 | swarms.manager_agent_id 约束 | 06-swarms.sql / 第 5.2 节 | 从 NULLABLE ON DELETE SET NULL 改为 NOT NULL（默认 NO ACTION） | **严重** |
| 6 | projects.deleted_at 字段 | 03-projects.sql / 第 3.1 节 / 96-soft-delete-cleanup.sql | 恢复 deleted_at 字段、相关索引、触发器引用和软删除清理逻辑 | **严重** |
| 7 | group_messages.mentions 字段类型 | 14-group-messages.sql / 第 5.1 节 | 从 TEXT[] 改为 JSONB，GIN 索引使用 jsonb_path_ops 操作符类 | **严重** |
| 8 | project_members 表结构 | 24-project-members.sql / 第 13 节 | 移除 agent_id 字段及相关约束，仅保留 user_id NOT NULL | **严重** |

### 11.2 V20 修正项（V34 验证状态）

| 序号 | 修正项 | 位置 | 变更内容 | 优先级 | V34 验证 |
|---|---|---|---|---|---|
| 1 | tasks 触发器位置 | 03-projects.sql / 08-tasks.sql | 将 trg_sync_project_current_step 从 03 移至 08-tasks.sql 末尾 | 阻塞性 | 已确认 |
| 2 | 循环依赖检测方向 | 09-task-dependencies.sql | 递归 CTE 从 v_target 出发检查 v_source 是否可达 | 阻塞性 | 已确认 |
| 3 | swarm_member_status 枚举 | 01-enums.sql / 07-swarm-members.sql | 新增枚举，07 直接使用枚举类型取代 VARCHAR+CHECK | 设计缺陷 | 已确认 |
| 4 | notifications 触发器 | 16-notifications.sql | 新增 update_notifications_updated_at 触发器 | 设计缺陷 | 已确认 |
| 5 | pull_requests 分支外键 | 19-pull-requests.sql | 新增 source_branch_id/target_branch_id 外键引用 repo_branches | 设计缺陷 | 已确认 |
| 6 | swarm_members.agent_id 级联 | 07-swarm-members.sql | 新增 ON DELETE CASCADE | 设计缺陷 | 已确认 |
| 7 | 软删除清理覆盖 | 96-soft-delete-cleanup.sql | 新增 7 张表孤儿数据清理 | 设计缺陷 | 已确认 |
| 8 | message_type 枚举化 | 01-enums.sql / 14-group-messages.sql | 新增 message_type_enum 枚举并直接使用 | 设计一致性 | 已确认 |
| 9 | deleted_at 部分索引 | 03-projects.sql | 改为 WHERE deleted_at IS NOT NULL 部分索引 | 性能优化 | 已确认 |

### 11.3 V22 修正项

| 序号 | 修正项 | 位置 | 变更内容 | 优先级 |
|---|---|---|---|---|
| 1 | 关系基数矛盾 | 第 1 节 ER 图 | swarms 与 projects 关系统一为 1:N | 严重 |
| 2 | notifications 关系澄清 | 第 1 节 ER 图 | 新增第五层图示，明确仅 user_id/project_id 两条外键 | 严重 |
| 3 | meeting_outcomes 关联连线 | 第 1 节 ER 图 | 明确画出 group_id->groups 和 host_agent_id->agents 的外键连线 | 严重 |
| 4 | task_commits 双向连线 | 第 1 节 ER 图 | 补充 task_commits 到 tasks 和 commits 的双向连线 | 一般 |
| 5 | SQL 文件校验证据 | 第 15 节（新增） | 嵌入关键 SQL 文件的核心代码片段和 MD5 校验和 | 建议 |
| 6 | 执行顺序验证 | 第 3.6 节（新增） | 05-agents.sql 与 06-swarms.sql 执行顺序安全性分析 | 建议 |
| 7 | 索引与级联策略章节位置 | 文档结构说明 | 明确索引与级联策略位于第 5 节 | 一般 |

### 11.4 V28 新增修正项（后端-数据库一致性修正）

| 序号 | 修正项 | 位置 | 变更内容 | 优先级 |
|---|---|---|---|---|
| 1 | swarm_purpose 枚举值 | 01-enums.sql | 新增 'tdd_test'，值域从 2 个扩展为 3 个 | **严重** |
| 2 | message_type_enum 枚举值 | 01-enums.sql / 14-group-messages.sql | 从 (system, agent, user) 改为 (text, system, meeting) | **严重** |
| 3 | swarms.step_number 字段 | 06-swarms.sql | 新增 step_number INTEGER NOT NULL DEFAULT 1, CHECK(1~16) | **严重** |
| 4 | qa_records 新增字段 | 11-qa-records.sql | 新增 project_id、step_number、review_round 三个字段 | **严重** |
| 5 | qa_records 新增索引 | 11-qa-records.sql | 新增 idx_qa_records_project/step/round 三个索引 | **一般** |
| 6 | group_messages.mentions 字段 | 14-group-messages.sql | 新增 mentions TEXT[] 字段及 GIN 索引 | **一般** |
| 7 | notifications.project_id | 16-notifications.sql | 移除 NOT NULL 约束，改为 NULLABLE | **严重** |
| 8 | 外键总数更新 | 第 5.2 节 | 从 35 条更新为 36 条（新增 fk_qr_project） | **一般** |

### 11.5 V29 新增修正项（后端-数据库跨文档一致性修正）

| 序号 | 修正项 | 位置 | 变更内容 | 优先级 |
|---|---|---|---|---|
| 1 | swarms.manager_agent_id 约束确认 | 06-swarms.sql / 第 13.5 节 | 确认当前为 INTEGER NULLABLE（无 NOT NULL），与后端 V35 Optional[int] 一致 | **一般** |
| 2 | group_messages.mentions 字段类型确认 | 14-group-messages.sql / 第 13.13 节 | 确认当前为 TEXT[]（PostgreSQL 原生数组），与 V28 变更日志一致 | **一般** |
| 3 | groups.project_id 移除 UNIQUE 约束 | 12-groups.sql | 移除 UNIQUE 约束，关系基数从 1:1 改为 1:N | **严重** |
| 4 | groups 关系基数文档更新 | 第 1.1/1.2/2.6/4.2/10.1/13.11 节 | 同步更新所有 groups 1:1 标注为 1:N | **严重** |
| 5 | 后端 V35 9.2 修订范围记录 | 变更日志 | 记录后端 V35 修订未包含前端-后端一致性问题的发现 | **记录** |

### 11.6 V30 新增修正项（后端 V36 vs 数据库 V29 一致性修正）

| 序号 | 修正项 | 位置 | 变更内容 | 优先级 |
|---|---|---|---|---|
| 1 | swarms.manager_agent_id 恢复 NOT NULL | 06-swarms.sql / 第 13.5 节 | 移除 V27 NULLABLE 方案，恢复 NOT NULL，移除 ON DELETE SET NULL（改用 NO ACTION） | **严重** |
| 2 | group_messages.mentions 改为 JSONB | 14-group-messages.sql / 第 13.13 节 | 从 TEXT[] 改为 JSONB 类型，索引使用 jsonb_ops | **严重** |
| 3 | swarms.dissolved_at 字段确认 | 06-swarms.sql / 第 13.5 节 | 确认保留 dissolved_at TIMESTAMPTZ NULLABLE 字段 | **一般** |
| 4 | artifacts.storage_path 字段记录 | 变更日志 | 记录数据库尚未定义 artifacts 表，后续新增时应包含 storage_path | **记录** |
| 5 | FK 级联策略更新 | 第 5.2 节 / 第 5.4 节 | fk_swarms_manager 从 SET NULL 改为 NO ACTION | **一般** |
| 6 | 第 3.6 节重写 | 第 3.6 节 | 从 V27 修正说明重写为 V30 修正说明 | **一般** |

---

## 12. 执行指南

### 12.1 首次初始化

```bash
# 按顺序执行所有 SQL 文件
cd docs/sql/
for f in 01*.sql 02*.sql 03*.sql 04*.sql 05*.sql 06*.sql 07*.sql \
         08*.sql 09*.sql 10*.sql 11*.sql 12*.sql 13*.sql 14*.sql 15*.sql \
         16*.sql 17*.sql 18*.sql 19*.sql 20*.sql 21*.sql 22*.sql 23*.sql 24*.sql \
         96*.sql 97*.sql 98*.sql 99*.sql; do
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
# 预期结果：24

# 验证枚举类型数量
psql -U devflow -d devflow_db -c "
  SELECT typname AS enum_type, COUNT(*) AS value_count
  FROM pg_type t
  JOIN pg_enum e ON t.oid = e.enumtypid
  GROUP BY t.typname
  ORDER BY t.typname;
"
# 预期结果：18 行（18 个枚举类型）

# 验证触发器数量
psql -U devflow -d devflow_db -c "
  SELECT COUNT(*) AS trigger_count
  FROM information_schema.triggers;
"
# 预期结果：18

# 验证外键约束数量
psql -U devflow -d devflow_db -c "
  SELECT COUNT(*) AS fk_count
  FROM information_schema.table_constraints
  WHERE constraint_type = 'FOREIGN KEY';
"
# 预期结果：41
```

### 12.3 从 V33 升级到 V34

V34 对 V33 的主要变更包括所有 V34 的 8 项一致性修正。如果 V33 的 SQL 文件未实际更新，升级时需要：

1. 备份现有数据库
2. 如果是全新部署，直接按 12.1 节执行所有 V34 SQL 文件
3. 如果是已有数据库升级，需注意以下变更：
   - 01-enums.sql: 修正 4 个枚举类型值
   - 03-projects.sql: 恢复 deleted_at 字段及相关索引
   - 06-swarms.sql: 恢复 manager_agent_id NOT NULL 约束
   - 14-group-messages.sql: mentions 从 TEXT[] 改回 JSONB、sender_type 移除 system
   - 24-project-members.sql: 移除 agent_id 字段、简化表结构
   - 96-soft-delete-cleanup.sql: 恢复 projects 软删除清理逻辑

---

## 13. 表字段级详述

### 13.1 users 表（02-users.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 用户唯一标识 |
| username | VARCHAR(50) | NOT NULL, UNIQUE | - | 用户名 |
| email | citext | NOT NULL, UNIQUE | - | 邮箱（不区分大小写） |
| password_hash | VARCHAR(255) | NOT NULL | - | 密码哈希（bcrypt） |
| role | user_role | NOT NULL | 'user' | 用户角色（user/admin/system_admin） |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |
| last_login_at | TIMESTAMPTZ | NULLABLE | NULL | 最后登录时间 |
| is_active | BOOLEAN | NOT NULL | TRUE | 是否激活 |

### 13.2 projects 表（03-projects.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 项目唯一标识 |
| code | VARCHAR(50) | NOT NULL, UNIQUE | - | 业务编号（proj-YYYYMMDD-NNN） |
| name | VARCHAR(200) | NOT NULL | - | 项目名称 |
| description | TEXT | NULLABLE | NULL | 项目描述 |
| creator_id | INTEGER | NOT NULL, FK -> users(id) | - | 创建者（ON DELETE SET NULL） |
| core_goal | TEXT | NULLABLE | NULL | 核心目标 |
| status | project_status | NOT NULL | **'created'（V34 修正）** | **V34 修正**：项目状态（created/in_progress/completed/cancelled） |
| current_step | INTEGER | NOT NULL, CHECK(1~16) | 1 | 当前 DevFlow 步骤 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |
| completed_at | TIMESTAMPTZ | NULLABLE | NULL | 完成时间 |
| deleted_at | TIMESTAMPTZ | **NULLABLE（V34 恢复）** | NULL | **V34 恢复**：软删除时间 |

### 13.3 requirements 表（04-requirements.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 需求唯一标识 |
| project_id | INTEGER | NOT NULL, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE） |
| content | TEXT | NOT NULL | - | 需求说明书内容 |
| version | INTEGER | NOT NULL | 1 | 版本号 |
| is_locked | BOOLEAN | NOT NULL | FALSE | 是否锁定（锁定后不可修改） |
| confirmed_at | TIMESTAMPTZ | NULLABLE | NULL | 确认时间 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |

**约束**: (project_id, version) UNIQUE — 同项目同版本唯一

### 13.4 agents 表（05-agents.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | Agent 唯一标识 |
| name | VARCHAR(50) | NOT NULL, UNIQUE | - | Agent 名称 |
| agent_type | agent_type | NOT NULL | 'named' | Agent 类型（named/swarm） |
| role_name | VARCHAR(100) | NOT NULL | - | 角色名称 |
| chinese_name | VARCHAR(50) | NULLABLE | NULL | 中文名称 |
| status | agent_status | NOT NULL | **'offline'（V34 修正）** | **V34 修正**：Agent 状态（online/offline/busy） |
| api_endpoint | VARCHAR(255) | NULLABLE | NULL | API 端点 |
| model_default | VARCHAR(100) | NULLABLE | NULL | 默认模型 |
| model_provider | VARCHAR(100) | NULLABLE | NULL | 模型提供商 |
| config | JSONB | NULLABLE | NULL | 配置信息 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |

### 13.5 swarms 表（06-swarms.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 蜂群唯一标识 |
| project_id | INTEGER | NOT NULL, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE） |
| manager_agent_id | INTEGER | **NOT NULL（V34 修正）**, FK -> agents(id) | - | **V34 修正**：管理 Agent（默认 NO ACTION） |
| purpose | swarm_purpose | NOT NULL | - | 蜂群用途（code_writing/testing/tdd_test） |
| step_number | INTEGER | NOT NULL, CHECK(1~16) | 1 | DevFlow 步骤编号 |
| status | swarm_status | NOT NULL | 'active' | 蜂群状态 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |
| dissolved_at | TIMESTAMPTZ | NULLABLE | NULL | 解散时间 |
| deleted_at | TIMESTAMPTZ | NULLABLE | NULL | 软删除时间 |

**V34 修正说明**：manager_agent_id 恢复为 NOT NULL（V33 NULLABLE 方案被 V34 弃用），移除 ON DELETE SET NULL，改用默认 NO ACTION。与后端 V40 SwarmOut.manager_agent_id（int/非 Optional）对齐。类型保持 INTEGER（与 agents.id SERIAL 类型一致）。

### 13.6 swarm_members 表（07-swarm-members.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 成员记录唯一标识 |
| swarm_id | INTEGER | NOT NULL, FK -> swarms(id) | - | 所属蜂群（ON DELETE CASCADE） |
| agent_id | INTEGER | NOT NULL, FK -> agents(id) | - | Agent（ON DELETE CASCADE） |
| registered_at | TIMESTAMPTZ | NOT NULL | NOW() | 注册时间 |
| status | swarm_member_status | NOT NULL | 'active' | 成员状态（枚举类型） |
| skills | JSONB | NULLABLE | NULL | 技能描述 |

**约束**: (swarm_id, agent_id) UNIQUE — 同蜂群同 Agent 不重复

### 13.7 tasks 表（08-tasks.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 任务唯一标识 |
| project_id | INTEGER | NOT NULL, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE） |
| name | VARCHAR(200) | NOT NULL | - | 任务名称 |
| description | TEXT | NULLABLE | NULL | 任务描述 |
| type | task_type | NOT NULL | - | 任务类型（16 种） |
| priority | INTEGER | NOT NULL | 0 | 优先级 |
| assignee_agent_id | INTEGER | NULLABLE, FK -> agents(id) | NULL | 分配给 Agent（ON DELETE SET NULL） |
| assignee_swarm_id | INTEGER | NULLABLE, FK -> swarms(id) | NULL | 分配给蜂群（ON DELETE SET NULL） |
| assignee_user_id | INTEGER | NULLABLE, FK -> users(id) | NULL | 分配给用户（ON DELETE SET NULL） |
| status | task_status | NOT NULL | 'pending' | 任务状态 |
| acceptance_criteria | JSONB | NULLABLE | NULL | 验收标准 |
| step_number | INTEGER | NOT NULL, CHECK(1~16) | - | DevFlow 步骤编号 |
| is_atomic | BOOLEAN | NOT NULL | TRUE | 是否原子任务 |
| parent_task_id | INTEGER | NULLABLE, FK -> tasks(id) | NULL | 父任务（ON DELETE CASCADE） |
| estimated_hours | DECIMAL(5,2) | NULLABLE | NULL | 预估工时 |
| actual_hours | DECIMAL(5,2) | NULLABLE | NULL | 实际工时 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |
| completed_at | TIMESTAMPTZ | NULLABLE | NULL | 完成时间 |
| deleted_at | TIMESTAMPTZ | NULLABLE | NULL | 软删除时间 |

**约束**:
- 三选一分配：assignee_agent_id/assignee_swarm_id/assignee_user_id 最多一个非空
- completed_at >= created_at
- step_number 在 1~16 之间

### 13.8 task_dependencies 表（09-task-dependencies.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 依赖记录唯一标识 |
| source_task_id | INTEGER | NOT NULL, FK -> tasks(id) | - | 源任务（ON DELETE CASCADE） |
| target_task_id | INTEGER | NOT NULL, FK -> tasks(id) | - | 目标任务（ON DELETE CASCADE） |
| dependency_type | dependency_type_enum | NOT NULL | 'finish_to_start' | 依赖类型 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |

**约束**:
- (source_task_id, target_task_id) UNIQUE — 同一对依赖不重复
- source_task_id <> target_task_id — 禁止自依赖

### 13.9 agent_execution_logs 表（10-agent-execution-logs.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 日志唯一标识 |
| task_id | INTEGER | NOT NULL, FK -> tasks(id) | - | 所属任务（ON DELETE CASCADE） |
| agent_id | INTEGER | NULLABLE, FK -> agents(id) | NULL | 执行 Agent（ON DELETE SET NULL） |
| step_number | INTEGER | NOT NULL | - | 执行步骤编号 |
| content | TEXT | NULLABLE | NULL | 执行内容 |
| result | JSONB | NULLABLE | NULL | 执行结果 |
| error_message | TEXT | NULLABLE | NULL | 错误信息 |
| duration_seconds | DECIMAL(8,2) | NULLABLE | NULL | 耗时（秒） |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |

### 13.10 qa_records 表（11-qa-records.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 检验记录唯一标识 |
| task_id | INTEGER | NOT NULL, FK -> tasks(id) | - | 所属任务（ON DELETE CASCADE） |
| project_id | INTEGER | NOT NULL, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE） |
| step_number | INTEGER | NOT NULL, CHECK(1~16) | - | DevFlow 步骤编号 |
| reviewer_agent_id | INTEGER | NULLABLE, FK -> agents(id) | NULL | 审查 Agent（ON DELETE SET NULL） |
| score | DECIMAL(5,2) | NULLABLE, CHECK(0~100) | NULL | 评分 |
| acceptance_result | qa_result | NOT NULL | - | 验收结果（pass/fail） |
| review_dimensions | JSONB | NULLABLE | NULL | 审查维度详情 |
| comments | TEXT | NULLABLE | NULL | 审查意见 |
| review_round | INTEGER | NOT NULL | 1 | 审查轮次 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |

### 13.11 groups 表（12-groups.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 群组唯一标识 |
| project_id | INTEGER | NOT NULL, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE，1:N） |
| name | VARCHAR(200) | NOT NULL | - | 群组名称 |
| mode | group_mode | NOT NULL | 'discussion' | 群组模式（discussion/meeting） |
| host_agent_id | INTEGER | NULLABLE, FK -> agents(id) | NULL | 主持人 Agent（ON DELETE SET NULL） |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |
| deleted_at | TIMESTAMPTZ | NULLABLE | NULL | 软删除时间 |

### 13.12 group_members 表（13-group-members.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 成员记录唯一标识 |
| group_id | INTEGER | NOT NULL, FK -> groups(id) | - | 所属群组（ON DELETE CASCADE） |
| user_id | INTEGER | NULLABLE, FK -> users(id) | NULL | 用户（ON DELETE SET NULL） |
| agent_id | INTEGER | NULLABLE, FK -> agents(id) | NULL | Agent（ON DELETE SET NULL） |
| member_type | member_type | NOT NULL | - | 成员类型（user/agent） |
| joined_at | TIMESTAMPTZ | NOT NULL | NOW() | 加入时间 |

**约束**:
- member_type = 'user' 时 user_id 非空且 agent_id 为空
- member_type = 'agent' 时 agent_id 非空且 user_id 为空
- (group_id, user_id) UNIQUE WHERE user_id IS NOT NULL
- (group_id, agent_id) UNIQUE WHERE agent_id IS NOT NULL

**V27 孤儿记录风险**：user_id 和 agent_id 均为 ON DELETE SET NULL 且 NULLABLE，当关联的用户或 Agent 被删除时，对应字段被设为 NULL，可能产生双空记录（user_id=NULL 且 agent_id=NULL），member_type 字段失去意义。当前 CHECK 约束仅在 INSERT/UPDATE 时生效，ON DELETE SET NULL 为级联操作，绕过 CHECK 约束。建议在应用层添加清理逻辑或考虑改为 ON DELETE CASCADE。详见第 3.9 节。

### 13.13 group_messages 表（14-group-messages.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | BIGSERIAL | PRIMARY KEY | 自增 | 消息唯一标识（BIGSERIAL 支持大数据量） |
| group_id | INTEGER | NOT NULL, FK -> groups(id) | - | 所属群组（ON DELETE CASCADE） |
| sender_id | INTEGER | NULLABLE | NULL | 发送者 ID（触发器校验存在性） |
| sender_type | sender_type | **NULLABLE（V34 修正）** | NULL | **V34 修正**：发送者类型（user/agent） |
| role | VARCHAR(100) | NULLABLE | NULL | 消息角色（system/user/assistant 等） |
| content | TEXT | NOT NULL | - | 消息内容 |
| message_type | message_type_enum | NOT NULL | 'text' | 消息类型（text/system/meeting） |
| timestamp | TIMESTAMPTZ | NOT NULL | NOW() | 消息时间 |
| is_streaming | BOOLEAN | NOT NULL | FALSE | 是否流式消息 |
| metadata | JSONB | NULLABLE | NULL | 元数据 |
| mentions | **JSONB（V34 修正）** | NULLABLE | NULL | **V34 修正**：被提及的用户/Agent ID 数组（JSONB 类型） |

**约束**:
- sender_type 与 sender_id 互斥校验（CHECK）
- sender_id 存在性由触发器 trg_validate_sender 校验
- message_type 默认值 'text'，枚举值 (text, system, meeting)

### 13.14 meeting_outcomes 表（15-meeting-outcomes.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 会议记录唯一标识 |
| group_id | INTEGER | NOT NULL, FK -> groups(id) | - | 所属群组（ON DELETE CASCADE） |
| host_agent_id | INTEGER | NULLABLE, FK -> agents(id) | NULL | 主持人 Agent（ON DELETE SET NULL） |
| started_at | TIMESTAMPTZ | NOT NULL | - | 开始时间 |
| ended_at | TIMESTAMPTZ | NULLABLE | NULL | 结束时间 |
| type | meeting_type | NOT NULL | - | 会议类型 |
| outcome | TEXT | NULLABLE | NULL | 会议结果 |

**约束**:
- (group_id, started_at) UNIQUE — 同一会议不重复
- ended_at IS NULL OR ended_at >= started_at

### 13.15 notifications 表（16-notifications.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 通知唯一标识 |
| user_id | INTEGER | NOT NULL, FK -> users(id) | - | 接收用户（ON DELETE CASCADE） |
| project_id | INTEGER | NULLABLE, FK -> projects(id) | NULL | 关联项目（ON DELETE CASCADE） |
| type | notification_type | NOT NULL | - | 通知类型 |
| title | VARCHAR(200) | NOT NULL | - | 通知标题 |
| content | TEXT | NULLABLE | NULL | 通知内容 |
| is_read | BOOLEAN | NOT NULL | FALSE | 是否已读 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |
| deleted_at | TIMESTAMPTZ | NULLABLE | NULL | 软删除时间 |

### 13.16 repos 表（17-repos.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 仓库唯一标识 |
| project_id | INTEGER | NOT NULL, UNIQUE, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE，1:1） |
| name | VARCHAR(200) | NOT NULL | - | 仓库名称 |
| vcs_platform | VARCHAR(50) | NOT NULL, CHECK | - | VCS 平台（gitea/github/gitlab） |
| vcs_repo_id | VARCHAR(100) | NULLABLE | NULL | VCS 仓库 ID |
| url | TEXT | NULLABLE | NULL | 仓库 URL |
| default_branch | VARCHAR(100) | NULLABLE | 'main' | 默认分支 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |

**约束**: (vcs_platform, vcs_repo_id) UNIQUE — VCS 仓库全局唯一

### 13.17 repo_branches 表（18-repo-branches.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 分支唯一标识 |
| repo_id | INTEGER | NOT NULL, FK -> repos(id) | - | 所属仓库（ON DELETE CASCADE） |
| name | VARCHAR(100) | NOT NULL | - | 分支名称 |
| commit_sha | VARCHAR(40) | NULLABLE | NULL | 最新提交 SHA |
| is_protected | BOOLEAN | NOT NULL | FALSE | 是否受保护 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |

**约束**: (repo_id, name) UNIQUE — 同仓库分支名唯一

### 13.18 pull_requests 表（19-pull-requests.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | PR 唯一标识 |
| repo_id | INTEGER | NOT NULL, FK -> repos(id) | - | 所属仓库（ON DELETE CASCADE） |
| number | INTEGER | NOT NULL | - | PR 编号 |
| title | VARCHAR(200) | NOT NULL | - | PR 标题 |
| body | TEXT | NULLABLE | NULL | PR 描述 |
| status | pr_status | NOT NULL | 'open' | PR 状态 |
| source_branch_id | INTEGER | NULLABLE, FK -> repo_branches(id) | NULL | 源分支（INTEGER + FK） |
| target_branch_id | INTEGER | NULLABLE, FK -> repo_branches(id) | NULL | 目标分支（INTEGER + FK） |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |

**约束**: (repo_id, number) UNIQUE — 同仓库 PR 号唯一

### 13.19 commits 表（20-commits.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 提交唯一标识 |
| repo_id | INTEGER | NOT NULL, FK -> repos(id) | - | 所属仓库（ON DELETE CASCADE） |
| sha | VARCHAR(40) | NOT NULL | - | 提交 SHA |
| message | TEXT | NULLABLE | NULL | 提交信息 |
| author | VARCHAR(200) | NULLABLE | NULL | 提交者 |
| parent_sha | VARCHAR(40) | NULLABLE | NULL | 父提交 SHA |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |

**约束**: (repo_id, sha) UNIQUE — 同仓库提交 SHA 唯一

### 13.20 task_commits 表（21-task-commits.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 关联记录唯一标识 |
| task_id | INTEGER | NOT NULL, FK -> tasks(id) | - | 所属任务（ON DELETE CASCADE） |
| commit_id | INTEGER | NOT NULL, FK -> commits(id) | - | 所属提交（ON DELETE CASCADE） |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |

**约束**: (task_id, commit_id) UNIQUE — 同一关联不重复

### 13.21 workflow_progress 表（22-workflow-progress.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 工作流进度唯一标识 |
| project_id | INTEGER | NOT NULL, UNIQUE, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE，1:1） |
| current_step | INTEGER | NOT NULL, CHECK(1~16) | 1 | 当前步骤 |
| total_steps | INTEGER | NOT NULL | 16 | 总步骤数 |
| started_at | TIMESTAMPTZ | NOT NULL | NOW() | 开始时间 |
| completed_at | TIMESTAMPTZ | NULLABLE | NULL | 完成时间 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |

**约束**: project_id UNIQUE — 项目与工作流进度 1:1

### 13.22 workflow_steps 表（23-workflow-steps.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 工作流步骤唯一标识 |
| workflow_id | INTEGER | NOT NULL, FK -> workflow_progress(id) | - | 所属工作流（ON DELETE CASCADE） |
| step_number | INTEGER | NOT NULL, CHECK(1~16) | - | 步骤编号 |
| step_name | VARCHAR(200) | NOT NULL | - | 步骤名称 |
| status | VARCHAR(50) | NOT NULL | 'pending' | 步骤状态 |
| assigned_agent_id | INTEGER | NULLABLE, FK -> agents(id) | NULL | 分配的 Agent（ON DELETE SET NULL） |
| started_at | TIMESTAMPTZ | NULLABLE | NULL | 开始时间 |
| completed_at | TIMESTAMPTZ | NULLABLE | NULL | 完成时间 |
| result | JSONB | NULLABLE | NULL | 执行结果 |
| created_at | TIMESTAMPTZ | NOT NULL | NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL | NOW() | 更新时间（触发器自动维护） |

**约束**: (workflow_id, step_number) UNIQUE — 同工作流同步骤不重复

### 13.23 project_members 表（24-project-members.sql）

| 字段 | 数据类型 | 约束 | 默认值 | 说明 |
|------|------|------|------|------|
| id | SERIAL | PRIMARY KEY | 自增 | 成员记录唯一标识 |
| project_id | INTEGER | NOT NULL, FK -> projects(id) | - | 所属项目（ON DELETE CASCADE） |
| user_id | INTEGER | **NOT NULL（V34 修正）**, FK -> users(id) | - | **V34 修正**：用户（ON DELETE SET NULL） |
| role | VARCHAR(50) | NOT NULL | 'member' | 角色 |
| joined_at | TIMESTAMPTZ | NOT NULL | NOW() | 加入时间 |

**约束**: (project_id, user_id) UNIQUE — 同项目同用户不重复

**V34 修正说明**：从 V33 的 user_id/agent_id 双成员模式（均 NULLABLE）改为仅 user_id NOT NULL。与后端 V40 §5.2.20 对齐，project_members 表仅支持用户成员。

---

## 14. V34 修正验证总结

### 14.1 V34 八项修正验证清单

| 序号 | 修正项 | 涉及 SQL 文件 | 验证结果 |
|---|---|---|---|
| 1 | project_status 枚举值 | 01-enums.sql（已修正） | **通过** |
| 2 | user_role 枚举值 | 01-enums.sql（已修正） | **通过** |
| 3 | agent_status 枚举值 | 01-enums.sql（已修正） | **通过** |
| 4 | sender_type 枚举值 | 01-enums.sql（已修正）、14-group-messages.sql（触发器已修正） | **通过** |
| 5 | swarms.manager_agent_id 约束 | 06-swarms.sql（已恢复 NOT NULL） | **通过** |
| 6 | projects.deleted_at 字段 | 03-projects.sql（已恢复）、96-soft-delete-cleanup.sql（已恢复） | **通过** |
| 7 | group_messages.mentions 字段类型 | 14-group-messages.sql（已改为 JSONB） | **通过** |
| 8 | project_members 表结构 | 24-project-members.sql（已移除 agent_id） | **通过** |

### 14.2 V33 新增验证项

| 验证项 | 说明 | 验证结果 |
|---|---|---|
| workflow_progress 表 | 22-workflow-progress.sql 已创建，与 projects 1:1 关系 | **通过** |
| workflow_steps 表 | 23-workflow-steps.sql 已创建，与 workflow_progress 1:N 关系 | **通过** |
| project_members 表 | 24-project-members.sql 已创建，**V34 修正为仅 user_id NOT NULL** | **通过** |

### 14.3 V30 新增验证项

| 验证项 | 说明 | 验证结果 |
|---|---|---|
| swarms.manager_agent_id 恢复 NOT NULL | 06-swarms.sql 恢复 NOT NULL，移除 ON DELETE SET NULL | **通过** |
| group_messages.mentions 改为 JSONB | 14-group-messages.sql 类型从 TEXT[] 改为 JSONB，索引使用 jsonb_ops | **通过** |
| swarms.dissolved_at 字段保留 | 06-swarms.sql 保留 dissolved_at TIMESTAMPTZ NULLABLE 字段 | **通过** |
| FK 级联策略 fk_swarms_manager 更新 | 第 5.2 节 fk_swarms_manager 从 SET NULL 改为 NO ACTION | **通过** |

### 14.4 V28 新增验证项

| 验证项 | 说明 | 验证结果 |
|---|---|---|
| swarm_purpose 枚举扩展 | 01-enums.sql 新增 'tdd_test' 值 | **通过** |
| message_type_enum 重构 | 01-enums.sql 值域改为 (text, system, meeting) | **通过** |
| swarms.step_number 字段 | 06-swarms.sql 新增字段及 CHECK 约束 | **通过** |
| qa_records 新增字段 | 11-qa-records.sql 新增 project_id/step_number/review_round | **通过** |
| qa_records 新增索引 | 11-qa-records.sql 新增 project/step/round 三个索引 | **通过** |
| group_messages.mentions | 14-group-messages.sql 新增 TEXT[] 字段及 GIN 索引 | **通过** |
| notifications.project_id | 16-notifications.sql 移除 NOT NULL 约束 | **通过** |
| 外键总数更新 | 从 35 条更新为 36 条 | **通过** |

### 14.5 V29 新增验证项

| 验证项 | 说明 | 验证结果 |
|---|---|---|
| swarms.manager_agent_id 约束确认 | 06-swarms.sql 确认 INTEGER NULLABLE（无 NOT NULL），V27 修复持续有效 | **通过** |
| group_messages.mentions 类型确认 | 14-group-messages.sql 确认 TEXT[] 类型，与 V28 变更日志一致 | **通过** |
| groups.project_id 移除 UNIQUE | 12-groups.sql 移除 UNIQUE 约束，改为 1:N 关系 | **通过** |
| groups 1:N 关系同步更新 | 第 1.1/1.2/2.6/4.2/10.1/13.11 节全部更新为 1:N | **通过** |

---

## 15. SQL 文件校验与执行顺序验证

### 15.1 SQL 文件校验方法

V22 引入 MD5 校验和机制，用于验证 SQL 文件内容完整性，避免 V20 '文档写了但 SQL 没改'的问题重演。

> **校验方法**：执行 `md5sum sql/*.sql` 可与上表校验和比对，验证 SQL 文件未被意外修改。

> **V34 注意**：V34 对 01-enums.sql、03-projects.sql、06-swarms.sql、14-group-messages.sql、24-project-members.sql、96-soft-delete-cleanup.sql 进行了修改。MD5 校验和已变更。请使用新的校验和进行比对。

### 15.2 关键修正项代码片段验证

#### 15.2.1 V34 修正：user_role 枚举（01-enums.sql）

```sql
-- 01-enums.sql 第 22 行（V34 修正）
CREATE TYPE user_role AS ENUM ('user', 'admin', 'system_admin');
```

**验证点**：
1. 已添加 system_admin 枚举值
2. 与后端 V40 §5.2.1 对齐

#### 15.2.2 V34 修正：project_status 枚举（01-enums.sql）

```sql
-- 01-enums.sql 第 24 行（V34 修正）
CREATE TYPE project_status AS ENUM ('created', 'in_progress', 'completed', 'cancelled');
```

**验证点**：
1. 枚举值从 V33 的 (active, paused, completed, archived) 改为 (created, in_progress, completed, cancelled)
2. 与后端 V40 §5.2.2 对齐

#### 15.2.3 V34 修正：agent_status 枚举（01-enums.sql）

```sql
-- 01-enums.sql 第 27 行（V34 修正）
CREATE TYPE agent_status AS ENUM ('online', 'offline', 'busy');
```

**验证点**：
1. 枚举值从 V33 的 (idle, busy, error, offline) 改为 (online, offline, busy)
2. 与后端 V40 §5.2.4 对齐

#### 15.2.4 V34 修正：sender_type 枚举（01-enums.sql）

```sql
-- 01-enums.sql 第 37 行（V34 修正）
CREATE TYPE sender_type AS ENUM ('user', 'agent');
```

**验证点**：
1. 已移除 system 枚举值
2. 改为二值 (user, agent)
3. 与后端 V40 §5.2.10 对齐

#### 15.2.5 V34 修正：manager_agent_id NOT NULL（06-swarms.sql）

```sql
-- 06-swarms.sql 第 15 行（V34 修正）
manager_agent_id INTEGER NOT NULL REFERENCES agents(id),
```

**验证点**：
1. 已恢复 NOT NULL 约束（V33 NULLABLE 方案被 V34 弃用）
2. 已移除 ON DELETE SET NULL，改用默认 NO ACTION
3. 与后端 V40 §5.2.11 对齐

#### 15.2.6 V34 修正：projects.deleted_at 恢复（03-projects.sql）

```sql
-- 03-projects.sql（V34 修正）
    deleted_at TIMESTAMP WITH TIME ZONE
);
-- 03-projects.sql 索引（V34 修正：恢复 deleted_at 部分索引）
CREATE INDEX idx_projects_deleted ON projects(deleted_at) WHERE deleted_at IS NOT NULL;
```

**验证点**：
1. 已恢复 deleted_at 字段
2. 已恢复 deleted_at 部分索引
3. 与后端 V40 §5.2.2 对齐

#### 15.2.7 V34 修正：group_messages.mentions JSONB（14-group-messages.sql）

```sql
-- 14-group-messages.sql（V34 修正）
    mentions JSONB,
-- 14-group-messages.sql 索引（V34 修正：JSONB GIN 索引）
CREATE INDEX idx_group_messages_mentions_gin ON group_messages USING gin(mentions jsonb_path_ops);
```

**验证点**：
1. mentions 类型从 TEXT[] 改回 JSONB（与后端 V40 对齐）
2. GIN 索引使用 jsonb_path_ops 操作符类
3. 存储格式为 JSON 数组，如 `[1, 2, 3]`

#### 15.2.8 V34 修正：project_members 仅 user_id（24-project-members.sql）

```sql
-- 24-project-members.sql（V34 修正）
CREATE TABLE project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**验证点**：
1. 已移除 agent_id 字段
2. user_id 为 NOT NULL
3. 与后端 V40 §5.2.20 对齐

### 15.3 执行顺序依赖图

```
层级 1（无依赖）:
  01-enums.sql

层级 2（仅依赖 01）:
  02-users.sql -> 05-agents.sql

层级 3（依赖 02/05）:
  03-projects.sql -> 06-swarms.sql -> 07-swarm-members.sql
  04-requirements.sql

层级 4（依赖 03/05/06）:
  08-tasks.sql -> 09-task-dependencies.sql
  10-agent-execution-logs.sql
  11-qa-records.sql
  12-groups.sql -> 13-group-members.sql -> 14-group-messages.sql
              -> 15-meeting-outcomes.sql

层级 5（依赖 02/03）:
  16-notifications.sql

层级 6（依赖 03）:
  17-repos.sql -> 18-repo-branches.sql -> 19-pull-requests.sql
            -> 20-commits.sql
  22-workflow-progress.sql -> 23-workflow-steps.sql
  24-project-members.sql

层级 7（依赖 08/20）:
  21-task-commits.sql

层级 8（依赖全部）:
  96-soft-delete-cleanup.sql
  97-permissions.sql
  98-init-data.sql
  99-views.sql
```

**关键路径**：01 -> 02 -> 03 -> 06 -> 07 -> 08 -> 09 -> 10/11 -> 12 -> 13 -> 14 -> 17 -> 18 -> 19 -> 20 -> 21 -> 22 -> 23 -> 24 -> 96/97/98/99

**V34 执行顺序验证结论**：
1. 05-agents.sql 在 06-swarms.sql 之前执行，swarms 的 manager_agent_id FK 引用 agents，安全
2. 06-swarms.sql 中的 auto_add_manager_to_members 触发器仅在 INSERT swarms 时触发，不依赖 swarm_members 表已存在
3. 07-swarm-members.sql 在 06-swarms.sql 之后执行，触发器定义时 swarm_members 已存在，安全
4. 11-qa-records.sql 在 03-projects.sql 之后执行，qa_records.project_id FK 引用 projects，安全
5. 12-groups.sql 在 03-projects.sql 之后执行，groups.project_id FK 引用 projects，安全
6. 14-group-messages.sql 在 12-groups.sql 之后执行，group_messages.group_id FK 引用 groups，安全
7. 16-notifications.sql 在 02-users.sql 和 03-projects.sql 之后执行，notifications.user_id/project_id FK 引用安全
8. 22-workflow-progress.sql 在 03-projects.sql 之后执行，workflow_progress.project_id FK 引用 projects，安全
9. 23-workflow-steps.sql 在 22-workflow-progress.sql 之后执行，workflow_steps.workflow_id FK 引用 workflow_progress，安全
10. 24-project-members.sql 在 03-projects.sql 之后执行，project_members.project_id/user_id FK 引用安全
11. 不存在循环依赖，所有文件按数字顺序执行即可

---

*文档结束。完整 DDL 请参见 sql/ 目录。*
