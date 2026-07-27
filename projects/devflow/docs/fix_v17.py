#!/usr/bin/env python3
import re

with open('devflow_FRONTEND_V17.md', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Header: V16 -> V17
c = c.replace(
    '**版本**: V16  \n**日期**: 2026-06-22  \n**作者**: HouWang (后旺)  \n**状态**: 修订版V16（等待后荣检验）',
    '**版本**: V17  \n**日期**: 2026-06-22  \n**作者**: HouWang (后旺)  \n**状态**: 修订版V17（跨文档一致性修正）'
)

# 2. WebSocket auth types: auth_ok -> auth_success, auth_fail -> auth_error
c = c.replace('auth_ok', 'auth_success')
c = c.replace('auth_fail', 'auth_error')

# 3. notification markAsRead: PATCH -> PUT
c = c.replace(
    "await api.patch(`/notifications/${id}/read`);",
    "await api.put(`/notifications/${id}/read`);"
)

# 4. project update: PATCH -> PUT in API module
c = c.replace(
    "return api.patch<Project>(`/projects/${id}`, data);",
    "return api.put<Project>(`/projects/${id}`, data);"
)

# 5. project steps -> progress in API module
c = c.replace(
    "export function fetchProjectSteps(id: string) {\n  return api.get<Step[]>(`/projects/${id}/steps`);\n}",
    "export function fetchProjectProgress(id: string) {\n  return api.get<ProjectProgress>(`/projects/${id}/progress`);\n}"
)

# 6. API endpoint table: PATCH /projects/:id -> PUT
c = c.replace('| PATCH | /projects/:id | 更新项目 |', '| PUT | /projects/:id | 更新项目 |')

# 7. API endpoint table: GET /projects/:id/steps -> GET /projects/:id/progress
c = c.replace('| GET | /projects/:id/steps | 项目步骤进度 |', '| GET | /projects/:id/progress | 项目进度 |')

# 8. API endpoint table: PATCH /notifications/:id/read -> PUT
c = c.replace('| PATCH | /notifications/:id/read | 标记已读 |', '| PUT | /notifications/:id/read | 标记已读 |')

# 9. Remove ws-token endpoint from auth table
c = c.replace(
    '| POST | /auth/ws-token | **V15 新增**：获取 WebSocket 专用短时效令牌 |\n| POST | /auth/logout | 退出登录 |',
    '| POST | /auth/logout | 退出登录 |'
)

# 10. Remove ws-token endpoint description section
ws_sec = '''
**V15 新增：/auth/ws-token 端点说明**

| 项 | 说明 |
|----|------|
| 方法 | POST |
| 端点 | /auth/ws-token |
| 认证 | 需要有效的 access_token（Authorization Header） |
| 请求体 | 无 |
| 响应体 | `{ "ws_token": "xxx", "expires_in": 300 }` |
| ws_token 有效期 | 5 分钟（300 秒） |
| 用途 | 仅用于 WebSocket 连接认证，不可用于 REST API |
| 安全特性 | 短时效、单次用途、与 access_token 分离、泄露后影响范围小 |
'''
c = c.replace(ws_sec, '\n')

# 11. userStore: remove wsToken/wsTokenExpiry from interface
c = c.replace(
    '  wsToken: string | null;       // V15 新增：WebSocket 专用短时效令牌\n  tokenExpiry: number | null;\n  wsTokenExpiry: number | null; // V15 新增：ws_token 过期时间',
    '  tokenExpiry: number | null;'
)

# 12. userStore: remove wsToken/wsTokenExpiry from state
c = c.replace(
    '    wsToken: null,               // V15 新增\n    tokenExpiry: null,\n    wsTokenExpiry: null,         // V15 新增',
    '    tokenExpiry: null,'
)

# 13. userStore login: remove fetchWsToken call
c = c.replace(
    '      this.user = res.data.user;\n      // V15 新增：登录后同时获取 ws_token\n      await this.fetchWsToken();',
    '      this.user = res.data.user;'
)

# 14. userStore refreshToken: remove fetchWsToken call
c = c.replace(
    '        this.tokenExpiry = Date.now() + res.data.expires_in * 1000;\n        // V15 新增：刷新 access_token 后同时刷新 ws_token\n        await this.fetchWsToken();\n        return true;',
    '        this.tokenExpiry = Date.now() + res.data.expires_in * 1000;\n        return true;'
)

# 15. Remove fetchWsToken and ensureWsToken methods
old_methods = '''    // V15 新增：获取 WebSocket 专用令牌
    async fetchWsToken() {
      try {
        const res = await api.post('/auth/ws-token');
        this.wsToken = res.data.ws_token;
        this.wsTokenExpiry = Date.now() + res.data.expires_in * 1000;
      } catch {
        // ws_token 获取失败不影响正常使用，WebSocket 重连时会重试
      }
    },
    async ensureAuthenticated()'''

new_methods = '''    async ensureAuthenticated()'''
c = c.replace(old_methods, new_methods)

old_ensure = '''    // V15 修订：确保 ws_token 有效
    async ensureWsToken() {
      if (!this.wsToken || !this.wsTokenExpiry) return false;
      // ws_token 将在 30 秒内过期，主动刷新
      if (Date.now() >= this.wsTokenExpiry - 30000) {
        await this.fetchWsToken();
        return !!this.wsToken;
      }
      return true;
    },
    logout()'''

new_ensure = '''    logout()'''
c = c.replace(old_ensure, new_ensure)

# 16. logout: remove wsToken cleanup
c = c.replace(
    '      this.refreshToken = null;\n      this.wsToken = null;           // V15 新增\n      this.tokenExpiry = null;\n      this.wsTokenExpiry = null;     // V15 新增',
    '      this.refreshToken = null;\n      this.tokenExpiry = null;'
)

# 17. persist comment
c = c.replace(
    "// 仅持久化 refreshToken，accessToken 和 wsToken 均不持久化",
    "// 仅持久化 refreshToken，accessToken 不持久化"
)

# 18. ws_token security table - remove
ws_table = '''
**ws_token 安全设计说明：**

| 对比项 | access_token | ws_token（V15 新增） |
|--------|-------------|---------------------|
| 用途 | REST API 认证（Authorization Header） | WebSocket 连接认证 |
| 有效期 | 30 分钟 | 5 分钟 |
| 传递方式 | HTTP Header（Authorization: Bearer *** | WebSocket 连接时通过 Subprotocol Header 或首次消息认证 |
| 泄露风险 | 存在于内存，XSS 可窃取 | 短时效，泄露后 5 分钟自动失效 |
| 持久化 | 不持久化（内存） | 不持久化（内存） |
| 获取方式 | /auth/login 或 /auth/refresh | /auth/ws-token（需要有效的 access_token） |
'''
c = c.replace(ws_table, '\n')

# 19. Token refresh mechanism
c = c.replace(
    '1. 登录成功后同时获取 access token、refresh token 和 ws_token\n2. access token 存储在 memory 中，refresh token 持久化到 localStorage，ws_token 存储在 memory 中',
    '1. 登录成功后获取 access token 和 refresh token\n2. access token 存储在 memory 中，refresh token 持久化到 localStorage'
)
c = c.replace(
    '5. **V15 新增**：WebSocket 连接前调用 `ensureWsToken()` 确保 ws_token 有效，过期则先刷新再建立连接',
    '5. WebSocket 认证使用 access_token，连接建立后通过首条 auth 消息携带认证'
)

# 20. V15 revision comment -> V17
c = c.replace(
    '**V15 修订：新增 ws_token 字段**\n\nV14 中 WebSocket 使用 access_token 通过 URL query 参数传递，存在安全隐患。V15 新增 `ws_token` 字段：短时效的专用 WebSocket 认证令牌，与 access_token 分离，通过后端 API 单独获取。ws_token 有效期较短（5 分钟），仅用于 WebSocket 连接认证，泄露后影响范围小。',
    '**V17 修订：移除 ws_token 字段**\n\nV15 中引入了 ws_token 字段，但后端 V35 未定义 `/auth/ws-token` 端点，存在跨文档一致性问题。V17 移除 ws_token 相关字段和方法，WebSocket 认证改回使用 access_token 通过首条 auth 消息传递（不通过 URL query），与后端 V35 2.16 节 WebSocket 认证流程保持一致。'
)

# 21. Store responsibility table
c = c.replace(
    '| userStore | 认证状态、Token 管理 | 登录接口 + refresh 接口 | 仅 refreshToken | 无（ws_token 存储在内存，不通过 WS 传递） |',
    '| userStore | 认证状态、Token 管理 | 登录接口 + refresh 接口 | 仅 refreshToken | 无（access_token 存储在内存，WebSocket 使用 auth 消息认证） |'
)

# 22. Remove ws_token expiry table section 6.1
c = c.replace(
    '''**V15 修订：ws_token 过期处理**

| 场景 | 连接行为 |
|------|---------|
| ws_token 即将过期 | 不中断现有连接，重新获取 ws_token 后在下次重连时使用 |
| ws_token 已过期导致连接被服务端拒绝 | 自动重新获取 ws_token 后重连 |

**消息路由机制：**''',
    '**消息路由机制：**'
)

# 23. Fix useWebSocket composable section 6.3
c = c.replace(
    '### 6.3 WebSocket 连接管理（useWebSocket composable）\n\n**V15 修订：认证安全修复**\n\nV14 中 WebSocket 通过 URL query 参数携带 access_token（`ws://host/ws?token=xxx`），token 会暴露在浏览器历史记录、服务端访问日志、代理日志中，可被窃取。V15 采用以下安全方案：\n\n**方案：短时效 ws_token + auth 消息认证 + 后端禁用 access log**\n\n1. 前端通过 REST API `POST /auth/ws-token` 获取短时效（5 分钟）的专用 ws_token\n2. WebSocket 连接 URL 不携带任何 token：`ws://host/ws`\n3. 连接建立后，客户端立即发送首条 auth 消息携带 ws_token 认证\n4. 后端对 `/ws` 端点禁用 access log，避免 token 泄露\n5. ws_token 与 access_token 分离，即使 ws_token 泄露，5 分钟后自动失效，且不能用于 REST API',
    '### 6.3 WebSocket 连接管理（useWebSocket composable）\n\n**V17 修订：对齐后端 V35 WebSocket 认证方案**\n\nV15 中引入了 ws_token 方案，但后端 V35 未定义 `/auth/ws-token` 端点。V17 对齐后端 V35 2.16 节定义的 WebSocket 认证流程：\n\n1. WebSocket 连接 URL 不携带任何 token：`ws://host/ws`\n2. 连接建立后，客户端立即发送首条 auth 消息携带 access_token 认证\n3. 后端对 `/ws` 端点禁用 access log，避免 token 泄露\n4. 认证成功后返回 `auth_success`，认证失败返回 `auth_error`\n\n此方案与后端 V35 2.16 节完全一致，避免了 URL query 参数传递 token 的安全风险。'
)

# 24. Replace useWebSocket code block
old_ws = '''```typescript
// src/composables/useWebSocket.ts
interface WebSocketOptions {
  groupId?: string;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null);
  const connected = ref(false);
  const reconnectAttempts = ref(0);
  const reconnectStatus = ref<'connected' | 'disconnected' | 'reconnecting'>('disconnected');
  let eventHandlers: Map<string, Function[]> = new Map();
  let heartbeatTimer: number | null = null;
  let heartbeatTimeout: number | null = null;
  let authenticated = false; // V15 新增：认证状态

  // V15 修订：URL 不携带 token
  const getWsUrl = () => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || location.host;
    return `${protocol}//${host}/ws`; // 不再携带 ?token=xxx
  };

  // V15 新增：连接建立后发送 auth 消息
  const authenticate = () => {
    const userStore = useUserStore();
    if (!userStore.wsToken) {
      // ws_token 不存在，先获取再认证
      userStore.fetchWsToken().then(() => {
        if (ws.value && ws.value.readyState === WebSocket.OPEN) {
          ws.value.send(JSON.stringify({
            type: 'auth',
            token: userStore.wsToken,
          }));
        }
      });
    } else {
      ws.value?.send(JSON.stringify({
        type: 'auth',
        token: userStore.wsToken,
      }));
    }
  };

  const startHeartbeat = () => {
    stopHeartbeat();
    heartbeatTimer = window.setInterval(() => {
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return;
      ws.value.send(JSON.stringify({ type: 'heartbeat.ping', timestamp: Date.now() }));
      heartbeatTimeout = window.setTimeout(() => {
        ElMessage.warning('网络连接不稳定，正在重连...');
        ws.value?.close(4000, 'Heartbeat timeout');
      }, 5000);
    }, 30000);
  };

  const stopHeartbeat = () => {
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
    if (heartbeatTimeout) { clearTimeout(heartbeatTimeout); heartbeatTimeout = null; }
  };

  const connect = async (groupId?: string) => {
    if (ws.value) return;

    // V15 新增：确保 ws_token 有效
    const userStore = useUserStore();
    await userStore.ensureWsToken();

    ws.value = new WebSocket(getWsUrl());

    ws.value.onopen = () => {
      connected.value = true;
      reconnectAttempts.value = 0;
      reconnectStatus.value = 'connected';

      // V15 修订：连接建立后发送 auth 消息认证
      authenticate();

      // 认证成功后再发送 chat.join
      // heartbeat 在收到 auth_success 后启动
    };

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // V15 新增：处理 auth 响应
      if (data.type === 'auth_success') {
        authenticated = true;
        startHeartbeat();
        if (groupId) {
          ws.value?.send(JSON.stringify({
            type: 'chat.join',
            payload: { group_id: groupId },
          }));
        }
        return;
      }

      if (data.type === 'auth_error') {
        // ws_token 过期或无效，重新获取后重试
        authenticated = false;
        userStore.fetchWsToken().then(() => {
          if (ws.value && ws.value.readyState === WebSocket.OPEN) {
            authenticate();
          }
        });
        return;
      }

      if (data.type === 'heartbeat.pong') {
        if (heartbeatTimeout) { clearTimeout(heartbeatTimeout); heartbeatTimeout = null; }
        return;
      }

      triggerEvent(data.type, data);
    };

    ws.value.onerror = () => {
      reconnectStatus.value = 'reconnecting';
    };

    ws.value.onclose = (event) => {
      connected.value = false;
      authenticated = false;
      stopHeartbeat();
      ws.value = null;
      if (!event.wasClean) {
        attemptReconnect(groupId);
      }
    };
  };

  const disconnect = () => {
    stopHeartbeat();
    authenticated = false;
    if (ws.value) {
      ws.value.close(1000, 'Client disconnecting');
      ws.value = null;
      connected.value = false;
      reconnectStatus.value = 'disconnected';
    }
  };

  const attemptReconnect = async (groupId?: string) => {
    const maxAttempts = 5;
    // 指数退避算法：1s -> 2s -> 4s -> 8s -> 16s（上限 30s）
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000);
    reconnectAttempts.value++;
    reconnectStatus.value = 'reconnecting';

    if (reconnectAttempts.value <= maxAttempts) {
      setTimeout(() => connect(groupId), delay);
    } else {
      reconnectStatus.value = 'disconnected';
      ElMessage.error({
        message: 'WebSocket 连接失败，已超出最大重连次数，请检查网络后刷新页面',
        duration: 5000,
      });
    }
  };

  const on = (eventType: string, handler: Function) => {
    if (!eventHandlers.has(eventType)) {
      eventHandlers.set(eventType, []);
    }
    eventHandlers.get(eventType)?.push(handler);
  };

  const off = (eventType: string, handler: Function) => {
    const handlers = eventHandlers.get(eventType);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx > -1) handlers.splice(idx, 1);
    }
  };

  const triggerEvent = (eventType: string, data: any) => {
    const handlers = eventHandlers.get(eventType);
    handlers?.forEach(h => h(data));
  };

  return {
    ws,
    connected,
    reconnectStatus,
    connect,
    disconnect,
    on,
    off,
  };
}
```'''

new_ws = '''```typescript
// src/composables/useWebSocket.ts
interface WebSocketOptions {
  groupId?: string;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null);
  const connected = ref(false);
  const reconnectAttempts = ref(0);
  const reconnectStatus = ref<'connected' | 'disconnected' | 'reconnecting'>('disconnected');
  let eventHandlers: Map<string, Function[]> = new Map();
  let heartbeatTimer: number | null = null;
  let heartbeatTimeout: number | null = null;
  let authenticated = false; // 认证状态

  const getWsUrl = () => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || location.host;
    return `${protocol}//${host}/ws`; // URL 不携带 token
  };

  // V17 修订：使用 access_token 进行 auth 消息认证
  const authenticate = () => {
    const userStore = useUserStore();
    if (ws.value && ws.value.readyState === WebSocket.OPEN && userStore.accessToken) {
      ws.value.send(JSON.stringify({
        type: 'auth',
        token: userStore.accessToken,
      }));
    }
  };

  const startHeartbeat = () => {
    stopHeartbeat();
    heartbeatTimer = window.setInterval(() => {
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return;
      ws.value.send(JSON.stringify({ type: 'heartbeat.ping', timestamp: Date.now() }));
      heartbeatTimeout = window.setTimeout(() => {
        ElMessage.warning('网络连接不稳定，正在重连...');
        ws.value?.close(4000, 'Heartbeat timeout');
      }, 5000);
    }, 30000);
  };

  const stopHeartbeat = () => {
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null; }
    if (heartbeatTimeout) { clearTimeout(heartbeatTimeout); heartbeatTimeout = null; }
  };

  const connect = (groupId?: string) => {
    if (ws.value) return;

    ws.value = new WebSocket(getWsUrl());

    ws.value.onopen = () => {
      connected.value = true;
      reconnectAttempts.value = 0;
      reconnectStatus.value = 'connected';

      // 连接建立后发送 auth 消息认证
      authenticate();
    };

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // 处理 auth 响应（对齐后端 V35 2.16 节定义的响应类型）
      if (data.type === 'auth_success') {
        authenticated = true;
        startHeartbeat();
        if (groupId) {
          ws.value?.send(JSON.stringify({
            type: 'chat.join',
            payload: { group_id: groupId },
          }));
        }
        return;
      }

      if (data.type === 'auth_error') {
        // access_token 过期或无效，跳转登录页
        authenticated = false;
        const userStore = useUserStore();
        userStore.logout();
        router.push('/login');
        ws.value?.close();
        return;
      }

      if (data.type === 'heartbeat.pong') {
        if (heartbeatTimeout) { clearTimeout(heartbeatTimeout); heartbeatTimeout = null; }
        return;
      }

      triggerEvent(data.type, data);
    };

    ws.value.onerror = () => {
      reconnectStatus.value = 'reconnecting';
    };

    ws.value.onclose = (event) => {
      connected.value = false;
      authenticated = false;
      stopHeartbeat();
      ws.value = null;
      if (!event.wasClean) {
        attemptReconnect(groupId);
      }
    };
  };

  const disconnect = () => {
    stopHeartbeat();
    authenticated = false;
    if (ws.value) {
      ws.value.close(1000, 'Client disconnecting');
      ws.value = null;
      connected.value = false;
      reconnectStatus.value = 'disconnected';
    }
  };

  const attemptReconnect = (groupId?: string) => {
    const maxAttempts = 5;
    // 指数退避算法：1s -> 2s -> 4s -> 8s -> 16s（上限 30s）
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000);
    reconnectAttempts.value++;
    reconnectStatus.value = 'reconnecting';

    if (reconnectAttempts.value <= maxAttempts) {
      setTimeout(() => connect(groupId), delay);
    } else {
      reconnectStatus.value = 'disconnected';
      ElMessage.error({
        message: 'WebSocket 连接失败，已超出最大重连次数，请检查网络后刷新页面',
        duration: 5000,
      });
    }
  };

  const on = (eventType: string, handler: Function) => {
    if (!eventHandlers.has(eventType)) {
      eventHandlers.set(eventType, []);
    }
    eventHandlers.get(eventType)?.push(handler);
  };

  const off = (eventType: string, handler: Function) => {
    const handlers = eventHandlers.get(eventType);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx > -1) handlers.splice(idx, 1);
    }
  };

  const triggerEvent = (eventType: string, data: any) => {
    const handlers = eventHandlers.get(eventType);
    handlers?.forEach(h => h(data));
  };

  return {
    ws,
    connected,
    reconnectStatus,
    connect,
    disconnect,
    on,
    off,
  };
}
```'''

c = c.replace(old_ws, new_ws)

# 25. Auth flow table
old_flow = '''
**V15 修订：认证流程变化**

| 步骤 | V14 方案 | V15 方案 |
|------|---------|---------|
| 1. 获取令牌 | 使用 access_token | 调用 POST /auth/ws-token 获取专用 ws_token（5 分钟有效） |
| 2. 建立连接 | `new WebSocket('ws://host/ws?token=xxx')` | `new WebSocket('ws://host/ws')`（URL 不携带 token） |
| 3. 认证 | 服务端从 URL query 解析 token | 连接建立后发送 `{"type": "auth", "token": "ws_token"}` |
| 4. 认证通过 | 直接进入业务通信 | 收到 `auth_success` 后启动心跳，发送 chat.join |
| 5. 认证失败 | 连接被关闭 | 收到 `auth_error` 后重新获取 ws_token 并重试 |
| 6. token 泄露影响 | access_token 泄露可访问所有 API | ws_token 泄露仅影响 WebSocket，5 分钟后自动失效 |'''

new_flow = '''
**V17 修订：认证流程（对齐后端 V35）**

| 步骤 | V14 方案 | V17 方案 |
|------|---------|---------|
| 1. 获取令牌 | 使用 access_token | 使用 access_token（与后端 V35 2.16 节一致） |
| 2. 建立连接 | `new WebSocket('ws://host/ws?token=xxx')` | `new WebSocket('ws://host/ws')`（URL 不携带 token） |
| 3. 认证 | 服务端从 URL query 解析 token | 连接建立后发送 `{"type": "auth", "token": "access_token"}` |
| 4. 认证通过 | 直接进入业务通信 | 收到 `auth_success` 后启动心跳，发送 chat.join |
| 5. 认证失败 | 连接被关闭 | 收到 `auth_error` 后跳转登录页 |
| 6. token 泄露影响 | access_token 泄露可访问所有 API | URL 不携带 token，降低日志泄露风险；access_token 仍在内存中，XSS 防护依赖 CSP |'''

c = c.replace(old_flow, new_flow)

# 26. Security table
old_sec = '''
**V15 修订：认证方式安全说明**

| 安全维度 | V14 方案 | V15 方案 |
|----------|---------|---------|
| URL 暴露 | token 出现在 WebSocket URL 中 | URL 纯净，无 token |
| 浏览器历史 | token 记录在浏览器历史 | 无 URL 参数，不记录 |
| 服务端日志 | token 出现在 access log 的 request URI 中 | 后端对 /ws 端点禁用 access log |
| 代理日志 | 反向代理记录含 token 的请求 URI | WebSocket 升级请求无 token |
| token 时效 | access_token 30 分钟 | ws_token 5 分钟 |
| token 用途 | access_token 可用于所有 API | ws_token 仅用于 WebSocket |
| 泄露影响范围 | 攻击者可访问所有 REST API | 攻击者仅能使用 WebSocket 5 分钟 |'''

new_sec = '''
**V17 修订：认证方式安全说明**

| 安全维度 | V14 方案 | V17 方案 |
|----------|---------|---------|
| URL 暴露 | token 出现在 WebSocket URL 中 | URL 纯净，无 token |
| 浏览器历史 | token 记录在浏览器历史 | 无 URL 参数，不记录 |
| 服务端日志 | token 出现在 access log 的 request URI 中 | 后端对 /ws 端点禁用 access log |
| 代理日志 | 反向代理记录含 token 的请求 URI | WebSocket 升级请求无 token |
| token 类型 | access_token | access_token（与后端 V35 2.16 节一致） |
| 响应类型 | 无明确定义 | auth_success / auth_error（与后端 V35 2.16 节一致） |
| 安全改进 | - | 相比 V14，V17 避免了 URL 携带 token 的风险，认证响应类型与后端一致 |'''

c = c.replace(old_sec, new_sec)

# 27. Auth event description
old_auth_evt = '''**V15 新增：auth 事件说明**

V14 方案通过 URL query 参数携带 token 认证 WebSocket 连接，V15 改为连接建立后通过首条 JSON 消息携带 ws_token 认证：

```
客户端                          服务端
  |                               |
  |-- WebSocket 连接请求 -------->|  (不携带 token)
  |                               |
  |<-- 连接建立 (101 Switching) --|
  |                               |
  |-- {"type": "auth",           |
      "token": "ws_token_xxx"} ->|
  |                               |
  |<-- {"type": "auth_success"} ------|  (认证通过)
  |                               |
  |-- 正常业务消息 ... ---------->|
```'''

new_auth_evt = '''**V17 修订：auth 事件说明（对齐后端 V35 2.16 节）**

WebSocket 连接建立后，客户端通过首条 JSON 消息携带 access_token 进行认证，与后端 V35 2.16 节定义的认证流程一致：

```
客户端                          服务端
  |                               |
  |-- WebSocket 连接请求 -------->|  (不携带 token)
  |                               |
  |<-- 连接建立 (101 Switching) --|
  |                               |
  |-- {"type": "auth",           |
      "token": "access_token_xxx"} ->|
  |                               |
  |<-- {"type": "auth_success"} ------|  (认证通过)
  |                               |
  |-- 正常业务消息 ... ---------->|
```'''

c = c.replace(old_auth_evt, new_auth_evt)

# 28. Auth event advantages table
c = c.replace(
    '| 对比项 | V14（query 参数） | V15（auth 消息） |',
    '| 对比项 | V14（query 参数） | V17（auth 消息） |'
)
c = c.replace(
    '| token 时效 | 长时效 access_token（30 分钟） | 短时效 ws_token（5 分钟） |',
    '| token 类型 | access_token | access_token（与后端 V35 一致） |'
)

# 29. Add V16 -> V17 revision section
old_end = '''---

**文档结束。V16 版本共 21 章，涵盖前端概述、页面设计、组件设计、状态管理、API 设计、WebSocket 通信、路由设计、国际化、样式设计、无障碍设计、多环境配置、安全设计、测试设计、构建部署、性能优化、以及 V14->V15 / V13->V14 / V12->V13 / V11->V12 / V9->V10 / V15->V16 修订记录。**'''

new_end = '''---

## 22. V16 -> V17 修订记录

### 跨文档一致性检验意见与修订对照

| 编号 | 一致性问题 | V17 修订内容 |
|------|-----------|-------------|
| 1 | 前端-后端: WebSocket auth 响应类型不一致：前端 V16 使用 'auth_ok' 和 'auth_fail'，后端 V35 2.16 定义为 'auth_success' 和 'auth_error' | 6.2 节 auth 事件通信图、6.3 节 useWebSocket 代码、V17 认证流程表：全部将 'auth_ok' 改为 'auth_success'、'auth_fail' 改为 'auth_error'，与后端 V35 2.16 节保持一致 |
| 2 | 前端-后端: 项目更新 HTTP 方法不一致：前端 V16 使用 PATCH，后端 V35 2.3 定义为 PUT | 5.1 节模块层 API 示例：updateProject 从 api.patch 改为 api.put；5.2 节 API 端点清单：/projects/:id 从 PATCH 改为 PUT，与后端 V35 2.3 节保持一致 |
| 3 | 前端-后端: 通知已读标记方法不一致：前端 V16 使用 PATCH，后端 V35 2.12 定义为 PUT | 4.6 节 notificationStore：markAsRead 从 api.patch 改为 api.put；5.2 节 API 端点清单：/notifications/:id/read 从 PATCH 改为 PUT，与后端 V35 2.12 节保持一致 |
| 4 | 前端-后端: 项目步骤端点路径不一致：前端 V16 定义了 GET /projects/:id/steps，后端 V35 对应的是 GET /api/v1/projects/:id/progress | 5.1 节模块层 API 示例：fetchProjectSteps 改为 fetchProjectProgress，路径从 /projects/${id}/steps 改为 /projects/${id}/progress；5.2 节 API 端点清单：端点从 /projects/:id/steps 改为 /projects/:id/progress，说明从"项目步骤进度"改为"项目进度"，与后端 V35 2.3 节保持一致 |
| 5 | 前端-后端: ws-token 端点：前端 V16 定义了 POST /auth/ws-token 端点，后端 V35 2.2 认证端点列表中未定义 | 4.2 节 userStore：移除 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法；5.2 节：移除 /auth/ws-token 端点及其说明；6.3 节 useWebSocket：移除 ws_token 相关逻辑，改回使用 access_token 进行 auth 消息认证；V17 认证流程、安全说明表全部更新，与后端 V35 保持一致 |

### V17 修订内容清单

| 修订项 | 位置 | V16 值 | V17 值 | 说明 |
|--------|------|--------|--------|------|
| auth_ok 响应类型 | 6.2 节、6.3 节 | auth_ok | auth_success | 对齐后端 V35 2.16 节 |
| auth_fail 响应类型 | 6.2 节、6.3 节 | auth_fail | auth_error | 对齐后端 V35 2.16 节 |
| 项目更新方法 | 5.1 节、5.2 节 | PATCH /projects/:id | PUT /projects/:id | 对齐后端 V35 2.3 节 |
| 通知已读方法 | 4.6 节、5.2 节 | PATCH /notifications/:id/read | PUT /notifications/:id/read | 对齐后端 V35 2.12 节 |
| 项目进度端点 | 5.1 节、5.2 节 | /projects/:id/steps | /projects/:id/progress | 对齐后端 V35 2.3 节 |
| 项目进度函数名 | 5.1 节 | fetchProjectSteps | fetchProjectProgress | 与端点名称对齐 |
| ws-token 端点 | 5.2 节 | 已定义 | 已移除 | 后端 V35 未定义此端点 |
| wsToken 字段 | 4.2 节 userStore | 已存在 | 已移除 | 后端 V35 未定义此端点 |
| wsTokenExpiry 字段 | 4.2 节 userStore | 已存在 | 已移除 | 后端 V35 未定义此端点 |
| fetchWsToken 方法 | 4.2 节 userStore | 已存在 | 已移除 | 后端 V35 未定义此端点 |
| ensureWsToken 方法 | 4.2 节 userStore | 已存在 | 已移除 | 后端 V35 未定义此端点 |
| WebSocket 认证方式 | 6.3 节 useWebSocket | ws_token | access_token | 对齐后端 V35 2.16 节 |
| WebSocket auth 响应处理 | 6.3 节 useWebSocket | auth_ok/auth_fail | auth_success/auth_error | 对齐后端 V35 2.16 节 |
| 认证安全说明表 | 6.3 节 | ws_token 相关 | access_token + auth 消息 | 与后端 V35 对齐 |
| 版本号 | 文档头部 | V16 | V17 | 版本号升级 |
| 文档状态 | 文档头部 | 修订版V16 | 修订版V17 | 状态更新 |

---

**文档结束。V17 版本共 22 章，涵盖前端概述、页面设计、组件设计、状态管理、API 设计、WebSocket 通信、路由设计、国际化、样式设计、无障碍设计、多环境配置、安全设计、测试设计、构建部署、性能优化、以及 V14->V15 / V13->V14 / V12->V13 / V11->V12 / V9->V10 / V15->V16 / V16->V17 修订记录。**'''

c = c.replace(old_end, new_end)

with open('devflow_FRONTEND_V17.md', 'w', encoding='utf-8') as f:
    f.write(c)

print("DONE: V17 document written successfully")
