#!/usr/bin/env python3
"""Generate V21 from V20 with cross-document consistency fixes."""

import re

src = '/home/jim/DevFlow/projects/devflow/docs/devflow_FRONTEND_V20.md'
dst = '/home/jim/DevFlow/projects/devflow/docs/devflow_FRONTEND_V21.md'

with open(src, 'r') as f:
    content = f.read()
    lines = content.split('\n')

# We'll do line-by-line transformations
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # === 1. Document header: version V20 -> V21, date, status ===
    if line.strip() == '**版本**: V20':
        new_lines.append('**版本**: V21')
        i += 1
        continue
    if line.strip() == '**日期**: 2026-06-23':
        new_lines.append('**日期**: 2026-06-24')
        i += 1
        continue
    if line.strip() == '**状态**: 修订版V20（跨文档一致性检验修正）':
        new_lines.append('**状态**: 修订版V21（跨文档一致性检验修正）')
        i += 1
        continue
    
    # === 2. §1.2 Tech selection table: WebSocket row ===
    if '| WebSocket |' in line and '多连接方案' in line:
        new_lines.append('| WebSocket | 原生 WebSocket（单连接 + 频道订阅 + ws_token 认证） | - | 统一实时通信方案（消息推送 + 流式输出），单 WebSocket 连接 ws://host/ws，通过频道订阅机制支持群聊/通知/工作流，使用 ws_token（通过 POST /api/v1/auth/ws-token 获取）进行 auth 消息认证 |')
        i += 1
        continue
    
    # === 3. V19->V20 change log: update to V20->V21 ===
    if line.strip() == '**V19 -> V20 技术选型变更说明：**':
        new_lines.append('**V20 -> V21 技术选型变更说明：**')
        i += 1
        continue
    if line.strip() == '| 变更项 | V19 方案 | V20 方案 | 变更理由 |':
        new_lines.append('| 变更项 | V20 方案 | V21 方案 | 变更理由 |')
        i += 1
        continue
    if line.strip() == '| WebSocket 连接方案 | 单连接复用 + 自定义消息路由 | 多连接方案（3个独立端点） | 对齐后端 V37 2.16 节定义的三个独立 WebSocket 端点：ws/group-chat、ws/notifications、ws/workflow/:project_id |':
        new_lines.append('| WebSocket 连接方案 | 多连接方案（3个独立端点） | 单连接 + 频道订阅 | 对齐后端 V40 §2.17 定义的 ws://host/ws 单连接 + 频道订阅机制 |')
        i += 1
        continue
    if line.strip() == '| WebSocket 认证方式 | ws_token（专用短时效令牌） | access_token（通过 auth 消息） | 后端 V37 移除了 ws-token 端点，恢复使用 access_token 进行 WebSocket 认证 |':
        new_lines.append('| WebSocket 认证方式 | access_token（通过 auth 消息） | ws_token（专用短时效令牌） | 对齐后端 V40 §2.2 定义的 POST /api/v1/auth/ws-token 端点，使用 ws_token 进行 WebSocket 认证 |')
        i += 1
        continue
    
    # === 4. §4.2 userStore: re-add ws_token support ===
    if 'V20 修订：恢复使用 access_token 进行 WebSocket 认证' in line:
        new_lines.append('**V21 修订：恢复使用 ws_token 进行 WebSocket 认证**')
        i += 1
        continue
    if 'V19 使用 ws_token 进行 WebSocket 认证。后端 V37 移除了 ws-token 端点，恢复使用 access_token 进行 WebSocket auth 消息认证，响应类型改为 auth_success/auth_error。V20 移除 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法，与后端 V37 保持一致。' in line:
        new_lines.append('V20 使用 access_token 进行 WebSocket 认证。后端 V40 恢复了 ws-token 端点并定义了 ws_token 专用认证机制，响应类型改为 auth_ok/auth_fail。V21 重新添加 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法，与后端 V40 §2.2 保持一致。')
        i += 1
        continue
    
    # Replace userState interface to add ws_token fields
    if 'interface UserState {' in line:
        new_lines.append(line)
        i += 1
        # Copy lines until closing brace, inserting ws_token fields
        while i < len(lines) and lines[i].strip() != '}':
            new_lines.append(lines[i])
            i += 1
        # Add ws_token fields before closing brace
        new_lines.append('  wsToken: string | null;')
        new_lines.append('  wsTokenExpiry: number | null;')
        new_lines.append(lines[i])  # closing brace
        i += 1
        continue
    
    # Replace state definition to add ws_token
    if 'state: (): UserState => ({' in line:
        new_lines.append(line)
        i += 1
        # Copy until the tokenExpiry line
        while i < len(lines) and 'tokenExpiry: null,' not in lines[i]:
            new_lines.append(lines[i])
            i += 1
        new_lines.append(lines[i])  # tokenExpiry: null,
        i += 1
        new_lines.append('    wsToken: null,')
        new_lines.append('    wsTokenExpiry: null,')
        continue
    
    # Replace logout to add ws_token cleanup
    if 'this.tokenExpiry = null;' in line and i + 1 < len(lines) and lines[i + 1].strip() == '},':
        new_lines.append(line)
        i += 1
        new_lines.append('      this.wsToken = null;')
        new_lines.append('      this.wsTokenExpiry = null;')
        continue
    
    # Add ws_token methods after logout method
    if line.strip() == '  },' and i > 1170 and i < 1190:
        # This is the closing of actions - we need to add ws_token methods before it
        # But we need to be careful - this closes actions block
        # Let's check if this is the actions closing brace
        # Actually let's insert before this line
        new_lines.append('    async fetchWsToken() {')
        new_lines.append('      const res = await api.post(\'/auth/ws-token\', {});')
        new_lines.append('      this.wsToken = res.data.ws_token;')
        new_lines.append('      this.wsTokenExpiry = Date.now() + res.data.expires_in * 1000;')
        new_lines.append('    },')
        new_lines.append('    async ensureWsToken() {')
        new_lines.append('      if (this.wsToken && this.wsTokenExpiry && Date.now() < this.wsTokenExpiry - 60000) {')
        new_lines.append('        return true;')
        new_lines.append('      }')
        new_lines.append('      await this.fetchWsToken();')
        new_lines.append('      return true;')
        new_lines.append('    },')
        new_lines.append(line)
        i += 1
        continue
    
    # Replace Token refresh mechanism description point 5
    if line.strip() == '5. WebSocket 认证使用 access_token，连接建立后通过首条 auth 消息携带 access_token 认证':
        new_lines.append('5. WebSocket 认证使用 ws_token（通过 POST /api/v1/auth/ws-token 获取），连接建立后通过首条 auth 消息携带 ws_token 认证')
        i += 1
        continue
    
    # === 5. §4.4 taskStore: PUT -> PATCH ===
    if 'V20 改为使用 `api.put`，与后端保持一致。' in line and 'taskStore' in ''.join(lines[max(0,i-10):i+1]):
        new_lines.append('**V21 修订**：前端 V20 使用 `api.put`，后端 V40 §2.5 定义为 `PATCH /api/v1/tasks/:id`。V21 改为使用 `api.patch`，与后端 V40 保持一致。')
        i += 1
        continue
    if 'await api.put(`/tasks/${taskId}`, { status });' in line:
        new_lines.append('      await api.patch(`/tasks/${taskId}`, { status });')
        i += 1
        continue
    
    # === 6. §4.6 notificationStore: PUT -> PATCH ===
    if 'V20 改为使用 `api.put`，与后端保持一致。' in line and 'notification' in ''.join(lines[max(0,i-10):i+1]):
        new_lines.append('**V21 修订**：前端 V20 使用 `api.put`，后端 V40 §2.12 定义为 `PATCH /api/v1/notifications/:id/read`。V21 改为使用 `api.patch`，与后端 V40 保持一致。')
        i += 1
        continue
    if 'await api.put(`/notifications/${id}/read`);' in line:
        new_lines.append('      await api.patch(`/notifications/${id}/read`);')
        i += 1
        continue
    
    # === 7. §4.7 Store responsibility table: WebSocket column ===
    if '| userStore | 认证状态、Token 管理 |' in line and 'access_token' in line:
        new_lines.append('| userStore | 认证状态、Token 管理 | 登录接口 + refresh 接口 | 仅 refreshToken | WebSocket 使用 ws_token（通过 POST /api/v1/auth/ws-token 获取） |')
        i += 1
        continue
    
    # === 8. §5.1 API example: updateProject PUT -> PATCH ===
    if line.strip() == '// V20 修订：改为 api.put，对齐后端 V37 §2.3':
        new_lines.append('// V21 修订：改为 api.patch，对齐后端 V40 §2.3')
        i += 1
        continue
    if 'return api.put<Project>(`/projects/${id}`, data);' in line:
        new_lines.append('  return api.patch<Project>(`/projects/${id}`, data);')
        i += 1
        continue
    
    # === 9. §5.2 API endpoint list ===
    # Auth section: add ws-token endpoint
    if '| POST | /auth/logout | 退出登录 |' in line:
        new_lines.append(line)
        new_lines.append('| POST | /auth/ws-token | 获取 WebSocket 专用 Token（V21 新增：对齐后端 V40 §2.2） |')
        i += 1
        continue
    
    # Remove the V20 note about removing ws-token
    if 'V20 修订：移除 POST /auth/ws-token 端点' in line:
        new_lines.append('**V21 修订：新增 POST /auth/ws-token 端点**（对齐后端 V40 §2.2，WebSocket 认证使用 ws_token）')
        i += 1
        continue
    
    # Project update: PUT -> PATCH
    if '| PUT | /projects/:id | 更新项目（V20 修订：对齐后端 V37 §2.3） |' in line:
        new_lines.append('| PATCH | /projects/:id | 更新项目（V21 修订：对齐后端 V40 §2.3） |')
        i += 1
        continue
    
    # Task update: PUT -> PATCH
    if '| PUT | /tasks/:id | 更新任务（V20 修订：对齐后端 V37 §2.5） |' in line:
        new_lines.append('| PATCH | /tasks/:id | 更新任务（V21 修订：对齐后端 V40 §2.5） |')
        i += 1
        continue
    
    # Notification read: PUT -> PATCH
    if '| PUT | /notifications/:id/read | 标记已读（V20 修订：对齐后端 V37 §2.12） |' in line:
        new_lines.append('| PATCH | /notifications/:id/read | 标记已读（V21 修订：对齐后端 V40 §2.12） |')
        i += 1
        continue
    
    # === 10. §6.1 WebSocket communication scheme: major rewrite ===
    if line.strip() == '### 6.1 多连接通信方案':
        new_lines.append('### 6.1 单连接 + 频道订阅方案')
        i += 1
        continue
    
    # Replace V20 revision note about multi-connection
    if 'V20 修订：多连接方案（对齐后端 V37 §2.16）' in line:
        new_lines.append('**V21 修订：单连接 + 频道订阅方案（对齐后端 V40 §2.17）**')
        i += 1
        continue
    if 'V19 采用全局单连接方案，整个应用生命周期内仅维护一个 WebSocket 连接。后端 V37 定义为三个独立的 WebSocket 端点：' in line:
        new_lines.append('V20 采用三个独立的 WebSocket 端点。后端 V40 §2.17 定义为 `ws://host/ws` 单连接入口，通过频道订阅机制支持群聊消息、通知推送、工作流状态推送。')
        i += 1
        continue
    if line.strip() == '- `ws://host/ws/group-chat` — 群聊消息推送和流式输出':
        new_lines.append('- 后端 V40 §2.17 定义 WebSocket 端点为 `ws://host/ws`（统一入口）')
        i += 1
        continue
    if line.strip() == '- `ws://host/ws/notifications` — 通知推送':
        new_lines.append('- 前端通过单 WebSocket 连接订阅多个频道，服务端根据消息 content 的 channel 字段进行路由分发')
        i += 1
        continue
    if line.strip() == '- `ws://host/ws/workflow/:project_id` — 工作流状态变更推送':
        new_lines.append('- 频道订阅机制：客户端发送 subscription 消息订阅频道（群聊、通知、工作流），服务端按频道推送消息')
        i += 1
        continue
    if line.strip() == 'V20 改为多连接方案，每个端点独立连接、独立认证、独立重连。':
        new_lines.append('V21 改为单连接方案，整个应用生命周期内维护一个 WebSocket 连接，通过频道订阅/取消订阅管理不同的业务领域。')
        i += 1
        continue
    
    # Replace the endpoint-to-store mapping table
    if line.strip() == '**三个 WebSocket 端点与 Store 的映射关系：**':
        new_lines.append('**频道与 Store 的映射关系：**')
        i += 1
        continue
    if line.strip() == '| WebSocket 端点 | 目标消费者 | 说明 |':
        new_lines.append('| 频道类型 | 目标消费者 | 说明 |')
        i += 1
        continue
    if line.strip() == '|---------------|----------|------|':
        new_lines.append('|----------|----------|------|')
        i += 1
        continue
    if line.strip() == '| ws/group-chat | chatStore | 群聊消息推送、流式输出 |':
        new_lines.append('| 群聊消息 | chatStore | 群聊消息推送、流式输出 |')
        i += 1
        continue
    if line.strip() == '| ws/notifications | notificationStore | 系统通知推送 |':
        new_lines.append('| 系统通知 | notificationStore | 系统通知推送 |')
        i += 1
        continue
    if line.strip() == '| ws/workflow/:project_id | projectStore、taskStore | 项目步骤变更、任务状态变更 |':
        new_lines.append('| 工作流状态 | projectStore、taskStore | 项目步骤变更、任务状态变更 |')
        i += 1
        continue
    
    # Replace connection management table
    if line.strip() == '**连接管理策略：**':
        new_lines.append('**连接管理策略：**')
        i += 1
        continue
    if '| 进入讨论群 | 建立 group-chat 连接 |' in line:
        new_lines.append('| 进入讨论群 | 订阅群聊频道（携带 groupId） |')
        i += 1
        continue
    if '| 切换讨论群 | 不重建 group-chat 连接，发送 chat.join 加入新群，同时发送 chat.leave 离开旧群 |' in line:
        new_lines.append('| 切换讨论群 | 发送 chat.join 加入新群，同时发送 chat.leave 离开旧群 |')
        i += 1
        continue
    if '| 进入项目详情 | 建立 workflow 连接（携带 projectId） |' in line:
        new_lines.append('| 进入项目详情 | 订阅工作流频道（携带 projectId） |')
        i += 1
        continue
    if '| 切换项目 | 关闭旧 workflow 连接，建立新 workflow 连接 |' in line:
        new_lines.append('| 切换项目 | 取消旧工作流频道订阅，订阅新工作流频道 |')
        i += 1
        continue
    
    # Replace auth section in §6.1
    if line.strip() == '**认证方式（V20 修订）：**':
        new_lines.append('**认证方式（V21 修订）：**')
        i += 1
        continue
    if line.strip() == '所有 WebSocket 端点使用统一的认证方式：':
        new_lines.append('WebSocket 连接使用 ws_token 进行认证：')
        i += 1
        continue
    if line.strip() == '1. WebSocket 连接 URL 不携带任何 token':
        new_lines.append('1. WebSocket 连接 URL 不携带任何 token')
        i += 1
        continue
    if line.strip() == '2. 连接建立后，客户端发送首条 auth 消息携带 access_token 进行认证':
        new_lines.append('2. 连接建立后，客户端调用 userStore.ensureWsToken() 获取 ws_token，发送首条 auth 消息携带 ws_token 进行认证')
        i += 1
        continue
    if line.strip() == '3. 后端对 WS 端点禁用 access log，避免 token 泄露':
        new_lines.append('3. 后端对 WS 端点禁用 access log，避免 token 泄露')
        i += 1
        continue
    if line.strip() == '4. 认证成功后返回 `auth_success`，认证失败返回 `auth_error`':
        new_lines.append('4. 认证成功后返回 `auth_ok`，认证失败返回 `auth_fail`')
        i += 1
        continue
    
    # Replace message routing section
    if line.strip() == '**消息路由机制（V20 修订）：**':
        new_lines.append('**消息路由机制（V21 修订）：**')
        i += 1
        continue
    if '由于采用多连接方案，每个 WebSocket 端点承载特定类型的消息，不需要全局 type 路由：' in line:
        new_lines.append('由于采用单连接方案，所有消息通过同一个 WebSocket 连接传输，使用 type 字段区分消息类型：')
        i += 1
        continue
    if line.strip() == '- group-chat 连接：message.new、message.deleted、stream.chunk、stream.done、stream.error':
        new_lines.append('- 群聊消息：message.new、message.deleted、stream.chunk、stream.done、stream.error')
        i += 1
        continue
    if line.strip() == '- notifications 连接：notification':
        new_lines.append('- 通知消息：notification')
        i += 1
        continue
    if line.strip() == '- workflow 连接：project.step.changed、task.updated':
        new_lines.append('- 工作流消息：project.step.changed、task.updated')
        i += 1
        continue
    
    # Fix priority handling comment
    if '（仅 group-chat 连接需要优先级处理）' in line:
        new_lines.append('// onmessage 处理器内部按优先级分发')
        i += 1
        continue
    
    # === 11. §6.2 WebSocket event types ===
    # Remove endpoint column from event type table
    if line.strip() == '| 事件类型 | 方向 | 端点 | 说明 |':
        new_lines.append('| 事件类型 | 方向 | 说明 |')
        i += 1
        continue
    if line.strip() == '|----------|------|------|------|':
        new_lines.append('|----------|------|------|')
        i += 1
        continue
    # Remove endpoint column from each event row
    if '| message.new | Server -> Client | group-chat | 新消息推送（消息已完成） |' in line:
        new_lines.append('| message.new | Server -> Client | 新消息推送（消息已完成） |')
        i += 1
        continue
    if '| message.deleted | Server -> Client | group-chat | 消息删除通知 |' in line:
        new_lines.append('| message.deleted | Server -> Client | 消息删除通知 |')
        i += 1
        continue
    if '| stream.chunk | Server -> Client | group-chat | Agent 回复内容增量追加 |' in line:
        new_lines.append('| stream.chunk | Server -> Client | Agent 回复内容增量追加 |')
        i += 1
        continue
    if '| stream.done | Server -> Client | group-chat | Agent 回复完成 |' in line:
        new_lines.append('| stream.done | Server -> Client | Agent 回复完成 |')
        i += 1
        continue
    if '| stream.error | Server -> Client | group-chat | 流式输出错误 |' in line:
        new_lines.append('| stream.error | Server -> Client | 流式输出错误 |')
        i += 1
        continue
    if '| notification | Server -> Client | notifications | 系统通知推送 |' in line:
        new_lines.append('| notification | Server -> Client | 系统通知推送 |')
        i += 1
        continue
    if '| project.step.changed | Server -> Client | workflow | 项目步骤推进 |' in line:
        new_lines.append('| project.step.changed | Server -> Client | 项目步骤推进 |')
        i += 1
        continue
    if '| task.updated | Server -> Client | workflow | 任务状态变更 |' in line:
        new_lines.append('| task.updated | Server -> Client | 任务状态变更 |')
        i += 1
        continue
    if '| chat.join | Client -> Server | group-chat | 加入讨论群 |' in line:
        new_lines.append('| chat.join | Client -> Server | 加入讨论群 |')
        i += 1
        continue
    if '| chat.leave | Client -> Server | group-chat | 离开讨论群 |' in line:
        new_lines.append('| chat.leave | Client -> Server | 离开讨论群 |')
        i += 1
        continue
    if '| message.send | Client -> Server | group-chat | 发送消息 |' in line:
        new_lines.append('| message.send | Client -> Server | 发送消息 |')
        i += 1
        continue
    if '| heartbeat.ping | Client -> Server | 所有 | 心跳请求 |' in line:
        new_lines.append('| heartbeat.ping | Client -> Server | 心跳请求 |')
        i += 1
        continue
    if '| heartbeat.pong | Server -> Client | 所有 | 心跳响应 |' in line:
        new_lines.append('| heartbeat.pong | Server -> Client | 心跳响应 |')
        i += 1
        continue
    if '| auth | Client -> Server | 所有 | 连接建立后的首次认证消息（携带 access_token） |' in line:
        new_lines.append('| auth | Client -> Server | 连接建立后的首次认证消息（携带 ws_token） |')
        i += 1
        continue
    
    # Replace auth section in §6.2
    if 'V20 修订：auth 事件说明（对齐后端 V37 §2.16）' in line:
        new_lines.append('**V21 修订：auth 事件说明（对齐后端 V40 §2.17）**')
        i += 1
        continue
    if 'WebSocket 连接建立后，客户端直接使用 `userStore.accessToken` 进行认证，与后端 V37 §2.16 节定义的认证流程一致：' in line:
        new_lines.append('WebSocket 连接建立后，客户端使用 `userStore.ensureWsToken()` 获取 ws_token 进行认证，与后端 V40 §2.17 节定义的认证流程一致：')
        i += 1
        continue
    # Fix auth communication diagram
    if '      "token": "access_token_xxx"} --->|' in line:
        new_lines.append('      "token": "ws_token_xxx"} --->|')
        i += 1
        continue
    if '|<-- {"type": "auth_success"} --------|  (认证通过)' in line:
        new_lines.append('  |<-- {"type": "auth_ok"} ----------------|  (认证通过)')
        i += 1
        continue
    
    # === 12. §6.3 useWebSocket composable: major rewrite ===
    if line.strip() == '### 6.3 WebSocket 连接管理（useWebSocket composable）':
        new_lines.append(line)
        i += 1
        continue
    if 'V20 修订：多连接管理 + access_token 认证（对齐后端 V37）' in line:
        new_lines.append('**V21 修订：单连接管理 + ws_token 认证（对齐后端 V40）**')
        i += 1
        continue
    if 'V19 使用单连接方案 + ws_token 认证。V20 改为三个独立 WebSocket 连接 + access_token 认证，与后端 V37 §2.16 节保持一致。' in line:
        new_lines.append('V20 使用三个独立的 WebSocket 连接 + access_token 认证。V21 改为单连接 + ws_token 认证，与后端 V40 §2.17 节保持一致。')
        i += 1
        continue
    
    # Replace the entire useWebSocket code block
    if '```typescript' in line and i + 1 < len(lines) and 'src/composables/useWebSocket.ts' in lines[i + 1]:
        # Find the start of the code block and replace the entire thing
        # Collect everything until the closing ```
        code_start = i
        i += 1
        # Skip to closing ```
        while i < len(lines) and lines[i].strip() != '```':
            i += 1
        i += 1  # skip closing ```
        
        # Write the new useWebSocket code
        new_lines.append('```typescript')
        new_lines.append('// src/composables/useWebSocket.ts')
        new_lines.append('')
        new_lines.append('export function useWebSocket() {')
        new_lines.append('  // 单 WebSocket 连接')
        new_lines.append('  const ws = ref<WebSocket | null>(null);')
        new_lines.append('  const connected = ref(false);')
        new_lines.append('  const reconnectAttempts = ref(0);')
        new_lines.append('  const reconnectStatus = ref<\'connected\' | \'disconnected\' | \'reconnecting\'>(\'disconnected\');')
        new_lines.append('')
        new_lines.append('  let handlers: Map<string, Function[]> = new Map();')
        new_lines.append('  let heartbeat: { timer: number | null; timeout: number | null } = { timer: null, timeout: null };')
        new_lines.append('  let authenticated = false;')
        new_lines.append('')
        new_lines.append('  // 已订阅的频道')
        new_lines.append('  let subscribedChannels: Set<string> = new Set();')
        new_lines.append('')
        new_lines.append('  // ==================== 工具函数 ====================')
        new_lines.append('')
        new_lines.append('  const getWsUrl = () => {')
        new_lines.append('    const protocol = location.protocol === \'https:\' ? \'wss:\' : \'ws:\';')
        new_lines.append('    const host = import.meta.env.VITE_WS_HOST || location.host;')
        new_lines.append('    return `${protocol}//${host}/ws`;')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // V21 修订：使用 ws_token 进行 auth 消息认证')
        new_lines.append('  const authenticate = async (socket: WebSocket) => {')
        new_lines.append('    const userStore = useUserStore();')
        new_lines.append('    await userStore.ensureWsToken();')
        new_lines.append('    if (socket.readyState === WebSocket.OPEN && userStore.wsToken) {')
        new_lines.append('      socket.send(JSON.stringify({')
        new_lines.append('        type: \'auth\',')
        new_lines.append('        token: userStore.wsToken,')
        new_lines.append('      }));')
        new_lines.append('    }')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  const startHeartbeat = (socket: WebSocket) => {')
        new_lines.append('    heartbeat.timer = window.setInterval(() => {')
        new_lines.append('      if (!socket || socket.readyState !== WebSocket.OPEN) return;')
        new_lines.append('      socket.send(JSON.stringify({ type: \'heartbeat.ping\', timestamp: Date.now() }));')
        new_lines.append('      heartbeat.timeout = window.setTimeout(() => {')
        new_lines.append('        ElMessage.warning(\'网络连接不稳定，正在重连...\');')
        new_lines.append('        socket.close(4000, \'Heartbeat timeout\');')
        new_lines.append('      }, 5000);')
        new_lines.append('    }, 30000);')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  const stopHeartbeat = () => {')
        new_lines.append('    if (heartbeat.timer) { clearInterval(heartbeat.timer); heartbeat.timer = null; }')
        new_lines.append('    if (heartbeat.timeout) { clearTimeout(heartbeat.timeout); heartbeat.timeout = null; }')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  const triggerEvent = (eventType: string, data: any) => {')
        new_lines.append('    const handlerList = handlers.get(eventType);')
        new_lines.append('    handlerList?.forEach(h => h(data));')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // ==================== 连接管理 ====================')
        new_lines.append('')
        new_lines.append('  const connect = () => {')
        new_lines.append('    if (ws.value && ws.value.readyState === WebSocket.OPEN) return;')
        new_lines.append('')
        new_lines.append('    ws.value = new WebSocket(getWsUrl());')
        new_lines.append('')
        new_lines.append('    ws.value.onopen = () => {')
        new_lines.append('      connected.value = true;')
        new_lines.append('      reconnectAttempts.value = 0;')
        new_lines.append('      reconnectStatus.value = \'connected\';')
        new_lines.append('      authenticated = false;')
        new_lines.append('')
        new_lines.append('      // 连接建立后发送 auth 消息（使用 ws_token）')
        new_lines.append('      authenticate(ws.value);')
        new_lines.append('    };')
        new_lines.append('')
        new_lines.append('    ws.value.onmessage = (event) => {')
        new_lines.append('      const data = JSON.parse(event.data);')
        new_lines.append('')
        new_lines.append('      // 处理 auth 响应')
        new_lines.append('      if (data.type === \'auth_ok\') {')
        new_lines.append('        authenticated = true;')
        new_lines.append('        startHeartbeat(ws.value);')
        new_lines.append('        // 重连后重新订阅所有频道')
        new_lines.append('        subscribedChannels.forEach(channel => {')
        new_lines.append('          ws.value?.send(JSON.stringify({')
        new_lines.append('            type: \'subscription\',')
        new_lines.append('            action: \'subscribe\',')
        new_lines.append('            payload: { channel },')
        new_lines.append('          }));')
        new_lines.append('        });')
        new_lines.append('        return;')
        new_lines.append('      }')
        new_lines.append('')
        new_lines.append('      if (data.type === \'auth_fail\') {')
        new_lines.append('        // ws_token 过期或无效，尝试重新获取')
        new_lines.append('        const userStore = useUserStore();')
        new_lines.append('        userStore.fetchWsToken().then(() => {')
        new_lines.append('          if (ws.value?.readyState === WebSocket.OPEN) {')
        new_lines.append('            authenticate(ws.value);')
        new_lines.append('          }')
        new_lines.append('        }).catch(() => {')
        new_lines.append('          userStore.logout();')
        new_lines.append('          router.push(\'/login\');')
        new_lines.append('          ws.value?.close();')
        new_lines.append('        });')
        new_lines.append('        return;')
        new_lines.append('      }')
        new_lines.append('')
        new_lines.append('      if (data.type === \'heartbeat.pong\') {')
        new_lines.append('        if (heartbeat.timeout) {')
        new_lines.append('          clearTimeout(heartbeat.timeout);')
        new_lines.append('          heartbeat.timeout = null;')
        new_lines.append('        }')
        new_lines.append('        return;')
        new_lines.append('      }')
        new_lines.append('')
        new_lines.append('      // 优先级处理')
        new_lines.append('      if (data.type.startsWith(\'stream.\')) {')
        new_lines.append('        triggerEvent(data.type, data); // 同步')
        new_lines.append('      } else if (data.type === \'message.new\') {')
        new_lines.append('        queueMicrotask(() => triggerEvent(data.type, data));')
        new_lines.append('      } else {')
        new_lines.append('        setTimeout(() => triggerEvent(data.type, data), 0);')
        new_lines.append('      }')
        new_lines.append('    };')
        new_lines.append('')
        new_lines.append('    ws.value.onerror = () => {')
        new_lines.append('      reconnectStatus.value = \'reconnecting\';')
        new_lines.append('    };')
        new_lines.append('')
        new_lines.append('    ws.value.onclose = (event) => {')
        new_lines.append('      connected.value = false;')
        new_lines.append('      authenticated = false;')
        new_lines.append('      stopHeartbeat();')
        new_lines.append('      ws.value = null;')
        new_lines.append('      if (!event.wasClean) {')
        new_lines.append('        attemptReconnect();')
        new_lines.append('      }')
        new_lines.append('    };')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  const disconnect = () => {')
        new_lines.append('    stopHeartbeat();')
        new_lines.append('    subscribedChannels.clear();')
        new_lines.append('    if (ws.value) {')
        new_lines.append('      ws.value.close(1000, \'Client disconnecting\');')
        new_lines.append('      ws.value = null;')
        new_lines.append('      connected.value = false;')
        new_lines.append('      reconnectStatus.value = \'disconnected\';')
        new_lines.append('    }')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // ==================== 频道订阅 ====================')
        new_lines.append('')
        new_lines.append('  const subscribeChannel = (channel: string, payload?: any) => {')
        new_lines.append('    if (!ws.value || ws.value.readyState !== WebSocket.OPEN || !authenticated) return;')
        new_lines.append('    subscribedChannels.add(channel);')
        new_lines.append('    ws.value.send(JSON.stringify({')
        new_lines.append('      type: \'subscription\',')
        new_lines.append('      action: \'subscribe\',')
        new_lines.append('      payload: { channel, ...payload },')
        new_lines.append('    }));')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  const unsubscribeChannel = (channel: string) => {')
        new_lines.append('    if (!ws.value || ws.value.readyState !== WebSocket.OPEN || !authenticated) return;')
        new_lines.append('    subscribedChannels.delete(channel);')
        new_lines.append('    ws.value.send(JSON.stringify({')
        new_lines.append('      type: \'subscription\',')
        new_lines.append('      action: \'unsubscribe\',')
        new_lines.append('      payload: { channel },')
        new_lines.append('    }));')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // 便捷方法：订阅群聊频道')
        new_lines.append('  const subscribeGroupChat = (groupId: string) => {')
        new_lines.append('    subscribeChannel(\'group-chat\', { group_id: groupId });')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // 便捷方法：订阅通知频道')
        new_lines.append('  const subscribeNotifications = () => {')
        new_lines.append('    subscribeChannel(\'notifications\');')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // 便捷方法：订阅工作流频道')
        new_lines.append('  const subscribeWorkflow = (projectId: string) => {')
        new_lines.append('    subscribeChannel(\'workflow\', { project_id: projectId });')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // ==================== 通用重连逻辑 ====================')
        new_lines.append('')
        new_lines.append('  const attemptReconnect = () => {')
        new_lines.append('    const maxAttempts = 5;')
        new_lines.append('    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000);')
        new_lines.append('    reconnectAttempts.value++;')
        new_lines.append('')
        new_lines.append('    if (reconnectAttempts.value <= maxAttempts) {')
        new_lines.append('      reconnectStatus.value = \'reconnecting\';')
        new_lines.append('      setTimeout(() => connect(), delay);')
        new_lines.append('    } else {')
        new_lines.append('      reconnectStatus.value = \'disconnected\';')
        new_lines.append('      ElMessage.error({')
        new_lines.append('        message: \'WebSocket 连接失败，已超出最大重连次数，请检查网络后刷新页面\',')
        new_lines.append('        duration: 5000,')
        new_lines.append('      });')
        new_lines.append('    }')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // ==================== 事件注册 ====================')
        new_lines.append('')
        new_lines.append('  const on = (eventType: string, handler: Function) => {')
        new_lines.append('    if (!handlers.has(eventType)) handlers.set(eventType, []);')
        new_lines.append('    handlers.get(eventType)?.push(handler);')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  const off = (eventType: string, handler: Function) => {')
        new_lines.append('    const hList = handlers.get(eventType);')
        new_lines.append('    if (hList) { const idx = hList.indexOf(handler); if (idx > -1) hList.splice(idx, 1); }')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  // ==================== 消息发送 ====================')
        new_lines.append('')
        new_lines.append('  const send = (type: string, payload?: any) => {')
        new_lines.append('    if (ws.value && ws.value.readyState === WebSocket.OPEN) {')
        new_lines.append('      ws.value.send(JSON.stringify({ type, payload }));')
        new_lines.append('    }')
        new_lines.append('  };')
        new_lines.append('')
        new_lines.append('  return {')
        new_lines.append('    connected,')
        new_lines.append('    reconnectStatus,')
        new_lines.append('    connect,')
        new_lines.append('    disconnect,')
        new_lines.append('    subscribeChannel,')
        new_lines.append('    unsubscribeChannel,')
        new_lines.append('    subscribeGroupChat,')
        new_lines.append('    subscribeNotifications,')
        new_lines.append('    subscribeWorkflow,')
        new_lines.append('    on,')
        new_lines.append('    off,')
        new_lines.append('    send,')
        new_lines.append('  };')
        new_lines.append('}')
        new_lines.append('```')
        continue
    
    # === 13. Replace V20 auth flow comparison table ===
    if line.strip() == '**V20 修订：认证流程（对齐后端 V37）**':
        new_lines.append('**V21 修订：认证流程（对齐后端 V40）**')
        i += 1
        continue
    if line.strip() == '| 步骤 | V19 方案 | V20 方案 |':
        new_lines.append('| 步骤 | V20 方案 | V21 方案 |')
        i += 1
        continue
    if line.strip() == '| 1. 获取令牌 | 通过 POST /auth/ws-token 获取 ws_token | 直接使用 userStore.accessToken |':
        new_lines.append('| 1. 获取令牌 | 直接使用 userStore.accessToken | 通过 POST /api/v1/auth/ws-token 获取 ws_token |')
        i += 1
        continue
    if line.strip() == '| 2. 建立连接 | `new WebSocket(\'ws://host/ws\')` 单连接 | 三个独立连接：`ws/group-chat`、`ws/notifications`、`ws/workflow/:project_id` |':
        new_lines.append('| 2. 建立连接 | 三个独立连接（ws/group-chat、ws/notifications、ws/workflow/:project_id） | `new WebSocket(\'ws://host/ws\')` 单连接 |')
        i += 1
        continue
    if line.strip() == '| 3. 认证 | 连接建立后调用 `userStore.ensureWsToken()` 获取 ws_token，发送 `{"type": "auth", "token": "ws_token"}` | 连接建立后直接使用 `userStore.accessToken`，发送 `{"type": "auth", "token": "access_token"}` |':
        new_lines.append('| 3. 认证 | 连接建立后直接使用 `userStore.accessToken`，发送 `{"type": "auth", "token": "access_token"}` | 连接建立后调用 `userStore.ensureWsToken()` 获取 ws_token，发送 `{"type": "auth", "token": "ws_token"}` |')
        i += 1
        continue
    if line.strip() == '| 4. 认证通过 | 收到 `auth_ok` 后启动心跳 | 收到 `auth_success` 后启动心跳 |':
        new_lines.append('| 4. 认证通过 | 收到 `auth_success` 后启动心跳 | 收到 `auth_ok` 后启动心跳 |')
        i += 1
        continue
    if line.strip() == '| 5. 认证失败 | 收到 `auth_fail` 后尝试重新获取 ws_token，失败后跳转登录页 | 收到 `auth_error` 后直接跳转登录页 |':
        new_lines.append('| 5. 认证失败 | 收到 `auth_error` 后直接跳转登录页 | 收到 `auth_fail` 后尝试重新获取 ws_token，失败后跳转登录页 |')
        i += 1
        continue
    if line.strip() == '| 6. token 泄露影响 | ws_token 仅用于 WebSocket | access_token 泄露可访问所有 API（但 WS 帧不记录到日志） |':
        new_lines.append('| 6. token 泄露影响 | access_token 泄露可访问所有 API（但 WS 帧不记录到日志） | ws_token 仅用于 WebSocket |')
        i += 1
        continue
    
    # === 14. Replace V20 auth security table ===
    if line.strip() == '**V20 修订：认证方式安全说明**':
        new_lines.append('**V21 修订：认证方式安全说明**')
        i += 1
        continue
    if line.strip() == '| 安全维度 | V19 方案 | V20 方案 |':
        new_lines.append('| 安全维度 | V20 方案 | V21 方案 |')
        i += 1
        continue
    if line.strip() == '| token 类型 | ws_token（专用短时效令牌） | access_token（与 HTTP API 共享） |':
        new_lines.append('| token 类型 | access_token（与 HTTP API 共享） | ws_token（专用短时效令牌） |')
        i += 1
        continue
    if line.strip() == '| 响应类型 | auth_ok / auth_fail | auth_success / auth_error（与后端 V37 一致） |':
        new_lines.append('| 响应类型 | auth_success / auth_error | auth_ok / auth_fail（与后端 V40 一致） |')
        i += 1
        continue
    if line.strip() == '| 连接数量 | 单连接 | 三个独立连接（与后端 V37 一致） |':
        new_lines.append('| 连接数量 | 三个独立连接 | 单连接 + 频道订阅（与后端 V40 一致） |')
        i += 1
        continue
    
    # === 15. §6.4 streaming: update to use single connection API ===
    if 'ws.connectGroup(groupId)' in line:
        new_lines.append('  ws.connect();')
        new_lines.append('  ws.subscribeGroupChat(groupId);')
        i += 1
        continue
    if 'ws.onGroup(' in line:
        new_lines.append(line.replace('ws.onGroup(', 'ws.on('))
        i += 1
        continue
    if 'ws.disconnectGroup()' in line:
        new_lines.append('  ws.disconnect();')
        i += 1
        continue
    
    # === 16. Nginx config: replace multi-endpoint with single endpoint ===
    if line.strip() == '    // V20 修订：WebSocket 多端点代理配置':
        new_lines.append('    # V21 修订：WebSocket 单端点代理配置')
        i += 1
        continue
    if line.strip() == '    # group-chat 连接':
        # Skip the three location blocks and replace with a single one
        new_lines.append('    location /ws {')
        new_lines.append('        proxy_pass http://backend:8080;')
        new_lines.append('        proxy_http_version 1.1;')
        new_lines.append('        proxy_set_header Upgrade $http_upgrade;')
        new_lines.append('        proxy_set_header Connection "upgrade";')
        new_lines.append('        proxy_set_header Host $host;')
        new_lines.append('        proxy_read_timeout 86400s;')
        new_lines.append('        access_log off;')
        new_lines.append('    }')
        # Skip the old three location blocks
        while i < len(lines) and line.strip() != '    }':
            i += 1
            if i < len(lines):
                line = lines[i]
        i += 1  # skip closing brace
        # Skip remaining location blocks for notifications and workflow
        while i < len(lines) and ('location' in lines[i] or 'proxy_pass' in lines[i] or lines[i].strip() == '}' or lines[i].strip().startswith('#') or 'proxy_' in lines[i] or 'access_log' in lines[i]):
            i += 1
            if i < len(lines):
                line = lines[i]
        continue
    
    # Actually let me handle the nginx section more carefully
    # Let me just skip this for now and handle it differently
    
    # === 17. V20->V21 change record at end of doc ===
    # We'll add this at the end
    
    new_lines.append(line)
    i += 1

# Now handle the Nginx section more carefully
# Find and replace the entire multi-endpoint nginx block
full_text = '\n'.join(new_lines)

# Replace nginx WS config
old_nginx = '''    // V20 修订：WebSocket 多端点代理配置
    # group-chat 连接
    location /ws/group-chat {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
        access_log off;
    }

    # notifications 连接
    location /ws/notifications {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
        access_log off;
    }

    # workflow 连接
    location ~ ^/ws/workflow/ {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
        access_log off;
    }'''

new_nginx = '''    # V21 修订：WebSocket 单端点代理配置
    location /ws {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
        access_log off;
    }'''

full_text = full_text.replace(old_nginx, new_nginx)

# Now add the V20->V21 change record at the end
# Find the end of the document
end_marker = '**文档结束。V20 版本共 25 章，涵盖前端概述、页面设计、组件设计、状态管理、API 设计、WebSocket 通信、路由设计、国际化、样式设计、无障碍设计、多环境配置、安全设计、测试设计、构建部署、性能优化、以及 V14->V15 / V13->V14 / V12->V13 / V11->V12 / V9->V10 / V15->V16 / V16->V17 / V17->V18 / V18->V19 / V19->V20 修订记录。**'

v21_record = '''
---

## 26. V20 -> V21 修订记录

### 跨文档一致性检验意见与修订对照

| 编号 | 一致性问题 | V21 修订内容 |
|------|-----------|-------------|
| 1 | 前端-后端: WebSocket 连接方案不一致：前端 V20 §6.1 采用多连接方案（3个独立端点：ws/group-chat、ws/notifications、ws/workflow/:project_id），后端 V40 §2.17 采用单连接方案（ws://host/ws + 频道订阅） | 6.1 节改为单连接 + 频道订阅方案，6.3 节 useWebSocket 完全重写为单连接管理（ws://host/ws），通过 subscribeChannel/unsubscribeChannel 管理频道订阅，对齐后端 V40 §2.17 |
| 2 | 前端-后端: WebSocket 认证方式不一致：前端 V20 使用 access_token 通过 auth 消息认证（已移除 ws_token），后端 V40 §2.2 定义了 POST /api/v1/auth/ws-token 端点并使用 ws_token 认证，auth 响应类型为 auth_ok/auth_fail 而非前端的 auth_success/auth_error | 4.2 节 userStore 重新添加 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法；6.2 节 auth 事件类型改回 auth_ok/auth_fail；6.3 节 useWebSocket authenticate 改为调用 ensureWsToken 获取 ws_token；5.2 节新增 POST /auth/ws-token 端点 |
| 3 | 前端-后端: HTTP 方法不一致：前端 V20 §5.2 项目更新使用 PUT /projects/:id，后端 V40 §2.3 使用 PATCH /api/v1/projects/:id | 5.1 节 updateProject 改为 api.patch；5.2 节端点清单改为 PATCH /projects/:id，与后端 V40 §2.3 保持一致 |
| 4 | 前端-后端: HTTP 方法不一致：前端 V20 §4.5 任务更新使用 PUT /tasks/:id，后端 V40 §2.5 使用 PATCH /api/v1/tasks/:id | 4.4 节 taskStore updateTaskStatus 改为 api.patch；5.2 节端点清单改为 PATCH /tasks/:id，与后端 V40 §2.5 保持一致 |
| 5 | 前端-后端: HTTP 方法不一致：前端 V20 §4.6 通知已读使用 PUT /notifications/:id/read，后端 V40 §2.12 使用 PATCH /api/v1/notifications/:id/read | 4.6 节 notificationStore markAsRead 改为 api.patch；5.2 节端点清单改为 PATCH /notifications/:id/read，与后端 V40 §2.12 保持一致 |

### V21 修订内容清单

| 修订项 | 位置 | V20 值 | V21 值 | 说明 |
|--------|------|--------|--------|------|
| WebSocket 连接方案 | 6.1 节、6.3 节 | 三连接：ws/group-chat、ws/notifications、ws/workflow/:project_id | 单连接 ws://host/ws + 频道订阅 | 对齐后端 V40 §2.17 |
| WebSocket 认证方式 | 6.3 节 useWebSocket | access_token | ws_token | 对齐后端 V40 §2.2 |
| auth 响应类型 | 6.2 节、6.3 节 | auth_success/auth_error | auth_ok/auth_fail | 对齐后端 V40 §2.17 |
| ws-token 端点 | 5.2 节 | 已移除 | POST /auth/ws-token | 对齐后端 V40 §2.2 |
| wsToken 字段 | 4.2 节 userStore | 已移除 | wsToken: string \\| null | 对齐后端 V40 §2.2 |
| wsTokenExpiry 字段 | 4.2 节 userStore | 已移除 | wsTokenExpiry: number \\| null | 对齐后端 V40 §2.2 |
| fetchWsToken 方法 | 4.2 节 userStore | 已移除 | 重新添加 | 获取 WebSocket 专用认证令牌 |
| ensureWsToken 方法 | 4.2 节 userStore | 已移除 | 重新添加 | 验证 ws_token 有效性，过期自动刷新 |
| 项目更新方法 | 5.1 节、5.2 节 | PUT /projects/:id (api.put) | PATCH /projects/:id (api.patch) | 对齐后端 V40 §2.3 |
| 通知已读方法 | 4.6 节、5.2 节 | PUT /notifications/:id/read (api.put) | PATCH /notifications/:id/read (api.patch) | 对齐后端 V40 §2.12 |
| 任务状态更新方法 | 4.4 节、5.2 节 | PUT /tasks/:id (api.put) | PATCH /tasks/:id (api.patch) | 对齐后端 V40 §2.5 |
| useWebSocket 重写 | 6.3 节 | 三个独立 WebSocket 连接管理 | 单连接 + subscribeChannel/unsubscribeChannel | 对齐后端 V40 §2.17 |
| Nginx WS 代理 | 14.3 节 | 三个 /ws/* 端点代理 | 单一 /ws 端点代理 | 对齐单连接方案 |
| 技术选型 WebSocket | 1.2 节 | 多连接方案（3个独立端点） | 单连接 + 频道订阅 + ws_token 认证 | 对齐后端 V40 |
| 版本号 | 文档头部 | V20 | V21 | 版本号升级 |
| 文档状态 | 文档头部 | 修订版V20（跨文档一致性检验修正） | 修订版V21（跨文档一致性检验修正） | 状态更新 |

---

**文档结束。V21 版本共 26 章，涵盖前端概述、页面设计、组件设计、状态管理、API 设计、WebSocket 通信、路由设计、国际化、样式设计、无障碍设计、多环境配置、安全设计、测试设计、构建部署、性能优化、以及 V14->V15 / V13->V14 / V12->V13 / V11->V12 / V9->V10 / V15->V16 / V16->V17 / V17->V18 / V18->V19 / V19->V20 / V20->V21 修订记录。**'''

full_text = full_text.replace(end_marker, v21_record)

with open(dst, 'w') as f:
    f.write(full_text)

print(f"V21 document generated: {dst}")
print(f"Total lines: {full_text.count(chr(10))}")
