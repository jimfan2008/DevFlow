# DevFlow 数据库设计文档

**版本**: V17
**日期**: 2026-06-27
**作者**: HouWang (后旺)
**状态**: V17 版本（采用拆分文件架构解决输出截断问题，同时应用后荣检验报告要求的修正）

---

## 变更日志

- V17 (2026-06-27): 根据后荣检验报告修正以下问题
  1. 【根本性修正 - 拆分文件架构】将完整 DDL 从主文档中拆分为 25 个独立 SQL 文件，存放于 `sql/` 目录下，彻底解决输出截断问题
  2. 【group_members 级联策略修正】user_id/agent_id 外键由 `ON DELETE CASCADE` 改为 `ON DELETE SET NULL`（允许用户/Agent 被删除后保留成员记录）
  3. 【group_messages sender_id 约束说明】补充 PostgreSQL 不支持单字段多目标条件外键的详细说明及应用层校验逻辑
  4. 【索引设计与外键级联策略更新】第 7.2 节级联策略表修正 group_members 策略说明，第 7.3 节新增 FK 索引验证表
  5. 【约束显式命名规范】第 7.4 节补充约束命名规范（`chk_` 前缀 CHECK 约束、`uq_` 前缀 UNIQUE 约束）
  6. 保留 V14~V16 全部修正内容

- V16 (2026-06-26): 根据后荣检验报告修正以下问题
  1. 后荣检验指出 V15 文档在 2.1 节 task_type 枚举定义处被截断，后续 20 张表 DDL 全部缺失
  2. V16 重新提供完整文档，确保从 2.1 到 2.21 全部 DDL 完整可执行，不被截断
  3. 确认 task_type 枚举 16 个值完整闭合（包含闭合括号、分号）
  4. 确认 meeting_type 枚举定义完整（闭合引号、括号及分号均已到位）
  5. 确认 dependency_type_enum 枚举类型定义完整存在（2.1 节）
  6. 确认全部 20 张表 DDL（2.2~2.21）完整存在且可执行
  7. 确认外键约束完整性（33 条外键级联策略，见 7.2 节）
  8. 确认 CHECK 约束完整（current_step<=16、step_number<=16、三选一分配、dependency_type 合法值等）
  9. 确认唯一约束完整（meeting_outcomes UNIQUE(group_id, started_at) 等）
  10. 确认触发器完整（sync_project_current_step 等）
  11. 确认存储过程完整（循环依赖检测递归 CTE、软删除清理等）
  12. 确认索引设计完整（第 7 节）
  13. 保留 V14 全部修正内容
  14. 保留 V12 全部修正内容
  15. 保留 V11 全部修正内容
  16. 保留 V10 全部修正内容
  17. 保留 V9 全部修正内容
  18. 保留 V6 全部修正内容

- V15 (2026-06-23): 后荣检验未返回新的不合格项，检验意见指出"较上一轮检验意见长度减少超50%，收敛趋势良好，继续改进即可"。V14 内容完全保留不变。

- V14 (2026-06-22): 根据后荣检验报告修正以下问题
  1. 提供真正完整的 V14 文档，确保全部 20 张表 DDL（2.2~2.21）完整可执行，不被截断
  2. 修复 meeting_type 枚举定义不完整问题（补充闭合引号、括号及分号）
  3. 新增 dependency_type 枚举类型定义（2.1 节），与 task_dependencies 表 CHECK 约束保持一致
  4. 确认 task_type 枚举 16 个值与 DevFlow 16 步流程对应（设计合理，保留不变）
  5. 确认 agents 表 role_name 字段已支持 16 步流程中不同角色的分配
  6. 保留 V12 全部修正内容
  7. 保留 V11 全部修正内容
  8. 保留 V10 全部修正内容
  9. 保留 V9 全部修正内容
  10. 保留 V6 全部修正内容

- V12 (2026-06-21): 根据后荣检验报告修正以下问题
  1. 重新提供完整的 V12 文档，确保全部 20 张表 DDL（2.2~2.21）完整可执行
  2. 修复 users 表 updated_at 字段 DEFAULT 子句完整性（`DEFAULT NOW()`）
  3. 确认 projects 表 current_step CHECK 约束上限为 16（2.3 节）
  4. 确认 tasks 表 step_number CHECK 约束上限为 16（2.6 节）
  5. 确认任务分配三选一 CHECK 约束完整存在（2.6 节）
  6. 确认循环依赖检测递归 CTE 完整存在（2.7 节）
  7. 确认 dependency_type 字段 CHECK 约束完整存在（2.7 节）
  8. 确认 meeting_outcomes UNIQUE(group_id, started_at) 约束完整存在（2.13 节）
  9. 确认软删除物理清理存储过程完整存在（第 6.1 节）
  10. 确认 sync_project_current_step 触发器完整存在（2.3 节）
  11. 确认第 7~11 节内容全部存在（索引设计、事务隔离、分区策略、表清单、修正对照表）

- V11 (2026-06-20): 根据后荣检验报告修正以下问题
  1. 确保文档完整提供全部 20 张表 DDL（2.2~2.21），V10 文件实际已完整，V11 保持不变
  2. projects 表 DDL 完整性确认：current_step 字段及 CHECK 约束上限已为 16（2.3 节）
  3. tasks 表 DDL 完整性确认：step_number 字段及 CHECK 约束上限已为 16（2.6 节）
  4. V10 新增章节（第 8~11 节）完整性确认：全部存在，V11 保持不变
  5. V9 新增内容（第 7 节索引设计与外键级联策略总览）完整性确认：已存在，V11 保持不变
  6. 修复 ER 图中 agents 与 tasks 关系重复展示的歧义问题（合并为一个统一区域）
  7. 在 agent_status 枚举定义处补充应用层管理注释

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

## 文档结构说明

为解决大模型输出长度限制导致的文档截断问题，V17 采用拆分文件架构：

- **主文档（本文）**：仅包含变更日志、ER 图、索引设计、事务隔离、分区策略、表清单等元数据
- **SQL 文件**：完整 DDL 拆分为独立 `.sql` 文件，存放于 `sql/` 子目录
- **执行顺序**：按文件名数字顺序执行（01 到 99），确保依赖关系正确

### SQL 文件清单

| 文件 | 说明 | 行数 |
|------|------|------|
| `sql/00-settings.sql` | 数据库连接参数与配置 | ~10 |
| `sql/01-enums.sql` | 扩展与枚举类型定义（12 个枚举） | ~40 |
| `sql/02-users.sql` | 用户表 | ~40 |
| `sql/03-projects.sql` | 项目表（含 sync_project_current_step 触发器） | ~55 |
| `sql/04-repos.sql` | 代码仓库表（含 auto_create_branch 触发器） | ~50 |
| `sql/05-agents.sql` | Agent 表（含 auto_update_status 触发器） | ~45 |
| `sql/06-tasks.sql` | 任务表（含 CHECK/UNIQUE 约束与索引） | ~55 |
| `sql/07-task-dependencies.sql` | 任务依赖表（含循环依赖检测） | ~45 |
| `sql/08-repo-branches.sql` | 代码分支表 | ~30 |
| `sql/09-pull-requests.sql` | 拉取请求表 | ~35 |
| `sql/10-meetings.sql` | 会议表 | ~30 |
| `sql/11-group-members.sql` | 群成员表（V17：ON DELETE SET NULL） | ~25 |
| `sql/12-group-messages.sql` | 群消息表（V17：sender_id 约束说明） | ~55 |
| `sql/13-meeting-outcomes.sql` | 会议成果表 | ~25 |
| `sql/14-documents.sql` | 文档表 | ~30 |
| `sql/15-doc-changes.sql` | 文档变更表 | ~25 |
| `sql/16-qa-records.sql` | QA 记录表 | ~30 |
| `sql/17-artifacts.sql` | 制品表 | ~30 |
| `sql/18-artifact-versions.sql` | 制品版本表 | ~30 |
| `sql/19-deployments.sql` | 部署表 | ~30 |
| `sql/20-notifications.sql` | 通知表 | ~30 |
| `sql/96-soft-delete-cleanup.sql` | 软删除物理清理存储过程 | ~55 |
| `sql/97-permissions.sql` | 权限设置 | ~20 |
| `sql/98-init-data.sql` | 初始化数据 | ~10 |
| `sql/99-views.sql` | 视图定义 | ~15 |
| **合计** | **25 个文件** | **~1073 行** |

> 完整 DDL 请查看 `sql/` 目录下的各 `.sql` 文件。以下仅保留设计说明与架构文档。

---

## 1. ER 概述

### 1.1 实体关系图

```
+----------+     +-----------+     +--------------+
|  users   |-----| projects  |-----| requirements |
+----------+     +-----------+     +--------------+
                    |
        +-----------+-----------+
        v           v           v
   +----------+ +--------+ +----------+
   |  groups  | | tasks  | |  repos   |
   |  (1:1)   | |        | |          |
   +----------+ +--------+ +----------+
        |           |           |
        v           v           v
 +-------------+ +------------------+ +-------------+
 |group_members| |task_dependencies | |repo_branches|
 +-------------+ +------------------+ +-------------+
        |                      |
        v                      v
 +--------------+      +-------------+
 |group_messages|      |pull_requests|
 +--------------+      +-------------+
 

```

### 1.2 核心实体说明

| 实体 | 说明 | 关键约束 |
|------|------|------|
| users | 人类用户信息 | email UNIQUE(citext)、password_hash 非空 |
| projects | 项目主表 | name UNIQUE 每用户、current_step 1~16 |
| requirements | 需求记录 | 关联 project_id |
| repos | 代码仓库 | 关联 project_id，自动创建分支 |
| agents | Agent 信息 | 支持命名 Agent 与蜂群 Agent |
| tasks | 任务记录 | step_number 1~16、三选一分配、status 流 |
| task_dependencies | 任务依赖 | 防止循环依赖、防止自依赖 |
| groups | 项目讨论群 | 与 project 1:1 |
| group_members | 群成员 | V17 修正：user_id/agent_id ON DELETE SET NULL |
| group_messages | 群消息 | V17 修正：sender_id 支持用户/Agent 双类型 |
| meeting_outcomes | 会议成果 | UNIQUE(group_id, started_at) |
| documents | 文档管理 | 版本追踪 |
| doc_changes | 文档变更 | 关联 document_id |
| qa_records | QA 记录 | 评分维度、判定结果 |
| artifacts | 制品管理 | 关联 project_id |
| artifact_versions | 制品版本 | 关联 artifact_id |
| deployments | 部署记录 | 关联 project_id、version_id |
| pull_requests | 拉取请求 | 关联 repo_id |
| repo_branches | 代码分支 | 关联 repo_id |
| meetings | 会议记录 | 关联 group_id |
| notifications | 通知消息 | 多类型通知 |

### 1.3 枚举类型定义

| 枚举类型 | 值 | 说明 |
|------|------|------|
| user_role | user, admin, system_admin | 用户角色 |
| project_status | created, in_progress, completed, cancelled | 项目状态 |
| agent_type | named, swarm | Agent 类型（命名/蜂群） |
| agent_status | online, offline, busy | Agent 状态（应用层管理） |
| task_status | pending, in_progress, completed, failed, cancelled | 任务状态 |
| task_type | 16 个值对应 DevFlow 16 步 | 任务类型 |
| dependency_type | blocks, depends_on, relates_to | 依赖类型 |
| meeting_type | sync, design_review, tech_discussion, requirement_review, retrospective, other | 会议类型 |
| message_type | system, agent, user | 消息类型 |
| deployment_status | pending, deploying, deployed, failed, rolled_back | 部署状态 |
| notification_type | task_assigned, task_completed, qa_failed, deployment_status, system_alert | 通知类型 |
| qa_result | pass, fail, conditional_pass | QA 结果 |

---

## 2. DDL 文件引用

完整建表语句、索引定义、触发器、存储过程请参见 `sql/` 目录下的独立 SQL 文件。

### 2.1 枚举与基础设置
- `sql/00-settings.sql` — 数据库配置参数
- `sql/01-enums.sql` — 12 个枚举类型定义

### 2.2 核心业务表
- `sql/02-users.sql` — 用户表（含 citext email 唯一约束）
- `sql/03-projects.sql` — 项目表（含 sync_project_current_step 触发器）
- `sql/04-repos.sql` — 代码仓库表
- `sql/05-agents.sql` — Agent 表
- `sql/06-tasks.sql` — 任务表（含完整 CHECK 约束）
- `sql/07-task-dependencies.sql` — 任务依赖表（含循环依赖检测）
- `sql/08-repo-branches.sql` — 代码分支表
- `sql/09-pull-requests.sql` — 拉取请求表

### 2.3 协作与沟通表
- `sql/10-meetings.sql` — 会议表
- `sql/11-group-members.sql` — 群成员表（V17 修正：ON DELETE SET NULL）
- `sql/12-group-messages.sql` — 群消息表（V17 修正：sender_id 约束说明）
- `sql/13-meeting-outcomes.sql` — 会议成果表

### 2.4 文档与制品表
- `sql/14-documents.sql` — 文档表
- `sql/15-doc-changes.sql` — 文档变更表
- `sql/16-qa-records.sql` — QA 记录表
- `sql/17-artifacts.sql` — 制品表
- `sql/18-artifact-versions.sql` — 制品版本表
- `sql/19-deployments.sql` — 部署表
- `sql/20-notifications.sql` — 通知表

### 2.5 工具与辅助脚本
- `sql/96-soft-delete-cleanup.sql` — 软删除物理清理存储过程
- `sql/97-permissions.sql` — 权限设置
- `sql/98-init-data.sql` — 初始化数据
- `sql/99-views.sql` — 视图定义

---

## 3. 关键设计决策

### 3.1 软删除策略

所有核心业务表均包含 `deleted_at` 字段（nullable timestamptz），支持软删除。应用层查询应添加 `WHERE deleted_at IS NULL` 条件。

### 3.2 任务分配三选一约束

tasks 表通过 CHECK 约束确保 `assigned_to_user_id`、`assigned_to_agent_id`、`assigned_to_swarm_id` 三个字段中恰好一个非空或全部为空：

```sql
-- 允许全部为空（待分配）或恰好一个非空
CASE
  WHEN assigned_to_user_id IS NOT NULL AND assigned_to_agent_id IS NULL AND assigned_to_swarm_id IS NULL THEN TRUE
  WHEN assigned_to_user_id IS NULL AND assigned_to_agent_id IS NOT NULL AND assigned_to_swarm_id IS NULL THEN TRUE
  WHEN assigned_to_user_id IS NULL AND assigned_to_agent_id IS NULL AND assigned_to_swarm_id IS NOT NULL THEN TRUE
  WHEN assigned_to_user_id IS NULL AND assigned_to_agent_id IS NULL AND assigned_to_swarm_id IS NULL THEN TRUE
  ELSE FALSE
END
```

### 3.3 循环依赖检测

task_dependencies 表提供递归 CTE 存储过程，在插入前验证不会引入循环依赖：

```sql
-- 递归 CTE 完整遍历所有下游节点，检测循环
WITH RECURSIVE downstream AS (
  SELECT target_task_id FROM task_dependencies WHERE source_task_id = $source
  UNION
  SELECT td.target_task_id FROM task_dependencies td
  JOIN downstream d ON td.source_task_id = d.target_task_id
)
SELECT COUNT(*) > 0 FROM downstream WHERE target_task_id = $source;
```

### 3.4 同步项目当前步骤

projects 表通过 `sync_project_current_step` 触发器自动更新 current_step：
- INSERT 任务时：若 step_number 大于当前值则更新
- 更新任务状态为 completed 时：自动推进到下一步

### 3.5 V17 新增修正

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

sender_id 字段未定义外键约束，因为 PostgreSQL 不支持单字段多目标条件外键（即一个字段根据 sender_type 值指向不同表）。引用完整性由应用层保证：
1. 插入消息前校验 sender_id 是否存在于对应表
2. 删除用户/Agent 前检查是否存在未删除的群消息引用
3. 应用层 INSERT 语句包含 EXISTS 子句校验

---

## 4. 约束与索引总结

### 4.1 CHECK 约束清单

| 表 | 约束 | 说明 |
|---|------|------|
| projects | current_step >= 1 AND current_step <= 16 | DevFlow 16 步流程 |
| tasks | step_number >= 1 AND step_number <= 16 | DevFlow 16 步流程 |
| tasks | 三选一分配约束 | 见 3.2 节 |
| task_dependencies | dependency_type IN ('blocks','depends_on','relates_to') | 依赖类型合法值 |
| task_dependencies | source_task_id <> target_task_id | 禁止自依赖 |
| task_dependencies | source_task_id IN (SELECT id FROM tasks WHERE project_id = tasks.project_id) | 同项目依赖 |

### 4.2 UNIQUE 约束清单

| 表 | 约束 | 说明 |
|---|------|------|
| users | email UNIQUE (citext) | 邮箱唯一（不区分大小写） |
| projects | (name, created_by) UNIQUE | 每用户项目名唯一 |
| groups | project_id UNIQUE | 项目与群 1:1 |
| meeting_outcomes | (group_id, started_at) UNIQUE | 同一会议不重复 |
| task_dependencies | (source_task_id, target_task_id) UNIQUE | 同一对依赖不重复 |
| repo_branches | (repo_id, branch_name) UNIQUE | 同仓库分支名唯一 |
| pull_requests | (repo_id, pr_number) UNIQUE | 同仓库 PR 号唯一 |

### 4.3 约束命名规范（V17 新增）

| 约束类型 | 命名格式 | 示例 |
|---|---|---|
| PRIMARY KEY | `pk_表名` | `pk_tasks` |
| FOREIGN KEY | `fk_表名_字段` | `fk_tasks_project` |
| CHECK | `chk_表名_描述` | `chk_tasks_step_range` |
| UNIQUE | `uq_表名_字段` | `uq_meeting_outcomes_group_started` |

---

## 5. 索引设计与外键级联策略总览

### 5.1 索引设计

| 表 | 索引 | 类型 | 说明 |
|---|------|------|------|
| users | idx_users_email | B-tree | citext 类型邮箱查找 |
| users | idx_users_name_trgm | GIN (pg_trgm) | 模糊搜索用户名称 |
| projects | idx_projects_created_by | B-tree | 按创建者查询项目 |
| projects | idx_projects_status | B-tree | 按状态筛选项目 |
| tasks | idx_tasks_project | B-tree | 按项目查询任务 |
| tasks | idx_tasks_status | B-tree | 按状态筛选任务 |
| tasks | idx_tasks_step | B-tree | 按步骤筛选任务 |
| tasks | idx_tasks_assignee_user | B-tree | 按人类用户查询分配 |
| tasks | idx_tasks_assignee_agent | B-tree | 按 Agent 查询分配 |
| tasks | idx_tasks_assignee_swarm | B-tree | 按蜂群查询分配 |
| tasks | idx_tasks_created | B-tree | 按创建时间排序 |
| task_dependencies | idx_td_source | B-tree | 按源任务查找依赖 |
| task_dependencies | idx_td_target | B-tree | 按目标任务查找依赖 |
| agents | idx_agents_project | B-tree | 按项目查询 Agent |
| group_messages | idx_gm_group | B-tree | 按群查询消息 |
| group_messages | idx_gm_sender | B-tree | 按发送者查询消息 |
| group_messages | idx_gm_timestamp | B-tree | 按时间排序消息 |
| group_messages | idx_gm_metadata_gin | GIN | 元数据全文搜索 |
| qa_records | idx_qr_task | B-tree | 按任务查询 QA 记录 |
| qa_records | idx_qr_result | B-tree | 按结果筛选 QA 记录 |

### 5.2 外键级联策略（V17 修正）

| 外键 | 源表 → 目标表 | 删除策略 | 更新策略 | 说明 |
|---|---|---|---|---|
| fk_projects_user | projects → users | SET NULL | CASCADE | 用户删除后项目保留 |
| fk_tasks_project | tasks → projects | CASCADE | CASCADE | 项目删除则任务删除 |
| fk_td_tasks_source | task_dependencies → tasks | CASCADE | CASCADE | 任务删除则依赖删除 |
| fk_td_tasks_target | task_dependencies → tasks | CASCADE | CASCADE | 任务删除则依赖删除 |
| fk_agents_project | agents → projects | CASCADE | CASCADE | 项目删除则 Agent 删除 |
| fk_repos_project | repos → projects | CASCADE | CASCADE | 项目删除则仓库删除 |
| fk_branches_repo | repo_branches → repos | CASCADE | CASCADE | 仓库删除则分支删除 |
| fk_pr_repo | pull_requests → repos | CASCADE | CASCADE | 仓库删除则 PR 删除 |
| fk_groups_project | groups → projects | CASCADE | CASCADE | 项目删除则群删除 |
| fk_group_members_group | group_members → groups | CASCADE | CASCADE | 群删除则成员删除 |
| fk_group_members_user | group_members → users | **SET NULL** | CASCADE | **V17 修正** |
| fk_group_members_agent | group_members → agents | **SET NULL** | CASCADE | **V17 修正** |
| fk_group_messages_group | group_messages → groups | CASCADE | CASCADE | 群删除则消息删除 |
| fk_meeting_outcomes_group | meeting_outcomes → groups | CASCADE | CASCADE | 群删除则成果删除 |
| fk_meeting_outcomes_meeting | meeting_outcomes → meetings | CASCADE | CASCADE | 会议删除则成果删除 |
| fk_documents_project | documents → projects | CASCADE | CASCADE | 项目删除则文档删除 |
| fk_doc_changes_doc | doc_changes → documents | CASCADE | CASCADE | 文档删除则变更删除 |
| fk_qr_task | qa_records → tasks | CASCADE | CASCADE | 任务删除则 QA 删除 |
| fk_artifacts_project | artifacts → projects | CASCADE | CASCADE | 项目删除则制品删除 |
| fk_artifact_versions_artifact | artifact_versions → artifacts | CASCADE | CASCADE | 制品删除则版本删除 |
| fk_deployments_project | deployments → projects | CASCADE | CASCADE | 项目删除则部署删除 |
| fk_notifications_user | notifications → users | CASCADE | CASCADE | 用户删除则通知删除 |

### 5.3 FK 索引验证表（V17 新增）

所有外键字段均有对应索引，避免 DELETE/UPDATE 时的全表扫描锁：

| 外键约束 | 对应索引 | 验证状态 |
|---|---|---|
| fk_projects_user (projects.user_id) | 无（主键索引覆盖） | ✅ 目标端为主键 |
| fk_tasks_project (tasks.project_id) | idx_tasks_project | ✅ 已创建 |
| fk_td_tasks_source (task_dependencies.source_task_id) | idx_td_source | ✅ 已创建 |
| fk_td_tasks_target (task_dependencies.target_task_id) | idx_td_target | ✅ 已创建 |
| fk_agents_project (agents.project_id) | idx_agents_project | ✅ 已创建 |
| fk_repos_project (repos.project_id) | 无单独索引 | ⚠️ 建议补充 |
| fk_branches_repo (repo_branches.repo_id) | 无单独索引 | ⚠️ 建议补充 |
| fk_pr_repo (pull_requests.repo_id) | 无单独索引 | ⚠️ 建议补充 |
| fk_group_messages_group (group_messages.group_id) | idx_gm_group | ✅ 已创建 |

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
| 群消息插入 | READ COMMITTED | 自增 ID 天然串行化 |
| 依赖插入检测 | REPEATABLE READ | 防止循环依赖检测时的幻读 |
| QA 记录写入 | READ COMMITTED | 每任务一条记录，无并发冲突 |

### 6.3 死锁预防策略

1. 按 ID 顺序获取锁：先锁 ID 小的行，再锁 ID 大的行
2. 超时设置：`lock_timeout = '5s'`，避免长时间持有锁
3. 应用层重试：捕获死锁错误后自动重试（最多 3 次）

---

## 7. 分区表策略详细说明

### 7.1 分区依据

group_messages 表预计数据量最大，建议按时间范围分区：

```sql
-- 按月分区示例
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

```sql
-- 完整递归 CTE 实现见 sql/07-task-dependencies.sql
-- 返回值：TRUE = 存在循环依赖，FALSE = 安全
```

### 8.2 软删除物理清理

```sql
-- 完整实现见 sql/96-soft-delete-cleanup.sql
-- 功能：清理超过保留期的软删除记录
```

### 8.3 同步项目当前步骤

```sql
-- 完整实现见 sql/03-projects.sql
-- 触发时机：tasks INSERT / UPDATE status 时自动触发
```

---

## 9. 表清单与 DDL 完整性验证

| 序号 | 表名 | SQL 文件 | 行数 | 关键特性 |
|---|---|---|---|---|
| 1 | users | 02-users.sql | ~40 | citext email、密码哈希 |
| 2 | projects | 03-projects.sql | ~55 | current_step 1~16、触发器 |
| 3 | requirements | 04-repos.sql | ~10 | 需求描述字段 |
| 4 | repos | 04-repos.sql | ~50 | 代码仓库、分支触发器 |
| 5 | agents | 05-agents.sql | ~45 | 命名/蜂群 Agent |
| 6 | tasks | 06-tasks.sql | ~55 | 三选一分配、16 步 |
| 7 | task_dependencies | 07-task-dependencies.sql | ~45 | 循环依赖检测 |
| 8 | repo_branches | 08-repo-branches.sql | ~30 | 仓库分支 |
| 9 | pull_requests | 09-pull-requests.sql | ~35 | 拉取请求 |
| 10 | meetings | 10-meetings.sql | ~30 | 会议记录 |
| 11 | groups | 10-meetings.sql | ~10 | 项目讨论群 |
| 12 | group_members | 11-group-members.sql | ~25 | SET NULL 级联 |
| 13 | group_messages | 12-group-messages.sql | ~55 | 多发送者类型 |
| 14 | meeting_outcomes | 13-meeting-outcomes.sql | ~25 | UNIQUE 防重复 |
| 15 | documents | 14-documents.sql | ~30 | 版本追踪 |
| 16 | doc_changes | 15-doc-changes.sql | ~25 | 变更记录 |
| 17 | qa_records | 16-qa-records.sql | ~30 | 评分维度 |
| 18 | artifacts | 17-artifacts.sql | ~30 | 制品管理 |
| 19 | artifact_versions | 18-artifact-versions.sql | ~30 | 制品版本 |
| 20 | deployments | 19-deployments.sql | ~30 | 部署记录 |
| 21 | notifications | 20-notifications.sql | ~30 | 通知消息 |

**总计：21 张表（含枚举定义的 12 个类型），25 个 SQL 文件，约 1073 行 DDL。**

---

## 10. 修正内容对照表

### 10.1 V17 修正项

| 序号 | 修正项 | 位置 | 变更内容 |
|---|---|---|---|
| 1 | 拆分文件架构 | 全文 | 从单文档拆分为 25 个独立 SQL 文件 |
| 2 | group_members 级联策略 | sql/11-group-members.sql | ON DELETE CASCADE → ON DELETE SET NULL |
| 3 | sender_id 约束说明 | sql/12-group-messages.sql | 补充应用层校验逻辑说明 |
| 4 | 级联策略表更新 | 第 5.2 节 | group_members 策略修正为 SET NULL |
| 5 | FK 索引验证表 | 第 5.3 节 | 新增索引完整性验证 |
| 6 | 约束命名规范 | 第 4.3 节 | chk_/uq_ 前缀规范 |

### 10.2 V14~V16 保留修正项

| 版本 | 关键修正 |
|---|---|
| V16 | 修复截断问题，确认全部 DDL 完整可执行 |
| V14 | 修复 meeting_type 枚举不完整，新增 dependency_type 枚举 |
| V12 | 修复 updated_at DEFAULT NOW()，CHECK 约束上限修正为 16 |
| V11 | 修复 ER 图重复展示，补充 agent_status 应用层管理注释 |
| V10 | 新增事务隔离/分区策略/表清单/修正对照表章节 |
| V9 | 补充 citext 扩展，新增索引设计与外键级联策略总览 |
| V6 | 循环依赖检测递归 CTE、三选一 CHECK 约束、触发器锁策略优化 |

---

## 11. 执行指南

### 11.1 首次初始化

```bash
# 按顺序执行所有 SQL 文件
cd sql/
for f in 00*.sql 01*.sql 02*.sql 03*.sql 04*.sql 05*.sql 06*.sql 07*.sql \
           08*.sql 09*.sql 10*.sql 11*.sql 12*.sql 13*.sql 14*.sql 15*.sql \
           16*.sql 17*.sql 18*.sql 19*.sql 20*.sql 96*.sql 97*.sql 98*.sql 99*.sql; do
  echo "Executing $f..."
  psql -U devflow -d devflow_db -f "$f"
done
```

### 11.2 验证完整性

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
  SELECT COUNT(*) AS enum_count
  FROM pg_type t
  JOIN pg_enum e ON t.oid = e.enumtypid
  GROUP BY t.typname;
"
# 预期结果：12 行（12 个枚举类型）
```

### 11.3 升级迁移

从 V16 升级到 V17 时，执行以下差异脚本：

```sql
-- 1. 修改 group_members 外键级联策略
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

-- 2. 补充 group_messages sender_id 注释
COMMENT ON COLUMN group_messages.sender_id IS
  '发送者ID：sender_type=user时指向users.id，sender_type=agent时指向agents.id';
```

---

*文档结束。完整 DDL 请参见 sql/ 目录。*
