# DevFlow 项目管理平台 - 前端设计文档

**版本**: V13  
**日期**: 2026-06-20  
**作者**: HouWang (后旺)  
**状态**: 修订版V13（等待后荣检验）

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
8. **多语言与无障碍**：支持中/英文切换，满足 WCAG 2.1 AA 级无障碍标准

### 1.2 技术选型

| 类别 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 框架 | Vue.js | 3.4+ | 响应式、组合式 API、TypeScript 友好 |
| 构建工具 | Vite | 5.x | 快速启动、HMR、原生 ESM |
| 语言 | TypeScript | 5.x | 类型安全、IDE 支持 |
| 状态管理 | Pinia | 2.x | Vue 3 官方推荐、轻量 |
| 状态持久化 | pinia-plugin-persistedstate | 4.x | Pinia 官方推荐的持久化插件 |
| UI 组件库 | Element Plus | 2.x | 丰富的企业级组件、主题定制 |
| 组件按需引入 | unplugin-vue-components | - | 自动按需导入 Element Plus 组件 JS 代码 |
| 接口按需引入 | unplugin-auto-import | - | 自动按需导入 Vue/VueRouter/Pinia API |
| 样式按需引入 | unplugin-vue-components + ElementPlusResolver(importStyle: 'css') | - | ElementPlusResolver 配置 importStyle: 'css' 时，unplugin-vue-components 会自动按需引入每个组件对应的 CSS 样式文件，无需额外插件 |
| HTTP 客户端 | Axios | 1.x | 拦截器、超时控制、取消请求 |
| WebSocket | 原生 WebSocket（单连接复用 + 自定义消息路由） | - | 统一实时通信方案（消息推送 + 流式输出），单连接复用，基于 JSON type 字段路由，流式消息高优先级 |
| 路由 | Vue Router | 4.x | Vue 3 官方路由 |
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
|--------|---------|----------|----------|
| 虚拟列表 | vue-virtual-scroller | @tanstack/vue-virtual | vue-virtual-scroller 是 Vue 2 时代的库，在 Vue 3 项目中存在兼容性问题；@tanstack/vue-virtual 由 TanStack 维护，原生支持 Vue 3 Composition API，活跃度高 |
| ECharts 引入方式 | echarts 全量引入 | @echarts/core 按需加载 | ECharts 全量引入体积约 400KB gzip，按需加载可减少约 60% 体积 |
| Element Plus 样式按需 | importStyle 未明确 | ElementPlusResolver(importStyle: 'css') | V12 描述不够精确，V13 明确：ElementPlusResolver 配置 importStyle: 'css' 时，unplugin-vue-components 自动按需引入每个组件对应的 CSS 样式文件，无需 unelement 等额外插件 |

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
│   │   └── notification.ts     # 通知 API
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
│   │   └── qa/                 # QA 相关组件
│   │       ├── QAResultCard.vue # 检验结果卡片
│   │       ├── QAScoreChart.vue # 评分图表
│   │       └── QAProblemList.vue # 问题列表
│   ├── composables/            # 组合式函数
│   │   ├── useWebSocket.ts     # WebSocket 连接（统一实时通信）
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
│   │   └── settingStore.ts     # 系统设置
│   ├── views/                  # 页面视图
│   │   ├── LoginView.vue       # 登录页
│   │   ├── DashboardView.vue   # 首页/仪表板
│   │   ├── ProjectListView.vue # 项目列表页
│   │   ├── ProjectDetailView.vue # 项目详情页
│   │   ├── ChatView.vue        # 讨论群聊天页
│   │   ├── TaskView.vue        # 任务看板页
│   │   ├── QAView.vue          # QA 检验页
│   │   ├── RepoView.vue        # 代码仓库页
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

#### 2.2.9 系统设置 (/settings)

- 个人信息：头像、用户名
- 通知偏好：邮件通知、浏览器推送开关
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

```vue
<template>
  <div v-if="error">
    <el-result icon="error" title="组件加载失败" :sub-title="errorMessage">
      <template #extra>
        <el-button type="primary" @click="retry">重试</el-button>
      </template>
    </el-result>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue';

const error = ref(false);
const errorMessage = ref('');

onErrorCaptured((err, vm, info) => {
  error.value = true;
  errorMessage.value = err.message || '未知错误';
  reportError(err, vm, info);
  return false;
});

const retry = () => {
  error.value = false;
};
</script>
```

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
- 连接 WebSocket 获取实时消息和流式输出
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
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useVirtualizer } from '@tanstack/vue-virtual';

const props = defineProps<MessageListProps>();
const parentRef = ref<HTMLElement | null>(null);

const rowVirtualizer = useVirtualizer({
  count: computed(() => props.messages.length),
  getScrollElement: () => parentRef.value,
  estimateSize: () => 80, // 每条消息预估高度 80px
  overscan: 5, // 预渲染 5 条
});

const virtualRows = computed(() => rowVirtualizer.value?.getVirtualItems() || []);
const totalHeight = computed(() => rowVirtualizer.value?..getTotalSize() || 0);

const isStreaming = (messageId: string) => {
  return props.streamingMessages.has(messageId);
};
</script>
```

- @tanstack/vue-virtual 使用 `useVirtualizer` hook，原生支持 Vue 3 Composition API
- `estimateSize` 为每条消息的预估高度（80px），实际高度变化时可调用 `measure()` 更新
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

1. 登录成功后同时获取 access token 和 refresh token
2. access token 存储在 memory 中，refresh token 持久化到 localStorage
3. Axios 请求拦截器中检查 token 有效期：
   - 若 token 将在 60 秒内过期，主动调用 `/auth/refresh` 刷新
   - 若接口返回 401，尝试使用 refresh token 刷新
   - 刷新成功后重试原请求
   - 刷新失败则跳转登录页
4. 同一时刻只允许一个 refresh 请求，其他请求排队等待

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

```typescript
interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
}

export const useProjectStore = defineStore('project', {
  state: (): ProjectState => ({
    projects: [],
    currentProject: null,
    loading: false,
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
  },
});
```

### 4.4 taskStore

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
    async updateTaskStatus(taskId: string, status: string) {
      await api.patch(`/tasks/${taskId}`, { status });
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
      useWebSocket().connect(groupId);
    },
    disconnectWebSocket() {
      useWebSocket().disconnect();
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

**Store 与 composable 的调用关系：**

- `connectWebSocket` / `disconnectWebSocket`：chatStore 委托 useWebSocket composable 处理底层 WebSocket 连接生命周期
- `handleStreamChunk` / `handleStreamDone`：流式输出通过 WebSocket 接收，由 chatStore 处理状态更新
- composable 负责连接管理，Store 负责状态更新和消息协调

### 4.6 notificationStore

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
    async markAsRead(id: string) {
      await api.patch(`/notifications/${id}/read`);
      const n = this.notifications.find(x => x.id === id);
      if (n) n.read = true;
      this.unreadCount = this.notifications.filter(x => !x.read).length;
    },
  },
});
```

### 4.7 settingStore

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
  actions: {
    async fetchSettings() {
      this.$state = await api.get('/settings');
    },
    async updateSettings(data: Partial<SettingState>) {
      await api.patch('/settings', data);
      Object.assign(this.$state, data);
    },
  },
  persist: {
    key: 'devflow-settings',
    storage: localStorage,
  },
});
```

---

## 5. API 设计

### 5.1 API 基础配置

```typescript
// src/api/index.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
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

// 响应拦截器：token 刷新（详见 4.2 节）
// 见 userStore 中的拦截器实现
```

### 5.2 API 端点清单

#### 认证相关

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /auth/login | 用户登录 |
| POST | /auth/refresh | 刷新 access token |
| POST | /auth/logout | 退出登录 |

#### 项目相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects | 项目列表 |
| POST | /projects | 创建项目 |
| GET | /projects/:id | 项目详情 |
| PATCH | /projects/:id | 更新项目 |
| GET | /projects/:id/steps | 项目步骤进度 |

#### 任务相关

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /projects/:id/tasks | 任务列表 |
| PATCH | /tasks/:id | 更新任务状态 |

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
| PATCH | /notifications/:id/read | 标记已读 |

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

## 6. WebSocket 统一通信设计

### 6.1 统一通信方案

**V9 -> V10 变更说明：**

V9 同时使用 WebSocket 和 SSE（EventSource）两种协议，存在以下问题：

1. EventSource 不支持自定义 Header，无法携带认证 token
2. 同时维护两种实时通信协议增加前后端复杂度
3. 需要后端额外设计 token-less 的 SSE 端点

V10 统一为 WebSocket 单一方案，所有实时通信（消息推送、状态变更、流式输出）均通过 WebSocket 完成。

**V12 -> V13 补充：连接复用、消息路由、优先级处理**

**连接复用策略：**

采用全局单连接方案，整个应用生命周期内仅维护一个 WebSocket 连接，所有页面共享。连接管理由 `useWebSocket` composable 作为单例提供：

```typescript
// 全局单例模式
let wsInstance: ReturnType<typeof createWebSocketManager> | null = null;

export function useWebSocket() {
  if (!wsInstance) {
    wsInstance = createWebSocketManager();
  }
  return wsInstance;
}
```

| 场景 | 连接行为 |
|------|---------|
| 应用启动 | 用户登录后自动建立连接 |
| 切换项目 | 不重建连接，通过消息路由切换到新项目上下文 |
| 切换讨论群 | 不重建连接，发送 `chat.join` 加入新群，同时发送 `chat.leave` 离开旧群 |
| 用户登出 | 主动关闭连接 |
| 页面刷新 | 连接丢失，登录后重新建立 |
| Token 刷新 | 不中断连接，服务端识别新 token 的权限变更 |

**消息路由机制：**

单连接承载多种消息类型，通过 JSON 消息的 `type` 字段进行路由。useWebSocket 内部维护事件处理器映射表，收到消息后按 type 分发：

```
WebSocket 收到消息 (JSON)
    |
    v
JSON.parse(event.data)
    |
    v
读取 data.type 字段
    |
    v
查找 eventHandlers.get(type)
    |
    v
遍历该 type 下的所有 handler，依次执行
```

| 消息 type | 目标消费者 | 说明 |
|-----------|----------|------|
| message.new | chatStore | 新消息到达，推入消息列表 |
| message.deleted | chatStore | 消息被删除，从列表移除 |
| stream.chunk | chatStore (高优先级) | Agent 流式输出增量，触发打字机效果 |
| stream.done | chatStore (高优先级) | Agent 流式输出结束 |
| stream.error | chatStore | 流式输出异常 |
| agent.status | 全局监听器 | Agent 状态变更，更新 AgentBadge |
| task.updated | taskStore | 任务状态变更，更新看板 |
| project.step.changed | projectStore | 项目步骤推进，更新进度条 |
| notification | notificationStore | 系统通知推送，更新未读数 + 弹出提示 |

**流式输出与普通消息的优先级处理：**

| 优先级 | 消息类型 | 处理策略 | 原因 |
|--------|---------|---------|------|
| 高 | stream.chunk | 立即处理，直接更新 pendingContent，触发 requestAnimationFrame 渲染 | 流式输出需要实时展示，延迟超过 16ms 会感知卡顿 |
| 高 | stream.done | 立即处理，清除流式状态，最终渲染 | 确保流式输出结束时内容完整 |
| 普通 | message.new | 推入消息列表，Vue 响应式自动渲染 | 已完成的消息，无需立即渲染 |
| 普通 | agent.status | 更新 store 状态 | 状态变更可延迟到下一帧 |
| 普通 | task.updated | 更新 store 状态 | 看板更新可延迟 |
| 低 | notification | 推入通知列表 + 弹出 ElNotification | 通知可异步展示 |

**优先级实现方式：**

```typescript
// onmessage 处理器内部按优先级分发
ws.value.onmessage = (event) => {
  const data = JSON.parse(event.data);
  const type = data.type;

  // 高优先级：直接同步处理（stream.*）
  if (type.startsWith('stream.')) {
    triggerEvent(type, data); // 同步执行，不排队
  }
  // 普通优先级：推入微任务队列
  else if (['message.new', 'agent.status', 'task.updated'].includes(type)) {
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

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| message.new | Server -> Client | 新消息推送（消息已完成） |
| message.deleted | Server -> Client | 消息删除通知 |
| agent.status | Server -> Client | Agent 状态变更 |
| task.updated | Server -> Client | 任务状态变更 |
| project.step.changed | Server -> Client | 项目步骤推进 |
| notification | Server -> Client | 系统通知推送 |
| stream.chunk | Server -> Client | Agent 回复内容增量追加 |
| stream.done | Server -> Client | Agent 回复完成 |
| stream.error | Server -> Client | 流式输出错误 |
| chat.join | Client -> Server | 加入讨论群 |
| chat.leave | Client -> Server | 离开讨论群 |
| message.send | Client -> Server | 发送消息 |

**职责说明：**

- `message.new` 推送的是**已完成的消息**
- `stream.chunk` / `stream.done` 负责**流式输出的过程展示**
- 两者不重复：流式输出结束后，客户端已拥有完整消息内容
- 前端流程：用户发送消息 -> WebSocket 发送 message.send -> 服务端开始生成回复 -> WebSocket 推送 stream.chunk 逐块 -> WebSocket 推送 stream.done 结束

### 6.3 WebSocket 连接管理（useWebSocket composable）

```typescript
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

  const getWsUrl = () => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || location.host;
    const userStore = useUserStore();
    const token = userStore?.accessToken || '';
    return `${protocol}//${host}/ws?token=${encodeURIComponent(token)}`;
  };

  const connect = (groupId?: string) => {
    if (ws.value) return;
    ws.value = new WebSocket(getWsUrl());

    ws.value.onopen = () => {
      connected.value = true;
      reconnectAttempts.value = 0;
      reconnectStatus.value = 'connected';
      if (groupId) {
        ws.value?.send(JSON.stringify({
          type: 'chat.join',
          payload: { group_id: groupId },
        }));
      }
    };

    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data);
      triggerEvent(data.type, data);
    };

    ws.value.onerror = () => {
      reconnectStatus.value = 'reconnecting';
    };

    ws.value.onclose = (event) => {
      connected.value = false;
      ws.value = null;
      if (!event.wasClean) {
        attemptReconnect(groupId);
      }
    };
  };

  const disconnect = () => {
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
```

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
| 重连成功后 | 重置计数器 | reconnectAttempts 归零 |
| 超过最大次数后 | 停止重连 | 弹出 ElMessage 错误提示，建议用户刷新页面 |

**用户感知提示：**

- `reconnectStatus` 为响应式 ref，暴露给 UI 层
- 聊天页面底部输入框上方根据 `reconnectStatus` 显示不同状态：
  - `connected`：绿色圆点 + "已连接"
  - `reconnecting`：黄色圆点 + "连接中断，正在重连..."
  - `disconnected`：红色圆点 + "连接已断开"
- 重连超过 5 次后弹出 ElMessage 错误提示："WebSocket 连接失败，请检查网络后刷新页面"

**认证方式：**

- WebSocket 连接时通过 URL query 参数携带 token：`ws://host/ws?token=xxx`
- 服务端验证 token 有效性后建立连接
- Token 过期后重连时会自动使用新 token（userStore 中已刷新）

### 6.4 流式输出处理

V10 将 V9 的 SSE 流式输出迁移至 WebSocket，处理方式如下：

```typescript
// ChatView.vue 中绑定 WebSocket 事件
const ws = useWebSocket();
const chatStore = useChatStore();

onMounted(() => {
  ws.connect(groupId);

  ws.on('stream.chunk', (data) => {
    chatStore.handleStreamChunk(data.message_id, data.content);
  });

  ws.on('stream.done', (data) => {
    chatStore.handleStreamDone(data.message_id, data.full_content);
  });

  ws.on('stream.error', (data) => {
    ElMessage.error('Agent 回复生成失败');
    chatStore.clearStreamingContent(data.message_id);
  });

  ws.on('message.new', (data) => {
    chatStore.messages.push(data.message);
  });
});

onUnmounted(() => {
  ws.disconnect();
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
];
```

**路由懒加载策略：**

- 所有页面组件均采用 `() => import()` 动态导入
- Vite 构建时自动按路由分割代码包（chunk）
- 大体积库（ECharts 按需加载模块、md-editor-v3）也会被单独拆分
- views 目录下 9 个页面视图全部使用懒加载，确保首屏只加载 Dashboard 相关代码

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

- vendor-vue chunk < 50KB (gzip)
- vendor-element chunk < 100KB (gzip)（按需引入后）
- vendor-echarts chunk < 100KB (gzip)（V12 变更：按需加载后从 200KB 降至约 100KB）
- 首页首屏 JS 总体积 < 150KB (gzip)

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

// 登录成功后跳转处理
router.afterEach((to) => {
  // 如果有 redirect query，登录后已自动处理（在 LoginView 中）
  // 这里可添加页面标题更新等全局逻辑
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
| 访问不存在的路由 | Vue Router 404 处理 | 需配置 catch-all 路由 |
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

通过 Nginx 设置 CSP Header，限制资源加载来源：

```nginx
add_header Content-Security-Policy "default-src 'self'; \
  script-src 'self' 'unsafe-inline'; \
  style-src 'self' 'unsafe-inline'; \
  img-src 'self' data: https:; \
  font-src 'self'; \
  connect-src 'self' ws: wss:; \
  frame-src 'none'; \
  object-src 'none';";
```

**CSP 策略说明：**

| 指令 | 值 | 说明 |
|------|------|------|
| default-src | 'self' | 默认只允许同源资源 |
| script-src | 'self' 'unsafe-inline' | 允许内联脚本（Vue 运行时注入） |
| style-src | 'self' 'unsafe-inline' | 允许内联样式（Element Plus 动态样式） |
| img-src | 'self' data: https: | 允许站内图片、data URI、HTTPS 外部图片（头像等） |
| font-src | 'self' | 仅允许同源字体 |
| connect-src | 'self' ws: wss: | 允许同源 API 和 WebSocket 连接 |
| frame-src | 'none' | 禁止 iframe |
| object-src | 'none' | 禁止 object/embed 标签 |

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

    location /ws {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ws: wss:; frame-src 'none'; object-src 'none';";

    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
```

---

## 15. 性能优化设计（V12 新增）

### 15.1 性能预算指标

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 首屏 LCP (Largest Contentful Paint) | < 2.5s | Lighthouse CI |
| 首屏 JS 总体积 (gzip) | < 150KB | Vite build 分析 |
| 首屏 FCP (First Contentful Paint) | < 1.5s | Lighthouse CI |
| 交互就绪时间 (TTI) | < 3s | Lighthouse CI |
| 路由切换时间 | < 300ms | Performance API |
| 虚拟列表滚动帧率 | >= 55fps | Chrome DevTools |
| 内存占用峰值 | < 200MB | Chrome DevTools Memory |

### 15.2 性能优化措施

**路由懒加载：**

- 所有 9 个页面视图使用 `() => import()` 动态导入
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

### 15.3 加载状态设计

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

## 16. V12 -> V13 修订记录

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

## 17. V11 -> V12 修订记录（历史保留）

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

## 18. V9 -> V10 修订记录（历史保留）

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
