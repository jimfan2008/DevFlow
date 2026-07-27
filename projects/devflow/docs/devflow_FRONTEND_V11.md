# DevFlow 项目管理平台 - 前端设计文档

**版本**: V11  
**日期**: 2026-06-17  
**作者**: HouWang (后旺)  
**状态**: 修订版V11（等待后荣检验）

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
| 组件按需引入 | unplugin-vue-components | - | 自动按需导入 Element Plus 组件 |
| 接口按需引入 | unplugin-auto-import | - | 自动按需导入 Vue/VueRouter/Pinia API |
| 样式按需引入 | unplugin-auto-import + ElementPlusResolver | - | 配合 unplugin-vue-components 自动引入组件样式 |
| HTTP 客户端 | Axios | 1.x | 拦截器、超时控制、取消请求 |
| WebSocket | 原生 WebSocket（自定义重连逻辑） | - | 统一实时通信方案（消息推送 + 流式输出） |
| 路由 | Vue Router | 4.x | Vue 3 官方路由 |
| 国际化 | vue-i18n | 9.x | 多语言支持 |
| 代码规范 | ESLint + Prettier | - | 统一代码风格 |
| 测试框架 | Vitest | 2.x | 与 Vite 生态一致、快速执行 |
| 组件测试 | @vue/test-utils | 2.x | Vue 官方组件测试库 |
| E2E 测试 | Playwright | 1.x | 跨浏览器 E2E 测试、Vue 官方推荐 |
| 拖拽库 | vue-draggable-plus | 2.x | Vue3 拖拽库，支持看板拖拽排序 |
| 虚拟列表 | vue-virtual-scroller | - | 长列表性能优化，虚拟滚动渲染 |
| CSS 预处理 | SCSS | - | 变量、嵌套、混入 |
| 图标库 | @element-plus/icons-vue | - | 与 Element Plus 风格统一 |
| 富文本编辑器 | @tiptap/vue-3 | - | 需求描述、文档编辑 |
| Markdown 预览 | md-editor-v3 | - | SRS 等文档预览 |
| XSS 过滤 | DOMPurify | 3.x | 过滤富文本和 Markdown 中的危险 HTML |
| 图表 | ECharts | 5.x | 项目进度、Agent 负载统计 |

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
│   │   │   └── ErrorBoundary.vue # 错误边界组件
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
│   │   └── useTheme.ts         # 主题切换（V11 明确）
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
| 新增 useTheme.ts | 明确主题切换 composable 位置（V10 仅在 9.2 节代码示例中出现，未列入目录） |

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

#### 2.2.2 仪表板 (/dashboard)

- 顶部统计卡片：进行中项目数、待处理通知数、Agent 在线数
- 项目列表（最近 5 个），点击跳转项目详情
- 最近动态时间线
- 快捷操作按钮：新建项目

#### 2.2.3 项目列表 (/projects)

- 卡片列表布局，每张卡片展示：项目名称、描述、当前阶段、进度百分比、负责人 Agent
- 搜索框（按名称/描述搜索）
- 筛选条件：状态（进行中/已完成/已暂停）、创建时间
- 新建项目按钮，弹出创建对话框

#### 2.2.4 项目详情 (/projects/:id)

- 项目基本信息（名称、描述、创建时间、当前阶段）
- 16 步流程进度条，高亮当前步骤
- 左侧导航标签：概览、文档、任务、讨论群、QA、代码仓库
- 文档区域：SRS、架构设计文档等，使用 md-editor-v3 预览（V11：渲染前经过 sanitizeHtml 过滤，详见 12.1 节）
- Agent 分配情况列表

#### 2.2.5 讨论群聊天 (/projects/:id/chat)

- 左侧：讨论群列表（当前项目的多个讨论群）
- 中间：消息列表，区分用户消息和 Agent 消息，使用 vue-virtual-scroller 虚拟滚动渲染（V11 新增，详见第 3 点补充）
- Agent 消息支持 WebSocket 流式输出显示，采用打字机效果渲染（V11 新增，详见第 3 点补充）
- 会议模式：顶部显示会议议程（MeetingAgenda 组件）
- 底部区域说明（V11 补全）：
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
- 顶部工具栏（V11 补全）：
  - 筛选条件：按负责 Agent 筛选、按优先级筛选、按步骤编号筛选
  - 视图切换：看板视图 / 列表视图 / 时间线视图（TaskTimeline 组件）
  - 搜索框：按任务标题搜索
- 每列顶部显示该列任务数量统计
- 拖拽完成后自动调用 API 更新任务状态，失败时回滚卡片位置并提示用户

#### 2.2.7 QA 检验 (/projects/:id/qa)

- 检验结果列表，按步骤排序
- 每个检验结果展示：步骤名称、检验 Agent（后荣）、评分、状态（通过/不通过）
- 不通过的检验项展示具体问题列表（QAProblemList 组件）
- 评分雷达图（QAScoreChart 组件，基于 ECharts）
- 顶部工具栏（V11 补全）：
  - 筛选条件：按检验状态（通过/不通过）筛选、按步骤筛选
  - 查看模式切换：列表模式 / 雷达图对比模式
- 评分趋势折线图：展示各步骤检验评分的变化趋势（ECharts 折线图）
- 点击检验结果卡片弹出详情抽屉，展示完整检验报告（包括检验维度明细、问题描述、建议修改方案）

#### 2.2.8 代码仓库 (/projects/:id/repo)

- 仓库基本信息：名称、描述、默认分支
- 提交记录列表（CommitList 组件），使用 vue-virtual-scroller 虚拟滚动渲染，支持分页（V11 新增）
- 分支列表（BranchList 组件）
- PR 列表（PRList 组件），展示 PR 状态、评论数、文件变更
- 顶部工具栏（V11 补全）：
  - 分支切换下拉框：切换查看不同分支的提交记录
  - 查看模式切换：提交记录 / 分支列表 / PR 列表
  - 搜索框：按提交信息、作者搜索

#### 2.2.9 系统设置 (/settings)

- 个人信息：头像、用户名
- 通知偏好：邮件通知、浏览器推送开关
- 语言切换：中文/英文
- 主题设置：浅色/深色（V11：由 settingStore 管理 theme 字段，切换时通过 useTheme composable 给 `<html>` 添加/移除 `dark` 类，Element Plus 内置 dark 主题跟随切换，详见 9.2 节补充）
- 其他设置（V11 补全）：
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
  // 上报错误日志
  reportError(err, vm, info);
  return false; // 停止错误传播
});

const retry = () => {
  error.value = false;
};
</script>
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
- V11 补充：渲染 Markdown 内容时，先通过 sanitizeHtml() 过滤再使用 v-html 渲染，防止 XSS 注入

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

- 虚拟滚动渲染（V11 补充：使用 vue-virtual-scroller 的 `RecycleScroller` 组件）
- 按时间分组显示（今天、昨天、更早）
- 流式消息实时追加渲染

**V11 补充：虚拟列表实现方案**

```vue
<template>
  <RecycleScroller
    class="message-scroller"
    :items="messages"
    :item-size="80"
    key-field="id"
    v-slot="{ item }"
  >
    <MessageBubble :message="item" :is-streaming="isStreaming(item.id)" />
  </RecycleScroller>
</template>

<script setup lang="ts">
import { RecycleScroller } from 'vue-virtual-scroller';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
</script>
```

- `item-size` 为每条消息的预估高度（80px），实际高度变化时调用 `setItemSize()` 更新
- 仅渲染可视区域内的消息 DOM 节点，数千条消息也能保持流畅滚动
- 流式消息追加时，Vue 响应式更新自动触发 RecycleScroller 重新计算

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

- 基于 ECharts 的雷达图
- 维度：完整性、一致性、可验证性、无歧义性、代码正确性、测试通过率
- 多步骤对比（折线图模式）

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
| userStore | refreshToken | localStorage | 页面刷新后保持登录状态 |
| settingStore | 全部字段 | localStorage | 用户偏好设置需持久保存 |
| projectStore | 不持久化 | - | 项目数据从服务器获取 |
| taskStore | 不持久化 | - | 任务数据从服务器获取 |
| chatStore | 不持久化 | - | 聊天数据从服务器获取 |
| notificationStore | 不持久化 | - | 通知数据从服务器获取 |

```typescript
// main.ts 中配置持久化插件
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);
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

**Token 刷新机制说明（V11 补充完整流程）：**

1. 登录成功后同时获取 access token 和 refresh token
2. access token 存储在 memory 中，refresh token 持久化到 localStorage
3. Axios 请求拦截器中检查 token 有效期：
   - 若 token 将在 60 秒内过期，主动调用 `/auth/refresh` 刷新
   - 若接口返回 401，尝试使用 refresh token 刷新
   - 刷新成功后重试原请求
   - 刷新失败则跳转登录页
4. 同一时刻只允许一个 refresh 请求，其他请求排队等待

**V11 补充：Axios 拦截器 + 请求队列完整实现**

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

    // 401 且未重试过 -> 尝试刷新 token
    if (error.response?.status === 401 && !originalRequest._retried) {
      // 如果已经在刷新中，将请求加入队列等待
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
          // 刷新成功，更新原请求的 Authorization Header 并重试
          originalRequest.headers.Authorization = `Bearer ${userStore.accessToken}`;
          processQueue(null, userStore.accessToken);
          return api(originalRequest);
        } else {
          // 刷新失败（refresh token 也过期或无效）
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
    // V10 变更：流式输出也通过 WebSocket 处理，不再使用 SSE
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
- `handleStreamChunk` / `handleStreamDone`：V10 变更后，流式输出也通过 WebSocket 接收，由 chatStore 处理状态更新
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
  // 上报错误至后端
  api.post('/errors/report', {
    message: err.message,
    stack: err.stack,
    component: info,
    timestamp: new Date().toISOString(),
  }).catch(() => {}); // 避免二次报错
};

// 未处理的 Promise 拒绝
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

// 统一错误映射
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

// 全局错误提示 composable
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

---

## 6. WebSocket 统一通信设计

### 6.1 统一通信方案

**V9 -> V10 变更说明：**

V9 同时使用 WebSocket 和 SSE（EventSource）两种协议，存在以下问题：

1. EventSource 不支持自定义 Header，无法携带认证 token
2. 同时维护两种实时通信协议增加前后端复杂度
3. 需要后端额外设计 token-less 的 SSE 端点

V10 统一为 WebSocket 单一方案，所有实时通信（消息推送、状态变更、流式输出）均通过 WebSocket 完成。

### 6.2 WebSocket 事件类型

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| message.new | Server -> Client | 新消息推送（消息已完成） |
| message.deleted | Server -> Client | 消息删除通知 |
| agent.status | Server -> Client | Agent 状态变更 |
| task.updated | Server -> Client | 任务状态变更 |
| project.step.changed | Server -> Client | 项目步骤推进 |
| notification | Server -> Client | 系统通知推送 |
| stream.chunk | Server -> Client | Agent 回复内容增量追加（V10 新增，原为 SSE） |
| stream.done | Server -> Client | Agent 回复完成（V10 新增，原为 SSE） |
| stream.error | Server -> Client | 流式输出错误（V10 新增，原为 SSE） |
| chat.join | Client -> Server | 加入讨论群 |
| chat.leave | Client -> Server | 离开讨论群 |
| message.send | Client -> Server | 发送消息 |

**职责说明：**

- `message.new` 推送的是**已完成的消息**（即 Agent 回复完成后整条消息）
- `stream.chunk` / `stream.done` 负责**流式输出的过程展示**（原 SSE 职责迁移至 WebSocket）
- 两者不重复：流式输出结束后，客户端已拥有完整消息内容；`message.new` 仅在消息通过其他途径变更时推送
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
    // V10 变更：WebSocket URL 携带 token 参数用于认证
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
      // 连接错误，准备重连
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
      // 超过最大重连次数，通知用户
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
    reconnectStatus, // V11 新增：暴露重连状态供 UI 显示
    connect,
    disconnect,
    on,
    off,
  };
}
```

**V11 补充：重连机制完整说明**

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

**用户感知提示（V11 新增）：**

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

  // 绑定流式输出事件
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

  // 绑定消息推送事件
  ws.on('message.new', (data) => {
    chatStore.messages.push(data.message);
  });
});

onUnmounted(() => {
  ws.disconnect();
});
```

**V11 补充：打字机效果渲染方案**

流式输出采用 `requestAnimationFrame` 节流渲染，避免高频 DOM 更新导致页面卡顿：

```typescript
// composables/useStreamRender.ts
export function useStreamRender() {
  const displayContent = ref('');
  const pendingContent = ref('');
  let rafId: number | null = null;
  let lastRenderTime = 0;
  const renderInterval = 16; // ~60fps，约 16ms 一帧

  // 接收新的 chunk 内容
  const appendChunk = (chunk: string) => {
    pendingContent.value += chunk;
    scheduleRender();
  };

  // 使用 requestAnimationFrame 节流渲染
  const scheduleRender = () => {
    if (rafId !== null) return; // 已有一帧在等待，跳过
    rafId = requestAnimationFrame(() => {
      const now = performance.now();
      if (now - lastRenderTime >= renderInterval) {
        // 将待渲染内容追加到显示内容中
        displayContent.value += pendingContent.value;
        pendingContent.value = '';
        lastRenderTime = now;
      } else {
        // 未达到渲染间隔，继续等待下一帧
        scheduleRender();
        rafId = null;
        return;
      }
      rafId = null;
    });
  };

  // 流式输出结束时，渲染剩余内容
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
- 大体积库（ECharts、md-editor-v3）也会被单独拆分
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
          'vendor-echarts': ['echarts'],
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
- vendor-echarts chunk < 200KB (gzip)
- 首页首屏 JS 总体积 < 150KB (gzip)

### 7.2 路由守卫

```typescript
// src/router/guards.ts
router.beforeEach((to, from, next) => {
  const userStore = useUserStore();

  if (to.meta.requiresAuth !== false && !userStore.accessToken) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
    return;
  }

  if (to.name === 'Login' && userStore.accessToken) {
    next({ name: 'Dashboard' });
    return;
  }

  next();
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

### 9.2 暗黑模式切换机制（V11 补充完整说明）

```typescript
// composables/useTheme.ts
import { useSettingStore } from '@/stores/settingStore';

export function useTheme() {
  const settingStore = useSettingStore();

  const setTheme = (theme: 'light' | 'dark') => {
    settingStore.theme = theme; // 更新 settingStore，自动持久化到 localStorage
    applyTheme(theme);
  };

  const applyTheme = (theme: 'light' | 'dark') => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  // 初始化时读取持久化的主题设置
  onMounted(() => {
    if (settingStore.theme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  });

  return { setTheme };
}
```

**V11 补充：暗黑模式切换完整流程**

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
      dts: 'src/types/components.d.ts', // 生成类型声明
      resolvers: [
        ElementPlusResolver({
          importStyle: 'css', // 自动按需引入组件样式（CSS 版本）
        }),
      ],
    }),
    AutoImport({
      dts: 'src/types/auto-imports.d.ts',
      imports: ['vue', 'vue-router', 'pinia'],
      resolvers: [
        ElementPlusResolver(), // 自动按需导入 Element Plus  composables/API
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
// 移动端混入
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

// 使用示例
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
<!-- 表单无障碍示例 -->
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

**V11 补充：sanitize.ts 在 md-editor-v3 中的具体使用场景**

md-editor-v3 渲染 Agent 产出的 Markdown 内容（如 SRS 文档、架构设计文档、需求描述等）时，Agent 生成的 Markdown 可能包含恶意 HTML 注入（如 `<script>` 标签、`onerror` 事件属性等）。过滤方案如下：

```vue
<!-- ProjectDetailView 中的文档预览区域 -->
<template>
  <div ref="editorRef" class="md-preview" />
</template>

<script setup lang="ts">
import { sanitizeHtml } from '@/utils/sanitize';

const docContent = ref(''); // Agent 产出的 Markdown 原始内容

// md-editor-v3 预览模式下，使用自定义渲染钩子过滤 XSS
const previewConfig = {
  // md-editor-v3 支持在预览前对 HTML 进行处理
  codeHighlightTheme: 'default',
};

// 在将内容传入 md-editor-v3 之前，先过滤
watch(() => docContent.value, (newContent) => {
  // md-editor-v3 内部会将 Markdown 转为 HTML 再渲染
  // 我们在 v-html 渲染自定义预览时使用 sanitizeHtml
  sanitizedContent.value = sanitizeHtml(renderMarkdown(newContent));
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

| 组件 | 渲染内容来源 | 是否经过 sanitize |
|------|------------|-----------------|
| MessageBubble | Agent 消息（富文本） | 是 |
| ProjectDetailView 文档预览 | Agent 产出的 Markdown 文档 | 是 |
| MessageInput 发送的消息 | 用户输入（@tiptap 编辑器） | 提交后端前经过 sanitize |
| DashboardView 动态数据 | 后端 API 返回 | 使用 `{{ }}` 插值，Vue 默认转义 |

### 12.2 CSP（内容安全策略）

通过 Nginx 设置 CSP Header，限制资源加载来源：

```nginx
# nginx.conf 中添加
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
// axios 配置中确保不发送 Cookie
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  withCredentials: false, // 不发送 Cookie，避免 CSRF
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
          'vendor-echarts': ['echarts'],
          'vendor-editor': ['@tiptap/vue-3', 'md-editor-v3'],
        },
      },
    },
  },
});
```

### 14.2 Docker 部署

```dockerfile
# Dockerfile
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

    # 静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;  # history 模式路由 fallback
    }

    # API 反向代理
    location /api {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 反向代理
    location /ws {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;  # WebSocket 长连接超时
    }

    # CSP Header
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ws: wss:; frame-src 'none'; object-src 'none';";

    # Gzip 压缩
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
```

**history 模式路由 fallback 说明：**

- Vue Router 使用 history 模式（非 hash 模式）
- Nginx 配置 `try_files $uri $uri/ /index.html;` 实现前端路由 fallback
- 用户直接访问 `/projects/123` 时，Nginx 返回 `index.html`，由前端路由解析

---

## 15. V10 -> V11 修订记录

### 后荣检验意见与修订对照

| 编号 | 严重程度 | 后荣检验意见 | V11 修订内容 |
|------|----------|-------------|-------------|
| 1 | 致命 | 文档严重不完整：2.2.5 在'底部'处戛然而止，2.2.6 至 2.2.9 页面说明全部缺失 | 补全 2.2.5 底部区域说明（输入框、附件上传、发送按钮、连接状态指示、流式输出等待状态），补全 2.2.6 任务看板页（顶部工具栏、筛选、视图切换、统计），补全 2.2.7 QA 检验页（顶部工具栏、筛选、趋势图、详情抽屉），补全 2.2.8 代码仓库页（顶部工具栏、分支切换、搜索），补全 2.2.9 系统设置页（自动刷新间隔、清除缓存） |
| 2 | 严重 | 路由懒加载策略未配置 | V10 已有懒加载，V11 在 7.1 节补充明确说明：views 目录下 9 个页面全部使用 `() => import()` 懒加载，确保首屏只加载 Dashboard 相关代码 |
| 3 | 严重 | WebSocket 流式输出渲染未说明打字机效果实现方式 | 新增 6.4 节打字机效果方案：使用 `requestAnimationFrame` 节流渲染，pendingContent 缓冲 + 16ms 帧间隔控制 DOM 更新频率，避免高频 chunk 推送导致页面卡顿；新增 `useStreamRender` composable 示例代码 |
| 4 | 严重 | Markdown 内容安全：sanitize.ts 已规划但未说明具体使用场景 | 新增 12.1 节完整 XSS 防护方案：明确 md-editor-v3 渲染 Agent 产出 Markdown 时的过滤流程；补充危险注入类型对照表（`<script>`、`onerror`、`javascript:` URI、`<iframe>` 等）；补充使用场景汇总表（MessageBubble、ProjectDetailView、MessageInput 等） |
| 5 | 中等 | 长列表性能：需要虚拟列表方案 | 技术选型新增 vue-virtual-scroller；3.2.4 节 MessageList 补充 vue-virtual-scroller 的 `RecycleScroller` 实现方案及代码示例；2.2.8 节代码仓库页 CommitList 同样采用虚拟滚动 |
| 6 | 中等 | 暗黑模式：缺少切换机制说明 | 9.2 节补充完整暗黑模式切换流程：settingStore 管理 theme 字段 -> pinia-plugin-persistedstate 持久化 -> useTheme composable 切换 `html.dark` class -> Element Plus 内置 dark 主题自动跟随 -> 自定义组件通过 CSS 变量自动跟随；新增 settingStore 与暗黑模式关系对照表 |
| 7 | 中等 | 网络异常处理：WebSocket 断线重连策略未说明 | 6.3 节补充完整重连机制：最大重连 5 次、指数退避算法（1s/2s/4s/8s/16s）、重连成功后重置计数器、超限后停止重连；新增 `reconnectStatus` 响应式状态暴露给 UI 层；新增用户感知提示方案（连接状态指示灯 + ElMessage 错误提示）；新增重连参数对照表 |
| 8 | 中等 | 认证刷新机制：access token 过期的自动刷新流程未描述 | 4.2 节 userStore 已有完整实现，V11 在 api/index.ts 中补充完整的 Axios 拦截器 + 请求队列代码；新增请求队列工作流程图解（T1-T5 时序说明）；明确 isRefreshing 锁 + failedQueue 排队的并发安全机制 |

### V11 新增内容清单

| 新增项 | 位置 | 说明 |
|--------|------|------|
| vue-virtual-scroller | 1.2 技术选型表 + 3.2.4 节 | 长列表虚拟滚动方案 |
| DOMPurify 3.x | 1.2 技术选型表 + 12.1 节 | 明确 XSS 过滤库及使用场景 |
| useTheme composable | 1.4 目录结构 + 9.2 节 | 明确主题切换 composable 位置 |
| useStreamRender composable | 6.4 节 | 打字机效果渲染方案 |
| reconnectStatus 状态 | 6.3 节 | WebSocket 连接状态暴露给 UI |
| sanitize.ts 使用场景表 | 12.1 节 | XSS 过滤的具体使用场景汇总 |
| 请求队列工作流程图 | 4.2 节 | Token 刷新请求队列时序说明 |
| 2.2.5-2.2.9 页面详说 | 2.2 节 | 补全所有缺失的页面详细说明 |

### V11 对 V10 的变更

| 变更项 | V10 | V11 |
|--------|-----|-----|
| 2.2.5 讨论群聊天 | 底部区域说明缺失 | 补全底部输入框、附件上传、发送按钮、连接状态指示、流式等待状态 |
| 2.2.6 任务看板 | 仅有基本列说明 | 补充顶部工具栏、筛选条件、视图切换、统计信息 |
| 2.2.7 QA 检验 | 仅有基本列表说明 | 补充顶部工具栏、筛选、趋势图、详情抽屉 |
| 2.2.8 代码仓库 | 仅有基本组件说明 | 补充顶部工具栏、分支切换、搜索、虚拟滚动 |
| 2.2.9 系统设置 | 仅有四项基本设置 | 补充自动刷新间隔、清除本地缓存 |
| 虚拟列表 | 未选型 | 新增 vue-virtual-scroller |
| XSS 过滤库 | sanitize.ts 已规划 | 明确 DOMPurify 3.x，补充完整使用场景 |
| 暗黑模式 | 9.2 节仅有代码示例 | 补充完整切换流程、settingStore 关系说明、Element Plus 跟随机制 |
| WebSocket 重连 | 有代码但缺说明 | 补充参数表、用户感知提示、reconnectStatus 状态 |
| Token 刷新 | 有代码但缺流程说明 | 补充完整 Axios 拦截器代码、请求队列时序图 |
| 流式输出渲染 | 仅有 store 层处理 | 补充打字机效果、requestAnimationFrame 节流方案 |

---

## 16. V9 -> V10 修订记录（历史保留）

| 编号 | 严重程度 | 后荣检验意见 | V10 修订内容 |
|------|----------|-------------|-------------|
| 1 | 严重 | 文档截断、章节缺失 | 本文档为完整独立文档，包含全部章节（1-15章），无截断 |
| 2 | 严重 | 缺少 API 接口设计说明 | 新增 5.2 节 API 端点清单，列出所有端点的方法、路径、说明 |
| 3 | 严重 | 缺少错误处理统一方案 | 新增 5.3 节错误处理方案：全局异常捕获 + Axios 错误处理 + ErrorBoundary 组件 |
| 4 | 中等 | SSE EventSource 不支持自定义 Header | 统一为 WebSocket 方案，移除 SSE/EventSource，流式输出改为 WebSocket 事件（stream.chunk / stream.done） |
| 5 | 中等 | 同时使用 WebSocket + SSE 增加复杂度 | 统一为 WebSocket 单一方案，详见 6 节 WebSocket 统一通信设计 |
| 6 | 中等 | 缺少测试框架选型 | 新增 13 节测试设计：Vitest + @vue/test-utils + Playwright，含配置、覆盖率要求、示例代码 |
| 7 | 中等 | 缺少打包体积优化方案 | 新增路由懒加载策略、manualChunks 代码分割、打包体积目标值 |
| 8 | 中等 | 无障碍标准无具体实施方案 | 扩充 10 节无障碍设计：键盘导航、屏幕阅读器、对比度、表单无障碍、焦点管理，含代码示例 |
| 9 | 中等 | 深色主题切换机制未说明 | 改为 CSS 变量方案，新增 9.2 节主题切换机制（composable + class 切换），运行时生效无需重编译 |
| 10 | 中等 | Element Plus 样式按需引入方案未说明 | 新增 9.3 节：unplugin-vue-components + ElementPlusResolver + unplugin-auto-import 完整方案 |
| 11 | 中等 | 未说明移动端适配策略 | 新增 9.4 节：响应式断点定义、各断点布局方案、移动端具体适配说明 |
| 12 | 中等 | 未说明多环境配置方案 | 新增 11 节多环境配置：.env / .env.development / .env.production 及构建命令 |
| 13 | 中等 | 未说明构建产物部署方案 | 新增 14.3 节 Nginx 配置：history 模式 fallback、WebSocket 代理、CSP Header、Gzip 压缩 |
| 14 | 轻微 | 未说明 Pinia 持久化策略 | 新增 4.1 节持久化策略：pinia-plugin-persistedstate，明确各 store 持久化字段和存储介质 |
| 15 | 轻微 | refresh token 无感刷新流程未设计 | 4.2 节 userStore 已有完整实现：拦截器排队机制 + 60 秒提前刷新 + 失败重定向 |
| 16 | 中等 | 无 XSS 防护方案 | 新增 12.1 节：Vue 默认转义 + DOMPurify 过滤富文本 + sanitizeHtml 工具函数 |
| 17 | 中等 | 无 CSP 设计 | 新增 12.2 节：Nginx 设置 CSP Header，包含各指令及说明 |
| 18 | 中等 | 无 CSRF 防护说明 | 新增 12.3 节：Bearer Token 无状态认证天然免疫 CSRF + withCredentials:false |

### V10 新增章节清单

| 章节 | 标题 | 说明 |
|------|------|------|
| 6 | WebSocket 统一通信设计 | 替代 V9 的 6 节（原为 WebSocket 与 SSE 双协议） |
| 11 | 多环境配置 | 响应后荣检验意见 |
| 12 | 安全设计 | 响应后荣检验意见 |
| 13 | 测试设计 | 响应后荣检验意见 |
| 14 | 构建与部署 | 整合 V9 的 11 节并扩充 |
| 15 | V9 -> V10 修订记录 | 记录本次修订内容 |

### V10 移除内容

| 移除项 | 原因 |
|--------|------|
| useSSE composable | 统一为 WebSocket 后不再需要 |
| SSE 相关 Nginx 配置（/api/stream） | 统一为 WebSocket 后不再需要 |
| useSSE.ts 文件引用 | 统一为 WebSocket 后不再需要 |
