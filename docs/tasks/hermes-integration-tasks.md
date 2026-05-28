# Hermes Agent 集成 — 编码任务列表

> **基于文档**：`hermes-integration-design.md` + `hermes-integration-spec.md`
> **方案决策**：方案 A（Hermes API Server 通信）为主，方案 B（Socket.IO BFF）为可选增强
> **核心变更**：废弃 7 个旧模块，新增 8 个后端模块 + 7 个前端文件 + 1 个数据库迁移

---

## 1. 后端基础层：数据类型与配置

### T1.1 创建 Hermes 数据类型定义
- [ ] 新增 `backend/app/services/hermes/__init__.py`，创建 `hermes` 包
- [ ] 新增 `backend/app/services/hermes/types.py`，定义所有数据类型：
  - `HermesConfig`（config.yaml 结构化配置）
  - `ProviderCredential`（Provider 凭证）
  - `APIServerConfig`（API Server 配置 + `base_url`/`v1_url` 属性）
  - `DiscoveryResult`（发现结果）
  - `APIServerInfo`（API Server 可达性信息）
  - `DiagnosticStep`（诊断步骤）
  - `ChatChunk`（流式 chunk，含 content/reasoning_content/tool_calls/finish_reason）
  - `ChatCompletionResult`（非流式完成结果）
  - `ModelInfo`（模型信息）
  - `ProfileInfo`（Profile 信息）
  - `SSEEvent`（SSE 事件：event + data）
  - `HermesAPIError`（自定义异常类）
- [ ] 所有 dataclass 使用 `frozen=True`（不可变类型），枚举值使用 `Literal` 类型

**依赖**：无
**复杂度**：低（1h）
**涉及文件**：`backend/app/services/hermes/__init__.py`（新增），`backend/app/services/hermes/types.py`（新增）
**验收标准**：所有类型可正常实例化，`HermesConfig.from_raw()` 能从 config.yaml 原始字典解析

---

### T1.2 新增 Settings 配置项
- [ ] 修改 `backend/app/core/config.py`（或对应 Settings 类文件），新增以下配置项：
  - `HERMES_API_BASE`：默认 `http://host.docker.internal:8642/v1`
  - `HERMES_API_KEY`：默认空
  - `HERMES_MODEL`：默认 `hermes-agent`
  - `HERMES_PROFILES_PATH`：默认 `/hermes-home`
  - `HERMES_BFF_URL`：默认空（可选 Socket.IO BFF）
  - `HERMES_HEALTH_INTERVAL`：默认 30（秒）
  - `HERMES_MAX_CONCURRENT_CHATS`：默认 5
  - `HERMES_SHOW_THINKING`：默认 False

**依赖**：无
**复杂度**：低（0.5h）
**涉及文件**：`backend/app/core/config.py`（修改）
**验收标准**：应用启动时能正确读取环境变量，Docker 环境下 `HERMES_API_BASE` 为 `host.docker.internal:8642`

---

### T1.3 创建 ORM 模型
- [ ] 新增 `backend/app/models/hermes_session.py`，定义 `HermesSession` 表（id, user_id, profile_name, model_id, display_name, message_count, is_active, created_at, updated_at）
- [ ] 新增 `backend/app/models/hermes_message.py`，定义 `HermesMessage` 表（id, session_id, role, content, thinking_content, tool_calls, model, is_streaming, is_interrupted, timestamp）
- [ ] 在 `backend/app/models/__init__.py` 中注册新模型
- [ ] 确保 `HermesSession.user_id` 有 `ForeignKey("users.id")`，`HermesMessage.session_id` 有 `ForeignKey("hermes_sessions.id")`
- [ ] 创建索引：`ix_hermes_sessions_user_id`、`ix_hermes_messages_session_id`、`ix_hermes_messages_timestamp`

**依赖**：T1.1
**复杂度**：中（1.5h）
**涉及文件**：`backend/app/models/hermes_session.py`（新增），`backend/app/models/hermes_message.py`（新增），`backend/app/models/__init__.py`（修改）
**验收标准**：模型可被 Alembic autogenerate 识别，表结构与设计文档一致

---

### T1.4 创建 Alembic 数据库迁移
- [ ] 新增 `backend/alembic/versions/004_hermes_sessions_messages.py`，创建 `hermes_sessions` 和 `hermes_messages` 两张表
- [ ] 迁移包含所有字段、外键、索引、枚举类型（`hermes_msg_role`）
- [ ] 编写 `downgrade()` 支持回滚（删除两张表和枚举类型）
- [ ] 在开发环境执行 `alembic upgrade head` 验证迁移成功

**依赖**：T1.3
**复杂度**：中（1.5h）
**涉及文件**：`backend/alembic/versions/004_hermes_sessions_messages.py`（新增）
**验收标准**：迁移执行后数据库中存在 `hermes_sessions` 和 `hermes_messages` 表，字段和索引正确

---

## 2. 后端核心层：配置读取与发现

### T2.1 实现 HermesConfigReader
- [ ] 新增 `backend/app/services/hermes/hermes_config.py`，实现 `HermesConfigReader` 类：
  - `read_config(profile_name)` → 读取 config.yaml，返回 `HermesConfig`
  - `read_auth_pool()` → 读取 auth.json，返回 `list[ProviderCredential]`
  - `read_env()` → 读取 .env 文件，返回 `dict[str, str]`
  - `scan_profiles()` → 扫描 profiles/ 目录，返回 `list[ProfileInfo]`
  - `read_soul(profile_name)` → 读取 SOUL.md（前 300 字）
  - `extract_api_server_config(config)` → 从 config 提取 API Server 配置
  - `mask_api_key(key)` → 密钥脱敏（保留前 3 后 3）
- [ ] 适配 Docker 挂载路径（`/hermes-home`）和 Windows 路径（`LOCALAPPDATA/hermes`）
- [ ] 处理文件不存在、JSON/YAML 解析失败等异常

**依赖**：T1.1
**复杂度**：中（2h）
**涉及文件**：`backend/app/services/hermes/hermes_config.py`（新增）
**验收标准**：
- Docker 环境下能读取 `/hermes-home/config.yaml`
- `read_auth_pool()` 正确解析 auth.json 中的多 Provider 凭证
- `mask_api_key("sk-abc12345xyz")` 返回 `"sk-...xyz"`

---

### T2.2 实现 HermesDiscoveryService
- [ ] 新增 `backend/app/services/hermes/hermes_discovery.py`，实现 `HermesDiscoveryService` 类：
  - `discover()` → 执行完整发现流程，返回 `DiscoveryResult`
  - `_resolve_hermes_home()` → 确定配置目录（环境变量 > Docker 挂载 > Windows 路径 > 默认）
  - `_check_api_server(api_config)` → 检测 API Server 可达性（候选配置 + 环境变量回退）
  - `_detect_runtime_type(hermes_home)` → 文件系统检测（源码目录 > CLI 命令 > 未发现）
  - `_determine_connection_mode(api_info)` → 确定连接方式（API Server > Socket.IO > CLI 回退）
- [ ] Docker 容器中 `localhost` 自动替换为 `host.docker.internal`
- [ ] 禁止任何 `subprocess.Popen`/`subprocess.run` 调用
- [ ] 每步记录 `DiagnosticStep`，支持 `/hermes/diagnose` 诊断接口
- [ ] httpx 请求超时 5 秒

**依赖**：T2.1
**复杂度**：高（3h）
**涉及文件**：`backend/app/services/hermes/hermes_discovery.py`（新增）
**验收标准**：
- Docker 环境下通过 `host.docker.internal:8642` 检测到 Hermes API Server
- API Server 不可达时正确回退，`connection_mode` 为 `cli_fallback`
- `diagnostic_steps` 包含完整的检测过程记录

---

### T2.3 实现 HermesModelDiscovery
- [ ] 新增 `backend/app/services/hermes/hermes_model_discovery.py`，实现 `HermesModelDiscovery` 类：
  - `discover_models()` → 4 级模型发现策略：
    1. Hermes API Server `/v1/models`（含 `hermes-agent` 模型）
    2. auth.json 凭证池 → 各 Provider `/v1/models`
    3. .env 环境变量中的模型
    4. 合并去重
  - `_fetch_provider_models(cred)` → 调用 Provider 的 `/v1/models`（超时 8s）
  - Provider 端点不可达时标记为"离线"
- [ ] 密钥仅脱敏显示，不暴露完整 key

**依赖**：T2.1, T3.1（HermesAPIClient）
**复杂度**：中（2h）
**涉及文件**：`backend/app/services/hermes/hermes_model_discovery.py`（新增）
**验收标准**：
- Hermes API Server 可用时返回含 `hermes-agent` 的模型列表
- Provider 不可达时返回标记 `is_available=False` 的条目
- 模型列表合并去重正确

---

## 3. 后端核心层：API 客户端与对话

### T3.1 实现 HermesAPIClient
- [ ] 新增 `backend/app/services/hermes/hermes_api_client.py`，实现 `HermesAPIClient` 类：
  - `__init__(base_url, api_key, timeout=360, max_connections=10)` → 初始化 httpx.AsyncClient 连接池
  - `chat_completions_stream(messages, model, ...)` → 流式对话，`stream=True`，yield `ChatChunk`
  - `chat_completions(messages, model, ...)` → 非流式对话，返回 `ChatCompletionResult`
  - `list_models(use_cache=True)` → 模型发现（8s 缓存）
  - `health_check()` → `GET /health`，5s 超时
  - `close()` → 关闭连接池
  - `_parse_chunk(chunk_json)` → 解析 OpenAI SSE chunk，分离 content/reasoning_content/tool_calls
- [ ] 默认 `model=hermes-agent` 走完整 agent runtime
- [ ] SSE 解析：跳过非 `data:` 行，处理 `[DONE]` 标记
- [ ] 错误时抛出 `HermesAPIError`（含 status_code 和 body）

**依赖**：T1.1
**复杂度**：高（3h）
**涉及文件**：`backend/app/services/hermes/hermes_api_client.py`（新增）
**验收标准**：
- 能向 `http://host.docker.internal:8642/v1/chat/completions` 发起流式请求
- 流式解析正确处理 content chunk、tool_calls、reasoning_content
- `health_check()` 在 API Server 可达时返回 True

---

### T3.2 实现 HermesSessionManager
- [ ] 新增 `backend/app/services/hermes/hermes_session.py`，实现 `HermesSessionManager` 类：
  - `create_session(user_id, profile_name, model_id)` → 创建新会话
  - `get_session(session_id)` → 获取会话
  - `list_sessions(user_id, limit=50)` → 列出用户会话（按 updated_at 降序）
  - `delete_session(session_id)` → 删除会话及所有消息
  - `rename_session(session_id, display_name)` → 重命名会话
  - `get_messages(session_id, limit=100, offset=0)` → 按时间分页加载消息
  - `add_message(session_id, role, content, ...)` → 追加消息并更新会话统计
  - `build_openai_messages(history, new_message)` → 构建 OpenAI messages 数组
  - `truncate_context_if_needed(messages, max_tokens=128000)` → 上下文截断（保留最近 10 轮）
- [ ] 所有数据库操作使用 SQLAlchemy async session

**依赖**：T1.3
**复杂度**：中（2h）
**涉及文件**：`backend/app/services/hermes/hermes_session.py`（新增）
**验收标准**：
- 会话 CRUD 操作正确，消息持久化成功
- `build_openai_messages()` 生成的 messages 数组格式符合 OpenAI API
- 上下文截断在超过 128K token 时自动触发

---

### T3.3 实现 ThinkingFilter
- [ ] 在 `backend/app/services/hermes/hermes_chat.py` 中实现 `ThinkingFilter` 类：
  - `filter_chunk(chunk)` → 状态机模式跨 chunk 处理 `<tool_call>...</think>` 标签
  - `flush()` → 流结束时刷新缓冲区
  - 识别 `<tool_call>` 开始标签和 `</think>` 结束标签
  - 分离 thinking_content 和 content

**依赖**：T1.1
**复杂度**：中（1.5h）
**涉及文件**：`backend/app/services/hermes/hermes_chat.py`（新增，部分实现）
**验收标准**：
- `hlelo world` → content 输出完整
- `hle思考内容

---

### T3.4 实现 HermesChatService
- [ ] 在 `backend/app/services/hermes/hermes_chat.py` 中实现 `HermesChatService` 类：
  - `stream_chat(session_id, message, model, profile_name)` → 流式对话主入口，yield `SSEEvent`
  - SSEEvent 类型：content / thinking / reasoning / tool_call / done / error
  - 并发限流：`asyncio.Semaphore(5)`
  - 读取会话历史 → 追加用户消息 → 构建 OpenAI messages → 上下文截断 → 调用 API 流式 → 分离思考/推理/工具 → 持久化 assistant 消息
  - 错误处理：`HermesAPIError` → 格式化用户可读提示（401/429/500/503）
  - 超时处理：保留已接收内容，标记 `is_interrupted=True`
  - 断连处理：`httpx.ConnectError` → 返回 DISCONNECTED 错误
  - 用户中断：`asyncio.CancelledError` → 保留已接收内容
- [ ] 实现 `_format_error()` 静态方法，映射常见 HTTP 错误码到中文提示

**依赖**：T3.1, T3.2, T3.3
**复杂度**：高（3h）
**涉及文件**：`backend/app/services/hermes/hermes_chat.py`（修改，完善）
**验收标准**：
- 流式对话通过 SSE 正确推送 content/thinking/tool_call 事件
- 并发超过 5 时请求被限流等待
- 401 错误返回"API 密钥无效"，429 返回"请求过于频繁"
- 中断时已接收内容被保留

---

### T3.5 实现 HermesHealthChecker
- [ ] 新增 `backend/app/services/hermes/hermes_health.py`，实现 `HermesHealthChecker` 类：
  - `start()` → 启动心跳循环（后台 asyncio.Task）
  - `stop()` → 停止心跳
  - `_health_loop()` → 定期检测（默认 30s）
  - `_check_health()` → 调用 `api_client.health_check()`
  - `_apply_debounced_status()` → 防抖：连续 3 次一致才更新
  - `_try_reconnect()` → 自动重连：每 10s 尝试，最多 12 次
  - `on_status_change(callback)` → 注册状态变更回调
  - `get_diagnostic_info()` → 诊断接口
  - `status` 属性 → 当前状态
- [ ] 状态值：online / offline / degraded / unknown

**依赖**：T3.1
**复杂度**：中（2h）
**涉及文件**：`backend/app/services/hermes/hermes_health.py`（新增）
**验收标准**：
- 心跳循环正常运行，Hermes 在线时 status 为 `online`
- Hermes 断连后，3 次检测结果一致才更新状态（防抖）
- 重连最多尝试 12 次（共 2 分钟）

---

## 4. 后端 API 层：路由与依赖注入

### T4.1 创建 Hermes API 路由
- [ ] 新增 `backend/app/api/hermes_router.py`，实现所有 API 端点：
  - `POST /hermes/chat/stream` → SSE 流式对话（`StreamingResponse` + `event_generator`）
  - `POST /hermes/chat/cancel` → 取消对话（取消 asyncio.Task）
  - `GET /hermes/sessions` → 列出会话
  - `POST /hermes/sessions` → 创建会话
  - `GET /hermes/sessions/{id}` → 获取会话
  - `DELETE /hermes/sessions/{id}` → 删除会话
  - `PATCH /hermes/sessions/{id}` → 重命名会话
  - `GET /hermes/sessions/{id}/messages` → 获取消息（分页）
  - `GET /hermes/models` → 模型发现
  - `GET /hermes/profiles` → Profile 列表
  - `GET /hermes/status` → 连接状态
  - `GET /hermes/diagnose` → 诊断信息
  - `GET /hermes/health` → 健康检查
- [ ] SSE 端点设置正确的 headers：`Cache-Control: no-cache`、`X-Accel-Buffering: no`
- [ ] 所有端点需要用户鉴权（`Depends(get_current_user)`）
- [ ] 请求/响应使用 Pydantic 模型

**依赖**：T3.2, T3.4, T3.5, T2.2, T2.3
**复杂度**：高（3h）
**涉及文件**：`backend/app/api/hermes_router.py`（新增）
**验收标准**：
- 所有端点可通过 Swagger UI 调用
- SSE 端点返回 `text/event-stream` 类型
- 未认证请求返回 401

---

### T4.2 创建 WebSocket 状态推送端点
- [ ] 在 `backend/app/api/hermes_router.py`（或 `ws.py`）中新增 WebSocket 端点 `WS /hermes/ws`
- [ ] 当 `HermesHealthChecker` 状态变更时，通过 WebSocket 推送 `hermes.status` 和 `hermes.health` 事件到所有连接的客户端
- [ ] 处理 WebSocket 连接/断连生命周期

**依赖**：T3.5, T4.1
**复杂度**：中（1.5h）
**涉及文件**：`backend/app/api/hermes_router.py`（修改）或 `backend/app/api/ws.py`（修改）
**验收标准**：
- 前端通过 WebSocket 能接收到 Hermes 状态变更事件
- 连接断开后不报错

---

### T4.3 注册路由与依赖注入
- [ ] 在 `backend/app/main.py`（或路由注册入口）中注册 `hermes_router`，前缀 `/hermes`
- [ ] 创建服务实例的依赖注入函数：
  - `get_hermes_config_reader()` → `HermesConfigReader`
  - `get_hermes_discovery_service()` → `HermesDiscoveryService`
  - `get_hermes_api_client()` → `HermesAPIClient`（单例，连接池复用）
  - `get_hermes_chat_service()` → `HermesChatService`
  - `get_hermes_session_manager()` → `HermesSessionManager`
  - `get_hermes_health_checker()` → `HermesHealthChecker`（单例，应用启动时 start）
- [ ] 应用启动事件中启动 `HermesHealthChecker`，关闭事件中关闭 `HermesAPIClient` 和 `HermesHealthChecker`

**依赖**：T4.1
**复杂度**：中（1.5h）
**涉及文件**：`backend/app/main.py`（修改），`backend/app/api/deps.py`（修改）
**验收标准**：
- `/hermes/*` 路由可访问
- `HermesAPIClient` 在应用生命周期内复用连接池
- 应用关闭时正确清理资源

---

## 5. 废弃旧模块

### T5.1 废弃后端旧模块
- [ ] 删除 `backend/app/services/gateway_client.py`（替代：`hermes_api_client.py`）
- [ ] 删除 `backend/app/services/gateway_health.py`（替代：`hermes_health.py`）
- [ ] 删除 `backend/app/services/hermes_acp_client.py`（ACP 协议在 Docker 中不可用）
- [ ] 删除 `backend/app/services/hermes_discovery.py`（替代：`hermes/hermes_discovery.py`）
- [ ] 删除 `backend/app/services/hermes_service.py`（替代：`hermes/hermes_chat.py`）
- [ ] 删除 `backend/app/services/llm_client.py`（替代：`hermes_api_client.py`）
- [ ] 删除 `backend/app/utils/hermes_fs.py`（替代：`hermes/hermes_config.py`）
- [ ] 删除 `backend/app/api/hermes.py`（替代：`hermes_router.py`）
- [ ] 删除 `backend/app/api/hermes_integration.py`（替代：`hermes_router.py`）
- [ ] 清理所有对上述模块的 import 引用（搜索并修复编译错误）

**依赖**：T4.3（新模块完全可用后）
**复杂度**：中（2h）
**涉及文件**：9 个废弃文件（删除），以及引用这些文件的所有其他文件（修改 import）
**验收标准**：
- 删除后无 import 错误，应用可正常启动
- `grep -r "gateway_client\|hermes_acp\|llm_client\|hermes_fs"` 无结果

---

## 6. 前端基础层：API 与 Composables

### T6.1 新增 Hermes API 模块
- [ ] 新增 `frontend/src/api/modules/hermes.ts`，封装所有 Hermes API 调用：
  - `chatStream(params)` → POST `/hermes/chat/stream`（返回 fetch Response 供 SSE 读取）
  - `cancelChat(sessionId)` → POST `/hermes/chat/cancel`
  - `listSessions()` → GET `/hermes/sessions`
  - `createSession(data)` → POST `/hermes/sessions`
  - `getSession(id)` → GET `/hermes/sessions/{id}`
  - `deleteSession(id)` → DELETE `/hermes/sessions/{id}`
  - `renameSession(id, name)` → PATCH `/hermes/sessions/{id}`
  - `getMessages(sessionId, params)` → GET `/hermes/sessions/{id}/messages`
  - `listModels()` → GET `/hermes/models`
  - `listProfiles()` → GET `/hermes/profiles`
  - `getStatus()` → GET `/hermes/status`
  - `diagnose()` → GET `/hermes/diagnose`
- [ ] 在 `frontend/src/api/index.ts` 中注册 hermes 模块

**依赖**：无
**复杂度**：中（1.5h）
**涉及文件**：`frontend/src/api/modules/hermes.ts`（新增），`frontend/src/api/index.ts`（修改），`frontend/src/api/client.ts`（修改，如需调整 baseURL）
**验收标准**：所有 API 函数类型正确，能发起 HTTP 请求

---

### T6.2 实现 useSSE Composable
- [ ] 新增 `frontend/src/composables/useSSE.ts`，实现 SSE 请求封装：
  - `postSSE(url, body, handlers, signal?)` → 使用 `fetch` + `ReadableStream` 读取 SSE 流
  - handlers 支持：`onContent` / `onThinking` / `onReasoning` / `onToolCall` / `onDone` / `onError`
  - 正确解析 `event:` 和 `data:` 行
  - 支持 `AbortSignal` 用于取消请求
  - 处理不完整行的 buffer 缓冲
- [ ] 处理网络错误和 SSE 解析异常

**依赖**：无
**复杂度**：中（2h）
**涉及文件**：`frontend/src/composables/useSSE.ts`（新增）
**验收标准**：
- 能正确解析 `event: content\ndata: 你好\n\n` 格式的 SSE
- 支持 AbortController 取消请求
- buffer 缓冲正确处理跨 chunk 的行分割

---

### T6.3 实现 useWebSocket Composable（状态监听）
- [ ] 新增或修改 `frontend/src/composables/useHermesWS.ts`，实现 Hermes 状态 WebSocket：
  - 连接 `ws://<host>/hermes/ws`
  - 监听 `hermes.status` 和 `hermes.health` 事件
  - 自动重连（断开后 5s 重试）
  - 提供响应式状态 `ref<string>` 供组件绑定

**依赖**：无
**复杂度**：中（1.5h）
**涉及文件**：`frontend/src/composables/useHermesWS.ts`（新增）
**验收标准**：WebSocket 断连后自动重连，状态变更时响应式变量更新

---

### T6.4 新增 TypeScript 类型定义
- [ ] 在 `frontend/src/types/` 中新增 Hermes 相关类型：
  - `HermesSession`、`HermesMessage`、`ToolCall`、`ModelInfo`、`ProfileInfo`、`DiscoveryResult`
  - SSE 事件类型：`SSEContentEvent`、`SSEThinkingEvent`、`SSEToolCallEvent`、`SSEDoneEvent`、`SSEErrorEvent`

**依赖**：无
**复杂度**：低（1h）
**涉及文件**：`frontend/src/types/index.ts`（修改）或 `frontend/src/types/hermes.ts`（新增）
**验收标准**：类型与后端 API 响应结构一致

---

## 7. 前端状态层：Pinia Store

### T7.1 实现 useHermesChatStore
- [ ] 新增 `frontend/src/stores/useHermesChatStore.ts`，实现对话状态管理：
  - 状态：`sessions`、`currentSessionId`、`messages`、`streamingMessage`、`thinkingBuffer`、`currentToolCalls`、`isStreaming`、`isLoading`、`error`
  - 动作：
    - `loadSessions()` → 加载会话列表
    - `createSession(profileName, modelId)` → 创建新会话
    - `switchSession(sessionId)` → 切换会话（加载消息）
    - `deleteSession(sessionId)` → 删除会话
    - `sendMessage(content, model)` → 发送消息（调用 `useSSE.postSSE`）
    - `cancelStream()` → 取消流式对话
  - SSE 事件处理：content → 追加到 streamingMessage，thinking → 追加到 thinkingBuffer，tool_call → 追加到 currentToolCalls，done → 持久化为 assistant 消息，error → 设置 error
  - 流式光标效果管理

**依赖**：T6.1, T6.2, T6.4
**复杂度**：高（3h）
**涉及文件**：`frontend/src/stores/useHermesChatStore.ts`（新增）
**验收标准**：
- 发送消息后 SSE 流正确追加到 streamingMessage
- done 事件后 streamingMessage 持久化为 messages 中的 assistant 消息
- 切换会话时加载正确的消息历史

---

### T7.2 实现 useHermesStatusStore
- [ ] 新增 `frontend/src/stores/useHermesStatusStore.ts`，实现连接状态管理：
  - 状态：`connectionStatus`（online/offline/degraded/unknown）、`connectionMode`、`discoveryResult`、`availableModels`、`profiles`
  - 动作：
    - `checkStatus()` → 调用 `/hermes/status`
    - `loadModels()` → 调用 `/hermes/models`
    - `loadProfiles()` → 调用 `/hermes/profiles`
    - `diagnose()` → 调用 `/hermes/diagnose`
  - WebSocket 状态监听：连接 `useHermesWS`，实时更新 `connectionStatus`

**依赖**：T6.1, T6.3, T6.4
**复杂度**：中（2h）
**涉及文件**：`frontend/src/stores/useHermesStatusStore.ts`（新增）
**验收标准**：
- WebSocket 推送状态变更时 store 自动更新
- 可用模型列表和 Profile 列表正确加载

---

## 8. 前端视图层：对话界面

### T8.1 实现 ChatBubble 组件
- [ ] 新增 `frontend/src/components/ChatBubble.vue`，实现消息气泡：
  - Markdown 渲染（使用 markdown-it 或类似库）
  - 流式打字效果（streaming 时显示光标 `▌`）
  - 思考过程折叠（`el-collapse`，可展开/收起）
  - 工具调用卡片（嵌套 `ToolCallCard`）
  - 中断标记（`el-tag type="warning"`）
  - 区分 user/assistant/system 角色样式
  - 代码块语法高亮

**依赖**：T6.4
**复杂度**：中（2h）
**涉及文件**：`frontend/src/components/ChatBubble.vue`（新增）
**验收标准**：
- Markdown 内容正确渲染（含代码块）
- 思考过程默认折叠，可展开
- 流式接收时显示打字光标

---

### T8.2 实现 ToolCallCard 组件
- [ ] 新增 `frontend/src/components/ToolCallCard.vue`，实现工具调用卡片：
  - 显示工具名称（如 `read_file`、`execute_command`）
  - 可折叠显示参数（JSON 格式化）
  - 显示执行结果
  - 状态图标：运行中 / 完成 / 失败

**依赖**：T6.4
**复杂度**：低（1h）
**涉及文件**：`frontend/src/components/ToolCallCard.vue`（新增）
**验收标准**：工具调用信息完整展示，参数 JSON 格式化可读

---

### T8.3 实现 ThinkingBlock 组件
- [ ] 新增 `frontend/src/components/ThinkingBlock.vue`，实现思考过程折叠块：
  - 默认折叠，标题显示"思考过程"
  - 展开后显示思考内容（Markdown 渲染）
  - 折叠/展开动画

**依赖**：T6.4
**复杂度**：低（0.5h）
**涉及文件**：`frontend/src/components/ThinkingBlock.vue`（新增）
**验收标准**：思考过程默认折叠，展开后内容正确渲染

---

### T8.4 重写 HermesChatView 对话界面
- [ ] 重写 `frontend/src/views/RequirementsView.vue`（或新增 `HermesChatView.vue`），实现完整对话界面：
  - **左侧栏**：会话列表（新建、切换、删除、重命名）
  - **主区域**：
    - 消息列表（滚动到底部、虚拟滚动支持）
    - 消息气泡（使用 `ChatBubble` 组件）
    - 流式消息渲染（streamingMessage 实时追加）
  - **底部**：输入框 + 发送按钮 + 停止生成按钮
  - **顶部**：模型选择器（下拉框）、Profile 选择器、Hermes 状态指示器
  - **空状态**：无会话时显示引导创建
- [ ] 修改路由配置，将新视图注册到路由

**依赖**：T7.1, T7.2, T8.1, T8.2, T8.3
**复杂度**：高（4h）
**涉及文件**：`frontend/src/views/RequirementsView.vue`（重写）或 `frontend/src/views/HermesChatView.vue`（新增），`frontend/src/router/index.ts`（修改）
**验收标准**：
- 能创建会话、发送消息、接收流式回复
- 停止生成按钮可中断对话
- 会话列表可切换、删除
- 模型选择器显示可用模型
- Hermes 离线时状态指示器正确显示

---

## 9. 前端旧代码清理

### T9.1 废弃前端旧模块
- [ ] 删除或标记废弃 `frontend/src/api/modules/chat.ts`（旧 chat API，替代：`hermes.ts`）
- [ ] 删除或标记废弃 `frontend/src/stores/chat.ts`（旧 chat store，替代：`useHermesChatStore.ts`）
- [ ] 删除或标记废弃 `frontend/src/stores/useChatStore.ts`（如有）
- [ ] 修改 `frontend/src/views/ChatView.vue`（如有引用旧 chat 模块，改为使用新 Hermes 模块）
- [ ] 清理所有对旧模块的 import 引用

**依赖**：T8.4（新视图可用后）
**复杂度**：中（1.5h）
**涉及文件**：`frontend/src/api/modules/chat.ts`（废弃），`frontend/src/stores/chat.ts`（废弃），以及引用文件
**验收标准**：删除后无编译错误，旧 ChatView 使用新模块

---

## 10. 部署配置

### T10.1 修改 Docker Compose 配置
- [ ] 修改 `docker-compose.yml`，为 backend 服务新增：
  - 环境变量：`HERMES_API_BASE`、`HERMES_API_KEY`、`HERMES_PROFILES_PATH`、`HERMES_MODEL`、`HERMES_BFF_URL`
  - volumes：`/c/Users/Lenovo/AppData/Local/hermes:/hermes-home:ro`（Hermes 配置只读挂载）
  - extra_hosts：`host.docker.internal:host-gateway`
- [ ] 确保容器间网络配置正确

**依赖**：T4.3
**复杂度**：低（1h）
**涉及文件**：`docker-compose.yml`（修改）
**验收标准**：
- Docker 容器启动后环境变量正确注入
- `/hermes-home/config.yaml` 可读
- `host.docker.internal` 可解析

---

### T10.2 修改生产环境配置
- [ ] 修改 `.env.production`，新增 Hermes 相关环境变量
- [ ] 更新 `.env.example`（如有），添加 Hermes 配置项说明
- [ ] 确认 Hermes Agent 的 `config.yaml` 中 `api_server.host` 为 `0.0.0.0`（不仅限 localhost）

**依赖**：T10.1
**复杂度**：低（0.5h）
**涉及文件**：`.env.production`（修改），`.env.example`（修改）
**验收标准**：生产环境配置完整，Docker 容器可连接宿主机 Hermes

---

## 11. 实操验证（前端交互可用性测试）

### T11.1 后端 API 实操验证
- [ ] 启动 Hermes Agent（`hermes --serve`），确认 API Server 在 `0.0.0.0:8642` 监听
- [ ] 启动 DevFlow 后端（Docker），验证：
  - `GET /hermes/health` 返回 `{healthy: true}`
  - `GET /hermes/status` 返回 `connection_mode: "api_server"`, `health_status: "online"`
  - `GET /hermes/models` 返回含 `hermes-agent` 的模型列表
  - `GET /hermes/diagnose` 返回完整诊断信息
  - `POST /hermes/sessions` 创建会话成功
  - `POST /hermes/chat/stream` 流式对话返回 SSE 事件

**依赖**：T4.3, T10.1
**复杂度**：中（2h）
**涉及文件**：无（验证步骤）
**验收标准**：所有 API 端点在 Docker + Hermes 环境下正常工作

---

### T11.2 前端对话交互实操验证
- [ ] 启动 DevFlow 前端，验证以下交互场景：
  - **正常对话**：发送消息 → 流式回复逐字显示 → 回复完成
  - **思考过程**：选择 DeepSeek 模型 → 发送消息 → 思考过程折叠显示 → 展开查看
  - **工具调用**：发送需要工具的消息 → 工具调用卡片显示 → 查看参数和结果
  - **停止生成**：发送消息 → 回复中点击"停止生成" → 内容保留并标记"已中断"
  - **会话管理**：创建新会话 → 切换会话 → 删除会话 → 重命名会话
  - **模型切换**：在模型下拉框切换模型 → 新消息使用新模型
  - **Hermes 离线**：停止 Hermes Agent → 前端显示"离线"状态 → 重启 Hermes → 状态恢复"在线"
  - **页面刷新**：刷新页面 → 会话和消息历史恢复

**依赖**：T8.4, T11.1
**复杂度**：高（3h）
**涉及文件**：无（验证步骤）
**验收标准**：所有交互场景正常工作，无 JS 报错，UI 显示正确

---

### T11.3 异常场景实操验证
- [ ] 验证以下异常场景：
  - **Hermes 未启动**：前端显示"Hermes Agent 未运行"，诊断信息完整
  - **网络中断**：对话中断 → 保留已接收内容 → 提供"重试"
  - **超长对话**：超过 128K token → 自动截断 → 提示"上下文已截断"
  - **并发限流**：同时发起 6 个对话 → 第 6 个被限流 → 提示"请等待"
  - **auth.json 缺失**：模型发现仍能返回 API Server 模型
  - **配置目录不可读**：回退到环境变量配置

**依赖**：T11.2
**复杂度**：中（2h）
**涉及文件**：无（验证步骤）
**验收标准**：所有异常场景有合理的用户提示，无崩溃

---

## 12. 文档与收尾

### T12.1 更新项目文档
- [ ] 更新 README（如有）中 Hermes 集成相关说明
- [ ] 更新 API 文档（Swagger/OpenAPI 注解完整）
- [ ] 确保 `.env.example` 包含所有新增环境变量及注释

**依赖**：T11.3
**复杂度**：低（1h）
**涉及文件**：`README.md`（修改），后端各路由文件的 docstring
**验收标准**：Swagger UI 文档完整，新环境变量有注释说明

---

## 任务依赖关系图

```
T1.1 ──→ T1.3 ──→ T1.4
  │        │
  │        └──→ T3.2 ──→ T3.4
  │                      ↑
  ├──→ T2.1 ──→ T2.2     │
  │        │              │
  │        └──→ T2.3 ←── T3.1 ──→ T3.3 ──→ T3.4
  │                       │              │
  │                       └──→ T3.5 ──→ T4.2
  │                                     │
  ├──→ T1.2                              │
  │                                      │
  T4.1 ←── T3.2, T3.4, T3.5, T2.2, T2.3
  │
  ├──→ T4.2
  │
  ├──→ T4.3 ──→ T5.1
  │      │
  │      └──→ T10.1 ──→ T10.2
  │
  T6.1, T6.2, T6.3, T6.4（独立，可并行）
  │
  ├──→ T7.1 ──→ T8.4
  ├──→ T7.2 ──→ T8.4
  │
  T8.1, T8.2, T8.3 ──→ T8.4 ──→ T9.1
  │
  T4.3, T10.1 ──→ T11.1 ──→ T11.2 ──→ T11.3 ──→ T12.1
```

## 统计摘要

| 类别 | 任务组数 | 任务数 | 预估总工时 |
|------|---------|--------|-----------|
| 后端基础层 | 4 | T1.1~T1.4 | 4.5h |
| 后端核心层 | 6 | T2.1~T3.5 | 15h |
| 后端 API 层 | 3 | T4.1~T4.3 | 6h |
| 废弃旧模块 | 1 | T5.1 | 2h |
| 前端基础层 | 4 | T6.1~T6.4 | 6h |
| 前端状态层 | 2 | T7.1~T7.2 | 5h |
| 前端视图层 | 4 | T8.1~T8.4 | 7.5h |
| 前端旧代码清理 | 1 | T9.1 | 1.5h |
| 部署配置 | 2 | T10.1~T10.2 | 1.5h |
| 实操验证 | 3 | T11.1~T11.3 | 7h |
| 文档收尾 | 1 | T12.1 | 1h |
| **合计** | **12 组** | **31 项** | **~57h** |

## 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新增 | `backend/app/services/hermes/__init__.py` | Hermes 服务包 |
| 新增 | `backend/app/services/hermes/types.py` | 数据类型定义 |
| 新增 | `backend/app/services/hermes/hermes_config.py` | 配置读取（替代 hermes_fs.py） |
| 新增 | `backend/app/services/hermes/hermes_discovery.py` | 运行时发现（替代旧 discovery） |
| 新增 | `backend/app/services/hermes/hermes_api_client.py` | OpenAI 兼容客户端（替代 gateway_client + llm_client） |
| 新增 | `backend/app/services/hermes/hermes_chat.py` | 流式对话（替代 hermes_service） |
| 新增 | `backend/app/services/hermes/hermes_session.py` | 会话管理 |
| 新增 | `backend/app/services/hermes/hermes_health.py` | 连接状态（替代 gateway_health） |
| 新增 | `backend/app/services/hermes/hermes_model_discovery.py` | 模型发现 |
| 新增 | `backend/app/api/hermes_router.py` | API 路由（替代 hermes.py + hermes_integration.py） |
| 新增 | `backend/app/models/hermes_session.py` | ORM 模型 |
| 新增 | `backend/app/models/hermes_message.py` | ORM 模型 |
| 新增 | `backend/alembic/versions/004_hermes_sessions_messages.py` | 数据库迁移 |
| 新增 | `frontend/src/api/modules/hermes.ts` | Hermes API 模块 |
| 新增 | `frontend/src/composables/useSSE.ts` | SSE 请求封装 |
| 新增 | `frontend/src/composables/useHermesWS.ts` | WebSocket 状态监听 |
| 新增 | `frontend/src/stores/useHermesChatStore.ts` | 对话状态管理 |
| 新增 | `frontend/src/stores/useHermesStatusStore.ts` | 连接状态管理 |
| 新增 | `frontend/src/components/ChatBubble.vue` | 消息气泡组件 |
| 新增 | `frontend/src/components/ToolCallCard.vue` | 工具调用卡片 |
| 新增 | `frontend/src/components/ThinkingBlock.vue` | 思考过程折叠 |
| 修改 | `backend/app/core/config.py` | 新增 Hermes 配置项 |
| 修改 | `backend/app/models/__init__.py` | 注册新模型 |
| 修改 | `backend/app/main.py` | 注册路由 + 生命周期 |
| 修改 | `backend/app/api/deps.py` | 依赖注入 |
| 修改 | `frontend/src/api/index.ts` | 注册 hermes 模块 |
| 修改 | `frontend/src/api/client.ts` | 调整 baseURL（如需） |
| 修改 | `frontend/src/router/index.ts` | 注册新视图路由 |
| 修改 | `docker-compose.yml` | Hermes 环境变量 + 挂载 |
| 修改 | `.env.production` | 新增 Hermes 配置 |
| 重写 | `frontend/src/views/RequirementsView.vue` | 对话界面重写 |
| 删除 | `backend/app/services/gateway_client.py` | 废弃 |
| 删除 | `backend/app/services/gateway_health.py` | 废弃 |
| 删除 | `backend/app/services/hermes_acp_client.py` | 废弃 |
| 删除 | `backend/app/services/hermes_discovery.py` | 废弃 |
| 删除 | `backend/app/services/hermes_service.py` | 废弃 |
| 删除 | `backend/app/services/llm_client.py` | 废弃 |
| 删除 | `backend/app/utils/hermes_fs.py` | 废弃 |
| 删除 | `backend/app/api/hermes.py` | 废弃 |
| 删除 | `backend/app/api/hermes_integration.py` | 废弃 |
| 废弃 | `frontend/src/api/modules/chat.ts` | 替代为 hermes.ts |
| 废弃 | `frontend/src/stores/chat.ts` | 替代为 useHermesChatStore |
