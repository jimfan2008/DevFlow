# Hermes Agent 部署与配置指南

## 概述

Hermes Agent 是 DevFlow 的协调者，负责：
- 需求评审会议主持
- 编程 Agent 的发现与对接
- 任务分配与调度
- 成果验收与通知
- 与编程 Agent 的所有通信（通过 Skill 层）

**重要约束**：DevFlow 不直接与编程 Agent 通信，所有交互必须通过 Hermes Agent 的 Skill 层进行。

## 安装

### 前置条件

- Python 3.12+
- Node.js 20+（如使用 npm 安装的 Hermes）
- WSL2（Windows 环境）

### 安装步骤

```bash
# 方式1：通过 npm 安装
npm install -g @anthropic/hermes

# 方式2：通过 pip 安装
pip install hermes-agent

# 方式3：从源码安装
git clone https://github.com/hermes-agent/hermes.git
cd hermes
pip install -e .
```

## Gateway 启动

Hermes Agent 通过本地 Gateway 提供 API 服务：

```bash
# 启动 Gateway（默认端口 8080）
hermes gateway start

# 指定端口
hermes gateway start --port 8081

# 指定配置文件
hermes gateway start --config ~/.hermes/gateway.yaml
```

验证 Gateway 是否运行：

```bash
curl http://localhost:8080/health
```

## Profile 配置

### 配置文件位置

```
~/.hermes/profiles/
├── default.yaml
├── devflow.yaml
└── production.yaml
```

### DevFlow Profile 示例

```yaml
# ~/.hermes/profiles/devflow.yaml
name: devflow
gateway:
  port: 8080
  api_key: ${HERMES_API_KEY}

model:
  name: claude-sonnet-4
  temperature: 0.7
  max_tokens: 4096

agents:
  coding:
    - name: OpenCode
      type: opencode
      capabilities: [coding, debugging]
      max_concurrent_tasks: 3
    - name: Cursor
      type: cursor
      capabilities: [coding, frontend]
      max_concurrent_tasks: 2
    - name: Claude-Code
      type: claude_code
      capabilities: [coding, testing, review]
      max_concurrent_tasks: 3

skills:
  discover_agent:
    enabled: true
    scan_interval: 60
  connect_agent:
    enabled: true
    max_reconnect_attempts: 3
    reconnect_delay: exponential
  assign_task:
    enabled: true
    load_balance: least-loaded
    max_load_threshold: 80
  receive_message:
    enabled: true
    message_types: [progress, deliver, fail]
```

### 在 DevFlow 中配置

```env
HERMES_API_BASE=http://localhost:8080
HERMES_API_KEY=<your-api-key>
HERMES_PROFILES_PATH=/home/user/.hermes/profiles
```

## Skill 层架构说明

### 四个核心 Skill

Hermes Agent 通过四个核心 Skill 与编程 Agent 交互：

```
┌─────────────────────────────────────────────────┐
│                  Hermes Agent                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────┐ │
│  │ Skill-发现│ │ Skill-对接│ │ Skill-分配│ │接收│ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─┬──┘ │
│       │            │            │          │    │
└───────┼────────────┼────────────┼──────────┼────┘
        │            │            │          │
        ▼            ▼            ▼          ▼
┌─────────────────────────────────────────────────┐
│              编程 Agent (OpenCode/Cursor/...)     │
└─────────────────────────────────────────────────┘
```

### Skill-发现 (discover_agent)

- **功能**：扫描并列出所有可用的编程 Agent
- **触发**：项目创建后、定期扫描、手动触发
- **实现**：通过 Gateway API 或数据库扫描
- **错误码**：SKILL_001（无可用 Agent）

### Skill-对接 (connect_agent)

- **功能**：建立与编程 Agent 的通信通道
- **特性**：支持断线重连（最多3次，指数退避）
- **连接状态**：connected / disconnected / reconnecting
- **错误码**：SKILL_002（连接失败）

### Skill-分配 (assign_task)

- **功能**：将任务分配给最佳匹配的编程 Agent
- **调度策略**：
  1. 按任务类型匹配 Agent 类型
  2. 负载均衡（最小负载优先）
  3. 避免重复分配同一 Agent
- **错误码**：SKILL_003（所有 Agent 过载）、SKILL_004（执行失败）

### Skill-接收 (receive_message)

- **功能**：接收编程 Agent 的进度/交付/失败消息
- **消息类型**：
  - `progress`：进度更新
  - `deliver`：成果交付
  - `fail`：任务失败
- **自动处理**：更新任务状态、释放 Agent 资源

### 通信约束验证

DevFlow 系统设计保证：
1. 没有直接调用编程 Agent API 的路由
2. 所有任务分配通过 `assign_task` Skill 进行
3. 所有消息接收通过 `receive_message` Skill 处理
4. Webhook 回调仅处理 Hermes 状态通知

## 负载均衡

Skill-分配 使用最小负载策略选择编程 Agent：

1. 过滤在线且有负载能力的 Agent
2. 按任务类型偏好匹配 Agent 类型
3. 计算每个 Agent 的当前负载
4. 选择负载最低的 Agent（阈值 80%）
5. 避免将连续任务分配给同一 Agent

## 故障处理

### Agent 离线

1. Skill-接收 检测到 Agent 离线
2. 标记任务为 `failed`
3. 通知相关人员
4. Skill-发现 重新扫描可用 Agent

### 连接断开

1. Skill-对接 自动重试（最多3次）
2. 指数退避：1s → 2s → 4s
3. 超过重试次数抛出 `SKILL_002` 错误
4. 管理员可手动触发重连

### 会议主持离线

1. 系统自动暂停会议
2. 群组内发送通知消息
3. 等待主持恢复或人工指定新主持
