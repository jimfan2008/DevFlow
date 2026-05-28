# DevFlow Playwright CLI 完整实操检验计划

## 背景概述
- **目标**：使用 Playwright CLI 对已部署在 Docker 的 DevFlow 项目进行完整的功能实操验证
- **测试 URL**：`http://localhost:8080/`（用户已在 Chrome 中打开）
- **测试流程**：Hermes创建群聊 → 召开会议 → 确认需求说明书 → Hermes拆解任务 → 调度编程agent开发 → 子任务验收 → 子任务交接 → 项目交付

## 当前状态分析

### 环境状态
| 组件 | 状态 | 端口 |
|------|------|------|
| Docker 容器 | 运行中 | - |
| Nginx 前端 | 运行中 | 8080 |
| Backend API | healthy | 8000 |
| PostgreSQL | healthy | 15432 |
| Redis | healthy | 6379 |
| Gitea | 运行中 | 3000 |

### 问题诊断
1. **playwright 包损坏**：`node_modules/playwright/index.js` 和 `node_modules/playwright-core/index.js` 不存在
2. **测试配置过时**：使用 `localhost:3001` 而非 `localhost:8080`
3. **现有测试文件**：`frontend/e2e/cli/full-flow.mjs` 已创建但无法运行

### 架构理解
- **前端路由**：`/chat`, `/requirements`, `/boards`, `/acceptance`, `/delivery`
- **API 代理**：nginx 将 `/api/` 代理到 `backend:8000`
- **关键交互**：
  - ChatView.vue: 群聊/会议功能，Hermes Agent 参与
  - RequirementsView.vue: 需求管理，与 Hermes 对话确认需求

## 执行计划

### 阶段 1：修复测试环境
1. **清理损坏的 node_modules**
   - 强制删除 `frontend/node_modules` 目录
   - 删除 `frontend/package-lock.json`

2. **重新安装依赖**
   - 运行 `npm install` 安装所有依赖
   - 确保 playwright 包正确安装

### 阶段 2：更新测试配置
1. **修改 `frontend/e2e/cli/playwright.config.mjs`**
   ```javascript
   export const baseURL = 'http://localhost:8080';  // 更新为 nginx 端口
   export const apiURL = 'http://localhost:8080/api';  // 通过 nginx 代理
   ```

### 阶段 3：创建/更新测试脚本
创建 `frontend/e2e/cli/hermes-workflow.spec.mjs`，覆盖以下流程：

| 测试模块 | 测试内容 | 验证方式 |
|----------|----------|----------|
| TC-01: 登录 | 访问登录页，输入凭据登录 | 页面跳转、localStorage token |
| TC-02: Hermes创建群聊 | 进入 /chat，点击"新建"创建群组 | API `/api/chat/groups` 返回 200 |
| TC-03: 召开会议 | 在群聊中点击"启动会议" | 会议模式切换、agenda 显示 |
| TC-04: 确认需求 | 进入 /requirements，与 Hermes 对话 | 消息发送、AI 响应、文档生成 |
| TC-05: 需求文档 | 编辑需求文档，点击提交 | API `/api/requirements` 成功 |
| TC-06: 拆解任务 | 查看看板，Hermes 生成任务列表 | 任务卡片出现 |
| TC-07: Agent调度 | 分配任务给 Agent | API `/api/tasks/{id}/assign` 成功 |
| TC-08: 子任务验收 | 进入 /acceptance，验收任务 | 验收状态更新 |
| TC-09: 任务交接 | 完成任务交接 | 状态流转 |
| TC-10: 项目交付 | 进入 /delivery，交付项目 | 交付成功 |

### 阶段 4：运行测试
1. **执行命令**：
   ```bash
   cd frontend
   node e2e/cli/hermes-workflow.spec.mjs
   ```

2. **测试输出**：
   - 截图保存到 `e2e/screenshots/`
   - JSON 报告保存到 `e2e/results/`

### 阶段 5：验证结果
1. **检查测试通过率**：目标 > 80%
2. **分析失败原因**：针对每个失败的测试分析原因
3. **修复问题**：如有必要，更新测试或代码

## 测试数据
- **用户名**：`cli_hermes_{timestamp}`
- **邮箱**：`cli_hermes_{timestamp}@devflow.io`
- **密码**：`Test@1234`
- **项目名**：`Hermes工作流测试_{timestamp}`
- **群组名**：`Hermes测试组_{timestamp}`

## 关键验证点
1. **API 响应验证**：确保每个操作后端返回成功状态
2. **UI 状态验证**：页面元素正确显示
3. **数据持久化**：数据库中数据正确创建
4. **跨模块依赖**：测试顺序正确，前置数据存在

## 风险与应对
| 风险 | 应对措施 |
|------|----------|
| 网络超时 | 增加超时时间，使用重试 |
| 测试数据冲突 | 使用时间戳确保唯一性 |

## 预期输出
- 测试执行日志（控制台）
- 截图文件（每个测试步骤）
- JSON 测试报告
- 控制台错误日志
