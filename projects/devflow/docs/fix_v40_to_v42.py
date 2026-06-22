#!/usr/bin/env python3
"""
DevFlow 后端 V40 -> V42 一致性修正脚本
修正 13 项跨文档一致性问题：
- 前端-后端 (3项): WebSocket 方案、WebSocket 认证、HTTP 方法
- 后端-数据库 (8项): project_status、user_role、agent_status、sender_type、
  manager_agent_id、deleted_at、mentions、project_members
"""
import re
import sys

INFILE = '/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V40.md'
OUTFILE = '/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V42.md'

with open(INFILE, 'r') as f:
    lines = f.readlines()

total = len(lines)
print(f"Read {total} lines from {INFILE}")

# ======================================
# Phase 1: Line-based multi-line fixes
# ======================================

# --- Fix 1: Remove ws-token endpoint section (lines ~613-636) ---
# Find the ws-token endpoint detail section and remove it
ws_token_start = None
ws_token_end = None
for i, line in enumerate(lines):
    if '**POST /api/v1/auth/ws-token** - 获取 WebSocket 专用 Token' in line:
        ws_token_start = i
    if ws_token_start is not None and i > ws_token_start and line.startswith('### 2.3 '):
        ws_token_end = i
        break

if ws_token_start is not None and ws_token_end is not None:
    print(f"Removing ws-token endpoint section: lines {ws_token_start+1}-{ws_token_end}")
    # Find the last non-empty line before ws_token_end
    cut_end = ws_token_end
    for j in range(ws_token_end - 1, ws_token_start, -1):
        if lines[j].strip():
            cut_end = j + 1
            break
    removed = lines[ws_token_start:cut_end]
    del lines[ws_token_start:cut_end]
    print(f"  Removed {len(removed)} lines")
else:
    print(f"WARNING: ws-token section not found (start={ws_token_start}, end={ws_token_end})")

# Refresh content after deletion
content_after_del1 = ''.join(lines)

# --- Fix 2: Replace WebSocket endpoint table and auth flow (lines ~1201-1239) ---
# Find the section markers
ws_table_start = None
ws_channel_sub = None
for i, line in enumerate(lines):
    if '| ws://host/ws' in line and '统一 WebSocket 入口' in line:
        # Go back to find the table header
        for j in range(i, max(0, i-5), -1):
            if '| 端点' in lines[j] and '|' in lines[j]:
                ws_table_start = j
                break
    if ws_table_start is not None and '**WebSocket 频道订阅**' in line:
        ws_channel_sub = i
        break

if ws_table_start is not None and ws_channel_sub is not None:
    print(f"Replacing WebSocket endpoint table: lines {ws_table_start+1}-{ws_channel_sub}")
    new_ws_content = [
        '| 端点                                 | 用途                     | 认证  |\n',
        '| ------------------------------------ | -------------------- | --- |\n',
        '| ws://host/ws/group-chat              | 项目讨论群实时消息推送     | 是   |\n',
        '| ws://host/ws/notifications           | 系统通知实时推送         | 是   |\n',
        '| ws://host/ws/workflow/:project_id   | 16步流程状态推送和流式响应 | 是   |\n',
        '\n',
        '**V42 修正**: WebSocket 端点改为多连接方案（3个独立端点），与前端 V20 §6.1 保持一致。\n',
        '前端通过 useWebSocket composable 管理三个独立 WebSocket 连接，按业务领域分离（群聊、通知、工作流），\n',
        '每个连接使用 HTTP 升级方式建立，连接 URL 中不携带 Token，连接建立后通过第一条 auth 消息使用 access_token 认证。\n',
        '\n',
        '**WebSocket 认证流程 (V42 修正)**：\n',
        '\n',
        '客户端建立 WebSocket 连接后，第一条消息必须为 auth 消息。客户端使用 HTTP 请求的 access_token 进行认证：\n',
        '\n',
        '```json\n',
        '{\n',
        '  "type": "auth",\n',
        '  "token": "access_token_value"\n',
        '}\n',
        '```\n',
        '\n',
        '**V42 修正**: (1) 认证 token 改为 access_token（与 HTTP 请求共用），移除 ws_token 专用令牌；\n',
        '(2) auth 响应 type 值改为 auth_success/auth_error，与前端 V20 §6.1 保持一致。\n',
        '\n',
        '服务端验证 access_token 后返回：\n',
        '\n',
        '认证成功:\n',
        '\n',
        '```json\n',
        '{\n',
        '  "type": "auth_success"\n',
        '}\n',
        '```\n',
        '\n',
        '认证失败:\n',
        '\n',
        '```json\n',
        '{\n',
        '  "type": "auth_error",\n',
        '  "message": "Token 无效或已过期"\n',
        '}\n',
        '```\n',
        '\n',
        '认证通过后方可发送/接收业务消息。\n',
        '\n',
    ]
    # Replace lines from ws_table_start to ws_channel_sub (exclusive of channel sub line)
    del lines[ws_table_start:ws_channel_sub]
    for idx, new_line in enumerate(new_ws_content):
        lines.insert(ws_table_start + idx, new_line)
    print(f"  Replaced with {len(new_ws_content)} lines")
else:
    print(f"WARNING: WebSocket table not found (table_start={ws_table_start}, channel_sub={ws_channel_sub})")

# Refresh content after multi-line line-based fixes
content = ''.join(lines)
print(f"Lines after multi-line fixes: {len(lines)} (was {total})")

# ======================================
# Phase 2: String replacements on content
# ======================================

replacements = [
    # --- Version metadata ---
    ('**版本**: V40', '**版本**: V42'),
    ('**日期**: 2026-06-16', '**日期**: 2026-07-12'),
    ('**状态**: 修订版V40（基于V39进行跨文档一致性再检验验证，确认20项一致性问题已全部修正并通过验证）',
     '**状态**: 修订版V42（基于V40进行跨文档一致性修正，修复前端V20/数据库V33共13项不一致问题）'),

    # --- §2.2 Auth: Remove ws-token from endpoint table ---
    ('| POST | /api/v1/auth/ws-token | 获取 WebSocket 专用 Token  | 是   |', ''),
    ('**V39 修正**: 新增 POST /api/v1/auth/ws-token 端点，与前端 V19 §5.2 端点清单保持一致。该端点用于获取 WebSocket 专用短命 Token (ws_token)，有效期 15 分钟，仅用于 WebSocket 连接认证。',
     '**V42 修正**: 移除 POST /api/v1/auth/ws-token 端点，WebSocket 认证改用 access_token 通过 auth 消息进行，与前端 V20 §6.1 保持一致。'),

    # --- §2.2.1 Token description ---
    ('- WebSocket Token (ws_token): 专用短命 Token，有效期 15 分钟（900 秒），仅用于 WebSocket 认证',
     '- WebSocket 认证: 使用 access_token 通过 auth 消息进行，与 HTTP 请求共用 Token，无需专用 WebSocket 令牌'),

    # --- §2.3 Projects: PATCH -> PUT ---
    ('| PATCH  | /api/v1/projects/:id          | 更新项目信息 (部分更新)    | 是   |',
     '| PUT    | /api/v1/projects/:id          | 更新项目信息               | 是   |'),
    ('**V39 修正**: 项目更新端点 HTTP 方法改为 PATCH，与前端 V19 §5.1 updateProject (api.patch) 和 §5.2 端点清单 (PATCH /projects/:id) 保持一致。',
     '**V42 修正**: 项目更新端点 HTTP 方法改为 PUT，与前端 V20 §5.2 端点清单 (PUT /projects/:id) 保持一致。'),
    ('**PATCH /api/v1/projects/:id** - 更新项目信息 (V39 修正: 改为 PATCH，与前端 V19 5.1/5.2 保持一致)',
     '**PUT /api/v1/projects/:id** - 更新项目信息'),
    ('说明：V39 修正，将 HTTP 方法从 PUT 改为 PATCH，与前端 V19 5.1 节 updateProject (api.patch) 和 5.2 节端点清单 (PATCH /projects/:id) 保持一致。请求体所有字段可选，仅提交需要更新的字段（语义上为部分更新）。',
     '说明：V42 修正，HTTP 方法改为 PUT，与前端 V20 §5.2 端点清单保持一致。'),

    # --- §2.3 Projects: status enum ---
    ('| status | string | 否 | null | 按状态过滤: created/in_progress/completed/cancelled |',
     '| status | string | 否 | null | 按状态过滤: active/paused/completed/archived |'),
    ('**V39 修正**: status 过滤枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致。',
     '**V42 修正**: status 过滤枚举值改为 active/paused/completed/archived，与数据库 V33 §1.3 project_status 枚举保持一致。'),
    ('      "status": "in_progress",',
     '      "status": "active",'),

    # --- §2.3 Projects: DELETE removed_at ---
    ('      "deleted_at": null', ''),
    ('    "deleted_at": "2026-06-29T10:00:00Z"', '    "status": "archived"'),
    ('V39 修正：DELETE 操作为软删除，设置 deleted_at 字段，与数据库 V30 §3.1 projects 表 deleted_at 字段一致。',
     'V42 修正：DELETE 操作为逻辑归档，将项目 status 设置为 archived，与数据库 V33 §3.1 projects 表一致（V33 已移除 deleted_at 字段）。'),

    # --- §2.5 Tasks: PATCH -> PUT ---
    ('| PATCH  | /api/v1/tasks/:id                      | 更新任务状态 (部分更新)   | 是   |',
     '| PUT    | /api/v1/tasks/:id                      | 更新任务状态              | 是   |'),
    ('**V39 修正**: 任务更新端点 HTTP 方法改为 PATCH，与前端 V19 §4.5 taskStore updateTaskStatus (api.patch) 保持一致。',
     '**V42 修正**: 任务更新端点 HTTP 方法改为 PUT，与前端 V20 §4.5 端点清单 (PUT /tasks/:id) 保持一致。'),
    ('**PATCH /api/v1/tasks/:id** - 更新任务状态 (V39 修正: 改为 PATCH)',
     '**PUT /api/v1/tasks/:id** - 更新任务状态'),
    ('说明：V39 修正，将 HTTP 方法从 PUT 改为 PATCH，与前端 V19 §4.5 taskStore updateTaskStatus (api.patch) 保持一致。',
     '说明：V42 修正，HTTP 方法改为 PUT，与前端 V20 §4.5 端点清单保持一致。'),

    # --- §2.12 Notifications: PATCH -> PUT ---
    ('| PATCH  | /api/v1/notifications/:id/read | 标记通知已读   | 是   |',
     '| PUT    | /api/v1/notifications/:id/read | 标记通知已读   | 是   |'),
    ('| PATCH  | /api/v1/notifications/read-all | 全部标记已读   | 是   |',
     '| PUT    | /api/v1/notifications/read-all | 全部标记已读   | 是   |'),
    ('**V39 修正**: 标记已读的 HTTP 方法改为 PATCH，与前端 V19 §4.6 markAsRead (api.patch) 和 §5.2 端点清单 (PATCH /notifications/:id/read) 保持一致。',
     '**V42 修正**: 标记已读的 HTTP 方法改为 PUT，与前端 V20 §4.6 端点清单 (PUT /notifications/:id/read) 保持一致。'),

    # --- §4.2 Schema: user_role ---
    ('    role: str = Field(..., pattern=r\'^(user|admin|system_admin)$\')  # V39 修正: user/admin/system_admin',
     '    role: str = Field(..., pattern=r\'^(user|admin)$\')  # V42 修正: user/admin'),
    ('**V39 修正**: (1) UserOut.role 枚举值改为 user/admin/system_admin，与数据库 V30 user_role 枚举保持一致；(2) 新增 WsTokenRequest 和 WsTokenResponse schema，支持 POST /api/v1/auth/ws-token 端点。',
     '**V42 修正**: (1) UserOut.role 枚举值改为 user/admin，移除 system_admin，与数据库 V33 §1.3 user_role 枚举保持一致；(2) 移除 WsTokenRequest 和 WsTokenResponse schema。'),

    # --- §4.2 Schema: WsToken classes ---
    ('class WsTokenRequest(BaseModel):\n    """V39 新增: WebSocket Token 请求"""\n    pass  # 从当前用户的 Access Token 中派生 ws_token，无需额外请求体\n\nclass WsTokenResponse(BaseModel):\n    """V39 新增: WebSocket Token 响应"""\n    ws_token: str\n    expires_in: int = 900',
     ''),

    # --- §4.3 Schema: project_status ---
    ('    status: str                        # V39 修正: created/in_progress/completed/cancelled',
     '    status: str                        # V42 修正: active/paused/completed/archived'),

    # --- §4.3 Schema: project deleted_at ---
    ('    deleted_at: Optional[datetime]     # V39 新增: 对应数据库 projects.deleted_at 软删除字段',
     ''),

    # --- §4.3 Schema: ProjectUpdate PATCH comment ---
    ('    """V39 修正: 配合 PATCH 方法，所有字段可选（部分更新）"""',
     '    """V42 修正: 配合 PUT 方法"""'),

    # --- §4.3 Schema: V39 correction note ---
    ('**V39 修正**: (1) ProjectOut 新增 deleted_at 字段 (Optional[datetime])，对应数据库 V30 §3.1 projects 表 deleted_at 软删除字段；(2) status 枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致；(3) ProjectUpdate 配合 PATCH 方法使用。',
     '**V42 修正**: (1) ProjectOut 移除 deleted_at 字段，与数据库 V33 §3.1 projects 表一致（V33 已移除该字段）；(2) status 枚举值改为 active/paused/completed/archived，与数据库 V33 §1.3 project_status 枚举保持一致；(3) ProjectUpdate 配合 PUT 方法使用。'),

    # --- §4.4 Schema: agent_status ---
    ('    status: str                        # V39 修正: online/offline/busy',
     '    status: str                        # V42 修正: idle/busy/error/offline'),
    ('    status: str = Field(..., pattern=r\'^(online|offline|busy)$\')   # V39 修正: online/offline/busy',
     '    status: str = Field(..., pattern=r\'^(idle|busy|error|offline)$\')   # V42 修正: idle/busy/error/offline'),
    ('**V39 修正**: (1) AgentOut.status 枚举值改为 online/offline/busy，与数据库 V30 agent_status 枚举保持一致（原 V37 使用 idle/busy/error/offline 四值）；(2) AgentStatusReport.status 正则模式改为 `^(online|offline|busy)$`。',
     '**V42 修正**: (1) AgentOut.status 枚举值改为 idle/busy/error/offline，与数据库 V33 §1.3 agent_status 枚举保持一致；(2) AgentStatusReport.status 正则模式改为 `^(idle|busy|error|offline)$`。'),

    # --- §4.5 Schema: TaskUpdate PATCH comment ---
    ('    """V39 修正: 配合 PATCH 方法"""',
     '    """V42 修正: 配合 PUT 方法"""'),

    # --- §4.7 Schema: swarm manager_agent_id ---
    ('    manager_agent_id: int              # V39 修正: 对应数据库 swarms.manager_agent_id INTEGER NOT NULL',
     '    manager_agent_id: Optional[int]    # V42 修正: 对应数据库 swarms.manager_agent_id INTEGER NULLABLE ON DELETE SET NULL'),
    ('**V39 修正**: SwarmOut.manager_agent_id 类型从 Optional[int] 改回 int (NOT NULL)，与数据库 V30 第1条变更记录一致：V30 已恢复 NOT NULL 并移除 ON DELETE SET NULL。说明：数据库 V30 明确声明 swarms.manager_agent_id 为 NOT NULL 且无 ON DELETE SET NULL 约束。',
     '**V42 修正**: SwarmOut.manager_agent_id 类型从 int 改回 Optional[int] (NULLABLE)，与数据库 V33 §3.6 swarms.manager_agent_id NULLABLE ON DELETE SET NULL 保持一致。当蜂群管理器 Agent 被删除时，manager_agent_id 自动设为 NULL。'),

    # --- §4.8 Schema: sender_type ---
    ('    sender_type: str                  # V39 修正: user/agent（与数据库 V30 一致）',
     '    sender_type: str                  # V42 修正: user/agent/system（与数据库 V33 一致）'),
    ('    mentions: Optional[Dict[str, Any]]     # V39 修正: 对应数据库 JSONB 字段',
     '    mentions: Optional[List[str]]         # V42 修正: 对应数据库 TEXT[] 字段'),

    # --- §4.8 Schema: V39 correction note ---
    ('2. **GroupMessageOut.sender_type**: 枚举值改为 user/agent（二值），与数据库 V30 §1.3 sender_type 枚举保持一致（原 V37 使用 user/agent/system 三值）',
     '2. **GroupMessageOut.sender_type**: 枚举值改为 user/agent/system（三值），与数据库 V33 §1.3 sender_type 枚举保持一致'),
    ('5. **GroupMessageOut.mentions**: 类型改为 Optional[Dict[str, Any]]，对应数据库 V30 JSONB 字段（V30 变更日志第1条明确声称已将 mentions 从 TEXT[] 改为 JSONB）',
     '5. **GroupMessageOut.mentions**: 类型改为 Optional[List[str]]，对应数据库 V33 TEXT[] 字段（V33 已将 mentions 从 JSONB 改回 TEXT[]）'),

    # --- §5.2.1 users: role ---
    ('| role          | VARCHAR(20)  | NOT NULL, DEFAULT \'user\' | 角色: user/admin/system_admin |',
     '| role          | VARCHAR(20)  | NOT NULL, DEFAULT \'user\' | 角色: user/admin |'),
    ('**V39 修正**: role 枚举值改为 user/admin/system_admin，与数据库 V30 user_role 枚举保持一致。',
     '**V42 修正**: role 枚举值改为 user/admin，移除 system_admin，与数据库 V33 §1.3 user_role 枚举保持一致。'),

    # --- §5.2.2 projects: status ---
    ('| status        | VARCHAR(20)  | NOT NULL, DEFAULT \'created\'| 状态: created/in_progress/completed/cancelled |',
     '| status        | VARCHAR(20)  | NOT NULL, DEFAULT \'active\'| 状态: active/paused/completed/archived |'),

    # --- §5.2.2 projects: deleted_at ---
    ('| deleted_at    | TIMESTAMPTZ  | NULLABLE                   | 软删除时间 (V39 新增)                      |', ''),
    ('**V39 修正**: (1) 新增 deleted_at 字段 (TIMESTAMPTZ NULLABLE)，与数据库 V30 §3.1 projects 表 deleted_at 软删除字段保持一致；(2) status 枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致。',
     '**V42 修正**: (1) 移除 deleted_at 字段，与数据库 V33 §3.1 projects 表一致（V33 已移除该字段）；(2) status 枚举值改为 active/paused/completed/archived，默认值改为 \'active\'，与数据库 V33 §1.3 project_status 枚举保持一致。'),
    ("`idx_projects_deleted_at`", ""),

    # --- §5.2.4 agents: status ---
    ('| status         | VARCHAR(20)  | NOT NULL, DEFAULT \'online\'    | online/offline/busy     |',
     '| status         | VARCHAR(20)  | NOT NULL, DEFAULT \'idle\'      | idle/busy/error/offline |'),
    ('**V39 修正**: status 枚举值改为 online/offline/busy，默认值改为 \'online\'，与数据库 V30 agent_status 枚举保持一致。',
     '**V42 修正**: status 枚举值改为 idle/busy/error/offline，默认值改为 \'idle\'，与数据库 V33 §1.3 agent_status 枚举保持一致。'),

    # --- §5.2.10 group_messages: sender_type ---
    ('| sender_type  | VARCHAR(20) | NOT NULL                     | user/agent            |',
     '| sender_type  | VARCHAR(20) | NOT NULL                     | user/agent/system     |'),

    # --- §5.2.10 group_messages: mentions ---
    ('| mentions     | JSONB       |                              | @mention 信息 (V30 改为 JSONB) |',
     '| mentions     | TEXT[]      |                              | @mention 信息 (TEXT[] 原生数组) |'),

    # --- §5.2.10 group_messages: V39 correction note ---
    ('1. **sender_type**: 枚举值改为 user/agent（二值），与数据库 V30 §1.3 sender_type 枚举保持一致',
     '1. **sender_type**: 枚举值改为 user/agent/system（三值），与数据库 V33 §1.3 sender_type 枚举保持一致'),
    ('4. **mentions**: 字段类型改为 JSONB，与数据库 V30 变更日志第1条一致（V30 已将 mentions 从 TEXT[] 改为 JSONB）',
     '4. **mentions**: 字段类型改为 TEXT[]，与数据库 V33 TEXT[] 字段一致（V33 已将 mentions 从 JSONB 改回 TEXT[]）'),

    # --- §5.2.11 swarms: manager_agent_id ---
    ('| manager_agent_id | INTEGER     | NOT NULL, FK→agents.id     | 管理者 Agent (后发/后达)         |',
     '| manager_agent_id | INTEGER     | NULLABLE, FK→agents.id ON DELETE SET NULL | 管理者 Agent (后发/后达)         |'),
    ('**V39 修正**: manager_agent_id 恢复为 NOT NULL 且移除 ON DELETE SET NULL，与数据库 V30 第1条变更记录一致（V30 已恢复 NOT NULL 并移除 ON DELETE SET NULL）。',
     '**V42 修正**: manager_agent_id 恢复为 NULLABLE 并添加 ON DELETE SET NULL，与数据库 V33 §3.6 swarms.manager_agent_id NULLABLE ON DELETE SET NULL 保持一致。'),

    # --- §5.2.12 swarm_agents: status ---
    ("| status           | VARCHAR(20) | NOT NULL, DEFAULT 'online' | online/offline/busy   |",
     "| status           | VARCHAR(20) | NOT NULL, DEFAULT 'idle'     | idle/busy/error/offline   |"),
    ('**V39 修正**: status 枚举值改为 online/offline/busy，默认值改为 \'online\'，与数据库 V30 agent_status 枚举保持一致。',
     '**V42 修正**: status 枚举值改为 idle/busy/error/offline，默认值改为 \'idle\'，与数据库 V33 §1.3 agent_status 枚举保持一致。'),

    # --- §5.2.20 project_members: dual mode ---
    ('| user_id    | BIGINT      | NOT NULL, FK→users.id          | 用户 ID              |',
     '| user_id    | BIGINT      | NULLABLE, FK→users.id          | 人类用户 ID (NULL 表示 Agent 成员)  |'),
    ('索引: `idx_pm_project`, UNIQUE: `(project_id, user_id)`',
     '| agent_id   | BIGINT      | NULLABLE, FK→agents.id         | Agent ID (NULL 表示人类用户成员)   |\n| role       | VARCHAR(20) | NOT NULL, CHECK 约束             | owner/admin/member/viewer |\n| invited_by | BIGINT      | FK→users.id                    | 邀请者用户 ID          |\n| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now()        | 加入时间               |\n\n索引: `idx_pm_project`, UNIQUE: `(project_id, user_id)`, UNIQUE: `(project_id, agent_id)`\n\n说明: V42 修正，支持用户/Agent 双成员模式。user_id 和 agent_id 均为 NULLABLE，其中必有一个有值（CHECK 约束）。'),
    ('说明: 项目创建时，创建者自动以 `owner` 角色加入。`owner` 拥有项目完全控制权，`admin` 可管理项目成员和执行流程操作，`member` 可执行流程操作和编辑项目，`viewer` 仅能查看项目和流程状态。',
     '说明: V42 修正，project_members 表支持用户和 Agent 双成员模式，与数据库 V33 §13.23 project_members 表结构保持一致。项目创建时，创建者自动以 `owner` 角色加入（user_id 有值，agent_id 为 NULL）。`owner` 拥有项目完全控制权，`admin` 可管理项目成员和执行流程操作，`member` 可执行流程操作和编辑项目，`viewer` 仅能查看项目和流程状态。'),

    # --- §6.1 Security: WebSocket Token ---
    ('- WebSocket Token (ws_token): 专用短命 Token，有效期 15 分钟（900 秒），仅用于 WebSocket 认证',
     '- WebSocket 认证: 使用 access_token 通过 auth 消息进行，与 HTTP 请求共用 Token'),
    ('**V39 修正**: WebSocket 认证使用专用 ws_token，通过 POST /api/v1/auth/ws-token 端点获取，与前端 V19 §6.3 保持一致。',
     '**V42 修正**: WebSocket 认证使用 access_token 通过 auth 消息进行，与 HTTP 请求共用 Token，与前端 V20 §6.1 保持一致。'),
    ('| WebSocket   | ws_token 认证，不受 Cookie 影响          | 连接建立后通过第一条消息验证身份  |',
     '| WebSocket   | access_token 认证，通过 auth 消息验证    | 连接建立后通过第一条消息验证身份  |'),

    # --- §11.1 Constraints: WebSocket Token ---
    ('| BR-037  | WebSocket Token有效期 (V39) | WebSocket 专用 Token (ws_token) 有效期 15 分钟 (900 秒) | security / websocket_service |',
     '| BR-037  | WebSocket 认证方式 (V42)     | WebSocket 使用 access_token 通过 auth 消息认证，与 HTTP 请求共用 Token | security / websocket_service |'),

    # --- V39/V40 correction tables at end of doc ---
    # These are historical records, update V40 reference to V42
]

# Apply replacements
changed_count = 0
for old, new in replacements:
    if old in content:
        count = content.count(old)
        content = content.replace(old, new)
        changed_count += count
        print(f"  Replaced ({count}x): {old[:60]}... -> {new[:60]}...")
    else:
        print(f"  NOT FOUND: {old[:80]}...")

print(f"\nTotal replacements applied: {changed_count}")

# Write output
with open(OUTFILE, 'w') as f:
    f.write(content)

print(f"\nWritten to {OUTFILE}")
print(f"Output size: {len(content)} chars")
