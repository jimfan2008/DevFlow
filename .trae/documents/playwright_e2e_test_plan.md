# Playwright E2E 完整实操测试计划

## 1. 概述

### 1.1 测试目标
对 DevFlow 项目进行端到端（E2E）完整流程测试，验证从用户注册到项目交付的全链路功能是否正常工作。

### 1.2 测试环境
- **前端地址**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **Docker 服务**: PostgreSQL, Redis, Backend
- **测试框架**: Playwright 1.60.0

### 1.3 测试流程
```
注册 → 登录 → 创建项目 → Agent管理 → 扫描对接Hermes Agent 
→ 创建群聊 → 召开会议 → 确认需求说明书 → Hermes拆解任务 
→ 调度编程Agent开发 → 子任务验收 → 子任务交接 → 项目交付
```

---

## 2. 项目调研结论

### 2.1 现有测试文件
| 文件 | 路径 | 说明 |
|------|------|------|
| final-test.mjs | frontend/e2e/final-test.mjs | 注册+创建看板+添加任务测试 |
| register-debug.mjs | frontend/e2e/register-debug.mjs | 注册调试测试 |
| acceptance-test.mjs | frontend/e2e/acceptance-test.mjs | 验收测试 |
| board-test.mjs | frontend/e2e/board-test.mjs | 看板测试 |
| debug-test.mjs | frontend/e2e/debug-test.mjs | 调试测试 |
| network-test.mjs | frontend/e2e/network-test.mjs | 网络测试 |

### 2.2 关键页面组件

#### 认证相关
- [RegisterView.vue](file:///e:/code/DevFlow/frontend/src/views/RegisterView.vue) - 注册页面
- [LoginView.vue](file:///e:/code/DevFlow/frontend/src/views/LoginView.vue) - 登录页面

#### 项目管理
- [ProjectListView.vue](file:///e:/code/DevFlow/frontend/src/views/ProjectListView.vue) - 项目列表
- [ProjectDetailView.vue](file:///e:/code/DevFlow/frontend/src/views/ProjectDetailView.vue) - 项目详情

#### Agent管理
- [AgentListView.vue](file:///e:/code/DevFlow/frontend/src/views/AgentListView.vue) - Agent列表
- [AgentDetailView.vue](file:///e:/code/DevFlow/frontend/src/views/AgentDetailView.vue) - Agent详情

#### 群聊与会议
- [ChatView.vue](file:///e:/code/DevFlow/frontend/src/views/ChatView.vue) - 群聊与会议

#### 需求管理
- [RequirementsView.vue](file:///e:/code/DevFlow/frontend/src/views/RequirementsView.vue) - 需求管理

#### 看板与任务
- [BoardListView.vue](file:///e:/code/DevFlow/frontend/src/views/BoardListView.vue) - 看板列表
- [BoardView.vue](file:///e:/code/DevFlow/frontend/src/views/BoardView.vue) - 看板详情
- [TaskDetailView.vue](file:///e:/code/DevFlow/frontend/src/views/TaskDetailView.vue) - 任务详情

#### 验收与交付
- [AcceptanceView.vue](file:///e:/code/DevFlow/frontend/src/views/AcceptanceView.vue) - 验收报告
- [DeliveryView.vue](file:///e:/code/DevFlow/frontend/src/views/DeliveryView.vue) - 项目交付

### 2.3 路由配置
- [router/index.js](file:///e:/code/DevFlow/frontend/src/router/index.js)

### 2.4 API 模块
| 模块 | 文件 | 说明 |
|------|------|------|
| auth | api/modules/auth.ts | 认证 API |
| agent | api/modules/agent.ts | Agent API |
| chat | api/modules/chat.ts | 聊天 API |
| requirement | api/modules/requirement.ts | 需求 API |
| project | api/modules/project.ts | 项目 API |
| task | api/modules/task.ts | 任务 API |
| acceptance | api/modules/acceptance.ts | 验收 API |

---

## 3. 测试用例设计

### 3.1 测试模块划分

#### 模块一：用户认证
**编号**: TC-AUTH-001~002

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-AUTH-001 | 用户注册 | 未登录状态 | 1. 访问 /register<br>2. 填写用户名、邮箱、密码<br>3. 点击注册按钮 | 1. 注册成功<br>2. 自动跳转到 /boards<br>3. 页面显示应用头部和侧边栏 |
| TC-AUTH-002 | 用户登录 | 已注册账号 | 1. 访问 /login<br>2. 填写邮箱和密码<br>3. 点击登录按钮 | 1. 登录成功<br>2. 跳转到 /boards |

#### 模块二：项目管理
**编号**: TC-PROJECT-001~002

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-PROJECT-001 | 创建项目 | 已登录 | 1. 访问 /projects<br>2. 点击"创建项目"按钮<br>3. 填写项目名称和描述<br>4. 点击创建 | 1. 项目创建成功<br>2. 项目卡片显示在列表中<br>3. 显示成功提示 |
| TC-PROJECT-002 | 查看项目详情 | 已有项目 | 1. 点击项目卡片<br>2. 查看项目详情页面 | 1. 跳转到项目详情页<br>2. 显示项目基本信息 |

#### 模块三：Agent管理
**编号**: TC-AGENT-001~004

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-AGENT-001 | Agent列表页面 | 已登录 | 1. 访问 /agents<br>2. 等待页面加载 | 1. 显示 Agent 列表<br>2. 显示"Profile扫描"按钮<br>3. 显示类型筛选下拉框 |
| TC-AGENT-002 | Profile扫描 | 已登录 | 1. 点击"Profile扫描"按钮<br>2. 等待扫描完成 | 1. 显示加载状态<br>2. 扫描完成后刷新列表<br>3. 显示成功提示 |
| TC-AGENT-003 | 对接Hermes Agent | 扫描完成 | 1. 筛选 Hermes 类型<br>2. 查看 Agent 卡片<br>3. 点击"Skill发现"按钮 | 1. 显示 Hermes Agent 卡片<br>2. 状态显示在线/离线<br>3. 技能发现完成提示 |
| TC-AGENT-004 | 查看Agent详情 | 已有Agent | 1. 点击 Agent 卡片<br>2. 查看详情页面 | 1. 跳转到 Agent 详情页<br>2. 显示 Agent 详细信息 |

#### 模块四：群聊与会议
**编号**: TC-CHAT-001~004

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-CHAT-001 | 创建群聊 | 已登录 | 1. 访问 /chat<br>2. 点击"新建"按钮<br>3. 填写群组名称<br>4. 选择模式<br>5. 点击创建 | 1. 群组创建成功<br>2. 群组显示在侧边栏列表中 |
| TC-CHAT-002 | 选择群聊 | 已有群组 | 1. 点击侧边栏中的群组<br>2. 查看聊天界面 | 1. 右侧显示聊天界面<br>2. 显示群组名称和模式 |
| TC-CHAT-003 | 发送消息 | 已选择群组 | 1. 输入消息内容<br>2. 点击发送按钮 | 1. 消息发送成功<br>2. 消息显示在聊天区域 |
| TC-CHAT-004 | 召开会议 | 讨论模式群组 | 1. 点击"启动会议"按钮<br>2. 等待会议开始<br>3. 发送会议消息<br>4. 结束会议 | 1. 会议启动成功<br>2. 显示会议议程<br>3. 结束后生成会议纪要 |

#### 模块五：需求管理
**编号**: TC-REQ-001~005

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-REQ-001 | 进入需求管理 | 已有项目 | 1. 访问 /requirements<br>2. 选择项目 | 1. 显示需求管理界面<br>2. 左侧显示 Hermes 聊天<br>3. 右侧显示需求文档 |
| TC-REQ-002 | Hermes需求讨论 | 已选择项目 | 1. 点击引导按钮或输入需求描述<br>2. 与 Hermes 多轮对话<br>3. 完善需求细节 | 1. Hermes 响应消息<br>2. 显示问题引导标签<br>3. 聊天区域显示对话历史 |
| TC-REQ-003 | 生成需求文档 | 需求讨论完成 | 1. 等待需求分析完成<br>2. 检查右侧文档内容<br>3. 编辑完善文档 | 1. 需求文档自动生成<br>2. 可手动编辑补充<br>3. 显示文档版本和状态 |
| TC-REQ-004 | 确认需求说明书 | 文档已提交 | 1. 点击"确认锁定"按钮<br>2. 确认对话框<br>3. 等待锁定完成 | 1. 需求状态变为"已确认"<br>2. 文档不可编辑<br>3. 显示已确认标签 |
| TC-REQ-005 | 任务拆解 | 需求已确认 | 1. 点击"拆解任务"按钮<br>2. 等待拆解完成 | 1. Hermes 自动拆解需求<br>2. 生成多个子任务<br>3. 跳转到看板查看任务 |

#### 模块六：看板与任务
**编号**: TC-TASK-001~003

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-TASK-001 | 查看任务看板 | 已拆解任务 | 1. 访问 /boards<br>2. 进入看板详情<br>3. 查看任务卡片 | 1. 显示看板列（待办、进行中、已完成等）<br>2. 任务卡片显示在对应列<br>3. 显示任务标题和状态 |
| TC-TASK-002 | 任务详情 | 已有任务 | 1. 点击任务卡片<br>2. 查看任务详情 | 1. 显示任务标题、描述<br>2. 显示负责人、截止日期<br>3. 右侧显示验收标准、Agent信息 |
| TC-TASK-003 | Agent分配任务 | 任务未分配 | 1. 点击"Agent分配"按钮<br>2. 等待分配完成 | 1. 任务分配给合适的 Agent<br>2. 显示分配成功提示<br>3. 任务状态更新 |

#### 模块七：子任务验收
**编号**: TC-ACCEPT-001~003

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-ACCEPT-001 | 查看验收报告 | 已有验收报告 | 1. 访问 /acceptance<br>2. 查看验收报告列表 | 1. 显示验收报告表格<br>2. 显示任务ID、状态、审核人 |
| TC-ACCEPT-002 | 通过验收 | 待审核报告 | 1. 点击"详情"查看报告<br>2. 点击"通过"按钮 | 1. 状态变为"已通过"<br>2. 显示成功提示 |
| TC-ACCEPT-003 | 驳回验收 | 待审核报告 | 1. 点击"驳回"按钮<br>2. 填写问题明细<br>3. 确认驳回 | 1. 状态变为"已驳回"<br>2. 问题明细已记录 |

#### 模块八：项目交付
**编号**: TC-DELIVER-001

| 用例 | 名称 | 前置条件 | 操作步骤 | 预期结果 |
|------|------|----------|----------|----------|
| TC-DELIVER-001 | 项目交付 | 所有验收通过 | 1. 访问 /delivery<br>2. 选择项目<br>3. 点击"确认交付"<br>4. 确认对话框 | 1. 项目状态变为"已完成"<br>2. 显示交付成功结果<br>3. 显示交付摘要 |

---

## 4. 测试脚本设计

### 4.1 目录结构
```
frontend/e2e/
├── full-flow-test.mjs       # 完整流程测试（主脚本）
├── helpers/
│   ├── auth-helper.mjs      # 认证辅助函数
│   ├── project-helper.mjs   # 项目辅助函数
│   ├── agent-helper.mjs     # Agent辅助函数
│   ├── chat-helper.mjs      # 聊天辅助函数
│   └── requirement-helper.mjs # 需求辅助函数
└── config.mjs               # 测试配置
```

### 4.2 测试配置 (config.mjs)
```javascript
export const BASE_URL = 'http://localhost:5173';
export const API_URL = 'http://localhost:8000';
export const TIMEOUT = 30000;
export const SLOW_MO = 100;
```

### 4.3 测试数据管理
- 测试数据将从独立的数据文件加载，而非硬编码
- 每次测试使用唯一的用户名/邮箱，避免冲突
- 测试完成后清理测试数据（可选）

---

## 5. 潜在风险与考虑

### 5.1 风险点
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Hermes Agent 未启动 | Agent相关测试失败 | 检查后端状态，提供降级方案 |
| API 响应超时 | 测试中断 | 增加超时时间，添加重试机制 |
| 页面元素定位不稳定 | 测试误报 | 使用多种定位策略，等待元素稳定 |
| 测试数据冲突 | 测试结果不一致 | 使用唯一标识符，测试前后清理 |
| 异步操作未完成 | 断言过早 | 使用显式等待，监听网络请求 |

### 5.2 注意事项
1. **元素定位优先级**: data-testid > role > text > CSS selector
2. **等待策略**: 优先使用 `waitForSelector` 和 `waitForResponse`
3. **错误处理**: 每个步骤添加错误捕获和截图
4. **日志记录**: 关键步骤记录日志，便于调试
5. **截图**: 失败时自动截图保存

---

## 6. 测试执行流程

### 6.1 执行顺序
1. 环境检查（Docker 服务状态）
2. 测试数据准备
3. 模块一：用户认证
4. 模块二：项目管理
5. 模块三：Agent管理
6. 模块四：群聊与会议
7. 模块五：需求管理
8. 模块六：看板与任务
9. 模块七：子任务验收
10. 模块八：项目交付
11. 测试结果汇总

### 6.2 执行命令
```bash
# 进入前端目录
cd frontend

# 运行完整流程测试
node e2e/full-flow-test.mjs

# 或使用 playwright 浏览器（如已安装）
# npx playwright test e2e/full-flow-test.mjs --headed
```

---

## 7. 验证标准

### 7.1 通过标准
- 所有 13 个测试用例全部通过
- 无意外的控制台错误
- 页面交互流畅，无明显卡顿
- 数据库状态与前端显示一致

### 7.2 输出产物
- 测试执行日志
- 关键步骤截图
- 失败时的错误堆栈
- 测试结果汇总报告

---

## 8. 测试脚本文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 测试数据 | frontend/e2e/test-data.json | 测试用模拟数据 |
| 配置文件 | frontend/e2e/test-config.mjs | 测试配置 |
| 工具函数 | frontend/e2e/utils/helpers.mjs | 通用辅助函数 |
| 完整流程测试 | frontend/e2e/full-flow-test.mjs | 完整 E2E 测试脚本 |
