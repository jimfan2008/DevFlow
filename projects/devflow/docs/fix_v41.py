#!/usr/bin/env python3
import re

src = "/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V40.md"
dst = "/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V41.md"

with open(src, "r", encoding="utf-8") as f:
    text = f.read()

original_len = len(text)

# 1. Version and status
text = text.replace("**版本**: V40", "**版本**: V41")
text = text.replace("**状态**: 修订版V40（基于V39进行跨文档一致性再检验验证，确认20项一致性问题已全部修正并通过验证）",
                    "**状态**: 修订版V41（基于V40进行跨文档一致性检验修正，修复前端V20/数据库V33共13项不一致问题）")

# 2. Remove ws-token endpoint from auth table
text = text.replace("| POST | /api/v1/auth/ws-token | 获取 WebSocket 专用 Token  | 是   |\n", "")
text = text.replace("**V39 修正**: 新增 POST /api/v1/auth/ws-token 端点，与前端 V19 §5.2 端点清单保持一致。该端点用于获取 WebSocket 专用短命 Token (ws_token)，有效期 15 分钟，仅用于 WebSocket 连接认证。\n",
                    "**V41 修正**: 移除 POST /api/v1/auth/ws-token 端点。WebSocket 认证直接使用前端的 access_token，与前端 V20 保持一致。\n")

# 3. Remove ws-token detailed endpoint section
old_ws = """**POST /api/v1/auth/ws-token** - 获取 WebSocket 专用 Token (V39 新增)

V39 新增：与前端 V19 §5.2 端点清单保持一致。

请求头: `Authorization: Bearer *** (200 OK):

```json
{
  "success": true,
  "data": {
    "ws_token": "ws_eyJhbG...NiIs...",
    "expires_in": 900
  },
  "message": "WebSocket Token 获取成功"
}
```

说明：
- ws_token 有效期 15 分钟（900 秒）
- 仅用于 WebSocket 连接认证，不可用于 REST API
- 服务端通过 Redis 验证 ws_token 有效性，键格式 `ws_token:{token_hash}`

"""
new_ws = """**V41 修正**: WebSocket 认证方案变更

V41 修正：前端 V20 已移除 ws_token 方案，WebSocket 认证直接使用 access_token 通过 auth 消息进行。后端同步修正，不再需要专用的 ws-token 端点。

"""
text = text.replace(old_ws, new_ws)

# 4. Token description - access_token instead of ws_token
text = text.replace("- WebSocket Token (ws_token): 专用短命 Token，有效期 15 分钟（900 秒），仅用于 WebSocket 认证",
                    "- WebSocket 认证: 直接使用 access_token 通过 auth 消息进行认证，无需专用 ws_token")

# 5. WebSocket endpoints: single -> multi
old_ws_endpoints = """### 2.17 WebSocket 端点

| 端点                    | 用途                           | 认证  |
| --------------------- | ---------------------------- | --- |
| ws://host/ws          | 统一 WebSocket 入口 (群聊、通知、流程状态) | 是   |

**V39 修正**: WebSocket 端点统一为 `ws://host/ws` 单连接，与前端 V19 §6.3 useWebSocket 保持一致。前端通过单 WebSocket 连接订阅多个频道（群聊消息、通知、流程状态），服务端根据消息 content 的 channel 字段进行路由分发。架构 V24 §3.5 定义的路径格式 `/ws/v1/groups/{id}` 为频道标识而非独立端点，实际连接入口统一为 `ws://host/ws`。"""

new_ws_endpoints = """### 2.17 WebSocket 端点

| 端点                              | 用途                 | 认证  |
| ------------------------------- | ------------------ | --- |
| ws://host/ws/group-chat             | 群聊消息实时推送         | 是   |
| ws://host/ws/notifications          | 通知实时推送           | 是   |
| ws://host/ws/workflow/:project_id   | 项目流程状态推送      | 是   |

**V41 修正**: WebSocket 端点改为多连接方案，与前端 V20 §6.1 保持一致。前端采用 3 个独立 WebSocket 端点分别处理群聊消息、通知和项目流程状态推送，不再使用单连接加频道订阅的模式。"""
text = text.replace(old_ws_endpoints, new_ws_endpoints)

# 6. WebSocket auth flow
old_auth_flow = """**WebSocket 认证流程 (V39 修正)**：

客户端建立 WebSocket 连接后，第一条消息必须为 auth 消息。客户端使用 ws_token 进行认证：

```json
{
  "type": "auth",
  "token": "ws_token_value"
}
```

**V39 修正**: (1) 认证 token 改为 ws_token，通过 POST /api/v1/auth/ws-token 端点获取；(2) auth 响应 type 值改为 auth_ok/auth_fail，与前端 V19 §6.3 保持一致。

服务端验证 ws_token 后返回：

认证成功:

```json
{
  "type": "auth_ok"
}
```

认证失败:

```json
{
  "type": "auth_fail",
  "message": "Token 无效或已过期"
}
```

认证通过后方可发送/接收业务消息。"""

new_auth_flow = """**WebSocket 认证流程 (V41 修正)**：

客户端建立 WebSocket 连接后，第一条消息必须为 auth 消息。客户端使用 access_token 进行认证：

```json
{
  "type": "auth",
  "token": "access_token_value"
}
```

**V41 修正**: (1) 认证 token 改为 access_token（直接使用 HTTP 认证的 JWT Token），移除 ws_token 专用方案；(2) auth 响应 type 值改为 auth_success/auth_error，与前端 V20 保持一致。

服务端验证 access_token 后返回：

认证成功:

```json
{
  "type": "auth_success"
}
```

认证失败:

```json
{
  "type": "auth_error",
  "message": "Token 无效或已过期"
}
```

认证通过后方可发送/接收业务消息。"""
text = text.replace(old_auth_flow, new_auth_flow)

# 7. WebSocket channel subscription -> message format
old_channels = """**WebSocket 频道订阅**:

认证成功后，客户端可订阅以下频道：

```json
{
  "type": "subscribe",
  "channel": "group-chat:{group_id}"
}
```

```json
{
  "type": "subscribe",
  "channel": "notifications"
}
```

```json
{
  "type": "subscribe",
  "channel": "workflow:{project_id}"
}
```

服务端根据 channel 将消息路由到对应的订阅者。"""

new_channels = """**WebSocket 消息格式**:

多连接方案下，每个 WebSocket 连接仅处理对应类型消息，无需频道订阅。消息格式由各端点独立定义：

- **群聊消息**: 收到新的 group_message 时推送
- **通知消息**: 收到新的 notification 时推送
- **流程状态**: 项目 workflow 状态变更时推送"""
text = text.replace(old_channels, new_channels)

# 8. HTTP methods: PATCH -> PUT
text = text.replace("| PATCH  | /api/v1/projects/:id          | 更新项目信息 (部分更新)    | 是   |",
                    "| PUT    | /api/v1/projects/:id          | 更新项目信息           | 是   |")
text = text.replace("**V39 修正**: 项目更新端点 HTTP 方法改为 PATCH，与前端 V19 §5.1 updateProject (api.patch) 和 §5.2 端点清单 (PATCH /projects/:id) 保持一致。",
                    "**V41 修正**: 项目更新端点 HTTP 方法改为 PUT，与前端 V20 §5.2 端点清单 (PUT /projects/:id) 保持一致。")
text = text.replace("**PATCH /api/v1/projects/:id** - 更新项目信息 (V39 修正: 改为 PATCH，与前端 V19 5.1/5.2 保持一致)",
                    "**PUT /api/v1/projects/:id** - 更新项目信息 (V41 修正: 改为 PUT，与前端 V20 保持一致)")
text = text.replace("""说明：V39 修正，将 HTTP 方法从 PUT 改为 PATCH，与前端 V19 5.1 节 updateProject (api.patch) 和 5.2 节端点清单 (PATCH /projects/:id) 保持一致。请求体所有字段可选，仅提交需要更新的字段（语义上为部分更新）。""",
                    """说明：V41 修正，将 HTTP 方法改为 PUT，与前端 V20 §5.2 节 updateProject (PUT /projects/:id) 保持一致。""")

text = text.replace("| PATCH  | /api/v1/tasks/:id                      | 更新任务状态 (部分更新)   | 是   |",
                    "| PUT    | /api/v1/tasks/:id                      | 更新任务状态            | 是   |")
text = text.replace("**V39 修正**: 任务更新端点 HTTP 方法改为 PATCH，与前端 V19 §4.5 taskStore updateTaskStatus (api.patch) 保持一致。",
                    "**V41 修正**: 任务更新端点 HTTP 方法改为 PUT，与前端 V20 §4.5 taskStore updateTaskStatus (PUT /tasks/:id) 保持一致。")
text = text.replace("**PATCH /api/v1/tasks/:id** - 更新任务状态 (V39 修正: 改为 PATCH)",
                    "**PUT /api/v1/tasks/:id** - 更新任务状态 (V41 修正: 改为 PUT)")
text = text.replace("""说明：V39 修正，将 HTTP 方法从 PUT 改为 PATCH，与前端 V19 §4.5 taskStore updateTaskStatus (api.patch) 保持一致。""",
                    """说明：V41 修正，将 HTTP 方法改为 PUT，与前端 V20 §4.5 节 updateTaskStatus (PUT /tasks/:id) 保持一致。""")

text = text.replace("| PATCH  | /api/v1/notifications/:id/read | 标记通知已读   | 是   |",
                    "| PUT    | /api/v1/notifications/:id/read | 标记通知已读   | 是   |")
text = text.replace("**V39 修正**: 标记已读的 HTTP 方法改为 PATCH，与前端 V19 §4.6 markAsRead (api.patch) 和 §5.2 端点清单 (PATCH /notifications/:id/read) 保持一致。",
                    "**V41 修正**: 标记已读的 HTTP 方法改为 PUT，与前端 V20 §4.6 markAsRead (PUT /notifications/:id/read) 保持一致。")

# 9. Backend-Database: project_status enum
text = text.replace("| status | string | 否 | null | 按状态过滤: created/in_progress/completed/cancelled |",
                    "| status | string | 否 | null | 按状态过滤: active/paused/completed/archived |")
text = text.replace("**V39 修正**: status 过滤枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致。",
                    "**V41 修正**: status 过滤枚举值改为 active/paused/completed/archived，与数据库 V33 §1.3 project_status 枚举保持一致。")

# 10. user_role enum
text = text.replace("    role: str                          # V39 修正: user/admin/system_admin，与数据库 V30 枚举一致",
                    "    role: str                          # V41 修正: user/admin，与数据库 V33 枚举一致")

# 11. agent_status enum
text = text.replace("online/offline/busy", "idle/busy/error/offline")

# 12. sender_type enum
text = text.replace("sender_type (user/agent 二值枚举)", "sender_type (user/agent/system 三值枚举)")
text = text.replace("sender_type: str  # user/agent", "sender_type: str  # user/agent/system")

# 13. swarms.manager_agent_id
text = text.replace("manager_agent_id: int  # NOT NULL", "manager_agent_id: int | None  # NULLABLE, ON DELETE SET NULL")
text = text.replace("manager_agent_id (NOT NULL)", "manager_agent_id (NULLABLE, ON DELETE SET NULL)")

# 14. projects.deleted_at
text = text.replace("deleted_at: str | None", "# V41: deleted_at 已移除，与数据库 V33 一致")

# 15. group_messages.mentions JSONB -> TEXT[]
text = text.replace("    mentions: list  # JSONB: 被 @ 的用户 ID 列表",
                    "    mentions: list[str]  # TEXT[]: 被 @ 的用户名列表，与数据库 V33 §13.13 一致")
text = text.replace("mentions: Optional[list]     # JSONB",
                    "mentions: Optional[list[str]]     # TEXT[]，与数据库 V33 §13.13 一致")

# 16. DELETE project response
old_delete = """**DELETE /api/v1/projects/:id** - 软删除项目

V39 修正：DELETE 操作为软删除，设置 deleted_at 字段，与数据库 V30 §3.1 projects 表 deleted_at 字段一致。

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "status": "cancelled",
    "deleted_at": "2026-06-29T10:00:00Z"
  },
  "message": "项目已删除"
}
```"""
new_delete = """**DELETE /api/v1/projects/:id** - 删除项目

V41 修正：DELETE 操作将项目 status 更新为 archived，与数据库 V33 §3.1 projects 表一致（已移除 deleted_at 字段）。

成功响应 (200 OK):

```json
{
  "success": true,
  "data": {
    "project_id": 1,
    "status": "archived"
  },
  "message": "项目已删除"
}
```"""
text = text.replace(old_delete, new_delete)

# 17. WsTokenRequest/WsTokenResponse schema removal
old_ws_schema = """class WsTokenRequest(BaseModel):
    \"\"\"V39 新增: WebSocket Token 请求\"\"\"
    pass  # 从当前用户的 Access Token 中派生 ws_token，无需额外请求体


class WsTokenResponse(BaseModel):
    \"\"\"V39 新增: WebSocket Token 响应\"\"\"
    ws_token: str
    expires_in: int  # 15 分钟 = 900 秒"""
new_ws_schema = """# V41 修正: WsTokenRequest 和 WsTokenResponse 已移除，WebSocket 认证直接使用 access_token"""
text = text.replace(old_ws_schema, new_ws_schema)

# 18. Security section ws_token -> access_token
text = text.replace("- WebSocket 使用 `ws_token` 进行认证",
                    "- WebSocket 使用 `access_token` 进行认证")
text = text.replace("- WebSocket Token (ws_token): 专用短命 Token，有效期 15 分钟（900 秒），仅用于 WebSocket 认证",
                    "- WebSocket 认证: 使用 access_token 通过 auth 消息认证，无需专用 Token")
text = text.replace("**V39 修正**: WebSocket 认证使用专用 ws_token，通过 POST /api/v1/auth/ws-token 端点获取，与前端 V19 §6.3 保持一致。",
                    "**V41 修正**: WebSocket 认证直接使用 access_token 通过 auth 消息进行，已移除 ws_token 专用方案，与前端 V20 保持一致。")
text = text.replace("| WebSocket   | ws_token 认证，不受 Cookie 影响          | 连接建立后通过第一条消息验证身份  |",
                    "| WebSocket   | access_token 认证，通过 auth 消息进行        | 连接建立后通过第一条消息验证身份  |")
text = text.replace("| BR-037  | WebSocket Token有效期 (V39) | WebSocket 专用 Token (ws_token) 有效期 15 分钟 (900 秒) | security / websocket_service |",
                    "| BR-037  | WebSocket 认证方式 (V41) | WebSocket 使用 access_token 通过 auth 消息认证，响应类型为 auth_success/auth_error | security / websocket_service |")

# 19. Consistency check table updates
text = text.replace("| 1 | 【严重】WebSocket 认证方式不一致：前端 V19 §6.3 使用 ws_token 进行 auth 消息认证，期望响应 auth_ok/auth_fail；后端 V37 明确使用 access_token 认证，响应类型为 auth_success/auth_error | 不一致 | 改为 ws_token 认证（通过 POST /api/v1/auth/ws-token 获取），响应类型改为 auth_ok/auth_fail | ✅ 已修正 | §2.2, §2.17, §4.2, §6.1 |",
                    "| 1 | V41 修正：WebSocket 认证方式统一为 access_token 加 auth_success/auth_error，与前端 V20 保持一致 | 已修正 | - | ✅ V41 | §2.2, §2.17 |")
text = text.replace("| 4 | 【严重】ws-token 端点：前端 V19 §5.2 定义了 POST /auth/ws-token，后端 V37 无此端点 | 不一致 | 新增 POST /api/v1/auth/ws-token 端点，返回 ws_token (15分钟有效期) | ✅ 已修正 | §2.2, §2.2.2, §4.2 |",
                    "| 4 | V41 修正：ws-token 端点已移除，WebSocket 认证直接使用 access_token，与前端 V20 保持一致 | 已修正 | - | ✅ V41 | §2.2, §2.17 |")
text = text.replace("| 1 | WebSocket 端点不一致：架构 V24 §3.5 定义 WS `/ws/v1/groups/{id}`，后端 V37 §2.16 定义三个独立端点 | 不一致 | 统一为 `ws://host/ws` 单连接入口，`/ws/v1/groups/{id}` 作为频道标识而非独立端点 | ✅ 已修正 | §2.17 |",
                    "| 1 | V41 修正：WebSocket 端点改为多连接方案（ws/group-chat, ws/notifications, ws/workflow/:project_id），与前端 V20 §6.1 保持一致 | 已修正 | - | ✅ V41 | §2.17 |")
text = text.replace("| 5 | WebSocket 端点不一致：前端 V19 §6.3 使用 ws://host/ws 单连接，后端 V37 定义三个独立端点 | 不一致 | 统一为 ws://host/ws 单连接，通过频道订阅机制支持群聊、通知、流程状态 | ✅ 已修正 | §2.17 |",
                    "| 5 | V41 修正：WebSocket 端点改为多连接方案（3个独立端点），与前端 V20 §6.1 保持一致 | 已修正 | - | ✅ V41 | §2.17 |")

# 20. Comparison table updates
text = text.replace("| ws-token 端点 | POST /api/v1/auth/ws-token | POST /auth/ws-token | ✅ |",
                    "| ws-token 端点 | V41 已移除 (使用 access_token) | V20 无此端点 | ✅ |")
text = text.replace("| WebSocket 端点 | ws://host/ws (单连接) | ws://host/ws (单连接) | ✅ |",
                    "| WebSocket 端点 | 多连接方案 (3端点) | 多连接方案 (3端点) | ✅ |")

# 21. project_members dual member model
text = text.replace("ProjectMember (user_id NOT NULL 仅支持人类成员)",
                    "ProjectMember (user_id/agent_id 双成员模式，均 NULLABLE, CHECK 约束)")

# 22. Example JSON status updates
text = text.replace('"status": "in_progress"', '"status": "paused"')
text = text.replace('"current_status": "in_progress"', '"current_status": "paused"')
text = text.replace('"status": "cancelled"', '"status": "archived"')

# 23. V39 correction note for UserOut
old_userout_note = "**V39 修正**: (1) UserOut.role 枚举值改为 user/admin/system_admin，与数据库 V30 user_role 枚举保持一致；(2) 新增 WsTokenRequest 和 WsTokenResponse schema，支持 POST /api/v1/auth/ws-token 端点。"
new_userout_note = "**V41 修正**: UserOut.role 枚举值改为 user/admin，与数据库 V33 §1.3 user_role 枚举保持一致（已移除 system_admin）。"
text = text.replace(old_userout_note, new_userout_note)

# Save
with open(dst, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Original: {original_len} chars")
print(f"New: {len(text)} chars")
print(f"Diff: {len(text) - original_len} chars")
print(f"V41 saved to: {dst}")
