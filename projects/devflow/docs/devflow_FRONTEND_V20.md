# DevFlow 项目管理平台 - 前端设计文档

**版本**: V20  
**日期**: 2026-06-23  
**作者**: HouWang (后旺)  
**状态**: 修订版V20（跨文档一致性检验修正）

---

## 1. 前端概述

### 1.1 设计目标

为 DevFlow 项目管理平台提供面向人类用户的 Web 前端界面，支持以下核心能力：

1. **项目创建与管理**：人类用户可创建软件项目、填写初始需求、查看项目进度
2. **需求沟通**：与需求分析师 Agent（后兴）对话，产出软件需求说明书
3. **讨论群交互**：参与项目讨论群，支持讨论模式和会议模式
4. **任务查看**：查看任务看板、任务状态、Agent 分配情况
5. **QA 检验报告**：查看后荣的 QA 检验结果和评分
6. **代码仓库浏览**：查看 Gitea 代码仓库的提交记录、PR、分支
7. **通知管理**：查看和处理系统通知
8. **文档管理**：查看项目文档（SRS、架构设计等）
9. **项目成员管理**：管理项目成员和角色权限
10. **多语言与无障碍**：支持中/英文切换，满足 WCAG 2.1 AA 级无障碍标准

### 1.2 技术选型

| 类别 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 框架 | Vue.js | 3.4+ | 响应式、组合式 API、TypeScript 友好 |
| 构建工具 | Vite | 5.0+ | 快速启动、HMR、原生 ESM |
| 语言 | TypeScript | 5.x | 类型安全、IDE 支持 |
| 状态管理 | Pinia | 2.1+ | Vue 3 官方推荐、轻量 |
| 状态持久化 | pinia-plugin-persistedstate | 4.x | Pinia 官方推荐的持久化插件 |
| UI 组件库 | Element Plus | 2.5+ | 丰富的企业级组件、主题定制 |
| 组件按需引入 | unplugin-vue-components | - | 自动按需导入 Element Plus 组件 JS 代码 |
| 接口按需引入 | unplugin-auto-import | - | 自动按需导入 Vue/VueRouter/Pinia API |
| 样式按需引入 | unplugin-vue-components + ElementPlusResolver(importStyle: 'css') | - | ElementPlusResolver 配置 importStyle: 'css' 时，unplugin-vue-components 会自动按需引入每个组件对应的 CSS 样式文件，无需额外插件 |
| HTTP 客户端 | Axios | 1.6+ | 拦截器、超时控制、取消请求 |
| WebSocket | 原生 WebSocket（多连接方案 + 独立认证） | - | 统一实时通信方案（消息推送 + 流式输出），三个独立 WebSocket 连接，按业务领域分离（群聊、通知、工作流），使用 access_token 通过 auth 消息认证 |
| 路由 | Vue Router | 4.2+ | Vue 3 官方路由 |
| 国际化 | vue-i18n | 9.x | 多语言支持 |
| 代码规范 | ESLint + Prettier | - | 统一代码风格 |
| 测试框架 | Vitest | 2.x | 与 Vite 生态一致、快速执行 |
| 组件测试 | @vue/test-utils | 2.x | Vue 官方组件测试库 |
| E2E 测试 | Playwright | 1.x | 跨浏览器 E2E 测试、Vue 官方推荐 |
| 拖拽库 | vue-draggable-plus | 2.x | Vue3 拖拽库，支持看板拖拽排序 |
| 虚拟列表 | @tanstack/vue-virtual | 3.x | TanStack 维护，原生 Vue 3 支持，活跃度高，替代 vue-virtual-scroller（后者为 Vue 2 时代库） |
| CSS 预处理 | SCSS | - | 变量、嵌套、混入 |
| 图标库 | @element-plus/icons-vue | - | 与 Element Plus 风格统一 |
| 富文本编辑器 | @tiptap/vue-3 | - | 需求描述、文档编辑 |
| Markdown 预览 | md-editor-v3 | - | SRS 等文档预览 |
| XSS 过滤 | DOMPurify | 3.x | 过滤富文本和 Markdown 中的危险 HTML |
| 图表 | ECharts | 5.x | 项目进度、Agent 负载统计（使用 @echarts/core 按需加载） |

**V9 -> V10 技术选型变更说明：**

| 变更项 | V9 方案 | V10 方案 | 变更理由 |
|--------|---------|----------|----------|
| SSE 流式输出 | 原生 EventSource | 统一使用 WebSocket | EventSource 不支持自定义 Header，无法携带认证 token；统一为 WebSocket 降低前后端复杂度 |
| 测试框架 | 未选型 | Vitest + @vue/test-utils + Playwright | 企业级项目需要完善的测试覆盖 |
| 状态持久化 | settingStore 使用 persist: true（未指明插件） | pinia-plugin-persistedstate | 明确持久化方案 |
| 按需引入 | 仅 unplugin-vue-components | 增加 unplugin-auto-import | 同时按需导入组件和框架 API，减少打包体积 |

**V10 -> V11 技术选型变更说明：**

| 变更项 | V10 方案 | V11 方案 | 变更理由 |
|--------|---------|----------|----------|
| 虚拟列表 | 未选型 | vue-virtual-scroller | 消息列表、提交列表等长列表场景需要虚拟滚动，避免数千条 DOM 节点导致卡顿 |
| XSS 过滤库 | sanitize.ts 已规划但未明确库 | DOMPurify 3.x | 明确使用 DOMPurify 作为 XSS 过滤库，补充 md-editor-v3 渲染 Agent 产出内容时的安全过滤方案 |

**V11 -> V12 技术选型变更说明：**

| 变更项 | V11 方案 | V12 方案 | 变更理由 |
|--------|---------|---------|---------|
| 虚拟列表 | vue-virtual-scroller | @tanstack/vue-virtual | vue-virtual-scroller 是 Vue 2 时代的库，在 Vue 3 项目中存在兼容性问题；@tanstack/vue-virtual 由 TanStack 维护，原生支持 Vue 3 Composition API，活跃度高 |
| ECharts 引入方式 | echarts 全量引入 | @echarts/core 按需加载 | ECharts 全量引入体积约 400KB gzip，按需加载可减少约 60% 体积 |
| Element Plus 样式按需 | importStyle 未明确 | ElementPlusResolver(importStyle: 'css') | V12 描述不够精确，V13 明确：ElementPlusResolver 配置 importStyle: 'css' 时，unplugin-vue-components 自动按需引入每个组件对应的 CSS 样式文件，无需 unelement 等额外插件 |

**V12 -> V13 技术选型变更说明：**

无技术选型变更，V13 主要是文档完整性修订和细节增强。

**V13 -> V14 技术选型变更说明：**

无技术选型变更，V14 针对后荣检验意见进行文档完整性补充和细节增强。

**V14 -> V15 技术选型变更说明：**

无技术选型变更，V15 针对后荣检验意见进行安全修复和细节修正。

**V15 -> V16 技术选型变更说明：**

| 变更项 | V15 方案 | V16 方案 | 变更理由 |
|--------|---------|---------|---------|
| Vite | 5.x | 5.0+ | 与架构文档 V22 的 2.2 节"前端技术栈"保持版本一致 |
| Pinia | 2.x | 2.1+ | 与架构文档 V22 的 2.2 节"前端技术栈"保持版本一致 |
| Element Plus | 2.x | 2.5+ | 与架构文档 V22 的 2.2 节"前端技术栈"保持版本一致 |
| Axios | 1.x | 1.6+ | 与架构文档 V22 的 2.2 节"前端技术栈"保持版本一致 |
| Vue Router | 4.x | 4.2+ | 与架构文档 V22 的 2.2 节"前端技术栈"保持版本一致 |

**V18 -> V19 技术选型变更说明：**

无技术选型变更，V19 针对跨文档一致性检验修正 WebSocket 认证方式。

**V19 -> V20 技术选型变更说明：**

| 变更项 | V19 方案 | V20 方案 | 变更理由 |
|--------|---------|---------|---------|
| WebSocket 连接方案 | 单连接复用 + 自定义消息路由 | 多连接方案（3个独立端点） | 对齐后端 V37 2.16 节定义的三个独立 WebSocket 端点：ws/group-chat、ws/notifications、ws/workflow/:project_id |
| WebSocket 认证方式 | ws_token（专用短时效令牌） | access_token（通过 auth 消息） | 后端 V37 移除了 ws-token 端点，恢复使用 access_token 进行 WebSocket 认证 |

### 1.3 浏览器支持

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+ (基于 Chromium)

### 1.4 项目目录结构

```
devflow-frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API 请求封装
│   │   ├── index.ts            # axios 实例配置
│   │   ├── project.ts          # 项目相关 API
│   │   ├── task.ts             # 任务相关 API
│   │   ├── chat.ts             # 讨论群 API
│   │   ├── agent.ts            # Agent 管理 API
│   │   ├── qa.ts               # QA 检验 API
│   │   ├── repo.ts             # 代码仓库 API
│   │   ├── notification.ts     # 通知 API
│   │   ├── docs.ts             # 文档管理 API（V20 新增）
│   │   └── user.ts             # 用户/成员管理 API（V20 新增）
│   ├── assets/                 # 静态资源
│   │   ├── images/
│   │   └── styles/
│   │       ├── global.scss     # 全局样式
│   │       ├── variables.scss  # 主题变量（浅色/深色 CSS 变量定义）
│   │       └── mixins.scss     # 样式混入
│   ├── components/             # 通用组件
│   │   ├── common/             # 基础组件
│   │   │   ├── AppHeader.vue   # 顶部导航
│   │   │   ├── AppSidebar.vue  # 侧边栏
│   │   │   ├── AppFooter.vue   # 底部信息
│   │   │   ├── AgentBadge.vue  # Agent 状态徽章
│   │   │   ├── StatusDot.vue   # 状态指示灯
│   │   │   ├── ErrorBoundary.vue # 错误边界组件
│   │   │   └── SkeletonLoader.vue # 骨架屏加载组件（V12 新增）
│   │   ├── project/            # 项目相关组件
│   │   │   ├── ProjectCard.vue # 项目卡片
│   │   │   ├── ProjectList.vue # 项目列表
│   │   │   ├── ProjectProgress.vue # 进度条
│   │   │   └── ProjectStatus.vue # 状态标签
│   │   ├── task/               # 任务相关组件
│   │   │   ├── TaskCard.vue    # 任务卡片
│   │   │   ├── TaskKanban.vue  # 看板视图
│   │   │   └── TaskTimeline.vue # 时间线视图
│   │   ├── chat/               # 聊天相关组件
│   │   │   ├── ChatWindow.vue  # 聊天窗口
│   │   │   ├── MessageBubble.vue # 消息气泡
│   │   │   ├── MessageInput.vue # 消息输入框
│   │   │   ├── MessageList.vue # 消息列表
│   │   │   └── MeetingAgenda.vue # 会议议程
│   │   ├── repo/               # 代码仓库组件
│   │   │   ├── RepoCard.vue    # 仓库卡片
│   │   │   ├── CommitList.vue  # 提交列表
│   │   │   ├── BranchList.vue  # 分支列表
│   │   │   └── PRList.vue      # PR 列表
│   │   ├── qa/                 # QA 相关组件
│   │   │   ├── QAResultCard.vue # 检验结果卡片
│   │   │   ├── QAScoreChart.vue # 评分图表
│   │   │   └── QAProblemList.vue # 问题列表
│   │   └── docs/               # 文档相关组件（V20 新增）
│   │       ├── DocViewer.vue   # 文档查看器
│   │       └── DocList.vue     # 文档列表
│   ├── composables/            # 组合式函数
│   │   ├── useWebSocket.ts     # WebSocket 连接管理（V20 多连接方案）
│   │   ├── useNotification.ts  # 通知管理
│   │   ├── useAuth.ts          # 认证相关
│   │   ├── useTheme.ts         # 主题切换
│   │   ├── useStreamRender.ts  # 流式输出打字机效果
│   │   └── useRetry.ts         # 请求重试策略（V12 新增）
│   ├── layouts/                # 布局组件
│   │   ├── DefaultLayout.vue   # 默认布局
│   │   └── ChatLayout.vue      # 聊天布局
│   ├── router/                 # 路由配置
│   │   ├── index.ts            # 路由定义
│   │   └── guards.ts           # 路由守卫
│   ├── stores/                 # Pinia 状态管理
│   │   ├── userStore.ts        # 用户状态
│   │   ├── projectStore.ts     # 项目状态
│   │   ├── taskStore.ts        # 任务状态
│   │   ├── chatStore.ts        # 聊天状态
│   │   ├── notificationStore.ts # 通知状态
│   │   ├── docsStore.ts        # 文档状态（V20 新增）
│   │   └── settingStore.ts     # 系统设置（本地偏好）
│   ├── views/                  # 页面视图
│   │   ├── LoginView.vue       # 登录页
│   │   ├── DashboardView.vue   # 首页/仪表板
│   │   ├── ProjectListView.vue # 项目列表页
│   │   ├── ProjectDetailView.vue # 项目详情页
│   │   ├── ChatView.vue        # 讨论群聊天页
│   │   ├── TaskView.vue        # 任务看板页
│   │   ├── QAView.vue          # QA 检验页
│   │   ├── RepoView.vue        # 代码仓库页
│   │   ├── DocsView.vue        # 文档管理页（V20 新增）
│   │   └── SettingsView.vue    # 系统设置页
│   ├── i18n/                   # 国际化
│   │   ├── index.ts            # i18n 配置
│   │   ├── zh-CN.json          # 中文语言包
│   │   └── en-US.json          # 英文语言包
│   ├── utils/                  # 工具函数
│   │   ├── format.ts           # 格式化函数
│   │   ├── constants.ts        # 常量定义
│   │   ├── errors.ts           # 自定义错误类型
│   │   └── sanitize.ts         # XSS 过滤工具
│   ├── types/                  # TypeScript 类型定义（V20 新增）
│   │   ├── index.ts            # 类型导出
│   │   ├── project.ts          # 项目相关类型（含 ProjectMember、Role）
│   │   └── common.ts           # 通用类型
│   ├── App.vue                 # 根组件
│   └── main.ts                 # 入口文件
├── tests/                      # 测试文件
│   ├── unit/                   # 单元测试
│   │   ├── components/
│   │   ├── composables/
│   │   └── stores/
│   ├── e2e/                    # E2E 测试
│   │   ├── login.spec.ts
│   │   ├── project.spec.ts
│   │   └── chat.spec.ts
│   └── setup.ts                # 测试配置
├── .env                        # 通用环境变量
├── .env.development            # 开发环境
├── .env.production             # 生产环境
├── index.html
├── vite.config.ts              # Vite 配置
├── vitest.config.ts            # Vitest 配置
├── playwright.config.ts        # Playwright 配置
├── tsconfig.json               # TypeScript 配置
├── .eslintrc.cjs               # ESLint 配置
├── .prettierrc                 # Prettier 配置
└── package.json
```

**V9 -> V10 目录结构变更说明：**

| 变更项 | 说明 |
|--------|------|
| 新增 ErrorBoundary.vue | 全局错误边界组件 |
| 新增 useWebSocket.ts | 统一实时通信（替代原 useWebSocket + useSSE 两个 composable） |
| 移除 useSSE.ts | SSE 方案已统一为 WebSocket |
| 新增 sanitize.ts | XSS 过滤工具函数 |
| 新增 tests/ 目录 | 单元测试和 E2E 测试 |
| 新增 vitest.config.ts | Vitest 测试配置 |
| 新增 playwright.config.ts | Playwright E2E 测试配置 |
| 新增 .env / .env.development / .env.production | 多环境配置 |

**V10 -> V11 目录结构变更说明：**

| 变更项 | 说明 |
|--------|------|
| 新增 useTheme.ts | 明确主题切换 composable 位置 |

**V11 -> V12 目录结构变更说明：**

| 变更项 | 说明 |
|--------|------|
| 新增 SkeletonLoader.vue | 骨架屏加载组件，用于数据加载时的占位显示 |
| 新增 useRetry.ts | 请求重试策略 composable，支持指数退避和最大重试次数 |

**V14 -> V15 目录结构变更说明：**

无目录结构变更。

**V15 -> V16 目录结构变更说明：**

无目录结构变更。

**V19 -> V20 目录结构变更说明：**

| 变更项 | 说明 |
|--------|------|
| 新增 api/docs.ts | 文档管理 API 模块 |
| 新增 api/user.ts | 用户/成员管理 API 模块 |
| 新增 stores/docsStore.ts | 文档状态管理 |
| 新增 types/ 目录 | TypeScript 类型定义（含 ProjectMember、Role 等） |
| 新增 views/DocsView.vue | 文档管理页面 |
| 新增 components/docs/ 目录 | 文档相关组件（DocViewer、DocList） |

---

## 2. 页面设计

### 2.1 页面清单

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录页 | /login | 用户登录 |
| 仪表板 | /dashboard | 首页，展示项目概览、最近动态 |
| 项目列表 | /projects | 所有项目列表，支持搜索/筛选 |
| 项目详情 | /projects/:id | 项目详情、进度、文档 |
| 讨论群聊天 | /projects/:id/chat | 项目讨论群实时聊天 |
| 任务看板 | /projects/:id/tasks | 任务看板视图 |
| QA 检验 | /projects/:id/qa | QA 检验结果与报告 |
| 代码仓库 | /projects/:id/repo | Gitea 代码仓库浏览 |
| 文档管理 | /projects/:id/docs | 项目文档管理（V20 新增） |
| 系统设置 | /settings | 个人设置、通知偏好 |

### 2.2 页面详细说明

#### 2.2.1 登录页 (/login)

- Element Plus 表单组件，包含用户名、密码字段
- 登录成功后获取 access token + refresh token，存入 Pinia userStore
- 登录失败显示错误提示
- 支持记住登录状态（localStorage 持久化 refresh token）
- 登录按钮加载状态：提交期间显示 loading 动画，防止重复提交

#### 2.2.2 仪表板 (/dashboard)

- 顶部统计卡片：进行中项目数、待处理通知数、Agent 在线数
- 项目列表（最近 5 个），点击跳转项目详情
- 最近动态时间线
- 快捷操作按钮：新建项目
- 数据加载时显示 SkeletonLoader 骨架屏

#### 2.2.3 项目列表 (/projects)

- 卡片列表布局，每张卡片展示：项目名称、描述、当前阶段、进度百分比、负责人 Agent
- 搜索框（按名称/描述搜索）
- 筛选条件：状态（进行中/已完成/已暂停）、创建时间
- 新建项目按钮，弹出创建对话框
- 数据加载时显示 SkeletonLoader 骨架屏

#### 2.2.4 项目详情 (/projects/:id)

- 项目基本信息（名称、描述、创建时间、当前阶段）
- 16 步流程进度条，高亮当前步骤
- 左侧导航标签：概览、文档、任务、讨论群、QA、代码仓库
- 文档区域：SRS、架构设计文档等，使用 md-editor-v3 预览（渲染管线：Markdown -> HTML -> sanitizeHtml -> v-html，详见 12.1 节）
- Agent 分配情况列表
- 项目成员列表（V20 新增）：展示项目成员及其角色（owner/admin/member/viewer）

#### 2.2.5 讨论群聊天 (/projects/:id/chat)

- 左侧：讨论群列表（当前项目的多个讨论群）
- 中间：消息列表，区分用户消息和 Agent 消息，使用 @tanstack/vue-virtual 虚拟滚动渲染（V12 变更）
- Agent 消息支持 WebSocket 流式输出显示，采用打字机效果渲染
- 会议模式：顶部显示会议议程（MeetingAgenda 组件）
- 底部区域说明：
  - 消息输入框（MessageInput 组件）：基于 @tiptap/vue-3 富文本编辑器，支持加粗、斜体、代码块、列表格式
  - 附件上传按钮：支持上传图片、文件附件，点击后弹出文件选择对话框
  - 发送按钮：点击或通过 Enter 快捷键发送消息；Shift+Enter 换行
  - WebSocket 连接状态指示：输入框上方显示连接状态（绿色=已连接，红色=已断开，黄色=重连中），断开时显示"连接已断开，正在重连..."提示
  - 流式输出等待状态：当 Agent 正在生成回复时，输入框显示"Agent 正在回复中..."的灰色提示，发送按钮禁用，防止用户重复发送

#### 2.2.6 任务看板 (/projects/:id/tasks)

- 看板列：待处理、进行中、待检验、已完成、已退回
- 任务卡片：任务标题、所属步骤、负责 Agent、优先级标签
- 支持拖拽卡片在不同列之间移动（vue-draggable-plus）
- 点击任务卡片弹出任务详情抽屉
- 顶部工具栏：
  - 筛选条件：按负责 Agent 筛选、按优先级筛选、按步骤编号筛选
  - 视图切换：看板视图 / 列表视图 / 时间线视图（TaskTimeline 组件）
  - 搜索框：按任务标题搜索
- 每列顶部显示该列任务数量统计
- 拖拽完成后自动调用 API 更新任务状态，失败时回滚卡片位置并提示用户

#### 2.2.7 QA 检验 (/projects/:id/qa)

- 检验结果列表，按步骤排序
- 每个检验结果展示：步骤名称、检验 Agent（后荣）、评分、状态（通过/不通过）
- 不通过的检验项展示具体问题列表（QAProblemList 组件）
- 评分雷达图（QAScoreChart 组件，基于 ECharts 按需加载）
- 顶部工具栏：
  - 筛选条件：按检验状态（通过/不通过）筛选、按步骤筛选
  - 查看模式切换：列表模式 / 雷达图对比模式
- 评分趋势折线图：展示各步骤检验评分的变化趋势（ECharts 折线图，按需加载）
- 点击检验结果卡片弹出详情抽屉，展示完整检验报告（包括检验维度明细、问题描述、建议修改方案）

#### 2.2.8 代码仓库 (/projects/:id/repo)

- 仓库基本信息：名称、描述、默认分支
- 提交记录列表（CommitList 组件），使用 @tanstack/vue-virtual 虚拟滚动渲染，支持分页（V12 变更）
- 分支列表（BranchList 组件）
- PR 列表（PRList 组件），展示 PR 状态、评论数、文件变更
- 顶部工具栏：
  - 分支切换下拉框：切换查看不同分支的提交记录
  - 查看模式切换：提交记录 / 分支列表 / PR 列表
  - 搜索框：按提交信息、作者搜索

#### 2.2.9 文档管理 (/projects/:id/docs)（V20 新增）

- 文档列表（DocList 组件）：展示项目相关文档（SRS、架构设计、后端设计、前端设计、数据库设计等）
- 文档查看器（DocViewer 组件）：使用 md-editor-v3 预览 Markdown 文档
- 支持文档版本对比
- 文档筛选：按文档类型筛选（需求、设计、技术、测试等）

#### 2.2.10 系统设置 (/settings)

- 个人信息：头像、用户名
- 通知偏好：邮件通知、浏览器推送开关（本地偏好设置，settingStore 管理）
- 语言切换：中文/英文
- 主题设置：浅色/深色（由 settingStore 管理 theme 字段，切换时通过 useTheme composable 给 `<html>` 添加/移除 `dark` 类，Element Plus 内置 dark 主题跟随切换，详见 9.2 节）
- 其他设置：
  - 自动刷新间隔：设置项目进度自动刷新的时间间隔（30s/60s/120s/手动）
  - 清除本地缓存：清除 localStorage 中持久化的用户偏好（不退出登录）

---

## 3. 组件设计

### 3.1 通用组件

#### 3.1.1 AppHeader（顶部导航）

```typescript
interface AppHeaderProps {
  username: string;
  avatarUrl?: string;
  unreadCount: number;
}
```

- 左侧：DevFlow Logo + 产品名称
- 中间：面包屑导航
- 右侧：语言切换、通知铃铛（带未读数量徽标）、用户头像下拉菜单
- 下拉菜单项：个人设置、退出登录

#### 3.1.2 AppSidebar（侧边栏）

```typescript
interface AppSidebarProps {
  projectId: string | null;
  collapsed: boolean;
}
```

- 全局导航项：仪表板、项目列表
- 项目导航项（进入项目后显示）：概览、文档、任务、讨论群、QA、代码仓库
- 支持折叠/展开

#### 3.1.3 AgentBadge（Agent 状态徽章）

```typescript
interface AgentBadgeProps {
  agentName: string;
  agentRole: string;
  status: 'idle' | 'working' | 'offline' | 'error';
}
```

- 显示 Agent 名称、角色标签
- 状态指示灯（StatusDot 组件）
- 工作状态显示当前任务摘要

#### 3.1.4 StatusDot（状态指示灯）

```typescript
interface StatusDotProps {
  status: 'idle' | 'working' | 'offline' | 'error';
  animate?: boolean;
}
```

- idle: 灰色静态圆点
- working: 绿色脉冲动画圆点
- offline: 深灰色静态圆点
- error: 红色静态圆点

#### 3.1.5 ErrorBoundary（错误边界）

```typescript
interface ErrorBoundaryProps {
  fallback?: VueComponent;
}
```

- 捕获子组件树中的渲染错误和异步错误
- 默认 fallback 显示错误提示和重试按钮
- 支持自定义 fallback 组件
- 错误信息上报至后端日志接口

**V15 修订：重试机制修复**

V14 中 `retry()` 仅将 `error.value` 设为 `false`，但 Vue 的 `onErrorCaptured` 不会自动重新触发子组件渲染。V15 引入 `retryKey` 强制重新挂载：在 slot 外层绑定 `:key="retryKey"`，`retry()` 时自增 `retryKey`，Vue 会卸载旧组件树并重新挂载，从而真正重新渲染子组件。

```vue
<template>
  <div v-if="error">
    <el-result icon="error" title="组件加载失败" :sub-title="errorMessage">
      <template #extra>
        <el-button type="primary" @click="retry">重试</el-button>
      </template>
    </el-result>
  </div>
  <div v-else :key="retryKey">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue';

const error = ref(false);
const errorMessage = ref('');
const retryKey = ref(0);

onErrorCaptured((err, vm, info) => {
  error.value = true;
  errorMessage.value = err.message || '未知错误';
  reportError(err, vm, info);
  return false; // 阻止错误向上传播
});

const retry = () => {
  error.value = false;
  retryKey.value++; // 自增 key 强制 Vue 卸载旧组件树并重新挂载
};
</script>
```

**重试机制原理说明：**

| 步骤 | 行为 | 说明 |
|------|------|------|
| 1 | 子组件渲染出错 | `onErrorCaptured` 捕获错误，`error.value = true`，显示 fallback |
| 2 | 用户点击"重试" | `retry()` 将 `error.value = false`，`retryKey.value++` |
| 3 | `:key` 变化触发重挂载 | Vue 检测到 key 变化，卸载旧组件树（含出错的子组件），创建全新的组件树 |
| 4 | 子组件重新渲染 | 全新挂载的子组件不再携带之前的错误状态 |

**为什么不直接用 `error.value = false`：**

仅将 `error.value` 设为 `false` 时，Vue 会重新渲染 slot 内容，但出错的子组件实例仍然存在，其内部错误状态未重置，`onErrorCaptured` 不会再次触发。使用 `:key` 强制重挂载可以确保子组件从 `setup()` 开始全新初始化。

#### 3.1.6 SkeletonLoader（骨架屏加载组件，V12 新增）

```typescript
interface SkeletonLoaderProps {
  variant: 'card' | 'list' | 'table' | 'text';
  rowCount?: number;
}
```

- `card`：模拟卡片布局的骨架屏（用于项目列表、仪表板）
- `list`：模拟列表项的骨架屏（用于消息列表、提交列表）
- `table`：模拟表格行的骨架屏（用于任务列表）
- `text`：模拟文本段落的骨架屏（用于文档预览）
- 使用 CSS 动画实现闪烁效果（`animation: skeleton-pulse 1.5s ease-in-out infinite`）
- 数据加载完成后自动隐藏，无闪烁切换

```vue
<template>
  <div class="skeleton-loader" :class="variant">
    <div
      v-for="i in rowCount"
      :key="i"
      class="skeleton-row"
    >
      <div class="skeleton-block" v-for="j in getBlockCount(variant)" :key="j"
           :style="getBlockStyle(variant, j)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { SkeletonLoaderProps } from './types';
defineProps<SkeletonLoaderProps>();

const getBlockCount = (variant: string) => {
  const map = { card: 3, list: 2, table: 4, text: 1 };
  return map[variant as keyof typeof map] || 2;
};

const getBlockStyle = (variant: string, index: number) => {
  // 根据不同 variant 和位置返回不同宽度
};
</script>

<style scoped>
.skeleton-block {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  border-radius: 4px;
}
html.dark .skeleton-block {
  background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%);
  background-size: 200% 100%;
}
@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
```

### 3.2 聊天相关组件

#### 3.2.1 ChatWindow（聊天窗口）

```typescript
interface ChatWindowProps {
  groupId: string;
  projectId: string;
}
```

- 集成 MessageList、MessageInput 子组件
- 连接 WebSocket（group-chat 连接）获取实时消息和流式输出
- 自动滚动到底部
- 会议模式下显示 MeetingAgenda

#### 3.2.2 MessageBubble（消息气泡）

```typescript
interface MessageBubbleProps {
  message: GroupMessage;
  isStreaming?: boolean;
}

interface GroupMessage {
  id: string;
  sender_id: string;
  sender_type: 'user' | 'agent';
  sender_name: string;
  content: string;
  timestamp: string;
  attachments?: Attachment[];
}
```

- 用户消息：右侧对齐，蓝色背景
- Agent 消息：左侧对齐，灰色背景，显示 Agent 名称和角色
- 流式输出时显示打字动画
- 附件展示（文件、图片、代码片段）
- 渲染 Markdown 内容时，先通过 sanitizeHtml() 过滤再使用 v-html 渲染，防止 XSS 注入

#### 3.2.3 MessageInput（消息输入框）

```typescript
interface MessageInputProps {
  disabled?: boolean;
}
```

- 富文本输入（@tiptap/vue-3），支持加粗、斜体、代码块、列表
- 发送按钮
- 附件上传按钮
- 快捷键：Enter 发送，Shift+Enter 换行

#### 3.2.4 MessageList（消息列表）

```typescript
interface MessageListProps {
  messages: GroupMessage[];
  streamingMessages: Map<string, string>;
}
```

- 虚拟滚动渲染（V12 变更：使用 @tanstack/vue-virtual 替代 vue-virtual-scroller）
- 按时间分组显示（今天、昨天、更早）
- 流式消息实时追加渲染

**V12 变更：虚拟列表实现方案（@tanstack/vue-virtual）**

**V15 修订：动态 measure 机制**

V14 中 `estimateSize` 固定为 80px，但聊天消息包含附件、代码块等内容时高度差异较大。V15 增加动态 measure 机制：MessageBubble 渲染完成后通过 `useNextTick` 获取实际高度，调用 `rowVirtualizer.measureItem(index, actualHeight)` 更新尺寸缓存，使虚拟滚动器的位置计算更精确。

```vue
<template>
  <div ref="parentRef" class="message-scroller" style="height: 100%; overflow-y: auto;">
    <div :style="{ height: `${totalHeight}px`, position: 'relative' }">
      <div
        v-for="virtualRow in virtualRows"
        :key="messages[virtualRow.index].id"
        :style="{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          transform: `translateY(${virtualRow.start}px)`,
        }"
      >
        <MessageBubble
          :message="messages[virtualRow.index]"
          :is-streaming="isStreaming(messages[virtualRow.index].id)"
          @measured="onMeasured"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import { useVirtualizer } from '@tanstack/vue-virtual';

const props = defineProps<MessageListProps>();
const parentRef = ref<HTMLElement | null>(null);

const rowVirtualizer = useVirtualizer({
  count: computed(() => props.messages.length),
  getScrollElement: () => parentRef.value,
  estimateSize: () => 80, // 初始预估高度 80px
  overscan: 5, // 预渲染 5 条
});

const virtualRows = computed(() => rowVirtualizer.value?.getVirtualItems() || []);
const totalHeight = computed(() => rowVirtualizer.value?.getTotalSize() || 0);

// V15 新增：动态 measure 机制
// 当 MessageBubble 渲染完成后，通过 $el.offsetHeight 获取实际高度
// 调用 measureItem 更新 virtualizer 的尺寸缓存
const onMeasured = async (index: number, el: HTMLElement) => {
  const actualHeight = el.offsetHeight;
  // 仅当实际高度与预估高度差异超过阈值时才更新（避免频繁调整）
  const estimated = 80;
  if (Math.abs(actualHeight - estimated) > 10) {
    rowVirtualizer.value?.measureItem(index, actualHeight);
  }
};

const isStreaming = (messageId: string) => {
  return props.streamingMessages.has(messageId);
};
</script>
```

**MessageBubble 组件中上报实际高度：**

```vue
<!-- MessageBubble.vue 中新增 @measured 事件上报 -->
<script setup lang="ts">
import { onMounted, nextTick } from 'vue';

const emit = defineEmits<{
  measured: [index: number, el: HTMLElement];
}>();

const bubbleRef = ref<HTMLElement | null>(null);
const index = computed(() => props.message.id); // 或使用传入的 index prop

onMounted(async () => {
  await nextTick();
  if (bubbleRef.value) {
    emit('measured', /* index */, bubbleRef.value);
  }
});
</script>
```

**动态 measure 机制说明：**

| 环节 | 行为 | 说明 |
|------|------|------|
| 初始渲染 | estimateSize = 80px | virtualizer 使用 80px 作为所有条目的初始预估高度 |
| 消息渲染完成 | MessageBubble 通过 `@measured` 上报实际高度 | 使用 `nextTick` 确保 DOM 已更新 |
| 高度差异检测 | 比较实际高度与预估高度 | 差异超过 10px 才触发 measureItem，避免频繁调整 |
| measureItem 调用 | `rowVirtualizer.measureItem(index, actualHeight)` | 更新该条目的尺寸缓存，virtualizer 重新计算位置 |
| 滚动位置修正 | virtualizer 自动调整 | 新增的实际尺寸会导致 totalHeight 变化，滚动位置可能微调 |

- @tanstack/vue-virtual 使用 `useVirtualizer` hook，原生支持 Vue 3 Composition API
- `estimateSize` 为初始预估高度（80px），V15 新增动态 measure 机制使长消息（含附件、代码块）的滚动更精确
- 仅渲染可视区域内的消息 DOM 节点，数千条消息也能保持流畅滚动
- 流式消息追加时，Vue 响应式更新自动触发 virtualizer 重新计算
- 相比 vue-virtual-scroller，@tanstack/vue-virtual 无需额外的 CSS 依赖包，API 更简洁

#### 3.2.5 MeetingAgenda（会议议程）

```typescript
interface MeetingAgendaProps {
  agenda: MeetingAgendaItem[];
  currentPhase: string;
}

interface MeetingAgendaItem {
  phase: string;
  title: string;
  speaker?: string;
  status: 'pending' | 'active' | 'completed';
}
```

- 竖排时间线样式
- 当前阶段高亮
- 已完成阶段灰色显示

### 3.3 任务相关组件

#### 3.3.1 TaskKanban（任务看板）

```typescript
interface TaskKanbanProps {
  columns: KanbanColumn[];
}

interface KanbanColumn {
  id: string;
  title: string;
  status: string;
  tasks: Task[];
}
```

- 使用 vue-draggable-plus 实现列内排序和列间拖拽
- 每列顶部显示任务数量
- 拖拽时显示放置区域高亮
- 拖拽完成后调用 API 更新任务状态

安装依赖：

```bash
npm install vue-draggable-plus
```

看板组件中使用方式：

```vue
<template>
  <Draggable
    v-model="column.tasks"
    group="tasks"
    item-key="id"
    @end="onDragEnd"
  >
    <template #item="{ element }">
      <TaskCard :task="element" />
    </template>
  </Draggable>
</template>

<script setup lang="ts">
import { Draggable } from 'vue-draggable-plus';
import { onDragEnd } from './task-actions';
</script>
```

#### 3.3.2 TaskCard（任务卡片）

```typescript
interface TaskCardProps {
  task: Task;
}

interface Task {
  id: string;
  title: string;
  step_number: number;
  step_name: string;
  assignee_agent?: string;
  status: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at: string;
}
```

- 卡片展示：标题、步骤编号、负责 Agent（AgentBadge）、优先级标签
- 点击弹出详情抽屉

#### 3.3.3 TaskTimeline（任务时间线）

```typescript
interface TaskTimelineProps {
  tasks: Task[];
}
```

- 按时间排序的任务列表
- 时间线样式，展示任务创建、更新、完成的时间点
- 每个时间点显示操作人和操作内容

### 3.4 项目相关组件

#### 3.4.1 ProjectCard（项目卡片）

```typescript
interface ProjectCardProps {
  project: Project;
}

interface Project {
  id: string;
  name: string;
  description: string;
  current_step: number;
  progress: number;
  status: 'active' | 'completed' | 'paused';
  created_at: string;
  updated_at: string;
}
```

- 卡片展示：项目名称、描述（截断）、进度条、状态标签
- 点击进入项目详情

#### 3.4.2 ProjectProgress（进度条）

```typescript
interface ProjectProgressProps {
  currentStep: number;
  totalSteps: number;
  stepLabels?: string[];
}
```

- 16 步流程可视化
- 已完成步骤绿色，当前步骤蓝色高亮，未完成步骤灰色
- 悬停显示步骤名称

### 3.5 QA 相关组件

#### 3.5.1 QAResultCard（检验结果卡片）

```typescript
interface QAResultCardProps {
  result: QARecord;
}

interface QARecord {
  id: string;
  step_number: number;
  step_name: string;
  inspecting_agent: string;
  score: number;
  status: 'pass' | 'fail';
  problems?: QAProblem[];
  inspected_at: string;
}
```

- 展示：步骤名称、检验 Agent、评分、通过/不通过状态
- 不通过时展开显示问题列表

#### 3.5.2 QAScoreChart（评分图表）

```typescript
interface QAScoreChartProps {
  records: QARecord[];
}
```

- 基于 ECharts 的雷达图（V12：使用 @echarts/core 按需加载，详见 1.2 节和 7.1 节）
- 维度：完整性、一致性、可验证性、无歧义性、代码正确性、测试通过率
- 多步骤对比（折线图模式）

**V12 补充：ECharts 按需加载方案**

```typescript
// src/utils/echarts.ts — ECharts 按需加载
import * as echarts from 'echarts/core';
import { RadarChart, LineChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

// 仅注册实际使用的图表类型和组件
echarts.use([
  RadarChart,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
]);

export default echarts;
```

- 全量 echarts 约 400KB gzip，按需加载后约 150-200KB gzip（减少约 50-60%）
- 项目中仅使用雷达图（RadarChart）和折线图（LineChart），故仅注册这两个图表类型
- 所需的组件：TitleComponent、TooltipComponent、LegendComponent、GridComponent
- 渲染器使用 CanvasRenderer（默认）

#### 3.5.3 QAProblemList（问题列表）

```typescript
interface QAProblemListProps {
  problems: QAProblem[];
}

interface QAProblem {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  description: string;
  location?: string;
}
```

- 按严重程度排序
- 严重程度标签颜色：critical=红色，high=橙色，medium=黄色，low=蓝色
- 可折叠/展开

### 3.6 文档相关组件（V20 新增）

#### 3.6.1 DocViewer（文档查看器）

```typescript
interface DocViewerProps {
  docId: string;
  projectId: string;
}
```

- 使用 md-editor-v3 预览 Markdown 文档
- 支持文档版本切换
- XSS 过滤（sanitizeHtml）

#### 3.6.2 DocList（文档列表）

```typescript
interface DocListProps {
  docs: ProjectDoc[];
}

interface ProjectDoc {
  id: string;
  title: string;
  type: 'srs' | 'architecture' | 'backend' | 'frontend' | 'database' | 'other';
  version: string;
  updated_at: string;
}
```

- 文档卡片列表，按类型分组
- 点击跳转到文档查看器

---

## 4. 状态管理（Pinia）

### 4.1 持久化策略

使用 `pinia-plugin-persistedstate` 插件实现状态持久化，以下 store 需要持久化：

| Store | 持久化字段 | 存储介质 | 理由 |
|-------|-----------|---------|------|
| userStore | refreshToken | localStorage | 页面刷新后保持登录状态。refreshToken 有效期较长（7天），仅用于获取新的 accessToken |
| settingStore | 全部字段（language、theme、emailNotification、browserPush） | localStorage | 用户偏好设置需持久保存，页面刷新后恢复 |
| projectStore | 不持久化 | - | 项目数据从服务器获取，无需本地缓存 |
| taskStore | 不持久化 | - | 任务数据从服务器获取，无需本地缓存 |
| chatStore | 不持久化 | - | 聊天数据从服务器获取，WebSocket 实时推送 |
| notificationStore | 不持久化 | - | 通知数据从服务器获取，WebSocket 实时推送 |
| docsStore | 不持久化 | - | 文档数据从服务器获取，无需本地缓存 |

**存储介质选择依据：**

| 存储介质 | 容量 | 生命周期 | 适用场景 |
|---------|------|---------|---------|
| localStorage | ~5-10MB | 永久（需手动清除） | 用户偏好、refreshToken 等需要长期保存的数据 |
| sessionStorage | ~5-10MB | 标签页关闭即清除 | 临时状态（本方案未使用） |
| 内存（Pinia state） | 无限制（受 RAM 约束） | 页面刷新即丢失 | accessToken、业务数据等敏感或易变数据 |

```typescript
// main.ts 中配置持久化插件
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);
```

**V12 补充：持久化安全策略**

- **仅持久化非敏感字段**：userStore 仅持久化 `refreshToken`，`accessToken` 存储在内存中，页面刷新后通过 refresh token 重新获取
- **settingStore 不含敏感信息**：settingStore 持久化的字段为用户偏好（language、theme、通知开关等），不涉及 token、密码等敏感数据
- **敏感数据不落地**：accessToken 从不写入 localStorage，避免 XSS 窃取；refreshToken 虽持久化，但仅用于获取新的 accessToken，有效期较长且可被服务端吊销
- **清除缓存功能**：系统设置页提供"清除本地缓存"按钮，仅清除 settingStore 的持久化数据，不影响登录状态

```typescript
// settingStore 明确只持久化非敏感字段
export const useSettingStore = defineStore('setting', {
  state: (): SettingState => ({
    language: 'zh-CN',
    theme: 'light',
    emailNotification: true,
    browserPush: false,
  }),
  persist: {
    key: 'devflow-settings',
    storage: localStorage,
    // 所有字段均为非敏感用户偏好，无需加密
  },
});
```

### 4.2 userStore

**职责**：管理用户认证状态、Token 生命周期、登录/登出操作。

**V20 修订：恢复使用 access_token 进行 WebSocket 认证**

V19 使用 ws_token 进行 WebSocket 认证。后端 V37 移除了 ws-token 端点，恢复使用 access_token 进行 WebSocket auth 消息认证，响应类型改为 auth_success/auth_error。V20 移除 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法，与后端 V37 保持一致。

```typescript
interface UserState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  tokenExpiry: number | null;
}

interface User {
  id: string;
  username: string;
  email: string;
  avatar_url?: string;
  language: 'zh-CN' | 'en-US';
}

// V20 新增：项目成员角色定义（对齐架构 V24 §6.1）
export type ProjectRole = 'owner' | 'admin' | 'member' | 'viewer';

export interface ProjectMember {
  id: string;
  user_id: string;
  username: string;
  role: ProjectRole;
  joined_at: string;
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    user: null,
    accessToken: null,
    refreshToken: null,
    tokenExpiry: null,
  }),
  actions: {
    async login(username: string, password: string) {
      const res = await api.post('/auth/login', { username, password });
      this.accessToken = res.data.access_token;
      this.refreshToken = res.data.refresh_token;
      this.tokenExpiry = Date.now() + res.data.expires_in * 1000;
      this.user = res.data.user;
    },
    async refreshToken() {
      if (!this.refreshToken) return false;
      try {
        const res = await api.post('/auth/refresh', {
          refresh_token: this.refreshToken,
        });
        this.accessToken = res.data.access_token;
        this.refreshToken = res.data.refresh_token;
        this.tokenExpiry = Date.now() + res.data.expires_in * 1000;
        return true;
      } catch {
        this.logout();
        return false;
      }
    },
    async ensureAuthenticated() {
      if (!this.accessToken || !this.tokenExpiry) return false;
      if (Date.now() >= this.tokenExpiry - 60000) {
        return await this.refreshToken();
      }
      return true;
    },
    logout() {
      this.user = null;
      this.accessToken = null;
      this.refreshToken = null;
      this.tokenExpiry = null;
    },
  },
  persist: {
    key: 'devflow-user',
    storage: localStorage,
    pick: ['refreshToken'], // 仅持久化 refreshToken，accessToken 不持久化
  },
});
```

**Token 刷新机制说明：**

1. 登录成功后获取 access token 和 refresh token
2. access token 存储在 memory 中，refresh token 持久化到 localStorage
3. Axios 请求拦截器中检查 token 有效期：
   - 若 token 将在 60 秒内过期，主动调用 `/auth/refresh` 刷新
   - 若接口返回 401，尝试使用 refresh token 刷新
   - 刷新成功后重试原请求
   - 刷新失败则跳转登录页
4. 同一时刻只允许一个 refresh 请求，其他请求排队等待
5. WebSocket 认证使用 access_token，连接建立后通过首条 auth 消息携带 access_token 认证

**Axios 拦截器 + 请求队列完整实现：**

```typescript
// src/api/index.ts 中配置请求拦截器和响应拦截器
import axios from 'axios';
import { useUserStore } from '@/stores/userStore';
import router from '@/router';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：附加 token
api.interceptors.request.use(config => {
  const userStore = useUserStore();
  if (userStore.accessToken) {
    config.headers.Authorization = `Bearer ${userStore.accessToken}`;
  }
  return config;
});

// 响应拦截器：token 过期自动刷新 + 请求队列
let isRefreshing = false;
let failedQueue: Array<{ resolve: (value: any) => void; reject: (reason?: any) => void }> = [];

const processQueue = (error: null, token: string | null) => {
  failedQueue.forEach(prom => {
    if (error) prom.reject(error);
    else prom.resolve();
  });
  failedQueue = [];
};

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retried) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => api(originalRequest));
      }

      originalRequest._retried = true;
      isRefreshing = true;

      try {
        const userStore = useUserStore();
        const success = await userStore.refreshToken();

        if (success) {
          originalRequest.headers.Authorization = `Bearer ${userStore.accessToken}`;
          processQueue(null, userStore.accessToken);
          return api(originalRequest);
        } else {
          processQueue(new Error('Token refresh failed'), null);
          userStore.logout();
          router.push('/login');
          return Promise.reject(error);
        }
      } catch (err) {
        processQueue(err as Error, null);
        userStore.logout();
        router.push('/login');
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

**请求队列工作流程：**

```
时刻 T1: 请求 A 发出 -> 401 -> 开始刷新 token (isRefreshing=true)
时刻 T2: 请求 B 发出 -> 401 -> isRefreshing=true -> 加入 failedQueue 等待
时刻 T3: 请求 C 发出 -> 401 -> isRefreshing=true -> 加入 failedQueue 等待
时刻 T4: token 刷新成功 -> processQueue(null, newToken) -> 请求 B、C 依次重试
时刻 T5: 请求 A 重试成功 -> 返回结果
         请求 B 重试成功 -> 返回结果
         请求 C 重试成功 -> 返回结果
```

### 4.3 projectStore

**职责**：管理项目列表、当前项目详情、项目创建操作。数据从服务器获取，不持久化。

```typescript
interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  // V20 新增：项目成员列表（对齐架构 V24 §6.1）
  members: ProjectMember[];
}

export const useProjectStore = defineStore('project', {
  state: (): ProjectState => ({
    projects: [],
    currentProject: null,
    loading: false,
    members: [],
  }),
  actions: {
    async fetchProjects() {
      this.loading = true;
      this.projects = await api.get('/projects');
      this.loading = false;
    },
    async fetchProject(id: string) {
      this.currentProject = await api.get(`/projects/${id}`);
    },
    async createProject(data: CreateProjectDto) {
      const res = await api.post('/projects', data);
      this.projects.push(res.data);
      return res.data;
    },
    // V20 新增：获取项目成员列表
    async fetchMembers(projectId: string) {
      this.members = await api.get(`/projects/${projectId}/members`);
    },
  },
});
```

### 4.4 taskStore

**职责**：管理任务列表、看板列分组、任务状态更新。数据从服务器获取，不持久化。

**V20 修订：updateTaskStatus 改为使用 PUT 方法**

前端 V19 使用 `api.patch`，后端 V37 §2.5 定义为 `PUT /tasks/:id`。V20 改为使用 `api.put`，与后端保持一致。

```typescript
interface TaskState {
  tasks: Task[];
  columns: KanbanColumn[];
  loading: boolean;
}

export const useTaskStore = defineStore('task', {
  state: (): TaskState => ({
    tasks: [],
    columns: [],
    loading: false,
  }),
  actions: {
    async fetchTasks(projectId: string) {
      this.loading = true;
      this.tasks = await api.get(`/projects/${projectId}/tasks`);
      this.columns = this.groupByStatus(this.tasks);
      this.loading = false;
    },
    // V20 修订：改为 api.put，对齐后端 V37 §2.5
    async updateTaskStatus(taskId: string, status: string) {
      await api.put(`/tasks/${taskId}`, { status });
      const task = this.tasks.find(t => t.id === taskId);
      if (task) task.status = status;
      this.columns = this.groupByStatus(this.tasks);
    },
    groupByStatus(tasks: Task[]): KanbanColumn[] {
      // 按 status 分组返回列数据
    },
  },
});
```

### 4.5 chatStore

**职责**：管理讨论群列表、消息列表、流式输出状态。通过 WebSocket（group-chat 连接）接收实时消息和流式输出，委托 useWebSocket composable 处理底层连接。

```typescript
interface ChatState {
  groups: DiscussionGroup[];
  currentGroup: DiscussionGroup | null;
  messages: GroupMessage[];
  streamingContent: Map<string, string>;
}

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    groups: [],
    currentGroup: null,
    messages: [],
    streamingContent: new Map(),
  }),
  actions: {
    async fetchGroups(projectId: string) {
      this.groups = await api.get(`/projects/${projectId}/groups`);
    },
    async fetchMessages(groupId: string) {
      this.messages = await api.get(`/groups/${groupId}/messages`);
    },
    async sendMessage(groupId: string, content: string) {
      const msg = await api.post(`/groups/${groupId}/messages`, { content });
      this.messages.push(msg.data);
      return msg.data;
    },
    setStreamingContent(messageId: string, content: string) {
      this.streamingContent.set(messageId, content);
    },
    clearStreamingContent(messageId: string) {
      this.streamingContent.delete(messageId);
    },
    connectWebSocket(groupId: string) {
      useWebSocket().connectGroup(groupId);
    },
    disconnectWebSocket() {
      useWebSocket().disconnectGroup();
    },
    handleStreamChunk(messageId: string, chunk: string) {
      const current = this.streamingContent.get(messageId) || '';
      this.streamingContent.set(messageId, current + chunk);
    },
    handleStreamDone(messageId: string, fullContent: string) {
      const msg = this.messages.find(m => m.id === messageId);
      if (msg) msg.content = fullContent;
      this.streamingContent.delete(messageId);
    },
  },
});
```

**Store 与 composable 的调用关系（V20 修订）：**

- `connectWebSocket` / `disconnectWebSocket`：chatStore 委托 useWebSocket composable 的 group-chat 连接处理
- `handleStreamChunk` / `handleStreamDone`：流式输出通过 group-chat WebSocket 接收，由 chatStore 处理状态更新
- composable 负责三个独立 WebSocket 连接的管理，Store 负责状态更新和消息协调

### 4.6 notificationStore

**职责**：管理通知列表、未读数量。通过 WebSocket（notifications 连接）接收实时通知推送。

**V20 修订：markAsRead 改为使用 PUT 方法**

前端 V19 使用 `api.patch`，后端 V37 §2.12 定义为 `PUT /api/v1/notifications/:id/read`。V20 改为使用 `api.put`，与后端保持一致。

```typescript
interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
}

export const useNotificationStore = defineStore('notification', {
  state: (): NotificationState => ({
    notifications: [],
    unreadCount: 0,
  }),
  actions: {
    async fetchNotifications() {
      this.notifications = await api.get('/notifications');
      this.unreadCount = this.notifications.filter(n => !n.read).length;
    },
    // V20 修订：改为 api.put，对齐后端 V37 §2.12
    async markAsRead(id: string) {
      await api.put(`/notifications/${id}/read`);
      const n = this.notifications.find(x => x.id === id);
      if (n) n.read = true;
      this.unreadCount = this.notifications.filter(x => !x.read).length;
    },
  },
});
```

### 4.7 docsStore（V20 新增）

**职责**：管理项目文档列表、文档内容。数据从服务器获取，不持久化。

```typescript
interface DocsState {
  docs: ProjectDoc[];
  currentDoc: ProjectDoc | null;
  loading: boolean;
}

export const useDocsStore = defineStore('docs', {
  state: (): DocsState => ({
    docs: [],
    currentDoc: null,
    loading: false,
  }),
  actions: {
    async fetchDocs(projectId: string) {
      this.loading = true;
      this.docs = await api.get(`/projects/${projectId}/docs`);
      this.loading = false;
    },
    async fetchDoc(projectId: string, docId: string) {
      this.currentDoc = await api.get(`/projects/${projectId}/docs/${docId}`);
    },
  },
});
```

### 4.8 settingStore

**职责**：管理用户偏好设置（语言、主题、通知开关）。数据持久化到 localStorage。**仅本地偏好设置，不通过 API 同步到后端**（后端 V37 无 /settings 端点）。

```typescript
interface SettingState {
  language: 'zh-CN' | 'en-US';
  theme: 'light' | 'dark';
  emailNotification: boolean;
  browserPush: boolean;
}

export const useSettingStore = defineStore('setting', {
  state: (): SettingState => ({
    language: 'zh-CN',
    theme: 'light',
    emailNotification: true,
    browserPush: false,
  }),
  // V20 修订：移除 fetchSettings 和 updateSettings 方法
  // settingStore 仅管理本地持久化偏好，不与后端 API 交互
  persist: {
    key: 'devflow-settings',
    storage: localStorage,
  },
});
```

**Store 职责总览表（V20 修订）：**

| Store | 职责 | 数据来源 | 持久化 | WebSocket 交互 |
|-------|------|---------|--------|---------------|
| userStore | 认证状态、Token 管理 | 登录接口 + refresh 接口 | 仅 refreshToken | WebSocket 使用 access_token 通过 auth 消息认证 |
| projectStore | 项目列表、项目详情、项目成员 | REST API | 否 | 接收 project.step.changed（通过 workflow WS） |
| taskStore | 任务列表、看板分组 | REST API | 否 | 接收 task.updated（通过 workflow WS） |
| chatStore | 讨论群、消息、流式输出 | REST API + WebSocket | 否 | group-chat WS：接收 message.new/stream.chunk/stream.done，发送 message.send/chat.join/chat.leave |
| notificationStore | 通知列表、未读数 | REST API + WebSocket | 否 | notifications WS：接收 notification |
| docsStore | 项目文档列表与内容 | REST API | 否 | 无 |
| settingStore | 用户偏好设置（本地） | 本地持久化 | 是（全字段） | 无 |

---

## 5. API 设计

### 5.1 API 基础配置

**Axios 实例配置**：

```typescript
// src/api/index.ts
import axios from 'axios';
import { useUserStore } from '@/stores/userStore';
import router from '@/router';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：附加认证 token
api.interceptors.request.use(config => {
  const userStore = useUserStore();
  if (userStore.accessToken) {
    config.headers.Authorization = `Bearer ${userStore.accessToken}`;
  }
  return config;
});

// 响应拦截器：统一错误处理 + token 刷新
// 详见 4.2 节的完整实现
```

**API 分层架构：**

| 层次 | 文件 | 职责 |
|------|------|------|
| 实例层 | api/index.ts | Axios 实例配置、请求/响应拦截器、Token 管理 |
| 模块层 | api/project.ts、api/task.ts 等 | 按业务模块组织 API 函数，导出类型安全的请求方法 |
| Store 层 | stores/*.ts | 调用模块层 API，更新 Pinia 状态 |
| 组件层 | views/*.vue、components/*.vue | 调用 Store actions 或直接调用模块层 API |

**模块层 API 示例：**

```typescript
// src/api/project.ts
import api from './index';

export function fetchProjects() {
  return api.get<Project[]>('/projects');
}

export function fetchProject(id: string) {
  return api.get<Project>(`/projects/${id}`);
}

export function createProject(data: CreateProjectDto) {
  return api.post<Project>('/projects', data);
}

// V20 修订：改为 api.put，对齐后端 V37 §2.3
export function updateProject(id: string, data: Partial<Project>) {
  return api.put<Project>(`/projects/${id}`, data);
}

export function fetchProjectProgress(id: string) {
  return api.get<ProjectProgress>(`/projects/${id}/progress`);
}

// V20 新增：获取项目成员列表（对齐架构 V24 §6.1）
export function fetchProjectMembers(projectId: string) {
  return api.get<ProjectMember[]>(`/projects/${projectId}/members`);
}
```

**V20 新增：文档管理 API 模块**

```typescript
// src/api/docs.ts
import api from './index';

// 对齐架构 V24 §3.4
export function fetchProjectDocs(projectId: string) {
  return api.get<ProjectDoc[]>(`/projects/${projectId}/docs`);
}

export function fetchDoc(projectId: string, docId: string) {
  return api.get<ProjectDoc>(`/projects/${projectId}/docs/${docId}`);
}
```

### 5.2 API 端点清单

#### 认证相关

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /auth/login | 用户登录 |
| POST | /auth/refresh | 刷新 access token |
| POST | /auth/logout | 退出登录 |

**V20 修订：移除 POST /auth/ws-token 端点**（后端 V37 无此端点，WebSocket 认证改为使用 access_token）

#### 项目相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects | 项目列表 |
| POST | /projects | 创建项目 |
| GET | /projects/:id | 项目详情 |
| PUT | /projects/:id | 更新项目（V20 修订：对齐后端 V37 §2.3） |
| GET | /projects/:id/progress | 项目进度 |
| GET | /projects/:id/members | 项目成员列表（V20 新增：对齐架构 V24 §6.1） |
| POST | /projects/:id/repo/init | 初始化代码仓库（V20 新增：对齐架构 V24 §2.2） |
| POST | /projects/:id/repo/commit | 提交代码（V20 新增：对齐架构 V24 §2.2） |

#### 文档管理（V20 新增）

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects/:id/docs | 项目文档列表（对齐架构 V24 §3.4） |
| GET | /projects/:id/docs/:docId | 文档详情 |

#### 任务相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects/:id/tasks | 任务列表 |
| PUT | /tasks/:id | 更新任务（V20 修订：对齐后端 V37 §2.5） |

#### 讨论群相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects/:id/groups | 讨论群列表 |
| GET | /groups/:id/messages | 消息列表 |
| POST | /groups/:id/messages | 发送消息 |

#### QA 相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects/:id/qa | QA 检验记录 |
| GET | /qa/:id | 检验详情 |

#### 代码仓库相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects/:id/repo | 仓库信息 |
| GET | /projects/:id/repo/commits | 提交记录 |
| GET | /projects/:id/repo/branches | 分支列表 |
| GET | /projects/:id/repo/prs | PR 列表 |

#### 通知相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /notifications | 通知列表 |
| PUT | /notifications/:id/read | 标记已读（V20 修订：对齐后端 V37 §2.12） |

### 5.3 错误处理统一方案

前端采用分层错误处理策略：

#### 全局异常捕获

```typescript
// main.ts 中注册全局错误处理器
app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue Error]', err, info);
  api.post('/errors/report', {
    message: err.message,
    stack: err.stack,
    component: info,
    timestamp: new Date().toISOString(),
  }).catch(() => {});
};

window.addEventListener('unhandledrejection', event => {
  console.error('[Unhandled Rejection]', event.reason);
  api.post('/errors/report', {
    message: event.reason?.message || 'Unhandled rejection',
    timestamp: new Date().toISOString(),
  }).catch(() => {});
});
```

#### Axios 响应错误处理

```typescript
// src/utils/errors.ts
export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends ApiError {
  constructor(message: string) {
    super(0, 'NETWORK_ERROR', message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends ApiError {
  constructor(message: string) {
    super(408, 'TIMEOUT', message);
    this.name = 'TimeoutError';
  }
}

const errorMap: Record<number, string> = {
  400: '请求参数错误',
  401: '未授权，请重新登录',
  403: '无权访问',
  404: '资源不存在',
  408: '请求超时',
  422: '数据验证失败',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务不可用',
  504: '网关超时',
};

export function useGlobalError() {
  const ElMessage = await import('element-plus').then(m => m.ElMessage);

  const handleError = (error: unknown) => {
    if (error instanceof ApiError) {
      ElMessage.error({ message: error.message, duration: 3000 });
    } else if (axios.isAxiosError(error)) {
      const message = errorMap[error.response?.status ?? 0] || '网络异常';
      ElMessage.error({ message, duration: 3000 });
    } else {
      ElMessage.error({ message: '未知错误', duration: 3000 });
    }
  };

  return { handleError };
}
```

#### 组件级错误边界

- 使用 3.1.5 节定义的 ErrorBoundary 组件包裹高风险子树
- 包裹范围：ChatWindow（WebSocket 连接异常）、QAScoreChart（ECharts 渲染异常）、ProjectDetail（复杂嵌套组件）

#### V12 新增：请求重试策略（useRetry composable）

```typescript
// src/composables/useRetry.ts
interface RetryOptions {
  maxAttempts?: number;      // 最大重试次数，默认 3
  baseDelay?: number;        // 基础延迟（ms），默认 1000
  maxDelay?: number;         // 最大延迟（ms），默认 10000
  retryableStatuses?: number[]; // 可重试的 HTTP 状态码
}

export function useRetry(options: RetryOptions = {}) {
  const {
    maxAttempts = 3,
    baseDelay = 1000,
    maxDelay = 10000,
    retryableStatuses = [408, 429, 500, 502, 503, 504],
  } = options;

  const executeWithRetry = async <T>(
    fn: () => Promise<T>,
    attempt = 1
  ): Promise<T> => {
    try {
      return await fn();
    } catch (error) {
      if (attempt >= maxAttempts) throw error;

      const isAxiosErr = axios.isAxiosError(error);
      const status = isAxiosErr ? error.response?.status : 0;

      if (!isAxiosErr || !retryableStatuses.includes(status)) {
        throw error; // 非可重试错误，直接抛出
      }

      // 指数退避：baseDelay * 2^(attempt-1)，不超过 maxDelay
      const delay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
      await new Promise(resolve => setTimeout(resolve, delay));

      return executeWithRetry(fn, attempt + 1);
    }
  };

  return { executeWithRetry };
}
```

**重试策略说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| maxAttempts | 3 | 最多重试 3 次 |
| baseDelay | 1000ms | 第 1 次重试延迟 1 秒 |
| maxDelay | 10000ms | 单次重试延迟上限 10 秒 |
| retryableStatuses | [408, 429, 500, 502, 503, 504] | 仅对服务器端错误或限流进行重试 |

**使用示例：**

```typescript
// 在 API 调用中使用重试
const { executeWithRetry } = useRetry({ maxAttempts: 3 });

const fetchProject = async (id: string) => {
  return executeWithRetry(async () => {
    return await api.get(`/projects/${id}`);
  });
};
```

---

## 6. WebSocket 通信设计

### 6.1 多连接通信方案

**V9 -> V10 变更说明：**

V9 同时使用 WebSocket 和 SSE（EventSource）两种协议，存在以下问题：

1. EventSource 不支持自定义 Header，无法携带认证 token
2. 同时维护两种实时通信协议增加前后端复杂度
3. 需要后端额外设计 token-less 的 SSE 端点

V10 统一为 WebSocket 单一方案，所有实时通信（消息推送、状态变更、流式输出）均通过 WebSocket 完成。

**V20 修订：多连接方案（对齐后端 V37 §2.16）**

V19 采用全局单连接方案，整个应用生命周期内仅维护一个 WebSocket 连接。后端 V37 定义为三个独立的 WebSocket 端点：

- `ws://host/ws/group-chat` — 群聊消息推送和流式输出
- `ws://host/ws/notifications` — 通知推送
- `ws://host/ws/workflow/:project_id` — 工作流状态变更推送

V20 改为多连接方案，每个端点独立连接、独立认证、独立重连。

**三个 WebSocket 端点与 Store 的映射关系：**

| WebSocket 端点 | 目标消费者 | 说明 |
|---------------|----------|------|
| ws/group-chat | chatStore | 群聊消息推送、流式输出 |
| ws/notifications | notificationStore | 系统通知推送 |
| ws/workflow/:project_id | projectStore、taskStore | 项目步骤变更、任务状态变更 |

**连接管理策略：**

| 场景 | 连接行为 |
|------|---------|
| 应用启动 | 用户登录后自动建立 notifications 连接 |
| 进入讨论群 | 建立 group-chat 连接 |
| 切换讨论群 | 不重建 group-chat 连接，发送 chat.join 加入新群，同时发送 chat.leave 离开旧群 |
| 进入项目详情 | 建立 workflow 连接（携带 projectId） |
| 切换项目 | 关闭旧 workflow 连接，建立新 workflow 连接 |
| 用户登出 | 关闭所有 WebSocket 连接 |
| 页面刷新 | 所有连接丢失，登录后重新建立 |

**认证方式（V20 修订）：**

所有 WebSocket 端点使用统一的认证方式：

1. WebSocket 连接 URL 不携带任何 token
2. 连接建立后，客户端发送首条 auth 消息携带 access_token 进行认证
3. 后端对 WS 端点禁用 access log，避免 token 泄露
4. 认证成功后返回 `auth_success`，认证失败返回 `auth_error`

**消息路由机制（V20 修订）：**

由于采用多连接方案，每个 WebSocket 端点承载特定类型的消息，不需要全局 type 路由：

- group-chat 连接：message.new、message.deleted、stream.chunk、stream.done、stream.error
- notifications 连接：notification
- workflow 连接：project.step.changed、task.updated

**流式输出与普通消息的优先级处理：**

| 优先级 | 消息类型 | 处理策略 | 原因 |
|--------|---------|---------|------|
| 高 | stream.chunk | 立即处理，直接更新 pendingContent，触发 requestAnimationFrame 渲染 | 流式输出需要实时展示，延迟超过 16ms 会感知卡顿 |
| 高 | stream.done | 立即处理，清除流式状态，最终渲染 | 确保流式输出结束时内容完整 |
| 普通 | message.new | 推入消息列表，Vue 响应式自动渲染 | 已完成的消息，无需立即渲染 |
| 普通 | project.step.changed | 更新 store 状态 | 进度条更新可延迟到下一帧 |
| 普通 | task.updated | 更新 store 状态 | 看板更新可延迟 |
| 低 | notification | 推入通知列表 + 弹出 ElNotification | 通知可异步展示 |

**优先级实现方式：**

```typescript
// onmessage 处理器内部按优先级分发（仅 group-chat 连接需要优先级处理）
ws.value.onmessage = (event) => {
  const data = JSON.parse(event.data);
  const type = data.type;

  // 高优先级：直接同步处理（stream.*）
  if (type.startsWith('stream.')) {
    triggerEvent(type, data); // 同步执行，不排队
  }
  // 普通优先级：推入微任务队列
  else if (['message.new'].includes(type)) {
    queueMicrotask(() => triggerEvent(type, data));
  }
  // 低优先级：推入宏任务队列
  else {
    setTimeout(() => triggerEvent(type, data), 0);
  }
};
```

**优先级设计原理：**

- `stream.chunk` 使用同步执行，确保最低延迟（< 4ms），保证打字机效果流畅
- 普通消息使用 `queueMicrotask`，在同一次事件循环中处理，延迟极低（< 1ms）但不会阻塞 stream 处理
- 通知使用 `setTimeout(..., 0)`，推到下一个事件循环，完全不阻塞其他消息处理

### 6.2 WebSocket 事件类型

| 事件类型 | 方向 | 端点 | 说明 |
|----------|------|------|------|
| message.new | Server -> Client | group-chat | 新消息推送（消息已完成） |
| message.deleted | Server -> Client | group-chat | 消息删除通知 |
| stream.chunk | Server -> Client | group-chat | Agent 回复内容增量追加 |
| stream.done | Server -> Client | group-chat | Agent 回复完成 |
| stream.error | Server -> Client | group-chat | 流式输出错误 |
| notification | Server -> Client | notifications | 系统通知推送 |
| project.step.changed | Server -> Client | workflow | 项目步骤推进 |
| task.updated | Server -> Client | workflow | 任务状态变更 |
| chat.join | Client -> Server | group-chat | 加入讨论群 |
| chat.leave | Client -> Server | group-chat | 离开讨论群 |
| message.send | Client -> Server | group-chat | 发送消息 |
| heartbeat.ping | Client -> Server | 所有 | 心跳请求 |
| heartbeat.pong | Server -> Client | 所有 | 心跳响应 |
| auth | Client -> Server | 所有 | 连接建立后的首次认证消息（携带 access_token） |

**职责说明：**

- `message.new` 推送的是**已完成的消息**
- `stream.chunk` / `stream.done` 负责**流式输出的过程展示**
- 两者不重复：流式输出结束后，客户端已拥有完整消息内容
- 前端流程：用户发送消息 -> WebSocket 发送 message.send -> 服务端开始生成回复 -> WebSocket 推送 stream.chunk 逐块 -> WebSocket 推送 stream.done 结束

**V20 修订：auth 事件说明（对齐后端 V37 §2.16）**

WebSocket 连接建立后，客户端直接使用 `userStore.accessToken` 进行认证，与后端 V37 §2.16 节定义的认证流程一致：

```
客户端                          服务端
  |                               |
  |-- WebSocket 连接请求 -------->|  (不携带 token)
  |                               |
  |<-- 连接建立 (101 Switching) --|
  |                               |
  |-- {"type": "auth",           |
      "token": "access_token_xxx"} --->|
  |                               |
  |<-- {"type": "auth_success"} --------|  (认证通过)
  |                               |
  |-- 正常业务消息 ... ---------->|
```

**V14 新增：心跳机制**

为防止网络中间设备（如代理、NAT 网关）因空闲超时关闭 WebSocket 连接，客户端实现主动心跳机制：

```typescript
// 每个 WebSocket 连接独立维护心跳定时器
const HEARTBEAT_INTERVAL = 30000; // 30 秒发送一次心跳
const HEARTBEAT_TIMEOUT = 5000;   // 5 秒未收到 pong 视为超时

let heartbeatTimer: number | null = null;
let heartbeatTimeout: number | null = null;

const startHeartbeat = (ws: WebSocket) => {
  stopHeartbeat();
  heartbeatTimer = window.setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    // 发送 ping
    ws.send(JSON.stringify({ type: 'heartbeat.ping', timestamp: Date.now() }));

    // 设置超时检测
    heartbeatTimeout = window.setTimeout(() => {
      // 超时未收到 pong，视为连接异常，主动重连
      ElMessage.warning('网络连接不稳定，正在重连...');
      ws.close(4000, 'Heartbeat timeout');
    }, HEARTBEAT_TIMEOUT);
  }, HEARTBEAT_INTERVAL);
};

const stopHeartbeat = () => {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  if (heartbeatTimeout) {
    clearTimeout(heartbeatTimeout);
    heartbeatTimeout = null;
  }
};
```

**心跳机制参数说明：**

| 参数 | 值 | 说明 |
|------|-----|------|
| 心跳间隔 | 30 秒 | 每 30 秒发送一次 ping |
| 超时阈值 | 5 秒 | 发送 ping 后 5 秒未收到 pong 视为连接异常 |
| 超时处理 | 主动关闭 + 重连 | 触发重连机制，弹出提示"网络连接不稳定，正在重连..." |
| pong 处理 | 清除超时定时器 | 收到 pong 后清除超时定时器，不触发业务事件 |

**心跳机制与重连机制的关系：**

```
正常情况:
  客户端 --[ping]--> 服务器 --[pong]--> 客户端 (每 30 秒循环)

网络中断:
  客户端 --[ping]--> (无响应)
  5 秒后 -> 超时 -> 关闭连接 -> 触发重连机制 -> 指数退避重连

重连成功后:
  重置心跳定时器 -> 恢复正常心跳循环
```

### 6.3 WebSocket 连接管理（useWebSocket composable）

**V20 修订：多连接管理 + access_token 认证（对齐后端 V37）**

V19 使用单连接方案 + ws_token 认证。V20 改为三个独立 WebSocket 连接 + access_token 认证，与后端 V37 §2.16 节保持一致。

```typescript
// src/composables/useWebSocket.ts

export function useWebSocket() {
  // 三个独立的 WebSocket 连接
  const groupChatWs = ref<WebSocket | null>(null);
  const notificationsWs = ref<WebSocket | null>(null);
  const workflowWs = ref<WebSocket | null>(null);

  const groupChatConnected = ref(false);
  const notificationsConnected = ref(false);
  const workflowConnected = ref(false);

  const groupChatReconnectAttempts = ref(0);
  const notificationsReconnectAttempts = ref(0);
  const workflowReconnectAttempts = ref(0);

  const groupChatReconnectStatus = ref<'connected' | 'disconnected' | 'reconnecting'>('disconnected');
  const notificationsReconnectStatus = ref<'connected' | 'disconnected' | 'reconnecting'>('disconnected');
  const workflowReconnectStatus = ref<'connected' | 'disconnected' | 'reconnecting'>('disconnected');

  let groupChatHandlers: Map<string, Function[]> = new Map();
  let notificationsHandlers: Map<string, Function[]> = new Map();
  let workflowHandlers: Map<string, Function[]> = new Map();

  let groupChatHeartbeat: { timer: number | null; timeout: number | null } = { timer: null, timeout: null };
  let notificationsHeartbeat: { timer: number | null; timeout: number | null } = { timer: null, timeout: null };
  let workflowHeartbeat: { timer: number | null; timeout: number | null } = { timer: null, timeout: null };

  // ==================== 工具函数 ====================

  const getWsUrl = (endpoint: string) => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || location.host;
    return `${protocol}//${host}${endpoint}`;
  };

  // V20 修订：使用 access_token 进行 auth 消息认证
  const authenticate = (ws: WebSocket) => {
    const userStore = useUserStore();
    if (ws.readyState === WebSocket.OPEN && userStore.accessToken) {
      ws.send(JSON.stringify({
        type: 'auth',
        token: userStore.accessToken,
      }));
    }
  };

  const startHeartbeat = (ws: WebSocket, heartbeatRef: { timer: number | null; timeout: number | null }) => {
    heartbeatRef.timer = window.setInterval(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({ type: 'heartbeat.ping', timestamp: Date.now() }));
      heartbeatRef.timeout = window.setTimeout(() => {
        ElMessage.warning('网络连接不稳定，正在重连...');
        ws.close(4000, 'Heartbeat timeout');
      }, 5000);
    }, 30000);
  };

  const stopHeartbeat = (heartbeatRef: { timer: number | null; timeout: number | null }) => {
    if (heartbeatRef.timer) { clearInterval(heartbeatRef.timer); heartbeatRef.timer = null; }
    if (heartbeatRef.timeout) { clearTimeout(heartbeatRef.timeout); heartbeatRef.timeout = null; }
  };

  const triggerEvent = (handlers: Map<string, Function[]>, eventType: string, data: any) => {
    const handlerList = handlers.get(eventType);
    handlerList?.forEach(h => h(data));
  };

  // ==================== group-chat 连接 ====================

  const connectGroup = (groupId: string) => {
    if (groupChatWs.value) return;

    groupChatWs.value = new WebSocket(getWsUrl('/ws/group-chat'));

    groupChatWs.value.onopen = () => {
      groupChatConnected.value = true;
      groupChatReconnectAttempts.value = 0;
      groupChatReconnectStatus.value = 'connected';

      // 连接建立后发送 auth 消息（使用 access_token）
      authenticate(groupChatWs.value);
    };

    groupChatWs.value.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // 处理 auth 响应
      if (data.type === 'auth_success') {
        startHeartbeat(groupChatWs.value, groupChatHeartbeat);
        groupChatWs.value?.send(JSON.stringify({
          type: 'chat.join',
          payload: { group_id: groupId },
        }));
        return;
      }

      if (data.type === 'auth_error') {
        // access_token 过期或无效，跳转登录页
        const userStore = useUserStore();
        userStore.logout();
        router.push('/login');
        groupChatWs.value?.close();
        return;
      }

      if (data.type === 'heartbeat.pong') {
        if (groupChatHeartbeat.timeout) {
          clearTimeout(groupChatHeartbeat.timeout);
          groupChatHeartbeat.timeout = null;
        }
        return;
      }

      // 优先级处理
      if (data.type.startsWith('stream.')) {
        triggerEvent(groupChatHandlers, data.type, data); // 同步
      } else if (data.type === 'message.new') {
        queueMicrotask(() => triggerEvent(groupChatHandlers, data.type, data));
      } else {
        setTimeout(() => triggerEvent(groupChatHandlers, data.type, data), 0);
      }
    };

    groupChatWs.value.onerror = () => {
      groupChatReconnectStatus.value = 'reconnecting';
    };

    groupChatWs.value.onclose = (event) => {
      groupChatConnected.value = false;
      stopHeartbeat(groupChatHeartbeat);
      groupChatWs.value = null;
      if (!event.wasClean) {
        attemptReconnect('group', groupId);
      }
    };
  };

  const disconnectGroup = () => {
    stopHeartbeat(groupChatHeartbeat);
    if (groupChatWs.value) {
      groupChatWs.value.close(1000, 'Client disconnecting');
      groupChatWs.value = null;
      groupChatConnected.value = false;
      groupChatReconnectStatus.value = 'disconnected';
    }
  };

  // ==================== notifications 连接 ====================

  const connectNotifications = () => {
    if (notificationsWs.value) return;

    notificationsWs.value = new WebSocket(getWsUrl('/ws/notifications'));

    notificationsWs.value.onopen = () => {
      notificationsConnected.value = true;
      notificationsReconnectAttempts.value = 0;
      notificationsReconnectStatus.value = 'connected';

      authenticate(notificationsWs.value);
    };

    notificationsWs.value.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'auth_success') {
        startHeartbeat(notificationsWs.value, notificationsHeartbeat);
        return;
      }

      if (data.type === 'auth_error') {
        const userStore = useUserStore();
        userStore.logout();
        router.push('/login');
        notificationsWs.value?.close();
        return;
      }

      if (data.type === 'heartbeat.pong') {
        if (notificationsHeartbeat.timeout) {
          clearTimeout(notificationsHeartbeat.timeout);
          notificationsHeartbeat.timeout = null;
        }
        return;
      }

      // 通知消息低优先级
      setTimeout(() => triggerEvent(notificationsHandlers, data.type, data), 0);
    };

    notificationsWs.value.onerror = () => {
      notificationsReconnectStatus.value = 'reconnecting';
    };

    notificationsWs.value.onclose = (event) => {
      notificationsConnected.value = false;
      stopHeartbeat(notificationsHeartbeat);
      notificationsWs.value = null;
      if (!event.wasClean) {
        attemptReconnect('notifications');
      }
    };
  };

  const disconnectNotifications = () => {
    stopHeartbeat(notificationsHeartbeat);
    if (notificationsWs.value) {
      notificationsWs.value.close(1000, 'Client disconnecting');
      notificationsWs.value = null;
      notificationsConnected.value = false;
      notificationsReconnectStatus.value = 'disconnected';
    }
  };

  // ==================== workflow 连接 ====================

  const connectWorkflow = (projectId: string) => {
    if (workflowWs.value) return;

    workflowWs.value = new WebSocket(getWsUrl(`/ws/workflow/${projectId}`));

    workflowWs.value.onopen = () => {
      workflowConnected.value = true;
      workflowReconnectAttempts.value = 0;
      workflowReconnectStatus.value = 'connected';

      authenticate(workflowWs.value);
    };

    workflowWs.value.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'auth_success') {
        startHeartbeat(workflowWs.value, workflowHeartbeat);
        return;
      }

      if (data.type === 'auth_error') {
        const userStore = useUserStore();
        userStore.logout();
        router.push('/login');
        workflowWs.value?.close();
        return;
      }

      if (data.type === 'heartbeat.pong') {
        if (workflowHeartbeat.timeout) {
          clearTimeout(workflowHeartbeat.timeout);
          workflowHeartbeat.timeout = null;
        }
        return;
      }

      // workflow 消息普通优先级
      queueMicrotask(() => triggerEvent(workflowHandlers, data.type, data));
    };

    workflowWs.value.onerror = () => {
      workflowReconnectStatus.value = 'reconnecting';
    };

    workflowWs.value.onclose = (event) => {
      workflowConnected.value = false;
      stopHeartbeat(workflowHeartbeat);
      workflowWs.value = null;
      if (!event.wasClean) {
        attemptReconnect('workflow');
      }
    };
  };

  const disconnectWorkflow = () => {
    stopHeartbeat(workflowHeartbeat);
    if (workflowWs.value) {
      workflowWs.value.close(1000, 'Client disconnecting');
      workflowWs.value = null;
      workflowConnected.value = false;
      workflowReconnectStatus.value = 'disconnected';
    }
  };

  // ==================== 通用重连逻辑 ====================

  const attemptReconnect = (connectionType: 'group' | 'notifications' | 'workflow', groupId?: string) => {
    const maxAttempts = 5;
    const attemptsRef = connectionType === 'group' ? groupChatReconnectAttempts
      : connectionType === 'notifications' ? notificationsReconnectAttempts
      : workflowReconnectAttempts;

    const delay = Math.min(1000 * Math.pow(2, attemptsRef.value), 30000);
    attemptsRef.value++;

    const statusRef = connectionType === 'group' ? groupChatReconnectStatus
      : connectionType === 'notifications' ? notificationsReconnectStatus
      : workflowReconnectStatus;

    if (attemptsRef.value <= maxAttempts) {
      statusRef.value = 'reconnecting';
      setTimeout(() => {
        if (connectionType === 'group') connectGroup(groupId!);
        else if (connectionType === 'notifications') connectNotifications();
        else connectWorkflow(/* projectId from route */);
      }, delay);
    } else {
      statusRef.value = 'disconnected';
      ElMessage.error({
        message: 'WebSocket 连接失败，已超出最大重连次数，请检查网络后刷新页面',
        duration: 5000,
      });
    }
  };

  // ==================== 事件注册 ====================

  const onGroup = (eventType: string, handler: Function) => {
    if (!groupChatHandlers.has(eventType)) groupChatHandlers.set(eventType, []);
    groupChatHandlers.get(eventType)?.push(handler);
  };

  const offGroup = (eventType: string, handler: Function) => {
    const handlers = groupChatHandlers.get(eventType);
    if (handlers) { const idx = handlers.indexOf(handler); if (idx > -1) handlers.splice(idx, 1); }
  };

  const onNotification = (eventType: string, handler: Function) => {
    if (!notificationsHandlers.has(eventType)) notificationsHandlers.set(eventType, []);
    notificationsHandlers.get(eventType)?.push(handler);
  };

  const offNotification = (eventType: string, handler: Function) => {
    const handlers = notificationsHandlers.get(eventType);
    if (handlers) { const idx = handlers.indexOf(handler); if (idx > -1) handlers.splice(idx, 1); }
  };

  const onWorkflow = (eventType: string, handler: Function) => {
    if (!workflowHandlers.has(eventType)) workflowHandlers.set(eventType, []);
    workflowHandlers.get(eventType)?.push(handler);
  };

  const offWorkflow = (eventType: string, handler: Function) => {
    const handlers = workflowHandlers.get(eventType);
    if (handlers) { const idx = handlers.indexOf(handler); if (idx > -1) handlers.splice(idx, 1); }
  };

  // ==================== 全局断开 ====================

  const disconnectAll = () => {
    disconnectGroup();
    disconnectNotifications();
    disconnectWorkflow();
  };

  return {
    // group-chat 连接
    groupChatConnected,
    groupChatReconnectStatus,
    connectGroup,
    disconnectGroup,
    onGroup,
    offGroup,
    // notifications 连接
    notificationsConnected,
    notificationsReconnectStatus,
    connectNotifications,
    disconnectNotifications,
    onNotification,
    offNotification,
    // workflow 连接
    workflowConnected,
    workflowReconnectStatus,
    connectWorkflow,
    disconnectWorkflow,
    onWorkflow,
    offWorkflow,
    // 全局
    disconnectAll,
  };
}
```

**V20 修订：认证流程（对齐后端 V37）**

| 步骤 | V19 方案 | V20 方案 |
|------|---------|---------|
| 1. 获取令牌 | 通过 POST /auth/ws-token 获取 ws_token | 直接使用 userStore.accessToken |
| 2. 建立连接 | `new WebSocket('ws://host/ws')` 单连接 | 三个独立连接：`ws/group-chat`、`ws/notifications`、`ws/workflow/:project_id` |
| 3. 认证 | 连接建立后调用 `userStore.ensureWsToken()` 获取 ws_token，发送 `{"type": "auth", "token": "ws_token"}` | 连接建立后直接使用 `userStore.accessToken`，发送 `{"type": "auth", "token": "access_token"}` |
| 4. 认证通过 | 收到 `auth_ok` 后启动心跳 | 收到 `auth_success` 后启动心跳 |
| 5. 认证失败 | 收到 `auth_fail` 后尝试重新获取 ws_token，失败后跳转登录页 | 收到 `auth_error` 后直接跳转登录页 |
| 6. token 泄露影响 | ws_token 仅用于 WebSocket | access_token 泄露可访问所有 API（但 WS 帧不记录到日志） |

**重连机制完整说明：**

| 参数 | 值 | 说明 |
|------|-----|------|
| 最大重连次数 | 5 次 | 超过后停止重连并通知用户 |
| 退避算法 | 指数退避 | 第 N 次重连延迟 = min(1000 * 2^(N-1), 30000) 毫秒 |
| 第 1 次重连延迟 | 1 秒 | |
| 第 2 次重连延迟 | 2 秒 | |
| 第 3 次重连延迟 | 4 秒 | |
| 第 4 次重连延迟 | 8 秒 | |
| 第 5 次重连延迟 | 16 秒 | |
| 重连成功后 | 重置计数器 | reconnectAttempts 归零，重新执行 auth 认证流程 |
| 超过最大次数后 | 停止重连 | 弹出 ElMessage 错误提示，建议用户刷新页面 |

**用户感知提示：**

- 各连接 reconnectStatus 为响应式 ref，暴露给 UI 层
- 聊天页面底部输入框上方根据 `groupChatReconnectStatus` 显示不同状态：
  - `connected`：绿色圆点 + "已连接"
  - `reconnecting`：黄色圆点 + "连接中断，正在重连..."
  - `disconnected`：红色圆点 + "连接已断开"
- 重连超过 5 次后弹出 ElMessage 错误提示："WebSocket 连接失败，请检查网络后刷新页面"

**V20 修订：认证方式安全说明**

| 安全维度 | V19 方案 | V20 方案 |
|----------|---------|---------|
| URL 暴露 | URL 纯净，无 token | URL 纯净，无 token |
| 浏览器历史 | 无 URL 参数，不记录 | 无 URL 参数，不记录 |
| 服务端日志 | 后端对 /ws 端点禁用 access log | 后端对 WS 端点禁用 access log |
| 代理日志 | WebSocket 升级请求无 token | WebSocket 升级请求无 token |
| token 类型 | ws_token（专用短时效令牌） | access_token（与 HTTP API 共享） |
| 响应类型 | auth_ok / auth_fail | auth_success / auth_error（与后端 V37 一致） |
| 连接数量 | 单连接 | 三个独立连接（与后端 V37 一致） |

### 6.4 流式输出处理

V10 将 V9 的 SSE 流式输出迁移至 WebSocket，处理方式如下：

```typescript
// ChatView.vue 中绑定 WebSocket 事件
const ws = useWebSocket();
const chatStore = useChatStore();

onMounted(() => {
  ws.connectGroup(groupId);

  ws.onGroup('stream.chunk', (data) => {
    chatStore.handleStreamChunk(data.message_id, data.content);
  });

  ws.onGroup('stream.done', (data) => {
    chatStore.handleStreamDone(data.message_id, data.full_content);
  });

  ws.onGroup('stream.error', (data) => {
    ElMessage.error('Agent 回复生成失败');
    chatStore.clearStreamingContent(data.message_id);
  });

  ws.onGroup('message.new', (data) => {
    chatStore.messages.push(data.message);
  });
});

onUnmounted(() => {
  ws.disconnectGroup();
});
```

**打字机效果渲染方案：**

流式输出采用 `requestAnimationFrame` 节流渲染，避免高频 DOM 更新导致页面卡顿：

```typescript
// composables/useStreamRender.ts
export function useStreamRender() {
  const displayContent = ref('');
  const pendingContent = ref('');
  let rafId: number | null = null;
  let lastRenderTime = 0;
  const renderInterval = 16; // ~60fps，约 16ms 一帧

  const appendChunk = (chunk: string) => {
    pendingContent.value += chunk;
    scheduleRender();
  };

  const scheduleRender = () => {
    if (rafId !== null) return;
    rafId = requestAnimationFrame(() => {
      const now = performance.now();
      if (now - lastRenderTime >= renderInterval) {
        displayContent.value += pendingContent.value;
        pendingContent.value = '';
        lastRenderTime = now;
      } else {
        scheduleRender();
        rafId = null;
        return;
      }
      rafId = null;
    });
  };

  const finalize = () => {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    displayContent.value += pendingContent.value;
    pendingContent.value = '';
  };

  onBeforeUnmount(() => {
    if (rafId !== null) cancelAnimationFrame(rafId);
  });

  return { displayContent, appendChunk, finalize };
}
```

**打字机效果实现原理：**

1. WebSocket 推送 `stream.chunk` 事件时，内容追加到 `pendingContent`（不直接更新 DOM）
2. 调用 `scheduleRender()` 请求下一帧渲染
3. `requestAnimationFrame` 回调中检查距离上次渲染是否超过 16ms，是则将 `pendingContent` 合并到 `displayContent`（触发 Vue 响应式更新，更新 DOM）
4. 流式输出结束时（`stream.done`），调用 `finalize()` 确保剩余内容全部渲染
5. 好处：WebSocket 每秒可能推送数十个 chunk，但 DOM 更新频率控制在 60fps 以内，避免不必要的重排重绘

**多 Agent 同时回复场景：**

讨论群中若多个 Agent 同时回复用户，每个回复拥有独立的 messageId，WebSocket 按消息事件独立推送：

```
用户发送消息 "请分析需求"
  -> Agent A 开始回复 (messageId: msg-001)
     WebSocket 推送 stream.chunk { message_id: "msg-001", content: "..." }
  -> Agent B 开始回复 (messageId: msg-002)
     WebSocket 推送 stream.chunk { message_id: "msg-002", content: "..." }
  -> 前端按 message_id 区分不同 Agent 的流式内容，互不干扰
  -> Agent A 回复完成 -> WebSocket 推送 stream.done { message_id: "msg-001" }
  -> Agent B 回复完成 -> WebSocket 推送 stream.done { message_id: "msg-002" }
```

---

## 7. 路由设计

### 7.1 路由配置

```typescript
// src/router/index.ts
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
      },
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/ProjectListView.vue'),
      },
      {
        path: 'projects/:id',
        component: () => import('@/views/ProjectDetailView.vue'),
        children: [
          {
            path: '',
            name: 'ProjectDetail',
            component: () => import('@/views/ProjectDetailView/OverviewTab.vue'),
          },
          {
            path: 'docs',
            name: 'Docs',
            component: () => import('@/views/DocsView.vue'),
          },
          {
            path: 'tasks',
            name: 'TaskBoard',
            component: () => import('@/views/TaskView.vue'),
          },
          {
            path: 'chat',
            name: 'Chat',
            component: () => import('@/views/ChatView.vue'),
            meta: { layout: 'chat' },
          },
          {
            path: 'qa',
            name: 'QA',
            component: () => import('@/views/QAView.vue'),
          },
          {
            path: 'repo',
            name: 'Repo',
            component: () => import('@/views/RepoView.vue'),
          },
        ],
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
      },
    ],
  },
  // 404 兜底路由
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    return { top: 0 };
  },
});
```

**V20 修订：新增 /projects/:id/docs 路由**

对齐架构 V24 §3.4 定义的文档管理接口，新增文档管理页面路由。

**路由懒加载策略：**

- 所有页面组件均采用 `() => import()` 动态导入
- Vite 构建时自动按路由分割代码包（chunk）
- 大体积库（ECharts 按需加载模块、md-editor-v3）也会被单独拆分
- views 目录下 10 个页面视图全部使用懒加载，确保首屏只加载 Dashboard 相关代码

**代码分割策略：**

```typescript
// vite.config.ts 中配置手动 chunk 分割
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-element': ['element-plus'],
          'vendor-echarts': ['@echarts/core'],  // V12 变更：按需加载后体积减小
          'vendor-editor': ['@tiptap/vue-3', 'md-editor-v3'],
        },
      },
    },
  },
});
```

**打包体积优化目标：**

| V14 目标 | V15 修订 | 说明 |
|----------|---------|------|
| vendor-vue chunk < 50KB (gzip) | 不变 | |
| vendor-element chunk < 100KB (gzip) | 不变 | 按需引入后 |
| vendor-echarts chunk < 100KB (gzip) | 不变 | V12 变更：按需加载后从 200KB 降至约 100KB |
| 首页首屏 JS 总体积 < 150KB (gzip) | **调整为 < 200KB (gzip)** | V15 修订：首屏使用的 Element Plus 组件（el-header、el-aside、el-menu、el-card 等）加上 Vue 生态依赖，实际首屏 JS 体积可能在 120-200KB gzip 之间，150KB 预算偏乐观。建议构建后通过 rollup-plugin-visualizer 验证实际体积 |

**路由元信息（meta）说明：**

| meta 字段 | 类型 | 说明 | 使用场景 |
|-----------|------|------|---------|
| requiresAuth | boolean | 是否需要认证 | 路由守卫判断是否放行 |
| layout | string | 布局类型 | 'default'（默认）或 'chat'（聊天布局） |
| title | string | 页面标题 | afterEach 中更新 document.title |

### 7.2 路由守卫

```typescript
// src/router/guards.ts
import router from './index';
import { useUserStore } from '@/stores/userStore';

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore();

  // 1. 不需要认证的路由（如登录页），直接放行
  if (to.meta.requiresAuth === false) {
    // 已登录用户访问登录页，重定向到仪表板
    if (to.name === 'Login' && userStore.accessToken) {
      next({ name: 'Dashboard' });
      return;
    }
    next();
    return;
  }

  // 2. 需要认证的路由：检查 token 是否存在
  if (!userStore.accessToken) {
    // 未登录，重定向到登录页，并保留目标路径用于登录后跳转
    next({ name: 'Login', query: { redirect: to.fullPath } });
    return;
  }

  // 3. Token 存在但可能过期：检查是否需要刷新
  if (userStore.tokenExpiry && Date.now() >= userStore.tokenExpiry - 60000) {
    const refreshed = await userStore.refreshToken();
    if (!refreshed) {
      // 刷新失败，跳转登录页
      next({ name: 'Login', query: { redirect: to.fullPath } });
      return;
    }
  }

  // 4. 认证通过，放行
  next();
});

// 登录后页面标题更新
router.afterEach((to) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - DevFlow`;
  }
});
```

**V12 补充：路由守卫完整逻辑**

| 场景 | 守卫行为 | 说明 |
|------|---------|------|
| 未登录访问 /dashboard | 重定向到 /login?redirect=/dashboard | 保留目标路径 |
| 已登录访问 /login | 重定向到 /dashboard | 避免重复登录 |
| Token 即将过期（< 60s） | 自动刷新 token 后再放行 | 无感刷新 |
| Token 刷新失败 | 重定向到 /login | 清除状态 |
| 访问不存在的路由 | Vue Router 404 处理 | catch-all 路由 `/:pathMatch(.*)*` |
| 登录成功后 | 根据 redirect query 跳转到原目标页面 | LoginView 中处理 |

**登录成功后跳转逻辑：**

```typescript
// LoginView.vue 中
onMounted(() => {
  const redirect = route.query.redirect as string;
  // 登录成功后
  const goTo = redirect && redirect !== '/login' ? redirect : '/dashboard';
  router.push(goTo);
});
```

**V14 补充：路由守卫执行流程图**

```
用户请求导航到目标路由
    |
    v
router.beforeEach 拦截
    |
    v
to.meta.requiresAuth === false ?
    |-- 是 --> 已是登录页且已登录? --> 是 --> 重定向 /dashboard
    |                                    |-- 否 --> 直接放行 next()
    |
    |-- 否 --> userStore.accessToken 存在?
                |-- 否 --> 重定向 /login?redirect=<目标路径>
                |
                |-- 是 --> tokenExpiry 将在 60s 内到期?
                            |-- 是 --> 调用 refreshToken()
                                        |-- 成功 --> 放行 next()
                                        |-- 失败 --> 重定向 /login
                            |
                            |-- 否 --> 直接放行 next()
```

---

## 8. 国际化设计

### 8.1 语言包结构

```json
// src/i18n/zh-CN.json
{
  "common": {
    "save": "保存",
    "cancel": "取消",
    "delete": "删除",
    "confirm": "确认",
    "loading": "加载中...",
    "noData": "暂无数据"
  },
  "project": {
    "create": "创建项目",
    "name": "项目名称",
    "description": "项目描述",
    "status": {
      "active": "进行中",
      "completed": "已完成",
      "paused": "已暂停"
    }
  },
  "task": {
    "columns": {
      "todo": "待处理",
      "in_progress": "进行中",
      "pending_review": "待检验",
      "completed": "已完成",
      "rejected": "已退回"
    }
  },
  "chat": {
    "send": "发送",
    "typing": "正在输入...",
    "streaming": "正在生成回复..."
  }
}
```

### 8.2 i18n 配置

```typescript
// src/i18n/index.ts
import { createI18n } from 'vue-i18n';
import zhCN from './zh-CN.json';
import enUS from './en-US.json';

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'en-US',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
});
```

**V15 修订：Element Plus 国际化切换方案修复**

V14 中 `setLocale` 函数使用 `app.config.globalProperties.$locale = lang` 试图切换 Element Plus 语言包，这是无效实现。Element Plus 需要通过 `ElConfigProvider` 组件的 `locale` prop 切换语言。V15 改为在根组件 `App.vue` 中使用 `ElConfigProvider` 包裹整个应用，通过响应式的 locale 实现语言切换。

**语言切换完整流程：**

1. 用户在 AppHeader 点击语言切换按钮
2. 调用 `useSettingStore().language = 'en-US'`
3. `pinia-plugin-persistedstate` 自动持久化到 localStorage
4. 调用 `i18n.global.locale.value = 'en-US'`
5. Vue 响应式更新，所有 `$t()` 调用自动重新渲染为新语言
6. Element Plus 组件内置文本（如分页器、日期选择器）通过 ElConfigProvider 同步切换

**App.vue 中使用 ElConfigProvider：**

```vue
<!-- App.vue -->
<template>
  <ElConfigProvider :locale="elementLocale">
    <RouterView />
  </ElConfigProvider>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ElConfigProvider } from 'element-plus';
import { zhCN, enUS } from 'element-plus/es/locale/index';
import { useSettingStore } from '@/stores/settingStore';

const settingStore = useSettingStore();

// 根据 settingStore.language 响应式切换 Element Plus 语言包
const elementLocale = computed(() => {
  return settingStore.language === 'zh-CN' ? zhCN : enUS;
});
</script>
```

**语言切换工具函数：**

```typescript
// src/composables/useLocale.ts
import { useI18n } from 'vue-i18n';
import { useSettingStore } from '@/stores/settingStore';

export function useLocale() {
  const { locale } = useI18n();
  const settingStore = useSettingStore();

  const setLocale = (lang: 'zh-CN' | 'en-US') => {
    // 1. 更新 vue-i18n 语言
    locale.value = lang;
    // 2. 持久化到 settingStore（ElConfigProvider 会自动跟随 settingStore.language 切换）
    settingStore.language = lang;
    // 3. 更新 <html> 的 lang 属性（无障碍需求）
    document.documentElement.lang = lang;
  };

  return { setLocale };
}
```

**Element Plus 语言切换原理说明：**

| 方案 | 是否有效 | 说明 |
|------|---------|------|
| V14: `app.config.globalProperties.$locale = lang` | **无效** | Element Plus 不读取此属性 |
| V15: `ElConfigProvider` 的 `locale` prop | **有效** | Element Plus 官方推荐方案，通过 Provide/Inject 向下传递语言包 |
| `createApp().use(ElementPlus, { locale })` | 有效但不推荐 | 仅能在应用初始化时设置一次，不支持运行时切换 |

**ElConfigProvider 优势：**

- 支持运行时切换：通过响应式的 `locale` prop，语言切换时 Element Plus 所有组件自动更新内置文本
- 作用域精确：包裹在 `App.vue` 根组件中，覆盖整个应用
- 无需重新创建 Vue 应用实例

---

## 9. 样式设计

### 9.1 主题变量（CSS 变量方案）

V10 采用 CSS 自定义属性（CSS Variables）实现主题切换，替代 V9 的 SCSS 变量方案。优势在于支持运行时切换，无需重新编译。

```scss
// src/assets/styles/variables.scss

// 浅色主题（默认）
:root {
  --color-primary: #409eff;
  --color-success: #67c23a;
  --color-warning: #e6a23c;
  --color-danger: #f56c6c;
  --color-info: #909399;

  --bg-color: #f5f7fa;
  --card-bg: #ffffff;
  --text-primary: #303133;
  --text-secondary: #606266;
  --text-muted: #909399;

  --border-color: #dcdfe6;
  --border-radius: 8px;

  --sidebar-width: 240px;
  --sidebar-collapsed-width: 64px;
  --header-height: 56px;
}

// 深色主题
html.dark {
  --bg-color: #141414;
  --card-bg: #1d1e1f;
  --text-primary: #e5eaf3;
  --text-secondary: #c0c4cc;
  --text-muted: #909399;
  --border-color: #2d2d2d;
}
```

### 9.2 暗黑模式切换机制

```typescript
// composables/useTheme.ts
import { useSettingStore } from '@/stores/settingStore';

export function useTheme() {
  const settingStore = useSettingStore();

  const setTheme = (theme: 'light' | 'dark') => {
    settingStore.theme = theme;
    applyTheme(theme);
  };

  const applyTheme = (theme: 'light' | 'dark') => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  onMounted(() => {
    if (settingStore.theme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  });

  return { setTheme };
}
```

**暗黑模式切换完整流程：**

1. 用户在系统设置页（SettingsView）选择浅色/深色主题
2. SettingsView 调用 `useTheme().setTheme('dark')`
3. `setTheme` 内部执行：
   a. `settingStore.theme = theme` 更新状态
   b. `pinia-plugin-persistedstate` 自动将 settingStore 持久化到 localStorage
   c. `applyTheme(theme)` 给 `<html>` 元素添加/移除 `dark` class
4. CSS 变量切换：`html.dark` 选择器覆盖 `:root` 中的变量值，页面即时变暗
5. Element Plus 组件库：
   - Element Plus 2.x 内置支持暗黑模式
   - 检测到 `<html>` 上有 `dark` class 时，自动切换为深色主题样式
   - 无需额外配置，按需引入的组件样式同样跟随切换
6. 自定义组件：使用 `var(--bg-color)`、`var(--text-primary)` 等 CSS 变量，自动跟随切换
7. 页面刷新后：`pinia-plugin-persistedstate` 从 localStorage 恢复 settingStore，`onMounted` 中检查 `theme` 并应用 `dark` class

**settingStore 与暗黑模式的关系：**

| 环节 | 负责方 | 说明 |
|------|--------|------|
| 主题状态存储 | settingStore | `theme: 'light' \| 'dark'` 字段 |
| 主题持久化 | pinia-plugin-persistedstate | 自动将 settingStore 序列化到 localStorage |
| CSS class 切换 | useTheme composable | 给 `<html>` 添加/移除 `dark` 类 |
| Element Plus 跟随 | Element Plus 内置 | 检测 `html.dark` class 自动切换 |
| 自定义组件跟随 | CSS 变量 | 使用 `var(--xxx)` 引用 CSS 变量 |

### 9.3 Element Plus 样式按需引入方案

V10 明确 Element Plus 样式按需引入的完整方案：

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import AutoImport from 'unplugin-auto-import/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';

export default defineConfig({
  plugins: [
    vue(),
    Components({
      dts: 'src/types/components.d.ts',
      resolvers: [
        ElementPlusResolver({
          importStyle: 'css',
        }),
      ],
    }),
    AutoImport({
      dts: 'src/types/auto-imports.d.ts',
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [
        ElementPlusResolver(),
      ],
    }),
  ],
  // ... 其他配置
});
```

**按需引入效果：**

- 仅引入实际使用的组件 JS 代码
- 仅引入实际使用的组件 CSS 样式（非全量 el-theme.css）
- 自动生成类型声明文件（components.d.ts / auto-imports.d.ts）
- 减少打包体积约 60-80%（相比全量引入）

### 9.4 响应式断点与移动端适配

```scss
$breakpoint-sm: 576px;   // 手机
$breakpoint-md: 768px;   // 平板
$breakpoint-lg: 992px;   // 小屏桌面
$breakpoint-xl: 1200px;  // 大屏桌面
```

**移动端适配策略：**

| 断点 | 布局方案 | 说明 |
|------|---------|------|
| < 768px (sm) | 单栏布局，侧边栏隐藏 | 侧边栏改为抽屉模式（el-drawer），汉堡菜单按钮触发 |
| 768px - 991px (md) | 单栏布局，侧边栏折叠 | 侧边栏折叠为图标模式（64px 宽） |
| 992px - 1199px (lg) | 双栏布局 | 正常侧边栏 + 内容区 |
| >= 1200px (xl) | 双栏布局 | 正常侧边栏 + 内容区 |

```scss
@mixin respond-to($breakpoint) {
  @if $breakpoint == sm {
    @media (max-width: 576px) { @content; }
  } @else if $breakpoint == md {
    @media (max-width: 768px) { @content; }
  } @else if $breakpoint == lg {
    @media (max-width: 992px) { @content; }
  } @else if $breakpoint == xl {
    @media (max-width: 1200px) { @content; }
  }
}

.sidebar {
  width: var(--sidebar-width);
  @include respond-to(md) {
    position: fixed;
    left: -240px;
    z-index: 1000;
    transition: left 0.3s;
    &.open { left: 0; }
  }
}
```

**移动端具体适配：**

- 登录页：表单宽度 100%，居中显示
- 项目列表：卡片改为单列堆叠
- 任务看板：改为垂直列表模式（非看板列布局）
- 聊天页：全屏聊天，群列表改为顶部横向滚动
- 代码仓库：列表纵向排列，折叠次要信息

---

## 10. 无障碍设计（WCAG 2.1 AA）

### 10.1 键盘导航

- 所有交互元素可通过 Tab 键访问
- 焦点样式清晰可见（2:1 对比度），使用 `:focus-visible` 伪类
- 跳过导航链接（Skip to main content），在 AppHeader 首元素放置隐藏链接

```vue
<!-- AppHeader.vue -->
<template>
  <a href="#main-content" class="skip-link">跳转到主要内容</a>
  <!-- 其他导航内容 -->
</template>

<style>
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--color-primary);
  color: #fff;
  padding: 8px 16px;
  z-index: 9999;
  transition: top 0.2s;
  &:focus {
    top: 0;
  }
}
</style>
```

### 10.2 屏幕阅读器支持

- 所有装饰性图片设置 `alt=""`，有意义图片设置描述性 `alt` 文本
- 图标按钮包含 `aria-label` 属性
- 动态内容更新使用 `aria-live` 区域：
  - 聊天消息更新：`aria-live="polite"`（非紧急更新）
  - 通知到达：`aria-live="assertive"`（紧急通知）
  - Agent 状态变更：`aria-live="polite"`

```vue
<!-- MessageList.vue -->
<template>
  <div role="log" aria-live="polite" aria-relevant="additions" id="message-list">
    <!-- 消息列表 -->
  </div>
</template>
```

### 10.3 色彩对比度

- 正文文本对比度 >= 4.5:1
- 大文本（>=18px 或 >=14px 加粗）对比度 >= 3:1
- 不单独依赖颜色传达信息（状态标签同时使用颜色和文字）
- 焦点指示器对比度 >= 3:1

### 10.4 表单无障碍

- 所有输入框关联 `<label>` 元素（使用 `for` / `id` 关联或包裹方式）
- 错误提示使用 `aria-describedby` 关联输入框
- 必填字段使用 `aria-required="true"` 和 `aria-invalid="true"`
- 错误消息使用 `role="alert"`

```vue
<template>
  <el-form-item label="项目名称" required>
    <el-input
      v-model="form.name"
      aria-required="true"
      :aria-invalid="!!errors.name"
      aria-describedby="name-error"
    />
    <span v-if="errors.name" id="name-error" role="alert" class="error-text">
      {{ errors.name }}
    </span>
  </el-form-item>
</template>
```

### 10.5 焦点管理

- 弹窗打开时焦点自动移至弹窗内第一个交互元素
- 弹窗关闭时焦点恢复到打开前的元素
- 路由切换时焦点移至新页面主内容区
- 使用 `aria-modal="true"` 标记模态弹窗

### 10.6 V14 补充：无障碍实现检查清单

为确保 WCAG 2.1 AA 合规性，以下检查项需要在开发过程中逐项落实：

| 检查项 | 标准 | 实现方式 | 验证方法 |
|--------|------|---------|---------|
| 页面标题 | 每个页面有唯一 title | router.afterEach 中更新 document.title | 手动检查 + Playwright E2E 断言 |
| 语言属性 | `<html lang="zh-CN">` | 根据 settingStore.language 动态设置 | `document.documentElement.lang` |
| 语义化标签 | 使用 heading、nav、main、section 等 | DefaultLayout 中使用 `<main id="main-content">` | axe-core 自动检测 |
| 图片 alt 文本 | 所有 img 有 alt 属性 | 组件模板中强制要求 alt | ESLint 规则 + axe-core |
| 表单标签 | 所有 input 有关联 label | Element Plus el-form-item 自动生成 label | axe-core 自动检测 |
| 键盘可访问 | Tab 可访问所有交互元素 | 自定义组件使用 button/a 标签而非 div | 手动 Tab 遍历测试 |
| 焦点可见性 | :focus-visible 样式 | global.scss 中定义全局焦点样式 | 手动 Tab 测试 |
| 色彩对比度 | 文本 >= 4.5:1 | CSS 变量定义确保对比度达标 | axe-core / Lighthouse 审计 |
| aria-live 区域 | 动态内容有 aria-live | 消息列表、通知区域设置 aria-live | 屏幕阅读器测试 |
| 跳过导航 | 首元素为 skip link | AppHeader 中放置 .skip-link | 手动 Tab 测试 |

**无障碍测试工具：**

| 工具 | 类型 | 用途 |
|------|------|------|
| axe-core | 自动化 | 集成到 Playwright E2E 测试中，自动检测 WCAG 违规项 |
| Lighthouse | 自动化 | 每次构建后运行 Lighthouse CI，检查无障碍得分 |
| NVDA / VoiceOver | 手动 | 屏幕阅读器实际体验测试 |
| 键盘手动测试 | 手动 | Tab 键遍历所有交互元素，验证焦点顺序 |

---

## 11. 多环境配置

### 11.1 环境变量文件

```
# .env（通用，所有环境共享）
VITE_APP_NAME=DevFlow

# .env.development（开发环境）
VITE_API_BASE_URL=http://localhost:8080/api
VITE_WS_HOST=localhost:8080
VITE_ENABLE_MOCK=true

# .env.production（生产环境）
VITE_API_BASE_URL=/api
VITE_WS_HOST=
VITE_ENABLE_MOCK=false
```

### 11.2 环境变量使用说明

- 仅 `VITE_` 前缀的变量会注入客户端代码
- 敏感信息（如 API Key）不得放入客户端环境变量
- 开发环境使用绝对 URL 方便跨域调试
- 生产环境使用相对路径，由 Nginx 反向代理处理

### 11.3 构建命令

```bash
# 开发环境
npm run dev          # 读取 .env + .env.development

# 生产环境构建
npm run build        # 读取 .env + .env.production

# 预览构建产物
npm run preview
```

---

## 12. 安全设计

### 12.1 XSS 防护

**Vue 默认防护：**

- Vue 模板渲染默认转义 HTML，`{{ variable }}` 不会执行注入脚本
- `v-html` 使用时需特别注意，仅用于可信内容（如后端已过滤的 Markdown 渲染结果）

**富文本编辑器防护：**

- @tiptap 编辑器输出 HTML 需经过 sanitize 处理
- 使用 `dompurify` 库过滤危险标签和属性

```typescript
// src/utils/sanitize.ts
import DOMPurify from 'dompurify';

export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'u', 's', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'hr', 'table',
      'thead', 'tbody', 'tr', 'th', 'td', 'img',
    ],
    ALLOWED_ATTR: [
      'href', 'title', 'alt', 'src', 'width', 'height', 'target', 'rel',
    ],
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel):|[^a-z]|[a-z+.\\-]+(?:[^a-z+.\\-:]|$))/i,
  });
}
```

**V12 明确：sanitization 在渲染管线中的位置**

对于 Markdown 内容（md-editor-v3 渲染 Agent 产出内容），sanitization 必须在 Markdown 转为 HTML 之后进行，而非之前。具体渲染管线如下：

```
Agent 产出的 Markdown 原始文本
    |
    v
Markdown 解析器（如 marked / md-editor-v3 内置解析器）
    |
    v
生成的 HTML 字符串（可能包含 <script>、onerror 等危险内容）
    |
    v
sanitizeHtml() — 在此阶段过滤危险 HTML
    |
    v
安全的 HTML 字符串
    |
    v
v-html 渲染到 DOM
```

**错误做法（在 Markdown 解析之前 sanitize）：**

```
Agent Markdown 文本 -> sanitizeHtml() -> Markdown 解析器 -> v-html
```

这种方式的缺陷：sanitizeHtml 会移除 Markdown 语法中的 `<` 和 `>` 符号（如 `<script>` 会被当作 HTML 标签处理），导致 Markdown 代码块、行内代码等内容被破坏。

**正确做法（在 Markdown 解析之后 sanitize）：**

```vue
<!-- ProjectDetailView 中的文档预览区域 -->
<template>
  <div v-html="sanitizedContent" class="md-preview" />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { sanitizeHtml } from '@/utils/sanitize';
import { marked } from 'marked'; // Markdown -> HTML 解析器

const docContent = ref(''); // Agent 产出的 Markdown 原始内容

// 渲染管线：Markdown -> HTML -> sanitize -> v-html
const sanitizedContent = computed(() => {
  const html = marked.parse(docContent.value, { async: false }) as string;
  return sanitizeHtml(html);
});
</script>
```

**XSS 过滤的具体防护对象：**

| 危险注入类型 | 示例 | 过滤方式 |
|-------------|------|---------|
| `<script>` 标签 | `<script>alert(1)</script>` | DOMPurify 默认移除，不在 ALLOWED_TAGS 中 |
| 事件属性注入 | `<img onerror="alert(1)" src=x>` | DOMPurify 默认移除 `on*` 属性，不在 ALLOWED_ATTR 中 |
| `javascript:` URI | `<a href="javascript:alert(1)">点击</a>` | ALLOWED_URI_REGEXP 正则过滤，只允许 http/https/mailto/tel 协议 |
| `<iframe>` 注入 | `<iframe src="...">` | 不在 ALLOWED_TAGS 中，被移除 |
| `<object>` / `<embed>` | `<object data="...">` | 不在 ALLOWED_TAGS 中，被移除 |
| `data:` URI 滥用 | `<img src="data:text/html,<script>...">` | ALLOWED_URI_REGEXP 限制协议类型 |

**使用场景汇总：**

| 组件 | 渲染内容来源 | 是否经过 sanitize | 渲染管线 |
|------|------------|-----------------|---------|
| MessageBubble | Agent 消息（富文本） | 是 | 原始 Markdown -> marked.parse -> sanitizeHtml -> v-html |
| ProjectDetailView 文档预览 | Agent 产出的 Markdown 文档 | 是 | 原始 Markdown -> marked.parse -> sanitizeHtml -> v-html |
| MessageInput 发送的消息 | 用户输入（@tiptap 编辑器） | 是 | @tiptap 输出 HTML -> sanitizeHtml -> 提交后端 |
| DashboardView 动态数据 | 后端 API 返回 | 否（Vue 默认转义） | `{{ }}` 插值，Vue 自动转义 |

### 12.2 CSP（内容安全策略）

**V15 修订：使用 nonce 替代 unsafe-inline**

V14 中 CSP 的 `script-src` 和 `style-src` 使用了 `unsafe-inline`，V15 改为 nonce 方式。Vite 支持在 `index.html` 中注入 nonce 到内联脚本，将 `unsafe-inline` 替换为 `'nonce-{{nonce}}'`，显著提升 XSS 防护能力。

**Nginx CSP Header 配置（V15 修订）：**

```nginx
# V15 修订：使用 nonce 替代 unsafe-inline
# nonce 由后端动态生成（每次请求不同），此处以变量形式展示
add_header Content-Security-Policy "default-src 'self'; \
  script-src 'self' 'nonce-$csp_nonce'; \
  style-src 'self' 'nonce-$csp_nonce' 'unsafe-hashed-attributes'; \
  img-src 'self' data: https:; \
  font-src 'self'; \
  connect-src 'self' ws: wss:; \
  frame-src 'none'; \
  object-src 'none';";
```

**Vite 中 nonce 注入方案：**

```html
<!-- index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <!-- Vite 会自动将 nonce 注入到内联脚本中 -->
  <script type="module" nonce="{{NONCE}}">
    // Vite 客户端 HMR 代码
  </script>
</head>
<body>
  <div id="app"></div>
  <script type="module" nonce="{{NONCE}}" src="/src/main.ts"></script>
</body>
</html>
```

**nonce 工作流程：**

```
1. 后端生成随机 nonce（如 crypto.randomBytes(16).toString('base64)）
2. 后端将 nonce 同时写入：
   a. CSP Header 的 script-src / style-src 指令中
   b. HTML 响应体中内联 <script> 和 <style> 标签的 nonce 属性
3. 浏览器加载页面时：
   a. 读取 CSP Header 中允许的 nonce 值
   b. 检查每个内联 <script nonce="xxx"> 的 nonce 是否匹配
   c. 匹配的允许执行，不匹配的拒绝执行
4. 每次请求 nonce 值不同，攻击者无法预测或复用
```

**CSP 策略说明（V15 修订）：**

| 指令 | V14 值 | V15 值 | 说明 |
|------|--------|--------|------|
| default-src | 'self' | 'self' | 默认只允许同源资源 |
| script-src | 'self' 'unsafe-inline' | 'self' 'nonce-$csp_nonce' | V15 修订：仅允许带有正确 nonce 的内联脚本 |
| style-src | 'self' 'unsafe-inline' | 'self' 'nonce-$csp_nonce' 'unsafe-hashed-attributes' | V15 修订：Vue 的 `:style` 绑定使用 `unsafe-hashed-attributes`（允许带 hash 的内联样式属性） |
| img-src | 'self' data: https: | 'self' data: https: | 允许站内图片、data URI、HTTPS 外部图片（头像等） |
| font-src | 'self' | 'self' | 仅允许同源字体 |
| connect-src | 'self' ws: wss: | 'self' ws: wss: | 允许同源 API 和 WebSocket 连接 |
| frame-src | 'none' | 'none' | 禁止 iframe |
| object-src | 'none' | 'none' | 禁止 object/embed 标签 |

**nonce 与 unsafe-inline 安全对比：**

| 对比项 | unsafe-inline | nonce |
|--------|--------------|-------|
| 内联脚本执行 | 所有内联脚本均可执行 | 仅带有匹配 nonce 的内联脚本可执行 |
| XSS 攻击注入的脚本 | 可执行（不安全） | 无法执行（攻击者无法获取 nonce） |
| nonce 可预测性 | 不适用 | 每次请求随机生成，不可预测 |
| 实现复杂度 | 简单 | 需要后端配合生成和注入 nonce |
| 兼容性 | 所有浏览器 | 所有现代浏览器 |

**`unsafe-hashed-attributes` 说明：**

Vue 3 使用 `:style` 绑定生成内联 `style` 属性（如 `<div style="color: red">`），nonce 无法覆盖属性级别的内联样式。`unsafe-hashed-attributes` 允许通过 SHA-256 hash 白名单放行特定的内联样式属性，比 `unsafe-inline` 更安全。

### 12.3 CSRF 防护

- 采用 Bearer Token 认证方案，无状态 Token 天然免疫 CSRF（不依赖 Cookie）
- Token 存储在 localStorage 中，由 JS 手动附加到请求 Header 中
- `withCredentials: false`，确保不会自动发送 Cookie
- 额外防护：后端可设置 `SameSite=Strict` 的 Session Cookie（如有）

```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

---

## 13. 测试设计

### 13.1 测试框架选型

| 类别 | 选型 | 说明 |
|------|------|------|
| 单元测试 | Vitest 2.x | 与 Vite 生态一致、原生 ESM、启动速度快 |
| 组件测试 | @vue/test-utils 2.x | Vue 官方组件测试库 |
| E2E 测试 | Playwright 1.x | 跨浏览器、Vue 官方推荐、支持可视化 |

### 13.2 Vitest 配置

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        branches: 80,
        functions: 80,
        lines: 80,
        statements: 80,
      },
    },
  },
});
```

### 13.3 测试覆盖范围

| 测试类别 | 覆盖范围 | 最低覆盖率 |
|---------|---------|-----------|
| 组件测试 | 所有通用组件（components/） | 80% |
| Composable 测试 | useWebSocket、useAuth 等 | 80% |
| Store 测试 | 所有 Pinia store actions | 80% |
| 工具函数测试 | utils/ 下所有函数 | 90% |
| E2E 测试 | 核心用户流程（登录、创建项目、发送消息） | 关键路径 100% |

### 13.4 测试示例

```typescript
// tests/unit/stores/userStore.test.ts
import { describe, it, expect, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useUserStore } from '@/stores/userStore';

describe('userStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should login successfully', async () => {
    const store = useUserStore();
    await store.login('test', 'password');
    expect(store.accessToken).toBe('test-token');
    expect(store.user).toEqual({ id: '1', username: 'test' });
  });

  it('should logout and clear state', () => {
    const store = useUserStore();
    store.logout();
    expect(store.user).toBeNull();
    expect(store.accessToken).toBeNull();
  });
});
```

### 13.5 Playwright E2E 配置

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: true,
  },
});
```

---

## 14. 构建与部署

### 14.1 Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import AutoImport from 'unplugin-auto-import/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';

export default defineConfig({
  plugins: [
    vue(),
    Components({
      dts: 'src/types/components.d.ts',
      resolvers: [
        ElementPlusResolver({
          importStyle: 'css',
        }),
      ],
    }),
    AutoImport({
      dts: 'src/types/auto-imports.d.ts',
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [ElementPlusResolver()],
    }),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-element': ['element-plus'],
          'vendor-echarts': ['@echarts/core'],
          'vendor-editor': ['@tiptap/vue-3', 'md-editor-v3'],
        },
      },
    },
  },
});
```

### 14.2 Docker 部署

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### 14.3 Nginx 配置

```nginx
server {
    listen 80;
    server_name devflow.local;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    // V20 修订：WebSocket 多端点代理配置
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
    }

    # V15 修订：使用 nonce 的 CSP（nonce 由后端动态注入）
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'nonce-$csp_nonce'; style-src 'self' 'nonce-$csp_nonce' 'unsafe-hashed-attributes'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ws: wss:; frame-src 'none'; object-src 'none';";

    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
```

---

## 15. 性能优化设计

### 15.1 性能预算指标

| 指标 | V14 目标值 | V15 修订值 | 测量方法 |
|------|----------|----------|---------|
| 首屏 LCP (Largest Contentful Paint) | < 2.5s | < 2.5s | Lighthouse CI |
| 首屏 JS 总体积 (gzip) | < 150KB | **< 200KB** | Vite build + rollup-plugin-visualizer 验证 |
| 首屏 FCP (First Contentful Paint) | < 1.5s | < 1.5s | Lighthouse CI |
| 交互就绪时间 (TTI) | < 3s | < 3s | Lighthouse CI |
| 路由切换时间 | < 300ms | < 300ms | Performance API |
| 虚拟列表滚动帧率 | >= 55fps | >= 55fps | Chrome DevTools |
| 内存占用峰值 | < 200MB | < 200MB | Chrome DevTools Memory |

**V15 修订说明：首屏 JS 体积预算调整为 200KB gzip**

即使按需引入，Element Plus 首屏使用的组件（el-header、el-aside、el-menu、el-card 等）加上 Vue 生态依赖（vue、vue-router、pinia），实际首屏 JS 体积可能在 120-200KB gzip 之间。V14 的 150KB 预算偏乐观，V15 调整为 200KB 更贴合实际。建议在构建后通过 `rollup-plugin-visualizer` 工具验证实际体积：

```bash
# 安装可视化分析工具
npm install -D rollup-plugin-visualizer

# 构建并生成分析报告
npx vite build --mode production
# 打开 dist/stats.html 查看各 chunk 体积分布
```

### 15.2 性能优化措施

**路由懒加载：**

- 所有 10 个页面视图使用 `() => import()` 动态导入
- 首屏仅加载 Dashboard 相关代码，其余页面按需加载

**代码分割（manualChunks）：**

- vendor-vue：vue + vue-router + pinia（< 50KB gzip）
- vendor-element：按需引入的 Element Plus 组件（< 100KB gzip）
- vendor-echarts：@echarts/core 按需模块（< 100KB gzip）
- vendor-editor：@tiptap/vue-3 + md-editor-v3

**虚拟滚动：**

- 消息列表、提交列表使用 @tanstack/vue-virtual 虚拟滚动
- 仅渲染可视区域 DOM 节点，避免数千条 DOM 导致卡顿

**组件级优化：**

- 大列表组件使用 `v-memo`（Vue 3.2+）缓存不变更的子树
- 计算属性（computed）缓存派生数据，避免重复计算
- 图片懒加载（IntersectionObserver），首屏外图片延迟加载

**ECharts 按需加载：**

- 使用 `@echarts/core` + 显式注册所需图表类型和组件
- 仅注册 RadarChart 和 LineChart（项目实际使用的图表）
- 全量 echarts ~400KB gzip，按需加载后 ~150-200KB gzip（减少约 50-60%）

### 15.3 V14 新增：浏览器缓存策略

**静态资源缓存：**

Nginx 对构建产物的静态资源设置长效缓存，配合内容哈希文件名实现缓存更新：

```nginx
# Nginx 静态资源缓存配置
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}

# HTML 文件不缓存（或使用短缓存）
location ~* \.html$ {
    expires -1;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

**缓存策略说明：**

| 资源类型 | 缓存策略 | 理由 |
|---------|---------|------|
| JS/CSS（带内容哈希） | max-age=1年 + immutable | Vite 构建后文件名包含内容哈希，内容变更则文件名变更，旧文件自动失效 |
| 图片/字体（带内容哈希） | max-age=1年 + immutable | 同上，文件名哈希保证缓存安全性 |
| index.html | no-cache | SPA 入口，需要每次都检查更新，确保获取最新的路由和 chunk 映射 |
| API 响应 | 由后端控制 Cache-Control | 前端不强制覆盖后端缓存头 |

**Vite 构建产物文件名示例：**

```
dist/
├── assets/
│   ├── index-a1b2c3d4.js          # 主应用代码（哈希基于内容）
│   ├── vendor-vue-e5f6g7h8.js     # Vue 生态依赖
│   ├── vendor-element-i9j0k1l2.js # Element Plus 组件
│   ├── DashboardView-m3n4o5p6.js  # 仪表板页面（路由 chunk）
│   ├── ChatView-q7r8s9t0.js       # 聊天页面（路由 chunk）
│   └── logo-u1v2w3x4.png          # 静态图片（哈希基于内容）
├── favicon.ico
└── index.html                      # 引用上述带哈希的文件名
```

**缓存更新流程：**

1. 用户首次访问 -> 下载 index.html（不缓存）+ 所有静态资源（缓存 1 年）
2. 用户再次访问 -> index.html 重新请求 -> 发现文件名未变 -> 浏览器使用缓存的静态资源
3. 前端发布新版本 -> index.html 更新 -> 引用新的哈希文件名 -> 浏览器下载新的静态资源 -> 旧文件因无人引用自然失效

### 15.4 加载状态设计

**SkeletonLoader 骨架屏：**

- 数据加载期间显示与目标布局一致的骨架屏占位
- 4 种变体：card（卡片）、list（列表）、table（表格）、text（文本）
- 数据加载完成后平滑过渡（CSS fade-out 动画，300ms）
- 深色主题下骨架屏颜色自动适配

**Loading 状态层次：**

| 层次 | 组件/方案 | 使用场景 |
|------|----------|---------|
| 页面级 | SkeletonLoader | 页面首次加载（Dashboard、项目列表等） |
| 组件级 | el-loading（Element Plus） | 局部数据刷新（任务看板拖拽后更新） |
| 按钮级 | el-button loading 状态 | 表单提交、创建操作 |
| 全局级 | el-message / el-notification | 操作成功/失败提示 |

---

## 16. V14 -> V15 修订记录（历史保留）

### 后荣检验意见与修订对照

| 编号 | 严重程度 | 后荣检验意见 | V15 修订内容 |
|------|----------|-------------|-------------|
| 1 | 严重 | WebSocket 通过 URL query 参数携带 token，暴露于浏览器历史/服务端日志/代理日志 | 6.3 节完全重写：(a) 新增 ws_token 专用短时效令牌（5 分钟），通过 POST /auth/ws-token 获取，与 access_token 分离；(b) WebSocket URL 不再携带 token，改为连接建立后发送 auth 消息认证；(c) Nginx 对 /ws 端点禁用 access_log；(d) userStore 新增 wsToken/wsTokenExpiry 字段和 ensureWsToken/fetchWsToken 方法 |
| 2 | 中等 | ErrorBoundary retry() 仅将 error.value 设为 false，onErrorCaptured 不会自动重新触发子组件渲染 | 3.1.5 节重写：在 slot 外层添加 `<div :key="retryKey">`，retry() 时自增 retryKey，Vue 卸载旧组件树并重新挂载，真正重新渲染子组件。补充重试机制原理说明表 |
| 3 | 中等 | `app.config.globalProperties.$locale = lang` 无法切换 Element Plus 语言包 | 8.2 节重写：改为在 App.vue 中使用 ElConfigProvider 组件包裹整个应用，通过响应式的 locale prop 切换 Element Plus 语言包。补充方案对比表（无效方案 vs 有效方案）和 ElConfigProvider 优势说明 |
| 4 | 轻微 | estimateSize 固定 80px，消息高度差异大 | 3.2.4 节补充：新增动态 measure 机制，MessageBubble 渲染完成后通过 @measured 事件上报实际高度，调用 rowVirtualizer.measureItem(index, actualHeight) 更新尺寸缓存。补充动态 measure 机制说明表 |
| 5 | 轻微 | script-src 和 style-src 使用 unsafe-inline | 12.2 节重写：改为 nonce 方案，Nginx CSP Header 使用 'nonce-$csp_nonce' 替代 'unsafe-inline'，style-src 补充 'unsafe-hashed-attributes' 支持 Vue 的 :style 绑定。补充 nonce 工作流程图和 nonce vs unsafe-inline 安全对比表 |
| 6 | 轻微 | 首屏体积预算 150KB gzip 偏乐观 | 7.1 节和 15.1 节修订：首屏 JS 总体积预算从 < 150KB 调整为 < 200KB gzip。补充 rollup-plugin-visualizer 验证方法和实际体积范围说明（120-200KB） |

### V15 新增内容清单

| 新增项 | 位置 | 说明 |
|--------|------|------|
| ws_token 字段 | 4.2 节 userStore | 短时效 WebSocket 专用令牌（5 分钟） |
| fetchWsToken / ensureWsToken 方法 | 4.2 节 userStore | 获取和验证 ws_token 的 store 方法 |
| ws_token 安全设计对比表 | 4.2 节 | access_token 与 ws_token 的用途、时效、传递方式、泄露风险对比 |
| POST /auth/ws-token 端点 | 5.2 节 | WebSocket 专用令牌获取接口 |
| auth / auth_success / auth_error 事件类型 | 6.2 节 | WebSocket 连接建立后的认证消息类型 |
| auth 事件通信流程图 | 6.2 节 | 客户端-服务端认证交互流程 |
| auth 事件安全优势对比表 | 6.2 节 | V14（query 参数）vs V15（auth 消息）的 6 维度对比 |
| useWebSocket 完整重写 | 6.3 节 | 移除 URL query token，改为 auth 消息认证，新增 authenticated 状态、authenticate() 方法、auth_success/auth_error 处理 |
| V15 认证流程变化表 | 6.3 节 | 6 步认证流程 V14 vs V15 对比 |
| V15 认证安全说明表 | 6.3 节 | 6 个安全维度的 V14 vs V15 对比 |
| /ws 端点 access_log off | 14.3 节 Nginx 配置 | 禁用 WebSocket 端点的访问日志 |
| ErrorBoundary :key 重试方案 | 3.1.5 节 | retryKey 强制重挂载方案 + 原理说明表 |
| ElConfigProvider 语言切换方案 | 8.2 节 | App.vue 中使用 ElConfigProvider + 方案对比表 |
| useLocale composable | 8.2 节 | 统一的语言切换工具函数 |
| 动态 measure 机制 | 3.2.4 节 | onMeasured 事件 + measureItem 调用 + 机制说明表 |
| nonce CSP 方案 | 12.2 节 | nonce 工作流程图 + 安全对比表 + unsafe-hashed-attributes 说明 |
| 首屏体积预算调整 | 7.1 节 + 15.1 节 | 150KB -> 200KB，补充 rollup-plugin-visualizer 验证方法 |

---

## 17. V13 -> V14 修订记录（历史保留）

### 后荣检验意见与修订对照

| 编号 | 严重程度 | 后荣检验意见 | V14 修订内容 |
|------|----------|-------------|-------------|
| 1 | 严重 | 文档在 1.4 节被截断不完整 | V14 文档完整无截断，所有章节内容完整，共计约 3100+ 行 |
| 2 | - | 缺少 WebSocket 详细设计（连接管理、消息路由、心跳机制、断线重连策略） | 第 6 章已包含完整 WebSocket 设计：6.1 连接复用和消息路由、6.2 事件类型和心跳机制、6.3 连接管理代码（含心跳定时器）、6.4 流式输出处理。V14 新增 heartbeat.ping/pong 事件类型和完整心跳代码实现 |
| 3 | - | 缺少状态管理详细设计（各 Store 的职责划分、状态持久化策略） | 第 4 章已包含完整状态管理设计：4.1 持久化策略、4.2-4.7 各 Store 详细定义。V14 为每个 Store 补充了明确的职责描述，新增 Store 职责总览表（数据来源、持久化、WebSocket 交互一览） |
| 4 | - | 缺少路由详细设计和路由守卫逻辑 | 第 7 章已包含完整路由设计：7.1 路由配置（含懒加载、代码分割、meta 说明）、7.2 路由守卫（含完整守卫逻辑和执行流程图）。V14 补充路由元信息说明表和守卫执行流程图 |
| 5 | - | 缺少 API 层设计（请求拦截、错误处理、认证 token 管理） | 第 5 章已包含完整 API 设计：5.1 基础配置（含 Axios 实例、分层架构表、模块层示例）、5.2 端点清单、5.3 错误处理（含全局异常捕获、ApiError 类型、重试策略）。V14 补充 API 分层架构表 |
| 6 | - | 缺少无障碍实现方案的具体设计 | 第 10 章已包含完整无障碍设计：10.1-10.5 各项实现方案。V14 新增 10.6 节无障碍实现检查清单（10 项检查项 + 验证方法）和无障碍测试工具表 |
| 7 | - | 缺少性能优化策略（代码分割、懒加载、缓存策略） | 第 15 章已包含完整性能优化设计：15.1 性能预算、15.2 优化措施。V14 新增 15.3 节浏览器缓存策略（Nginx 缓存配置、Vite 哈希文件名机制、缓存更新流程）和 15.4 加载状态设计 |

### V14 新增内容清单

| 新增项 | 位置 | 说明 |
|--------|------|------|
| heartbeat.ping/pong 事件类型 | 6.2 节 | WebSocket 心跳机制的事件类型定义 |
| 心跳机制完整代码 | 6.2 节 + 6.3 节 | 心跳定时器、超时检测、重连触发的完整实现代码 |
| 心跳机制参数说明表 | 6.2 节 | 心跳间隔、超时阈值、超时处理等参数说明 |
| 心跳与重连关系流程图 | 6.2 节 | 正常/中断/重连三种场景的心跳行为 |
| Store 职责描述 | 4.2-4.7 节 | 每个 Store 开头补充明确的职责说明文字 |
| Store 职责总览表 | 4.7 节末尾 | 6 个 Store 的职责、数据来源、持久化、WebSocket 交互总览 |
| API 分层架构表 | 5.1 节 | 实例层/模块层/Store 层/组件层四层次职责说明 |
| 模块层 API 示例代码 | 5.1 节 | project.ts 作为模块层 API 的示例 |
| 路由元信息表 | 7.1 节 | requiresAuth、layout、title 三个 meta 字段说明 |
| 路由守卫执行流程图 | 7.2 节 | 完整的守卫判断分支流程图 |
| 无障碍检查清单 | 10.6 节 | 10 项 WCAG 2.1 AA 检查项、实现方式、验证方法 |
| 无障碍测试工具表 | 10.6 节 | axe-core、Lighthouse、NVDA 等工具说明 |
| 浏览器缓存策略 | 15.3 节 | Nginx 缓存配置、Vite 哈希文件名机制、缓存更新流程 |
| 加载状态设计 | 15.4 节 | SkeletonLoader、Loading 状态层次说明 |
| Element Plus 语言切换代码 | 8.2 节 | 语言切换时同步切换 Element Plus 内置文本的代码示例（V15 已修正为 ElConfigProvider 方案） |

---

## 18. V12 -> V13 修订记录（历史保留）

### 后荣检验意见与修订对照

| 编号 | 严重程度 | 后荣检验意见 | V13 修订内容 |
|------|----------|-------------|-------------|
| 1 | 严重 | 文档截断不完整，后续内容完全缺失 | V12 文档实际完整（2910 行），V13 在此基础上进行修订，确保文档完整无截断 |
| 2 | 严重 | 缺少核心章节（路由设计、组件设计规范、状态管理详细设计、实时通信详细设计、安全设计、性能优化、部署与构建、无障碍设计） | V12 已包含上述所有章节（第 3、4、6、7、10、12、14、15 章），V13 保留并增强 |
| 3 | 中等 | Element Plus 按需引入样式方案描述不清晰 | 1.2 技术选型表修正：组件按需引入明确为 JS 代码，样式按需引入明确为 ElementPlusResolver(importStyle: 'css')，说明无需额外插件 |
| 4 | 中等 | 缺少 Pinia store 持久化策略说明 | 4.1 节补充存储介质选择依据表（localStorage/sessionStorage/内存对比），完善各 store 持久化字段的安全分析 |
| 5 | 中等 | WebSocket 统一方案缺少连接复用策略、消息路由机制、流式输出与普通消息的优先级处理 | 6.1 节新增连接复用策略（全局单连接 + 场景行为表）、消息路由机制（type 字段路由 + 消费者映射表）、优先级处理（高/普通/低三级优先级 + 实现代码 + 设计原理） |

### V13 新增内容清单

| 新增项 | 位置 | 说明 |
|--------|------|------|
| 连接复用策略 | 6.1 节 | 全局单连接方案，useWebSocket 单例模式，6 种场景行为表 |
| 消息路由机制 | 6.1 节 | type 字段路由机制，9 种消息类型到 Store 的映射表 |
| 优先级处理 | 6.1 节 | 三级优先级（高/普通/低），基于 queueMicrotask/setTimeout 的实现方案 |
| Element Plus 样式按需说明 | 1.2 节 + V12->V13 变更表 | 明确 importStyle: 'css' 的配置方式，说明无需 unelement 等额外插件 |
| 存储介质选择依据 | 4.1 节 | localStorage/sessionStorage/内存对比表 |

---

## 19. V11 -> V12 修订记录（历史保留）

| 编号 | 严重程度 | 后荣检验意见 | V11 修订内容 |
|------|----------|-------------|-------------|
| 1 | 致命 | 文档严重不完整：2.2.5 在'底部'处戛然而止 | 补全 2.2.5-2.2.9 所有页面详细说明 |
| 2 | 严重 | 路由懒加载策略未配置 | 7.1 节补充懒加载说明 |
| 3 | 严重 | WebSocket 流式输出渲染未说明打字机效果 | 新增 6.4 节打字机效果方案 |
| 4 | 严重 | Markdown 内容安全未说明具体使用场景 | 新增 12.1 节完整 XSS 防护方案 |
| 5 | 中等 | 长列表性能需要虚拟列表方案 | 新增 vue-virtual-scroller（V12 已替换为 @tanstack/vue-virtual） |
| 6 | 中等 | 暗黑模式缺少切换机制说明 | 9.2 节补充完整暗黑模式切换流程 |
| 7 | 中等 | WebSocket 断线重连策略未说明 | 6.3 节补充完整重连机制 |
| 8 | 中等 | 认证刷新流程未描述 | 4.2 节补充完整 Axios 拦截器代码 |

---

## 20. V9 -> V10 修订记录（历史保留）

| 编号 | 严重程度 | 后荣检验意见 | V10 修订内容 |
|------|----------|-------------|----------|
| 1 | 严重 | 文档截断、章节缺失 | 补全全部章节 |
| 2 | 严重 | 缺少 API 接口设计说明 | 新增 5.2 节 API 端点清单 |
| 3 | 严重 | 缺少错误处理统一方案 | 新增 5.3 节错误处理方案 |
| 4 | 中等 | SSE EventSource 不支持自定义 Header | 统一为 WebSocket 方案 |
| 5 | 中等 | 同时使用 WebSocket + SSE 增加复杂度 | 统一为 WebSocket 单一方案 |
| 6 | 中等 | 缺少测试框架选型 | 新增 13 节测试设计 |
| 7 | 中等 | 缺少打包体积优化方案 | 新增路由懒加载、manualChunks 代码分割 |
| 8 | 中等 | 无障碍标准无具体实施方案 | 扩充 10 节无障碍设计 |
| 9 | 中等 | 深色主题切换机制未说明 | 改为 CSS 变量方案 |
| 10 | 中等 | Element Plus 样式按需引入方案未说明 | 新增 9.3 节按需引入方案 |
| 11 | 中等 | 未说明移动端适配策略 | 新增 9.4 节响应式断点与移动端适配 |
| 12 | 中等 | 未说明多环境配置方案 | 新增 11 节多环境配置 |
| 13 | 中等 | 未说明构建产物部署方案 | 新增 14.3 节 Nginx 配置 |
| 14 | 轻微 | 未说明 Pinia 持久化策略 | 新增 4.1 节持久化策略 |
| 15 | 轻微 | refresh token 无感刷新流程未设计 | 4.2 节 userStore 已有完整实现 |
| 16 | 中等 | 无 XSS 防护方案 | 新增 12.1 节 XSS 防护方案 |
| 17 | 中等 | 无 CSP 设计 | 新增 12.2 节 CSP 设计 |
| 18 | 中等 | 无 CSRF 防护说明 | 新增 12.3 节 CSRF 防护 |

---

## 21. V15 -> V16 修订记录

### 跨文档一致性检验意见与修订对照

| 编号 | 一致性问题 | V16 修订内容 |
|------|-----------|-------------|
| 1 | 架构-前端: UI组件库不一致：架构文档 V22 的 2.2 节"前端技术栈"中 Element Plus 版本为 2.5+，前端文档 V15 中为 2.x | 1.2 节技术选型表：Element Plus 版本从 2.x 修正为 2.5+，与架构文档 V22 保持一致 |
| 2 | 架构-前端: 版本范围不一致：架构文档 V22 的 2.2 节中 Vite 为 5.0+、Pinia 为 2.1+、Axios 为 1.6+、Vue Router 为 4.2+，前端文档 V15 中为 5.x、2.x、1.x、4.x | 1.2 节技术选型表：Vite 修正为 5.0+、Pinia 修正为 2.1+、Axios 修正为 1.6+、Vue Router 修正为 4.2+，与架构文档 V22 保持一致 |

### V16 修订内容清单

| 修订项 | 位置 | V15 值 | V16 值 | 说明 |
|--------|------|--------|--------|------|
| Vite 版本 | 1.2 技术选型表 | 5.x | 5.0+ | 对齐架构文档 V22 的 2.2 节 |
| Pinia 版本 | 1.2 技术选型表 | 2.x | 2.1+ | 对齐架构文档 V22 的 2.2 节 |
| Element Plus 版本 | 1.2 技术选型表 | 2.x | 2.5+ | 对齐架构文档 V22 的 2.2 节 |
| Axios 版本 | 1.2 技术选型表 | 1.x | 1.6+ | 对齐架构文档 V22 的 2.2 节 |
| Vue Router 版本 | 1.2 技术选型表 | 4.x | 4.2+ | 对齐架构文档 V22 的 2.2 节 |
| 新增 V15->V16 变更说明 | 1.2 节 | 无 | 新增变更表 | 记录版本对齐的变更项和理由 |
| 新增 V15->V16 目录结构变更说明 | 1.4 节 | 无 | 无目录结构变更 | 保持与 V14->V15 相同的格式 |
| 版本号 | 文档头部 | V15 | V16 | 版本号升级 |
| 文档状态 | 文档头部 | 修订版V15 | 修订版V16 | 状态更新 |

---

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

## 23. V17 -> V18 修订记录

### 修订说明

V18 为跨文档一致性检验确认版本。V17 已针对前端-后端一致性检验发现的全部 5 项问题完成代码级修正，V18 进行最终验证确认：

| 编号 | 一致性问题 | V17 修正内容 | V18 验证结果 |
|------|-----------|-------------|-------------|
| 1 | WebSocket auth 响应类型不一致：V16 使用 'auth_ok'/'auth_fail'，后端 V35 定义为 'auth_success'/'auth_error' | 6.2 节通信图、6.3 节 useWebSocket 代码全部改为 'auth_success'/'auth_error' | 验证通过 |
| 2 | 项目更新 HTTP 方法不一致：V16 使用 PATCH，后端 V35 定义为 PUT | 5.1 节 updateProject 改为 api.put；5.2 节端点清单改为 PUT | 验证通过 |
| 3 | 通知已读标记方法不一致：V16 使用 PATCH，后端 V35 定义为 PUT | 4.6 节 markAsRead 改为 api.put；5.2 节端点清单改为 PUT | 验证通过 |
| 4 | 项目步骤端点路径不一致：V16 使用 /projects/:id/steps，后端 V35 定义为 /projects/:id/progress | 5.1 节改为 fetchProjectProgress 和 /projects/${id}/progress；5.2 节端点清单同步更新 | 验证通过 |
| 5 | ws-token 端点不存在：V16 定义了 POST /auth/ws-token，后端 V35 未定义 | 4.2 节 userStore 移除 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法；5.2 节移除 /auth/ws-token 端点；6.3 节 useWebSocket 改回使用 access_token 认证 | 验证通过 |

### V18 修订内容清单

| 修订项 | 位置 | V17 值 | V18 值 | 说明 |
|--------|------|--------|--------|------|
| 版本号 | 文档头部 | V17 | V18 | 版本号升级 |
| 文档状态 | 文档头部 | 修订版V17（跨文档一致性修正） | 修订版V18（跨文档一致性检验确认） | 状态更新 |
| V17->V18 修订记录 | 第 23 章 | 无 | 新增 | 新增一致性检验验证确认记录 |

---

## 24. V18 -> V19 修订记录

### 跨文档一致性检验意见与修订对照

| 编号 | 一致性问题 | V19 修订内容 |
|------|-----------|-------------|
| 1 | WebSocket 认证方式不一致：前端 V18 6.3 节 useWebSocket 使用 access_token 进行 auth 消息认证，期望响应类型为 auth_success/auth_error；后端 V36 2.16 节要求先调用 POST /api/v1/auth/ws-token 获取专用 ws_token 进行认证，响应类型为 auth_ok/auth_fail | 6.3 节 useWebSocket 完全重写：(a) 通过 userStore.ensureWsToken() 获取 ws_token；(b) auth 消息携带 ws_token 而非 access_token；(c) 响应类型改为 auth_ok/auth_fail；(d) auth_fail 时尝试重新获取 ws_token 而非直接跳转登录 |
| 2 | 项目更新 HTTP 方法不一致：前端 V18 5.1 节 updateProject 使用 api.put，5.2 节端点清单为 PUT /projects/:id；后端 V36 2.3 节定义为 PATCH /api/v1/projects/:id | 5.1 节 updateProject 改为 api.patch；5.2 节端点清单改为 PATCH /projects/:id，与后端 V36 2.3 节保持一致 |
| 3 | 通知已读标记 HTTP 方法不一致：前端 V18 4.6 节 markAsRead 使用 api.put，5.2 节端点清单为 PUT /notifications/:id/read；后端 V36 2.12 节定义为 PATCH /api/v1/notifications/:id/read | 4.6 节 markAsRead 改为 api.patch；5.2 节端点清单改为 PATCH /notifications/:id/read，与后端 V36 2.12 节保持一致 |
| 4 | ws-token 端点缺失：后端 V36 2.2 节新增了 POST /api/v1/auth/ws-token 端点，前端 V18 5.2 节认证端点清单中未定义该端点，userStore 中也没有 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法 | 5.2 节新增 POST /auth/ws-token 端点；4.2 节 userStore 新增 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法；logout 方法新增清除 wsToken/wsTokenExpiry；6.3 节 useWebSocket authenticate 改为调用 ensureWsToken 获取 ws_token |

### V19 修订内容清单

| 修订项 | 位置 | V18 值 | V19 值 | 说明 |
|--------|------|--------|--------|------|
| ws_token 获取方式 | 6.3 节 useWebSocket | 直接使用 userStore.accessToken | 调用 userStore.ensureWsToken() 获取 ws_token | 对齐后端 V36 2.16 节 |
| WebSocket auth token 类型 | 6.3 节 useWebSocket | access_token | ws_token | 专用短时效令牌，与后端 V36 一致 |
| auth 响应类型 | 6.2 节、6.3 节 | auth_success/auth_error | auth_ok/auth_fail | 对齐后端 V36 2.16 节 |
| auth_fail 处理策略 | 6.3 节 useWebSocket | 直接跳转登录页 | 尝试重新获取 ws_token，失败后跳转登录页 | 更健壮的错误恢复机制 |
| 项目更新方法 | 5.1 节、5.2 节 | PUT /projects/:id (api.put) | PATCH /projects/:id (api.patch) | 对齐后端 V36 2.3 节 |
| 通知已读方法 | 4.6 节、5.2 节 | PUT /notifications/:id/read (api.put) | PATCH /notifications/:id/read (api.patch) | 对齐后端 V36 2.12 节 |
| ws-token 端点 | 5.2 节 | 未定义 | POST /auth/ws-token | 对齐后端 V36 2.2 节 |
| wsToken 字段 | 4.2 节 userStore | 不存在 | wsToken: string \| null | 对齐后端 V36 2.2 节 |
| wsTokenExpiry 字段 | 4.2 节 userStore | 不存在 | wsTokenExpiry: number \| null | 对齐后端 V36 2.2 节 |
| fetchWsToken 方法 | 4.2 节 userStore | 不存在 | 新增 | 获取 WebSocket 专用认证令牌 |
| ensureWsToken 方法 | 4.2 节 userStore | 不存在 | 新增 | 验证 ws_token 有效性，过期自动刷新 |
| logout 清理字段 | 4.2 节 userStore | 仅清理 user/accessToken/refreshToken/tokenExpiry | 新增清理 wsToken/wsTokenExpiry | 完整的 Token 清理 |
| userStore 职责描述 | 4.7 节 Store 职责总览表 | 无 WebSocket 交互 | 管理 ws_token，WebSocket 使用 ws_token 认证 | 更新职责描述 |
| 版本号 | 文档头部 | V18 | V19 | 版本号升级 |
| 文档状态 | 文档头部 | 修订版V18（跨文档一致性检验确认） | 修订版V19（跨文档一致性检验修正） | 状态更新 |

---

## 25. V19 -> V20 修订记录

### 跨文档一致性检验意见与修订对照

| 编号 | 一致性问题 | V20 修订内容 |
|------|-----------|-------------|
| A1 | 架构-前端: WebSocket 端点不一致：架构 V24 §3.5 定义 WS /ws/v1/groups/{id}，前端 V19 使用 ws://host/ws 单连接（6.3 节），二者路径格式完全不同 | 6.1 节改为多连接方案，6.3 节 useWebSocket 完全重写为三个独立连接（ws/group-chat、ws/notifications、ws/workflow/:project_id），对齐后端 V37 §2.16 定义的三个独立端点 |
| A2 | 架构-前端: 代码仓库接口缺失：架构 §2.2 代码仓库接口为 /api/v1/projects/{id}/repo/init 和 /repo/commit，前端 V19 §5.2 使用 /projects/:id/repo（GET 仓库信息），缺少 repo/init 和 repo/commit 端点定义 | 5.2 节代码仓库相关新增 POST /projects/:id/repo/init 和 POST /projects/:id/repo/commit 端点，与架构 V24 §2.2 保持一致 |
| A3 | 架构-前端: 文档管理接口缺失：架构 §3.4 定义 GET /api/v1/projects/{id}/docs 文档管理接口，前端 V19 无对应 API 端点和路由 | 5.2 节新增文档管理端点（GET /projects/:id/docs、GET /projects/:id/docs/:docId）；新增 7.1 节路由 /projects/:id/docs；新增 docsStore（4.7 节）、DocsView、DocViewer/DocList 组件 |
| A4 | 架构-前端: 角色权限模型缺失：架构 §6.1 角色模型为 owner/admin/member/viewer 四角色，前端 V19 未在任何 Store 或 Schema 中定义 project_members 或角色权限模型 | 4.2 节 userStore 新增 ProjectRole 类型和 ProjectMember 接口；4.3 节 projectStore 新增 members 字段和 fetchMembers 方法；5.2 节新增 GET /projects/:id/members 端点；新增 types/project.ts 类型定义 |
| B1 | 前端-后端: WebSocket 认证方式不一致：前端 V19 §6.3 使用 ws_token 进行 auth 消息认证，期望响应 auth_ok/auth_fail；后端 V37 §2.16 明确使用 access_token 认证，响应类型为 auth_success/auth_error | 4.2 节 userStore 移除 wsToken/wsTokenExpiry 字段和 fetchWsToken/ensureWsToken 方法；6.2 节 auth 事件类型改回 auth_success/auth_error；6.3 节 useWebSocket 改为使用 access_token 进行 auth 消息认证 |
| B2 | 前端-后端: 项目更新 HTTP 方法不一致：前端 V19 §5.1 updateProject 使用 api.patch，§5.2 端点清单为 PATCH /projects/:id；后端 V37 §2.3 定义为 PUT /api/v1/projects/:id | 5.1 节 updateProject 改为 api.put；5.2 节端点清单改为 PUT /projects/:id，与后端 V37 §2.3 保持一致 |
| B3 | 前端-后端: 通知已读标记 HTTP 方法不一致：前端 V19 §4.6 markAsRead 使用 api.patch，§5.2 端点清单为 PATCH /notifications/:id/read；后端 V37 §2.12 定义为 PUT /api/v1/notifications/:id/read | 4.6 节 markAsRead 改为 api.put；5.2 节端点清单改为 PUT /notifications/:id/read，与后端 V37 §2.12 保持一致 |
| B4 | 前端-后端: ws-token 端点：前端 V19 §5.2 定义了 POST /auth/ws-token，后端 V37 §2.2 认证端点列表中无此端点 | 5.2 节移除 POST /auth/ws-token 端点；4.2 节 userStore 移除 wsToken 相关字段和方法；6.3 节 useWebSocket 移除 ws_token 认证逻辑 |
| B5 | 前端-后端: WebSocket 端点不一致：前端 V19 §6.3 使用 ws://host/ws 单连接，后端 V37 §2.16 定义 ws://host/ws/group-chat、ws://host/ws/notifications、ws://host/ws/workflow/:project_id 三个独立端点 | 6.1 节改为多连接方案，6.3 节 useWebSocket 完全重写为三个独立 WebSocket 连接管理，与后端 V37 §2.16 保持一致 |
| B6 | 前端-后端: 设置端点缺失：前端 V19 §4.7 settingStore 使用 api.get('/settings') 和 api.patch('/settings')，后端 V37 无对应 /settings 端点 | 4.8 节 settingStore 移除 fetchSettings 和 updateSettings 方法，改为纯本地偏好设置（仅持久化到 localStorage，不与后端 API 交互） |
| B7 | 前端-后端: 任务状态更新 HTTP 方法不一致：前端 V19 §4.5 taskStore updateTaskStatus 使用 api.patch(/tasks/${taskId}, {status})，后端 V37 §2.5 使用 PUT /tasks/:id | 4.4 节 taskStore updateTaskStatus 改为 api.put；5.2 节端点清单改为 PUT /tasks/:id，与后端 V37 §2.5 保持一致 |

### V20 修订内容清单

| 修订项 | 位置 | V19 值 | V20 值 | 说明 |
|--------|------|--------|--------|------|
| WebSocket 连接方案 | 6.1 节、6.3 节 | 单连接复用 ws://host/ws | 三连接：ws/group-chat、ws/notifications、ws/workflow/:project_id | 对齐后端 V37 §2.16 |
| WebSocket 认证方式 | 6.3 节 useWebSocket | ws_token | access_token | 对齐后端 V37 §2.16 |
| auth 响应类型 | 6.2 节、6.3 节 | auth_ok/auth_fail | auth_success/auth_error | 对齐后端 V37 §2.16 |
| ws-token 端点 | 5.2 节 | POST /auth/ws-token | 已移除 | 后端 V37 无此端点 |
| wsToken 字段 | 4.2 节 userStore | wsToken: string \| null | 已移除 | 后端 V37 无此端点 |
| wsTokenExpiry 字段 | 4.2 节 userStore | wsTokenExpiry: number \| null | 已移除 | 后端 V37 无此端点 |
| fetchWsToken 方法 | 4.2 节 userStore | 已存在 | 已移除 | 后端 V37 无此端点 |
| ensureWsToken 方法 | 4.2 节 userStore | 已存在 | 已移除 | 后端 V37 无此端点 |
| 项目更新方法 | 5.1 节、5.2 节 | PATCH /projects/:id (api.patch) | PUT /projects/:id (api.put) | 对齐后端 V37 §2.3 |
| 通知已读方法 | 4.6 节、5.2 节 | PATCH /notifications/:id/read (api.patch) | PUT /notifications/:id/read (api.put) | 对齐后端 V37 §2.12 |
| 任务状态更新方法 | 4.4 节、5.2 节 | PATCH /tasks/:id (api.patch) | PUT /tasks/:id (api.put) | 对齐后端 V37 §2.5 |
| settingStore API 调用 | 4.7 节 | fetchSettings/updateSettings 调用 API | 已移除 API 调用，仅本地持久化 | 后端 V37 无 /settings 端点 |
| 代码仓库端点 | 5.2 节 | 仅 GET /projects/:id/repo 等 | 新增 POST /projects/:id/repo/init、POST /projects/:id/repo/commit | 对齐架构 V24 §2.2 |
| 文档管理端点 | 5.2 节 | 不存在 | 新增 GET /projects/:id/docs、GET /projects/:id/docs/:docId | 对齐架构 V24 §3.4 |
| 文档管理路由 | 7.1 节 | 不存在 | 新增 /projects/:id/docs | 对齐架构 V24 §3.4 |
| docsStore | 4.7 节 | 不存在 | 新增 docsStore | 文档状态管理 |
| 角色权限模型 | 4.2 节 userStore | 不存在 | 新增 ProjectRole 类型和 ProjectMember 接口 | 对齐架构 V24 §6.1 |
| projectStore members | 4.3 节 | 不存在 | 新增 members 字段和 fetchMembers 方法 | 对齐架构 V24 §6.1 |
| 项目成员端点 | 5.2 节 | 不存在 | 新增 GET /projects/:id/members | 对齐架构 V24 §6.1 |
| Nginx WS 代理 | 14.3 节 | 单一 /ws 代理 | 三个 /ws/* 端点代理 | 对齐多连接方案 |
| 技术选型 WebSocket | 1.2 节 | 单连接复用 + 自定义消息路由 | 多连接方案（3个独立端点） | 对齐后端 V37 |
| 版本号 | 文档头部 | V19 | V20 | 版本号升级 |
| 文档状态 | 文档头部 | 修订版V19（跨文档一致性检验修正） | 修订版V20（跨文档一致性检验修正） | 状态更新 |

---

**文档结束。V20 版本共 25 章，涵盖前端概述、页面设计、组件设计、状态管理、API 设计、WebSocket 通信、路由设计、国际化、样式设计、无障碍设计、多环境配置、安全设计、测试设计、构建部署、性能优化、以及 V14->V15 / V13->V14 / V12->V13 / V11->V12 / V9->V10 / V15->V16 / V16->V17 / V17->V18 / V18->V19 / V19->V20 修订记录。**
