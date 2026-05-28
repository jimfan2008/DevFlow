# Playwright CLI 完整实操检验计划

## 1. 概述

### 1.1 测试目标
使用 **Playwright CLI** 对 DevFlow 项目进行**完整实操检验**，验证从项目创建到项目交付的全链路功能是否真正可用。

### 1.2 测试范围（用户指定流程）
```
创建项目 
→ Agent管理 
→ 扫描并对接hermes agent 
→ hermes创建群聊 
→ 召开会议 
→ 确认需求说明书 
→ hermes拆解任务 
→ 调度编程agent进行开发 
→ 子任务验收 
→ 子任务交接 
→ 项目交付
```

### 1.3 测试环境
- **前端地址**: http://localhost:3001 (vite dev server)
- **后端 API**: http://localhost:8000
- **Docker 服务**: PostgreSQL, Redis, Backend, Gitea, Nginx
- **测试框架**: Playwright 1.60.0 (CLI 模式)
- **执行方式**: `npx playwright test` 或 `node e2e/*.mjs`

### 1.4 关键差异（与之前测试的区别）
| 特性 | 之前的自动化测试 | 本次 Playwright CLI 实操检验 |
|------|-----------------|---------------------------|
| 执行方式 | 直接调用 `node` | 使用 `npx playwright test` CLI |
| 测试目标 | 页面加载和元素存在 | **实际功能可用，端到端验证** |
| 数据验证 | 仅验证界面显示 | **验证 API 返回 + 数据库状态** |
| 时间等待 | 固定 `waitForTimeout` | **监听网络请求，等待实际完成** |
| 断言方式 | `isVisible()` 可见性检查 | **API 响应验证 + 数据库查询** |

---

## 2. 项目调研结论

### 2.1 现有测试文件

| 文件 | 路径 | 说明 | 状态 |
|------|------|------|------|
| full-flow-test.mjs | frontend/e2e/full-flow-test.mjs | 完整流程测试脚本 | ✅ 可用，需增强 |
| final-test.mjs | frontend/e2e/final-test.mjs | 注册+看板+任务测试 | ✅ 可用 |
| test-config.mjs | frontend/e2e/test-config.mjs | 测试配置 | ✅ 可用 |
| test-data.json | frontend/e2e/test-data.json | 测试数据 | ✅ 可用 |
| helpers.mjs | frontend/e2e/utils/helpers.mjs | 工具函数 | ✅ 可用 |

### 2.2 关键 API 端点（需要验证）

| 功能模块 | API 端点 | 方法 | 验证点 |
|---------|----------|------|--------|
| 项目管理 | `/api/projects` | POST | 返回 `200` + project_id |
| Agent管理 | `/api/agents/scan-profile` | POST | 返回 `200` + agent 列表 |
| 群组管理 | `/api/chat/groups` | POST | 返回 `200` + group_id |
| 会议功能 | `/api/meetings` | POST | 返回 `200` + meeting_id |
| 需求管理 | `/api/requirements` | POST | 返回 `200` + requirement_id |
| 需求锁定 | `/api/requirements/{id}/lock` | POST | 返回 `200` + locked=true |
| 任务拆解 | `/api/requirements/{id}/decompose` | POST | 返回 `200` + tasks[] |
| Agent分配 | `/api/agents/auto-assign/{taskId}` | POST | 返回 `200` + execution_id |
| 任务执行 | `/api/tasks/{id}/execute` | POST | 返回 `200` + result |
| 验收功能 | `/api/acceptance` | POST | 返回 `200` + status |
| 项目交付 | `/api/projects/{id}/deliver` | POST | 返回 `200` + delivered=true |

### 2.3 关键页面组件

| 页面 | 文件 | 关键交互元素 |
|------|------|-------------|
| 项目列表 | [ProjectListView.vue](file:///e:/code/DevFlow/frontend/src/views/ProjectListView.vue) | 创建项目按钮、项目卡片、项目选择器 |
| Agent列表 | [AgentListView.vue](file:///e:/code/DevFlow/frontend/src/views/AgentListView.vue) | Profile扫描按钮、Agent卡片、技能发现 |
| 群聊会议 | [ChatView.vue](file:///e:/code/DevFlow/frontend/src/views/ChatView.vue) | 新建群组、启动会议、发送消息 |
| 需求管理 | [RequirementsView.vue](file:///e:/code/DevFlow/frontend/src/views/RequirementsView.vue) | Hermes聊天、需求编辑器、提交/锁定/拆解 |
| 任务看板 | [BoardView.vue](file:///e:/code/DevFlow/frontend/src/views/BoardView.vue) | 看板列、任务卡片、拖拽操作 |
| 任务详情 | [TaskDetailView.vue](file:///e:/code/DevFlow/frontend/src/views/TaskDetailView.vue) | Agent分配、执行、验收 |
| 验收报告 | [AcceptanceView.vue](file:///e:/code/DevFlow/frontend/src/views/AcceptanceView.vue) | 通过/驳回按钮、验收详情 |
| 项目交付 | [DeliveryView.vue](file:///e:/code/DevFlow/frontend/src/views/DeliveryView.vue) | 项目选择、确认交付 |

### 2.4 后端测试场景参考

项目已有完整的后端测试场景：
- [project_flow.json](file:///e:/code/DevFlow/backend/tests/data/scenarios/project_flow.json) - 完整项目生命周期场景

---

## 3. 测试用例设计

### 3.1 测试模块划分

#### 模块一：项目创建
**编号**: TC-PROJECT-001

| 项目 | 内容 |
|------|------|
| 用例名称 | 项目创建实操检验 |
| 前置条件 | 用户已登录 |
| 操作步骤 | 1. 访问 `/projects` 页面<br>2. 点击"创建项目"按钮<br>3. 填写项目名称和描述<br>4. 点击"创建"按钮<br>5. **验证 API 响应和数据库状态** |
| 验证点 | 1. 按钮点击后显示加载状态<br>2. API 调用返回 `200` OK<br>3. 项目卡片出现在列表中<br>4. 数据库查询确认项目存在<br>5. 显示"项目创建成功"消息 |
| 关键断言 | - API response.status === 200<br>- project.id 非空<br>- 列表中存在项目卡片 |

#### 模块二：Agent管理与对接
**编号**: TC-AGENT-001~002

| 用例 | 名称 | 前置条件 | 操作步骤 | 验证点 |
|------|------|----------|----------|--------|
| TC-AGENT-001 | Profile扫描 | 已登录 | 1. 访问 `/agents`<br>2. 点击"Profile扫描"按钮<br>3. 等待扫描完成<br>4. **验证扫描结果** | 1. 显示加载动画<br>2. API 返回 `200`<br>3. Agent 列表非空<br>4. 显示 Hermes 类型 Agent |
| TC-AGENT-002 | Hermes对接 | 扫描完成 | 1. 筛选 Hermes 类型<br>2. 点击 Agent 卡片<br>3. 点击"Skill发现"按钮<br>4. **验证技能发现** | 1. Hermes Agent 显示在线状态<br>2. 技能发现 API 成功<br>3. Agent 详情页面显示技能列表 |

#### 模块三：Hermes群聊创建
**编号**: TC-GROUP-001

| 项目 | 内容 |
|------|------|
| 用例名称 | Hermes群聊创建实操检验 |
| 前置条件 | Hermes Agent 已对接 |
| 操作步骤 | 1. 访问 `/chat`<br>2. 点击"新建"按钮<br>3. 填写群组名称，选择讨论模式<br>4. 添加 Hermes Agent 到群组<br>5. 点击"创建"<br>6. **验证群组创建** |
| 验证点 | 1. 对话框正确显示<br>2. 可选择 Hermes Agent 作为成员<br>3. API 调用成功<br>4. 群组出现在侧边栏<br>5. 聊天界面加载完成 |

#### 模块四：召开会议
**编号**: TC-MEETING-001

| 项目 | 内容 |
|------|------|
| 用例名称 | 召开会议实操检验 |
| 前置条件 | 已创建包含 Hermes 的群组 |
| 操作步骤 | 1. 选择群组<br>2. 点击"启动会议"按钮<br>3. 填写会议议程<br>4. **发送会议消息（模拟）**<br>5. 等待会议响应<br>6. 结束会议 |
| 验证点 | 1. 会议模式切换成功<br>2. 显示会议议程区域<br>3. 消息发送 API 成功<br>4. 会议结束后生成纪要<br>5. 会议状态正确更新 |

#### 模块五：需求说明书确认
**编号**: TC-REQ-001~003

| 用例 | 名称 | 操作步骤 | 验证点 |
|------|------|----------|--------|
| TC-REQ-001 | 需求讨论 | 1. 访问 `/requirements`<br>2. 选择项目<br>3. 与 Hermes 多轮对话<br>4. **验证对话历史** | 1. 项目选择成功<br>2. 消息发送 API 成功<br>3. Hermes 响应消息<br>4. 聊天区域显示完整历史 |
| TC-REQ-002 | 生成需求文档 | 1. 输入需求描述<br>2. **等待需求分析完成**<br>3. 编辑完善文档<br>4. 点击"提交需求文档" | 1. 需求文档自动生成<br>2. 提交 API 成功<br>3. 显示提交成功提示 |
| TC-REQ-003 | 确认锁定 | 1. 点击"确认锁定"按钮<br>2. 确认对话框<br>3. **验证锁定状态** | 1. 锁定 API 成功<br>2. 文档变为只读<br>3. 显示"已确认"标签<br>4. 状态变为 locked |

#### 模块六：Hermes任务拆解
**编号**: TC-DECOMPOSE-001

| 项目 | 内容 |
|------|------|
| 用例名称 | Hermes任务拆解实操检验 |
| 前置条件 | 需求已确认锁定 |
| 操作步骤 | 1. 点击"拆解任务"按钮<br>2. **等待拆解完成（可能需要较长时间）**<br>3. **验证生成的任务数量和质量**<br>4. 检查任务依赖关系<br>5. **验证看板显示** |
| 验证点 | 1. 拆解 API 返回 200<br>2. 生成 3+ 个子任务<br>3. 任务有明确依赖关系<br>4. 跳转到看板页面<br>5. 看板列显示任务卡片<br>6. 任务状态为"待办" |
| 数据库验证 | - 查询 tasks 表<br>- 验证 task_count > 0<br>- 验证 requirement_id 关联正确 |

#### 模块七：调度编程Agent开发
**编号**: TC-ASSIGN-001~002

| 用例 | 名称 | 操作步骤 | 验证点 |
|------|------|----------|--------|
| TC-ASSIGN-001 | Agent自动分配 | 1. 进入任务详情<br>2. 点击"Agent分配"按钮<br>3. **等待分配完成**<br>4. 验证分配结果 | 1. 分配 API 成功<br>2. 显示分配的 Agent 名称<br>3. 任务状态变为"已分配"<br>4. 显示执行 ID |
| TC-ASSIGN-002 | 任务执行（模拟） | 1. 触发任务执行<br>2. **等待执行完成**<br>3. 检查执行日志<br>4. 验证执行结果 | 1. 执行 API 成功<br>2. 执行日志正常<br>3. 结果字段非空<br>4. 任务状态变为"已交付" |

#### 模块八：子任务验收
**编号**: TC-ACCEPT-001

| 项目 | 内容 |
|------|------|
| 用例名称 | 子任务验收实操检验 |
| 前置条件 | 任务已交付 |
| 操作步骤 | 1. 访问 `/acceptance`<br>2. 查看验收报告<br>3. 点击"详情"<br>4. 检查验收标准<br>5. **点击"通过"按钮**<br>6. **验证验收结果** |
| 验证点 | 1. 验收报告列表显示<br>2. 详情对话框打开<br>3. 通过 API 成功<br>4. 状态变为"已通过"<br>5. 显示成功消息 |

#### 模块九：子任务交接
**编号**: TC-HANDOVER-001

| 项目 | 内容 |
|------|------|
| 用例名称 | 子任务交接实操检验 |
| 前置条件 | 前序任务验收通过 |
| 操作步骤 | 1. **检查下游任务状态**<br>2. 验证任务依赖解锁<br>3. 进入下游任务详情<br>4. 分配给下一个 Agent<br>5. 执行任务 |
| 验证点 | 1. 下游任务状态从"阻塞"变为"待办"<br>2. 依赖图显示已解锁<br>3. 可分配给新 Agent<br>4. 执行 API 成功 |

#### 模块十：项目交付
**编号**: TC-DELIVER-001

| 项目 | 内容 |
|------|------|
| 用例名称 | 项目交付实操检验 |
| 前置条件 | 所有子任务验收通过 |
| 操作步骤 | 1. 访问 `/delivery`<br>2. 选择项目<br>3. **检查交付摘要**<br>4. 点击"确认交付"<br>5. 确认对话框<br>6. **验证交付结果** |
| 验证点 | 1. 项目列表显示可交付项目<br>2. 交付摘要显示统计数据<br>3. 交付 API 成功<br>4. 项目状态变为"已完成"<br>5. 显示交付成功结果 |

---

## 4. Playwright CLI 测试脚本设计

### 4.1 目录结构
```
frontend/e2e/
├── cli/
│   ├── playwright.config.mjs      # Playwright CLI 配置
│   └── specs/
│       ├── 01_project.spec.mjs    # 项目创建测试
│       ├── 02_agent.spec.mjs      # Agent管理测试
│       ├── 03_group.spec.mjs      # 群聊创建测试
│       ├── 04_meeting.spec.mjs    # 会议功能测试
│       ├── 05_requirement.spec.mjs # 需求管理测试
│       ├── 06_decompose.spec.mjs  # 任务拆解测试
│       ├── 07_assign.spec.mjs     # Agent分配测试
│       ├── 08_acceptance.spec.mjs # 验收测试
│       ├── 09_handover.spec.mjs   # 任务交接测试
│       └── 10_delivery.spec.mjs   # 项目交付测试
├── fixtures/
│   └── test-data.json             # 测试数据（独立文件）
├── utils/
│   ├── api-helpers.mjs            # API 验证辅助函数
│   ├── db-helpers.mjs             # 数据库验证辅助函数
│   └── page-helpers.mjs           # 页面操作辅助函数
└── setup.mjs                      # 测试环境初始化
```

### 4.2 Playwright CLI 配置 (playwright.config.mjs)
```javascript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './cli/specs',
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ['list'],
    ['json', { outputFile: './e2e/results/cli-report.json' }],
    ['html', { outputFolder: './e2e/results/html-report', open: 'never' }],
  ],
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'retain-on-failure',
    screenshot: 'on',
    video: 'retain-on-failure',
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
```

### 4.3 测试数据文件 (fixtures/test-data.json)
```json
{
  "project": {
    "name": "CLI测试项目 {timestamp}",
    "description": "Playwright CLI 完整流程测试项目，用于验证端到端功能",
    "requirements": {
      "content": "# 需求文档\n\n## 1. 功能需求\n- 用户注册登录\n- 商品展示\n- 购物车管理\n- 订单处理\n\n## 2. 技术要求\n- 响应式设计\n- 安全性保障"
    }
  },
  "group": {
    "name": "CLI测试讨论组 {timestamp}",
    "mode": "discussion",
    "messages": [
      "让我们开始讨论项目需求",
      "首先确认功能范围",
      "然后拆解开发任务"
    ]
  },
  "verification": {
    "apiTimeout": 30000,
    "dbTimeout": 5000,
    "retryCount": 2
  }
}
```

### 4.4 关键辅助函数

#### API 验证辅助 (api-helpers.mjs)
```javascript
export async function verifyApiResponse(response, expectedStatus = 200) {
  expect(response.status()).toBe(expectedStatus);
  const data = await response.json();
  expect(data).toBeDefined();
  return data;
}

export async function waitForApiCompletion(page, urlPattern, timeout = 30000) {
  const response = await page.waitForResponse(
    resp => resp.url().includes(urlPattern) && resp.request().method() !== 'OPTIONS',
    { timeout }
  );
  return verifyApiResponse(response);
}
```

#### 数据库验证辅助 (db-helpers.mjs)
```javascript
export async function queryDatabase(query, params = []) {
  const response = await fetch('http://localhost:8000/api/test/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, params }),
  });
  return response.json();
}

export async function verifyProjectExists(projectId) {
  const result = await queryDatabase(
    'SELECT * FROM projects WHERE id = $1',
    [projectId]
  );
  return result.rows.length > 0;
}
```

---

## 5. 执行策略与风险处理

### 5.1 执行策略

#### 策略一：串行执行（推荐）
```
原因：测试流程有严格依赖关系
- 项目创建 → Agent管理 → 群聊创建 → 会议 → 需求确认 → 任务拆解
  → Agent分配 → 验收 → 交接 → 交付
```

#### 策略二：状态共享
```
使用 Playwright 的 storageState 共享登录状态
- 第一个测试完成登录
- 后续测试复用登录状态
- 共享测试数据（项目ID、群组ID等）
```

### 5.2 风险分析与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| Hermes Agent 未启动 | 高 | 阻塞流程 | 1. 检查 Agent 状态<br>2. 如果离线，跳过依赖 Agent 的步骤<br>3. 记录警告信息 |
| API 响应超时 | 中 | 测试中断 | 1. 增加超时时间<br>2. 重试机制（最多3次）<br>3. 异步操作使用 `waitForResponse` |
| 页面元素定位失败 | 中 | 测试误报 | 1. 使用多种定位策略<br>2. 添加 `data-testid` 属性<br>3. 等待元素稳定后再操作 |
| 测试数据冲突 | 低 | 结果不一致 | 1. 使用时间戳唯一标识<br>2. 测试前清理旧数据<br>3. 隔离测试环境 |
| 异步操作未完成 | 高 | 断言过早 | 1. 监听网络请求<br>2. 使用 `waitForResponse`<br>3. 验证 API 响应而非仅界面 |

### 5.3 降级方案

**当 Hermes Agent 不可用时：**

1. **跳过需要 Hermes 的步骤**：任务拆解、会议、需求分析
2. **执行其他可独立验证的功能**：项目创建、Agent页面、需求页面、验收页面
3. **使用模拟数据创建测试任务**：直接调用 API 创建任务进行验收测试
4. **记录警告信息**：明确哪些功能依赖外部 Agent

---

## 6. 执行步骤

### 6.1 环境准备

```bash
# 1. 检查 Docker 服务
docker ps

# 2. 检查后端健康
curl http://localhost:8000/health

# 3. 启动前端
cd frontend && npm run dev

# 4. 检查前端可用
curl http://localhost:3001/
```

### 6.2 测试执行

```bash
# 方式一：使用 Playwright CLI（推荐）
cd frontend
npx playwright test --config=./e2e/cli/playwright.config.mjs

# 方式二：运行单个测试文件
npx playwright test ./e2e/cli/specs/01_project.spec.mjs --headed

# 方式三：生成 HTML 报告并查看
npx playwright test --reporter=html
npx playwright show-report ./e2e/results/html-report
```

### 6.3 测试输出

| 输出类型 | 路径 | 说明 |
|---------|------|------|
| 测试截图 | `frontend/e2e/screenshots/` | 每个测试步骤的截图 |
| JSON 报告 | `frontend/e2e/results/cli-report.json` | 机器可读的测试结果 |
| HTML 报告 | `frontend/e2e/results/html-report/` | 可视化测试报告 |
| 追踪信息 | `frontend/e2e/results/traces/` | 失败测试的 Playwright Trace |

---

## 7. 验收标准

### 7.1 通过标准

1. **所有测试用例通过**：10 个模块全部通过
2. **无错误**：无未处理的控制台错误、无页面崩溃
3. **API 验证**：所有关键 API 调用返回 200 OK
4. **数据一致性**：数据库状态与前端显示一致
5. **流程完整性**：从项目创建到项目交付的完整链路

### 7.2 部分通过标准

如果 Hermes Agent 不可用：

1. **独立功能**：项目创建、Agent页面、需求页面、验收页面等独立功能正常
2. **模拟测试**：能够使用模拟数据完成其他验证
3. **降级运行**：系统在缺少外部依赖时仍能正常工作

---

## 8. 测试脚本清单

| 文件 | 路径 | 说明 |
|------|------|------|
| CLI 配置 | frontend/e2e/cli/playwright.config.mjs | Playwright 测试配置 |
| 测试数据 | frontend/e2e/fixtures/test-data.json | 测试用模拟数据 |
| 辅助函数 | frontend/e2e/utils/api-helpers.mjs | API 验证 |
| 辅助函数 | frontend/e2e/utils/db-helpers.mjs | 数据库验证 |
| 测试用例 1 | frontend/e2e/cli/specs/01_project.spec.mjs | 项目创建 |
| 测试用例 2 | frontend/e2e/cli/specs/02_agent.spec.mjs | Agent管理 |
| 测试用例 3 | frontend/e2e/cli/specs/03_group.spec.mjs | 群聊创建 |
| 测试用例 4 | frontend/e2e/cli/specs/04_meeting.spec.mjs | 召开会议 |
| 测试用例 5 | frontend/e2e/cli/specs/05_requirement.spec.mjs | 需求确认 |
| 测试用例 6 | frontend/e2e/cli/specs/06_decompose.spec.mjs | 任务拆解 |
| 测试用例 7 | frontend/e2e/cli/specs/07_assign.spec.mjs | Agent分配 |
| 测试用例 8 | frontend/e2e/cli/specs/08_acceptance.spec.mjs | 子任务验收 |
| 测试用例 9 | frontend/e2e/cli/specs/09_handover.spec.mjs | 子任务交接 |
| 测试用例 10 | frontend/e2e/cli/specs/10_delivery.spec.mjs | 项目交付 |
